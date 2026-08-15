/* ============================================================================
   F-11 — عقد سياسة المحتوى بعد الإغلاق: لا 'unsafe-*' ولا استثناء غير مبرَّر.

   يُشغَّل هكذا:
     node tests/lib/run.js tests/remediation/test_csp.js      (كما في run_all.sh)
     node tests/remediation/test_csp.js                        (مستقلّاً)

   بعد F-09 صارت public/index.html قشرة بلا شيفرة تطبيق، وبعد F-11 صارت السياسة
   `script-src 'self' 'sha256-…'` وحدها: بصمة واحدة لعنصر داخليّ واحد هو خريطة
   الاستيراد (لا يمكن أن تكون ملفّاً خارجياً بدعم كافٍ عبر المتصفّحات). هذا
   الملفّ لا يقبل السياسة على كلمتها:
     · يعيد حساب بصمة الخريطة من الصفحة المشحونة نفسها ويقارنها بما في الترويسة؛
     · يرفض 'unsafe-inline' و'unsafe-eval' في أي توجيه مهما كان؛
     · يشتقّ أصل الخادم من عقد النشر (render.yaml) لا من السياسة، فلا تُصدّق
       السياسة نفسها؛
     · يمسح public/app/ بحثاً عن أي موضع نداء eval/new Function حقيقيّ، مع
       تمييز معلن بينه وبين مدخلات قوائم الحظر المقتبسة داخل مواصفات JSON؛
     · ويُشغَّل على سياسات معادية مُشتقّة من السياسة الحقيقية (§11) كي لا يكون
       حارساً لا يسقط أبداً.

   القياس الحيّ في متصفّح حقيقي يعيش في ملفّ منفصل:
     node tests/remediation/csp_browser_probe.js
   ويُقارَن مخرجه هنا إن وُجد (§10). لا يُشترط وجوده كي لا يدّعي هذا الملفّ
   قياساً لم يجرِ.
   ========================================================================== */
const fs = require('fs'), _np = require('path'), crypto = require('crypto');
const HERE = __dirname, ROOT = _np.resolve(HERE, '..', '..');
const APPSRC = require(_np.join(ROOT, 'tests', 'lib', 'app_source.js'));

let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
  : (fail++, console.log('  ✗', n, d === undefined ? '' : String(d).slice(0, 300))); };
const rd = rel => fs.readFileSync(_np.join(ROOT, rel), 'utf8');

const TOML = rd('netlify.toml');
const SHELL = APPSRC.shell();          // public/index.html — القشرة وحدها
const APPTEXT = APPSRC.appText();      // كل شيفرة public/app/ موصولة
const MODULES = APPSRC.modules();
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
function parseRaw(raw) {
  const map = new Map(), order = [];
  String(raw).split(';').forEach(part => {
    const toks = part.trim().split(/\s+/).filter(Boolean);
    if (!toks.length) return;
    if (!map.has(toks[0])) map.set(toks[0], toks.slice(1));
    order.push(toks[0]);
  });
  return { raw: String(raw), map, order };
}
function parseCSP(text) {
  const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(text);
  return m ? parseRaw(m[1]) : null;
}

/* ---------------------- بصمة خريطة الاستيراد، محسوبة من الصفحة استقلالاً --- */
function importMapText(shell) {
  const m = /<script type="importmap">([\s\S]*?)<\/script>/.exec(shell);
  return m ? m[1] : null;
}
function sha256b64(s) {
  return 'sha256-' + crypto.createHash('sha256').update(s, 'utf8').digest('base64');
}
const IMPORTMAP = importMapText(SHELL);
const EXPECTED_HASH = IMPORTMAP === null ? null : sha256b64(IMPORTMAP);

/* ---------------------------- أصل الخادم من عقد النشر لا من السياسة ------- */
const svcMatch =
  /(?:^|\n)\s*-\s*type:\s*web[\s\S]{0,200}?\n\s*name:\s*([A-Za-z0-9_-]+)/.exec(RENDER);
const BACKEND_ORIGIN = svcMatch ? 'https://' + svcMatch[1] + '.onrender.com' : null;
const FRONTEND_ORIGIN = (/_DEFAULT_ORIGIN\s*=\s*"([^"]+)"/.exec(API) || [, ''])[1];

/* ══════════════════════════════════════════════════════════════════════════
   المدقّق الواحد. كل قاعدة بنيوية على السياسة تعيش هنا وحدها، فيستعملها
   القسمان: التحقّق من السياسة الحقيقية (§2–§7) وقصف الطفرات المعادية (§11).
   وجود مصدر واحد للقواعد هو ما يجعل §11 دليلاً على §2–§7 لا اختباراً موازياً.
   ════════════════════════════════════════════════════════════════════════ */
const EXPECTED = {
  'default-src': ["'self'"],
  'base-uri': ["'self'"],
  'object-src': ["'none'"],
  'frame-ancestors': ["'none'"],
  'frame-src': ["'none'"],
  'form-action': ["'self'"],
  'style-src': ["'self'"],
  'img-src': ["'self'", 'data:', 'blob:'],
  'font-src': ["'self'"],
  'worker-src': ["'self'"],
  'media-src': ["'self'"],
  'manifest-src': ["'self'"]
};

