import assert from 'node:assert/strict';
import {analyzeBrief, buildBriefProgram, warehouseRequirementsPreflight} from '../../public/app/core/brief-program.mjs';

const form = (brief, extra={}) => ({brief, type:'residential', width:'20', depth:'25', levels:'3', rows:[], ...extra});
const evidence = program => {
  const points = Array.from(program.brief);
  for (const r of program.requirements) {
    assert.equal(points.slice(r.source_span.start,r.source_span.end).join(''),r.evidence);
    assert.equal(r.confirmed,true);
  }
};
const cases = [
  ['Standalone Arabic dimensions and dual floors keep exact reviewable evidence', () => {
    const brief='🏡 عمارة سكنية\n٢٠ متر في ٢٥ متر\nدورين';
    const a=analyzeBrief(brief);
    assert.deepEqual(a.candidates.map(r=>[r.metric,r.expected]),[['site_width_m',20],['site_depth_m',25],['level_count',2]]);
    assert.ok(a.candidates.slice(0,2).every(r=>r.source==='inferred'&&!r.confirmed));
    const p=buildBriefProgram(form(brief,{levels:'2'}));evidence(p);
    assert.equal(p.requirements[2].evidence,'دورين');
    for(const text of ['عرض 100 متر\n150 متر عمق','100 متر عرض\nعمق 150 متر']){
      assert.deepEqual(analyzeBrief(text).candidates.map(r=>[r.metric,r.expected]),[['site_width_m',100],['site_depth_m',150]]);
    }
    assert.deepEqual(analyzeBrief('۲۰۰۰ سم في ۲۵ متر').candidates.map(r=>r.expected),[20,25]);
    for(const text of ['غرفة 20 متر في 25 متر','غرفة عرض 4 متر','100 عرض\n150 عمق','دورين أو ثلاثة','لا أريد دورين','20 متر في 25 متر تقريبًا'])assert.equal(analyzeBrief(text).candidates.length,0,text);
    assert.throws(()=>buildBriefProgram(form(brief,{levels:'3'})),/تعارض/);
  }],
  ['Arabic quantities and original Unicode spans', () => {
    const brief='🏡 فيلا. عرض الموقع ٢٠ متر؛ عمق الموقع ٢٥ متر؛ عدد الأدوار ٣؛ إجمالي ٤ غرف نوم.';
    const a=analyzeBrief(brief);
    assert.equal(a.candidates.find(r=>r.metric==='site_width_m').expected,20);
    assert.equal(a.candidates.find(r=>r.role==='bedroom').expected,4);
    for(const r of a.candidates)assert.equal(Array.from(brief).slice(r.source_span.start,r.source_span.end).join(''),r.evidence);
    const p=buildBriefProgram(form(brief,{rows:[{metric:'room_count',role:'bedroom',expected:'4'}]}));
    evidence(p);assert.equal(p.requirements.find(r=>r.role==='bedroom').evidence,'٤ غرف نوم');
    assert.ok(p.brief.startsWith(brief));
  }],
  ['Explicit units convert to meters without inventing absent dimensions', () => {
    const a=analyzeBrief('عرض الموقع ۲۵۰۰ سم؛ عمق الموقع 30000 mm؛ 2 floors.');
    assert.equal(a.candidates.find(r=>r.metric==='site_width_m').expected,25);
    assert.equal(a.candidates.find(r=>r.metric==='site_depth_m').expected,30);
    assert.equal(a.candidates.find(r=>r.metric==='level_count').expected,2);
    assert.equal(analyzeBrief('مستودع مساحته ٥٠٠٠ م²').candidates.length,0);
    assert.equal(analyzeBrief('غرفة بعرض 4 متر وعمق 5 متر').candidates.length,0);
    assert.equal(analyzeBrief('عرض الموقع 20 feet').candidates.length,0);
  }],
  ['Unlabelled dimension order remains an explicitly confirmed interpretation', () => {
    const a=analyzeBrief('أبعاد الموقع ٢٠ × ٢٥ متر');
    assert.equal(a.candidates.length,2);assert.ok(a.candidates.every(r=>r.source==='inferred'&&!r.confirmed));
    const p=buildBriefProgram(form('أبعاد الموقع ٢٠ × ٢٥ متر'));
    assert.equal(p.requirements[0].source,'inferred');evidence(p);
  }],
  ['Do not turn per-floor, conditional, negative, approximate or fractional counts into totals', () => {
    for(const text of ['٣ غرف نوم في كل دور','٣ غرف نوم بالدور الأرضي','لا أريد ٣ غرف نوم','إذا أمكن ٣ غرف نوم','حوالي ٣ غرف نوم','3 bedrooms per floor','3.5 bedrooms','عدد الأدوار ٢ أو ٣','عدد الأدوار ٣-٤','3–4 bedrooms','1,000 bedrooms','-3 bedrooms','على الأقل ٣ غرف نوم','٣ غرف نوم على الأقل']) {
      assert.equal(analyzeBrief(text).candidates.length,0,text);
      assert.ok(analyzeBrief(text).questions.length,text);
    }
  }],
  ['Thousands-grouped measured areas do not create fake ambiguity questions', () => {
    const text='أريد مستودعًا بمساحة بناء إجمالية تقارب 5,000 م²، ثم Zoning Plan يوزع المساحة الإجمالية 5,000 م²، ولا تفترض أن مساحة الأرض نفسها 5,000 م².';
    const a=analyzeBrief(text);
    assert.equal(a.questions.length,0,'5,000 m² is a measured area with a thousands separator, not a range');
    assert.equal(a.candidates.length,0,'unsupported area wording must remain prose rather than become an invented hard requirement');
    assert.ok(analyzeBrief('1,000 bedrooms').questions.length,'non-area grouped counts remain reviewable instead of silently becoming totals');
  }],
  ['Warehouse site/building envelope stops in requirements before design options', () => {
    const reqs=(target=5000,levels=1)=>[
      {metric:'site_width_m',expected:50},{metric:'site_depth_m',expected:100},
      {metric:'level_count',expected:levels},{metric:'building_target_area_m2',expected:target},
    ];
    const blocked=warehouseRequirementsPreflight(reqs());
    assert.equal(blocked.status,'BUILDABLE_ENVELOPE_NOT_VERIFIED');
    assert.equal(blocked.site_area_m2,5000);assert.equal(blocked.unallocated_site_area_m2,0);assert.equal(blocked.may_generate_layout,false);
    assert.equal(warehouseRequirementsPreflight(reqs(2000)).status,'FEASIBLE_FOR_LAYOUT_PREFLIGHT');
    assert.equal(warehouseRequirementsPreflight(reqs(5000,2)).may_generate_layout,true);
    assert.equal(warehouseRequirementsPreflight(reqs(10001,2)).status,'BUILDING_TARGET_EXCEEDS_THEORETICAL_FLOOR_AREA');
    assert.equal(warehouseRequirementsPreflight(reqs().slice(0,3)).status,'NOT_EVALUATED');
    const warehouse=form('مستودع لوجستي',{type:'warehouse',width:'50',depth:'100',levels:'1',rows:[{metric:'building_target_area_m2',expected:'5000'}]});
    assert.throws(()=>buildBriefProgram(warehouse),/تستهلك كامل مساحة الموقع/);
    assert.doesNotThrow(()=>buildBriefProgram(form('مستودع لوجستي',{type:'warehouse',width:'50',depth:'100',levels:'1',rows:[{metric:'building_target_area_m2',expected:'2000'}]})));
    assert.doesNotThrow(()=>buildBriefProgram(form('مشروع سكني',{type:'residential',width:'50',depth:'100',levels:'1',rows:[{metric:'building_target_area_m2',expected:'5000'}]})));
  }],
  ['Conflicting description and inputs stop before generation', () => {
    assert.throws(()=>buildBriefProgram(form('عرض الموقع ٢٢ متر')),/تعارض/);
    assert.throws(()=>buildBriefProgram(form('عرض الموقع 20 متر؛ عرض الموقع 22 متر')),/تعارض/);
    assert.throws(()=>buildBriefProgram(form('عدد الأدوار 3؛ 4 غرف نوم')),/غرف النوم/);
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{rows:[{metric:'room_count',role:'bedroom',expected:'1.5'}]})),/صحيح/);
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{width:''})),/عرض الموقع/);
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{width:'0'})),/موجبة/);
  }],
  ['Manual answers get exact separately labelled source spans', () => {
    const p=buildBriefProgram(form('مستودع باستلام وشحن',{type:'warehouse',rows:[{metric:'dock_count',role:'',expected:'0'}]}));
    evidence(p);const dock=p.requirements.find(r=>r.metric==='dock_count');
    assert.equal(dock.expected,0);assert.equal(dock.source_id,'brief:form');
    assert.ok(dock.evidence.includes('الأرصفة'));
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{rows:[{metric:'room_count',role:'',expected:'2'}]})),/استخدام/);
  }],
  ['Exact dock counts differ from minimum groups and repeated facts are not added', () => {
    const a=analyzeBrief('عدد الأرصفة ٤؛ ٤ أرصفة؛ على الأقل ٣ مجموعات رفوف');
    assert.equal(a.candidates.filter(r=>r.metric==='dock_count').length,1);
    assert.equal(a.candidates.find(r=>r.metric==='min_rack_group_count').expected,3);
    assert.equal(analyzeBrief('أربعة أرصفة').candidates.length,0);
    assert.equal(analyzeBrief('٤ رفوف').candidates.length,0);
  }],
  ['No silent merging of conflicting rows, unsupported selectors or oversized programs', () => {
    const rows=[{metric:'room_count',role:'bedroom',expected:2},{metric:'room_count',role:'bedroom',expected:3}];
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{rows})),/تعارض/);
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{rows:[{metric:'unknown',expected:2}]})),/متطلب/);
    assert.throws(()=>buildBriefProgram(form('x'.repeat(60001))),/الحد/);
  }],
  ['Requirement identities survive row reordering and legacy reopen when evidence is unchanged', () => {
    const initialRows=[
      {metric:'room_count',role:'bedroom',expected:'2'},
      {metric:'min_space_area_by_role_m2',role:'bedroom',expected:'18'},
    ];
    const first=buildBriefProgram(form('طلب بناء',{rows:initialRows}));
    const firstIds=new Map(first.requirements.map(r=>[JSON.stringify([r.metric,r.role||'']),r.id]));
    const reordered=buildBriefProgram(form(first.brief,{savedRequirements:first.requirements,rows:[
      {metric:'room_count',role:'kitchen',expected:'1'},
      initialRows[1],initialRows[0],
    ]}));
    evidence(reordered);
    for(const r of first.requirements){
      const current=reordered.requirements.find(x=>x.metric===r.metric&&(x.role||'')===(r.role||''));
      assert.equal(current.id,r.id,'unchanged requirement identity must survive form row reordering');
    }
    const kitchen=reordered.requirements.find(r=>r.role==='kitchen');
    assert.ok(kitchen&&!new Set(firstIds.values()).has(kitchen.id),'new requirement needs a fresh non-colliding identity');

    // If the engineer rewrites the brief and retires the old evidence, a changed
    // requirement must not inherit that retired identity merely because the
    // local fresh-id counter reaches the same brief-N slot.
    const changed=buildBriefProgram(form('طلب بناء',{savedRequirements:first.requirements,rows:[
      {metric:'room_count',role:'bedroom',expected:'3'},
      initialRows[1],
    ]}));
    const oldBedroom=first.requirements.find(r=>r.metric==='room_count'&&r.role==='bedroom');
    const changedBedroom=changed.requirements.find(r=>r.metric==='room_count'&&r.role==='bedroom');
    assert.notEqual(changedBedroom.id,oldBedroom.id,'changed requirement value must receive a new provenance identity');
    assert.ok(!new Set(first.requirements.map(r=>r.id)).has(changedBedroom.id),'fresh identity must not recycle a retired saved requirement id');

    const legacyBrief='طلب بناء\nالعرض: 20\nالعمق: 25\nعدد الأدوار: 3\nroom_count bedroom: 2';
    const legacySaved=[
      {id:'brief-site_width_m',metric:'site_width_m',expected:20,source:'requested',evidence:'العرض: 20',confirmed:true},
      {id:'brief-site_depth_m',metric:'site_depth_m',expected:25,source:'requested',evidence:'العمق: 25',confirmed:true},
      {id:'brief-level_count',metric:'level_count',expected:3,source:'requested',evidence:'عدد الأدوار: 3',confirmed:true},
      {id:'program-0',metric:'room_count',role:'bedroom',expected:2,source:'requested',evidence:'room_count bedroom: 2',confirmed:true},
    ];
    const migrated=buildBriefProgram(form(legacyBrief,{savedRequirements:legacySaved,rows:[{metric:'room_count',role:'bedroom',expected:'2'}]}));
    evidence(migrated);
    for(const prior of legacySaved){
      const current=migrated.requirements.find(r=>r.metric===prior.metric&&(r.role||'')===(prior.role||''));
      assert.equal(current.id,prior.id,'legacy requirement identity must survive provenance-span migration');
    }
  }],
  ['Reopening retains the original evidence and never upgrades unknown input to a measured value', () => {
    const p=buildBriefProgram(form('طلب بناء'));
    const restored=buildBriefProgram(form(p.brief,{savedRequirements:p.requirements}));
    evidence(restored);assert.equal(restored.requirements[0].evidence,p.requirements[0].evidence);
    assert.equal(restored.brief,p.brief,'reopening must not append duplicate metadata that changes the confirmed program');
    assert.deepEqual(restored.requirements,p.requirements,'a saved manual answer must not become a quoted description requirement');
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{depth:'NaN'})),/موجبة/);
    assert.throws(()=>buildBriefProgram(form('طلب بناء',{rows:[{metric:'dock_count',expected:' '}]})),/غير محددة/);
    const source=form('طلب بناء',{rows:[{metric:'room_count',role:'bedroom',expected:'2'}]});
    const snapshot=JSON.stringify(source);buildBriefProgram(source);assert.equal(JSON.stringify(source),snapshot);
  }],
];
for(const [name,test] of cases){test();console.log('PASS '+name);}
console.log('BRIEF PROGRAM: '+cases.length+' passed');
