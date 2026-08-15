/* ============================================================================
   tests/remediation/test_module_graph.js — F-09: قفل خاصّية ترتيب التقييم.

   F-09 فكّك صفحةً واحدة (١٫٨٦ م.ب، نطاق واحد، ترتيب تقييم = ترتيب النصّ) إلى
   وحدات ES. ترتيب تقييم وحدات ES يتبع رسم الاستيراد لا ترتيب السطور، فحافةٌ
   واحدة إلى وحدة لاحقة تقلب الترتيب أو تفتح دورة، وعندها يقرأ مقطعٌ اسماً في
   منطقة الموت الزمني (TDZ) أو يقرأ `undefined` فيمرّ صامتاً. الخاصّية التي
   تحفظ التكافؤ مع الصفحة قبل التفكيك دقيقة وغير مرئية في أي اختبار آخر، ولذلك
   تُقفَل هنا صراحة، بمحلّل نحويّ حقيقي لا بتعبير نمطي:

     §1  كل وحدة تحت public/app (عدا boot/ و styles/) يستوردها main.js مرّة
         واحدة بالضبط، وmain.js لا يحمل منطقاً — سطور استيراد فقط.
     §2  رسم الاستيراد الطرفيّ الأوّل لا دوري.
     §3  كل حافّة تشير إلى الوراء في ترتيب استيراد main.js.
     §4  لا معرّف حرّ غير محلول في أي وحدة خارج قائمة tools/frontend_globals.txt.
     §5  __ACS_LATE لا يُقرأ إلّا من وحدة أسبق من مالكه، ولا يُكتَب إلّا بسطر
         النشر الواحد Object.assign(__ACS_LATE, {…}) في آخر الوحدة المالكة.

   المحلّل: حزمة Babel المضمّنة في playwright (لا شبكة، لا تثبيت) — نفس المحلّل
   الذي يستعمله tools/frontend_analyze.js و tests/phase3/lib/extract_browser_bundle.js.
   ============================================================================ */
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const APP = require(path.join(ROOT, 'tests', 'lib', 'app_source.js'));
const B = require(path.join(ROOT, 'node_modules', 'playwright', 'lib',
                            'transform', 'babelBundle.js'));

let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
                             : (fail++, console.log('  ✗', n,
                                                    d === undefined ? '' : d)); };

const mods = APP.modules();
const order = APP.order();
const ENTRY = 'main.js';
/* boot/ سكربتات كلاسيكية يحمّلها <script> في القشرة قبل خريطة الاستيراد،
   وstyles/ ورقة أنماط — لا واحد منهما وحدة ES يستوردها main.js. */
const isBoot = f => f.indexOf('boot/') === 0;
const graphModules = Object.keys(mods)
  .filter(f => !isBoot(f) && f !== ENTRY).sort();

/* المعرّفات المسموح بقاؤها حرّة — تُقرأ من الملفّ المعلن، لا من قائمة هنا. */
const DECLARED_GLOBALS = new Set(
  fs.readFileSync(path.join(ROOT, 'tools', 'frontend_globals.txt'), 'utf8')
    .split('\n').map(s => s.trim()).filter(s => s && s[0] !== '#'));
/* استثناءان مسمّيان لا يزيدان صلاحية أحد:
     addEventListener — window.addEventListener بلا مؤهِّل؛ اسم بيئة متصفّح
       قائم مثل كل ما في القائمة، وغيابه عنها ثغرةٌ في tools/frontend_globals.txt
       مُبلَّغ عنها (لا يجوز لهذه المجموعة تعديل tools/).
     arguments — كلمة اللغة داخل دالّة عادية؛ Babel لا يُنشئ لها ارتباطاً في
       النطاق فتظهر «حرّة» وهي ليست كذلك. */
const PARSER_AND_ENV_EXEMPT = new Set(['addEventListener', 'arguments']);

function parse(src, label, isModule) {
  return B.babelParse(src, String(label).replace(/[^A-Za-z0-9_.-]/g, '_'),
                      isModule);
}

/* ── §1 — كل وحدة مستوردة من main.js مرّة واحدة بالضبط ───────────────────── */
console.log('\n== §1 — MAIN.JS IS THE ONE ENTRY, AND IT IMPORTS EVERY MODULE '
            + 'EXACTLY ONCE ==');
