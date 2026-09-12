import {parseReviewFile, MAX_FILE_BYTES} from './packet.mjs';
const $ = id => document.getElementById(id);
const ns = 'http://www.w3.org/2000/svg';
let versions = [], active = null, projection = null, zoom = 1, generation = 0;
const format = value => value === null || value === undefined ? 'غير متاح / غير قابل للقياس' :
  typeof value === 'object' ? JSON.stringify(value) : String(value);
const sourceNames = {requested:'مطلوب صراحة', inferred:'مستنتج — راجع التأكيد', unknown:'غير محدد'};
const metricNames = {
  site_area_m2:'مساحة الموقع (م²)',
  level_count:'عدد الأدوار',
  space_instance_count:'عدد الفراغات',
  space_rect_area_m2:'مجموع مساحات حدود الفراغات (م²)',
  space_area_by_role_m2:'مساحات الفراغات حسب الدور الوظيفي (م²)',
  unclassified_space_area_m2:'مساحة الفراغات غير المصنفة (م²)',
  space_count_by_role:'عدد الفراغات حسب الدور الوظيفي',
  unclassified_space_count:'عدد الفراغات غير المصنفة',
  gross_floor_area_m2:'إجمالي مساحة الأرضيات GFA (م²)',
  net_floor_area_m2:'صافي مساحة الأرضيات NFA (م²)',
  efficiency:'كفاءة المساحة',
  zone_area_by_role_m2:'مساحة مناطق التشغيل حسب الدور الوظيفي (م²)',
  unclassified_zone_area_m2:'مساحة مناطق التشغيل غير المصنفة (م²)',
  dock_count:'عدد الأرصفة',
  dock_count_by_edge:'الأرصفة حسب الواجهة',
  dock_count_by_zone_role:'الأرصفة حسب منطقة التشغيل',
  rack_group_count:'مجموعات الرفوف',
  rack_declared_level_sum:'مجموع مستويات الرفوف المعلنة',
  rack_declared_footprint_area_m2:'مساحة بصمة الرفوف المعلنة (م²)',
  station_count:'محطات العمل',
  lane_area_by_kind_m2:'مساحات الممرات حسب النوع (م²)',
  lane_centerline_length_by_kind_m:'أطوال محاور الممرات المعلنة حسب النوع (م)',
  lane_overlap_area_by_kind_pair_m2:'مساحات تداخل أنواع الممرات (م²)',
  storage_capacity_positions:'السعة التخزينية المحسوبة (مواضع)',
  throughput_per_hour:'معدل التشغيل المحسوب في الساعة',
  travel_distance_m:'مسافة الحركة المحسوبة (م)',
  pedestrian_vehicle_separation_compliance:'التحقق من فصل المشاة والمركبات',
  fire_life_safety_compliance:'التحقق من متطلبات الحريق وسلامة الأرواح'
};
const scopeNames = {rectangular_geometry:'هندسة حدود الفراغات',program:'برنامج المتطلبات',topology:'الترابط',vertical_circulation:'الحركة الرأسية',regulatory_compliance:'الامتثال التنظيمي',structural_safety:'السلامة الإنشائية'};
const states = {PASS:'اجتاز وفق الملف',FAIL:'يحتاج معالجة',NOT_VERIFIED:'غير متحقق'};
function node(tag, text, parent, cls) { const e=document.createElement(tag); if(text!==null)e.textContent=text; if(cls)e.className=cls;if(parent)parent.append(e);return e; }
function svg(tag, attrs, parent, text) { const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;parent.append(e);return e; }
function pair(parent, label, value) { node('dt',label,parent);node('dd',format(value),parent); }
function metricValue(key, value) {
  if (value !== null && value !== undefined) return value;
  const unavailable = active && active.scorecard && active.scorecard.unavailable;
  const reason = unavailable && unavailable[key];
  return typeof reason === 'string' && reason.trim()
    ? `غير متاح / غير قابل للقياس — ${reason}`
    : value;
}
function resetView() {
  active=projection=null;versions=[];$('workspace').hidden=true;$('empty').hidden=false;
  for(const id of ['plan','selection','spaces','metrics','scopes','issues','locks','requirements','identity','revision','level'])$(id).replaceChildren();
}
function selected(item) {
  $('selection').replaceChildren();node('h3',item.label,$('selection'));
  const dl=node('dl',null,$('selection'));pair(dl,'الموضع X / Z (م)',item.rect_xz_m.slice(0,2));pair(dl,'العرض × العمق (م)',item.rect_xz_m.slice(2));pair(dl,'مساحة حدود الفراغ (م²)',item.space_rect_area_m2);
  pair(dl,'source_id',item.source_id);pair(dl,'القالب / الفراغ',`${item.source.template} / ${item.source.room_id}`);
  const locked=active.locks.rooms.some(r=>r[0]===item.source.template&&r[1]===item.source.room_id)||active.locks.semantic.some(s=>s.kind==='room'&&s.template===item.source.template&&s.room_id===item.source.room_id);
  pair(dl,'قفل الفراغ المسجل',locked?'مقفل في الملف — عرض فقط':'لا يوجد قفل مباشر مسجل للفراغ');
  pair(dl,'المتطلبات المرتبطة',item.requirement_refs.map(r=>r.requirement_id));
  const nested=projection.source_map.filter(s=>s.source.kind==='element'&&s.source.level_index===projection.level_index&&s.source.template===item.source.template&&s.source.room_id===item.source.room_id);
  for(const s of nested)pair(dl,`${s.source.collection} / ${s.source.element_id} (رابط فقط؛ غير مرسوم)`,s.requirement_refs.map(r=>r.requirement_id));
  for(const e of document.querySelectorAll('[data-source-id]'))e.setAttribute('aria-pressed',String(e.dataset.sourceId===item.source_id));
}
function viewport() { if(!projection)return;const{w,d}=projection.site;const width=w*1.1/zoom,depth=d*1.1/zoom;$('plan').setAttribute('viewBox',`${(w-width)/2} ${(d-depth)/2} ${width} ${depth}`); }
function draw() {
  projection=active.projections[Number($('level').value)];zoom=1;
  $('plan').replaceChildren();$('spaces').replaceChildren();$('selection').textContent='اختر فراغًا من المخطط أو القائمة.';
  svg('title',{},$('plan'),`مخطط الدور ${projection.level_index}`);
  svg('rect',{x:0,y:0,width:projection.site.w,height:projection.site.d,class:'site'},$('plan'));
  for(const item of projection.primitives){
    const[x,z,w,d]=item.rect_xz_m;
    const g=svg('g',{class:'space',role:'button',tabindex:0,'aria-label':`${item.label}، ${format(item.space_rect_area_m2)} متر مربع`,'aria-pressed':'false','data-source-id':item.source_id},$('plan'));
    svg('title',{},g,item.label);svg('rect',{x,y:z,width:w,height:d,class:'space-shape'},g);
    svg('text',{x:x+w/2,y:z+d/2,'font-size':Math.min(w,d)*.095},g,item.label.slice(0,50));
    svg('text',{x:x+w/2,y:z+d/2+Math.min(w,d)*.16,'font-size':Math.min(w,d)*.075},g,`${format(w)} × ${format(d)} m`);
    g.addEventListener('click',()=>selected(item));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selected(item);}});
    const b=node('button',`${item.label} · ${format(item.space_rect_area_m2)} م²`,$('spaces'));b.type='button';b.dataset.sourceId=item.source_id;b.setAttribute('aria-pressed','false');b.addEventListener('click',()=>selected(item));
  }
  $('extent').textContent=`الموقع ${format(projection.site.w)} × ${format(projection.site.d)} م · اتجاه ACS: X أفقي وZ إلى أسفل الرسم. لا يُستنتج اتجاه الشمال من هذا العرض.`;
  viewport();
}
function showVersion() {
  active=versions[Number($('revision').value)];$('level').replaceChildren();
  active.projections.forEach((p,i)=>{const o=node('option',`الدور ${p.level_index}`,$('level'));o.value=String(i);});
  for(const id of ['metrics','scopes','issues','locks','requirements','identity'])$(id).replaceChildren();
  for(const[k,v]of Object.entries(active.scorecard.metrics))pair($('metrics'),metricNames[k]||k,metricValue(k,v));
  for(const[k,v]of Object.entries(active.review.scopes))pair($('scopes'),scopeNames[k]||k,states[v]);
  if(!active.review.issues.length)node('li','لا توجد ملاحظات مسجلة في الملف. لا يُعد ذلك اعتمادًا.', $('issues'));
  for(const i of active.review.issues)node('li',`${i.code}${i.requirement_id?' · '+i.requirement_id:''}`,$('issues'));
  for(const r of active.locks.rooms)node('li',`فراغ: ${r.join(' / ')} (على مستوى القالب)`,$('locks'));
  for(const s of active.locks.semantic)node('li',`${s.kind} · ${[s.template,s.room_id,s.collection,s.element_id].filter(Boolean).join(' / ')}`,$('locks'));
  if(!active.locks.rooms.length&&!active.locks.semantic.length)node('li','لا توجد أقفال مسجلة في هذه النسخة.',$('locks'));
  for(const r of active.requirements){const c=node('article',null,$('requirements'),'requirement');node('strong',r.id,c);node('div',sourceNames[r.source],c,'badge');const dl=node('dl',null,c);pair(dl,'المقياس',r.metric);pair(dl,'المطلوب',r.expected);if(r.source_id)pair(dl,'معرّف المصدر',r.source_id);if(r.source_span)pair(dl,'موضع الدليل في النص الأصلي',`${r.source_span.start} → ${r.source_span.end} (أحرف Unicode، النهاية غير مشمولة)`);}
  for(const[k,v]of Object.entries(active.revision))pair($('identity'),k,v);
  $('workspace').hidden=false;$('empty').hidden=true;draw();
}
export async function importFiles(files) {
  const current=++generation;resetView();$('error').hidden=true;$('status').textContent='جارٍ فحص الملفات محليًا…';
  try{
    const list=Array.from(files);if(!list.length||list.length>8)throw new Error('REVIEW_FILE_COUNT');
    const views=[];const ids=new Set();
    for(const f of list){if(f.size>MAX_FILE_BYTES)throw new Error('REVIEW_FILE_LIMIT');const p=await parseReviewFile(await f.text());if(ids.has(p.revision.id))throw new Error('DUPLICATE_REVISION');ids.add(p.revision.id);views.push(p);}
    if(current!==generation)return;versions=views;
    versions.forEach((p,i)=>{const o=node('option',`V${p.revision.version} · ${p.revision.id.slice(0,17)}`,$('revision'));o.value=String(i);});
    showVersion();$('status').textContent=`تم فتح ${views.length} نسخة محليًا. لا رفع ولا حفظ سحابي ولا اعتماد.`;
  }catch(e){if(current!==generation)return;resetView();$('status').textContent='لم تُعرض النسخة غير الصالحة.';$('error').hidden=false;$('error').textContent=`تعذر فتح ملف المراجعة. تحقق من مصدره وبنيته وحجمه. (${['REVIEW_FILE_COUNT','REVIEW_FILE_LIMIT','DUPLICATE_REVISION','REVIEW_HASH_MISMATCH','PROVENANCE_MISMATCH','REVISION_MISMATCH','SECURE_CONTEXT_REQUIRED'].includes(e.message)?e.message:'INVALID_REVIEW_FILE'})`;}
}
$('files').addEventListener('change',()=>importFiles($('files').files));
$('clear').addEventListener('click',()=>{++generation;resetView();$('files').value='';$('error').hidden=true;$('status').textContent='أزيلت الملفات من العرض.';});
$('revision').addEventListener('change',showVersion);$('level').addEventListener('change',draw);
$('zoomIn').addEventListener('click',()=>{zoom=Math.min(4,zoom*1.25);viewport();});$('zoomOut').addEventListener('click',()=>{zoom=Math.max(.5,zoom/1.25);viewport();});$('fit').addEventListener('click',()=>{zoom=1;viewport();});
