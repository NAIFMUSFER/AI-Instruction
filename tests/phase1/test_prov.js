/* F-09: الأسماء التي تُكتب عبر حدود الوحدات انتقلت إلى كائن الحالة المشترك
   __ACS_SHARED؛ الاختبار يكتب حيث يقرأ التطبيق فعلاً، لا في اسم ميت. */
let pass=0,fail=0; const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const VILLA='فيلا دورين، الدور الأرضي يحتوي على مجلس وصالة ومطبخ وغرفة ضيوف وحمامين، والدور الأول يحتوي على 4 غرف نوم و3 حمامات وصالة عائلية، مع درج وموقف سيارتين.';
const FORBIDDEN=/وفق\s+الكود|متطلّب\s*كود|متطلب\s*كود|مطابق\s+للكود|متوافق\s+مع\s+الكود|code[- ]?compliant|code[- ]?required|إصلاح\s*:|تم\s+التحقق\s+هندسي/i;

console.log('\n== TEST A — VILLA FLOORS (user=2, model=3) ==');
chk('requestedFloorsFromText("فيلا دورين…") === 2', requestedFloorsFromText(VILLA)===2, requestedFloorsFromText(VILLA));
let A=classifyReport({requirements:[
  {req:'عدد الأدوار 3', where:'levels', how:'ground+first+roof'},
  {req:'مجلس', where:'majlis', how:'غرفة مغلقة'}]}, VILLA);
chk('floors claim NOT under USER_REQUESTED', !A.user.some(r=>/الأدوار|المستويات/.test(r.req)), JSON.stringify(A.user.map(r=>r.req)));
chk('floors claim reclassified to SYSTEM', A.system.some(r=>/المستويات في النموذج/.test(r.req)), JSON.stringify(A.system.map(r=>r.req)));
chk('states user requested 2', A.system.some(r=>/طلب المستخدم: 2/.test(r.req)));
chk('report exposes requested floors = 2', A.floors.requested===2, A.floors.requested);
chk('genuine user item (مجلس) stays USER', A.user.some(r=>r.req==='مجلس'));

console.log('\n== TEST B — ROOF (auto) ==');
let B=classifyReport({added:['سطح (roof) لإيصال بيت الدرج وفق الكود']}, VILLA);
chk('roof → SYSTEM (not USER, not RULE)', B.system.length===1&&B.user.length===0&&B.rule.length===0);
chk('no "وفق الكود" in text', !FORBIDDEN.test(B.system[0].req), B.system[0].req);
chk('source=system_default', B.system[0].source===PROV.SYSTEM, B.system[0].source);

console.log('\n== TEST C — SMOKE DETECTOR ==');
let C=classifyReport({added:['إصلاح: أُضيف كاشف دخان smoke في غرفة bath3 التي كانت تفتقد له']}, VILLA);
chk('smoke → SYSTEM/AUTO_ADDED', C.system.length===1&&C.rule.length===0);
chk('no "إصلاح:" framing', !FORBIDDEN.test(C.system[0].req), C.system[0].req);
chk('CODE_REQUIRED count = 0', C.rule.length===0);

console.log('\n== TEST D — STAIR CONNECTIVITY ==');
let D=classifyReport({requirements:[{req:'عنصر kind=stairs في منطقة corridor بكل دور يربط الطوابق'}]}, VILLA);
const dtxt=(D.user.concat(D.ai,D.system))[0].req;
chk('no "يربط الطوابق" claim', !/يربط\s+الطوابق/.test(dtxt), dtxt);
chk('uses visual-representation wording', /مُمثَّل بصرياً/.test(dtxt)&&/لم يُتحقَّق من الربط الرأسي/.test(dtxt), dtxt);

console.log('\n== TEST E — PARKING (represented alternatively) ==');
const pk=Object.fromEntries(objectsFromText('موقف سيارتين').objects.map(o=>[o.kind,o.count]));
chk('cars = 2, dropped = 0', pk.car===2, JSON.stringify(pk));
let E=classifyReport({extras:['موقف سيارتين — مُثِّل كمنطقة خارجية + سيارتان']}, VILLA);
chk('appears under REPRESENTED_ALTERNATIVELY', E.alt.length===1&&/موقف/.test(E.alt[0]), JSON.stringify(E.alt));
chk('not reported as unsupported', E.unsupported.length===0);

console.log('\n== TEST F — EXPLICIT EXCLUSION (بدون مصعد) ==');
const ex=objectsFromText('فيلا دورين بدون مصعد');
let F=classifyReport({requirements:objCoverage(ex.objects), excluded:ex.excluded}, 'فيلا دورين بدون مصعد');
chk('elevator EXCLUDED', F.excluded.some(t=>/مصعد/.test(t)), JSON.stringify(F.excluded));
chk('elevator NOT in AUTO_ADDED/system', !F.system.some(r=>/مصعد/.test(r.req)));
chk('elevator NOT in CODE_REQUIRED', !F.rule.some(r=>/مصعد/.test(r.req)));
chk('elevator NOT generated as object', !ex.objects.some(o=>o.kind==='elevator'), JSON.stringify(ex.objects.map(o=>o.kind)));

