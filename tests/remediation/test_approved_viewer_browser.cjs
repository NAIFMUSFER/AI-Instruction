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
const meta={scope:'synthetic exact approved artifacts; not live AI or physical mobile acceptance',budgets:{first_view_ms:3000,desktop_frame_p95_ms:20,mobile_frame_p95_ms:33,transition_timeout_ms:2000,idle_additional_render_calls:0},measurements:[]};
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
  assert.equal(baseline.modelHash,fixture.model_hash);
  const hardware=await page.evaluate(()=>{const gl=document.querySelector('#cwViewer canvas').getContext('webgl2');const ext=gl.getExtension('WEBGL_debug_renderer_info');return{browser:navigator.userAgent,cpuLogicalCores:navigator.hardwareConcurrency,webglVendor:ext?gl.getParameter(ext.UNMASKED_VENDOR_WEBGL):'unavailable',webglRenderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable',physicalDevice:'not available; desktop automation viewport'}});
  const views=[];
  for(const name of ['exterior','aerial','street','interior','cutaway','detail']){
   const intervalStart=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.frameIntervalsMs.length);
   const time=performance.now();await page.locator('[data-view="'+name+'"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);
   const transitionMs=performance.now()-time;assert.ok(transitionMs<meta.budgets.transition_timeout_ms);
   const stats=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.equal(stats.view,name);assert.equal(stats.modelHash,fixture.model_hash);assert.equal(stats.meshCount,baseline.meshCount);
   if(name==='detail'&&fixture.kind==='warehouse')assert.ok(stats.detailGroupSize>3,'rack detail must frame its actual assembly, not an isolated thin shelf');
   const fits=await page.evaluate(async()=>{const stats=document.querySelector('#cwViewer').acsViewer.inspect();if(!stats.framedBounds)return true;const THREE=await import('three');const camera=new THREE.PerspectiveCamera(stats.fov,stats.aspect,.001,10000);camera.position.fromArray(stats.camera);camera.lookAt(new THREE.Vector3().fromArray(stats.target));camera.updateMatrixWorld();return [0,1].every(i=>[0,1].every(j=>[0,1].every(k=>{const p=new THREE.Vector3(stats.framedBounds[i?'max':'min'][0],stats.framedBounds[j?'max':'min'][1],stats.framedBounds[k?'max':'min'][2]).project(camera);return Math.abs(p.x)<=.94&&Math.abs(p.y)<=.94;})));});
   assert.equal(fits,true,name+' bounds must fit the actual aspect ratio');
   const screenshot=fixture.kind+'-'+viewport.width+'-'+name+'.png';await page.locator('#cwViewer').screenshot({path:path.join(output,screenshot)});assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.frameIntervalsMs.length),stats.frameIntervalsMs.length,'idle screenshot time is excluded from active transition timing');
   views.push({view:name,transition_ms:transitionMs,active_frame_intervals_ms:stats.frameIntervalsMs.slice(intervalStart),stats,screenshot});
  }
  if(fixture.kind==='residential'){
   await page.locator('select[aria-label="الدور المعروض في 3D"]').selectOption('1');const after=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.ok(after.visibleMeshCount<baseline.meshCount&&after.visibleMeshCount>0,'floor isolation preserves selected physical level');
  }
  await page.locator('#cwViewer canvas').focus();const cameraBefore=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().camera);await page.keyboard.press('ArrowLeft');assert.notDeepEqual(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().camera),cameraBefore);
  const calls=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.renderCalls);await page.waitForTimeout(250);assert.equal(await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.renderCalls),calls,'no idle render loop');
  await page.evaluate(()=>document.querySelector('#cwViewer canvas').dispatchEvent(new Event('webglcontextlost',{cancelable:true})));
  assert.equal(await page.locator('#cwViewer canvas').count(),0);assert.ok((await page.evaluate(()=>window.contextLostMessage)).includes('فُقد'));
  await page.evaluate(()=>window.fixtureDispose());assert.equal(await page.locator('#cwViewer canvas').count(),0,'idempotent teardown');
  assert.deepEqual(errors,[]);const frameTimes=views.at(-1).stats.frameIntervalsMs.slice().sort((a,b)=>a-b),frameP95=frameTimes.length>=2?frameTimes[Math.ceil(frameTimes.length*.95)-1]:null;meta.measurements.push({frame_p95_ms:frameP95,frame_sample_count:frameTimes.length,frame_scope:'active preset transition callbacks only; no idle/screenshot gaps; CPU-submission timing is separate',targets_met:{first_view:firstMs<=meta.budgets.first_view_ms,frame_p95:frameP95!==null&&frameP95<=(viewport.width<500?meta.budgets.mobile_frame_p95_ms:meta.budgets.desktop_frame_p95_ms)},fixture:fixture.kind,revision:fixture.revision,model_hash:fixture.model_hash,viewport,hardware,first_view_ms:firstMs,views});await context.close();
 }
 fs.writeFileSync(path.join(output,'visual-evidence.json'),JSON.stringify(meta,null,2));console.log('PASS: two exact approved fixtures, six views each at desktop/mobile, identity, floor isolation, keyboard, idle rendering, context loss, disposal. Evidence: '+output);
}catch(error){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:error.message,completed_measurements:meta.measurements.length,scope:meta.scope},null,2));throw error;}finally{if(browser)await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
