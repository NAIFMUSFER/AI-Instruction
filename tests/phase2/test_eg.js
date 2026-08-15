/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const B=n=>JSON.parse(JSON.stringify(FX[n]));
const EG=(n,o)=>{const b=B(n),r=buildRelationships(b,'bld_0');return {r:findEgress(b,r,o,'bld_0'),b,rels:r};};
// نحذف أولاً عبارات النفي المسموحة (إفصاح مطلوب) ثم نفحص الادّعاءات الإيجابية فقط
const ALLOWED=/لم تُقيَّم أي مطابقة|المسافة الفعلية للمشي لم تُحسب|NOT_EVALUATED|NOT_MEASURED/g;
const FORB_RE=/آمن|إخلاء|مطابق|نظامي|كافٍ|ضمن الحد|compliant|approved|safe route|adequate|safest|best exit/i;
const FORB={test:(t)=>FORB_RE.test(String(t).replace(ALLOWED,''))};

console.log('\n== TEST A — VILLA ==');
let x=EG('villa','bld_0.g.majlis');
chk('majlis → FOUND', x.r.status==='FOUND', x.r.status);
chk('compliance NOT_EVALUATED', x.r.compliance==='NOT_EVALUATED');
// المسافة تُنشر فقط حين تكون مقيسة بالكامل من هندسة النموذج، وإلا تبقى null
chk('distance non-null only when COMPLETE', (x.r.distance===null)===(x.r.distance_status!=='COMPLETE'),
    x.r.distance+'/'+x.r.distance_status);
chk('measured distance carries a stated basis',
    x.r.distance_status!=='COMPLETE'||(x.r.distance_measurement.measurement_basis||[]).length>0,
    JSON.stringify((x.r.distance_measurement||{}).measurement_basis));
chk('selection_basis is one of the two documented modes',
    ['minimum_hops','minimum_measured_walking_distance'].indexOf(x.r.selection_basis)>=0, x.r.selection_basis);
chk('minimum_hops fallback always records why',
    x.r.selection_basis!=='minimum_hops'||/not claimed/.test(x.r.selection_basis_reason||''),
    x.r.selection_basis_reason);
x=EG('villa','bld_0.f.bed1');
chk('first-floor bedroom → FOUND', x.r.status==='FOUND', x.r.status);
chk('route uses stairs, crosses 1 level', x.r.characteristics.uses_stairs&&x.r.characteristics.levels_crossed===1, JSON.stringify(x.r.characteristics));
chk('no unresolved edges in route', x.r.characteristics.contains_unresolved_edges===false);
chk('exit provenance is geometry_inference/inferred', x.r.exit.source==='geometry_inference'&&x.r.exit.status==='inferred', x.r.exit.source+'/'+x.r.exit.status);
chk('exit destination=exterior with stated basis', x.r.exit.destination==='exterior'&&/footprint/.test(x.r.exit.meta.basis));
chk('summary has no compliance words', !FORB.test(egressSummary(x.r)), egressSummary(x.r).slice(0,50));
chk('exit validation clean', validateExits(x.b,extractExits(x.b,x.rels,'bld_0'),'bld_0').length===0);

console.log('\n== TEST B — HOTEL ==');
x=EG('hotel','bld_0.t.guest_1@2');
chk('guest level2 → FOUND', x.r.status==='FOUND', x.r.status);
chk('crosses 2 levels', x.r.characteristics.levels_crossed===2, x.r.characteristics.levels_crossed);
chk('vertical transitions recorded', x.r.characteristics.vertical_transition_count===2);
chk('elevator use recorded factually (not judged)', typeof x.r.characteristics.uses_elevator==='boolean');
chk('no "safest/best" wording', !FORB.test(JSON.stringify(x.r).slice(0,4000)));

console.log('\n== TEST C — CLINIC (single floor) ==');
x=EG('clinic','bld_0.g.exam_1');
chk('exam → FOUND', x.r.status==='FOUND', x.r.status);
chk('ZERO vertical transitions', x.r.characteristics.vertical_transition_count===0);

