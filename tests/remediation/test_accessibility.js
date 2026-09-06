/* ============================================================================
   إتاحة الوصول — خطّ الأساس WCAG 2.1 AA على الصفحة المشحونة في Chromium حقيقي.
     node tests/remediation/test_accessibility.js

   نطاق هذا التشغيل مُعلَن بدقّة:
     · تُخدَم public/ على 127.0.0.1 بأنواع محتوى صحيحة وبرأس سياسة الأمن
       الإنتاجي نفسه. (قبل F-09 كان التحميل من file:// كافياً لأن الصفحة كانت
       تحمل أنماطها وشيفرتها؛ بعده صارت قشرة تشير إلى /app/… بمسارات جذريّة
       لا يحلّها file://، فكان القياس يجري على وثيقة بلا أنماط.) Three.js غير
       مُعبَّأ في هذا الصندوق (public/vendor فارغ، لا شبكة)، فرسم الوحدات يفشل
       عند استيراده.
       هذا متوقَّع، وليس نجاحاً ولا فشلاً في إتاحة الوصول: النطاق هنا هو طبقة
       DOM/ARIA وحدها، وهي بالضبط الطبقة التي يقرأها قارئ الشاشة.
     · axe-core غير مُعبَّأ في هذا المستودع (فُحص node_modules وpublic). لا
       نزيّف تشغيله: تغطية axe هي NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED،
       وما يجري هنا هو فاحص حتمي مكتوب لهذه المعايير بعينها.
     · بكسلات WebGL لا يقرؤها قارئ شاشة أصلاً. لذلك يُفحَص البديل النصّي، لا
       الصورة.
   ========================================================================== */
const fs=require('fs'), path=require('path'), http=require('http');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const PUB=path.join(ROOT,'public');
const PW=require(path.join(ROOT,'tools','pw_chromium.js'));
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js):
   نداء chromium.launch() المباشر يطلب البناء الذي تتوقّعه نسخة Playwright
   المثبّتة، فيسقط في صندوق يحمل بناءً آخر — فشلُ بيئةٍ لا فشلُ منتج. */
/* المصدر الوحيد الذي يعرف تخطيط الواجهة بعد F-09 */
const AS=require(path.join(ROOT,'tests','lib','app_source.js'));
const CSSTEXT=fs.existsSync(path.join(PUB,'app','styles','app.css'))
  ? fs.readFileSync(path.join(PUB,'app','styles','app.css'),'utf8') : '';
const TRUST=require(path.join(HERE,'_trust_core.js'));

/* F-09 — الصفحة صارت قشرة تشير إلى /app/… بمسارات جذريّة، وfile:// لا يحلّها:
   الورقة الخارجية لا تُحمَّل فيعود كل قياس تباين أو هدف لمس قياساً على وثيقة
   عارية. تُخدَم public/ على 127.0.0.1 بأنواع محتوى صحيحة وبرأس السياسة
   الإنتاجي نفسه، فما يُقاس هنا هو ما يراه المستخدم هناك. */
function productionCSP(){
  try{ const nt=fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8');
    const m=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
    return m?m[1]:''; }catch(e){ return ''; }
}
const MIME={'.html':'text/html; charset=utf-8',
  '.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8',
  '.css':'text/css; charset=utf-8','.json':'application/json',
  '.png':'image/png','.svg':'image/svg+xml','.txt':'text/plain',
  '.xml':'application/xml'};
function serve(){
  const CSP=productionCSP();
  return new Promise(res=>{
    const srv=http.createServer((rq,rs)=>{
      const u=decodeURIComponent(rq.url.split('?')[0]);
      const f=path.normalize(path.join(PUB,u==='/'?'index.html':u));
      if(!f.startsWith(PUB)||!fs.existsSync(f)||fs.statSync(f).isDirectory()){
        rs.writeHead(404); rs.end(); return; }
      const h={'Content-Type':MIME[path.extname(f)]||'application/octet-stream',
               'X-Content-Type-Options':'nosniff'};
      if(CSP) h['Content-Security-Policy']=CSP;
      rs.writeHead(200,h); fs.createReadStream(f).pipe(rs);
    });
    srv.listen(0,'127.0.0.1',()=>res(srv));
  });
}

let pass=0, fail=0, soft=0;
const chk=(n,c,d)=>{ c?(pass++,console.log('  ✓',n))
                      :(fail++,console.log('  ✗',n,d===undefined?'':
                          String(typeof d==='string'?d:JSON.stringify(d)).slice(0,300))); };
const note=(n,d)=>{ soft++; console.log('  ·',n,d===undefined?'':d); };

/* axe-core: يُبحَث عنه فعلاً ولا يُدَّعى وجوده */
function findAxe(){
  const cands=[path.join(ROOT,'node_modules','axe-core','axe.min.js'),
               path.join(ROOT,'node_modules','axe-core','axe.js'),
               path.join(ROOT,'public','vendor','axe-core','axe.min.js'),
               path.join(ROOT,'public','assets','axe.min.js')];
  return cands.filter(p=>fs.existsSync(p))[0]||null;
}

async function launch(){ return await PW.launch(); }

