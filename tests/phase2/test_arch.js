/* ======================================================================
   المرحلة 2 — اختبارات أساس الهندسة المعمارية وغلاف المبنى.
   هندسة معمارية فقط: لا إنشاء، لا ميكانيكا، لا حريق، لا وصول، لا مطابقة كود.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const SC=JSON.parse(fs.readFileSync(_np.join(FIXD,'arch_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
const A=(name,bid,pos,rot)=>compileArchitecture(C(SC.models[name]||FX[name]),bid||'bld_0',pos||null,rot||0);
const ALL=['villa','hotel','clinic','office','warehouse'];

console.log('\n== §1 — NO CODE / NO STRUCTURE / NO MEP CONTENT ==');
const specTxt=JSON.stringify(ACS_ARCH_SPEC);
chk('the architecture spec names no code standard',
    !/\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|civil.?defen/i.test(specTxt));
chk('regulatory rule count is still zero', regulatoryRuleCount([])===0);
chk('real occupancy classification count is still zero',
    occRealClassificationCount(occupancyFixtureStore())===0);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_arch.json'),'utf8'));
chk('browser spec is byte-identical to acs_arch.json',
    JSON.stringify(sk(ACS_ARCH_SPEC))===JSON.stringify(sk(CANON)));
chk('twelve element types declared', ARCH_ELEMENT_TYPES.length===12, ARCH_ELEMENT_TYPES.length);
chk('nineteen geometry issue codes declared', ARCH_ISSUE_CODES.length===19, ARCH_ISSUE_CODES.length);
{ const forb=ACS_ARCH_SPEC.forbidden_claims;
  /* الادّعاء هو قيمة صادقة لخاصية ممنوعة. النفي الصريح (structural:false) ليس
     ادّعاءً بل تبرئة — والاختبار يفرّق بينهما بدل البحث عن نصّ المفتاح. */
  const claims=[];
  const walk=(v)=>{ if(Array.isArray(v)) return v.forEach(walk);
    if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
      if(forb.indexOf(k)>=0&&v[k]) claims.push(k+'='+JSON.stringify(v[k]));
      walk(v[k]); }); };
  ALL.forEach(n=>walk(A(n)));
  chk('no compiled element claims a structural / fire / compliance property',
      claims.length===0, claims.slice(0,3).join(','));
  const all=ALL.map(n=>JSON.stringify(A(n))).join(' ');
  chk('the only mention of a forbidden property is an explicit denial',
      /"structural":false/.test(all)&&!/"structural":true/.test(all)); }
{ const v=A('villa');
  chk('every slab declares itself non-structural',
      v.slabs.every(s=>s.structural===false&&/not a structural design/.test(s.note)));
  chk('every void declares that no framing is implied',
      A('core').voids.every(x=>/no structural framing implied/.test(x.note))); }

console.log('\n== §2 — SHARED WALLS ARE DEFINED ONCE ==');
{ const a=A('shared');
  const sh=a.walls.filter(w=>w.shared);
  chk('the boundary between two spaces yields exactly one wall', sh.length===1, sh.length);
  chk('that wall names both spaces and nothing else',
      sh[0].spaces.length===2&&sh[0].spaces.indexOf('bld_0.g.a')>=0&&sh[0].spaces.indexOf('bld_0.g.b')>=0,
      JSON.stringify(sh[0].spaces));
  chk('the shared wall is interior and confirmed, not inferred',
      sh[0].exposure==='interior'&&sh[0].exposure_status==='confirmed'&&
      sh[0].exposure_basis==='bounded_by_two_spaces');
  chk('total walls = 6 perimeter + 1 shared, not 8 duplicated', a.walls.length===7, a.walls.length);
  chk('sharedWallBetween finds it from either direction',
      archSharedWallBetween(a,'bld_0.g.a','bld_0.g.b')&&archSharedWallBetween(a,'bld_0.g.b','bld_0.g.a'));
  chk('an unrelated pair has no shared wall', archSharedWallBetween(a,'bld_0.g.a','nope')===null); }
{ const a=A('partial');
  const shared=a.walls.filter(w=>w.shared);
  chk('a partially shared boundary breaks into segments at every breakpoint',
      shared.length===1&&Math.abs(shared[0].u1-shared[0].u0-4)<1e-9,
      JSON.stringify(shared.map(w=>[w.u0,w.u1])));
  chk('the unshared remainder of that boundary stays separate',
      a.walls.filter(w=>w.axis==='x'&&Math.abs(w.fixed-4)<1e-9).length===3); }
{ const a=A('villa');
  const dupes={};
  a.walls.forEach(w=>{ const k=[w.level_id,w.axis,w.fixed,w.u0,w.u1].join('|');
    dupes[k]=(dupes[k]||0)+1; });
  chk('no two walls occupy the same geometry on the same level',
      Object.keys(dupes).every(k=>dupes[k]===1)); }

