import {parseReviewFile} from '../core/plan-review-packet.mjs';
import {showApprovedGLTF} from './approved-viewer.mjs';
import {createBriefEditor} from './brief-review.mjs';
import {createPlotRules} from './plot-rules.mjs';
import {createPlanUpload,TRANSCRIPTION} from './plan-upload.mjs';
import {createResidentialOptions} from './residential-options.mjs';
import {createBriefReader} from './brief-reader.mjs';
import {floorLabel,planRoomName,roomLabelLayout} from '../core/plan-labels.mjs';

const $ = id => document.getElementById(id);
const scopeNames = {rectangular_geometry:'الأبعاد والتداخلات',program:'المتطلبات المقاسة',topology:'الترابط والفتحات',vertical_circulation:'محاذاة النوى بين الأدوار',warehouse_expansion_reserve:'حماية مساحة التوسّع المعلنة',regulatory_compliance:'الامتثال التنظيمي',structural_safety:'السلامة الإنشائية'};
const metricNames = {site_area_m2:'مساحة الموقع (م²)',level_count:'الأدوار',space_instance_count:'الفراغات',space_rect_area_m2:'مساحة حدود الفراغات (م²)',space_count_by_role:'عدد الفراغات حسب الاستخدام',space_area_by_role_m2:'المساحة حسب الاستخدام (م²)',zone_area_by_role_m2:'مساحات التشغيل (م²)',zone_area_ratio_by_role:'نسب توزيع مناطق التشغيل',unclassified_zone_area_m2:'مساحة مناطق التشغيل غير المصنفة (م²)',dock_count:'الأرصفة',dock_count_by_edge:'الأرصفة حسب الواجهة',dock_count_by_zone_role:'الأرصفة حسب منطقة التشغيل',dock_site_x_by_slot_m:'مواضع الأرصفة X (م)',dock_site_z_by_slot_m:'مواضع الأرصفة Z (م)',rack_group_count:'مجموعات الرفوف',rack_declared_level_sum:'مجموع مستويات الرفوف المعلنة',rack_declared_height_max_m:'أقصى ارتفاع رف معلن (م)',rack_geometric_bay_count:'عدد خلايا الرفوف الهندسية',rack_geometric_bay_level_positions:'المواضع الهندسية للرفوف عبر المستويات',rack_declared_footprint_area_m2:'مساحة بصمة الرفوف المعلنة (م²)',rack_overlap_area_m2:'مساحة تداخل الرفوف (م²)',rack_lane_overlap_area_by_lane_kind_m2:'تداخل الرفوف مع الممرات حسب النوع (م²)',station_count:'محطات العمل',lane_area_by_kind_m2:'مساحات الممرات حسب النوع (م²)',lane_centerline_length_by_kind_m:'أطوال محاور الممرات حسب النوع (م)',lane_overlap_area_by_kind_pair_m2:'تداخل أنواع الممرات (م²)',configured_route_length_by_id_m:'أطوال المسارات المعلنة حسب المعرّف (م)',configured_route_length_by_flow_m:'أطوال المسارات المعلنة حسب التدفق (م)',expansion_reserve_area_m2:'مساحة التوسع المحجوزة (م²)',expansion_reserve_zone_overlap_area_m2:'تداخل مناطق التشغيل مع مساحة التوسع (م²)',expansion_reserve_rack_overlap_area_m2:'تداخل الرفوف مع مساحة التوسع (م²)',expansion_reserve_lane_overlap_area_by_kind_m2:'تداخل الممرات مع مساحة التوسع حسب النوع (م²)',storage_capacity_positions:'السعة التخزينية التشغيلية المتحققة (مواضع)',travel_distance_m:'مسافة الحركة المجمعة (م)',throughput_per_hour:'معدل التشغيل في الساعة',pedestrian_vehicle_separation_compliance:'التحقق من فصل المشاة والمركبات',fire_life_safety_compliance:'التحقق من الحريق وسلامة الأرواح'};
const issueNames = {PROGRAM_NOT_CONFIRMED:'لم يؤكد برنامج المتطلبات',REQUIREMENT_MISMATCH:'المخطط لا يحقق متطلبًا مؤكدًا',REQUIREMENT_NOT_SPECIFIED:'يوجد متطلب لم تحدد قيمته',INFERENCE_NOT_CONFIRMED:'متطلب مقترح يحتاج التأكيد',PLAN_ZONE_UNRESOLVED:'منطقة تحتاج استكمال هندستها',VERIFICATION_UNAVAILABLE:'تعذّر إكمال التحقق',ACS_GEOMETRY_FINDING:'ملاحظة في الأبعاد أو الفتحات تحتاج المراجعة',WAREHOUSE_EXPANSION_RESERVE_INTRUSION:'التخطيط يشغل جزءًا من مساحة التوسّع المعلنة',WAREHOUSE_EXPANSION_RESERVE_NOT_VERIFIED:'تحتاج مساحة التوسّع المعلنة إلى هندسة قابلة للتحقق'};
Object.assign(metricNames,{building_target_area_m2:'مساحة المبنى المستهدفة (م²)',efficiency:'كفاءة المساحة',gross_floor_area_m2:'إجمالي مساحة الأرضيات (م²)',net_floor_area_m2:'صافي مساحة الأرضيات (م²)',unclassified_space_area_m2:'مساحة الفراغات غير المصنفة (م²)',unclassified_space_count:'عدد الفراغات غير المصنفة'});
const value = v => v == null ? 'غير متحقق' : typeof v === 'object'
  ? (Array.isArray(v) ? v.map(value) : Object.entries(v).map(([k,n])=>(metricNames[k]||roomLabel(k))+': '+value(n))).join('\n') || 'لا توجد بيانات'
  : typeof v === 'number' && Number.isFinite(v) ? String(Number(v.toPrecision(12))) : String(v);
