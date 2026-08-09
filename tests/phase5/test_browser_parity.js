/* ============================================================================
   المرحلة 5 — التحقّق في متصفّح حقيقي (§93)
   يشغّل كل جناح تأليف داخل Chromium عبر Playwright ويقارن النتيجة بنتيجة Node،
   ثمّ يشغّل جسم التكافؤ نفسه داخل الصفحة ويقارن مخرجاته ببايثون بايتاً ببايت.
   إن تعذّر تشغيل Chromium تُعلَن الحالة NOT VERIFIED — لا يُختلق نجاح.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const BUILD=path.join(ROOT,'tests','phase3','lib','build_browser_page.js');
const PY=path.join(os.tmpdir(),'acs_parity_authoring_py.json');

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

let chromium=null;
try{ chromium=require('playwright').chromium; }catch(e){ chromium=null; }
if(!chromium){
  console.log('\nAUTHORING BROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  Playwright is not installed in this environment; no browser claim is made.');
  process.exit(0);
}

/* test_browser.js يفحص واجهة المطوّر التي لا توجد إلا داخل صفحة، فعدده يزيد
   في المتصفّح عمداً؛ بقيّة الأجنحة يجب أن تتطابق بالضبط. */
const SUITES=[
  ['test_authoring.js',true],['test_commands.js',true],['test_transaction.js',true],
  ['test_revision.js',true],['test_ai_boundary.js',true],['test_integration.js',true],
  ['test_immutability.js',false],['test_adversarial.js',true],['test_browser.js',false]];

function nodeCounts(suite){
  const out=execFileSync(process.execPath,[RUN,path.join(HERE,suite)],
    {encoding:'utf8',maxBuffer:1<<28});
  const m=/([A-Z /]+): (\d+) passed, (\d+) failed/.exec(out);
  return m?{pass:Number(m[2]),fail:Number(m[3])}:null;
}

(async()=>{
  const browser=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
  console.log('\n== EVERY AUTHORING SUITE RUNS IN A REAL BROWSER ENGINE ==');
  for(const entry of SUITES){
    const suite=entry[0], exact=entry[1];
    const nodeR=(suite==='test_immutability.js')?null:nodeCounts(suite);
    execFileSync(process.execPath,[BUILD,path.join(HERE,suite)],{stdio:'pipe'});
    const page=path.join(os.tmpdir(),path.basename(suite,'.js')+'_browser.html');
    const pg=await browser.newPage();
    const errs=[];
    pg.on('pageerror',e=>errs.push(e.message));
    pg.setDefaultTimeout(300000); pg.setDefaultNavigationTimeout(300000);
    await pg.goto('file://'+page,{waitUntil:'load',timeout:300000});
    await pg.waitForFunction('window.__RESULT',{timeout:300000});
    const br=await pg.evaluate('window.__RESULT');
    await pg.close();
    chk(suite+': the page raised no uncaught error', errs.length===0, errs.join(' | '));
    chk(suite+': the browser reported a real result',
        !!br&&typeof br.pass==='number'&&br.pass>0, JSON.stringify(br));
    chk(suite+': the browser passed every assertion', !!br&&br.fail===0, JSON.stringify(br));
    if(exact) chk(suite+': the browser and Node agree on the assertion counts',
      !!nodeR&&!!br&&nodeR.pass===br.pass&&nodeR.fail===br.fail,
      'node='+JSON.stringify(nodeR)+' browser='+JSON.stringify(br));
    else if(nodeR) chk(suite+': the browser runs at least everything Node ran',
      !!br&&br.pass>=nodeR.pass,
      'node='+JSON.stringify(nodeR)+' browser='+JSON.stringify(br));
  }

  console.log('\n== THE BROWSER RESULT AGREES WITH PYTHON BYTE FOR BYTE ==');
  execFileSync('python3',[path.join(HERE,'parity','py_authoring.py')],
    {env:Object.assign({},process.env,{ACS_PARITY_AUTHORING_PY:PY}),stdio:'pipe'});
  execFileSync(process.execPath,[BUILD,path.join(HERE,'parity','js_authoring_body.js')],
    {stdio:'pipe'});
  const parityPage=path.join(os.tmpdir(),'js_authoring_body_browser.html');
  const pg=await browser.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push(e.message));
  pg.setDefaultTimeout(300000); pg.setDefaultNavigationTimeout(300000);
  await pg.goto('file://'+parityPage,{waitUntil:'load',timeout:300000});
  await pg.waitForFunction('window.__WROTE__&&Object.keys(window.__WROTE__).length>0',
    {timeout:300000});
  const wrote=await pg.evaluate('window.__WROTE__');
  await pg.close();
  await browser.close();

  chk('the parity body ran in the browser without an uncaught error',
      errs.length===0, errs.join(' | '));
  const keyPath=Object.keys(wrote||{})[0];
  chk('the browser produced an authoring parity document', !!keyPath);
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
      for(let i=0;i<Math.max(a.length,b.length);i++) if(a[i]!==b[i]){
        console.log('    browser:',a.slice(Math.max(0,i-110),i+110));
        console.log('    python :',b.slice(Math.max(0,i-110),i+110));
        break; } } });
  chk('the browser and python carry the same keys',
      JSON.stringify(Object.keys(B).sort())===JSON.stringify(Object.keys(P).sort()));
  chk('the comparison covers every scenario', keys.length>=50, String(keys.length));
  chk('every scenario is byte-identical between the browser and python',
      bad===0, bad+' of '+keys.length+' differ');
  const scen=keys.filter(k=>k.indexOf('__')!==0);
  chk('command hashes computed in the browser match python',
      scen.every(k=>B[k].command_hash===P[k].command_hash));
  chk('candidate model hashes computed in the browser match python',
      scen.every(k=>((B[k].preview||{}).preview||{}).candidate_model_hash
        ===((P[k].preview||{}).preview||{}).candidate_model_hash));
  chk('committed revision ids computed in the browser match python',
      scen.every(k=>B[k].commit_revision===P[k].commit_revision));

  console.log('\n──────────────────────────────────────────────');
  console.log('AUTHORING BROWSER PARITY: '+pass+' passed, '+fail+' failed');
  process.exit(fail?1:0);
})().catch(e=>{ console.log('  ✗ browser parity aborted:',e&&e.message);
  console.log('\nAUTHORING BROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  process.exit(1); });
