/* ============================================================
   public/app/trust/wiring.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   المصدر المولِّد: hand-written · DOM · IndexedDB · network
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { __ACS_SHARED } from '../shared-state.js';
import { ACS_AUTHORING_SPEC } from '../generated/authoring.js';
import { statusEl } from '../render/scene.js';
import { ACS_TRUST } from './core.js';
import { acsGenerateFromServer, lastBuilding, notes, setModel } from '../ui/workspace-ui-wiring.js';

/* ===== ACS PRODUCTION TRUST WIRING (hand-written · DOM · IndexedDB · network) =====
   الطبقة الوحيدة التي تلمس المتصفّح. كل منطقٍ قابلٍ للاختبار يعيش في النواة
   النقيّة أعلاه؛ ما هنا هو التوصيل وحده: IndexedDB، DOM، BroadcastChannel،
   واعتراض مسارات الشبكة القائمة. لا نظام إشعارات ثانٍ: نُعيد استعمال
   #status و#reportBox و#engineWarn وشريط رسائل مساحة العمل كما هي.
   كتلة مكتوبة يدوياً — لا يولّدها مولّد ولا تُقارَن بايتياً. */
(function ACS_TRUST_WIRING(){
'use strict';
const T=ACS_TRUST;
window.ACS=window.ACS||{};
const $=id=>document.getElementById(id);
const escT=s=>String(s==null?'':s).replace(/[&<>"]/g,
  c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ═══════════ 0 · إعلان النواة على window (قابل للفحص من الاختبارات) ═══════════ */
window.ACS.trust        = T;
window.ACS.errorStates  = T.errorStates;
window.ACS.errorCodeMap = T.errorCodeMap;
window.ACS.resolveErrorState = r=>T.resolveErrorState(r);
window.ACS.errorStateCoverage = c=>T.errorStateCoverage(c);
window.ACS.concurrency  = T.concurrency;

/* ═══════════ 1 · F-15 · الحفظ المحلي على IndexedDB ═══════════ */
const P=T.persistence;
const DB_NAME='acs_local_project', DB_VER=1;
const ST_REC='records', ST_META='meta';
const PTR_KEY='pointer';
let pState={pointer:null, records:[], last_good:null, last_error:null,
            last_saved_at_ms:null};
let pStatusKey='IDLE', pLastCode='', pDbError=null, pRecovered=null;

function idbOpen(){
  return new Promise((res,rej)=>{
    let rq;
    try{ rq=indexedDB.open(DB_NAME,DB_VER); }
    catch(e){ rej(e); return; }
    rq.onupgradeneeded=()=>{ const db=rq.result;
      if(!db.objectStoreNames.contains(ST_REC))
        db.createObjectStore(ST_REC,{keyPath:'record_id'});
      if(!db.objectStoreNames.contains(ST_META))
        db.createObjectStore(ST_META); };
    rq.onsuccess=()=>res(rq.result);
    rq.onerror=()=>rej(rq.error||new Error('indexedDB open failed'));
    rq.onblocked=()=>rej(Object.assign(new Error('indexedDB blocked'),
                                       {name:'InvalidStateError'}));
  });
}
function idbTx(db, stores, mode, work){
  return new Promise((res,rej)=>{
    let tx;
    try{ tx=db.transaction(stores,mode); }catch(e){ rej(e); return; }
    let out=null;
    tx.oncomplete=()=>res(out);
    tx.onerror=()=>rej(tx.error||new Error('transaction failed'));
    tx.onabort=()=>rej(tx.error||Object.assign(new Error('transaction aborted'),
                                               {name:'AbortError'}));
    try{ out=work(tx); }catch(e){ try{tx.abort();}catch(_e){} rej(e); }
  });
}
function req(r){ return new Promise((res,rej)=>{
  r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); }); }

async function pReadAll(){
  const db=await idbOpen();
  let recs=[], ptr=null;
  await idbTx(db,[ST_REC,ST_META],'readonly',tx=>{
    tx.objectStore(ST_REC).getAll().onsuccess=e=>{ recs=e.target.result||[]; };
    tx.objectStore(ST_META).get(PTR_KEY).onsuccess=e=>{ ptr=e.target.result||null; };
  });
  db.close();
  return {records:recs, pointer:ptr};
}

/* الكتابة المعاملاتية: سجلّ جديد ⇒ قراءة تحقّق ⇒ قلب المؤشّر ⇒ تقليم.
   لا نكتب فوق السجلّ السليم الوحيد أبداً، ولا يتحرّك المؤشّر قبل التحقّق. */
async function pSave(project, origin){
  const plan=P.planWrite(pState, project, {now:Date.now(), origin:origin||'AUTOSAVE',
    project_id:(project&&project.project_id)||'default'});
  if(!plan.ok){ pApply(P.applyWriteResult(pState,null,{ok:false})); return plan; }
  pSetStatus('SAVING');
  let db=null;
  try{
    db=await idbOpen();
    /* 1) اكتب سجلاً جديداً بمعرّف جديد */
    await idbTx(db,[ST_REC],'readwrite',tx=>{
      tx.objectStore(ST_REC).put(plan.plan.new_record); });
    /* 2) اقرأه وتحقّق منه فعلاً قبل أن تثق به */
    let back=null;
    await idbTx(db,[ST_REC],'readonly',tx=>{
      tx.objectStore(ST_REC).get(plan.plan.new_record_id).onsuccess
        =e=>{ back=e.target.result||null; }; });
    const v=P.validateRecord(back);
    if(!v.usable) throw Object.assign(new Error('read-back validation failed: '+v.code),
                                      {name:'DataError'});
    /* 3) الآن فقط اقلب المؤشّر */
    await idbTx(db,[ST_META],'readwrite',tx=>{
      tx.objectStore(ST_META).put(plan.plan.new_record_id, PTR_KEY); });
    /* 4) قلّم القديم — بعد أن صار للمؤشّر هدف سليم */
    if(plan.plan.prune.length)
      await idbTx(db,[ST_REC],'readwrite',tx=>{
        const s=tx.objectStore(ST_REC);
        plan.plan.prune.forEach(id=>s.delete(id)); });
    db.close();
    pApply(P.applyWriteResult(pState, plan.plan, {ok:true}));
    return {ok:true, code:'SAVED', record_id:plan.plan.new_record_id};
  }catch(e){
    if(db) try{ db.close(); }catch(_e){}
    const r=P.applyWriteResult(pState, plan.plan, {ok:false, error:e});
    pApply(r);
    return {ok:false, code:r.code, error_name:String(e&&e.name||'')};
  }
}
function pApply(r){
  pState=r.state; pLastCode=r.code;
  pSetStatus(r.status==='SAVED'?'SAVED':(r.code==='STORAGE_QUOTA'?'QUOTA':'FAILED'));
  if(r.code==='STORAGE_QUOTA') showErrorState({class:'STORAGE_QUOTA',
    operation:'LOCAL_SAVE', request_id:''});
}
function pSetStatus(key){
  pStatusKey=key;
  const el=$('acsSaveState'); if(!el) return;
  const L=P.statusLabel(key);
  el.setAttribute('data-acs-save', L.key);
  el.setAttribute('data-tone', L.tone);
  el.innerHTML='<span class="ar" lang="ar">'+escT(L.ar)+'</span>'
    +'<span class="en" lang="en" dir="ltr">'+escT(L.en)+'</span>'
    +(pState.last_saved_at_ms
      ?('<span class="ts" lang="ar"> · '
        +escT(new Date(pState.last_saved_at_ms).toLocaleTimeString('ar'))+'</span>')
      :'');
}
async function pRecover(){
  let all;
  try{ all=await pReadAll(); }
  catch(e){ pDbError=P.classifyStorageError(e); pSetStatus('FAILED');
            return {ok:false, code:pDbError}; }
  const pick=P.chooseRecovery(all.records);
  pState={pointer:all.pointer, records:all.records.map(r=>r&&r.record_id),
          last_good:pick.chosen_id, last_error:null,
          last_saved_at_ms:pick.chosen?pick.chosen.saved_at_ms:null};
  pRecovered=pick;
  /* الحجر لا يحذف: يُعلَّم السجلّ الفاسد ويُنقل جانباً، ولا يقع أصلاً إن لم
     يبقَ سجلّ سليم واحد. */
  if(pick.quarantine.length){
    try{
      const db=await idbOpen();
      await idbTx(db,[ST_REC],'readwrite',tx=>{
        const s=tx.objectStore(ST_REC);
        pick.quarantine.forEach(id=>{ if(!id) return;
          const g=s.get(id);
          g.onsuccess=()=>{ const rec=g.result; if(!rec) return;
            rec.quarantined=true; rec.quarantined_at_ms=Date.now();
            s.put(rec); }; }); });
      db.close();
    }catch(e){ /* الحجر تحسين لا شرط — فشله لا يفقد شيئاً */ }
  }
  if(!pick.chosen){
    pSetStatus('IDLE');
    if(pick.rejected.length) pBanner(pick);
    return {ok:false, code:pick.code, rejected:pick.rejected};
  }
  const d=P.decode(pick.chosen);
  if(!d.ok){ pSetStatus('FAILED'); pBanner(pick); return {ok:false, code:d.code}; }
  pSetStatus('RECOVERED');
  pBanner(pick, d);
  return {ok:true, code:'RECOVERED', project:d.project, migrated:d.migrated,
          record_id:pick.chosen_id};
}
function pBanner(pick, decoded){
  const box=$('acsRecoverBox'); if(!box) return;
  const bad=pick.rejected.length;
  let h='';
  if(decoded&&decoded.ok){
    h+='<div class="acs-rec-line"><b lang="ar">وُجد عمل محفوظ محلياً على هذا الجهاز</b>'
      +'<span lang="en" dir="ltr">Work saved locally on this device was found</span></div>'
      +'<div class="acs-rec-meta" dir="ltr">rev '+escT(decoded.revision_id||'—')
      +' · hash '+escT(String(decoded.model_hash||'').slice(0,10))
      +' · '+escT(new Date(decoded.saved_at_ms||0).toLocaleString('ar'))
      +(decoded.migrated?' · migrated from an older schema':'')+'</div>'
      +'<div class="acs-rec-act">'
      +'<button type="button" id="acsRecRestore" class="ghost">استعادة هذا العمل / Restore</button>'
      +'<button type="button" id="acsRecDismiss" class="ghost">تجاهل / Dismiss</button></div>';
  }
  if(bad){
    h+='<div class="acs-rec-bad"><b lang="ar">سجلّات محلية لم تُقبل — لم تُحذف</b>'
      +'<span lang="en" dir="ltr">Local records were not accepted — nothing was deleted</span>'
      +'<ul>'+pick.rejected.map(r=>'<li dir="ltr">'+escT(r.record_id||'(no id)')
        +' — '+escT(r.code)+'</li>').join('')+'</ul></div>';
  }
  box.innerHTML=h; box.style.display=h?'block':'none';
  const rb=$('acsRecRestore');
  if(rb) rb.onclick=()=>{
    const d=P.decode(pick.chosen);
    if(d.ok&&d.project&&d.project.model){
      try{ setModel(d.project.model); }catch(e){}
      statusEl.textContent='✓ استُعيد آخر عمل محفوظ محلياً على هذا الجهاز.';
    }
    box.style.display='none'; };
  const db2=$('acsRecDismiss');
  if(db2) db2.onclick=()=>{ box.style.display='none'; };
}
async function pClear(){
  const ok=window.confirm('سيُمسح كل ما هو محفوظ محلياً لهذا المشروع على هذا الجهاز '
    +'ولا يمكن التراجع. صدّر نسخة احتياطية أولاً إن أردت الاحتفاظ بها.\n\n'
    +'This deletes everything saved locally for this project on this device and '
    +'cannot be undone. Export a backup first if you want to keep it.');
  if(!ok) return {ok:false, code:'CANCELLED'};
  try{
    const db=await idbOpen();
    await idbTx(db,[ST_REC,ST_META],'readwrite',tx=>{
      tx.objectStore(ST_REC).clear(); tx.objectStore(ST_META).delete(PTR_KEY); });
    db.close();
    pState={pointer:null,records:[],last_good:null,last_error:null,last_saved_at_ms:null};
    pSetStatus('IDLE');
    const box=$('acsRecoverBox'); if(box){ box.innerHTML=''; box.style.display='none'; }
    return {ok:true, code:'CLEARED'};
  }catch(e){ return {ok:false, code:P.classifyStorageError(e)}; }
}
function pProject(){
  return {contract:'acs-local-project-payload/1',
    project_id:'default',
    current_revision:(window.ACS_CURRENT_REVISION||null),
    model:(typeof lastBuilding!=='undefined')?lastBuilding:null,
    request_text:(typeof __ACS_SHARED.LAST_REQUEST_TEXT!=='undefined')?__ACS_SHARED.LAST_REQUEST_TEXT:'',
    notes:(typeof notes!=='undefined')?notes:[],
    generation_in_flight:!!ACS_GEN_IN_FLIGHT};
}
function pDownload(name, mime, text){
  const blob=new Blob([text],{type:mime});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url; a.download=name; a.rel='noopener';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>{ try{ URL.revokeObjectURL(url); }catch(e){} },30000);
}

window.ACS.persistence={
  /* النواة النقيّة كما هي — هي المُختبَرة في Node */
  encode:P.encode, decode:P.decode, validateRecord:P.validateRecord,
  chooseRecovery:P.chooseRecovery, planWrite:P.planWrite,
  applyWriteResult:P.applyWriteResult, classifyStorageError:P.classifyStorageError,
  statusLabel:P.statusLabel, assertNoCloudClaim:P.assertNoCloudClaim,
  exportBackup:P.exportBackup, restoreBackup:P.restoreBackup,
  CONTRACT:P.CONTRACT, SCHEMA_VERSION:P.SCHEMA_VERSION, CODES:P.CODES,
  /* غلاف IndexedDB */
  save:(origin)=>pSave(pProject(), origin||'MANUAL'),
  recover:()=>pRecover(),
  clear:()=>pClear(),
  state:()=>JSON.parse(JSON.stringify(pState)),
  status:()=>({key:pStatusKey, label:P.statusLabel(pStatusKey),
               last_code:pLastCode, db_error:pDbError}),
  lastRecovery:()=>pRecovered?{code:pRecovered.code, chosen_id:pRecovered.chosen_id,
    accepted:pRecovered.accepted.length, rejected:pRecovered.rejected.slice(),
    preserved:pRecovered.preserve.slice(), quarantined:pRecovered.quarantine.slice()}:null,
  storage_kind:'INDEXEDDB_LOCAL_TO_THIS_DEVICE',
  is_cloud_backup:false
};

/* ═══════════ 2 · حالات الخطأ الظاهرة — مسار عرض واحد ═══════════ */
function showErrorState(res, onRetry, onLocal){
  const st=T.resolveErrorState(res||{});
  const box=$('reportBox');
  const rid=st.request_id||'';
  const wait=st.retry_after?(' — أعِد المحاولة بعد '+st.retry_after+' ثانية / retry after '
    +st.retry_after+'s'):'';
  if(box){
    box.className='report open';
    box.innerHTML=
      '<div class="acs-err" data-acs-error="'+escT(st.class)+'" role="alert">'
      +'<div class="acs-err-h" lang="ar">✕ '+escT(st.ar)+'</div>'
      +'<div class="acs-err-en" lang="en" dir="ltr">'+escT(st.en)+'</div>'
      +'<div class="acs-err-meta" dir="ltr">'
        +'class <code>'+escT(st.class)+'</code>'
        +' · retryable <code>'+(st.retryable?'yes':'no')+'</code>'
        +' · retry-safe <code>'+(st.retry_safe_for_operation?'yes':'no')+'</code>'
        +(st.http?(' · HTTP '+escT(String(st.http))):'')
        +escT(wait)
        +(rid?(' · request id <code id="acsReqId">'+escT(rid)+'</code>')
             :' · <span data-acs-noreqid="1">no request id (the request never reached the server)</span>')
      +'</div>'
      +'<div class="acs-err-act">'
        +(st.show_retry_button
          ?'<button id="acsRetryBtn" type="button">إعادة المحاولة / Retry</button>':'')
        +'<button id="acsLocalBtn" type="button">توليد محلي تقريبي (ليس ناتج المحرّك) / Local approximation</button>'
      +'</div></div>';
    const rb=$('acsRetryBtn'); if(rb&&onRetry) rb.onclick=onRetry;
    const lb=$('acsLocalBtn');
    if(lb){ if(onLocal) lb.onclick=onLocal; else lb.style.display='none'; }
  }
  try{ if(typeof statusEl!=='undefined'&&statusEl)
    statusEl.textContent='✕ '+st.ar+(rid?(' · معرّف الطلب '+rid):''); }catch(e){}
  const live=$('acsLiveRegion');
  if(live) live.textContent=st.ar+' — '+st.en;
  return st;
}
window.ACS.showErrorState=(res,onRetry,onLocal)=>showErrorState(res,onRetry,onLocal);

/* نُبدّل مسار الخطأ القائم بدل أن نبني نظاماً ثانياً: نفس العنصر، نفس
   معرّفات الأزرار، نفس المستدعين — والنصّ الآن من الجدول المعلن. */
__ACS_SHARED.acsErrorPanel=function(res,onRetry,onLocal){
  const r=res||{};
  return showErrorState({status:r.status, code:r.code, http:r.http,
    request_id:r.request_id, retry_after:r.retry_after,
    operation:r.operation||'GENERATE',
    idempotency_key:ACS_ACTIVE_IDEMPOTENCY_KEY}, onRetry, onLocal);
};

/* ═══════════ 3 · التزامن: قفل التنفيذ ومفتاح التكرار ═══════════ */
let cState={inflight:{},intent_seq:{},keys:{},completed:{}};
let ACS_ACTIVE_IDEMPOTENCY_KEY='';
let ACS_GEN_IN_FLIGHT=false;
const OP_PATHS={'/v1/understand':'GENERATE','/v1/edit':'EDIT',
  '/v1/understand/image':'UNDERSTAND_IMAGE','/v1/understand/pdf':'UNDERSTAND_PDF'};

/* نغلّف ناقل الشبكة القائم — لا ناقل ثانٍ: نضيف الرأس فقط. */
const _acsFetchBase=__ACS_SHARED.acsFetchJSON;
__ACS_SHARED.acsFetchJSON=function(path, opts, timeoutMs){
  const op=OP_PATHS[String(path||'').split('?')[0]];
  if(op&&ACS_ACTIVE_IDEMPOTENCY_KEY){
    const o=Object.assign({}, opts||{});
    o.headers=Object.assign({}, o.headers||{});
    o.headers['Idempotency-Key']=ACS_ACTIVE_IDEMPOTENCY_KEY;
    return _acsFetchBase(path,o,timeoutMs);
  }
  return _acsFetchBase(path,opts,timeoutMs);
};

function lockedRun(op, btnId, payload, fn, opts){
  const o=opts||{};
  const own=tabOwnership();
  if(o.requires_ownership&&own.owner_id&&!own.is_self){
    showErrorState({class:'STALE_REVISION', operation:op});
    liveSay(own.ar+' / '+own.en);
    return Promise.resolve({ok:false, code:'ANOTHER_TAB_OWNS'});
  }
  const r=T.concurrency.beginIntent(cState,{op:op, project_id:'default',
    base_revision:o.base_revision, payload_hash:T.concurrency.payloadHash(payload),
    now:Date.now()});
  if(!r.allowed){
    liveSay(r.ar+' / '+r.en);
    try{ if(typeof statusEl!=='undefined'&&statusEl) statusEl.textContent='⏳ '+r.ar; }catch(e){}
    return Promise.resolve({ok:false, code:r.code,
      idempotency_key:r.idempotency_key});
  }
  cState=r.state;
  ACS_ACTIVE_IDEMPOTENCY_KEY=r.idempotency_key;
  if(op==='GENERATE') ACS_GEN_IN_FLIGHT=true;
  const btn=btnId?$(btnId):null;
  if(btn){ btn.disabled=true; btn.setAttribute('aria-disabled','true');
           btn.setAttribute('aria-busy','true');
           btn.setAttribute('data-acs-inflight','1'); }
  const finish=(ok)=>{
    cState=T.concurrency.endIntent(cState,{op:op,project_id:'default'},{ok:!!ok}).state;
    ACS_ACTIVE_IDEMPOTENCY_KEY='';
    if(op==='GENERATE') ACS_GEN_IN_FLIGHT=false;
    if(btn){ btn.disabled=false; btn.removeAttribute('aria-disabled');
             btn.removeAttribute('aria-busy'); btn.removeAttribute('data-acs-inflight'); }
    tabSend('HEARTBEAT');
  };
  let p;
  try{ p=Promise.resolve(fn(r.idempotency_key)); }
  catch(e){ finish(false); throw e; }
  return p.then(v=>{ finish(true); return {ok:true, value:v,
                      idempotency_key:r.idempotency_key}; },
                e=>{ finish(false); throw e; });
}
window.ACS.inFlight=(op)=>T.concurrency.isInFlight(cState, op||'GENERATE','default');
window.ACS.activeIdempotencyKey=()=>ACS_ACTIVE_IDEMPOTENCY_KEY;
window.ACS.concurrencyState=()=>JSON.parse(JSON.stringify(cState));

/* ═══════════ 4 · تعدّد الألسنة ═══════════ */
const TAB_ID='tab_'+Math.random().toString(36).slice(2,8)+'_'+Date.now().toString(36);
let tState=T.concurrency.tabsReduce({self_id:TAB_ID},{type:'SELF',tab_id:TAB_ID},Date.now());
let bc=null;
try{ if(typeof BroadcastChannel!=='undefined') bc=new BroadcastChannel('acs_project_tabs'); }
catch(e){ bc=null; }
function tabSend(type){
  const msg={type:type, tab_id:TAB_ID, project_id:'default', ts:Date.now()};
  tState=T.concurrency.tabsReduce(tState,msg,Date.now());
  if(bc) try{ bc.postMessage(msg); }catch(e){}
  paintTabs();
}
if(bc) bc.onmessage=ev=>{
  tState=T.concurrency.tabsReduce(tState, ev&&ev.data, Date.now());
  if(ev&&ev.data&&ev.data.type==='HELLO') tabSend('HEARTBEAT');
  paintTabs(); };
function tabOwnership(){ return T.concurrency.tabOwner(tState,'default',Date.now()); }
function paintTabs(){
  const el=$('acsTabState'); if(!el) return;
  const o=tabOwnership();
  el.setAttribute('data-acs-tabs', o.code);
  el.innerHTML='<span class="ar" lang="ar">'+escT(o.ar)+'</span>'
    +'<span class="en" lang="en" dir="ltr">'+escT(o.en)+'</span>';
}
window.ACS.tabs=()=>({self:TAB_ID, owner:tabOwnership(),
  channel:bc?'BroadcastChannel':'UNAVAILABLE',
  state:JSON.parse(JSON.stringify(tState))});

/* ═══════════ 5 · F-16 · إفصاح القدرات ═══════════ */
const DISCLOSURE=T.capability.capabilityDisclosure(
  (typeof ACS_AUTHORING_SPEC!=='undefined')?ACS_AUTHORING_SPEC:{});
window.ACS.capabilityDisclosure=()=>JSON.parse(JSON.stringify(DISCLOSURE));

function discloseEl(el, kind, value){
  const e=DISCLOSURE.all_entries.filter(x=>x.kind===kind&&x.value===value)[0];
  if(!e) return false;
  el.disabled=true;
  el.setAttribute('aria-disabled','true');
  el.setAttribute('data-acs-unimplemented', kind+':'+value);
  el.setAttribute('title', value+' — '+e.label+' — '+e.why_en);
  el.setAttribute('aria-description', e.why_ar+' / '+e.why_en);
  el.setAttribute('aria-label', value+' — '+e.label_ar+' / '+e.label_en);
  el.onclick=null;
  return true;
}
/* التدقيق يجري على الصفحة المشحونة فعلاً وليس على ورق: أي عنصر يعلن أمراً
   أو التقاطاً أو مقبضاً غير منفَّذ ولا يُفصح ⇒ يُسجَّل ويُفصَح عنه قسراً. */
function auditCapabilityAffordances(root){
  const scope=root||document;
  const sel='[data-acs-cmd],[data-acs-snap],[data-acs-gizmo],[data-ws-op],[data-au-command]';
  const out={checked:0, violations:[], repaired:[]};
  Array.prototype.forEach.call(scope.querySelectorAll(sel), el=>{
    const kind=el.hasAttribute('data-acs-snap')?'SNAP'
              :el.hasAttribute('data-acs-gizmo')?'GIZMO':'COMMAND';
    const value=el.getAttribute('data-acs-cmd')||el.getAttribute('data-acs-snap')
      ||el.getAttribute('data-acs-gizmo')||el.getAttribute('data-ws-op')
      ||el.getAttribute('data-au-command')||'';
    out.checked++;
    const r=T.capability.auditAffordance({kind:kind, value:value,
      disabled:el.disabled===true,
      aria_disabled:el.getAttribute('aria-disabled'),
      text:(el.textContent||''), aria_label:el.getAttribute('aria-label')||'',
      title:el.getAttribute('title')||'',
      aria_description:el.getAttribute('aria-description')||'',
      has_handler:!!el.onclick}, DISCLOSURE);
    if(!r.ok){
      out.violations.push({value:value, kind:kind, violations:r.violations,
        id:el.id||null});
      if(discloseEl(el,kind,value)) out.repaired.push(value);
    }
  });
  return out;
}
window.ACS.auditCapabilityAffordances=(r)=>auditCapabilityAffordances(r);

function paintDisclosure(){
  const box=$('acsCapList'); if(!box) return;
  const gr=[['COMMAND','أوامر التحرير / Editing commands'],
            ['SNAP','أنواع الالتقاط / Snap types'],
            ['GIZMO','عمليات المقبض / Gizmo operations']];
  let h='';
  gr.forEach(([k,t])=>{
    const es=DISCLOSURE.all_entries.filter(e=>e.kind===k);
    if(!es.length) return;
    h+='<div class="acs-cap-g"><h4>'+escT(t)+'</h4>';
    es.forEach(e=>{
      h+='<button type="button" class="ghost acs-cap-btn" disabled '
        +'aria-disabled="true" '
        +'data-acs-'+(k==='COMMAND'?'cmd':k==='SNAP'?'snap':'gizmo')+'="'+escT(e.value)+'" '
        +'title="'+escT(e.value+' — '+e.label+' — '+e.why_en)+'" '
        +'aria-description="'+escT(e.why_ar+' / '+e.why_en)+'" '
        +'aria-label="'+escT(e.value+' — '+e.label_ar+' / '+e.label_en)+'">'
        +'<code dir="ltr">'+escT(e.value)+'</code> '
        +'<span class="acs-cap-lbl">'+escT(e.label)+'</span>'
        +'<span class="acs-cap-why" lang="ar">'+escT(e.why_ar)+'</span>'
        +'</button>';
    });
    h+='</div>';
  });
  box.innerHTML=h;
}

/* ═══════════ 6 · إتاحة الوصول — البديل النصّي للعرض ثلاثي الأبعاد ═══════════ */
function liveSay(t){ const el=$('acsLiveRegion'); if(el) el.textContent=String(t||''); }
window.ACS.announce=liveSay;

/* البنّاء نقيّ في النواة؛ هنا نُمرّر له النموذج الحيّ من نطاق الوحدة. */
const a11yBuild=b=>T.accessibility.buildModel(
  b||((typeof lastBuilding!=='undefined')?lastBuilding:null));
const a11yPlanSvg=p=>T.accessibility.planSvg(p, escT);
function a11yRender(){
  const host=$('acsA11yBody'); if(!host) return null;
  const d=a11yBuild(null);
  const N='<span class="unk" lang="ar">غير محدد</span>'
        +'<span class="unk en" lang="en" dir="ltr">Not specified</span>';
  const num=v=>(v==null||!isFinite(v))?N:escT(String(Math.round(v*100)/100));
  let h='';
  if(d.empty){
    h='<p lang="ar">لا يوجد مشروع محمَّل بعد. ولّد مبنى أو افتح مثالاً، ثمّ عُد إلى هنا.</p>'
     +'<p lang="en" dir="ltr">No project is loaded yet. Generate a building or open an '
     +'example, then return here.</p>';
    host.innerHTML=h; return d;
  }
  h+='<h3 id="acsA11yTreeH" lang="ar">شجرة المشروع <span lang="en" dir="ltr">· Project tree</span></h3>'
    +'<ul role="tree" aria-labelledby="acsA11yTreeH" class="acs-a11y-tree">';
  d.tree.forEach(l=>{
    h+='<li role="treeitem" aria-expanded="true"><span>'+escT(l.name)+'</span><ul role="group">'
      +l.children.map(c=>'<li role="treeitem">'+escT(c.name)+'</li>').join('')
      +'</ul></li>';
  });
  h+='</ul>';
  h+='<h3 id="acsA11yElH" lang="ar">قائمة العناصر وخصائصها '
    +'<span lang="en" dir="ltr">· Element list and properties</span></h3>'
    +'<table class="acs-a11y-tbl"><caption>كل قيمة غير معروفة تُعرض «غير محدد» '
    +'ولا تُستبدل بصفر أو تقدير / Any unknown value is shown as Not specified, '
    +'never as zero or an estimate.</caption><thead><tr>'
    +'<th scope="col">الدور</th><th scope="col">المعرّف</th>'
    +'<th scope="col">العرض (م)</th><th scope="col">العمق (م)</th>'
    +'<th scope="col">المساحة (م²)</th><th scope="col">أبواب</th>'
    +'<th scope="col">نوافذ</th><th scope="col">نقاط</th></tr></thead><tbody>';
  d.elements.forEach(e=>{
    h+='<tr><td>'+escT(e.level)+'</td><th scope="row">'+escT(e.id)+'</th>'
      +'<td>'+num(e.w)+'</td><td>'+num(e.d)+'</td><td>'+num(e.area)+'</td>'
      +'<td>'+escT(String(e.doors))+'</td><td>'+escT(String(e.windows))+'</td>'
      +'<td>'+escT(String(e.points))+'</td></tr>';
  });
  h+='</tbody></table>';
  h+='<h3 lang="ar">المسقط الأفقي <span lang="en" dir="ltr">· Floor plan</span></h3>'
    +'<div class="acs-a11y-plan">'+a11yPlanSvg(d.plan)+'</div>';
  h+='<h3 id="acsA11yIsH" lang="ar">الملاحظات <span lang="en" dir="ltr">· Issues</span></h3>'
    +'<ul aria-labelledby="acsA11yIsH" class="acs-a11y-iss">'
    +(d.issues.length?d.issues.map(i=>'<li data-sev="'+escT(i.severity)+'">'
      +'<b dir="ltr">'+escT(i.severity)+'</b> <span lang="ar">'+escT(i.ar)+'</span> '
      +'<span lang="en" dir="ltr">'+escT(i.en)+'</span></li>').join('')
      :'<li lang="ar">لا ملاحظات مسجّلة على النموذج الحالي.</li>')
    +'</ul>';
  d.schedules.forEach((s,si)=>{
    h+='<h3 id="acsA11ySch'+si+'">'+escT(s.name)+'</h3>'
      +'<table class="acs-a11y-tbl" aria-labelledby="acsA11ySch'+si+'"><thead><tr>'
      +'<th scope="col">الدور</th><th scope="col">الفراغ</th>'
      +'<th scope="col">العرض</th><th scope="col">العمق</th>'
      +'<th scope="col">المساحة</th><th scope="col">أبواب</th>'
      +'<th scope="col">نوافذ</th></tr></thead><tbody>'
      +s.rows.map(r=>'<tr><td>'+escT(r.level)+'</td><th scope="row">'+escT(r.id)
        +'</th><td>'+num(r.w)+'</td><td>'+num(r.d)+'</td><td>'+num(r.area)
        +'</td><td>'+escT(String(r.doors))+'</td><td>'+escT(String(r.windows))
        +'</td></tr>').join('')
      +'</tbody></table>';
  });
  host.innerHTML=h;
  return d;
}
window.ACS.accessibleModel=()=>a11yBuild(null);
window.ACS.renderAccessibleAlternative=()=>a11yRender();

/* إدارة تركيز الحوارات — للبديل النصّي ولنافذة ملاحظة المهندس */
const FOCUSABLE='a[href],button:not([disabled]),input:not([disabled]),'
  +'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function trapFocus(el, ev){
  const items=Array.prototype.filter.call(el.querySelectorAll(FOCUSABLE),
    n=>n.offsetParent!==null||n===document.activeElement);
  if(!items.length) return;
  const first=items[0], last=items[items.length-1];
  if(ev.shiftKey && document.activeElement===first){ ev.preventDefault(); last.focus(); }
  else if(!ev.shiftKey && document.activeElement===last){ ev.preventDefault(); first.focus(); }
}
function makeModal(el, closeFn){
  if(!el||el.getAttribute('data-acs-modal')==='1') return;
  el.setAttribute('data-acs-modal','1');
  el.addEventListener('keydown', ev=>{
    if(ev.key==='Escape'){ ev.stopPropagation(); closeFn(); }
    else if(ev.key==='Tab'){ trapFocus(el, ev); }
  });
}
let a11yReturnFocus=null;
function a11yOpen(){
  const p=$('acsA11yAlt'); if(!p) return;
  a11yReturnFocus=document.activeElement;
  a11yRender();
  p.classList.add('on');
  p.removeAttribute('aria-hidden');
  const c=$('acsA11yClose'); if(c) c.focus();
  liveSay('فُتح البديل النصّي للعرض ثلاثي الأبعاد.');
}
function a11yClose(){
  const p=$('acsA11yAlt'); if(!p) return;
  p.classList.remove('on');
  p.setAttribute('aria-hidden','true');
  if(a11yReturnFocus&&a11yReturnFocus.focus) a11yReturnFocus.focus();
}
window.ACS.openAccessibleAlternative=a11yOpen;
window.ACS.closeAccessibleAlternative=a11yClose;

/* ═══════════ 7 · التوصيل بعناصر الصفحة القائمة ═══════════ */
function wireAll(){
  /* 7a-c · أساس ARIA (لغة مساحة العمل، المناطق الحيّة، حوار الملاحظة، مصيدة
     التركيز، Escape) يملكه السكربت الكلاسيكي «ACS A11Y BASELINE» وحده، فيبقى
     عاملاً حتى إن فشل استيراد Three.js ومات سكربت الوحدة كلّه. لا نكرّره هنا:
     مالك واحد لكل سلوك. */

  /* 7d · الحفظ المحلي */
  const bs=$('acsSaveNow');
  if(bs) bs.onclick=()=>{ window.ACS.persistence.save('MANUAL'); };
  const be=$('acsExportBackup');
  if(be) be.onclick=()=>{
    const r=P.exportBackup(pProject(),{now:Date.now()});
    if(!r.ok){ liveSay('تعذّر تجهيز النسخة الاحتياطية.'); return; }
    pDownload(r.file.filename, r.file.mime, r.file.text);
    liveSay('نُزِّلت نسخة احتياطية إلى جهازك — لم تُرفع إلى أي خادم.'); };
  const br=$('acsRestoreBackup');
  if(br) br.onchange=ev=>{
    const f=ev.target.files&&ev.target.files[0]; if(!f) return;
    const rd=new FileReader();
    rd.onload=()=>{
      const r=P.restoreBackup(rd.result);
      const out=$('acsRestoreState');
      if(r.ok&&r.project&&r.project.model){
        try{ setModel(r.project.model); }catch(e){}
        if(out) out.textContent='✓ استُعيدت النسخة الاحتياطية من ملفّك المحلي.'
          +' / Backup restored from your local file.';
        liveSay('استُعيدت النسخة الاحتياطية.');
      }else{
        if(out) out.textContent='✕ لم تُقبل النسخة الاحتياطية ('+r.code+') — '
          +'لم يُغيَّر شيء. / Backup rejected ('+r.code+') — nothing was changed.';
      }
      ev.target.value='';
    };
    rd.readAsText(f); };
  const bc2=$('acsClearLocal');
  if(bc2) bc2.onclick=async()=>{
    const r=await pClear();
    const out=$('acsRestoreState');
    if(out) out.textContent=(r.ok?'✓ مُسحت البيانات المحلية على هذا الجهاز.'
      :'لم يُمسح شيء ('+r.code+').'); };

  /* 7e · إفصاح القدرات */
  paintDisclosure();
  const audit=auditCapabilityAffordances(document);
  window.ACS.lastCapabilityAudit=()=>JSON.parse(JSON.stringify(audit));
  if(audit.violations.length)
    console.warn('[ACS-F16] undisclosed unimplemented affordance(s) repaired at runtime:',
                 audit.violations);

  /* 7f · البديل النصّي — الفتح والإغلاق ومصيدة التركيز يملكها السكربت
     الكلاسيكي؛ هنا نملأ محتواه من النموذج وحسب. */
  const ob=$('acsA11yOpen');
  if(ob) ob.addEventListener('click', ()=>{ a11yRender();
    liveSay('فُتح البديل النصّي للعرض ثلاثي الأبعاد.'); });
  const rb=$('acsA11yRefresh'); if(rb) rb.onclick=()=>{ a11yRender();
    liveSay('حُدِّث البديل النصّي من النموذج الحالي.'); };

  /* 7g · قفل النقر المزدوج على التوليد + مفتاح التكرار */
  const g=$('genLLM');
  if(g){
    g.onclick=()=>{
      const txt=($('descText')||{}).value||'';
      lockedRun('GENERATE','genLLM',
        {text:txt, w:($('siteW')||{}).value, d:($('siteD')||{}).value,
         f:($('nFloors')||{}).value},
        ()=>acsGenerateFromServer());
    };
  }
  /* 7h · قفل الإيداع + حارس المراجعة القاعدية */
  const na=$('bNotesApply');
  if(na){
    const base=na.onclick;
    na.onclick=()=>{
      const cur=window.ACS_CURRENT_REVISION||null;
      const chk=T.concurrency.checkBaseRevision(cur, ACS_EDIT_BASE_REVISION||cur);
      if(!chk.ok&&chk.code==='STALE_BASE_REVISION'){
        showErrorState({class:'STALE_REVISION', operation:'COMMIT'});
        return; }
      lockedRun('EDIT','bNotesApply',
        {notes:(typeof notes!=='undefined')?notes:[], base:cur},
        ()=>base.call(na), {requires_ownership:true, base_revision:cur});
    };
  }
  /* 7i · قفل التصدير — لا ملفّان من نقرة مزدوجة */
  [['bGlb','EXPORT'],['bJson','EXPORT'],['bShot','EXPORT'],
   ['acsExportBackup','EXPORT']].forEach(([id,op])=>{
    const el=$(id); if(!el||!el.onclick) return;
    const base=el.onclick;
    el.onclick=()=>lockedRun(op+':'+id, id, {t:Date.now()},
      ()=>new Promise(r=>{ base.call(el); setTimeout(r,400); }));
  });

  /* 7i2 · مزامنة aria مع أصناف CSS يملكها السكربت الكلاسيكي وحده. */

  /* 7j · الحفظ التلقائي واستعادة ما بعد إعادة التحميل */
  pSetStatus('IDLE');
  paintTabs(); tabSend('HELLO');
  setInterval(()=>tabSend('HEARTBEAT'), 5000);
  window.addEventListener('pagehide',()=>{ if(bc) try{ bc.postMessage(
    {type:'BYE',tab_id:TAB_ID,project_id:'default',ts:Date.now()}); }catch(e){} });

  let lastHash='';
  const tick=()=>{
    let m=null;
    try{ m=(typeof lastBuilding!=='undefined')?lastBuilding:null; }catch(e){ m=null; }
    if(!m) return;
    const h=T.hash(T.canonical(m));
    if(h===lastHash) return;
    lastHash=h;
    pSave(pProject(),'AUTOSAVE');
  };
  setInterval(tick, 2500);
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='hidden') tick(); });

  pRecover().then(r=>{
    window.ACS.recoveryResult=()=>r;
    if(r.ok&&r.project&&r.project.model){
      let has=false;
      try{ has=!!lastBuilding; }catch(e){ has=false; }
      if(!has){
        try{ setModel(r.project.model); }catch(e){}
        pSetStatus('RECOVERED');
        try{ if(typeof statusEl!=='undefined'&&statusEl)
          statusEl.textContent='✓ استُعيد آخر عمل محفوظ محلياً على هذا الجهاز'
            +(r.project.generation_in_flight
              ?' — كان التوليد جارياً وقت الإغلاق ولم يكتمل؛ أعِد الضغط على «توليد».'
              :'.'); }catch(e){}
      }
    }
  }).catch(()=>{});
}
let ACS_EDIT_BASE_REVISION=null;

if(document.readyState==='loading')
  document.addEventListener('DOMContentLoaded', wireAll);
else wireAll();

window.ACS.trustReady=true;
})();
/* ===== END ACS PRODUCTION TRUST WIRING ===== */
