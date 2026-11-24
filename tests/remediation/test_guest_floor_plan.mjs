import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import APP from '../lib/app_source.js';
import {apartmentFromBrief,apartmentFromRevision,apartmentDoorPairs,apartmentSample} from '../../public/app/core/local-apartment.mjs';
import {resolveStairGeometry,stairConnections} from '../../public/app/core/stairs.mjs';
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
// The outer-face dimension must come from the physical wall faces, even if a
// caller changes the description or the site dimensions without moving walls.
const perimeterModel = {...model,meta:{acs_apartment:{wall_reference:'room_wall_centrelines',width_m:20,depth_m:25}}};
const perimeter = {level_index:2,spaces:[{...packet.spaces[0],x:2.09,z:4.09,w:9.82,d:11.82}],walls:[
  {id:'north',x1:2.09,z1:4.09,x2:11.91,z2:4.09,thickness_m:.18},
  {id:'south',x1:2.09,z1:15.91,x2:11.91,z2:15.91,thickness_m:.18},
  {id:'west',x1:2.09,z1:4.09,x2:2.09,z2:15.91,thickness_m:.18},
  {id:'east',x1:11.91,z1:4.09,x2:11.91,z2:15.91,thickness_m:.18},
],openings:[]};
const outside = renderGuestFloorSVG(perimeter,perimeterModel);
assert.ok(outside.includes('data-width-m="10" data-depth-m="12"'), 'exterior dimension endpoints must measure both wall faces');
assert.ok(outside.includes('data-grid-width-m="9.82" data-grid-depth-m="11.82"'));
assert.ok(outside.includes('data-dimension-basis="outer_wall_faces"'));
assert.ok(outside.includes('محاور الجدران'));
console.log('PASS guest physical floor instance, footprint, source names, apertures, unit labels, safe SVG and source preservation');

// Check real downloadable sheets against independently authored physical instances.
const apartment = apartmentSample();
for(const floor of apartment.levels) {
  const sheet=readFileSync(new URL(`../../public/guest-plans/apartment-floor-${floor.index}.svg`,import.meta.url),'utf8');
  assert.ok(sheet.includes('data-width-m="20" data-depth-m="25"'));
  assert.ok(sheet.includes('data-grid-width-m="19.82" data-grid-depth-m="24.82"'));
  assert.ok(sheet.includes('data-dimension-basis="outer_wall_faces"'));
  assert.ok(sheet.includes('المستطيل المحيط بالجدران 500 م²'));
  assert.ok(sheet.includes(`data-level-index="${floor.index}"`));
  const preview=readFileSync(new URL(`../../public/guest-plans/apartment-floor-${floor.index}-preview.svg`,import.meta.url),'utf8');
  const attrValues=(svg,key)=>[...svg.matchAll(new RegExp(` ${key}="([^"]*)"`,'g'))].map(match=>match[1]);
  for (const attr of ['data-room-key','data-wall-id','data-opening-id','data-stair-object','data-stair-part']) {
    assert.deepEqual(attrValues(preview,attr),attrValues(sheet,attr));
  }
  const viewBoxHeights=[preview,sheet].map(svg=>Number(attrValues(svg,'viewBox')[0].split(' ')[3]));
  assert.ok(viewBoxHeights[0]<viewBoxHeights[1]/2,'inline drawing must omit the extra height of the room schedule');
  assert.ok(!preview.includes('الشقة الشرقية') && sheet.includes('الشقة الشرقية'));
  const rooms=apartment.floors[floor.template].rooms;
  assert.equal((sheet.match(/data-room-key=/g)||[]).length,rooms.length);
  for (const unit of ['east','west']) {
    assert.equal((sheet.match(new RegExp(`data-unit="${unit}"`,'g'))||[]).length,rooms.filter(r=>r.unit_id===unit).length);
  }
  for(const stair of stairConnections(apartment)) {
    if(stair.source_level_index===floor.index){
      assert.ok(sheet.includes(`data-stair-object="${stair.object.id}"`));
      assert.equal((sheet.match(/data-stair-part=/g)||[]).length,resolveStairGeometry(stair.object).components.length);
    }
    if(stair.target_level_index===floor.index) assert.ok(sheet.includes(`data-stair-opening="${stair.object.id}"`));
  }
}
console.log('PASS named apartment fallback, physical level/room/unit counts and source stair components');

// Check the occupied/void partition, and the actual adjoining surfaces around
// the common entrance. Metadata and a label on an otherwise solid floor fail.
const closed=apartmentFromBrief('أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور');
const withCourt=apartmentFromRevision('خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق',closed);
const rotated=apartmentFromRevision('خل المدخل شرقي',withCourt);
const {compileArchitecture,projectArchitecturalLevel}=new Function(APP.nodeBundle()+';return {compileArchitecture,projectArchitecturalLevel};')();
for(const building of [withCourt,rotated]) {
  const source=JSON.stringify(building);
  const architecture=compileArchitecture(building);
  const firstCourt=building.floors[building.levels[0].template].courtyards[0];
  for(const level of building.levels) {
    const floor=building.floors[level.template], rooms=floor.rooms;
    const {rect}=floor.courtyards[0], [x,z,w,d]=rect;
    assert.deepEqual(rect,firstCourt.rect,'every floor must leave the same unoccupied opening');
    assert.ok(x<12 && x+w>12 && z<14 && z+d>14,'court is within the middle of the building');
    const occupied=rooms.reduce((sum,room)=>{
      const [u,v,rw,rd]=room.rect;
      assert.ok(Math.min(u+rw,x+w)-Math.max(x,u)<0.002 || Math.min(v+rd,z+d)-Math.max(v,z)<0.002,room.id+' overlaps the court');
      return sum+rw*rd;
    },0);
    assert.ok(Math.abs(occupied+w*d-(24-building.wall_t)*(28-building.wall_t))<0.002);
    const pairs=apartmentDoorPairs(rooms);
    for(const [a,b] of [['stair','lobby'],['east_foyer','lobby'],['west_foyer','lobby'],['court_passage','lobby'],['lift','court_passage']]) {
      const door=rooms.find(r=>r.id===a).doors.find(dr=>dr.acs_door_pair?.peer_room_id===b);
      assert.ok(pairs.has(door),'missing shared access '+a+' → '+b);
    }
    const passage=rooms.find(r=>r.id==='court_passage');
    assert.equal(passage.doors.some(dr=>dr.id==='court_ground_door'),level.index===0,'court exit is on the ground only');
    const sheet=renderGuestFloorSVG(projectArchitecturalLevel(architecture,level.index),building);
    assert.ok(sheet.includes('data-courtyard-id="central_courtyard"') && sheet.includes('مفتوح للسماء'));
    assert.ok(sheet.includes('data-width-m="24" data-depth-m="28"') && sheet.includes('ممر الفناء المشترك'));
    if (building===rotated) assert.ok(sheet.includes('شمال') && sheet.includes('الشقة الشمالية'));
  }
  assert.equal(stairConnections(building).length,3,'four levels must have three real stair connections');
  assert.equal(JSON.stringify(building),source,'compiling, selecting and projecting every floor must preserve the active revision byte for byte');
}
assert.ok(closed.levels.every(level=>!closed.floors[level.template].courtyards),'revision must preserve the previous model');
console.log('PASS aligned open court and independent common routes to both apartments, lift and ground garden');
