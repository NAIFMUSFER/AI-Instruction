'use strict';
// Exact approved artifact renderer, real Three/WebGL, no synthetic replacement
// geometry. Full private-workspace flow is test_connected_workspace_browser.cjs.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const output=path.resolve(process.env.ACS_VISUAL_OUTPUT||path.join(os.tmpdir(),'acs-approved-visuals'));
fs.mkdirSync(output,{recursive:true});
execFileSync(process.env.PYTHON||'python',['tests/remediation/approved_viewer_fixtures.py',output],{cwd:ROOT,stdio:'inherit'});
const fixtures=JSON.parse(fs.readFileSync(path.join(output,'fixtures.json'),'utf8'));
const meta={scope:'synthetic exact approved artifacts; not live AI or physical mobile acceptance',budgets:{first_view_ms:3000,desktop_frame_p95_ms:20,mobile_frame_p95_ms:33,transition_timeout_ms:2000,transition_stall_ms:10000,idle_additional_render_calls:0},measurements:[]};
const html=`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/app/styles/connected-workspace.css"><script type="importmap">{"imports":{"three":"/vendor/three@0.160.0/build/three.module.js","three/addons/":"/vendor/three@0.160.0/examples/jsm/"}}</script></head><body><main id="designWorkspace"><h1>مراجعة عرض النسخة المعتمدة</h1><p>حالة اختبار صناعية ثابتة — ليست توليدًا بالذكاء</p><div id="cwViewer"></div></main></body></html>`;
(async()=>{let browser;try{
 browser=await PW.launch({headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 for(const viewport of [{width:1440,height:900},{width:393,height:852}])for(const fixture of fixtures){
  const context=await browser.newContext({viewport,reducedMotion:'no-preference'}),page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',route=>{
   const url=new URL(route.request().url());if(url.hostname!=='approved.test')return route.abort();
   if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:html});
   let file=path.resolve(PUB,'.'+url.pathname);
   if(url.pathname.startsWith('/vendor/three@0.160.0/'))file=path.join(ROOT,'node_modules','three',url.pathname.slice('/vendor/three@0.160.0/'.length));
   if(!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
   return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(file)});
  });
  await page.goto('https://approved.test/');
  const bytes=[...fs.readFileSync(path.join(output,fixture.gltf))];
  const start=performance.now();
  await page.evaluate(async({bytes,revision})=>{const {showApprovedGLTF}=await import('/app/ui/approved-viewer.mjs');window.fixtureCurrent=true;window.fixtureDispose=await showApprovedGLTF(document.getElementById('cwViewer'),new Uint8Array(bytes),revision,{isCurrent:()=>window.fixtureCurrent,onFailure:message=>{document.getElementById('cwViewer').textContent=message;window.contextLostMessage=message;}});},{bytes,revision:fixture.revision});
  const firstMs=performance.now()-start;assert.ok(firstMs<15000,'first actual artifact view cannot stall beyond 15 seconds');
  await page.locator('#cwViewer canvas').waitFor({state:'visible'});
  assert.equal(await page.locator('#cwViewer').getAttribute('data-revision'),fixture.revision);
  assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false);
  const baseline=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.ok(baseline.meshCount>0&&baseline.triangleCount>0);
  assert.equal(baseline.modelHash,fixture.model_hash);assert.equal(baseline.lastFrame.mode,'settled');
  // Presentation layer: derived from the exact meshes, never added to them.
  assert.ok(baseline.presentation.edgeSegments>0&&baseline.presentation.roomLabels>0&&[1,5].includes(baseline.presentation.gridCellM));
  assert.equal(baseline.presentation.entranceDetected,true,'hero and street cameras face a real exterior door');
  // Dressing exists only for approved openings; the assumed roof and scale figures are disclosed as assumptions.
  assert.ok(baseline.presentation.detailInstances>0&&baseline.presentation.figures===2);
  const evidenceText=await page.locator('.av-evidence').textContent(),canonicalRoof=!!fixture.canonical_roof;assert.ok(evidenceText.includes('ليست دراسة شمسية'));
  // Canonical roof level: approved geometry, no assumed roof. No roof in the artifact: a disclosed, removable assumption.
  assert.equal(baseline.presentation.roofSource,canonicalRoof?'artifact':'assumed');assert.equal(baseline.presentation.roofInArtifact,canonicalRoof);
  assert.equal(baseline.presentation.roofPieces>0,!canonicalRoof);assert.ok(evidenceText.includes(canonicalRoof?'جزء من النسخة المعتمدة':'سقف افتراضي'));assert.equal(evidenceText.includes('لا يحتوي سقفًا'),!canonicalRoof);
  if(canonicalRoof)assert.ok(await page.locator('select[aria-label="الدور المعروض في 3D"] option',{hasText:'السطح'}).count()===1,'the roof level is named, not numbered as a storey');
  const hardware=await page.evaluate(()=>{const gl=document.querySelector('#cwViewer canvas').getContext('webgl2');const ext=gl.getExtension('WEBGL_debug_renderer_info');return{browser:navigator.userAgent,cpuLogicalCores:navigator.hardwareConcurrency,webglVendor:ext?gl.getParameter(ext.UNMASKED_VENDOR_WEBGL):'unavailable',webglRenderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable',physicalDevice:'not available; desktop automation viewport'}});
  const views=[];
  for(const name of ['exterior','aerial','street','interior','cutaway','detail']){
   const intervalStart=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.frameIntervalsMs.length);
   const time=performance.now();await page.locator('[data-view="'+name+'"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
   const transitionMs=performance.now()-time;
   // The 2 s budget is enforced on the CI runner class (4+ logical cores). A weaker
   // host still fails on a stall, and its measurement is recorded as a missed target.
   assert.ok(transitionMs<(hardware.cpuLogicalCores>=4?meta.budgets.transition_timeout_ms:meta.budgets.transition_stall_ms),'view transition '+name+' took '+Math.round(transitionMs)+' ms');
   const stats=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.equal(stats.lastFrame.mode,'settled');assert.equal(stats.view,name);assert.equal(stats.modelHash,fixture.model_hash);assert.equal(stats.meshCount,baseline.meshCount);assert.equal(stats.triangleCount,baseline.triangleCount,'presentation never changes approved triangles');assert.equal(stats.presentation.clippingPlanes,1,'cutaway never changes the compiled clipping-plane count');
   const shownLabels=await page.locator('.av-label:not([hidden])').count();if(['aerial','cutaway'].includes(name))assert.ok(shownLabels>0,'room names are visible in plan-like views');if(['street','interior','detail'].includes(name))assert.equal(shownLabels,0,'room names do not float over eye-level views');
   assert.equal(stats.presentation.roofShown,canonicalRoof&&!['aerial','cutaway'].includes(name),'initial view only shows roofs present in the artifact');
   const fits=await page.evaluate(async()=>{const stats=document.querySelector('#cwViewer').acsViewer.inspect();if(!stats.framedBounds)return true;const THREE=await import('three');const camera=new THREE.PerspectiveCamera(stats.fov,stats.aspect,.001,10000);camera.position.fromArray(stats.camera);camera.lookAt(new THREE.Vector3().fromArray(stats.target));camera.updateMatrixWorld();return [0,1].every(i=>[0,1].every(j=>[0,1].every(k=>{const p=new THREE.Vector3(stats.framedBounds[i?'max':'min'][0],stats.framedBounds[j?'max':'min'][1],stats.framedBounds[k?'max':'min'][2]).project(camera);return Math.abs(p.x)<=.94&&Math.abs(p.y)<=.94;})));});
   assert.equal(fits,true,name+' bounds must fit the actual aspect ratio');
   const screenshot=fixture.kind+'-'+viewport.width+'-'+name+'.png';await page.locator('#cwViewer').screenshot({path:path.join(output,screenshot)});assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.frameIntervalsMs.length),stats.frameIntervalsMs.length,'idle screenshot time is excluded from active transition timing');
   views.push({view:name,transition_ms:transitionMs,active_frame_intervals_ms:stats.frameIntervalsMs.slice(intervalStart),stats,screenshot});
  }
  await page.locator('[data-view="aerial"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
  await page.locator('.av-more summary').click();
  const wallMode=page.getByRole('combobox',{name:'ألوان الجدران'});assert.equal(await wallMode.inputValue(),'assumed');
  assert.ok(baseline.presentation.eligibleWalls>0);
  for(const mode of ['source','assumed']){
   await wallMode.selectOption(mode);const changed=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());
   assert.equal(changed.presentation.wallFinish,mode);assert.equal(changed.modelHash,fixture.model_hash);
   assert.equal(changed.meshCount,baseline.meshCount);assert.equal(changed.triangleCount,baseline.triangleCount);
   assert.deepEqual(changed.objectGroups,baseline.objectGroups);assert.deepEqual(changed.rackGroups,baseline.rackGroups);
  }
  const labelToggle=page.getByRole('button',{name:'أسماء الفراغات'});await labelToggle.click();assert.equal(await page.locator('.av-label:not([hidden])').count(),0);assert.equal(await labelToggle.getAttribute('aria-pressed'),'false');await labelToggle.click();assert.ok(await page.locator('.av-label:not([hidden])').count()>0);
  if(fixture.kind==='warehouse'){
   const rack=baseline.rackGroups.find(group=>group.meshCount>3);assert.ok(rack,'fixture contains a complete derived rack assembly');
   const point=await page.evaluate(async center=>{const stats=document.querySelector('#cwViewer').acsViewer.inspect(),THREE=await import('three'),camera=new THREE.PerspectiveCamera(stats.fov,stats.aspect,.001,10000);camera.position.fromArray(stats.camera);camera.lookAt(new THREE.Vector3().fromArray(stats.target));camera.updateMatrixWorld();const p=new THREE.Vector3().fromArray(center).project(camera),rect=document.querySelector('#cwViewer canvas').getBoundingClientRect();return{x:rect.x+(p.x+1)*rect.width/2,y:rect.y+(1-p.y)*rect.height/2};},rack.center);
   await page.mouse.click(point.x,point.y);await page.locator('[data-view="detail"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
   const picked=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.equal(picked.detailGroupSize,rack.meshCount,'picking a rack part and requesting detail frames its complete assembly');assert.equal(picked.meshCount,baseline.meshCount);assert.equal(picked.modelHash,fixture.model_hash);
  }
  // Assumed roof can be removed; sun control re-renders once; the tour stops on any view choice.
  await page.locator('[data-view="exterior"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
  const roofToggle=page.getByRole('button',{name:fixture.canonical_roof?'السطح':'سقف افتراضي',exact:true});await roofToggle.click();assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().presentation.roofShown),!canonicalRoof);await roofToggle.click();
  const finish=page.getByRole('button',{name:'تشطيب أرضية افتراضي · بلاط ٦٠ سم'});
  for(const on of [true,false]){
   await finish.click();const after=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());
   assert.equal(after.presentation.floorFinishShown,on);assert.equal(after.meshCount,baseline.meshCount);assert.equal(after.triangleCount,baseline.triangleCount);assert.equal(after.modelHash,fixture.model_hash);
  }
  const beforeSun=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.renderCalls);await page.locator('.av-more-body input[type=range]').fill('16');
  assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().presentation.sunHour),16);assert.ok(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.renderCalls)>beforeSun);
  await page.locator('.av-more-body input[type=range]').fill('10');
  const tourToggle=page.getByRole('button',{name:'جولة تلقائية'});await tourToggle.click();assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().presentation.tour),true);
  await page.locator('[data-view="aerial"]').click();assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().presentation.tour),false,'choosing a view ends the tour');await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
  assert.equal((await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect())).meshCount,baseline.meshCount,'toggles never change approved meshes');
  if(fixture.kind==='residential'){
   const floorSelector=page.locator('select[aria-label="الدور المعروض في 3D"]'),roofIndex=await floorSelector.locator('option').filter({hasText:/^السطح$/}).getAttribute('value');assert.ok(roofIndex,'canonical roof is explicitly selectable');
   for(const name of ['aerial','cutaway']){
    await page.locator('[data-view="'+name+'"]').click();await floorSelector.selectOption(roofIndex);await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
    const selectedRoof=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.ok(selectedRoof.presentation.visibleRoofMeshCount>0,'selected roof has actual visible geometry in '+name);assert.equal(selectedRoof.presentation.roofShown,true);assert.equal(selectedRoof.modelHash,fixture.model_hash);assert.equal(selectedRoof.meshCount,baseline.meshCount);
   }
   await page.getByRole('button',{name:'إعادة الضبط',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);assert.equal(await floorSelector.inputValue(),'all');
   await page.locator('[data-view="aerial"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
   const allFloors=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.equal(allFloors.presentation.visibleRoofMeshCount,0,'default all-floor aerial view hides the roof again');assert.equal(allFloors.presentation.roofShown,false);assert.equal(allFloors.modelHash,fixture.model_hash);assert.equal(allFloors.meshCount,baseline.meshCount);
   await page.locator('select[aria-label="الدور المعروض في 3D"]').selectOption('1');const after=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.ok(after.visibleMeshCount<baseline.meshCount&&after.visibleMeshCount>0,'floor isolation preserves selected physical level');
  }
  // Measure continuous input through the shipping keyboard/orbit handler. Every
  // timestamp is an actual RAF callback with a changed camera and rendered frame.
  // Stop on a stalled browser. Missed frame budgets remain visible in the report.
  await page.locator('[data-view="exterior"]').click();
  await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
  await page.locator('#cwViewer canvas').focus();
  const orbit=await page.evaluate(async()=>{
    const host=document.querySelector('#cwViewer'),viewer=host.acsViewer,canvas=host.querySelector('canvas');
    const intervals=[],renders=[],start=performance.now();
    return new Promise((resolve,reject)=>{
      let previous=null,pending=null,frame;
      const watchdog=setTimeout(()=>{cancelAnimationFrame(frame);reject(new Error('interactive orbit did not complete in 20 seconds'));},20000);
      function step(timestamp){
        if(pending){
          const current=viewer.inspect();
          // This callback follows the application's queued frame for the same input.
          if(viewer.renderCalls!==pending.calls+1||pending.camera.every((v,i)=>Math.abs(v-current.camera[i])<1e-9)){
            clearTimeout(watchdog);reject(new Error('orbit input did not change the camera and produce exactly one draw'));return;
          }
          renders.push({...current.lastFrame});
          if(previous!==null)intervals.push(timestamp-previous);
          previous=timestamp;
          if(intervals.length===24){
            clearTimeout(watchdog);resolve({intervals_ms:intervals,frames:renders,elapsed_ms:performance.now()-start,last_render_calls:viewer.renderCalls,input:'ArrowLeft via focused production canvas on consecutive rendered animation frames'});return;
          }
        }
        pending={calls:viewer.renderCalls,camera:viewer.inspect().camera};
        canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true,cancelable:true}));
        frame=requestAnimationFrame(step);
      }
      frame=requestAnimationFrame(step);
    });
  });
  const reduced=orbit.frames.some(f=>f.mode==='motion-preview');
  if(/swiftshader|llvmpipe|software|microsoft basic render/i.test(hardware.webglRenderer)){
    assert.ok(orbit.frames.every(f=>f.mode==='motion-preview'&&f.width*f.height<baseline.lastFrame.width*baseline.lastFrame.height));
  }
  await page.waitForFunction(()=>document.querySelector('#cwViewer').acsViewer.lastFrame.mode==='settled');
  const settled=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());
  assert.equal(settled.modelHash,baseline.modelHash);assert.equal(settled.triangleCount,baseline.triangleCount);assert.equal(settled.meshCount,baseline.meshCount);
  assert.equal(settled.lastFrame.width,baseline.lastFrame.width);assert.equal(settled.lastFrame.height,baseline.lastFrame.height);
  assert.equal(settled.renderCalls,orbit.last_render_calls+(reduced?1:0),'restore settled quality once after preview input');
  orbit.settled_frame=settled.lastFrame;orbit.restore_draws=settled.renderCalls-orbit.last_render_calls;
  const calls=settled.renderCalls;await page.waitForTimeout(300);assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.renderCalls),calls,'no idle render loop after restoration');
  await page.evaluate(()=>document.querySelector('#cwViewer canvas').dispatchEvent(new Event('webglcontextlost',{cancelable:true})));
  assert.equal(await page.locator('#cwViewer canvas').count(),0);assert.ok((await page.evaluate(()=>window.contextLostMessage)).includes('فُقد'));
  await page.evaluate(()=>window.fixtureDispose());assert.equal(await page.locator('#cwViewer canvas').count(),0,'idempotent teardown');
  assert.deepEqual(errors,[]);const frameTimes=orbit.intervals_ms.slice().sort((a,b)=>a-b),frameP95=frameTimes[Math.ceil(frameTimes.length*.95)-1];assert.equal(frameTimes.length,24);assert.ok(frameP95>0);meta.measurements.push({frame_p95_ms:frameP95,frame_sample_count:frameTimes.length,frame_scope:'consecutive rendered interactive orbit frames; excludes idle/screenshot gaps and preset transitions; excludes scan-out measurement',interactive_orbit:orbit,transition_frame_intervals_ms:views.flatMap(view=>view.active_frame_intervals_ms),idle_additional_render_calls:0,targets_met:{first_view:firstMs<=meta.budgets.first_view_ms,transitions:views.every(view=>view.transition_ms<=meta.budgets.transition_timeout_ms),frame_p95:frameP95<=(viewport.width<500?meta.budgets.mobile_frame_p95_ms:meta.budgets.desktop_frame_p95_ms),navigation_30fps:frameP95<=1000/30},fixture:fixture.kind,revision:fixture.revision,model_hash:fixture.model_hash,viewport,hardware,first_view_ms:firstMs,views});await context.close();
 }
 fs.writeFileSync(path.join(output,'visual-evidence.json'),JSON.stringify(meta,null,2));console.log('PASS: two exact approved fixtures, six views each at desktop/mobile, identity, floor isolation, keyboard, idle rendering, context loss, disposal. Evidence: '+output);
}catch(error){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:error.message,completed_measurements:meta.measurements.length,scope:meta.scope},null,2));throw error;}finally{if(browser)await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
