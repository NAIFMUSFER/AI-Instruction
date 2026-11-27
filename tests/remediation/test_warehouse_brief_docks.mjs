// Warehouse dock counts read from the owner's brief: receiving and shipping groups
// add up to one total to confirm; a repeated or unsided count keeps its own reading.
//   node tests/remediation/test_warehouse_brief_docks.mjs
import assert from 'node:assert/strict';
import {analyzeBrief,buildBriefProgram} from '../../public/app/core/brief-program.mjs';

const docks=text=>analyzeBrief(text).candidates.filter(c=>/dock/.test(c.metric));
const cp=s=>Array.from(s);
let checks=0;
const ok=(name,fn)=>{fn();checks++;console.log('PASS '+name);};

ok('receiving and shipping groups are summed into one inferred total',()=>{
  const text='مستودع على أرض 100×60 م، 6 أرصفة استلام و8 أرصفة شحن، ارتفاع صافي 12 م.';
  const [d,...rest]=docks(text);
  assert.equal(rest.length,0);
  assert.deepEqual([d.metric,d.expected,d.source,d.confirmed],['dock_count',14,'inferred',false]);
  assert.equal(cp(text).slice(d.source_span.start,d.source_span.end).join(''),d.evidence);
  assert.ok(d.evidence.includes('6 أرصفة استلام')&&d.evidence.includes('8 أرصفة'));
});
ok('the side may come before the count, and «و» may join the number',()=>{
  const text='الأرض 80×50 متر. الاستلام من الجهة الشمالية فيه 4 أرصفة، ثم تخزين بالتات، و4 أرصفة صادر من الجهة الجنوبية.';
  assert.deepEqual(docks(text).map(d=>[d.metric,d.expected]),[['dock_count',8]]);
});
ok('a repeated or unsided count stays one fact, and a minimum stays a minimum',()=>{
  assert.deepEqual(docks('عدد الأرصفة ٤؛ ٤ أرصفة').map(d=>[d.metric,d.expected,d.source]),[['dock_count',4,'requested']]);
  assert.deepEqual(docks('مستودع بـ 4 أرصفة تحميل').map(d=>[d.metric,d.expected]),[['dock_count',4]]);
  assert.deepEqual(docks('4 أرصفة استلام، و6 أرصفة').map(d=>[d.metric,d.expected]),[['dock_count',4],['dock_count',6]]);
  assert.deepEqual(docks('على الأقل 3 أرصفة استلام').map(d=>[d.metric,d.expected]),[['min_dock_count',3]]);
  assert.deepEqual(docks('5 أرصفة استلام').map(d=>[d.metric,d.expected]),[['dock_count',5]]);
});
ok('the confirmed inferred total enters the requirement program with its evidence',()=>{
  const brief='مستودع: 2 أرصفة استلام و3 أرصفة شحن';
  const [d]=docks(brief);
  const p=buildBriefProgram({brief,type:'warehouse',width:'60',depth:'90',levels:'1',
    rows:[{metric:'dock_count',expected:String(d.expected),source:d.source,evidence:d.evidence,source_span:d.source_span,confirmed:true}],savedRequirements:[]});
  const saved=p.requirements.find(r=>r.metric==='dock_count');
  assert.equal(saved.expected,5);
});
console.log('WAREHOUSE BRIEF DOCKS: '+checks+' passed');
