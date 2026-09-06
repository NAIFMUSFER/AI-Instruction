/* ============================================================================
   tests/remediation/test_bundle_extractor.js

   الثابت: **مستخرِج حزمة المتصفّح يعمل بلا تبعيات مركَّبة، وبلا مسارٍ داخليّ.**

   العطل الذي أوجب هذا الملفّ
   --------------------------
       Error: Cannot find module
         '…/node_modules/playwright/lib/transform/babelBundle.js'
       Require stack:
       - …/tests/phase3/lib/extract_browser_bundle.js

   Playwright تبعيةُ تطوير، ولا تُركَّب إلّا في وظيفةٍ واحدة من تسع في CI:
   `3 · Real Chromium` هي الوحيدة التي تنفّذ `npm ci`. وكانت وظائف ٢ و٥
   (وكلّ ما يمرّ من tests/lib/run.js فيهما) تستهلك حزمة المتصفّح، فتسقط قبل
   أوّل توكيد. ومع ذلك كان المسار داخلياً أصلاً: `lib/transform/babelBundle.js`
   ليس من واجهة Playwright المعلنة، فله أن يزول في أيّ إصدار بلا إخطار.

   البديل: tests/lib/js_segment.js — تقطيعٌ بـ`node:vm` وحدها، وقد ثبت تكافؤه
   مع Babel على كل وحدة تحت public/app/ (حدودُ التعليمات وأسماءُ التصريحات
   متطابقة)، والحزمة الناتجة **مطابقة بايتاً ببايت** لِما كان Babel ينتجه.

   ما يُثبَّت هنا:
     أ  لا ملفّ يشارك في وظيفةٍ لا تُركِّب التبعيات يطلب شيئاً من node_modules
     ب  المستخرِج يُنتج حزمةً صالحة في هذه البيئة، وتُحلَّل بـ new vm.Script
     ج  المُقطِّع صحيحٌ على الحالات التي كسرته أثناء التطوير — بشواهد سالبة
     د  المديات مرتّبة ولا تتداخل، وما بينها فراغٌ أو تعليقٌ لا شيفرة
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('node:vm');
const { execFileSync } = require('child_process');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const SEG = require(path.join(ROOT, 'tests', 'lib', 'js_segment.js'));

let pass = 0, fail = 0;
const chk = (n, c, d) => {
  c ? (pass++, console.log('  ✓', n))
    : (fail++, console.log('  ✗', n, d === undefined ? '' : '\n      ' + d));
};

/* ── أ · لا تبعيةً مركَّبة في مسار الاستخراج ───────────────────────────── */
console.log('\n== أ · مسار استخراج الحزمة لا يطلب شيئاً من node_modules ==');

/* هذه الملفّات تعمل في وظائف CI التي لا تنفّذ `npm ci`. أيّ require منها إلى
   node_modules عطلٌ بنيويّ لا مجرّد هشاشة. */
const MUST_BE_DEPENDENCY_FREE = [
  'tests/lib/js_segment.js',
  'tests/lib/app_source.js',
  'tests/lib/run.js',
  'tests/phase3/lib/extract_browser_bundle.js',
  'tests/phase3/lib/run.js'
];
const NM = /require\s*\([^)]*node_modules/;
for (const rel of MUST_BE_DEPENDENCY_FREE) {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) { chk(rel + ' exists', false, 'missing'); continue; }
  const src = fs.readFileSync(p, 'utf8');
  /* التعليقات تشرح العطل القديم وتذكر المسار بالاسم — يُفحَص المنفَّذ وحده. */
  const code = src.replace(/\/\*[\s\S]*?\*\//g, ' ')
                  .replace(/(^|[^:])\/\/[^\n]*/g, '$1');
  chk(rel + ' requires nothing from node_modules', !NM.test(code),
      (NM.exec(code) || [''])[0]);
}

