/* أدوات مشتركة لاختبارات المرحلة 8 في جافاسكربت.
   نفس النماذج التي يقرأها lib_bim_fixtures.py حرفاً بحرف. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
function models(){
  const b=JSON.parse(fs.readFileSync(
    _np.join(ROOT,'tests','phase3','fixtures','base_fixtures.json'),'utf8'));
  const r=JSON.parse(fs.readFileSync(
    _np.join(ROOT,'tests','phase7','fixtures','render_fixtures.json'),'utf8'));
  Object.keys(r).forEach(k=>{ b[k]=r[k]; });
  return b; }
/* التمثيل المرحلي المشترك: يكتبه جانب بايثون لأن تحليل STEP يعمل هناك وحده،
   وهذا الحدّ معلَن في المواصفة وفي التقرير ولا يُموّه. */
function staging(){
  const p=(process.env&&process.env.ACS_PARITY_BIM_STAGING)
    ||_np.join(HERE,'fixtures','staging_parity.json');
  return JSON.parse(fs.readFileSync(p,'utf8')); }
module.exports={models,staging,ROOT,HERE};
