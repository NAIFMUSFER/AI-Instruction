/* ======================================================================
   المرحلة 2 — اختبارات أساس التصنيف النظامي للإشغال وسياق الكود.
   كل التصنيفات اصطناعية: TEST_OCC_* ، regulatory=false ، synthetic=true.
   لا اسم مجموعة إشغال حقيقي من أي كود في أي موضع.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='T0', WHO='explicit_manual_approval';
const EV=[{type:'manual_review',ref:'reviewer',detail:'synthetic verification for engine testing'}];
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);

function hotel(){ const b=C(FX.hotel); b.wall_t=0.20; return b; }
function ctx(){ const c=newCodeContext(); return c; }
/* يفعّل حزمة تصنيف اصطناعية عبر مسارها الكامل: DRAFT → UNDER_REVIEW → VERIFIED_PARTIAL → تثبيت */
function activate(store,project,packId,version){
  const p=occPack(store,packId,version||'1');
  verifyOccupancyPack(p,'UNDER_REVIEW',null,AT,WHO,null);
  verifyOccupancyPack(p,'VERIFIED_PARTIAL',null,AT,WHO,null);
  project.code_context.classification_packs.push({pack_id:packId,version:version||'1',enabled:true});
  return activeOccupancyPacks(project,store); }
const RULE=(id)=>ruleById(id,[],'TEST_ONLY.CORE');
function evalRule(id,b,subjId,store,project,extraCtx){
  const rels=buildRelationships(b,'bld_0');
  const idx=occupancyIndex(store,[subjId]);
  const s=resolveSubject(b,rels,subjId,'bld_0',idx);
  const p=RULE(id);
  return evaluateRule(p[1],s,Object.assign({evaluated_at:AT},extraCtx||{}),p[0],[]); }

console.log('\n== §37 — NO REAL CLASSIFICATIONS ==');
let store=occupancyFixtureStore();
chk('real regulatory verified classifications = 0', occRealClassificationCount(store)===0);
chk('every shipped pack is synthetic and non-regulatory',
    store.packs.every(p=>p.synthetic===true&&p.regulatory===false));
// نفحص المحتوى نفسه لا عبارة الإخلاء التي تذكر هذه الأسماء لتنفيها
const REGTXT=JSON.stringify(ACS_OCCUPANCY_REGISTRY.packs);
chk('no SBC/IBC occupancy group name in any shipped classification',
    !/\bSBC\b|\bIBC\b|Group [A-Z]-?\d?\b|occupancy group/i.test(REGTXT), REGTXT.slice(0,60));
chk('the disclaimer names those codes only to exclude them',
    /No SBC, IBC or any real occupancy group name appears/.test(ACS_OCCUPANCY_REGISTRY.note));
chk('every classification id is namespaced TEST_OCC',
    store.packs.every(p=>p.classifications.every(c=>/^TEST_OCC/.test(c.id))));
chk('packs ship as DRAFT with nothing activated',
    store.packs.every(p=>p.verification.status==='DRAFT')&&
    activeOccupancyPacks(ctx(),store).packs.length===0);
chk('registry validates clean', occupancyIssues(store).length===0, JSON.stringify(occupancyIssues(store)));
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_occupancy.json'),'utf8'));
chk('browser registry is byte-identical to acs_occupancy.json',
    JSON.stringify(sk(ACS_OCCUPANCY_REGISTRY))===JSON.stringify(sk(CANON)));

console.log('\n== §1 — CODE CONTEXT MODEL ==');
const cc=newCodeContext();
chk('jurisdiction starts entirely null',
    cc.jurisdiction.country===null&&cc.jurisdiction.region===null&&cc.jurisdiction.authority===null);
chk('code_context starts with no standard, edition or packs',
    cc.code_context.standard===null&&cc.code_context.edition===null&&
    cc.code_context.rulepacks.length===0&&cc.code_context.classification_packs.length===0);
