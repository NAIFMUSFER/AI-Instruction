/* ============================================================================
   F-11 — عقد سياسة المحتوى: ما يمكن تشديده مشدَّد، وما لا يمكن مُعلَن ومُتعقَّب.

   يُشغَّل هكذا:
     node tests/lib/run.js tests/remediation/test_csp.js      (كما في run_all.sh)
     node tests/remediation/test_csp.js                        (مستقلّاً)

   الفكرة الحاكمة: سياسة فيها 'unsafe-inline' و'unsafe-eval' ضعيفة سواء
   اعترفنا أم لا. الفرق الوحيد الذي نملكه اليوم هو بين ضعف صامت وضعف متعقَّب.
   لذلك هذا الملفّ لا يقبل وجود 'unsafe-*' إلّا إذا كان مُوثَّقاً في
   CSP-HARDENING.md بسببه، وبثمن إزالته، وبتصريح أن التشديد غير مكتمل. غياب
   التوثيق = فشل.

   القياس الحيّ في متصفّح حقيقي يعيش في ملفّ منفصل:
     node tests/remediation/csp_browser_probe.js
   ويُقارَن مخرجه هنا إن وُجد (§9). لا يُشترط وجوده كي لا يدّعي هذا الملفّ
   قياساً لم يجرِ.
   ========================================================================== */
const fs = require('fs'), _np = require('path');
const HERE = __dirname, ROOT = _np.resolve(HERE, '..', '..');
let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
  : (fail++, console.log('  ✗', n, d === undefined ? '' : String(d).slice(0, 260))); };
const rd = rel => fs.readFileSync(_np.join(ROOT, rel), 'utf8');

const TOML = rd('netlify.toml');
const PAGE = rd('public/index.html');
const RENDER = rd('render.yaml');
const API = rd('acs_understand_api.py');
const DOC_PATH = 'CSP-HARDENING.md';
const DOC = fs.existsSync(_np.join(ROOT, DOC_PATH)) ? rd(DOC_PATH) : '';

/* مضيفو الشبكات الخارجية الممنوعون — نفس القائمة المستعملة في تحقّق الإنتاج */
const CDN_HOSTS = ['cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com',
  'ajax.googleapis.com', 'esm.sh', 'skypack.dev', 'jspm.io', 'polyhaven.com',
  'fonts.googleapis.com', 'fonts.gstatic.com', 'code.jquery.com',
  'stackpath.bootstrapcdn.com', 'raw.githubusercontent.com'];

/* ------------------------------------------------------------- محلّل ----- */
function parseCSP(text) {
  const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(text);
  if (!m) return null;
  const raw = m[1];
  const map = new Map();
  const order = [];
  raw.split(';').forEach(part => {
    const toks = part.trim().split(/\s+/).filter(Boolean);
    if (!toks.length) return;
    map.set(toks[0], toks.slice(1));
    order.push(toks[0]);
  });
  return { raw, map, order };
}

