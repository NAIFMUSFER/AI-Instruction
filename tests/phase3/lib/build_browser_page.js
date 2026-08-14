/* يبني صفحة اختبار حقيقية للمتصفّح من نفس مصدر المتصفّح (pure_audit) ونفس ملف
   الاختبار الذي يُشغَّل في Node — بلا نسخة ثانية من المنطق. */
const fs=require('fs'),path=require('path'),os=require('os');
const {execFileSync}=require('child_process');
const suite=process.argv[2];
const HERE=__dirname, REPO=path.resolve(HERE,'..','..','..');
/* مجلّد الجناح يُشتقّ من مسار الملفّ نفسه، كي تعمل أجنحة أي مرحلة لا المرحلة 3 وحدها */
const PHASE=path.isAbsolute(suite)?path.dirname(suite):path.resolve(HERE,'..');
const FIXDIR=path.join(PHASE,'fixtures');
const files={};
/* تجهيزات المرحلة 3 تأتي من المستودع، وتُقدَّم للصفحة بالمسارات التي يطلبها الاختبار */
/* تجهيزات كل مرحلة تُقدَّم بمسارها الحقيقي وباسمها المجرّد معاً، كي يعمل
   أي اختبار أياً كان المجلّد الذي يقرأ منه */
const TESTS=path.resolve(REPO,'tests');
fs.readdirSync(TESTS).forEach(d=>{
  const fd=path.join(TESTS,d,'fixtures');
  if(!fs.existsSync(fd)) return;
  fs.readdirSync(fd).filter(f=>/\.json$/.test(f)).forEach(f=>{
    const t=fs.readFileSync(path.join(fd,f),'utf8');
    files[path.join(fd,f)]=t; if(!(f in files)) files[f]=t; }); });
/* صفحة التطبيق نفسها: القشرة — العلامة وخريطة الاستيراد. تبقى بالمفتاحين
   اللذين تطلبهما الاختبارات التي تفحص العلامة (معرّفات العناصر، سمات الوصول). */
{ const t=fs.readFileSync(path.join(REPO,'public','index.html'),'utf8');
  files[path.join(REPO,'public','index.html')]=t; files['public/index.html']=t; }
/* وشيفرة التطبيق نفسها: بعد F-09 صارت وحدات ES تحت public/app/. كل ملفّ يُقدَّم
   بمساره المطلق وبمساره النسبي من جذر المستودع، كي يقرأ الاختبار
   public/app/generated/*.js داخل الصفحة كما يقرأه في Node بلا فرع ثانٍ. */
(function addAppTree(dir){
  fs.readdirSync(dir).sort().forEach(f=>{
    const p=path.join(dir,f);
    if(fs.statSync(p).isDirectory()) return addAppTree(p);
    const t=fs.readFileSync(p,'utf8');
    files[p]=t; files[path.relative(REPO,p).split(path.sep).join('/')]=t; }); })(
  path.join(REPO,'public','app'));
/* المواصفات القانونية تُقدَّم بكل صيغة مسار قد يطلبها اختبار (اختبار الانحراف) */
fs.readdirSync(REPO).filter(f=>/^acs_.*\.json$/.test(f)).forEach(f=>{
  const t=fs.readFileSync(path.join(REPO,f),'utf8');
  files[f]=t; files['./'+f]=t; files[path.join(REPO,f)]=t;
  files[path.join(PHASE,'..','..',f)]=t; });
fs.readdirSync(REPO).filter(f=>/^acs_.*\.json$/.test(f)).forEach(f=>{
  const t=fs.readFileSync(path.join(REPO,f),'utf8');
  files[f]=t; files['./'+f]=t; files[path.join(REPO,f)]=t; });
/* مصادر بايثون تُقدَّم للصفحة أيضاً: بعض الفحوص تقرأ الشيفرة نفسها للتأكّد من
   خلوّها من التنفيذ الديناميكي، وهي فحوص يجب أن تعمل في المتصفّح كما في Node */
fs.readdirSync(REPO).filter(f=>/^acs_.*\.py$/.test(f)).forEach(f=>{
  const t=fs.readFileSync(path.join(REPO,f),'utf8');
  files[f]=t; files['./'+f]=t; files[path.join(REPO,f)]=t; });
/* وحدات مساعدة داخل المستودع (lib_*.js) تُقدَّم للصفحة كي يعمل require المحلّي */
const mods={};
fs.readdirSync(TESTS).forEach(d=>{
  const dd=path.join(TESTS,d);
  if(!fs.statSync(dd).isDirectory()) return;
  fs.readdirSync(dd).filter(f=>/^lib_.*\.js$/.test(f)).forEach(f=>{
    const t=fs.readFileSync(path.join(dd,f),'utf8');
    mods[path.join(dd,f)]={src:t,dir:dd}; mods[f]={src:t,dir:dd}; }); });
const bundlePath=path.join(os.tmpdir(),'acs_browser_bundle.js');
execFileSync(process.execPath,[path.join(HERE,'extract_browser_bundle.js')],
  {env:Object.assign({},process.env,{ACS_BUNDLE:bundlePath}),stdio:'pipe'});
