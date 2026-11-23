'use strict';
// Actual approved artifact and shipped viewer. No injected scene, altered mesh,
// custom approval verifier or navigation/walkability claim.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process'),PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const output=path.resolve(process.env.ACS_STAIRS_VISUAL_OUTPUT||path.join(os.tmpdir(),'acs-stairs-visuals'));
fs.mkdirSync(output,{recursive:true});
execFileSync(process.env.PYTHON||'python',['tests/remediation/stairs_delivery_fixture.py',output],{cwd:ROOT,stdio:'inherit'});
const fixture=JSON.parse(fs.readFileSync(path.join(output,'stairs-fixture.json')));
const bytes=fs.readFileSync(path.join(output,fixture.gltf));
const decoded=JSON.parse(execFileSync('node',['tests/remediation/stairs_gltf_reader.mjs',path.join(output,fixture.gltf)],{cwd:ROOT,encoding:'utf8'}));
const components=decoded.meshes.filter(mesh=>mesh.extras.acs_stair);
assert.equal(components.length,17,'serialized artifact contains sixteen treads and one mid landing');
const selected=components.find(mesh=>mesh.extras.acs_stair.component_id==='f2_t08');
assert.ok(selected);const pickPoint=[0,1,2].map(k=>k===1?Math.max(...selected.vertices.map(v=>v[k])):(Math.min(...selected.vertices.map(v=>v[k]))+Math.max(...selected.vertices.map(v=>v[k])))/2);
const html=`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/app/styles/connected-workspace.css"><script type="importmap">{"imports":{"three":"/vendor/three@0.160.0/build/three.module.js","three/addons/":"/vendor/three@0.160.0/examples/jsm/"}}</script></head><body><main id="designWorkspace"><h1>درج تجريبي من النسخة المعتمدة</h1><p>حالة اصطناعية ثابتة؛ السير والدرابزين والخلوص والمطابقة الهندسية غير متحققة.</p><div id="cwViewer"></div></main></body></html>`;
const evidence={scope:'synthetic exact approved stair artifact; no provider call or physical mobile test',physical_traversal:'NOT_VERIFIED',fixture,
  limitations:['no guard, headroom, structure, accessibility or code verification','cutaway is a horizontal view of one level, not a section through both complete flights and upper slab','detail selects one actual tread; stair assembly grouping is unsupported'],
  budgets:{first_view_target_ms:3000,first_view_stall_ms:15000,preset_target_ms:2000,preset_stall_ms:10000,desktop_frame_p95_target_ms:20,mobile_frame_p95_target_ms:33},measurements:[]};
