/* ============================================================================
   واجهة الخطأ الإنتاجية — جدول واحد معلن، كلّي على عقد أخطاء الخادم.
     node tests/lib/run.js tests/remediation/test_production_error_ui.js
   يقرأ acs_api_errors.py مباشرةً فلا تنجو خريطة ناقصة من هذا الاختبار: كل رمز
   يُصدره الخادم لا بدّ أن يصل إلى حالة يراها المستخدم بالعربية والإنجليزية.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const LOAD=require(_np.join(__dirname,'_trust_core.js'));
const {T, page, ROOT}=Object.assign({}, LOAD.load(), {ROOT:LOAD.ROOT});
let pass=0, fail=0;
const chk=(n,c,d)=>{ c?(pass++,console.log('  ✓',n))
                      :(fail++,console.log('  ✗',n,d===undefined?'':d)); };

/* ── الرموز تُقرأ من الملفّ الأصلي، لا من نسخة في الاختبار ── */
const PY=fs.readFileSync(_np.join(LOAD.ROOT,'acs_api_errors.py'),'utf8');
const CONSTS={};
PY.replace(/^(ACS_[A-Z_]+)\s*=\s*"([^"]+)"/gm,(m,k,v)=>{ CONSTS[k]=v; return m; });
const mTuple=/^CODES\s*=\s*\(([\s\S]*?)\)\s*$/m.exec(PY);
if(!mTuple) throw new Error('CODES tuple not found in acs_api_errors.py');
const CODES=mTuple[1].split(',').map(s=>s.trim()).filter(Boolean)
  .map(nm=>CONSTS[nm]).filter(Boolean);
const RETRYABLE=(/^RETRYABLE\s*=\s*frozenset\(\{([\s\S]*?)\}\)/m.exec(PY)||[,''])[1]
  .split(',').map(s=>s.trim()).filter(Boolean).map(nm=>CONSTS[nm]).filter(Boolean);

console.log('\n== §0 — عقد الأخطاء قُرئ من المصدر ==');
chk('acs_api_errors.CODES was read from the python source', CODES.length===26,
    CODES.length);
chk('every code resolved to a real string constant',
    CODES.every(c=>typeof c==='string'&&/^ACS_[A-Z_]+$/.test(c)));
chk('RETRYABLE was read from the python source', RETRYABLE.length>=5, RETRYABLE.length);

console.log('\n== §1 — الجدول معلن مرّة واحدة وكل صنف مطلوب موجود ==');
(function(){
  const S=T.errorStates;
  chk('the page declares one error-state table on window.ACS.errorStates',
      page.indexOf('window.ACS.errorStates  = T.errorStates;')>=0
      || page.indexOf('window.ACS.errorStates=T.errorStates')>=0);
  const REQUIRED=['NETWORK_OFFLINE','NETWORK_DNS','TIMEOUT','HTTP_429',
    'HTTP_4XX_VALIDATION','HTTP_5XX','INVALID_JSON','PROVIDER_UNAVAILABLE',
    'FILE_REJECTED','WEBGL_UNSUPPORTED','WEBGL_CONTEXT_LOST','BLACK_VIEWPORT',
    'STORAGE_QUOTA','STALE_REVISION'];
  REQUIRED.forEach(k=>chk('the required class '+k+' has a declared user state', !!S[k]));
  chk('the table declares exactly the fourteen required classes and no filler',
      Object.keys(S).length===REQUIRED.length, Object.keys(S));
  chk('every class is distinguishable — no two share a code',
      new Set(Object.keys(S).map(k=>S[k].code)).size===Object.keys(S).length);
  chk('every class is distinguishable — no two share an Arabic message',
      new Set(Object.keys(S).map(k=>S[k].ar)).size===Object.keys(S).length);
  chk('the table is frozen against accidental mutation at runtime',
      Object.isFrozen(S));
})();