chk('occupancy starts UNCLASSIFIED', cc.occupancy.status==='UNCLASSIFIED');
chk('code context validates clean', validateCodeContext(cc).length===0);
chk('a pack reference must state enabled explicitly',
    (()=>{const c=C(cc); c.code_context.classification_packs.push({pack_id:'p',version:'1'});
      return validateCodeContext(c).some(i=>/enabled explicitly/.test(i));})());
chk('phase 1/2 building JSON is untouched by the code context',
    !/code_context|occupancy/.test(JSON.stringify(hotel())));

console.log('\n== TEST A (§22) — PROGRAM IS NOT OCCUPANCY ==');
store=occupancyFixtureStore(); let project=ctx();
const b=hotel();
chk('building program is hotel', (b.meta||{}).type==='hotel');
chk('with nothing activated, the subject is UNCLASSIFIED',
    resolveOccupancy('BUILDING:bld_0',store).status==='UNCLASSIFIED');
chk('a program suggestion produces nothing while no pack is activated',
    suggestOccupancyFromProgram('BUILDING:bld_0','BUILDING','hotel',store,project,AT).length===0);
activate(store,project,'TEST_ONLY.OCCPACK');
const sug=suggestOccupancyFromProgram('BUILDING:bld_0','BUILDING','hotel',store,project,AT);
sug.forEach(c=>addOccupancyClassification(store,c));
chk('an explicit suggestion call yields CANDIDATE only',
    sug.length===1&&sug[0].status==='CANDIDATE', JSON.stringify(sug.map(x=>[x.group,x.status])));
chk('the suggestion is never VERIFIED', sug[0].status!=='VERIFIED');
chk('its source is AI_SUGGESTED', sug[0].source==='AI_SUGGESTED');
chk('the resolved subject status is CANDIDATE, not VERIFIED',
    resolveOccupancy('BUILDING:bld_0',store).status==='CANDIDATE');
chk('the hint records that it is a suggestion only',
    /suggestion only/.test(JSON.stringify(sug[0].evidence)));
chk('acs_programs.json was not turned into a classification registry',
    !/TEST_OCC|occupancy_group|regulatory/.test(JSON.stringify(ACS_PROGRAMS)));

console.log('\n== TEST B (§23) — AI SUGGESTION CANNOT SATISFY A RULE ==');
let r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',store,project);
chk('rule requiring verified occupancy is NOT_EVALUATED', r.status==='NOT_EVALUATED', r.status);
chk('reason is OCCUPANCY_NOT_VERIFIED', r.reason==='OCCUPANCY_NOT_VERIFIED', r.reason);
chk('no PASS and no FAIL', r.status!=='PASS'&&r.status!=='FAIL');
chk('AI can never verify a classification',
    verifyOccupancy(sug[0],store,project,null,AT,'ai_suggestion',EV,null)[1]==='AI_MAY_NOT_VERIFY');
chk('verification without evidence is refused',
    verifyOccupancy(sug[0],store,project,null,AT,WHO,null,null)[1]==='VERIFICATION_EVIDENCE_REQUIRED');
chk('an AI_SUGGESTED record carrying VERIFIED is structurally invalid',
    (()=>{const c=C(sug[0]); c.status='VERIFIED'; c.verification={x:1};
      return validateOccupancyClassification(c,store).some(i=>/AI_SUGGESTED.*VERIFIED/.test(i));})());

console.log('\n== TEST C (§24) — MANUAL VERIFICATION OF A SYNTHETIC CLASSIFICATION ==');
const v=verifyOccupancy(sug[0],store,project,null,AT,WHO,EV,'synthetic engine probe');
chk('explicit manual approval verifies it', v[0]===true, v[1]);
chk('status is VERIFIED', sug[0].status==='VERIFIED');
chk('source changed to MANUAL_VERIFIED and the origin is retained',
    sug[0].source==='MANUAL_VERIFIED'&&sug[0].verification.source_before==='AI_SUGGESTED');
