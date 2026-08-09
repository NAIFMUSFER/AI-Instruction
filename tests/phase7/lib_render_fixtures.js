/* أدوات مشتركة لاختبارات المرحلة 7. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
function base(){ return JSON.parse(fs.readFileSync(
  _np.join(ROOT,'tests','phase3','fixtures','base_fixtures.json'),'utf8')); }
function render(){ return JSON.parse(fs.readFileSync(
  _np.join(HERE,'fixtures','render_fixtures.json'),'utf8')); }
function all(){ const o={}, b=base(), r=render();
  Object.keys(b).forEach(k=>{o[k]=b[k];});
  Object.keys(r).forEach(k=>{o[k]=r[k];});
  return o; }
module.exports={base,render,all,ROOT,HERE};
