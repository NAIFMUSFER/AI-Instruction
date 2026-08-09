/* ============================================================================
   المرحلة 7 — تكافؤ بايثون وجافاسكربت في خطّ العرض
   الفشل هنا يعني أن الواجهة تُظهر للمستعمل هندسة غير التي يقيسها المحرّك في
   اللغة الأخرى من التطبيق — وهو ما يمنعه العقد صراحةً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_render_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_render_py.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_RENDER_JS:JS,ACS_PARITY_RENDER_PY:PY});
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
[JS,PY].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_render_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran and wrote its result', /parity written/.test(o));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_render.py')],
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
  chk('every '+label+' agrees between the two implementations', !!m&&m[1]===m[2], m?m[0]:''); };
grab(/RENDER PARITY: (\d+)\/(\d+) byte-identical/,'top-level key');
grab(/cameras: (\d+)\/(\d+)/,'camera solution');
grab(/materials: (\d+)\/(\d+)/,'material assignment');
grab(/drawings: (\d+)\/(\d+)/,'drawing');
grab(/control buffers: (\d+)\/(\d+)/,'control buffer set');
grab(/geometry features: (\d+)\/(\d+)/,'geometry feature set');
grab(/svg output: (\d+)\/(\d+)/,'vector output');
grab(/png bytes: (\d+)\/(\d+)/,'raster byte stream');
grab(/model hashes: (\d+)\/(\d+)/,'model hash');
grab(/drift cases: (\d+)\/(\d+)/,'drift case');
grab(/ai boundary: (\d+)\/(\d+)/,'AI boundary case');
grab(/material ops: (\d+)\/(\d+)/,'material operation');
grab(/interior cameras: (\d+)\/(\d+)/,'interior camera case');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  const CANON=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_render.json'),'utf8'));
  chk('both files carry the same keys',
      JSON.stringify(Object.keys(J).sort())===JSON.stringify(Object.keys(P).sort()));
  const scen=Object.keys(J).filter(k=>k.indexOf('__')!==0);
  chk('the comparison covers every shipped fixture model', scen.length>=9, String(scen.length));
  chk('every model produced real control buffers',
      scen.every(k=>J[k].buffers.valid===true
        &&J[k].buffers.buffers.buffers.SEMANTIC_MASK.length===96*64));
  chk('every model produced a geometry feature set',
      scen.every(k=>J[k].features.valid===true));
  chk('at least one model shows real openings in the buffers',
      scen.some(k=>J[k].features.features.opening_count>0));
  chk('at least one model shows more than one storey band',
      scen.some(k=>J[k].features.features.floor_band_count>1));
  chk('every model produced non-trivial vector output',
      scen.every(k=>J[k].plan_svg.indexOf('<svg')===0&&J[k].plan_svg.length>500));
  chk('the vector output is identical character for character',
      scen.every(k=>J[k].plan_svg===P[k].plan_svg
        &&J[k].elevation_svg===P[k].elevation_svg
        &&J[k].section_svg===P[k].section_svg));
  chk('the raster byte streams are identical',
      scen.every(k=>JSON.stringify(J[k].png_sha)===JSON.stringify(P[k].png_sha)));
  chk('a self comparison passes in both implementations',
      scen.every(k=>J[k].self_drift.status==='PASS'&&P[k].self_drift.status==='PASS'));
  chk('every synthetic drift case is rejected identically',
      ['window_added','window_removed','door_moved','floor_drift','footprint_drift',
       'wall_drift','roof_drift','wrong_camera','wrong_model']
        .every(k=>J.__drift__[k].status==='REJECTED'
          &&P.__drift__[k].status==='REJECTED'));
  chk('an identical candidate passes in both implementations',
      J.__drift__.identical.status==='PASS'&&P.__drift__.identical.status==='PASS');
  chk('a missing semantic object warns in both implementations',
      J.__drift__.semantic_missing.status==='WARNING'
      &&P.__drift__.semantic_missing.status==='WARNING');
  chk('the AI request is refused identically without buffers or a base render',
      J.__ai__.request_no_buffers.valid===false&&P.__ai__.request_no_buffers.valid===false
      &&J.__ai__.request_no_base.valid===false&&P.__ai__.request_no_base.valid===false);
  chk('an unreachable provider falls back identically',
      J.__ai__.enhance_unavailable.used_ai===false
      &&P.__ai__.enhance_unavailable.used_ai===false);
  chk('a hostile reference is dropped from the prompt in both',
      J.__ai__.contract.reference_ids.length===1
      &&P.__ai__.contract.reference_ids.length===1);
  chk('a specification-intent override is refused in both',
      J.__materials__.override_spec.requires_authoring===true
      &&P.__materials__.override_spec.requires_authoring===true);
  chk('a space too small for a camera is refused in both',
      J.__interior__.missing.valid===false&&P.__interior__.missing.valid===false);
  chk('industrial context stays off by default in both',
      J.__context__.default.indexOf('industrial_equipment')<0
      &&P.__context__.default.indexOf('industrial_equipment')<0);
  chk('a planted difference would be detected', (function(){
    const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
      if(v&&typeof v==='object'){ const o={};
        Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
      return v; };
    const t=JSON.parse(JSON.stringify(P[scen[0]]));
    t.model_hash='tampered';
    return JSON.stringify(canon(J[scen[0]]))!==JSON.stringify(canon(t)); })());
})();

console.log('\n──────────────────────────────────────────────');
console.log('RENDER PARITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
