/* ============================================================================
   tools/frontend_shell.js — تحويل public/index.html إلى قشرة (F-09/F-11).

   يُشغَّل بعد tools/frontend_split.js. يخرج من الصفحة كل ما هو قابل للتنفيذ أو
   للتنسيق، فلا يبقى فيها إلا البنية:

     • <style> الواحدة            → public/app/styles/app.css
     • كل سمة style="…" في العلامة → صنف مولَّد في app.css (acs-u-NN)
     • كل <script> كلاسيكي داخلي  → public/app/boot/<name>.js
     • <script type="module">     → public/app/main.js (أنتجه المفكّك)
     • محمّل es-module-shims       → يُحذف (انظر CSP-HARDENING.md §5)

   خريطة الاستيراد تبقى داخلية — لا يمكن أن تكون خارجية في كل المتصفّحات — ويُحسَب
   لها sha256 يدخل script-src، فلا حاجة إلى 'unsafe-inline' من أجلها.

     node tools/frontend_shell.js
     node tools/frontend_shell.js --check    # لا يكتب، يتحقّق فقط
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..');
const PUB = path.join(ROOT, 'public');
const APP = path.join(PUB, 'app');

/* ترتيب السكربتات الكلاسيكية واسم كل واحد — معلن لا مشتقّ */
const BOOT = [
  { match: 'var CONFIGURED_BASE', file: 'boot/api-base.js',
    why: 'أصل واجهة الخادوم الوحيد' },
  { match: 'ACS_BUILD_INFO', file: 'boot/build-info.js',
    why: 'أصل البناء + مسار التنزيل الاحتياطي' },
  { match: 'acs_debug', file: 'boot/debug-toggle.js',
    why: 'مفتاح عرض عدّاد التشخيص' },
  { match: 'window.ACS = { ready:false', file: 'boot/engine-guard.js',
    why: 'تهيئة window.ACS وحارس تعذّر تحميل المحرّك' },
  { match: "var EN=['acsWorkspace'", file: 'boot/a11y-baseline.js',
    why: 'أساس الوصولية — كلاسيكي عمداً كي لا يعتمد على تحميل Three.js' },
];

const SHIM_MARK = 'es-module-shims';

function readPage() {
  return fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
}

/* عناصر <script> الحقيقية: الوسم يبدأ بـ <script ثمّ ينتهي بـ > قبل أي سطر
   جديد، والإغلاق أوّل </script> يليه محرف إنهاء صالح. السلاسل التي تحتوي
   "</script" داخل الشيفرة لا تُغلق العنصر (المحرف التالي " ليس منهياً). */
function scriptElements(html) {
  const out = [];
  const re = /<script(\s[^>]*)?>/g;
  let m;
  while ((m = re.exec(html))) {
    const attrs = (m[1] || '').trim();
    let i = m.index + m[0].length;
    let end = -1;
    const close = /<\/script([\s/>])/g;
    close.lastIndex = i;
    const c = close.exec(html);
    if (!c) continue;
    end = c.index;
    out.push({ tagStart: m.index, bodyStart: i, bodyEnd: end,
               tagEnd: html.indexOf('>', end) + 1, attrs,
               body: html.slice(i, end) });
    re.lastIndex = html.indexOf('>', end) + 1;
  }
  return out;
}

/* ------------------------------------------------------ سمات style="…" --- */
function cssIdent(v, n) { return 'acs-u-' + String(n).padStart(2, '0'); }

function extractInlineStyles(html, markupRanges) {
  const found = new Map();                 /* قيمة → اسم صنف */
  const edits = [];
  const re = /\sstyle="([^"]*)"/g;
  for (const [a, b] of markupRanges) {
    re.lastIndex = 0;
    const chunk = html.slice(a, b);
    let m;
    while ((m = re.exec(chunk))) {
      const val = m[1].trim();
      if (!val) continue;
      if (!found.has(val)) found.set(val, cssIdent(val, found.size + 1));
      edits.push({ start: a + m.index, end: a + m.index + m[0].length,
                   cls: found.get(val) });
    }
  }
  return { found, edits };
}

/* يدمج الصنف في سمة class القائمة على العنصر نفسه، أو ينشئها */
function applyStyleEdits(html, edits) {
  edits.sort((x, y) => y.start - x.start);
  let out = html;
  for (const e of edits) {
    /* حدود الوسم الذي تنتمي إليه السمة */
    const tagOpen = out.lastIndexOf('<', e.start);
    const tagClose = out.indexOf('>', e.end);
    const tag = out.slice(tagOpen, tagClose + 1);
    const removed = tag.slice(0, e.start - tagOpen) + tag.slice(e.end - tagOpen);
    let next;
    const cm = /\sclass="([^"]*)"/.exec(removed);
    if (cm) {
      next = removed.slice(0, cm.index)
           + ' class="' + (cm[1] + ' ' + e.cls).trim() + '"'
           + removed.slice(cm.index + cm[0].length);
    } else {
      const sp = removed.indexOf(' ') >= 0 ? removed.indexOf(' ')
                                           : removed.length - 1;
      next = removed.slice(0, sp) + ' class="' + e.cls + '"' + removed.slice(sp);
    }
    out = out.slice(0, tagOpen) + next + out.slice(tagClose + 1);
  }
  return out;
}

