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
/* صفحة التطبيق نفسها: فحص واجهة المطوّر يقرأ الكتلة المحقونة منها مباشرةً */
{ const t=fs.readFileSync(path.join(REPO,'public','index.html'),'utf8');
  files[path.join(REPO,'public','index.html')]=t; files['public/index.html']=t; }
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
/* كتلة DOM لمساحة العمل تُؤخذ من نفس المصدر المولَّد في الصفحة، لا نسخة ثانية،
   كي تعمل فحوص الواجهة داخل الصفحة كما تعمل في التطبيق */
let wsDom='', wsCss='';
{ const page=fs.readFileSync(path.join(REPO,'public','index.html'),'utf8');
  const db='<!-- ===== ACS WORKSPACE DOM (generated) ===== -->';
  const de='<!-- ===== END ACS WORKSPACE DOM ===== -->';
  if(page.indexOf(db)>=0&&page.indexOf(de)>=0)
    wsDom=page.slice(page.indexOf(db)+db.length,page.indexOf(de));
  const cb='/* ===== ACS WORKSPACE STYLES (generated) ===== */';
  const ce='/* ===== END ACS WORKSPACE STYLES ===== */';
  if(page.indexOf(cb)>=0&&page.indexOf(ce)>=0)
    wsCss=page.slice(page.indexOf(cb)+cb.length,page.indexOf(ce));
  /* كتلة لوحة التصوير تُؤخذ من نفس المصدر المولَّد أيضاً */
  const rb='<!-- ===== ACS RENDER DOM (generated) ===== -->';
  const re_='<!-- ===== END ACS RENDER DOM ===== -->';
  if(page.indexOf(rb)>=0&&page.indexOf(re_)>=0)
    wsDom+=page.slice(page.indexOf(rb)+rb.length,page.indexOf(re_));
  const rcb='/* ===== ACS RENDER STYLES (generated) ===== */';
  const rce='/* ===== END ACS RENDER STYLES ===== */';
  if(page.indexOf(rcb)>=0&&page.indexOf(rce)>=0)
    wsCss+=page.slice(page.indexOf(rcb)+rcb.length,page.indexOf(rce));
  /* كتلة لوحة التبادل تُؤخذ من نفس المصدر المولَّد كذلك — لا نسخة ثانية */
  const bb='<!-- ===== ACS BIM DOM (generated) ===== -->';
  const be='<!-- ===== END ACS BIM DOM ===== -->';
  if(page.indexOf(bb)>=0&&page.indexOf(be)>=0)
    wsDom+=page.slice(page.indexOf(bb)+bb.length,page.indexOf(be));
  const bcb='/* ===== ACS BIM STYLES (generated) ===== */';
  const bce='/* ===== END ACS BIM STYLES ===== */';
  if(page.indexOf(bcb)>=0&&page.indexOf(bce)>=0)
    wsCss+=page.slice(page.indexOf(bcb)+bcb.length,page.indexOf(bce));
  /* كتلة لوحة التوثيق تُؤخذ من نفس المصدر المولَّد كذلك */
  const db2='<!-- ===== ACS DOCS DOM (generated) ===== -->';
  const de2='<!-- ===== END ACS DOCS DOM ===== -->';
  if(page.indexOf(db2)>=0&&page.indexOf(de2)>=0)
    wsDom+=page.slice(page.indexOf(db2)+db2.length,page.indexOf(de2));
  const dcb='/* ===== ACS DOCS STYLES (generated) ===== */';
  const dce='/* ===== END ACS DOCS STYLES ===== */';
  if(page.indexOf(dcb)>=0&&page.indexOf(dce)>=0)
    wsCss+=page.slice(page.indexOf(dcb)+dcb.length,page.indexOf(dce)); }
const html='<!doctype html><meta charset="utf-8"><title>'+suite+'</title>\n'
  +'<style>\n'+wsCss+'\n</style>\n'
  +'<body><div id="reportBox"></div>\n'+wsDom+'\n<script>\n'
  +body+'<\/script>\n';
const outHtml=path.join(os.tmpdir(),path.basename(suite,'.js')+'_browser.html');
fs.writeFileSync(outHtml,html);
console.log('built',outHtml,html.length,'bytes');
module.exports={outHtml};
