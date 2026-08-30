/* ============================================================================
   tests/lib/js_segment.js — تقطيعُ شيفرةٍ إلى تعليماتها العليا بأدوات Node وحدها.

   لماذا يوجد هذا الملفّ
   ---------------------
   كان tests/phase3/lib/extract_browser_bundle.js يستورد محلّل Babel من مسارٍ
   داخليّ غير موثَّق داخل Playwright:

       require(path.join(ROOT, 'node_modules', 'playwright', 'lib',
                         'transform', 'babelBundle.js'))

   وهذا معطوبٌ من وجهين، ظهر أوّلهما في CI بوضوح:

     ١) Playwright تبعيةُ تطوير، ولا تُركَّب إلّا في وظيفةٍ واحدة من تسع —
        `3 · Real Chromium` هي الوحيدة التي تنفّذ `npm ci`. فكل وظيفة أخرى
        تستهلك حزمة المتصفّح كانت تسقط قبل أوّل توكيد:

            Error: Cannot find module
              '…/node_modules/playwright/lib/transform/babelBundle.js'
            Require stack:
            - …/tests/phase3/lib/extract_browser_bundle.js

        أصابت هذه الوظائفَ ٢ (parity) و٥ (accessibility) وكل ما يمرّ من
        tests/lib/run.js فيها.

     ٢) المسار داخليّ: ليس من واجهة Playwright المعلنة، فله أن يزول أو ينتقل
        في أي إصدار بلا نقضٍ معلَن للتوافق. تثبيتُ الإصدار لا يحمي من ذلك،
        لأن العقد الذي نعتمد عليه غير موجودٍ أصلاً.

   الآلية البديلة: `node:vm` — واجهة Node عامّة وموثّقة، حاضرة بلا تركيب.

   الفكرة في سطر: **أقصرُ بادئةٍ تُحلَّل نحوياً هي تعليمة واحدة.**
   نبدأ من حدّ التعليمة السابقة ونمدّ سطراً سطراً حتى يقبل `new vm.Script`
   النصَّ المتراكم؛ عندها تكون تعليمةً كاملة، فنسجّل حدّها ونستأنف. هذا هو
   المنطق نفسه الذي يميّز به REPL «سطراً تامّاً» من «سطرٍ ناقص»، ولا يحتاج
   شجرةً نحويّة ولا حزمةً خارجية.

   ولأن الحدود تُعرَف بالضبط، صار استخراجُ اسمِ التصريح تعبيراً نمطياً
   مربوطاً برأس التعليمة وحده — لا بحثاً حرّاً في الملفّ. الالتباس الذي يجعل
   التعابير النمطية خطراً (أن تصطاد `function` داخل نصّ أو تعليق أو جسم دالّة)
   ساقطٌ هنا: لا يُنظَر إلّا إلى أوّل رمز في مدّى تعليمةٍ عليا معروفة الحدّين.

   تكافؤ هذا الملفّ مع ما كان Babel يُنتجه مُثبَّت على كل وحدة تحت public/app/
   في tests/remediation/test_bundle_extractor.js، وعلى بصمة الحزمة كاملةً.
   ============================================================================ */
'use strict';
const vm = require('node:vm');

/* هل النصّ برنامجٌ تامّ نحوياً؟ التحقّق بواجهة Node العامّة، بلا تنفيذ. */
function parses(src) {
  try {
    new vm.Script(src, { filename: 'acs_segment_probe.js' });
    return true;
  } catch (e) {
    return false;
  }
}

/* حدود التعليمات العليا: [{start, end}] بمواضع بايتية في `src`.

   `end` هو آخر محرف غير فراغيّ في التعليمة (كما يفعل Babel تماماً)، و`start`
   أوّل محرف غير فراغيّ فيها — فتُطابق المديات ما كانت `node.start/node.end`
   تعطيه، ويبقى `src.slice(0, stmt.start)` صالحاً كبادئة. */
