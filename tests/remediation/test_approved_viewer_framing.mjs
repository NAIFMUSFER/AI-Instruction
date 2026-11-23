import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from 'three';
import {frameBounds,detailGroupKey,floorFinishUVs,embeddedGLB} from '../../public/app/ui/approved-viewer.mjs';
let checks=0;
for(const [label,min,max] of [
 ['villa',[0,-.1,0],[10,7.4,9]],['warehouse',[0,-.1,0],[20,6,16]],['rack',[2,0,2],[18,4.4,3.2]],
])for(const aspect of [1220/522,369/400])for(const direction of [new THREE.Vector3(.95,.72,.95),new THREE.Vector3(0,1,.0001),new THREE.Vector3(.8,0,.6)]){
 const bounds=new THREE.Box3(new THREE.Vector3(...min),new THREE.Vector3(...max));
 const original=JSON.stringify(bounds),frame=frameBounds(bounds,direction,43,aspect);
 const camera=new THREE.PerspectiveCamera(43,aspect,.001,10000);camera.position.copy(frame.position);camera.lookAt(frame.target);camera.updateMatrixWorld();
 let largest=0;
 for(const x of [min[0],max[0]])for(const y of [min[1],max[1]])for(const z of [min[2],max[2]]){
  const point=new THREE.Vector3(x,y,z).project(camera);
  assert.ok(Math.abs(point.x)<=.9&&Math.abs(point.y)<=.9&&point.z<1,`${label} must fit all8 corners at ${aspect}`);
  largest=Math.max(largest,Math.abs(point.x),Math.abs(point.y));
 }
 assert.ok(largest>.7,'the model must use a meaningful share of the viewport');
 assert.equal(JSON.stringify(bounds),original,'camera framing cannot change geometry');checks++;
}
// Presentation UVs follow world metres across slab boundaries without moving vertices.
{
 const geometry=new THREE.PlaneGeometry(2.4,1.2);
 geometry.rotateX(-Math.PI/2);
 const placement=new THREE.Matrix4().makeRotationY(Math.PI/2).setPosition(3,7.5,4.2);
 const original=Array.from(geometry.attributes.position.array),uv=floorFinishUVs(geometry,placement);
 for(let i=0;i<uv.count;i++){
  const p=new THREE.Vector3().fromBufferAttribute(geometry.attributes.position,i).applyMatrix4(placement);
  assert.ok(Math.abs(uv.getX(i)*.6-p.x)<1e-5 && Math.abs(uv.getY(i)*.6-p.z)<1e-5);checks++;
 }
 assert.deepEqual(Array.from(geometry.attributes.position.array),original);checks++;
}
{
 const receipt={revision_id:'R1',model_hash:'model',content_hash:'content',source_map_hash:'sources',provenance_hash:'provenance'};
 const document={buffers:[{byteLength:4,uri:'data:application/octet-stream;base64,AAAAAA=='}],extras:{acs_plan_baseline:receipt}};
 const bytes=new TextEncoder().encode(JSON.stringify(document));
 assert.ok(embeddedGLB(bytes,'R1',receipt).byteLength>0);checks++;
 for(const key of Object.keys(receipt)){
  assert.throws(()=>embeddedGLB(bytes,'R1',{...receipt,[key]:'different'}));checks++;
 }
}
const names=['rack0r0L0','rack0r0L1','post0r0p0','beam0r0','goods0r0L1s2'];
assert.equal(new Set(names.map(name=>detailGroupKey('FURN|F0|storage|'+name))).size,1);checks++;
for(const other of ['FURN|F1|storage|rack0r0L0','FURN|F0|dispatch|rack0r0L0','FURN|F0|storage|rack1r0L0','FURN|F0|storage|rack0r1L0']){
 assert.notEqual(detailGroupKey(other),detailGroupKey('FURN|F0|storage|rack0r0L0'),'derived grouping may not cross level, room, rack or row');checks++;
}
assert.equal(detailGroupKey('OBJ|F-1|living|table0'),'OBJ|F-1|living|table0');checks++;
// Execute the shipped classifiers: naming a normal room roof_* must not hide
// an occupied storey or promote it to a canonical roof. Metadata wins by kind.
const viewerSource=fs.readFileSync('public/app/ui/approved-viewer.mjs','utf8');
// A presentation material must follow the live plane when the selected cut changes.
{
 const code=viewerSource.slice(viewerSource.indexOf('const finishTileMetres'),viewerSource.indexOf('function lineSet')).replace('export function floorFinishUVs','function floorFinishUVs');
 const make=vm.runInNewContext(code+'\nfloorFinish',{THREE,Float32Array,Uint8Array});
 const plane=new THREE.Plane(new THREE.Vector3(0,-1,0),1000),original=new THREE.MeshStandardMaterial();
 original.clippingPlanes=[plane];
 const slab=new THREE.Mesh(new THREE.BoxGeometry(1,.12,1),original),geometry=slab.geometry;
 slab.userData.acsViewerIdentity={kind:'FLOOR',name:'FLOOR|F0|slab|0'};
 const finish=make([slab]);
 finish.set(true);plane.constant=.7;assert.equal(slab.material.clippingPlanes[0].constant,.7);checks++;
 finish.set(false);assert.equal(slab.material,original);assert.equal(slab.geometry,geometry);checks++;
 finish.set(true);plane.constant=1000;assert.equal(slab.material.clippingPlanes[0].constant,1000);checks++;
 finish.dispose();geometry.dispose();original.dispose();
}
{
 const code=viewerSource.slice(viewerSource.indexOf('const finishTileMetres'),viewerSource.indexOf('function lineSet')).replace('export function floorFinishUVs','function floorFinishUVs');
 const make=vm.runInNewContext(code+'\narchitecturalFinish',{THREE,Float32Array,Uint8Array});
 const material=new THREE.MeshStandardMaterial({color:'#2563eb'}),geometry=new THREE.BoxGeometry(2,1,1);
 const plane=new THREE.Plane();material.clippingPlanes=[plane];
 const example=(kind,style)=>{
  const mesh=new THREE.Mesh(geometry,material);
  mesh.userData.acsViewerIdentity={name:kind+'|F0|bay|wN',kind};
  mesh.userData.acsOptionalWallFinish=style;
  mesh.rotation.y=Math.PI/4;mesh.updateMatrixWorld();return mesh;
 };
 const implicit=example('WALL','industrial_cladding'),explicit=example('WALL',null),lane=example('SAFETY','industrial_cladding');
 const identity=implicit.userData.acsViewerIdentity,finish=make([implicit,explicit,lane]);
 assert.equal(finish.count,1);finish.set(true);
 assert.equal(implicit.userData.acsViewerIdentity,identity);assert.equal(implicit.geometry.attributes.position,geometry.attributes.position);
 assert.equal(implicit.geometry.index,geometry.index);assert.equal(implicit.material.clippingPlanes[0],plane);
 assert.equal(explicit.material,material);assert.equal(lane.material,material);checks+=6;
 const source=geometry.getAttribute('position'),uv=implicit.geometry.getAttribute('uv');
 const width=Math.abs(source.getZ(1)-source.getZ(0)),mapped=Math.abs(uv.getX(1)-uv.getX(0));
 assert.ok(width>0&&Math.abs(width-mapped)<1e-5,'wall grain repeats by the metre after rotation');checks++;
 finish.set(false);assert.equal(implicit.geometry,geometry);assert.equal(implicit.material,material);checks++;
 finish.dispose();geometry.dispose();material.dispose();
}
// Demand scheduling must not redraw every pointer event or leave work queued
// after a switch, lost context, or hide. Use deterministic frame/timer clocks.
{
 const code=viewerSource.slice(viewerSource.indexOf('function cameraFrameQueue'),viewerSource.indexOf('function orbitPreview'));
 const frames=new Map(),timers=new Map(),painted=[];let id=0,visible=true,slow=true;
 const make=vm.runInNewContext(code+'\ncameraFrameQueue',{
   requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:key=>frames.delete(key),
   setTimeout:fn=>{timers.set(++id,fn);return id;},clearTimeout:key=>timers.delete(key)
 });
 const queue=make(()=>visible,()=>slow,preview=>painted.push(preview));
 const run=map=>{const callbacks=[...map.values()];map.clear();callbacks.forEach(fn=>fn());};
 queue.request();queue.request();assert.equal(frames.size,1);run(frames);assert.deepEqual(painted,[true]);checks++;
 queue.request();assert.equal(timers.size,0);run(frames);run(timers);assert.deepEqual(painted,[true,true,false]);checks++;
 run(timers);run(frames);assert.equal(painted.length,3);checks++;
 queue.request();visible=false;run(frames);assert.equal(painted.length,3);checks++;
 visible=true;queue.request();run(frames);visible=false;run(timers);assert.equal(painted.length,4);checks++;
 visible=true;queue.request();queue.cancel();assert.equal(frames.size,0);assert.equal(timers.size,0);checks++;
 slow=false;queue.request();run(frames);assert.equal(timers.size,0);assert.equal(painted.at(-1),false);checks++;
}
{
 const code=viewerSource.slice(viewerSource.indexOf('function orbitPreview'),viewerSource.indexOf('function releaseObject'));
 const make=vm.runInNewContext(code+'\norbitPreview',{THREE});
 const geometry=new THREE.BoxGeometry(),source=new THREE.MeshStandardMaterial({color:0x447799,transparent:true,opacity:.7});
 source.clippingPlanes=[new THREE.Plane()];source.alphaTest=.2;
 const mesh=new THREE.Mesh(geometry,source),identity=mesh.uuid,detail=new THREE.Object3D();
 const preview=make([mesh],[detail]);let simplified,draws=0;
 const renderer={shadowMap:{enabled:true},render(){
   draws++;assert.equal(mesh.uuid,identity);assert.equal(mesh.geometry,geometry);assert.equal(mesh.visible,true);
   assert.equal(mesh.material.isMeshLambertMaterial,true);assert.ok(mesh.material.color.equals(source.color));
   assert.equal(mesh.material.opacity,source.opacity);assert.equal(mesh.material.alphaTest,source.alphaTest);assert.equal(mesh.material.clippingPlanes,source.clippingPlanes);
   assert.equal(detail.visible,false);assert.equal(this.shadowMap.enabled,false);
   if(simplified)assert.equal(mesh.material,simplified);simplified=mesh.material;
 }};
 preview.draw(renderer);preview.draw(renderer);assert.equal(draws,2);assert.equal(mesh.material,source);
 assert.equal(detail.visible,true);assert.equal(renderer.shadowMap.enabled,true);checks+=5;
 renderer.render=()=>{throw new Error('synthetic context failure');};
 assert.throws(()=>preview.draw(renderer));assert.equal(mesh.material,source);assert.equal(detail.visible,true);checks++;
 let freed=false;simplified.addEventListener('dispose',()=>{freed=true;});preview.dispose();assert.ok(freed);checks++;
 geometry.dispose();source.dispose();
}
const roofCode=viewerSource.slice(viewerSource.indexOf('  const roofLevels='),viewerSource.indexOf('  const isRoofRow='));
const connectedSource=fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8');
const projectionCode=connectedSource.match(/^const isRoofProjection = (.*);$/m)[1];
for(const [kind,room,expected]of [[null,'roof_bedroom',false],['occupied','roof_living',false],['roof','terrace',true]]){
 const rows=new Map([['3|'+room,{identity:{level:3,room}}]]),context=vm.createContext({levels:new Map([[3,{}]]),roomBounds:rows,original:{scene:0,scenes:[{extras:{acs_levels:[{index:3,kind,template:'upper',elevation_m:7.5}]}}]}});
 vm.runInContext(roofCode+'globalThis.detected=roofLevels.has(3);',context);assert.equal(context.detected,expected,'artifact roof recognition must use explicit canonical kind, not room prefix');checks++;
 const classify=vm.runInNewContext('('+projectionCode+')');assert.equal(classify({level_kind:kind,primitives:[{source:{room_id:room}}]}),expected,'review roof recognition must use explicit level_kind');checks++;
}
// A selected canonical roof remains visible even in plan-like views; the
// disclosure must describe actual meshes, not only the default all-floor filter.
const visibilityCode=viewerSource.slice(viewerSource.indexOf('  function setVisibility(){'),viewerSource.indexOf('  function preset('));
for(const [floor,view,expected]of [['2','aerial',true],['2','cutaway',true],['all','aerial',false]]){
 const roofMesh={userData:{acsViewerIdentity:{level:2}},visible:false},context=vm.createContext({floors:{value:floor},roofOn:true,currentPreset:view,roofLevels:new Set([2]),meshes:[roofMesh],edgeLines:new Map(),clipPlane:{constant:0},clipOff:1000,chosenBounds:()=>({min:{y:8.4},getSize:()=>({y:.9})}),THREE:{Vector3:class{}},renderer:{shadowMap:{}},detailObjects:[],detailOn:true,figures:{},telemetry:{presentation:{}},roofPieces:0,roofNote:{hidden:true},selectionBox:null,selected:null});
 vm.runInContext(visibilityCode+'setVisibility();',context);assert.equal(roofMesh.visible,expected,'explicit roof selection overrides the all-floor default filter');assert.equal(context.telemetry.presentation.roofShown,expected,'roof disclosure agrees with actual canonical visibility');checks++;
}
console.log(`APPROVED VIEWER FRAMING: ${checks} passed; aspect fit, useful scale, immutable bounds and derived assembly isolation.`);