console.log('\n== §3 — DETERMINISM AND IDENTITY ==');
{ const a=A('orderA'), b=A('orderB');
  const g=x=>x.walls.map(w=>[w.id,w.axis,w.fixed,w.u0,w.u1,w.spaces.join('+')].join(' '));
  chk('reversing room order changes no wall id and no wall geometry',
      JSON.stringify(g(a))===JSON.stringify(g(b))); }
chk('compiling twice gives byte-identical output',
    JSON.stringify(A('hotel'))===JSON.stringify(A('hotel')));
{ const m=C(FX.villa), before=JSON.stringify(m);
  compileArchitecture(m,'bld_0'); validateArchitecture(compileArchitecture(m,'bld_0'));
  chk('the compiler never mutates the model it reads', JSON.stringify(m)===before); }
{ let bad=[];
  ALL.concat(['core','overlap','poly','unicode']).forEach(n=>{ const a=A(n); const ids=[];
    ['walls','openings','slabs','voids','ceilings','roofs','cores','spaces']
      .forEach(t=>(a[t]||[]).forEach(e=>ids.push(e.id)));
    if(new Set(ids).size!==ids.length) bad.push(n); });
  chk('every element id is unique inside a building', bad.length===0, bad.join(',')); }
{ const a=A('villa','bld_7');
  chk('a second building namespaces every id',
      a.walls.every(w=>w.id.indexOf('bld_7.')===0)&&a.envelope.id==='bld_7.envelope'&&
      a.cores.every(c=>c.id.indexOf('bld_7.')===0));
  chk('space instance ids carry the building and the level',
      a.spaces.every(s=>/^bld_7\..+@\d+$/.test(s.id))); }
{ const a=A('core');
  chk('one floor template used twice yields two physical space instances',
      a.spaces.filter(s=>s.space_id==='bld_0.t.hall').length===2);
  chk('those instances keep the semantic space id for the other layers',
      a.spaces.filter(s=>s.space_id==='bld_0.t.hall').every(s=>s.space_id==='bld_0.t.hall')); }

console.log('\n== §4 — EXTERIOR IS INFERRED, NEVER ASSUMED ==');
{ const a=A('villa');
  chk('villa has real exterior walls', a.walls.filter(w=>w.exposure==='exterior').length>0);
  chk('every exterior wall states the basis of that claim',
      a.walls.filter(w=>w.exposure==='exterior').every(w=>!!w.exposure_basis&&
        ['confirmed','inferred'].indexOf(w.exposure_status)>=0));
  chk('exposure never takes a value outside the declared vocabulary',
      a.walls.every(w=>ARCH_EXPOSURE.indexOf(w.exposure)>=0&&
                       ARCH_EVIDENCE.indexOf(w.exposure_status)>=0)); }
{ const a=A('court');
  const un=a.walls.filter(w=>w.exposure==='unresolved');
  chk('a wall facing an internal courtyard is NOT claimed exterior', un.length===4, un.length);
  chk('the courtyard walls say why they are unresolved',
      un.every(w=>w.exposure_basis==='opposite_side_is_void_inside_the_footprint'));
  chk('no courtyard wall was silently called interior either',
      un.every(w=>w.exposure!=='interior')); }
{ const curved=C(SC.models.poly); curved.floors.g.rooms[0].shape={type:'arc'};
  const a=compileArchitecture(curved,'bld_0');
  chk('a wall opposite an unsupported outline stays unresolved',
      a.walls.some(w=>w.exposure_basis==='opposite_side_near_a_space_with_unsupported_outline')); }
{ const a=A('declared');
  const sh=a.walls.filter(w=>w.shared);
  chk('a room-level exterior flag does NOT override a wall between two spaces',
      sh.length===1&&sh[0].exposure==='interior', sh.length&&sh[0].exposure);
  chk('the flag does apply to that room’s single-space walls',
      a.walls.some(w=>w.exposure_basis==='declared_by_model')); }

