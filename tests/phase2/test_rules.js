/* ======================================================================
   المرحلة 2 — اختبارات أساس محرّك قواعد الكود.
   بنية فقط: كل القواعد المستعملة هنا اصطناعية (regulatory=false).
   لا قيمة تنظيمية واحدة تُدَّعى في أي موضع.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const CTX={evaluated_at:'T0'};

function villaS(){ const b=C(FX.villa); b.wall_t=0.20;
  [['f','corridor_f'],['g','corridor']].forEach(([t,id])=>{
    const r=b.floors[t].rooms.find(r=>r.id===id);
    Object.assign(r.objects[0],{risers:16,tread_m:0.28,riser_m:0.20}); });
  return b; }
const S=(b,sid)=>resolveSubject(b,buildRelationships(b,'bld_0'),sid,'bld_0');
const EV=(b,ruleId,sid,ctx,rsId)=>{ const p=ruleById(ruleId,[],rsId);
  return evaluateRule(p[1],S(b,sid),ctx||CTX,p[0],[]); };

console.log('\n== §46 — NO REGULATORY CONTENT ==');
chk('regulatory rule count = 0', regulatoryRuleCount([])===0, regulatoryRuleCount([]));
chk('every shipped rule is synthetic',
    allRules([]).every(p=>p[1].regulatory===false&&p[1].namespace==='TEST_ONLY'));
chk('every shipped rule uses a synthetic_test source',
    allRules([]).every(p=>(p[1].source||{}).type==='synthetic_test'));
chk('registry definition issues = none', ruleIssues([]).length===0, JSON.stringify(ruleIssues([]).slice(0,3)));
const REGTXT=JSON.stringify(ACS_RULES_REGISTRY.rulesets);
chk('no SBC/IBC/NFPA/ADA/Civil-Defense value encoded in any rule',
    !/SBC|IBC|NFPA|ADA|civil[_ ]?defense/i.test(REGTXT), REGTXT.slice(0,80));
chk('source registry entries are NOT_LOADED and unverified',
    ruleSources().filter(s=>s.source_id!=='synthetic_test')
      .every(s=>s.status==='NOT_LOADED'&&s.verified===false&&s.edition===null));
chk('no edition is fabricated for any real standard',
    ruleSources().every(s=>s.edition===null));

console.log('\n== §42 — SINGLE CANONICAL REGISTRY (drift test) ==');
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_rules.json'),'utf8'));
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);
chk('embedded browser registry is byte-identical to acs_rules.json',
    JSON.stringify(sk(ACS_RULES_REGISTRY))===JSON.stringify(sk(CANON)));
chk('schema version matches', ACS_RULES_REGISTRY.schema===CANON.schema);
chk('engine version matches', RULE_ENGINE_VERSION===CANON.engine_version);
chk('units/operators/contracts come from one source',
    JSON.stringify(sk(RULE_UNITS))===JSON.stringify(sk(CANON.units))&&
    JSON.stringify(sk(RULE_OPERATORS))===JSON.stringify(sk(CANON.operators))&&
    JSON.stringify(sk(RULE_CONTRACTS))===JSON.stringify(sk(CANON.input_contracts)));
chk('rule content is not hand-maintained in two places',
    JSON.stringify(sk(ACS_RULES_REGISTRY.rulesets))===JSON.stringify(sk(CANON.rulesets)));

console.log('\n== §39 — STORAGE SEPARATION ==');
chk('rule library lives outside project data',
    !/\"rulesets\"|\"rule_id\"/.test(JSON.stringify(villaS())));
chk('a project references a ruleset by id/edition only, never embeds it',
    typeof ruleSetById('TEST_ONLY.CORE',[]).ruleset_id==='string');

console.log('\n== §23 — SYNTHETIC PASS (COMPLETE distance) ==');
const vb=villaS();
let r=EV(vb,'TEST_ONLY.NUMERIC_MAX_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('status PASS', r.status==='PASS', r.status+' '+r.reason);
chk('evaluation value is unrounded', r.actual.value>24.9054&&r.actual.value!==24.905, r.actual.value);
chk('display value is the rounded 24.905', r.actual.display_value===24.905, r.actual.display_value);
chk('required exposed with unit', r.required.value===30&&r.required.unit==='m');
chk('applicability APPLICABLE + data_quality COMPLETE',
    r.applicability==='APPLICABLE'&&r.data_quality==='COMPLETE');
chk('rule is synthetic, never code-required',
    r.regulatory===false&&r.code_required_eligible===false);
chk('evidence chain reaches path + measurement',
    r.evidence.some(e=>e.type==='path')&&r.evidence.some(e=>e.type==='measurement'),
    JSON.stringify(r.evidence));
chk('evidence names the rule source', r.evidence[0].type==='rule_source');
chk('rule_uid carries standard|edition|section|id|revision',
    r.rule_uid==='TEST_STANDARD|0|§T.MAX|TEST_ONLY.NUMERIC_MAX_001|r1', r.rule_uid);
chk('engine version recorded', r.engine_version===RULE_ENGINE_VERSION);
chk('evaluated_at comes from context (engine invents no clock)', r.evaluated_at==='T0');

console.log('\n== §24 — SYNTHETIC FAIL ==');
// نفس القاعدة على مسار أطول فعلياً (28.400 م مقاسة) — آلية المقيّم فقط
const LONG={meta:{type:'office'},site:{w:60,d:20},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'r1',rect:[0,0,4,4],doors:[{edge:'E',offset:2,width:0.9}]},
    {id:'hall',rect:[4,0,24,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]},
    {id:'r2',rect:[28,0,4,4],doors:[{edge:'W',offset:2,width:0.9}]}]}}};
let rf=EV(LONG,'TEST_ONLY.EDITION_MAX_001','ROUTE:bld_0.g.r1>bld_0.g.r2',
          {evaluated_at:'T0',edition_pin:{TEST_STANDARD:'2'}},'TEST_ONLY.STD_ED2');
chk('status FAIL against the tighter synthetic edition', rf.status==='FAIL', rf.status+' '+rf.reason);
chk('actual > required, both reported', rf.actual.value>rf.required.value,
    rf.actual.display_value+' vs '+rf.required.display_value);
chk('FAIL still carries full evidence', rf.evidence.length>=3);

console.log('\n== §25 — PARTIAL ⇒ NOT_EVALUATED ==');
const vp=C(FX.villa); vp.wall_t=0.20;            // بلا هندسة درج ⇒ PARTIAL
let rp=EV(vp,'TEST_ONLY.NUMERIC_MAX_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('status NOT_EVALUATED (not PASS, not FAIL)', rp.status==='NOT_EVALUATED', rp.status);
chk('reason INCOMPLETE_DISTANCE_MEASUREMENT', rp.reason==='INCOMPLETE_DISTANCE_MEASUREMENT', rp.reason);
chk('data_quality INCOMPLETE', rp.data_quality==='INCOMPLETE');
chk('no actual/required fabricated', rp.actual===null&&rp.required===null);
chk('quality evidence recorded', rp.evidence.some(e=>e.type==='data_quality'));

console.log('\n== §26 — GEOMETRY_NOT_SUPPORTED ⇒ NOT_EVALUATED ==');
const GP=C(LONG); GP.floors.g.rooms[1].polygon=[[4,0],[28,0],[28,4],[16,6],[4,4]];
let rg=EV(GP,'TEST_ONLY.NUMERIC_MAX_001','ROUTE:bld_0.g.r1>bld_0.g.r2');
chk('status NOT_EVALUATED', rg.status==='NOT_EVALUATED', rg.status);
chk('reason GEOMETRY_NOT_SUPPORTED', rg.reason==='GEOMETRY_NOT_SUPPORTED', rg.reason);
chk('no distance claimed', rg.actual===null);

console.log('\n== §27 — UNKNOWN JURISDICTION ==');
let rj=EV(vb,'TEST_ONLY.JURISDICTION_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('status NOT_EVALUATED', rj.status==='NOT_EVALUATED', rj.status);
chk('reason JURISDICTION_NOT_SET', rj.reason==='JURISDICTION_NOT_SET', rj.reason);
let rj2=EV(vb,'TEST_ONLY.JURISDICTION_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis',
           {evaluated_at:'T0',jurisdiction:{country:'TESTLAND'}});
chk('declared jurisdiction ⇒ evaluated', rj2.status==='PASS', rj2.status+' '+rj2.reason);
let rj3=EV(vb,'TEST_ONLY.JURISDICTION_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis',
           {evaluated_at:'T0',jurisdiction:{country:'OTHERLAND'}});
chk('different jurisdiction ⇒ NOT_APPLICABLE (not FAIL)',
    rj3.status==='NOT_APPLICABLE'&&rj3.reason==='JURISDICTION_MISMATCH', rj3.status+'/'+rj3.reason);
chk('Arabic input never implies a jurisdiction',
    EV(vb,'TEST_ONLY.JURISDICTION_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis',
       {evaluated_at:'T0',request_text:'فيلا دورين في الرياض'}).reason==='JURISDICTION_NOT_SET');

console.log('\n== §28 — EDITION ISOLATION ==');
const e1=EV(LONG,'TEST_ONLY.EDITION_MAX_001','ROUTE:bld_0.g.r1>bld_0.g.r2',
            {evaluated_at:'T0',edition_pin:{TEST_STANDARD:'1'}},'TEST_ONLY.STD_ED1');
const e2=EV(LONG,'TEST_ONLY.EDITION_MAX_001','ROUTE:bld_0.g.r1>bld_0.g.r2',
            {evaluated_at:'T0',edition_pin:{TEST_STANDARD:'2'}},'TEST_ONLY.STD_ED2');
chk('ambiguous rule_id across editions is never silently resolved by the gate',
    codeRequiredAllowed('TEST_ONLY.EDITION_MAX_001',[])===false);
chk('edition 1 pinned ⇒ evaluated under edition 1', e1.edition==='1'&&e1.status==='PASS', e1.edition+'/'+e1.status);
chk('edition 2 pinned ⇒ evaluated under edition 2', e2.edition==='2'&&e2.status==='FAIL', e2.edition+'/'+e2.status);
chk('same rule_id, different identity', e1.rule_uid!==e2.rule_uid, e1.rule_uid+' | '+e2.rule_uid);
// مشروع مثبّت على الإصدار 1 لا يستعمل الإصدار 2 بصمت
const ed2rule=ruleSetById('TEST_ONLY.STD_ED2',[]).rules[0];
const pinned1=evaluateRule(ed2rule,S(LONG,'ROUTE:bld_0.g.r1>bld_0.g.r2'),
  {evaluated_at:'T0',edition_pin:{TEST_STANDARD:'1'}},ruleSetById('TEST_ONLY.STD_ED2',[]),[]);
chk('edition-2 rule under an edition-1 pin ⇒ NOT_APPLICABLE/EDITION_NOT_PINNED',
    pinned1.status==='NOT_APPLICABLE'&&pinned1.reason==='EDITION_NOT_PINNED', pinned1.status+'/'+pinned1.reason);

console.log('\n== §29 — MISSING INPUT ⇒ INSUFFICIENT_DATA ==');
let rm=EV(LONG,'TEST_ONLY.NUMERIC_MIN_001','DOOR:bld_0.g.r1.door_0');
chk('status INSUFFICIENT_DATA', rm.status==='INSUFFICIENT_DATA', rm.status);
chk('reason names the field and why', /MISSING_REQUIRED_INPUT: door.clear_width/.test(rm.reason)&&
    /FIELD_NOT_PRESENT_IN_MODEL/.test(rm.reason), rm.reason);
chk('never PASS, never FAIL', rm.status!=='PASS'&&rm.status!=='FAIL');
chk('width is NOT derived from the door opening width',
    rm.inputs['door.clear_width'].value===null&&LONG.floors.g.rooms[0].doors[0].width===0.9);

console.log('\n== §30 — UNIT CONVERSION ==');
const UW=C(LONG); UW.floors.g.rooms[0].doors[0].clear_width_m=0.95;
let ru=EV(UW,'TEST_ONLY.NUMERIC_MIN_001','DOOR:bld_0.g.r1.door_0');
chk('status PASS (0.95 m vs synthetic 900 mm)', ru.status==='PASS', ru.status+' '+ru.reason);
chk('actual displayed in the rule unit as 950 mm',
    ru.actual.display_value===950&&ru.actual.display_unit==='mm',
    ru.actual.display_value+' '+ru.actual.display_unit);
chk('required displayed as 900 mm', ru.required.display_value===900&&ru.required.display_unit==='mm');
chk('comparison happened in the base unit (m)', Math.abs(ru.actual.value-0.95)<1e-12, ru.actual.value);
const UW2=C(UW); UW2.floors.g.rooms[0].doors[0].clear_width_m=0.85;
chk('0.85 m ⇒ FAIL against the same synthetic floor',
    EV(UW2,'TEST_ONLY.NUMERIC_MIN_001','DOOR:bld_0.g.r1.door_0').status==='FAIL');
chk('mm and m are never compared without conversion',
    unitDim('mm')===unitDim('m')&&toBase(900,'mm')===0.9);
chk('cross-dimension comparison is refused (UNSUPPORTED)',
    _evalPrimitive('numeric_min',5,'m2',{value:1,unit:'m'})[0]===null);

console.log('\n== §31 — PROVENANCE ==');
chk('geometry-inferred input is disclosed as such',
    r.input_provenance['route.walking_distance_m']==='geometry_inference',
    JSON.stringify(r.input_provenance));
chk('inferred data is not promoted to user-confirmed',
    Object.values(r.input_provenance).indexOf('user')<0);
const UW3=C(UW); UW3.floors.g.rooms[0].doors[0].source='user';
chk('a user-stated field is reported as user',
    EV(UW3,'TEST_ONLY.NUMERIC_MIN_001','DOOR:bld_0.g.r1.door_0').input_provenance['door.clear_width']==='user');

console.log('\n== §32 — INVALID RULE DEFINITION ==');
const BAD={rule_id:'FAKE-1',namespace:'FAKE',regulatory:true,title:'regulatory-looking but unproven',
  category:'egress',severity:'info',enabled:true,revision:1,
  standard:'SOME_STANDARD',jurisdiction_required:false,
  jurisdiction:{country:null,region:null,authority:null},
  source:{type:'official_document',source_id:'SOME',document_id:null,page:null,clause:null,url:null,verified:false},
  subject_type:'ROUTE',applies_to:{subject_type:'ROUTE',conditions:[]},
  inputs:[{key:'route.hops',unit:'count',required:true}],
  operator:'count_min',expected:{value:1}};
const rb=evaluateRule(BAD,S(vb,'ROUTE:bld_0.f.bed1>bld_0.g.majlis'),CTX,null,[]);
chk('status INVALID_RULE_DEFINITION', rb.status==='INVALID_RULE_DEFINITION', rb.status);
chk('rule did not execute (no actual/required)', rb.actual===null&&rb.required===null);
chk('missing edition reported', rb.definition_issues.some(i=>/edition/.test(i)), JSON.stringify(rb.definition_issues));
chk('missing section reported', rb.definition_issues.some(i=>/section/.test(i)));
chk('unverified source reported', rb.definition_issues.some(i=>/not verified/.test(i)));
chk('missing document reference reported', rb.definition_issues.some(i=>/document reference/.test(i)));
chk('invalid rule can never be code-required', rb.code_required_eligible===false);

console.log('\n== §33 — CODE_REQUIRED GATE ==');
chk('synthetic rule never opens the gate', codeRequiredAllowed('TEST_ONLY.NUMERIC_MAX_001',[])===false);
chk('unknown rule never opens the gate', codeRequiredAllowed('SBC-999',[])===false);
const GOOD=C(BAD); GOOD.edition='2099'; GOOD.section='9.9'; GOOD.namespace='GATE_TEST';
GOOD.source.document_id='GATE-TEST-DOC'; GOOD.source.verified=true;
const GRS={ruleset_id:'GATE_TEST',ruleset_version:'1',standard:'SOME_STANDARD',edition:'2099',
  completeness:'partial',coverage_scope:'gate probe',regulatory:true,rules:[GOOD]};
chk('valid + verified + regulatory ⇒ gate opens', codeRequiredAllowed('FAKE-1',[GRS])===true,
    JSON.stringify(validateRule(GOOD)));
chk('same rule unverified ⇒ gate closes',
    (()=>{const g=C(GRS); g.rules[0].source.verified=false; return codeRequiredAllowed('FAKE-1',[g]);})()===false);
chk('regulatory rule may not use a synthetic source',
    validateRule(Object.assign(C(GOOD),{source:Object.assign(C(GOOD.source),{type:'synthetic_test'})}))
      .some(i=>/synthetic_test source/.test(i)));
chk('regulatory rule may not live in TEST_ONLY',
    validateRule(Object.assign(C(GOOD),{namespace:'TEST_ONLY'})).some(i=>/TEST_ONLY namespace/.test(i)));

console.log('\n== §7 — APPLICABILITY vs EXISTENCE ==');
const hotel=C(FX.hotel); hotel.wall_t=0.20;
const ra=EV(hotel,'TEST_ONLY.PROGRAM_APPLICABILITY_001','ROUTE:bld_0.t.guest_1@2>bld_0.g.lobby@0',
  {evaluated_at:'T0',subjects:{BUILDING:S(hotel,'BUILDING:bld_0')}});
chk('program matches ⇒ APPLICABLE and evaluated', ra.status==='PASS'&&ra.applicability==='APPLICABLE',
    ra.status+'/'+ra.applicability+'/'+ra.reason);
const rna=EV(vb,'TEST_ONLY.PROGRAM_APPLICABILITY_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis',
  {evaluated_at:'T0',subjects:{BUILDING:S(vb,'BUILDING:bld_0')}});
chk('program differs ⇒ NOT_APPLICABLE (not FAIL)',
    rna.status==='NOT_APPLICABLE'&&/CONDITION_NOT_MET/.test(rna.reason), rna.status+'/'+rna.reason);
const noMeta=C(vb); delete noMeta.meta;
const rid=EV(noMeta,'TEST_ONLY.PROGRAM_APPLICABILITY_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis',
  {evaluated_at:'T0',subjects:{BUILDING:S(noMeta,'BUILDING:bld_0')}});
chk('classification missing ⇒ INSUFFICIENT_DATA (not guessed)',
    rid.status==='INSUFFICIENT_DATA'&&/APPLICABILITY_INPUT_MISSING/.test(rid.reason), rid.status+'/'+rid.reason);
chk('the three outcomes stay distinct',
    new Set([ra.status,rna.status,rid.status]).size===3);
const disabled=C(ruleSetById('TEST_ONLY.CORE',[]).rules[0]); disabled.enabled=false;
chk('disabled rule ⇒ NOT_APPLICABLE/RULE_DISABLED',
    evaluateRule(disabled,S(vb,'ROUTE:bld_0.f.bed1>bld_0.g.majlis'),CTX,null,[]).reason==='RULE_DISABLED');

console.log('\n== §16 — EVALUATOR PRIMITIVES ==');
const eg=S(vb,'EGRESS:bld_0.g.majlis');
chk('existence', evaluateRule(ruleById('TEST_ONLY.EXISTS_001',[])[1],eg,CTX,null,[]).status==='PASS');
chk('count_min', evaluateRule(ruleById('TEST_ONLY.COUNT_MIN_001',[])[1],eg,CTX,null,[]).status==='PASS');
chk('enumeration', EV(vb,'TEST_ONLY.ENUM_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis').status==='PASS');
chk('boolean_required', EV(vb,'TEST_ONLY.BOOL_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis').status==='PASS');
chk('boolean_required FAIL when false',
    EV(vb,'TEST_ONLY.BOOL_001','ROUTE:bld_0.g.majlis>bld_0.g.living').status==='FAIL');
chk('numeric_range', EV(vb,'TEST_ONLY.RANGE_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis').status==='PASS');
const rall=EV(vb,'TEST_ONLY.ALL_OF_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('all_of PASS with per-clause detail', rall.status==='PASS'&&rall.actual.clauses.length===2,
    JSON.stringify(rall.actual));
const rany=EV(vb,'TEST_ONLY.ANY_OF_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('any_of PASS when one clause holds',
    rany.status==='PASS'&&rany.actual.clauses.filter(c=>c.satisfied).length===1, JSON.stringify(rany.actual));
chk('all ten primitives are declared', Object.keys(RULE_OPERATORS).length===10, Object.keys(RULE_OPERATORS));

console.log('\n== §17 / §38 — EXPRESSION SAFETY & IMPORT SECURITY ==');
chk('engine source contains no eval/Function constructor',
    !/[^a-zA-Z_]eval\s*\(|new\s+Function\s*\(/.test(evaluateRule.toString()+validateRule.toString()+
      _evalPrimitive.toString()+evaluateRuleSet.toString()));
chk('script-bearing rule rejected',
    validateRule(Object.assign(C(GOOD),{script:'alert(1)'})).some(i=>/forbidden executable/.test(i)));
chk('javascript: URL rejected',
    validateRule(Object.assign(C(GOOD),{source:Object.assign(C(GOOD.source),{url:'javascript:alert(1)'})}))
      .some(i=>/forbidden executable|https/.test(i)));
chk('non-https source url rejected',
    validateRule(Object.assign(C(GOOD),{source:Object.assign(C(GOOD.source),{url:'http://x.example/doc'})}))
      .some(i=>/https/.test(i)));
chk('unknown operator rejected', validateRule(Object.assign(C(GOOD),{operator:'do_whatever'}))
      .some(i=>/unknown operator/.test(i)));
chk('unknown unit rejected',
    validateRule(Object.assign(C(GOOD),{inputs:[{key:'route.hops',unit:'furlong',required:true}]}))
      .some(i=>/unknown input unit/.test(i)));
chk('input outside the contract rejected',
    validateRule(Object.assign(C(GOOD),{inputs:[{key:'route.made_up',required:true}]}))
      .some(i=>/outside the declared contract/.test(i)));
chk('unknown subject_type rejected',
    validateRule(Object.assign(C(GOOD),{subject_type:'DRAGON'})).some(i=>/unknown subject_type/.test(i)));
chk('duplicate rule identity rejected at ruleset level',
    validateRuleSet({ruleset_id:'D',ruleset_version:'1',standard:'X',edition:'1',completeness:'partial',
      rules:[C(GOOD),C(GOOD)]}).some(i=>/duplicate rule identity/.test(i)));
chk('nested composite operators rejected',
    validateRule(Object.assign(C(GOOD),{operator:'all_of',
      expected:{clauses:[{operator:'all_of',input:'route.hops',expected:{value:1}}]}}))
      .some(i=>/nested composite/.test(i)));
chk('unknown completeness rejected',
    validateRuleSet({ruleset_id:'D',ruleset_version:'1',standard:'X',edition:'1',
      completeness:'complete',rules:[]}).some(i=>/unknown completeness/.test(i)));
chk('complete_for_declared_scope requires a declared scope',
    validateRuleSet({ruleset_id:'D',ruleset_version:'1',standard:'X',edition:'1',
      completeness:'complete_for_declared_scope',rules:[]}).some(i=>/requires a declared coverage_scope/.test(i)));
chk('invalid ruleset does not execute',
    evaluateRuleSet('BROKEN',[],CTX,[{ruleset_id:'BROKEN',ruleset_version:'1',standard:'X',
      edition:'1',completeness:'partial',rules:[C(GOOD),C(GOOD)]}]).error==='INVALID_RULESET');

console.log('\n== §34/§35/§36 — AGGREGATION SEMANTICS ==');
const subs=['ROUTE:bld_0.f.bed1>bld_0.g.majlis','EGRESS:bld_0.g.majlis','DOOR:bld_0.g.majlis.door_0']
  .map(x=>S(vb,x)).filter(Boolean);
const run=evaluateRuleSet('TEST_ONLY.CORE',subs,{evaluated_at:'T0',subjects:{BUILDING:S(vb,'BUILDING:bld_0')}},[]);
const agg=aggregateRuleResults(run.results,ruleSetById('TEST_ONLY.CORE',[]));
chk('overall_compliance = NOT_DETERMINED', agg.overall_compliance==='NOT_DETERMINED', agg.overall_compliance);
chk('all seven state counters present',
    ['pass','fail','not_applicable','not_evaluated','insufficient_data','invalid_rules','unsupported']
      .every(k=>typeof agg[k]==='number'), JSON.stringify(agg));
chk('counters sum to rules_evaluated',
    agg.pass+agg.fail+agg.not_applicable+agg.not_evaluated+agg.insufficient_data+
    agg.invalid_rules+agg.unsupported===agg.rules_evaluated, JSON.stringify(agg));
chk('regulatory results = 0, synthetic > 0', agg.regulatory_results===0&&agg.synthetic_results>0);
chk('regulatory_rules_loaded = 0', agg.regulatory_rules_loaded===0);
chk('completeness surfaced as partial', agg.completeness==='partial');
chk('statement never says the building is compliant',
    !/مطابق للكود|code compliant|building is compliant|BUILDING COMPLIANT/i.test(agg.statement), agg.statement);
chk('statement declares how many rules were configured',
    /تم التقييم مقابل \d+ قاعدة/.test(agg.statement), agg.statement);
chk('aggregation never invents a verdict from partial passes',
    !(agg.pass>0&&agg.overall_compliance!=='NOT_DETERMINED'));

console.log('\n== §14 — READ-ONLY ENGINE ==');
const before=JSON.stringify(vb);
evaluateRuleSet('TEST_ONLY.CORE',subs,{evaluated_at:'T0',subjects:{BUILDING:S(vb,'BUILDING:bld_0')}},[]);
chk('model unchanged after evaluation', JSON.stringify(vb)===before);
chk('no remediation/auto-fix field is produced',
    !/suggested_action|autofix|auto_fix|remediation/i.test(JSON.stringify(run.results)));
chk('no exit/door/stair was created',
    extractExits(vb,buildRelationships(vb,'bld_0'),'bld_0').length===
    extractExits(JSON.parse(before),buildRelationships(JSON.parse(before),'bld_0'),'bld_0').length);

console.log('\n== §20 — SUBJECT RESOLUTION ==');
chk('BUILDING resolves', S(vb,'BUILDING:bld_0').type==='BUILDING');
chk('SPACE resolves', S(vb,'SPACE:bld_0.g.majlis').type==='SPACE');
chk('DOOR resolves', S(vb,'DOOR:bld_0.g.majlis.door_0').type==='DOOR');
chk('ROUTE resolves', S(vb,'ROUTE:bld_0.g.majlis>bld_0.g.living').type==='ROUTE');
chk('EGRESS resolves', S(vb,'EGRESS:bld_0.g.majlis').type==='EGRESS');
chk('unknown subject type refused', S(vb,'DRAGON:x')===null);
chk('unknown space refused', S(vb,'SPACE:bld_0.g.nope')===null);
chk('subject with no prefix refused', S(vb,'bld_0.g.majlis')===null);
chk('unresolved subject ⇒ NOT_EVALUATED (not FAIL)',
    evaluateRule(ruleById('TEST_ONLY.NUMERIC_MAX_001',[])[1],null,CTX,null,[]).status==='NOT_EVALUATED');
chk('subject/rule type mismatch ⇒ NOT_APPLICABLE',
    EV(vb,'TEST_ONLY.NUMERIC_MAX_001','SPACE:bld_0.g.majlis').reason==='SUBJECT_TYPE_MISMATCH');
chk('all 14 subject types declared', RULE_SUBJECT_TYPES.length===14, RULE_SUBJECT_TYPES.length);

console.log('\n== §11 — PASS/FAIL SEMANTICS ==');
const every=[r,rf,rp,rg,rj,rm,ru,rb,ra,rna,rid].concat(run.results);
chk('PASS/FAIL only when applicable + complete data',
    every.filter(x=>x.status==='PASS'||x.status==='FAIL')
         .every(x=>x.applicability==='APPLICABLE'&&x.data_quality==='COMPLETE'));
chk('missing data never became PASS or FAIL',
    every.filter(x=>x.data_quality==='MISSING'||x.data_quality==='INCOMPLETE')
         .every(x=>x.status!=='PASS'&&x.status!=='FAIL'));
chk('every result declares an evaluation state', every.every(x=>RULE_STATES.indexOf(x.status)>=0));
chk('every non-PASS/FAIL result states a reason',
    every.filter(x=>x.status!=='PASS'&&x.status!=='FAIL').every(x=>!!x.reason));
chk('no result claims code compliance',
    !/code[_ -]?compliant|مطابق للكود|نظامي/i.test(JSON.stringify(every)));
chk('code_required_eligible false everywhere in this phase',
    every.every(x=>x.code_required_eligible===false));

console.log(`\nRULES: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