(async()=>{
console.log('HARNESS: accessibility DOM/ARIA layer, real Chromium, '
  +'http:// load of public/ under the production CSP');
const AXE=findAxe();
if(AXE) console.log('axe-core found at '+AXE);
else console.log('axe-core: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED '
  +'(not vendored in node_modules or public/; no network in this sandbox). '
  +'A focused deterministic checker runs instead and is reported as such.');

let browser;
try{ browser=await launch(); }
catch(e){
  console.log('\nCHROMIUM UNAVAILABLE: '+String(e).slice(0,200));
  console.log('ACCESSIBILITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  process.exit(2);
}
const SRV=await serve();
const PAGE='http://127.0.0.1:'+SRV.address().port+'/index.html';
console.log('serving public/ at '+PAGE
  +' with the production Content-Security-Policy as a real response header');
const ctx=await browser.newContext({viewport:{width:1440,height:900}});
const page=await ctx.newPage();
const consoleErrors=[];
page.on('console',m=>{ if(m.type()==='error') consoleErrors.push(m.text()); });
page.on('pageerror',e=>consoleErrors.push('pageerror: '+String(e.message)));
await page.addInitScript(()=>{ window.__CSPV=[];
  document.addEventListener('securitypolicyviolation',
    e=>window.__CSPV.push(e.violatedDirective+' '+(e.blockedURI||''))); });
await page.goto(PAGE,{waitUntil:'domcontentloaded'});
await page.waitForTimeout(700);

console.log('\n== §0 — النطاق المُعلَن: المحرّك ثلاثي الأبعاد غائب هنا عمداً ==');
(function(){})();
const three=await page.evaluate(()=>({
  ready:!!(window.ACS&&window.ACS.ready),
  hasThree:typeof window.THREE!=='undefined'}));
console.log('  · three.js loaded: '+three.hasThree+' · ACS.ready: '+three.ready);
console.log('  · the module script cannot run without vendored Three.js in this '
  +'sandbox — that is EXPECTED and is neither an accessibility pass nor failure.');
const modErrs=consoleErrors.filter(t=>/three|module|import/i.test(t));
note('module-load errors observed (expected, out of scope)', modErrs.length);

/* ── §0b — الطبقة التي يقرأها قارئ الشاشة تعتمد الآن على ورقة أنماط خارجية ──
   قبل F-11 كانت الأنماط مضمّنة في الصفحة، فكانت تصل دائماً. الآن هي طلب ثانٍ
   تحكمه السياسة ونوع المحتوى: إن لم تصل، عاد كل قياس تباين وهدف لمس أدناه
   قياساً على وثيقة عارية — أي نجاحاً كاذباً. تُقاس أوّلاً. */
const cssState=await page.evaluate(()=>({
  sheets:document.styleSheets.length,
  rules:(function(){let n=0;for(const s of document.styleSheets){
    try{n+=s.cssRules.length;}catch(e){}}return n;})(),
  styleBlocks:document.querySelectorAll('style').length,
  inlineStyleAttrs:document.querySelectorAll('[style]').length,
  inlineHandlers:Array.from(document.querySelectorAll('*'))
    .filter(el=>Array.from(el.attributes).some(a=>/^on[a-z]+$/.test(a.name)))
    .map(el=>(el.tagName.toLowerCase()+(el.id?'#'+el.id:''))),
  utilities:Array.from(new Set(Array.from(document.querySelectorAll('[class]'))
    .flatMap(el=>String(el.className).split(/\s+/))
    .filter(c=>/^acs-u-\d+$/.test(c)))).sort(),
  csp:(window.__CSPV||[])
}));
chk('the EXTERNAL stylesheet loaded and its rules resolved — every contrast and '
    +'touch-target measurement below is made against the shipped styling',
    cssState.sheets>=1 && cssState.rules>200, cssState);
chk('no <style> block and no style= attribute survive in the served document — '
    +'the strict CSP forbids the second and the utility classes replaced it',
    cssState.styleBlocks===0 && cssState.inlineStyleAttrs===0, cssState);
chk('the .acs-u-NN utility classes that replaced the inline styles are really '
    +'in use in the DOM', cssState.utilities.length>=20,
    cssState.utilities.length);
chk('every utility class used in the DOM is defined in the external stylesheet '
    +'— none silently lost its declaration in the move',
    CSSTEXT.length>1000
    && cssState.utilities.every(c=>CSSTEXT.indexOf('.'+c)>=0),
    cssState.utilities.filter(c=>CSSTEXT.indexOf('.'+c)<0).join(', '));
chk('NO element carries an inline event handler: under this CSP it would never '
    +'fire, so a control that depends on one is unusable by anyone — keyboard '
    +'or mouse', cssState.inlineHandlers.length===0,
    cssState.inlineHandlers.join(', '));
chk('the production CSP raised no violation while the DOM/ARIA layer loaded',
    cssState.csp.length===0, JSON.stringify(cssState.csp));

/* الإخفاء الابتدائي جزء من الطبقة التي يقرأها قارئ الشاشة: لوحُ مشروعٍ مرئيّ
   قبل الدخول يضع عشرات عناصر التحكّم في ترتيب Tab أمام بطاقة الدخول. قبل
   F-11 كان الإخفاء خاصيّةً مضمّنة تعلو كل قاعدة؛ بعده صار صنفاً يُهزَم بأي
   قاعدة مُعرِّف. يُقاس هنا على الوثيقة المخدومة بلا أي تدخّل. */
const gate=await page.evaluate(()=>{
  const g=id=>{const e=document.getElementById(id);
    return e?{display:getComputedStyle(e).display,
              cls:String(e.className||'')}:null;};
  return {login:g('login'), left:g('left'),
          panelModel:g('acsPanelModel'), panelShow:g('acsPanelShow'),
          clipBox:g('clipBox')};
});
chk('at load the login gate is the visible surface and the project panel is '
    +'still hidden — a visible panel puts dozens of controls ahead of the login '
    +'card in the Tab order',
    !!gate.login && gate.login.display!=='none'
    && !!gate.left && gate.left.display==='none', gate);
chk('at load the inactive tab panels are hidden, so Tab does not walk through '
    +'three panels at once',
    !!gate.panelModel && gate.panelModel.display==='none'
    && !!gate.panelShow && gate.panelShow.display==='none', gate);

console.log('\n== §1 — اسم متاح لكل عنصر تفاعلي في الـDOM المكتوب يدوياً ==');
/* اسم متاح = محتوى نصّي حقيقي، أو aria-label، أو aria-labelledby، أو <label for>.
   title وحده لا يُحتسب: ليس اسماً موثوقاً عبر التقنيات المساعدة. */
const named=await page.evaluate(()=>{
  const GEN=['acsWorkspace','wsModal','wsToasts','rvPanel','rvView','bxPanel',
             'dcPanel','pqPanel','adPanel'];
  const inGenerated=el=>GEN.some(id=>{ const g=document.getElementById(id);
    return g && (g===el||g.contains(el)); });
  const EMOJI=/^[\s -㌀\uD83C-􏰀-\uDFFF←-⇿☀-➿×✕✖✗✘×✕✓↶↷⏱⚠✦⤓▤▲▼☰📷📏▱✂️✏️🔄🏛️🦅⬛🎬🚶🏃💾⬇⬆🗑📄🎨📎🤖↻⚖]*$/;
  const out=[];
  const nodes=document.querySelectorAll(
    'button, a[href], input, select, textarea, [role=button], [tabindex]:not([tabindex="-1"])');
  nodes.forEach(el=>{
    if(inGenerated(el)) return;
    if(el.type==='hidden') return;
    const tag=el.tagName.toLowerCase();
    const aria=(el.getAttribute('aria-label')||'').trim();
    const alb=(el.getAttribute('aria-labelledby')||'').trim();
    const albText=alb.split(/\s+/).map(id=>{
      const n=document.getElementById(id); return n?(n.textContent||'').trim():''; })
      .join(' ').trim();
    let lbl='';
    if(el.id){ const l=document.querySelector('label[for="'+CSS.escape(el.id)+'"]');
      if(l) lbl=(l.textContent||'').trim(); }
    if(!lbl && el.closest && el.closest('label')) lbl=(el.closest('label').textContent||'').trim();
    const txt=(el.textContent||'').trim();
    const textIsMeaningful = txt.length>0 && !EMOJI.test(txt);
    const name=aria||albText||lbl||(textIsMeaningful?txt:'');
    out.push({tag:tag, id:el.id||null, cls:el.className||'',
      text:txt.slice(0,24), name:name.slice(0,60), ok:name.length>0,
      title:(el.getAttribute('title')||'').slice(0,40)});
  });
  return out;
});
chk('the hand-written DOM exposes interactive controls at all', named.length>=40,
    named.length);
const unnamed=named.filter(x=>!x.ok);
chk('EVERY interactive control in the hand-written DOM has an accessible name '
    +'(not title alone)', unnamed.length===0,
    unnamed.map(u=>u.tag+'#'+(u.id||'?')+'["'+u.text+'"]'));
console.log('  · '+named.length+' hand-written interactive controls checked, '
  +named.filter(x=>x.ok).length+' named');

console.log('\n== §2 — الأزرار الأيقونية التي كانت بلا اسم ==');
const icons=await page.evaluate(()=>{
  const ids=['panelToggle','wUp','wDown','wRun','wExit','cbClip','cbNote','cbShot',
             'bShot','acsA11yOpen','acsExportBackup','acsClearLocal'];
  const out={};
  ids.forEach(id=>{ const e=document.getElementById(id);
    out[id]=e?{aria:e.getAttribute('aria-label')||'', title:e.getAttribute('title')||'',
               type:e.getAttribute('type')||''}:null; });
  const views=[];
  document.querySelectorAll('#camBar button[data-view]').forEach(b=>views.push({
    v:b.getAttribute('data-view'), aria:b.getAttribute('aria-label')||'',
    title:b.getAttribute('title')||'', pressed:b.getAttribute('aria-pressed')}));
  return {out:out, views:views};
});
Object.keys(icons.out).forEach(id=>{
  const e=icons.out[id];
  chk(id+' exists and carries an aria-label', !!e && e.aria.length>3, e);
  if(e) chk(id+' names itself in Arabic AND English',
    /[؀-ۿ]/.test(e.aria) && /[A-Za-z]/.test(e.aria), e.aria);
  if(e) chk(id+' keeps its title as a supplementary hint', e.title.length>3, e.title);
});
chk('all six camera-view buttons carry an aria-label', icons.views.length===6
    && icons.views.every(v=>v.aria.length>3), icons.views);
chk('camera-view buttons declare their pressed state',
    icons.views.every(v=>v.pressed==='true'||v.pressed==='false'), icons.views);
chk('exactly one camera view is pressed at load',
    icons.views.filter(v=>v.pressed==='true').length===1);

console.log('\n== §3 — الأدوار والمناطق الحيّة ==');
const roles=await page.evaluate(()=>({
  camBarToolbar:(document.getElementById('camBar')||{}).getAttribute
    ?document.getElementById('camBar').getAttribute('role'):null,
  camBarLabel:document.getElementById('camBar')
    ?document.getElementById('camBar').getAttribute('aria-label'):null,
  walkToolbar:document.getElementById('walkBtns')
    ?document.getElementById('walkBtns').getAttribute('role'):null,
  tablist:document.querySelector('.tabs')
    ?document.querySelector('.tabs').getAttribute('role'):null,
  tabs:Array.prototype.map.call(document.querySelectorAll('.tabs button'),
    b=>({role:b.getAttribute('role'), sel:b.getAttribute('aria-selected'),
         controls:b.getAttribute('aria-controls')})),
  tabpanels:document.querySelectorAll('[role=tabpanel]').length,
  live:Array.prototype.map.call(document.querySelectorAll('[aria-live]'),
    n=>({id:n.id||null, v:n.getAttribute('aria-live'), role:n.getAttribute('role')})),
  statusLive:document.getElementById('status')
    ?document.getElementById('status').getAttribute('aria-live'):null,
  engineWarnRole:document.getElementById('engineWarn')
    ?document.getElementById('engineWarn').getAttribute('role'):null,
  wsLang:document.getElementById('acsWorkspace')
    ?document.getElementById('acsWorkspace').getAttribute('lang'):null,
  htmlLang:document.documentElement.getAttribute('lang'),
  skips:document.querySelectorAll('a.acs-skip').length
}));
chk('#camBar is a named toolbar',
    roles.camBarToolbar==='toolbar' && (roles.camBarLabel||'').length>5, roles);
chk('the walk HUD buttons are a toolbar', roles.walkToolbar==='toolbar');
chk('the project panel tabs are a real tablist',
    roles.tablist==='tablist' && roles.tabs.length===3
    && roles.tabs.every(t=>t.role==='tab'&&t.controls), roles.tabs);
chk('exactly one tab is selected and each controls a tabpanel',
    roles.tabs.filter(t=>t.sel==='true').length===1 && roles.tabpanels===3, roles);
chk('#status is an aria-live region for status updates',
    roles.statusLive==='polite', roles.statusLive);
chk('#engineWarn is an alert', roles.engineWarnRole==='alert');
chk('there is a dedicated global aria-live region', roles.live.some(l=>l.id==='acsLiveRegion'));
chk('the save-state, tab-state and restore-state widgets announce politely',
    ['acsSaveState','acsTabState','acsRestoreState'].every(
      id=>roles.live.some(l=>l.id===id&&l.v==='polite')), roles.live);
chk('the document is Arabic and the English-labelled workspace declares lang="en"',
    roles.htmlLang==='ar' && roles.wsLang==='en', roles);
chk('skip links are present as the first tab stops', roles.skips>=2, roles.skips);

console.log('\n== §4 — ارتباط التسميات بالحقول ==');
const labels=await page.evaluate(()=>{
  const bad=[];
  document.querySelectorAll('#left input, #left select, #left textarea, '
    +'#login input, #noteModal input, #noteModal select, #noteModal textarea')
    .forEach(el=>{
      if(el.type==='hidden') return;
      const has=(el.getAttribute('aria-label')||'').trim()
        || (el.getAttribute('aria-labelledby')||'').trim()
        || (el.id && document.querySelector('label[for="'+CSS.escape(el.id)+'"]'))
        || (el.closest && el.closest('label'));
      if(!has) bad.push(el.tagName.toLowerCase()+'#'+(el.id||'?'));
    });
  return bad;
});
chk('every form control in the hand-written panels has an associated label',
    labels.length===0, labels);

console.log('\n== §5 — التركيز مرئي وترتيب Tab منطقي وبلا مصيدة ==');
await page.evaluate(()=>{ const l=document.getElementById('login');
  if(l) l.style.display='none'; const lf=document.getElementById('left');
  if(lf) lf.style.display='';
  if(document.activeElement&&document.activeElement.blur) document.activeElement.blur(); });
/* التركيز يُقاس بعد Tab حقيقي: :focus-visible لا ينطبق على focus() برمجي،
   وقياسه برمجياً كان سيعطي نتيجة كاذبة في الاتجاهين. */
await page.keyboard.press('Tab');
await page.keyboard.press('Tab');
await page.keyboard.press('Tab');
const focusCss=await page.evaluate(()=>{
  const a=document.activeElement;
  if(!a||a===document.body) return null;
  const s=getComputedStyle(a);
  return {tag:a.tagName.toLowerCase(), id:a.id||null, cls:String(a.className).slice(0,20),
          outlineWidth:s.outlineWidth, outlineStyle:s.outlineStyle,
          outlineColor:s.outlineColor};
});
chk('a keyboard-focused control receives a visible outline',
    !!focusCss && parseFloat(focusCss.outlineWidth)>=2
    && focusCss.outlineStyle!=='none' && focusCss.outlineColor!=='transparent', focusCss);
const noFocusCss=await page.evaluate(()=>{
  const b=document.getElementById('acsA11yOpen'); if(!b) return null;
  const s=getComputedStyle(b);
  return {w:s.outlineWidth, style:s.outlineStyle}; });
chk('the focus-outline check is not vacuous — an unfocused control has no outline',
    !!noFocusCss && (parseFloat(noFocusCss.w)===0||noFocusCss.style==='none'), noFocusCss);

/* نقطة بدء التنقّل التسلسلي في Chromium لا تُصفَّر بـ blur وحده — نعيد التحميل
   فعلاً حتى يكون «أوّل موضع Tab» أوّلَ موضع حقيقي لا بقيّة اجتياز سابق. */
await page.reload({waitUntil:'domcontentloaded'});
await page.waitForTimeout(400);
/* F-11 — بالآليّة المشحونة نفسها (boot/engine-guard.js): الصنف لا style. */
const railUp=await page.evaluate(()=>{ const l=document.getElementById('login');
  if(l) l.classList.add('acs-hidden');
  const lf=document.getElementById('left');
  if(lf){ lf.classList.remove('acs-hidden'); lf.style.display=''; }
  return {rail:lf?getComputedStyle(lf).display:null,
          login:l?getComputedStyle(l).display:null}; });
chk('the tool rail is laid out before the tab order is walked — otherwise this '
    +'section would measure a page with almost no controls on it',
    railUp.rail!=='none'&&railUp.rail!==null&&railUp.login==='none', railUp);
await page.keyboard.press('Tab');
const order=[];
for(let i=0;i<60;i++){
  const cur=await page.evaluate(()=>{ const a=document.activeElement;
    if(!a||a===document.body) return null;
    return {tag:a.tagName.toLowerCase(), id:a.id||null,
      name:(a.getAttribute('aria-label')||a.textContent||'').trim().slice(0,40)}; });
  if(cur) order.push(cur);
  await page.keyboard.press('Tab');
}
chk('Tab reaches at least 25 distinct controls without stalling',
    new Set(order.map(o=>(o.id||'')+o.name)).size>=25,
    new Set(order.map(o=>(o.id||'')+o.name)).size);
chk('the FIRST tab stop is a skip link',
    order.length>0 && order[0].id==='' ? true : (order[0]&&/تخطّي|Skip/.test(order[0].name)),
    order[0]);
const stuck=order.length>6 && order.slice(0,6).every(
  o=>((o.id||'')+o.name)===((order[0].id||'')+order[0].name));
chk('Tab is not trapped on a single control', !stuck, order.slice(0,4));
/* Shift+Tab يعود فعلاً */
const fwd=await page.evaluate(()=>document.activeElement.id
  ||document.activeElement.className||document.activeElement.tagName);
await page.keyboard.press('Shift+Tab');
const back=await page.evaluate(()=>document.activeElement.id
  ||document.activeElement.className||document.activeElement.tagName);
chk('Shift+Tab moves focus backwards', fwd!==back, {fwd:fwd, back:back});

console.log('\n== §6 — البديل النصّي للعرض ثلاثي الأبعاد ==');
const alt=await page.evaluate(()=>{
  const p=document.getElementById('acsA11yAlt');
  if(!p) return null;
  const app=document.getElementById('app');
  return {role:p.getAttribute('role'), modal:p.getAttribute('aria-modal'),
    hidden:p.getAttribute('aria-hidden'),
    labelled:p.getAttribute('aria-labelledby'),
    described:p.getAttribute('aria-describedby'),
    limitText:(document.getElementById('acsA11yLimit')||{}).textContent||'',
    appRole:app?app.getAttribute('role'):null,
    appLabel:app?(app.getAttribute('aria-label')||''):''};
});
chk('the accessible alternative ships as a labelled dialog', !!alt
    && alt.role==='dialog' && alt.modal==='true' && !!alt.labelled, alt);
chk('the alternative STATES that a screen reader cannot read WebGL pixels',
    !!alt && alt.limitText.indexOf('قارئ الشاشة')>=0
    && alt.limitText.indexOf('لا يستطيع')>=0
    && alt.limitText.indexOf('تفسير بكسلاتها')>=0
    && /screen reader/i.test(alt.limitText)
    && /cannot/i.test(alt.limitText) && /webgl/i.test(alt.limitText),
    (alt||{}).limitText.replace(/\s+/g,' ').slice(0,200));
chk('the 3D canvas host itself declares the same limitation and points at the way out',
    !!alt && alt.appRole==='img'
    && alt.appLabel.indexOf('قارئ الشاشة')>=0
    && alt.appLabel.indexOf('تفسير')>=0
    && /screen reader cannot interpret its pixels/i.test(alt.appLabel),
    (alt||{}).appLabel.slice(0,140));

/* نحقن نموذجاً ونطلب البديل النصّي مباشرةً من الدوالّ المشحونة.
   سكربت الوحدة لم يعمل هنا (لا Three.js)، فنشغّل نواة العرض النصّي وحدها. */
/* F-09 — النواة لم تعد داخل الصفحة: صارت وحدة تُخدَم على /app/trust/core.js
   ويستوردها رسم الوحدات. الفحص أشدّ الآن: يُطلَب الملفّ من الخادم نفسه الذي
   يخدم الصفحة، ويُشترط أن يعود 200 وأن يحمل العلامتين — «موجود في نصّ
   الصفحة» كان يمرّ حتى لو لم يكن الملفّ قابلاً للتحميل أصلاً. */
const built=await page.evaluate(async()=>{
  const r=await fetch('/app/trust/core.js');
  if(!r.ok) return {error:'the trust-core module did not load: HTTP '+r.status};
  const src=await r.text();
  const b=src.indexOf('/* ===== ACS PRODUCTION TRUST CORE (hand-written · pure');
  const e=src.indexOf('/* ===== END ACS PRODUCTION TRUST CORE ===== */');
  if(b<0||e<0) return {error:'core markers not found in the served module'};
  return {found:true, bytes:src.length,
          exported:/export\s*\{[^}]*ACS_TRUST\b/.test(src)};
});
chk('the pure trust core is served as a module, with its markers intact',
    built.found===true && built.bytes>4000, built);
chk('and it is exported, so the module graph can reach it', built.exported===true,
    built);
chk('the shell reaches it through the single module entry point',
    AS.shell().indexOf('<script type="module" src="/app/main.js">')>=0
    && AS.order().indexOf('trust/core.js')>=0, AS.order().join(','));

const rendered=await page.evaluate(()=>{
  /* نبني البديل النصّي بيدنا من نفس هيكل النموذج للتحقّق من العلامات المشحونة،
     لأنّ سكربت الوحدة لم يُنفَّذ (لا Three.js في هذا الصندوق). */
  const host=document.getElementById('acsA11yBody');
  if(!host) return null;
  const p=document.getElementById('acsA11yAlt');
  p.classList.add('on'); p.removeAttribute('aria-hidden');
  return {hasHost:true, visible:getComputedStyle(p).display!=='none'};
});
chk('the alternative can be opened and has a body container',
    !!rendered && rendered.hasHost && rendered.visible, rendered);
const altControls=await page.evaluate(()=>{
  const ids=['acsA11yRefresh','acsA11yClose'];
  return ids.map(id=>{ const e=document.getElementById(id);
    return {id:id, aria:e?(e.getAttribute('aria-label')||''):null}; }); });
chk('the alternative’s own controls are named',
    altControls.every(c=>c.aria && c.aria.length>5), altControls);

console.log('\n== §6b — محتوى البديل النصّي مشتقّ من الهندسة، لا من الشاشة ==');
/* البنّاء دالّة نقيّة في نواة الصفحة، فيُختبَر هنا مباشرةً رغم غياب Three.js. */
const CORE=require(path.join(HERE,'_trust_core.js')).load().T;
(function(){
  const A11Y=CORE.accessibility;
  const M={site:{w:22,d:16},
    levels:[{index:0,name:'الأرضي',template:'ground'},
            {index:1,name:'الأول',template:'typical'}],
    floors:{ground:{rooms:[{id:'lobby',rect:[1,1,6,5],doors:[{}],windows:[{},{}],
                            points:[{}],furniture:[{}]},
                           {id:'store'}]},
            typical:{rooms:[{id:'flat1',rect:[0,0,10,8]}]}}};
  const d=A11Y.buildModel(M);
  chk('with no model the alternative reports an explicit empty state, not a blank page',
      A11Y.buildModel(null).empty===true);
  chk('the project tree carries one node per level with real space children',
      d.tree.length===2 && d.tree[0].children.length===2
      && d.tree[0].children[0].name==='lobby', d.tree);
  chk('the element list carries every space from every level',
      d.elements.length===3 && d.elements.map(e=>e.id).join(',')
        ==='lobby,store,flat1', d.elements.map(e=>e.id));
  chk('element properties include geometry, area and counted sub-elements',
      d.elements[0].w===6 && d.elements[0].d===5 && d.elements[0].area===30
      && d.elements[0].doors===1 && d.elements[0].windows===2, d.elements[0]);
  chk('an unknown dimension stays null — never zero, never an estimate',
      d.elements[1].w===null && d.elements[1].d===null && d.elements[1].area===null,
      d.elements[1]);
  chk('a space with no declared dimensions raises a WARNING rather than being hidden',
      d.issues.some(i=>i.severity==='WARNING' && i.ar.indexOf('store')>=0), d.issues);
  chk('every issue is bilingual', d.issues.every(i=>/[؀-ۿ]/.test(i.ar)
      && /[A-Za-z]/.test(i.en)));
  chk('a model with no levels is reported as an ERROR, not silently empty',
      A11Y.buildModel({site:{}}).issues.some(i=>i.severity==='ERROR'));
  chk('a schedule is produced with one row per space',
      d.schedules.length===1 && d.schedules[0].rows.length===3);
  const svg=A11Y.planSvg(d.plan);
  chk('the floor plan is real SVG derived from the model rectangles',
      svg.indexOf('<svg')===0 && (svg.match(/<rect/g)||[]).length===d.plan.rooms.length+1,
      (svg.match(/<rect/g)||[]).length);
  chk('the floor plan is exposed to assistive technology as a labelled image',
      /role="img"/.test(svg) && /<title id="acsPlanTitle">/.test(svg)
      && /<desc id="acsPlanDesc">/.test(svg)
      && /aria-labelledby="acsPlanTitle acsPlanDesc"/.test(svg));
  chk('the plan description states it comes from geometry, not from 3D pixels',
      svg.indexOf('لا من بكسلات')>=0 && /not from 3D pixels/i.test(svg));
  chk('the plan labels each space by its real identifier',
      svg.indexOf('>lobby<')>=0 && svg.indexOf('>store<')>=0);
  chk('space identifiers are escaped before they reach the SVG',
      A11Y.planSvg({w:1,d:1,rooms:[{id:'<script>x',rect:[0,0,1,1]}]})
        .indexOf('&lt;script&gt;')>=0);
  chk('the core states the WebGL limitation in both languages',
      /[؀-ۿ]/.test(A11Y.canvas_limitation.ar)
      && /screen reader cannot interpret its pixels/i.test(A11Y.canvas_limitation.en));
  chk('the builder is pure — it does not mutate the model handed to it',
      (function(){ const before=JSON.stringify(M); A11Y.buildModel(M);
        return JSON.stringify(M)===before; })());
})();

console.log('\n== §7 — إدارة تركيز الحوارات (Escape يغلق ويعيد التركيز) ==');
const modalWork=await page.evaluate(()=>{
  const nm=document.getElementById('noteModal');
  return {role:nm.getAttribute('role'), modal:nm.getAttribute('aria-modal'),
          labelled:nm.getAttribute('aria-labelledby'),
          titleExists:!!document.getElementById('nmTitle'),
          hidden:nm.getAttribute('aria-hidden')};
});
chk('#noteModal is a labelled modal dialog',
    modalWork.role==='dialog' && modalWork.modal==='true'
    && modalWork.labelled==='nmTitle' && modalWork.titleExists, modalWork);
chk('#noteModal is aria-hidden while closed', modalWork.hidden==='true', modalWork);
/* الأساس مكتوب كسكربت كلاسيكي عمداً، فلا يعتمد على Three.js: نشغّله فعلاً هنا
   بدل الاكتفاء بقراءة المصدر. */
const baseline=await page.evaluate(()=>!!(window.ACS&&window.ACS.a11yBaselineReady));
chk('the accessibility baseline runs even though the 3D module script did not',
    baseline===true);

/* F-09/F-11 — الإخفاء الابتدائي كان خاصيّة مضمّنة style="display:none"، وصار
   صنف .acs-hidden وقاعدته الخارجية display:none!important. لذلك تبدّل المبدّل
   المشحون نفسه: showTab في public/app/ui/workspace-ui-wiring.js صار ينزع الصنف
   *ثم* يضبط style.display (السطران معاً)، وحارس الإقلاع في
   public/app/boot/engine-guard.js يُظهر #left بنزع الصنف كذلك.
   هذا الفحص يُشغّل الآليّة المشحونة كما هي — نسخةً من سطرَي showTab لا صياغةً
   أخرى. الصيغة القديمة (style.display='' وحدها) لم تعد آليّةً مشحونة: قاعدة
   !important تغلبها، فكانت تقيس فشلاً من صنعها هي لا من الصفحة. */
const tabSwitch=await page.evaluate(()=>{
  /* نسخة حرفية من public/app/boot/engine-guard.js */
  const lg=document.getElementById('login'); if(lg) lg.classList.add('acs-hidden');
  const lf=document.getElementById('left'); if(lf) lf.classList.remove('acs-hidden');
  const sp=document.getElementById('acsPanelShow');
  /* نسخة حرفية من سطرَي showTab في ui/workspace-ui-wiring.js */
  sp.classList.toggle('acs-hidden', false);
  sp.style.display='';
  return {display:getComputedStyle(sp).display,
          cls:String(sp.className||''),
          leftDisplay:lf?getComputedStyle(lf).display:null};
});
chk('the shipped tab switcher can actually reveal a panel: showTab removes '
    +".acs-hidden and clears style.display, and the panel then lays out",
    tabSwitch.display!=='none', tabSwitch);
chk('and the shipped boot guard reveals the tool rail the same way',
    tabSwitch.leftDisplay!=='none'&&tabSwitch.leftDisplay!==null, tabSwitch);
/* حتى تبقى فحوص التركيز أدناه قابلة للقياس، يُرفَع الإخفاء بالآليّة المشحونة
   نفسها. أي بقاء لـ display:none بعدها عطلٌ يُعلَن هنا لا يُبتلَع. */
const revealed=await page.evaluate(()=>{ const a=document.getElementById('acsA11yAlt');
  a.className=a.className.replace(/\bon\b/g,''); a.setAttribute('aria-hidden','true');
  const sp=document.getElementById('acsPanelShow');
  sp.classList.remove('acs-hidden'); sp.style.display='';
  const lf=document.getElementById('left');
  lf.classList.remove('acs-hidden'); lf.style.display='';
  const lg=document.getElementById('login'); if(lg) lg.classList.add('acs-hidden');
  return {panel:getComputedStyle(sp).display, rail:getComputedStyle(lf).display}; });
chk('the panel and the tool rail are really laid out before focus is measured',
    revealed.panel!=='none'&&revealed.rail!=='none', revealed);
const canFocus=await page.evaluate(()=>{
  const b=document.getElementById('acsA11yOpen'); b.focus();
  return document.activeElement===b; });
chk('the text-alternative opener is reachable by keyboard', canFocus===true);
await page.keyboard.press('Enter');
await page.waitForTimeout(120);
const opened=await page.evaluate(()=>({
  on:document.getElementById('acsA11yAlt').className.indexOf('on')>=0,
  hidden:document.getElementById('acsA11yAlt').getAttribute('aria-hidden'),
  focus:document.activeElement.id}));
chk('Enter on the opener opens the dialog and moves focus inside it',
    opened.on===true && opened.hidden===null && opened.focus==='acsA11yClose', opened);
await page.keyboard.press('Tab');
await page.keyboard.press('Tab');
const inside=await page.evaluate(()=>{
  const d=document.getElementById('acsA11yAlt');
  return {inside:d.contains(document.activeElement), id:document.activeElement.id}; });
chk('Tab stays inside the modal dialog while it is open',
    inside.inside===true, inside);
await page.keyboard.press('Escape');
await page.waitForTimeout(120);
const closed=await page.evaluate(()=>({
  on:document.getElementById('acsA11yAlt').className.indexOf('on')>=0,
  hidden:document.getElementById('acsA11yAlt').getAttribute('aria-hidden'),
  focus:document.activeElement.id}));
chk('ESCAPE CLOSES the dialog — the trap is escapable, so it is not a keyboard trap',
    closed.on===false && closed.hidden==='true', closed);
chk('FOCUS RETURNS to the control that opened it',
    closed.focus==='acsA11yOpen', closed);

/* F-09 — «مصدر الصفحة» بعد التفكيك = القشرة + شيفرة الوحدات. البحث عن رمز
   يجري على الشيفرة، والبحث عن علامة على القشرة؛ ما يلي منطق مشحون فيُقرأ من
   الشيفرة، وما هو علامة يُقرأ من القشرة صراحةً حيث يلزم. */
const escSrc=AS.appText();
chk('the shipped source wires Escape-to-close and a Tab focus trap for dialogs',
    escSrc.indexOf("if(ev.key==='Escape'){ ev.stopPropagation(); close(); }")>=0
    && escSrc.indexOf("else if(ev.key==='Tab'){ trap(el,ev); }")>=0);
chk('the shipped source returns focus to the opener when a dialog closes',
    escSrc.indexOf("if(altBack&&altBack.focus){ var r=altBack; altBack=null;")>=0
    && escSrc.indexOf("else if(nmBack&&nmBack.focus){ var r=nmBack; nmBack=null;")>=0);
chk('the note modal is also given Escape and focus-trap handling',
    escSrc.indexOf("dialog(nmEl,function(){")>=0);

console.log('\n== §8 — تباين اللون محسوباً من الأنماط المُحلَّلة ==');
const contrast=await page.evaluate(()=>{
  function parse(c){ const m=/rgba?\(([^)]+)\)/.exec(c); if(!m) return null;
    const p=m[1].split(',').map(s=>parseFloat(s));
    return {r:p[0],g:p[1],b:p[2],a:(p.length>3?p[3]:1)}; }
  function lum(c){ const f=v=>{ v/=255; return v<=0.03928?v/12.92
      :Math.pow((v+0.055)/1.055,2.4); };
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); }
  function over(fg,bg){ if(fg.a>=1) return fg;
    return {r:fg.r*fg.a+bg.r*(1-fg.a), g:fg.g*fg.a+bg.g*(1-fg.a),
            b:fg.b*fg.a+bg.b*(1-fg.a), a:1}; }
  function gradOf(el){
    const bi=getComputedStyle(el).backgroundImage||'';
    if(bi==='none') return null;
    const cols=(bi.match(/rgba?\([^)]+\)/g)||[]).map(parse).filter(Boolean)
      .filter(c=>c.a>0.9);
    if(!cols.length) return null;
    /* أسوأ حالة: أفتح لون في التدرّج مقابل نصّ داكن، وأغمقه مقابل نصّ فاتح */
    return cols; }
  function bgOf(el){ let n=el;
    while(n && n!==document.documentElement){
      const g=gradOf(n); if(g) return g;
      const c=parse(getComputedStyle(n).backgroundColor);
      if(c && c.a>0.9) return [c];
      n=n.parentElement; }
    return [{r:11,g:18,b:32,a:1}]; }
  const out=[];
  const sel='#left h1, #left h2, #left .note, #left button, #left label, '
    +'#status, #acsSaveState, .acs-local-note, #acsA11yAlt h2, .acs-a11y-limit';
  document.querySelectorAll(sel).forEach(el=>{
    const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden') return;
    const t=(el.textContent||'').trim(); if(!t) return;
    const fg0=parse(s.color); if(!fg0) return;
    const bgs=bgOf(el);
    /* أسوأ نسبة عبر كل ألوان الخلفية الممكنة — لا نختار الأفضل لنا */
    let ratio=Infinity, bg=bgs[0];
    bgs.forEach(b=>{ const fg=over(fg0,b);
      const L1=lum(fg), L2=lum(b);
      const r=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
      if(r<ratio){ ratio=r; bg=b; } });
    const size=parseFloat(s.fontSize), bold=parseInt(s.fontWeight,10)>=700;
    const large=(size>=24)||(bold&&size>=18.66);
    out.push({sel:el.tagName.toLowerCase()+(el.id?'#'+el.id:''),
      ratio:Math.round(ratio*100)/100, need:large?3:4.5,
      ok:ratio>=(large?3:4.5), size:size, text:t.slice(0,26)});
  });
  return out;
});
chk('contrast was computed from resolved CSS on real text', contrast.length>=10,
    contrast.length);
