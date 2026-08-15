/* أدوات مشتركة لاختبارات المرحلة 6. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
function models(){
  return JSON.parse(fs.readFileSync(
    _np.join(ROOT,'tests','phase3','fixtures','base_fixtures.json'),'utf8')); }
function mep(){
  return JSON.parse(fs.readFileSync(
    _np.join(ROOT,'tests','phase3','fixtures','mep_fixtures.json'),'utf8')).models; }
module.exports={models,mep,ROOT,HERE};
