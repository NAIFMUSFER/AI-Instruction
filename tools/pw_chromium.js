/* ============================================================================
   محدِّد ثنائيّة Chromium لـPlaywright — موضعٌ واحد، وبلا نجاح مزيَّف.

   لماذا يوجد
   ----------
   لكل نسخة Playwright بناءٌ من Chromium تتوقّعه بالرقم (1.62.1 ⇒ 1234). حيث
   تعمل الشبكة — وظيفة CI الثالثة — يُنزَّل ذلك البناء بالضبط:
       npx playwright install --with-deps chromium
       → /home/runner/.cache/ms-playwright/chromium-1234/…
   وحيث لا شبكة — هذا الصندوق — تحمل الصورة بناءً آخر (1194) تحت
   /opt/pw-browsers. فالسؤال «أيّ ثنائيّة؟» له جوابان مختلفان بيئةً ببيئة،
   وهذا الملفّ هو الموضع الوحيد الذي يُجاب فيه.

   ترتيب القرار — والترتيب هو العقد
   --------------------------------
     1) تجاوزٌ صريح من المشغّل (ACS_CHROMIUM …) — نيّةٌ معلنة تسبق كل استنتاج.
     2) **ثنائيّة Playwright المُدارة**: chromium.executablePath(). هذا هو
        الجواب الصحيح كلّما كان `playwright install` قد جرى فعلاً — أي في
        GitHub Actions دائماً. لا يجوز لأي مسار صندوقٍ أن يسبقه.
     3) مسحُ جذور المتصفّحات، وجذر الصورة /opt/pw-browsers **آخرها**: لا
        يُبلَغ إلا حين تعجز Playwright عن حلّ بنائها، أي في صندوقٍ بلا شبكة.

   وما ليس فيه: احتياطٌ يُخفي الغياب. إن لم توجد ثنائيّة، يرمي launch()
   ويسمّي ما فُتِّش عنه. الغياب البيئيّ يُعلَن، ولا يُقرأ نجاحاً أبداً.

     const PW = require('tools/pw_chromium.js');
     const exe = PW.executable();          // مسار موجود، أو null
     const browser = await PW.launch();    // يرمي إن لم يوجد متصفّح
   ========================================================================== */
const fs = require('fs'), path = require('path');

const CANDIDATE_ENV = ['ACS_CHROMIUM', 'CHROMIUM_PATH', 'PLAYWRIGHT_CHROMIUM_EXECUTABLE'];

/* جذر الصورة في هذا الصندوق. يُذكر مرّةً واحدة، وبوصفه **مجلّد بحث** لا
   مسار ثنائيّة: لا ملفّ اختبارٍ واحد يخبز مساراً تحته (يثبّت ذلك
   tests/remediation/test_browser_acquisition.py). */
const SANDBOX_BROWSERS_ROOT = '/opt/pw-browsers';

function fromPlaywright() {
  try {
    const { chromium } = require('playwright');
    const p = chromium.executablePath();
    if (p && fs.existsSync(p)) return p;
  } catch (e) { /* يُبلَّغ عنه في المستدعي عبر searched */ }
  return null;
}

/* البناء الكامل قبل قشرة headless: القشرة لا تصلح لقياسٍ يحتاج WebGL كامل،
   فلا يجوز أن تسبق الكامل لمجرّد ترتيب readdir. */
function rank(p) {
  return /headless[-_]shell/.test(p) ? 1 : 0;
}

function browsersRoots(env) {
  const e = env || process.env;
  const roots = [];
  for (const r of [e.PLAYWRIGHT_BROWSERS_PATH,
    path.join(e.HOME || '/root', '.cache', 'ms-playwright'),
    SANDBOX_BROWSERS_ROOT]) {
    if (r && roots.indexOf(r) < 0) roots.push(r);   /* بلا تكرار */
  }
  return roots;
}

