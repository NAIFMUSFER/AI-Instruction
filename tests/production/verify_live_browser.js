/* ============================================================================
   tests/production/verify_live_browser.js
   التحقّق الإنتاجي الحيّ في متصفّح Chromium حقيقي عبر Playwright.

   ثلاث نتائج لا رابع لها ولا تُخلط:
     PASS         — رُصد السلوك الصحيح في صفحة محمَّلة فعلاً.
     FAIL         — رُصد سلوك خاطئ.
     NOT VERIFIED — تعذّر الرصد (شبكة، أو غياب Chromium/Playwright).
   لا يُحوَّل فحص لم يُنفَّذ إلى نجاح، ولا يُستنتج نجاح من قراءة ملفّ.

   المجموعات هنا:
     C — الإقلاع: لا page error، نافذة العرض تُهيَّأ، نموذج اختبار يُرسم،
         مخرج البكسلات غير فارغ، سياق WebGL متاح، وانتقالات
         ENGINEERING / PBR / ARCHITECTURAL تنجح.
     D — المرور الوظيفي: إنشاء/فتح مشروع، توليد أو تحميل عيّنة، تحديد عنصر،
         فحصه، دخول التحرير، معاينة، إلغاء، معاينة ثانية، إيداع، تراجع،
         إعادة، فتح لوحة BIM، فتح لوحة التوثيق، تصدير.
     E — الاستجابة: 375 · 390 · 430 · 768 · 1024 · 1440 · 1920 — لا فيض أفقي،
         وكل عنصر تحكّم رئيسي قابل للوصول.
     F — العربية: lang=ar و dir=rtl، ولا نصّ إنجليزي ذو معنى في واجهة الكروم،
         ولا فيض أفقي.
     G — أصل النشر في المتصفّح: window.ACS_BUILD_INFO.

   المجموعات A و B و G(HTTP) في tests/production/verify_live.py.

     node tests/production/verify_live_browser.js
     node tests/production/verify_live_browser.js --frontend https://…
     node tests/production/verify_live_browser.js --expect-sha <sha>
     ACS_VERIFY_FRONTEND=http://127.0.0.1:8901 node tests/production/verify_live_browser.js

   رموز الخروج: 0 لا فشل · 1 فشل مرصود · 2 لم يُرصد شيء إطلاقاً.
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const OUTDIR = path.join(HERE, 'outputs');
/* محلّل البكسلات المُستعمل هو نفسه المشحون مع اختبارات النشر — لا نسخة ثانية */
const PX = require(path.join(ROOT, 'tests', 'deploy', 'lib_viewport_pixels.js'));

const DEFAULT_FRONTEND = 'https://sprightly-selkie-d906c3.netlify.app';
const NV_SUFFIX = 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED';
const CHROMIUM_PATH = '/opt/pw-browsers/chromium';

/* ── الوسائط ─────────────────────────────────────────────────────────────── */
function argOf(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}
const FRONTEND = String(argOf('--frontend',
  process.env.ACS_VERIFY_FRONTEND || DEFAULT_FRONTEND)).replace(/\/+$/, '');
const EXPECT_SHA = String(argOf('--expect-sha',
  process.env.ACS_VERIFY_EXPECT_SHA || '')).trim();
const JSON_OUT = argOf('--json', path.join(OUTDIR, 'verify_live_browser.json'));
const NAV_TIMEOUT = Number(argOf('--timeout', '90000'));

/* ── سجلّ النتائج ────────────────────────────────────────────────────────── */
const ROWS = [];
function record(group, id, name, status, detail, reason) {
  const row = { group, id, name, status,
    detail: String(detail === undefined ? '' : detail).slice(0, 600),
    reason: String(reason === undefined ? '' : reason).slice(0, 400) };
  ROWS.push(row);
  const mark = status === 'PASS' ? '✓' : (status === 'FAIL' ? '✗' : '―');
  let line = '  ' + mark + ' ' + id.padEnd(5) + ' ' + name;
  if (status === 'NOT VERIFIED') {
    line += '\n      ' + NV_SUFFIX;
    if (row.reason) line += '\n      reason: ' + row.reason.slice(0, 300);
  } else if (row.detail) line += '\n      ' + row.detail.slice(0, 300);
  console.log(line);
  return row;
}
const ok = (g, id, name, cond, detail) =>
  record(g, id, name, cond ? 'PASS' : 'FAIL', detail);
const nv = (g, id, name, reason) =>
  record(g, id, name, 'NOT VERIFIED', '', reason);
const count = s => ROWS.filter(r => r.status === s).length;

/* كل فحص مُخطَّط له، ليعرف مسار الفشل ماذا يُعلن NOT VERIFIED بدل الصمت */
const PLAN = [
  ['C', 'C1', 'no uncaught page error during boot'],
  ['C', 'C2', 'the viewport initialises (canvas sized, WebGL context available)'],
  ['C', 'C3', 'a WebGL rendering context is really available'],
  ['C', 'C4', 'a test model renders (canonical meshes, draw calls, triangles)'],
  ['C', 'C5', 'the pixel output is non-empty (decoded RGBA, not black)'],
  ['C', 'C6', 'ENGINEERING / PBR / ARCHITECTURAL mode transitions succeed'],
  ['C', 'C7', 'no failed asset request and no CSP violation during boot'],
  ['C', 'C8', 'no uncaught page error after the whole run'],
  ['D', 'D1', 'create/open a project'],
  ['D', 'D2', 'generate or load a fixture model'],
  ['D', 'D3', 'select an element'],
  ['D', 'D4', 'inspect the selected element'],
  ['D', 'D5', 'enter edit mode'],
  ['D', 'D6', 'preview a change without touching the committed model'],
  ['D', 'D7', 'cancel the preview'],
  ['D', 'D8', 'preview again'],
  ['D', 'D9', 'commit the change'],
  ['D', 'D10', 'undo'],
  ['D', 'D11', 'redo'],
  ['D', 'D12', 'open the BIM panel'],
  ['D', 'D13', 'open the documentation panel'],
  ['D', 'D14', 'export'],
  ['E', 'E1', 'no horizontal overflow at 375/390/430/768/1024/1440/1920'],
  ['E', 'E2', 'the primary controls stay reachable at every width'],
  ['F', 'F1', 'the document declares lang=ar and dir=rtl'],
  ['F', 'F2', 'no meaningful untranslated English chrome'],
  ['F', 'F3', 'no horizontal overflow in the Arabic layout'],
  ['H', 'H1', 'the deployed page is a shell under 200 KB with /app/main.js as '
    + 'its only module entry'],
  ['H', 'H2', 'the classic boot scripts and the external stylesheet load and apply'],
  ['H', 'H3', 'no <style> block, no style= attribute and no inline event handler'],
  ['H', 'H4', 'the deployed CSP raised no violation in a real browser'],
  ['G', 'G5', 'window.ACS_BUILD_INFO carries the frontend build SHA and timestamp'],
  ['G', 'G6', 'the frontend build SHA matches --expect-sha'],
];
function planRemaining(reason) {
  const done = new Set(ROWS.map(r => r.id));
  for (const [g, id, name] of PLAN) if (!done.has(id)) nv(g, id, name, reason);
}

