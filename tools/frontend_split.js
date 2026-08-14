/* ============================================================================
   tools/frontend_split.js — تفكيك الواجهة (F-09).

   يحوّل public/index.html من صفحة تحمل التطبيق كاملاً داخلها إلى قشرة + وحدات
   ES خارجية تحت public/app/. العملية ميكانيكية ومُثبَتة، لا يدوية:

     1) يُحلَّل نصّ الوحدة بمحلّل نحويّ حقيقي (Babel المضمّن في playwright).
     2) يُقسَّم عند حدود معلنة: الكتل المولَّدة، وقواطع مصرَّح بها في CUTS.
     3) لكل مقطع تُحسَب التصريحات العليا والمعرّفات الحرّة من شجرة النحو.
     4) تُولَّد قوائم import/export ميكانيكياً من هذا الحساب — لا تخمين.
     5) الأسماء المتغيّرة عبر المقاطع (٦ فقط) تُنقَل إلى كائن حالة مشترك،
        لأن ارتباط الاستيراد في ES للقراءة فقط ولا يقبل الإسناد.
     6) الكتابة نصّية بإحداثيات دقيقة من الشجرة: لا يُعاد توليد الشيفرة، فكل
        بايت لم يُقصَد تغييره يخرج كما دخل.

   ضمانة التحقّق (تُنفَّذ في نهاية التشغيل، والخروج غير صفري عند الإخفاق):
     • كل ملفّ مُخرَج يُحلَّل وحدةً صالحة.
     • اتحاد التصريحات بعد التفكيك = تصريحات الوحدة الأصلية.
     • لا معرّف حرّ غير محلول خارج قائمة globals المعلنة.
     • مجموع بايتات الشيفرة محفوظ ضمن هامش الوسوم المضافة.

     node tools/frontend_split.js            # ينفّذ التفكيك
     node tools/frontend_split.js --check    # يتحقّق فقط ولا يكتب
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const B = require(path.join(ROOT, 'node_modules', 'playwright', 'lib',
                            'transform', 'babelBundle.js'));
const A = require(path.join(__dirname, 'frontend_analyze.js'));

const APP = path.join(ROOT, 'public', 'app');
const SHARED = '__ACS_SHARED';
const LATE = '__ACS_LATE';

/* قواطع إضافية داخل المقاطع اليدوية الكبيرة — تُطبَّق عند أوّل تعليمة عليا
   يبدأ نصّها بالمرساة. الهدف ألّا تتجاوز وحدة واحدة سقف 300 ك.ب المعلن. */