function auditPolicy(raw, expectedHash, backendOrigin) {
  const bad = [];
  const add = (code, detail) => bad.push({ code, detail: String(detail) });
  if (!raw || !String(raw).trim()) { add('NO_POLICY', ''); return bad; }
  const p = parseRaw(raw);

  /* توجيه واحد لكل اسم */
  if (p.order.length !== new Set(p.order).size) {
    add('DUPLICATE_DIRECTIVE', p.order.join(','));
  }

  /* التوجيهات المطلوبة بقيمها المتوقّعة كمجموعة — أي توسيع أو حذف يسقط */
  Object.keys(EXPECTED).forEach(d => {
    const got = p.map.get(d);
    if (!got) { add('MISSING_DIRECTIVE:' + d, 'absent'); return; }
    const want = EXPECTED[d];
    if (got.length !== want.length || !want.every(t => got.indexOf(t) >= 0)) {
      add('WRONG_VALUE:' + d, got.join(' '));
    }
  });
  if (!p.map.has('connect-src')) add('MISSING_DIRECTIVE:connect-src', 'absent');
  if (!p.map.has('script-src')) add('MISSING_DIRECTIVE:script-src', 'absent');
  if (!p.map.has('upgrade-insecure-requests')
      || p.map.get('upgrade-insecure-requests').length !== 0) {
    add('MISSING_UPGRADE_INSECURE_REQUESTS',
        JSON.stringify(p.map.get('upgrade-insecure-requests') || null));
  }

  const toks = [];
  p.map.forEach((v, k) => v.forEach(t => toks.push([k, t])));

  /* لا 'unsafe-*' في أي توجيه — لا في script-src ولا في style-src ولا غيرهما */
  toks.forEach(([d, t]) => {
    if (t === "'unsafe-inline'") add('UNSAFE_INLINE', d + ' ' + t);
    else if (t === "'unsafe-eval'") add('UNSAFE_EVAL', d + ' ' + t);
    else if (t === "'unsafe-hashes'") add('UNSAFE_HASHES', d + ' ' + t);
    else if (t === "'wasm-unsafe-eval'") add('WASM_UNSAFE_EVAL', d + ' ' + t);
    else if (t.indexOf("'unsafe-") === 0) add('UNSAFE_OTHER', d + ' ' + t);
  });

  /* مصادر خطرة أياً كان توجيهها */
  toks.forEach(([d, t]) => {
    if (/^javascript:/i.test(t)) add('JAVASCRIPT_URL', d + ' ' + t);
    if (t === '*') add('WILDCARD', d + ' ' + t);
    if (t.indexOf('*.') === 0) add('WILDCARD_SUBDOMAIN', d + ' ' + t);
    if (t === 'http:' || /^http:\/\//i.test(t)) add('INSECURE_SCHEME', d + ' ' + t);
    if (t === 'data:' && (d === 'script-src' || d === 'default-src')) {
      add('DATA_IN_SCRIPT_SRC', d + ' ' + t);
    }
    if (t === 'blob:' && (d === 'script-src' || d === 'default-src')) {
      add('BLOB_IN_SCRIPT_SRC', d + ' ' + t);
    }
  });
  if (/javascript:/i.test(String(raw))) {
    add('JAVASCRIPT_URL_IN_RAW_TEXT', 'raw policy text');
  }

  /* شكل script-src: 'self' + بصمة sha256 واحدة، ولا شيء رابع */
  const ss = p.map.get('script-src') || [];
  const hashes = ss.filter(t => /^'sha(256|384|512)-[A-Za-z0-9+/=]+'$/.test(t));
  const others = ss.filter(t => hashes.indexOf(t) < 0);
  if (!(others.length === 1 && others[0] === "'self'")) {
    add('SCRIPT_SRC_SHAPE', "script-src carries sources other than 'self' plus "
      + 'one hash: ' + JSON.stringify(others));
  }
  if (hashes.length !== 1) {
    add('SCRIPT_SRC_HASH_COUNT', hashes.length + ' hash source(s): '
      + JSON.stringify(hashes));
  } else if (expectedHash && hashes[0] !== "'" + expectedHash + "'") {
    add('HASH_MISMATCH', 'policy=' + hashes[0] + ' page=' + "'" + expectedHash + "'");
  }
  if (hashes.length === 1 && !/^'sha256-/.test(hashes[0])) {
    add('HASH_NOT_SHA256', JSON.stringify(hashes));
  }

  /* connect-src مثبَّت على 'self' + أصل الخادم المعلن، ولا شيء غيرهما */
  const c = p.map.get('connect-src') || [];
  if (!(c.length === 2 && c.indexOf("'self'") >= 0
        && backendOrigin && c.indexOf(backendOrigin) >= 0)) {
    add('CONNECT_SRC_NOT_PINNED', c.join(' ') + '  (expected: \'self\' '
      + backendOrigin + ')');
  }
  /* لا أصل بعيد ثانٍ في أي توجيه آخر */
  toks.filter(([, t]) => /^https:\/\//i.test(t)).forEach(([d, t]) => {
    if (!(d === 'connect-src' && t === backendOrigin)) {
      add('EXTRA_REMOTE_ORIGIN', d + ' ' + t);
    }
  });

  /* لا مضيف CDN في أي موضع من نصّ السياسة */
  CDN_HOSTS.forEach(h => {
    if (String(raw).toLowerCase().indexOf(h) >= 0) add('CDN_HOST', h);
  });

  return bad;
}