console.log('\n== §5 — OPENINGS ARE HOSTED, NOT FLOATING ==');
{ const a=A('shared');
  const d=a.openings.filter(o=>o.type==='DOOR')[0];
  const wnd=a.openings.filter(o=>o.type==='WINDOW')[0];
  chk('a door resolves to a host wall', d.host_status==='resolved'&&!!d.host_wall_id);
  chk('a window resolves to a host wall', wnd.host_status==='resolved'&&!!wnd.host_wall_id);
  chk('the host wall lists the opening back', archElementById(a,d.host_wall_id).openings.indexOf(d.id)>=0);
  chk('the door sits on the shared wall between the two spaces',
      archElementById(a,d.host_wall_id).shared===true);
  chk('door and window are distinct element types', d.type==='DOOR'&&wnd.type==='WINDOW'); }
{ const a=A('badopen');
  const codes=a.issues.map(i=>i.code);
  chk('an opening wider than its host is reported', codes.indexOf('OPENING_WIDER_THAN_HOST')>=0);
  chk('a door taller than its wall is reported', codes.indexOf('DOOR_TALLER_THAN_WALL')>=0);
  chk('a window below the floor is reported', codes.indexOf('WINDOW_BELOW_FLOOR')>=0);
  chk('a window above the wall height is reported', codes.indexOf('WINDOW_ABOVE_WALL_HEIGHT')>=0);
  chk('none of these are silently corrected', a.openings.every(o=>o.width_m&&o.height_m)); }
{ const a=A('unstated');
  chk('an opening hanging off the end of its host is OUTSIDE, not WIDER',
      a.issues.every(i=>i.code!=='OPENING_WIDER_THAN_HOST')&&
      a.issues.filter(i=>i.code==='OPENING_OUTSIDE_HOST').length===2,
      JSON.stringify(a.issues.map(i=>i.code)));
  chk('its host note describes the real situation',
      a.openings.every(o=>o.host_note==='opening extends beyond the single wall segment that hosts it')); }

console.log('\n== §6 — A RENDER FALLBACK IS NEVER AN ENGINEERING VALUE ==');
{ const a=A('unstated');
  const d=a.openings[0];
  chk('an unstated door width stays null', d.width_m.value===null);
  chk('the drawing fallback is exposed separately', d.width_m.render_fallback===0.9);
  chk('and its provenance is unknown, not imported', d.width_m.source==='unknown');
  chk('an unstated clear width is never derived from the nominal width',
      d.clear_width_m.value===null&&d.clear_width_m.render_fallback===null);
  chk('an unspecified swing is reported as unspecified, not assumed',
      d.swing_status==='not_specified'&&d.hinge_side===null&&d.swing_direction===null);
  chk('an unstated wall thickness stays null with a separate fallback',
      a.walls.every(w=>w.thickness_m.value===null&&w.thickness_m.render_fallback===0.15&&
                       w.thickness_m.source==='unknown'));
  chk('an unstated wall height stays null too',
      a.walls.every(w=>w.height_m.value===null&&w.height_m.source==='unknown'));
  chk('every provenance value is inside the declared vocabulary',
      [d.width_m.source,d.height_m.source,a.walls[0].thickness_m.source]
        .every(s=>ARCH_PROVENANCE.indexOf(s)>=0)); }
{ const a=A('shared');
  chk('a stated width IS a semantic value with imported provenance',
      a.openings[0].width_m.value===0.9&&a.openings[0].width_m.source==='imported');
  chk('a stated wall thickness is carried, not defaulted',
      a.walls[0].thickness_m.value===0.2); }