/* عناصر التحكّم الرئيسية في شريط مساحة العمل — أسماؤها من public/index.html */
const PRIMARY_CONTROLS = ['#wsBtnTree', '#wsBtnMode', '#wsBtnUndo', '#wsBtnRedo',
  '#wsBtnHistory', '#wsBtnIssues', '#wsBtnExport', '#wsBtnLang', '#wsBtnInsp'];
const VIEWPORTS = [375, 390, 430, 768, 1024, 1440, 1920];

/* F-09 — الصفحة المنشورة قشرة. الرقم نفسه المستعمل في tests/production/
   verify_live.py، ومصدره أن الملفّ الواحد قبل التفكيك كان 1,863,894 بايت. */
const SHELL_MAX_BYTES = 200000;

/* مصطلحات تقنية إنجليزية مقبولة داخل واجهة عربية — لا تُعدّ «غير مترجمة».
   القائمة صريحة عمداً: أي كلمة إنجليزية خارجها تُعَدّ chrome غير مترجم. */
const ALLOWED_EN = new Set(['ACS', 'BIM', 'IFC', 'PDF', 'GLB', 'GLTF', 'JSON',
  'CSV', 'SVG', 'PNG', 'DXF', 'DWG', 'STEP', 'COBIE', 'MEP', 'FLS', 'HVAC',
  'VIEW', 'EDIT', 'AI', 'VR', 'AR', 'XR', 'WEBGL', 'GL', 'UI', 'ID', 'E', 'P',
  'A', 'B', 'I', 'EN', 'AR', '3D', '2D', 'LED', 'PBR', 'AO', 'FOV', 'M', 'CM',
  'MM', 'KM', 'M2', 'M3', 'REV', 'CTRL', 'SHIFT', 'ALT', 'ESC', 'OK']);

function untranslated(text) {
  const words = String(text || '').match(/[A-Za-z][A-Za-z0-9_]{1,}/g) || [];
  const out = [];
  for (const w of words) {
    if (ALLOWED_EN.has(w.toUpperCase())) continue;
    if (/^\d+$/.test(w)) continue;
    out.push(w);
  }
  return out;
}

/* ── منفذ الخروج الموحَّد ────────────────────────────────────────────────── */
function finish(extra) {
  const nPass = count('PASS'), nFail = count('FAIL'), nNv = count('NOT VERIFIED');
  const code = nFail ? 1 : (nPass === 0 ? 2 : 0);
  const summary = Object.assign({
    schema: 'acs-production-verification/1.0.0',
    tool: 'tests/production/verify_live_browser.js',
    started_at: new Date().toISOString(),
    frontend: FRONTEND,
    expect_sha: EXPECT_SHA || null,
    groups: ['C', 'D', 'E', 'F', 'G(browser)'],
    counts: { pass: nPass, fail: nFail, not_verified: nNv, total: ROWS.length },
    exit_code: code,
    verdict: nFail ? 'FAIL' : (nPass === 0 ? NV_SUFFIX : 'PASS'),
    checks: ROWS
  }, extra || {});
  let wrote;
  try {
    fs.mkdirSync(path.dirname(path.resolve(JSON_OUT)), { recursive: true });
    fs.writeFileSync(JSON_OUT, JSON.stringify(summary, null, 2) + '\n', 'utf8');
    wrote = JSON_OUT;
  } catch (e) { wrote = '<not written: ' + e.message + '>'; }
  console.log('\n' + '─'.repeat(70));
  console.log('BROWSER LAYER: ' + nPass + ' PASS · ' + nFail + ' FAIL · '
    + nNv + ' NOT VERIFIED (of ' + ROWS.length + ' checks)');
  console.log('summary: ' + wrote);
  if (code === 2) console.log('VERDICT: ' + NV_SUFFIX
    + ' — no pixel was rendered here and nothing is claimed.');
  else if (code === 1) console.log('VERDICT: FAIL — at least one check observed '
    + 'wrong behaviour.');
  else console.log('VERDICT: PASS — no observed failure.');
  process.exit(code);
}

/* ── فحوص مشتركة ─────────────────────────────────────────────────────────
   تُستدعى من المسار السليم ومن المسار المتدهور معاً. حين لا يقلع التطبيق تبقى
   خصائص المستند (lang/dir، الفيض الأفقي، ACS_BUILD_INFO) قابلة للرصد فعلاً،
   فقياسها واجب؛ وما يعتمد على مساحة عمل حيّة وحده يُعلَن NOT VERIFIED.       */

