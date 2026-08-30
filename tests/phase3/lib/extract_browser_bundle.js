/* ============================================================================
   tests/phase3/lib/extract_browser_bundle.js

   يبني حزمة شيفرة المتصفّح القابلة للتشغيل في نطاق Node واحد.

   قبل F-09 كان هذا الملفّ يقتطع مدياتٍ من أسطر public/index.html بمراسٍ نمطيّة
   (grab(L(/^const LAYER_NAMES=\{/), …)). بعد تفكيك الصفحة إلى وحدات ES تحت
   public/app/ لم تعد تلك الأسطر موجودة، والأسوأ أن الاقتطاع بالسطر كان يخمّن
   حدود الطبقات بدل أن يقرأها. الآن المصدر الوحيد هو tests/lib/app_source.js،
   والاختيار يجري على ثلاثة مستويات مصرَّح بها ومُتحقَّق منها:

     FULL    وحدات نقيّة بكاملها (لا DOM ولا Three ولا window) — تُدرَج كما هي.
     PREFIX  وحدة تبدأ بطبقات نقيّة وتنتهي بمحرّك المتصفّح: تُدرَج البادئة
             القصوى من تعليماتها العليا التي تُقيَّم في Node بلا بيئة متصفّح.
             الحدّ يُقاس بالتنفيذ لا بالاستنتاج: أكبر بادئةٍ تعمل في `node:vm`
             بلا ReferenceError. أوّل تعليمة تحتاج معرّفاً غير موجود في Node
             ولا مصرَّحاً به قبلها هي الحدّ، والاسم يأتي من الخطأ نفسه.
     PICK    تصريحات عليا مسمّاة تُنتزع من وحدة متصفّح بالاسم عبر الشجرة
             النحويّة (لا بمدى أسطر). كل اسم مطلوب يجب أن يوجد وإلا فشل البناء.

   المخرج والعقد كما كانا: يُكتب إلى process.env.ACS_BUNDLE (أو /tmp)، ويطبع
   سطر تأكيد بالصيغة نفسها، فيبقى كل مستدعٍ (tests/lib/run.js،
   tests/phase3/lib/run.js، tests/phase3/lib/build_browser_page.js) عاملاً.
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const vm = require('node:vm');
const APP = require(path.join(ROOT, 'tests', 'lib', 'app_source.js'));
/* تقطيعُ التعليمات وأسماءُ التصريحات بأدوات Node وحدها — لا محلّل خارجيّ.
   كان هنا `require(node_modules/playwright/lib/transform/babelBundle.js)`:
   مسارٌ داخليّ غير موثَّق في تبعية تطوير لا تُركَّب إلّا في وظيفةٍ واحدة من
   تسع في CI، فكانت كل وظيفة أخرى تسقط قبل أوّل توكيد بـ«Cannot find module».
   التفصيل والتكافؤ المُثبَّت في tests/lib/js_segment.js. */
const SEG = require(path.join(ROOT, 'tests', 'lib', 'js_segment.js'));

const OUT = process.env.ACS_BUNDLE
         || path.join(os.tmpdir(), 'acs_browser_bundle.js');

/* الوحدات النقيّة بكاملها، بترتيب التحميل الحقيقي المعلن في public/app/main.js.
   كلٌّ منها كانت مقطعاً في الصفحة الواحدة، وكلٌّ منها تُقيَّم في Node وحدها. */
const FULL = [
  'core/viewer.js',
  'core/standards.js',
  'core/disciplines.js',
  'generated/runtime.js',
  'generated/authoring.js',
  'generated/workspace-ui.js',
  'generated/render-engine.js',
  'generated/bim.js',
  'generated/docs.js',
  'generated/pbr.js',
  'generated/arch-detail.js'
];

/* وحدة مختلطة: تبدأ بطبقة العرض البصري وطبقة التنسيق وكاشف نوع المبنى (نقيّ
   كلّه)، ثم تنتقل عند «المشهد والعرض» إلى renderer/scene/camera. */
const PREFIX = ['render/scene.js'];