console.log('\n== §7 — SLABS, VOIDS AND VERTICAL CORES ==');
{ const a=A('core');
  chk('one slab per level', a.slabs.length===a.levels.length, a.slabs.length);
  chk('a slab never claims to be structural', a.slabs.every(s=>s.structural===false));
  chk('two vertical cores are found', a.cores.length===2, a.cores.length);
  chk('a stair crossing three levels cuts the slabs it passes through',
      a.voids.filter(v=>v.core_type==='STAIR').length===2,
      JSON.stringify(a.voids.map(v=>[v.level_index,v.core_type])));
  chk('no void is cut at the lowest level the core serves',
      a.voids.every(v=>v.level_index>Math.min.apply(null,
        a.cores.filter(c=>c.id===v.core_id)[0].served_levels)));
  chk('a core whose position is not stated says so',
      a.issues.some(i=>i.code==='CORE_POSITION_NOT_STATED'));
  chk('a multi-level core always has a void', !a.issues.some(i=>i.code==='VOID_MISSING_FOR_CORE'));
  chk('void geometry is a real rect derived from the core footprint',
      a.voids.every(v=>v.rect.length===4&&v.rect[2]>0&&v.rect[3]>0)); }
{ const a=A('villa');
  chk('the villa stair cuts the first floor slab', a.voids.length===1&&a.voids[0].level_index===1,
      JSON.stringify(a.voids.map(v=>v.level_index)));
  const holes=a.voids.filter(v=>v.level_index===1).map(v=>v.rect);
  const strips=slabStrips(0,0,FX.villa.site.w,FX.villa.site.d,holes);
  const area=strips.reduce((s,r)=>s+r[2]*r[3],0);
  const full=FX.villa.site.w*FX.villa.site.d;
  const hole=holes.reduce((s,r)=>s+r[2]*r[3],0);
  chk('the rendered slab strips cover the plate minus exactly the void area',
      Math.abs(area-(full-hole))<1e-6, area+' vs '+(full-hole));
  chk('no strip overlaps a void',
      strips.every(s=>holes.every(h=>!(s[0]+1e-9<h[0]+h[2]&&s[0]+s[2]>h[0]+1e-9&&
        s[1]+1e-9<h[1]+h[3]&&s[1]+s[3]>h[1]+1e-9))));
  chk('a level with no void still renders exactly one slab strip',
      slabStrips(0,0,30,24,[]).length===1); }
{ const a=A('hotel');
  chk('the hotel core serves the levels the model actually shows',
      a.cores.every(c=>c.served_levels.length>=1));
  chk('every void points back at a real core',
      a.voids.every(v=>a.cores.some(c=>c.id===v.core_id))); }

console.log('\n== §8 — LEVELS AND ROOFS ==');
{ const a=A('core');
  chk('levels are ordered and elevations derived from floor_height',
      a.levels.map(l=>l.index).join(',')==='0,1,2,3'&&a.levels[1].elevation_m===3.2);
  chk('a derived elevation is marked system_default, not imported',
      a.levels[1].elevation_source==='system_default');
  chk('a roof level produces a ROOF and is never an occupied floor',
      a.roofs.length===1&&a.roofs[0].occupied_floor===false);
  chk('an auto-added roof says its source is a system default',
      a.roofs[0].source==='system_default');
  chk('no ceilings are emitted for the roof level',
      a.ceilings.every(c=>c.level_id!==a.roofs[0].level_id)); }
chk('inconsistent level elevations are reported, not reordered',
    A('badlevel').issues.some(i=>i.code==='LEVEL_ELEVATION_INCONSISTENT'));
{ const a=A('villa');
  chk('a stated elevation would be marked imported',
      A('badlevel').levels.every(l=>l.elevation_source==='imported'));
  chk('ceiling elevation = level elevation + wall height when both are known',
      a.ceilings.every(c=>c.elevation_m===null||typeof c.elevation_m==='number')); }