/* الملفّات التي يُسمح لها بذلك، ولماذا. قائمة مُعلَنة: إضافة اسمٍ إليها قرارٌ
   مرئيّ في المراجعة، لا انزلاقٌ صامت. */
const ALLOWED_TO_USE_DEV_DEPS = {
  'tests/remediation/test_module_graph.js':
    'يعمل في الوظيفة 3 وحدها، وهي الوحيدة التي تنفّذ npm ci',
  'tools/frontend_split.js': 'أداة تشغَّل يدوياً على آلة تطوير',
  'tools/frontend_analyze.js': 'أداة تشغَّل يدوياً على آلة تطوير'
};
for (const rel of Object.keys(ALLOWED_TO_USE_DEV_DEPS)) {
  chk(rel + ' is declared as a dev-dependency consumer ('
      + ALLOWED_TO_USE_DEV_DEPS[rel] + ')',
      fs.existsSync(path.join(ROOT, rel)));
}
chk('the dependency-free list and the dev-dependency list do not overlap',
    !MUST_BE_DEPENDENCY_FREE.some(f => ALLOWED_TO_USE_DEV_DEPS[f]));

/* ── ب · المستخرِج يُنتج حزمةً صالحة هنا والآن ─────────────────────────── */
console.log('\n== ب · المستخرِج يعمل في هذه البيئة ويُنتج نصّاً صالحاً ==');
const OUT = path.join(require('os').tmpdir(),
                      'acs_bundle_extractor_probe_' + process.pid + '.js');
