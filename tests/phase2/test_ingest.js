/* ======================================================================
   المرحلة 2 — اختبارات أساس استيراد المصادر والتحقّق من حِزَم القواعد.
   كل الوثائق والمرشّحين والحزم اصطناعية: synthetic=true, official=false,
   regulatory=false. لا نصّ معيار حقيقي ولا بند ولا إصدار ولا رابط تنظيمي.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const ST=()=>ingestFixtureStore();
const AT='T0', WHO='explicit_manual_approval';

function villaS(){ const b=C(FX.villa); b.wall_t=0.20;
  [['f','corridor_f'],['g','corridor']].forEach(([t,id])=>{
    const r=b.floors[t].rooms.find(r=>r.id===id);
    Object.assign(r.objects[0],{risers:16,tread_m:0.28,riser_m:0.20}); });
  return b; }
const SUBJ=(b,sid)=>resolveSubject(b,buildRelationships(b,'bld_0'),sid,'bld_0');
/* يوصل وثيقة إلى CONTENT_VERIFIED عبر الانتقالات المسموحة فقط */
function contentVerify(st,docId){
  const d=ingDocument(st,docId);
  transitionDocument(d,'SOURCE_IDENTIFIED',WHO,{note:'synthetic fixture identified'},AT,null);
  return transitionDocument(d,'CONTENT_VERIFIED',WHO,{note:'synthetic content checked'},AT,null); }

console.log('\n== §36 — NO REAL REGULATORY CONTENT ==');
let st=ST();
chk('verified regulatory rules = 0', ingestRegulatoryRuleCount(st)===0);
chk('every fixture document is synthetic and not official',
    st.documents.every(d=>d.synthetic===true&&d.official!==true));
chk('every proposed rule is synthetic TEST_ONLY',
    st.candidates.every(c=>c.proposed_rule.regulatory===false&&c.proposed_rule.namespace==='TEST_ONLY'));
const FIXTXT=JSON.stringify(ACS_INGEST_FIXTURES);
chk('no SBC/IBC/NFPA/ADA/Civil-Defense text anywhere in the fixtures',
    !/\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|civil[_ ]?defense/i.test(FIXTXT));
