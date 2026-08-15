/* ============================================================
   public/app/trust/core.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   المصدر المولِّد: hand-written · pure · no DOM · no IndexedDB
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
/* ===== ACS PRODUCTION TRUST CORE (hand-written · pure · no DOM · no IndexedDB) =====
   نواة نقيّة واحدة لأربع مسؤوليات إنتاجية: الحفظ المحلي (F-15)، إفصاح القدرات
   (F-16)، جدول حالات الخطأ الظاهر للمستخدم، وسلامة التزامن والنقر المزدوج.
   لا تلمس هذه الكتلة DOM ولا IndexedDB ولا الشبكة: كل ما فيها دوالّ نقيّة
   قابلة للاختبار في Node وحده. الطبقة التي تلمس المتصفّح تغلّفها وحدها.
   هذه كتلة مكتوبة يدوياً — لا يولّدها أي مولّد ولا تُقارَن بايتياً. */
function ACS_TRUST_CORE(){
'use strict';

/* ─────────────────────── 0 · أدوات نقيّة مشتركة ─────────────────────── */
function _canon(v){
  if(v===null||v===undefined) return 'n';
  const t=typeof v;
  if(t==='number') return isFinite(v)?('#'+String(v)):'n';
  if(t==='boolean') return v?'t':'f';
  if(t==='string') return 's'+v.length+':'+v;
  if(Array.isArray(v)) return '['+v.map(_canon).join(',')+']';
  if(t==='object'){
    const ks=Object.keys(v).filter(k=>v[k]!==undefined).sort();
    return '{'+ks.map(k=>k.length+':'+k+'='+_canon(v[k])).join(',')+'}';
  }
  return 'n';
}
/* بصمة 64-بت في مرورٍ واحد (مساران مستقلّان 32-بت). ليست تعمية، ولا تُقدَّم
   على أنّها كذلك: وظيفتها كشف الفساد والتلف، لا مقاومة خصم. */
function _hash64(s){
  const str=String(s);
  let h1=0x811c9dc5>>>0, h2=0x9e3779b9>>>0;
  for(let i=0;i<str.length;i++){
    const c=str.charCodeAt(i);
    h1=Math.imul(h1^(c&0xff),0x01000193)>>>0;
    h1=(h1^(h1>>>15))>>>0;
    h2=Math.imul(h2^(((c>>>8)&0xff)|((c&0xff)<<8)),0x85ebca6b)>>>0;
    h2=(h2^(h2>>>13))>>>0;
  }
  return ('00000000'+h1.toString(16)).slice(-8)
        +('00000000'+h2.toString(16)).slice(-8);
}
function _deepFreeze(o){
  if(o&&(typeof o==='object')&&!Object.isFrozen(o)){
    Object.freeze(o);
    Object.keys(o).forEach(k=>_deepFreeze(o[k]));
  }
  return o;
}
function _clone(o){ try{ return JSON.parse(JSON.stringify(o)); }catch(e){ return null; } }

/* ══════════════════════════════════════════════════════════════════════
   1 · F-15 — الحفظ المحلي الآمن ضدّ الفساد
   ══════════════════════════════════════════════════════════════════════ */
const P_CONTRACT   = 'acs-local-project/1';
const P_SCHEMA     = 3;      /* مخطّط السجلّ الحالي */
const P_MIN_SCHEMA = 2;      /* أقدم مخطّط نعرف كيف نرقّيه */
const P_KEEP       = 3;      /* عدد السجلّات المحفوظة قبل التقليم */

const P_CODES={
  OK:'OK',
  NOT_OBJECT:'RECORD_NOT_OBJECT',
  BAD_CONTRACT:'RECORD_BAD_CONTRACT',
  MISSING:'RECORD_MISSING_FIELD',
  PAYLOAD_NOT_JSON:'RECORD_PAYLOAD_NOT_JSON',
  TRUNCATED:'RECORD_TRUNCATED',
  HASH_MISMATCH:'RECORD_HASH_MISMATCH',
  SCHEMA_OLDER:'RECORD_SCHEMA_OLDER',
  SCHEMA_TOO_OLD:'RECORD_SCHEMA_TOO_OLD',
  SCHEMA_NEWER:'RECORD_SCHEMA_NEWER',
  NO_RECORDS:'NO_RECORDS',
  NONE_USABLE:'NO_USABLE_RECORD',
  NOT_SERIALISABLE:'PROJECT_NOT_SERIALISABLE'
};

/* عبارات ممنوعة منعاً باتّاً في أي نصّ يصف الحفظ المحلي: هذا ليس نسخاً
   احتياطياً سحابياً ولا يجوز أن يُفهَم كذلك ولو تلميحاً. */
const P_FORBIDDEN_CLAIMS=[
  'cloud','سحاب','السحابة','نسخة احتياطية سحابية','backed up to',
  'synced','مزامنة','on our servers','على خوادمنا','خادومنا','remote backup'
];
function assertNoCloudClaim(text){
  const t=String(text||'').toLowerCase();
  const hit=P_FORBIDDEN_CLAIMS.filter(w=>t.indexOf(String(w).toLowerCase())>=0);
  return {ok:hit.length===0, offending:hit};
}

const P_STATUS={
  IDLE:  {key:'IDLE',   tone:'neutral',
          ar:'لم يُحفَظ بعد على هذا الجهاز',
          en:'Not yet saved on this device'},
  SAVING:{key:'SAVING', tone:'busy',
          ar:'جارٍ الحفظ محلياً على هذا الجهاز…',
          en:'Saving locally on this device…'},
  SAVED: {key:'SAVED',  tone:'ok',
          ar:'محفوظ محلياً على هذا الجهاز',
          en:'saved locally on this device'},
  FAILED:{key:'FAILED', tone:'error',
          ar:'تعذّر الحفظ المحلي — نسختك الأخيرة السليمة ما زالت موجودة',
          en:'Local save failed — your last good copy is still intact'},
  RECOVERED:{key:'RECOVERED', tone:'ok',
          ar:'استُعيد آخر عمل محفوظ محلياً على هذا الجهاز',
          en:'Recovered the last work saved locally on this device'},
  QUOTA: {key:'QUOTA',  tone:'error',
          ar:'مساحة التخزين المحلية ممتلئة — لم يُكتب سجلّ جديد، والسجلّ السليم الأخير لم يُمَس',
          en:'Local storage is full — no new record was written and the last good record was not touched'}
};
function statusLabel(key){
  const s=P_STATUS[key]||P_STATUS.IDLE;
  return {key:s.key, tone:s.tone, ar:s.ar, en:s.en};
}

function encode(project, opts){
  const o=opts||{};
  let payload=null;
  try{ payload=JSON.stringify(project===undefined?null:project); }
  catch(e){ payload=null; }
  if(typeof payload!=='string')
    return {ok:false, code:P_CODES.NOT_SERIALISABLE, record:null};
  const model=(project&&typeof project==='object'&&project.model!==undefined)
    ? project.model : project;
  const now=(typeof o.now==='number'&&isFinite(o.now))?o.now:0;
  const ph=_hash64(payload);
  const rec={
    contract:P_CONTRACT,
    schema_version:(typeof o.schema_version==='number')?o.schema_version:P_SCHEMA,
    record_id:o.record_id||('rec_'+now+'_'+ph.slice(0,10)),
    project_id:String((project&&project.project_id)||o.project_id||'default'),
    revision_id:(project&&(project.current_revision||project.revision_id))
                ||o.revision_id||null,
    model_hash:_hash64(_canon(model)),
    saved_at_ms:now,
    origin:o.origin||'AUTOSAVE',
    payload_bytes:payload.length,
    payload_hash:ph,
    payload:payload
  };
  return {ok:true, code:P_CODES.OK, record:rec};
}

function validateRecord(rec){
  const out={valid:false, usable:false, code:'', reasons:[],
             schema_relation:'UNKNOWN', migrated:false,
             record_id:(rec&&rec.record_id)||null};
  if(!rec||typeof rec!=='object'||Array.isArray(rec)){
    out.code=P_CODES.NOT_OBJECT; out.reasons.push('record is not a plain object');
    return out; }
  if(rec.contract!==P_CONTRACT){
    out.code=P_CODES.BAD_CONTRACT;
    out.reasons.push('contract is '+JSON.stringify(rec.contract)
                     +', expected '+JSON.stringify(P_CONTRACT));
    return out; }
  const need=['schema_version','record_id','model_hash','saved_at_ms',
              'payload','payload_bytes','payload_hash'];
  const miss=need.filter(k=>rec[k]===undefined||rec[k]===null);
  if(miss.length){
    out.code=P_CODES.MISSING; out.reasons.push('missing field(s): '+miss.join(', '));
    return out; }
  const sv=rec.schema_version;
  if(typeof sv!=='number'||!isFinite(sv)){
    out.code=P_CODES.MISSING; out.reasons.push('schema_version is not a number');
    return out; }
  out.schema_relation = (sv===P_SCHEMA)?'CURRENT':(sv>P_SCHEMA?'NEWER':'OLDER');
  if(typeof rec.payload!=='string'){
    out.code=P_CODES.PAYLOAD_NOT_JSON; out.reasons.push('payload is not a string');
    return out; }
  if(typeof rec.payload_bytes!=='number'||rec.payload.length!==rec.payload_bytes){
    out.code=P_CODES.TRUNCATED;
    out.reasons.push('declared '+rec.payload_bytes+' characters, found '
                     +rec.payload.length);
    return out; }
  if(_hash64(rec.payload)!==rec.payload_hash){
    out.code=P_CODES.HASH_MISMATCH; out.reasons.push('payload hash does not match');
    return out; }
  let obj=null;
  try{ obj=JSON.parse(rec.payload); }
  catch(e){ out.code=P_CODES.PAYLOAD_NOT_JSON;
            out.reasons.push('payload is not valid JSON'); return out; }
  const model=(obj&&typeof obj==='object'&&obj.model!==undefined)?obj.model:obj;
  if(_hash64(_canon(model))!==rec.model_hash){
    out.code=P_CODES.HASH_MISMATCH; out.reasons.push('model hash does not match');
    return out; }
  /* البنية سليمة. يبقى سؤال المخطّط. */
  if(out.schema_relation==='NEWER'){
    out.valid=true; out.usable=false; out.code=P_CODES.SCHEMA_NEWER;
    out.reasons.push('written by a newer build (schema '+sv+' > '+P_SCHEMA
                     +') — preserved, never overwritten, never guessed at');
    return out; }
  if(out.schema_relation==='OLDER'){
    if(sv<P_MIN_SCHEMA){
      out.valid=true; out.usable=false; out.code=P_CODES.SCHEMA_TOO_OLD;
      out.reasons.push('schema '+sv+' is older than the oldest migratable '
                       +P_MIN_SCHEMA+' — preserved for manual export');
      return out; }
    out.valid=true; out.usable=true; out.migrated=true; out.code=P_CODES.SCHEMA_OLDER;
    out.reasons.push('schema '+sv+' will be migrated forward to '+P_SCHEMA);
    return out; }
  out.valid=true; out.usable=true; out.code=P_CODES.OK;
  return out;
}

function migrateProject(obj, fromSchema){
  const p=(obj&&typeof obj==='object'&&!Array.isArray(obj))?obj:{model:obj};
  p.schema_migrated_from=fromSchema;
  p.schema_version=P_SCHEMA;
  return p;
}

function decode(rec){
  const v=validateRecord(rec);
  const out={ok:false, code:v.code, project:null, migrated:false,
             schema_relation:v.schema_relation, reasons:v.reasons.slice(),
             record_id:v.record_id,
             revision_id:(rec&&rec.revision_id)||null,
             model_hash:(rec&&rec.model_hash)||null,
             saved_at_ms:(rec&&typeof rec.saved_at_ms==='number')?rec.saved_at_ms:null,
             preserve:(v.code===P_CODES.SCHEMA_NEWER
                       ||v.code===P_CODES.SCHEMA_TOO_OLD)};
  if(!v.usable) return out;
  let obj=null;
  try{ obj=JSON.parse(rec.payload); }
  catch(e){ out.code=P_CODES.PAYLOAD_NOT_JSON; return out; }
  if(v.migrated){ obj=migrateProject(obj, rec.schema_version); out.migrated=true; }
  out.ok=true; out.code=P_CODES.OK; out.project=obj;
  return out;
}

/* يختار السجلّ الذي يُستأنَف منه العمل بعد إعادة التحميل.
   قاعدتان لا تُكسران:
     · لا يُعاد سجلّ غير صالح أبداً — الفساد لا يُقدَّم على أنّه عمل المستخدم.
     · لا يُحجَر على شيء إن لم يبقَ سجلّ سليم واحد — لا نُتلف آخر ما بقي. */
function chooseRecovery(records){
  const out={chosen:null, chosen_id:null, code:P_CODES.NO_RECORDS,
             considered:0, accepted:[], rejected:[], preserve:[], quarantine:[],
             migrated:false, note:''};
  const list=Array.isArray(records)?records:[];
  out.considered=list.length;
  if(!list.length){ out.note='no local record exists yet'; return out; }
  list.forEach(r=>{
    const v=validateRecord(r);
    const id=(r&&r.record_id)||null;
    if(v.usable){
      out.accepted.push({record_id:id, code:v.code, migrated:v.migrated,
        saved_at_ms:(r&&typeof r.saved_at_ms==='number')?r.saved_at_ms:0,
        record:r});
    }else{
      out.rejected.push({record_id:id, code:v.code, reasons:v.reasons.slice()});
      if(v.code===P_CODES.SCHEMA_NEWER||v.code===P_CODES.SCHEMA_TOO_OLD)
        out.preserve.push(id);
      else out.quarantine.push(id);
    }
  });
  if(!out.accepted.length){
    out.code=P_CODES.NONE_USABLE;
    /* لا سجلّ سليم ⇒ لا نحجر على أي شيء ولا نحذف: ما بقي هو كلّ ما بقي. */
    out.quarantine=[];
    out.note='no usable record; every remaining record is preserved untouched '
            +'so it can still be exported by hand';
    return out; }
  out.accepted.sort((a,b)=>{
    if(b.saved_at_ms!==a.saved_at_ms) return b.saved_at_ms-a.saved_at_ms;
    return a.record_id<b.record_id?1:(a.record_id>b.record_id?-1:0); });
  const best=out.accepted[0];
  out.chosen=best.record; out.chosen_id=best.record_id;
  out.migrated=!!best.migrated;
  out.code=best.migrated?P_CODES.SCHEMA_OLDER:P_CODES.OK;
  return out;
}

function classifyStorageError(err){
  if(!err) return 'STORAGE_UNKNOWN';
  const n=String(err.name||''), m=String(err.message||''), c=err.code;
  if(n==='QuotaExceededError'||n==='NS_ERROR_DOM_QUOTA_REACHED'
     ||c===22||c===1014||/quota|exceeded the quota/i.test(m))
    return 'STORAGE_QUOTA';
  if(n==='InvalidStateError')  return 'STORAGE_UNAVAILABLE';
  if(n==='AbortError')         return 'STORAGE_ABORTED';
  if(n==='VersionError')       return 'STORAGE_VERSION';
  if(n==='SecurityError')      return 'STORAGE_BLOCKED';
  return 'STORAGE_UNKNOWN';
}

function _pState(s){
  const st=s||{};
  return {pointer:st.pointer||null,
          records:Array.isArray(st.records)?st.records.slice():[],
          last_good:st.last_good||null,
          last_error:st.last_error||null,
          last_saved_at_ms:(typeof st.last_saved_at_ms==='number')
                            ?st.last_saved_at_ms:null};
}
/* خطّة الكتابة المعاملاتية: اكتب سجلاً *جديداً*، تحقّق منه، ثمّ اقلب المؤشّر.
   لا يُكتب فوق النسخة السليمة الوحيدة أبداً؛ قلب المؤشّر هو آخر خطوة. */
function planWrite(state, project, opts){
  const s=_pState(state);
  const enc=encode(project, opts);
  if(!enc.ok) return {ok:false, code:enc.code, plan:null};
  const id=enc.record.record_id;
  const keep=[id].concat(s.records.filter(x=>x!==id)).slice(0,P_KEEP);
  if(s.pointer&&keep.indexOf(s.pointer)<0) keep.push(s.pointer);
  const prune=s.records.filter(x=>keep.indexOf(x)<0);
  return {ok:true, code:P_CODES.OK, plan:{
    new_record:enc.record,
    new_record_id:id,
    previous_pointer:s.pointer,
    steps:['PUT_NEW_RECORD','READ_BACK_AND_VALIDATE','FLIP_POINTER','PRUNE_OLD'],
    pointer_flip_is_last:true,
    overwrites_existing_record:false,
    keep:keep, prune:prune}};
}
function applyWriteResult(state, plan, result){
  const s=_pState(state);
  const r=result||{};
  if(!plan||!plan.new_record)
    return {ok:false, code:'NO_PLAN', status:'FAILED', state:s, pointer_moved:false,
            last_good_survived:true};
  if(r.ok===true){
    const id=plan.new_record_id;
    const records=[id].concat(s.records.filter(x=>x!==id&&plan.prune.indexOf(x)<0));
    return {ok:true, code:'SAVED', status:'SAVED', pointer_moved:true,
      last_good_survived:true,
      state:{pointer:id, records:records, last_good:id, last_error:null,
             last_saved_at_ms:plan.new_record.saved_at_ms}};
  }
  const cls=classifyStorageError(r.error);
  /* فشل الكتابة ⇒ المؤشّر لا يتحرّك، والسجلّ السليم السابق يبقى كما هو. */
  return {ok:false, code:cls,
    status:(cls==='STORAGE_QUOTA')?'QUOTA':'FAILED',
    pointer_moved:false, last_good_survived:true,
    state:{pointer:s.pointer, records:s.records.slice(), last_good:s.last_good,
           last_error:cls, last_saved_at_ms:s.last_saved_at_ms}};
}

/* نسخة احتياطية يُنزّلها المستخدم — ملفّ محلي، لا رفع ولا خادم. */
const B_CONTRACT='acs-project-backup/1';
function exportBackup(project, opts){
  const o=opts||{};
  const enc=encode(project,{now:o.now||0, origin:'MANUAL_EXPORT',
                            project_id:o.project_id});
  if(!enc.ok) return {ok:false, code:enc.code, file:null};
  const env={contract:B_CONTRACT, schema_version:P_SCHEMA,
             exported_at_ms:o.now||0,
             storage:'LOCAL_FILE_DOWNLOAD',
             storage_note_ar:'ملفّ يُنزَّل إلى جهازك — لا يُرفع إلى أي خادم.',
             storage_note_en:'A file downloaded to your device — nothing is uploaded.',
             record:enc.record};
  const text=JSON.stringify(env,null,1);
  return {ok:true, code:P_CODES.OK, envelope:env, file:{
    filename:'ACS-project-backup-'+(enc.record.model_hash.slice(0,8))+'.json',
    mime:'application/json;charset=utf-8', text:text, bytes:text.length}};
}
function restoreBackup(text){
  let env=null;
  try{ env=JSON.parse(String(text)); }
  catch(e){ return {ok:false, code:'BACKUP_NOT_JSON', project:null, reasons:
    ['the selected file is not valid JSON']}; }
  if(!env||typeof env!=='object'||env.contract!==B_CONTRACT)
    return {ok:false, code:'BACKUP_BAD_CONTRACT', project:null, reasons:
      ['the selected file is not an ACS project backup']};
  const d=decode(env.record);
  return {ok:d.ok, code:d.ok?P_CODES.OK:d.code, project:d.project,
          migrated:d.migrated, schema_relation:d.schema_relation,
          reasons:d.reasons.slice()};
}

const persistence={
  CONTRACT:P_CONTRACT, SCHEMA_VERSION:P_SCHEMA, MIN_SCHEMA_VERSION:P_MIN_SCHEMA,
  KEEP_RECORDS:P_KEEP, CODES:P_CODES, STATUS:P_STATUS,
  FORBIDDEN_CLOUD_CLAIMS:P_FORBIDDEN_CLAIMS,
  encode:encode, decode:decode, validateRecord:validateRecord,
  chooseRecovery:chooseRecovery, migrateProject:migrateProject,
  classifyStorageError:classifyStorageError,
  planWrite:planWrite, applyWriteResult:applyWriteResult,
  statusLabel:statusLabel, assertNoCloudClaim:assertNoCloudClaim,
  exportBackup:exportBackup, restoreBackup:restoreBackup,
  hash:_hash64, canonical:_canon
};

/* ══════════════════════════════════════════════════════════════════════
   2 · جدول حالات الخطأ الظاهرة للمستخدم (Task 3)
   لكلّ صنف: رمز، نصّ عربي وإنجليزي، قابلية الإعادة، أمان الإعادة، إجراء.
   لا أثر مكدّس، ولا رسالة خام من المتصفّح، ولا صنف بلا نصّ للمستخدم.
   ══════════════════════════════════════════════════════════════════════ */
const E=function(code,ar,en,retryable,retrySafe,action,extra){
  const o={code:code, ar:ar, en:en, retryable:!!retryable,
           retry_safe:!!retrySafe, action:action,
           request_id_required:true, shows_stack_trace:false};
  if(extra) Object.keys(extra).forEach(k=>{ o[k]=extra[k]; });
  return o; };

const errorStates={
  NETWORK_OFFLINE: E('NETWORK_OFFLINE',
    'لا يوجد اتصال بالإنترنت على هذا الجهاز. لم يُرسَل الطلب أصلاً.',
    'This device is offline. The request was never sent.',
    true, true, 'RETRY_WHEN_ONLINE'),
  NETWORK_DNS: E('NETWORK_DNS',
    'تعذّر الوصول إلى مضيف الخادم (تعذّر تحليل الاسم، أو رُفض الاتصال، أو منعته سياسة CORS). لم يصل الطلب إلى الخادم.',
    'The server host could not be reached (name resolution, refused connection, or CORS). The request did not reach the server.',
    true, true, 'RETRY'),
  TIMEOUT: E('TIMEOUT',
    'انتهت المهلة قبل ردّ الخادم. قد يكون الطلب قد نُفِّذ على الخادم رغم ذلك.',
    'The request timed out before the server answered. It may still have been processed.',
    true, false, 'RETRY_WITH_IDEMPOTENCY_KEY'),
  HTTP_429: E('HTTP_429',
    'تجاوزت حدّ الطلبات المسموح. رُفض الطلب قبل تنفيذ أي عمل.',
    'You exceeded the request limit. The request was refused before any work was done.',
    true, true, 'RETRY_AFTER_WAIT', {honours_retry_after:true}),
  HTTP_4XX_VALIDATION: E('HTTP_4XX_VALIDATION',
    'رفض الخادم محتوى الطلب. تكرار الطلب نفسه سيُرفض بالنتيجة نفسها — عدّل المُدخَل.',
    'The server rejected the request content. Repeating it unchanged will fail identically — change the input.',
    false, false, 'FIX_INPUT'),
  HTTP_5XX: E('HTTP_5XX',
    'عطل داخلي في الخادم. قد يكون الطلب قد نُفِّذ جزئياً.',
    'An internal server fault. The request may have been partially processed.',
    true, false, 'RETRY_WITH_IDEMPOTENCY_KEY'),
  INVALID_JSON: E('INVALID_JSON',
    'ردّ الخادم ليس JSON صالحاً. هذا عطل في الخادم لا في مُدخَلك، وقد يكون العمل قد نُفِّذ.',
    'The server reply was not valid JSON. That is a server fault, not an input fault, and the work may already have run.',
    true, false, 'RETRY_WITH_IDEMPOTENCY_KEY'),
  PROVIDER_UNAVAILABLE: E('PROVIDER_UNAVAILABLE',
    'مزوّد النموذج اللغوي غير متاح أو مُحمَّل حالياً. قد يكون النداء قد احتُسِب عليه.',
    'The language-model provider is unavailable or overloaded. The call may already have been counted.',
    true, false, 'RETRY_WITH_IDEMPOTENCY_KEY'),
  FILE_REJECTED: E('FILE_REJECTED',
    'رُفض الملفّ المرفوع (النوع أو الحجم أو المحتوى). اختر ملفاً آخر.',
    'The uploaded file was rejected (type, size or content). Choose a different file.',
    false, false, 'CHOOSE_ANOTHER_FILE'),
  WEBGL_UNSUPPORTED: E('WEBGL_UNSUPPORTED',
    'هذا المتصفّح أو الجهاز لا يدعم العرض ثلاثي الأبعاد. بيانات المشروع والبديل النصّي تبقى صالحة للاستعمال.',
    'This browser or device does not support 3D rendering. The project data and the text alternative remain usable.',
    false, false, 'USE_ACCESSIBLE_ALTERNATIVE'),
  WEBGL_CONTEXT_LOST: E('WEBGL_CONTEXT_LOST',
    'فقد المتصفّح سياق العرض ثلاثي الأبعاد. الاستعادة محلية بالكامل ولا تمسّ الخادم ولا مشروعك.',
    'The browser lost the 3D rendering context. Recovery is entirely local and touches neither the server nor your project.',
    true, true, 'RESTORE_CONTEXT'),
  BLACK_VIEWPORT: E('BLACK_VIEWPORT',
    'اكتُشِف مشهد أسود: النموذج مُحمَّل لكن لا شيء ظاهر. أُعيد ضبط الكاميرا محلياً — لا يُرسَل شيء.',
    'A black viewport was detected: the model is loaded but nothing is visible. The camera is reset locally — nothing is sent.',
    true, true, 'RESET_CAMERA'),
  STORAGE_QUOTA: E('STORAGE_QUOTA',
    'مساحة التخزين المحلية ممتلئة. لم يُكتب سجلّ جديد، ونسختك السليمة الأخيرة لم تُمَس. صدّر نسخة احتياطية ثمّ امسح البيانات المحلية.',
    'Local storage is full. No new record was written and your last good copy was not touched. Export a backup, then clear local data.',
    false, false, 'EXPORT_THEN_CLEAR_LOCAL_DATA'),
  STALE_REVISION: E('STALE_REVISION',
    'تغيّر المشروع منذ أن بدأت هذا التعديل. لم يُودَع شيء. راجِع المراجعة الأحدث ثمّ أعِد المحاولة على أساسها.',
    'The project changed after you started this edit. Nothing was committed. Review the newer revision and re-base your edit.',
    false, false, 'RELOAD_LATEST_REVISION', {http_status:409})
};

/* العمليات المعلنة: هل هي مُتماثلة (idempotent) وهل تحمل مفتاح تكرار؟ */
const operations={
  HEALTH:  {idempotent:true,  idempotency_key:false, billable:false},
  GENERATE:{idempotent:false, idempotency_key:true,  billable:true},
  EDIT:    {idempotent:false, idempotency_key:true,  billable:true},
  UNDERSTAND_IMAGE:{idempotent:false, idempotency_key:true, billable:true},
  UNDERSTAND_PDF:  {idempotent:false, idempotency_key:true, billable:true},
  COMMIT:  {idempotent:false, idempotency_key:true,  billable:false},
  EXPORT:  {idempotent:true,  idempotency_key:false, billable:false},
  LOCAL_SAVE:{idempotent:true, idempotency_key:false, billable:false}
};

/* خريطة رموز الخادم → أصناف العرض. يجب أن تكون *كلّية* على
   acs_api_errors.CODES: كلّ رمز يصل إلى حالة يراها المستخدم. */
const codeMap={
  ACS_BAD_REQUEST:'HTTP_4XX_VALIDATION',
  ACS_VALIDATION_FAILED:'HTTP_4XX_VALIDATION',
  ACS_PAYLOAD_TOO_LARGE:'FILE_REJECTED',
  ACS_UNPROCESSABLE:'HTTP_4XX_VALIDATION',
  ACS_NOT_FOUND:'HTTP_4XX_VALIDATION',
  ACS_METHOD_NOT_ALLOWED:'HTTP_4XX_VALIDATION',
  ACS_RATE_LIMITED:'HTTP_429',
  ACS_TIMEOUT:'TIMEOUT',
  ACS_NOT_CONFIGURED:'PROVIDER_UNAVAILABLE',
  ACS_INTERNAL:'HTTP_5XX',
  /* F-33: عطل تكامل محلّي — لا عند المزوّد ولا في طلب المستخدم. يُعرض حالةً
     من فئة 5xx لأن الإصلاح عند المشغّل، ولا يُعرض PROVIDER_UNAVAILABLE كي لا
     يُلقى اللوم على المزوّد كما كان يحدث قبل الإصلاح. */
  ACS_INTEGRATION_ERROR:'HTTP_5XX',
  ACS_UPSTREAM_NOT_CONFIGURED:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_AUTH:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_PERMISSION:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_MODEL_REJECTED:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_BAD_REQUEST:'HTTP_4XX_VALIDATION',
  ACS_UPSTREAM_RATE_LIMIT:'HTTP_429',
  ACS_UPSTREAM_OVERLOADED:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_UNAVAILABLE:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_TIMEOUT:'TIMEOUT',
  ACS_UPSTREAM_CONNECTION:'PROVIDER_UNAVAILABLE',
  ACS_UPSTREAM_EMPTY_RESPONSE:'INVALID_JSON',
  ACS_UPSTREAM_INVALID_JSON:'INVALID_JSON',
  ACS_UPSTREAM_TRAILING_JSON:'INVALID_JSON',
  ACS_UPSTREAM_TRUNCATED:'INVALID_JSON',
  /* F-50: سقف مخرجات أعلى ممّا يقبله النموذج. عطل ضبطٍ عند المشغّل لا
     خطأ من الزائر ولا عطل شبكة: يُعرَض كعطل خادم صريح، ولا يُقترَح على
     المستخدم أن يقصّر وصفه — تقصيره لن يغيّر سقفاً مضبوطاً في النشر. */
  ACS_UPSTREAM_MAX_TOKENS:'HTTP_5XX',
  ACS_UPSTREAM_REFUSED:'HTTP_4XX_VALIDATION',
  ACS_UPSTREAM_UNKNOWN:'HTTP_5XX'
};
/* أصناف طبقة النقل في acsFetchJSON → أصناف العرض نفسها */
const netMap={
  NETWORK_OFFLINE:'NETWORK_OFFLINE', NETWORK_DNS:'NETWORK_DNS',
  TIMEOUT:'TIMEOUT', HTTP_429:'HTTP_429', HTTP_4XX:'HTTP_4XX_VALIDATION',
  HTTP_5XX:'HTTP_5XX', INVALID_JSON:'INVALID_JSON',
  NOT_CONFIGURED:'PROVIDER_UNAVAILABLE', VALID_API_ERROR:'HTTP_5XX'
};

/* يحلّ نتيجة نداء واحدة إلى حالة مستخدم واحدة. لا يعيد null أبداً. */
function resolveErrorState(res){
  const r=res||{};
  let cls=null;
  if(r.class && errorStates[r.class]) cls=r.class;
  if(!cls && r.code && codeMap[r.code]) cls=codeMap[r.code];
  if(!cls && r.status && netMap[r.status]) cls=netMap[r.status];
  if(!cls && typeof r.http==='number' && r.http){
    cls = r.http===429?'HTTP_429' : (r.http>=500?'HTTP_5XX':'HTTP_4XX_VALIDATION'); }
  if(!cls) cls='HTTP_5XX';
  const base=errorStates[cls];
  const op=r.operation||'GENERATE';
  const opd=operations[op]||operations.GENERATE;
  const retry_safe_here = base.retry_safe && opd.idempotent===true;
  const key_makes_safe  = !!(opd.idempotency_key && r.idempotency_key);
  return {
    class:cls, code:base.code, ar:base.ar, en:base.en,
    retryable:base.retryable, retry_safe:base.retry_safe,
    action:base.action, operation:op,
    operation_idempotent:opd.idempotent===true,
    retry_safe_for_operation:retry_safe_here,
    /* الزرّ يظهر فقط حين تكون الإعادة آمنة فعلاً: إمّا العملية متماثلة،
       أو نُعيد إرسالها بمفتاح تكرار يمنع الازدواج على الخادم. */
    show_retry_button: base.retryable && (retry_safe_here||key_makes_safe),
    request_id: String(r.request_id||''),
    http: (typeof r.http==='number')?r.http:0,
    retry_after: (typeof r.retry_after==='number')?r.retry_after:0,
    /* لا أثر مكدّس ولا رسالة خام: النصّ المعروض هو النصّ المعلن وحده. */
    shows_stack_trace:false
  };
}
function errorStateCoverage(codes){
  const list=Array.isArray(codes)?codes:Object.keys(codeMap);
  const missing=list.filter(c=>!codeMap[c]||!errorStates[codeMap[c]]);
  return {total:list.length, missing:missing, complete:missing.length===0};
}
/* علامات أثر المكدّس التي لا يجوز أن تظهر لمستخدم */
const STACK_MARKERS=['\n    at ','Traceback (most recent call last)',
  '.js:','@http','ReferenceError','TypeError:','stack trace',
  'File "','Uncaught '];
function containsStackTrace(text){
  const t=String(text||'');
  return STACK_MARKERS.some(m=>t.indexOf(m)>=0);
}

/* ══════════════════════════════════════════════════════════════════════
   3 · التزامن وسلامة النقر المزدوج (Task 4)
   ══════════════════════════════════════════════════════════════════════ */
/* مفتاح التكرار يُشتقّ من *نيّة المستخدم* لا من محاولة الإرسال: نفس النيّة
   عبر كل إعادات المحاولة ⇒ نفس المفتاح ⇒ لا ازدواج في الفوترة ولا في الإيداع. */
function intentKey(intent){
  const i=intent||{};
  const material={op:String(i.op||''), project_id:String(i.project_id||'default'),
    base_revision:(i.base_revision===undefined||i.base_revision===null)
      ?null:String(i.base_revision),
    payload_hash:String(i.payload_hash||''),
    intent_seq:(typeof i.intent_seq==='number')?i.intent_seq:0};
  return 'acs-'+String(material.op||'OP').toLowerCase()+'-'+_hash64(_canon(material));
}
function payloadHash(payload){
  if(typeof payload==='string') return _hash64(payload);
  return _hash64(_canon(payload));
}
function _cState(s){
  const st=s||{};
  return {inflight:Object.assign({}, st.inflight||{}),
          intent_seq:Object.assign({}, st.intent_seq||{}),
          keys:Object.assign({}, st.keys||{}),
          completed:Object.assign({}, st.completed||{})};
}
/* نيّة جديدة: تُزاد فقط حين تتغيّر الحمولة أو حين اكتملت نيّة سابقة.
   نقرتان متتاليتان بلا تغيير ⇒ نفس المفتاح ⇒ لا طلب ثانٍ يُفوتَر. */
function beginIntent(state, req){
  const s=_cState(state);
  const r=req||{};
  const op=String(r.op||'GENERATE');
  const ph=String(r.payload_hash||'');
  const slot=op+'|'+String(r.project_id||'default');
  const prev=s.keys[slot]||null;
  let seq=(typeof s.intent_seq[slot]==='number')?s.intent_seq[slot]:0;
  const changed = !prev || prev.payload_hash!==ph
    || String(prev.base_revision)!==String(r.base_revision===undefined?null:r.base_revision)
    || prev.completed===true;
  if(changed) seq=seq+1;
  const key=intentKey({op:op, project_id:r.project_id, base_revision:r.base_revision,
                       payload_hash:ph, intent_seq:seq});
  if(s.inflight[slot]){
    return {allowed:false, code:'REQUEST_ALREADY_IN_FLIGHT', reused_key:true,
      idempotency_key:s.inflight[slot].idempotency_key, state:s,
      ar:'الطلب قيد التنفيذ بالفعل — لن يُرسَل طلب ثانٍ ولن تُحتسب عملية ثانية.',
      en:'A request is already in flight — no second request is sent and no second operation is billed.'};
  }
  s.intent_seq[slot]=seq;
  s.keys[slot]={payload_hash:ph,
    base_revision:(r.base_revision===undefined?null:r.base_revision),
    idempotency_key:key, intent_seq:seq, completed:false};
  s.inflight[slot]={idempotency_key:key, started_at_ms:r.now||0};
  return {allowed:true, code:'STARTED', reused_key:!changed,
    idempotency_key:key, intent_seq:seq, slot:slot, state:s,
    headers:{'Idempotency-Key':key},
    ar:'جارٍ التنفيذ…', en:'Working…'};
}
function endIntent(state, req, outcome){
  const s=_cState(state);
  const r=req||{};
  const slot=String(r.op||'GENERATE')+'|'+String(r.project_id||'default');
  delete s.inflight[slot];
  if(s.keys[slot] && outcome && outcome.ok===true){
    s.keys[slot].completed=true;
    s.completed[s.keys[slot].idempotency_key]=true;
  }
  return {state:s, code:(outcome&&outcome.ok)?'COMPLETED':'ENDED', slot:slot};
}
function isInFlight(state, op, projectId){
  const s=_cState(state);
  return !!s.inflight[String(op)+'|'+String(projectId||'default')];
}
/* حارس المراجعة القاعدية: الإيداع على أساس قديم يُرفض برمز واحد ثابت. */
function checkBaseRevision(currentRevision, baseRevision){
  const cur=(currentRevision===undefined||currentRevision===null)
    ?null:String(currentRevision);
  const base=(baseRevision===undefined||baseRevision===null)
    ?null:String(baseRevision);
  if(base===null)
    return {ok:false, code:'MISSING_BASE_REVISION', http_status:400,
      ar:'لم تُذكر المراجعة التي بُني عليها هذا التعديل.',
      en:'The revision this edit was based on was not stated.'};
  if(cur!==null && cur!==base)
    return {ok:false, code:'STALE_BASE_REVISION', http_status:409,
      current_revision:cur, base_revision:base,
      ar:errorStates.STALE_REVISION.ar, en:errorStates.STALE_REVISION.en};
  return {ok:true, code:'BASE_REVISION_CURRENT', http_status:200,
    current_revision:cur, base_revision:base};
}

/* تعدّد الألسنة: مُخفِّض نقيّ. المالك محدَّد حتمياً وليس سباقاً. */
const TAB_TTL_MS=15000;
function _tState(s){
  const st=s||{};
  return {self_id:st.self_id||null,
          tabs:JSON.parse(JSON.stringify(st.tabs||{}))};
}
function tabsReduce(state, msg, nowMs){
  const s=_tState(state);
  const now=(typeof nowMs==='number')?nowMs:0;
  const m=msg||{};
  if(m.type==='SELF'){ s.self_id=String(m.tab_id); }
  if(m.type==='HELLO'||m.type==='HEARTBEAT'||m.type==='CLAIM'){
    const id=String(m.tab_id||'');
    if(id){
      const prev=s.tabs[id]||{};
      s.tabs[id]={tab_id:id, project_id:String(m.project_id||'default'),
        claimed_at_ms:(typeof prev.claimed_at_ms==='number')
          ?prev.claimed_at_ms
          :((typeof m.claimed_at_ms==='number')?m.claimed_at_ms:now),
        seen_at_ms:now};
    }
  }
  if(m.type==='BYE'){ delete s.tabs[String(m.tab_id||'')]; }
  Object.keys(s.tabs).forEach(id=>{
    if(now - (s.tabs[id].seen_at_ms||0) > TAB_TTL_MS) delete s.tabs[id]; });
  return s;
}
function tabOwner(state, projectId, nowMs){
  const s=_tState(state);
  const now=(typeof nowMs==='number')?nowMs:0;
  const pid=String(projectId||'default');
  const live=Object.keys(s.tabs).map(k=>s.tabs[k])
    .filter(t=>t.project_id===pid && (now-(t.seen_at_ms||0))<=TAB_TTL_MS)
    .sort((a,b)=>{
      if(a.claimed_at_ms!==b.claimed_at_ms) return a.claimed_at_ms-b.claimed_at_ms;
      return a.tab_id<b.tab_id?-1:(a.tab_id>b.tab_id?1:0); });
  if(!live.length)
    return {owner_id:null, is_self:false, tabs:0, code:'NO_TAB',
      ar:'لا لسان مسجَّل لهذا المشروع.', en:'No tab is registered for this project.'};
  const owner=live[0];
  const isSelf=(s.self_id!==null && owner.tab_id===String(s.self_id));
  return {owner_id:owner.tab_id, is_self:isSelf, tabs:live.length,
    code:isSelf?'THIS_TAB_OWNS':'ANOTHER_TAB_OWNS',
    ar:isSelf
      ? ('هذا اللسان هو صاحب المشروع'
         +(live.length>1?(' — و'+(live.length-1)+' لسان آخر مفتوح للقراءة فقط.'):'.'))
      : ('لسان آخر ('+owner.tab_id+') يملك هذا المشروع الآن — التحرير هنا معطّل '
         +'حتى تُغلقه أو تستلم الملكية صراحةً.'),
    en:isSelf
      ? ('This tab owns the project'
         +(live.length>1?(' — '+(live.length-1)+' other tab(s) are read-only.'):'.'))
      : ('Another tab ('+owner.tab_id+') currently owns this project — editing here '
         +'is disabled until you close it or explicitly take over.')};
}

const concurrency={
  intentKey:intentKey, payloadHash:payloadHash,
  beginIntent:beginIntent, endIntent:endIntent, isInFlight:isInFlight,
  checkBaseRevision:checkBaseRevision,
  tabsReduce:tabsReduce, tabOwner:tabOwner, TAB_TTL_MS:TAB_TTL_MS,
  operations:operations
};

/* ══════════════════════════════════════════════════════════════════════
   4 · F-16 — إفصاح القدرات: المعلَن مقابل المنفَّذ
   ══════════════════════════════════════════════════════════════════════ */
const NOT_SUPPORTED_LABEL={
  ar:'غير مدعوم بعد', en:'Not yet supported',
  both:'غير مدعوم بعد / Not yet supported'};

function capabilityGap(declared, implemented){
  const d=Array.isArray(declared)?declared:[];
  const i=Array.isArray(implemented)?implemented:[];
  return d.filter(x=>i.indexOf(x)<0);
}
/* يبني جدول الإفصاح من مواصفة التأليف نفسها — لا قوائم مكرّرة يدوياً. */
function capabilityDisclosure(spec){
  const s=spec||{};
  const cmdGap=capabilityGap(s.command_types, s.implemented_command_types);
  const snapGap=capabilityGap(s.snap_types, s.implemented_snap_types);
  const gizGap=capabilityGap(s.gizmo_operations, s.implemented_gizmo_operations);
  const why={
    COMMAND:{code:'COMMAND_NOT_IMPLEMENTED',
      ar:'أُعلِن هذا الأمر في مفردات المحرّك ليُذكر مالكه الهندسي صراحةً، ولم يُنفَّذ في هذه المرحلة. إرساله يُرفَض برمز COMMAND_NOT_IMPLEMENTED ولا يُنفَّذ صامتاً ولا يُحوَّل إلى تعديل معماري آخر.',
      en:'This command is declared in the engine vocabulary so its engineering ownership is stated, but it is not implemented in this phase. Submitting it is refused with COMMAND_NOT_IMPLEMENTED; it is never silently ignored and never rewritten into a different edit.'},
    SNAP:{code:'SNAP_TYPE_NOT_IMPLEMENTED',
      ar:'نوع الالتقاط هذا معلَن في المواصفة ولم يُنفَّذ بعد. المنفَّذ هو NONE وGRID فقط.',
      en:'This snap type is declared in the specification and is not implemented yet. Only NONE and GRID are implemented.'},
    GIZMO:{code:'GIZMO_OPERATION_NOT_IMPLEMENTED',
      ar:'عملية المقبض هذه معلَنة ولم تُنفَّذ بعد؛ المنفَّذ هو TRANSLATE وحده لأنّ التدوير والتحجيم لا يحملان معنى هندسياً لكل عنصر في هذه المرحلة.',
      en:'This gizmo operation is declared and not implemented yet; only TRANSLATE is implemented, because rotate and scale do not carry a domain meaning for every element in this phase.'}
  };
  const entry=(kind,value)=>({
    kind:kind, value:value, implemented:false,
    label_ar:NOT_SUPPORTED_LABEL.ar, label_en:NOT_SUPPORTED_LABEL.en,
    label:NOT_SUPPORTED_LABEL.both,
    refusal_code:why[kind].code, why_ar:why[kind].ar, why_en:why[kind].en,
    ui_requirement:{must_be_absent_or_disabled:true, disabled:true,
      aria_disabled:'true', requires_title:true, requires_aria_description:true}});
  return {
    contract:'acs-capability-disclosure/1.0.0',
    label:NOT_SUPPORTED_LABEL,
    commands:{declared:(s.command_types||[]).slice(),
              implemented:(s.implemented_command_types||[]).slice(),
              not_implemented:cmdGap, entries:cmdGap.map(v=>entry('COMMAND',v))},
    snap_types:{declared:(s.snap_types||[]).slice(),
              implemented:(s.implemented_snap_types||[]).slice(),
              not_implemented:snapGap, entries:snapGap.map(v=>entry('SNAP',v))},
    gizmo_operations:{declared:(s.gizmo_operations||[]).slice(),
              implemented:(s.implemented_gizmo_operations||[]).slice(),
              not_implemented:gizGap, entries:gizGap.map(v=>entry('GIZMO',v))},
    all_entries:[].concat(cmdGap.map(v=>entry('COMMAND',v)),
                          snapGap.map(v=>entry('SNAP',v)),
                          gizGap.map(v=>entry('GIZMO',v)))
  };
}
/* يفحص وصفاً مجرَّداً لعنصر واجهة: هل يعرض قدرة غير منفَّذة بلا إفصاح؟
   مجرّد عن DOM عمداً حتى يُختبَر في Node، وتغلّفه طبقة DOM. */
function auditAffordance(af, disclosure){
  const a=af||{};
  const value=String(a.value||'');
  const kind=String(a.kind||'COMMAND');
  const bucket=(kind==='SNAP')?disclosure.snap_types
              :(kind==='GIZMO')?disclosure.gizmo_operations
              :disclosure.commands;
  const unimplemented=bucket.not_implemented.indexOf(value)>=0;
  if(!unimplemented) return {ok:true, code:'IMPLEMENTED', value:value, kind:kind,
    violations:[]};
  const v=[];
  if(a.disabled!==true) v.push('NOT_DISABLED');
  if(String(a.aria_disabled)!=='true') v.push('MISSING_ARIA_DISABLED');
  const text=String(a.text||'')+' '+String(a.aria_label||'');
  if(text.indexOf(NOT_SUPPORTED_LABEL.ar)<0
     ||text.toLowerCase().indexOf(NOT_SUPPORTED_LABEL.en.toLowerCase())<0)
    v.push('MISSING_NOT_SUPPORTED_LABEL');
  if(!String(a.title||'').trim()) v.push('MISSING_TITLE');
  if(!String(a.aria_description||'').trim()) v.push('MISSING_ARIA_DESCRIPTION');
  if(a.has_handler===true&&a.disabled!==true) v.push('DEAD_BUTTON_WITH_HANDLER');
  return {ok:v.length===0, code:v.length?'UNDISCLOSED_UNIMPLEMENTED':'DISCLOSED',
          value:value, kind:kind, violations:v};
}
const capability={
  NOT_SUPPORTED_LABEL:NOT_SUPPORTED_LABEL,
  capabilityGap:capabilityGap, capabilityDisclosure:capabilityDisclosure,
  auditAffordance:auditAffordance
};


/* ══════════════════════════════════════════════════════════════════════
   5 · البديل النصّي للعرض ثلاثي الأبعاد — اشتقاق نقيّ من هندسة النموذج
   قارئ الشاشة لا يقرأ بكسلات WebGL. لذلك يُشتَقّ هنا ما يمكن قراءته فعلاً:
   شجرة، عناصر وخصائص، ملاحظات، مسقط متجهي، وجداول. نقيّ عمداً ليُختبَر.
   ══════════════════════════════════════════════════════════════════════ */
function _a11yEsc(x){ return String(x==null?'':x).replace(/[&<>"]/g,
  c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function a11yBuild(b){
  const model=b||null;
  if(!model||typeof model!=='object') return {tree:[], elements:[], schedules:[], issues:[], plan:null,
                     site:null, empty:true};
  const site=model.site||{w:null,d:null};
  const levels=(model.levels||[]).map(l=>({index:l.index, name:l.name||('#'+l.index),
    template:l.template||''}));
  const floors=model.floors||{};
  const tree=[], elements=[], schedules=[];
  const rows=[];
  levels.forEach(l=>{
    const f=floors[l.template]||{};
    const rooms=(f.rooms||[]);
    tree.push({kind:'LEVEL', id:'level_'+l.index, name:l.name,
      children:rooms.map(r=>({kind:'SPACE', id:r.id,
        name:r.id, rect:r.rect||null}))});
    rooms.forEach(r=>{
      const rc=r.rect||[null,null,null,null];
      const area=(rc[2]!=null&&rc[3]!=null)?(rc[2]*rc[3]):null;
      elements.push({level:l.name, id:r.id, kind:'SPACE',
        x:rc[0], z:rc[1], w:rc[2], d:rc[3], area:area,
        doors:(r.doors||[]).length, windows:(r.windows||[]).length,
        points:(r.points||[]).length, furniture:(r.furniture||[]).length});
      rows.push({level:l.name, id:r.id, w:rc[2], d:rc[3], area:area,
        doors:(r.doors||[]).length, windows:(r.windows||[]).length});
    });
  });
  schedules.push({name:'جدول الفراغات / Space schedule', rows:rows});
  const ground=levels.length?(floors[levels[0].template]||{}):{};
  return {empty:false, site:site, levels:levels, tree:tree, elements:elements,
          schedules:schedules,
          plan:{w:site.w||30, d:site.d||25, rooms:(ground.rooms||[]).map(r=>({
            id:r.id, rect:r.rect||[0,0,0,0]}))},
          issues:a11yIssues(model, elements)};
}
function a11yIssues(model, elements){
  const out=[];
  if(!(model.levels||[]).length)
    out.push({severity:'ERROR', ar:'لا توجد مستويات في النموذج.',
              en:'The model declares no levels.'});
  elements.filter(e=>e.w==null||e.d==null).forEach(e=>
    out.push({severity:'WARNING',
      ar:'الفراغ '+e.id+' بلا أبعاد معلنة — تُعرض «غير محدد» ولا تُخمَّن.',
      en:'Space '+e.id+' has no declared dimensions — shown as Not specified, never guessed.'}));
  if(!elements.length)
    out.push({severity:'INFO', ar:'لا فراغات في النموذج الحالي.',
              en:'The current model contains no spaces.'});
  return out;
}
function a11yPlanSvg(plan, escFn){
  if(!plan) return '';
  const W=plan.w||30, D=plan.d||25, S=16, pad=10;
  const w=Math.round(W*S)+pad*2, h=Math.round(D*S)+pad*2;
  let s='<svg role="img" viewBox="0 0 '+w+' '+h+'" width="100%" '
    +'aria-labelledby="acsPlanTitle acsPlanDesc">'
    +'<title id="acsPlanTitle">مسقط أفقي للدور الأرضي / Ground floor plan</title>'
    +'<desc id="acsPlanDesc">رسم متجهي مولَّد من هندسة النموذج نفسها، لا من بكسلات '
    +'العرض ثلاثي الأبعاد. أرض '+W+'×'+D+' متر و'+plan.rooms.length+' فراغاً. '
    +'A vector drawing derived from the model geometry itself, not from 3D pixels. '
    +'Site '+W+' by '+D+' metres with '+plan.rooms.length+' spaces.</desc>'
    +'<rect x="'+pad+'" y="'+pad+'" width="'+Math.round(W*S)+'" height="'
    +Math.round(D*S)+'" fill="#ffffff" stroke="#1f2937" stroke-width="2"/>';
  plan.rooms.forEach(r=>{
    const rc=r.rect||[0,0,0,0];
    s+='<g><rect x="'+(pad+rc[0]*S)+'" y="'+(pad+rc[1]*S)+'" width="'+(rc[2]*S)
      +'" height="'+(rc[3]*S)+'" fill="#e5edff" stroke="#1d4ed8" stroke-width="1.5"/>'
      +'<text x="'+(pad+rc[0]*S+4)+'" y="'+(pad+rc[1]*S+14)
      +'" font-size="11" fill="#111827">'+(escFn||_a11yEsc)(r.id)+'</text></g>';
  });
  return s+'</svg>';
}

const accessibility={
  buildModel:a11yBuild, issues:a11yIssues, planSvg:a11yPlanSvg, escape:_a11yEsc,
  canvas_limitation:{
    ar:'لوحة العرض ثلاثي الأبعاد مبنيّة على WebGL ولا يستطيع قارئ الشاشة تفسير بكسلاتها.',
    en:'The 3D viewport is WebGL and a screen reader cannot interpret its pixels.'}
};

return _deepFreeze({
  contract:'acs-production-trust/1.0.0',
  persistence:persistence,
  errorStates:errorStates,
  errorCodeMap:codeMap,
  errorNetMap:netMap,
  operations:operations,
  resolveErrorState:resolveErrorState,
  errorStateCoverage:errorStateCoverage,
  containsStackTrace:containsStackTrace,
  STACK_MARKERS:STACK_MARKERS,
  concurrency:concurrency,
  capability:capability,
  accessibility:accessibility,
  hash:_hash64, canonical:_canon, clone:_clone
});
}
const ACS_TRUST=ACS_TRUST_CORE();
/* ===== END ACS PRODUCTION TRUST CORE ===== */

export { ACS_TRUST, ACS_TRUST_CORE };