async function checkResponsive(pg, appReady) {
  console.log('\n── E · الاستجابة عبر سبعة عروض ──');
  const overflow = [], unreachable = [];
  for (const w of VIEWPORTS) {
    const h = w < 500 ? 844 : (w < 800 ? 1024 : 900);
    await pg.setViewportSize({ width: w, height: h });
    await pg.waitForTimeout(450);
    const r = await pg.evaluate((controls) => {
      const de = document.documentElement;
      const over = de.scrollWidth - window.innerWidth;
      const out = [];
      for (const sel of controls) {
        const el = document.querySelector(sel);
        if (!el) { out.push({ sel, why: 'absent' }); continue; }
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden'
          || Number(cs.opacity) === 0) { out.push({ sel, why: 'hidden' }); continue; }
        const b = el.getBoundingClientRect();
        if (!(b.width >= 20 && b.height >= 20)) {
          out.push({ sel, why: 'tap target ' + Math.round(b.width) + 'x'
            + Math.round(b.height) }); continue; }
        if (b.left < 0 || b.top < 0 || b.right > window.innerWidth + 1
          || b.bottom > window.innerHeight + 1) {
          out.push({ sel, why: 'outside the viewport' }); continue; }
        const hit = document.elementFromPoint(b.left + b.width / 2,
          b.top + b.height / 2);
        if (!(hit === el || el.contains(hit) || (hit && hit.contains(el))))
          out.push({ sel, why: 'covered by another element' });
      }
      return { overflow: over, scrollWidth: de.scrollWidth,
        innerWidth: window.innerWidth, unreachable: out };
    }, appReady ? PRIMARY_CONTROLS : []);
    console.log('  ' + String(w).padStart(4) + 'px  overflow=' + r.overflow
      + (appReady ? ('  unreachable=' + r.unreachable.length) : ''));
    if (r.overflow > 1) overflow.push(w + 'px: scrollWidth ' + r.scrollWidth
      + ' > innerWidth ' + r.innerWidth);
    if (r.unreachable.length) unreachable.push(w + 'px: '
      + r.unreachable.map(u => u.sel + ' (' + u.why + ')').join(', '));
  }
  ok('E', 'E1', 'no horizontal overflow at ' + VIEWPORTS.join('/'),
    overflow.length === 0, overflow.join(' | ')
    || 'scrollWidth ≤ innerWidth at all ' + VIEWPORTS.length + ' widths');
  if (!appReady) {
    nv('E', 'E2', 'the primary controls stay reachable at every width',
      'the workspace toolbar never rendered because the application did not '
      + 'boot, so no primary control could be hit-tested');
  } else {
    ok('E', 'E2', 'the primary controls stay reachable at every width ('
      + PRIMARY_CONTROLS.join(' ') + ')',
      unreachable.length === 0, unreachable.join(' | ')
      || 'all ' + PRIMARY_CONTROLS.length
      + ' controls visible, sized and hit-testable');
  }
}

async function checkArabic(pg, appReady) {
  console.log('\n── F · العربية: lang/dir والنصّ غير المترجم ──');
  await pg.setViewportSize({ width: 1440, height: 900 });
  await pg.waitForTimeout(400);
  const langInfo = await pg.evaluate(() => ({
    lang: document.documentElement.getAttribute('lang'),
    dir: document.documentElement.getAttribute('dir'),
    computedDir: getComputedStyle(document.documentElement).direction
  }));
  ok('F', 'F1', 'the document declares lang=ar and dir=rtl',
    langInfo.lang === 'ar' && langInfo.dir === 'rtl'
    && langInfo.computedDir === 'rtl', JSON.stringify(langInfo));

  if (!appReady) {
    nv('F', 'F2', 'no meaningful untranslated English chrome',
      'the application chrome never rendered, so there was no interface text '
      + 'to inspect — an empty inspection is not a pass');
  } else {
    const chrome = await pg.evaluate(() => {
      const sels = ['.ws-top button', '.ws-top span', '#wsTreeTitle', '#wsInspTitle',
        '#wsStMode', '#wsStRev', '#wsStLevel', '#wsStCompliance', '#wsStNav',
        '#wsLblMode', '#wsLblRev', '#wsLblLevel', '#wsLblCompliance', '#wsLblNav',
        '#adTitle', '#pqTitle', '#bxTitle', '#dcTitle'];
      const out = [];
      for (const s of sels) {
        document.querySelectorAll(s).forEach(el => {
          const cs = getComputedStyle(el);
          if (cs.display === 'none' || cs.visibility === 'hidden') return;
          const t = (el.textContent || '').trim();
          if (t) out.push({ sel: s, text: t.slice(0, 60) });
        });
      }
      return out;
    });
    const offenders = [];
    for (const c of chrome) {
      const bad = untranslated(c.text);
      if (bad.length) offenders.push(c.sel + ' → ' + JSON.stringify(bad));
    }
    if (chrome.length === 0) {
      nv('F', 'F2', 'no meaningful untranslated English chrome',
        'no chrome string was found to inspect — an empty inspection is not a pass');
    } else {
      ok('F', 'F2', 'no meaningful untranslated English chrome (technical '
        + 'acronyms are allow-listed) — ' + chrome.length + ' strings inspected',
        offenders.length === 0,
        offenders.slice(0, 8).join(' | ') || (chrome.length
          + ' chrome strings inspected, none carried untranslated English'));
    }
  }

  const rtlOverflow = await pg.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    dir: getComputedStyle(document.documentElement).direction }));
  ok('F', 'F3', 'no horizontal overflow in the Arabic (RTL) layout',
    rtlOverflow.overflow <= 1, JSON.stringify(rtlOverflow));
}