console.log('\n== §2 — كل صنف يحمل عربية وإنجليزية وقابلية إعادة معلنة ==');
(function(){
  const S=T.errorStates;
  const AR=/[؀-ۿ]/, LAT=/[A-Za-z]/;
  Object.keys(S).forEach(k=>{
    const e=S[k];
    chk(k+' has Arabic text', typeof e.ar==='string'&&e.ar.length>=15&&AR.test(e.ar), e.ar);
    chk(k+' has English text',
        typeof e.en==='string'&&e.en.length>=15&&LAT.test(e.en)&&!AR.test(e.en), e.en);
    chk(k+' states retryability as a boolean', typeof e.retryable==='boolean');
    chk(k+' states retry safety as a boolean', typeof e.retry_safe==='boolean');
    chk(k+' declares an action for the user', typeof e.action==='string'&&e.action.length>2);
    chk(k+' declares that a request id is carried for support',
        e.request_id_required===true);
    chk(k+' never carries a stack trace',
        e.shows_stack_trace===false
        && !T.containsStackTrace(e.ar) && !T.containsStackTrace(e.en));
  });
})();

console.log('\n== §3 — لا أثر مكدّس في أي نصّ يراه المستخدم ==');
(function(){
  const S=T.errorStates;
  const all=Object.keys(S).map(k=>S[k].ar+' '+S[k].en+' '+S[k].code+' '+S[k].action).join(' ');
  chk('no entry contains a stack-trace marker', T.containsStackTrace(all)===false);
  chk('the stack-trace detector is not vacuous — it fires on a real JS trace',
      T.containsStackTrace('TypeError: x is undefined\n    at foo (/app/index.js:12:3)')===true);
  chk('the stack-trace detector fires on a real python traceback',
      T.containsStackTrace('Traceback (most recent call last):\n  File "a.py", line 1')===true);
  chk('the resolved state for every class also carries no stack trace',
      Object.keys(S).every(k=>{
        const r=T.resolveErrorState({class:k, request_id:'req_1'});
        return r.shows_stack_trace===false
          && !T.containsStackTrace(r.ar+' '+r.en); }));
})();

console.log('\n== §4 — الخريطة كلّية على acs_api_errors.CODES ==');
(function(){
  const cov=T.errorStateCoverage(CODES);
  chk('every backend code resolves to a user state — the map is TOTAL',
      cov.complete===true && cov.missing.length===0, cov.missing);
  chk('the coverage check actually counted all 26 codes', cov.total===26, cov.total);
  CODES.forEach(code=>{
    const st=T.resolveErrorState({code:code, status:'VALID_API_ERROR',
      request_id:'req_'+code, operation:'GENERATE'});
    chk(code+' → a named user class with Arabic and English',
        !!T.errorStates[st.class] && st.ar.length>10 && st.en.length>10, st.class);
  });
  chk('the coverage check is not vacuous — an unmapped code is reported missing',
      T.errorStateCoverage(['ACS_SOMETHING_NEW']).complete===false);
  chk('an unknown code still resolves to a visible state rather than silence',
      T.resolveErrorState({code:'ACS_SOMETHING_NEW'}).ar.length>10);
  chk('resolveErrorState never returns null for any input',
      [null,undefined,{},{http:0},{status:'???'}].every(
        x=>{ const r=T.resolveErrorState(x); return !!r && !!r.ar && !!r.en; }));
})();

console.log('\n== §5 — retry_safe يكون false لكل عملية غير متماثلة ==');
(function(){
  const S=T.errorStates, OPS=T.operations;
  const nonIdem=Object.keys(OPS).filter(o=>OPS[o].idempotent===false);
  chk('the operation table declares non-idempotent operations',
      nonIdem.length>=3 && nonIdem.indexOf('GENERATE')>=0
      && nonIdem.indexOf('COMMIT')>=0 && nonIdem.indexOf('EDIT')>=0, nonIdem);
  nonIdem.forEach(op=>{
    Object.keys(S).forEach(k=>{
      const r=T.resolveErrorState({class:k, operation:op, request_id:'r'});
      chk('retry is NOT declared safe for '+k+' on the non-idempotent '+op,
          r.retry_safe_for_operation===false, r); });
  });
  chk('a retry button is never offered for a non-idempotent operation without a key',
      Object.keys(S).every(k=>
        T.resolveErrorState({class:k, operation:'GENERATE'}).show_retry_button===false));
  chk('with an idempotency key present, a retryable class MAY offer retry safely',
      T.resolveErrorState({class:'TIMEOUT', operation:'GENERATE',
        idempotency_key:'acs-generate-abc'}).show_retry_button===true);
  chk('an idempotency key does NOT make a non-retryable class retryable',
      T.resolveErrorState({class:'HTTP_4XX_VALIDATION', operation:'GENERATE',
        idempotency_key:'acs-generate-abc'}).show_retry_button===false
      && T.resolveErrorState({class:'STALE_REVISION', operation:'COMMIT',
        idempotency_key:'k'}).show_retry_button===false);
  chk('for an idempotent operation a retry-safe class does offer retry',
      T.resolveErrorState({class:'NETWORK_DNS', operation:'EXPORT'})
        .show_retry_button===true);
  /* الأصناف التي قد يكون الطلب فيها قد وصل الخادم ليست آمنة للإعادة أصلاً */
  ['TIMEOUT','HTTP_5XX','INVALID_JSON','PROVIDER_UNAVAILABLE'].forEach(k=>
    chk(k+' is not baseline retry-safe: the request may already have been processed',
        S[k].retry_safe===false));
  ['NETWORK_OFFLINE','NETWORK_DNS'].forEach(k=>
    chk(k+' is baseline retry-safe: the request never reached the server',
        S[k].retry_safe===true));
})();

