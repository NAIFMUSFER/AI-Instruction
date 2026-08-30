/* ============================================================================
   المرحلة 6 — التحقّق المتجاوب و RTL واللقطات في Chromium حقيقي (§87/§88/§93/§94)
   إن تعذّر Chromium تُعلَن الحالة NOT VERIFIED — لا يُختلق نجاح.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const BUILD=path.join(ROOT,'tests','phase3','lib','build_browser_page.js');
const SHOTS=path.join(HERE,'screenshots');
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
  console.log('\nRESPONSIVE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  Playwright is not installed here; no browser or screenshot claim is made.');
  process.exit(0);
}
if(!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS,{recursive:true});

/* صفحة سيناريو تُبنى من نفس المصدر المولَّد — لا نسخة ثانية من الواجهة */
const DRIVER=path.join(os.tmpdir(),'acs_ws_driver.js');
fs.writeFileSync(DRIVER,
  "const fs=require('fs'), _np=require('path');\n"+
  "const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');\n"+
  "let pass=0,fail=0;\n"+
  "const chk=(n,c)=>{c?pass++:fail++;};\n"+
  /* الغلاف يقدّم التجهيزات باسمها المجرّد أيضاً، وهو ما يعمل أياً كان مجلّد
     السائق — لا نسخة ثانية من التجهيزات ولا مسار مُختلق */
  "const FX=JSON.parse(fs.readFileSync('base_fixtures.json','utf8'));\n"+
  "const C=o=>JSON.parse(JSON.stringify(o));\n"+
  "window.__WS_READY__=false;\n"+
  "WS.init(auCreateProject(C(FX.villa),'bld_0','IMPORT',null));\n"+
  "WS.open();\n"+
  "WS.ui().tree_expanded=['project','site','bld_0','bld_0.flr_0','bld_0.flr_0.spaces'];\n"+
  "WS.render();\n"+
  "window.__WS__=WS;\n"+
  "chk('ready',true);\n"+
  "window.__WS_READY__=true;\n",'utf8');

const WIDTHS=[360,390,430,768,1024,1440,1920];

/* الصفحة المولَّدة ضخمة (‏~8MB) والتحليل بطيء، والمهلة الافتراضية 30s لا تكفي.
   المهلة تُضبط على مستوى الصفحة لأن waitForFunction يأخذ الوسيط الثاني كقيمة
   تُمرَّر للدالة لا كخيارات — تمرير {timeout} هناك لا أثر له. */
async function open(browser,w,h,pageFile){
  const pg=await browser.newPage({viewport:{width:w,height:h}});
  pg.setDefaultTimeout(300000);
  pg.setDefaultNavigationTimeout(300000);
  const errs=[];
  pg.on('pageerror',e=>errs.push(e&&e.message?e.message:String(e)));
  await pg.goto('file://'+pageFile,{waitUntil:'load'});
  try{ await pg.waitForFunction('window.__WS_READY__===true'); }
  catch(e){ throw new Error('driver never became ready at '+w+'px'
    +(errs.length?' — page errors: '+errs.join(' | '):' — no page error was raised')); }
  return {pg:pg,errs:errs};
}