const stats=page=>page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());
const settle=page=>page.waitForFunction(()=>document.querySelector('#cwViewer')?.acsViewer&&!document.querySelector('#cwViewer').acsViewer.activeAnimation,null,{timeout:10000});
(async()=>{let browser,page;try{
  browser=await PW.launch({headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
  for(const viewport of [{width:1440,height:900},{width:393,height:852}]){
    const context=await browser.newContext({viewport,reducedMotion:'no-preference'});page=await context.newPage();const errors=[],attempted=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/*',route=>{
      const url=new URL(route.request().url());attempted.push(url.hostname+url.pathname);
      if(url.hostname!=='stairs.test')return route.abort();
      if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:html});
      let file=path.resolve(PUB,'.'+url.pathname);
      if(url.pathname.startsWith('/vendor/three@0.160.0/'))file=path.join(ROOT,'node_modules/three',url.pathname.slice('/vendor/three@0.160.0/'.length));
      if(!file.startsWith(PUB+path.sep)&&!file.startsWith(path.join(ROOT,'node_modules/three')+path.sep))return route.abort();
      if(!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
      return route.fulfill({contentType:file.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(file)});
    });
    await page.goto('https://stairs.test/');const start=performance.now();
    await page.evaluate(async({bytes,revision})=>{const {showApprovedGLTF}=await import('/app/ui/approved-viewer.mjs');window.currentFixture=true;window.disposeFixture=await showApprovedGLTF(document.querySelector('#cwViewer'),new Uint8Array(bytes),revision,{isCurrent:()=>window.currentFixture,onFailure:message=>{window.fixtureFailure=message;}});},{bytes:[...bytes],revision:fixture.revision});
    const firstViewMs=performance.now()-start;assert.ok(firstViewMs<evidence.budgets.first_view_stall_ms,'actual stair artifact first view must finish');
    const baseline=await stats(page);assert.equal(baseline.revisionId,fixture.revision);assert.equal(baseline.modelHash,fixture.model_hash);
    assert.equal(baseline.meshCount,decoded.meshes.length);assert.equal(baseline.triangleCount,decoded.meshes.reduce((sum,m)=>sum+m.indices.length/3,0));
    assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false,'controls must fit the viewport');
    const hardware=await page.evaluate(()=>{const gl=document.querySelector('#cwViewer canvas').getContext('webgl2'),ext=gl.getExtension('WEBGL_debug_renderer_info');return{browser:navigator.userAgent,cpuLogicalCores:navigator.hardwareConcurrency,webglRenderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable',physicalDevice:'unavailable; desktop browser viewport emulation'};});
    const floor=page.locator('select[aria-label="الدور المعروض في 3D"]'),views=[];
    for(const name of ['exterior','aerial','street','interior','cutaway','detail']){
      const floorValue=['aerial','interior','cutaway','detail'].includes(name)?'0':'all';
      await floor.selectOption(floorValue);await settle(page);
      if(name==='detail'){
        await page.locator('[data-view="aerial"]').click();await settle(page);
        const point=await page.evaluate(async center=>{const s=document.querySelector('#cwViewer').acsViewer.inspect(),THREE=await import('three'),camera=new THREE.PerspectiveCamera(s.fov,s.aspect,.001,10000);camera.position.fromArray(s.camera);camera.lookAt(new THREE.Vector3().fromArray(s.target));camera.updateMatrixWorld();const p=new THREE.Vector3().fromArray(center).project(camera),rect=document.querySelector('#cwViewer canvas').getBoundingClientRect();return{x:rect.x+(p.x+1)*rect.width/2,y:rect.y+(1-p.y)*rect.height/2};},pickPoint);
        await page.mouse.click(point.x,point.y);
        await page.waitForFunction(identity=>document.querySelector('.av-inspector')?.textContent.includes(identity),selected.name,{timeout:5000});
      }
      const time=performance.now();await page.locator('[data-view="'+name+'"]').click();await settle(page);const transitionMs=performance.now()-time;
      assert.ok(transitionMs<(hardware.cpuLogicalCores>=4?2000:10000),'stair '+name+' preset exceeded its measured-device budget');
      const current=await stats(page);assert.equal(current.view,name);assert.equal(current.revisionId,fixture.revision);assert.equal(current.modelHash,fixture.model_hash);assert.equal(current.meshCount,baseline.meshCount);assert.equal(current.triangleCount,baseline.triangleCount);
      assert.equal(current.presentation.clippingPlanes,1,'no geometry replacement or clipping shader proliferation');
      if(name==='cutaway')assert.ok(current.framedBounds.max[1]<1.6,'lower-flight section actually cuts the model');
      if(name==='detail')assert.ok((await page.locator('.av-inspector').textContent()).includes(selected.name),'detail keeps actual canonical tread identity');
      const screenshot='stairs-'+viewport.width+'-'+name+'.png';await page.locator('#cwViewer').screenshot({path:path.join(output,screenshot)});
      views.push({view:name,floor:floorValue,transition_ms:transitionMs,stats:current,selected_component:name==='detail'?selected.name:null,screenshot});
    }
    // Extra view documents the upper slab opening and retained arrival strip.
    // It does not claim the lower flight remains visible while isolating floor1.
    await floor.selectOption('1');await page.locator('[data-view="cutaway"]').click();await settle(page);
    const arrival=await stats(page);assert.ok(arrival.visibleMeshCount>0&&arrival.visibleMeshCount<baseline.meshCount);assert.equal(arrival.modelHash,fixture.model_hash);
    const arrivalScreenshot='stairs-'+viewport.width+'-upper-arrival.png';await page.locator('#cwViewer').screenshot({path:path.join(output,arrivalScreenshot)});
    assert.deepEqual(errors,[]);assert.ok(attempted.every(url=>url.startsWith('stairs.test/')),'fixture must never request auth, private projects or providers');
    const intervals=views.at(-1).stats.frameIntervalsMs.slice().sort((a,b)=>a-b),p95=intervals.length>=2?intervals[Math.ceil(intervals.length*.95)-1]:null;
    evidence.measurements.push({viewport,hardware,revision:fixture.revision,model_hash:fixture.model_hash,first_view_ms:firstViewMs,quality:baseline.quality,frame_p95_ms:p95,frame_samples:intervals.length,frame_scope:'active preset transition callbacks only; not GPU completion or physical-device performance',targets_met:{first_view:firstViewMs<=3000,presets:views.every(v=>v.transition_ms<=2000),frame_p95:p95!==null&&p95<=(viewport.width<500?33:20)},views,upper_arrival:{stats:arrival,screenshot:arrivalScreenshot},physical_traversal:'NOT_VERIFIED'});
    await page.evaluate(()=>window.disposeFixture());assert.equal(await page.locator('#cwViewer canvas').count(),0);await context.close();page=null;
  }
  fs.writeFileSync(path.join(output,'stairs-visual-evidence.json'),JSON.stringify(evidence,null,2));
  console.log('PASS: exact approved stairs artifact, 12 preset images plus 2 upper-arrival images, actual tread selection and stable source/revision identity; traversal NOT_VERIFIED. '+output);
}catch(error){if(page)await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:error.message,completed:evidence.measurements,physical_traversal:'NOT_VERIFIED'},null,2));throw error;}finally{if(browser)await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