/* ------------------------------------------------------------- التنفيذ --- */
function main() {
  const check = process.argv.includes('--check');
  let html = readPage();
  const scripts = scriptElements(html);
  const moduleScript = scripts.find(s => /type\s*=\s*"module"/.test(s.attrs)
                                         && !/\bsrc\s*=/.test(s.attrs));
  const importmap = scripts.find(s => /type\s*=\s*"importmap"/.test(s.attrs));
  const classics = scripts.filter(s => !s.attrs || (!/type\s*=/.test(s.attrs)));
  if (!importmap) throw new Error('import map not found');

  const written = [];

  /* 1) CSS */
  const sOpen = html.indexOf('<style>');
  const sClose = html.indexOf('</style>');
  if (sOpen < 0) throw new Error('no <style> block');
  const css = html.slice(sOpen + '<style>'.length, sClose);

  /* 2) سمات style في العلامة (خارج script/style) */
  const markupRanges = [[0, sOpen], [sClose + '</style>'.length,
                                     moduleScript ? moduleScript.tagStart : html.length]];
  if (moduleScript) markupRanges.push([moduleScript.tagEnd, html.length]);
  const { found, edits } = extractInlineStyles(html, markupRanges);

  const utilCss = '\n\n/* ============================================================\n'
    + '   أصناف مولَّدة من سمات style="…" التي كانت في العلامة (F-11).\n'
    + '   وجودها هناك كان يفرض style-src \'unsafe-inline\'. تُولَّد آلياً من\n'
    + '   tools/frontend_shell.js فلا تتحرّر يدوياً.\n'
    + '   ============================================================ */\n'
    + [...found.entries()].map(([v, c]) => '.' + c + '{' +
        (v.endsWith(';') ? v : v + ';') + '}').join('\n') + '\n';

  /* 3) السكربتات الكلاسيكية */
  const bootFiles = [];
  for (const s of classics) {
    if (s.body.indexOf(SHIM_MARK) >= 0) continue;              /* يُحذف */
    const spec = BOOT.find(b => s.body.indexOf(b.match) >= 0);
    if (!spec) throw new Error('undeclared inline classic script at offset '
                               + s.tagStart + ': ' + s.body.slice(0, 80));
    bootFiles.push({ spec, s });
  }
  if (bootFiles.length !== BOOT.length)
    throw new Error('expected ' + BOOT.length + ' boot scripts, matched '
                    + bootFiles.length);

  /* 4) أعِد بناء الصفحة — من الآخر إلى الأوّل حتى تبقى الإحداثيات صالحة */
  const replacements = [];
  for (const { spec, s } of bootFiles)
    replacements.push({ start: s.tagStart, end: s.tagEnd,
                        text: '<script src="/app/' + spec.file + '"></script>' });
  for (const s of classics)
    if (s.body.indexOf(SHIM_MARK) >= 0)
      replacements.push({ start: s.tagStart, end: s.tagEnd, text:
        '<!-- es-module-shims removed: خرائط الاستيراد أصلية في كل متصفّح مدعوم،\n'
      + '     والـshim كان السبب الوحيد لـ script-src \'unsafe-eval\' و blob:.\n'
      + '     الأثر على التوافق موثّق بالأرقام في CSP-HARDENING.md §5. -->' });
  if (moduleScript)
    replacements.push({ start: moduleScript.tagStart, end: moduleScript.tagEnd,
                        text: '<script type="module" src="/app/main.js"></script>' });
  replacements.push({ start: sOpen, end: sClose + '</style>'.length,
                      text: '<link rel="stylesheet" href="/app/styles/app.css" />' });

  let out = applyStyleEdits(html, edits);
  /* أعِد حساب الإحداثيات: تعديلات الأصناف تسبق، فنعيد البحث بالنصّ */
  const reapply = [];
  for (const r of replacements) {
    const original = html.slice(r.start, r.end);
    const at = out.indexOf(original);
    if (at < 0) throw new Error('could not relocate block after class edits: '
                                + original.slice(0, 60));
    reapply.push({ start: at, end: at + original.length, text: r.text });
  }
  reapply.sort((a, b) => b.start - a.start);
  for (const r of reapply) out = out.slice(0, r.start) + r.text + out.slice(r.end);

  /* 5) بصمة خريطة الاستيراد للـCSP */
  const mapBody = importmap.body;
  const hash = 'sha256-' + crypto.createHash('sha256')
    .update(mapBody, 'utf8').digest('base64');

  if (check) {
    console.log('would write %d boot scripts, %d utility classes', bootFiles.length,
                found.size);
    console.log('importmap hash: %s', hash);
    return;
  }

  fs.mkdirSync(path.join(APP, 'styles'), { recursive: true });
  fs.mkdirSync(path.join(APP, 'boot'), { recursive: true });
  fs.writeFileSync(path.join(APP, 'styles', 'app.css'),
    '/* ============================================================\n'
  + '   public/app/styles/app.css — مُستخرَج من public/index.html.\n'
  + '   وجود التنسيق داخل الصفحة كان يفرض style-src \'unsafe-inline\'.\n'
  + '   ============================================================ */\n'
  + css.replace(/^\n/, '') + utilCss);
  written.push('styles/app.css');

  for (const { spec, s } of bootFiles) {
    const dst = path.join(APP, spec.file);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.writeFileSync(dst,
      '/* ============================================================\n'
    + '   public/app/' + spec.file + ' — ' + spec.why + '\n'
    + '   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).\n'
    + '   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.\n'
    + '   ============================================================ */\n'
    + s.body.replace(/^\n/, '') + '\n');
    written.push(spec.file);
  }

  fs.writeFileSync(path.join(PUB, 'index.html'), out);
  fs.writeFileSync(path.join(APP, 'importmap.sha256'), hash + '\n');
  console.log('shell written: %d bytes (was %d)',
              Buffer.byteLength(out, 'utf8'), Buffer.byteLength(html, 'utf8'));
  console.log('boot scripts: %s', written.join(', '));
  console.log('utility classes generated: %d', found.size);
  console.log('importmap hash: %s', hash);
}

module.exports = { scriptElements, BOOT };
if (require.main === module) main();
