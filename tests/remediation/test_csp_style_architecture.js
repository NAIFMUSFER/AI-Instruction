/* ============================================================================
   KI-13 / F-30 — معمارية التنسيق تحت `style-src 'self'`، مقيسة في Chromium.
     node tests/remediation/test_csp_style_architecture.js

   العطل الذي يغلقه هذا الملفّ
   ---------------------------
   السياسة الإنتاجية تحوي `style-src 'self'` بلا 'unsafe-inline'. المتصفّح يحجب
   بذلك **سمة** style مهما كان طريق وصولها — مكتوبةً في العلامة، أو عبر
   setAttribute('style',…), أو داخل نصّ يُسنَد إلى innerHTML. الطبقات كانت تحقن
   سمات style عبر innerHTML، فتُحجَب صامتةً: العنصر في DOM بلا تنسيقه.

   الخرق الحيّ المُبلَّغ عنه من الإنتاج، وأُعيد إنتاجه هنا حرفياً قبل الإصلاح:
     style-src-attr | public/app/ui/workspace-ui-wiring.js:1300

   وأثره الأخطر لم يكن ذاك السطر بل لوحة التوثيق: `.dc-vp` كانت تأخذ
   left/top/width/height كاملةً من السمة المحجوبة، و`.dc-sheet` تأخذ
   aspect-ratio منها — فينهار كل عرض لوحة إلى ‎0×0‎ في الزاوية بينما تبدو
   العلامة سليمة تماماً في DOM.

   ما يثبّته هذا الملفّ
   -------------------
     §١  قياس أوّليّ: أي آلية تنسيق تعمل تحت هذه السياسة وأيّها لا يعمل.
     §٢  فحص ساكن على **المخرجات المشحونة** لا على المصدر وحده.
     §٣  المولّدات ومخرجاتها متزامنة (لا انحراف مكتوب يدوياً).
     §٤  workspace-ui-wiring.js مصدرٌ قانونيّ لا مخرجٌ مولَّد — بالبرهان.
     §٥  السياسة نفسها ما زالت صارمة (لا 'unsafe-inline' بأي صورة).
     §٦  جسر ACS_STYLE يطبّق المسموح ويُسقط الخطر (قائمة سماح، لا ثقة).
     §٧  القياس الحيّ: إقلاع + نموذج + مساحة العمل + اللوحات الخمس + التوثيق،
         بصفر خرق، مع قياس هندسة لوحة التوثيق فعلياً من getBoundingClientRect.

   نطاق مُعلَن: three.js غير مُعبَّأ هنا (public/vendor يملؤه tools/netlify-build.sh
   وقت البناء، ولا شبكة في هذا الصندوق)، فيُخدَم كعبٌ أدنى ليُقيَّم رسم الوحدات.
   بكسلات WebGL ليست مقيسة ولا مُدّعاة. كل ما يُقاس هنا DOM وCSSOM وخروق
   السياسة، ولا يمرّ أيٌّ منها عبر GPU.
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const APP = path.join(PUB, 'app');
const H = require(path.join(HERE, 'lib_csp_harness.js'));
const { chromium } = require(path.join(ROOT, 'node_modules', 'playwright'));

let pass = 0, fail = 0;
const chk = (name, cond, detail) => {
  if (cond) { pass++; console.log('  ✓', name); }
  else { fail++; console.log('  ✗', name, detail === undefined ? '' : detail); }
};

/* الآليات التي تحجبها `style-src 'self'`. مكتوبة مرّةً هنا ويستعملها §٢ و§٣. */
const BLOCKED_PATTERNS = [
  { name: 'style="…" داخل قالب أو سلسلة', re: /(?<!data-acs-)style\s*=\s*"/g },
  { name: "style='…' داخل قالب أو سلسلة", re: /(?<!data-acs-)style\s*=\s*'/g },
  /* نداء عضو صراحةً: النقطة تمنع اصطياد نصّ مثل 'setAttribute("style")'
     داخل عقد مُعلَن يذكر الآلية بالاسم ليشرح ما لا يفعله. */
  { name: 'setAttribute("style", …)',
    re: /\.\s*setAttribute\s*\(\s*['"`]style['"`]/g },
  { name: 'style.cssText = …', re: /\.style\s*\.\s*cssText\s*=/g },
];

/* يزيل التعليقات قبل الفحص: نصّ التوثيق يذكر الآليات المحجوبة بالاسم عمداً،
   وعدّها خرقاً يجعل الاختبار يعاقب على شرح العطل. */
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
}

function walkJs(dir, acc) {
  for (const f of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walkJs(p, acc);
    else if (p.endsWith('.js')) acc.push(p);
  }
  return acc;
}

/* ─────────────────────────── §٢ · المخرجات المشحونة ───────────────────── */
console.log('\n== 2 · فحص ساكن على المخرجات المشحونة (لا المصدر وحده) ==');
const SHIPPED = walkJs(APP, []).concat([
  path.join(PUB, 'index.html'), path.join(PUB, 'privacy.html')]);
chk('الشجرة المفحوصة هي public/ الفعليّة وفيها الطبقات المولَّدة',
  SHIPPED.some((p) => p.indexOf(path.join('generated', 'docs.js')) >= 0)
  && SHIPPED.some((p) => p.endsWith('index.html'))
  && SHIPPED.length >= 25, String(SHIPPED.length));

const offenders = [];
for (const file of SHIPPED) {
  const raw = fs.readFileSync(file, 'utf8');
  const src = file.endsWith('.html') ? raw.replace(/<!--[\s\S]*?-->/g, ' ')
    : stripComments(raw);
  for (const pat of BLOCKED_PATTERNS) {
    pat.re.lastIndex = 0;
    let m;
    while ((m = pat.re.exec(src))) {
      offenders.push(path.relative(ROOT, file) + ' :: ' + pat.name
        + ' @' + (src.slice(0, m.index).split('\n').length));
    }
  }
}
chk('صفر آلية تنسيق محجوبة في أي ملفّ مشحون', offenders.length === 0,
  offenders.slice(0, 6).join(' | '));

/* ضابط سالب: لو لم يكن الفاحص يرى شيئاً أصلاً لمرّ كل شيء. نحقن نصّاً
   مخالفاً في الذاكرة ونتأكّد أنه يُصطاد. */
const CANARY = 'x.innerHTML = \'<div style="left:1px">y</div>\';'
  + ' e.setAttribute("style","a:b"); e.style.cssText="c:d";';
let caught = 0;
for (const pat of BLOCKED_PATTERNS) {
  pat.re.lastIndex = 0;
  if (pat.re.test(stripComments(CANARY))) caught++;
}
chk('الفاحص نفسه غير عبثيّ — يصطاد الآليات الثلاث في عيّنة مخالفة',
  caught >= 3, String(caught));
chk('data-acs-style لا يُحسب خرقاً (وهو البديل المقصود)',
  !BLOCKED_PATTERNS[0].re.test(' data-acs-style="--dc-vp-x:5%" '));

/* ────────────────── §٣ · المولّد ومخرجه متزامنان ───────────────────────── */
console.log('\n== 3 · المولّدات ومخرجاتها متزامنة ==');
const GENERATORS = [
  ['tools/build_workspace_ui.py', 'public/app/generated/workspace-ui.js'],
  ['tools/build_render_browser.py', 'public/app/generated/render-engine.js'],
  ['tools/build_docs_browser.py', 'public/app/generated/docs.js'],
  ['tools/build_bim_browser.py', 'public/app/generated/bim.js'],
  ['tools/build_pbr_browser.py', 'public/app/generated/pbr.js'],
  ['tools/build_archdetail_browser.py', 'public/app/generated/arch-detail.js'],
  ['tools/build_runtime_browser.py', 'public/app/generated/runtime.js'],
  ['tools/build_authoring_browser.py', 'public/app/generated/authoring.js'],
];
for (const [gen, out] of GENERATORS) {
  const outPath = path.join(ROOT, out);
  const cssPath = path.join(APP, 'styles', 'app.css');
  const beforeJs = fs.readFileSync(outPath, 'utf8');
  const beforeCss = fs.readFileSync(cssPath, 'utf8');
  const beforeIdx = fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
  let ran = true;
  try { execFileSync('python3', [path.join(ROOT, gen)], { cwd: ROOT, stdio: 'pipe' }); }
  catch (e) { ran = false; }
  const afterJs = fs.readFileSync(outPath, 'utf8');
  const afterCss = fs.readFileSync(cssPath, 'utf8');
  const afterIdx = fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
  chk(path.basename(gen) + ' يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)',
    ran && beforeJs === afterJs && beforeCss === afterCss
    && beforeIdx === afterIdx,
    ran ? 'drift' : 'generator failed to run');
}

/* ──────── §٤ · workspace-ui-wiring.js مصدرٌ قانونيّ لا مخرجٌ مولَّد ─────── */
console.log('\n== 4 · هل workspace-ui-wiring.js مخرجٌ مولَّد؟ ==');
/* الأداة الوحيدة التي أنتجته يوماً هي tools/frontend_split.js، ومدخلها هو
   الشيفرة المضمّنة في public/index.html. بعد F-09 صارت الصفحة قشرةً بصفر
   سكربت مضمّن، فلم يعد للأداة مدخل: لا يمكن أن تعيد توليد الملفّ، وصار هو
   المصدر القانونيّ. هذا يُقاس هنا ولا يُفترض. */
const IDX = fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
const inlineExecutable = (IDX.match(
  /<script(?![^>]*\bsrc=)(?![^>]*type="importmap")[^>]*>/g) || []).length;
chk('public/index.html فيها صفر سكربت مضمّن قابل للتنفيذ (مدخل المولّد استُهلك)',
  inlineExecutable === 0, String(inlineExecutable));
let segCount = null;
try {
  const A = require(path.join(ROOT, 'tools', 'frontend_analyze.js'));
  segCount = A.segments(IDX).length;
} catch (e) { segCount = 'throws: ' + e.message.slice(0, 60); }
chk('frontend_analyze.segments على الصفحة الحالية لا تعيد مقاطع التطبيق',
  segCount === 1 || typeof segCount === 'string', String(segCount));
/* الفحص عن **كتابة** لا عن ذِكر: ملفّان يذكران المسار في تعليق أو في عدٍّ،
   وهذا ليس توليداً. الكتابة تعني اقتران المسار بفتحٍ للكتابة أو write_text. */
const WRITERS = fs.readdirSync(path.join(ROOT, 'tools'))
  .filter((f) => f.endsWith('.py') || f.endsWith('.js'))
  .filter((f) => {
    const src = fs.readFileSync(path.join(ROOT, 'tools', f), 'utf8');
    if (src.indexOf('workspace-ui-wiring') < 0) return false;
    return /workspace-ui-wiring[^\n]{0,200}(write|'w'|"w")/.test(src)
      || /(write|'w'|"w")[^\n]{0,200}workspace-ui-wiring/.test(src);
  });
chk('لا أداة في tools/ تكتب ui/workspace-ui-wiring.js (ذِكرُه في تعليق ليس توليداً)',
  WRITERS.length === 0, WRITERS.join(', '));

/* ─────────────────────── §٥ · السياسة ما زالت صارمة ────────────────────── */
console.log('\n== 5 · السياسة الإنتاجية لم تُضعَّف ==');
const CSP = H.productionCSP();
chk("netlify.toml ما زال يحوي style-src 'self' حرفياً",
  /style-src 'self'\s*;/.test(CSP), CSP);
chk("لا 'unsafe-inline' في أي مكان من السياسة",
  CSP.indexOf('unsafe-inline') < 0);
chk("لا 'unsafe-eval' في أي مكان من السياسة",
  CSP.indexOf('unsafe-eval') < 0);
chk('لا توجيه style-src-attr ولا style-src-elem مُضاف',
  CSP.indexOf('style-src-attr') < 0 && CSP.indexOf('style-src-elem') < 0);
chk("لا 'unsafe-hashes' (وهو ما يعيد سمات style من الباب الخلفي)",
  CSP.indexOf('unsafe-hashes') < 0);

/* ───────────────────────── القياس الحيّ (§١ · §٦ · §٧) ─────────────────── */
const MODEL = {
  site: { w: 30, d: 24 },
  levels: [{ index: 0, template: 'typical' }],
  floors: { typical: { rooms: [
    { id: 'hall', name: 'صالة', rect: [0, 0, 12, 9] },
    { id: 'room1', name: 'غرفة نوم', rect: [12, 0, 6, 5] },
    { id: 'room2', name: 'مطبخ', rect: [12, 5, 6, 4] }] } },
  meta: { requirements: [], excluded: [] },
};

async function live() {
  const srv = await H.serve();
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const consoleLog = [];
  H.attachConsole(page, consoleLog);
  await page.addInitScript(H.VIOLATION_RECORDER);

  const phases = {};
  const snap = async (label) => {
    phases[label] = await page.evaluate(() => (window.__cspViolations || []).length);
  };

  await page.goto(`http://127.0.0.1:${srv.port}/`, { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  await snap('boot');

  const MECH_PROBE = () => {
    const out = {};
    const mk = () => { const d = document.createElement('div');
      document.body.appendChild(d); return d; };
    const a = mk();
    try { a.style.left = '12.5%'; out.cssom_prop = a.style.left; }
    catch (e) { out.cssom_prop = 'throw'; }
    try { a.style.setProperty('aspect-ratio', '297/210');
      out.cssom_aspect = getComputedStyle(a).aspectRatio; }
    catch (e) { out.cssom_aspect = 'throw'; }
    try { a.style.setProperty('--acs-probe', '7px');
      out.cssom_custom = getComputedStyle(a).getPropertyValue('--acs-probe').trim(); }
    catch (e) { out.cssom_custom = 'throw'; }
    const b = mk();
    try { b.setAttribute('style', 'color:rgb(9,9,9)');
      out.setattr_color = getComputedStyle(b).color; }
    catch (e) { out.setattr_color = 'throw'; }
    const c = mk();
    c.innerHTML = '<span id="__ihp" style="color:rgb(8,8,8)">x</span>';
    out.innerhtml_color = getComputedStyle(document.getElementById('__ihp')).color;
    out.baseline_color = getComputedStyle(mk()).color;
    return out;
  };

  /* §٦ — قائمة سماح الجسر */
  const bridge = await page.evaluate(() => {
    if (!window.ACS_STYLE) return null;
    const d = document.createElement('div');
    d.setAttribute('data-acs-style',
      'left:10%;--dc-vp-w:25%;background-image:url(javascript:1);'
      + 'position:fixed;color:#abcdef;width:999999999999999999999999px;'
      + 'height:expression(alert(1));top:5%');
    document.body.appendChild(d);
    const before = window.ACS_STYLE.stats().dropped;
    const n = window.ACS_STYLE.apply(d);
    return {
      applied: n,
      left: d.style.left,
      custom: d.style.getPropertyValue('--dc-vp-w'),
      color: d.style.color,
      top: d.style.top,
      backgroundImage: d.style.backgroundImage,   // يجب أن تبقى فارغة
      position: d.style.position,                 // خارج قائمة السماح
      height: d.style.height,                     // قيمة خطرة
      droppedDelta: window.ACS_STYLE.stats().dropped - before,
      attrRemoved: !d.hasAttribute('data-acs-style'),
      contract: window.ACS_STYLE.contract,
    };
  });

  /* §٧ — المسار الحقيقيّ للمستخدم: دخول ← تبويب ٣ ← نموذج ← اللوحات.
     لا نتجاوز الواجهة بنداءات داخلية: الأزرار مخفيّة قبل الدخول عمداً،
     وقياس ما لا يراه المستخدم لا يثبت شيئاً عن الإنتاج. */
  await page.fill('#lgName', 'مُدقّق');
  await page.click('#lgGo');
  await page.waitForTimeout(400);
  await snap('login');

  await page.evaluate((m) => { window.ACS.setModel(m); }, MODEL);
  await page.waitForTimeout(600);
  await snap('model');

  /* setModel يعيد الواجهة إلى تبويب «النموذج» عمداً، فيأتي فتح تبويب «العرض»
     بعده — وهو التبويب الذي يحمل مداخل اللوحات. */
  await page.click('#acsTabShow');
  await page.waitForTimeout(300);

  await page.click('#acsOpenWorkspace');
  await page.waitForTimeout(500);
  const workspaceOpen = await page.evaluate(() => {
    const el = document.getElementById('acsWorkspace');
    return !!(el && el.classList.contains('on'));
  });
  await snap('workspace');

  /* مساحة العمل تملأ الشاشة وتغطّي شريط المداخل — تُغلق بـEscape قبل فتح
     البقيّة، وهو نفس ما يفعله المستخدم. */
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  const workspaceClosed = await page.evaluate(() => {
    const el = document.getElementById('acsWorkspace');
    return !!(el && !el.classList.contains('on'));
  });

  const panelState = {};
  for (const [btn, panel] of [['acsOpenRender', 'rvPanel'],
    ['acsOpenBim', 'bxPanel'], ['acsOpenDocs', 'dcPanel'],
    ['acsOpenPbr', 'pqPanel'], ['acsOpenDetail', 'adPanel']]) {
    await page.click('#' + btn);
    await page.waitForTimeout(400);
    panelState[panel] = await page.evaluate((id) => {
      const el = document.getElementById(id);
      return !!(el && el.classList.contains('on'));
    }, panel);
    /* كل لوحة حوارٌ جانبيّ يغطّي شريط المداخل؛ تُغلق بـEscape قبل التالية،
       وهو نفس ما يفعله المستخدم. */
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
  }
  await snap('panels');
  panelState.__workspaceOpen = workspaceOpen;
  panelState.__workspaceClosed = workspaceClosed;

  /* لوحة التوثيق: تُفتح ثانيةً (أُغلقت في الجولة أعلاه) ثم نُنشئ عرضاً ولوحة
     حقيقيّين ونقيس الهندسة من الصفحة نفسها لا من النموذج. */
  await page.click('#acsOpenDocs');
  await page.waitForTimeout(400);
  /* لوحة التوثيق: نُنشئ عرضاً ولوحة حقيقيّين ثم نقيس الهندسة من الصفحة. */
  const docs = await page.evaluate(() => {
    const D = window.ACS.docs && window.ACS.docs.panel;
    if (!D) return { error: 'docs panel missing' };
    const out = { steps: [] };
    try {
      const S = D.state();
      const arch = S.src ? S.src.arch : null;
      const lid = (arch && arch.levels && arch.levels.length)
        ? arch.levels[0].id : null;
      D.createView({ view_type: 'FLOOR_PLAN', level_id: lid,
        scale_denominator: 100 });
      out.steps.push('view:' + (D.state().views || []).length);
      const v = (D.state().views || [])[0];
      const vid = v ? (v.view ? v.view.view_id : v.view_id) : null;
      /* عرضان بمواضع وأبعاد مختلفة عمداً: عرضٌ واحد قد يبدو سليماً بالصدفة،
         واثنان بمواضع متباعدة يكشفان أي انهيار إلى الزاوية. القيم بالمليمتر
         على ورق A3 أفقيّ (‎420×297‎). */
      D.composeSheet({ sheet_number: 'A-101', paper_size: 'A3',
        orientation: 'LANDSCAPE',
        viewports: vid ? [
          { view_id: vid, x: 20, y: 20, width: 180, height: 120 },
          { view_id: vid, x: 220, y: 150, width: 170, height: 110 },
        ] : [] });
      out.steps.push('sheet:' + (D.state().sheets || []).length);
      const sh = (D.state().sheets || [])[0];
      if (sh) {
        D.select('SHEET', sh.sheet_id);
        out.paper_mm = sh.paper_mm;
        out.viewport_count = (sh.viewports || []).length;
        out.model_viewports = (sh.viewports || []).map((x) => ({
          x: x.x, y: x.y, w: x.width, h: x.height }));
      }
    } catch (e) { out.error = String(e.message || e); }
    return out;
  });
  await page.waitForTimeout(400);

  const geom = await page.evaluate(() => {
    const sheet = document.querySelector('.dc-sheet');
    if (!sheet) return { error: 'no .dc-sheet in DOM' };
    const sr = sheet.getBoundingClientRect();
    const cs = getComputedStyle(sheet);
    const vps = Array.prototype.map.call(
      document.querySelectorAll('.dc-vp'), (v) => {
        const r = v.getBoundingClientRect();
        const c = getComputedStyle(v);
        return {
          id: v.getAttribute('data-dc-viewport'),
          left_pct: c.getPropertyValue('--dc-vp-x').trim(),
          top_pct: c.getPropertyValue('--dc-vp-y').trim(),
          w_pct: c.getPropertyValue('--dc-vp-w').trim(),
          h_pct: c.getPropertyValue('--dc-vp-h').trim(),
          computed_left: c.left, computed_top: c.top,
          computed_width: c.width, computed_height: c.height,
          rect: { w: Math.round(r.width * 100) / 100,
            h: Math.round(r.height * 100) / 100,
            dx: Math.round((r.left - sr.left) * 100) / 100,
            dy: Math.round((r.top - sr.top) * 100) / 100 },
          leftoverAttr: v.hasAttribute('data-acs-style'),
        };
      });
    return {
      sheet: { w: Math.round(sr.width * 100) / 100,
        h: Math.round(sr.height * 100) / 100,
        aspectRatio: cs.aspectRatio,
        leftoverAttr: sheet.hasAttribute('data-acs-style') },
      viewports: vps,
    };
  });
  await snap('docs');

  /* خروق التطبيق تُجمَع أوّلاً. §١ يولّد خرقين **متعمَّدين** (ضابطان سالبان
     يثبتان أن السياسة تعمل فعلاً)، فلا يجوز خلطهما بحصيلة التطبيق. */
  const violations = await page.evaluate(() => window.__cspViolations || []);
  const mech = await page.evaluate(MECH_PROBE);
  const afterProbe = await page.evaluate(() => (window.__cspViolations || []).length);
  /* السمة المحجوبة تبقى في DOM (المحلّل يحتفظ بها، المتصفّح يرفض تطبيقها).
     فالبحث عن [style] في الصفحة الحيّة يسمّي مصدر أي خرق باقٍ بدقّة، بدل
     الاعتماد على sourceFile الذي يأتي فارغاً لسمات العلامة. */
  const residual = await page.evaluate(() => Array.prototype.map.call(
    document.querySelectorAll('[style]'), (el) => ({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      cls: (el.className && el.className.baseVal !== undefined
        ? el.className.baseVal : String(el.className || '')).slice(0, 60),
      style: el.getAttribute('style').slice(0, 90),
      parentId: el.parentElement ? (el.parentElement.id || null) : null,
    })).slice(0, 20));
  await browser.close();
  srv.close();
  return { mech, bridge, panelState, docs, geom, violations, phases, consoleLog,
    residual, probeViolations: afterProbe - violations.length };
}

(async () => {
  let R;
  try { R = await live(); }
  catch (e) {
    console.log('\n  ! تعذّر تشغيل Chromium: ' + (e && e.message));
    console.log('\nCSP STYLE ARCHITECTURE: %d passed, %d failed  '
      + '(الطبقة الحيّة: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED)',
    pass, fail);
    process.exit(1);
  }

  console.log('\n== 1 · أي آلية تنسيق تعمل تحت هذه السياسة؟ (قياس) ==');
  chk('CSSOM: إسناد خاصيّة يُطبَّق', R.mech.cssom_prop === '12.5%', R.mech.cssom_prop);
  chk('CSSOM: setProperty("aspect-ratio") يُطبَّق',
    /297\s*\/\s*210/.test(String(R.mech.cssom_aspect)), R.mech.cssom_aspect);
  chk('CSSOM: خاصيّة مخصّصة تُطبَّق', R.mech.cssom_custom === '7px', R.mech.cssom_custom);
  chk('setAttribute("style") محجوب فعلاً (ضابط سالب)',
    R.mech.setattr_color !== 'rgb(9, 9, 9)', R.mech.setattr_color);
  chk('سمة style داخل innerHTML محجوبة فعلاً (ضابط سالب)',
    R.mech.innerhtml_color !== 'rgb(8, 8, 8)', R.mech.innerhtml_color);
  chk('الضابطان السالبان يعودان إلى اللون الموروث لا إلى قيمتهما',
    R.mech.setattr_color === R.mech.baseline_color
    && R.mech.innerhtml_color === R.mech.baseline_color,
    R.mech.setattr_color + ' / ' + R.mech.baseline_color);
  chk('الضابطان السالبان رفعا خرقَي سياسة فعلاً — فالقياس ليس عبثياً',
    R.probeViolations >= 2, String(R.probeViolations));

  console.log('\n== 6 · جسر ACS_STYLE: يطبّق المسموح ويُسقط الخطر ==');
  chk('الجسر محمّل في الصفحة', !!R.bridge);
  if (R.bridge) {
    chk('يطبّق خاصيّة هندسية مسموحة (left)', R.bridge.left === '10%', R.bridge.left);
    chk('يطبّق خاصيّة مخصّصة من مساحة أسماء المشروع (--dc-vp-w)',
      R.bridge.custom.trim() === '25%', R.bridge.custom);
    chk('يطبّق لوناً سداسياً صالحاً', /rgb\(171, 205, 239\)|#abcdef/.test(R.bridge.color),
      R.bridge.color);
    chk('يُسقط url(javascript:…) — لا ينقل الحقن من السمة إلى الجسر',
      !R.bridge.backgroundImage, JSON.stringify(R.bridge.backgroundImage));
    chk('يُسقط خاصيّة خارج قائمة السماح (position)',
      !R.bridge.position, JSON.stringify(R.bridge.position));
    chk('يُسقط قيمة خطرة (expression(...))', !R.bridge.height,
      JSON.stringify(R.bridge.height));
    chk('يعدّ ما أسقطه بدل تمريره صامتاً (url + position + expression)',
      R.bridge.droppedDelta >= 3, String(R.bridge.droppedDelta));
    chk('يحذف السمة بعد التطبيق (لا تطبيق مزدوج ولا بقايا)',
      R.bridge.attrRemoved === true);
    chk('العقد المُعلَن يقول إن الآلية CSSOM لا سمة style',
      R.bridge.contract && R.bridge.contract.mechanism === 'CSSOM setProperty'
      && R.bridge.contract.governed_by_style_src === false);
  }

  console.log('\n== 7 · القياس الحيّ: صفر خرق عبر كل سطح إنتاجيّ ==');
  const byPhase = R.phases;
  chk('الإقلاع: صفر خرق', byPhase.boot === 0, 'violations=' + byPhase.boot);
  chk('الدخول وفتح تبويب العرض: صفر خرق', byPhase.login === 0,
    'violations=' + byPhase.login);
  chk('تحميل النموذج: صفر خرق', byPhase.model === 0, 'violations=' + byPhase.model);
  chk('فتح مساحة العمل: صفر خرق', byPhase.workspace === 0,
    'violations=' + byPhase.workspace);
  chk('فتح اللوحات الخمس: صفر خرق', byPhase.panels === 0,
    'violations=' + byPhase.panels);
  chk('رسم لوحة التوثيق: صفر خرق', byPhase.docs === 0, 'violations=' + byPhase.docs);
  chk('المجموع الكلّي صفر خرق سياسة', R.violations.length === 0,
    JSON.stringify(R.violations.slice(0, 4).map((v) => ({
      d: v.directive, target: v.target }))));
  /* وجود سمة style وحده ليس دليل خرق: إسناد CSSOM يُسلسِل نفسه في السمة وهو
     مسموح (مقيس في §١). الدليل هو حدث الخرق نفسه، ومعه العنصر المستهدَف. */
  console.log('    (للعلم) عناصر تحمل سمة style من CSSOM المشروع: '
    + R.residual.length);

  chk('مساحة العمل فُتحت فعلاً', R.panelState.__workspaceOpen === true);
  chk('Escape يغلق مساحة العمل (وإلا غطّت شريط المداخل بلا طريق عودة)',
    R.panelState.__workspaceClosed === true);
  for (const [id, ar] of [['rvPanel', 'العرض'], ['bxPanel', 'تبادل BIM'],
    ['dcPanel', 'التوثيق'], ['pqPanel', 'جودة العرض'],
    ['adPanel', 'التفصيل المعماري']]) {
    chk('لوحة ' + ar + ' فُتحت فعلاً', R.panelState[id] === true);
  }

  console.log('\n== 7ب · هندسة لوحة التوثيق مقيسة من الصفحة ==');
  chk('لوحة ورقيّة حقيقيّة أُنشئت وعُرضت', !R.docs.error && !R.geom.error,
    JSON.stringify(R.docs.error || R.geom.error || ''));
  if (!R.geom.error) {
    const s = R.geom.sheet;
    chk('‎.dc-sheet‎ ليست ‎0×0‎ — العطل الأصلي', s.w > 20 && s.h > 20,
      JSON.stringify(s));
    const paper = R.docs.paper_mm || [420, 297];
    const want = paper[0] / paper[1];
    const got = s.w / s.h;
    chk('نسبة عرض اللوحة تطابق مقاس الورق المعلن ('
      + paper[0] + '×' + paper[1] + ' ⇒ ' + want.toFixed(3) + ')',
    Math.abs(got - want) < 0.02, 'measured=' + got.toFixed(3)
      + ' computed=' + s.aspectRatio);
    chk('لا بقايا data-acs-style على اللوحة (طُبِّقت لا أُهمِلت)',
      s.leftoverAttr === false);
    chk('اللوحة تحوي عرضاً واحداً على الأقل',
      R.geom.viewports.length >= 1, String(R.geom.viewports.length));
    const bad = R.geom.viewports.filter((v) => v.rect.w < 1 || v.rect.h < 1);
    chk('لا عرض انهار إلى ‎0×0‎', bad.length === 0,
      JSON.stringify(bad.slice(0, 2)));
    const atCorner = R.geom.viewports.filter(
      (v) => v.rect.dx === 0 && v.rect.dy === 0 && v.top_pct
        && parseFloat(v.top_pct) > 0.5);
    chk('لا عرض التصق بالزاوية رغم أن نموذجه يضعه بعيداً عنها',
      atCorner.length === 0, JSON.stringify(atCorner.slice(0, 2)));
    const unresolved = R.geom.viewports.filter(
      (v) => v.leftoverAttr || !v.left_pct || !v.w_pct);
    chk('كل عرض استلم left/top/width/height كخصائص محسوبة',
      unresolved.length === 0, JSON.stringify(unresolved.slice(0, 2)));
    /* التحقّق العدديّ: النسبة المئوية في الخاصيّة المخصّصة يجب أن تعطي
       البكسلات المقابلة داخل اللوحة. هذا ما يفرّق «طُبِّقت» عن «بدت مطبَّقة». */
    let mismatched = 0;
    for (const v of R.geom.viewports) {
      const wantW = s.w * parseFloat(v.w_pct) / 100;
      const wantX = s.w * parseFloat(v.left_pct) / 100;
      if (Math.abs(v.rect.w - wantW) > 2) mismatched++;
      else if (Math.abs(v.rect.dx - wantX) > 2) mismatched++;
    }
    chk('البكسلات المقيسة تطابق النِّسب المطلوبة (±2px)', mismatched === 0,
      String(mismatched) + '/' + R.geom.viewports.length);
    console.log('    قياس: اللوحة ' + s.w + '×' + s.h + 'px · aspect-ratio='
      + s.aspectRatio + ' · ' + R.geom.viewports.length + ' عرضاً');
    for (const v of R.geom.viewports.slice(0, 4)) {
      console.log('      ' + (v.id || '?') + '  ' + v.left_pct + '/' + v.top_pct
        + '  ' + v.w_pct + '×' + v.h_pct + '  ⇒  ' + v.rect.w + '×' + v.rect.h
        + 'px @ +' + v.rect.dx + ',+' + v.rect.dy);
    }
  }

  /* تصنيف الكونسول — يُطبع دائماً ولا يُخفى. */
  console.log('\n== 8 · تصنيف كل رسالة كونسول ==');
  const seen = new Map();
  for (const l of R.consoleLog) {
    const key = l.type + '|' + l.text.slice(0, 110);
    seen.set(key, (seen.get(key) || 0) + 1);
  }
  const EXPECTED = [
    { re: /acs-engine\.onrender\.com/, why:
      'لا شبكة في هذا الصندوق — الخادم الحيّ غير قابل للوصول. متوقَّع.' },
    { re: /ERR_TUNNEL_CONNECTION_FAILED|net::ERR_/, why:
      'أثر انقطاع الشبكة نفسه. متوقَّع.' },
    { re: /favicon/, why: 'لا أيقونة في المستودع. متوقَّع وغير ضارّ.' },
    { re: /Refused to apply inline style/, why:
      'من الضابطَين السالبَين في §١ وحدهما: يحقنان سمة style عمداً ليثبتا أن '
      + 'السياسة تحجبها. حصيلة التطبيق نفسه صفر — انظر §٧.' },
  ];
  let blockers = 0;
  for (const [key, n] of seen) {
    const [type, text] = [key.split('|')[0], key.slice(key.indexOf('|') + 1)];
    if (type !== 'error' && type !== 'warning' && type !== 'pageerror'
        && type !== 'requestfailed') continue;
    const hit = EXPECTED.filter((e) => e.re.test(text))[0];
    if (hit) console.log('  · EXPECTED/BENIGN ×' + n + ' [' + type + '] '
      + text.slice(0, 90) + '\n      ⤷ ' + hit.why);
    else { blockers++;
      console.log('  · OPEN BLOCKER ×' + n + ' [' + type + '] ' + text.slice(0, 140)); }
  }
  chk('لا رسالة كونسول غير مصنَّفة كمتوقَّعة', blockers === 0, String(blockers));

  console.log('\n──────────────────────────────────────────────');
  console.log('نطاق مُعلَن: three.js مُكعَّب (public/vendor يملؤه البناء) — '
    + 'بكسلات WebGL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.');
  console.log('CSP STYLE ARCHITECTURE: %d passed, %d failed', pass, fail);
  if (fail) process.exit(1);
})();
