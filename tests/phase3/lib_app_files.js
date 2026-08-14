/* ============================================================================
   tests/phase3/lib_app_files.js — قراءة شيفرة التطبيق المفكّكة من داخل اختبار.

   بعد F-09 صارت public/index.html قشرة، وشيفرة التطبيق وحدات ES تحت public/app/.
   الاختبارات التي كانت تقرأ الصفحة نصّاً تحتاج الآن مصدرين مختلفين:

       shell()     العلامة (DOM، معرّفات العناصر، سمات الوصول)
       appText()   الشيفرة (الرموز، الكتل المولَّدة، علاماتها)

   نظير tests/lib/app_source.js، لكنه لا يستعمل إلّا fs.readFileSync و path،
   فيعمل حرفياً كما هو داخل صفحة اختبار المتصفّح التي يبنيها
   tests/phase3/lib/build_browser_page.js — حيث fs خريطة ملفّات لا قرص.

   ترتيب التحميل يُقرأ من public/app/main.js نفسه، فلا تُكرَّر معرفة التخطيط.
   ============================================================================ */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const APPDIR = path.join(ROOT, 'public', 'app');

function mainJs() { return fs.readFileSync(path.join(APPDIR, 'main.js'), 'utf8'); }

/* ترتيب التحميل الحقيقي: قائمة الاستيراد في main.js بالترتيب المكتوب */
function order() {
  return mainJs().split('\n')
    .map(l => (/^import '\.\/(.+?)';$/.exec(l) || [])[1])
    .filter(Boolean);
}

function mod(rel) { return fs.readFileSync(path.join(APPDIR, rel), 'utf8'); }

function has(rel) { return fs.existsSync(path.join(APPDIR, rel)); }

/* كل شيفرة التطبيق موصولة بترتيب التحميل — بديل ما كان البحث في نصّ الصفحة */
function appText() {
  return order().map(f => '/* ==== public/app/' + f + ' ==== */\n' + mod(f))
                .join('\n');
}

function shell() {
  return fs.readFileSync(path.join(ROOT, 'public', 'index.html'), 'utf8');
}

function css() {
  return fs.readFileSync(path.join(APPDIR, 'styles', 'app.css'), 'utf8');
}

/* الوحدة الوحيدة التي تحتوي علامةً ما — يفشل إن لم تكن واحدة بالضبط */
function moduleCarrying(marker) {
  const hits = order().filter(f => mod(f).indexOf(marker) >= 0);
  if (hits.length !== 1)
    throw new Error('expected exactly one application module to carry '
                    + JSON.stringify(marker) + ', found ' + hits.length
                    + (hits.length ? ': ' + hits.join(', ') : ''));
  return hits[0];
}

/* عدد مرّات ظهور علامة في كل شيفرة التطبيق */
function countInApp(marker) {
  return order().reduce((n, f) => n + mod(f).split(marker).length - 1, 0);
}

/* المقطع بين علامتي بداية ونهاية داخل وحدة واحدة، شاملاً العلامتين */
function block(rel, open, close) {
  const t = mod(rel);
  const a = t.indexOf(open);
  if (a < 0) throw new Error('marker not found in public/app/' + rel + ': ' + open);
  const b = t.indexOf(close, a);
  if (b < 0) throw new Error('end marker not found in public/app/' + rel + ': ' + close);
  return t.slice(a, b + close.length);
}

module.exports = { ROOT, APPDIR, mainJs, order, mod, has, appText, shell, css,
                   moduleCarrying, countInApp, block };
