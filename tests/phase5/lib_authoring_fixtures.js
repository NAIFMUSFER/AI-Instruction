/* أدوات مشتركة لاختبارات المرحلة 5: تحميل التجهيزات واستبدال علامات القيم
   غير المنتهية بقيم حقيقية (JSON لا يستطيع حمل NaN أو Infinity). */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
function load(){
  return JSON.parse(fs.readFileSync(_np.join(HERE,'fixtures','authoring_scenarios.json'),'utf8')); }
function hydrate(v){
  if(Array.isArray(v)) return v.map(hydrate);
  if(v&&typeof v==='object'){ const o={};
    /* التعيين المباشر لمفتاح __proto__ يضبط النموذج الأولي ويبتلع المفتاح،
       فتضيع الحالة الخصومية نفسها. التعريف الصريح يحفظه خاصّيةً ذاتية. */
    Object.keys(v).forEach(k=>{ Object.defineProperty(o,k,
      {value:hydrate(v[k]),enumerable:true,writable:true,configurable:true}); });
    return o; }
  if(v==='NaN_MARKER') return NaN;
  if(v==='INF_MARKER') return Infinity;
  if(v==='NEG_INF_MARKER') return -Infinity;
  return v; }
module.exports={load,hydrate,ROOT,HERE};