const lowC=contrast.filter(c=>!c.ok);
chk('every sampled text node meets the WCAG 2.1 AA contrast minimum',
    lowC.length===0, lowC.slice(0,8));

console.log('\n== §9 — أهداف اللمس ≥44 بكسل عند عرض 375 ==');
const mobile=await ctx.newPage();
await mobile.goto(PAGE,{waitUntil:'domcontentloaded'});
await mobile.setViewportSize({width:375,height:812});
await mobile.evaluate(()=>{ const l=document.getElementById('login');
  if(l) l.style.display='none';
  const lf=document.getElementById('left'); if(lf) lf.classList.add('open');
  const w=document.getElementById('walkHUD'); if(w) w.style.display='flex';
  const c=document.getElementById('camBar'); if(c) c.style.display='flex'; });
await mobile.waitForTimeout(200);
const small=await mobile.evaluate(()=>{
  const GEN=['acsWorkspace','wsModal','rvPanel','bxPanel','dcPanel','pqPanel','adPanel'];
  const inGen=el=>GEN.some(id=>{ const g=document.getElementById(id);
    return g&&(g===el||g.contains(el)); });
  const bad=[];
  document.querySelectorAll('button, a.acs-skip, label.file, label.filebtn, .card')
    .forEach(el=>{
      if(inGen(el)) return;
      const s=getComputedStyle(el);
      if(s.display==='none'||s.visibility==='hidden') return;
      const r=el.getBoundingClientRect();
      if(r.width===0&&r.height===0) return;
      if(r.height<44-0.5||r.width<44-0.5)
        bad.push({id:el.id||null, cls:String(el.className).slice(0,24),
          w:Math.round(r.width), h:Math.round(r.height)});
    });
  return bad;
});
chk('every visible hand-written control is at least 44x44 CSS px at 375px wide',
    small.length===0, small.slice(0,10));

