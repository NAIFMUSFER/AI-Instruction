import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { apartmentConfirmation, apartmentDoorPairs, apartmentFromBrief, apartmentFromRevision, apartmentSample } from '../../public/app/core/local-apartment.mjs';
import { stairConnections, validateStairReport } from '../../public/app/core/stairs.mjs';
import { withDefaultRoof, carryAutoRoof } from '../../public/app/core/roof.mjs';
import { withContextDetails } from '../../public/app/core/context-details.mjs';
import { pqPlateRect } from '../../public/app/generated/pbr.js';
import { compileArchitecture } from '../../public/app/core/disciplines.js';

const fixture=readFileSync(new URL('../fixtures/briefs/riyadh-apartment-ar.txt',import.meta.url),'utf8');
const sample=apartmentSample();
const original=JSON.stringify(sample);
const exact=apartmentFromBrief(fixture);
const near=(a,b)=>Math.abs(a-b)<0.003;
{
  // Rooms declare the ceiling light the approval gate requires, and the
  // largest supported design still fits the context-details resource bound.
  const largest=apartmentFromBrief('عمارة سكنية عرض المبنى ٣٢ متر وعمقه ٣٦ متر، ستة أدوار شاملة الأرضي، شقتين في كل دور');
  for(const level of largest.levels)for(const room of largest.floors[level.template].rooms)
    assert.ok((room.points||[]).some(point=>point.type==='light'&&point.id==='ceiling_light'),'every generated room declares its ceiling light: '+room.id);
  assert.equal(withContextDetails(withDefaultRoof(largest)[0])[2],null,'the largest supported design keeps its context details');
}
{
  // A guest project saved before these conventions still accepts an entrance
  // or courtyard revision: no lights, role 'entry', no object repeat fields,
  // and paired door leaves up to 1 mm apart are not manual edits.
  const legacy=structuredClone(apartmentFromBrief(fixture));
  let shifted=0;
  for(const floor of Object.values(legacy.floors))for(const room of floor.rooms){
    room.points=(room.points||[]).filter(point=>point.id!=='ceiling_light');
    if(!room.points.length)delete room.points;
    if(room.role==='entrance'&&room.unit_id)room.role='entry';
    for(const obj of room.objects||[])if(obj.count===1){delete obj.count;delete obj.pitch;delete obj.dir;}
    for(const door of room.doors||[])if(door.acs_door_pair&&shifted<5){door.offset=Math.round((door.offset+0.001)*1000)/1000;shifted++;}
  }
  const revised=apartmentFromRevision('خل المدخل من الشرق',legacy);
  assert.equal(revised.meta.acs_apartment.street_edge,'E');
  assert.ok(revised.levels.every(level=>revised.floors[level.template].rooms.every(room=>room.points?.some(point=>point.id==='ceiling_light'))));
}
// Re-pinned when the sample became approvable: rooms gained one ceiling light,
// objects state count/pitch/dir, the foyer role is 'entrance' and paired door
// offsets share one rounded centre (each moved <= 1 mm). No room rectangle moved;
// the prebuilt USDZ was refreshed and the schematic drawings are unchanged.
assert.equal(createHash('sha256').update(original).digest('hex'),'b1c1bf1bb2aedc5628da929888b2ebeb4505c13bec1e70a7b641ffa542eeed58',
  'the shipped sample and its prebuilt drawings/USDZ must retain their original source geometry');

function outside(room,opening,step) {
  const [x,z,w,d]=room.rect, o=opening.offset;
  return {N:[x+o,z-step], S:[x+o,z+d+step], E:[x+w+step,z+o], W:[x-step,z+o]}[opening.edge];
}
function contains(room,[x,z]) {
  const [u,v,w,d]=room.rect;
  return x>u && x<u+w && z>v && z<v+d;
}
function overlaps(a,b) {
  return Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0])>0.003 &&
    Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1])>0.003;
}