const pure=fs.readFileSync(bundlePath,'utf8');
const testPath=path.isAbsolute(suite)?suite:path.join(PHASE,suite);
let test=fs.readFileSync(testPath,'utf8')
  /* تعريفات الوحدات تُزال: الصفحة تقدّم fs و path من الغلاف نفسه */
  /* أي سطر تعريف وحدات فقط يُزال: الصفحة تقدّم fs و path من الغلاف نفسه */
  .replace(/^\s*const\s+[A-Za-z_$][\w$]*\s*=\s*require\((['"])[^'"]+\1\)\s*(,\s*[A-Za-z_$][\w$]*\s*=\s*require\((['"])[^'"]+\3\)\s*)*;?\s*$/mg,'')
  .replace(/^\s*const\s+\{[^}]*\}\s*=\s*require\(['"][^'"]+['"]\)\s*;?\s*$/mg,'')
  .replace(/^\s*require\(['"][^'"]*\.js['"]\)\s*;?\s*$/mg,'')   // نسخة قديمة مُستبدَلة بـ pure_audit
  .replace(/require\(['"]fs['"]\)/g,'fs');
const shim=`
const __dirname=${JSON.stringify(PHASE)};
const __filename=${JSON.stringify(testPath)};
const _norm=(s)=>{const abs=String(s).charAt(0)==='/';const out=[];
  String(s).split('/').forEach(seg=>{ if(!seg||seg==='.') return;
    if(seg==='..'){ if(out.length&&out[out.length-1]!=='..') out.pop(); else if(!abs) out.push('..'); return; }
    out.push(seg); });
  return (abs?'/':'')+out.join('/');};
const path={resolve:(...p)=>_norm(p.filter(Boolean).join('/')),
  join:(...p)=>_norm(p.filter(Boolean).join('/')),
  dirname:(p)=>_norm(String(p)).split('/').slice(0,-1).join('/')||'/',
  isAbsolute:(p)=>String(p).charAt(0)==='/',
  basename:(p)=>String(p).split('/').pop()};
const __FILES__=${JSON.stringify(files)};
window.__WROTE__={};
const fs={readFileSync:(p)=>{ if(!(p in __FILES__)) throw new Error('ENOENT '+p); return __FILES__[p]; },
          existsSync:(p)=>p in __FILES__,
          writeFileSync:(p,t)=>{ window.__WROTE__[String(p)]=String(t); }};
const process={exit:()=>{},argv:[],env:{}};
const _os={tmpdir:()=>'/tmp'};
const _np=path;
const __MODS__=${JSON.stringify(mods)};
const __MODCACHE__={};
const require=(m)=>{ if(m==='fs') return fs; if(m==='path') return path;
  if(m==='os') return _os;
  const key=(String(m) in __MODS__)?String(m):path.basename(String(m));
  if(key in __MODS__){
    if(!(key in __MODCACHE__)){
      const e=__MODS__[key], module={exports:{}};
      /* لا تُمرَّر fs و path كوسائط: الوحدة نفسها قد تعلنهما بـ const */
      (new Function('module','exports','require','__dirname','__filename',
                    e.src))(module,module.exports,require,e.dir,
                            path.join(e.dir,key));
      __MODCACHE__[key]=module.exports; }
    return __MODCACHE__[key]; }
  throw new Error('no module '+m); };
/* عنصر التقرير الحقيقي في DOM حقيقي — لا نمذجة ولا سلسلة نصّية بديلة */
const __box=document.getElementById('reportBox');
window.__LOG__=[];
(function(){const o=console.log; console.log=function(){ window.__LOG__.push(Array.from(arguments).join(' ')); o.apply(console,arguments); };})();
`;
/* جسم الاختبار يعمل في نطاقه الخاص: بعض الأجنحة تعرّف متغيّرات باسم path
   وغيره، فلا يجوز أن تتصادم مع تعريفات الغلاف */
let body=shim+'\n'+pure+'\n(function(){\n'+test
  +'\nwindow.__RESULT={pass:typeof pass!=="undefined"?pass:null,fail:typeof fail!=="undefined"?fail:null};\n})();\n';
/* أي "</script" داخل نصّ أو JSON يقطع الوسم — نهرّبه دون تغيير قيمة أي سلسلة */
body=body.replace(/<\/script/gi,'<\\/script').replace(/<!--/g,'<\\!--')
         .replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
/* كتل DOM والأنماط تُؤخذ من نفس المصدر المولَّد الذي يشحنه التطبيق، لا نسخة
   ثانية: العلامة من القشرة public/index.html، والأنماط من public/app/styles/app.css
   بعد أن نقل F-09 الوسم <style> المضمَّن إلى ملفّ.
   الغياب لم يعد يُتجاوَز بصمت: صفحة بلا كتلة تجعل فحوص الواجهة تمرّ على فراغ. */
let wsDom='', wsCss='';
{ const shell=fs.readFileSync(path.join(REPO,'public','index.html'),'utf8');
  const appCss=fs.readFileSync(path.join(REPO,'public','app','styles','app.css'),'utf8');
  const PANELS=['WORKSPACE','RENDER','BIM','DOCS','PBR','ARCH DETAIL'];
  const cut=(src,open,close,where)=>{
    const a=src.indexOf(open), b=src.indexOf(close);
    if(a<0||b<a) throw new Error('generated block missing from '+where+': '+open);
    return src.slice(a+open.length,b); };
  PANELS.forEach(name=>{
    wsDom+=cut(shell,'<!-- ===== ACS '+name+' DOM (generated) ===== -->',
                     '<!-- ===== END ACS '+name+' DOM ===== -->',
                     'public/index.html');
    wsCss+=cut(appCss,'/* ===== ACS '+name+' STYLES (generated) ===== */',
                      '/* ===== END ACS '+name+' STYLES ===== */',
                      'public/app/styles/app.css'); }); }
const html='<!doctype html><meta charset="utf-8"><title>'+suite+'</title>\n'
  +'<style>\n'+wsCss+'\n</style>\n'
  +'<body><div id="reportBox"></div>\n'+wsDom+'\n<script>\n'
  +body+'<\/script>\n';
const outHtml=path.join(os.tmpdir(),path.basename(suite,'.js')+'_browser.html');
fs.writeFileSync(outHtml,html);
console.log('built',outHtml,html.length,'bytes');
module.exports={outHtml};