console.log('\n== §1 — THE POLICY IS DELIVERED AS A RESPONSE HEADER AND PARSES ==');
const CSP = parseCSP(TOML);
chk('netlify.toml declares a Content-Security-Policy response header', !!CSP);
if (!CSP) {
  console.log('\nCSP: cannot continue without a policy');
  process.exit(1);
}
chk('the policy is on the site-wide header block, not a single path',
    /for\s*=\s*["']\/\*["'][\s\S]{0,4000}?Content-Security-Policy/.test(TOML));
chk('no <meta http-equiv="Content-Security-Policy"> shadows the header '
    + '(meta cannot express frame-ancestors and would measure a different '
    + 'policy than the one deployed)',
    !/http-equiv\s*=\s*["']Content-Security-Policy/i.test(PAGE));
chk('every directive name appears exactly once',
    CSP.order.length === new Set(CSP.order).size,
    CSP.order.join(','));
console.log('  policy: ' + CSP.raw);

console.log('\n== §2 — EVERY REQUIRED DIRECTIVE IS PRESENT WITH THE EXPECTED '
  + 'VALUE ==');
/* القيمة المتوقّعة كمجموعة مرتّبة: أي توسيع أو حذف يسقط هنا. */
const EXPECTED = {
  'default-src': ["'self'"],
  'base-uri': ["'self'"],
  'object-src': ["'none'"],
  'frame-ancestors': ["'none'"],
  'img-src': ["'self'", 'data:', 'blob:'],
  'style-src': ["'self'", "'unsafe-inline'"],
  'font-src': ["'self'", 'data:'],
  'worker-src': ["'self'", 'blob:'],
  'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'blob:'],
  /* التشديد المضاف في F-11 — مجاني لأن الصفحة لا تستعمل أياً من هذه القدرات */
  'form-action': ["'self'"],
  'frame-src': ["'none'"],
  'manifest-src': ["'self'"],
  'media-src': ["'self'"]
};
Object.keys(EXPECTED).forEach(d => {
  const got = CSP.map.get(d);
  chk('`' + d + '` is present with exactly ' + JSON.stringify(EXPECTED[d]),
      !!got && got.length === EXPECTED[d].length
      && EXPECTED[d].every(t => got.indexOf(t) >= 0),
      got ? got.join(' ') : 'MISSING');
});
chk('`connect-src` is present', CSP.map.has('connect-src'));
chk('`upgrade-insecure-requests` is present (valueless directive)',
    CSP.map.has('upgrade-insecure-requests')
    && CSP.map.get('upgrade-insecure-requests').length === 0);

console.log('\n== §3 — THE SURFACE-REDUCING DIRECTIVES ARE EXACT ==');
chk("object-src is 'none'", (CSP.map.get('object-src') || []).join(' ') === "'none'");
chk("base-uri is 'self'", (CSP.map.get('base-uri') || []).join(' ') === "'self'");
chk("frame-ancestors is 'none'",
    (CSP.map.get('frame-ancestors') || []).join(' ') === "'none'");
chk('frame-ancestors is backed by X-Frame-Options: DENY for old agents',
    /X-Frame-Options\s*=\s*"DENY"/.test(TOML));

console.log('\n== §4 — NO DANGEROUS SOURCE ANYWHERE IN THE POLICY ==');
const ALL_TOKENS = [];
CSP.map.forEach((v, k) => v.forEach(t => ALL_TOKENS.push([k, t])));
chk('no `javascript:` source in any directive',
    !ALL_TOKENS.some(([, t]) => /^javascript:/i.test(t)),
    JSON.stringify(ALL_TOKENS.filter(([, t]) => /^javascript:/i.test(t))));
chk('the raw policy text contains no `javascript:` at all',
    CSP.raw.toLowerCase().indexOf('javascript:') < 0);
chk('no bare wildcard `*` source in any directive',
    !ALL_TOKENS.some(([, t]) => t === '*'),
    JSON.stringify(ALL_TOKENS.filter(([, t]) => t === '*')));
chk('no wildcard-subdomain source (`*.`) in any directive',
    !ALL_TOKENS.some(([, t]) => t.indexOf('*.') === 0));
chk('no insecure `http:` scheme source, and no `http://` origin',
    !ALL_TOKENS.some(([, t]) => t === 'http:' || /^http:\/\//i.test(t)));
chk('no `data:` source in script-src (a data: script is an XSS primitive)',
    (CSP.map.get('script-src') || []).indexOf('data:') < 0);
chk('no `data:` source in default-src either',
    (CSP.map.get('default-src') || []).indexOf('data:') < 0);
chk("no 'unsafe-hashes' is smuggled in",
    CSP.raw.indexOf("'unsafe-hashes'") < 0);
chk("the only 'unsafe-*' tokens are the two declared ones, and only where "
    + 'declared',
    ALL_TOKENS.filter(([, t]) => t.indexOf("'unsafe-") === 0)
      .every(([d, t]) => (d === 'script-src'
        && (t === "'unsafe-inline'" || t === "'unsafe-eval'"))
        || (d === 'style-src' && t === "'unsafe-inline'")),
    JSON.stringify(ALL_TOKENS.filter(([, t]) => t.indexOf("'unsafe-") === 0)));

console.log('\n== §5 — connect-src PINS EXACTLY THE DECLARED BACKEND ORIGIN ==');
/* الأصل يُشتقّ من عقد النشر لا من السياسة نفسها: خدمة Render اسمها acs-engine
   ⇒ https://acs-engine.onrender.com. لو غُيّر اسم الخدمة ولم تُغيّر السياسة،
   يسقط هذا الفحص — وهو بالضبط الحادث الذي يمنعه. */
const svc = /(?:^|\n)\s*-\s*type:\s*web[\s\S]{0,200}?\n\s*name:\s*([A-Za-z0-9_-]+)/
  .exec(RENDER);
chk('render.yaml declares exactly one web service with a name', !!svc,
    svc ? svc[1] : 'no `type: web` + `name:` pair found');
const backendOrigin = svc ? 'https://' + svc[1] + '.onrender.com' : null;
console.log('  backend origin derived from render.yaml: ' + backendOrigin);
const pageBase = (/CONFIGURED_BASE\s*=\s*"([^"]*)"/.exec(PAGE) || [, ''])[1]
  .replace(/\/+$/, '');
chk('public/index.html declares the same origin exactly once',
    (PAGE.match(/CONFIGURED_BASE\s*=\s*"/g) || []).length === 1
    && pageBase === backendOrigin,
    'page=' + pageBase + ' render.yaml=' + backendOrigin);
const connect = CSP.map.get('connect-src') || [];
chk("connect-src is exactly ['self', <backend origin>] and nothing else",
    connect.length === 2 && connect.indexOf("'self'") >= 0
    && connect.indexOf(backendOrigin) >= 0,
    connect.join(' '));
/* الاتجاه المعاكس لا يُخلط: أصل الواجهة (CORS على الخادم) ليس وجهة اتصال. */
const feOrigin = (/_DEFAULT_ORIGIN\s*=\s*"([^"]+)"/.exec(API) || [, ''])[1];
chk('the backend CORS allow-list origin was located in acs_understand_api.py',
    !!feOrigin, feOrigin);
chk('that frontend origin is NOT in connect-src — it is what the backend '
    + 'allows to call it, not what the page may call',
    !!feOrigin && connect.indexOf(feOrigin) < 0, feOrigin);
chk('render.yaml ACS_ALLOWED_ORIGINS names the frontend, matching the API '
    + 'default (one origin story, not two)',
    new RegExp('ACS_ALLOWED_ORIGINS[\\s\\S]{0,160}?'
      + feOrigin.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(RENDER));
chk('no second remote origin was added to any directive',
    ALL_TOKENS.filter(([, t]) => /^https:\/\//i.test(t))
      .every(([d, t]) => d === 'connect-src' && t === backendOrigin),
    JSON.stringify(ALL_TOKENS.filter(([, t]) => /^https:\/\//i.test(t))));

console.log('\n== §6 — NO CDN HOST IN THE POLICY, AND NO RUNTIME CDN URL IN '
  + 'THE PAGE ==');
CDN_HOSTS.forEach(h => chk('no directive allows ' + h,
  CSP.raw.toLowerCase().indexOf(h) < 0));
/* الصفحة نفسها: أي إشارة إلى مضيف CDN تعني اعتماداً وقت التشغيل على طرف ثالث،
   وهو ما تمنعه سياسة الاعتمادية أصلاً. تُستثنى التعليقات التي تشرح المنع. */
CDN_HOSTS.forEach(h => {
  const lines = PAGE.split('\n')
    .map((l, i) => [i + 1, l])
    .filter(([, l]) => l.indexOf(h) >= 0);
  chk('public/index.html carries no reference to ' + h, lines.length === 0,
      lines.slice(0, 2).map(([i, l]) => i + ':' + l.trim().slice(0, 90)).join(' | '));
});
/* لا عنوان مطلق يُحمَّل منه سكربت أو وحدة وقت التشغيل */
chk('no <script src="http…"> in the shipped page',
    !/<script[^>]+src\s*=\s*["']https?:\/\//i.test(PAGE));
chk('no <link href="http…"> in the shipped page',
    !/<link[^>]+href\s*=\s*["']https?:\/\//i.test(PAGE));
chk('no import map entry points at a remote origin',
    (function () {
      const m = /<script type="importmap">([\s\S]*?)<\/script>/.exec(PAGE);
      if (!m) return false;
      try {
        const im = JSON.parse(m[1]);
        return Object.values(im.imports || {})
          .every(v => String(v).indexOf('/') === 0);
      } catch (e) { return false; }
    })());
chk('the es-module-shims loader points at a local path, not a CDN',
    /s\.src\s*=\s*'\/vendor\/es-module-shims@[0-9.]+\/es-module-shims\.js'/
      .test(PAGE));

console.log('\n== §7 — EVERY WEAKNESS THE POLICY STILL CARRIES IS DECLARED IN '
  + 'WRITING ==');
/* هذا القسم هو جوهر F-11: 'unsafe-*' مسموح به فقط إن كان متعقَّباً.
   لو حُذف CSP-HARDENING.md أو أُفرغ من الشرح، يفشل هنا فوراً. */
chk(DOC_PATH + ' exists', DOC.length > 0);
chk(DOC_PATH + ' is a real audit, not a stub', DOC.length > 4000,
    String(DOC.length));
const UNSAFE_PRESENT = [];
CSP.map.forEach((v, k) => v.forEach(t => {
  if (t.indexOf("'unsafe-") === 0 || t === 'blob:') UNSAFE_PRESENT.push(k + ' ' + t);
}));
console.log('  permissive sources still in the policy: '
  + JSON.stringify(UNSAFE_PRESENT));
[["'unsafe-inline'", 'script-src'], ["'unsafe-eval'", 'script-src'],
 ["'unsafe-inline'", 'style-src'], ['blob:', 'script-src'],
 ['blob:', 'worker-src'], ['data:', 'img-src'], ['blob:', 'img-src']]
  .forEach(([tok, dir]) => {
    if ((CSP.map.get(dir) || []).indexOf(tok) < 0) return;
    chk('`' + dir + ' ' + tok + '` is present, so ' + DOC_PATH
        + ' must name it', DOC.indexOf(tok) >= 0 && DOC.indexOf(dir) >= 0,
        'token documented=' + (DOC.indexOf(tok) >= 0)
        + ' directive documented=' + (DOC.indexOf(dir) >= 0));
  });
const DOC_MUST_SAY = [
  ['why unsafe-inline is required (the whole app is inline)',
   /entire application is one inline|whole application is inline|the whole application is inline|application is one inline/i],
  /* لا رقم مثبَّت هنا: public/index.html يُعدَّل الآن بواسطة تغيير آخر جارٍ،
     وأي رقم محفور في الاختبار سيصير كذباً بعد أوّل تحرير. يُشترط بدلاً منه أن
     يحيل المستند إلى المُخرَجَين القابلين لإعادة التوليد، وأن يصف البنية. */
  ['the authoritative bundle measurement is referenced, not re-typed',
   /bundle_report\.json/],
  ['the authoritative browser measurement is referenced',
   /csp_probe\.json/],
  ['the concrete figures are labelled as a snapshot of a page under edit',
   /snapshot/i],
  ['the per-script inventory shows the application is ONE inline module',
   /the entire application/i],
  ['the page ships no external application script',
   /no external application script|<script src="\/app\//i],
  ['es-module-shims and its version', /es-module-shims/i],
  ['the exact browser versions that lose support if the shim is dropped',
   /16\.4/],
  ['iOS is named explicitly', /iOS/],
  ['Firefox 108 is named', /Firefox[^\n]*108/],
  ['Chrome\\/Edge 89 is named', /(Chrome|Edge)[^\n]*89/],
  ['an explicit recommendation NOT to drop the shim without owning the impact',
   /do NOT drop the shim|Recommendation: keep|not drop the shim/i],
  ['worker-src blob: is attributed to the local pdf.js worker', /pdf\.js|pdfjs/i],
  ['img-src data:/blob: is attributed to WebGL textures and screenshots',
   /(WebGL|texture)[\s\S]{0,400}?(screenshot|toDataURL)|screenshot[\s\S]{0,400}?texture/i],
  ['F-09 is named as the prerequisite', /F-09/],
  ['an ordered migration plan to nonce\\/hash', /nonce/i],
  ['CSP hardening is declared NOT COMPLETE', /NOT COMPLETE/],
  ['F-09 is declared not implemented', /F-09[^\n]*NOT IMPLEMENTED|NOT IMPLEMENTED/]
];
DOC_MUST_SAY.forEach(([label, re]) =>
  chk(DOC_PATH + ' documents: ' + label, re.test(DOC)));
chk(DOC_PATH + ' records the before policy verbatim',
    DOC.indexOf("script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:") >= 0);
chk(DOC_PATH + ' records the after policy including every added directive',
    ['form-action', 'frame-src', 'manifest-src', 'media-src',
     'upgrade-insecure-requests'].every(d => DOC.indexOf(d) >= 0));

console.log('\n== §8 — THE GATE IS NOT VACUOUS (it is run against hostile '
  + 'inputs) ==');
/* حارس لا يسقط أبداً ليس حارساً. نمرّر سياسات معادية عبر المنطق نفسه. */
function gate(cspText, docText) {
  const p = parseCSP(cspText);
  if (!p) return ['no policy'];
  const bad = [];
  const toks = [];
  p.map.forEach((v, k) => v.forEach(t => toks.push([k, t])));
  if (toks.some(([, t]) => /^javascript:/i.test(t))) bad.push('javascript: source');
  if (toks.some(([, t]) => t === '*')) bad.push('wildcard source');
  if (CDN_HOSTS.some(h => p.raw.toLowerCase().indexOf(h) >= 0)) bad.push('CDN host');
  if ((p.map.get('object-src') || []).join(' ') !== "'none'") bad.push('object-src');
  toks.filter(([, t]) => t.indexOf("'unsafe-") === 0).forEach(([, t]) => {
    if (docText.indexOf(t) < 0) bad.push('undeclared ' + t);
  });
  const c = p.map.get('connect-src') || [];
  if (c.length !== 2 || c.indexOf("'self'") < 0) bad.push('connect-src not pinned');
  return bad;
}
const GOOD = 'Content-Security-Policy = "' + CSP.raw + '"';
chk('the gate passes the real policy with the real document',
    gate(GOOD, DOC).length === 0, JSON.stringify(gate(GOOD, DOC)));
[['a javascript: source',
  'Content-Security-Policy = "default-src \'self\'; object-src \'none\'; '
  + 'script-src \'self\' javascript:; connect-src \'self\' https://x.onrender.com"'],
 ['a bare wildcard',
  'Content-Security-Policy = "default-src \'self\'; object-src \'none\'; '
  + 'script-src *; connect-src \'self\' https://x.onrender.com"'],
 ['a CDN host',
  'Content-Security-Policy = "default-src \'self\'; object-src \'none\'; '
  + 'script-src \'self\' https://cdn.jsdelivr.net; connect-src \'self\' '
  + 'https://x.onrender.com"'],
 ['a widened connect-src',
  'Content-Security-Policy = "default-src \'self\'; object-src \'none\'; '
  + 'script-src \'self\'; connect-src \'self\' https://x.onrender.com '
  + 'https://telemetry.example.com"'],
 ['object-src re-opened',
  'Content-Security-Policy = "default-src \'self\'; object-src \'self\'; '
  + 'script-src \'self\'; connect-src \'self\' https://x.onrender.com"']
].forEach(([label, hostile]) =>
  chk('the gate rejects ' + label, gate(hostile, DOC).length > 0));
chk("the gate rejects 'unsafe-inline' when the document does NOT declare it "
    + '(this is what turns a silent weakness into a tracked one)',
    gate(GOOD, 'a document that says nothing').some(
      b => b.indexOf('undeclared') === 0),
    JSON.stringify(gate(GOOD, 'a document that says nothing')));

console.log('\n== §9 — THE REAL-CHROMIUM MEASUREMENT, WHERE IT EXISTS ==');
const PROBE = _np.join(HERE, 'outputs', 'csp_probe.json');
if (!fs.existsSync(PROBE)) {
  console.log('  (no measurement on disk — run: node tests/remediation/'
    + 'csp_browser_probe.js. Nothing is claimed here without it.)');
} else {
  const P = JSON.parse(fs.readFileSync(PROBE, 'utf8'));
  if (P.status !== 'MEASURED') {
    console.log('  measurement present but not performed: ' + P.status
      + ' — ' + P.reason);
    chk('an unperformed measurement is recorded as NOT VERIFIED, never as a '
        + 'pass', String(P.status).indexOf('NOT VERIFIED') === 0);
  } else {
    const cur = P.results.filter(r => r.label === 'CURRENT')[0];
    const hard = P.results.filter(r => r.label === 'HARDENED_TRIAL')[0];
    chk('the measured policy is byte-identical to the deployed policy',
        P.current_policy === CSP.raw);
    chk('the hardened trial policy differs from the deployed one only by '
        + "'unsafe-inline'/'unsafe-eval'",
        P.hardened_trial_policy === CSP.raw.split(';').map(d => d.split(/\s+/)
          .filter(t => t !== "'unsafe-inline'" && t !== "'unsafe-eval'")
          .join(' ').trim()).filter(Boolean).join('; '));
    chk('both policies were actually loaded in a browser',
        !!cur && !!hard && cur.page_loaded && hard.page_loaded);
    console.log('  CURRENT   violations=' + cur.violations_total
      + '  hostile inline executed=' + cur.hostile_inline_executed
      + '  hostile eval executed=' + cur.hostile_eval_executed);
    console.log('  HARDENED  violations=' + hard.violations_total
      + '  by directive=' + JSON.stringify(hard.violations_by_directive));
    /* الحقيقة غير المريحة تُسجَّل بوصفها ضعفاً متعقَّباً، لا نجاحاً. */
    if (cur.hostile_inline_executed || cur.hostile_eval_executed === true) {
      chk('the measured inline/eval execution is recorded as a KNOWN-WEAKNESS '
          + 'line, not swallowed',
          (P.known_weaknesses || []).length > 0
          && (P.known_weaknesses || []).every(w => w.indexOf('KNOWN-WEAKNESS') === 0),
          JSON.stringify((P.known_weaknesses || []).map(w => w.slice(0, 40))));
      (P.known_weaknesses || []).forEach(w => console.log('  ' + w.slice(0, 118)));
    }
    chk('the hardened policy really does block what the deployed one allows '
        + '(this is the evidence the migration plan rests on)',
        hard.hostile_inline_executed === false
        && hard.hostile_eval_executed === false
        && hard.violations_total > cur.violations_total,
        'cur=' + cur.violations_total + ' hard=' + hard.violations_total);
    chk('the measurement records that the application itself stops working '
        + 'under the hardened policy — the honest cost of the migration',
        hard.application_inline_scripts_executed === false);
    chk('the measurement does not claim a rendered frame',
        P.frame_rendered === false);
  }
}

console.log('\n== §10 — THE STATUS IS REPORTED AS INCOMPLETE ==');
const hasUnsafe = CSP.raw.indexOf("'unsafe-inline'") >= 0
  || CSP.raw.indexOf("'unsafe-eval'") >= 0;
chk('while any \'unsafe-*\' source remains, the repository states plainly '
    + 'that CSP hardening is NOT COMPLETE',
    !hasUnsafe || /NOT COMPLETE/.test(DOC));
chk('and states that F-09 is the prerequisite',
    !hasUnsafe || /F-09[\s\S]{0,200}prerequisite|prerequisite[\s\S]{0,200}F-09/i
      .test(DOC));
if (hasUnsafe) {
  console.log('\n  KNOWN-WEAKNESS · CSP-INLINE-EXEC / CSP-EVAL-EXEC — the '
    + "deployed policy still carries 'unsafe-inline' and 'unsafe-eval'. They "
    + 'are documented in ' + DOC_PATH + ' with measured impact and an ordered '
    + 'removal plan. F-11 CSP HARDENING: NOT COMPLETE (blocked on F-09).');
}

console.log('\n──────────────────────────────────────────────');
console.log('CSP: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
