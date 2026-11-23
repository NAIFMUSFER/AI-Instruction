import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as THREE from 'three';
import {frameBounds,detailGroupKey} from '../../public/app/ui/approved-viewer.mjs';
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
const names=['rack0r0L0','rack0r0L1','post0r0p0','beam0r0','goods0r0L1s2'];
assert.equal(new Set(names.map(name=>detailGroupKey('FURN|F0|storage|'+name))).size,1);checks++;
for(const other of ['FURN|F1|storage|rack0r0L0','FURN|F0|dispatch|rack0r0L0','FURN|F0|storage|rack1r0L0','FURN|F0|storage|rack0r1L0']){
 assert.notEqual(detailGroupKey(other),detailGroupKey('FURN|F0|storage|rack0r0L0'),'derived grouping may not cross level, room, rack or row');checks++;
}
assert.equal(detailGroupKey('OBJ|F-1|living|table0'),'OBJ|F-1|living|table0');checks++;
// Execute the shipped classifiers: naming a normal room roof_* must not hide
// an occupied storey or promote it to a canonical roof. Metadata wins by kind.
const viewerSource=fs.readFileSync('public/app/ui/approved-viewer.mjs','utf8');
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
 const roofMesh={userData:{acsViewerIdentity:{level:2}},visible:false},context=vm.createContext({floors:{value:floor},roofOn:true,currentPreset:view,roofLevels:new Set([2]),meshes:[roofMesh],edgeLines:new Map(),clipPlane:{constant:0},clipOff:1000,chosenBounds:()=>({min:{y:8.4},getSize:()=>({y:.9})}),THREE:{Vector3:class{}},renderer:{shadowMap:{}},detailObjects:[],detailOn:true,figures:{},telemetry:{presentation:{}},roofPieces:0,selectionBox:null,selected:null});
 vm.runInContext(visibilityCode+'setVisibility();',context);assert.equal(roofMesh.visible,expected,'explicit roof selection overrides the all-floor default filter');assert.equal(context.telemetry.presentation.roofShown,expected,'roof disclosure agrees with actual canonical visibility');checks++;
}
console.log(`APPROVED VIEWER FRAMING: ${checks} passed; aspect fit, useful scale, immutable bounds and derived assembly isolation.`);
