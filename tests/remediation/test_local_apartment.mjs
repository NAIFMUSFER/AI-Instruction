import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { apartmentDoorPairs, apartmentFromBrief, apartmentFromRevision, apartmentSample } from '../../public/app/core/local-apartment.mjs';
import { stairConnections, validateStairReport } from '../../public/app/core/stairs.mjs';

const fixture=readFileSync(new URL('../fixtures/briefs/riyadh-apartment-ar.txt',import.meta.url),'utf8');
const sample=apartmentSample();
const original=JSON.stringify(sample);
const exact=apartmentFromBrief(fixture,{width:30,depth:25,levels:4});
const near=(a,b)=>Math.abs(a-b)<0.003;

function outside(room,opening,step) {
  const [x,z,w,d]=room.rect, o=opening.offset;
  return {N:[x+o,z-step], S:[x+o,z+d+step], E:[x+w+step,z+o], W:[x-step,z+o]}[opening.edge];
}
function contains(room,[x,z]) {
  const [u,v,w,d]=room.rect;
  return x>u && x<u+w && z>v && z<v+d;
}

function validate(model,w,d,n) {
  assert.equal(model.meta.acs_apartment.units_total,n*2);
  assert.equal(model.meta.acs_apartment.units_per_floor,2);
  assert.deepEqual(model.site,{w,d});
  assert.equal(model.levels.length,n);
  for(const level of model.levels) {
    const rooms=model.floors[level.template].rooms;
    assert.equal(new Set(rooms.map(r=>r.id)).size,rooms.length);
    const half=model.wall_t/2;
    const opaque=rooms.filter(r=>r.walls===undefined || r.walls==='full');
    const outsideFaces=[
      Math.min(...opaque.map(r=>r.rect[0]))-half,
      Math.min(...opaque.map(r=>r.rect[1]))-half,
      Math.max(...opaque.map(r=>r.rect[0]+r.rect[2]))+half,
      Math.max(...opaque.map(r=>r.rect[1]+r.rect[3]))+half
    ];
    assert.ok(outsideFaces.every((v,i)=>near(v,[0,0,w,d][i])),'exterior wall faces must meet the brief: '+outsideFaces);
    assert.equal(model.meta.acs_apartment.wall_reference,'room_wall_centrelines');
    assert.equal(model.meta.acs_apartment.outer_face_offset_m,half);
    assert.ok(near(rooms.reduce((a,r)=>a+r.rect[2]*r.rect[3],0),(w-2*half)*(d-2*half)),'room axes tile the full plan within the exterior walls');
    for(const r of rooms) {
      const [x,z,rw,rd]=r.rect;
      assert.ok(x>=0&&z>=0&&rw>0&&rd>0&&x+rw<=w+.002&&z+rd<=d+.002);
      for(const other of rooms.filter(o=>o!==r)){
        const [u,v,ow,od]=other.rect;
        assert.ok(Math.min(x+rw,u+ow)-Math.max(x,u)<0.003 || Math.min(z+rd,v+od)-Math.max(z,v)<0.003,'overlap '+r.id+' and '+other.id);
      }
      for(const door of r.doors){
        const q=outside(r,door,.025);
        const target=rooms.find(other=>other!==r&&contains(other,q));
        assert.ok(target,'opposite floor missing at '+r.id+'/'+door.id);
        assert.ok(target.doors.some(other=>{
          const b=outside(target,other,0), a=outside(r,door,0);
          return near(a[0],b[0])&&near(a[1],b[1])&&near(other.width,door.width);
        }),'missing reciprocal aperture '+r.id+'/'+door.id);
      }
      for(const win of r.windows){
        const p=outside(r,win,.025);
        assert.ok(!rooms.some(other=>contains(other,p))||r.id==='lobby'&&level.index===0,'blocked daylight '+r.id);
        assert.ok(win.offset-win.width/2>=0.07);
        assert.ok(win.offset+win.width/2<=r.rect[['N','S'].includes(win.edge)?2:3]-.07);
        assert.ok(win.sill+win.height<=model.wall_h);
      }
    }
    const leafClaims=apartmentDoorPairs(rooms);
    const allDoors=rooms.flatMap(r=>r.doors);
    assert.equal(leafClaims.size,allDoors.length,'every physical door retains both host references');
    assert.equal([...leafClaims.values()].filter(v=>v.primary).length*2,allDoors.length);
    for(const door of allDoors){
      const pair=leafClaims.get(door);
      assert.ok(pair.hosts.some(s=>s.door_id===door.id));
      assert.equal(pair.hosts.length,2);
    }
    const shared=rooms.filter(r=>!r.unit_id);
    assert.ok(shared.some(r=>r.id==='lobby')&&shared.some(r=>r.role==='stairs')&&shared.some(r=>r.role==='elevator'));
    const start=rooms.find(r=>r.id===(level.index?'lobby':'entrance_porch'));
    assert.ok(start);
    const queue=[start],seen=new Set();
    while(queue.length) {
      const room=queue.shift(); if(seen.has(room)) continue;
      seen.add(room);
      for(const door of room.doors) queue.push(rooms.find(other=>other!==room&&contains(other,outside(room,door,.025))));
    }
    assert.equal(seen.size,rooms.length,'disconnected from common entry');
    for(const unit of ['west','east']) {
      const wing=rooms.filter(r=>r.unit_id===unit);
      assert.equal(wing.filter(r=>r.role==='bedroom').length,3);
      assert.ok(wing.filter(r=>r.role==='bedroom').every(r=>r.windows.length));
      assert.equal(wing.filter(r=>r.role==='kitchen').length,1);
      assert.equal(wing.filter(r=>r.role==='bathroom').length,3);
      const foyer=wing.find(r=>r.id.endsWith('_foyer')),majlis=wing.find(r=>r.role==='majlis');
      assert.ok(foyer.doors.some(dr=>contains(majlis,outside(foyer,dr,.025))),'direct guest path into majlis');
      const b=wing.find(r=>r.role==='balcony');
      if(level.index){
        assert.ok(b.objects.some(o=>o.kind==='railing'));
        assert.equal(b.doors.length,1); assert.equal(b.doors[0].material,'glass');
      }else assert.equal(b,undefined);
    }
  }
  if(n>1) {
    validateStairReport(model);
    const links=stairConnections(model);
    assert.equal(links.length,n-1);
    assert.deepEqual(links.map(s=>[s.room_id,s.source_level_index,s.target_level_index]),
      Array.from({length:n-1},(_,i)=>['stair',i,i+1]));
  }
}

