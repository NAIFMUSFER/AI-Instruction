'use strict';
// Real deployed guest journey. Abort and count any forbidden network attempt so
// even a regression cannot invoke a private or paid endpoint during this monitor.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const PX=require('./lib_viewport_pixels.js');

// Only fixed stage names, viewport widths, elapsed milliseconds and an error
// class are persisted. Playwright errors can contain URLs or request details.
function progressRecorder(output){
 const progress={schema:'acs-public-guest-progress/1',status:'running',completed:[],active:null};
 let started=0;
 function flush(){
  const file=path.join(output,'progress.json');
  fs.writeFileSync(file+'.tmp',JSON.stringify(progress,null,2));fs.renameSync(file+'.tmp',file);
 }
 function complete(){
  if(progress.active)progress.completed.push({...progress.active,elapsed_ms:Math.round(performance.now()-started)});
  progress.active=null;
 }
 return {
  begin(stage,width=0){complete();progress.active={stage,width};started=performance.now();flush();},
  success(){complete();progress.status='passed';flush();},
  failure(error){
   progress.status='failed';
   progress.error=['TimeoutError','AssertionError','TypeError','Error'].includes(error?.name)?error.name:'Error';
   flush();
   const safe=new Error(progress.error+' at '+(progress.active?.stage||'unknown')+' ('+(progress.active?.width||0)+'px)');
   safe.name=progress.error;safe.guestProgress=progress;return safe;
  }
 };
}

async function openGuestOptions(page) {
 const options = page.locator('#guestOptions');
 // The earlier public release exposes the same sample and sign-in buttons inline.
 if (await options.count() && !await options.evaluate(element => element.open)) {
  await page.locator('#guestTools').click();
 }
}

async function assertTouchTargets(page, selectors) {
 for (const selector of selectors) {
  const box = await page.locator(selector).boundingBox();
  assert.ok(box && box.height>=44 && box.width>=44, selector+' is at least 44 CSS pixels');
 }
}

async function downloadProject(page,mobile,begin){
 const toggle=page.locator('#panelToggle');
 if(mobile){
  begin('open_project_sheet');
  assert.equal(await toggle.getAttribute('aria-expanded'),'false');
  await toggle.click();
  assert.equal(await toggle.getAttribute('aria-expanded'),'true');
 }
 begin('open_export_tab');await page.locator('#acsTabShow').click();
 begin('json_download');
 const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#bJson').click()]);
 assert.match(download.suggestedFilename(),/\.json$/i);
 assert.equal(await download.failure(),null);
 if(mobile){
  begin('close_project_sheet');
  await page.locator('#projectPanelClose').click();
  assert.equal(await toggle.getAttribute('aria-expanded'),'false');
 }
}

