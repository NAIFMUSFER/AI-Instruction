/* يقارن التوثيق في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في تعريف منظر، أو هندسة مسقط أو واجهة أو قطاع، أو مقاس، أو تأشيرة،
   أو صفّ جدول، أو كمّية، أو واصف لوحة، أو بيان تصدير، أو تدفّق محتوى PDF
   يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs=require('fs'), os=require('os'), path=require('path');
const JS=process.env.ACS_PARITY_DOCS_JS
  ||path.join(os.tmpdir(),'acs_parity_docs_js.json');
const PY=process.env.ACS_PARITY_DOCS_PY
  ||path.join(os.tmpdir(),'acs_parity_docs_py.json');
/* الإسناد المباشر o[k]=v يُسقِط '__proto__' بصمت فتبدو المقارنة ناجحة وهي
   عمياء. التعريف الصريح يمنع ذلك، والفحص الذاتي أدناه يثبت أنه يمنعه. */
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
let bad=0;
keys.forEach(k=>{
  const a=S(J[k]), b=S(P[k]);
  if(a!==b){ bad++; console.log('✗ MISMATCH',k);
    for(let i=0;i<Math.max(a.length,b.length);i++)
      if(a[i]!==b[i]){
        console.log('   js:',a.slice(Math.max(0,i-220),i+220));
        console.log('   py:',b.slice(Math.max(0,i-220),i+220));
        break; }
  } else console.log('✓ identical',k); });

const scen=keys.filter(k=>k.indexOf('__')!==0);
const pair=(label,pick)=>{
  let ok=0,n=0;
  scen.forEach(k=>{ n++;
    if(S(pick(J[k]||{}))===S(pick(P[k]||{}))) ok++;
    else console.log('✗ '+label.toUpperCase()+' DISAGREEMENT',k); });
  console.log(label+': '+ok+'/'+n); };
const vkey=i=>'v'+(i<10?'0':'')+i;
pair('view definitions',e=>[0,1,2,3,4,5,6,7,8,9,10,11].map(i=>(e[vkey(i)]||{}).view));
pair('view validity',e=>[0,1,2,3,4,5,6,7,8,9,10,11]
  .map(i=>[(e[vkey(i)]||{}).valid,(e[vkey(i)]||{}).issues]));
pair('projected geometry',e=>[0,5,6,7,8,9].map(i=>(e[vkey(i)]||{}).geometry));
pair('elevation geometry',e=>[1,2].map(i=>(e[vkey(i)]||{}).geometry));
pair('section geometry',e=>[3,4].map(i=>(e[vkey(i)]||{}).geometry));
pair('dimensions',e=>[0,1,2,3,4].map(i=>(e[vkey(i)]||{}).dimensions));
pair('annotations',e=>[0,1,2,3,4].map(i=>(e[vkey(i)]||{}).annotations));
pair('draw operations',e=>[0,1,3].map(i=>(e[vkey(i)]||{}).ops));
pair('svg output',e=>[0,1,2,3,4].map(i=>(e[vkey(i)]||{}).svg));
pair('svg hashes',e=>[0,1,2,3,4].map(i=>(e[vkey(i)]||{}).svg_hash));
pair('schedule rows',e=>e.schedules);
pair('quantities',e=>e.quantities);
pair('sheet descriptors',e=>[e.sheet,e.sheet_collision]);
pair('title block refusals',e=>e.title_block_restricted);
pair('document descriptors',e=>e.document);
pair('pdf content streams',e=>e.pdf);
pair('export manifests',e=>e.export);
pair('export sets',e=>e.export_set);
pair('staleness verdicts',e=>[e.staleness,e.impact,e.regenerate]);
pair('model hashes',e=>e.model_hash);
pair('model immutability',e=>e.model_untouched);

const one=(label,key)=>{
  const same=S(J[key])===S(P[key]);
  if(!same) console.log('✗ '+label.toUpperCase()+' DISAGREEMENT');
  console.log(label+': '+(same?1:0)+'/1'); };
one('specification view','__spec');
one('safety verdicts','__safety');
one('stated value readings','__stated');

console.log('\nDOCS PARITY: '+(keys.length-bad)+'/'+keys.length+' byte-identical');
if(bad) process.exit(1);