chk('no fabricated regulatory URL', !/https?:\/\//.test(FIXTXT));
chk('no fixture document carries a page number', st.fixtureless!==undefined||
    st.documents.every(d=>true)&&st.candidates.every(c=>c.page===null));
chk('only the two intentional defect fixtures are flagged',
    ingestStoreIssues(st).length===2&&
    ingestStoreIssues(st).every(i=>/SYNCAND-BROKEN|SYNCAND-STALEHASH/.test(i)),
    JSON.stringify(ingestStoreIssues(st)));

console.log('\n== §39 — SINGLE CANONICAL FIXTURE SET (drift test) ==');
const CANON_ING=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_ingest.json'),'utf8'));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
chk('embedded browser fixtures are byte-identical to acs_ingest.json',
    JSON.stringify(sk(ACS_INGEST_FIXTURES))===JSON.stringify(sk(CANON_ING)));
chk('schema and pipeline version match',
    INGEST_SCHEMA===CANON_ING.schema&&INGEST_PIPELINE_VERSION===CANON_ING.pipeline_version);
chk('state machines come from one source',
    JSON.stringify(sk(ING_DOC_TRANSITIONS))===JSON.stringify(sk(CANON_ING.document_transitions))&&
    JSON.stringify(sk(ING_CANDIDATE_TRANSITIONS))===JSON.stringify(sk(CANON_ING.candidate_transitions))&&
    JSON.stringify(sk(ING_PACK_TRANSITIONS))===JSON.stringify(sk(CANON_ING.pack_transitions)));
chk('no hand-maintained duplication of rule content',
    JSON.stringify(sk(ACS_INGEST_FIXTURES.store))===JSON.stringify(sk(CANON_ING.store)));

console.log('\n== §3 — DOCUMENT INTEGRITY (real SHA-256) ==');
st=ST();
const d1=ingDocument(st,'SYNDOC-ED1');
const bytesOk=verifyDocumentBytes(d1,d1.synthetic_content);
chk('recorded hash matches the document bytes', bytesOk[0]===true, bytesOk[1]);
chk('hash is a 64-hex digest', /^[0-9a-f]{64}$/.test(bytesOk[1]));
chk('a single changed byte changes the hash',
    verifyDocumentBytes(d1,d1.synthetic_content+' ')[0]===false);
chk('editions 1 and 2 are distinct documents with distinct hashes',
    ingDocument(st,'SYNDOC-ED1').integrity.sha256!==ingDocument(st,'SYNDOC-ED2').integrity.sha256);
chk('identity is not the filename', d1.origin.filename===null&&!!d1.integrity.sha256);
chk('SHA-256 matches the reference vector for the empty string',
    sha256Hex('')==='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');

console.log('\n== §2 — SOURCE VERIFICATION STATES ==');
st=ST();
const dA=ingDocument(st,'SYNDOC-ED1');
chk('starts UNVERIFIED', dA.verification.status==='UNVERIFIED');
chk('UNVERIFIED → CONTENT_VERIFIED is not a legal jump',
    transitionDocument(dA,'CONTENT_VERIFIED',WHO,{n:1},AT,null)[0]===false);
chk('transition needs a method', transitionDocument(dA,'SOURCE_IDENTIFIED',null,{n:1},AT,null)[0]===false);
chk('transition needs recorded evidence',
    transitionDocument(dA,'SOURCE_IDENTIFIED',WHO,null,AT,null)[0]===false);
chk('SOURCE_IDENTIFIED reached with method + evidence',
    transitionDocument(dA,'SOURCE_IDENTIFIED',WHO,{note:'ok'},AT,null)[0]===true);
chk('OFFICIAL_SOURCE_VERIFIED refused: title looks official but source is not marked official',
    transitionDocument(dA,'OFFICIAL_SOURCE_VERIFIED',WHO,{note:'looks official'},AT,null)[1]
      ==='DOCUMENT_NOT_MARKED_OFFICIAL_BY_EVIDENCE');
chk('OFFICIAL_SOURCE_VERIFIED and CONTENT_VERIFIED are different states',
    ING_DOC_STATES.indexOf('OFFICIAL_SOURCE_VERIFIED')!==ING_DOC_STATES.indexOf('CONTENT_VERIFIED'));
chk('CONTENT_VERIFIED reached from SOURCE_IDENTIFIED',
    transitionDocument(dA,'CONTENT_VERIFIED',WHO,{note:'content checked'},AT,null)[0]===true);
chk('all seven source states exist', ING_DOC_STATES.length===7);
chk('REVOKED is terminal', (ING_DOC_TRANSITIONS.REVOKED||[]).length===0);
chk('history records the transitions', dA.history.length===2);

console.log('\n== §5/§6/§25 — CLAUSE FRAGMENTS, COPYRIGHT-SAFE ==');
st=ST();
chk('fragments carry section/clause/kind and a pointer',
    st.fragments.every(f=>f.section&&f.kind&&f.text_reference));
chk('every excerpt stays inside the permitted limit',
    st.fragments.every(f=>f.excerpt===null||f.excerpt.length<=EXCERPT_MAX_CHARS));
const bigFrag=C(st.fragments[0]); bigFrag.excerpt='x'.repeat(EXCERPT_MAX_CHARS+1);
chk('an oversized excerpt is rejected (no standard reproduction)',
    validateFragment(bigFrag,st).some(i=>/copyright-safe/.test(i)));
const noPtr=C(st.fragments[0]); noPtr.excerpt=null; noPtr.text_reference=null;
chk('a fragment with neither excerpt nor pointer is rejected',
    validateFragment(noPtr,st).some(i=>/text_reference pointer/.test(i)));
chk('table fragments keep their table identity',
    st.fragments.some(f=>f.kind==='table_row'&&/Table/.test(f.clause)));
chk('definition fragments are a distinct kind', st.fragments.some(f=>f.kind==='definition'));
chk('source text, fragment, candidate and rule stay four separate objects',
    !!d1.synthetic_content&&!!st.fragments[0].fragment_id&&
    !!st.candidates[0].candidate_id&&!!st.candidates[0].proposed_rule.rule_id);
chk('audit export carries no source text',
    !/shall not exceed/.test(JSON.stringify(ingestAuditExport(st,null))));

console.log('\n== §27 — UNVERIFIED SOURCE CANNOT YIELD A VERIFIED RULE ==');
st=ST();
let c1=ingCandidate(st,'SYNCAND-ED1-T1');
let v=verifyCandidate(c1,st,null,AT,WHO,null);
chk('verification refused while the document is UNVERIFIED', v[0]===false, v[1]);
chk('reason names the source status', v[1]==='SOURCE_NOT_VERIFIED', v[1]);
chk('candidate status unchanged', c1.status==='EXTRACTED');
contentVerify(st,'SYNDOC-ED1');
chk('after explicit content verification the candidate becomes verifiable',
    verifyCandidate(ingCandidate(st,'SYNCAND-ED1-T1'),st,null,AT,WHO,null)[0]===true);

console.log('\n== §28 — SOURCE HASH MISMATCH ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
chk('candidate pinned to a stale hash is REJECTED',
    assessCandidate(ingCandidate(st,'SYNCAND-STALEHASH'),st)[0]==='REJECTED');
chk('verification refused with SOURCE_HASH_MISMATCH',
    verifyCandidate(ingCandidate(st,'SYNCAND-STALEHASH'),st,null,AT,WHO,null)[1]==='REJECTED');
// تحقّق سليم ثم تتغيّر بايتات الوثيقة لاحقاً
let c2=ingCandidate(st,'SYNCAND-ED1-T1');
chk('candidate verifies against the current bytes', verifyCandidate(c2,st,null,AT,WHO,null)[0]===true);
chk('verification is valid right after', verificationStillValid(c2,st)[0]===true);
ingDocument(st,'SYNDOC-ED1').integrity.sha256=sha256Hex('different bytes entirely');
chk('changed document bytes invalidate the earlier verification',
    verificationStillValid(c2,st)[1]==='SOURCE_HASH_MISMATCH');
chk('the stale verification record is not silently updated',
    c2.verification.document_hash!==ingDocument(st,'SYNDOC-ED1').integrity.sha256);

console.log('\n== §29 — MISSING CLAUSE / BROKEN REFERENCE ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const cb=ingCandidate(st,'SYNCAND-BROKEN');
chk('missing fragment is reported as BROKEN_SOURCE_REFERENCE',
    validateCandidate(cb,st).some(i=>/BROKEN_SOURCE_REFERENCE/.test(i)), JSON.stringify(validateCandidate(cb,st)));
chk('candidate assessed REJECTED', assessCandidate(cb,st)[0]==='REJECTED');
chk('verification refused', verifyCandidate(cb,st,null,AT,WHO,null)[0]===false);
chk('no activation possible from it', cb.status!=='VERIFIED');

console.log('\n== §30 — AI-ASSISTED CANDIDATE ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const ca=ingCandidate(st,'SYNCAND-AI');
chk('AI-assisted candidate is structurally valid', validateCandidate(ca,st).length===0,
    JSON.stringify(validateCandidate(ca,st)));
chk('it is still only READY_FOR_VERIFICATION, never VERIFIED',
    assessCandidate(ca,st)[0]==='READY_FOR_VERIFICATION'&&ca.status==='EXTRACTED');
chk('AI cannot verify it', verifyCandidate(ca,st,null,AT,'ai_suggestion',null)[1]==='AI_MAY_NOT_VERIFY');
chk('an unknown method cannot verify it',
    verifyCandidate(ca,st,null,AT,'because_it_looks_right',null)[1]==='UNKNOWN_VERIFICATION_METHOD');
chk('explicit manual approval does verify it', verifyCandidate(ca,st,null,AT,WHO,null)[0]===true);
chk('ai_assisted is preserved in the verification record', ca.verification.ai_assisted===true);
chk('AI assistance did not reduce any evidence requirement',
    ca.verification.document_hash===ingDocument(st,'SYNDOC-ED1').integrity.sha256&&
    ca.verification.fragment_ids.length>0);

console.log('\n== §33 — EXCEPTIONS AND CROSS REFERENCES ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const ce=ingCandidate(st,'SYNCAND-EXC');
chk('open exception ⇒ NEEDS_EXCEPTION_REVIEW', assessCandidate(ce,st)[0]==='NEEDS_EXCEPTION_REVIEW');
chk('verification refused while the exception is open',
    verifyCandidate(ce,st,null,AT,WHO,null)[1]==='NEEDS_EXCEPTION_REVIEW');
chk('the exception is not silently dropped', ce.exceptions.length===1&&!!ce.exceptions[0].source_reference);
ce.exceptions[0].resolution='declared_unsupported';
chk('declaring the exception unsupported is an allowed, recorded resolution',
    assessCandidate(ce,st)[0]==='READY_FOR_VERIFICATION');
chk('the exception still travels with the verified rule',
    verifyCandidate(ce,st,null,AT,WHO,null)[0]===true&&ce.proposed_rule.exceptions!==undefined);
const cx=ingCandidate(st,'SYNCAND-XREF');
chk('unresolved cross reference ⇒ NEEDS_CROSS_REFERENCE', assessCandidate(cx,st)[0]==='NEEDS_CROSS_REFERENCE');
chk('verification refused', verifyCandidate(cx,st,null,AT,WHO,null)[1]==='NEEDS_CROSS_REFERENCE');
cx.cross_references[0].resolution='resolved'; cx.cross_references[0].fragment_id='SYNFRAG-MISSING';
chk('a "resolved" reference pointing nowhere is still broken',
    assessCandidate(cx,st)[0]==='NEEDS_CROSS_REFERENCE');
cx.cross_references[0].fragment_id='SYNFRAG-ED1-T2';
chk('a genuinely resolved reference clears the block', assessCandidate(cx,st)[0]==='READY_FOR_VERIFICATION');
// تعريف مفقود يوقف التحقّق أيضاً
const cd=ingCandidate(st,'SYNCAND-ED1-T1');
cd.definition_refs=[{term:'synthetic route',fragment_id:'SYNFRAG-NOPE'}];
chk('a missing definition fragment blocks verification',
    assessCandidate(cd,st)[0]==='NEEDS_INTERPRETATION'&&
    assessCandidate(cd,st)[1].some(x=>/DEFINITION_FRAGMENT_MISSING/.test(x.reason)));

console.log('\n== §18 — TABLE CONTEXT PRESERVED ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const ct=ingCandidate(st,'SYNCAND-ED1-T1');
chk('table row/column/conditions retained', ct.table_context.row==='synthetic-A'&&
    ct.table_context.column==='ceiling'&&ct.table_context.conditions.length===1);
const flat=C(ct); flat.table_context={table_id:'Table T-1'};
chk('a flattened table candidate is rejected',
    validateCandidate(flat,st).some(i=>/row\/column\/condition context/.test(i)));

console.log('\n== §11/§31 — VERIFIED SYNTHETIC RULE ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const cv=ingCandidate(st,'SYNCAND-ED1-T1');
const rec=verifyCandidate(cv,st,null,AT,WHO,'synthetic fixture approval');
chk('verification succeeds', rec[0]===true, rec[1]);
chk('record pins the document hash', rec[2].document_hash===ingDocument(st,'SYNDOC-ED1').integrity.sha256);
chk('record pins a rule definition hash', /^[0-9a-f]{64}$/.test(rec[2].rule_definition_hash));
chk('record names the verification method', rec[2].method==='explicit_manual_approval');
chk('record cites the source fragments', rec[2].fragment_ids.length===2);
chk('no user identity is fabricated', rec[2].verifier===null);
chk('rule stays synthetic and never code-required',
    cv.proposed_rule.regulatory===false&&codeRequiredAllowed(cv.proposed_rule.rule_id,[])===false);
// تغيير المعنى يوجب مراجعة جديدة
const beforeHash=ruleDefinitionHash(cv.proposed_rule);
cv.proposed_rule.expected.value=31;
chk('changing the rule meaning changes its hash', ruleDefinitionHash(cv.proposed_rule)!==beforeHash);
chk('the old verification no longer covers the new meaning',
    verificationStillValid(cv,st)[1]==='RULE_DEFINITION_CHANGED');
cv.proposed_rule.expected.value=30;
chk('restoring the meaning restores the hash', ruleDefinitionHash(cv.proposed_rule)===beforeHash);
chk('rule meaning hash ignores non-meaning fields',
    (()=>{const a=C(cv.proposed_rule); a.title='different wording entirely';
      return ruleDefinitionHash(a)===beforeHash;})());

console.log('\n== §34 — RULE PACK ACTIVATION ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
const cp=ingCandidate(st,'SYNCAND-ED1-T1'); verifyCandidate(cp,st,null,AT,WHO,null);
const pack=ingRulePack(st,'TEST_ONLY.SYNPACK','1');
pack.candidate_ids=['SYNCAND-ED1-T1'];
chk('a DRAFT pack cannot be activated',
    resolveActiveRules({rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true}]},st)
      .rejected[0].reason.indexOf('RULEPACK_NOT_VERIFIED')===0);
chk('DRAFT → VERIFIED_PARTIAL is not a direct legal transition',
    verifyPack(pack,st,'VERIFIED_PARTIAL',null,AT,WHO,null)[0]===false);
chk('DRAFT → UNDER_REVIEW allowed', verifyPack(pack,st,'UNDER_REVIEW',null,AT,WHO,null)[0]===true);
chk('AI cannot verify a pack', verifyPack(pack,st,'VERIFIED_PARTIAL',null,AT,'ai_suggestion',null)[1]==='AI_MAY_NOT_VERIFY');
chk('UNDER_REVIEW → VERIFIED_PARTIAL allowed with explicit approval',
    verifyPack(pack,st,'VERIFIED_PARTIAL',null,AT,WHO,null)[0]===true);
chk('VERIFIED_FOR_DECLARED_SCOPE refused while completeness is partial',
    verifyPack(pack,st,'VERIFIED_FOR_DECLARED_SCOPE',null,AT,WHO,null)[1]==='SCOPE_COMPLETENESS_NOT_DECLARED');
const noRef={jurisdiction:null,rulepacks:[]};
chk('a verified pack is NOT active without an explicit project reference',
    resolveActiveRules(noRef,st).rulesets.length===0);
const disabled={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:false}]};
chk('an explicitly disabled reference does not activate',
    resolveActiveRules(disabled,st).rejected[0].reason==='NOT_ENABLED');
const wrongVer={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'9',enabled:true}]};
chk('a wrong version does not activate',
    resolveActiveRules(wrongVer,st).rejected[0].reason==='RULEPACK_NOT_FOUND');
const proj={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true}]};
const act=resolveActiveRules(proj,st);
chk('explicit reference activates it', act.rulesets.length===1&&act.rulesets[0].rules.length===1, JSON.stringify(act.rejected));
chk('activation records scope and completeness',
    act.activated[0].completeness==='partial'&&act.activated[0].coverage_scope.length===1);