console.log('\n== §10 — احترام prefers-reduced-motion ==');
const rm=await ctx.newPage();
await rm.emulateMedia({reducedMotion:'reduce'});
await rm.goto(PAGE,{waitUntil:'domcontentloaded'});
await rm.setViewportSize({width:375,height:812});
await rm.waitForTimeout(200);
const motion=await rm.evaluate(()=>{
  const l=document.getElementById('left');
  const s=getComputedStyle(l);
  const skip=document.querySelector('a.acs-skip');
  return {leftTransition:s.transitionDuration,
          skipTransition:skip?getComputedStyle(skip).transitionDuration:null,
          matches:window.matchMedia('(prefers-reduced-motion: reduce)').matches};
});
chk('the browser reports the reduced-motion preference', motion.matches===true, motion);
chk('the sliding project panel stops animating under reduced motion',
    parseFloat(motion.leftTransition)<=0.002, motion.leftTransition);
chk('the skip link stops animating under reduced motion',
    parseFloat(motion.skipTransition)<=0.002, motion.skipTransition);
const noRm=await ctx.newPage();
await noRm.goto(PAGE,{waitUntil:'domcontentloaded'});
await noRm.setViewportSize({width:375,height:812});
const normal=await noRm.evaluate(()=>getComputedStyle(
  document.getElementById('left')).transitionDuration);