const unavailableReasons={
  gross_floor_area_m2:'لا توجد طريقة معتمدة لحساب إجمالي مساحة الأرضيات من غلاف المبنى.',
  net_floor_area_m2:'لا يوجد تصنيف معتمد لصافي المساحة.',
  efficiency:'لا تُحسب كفاءة المساحة لأن إجمالي وصافي مساحة الأرضيات غير محسوبين.',
  storage_capacity_positions:'عدد خلايا ومستويات الرفوف الهندسية ليس سعة تخزين قابلة للاستخدام أو محسوبة الأحمال؛ لا توجد بيانات وحدة التحميل والخلوص وتصنيف الأحمال.',
  throughput_per_hour:'لا يوجد في النموذج نموذج مقاس للتدفق والزمن.',
  travel_distance_m:'لا يوجد نموذج حركة واحد محدد؛ أطوال المسارات المعلنة معروضة منفصلة.',
  pedestrian_vehicle_separation_compliance:'قياس تداخل الممرات وحده لا يثبت الامتثال لاشتراطات السلامة.',
  fire_life_safety_compliance:'لا يُجرى هنا تقييم معتمد لاشتراطات الجهة المختصة.',
  rack_declared_height_max_m:'يحتاج أقصى ارتفاع للرفوف إلى ارتفاع صريح لكل مجموعة رفوف معلنة.',
  expansion_reserve_area_m2:'تحتاج مساحة التوسع المعلنة إلى حدود غرف صريحة قابلة للقياس.',
  expansion_reserve_zone_overlap_area_m2:'يحتاج قياس تداخل مناطق التشغيل مع مساحة التوسع إلى حدود غرف صريحة.',
  expansion_reserve_rack_overlap_area_m2:'يحتاج قياس تداخل الرفوف مع مساحة التوسع إلى أبعاد ومواضع صريحة للرفوف.',
  expansion_reserve_lane_overlap_area_by_kind_m2:'يحتاج قياس تداخل الممرات مع مساحة التوسع إلى أبعاد ومواضع صريحة للممرات.',
  configured_route_length_by_id_m:'تعذّر قياس المسارات المعلنة؛ راجع تعريف المسارات في النموذج.',
  configured_route_length_by_flow_m:'تعذّر قياس المسارات المعلنة؛ راجع تعريف المسارات في النموذج.',
  dock_count_by_zone_role:'يحتاج توزيع الأرصفة على المناطق إلى أعداد صريحة ومنطقة مالكة لكل رصيف.',
  dock_site_x_by_slot_m:'تحتاج مواضع الأرصفة إلى حافة وإزاحة وتباعد وعدد صريح لكل مجموعة أرصفة.',
  dock_site_z_by_slot_m:'تحتاج مواضع الأرصفة إلى حافة وإزاحة وتباعد وعدد صريح لكل مجموعة أرصفة.',
  zone_area_ratio_by_role:'تحتاج نسب مناطق التشغيل إلى مساحات غرف مقاسة كاملة.',
  rack_geometric_bay_count:'تحتاج خلايا الرفوف إلى أبعاد واتجاه وعدد صفوف ومستويات صريح لكل مجموعة رفوف.',
  rack_geometric_bay_level_positions:'تحتاج خلايا الرفوف إلى أبعاد واتجاه وعدد صفوف ومستويات صريح لكل مجموعة رفوف.',
  rack_overlap_area_m2:'يحتاج قياس تداخل الرفوف إلى أبعاد ومواضع صريحة لكل مجموعة رفوف.',
  rack_lane_overlap_area_by_lane_kind_m2:'يحتاج قياس تداخل الرفوف والممرات إلى أبعاد صريحة للرفوف والممرات.',
};
const metricValue = (key, v) => {
  if(v != null)return value(v);
  const reason=packet?.scorecard?.unavailable?.[key];
  if(typeof reason!=='string'||!reason.trim())return value(v);
  const arabic=hasArabic(reason)?reason:key==='rack_declared_height_max_m'&&/^No declared rack groups/.test(reason)?'لا توجد مجموعات رفوف معلنة، فلا يوجد أقصى ارتفاع.':unavailableReasons[key]||'لا توجد طريقة قياس معتمدة لهذا المقياس في النموذج الحالي.';
  return 'غير متاح / غير قابل للقياس — '+arabic;
};
// Canonical level kind is explicit; room names never determine roof authority.
const isRoofProjection = p => p?.level_kind === 'roof';
const levelLabel = p => isRoofProjection(p) ? (p.level_auto===true?'السطح · افتراضي غير مشغول':'السطح · غير مشغول') : floorLabel(p.level_index);
function issueRoomRef(issue){
  if(Array.isArray(issue?.room_ref)&&issue.room_ref.length===2&&issue.room_ref.every(v=>typeof v==='string'))return issue.room_ref;
  const match=typeof issue?.message==='string'?issue.message.match(/\[([^/\]]+)\/([^\]]+)\]/):null;
  return match?[match[1],match[2]]:null;
}
// A finding on the system's automatic roof deck (template roof/roof_N, rooms
// roof_*, role roof_deck). The loaded packet decides when it knows the template.
function autoRoofFinding(issue){
  const ref=issueRoomRef(issue);
  if(!ref)return /\broof_deck\b/.test(typeof issue?.message==='string'?issue.message:'');
  const owner=(packet?.projections||[]).find(p=>p.primitives?.some(r=>r.source?.template===ref[0]));
  if(owner)return isRoofProjection(owner)&&owner.level_auto===true;
  return /^roof(?:_\d+)?$/.test(ref[0])||ref[1].startsWith('roof_');
}
function roomLabel(label) {
  const names={entrance:'مدخل المبنى',stairs:'الدرج',stair:'الدرج',elevator:'المصعد',living:'الصالة',kitchen:'المطبخ',bedroom:'غرفة النوم',bathroom:'دورة المياه',corridor:'الممر',majlis:'المجلس',lobby:'البهو',porch:'الرواق',balcony:'الشرفة',courtyard:'الفناء',dining:'غرفة الطعام',laundry:'الغسيل',office:'المكتب',storage:'التخزين',staging:'التجهيز',receiving:'الاستلام',shipping:'الشحن',expansion:'مساحة التوسع',roof_deck:'السطح',circulation:'الحركة',service:'الخدمات'};
  return names[label] || (/^flat_\d+$/.test(label) ? 'شقة '+label.slice(5) : label);
}
// Internal ids (room/element ids, Python reprs) appear only in the engineer view.
const engineerIds=()=>$('cwEngineerIds')?.checked===true;
const roomName=(template,roomId)=>planRoomName(packet?.projections,template,roomId);
function revisionNote(note){
  const raw=String(note||'').replace(/\s*[·،]?\s*task:[0-9a-f-]+$/,'');
  if(engineerIds())return raw;
  const lock=/^(UN)?LOCK \('([^']*)', '([^']*)'\)$/.exec(raw);
  if(lock)return (lock[1]?'إلغاء قفل ':'قفل ')+roomName(lock[2],lock[3]);
  const edit=/^تعديل أبعاد وموضع ([^\s\u0600-\u06FF]+)$/.exec(raw);
  return edit?'تعديل أبعاد وموضع '+roomName(null,edit[1]):raw;
}
// «[template/room] نص» becomes «اسم الفراغ – الدور: نص»; the bracket breaks RTL.
function findingMessage(message){
  const text=String(message||'');
  if(engineerIds())return text;
  return text.replace(/^\s*\[([^/\]]+)\/([^\]]+)\]\s*/,(all,template,roomId)=>roomName(template,roomId)+': ');
}
function renderVersions(data){
  $('cwRevision').replaceChildren();$('cwCompareRevision').replaceChildren();
  for(const revision of data?.history||[]){
    const label='V'+revision.version+' · '+(revision.state==='APPROVED'?'معتمدة':'مسودة')+' · '+revisionNote(revision.note);
    const o=el('option',label,$('cwRevision'));o.value=revision.revision_id;
    const ref=el('option',label,$('cwCompareRevision'));ref.value=revision.revision_id;
  }
}
function projectCopy() {
  const residential=$('cwType').value==='residential';
  // Typology-specific guidance lives in the examples, not in a side box.
  $('cwBrief').placeholder=residential?'مثال: فيلا من دورين على أرض ٢٠ × ٣٠ م، أربع غرف نوم ومجلس قريب من المدخل…':'مثال للمستودعات: مستودع توزيع على أرض ٦٠ × ٨٠ م، رصيف استلام شرقي وشحن غربي، ورفوف بارتفاع ٨ م…';
  $('cwChat').placeholder=residential?'مثال: افصل مجلس الضيوف عن الصالة، وأكمل اتصال الدرج بالدور العلوي.':'مثال: انقل منطقة التجهيز بجوار الشحن، مع الحفاظ على الأقفال الحالية.';
}
let root, briefEditor, planUpload, residentialOptions, projectId, state = null, packet = null, selected = null, busy = false, pendingJob = null, pollTimer = null, revisionEpoch = 0, viewerEpoch = 0, activeStep = 1, viewerDispose = null;
let progressState=null,progressTimer=null,starting=false,objectSelection=null,failedJob=null;
const draftKey = () => 'acs_brief_draft:' + window.ACS_AUTH.storageScope();
const jobKey = () => 'acs_plan_job:' + window.ACS_AUTH.storageScope();
let plotRules=null,briefReader=null;
function el(tag, text, parent, cls) { const n=document.createElement(tag);if(text!==null)n.textContent=text;if(cls)n.className=cls;if(parent)parent.append(n);return n; }
function status(text, bad=false) { $('cwStatus').textContent=text;$('cwStatus').classList.toggle('bad',bad);$('cwStatus').setAttribute('role',bad?'alert':'status'); }
function progressTick(){
  if(!progressState)return;
  const seconds=Math.max(0,Math.floor((Date.now()-progressState.startedAt)/1000));
  const clock=[Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(n=>String(n).padStart(2,'0')).join(':');
  $('cwJobElapsed').textContent=(progressState.fromSubmission?'الوقت منذ إرسال الطلب: ':'الوقت في هذه المتابعة: ')+clock;
  $('cwJobElapsed').dataset.seconds=String(seconds);
  $('cwJobHeartbeat').textContent=progressState.lastSeenAt?'آخر تحديث من الخادم قبل '+Math.max(0,Math.floor((Date.now()-progressState.lastSeenAt)/1000))+' ثانية.':'في انتظار تأكيد الحالة من الخادم.';
}
function progressPhase(phase,confirmed=false){
  if(!progressState)return;
  const labels={SUBMITTING:'جارٍ إرسال الطلب…',CHECKING:'جارٍ التحقق من حالة المهمة…',QUEUED:'المهمة في قائمة الانتظار',RUNNING:'الخادم يعالج المخطط',UNDERSTANDING:'فهم برنامج المشروع',LAYOUT:progressState.read?'قراءة المخطط':'توزيع الغرف على الأدوار',ROOM_DETAILS:'تفصيل الأبواب والنوافذ',REVIEW:'مراجعة المخطط',SAVING:'حفظ النسخة',UNKNOWN:'تعذّر التحقق من الحالة. اضغط متابعة المهمة عند عودة الاتصال.'};
  const text=labels[phase]||labels.CHECKING;
  if($('cwJobPhase').textContent!==text)$('cwJobPhase').textContent=text;
  $('cwJobProgress').dataset.phase=phase;
  $('cwJobActivity').hidden=phase==='UNKNOWN';
  if(confirmed)progressState.lastSeenAt=Date.now();
  progressTick();
}
function beginJob(id,saved=null,read=!!saved?.read){
  clearInterval(progressTimer);pendingJob=id;failedJob=null;if($('cwResumeJob'))$('cwResumeJob').hidden=true;
  const valid=typeof saved?.startedAt==='number'&&Number.isFinite(saved.startedAt)&&saved.startedAt>0&&saved.startedAt<=Date.now();
  progressState={startedAt:valid?saved.startedAt:Date.now(),fromSubmission:saved===null||(valid&&saved.fromSubmission!==false),lastSeenAt:0,read};
  try{localStorage.setItem(jobKey(),JSON.stringify({jobId:id,startedAt:progressState.startedAt,fromSubmission:progressState.fromSubmission,read}));}catch(e){}
  $('cwJobProgress').hidden=false;$('cwJobProgress').dataset.startedAt=String(progressState.startedAt);$('cwJobProgress').scrollIntoView?.({block:'center',behavior:'smooth'});
  progressPhase(saved?'CHECKING':'SUBMITTING');progressTimer=setInterval(progressTick,1000);
}
function stopProgress(){clearInterval(progressTimer);progressTimer=null;progressState=null;if($('cwJobProgress'))$('cwJobProgress').hidden=true;}
function safeError(e) {
  const friendly={APPROVAL_REQUIRED:'اعتمد النسخة المختارة قبل التحويل والتصدير.',DOWNSTREAM_GEOMETRY_NOT_SPECIFIED:'تحتاج عناصر النسخة إلى أبعاد إضافية قبل عرض 3D. اطلب استكمالها في المحادثة ثم راجع النسخة الجديدة.',DOWNSTREAM_GEOMETRY_INVALID:'توجد أبعاد غير صالحة للتحويل إلى 3D. راجع العناصر وعدّلها في نسخة جديدة.',STALE_REVISION:'وصل تعديل أحدث لهذا المشروع. افتح آخر نسخة ثم أعد العملية.',LOCK_VIOLATION:'هذا التعديل يمس عنصرًا مقفلًا. عدّل الطلب أو ألغِ قفله أولًا.'};
  status(friendly[e?.code]||ownerMessage(e?.code,e?.message,'تعذّر إكمال العملية. حاول مجددًا.'),true);
}
// Server messages without Arabic text (engine diagnostics) never reach the owner raw.
const hasArabic=text=>/[\u0600-\u06FF]/.test(text);
const englishServerMessages={
  INVALID_GEOMETRY:'لم يُحفظ التعديل: الأبعاد الجديدة تُحدث تداخلًا أو خللًا يمنع رسم المخطط. نسختك كما هي؛ جرّب أبعادًا أخرى.',
  OPTION_TYPOLOGY_UNKNOWN:'مقارنة مؤشرات النسخ غير متاحة لهذا المشروع لأن نوع المبنى غير مسجّل في نسخه المحفوظة.',
  OPTION_TYPOLOGY_MISMATCH:'لا يمكن مقارنة نسختين لنوعي مبنى مختلفين.',
  ROOM_NOT_FOUND:'الفراغ المحدد غير موجود في هذه النسخة. افتح آخر نسخة ثم أعد الاختيار.',
  LOCK_CONTEXT_CHANGED:'هذا التعديل يغيّر سياق فراغ مقفل. فكّ القفل أولًا ثم أعد المحاولة.',
};
function ownerMessage(code,message,fallback){
  if(typeof message==='string'&&message.trim()&&hasArabic(message))return message;
  return englishServerMessages[code]||fallback;
}
function setBusy(on) { busy=on;root.setAttribute('aria-busy',String(on));$('cwRevision').disabled=on;root.querySelectorAll('[data-mutate]').forEach(b=>{b.disabled=on||!!pendingJob||b.dataset.unavailable==='true';});syncApproval(); }
async function api(body, commands=false) {
  const session=await window.ACS_AUTH.freshSession();
  if(!session)throw new Error('انتهت جلسة الدخول. أعد تحميل الصفحة لتسجيل الدخول؛ نسخك محفوظة.');
  const path='/v1/projects/'+projectId+(commands?'/plan/commands':'/workspace');
  const response=await window.ACS_AUTH.acsFetchJSON(path,body,session.access_token,body.action==='artifact'?90000:20000);
  if(commands){
    if(!response.result||typeof response.result!=='object')throw new Error('لم يصل تأكيد مكتمل من خدمة المراجعة. افتح آخر نسخة محفوظة.');
    return response.result;
  }
  return response;
}
async function run(fn) { if(busy)return;setBusy(true);try{await fn();}catch(e){safeError(e);}finally{setBusy(false);} }
function clearViewer() {
  viewerEpoch++;
  selectApprovedObject(null);
  if(viewerDispose){viewerDispose();viewerDispose=null;}
  const host=$('cwViewer');if(host){host.replaceChildren();host.hidden=true;delete host.dataset.revision;}
  if($('cwShow3D'))$('cwShow3D').hidden=false;
}
// Steps the owner opens are browser-history entries, so Back returns to the previous step.
function step(n,{record=false}={}) {
  if(record&&activeStep!==n){try{history.pushState({...(history.state||{}),acsStep:n},'');}catch(e){}}
  const moved=activeStep!==n;
  activeStep=n;
  if(n===2&&$('cwGenerateSource')){
    const uploaded=$('cwStartMode').value==='upload';root.querySelector('.cw-options').hidden=uploaded;$('cwGenerateSource').hidden=!uploaded;
    planUpload.step2(uploaded);
  }
  root.querySelectorAll('[data-step-panel]').forEach(p=>{p.hidden=Number(p.dataset.stepPanel)!==n;});
  root.querySelectorAll('[data-step]').forEach(b=>{if(Number(b.dataset.step)===n)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');b.dataset.done=String(Number(b.dataset.step)<n);});
  if(n!==4)clearViewer();
  if(moved&&!root.classList.contains('cw-loading'))root.scrollTo?.(0,0);
}
function briefProgram() { return briefEditor.program(); }
function fillBrief(data) { briefEditor.fill(data,packet?.scorecard?.typology);residentialOptions?.fill();plotRules?.fill();briefReader?.fill(data);projectCopy(); }
// A selected option is not authoritative until its matching revision is loaded.
function loadedRevisionSelected() { return !!state?.revision_id&&$('cwRevision')?.value===state.revision_id; }
function headRevisionSelected() { return loadedRevisionSelected()&&state.revision_id===state.head; }
function contextDefaultsText(summary,revision){
  if(!summary||!revision?.id||!revision.model_hash||summary.revision_id!==revision.id||summary.model_hash!==revision.model_hash||!Array.isArray(summary.items))return '';
  const seen=new Set(),counts={column:0,railing:0,plant:0,planter:0};
  for(const row of summary.items.slice(0,256)){
    if(!row)continue;
    const p=row.context_detail_provenance,key=JSON.stringify([row.template,row.level_index,row.room_id,row.object_id]);
    if(seen.has(key)||!Object.hasOwn(counts,row.kind)||row.count!==1||p?.schema!=='acs.context-detail/1'||p.source!=='system_default'||p.conceptual_only!==true||!['porch','balcony','courtyard'].includes(p.context))continue;
    seen.add(key);counts[row.kind]++;
  }
  const count=Object.values(counts).reduce((sum,n)=>sum+n,0);if(!count)return '';
  const labels={column:'أعمدة',railing:'درابزين',plant:'نباتات',planter:'أحواض نباتات'};
  return 'عناصر افتراضية ضمن هندسة النسخة: '+Object.entries(counts).filter(([,n])=>n).map(([kind,n])=>n+' '+labels[kind]).join('،')+'. '+(summary.truncated?'القائمة جزئية؛ العدد ليس إجمالي المشروع. ':'')+'افتراضات تخطيطية؛ لا تثبت كفاية إنشائية أو حماية من السقوط أو خلوصًا آمنًا. الإزالة تنشئ مسودة جديدة وتخضع للأقفال.';
}
function objectRemovalTarget(){
  const selection=objectSelection,summary=state?.object_actions,source=selection?.source;
  if(!selection||selection.epoch!==revisionEpoch||selection.viewer_epoch!==viewerEpoch||!headRevisionSelected()||!packet)return null;
  if(packet.revision.id!==state.revision_id||selection.revision_id!==state.revision_id||selection.model_hash!==packet.revision.model_hash||summary?.revision_id!==state.revision_id||summary.model_hash!==selection.model_hash)return null;
  if(!selection.source_id||source?.kind!=='element'||source.collection!=='objects'||selection.repeat_index!==0||!Array.isArray(summary.items))return null;
  const rows=summary.items.filter(row=>row.template===source.template&&row.room_id===source.room_id&&row.object_id===source.element_id&&row.level_index===source.level_index);
  if(rows.length!==1)return null;
  const row=rows[0];if(!row.supported||row.count!==1||!['column','railing','plant','planter'].includes(row.kind))return null;
  return row;
}
function selectApprovedObject(selection){
  objectSelection=selection?{...selection,source:{...selection.source},epoch:revisionEpoch,viewer_epoch:viewerEpoch}:null;
  if($('cwObjectConfirm'))$('cwObjectConfirm').checked=false;
  syncObjectSelection();
}
function syncObjectSelection(){
  const panel=$('cwObjectSelection');if(!panel)return;
  panel.hidden=!objectSelection;
  const target=objectRemovalTarget(),requiresDraft=state?.object_actions?.requires_new_draft===true;
  const names={column:'عمود',railing:'درابزين',plant:'نبات',planter:'حوض نباتات'};
  $('cwObjectDescription').textContent=target?(names[target.kind]+($('cwEngineerIds')?.checked===true?' · '+target.object_id:'')+' · إزالة العنصر من هندسة النسخة، وليست إخفاءً للعرض. يُعاد فحص الأقفال والصلاحيات في الخادم.'):'العنصر المحدد غير متاح للإزالة هنا؛ اختر عنصرًا مدعومًا من آخر نسخة وبمصدر موثّق. العناصر المكررة أو القوالب المشتركة تُعدّل من مخططها.';
  $('cwObjectConfirmation').hidden=!target||!requiresDraft;
  $('cwObjectRemove').hidden=!target;
  $('cwObjectRemove').disabled=busy||!!pendingJob||!target||(requiresDraft&&!$('cwObjectConfirm').checked);
}
async function removeSelectedObject(){
  const target=objectRemovalTarget();
  if(!target||pendingJob)throw new Error('اختر عنصرًا موثّقًا ومدعومًا من آخر نسخة قبل إزالته.');
  const confirm=state.object_actions.requires_new_draft===true;
  if(confirm&&!$('cwObjectConfirm').checked)throw new Error('أكد إزالة العنصر وإنشاء مسودة جديدة؛ الاعتماد السابق يبقى محفوظًا.');
  const data=await api({action:'remove_object',expected_head:state.head,room_ref:[target.template,target.room_id],object_id:target.object_id,confirm_new_draft:confirm},true);
  await renderState(data);step(3);
  const comparisonNote=data.revision_comparison_unavailable?.reason==='OPTION_TYPOLOGY_UNKNOWN'?' مقارنة مؤشرات البدائل غير متاحة لأن نوع المبنى غير محدد؛ فرق حذف العنصر محفوظ.':'';
  status('أُزيل العنصر وحُفظت مسودة جديدة تحتاج المراجعة والاعتماد. النسخة المعتمدة السابقة محفوظة؛ لم يُستدعَ مزود ذكاء اصطناعي.'+comparisonNote);
}
const notesCount=n=>n===2?'ملاحظتان':n<=10?n+' ملاحظات':n+' ملاحظة';
// One plain line naming what blocks approval, with a deterministic fix when one exists.
function approvalBlocker(){
  if(!packet||!state)return {text:''};
  if(pendingJob)return {text:'انتظر انتهاء المهمة الحالية قبل الاعتماد.'};
  if(!headRevisionSelected())return {text:'هذه نسخة سابقة للقراءة فقط. الاعتماد يكون لآخر نسخة؛ استعد هذه النسخة كمسودة جديدة إن أردت اعتمادها.'};
  if(state.authority?.can_approve_concept===true)return {text:state.authority.source_transcription===true?TRANSCRIPTION.ready:'الفحوصات التخطيطية جاهزة للمراجعة والاعتماد المبدئي.'};
  const findings=(Array.isArray(state.review_findings)?state.review_findings:packet.review?.issues||[]).filter(issue=>issue.severity!=='advisory');
  const others=findings.filter(issue=>!autoRoofFinding(issue));
  if(findings.length&&!others.length)return {text:'يمنع الاعتماد: ملاحظات على السطح الافتراضي فقط. أزل السطح الافتراضي ثم اعتمد النسخة.',fix:'roof'};
  if(others.length===1)return {text:'يمنع الاعتماد: ملاحظة واحدة — '+(issueNames[others[0].code]||'ملاحظة تحتاج المراجعة')+'. راجعها في «ملاحظات المراجعة».'};
  if(others.length)return {text:'يمنع الاعتماد: '+notesCount(others.length)+' في «ملاحظات المراجعة». عالجها ثم اعتمد المخطط.'};
  const scope=['rectangular_geometry','program','topology','vertical_circulation'].find(key=>packet.review?.scopes?.[key]!=='PASS');
  return {text:scope?'يمنع الاعتماد: لم يكتمل فحص '+scopeNames[scope]+'. حدّث المشروع، وإن بقي اطلب المعالجة في المحادثة.':'يمنع الاعتماد: لم تكتمل الفحوصات بعد. حدّث المشروع ثم حاول مجددًا.'};
}
function syncApproval() {
  if(!root)return;
  const loaded=loadedRevisionSelected(),head=headRevisionSelected();
  const blocker=approvalBlocker();
  $('cwApprovalNote').textContent=blocker.text;
  const approveText=$('cwApproveConfirm').nextSibling;if(approveText)approveText.textContent=state?.authority?.source_transcription===true?TRANSCRIPTION.confirm:TRANSCRIPTION.concept;
  const roofFix=$('cwApprovalFix');
  if(roofFix){roofFix.hidden=blocker.fix!=='roof'||$('cwRoof')?.dataset.enabled!=='true'||$('cwRoof')?.dataset.userAuthored==='true';roofFix.disabled=busy||!!pendingJob||!head;}
  $('cwApprove').disabled=busy||!!pendingJob||!head||state?.authority?.can_approve_concept!==true||!$('cwApproveConfirm').checked;
  const approved=loaded&&!!state?.history?.some(v=>v.revision_id===state.revision_id&&v.state==='APPROVED');
  root.querySelectorAll('[data-format]:not([data-format=review]),#cwShow3D').forEach(b=>{b.disabled=busy||!approved;});
  root.querySelector('[data-format=review]').disabled=busy||!loaded||!packet;
  $('cwChatSubmit').disabled=busy||!!pendingJob||!head;
  const chatHint=$('cwChatHint');
  if(chatHint){chatHint.textContent=pendingJob?'التعديل بالمحادثة متاح بعد انتهاء المهمة الحالية.':loaded&&!head?'التعديل بالمحادثة يكون على آخر نسخة فقط، حتى لا يضيع ما بعدها. اختر آخر نسخة، أو استعد هذه النسخة كمسودة جديدة ثم عدّلها.':'';chatHint.hidden=!chatHint.textContent;}
  $('cwRestore').disabled=busy||!!pendingJob||!loaded||head;
  $('cwCompare').disabled=busy||!loaded||!packet||!$('cwCompareRevision').value||$('cwCompareRevision').value===state?.revision_id;
  $('cwResumeReview').hidden=!packet||approved;
  const roomLocked=!!selected&&packet?.locks.rooms.some(r=>r[0]===selected.source.template&&r[1]===selected.source.room_id);
  $('cwSaveGeometry').disabled=busy||!!pendingJob||!selected||!head||roomLocked;
  $('cwLock').disabled=busy||!!pendingJob||!selected||!head;
  if($('cwRoof'))$('cwRoof').disabled=busy||!!pendingJob||!head||!packet||$('cwRoof').dataset.userAuthored==='true';
  syncObjectSelection();
  planUpload?.sync();
}
async function renderState(data, {keepStep=false}={}) {
  const epoch=++revisionEpoch;
  clearViewer(); // Never show geometry belonging to the previous selection.
  const parsed=data.review_packet?await parseReviewFile(JSON.stringify(data.review_packet)):null;
  if(epoch!==revisionEpoch)return;
  state=data;packet=parsed;selected=null;
  renderVersions(data);
  $('cwRevision').value=data.revision_id||'';
  const position=(data.history||[]).findIndex(v=>v.revision_id===data.revision_id);
  const reference=data.history?.[Math.max(0,position-1)];
  $('cwCompareRevision').value=(reference?.revision_id!==data.revision_id?reference:data.history?.find(v=>v.revision_id!==data.revision_id))?.revision_id||'';
  // The measured comparison needs the building type recorded in the version.
  const comparable=!!packet&&packet.scorecard?.typology!=='unknown';
  $('cwCompareControls').hidden=(data.history||[]).length<2||!comparable;
  $('cwCompareUnavailable').hidden=(data.history||[]).length<2||comparable;
  $('cwComparison').hidden=true;
  $('cwVersionBadge').hidden=!data.revision_id;
  $('cwVersionBadge').textContent=data.revision_id?'V'+packet.revision.version+' · '+(data.history.find(v=>v.revision_id===data.revision_id)?.state==='APPROVED'?'معتمدة':'مسودة'):'لا يوجد مخطط بعد';
  $('cwReviewEmpty').hidden=!!packet;$('cwReviewContent').hidden=!packet;
  const approved=data.history?.some(row=>row.revision_id===data.revision_id&&row.state==='APPROVED');
  $('cwExportNote').textContent=approved?'النسخة معتمدة تخطيطيًا. اعرض مجسّمها أو نزّل ملفاتها.':packet?'اعتمد المخطط أولًا لفتح المجسّم والتنزيل.':'صف مشروعك وراجع المخطط أولًا.';
  $('cwApproveConfirm').checked=false;
  $('cwEditApprovalConfirm').checked=false;
  $('cwEditApprovalNotice').hidden=!data.history?.some(v=>v.revision_id===data.revision_id&&v.state==='APPROVED');
  $('cwAssumptions').replaceChildren();
  for(const item of data.planning_assumptions||[])el('li',item,$('cwAssumptions'));
  $('cwAssumptionsCard').hidden=!data.planning_assumptions?.length;
  planUpload?.review(data);
  const details=contextDefaultsText(data.object_actions,packet?.revision);
  if(details){el('li',details,$('cwAssumptions'));$('cwAssumptionsCard').hidden=false;}
  if(packet){
    $('cwLevel').replaceChildren();packet.projections.forEach((p,i)=>{const o=el('option',levelLabel(p),$('cwLevel'));o.value=String(i);});{const roof=$('cwRoof');if(roof){const roofs=packet.projections.filter(isRoofProjection),has=roofs.length>0,userAuthored=roofs.some(p=>p.level_auto!==true);roof.dataset.enabled=String(has);roof.dataset.userAuthored=String(userAuthored);roof.textContent=userAuthored?'سطح من النموذج · يُعدّل من مخططه':has?'إزالة السطح الافتراضي':'إضافة سطح افتراضي';}}
    for(const projection of packet.projections.filter(isRoofProjection)){
      for(const gap of projection.roof_disclosure?.parapet_gaps||[]){
        el('li','حاجز السطح غير مكتمل عند '+gap.room_id+' · الحافة '+gap.edge+' · طول مفتوح '+value(gap.open_length_m)+' م. هذه الفتحة لم تُملأ بافتراض هندسي.', $('cwAssumptions'));$('cwAssumptionsCard').hidden=false;
      }
    }
    draw();table($('cwMetrics'),Object.entries(packet.scorecard.metrics).map(([k,v])=>[metricNames[k]||k,metricValue(k,v)]));
    const checks=Object.entries(packet.review.scopes).map(([k,v])=>[scopeNames[k]||k,{PASS:'اجتاز ضمن نطاق الفحص',FAIL:'يحتاج معالجة',NOT_VERIFIED:'غير متحقق',NOT_APPLICABLE:'لا ينطبق على هذا المشروع'}[v]||v]);
    // محاذاة النوى ووجود عناصر درج أو مصعد لا يثبتان الانتقال الفعلي، حتى في ملف قديم بلا تغطية معلنة.
    const traversal='غير متحقق — '+(packet.review.coverage?.vertical_circulation?.geometry==='MISSING'?'هندسة الدرج أو المصعد بين الأدوار غير مكتملة في النموذج.':'لم يُنفّذ فحص يثبت الانتقال الفعلي عبر الدرج أو المصعد بين الأدوار.');
    checks.push(['المشي/الانتقال الفعلي بين الأدوار',traversal]);
    table($('cwChecks'),checks);
    const findings=data.review_findings||packet.review.issues;
    // A short list: severity, a plain title, and the details folded under it.
    let fixCount=0,infoCount=0;
    $('cwIssues').replaceChildren();for(const issue of findings){
      const requirement=data.requirements?.find(r=>r.id===issue.requirement_id);
      const title=issueNames[issue.code]||(engineerIds()?issue.code:'ملاحظة تحتاج المراجعة');
      const detail=[issue.requirement_id?(requirement?.evidence||issue.requirement_id):'',issue.message?findingMessage(issue.message):''].filter(Boolean).join(' — ');
      const text=title+(issue.requirement_id?' · '+(requirement?.evidence||issue.requirement_id):'')+(issue.message?' — '+findingMessage(issue.message):'');
      const info=issue.severity==='advisory';if(info)infoCount++;else fixCount++;
      const li=el('li',null,$('cwIssues'));li.dataset.severity=info?'info':'fix';
      el('span',info?'للعلم':'يحتاج إصلاحًا',li,'cw-sev');el('strong',title,li,'cw-issue-title');
      // The automatic roof is rebuilt from the top storey after every edit, so
      // an AI request cannot act on it. Its deterministic fix is offered once,
      // in the approval line below.
      const roof=autoRoofFinding(issue);
      if(roof){li.dataset.roof='true';el('span',' (على السطح الافتراضي)',li,'cw-muted');}
      if(!detail&&roof)continue;
      const more=el('details',null,li,'cw-issue-more');el('summary','التفاصيل',more);if(detail)el('p',detail,more);
      if(roof)continue;
      const fix=el('button','اطلب إصلاحها بالكتابة',more);fix.type='button';
      fix.addEventListener('click',()=>{const match=issue.message?.match(/\[([^/\]]+)\/([^\]]+)\]/);const ref=Array.isArray(issue.room_ref)?issue.room_ref:match?.slice(1);if(ref){const index=packet.projections.findIndex(p=>p.primitives.some(r=>r.source.template===ref[0]&&r.source.room_id===ref[1]));if(index>=0){$('cwLevel').value=String(index);draw();selectRoom(packet.projections[index].primitives.find(r=>r.source.template===ref[0]&&r.source.room_id===ref[1]));}}
        $('cwChat').value='عالج الملاحظة التالية مع الحفاظ على المتطلبات المؤكدة والأقفال وعدم حذف الغرف: '+text; $('cwChat').focus();$('cwChatForm').scrollIntoView({block:'center',behavior:'smooth'});});
    }
    if(!findings.length)el('li','لا توجد ملاحظات في الفحوصات المنفذة.', $('cwIssues')).dataset.severity='ok';
    $('cwIssuesSummary').textContent=!findings.length?'✓ لا توجد ملاحظات.':[fixCount?(fixCount===1?'ملاحظة واحدة تحتاج إصلاحًا':notesCount(fixCount)+' تحتاج إصلاحًا'):'',infoCount?(infoCount===1?'ملاحظة واحدة للعلم':notesCount(infoCount)+' للعلم'):''].filter(Boolean).join(' · ');
    $('cwRequirementEvidence').textContent=JSON.stringify(data.requirements||packet.requirements,null,2);
    $('cwDiff').textContent=data.semantic_diff?JSON.stringify(data.semantic_diff,null,2):'اختر نسخة مرجعية للمقارنة.';
  }
  syncAssumptions();
  syncApproval();if(!keepStep)step(packet?3:1);
}
function syncAssumptions(){
  const card=$('cwAssumptionsCard'),more=$('cwAssumptionsMore'),count=$('cwAssumptions').children.length;
  if(!more)return;
  const open=card.classList.contains('cw-open');more.hidden=count<=3;
  more.textContent=open?'عرض أقل':'عرض كل الافتراضات ('+count+')';more.setAttribute('aria-expanded',String(open));
}
function table(parent,rows) { parent.replaceChildren();for(const row of rows){const tr=el('tr',null,parent);row.forEach((v,i)=>el(i?'td':'th',value(v),tr));} }
function showComparison(data) {
  const comparison=data.comparison, options=comparison.measured.options;
  const reference=options.find(o=>o.option_id==='reference'), target=options.find(o=>o.option_id==='target');
  if(!reference||!target)throw new Error('لم تكتمل بيانات المقارنة.');
  const a=reference.scorecard.metrics,b=target.scorecard.metrics;
  table($('cwComparisonRows'),[...new Set([...Object.keys(a),...Object.keys(b)])].map(k=>[metricNames[k]||k,value(a[k]),value(b[k]),value(target.delta_from_reference.scalar[k]??target.delta_from_reference.mapping[k])]));
  $('cwComparisonNote').textContent=comparison.same_program_content?'النسختان تستخدمان برنامج المتطلبات المحفوظ نفسه. القيم غير المقاسة تظهر «غير متحقق».':'برنامج المتطلبات تغيّر بين النسختين؛ اقرأ الفرق في سياقه قبل الاختيار.';
  $('cwComparison').hidden=false;$('cwComparison').scrollIntoView({block:'start',behavior:'smooth'});
  $('cwDiff').textContent=JSON.stringify(data.semantic_diff,null,2);
}
function svg(tag,attrs,parent,text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));if(text!==undefined)e.textContent=text;parent.append(e);return e;}
function draw() {
  if(!packet)return;
  const p=packet.projections[Number($('cwLevel').value)||0];$('cwPlan').replaceChildren();$('cwSpaces').replaceChildren();
  const pad=Math.max(p.site.w,p.site.d)*.035;$('cwPlan').setAttribute('viewBox',[-pad,-pad,p.site.w+2*pad,p.site.d+2*pad].join(' '));
  svg('title',{},$('cwPlan'),'مخطط '+levelLabel(p));
  svg('rect',{x:0,y:0,width:p.site.w,height:p.site.d,fill:'#f7f9fb',stroke:'#668194','stroke-width':.06},$('cwPlan'));
  plotRules?.draw(p,state?.plot_rules,(tag,attrs)=>svg(tag,attrs,$('cwPlan')));
  // Label sizes follow the drawing's scale; a room's name and size stay inside it.
  const extent=Math.max(p.site.w,p.site.d)+2*pad,texts=[];
  for(const item of p.primitives){
    const [x,z,w,d]=item.rect_xz_m;
    const label=roomLabel(item.label);
    const g=svg('g',{class:'cw-room',role:'button',tabindex:0,'aria-label':label,'aria-pressed':false,'data-room':item.source_id},$('cwPlan'));
    svg('rect',{x,y:z,width:w,height:d},g);
    const layout=roomLabelLayout(label,w,d,{min:extent*.009,max:extent*.026}),cx=x+w/2,cy=z+d/2;
    for(const line of layout?.items||[]){
      // The thin halo is proportional to the text, so names stay crisp over lines at any size.
      const attrs={x:cx,y:cy+line.offset,'font-size':line.size,'stroke-width':Math.round(line.size*140)/1000,class:line.kind==='name'?'cw-room-name':'cw-room-size'};
      if(layout.vertical)attrs.transform='rotate(-90 '+cx+' '+cy+')';
      texts.push({text:svg('text',attrs,g,line.text),along:layout.along,size:line.size,offset:line.offset,cy,room:g});
    }
    g.addEventListener('click',()=>selectRoom(item));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectRoom(item);}});
    const b=el('button',label+' · '+value(item.space_rect_area_m2)+' م²',$('cwSpaces'));b.type='button';b.addEventListener('click',()=>selectRoom(item));
  }
  // The layout estimates glyph widths; where the page measures a wider line, the
  // room's whole label shrinks to fit (all reads first, then the writes).
  const scale=new Map();
  for(const line of texts){
    let length=0;try{length=line.text.getComputedTextLength?.()||0;}catch(error){}
    if(length>line.along)scale.set(line.room,Math.min(scale.get(line.room)??1,line.along/length));
  }
  for(const line of texts){
    const ratio=scale.get(line.room);if(!ratio)continue;
    const size=Math.round(line.size*ratio*1000)/1000;
    line.text.setAttribute('font-size',size);line.text.setAttribute('stroke-width',Math.round(size*140)/1000);line.text.setAttribute('y',line.cy+line.offset*ratio);
  }
  for(const opening of state?.openings||[]){
    if(opening.level_index!==p.level_index||!Array.isArray(opening.line)||opening.line.length!==4||!opening.line.every(Number.isFinite))continue;
    const [x1,y1,x2,y2]=opening.line;svg('line',{x1,y1,x2,y2,stroke:opening.kind==='doors'?'#b75f12':'#117bc0','stroke-width':.14},$('cwPlan'));
  }
  $('cwExtent').textContent='الأبواب بالبرتقالي والنوافذ بالأزرق عند وجودها في النسخة. الموقع '+p.site.w+' × '+p.site.d+' م · '+floorLabel(p.level_index);
  $('cwSelection').hidden=true;
}
function selectRoom(item) {
  selected=item;$('cwSelection').hidden=false;$('cwSelectedName').textContent=roomLabel(item.label);
  ['cwX','cwZ','cwW','cwD'].forEach((id,i)=>{$(id).value=item.rect_xz_m[i];});
  const locked=packet.locks.rooms.some(r=>r[0]===item.source.template&&r[1]===item.source.room_id);
  $('cwLock').textContent=locked?'إلغاء قفل الفراغ':'قفل الفراغ';$('cwLock').dataset.locked=String(locked);
  syncApproval();
  root.querySelectorAll('[data-room]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.room===item.source_id)));
}
async function refresh(rid, keepStep=false) {
  const epoch=++revisionEpoch;clearViewer();
  const next=await api({action:'state',...(rid?{revision_id:rid}:{})});
  if(epoch!==revisionEpoch)return;
  await renderState(next,{keepStep});
}
function confirmPaid(text,go,title='بدء توليد بالذكاء الاصطناعي؟'){
  const dialog=$('cwPaidConfirm');$('cwPaidConfirmTitle').textContent=title;$('cwPaidConfirmText').textContent=text;$('cwConfirmGenerate').textContent=go;
  if(typeof dialog.showModal!=='function')return Promise.resolve(window.confirm(text));
  return new Promise(resolve=>{dialog.returnValue='';dialog.addEventListener('close',()=>resolve(dialog.returnValue==='go'),{once:true});dialog.showModal();$('cwCancelGenerate').focus();});
}
// A confirmed program of three or more storeys needs a plan call and an
// openings call per storey plus a repair: the default 8 left no room for one
// retried call (live jobs 6cd7137f, 1b0eb00e). Unless the owner picked another
// limit, such a program gets 12, the highest the server allows. A limit is a
// ceiling: a job spends only the calls it needs.
function generationCalls(program){
  const chosen=Number($('cwBudget').value),storeys=Array.isArray(program?.levels)?program.levels.length:0;
  return chosen===8&&storeys>=3?12:chosen;
}
async function generation(option) {
  if(pendingJob)throw new Error('توجد مهمة معلّقة. استعد حالتها أولًا.');
  if(!$('cwConfirmed').checked)throw new Error('راجع برنامج المشروع وأكد المتطلبات أولًا.');
  const source=planUpload.command();
  const plot=source.source_id?{}:plotRules.command(); // validated before any paid call
  const program=source.source_id?briefProgram():($('cwType').value==='residential'?residentialOptions.program(briefProgram(),option):briefProgram());
  const reading=source.source_id?{}:briefReader.command(); // the confirmed smart-reading card, checked before any paid call
  const body={action:'generate',job_id:crypto.randomUUID(),...program,...source,...reading,option,confirmed:true,expected_head:state?.head||null,max_provider_calls:(source.source_id&&planUpload.calls())||generationCalls(reading.program)};
  // A generation is a paid, multi-minute run: the owner confirms it first.
  const name=source.source_id?'قراءة المخطط المرفوع':'«'+(root.querySelector('[data-option="'+option+'"]')?.closest('article')?.querySelector('h2')?.textContent.replace(/\s*·\s*مقترح لك$/,'')||'البديل '+option)+'»';
  const read=source.source_id?planUpload.confirm():null;
  if(!await confirmPaid(read?read.text:'سيبدأ إعداد '+name+'. يستغرق عادةً من دقيقتين إلى أربع دقائق، ويستهلك من رصيد الذكاء الاصطناعي. يمكنك مغادرة الصفحة والعودة لمتابعته.',read?read.go:'ابدأ التوليد',read?.title)){status(read?'لم تبدأ القراءة، ولم يُستهلك أي رصيد.':'لم يبدأ التوليد، ولم يُستهلك أي رصيد.');return;}
  beginJob(body.job_id,null,!!read);
  Object.assign(body,plot);
  setBusy(true);$('cwRecoverJob').hidden=false;status(read?read.sent:'جارٍ إرسال البديل '+option+' وحفظ رقم المهمة…');
  try{const result=await api(body);await handleJob(result.job);}
  catch(e){progressPhase('UNKNOWN');status('لم يصل تأكيد الطلب. استخدم متابعة المهمة للتحقق قبل أي طلب جديد. '+ownerMessage(e?.code,e?.message,''),true);}
  finally{setBusy(false);}
}
async function handleJob(job) {
  if(!job||job.id!==pendingJob)throw new Error('لم تصل حالة المهمة المطلوبة.');
  if(job.state==='SUCCEEDED'){
    const used=Number.isInteger(job.provider_calls)&&job.provider_calls>0?(progressState?.read?' القراءات المستخدمة: ':' طلبات الذكاء الاصطناعي المستخدمة: ')+job.provider_calls+'.':'';
    stopProgress();
    const referenceRevision=typeof job.reference_revision_id==='string'&&job.reference_revision_id?job.reference_revision_id:null;
    clearTimeout(pollTimer);pendingJob=null;try{localStorage.removeItem(jobKey());}catch(e){}
    $('cwRecoverJob').hidden=true;$('cwDismissJob').hidden=true;await refresh(job.revision_id);
    let comparisonShown=false;
    if(referenceRevision&&referenceRevision!==job.revision_id){
      try{
        const data=await api({action:'compare',reference_revision_id:referenceRevision,target_revision_id:job.revision_id},true);
        showComparison(data);
        if([...$('cwCompareRevision').options].some(o=>o.value===referenceRevision))$('cwCompareRevision').value=referenceRevision;
        comparisonShown=true;
      }catch(e){}
    }
    status((comparisonShown?'تم حفظ المخطط سحابيًا وعرض أثره المقاس من نسخة المصدر الدقيقة. راجعه قبل الاعتماد.':'تم حفظ المخطط سحابيًا. راجعه قبل الاعتماد.')+used);setBusy(false);return;
  }
  if(job.choice&&job.choice.kind==='generated_version'){
    // A newer revision landed while this paid job ran. Its result is kept apart:
    // never discarded, never written over the newer revision. The owner chooses.
    stopProgress();clearTimeout(pollTimer);pendingJob=null;try{localStorage.removeItem(jobKey());}catch(e){}
    $('cwRecoverJob').hidden=true;$('cwDismissJob').hidden=true;$('cwResumeJob').hidden=true;
    if(job.choice.adopted_revision_id){hideChoice();await refresh(job.choice.adopted_revision_id);status(CHOICE_ADOPTED);return;}
    await refresh();showChoice(job.id);
    status('حُفظ تعديل أحدث أثناء التوليد، فاحتفظنا بالنسخة المولّدة منفصلة دون أن تستبدل تعديلك. اختر: الإبقاء على تعديلك أو استخدام النسخة المولّدة.',true);return;
  }
  if(['FAILED','INTERRUPTED'].includes(job.state)){
    // A finished job holds nothing open: release the workspace at once instead
    // of asking the owner to find «إنهاء المتابعة». Only a resumable failure
    // keeps its id, for the paid «استئناف» action.
    stopProgress();clearTimeout(pollTimer);pendingJob=null;try{localStorage.removeItem(jobKey());}catch(e){}
    failedJob=job.can_resume===true?job.id:null;
    $('cwRecoverJob').hidden=true;$('cwDismissJob').hidden=true;$('cwResumeJob').hidden=!failedJob;
    const reason=typeof job.error_message==='string'&&job.error_message.length<=500&&/[\u0600-\u06FF]/.test(job.error_message)?job.error_message:'تعذّر إكمال التوليد.';
    const next=failedJob?' يمكنك استئناف المراحل المحفوظة (استدعاء مدفوع) أو تعديل طلبك.':'';
    status(job.state==='INTERRUPTED'?'توقف الخادم أثناء المهمة. راجع قائمة النسخ؛ يمكنك إرسال الطلب مرة أخرى إن لم تظهر نسخة جديدة.':reason+' لم تُحفظ نسخة جديدة، ونسخك السابقة كما هي.'+next,true);setBusy(false);return;
  }
  progressPhase(job.phase||job.state,true);if(job.progress?.total)$('cwJobHeartbeat').textContent+=' اكتملت '+job.progress.completed+' من '+job.progress.total+' مجموعات في هذه المرحلة.';status('جارٍ إعداد المخطط. يمكنك مغادرة الصفحة والعودة لمتابعة المهمة نفسها.');
  clearTimeout(pollTimer);pollTimer=setTimeout(()=>poll().catch(e=>{status('انقطع الاتصال. اضغط متابعة المهمة عند عودة الشبكة.',true);}),4000);
}
const CHOICE_ADOPTED='اعتُمدت النسخة المولّدة كنسخة جديدة. تعديلك السابق محفوظ في سجل النسخ ويمكن استعادته.';
function showChoice(jobId){const box=$('cwChoice');box.dataset.job=jobId;box.hidden=false;}
function hideChoice(){const box=$('cwChoice');if(box){box.hidden=true;delete box.dataset.job;}}
function keepEdit(){hideChoice();status('أبقينا تعديلك كما هو. النسخة المولّدة محفوظة، ويمكنك استخدامها لاحقًا من «نسخ مولّدة محفوظة».');return listGenerated();}
async function useGenerated(jobId){
  if(!jobId)throw new Error('اختر النسخة المولّدة من جديد.');
  if(!state?.head)throw new Error('افتح آخر نسخة أولًا.');
  const data=await api({action:'adopt_generated',job_id:jobId,expected_head:state.head,confirmed:true});
  hideChoice();await refresh(data.revision_id);status(CHOICE_ADOPTED);await listGenerated();
}
async function listGenerated(){
  const host=$('cwGeneratedVersions');if(!host)return;
  let data;try{data=await api({action:'generated_versions'});}catch(e){return;}
  const open=(Array.isArray(data?.versions)?data.versions:[]).filter(v=>typeof v?.job_id==='string'&&!v.adopted_revision_id);
  host.replaceChildren();host.hidden=!open.length;
  if(!open.length)return;
  el('p','نسخ مولّدة محفوظة لم تُعتمد بعد. استخدام إحداها يحفظها كنسخة جديدة دون توليد جديد، ويبقى تعديلك في السجل.',host,'cw-muted');
  for(const v of open){const b=el('button','استخدام النسخة المولّدة المحفوظة',host);b.type='button';b.dataset.mutate='';b.addEventListener('click',()=>run(()=>useGenerated(v.job_id)));}
}
async function poll(){if(!pendingJob)return;try{await handleJob((await api({action:'job',job_id:pendingJob})).job);}catch(e){progressPhase('UNKNOWN');if(e.code==='REVISION_NOT_FOUND')$('cwDismissJob').hidden=false;throw e;}}
function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type}));const a=el('a',null,document.body);a.href=url;a.download=name;a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function bytes64(str){return Uint8Array.from(atob(str),c=>c.charCodeAt(0));}
async function exportFile(format, display=false){
  const revisionId=state?.revision_id, epoch=revisionEpoch;
  if(!revisionId)return;
  const levelIndex=packet.projections[Number($('cwLevel').value)||0].level_index;
  if(display)clearViewer();
  const viewEpoch=viewerEpoch;
  const current=()=>revisionEpoch===epoch&&state?.revision_id===revisionId&&(!display||(viewerEpoch===viewEpoch&&activeStep===4));
  const data=await api({action:'artifact',format,revision_id:revisionId,level_index:levelIndex});
  if(!current())return;
  const bytes=bytes64(data.data_base64);
  await verifyArtifactDelivery(data, bytes, format, packet.revision, levelIndex);
  if(!current())return;
  if(display){
    const host=$('cwViewer');host.hidden=false;
    try{
      const dispose=await showApprovedGLTF(host,bytes,revisionId,{isCurrent:current,projections:packet.projections,receipt:data.receipt,
        onSelectObject:selection=>{if(current())selectApprovedObject(selection);},
        onFailure:message=>{if(current()){status(message,true);host.hidden=false;showViewerFallback(host,message);}}});
      if(!current()){dispose?.();return;}
      viewerDispose=dispose;host.dataset.revision=revisionId;$('cwShow3D').hidden=true;
      status('هذا مجسّم النسخة المعتمدة نفسها. الإضاءة والخامات للعرض فقط ولا تغيّر المخطط.');
    }catch(error){if(current()){showViewerFallback(host,ownerMessage(error?.code,error?.message,'تعذّر عرض النموذج ثلاثي الأبعاد على هذا الجهاز.'));throw error;}}
  }else{
    // One file per tap, named for the owner: «مخطط-الدور-الأرضي-V7.svg». The
    // receipt manifest is an engineer file (engineer view on).
    const ext=(String(data.filename||'').match(/\.[A-Za-z0-9]{1,8}$/)||['.'+format])[0];
    const floor=['svg','dxf'].includes(format)?String($('cwLevel').selectedOptions?.[0]?.textContent||'').split('·')[0].trim():'';
    const stem={svg:'مخطط',dxf:'مخطط-CAD',pdf:'مخطط-كل-الأدوار',gltf:'نموذج-3D',ifc:'نموذج-IFC',review:'ملف-مراجعة'}[format]||'ملف';
    const name=[stem,floor,packet.revision.version?'V'+packet.revision.version:''].filter(Boolean).join('-').replace(/[\s/\\:*?"<>|·]+/g,'-').replace(/-+/g,'-')+ext;
    download(bytes,name,data.mime);
    const manifest=data.receipt&&$('cwEngineerIds')?.checked===true;
    if(manifest)download(JSON.stringify(data.receipt,null,2),name.slice(0,-ext.length)+'-manifest.json','application/json');
    status(manifest?'تم تنزيل الملف وبيان النسخة المرافق له.':'تم تنزيل الملف: '+name);
  }
}
async function verifyArtifactDelivery(data, bytes, format, revision, levelIndex) {
  const mismatch = () => new Error('تعذّر مطابقة ملف التسليم مع النسخة المختارة. أعد فتح النسخة ثم حاول مجددًا.');
  if(format==='review'){
    const review = await parseReviewFile(new TextDecoder().decode(bytes));
    if(review.revision.id!==revision.id || review.revision.model_hash!==revision.model_hash ||
       review.revision.content_hash!==revision.content_hash)throw mismatch();
    return;
  }
  const receipt=data.receipt;
  if(data.revision_id!==revision.id || receipt?.revision_id!==revision.id ||
     receipt.model_hash!==revision.model_hash || receipt.content_hash!==revision.content_hash ||
     receipt.artifact_bytes!==bytes.byteLength)throw mismatch();
  if((format==='svg'||format==='dxf') && (receipt.level_index!==levelIndex || receipt.format!==format.toUpperCase()))throw mismatch();
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  const sha=Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');
  if(sha!==receipt.artifact_sha256)throw mismatch();
}
function showViewerFallback(host,message){
  host.replaceChildren();const panel=el('div',null,host,'cw-viewer-fallback');
  el('h3','المخطط محفوظ — العرض ثلاثي الأبعاد غير متاح',panel);el('p',message,panel);
  if($('cwPlan')){const plan=$('cwPlan').cloneNode(true);plan.removeAttribute('id');plan.querySelectorAll('[tabindex]').forEach(n=>n.removeAttribute('tabindex'));panel.append(plan);}
  const back=el('button','متابعة المخطط ثنائي الأبعاد',panel);back.type='button';back.addEventListener('click',()=>step(3));
  const retry=el('button','إعادة محاولة 3D',panel);retry.type='button';retry.addEventListener('click',()=>run(()=>exportFile('gltf',true)));
}
async function projectList(){
  const s=await window.ACS_AUTH.freshSession();if(!s)return;
  const data=await window.ACS_AUTH.acsFetchJSON('/v1/auth/projects',{action:'list'},s.access_token);
  $('cwProject').replaceChildren();for(const p of data.projects){const o=el('option',p.name,$('cwProject'));o.value=p.id;}$('cwProject').value=projectId;
}
function mount(){
  Object.assign(issueNames,TRANSCRIPTION.issues); // names of the upload transcription findings
  if(root)return;
  root=el('section',null,document.body);root.id='designWorkspace';root.setAttribute('aria-label','مساحة تصميم المشروع');
  root.innerHTML=`
  <header class="cw-top"><div><span class="cw-brand" lang="en">ACS</span><div class="cw-muted">استوديو التصميم</div></div><div class="cw-toolbar"><label for="cwProject">المشروع</label><select id="cwProject" aria-label="المشروع الحالي"></select><button id="cwNewProject" type="button">مشروع جديد</button><button id="cwLogout" type="button">خروج</button></div></header>
  <p id="cwLoading" class="cw-loading-note" role="status">جارٍ فتح مشروعك ونسخه المحفوظة…</p>
  <form id="cwNewProjectForm" hidden class="cw-card"><label for="cwProjectName">اسم المشروع الجديد</label><input id="cwProjectName" maxlength="200" required><div class="cw-actions"><button type="submit" data-mutate class="cw-primary">إنشاء المشروع</button><button id="cwCancelProject" type="button">إلغاء</button></div></form>
  <h1 class="cw-sr">خطوات مشروعك</h1>
  <nav class="cw-steps" aria-label="خطوات المشروع"><ol><li><button type="button" data-step="1" aria-current="step"><span class="cw-step-n" aria-hidden="true">١</span><span class="cw-step-t">الوصف</span></button></li><li><button type="button" data-step="2"><span class="cw-step-n" aria-hidden="true">٢</span><span class="cw-step-t">التصميم</span></button></li><li><button type="button" data-step="3"><span class="cw-step-n" aria-hidden="true">٣</span><span class="cw-step-t">المراجعة</span></button></li><li><button type="button" data-step="4"><span class="cw-step-n" aria-hidden="true">٤</span><span class="cw-step-t">ثلاثي الأبعاد</span></button></li></ol><span id="cwVersionBadge" class="cw-badge">جارٍ فتح المشروع</span></nav>
  <div class="cw-statusbar"><div id="cwStatus" class="cw-status" role="status" aria-live="polite"></div><div class="cw-status-actions"><button id="cwRecoverJob" type="button" hidden>متابعة المهمة</button><button id="cwDismissJob" type="button" hidden>إنهاء المتابعة والسماح بطلب جديد</button><button id="cwReload" type="button" class="cw-quiet" title="تحديث المشروع" aria-label="تحديث المشروع"><span aria-hidden="true">↻</span> تحديث</button></div></div>
  <section id="cwChoice" class="cw-card" role="group" aria-labelledby="cwChoiceTitle" hidden><h2 id="cwChoiceTitle">أي نسخة تريد اعتمادها؟</h2><p class="cw-muted">تعديلك هو النسخة الحالية. النسخة المولّدة محفوظة منفصلة ولن يُحسب توليدها مرة ثانية. ما لا تختاره يبقى محفوظًا.</p><div class="cw-actions"><button id="cwKeepEdit" type="button">الإبقاء على تعديلي</button><button id="cwUseGenerated" type="button" class="cw-primary">استخدام النسخة المولّدة</button></div></section>
  <div id="cwGeneratedVersions" class="cw-card" hidden></div>
  <section id="cwJobProgress" class="cw-card cw-job-progress" aria-label="متابعة إعداد المخطط" hidden><strong id="cwJobPhase" role="status" aria-live="polite"></strong><progress id="cwJobActivity" aria-label="جارٍ تنفيذ المهمة"></progress><output id="cwJobElapsed" aria-live="off"></output><p id="cwJobHeartbeat" class="cw-muted" aria-live="off"></p><p class="cw-muted">يمكنك إغلاق الصفحة والعودة؛ نتابع المهمة نفسها ويظهر المخطط عند اكتماله.</p></section>
  <section data-step-panel="1"><form id="cwBriefForm" class="cw-card cw-form" novalidate><h2>صف مشروعك</h2><label for="cwType">نوع المبنى</label><select id="cwType"><option value="residential">سكني / عمارة / فيلا</option><option value="warehouse">مستودع / صناعي</option></select><label for="cwBrief">الوصف</label><textarea id="cwBrief" rows="6" maxlength="58000" placeholder="مثال: فيلا من دورين على أرض ٢٠ × ٣٠ م، أربع غرف نوم ومجلس قريب من المدخل…"></textarea><div class="cw-fields"><div><label for="cwWidth">عرض الأرض (م)</label><input id="cwWidth" type="text" inputmode="decimal" autocomplete="off" placeholder="غير محدد"></div><div><label for="cwDepth">عمق الأرض (م)</label><input id="cwDepth" type="text" inputmode="decimal" autocomplete="off" placeholder="غير محدد"></div><div><label for="cwLevels">عدد الأدوار</label><input id="cwLevels" type="text" inputmode="numeric" autocomplete="off" placeholder="غير محدد"></div></div><details id="cwBriefMore" class="cw-more"><summary>تفاصيل إضافية (اختياري)</summary><div id="cwBriefMoreBody"><h3>متطلبات تريد التحقق منها</h3><p class="cw-muted">أعداد أو مساحات محددة. اكتب بقية القيود في الوصف.</p><div class="cw-table-wrap"><table class="cw-req-table"><thead><tr><th>المتطلب</th><th>الاستخدام</th><th>القيمة</th><th></th></tr></thead><tbody id="cwRequirements"></tbody></table></div><button id="cwAddRequirement" type="button">+ إضافة متطلب</button></div></details><label class="cw-check"><input id="cwConfirmed" type="checkbox">راجعت الوصف والأرقام، وأؤكد استخدامها في التصميم.</label><button type="submit" class="cw-primary cw-next">التالي: اختيار التصميم <span aria-hidden="true">←</span></button></form></section>
  <section data-step-panel="2" hidden><div class="cw-card cw-step-intro"><h2>اختر تصميمًا</h2><p class="cw-muted">كل خيار يرتّب غرفك بطريقة مختلفة. اختر واحدًا لنصمّمه لك.</p><p class="cw-muted cw-paid-note">يبدأ التصميم بعد تأكيدك، ويستغرق من دقيقتين لمبنى صغير إلى نحو ربع ساعة لمبنى من ثلاثة أدوار، ويستهلك من رصيد الذكاء الاصطناعي.</p></div><div class="cw-options"><article class="cw-card cw-option"><span class="cw-option-code">A</span><h2>استثمار المساحة</h2><p>تركيز على توزيع البرنامج المطلوب ضمن الأبعاد والقيود.</p><button data-option="A" data-mutate>توليد البديل A</button></article><article class="cw-card cw-option"><span class="cw-option-code">B</span><h2>وضوح الحركة</h2><p>تركيز على العلاقات بين الفراغات وقرب الأنشطة المرتبطة.</p><button data-option="B" data-mutate>توليد البديل B</button></article><article class="cw-card cw-option"><span class="cw-option-code">C</span><h2>المرونة والفصل</h2><p>تركيز على فصل الاستخدامات ومرونة التوسع المطلوبة.</p><button data-option="C" data-mutate>توليد البديل C</button></article></div><details id="cwGenerationSettings" class="cw-more"><summary>خيارات متقدمة</summary><label for="cwBudget">أقصى عدد لطلبات الذكاء الاصطناعي</label><select id="cwBudget"><option value="3">حتى 3 طلبات</option><option value="6">حتى 6 طلبات</option><option value="8" selected>حتى 8 طلبات</option><option value="12">حتى 12 طلبًا</option></select><p class="cw-muted">يحتاج كل دور نحو طلبين؛ الحد يمنع تجاوز العدد المختار، ويُرفع تلقائيًا إلى 12 لبرنامج مؤكد من ثلاثة أدوار أو أكثر ما لم تختر غيره.</p></details></section>
  <section data-step-panel="3" hidden><div id="cwReviewEmpty" class="cw-card"><h2>لا يوجد مخطط بعد</h2><p>صف مشروعك واختر تصميمًا لتبدأ المراجعة.</p></div><div id="cwReviewContent" hidden><div class="cw-review-bar"><div class="cw-pick"><label for="cwLevel">الدور</label><select id="cwLevel"></select></div><div class="cw-pick"><label for="cwRevision">النسخة</label><select id="cwRevision"></select></div></div><label id="cwEditApprovalNotice" class="cw-check cw-card cw-notice" hidden><input id="cwEditApprovalConfirm" type="checkbox">أفهم أن أي تعديل ينشئ مسودة جديدة تحتاج اعتمادًا، وأن النسخة المعتمدة تبقى محفوظة.</label><div class="cw-review"><div class="cw-card cw-plan-card"><div class="cw-drawing"><svg id="cwPlan" role="group" aria-label="المخطط القابل للاختيار"></svg><p id="cwExtent"></p></div></div><aside class="cw-card cw-rooms"><form id="cwSelection" hidden><h3 id="cwSelectedName"></h3><div class="cw-fields cw-fields-2"><div><label for="cwW">العرض (م)</label><input id="cwW" type="number" step="any" min=".01"></div><div><label for="cwD">العمق (م)</label><input id="cwD" type="number" step="any" min=".01"></div></div><details class="cw-position-details"><summary>الموضع (X/Z)</summary><div class="cw-fields cw-fields-2"><div><label for="cwX">X (م)</label><input id="cwX" type="number" step="any"></div><div><label for="cwZ">Z (م)</label><input id="cwZ" type="number" step="any"></div></div></details><div class="cw-actions"><button id="cwSaveGeometry" type="submit" class="cw-primary" data-mutate>حفظ التعديل</button><button id="cwLock" type="button" data-mutate>قفل الفراغ</button></div></form><details id="cwSpacesBox" class="cw-spaces-box"><summary>الغرف والمساحات</summary><div id="cwSpaces" class="cw-space-list"></div></details><p class="cw-hint">اضغط غرفة في المخطط لتعديل مقاسها.</p></aside></div><section class="cw-card cw-findings" aria-labelledby="cwIssuesTitle"><h2 id="cwIssuesTitle">ملاحظات المراجعة</h2><p id="cwIssuesSummary" class="cw-findings-summary" role="status"></p><ul id="cwIssues" class="cw-issues"></ul><details class="cw-more"><summary>تفاصيل الفحوصات والقياسات</summary><div class="cw-table-wrap"><table><tbody id="cwChecks"></tbody></table></div><div class="cw-table-wrap"><table><tbody id="cwMetrics"></tbody></table></div><p class="cw-muted">الفحوصات تخص نطاقها فقط؛ المتطلبات غير المقاسة تحتاج مراجعة مختص.</p></details></section><section id="cwAssumptionsCard" class="cw-card cw-assumptions-card" hidden><h2>افتراضات التصميم</h2><ul id="cwAssumptions"></ul><button id="cwAssumptionsMore" type="button" class="cw-link" aria-expanded="false" hidden></button></section><section class="cw-card cw-approve-card" aria-labelledby="cwApproveTitle"><h2 id="cwApproveTitle">اعتماد المخطط</h2><p id="cwApprovalNote" role="status"></p><button id="cwApprovalFix" type="button" hidden>إزالة السطح الافتراضي</button><label class="cw-check"><input id="cwApproveConfirm" type="checkbox">راجعت هذه النسخة وأعتمدها تخطيطيًا فقط. هذا لا يُعد اعتمادًا إنشائيًا أو تصريحًا للتنفيذ.</label><button id="cwApprove" class="cw-primary" data-mutate disabled>اعتماد المخطط</button></section><section class="cw-card cw-chat-card"><h2>تعديل بالكتابة</h2><form id="cwChatForm"><label for="cwChat">ما الذي تريد تغييره؟</label><textarea id="cwChat" rows="3" maxlength="6000" placeholder="مثال: انقل منطقة التجهيز بجوار الشحن، مع الحفاظ على الأقفال الحالية."></textarea><p class="cw-muted">يستخدم الذكاء الاصطناعي (حتى 3 طلبات من الرصيد). كل تعديل يصبح مسودة جديدة، والأقفال محفوظة.</p><button id="cwChatSubmit" type="submit" data-mutate>إرسال التعديل</button><p id="cwChatHint" class="cw-muted" hidden></p></form></section><details id="cwMore" class="cw-card cw-more cw-advanced-tools"><summary>أدوات متقدمة</summary><div id="cwMoreBody"><div class="cw-actions"><button id="cwRestore" data-mutate>استعادة كمسودة جديدة</button></div><button id="cwCompare">عرض المقارنة</button><label class="cw-check"><input id="cwEngineerIds" type="checkbox">إظهار المعرّفات الهندسية (للمهندس)</label><details><summary>مصادر المتطلبات وفرق النسخ</summary><pre id="cwRequirementEvidence"></pre><pre id="cwDiff"></pre></details></div></details></div></section>
  <section data-step-panel="4" hidden class="cw-card cw-final"><h2>المخطط المعتمد</h2><p id="cwExportNote"></p><button id="cwShow3D" class="cw-primary" disabled>عرض المجسّم ثلاثي الأبعاد</button><div id="cwViewer" hidden aria-label="عارض النسخة المعتمدة"></div><h3 class="cw-downloads-title">تنزيل</h3><div class="cw-actions cw-downloads" role="group" aria-label="تنزيل ملفات النسخة"><button data-format="pdf" disabled>المخطط PDF</button><button data-format="svg" disabled>صورة الدور SVG</button></div><details class="cw-more"><summary>ملفات للمهندس</summary><div class="cw-actions" role="group" aria-label="ملفات للمهندس"><button data-format="dxf" disabled>DXF</button><button data-format="ifc" disabled>IFC4</button><button data-format="gltf" disabled>3D (glTF)</button><button data-format="review">ملف مراجعة</button></div><p class="cw-muted">ملفات PDF وSVG وDXF لوحات بمقياس رسم قياسي: جدران بسماكتها في النموذج، وأبواب ونوافذ ودرج، وأبعاد بالمتر، ومساحات صافية. اتجاه فتح الأبواب افتراض رسم. IFC4 يصدّر الفراغات والسطح كمنطقة مرجعية. ليست مخططات تنفيذية أو نموذجًا إنشائيًا.</p></details></section>
  <dialog id="cwPaidConfirm" class="cw-dialog" aria-labelledby="cwPaidConfirmTitle"><form method="dialog"><h2 id="cwPaidConfirmTitle">بدء توليد بالذكاء الاصطناعي؟</h2><p id="cwPaidConfirmText"></p><div class="cw-actions"><button id="cwConfirmGenerate" value="go" class="cw-primary">ابدأ التوليد</button><button id="cwCancelGenerate" value="cancel">ليس الآن</button></div></form></dialog>
  <footer><a href="/privacy.html" target="_blank" rel="noopener">الخصوصية وحفظ البيانات</a></footer>`;
  root.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>step(Number(b.dataset.step),{record:true})));
  window.addEventListener('popstate',event=>{const n=Number(event.state?.acsStep);if(!root.hidden&&n>=1&&n<=4&&n!==activeStep)step(n);});
  const objectPanel=el('section',null,null,'cw-card');objectPanel.id='cwObjectSelection';objectPanel.hidden=true;
  el('p',null,objectPanel).id='cwObjectDescription';
  const objectConfirmation=el('label',null,objectPanel,'cw-check');objectConfirmation.id='cwObjectConfirmation';
  const objectConfirm=el('input',null,objectConfirmation);objectConfirm.type='checkbox';objectConfirm.id='cwObjectConfirm';
  el('span','أؤكد إزالة العنصر وإنشاء مسودة جديدة تحتاج اعتمادًا جديدًا؛ النسخة المعتمدة السابقة محفوظة.',objectConfirmation);
  const objectRemove=el('button','إزالة العنصر وحفظ مسودة',objectPanel);objectRemove.type='button';objectRemove.id='cwObjectRemove';objectRemove.dataset.mutate='';
  objectConfirm.addEventListener('change',syncObjectSelection);objectRemove.addEventListener('click',()=>run(removeSelectedObject));$('cwViewer').after(objectPanel);
  const compareLabel=el('label','قارن مع نسخة محفوظة');compareLabel.htmlFor='cwCompareRevision';
  const compareSelect=el('select',null);compareSelect.id='cwCompareRevision';
  const compareControls=el('div',null,null,'cw-toolbar');compareControls.id='cwCompareControls';
  $('cwCompare').before(compareControls);compareControls.append(compareLabel,compareSelect,$('cwCompare'));
  const compareUnavailable=el('p',englishServerMessages.OPTION_TYPOLOGY_UNKNOWN+' فرق كل تعديل محفوظ في سجل النسخ.',null,'cw-muted');compareUnavailable.id='cwCompareUnavailable';compareUnavailable.hidden=true;compareControls.after(compareUnavailable);
  compareSelect.addEventListener('change',syncApproval);
  const resumeReview=el('button','العودة إلى مراجعة النواقص');resumeReview.id='cwResumeReview';resumeReview.type='button';resumeReview.hidden=true;
  $('cwExportNote').after(resumeReview);
  resumeReview.addEventListener('click',()=>{step(3,{record:true});$('cwIssues').closest('section').scrollIntoView({block:'start'});status('راجع الملاحظات التالية، ثم اكتب التعديل المطلوب في المحادثة.');});
  const comparison=el('section',null,null,'cw-card');comparison.id='cwComparison';comparison.hidden=true;
  comparison.innerHTML='<h2>مقارنة النسخ</h2><p id="cwComparisonNote"></p><div class="cw-table-wrap"><table><thead><tr><th>المقياس</th><th>النسخة المرجعية</th><th>النسخة المختارة</th><th>الفرق</th></tr></thead><tbody id="cwComparisonRows"></tbody></table></div>';
  $('cwChatForm').closest('section').before(comparison);
  root.querySelectorAll('[data-option]').forEach(b=>b.addEventListener('click',()=>run(()=>generation(b.dataset.option))));
  root.querySelectorAll('[data-format]').forEach(b=>b.addEventListener('click',()=>run(()=>exportFile(b.dataset.format))));
  $('cwShow3D').addEventListener('click',()=>run(()=>exportFile('gltf',true)));
  briefEditor=createBriefEditor(root,{storageKey:draftKey,onError:safeError});
  residentialOptions=createResidentialOptions(root,{storageKey:()=>draftKey()+':residential',api,onError:safeError,buildable:()=>plotRules?.buildable()??null,issueNames,scopeNames,
    confirmedProgram:()=>briefReader?.current()??null});
  const resumeButton=el('button','استئناف المراحل المحفوظة · استدعاء مدفوع',$('cwRecoverJob').parentElement);resumeButton.id='cwResumeJob';resumeButton.type='button';resumeButton.hidden=true;
  resumeButton.addEventListener('click',()=>run(async()=>{
    const oldId=failedJob;if(!oldId||pendingJob)return;
    if(!await confirmPaid('استئناف المراحل المحفوظة يرسل طلبًا جديدًا إلى الذكاء الاصطناعي ويستهلك من رصيده، وقد يستغرق بضع دقائق. المراحل المكتملة لا تُعاد.','استئناف المراحل')){status('لم يبدأ الاستئناف، ولم يُستهلك أي رصيد.');return;}
    const nextId=crypto.randomUUID();beginJob(nextId);failedJob=null;resumeButton.hidden=true;$('cwRecoverJob').hidden=false;
    try{await handleJob((await api({action:'resume',job_id:nextId,resume_job_id:oldId,confirmed:true,max_provider_calls:Number($('cwBudget').value)})).job);}
    catch(e){
      // The service answered with a refusal: no job started, so nothing stays open.
      if(e?.status>0){stopProgress();pendingJob=null;try{localStorage.removeItem(jobKey());}catch(err){}$('cwRecoverJob').hidden=true;failedJob=oldId;resumeButton.hidden=false;throw e;}
      progressPhase('UNKNOWN');status('لم يصل تأكيد طلب الاستئناف. اضغط «متابعة المهمة» للتحقق قبل أي طلب جديد. '+ownerMessage(e?.code,e?.message,''),true);
    }
  }));
  planUpload=createPlanUpload(root,{storageKey:()=> 'acs_plan_source:'+window.ACS_AUTH.storageScope(),onError:safeError,onOk:()=>{if($('cwStatus').classList.contains('bad'))status('');}});
  plotRules=createPlotRules(root,{storageKey:()=>draftKey()+':plot',issueNames,scopeNames});
  briefReader=createBriefReader(root,{api,confirmPaid,briefEditor,onError:safeError,storageKey:()=>draftKey()+':program',
    jobKey:()=>'acs_brief_read_job:'+window.ACS_AUTH.storageScope(),localDraftKeys:()=>[draftKey(),draftKey()+':residential',draftKey()+':plot']});
  // Optional sizes (building block, setbacks, parking, extra requirements) sit
  // under one «تفاصيل إضافية» so the description and the land stay in view.
  $('cwBriefMoreBody').prepend(...[$('cwBuildingFields'),$('cwPlot')].filter(Boolean));
  // A wide screen has room for the room list beside the plan; a phone keeps it folded.
  if(window.matchMedia?.('(min-width: 821px)').matches)$('cwSpacesBox').open=true;
  $('cwAssumptionsMore').addEventListener('click',()=>{$('cwAssumptionsCard').classList.toggle('cw-open');syncAssumptions();});
  const sourceGenerate=el('button','قراءة المخطط وحفظ مسودة',null,'cw-primary');sourceGenerate.id='cwGenerateSource';sourceGenerate.type='button';sourceGenerate.dataset.mutate='';sourceGenerate.hidden=true;
  root.querySelector('[data-step-panel="2"] .cw-card').append(sourceGenerate);
  sourceGenerate.addEventListener('click',()=>run(()=>generation('A')));
  $('cwBriefForm').addEventListener('submit',e=>{e.preventDefault();try{const confirmedProgram=briefProgram();const uploaded=!!planUpload.command().source_id;if(!$('cwConfirmed').checked)throw new Error('أكد المتطلبات قبل المتابعة.');if(!uploaded){residentialOptions.validate();residentialOptions.prepare(confirmedProgram);}root.querySelector('.cw-options').hidden=uploaded;sourceGenerate.hidden=!uploaded;planUpload.step2(uploaded);status(uploaded?'ملفك محفوظ. ابدأ قراءة المخطط عندما تكون جاهزًا.':'اختر تصميمًا لنبدأ؛ ستراجعه قبل الاعتماد.');step(2,{record:true});}catch(err){safeError(err);}});
  $('cwReload').addEventListener('click',()=>run(async()=>{await refresh();status('فتحنا آخر نسخة محفوظة.');}));
  $('cwRecoverJob').addEventListener('click',()=>run(poll));
  $('cwKeepEdit').addEventListener('click',()=>run(keepEdit));
  $('cwUseGenerated').addEventListener('click',()=>run(()=>useGenerated($('cwChoice').dataset.job)));
  $('cwDismissJob').addEventListener('click',()=>{stopProgress();pendingJob=null;failedJob=null;$('cwResumeJob').hidden=true;clearTimeout(pollTimer);try{localStorage.removeItem(jobKey());}catch(e){}$('cwRecoverJob').hidden=true;$('cwDismissJob').hidden=true;setBusy(false);status('انتهت المتابعة. تحقق من آخر نسخة قبل بدء مقترح جديد.');});
  $('cwRevision').addEventListener('change',()=>{syncApproval();run(()=>refresh($('cwRevision').value,true));});
  $('cwLevel').addEventListener('change',()=>{draw();planUpload.review(state,packet?.projections?.[Number($('cwLevel').value)]?.level_index??0);});
  try{$('cwEngineerIds').checked=localStorage.getItem('acs_engineer_ids')==='1';}catch(e){}
  $('cwEngineerIds').addEventListener('change',()=>{
    try{localStorage.setItem('acs_engineer_ids',$('cwEngineerIds').checked?'1':'0');}catch(e){}
    if(!state||busy)return;const revision=$('cwRevision').value,reference=$('cwCompareRevision').value;
    renderVersions(state);$('cwRevision').value=revision;$('cwCompareRevision').value=reference;
    if(packet)renderState(state,{keepStep:true}).catch(safeError);
  });
  $('cwType').addEventListener('change',projectCopy);
  $('cwApproveConfirm').addEventListener('change',syncApproval);
  $('cwApprovalFix').addEventListener('click',()=>{$('cwRoof')?.click();});
  $('cwApprove').addEventListener('click',()=>run(async()=>{const transcribed=state.authority?.source_transcription===true;const data=await api({action:'approve',expected_head:state.head,confirmed:true,acknowledge_concept_only:true,...(transcribed?{acknowledge_transcription:true}:{})},true);await renderState(data);step(4,{record:true});status(transcribed?TRANSCRIPTION.approved:'اعتُمد المخطط. اعرض المجسّم أو نزّل ملفاته.');}));
  $('cwLock').addEventListener('click',()=>run(async()=>{const data=await api({action:'set_room_lock',expected_head:state.head,room_ref:[selected.source.template,selected.source.room_id],locked:$('cwLock').dataset.locked!=='true'},true);await renderState(data);status('حُفظ القفل في نسخة جديدة.');}));
  $('cwChatForm').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
    if(pendingJob)throw new Error('تابع المهمة الحالية أولًا.');
    if(!state?.head||state.revision_id!==state.head)throw new Error('اختر آخر نسخة قبل التعديل.');
    if(!$('cwEditApprovalNotice').hidden&&!$('cwEditApprovalConfirm').checked)throw new Error('أكد إنشاء مسودة جديدة قبل تعديل النسخة المعتمدة.');
    const text=$('cwChat').value.trim();if(!text)throw new Error('اكتب طلب التعديل.');
    const body={action:'chat_edit',job_id:crypto.randomUUID(),expected_head:state.head,notes:[{text}],confirmed:true,max_provider_calls:3};
    beginJob(body.job_id);
    $('cwRecoverJob').hidden=false;setBusy(true);status('جارٍ إرسال طلب التعديل…');
    try{await handleJob((await api(body)).job);}catch(err){progressPhase('UNKNOWN');status('لم يصل تأكيد طلب التعديل. تابع المهمة قبل إرسال طلب آخر. '+ownerMessage(err?.code,err?.message,''),true);}
  });});
  $('cwSelection').addEventListener('submit',e=>{e.preventDefault();run(async()=>{if(!$('cwEditApprovalNotice').hidden&&!$('cwEditApprovalConfirm').checked)throw new Error('أكد إنشاء مسودة جديدة قبل تعديل النسخة المعتمدة.');const data=await api({action:'edit_geometry',expected_head:state.head,room_ref:[selected.source.template,selected.source.room_id],rect:['cwX','cwZ','cwW','cwD'].map(id=>Number($(id).value))});await renderState(data);status('حُفظ التعديل كنسخة جديدة.');});});
  {const roof=el('button','إضافة سطح افتراضي',$('cwRestore').parentNode);roof.type='button';roof.id='cwRoof';roof.setAttribute('data-mutate','');roof.title='سطح مسطح بحاجز 0.9 م يتبع الدور الأخير. افتراض معلن وليس دورًا مشغولًا.';
  roof.addEventListener('click',()=>run(async()=>{if(!headRevisionSelected())throw new Error('اختر آخر نسخة قبل تعديل السطح.');if(!$('cwEditApprovalNotice').hidden&&!$('cwEditApprovalConfirm').checked)throw new Error('أكد إنشاء مسودة جديدة قبل تعديل النسخة المعتمدة.');const enabled=roof.dataset.enabled!=='true';const data=await api({action:'set_roof',expected_head:state.head,enabled});await renderState(data);status(enabled?'أُضيف السطح الافتراضي كنسخة جديدة.':'أُزيل السطح الافتراضي كنسخة جديدة. لن يُضاف تلقائيًا في التوليد القادم.');}));}
  $('cwRestore').addEventListener('click',()=>run(async()=>{await renderState(await api({action:'restore',expected_head:state.head,source_revision_id:state.revision_id,note:'استعادة نسخة محفوظة من واجهة المشروع'},true));status('تمت الاستعادة كمسودة جديدة؛ النسخ المعتمدة السابقة محفوظة.');}));
  $('cwCompare').addEventListener('click',()=>run(async()=>{const reference=$('cwCompareRevision').value;if(!reference||reference===state.revision_id)throw new Error('اختر نسخة مرجعية مختلفة للمقارنة.');const data=await api({action:'compare',reference_revision_id:reference,target_revision_id:state.revision_id},true);showComparison(data);status('المقارنة من النسختين المحفوظتين.');}));
  $('cwLogout').addEventListener('click',()=>{stopProgress();clearTimeout(pollTimer);revisionEpoch++;clearViewer();state=null;packet=null;root.hidden=true;document.body.classList.remove('acs-connected');$('acsLogout')?.click();});
  $('cwNewProject').addEventListener('click',()=>{$('cwNewProjectForm').hidden=false;$('cwProjectName').focus();});
  $('cwCancelProject').addEventListener('click',()=>{$('cwNewProjectForm').hidden=true;});
  $('cwProject').addEventListener('change',()=>{revisionEpoch++;clearViewer();state=null;packet=null;root.hidden=true;try{localStorage.setItem('acs_project_v1',JSON.stringify({id:$('cwProject').value}));}catch(e){}location.reload();});
  $('cwNewProjectForm').addEventListener('submit',e=>{e.preventDefault();run(async()=>{const s=await window.ACS_AUTH.freshSession();const data=await window.ACS_AUTH.acsFetchJSON('/v1/auth/projects',{action:'create',name:$('cwProjectName').value},s.access_token);localStorage.setItem('acs_project_v1',JSON.stringify(data.projects[0]));location.reload();});});
}
async function start(){
  if(starting||!window.ACS?.projectId||!window.ACS?.authSession)return;
  starting=true;projectId=window.ACS.projectId;mount();root.classList.add('cw-loading');root.hidden=false;document.body.classList.add('acs-connected');
  status('جارٍ فتح مشروعك ونسخه المحفوظة…');
  try{const data=await api({action:'state'});await renderState(data);fillBrief(data);await projectList();status('مشروعك جاهز.');}
  catch(e){safeError(e);fillBrief(null);}
  finally{root.classList.remove('cw-loading');starting=false;try{history.replaceState({...(history.state||{}),acsStep:activeStep},'');}catch(e){}}
  try{await planUpload.restore();}catch(e){safeError(e);}
  stopProgress();pendingJob=null;
  try{const saved=JSON.parse(localStorage.getItem(jobKey())||'null');if(typeof saved?.jobId==='string'&&saved.jobId)beginJob(saved.jobId,saved);}catch(e){}
  if(pendingJob){$('cwRecoverJob').hidden=false;setBusy(false);poll().catch(safeError);}
  listGenerated();
}
window.addEventListener('storage',event=>{
  if(event.key!=='acs_supabase_session_v1'||!root)return;
  let nextUser=null;try{nextUser=JSON.parse(event.newValue||'null')?.user?.id;}catch(error){}
  if(nextUser&&nextUser===window.ACS?.authSession?.user?.id)return;
  revisionEpoch++;clearViewer();state=null;packet=null;root.hidden=true;
});
document.addEventListener('acs:authenticated',()=>{start().catch(e=>{if(root)safeError(e);});});
if(document.body.classList.contains('acs-entered'))start().catch(e=>{if(root)safeError(e);});
