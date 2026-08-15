/* المرحلة 9.2 — تكافؤ بايثون وجافاسكربت في طبقة التفصيل المعماري. */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_ad_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_ad_py.json');
const env=Object.assign({},process.env,{ACS_PARITY_AD_JS:JS,ACS_PARITY_AD_PY:PY});
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
[JS,PY].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });
console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_ad.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran',/parity written/.test(o),o.slice(-200));
}catch(e){ chk('the python implementation ran',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-600)); }
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_ad_body.js')],
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
const m=/AD PARITY: (\d+)\/(\d+) byte-identical/.exec(cmp);
chk('every group agrees between the two implementations',!!m&&m[1]===m[2],
  m?m[0]:'');
const cm=/counts: (\{.*\})/.exec(cmp);
const counts=cm?JSON.parse(cm[1]):{};
chk('the comparison is not vacuous — twenty-seven materials compared',
  counts.materials===27,JSON.stringify(counts));
chk('zoning, windows, recipes, cameras and configs were really exercised',
  counts.zoning===24&&counts.windows===30&&counts.recipes===29
  &&counts.cameras===52&&counts.configs===6&&counts.captures===3,
  JSON.stringify(counts));
console.log('\nAD PARITY SUITE: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
