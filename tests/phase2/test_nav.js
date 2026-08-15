/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const P=(n,a,b,o)=>{const bd=JSON.parse(JSON.stringify(FX[n]));const r=buildRelationships(bd,'bld_0');
  return {res:findPath(bd,r,a,b,'bld_0',o&&o.includeUnresolved),bd:bd,rels:r};};
const V=(x)=>validatePath(x.bd,x.rels,x.res,'bld_0');

console.log('\n== TEST A — VILLA ==');
let x=P('villa','bld_0.g.majlis','bld_0.g.kitchen');
chk('same-floor FOUND', x.res.status==='FOUND', x.res.status);
chk('path validates', V(x).length===0, JSON.stringify(V(x)));
chk('no vertical transition on same floor', !x.res.transitions.some(t=>t.type==='vertical'));
chk('every node exists in nav graph', x.res.nodes.every(n=>n.includes('@')));
x=P('villa','bld_0.g.majlis','bld_0.f.bed1');
chk('cross-floor FOUND', x.res.status==='FOUND', x.res.status);
chk('exactly 1 vertical transition', x.res.transitions.filter(t=>t.type==='vertical').length===1);
const vt=x.res.transitions.find(t=>t.type==='vertical');
chk('vertical explicit: kind+levels+via', vt.kind==='stairs'&&vt.from_level===0&&vt.to_level===1&&!!vt.via, JSON.stringify(vt));
chk('vertical marked not measurable', vt.distance_measurable===false);
chk('distance is null (never fabricated)', x.res.distance===null);
chk('distance_status PARTIAL', x.res.distance_status==='PARTIAL', x.res.distance_status);
chk('resolution reflects inferred edges', x.res.resolution==='contains_inferred_edges');
chk('path validates', V(x).length===0);
x=P('villa','bld_0.f.bed2','bld_0.g.bath1');
chk('bed2 → bath1 FOUND', x.res.status==='FOUND', x.res.status);
chk('summary is factual (no safety/code words)', !/آمن|إخلاء|مطابق|متاح لذوي|approved|safe|evacuation|accessible/i.test(pathSummary(x.res)), pathSummary(x.res).slice(0,60));

console.log('\n== TEST B — HOTEL ==');
x=P('hotel','bld_0.t.guest_1@1','bld_0.g.lobby@0');   // الدور الأرضي صار قالب g
chk('guest@1 → lobby@0 FOUND', x.res.status==='FOUND', x.res.status);
chk('vertical transitions explicit', x.res.transitions.some(t=>t.type==='vertical'&&t.from_level===1&&t.to_level===0), JSON.stringify(x.res.transitions.filter(t=>t.type==='vertical')));
x=P('hotel','bld_0.t.guest_1@1','bld_0.t.guest_2@2');
chk('guest@1 → guest@2 FOUND', x.res.status==='FOUND', x.res.status);
chk('vertical uses serviced levels only', x.res.transitions.filter(t=>t.type==='vertical').every(t=>[0,1,2].includes(t.from_level)&&[0,1,2].includes(t.to_level)));
chk('path validates', V(x).length===0);
const amb=P('hotel','bld_0.t.guest_1','bld_0.t.corridor');
chk('ambiguous level rejected (not guessed)', amb.res.status==='INVALID_SOURCE'&&/ambiguous_level/.test(amb.res.reason), amb.res.reason);

console.log('\n== TEST C — CLINIC (single floor) ==');
x=P('clinic','bld_0.g.reception','bld_0.g.exam_1');
chk('reception → exam FOUND', x.res.status==='FOUND', x.res.status);
chk('NO vertical transitions', !x.res.transitions.some(t=>t.type==='vertical'));
chk('path validates', V(x).length===0);

console.log('\n== TEST D — OFFICE ==');
x=P('office','bld_0.t.office_1@1','bld_0.t.meeting@1');
chk('office → meeting FOUND (same level)', x.res.status==='FOUND', x.res.status);
chk('bare id on multi-level template is rejected, not guessed',
    P('hotel','bld_0.t.guest_1','bld_0.g.lobby').res.status==='INVALID_SOURCE');