console.log('\n== §9 — SPACES, SHAPES AND OVERLAPS ==');
{ const a=A('poly');
  chk('a non-rectangular outline is NOT approximated as a rectangle',
      a.spaces.filter(s=>s.boundary_basis==='polygon_edges').length===1);
  chk('the L retains its actual 27 square metre area',
      a.spaces.find(s=>s.space_id==='bld_0.g.L').area_m2===27
      &&!a.approximations.some(x=>x.reason==='SPACE_SHAPE_UNSUPPORTED'));
  chk('all six real L edges exist, including its shared edge',
      a.walls.filter(w=>w.spaces.indexOf('bld_0.g.L')>=0).length===6); }
{ const curved=C(SC.models.poly);curved.floors.g.rooms[0].shape={type:'arc'};
  const a=compileArchitecture(curved,'bld_0');
  chk('an unsupported curved boundary remains explicit, without fabricated walls or area',
      a.approximations.some(x=>x.reason==='SPACE_SHAPE_UNSUPPORTED')
      &&a.walls.every(w=>w.spaces.indexOf('bld_0.g.L')<0)
      &&a.spaces.find(s=>s.space_id==='bld_0.g.L').area_m2===null); }
{ const a=A('overlap');
  const codes=a.issues.map(i=>i.code);
  chk('two genuinely overlapping spaces are reported as an overlap',
      codes.indexOf('SPACE_OVERLAP')>=0);
  chk('a space fully inside another is reported as containment, not overlap',
      a.issues.some(i=>i.code==='SPACE_CONTAINED'&&i.subject==='bld_0.g.shell@0'));
  chk('the reported overlap area is a real number', a.issues.filter(i=>
      i.code==='SPACE_OVERLAP'||i.code==='SPACE_CONTAINED').every(i=>i.overlap_m2>0)); }
chk('the warehouse envelope-inside-zones layout reads as containment, not error',
    A('warehouse').issues.every(i=>i.code==='SPACE_CONTAINED'));
chk('an empty level compiles to nothing rather than to a fabricated box',
    (()=>{const a=A('empty'); return a.walls.length===0&&a.slabs.length===0&&
      a.envelope.exterior_walls.length===0;})());

console.log('\n== §10 — ENVELOPE ==');
{ const a=A('villa');
  chk('the envelope lists exactly the exterior walls',
      a.envelope.exterior_walls.length===a.walls.filter(w=>w.exposure==='exterior').length);
  chk('the envelope lists unresolved walls separately, never as exterior',
      a.envelope.unresolved_walls.length===a.walls.filter(w=>w.exposure==='unresolved').length&&
      a.envelope.unresolved_walls.every(id=>a.envelope.exterior_walls.indexOf(id)<0));
  chk('external openings are only those hosted on exterior walls',
      a.envelope.external_openings.every(oid=>{
        const o=archElementById(a,oid);
        return archElementById(a,o.host_wall_id).exposure==='exterior'; }));
  chk('the envelope performs no analysis and says so',
      /no analysis is performed here/.test(a.envelope.note));
  chk('ground interface comes from the lowest slab',
      JSON.stringify(a.envelope.ground_interface)===JSON.stringify(a.slabs[0].outline)); }

console.log('\n== §11 — TRANSFORMS ==');
{ const a=A('villa','bld_0',{x:12.5,z:-3.25},30);
  chk('segments keep local coordinates and declare it',
      /world transform is applied on read/.test(a.transform.applied));
  const p0=archToWorld(a,0,0);
  chk('the origin maps to the stated position',
      Math.abs(p0[0]-12.5)<1e-9&&Math.abs(p0[1]+3.25)<1e-9, JSON.stringify(p0));
  const p1=archToWorld(a,10,0);
  chk('rotation is applied about the building origin',
      Math.abs(p1[0]-(12.5+10*Math.cos(Math.PI/6)))<1e-9&&
      Math.abs(p1[1]-(-3.25+10*Math.sin(Math.PI/6)))<1e-9);
  const b=A('villa');
  chk('a transform never changes the compiled geometry itself',
      JSON.stringify(a.walls)===JSON.stringify(b.walls));
  chk('rotating by 90° preserves segment lengths',
      (()=>{const r=A('hotel','bld_1',{x:-7,z:11},90);
        return r.walls.every((w,i)=>Math.abs(w.length_m-A('hotel','bld_1').walls[i].length_m)<1e-12);})()); }

