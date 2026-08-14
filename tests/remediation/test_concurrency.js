/* ============================================================================
   التزامن وسلامة الفعل المزدوج.
     node tests/lib/run.js tests/remediation/test_concurrency.js
   يُثبت على الدوالّ النقيّة المشحونة في الصفحة: مفتاح التكرار المستقرّ لكل
   نيّة، قفل التنفيذ، رفض المراجعة القاعدية القديمة، وكشف تعدّد الألسنة.
   ========================================================================== */
const _np=require('path');
const LOAD=require(_np.join(__dirname,'_trust_core.js'));
const {T, page}=LOAD.load();
const K=T.concurrency;
let pass=0, fail=0;
const chk=(n,c,d)=>{ c?(pass++,console.log('  ✓',n))
                      :(fail++,console.log('  ✗',n,d===undefined?'':d)); };
const S0=()=>({inflight:{},intent_seq:{},keys:{},completed:{}});

console.log('\n== §1 — مفتاح التكرار مشتقّ من النيّة لا من المحاولة ==');
(function(){
  const base={op:'GENERATE', project_id:'p1', base_revision:'rev_3',
              payload_hash:'aaaa', intent_seq:1};
  chk('the same intent yields the same key, every time',
      K.intentKey(base)===K.intentKey(JSON.parse(JSON.stringify(base))));
  chk('the key is namespaced by operation so two operations never collide',
      K.intentKey(base).indexOf('acs-generate-')===0
      && K.intentKey(Object.assign({},base,{op:'COMMIT'})).indexOf('acs-commit-')===0);
  chk('a different payload is a different intent',
      K.intentKey(Object.assign({},base,{payload_hash:'bbbb'}))!==K.intentKey(base));
  chk('a different base revision is a different intent',
      K.intentKey(Object.assign({},base,{base_revision:'rev_4'}))!==K.intentKey(base));
  chk('a different project is a different intent',
      K.intentKey(Object.assign({},base,{project_id:'p2'}))!==K.intentKey(base));
  chk('a new user intent (next sequence) is a different key',
      K.intentKey(Object.assign({},base,{intent_seq:2}))!==K.intentKey(base));
  chk('payloadHash is stable across key order — it hashes meaning, not text',
      K.payloadHash({a:1,b:2})===K.payloadHash({b:2,a:1}));
  chk('payloadHash separates different payloads',
      K.payloadHash({a:1})!==K.payloadHash({a:2}));
})();

console.log('\n== §2 — نقر مزدوج على «توليد»: طلب واحد، فوترة واحدة ==');
(function(){
  let s=S0();
  const req={op:'GENERATE', project_id:'default', payload_hash:'h1', now:1};
  const a=K.beginIntent(s, req);
  chk('the first click is allowed', a.allowed===true, a.code);
  chk('the first click carries an Idempotency-Key header',
      a.headers && typeof a.headers['Idempotency-Key']==='string'
      && a.headers['Idempotency-Key']===a.idempotency_key, a.headers);
  s=a.state;
  chk('the operation is now recorded as in flight',
      K.isInFlight(s,'GENERATE','default')===true);
  const b=K.beginIntent(s, Object.assign({},req,{now:2}));
  chk('THE SECOND CLICK IS REFUSED while the first is in flight',
      b.allowed===false && b.code==='REQUEST_ALREADY_IN_FLIGHT', b.code);
  chk('the refusal is explained to the user in Arabic and English',
      b.ar.length>10 && b.en.length>10 && /[؀-ۿ]/.test(b.ar) && /[A-Za-z]/.test(b.en));
  chk('the refusal reports the SAME key — no second billable request exists',
      b.idempotency_key===a.idempotency_key && b.reused_key===true);
  chk('a refused second click does not start a second in-flight slot',
      Object.keys(b.state.inflight).length===1);
  /* ثلاث نقرات متتالية */
  let s3=a.state, refused=0;
  for(let i=0;i<5;i++){ const r=K.beginIntent(s3, Object.assign({},req,{now:3+i}));
    if(!r.allowed) refused++; else s3=r.state; }
  chk('five further rapid clicks are all refused', refused===5, refused);
  s=K.endIntent(s, req, {ok:true}).state;
  chk('after completion the lock is released',
      K.isInFlight(s,'GENERATE','default')===false);
})();