async function checkBuildInfo(pg, expectSha) {
  console.log('\n── G · أصل بناء الواجهة من window.ACS_BUILD_INFO ──');
  const buildInfo = await pg.evaluate(() => {
    const b = window.ACS_BUILD_INFO;
    if (!b) return { present: false };
    const sha = b.git_sha || b.sha || null;
    /* رمز نائب لم يستبدله البناء ليس هويّة — يُصنَّف صراحةً لا يُقبل كـSHA */
    const placeholder = typeof sha === 'string' && /^__[A-Z0-9_]+__$/.test(sha);
    return { present: true, value: b, placeholder,
      substituted: b.substituted !== false && !placeholder,
      provenance: b.provenance || null,
      git_sha: placeholder ? null : sha,
      built_at: b.built_at || b.builtAt || null };
  });
  ok('G', 'G5', 'window.ACS_BUILD_INFO carries a substituted frontend build SHA '
    + 'and deployment timestamp',
    buildInfo.present === true && !!buildInfo.git_sha && !!buildInfo.built_at
    && buildInfo.substituted === true,
    !buildInfo.present
      ? 'window.ACS_BUILD_INFO is undefined on the deployed page — the '
        + 'frontend ships no build provenance, so the running page cannot be '
        + 'tied to a revision'
      : (buildInfo.placeholder || buildInfo.substituted === false
        ? 'window.ACS_BUILD_INFO exists but its identity tokens were never '
          + 'substituted by a build step (provenance=' + buildInfo.provenance
          + ') — the running page is UNPROVENANCED: '
          + JSON.stringify(buildInfo.value).slice(0, 200)
        : JSON.stringify(buildInfo.value).slice(0, 300)));

  if (!expectSha) {
    nv('G', 'G6', 'the frontend build SHA matches --expect-sha',
      'no expected revision was supplied; pass --expect-sha <sha> to turn this '
      + 'into a measured check');
  } else if (!buildInfo.git_sha) {
    nv('G', 'G6', 'the frontend build SHA matches --expect-sha',
      'no frontend build SHA could be observed, so nothing could be compared '
      + 'against ' + expectSha);
  } else {
    ok('G', 'G6', 'the frontend build SHA matches --expect-sha',
      String(buildInfo.git_sha).startsWith(expectSha)
      || expectSha.startsWith(String(buildInfo.git_sha)),
      'expected=' + expectSha + ' observed=' + buildInfo.git_sha);
  }
  return buildInfo;
}

/* ── H · شكل ما نُشر فعلاً: قشرة + وحدات + ورقة أنماط خارجية (F-09/F-11) ──
   يُقاس على المستند المخدوم لا على المستودع. نشرٌ ما زال يحمل التطبيق داخل
   الصفحة ليس «نجاحاً» — هو نشر شجرة أخرى، ويجب أن يُرى كذلك. */