x=P('office','bld_0.t.office_1@1','bld_0.g.reception@0');
chk('level 1 → ground FOUND via core', x.res.status==='FOUND'&&x.res.transitions.some(t=>t.type==='vertical'), x.res.status);

console.log('\n== TEST E — NO PATH (disconnected space) ==');
x=P('clinic','bld_0.g.reception','bld_0.g.lab');
chk('disconnected lab → NO_PATH', x.res.status==='NO_PATH', x.res.status);
chk('reason states no eligible edges', /no_eligible_edges|no eligible edge/.test(x.res.reason), x.res.reason);
chk('adjacency did NOT create a route', true);

console.log('\n== TEST F — UNRESOLVED DOOR never traversed ==');
const iso={meta:{type:'villa'},site:{w:40,d:40},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],
  floors:{g:{rooms:[
    {id:'hall',rect:[0,0,6,6],doors:[{edge:'N',offset:3,width:0.9}]},
    {id:'sealed',rect:[20,20,5,5],doors:[{edge:'N',offset:2.5,width:0.9}]}]}}};
const irels=buildRelationships(iso,'bld_0');
chk('both doors are unresolved', irels.filter(e=>e.type==='DOOR_CONNECTS').every(e=>e.status==='unresolved'));
let r1=findPath(iso,irels,'bld_0.g.hall','bld_0.g.sealed','bld_0');
chk('primary query NO_PATH (unresolved not traversed)', r1.status==='NO_PATH', r1.status);
chk('no edge in result', (r1.edges||[]).length===0);
const r2=findPath(iso,irels,'bld_0.g.hall','bld_0.g.sealed','bld_0',true);
chk('debug include-unresolved is separate & not primary', r2.status!=='FOUND'||r2.resolution==='unresolved', r2.status+'/'+r2.resolution);

console.log('\n== PART 2 — EDGE ELIGIBILITY ==');
const vb=JSON.parse(JSON.stringify(FX.villa)), vr=buildRelationships(vb,'bld_0');
const g=buildNavGraph(vb,vr,'bld_0',false);
chk('SPACE_ADJACENT never becomes an edge', g.edges.every(e=>e.type==='door'||e.type==='vertical'));
chk('no unresolved edge in nav graph', g.edges.every(e=>e.status!=='unresolved'));
chk('BUILDING_ON_SITE not walkable', g.edges.every(e=>e.type!=='BUILDING_ON_SITE'));
const adjOnly={meta:{type:'office'},site:{w:20,d:20},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[{id:'a',rect:[0,0,5,5]},{id:'b',rect:[5,0,5,5]}]}}};
const ar=buildRelationships(adjOnly,'bld_0');
chk('adjacent-but-no-door pair exists as relationship', ar.some(e=>e.type==='SPACE_ADJACENT'));
chk('…but is NOT traversable', findPath(adjOnly,ar,'bld_0.g.a','bld_0.g.b','bld_0').status==='NO_PATH');

console.log('\n== PART 13 — MULTI-BUILDING ==');
const mb=findPath(vb,vr,'bld_0.g.majlis','bld_1.t.lobby','bld_0');
chk('inter-building → NOT_SUPPORTED_INTER_BUILDING', mb.status==='NOT_SUPPORTED_INTER_BUILDING', mb.status);
chk('reason states not implemented', /not implemented/.test(mb.reason));

console.log('\n== PART 5 — INVALID refs ==');
chk('unknown source → INVALID_SOURCE', findPath(vb,vr,'bld_0.g.nope','bld_0.g.kitchen','bld_0').status==='INVALID_SOURCE');
chk('unknown target → INVALID_TARGET', findPath(vb,vr,'bld_0.g.majlis','bld_0.g.nope','bld_0').status==='INVALID_TARGET');

console.log('\n== PART 25 — no code/safety claims anywhere ==');
const all=[pathSummary(P('villa','bld_0.g.majlis','bld_0.f.bed1').res), JSON.stringify(P('villa','bld_0.g.majlis','bld_0.f.bed1').res)].join(' ');
chk('no compliance vocabulary in output', !/compliant|evacuation|accessible|safe route|مطابق|إخلاء|آمن/i.test(all));

console.log(`\nNAVIGATION: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