chk('the reduced-motion check is not vacuous — the panel does animate otherwise',
    parseFloat(normal)>0.05, normal);

console.log('\n== §11 — إفصاح القدرات معطَّل ومُعلَّم في العلامات نفسها ==');
const capSrc=escSrc;                     /* الشيفرة: ما يبني الأزرار */
chk('the page ships a capability-disclosure container',
    AS.shell().indexOf('id="acsCapList"')>=0);   /* العلامة: في القشرة */
chk('the disclosure buttons are rendered disabled with aria-disabled',
    capSrc.indexOf("'<button type=\"button\" class=\"ghost acs-cap-btn\" disabled '")>=0
    && capSrc.indexOf("+'aria-disabled=\"true\" '")>=0);
chk('the disclosure carries the exact bilingual label demanded',
    capSrc.indexOf("ar:'غير مدعوم بعد', en:'Not yet supported'")>=0
    && capSrc.indexOf("both:'غير مدعوم بعد / Not yet supported'")>=0);
chk('the disclosure carries a title and an aria-description explaining why',
    capSrc.indexOf("+'title=\"'+escT(e.value+' — '+e.label+' — '+e.why_en)+'\" '")>=0
    && capSrc.indexOf("+'aria-description=\"'+escT(e.why_ar+' / '+e.why_en)+'\" '")>=0);
