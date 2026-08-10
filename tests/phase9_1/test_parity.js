/* المرحلة 9.1 — تكافؤ بايثون وجافاسكربت في طبقة الجودة البصرية. */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_pbr_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_pbr_py.json');
const env=Object.assign({},process.env,{ACS_PARITY_PBR_JS:JS,ACS_PARITY_PBR_PY:PY});
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
[JS,PY].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });
console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_pbr.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran',/parity written/.test(o),o.slice(-200));
}catch(e){ chk('the python implementation ran',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-600)); }
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_pbr_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran',/parity written/.test(o),o.slice(-400));
}catch(e){ chk('the browser implementation ran',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-600)); }
console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', ok=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8',maxBuffer:1<<28}); ok=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); ok=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,8).forEach(l=>console.log('   ',l));
chk('the comparator proves it is not blind to a prototype key',
  /does not silently drop a prototype key/.test(cmp));
chk('the canonical comparison reports no mismatch',ok,
  cmp.split('\n').filter(Boolean).pop());
const m=/PBR PARITY: (\d+)\/(\d+) byte-identical/.exec(cmp);
chk('every group agrees between the two implementations',!!m&&m[1]===m[2],
  m?m[0]:'');
const cm=/counts: (\{.*\})/.exec(cmp);
const counts=cm?JSON.parse(cm[1]):{};
chk('the comparison is not vacuous — twenty materials compared',
  counts.materials===20,JSON.stringify(counts));
chk('quality, camera and config matrices were really exercised',
  counts.quality===30&&counts.cameras===41&&counts.configs===5
  &&counts.shadows===25&&counts.textures===11&&counts.captures===6,
  JSON.stringify(counts));
console.log('\nPBR PARITY SUITE: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