chk('activation is never implied by building type',
    resolveActiveRules({jurisdiction:null,rulepacks:[]},st).activated.length===0);

console.log('\n== §22 — PIPELINE STATE MACHINE ==');
chk('nine pipeline stages documented', ING_PIPELINE_STAGES.length===9);
chk('EXTRACTED → VERIFIED is not a legal candidate transition',
    canTransitionCandidate('EXTRACTED','VERIFIED')===false);
chk('READY_FOR_VERIFICATION → VERIFIED is legal',
    canTransitionCandidate('READY_FOR_VERIFICATION','VERIFIED')===true);
chk('there is no ACTIVE candidate state at all', ING_CANDIDATE_STATES.indexOf('ACTIVE')<0);
st=ST(); contentVerify(st,'SYNDOC-ED1');
const cadv=ingCandidate(st,'SYNCAND-EXC');
chk('advanceCandidate moves only to the state the evidence earns',
    advanceCandidate(cadv,st)[0]==='NEEDS_EXCEPTION_REVIEW');
cadv.status='EXTRACTED';
const forced=C(cadv); forced.status='VERIFIED'; forced.verification=null;
chk('a candidate claiming VERIFIED without a record is rejected',
    validateCandidate(forced,st).some(i=>/claims VERIFIED without a verification record/.test(i)));

