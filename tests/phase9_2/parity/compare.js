/* يقارن طبقة التفصيل المعماري في بايثون وجافاسكربت مقارنة قانونية دقيقة. */
const fs=require('fs'), os=require('os'), path=require('path');
const JS=process.env.ACS_PARITY_AD_JS||path.join(os.tmpdir(),'acs_parity_ad_js.json');
const PY=process.env.ACS_PARITY_AD_PY||path.join(os.tmpdir(),'acs_parity_ad_py.json');
const put=(o,k,v)=>Object.defineProperty(o,k,
  {value:v,enumerable:true,writable:true,configurable:true});
const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).sort().forEach(k=>{ put(o,k,canon(v[k])); }); return o; }
  return v; };
const S=v=>JSON.stringify(canon(v));
(function(){
  const a=JSON.parse('{"__proto__":1,"x":2}'), b=JSON.parse('{"x":2}');
  if(S(a)===S(b)){ console.log('✗ COMPARATOR IS BLIND TO A PROTOTYPE KEY');
    process.exit(2); }
  console.log('✓ the comparator does not silently drop a prototype key');
})();
const J=JSON.parse(fs.readFileSync(JS,'utf8'));
const P=JSON.parse(fs.readFileSync(PY,'utf8'));
const keys=Array.from(new Set(Object.keys(J).concat(Object.keys(P)))).sort();
let same=0;
const counts={};
keys.forEach(k=>{
  const a=S(J[k]), b=S(P[k]);
  counts[k]=Array.isArray(J[k])?J[k].length
    :(J[k]&&typeof J[k]==='object'?Object.keys(J[k]).length:1);
  if(a===b){ same++; return; }
  console.log('✗ group differs: '+k);
  for(let i=0;i<Math.min(a.length,b.length);i++)
    if(a[i]!==b[i]){
      console.log('   first divergence @'+i+':');
      console.log('   js: …'+a.slice(Math.max(0,i-80),i+80)+'…');
      console.log('   py: …'+b.slice(Math.max(0,i-80),i+80)+'…');
      break; } });
console.log('counts: '+JSON.stringify(counts));
console.log('AD PARITY: '+same+'/'+keys.length+' byte-identical');
if(same!==keys.length) process.exit(1);
