'use strict';
// Tests the shipped pure presentation function; real rendering remains a CI gate.
const assert=require('node:assert/strict');
const path=require('node:path');
const {T}=require(path.join(__dirname,'_trust_core.js')).load();
let passed=0;
function check(name, fn){ fn(); passed++; console.log('  PASS '+name); }
const review=T.modelReviewSummary;
check('Arabic exposes the seven captured wall findings',()=>{
  assert.match(review({model_validation:{status:'COMPLETED',issue_count:7}},'ar'),/النموذج: 7/);
});
check('English exposes a completed geometry review without compliance approval',()=>{
  const text=review({model_validation:{status:'COMPLETED',issue_count:0}},'en');
  assert.match(text,/Geometry findings: 0/);
  assert.match(text,/Regulatory compliance not evaluated/);
});
for(const data of [{}, {issues:0}, {model_validation:{status:'NOT_EVALUATED',issue_count:0}},
  {model_validation:{status:'COMPLETED',issue_count:null}},
  {model_validation:{status:'COMPLETED',issue_count:-1}},
  {model_validation:{status:'COMPLETED',issue_count:'0'}},
  {model_validation:{status:'COMPLETED',issue_count:Infinity}}]){
  check('missing/partial/invalid evidence is not displayed as zero',()=>{
    assert.match(review(data,'en'),/Model review not evaluated/);
    assert.doesNotMatch(review(data,'en'),/findings: 0/);
  });
}
check('six unresolved review tasks remain visible',()=>{
  assert.match(review({review_requirements:Array(6).fill({status:'NOT_EVALUATED'})},'en'),
    /Unresolved reviews: 6/);
});
check('provider text is never copied into the displayed summary',()=>{
  const data={model_validation:{status:'<img onerror=alert(1)>',issue_count:'<script>'},
    review_requirements:[{reason:'<img onerror=alert(1)>'}]};
  assert.doesNotMatch(review(data,'en'),/[<>]/);
});
console.log('MODEL REVIEW UI: '+passed+' passed, 0 failed');
