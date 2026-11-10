import assert from 'node:assert/strict';
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
console.log(`APPROVED VIEWER FRAMING: ${checks} passed; aspect fit, useful scale, immutable bounds and derived assembly isolation.`);
