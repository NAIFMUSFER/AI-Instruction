import assert from 'node:assert/strict';
import {analyzeBrief,buildBriefProgram} from '../../public/app/core/brief-program.mjs';

const brief='مستودع لوجستي على أرض 50 في 100 متر. مساحة مبنى المستودع المغلقة قرابة 2,000 م² مع ساحات شاحنات ومواقف خارجية.';
const a=analyzeBrief(brief);
const target=a.candidates.find(r=>r.metric==='building_target_area_m2');
assert.ok(target,'building target must be extracted separately from site area');
assert.equal(target.expected,2000);
assert.equal(target.source,'inferred','approximate target remains reviewable, never silently hard');
const p=buildBriefProgram({brief,type:'warehouse',width:'50',depth:'100',levels:'1',rows:[{metric:'building_target_area_m2',expected:'2000'}],savedRequirements:[]});
const saved=p.requirements.find(r=>r.metric==='building_target_area_m2');
assert.equal(saved.expected,2000);assert.equal(saved.confirmed,true);
assert.equal(saved.evidence,target.evidence);
assert.ok(!p.requirements.some(r=>r.metric==='site_width_m'&&r.expected===2000));
console.log('WAREHOUSE BUILDING TARGET: PASS');
