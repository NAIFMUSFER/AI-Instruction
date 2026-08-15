/* يقارن الطبقة المشتركة بين بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في نموذج تبادل، أو تحقّق، أو فرق، أو تضارب، أو مقترح، أو أمر
   مولَّد، أو نتيجة إيداع يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL. */
const fs=require('fs'), os=require('os'), path=require('path');
const JS=process.env.ACS_PARITY_BIM_JS
  ||path.join(os.tmpdir(),'acs_parity_bim_js.json');
const PY=process.env.ACS_PARITY_BIM_PY
  ||path.join(os.tmpdir(),'acs_parity_bim_py.json');
/* لا يجوز أن يُسقِط المقارِن مفتاحاً بصمت: الإسناد المباشر o['__proto__']=x
   لا ينشئ خاصّية بل ينادي واضعاً موروثاً، فيختفي المفتاح من الطرفين معاً
   وتبدو المقارنة ناجحة وهي عمياء. الإسناد هنا صريح ولذلك أمين. */
const put=(o,k,v)=>Object.defineProperty(o,k,
  {value:v,enumerable:true,writable:true,configurable:true});
const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).sort().forEach(k=>{ put(o,k,canon(v[k])); }); return o; }
  return v; };
const S=v=>JSON.stringify(canon(v));
/* فحص ذاتي للمقارِن نفسه قبل أي مقارنة */
(function(){
  const a=JSON.parse('{"__proto__":1,"x":2}'), b=JSON.parse('{"x":2}');
  if(S(a)===S(b)){
    console.log('✗ COMPARATOR IS BLIND TO A PROTOTYPE KEY');
    process.exit(2); }
  console.log('✓ the comparator does not silently drop a prototype key');
})();
const J=JSON.parse(fs.readFileSync(JS,'utf8'));
const P=JSON.parse(fs.readFileSync(PY,'utf8'));
/* الحقول التي لا يملكها المتصفّح لأنه لا يسلسل STEP — تُستثنى صراحةً لا ضمناً */
const SERIALISED_ONLY=['manifest_serialised_only'];
const prune=o=>{ const c=JSON.parse(JSON.stringify(o));
  Object.keys(c).forEach(k=>{ if(c[k]&&typeof c[k]==='object')
    SERIALISED_ONLY.forEach(f=>{ delete c[k][f]; }); }); return c; };
const Jp=prune(J), Pp=prune(P);
const keys=Array.from(new Set(Object.keys(Jp).concat(Object.keys(Pp)))).sort();
let bad=0;
keys.forEach(k=>{
  const a=S(Jp[k]), b=S(Pp[k]);
  if(a!==b){ bad++; console.log('✗ MISMATCH',k);
    for(let i=0;i<Math.max(a.length,b.length);i++)
      if(a[i]!==b[i]){
        console.log('   js:',a.slice(Math.max(0,i-200),i+200));
        console.log('   py:',b.slice(Math.max(0,i-200),i+200));
        break; }
  } else console.log('✓ identical',k); });

const scen=keys.filter(k=>k.indexOf('__')!==0);
const pair=(label,pick)=>{
  let ok=0,n=0;
  scen.forEach(k=>{ n++;
    if(S(pick(Jp[k]||{}))===S(pick(Pp[k]||{}))) ok++;
    else console.log('✗ '+label.toUpperCase()+' DISAGREEMENT',k); });
  console.log(label+': '+ok+'/'+n); };
pair('exchange models',e=>e.exchange);
pair('exchange validations',e=>e.validation);
pair('export manifests',e=>e.manifest_shared);
pair('staging counts',e=>e.staging_counts);
pair('import diffs',e=>e.diff);
pair('conflict sets',e=>e.conflicts);
pair('proposal sets',e=>e.proposals);
pair('generated commands',e=>e.commands);
pair('staleness verdicts',e=>[e.staleness_current,e.staleness_moved,
  e.export_staleness_current,e.export_staleness_moved]);
pair('empty commits',e=>e.commit_nothing_accepted);
pair('deterministic guids',e=>e.guids);
pair('model hashes',e=>e.model_hash);

const one=(label,key)=>{
  const same=S(Jp[key])===S(Pp[key]);
  if(!same) console.log('✗ '+label.toUpperCase()+' DISAGREEMENT');
  console.log(label+': '+(same?1:0)+'/1'); };
one('commit case',' __commit'.trim());
one('specification view','__spec');
one('safety verdicts','__safety');
one('unit factors','__units');

console.log('\nBIM PARITY: '+(keys.length-bad)+'/'+keys.length+' byte-identical');
if(bad) process.exit(1);
