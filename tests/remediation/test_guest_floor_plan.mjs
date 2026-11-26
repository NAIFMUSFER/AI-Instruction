import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {apartmentFromBrief,apartmentFromRevision,apartmentSample} from '../../public/app/core/local-apartment.mjs';
import {resolveStairGeometry,stairConnections} from '../../public/app/core/stairs.mjs';
import {renderGuestFloorSVG} from '../../public/app/ui/guest-floor-plan.mjs';
import {withDefaultRoof} from '../../public/app/core/roof.mjs';

const level={index:2,template:'same',name:'الدور الثاني'};
const model={levels:[level],meta:{north:'-Z',acs_apartment:{street_edge:'N'}}, floors:{same:{rooms:[
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
const turned = structuredClone(model);
turned.meta.acs_apartment.street_edge = 'W';
turned.meta.acs_apartment.unit_labels = {east:'الشقة الشمالية',west:'الشقة الجنوبية'};
const turnedSVG = renderGuestFloorSVG(packet,turned);
assert.ok(turnedSVG.includes('الشقة الشمالية') && turnedSVG.includes('الشقة الجنوبية'));
assert.ok(turnedSVG.includes('data-unit="east"') && turnedSVG.includes('data-unit="west"'), 'drawing labels must not rename stable unit identities');
assert.ok(turnedSVG.includes('شمال'), 'declared north remains visible when the entrance moves west');
assert.ok(!turnedSVG.includes('الشقة الشرقية') && !turnedSVG.includes('الشقة الغربية'));
turned.meta.acs_apartment.unit_labels.east = '<script>alert(1)</script>';
assert.ok(renderGuestFloorSVG(packet,turned).includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
assert.ok(!renderGuestFloorSVG(packet,turned).includes('<script>'));
delete turned.meta.north;
assert.ok(!renderGuestFloorSVG(packet,turned).includes('>شمال<'), 'street direction alone does not establish plan north');
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

// Run the JSON download and floor projection on the same live model reference,
// using the shipped compiler and export functions from the headless test bundle.
const root=fileURLToPath(new URL('../../',import.meta.url));
const work=mkdtempSync(join(tmpdir(),'acs-guest-export-'));
try {
  const bundleFile=join(work,'browser-bundle.js');
  execFileSync(process.execPath,['tests/phase3/lib/extract_browser_bundle.js'],{
    cwd:root,env:{...process.env,ACS_BUNDLE:bundleFile},stdio:'pipe'
  });
  const api=new Function(readFileSync(bundleFile,'utf8')+
    '\nreturn {projectEnvelope,compileArchitecture,visFloorPlan};')();
  const brief=readFileSync(new URL('../fixtures/briefs/riyadh-apartment-ar.txt',import.meta.url),'utf8');
  const selected=apartmentFromBrief(brief);
  function sheetFor(building){
    const arch=api.compileArchitecture(building,'bld_0',null,0);
    return renderGuestFloorSVG(api.visFloorPlan(arch,1,'TECHNICAL','bld_0'),building);
  }
  for(const authored of [false,true]){
    if(authored)selected.floors.level_1.rooms[0].space_id='authored-lobby';
    const serialized=JSON.stringify(selected);
    const initialSheet=sheetFor(selected);
    assert.equal(JSON.stringify(selected),serialized,'drawing a floor changed the selected model');
    const envelope=JSON.parse(JSON.stringify(api.projectEnvelope(selected)));
    assert.ok(JSON.stringify(selected)===serialized,'downloading JSON added export identifiers to the selected apartment');
    assert.ok(envelope.levels.every(l=>l.id));
    const room=envelope.floors.level_1.rooms[0];
    assert.equal(room.space_id,authored?'authored-lobby':'bld_0.level_1.'+room.id);
    assert.ok(envelope.relationships.length>0,'the exported model retains its relationship identifiers');
    assert.equal(sheetFor(envelope),initialSheet,'exported room, opening and stair identifiers differ from the live drawing');
    assert.equal(sheetFor(selected),initialSheet);
  }
  const initial=apartmentFromBrief('عمارة سكنية عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور');
  const withCourt=apartmentFromRevision('خل وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق',initial);
  const turnedCourt=apartmentFromRevision('خل المدخل شرقي',withCourt);
  for(const building of [withCourt,turnedCourt]){
    const serialized=JSON.stringify(building);
    for(const level of building.levels){
      const arch=api.compileArchitecture(building,'bld_0',null,0);
      const actual=api.visFloorPlan(arch,level.index,'TECHNICAL','bld_0');
      const drawing=renderGuestFloorSVG(actual,building);
      const court=building.floors[level.template].courtyards[0];
      const [,,cw,cd]=court.clear_rect;
      assert.ok(drawing.includes('data-courtyard-id="central_courtyard"'));
      assert.ok(drawing.includes(`data-courtyard-width-m="${cw}" data-courtyard-depth-m="${cd}"`));
      assert.ok(drawing.includes('مفتوح للسماء') && drawing.includes('بين وجوه الجدران'));
      assert.ok(drawing.includes('>شمال<'), 'orientation uses the fixed coordinate system after a facade change');
      const forged=structuredClone(building);
      const sourceFloor=forged.floors[level.template];
      sourceFloor.courtyards[0].rect=[...sourceFloor.rooms[0].rect];
      sourceFloor.courtyards[0].clear_rect=[...sourceFloor.rooms[0].rect];
      assert.ok(!renderGuestFloorSVG(actual,forged).includes('data-courtyard-id='), 'an occupied room cannot acquire a courtyard label from metadata');
    }
    assert.equal(JSON.stringify(building),serialized, 'every-floor courtyard drawing must preserve source geometry');
  }
  assert.ok(initial.levels.every(level=>!initial.floors[level.template].courtyards), 'a courtyard revision preserves the prior project');
  // The roof plan shows the courtyard opening too, labelled as open and guarded.
  const [roofed]=withDefaultRoof(withCourt), roofLevel=roofed.levels.find(level=>level.kind==='roof');
  const roofSheet=renderGuestFloorSVG(api.visFloorPlan(api.compileArchitecture(roofed,'bld_0',null,0),roofLevel.index,'TECHNICAL','bld_0'),roofed);
  const [,,rcw,rcd]=roofed.meta.acs_apartment.courtyard.rect_m;
  assert.ok(roofSheet.includes('data-courtyard-id="central_courtyard"')&&roofSheet.includes(`data-courtyard-width-m="${rcw}" data-courtyard-depth-m="${rcd}"`),'roof plan draws the opening');
  assert.ok(roofSheet.includes('فناء مفتوح'),'roof plan labels the opening «فناء مفتوح»');
  assert.ok(!renderGuestFloorSVG(api.visFloorPlan(api.compileArchitecture(withDefaultRoof(initial)[0],'bld_0',null,0),4,'TECHNICAL','bld_0'),withDefaultRoof(initial)[0]).includes('data-courtyard-id='),'no opening on a roof without a courtyard');
} finally { rmSync(work,{recursive:true,force:true}); }
console.log('PASS apartment JSON and every-floor courtyard plans preserve source, authored IDs, measured clear openings and actual orientation');