function skipTrivia(src, i) {
  const n = src.length;
  for (;;) {
    while (i < n && /\s/.test(src[i])) i++;
    if (src[i] === '/' && src[i + 1] === '*') {
      const j = src.indexOf('*/', i + 2);
      i = j < 0 ? n : j + 2;
      continue;
    }
    if (src[i] === '/' && src[i + 1] === '/') {
      const j = src.indexOf('\n', i);
      i = j < 0 ? n : j + 1;
      continue;
    }
    return i;
  }
}

function topLevelStatements(src) {
  const out = [];
  const n = src.length;
  let from = 0;

  while (from < n) {
    /* بداية التعليمة هي أوّل محتوى حقيقيّ: لا فراغ ولا تعليق — مطابقةً
       لِما كان Babel يعطيه في node.start. */
    from = skipTrivia(src, from);
    if (from >= n) break;

    let cursor = from;
    let closed = -1;
    while (cursor < n) {
      let nl = src.indexOf('\n', cursor);
      if (nl < 0) nl = n; else nl += 1;
      const chunk = src.slice(from, nl);
      cursor = nl;
      /* بادئة فارغة المحتوى (تعليق وحده مثلاً) تُحلَّل لكنها ليست تعليمة */
      if (!chunk.replace(/\s+/g, '')) continue;
      if (parses(chunk) && hasStatement(chunk)) { closed = nl; break; }
    }
    if (closed < 0) closed = n;

    /* السطر قد يحمل أكثر من تعليمة: `const a={}; a.forEach(…);`
       فالنموّ سطراً سطراً يعطي أقصر سطرٍ تامّ لا أقصر تعليمة. نضيّق من اليمين
       داخل السطر الأخير: أوّل موضعٍ ينتهي عنده نصٌّ تامّ هو نهاية التعليمة.
       المرشّحون مواضع ما بعد `;` أو `}` وحدهم، وكلٌّ منهم يُتحقَّق منه بـ
       new vm.Script — فـ`;` داخل نصّ أو داخل رأس `for` لا يُحلَّل فيسقط. */
    if (closed > from) {
      let lineStart = src.lastIndexOf('\n', closed - 2) + 1;
      if (lineStart < from) lineStart = from;
      for (let k = lineStart + 1; k < closed; k++) {
        /* الفاصلة المنقوطة وحدها مرشَّحة. القوس `}` ليس مرشَّحاً: قد يغلق
           كائناً في وسط تصريحٍ متعدّد — `let a={},b={},c=1;` — فتُقطَع
           التعليمة عند `a={}` وهي تُحلَّل وحدها فيمرّ القطع الخاطئ صامتاً.
           و`;` لا يقع هذا الالتباس فيها: أيّ `;` وسط تعبيرٍ يجعل البادئة
           غير قابلة للتحليل فتُرفض. */
        if (src[k - 1] !== ';') continue;
        const cand = src.slice(from, k);
        if (parses(cand) && hasStatement(cand)) { closed = k; break; }
      }
    }

    let end = closed;
    while (end > from && /\s/.test(src[end - 1])) end--;
    out.push({ start: from, end: end });
    from = closed;
  }
  return out;
}

/* بادئةٌ قد تُحلَّل وهي كلّها تعليقات — تلك ليست تعليمةً. نتحقّق بأن حذف
   التعليقات يترك محتوى. الحذف هنا غرضه هذا السؤال وحده. */
function hasStatement(chunk) {
  const stripped = chunk
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1');
  return /\S/.test(stripped);
}

/* رأسُ التعليمة: أوّل رمزٍ فعليّ بعد أي تعليقات صدرية. */
function head(stmtText) {
  let s = stmtText;
  for (;;) {
    const t = s.replace(/^\s+/, '');
    if (t.startsWith('/*')) {
      const i = t.indexOf('*/');
      if (i < 0) return '';
      s = t.slice(i + 2);
      continue;
    }
    if (t.startsWith('//')) {
      const i = t.indexOf('\n');
      if (i < 0) return '';
      s = t.slice(i + 1);
      continue;
    }
    return t;
  }
}