console.log('\n== §3 — إعادة المحاولة تحمل نفس المفتاح؛ النيّة الجديدة تحمل مفتاحاً جديداً ==');
(function(){
  let s=S0();
  const req={op:'GENERATE', project_id:'default', payload_hash:'same', now:1};
  const a=K.beginIntent(s, req); s=a.state;
  s=K.endIntent(s, req, {ok:false}).state;                 /* فشل ⇒ إعادة محاولة */
  const b=K.beginIntent(s, Object.assign({},req,{now:2}));
  chk('A RETRY OF THE SAME INTENT REUSES THE KEY — the server can deduplicate it',
      b.idempotency_key===a.idempotency_key, [a.idempotency_key,b.idempotency_key]);
  s=K.endIntent(b.state, req, {ok:true}).state;            /* نجح الآن */
  const c=K.beginIntent(s, Object.assign({},req,{now:3}));
  chk('a NEW click after a completed intent is a NEW key — not a replay',
      c.idempotency_key!==a.idempotency_key);
  const d=K.beginIntent(S0(), Object.assign({},req,{payload_hash:'changed'}));
  chk('editing the description before clicking is a new intent, hence a new key',
      d.idempotency_key!==a.idempotency_key);
})();

console.log('\n== §4 — الإيداع والتصدير يقفلان بنفس الآلية، ولا يخلطان أسلاكهما ==');
(function(){
  let s=S0();
  const gen={op:'GENERATE', project_id:'default', payload_hash:'g'};
  const com={op:'COMMIT', project_id:'default', payload_hash:'c'};
  s=K.beginIntent(s, gen).state;
  const c1=K.beginIntent(s, com);
  chk('a commit is not blocked merely because a generate is running',
      c1.allowed===true);
  s=c1.state;
  chk('a second commit IS blocked while the first commit is in flight',
      K.beginIntent(s, com).code==='REQUEST_ALREADY_IN_FLIGHT');
  chk('both operations are tracked independently',
      K.isInFlight(s,'GENERATE','default')&&K.isInFlight(s,'COMMIT','default'));
  const e=K.endIntent(s, com, {ok:true}).state;
  chk('ending the commit does not release the generate lock',
      K.isInFlight(e,'GENERATE','default')===true
      && K.isInFlight(e,'COMMIT','default')===false);
  let x=S0();
  x=K.beginIntent(x,{op:'EXPORT:bJson', project_id:'default', payload_hash:'e'}).state;
  chk('a double-click on export is refused too — one file, not two',
      K.beginIntent(x,{op:'EXPORT:bJson', project_id:'default', payload_hash:'e'})
        .allowed===false);
  chk('exporting a DIFFERENT artefact is not blocked by the first export',
      K.beginIntent(x,{op:'EXPORT:bGlb', project_id:'default', payload_hash:'e'})
        .allowed===true);
})();

console.log('\n== §5 — تبديل المشروع أثناء التوليد ==');
(function(){
  let s=S0();
  s=K.beginIntent(s,{op:'GENERATE', project_id:'p1', payload_hash:'h'}).state;
  const other=K.beginIntent(s,{op:'GENERATE', project_id:'p2', payload_hash:'h'});
  chk('a generate on a different project is a separate slot with a separate key',
      other.allowed===true && other.idempotency_key
        !==s.keys['GENERATE|p1'].idempotency_key);
  chk('the first project stays locked while its generation runs',
      K.isInFlight(other.state,'GENERATE','p1')===true);
  chk('the two projects never share an idempotency key',
      other.state.keys['GENERATE|p1'].idempotency_key
      !==other.state.keys['GENERATE|p2'].idempotency_key);
})();