function scanBrowsersRoot(roots) {
  const found = [];
  for (const root of (roots || browsersRoots())) {
    if (!fs.existsSync(root)) continue;
    /* الرابط الرمزي المباشر أوّلاً — أوضح نيّة من مسح الأرقام */
    for (const direct of ['chromium', 'chrome']) {
      const d = path.join(root, direct);
      try { if (fs.existsSync(d) && fs.statSync(d).isFile()) found.push(d); }
      catch (e) { /* تجاهل */ }
    }
    let entries = [];
    try { entries = fs.readdirSync(root); } catch (e) { entries = []; }
    for (const e of entries) {
      for (const rel of [
        path.join(e, 'chrome-linux', 'chrome'),
        path.join(e, 'chrome-linux64', 'chrome'),
        path.join(e, 'chrome-headless-shell-linux64', 'chrome-headless-shell')]) {
        const p = path.join(root, rel);
        if (fs.existsSync(p) && found.indexOf(p) < 0) found.push(p);
      }
    }
  }
  /* ترتيبٌ مستقرّ: الكامل قبل القشرة، وبقيّة الترتيب كما وُجد. */
  return found.map((p, i) => [p, i])
    .sort((a, b) => (rank(a[0]) - rank(b[0])) || (a[1] - b[1]))
    .map(e => e[0]);
}

/* القرار كاملاً، بمصدره وبما فُتِّش عنه — ليقول سجلُّ CI *لماذا* لا متصفّح.

   `acq` وسيطُ حَقنٍ اختياريّ ({env, roots, playwright:false}) على نفس نمط
   acs_rate_limit.production_invariant(env=…): يسمح لعقد الاكتساب أن يقيس فرع
   **الرفض** حيّاً في بيئةٍ يوجد فيها متصفّح، بدل الاكتفاء بقراءة نصّ الملفّ —
   وبلا ذلك لا يمكن قياس هذا الفرع على أيّ آلة تشغّل CI أصلاً، لأن المتصفّح
   موجود فيها بالتعريف. وهو يضيّق البحث ولا يوسّعه أبداً: كل مفتاح فيه يحذف
   مصدراً، ولا مفتاح فيه يضيف مساراً. */
function resolve(acq) {
  const o = acq || {};
  const env = o.env || process.env;
  const searched = [];
  for (const k of CANDIDATE_ENV) {
    const v = env[k];
    if (!v) continue;
    searched.push(k + '=' + v);
    if (fs.existsSync(v)) return { path: v, source: k, searched: searched };
  }

  if (o.playwright === false) {
    searched.push('playwright-managed: (excluded by caller)');
  } else {
    let pwWanted = null;
    try { pwWanted = require('playwright').chromium.executablePath(); }
    catch (e) { pwWanted = null; }
    searched.push('playwright-managed: '
      + (pwWanted || '(playwright could not be loaded)'));
    const pw = fromPlaywright();
    if (pw) return { path: pw, source: 'playwright-managed', searched: searched };
  }

  const roots = o.roots || browsersRoots(env);
  searched.push('browser roots: ' + (roots.join(', ') || '(none)'));
  const scanned = scanBrowsersRoot(roots);
  if (scanned.length) {
    return { path: scanned[0], source: 'scanned', searched: searched };
  }
  return { path: null, source: null, searched: searched };
}

function executable(acq) {
  return resolve(acq).path;
}

async function launch(opts, acq) {
  const { chromium } = require('playwright');
  const r = resolve(acq);
  if (!r.path) {
    throw new Error('no Chromium binary is available in this sandbox — '
      + 'searched: ' + r.searched.join(' | '));
  }
  return chromium.launch(Object.assign({ executablePath: r.path }, opts || {}));
}

module.exports = { executable, launch, resolve, scanBrowsersRoot, browsersRoots,
  SANDBOX_BROWSERS_ROOT: SANDBOX_BROWSERS_ROOT };