/* من طبقة الربط كان المستخرج القديم يأخذ showReport و esc وحدهما — وهما ما
   تفحصه اختبارات المرحلتين ١ و٢.
   KI-25/F-44 أضاف حاجز التطبيق بعد 200: منطقه نقيّ ويقرأ setModel و
   window.ACS.verifyVisibleModel و acsBuildDefects بأسماءَ يمكن إبدالها في
   نطاق الاختبار، فيُقاس تصنيفه بلا متصفّح. البكسلات لا تُدّعى هنا: لها
   اختبار Chromium وحده. */
const PICK = { 'ui/workspace-ui-wiring.js': [
  'showReport', 'esc',
  'ACS_FAIL', 'ACS_APPLY_CONTRACT', 'ACS_APPLY_MIN_KEPT',
  'ACS_APPLY_SEQ', 'ACS_LAST_APPLY',
  'acsApplyTicket', 'acsApplyBuilding', 'acsApplyFirstFrame',
  '_acsZonesAsked', '_acsErrorSite', '_acsStackHead', '_acsFin', 'acsFail'] };

/* لم تعد هناك قائمة معرّفاتٍ مكتوبة: الحدّ يقيسه التنفيذ في `node:vm`،
   ومعرّفات Node المتاحة هي ما يتيحه المُفسِّر نفسه لحظة القياس. */

/* تحقّق نحويّ بواجهة Node العامّة. يرمي كما كان يرمي المحلّل السابق. */
function parse(src, label) {
  try {
    new vm.Script(src, { filename: String(label) });
  } catch (e) {
    throw new Error('syntax error in ' + label + ': ' + e.message);
  }
  return true;
}

/* التحليل النحويّ لِـ ١٫٤ م.ب في كل تشغيل اختبار مكلف بلا فائدة، لكن التخزين
   المؤقّت لا يجوز أن يعتمد على زمن التعديل: ملفّ /tmp واحد قد تكتبه شجرة أخرى
   من المستودع فتقرأ الشجرة الحالية حزمة ليست لها. الوسم بصمة محتوى: مصدر
   المستخرج + وحدة القراءة + كل ملفّ تحت public/app. لا يُعاد الاستعمال إلّا
   عند تطابقها حرفاً بحرف. */
function stamp() {
  const h = require('crypto').createHash('sha256');
  h.update(fs.readFileSync(__filename));
  h.update(fs.readFileSync(path.join(ROOT, 'tests', 'lib', 'app_source.js')));
  h.update(fs.readFileSync(path.join(ROOT, 'tests', 'lib', 'js_segment.js')));
  const mods = APP.modules();
  for (const f of Object.keys(mods).sort()) { h.update(f); h.update(mods[f]); }
  return '/* acs-browser-bundle sha256:' + h.digest('hex') + ' */';
}
const STAMP = stamp();
if (!process.env.ACS_BUNDLE_FORCE) {
  let head = null;
  try {
    const fd = fs.openSync(OUT, 'r');
    const buf = Buffer.alloc(STAMP.length);
    fs.readSync(fd, buf, 0, STAMP.length, 0);
    fs.closeSync(fd);
    head = buf.toString('utf8');
  } catch (e) { head = null; }
  if (head === STAMP) {
    console.log('browser bundle extracted ->', OUT);
    process.exit(0);
  }
}

/* التصريحات العليا لنصّ — من حدود التعليمات، لا ببحثٍ حرّ في الملفّ */
function topLevelNames(src) {
  return SEG.declaredNames(src);
}

/* أكبر عددٍ من التعليمات العليا يعمل فعلاً في Node.

   هذا قياسٌ لا استنتاج: تُنفَّذ البادئة في `node:vm` فوق ما سبقها من الحزمة،
   ويُنظَر هل ترمي ReferenceError. الخاصية رتيبة — ما إن تحتاج تعليمةٌ معرّفاً
   غائباً حتى تحتاجه كل بادئةٍ أطول — فيكفي بحثٌ ثنائيّ.

   وهو أدقّ ممّا كان: المعيار السابق «معرّف حرّ خارج أي دالّة» تقديرٌ ساكن،
   وهذا هو السلوك نفسه الذي تعتمد عليه المجموعات حين تحمّل الحزمة. */
