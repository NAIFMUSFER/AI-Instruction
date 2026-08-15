/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const G=n=>buildRelationships(JSON.parse(JSON.stringify(FX[n])),'bld_0');
const has=(r,t,f,to)=>r.some(e=>e.type===t&&e.from===f&&(to===undefined||e.to===to));

console.log('\n== TEST A — VILLA ==');
const V=G('villa'), Vb=FX.villa;
chk('all IDs unique', new Set(V.map(e=>e.id)).size===V.length);
chk('validation clean (no dangling/dupe/self)', validateRelationships(V,Vb,'bld_0').length===0,
    JSON.stringify(validateRelationships(V,Vb,'bld_0').slice(0,3)));
chk('majlis ↔ corridor adjacency', has(V,'SPACE_ADJACENT','bld_0.g.majlis','bld_0.g.corridor'));
/* بعد أساس الهندسة المعمارية: الباب المستضاف على جدار يفصل فراغين بالضبط
   يرتقي إلى confirmed ويحمل دليله. الشرط هنا أقوى لا أضعف: نطلب الحالة
   والدليل معاً، ونطلب أن يبقى كل confirmed مسنوداً بجدار مسمّى. */
{ const md=V.find(e=>e.type==='DOOR_CONNECTS'&&e.from==='bld_0.g.majlis'&&e.to==='bld_0.g.corridor');
  chk('majlis door resolves to corridor', !!md&&(md.status==='confirmed'||md.status==='inferred'), md&&md.status);
  chk('a confirmed door edge carries its architectural evidence',
      !!md&&md.status==='confirmed'&&(md.meta||{}).evidence_basis
        ==='door_hosted_on_a_wall_shared_by_exactly_two_spaces'&&!!(md.meta||{}).wall_id,
      JSON.stringify(md&&md.meta));
  chk('no DOOR_CONNECTS is confirmed without a named shared wall',
      V.filter(e=>e.type==='DOOR_CONNECTS'&&e.status==='confirmed')
       .every(e=>(e.meta||{}).wall_id&&(e.meta||{}).evidence_basis));
  chk('unresolved door edges were not upgraded by the architectural layer',
      V.filter(e=>e.type==='DOOR_CONNECTS'&&e.status==='unresolved').every(e=>e.to===null)); }
chk('stair connects ground → first', has(V,'VERTICAL_CONNECTS','bld_0.flr_0','bld_0.flr_1'));
chk('LEVEL_CONNECTS derived', has(V,'LEVEL_CONNECTS','bld_0.flr_0','bld_0.flr_1'));
chk('no phantom: no edge to a non-existent space', V.every(e=>!e.to||/^bld_0\.(g|f|flr_)/.test(e.to)));
chk('unresolved doors are marked, not invented', V.filter(e=>e.status==='unresolved').every(e=>e.to===null));
chk('no confidence fabricated', V.every(e=>e.confidence===undefined));
chk('every edge has provenance source', V.every(e=>['user','ai_inference','system_generated','geometry_inference'].includes(e.source)));
chk('no source=rule (no rule engine)', V.every(e=>e.source!=='rule'));

console.log('\n== TEST B — HOTEL ==');
const H=G('hotel'), Hb=FX.hotel;
chk('validation clean', validateRelationships(H,Hb,'bld_0').length===0);
chk('guest_1 door → corridor', H.some(e=>e.type==='DOOR_CONNECTS'&&e.from==='bld_0.t.guest_1'&&e.to==='bld_0.t.corridor'));
chk('elevator serves 3 levels', H.some(e=>e.type==='VERTICAL_CONNECTS'&&(e.meta||{}).kind==='elevator'&&JSON.stringify((e.meta||{}).serviced_levels)==='[0,1,2]'));
chk('stairs vertical edges present', H.some(e=>e.type==='VERTICAL_CONNECTS'&&(e.meta||{}).kind==='stairs'));
chk('LEVEL_CONNECTS lists both kinds', H.some(e=>e.type==='LEVEL_CONNECTS'&&JSON.stringify((e.meta||{}).kinds)==='["elevator","stairs"]'));
chk('two level pairs (0-1, 1-2)', H.filter(e=>e.type==='LEVEL_CONNECTS').length===2);

console.log('\n== TEST C — CLINIC (no industrial leakage) ==');
const C=G('clinic'), Cb=FX.clinic;
chk('validation clean', validateRelationships(C,Cb,'bld_0').length===0);
chk('reception ↔ waiting adjacency', has(C,'SPACE_ADJACENT','bld_0.g.reception','bld_0.g.waiting'));
chk('reception door → waiting', C.some(e=>e.type==='DOOR_CONNECTS'&&e.from==='bld_0.g.reception'&&e.to==='bld_0.g.waiting'));
chk('NO vertical edges (single level, nothing proven)', !C.some(e=>e.type==='VERTICAL_CONNECTS'));
chk('no industrial-only types leaked', C.every(e=>['SPACE_ADJACENT','DOOR_CONNECTS'].includes(e.type)));