console.log('\n== §6 — مراجعة قاعدية قديمة تُرفض برمز حتمي واحد ==');
(function(){
  const ok=K.checkBaseRevision('rev_9','rev_9');
  chk('committing on the current revision is allowed',
      ok.ok===true && ok.code==='BASE_REVISION_CURRENT' && ok.http_status===200);
  const stale=K.checkBaseRevision('rev_10','rev_9');
  chk('committing on a stale base revision is REFUSED',
      stale.ok===false && stale.code==='STALE_BASE_REVISION', stale.code);
  chk('the refusal is deterministic: HTTP 409, every time',
      stale.http_status===409
      && K.checkBaseRevision('rev_10','rev_9').http_status===409
      && K.checkBaseRevision('rev_10','rev_9').code===stale.code);
  chk('the refusal names both revisions so the user can re-base',
      stale.current_revision==='rev_10' && stale.base_revision==='rev_9');
  chk('the refusal speaks Arabic and English',
      /[؀-ۿ]/.test(stale.ar) && /[A-Za-z]/.test(stale.en)
      && stale.ar.length>20 && stale.en.length>20);
  chk('a missing base revision is its own refusal, not a silent pass',
      K.checkBaseRevision('rev_10', null).ok===false
      && K.checkBaseRevision('rev_10', null).code==='MISSING_BASE_REVISION');
  chk('a fresh project with no current revision does not falsely refuse',
      K.checkBaseRevision(null,'rev_1').ok===true);
  chk('the refusal maps onto the declared STALE_REVISION user state',
      T.resolveErrorState({class:'STALE_REVISION'}).ar===stale.ar);
})();

console.log('\n== §7 — تعدّد الألسنة: مالك واحد محدَّد، لا سباق ==');
(function(){
  const NOW=100000;
  let s={self_id:'tab_a', tabs:{}};
  s=K.tabsReduce(s,{type:'SELF',tab_id:'tab_a'},NOW);
  s=K.tabsReduce(s,{type:'HELLO',tab_id:'tab_a',project_id:'default'},NOW);
  let o=K.tabOwner(s,'default',NOW);
  chk('a single tab owns the project and is told so',
      o.owner_id==='tab_a' && o.is_self===true && o.code==='THIS_TAB_OWNS', o);
  s=K.tabsReduce(s,{type:'HELLO',tab_id:'tab_b',project_id:'default'},NOW+1000);
  o=K.tabOwner(s,'default',NOW+1000);
  chk('when a second tab appears the FIRST claimant still owns the project',
      o.owner_id==='tab_a' && o.tabs===2, o);
  chk('the owning tab is told it owns it, and how many others are open',
      o.is_self===true && o.ar.indexOf('هذا اللسان هو صاحب المشروع')>=0, o.ar);
  /* من منظور اللسان الثاني */
  let s2={self_id:'tab_b', tabs:JSON.parse(JSON.stringify(s.tabs))};
  const o2=K.tabOwner(s2,'default',NOW+1000);
  chk('THE OTHER TAB IS TOLD WHICH TAB OWNS THE PROJECT',
      o2.is_self===false && o2.code==='ANOTHER_TAB_OWNS'
      && o2.ar.indexOf('tab_a')>=0 && o2.en.indexOf('tab_a')>=0, o2.ar);
  chk('the non-owning tab is told editing is disabled there',
      o2.ar.indexOf('معطّل')>=0 && o2.en.toLowerCase().indexOf('disabled')>=0);
  chk('ownership is decided by claim time then id — never by message arrival order',
      K.tabOwner(K.tabsReduce(K.tabsReduce({self_id:'x',tabs:{}},
        {type:'HELLO',tab_id:'tab_b',project_id:'default',claimed_at_ms:5},NOW),
        {type:'HELLO',tab_id:'tab_a',project_id:'default',claimed_at_ms:1},NOW),
        'default',NOW).owner_id==='tab_a');
  /* لسان يموت بلا وداع */
  const later=NOW+1000+K.TAB_TTL_MS+1;
  s=K.tabsReduce(s,{type:'HEARTBEAT',tab_id:'tab_b',project_id:'default'},later);
  const o3=K.tabOwner(s,'default',later);
  chk('a tab that stopped sending heartbeats is expired, not kept forever',
      o3.owner_id==='tab_b' && o3.tabs===1, o3);
  /* وداع صريح */
  let s4=K.tabsReduce({self_id:'tab_a',tabs:{}},
    {type:'HELLO',tab_id:'tab_a',project_id:'default'},NOW);
  s4=K.tabsReduce(s4,{type:'HELLO',tab_id:'tab_b',project_id:'default'},NOW);
  s4=K.tabsReduce(s4,{type:'BYE',tab_id:'tab_a'},NOW);
  chk('an explicit BYE hands ownership over immediately',
      K.tabOwner(s4,'default',NOW).owner_id==='tab_b');
  chk('a different project has its own ownership, not a shared global lock',
      K.tabOwner(s4,'other_project',NOW).code==='NO_TAB');
  chk('the reducer is pure — it does not mutate the state handed to it',
      (function(){ const a={self_id:'t',tabs:{}};
        K.tabsReduce(a,{type:'HELLO',tab_id:'z',project_id:'default'},NOW);
        return Object.keys(a.tabs).length===0; })());
})();