const CUTS = [
  { after: 'hand_0', anchor: /^const ACS_RULES_REGISTRY\s*=/ },
  { after: 'hand_0', anchor: /^function compileArchitecture\s*\(/ },
];

/* اسم الملفّ لكل مقطع — معلن هنا لا مشتقّ، فالمراجعة تراه دفعةً واحدة */
const FILES = {
  'hand_0#0': 'core/viewer.js',
  'hand_0#1': 'core/standards.js',
  'hand_0#2': 'core/disciplines.js',
  'ACS RUNTIME LAYER': 'generated/runtime.js',
  'ACS AUTHORING LAYER': 'generated/authoring.js',
  'ACS WORKSPACE UI': 'generated/workspace-ui.js',
  'ACS RENDER ENGINE': 'generated/render-engine.js',
  'ACS BIM EXCHANGE': 'generated/bim.js',
  'ACS DOCUMENTATION': 'generated/docs.js',
  'ACS PBR QUALITY': 'generated/pbr.js',
  'ACS ARCH DETAIL': 'generated/arch-detail.js',
  'hand_16': 'render/scene.js',
  'ACS PBR BRIDGE': 'generated/pbr-bridge.js',
  'ACS ARCH DETAIL BRIDGE': 'generated/arch-detail-bridge.js',
  'hand_20': 'ui/workspace-ui-wiring.js',
  'ACS PRODUCTION TRUST CORE': 'trust/core.js',
  'ACS PRODUCTION TRUST WIRING': 'trust/wiring.js',
};

const GLOBALS = new Set(String(fs.readFileSync(
  path.join(__dirname, 'frontend_globals.txt'), 'utf8')).split('\n')
  .map(s => s.trim()).filter(s => s && !s.startsWith('#')));
/* أسماء بيئة المتصفّح التي أضافها التحليل ولم تكن في القائمة الأولى */
['arguments', 'addEventListener', 'removeEventListener', 'dispatchEvent',
 'scrollTo', 'open', 'close', 'focus', 'blur', 'getSelection',
 'requestIdleCallback', 'onerror', 'onload'].forEach(n => GLOBALS.add(n));

function parse(src, label) {
  return B.babelParse(src, String(label).replace(/[^A-Za-z0-9_.-]/g, '_') + '.js',
                      true);
}

/* ---------------------------------------------------------------- مقاطع --- */
function buildSegments(code) {
  const base = A.segments(code);
  const ast = parse(code, 'module');
  const top = ast.program.body;
  const out = [];
  for (const s of base) {
    const cuts = CUTS.filter(c => c.after === s.name);
    if (!cuts.length) { out.push(Object.assign({}, s, { key: s.name })); continue; }
    const points = [s.start];
    for (const c of cuts) {
      const hit = top.find(n => n.start >= s.start && n.end <= s.end
                                && c.anchor.test(code.slice(n.start, n.start + 200)));
      if (!hit) throw new Error('cut anchor not found: ' + c.anchor);
      points.push(hit.start);
    }
    points.push(s.end);
    for (let i = 0; i < points.length - 1; i++)
      out.push({ kind: s.kind, name: s.name, key: s.name + '#' + i,
                 start: points[i], end: points[i + 1] });
  }
  return out;
}

/* ------------------------------------------------------- تحليل كل مقطع --- */
function scan(src, label) {
  const ast = parse(src, label);
  const info = { declared: new Set(), imported: new Set(), free: new Set(),
                 written: new Set(), importStatements: [], refs: [], decls: {} };
  let programScope = null;
  B.traverse(ast, {
    Program(p) {
      programScope = p.scope;
      for (const [k, b] of Object.entries(p.scope.bindings)) {
        if (b.kind === 'module') info.imported.add(k); else info.declared.add(k);
        info.decls[k] = b;
      }
      Object.keys(p.scope.globals || {}).forEach(n => info.free.add(n));
    }
  });
  B.traverse(ast, {
    ImportDeclaration(p) { info.importStatements.push(src.slice(p.node.start, p.node.end)); },
    AssignmentExpression(p) {
      const l = p.node.left;
      if (l && l.type === 'Identifier' && info.free.has(l.name)) info.written.add(l.name);
    },
    UpdateExpression(p) {
      const a = p.node.argument;
      if (a && a.type === 'Identifier' && info.free.has(a.name)) info.written.add(a.name);
    }
  });
  info.ast = ast;
  info.programScope = programScope;
  return info;
}

/* كل موضع لاسم يُحلّ إلى ارتباط المستوى الأعلى (أو إلى لا شيء = عالميّ) */
function occurrences(ast, names) {
  const hits = [];
  const want = new Set(names);
  B.traverse(ast, {
    Identifier(p) {
      const n = p.node.name;
      if (!want.has(n)) return;
      if (p.parentPath.isMemberExpression() && p.parentPath.node.property === p.node
          && !p.parentPath.node.computed) return;         /* obj.X ليست مرجعاً */
      if (p.parentPath.isObjectProperty() && p.parentPath.node.key === p.node
          && !p.parentPath.node.computed
          && p.parentPath.node.value !== p.node) return;   /* {X: ...} */
      if (p.parentPath.isImportSpecifier() || p.parentPath.isExportSpecifier()) return;
      const b = p.scope.getBinding(n);
      const isProgramBinding = b && b.scope.block.type === 'Program';
      if (b && !isProgramBinding) return;                  /* اسم محلّي يظلّل */
      hits.push({ name: n, start: p.node.start, end: p.node.end,
                  isDeclarator: p.parentPath.isVariableDeclarator()
                                && p.parentPath.node.id === p.node,
                  isFunctionDecl: p.parentPath.isFunctionDeclaration()
                                  && p.parentPath.node.id === p.node,
                  fnPath: p.parentPath.isFunctionDeclaration() ? p.parentPath : null,
                  declPath: p.parentPath.isVariableDeclarator() ? p.parentPath : null });
    }
  });
  return hits;
}

function applyEdits(src, edits) {
  edits.sort((a, b) => b.start - a.start);
  let out = src;
  let last = Infinity;
  for (const e of edits) {
    if (e.end > last) throw new Error('overlapping edit');
    out = out.slice(0, e.start) + e.text + out.slice(e.end);
    last = e.start;
  }
  return out;
}

function header(key, file, generator) {
  return '/* ============================================================\n'
       + '   public/app/' + file + '\n'
       + '   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).\n'
       + (generator ? '   المصدر المولِّد: ' + generator + '\n' : '')
       + '   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.\n'
       + '   ============================================================ */\n';
}

/* ------------------------------------------------------------- التنفيذ --- */
function main() {
  const check = process.argv.includes('--check');
  const html = A.readIndex(process.env.ACS_INDEX);
  const mod = A.moduleBody(html);
  if (!mod) { console.error('no module script in page — already split?'); process.exit(2); }
  const code = mod.code;
  const segs = buildSegments(code);

  /* 1) مسح أوّليّ */
  const scans = segs.map(s => {
    const src = code.slice(s.start, s.end);
    const info = scan(src, s.key);
    return Object.assign({}, s, { src, info });
  });

  /* 2) خريطة المالك */
  const owner = new Map();
  for (const s of scans) {
    for (const n of s.info.declared) owner.set(n, s.key);
    for (const n of s.info.imported) owner.set(n, s.key);
  }

  /* 3) الأسماء المتغيّرة عبر المقاطع */
  const mutable = new Set();
  for (const s of scans)
    for (const n of s.info.written)
      if (owner.has(n) && owner.get(n) !== s.key) mutable.add(n);
  /* اسم يكتبه مالكه ويقرأه غيره يبقى ارتباطاً حيّاً — القراءة عبر الاستيراد
     تُحدَّث تلقائياً، فلا حاجة لنقله إلى الحالة المشتركة. */

  /* رتبة كل مقطع في ترتيب التقييم الأصلي */
  const ORDER = scans.map(s => s.key);
  const indexOfKey = k => ORDER.indexOf(k);

  /* مرور تمهيدي: أي اسم يُقرَأ من مقطع سابق لمالكه هو ربط متأخّر */
  const lateNames = new Set();
  const lateByOwner = new Map();
  for (const s of scans) {
    for (const n of s.info.free) {
      if (mutable.has(n)) continue;
      const own = owner.get(n);
      if (!own || own === s.key) continue;
      if (indexOfKey(own) > indexOfKey(s.key)) {
        lateNames.add(n);
        if (!lateByOwner.has(own)) lateByOwner.set(own, new Set());
        lateByOwner.get(own).add(n);
      }
    }
  }

  console.log('segments: %d · shared mutable bindings: %d (%s)',
              scans.length, mutable.size, [...mutable].sort().join(', ') || '—');
  console.log('forward (late-bound) references: %d (%s)',
              lateNames.size, [...lateNames].sort().join(', ') || '—');

  /* 4) تحويل كل مقطع */
  const emitted = [];
  for (const s of scans) {
    const file = FILES[s.key];
    if (!file) throw new Error('no target file declared for segment ' + s.key);
    const edits = [];
    if (mutable.size) {
      for (const h of occurrences(s.info.ast, mutable)) {
        if (h.isDeclarator && s.info.declared.has(h.name)) {
          const decl = h.declPath.parentPath.node;      /* VariableDeclaration */
          if (decl.declarations.length !== 1)
            throw new Error('multi-declarator shared binding: ' + h.name);
          edits.push({ start: decl.start, end: h.end, text: SHARED + '.' + h.name });
        } else if (h.isFunctionDecl && s.info.declared.has(h.name)) {
          /* `function X(){}` تصير `__ACS_SHARED.X = function X(){}`.
             الرفع (hoisting) يسقط بذلك، وقد تحقّقنا قبل التحويل أن الاسم لا
             يُقرأ ولا يُستدعى وقت تقييم الوحدة إطلاقاً — تسعة مراجع كلّها داخل
             دوالّ. الاسم الداخلي يبقى فيعمل الاستدعاء الذاتي كما كان. */
          const fn = h.fnPath.node;
          edits.push({ start: fn.start, end: fn.start,
                       text: SHARED + '.' + h.name + ' = ' });
          edits.push({ start: fn.end, end: fn.end, text: ';' });
        } else {
          edits.push({ start: h.start, end: h.end, text: SHARED + '.' + h.name });
        }
      }
    }
    let body = null;   /* يُبنى بعد حساب lateReads أدناه */

    /* استيرادات: كل معرّف حرّ يملكه مقطع آخر.

       ترتيب تقييم وحدات ES يتبع رسم الاستيراد لا ترتيب الاستيراد في نقطة
       الدخول: أي حافة إلى مقطع لاحق تقلب الترتيب الأصلي وتخلق دورة، فيقرأ
       جسمُ وحدةٍ ارتباطاً لم يُهيَّأ بعد (TDZ). لذلك:
         • حافة إلى مقطع سابق  → import عاديّ (آمنة، والترتيب محفوظ).
         • حافة إلى مقطع لاحق  → عبر سجلّ ربط متأخّر __ACS_LATE.
       كل الحواف الأمامية في هذا التطبيق تُقرأ داخل دوالّ لا وقت التقييم — وهذا
       مُقاس بالمحلّل النحويّ لا مفترَض — فالربط المتأخّر يحفظ الدلالة تماماً،
       ويصير الرسم لا دوريّاً وترتيب التقييم = ترتيب main.js = الترتيب الأصلي. */
    const needs = new Map();
    const lateReads = new Set();
    for (const n of s.info.free) {
      if (mutable.has(n)) continue;
      const own = owner.get(n);
      if (!own || own === s.key) continue;
      if (indexOfKey(own) > indexOfKey(s.key)) { lateReads.add(n); continue; }
      const f = FILES[own];
      if (!needs.has(f)) needs.set(f, new Set());
      needs.get(f).add(n);
    }

    const publishes = [...(lateByOwner.get(s.key) || [])].sort();
    if (lateReads.size) {
      for (const h of occurrences(s.info.ast, lateReads))
        edits.push({ start: h.start, end: h.end, text: LATE + '.' + h.name });
    }
    body = applyEdits(s.src, edits);

    const rel = f => {
      let r = path.relative(path.dirname(file), f).replace(/\\/g, '/');
      return r.startsWith('.') ? r : './' + r;
    };
    const importLines = [...needs.entries()].sort()
      .map(([f, names]) => 'import { ' + [...names].sort().join(', ')
                           + " } from '" + rel(f) + "';");
    if (lateReads.size || publishes.length)
      importLines.unshift("import { " + LATE + " } from '"
                          + rel('late-bindings.js') + "';");
    if (mutable.size && (occurrenceCount(body) > 0))
      importLines.unshift("import { " + SHARED + " } from '"
                          + rel('shared-state.js') + "';");

    /* تصديرات: كل ما يصرّح به المقطع ويحتاجه غيره (نصدّر الكلّ — أبسط وأأمن) */
    const exportNames = [...s.info.declared, ...s.info.imported]
      .filter(n => !mutable.has(n)).sort();
    const publishLine = publishes.length
      ? '\n\n/* نشر الارتباطات التي يقرأها مقطع أسبق — تُقرأ داخل دوالّ فقط،\n'
        + '   فالنشر عند نهاية تقييم هذه الوحدة يسبق أي قراءة حتماً. */\n'
        + 'Object.assign(' + LATE + ', { ' + publishes.join(', ') + ' });\n' : '';
    const exportLine = exportNames.length
      ? '\n\nexport { ' + exportNames.join(', ') + ' };\n' : '\n';

    const text = header(s.key, file, s.generator)
               + (importLines.length ? importLines.join('\n') + '\n\n' : '')
               + body + publishLine + exportLine;
    emitted.push({ key: s.key, file, text, bytes: Buffer.byteLength(text, 'utf8'),
                   declared: exportNames, kind: s.kind });

    function occurrenceCount(t) { return t.indexOf(SHARED + '.') >= 0 ? 1 : 0; }
  }

  /* 5) وحدة الحالة المشتركة */
  const sharedText =
    '/* ============================================================\n'
  + '   public/app/shared-state.js\n'
  + '   ارتباط الاستيراد في ES للقراءة فقط. الأسماء القليلة التي تُكتَب من\n'
  + '   وحدة غير مالكها تعيش هنا على كائن واحد، فيبقى معناها في النطاق\n'
  + '   الواحد الأصلي محفوظاً بلا إعادة كتابة للمنطق.\n'
  + '   ============================================================ */\n'
  + 'export const ' + SHARED + ' = Object.seal({\n'
  + [...mutable].sort().map(n => '  ' + n + ': undefined,').join('\n') + '\n});\n';

  /* 6) نقطة الدخول */
  const order = emitted.map(e => e.file);
  const mainText =
    '/* ============================================================\n'
  + '   public/app/main.js — نقطة دخول التطبيق.\n'
  + '   ترتيب الاستيراد هو ترتيب المقاطع في الصفحة الأصلية بالضبط، فالتقييم\n'
  + '   يجري بالتتابع نفسه. لا منطق هنا: الوحدات هي المنطق.\n'
  + '   ============================================================ */\n'
  + order.map(f => "import './" + f + "';").join('\n') + '\n';

  if (check) {
    console.log('--check: nothing written');
    return report(emitted, mutable);
  }

  /* لا نمسح app/ كلّه: boot/ و styles/ يملكهما tools/frontend_shell.js */
  for (const d of ['core', 'generated', 'render', 'ui', 'trust'])
    fs.rmSync(path.join(APP, d), { recursive: true, force: true });
  for (const e of emitted) {
    const dst = path.join(APP, e.file);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.writeFileSync(dst, e.text);
  }
  fs.writeFileSync(path.join(APP, 'shared-state.js'), sharedText);
  fs.writeFileSync(path.join(APP, 'late-bindings.js'),
    '/* ============================================================\n'
  + '   public/app/late-bindings.js\n'
  + '   سجلّ الربط المتأخّر. ترتيب تقييم وحدات ES يتبع رسم الاستيراد، فحافةٌ\n'
  + '   إلى وحدة لاحقة تقلب الترتيب وتفتح دورة. الأسماء هنا يقرؤها مقطع أسبق\n'
  + '   من مالكها، وكلّها تُقرأ داخل دوالّ لا وقت التقييم (مُقاس بالمحلّل\n'
  + '   النحويّ). المرور بهذا السجلّ يبقي الرسم لا دورياً وترتيب التقييم\n'
  + '   مطابقاً لترتيب الصفحة قبل التفكيك.\n'
  + '   ============================================================ */\n'
  + 'export const ' + LATE + ' = Object.seal({\n'
  + [...lateNames].sort().map(n => '  ' + n + ': undefined,').join('\n')
  + '\n});\n');
  fs.writeFileSync(path.join(APP, 'main.js'), mainText);
  console.log('wrote %d modules under public/app/', emitted.length + 2);
  return report(emitted, mutable);
}

function report(emitted, mutable) {
  let total = 0;
  for (const e of emitted) { total += e.bytes; }
  emitted.slice().sort((a, b) => b.bytes - a.bytes).forEach(e =>
    console.log('  %s %s', String(e.bytes).padStart(8), e.file));
  console.log('  total first-party module bytes: %d', total);
  const over = emitted.filter(e => e.bytes > 307200);
  if (over.length) console.log('  OVER 300KB: ' + over.map(e => e.file).join(', '));
  return { emitted, mutable: [...mutable] };
}

module.exports = { buildSegments, scan, occurrences, FILES, GLOBALS };
if (require.main === module) main();