chk('no verifier identity is fabricated', sug[0].verification.verifier===null);
chk('the verification pins the pack and its edition',
    sug[0].verification.pack_id==='TEST_ONLY.OCCPACK'&&sug[0].verification.edition==='0');
r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',store,project);
chk('the occupancy-dependent synthetic rule now evaluates', r.status==='PASS', r.status+' '+r.reason);
chk('the actual value is the verified group', r.actual.value==='TEST_OCC_A', JSON.stringify(r.actual));
chk('data quality COMPLETE and applicability APPLICABLE',
    r.data_quality==='COMPLETE'&&r.applicability==='APPLICABLE');
chk('CODE_REQUIRED stays false — the data is synthetic',
    r.code_required_eligible===false&&r.regulatory===false);
chk('occupancy evidence is part of the result chain',
    r.evidence.some(e=>e.type==='occupancy'), JSON.stringify(r.evidence));
chk('input provenance is user (a human verified it), not ai_inference',
    r.input_provenance['occupancy.group']==='user', JSON.stringify(r.input_provenance));
chk('real regulatory classification count is still 0', occRealClassificationCount(store)===0);

console.log('\n== TEST D (§25) — MIXED OCCUPANCY ==');
let mstore=occupancyFixtureStore(), mproj=ctx();
activate(mstore,mproj,'TEST_ONLY.OCCPACK');
const spaces=['SPACE:bld_0.t.guest_1','SPACE:bld_0.t.guest_2','SPACE:bld_0.g.lobby','SPACE:bld_0.t.core'];
const groups=['TEST_OCC_A','TEST_OCC_A','TEST_OCC_B','TEST_OCC_B'];
spaces.forEach((sid,i)=>{
  const d=declareOccupancy(sid,'SPACE',groups[i],mstore,mproj,null,null,AT,'portion declaration');
  addOccupancyClassification(mstore,d[0]);
  verifyOccupancy(d[0],mstore,mproj,null,AT,WHO,EV,null); });
chk('four space-level classifications coexist', mstore.classifications.length===4);
chk('two portions are TEST_OCC_A',
    resolveOccupancy(spaces[0],mstore).group==='TEST_OCC_A'&&
    resolveOccupancy(spaces[1],mstore).group==='TEST_OCC_A');
chk('two portions are TEST_OCC_B',
    resolveOccupancy(spaces[2],mstore).group==='TEST_OCC_B'&&
    resolveOccupancy(spaces[3],mstore).group==='TEST_OCC_B');
chk('no building-wide collapse — the building itself stays UNCLASSIFIED',
    resolveOccupancy('BUILDING:bld_0',mstore).status==='UNCLASSIFIED');
chk('differing groups on DIFFERENT subjects are not a conflict',
    resolveOccupancy(spaces[0],mstore).status==='VERIFIED'&&
    resolveOccupancy(spaces[2],mstore).status==='VERIFIED');
chk('mixed_use as a building program is not a classification',
    (()=>{const mb=C(b); mb.meta.type='mixed_use';
      return resolveOccupancy('BUILDING:bld_0',occupancyFixtureStore()).status==='UNCLASSIFIED';})());
chk('classification subjects span BUILDING, LEVEL, SPACE and ZONE',
    ['BUILDING','LEVEL','SPACE','ZONE'].every(t=>OCC_SUBJECT_TYPES.indexOf(t)>=0));
chk('no separation or rated assembly is claimed anywhere',
    !/separation|rated_assembly|fire_rating/i.test(JSON.stringify(mstore)));
const aud=auditOccupancy(mstore,spaces.concat(['BUILDING:bld_0']));
chk('audit counts verified and unclassified separately',
    aud.verified===4&&aud.unclassified===1&&aud.subjects_total===5, JSON.stringify(aud));
chk('audit makes no compliance statement', /not a compliance statement/.test(aud.note));

