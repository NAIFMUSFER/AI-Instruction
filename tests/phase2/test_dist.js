/* ======================================================================
   المرحلة 2 — اختبارات أساس قياس المسافة الهندسية الحقيقية (A–H)
   قياس فقط. لا مطابقة، لا حدود مسافة، لا حكم سلامة.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const B=n=>JSON.parse(JSON.stringify(FX[n]));
const M=(b,from,to,op)=>{const r=buildRelationships(b,'bld_0');
  const p=findPath(b,r,from,to,'bld_0'); return {p,m:measurePath(b,p,'bld_0',op&&op.origin,op&&op.destination),r};};
// ممنوع أي ادّعاء مطابقة/سلامة في أي مخرج قياس
// نحذف أولاً عبارات النفي/الإفصاح المطلوبة ثم نفحص الادّعاءات الإيجابية فقط
const ALLOWED=/لم تُقيَّم أي مطابقة|المسافة الفعلية للمشي لم تُحسب|NOT_EVALUATED|NOT_MEASURED|لم تُقَس|غير قابلة للقياس/g;
const FORB_RE=/آمن|مطابق|نظامي|كافٍ|ضمن الحد|compliant|approved|safe|adequate|allowed|maximum|limit|travel distance limit/i;
const FORB=t=>FORB_RE.test(String(t).replace(ALLOWED,''));

console.log('\n== TEST A — غرف مستطيلة: قياس من هندسة الأبواب ==');
const A={meta:{type:'office'},site:{w:40,d:20},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'a',rect:[0,0,10,4],doors:[{edge:'E',offset:2,width:0.9}]},
    {id:'b',rect:[10,0,6,4],doors:[{edge:'W',offset:2,width:0.9}]}]}}};
let x=M(A,'bld_0.g.a','bld_0.g.b');
// يدويًا: مركز a(5,2) → مرساة الباب [10,2] = 5.000 | سماكة الجدار 0.200 | [10,2] → مركز b(13,2) = 3.000
chk('A1 المسار مقيس بالكامل COMPLETE', x.m.distance_status==='COMPLETE', x.m.distance_status);
chk('A2 المسافة = 8.200 م (تحقّق يدوي)', x.m.walking_distance_m===8.2, x.m.walking_distance_m);
chk('A3 الأساس: هندسة الباب + خط داخل المستطيل',
    JSON.stringify(x.m.measurement_basis)==='["door_geometry","straight_line_inside_rect"]', JSON.stringify(x.m.measurement_basis));
chk('A4 لا مقاطع غير مقيسة', x.m.unmeasured_segments.length===0);
chk('A5 مرساة الباب من الحافة+الإزاحة لا من المركز',
    x.m.segments[0].to[0]===10&&x.m.segments[0].to[1]===2, JSON.stringify(x.m.segments[0].to));
chk('A6 origin_basis معلن صراحةً', x.m.origin_basis==='space_centroid_fallback', x.m.origin_basis);
chk('A7 compliance = NOT_EVALUATED', x.m.compliance==='NOT_EVALUATED');
chk('A8 لا لفظ مطابقة/سلامة', !FORB(JSON.stringify(x.m))&&!FORB(distanceSummary(x.m)));
chk('A9 التحقق البنيوي نظيف', validateMeasurement(x.m).length===0, JSON.stringify(validateMeasurement(x.m)));
// نقطة بداية صريحة تُوسم بوضوح
let xe=M(A,'bld_0.g.a','bld_0.g.b',{origin:[1,2]});
chk('A10 نقطة بداية صريحة تُوسم explicit_origin_point', xe.m.origin_basis==='explicit_origin_point');
chk('A11 المسافة من نقطة صريحة = 12.200 م', xe.m.walking_distance_m===12.2, xe.m.walking_distance_m);
// ممر هندسي (نسبة ≥3) يُقاس على المحور الأوسط لا بخط قاطع للجدران
const A2={meta:{type:'office'},site:{w:60,d:20},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'r1',rect:[0,0,4,4],doors:[{edge:'E',offset:2,width:0.9}]},
    {id:'hall',rect:[4,0,24,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]},
    {id:'r2',rect:[28,0,4,4],doors:[{edge:'W',offset:2,width:0.9}]}]}}};
let x2=M(A2,'bld_0.g.r1','bld_0.g.r2');
// hall نسبة 24/4=6 ⇒ محور أوسط z=2 : |4-28|+0+0 = 24 ؛ الإجمالي 2+0.2+24+0.2+2 = 28.400
chk('A12 الممرّ الهندسي يُقاس على المحور الأوسط',
    x2.m.measurement_basis.indexOf('corridor_centerline')>=0, JSON.stringify(x2.m.measurement_basis));
chk('A13 المسافة عبر الممر = 28.400 م (تحقّق يدوي)', x2.m.walking_distance_m===28.4, x2.m.walking_distance_m);

console.log('\n== TEST B — فيلا، نفس الطابق، تحقّق يدوي ==');
let vb=B('villa'); vb.wall_t=0.20;
let b1=M(vb,'bld_0.g.majlis','bld_0.g.living');
// مجلس(0,0,6,5) مركز(3,2.5)→[6,2.5]=3.000 | 0.200 | ممر(6,0,2,10) محور x=7: 0+1+1=2.000 | 0.200 | [8,2.5]→مركز(11,2.5)=3.000
chk('B1 COMPLETE', b1.m.distance_status==='COMPLETE', b1.m.distance_status);
chk('B2 المسافة = 8.400 م (تحقّق يدوي)', b1.m.walking_distance_m===8.4, b1.m.walking_distance_m);
chk('B3 خمسة مقاطع (٣ داخل فراغ + بابان)', b1.m.segments.length===5, b1.m.segments.length);
chk('B4 مقطع الممر بالمحور الأوسط = 2.000',
    b1.m.segments[2].basis==='corridor_centerline'&&b1.m.segments[2].length_m===2, JSON.stringify(b1.m.segments[2]));
chk('B5 مسافة المشي ≠ مسافة مراكز الفراغات التشخيصية',
    b1.p.metrics.horizontal_centroid_m!==b1.m.walking_distance_m,
    b1.p.metrics.horizontal_centroid_m+' vs '+b1.m.walking_distance_m);
chk('B6 لا انتقال رأسي', b1.m.vertical_transport.length===0&&b1.m.vertical_elevation_change_m===null);

console.log('\n== TEST C — فيلا عبر الطوابق: الدرج يُقاس من هندسته فقط ==');
let vc=B('villa'); vc.wall_t=0.20;
let c0=M(vc,'bld_0.f.bed1','bld_0.g.majlis');
chk('C1 بلا هندسة درج ⇒ PARTIAL لا COMPLETE', c0.m.distance_status==='PARTIAL', c0.m.distance_status);
chk('C2 المسافة تبقى null (لا تلفيق)', c0.m.walking_distance_m===null);
chk('C3 سبب معلَن: هندسة الدرج غائبة',
    c0.m.unmeasured_segments.some(u=>/stair_geometry_absent/.test(u.reason)), JSON.stringify(c0.m.unmeasured_segments));
chk('C4 المقدار الأفقي المقيس معلن منفصلاً', typeof c0.m.measured_horizontal_m==='number', c0.m.measured_horizontal_m);
// أضف هندسة درج حقيقية للعنصر الموجود (لا نخترع عنصراً)
[['f','corridor_f'],['g','corridor']].forEach(([t,id])=>{
  const r=vc.floors[t].rooms.find(r=>r.id===id);
  Object.assign(r.objects[0],{risers:16,tread_m:0.28,riser_m:0.20}); });
let c1=M(vc,'bld_0.f.bed1','bld_0.g.majlis');
// سير الدرج: 16×0.28=4.480 أفقي، 16×0.20=3.200 رأسي ⇒ √(4.48²+3.2²)=5.505
// أفقي: 3.000+0.200+6.500+6.500+0.200+3.000 = 19.400 ⇒ الإجمالي 24.905
chk('C5 COMPLETE بعد توفّر هندسة الدرج', c1.m.distance_status==='COMPLETE', c1.m.distance_status);
chk('C6 طول سير الدرج = 5.505 م (تحقّق يدوي)',
    c1.m.segments.find(s=>s.type==='stair').length_m===5.505, JSON.stringify(c1.m.segments.find(s=>s.type==='stair')));
chk('C7 الأفقي = 19.400 م', c1.m.horizontal_m===19.4, c1.m.horizontal_m);
chk('C8 المسافة الكلية = 24.905 م (أفقي + سير درج)', c1.m.walking_distance_m===24.905, c1.m.walking_distance_m);
chk('C9 فرق المنسوب مسجَّل كبيان مستقل', c1.m.vertical_elevation_change_m===3.2, c1.m.vertical_elevation_change_m);
chk('C10 المشي داخل الفراغ حتى الدرج مقيس ولا يُسقَط',
    c1.m.segments.filter(s=>s.type==='in_space'&&s.length_m===6.5).length===2,
    JSON.stringify(c1.m.segments.map(s=>[s.type,s.length_m])));
chk('C11 التحقق البنيوي نظيف', validateMeasurement(c1.m).length===0, JSON.stringify(validateMeasurement(c1.m)));
// موضع الدرج غير مصرَّح ⇒ لا يُفترض مركز الفراغ
let vc2=B('villa'); vc2.wall_t=0.20;
[['f','corridor_f'],['g','corridor']].forEach(([t,id])=>{
  const r=vc2.floors[t].rooms.find(r=>r.id===id);
  r.objects[0]={kind:'stairs',count:1,risers:16,tread_m:0.28,riser_m:0.20}; });
let c2=M(vc2,'bld_0.f.bed1','bld_0.g.majlis');
chk('C12 موضع الدرج غير مصرَّح ⇒ PARTIAL بسبب معلَن',
    c2.m.distance_status==='PARTIAL'&&c2.m.unmeasured_segments.some(u=>/vertical_element_position_not_stated/.test(u.reason)),
    JSON.stringify(c2.m.unmeasured_segments));
chk('C13 ولا تُلفّق مسافة', c2.m.walking_distance_m===null);

console.log('\n== TEST D — فندق: رحلة المصعد ليست مسافة مشي ==');
let hd=B('hotel'); hd.wall_t=0.20;
let d1=M(hd,'bld_0.t.guest_1@2','bld_0.g.lobby@0');
// أفقي: 2.500+0.200+11.500+0.200+√10+0+√10+0.200+3.000 = 23.925 ؛ رحلة المصعد 6.600 مستبعدة
chk('D1 COMPLETE', d1.m.distance_status==='COMPLETE', d1.m.distance_status);
chk('D2 المسافة = 23.925 م (تحقّق يدوي)', d1.m.walking_distance_m===23.925, d1.m.walking_distance_m);
chk('D3 مسافة المشي = الأفقي فقط (لا سير درج)',
    d1.m.walking_distance_m===d1.m.horizontal_m&&d1.m.stair_walking_m===0);
chk('D4 رحلة المصعد مسجَّلة منفصلة (6.600 م منسوب)', d1.m.vertical_elevation_change_m===6.6, d1.m.vertical_elevation_change_m);
chk('D5 مقاطع المصعد بلا طول مشي',
    d1.m.segments.filter(s=>s.type==='vertical_transport').every(s=>s.length_m===null&&s.basis==='not_walking_distance'));
chk('D6 رحلة المصعد غير مجموعة في المسافة',
    Math.abs(d1.m.walking_distance_m-(d1.m.horizontal_m+d1.m.stair_walking_m))<1e-9);
chk('D7 المشي حتى المصعد داخل النواة مقيس',
    d1.m.segments.some(s=>s.type==='in_space'&&Math.abs(s.length_m-3.162)<0.001),
    JSON.stringify(d1.m.segments.map(s=>[s.type,s.length_m])));
chk('D8 التحقق يرفض إسناد طول مشي للمصعد',
    validateMeasurement({units:'m',segments:[],horizontal_m:0,distance_status:'PARTIAL',
      vertical_transport:[{kind:'elevator',length_m:5}]}).some(i=>/elevator travel must not carry walking length/.test(i)));

console.log('\n== TEST E — عيادة: طابق واحد، قياس كامل ==');
let ce=B('clinic'); ce.wall_t=0.15;
let crels=buildRelationships(ce,'bld_0');
let e1=findEgress(ce,crels,'bld_0.g.exam_1','bld_0');
// (8,2)→[6,2]=2.000 | 0.150 | [6,2]→مرساة باب المخرج [0,2] = 6.000 ⇒ 8.150
chk('E1 مخرج موجود ومسار مقيس بالكامل', e1.status==='FOUND'&&e1.distance_status==='COMPLETE', e1.status+'/'+e1.distance_status);
chk('E2 المسافة = 8.150 م (تحقّق يدوي)', e1.distance===8.15, e1.distance);
chk('E3 نقطة النهاية مرساة باب المخرج لا مركز الفراغ',
    (()=>{const s=e1.distance_measurement.segments.filter(s=>s.type==='in_space').pop();
      return s.to[0]===0&&s.to[1]===2;})(), JSON.stringify(e1.distance_measurement.segments.slice(-1)));
chk('E4 القياس مرفق داخل نتيجة المخارج', !!e1.distance_measurement);
chk('E5 compliance يبقى NOT_EVALUATED', e1.compliance==='NOT_EVALUATED'&&e1.distance_measurement.compliance==='NOT_EVALUATED');
chk('E6 لا انتقالات رأسية', e1.characteristics.vertical_transition_count===0);
chk('E7 لا لفظ مطابقة/سلامة في الملخّص', !FORB(egressSummary(e1)), egressSummary(e1));

console.log('\n== TEST F — مخارج متعددة: قاعدة الترتيب مشروطة ==');
const F={meta:{type:'office'},site:{w:40,d:10},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'west',rect:[0,0,8,4],doors:[{edge:'E',offset:2,width:0.9},{edge:'W',offset:2,width:0.9}]},
    {id:'start',rect:[8,0,4,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]},
    {id:'east',rect:[12,0,20,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]}]}}};
let fr=buildRelationships(F,'bld_0');
let f1=findEgress(F,fr,'bld_0.g.start','bld_0');
// غرب: 2.000+0.200+8.000 = 10.200 | شرق: 2.000+0.200+20.000 = 22.200 (نفس عدد الانتقالات = 1)
chk('F1 كل المرشّحين مقيسون ⇒ الترتيب بالمسافة المقاسة',
    f1.selection_basis==='minimum_measured_walking_distance', f1.selection_basis+' / '+f1.selection_basis_reason);
chk('F2 اختير المخرج الأقرب فعلياً = 10.200 م', f1.distance===10.2, f1.distance);
chk('F3 البديل مسجَّل بمسافته 22.200 م',
    f1.alternative_exits.length===1&&f1.alternative_exits[0].walking_distance_m===22.2, JSON.stringify(f1.alternative_exits));
chk('F4 عدد الانتقالات متساوٍ ⇒ الفرق من الهندسة لا الطوبولوجيا',
    f1.route.hops===1&&f1.alternative_exits[0].hops===1);
// مرشّح واحد غير قابل للقياس ⇒ لا يُدّعى أقصر مسار هندسي
const F2=JSON.parse(JSON.stringify(F));
F2.floors.g.rooms[2].polygon=[[12,0],[32,0],[32,4],[20,6],[12,4]];
let f2r=buildRelationships(F2,'bld_0'), f2=findEgress(F2,f2r,'bld_0.g.start','bld_0');
chk('F5 مرشّح غير مقيس ⇒ العودة إلى minimum_hops', f2.selection_basis==='minimum_hops', f2.selection_basis);
chk('F6 السبب مسجَّل صراحةً',
    /geometric shortest route not claimed/.test(f2.selection_basis_reason||'')&&
    /GEOMETRY_NOT_SUPPORTED/.test(f2.selection_basis_reason||''), f2.selection_basis_reason);
chk('F7 لا وصف "الأفضل/الأقصر" في النتيجة', !/best|shortest|optimal|أفضل|أقصر/i.test(JSON.stringify(f2).replace(/shortest route not claimed/g,'')));
// سماكة الجدار غير معلومة ⇒ لا مرشّح COMPLETE ⇒ عودة إلى minimum_hops
const F3=JSON.parse(JSON.stringify(F)); delete F3.wall_t;
let f3r=buildRelationships(F3,'bld_0'), f3=findEgress(F3,f3r,'bld_0.g.start','bld_0');
chk('F8 بلا سماكة جدار ⇒ minimum_hops + سبب PARTIAL',
    f3.selection_basis==='minimum_hops'&&/PARTIAL/.test(f3.selection_basis_reason||''), f3.selection_basis_reason);
chk('F9 ولا تُنشر مسافة مشي', f3.distance===null&&f3.distance_status==='PARTIAL', f3.distance+'/'+f3.distance_status);

console.log('\n== TEST G — هندسة غير مستطيلة: لا خط مستقيم عبر الجدران ==');
const G=JSON.parse(JSON.stringify(A));
G.floors.g.rooms[1].polygon=[[10,0],[16,0],[16,4],[13,6],[10,4]];
let g1=M(G,'bld_0.g.a','bld_0.g.b');
chk('G1 الحالة GEOMETRY_NOT_SUPPORTED', g1.m.distance_status==='GEOMETRY_NOT_SUPPORTED', g1.m.distance_status);
chk('G2 لا مسافة مشي مُدّعاة', g1.m.walking_distance_m===null);
chk('G3 سبب معلَن للفراغ غير المستطيل',
    g1.m.unmeasured_segments.some(u=>/non_rectangular_geometry_not_supported/.test(u.reason)), JSON.stringify(g1.m.unmeasured_segments));
chk('G4 المقدار المقيس جزئياً معلن منفصلاً', g1.m.measured_horizontal_m===5.2, g1.m.measured_horizontal_m);
chk('G5 الملخّص يذكر عدم الدعم صراحةً', /غير مستطيلة/.test(distanceSummary(g1.m)), distanceSummary(g1.m));

console.log('\n== TEST H — باب/سماكة غير محسومة ==');
const H=JSON.parse(JSON.stringify(A)); delete H.wall_t;
let h1=M(H,'bld_0.g.a','bld_0.g.b');
chk('H1 سماكة الجدار غير معلومة ⇒ PARTIAL', h1.m.distance_status==='PARTIAL', h1.m.distance_status);
chk('H2 السبب wall_thickness_unknown',
    h1.m.unmeasured_segments.some(u=>/wall_thickness_unknown/.test(u.reason)), JSON.stringify(h1.m.unmeasured_segments));
chk('H3 المسافة تبقى null', h1.m.walking_distance_m===null);
chk('H4 الأفقي المقيس = 8.000 م (بلا اختلاق السماكة)', h1.m.measured_horizontal_m===8, h1.m.measured_horizontal_m);
chk('H5 مرساة بلا إزاحة مصرَّحة ⇒ null',
    doorAnchor({rect:[0,0,5,5],doors:[{edge:'N',width:0.9}]},0)===null);
chk('H6 مرساة بلا حافة مصرَّحة ⇒ null',
    doorAnchor({rect:[0,0,5,5],doors:[{offset:2,width:0.9}]},0)===null);
chk('H7 مرساة صحيحة تُحسب من الحافة+الإزاحة',
    JSON.stringify(doorAnchor({rect:[1,2,5,5],doors:[{edge:'S',offset:2}]},0))==='[3,7]',
    JSON.stringify(doorAnchor({rect:[1,2,5,5],doors:[{edge:'S',offset:2}]},0)));
chk('H8 مسار غير موجود ⇒ INVALID_PATH لا صفر',
    measurePath(A,{status:'NO_PATH'},'bld_0').distance_status==='INVALID_PATH');
chk('H9 لا مسافة على مسار غير موجود', measurePath(A,{status:'NO_PATH'},'bld_0').walking_distance_m===null);

console.log('\n== ثوابت عامّة ==');
const all=[x.m,x2.m,b1.m,c0.m,c1.m,c2.m,d1.m,g1.m,h1.m,e1.distance_measurement];
chk('I1 walking_distance_m غير فارغة فقط عند COMPLETE',
    all.every(m=>(m.walking_distance_m===null)===(m.distance_status!=='COMPLETE')));
chk('I2 الوحدة دائماً متر', all.every(m=>m.units==='m'));
chk('I3 compliance = NOT_EVALUATED في كل قياس', all.every(m=>m.compliance==='NOT_EVALUATED'));
chk('I4 لا حقول حدود/مطابقة',
    !/max_travel|allowed_distance|limit_m|is_compliant|required_/i.test(JSON.stringify(all)));
chk('I5 التحقق البنيوي لا يرصد أخطاء في القياسات الصحيحة',
    all.every(m=>validateMeasurement(m).length===0),
    JSON.stringify(all.map(m=>validateMeasurement(m))));
chk('I6 التحقق يرفض COMPLETE مع مقاطع غير مقيسة',
    validateMeasurement({units:'m',segments:[],horizontal_m:0,distance_status:'COMPLETE',
      unmeasured_segments:[{type:'stair'}],walking_distance_m:1}).some(i=>/COMPLETE with unmeasured/.test(i)));
chk('I7 التحقق يرفض مسافة بلا COMPLETE',
    validateMeasurement({units:'m',segments:[],horizontal_m:0,distance_status:'PARTIAL',
      walking_distance_m:5}).some(i=>/must be null unless COMPLETE/.test(i)));
chk('I8 التحقق يرصد عدم تطابق مجموع المقاطع',
    validateMeasurement({units:'m',segments:[{type:'in_space',length_m:3,basis:'straight_line_inside_rect'}],
      horizontal_m:9,distance_status:'PARTIAL'}).some(i=>/segment sum/.test(i)));
chk('I9 التحقق يرصد أساس قياس مجهول',
    validateMeasurement({units:'m',segments:[{type:'in_space',length_m:0,basis:'guessed'}],
      horizontal_m:0,distance_status:'PARTIAL'}).some(i=>/unknown measurement basis/.test(i)));
chk('I10 لا وصف مطابقة في أي ملخّص',
    all.every(m=>!FORB(distanceSummary(m))));

console.log(`\nDISTANCE: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