/* ══════════════════════════════════════════════════════════════════════════ */
console.log('\n== §1 — THE POLICY IS DELIVERED AS A RESPONSE HEADER AND PARSES ==');
const CSP = parseCSP(TOML);
chk('netlify.toml declares a Content-Security-Policy response header', !!CSP);
if (!CSP) { console.log('\nCSP: cannot continue without a policy'); process.exit(1); }
chk('the policy is on the site-wide header block, not a single path',
    /for\s*=\s*["']\/\*["'][\s\S]{0,6000}?Content-Security-Policy/.test(TOML));
chk('no <meta http-equiv="Content-Security-Policy"> shadows the header '
    + '(meta cannot express frame-ancestors and would measure a different '
    + 'policy than the one deployed)',
    !/http-equiv\s*=\s*["']Content-Security-Policy/i.test(SHELL));
chk('exactly one Content-Security-Policy assignment exists in netlify.toml',
    (TOML.match(/Content-Security-Policy\s*=/g) || []).length === 1);
console.log('  policy: ' + CSP.raw);

const FINDINGS = auditPolicy(CSP.raw, EXPECTED_HASH, BACKEND_ORIGIN);
const has = code => FINDINGS.some(f => f.code === code
  || f.code.indexOf(code + ':') === 0);
const why = code => JSON.stringify(FINDINGS.filter(f => f.code === code
  || f.code.indexOf(code + ':') === 0));
const noFinding = (code, label) => chk(label, !has(code), why(code));

console.log('\n== §2 — EVERY REQUIRED DIRECTIVE IS PRESENT WITH THE EXPECTED '
  + 'VALUE ==');
noFinding('DUPLICATE_DIRECTIVE', 'every directive name appears exactly once');
Object.keys(EXPECTED).forEach(d => {
  const got = CSP.map.get(d);
  chk('`' + d + '` is present with exactly ' + JSON.stringify(EXPECTED[d]),
      !FINDINGS.some(f => f.code === 'MISSING_DIRECTIVE:' + d
        || f.code === 'WRONG_VALUE:' + d),
      got ? got.join(' ') : 'MISSING');
});
chk('`connect-src` is present', !has('MISSING_DIRECTIVE:connect-src'));
chk('`script-src` is present', !has('MISSING_DIRECTIVE:script-src'));
noFinding('MISSING_UPGRADE_INSECURE_REQUESTS',
  '`upgrade-insecure-requests` is present (valueless directive)');

console.log("\n== §3 — NO 'unsafe-inline' AND NO 'unsafe-eval', IN ANY "
  + 'DIRECTIVE ==');
/* هذا هو الفرق الجوهري عن السياسة السابقة، ويُفحَص على كل التوجيهات لا على
   script-src وحده: style-src كانت تحمل 'unsafe-inline' وقد سقطت أيضاً. */
noFinding('UNSAFE_INLINE', "no directive carries 'unsafe-inline'");
noFinding('UNSAFE_EVAL', "no directive carries 'unsafe-eval'");
noFinding('UNSAFE_HASHES', "no directive carries 'unsafe-hashes'");
noFinding('WASM_UNSAFE_EVAL', "no directive carries 'wasm-unsafe-eval'");
noFinding('UNSAFE_OTHER', "no other 'unsafe-*' keyword appears anywhere");
chk("the raw policy text contains the substring 'unsafe- zero times",
    CSP.raw.indexOf("'unsafe-") < 0,
    CSP.raw.slice(Math.max(0, CSP.raw.indexOf("'unsafe-") - 40),
      CSP.raw.indexOf("'unsafe-") + 40));

console.log("\n== §4 — script-src IS EXACTLY 'self' PLUS ONE IMPORT-MAP HASH, "
  + 'AND THE HASH IS RECOMPUTED FROM THE PAGE ==');
chk('the shipped page contains exactly one <script type="importmap">',
    (SHELL.match(/<script type="importmap">/g) || []).length === 1);
chk('the import map body was located and hashed independently by this test',
    IMPORTMAP !== null && !!EXPECTED_HASH, EXPECTED_HASH);
console.log('  sha256 of the page import map, computed here: ' + EXPECTED_HASH);
noFinding('SCRIPT_SRC_SHAPE',
  "script-src carries exactly 'self' plus hash sources and nothing else");
noFinding('SCRIPT_SRC_HASH_COUNT', 'script-src carries exactly ONE hash source');
noFinding('HASH_NOT_SHA256', 'that one hash source is a sha256 hash');
noFinding('HASH_MISMATCH',
  'the hash in the deployed policy equals the sha256 of the page import map '
  + '(recomputed here from public/index.html, not copied from the policy)');
noFinding('DATA_IN_SCRIPT_SRC',
  'no `data:` source in script-src or default-src (a data: script is an XSS '
  + 'primitive)');
noFinding('BLOB_IN_SCRIPT_SRC',
  'no `blob:` source in script-src or default-src (the es-module-shims blob '
  + 'worker was the only reason it was ever there)');
/* الملفّ المصاحب الذي يستعمله البناء: يجب أن يوافق الحساب المستقلّ */
const HASHFILE = 'public/app/importmap.sha256';
if (fs.existsSync(_np.join(ROOT, HASHFILE))) {
  chk(HASHFILE + ' agrees with the hash computed here',
      rd(HASHFILE).trim() === EXPECTED_HASH,
      rd(HASHFILE).trim() + ' vs ' + EXPECTED_HASH);
} else {
  console.log('  (' + HASHFILE + ' is absent — the policy hash is still checked '
    + 'against the page directly, so nothing is assumed)');
}
chk('no import map entry points at a remote origin', (function () {
  if (IMPORTMAP === null) return false;
  try {
    const im = JSON.parse(IMPORTMAP);
    return Object.values(im.imports || {}).every(v => String(v).indexOf('/') === 0);
  } catch (e) { return false; }
})());

console.log('\n== §5 — THE SURFACE-REDUCING DIRECTIVES ARE EXACT ==');
[['object-src', "'none'"], ['base-uri', "'self'"], ['frame-ancestors', "'none'"],
 ['frame-src', "'none'"], ['form-action', "'self'"]].forEach(([d, v]) => {
  chk('`' + d + '` is exactly ' + v, (CSP.map.get(d) || []).join(' ') === v,
      (CSP.map.get(d) || []).join(' ') || 'MISSING');
});
chk('frame-ancestors is backed by X-Frame-Options: DENY for old agents',
    /X-Frame-Options\s*=\s*"DENY"/.test(TOML));
noFinding('JAVASCRIPT_URL', 'no `javascript:` source in any directive');
noFinding('JAVASCRIPT_URL_IN_RAW_TEXT',
  'the raw policy text contains no `javascript:` at all');
noFinding('WILDCARD', 'no bare wildcard `*` source in any directive');
noFinding('WILDCARD_SUBDOMAIN', 'no wildcard-subdomain source (`*.`) anywhere');
noFinding('INSECURE_SCHEME',
  'no insecure `http:` scheme source, and no `http://` origin');

console.log('\n== §6 — connect-src PINS EXACTLY THE DECLARED BACKEND ORIGIN ==');
/* الأصل يُشتقّ من عقد النشر لا من السياسة نفسها: خدمة Render اسمها acs-engine
   ⇒ https://acs-engine.onrender.com. لو غُيّر اسم الخدمة ولم تُغيّر السياسة،
   يسقط هذا الفحص — وهو بالضبط الحادث الذي يمنعه. */
chk('render.yaml declares exactly one web service with a name', !!svcMatch,
    svcMatch ? svcMatch[1] : 'no `type: web` + `name:` pair found');
console.log('  backend origin derived from render.yaml: ' + BACKEND_ORIGIN);
const pageBase = (/CONFIGURED_BASE\s*=\s*"([^"]*)"/.exec(APPTEXT) || [, ''])[1]
  .replace(/\/+$/, '');
chk('public/app declares the same origin exactly once',
    (APPTEXT.match(/CONFIGURED_BASE\s*=\s*"/g) || []).length === 1
    && pageBase === BACKEND_ORIGIN,
    'app=' + pageBase + ' render.yaml=' + BACKEND_ORIGIN);
noFinding('CONNECT_SRC_NOT_PINNED',
  "connect-src is exactly ['self', <backend origin>] and nothing else");
chk('the backend CORS allow-list origin was located in acs_understand_api.py',
    !!FRONTEND_ORIGIN, FRONTEND_ORIGIN);
/* الاتجاه المعاكس لا يُخلط: أصل الواجهة (CORS على الخادم) ليس وجهة اتصال. */
chk('that frontend origin is NOT in connect-src — it is what the backend allows '
    + 'to call it, not what the page may call',
    !!FRONTEND_ORIGIN
    && (CSP.map.get('connect-src') || []).indexOf(FRONTEND_ORIGIN) < 0,
    FRONTEND_ORIGIN);
chk('render.yaml ACS_ALLOWED_ORIGINS names the frontend, matching the API '
    + 'default (one origin story, not two)',
    !!FRONTEND_ORIGIN && new RegExp('ACS_ALLOWED_ORIGINS[\\s\\S]{0,160}?'
      + FRONTEND_ORIGIN.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(RENDER));
noFinding('EXTRA_REMOTE_ORIGIN',
  'no second remote origin was added to any directive');

console.log('\n== §7 — NO CDN HOST IN THE POLICY, AND NO RUNTIME CDN URL OR '
  + 'EXECUTABLE INLINE SCRIPT IN THE SHIPPED PAGE ==');
noFinding('CDN_HOST', 'no directive allows any known CDN host');
CDN_HOSTS.forEach(h => {
  const lines = SHELL.split('\n').map((l, i) => [i + 1, l])
    .filter(([, l]) => l.indexOf(h) >= 0);
  chk('public/index.html carries no reference to ' + h, lines.length === 0,
      lines.slice(0, 2).map(([i, l]) => i + ':' + l.trim().slice(0, 90)).join(' | '));
});
const cdnInApp = [];
CDN_HOSTS.forEach(h => {
  Object.keys(MODULES).forEach(f => {
    if (MODULES[f].indexOf(h) >= 0) cdnInApp.push(f + ' → ' + h);
  });
});
chk('no module under public/app/ carries a runtime CDN URL',
    cdnInApp.length === 0, cdnInApp.slice(0, 4).join(' | '));
chk('no <script src="http…"> in the shipped page',
    !/<script[^>]+src\s*=\s*["']https?:\/\//i.test(SHELL));
chk('no <link href="http…"> in the shipped page',
    !/<link[^>]+href\s*=\s*["']https?:\/\//i.test(SHELL));
chk('es-module-shims is gone from the shipped page as a loadable asset (it was '
    + "the only reason 'unsafe-eval' and blob: ever existed in script-src)",
    !/es-module-shims[^\s"'<>]*\.js/i.test(SHELL),
    (/[^\n]*es-module-shims[^\n]*\.js[^\n]*/i.exec(SHELL) || [''])[0].slice(0, 140));

/* الصفحة كقشرة: كل <script> إمّا خارجيّ بمسار محلّي، وإمّا خريطة الاستيراد. */
const SCRIPT_TAGS = SHELL.match(/<script\b[^>]*>[\s\S]*?<\/script>/gi) || [];
const inlineExecutable = SCRIPT_TAGS.filter(t => {
  const open = /^<script\b[^>]*>/i.exec(t)[0];
  if (/\bsrc\s*=/i.test(open)) return false;                       // خارجيّ
  if (/type\s*=\s*["']importmap["']/i.test(open)) return false;    // خريطة
  return /<script\b[^>]*>([\s\S]*?)<\/script>/i.exec(t)[1].trim().length > 0;
});
chk('the shipped page carries ZERO executable inline <script> blocks (the only '
    + 'inline element left is the import map, pinned by hash)',
    inlineExecutable.length === 0,
    inlineExecutable.slice(0, 2).map(s => s.slice(0, 140)).join(' | '));
chk('every <script src> in the shipped page is a local absolute path',
    SCRIPT_TAGS.every(t => {
      const m = /\bsrc\s*=\s*["']([^"']+)["']/i.exec(t);
      return !m || m[1].charAt(0) === '/';
    }));
/* سمة معالج الحدث المضمَّن هي شيفرة مضمَّنة أيضاً، ويحجبها script-src-attr.
   القائمة أدناه أسماء معالِجات حقيقية لا نمط `on\w+` الفضفاض، حتى لا تُتَّهم
   سمة بيانات مثل data-tone="…" ظلماً. تركُ معالج مضمَّن في الصفحة تحت هذه
   السياسة يعني زرّاً ميّتاً لا يفعل شيئاً — وقد قِيس ذلك في Chromium:
   attacks.inline_event_handler = BLOCKED في csp_probe.json. */
const HANDLERS = ['onclick', 'ondblclick', 'onmousedown', 'onmouseup', 'onmouseover',
  'onmouseout', 'onmousemove', 'onmouseenter', 'onmouseleave', 'onwheel',
  'oncontextmenu', 'onkeydown', 'onkeyup', 'onkeypress', 'onfocus', 'onblur',
  'onchange', 'oninput', 'onsubmit', 'onreset', 'oninvalid', 'onselect',
  'onload', 'onunload', 'onbeforeunload', 'onerror', 'onabort', 'onresize',
  'onscroll', 'onhashchange', 'onpopstate', 'onstorage', 'onmessage',
  'ontouchstart', 'ontouchend', 'ontouchmove', 'ontouchcancel',
  'onpointerdown', 'onpointerup', 'onpointermove', 'onpointercancel',
  'ondragstart', 'ondragend', 'ondragover', 'ondrop', 'oncopy', 'oncut',
  'onpaste', 'onplay', 'onpause', 'onended', 'ontoggle', 'onanimationend',
  'ontransitionend'];
const handlerHits = [];
SHELL.split('\n').forEach((line, i) => {
  HANDLERS.forEach(h => {
    const re = new RegExp('\\s' + h + '\\s*=\\s*["\'][^"\']*["\']', 'i');
    const m = re.exec(line);
    if (m) handlerHits.push('line ' + (i + 1) + ': ' + m[0].trim().slice(0, 90));
  });
});
chk('the shipped page carries ZERO inline event-handler attributes (on…="…") — '
    + "under `script-src 'self' 'sha256-…'` such a handler NEVER runs, so any "
    + 'control that relies on one is silently dead',
    handlerHits.length === 0, handlerHits.slice(0, 4).join(' | '));
chk("the shipped page carries no <style> block (style-src is 'self')",
    !/<style\b/i.test(SHELL));
chk('the shipped page carries no style="…" attribute',
    !/\sstyle\s*=\s*["']/i.test(SHELL),
    (/[^\n]*\sstyle\s*=\s*["'][^\n]*/i.exec(SHELL) || [''])[0].trim().slice(0, 140));

console.log('\n== §8 — public/app/ CONTAINS NO eval( / new Function( CALL SITE ==');
/* التمييز المعلن: مواصفات JSON المحقونة في وحدات `generated/*` تحمل قوائم حظر
   فيها السلاسل المقتبسة "eval(" و"new Function". مسحها حرفيّاً يجعل قائمة
   الحظر تُدين نفسها. القاعدة هي نفسها المستعملة في tests/phase6/test_security.js
   بصياغة أدقّ: يُستبعَد الموضع إذا كان الحرف السابق مباشرةً علامة اقتباس
   (' أو ") — أي أنّه مدخل قائمة حظر مقتبس لا نداء. وكل موضع مستبعَد يُطبَع
   ويُشترط أن يقع داخل بناء قائمة حظر/مواصفة معروف، فلا يمرّ نداء حقيقي تحت
   غطاء الاستثناء. */
const DENY_TOKEN_SPELLINGS = ['eval(', 'exec(', 'new Function(', 'new Function'];
function scanDynamicExec(src) {
  const real = [], quoted = [];
  const re = /\beval\s*\(|\bnew\s+Function\s*\(/g;
  let m;
  while ((m = re.exec(src))) {
    const prev = m.index > 0 ? src.charAt(m.index - 1) : '';
    const line = src.slice(0, m.index).split('\n').length;
    const ctx = src.slice(Math.max(0, m.index - 90), m.index + 40).replace(/\n/g, ' ');
    /* نافذة أوسع تُستعمل لإثبات السياق وحدها، وتبقى ctx القصيرة للعرض. */
    const wide = src.slice(Math.max(0, m.index - 700), m.index + 200)
      .replace(/\n/g, ' ');
    if (prev !== "'" && prev !== '"') { real.push({ line, ctx, wide }); continue; }
    /* الموضع مسبوق باقتباس ⇒ مرشَّح لكونه مدخل قائمة حظر. لا يُقبل الاستثناء
       على هذا وحده: يُستخرَج النصّ المقتبس كاملاً ويُشترط أن يكون حرفيّاً أحد
       تهجئات الرمز المحظور، وأن يكون عنصراً في قائمة (يسبقه `[` أو `,`).
       نداء حقيقي لا يمكن أن يستوفي الشرطين. */
    const open = m.index - 1, q = prev;
    const close = src.indexOf(q, m.index);
    const literal = close < 0 ? null : src.slice(open + 1, close);
    const beforeOpen = src.slice(0, open).replace(/\s+$/, '').slice(-1);
    const isDenyEntry = literal !== null
      && DENY_TOKEN_SPELLINGS.indexOf(literal) >= 0
      && (beforeOpen === '[' || beforeOpen === ',');
    if (isDenyEntry) quoted.push({ line, ctx, wide, literal: literal });
    else real.push({ line, ctx, wide });
  }
  return { real, quoted };
}
const realSites = [], quotedSites = [];
Object.keys(MODULES).forEach(f => {
  const r = scanDynamicExec(MODULES[f]);
  r.real.forEach(x => realSites.push(f + ':' + x.line + ' :: ' + x.ctx));
  r.quoted.forEach(x => quotedSites.push({ file: f, line: x.line, ctx: x.ctx,
    wide: x.wide, literal: x.literal }));
});
chk('no module under public/app/ contains a real eval( or new Function( call site',
    realSites.length === 0, realSites.slice(0, 3).join(' | '));
console.log('  quoted deny-list occurrences deliberately excluded: '
  + quotedSites.length + '  ['
  + quotedSites.map(q => q.file + ':' + q.line).join(', ') + ']');
chk('every excluded occurrence is literally one of '
    + JSON.stringify(DENY_TOKEN_SPELLINGS) + ' written as a quoted element of a '
    + 'list — the exclusion is proven per occurrence, not assumed wholesale',
    quotedSites.every(q => DENY_TOKEN_SPELLINGS.indexOf(q.literal) >= 0),
    JSON.stringify(quotedSites.filter(q =>
      DENY_TOKEN_SPELLINGS.indexOf(q.literal) < 0).slice(0, 2)));
const DENYLIST_CONTEXT =
  /forbidden|unsafe_pattern|FORBIDDEN|denied|blocked|_SPEC\s*=|"schema"\s*:/;
chk('and each of those really sits in a deny-list / embedded JSON spec context',
    quotedSites.every(q => DENYLIST_CONTEXT.test(q.wide)),
    JSON.stringify(quotedSites.filter(q => !DENYLIST_CONTEXT.test(q.wide))
      .map(q => q.file + ':' + q.line).slice(0, 4)));
chk('the dynamic-execution scan is not vacuous — it flags a real call site',
    scanDynamicExec('x = eval("1+1");').real.length === 1
    && scanDynamicExec('const f = new Function("return 1");').real.length === 1);
chk('…and it does exclude a quoted deny-list entry, and only a quoted one',
    scanDynamicExec('const D = ["<script","eval(","new Function("];').real.length === 0
    && scanDynamicExec('const D = ["eval("]; y = eval("2");').real.length === 1);
chk('…and a quoted string that is NOT a bare deny-list entry is still counted '
    + 'as a call site (the exclusion cannot be widened by quoting)',
    scanDynamicExec('const s = "x = eval(1)";').real.length === 1);
chk('no module assigns a javascript: URL',
    !/=\s*['"]javascript:/i.test(APPTEXT));
chk('no module calls document.write', !/document\.write\s*\(/.test(APPTEXT));
chk('no module loads es-module-shims',
    !/es-module-shims/i.test(APPTEXT));

console.log('\n== §9 — THE HARDENING RECORD SAYS WHAT WAS DONE AND WHAT IS '
  + 'STILL EXCEPTED ==');
chk(DOC_PATH + ' exists', DOC.length > 0);
chk(DOC_PATH + ' is a real audit, not a stub', DOC.length > 4000, String(DOC.length));
const _cspEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const DOC_MUST_SAY = [
  ['a Before section', /^##[^\n]*\bBefore\b/mi],
  ['the OLD policy verbatim',
   /script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:/],
  ['the old measured numbers (62 violations under the hardened trial)', /\b62\b/],
  ['the old measured hostile inline / eval / new Function EXECUTED',
   /EXECUTED/],
  ['an After section', /^##[^\n]*\bAfter\b/mi],
  ['the NEW policy verbatim', new RegExp(_cspEsc(CSP.raw))],
  ['an Evidence section', /^##[^\n]*\bEvidence\b/mi],
  ['the probe file path', /tests\/remediation\/csp_browser_probe\.js/],
  ['the probe output path', /csp_probe\.json/],
  ['the page.evaluate methodology trap', /page\.evaluate/],
  ['CDP named as the reason page.evaluate bypasses CSP', /CDP/],
  ['the exact Chromium build used',
   /Chromium[^\n]{0,24}\b1[0-9]{2}\.[0-9]+\.[0-9]+\.[0-9]+\b/],
  ['a Compatibility section', /^##[^\n]*\bCompatibility\b/mi],
  ['the es-module-shims removal', /es-module-shims/i],
  ['Chrome/Edge 89 named', /(Chrome|Edge)[^\n]*\b89\b/],
  ['Firefox 108 named', /Firefox[^\n]*\b108\b/],
  ['Safari/iOS 16.4 named', /16\.4/],
  ['iOS named explicitly', /iOS/],
  ['the lost population is stated in VERSIONS and market share is declared '
   + 'NOT VERIFIED offline',
   /market share[\s\S]{0,400}?NOT VERIFIED|NOT VERIFIED[\s\S]{0,400}?market share/i],
  ["the security benefit paid for it — 'unsafe-eval' was borne by 100% of users",
   /100\s*%|100 per cent/],
  ['the alternative that restores old browsers WITHOUT unsafe-eval (rewriting '
   + 'the bare `three` specifiers at build time)',
   /bare[^\n]*specifier|specifier[^\n]*rewrit/i],
  ['that alternative is declared NOT IMPLEMENTED and NOT TESTED here',
   /NOT IMPLEMENTED[\s\S]{0,200}?NOT TESTED|NOT TESTED[\s\S]{0,200}?NOT IMPLEMENTED/],
  ['and why (no vendored tree, no network)', /no vendored tree|no network/i],
  ['a Remaining-exceptions section', /Remaining exception/i],
  ['img-src data: blob: attributed to textures / screenshots / user imports',
   /createObjectURL|texture|screenshot/i],
  ['the single import-map hash listed as an exception', /import map|import-map/i],
  ["worker-src 'self' and the pdf.js blob-worker note", /pdf\.js|pdfjs/i],
  ['the exact single directive to add if pdf.js needs a blob worker',
   /worker-src 'self' blob:/],
  ['a Status line', /Status:\s*(CLOSED|OPEN)/]
];
DOC_MUST_SAY.forEach(([label, re]) =>
  chk(DOC_PATH + ' documents: ' + label, re.test(DOC)));
/* الاتّجاهان محروسان: لا يدّعي المستند عدم الاكتمال وسياسته نظيفة، ولا يدّعي
   الإغلاق وفيها 'unsafe-*'. */
const policyIsClean = CSP.raw.indexOf("'unsafe-") < 0;
chk('the document does not still declare the hardening NOT COMPLETE while the '
    + "policy carries no 'unsafe-*' source",
    !policyIsClean || !/NOT COMPLETE/.test(DOC));
chk("the document does not claim Status: CLOSED while an 'unsafe-*' source "
    + 'remains in the policy',
    policyIsClean || !/Status:\s*CLOSED/.test(DOC));

console.log('\n== §10 — THE REAL-CHROMIUM MEASUREMENT, WHERE IT EXISTS ==');
const PROBE = _np.join(HERE, 'outputs', 'csp_probe.json');
const ATTACK_KEYS = ['inline_script', 'eval', 'function_constructor',
  'javascript_url', 'external_script', 'inline_event_handler',
  'data_url_script', 'blob_script'];
if (!fs.existsSync(PROBE)) {
  console.log('  (no measurement on disk — run: node tests/remediation/'
    + 'csp_browser_probe.js. Nothing is claimed here without it.)');
} else {
  const P = JSON.parse(fs.readFileSync(PROBE, 'utf8'));
  if (P.status !== 'MEASURED') {
    console.log('  measurement present but not performed: ' + P.status
      + ' — ' + P.reason);
    chk('an unperformed measurement is recorded as NOT VERIFIED, never as a pass',
        String(P.status).indexOf('NOT VERIFIED') === 0);
  } else {
    chk('the measured policy is byte-identical to the deployed policy',
        P.policy === CSP.raw);
    chk('the probe measured all eight attack classes',
        ATTACK_KEYS.every(k => typeof (P.attacks || {})[k] === 'string'),
        JSON.stringify(Object.keys(P.attacks || {})));
    ATTACK_KEYS.forEach(k => chk('measured: ' + k + ' is BLOCKED',
      (P.attacks || {})[k] === 'BLOCKED', (P.attacks || {})[k]));
    chk('a normal boot produced ZERO unexpected CSP violations',
        P.unexpected_csp_violations === 0, String(P.unexpected_csp_violations));
    chk('the boot brought up window.ACS_API and window.ACS',
        !!(P.boot && P.boot.acs_api_present && P.boot.acs_present));
    chk('the import map was accepted by its hash (the bare specifier `three` '
        + 'really resolved through it)',
        !!(P.boot && P.boot.import_map_accepted_by_hash));
    chk('element.style.<prop> writes still work (CSSOM is not governed by '
        + 'style-src — measured, not assumed)',
        (P.style || {}).cssom_property_write === 'ALLOWED',
        (P.style || {}).cssom_property_write);
    chk('setAttribute("style", …) is blocked by style-src',
        (P.style || {}).style_attribute === 'BLOCKED',
        (P.style || {}).style_attribute);
    chk('the probe records concrete violation detail (directive, blocked URI, '
        + 'source file, line) rather than a bare count',
        Array.isArray(P.violations) && P.violations.length > 0
        && P.violations.every(v => 'violatedDirective' in v && 'blockedURI' in v
          && 'sourceFile' in v && 'lineNumber' in v),
        String((P.violations || []).length));
    chk('the probe does not claim a rendered frame',
        !!(P.environment && P.environment.rendering_verified === false));
    chk('the TEST-ONLY Three.js stub is declared, and lives outside public/',
        !!(P.environment && P.environment.three_js_stub)
        && (!P.environment.three_js_stub.used
            || (/TEST-ONLY/.test(P.environment.three_js_stub.label)
                && String(P.environment.three_js_stub.location)
                  .indexOf(_np.join(ROOT, 'public')) !== 0)));
    console.log('  chromium: ' + (P.environment || {}).chromium);
    console.log('  attacks : ' + JSON.stringify(P.attacks));
    console.log('  boot violations: ' + P.unexpected_csp_violations
      + '   total recorded: ' + (P.violations || []).length);
  }
}

console.log('\n== §11 — THE GATE IS NOT VACUOUS (mutation testing on the real '
  + 'policy) ==');
/* حارس لا يسقط أبداً ليس حارساً. كل طفرة أدناه مشتقّة من السياسة الحقيقية
   بتغيير واحد، وكلّها يجب أن يمسكها المدقّق نفسه المستعمل في §2–§7. */
const swap = (raw, from, to) => raw.replace(from, to);
const MUTANTS = [
  ["'unsafe-inline' restored in script-src",
   r => swap(r, "script-src 'self'", "script-src 'self' 'unsafe-inline'")],
  ["'unsafe-eval' restored in script-src",
   r => swap(r, "script-src 'self'", "script-src 'self' 'unsafe-eval'")],
  ["'unsafe-inline' restored in style-src",
   r => swap(r, "style-src 'self'", "style-src 'self' 'unsafe-inline'")],
  ["'unsafe-hashes' smuggled into script-src",
   r => swap(r, "script-src 'self'", "script-src 'self' 'unsafe-hashes'")],
  ["'wasm-unsafe-eval' smuggled into script-src",
   r => swap(r, "script-src 'self'", "script-src 'self' 'wasm-unsafe-eval'")],
  ['a second script hash added',
   r => r.replace(/('sha256-[^']*')/,
     "$1 'sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='")],
  ['the import-map hash altered by one character',
   r => r.replace(/'sha256-(.)/, (m0, c) => "'sha256-" + (c === 'k' ? 'j' : 'k'))],
  ['the import-map hash removed entirely',
   r => r.replace(/ 'sha256-[^']*'/, '')],
  ['blob: added back to script-src',
   r => swap(r, "script-src 'self'", "script-src 'self' blob:")],
  ['data: added to script-src',
   r => swap(r, "script-src 'self'", "script-src 'self' data:")],
  ['a javascript: source added',
   r => swap(r, "script-src 'self'", "script-src 'self' javascript:")],
  ['a bare wildcard in script-src',
   r => swap(r, "script-src 'self'", 'script-src *')],
  ['a wildcard subdomain in connect-src',
   r => swap(r, 'https://acs-engine.onrender.com', '*.onrender.com')],
  ['a CDN host added to script-src',
   r => swap(r, "script-src 'self'", "script-src 'self' https://cdn.jsdelivr.net")],
  ['connect-src widened with a telemetry origin',
   r => swap(r, "connect-src 'self' https://acs-engine.onrender.com",
     "connect-src 'self' https://acs-engine.onrender.com "
     + 'https://telemetry.example.com')],
  ["connect-src stripped down to 'self' (the backend origin dropped)",
   r => swap(r, "connect-src 'self' https://acs-engine.onrender.com",
     "connect-src 'self'")],
  ['connect-src pointed at the WRONG render service',
   r => swap(r, 'https://acs-engine.onrender.com', 'https://acs-other.onrender.com')],
  ['an http:// origin added to img-src',
   r => swap(r, "img-src 'self' data: blob:",
     "img-src 'self' data: blob: http://tracker.example.com")],
  ["object-src re-opened to 'self'",
   r => swap(r, "object-src 'none'", "object-src 'self'")],
  ['base-uri widened to *', r => swap(r, "base-uri 'self'", 'base-uri *')],
  ["frame-ancestors relaxed to 'self'",
   r => swap(r, "frame-ancestors 'none'", "frame-ancestors 'self'")],
  ["frame-src re-opened to 'self'",
   r => swap(r, "frame-src 'none'", "frame-src 'self'")],
  ['form-action opened to any origin',
   r => swap(r, "form-action 'self'", 'form-action *')],
  ['upgrade-insecure-requests removed',
   r => r.replace('; upgrade-insecure-requests', '')],
  ['style-src removed entirely', r => r.replace("style-src 'self'; ", '')],
  ['worker-src widened with blob:',
   r => swap(r, "worker-src 'self'", "worker-src 'self' blob:")],
  ['font-src widened with data:',
   r => swap(r, "font-src 'self'", "font-src 'self' data:")],
  ['default-src widened to *', r => swap(r, "default-src 'self'", 'default-src *')],
  ['a duplicated script-src directive appended',
   r => r + "; script-src 'self' 'unsafe-inline'"],
  ['an empty policy', () => '']
];
chk('the auditor passes the real, unmutated policy with ZERO findings',
    FINDINGS.length === 0, JSON.stringify(FINDINGS));
let caught = 0;
const missed = [];
MUTANTS.forEach(([label, fn]) => {
  const raw = fn(CSP.raw);
  if (raw === CSP.raw) { missed.push(label + '  (the mutation did not apply)'); return; }
  if (auditPolicy(raw, EXPECTED_HASH, BACKEND_ORIGIN).length > 0) caught++;
  else missed.push(label);
});
chk('every hostile mutant of the real policy is rejected (' + caught + '/'
    + MUTANTS.length + ' caught)', caught === MUTANTS.length,
    'missed: ' + JSON.stringify(missed));
console.log('  hostile policy mutants caught: ' + caught + ' / ' + MUTANTS.length);
/* والاتّجاه المعاكس: تغيير حميد لا يجوز أن يسقط، وإلّا كان الفحص مقارنة نصّية
   تمنع أي صيانة بدل أن تحرس معنىً. */
const BENIGN = [
  ['img-src source order swapped',
   CSP.raw.replace("img-src 'self' data: blob:", "img-src 'self' blob: data:")],
  ['directive order rotated', CSP.raw.split('; ').reverse().join('; ')],
  ['extra whitespace between directives', CSP.raw.replace(/; /g, ';   ')]
];
BENIGN.forEach(([label, raw]) => {
  const f = auditPolicy(raw, EXPECTED_HASH, BACKEND_ORIGIN);
  chk('a benign rewrite still passes: ' + label, f.length === 0, JSON.stringify(f));
});

console.log('\n== §12 — STATUS ==');
if (policyIsClean) {
  console.log("  the deployed policy carries no 'unsafe-*' source, no wildcard, "
    + 'no CDN host and no blob:/data: script source.');
} else {
  console.log("  KNOWN-WEAKNESS · the deployed policy still carries an 'unsafe-*' "
    + 'source. F-11 CSP HARDENING: NOT COMPLETE.');
}

console.log('\n──────────────────────────────────────────────');
console.log('CSP: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