chk('the entry module exists', !!mods[ENTRY]);
chk('the module set is not empty — this suite would otherwise be vacuous',
    graphModules.length >= 19, String(graphModules.length));
{
  const ast = parse(mods[ENTRY], ENTRY, true);
  const body = ast.program.body;
  chk('main.js carries no logic: every top-level statement is an import',
      body.length > 0 && body.every(s => s.type === 'ImportDeclaration'),
      JSON.stringify(Array.from(new Set(body.map(s => s.type)))));
  chk('every main.js import is a bare side-effect import of a relative module',
      body.every(s => s.specifiers.length === 0
                      && /^\.\//.test(s.source.value)),
      JSON.stringify(body.filter(s => s.specifiers.length)
        .map(s => s.source.value)));
  chk('the reader agrees with the parser on the import order',
      JSON.stringify(order)
      === JSON.stringify(body.map(s => s.source.value.replace(/^\.\//, ''))),
      JSON.stringify(order));
}
{
  const seen = {};
  order.forEach(f => { seen[f] = (seen[f] || 0) + 1; });
  chk('no module is imported twice by main.js',
      Object.keys(seen).every(k => seen[k] === 1),
      JSON.stringify(Object.keys(seen).filter(k => seen[k] > 1)));
  chk('every module main.js imports really exists on disk',
      order.every(f => !!mods[f]),
      JSON.stringify(order.filter(f => !mods[f])));
  const missing = graphModules.filter(f => order.indexOf(f) < 0);
  chk('not one module under public/app is orphaned — every non-boot, '
      + 'non-style module is imported by main.js',
      missing.length === 0, JSON.stringify(missing));
  chk('main.js imports nothing beyond those modules',
      order.every(f => graphModules.indexOf(f) >= 0),
      JSON.stringify(order.filter(f => graphModules.indexOf(f) < 0)));
  chk('the two leaf registries are imported first, in the declared order',
      JSON.stringify(order.slice(0, APP.REGISTRIES.length))
      === JSON.stringify(APP.REGISTRIES),
      JSON.stringify(order.slice(0, 2)));
}

/* ── الرسم: الحوافّ الطرفية الأولى وحدها (three وتوابعها خارجيّة) ────────── */
const EXTERNAL_PREFIX = 'three';
const edges = [];          /* [from, to] لكل استيراد طرفيّ أوّل */
const external = new Set();
const astOf = {};
for (const f of Object.keys(mods)) {
  const isMod = !isBoot(f);
  let ast;
  try { ast = parse(mods[f], f, isMod); }
  catch (e) { chk('public/app/' + f + ' parses', false, String(e.message)); continue; }
  astOf[f] = ast;
  if (isBoot(f)) continue;
  for (const st of ast.program.body) {
    if (st.type !== 'ImportDeclaration' && st.type !== 'ExportNamedDeclaration'
        && st.type !== 'ExportAllDeclaration') continue;
    const spec = st.source && st.source.value;
    if (!spec) continue;
    if (spec[0] === '.') {
      edges.push([f, path.posix.normalize(
        path.posix.join(path.posix.dirname(f), spec))]);
    } else external.add(spec);
  }
}
const firstParty = edges.filter(e => e[0] !== ENTRY);

console.log('\n== §2 — THE FIRST-PARTY IMPORT GRAPH IS ACYCLIC ==');
chk('every module parsed', Object.keys(astOf).length === Object.keys(mods).length,
    Object.keys(astOf).length + '/' + Object.keys(mods).length);
chk('the graph is not empty — this suite would otherwise be vacuous',
    firstParty.length >= 50, String(firstParty.length));
chk('every import target resolves to a real module under public/app',
    edges.every(e => !!mods[e[1]]),
    JSON.stringify(edges.filter(e => !mods[e[1]])));
chk('the only bare specifiers are the three renderer entries declared in the '
    + 'import map',
    Array.from(external).every(s => s === EXTERNAL_PREFIX
      || s.indexOf(EXTERNAL_PREFIX + '/') === 0),
    JSON.stringify(Array.from(external).sort()));
{
  /* بحث عمق أوّل بثلاثة ألوان — يُبلّغ الدورة كاملة لا مجرّد وجودها */
  const adj = {};
  edges.forEach(([a, b]) => { (adj[a] = adj[a] || []).push(b); });
  const colour = {}, stack = [];
  let cycle = null;
  const walk = n => {
    if (cycle) return;
    colour[n] = 1; stack.push(n);
    for (const m of (adj[n] || [])) {
      if (colour[m] === 1) { cycle = stack.slice(stack.indexOf(m)).concat([m]); return; }
      if (!colour[m]) { walk(m); if (cycle) return; }
    }
    colour[n] = 2; stack.pop();
  };
  Object.keys(mods).filter(f => !isBoot(f)).forEach(f => { if (!colour[f]) walk(f); });
  chk('there is no import cycle anywhere in public/app', cycle === null,
      cycle ? cycle.join(' -> ') : '');
  chk('the traversal really reached every module (it did not stop early)',
      Object.keys(mods).filter(f => !isBoot(f)).every(f => colour[f] === 2),
      JSON.stringify(Object.keys(mods).filter(f => !isBoot(f) && colour[f] !== 2)));
}

console.log('\n== §3 — EVERY EDGE POINTS BACKWARDS IN MAIN.JS IMPORT ORDER ==');
{
  const forward = firstParty.filter(([a, b]) => {
    const ia = order.indexOf(a), ib = order.indexOf(b);
    return ia < 0 || ib < 0 || ib >= ia;
  });
  chk('no module imports one that main.js evaluates later or at the same rank',
      forward.length === 0,
      JSON.stringify(forward.map(e => e[0] + ' -> ' + e[1]).slice(0, 8)));
  chk('main.js itself imports nothing but graph modules (its own edges are the '
      + 'entry edges, not intra-graph edges)',
      edges.filter(e => e[0] === ENTRY).every(e => order.indexOf(e[1]) >= 0));
  /* الترتيب المستقرّ: ترتيب main.js هو ترتيب طوبولوجي صالح للرسم. لو كان
     صالحاً لكن غير الترتيب المشحون لتغيّر زمن التقييم بلا أن يظهر أعلاه. */
  const rank = {}; order.forEach((f, i) => { rank[f] = i; });
  chk('main.js import order is a valid topological order of the whole graph',
      firstParty.every(([a, b]) => rank[b] < rank[a]));
}

console.log('\n== §4 — NO UNRESOLVED FREE IDENTIFIER IN ANY MODULE ==');
{
  let checked = 0;
  const offenders = [];
  for (const f of Object.keys(astOf)) {
    let globals = [];
    B.traverse(astOf[f], { Program(p) {
      globals = Object.keys(p.scope.globals || {}); p.stop(); } });
    checked++;
    const bad = globals.filter(n => !DECLARED_GLOBALS.has(n)
                                    && !PARSER_AND_ENV_EXEMPT.has(n));
    if (bad.length) offenders.push(f + ': ' + bad.join(', '));
  }
  chk('every file under public/app was scanned', checked === Object.keys(mods).length,
      checked + '/' + Object.keys(mods).length);
  chk('not one module reaches for a name that is neither imported, nor '
      + 'declared, nor a declared browser global',
      offenders.length === 0, JSON.stringify(offenders.slice(0, 8)));
  chk('the declared-globals list is the real one and is not empty',
      DECLARED_GLOBALS.size >= 100 && DECLARED_GLOBALS.has('window')
      && DECLARED_GLOBALS.has('document'), String(DECLARED_GLOBALS.size));
  chk('the two named exemptions stay exactly two — no quiet growth',
      PARSER_AND_ENV_EXEMPT.size === 2);
}

console.log('\n== §5 — __ACS_LATE IS READ EARLY AND WRITTEN ONCE, BY ITS OWNER ==');
{
  const REG = 'late-bindings.js';
  /* مفاتيح السجلّ كما هي في الملفّ — من الشجرة لا بتعبير نمطي */
  const regKeys = [];
  let sealed = false;
  B.traverse(parse(mods[REG], REG, true), {
    CallExpression(p) {
      const c = p.node.callee;
      if (c.type === 'MemberExpression' && c.object.name === 'Object'
          && c.property.name === 'seal' && p.node.arguments[0]
          && p.node.arguments[0].type === 'ObjectExpression') {
        sealed = true;
        p.node.arguments[0].properties.forEach(pr => regKeys.push(pr.key.name));
      }
    }
  });
  chk('the registry is a sealed object literal, so an unregistered name cannot '
      + 'be published by accident', sealed && regKeys.length > 0);
  chk('the registry declares the twenty forward references it is documented to',
      regKeys.length === 20, String(regKeys.length));

  const reads = {};          /* module -> Set(name) */
  const publishedBy = {};    /* name -> [module] */
  const pubStatements = {};  /* module -> count of publish statements */
  const violations = [];
  for (const f of graphModules) {
    const seen = new Set();
    B.traverse(astOf[f], {
      MemberExpression(p) {
        const n = p.node;
        if (n.object.type !== 'Identifier' || n.object.name !== '__ACS_LATE') return;
        if (n.computed) {
          violations.push(f + ': computed access to __ACS_LATE defeats the '
                          + 'static check'); return; }
        seen.add(n.property.name);
      },
      AssignmentExpression(p) {
        const l = p.node.left;
        if (l.type === 'MemberExpression' && l.object.type === 'Identifier'
            && l.object.name === '__ACS_LATE')
          violations.push(f + ': assigns __ACS_LATE.' + (l.property.name || '?')
                          + ' directly instead of the single publish line');
      },
      UpdateExpression(p) {
        const a = p.node.argument;
        if (a.type === 'MemberExpression' && a.object.type === 'Identifier'
            && a.object.name === '__ACS_LATE')
          violations.push(f + ': mutates __ACS_LATE in place');
      }
    });
    /* سطر النشر: تعليمة عليا وحيدة بالشكل القانوني الوحيد */
    let count = 0;
    for (const st of astOf[f].program.body) {
      if (st.type !== 'ExpressionStatement') continue;
      const e = st.expression;
      if (!e || e.type !== 'CallExpression') continue;
      const c = e.callee;
      if (c.type !== 'MemberExpression' || c.object.name !== 'Object'
          || c.property.name !== 'assign') continue;
      if (!e.arguments[0] || e.arguments[0].name !== '__ACS_LATE') continue;
      count++;
      if (e.arguments.length !== 2 || e.arguments[1].type !== 'ObjectExpression') {
        violations.push(f + ': the publish line is not a plain object literal');
        continue; }
      for (const pr of e.arguments[1].properties) {
        if (pr.type !== 'ObjectProperty' || !pr.shorthand
            || pr.key.type !== 'Identifier') {
          violations.push(f + ': the publish line uses a non-shorthand key');
          continue; }
        (publishedBy[pr.key.name] = publishedBy[pr.key.name] || []).push(f);
        seen.delete(pr.key.name);
      }
    }
    if (count > 1) violations.push(f + ': ' + count + ' publish lines, expected one');
    if (seen.size) reads[f] = seen;
  }

  chk('no module writes into __ACS_LATE by any route other than its one '
      + 'Object.assign publish line', violations.length === 0,
      JSON.stringify(violations.slice(0, 6)));
  const owned = Object.keys(publishedBy).sort();
  chk('every registry key is published by exactly one module',
      owned.every(n => publishedBy[n].length === 1),
      JSON.stringify(owned.filter(n => publishedBy[n].length > 1)));
  chk('the published names are exactly the registry keys — no key is dead and '
      + 'no name is published without a slot',
      JSON.stringify(owned) === JSON.stringify(regKeys.slice().sort()),
      JSON.stringify({ published: owned, registry: regKeys.slice().sort() }));

  const readers = Object.keys(reads).sort();
  chk('the registry is actually used — this section would otherwise be vacuous',
      readers.length >= 3
      && readers.reduce((s, f) => s + reads[f].size, 0) >= 20,
      JSON.stringify(readers.map(f => f + '=' + reads[f].size)));
  const late = [];
  const orphan = [];
  readers.forEach(f => reads[f].forEach(n => {
    if (!publishedBy[n]) { orphan.push(f + ' reads ' + n + ' — nobody publishes it');
      return; }
    const owner = publishedBy[n][0];
    if (order.indexOf(f) >= order.indexOf(owner))
      late.push(f + ' reads ' + n + ' owned by the not-earlier ' + owner);
  }));
  chk('every __ACS_LATE name a module reads is really published somewhere',
      orphan.length === 0, JSON.stringify(orphan.slice(0, 6)));
  chk('a module only ever reads a __ACS_LATE name whose owner main.js '
      + 'evaluates strictly later — which is exactly why the edge was moved '
      + 'into the registry instead of becoming a forward import',
      late.length === 0, JSON.stringify(late.slice(0, 6)));
  /* الشرط الآخر الذي يجعل السجلّ آمناً: القراءة داخل دالّة، لا وقت التقييم */
  const evalTime = [];
  readers.forEach(f => {
    B.traverse(astOf[f], {
      MemberExpression(p) {
        const n = p.node;
        if (n.object.type !== 'Identifier' || n.object.name !== '__ACS_LATE') return;
        if (p.getFunctionParent()) return;
        if (p.findParent(x => x.isExpressionStatement()
              && x.node.expression.type === 'CallExpression')) { /* سطر النشر */ }
        evalTime.push(f + ': __ACS_LATE.' + n.property.name
                      + ' is read at evaluation time, not inside a function');
      }
    });
  });
  chk('no __ACS_LATE name is read while a module is being evaluated — every '
      + 'read sits inside a function, so the registry is full by call time',
      evalTime.length === 0, JSON.stringify(evalTime.slice(0, 6)));
}

console.log('\n──────────────────────────────────────────────');
console.log('F-09 MODULE GRAPH: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
