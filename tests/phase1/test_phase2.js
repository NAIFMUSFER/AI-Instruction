/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

console.log('\n== DRIFT — frontend registry must equal acs_programs.json (single source of truth) ==');
const REG=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_programs.json'),'utf8'));
const jsIds=ACS_PROGRAMS.map(p=>p.id), pyIds=REG.programs.map(p=>p.id);
chk('same program ids/order', JSON.stringify(jsIds)===JSON.stringify(pyIds), JSON.stringify(jsIds));
chk('same industrial domain', JSON.stringify(ACS_INDUSTRIAL)===JSON.stringify(REG.industrial_domain));
let drift=[];
REG.programs.forEach(p=>{ const j=ACS_PROGRAMS.find(x=>x.id===p.id);
  if(!j) return drift.push(p.id+':missing');
  if(JSON.stringify(j.strong)!==JSON.stringify(p.strong)) drift.push(p.id+':strong');
  if(JSON.stringify(j.weak)!==JSON.stringify(p.weak)) drift.push(p.id+':weak');
  if(j.domain!==p.domain) drift.push(p.id+':domain');
  if(j.categories!==p.categories) drift.push(p.id+':categories'); });
chk('no keyword/domain drift', drift.length===0, drift.join(','));
chk('space categories identical', JSON.stringify(ACS_SPACE_CATEGORIES)===JSON.stringify(REG.space_categories));

console.log('\n== PART 8 — building type detection (10 types) ==');
const CASES=[
 ['Villa','فيلا دورين فيها مجلس وصالة ومطبخ و4 غرف نوم','villa'],
 ['Hotel','فندق من 8 أدوار يحتوي على 40 غرفة نزلاء ولوبي واستقبال ومطعم ومطبخ','hotel'],
 ['Clinic','عيادة طبية تحتوي على استقبال وصالة انتظار و4 غرف كشف ومختبر وصيدلية','clinic'],
 ['Office','مبنى مكاتب من 5 أدوار يحتوي على مكاتب مفتوحة وغرف اجتماعات','office'],
 ['Restaurant','مطعم فيه صالة طعام ومطبخ ودورات مياه','restaurant'],
 ['School','مدرسة فيها 12 فصل ومكتبة وصالة رياضية','school'],
 ['Hospital','مستشفى فيه طوارئ وغرف مرضى وغرفتا عمليات وعيادات','hospital'],
 ['Warehouse','مستودع 100×60 يحتوي على 6 عمال و2 AMR ورافعة شوكية','warehouse'],
 ['Factory','مصنع فيه خط إنتاج ومخزن ومكاتب','factory'],
 ['Mixed-use','مبنى متعدد الاستخدامات: محلات تجارية ومكاتب وشقق','mixed_use'],
];
CASES.forEach(([n,txt,exp])=>chk(`${n} → ${exp}`, detectTypeJS(txt)===exp, detectTypeJS(txt)));

console.log('\n== PART 8 — no cross-domain contamination ==');
chk('clinic is NOT industrial', !isIndustrialProgram(detectTypeJS(CASES[2][1])));
chk('hotel is NOT industrial', !isIndustrialProgram(detectTypeJS(CASES[1][1])));
chk('warehouse IS industrial', isIndustrialProgram(detectTypeJS(CASES[7][1])));
chk('factory IS industrial (program preserved)', isIndustrialProgram(detectTypeJS(CASES[8][1])));
chk('clinic categories = healthcare (not hospitality)', JSON.stringify(spaceCategories('clinic'))===JSON.stringify(ACS_SPACE_CATEGORIES.healthcare));
chk('office categories ≠ healthcare', JSON.stringify(spaceCategories('office'))!==JSON.stringify(ACS_SPACE_CATEGORIES.healthcare));

console.log('\n== PART 18 — project hierarchy (data level) ==');
function mkBuilding(type,nLevels,rooms){
  const floors={t:{rooms:rooms||[{id:'r1',rect:[0,0,5,4]}]}};
  const levels=[]; for(let i=0;i<nLevels;i++) levels.push({index:i,name:'L'+i,template:'t'});
  return {meta:{type:type,name:type},site:{w:40,d:30},wall_h:3,floor_height:3.2,levels:levels,floors:floors};
}
// A — Villa: 1 site, 1 building, 2 floors
const A=toProject(mkBuilding('villa',2));
chk('A villa: 1 building', A.project.buildings.length===1);
chk('A villa: 2 levels', A.project.buildings[0].building.levels.length===2);
chk('A villa: site has id/units/origin', !!(A.project.site.id&&A.project.site.units==='m'&&A.project.site.origin));
chk('A villa: floor ids + elevations', A.project.buildings[0].building.levels.every(l=>l.id&&l.elevation!=null),
    JSON.stringify(A.project.buildings[0].building.levels.map(l=>[l.id,l.elevation])));
