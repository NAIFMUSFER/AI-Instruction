/* ============================================================================
   المرحلة 4 — تكافؤ بايثون وجافاسكربت
   يشغّل الجانبين ثمّ يقارن مقارنة قانونية دقيقة. الفشل هنا يعني أن تطبيقاً
   يقبل ما يرفضه الآخر — وهو ما يمنعه العقد صراحةً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_runtime_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_runtime_py.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_RUNTIME_JS:JS,ACS_PARITY_RUNTIME_PY:PY});

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
let jsOut='', pyOut='';
try{
  jsOut=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_runtime_body.js')],
    {env:env,encoding:'utf8'});
  chk('the browser implementation ran and wrote its result', /parity written/.test(jsOut));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }
try{
  pyOut=execFileSync('python3',[path.join(HERE,'parity','py_runtime.py')],
    {env:env,encoding:'utf8'});
  chk('the python implementation ran and wrote its result', /parity written/.test(pyOut));
}catch(e){ chk('the python implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }

console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', cmpOk=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8'}); cmpOk=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); cmpOk=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,8).forEach(l=>console.log('   ',l));
chk('the canonical comparison reports no mismatch', cmpOk, cmp.split('\n').pop());
const m=/RUNTIME PARITY: (\d+)\/(\d+) byte-identical/.exec(cmp);
chk('a real comparison was performed over every scenario', !!m&&Number(m[2])>0,
    m?m[0]:'no summary line');
chk('every scenario is byte-identical between the two implementations',
    !!m&&m[1]===m[2], m?m[0]:'');
const a=/adversarial agreement: (\d+)\/(\d+)/.exec(cmp);
chk('every adversarial scene is accepted or refused identically by both',
    !!a&&a[1]===a[2]&&Number(a[2])>0, a?a[0]:'');
const o=/operation agreement: (\d+)\/(\d+)/.exec(cmp);
chk('every runtime operation yields the same issue-code sequence in both',
    !!o&&o[1]===o[2]&&Number(o[2])>0, o?o[0]:'');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  chk('both files carry the same scenario keys',
      JSON.stringify(Object.keys(J).sort())===JSON.stringify(Object.keys(P).sort()));
  chk('the comparison covers more than a handful of scenarios',
      Object.keys(J).length>=10, String(Object.keys(J).length));
  const scenes=Object.keys(J).filter(k=>k.indexOf('__')!==0);
  chk('every compared scenario carries a compiled runtime scene',
      scenes.every(k=>J[k].scene&&P[k].scene));
  chk('at least one compared scenario carries real geometry',
      scenes.some(k=>(J[k].scene.objects||[]).length>20));
  chk('at least one compared scenario carries portals',
      scenes.some(k=>(J[k].scene.walkability.portals||[]).length>0));
  chk('at least one compared scenario is rotated and translated',
      scenes.some(k=>J[k].scene.transform.rotation_deg!==0));
  chk('the adversarial block is populated on both sides',
      Object.keys(J.__adversarial__||{}).length>=10
      &&Object.keys(P.__adversarial__||{}).length
        ===Object.keys(J.__adversarial__||{}).length);
  chk('a planted difference would be detected', (function(){
    const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
      if(v&&typeof v==='object'){ const x={};
        Object.keys(v).sort().forEach(k=>{x[k]=canon(v[k]);}); return x; }
      return v; };
    const tampered=JSON.parse(JSON.stringify(P[scenes[0]]));
    tampered.scene.counts.objects=(tampered.scene.counts.objects||0)+1;
    return JSON.stringify(canon(J[scenes[0]]))!==JSON.stringify(canon(tampered)); })());
  chk('measurement identifiers agree — the numeric encoding is shared', (function(){
    return scenes.every(k=>{
      const j=(J[k].measure_width||{}).measurement;
      const p=(P[k].measure_width||{}).measurement;
      if(!j&&!p) return true;
      return !!j&&!!p&&j.measurement_id===p.measurement_id; }); })());
  chk('scene signatures agree — the canonical hash is shared',
      scenes.every(k=>J[k].scene.source_signature===P[k].scene.source_signature));
})();

console.log('\n──────────────────────────────────────────────');
console.log('PARITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
