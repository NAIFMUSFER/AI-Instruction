import {parseReviewFile} from '../core/plan-review-packet.mjs';
import {showApprovedGLTF} from './approved-viewer.mjs';
import {createBriefEditor} from './brief-review.mjs';
import {createPlanUpload} from './plan-upload.mjs';

const $ = id => document.getElementById(id);
const scopeNames = {rectangular_geometry:'الأبعاد والتداخلات',program:'المتطلبات المقاسة',topology:'الترابط والفتحات',vertical_circulation:'الحركة بين الأدوار',warehouse_expansion_reserve:'حماية مساحة التوسّع المعلنة',regulatory_compliance:'الامتثال التنظيمي',structural_safety:'السلامة الإنشائية'};
const metricNames = {site_area_m2:'مساحة الموقع (م²)',level_count:'الأدوار',space_instance_count:'الفراغات',space_rect_area_m2:'مساحة حدود الفراغات (م²)',space_count_by_role:'عدد الفراغات حسب الاستخدام',space_area_by_role_m2:'المساحة حسب الاستخدام',zone_area_by_role_m2:'مساحات التشغيل (م²)',dock_count:'الأرصفة',rack_group_count:'مجموعات الرفوف',storage_capacity_positions:'مواضع التخزين',travel_distance_m:'مسافة الحركة (م)',throughput_per_hour:'معدل التشغيل في الساعة',rack_modeled_bay_count:'خلايا الرفوف المقاسة',rack_geometric_position_count:'المواضع الهندسية',configured_route_length_m:'أطوال المسارات (م)'};
const issueNames = {PROGRAM_NOT_CONFIRMED:'لم يؤكد برنامج المتطلبات',REQUIREMENT_MISMATCH:'المخطط لا يحقق متطلبًا مؤكدًا',REQUIREMENT_NOT_SPECIFIED:'يوجد متطلب لم تحدد قيمته',INFERENCE_NOT_CONFIRMED:'متطلب مقترح يحتاج التأكيد',PLAN_ZONE_UNRESOLVED:'منطقة تحتاج استكمال هندستها',VERIFICATION_UNAVAILABLE:'تعذّر إكمال التحقق',ACS_GEOMETRY_FINDING:'ملاحظة في الأبعاد أو الفتحات تحتاج المراجعة',WAREHOUSE_EXPANSION_RESERVE_INTRUSION:'التخطيط يشغل جزءًا من مساحة التوسّع المعلنة',WAREHOUSE_EXPANSION_RESERVE_NOT_VERIFIED:'تحتاج مساحة التوسّع المعلنة إلى هندسة قابلة للتحقق'};
Object.assign(metricNames,{efficiency:'كفاءة المساحة',gross_floor_area_m2:'إجمالي مساحة الأرضيات (م²)',net_floor_area_m2:'صافي مساحة الأرضيات (م²)',unclassified_space_area_m2:'مساحة الفراغات غير المصنفة (م²)',unclassified_space_count:'عدد الفراغات غير المصنفة'});
const value = v => v == null ? 'غير متحقق' : typeof v === 'object'
  ? (Array.isArray(v) ? v.map(value) : Object.entries(v).map(([k,n])=>(metricNames[k]||k)+': '+value(n))).join('\n') || 'لا توجد بيانات'
  : String(v);