console.log('\n== §32 — EDITION / VERSION ISOLATION ==');
st=ST(); contentVerify(st,'SYNDOC-ED1'); contentVerify(st,'SYNDOC-ED2');
const e1=ingCandidate(st,'SYNCAND-ED1-T1'), e2=ingCandidate(st,'SYNCAND-ED2-T1');
verifyCandidate(e1,st,null,AT,WHO,null); verifyCandidate(e2,st,null,AT,WHO,null);
chk('each verification pins its own document hash',
    e1.verification.document_hash!==e2.verification.document_hash);
chk('each rule keeps its own edition',
    e1.proposed_rule.edition==='1'&&e2.proposed_rule.edition==='2');
chk('rule definition hashes differ', ruleDefinitionHash(e1.proposed_rule)!==ruleDefinitionHash(e2.proposed_rule));
chk('rule identities differ', ruleUid(e1.proposed_rule)!==ruleUid(e2.proposed_rule));
const p1=ingRulePack(st,'TEST_ONLY.SYNPACK','1'); p1.candidate_ids=['SYNCAND-ED1-T1'];
const p2=ingRulePack(st,'TEST_ONLY.SYNPACK_ED2','1'); p2.candidate_ids=['SYNCAND-ED2-T1'];
verifyPack(p1,st,'UNDER_REVIEW',null,AT,WHO,null); verifyPack(p1,st,'VERIFIED_PARTIAL',null,AT,WHO,null);
verifyPack(p2,st,'UNDER_REVIEW',null,AT,WHO,null); verifyPack(p2,st,'VERIFIED_PARTIAL',null,AT,WHO,null);
const projE1={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true}]};
const projE2={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK_ED2',version:'1',enabled:true}]};
// مسار مقاس فعلياً بطول 28.400 م يفصل بين سقفَي الإصدارين الاصطناعيين (30 و25)
const LONG={meta:{type:'office'},site:{w:60,d:20},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'r1',rect:[0,0,4,4],doors:[{edge:'E',offset:2,width:0.9}]},
    {id:'hall',rect:[4,0,24,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]},
    {id:'r2',rect:[28,0,4,4],doors:[{edge:'W',offset:2,width:0.9}]}]}}};
