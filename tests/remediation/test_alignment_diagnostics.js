/* Node integration: real Three.js geometry/matrices, no WebGL/pixel claim.
   Runs the shipped compiler and shipped alignment bridge on the CI fixtures. */
'use strict';
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '../..');
let passed = 0, failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; console.log('  ✓ '+name); }
  else { failed++; console.log('  ✗ '+name+' '+JSON.stringify(detail)); }
}
globalThis.THREE = require(path.join(root, 'node_modules/three/build/three.cjs'));
const material = new THREE.MeshBasicMaterial();
getMat = () => material;
scaleBoxUV = () => {};
const source = fs.readFileSync(path.join(root, 'public/app/generated/pbr-bridge.js'),'utf8');
const start = source.indexOf('function _pqTagParts(');
const end = source.indexOf('window.ACS.canonicalTransformSnapshot=',start);
if (start < 0 || end < 0) throw Error('shipped diagnostics block not found');
function diagnose(input, mutate) {
  const built = compile(input);
  const scene = new THREE.Scene(); scene.add(built);
  if (mutate) mutate(built);
  scene.updateMatrixWorld(true);
  const snapshot = () => { const rows=[]; built.traverse(o=>{
    if(o.isMesh) rows.push([o.name,o.matrixWorld.elements.slice()]); }); return JSON.stringify(rows); };
  const before = snapshot();
  const api = {ACS:{}};
  new Function('THREE','scene','__ACS_LATE','window','pqLevelBaseY',
    'pqContainment','PQ_TC','pqPlateRect','PQ_PLATE_POLICY','pqRoofAlignment',
    'acsRenderLevel','SCENE_LIMITS',source.slice(start,end))(
      THREE,scene,{model:built,lastBuilding:input},api,pqLevelBaseY,
      pqContainment,PQ_TC,pqPlateRect,PQ_PLATE_POLICY,pqRoofAlignment,
      typeof acsRenderLevel==='function'?acsRenderLevel:undefined,SCENE_LIMITS);
  const result=api.ACS.alignmentDiagnostics();
  check('diagnostics preserves all world matrices',snapshot()===before);
  built.traverse(o=>{ if(o.isMesh) o.geometry.dispose(); });
  return result;
}
for (const name of ['live_large_generated','live_large_generated_outlier']) {
  const input=JSON.parse(fs.readFileSync(path.join(root,'tests/phase9_2/fixtures',name+'.json'),'utf8'));
  const before=JSON.stringify(input), r=diagnose(input);
  check(name+': hosted objects are actually checked',r.objects_checked===1378,r.objects_checked);
  check(name+': every hosted transform resolves',r.unresolved_transforms===0,r.unresolved_transforms);
  check(name+': every level plate aligns',r.level_alignment.every(x=>x.aligned),r.level_alignment);
  check(name+': roof aligns',r.roof_alignment.aligned,r.roof_alignment);
  check(name+': all input levels remain distinct',r.level_alignment.length===input.levels.length);
  check(name+': derived addresses are labelled as rendering fallback',r.level_alignment.every(x=>x.index_source==='ARRAY_ORDER_RENDER_FALLBACK'));
  check(name+': canonical input stays byte-equivalent',JSON.stringify(input)===before);
}
const sample={site:{w:12,d:10},floor_height:4.2,wall_h:3.5,wall_t:.2,
 levels:[{index:0,template:'g'},{index:3,template:'g'}],
 floors:{g:{rooms:[{id:'room',rect:[1,1,8,7],furniture:[{kind:'desk',x:1,z:1,w:1,d:1}]}]}}};
const valid=diagnose(sample);
check('explicit non-contiguous indices are preserved',valid.level_alignment.map(x=>x.index).join(',')==='0,3');
check('explicit indices retain their source',valid.level_alignment.every(x=>x.index_source==='MODEL_INDEX'));
check('explicit-index plates and roof align',valid.level_alignment.every(x=>x.aligned)&&valid.roof_alignment.aligned);
const bad=diagnose(sample,built=>built.traverse(o=>{
 if(o.isMesh&&o.name.startsWith('FURN|'))o.position.x+=100;
 if(o.isMesh&&o.name.startsWith('FLOOR|F3|'))o.position.y+=1;
}));
check('displaced hosted object is rejected',bad.outside_host_objects>0,bad);
check('displaced plate is rejected',bad.level_alignment.some(x=>!x.aligned));
check('displaced roof is rejected',bad.roof_alignment.aligned===false);
material.dispose();
console.log(`ALIGNMENT DIAGNOSTICS: ${passed} passed, ${failed} failed (real Three.js; no WebGL)`);
process.exitCode=failed?1:0;