chk('A villa: space_id assigned', !!A.project.buildings[0].building.floors.t.rooms[0].space_id);
// B — Hotel 8 floors
const B=toProject(mkBuilding('hotel',8));
chk('B hotel: 8 levels, type=hotel', B.project.buildings[0].building.levels.length===8 && B.project.buildings[0].building_type==='hotel');
// C — Compound: 3 buildings
let C=toProject(mkBuilding('villa',2),'مجمّع');
function addBuilding(pr,b,type,name){ const i=pr.project.buildings.length;
  ensureElementIds(b,'bld_'+i);
  pr.project.buildings.push({id:'bld_'+i,name:name,building_type:type,programs:[type],
    position:{x:i*50,z:0,rotation:0},active:false,building:b}); return pr; }
C=addBuilding(C,mkBuilding('villa',2),'villa','فيلا ب');
C=addBuilding(C,mkBuilding('restaurant',1),'restaurant','النادي');
chk('C compound: 3 buildings', C.project.buildings.length===3, C.project.buildings.length);
chk('C compound: distinct ids', new Set(C.project.buildings.map(b=>b.id)).size===3);
chk('C compound: positions distinct', new Set(C.project.buildings.map(b=>b.position.x)).size===3);
chk('C compound: active building still first', activeBuilding(C)===C.project.buildings[0].building);
chk('C compound: mixed types coexist', JSON.stringify(C.project.buildings.map(b=>b.building_type))==='["villa","villa","restaurant"]');
// D — Resort multi-building
let D=toProject(mkBuilding('resort',3),'منتجع');
D=addBuilding(D,mkBuilding('villa',1),'villa','شاليه'); D=addBuilding(D,mkBuilding('restaurant',1),'restaurant','مطعم');
chk('D resort: 3 buildings, no industrial fields', D.project.buildings.length===3 && !D.project.buildings.some(b=>isIndustrialProgram(b.building_type)));
// E — Mixed use: one building, multiple programs
const E=toProject(mkBuilding('mixed_use',15));
E.project.buildings[0].programs=['retail','office','residential'];
chk('E mixed-use: multiple programs on one building', E.project.buildings[0].programs.length===3, JSON.stringify(E.project.buildings[0].programs));
chk('E mixed-use: building_type stays mixed_use', E.project.buildings[0].building_type==='mixed_use');
// F — Warehouse program still works
const F=toProject(mkBuilding('warehouse',1));
chk('F warehouse: industrial program preserved', isIndustrialProgram(F.project.buildings[0].building_type));

console.log('\n== PART 19 — backward compatibility (Phase 1 JSON) ==');
const p1=mkBuilding('villa',2,[{id:'majlis',rect:[0,0,6,5],objects:[{kind:'car',count:2},{kind:'stairs',count:1}]},{id:'kitchen',rect:[7,0,4,3]}]);
const before={rooms:2, objects:3, levels:2, json:JSON.stringify(p1)};
chk('Phase 1 building recognized', isBuildingModel(p1)&&!isProjectModel(p1));
const wrapped=toProject(p1);
chk('wrapped: no data loss (same building object)', activeBuilding(wrapped)===p1);
const rooms=Object.values(activeBuilding(wrapped).floors).flatMap(f=>f.rooms);
const objs=rooms.flatMap(r=>(r.objects||[]).map(o=>(o.count||1))).reduce((a,b)=>a+b,0);
chk('same room count (2)', rooms.length===2, rooms.length);
chk('same object count (3)', objs===3, objs);
chk('same level count (2)', activeBuilding(wrapped).levels.length===2);
const env=projectEnvelope(p1);
chk('export envelope keeps Phase 1 fields at root', !!(env.site&&env.levels&&env.floors&&env.meta));
chk('export envelope adds project hierarchy', !!(env.project&&env.project.buildings.length===1&&env.project.site));
chk('export carries building_type + space_categories', env.project.buildings[0].building_type==='villa'&&env.project.buildings[0].space_categories.length>0);
chk('setModel-compatible: activeBuilding(project) works', !!activeBuilding(toProject(p1)).floors);
chk('idempotent: toProject(project) === project', toProject(wrapped)===wrapped);

console.log('\n== PART 9 — programs must not invent user requirements ==');
chk('suggested spaces are NOT auto-injected into building', !(activeBuilding(toProject(mkBuilding('hotel',2))).floors.t.rooms.some(r=>/lobby|ballroom|spa/i.test(r.id))));
chk('registry marks suggestions as guidance only', /AI_SUGGESTED|SYSTEM_DEFAULT/.test(REG.suggested_spaces._note));

console.log(`\nPHASE2: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