console.log('\n== TEST D — OFFICE ==');
const O=G('office'), Ob=FX.office;
chk('validation clean', validateRelationships(O,Ob,'bld_0').length===0);
chk('office_1 door → corridor', O.some(e=>e.type==='DOOR_CONNECTS'&&e.from==='bld_0.t.office_1'&&e.to==='bld_0.t.corridor'));
chk('elevator + stairs connect 2 levels', O.filter(e=>e.type==='VERTICAL_CONNECTS').length===2);

console.log('\n== WAREHOUSE (one program among many) ==');
const W=G('warehouse');
chk('envelope excluded from adjacency', !W.some(e=>String(e.from).includes('envelope')||String(e.to||'').includes('envelope')));
chk('zones adjacency present', has(W,'SPACE_ADJACENT','bld_0.o.receiving','bld_0.o.storage'));

console.log('\n== TEST E — MULTI-BUILDING (unique IDs, no collisions) ==');
const b1=JSON.parse(JSON.stringify(FX.villa)), b2=JSON.parse(JSON.stringify(FX.hotel)), b3=JSON.parse(JSON.stringify(FX.clinic));
const R1=buildRelationships(b1,'bld_0'), R2=buildRelationships(b2,'bld_1'), R3=buildRelationships(b3,'bld_2');
const allIds=[...R1,...R2,...R3].map(e=>e.id);
chk('globally unique relationship ids', new Set(allIds).size===allIds.length, allIds.length+' vs '+new Set(allIds).size);
chk('each building refs only its own ids', validateRelationships(R2,b2,'bld_1').length===0 && validateRelationships(R3,b3,'bld_2').length===0);
const proj={project:{id:'prj_0',site:{id:'site_0'},buildings:[
  {id:'bld_0',building_type:'villa',position:{x:0,z:0,rotation:0}},
  {id:'bld_1',building_type:'hotel',position:{x:60,z:0,rotation:0}},
  {id:'bld_2',building_type:'clinic',position:{x:120,z:0,rotation:0}}]}};
const PR=buildProjectRelationships(proj);
chk('BUILDING_ON_SITE for each building', PR.length===3&&PR.every(e=>e.type==='BUILDING_ON_SITE'&&e.to==='site_0'));
chk('project rel ids unique', new Set(PR.map(e=>e.id)).size===3);
chk('positions preserved in meta', PR[1].meta.position.x===60);

console.log('\n== PART 15 — GRAPH VALIDATION catches bad edges ==');
const bad=[
 {id:'x1',type:'DOOR_CONNECTS',from:'bld_0.g.majlis',to:'bld_0.g.nope',source:'geometry_inference',status:'inferred',via:'v'},
 {id:'x2',type:'SPACE_ADJACENT',from:'bld_0.g.majlis',to:'bld_0.g.majlis',source:'geometry_inference',status:'confirmed'},
 {id:'x2',type:'SPACE_ADJACENT',from:'bld_0.g.majlis',to:'bld_0.g.corridor',source:'geometry_inference',status:'confirmed'},
 {id:'x3',type:'DOOR_CONNECTS',from:'bld_0.g.majlis',to:'bld_0.g.corridor',source:'geometry_inference',status:'inferred'},
 {id:'x4',type:'VERTICAL_CONNECTS',from:'bld_0.flr_9',to:'bld_0.flr_1',source:'geometry_inference',status:'inferred',via:'v'},
 {id:'x5',type:'SPACE_ADJACENT',from:'bld_0.g.majlis',to:'bld_9.g.other',source:'geometry_inference',status:'confirmed'},
 {id:'x6',type:'SPACE_ADJACENT',from:'bld_0.g.majlis',to:'bld_0.g.corridor',source:'rule',status:'confirmed'}];
const iss=validateRelationships(bad,Vb,'bld_0');
const hit=re=>iss.some(i=>re.test(i));
chk('dangling space ref caught', hit(/dangling space ref/), JSON.stringify(iss.slice(0,2)));
chk('self-link caught', hit(/self-link/));
chk('duplicate id caught', hit(/duplicate relationship id/));
chk('missing via caught', hit(/requires 'via'/));
chk('invalid level ref caught', hit(/dangling level ref/));
chk('cross-building without permission caught', hit(/cross-building reference/));
chk('source=rule rejected (no rule evidence)', hit(/source=rule requires real rule evidence/));

console.log('\n== PART 12/13 — export additive + backward compatible ==');
const p1=JSON.parse(JSON.stringify(FX.villa));
const env=projectEnvelope(p1);
chk('Phase 1 fields still at root', !!(env.site&&env.levels&&env.floors&&env.meta));
chk('project hierarchy present', !!(env.project&&env.project.buildings.length===1));
chk('relationships exported additively', Array.isArray(env.relationships)&&env.relationships.length>0, (env.relationships||[]).length);
chk('project.relationships exported', Array.isArray(env.project.relationships)&&env.project.relationships.length===1);
const empty=projectEnvelope({meta:{type:'villa'},site:{w:10,d:10},levels:[{index:0,template:'g'}],floors:{g:{rooms:[]}}});
chk('empty graph is valid (never fabricated)', Array.isArray(empty.relationships)&&empty.relationships.length===0);
chk('summary helper works', relationshipSummary(V).total===V.length);

console.log(`\nRELATIONSHIPS: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
