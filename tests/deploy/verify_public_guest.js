'use strict';
// Real deployed guest journey. Abort and count any forbidden network attempt so
// even a regression cannot invoke a private or paid endpoint during this monitor.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const PX=require('./lib_viewport_pixels.js');

async function run(target,{expectSha=process.env.ACS_VERIFY_EXPECT_SHA||""}={}){
 const browser=await PW.launch(),runs=[];
 const output=path.resolve(process.env.ACS_GUEST_OUTPUT||'logs/public-guest');fs.mkdirSync(output,{recursive:true});
 try{
  for(const width of [1440,393]){
   const context=await browser.newContext({viewport:{width,height:width===393?852:900},acceptDownloads:true});
   const page=await context.newPage(),forbidden=[],errors=[];let guest=true;
   page.on('pageerror',e=>errors.push(e.name));
   const origin=new URL(target).origin;
   await context.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(guest && (u.origin!==origin || /^\/v1\//.test(u.pathname) || /\/auth\/|\/rest\/|\/storage\//.test(u.pathname))){forbidden.push({method:route.request().method(),origin:u.origin,path:u.pathname});return route.abort();}
    return route.continue();
   });
   await page.goto(target,{waitUntil:'load',timeout:90000});
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel(),{},{timeout:45000});
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner')?.dataset.recovery==='complete');
   assert.equal(await page.locator('#login').isVisible(),false,'fresh entry has no blocking sign-in');
   assert.equal(await page.locator('#acsGuestBanner').isVisible(),true);
   assert.deepEqual(await page.evaluate(()=>({lang:document.documentElement.lang,dir:document.documentElement.dir})),{lang:'ar',dir:'rtl'});
   for(const selector of ['#guestExample','#guestWarehouse','#guestCreate','#guestSignin']){
    const box=await page.locator(selector).boundingBox();assert.ok(box&&box.height>=44&&box.width>=44,'primary touch control is at least 44 CSS pixels');
   }
   await page.locator('#guestWarehouse').focus();assert.equal(await page.evaluate(()=>document.activeElement.id),'guestWarehouse');
   assert.match(await page.locator('#acsGuestStatus').textContent(),/محلي|الجهاز|تجريبي/);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   assert.equal(await page.evaluate(()=>Boolean(ACS.authSession||ACS.projectId)),false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const views=[];
   for(const [kind,id] of [['residential','guestExample'],['warehouse','guestWarehouse']]){
    await page.locator('#'+id).click();
    await page.waitForFunction(()=>window.ACS?.renderDiagnosticsDetail?.().canonical_meshes>0);
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const diagnostics=await page.evaluate(()=>ACS.renderDiagnosticsDetail());
    assert.ok(diagnostics.model_bounds&&diagnostics.canonical_meshes>0,'sample must contain canonical geometry');
    const pixels=await PX.analysePageViewport(page,'canvas');
    assert.equal(pixels.verdict,'VISIBLE_CONTENT','real visible sample pixels required; 2D fallback is separate coverage');
    await page.screenshot({path:path.join(output,`${width}-${kind}.png`),fullPage:false});
    views.push({kind,canonical_meshes:diagnostics.canonical_meshes,pixels:pixels.verdict});
   }
   const saved=await page.evaluate(()=>ACS.persistence.save('PUBLIC_GUEST_MONITOR'));
   assert.equal(saved.ok,true);await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner')?.dataset.recovery==='complete'&&ACS.exportModel()?.site.w===120);
   // Open the normal project panel to make the existing download control visible.
   await page.evaluate(()=>ACS.setProjectPanelOpen?.(true));
   await page.locator('#acsTabShow').click();
   const downloadPromise=page.waitForEvent('download');
   await page.locator('#bJson').click();
   const download=await downloadPromise;assert.match(download.suggestedFilename(),/\.json$/i);
   assert.deepEqual(forbidden,[],'guest must make zero auth/private/provider requests');assert.deepEqual(errors,[]);
   const build=await page.evaluate(()=>window.ACS_BUILD_INFO||null);
   assert.match(build?.git_sha||'',/^[a-f0-9]{40}$/,'published build must have exact SHA provenance');
   if(expectSha)assert.equal(build.git_sha,expectSha);
   // Sign-in is a distinct journey. It may read public auth configuration; no
   // credentials are supplied and no account or private project is created.
   guest=false;await page.locator('#guestSignin').click();await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
   runs.push({width,height:width===393?852:900,views,build,guest_forbidden_requests:forbidden.length,local_save_reload:true,json_download:true,signin_ui:true});
   await context.close();
  }
  const evidence={schema:'acs-public-guest-monitor/1.0',target,browser:await browser.version(),device:'headless Chromium desktop; mobile viewport emulation',runs};
  fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(evidence,null,2));
  console.log('PUBLIC GUEST: PASS (real residential/warehouse pixels, isolated local save/reload/download, sign-in UI; zero guest private/provider requests).');
  return evidence;
 }finally{await browser.close();}
}
module.exports={run};