(async()=>{
  execFileSync(process.execPath,[BUILD,DRIVER],{stdio:'pipe'});
  const page=path.join(os.tmpdir(),'acs_ws_driver_browser.html');
  const browser=await PW.launch();

  console.log('\n== §2/§87 — RESPONSIVE LAYOUT AT EVERY TESTED WIDTH ==');
  for(const w of WIDTHS){
    const o=await open(browser,w,800,page); const pg=o.pg, errs=o.errs;
    const m=await pg.evaluate(`(()=>{
      const ws=document.getElementById('acsWorkspace');
      const r=ws.getBoundingClientRect();
      const view=document.getElementById('wsViewport').getBoundingClientRect();
      const btns=Array.prototype.slice.call(document.querySelectorAll('.ws-top .ws-btn'));
      const minBtn=btns.length?Math.min.apply(null,btns.map(b=>
        Math.min(b.getBoundingClientRect().width,b.getBoundingClientRect().height))):0;
      return {docW:document.documentElement.scrollWidth,
        winW:window.innerWidth, wsW:r.width, viewW:view.width, viewH:view.height,
        rows:document.querySelectorAll('#wsTree [data-ws-node]').length,
        minBtn:minBtn,
        treeVisible:document.getElementById('wsTreePane').getBoundingClientRect().width>0,
        inspVisible:document.getElementById('wsInspPane').getBoundingClientRect().width>0,
        btnCount:btns.length,
        topScrollW:document.querySelector('.ws-top').scrollWidth,
        topClientW:document.querySelector('.ws-top').clientWidth,
        topOverflowX:getComputedStyle(document.querySelector('.ws-top')).overflowX};
    })()`);
    chk(w+'px: the page raises no uncaught error', errs.length===0, errs.join(' | '));
    chk(w+'px: there is no horizontal page overflow',
        m.docW<=m.winW+1, 'doc '+m.docW+' > win '+m.winW);
    chk(w+'px: the workspace fits the viewport width', m.wsW<=m.winW+1);
    chk(w+'px: the 3D viewport is usable', m.viewW>100&&m.viewH>100,
        m.viewW+'x'+m.viewH);
    chk(w+'px: the project tree rendered real rows', m.rows>0);
    if(w<1024){
      chk(w+'px: the viewport takes essentially the full width',
          m.viewW>=m.winW-2, m.viewW+' of '+m.winW);
    } else {
      chk(w+'px: all three panels are docked',
          m.treeVisible&&m.inspVisible&&m.viewW>200); }
    if(w<=430) chk(w+'px: touch targets meet the declared minimum',
      m.minBtn>=44-0.5, String(m.minBtn));
    /* لا يكفي غياب التمرير الأفقي للصفحة: لو قُصّ شريط الأدوات لصارت أزرار
       غير قابلة للوصول أصلاً. نتحقّق أنّ كل زرّ يُبلَغ إمّا لأنّه ظاهر أو
       لأنّ الشريط نفسه قابل للتمرير. */
    chk(w+'px: every toolbar control stays reachable',
        m.topScrollW<=m.topClientW+1
        ||m.topOverflowX==='auto'||m.topOverflowX==='scroll',
        'scroll '+m.topScrollW+' client '+m.topClientW+' overflowX '+m.topOverflowX);
    await pg.close(); }

  console.log('\n== §88 — ARABIC RTL ==');
  {
    const o=await open(browser,390,800,page); const pg=o.pg, errs=o.errs;
    const r=await pg.evaluate(`(()=>{
      const out={};
      window.__WS__.setLanguage('ar');
      out.dir=document.documentElement.getAttribute('dir');
      out.lang=document.documentElement.getAttribute('lang');
      window.__WS__.select('g.majlis');
      out.selected=window.__WS__.ui().selected_id;
      const tree=document.getElementById('wsTreePane').getBoundingClientRect();
      const insp=document.getElementById('wsInspPane').getBoundingClientRect();
      const row=document.querySelector('#wsTree .ws-row');
      const cs=row?getComputedStyle(row):null;
      out.rowPadStart=cs?cs.paddingInlineStart:null;
      out.treeRight=tree.right; out.winW=window.innerWidth;
      out.docW=document.documentElement.scrollWidth;
      out.rows=document.querySelectorAll('#wsTree [data-ws-node]').length;
      out.inspSections=document.querySelectorAll('#wsInsp [data-ws-section]').length;
      window.__WS__.issues();
      out.issueCats=document.querySelectorAll('#wsModalBody [data-ws-issue-cat]').length;
      window.__WS__.closeModal();
      window.__WS__.history();
      out.histRows=document.querySelectorAll('#wsModalBody [data-ws-rev]').length;
      window.__WS__.closeModal();
      window.__WS__.assistant();
      out.aiOpen=document.getElementById('wsModal').classList.contains('on');
      window.__WS__.closeModal();
      window.__WS__.exportPanel();
      out.exportRows=document.querySelectorAll('#wsModalBody [data-ws-export]').length;
      window.__WS__.closeModal();
      window.__WS__.references();
      out.refOpen=document.getElementById('wsModal').classList.contains('on');
      window.__WS__.closeModal();
      const un=document.querySelectorAll('#wsInsp [data-ws-unknown]');
      out.unknownTexts=Array.prototype.slice.call(un).map(e=>e.textContent);
      out.viewport=!!document.getElementById('wsViewport');
      return out; })()`);
    chk('the document direction is rtl', r.dir==='rtl');
    chk('the document language is Arabic', r.lang==='ar');
    chk('the RTL page raises no uncaught error', errs.length===0, errs.join(' | '));
    chk('there is no horizontal overflow in RTL', r.docW<=r.winW+1);
    chk('the tree renders in RTL', r.rows>0);
    chk('the inspector renders in RTL', r.inspSections>0);
    chk('the issue center renders every category in RTL',
        r.issueCats===JSON.parse(fs.readFileSync(path.join(ROOT,'acs_workspace.json'),
          'utf8')).issue_categories.length);
    chk('the history panel renders in RTL', r.histRows>0);
    chk('the assistant panel opens in RTL', r.aiOpen===true);
    chk('the export center renders in RTL', r.exportRows>0);
    chk('the references panel opens in RTL', r.refOpen===true);
    chk('the layout uses logical inline padding, not a mirrored hack',
        r.rowPadStart!==null&&r.rowPadStart!=='0px');
    chk('unknown values read in Arabic',
        r.unknownTexts.length===0||r.unknownTexts.every(x=>x==='غير محدد'),
        JSON.stringify(r.unknownTexts.slice(0,2)));
    chk('the selection survives the language switch', r.selected==='g.majlis');
    chk('the 3D viewport still exists in RTL', r.viewport===true);
    await pg.close(); }

  console.log('\n== §16/§88/§89 — NO MIXED-LANGUAGE CHROME ==');
  {
    const CAN=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_workspace.json'),'utf8'));
    const o=await open(browser,1440,900,page); const pg=o.pg;
    /* الرموز التعدادية قيم مواصفة لا نثر — تبقى رموزاً في اللغتين، ونستثنيها
       صراحةً بدل تجاهل الخلط كله */
    const ENUMS=[].concat(CAN.ui_modes,CAN.tree_node_kinds,CAN.tree_disciplines,
      CAN.rule_statuses,CAN.issue_severities,CAN.issue_categories,
      CAN.export_kinds,CAN.editability_classes,CAN.inspector_sections,
      ['ORBIT','WALK','FLY','ACS']);
    const probe=async lang=>await pg.evaluate(`(()=>{
      window.__WS__.setLanguage(${JSON.stringify(lang)});
      window.__WS__.select('g.majlis');
      const ids=['wsTreeTitle','wsInspTitle','wsLblRev','wsLblLevel','wsLblMode',
        'wsLblNav','wsLblCompliance','wsPreviewBadge','wsLoading','wsDegradedTitle',
        'wsDegradedBody','wsStSaved','wsStErr','wsStWarn','wsStInfo','wsStPreview'];
      const out={};
      ids.forEach(i=>{ const e=document.getElementById(i);
        out[i]=e?e.textContent:null; });
      /* زرّ اللغة ثنائي النصّ عمداً (ع/EN) كي يُعثر عليه في اللغتين،
         فيُستثنى صراحةً بدل تجاهل الخلط كلّه */
      const lb=document.getElementById('wsBtnLang');
      const lbTxt=lb?lb.textContent:'';
      /* الإفصاح التعاقدي موسوم lang=en عمداً — يُستبعَد من فحص نقاء اللغة */
      Array.prototype.forEach.call(
        document.querySelectorAll('[data-ws-note="canonical"]'),
        e=>{ e.setAttribute('data-was',e.textContent); e.textContent=''; });
      const NL=String.fromCharCode(10);
      out.__all=document.getElementById('acsWorkspace').innerText
        .split(NL).filter(l=>l.trim()!==lbTxt.trim()).join(NL);
      /* أسماء المستعمل داخل النموذج ليست نصّ واجهة ولا تُترجَم إطلاقاً */
      const m=window.__WS__.project().model, names=[];
      if(m.meta&&m.meta.name) names.push(String(m.meta.name));
      (m.levels||[]).forEach(lv=>{ if(lv.name) names.push(String(lv.name)); });
      Object.keys(m.floors||{}).forEach(tk=>{
        ((m.floors[tk]||{}).rooms||[]).forEach(r=>{
          names.push(String(r.id)); if(r.name) names.push(String(r.name));
          (r.objects||[]).forEach(o=>{ if(o.kind) names.push(String(o.kind)); }); }); });
      out.__modelNames=names;
      return out; })()`);
    const AR=/[\u0600-\u06FF]/;
    const en=await probe('en');
    const ar=await probe('ar');
    chk('every English chrome string matches the canonical English label',
        ['wsTreeTitle:project','wsInspTitle:inspector','wsLblRev:rev',
         'wsLblLevel:level','wsLblMode:mode','wsLblNav:nav',
         'wsLblCompliance:compliance','wsPreviewBadge:preview',
         'wsDegradedTitle:degraded','wsDegradedBody:degraded_body']
        .every(pair=>{ const q=pair.split(':');
          return en[q[0]]===CAN.ui_labels[q[1]].en; }),
        JSON.stringify(en.wsTreeTitle)+' / '+JSON.stringify(en.wsLblRev));
    chk('every Arabic chrome string matches the canonical Arabic label',
        ['wsTreeTitle:project','wsInspTitle:inspector','wsLblRev:rev',
         'wsLblLevel:level','wsLblMode:mode','wsLblNav:nav',
         'wsLblCompliance:compliance','wsPreviewBadge:preview',
         'wsDegradedTitle:degraded','wsDegradedBody:degraded_body']
        .every(pair=>{ const q=pair.split(':');
          return ar[q[0]]===CAN.ui_labels[q[1]].ar; }),
        JSON.stringify(ar.wsTreeTitle)+' / '+JSON.stringify(ar.wsLblRev));
    chk('no Arabic text leaks into the English workspace',
        !AR.test(en.__all),
        (en.__all.match(new RegExp('[^\\n]*['+'\\u0600-\\u06FF'+'][^\\n]*','g'))||[])
          .slice(0,3).join(' | '));
    {
      const leaked=String(ar.__all).split('\n')
        .map(l=>l.trim()).filter(Boolean)
        .filter(l=>/^[\x20-\x7E]+$/.test(l))
        .filter(l=>!/^[-—·0-9.,:;()\[\]\/%×+]+$/.test(l))
        .filter(l=>!ENUMS.some(e=>l.indexOf(String(e))>=0))
        .filter(l=>!/^(rev:|bld_|g\.|flr_|acs\.)/.test(l))
        /* مفاتيح الحقول القانونية (space.area_m2, lock_reason) ورموز التعداد
           (HOSTS_DOOR, NOT_EVALUATED) تُعرض حرفيّاً في اللغتين عمداً: هي قيم
           مواصفة يحتاجها المهندس بنصّها، لا نثر واجهة */
        .filter(l=>!/^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$/.test(l))
        .filter(l=>!/^[A-Z][A-Z0-9_]*(\s*\(\d+\))?$/.test(l))
        .filter(l=>!/^[0-9a-f]{8,}$/.test(l))
        .filter(l=>(ar.__modelNames||[]).indexOf(l)<0);
      chk('no untranslated English prose remains in the Arabic workspace',
          leaked.length===0, leaked.slice(0,4).join(' | ')); }
    chk('the language switch does not lose the selection',
        (await pg.evaluate('window.__WS__.ui().selected_id'))==='g.majlis');
    await pg.close(); }

  console.log('\n== §94 — SCREENSHOT REGRESSION EVIDENCE ==');
  const states=[
    ['EMPTY',1440,async pg=>{ await pg.evaluate('window.__WS__.attach(null)'); }],
    ['PROJECT_GENERATED',1440,async pg=>{}],
    ['ROOM_SELECTED',1440,async pg=>{
      await pg.evaluate("window.__WS__.select('g.majlis')"); }],
    ['EDIT_PREVIEW',1440,async pg=>{
      await pg.evaluate(`(()=>{ window.__WS__.setMode('EDIT');
        window.__WS__.select('g.majlis');
        window.__WS__.beginPreview({type:'RESIZE_SPACE',target_id:'g.majlis',
          parameters:{w:6,d:4}}); })()`); }],
    ['ISSUE_SELECTED',1440,async pg=>{
      await pg.evaluate('window.__WS__.issues()'); }],
    ['MOBILE',390,async pg=>{
      await pg.evaluate("window.__WS__.select('g.majlis')"); }],
    ['RTL',390,async pg=>{
      await pg.evaluate("window.__WS__.setLanguage('ar')");
      await pg.evaluate("window.__WS__.select('g.majlis')"); }]];
  for(const st of states){
    const o=await open(browser,st[1],900,page); const pg=o.pg, errs=o.errs;
    try{ await st[2](pg); }catch(e){}
    const file=path.join(SHOTS,st[0]+'.png');
    await pg.screenshot({path:file});
    const ok=fs.existsSync(file)&&fs.statSync(file).size>2000;
    chk('a screenshot was captured for the state '+st[0], ok,
        ok?String(fs.statSync(file).size):'missing');
    chk('the state '+st[0]+' raised no page error', errs.length===0, errs.join(' | '));
    await pg.close(); }
  chk('no claim of pixel identity across GPU environments is made',
      /No claim of pixel identity/.test(JSON.parse(fs.readFileSync(
        path.join(ROOT,'acs_workspace.json'),'utf8')).screenshot_note));

  await browser.close();
  console.log('\n──────────────────────────────────────────────');
  console.log('RESPONSIVE: '+pass+' passed, '+fail+' failed');
  process.exit(fail?1:0);
})().catch(e=>{ console.log('  ✗ responsive run aborted:',e&&e.message);
  console.log('\nRESPONSIVE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  process.exit(1); });