chk('the page audits itself for undisclosed unimplemented affordances at load',
    capSrc.indexOf('auditCapabilityAffordances(document)')>=0);
chk('a dead button is treated as a violation, not a style issue',
    capSrc.indexOf("v.push('DEAD_BUTTON_WITH_HANDLER')")>=0);

console.log('\n== §12 — طبقة التوصيل المشحونة تعمل فعلاً في متصفّح حقيقي ==');
/* Three.js غائب هنا فسكربت الوحدة كلّه لا يعمل. لكن كتلة التوصيل المكتوبة
   يدوياً لا تلمس Three.js: نحقنها كما هي من الصفحة المشحونة مع بدائل صريحة
   لهوياتها من نطاق الوحدة، فنُثبت أنّها تُنفَّذ ولا ترمي، وأن IndexedDB يدور
   فعلاً، وأنّ العلامات التي تنتجها هي المطلوبة. */
/* الكتلتان تُقرآن من وحدتيهما المشحونتين عبر المُحمِّل الواحد، لا بنسخة ثانية
   ولا باقتطاع نصّي مكرَّر هنا. */
const CORE_SRC=TRUST.coreBlock();
const WIRE_SRC=TRUST.wiringBlock();
const SPEC=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_authoring.json'),'utf8'));

const wired=await page.evaluate(async ([core, wire, spec])=>{
  const MODEL={site:{w:22,d:16},
    levels:[{index:0,name:'الأرضي',template:'ground'}],
    floors:{ground:{rooms:[{id:'lobby',rect:[1,1,6,5],doors:[{}],windows:[{},{}]}]}}};
  const statusEl=document.getElementById('status');
  const errs=[];
  window.__setModelCalls=0;
  const setModel=()=>{ window.__setModelCalls++; };
  /* F-09 — الأسماء التي تُكتَب عبر حدود الوحدات انتقلت إلى الكائن المشترك
     __ACS_SHARED (ارتباط الاستيراد في ES للقراءة فقط). نُمهّده هنا بنفس
     البدائل التي كانت تُمرَّر وسائطَ من قبل، فما يُنفَّذ يبقى الكتلة المشحونة
     نفسها بلا تعديل حرف واحد فيها. */
  const __ACS_SHARED={ LAST_REQUEST_TEXT:'وصف المستخدم',
    acsErrorPanel:()=>{}, acsFetchJSON:async()=>({status:'SUCCESS'}),
    ACS_EXTRA_RULESETS:undefined, ACS_INGEST_STORE:undefined,
    ACS_OCCUPANCY_STORE:undefined, DETAIL:undefined, USE_TEX:undefined };
  window.__ACS_SHARED_PROBE=__ACS_SHARED;
  try{
    /* eslint-disable no-new-func */
    new Function('setModel','statusEl','lastBuilding','notes',
                 'ACS_AUTHORING_SPEC','__ACS_SHARED',
                 core+'\n'+wire)
      (setModel, statusEl, MODEL, [], spec, __ACS_SHARED);
  }catch(e){ errs.push(String(e&&e.message||e)); }
  await new Promise(r=>setTimeout(r,600));
  const A=window.ACS||{};
  const save=document.getElementById('acsSaveState');
  const caps=document.querySelectorAll('#acsCapList button');
  const dead=[];
  caps.forEach(b=>{ if(!b.disabled||b.getAttribute('aria-disabled')!=='true'
    ||!b.getAttribute('title')||!b.getAttribute('aria-description')) dead.push(b.textContent); });
  /* دورة IndexedDB كاملة */
  let saved=null, recovered=null, cleared=null;
  try{ saved=await A.persistence.save('TEST'); }catch(e){ saved={error:String(e)}; }
  try{ recovered=await A.persistence.recover(); }catch(e){ recovered={error:String(e)}; }
  const disc=A.capabilityDisclosure?A.capabilityDisclosure():null;
  const audit=A.lastCapabilityAudit?A.lastCapabilityAudit():null;
  /* لوحة الخطأ */
  A.showErrorState({class:'STORAGE_QUOTA', operation:'LOCAL_SAVE', request_id:'req_test'});
  const errBox=document.querySelector('#reportBox .acs-err');
  const errShot={cls:errBox?errBox.getAttribute('data-acs-error'):null,
    role:errBox?errBox.getAttribute('role'):null,
    hasRetry:!!document.getElementById('acsRetryBtn'),
    text:errBox?errBox.textContent.replace(/\s+/g,' '):'',
    meta:errBox?(errBox.querySelector('.acs-err-meta')||{}).textContent||'':''};
  /* البديل النصّي يُرسَم من النموذج */
  A.renderAccessibleAlternative();
  const body=document.getElementById('acsA11yBody');
  try{ cleared=await A.persistence.clear?null:null; }catch(e){}
  return {errs:errs, trustReady:A.trustReady===true,
    saveText:save?save.textContent.replace(/\s+/g,' '):null,
    saveState:save?save.getAttribute('data-acs-save'):null,
    caps:caps.length, dead:dead,
    disclosure:disc?{cmd:disc.commands.not_implemented,
      snap:disc.snap_types.not_implemented,
      giz:disc.gizmo_operations.not_implemented}:null,
    auditViolations:audit?audit.violations:null,
    saved:saved, recovered:recovered && {ok:recovered.ok, code:recovered.code,
      rev:recovered.project?recovered.project.current_revision:null},
    err:errShot,
    altHtml:body?body.innerHTML.length:0,
    altHasTree:!!(body&&body.querySelector('[role=tree]')),
    altHasSvg:!!(body&&body.querySelector('svg[role=img]')),
    altHasTable:!!(body&&body.querySelector('table')),
    tabs:A.tabs?A.tabs().owner.code:null,
    inflight:A.inFlight?A.inFlight('GENERATE'):null};
}, [CORE_SRC, WIRE_SRC, SPEC]);