async function checkShippedShape(pg) {
  console.log('\n── H · شكل الواجهة المنشورة: قشرة ووحدات وأنماط خارجية ──');
  const shape = await pg.evaluate(() => ({
    html_bytes: document.documentElement.outerHTML.length,
    inline_scripts: Array.from(document.querySelectorAll('script'))
      .filter(x => !x.src).map(x => x.type || 'text/javascript'),
    module_entries: Array.from(document.querySelectorAll('script[type=module]'))
      .map(x => x.getAttribute('src')),
    boot_scripts: Array.from(document.querySelectorAll('script[src]'))
      .map(x => x.getAttribute('src')).filter(u => /^\/app\/boot\//.test(u)),
    stylesheets: Array.from(document.querySelectorAll('link[rel=stylesheet]'))
      .map(x => x.getAttribute('href')),
    sheet_count: document.styleSheets.length,
    css_rules: (function () { let n = 0;
      for (const s of document.styleSheets) {
        try { n += s.cssRules.length; } catch (e) { } } return n; })(),
    style_blocks: document.querySelectorAll('style').length,
    inline_style_attrs: document.querySelectorAll('[style]').length,
    inline_handlers: Array.from(document.querySelectorAll('*'))
      .filter(el => Array.from(el.attributes)
        .some(a => /^on[a-z]+$/.test(a.name)))
      .map(el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')).slice(0, 6)
  }));
  const shellProblems = [];
  if (shape.html_bytes >= SHELL_MAX_BYTES)
    shellProblems.push('the served document is ' + shape.html_bytes
      + ' bytes — a shell must be under ' + SHELL_MAX_BYTES);
  if (shape.inline_scripts.length !== 1
    || shape.inline_scripts[0] !== 'importmap')
    shellProblems.push('inline <script> types: '
      + JSON.stringify(shape.inline_scripts));
  if (JSON.stringify(shape.module_entries) !== JSON.stringify(['/app/main.js']))
    shellProblems.push('module entry points: '
      + JSON.stringify(shape.module_entries));
  ok('H', 'H1', 'the deployed page is a SHELL under ' + SHELL_MAX_BYTES
    + ' bytes whose only inline script is the import map and whose only module '
    + 'entry is /app/main.js',
    shellProblems.length === 0,
    shellProblems.join(' | ') || shape.html_bytes
      + ' bytes, entry /app/main.js, one inline import map');
  ok('H', 'H2', 'the classic boot scripts and the EXTERNAL stylesheet are '
    + 'loaded and applied by the deployed page',
    shape.boot_scripts.length >= 1 && shape.stylesheets.length === 1
    && /^\/app\/styles\//.test(shape.stylesheets[0] || '')
    && shape.sheet_count >= 1 && shape.css_rules > 200,
    JSON.stringify({ boot: shape.boot_scripts, css: shape.stylesheets,
      sheets: shape.sheet_count, rules: shape.css_rules }));
  ok('H', 'H3', 'the deployed document carries no <style> block, no style= '
    + 'attribute and no inline event handler — under the strict CSP the last '
    + 'two are dead code, not styling',
    shape.style_blocks === 0 && shape.inline_style_attrs === 0
    && shape.inline_handlers.length === 0,
    JSON.stringify({ style_blocks: shape.style_blocks,
      style_attrs: shape.inline_style_attrs,
      handlers: shape.inline_handlers }));
  return shape;
}

/* الفحوص التي تبقى قابلة للرصد على مستند حُمِّل ولم يُقلع تطبيقه */
async function documentLevelChecks(pg, expectSha, cspViolations) {
  await checkShippedShape(pg);
  reportCSP(cspViolations);
  await checkResponsive(pg, false);
  await checkArabic(pg, false);
  await checkBuildInfo(pg, expectSha);
}

/* F-11 — خرق السياسة على النشر الحقيقي فشل مرصود لا بيئة ناقصة */
function reportCSP(cspViolations) {
  const v = cspViolations || [];
  ok('H', 'H4', 'the deployed Content-Security-Policy raised no violation in a '
    + 'real browser', v.length === 0,
    v.slice(0, 4).join(' | ') || 'no CSP violation reported by Chromium');
}

/* ── التشغيل ─────────────────────────────────────────────────────────────── */
(async () => {
  console.log('ACS PRODUCTION VERIFICATION — real Chromium layer');
  console.log('  frontend : ' + FRONTEND);
  console.log('  started  : ' + new Date().toISOString());

  let chromium = null;
  try { ({ chromium } = require('playwright')); }
  catch (e) {
    planRemaining('Playwright is not installed here: ' + e.message);
    finish({ environment: { playwright: false } });
  }
  const execPath = fs.existsSync(CHROMIUM_PATH) ? CHROMIUM_PATH : undefined;
  console.log('  chromium : ' + (execPath || 'playwright default download'));

  let browser;
  try {
    browser = await chromium.launch(execPath ? { executablePath: execPath } : {});
  } catch (e) {
    planRemaining('Chromium could not be launched: ' + String(e.message).slice(0, 200));
    finish({ environment: { playwright: true, chromium: false } });
  }

  const pg = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  pg.setDefaultTimeout(NAV_TIMEOUT);
  pg.setDefaultNavigationTimeout(NAV_TIMEOUT);
  const pageErrors = [], badResponses = [], failedRequests = [], cspViolations = [];
  pg.on('pageerror', e => pageErrors.push(String(e && e.message || e).slice(0, 240)));
  pg.on('response', r => { if (r.status() >= 400)
    badResponses.push('HTTP ' + r.status() + ' ' + r.url().slice(0, 140)); });
  pg.on('requestfailed', r => failedRequests.push(
    r.url().slice(0, 140) + ' — ' + ((r.failure() || {}).errorText || 'failed')));
  pg.on('console', m => {
    const t = m.text() || '';
    if (/Content Security Policy|Refused to (load|execute|connect)/i.test(t))
      cspViolations.push(t.slice(0, 220));
  });

  /* التحميل — أي تعذّر هنا يعني NOT VERIFIED لكل ما بعده، لا فشل منطقي */
  console.log('\n── loading the deployed frontend ──');
  let response = null;
  try {
    response = await pg.goto(FRONTEND, { waitUntil: 'load', timeout: NAV_TIMEOUT });
  } catch (e) {
    const msg = String(e.message).split('\n')[0].slice(0, 220);
    /* Chromium يحوّل تحدّي المصادقة (401 مع WWW-Authenticate) إلى فشل تنقّل
       ERR_INVALID_AUTH_CREDENTIALS، فلا تصل حالة HTTP إلى الشيفرة. اعتبار ذلك
       «تعذّر الوصول» يخفي بالضبط الحالة التي يجب أن تُعلَن: موقع محميّ.
       الحجب هنا سلوك مرصود لا بيئة ناقصة ⇒ FAIL بالرمز الحرفي. */
    if (/ERR_INVALID_AUTH_CREDENTIALS|401|403|ERR_HTTP_RESPONSE_CODE_FAILURE/i
        .test(msg)) {
      record('C', 'C0', 'the frontend is publicly reachable', 'FAIL',
        'FRONTEND_ACCESS_RESTRICTED — ' + FRONTEND + ' answered an '
        + 'authentication challenge that Chromium reported as "' + msg + '". '
        + 'No authentication configuration exists in netlify.toml or '
        + 'public/_headers in this tree, so any restriction is set in the '
        + 'Netlify site dashboard (Site settings ▸ Access control), outside '
        + 'the repository. The site is NOT publicly verified.');
      await browser.close();
      planRemaining('the frontend refused access (FRONTEND_ACCESS_RESTRICTED), '
        + 'so nothing behind it could be observed');
      finish({ environment: { playwright: true, chromium: true, loaded: false },
        access_restricted: true });
    }
    await browser.close();
    planRemaining('the frontend could not be loaded: ' + msg);
    finish({ environment: { playwright: true, chromium: true, loaded: false } });
  }
  const status = response ? response.status() : 0;
  console.log('  HTTP ' + status + ' ' + (response ? response.url() : ''));
  if (status === 401 || status === 403) {
    record('C', 'C0', 'the frontend is publicly reachable', 'FAIL',
      'FRONTEND_ACCESS_RESTRICTED — HTTP ' + status + ' at ' + FRONTEND
      + '. No authentication configuration exists in netlify.toml or '
      + 'public/_headers in this tree, so any restriction is set in the '
      + 'Netlify site dashboard, outside the repository. The site is NOT '
      + 'publicly verified.');
    await browser.close();
    planRemaining('the frontend answered HTTP ' + status
      + ' (FRONTEND_ACCESS_RESTRICTED) so nothing behind it could be observed');
    finish({ environment: { playwright: true, chromium: true, loaded: false },
      http_status: status });
  }

  /* ═══ C — الإقلاع ═══════════════════════════════════════════════════════ */
  console.log('\n── C · إقلاع المتصفّح الحقيقي ──');
  let ready = false;
  try {
    await pg.waitForFunction('window.ACS && window.ACS.ready===true', null,
      { timeout: 45000 });
    ready = true;
  } catch (e) { /* يُبلَّغ أدناه */ }

  if (!ready) {
    ok('C', 'C1', 'no uncaught page error during boot', pageErrors.length === 0,
      pageErrors.slice(0, 3).join(' | ') || 'no page error captured');
    record('C', 'C2', 'the viewport initialises (window.ACS.ready)', 'FAIL',
      'window.ACS.ready never became true within 45s; failed requests: '
      + (failedRequests.slice(0, 3).join(' | ') || 'none') + '; bad responses: '
      + (badResponses.slice(0, 3).join(' | ') || 'none'));
    /* الصفحة حُمِّلت فعلاً، فبعض الفحوص ما زالت قابلة للرصد على مستوى المستند.
       التنازل عنها هنا يكون تكاسلاً لا أمانة: نقيس ما يمكن قياسه، ونُعلن
       NOT VERIFIED لما يعتمد على تطبيق لم يقلع فقط. */
    await documentLevelChecks(pg, EXPECT_SHA, cspViolations);
    await browser.close();
    planRemaining('the application never reached window.ACS.ready, so no '
      + 'downstream behaviour could be observed');
    finish({ environment: { playwright: true, chromium: true, loaded: true,
      ready: false }, http_status: status });
  }

  ok('C', 'C1', 'no uncaught page error during boot', pageErrors.length === 0,
    pageErrors.slice(0, 3).join(' | ') || '0 page errors');

  /* بطاقة الدخول تسبق الاستوديو — نمرّ منها كما يمرّ المستعمل */
  try {
    if (await pg.$('#lgGo')) {
      await pg.fill('#lgName', 'مُتحقّق الإنتاج').catch(() => {});
      await pg.fill('#lgEmail', 'verify@example.invalid').catch(() => {});
      await pg.fill('#lgProject', 'production-verification').catch(() => {});
      await pg.click('#lgGo');
      await pg.waitForTimeout(1500);
    }
  } catch (e) { /* لا يُخفي شيئاً: الفحوص التالية ستكشف أي تعثّر */ }

  const gl = await pg.evaluate(() => {
    try {
      const c = document.createElement('canvas');
      const ctx = c.getContext('webgl2') || c.getContext('webgl');
      if (!ctx) return { available: false };
      return { available: true,
        version: String(ctx.getParameter(ctx.VERSION) || ''),
        renderer: String(ctx.getParameter(ctx.RENDERER) || '') };
    } catch (e) { return { available: false, error: String(e.message) }; }
  });
  ok('C', 'C3', 'a WebGL rendering context is really available',
    gl.available === true, JSON.stringify(gl));

  /* نموذج اختبار قانوني — نستعمل المثال المشحون مع الصفحة، فلا نخترع هندسة */
  await pg.evaluate(() => { if (window.ACS.showExample) window.ACS.showExample(); });
  await pg.waitForTimeout(1500);
  await pg.evaluate(() => new Promise(r =>
    requestAnimationFrame(() => requestAnimationFrame(r))));

  const diag = await pg.evaluate(() =>
    (typeof window.ACS.renderDiagnostics === 'function')
      ? window.ACS.renderDiagnostics() : null);
  ok('C', 'C2', 'the viewport initialises (canvas has non-zero backing and CSS size)',
    !!diag && diag.canvas_width > 0 && diag.canvas_height > 0
    && diag.css_width > 0 && diag.css_height > 0
    && diag.projection_matrix_finite === true,
    diag ? JSON.stringify({ canvas: [diag.canvas_width, diag.canvas_height],
      css: [diag.css_width, diag.css_height],
      projection_finite: diag.projection_matrix_finite })
      : 'renderDiagnostics() is unavailable');

  ok('C', 'C4', 'a test model renders (canonical meshes, draw calls, triangles)',
    !!diag && diag.canonical_meshes > 0 && diag.visible_meshes > 0
    && diag.draw_calls > 0 && diag.triangles > 0
    && diag.camera_in_frustum === true,
    diag ? JSON.stringify({ canonical: diag.canonical_meshes,
      visible: diag.visible_meshes, calls: diag.draw_calls,
      triangles: diag.triangles, in_frustum: diag.camera_in_frustum })
      : 'renderDiagnostics() is unavailable');

  const px = await PX.analysePageViewport(pg, 'canvas');
  ok('C', 'C5', 'the pixel output is non-empty (decoded RGBA via '
    + 'tests/deploy/lib_viewport_pixels.js)',
    px.verdict === 'VISIBLE_CONTENT',
    JSON.stringify({ verdict: px.verdict, sampled: px.sampled,
      mean: px.luminance_mean, near_black_pct: px.near_black_pct,
      buckets: px.luminance_buckets, reasons: px.reasons }));

  const modes = [];
  for (const mode of ['ENGINEERING', 'PBR', 'ARCHITECTURAL']) {
    /* ARCHITECTURAL يحتاج ضبطاً مُطبَّقاً أولاً — نُطبّقه كما تفعل اللوحة */
    const r = await pg.evaluate(async (m) => {
      try {
        if (m === 'ARCHITECTURAL' && window.ACS.archdetail && window.ACS.adApply) {
          const c = window.ACS.archdetail.config('DETAIL_STANDARD', 'REQUESTED',
            'NONE', 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER',
            'CLEAR_SKY', null, false, [], window.ACS.adModelSummary());
          if (c && c.valid) window.ACS.adApply(c.config);
        }
        const out = window.ACS.adMode(m);
        return { mode: m, applied: !!(out && out.applied),
          issues: (out && out.issues || []).map(i => i.code || String(i)) };
      } catch (e) { return { mode: m, applied: false, error: String(e.message) }; }
    }, mode);
    await pg.evaluate(() => new Promise(r2 =>
      requestAnimationFrame(() => requestAnimationFrame(r2))));
    const p = await PX.analysePageViewport(pg, 'canvas');
    const d = await pg.evaluate(() => window.ACS.renderDiagnostics());
    modes.push({ mode, applied: r.applied, issues: r.issues, error: r.error,
      pixels: p.verdict, draw_calls: d.draw_calls });
  }
  await pg.evaluate(() => { try { window.ACS.adMode('ENGINEERING'); } catch (e) {} });
  ok('C', 'C6', 'ENGINEERING / PBR / ARCHITECTURAL mode transitions succeed and '
    + 'each leaves a drawn, non-black viewport',
    modes.every(m => m.applied && m.pixels === 'VISIBLE_CONTENT' && m.draw_calls > 0),
    JSON.stringify(modes));

  ok('C', 'C7', 'no failed asset request and no CSP violation during boot',
    badResponses.length === 0 && failedRequests.length === 0
    && cspViolations.length === 0,
    JSON.stringify({ bad: badResponses.slice(0, 3),
      failed: failedRequests.slice(0, 3), csp: cspViolations.slice(0, 3) }));

  /* ═══ D — المرور الوظيفي ════════════════════════════════════════════════ */
  console.log('\n── D · المرور الوظيفي الكامل ──');
  const has = await pg.evaluate(() => ({
    ws: !!(window.ACS && window.ACS.workspace),
    bim: !!(window.ACS && window.ACS.bim && window.ACS.bim.panel),
    docs: !!(window.ACS && window.ACS.docs && window.ACS.docs.panel)
  }));

  if (!has.ws) {
    for (const [g, id, name] of PLAN)
      if (g === 'D' && !ROWS.some(r => r.id === id))
        nv(g, id, name, 'window.ACS.workspace is not exposed by the deployed page, '
          + 'so the workflow could not be driven');
  } else {
    /* D1+D2 — المشروع يُنشأ عبر تدفّق المنتج نفسه (WS.generate) */
    const created = await pg.evaluate(() => {
      try {
        const r = window.ACS.workspace.generate({ name: 'production-verification',
          type: 'residential', w: 30, d: 24, requirements: 'مبنى تحقّق إنتاجي' });
        const p = window.ACS.workspace.project();
        return { ok: !!(r && r.project), name: p && p.name,
          rev: p && p.current_revision, hash: p && p.model_hash,
          rooms: p ? Object.keys((p.model.floors || {})).reduce((n, k) =>
            n + ((p.model.floors[k].rooms || []).length), 0) : 0 };
      } catch (e) { return { ok: false, error: String(e.message) }; }
    });
    ok('D', 'D1', 'create/open a project', created.ok === true && !!created.rev,
      JSON.stringify(created));
    ok('D', 'D2', 'generate or load a fixture model (a real canonical model with '
      + 'spaces and a model hash)',
      created.ok === true && created.rooms > 0 && !!created.hash,
      JSON.stringify({ rooms: created.rooms, hash: created.hash }));

    /* D3 — التحديد يُشتقّ من الشجرة الحقيقية، بلا معرّف مكتوب يدوياً */
    const selected = await pg.evaluate(() => {
      try {
        const WS = window.ACS.workspace;
        const tree = WS.tree && WS.tree();
        const flat = window.ACS.flattenTree
          ? window.ACS.flattenTree(tree, {}, 0, 'ar') : [];
        const before = WS.project().model_hash;
        const cand = (flat || []).filter(n => /^g\./.test(String(n.id || '')));
        const id = (cand[0] || flat[flat.length - 1] || {}).id;
        if (!id) return { ok: false, error: 'the project tree exposed no node id' };
        WS.select(id);
        return { ok: WS.ui().selected_id === id, id,
          hash_unchanged: WS.project().model_hash === before };
      } catch (e) { return { ok: false, error: String(e.message) }; }
    });
    ok('D', 'D3', 'select an element (and selecting writes nothing to the model)',
      selected.ok === true && selected.hash_unchanged === true,
      JSON.stringify(selected));

    const inspected = await pg.evaluate(() => {
      const sections = document.querySelectorAll('#wsInsp [data-ws-section]').length;
      const provenance = document.querySelectorAll('#wsInsp [data-ws-provenance]').length;
      const rows = document.querySelectorAll('#wsInsp [data-ws-prop]').length;
      return { sections, provenance, rows,
        text: (document.getElementById('wsInsp') || {}).textContent
          ? document.getElementById('wsInsp').textContent.length : 0 };
    });
    ok('D', 'D4', 'inspect the selected element (inspector renders sections with '
      + 'provenance labels)',
      inspected.sections >= 1 && inspected.provenance > 0,
      JSON.stringify(inspected));

    const edit = await pg.evaluate(() => {
      try {
        window.ACS.workspace.setMode('EDIT');
        const ops = document.querySelectorAll('#wsInsp [data-ws-op]').length;
        return { mode: window.ACS.workspace.ui().ui_mode, ops,
          badge: (document.getElementById('wsStMode') || {}).textContent || '' };
      } catch (e) { return { error: String(e.message) }; }
    });
    ok('D', 'D5', 'enter edit mode', edit.mode === 'EDIT' && edit.ops > 0,
      JSON.stringify(edit));

    const previewOnce = async () => pg.evaluate(() => {
      try {
        const WS = window.ACS.workspace;
        const id = WS.ui().selected_id;
        const before = WS.project().model_hash;
        const rev = WS.project().current_revision;
        const r = WS.beginPreview({ type: 'RESIZE_SPACE', target_id: id,
          parameters: { w: 6.5, d: 4.5 } });
        const st = WS.state();
        return { valid: !!(r && r.valid !== false),
          candidate: !!(st.preview && (st.preview.candidate_model_hash
            || (st.preview.preview || {}).candidate_model_hash)),
          committed_unchanged: WS.project().model_hash === before
            && WS.project().current_revision === rev,
          badge: !!(document.getElementById('wsPreviewBadge')
            && document.getElementById('wsPreviewBadge').classList.contains('on')),
          before };
      } catch (e) { return { valid: false, error: String(e.message) }; }
    });

    const p1 = await previewOnce();
    ok('D', 'D6', 'preview a change without touching the committed model',
      p1.valid === true && p1.committed_unchanged === true,
      JSON.stringify(p1));

    const cancelled = await pg.evaluate(() => {
      try {
        const WS = window.ACS.workspace;
        const before = WS.project().model_hash;
        const rev = WS.project().current_revision;
        WS.cancelPreview();
        return { hash_unchanged: WS.project().model_hash === before,
          rev_unchanged: WS.project().current_revision === rev,
          preview_cleared: !WS.state().preview,
          badge_off: !(document.getElementById('wsPreviewBadge')
            && document.getElementById('wsPreviewBadge').classList.contains('on')) };
      } catch (e) { return { error: String(e.message) }; }
    });
    ok('D', 'D7', 'cancel the preview (no revision, no hash change)',
      cancelled.hash_unchanged === true && cancelled.rev_unchanged === true
      && cancelled.preview_cleared === true,
      JSON.stringify(cancelled));

    const p2 = await previewOnce();
    ok('D', 'D8', 'preview again after cancelling',
      p2.valid === true && p2.committed_unchanged === true, JSON.stringify(p2));

    /* D9 — الإيداع بالزرّ نفسه الذي يضغطه المستعمل، لا باستدعاء داخلي */
    await pg.evaluate(() => {
      const a = document.getElementById('wsAck');
      if (a && !a.checked) a.checked = true;
    });
    let clicked = false;
    try {
      if (await pg.$('#wsCommitBtn')) { await pg.click('#wsCommitBtn'); clicked = true; }
    } catch (e) { /* يُبلَّغ في النتيجة */ }
    await pg.waitForTimeout(600);
    const committed = await pg.evaluate((before) => {
      const WS = window.ACS.workspace;
      const p = WS.project();
      return { hash_changed: p.model_hash !== before,
        history: (p.history || []).length,
        rev: p.current_revision,
        preview_cleared: !WS.state().preview };
    }, p2.before);
    ok('D', 'D9', 'commit the change through the commit button',
      clicked && committed.hash_changed === true
      && committed.preview_cleared === true && committed.history >= 2,
      JSON.stringify(Object.assign({ button_clicked: clicked }, committed)));

    const undone = await pg.evaluate(() => {
      try {
        const WS = window.ACS.workspace;
        const h1 = WS.project().model_hash;
        const u = WS.undo();
        return { valid: !!(u && u.valid !== false), h1,
          h2: WS.project().model_hash, changed: WS.project().model_hash !== h1 };
      } catch (e) { return { valid: false, error: String(e.message) }; }
    });
    ok('D', 'D10', 'undo', undone.valid === true && undone.changed === true,
      JSON.stringify(undone));

    const redone = await pg.evaluate((h1) => {
      try {
        const WS = window.ACS.workspace;
        const h2 = WS.project().model_hash;
        const r = WS.redo();
        const h3 = WS.project().model_hash;
        return { valid: !!(r && r.valid !== false), changed: h3 !== h2,
          restored: h3 === h1, h3 };
      } catch (e) { return { valid: false, error: String(e.message) }; }
    }, undone.h1);
    ok('D', 'D11', 'redo (and it restores the committed hash exactly)',
      redone.valid === true && redone.changed === true && redone.restored === true,
      JSON.stringify(redone));

    if (!has.bim) {
      nv('D', 'D12', 'open the BIM panel',
        'window.ACS.bim.panel is not exposed by the deployed page');
    } else {
      const bim = await pg.evaluate(() => {
        try {
          window.ACS.bim.panel.attach(window.ACS.workspace.project());
          window.ACS.bim.panel.open();
          const el = document.getElementById('bxPanel');
          return { open: !!(el && el.classList.contains('on')),
            body: (document.getElementById('bxBody') || {}).textContent
              ? document.getElementById('bxBody').textContent.length : 0 };
        } catch (e) { return { open: false, error: String(e.message) }; }
      });
      ok('D', 'D12', 'open the BIM panel', bim.open === true && bim.body > 0,
        JSON.stringify(bim));
      await pg.evaluate(() => { try { window.ACS.bim.panel.close(); } catch (e) {} });
    }

    if (!has.docs) {
      nv('D', 'D13', 'open the documentation panel',
        'window.ACS.docs.panel is not exposed by the deployed page');
    } else {
      const docs = await pg.evaluate(() => {
        try {
          window.ACS.docs.panel.attach(window.ACS.workspace.project());
          window.ACS.docs.panel.open();
          const el = document.getElementById('dcPanel');
          return { open: !!(el && el.classList.contains('on')),
            body: (document.getElementById('dcBody') || {}).textContent
              ? document.getElementById('dcBody').textContent.length : 0 };
        } catch (e) { return { open: false, error: String(e.message) }; }
      });
      ok('D', 'D13', 'open the documentation panel',
        docs.open === true && docs.body > 0, JSON.stringify(docs));
      await pg.evaluate(() => { try { window.ACS.docs.panel.close(); } catch (e) {} });
    }

    const exported = await pg.evaluate(() => {
      try {
        const WS = window.ACS.workspace;
        WS.exportPanel();
        const rows = document.querySelectorAll('#wsModalBody [data-ws-export]');
        const kinds = Array.prototype.slice.call(rows)
          .map(e => e.getAttribute('data-ws-export'));
        WS.closeModal();
        const p = WS.project();
        const d = window.ACS.exportDescriptor
          ? window.ACS.exportDescriptor(p, kinds[0] || 'MODEL_JSON', 'COMMITTED',
            null, '2026-01-01T00:00:00Z') : null;
        return { rows: rows.length, kinds,
          descriptor_valid: !!(d && d.valid),
          revision: d && d.descriptor && d.descriptor.metadata
            && d.descriptor.metadata.revision_id,
          hash: d && d.descriptor && d.descriptor.metadata
            && d.descriptor.metadata.model_hash,
          certifies_nothing: d && d.descriptor && d.descriptor.certifies_nothing };
      } catch (e) { return { rows: 0, error: String(e.message) }; }
    });
    ok('D', 'D14', 'export (the export centre lists kinds and a descriptor carries '
      + 'the revision and the model hash)',
      exported.rows > 0 && exported.descriptor_valid === true
      && !!exported.revision && !!exported.hash,
      JSON.stringify(exported));
  }

  /* ═══ E · F · G · H — تُقاس بنفس الدوالّ المشتركة في المسارين ═════════ */
  await checkShippedShape(pg);
  reportCSP(cspViolations);
  await checkResponsive(pg, true);
  await checkArabic(pg, true);
  const buildInfo = await checkBuildInfo(pg, EXPECT_SHA);

  ok('C', 'C8', 'no uncaught page error after the whole run',
    pageErrors.length === 0, pageErrors.slice(0, 4).join(' | ') || '0 page errors');

  await browser.close();
  finish({ environment: { playwright: true, chromium: true, loaded: true,
    ready: true }, http_status: status,
    observed: { webgl: gl, build_info: buildInfo.value || null,
      page_errors: pageErrors.slice(0, 10),
      failed_requests: failedRequests.slice(0, 10),
      csp_violations: cspViolations.slice(0, 10) } });
})().catch(e => {
  console.log('\nharness error: ' + String(e && e.stack || e).slice(0, 600));
  planRemaining('the harness itself failed before the check could run: '
    + String(e && e.message || e).slice(0, 200));
  finish({ harness_error: String(e && e.message || e).slice(0, 300) });
});