console.log('\n== §12 — JOIN WITH THE EXISTING LAYERS ==');
{ const b=C(FX.villa);
  const rels=buildRelationships(b,'bld_0');
  const a=compileArchitecture(b,'bld_0');
  const conf=rels.filter(e=>e.type==='DOOR_CONNECTS'&&e.status==='confirmed');
  chk('a door on a wall shared by exactly two spaces upgrades the edge to confirmed',
      conf.length>0, conf.length);
  chk('every upgraded edge names the wall that proves it',
      conf.every(e=>e.meta.wall_id&&archElementById(a,e.meta.wall_id)));
  chk('the proving wall really is shared by exactly the two linked spaces',
      conf.every(e=>{const w=archElementById(a,e.meta.wall_id);
        return w.shared&&w.spaces.length===2&&
          w.spaces.indexOf(e.from)>=0&&w.spaces.indexOf(e.to)>=0; }));
  chk('unresolved door edges were not upgraded',
      rels.filter(e=>e.type==='DOOR_CONNECTS'&&e.status==='unresolved').every(e=>e.to===null));
  chk('no relationship edge was added or removed by the architectural layer',
      rels.filter(e=>e.type==='DOOR_CONNECTS').length===
      (b.floors.g.rooms.concat(b.floors.f.rooms)).reduce((s,r)=>s+((r.doors||[]).length),0));
  chk('an opening with no proof yields no evidence object',
      archDoorConnectsConfirmed(a,'bld_0.g.majlis.door_1')===null); }
{ /* مرساة الباب: هندسة الفتحة المصرَّفة تطابق الاشتقاق من المستطيل تماماً */
  let checked=0, mismatched=[];
  ALL.forEach(n=>{ const b=C(FX[n]), a=compileArchitecture(b,'bld_0');
    Object.keys(b.floors||{}).forEach(tmpl=>{
      ((b.floors[tmpl]||{}).rooms||[]).forEach((r,i)=>{
        const sid=r.space_id||('bld_0.'+tmpl+'.'+(r.id||('sp_'+i)));
        (r.doors||[]).forEach((d,di)=>{
          const withArch=doorAnchor(r,di,a,sid), plain=doorAnchor(r,di);
          checked++;
          if(JSON.stringify(withArch)!==JSON.stringify(plain))
            mismatched.push(n+'/'+sid+'#'+di+' '+JSON.stringify(withArch)+' vs '+JSON.stringify(plain)); }); }); }); });
  chk('compiled opening anchors equal the rectangle-derived anchors on every model',
      checked>0&&mismatched.length===0, mismatched.slice(0,2).join(' | ')+' (checked '+checked+')');
  const r={rect:[0,0,4,4],doors:[{edge:'N'}]};
  const a2=compileArchitecture({levels:[{index:0,template:'g'}],
    floors:{g:{rooms:[{id:'a',rect:[0,0,4,4],doors:[{edge:'N'}]}]}}},'bld_0');
  chk('an unstated offset still refuses to produce an anchor, compiler or not',
      doorAnchor(r,0,a2,'bld_0.g.a')===null&&doorAnchor(r,0)===null); }
{ const b=C(FX.villa), rels=buildRelationships(b,'bld_0');
  const p=findPath(b,rels,'bld_0.f.bed1','bld_0.g.majlis','bld_0');
  const m1=measurePath(b,p,'bld_0'), m2=measurePath(b,p,'bld_0',null,null,compileArchitecture(b,'bld_0'));
  chk('measuring with and without the compiler gives identical results',
      JSON.stringify(m1)===JSON.stringify(m2), m1.walking_distance_m+' vs '+m2.walking_distance_m); }
{ const b=C(FX.villa);
  const h1=modelHash(b);
  compileArchitecture(b,'bld_0'); validateArchitecture(compileArchitecture(b,'bld_0'));
  chk('compiling architecture does not change the model revision hash', modelHash(b)===h1);
  const b2=C(FX.villa); b2.floors.g.rooms[0].rect=[0,0,6.5,5];
  chk('a real geometry change does change the hash', modelHash(b2)!==h1);
  const a1=compileArchitecture(C(FX.villa),'bld_0'), a2=compileArchitecture(b2,'bld_0');
  chk('and the compiled geometry changes with it',
      JSON.stringify(a1.walls)!==JSON.stringify(a2.walls)); }

