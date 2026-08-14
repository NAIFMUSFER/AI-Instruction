/* مشغّل موحّد لكل مراحل المستودع: يبني حزمة شيفرة المتصفّح من وحدات
   public/app/ عبر tests/phase3/lib/extract_browser_bundle.js (وهو بدوره يقرأ
   من tests/lib/app_source.js وحدها، لا من نصّ الصفحة كما كان قبل F-09)، ثم
   يشغّل ملفّ الاختبار في نطاق واحد معها بـ __dirname الحقيقي للملفّ. */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const EXTRACT=path.join(ROOT,'tests','phase3','lib','extract_browser_bundle.js');
function buildBundle(){
  const out=path.join(os.tmpdir(),'acs_browser_bundle.js');
  execFileSync(process.execPath,[EXTRACT],
    {env:Object.assign({},process.env,{ACS_BUNDLE:out}),stdio:'pipe'});
  return out; }
function run(testFile){
  const abs=path.isAbsolute(testFile)?testFile:path.resolve(ROOT,testFile);
  if(!fs.existsSync(abs)) throw new Error('test file not found: '+abs);
  const bundle=fs.readFileSync(buildBundle(),'utf8');
  const body=fs.readFileSync(abs,'utf8');
  const fn=new Function('__dirname','__filename','require','process','console',
                        'module','exports', bundle+'\n;\n'+body);
  fn(path.dirname(abs),abs,require,process,console,{exports:{}},{}); }
module.exports={run,buildBundle,ROOT};
if(require.main===module){
  const a=process.argv[2];
  if(!a){ console.error('usage: node tests/lib/run.js <path/to/test.js>'); process.exit(2); }
  run(a); }
