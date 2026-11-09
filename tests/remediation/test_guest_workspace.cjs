'use strict';
// Exercise the shipped public page on a production-like HTTPS origin with strict
// CSP. Every backend request is intercepted and counted; no real user/provider.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const ORIGIN='https://acs-guest.test';
async function runGuestWorkspaceTests(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const width of [393,1280]){
   const context=await browser.newContext({viewport:{width,height:852},acceptDownloads:true});
   const page=await context.newPage(),calls=[],errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{
    window.__guestAuthEvents=0;
    document.addEventListener('acs:authenticated',()=>window.__guestAuthEvents++);
   });
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==ORIGIN){calls.push(url.pathname);return route.abort();}
    const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
   });
   await page.goto(ORIGIN+'/');
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   assert.equal(await page.locator('#login').isVisible(),false);
   assert.equal(await page.locator('#acsGuestBanner').isVisible(),true);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.evaluate(()=>window.__guestAuthEvents),0);
   assert.equal(await page.evaluate(()=>window.ACS.authSession),undefined);
   assert.equal(await page.evaluate(()=>window.ACS.projectId),undefined);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   if(width<=820)assert.equal(await page.locator('#panelToggle').getAttribute('aria-expanded'),'false');
   assert.equal(await page.locator('#genLLM').isEnabled(),false);
   assert.equal(await page.locator('#bNotesApply').isEnabled(),false);
   await page.locator('#guestWarehouse').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/تجريبي/);
   await page.locator('#guestCreate').click();
   await page.locator('#descText').fill('غرفة معيشة 5×4 ومطبخ 4×3 وغرفة نوم 4×4');
   await page.locator('#siteW').fill('24');await page.locator('#siteD').fill('18');await page.locator('#nFloors').fill('1');
   await page.locator('#genText').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===24);
   const saved=await page.evaluate(()=>window.ACS.persistence.save('GUEST_TEST'));
   assert.equal(saved.ok,true);
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel()?.site.w===24);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/استُعيد/);
   // Delay the real IndexedDB recovery result, then act before it completes.
   // This instruments only scheduling; the shipped page and saved data are real.
   await page.evaluate(()=>sessionStorage.setItem('acs_test_delay_guest_recovery','1'));
   await page.addInitScript(()=>{
    let current;const seen=new WeakSet();
    Object.defineProperty(window,'ACS',{configurable:true,get(){return current;},set(value){
     current=value;if(!value||typeof value!=='object'||seen.has(value))return;seen.add(value);
     let persistence;
     Object.defineProperty(value,'persistence',{configurable:true,get(){return persistence;},set(api){
      persistence=api;
      if(sessionStorage.getItem('acs_test_delay_guest_recovery')==='1'){
       const original=api.recover;
       api.recover=()=>{const result=original();return new Promise(resolve=>{window.__releaseGuestRecovery=()=>result.then(resolve);});};
      }
     }});
    }});
   });
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.__releaseGuestRecovery);
   await page.locator('#guestWarehouse').click();
   await page.evaluate(()=>window.__releaseGuestRecovery());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete');
   assert.equal(await page.evaluate(()=>window.ACS.exportModel().site.w),120,'a late recovery must not replace the visitor sample choice');
   await page.evaluate(()=>sessionStorage.removeItem('acs_test_delay_guest_recovery'));
   // Cloud auth helpers fail closed even if invoked outside the disabled UI.
   const guard=await page.evaluate(async()=>{
    let code;try{await ACS_AUTH.acsFetchJSON('/v1/auth/projects',{});}catch(e){code=e.code;}
    return {code,session:await ACS_AUTH.freshSession()};
   });
   assert.deepEqual(guard,{code:'GUEST_SIGNIN_REQUIRED',session:null});
   assert.deepEqual(calls,[],'guest must never request health/auth/private/provider services');
   assert.deepEqual(errors,[],'the actual shipped guest must boot without page errors');
   // A saved account is preserved but not read/used in explicit guest mode.
   const privateSession={access_token:'private-access',refresh_token:'private-refresh',expires_at:1,user:{id:'private-user'}};
   await page.evaluate(s=>{localStorage.setItem('acs_supabase_session_v1',JSON.stringify(s));localStorage.setItem('acs_project_v1',JSON.stringify({id:'private-project'}));localStorage.setItem('acs_password_recovery_v1','private-user');},privateSession);
   await page.addInitScript(()=>{
    const original=Storage.prototype.getItem;window.__guestCredentialReads=0;
    Storage.prototype.getItem=function(key){if(key==='acs_supabase_session_v1'||key==='acs_project_v1')window.__guestCredentialReads++;return original.call(this,key);};
   });
   await page.goto(ORIGIN+'/?guest=1');await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   assert.equal(await page.evaluate(()=>window.__guestCredentialReads),0);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.loadSession()),null);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   assert.deepEqual(calls,[]);
   const preserved=await page.evaluate(()=>JSON.parse(localStorage.getItem('acs_supabase_session_v1')));
   assert.deepEqual(preserved,privateSession);
   await page.evaluate(()=>{localStorage.removeItem('acs_supabase_session_v1');localStorage.removeItem('acs_project_v1');localStorage.removeItem('acs_password_recovery_v1');});
   await page.locator('#guestSignin').click();await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
   assert.equal(new URL(page.url()).searchParams.get('signin'),'1');
   assert.equal(await page.evaluate(()=>window.ACS.guest),false);
   assert.equal(await page.locator('#acsGuestBanner').count(),0);
   passed++;await context.close();
  }
  console.log('GUEST WORKSPACE: '+passed+' production-origin desktop/mobile journeys passed');
 }finally{await browser.close();}
}
module.exports={runGuestWorkspaceTests};
if(require.main===module)runGuestWorkspaceTests().catch(e=>{console.error(e);process.exitCode=1;});