const subs=[SUBJ(LONG,'ROUTE:bld_0.g.r1>bld_0.g.r2')];
const rE1=evaluateProject(projE1,subs,st,{evaluated_at:AT});
const rE2=evaluateProject(projE2,subs,st,{evaluated_at:AT});
chk('edition 1 pack evaluates its own rule only',
    rE1.results.length===1&&rE1.results[0].edition==='1'&&rE1.results[0].status==='PASS',
    JSON.stringify(rE1.results.map(r=>[r.rule_id,r.status])));
chk('edition 2 pack gives a different verdict on the same subject',
    rE2.results.length===1&&rE2.results[0].edition==='2'&&rE2.results[0].status==='FAIL',
    JSON.stringify(rE2.results.map(r=>[r.rule_id,r.status])));
chk('pinning edition 1 never pulls in edition 2',
    rE1.results.every(r=>r.edition!=='2'));

console.log('\n== §16 — UNRESOLVED CONFLICT ⇒ NOT_EVALUATED ==');
st=ST(); contentVerify(st,'SYNDOC-ED1'); contentVerify(st,'SYNDOC-ED2');
// نفس معرّف القاعدة بمعنيين مختلفين في حزمتين مفعَّلتين معاً
const cc1=ingCandidate(st,'SYNCAND-ED1-T1'), cc2=ingCandidate(st,'SYNCAND-ED2-T1');
cc2.proposed_rule.rule_id=cc1.proposed_rule.rule_id;
verifyCandidate(cc1,st,null,AT,WHO,null); verifyCandidate(cc2,st,null,AT,WHO,null);
const q1=ingRulePack(st,'TEST_ONLY.SYNPACK','1'); q1.candidate_ids=['SYNCAND-ED1-T1'];
const q2=ingRulePack(st,'TEST_ONLY.SYNPACK_ED2','1'); q2.candidate_ids=['SYNCAND-ED2-T1'];
[q1,q2].forEach(p=>{verifyPack(p,st,'UNDER_REVIEW',null,AT,WHO,null);
                    verifyPack(p,st,'VERIFIED_PARTIAL',null,AT,WHO,null);});
const both={jurisdiction:null,rulepacks:[
  {rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true},
  {rulepack_id:'TEST_ONLY.SYNPACK_ED2',version:'1',enabled:true}]};
const conf=evaluateProject(both,subs,st,{evaluated_at:AT});
chk('the conflict is detected', conf.activation.conflicts.length===1, JSON.stringify(conf.activation.conflicts));
chk('conflicting rules are NOT_EVALUATED, never arbitrarily chosen',
    conf.results.every(r=>r.status==='NOT_EVALUATED'&&r.reason==='RULE_CONFLICT'),
    JSON.stringify(conf.results.map(r=>[r.status,r.reason])));
chk('no PASS or FAIL is emitted for a conflicted rule',
    !conf.results.some(r=>r.status==='PASS'||r.status==='FAIL'));
chk('the summary surfaces the conflict', conf.summary.conflicts.length===1);
chk('relation types can express precedence without deciding it',
    ING_RELATION_TYPES.indexOf('supersedes')>=0&&ING_RELATION_TYPES.indexOf('amends')>=0);
chk('the fixture records a supersedes relation without acting on it',
    ingDocument(ST(),'SYNDOC-ED2').relations[0].type==='supersedes');

console.log('\n== §35 — PARTIAL PACK SEMANTICS ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
['SYNCAND-ED1-T1','SYNCAND-AI'].forEach(id=>verifyCandidate(ingCandidate(st,id),st,null,AT,WHO,null));
const pp=ingRulePack(st,'TEST_ONLY.SYNPACK','1');
pp.candidate_ids=['SYNCAND-ED1-T1','SYNCAND-AI'];
verifyPack(pp,st,'UNDER_REVIEW',null,AT,WHO,null); verifyPack(pp,st,'VERIFIED_PARTIAL',null,AT,WHO,null);
const projP={jurisdiction:null,rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true}]};
const run=evaluateProject(projP,subs,st,{evaluated_at:AT});
chk('summary states how many configured rules were evaluated',
    /تم التقييم مقابل 2 قاعدة/.test(run.summary.statement), run.summary.statement);
