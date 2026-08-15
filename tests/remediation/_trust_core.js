/* مُحمِّل النواة النقيّة من الشيفرة المشحونة نفسها.
   لا نسخة ثانية من الشيفرة في الاختبارات: نقرأ الوحدة المشحونة
   public/app/trust/core.js عبر tests/lib/app_source.js ونشغّل كتلتها كما هي،
   فما نختبره هو ما يُنشَر بالضبط.

   قبل F-09 كانت الكتلة داخل public/index.html؛ بعده صارت وحدة ES مستقلّة.
   الكتلة نفسها لم تتغيّر: نفس العلامتين تحدّانها داخل الوحدة، ونُزيل جُمل
   import/export وحدها بـ stripModuleSyntax فيعود المقطع إلى نطاق واحد. */
const path=require('path');
const AS=require(path.resolve(__dirname,'..','lib','app_source.js'));
const ROOT=AS.ROOT;
const CORE_REL='trust/core.js';
const WIRE_REL='trust/wiring.js';
const CORE_PATH=path.join(AS.APP,'trust','core.js');
const WIRE_PATH=path.join(AS.APP,'trust','wiring.js');
/* تبقى PAGE معرّفة لمن يستوردها: الصفحة ما زالت القشرة التي تشحن الوحدات */
const PAGE=path.join(AS.PUB,'index.html');
const BEGIN='/* ===== ACS PRODUCTION TRUST CORE (hand-written · pure';
const END='/* ===== END ACS PRODUCTION TRUST CORE ===== */';
const WIRE_BEGIN='/* ===== ACS PRODUCTION TRUST WIRING (hand-written';
const WIRE_END='/* ===== END ACS PRODUCTION TRUST WIRING ===== */';

/* يستخرج كتلة محدّدة بعلامتين من نصّ وحدة مشحونة، ويشترط أن تكونا فريدتين. */
function cut(src, begin, end, what){
  const i=src.indexOf(begin), j=src.indexOf(end);
  if(i<0||j<0) throw new Error('the '+what+' block is not in the shipped module');
  if(src.split(begin).length-1!==1||src.split(end).length-1!==1)
    throw new Error('the '+what+' markers are not unique');
  return src.slice(i, j+end.length);
}

function moduleText(rel){
  const mods=AS.modules();
  if(!mods[rel]) throw new Error('the shipped module is missing: public/app/'+rel);
  return AS.stripModuleSyntax(mods[rel], 'public/app/'+rel);
}

/* كتلة التوصيل المشحونة (DOM/IndexedDB) — يستعملها فاحص الإتاحة في متصفّح حقيقي */
function wiringBlock(){
  return cut(moduleText(WIRE_REL), WIRE_BEGIN, WIRE_END, 'production-trust wiring');
}

function coreBlock(){
  return cut(moduleText(CORE_REL), BEGIN, END, 'production-trust core');
}

function load(){
  const block=coreBlock();
  /* eslint-disable no-new-func */
  const f=new Function(block+'\n;return {CORE:ACS_TRUST_CORE, T:ACS_TRUST, SRC:'
                       +JSON.stringify(block.length)+'};');
  const r=f();
  /* `page` كان قبل F-09 نصّ الصفحة الواحدة التي تحمل العلامة والشيفرة معاً.
     بديله المطابق دلالياً بعد التفكيك هو القشرة + كل شيفرة التطبيق. */
  return {T:r.T, factory:r.CORE, block:block, page:AS.pageText(),
          shell:AS.shell(), app:AS.appText(), wiring:wiringBlock()};
}

module.exports={load, coreBlock, wiringBlock, moduleText, ROOT, PAGE,
                CORE_PATH, WIRE_PATH, CORE_REL, WIRE_REL,
                BEGIN, END, WIRE_BEGIN, WIRE_END};