console.log('\n== §8 — الصفحة المشحونة توصّل هذا فعلاً ==');
(function(){
  chk('the shipped page sends the Idempotency-Key header on the engine calls',
      page.indexOf("o.headers['Idempotency-Key']=ACS_ACTIVE_IDEMPOTENCY_KEY;")>=0);
  chk('the header is added by wrapping the ONE existing transport, not a second one',
      page.indexOf('const _acsFetchBase=acsFetchJSON;')>=0
      && page.indexOf('acsFetchJSON=function(path, opts, timeoutMs){')>=0);
  chk('the key is only attached to the operations that need it',
      page.indexOf("const OP_PATHS={'/v1/understand':'GENERATE','/v1/edit':'EDIT',")>=0);
  chk('the generate button is disabled while a request is in flight',
      page.indexOf("btn.disabled=true; btn.setAttribute('aria-disabled','true');")>=0
      && page.indexOf("btn.setAttribute('aria-busy','true');")>=0);
  chk('the in-flight state is exposed on the element so it is testable',
      page.indexOf("btn.setAttribute('data-acs-inflight','1');")>=0);
  chk('generate, commit and export all go through the same lock',
      page.indexOf("lockedRun('GENERATE','genLLM'")>=0
      && page.indexOf("lockedRun('EDIT','bNotesApply'")>=0
      && page.indexOf("[['bGlb','EXPORT'],['bJson','EXPORT'],['bShot','EXPORT'],")>=0);
  chk('a commit checks the base revision before it is allowed to start',
      page.indexOf('T.concurrency.checkBaseRevision(cur, ACS_EDIT_BASE_REVISION||cur)')>=0);
  chk('a stale base revision shows the declared user state instead of committing',
      page.indexOf("showErrorState({class:'STALE_REVISION', operation:'COMMIT'});")>=0);
  chk('multi-tab detection uses BroadcastChannel',
      page.indexOf("new BroadcastChannel('acs_project_tabs')")>=0);
  chk('a heartbeat keeps tab liveness honest',
      page.indexOf("setInterval(()=>tabSend('HEARTBEAT'), 5000);")>=0);
  chk('the user is shown which tab owns the project',
      page.indexOf('id="acsTabState"')>=0 && page.indexOf('paintTabs()')>=0);
  chk('a tab that does not own the project cannot commit',
      page.indexOf('requires_ownership:true')>=0
      && page.indexOf("code:'ANOTHER_TAB_OWNS'")>=0);
  chk('window.ACS exposes the concurrency surface for verification',
      page.indexOf('window.ACS.inFlight=')>=0
      && page.indexOf('window.ACS.activeIdempotencyKey=')>=0
      && page.indexOf('window.ACS.tabs=')>=0);
})();

console.log('\n══════════════════════════════════════════════');
console.log('CONCURRENCY AND DOUBLE-ACTION SAFETY: '+pass+' passed, '+fail+' failed');
console.log('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: that the LIVE backend honours '
  +'the Idempotency-Key header and returns 409 on a stale base revision needs egress '
  +'to the deployment (blocked here, 403). This suite proves the page-side contract.');
if(fail) process.exit(1);
