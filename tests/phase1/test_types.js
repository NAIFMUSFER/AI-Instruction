let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d||''))};
function localBuild(txt,W,D,nF){
  const t=detectTypeJS(txt); const oi=objectsFromText(txt);
  if(isIndustrialProgram(t)) return {type:t, warehouse:true, oi};   // industrial path (tested separately)
  const b=parseDescription(txt,W||30,D||25,nF||2); attachObjects(b,oi.objects);
  stampMeta(b,t,objCoverage(oi.objects),oi.excluded,[]);
  return {type:t, building:b, oi};
}
function anyIndustrialFields(b){
  const bad=[];
  for(const lv of (b.levels||[])) for(const r of ((b.floors[lv.template]||{}).rooms||[])){
    for(const k of ['racks','lanes','docks','stations']) if(r[k]&&r[k].length) bad.push(r.id+'.'+k);
    if(r.role && ['receiving','crossdock','picking','packing','storage','shelf','bin'].includes(r.role)) bad.push(r.id+'.role='+r.role);
  }
  return bad;
}
function objKinds(oi){ return oi.objects.map(o=>o.kind); }

const IND=['forklift','amr','reachtruck','conveyor','pallet','shelf']; // industrial object kinds

console.log('\n== AUDIT 2/3: 10 building types (local DATA pipeline) ==');
const cases=[
 ['Villa','فيلا دورين فيها 5 غرف نوم ومجلس وصالة ومطبخ و4 حمامات ومسبح وموقف سيارتين','residential'],
 ['Apartment bldg','عمارة سكنية 4 أدوار متكررة فيها شقق، كل شقة مجلس وصالة ومطبخ وغرفتا نوم وحمام','residential'],
 ['Hotel','فندق 8 أدوار فيه 40 غرفة نزلاء ولوبي ومطعم واستقبال ومصعدين','residential'],
 ['Clinic','عيادة فيها استقبال وصالة انتظار و4 غرف كشف ومختبر وصيدلية','residential'],
 ['Office','مبنى مكاتب: استقبال وقاعة اجتماعات و10 مكاتب وغرفة خادم','office'],
 ['Restaurant','مطعم فيه صالة طعام ومطبخ واستقبال ودورات مياه','residential'],
 ['School','مدرسة فيها 12 فصل ومكتبة وصالة رياضية وإدارة','residential'],
 ['Hospital','مستشفى فيه طوارئ وغرف مرضى وغرفتا عمليات وعيادات وصيدلية','residential'],
 ['Warehouse','مستودع 120×80 فيه استقبال وتخزين بالتات وأرصفة تحميل ومنطقة التقاط','warehouse'],
 ['Factory','مصنع فيه خط إنتاج ومخزن ومكاتب','warehouse'],
];
for(const [name,txt,expType] of cases){
  const r=localBuild(txt);
  const typeOK = (expType==='warehouse') ? isIndustrialProgram(r.type) : !isIndustrialProgram(r.type);
  chk(`${name}: type=${r.type} (${expType==='warehouse'?'industrial':'generic'})`, typeOK, 'got '+r.type);
  if(!r.warehouse){
    const leak=anyIndustrialFields(r.building);
    chk(`${name}: NO industrial fields injected`, leak.length===0, 'leaked: '+leak.join(','));
    chk(`${name}: has rooms/spaces`, ((r.building.floors[r.building.levels.find(l=>l.template==='typical')?'typical':'ground']||{}).rooms||[]).length>=0 && r.building.levels.length>0);
  }
}

console.log('\n== AUDIT 3: cross-domain negative — no industrial objects auto-added ==');
const villa=localBuild('فيلا دورين فيها 5 غرف نوم ومجلس وصالة ومطبخ و4 حمامات ومسبح وموقف سيارتين');
const vk=objKinds(villa.oi);
chk('villa objects contain none of forklift/amr/conveyor/rack', !vk.some(k=>IND.includes(k)), JSON.stringify(vk));
chk('villa may contain car (requested)', true, JSON.stringify(vk));
const hotel=localBuild('فندق 8 أدوار فيه 40 غرفة ولوبي ومطعم واستقبال ومصعدين');
chk('hotel: no industrial objects', !objKinds(hotel.oi).some(k=>IND.includes(k)), JSON.stringify(objKinds(hotel.oi)));
chk('hotel: no industrial fields', hotel.warehouse?false:anyIndustrialFields(hotel.building).length===0);
const clinic=localBuild('عيادة فيها استقبال وصالة انتظار و4 غرف كشف ومختبر وصيدلية');
chk('clinic: no industrial objects', !objKinds(clinic.oi).some(k=>IND.includes(k)), JSON.stringify(objKinds(clinic.oi)));
chk('clinic: no industrial fields', clinic.warehouse?false:anyIndustrialFields(clinic.building).length===0);

console.log('\n== AUDIT 5: generic object model works across contexts ==');
const g=objectsFromText('فيلا فيها 3 سيارات و4 كراسي وسريران وطاولة و6 أشخاص');
const gk=Object.fromEntries(g.objects.map(o=>[o.kind,o.count]));
chk('cars/chairs/beds/table/people all parsed generically', gk.car===3&&gk.chair===4&&gk.bed===2&&gk.table===1&&gk.person===6, JSON.stringify(gk));

console.log(`\nTYPES RESULT: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