console.log('\n== TEST D — OFFICE ==');
x=EG('office','bld_0.t.office_1@1');
chk('office L1 → FOUND', x.r.status==='FOUND', x.r.status);
chk('reports uses_stairs & uses_elevator without judging', ('uses_stairs' in x.r.characteristics)&&('uses_elevator' in x.r.characteristics));

console.log('\n== TEST E — NO EXIT DEFINED ==');
const noExit={meta:{type:'office'},site:{w:20,d:20},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'a',rect:[0,0,5,5],doors:[{edge:'E',offset:2.5,width:0.9}]},
    {id:'b',rect:[5,0,5,5],doors:[{edge:'W',offset:2.5,width:0.9}]}]}}};
let nr=buildRelationships(noExit,'bld_0');
chk('no exits extracted (none invented)', extractExits(noExit,nr,'bld_0').length===0);
chk('status NO_EXIT_DEFINED', findEgress(noExit,nr,'bld_0.g.a','bld_0').status==='NO_EXIT_DEFINED');

console.log('\n== TEST F — EXIT EXISTS BUT NO PATH ==');
const iso={meta:{type:'office'},site:{w:40,d:40},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'lobby',rect:[0,0,6,6],doors:[{edge:'W',offset:3,width:1.2},{edge:'E',offset:3,width:0.9}]},
    {id:'hall',rect:[6,0,5,6],doors:[{edge:'W',offset:3,width:0.9}]},
    {id:'island',rect:[20,20,5,5],doors:[{edge:'N',offset:2.5,width:0.9}]}]}}};
let ir=buildRelationships(iso,'bld_0');
chk('exit exists', extractExits(iso,ir,'bld_0').length>=1);
let rr=findEgress(iso,ir,'bld_0.g.island','bld_0');
chk('island → NO_PATH', rr.status==='NO_PATH', rr.status);
chk('reason NO_PATH_TO_REPRESENTED_EXIT', rr.reason==='NO_PATH_TO_REPRESENTED_EXIT', rr.reason);
chk('distinct from NO_EXIT_DEFINED', rr.status!=='NO_EXIT_DEFINED');
chk('connected space still reaches exit', findEgress(iso,ir,'bld_0.g.hall','bld_0').status==='FOUND');

console.log('\n== TEST G — UNRESOLVED EXIT (marker only) ==');
const marker={meta:{type:'office'},site:{w:20,d:20},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'a',rect:[0,0,5,5],doors:[{edge:'E',offset:2.5,width:0.9}],points:[{type:'exit',x:1,z:1,auto:true}]},
    {id:'b',rect:[5,0,5,5],doors:[{edge:'W',offset:2.5,width:0.9}]}]}}};
let mr=buildRelationships(marker,'bld_0');
const mex=extractExits(marker,mr,'bld_0');
chk('marker becomes UNRESOLVED exit', mex.length===1&&mex[0].status==='unresolved', JSON.stringify(mex.map(e=>e.status)));
chk('destination unknown (not guessed exterior)', mex[0].destination==='unknown');
chk('system_generated provenance from auto flag', mex[0].source==='system_generated');
chk('query → UNRESOLVED_EXIT', findEgress(marker,mr,'bld_0.g.a','bld_0').status==='UNRESOLVED_EXIT');
chk('never presented as code-required', !/code|كود/i.test(JSON.stringify(mex)));

console.log('\n== TEST H — MULTIPLE EXITS (ranking + unreachable) ==');
const multi={meta:{type:'office'},site:{w:80,d:40},wall_h:3,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'r0',rect:[10,0,5,5],doors:[{edge:'E',offset:2.5,width:0.9}]},
    {id:'r1',rect:[15,0,5,5],doors:[{edge:'W',offset:2.5,width:0.9},{edge:'E',offset:2.5,width:0.9}]},
    {id:'exitA',rect:[20,0,5,5],doors:[{edge:'W',offset:2.5,width:0.9},{edge:'N',offset:2.5,width:1.2}]},
    {id:'r2',rect:[5,0,5,5],doors:[{edge:'E',offset:2.5,width:0.9},{edge:'W',offset:2.5,width:0.9}]},
    {id:'r3',rect:[0,0,5,5],doors:[{edge:'E',offset:2.5,width:0.9},{edge:'W',offset:2.5,width:1.2}]},
    {id:'far',rect:[60,20,5,5],doors:[{edge:'S',offset:2.5,width:1.2}]}]}}};
