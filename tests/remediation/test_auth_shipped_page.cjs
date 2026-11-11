'use strict';
// Real shipped page and strict CSP, controlled auth service, no production user.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const session=()=>({access_token:'fixture-access',refresh_token:'fixture-refresh',expires_at:Math.floor(Date.now()/1000)+3600,user:{id:'fixture-user',email:'fixture@example.test'}});
const sourcePath='/v1/projects/fixture-project/workspace/plan-source';
const sourceResponse=page=>page.waitForResponse(response=>new URL(response.url()).pathname===sourcePath&&response.request().method()==='POST');
async function privateWorkspaceReady(page,sourceRestore){
  const response=await sourceRestore;
  assert.equal(response.status(),200,'the authenticated source list must finish restoring');
  assert.deepEqual((await response.json()).sources,[]);
  await page.locator('#designWorkspace').waitFor({state:'visible'});
  await page.waitForFunction(()=>{
    const status=document.querySelector('#cwStatus');
    return status&&(status.textContent.includes('مشروعك جاهز')||status.getAttribute('role')==='alert');
  });
  assert.match(await page.locator('#cwStatus').textContent(),/مشروعك جاهز/,'private workspace must finish successfully');
  assert.equal(await page.locator('#cwProject').inputValue(),'fixture-project');
  assert.equal(await page.locator('#cwBriefForm').isVisible(),true);
}
(async()=>{
  const browser=await PW.launch();
  try{
    for(const width of [393,1280]){
      const context=await browser.newContext({viewport:{width,height:852}}), page=await context.newPage();
      const errors=[], calls=[], localModules=[];let firstProject=null, failSignin=true, googleChallenge=null;
      page.on('pageerror',e=>errors.push(e.message));
      try{
      await page.route('**/*',async route=>{
        const req=route.request(),url=new URL(req.url());
        if(['/app/render/scene.js','/app/ui/workspace-ui-wiring.js','/app/ui/guest-workspace.js'].includes(url.pathname))localModules.push(url.pathname);
        if(url.hostname==='auth.example.test'){
          assert.equal(url.pathname,'/auth/v1/authorize');
          assert.equal(url.searchParams.get('code_challenge'),googleChallenge);
          return route.fulfill({status:302,headers:{location:'https://acs-ui.test/?code=11111111-1111-4111-8111-111111111111'}});
        }
        if(url.hostname==='acs-engine.onrender.com'){
          const headers={'content-type':'application/json','access-control-allow-origin':'https://acs-ui.test',
            'access-control-allow-headers':'content-type,accept,authorization','access-control-allow-methods':'GET,POST,OPTIONS'};
          if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
          calls.push(url.pathname);
          let body={},status=200;
          if(url.pathname==='/health')body={ok:true,api_key_configured:true};
          else if(url.pathname==='/v1/auth/google/start'){
            const input=req.postDataJSON();googleChallenge=input.code_challenge;
            assert.equal(input.code_verifier,undefined);
            body={redirect_to:'https://acs-ui.test/',url:'https://auth.example.test/auth/v1/authorize?'+new URLSearchParams({
              provider:'google',redirect_to:'https://acs-ui.test/',code_challenge:googleChallenge,code_challenge_method:'s256'})};
          }else if(url.pathname==='/v1/auth/google/exchange'){
            const input=req.postDataJSON();assert.equal(input.auth_code,'11111111-1111-4111-8111-111111111111');
            assert.equal(require('node:crypto').createHash('sha256').update(input.code_verifier).digest('base64url'),googleChallenge);
            body=session();
          }
          else if(url.pathname==='/v1/auth/signin'){
            if(failSignin){status=503;body={error:{code:'AUTH_UPSTREAM_UNAVAILABLE',message:'خدمة الدخول غير متاحة مؤقتًا.'}};}
            else body=session();
          }else if(url.pathname==='/v1/auth/refresh')body=session();
          else if(url.pathname==='/v1/auth/bootstrap-project'){
            const input=req.postDataJSON();
            if(!firstProject&&!input.name){status=400;body={error:{code:'PROJECT_NAME_REQUIRED',message:'اسم المشروع مطلوب.'}};}
            else {firstProject=firstProject||{id:'fixture-project',name:input.name};body={project:firstProject,user:{id:'fixture-user'}};}
          }else if(url.pathname==='/v1/auth/signout')body={ok:true};
          else if(url.pathname==='/v1/auth/projects')body={ok:true,projects:firstProject?[firstProject]:[]};
          else if(url.pathname==='/v1/projects/fixture-project/workspace'){
            assert.equal(req.headers().authorization,'Bearer fixture-access');
            assert.deepEqual(req.postDataJSON(),{action:'state'});
            body={ok:true,head:null,baseline:null,history:[],revision_id:null};
          }else if(url.pathname===sourcePath){
            assert.equal(req.headers().authorization,'Bearer fixture-access');
            assert.deepEqual(req.postDataJSON(),{action:'list'},'sign-in must only read existing sources');
            body={ok:true,sources:[]};
          }
          else return route.abort();
          return route.fulfill({status,headers,body:JSON.stringify(body)});
        }
        if(url.hostname!=='acs-ui.test')return route.abort();
        const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
        if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
        return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream',
          'content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(f)});
      });
      await page.goto('https://acs-ui.test/?signin=1');
      await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
      assert.equal(await page.evaluate(()=>!!window.ACS_AUTH&&!window.ACS.guest),true);
      assert.equal(await page.locator('#app canvas').count(),0,'sign-in must allocate no hidden renderer');
      assert.equal(await page.locator('#lgName').isVisible(),false);
      assert.equal(await page.locator('#lgProject').isVisible(),false);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.ok((await page.locator('#login .card').boundingBox()).width<=448,'shared card styles must not stretch the sign-in form');
      assert.equal(await page.locator('#acsAuthGoogle').isVisible(),true);
      await page.locator('#acsAuthRecover').click();
      assert.equal(await page.locator('#lgGo').textContent(),'إرسال رابط الاستعادة');
      assert.equal(await page.locator('#lgPassword').isVisible(),false);
      assert.equal(await page.locator('#acsAuthGoogle').isVisible(),false);
      await page.locator('#lgSignup').click();
      await page.locator('#acsAuthResend').click();
      assert.equal(await page.locator('#lgGo').textContent(),'إرسال رسالة التأكيد');
      await page.locator('#lgSignup').click();
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
      const firstSourceRestore=sourceResponse(page);
      await page.locator('#lgProject').fill('مشروع تحقق الواجهة');await page.locator('#lgGo').click();
      await page.waitForFunction(()=>document.body.classList.contains('acs-entered'));
      assert.equal(await page.evaluate(()=>window.ACS.projectId),'fixture-project');
      await privateWorkspaceReady(page,firstSourceRestore);
      assert.equal(await page.evaluate(()=>window.ACS.exportModel?.()??null),null,'production entry must not inject a demo');
      assert.equal(await page.evaluate(()=>typeof window.ACS.persistence),'undefined','private review must not mount guest/local persistence');
      assert.equal(await page.locator('#app canvas').count(),0,'private entry must allocate no hidden renderer');
      assert.deepEqual(localModules,[],'sign-in and private review must not import the local studio graph');
      const before=calls.filter(p=>p==='/v1/auth/signin').length;
      const reloadSourceRestore=sourceResponse(page);
      await page.reload();await page.waitForFunction(()=>document.body.classList.contains('acs-entered'));
      await privateWorkspaceReady(page,reloadSourceRestore);
      assert.equal(calls.filter(p=>p==='/v1/auth/signin').length,before,'reload reuses a verified session');
      assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_local_project:fixture-user:fixture-project');
      // Logout owns a full reload. Wait for that navigation before starting a new
      // auth flow so the stale logout handler cannot overtake the Google redirect.
      await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.locator('#cwLogout').click()]);
      await page.waitForFunction(()=>!localStorage.getItem('acs_supabase_session_v1'));
      await page.goto('https://acs-ui.test/?signin=1');
      await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
      assert.equal(await page.evaluate(()=>!!window.ACS_AUTH&&!window.ACS.guest),true);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      // A real browser redirect round trip must preserve this tab's PKCE proof,
      // restore the same Supabase project, and keep auth codes out of the URL.
      const googleSourceRestore=sourceResponse(page);
      await page.locator('#acsAuthGoogle').click();
      await page.waitForFunction(()=>document.body.classList.contains('acs-entered'));
      await privateWorkspaceReady(page,googleSourceRestore);
      assert.equal(page.url(),'https://acs-ui.test/');
      assert.equal(await page.evaluate(()=>sessionStorage.getItem('acs_google_pkce_v1')),null);
      assert.equal(await page.evaluate(()=>window.ACS.projectId),'fixture-project');
      assert.equal(calls.filter(p=>p==='/v1/auth/google/exchange').length,1);
      assert.equal(calls.filter(p=>p==='/v1/auth/signin').length,before);
      await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.locator('#cwLogout').click()]);
      await page.waitForFunction(()=>!localStorage.getItem('acs_supabase_session_v1')&&document.querySelector('#acsAuthGoogle')&&!document.querySelector('#acsAuthGoogle').disabled);
      assert.deepEqual(errors,[]);
      fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
      await page.screenshot({path:path.join(ROOT,'logs','auth-'+width+'.png')});
      console.log('PASS shipped auth '+width+': email entry, project onboarding, Google PKCE redirect, reload and logout');
      }catch(error){
        fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
        const visible=await page.evaluate(()=>Object.fromEntries(['acsAuthStatus','cwStatus'].map(id=>{
          const el=document.getElementById(id),rect=el?.getBoundingClientRect(),style=el&&getComputedStyle(el);
          return [id,{visible:!!rect&&rect.width>0&&rect.height>0&&style.visibility!=='hidden'&&style.display!=='none',text:el?.textContent?.slice(0,300)||''}];
        }))).catch(()=>({unavailable:true}));
        const diagnostic={width,error_type:error.name,visible,endpoint_paths:[...new Set(calls)],local_modules:localModules};
        fs.writeFileSync(path.join(ROOT,'logs','auth-failure-'+width+'.json'),JSON.stringify(diagnostic,null,2));
        await page.screenshot({path:path.join(ROOT,'logs','auth-failure-'+width+'.png'),mask:[page.locator('input')]}).catch(()=>{});
        console.error('AUTH FIXTURE DIAGNOSTIC',JSON.stringify(diagnostic));
        throw error;
      }finally{await context.close();}
    }
  }finally{await browser.close();}
  await require('./test_guest_workspace.cjs').runGuestWorkspaceTests();
})().catch(e=>{console.error(e);process.exitCode=1;});
