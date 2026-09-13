'use strict';
// Actual shipped UI + actual workspace routes, with a controlled CI-only identity
// and provider. The backend lifecycle is also tested independently in Python.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'acs-ui-')),port=8891;
 const child=spawn(process.env.PYTHON||'python',['tests/remediation/connected_workspace_browser_server.py','--port',String(port),'--database',path.join(tmp,'plans.sqlite3')],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
 let backendLog='';child.stderr.on('data',b=>{backendLog+=b;});
 let browser;
 try{
  let ready=false;for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:'+port+'/health')).ok){ready=true;break;}}catch(e){}await delay(250);}
  assert.ok(ready,'fixture backend did not start: '+backendLog);browser=await PW.launch();
  for(const width of [393,1280]){
   const context=await browser.newContext({viewport:{width,height:900},acceptDownloads:true}),page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.hostname==='acs-engine.onrender.com'){
      const response=await route.fetch({url:'http://127.0.0.1:'+port+url.pathname+url.search});return route.fulfill({response});
    }
    if(url.hostname!=='acs-ui.test')return route.abort();
    const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(f)});
   });
   await page.goto('https://acs-ui.test/');
   await page.locator('#lgEmail').fill('fixture@example.test');await page.locator('#lgPassword').fill('fixture-password');await page.locator('#lgGo').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
   await page.locator('#cwNewProject').click();await page.locator('#cwProjectName').fill('مشروع قبول '+width);
   await Promise.all([page.waitForEvent('framenavigated',frame=>frame===page.mainFrame()),page.locator('#cwNewProjectForm button[type=submit]').click()]);
   await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
   assert.equal(await page.locator('#cwProject option:checked').textContent(),'مشروع قبول '+width);
   await page.locator('#cwBrief').waitFor({state:'visible'});
   await page.locator('#cwType').selectOption(width===393?'warehouse':'residential');
   await page.locator('#cwBrief').fill(width===393?'مستودع تجريبي على موقع بعرض 20 متر':'مشروع سكني تجريبي على موقع بعرض 20 متر');
   await page.locator('#cwWidth').fill('20');await page.locator('#cwDepth').fill('20');await page.locator('#cwLevels').fill('1');
   await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();
   const before=(await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation;
   await page.locator('[data-option=A]').click();await page.locator('#cwRecoverJob').waitFor({state:'visible'});
   await page.reload();await page.locator('#cwReviewContent').waitFor({state:'visible',timeout:45000});
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,before+1,'reload must not submit a second paid job');
   assert.ok(await page.locator('#cwPlan g[role=button]').count());
   assert.equal(await page.locator('#cwApprove').isEnabled(),false);
   await page.locator('#cwSpaces button').first().click();await page.locator('#cwLock').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('القفل'));
   await page.locator('#cwSpaces button').first().click();assert.equal(await page.locator('#cwSaveGeometry').isEnabled(),false);
   await page.locator('#cwApproveConfirm').check();await page.locator('#cwApprove').click();
   await page.locator('#cwShow3D').waitFor({state:'visible'});assert.equal(await page.locator('#cwShow3D').isEnabled(),true);
   const downloadPromise=page.waitForEvent('download');await page.locator('[data-format=svg]').click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'acs-approved.svg');
   await page.locator('#cwShow3D').click();await page.locator('#cwViewer canvas').waitFor({state:'visible',timeout:45000});
   assert.ok((await page.locator('#cwViewer canvas').boundingBox()).width>100);
   assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false);
   const revisionsBeforeChat=await page.locator('#cwRevision option').count();
   await page.locator('[data-step="3"]').click();await page.locator('#cwChat').fill('غيّر عرض الفراغ B مع تثبيت الفراغ المقفل.');await page.locator('#cwChatSubmit').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('تم حفظ المخطط'),{},{timeout:45000});
   assert.equal(await page.locator('#cwRevision option').count(),revisionsBeforeChat+1,'one chat edit must append one revision; approval itself preserves the selected version');
   assert.ok((await page.locator('#cwRevision option').allTextContents()).some(t=>t.includes('معتمدة')),'the previous approval remains in history');
   await page.locator('#cwCompare').click();await page.locator('#cwComparison').waitFor({state:'visible'});
   assert.ok(await page.locator('#cwComparisonRows tr').count()>2);
   await page.locator('#cwLogout').click();await page.locator('#lgEmail').waitFor({state:'visible'});
   assert.deepEqual(errors,[]);console.log('PASS connected workspace '+width+': generation, reload, lock, approval, SVG, exact 3D, chat revision, logout');
   await context.close();
  }
 }finally{if(browser)await browser.close();child.kill('SIGTERM');fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
