'use strict';
// Real shipped page and strict CSP, controlled auth service, no production user.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
// The page sends sign-in on any other origin to the official site, which is
// also the only origin the backend's CORS accepts. A Netlify branch deploy of
// the same site is the copy the owner's iPhone was refused from.
const OFFICIAL=/OFFICIAL_ORIGIN\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(PUB,'app','boot','api-base.js'),'utf8'))[1];
const PREVIEW='https://main--'+new URL(OFFICIAL).host;
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const session=()=>({access_token:'fixture-access',refresh_token:'fixture-refresh',expires_at:Math.floor(Date.now()/1000)+3600,user:{id:'fixture-user',email:'fixture@example.test'}});
const sourcePath='/v1/projects/fixture-project/workspace/plan-source';
function sourceResponse(page){
  const pending=page.waitForResponse(response=>new URL(response.url()).pathname===sourcePath&&response.request().method()==='POST');
  // Observe teardown rejection immediately: a failed navigation may prevent the
  // caller from reaching its await. Return the original promise so a source
  // request failure still fails privateWorkspaceReady instead of being swallowed.
  pending.catch(()=>{});
  return pending;
}
function workspaceEntered(){return !!document.body&&document.body.classList.contains('acs-entered');}
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
async function runAuthShippedPage(){
  const browser=await PW.launch();
  try{
    for(const width of [393,1440]){
      const context=await browser.newContext({viewport:{width,height:width===393?852:900}}), page=await context.newPage();
      const errors=[], calls=[], localModules=[], backendRefused=[];let firstProject=null, failSignin=true, failGoogle=true, googleChallenge=null;
      page.on('pageerror',e=>errors.push(e.message));
      try{
      await context.route('**/*',async route=>{
        const req=route.request(),url=new URL(req.url());
        if(['/app/render/scene.js','/app/ui/workspace-ui-wiring.js','/app/ui/guest-workspace.js'].includes(url.pathname))localModules.push(url.pathname);
        if(url.hostname==='auth.example.test'){
          assert.equal(url.pathname,'/auth/v1/authorize');
          assert.equal(url.searchParams.get('code_challenge'),googleChallenge);
          // The test provider completes consent in the same tab, as a user would.
          return route.fulfill({contentType:'text/html',body:'<a href="'+OFFICIAL+'/?code=11111111-1111-4111-8111-111111111111">Continue with test account</a>'});
        }
        if(url.hostname==='acs-engine.onrender.com'){
          // Like the deployed backend, only the official origin passes CORS.
          const from=(await req.allHeaders()).origin;
          if(from!==OFFICIAL){backendRefused.push(req.method()+' '+url.pathname+' from '+from);
            return route.fulfill({status:400,contentType:'text/plain',body:'Disallowed CORS origin'});}
          const headers={'content-type':'application/json','access-control-allow-origin':OFFICIAL,
            'access-control-allow-headers':'content-type,accept,authorization','access-control-allow-methods':'GET,POST,OPTIONS'};
          if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
          calls.push(url.pathname);
          let body={},status=200;
          if(url.pathname==='/health')body={ok:true,api_key_configured:true};
          else if(url.pathname==='/v1/auth/google/start'){
            const input=req.postDataJSON();googleChallenge=input.code_challenge;
            assert.equal(input.code_verifier,undefined);
            body={redirect_to:OFFICIAL+'/',url:'https://auth.example.test/auth/v1/authorize?'+new URLSearchParams({
              provider:'google',redirect_to:OFFICIAL+'/',code_challenge:googleChallenge,code_challenge_method:'s256'})};
            if(failGoogle){status=503;body={error:{code:'AUTH_UPSTREAM_UNAVAILABLE'}};}
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
          }else if(url.pathname==='/v1/auth/update-password'){
            assert.equal(req.headers().authorization,'Bearer fixture-access');
            assert.equal(req.postDataJSON().password,'fixture-new-password');
            body={ok:true};
          }else if(url.pathname==='/v1/auth/signout')body={ok:true};
          else if(url.pathname==='/v1/auth/projects')body={ok:true,projects:firstProject?[firstProject]:[]};
          else if(url.pathname==='/v1/projects/fixture-project/workspace'){
            assert.equal(req.headers().authorization,'Bearer fixture-access');
            // Sign-in may only read the workspace: its state, the list of saved
            // generated versions (kept when a paid result lost to a manual edit)
            // and the latest brief read of an empty project.
            const input=req.postDataJSON();
            if(input?.action==='generated_versions'){
              assert.deepEqual(input,{action:'generated_versions'},'sign-in must only read saved generated versions');
              body={ok:true,versions:[]};
            }else if(input?.action==='brief_read_latest'){
              // An empty project may restore a brief read on another device; still a read.
              assert.deepEqual(input,{action:'brief_read_latest'},'sign-in must only read the latest brief read');
              body={ok:true,read:null};
            }else{
              assert.deepEqual(input,{action:'state'},'sign-in must only read the workspace state');
              body={ok:true,head:null,baseline:null,history:[],revision_id:null};
            }
          }else if(url.pathname===sourcePath){
            assert.equal(req.headers().authorization,'Bearer fixture-access');
            assert.deepEqual(req.postDataJSON(),{action:'list'},'sign-in must only read existing sources');
            body={ok:true,sources:[]};
          }
          else return route.abort();
          return route.fulfill({status,headers,body:JSON.stringify(body)});
        }
        if(url.origin!==OFFICIAL&&url.origin!==PREVIEW)return route.abort();
        const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
        if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
        return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream',
          'content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(f)});
      });
      await page.goto(OFFICIAL+'/?signin=1');
      await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
      assert.equal(await page.evaluate(()=>!!window.ACS_AUTH&&!window.ACS.guest),true);
      assert.equal(await page.locator('#app canvas').count(),0,'sign-in must allocate no hidden renderer');
      assert.equal(await page.locator('#lgName').isVisible(),false);
      assert.equal(await page.locator('#lgProject').isVisible(),false);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.ok((await page.locator('#login .card').boundingBox()).width<=448,'shared card styles must not stretch the sign-in form');
      assert.equal(await page.locator('#acsAuthGoogle').isVisible(),true);
      assert.equal(await page.locator('#acsAuthOfficial').isVisible(),false,'the official site shows no preview notice');
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
      const fallback=page.locator('#acsAuthGuestLink');
      assert.equal(await fallback.textContent(),'متابعة بدون حساب');
      assert.equal(await fallback.getAttribute('href'),'/?guest=1');
      const fallbackBox=await fallback.boundingBox(), googleBox=await page.locator('#acsAuthGoogle').boundingBox();
      assert.ok(fallbackBox&&fallbackBox.height>=44&&fallbackBox.y>googleBox.y+googleBox.height,
        'optional local entry remains reachable below primary account actions');
      const googleLabel=page.locator('#acsAuthGoogle span').last();
      assert.equal(await googleLabel.evaluate(el=>getComputedStyle(el).color),
        await page.locator('#acsAuthGoogle').evaluate(el=>getComputedStyle(el).color));
      fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
      await page.screenshot({path:path.join(ROOT,'logs','auth-service-unavailable-'+width+'.png'),mask:[page.locator('input')]});
      failSignin=false;await page.locator('#lgGo').click();
      await page.locator('#acsAuthProjectField').waitFor({state:'visible'});
      assert.equal(await page.locator('#lgPassword').inputValue(),'');
      assert.equal(await page.locator('#acsAuthCredentials').isVisible(),false);
      const firstSourceRestore=sourceResponse(page);
      await page.locator('#lgProject').fill('مشروع تحقق الواجهة');await page.locator('#lgGo').click();
      await page.waitForFunction(workspaceEntered);
      assert.equal(await page.evaluate(()=>window.ACS.projectId),'fixture-project');
      await privateWorkspaceReady(page,firstSourceRestore);
      assert.equal(await page.evaluate(()=>window.ACS.exportModel?.()??null),null,'production entry must not inject a demo');
      assert.equal(await page.evaluate(()=>typeof window.ACS.persistence),'undefined','private review must not mount guest/local persistence');
      assert.equal(await page.locator('#app canvas').count(),0,'private entry must allocate no hidden renderer');
      assert.deepEqual(localModules,[],'sign-in and private review must not import the local studio graph');
      const before=calls.filter(p=>p==='/v1/auth/signin').length;
      const reloadSourceRestore=sourceResponse(page);
      await page.reload();await page.waitForFunction(workspaceEntered);
      await privateWorkspaceReady(page,reloadSourceRestore);
      assert.equal(calls.filter(p=>p==='/v1/auth/signin').length,before,'reload reuses a verified session');
      assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_local_project:fixture-user:fixture-project');
      // Logout owns a full reload. Wait for that navigation before starting a new
      // auth flow so the stale logout handler cannot overtake the Google redirect.
      await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.locator('#cwLogout').click()]);
      await page.waitForFunction(()=>!localStorage.getItem('acs_supabase_session_v1'));
      await page.goto(OFFICIAL+'/?signin=1');
      await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
      assert.equal(await page.evaluate(()=>!!window.ACS_AUTH&&!window.ACS.guest),true);
      assert.equal(await page.locator('#camBar').isVisible(),false);
      // A real browser redirect round trip must preserve this tab's PKCE proof,
      // restore the same Supabase project, and keep auth codes out of the URL.
      await page.getByRole('button',{name:'المتابعة باستخدام Google'}).click();
      const retry=page.getByRole('button',{name:'إعادة المحاولة باستخدام Google'});
      await retry.waitFor({state:'visible'});
      assert.equal(await retry.isEnabled(),true);
      assert.match(await page.locator('#acsAuthStatus').innerText(),/الاتصال بخدمة الحسابات.*Google/);
      assert.equal(page.url(),OFFICIAL+'/?signin=1');
      assert.equal(await page.evaluate(()=>sessionStorage.getItem('acs_google_pkce_v1')),null);
      failGoogle=false;
      const googleSourceRestore=sourceResponse(page);
      await retry.click();
      const consent=page.getByRole('link',{name:'Continue with test account'});
      await consent.waitFor({state:'visible'});
      assert.equal(new URL(page.url()).origin,'https://auth.example.test');
      assert.equal(calls.filter(p=>p==='/v1/auth/google/start').length,2);
      await consent.click();
      await page.waitForFunction(workspaceEntered);
      await privateWorkspaceReady(page,googleSourceRestore);
      assert.equal(page.url(),OFFICIAL+'/');
      assert.equal(await page.evaluate(()=>sessionStorage.getItem('acs_google_pkce_v1')),null);
      assert.equal(await page.evaluate(()=>window.ACS.projectId),'fixture-project');
      assert.equal(calls.filter(p=>p==='/v1/auth/google/exchange').length,1);
      assert.equal(calls.filter(p=>p==='/v1/auth/signin').length,before);
      const second=await context.newPage();
      const secondSource=sourceResponse(second);
      await second.goto(OFFICIAL+'/?signin=1');
      await privateWorkspaceReady(second,secondSource);
      await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),second.waitForNavigation({waitUntil:'domcontentloaded'}),second.locator('#cwLogout').click()]);
      assert.equal(await page.locator('#designWorkspace').isVisible(),false,'signing out in the other tab closes the old project');
      assert.equal(await page.evaluate(()=>localStorage.getItem('acs_supabase_session_v1')),null);
      await second.close();
      const privateReads=calls.filter(p=>p.includes('project')).length;
      await page.goto(OFFICIAL+'/?signin=1#type=recovery&refresh_token=fixture-email-refresh');
      await page.locator('#lgPasswordConfirm').waitFor({state:'visible'});
      assert.equal(new URL(page.url()).hash,'','the recovery fragment is cleared immediately');
      assert.equal(await page.locator('#designWorkspace').isVisible(),false);
      await page.reload();
      await page.locator('#lgPasswordConfirm').waitFor({state:'visible'});
      await page.locator('#lgPassword').fill('fixture-new-password');
      await page.locator('#lgPasswordConfirm').fill('fixture-new-password');
      await page.locator('#lgGo').click();
      await page.waitForFunction(()=>document.querySelector('#acsAuthStatus').textContent.includes('تم تغيير كلمة المرور'));
      assert.equal(calls.filter(p=>p==='/v1/auth/update-password').length,1);
      assert.equal(calls.filter(p=>p.includes('project')).length,privateReads,'recovery never opens a project');
      assert.equal(await page.evaluate(()=>localStorage.getItem('acs_supabase_session_v1')),null);
      assert.deepEqual(errors,[]);
      fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
      await page.screenshot({path:path.join(ROOT,'logs','auth-'+width+'.png')});
      // A Netlify branch copy of the site. The backend refuses its origin, as it
      // refused the owner's iPhone, so sign-in must lead to the official site
      // instead of failing as a connection error. Guest entry stays as it was.
      const target=OFFICIAL+'/?signin=1&example=apartment-20x25';
      const notice=page.locator('#acsAuthOfficial'),officialLink=page.locator('#acsAuthOfficialLink');
      await page.goto(PREVIEW+'/?signin=1&example=apartment-20x25&code=11111111-1111-4111-8111-111111111111');
      await notice.waitFor({state:'visible'});
      assert.match(await notice.innerText(),/نسخة معاينة.*الموقع الرسمي/s);
      assert.equal(await officialLink.textContent(),'الانتقال إلى الموقع الرسمي');
      assert.equal(await officialLink.getAttribute('href'),target,'same path and harmless parameters, never the OAuth code');
      assert.equal(new URL(page.url()).searchParams.has('code'),false);
      assert.equal(await page.locator('#acsAuthStatus').textContent(),'','the notice is not an error');
      assert.equal(await page.locator('#login').evaluate(el=>el.classList.contains('auth-outage')),false);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      const linkBox=await officialLink.boundingBox(),noticeBox=await notice.boundingBox(),googleTop=(await page.locator('#acsAuthGoogle').boundingBox()).y;
      assert.ok(linkBox.height>=44&&noticeBox.y+noticeBox.height<=googleTop,'the official-site action is a full target above the account buttons');
      await page.screenshot({path:path.join(ROOT,'logs','auth-preview-'+width+'.png'),mask:[page.locator('input')]});
      await Promise.all([page.waitForURL(target),page.getByRole('button',{name:'المتابعة باستخدام Google'}).click()]);
      await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
      assert.equal(await notice.isVisible(),false,'the official site opens its normal sign-in');
      for(const signup of [false,true]){
        await page.goto(PREVIEW+'/?signin=1&example=apartment-20x25');await notice.waitFor({state:'visible'});
        if(signup)await page.locator('#lgSignup').click();
        await page.locator('#lgEmail').fill('fixture@example.test');await page.locator('#lgPassword').fill('fixture-password');
        await Promise.all([page.waitForURL(target),page.locator('#lgGo').click()]);
        assert.equal(await page.locator('#lgPassword').inputValue(),'','nothing typed on the copy travels');
      }
      assert.deepEqual(backendRefused,[],'the preview copy sends no account request for the backend to refuse');
      await page.goto(PREVIEW+'/?signin=1&example=apartment-20x25');await notice.waitFor({state:'visible'});
      await Promise.all([page.waitForURL(PREVIEW+'/?guest=1&example=apartment-20x25'),page.locator('#acsAuthGuestLink').click()]);
      await page.waitForFunction(()=>window.ACS?.guest===true&&window.ACS.guestWorkspaceReady===true);
      assert.equal(await notice.isVisible(),false);
      assert.deepEqual(backendRefused,[]);
      assert.deepEqual(errors,[]);
      console.log('PASS shipped auth '+width+': email entry, project onboarding, Google PKCE redirect, reload, cross-tab logout, password recovery and preview-copy handoff to the official site');
      }catch(error){
        fs.mkdirSync(path.join(ROOT,'logs'),{recursive:true});
        const visible=await page.evaluate(()=>Object.fromEntries(['acsAuthStatus','acsAuthOfficial','cwStatus'].map(id=>{
          const el=document.getElementById(id),rect=el?.getBoundingClientRect(),style=el&&getComputedStyle(el);
          return [id,{visible:!!rect&&rect.width>0&&rect.height>0&&style.visibility!=='hidden'&&style.display!=='none',text:el?.textContent?.slice(0,300)||''}];
        }))).catch(()=>({unavailable:true}));
        const message=String(error.message||'').split('\n')[0]
          .replace(/https?:\/\/[^\s]+/g,value=>{try{const url=new URL(value);return url.origin+url.pathname;}catch{return '[url]';}})
          .replace(/(?:Bearer\s+|(?:access_token|refresh_token|code_verifier|password)\s*[:=]\s*)\S+/gi,'[redacted]')
          .slice(0,500);
        const diagnostic={width,error_type:error.name,error_message:message,visible,endpoint_paths:[...new Set(calls)],local_modules:localModules,
          refused_by_backend_cors:backendRefused.map(entry=>entry.replace(/ from .*/,''))};
        fs.writeFileSync(path.join(ROOT,'logs','auth-failure-'+width+'.json'),JSON.stringify(diagnostic,null,2));
        await page.screenshot({path:path.join(ROOT,'logs','auth-failure-'+width+'.png'),mask:[page.locator('input')]}).catch(()=>{});
        console.error('AUTH FIXTURE DIAGNOSTIC',JSON.stringify(diagnostic));
        throw error;
      }finally{await context.close();}
    }
  }finally{await browser.close();}
  await require('./test_guest_workspace.cjs').runGuestWorkspaceTests();
}
module.exports={sourceResponse,workspaceEntered};
if(require.main===module)runAuthShippedPage().catch(e=>{console.error(e);process.exitCode=1;});
