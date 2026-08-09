/* ============================================================================
   المرحلة 5 — تكافؤ بايثون وجافاسكربت في التأليف
   الفشل هنا يعني أن تطبيقاً يقبل تعديلاً يرفضه الآخر، أو ينتج نموذجاً مرشّحاً
   مختلفاً — وهو ما يمنعه العقد صراحةً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_authoring_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_authoring_py.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_AUTHORING_JS:JS,ACS_PARITY_AUTHORING_PY:PY});

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_authoring_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran and wrote its result', /parity written/.test(o));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_authoring.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran and wrote its result', /parity written/.test(o));
}catch(e){ chk('the python implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }

console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', ok=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8',maxBuffer:1<<28}); ok=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); ok=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,8).forEach(l=>console.log('   ',l));
chk('the canonical comparison reports no mismatch', ok, cmp.split('\n').pop());
const grab=(re,label)=>{ const m=re.exec(cmp);
  chk('a real comparison was performed for '+label, !!m&&Number(m[2])>0, m?m[0]:cmp.slice(-200));
  chk('every '+label+' agrees between the two implementations',
      !!m&&m[1]===m[2], m?m[0]:''); };
grab(/AUTHORING PARITY: (\d+)\/(\d+) byte-identical/,'scenario');
grab(/command hashes: (\d+)\/(\d+)/,'command hash');
grab(/candidate models: (\d+)\/(\d+)/,'candidate model hash');
grab(/validation issues: (\d+)\/(\d+)/,'validation issue sequence');
grab(/transaction results: (\d+)\/(\d+)/,'transaction result');
grab(/diffs: (\d+)\/(\d+)/,'revision diff');
grab(/adversarial: (\d+)\/(\d+)/,'adversarial case');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  chk('both files carry the same keys',
      JSON.stringify(Object.keys(J).sort())===JSON.stringify(Object.keys(P).sort()));
  const scen=Object.keys(J).filter(k=>k.indexOf('__')!==0);
  chk('the comparison covers a substantial number of scenarios',
      scen.length>=50, String(scen.length));
  chk('at least one scenario actually committed a revision',
      scen.some(k=>J[k].committed===true));
  chk('at least one scenario was refused by both',
      scen.some(k=>J[k].committed===false&&P[k].committed===false));
  chk('committed revisions match one for one',
      scen.filter(k=>J[k].committed).every(k=>J[k].commit_revision===P[k].commit_revision));
  chk('committed model hashes match one for one',
      scen.filter(k=>J[k].committed).every(k=>J[k].commit_model_hash===P[k].commit_model_hash));
  chk('undo results match where an undo was performed',
      scen.filter(k=>J[k].undo_hash!==undefined&&J[k].undo_hash!==null)
        .every(k=>J[k].undo_hash===P[k].undo_hash));
  chk('redo results match where a redo was performed',
      scen.filter(k=>J[k].redo_hash!==undefined&&J[k].redo_hash!==null)
        .every(k=>J[k].redo_hash===P[k].redo_hash));
  chk('the adversarial block is populated on both sides',
      Object.keys(J.__adversarial__||{}).length>=30
      &&Object.keys(P.__adversarial__||{}).length
        ===Object.keys(J.__adversarial__||{}).length);
  chk('both implementations agree that no adversarial command changed a model',
      Object.keys(J.__adversarial__).every(k=>
        J.__adversarial__[k].model_unchanged===true
        &&P.__adversarial__[k].model_unchanged===true));
  chk('a planted difference would be detected', (function(){
    const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
      if(v&&typeof v==='object'){ const o={};
        Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
      return v; };
    const t=JSON.parse(JSON.stringify(P[scen[0]]));
    t.command_hash='tampered';
    return JSON.stringify(canon(J[scen[0]]))!==JSON.stringify(canon(t)); })());
  /* ترتيب المفاتيح يختلف بين اللغتين؛ المقارنة قانونية كما في compare.js */
  const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
    if(v&&typeof v==='object'){ const o={};
      Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
    return v; };
  const same=(a,b)=>JSON.stringify(canon(a))===JSON.stringify(canon(b));
  chk('the target resolver agrees on every probed identifier',
      same(J.__ops__.resolve,P.__ops__.resolve));
  chk('the editable-property model agrees on every probed identifier',
      same(J.__ops__.properties,P.__ops__.properties));
  chk('natural-language target resolution agrees, including the ambiguous case',
      same(J.__ops__.nl_dup,P.__ops__.nl_dup));
  chk('the model-integrity verdict agrees',
      same(J.__ops__.integrity,P.__ops__.integrity));
  chk('the AI proposal is identical in both implementations',
      same(J.__ops__.proposal,P.__ops__.proposal));
  chk('a save and load round trip yields the same hash and revision in both',
      same(J.__ops__.load_roundtrip,P.__ops__.load_roundtrip));
  chk('a non-ASCII command parameter hashes identically in both',
      J.__ops__.hashes['مجلس']===P.__ops__.hashes['مجلس']);
})();

console.log('\n──────────────────────────────────────────────');
console.log('AUTHORING PARITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
