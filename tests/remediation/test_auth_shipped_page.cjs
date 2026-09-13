'use strict';
// Real shipped page and strict CSP, controlled auth service, no production user.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const session=()=>({access_token:'fixture-access',refresh_token:'fixture-refresh',expires_at:Math.floor(Date.now()/1000)+3600,user:{id:'fixture-user',email:'fixture@example.test'}});
(async()=>{
  const browser=await PW.launch();
  try{
    for(const width of [393,1280]){
      const context=await browser.newContext({viewport:{width,height:852}}), page=await context.newPage();
      const errors=[], calls=[];let firstProject=null, failSignin=true;
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/*',async route=>{
        const req=route.request(),url=new URL(req.url());
        if(url.hostname==='acs-engine.onrender.com'){
          const headers={'content-type':'application/json','access-control-allow-origin':'https://acs-ui.test',
            'access-control-allow-headers':'content-type,accept,authorization','access-control-allow-methods':'GET,POST,OPTIONS'};
          if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
          calls.push(url.pathname);
          let body={},status=200;
          if(url.pathname==='/health')body={ok:true,api_key_configured:true};
          else if(url.pathname==='/v1/auth/signin'){
            if(failSignin){status=503;body={error:{code:'AUTH_UPSTREAM_UNAVAILABLE',message:'خدمة الدخول غير متاحة مؤقتًا.'}};}
            else body=session();
          }else if(url.pathname==='/v1/auth/refresh')body=session();
          else if(url.pathname==='/v1/auth/bootstrap-project'){
            const input=req.postDataJSON();
            if(!firstProject&&!input.name){status=400;body={error:{code:'PROJECT_NAME_REQUIRED',message:'اسم المشروع مطلوب.'}};}
            else {firstProject=firstProject||{id:'fixture-project',name:input.name};body={project:firstProject,user:{id:'fixture-user'}};}
          }else if(url.pathname==='/v1/auth/signout')body={ok:true};
          else return route.abort();
          return route.fulfill({status,headers,body:JSON.stringify(body)});
        }
        if(url.hostname!=='acs-ui.test')return route.abort();
        const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
        if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
        return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream',
          'content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(f)});
      });
      await page.goto('https://acs-ui.test/');
      await page.waitForFunction(()=>window.ACS&&window.ACS.ready&&window.ACS.persistence);
      assert.equal(await page.locator('#lgName').isVisible(),false);
      assert.equal(await page.locator('#lgProject').isVisible(),false);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.ok((await page.locator('#login .card').boundingBox()).width<=448,'shared card styles must not stretch the sign-in form');
      await page.locator('#lgEmail').fill('fixture@example.test');
      await page.locator('#lgPassword').fill('fixture-password');
      await page.locator('#acsPasswordToggle').click();
      assert.equal(await page.locator('#lgPassword').getAttribute('type'),'text');
      await page.locator('#lgGo').click();
      await page.waitForFunction(()=>document.querySelector('#acsAuthStatus').textContent.includes('مؤقتًا'));
      assert.equal(await page.locator('#lgGo').isEnabled(),true);
      failSignin=false;await page.locator('#lgGo').click();
      await page.locator('#acsAuthProjectField').waitFor({state:'visible'});
      assert.equal(await page.locator('#lgPassword').inputValue(),'');
      assert.equal(await page.locator('#acsAuthCredentials').isVisible(),false);
      await page.locator('#lgProject').fill('مشروع تحقق الواجهة');await page.locator('#lgGo').click();
      await page.waitForFunction(()=>document.body.classList.contains('acs-entered'));
      assert.equal(await page.evaluate(()=>window.ACS.projectId),'fixture-project');
      assert.equal(await page.evaluate(()=>!!window.ACS.exportModel()),false,'production entry must not inject a demo');
      const before=calls.filter(p=>p==='/v1/auth/signin').length;
      await page.reload();await page.waitForFunction(()=>document.body.classList.contains('acs-entered'));
      assert.equal(calls.filter(p=>p==='/v1/auth/signin').length,before,'reload reuses a verified session');
      assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_local_project:fixture-user:fixture-project');
      await page.locator('#acsLogout').click();
      await page.waitForFunction(()=>!localStorage.getItem('acs_supabase_session_v1')&&document.querySelector('#lgEmail')&&!document.querySelector('#acsAuthCredentials').hidden);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      assert.deepEqual(errors,[]);
      fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
      await page.screenshot({path:path.join(ROOT,'logs','auth-'+width+'.png')});
      console.log('PASS shipped auth '+width+': first opening, service error, project onboarding, reload and logout');
      await context.close();
    }
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