console.log('\n== TEST E (§26) — CONFLICT ==');
let cstore=occupancyFixtureStore(), cproj=ctx();
activate(cstore,cproj,'TEST_ONLY.OCCPACK');
['TEST_OCC_A','TEST_OCC_B'].forEach(g=>{
  const d=declareOccupancy('BUILDING:bld_0','BUILDING',g,cstore,cproj,null,null,AT,'conflicting source');
  addOccupancyClassification(cstore,d[0]);
  verifyOccupancy(d[0],cstore,cproj,null,AT,WHO,EV,null); });
const res=resolveOccupancy('BUILDING:bld_0',cstore);
chk('two verified conflicting classifications ⇒ CONFLICT', res.status==='CONFLICT', res.status);
chk('reason is OCCUPANCY_CLASSIFICATION_CONFLICT', res.reason==='OCCUPANCY_CLASSIFICATION_CONFLICT');
chk('neither group is silently chosen', res.group===null);
r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',cstore,cproj);
chk('dependent rule is NOT_EVALUATED', r.status==='NOT_EVALUATED', r.status);
chk('rule reason names the conflict', r.reason==='OCCUPANCY_CLASSIFICATION_CONFLICT', r.reason);
chk('both classifications remain listed as candidates', res.candidates.length===2);

console.log('\n== TEST F (§27) — EDITION MISMATCH ==');
let estore=occupancyFixtureStore(), eproj=ctx();
activate(estore,eproj,'TEST_ONLY.OCCPACK_ED9');
const ed=declareOccupancy('BUILDING:bld_0','BUILDING','TEST_OCC_A',estore,eproj,null,null,AT,null);
addOccupancyClassification(estore,ed[0]);
verifyOccupancy(ed[0],estore,eproj,null,AT,WHO,EV,null);
chk('the classification verifies under edition 9',
    resolveOccupancy('BUILDING:bld_0',estore).status==='VERIFIED'&&
    resolveOccupancy('BUILDING:bld_0',estore).edition==='9');
r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',estore,eproj);
chk('an edition-0 rule refuses an edition-9 classification',
    r.status==='NOT_EVALUATED'&&r.reason==='OCCUPANCY_EDITION_MISMATCH', r.status+'/'+r.reason);
chk('no cross-edition laundering into PASS/FAIL', r.status!=='PASS'&&r.status!=='FAIL');
chk('the mismatch is recorded as evidence',
    r.evidence.some(e=>e.type==='alignment'), JSON.stringify(r.evidence.slice(-1)));

console.log('\n== §18 — JURISDICTION ALIGNMENT ==');
let jstore=occupancyFixtureStore(), jproj=ctx();
jstore.packs[0].jurisdiction={country:'OTHERLAND',region:null,authority:null};
activate(jstore,jproj,'TEST_ONLY.OCCPACK');
const jd=declareOccupancy('BUILDING:bld_0','BUILDING','TEST_OCC_A',jstore,jproj,null,null,AT,null);
addOccupancyClassification(jstore,jd[0]);
verifyOccupancy(jd[0],jstore,jproj,null,AT,WHO,EV,null);
r=evalRule('TEST_ONLY.OCC_JUR_001',b,'BUILDING:bld_0',jstore,jproj,{jurisdiction:{country:'TESTLAND'}});
chk('a TESTLAND rule refuses an OTHERLAND classification',
    r.status==='NOT_EVALUATED'&&r.reason==='OCCUPANCY_JURISDICTION_MISMATCH', r.status+'/'+r.reason);
chk('jurisdiction and occupancy are never silently combined', r.status!=='PASS'&&r.status!=='FAIL');

console.log('\n== TEST G (§28) — UNKNOWN OCCUPANCY ==');
let ustore=occupancyFixtureStore(), uproj=ctx();
r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',ustore,uproj);
chk('no classification at all ⇒ NOT_EVALUATED, reason OCCUPANCY_NOT_CLASSIFIED',
    r.status==='NOT_EVALUATED'&&r.reason==='OCCUPANCY_NOT_CLASSIFIED', r.status+'/'+r.reason);