console.log('\n== TEST G — AI INFERENCE (number user never stated) ==');
let G=classifyReport({requirements:[{req:'12 موقف سيارات إضافي', where:'site', how:'أُضيف'}]}, VILLA);
chk('unproven number → AI_INFERRED not USER', G.ai.length===1&&G.user.length===0, JSON.stringify({ai:G.ai.length,user:G.user.length}));
chk('source=ai_inference', G.ai[0].source===PROV.AI, G.ai[0].source);

console.log('\n== TEST H — CODE_REQUIRED gated on real evidence ==');
chk('no evidence ⇒ hasRuleEvidence=false', hasRuleEvidence({req:'x'})===false);
chk('partial evidence ⇒ false', hasRuleEvidence({req:'x',standard:'SBC',rule_id:'1'})===false);
let H0=classifyReport({added:['طفايات ومخارج طوارئ'],requirements:[{req:'مجلس'}]}, VILLA);
chk('CODE_REQUIRED count = 0 in Phase 1', H0.rule.length===0, H0.rule.length);
// الحقول وحدها لم تعد كافية: تلزم قاعدة تنظيمية محمّلة في السجلّ ومصدرها موثّق
const H_CLAIM={req:'مخرج طوارئ ثانٍ', rule_id:'SBC801-4.2', standard:'SBC 801', edition:'2018',
               condition:'occupancy>50', result:'required'};
let H1=classifyReport({requirements:[JSON.parse(JSON.stringify(H_CLAIM))]}, VILLA);
chk('full FIELDS but rule not loaded ⇒ rejected', H1.rule.length===0, JSON.stringify(H1.rule));
chk('registry holds zero regulatory rules', regulatoryRuleCount(__ACS_SHARED.ACS_EXTRA_RULESETS)===0);
// قاعدة اصطناعية موجودة فعلاً في السجلّ لا تفتح البوّابة أبداً
chk('synthetic TEST_ONLY rule can never open the gate',
    codeRequiredAllowed('TEST_ONLY.NUMERIC_MAX_001',__ACS_SHARED.ACS_EXTRA_RULESETS)===false);
// نحقن مجموعة تنظيمية موثّقة (اختبار آلية البوّابة فقط — ليست قاعدة كود حقيقية)
__ACS_SHARED.ACS_EXTRA_RULESETS=[{ruleset_id:'GATE_TEST',ruleset_version:'1',standard:'SBC 801',edition:'2018',
  completeness:'partial',coverage_scope:'gate mechanics probe',regulatory:true,
  rules:[{rule_id:'SBC801-4.2',namespace:'GATE_TEST',regulatory:true,title:'gate probe',
    category:'egress',severity:'info',enabled:true,revision:1,
    standard:'SBC 801',edition:'2018',section:'4.2',jurisdiction_required:false,
    jurisdiction:{country:null,region:null,authority:null},
    source:{type:'official_document',source_id:'SBC',document_id:'GATE-TEST-DOC',page:null,
            clause:'4.2',url:null,verified:true},
    subject_type:'ROUTE',applies_to:{subject_type:'ROUTE',conditions:[]},
    inputs:[{key:'route.hops',unit:'count',required:true}],
    operator:'count_min',expected:{value:1}}]}];
let H2=classifyReport({requirements:[JSON.parse(JSON.stringify(H_CLAIM))]}, VILLA);
chk('loaded + verified regulatory rule ⇒ CODE_REQUIRED accepted',
    H2.rule.length===1&&H2.rule[0].source===PROV.RULE, JSON.stringify(H2.rule));
// إزالة التحقّق من المصدر تُغلق البوّابة فوراً
__ACS_SHARED.ACS_EXTRA_RULESETS[0].rules[0].source.verified=false;
let H3=classifyReport({requirements:[JSON.parse(JSON.stringify(H_CLAIM))]}, VILLA);
chk('unverified source ⇒ gate closes again', H3.rule.length===0, JSON.stringify(H3.rule));
__ACS_SHARED.ACS_EXTRA_RULESETS=[];

console.log('\n== RENDER — no forbidden phrases + distinct sections ==');
showReport({requirements:[{req:'عدد الأدوار 3'},{req:'مجلس'}],
            added:['سطح (roof) لإيصال بيت الدرج وفق الكود','إصلاح: أُضيف كاشف دخان smoke في bath3'],
            extras:['موقف سيارتين — منطقة خارجية + سيارتان'], excluded:['مصعد']}, VILLA);
const html=__box.innerHTML;
chk('render has NO forbidden code claims', !FORBIDDEN.test(html));
chk('render shows user-requested floors = 2', /عدد الأدوار الذي طلبته: 2/.test(html));
chk('render has distinct SYSTEM section', /أضافه النظام تلقائياً/.test(html));
chk('render has EXCLUDED section', /مُستبعَد/.test(html));
chk('render has ALT section', /مُثِّل بطريقة بديلة/.test(html));
chk('render discloses no code validation performed', /لم يُنفَّذ تحقّق مطابقة لأي كود/.test(html));
chk('render has NO ⚖ rule section (no evidence)', !/مطلوب بقاعدة موثّقة/.test(html));
chk('XSS still escaped in report', (showReport({requirements:[{req:'<script>alert(1)</script>'}]},VILLA), !/<script>/.test(__box.innerHTML)));

console.log(`\nPROVENANCE: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