function validate(model,w,d,n) {
  assert.equal(model.meta.acs_apartment.units_total,n*2);
  assert.equal(model.meta.acs_apartment.units_per_floor,2);
  assert.deepEqual(model.site,{w,d});
  assert.equal(model.levels.length,n);
  const court=model.meta.acs_apartment.courtyard;
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
    const voidArea=court?court.footprint_void_m[2]*court.footprint_void_m[3]:0;
    assert.ok(near(rooms.reduce((a,r)=>a+r.rect[2]*r.rect[3],0),(w-2*half)*(d-2*half)-voidArea),
      'room axes tile the footprint except for the declared courtyard');
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
        if(!target) {
          assert.ok(court && level.index===0 && r.role==='corridor' && r.id==='courtyard_gallery_north' && door.id==='court_ground_door',
            'only the named ground door may open onto the site inside the court: '+r.id+'/'+door.id);
          assert.ok(contains({rect:court.rect_m},outside(r,door,model.wall_t/2+.05)), 'garden access must actually enter the clear courtyard');
          continue;
        }
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
    const interiorDoors=allDoors.filter(door=>door.id!=='court_ground_door');
    assert.equal(allDoors.length-interiorDoors.length,court&&level.index===0?1:0,'upper courtyard access is glazed, not a door into air');
    assert.equal(leafClaims.size,interiorDoors.length,'every interior physical door retains both host references');
    assert.equal([...leafClaims.values()].filter(v=>v.primary).length*2,interiorDoors.length);
    for(const door of interiorDoors){
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
      for(const door of room.doors) {
        const target=rooms.find(other=>other!==room&&contains(other,outside(room,door,.025)));
        if(target) queue.push(target);
      }
    }
    assert.equal(seen.size,rooms.length,'disconnected from common entry');
    if(court) {
      assert.equal(court.open_to_sky,true); assert.equal(court.occupied_floor,false);
      assert.ok(near(court.rect_m[0]+court.rect_m[2]/2,w/2) && near(court.rect_m[1]+court.rect_m[3]/2,d/2),'court is central');
      assert.ok(rooms.every(r=>!overlaps(r.rect,court.footprint_void_m)),'no occupied rectangle is hidden inside a declared void');
      assert.deepEqual(model.floors[level.template].courtyards[0].clear_rect,court.rect_m);
      const pending=[start], common=new Set();
      while(pending.length) {
        const room=pending.shift(); if(common.has(room)) continue; common.add(room);
        for(const door of room.doors) {
          const target=shared.find(other=>other!==room&&contains(other,outside(room,door,.025)));
          if(target)pending.push(target);
        }
      }
      assert.ok(shared.every(r=>common.has(r)),'all four courtyard galleries, stair and lift connect without crossing a private unit');
      const galleries=shared.filter(r=>r.id.startsWith('courtyard_gallery_'));
      assert.equal(galleries.length,4);
      for(const room of galleries) assert.equal(room.doors.filter(door=>galleries.some(other=>other!==room&&contains(other,outside(room,door,.025)))).length,2,
        'gallery circulation forms a complete ring');
    }
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
  const ground=model.floors[model.levels[0].template].rooms;
  const porch=ground.find(r=>r.id==='entrance_porch'), lobby=ground.find(r=>r.id==='lobby');
  const entrance=model.meta.acs_apartment.street_edge;
  const distances={N:porch.rect[1],E:w-porch.rect[0]-porch.rect[2],S:d-porch.rect[1]-porch.rect[3],W:porch.rect[0]};
  assert.ok(near(distances[entrance],model.wall_t/2),'porch physically reaches the requested facade');
  assert.equal(lobby.doors.find(door=>door.id.endsWith('_to_entrance_porch')).edge,entrance);
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
  ['عمارة سكنية على شارع غربي',30,30,4,{width:30,depth:30,levels:4}],
  ['عمارة سكنية طول المبنى ٢٩ متراً وعرض المبنى ٢٣ متراً، دورين',23,29,2],
  ['عمارة ٢٤×٢٨ م، أرضي وثلاثة أدوار فوقه. في كل دور شقتين',24,28,4],
  ['عمارة ٢٤×٢٨ م، أربعة أدوار شاملة الأرضي. المجموع ثماني شقق',24,28,4],
  ['مبنى سكني على قطعة أرض 26×30 م. أبعاد المبنى 18×22 م. دورين، شقتان في كل دور',18,22,2],
  ['عمارة سكنية ٣٢×٣٦ م، ستة أدوار، شقتين في كل دور',32,36,6],
  ['عمارة سكنية 23×27.5 م، دور واحد',23,27.5,1]
];
for(const [txt,w,d,n,form] of variants) validate(apartmentFromBrief(txt,form),w,d,n);
const explicitDimensions = [
  'عمارة سكنية من ٤ أدوار، عرض المبنى ٢٤ مترًا وعمقه ٢٨ مترًا، شقتان في كل دور',
  'عمارة سكنية بطول ٢٨ مترًا وعرض ٢٤ مترًا، ٤ طوابق بإجمالي ٨ شقق',
  'عمارة سكنية. عرض العمارة ٢٤ م، وطولها ٢٨ م. ٤ أدوار. في كل دور شقتان.',
  'عمارة سكنية من ٤ أدوار من دون فناء، ٢٤ مترًا عرضًا و٢٨ مترًا طولًا، على شارع شمالي',
  'عمارة سكنية من ٤ أدوار. أبعاد المبنى ٢٤ متراً في ٢٨ متراً، لا يوجد بها قبو.',
  'عمارة سكنية من ٤ أدوار، عرض المبنى ٢٤ م وعمقه ٢٨ م، على قطعة أرض ٢٦×٣٢ م',
  'عمارة سكنية من ٤ أدوار، الأرض ٢٦×٣٢ م، واجهة المبنى ٢٤ م وعمق المبنى ٢٨ م'
];
for(const txt of explicitDimensions) {
  const result=apartmentFromBrief(txt);
  assert.deepEqual(result.site,{w:24,d:28},txt);
  assert.deepEqual([result.levels.length,result.meta.acs_apartment.units_total],[4,8],txt);
}
for(const [txt,reason] of [
  ['عمارة سكنية فيها شقق دوبلكس','دوبلكس'],
  ['عمارة سكنية بفناء جانبي','فناء'],
  ['عمارة سكنية بفناء مسقوف','فناء'],
  ['عمارة سكنية ومدخل المبنى في يمين الواجهة الشمالية','منتصف'],
  ['عمارة سكنية ومدخل المبنى في يسار الواجهة الشمالية','منتصف'],
  ['عمارة سكنية ومدخل المبنى شمالي أو غربي','جهة'],
  ['عمارة سكنية من ثلاثة أدوار، في الأرضي شقة واحدة وفي الأول ثلاث شقق','شقتين'],
  ['عمارة سكنية من ٣ أدوار، شقتان في كل دور عدا الدور الأخير فيه ٣ شقق','شقتين'],
  ['عمارة سكنية من أربعة طوابق، شقتان بالأرضي و٣ شقق في الدور الأول','شقتين'],
  ['عمارة سكنية من ٣ أدوار، في كل دور شقتان وفي كل دور علوي ثلاث وحدات سكنية','شقتين'],
  ['عمارة سكنية عرض المبنى أربعة وعشرون مترًا وعمقه ٢٨ م','بالأرقام'],
  ['عمارة سكنية عرض المبنى ٢٤ قدم وعمقه ٢٨ م','بالمتر'],
  ['عمارة سكنية ٢٠×٢٥ م، عرض المبنى ٢٤ وعمقه ٢٨','متعارضة']
]) assert.throws(()=>apartmentFromBrief(txt),
  error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED'&&error.message.includes(reason),txt);
for(const txt of [
  'عمارة سكنية على أرض ٢٠×٢٥ م','عمارة سكنية 10×16','عمارة سكنية ثمانية أدوار','عمارة سكنية 3 شقق في كل دور',
  'عمارة سكنية لها قبو','عمارة سكنية لكل شقة أربع غرف نوم','عمارة سكنية ٣ أدوار بإجمالي ١٠ شقق',
  'عمارة سكنية 3 أدوار، منسوب الأول +3.20 م والثاني +7.50 م',
  'عمارة على شارع غربي والمدخل من الشمال',
  'عمارة ثلاثة أدوار، في كل دور شقتين، وبإجمالي أربعة أدوار شاملة الأرضي',
  'عمارة أرضي وثلاثة أدوار شاملة الأرضي',
  'عمارة عرض المبنى ٢٤ متر وعمقه ٢٨. عرض المبنى ٢٦ متر',
  'عمارة أبعاد المبنى ٢٤ × ٢٨. عمق المبنى ٣٢ متر',
  'عمارة٢٤×٢٨ م، ٤ أدوار.\n\nغرفة نوم.\n\nعرض المبنى ٢٦ م',
]) assert.throws(()=>apartmentFromBrief(txt),e=>e.code==='LOCAL_APARTMENT_UNSUPPORTED'&&/[ء-ي]/.test(e.message),txt);
for(const txt of ['مستودع 120×80','فيلا من دورين','مدرسة من 3 أدوار']) assert.equal(apartmentFromBrief(txt),null);

const cases=[
  ['riyadh-apartment-ar.txt',20,25,3,'N'],
  ['riyadh-apartment-24x28-ar.txt',24,28,4,'N'],
  ['riyadh-apartment-courtyard-ar.txt',20,25,3,'N'],
  ['saudi-apartment-west-ar.txt',24,28,3,'W']
];
for(const [file,w,d,n,entrance] of cases) {
  const text=readFileSync(new URL('../fixtures/briefs/'+file,import.meta.url),'utf8');
  const model=apartmentFromBrief(text);
  validate(model,w,d,n); assert.equal(model.meta.acs_apartment.street_edge,entrance);
  assert.equal(model.meta.acs_apartment.brief,text,'source brief remains distinguishable from the authored geometry');
}
const revisionBase=apartmentFromBrief('عمارة سكنية ٢٤×٢٨ م من ٤ أدوار، شقتان في كل دور بإجمالي ٨ شقق');
const revisionSource=JSON.stringify(revisionBase);
for(const [direction,edge] of Object.entries({الشمال:'N',الشرق:'E',الجنوب:'S',الغرب:'W'})) {
  for(const court of [false,true]) {
    const request='خل المدخل من '+direction+(court?' وأضف فناء مركزي مفتوح للسماء بأبعاد صافية ٤×٥ م':'');
    const changed=apartmentFromRevision(request,revisionBase);
    validate(changed,24,28,4); assert.equal(changed.meta.acs_apartment.street_edge,edge);
    assert.equal(changed.meta.acs_apartment.last_revision,request);
    if(court) {
      assert.deepEqual(changed.meta.acs_apartment.courtyard.rect_m,[10,11.5,4,5]);
      const [roofed,,reason]=withDefaultRoof(changed); assert.equal(reason,null);
      assert.equal(changed.meta.acs_apartment.courtyard.size_source,'client_stated');
      // Every roof edge stretch with no deck beyond it (the courtyard opening and the
      // facade alike) carries the 0.9 m parapet, as a whole-edge wall or a span; none
      // crosses a neighbouring deck, and every deck keeps its source rectangle.
      const decks=roofed.floors[roofed.levels.at(-1).template].rooms;
      const top=changed.floors[changed.levels.at(-1).template].rooms;
      assert.deepEqual(decks.map(deck=>deck.rect),top.map(room=>room.rect),'one deck per top-floor room, no slivers');
      for(const deck of decks) {
        assert.deepEqual(deck.roof_provenance.parapet_gaps,[],'no unguarded roof edge: '+deck.id);
        assert.equal(deck.wall_h,0.9);
        const [x,z,w,d]=deck.rect;
        for(const edge of ['N','S','W','E']) {
          const length=['N','S'].includes(edge)?w:d;
          for(const f of [.031,.061,.293,.517,.739,.947,.969]) {
            const point={N:[x+w*f,z-.02],S:[x+w*f,z+d+.02],W:[x-.02,z+d*f],E:[x+w+.02,z+d*f]}[edge];
            const open=!decks.some(other=>other!==deck&&contains(other,point));
            const guarded=deck.walls.includes(edge)||(deck.parapet_spans||[]).some(span=>span.edge===edge&&span.start_m<=f*length&&f*length<=span.end_m);
            assert.equal(guarded,open,'parapet follows the open roof edge: '+deck.id+'/'+edge+'@'+f);
          }
        }
      }
      // The architectural compiler declares the opening and pierces every slab and the roof.
      const arch=compileArchitecture(roofed), clearCourt=changed.meta.acs_apartment.courtyard.rect_m;
      const courtVoids=arch.voids.filter(v=>v.void_type==='COURTYARD');
      assert.deepEqual(courtVoids.map(v=>[v.level_index,v.rect,v.size_source,v.open_to_sky]),
        roofed.levels.map(l=>[l.index,clearCourt,'client_stated',true]));
      for(const element of [...arch.slabs,...arch.roofs]) {
        assert.equal(element.outline_basis,'bounding_box_minus_declared_voids');
        assert.ok(element.pieces.every(piece=>!overlaps(piece,clearCourt)),'slab or roof piece over the courtyard: '+element.id);
        assert.ok(near(element.pieces.reduce((a,p)=>a+p[2]*p[3],0),element.outline[2]*element.outline[3]-clearCourt[2]*clearCourt[3]));
      }
      const [detailed,,detailReason]=withContextDetails(roofed); assert.equal(detailReason,null);
      for(const level of detailed.levels) {
        const rooms=detailed.floors[level.template].rooms, clear=changed.meta.acs_apartment.courtyard.rect_m;
        assert.ok(rooms.every(room=>!overlaps(room.rect,clear)),'the actual generated roof/context must leave the courtyard open');
        const plate=pqPlateRect(rooms.map(room=>room.rect),[0,0,24,28]);
        assert.ok(plate.valid && plate.rectangles.length>1);
        assert.ok(plate.rectangles.every(rect=>!overlaps(rect,clear)),'the shipped slab union may not bridge the courtyard');
        for(const fx of [.05,.5,.95])for(const fz of [.05,.5,.95]) {
          const point=[clear[0]+clear[2]*fx,clear[1]+clear[3]*fz];
          assert.ok(!plate.rectangles.some(rect=>contains({rect},point)),'clear sky above each point in the courtyard');
        }
      }
      for(const connection of stairConnections(detailed)) {
        assert.ok(!overlaps(connection.opening,changed.meta.acs_apartment.courtyard.rect_m));
        assert.ok(!overlaps(connection.arrival,changed.meta.acs_apartment.courtyard.rect_m));
      }
      const noCourt=apartmentFromRevision('شيل الفناء',changed);
      const originalDirection=apartmentFromRevision('خل المدخل من '+direction,revisionBase);
      assert.deepEqual(noCourt.floors,originalDirection.floors,'removing a court restores the selected orientation without losing the source');
    }
  }
}
validate(apartmentFromBrief('عمارة سكنية ٢٠×٢٥ م من٣ أدوار، مدخل المبنى من الغرب'),20,25,3);
const lowCourt=apartmentFromBrief('عمارة سكنية٢٠×٢٥ م من٣ أدوار بارتفاع الدور٢٫٨ م، فناء مركزي مفتوح');
validate(lowCourt,20,25,3);
for(const request of [
  'خل المدخل من الجنوب واحذف غرفة نوم', 'خل المدخل من الجنوب وأضف دوراً خامساً',
  'خل المدخل من الجنوب وحافظ على جهة غرف النوم', 'خل المدخل من الجنوب مع بقاء الغرف في مواقعها',
  'خل وسط العمارة فناء مفتوح للسماء، مع المحافظة على جميع الجدران الحالية',
  'فناء وحافظ على أبعاد جميع الغرف', 'فناء وأبغى خمسة أدوار', 'خل المدخل في يمين الواجهة الشمالية', 'انقل السلم'
]) assert.throws(()=>apartmentFromRevision(request,revisionBase),error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED',request);
const roofedBase=withDefaultRoof(revisionBase)[0];
const roofRevision=apartmentFromRevision('خل المدخل من الجنوب',roofedBase);
assert.ok(carryAutoRoof(roofedBase,roofRevision).levels.some(level=>level.kind==='roof'),'normal automatic roof preference remains usable');
const editedRoof=structuredClone(roofedBase), roofLevel=editedRoof.levels.find(level=>level.kind==='roof');
editedRoof.floors[roofLevel.template].rooms[0].objects=[{id:'owner_roof_bench',kind:'box',x:1,z:1,w:1,d:.4,h:.4,rot:0}];
const editedSource=JSON.stringify(editedRoof);
assert.throws(()=>apartmentFromRevision('خل المدخل من الجنوب',editedRoof),error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED','manual roof descendants must not be discarded behind level.auto');
assert.equal(JSON.stringify(editedRoof),editedSource);
for(const [field,value] of Object.entries({
  mep:{systems:[{id:'owner_hvac',type:'HVAC',source:'engineer'}],equipment:[{id:'owner_ahu',type:'air_handling_unit',system_id:'owner_hvac',level:0,position:{x:2,y:0,z:2},dimensions:{w:1,d:1,h:1},source:'engineer'}]},
  structural:{columns:[{id:'owner_column',level:0,rect:[1,1,.4,.4],source:'engineer'}]},
  fire_life_safety:{routes:[{id:'owner_exit_route',level:0,points:[[1,1],[1,3]]}]},
  slab_t:.24
})) {
  const authored=structuredClone(roofedBase);authored[field]=value;
  const before=JSON.stringify(authored);
  assert.throws(()=>apartmentFromRevision('خل المدخل من الجنوب',authored),error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED',
    'regeneration must reject and preserve authored '+field);
  assert.equal(JSON.stringify(authored),before);
}
const annotated=structuredClone(revisionBase);annotated.meta.owner_note='مراجعة توزيع المدخل';
assert.equal(apartmentFromRevision('خل المدخل من الجنوب',annotated).meta.owner_note,annotated.meta.owner_note,
  'unrelated user metadata survives a supported revision');
assert.equal(JSON.stringify(revisionBase),revisionSource,'revision or failed requests may not mutate the source');

// Physical object placement follows the same rigid turn as the walls. Generate
// the matching pre-turn dimensions independently; inspect world centres and
// orientations rather than trusting the requested street_edge label.
const northModel=apartmentFromBrief('عمارة سكنية٢٨×٢٤ م من٣ أدوار، المدخل شمالي');
const westModel=apartmentFromBrief('عمارة سكنية٢٤×٢٨ م من٣ أدوار، المدخل غربي');
for(const level of northModel.levels) {
  const actual=westModel.floors[level.template].rooms;
  for(const room of northModel.floors[level.template].rooms) for(const obj of room.objects||[]) {
    const rotatedRoom=actual.find(item=>item.id===room.id), rotated=rotatedRoom.objects.find(item=>item.id===obj.id);
    assert.deepEqual([rotated.w,rotated.d,rotated.h],[obj.w,obj.d,obj.h]);
    assert.ok(near(rotatedRoom.rect[0]+rotated.x,room.rect[1]+obj.z));
    assert.ok(near(rotatedRoom.rect[1]+rotated.z,28-room.rect[0]-obj.x));
    assert.equal(rotated.rot,((obj.rot||0)+270)%360);
  }
}
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

// Saudi phrasing: floor counts that add the ground floor, listed floors, plot
// versus building, street width, number words and ambiguous decimals. Each was
// read silently as a different building before (agent 03-09 phrase set).
for(const [txt,w,d,n] of [
  ['عمارة سكنية ٢٤×٢٨ م، ثلاثة أدوار غير الأرضي، شقتين في كل دور',24,28,4],
  ['عمارة سكنية ٢٤×٢٨ م، ثلاث أدوار بدون الأرضي',24,28,4],
  ['عمارة سكنية ٢٤×٢٨ م، أرضي + دورين، شقتين بكل دور',24,28,3],
  ['عمارة سكنية ٢٤×٢٨ م، أرضي + ٣ أدوار',24,28,4],
  ['عمارة سكنية ٢٤×٢٨ م، أرضي وأول، شقتين بكل دور',24,28,2],
  ['عمارة سكنية ٢٤×٢٨ م، أرضي وأول وثاني وثالث، شقتين بكل دور',24,28,4],
  ['عمارة سكنية ٢٤×٢٨ م، عدد الأدوار أربعة، شقتين في كل دور',24,28,4],
  ['عمارة سكنية ٢٤×٢٨ م، ثلاث أدوار والأرضي، شقتين بكل دور',24,28,4],
  ['عمارة سكنية واجهتها ٢٢ متر وطولها ٢٦ متر، ثلاث أدوار، شقتين بكل دور',22,26,3],
  ['عمارة سكنية ٢٤×٢٨ على شارع عرضه ١٥ متر من الشمال، ثلاث أدوار',24,28,3],
  ['عمارة سكنية ٢٤×٢٨، أربع أدوار، كل دور فيه شقتين، والمجموع ثمان شقق',24,28,4]
]) validate(apartmentFromBrief(txt),w,d,n);
assert.equal(apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ٣ أدوار، شقتين بكل دور، واجهتها جنوبية').meta.acs_apartment.street_edge,'S');
assert.equal(apartmentFromBrief('عمارة سكنية ٢٤×٢٨ على شارع عرضه ١٥ متر من الجنوب، ثلاث أدوار').meta.acs_apartment.street_edge,'S');
for(const txt of ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، كل دور فيها شقتين','عمارة سكنية ٢٤×٢٨، أرضي وأول وثاني شقق، ومواقف أمامية','عمارة سكنية ٢٤×٢٨، عدد الأدوار ٣ شاملة الأرضي'])
  validate(apartmentFromBrief(txt),24,28,3);
for(const [txt,reason] of [
  ['عمارة سكنية على قطعة ٢٠×٣٠، ثلاث أدوار، شقتين في كل دور','الأرض'],
  ['أبغى عمارة سكنية في أرض صكها ٢٠ في ٣٠ متر، ثلاث أدوار','الأرض'],
  ['أبغى عمارة سكنية مقاسها عشرين في خمسة وعشرين متر، ثلاث أدوار، شقتين بكل دور','بالأرقام'],
  ['عمارة سكنية عرض المبنى 22,5 م وعمقه 26 م، 3 أدوار','بفاصلة'],
  ['عمارة سكنية ٢٤×٢٨ م، ثلاث أدوار فيها تسع شقق','9 شقق'],
  ['عمارة سكنية ٢٤×٢٨، ثلاث أدوار، شقتين في كل دور، والمجموع عشر شقق','10 شقق'],
  ['عمارة سكنية ٢٤×٢٨ م فيها ٤ شقق','4 شقق'],
  ['عمارة تجارية سكنية ٢٤×٢٨، الأرضي محلات وفوقه دورين شقق','تجاري'],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، الأرضي مواقف سيارات والشقق فوق','مواقف'],
  ['عمارة سكنية ٢٤×٢٨ م فيها ٤ شقق، ثلاث أدوار','4 شقق']
]) assert.throws(()=>apartmentFromBrief(txt),
  error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED'&&error.message.includes(reason),txt);
for(const txt of ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، بدون ملحق ولا منور','عمارة سكنية ٢٠×٢٥، أرضي ودورين وسطح، شقتين بكل دور'])
  assert.ok(apartmentFromBrief(txt),'an excluded or default-roof feature does not block the plan: '+txt);
// Missing building size or floors is asked, never filled from a prefilled default (owner decision 1).
for(const [txt,missing,phrase] of [
  ['أبغى عمارة سكنية',['width','depth','levels'],'كم عرض المبنى وعمقه بالمتر، وكم عدد أدواره شاملة الأرضي؟'],
  ['أبغى عمارة سكنية ٣ أدوار، شقتين بكل دور',['width','depth'],'كم عرض المبنى وعمقه'],
  ['أبغى عمارة سكنية عرضها ٢٤ متر، ٣ أدوار',['depth'],'كم عمق المبنى'],
  ['عمارة سكنية عمقها ٢٨ متر، أربعة أدوار',['width'],'كم عرض المبنى'],
  ['عمارة سكنية على قطعة ٢٠×٣٠، ثلاث أدوار، شقتين في كل دور',['width','depth'],'بعد الارتدادات'],
  ['عمارة سكنية ٢٤×٢٨ م فيها ٤ شقق',['levels'],'كم عدد الأدوار شاملة الأرضي']
]) assert.throws(()=>apartmentFromBrief(txt),error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED'&&error.question===true&&
  JSON.stringify(error.missing)===JSON.stringify(missing)&&error.message.includes(phrase),txt);
// A refusal still comes before a question.
assert.throws(()=>apartmentFromBrief('عمارة سكنية لها قبو'),error=>!error.question&&error.message.includes('قبو'));
assert.throws(()=>apartmentFromBrief('عمارة سكنية ثمانية أدوار'),error=>!error.question&&error.message.includes('ستة أدوار'));
// Form values are the visitor's own: they complete a brief, a disagreement is asked.
validate(apartmentFromBrief('عمارة سكنية، شقتين في كل دور',{width:'20',depth:'25',levels:'3'}),20,25,3);
for(const blank of [{},{width:'',depth:'',levels:''},{width:0,depth:null,levels:undefined}])
  assert.throws(()=>apartmentFromBrief('عمارة سكنية',blank),error=>error.question===true,'empty fields are not values');
// Text and field disagree: never settled silently. Every disagreement is offered; the visitor's pick is used.
assert.throws(()=>apartmentFromBrief('عمارة سكنية ٢٠×٢٥ م، ٣ أدوار',{width:30,levels:4}),error=>error.question===true&&
  JSON.stringify(error.conflicts.map(c=>[c.key,c.text,c.form]))===JSON.stringify([['width',20,30],['levels',3,4]])&&error.message.includes('في الوصف 20 م، وفي الحقل 30 م'));
let picked=apartmentFromBrief('عمارة سكنية ٢٤×٢٨ م، ٣ أدوار',{levels:4,prefer:{levels:'form'}});
validate(picked,24,28,4);
assert.match(apartmentConfirmation(picked).rows.find(row=>row.key==='levels').note,/اخترتَه حين اختلف الوصف عن الحقل/);
validate(apartmentFromBrief('عمارة سكنية ٢٤×٢٨ م، ٣ أدوار',{levels:4,prefer:{levels:'text'}}),24,28,3);
assert.throws(()=>apartmentFromBrief('عمارة سكنية ٢٤×٢٨ م، ٣ أدوار',{levels:4,prefer:{levels:'other'}}),error=>error.conflicts?.length===1,'only text or form is a pick');
assert.throws(()=>apartmentFromBrief('عمارة سكنية على أرض ٢٥×٣٠ م، والمبنى ٢٠×٢٥ م، ثلاث أدوار',{plotWidth:26,plotDepth:30}),
  error=>JSON.stringify(error.conflicts.map(c=>[c.key,c.text,c.form]))===JSON.stringify([['plot','25 × 30','26 × 30']]));
assert.deepEqual(apartmentFromBrief('عمارة سكنية على أرض ٢٥×٣٠ م، والمبنى ٢٠×٢٥ م، ثلاث أدوار',{plotWidth:26,plotDepth:30,prefer:{plot:'form'}})
  .meta.acs_apartment.understanding.plot,{w:26,d:30,source:'form'});
// Round 2 phrasing (independent check): ground floor added, and the deed is the plot.
for(const txt of ['عمارة سكنية ٢٤×٢٨ م، ثلاثة أدوار بالإضافة للأرضي، شقتين في كل دور','عمارة سكنية ٢٤×٢٨ م مكونة من ٣ أدوار والأرضي، شقتين في كل دور',
  'عمارة سكنية ٢٤×٢٨ م، ثلاثة أدوار علاوة على الدور الأرضي'])
  validate(apartmentFromBrief(txt),24,28,4);
assert.throws(()=>apartmentFromBrief('عمارة سكنية، الصك ٢٠×٣٠ م، ثلاث أدوار'),error=>error.question===true&&error.message.includes('ذكرت الأرض فقط'));
validate(apartmentFromBrief('عمارة سكنية، الصك ٢٥×٣٠ م، ثلاث أدوار',{width:20,depth:25}),20,25,3);
// Requests the local generator cannot honour are listed before drawing, never dropped (owner, round 2).
const listed=apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ٣ أدوار، شقتين في كل دور، كل شقة فيها أربع غرف نوم ومجلس حريم، مع منور وملحق علوي وغرفة خادمة');
validate(listed,24,28,3);
assert.deepEqual(listed.meta.acs_apartment.understanding.not_drawn.map(item=>item.key),['bedrooms','lightwell','annex','ladies_majlis','staff_room']);
const listedCard=apartmentConfirmation(listed);
assert.equal(listedCard.notDrawn.length,5);assert.match(listedCard.notDrawn[0],/طلبت 4، ويرسم المخطط المحلي 3/);
assert.ok(listed.meta.acs_apartment.assumptions.some(line=>line.startsWith('لم يُرسم لأنه غير مدعوم في المولّد المحلي بعد')));
for(const txt of ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، شقتين بكل دور، كل شقة غرفتين نوم','عمارة سكنية ٢٤×٢٨، ٣ أدوار، أربع غرف نوم'])
  assert.deepEqual(apartmentFromBrief(txt).meta.acs_apartment.understanding.not_drawn.map(item=>item.key),['bedrooms'],txt);
for(const txt of ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، بدون ملحق ولا منور ولا مجلس حريم','عمارة سكنية ٢٤×٢٨، ٣ أدوار، كل شقة ثلاث غرف نوم'])
  assert.deepEqual(apartmentFromBrief(txt).meta.acs_apartment.understanding.not_drawn,[],txt);
// Round 3: elevator, usable roof and separate entrances are listed, and any recognised
// requirement word the local plan does not represent is reported as not applied.
for(const [txt,keys] of [
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، بدون مصعد',['no_elevator']],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، مصعدين',['two_elevators']],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، سطح مستخدم',['usable_roof']],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، مدخل منفصل لكل شقة',['separate_entrances']],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، ومواقف أمامية وارتداد ٣ م',['unmapped']],
  ['عمارة سكنية ٢٤×٢٨، ٣ أدوار، بدون مواقف',[]]
]) assert.deepEqual(apartmentFromBrief(txt).meta.acs_apartment.understanding.not_drawn.map(item=>item.key),keys,txt);
assert.match(apartmentConfirmation(apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ٣ أدوار، ومواقف أمامية وارتداد ٣ م')).notDrawn[0],/لم يُطبَّق: مواقف السيارات، الارتدادات/);
assert.throws(()=>apartmentFromRevision('خل المدخل من الجنوب والمواقف قدام',apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ٣ أدوار')),
  error=>error.message.includes('مواقف السيارات'),'a revision cannot drop an unmapped request');
// «ثلاث أدوار مع الأرضي» states the ground floor: not an assumption.
const withGround=Object.fromEntries(apartmentConfirmation(apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ثلاث أدوار مع الأرضي، شقتين في كل دور')).rows.map(row=>[row.key,row]));
assert.equal(withGround.levels.note,'شاملة الأرضي كما ذكرت');assert.equal(withGround.levels.assumed,false);assert.equal(withGround.levels.value,'3 أدوار: الأرضي ودوران فوقه');
assert.equal(apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ثلاثة أدوار شاملة للأرضي').meta.acs_apartment.understanding.levels.ground,'stated_inclusive');
assert.throws(()=>apartmentFromRevision('خل المدخل من الجنوب ومنور في النص',apartmentFromBrief('عمارة سكنية ٢٤×٢٨، ٣ أدوار')),
  error=>error.message.includes('منور'),'a revision has no card, so it still refuses');
// Plot and building are separate (owner decision 3): plot 25×30 with building 20×25 draws 20×25.
for(const [txt,form] of [
  ['عمارة سكنية على أرض ٢٥×٣٠ م، والمبنى ٢٠×٢٥ م، ثلاث أدوار',{}],
  ['عندي قطعة أرض ٢٥×٣٠ م، أبغى عليها عمارة سكنية أبعادها ٢٠×٢٥، ثلاث أدوار',{}],
  ['عمارة سكنية على قطعة ٢٥×٣٠، ثلاث أدوار',{width:20,depth:25}],
  ['عمارة سكنية، ثلاث أدوار',{width:20,depth:25,plotWidth:25,plotDepth:30}]
]) {
  const model=apartmentFromBrief(txt,form);validate(model,20,25,3);
  assert.deepEqual(model.meta.acs_apartment.understanding.plot,{w:25,d:30,source:form.plotWidth?'form':'text'},txt);
  assert.deepEqual(apartmentConfirmation(model).rows.find(row=>row.key==='plot').value,'25 × 30 م',txt);
}
assert.throws(()=>apartmentFromBrief('عمارة سكنية، ثلاث أدوار',{width:26,depth:25,plotWidth:25,plotDepth:30}),error=>error.message.includes('أكبر من الأرض'));
// The confirmation card says how the ground floor was counted and marks every assumption.
const cardOf=(txt,form)=>Object.fromEntries(apartmentConfirmation(apartmentFromBrief(txt,form)).rows.map(row=>[row.key,row]));
let card=cardOf('عمارة سكنية ٢٤×٢٨ م، ثلاثة أدوار غير الأرضي، شقتين في كل دور');
assert.equal(card.levels.value,'4 أدوار: الأرضي و3 أدوار فوقه');assert.equal(card.levels.note,'أضفنا الأرضي إلى العدد الذي ذكرته');assert.equal(card.levels.assumed,false);
assert.equal(card.building.value,'عرض 24 م × عمق 28 م');assert.equal(card.plot,undefined);
assert.equal(card.units.assumed,false);assert.equal(card.entrance.assumed,true);assert.equal(card.entrance.value,'من الشمال');assert.equal(card.courtyard.value,'لا يوجد');
card=cardOf('أبغى عمارة سكنية، عرض المبنى ٢٠ متر وعمقه ٢٥ متر، ثلاثة أدوار، والمدخل جنوبي، وبوسطها فناء مفتوح');
assert.equal(card.levels.assumed,true,'a count that does not mention the ground floor is read as including it, and says so');
assert.equal(card.entrance.assumed,false);assert.equal(card.entrance.value,'من الجنوب');
assert.equal(card.units.assumed,true);assert.equal(card.courtyard.assumed,true);assert.equal(card.courtyard.value,'فناء مفتوح للسماء 4 × 5 م');
card=cardOf('عمارة سكنية، شقتين في كل دور',{width:20,depth:25,levels:2});
assert.equal(card.levels.note,'من حقل عدد الأدوار (شاملة الأرضي)');assert.equal(card.building.note,'من الحقول');assert.equal(card.levels.value,'دوران: الأرضي ودور واحد فوقه');
assert.equal(apartmentConfirmation(apartmentSample()),null,'the shipped sample is not a confirmed brief');
// Reference case 4 wording, and Saudi imperatives that must not be dropped from a revision.
const saudiBase=apartmentFromBrief('عمارة سكنية مقاس المبنى ٢٢ في ٢٦ متر، أرضي ودورين، كل دور فيه شقتين');
const east=apartmentFromRevision('غيّر المدخل وخله من الشرق',saudiBase);
validate(east,22,26,3);assert.equal(east.meta.acs_apartment.street_edge,'E');
assert.ok(!east.meta.acs_apartment.assumptions.some(line=>line.startsWith('لم تحدد جهة المدخل')),'a chosen entrance is no longer an assumption');
for(const request of ['خل المدخل من الجنوب وزيد دور','خل المدخل جنوبي وضيف دور ثالث فوق','خل المدخل من الجنوب ونقص شقة'])
  assert.throws(()=>apartmentFromRevision(request,saudiBase),error=>error.code==='LOCAL_APARTMENT_UNSUPPORTED'&&error.message.includes('افصل'),request);
assert.equal(JSON.stringify(sample),original,'other local creations leave existing drafts untouched');
console.log('PASS local apartment: four Arabic briefs, physical cardinal entries, open courtyard and roof, shared circulation, paired apertures, stairs, immutable default source and guarded revisions');
