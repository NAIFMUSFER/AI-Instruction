/* ============================================================================
   tests/lib/app_source.js — مصدر واحد لقراءة شيفرة الواجهة بعد التفكيك (F-09).

   قبل F-09 كانت كل أداة واختبار يقرآن public/index.html نصّاً ويبحثان فيه. بعد
   التفكيك صار التطبيق ملفّات تحت public/app/، والصفحة قشرة. هذه الوحدة هي
   الطبقة الوحيدة التي تعرف ذلك، فلا تتكرّر معرفة التخطيط في خمسين موضعاً.

     shell()        نصّ public/index.html (القشرة: بنية + خريطة استيراد فقط)
     modules()      خريطة: مسار نسبي تحت public/app → نصّ الملفّ
     appText()      كل شيفرة التطبيق موصولة (للبحث النصّي الذي كان يجري على الصفحة)
     pageText()     القشرة + شيفرة التطبيق — بديل مطابق دلالياً لِما كان `page`
     nodeBundle()   الطبقات النقيّة بلا import/export لتشغيلها في نطاق Node واحد

   الفصل مقصود: البحث عن علامة في العلامة (DOM) يستعمل shell()، والبحث عن رمز
   في الشيفرة يستعمل appText(). خلطهما هو ما جعل الملفّ الواحد يبدو مقبولاً.
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const PUB = path.join(ROOT, 'public');
const APP = path.join(PUB, 'app');

/* ترتيب التحميل الحقيقي — نفس ترتيب الاستيراد في public/app/main.js، وهو نفس
   ترتيب المقاطع في الصفحة قبل التفكيك. أي بحث نصّي يعتمد على الترتيب يبقى صحيحاً. */
function order() {
  const main = fs.readFileSync(path.join(APP, 'main.js'), 'utf8');
  const out = [];
  const re = /^import\s+'\.\/(.+?)';$/gm;
  let m;
  while ((m = re.exec(main))) out.push(m[1]);
  return out;
}

/* الطبقات النقيّة: لا DOM ولا Three ولا window — تعمل في Node كما كانت تعمل
   حين استخرجها tests/phase3/lib/extract_browser_bundle.js من الصفحة. */
const PURE = ['core/viewer.js', 'core/standards.js', 'core/disciplines.js'];

function shell() {
  return fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
}

function walk(dir, acc, base) {
  for (const f of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walk(p, acc, base);
    else if (p.endsWith('.js')) acc[path.relative(base, p).replace(/\\/g, '/')] =
      fs.readFileSync(p, 'utf8');
  }
  return acc;
}

function modules() {
  return walk(APP, {}, APP);
}

function appText() {
  const mods = modules();
  const seq = order().filter(f => mods[f]);
  const rest = Object.keys(mods).filter(f => seq.indexOf(f) < 0).sort();
  return seq.concat(rest).map(f => '/* ==== public/app/' + f + ' ==== */\n'
                                   + mods[f]).join('\n');
}

function pageText() {
  return shell() + '\n' + appText();
}

/* يزيل جُمل import/export من نصّ وحدة فيعود المقطع إلى نطاق واحد كما كان.
   الإزالة سطريّة على الشكل القانونيّ الذي يكتبه tools/frontend_split.js وحده،
   ويُتحقَّق منها: أي جملة import/export متبقّية تُرفَع خطأً بدل أن تمرّ صامتة. */
function stripModuleSyntax(src, label) {
  const out = src
    .replace(/^import\s*\{[^}]*\}\s*from\s*'[^']*';\s*$/gm, '')
    .replace(/^import\s+\*\s+as\s+\w+\s+from\s*'[^']*';\s*$/gm, '')
    .replace(/^import\s*\{[^}]*\}\s*from\s*"[^"]*";\s*$/gm, '')
    .replace(/^import\s+'[^']*';\s*$/gm, '')
    .replace(/^export\s*\{[^}]*\};\s*$/gm, '');
  const left = /^(import|export)\s/m.exec(out);
  if (left) throw new Error('unstripped module syntax in ' + label + ': '
                            + out.slice(left.index, left.index + 90));
  return out;
}

function nodeBundle(files) {
  const list = files || PURE;
  const mods = modules();
  /* __ACS_SHARED وحده يُمهَّد: هو الكائن الذي نقل إليه المفكّك الأسماء القليلة
     التي تُكتب عبر الوحدات. كل ما عداه يأتي من الملفّات نفسها. */
  const parts = ['const __ACS_SHARED = {};'];
  for (const f of list) {
    if (!mods[f]) throw new Error('module not found for node bundle: ' + f);
    parts.push('/* ==== ' + f + ' ==== */\n' + stripModuleSyntax(mods[f], f));
  }
  return parts.join('\n\n');
}

module.exports = { ROOT, PUB, APP, PURE, order, shell, modules, appText,
                   pageText, nodeBundle, stripModuleSyntax };
