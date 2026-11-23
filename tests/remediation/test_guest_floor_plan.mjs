import assert from 'node:assert/strict';
import {renderGuestFloorSVG} from '../../public/app/ui/guest-floor-plan.mjs';

const level={index:2,template:'same',name:'الدور الثاني'};
const model={levels:[level],meta:{acs_apartment:{street_edge:'N'}}, floors:{same:{rooms:[
  {id:'a',unit_id:'east',name:'مجلس & ضيافة'},
  {id:'b',unit_id:'west',name:'<script><&"\''},
]}}};
const packet={level_index:2,spaces:[
  {id:'id-a@2',space_id:'id-a',name:'a',x:7,z:2,w:3,d:4,area_m2:12,boundary_basis:'rectangle_edges'},
  {id:'id-b@2',space_id:'id-b',name:'b',x:10,z:2,w:5,d:6,area_m2:30,boundary_basis:'rectangle_edges'},
  {id:'unsupported',x:50,z:50,w:50,d:50,boundary_basis:'unsupported_shape'},
],walls:[{id:'e1',x1:7,z1:2,x2:10,z2:2,thickness_m:.16}],openings:[
 {id:'a.glazing',type:'WINDOW',host_wall_id:'e1',x1:8,z1:2,x2:9,z2:2,width_m:1},
 {id:'a.exit',type:'DOOR',host_wall_id:'e1',x1:9,z1:2,x2:9.9,z2:2,width_m:.9},
 {id:'orphan',type:'WINDOW',host_wall_id:'absent',x1:30,z1:31,x2:32,z2:32,width_m:2},
]};
const before=JSON.stringify([packet,model]);
const svg=renderGuestFloorSVG(packet,model);
for(const token of ['data-width-m="8"','data-depth-m="6"','data-level-index="2"','data-room-key="id-a@2" data-unit="east"','data-unit="west"','data-opening-id="a.glazing"','data-opening-id="a.exit"','data-wall-id="e1"','الدور الثاني','الشقة الشرقية','شمال','مجلس &amp; ضيافة','&lt;script&gt;']) assert.ok(svg.includes(token),token);
for(const token of ['<script>','data-opening-id="orphan"','data-room-key="unsupported"','NaN'])assert.ok(!svg.includes(token),token);
const local=renderGuestFloorSVG(packet,{...model,meta:{}},{schedule:false,selected:'id-a@2'});
assert.ok(!local.includes('شمال'),'no invented north for unreferenced imports');
assert.ok(local.includes('fill="#d0ae6d"'));
assert.equal(JSON.stringify([packet,model]),before);
assert.throws(()=>renderGuestFloorSVG({...packet,spaces:[]},model), /فراغات/);
console.log('PASS guest physical floor instance, footprint, source names, apertures, unit labels, safe SVG and source preservation');