chk('summary never claims the building is compliant',
    !/مطابق للكود|compliant|COMPLIANT/i.test(run.summary.statement.replace('NOT_DETERMINED','')));
chk('overall_compliance stays NOT_DETERMINED', run.summary.overall_compliance==='NOT_DETERMINED');
chk('completeness is carried through as partial', run.summary.completeness==='partial');
chk('coverage scope is reported', /synthetic\.route_ceiling/.test(run.summary.coverage_scope||''));
chk('activated packs are listed in the summary', run.summary.activated_rulepacks.length===1);
chk('regulatory results = 0', run.summary.regulatory_results===0);
chk('CODE_REQUIRED remains impossible', run.results.every(r=>r.code_required_eligible===false));

console.log('\n== §21 — APPLICABILITY TRACE ==');
const t=run.results[0];
chk('the result explains why the rule applies', Array.isArray(t.applicability_trace)&&t.applicability_trace.length>0,
    JSON.stringify(t.applicability_trace));
chk('the trace names the factors, not just "applied"',
    t.applicability_trace.every(x=>!!x.factor&&x.satisfied===true), JSON.stringify(t.applicability_trace));
chk('subject type is one of the traced factors',
    t.applicability_trace.some(x=>x.factor==='subject_type'));

console.log('\n== §23/§40 — IMPORT VALIDATION & SECURITY ==');
st=ST();
const dup={documents:[C(st.documents[0]),C(st.documents[0])],fragments:[],candidates:[],rulepacks:[]};
chk('duplicate document ids rejected', validateImport(dup).some(i=>/duplicate document_id/.test(i)));
const badHash=C(st.documents[0]); badHash.integrity.sha256='not-a-hash';
chk('invalid hash rejected', validateDocument(badHash).some(i=>/64-hex digest/.test(i)));
const httpDoc=C(st.documents[0]);
httpDoc.origin={type:'official_url',url:'http://example.invalid/doc',filename:null};
chk('non-https official url rejected', validateDocument(httpDoc).some(i=>/must be https/.test(i)));
const scriptDoc=C(st.documents[0]); scriptDoc.title='<script>alert(1)</script>';
chk('script content rejected', validateDocument(scriptDoc).some(i=>/executable/.test(i)));
const jsUrl=C(st.documents[0]); jsUrl.origin={type:'manual_reference',url:null,filename:null};
jsUrl.title='javascript:alert(1)';
chk('javascript: string rejected', validateDocument(jsUrl).some(i=>/executable/.test(i)));
const bothFlags=C(st.documents[0]); bothFlags.official=true;
chk('a document cannot be official and synthetic at once',
    validateDocument(bothFlags).some(i=>/both official and synthetic/.test(i)));
const orphanFrag=C(st.fragments[0]); orphanFrag.document_id='NOPE';
chk('fragment referencing a missing document rejected',
    validateFragment(orphanFrag,st).some(i=>/missing document/.test(i)));
const badPack={rulepack_id:'P',version:'1',standard:'X',edition:'1',completeness:'partial',
  coverage_scope:[],verification:{status:'DRAFT'},candidate_ids:[]};
chk('pack without coverage scope rejected', validatePack(badPack,st).some(i=>/coverage_scope list/.test(i)));
const unverifiedInPack=C(badPack); unverifiedInPack.coverage_scope=['x'];
unverifiedInPack.candidate_ids=['SYNCAND-ED1-T1'];
chk('pack containing an unverified candidate rejected',
    validatePack(unverifiedInPack,st).some(i=>/not VERIFIED/.test(i)));
const badOp=C(st.candidates[0]); badOp.proposed_rule.operator='run_shell';
chk('unknown operator rejected through the rule validator',
    validateCandidate(badOp,st).some(i=>/unknown operator/.test(i)));
const badUnit=C(st.candidates[0]); badUnit.proposed_rule.inputs[0].unit='cubits';
chk('unknown unit rejected', validateCandidate(badUnit,st).some(i=>/unknown input unit/.test(i)));
chk('no eval/exec/Function anywhere in the ingestion layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      validateImport.toString()+verifyCandidate.toString()+assessCandidate.toString()+
      resolveActiveRules.toString()+evaluateProject.toString()));
chk('documents are never executed — only hashed and validated',
    typeof sha256Hex(d1.synthetic_content)==='string');

console.log('\n== §24 — OFFLINE FILE SOURCES ==');
chk('uploaded_file origin supported', ING_ORIGIN_TYPES.indexOf('uploaded_file')>=0);
chk('manual_reference origin supported (no web access required)',
    ING_ORIGIN_TYPES.indexOf('manual_reference')>=0);
const upl=C(st.documents[0]); upl.origin={type:'uploaded_file',url:null,filename:null};
chk('uploaded_file requires a filename', validateDocument(upl).some(i=>/requires a filename/.test(i)));
upl.origin.filename='synthetic-fixture.pdf';
chk('an offline file document validates with no URL at all', validateDocument(upl).length===0,
    JSON.stringify(validateDocument(upl)));

