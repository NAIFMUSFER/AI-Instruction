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
async function guestSnapshot(page){
 return page.evaluate(()=>new Promise((resolve,reject)=>{
  const open=indexedDB.open('acs_guest_project_v1',2);
  open.onerror=()=>reject(open.error);
  open.onsuccess=()=>{
   const db=open.result,tx=db.transaction(['records','meta'],'readonly');
   let records=[],pointer=null;
   tx.objectStore('records').getAll().onsuccess=e=>{records=e.target.result;};
   tx.objectStore('meta').get('pointer').onsuccess=e=>{pointer=e.target.result;};
   tx.oncomplete=()=>{db.close();resolve({pointer,records:records.sort((a,b)=>a.record_id.localeCompare(b.record_id))});};
   tx.onerror=()=>{db.close();reject(tx.error);};
  };
 }));
}
// Local JSON export adds only absent stable instance identifiers and explicit
// fallback elevations. Predict that documented contract without calling exporter
// code, retaining all supplied dimensions, room IDs, heights and object data.
function normalizedLocalModel(model){
 const result=JSON.parse(JSON.stringify(model));
 const height=Number(result.floor_height||((Number(result.wall_h)||3)+.2));
 for(const level of result.levels||[]){
  const index=Number(level.index||0);
  if(level.id==null)level.id='bld_0.flr_'+index;
  if(level.elevation==null)level.elevation=Number((index*height).toFixed(3));
 }
 for(const [template,floor] of Object.entries(result.floors||{})){
  (floor.rooms||[]).forEach((room,index)=>{
   if(room.space_id==null)room.space_id='bld_0.'+template+'.'+(room.id||('sp_'+index));
  });
 }
 return result;
}
async function downloadedJSON(page,button){
 const event=page.waitForEvent('download',{timeout:15000});
 await page.locator(button).click();
 const download=await event;
 assert.match(download.suggestedFilename(),/\.json$/i);
 assert.equal(await download.failure(),null);
 const stream=await download.createReadStream();
 assert.ok(stream,'download must contain a real readable file');
 const parts=[];for await(const part of stream)parts.push(part);
 return JSON.parse(Buffer.concat(parts).toString('utf8'));
}
async function runGuestWorkspaceTests(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const width of [393,1280]){
   const context=await browser.newContext({viewport:{width,height:852},acceptDownloads:true});
   context.setDefaultTimeout(15000);
   const page=await context.newPage(),calls=[],errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{
    window.__guestAuthEvents=0;
    document.addEventListener('acs:authenticated',()=>window.__guestAuthEvents++);
   });
   await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==ORIGIN||/^\/(?:v1|auth|rest|functions)(?:\/|$)/.test(url.pathname)){calls.push(url.pathname);return route.abort();}
    const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
   });
   await page.goto(ORIGIN+'/');
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete');
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
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.site.w===24);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/استُعيد/);
   // Local file inputs and downloads exercise the actual handlers and bytes.
   // This fixture is synthetic; no real account files or credentials are read.
   const originalModel=await page.evaluate(()=>window.ACS.exportModel());
   const importedModel=JSON.parse(JSON.stringify(originalModel));
   importedModel.site.w=23;importedModel.meta={...importedModel.meta,name:'guest-import-'+width};
   importedModel.levels[0].id='explicit-guest-level';importedModel.levels[0].elevation=.45;
   const firstTemplate=importedModel.levels[0].template;
   importedModel.floors[firstTemplate].rooms[0].space_id='explicit-guest-space';
   await page.locator('#impFile').setInputFiles({name:'synthetic-building.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(importedModel))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===23&&document.getElementById('impInfo').textContent.includes('JSON ✓'));
   const importedVisible=await page.evaluate(()=>window.ACS.exportModel());
   assert.deepEqual(importedVisible.floors,importedModel.floors);
   assert.deepEqual(importedVisible.levels,importedModel.levels);
   await page.locator('#guestCreate').click();
   await page.locator('#acsTabShow').click();
   const exported=await downloadedJSON(page,'#bJson');
   const normalized=normalizedLocalModel(importedVisible);
   assert.deepEqual(exported.site,normalized.site);
   assert.deepEqual(exported.levels,normalized.levels,'export may only add the declared missing level IDs/elevations');
   assert.deepEqual(exported.floors,normalized.floors,'all room geometry, object data and explicit IDs must survive export');
   assert.equal(exported.levels[0].id,'explicit-guest-level');
   assert.equal(exported.levels[0].elevation,.45);
   assert.equal(exported.floors[firstTemplate].rooms[0].space_id,'explicit-guest-space');
   assert.equal(exported.meta.name,'guest-import-'+width);
   // Reimport the downloaded envelope, preserving the normalized canonical
   // dimensions/identities rather than comparing with the pre-export raw form.
   await page.locator('#impFile').setInputFiles({name:'download-roundtrip.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(exported))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.schema==='acs.project/1'&&document.getElementById('impInfo').textContent.includes('JSON ✓'));
   const roundtrip=await page.evaluate(()=>window.ACS.exportModel());
   assert.deepEqual(roundtrip.levels,normalized.levels);
   assert.deepEqual(roundtrip.floors,normalized.floors);
   assert.deepEqual(roundtrip.site,normalized.site);
   // Input accept filters are not enforcement: intentionally submit a PDF.
   await page.locator('#impFile').setInputFiles({name:'unsupported.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 synthetic unsupported guest fixture')});
   await page.waitForFunction(()=>document.getElementById('impInfo').textContent.includes('سجّل الدخول'));
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),roundtrip,'unsupported guest import must preserve the visible model');
   assert.deepEqual(calls,[],'local import and download must not call private/provider services');
   // Return to the saved24m fixture used by the delayed-recovery assertions.
   await page.locator('#impFile').setInputFiles({name:'restored-local.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(originalModel))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===24);
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_IMPORT_TEST'))).ok,true);
   if(width===1280){
    // A second real tab shares only the guest draft namespace. Its visible
    // sample choice must not overwrite the first tab's in-memory project.
    const second=await context.newPage();second.on('pageerror',e=>errors.push(e.message));
    await second.goto(ORIGIN+'/?guest=1');
    await second.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
    assert.equal(await second.evaluate(()=>window.ACS.exportModel().site.w),24);
    await page.waitForFunction(()=>window.ACS.tabs().owner.tabs>=2);
    await second.waitForFunction(()=>window.ACS.tabs().owner.tabs>=2);
    assert.notEqual(await second.evaluate(()=>window.ACS.tabs().self),await page.evaluate(()=>window.ACS.tabs().self));
    assert.equal(await second.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
    await second.locator('#guestWarehouse').click();
    await second.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
    assert.equal(await page.evaluate(()=>window.ACS.exportModel().site.w),24,'a sample selected in another guest tab must not replace this visible project');
    assert.equal(await second.evaluate(()=>window.ACS.authSession),undefined);
    assert.equal(await second.evaluate(()=>window.ACS.projectId),undefined);
    await second.close();
    // Restore the explicit current draft after closing the second tab; shared
    // guest persistence is disclosed, not claimed to be a private per-tab DB.
    assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_AFTER_TWO_TABS'))).ok,true);
    const existing=await guestSnapshot(page);
    const denied=await context.newPage();denied.on('pageerror',e=>errors.push(e.message));
    await denied.addInitScript(()=>{
     window.__guestDeniedStorageAttempts=0;
     IDBFactory.prototype.open=function(){window.__guestDeniedStorageAttempts++;throw new DOMException('Synthetic storage denial','SecurityError');};
    });
    await denied.goto(ORIGIN+'/?guest=1');
    await denied.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
    assert.ok(await denied.evaluate(()=>window.__guestDeniedStorageAttempts>0));
    assert.equal(await denied.locator('#login').isVisible(),false);
    assert.ok(await denied.evaluate(()=>window.ACS.exportModel()?.floors));
    assert.match(await denied.locator('#acsGuestStatus').textContent(),/تنزيل JSON/);
    assert.equal(await denied.evaluate(()=>window.ACS.guestAutosaveReady),false);
    await denied.locator('#guestCreate').click();await denied.locator('#acsTabShow').click();
    await denied.locator('#acsSaveNow').click();
    await denied.waitForFunction(()=>document.getElementById('acsSaveState').dataset.acsSave==='FAILED');
    assert.notEqual(await denied.locator('#acsSaveState').getAttribute('data-acs-save'),'SAVED');
    const deniedModel=await denied.evaluate(()=>window.ACS.exportModel());
    const backup=await downloadedJSON(denied,'#acsExportBackup');
    assert.equal(backup.contract,'acs-project-backup/1');
    assert.equal(backup.storage,'LOCAL_FILE_DOWNLOAD');
    assert.deepEqual(JSON.parse(backup.record.payload).model,deniedModel,'storage denial still allows an exact local backup download');
    await denied.close();
    const afterDenied=await guestSnapshot(page);
    const originalRecord=existing.records.find(record=>record.record_id===existing.pointer);
    assert.ok(originalRecord,'a real prior guest snapshot exists before denial');
    assert.deepEqual(afterDenied.records.find(record=>record.record_id===existing.pointer),originalRecord,'failed recovery/save must preserve the original guest record');
    assert.deepEqual(calls,[],'two tabs and denied storage must never invoke identity/private/provider requests');
   }
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
       api.recover=()=>{
        const result=original();result.then(()=>{window.__guestRecoveryReadDone=true;});
        return new Promise(resolve=>{window.__releaseGuestRecovery=()=>result.then(resolve);});
       };
      }
     }});
    }});
   });
   // Cross the UI's slow-read notice without releasing the genuine IndexedDB
   // result. This used to discard recovery and autosave the temporary sample.
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.__guestRecoveryReadDone);
   const beforeSlowRecovery=await guestSnapshot(page);
   assert.ok(beforeSlowRecovery.records.some(record=>JSON.parse(record.payload).model.site.w===24));
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recoveryStatus==='slow');
   assert.equal(await page.locator('#acsGuestBanner').getAttribute('data-recovery'),'pending');
   assert.notEqual(await page.evaluate(()=>window.ACS.exportModel().site.w),24,'a real temporary sample is visible while saved work is still loading');
   assert.deepEqual(await page.evaluate(()=>window.ACS.persistence.save('AUTOSAVE')),{ok:false,code:'RECOVERY_PENDING'});
   assert.deepEqual(await page.evaluate(()=>window.ACS.persistence.save('MANUAL')),{ok:false,code:'RECOVERY_PENDING'});
   await page.evaluate(()=>{
    Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});
    document.dispatchEvent(new Event('visibilitychange'));
    delete document.visibilityState;
   });
   assert.deepEqual(await guestSnapshot(page),beforeSlowRecovery,'pending recovery must preserve all saved records and the pointer');
   await page.evaluate(()=>window.__releaseGuestRecovery());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.site.w===24);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/استُعيد/);
   // A second slow read must not overwrite a new sample chosen by the visitor.
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.__guestRecoveryReadDone);
   await page.locator('#guestWarehouse').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
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
  // A real browser with WebGL deliberately unavailable must retain useful,
  // honest 2D content and navigation independently of the failed ESM graph.
  const noGl=await browser.newContext({viewport:{width:393,height:852}}),fallback=await noGl.newPage();
  const fallbackCalls=[];
  await fallback.addInitScript(()=>{
   const original=HTMLCanvasElement.prototype.getContext;
   HTMLCanvasElement.prototype.getContext=function(kind,...args){
    if(['webgl','webgl2','experimental-webgl'].includes(kind))return null;
    return original.call(this,kind,...args);
   };
  });
  await fallback.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.origin!==ORIGIN){fallbackCalls.push(url.pathname);return route.abort();}
   const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
   if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
   return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
  });
  await fallback.goto(ORIGIN+'/');
  await fallback.locator('#acsGuestFallback').waitFor({state:'visible'});
  await fallback.waitForFunction(()=>document.getElementById('acsGuestFallback')?.dataset.engineState==='unavailable');
  assert.equal(await fallback.locator('#acsGuestFallbackPlan rect').count(),4);
  assert.equal(await fallback.locator('#genLLM').isEnabled(),false);
  assert.equal(await fallback.locator('#impFile').isEnabled(),false);
  assert.equal(await fallback.locator('#acsGuestFallback').getAttribute('data-engine-state'),'unavailable');
  await fallback.locator('[data-guest-room]').first().click();
  assert.match(await fallback.locator('#acsGuestFallbackRoom').textContent(),/42/);
  assert.deepEqual(fallbackCalls,[]);
  assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await fallback.locator('#guestFallbackSignin').click();
  await fallback.locator('#acsAuthGoogle').waitFor({state:'visible'});
  assert.equal(new URL(fallback.url()).searchParams.get('signin'),'1');
  await noGl.close();passed++;
  console.log('GUEST WORKSPACE: '+passed+' production-origin journeys passed (desktop/mobile JSON import/download and unsupported files; two guest tabs; denied-storage backup; recovery; no-WebGL)');
 }finally{await browser.close();}
}
module.exports={runGuestWorkspaceTests};
if(require.main===module)runGuestWorkspaceTests().catch(e=>{console.error(e);process.exitCode=1;});
