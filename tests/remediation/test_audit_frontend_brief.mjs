import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {analyzeBrief,buildBriefProgram} from '../../public/app/core/brief-program.mjs';

const villa='فيلا دورين على أرض ٢٠×٢٥، مجلس ومقلط ومطبخ وأربع غرف نوم ودرج داخلي';
const warehouse='مستودع دور واحد على أرض ٤٠×٦٠ متر، منطقة تخزين رئيسية ومنطقة استلام ومنطقة شحن ومكتب ودورة مياه، مدخل منفصل للموظفين.';
const counts=a=>a.candidates.map(c=>[c.metric,c.role||'',c.expected]).sort();
const bedroom=n=>({metric:'room_count',role:'bedroom',expected:n});
const form=brief=>({brief,type:'residential',width:20,depth:25,levels:2,rows:[bedroom(4)]});
const provenance=(text,candidates)=>{
  for(const c of candidates){
    assert.equal(Array.from(text).slice(c.source_span.start,c.source_span.end).join(''),c.evidence);
    assert.equal(c.source_id,'brief:text');assert.equal(c.confirmed,false);
  }
};
const noTotal=(read,text)=>{
  const a=read(text);assert.equal(a.candidates.length,0,text);
  assert.ok(a.questions.length,text+' needs clarification');
};
const cases=[
  ['exact villa keeps dimensions unassigned, asks units/order, and quotes four bedrooms',()=>{
    const a=analyzeBrief(villa);
    assert.deepEqual(counts(a),[['level_count','',2],['room_count','bedroom',4]]);
    assert.ok(a.questions.some(q=>/وحدة/.test(q)&&/العرض/.test(q)&&/العمق/.test(q)));
    assert.equal(a.candidates.find(c=>c.role==='bedroom').evidence,'وأربع غرف نوم');
    provenance(villa,a.candidates);
  }],
  ['attached Arabic conjunction preserves numeric bedrooms and exact Unicode offsets',()=>{
    for(const [text,n] of [['🏡 مجلس ومطبخ و٤ غرف نوم',4],['مجلس و۴ غرف نوم',4],['مطبخ و24 bedrooms',24],['مطبخ و ٤ غرف نوم',4],['٤ غرف نوم',4]]){
      const a=analyzeBrief(text);assert.deepEqual(counts(a),[['room_count','bedroom',n]],text);
      assert.deepEqual(a.questions,[]);provenance(text,a.candidates);
    }
    for(const text of ['س٤ غرف نوم','غ٤ غرف نوم','كو٤ غرف نوم'])assert.equal(analyzeBrief(text).candidates.length,0,text);
  }],
  ['bounded bedroom vocabulary accepts direct single-word quantities only',()=>{
    for(const [word,n] of [['ثلاث',3],['ثلاثة',3],['أربع',4],['أربعة',4],['خمس',5],['خمسة',5],['ست',6],['ستة',6],['سبع',7],['سبعة',7],['ثمان',8],['ثماني',8],['ثمانية',8],['تسع',9],['تسعة',9],['عشر',10],['عشرة',10]]){
      const text='🏡 مجلس و'+word+' غرف نوم';const a=analyzeBrief(text);
      assert.deepEqual(counts(a),[['room_count','bedroom',n]],text);assert.deepEqual(a.questions,[]);provenance(text,a.candidates);
    }
    assert.equal(analyzeBrief('أربعة أرصفة').candidates.length,0,'no general number-word expansion');
    assert.equal(analyzeBrief('أربع غرف اجتماعات').candidates.length,0,'bedroom-specific vocabulary');
    assert.deepEqual(counts(analyzeBrief('أربع غرف نوم إلى الشمال')),[['room_count','bedroom',4]],'location is not a numeric range');
  }],
  ['warehouse single-storey wording is an explicit unconfirmed candidate',()=>{
    const a=analyzeBrief(warehouse);
    assert.deepEqual(counts(a),[['level_count','',1],['site_depth_m','',60],['site_width_m','',40]]);
    assert.deepEqual(a.questions,[]);provenance(warehouse,a.candidates);
    for(const text of ['دور واحد','مستودع وطابق واحد']){
      assert.deepEqual(counts(analyzeBrief(text)),[['level_count','',1]],text);
    }
  }],
  ['unitless labelled site pairs ask without assuming meters; measured controls stay silent',()=>{
    for(const text of ['أرض ٢٠×٢٥','أرض ۲۰x۲۵','plot 20x25','أبعاد الموقع ٢٠ × ٢٥','أرض ٢٠×٢٥ ومطبخ']){
      const a=analyzeBrief(text);assert.equal(a.candidates.length,0,text);
      assert.equal(a.questions.length,1,text);assert.match(a.questions[0],/وحدة/);
    }
    for(const [text,values] of [['أرض ٢٠×٢٥ متر',[20,25]],['أرض ٢٠×٢٥ سم',[0.2,0.25]],['plot 20000x25000 mm',[20,25]]]){
      const a=analyzeBrief(text);assert.deepEqual(a.candidates.map(c=>c.expected),values,text);
      assert.deepEqual(a.questions,[]);assert.ok(a.candidates.every(c=>c.source==='inferred'&&!c.confirmed));
    }
    assert.deepEqual(analyzeBrief('غرفة ٢٠×٢٥'),{candidates:[],questions:[]});
  }],
  ['conditional, negative, per-floor, bounded and approximate word counts are not totals',()=>{
    for(const text of ['إذا أمكن أربع غرف نوم','لا أريد أربع غرف نوم','مجلس ولا أربع غرف نوم','حوالي أربع غرف نوم','أربع غرف نوم في كل دور','أربع غرف نوم بالدور الأرضي','ثلاث أو أربع غرف نوم','على الأقل أربع غرف نوم','أربع غرف نوم على الأكثر','إذا أمكن دور واحد','لا أريد دور واحد','دور واحد لكل شقة','دور واحد على الأقل','ومطبخ و٤ غرف نوم في كل دور','حوالي و٤ غرف نوم'])noTotal(analyzeBrief,text);
  }],
  ['compound words, fractions and ranges cannot be truncated into smaller counts',()=>{
    for(const text of ['ألف وأربع غرف نوم','مائة وأربع غرف نوم','خمسمائة وأربع غرف نوم','عشرون وأربع غرف نوم','أربع عشرة غرف نوم','٢٤ وأربع غرف نوم','أربع غرف نوم ونصف','دور واحد ونصف','دور واحد وعشرون','ثلاث إلى أربع غرف نوم','ثلاث غرف نوم إلى أربع غرف نوم'])noTotal(analyzeBrief,text);
  }],
  ['contradictions block confirmation; manual unit answers remain separately attributed',()=>{
    const p=buildBriefProgram(form(villa));
    const b=p.requirements.find(r=>r.role==='bedroom');assert.equal(b.expected,4);assert.equal(b.evidence,'وأربع غرف نوم');
    assert.equal(p.requirements.find(r=>r.metric==='site_width_m').source_id,'brief:form');
    for(const r of p.requirements)assert.equal(Array.from(p.brief).slice(r.source_span.start,r.source_span.end).join(''),r.evidence);
    assert.throws(()=>buildBriefProgram({...form(villa),rows:[bedroom(3)]}),/تعارض/);
    assert.throws(()=>buildBriefProgram(form('أربع غرف نوم؛ ٣ غرف نوم')),/تعارض/);
    assert.deepEqual(counts(analyzeBrief('أربع غرف نوم وعشر غرف نوم')),[['room_count','bedroom',10],['room_count','bedroom',4]]);
    assert.throws(()=>buildBriefProgram({...form('أربع غرف نوم وعشر غرف نوم'),rows:[bedroom(10)]}),/تعارض/);
    assert.throws(()=>buildBriefProgram(form('أرض ٢٠×٢٥ متر؛ أرض ٣٠×٤٠ متر')),/تعارض/);
    const a=analyzeBrief('أرض ٢٠×٢٥؛ أرض ٣٠×٤٠');assert.equal(a.candidates.length,0);assert.equal(a.questions.length,2);
  }],
];
// Import isolated mutations in memory: the checkout and production files stay intact.
// Each assertion first passes against the shipped implementation, then must reject
// the deliberately broken guard. A syntax/import failure is never a mutation kill.
const source=readFileSync(new URL('../../public/app/core/brief-program.mjs',import.meta.url),'utf8');
const mutations=[
  ['attached conjunction','(?:و\\\\s*)?(?<n>${N})','(?<n>${N})',read=>assert.equal(read('مطبخ و٤ غرف نوم').candidates[0]?.expected,4)],
  ['word value','اربع:4','اربع:40',read=>assert.equal(read(villa).candidates.find(c=>c.role==='bedroom')?.expected,4)],
  ['missing-unit question',"questions.push('أكّد وحدة أبعاد الموقع ","void('أكّد وحدة أبعاد الموقع ",read=>assert.equal(read('أرض ٢٠×٢٥').questions.length,1)],
  ['no guessed site value','const quote=chunk[0].slice(match.index,match.index+match[0].length);',"const quote=chunk[0].slice(match.index,match.index+match[0].length); add('site_width_m',20,null,match,chunk.index,'inferred');",read=>assert.equal(read('أرض ٢٠×٢٥').candidates.length,0)],
  ['explicit unit silence','(?!\\\\s*${U}(?![\\\\p{L}\\\\p{N}²]))','',read=>assert.deepEqual(read('أرض ٢٠×٢٥ متر').questions,[])],
  ['word ambiguity question','if(/[0-9]/.test(text)||wordCounts.length)','if(/[0-9]/.test(text))',read=>noTotal(read,'أربع غرف نوم في كل دور')],
  ['attached negation','|(?:^|\\s)و?(?:لا|ليس|بدون|اذا|ان|او)','|(?:^|\\s)(?:لا|ليس|بدون|اذا|ان|او)',read=>noTotal(read,'مجلس ولا أربع غرف نوم')],
  ['bounded words','ambiguous.test(text)||bounded.test(text)||compoundWordCount(text,match)','ambiguous.test(text)||false||compoundWordCount(text,match)',read=>noTotal(read,'على الأقل أربع غرف نوم')],
  ['compound prefix','compoundBefore.test(text.slice(0,match.index))','false',read=>noTotal(read,'ألف وأربع غرف نوم')],
  ['compound suffix','compoundAfter.test(after)','false',read=>noTotal(read,'دور واحد ونصف')],
  ['independent conflicting counts','!followingBedroom.test(after)','true',read=>assert.equal(read('أربع غرف نوم وعشر غرف نوم').candidates.length,2)],
  ['word range','wordCounts.length&&wordRange.test(text)','false',read=>noTotal(read,'ثلاث غرف نوم إلى أربع غرف نوم')],
  ['Unicode source offsets','source_span:{start:cp(brief.slice(0,start))','source_span:{start:start',read=>{const text='🏡 وأربع غرف نوم';provenance(text,read(text).candidates);}],
];
for(const [name,from,to,guard] of mutations)cases.push(['reject mutation: '+name,async()=>{
  guard(analyzeBrief);
  assert.equal(source.split(from).length-1,1,'mutation anchor must match exactly once: '+name);
  const mutant=await import('data:text/javascript;base64,'+Buffer.from(source.replace(from,to)).toString('base64'));
  assert.throws(()=>guard(mutant.analyzeBrief),assert.AssertionError,'mutation survived: '+name);
}]);
let failed=0;
for(const [name,test] of cases){try{await test();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+'\n'+e.stack);}}
console.log('AUDIT FRONTEND BRIEF: '+(cases.length-failed)+' passed, '+failed+' failed');
if(failed)process.exitCode=1;