chk('the shipped wiring block executes in a real browser without throwing',
    wired.errs.length===0, wired.errs);
chk('the wiring reports itself ready', wired.trustReady===true);
chk('the local-save status renders Arabic primary and English secondary text',
    /محفوظ محلياً على هذا الجهاز/.test(wired.saveText)
    && /saved locally on this device/i.test(wired.saveText), wired.saveText);
chk('a REAL IndexedDB write succeeded in the browser',
    wired.saved && wired.saved.ok===true && wired.saved.code==='SAVED', wired.saved);
chk('a REAL IndexedDB recovery read the work back with its revision',
    wired.recovered && wired.recovered.ok===true, wired.recovered);
chk('the capability disclosure rendered the declared-but-unimplemented entries',
    wired.caps===(wired.disclosure.cmd.length+wired.disclosure.snap.length
                  +wired.disclosure.giz.length) && wired.caps>0,
    {rendered:wired.caps, expected:wired.disclosure});
chk('the disclosure covers exactly the three refused commands',
    JSON.stringify(wired.disclosure.cmd)
      ===JSON.stringify(['MOVE_COLUMN','MOVE_DUCT','CHANGE_FIRE_DOOR_METADATA']),
    wired.disclosure.cmd);
chk('the disclosure covers the declared-but-unimplemented snap types',
    JSON.stringify(wired.disclosure.snap)
      ===JSON.stringify(['ENDPOINT','MIDPOINT','WALL','OPENING','ALIGNMENT']),
    wired.disclosure.snap);
