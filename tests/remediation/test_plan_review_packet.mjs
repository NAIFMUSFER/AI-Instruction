import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {parseReviewFile, validateView, MAX_FILE_BYTES} from '../../public/plan-review/packet.mjs';
function view() {
  const source={kind:'space',level_index:0,template:'g',room_id:'r'};
  return {schema:'acs.plan-review-view/1.0',read_only:true,
    revision:{id:'plan_test',version:1,model_hash:'a'.repeat(64),content_hash:'b'.repeat(64)},
    review:{revision_id:'plan_test',model_hash:'a'.repeat(64),content_hash:'b'.repeat(64),scopes:{program:'PASS'},issues:[]},
    scorecard:{metrics:{storage_capacity:null}},requirements:[],locks:{rooms:[],semantic:[]},
    projections:[{scope:'SPACE_BOUNDARIES_ONLY',units:'m',revision_id:'plan_test',model_hash:'a'.repeat(64),level_index:0,site:{w:30,d:30},
      source_map:[{source_id:'s1',source,requirement_refs:[]}],
      primitives:[{source_id:'s1',source,requirement_refs:[],rect_xz_m:[0,0,30,30],space_rect_area_m2:900,label:'المجلس'}]}]};
}
function encode(p) {const raw=JSON.stringify(p);return JSON.stringify({schema:'acs.plan-review-file/1.0',payload_json:raw,payload_sha256:createHash('sha256').update(raw).digest('hex')});}
test('exact UTF8 packet preserves geometry and unknown metrics',async()=>{const p=await parseReviewFile(encode(view()));assert.equal(p.projections[0].primitives[0].label,'المجلس');assert.equal(p.scorecard.metrics.storage_capacity,null);});
test('altered payload without new hash fails',async()=>{const f=JSON.parse(encode(view()));f.payload_json+=' ';await assert.rejects(()=>parseReviewFile(JSON.stringify(f)),/REVIEW_HASH_MISMATCH/);});
test('revision/geometry receipt mismatch fails',()=>{const p=view();p.projections[0].revision_id='other';assert.throws(()=>validateView(p),/REVISION_MISMATCH/);});
test('no imported writable view',()=>{const p=view();p.read_only=false;assert.throws(()=>validateView(p));});
test('out-of-site and nonfinite geometry fail',()=>{for(const rect of [[0,0,31,30],[0,0,-1,30],[0,0,Infinity,30]]){const p=view();p.projections[0].primitives[0].rect_xz_m=rect;assert.throws(()=>validateView(p));}});
test('measured area must match drawn rectangle',()=>{const p=view();p.projections[0].primitives[0].space_rect_area_m2=5;assert.throws(()=>validateView(p));});
test('duplicate source identities fail',()=>{const p=view();p.projections[0].source_map.push(p.projections[0].source_map[0]);assert.throws(()=>validateView(p));});
test('unknown explicit requirement link fails',()=>{const p=view();p.projections[0].primitives[0].requirement_refs=[{requirement_id:'missing',source:'requested'}];assert.throws(()=>validateView(p),/PROVENANCE_MISMATCH/);});
test('prototype keys are rejected',async()=>{const p=view();p.scorecard.metrics=JSON.parse('{"__proto__":{}}');await assert.rejects(()=>parseReviewFile(encode(p)));});
test('oversized file rejected before parsing',async()=>{await assert.rejects(()=>parseReviewFile('x'.repeat(MAX_FILE_BYTES+1)),/REVIEW_FILE_LIMIT/);});
test('deep input is rejected',()=>{const p=view();let x=p.scorecard.metrics;for(let i=0;i<45;i++)x=x.deep={};assert.throws(()=>validateView(p),/REVIEW_FILE_LIMIT/);});
test('invalid source span offsets fail',()=>{const p=view();p.requirements=[{id:'a',source:'requested',source_span:{start:true,end:3}}];assert.throws(()=>validateView(p));});
