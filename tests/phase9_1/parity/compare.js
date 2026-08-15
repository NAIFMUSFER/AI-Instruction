/* يقارن طبقة الجودة في بايثون وجافاسكربت مقارنة قانونية دقيقة. */
const fs=require('fs'), os=require('os'), path=require('path');
const JS=process.env.ACS_PARITY_PBR_JS||path.join(os.tmpdir(),'acs_parity_pbr_js.json');
const PY=process.env.ACS_PARITY_PBR_PY||path.join(os.tmpdir(),'acs_parity_pbr_py.json');
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
/* عدم الخواء: ٠/٠ ليس تطابقاً بل غياب مقارنة. الحدّ أدناه هو ما يُنتَج فعلاً. */
const MIN_GROUPS=31;
if(keys.length===0){
  console.log('✗ THE COMPARISON SET IS EMPTY — nothing was compared');
  process.exit(2); }
if(Object.keys(J).length===0||Object.keys(P).length===0){
  console.log('✗ ONE SIDE WROTE NOTHING — js:'+Object.keys(J).length
    +' py:'+Object.keys(P).length); process.exit(2); }
if(keys.length<MIN_GROUPS){
  console.log('✗ THE COMPARISON IS VACUOUS: '+keys.length+' groups, minimum '
    +MIN_GROUPS); process.exit(2); }
console.log('not vacuous: '+keys.length+' groups compared (minimum '
  +MIN_GROUPS+')');
let bad=0;
keys.forEach(k=>{
  const a=S(J[k]), b=S(P[k]);
  if(a!==b){ bad++; console.log('✗ MISMATCH',k);
    for(let i=0;i<Math.max(a.length,b.length);i++)
      if(a[i]!==b[i]){
        console.log('   js:',a.slice(Math.max(0,i-200),i+200));
        console.log('   py:',b.slice(Math.max(0,i-200),i+200));
        break; } }
  else console.log('✓ identical',k); });
const counts={materials:Object.keys(J.materials||{}).length,
  lighting:Object.keys(J.lighting||{}).length,
  shadows:(J.shadows||[]).length,quality:(J.quality||[]).length,
  cameras:(J.cameras||[]).length,configs:(J.configs||[]).length,
  textures:(J.textures||[]).length,captures:(J.captures||[]).length};
console.log('counts: '+JSON.stringify(counts));
console.log('\nPBR PARITY: '+(keys.length-bad)+'/'+keys.length+' byte-identical');
if(bad) process.exit(1);