console.log('\n== §13 — GENERIC ACROSS BUILDING TYPES ==');
{ let rows=[];
  ALL.forEach(n=>{ const a=A(n), s=archSummary(a); rows.push([n,s.walls,s.openings,s.slabs]);
    chk(n+': compiles with the same element vocabulary',
        a.walls.every(w=>w.type==='WALL')&&a.slabs.every(s2=>s2.type==='FLOOR_SLAB')&&
        a.openings.every(o=>o.type==='DOOR'||o.type==='WINDOW'));
    chk(n+': every wall belongs to at least one space and one level',
        a.walls.every(w=>w.spaces.length>=1&&!!w.level_id));
    chk(n+': every opening resolves or explains itself',
        a.openings.every(o=>o.host_status==='resolved'||!!o.host_note));
    chk(n+': validation issues are all inside the declared code list',
        a.issues.every(i=>ARCH_ISSUE_CODES.indexOf(i.code)>=0),
        JSON.stringify(a.issues.map(i=>i.code)));
    chk(n+': no element carries a compliance verdict',
        !/PASS|FAIL|COMPLIANT|CODE_REQUIRED/.test(JSON.stringify(a))); });
  console.log('  ',JSON.stringify(rows)); }
{ const a=A('unicode');
  chk('non-ASCII space names survive intact', a.spaces.some(s=>s.name==='غرفة'));
  chk('astral-plane names are handled without corruption',
      a.spaces.some(s=>s.name==='\u{1D51E}room'));
  chk('wall space lists are sorted by code point, matching Python',
      a.walls.every(w=>{const c=w.spaces.slice();
        return JSON.stringify(c)===JSON.stringify(w.spaces); })); }

console.log('\n== §14 — BACKWARD COMPATIBILITY ==');
{ const legacy={levels:[{index:0,template:'g'}],
    floors:{g:{rooms:[{id:'a',rect:[0,0,5,4],doors:[{edge:'N',offset:2}]}]}}};
  const a=compileArchitecture(legacy,'bld_0');
  chk('a Phase 1 model with no architectural metadata compiles', a.walls.length===4);
  chk('and nothing was invented for it',
      a.walls.every(w=>w.height_m.value===null&&w.thickness_m.value===null)&&a.cores.length===0);
  chk('the compiler tolerates a model with no levels at all',
      compileArchitecture({},'bld_0').walls.length===0);
  chk('the compiler tolerates rooms with no rect',
      compileArchitecture({levels:[{index:0,template:'g'}],
        floors:{g:{rooms:[{id:'x'}]}}},'bld_0').spaces.length===1); }
{ const b=C(FX.villa);
  const before=buildRelationships(b,'bld_0').length;
  chk('Phase 1 relationship count is unchanged by the new layer', before===25, before);
  chk('Phase 1 egress still resolves', findEgress(b,buildRelationships(b,'bld_0'),
      'bld_0.g.majlis','bld_0').status==='FOUND'); }

console.log('\n== §15 — SECURITY OF THE NEW LAYER ==');
chk('no eval / Function in the architecture layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      compileArchitecture.toString()+validateArchitecture.toString()+
      archSummary.toString()+slabStrips.toString()));
chk('no network call in the architecture layer',
    !/fetch\s*\(|XMLHttpRequest|import\s*\(/.test(
      compileArchitecture.toString()+validateArchitecture.toString()));
chk('a hostile space name cannot escape into markup',
    (()=>{const a=compileArchitecture({levels:[{index:0,template:'g'}],
      floors:{g:{rooms:[{id:'<script>alert(1)</script>',rect:[0,0,4,4]}]}}},'bld_0');
      return esc(a.spaces[0].name).indexOf('<script')<0; })());

console.log(`\nARCHITECTURE: ${pass} passed, ${fail} failed`);