let xr=buildRelationships(multi,'bld_0');
const xex=extractExits(multi,xr,'bld_0');
chk('3 exits represented', xex.length===3, xex.length);
const mres=findEgress(multi,xr,'bld_0.g.r0','bld_0');
chk('FOUND with primary candidate', mres.status==='FOUND', mres.status);
chk('primary is minimum hops', mres.alternative_exits.every(a=>a.hops>=mres.route.hops), JSON.stringify(mres.alternative_exits.map(a=>a.hops))+' vs '+mres.route.hops);
chk('alternatives listed', mres.alternative_exits.length>=1, mres.alternative_exits.length);
chk('unreachable exit reported separately', mres.unreachable_exits.length>=1, JSON.stringify(mres.unreachable_exits.map(u=>u.status)));
chk('selection_basis stated as minimum_hops', mres.selection_basis==='minimum_hops');
chk('no "best/safest" label anywhere', !FORB.test(JSON.stringify(mres)));

console.log('\n== PART 10/28 — AUDIT ==');
const ab=B('villa'), arel=buildRelationships(ab,'bld_0'), aud=auditEgress(ab,arel,'bld_0');
chk('audit reports compliance NOT_EVALUATED', aud.compliance==='NOT_EVALUATED');
chk('audit has reachability counts', typeof aud.nodes_with_reachable_exit==='number'&&typeof aud.nodes_without_reachable_exit==='number', JSON.stringify(aud));
chk('audit counts exits by status', ('confirmed_exits' in aud)&&('inferred_exits' in aud)&&('unresolved_exits' in aud));

console.log('\n== PART 17 — occupants factual only ==');
const occ=B('warehouse');
occ.floors.o.rooms[1].objects=[{kind:'worker',count:6,x:2,z:2}];
const orl=buildRelationships(occ,'bld_0');
const ores=findEgress(occ,orl,'bld_0.o.receiving','bld_0');
chk('represented_people_count exposed as data', typeof ores.represented_people_count==='number');
chk('no occupant-load / capacity fields', !/occupant_load|required_capacity|persons_per/i.test(JSON.stringify(ores)));

console.log('\n== PART 29 — validation catches bad exits ==');
const bad=[{id:'e1',type:'exit',building_id:'bld_0',level:9,space_id:'bld_0.g.nope',via:null,
            destination:'moon',source:'rule',status:'weird'},
           {id:'e1',type:'exit',building_id:'bld_9',level:0,space_id:'bld_9.g.x',via:'v',
            destination:'exterior',source:'user',status:'confirmed'}];
const bi=validateExits(B('villa'),bad,'bld_0');
const hit=re=>bi.some(i=>re.test(i));
chk('duplicate id caught', hit(/duplicate exit id/));
chk('dangling space caught', hit(/dangling space/));
chk('invalid level caught', hit(/invalid level/));
chk('invalid destination caught', hit(/invalid destination/));
chk('source=rule rejected', hit(/source=rule requires real rule evidence/));
chk('invalid status caught', hit(/invalid status/));
chk('missing via caught', hit(/exit without via/));
chk('cross-building exit caught', hit(/points to another building/));

console.log('\n== PART 32 — inter-building not invented ==');
chk('cross-building origin → NOT_SUPPORTED_INTER_BUILDING',
    findEgress(B('villa'),arel,'bld_1.g.x','bld_0').status==='NOT_SUPPORTED_INTER_BUILDING');

console.log(`\nEGRESS: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