async function run(target,{expectSha=process.env.ACS_VERIFY_EXPECT_SHA||""}={}){
 let browser;const runs=[];
 const output=path.resolve(process.env.ACS_GUEST_OUTPUT||'logs/public-guest');fs.mkdirSync(output,{recursive:true});
 const progress=progressRecorder(output);
 try{
  progress.begin('browser_launch');browser=await PW.launch();
  for(const width of [1440,393]){
   const begin=stage=>progress.begin(stage,width);
   begin('fresh_context');const context=await browser.newContext({viewport:{width,height:width===393?852:900},acceptDownloads:true});
   context.setDefaultTimeout(30000);
   const page=await context.newPage(),forbidden=[],errors=[];let guest=true,signinChosen=false;
   page.on('pageerror',e=>errors.push(e.name));
   const origin=new URL(target).origin;
   page.on('framenavigated',frame=>{
    if(!signinChosen||frame!==page.mainFrame())return;
    const u=new URL(frame.url());
    if(u.origin===origin&&u.pathname==='/'&&u.searchParams.get('signin')==='1')guest=false;
   });
   await context.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(guest && (u.origin!==origin || /^\/v1\//.test(u.pathname) || /\/auth\/|\/rest\/|\/storage\//.test(u.pathname))){forbidden.push({method:route.request().method(),origin:u.origin,path:u.pathname});return route.abort();}
    return route.continue();
   });
   begin('public_navigation');await page.goto(target,{waitUntil:'load',timeout:90000});
   begin('guest_boot');await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel(),{},{timeout:45000});
   begin('local_recovery');await page.waitForFunction(()=>document.getElementById('acsGuestBanner')?.dataset.recovery==='complete');
   begin('guest_layout_and_isolation');assert.equal(await page.locator('#login').isVisible(),false,'fresh entry has no blocking sign-in');
   assert.equal(await page.locator('#acsGuestBanner').isVisible(),true);
   assert.deepEqual(await page.evaluate(()=>({lang:document.documentElement.lang,dir:document.documentElement.dir})),{lang:'ar',dir:'rtl'});
   if(await page.locator('#guestTools').count()){
    await assertTouchTargets(page,['#guestCreate','#guestPlan','#guestViewToggle','#guestTools']);
    if(width===393)assert.ok((await page.locator('#acsGuestBanner').boundingBox()).height<=80,'compact mobile guest toolbar');
    assert.equal(await page.locator('#guestSignin').isVisible(),false);
   }
   await openGuestOptions(page);
   await assertTouchTargets(page,['#guestExample','#guestWarehouse','#guestCreate','#guestSignin']);
   await page.locator('#guestWarehouse').focus();assert.equal(await page.evaluate(()=>document.activeElement.id),'guestWarehouse');
   assert.match(await page.locator('#acsGuestStatus').textContent(),/محلي|الجهاز|تجريبي/);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   assert.equal(await page.evaluate(()=>Boolean(ACS.authSession||ACS.projectId)),false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const views=[];
   for(const [kind,id] of [['residential','guestExample'],['warehouse','guestWarehouse']]){
    begin('select_'+kind);await openGuestOptions(page);await page.locator('#'+id).click();
    if(kind==='warehouse')await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
    await page.waitForFunction(()=>window.ACS?.renderDiagnosticsDetail?.().canonical_meshes>0);
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const diagnostics=await page.evaluate(()=>ACS.renderDiagnosticsDetail());
    assert.ok(diagnostics.model_bounds&&diagnostics.canonical_meshes>0,'sample must contain canonical geometry');
    begin('pixels_'+kind);const pixels=await PX.analysePageViewport(page,'canvas');
    assert.equal(pixels.verdict,'VISIBLE_CONTENT','real visible sample pixels required; 2D fallback is separate coverage');
    begin('capture_'+kind);await page.screenshot({path:path.join(output,`${width}-${kind}.png`),fullPage:false});
    views.push({kind,canonical_meshes:diagnostics.canonical_meshes,pixels:pixels.verdict});
   }
   begin('local_save');const saved=await page.evaluate(()=>ACS.persistence.save('PUBLIC_GUEST_MONITOR'));
   assert.equal(saved.ok,true);begin('reload_warehouse');await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner')?.dataset.recovery==='complete'&&ACS.exportModel()?.site.w===120);
   await downloadProject(page,width===393,begin);
   begin('verify_guest_requests_and_revision');
   assert.deepEqual(forbidden,[],'guest must make zero auth/private/provider requests');assert.deepEqual(errors,[]);
   const build=await page.evaluate(()=>window.ACS_BUILD_INFO||null);
   assert.match(build?.git_sha||'',/^[a-f0-9]{40}$/,'published build must have exact SHA provenance');
   if(expectSha)assert.equal(build.git_sha,expectSha);
   // Sign-in is a distinct journey. It may read public auth configuration; no
   // credentials are supplied and no account or private project is created.
   begin('open_signin');await openGuestOptions(page);signinChosen=true;await page.locator('#guestSignin').click();
   begin('signin_controls');await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
   assert.deepEqual(forbidden,[]);assert.equal(guest,false,'explicit sign-in must complete a distinct same-origin navigation');
   runs.push({width,height:width===393?852:900,views,build,guest_forbidden_requests:forbidden.length,local_save_reload:true,json_download:true,signin_ui:true});
   begin('close_verified_context');await context.close();
  }
  const evidence={schema:'acs-public-guest-monitor/1.0',target,browser:await browser.version(),device:'headless Chromium desktop; mobile viewport emulation',runs};
  progress.begin('write_complete_evidence');fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(evidence,null,2));
  progress.success();console.log('PUBLIC GUEST: PASS (real residential/warehouse pixels, isolated local save/reload/download, sign-in UI; zero guest private/provider requests).');
  return evidence;
 }catch(error){throw progress.failure(error);}finally{await browser?.close();}
}
module.exports={run,downloadProject,progressRecorder};