r=evalRule('TEST_ONLY.OCC_REQUIRED_001',b,'BUILDING:bld_0',ustore,uproj);
chk('a rule without a quality gate ⇒ INSUFFICIENT_DATA',
    r.status==='INSUFFICIENT_DATA'&&/occupancy.group/.test(r.reason), r.status+'/'+r.reason);
chk('the reason names OCCUPANCY_NOT_VERIFIED', /OCCUPANCY_NOT_VERIFIED/.test(r.reason), r.reason);
chk('neither PASS nor FAIL', r.status!=='PASS'&&r.status!=='FAIL');

console.log('\n== TEST H (§29) — USER DECLARED ==');
let dstore=occupancyFixtureStore(), dproj=ctx();
activate(dstore,dproj,'TEST_ONLY.OCCPACK');
const dec=declareOccupancy('BUILDING:bld_0','BUILDING','TEST_OCC_A',dstore,dproj,null,
                           null,AT,'stated by the design team');
addOccupancyClassification(dstore,dec[0]);
chk('a user declaration is recorded', dec[0]!==null&&dec[0].declared_value==='TEST_OCC_A');
chk('it is CANDIDATE, not VERIFIED', dec[0].status==='CANDIDATE'&&dec[0].source==='USER_DECLARED');
chk('no identity is invented when there is no auth', dec[0].declared_by===null);
chk('declaration time is recorded from the caller', dec[0].declaration_time===AT);
r=evalRule('TEST_ONLY.OCC_ENUM_001',b,'BUILDING:bld_0',dstore,dproj);
chk('a declared-but-unverified occupancy cannot satisfy a rule',
    r.status==='NOT_EVALUATED'&&r.reason==='OCCUPANCY_NOT_VERIFIED', r.status+'/'+r.reason);
chk('explicit verification is what promotes it',
    verifyOccupancy(dec[0],dstore,dproj,null,AT,WHO,EV,null)[0]===true&&dec[0].status==='VERIFIED');
chk('a group absent from every active pack cannot be declared',
    declareOccupancy('BUILDING:bld_0','BUILDING','TEST_OCC_INVENTED',dstore,dproj,null,null,AT,null)[1]
      ==='GROUP_NOT_IN_ANY_ACTIVE_CLASSIFICATION_PACK');

console.log('\n== TEST I (§30) — LANGUAGE INFERS NOTHING ==');
let lstore=occupancyFixtureStore(), lproj=ctx();
const ar=C(b); ar.meta.request_text='فندق فخم في الرياض يحتوي على غرف نزلاء ومطعم';
chk('Arabic text does not set a jurisdiction',
    lproj.jurisdiction.country===null&&validateCodeContext(lproj).length===0);
chk('Arabic text does not classify anything',
    resolveOccupancy('BUILDING:bld_0',lstore).status==='UNCLASSIFIED');
r=evalRule('TEST_ONLY.OCC_JUR_001',ar,'BUILDING:bld_0',lstore,lproj);
chk('a jurisdiction-gated rule stays NOT_EVALUATED / JURISDICTION_NOT_SET',
    r.status==='NOT_EVALUATED'&&r.reason==='JURISDICTION_NOT_SET', r.status+'/'+r.reason);
chk('the word فندق never becomes a verified occupancy',
    lstore.classifications.length===0&&occRealClassificationCount(lstore)===0);

console.log('\n== §14/§34 — CLASSIFICATION PACK LIFECYCLE & SECURITY ==');
let pstore=occupancyFixtureStore(), pproj=ctx();
const pk=occPack(pstore,'TEST_ONLY.OCCPACK','1');
chk('DRAFT → VERIFIED_PARTIAL directly is refused',
    verifyOccupancyPack(pk,'VERIFIED_PARTIAL',null,AT,WHO,null)[0]===false);