function runsInNode(prelude, code) {
  const ctx = vm.createContext(Object.create(null));
  try {
    vm.runInContext(prelude + '\n' + code, ctx,
                    { filename: 'acs_prefix_probe.js', timeout: 120000 });
    return { ok: true, missing: null };
  } catch (e) {
    /* الخطأ يأتي من عالَم `vm` الآخر، فـ`instanceof` من عالَمنا يكذب دائماً.
       الاسم هو المعيار الصحيح عبر العوالم. */
    if (e && (e.name === 'ReferenceError'
              || /is not defined/.test(String(e && e.message)))) {
      const m = /^(\w[\w$]*) is not defined/.exec(String(e.message));
      return { ok: false, missing: m ? m[1] : String(e.message) };
    }
    /* خطأ آخر (TypeError مثلاً) ليس حدّ متصفّح: البادئة مقبولة نحوياً
       ودلالياً هنا، والمشكلة في التنفيذ لا في الغياب. */
    return { ok: true, missing: null };
  }
}

function pureStatementCount(prelude, src, stmts) {
  let lo = 0, hi = stmts.length, why = null;
  const at = k => k === 0 ? '' : src.slice(0, stmts[k - 1].end);
  if (runsInNode(prelude, at(hi)).ok) return { cut: hi, why: null };
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    const r = runsInNode(prelude, at(mid));
    if (r.ok) lo = mid;
    else { hi = mid - 1; why = r.missing; }
  }
  /* اسم الحدّ من التعليمة التي سقطت، لا من آخر محاولة */
  const r = runsInNode(prelude, at(lo + 1));
  if (!r.ok) why = r.missing;
  return { cut: lo, why: why };
}

/* أسماء تنشرها وحدةٌ في سجلّ الربط المتأخّر: تُقرأ من الشجرة لا بتعبير نمطي،
   ويُشترط الشكل القانوني الوحيد الذي يكتبه tools/frontend_split.js —
   Object.assign(__ACS_LATE, { a, b, c }); بمفاتيح مختصرة فقط. */
function latePublications(src, stmts) {
  const out = [];
  for (const st of stmts) {
    const text = src.slice(st.start, st.end);
    const m = /^Object\s*\.\s*assign\s*\(\s*__ACS_LATE\s*,\s*\{([^}]*)\}\s*\)\s*;?$/
      .exec(SEG.head(text).trim());
    if (!m) continue;
    for (const raw of m[1].split(',')) {
      const k = raw.trim();
      if (!k) continue;
      if (!/^[A-Za-z_$][\w$]*$/.test(k))
        throw new Error('unexpected shape in an __ACS_LATE publication: ' + k);
      out.push(k);
    }
  }
  return out;
}

const parts = [];
const declared = new Set();
const stats = [];

const mods = APP.modules();
const loadOrder = APP.order();

/* سجلّا الأوراق يتصدّران الحزمة كما يتصدّران public/app/main.js: __ACS_SHARED
   (الأسماء التي تُكتب عبر حدود الوحدات) و __ACS_LATE (الإحالات الأمامية).
   يُقرآن من ملفّيهما ولا يُصطنعان كائنين فارغين: مجموعة المفاتيح وختم
   Object.seal يبقيان كما في المتصفّح، فنشرُ اسم غير مسجَّل يظهر بدل أن يمرّ. */
parts.push(APP.registryPrelude(mods));
for (const f of APP.REGISTRIES) {
  if (loadOrder.indexOf(f) !== APP.REGISTRIES.indexOf(f))
    throw new Error('leaf registry is not imported first by public/app/main.js: '
                    + f);
  topLevelNames(APP.stripModuleSyntax(mods[f], f)).forEach(n => declared.add(n));
}
if (!declared.has('__ACS_SHARED') || !declared.has('__ACS_LATE'))
  throw new Error('the leaf registries did not declare __ACS_SHARED/__ACS_LATE');
stats.push(APP.REGISTRIES.join(' + ') + ' — leaf registries');

/* تحقّق: كل وحدة مُدرَجة موجودة، وترتيب الإدراج هو ترتيب التحميل الحقيقي */
{
  const listed = FULL.concat(PREFIX);
  const at = listed.map(f => {
    if (!mods[f]) throw new Error('module not found: public/app/' + f);
    const i = loadOrder.indexOf(f);
    if (i < 0) throw new Error('module is not imported by public/app/main.js: ' + f);
    return i;
  });
  for (let i = 1; i < at.length; i++)
    if (at[i] <= at[i - 1])
      throw new Error('bundle order does not follow public/app/main.js: ' + listed[i]);
}