const DECL = /^(?:export\s+)?(?:async\s+)?(function\s*\*?|class|const|let|var)\s+([A-Za-z_$][\w$]*)/;

/* الأسماء التي تصرّح بها تعليمةٌ عليا واحدة.

   الأشكال المعالَجة هي التي يكتبها tools/frontend_split.js وحدها:
     function NAME(…){}      ·  async function NAME(…){}  ·  function* NAME
     class NAME {…}
     const/let/var NAME = …  ·  وقوائم بفواصل  ·  وتفكيك {a, b} و[a, b]
   وأي شكلٍ آخر يُعاد فارغاً، فلا يُخترع اسم. */
function statementDeclaredNames(text) {
  const h = head(text);
  const m = DECL.exec(h);
  if (!m) return [];
  const kw = m[1].replace(/\s*\*$/, '').trim();
  if (kw === 'function' || kw === 'class') return [m[2]];

  /* const/let/var: قد تكون قائمةً أو تفكيكاً. نقرأ حتى نهاية التعليمة على
     العمق صفر بالنسبة لبداية التصريح. */
  const body = h.slice(h.indexOf(m[1]) + m[1].length);
  const names = [];
  let depth = 0;
  let expect = true;
  let i = 0;
  let inStr = null;
  while (i < body.length) {
    const c = body[i];
    if (inStr) {
      if (c === '\\') { i += 2; continue; }
      if (c === inStr) inStr = null;
      i++;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { inStr = c; i++; continue; }
    if (c === '/' && body[i + 1] === '/') { const j = body.indexOf('\n', i); i = j < 0 ? body.length : j; continue; }
    if (c === '/' && body[i + 1] === '*') { const j = body.indexOf('*/', i); i = j < 0 ? body.length : j + 2; continue; }
    if (c === '(' || c === '[' || c === '{') { depth++; i++; if (depth === 1) expect = true; continue; }
    if (c === ')' || c === ']' || c === '}') { depth--; i++; if (depth === 0) expect = false; continue; }
    if (c === ',' && depth <= 1) { expect = true; i++; continue; }
    if (c === '=' && body[i + 1] !== '=' && depth === 0) {
      /* تخطَّ القيمة إلى الفاصلة التالية على العمق صفر */
      expect = false; i++;
      let d = 0;
      while (i < body.length) {
        const d2 = body[i];
        if (d2 === '"' || d2 === "'" || d2 === '`') {
          const q = d2; i++;
          while (i < body.length && body[i] !== q) { if (body[i] === '\\') i++; i++; }
          i++; continue;
        }
        if (d2 === '(' || d2 === '[' || d2 === '{') d++;
        else if (d2 === ')' || d2 === ']' || d2 === '}') d--;
        else if (d2 === ',' && d === 0) { expect = true; break; }
        i++;
      }
      i++;
      continue;
    }
    if (c === ':' && depth === 1) { names.pop(); expect = true; i++; continue; }
    if (expect && /[A-Za-z_$]/.test(c)) {
      let j = i;
      while (j < body.length && /[\w$]/.test(body[j])) j++;
      names.push(body.slice(i, j));
      expect = false;
      i = j;
      continue;
    }
    i++;
  }
  return names.filter(Boolean);
}

/* كل الأسماء المصرَّح بها على المستوى الأعلى لنصٍّ كامل. */
function declaredNames(src, stmts) {
  const list = stmts || topLevelStatements(src);
  const out = [];
  for (const s of list)
    for (const n of statementDeclaredNames(src.slice(s.start, s.end)))
      out.push(n);
  return out;
}

module.exports = { parses, skipTrivia, topLevelStatements, statementDeclaredNames,
                   declaredNames, head };
