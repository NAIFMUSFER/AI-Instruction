/* أدوات مشتركة لاختبارات المرحلة 4: تحميل التجهيزات واستبدال علامات القيم
   غير المنتهية بقيم حقيقية (JSON لا يستطيع حمل NaN أو Infinity). */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
function load(){
  return JSON.parse(fs.readFileSync(_np.join(HERE,'fixtures','runtime_scenarios.json'),'utf8')); }
function hydrate(v){
  if(Array.isArray(v)) return v.map(hydrate);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).forEach(k=>{o[k]=hydrate(v[k]);}); return o; }
  if(v==='NaN_MARKER') return NaN;
  if(v==='INF_MARKER') return Infinity;
  if(v==='NEG_INF_MARKER') return -Infinity;
  return v; }
module.exports={load,hydrate,ROOT,HERE};