assert.equal(exact.meta.acs_apartment.source,'local_brief');
assert.equal(sample.meta.acs_apartment.source,'synthetic_sample');
assert.deepEqual(exact.floors,sample.floors);
assert.deepEqual(exact.levels.map(l=>l.elevation),[0,3.4,6.8]);
for(const m of [sample,exact]) validate(m,20,25,3);
const variants=[
  ['عماره سكنيه من ٣ ادوار ٢٠ في ٢٥',20,25,3],
  ['عمارة سكنية بعرض ٢٠ م وعمق ٢٥ م، أرضي وأول وثانٍ.',20,25,3],
  ['أبغى عمارة سكنية، عرض المبنى ٢٠ متر وعمقه ٢٥ متر، ثلاثة أدوار شاملة الأرضي، وفي كل دور شقتين',20,25,3],
  ['أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور',24,28,4],
  ['عمارة سكنية على شارع غربي',30,30,4],
  ['مبنى سكني على قطعة أرض 26×30 م. أبعاد المبنى 18×22 م. دورين، شقتان في كل دور',18,22,2],
  ['عمارة سكنية ٣٢×٣٦ م، ستة أدوار، شقتين في كل دور',32,36,6],
  ['عمارة سكنية 23×27.5 م، دور واحد',23,27.5,1]
];
for(const [txt,w,d,n] of variants) validate(apartmentFromBrief(txt,{width:30,depth:30,levels:4}),w,d,n);
for(const txt of [
  'عمارة سكنية على أرض ٢٠×٢٥ م','عمارة سكنية 10×16','عمارة سكنية ثمانية أدوار','عمارة سكنية 3 شقق في كل دور',
  'عمارة سكنية لها قبو','عمارة سكنية لكل شقة أربع غرف نوم','عمارة سكنية ٣ أدوار بإجمالي ١٠ شقق',
  'عمارة سكنية 3 أدوار، منسوب الأول +3.20 م والثاني +7.50 م','عمارة على شارع غربي والمدخل من الشمال',
]) assert.throws(()=>apartmentFromBrief(txt),e=>e.code==='LOCAL_APARTMENT_UNSUPPORTED'&&/[ء-ي]/.test(e.message),txt);
for(const txt of ['مستودع 120×80','فيلا من دورين','مدرسة من 3 أدوار']) assert.equal(apartmentFromBrief(txt),null);
// Revisions retain actual dimensions and occupancy across the four facades.
// The check follows the porch, paired doors and stair openings after rotation.
const design=apartmentFromBrief(variants[3][0]);
const originalDesign=JSON.stringify(design);
for(const [direction,edge] of Object.entries({الشمال:'N',الشرق:'E',الجنوب:'S',الغرب:'W'})){
  const revision=apartmentFromRevision('خل المدخل من '+direction,design);
  validate(revision,24,28,4);
  const ground=revision.floors[revision.levels[0].template].rooms;
  const porch=ground.find(r=>r.id==='entrance_porch').rect, lobby=ground.find(r=>r.id==='lobby');
  assert.equal(lobby.doors.find(d=>d.id.endsWith('_to_entrance_porch')).edge,edge);
  const distances={N:porch[1],E:24-porch[0]-porch[2],S:28-porch[1]-porch[3],W:porch[0]};
  assert.ok(near(distances[edge],revision.wall_t/2));
}
const court=apartmentFromRevision('خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق',design);
assert.equal(court.meta.acs_apartment.units_total,8);
for(const l of court.levels) assert.ok(court.floors[l.template].courtyards[0].rect.every(Number.isFinite));
const back=apartmentFromRevision('شيل الفناء',court);
assert.deepEqual(back.floors,design.floors);
assert.equal(JSON.stringify(design),originalDesign);
for(const request of ['أضف فناء مسقوف','فناء وحافظ على أبعاد جميع الغرف','خل المدخل شمالي أو جنوبي','فناء وأبغى خمسة أدوار','انقل السلم']){
  assert.throws(()=>apartmentFromRevision(request,design),e=>e.code==='LOCAL_APARTMENT_UNSUPPORTED',request);
}
const edited=structuredClone(design);
edited.floors[edited.levels[0].template].rooms[0].wall_color='#666666';
assert.throws(()=>apartmentFromRevision('خلّ المدخل من الجنوب',edited),e=>e.code==='LOCAL_APARTMENT_UNSUPPORTED');
const exampleClaims=[
  {id:'left',rect:[0,0,4,4],doors:[{id:'left-door',edge:'E',offset:2.0,width:.9,height:2.1,material:'wood',acs_door_pair:{id:'pair',peer_room_id:'right'}}]},
  {id:'right',rect:[4,0,4,4],doors:[{id:'right-door',edge:'W',offset:2.001,width:.9,height:2.1,material:'wood',acs_door_pair:{id:'pair',peer_room_id:'left'}}]}
];
assert.equal(apartmentDoorPairs(exampleClaims).get(exampleClaims[0].doors[0]).primary,true);
for(const mutate of [r=>r[1].doors[0].offset=2.01,r=>r[1].doors[0].acs_door_pair.peer_room_id='other',
  r=>r[1].doors[0].height=2.3,r=>r[1].doors[0].swing='out',r=>r[1].rect[0]=4.05,
  r=>r[0].doors.push({...r[0].doors[0],id:'third'}),r=>delete r[1].doors[0].acs_door_pair]){
  const edited=structuredClone(exampleClaims);mutate(edited);
  assert.equal(apartmentDoorPairs(edited).size,0,'invalid imported claim cannot suppress a leaf');
}
assert.equal(JSON.stringify(sample),original,'other local creations leave existing drafts untouched');
console.log('PASS local apartment: original Arabic brief, independent dimensions, occupancy, true paired apertures, connected rooms, distinct units, stairs, street frontage and bounded errors');