let ran = true, runErr = '';
try {
  execFileSync(process.execPath,
               [path.join(ROOT, 'tests', 'phase3', 'lib',
                          'extract_browser_bundle.js')],
               { env: Object.assign({}, process.env,
                                    { ACS_BUNDLE: OUT, ACS_BUNDLE_FORCE: '1' }),
                 stdio: ['ignore', 'pipe', 'pipe'] });
} catch (e) {
  ran = false;
  runErr = String((e.stderr && e.stderr.toString()) || e.message).slice(0, 400);
}
chk('extract_browser_bundle.js runs to completion', ran, runErr);
if (ran) {
  const code = fs.readFileSync(OUT, 'utf8');
  chk('it wrote a non-trivial bundle', code.length > 100000,
      String(code.length));
  chk('the bundle carries the content stamp on its first line',
      /^\/\* acs-browser-bundle sha256:[0-9a-f]{64} \*\//.test(code));
  let ok = true, err = '';
  try { new vm.Script(code, { filename: 'acs_bundle.js' }); }
  catch (e) { ok = false; err = e.message; }
  chk('the emitted bundle parses (new vm.Script — Node public API)', ok, err);
  chk('the pure prefix boundary was found and is a real cut, not the whole file',
      /pure prefix: \d+ top-level statements; stops at the first one that needs/
        .test(code));
  try { fs.unlinkSync(OUT); } catch (e) { /* لا شيء */ }
}

/* ── ج · المُقطِّع: الحالات التي كسرته فعلاً ────────────────────────────── */
console.log('\n== ج · المُقطِّع صحيحٌ على الحالات التي كسرته أثناء التطوير ==');
const cases = [
  { why: 'تعليمتان على سطرٍ واحد تُقطَعان تعليمتين',
    src: 'const A={}; A.x=1;\nconst B=2;\n', n: 3,
    texts: ['const A={};', 'A.x=1;', 'const B=2;'] },
  { why: 'تصريحٌ متعدّد فيه `{}` لا يُقطَع عند القوس',
    src: 'let a=null,b={},c=[],d=1;\n', n: 1,
    names: ['a', 'b', 'c', 'd'] },
  { why: 'كائنٌ متعدّد الأسطر ينتهي بـ`};` لا بـ`}`',
    src: 'const o = {\n  a: 1\n};\nconst p = 2;\n', n: 2,
    texts: ['const o = {\n  a: 1\n};', 'const p = 2;'] },
  { why: 'تعليقٌ صدريّ لا يدخل في مدى التعليمة',
    src: '/* note */\nconst z = 1;\n', n: 1, texts: ['const z = 1;'] },
  { why: 'دالّة متعدّدة الأسطر تعليمةٌ واحدة',
    src: 'function f(a){\n  if(a){ return 1; }\n  return 2;\n}\nconst q=f(1);\n',
    n: 2, names: ['f', 'q'] },
  { why: '`;` داخل نصّ ليست حدّ تعليمة',
    src: 'const s = "a;b";\nconst t = 1;\n', n: 2,
    texts: ['const s = "a;b";', 'const t = 1;'] },
  { why: '`;` في رأس for ليست حدّ تعليمة',
    src: 'for (let i=0;i<2;i++){ void i; }\nconst u=1;\n', n: 2 },
  { why: 'صنفٌ يليه تصريح',
    src: 'class K { m(){ return 1; } }\nconst k = new K();\n', n: 2,
    names: ['K', 'k'] }
];
for (const c of cases) {
  const st = SEG.topLevelStatements(c.src);
  chk(c.why + ' — ' + st.length + ' تعليمة', st.length === c.n,
      JSON.stringify(st.map(s => c.src.slice(s.start, s.end))));
  if (c.texts) {
    const got = st.map(s => c.src.slice(s.start, s.end));
    chk('  ونصوصها بالضبط', JSON.stringify(got) === JSON.stringify(c.texts),
        JSON.stringify(got));
  }
  if (c.names) {
    const got = SEG.declaredNames(c.src, st);
    chk('  وأسماؤها بالضبط: ' + c.names.join(', '),
        JSON.stringify(got) === JSON.stringify(c.names), JSON.stringify(got));
  }
}

console.log('\n-- شاهد سالب: المُقطِّع لا يقبل ما لا يُحلَّل --');
chk('an unterminated construct is NOT reported as a complete statement',
    !SEG.parses('function f(){'));
chk('a complete construct IS', SEG.parses('function f(){}'));

/* ── د · المديات مرتّبة ولا تتداخل، وما بينها ليس شيفرة ────────────────── */
console.log('\n== د · المديات على كل وحدة مشحونة: مرتّبة، غير متداخلة، '
            + 'ولا شيفرة بينها ==');
const APP = require(path.join(ROOT, 'tests', 'lib', 'app_source.js'));
const mods = APP.modules();
let checked = 0, ordered = true, disjoint = true, gapClean = true;
let firstBad = '';
for (const f of Object.keys(mods).sort()) {
  const src = APP.stripModuleSyntax(mods[f], f);
  const st = SEG.topLevelStatements(src);
  checked++;
  for (let i = 0; i < st.length; i++) {
    if (st[i].end < st[i].start) { disjoint = false; firstBad = f; }
    if (i && st[i].start < st[i - 1].end) { ordered = false; firstBad = f; }
    const gapFrom = i ? st[i - 1].end : 0;
    const gap = src.slice(gapFrom, st[i].start);
    /* ما بين تعليمتين لا يجوز أن يكون إلّا فراغاً أو تعليقاً */
    const rest = gap.replace(/\/\*[\s\S]*?\*\//g, ' ')
                    .replace(/(^|[^:])\/\/[^\n]*/g, '$1');
    if (/\S/.test(rest)) { gapClean = false; firstBad = f + ' :: ' + JSON.stringify(gap.slice(0, 60)); }
  }
}
chk('every shipped module was segmented (' + checked + ')', checked >= 20,
    String(checked));
chk('statement ranges are ordered', ordered, firstBad);
chk('statement ranges do not overlap', disjoint, firstBad);
chk('nothing but whitespace or comments lies between statements', gapClean,
    firstBad);

console.log('\n' + '─'.repeat(62));
console.log('BUNDLE EXTRACTOR: %d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
