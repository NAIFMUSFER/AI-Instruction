import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from 'three';

// Execute the actual startup settings against a controlled GL capability
// report. This is a configuration regression, not a claim of measured pixels
// or performance: CI's real SwiftShader guest journey supplies that evidence.
const sceneSource=fs.readFileSync('public/app/render/scene.js','utf8');
const wiringSource=fs.readFileSync('public/app/ui/workspace-ui-wiring.js','utf8');
const bridgeSource=fs.readFileSync('public/app/generated/pbr-bridge.js','utf8');
const startup=sceneSource.slice(sceneSource.indexOf("const app=document.getElementById('app')"),sceneSource.indexOf('const scene=new THREE.Scene();'))
  +sceneSource.slice(sceneSource.indexOf('const sun=new THREE.DirectionalLight('),sceneSource.indexOf('scene.add(sun);'));
function boot({label='ANGLE (Google, Vulkan (SwiftShader Device), SwiftShader driver)',masked='WebKit WebGL',extension=true,throwExtension=false,dpr=2}={}){
  let reads=0;
  const gl={RENDERER:1,getExtension(){if(throwExtension)throw new Error('restricted extension');return extension?{UNMASKED_RENDERER_WEBGL:2}:null;},getParameter(key){reads++;return key===2?label:masked;}};
  class Renderer{
    constructor({canvas}){this.domElement=canvas;this.shadowMap={};this.xr={};}
    getContext(){return gl;}
    setPixelRatio(value){this.ratio=value;}
    getPixelRatio(){return this.ratio;}
    setSize(w,h,updateStyle){this.size=[w,h,updateStyle];}
  }
  const context=vm.createContext({THREE:{...THREE,WebGLRenderer:Renderer},document:{getElementById(){return {appendChild(){}};},createElement(){return {}; }},devicePixelRatio:dpr,innerWidth:1280,innerHeight:900,window:{ACS:{}}});
  vm.runInContext(startup+';globalThis.result={renderer,sun};',context);
  return {context,...context.result,get reads(){return reads;}};
}
const software=boot();
assert.equal(software.renderer.getPixelRatio(),.75,'actual startup must bound software-renderer pixels before its first frame');
assert.equal(software.sun.shadow.mapSize.x,512,'actual startup must bound software shadow work before its first frame');
assert.deepEqual(Array.from(software.renderer.size),[1280,900,false],'CSS layout and viewport dimensions must remain unchanged');
assert.equal(software.renderer.xr.enabled,true,'capability-aware quality must preserve the XR route');
console.log('PASS: software startup reduces pixel/shadow work without changing viewport layout');

for(const label of ['llvmpipe (LLVM 19)','softpipe','Mesa swrast','Microsoft Basic Render Driver']){
  const run=boot({label,dpr:3});assert.equal(run.renderer.getPixelRatio(),.75,label);assert.equal(run.sun.shadow.mapSize.x,512,label);
}
for(const label of ['ANGLE (NVIDIA RTX 4070)','ANGLE (Intel Iris Xe Graphics)','Apple M3']){
  const run=boot({label,dpr:3});assert.equal(run.renderer.getPixelRatio(),2,label);assert.equal(run.sun.shadow.mapSize.x,2048,label);
}
assert.equal(boot({label:'SwiftShader',dpr:.5}).renderer.getPixelRatio(),.5,'low native resolution must not be upscaled');
assert.equal(boot({label:'NVIDIA',dpr:NaN}).renderer.getPixelRatio(),1,'invalid DPR uses a finite fallback');
assert.equal(boot({extension:false,masked:'llvmpipe'}).renderer.getPixelRatio(),.75,'masked renderer can still identify software');
assert.equal(boot({throwExtension:true,masked:'SwiftShader'}).renderer.getPixelRatio(),.75,'a restricted debug extension must not break boot');
const unknown=boot({extension:false,masked:null});assert.equal(unknown.renderer.getPixelRatio(),2);assert.equal(unknown.renderer.acsInitialQuality.reason,'RENDERER_ID_UNAVAILABLE');
console.log('PASS: hardware defaults, constrained/unknown capability reports and finite DPR remain explicit');

const telemetryStart=wiringSource.indexOf('window.ACS.legacyRenderQuality=function()');
assert.notEqual(telemetryStart,-1,'the optional quality telemetry must be shipped');
const telemetry=wiringSource.slice(telemetryStart,wiringSource.indexOf('window.ACS.renderDiagnostics=function()',telemetryStart));
vm.runInContext(telemetry,software.context);
const initial=software.context.window.ACS.legacyRenderQuality(),readsBefore=software.reads;
assert.equal(initial.profile,'SOFTWARE_CONSERVATIVE');assert.equal(initial.reason,'SOFTWARE_RENDERER_REPORTED');assert.match(initial.renderer,/SwiftShader/);
assert.equal(initial.initial_pixel_ratio,.75);assert.equal(initial.initial_shadow_map_size,512);assert.equal(initial.pixel_ratio,.75);assert.equal(initial.shadow_map_size,512);
// Apply the existing explicit PBR settings section, rather than replacing it
// with a test-only assignment. Initial profile must not clamp requested ULTRA.
software.context.cfg={exposure:1.1,quality:{pixel_ratio:2},shadows_enabled:true,lighting:{shadows:true},shadow:{map_size:4096,bias:0,normal_bias:0,radius_px:2,camera:{left:-5,right:5,top:5,bottom:-5,near:.1,far:100}}};
software.context.report={changed:[]};software.context._pqDisposeShadowTargets=()=>{};
vm.runInContext(bridgeSource.slice(bridgeSource.indexOf('    renderer.toneMappingExposure=cfg.exposure;'),bridgeSource.indexOf('    /* 2. الشمس')),software.context);
const requested=software.context.window.ACS.legacyRenderQuality();
assert.equal(requested.pixel_ratio,2);assert.equal(requested.shadow_map_size,4096);assert.equal(requested.initial_pixel_ratio,.75);assert.equal(requested.initial_shadow_map_size,512);
assert.equal(software.reads,readsBefore,'telemetry must not perform additional GL queries or read pixels');
requested.profile='changed';assert.equal(software.context.window.ACS.legacyRenderQuality().profile,'SOFTWARE_CONSERVATIVE','callers cannot mutate the recorded profile');
console.log('PASS: actual quality telemetry is read-only and explicit PBR settings remain authoritative');
