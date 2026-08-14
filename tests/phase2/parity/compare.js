/* مقارنة قانونية بين مخرجات بايثون وجافاسكربت لطبقة واحدة. */
const fs=require('fs'), os=require('os'), path=require('path');
const layer=process.argv[2];
const JS=process.env.ACS_PARITY_JS||path.join(os.tmpdir(),'acs_parity_js_'+layer+'.json');
const PY=process.env.ACS_PARITY_PY||path.join(os.tmpdir(),'acs_parity_py_'+layer+'.json');
const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
  if(v&&typeof v==='object'){const o={};Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);});return o;}
  return v; };
const J=JSON.parse(fs.readFileSync(JS,'utf8')), P=JSON.parse(fs.readFileSync(PY,'utf8'));
const keys=Array.from(new Set(Object.keys(J).concat(Object.keys(P)))).sort();
/* عدم الخواء: مقارنة بلا مجموعات ليست نجاحاً بل غياب فحص. لكل طبقة حدّ أدنى
   معلن هو العدد المُنتَج فعلاً اليوم — نقصانه يعني أن جانباً توقّف عن الكتابة
   أو أن ملفّاً قديماً في /tmp قُرئ، وكلاهما فشل لا مرور. */
const MIN={arch:23,struct:13,mep:13,fls:15,ing:30,occ:27,rev:16,rules:28,
  dist:26,coord:20};
if(!layer||!(layer in MIN)){
  console.log('✗ unknown parity layer: '+layer+' — declare its minimum in MIN');
  process.exit(2); }
if(keys.length===0){
  console.log('✗ THE COMPARISON SET IS EMPTY — nothing was compared');
  process.exit(2); }
if(keys.length<MIN[layer]){
  console.log('✗ THE COMPARISON IS VACUOUS: '+keys.length+' groups, minimum '
    +MIN[layer]);
  process.exit(2); }
if(Object.keys(J).length===0||Object.keys(P).length===0){
  console.log('✗ ONE SIDE WROTE NOTHING — js:'+Object.keys(J).length
    +' py:'+Object.keys(P).length);
  process.exit(2); }
let bad=0;
keys.forEach(k=>{ if(JSON.stringify(canon(J[k]))!==JSON.stringify(canon(P[k]))){bad++;
  console.log('✗ MISMATCH',k);} });
console.log('not vacuous: '+keys.length+' groups compared (minimum '
  +MIN[layer]+')');
console.log(layer.toUpperCase()+' PARITY: '+(keys.length-bad)+'/'+keys.length+' byte-identical');
process.exit(bad?1:0);