const floorLabel = index => index === 0 ? 'الدور الأرضي' : index === 1 ? 'الدور الأول' : 'الدور '+index;
function roomLabel(label) {
  const names={entrance:'مدخل المبنى',stairs:'الدرج',stair:'الدرج',elevator:'المصعد',living:'الصالة',kitchen:'المطبخ',bedroom:'غرفة النوم',bathroom:'دورة المياه'};
  return names[label] || (/^flat_\d+$/.test(label) ? 'شقة '+label.slice(5) : label);
}
function projectCopy() {
  const residential=$('cwType').value==='residential';
  $('cwTypeHelpTitle').textContent=residential?'لمشروعك السكني':'للمستودعات';
  $('cwTypeHelp').textContent=residential?'اذكر عدد الشقق والغرف، وما إذا كنت تفضّل مجلسًا منفصلًا. أضف جهة الشارع والمداخل إن كانت معروفة. يمكنك تعديل هذه التفاصيل أثناء المراجعة.':'حدد وحدات التخزين والرفوف والمعدات وارتفاعاتها والأرصفة والممرات ومناطق التشغيل. البيانات غير المحددة تبقى غير متحققة.';
  $('cwChat').placeholder=residential?'مثال: افصل مجلس الضيوف عن الصالة، وأكمل اتصال الدرج بالدور العلوي، مع الحفاظ على الأقفال الحالية.':'مثال: انقل منطقة التجهيز بجوار الشحن، مع الحفاظ على الأقفال الحالية.';
}
let root, briefEditor, planUpload, projectId, state = null, packet = null, selected = null, busy = false, pendingJob = null, pollTimer = null, revisionEpoch = 0, viewerDispose = null;
let progressState=null,progressTimer=null;
const draftKey = () => 'acs_brief_draft:' + window.ACS_AUTH.storageScope();
const jobKey = () => 'acs_plan_job:' + window.ACS_AUTH.storageScope();
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
  const labels={SUBMITTING:'جارٍ إرسال الطلب…',CHECKING:'جارٍ التحقق من حالة المهمة…',QUEUED:'المهمة في قائمة الانتظار',RUNNING:'الخادم يعالج المخطط',UNKNOWN:'تعذّر التحقق من الحالة. اضغط متابعة المهمة عند عودة الاتصال.'};
  const text=labels[phase]||labels.CHECKING;
  if($('cwJobPhase').textContent!==text)$('cwJobPhase').textContent=text;
  $('cwJobProgress').dataset.phase=phase;
  $('cwJobActivity').hidden=phase==='UNKNOWN';
  if(confirmed)progressState.lastSeenAt=Date.now();
  progressTick();
}
function beginJob(id,saved=null){
  clearInterval(progressTimer);pendingJob=id;
  const valid=typeof saved?.startedAt==='number'&&Number.isFinite(saved.startedAt)&&saved.startedAt>0&&saved.startedAt<=Date.now();
  progressState={startedAt:valid?saved.startedAt:Date.now(),fromSubmission:saved===null||(valid&&saved.fromSubmission!==false),lastSeenAt:0};
  try{localStorage.setItem(jobKey(),JSON.stringify({jobId:id,startedAt:progressState.startedAt,fromSubmission:progressState.fromSubmission}));}catch(e){}
  $('cwJobProgress').hidden=false;$('cwJobProgress').dataset.startedAt=String(progressState.startedAt);
  progressPhase(saved?'CHECKING':'SUBMITTING');progressTimer=setInterval(progressTick,1000);
}
function stopProgress(){clearInterval(progressTimer);progressTimer=null;progressState=null;if($('cwJobProgress'))$('cwJobProgress').hidden=true;}
function safeError(e) {
  const friendly={APPROVAL_REQUIRED:'اعتمد النسخة المختارة قبل التحويل والتصدير.',DOWNSTREAM_GEOMETRY_NOT_SPECIFIED:'تحتاج عناصر النسخة إلى أبعاد إضافية قبل عرض 3D. اطلب استكمالها في المحادثة ثم راجع النسخة الجديدة.',DOWNSTREAM_GEOMETRY_INVALID:'توجد أبعاد غير صالحة للتحويل إلى 3D. راجع العناصر وعدّلها في نسخة جديدة.',STALE_REVISION:'وصل تعديل أحدث لهذا المشروع. افتح آخر نسخة ثم أعد العملية.',LOCK_VIOLATION:'هذا التعديل يمس عنصرًا مقفلًا. عدّل الطلب أو ألغِ قفله أولًا.'};
  status(friendly[e?.code]||e?.message||'تعذّر إكمال العملية. حاول مجددًا.',true);
}
function setBusy(on) { busy=on;root.setAttribute('aria-busy',String(on));root.querySelectorAll('[data-mutate]').forEach(b=>{b.disabled=on||!!pendingJob;});syncApproval(); }
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
function step(n) {
  if(n===2&&$('cwGenerateSource')){
    const uploaded=$('cwStartMode').value==='upload';root.querySelector('.cw-options').hidden=uploaded;$('cwGenerateSource').hidden=!uploaded;
    $('cwGenerateSource').textContent=$('cwSourceMode').value==='revise'?'اقتراح التعديل وحفظ مسودة':'قراءة المخطط وحفظ مسودة';
  }
  root.querySelectorAll('[data-step-panel]').forEach(p=>{p.hidden=Number(p.dataset.stepPanel)!==n;});
  root.querySelectorAll('[data-step]').forEach(b=>{if(Number(b.dataset.step)===n)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});
  if(n!==4&&viewerDispose){viewerDispose();viewerDispose=null;$('cwViewer').hidden=true;}
}
function briefProgram() { return briefEditor.program(); }
function fillBrief(data) { briefEditor.fill(data,packet?.scorecard?.typology);projectCopy(); }
function syncApproval() {
  if(!root)return;
  const head=state?.revision_id&&state.revision_id===state.head;
  $('cwApprove').disabled=busy||!!pendingJob||!head||state?.authority?.can_approve_concept!==true||!$('cwApproveConfirm').checked;
  const approved=!!state?.history?.some(v=>v.revision_id===state.revision_id&&v.state==='APPROVED');
  root.querySelectorAll('[data-format]:not([data-format=review]),#cwShow3D').forEach(b=>{b.disabled=busy||!approved;});
  root.querySelector('[data-format=review]').disabled=busy||!packet;
  $('cwChatSubmit').disabled=busy||!!pendingJob||!head;
  $('cwRestore').disabled=busy||!!pendingJob||!state?.revision_id||head;
  $('cwCompare').disabled=busy||!packet||!$('cwCompareRevision').value||$('cwCompareRevision').value===state?.revision_id;
  $('cwResumeReview').hidden=!packet||approved;
  const roomLocked=!!selected&&packet?.locks.rooms.some(r=>r[0]===selected.source.template&&r[1]===selected.source.room_id);
  $('cwSaveGeometry').disabled=busy||!!pendingJob||!selected||!head||roomLocked;
  $('cwLock').disabled=busy||!!pendingJob||!selected||!head;
  planUpload?.sync();
}
async function renderState(data, {keepStep=false}={}) {
  const epoch=++revisionEpoch;
  const parsed=data.review_packet?await parseReviewFile(JSON.stringify(data.review_packet)):null;
  if(epoch!==revisionEpoch)return;
  state=data;packet=parsed;selected=null;
  $('cwRevision').replaceChildren();
  $('cwCompareRevision').replaceChildren();
  for(const revision of data.history||[]){
    const label='V'+revision.version+' · '+(revision.state==='APPROVED'?'معتمدة':'مسودة')+' · '+revision.note.replace(/\s*[·،]?\s*task:[0-9a-f-]+$/,'');
    const o=el('option',label,$('cwRevision'));o.value=revision.revision_id;
    const ref=el('option',label,$('cwCompareRevision'));ref.value=revision.revision_id;
  }
  $('cwRevision').value=data.revision_id||'';
  const position=(data.history||[]).findIndex(v=>v.revision_id===data.revision_id);
  const reference=data.history?.[Math.max(0,position-1)];
  $('cwCompareRevision').value=(reference?.revision_id!==data.revision_id?reference:data.history?.find(v=>v.revision_id!==data.revision_id))?.revision_id||'';
  $('cwCompareControls').hidden=(data.history||[]).length<2;
  $('cwComparison').hidden=true;
  $('cwVersionBadge').textContent=data.revision_id?'V'+packet.revision.version+' · '+(data.history.find(v=>v.revision_id===data.revision_id)?.state==='APPROVED'?'نسخة معتمدة':'مسودة محفوظة سحابيًا'):'مشروع جديد';
  $('cwReviewEmpty').hidden=!!packet;$('cwReviewContent').hidden=!packet;
  $('cwExportNote').textContent=packet?'الملفات مشتقة من النسخة المختارة. اعتمدها بعد معالجة الفحوصات لفتح التصدير.':'اختر مخططًا وراجعه أولًا.';
  $('cwApproveConfirm').checked=false;
  if(packet){
    $('cwLevel').replaceChildren();packet.projections.forEach((p,i)=>{const o=el('option',floorLabel(p.level_index),$('cwLevel'));o.value=String(i);});
    draw();table($('cwMetrics'),Object.entries(packet.scorecard.metrics).map(([k,v])=>[metricNames[k]||k,value(v)]));
    table($('cwChecks'),Object.entries(packet.review.scopes).map(([k,v])=>[scopeNames[k]||k,{PASS:'اجتاز ضمن نطاق الفحص',FAIL:'يحتاج معالجة',NOT_VERIFIED:'غير متحقق',NOT_APPLICABLE:'لا ينطبق على هذا المشروع'}[v]||v]));
    $('cwIssues').replaceChildren();for(const issue of data.review_findings||packet.review.issues)el('li',(issueNames[issue.code]||issue.code)+(issue.requirement_id?' · '+issue.requirement_id:'')+(issue.message?' — '+issue.message:''),$('cwIssues'));
    if(!packet.review.issues.length)el('li','لا توجد ملاحظات في الفحوصات المنفذة.', $('cwIssues'));
    $('cwApprovalNote').textContent=data.authority?.can_approve_concept?'الفحوصات التخطيطية جاهزة للمراجعة والاعتماد المبدئي.':'عالِج الفحوصات غير المكتملة أو المتطلبات المخالفة قبل الاعتماد.';
    $('cwRequirementEvidence').textContent=JSON.stringify(data.requirements||packet.requirements,null,2);
    $('cwDiff').textContent=data.semantic_diff?JSON.stringify(data.semantic_diff,null,2):'اختر نسخة مرجعية للمقارنة.';
  }
  syncApproval();if(!keepStep)step(packet?3:1);
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
  svg('title',{},$('cwPlan'),'مخطط '+floorLabel(p.level_index));
  svg('rect',{x:0,y:0,width:p.site.w,height:p.site.d,fill:'#f7f9fb',stroke:'#668194','stroke-width':.06},$('cwPlan'));
  for(const item of p.primitives){
    const [x,z,w,d]=item.rect_xz_m;
    const label=roomLabel(item.label);
    const g=svg('g',{class:'cw-room',role:'button',tabindex:0,'aria-label':label,'aria-pressed':false,'data-room':item.source_id},$('cwPlan'));
    svg('rect',{x,y:z,width:w,height:d},g);
    const size=Math.max(.16,Math.min(w,d)*.105);svg('text',{x:x+w/2,y:z+d/2,'font-size':size},g,label.slice(0,40));svg('text',{x:x+w/2,y:z+d/2+size*1.6,'font-size':size*.8},g,w+' × '+d+' م');
    g.addEventListener('click',()=>selectRoom(item));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectRoom(item);}});
    const b=el('button',label+' · '+item.space_rect_area_m2+' م²',$('cwSpaces'));b.type='button';b.addEventListener('click',()=>selectRoom(item));
  }
  $('cwExtent').textContent='الموقع '+p.site.w+' × '+p.site.d+' م · '+floorLabel(p.level_index);
  $('cwSelection').hidden=true;
}
function selectRoom(item) {
  selected=item;$('cwSelection').hidden=false;$('cwSelectedName').textContent=roomLabel(item.label);
  ['cwX','cwZ','cwW','cwD'].forEach((id,i)=>{$(id).value=item.rect_xz_m[i];});
  const locked=packet.locks.rooms.some(r=>r[0]===item.source.template&&r[1]===item.source.room_id);
  $('cwLock').textContent=locked?'إلغاء قفل الفراغ':'قفل الفراغ';$('cwLock').dataset.locked=String(locked);
  $('cwSaveGeometry').disabled=locked||state.revision_id!==state.head||busy||!!pendingJob;
  $('cwLock').disabled=state.revision_id!==state.head||busy||!!pendingJob;
  root.querySelectorAll('[data-room]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.room===item.source_id)));
}
async function refresh(rid, keepStep=false) { await renderState(await api({action:'state',...(rid?{revision_id:rid}:{})}),{keepStep}); }
async function generation(option) {
  if(pendingJob)throw new Error('توجد مهمة معلّقة. استعد حالتها أولًا.');
  if(!$('cwConfirmed').checked)throw new Error('راجع برنامج المشروع وأكد المتطلبات أولًا.');
  const program=briefProgram();
  const body={action:'generate',job_id:crypto.randomUUID(),...program,...planUpload.command(),option,confirmed:true,expected_head:state?.head||null,max_provider_calls:Number($('cwBudget').value)};
  beginJob(body.job_id);
  setBusy(true);$('cwRecoverJob').hidden=false;status('جارٍ إرسال البديل '+option+' وحفظ رقم المهمة…');
  try{const result=await api(body);await handleJob(result.job);}
  catch(e){progressPhase('UNKNOWN');status('لم يصل تأكيد الطلب. استخدم متابعة المهمة للتحقق قبل أي طلب جديد. '+e.message,true);}
  finally{setBusy(false);}
}
async function handleJob(job) {
  if(!job||job.id!==pendingJob)throw new Error('لم تصل حالة المهمة المطلوبة.');
  if(job.state==='SUCCEEDED'){
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
    status(comparisonShown?'تم حفظ المخطط سحابيًا وعرض أثره المقاس من نسخة المصدر الدقيقة. راجعه قبل الاعتماد.':'تم حفظ المخطط سحابيًا. راجعه قبل الاعتماد.');setBusy(false);return;
  }
  if(['FAILED','INTERRUPTED'].includes(job.state)){
    stopProgress();
    clearTimeout(pollTimer);$('cwDismissJob').hidden=false;
    const reason=typeof job.error_message==='string'&&job.error_message.length<=500?job.error_message:'تعذّر إكمال التوليد ('+(job.error_code||'GENERATION_FAILED')+').';
    status(job.state==='INTERRUPTED'?'توقف الخادم أثناء المهمة. تحقق من آخر النسخ المحفوظة؛ لن يُعاد التوليد تلقائيًا.':reason+' لم تُحفظ نسخة جديدة. نسخك السابقة محفوظة؛ لن يُعاد التوليد تلقائيًا.',true);return;
  }
  progressPhase(job.state,true);status('جارٍ إعداد المخطط. يمكنك مغادرة الصفحة والعودة لمتابعة المهمة نفسها.');
  clearTimeout(pollTimer);pollTimer=setTimeout(()=>poll().catch(e=>{status('انقطع الاتصال. اضغط متابعة المهمة عند عودة الشبكة.',true);}),4000);
}
async function poll(){if(!pendingJob)return;try{await handleJob((await api({action:'job',job_id:pendingJob})).job);}catch(e){progressPhase('UNKNOWN');if(e.code==='REVISION_NOT_FOUND')$('cwDismissJob').hidden=false;throw e;}}
function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type}));const a=el('a',null,document.body);a.href=url;a.download=name;a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function bytes64(str){return Uint8Array.from(atob(str),c=>c.charCodeAt(0));}
async function exportFile(format, display=false){
  const data=await api({action:'artifact',format,revision_id:state.revision_id,level_index:packet.projections[Number($('cwLevel').value)||0].level_index});
  const bytes=bytes64(data.data_base64);
  if(display){
    if(viewerDispose)viewerDispose();$('cwViewer').hidden=false;
    viewerDispose=await showApprovedGLTF($('cwViewer'),bytes,state.revision_id);status('يعرض 3D النسخة المعتمدة نفسها، دون إعادة توليد المخطط.');
  }else{
    download(bytes,data.filename,data.mime);
    if(data.receipt)download(JSON.stringify(data.receipt,null,2),'acs-'+format+'-manifest.json','application/json');
    status('تم تجهيز الملف وبيان النسخة المرافق له.');
  }
}
async function projectList(){
  const s=await window.ACS_AUTH.freshSession();if(!s)return;
  const data=await window.ACS_AUTH.acsFetchJSON('/v1/auth/projects',{action:'list'},s.access_token);
  $('cwProject').replaceChildren();for(const p of data.projects){const o=el('option',p.name,$('cwProject'));o.value=p.id;}$('cwProject').value=projectId;
}
function mount(){
  if(root)return;
  root=el('section',null,document.body);root.id='designWorkspace';root.setAttribute('aria-label','مساحة تصميم المشروع');
  root.innerHTML=`
  <header class="cw-top"><div><span class="cw-brand" lang="en">ACS</span><div class="cw-muted">استوديو التصميم</div></div><div class="cw-toolbar"><label for="cwProject">المشروع</label><select id="cwProject" aria-label="المشروع الحالي"></select><button id="cwNewProject" type="button">مشروع جديد</button><button id="cwLogout" type="button">خروج</button></div></header>
  <form id="cwNewProjectForm" hidden class="cw-card"><label for="cwProjectName">اسم المشروع الجديد</label><input id="cwProjectName" maxlength="200" required><div class="cw-actions"><button type="submit" data-mutate class="cw-primary">إنشاء المشروع</button><button id="cwCancelProject" type="button">إلغاء</button></div></form>
  <div class="cw-toolbar"><div><h1>من الفكرة إلى مخطط محفوظ</h1><p class="cw-muted">حدد متطلباتك، راجع البدائل، ثم اعتمد النسخة التي تريد تحويلها وتصديرها.</p></div><span id="cwVersionBadge" class="cw-badge">جارٍ فتح المشروع</span></div>
  <nav class="cw-steps" aria-label="مراحل التصميم"><button data-step="1" aria-current="step">01 · المتطلبات</button><button data-step="2">02 · البدائل</button><button data-step="3">03 · المخطط والمراجعة</button><button data-step="4">04 · 3D والتصدير</button></nav>
  <div class="cw-toolbar"><div id="cwStatus" class="cw-status" role="status" aria-live="polite"></div><button id="cwReload" type="button">تحديث المشروع</button><button id="cwRecoverJob" type="button" hidden>متابعة المهمة</button><button id="cwDismissJob" type="button" hidden>إنهاء المتابعة والسماح بطلب جديد</button></div>
  <section id="cwJobProgress" class="cw-card cw-job-progress" aria-label="متابعة إعداد المخطط" hidden><strong id="cwJobPhase" role="status" aria-live="polite"></strong><progress id="cwJobActivity" aria-label="جارٍ تنفيذ المهمة"></progress><output id="cwJobElapsed" aria-live="off"></output><p id="cwJobHeartbeat" class="cw-muted" aria-live="off"></p><p class="cw-muted">يمكنك العودة لاحقًا ومتابعة المهمة نفسها. يظهر المخطط بعد اكتماله وحفظه.</p></section>
  <section data-step-panel="1" class="cw-grid"><form id="cwBriefForm" class="cw-card"><h2>متطلبات المشروع</h2><label for="cwType">نوع المشروع</label><select id="cwType"><option value="residential">سكني / عمارة / فيلا</option><option value="warehouse">مستودع / صناعي</option></select><label for="cwBrief">صف المشروع والاستخدامات والعلاقات المطلوبة</label><textarea id="cwBrief" rows="6" maxlength="58000" placeholder="الموقع، الفراغات المطلوبة، المداخل، الحركة، والقيود التي يجب الحفاظ عليها…"></textarea><div class="cw-fields"><div><label for="cwWidth">عرض الموقع (م)</label><input id="cwWidth" type="number" min="0.1" step="any" placeholder="غير محدد"></div><div><label for="cwDepth">عمق الموقع (م)</label><input id="cwDepth" type="number" min="0.1" step="any" placeholder="غير محدد"></div><div><label for="cwLevels">عدد الأدوار</label><input id="cwLevels" type="number" min="1" step="1" placeholder="غير محدد"></div></div><h3>برنامج الفراغات والمتطلبات المقاسة</h3><p class="cw-muted">أضف عدد الفراغات أو المساحات أو الأرصفة المطلوب التحقق منها. اكتب بقية القيود في الوصف لمراجعتها مع المخطط.</p><div class="cw-table-wrap"><table><thead><tr><th>المتطلب</th><th>الاستخدام</th><th>القيمة</th><th></th></tr></thead><tbody id="cwRequirements"></tbody></table></div><button id="cwAddRequirement" type="button">+ إضافة متطلب</button><label class="cw-check"><input id="cwConfirmed" type="checkbox">راجعت الوصف والأبعاد وبرنامج المتطلبات وأؤكد استخدامها في المقترح.</label><button type="submit" class="cw-primary">متابعة إلى البدائل ←</button></form><aside class="cw-card"><h2>ماذا سنحفظ؟</h2><p>وصفك ومتطلباتك مع كل نسخة، ثم تعديلات المخطط والأقفال وقرار الاعتماد.</p><p class="cw-muted">الحفظ السحابي يتم بعد اكتمال كل عملية. الكتابة التي لم ترسلها بعد تُستعاد على هذا الجهاز.</p><h3 id="cwTypeHelpTitle">للمستودعات</h3><p id="cwTypeHelp" class="cw-muted">حدد وحدات التخزين والرفوف والمعدات وارتفاعاتها والأرصفة والممرات ومناطق التشغيل. البيانات غير المحددة تبقى غير متحققة.</p><a href="/plan-review/" target="_blank" rel="noopener">فتح ملف مراجعة محلي</a></aside></section>
  <section data-step-panel="2" hidden><div class="cw-card"><h2>اختر هدف المقترح</h2><p class="cw-muted">كل زر يولد بديلًا واحدًا ويحفظه كمسودة جديدة. النسخة المعتمدة السابقة تبقى محفوظة. الأهداف التالية ليست ترتيبًا للجودة أو شهادة مطابقة.</p><details id="cwGenerationSettings"><summary>إعدادات التوليد المتقدمة</summary><label for="cwBudget">أقصى عدد استدعاءات المزود لهذا المقترح</label><select id="cwBudget"><option value="3">حتى 3 استدعاءات</option><option value="6" selected>حتى 6 استدعاءات</option><option value="12">حتى 12 استدعاء</option></select><p class="cw-muted">قد يُقسّم المخطط إلى مراحل ضمن هذا السقف. لا يبدأ توليد بديل آخر تلقائيًا، ولا توجد تكلفة مالية ثابتة يمكن تأكيدها قبل رد المزود.</p></details></div><div class="cw-options"><article class="cw-card"><span class="cw-option-code">A</span><h2>استثمار المساحة</h2><p>تركيز على توزيع البرنامج المطلوب ضمن الأبعاد والقيود.</p><button data-option="A" data-mutate class="cw-primary">توليد البديل A</button></article><article class="cw-card"><span class="cw-option-code">B</span><h2>وضوح الحركة</h2><p>تركيز على العلاقات بين الفراغات وقرب الأنشطة المرتبطة.</p><button data-option="B" data-mutate class="cw-primary">توليد البديل B</button></article><article class="cw-card"><span class="cw-option-code">C</span><h2>المرونة والفصل</h2><p>تركيز على فصل الاستخدامات ومرونة التوسع المطلوبة.</p><button data-option="C" data-mutate class="cw-primary">توليد البديل C</button></article></div></section>
  <section data-step-panel="3" hidden><div id="cwReviewEmpty" class="cw-card"><h2>لا توجد مسودة محفوظة بعد</h2><p>أكد متطلباتك ثم ولّد مقترحًا لبدء المراجعة.</p></div><div id="cwReviewContent" hidden><div class="cw-toolbar"><label for="cwRevision">النسخة المحفوظة</label><select id="cwRevision"></select><label for="cwLevel">الدور</label><select id="cwLevel"></select><button id="cwRestore" data-mutate>استعادة كمسودة جديدة</button><button id="cwCompare">عرض المقارنة</button></div><div class="cw-review"><div class="cw-card"><div class="cw-drawing"><svg id="cwPlan" role="group" aria-label="المخطط القابل للاختيار"></svg><p id="cwExtent"></p></div><p class="cw-muted">حدود الفراغات وأبعادها بالمتر. ملفات CAD الحالية تمثل حدود الفراغات؛ ليست مخططات تنفيذية كاملة.</p></div><aside class="cw-card"><h2>الفراغات</h2><form id="cwSelection" hidden><h3 id="cwSelectedName"></h3><div class="cw-fields"><div><label for="cwX">X (م)</label><input id="cwX" type="number" step="any"></div><div><label for="cwZ">Z (م)</label><input id="cwZ" type="number" step="any"></div></div><div class="cw-fields"><div><label for="cwW">العرض (م)</label><input id="cwW" type="number" step="any" min=".01"></div><div><label for="cwD">العمق (م)</label><input id="cwD" type="number" step="any" min=".01"></div></div><div class="cw-actions"><button id="cwSaveGeometry" type="submit" data-mutate>حفظ التعديل</button><button id="cwLock" type="button" data-mutate>قفل الفراغ</button></div></form><div id="cwSpaces" class="cw-space-list"></div></aside></div><div class="cw-results"><section class="cw-card"><h2>قياسات المخطط</h2><div class="cw-table-wrap"><table><tbody id="cwMetrics"></tbody></table></div></section><section class="cw-card"><h2>نتائج المراجعة</h2><div class="cw-table-wrap"><table><tbody id="cwChecks"></tbody></table></div><ul id="cwIssues"></ul><p class="cw-muted">تخص الفحوصات نطاقها المعلن. المتطلبات النصية غير المقاسة تحتاج مراجعة المختص.</p></section></div><section class="cw-card"><h2>تعديل بالمحادثة</h2><form id="cwChatForm"><label for="cwChat">ما الذي تريد تغييره؟</label><textarea id="cwChat" rows="3" maxlength="6000" placeholder="مثال: انقل منطقة التجهيز بجوار الشحن، مع الحفاظ على الأقفال الحالية."></textarea><p class="cw-muted">يولد طلب التعديل مقترحًا واحدًا بحد أقصى 3 استدعاءات. الأقفال محفوظة، وكل تعديل يصبح مسودة جديدة.</p><button id="cwChatSubmit" type="submit" data-mutate>إرسال التعديل وحفظ المقترح</button></form><details><summary>مصادر المتطلبات وتفاصيل المقارنة</summary><pre id="cwRequirementEvidence"></pre><pre id="cwDiff"></pre></details><h2>اعتماد النسخة</h2><p id="cwApprovalNote"></p><label class="cw-check"><input id="cwApproveConfirm" type="checkbox">راجعت هذه النسخة وأعتمدها تخطيطيًا فقط. هذا لا يُعد اعتمادًا إنشائيًا أو تصريحًا للتنفيذ.</label><button id="cwApprove" class="cw-primary" data-mutate disabled>اعتماد النسخة المختارة</button></section></div></section>
  <section data-step-panel="4" hidden class="cw-card"><h2>النسخة المعتمدة والتسليم</h2><p id="cwExportNote"></p><div class="cw-actions"><button id="cwShow3D" class="cw-primary" disabled>عرض النسخة المعتمدة في 3D</button><button data-format="gltf" disabled>تنزيل 3D</button><button data-format="svg" disabled>SVG</button><button data-format="dxf" disabled>DXF</button><button data-format="pdf" disabled>PDF</button><button data-format="ifc" disabled>IFC4</button><button data-format="review">ملف مراجعة</button></div><p class="cw-muted">DXF وSVG وPDF تعرض حدود الفراغات. IFC4 يصدر الفراغات. بيانات المصدر والنسخة وحدود التصدير مرفقة بكل ملف. قد يتوقف 3D إذا كانت أبعاد عناصره غير مكتملة.</p><div id="cwViewer" hidden aria-label="عارض النسخة المعتمدة"></div></section>
  <footer>ACS · المخطط ونسخه محفوظة في مشروعك. <a href="/privacy.html" target="_blank" rel="noopener">الخصوصية وحفظ البيانات</a></footer>`;
  root.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>step(Number(b.dataset.step))));
  const compareLabel=el('label','قارن مع نسخة محفوظة');compareLabel.htmlFor='cwCompareRevision';
  const compareSelect=el('select',null);compareSelect.id='cwCompareRevision';
  const compareControls=el('div',null,null,'cw-toolbar');compareControls.id='cwCompareControls';
  $('cwCompare').before(compareControls);compareControls.append(compareLabel,compareSelect,$('cwCompare'));
  compareSelect.addEventListener('change',syncApproval);
  const resumeReview=el('button','العودة إلى مراجعة النواقص');resumeReview.id='cwResumeReview';resumeReview.type='button';resumeReview.hidden=true;
  $('cwExportNote').after(resumeReview);
  resumeReview.addEventListener('click',()=>{step(3);$('cwIssues').closest('section').scrollIntoView({block:'start'});status('راجع الملاحظات التالية، ثم اكتب التعديل المطلوب في المحادثة.');});
  const comparison=el('section',null,null,'cw-card');comparison.id='cwComparison';comparison.hidden=true;
  comparison.innerHTML='<h2>مقارنة النسخ</h2><p id="cwComparisonNote"></p><div class="cw-table-wrap"><table><thead><tr><th>المقياس</th><th>النسخة المرجعية</th><th>النسخة المختارة</th><th>الفرق</th></tr></thead><tbody id="cwComparisonRows"></tbody></table></div>';
  $('cwChatForm').closest('section').before(comparison);
  root.querySelectorAll('[data-option]').forEach(b=>b.addEventListener('click',()=>run(()=>generation(b.dataset.option))));
  root.querySelectorAll('[data-format]').forEach(b=>b.addEventListener('click',()=>run(()=>exportFile(b.dataset.format))));
  $('cwShow3D').addEventListener('click',()=>run(()=>exportFile('gltf',true)));
  briefEditor=createBriefEditor(root,{storageKey:draftKey,onError:safeError});
  planUpload=createPlanUpload(root,{storageKey:()=> 'acs_plan_source:'+window.ACS_AUTH.storageScope(),onError:safeError});
  const sourceGenerate=el('button','قراءة المخطط وحفظ مسودة',null,'cw-primary');sourceGenerate.id='cwGenerateSource';sourceGenerate.type='button';sourceGenerate.dataset.mutate='';sourceGenerate.hidden=true;
  root.querySelector('[data-step-panel="2"] .cw-card').append(sourceGenerate);
  sourceGenerate.addEventListener('click',()=>run(()=>generation('A')));
  $('cwBriefForm').addEventListener('submit',e=>{e.preventDefault();try{briefProgram();const uploaded=!!planUpload.command().source_id;if(!$('cwConfirmed').checked)throw new Error('أكد المتطلبات قبل المتابعة.');root.querySelector('.cw-options').hidden=uploaded;sourceGenerate.hidden=!uploaded;sourceGenerate.textContent=$('cwSourceMode').value==='revise'?'اقتراح التعديل وحفظ مسودة':'قراءة المخطط وحفظ مسودة';status(uploaded?'ملفك محفوظ. ابدأ قراءة المخطط عندما تكون جاهزًا.':'اختر هدفًا للمخطط لبدء مقترح واحد. ستراجعه قبل الاعتماد.');step(2);}catch(err){safeError(err);}});
  $('cwReload').addEventListener('click',()=>run(async()=>{await refresh();status('تم فتح آخر نسخة محفوظة.');}));
  $('cwRecoverJob').addEventListener('click',()=>run(poll));
  $('cwDismissJob').addEventListener('click',()=>{stopProgress();pendingJob=null;clearTimeout(pollTimer);try{localStorage.removeItem(jobKey());}catch(e){}$('cwRecoverJob').hidden=true;$('cwDismissJob').hidden=true;setBusy(false);status('انتهت المتابعة. تحقق من آخر نسخة قبل بدء مقترح جديد.');});
  $('cwRevision').addEventListener('change',()=>run(()=>refresh($('cwRevision').value,true)));
  $('cwLevel').addEventListener('change',draw);
  $('cwType').addEventListener('change',projectCopy);
  $('cwApproveConfirm').addEventListener('change',syncApproval);
  $('cwApprove').addEventListener('click',()=>run(async()=>{const data=await api({action:'approve',expected_head:state.head,confirmed:true,acknowledge_concept_only:true},true);await renderState(data);step(4);status('حُفظ اعتماد النسخة. يمكنك الآن تحويلها أو تصديرها.');}));
  $('cwLock').addEventListener('click',()=>run(async()=>{const data=await api({action:'set_room_lock',expected_head:state.head,room_ref:[selected.source.template,selected.source.room_id],locked:$('cwLock').dataset.locked!=='true'},true);await renderState(data);status('حُفظ القفل في نسخة جديدة.');}));
  $('cwChatForm').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
    if(pendingJob)throw new Error('تابع المهمة الحالية أولًا.');
    if(!state?.head||state.revision_id!==state.head)throw new Error('اختر آخر نسخة قبل التعديل.');
    const text=$('cwChat').value.trim();if(!text)throw new Error('اكتب طلب التعديل.');
    const body={action:'chat_edit',job_id:crypto.randomUUID(),expected_head:state.head,notes:[{text}],confirmed:true,max_provider_calls:3};
    beginJob(body.job_id);
    $('cwRecoverJob').hidden=false;setBusy(true);status('جارٍ إرسال طلب التعديل…');
    try{await handleJob((await api(body)).job);}catch(err){progressPhase('UNKNOWN');status('لم يصل تأكيد طلب التعديل. تابع المهمة قبل إرسال طلب آخر. '+err.message,true);}
  });});
  $('cwSelection').addEventListener('submit',e=>{e.preventDefault();run(async()=>{const data=await api({action:'edit_geometry',expected_head:state.head,room_ref:[selected.source.template,selected.source.room_id],rect:['cwX','cwZ','cwW','cwD'].map(id=>Number($(id).value))});await renderState(data);status('حُفظ التعديل كنسخة جديدة.');});});
  $('cwRestore').addEventListener('click',()=>run(async()=>{await renderState(await api({action:'restore',expected_head:state.head,source_revision_id:state.revision_id,note:'استعادة نسخة محفوظة من واجهة المشروع'},true));status('تمت الاستعادة كمسودة جديدة؛ النسخ المعتمدة السابقة محفوظة.');}));
  $('cwCompare').addEventListener('click',()=>run(async()=>{const reference=$('cwCompareRevision').value;if(!reference||reference===state.revision_id)throw new Error('اختر نسخة مرجعية مختلفة للمقارنة.');const data=await api({action:'compare',reference_revision_id:reference,target_revision_id:state.revision_id},true);showComparison(data);status('المقارنة من النسختين المحفوظتين.');}));
  $('cwLogout').addEventListener('click',()=>{stopProgress();clearTimeout(pollTimer);if(viewerDispose)viewerDispose();$('acsLogout')?.click();});
  $('cwNewProject').addEventListener('click',()=>{$('cwNewProjectForm').hidden=false;$('cwProjectName').focus();});
  $('cwCancelProject').addEventListener('click',()=>{$('cwNewProjectForm').hidden=true;});
  $('cwProject').addEventListener('change',()=>{try{localStorage.setItem('acs_project_v1',JSON.stringify({id:$('cwProject').value}));}catch(e){}location.reload();});
  $('cwNewProjectForm').addEventListener('submit',e=>{e.preventDefault();run(async()=>{const s=await window.ACS_AUTH.freshSession();const data=await window.ACS_AUTH.acsFetchJSON('/v1/auth/projects',{action:'create',name:$('cwProjectName').value},s.access_token);localStorage.setItem('acs_project_v1',JSON.stringify(data.projects[0]));location.reload();});});
}
async function start(){
  if(!window.ACS?.projectId||!window.ACS?.authSession)return;
  mount();projectId=window.ACS.projectId;root.hidden=false;document.body.classList.add('acs-connected');
  status('جارٍ فتح مشروعك ونسخه المحفوظة…');
  try{const data=await api({action:'state'});await renderState(data);fillBrief(data);await projectList();status('مشروعك جاهز. كل تعديل محفوظ يظهر في قائمة النسخ.');}
  catch(e){safeError(e);fillBrief(null);}
  try{await planUpload.restore();}catch(e){safeError(e);}
  stopProgress();pendingJob=null;
  try{const saved=JSON.parse(localStorage.getItem(jobKey())||'null');if(typeof saved?.jobId==='string'&&saved.jobId)beginJob(saved.jobId,saved);}catch(e){}
  if(pendingJob){$('cwRecoverJob').hidden=false;setBusy(false);poll().catch(safeError);}
}
document.addEventListener('acs:authenticated',()=>{start().catch(e=>{if(root)safeError(e);});});
if(document.body.classList.contains('acs-entered'))start().catch(e=>{if(root)safeError(e);});
