/* ============================================================================
   المرحلة 4 — تكافؤ المتصفّح الحقيقي
   تشغّل كل جناح في Chromium حقيقي عبر Playwright وتقارن النتيجة بنتيجة Node،
   ثمّ تشغّل جسم التكافؤ نفسه داخل الصفحة وتقارن مخرجاته ببايثون بايتاً ببايت.
   إن تعذّر تشغيل Chromium تُعلَن الحالة NOT VERIFIED — لا يُختلق نجاح.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const BUILD=path.join(ROOT,'tests','phase3','lib','build_browser_page.js');
const PY=path.join(os.tmpdir(),'acs_parity_runtime_py.json');
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js):
   النداء المباشر chromium.launch() يطلب البناء الذي تتوقّعه نسخة
   Playwright بالرقم، فينجح حيث جرى `playwright install` ويفشل حيث
   تحمل الصورة بناءً آخر. المُحدِّد يجيب السؤال مرّة واحدة لكل بيئة. */
const PW=require(path.join(ROOT,'tools','pw_chromium.js'));

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

let chromium=null;
try{ chromium=require('playwright').chromium; }catch(e){ chromium=null; }
if(!chromium){
  console.log('\nBROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  Playwright is not installed in this environment; no browser claim is made.');
  process.exit(0);
}

const SUITES=['test_runtime.js','test_navigation.js','test_collision.js',
  'test_portals.js','test_selection.js','test_visibility.js','test_measurement.js',
  'test_immutability.js','test_adversarial.js'];

function nodeCounts(suite){
  const out=execFileSync(process.execPath,[RUN,path.join(HERE,suite)],
    {encoding:'utf8',maxBuffer:1<<28});
  const m=/([A-Z ]+): (\d+) passed, (\d+) failed/.exec(out);
  return m?{pass:Number(m[2]),fail:Number(m[3])}:null;
}

(async()=>{
const browser=await PW.launch();  console.log('\n== EVERY SUITE RUNS IN A REAL BROWSER ENGINE ==');
  for(const suite of SUITES){
    const nodeR=nodeCounts(suite);
    execFileSync(process.execPath,[BUILD,path.join(HERE,suite)],{stdio:'pipe'});
    const page=path.join(os.tmpdir(),path.basename(suite,'.js')+'_browser.html');
    const pg=await browser.newPage();
    const errs=[];
    pg.on('pageerror',e=>errs.push(e.message));
    pg.setDefaultTimeout(240000); pg.setDefaultNavigationTimeout(240000);
    await pg.goto('file://'+page,{waitUntil:'load',timeout:240000});
    await pg.waitForFunction('window.__RESULT',{timeout:240000});
    const br=await pg.evaluate('window.__RESULT');
    await pg.close();
    chk(suite+': the page raised no uncaught error', errs.length===0, errs.join(' | '));
    chk(suite+': the browser run reported a real result',
        !!br&&typeof br.pass==='number'&&br.pass>0, JSON.stringify(br));
    chk(suite+': the browser passed every assertion', !!br&&br.fail===0,
        JSON.stringify(br));
    chk(suite+': the browser and Node agree on the assertion counts',
        !!nodeR&&!!br&&nodeR.pass===br.pass&&nodeR.fail===br.fail,
        'node='+JSON.stringify(nodeR)+' browser='+JSON.stringify(br));
  }

  console.log('\n== THE BROWSER RESULT AGREES WITH PYTHON BYTE FOR BYTE ==');
  execFileSync('python',[path.join(HERE,'parity','py_runtime.py')],
    {env:Object.assign({},process.env,{ACS_PARITY_RUNTIME_PY:PY}),stdio:'pipe'});
  const body=path.join(HERE,'parity','js_runtime_body.js');
  execFileSync(process.execPath,[BUILD,body],{stdio:'pipe'});
  const parityPage=path.join(os.tmpdir(),'js_runtime_body_browser.html');
  const pg=await browser.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push(e.message));
  pg.setDefaultTimeout(240000); pg.setDefaultNavigationTimeout(240000);
  await pg.goto('file://'+parityPage,{waitUntil:'load',timeout:240000});
  await pg.waitForFunction('window.__WROTE__&&Object.keys(window.__WROTE__).length>0',
    {timeout:240000});
  const wrote=await pg.evaluate('window.__WROTE__');
  await pg.close();
  await browser.close();

  chk('the parity body ran in the browser without an uncaught error',
      errs.length===0, errs.join(' | '));
  const keyPath=Object.keys(wrote||{})[0];
  chk('the browser produced a parity document', !!keyPath);
  const B=JSON.parse(wrote[keyPath]);
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
    if(v&&typeof v==='object'){ const o={};
      Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
    return v; };
  const keys=Array.from(new Set(Object.keys(B).concat(Object.keys(P)))).sort();
  let bad=0;
  keys.forEach(function(k){
    const a=JSON.stringify(canon(B[k])), b=JSON.stringify(canon(P[k]));
    if(a!==b){ bad++;
      for(let i=0;i<Math.max(a.length,b.length);i++){
        if(a[i]!==b[i]){
          console.log('    browser:',a.slice(Math.max(0,i-110),i+110));
          console.log('    python :',b.slice(Math.max(0,i-110),i+110));
          break; } } } });
  chk('the browser and python carry the same scenario keys',
      JSON.stringify(Object.keys(B).sort())===JSON.stringify(Object.keys(P).sort()));
  chk('the comparison is not vacuous — it covers every scenario',
      keys.length>=10, String(keys.length));
  chk('every scenario is byte-identical between the browser and python',
      bad===0, bad+' of '+keys.length+' differ');
  const scenes=keys.filter(k=>k.indexOf('__')!==0);
  chk('at least one browser-compiled scene carries real geometry',
      scenes.some(k=>(B[k].scene.objects||[]).length>20));
  chk('scene signatures computed in the browser match python',
      scenes.every(k=>B[k].scene.source_signature===P[k].scene.source_signature));
  chk('measurement identifiers computed in the browser match python',
      scenes.every(k=>{
        const j=(B[k].measure_width||{}).measurement;
        const p=(P[k].measure_width||{}).measurement;
        return (!j&&!p)||(!!j&&!!p&&j.measurement_id===p.measurement_id); }));

  console.log('\n──────────────────────────────────────────────');
  console.log('BROWSER PARITY: '+pass+' passed, '+fail+' failed');
  process.exit(fail?1:0);
})().catch(e=>{ console.log('  ✗ browser parity aborted:',e&&e.message);
  console.log('\nBROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  process.exit(1); });