console.log('\n== §6 — قابلية الإعادة تحترم ما يقوله الخادم ==');
(function(){
  RETRYABLE.forEach(code=>{
    const st=T.resolveErrorState({code:code});
    chk(code+' is declared retryable by the backend and by the UI table',
        st.retryable===true, st.class); });
  ['ACS_UPSTREAM_AUTH','ACS_UPSTREAM_PERMISSION','ACS_UPSTREAM_MODEL_REJECTED']
    .forEach(code=>{
      const st=T.resolveErrorState({code:code});
      chk(code+' maps to a class that states the fault is configuration, not the user',
          st.class==='PROVIDER_UNAVAILABLE'); });
  chk('a validation failure is NOT presented as retryable',
      T.resolveErrorState({code:'ACS_VALIDATION_FAILED'}).retryable===false);
  chk('a stale revision is refused deterministically with HTTP 409',
      T.errorStates.STALE_REVISION.http_status===409);
})();

console.log('\n== §7 — معرّف الطلب يُعرَض للدعم، وغيابه يُصرَّح به ==');
(function(){
  const withId=T.resolveErrorState({code:'ACS_INTERNAL', request_id:'req_abc123'});
  chk('a request id survives into the resolved state', withId.request_id==='req_abc123');
  const noId=T.resolveErrorState({class:'NETWORK_DNS'});
  chk('a missing request id is an empty string, never a fabricated one',
      noId.request_id==='');
  chk('the page renders the request id when present, and says so when absent',
      page.indexOf('request id <code id="acsReqId">')>=0
      && page.indexOf('data-acs-noreqid="1"')>=0);
})();

console.log('\n== §8 — مسار عرض واحد لا اثنان ==');
(function(){
  chk('the existing error panel is REPLACED, not duplicated',
      page.indexOf('acsErrorPanel=function(res,onRetry,onLocal){')>=0);
  chk('the replacement renders into the existing #reportBox, not a new surface',
      page.indexOf("const box=$('reportBox');")>=0);
  chk('the replacement keeps the existing retry/local button ids',
      page.indexOf("id=\"acsRetryBtn\"")>=0 && page.indexOf("id=\"acsLocalBtn\"")>=0);
  chk('the replacement also updates the existing #status element',
      page.indexOf("statusEl.textContent='✕ '+st.ar")>=0);
  chk('the replacement announces on the existing aria-live region',
      page.indexOf("const live=$('acsLiveRegion');")>=0);
  chk('no second toast or notification system was introduced',
      page.indexOf('acsToastContainer')<0 && page.indexOf('ACS_NOTIFY_STACK')<0);
  chk('the shipped page carries the class attribute so the UI is testable',
      page.indexOf('data-acs-error="')>=0);
})();

console.log('\n══════════════════════════════════════════════');
console.log('PRODUCTION ERROR UI: '+pass+' passed, '+fail+' failed');
console.log('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: that a LIVE backend actually '
  +'emits each of these codes needs egress to the deployment (blocked here, 403).');
if(fail) process.exit(1);