chk('AI may not verify a classification pack',
    verifyOccupancyPack(pk,'UNDER_REVIEW',null,AT,'ai_suggestion',null)[1]==='AI_MAY_NOT_VERIFY');
chk('DRAFT → UNDER_REVIEW → VERIFIED_PARTIAL works',
    verifyOccupancyPack(pk,'UNDER_REVIEW',null,AT,WHO,null)[0]===true&&
    verifyOccupancyPack(pk,'VERIFIED_PARTIAL',null,AT,WHO,null)[0]===true);
chk('VERIFIED_FOR_DECLARED_SCOPE needs declared completeness',
    verifyOccupancyPack(pk,'VERIFIED_FOR_DECLARED_SCOPE',null,AT,WHO,null)[1]
      ==='SCOPE_COMPLETENESS_NOT_DECLARED');
chk('a verified pack is inert until the project pins it',
    activeOccupancyPacks(ctx(),pstore).packs.length===0);
chk('a disabled reference does not activate',
    (()=>{const pj=ctx(); pj.code_context.classification_packs.push(
      {pack_id:'TEST_ONLY.OCCPACK',version:'1',enabled:false});
      return activeOccupancyPacks(pj,pstore).rejected[0].reason==='NOT_ENABLED';})());
chk('duplicate classification ids in a pack are rejected',
    (()=>{const p2=C(pk); p2.classifications.push(C(p2.classifications[0]));
      return validateOccupancyPack(p2).some(i=>/duplicate classification id/.test(i));})());
chk('unknown pack state rejected',
    (()=>{const p2=C(pk); p2.verification.status='TOTALLY_FINE';
      return validateOccupancyPack(p2).some(i=>/unknown classification pack status/.test(i));})());
chk('script content rejected',
    (()=>{const p2=C(pk); p2.classifications[0].title='<script>x</script>';
      return validateOccupancyPack(p2).some(i=>/executable/.test(i));})());
chk('javascript: url rejected',
    (()=>{const p2=C(pk); p2.classifications[0].definition_reference='javascript:alert(1)';
      return validateOccupancyPack(p2).some(i=>/executable/.test(i));})());
chk('a regulatory pack must cite source documents',
    (()=>{const p2=C(pk); p2.regulatory=true;
      return validateOccupancyPack(p2).some(i=>/must cite source documents/.test(i));})());
chk('a classification citing an unknown group is rejected',
    (()=>{const c=newOccupancyClassification({subject_id:'BUILDING:bld_0',subject_type:'BUILDING',
      group:'TEST_OCC_NOPE',pack_id:'TEST_ONLY.OCCPACK',pack_version:'1',source:'USER_DECLARED'});
      c.declared_value='TEST_OCC_NOPE';
      return validateOccupancyClassification(c,pstore).some(i=>/does not exist in classification pack/.test(i));})());
chk('EXTRACTED-style jump UNCLASSIFIED → VERIFIED is not a legal transition',
    canTransitionOccupancy('UNCLASSIFIED','VERIFIED')===false);
chk('READY_FOR_VERIFICATION → VERIFIED is legal',
    canTransitionOccupancy('READY_FOR_VERIFICATION','VERIFIED')===true);
chk('all seven classification states exist', OCC_STATES.length===7);

console.log('\n== §33 — EXPORT ==');
const ex=exportOccupancy(mstore,mproj);
chk('export preserves status, source, evidence, standard, edition and verification',
    ex.classifications.every(c=>c.status&&c.source&&c.evidence&&c.standard&&c.edition&&
      ('verification' in c)));
chk('export marks only VERIFIED rows as authoritative',
    ex.classifications.every(c=>c.authoritative===(c.status==='VERIFIED')));
chk('export states that AI suggestions are never authoritative',
    /never authoritative/.test(ex.note));
chk('export reports zero real regulatory classifications', ex.real_regulatory_verified===0);
chk('export lists activated packs explicitly', ex.activated_classification_packs.length===1);

console.log(`\nOCCUPANCY: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
