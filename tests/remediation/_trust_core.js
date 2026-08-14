/* مُحمِّل النواة النقيّة من الصفحة المشحونة نفسها.
   لا نسخة ثانية من الشيفرة في الاختبارات: نستخرج الكتلة المكتوبة يدوياً من
   public/index.html ونشغّلها كما هي، فما نختبره هو ما يُنشَر بالضبط. */
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname,'..','..');
const PAGE=path.join(ROOT,'public','index.html');
const BEGIN='/* ===== ACS PRODUCTION TRUST CORE (hand-written · pure';
const END='/* ===== END ACS PRODUCTION TRUST CORE ===== */';
function load(){
  const src=fs.readFileSync(PAGE,'utf8');
  const i=src.indexOf(BEGIN), j=src.indexOf(END);
  if(i<0||j<0) throw new Error('the production-trust core block is not in the shipped page');
  if(src.split(BEGIN).length-1!==1||src.split(END).length-1!==1)
    throw new Error('the production-trust core markers are not unique');
  const block=src.slice(i, j+END.length);
  /* eslint-disable no-new-func */
  const f=new Function(block+'\n;return {CORE:ACS_TRUST_CORE, T:ACS_TRUST, SRC:'
                       +JSON.stringify(block.length)+'};');
  const r=f();
  return {T:r.T, factory:r.CORE, block:block, page:src};
}
module.exports={load, ROOT, PAGE, BEGIN, END};