for (const f of FULL) {
  const src = APP.stripModuleSyntax(mods[f], f);
  topLevelNames(src).forEach(n => declared.add(n));
  parts.push('/* ==== public/app/' + f + ' (whole module) ==== */\n' + src);
  stats.push(f + ' — whole module');
}

for (const f of PREFIX) {
  const src = APP.stripModuleSyntax(mods[f], f);
  parse(src, f);
  const body = SEG.topLevelStatements(src);
  /* البادئة تُقاس فوق ما تراكم من الحزمة، فتُحلّ أسماءُ الوحدات السابقة كما
     تُحلّ في التحميل الحقيقي، ولا يُحسَب غيابها حدَّ متصفّح. */
  const prelude = parts.join('\n\n');
  const measured = pureStatementCount(prelude, src, body);
  const cut = measured.cut;
  const why = measured.why;
  if (cut === body.length)
    throw new Error('no browser boundary found in ' + f
                    + ' — it is fully pure, list it in FULL instead');
  const head = src.slice(0, body[cut].start);
  topLevelNames(head).forEach(n => declared.add(n));
  parts.push('/* ==== public/app/' + f + ' (pure prefix: ' + cut
             + ' top-level statements; stops at the first one that needs `'
             + why + '`) ==== */\n' + head);
  stats.push(f + ' — pure prefix [0,' + cut + ') of ' + body.length
             + ' top-level statements, boundary: ' + why);
  /* سطر النشر `Object.assign(__ACS_LATE, {…})` يكتبه المفكّك في آخر الوحدة،
     أي بعد الحدّ دائماً. إسقاطه يترك السجلّ فارغاً من أسماء أُدرِجت تصريحاتها
     فعلاً، فينهار كل مستدعٍ أسبق بـ «ليست دالّة». يُعاد بثّه هنا مقصوراً على
     ما صرّحت به البادئة المُدرَجة — لا اسم يُنشَر بلا شيفرته. */
  const allPub = latePublications(src, body);
  const pub = allPub.filter(n => declared.has(n));
  const skipped = allPub.filter(n => !declared.has(n));
  if (pub.length)
    parts.push('/* ==== public/app/' + f + ' (late-binding publications whose '
               + 'declarations are included) ==== */\n'
               + 'Object.assign(__ACS_LATE, { ' + pub.join(', ') + ' });');
  stats.push(f + ' — publishes ' + (pub.join(', ') || '(none)')
             + (skipped.length ? '; beyond the boundary: ' + skipped.join(', ')
                               : ''));
}

for (const f of Object.keys(PICK)) {
  const want = PICK[f];
  const src = APP.stripModuleSyntax(mods[f], f);
  parse(src, f);
  const taken = [];
  const found = new Set();
  for (const st of SEG.topLevelStatements(src)) {
    const text = src.slice(st.start, st.end);
    const names = SEG.statementDeclaredNames(text);
    /* تصريحٌ واحد باسمٍ واحد فقط يُنتزَع: `let a=1,b=2;` لا يُقتطع نصفه. */
    if (names.length !== 1) continue;
    const n = names[0];
    if (want.indexOf(n) >= 0 && !found.has(n)) {
      found.add(n); taken.push(text); declared.add(n);
    }
  }
  const missing = want.filter(n => !found.has(n));
  if (missing.length)
    throw new Error('declaration not found in public/app/' + f + ': '
                    + missing.join(', '));
  parts.push('/* ==== public/app/' + f + ' (declarations: ' + want.join(', ')
             + ') ==== */\n' + taken.join('\n'));
  stats.push(f + ' — declarations ' + want.join(', '));
}

const code = STAMP + '\n' + parts.join('\n\n');
/* المخرج نفسه يجب أن يكون نصّاً صالحاً — يُتحقَّق منه قبل الكتابة */
parse(code, 'acs_browser_bundle');
fs.writeFileSync(OUT, code);
console.log('browser bundle extracted ->', OUT);
if (process.env.ACS_BUNDLE_VERBOSE) console.log('  ' + stats.join('\n  '));
