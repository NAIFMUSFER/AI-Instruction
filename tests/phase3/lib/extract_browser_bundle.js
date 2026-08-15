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
             الحدّ يُحسَب بمحلّل نحويّ حقيقي (Babel المضمّن في playwright)، لا
             بمرساة نصّية: أوّل تعليمة عليا تحتاج معرّفاً حرّاً غير معرَّف في
             Node ولا مصرَّحاً به قبلها هي الحدّ.
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
const APP = require(path.join(ROOT, 'tests', 'lib', 'app_source.js'));
const B = require(path.join(ROOT, 'node_modules', 'playwright', 'lib',
                            'transform', 'babelBundle.js'));

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

/* المعرّفات المتاحة في Node نفسه: تُقرأ من البيئة لا من قائمة مكتوبة بيد،
   فلا تتقادم. ما ليس فيها ولا مصرَّحاً به قبله يحتاج بيئة متصفّح. */
const NODE_GLOBALS = new Set(
  Object.getOwnPropertyNames(globalThis)
    .concat(['undefined', 'arguments', 'globalThis', 'require', 'module',
             'exports', '__dirname', '__filename']));

function parse(src, label) {
  return B.babelParse(src, String(label).replace(/[^A-Za-z0-9_.-]/g, '_'), false);
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

/* التصريحات العليا لنصّ — من الشجرة، لا بتعبير نمطي */
function topLevelNames(ast) {
  const out = [];
  B.traverse(ast, {
    Program(p) { out.push.apply(out, Object.keys(p.scope.bindings)); p.stop(); }
  });
  return out;
}

/* المعرّفات الحرّة المستعملة وقت التقييم (خارج أي دالّة) مع مواضعها */
function evalTimeFreeRefs(ast) {
  const hits = [];
  B.traverse(ast, {
    ReferencedIdentifier(p) {
      const n = p.node.name;
      if (p.scope.hasBinding(n, true)) return;      /* محلول داخل الوحدة */
      if (p.getFunctionParent()) return;            /* داخل دالّة: لا يُقيَّم الآن */
      hits.push({ name: n, at: p.node.start });
    }
  });
  return hits;
}

/* أسماء تنشرها وحدةٌ في سجلّ الربط المتأخّر: تُقرأ من الشجرة لا بتعبير نمطي،
   ويُشترط الشكل القانوني الوحيد الذي يكتبه tools/frontend_split.js —
   Object.assign(__ACS_LATE, { a, b, c }); بمفاتيح مختصرة فقط. */
function latePublications(ast) {
  const out = [];
  for (const st of ast.program.body) {
    if (st.type !== 'ExpressionStatement') continue;
    const e = st.expression;
    if (!e || e.type !== 'CallExpression') continue;
    const c = e.callee;
    if (!c || c.type !== 'MemberExpression' || c.object.name !== 'Object'
        || c.property.name !== 'assign') continue;
    if (e.arguments.length !== 2 || e.arguments[0].name !== '__ACS_LATE'
        || e.arguments[1].type !== 'ObjectExpression') continue;
    for (const p of e.arguments[1].properties) {
      if (p.type !== 'ObjectProperty' || !p.shorthand
          || p.key.type !== 'Identifier')
        throw new Error('unexpected shape in an __ACS_LATE publication');
      out.push(p.key.name);
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
  topLevelNames(parse(APP.stripModuleSyntax(mods[f], f), f))
    .forEach(n => declared.add(n));
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
  topLevelNames(parse(src, f)).forEach(n => declared.add(n));
  parts.push('/* ==== public/app/' + f + ' (whole module) ==== */\n' + src);
  stats.push(f + ' — whole module');
}

for (const f of PREFIX) {
  const src = APP.stripModuleSyntax(mods[f], f);
  const ast = parse(src, f);
  const body = ast.program.body;
  const refs = evalTimeFreeRefs(ast);
  let cut = body.length, why = null;
  for (let i = 0; i < body.length && cut === body.length; i++) {
    const st = body[i];
    for (const r of refs) {
      if (r.at < st.start || r.at >= st.end) continue;
      if (declared.has(r.name) || NODE_GLOBALS.has(r.name)) continue;
      cut = i; why = r.name; break;
    }
  }
  if (cut === body.length)
    throw new Error('no browser boundary found in ' + f
                    + ' — it is fully pure, list it in FULL instead');
  const head = src.slice(0, body[cut].start);
  topLevelNames(parse(head, f)).forEach(n => declared.add(n));
  parts.push('/* ==== public/app/' + f + ' (pure prefix: ' + cut
             + ' top-level statements; stops at the first one that needs `'
             + why + '`) ==== */\n' + head);
  stats.push(f + ' — pure prefix [0,' + cut + ') of ' + body.length
             + ' top-level statements, boundary: ' + why);
  /* سطر النشر `Object.assign(__ACS_LATE, {…})` يكتبه المفكّك في آخر الوحدة،
     أي بعد الحدّ دائماً. إسقاطه يترك السجلّ فارغاً من أسماء أُدرِجت تصريحاتها
     فعلاً، فينهار كل مستدعٍ أسبق بـ «ليست دالّة». يُعاد بثّه هنا مقصوراً على
     ما صرّحت به البادئة المُدرَجة — لا اسم يُنشَر بلا شيفرته. */
  const pub = latePublications(ast).filter(n => declared.has(n));
  const skipped = latePublications(ast).filter(n => !declared.has(n));
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
  const ast = parse(src, f);
  const taken = [];
  const found = new Set();
  for (const st of ast.program.body) {
    let n = null;
    if (st.type === 'FunctionDeclaration' || st.type === 'ClassDeclaration')
      n = st.id && st.id.name;
    else if (st.type === 'VariableDeclaration' && st.declarations.length === 1
             && st.declarations[0].id.type === 'Identifier')
      n = st.declarations[0].id.name;
    if (n && want.indexOf(n) >= 0 && !found.has(n)) {
      found.add(n); taken.push(src.slice(st.start, st.end)); declared.add(n);
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