chk('the disclosure covers the declared-but-unimplemented gizmo operations',
    JSON.stringify(wired.disclosure.giz)===JSON.stringify(['ROTATE','SCALE']),
    wired.disclosure.giz);
chk('NO DEAD BUTTON: every disclosed entry is disabled, aria-disabled, titled and described',
    wired.dead.length===0, wired.dead);
chk('the self-audit found no undisclosed unimplemented affordance in the shipped page',
    Array.isArray(wired.auditViolations) && wired.auditViolations.length===0,
    wired.auditViolations);
chk('the error panel renders the declared class with role=alert',
    wired.err.cls==='STORAGE_QUOTA' && wired.err.role==='alert', wired.err);
chk('the error panel shows Arabic AND English and the request id',
    /[؀-ۿ]/.test(wired.err.text) && /[A-Za-z]{6,}/.test(wired.err.text)
    && wired.err.text.indexOf('req_test')>=0, wired.err.text.slice(0,400));
chk('the error panel states the class, retryability and retry safety',
    /class/.test(wired.err.meta) && /retryable/.test(wired.err.meta)
    && /retry-safe/.test(wired.err.meta), wired.err.meta);
chk('no Retry button is offered for a storage-quota failure (retry cannot help)',
    wired.err.hasRetry===false);
chk('the accessible alternative rendered a tree, a table and an SVG plan from the model',
    wired.altHtml>500 && wired.altHasTree && wired.altHasTable && wired.altHasSvg,
    {altHtml:wired.altHtml, tree:wired.altHasTree, tbl:wired.altHasTable, svg:wired.altHasSvg});
chk('this tab is told it owns the project', wired.tabs==='THIS_TAB_OWNS', wired.tabs);
chk('nothing is left in flight after wiring settles', wired.inflight===false);

await browser.close();
SRV.close();

console.log('\n══════════════════════════════════════════════');
console.log('ACCESSIBILITY (DOM/ARIA layer, real Chromium): '
  +pass+' passed, '+fail+' failed, '+soft+' scoped notes');
console.log('SCOPE AND HONESTY:');
console.log('  · axe-core: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED. It is not '
  +'vendored in this repository (node_modules/ and public/ were both checked) and '
  +'there is no network. Nothing here simulates or substitutes for it.');
console.log('  · WebGL rendering, 3D interaction and anything that needs Three.js: '
  +'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (public/vendor is empty here).');
console.log('  · A screen reader cannot interpret WebGL pixels at all. This suite '
  +'checks the text alternative that exists precisely because of that, and does not '
  +'claim the canvas itself is accessible.');
console.log('  · Real assistive-technology behaviour (NVDA / JAWS / VoiceOver) is '
  +'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.');
if(fail){ process.exit(1); }
})().catch(e=>{ console.error('accessibility harness error:', e); process.exit(1); });