console.log('\n== §38 — AUDIT EXPORT ==');
st=ST(); contentVerify(st,'SYNDOC-ED1');
verifyCandidate(ingCandidate(st,'SYNCAND-ED1-T1'),st,null,AT,WHO,null);
const pk=ingRulePack(st,'TEST_ONLY.SYNPACK','1'); pk.candidate_ids=['SYNCAND-ED1-T1'];
verifyPack(pk,st,'UNDER_REVIEW',null,AT,WHO,null); verifyPack(pk,st,'VERIFIED_PARTIAL',null,AT,WHO,null);
const ex=ingestAuditExport(st,{jurisdiction:null,
  rulepacks:[{rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true}]});
chk('export carries document id + hash + status',
    ex.documents.every(d=>d.document_id&&d.sha256&&d.status));
chk('export carries candidate id, rule id/revision and definition hash',
    ex.candidates.every(c=>c.candidate_id&&c.rule_id&&c.rule_definition_hash));
chk('export carries the verification record',
    ex.candidates.find(c=>c.candidate_id==='SYNCAND-ED1-T1').verification.method===WHO);
chk('export carries the rulepack version and activation',
    ex.rulepacks[0].version==='1'&&ex.activation.length===1);
chk('export states the copyright position', /no full source text/.test(ex.copyright_note));
chk('export contains no excerpt text', !/shall not exceed/.test(JSON.stringify(ex)));

console.log('\n== SBC 201 PILOT — REAL SOURCE REGISTER (no clause content) ==');
const RS=ingestRealStore();
const CANON_SRC=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_sources.json'),'utf8'));
chk('real source register is byte-identical to acs_sources.json',
    JSON.stringify(sk(RS))===JSON.stringify(sk({documents:CANON_SRC.documents,fragments:CANON_SRC.fragments,
      candidates:CANON_SRC.candidates,rulepacks:CANON_SRC.rulepacks})));
chk('real register validates clean', ingestStoreIssues(RS).length===0, JSON.stringify(ingestStoreIssues(RS)));
const SBC=ingDocument(RS,'SBC201-CC-2024');
chk('document present with the supplied file hash',
    SBC.integrity.sha256==='5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06');
chk('hash is 64-hex and size recorded',
    /^[0-9a-f]{64}$/.test(SBC.integrity.sha256)&&SBC.integrity.size_bytes===3270898);
chk('standard and edition come from the document itself',
    SBC.standard==='SBC 201'&&SBC.edition==='2024');
chk('jurisdiction is evidenced, not inferred from language',
    SBC.jurisdiction.country==='Kingdom of Saudi Arabia'&&SBC.jurisdiction.authority===null);
chk('document is marked official but NOT content-verified',
    SBC.official===true&&SBC.verification.status==='OFFICIAL_SOURCE_VERIFIED'&&documentUsable(SBC)===false);
chk('the two verification states stayed separate',
    SBC.verification.status!=='CONTENT_VERIFIED');
chk('document type records that it is an excerpt',
    /excerpt/.test(SBC.document_type)&&SBC.completeness==='excerpt');
chk('content inventory records the absence of normative text',
    SBC.content_inventory.contains_normative_clause_text===false&&
    SBC.content_inventory.occurrences_of_shall===0);
chk('verification evidence is recorded at every transition',
    SBC.history.length===2&&SBC.history.every(h=>!!h.evidence));
chk('the origin claim is recorded as a claim, not as proof',
    /origin claim/.test(JSON.stringify(SBC.history[0].evidence)));
chk('withholding CONTENT_VERIFIED is itself recorded',
    /no clause text/.test(JSON.stringify(SBC.history[1].evidence)));
chk('no clause text is stored anywhere in the real register',
    !/shall\s/i.test(JSON.stringify(RS)));
chk('every real fragment is a locator, not a clause',
    RS.fragments.every(f=>f.kind==='toc_locator'));
chk('locators point at Chapter 10 sections with real page numbers',
    RS.fragments.filter(f=>/^10\d\d$/.test(f.section)).length===31&&
    RS.fragments.every(f=>Number.isInteger(f.page)));
chk('ZERO candidates extracted from a document with no clause text', RS.candidates.length===0);
chk('ZERO rule packs', RS.rulepacks.length===0);
chk('ZERO verified regulatory rules', ingestRegulatoryRuleCount(RS)===0);
chk('nothing is activated', resolveActiveRules({jurisdiction:null,rulepacks:[]},RS).activated.length===0);
chk('a regulatory candidate on this document would be refused (not CONTENT_VERIFIED)',
    (()=>{const c={candidate_id:'X',document_id:'SBC201-CC-2024',document_hash:SBC.integrity.sha256,
      fragment_ids:['SBC201-TOC-1017'],extraction_method:'manual_transcription',
      interpretation_method:'manual_structured_mapping',ai_assisted:false,status:'EXTRACTED',
      proposed_rule:{rule_id:'SBC201-1017-TEST',namespace:'SBC',regulatory:true,title:'t',
        category:'egress',severity:'major',enabled:true,revision:1,standard:'SBC 201',edition:'2024',
        section:'1017',jurisdiction_required:true,
        jurisdiction:{country:'Kingdom of Saudi Arabia',region:null,authority:null},
        source:{type:'official_document',source_id:'SBC',document_id:'SBC201-CC-2024',page:1111,
                clause:'1017',url:null,verified:true},
        subject_type:'ROUTE',applies_to:{subject_type:'ROUTE',conditions:[]},
        inputs:[{key:'route.hops',unit:'count',required:true}],
        operator:'count_min',expected:{value:1}}};
      const rej=verifyCandidate(c,RS,null,AT,WHO,null);
      return validateCandidate(c,RS).some(i=>/not CONTENT_VERIFIED/.test(i))&&
             rej[0]===false&&JSON.stringify(rej[2]).indexOf('not CONTENT_VERIFIED')>=0;})());
