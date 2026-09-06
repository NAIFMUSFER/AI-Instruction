/* Fault-injected WebGL API contract. This does not execute a browser/GPU.
   The real context-loss witness runs in test_apply_render_browser.js. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('./lib_gl_three.js',import.meta.url),'utf8');
const {assertGLContext,readGLPixels,WebGLRenderer}=await import(
  'data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
let passed=0,failed=0;
function check(name,test){
  try{test();passed++;console.log('  ✓ '+name);}
  catch(error){failed++;console.error('  ✗ '+name+': '+error.message);}
}
function api(){
  return {lost:false,error:0,reads:0,NO_ERROR:0,RGBA:6408,UNSIGNED_BYTE:5121,
    isContextLost(){return this.lost;},
    getError(){const error=this.error;this.error=0;return error;},
    readPixels(x,y,w,h,format,type,out){this.reads++;out.set([15,18,23,255]);}};
}
check('missing context cannot initialize a renderer',()=>{
  assert.throws(()=>new WebGLRenderer({canvas:{getContext:()=>null}}),/WEBGL_CONTEXT_UNAVAILABLE/);
});
check('truthy lost context cannot initialize a renderer',()=>{
  const gl=api();gl.lost=true;
  assert.throws(()=>new WebGLRenderer({canvas:{getContext:()=>gl}}),/WEBGL_CONTEXT_LOST/);
});
check('context loss is rejected even after the one-shot GL error is consumed',()=>{
  const gl=api();gl.lost=true;gl.error=0x9242;gl.getError();
  assert.throws(()=>assertGLContext(gl,'probe'),/WEBGL_CONTEXT_LOST/);
  assert.throws(()=>assertGLContext(gl,'probe again'),/WEBGL_CONTEXT_LOST/);
});
check('lost context never returns an initialized-to-zero pixel buffer',()=>{
  const gl=api();gl.lost=true;
  assert.throws(()=>readGLPixels(gl,1,1),/WEBGL_CONTEXT_LOST/);
  assert.equal(gl.reads,0);
});
check('context loss during readback is rejected',()=>{
  const gl=api();gl.readPixels=function(){this.lost=true;};
  assert.throws(()=>readGLPixels(gl,1,1),/WEBGL_CONTEXT_LOST/);
});
check('GL readback error is rejected before pixel classification',()=>{
  const gl=api();gl.readPixels=function(){this.error=0x502;};
  assert.throws(()=>readGLPixels(gl,1,1),/WEBGL_ERROR: after readPixels/);
});
check('a pending render error prevents readback',()=>{
  const gl=api();gl.error=0x502;
  assert.throws(()=>readGLPixels(gl,1,1),/WEBGL_ERROR: before readPixels/);
  assert.equal(gl.reads,0);
});
check('render refuses a lost context instead of counting attempted draws',()=>{
  const gl=api();gl.lost=true;
  assert.throws(()=>WebGLRenderer.prototype.render.call({_gl:gl}),/WEBGL_CONTEXT_LOST/);
});
check('zero-size samples cannot become NaN percentages',()=>{
  assert.throws(()=>readGLPixels(api(),0,1),/WEBGL_READBACK_SIZE_INVALID/);
});
check('fractional sample sizes are rejected',()=>{
  assert.throws(()=>readGLPixels(api(),1.5,1),/WEBGL_READBACK_SIZE_INVALID/);
});
check('successful API readback returns its actual bytes unchanged',()=>{
  const gl=api();assert.deepEqual([...readGLPixels(gl,1,1)],[15,18,23,255]);
  assert.equal(gl.reads,1);
});
console.log(`GL PROBE CONTRACT: ${passed} passed, ${failed} failed (fault-injected API; BROWSER NOT VERIFIED)`);
process.exitCode=failed?1:0;