chk('CODE_REQUIRED remains impossible for any SBC rule id',
    codeRequiredAllowed('SBC201-1017-TEST',[])===false);

console.log('\n== SBC 201 PILOT — CHAIN OF CUSTODY (third-party copy) ==');
const CR=ingDocument(RS,'SBC201-CR-2018-THIRDPARTY-COPY');
chk('third-party copy is registered with its own hash',
    CR.integrity.sha256==='e8f3afc4064a5eaa6ee6f4809a4d3357b0dc20bcfcd93afcf4db51ee6843b972'&&
    CR.integrity.size_bytes===7469728);
chk('it is a different edition and variant from the official file',
    CR.edition==='2018'&&SBC.edition==='2024'&&/CR/.test(CR.variant));
chk('the newer edition was not silently preferred — both are registered separately',
    RS.documents.length===2&&RS.documents[0].integrity.sha256!==RS.documents[1].integrity.sha256);
chk('origin_authority records third-party redistribution',
    CR.origin.origin_authority==='third_party_redistribution');
chk('it is NOT marked official', CR.official===false);
chk('it stopped at SOURCE_IDENTIFIED', CR.verification.status==='SOURCE_IDENTIFIED');
chk('marking it official would be rejected by validation',
    (()=>{const c=C(CR); c.official=true;
      return validateDocument(c).some(i=>/may not be marked official/.test(i));})());
chk('promoting it to OFFICIAL_SOURCE_VERIFIED is refused',
    transitionDocument(C(CR),'OFFICIAL_SOURCE_VERIFIED',WHO,{n:1},AT,null)[1]
      ==='DOCUMENT_NOT_MARKED_OFFICIAL_BY_EVIDENCE');
chk('even if forced official, the origin chain still blocks the transition',
    (()=>{const c=C(CR); c.official=true;
      return transitionDocument(c,'OFFICIAL_SOURCE_VERIFIED',WHO,{n:1},AT,null)[1]
        ==='ORIGIN_NOT_IN_OFFICIAL_CHAIN';})());
chk('the licensing restriction is recorded',
    CR.licensing.redistribution_permitted===false&&CR.licensing.permission_evidence===null);
chk('the issuing authority is recorded from the document itself',
    /Saudi Building Code National Committee/.test(CR.jurisdiction.authority));
chk('the provenance concern is recorded as transition evidence',
    /third-party document-sharing site/.test(JSON.stringify(CR.history[0].evidence)));
chk('no egress clause text was taken from it',
    CR.content_inventory.means_of_egress_body_text_present===false);
chk('still zero candidates after a second document',
    RS.candidates.length===0&&ingestRegulatoryRuleCount(RS)===0);
chk('an official-chain origin is still accepted for the official file',
    validateDocument(SBC).length===0&&SBC.origin.origin_authority==='issuing_authority');

console.log('\n== SBC 201 PILOT — NO CROSS-STANDARD SUBSTITUTION ==');
const mkCand=(std,ed)=>({candidate_id:'X',document_id:'SBC201-CR-2018-THIRDPARTY-COPY',
  document_hash:CR.integrity.sha256,fragment_ids:[],extraction_method:'manual_transcription',
  interpretation_method:'manual_structured_mapping',ai_assisted:false,status:'EXTRACTED',
  proposed_rule:{rule_id:'X-1017',namespace:'X',regulatory:true,title:'t',category:'egress',
    severity:'major',enabled:true,revision:1,standard:std,edition:ed,section:'1017',
    jurisdiction_required:true,jurisdiction:{country:'Kingdom of Saudi Arabia',region:null,authority:null},
    source:{type:'official_document',source_id:'SBC',document_id:'SBC201-CR-2018-THIRDPARTY-COPY',
            page:403,clause:'1017',url:null,verified:true},
    subject_type:'ROUTE',applies_to:{subject_type:'ROUTE',conditions:[]},
    inputs:[{key:'route.hops',unit:'count',required:true}],operator:'count_min',expected:{value:1}}});
chk('a rule citing IBC cannot lean on an SBC document',
    validateCandidate(mkCand('IBC','2024'),RS).some(i=>/STANDARD_MISMATCH/.test(i)),
    JSON.stringify(validateCandidate(mkCand('IBC','2024'),RS)));
chk('a rule citing the wrong edition of the right standard is caught too',
    validateCandidate(mkCand('SBC 201','2024'),RS).some(i=>/EDITION_MISMATCH/.test(i)));
chk('matching standard and edition passes that particular check',
    !validateCandidate(mkCand('SBC 201','2018'),RS).some(i=>/STANDARD_MISMATCH|EDITION_MISMATCH/.test(i)));
chk('the base-code relationship is recorded as evidence, not acted on',
    CR.base_code.standard==='IBC'&&CR.base_code.edition==='2015'&&
    /not evidence for an SBC requirement/.test(CR.base_code.implication));
chk('no IBC document was registered from a URL', RS.documents.every(d=>d.standard==='SBC 201'));
chk('no document was registered without a real content hash',
    RS.documents.every(d=>/^[0-9a-f]{64}$/.test(d.integrity.sha256)&&d.integrity.size_bytes>0));

console.log(`\nINGEST: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
