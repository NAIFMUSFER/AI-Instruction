/* ============================================================================
   إقلاع الصفحة + ظهور النموذج فعلياً — علاج الشاشة السوداء (§6/§9/§10).

   usage:
     node tests/deploy/verify_page_boot.js                 # يخدم public/ محلياً
     node tests/deploy/verify_page_boot.js <https://url>   # ضد النشر الحقيقي

   يفصل نتيجتين لا تُخلطان:
     BOOT         — الصفحة حُمِّلت وسكربت الوحدة نُفِّذ وTHREE استُورد ومحرّك
                    العرض حيّ.
     VISUAL MODEL — نموذج قانوني محدّد حُمِّل ورُسم فعلاً: شبكات مرئية،
                    نداءات رسم، مثلّثات، النموذج داخل هرم الرؤية، وبكسلات
                    نافذة العرض ليست سوداء.

   «أقلعت الصفحة» لم تعد تعني «ظهر النموذج». هذا بالضبط ما سمح للعطل
   الإنتاجي بالمرور: مشهد فارغ فيه قبّة سماء أعطى حدوداً «صالحة»، ومقياس
   حجم PNG أعطى «غير أسود» من بكسلات الواجهة.

   بلا Three.js مُعبَّأ محلياً وبلا وصول للنشر: توقف صريح exit 2 —
   NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED. لا نجاح مزيَّف أبداً.
   ========================================================================== */
const fs = require('fs'), path = require('path'), http = require('http');
const HERE = __dirname, ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const PX = require(path.join(HERE, 'lib_viewport_pixels.js'));
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js):
   كان هنا احتياطٌ يدويّ مكرَّر — launch() ثم launch({executablePath:'/opt/…'})
   — يخبز مسار صورة هذا الصندوق ويكرّر قراراً موضعه ملفّ واحد. */
const PW = require(path.join(ROOT, 'tools', 'pw_chromium.js'));
const TARGET = process.argv[2] || null;

/* هوية المِرقاب: النسخة القديمة كانت تطبع «PAGE BOOT: N passed» ولا تفرّق
   بين صفحة أقلعت ونموذج ظهر. طباعة الهوية تجعل تشغيل نسخة قديمة مرئياً
   فوراً في أي سجلّ، وحارس التكامل يرفض بقاء الصيغة القديمة في الشجرة. */
const HARNESS_VERSION = 'viewport-safety/1.0.0';
console.log('HARNESS: verify_page_boot ' + HARNESS_VERSION
  + ' (reports BOOT and VISUAL MODEL separately)');

const BOOT = [], VISUAL = [];
const rec = (bucket, n, c, d) => {
  bucket.push({ name: n, ok: !!c, detail: d === undefined ? '' : String(d) });
  console.log('  ' + (c ? '✓' : '✗') + ' ' + n
    + (c || d === undefined ? '' : '  ' + String(d).slice(0, 160)));
};
const boot = (n, c, d) => rec(BOOT, n, c, d);
const visual = (n, c, d) => rec(VISUAL, n, c, d);

const RESOLUTIONS = [[1920, 1080], [1440, 900], [1280, 800]];

/* F-11 — السياسة الإنتاجية تُقرأ من netlify.toml وتُبَثّ رأساً حقيقياً هنا.
   قياس الإقلاع بلا سياسة كان يقيس بيئةً لا وجود لها: ما يمرّ في مِرقاب بلا
   رؤوس قد يُحجَب في الإنتاج، وهذا بالضبط شكل «أقلعت عندي ولم تُقلع هناك». */
function productionCSP() {
  try {
    const nt = fs.readFileSync(path.join(ROOT, 'netlify.toml'), 'utf8');
    const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
    return m ? m[1] : '';
  } catch (e) { return ''; }
}

function serve() {
  /* F-09 — الصفحة صارت قشرة تحمّل وحدات ES: نوع المحتوى ليس تفصيلاً تجميلياً،
     فالمتصفّح يرفض type="module" بأي نوع غير جافاسكربت، وnosniff يجعل ذلك
     صريحاً كما في الإنتاج بدل أن ينقذنا التخمين. */
  const MIME = { '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json', '.png': 'image/png',
    '.svg': 'image/svg+xml', '.txt': 'text/plain', '.xml': 'application/xml' };
  const CSP = productionCSP();
  return new Promise(res => {
    const srv = http.createServer((rq, rs) => {
      const u = decodeURIComponent(rq.url.split('?')[0]);
      const p = path.normalize(path.join(PUB, u === '/' ? 'index.html' : u));
      if (!p.startsWith(PUB) || !fs.existsSync(p)
        || fs.statSync(p).isDirectory()) { rs.writeHead(404); rs.end(); return; }
      const h = { 'Content-Type':
        MIME[path.extname(p)] || 'application/octet-stream',
        'X-Content-Type-Options': 'nosniff' };
      if (CSP) h['Content-Security-Policy'] = CSP;
      rs.writeHead(200, h);
      fs.createReadStream(p).pipe(rs);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

/* المصدر الوحيد الذي يعرف تخطيط الواجهة بعد F-09 — لا قائمة وحدات ثانية
   تُكتب هنا وتتقادم في أوّل إضافة. */
const APPSRC = require(path.join(ROOT, 'tests', 'lib', 'app_source.js'));

function fixtures() {
  const base = JSON.parse(fs.readFileSync(path.join(ROOT, 'tests', 'phase3',
    'fixtures', 'base_fixtures.json'), 'utf8'));
  const out = [['villa_glazed', base.villa_glazed || base.villa],
               ['warehouse', base.warehouse]];
  if (base.apartment6 || base.apartment) {
    out.push(['apartment_6_level', base.apartment6 || base.apartment]);
  }
  /* §18 — النموذج المولَّد الكبير، وصورته ومعه إحداثيّة شاردة واحدة.
     الثاني هو إعادة إنتاج الشاشة السوداء المُبلَّغ عنها: النموذج نفسه تماماً
     زائد نقطة عند x=99999 — فإن مرّ الأول وسقط الثاني قبل العلاج، فالسبب هو
     تلوّث الحدود لا حجم النموذج. */
  const dir = path.join(ROOT, 'tests', 'phase9_2', 'fixtures');
  for (const [label, file] of [
    ['live_large_generated', 'live_large_generated.json'],
    ['live_large_generated_outlier', 'live_large_generated_outlier.json']]) {
    const fp = path.join(dir, file);
    if (fs.existsSync(fp)) out.push([label, JSON.parse(fs.readFileSync(fp, 'utf8'))]);
  }
  return out;
}

function notVerified(why) {
  console.log('\nBOOT: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('VISUAL MODEL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  reason: ' + why);
  console.log('  no pixel was rendered here and none is claimed. Run this '
    + 'file on a networked machine (sh tools/vendor.sh) or against the '
    + 'deployed URL.');
  process.exit(2);
}

(async () => {
  if (!TARGET) {
    const three = path.join(PUB, 'vendor', 'three@0.160.0', 'build',
      'three.module.js');
    if (!fs.existsSync(three) || fs.statSync(three).size < 100000)
      notVerified('vendored Three.js is absent from public/vendor');
  }
  try { require('playwright'); }
  catch (e) { notVerified('playwright is not installed'); }

  const srv = TARGET ? null : await serve();
  const base = TARGET
    || ('http://127.0.0.1:' + srv.address().port + '/index.html');
  /* متصفّح غائب ليس فشلاً في المنتَج: يُعلَن NOT VERIFIED ويخرج بالرمز 2،
     ولا يُحسَب نجاحاً بحال. المسار البديل هو نفسه الذي تستعمله بقيّة المراقب. */
  let b = null;
  try { b = await PW.launch(); }
  catch (e1) {
    if (srv) srv.close();
    notVerified('chromium could not be launched: '
      + String(e1.message).split('\n')[0].slice(0, 160));
  }
  const pg = await b.newPage({ viewport: { width: RESOLUTIONS[0][0],
    height: RESOLUTIONS[0][1] } });
  const errs = [], bad = [], served = new Set();
  pg.on('pageerror', e => errs.push(String(e.message).slice(0, 200)));
  pg.on('response', r => {
    if (r.status() >= 400)
      bad.push('HTTP ' + r.status() + ' ' + r.url().slice(0, 110));
    else served.add(new URL(r.url()).pathname);
  });
  /* F-11 — كل خرق للسياسة يُلتقط من الصفحة نفسها لا من سجلّ الكونسول:
     الخرق حدثٌ في الوثيقة، والاعتماد على نصّ رسالة الكونسول هشّ. */
  await pg.addInitScript(() => {
    window.__CSPV = [];
    document.addEventListener('securitypolicyviolation', e =>
      window.__CSPV.push(e.violatedDirective + ' ' + (e.blockedURI || '')
        + ' ' + (e.sourceFile || '')));
  });

  const specContract = (function(){
    try { return JSON.parse(fs.readFileSync(path.join(ROOT, 'acs_pbr.json'),
      'utf8')).viewport_contract_version; } catch (e) { return null; } })();
  console.log('\n== BOOT ==');
  boot('the harness and the shipped specification declare the same '
    + 'viewport contract', specContract === HARNESS_VERSION,
    'harness=' + HARNESS_VERSION + ' spec=' + specContract);
  try { await pg.goto(base, { waitUntil: 'load', timeout: 90000 }); }
  catch (e) { await b.close(); if (srv) srv.close();
    notVerified('the target could not be loaded: '
      + String(e.message).slice(0, 120)); }
  boot('the page loaded', true);

  /* ── F-09/F-11 — الصفحة قشرة، والتطبيق وحدات: يُقاس ذلك قبل أي شيء ─────
     «أقلعت الصفحة» بعد التفكيك تعني: القشرة وصلت، والسكربتات الكلاسيكية
     عملت، وورقة الأنماط طُبِّقت، ورسم الوحدات حُمِّل كلّه — بلا خرق سياسة
     واحد. سقوط أيٍّ من هذه يعطي صفحةً «تحمّلت» ولا تعمل. */
  const shape = await pg.evaluate(() => ({
    inline_scripts: Array.from(document.querySelectorAll('script'))
      .filter(s => !s.src).map(s => s.type || 'text/javascript'),
    module_entries: Array.from(document.querySelectorAll('script[type=module]'))
      .map(s => s.getAttribute('src')),
    classic_boot: Array.from(document.querySelectorAll('script[src]'))
      .map(s => s.getAttribute('src')).filter(x => /^\/app\/boot\//.test(x)),
    stylesheets: document.styleSheets.length,
    css_rules: (function () { let n = 0;
      for (const s of document.styleSheets) {
        try { n += s.cssRules.length; } catch (e) { } } return n; })(),
    inline_style_attrs: document.querySelectorAll('[style]').length,
    inline_handlers: Array.from(document.querySelectorAll('*'))
      .filter(el => Array.from(el.attributes)
        .some(a => /^on[a-z]+$/.test(a.name))).length,
    build: window.ACS_BUILD_INFO || null,
    api_base: typeof window.ACS_API === 'object' && !!window.ACS_API,
    csp: (window.__CSPV || []).slice(0, 10)
  }));
  boot('the shipped page is a SHELL: its only inline script is the import map',
    shape.inline_scripts.length === 1
    && shape.inline_scripts[0] === 'importmap',
    JSON.stringify(shape.inline_scripts));
  boot('the shell declares exactly one ES-module entry point, /app/main.js',
    JSON.stringify(shape.module_entries) === JSON.stringify(['/app/main.js']),
    JSON.stringify(shape.module_entries));
  boot('every classic boot script the shell names actually loaded',
    shape.classic_boot.length === Object.keys(APPSRC.modules())
      .filter(k => k.indexOf('boot/') === 0).length
    && shape.classic_boot.every(u => served.has(u) || !!TARGET),
    JSON.stringify(shape.classic_boot));
  boot('the classic boot scripts ran before the module graph: '
    + 'window.ACS_BUILD_INFO and the API base exist',
    !!shape.build && shape.build.contract === 'acs-build-info/1.0.0'
    && shape.api_base === true, JSON.stringify(shape.build));
  boot('the EXTERNAL stylesheet loaded and its rules applied',
    shape.stylesheets >= 1 && shape.css_rules > 200,
    JSON.stringify([shape.stylesheets, shape.css_rules]));
  boot('no element carries a style= attribute and none carries an inline '
    + 'event handler — the strict CSP would silently kill both',
    shape.inline_style_attrs === 0 && shape.inline_handlers === 0,
    JSON.stringify([shape.inline_style_attrs, shape.inline_handlers]));
  boot('the production CSP raised NO violation during boot',
    shape.csp.length === 0, JSON.stringify(shape.csp));
  if (!TARGET) {
    const want = Object.keys(APPSRC.modules())
      .filter(k => k.indexOf('boot/') !== 0);
    const missing = want.filter(k => !served.has('/app/' + k));
    boot('EVERY shipped module under public/app/ was fetched by the browser — '
      + 'no module ships without being reached, none 404s',
      missing.length === 0,
      missing.length + ' not fetched: ' + missing.slice(0, 5).join(', '));
  }

  let ready = false;
  try {
    await pg.waitForFunction('window.ACS&&window.ACS.ready===true', null,
      { timeout: 30000 });
    ready = true;
  } catch (e) { /* reported below */ }
  boot('the module graph executed to completion and THREE was imported '
    + '(window.ACS.ready)', ready);
  const api = await pg.evaluate(() => ({
    diag: typeof (window.ACS || {}).renderDiagnostics === 'function',
    diagDetail: typeof (window.ACS || {}).renderDiagnosticsDetail
      === 'function',
    capture: typeof (window.ACS || {}).captureRenderFailure === 'function',
    align: typeof (window.ACS || {}).alignmentDiagnostics === 'function',
    snap: typeof (window.ACS || {}).canonicalTransformSnapshot === 'function',
    setModel: typeof (window.ACS || {}).setModel === 'function',
    pbr: typeof (window.ACS || {}).pbrApply === 'function',
    ad: typeof (window.ACS || {}).adApply === 'function'
  }));
  boot('the render diagnostics bridge is available', api.diag);
  boot('the detailed render diagnostics bridge is available (renamed from '
    + 'renderDiagnostics when the F-08 fixed-key contract took that name)',
    api.diagDetail);
  boot('the render-failure capture entry point is available (F-08)',
    api.capture);
  boot('the alignment diagnostics bridge is available', api.align);
  boot('the canonical transform snapshot bridge is available — the harness '
    + 'never touches module-scoped engine state', api.snap);
  boot('the model loading entry point is available', api.setModel);
  boot('the 9.1 and 9.2 presentation bridges are live', api.pbr && api.ad);
  boot('no page errors during boot', errs.length === 0, errs.join(' | '));
  boot('no failed asset requests', bad.length === 0, bad.slice(0, 4).join(' | '));

  if (!ready || !api.diag || !api.diagDetail || !api.setModel) {
    await b.close(); if (srv) srv.close();
    summarise(); return;
  }

  /* §6 — نموذج قانوني محدّد يُحمَّل فعلاً؛ لا يصحّ الفحص على ورشة فارغة */
  console.log('\n== EMPTY WORKSPACE IS NOT A PASS (§6) ==');
  const emptyDiag = await pg.evaluate('window.ACS.renderDiagnosticsDetail()');
  visual('an empty workspace reports NO canonical geometry instead of '
    + 'sky-sized bounds (the old false pass)',
    emptyDiag.model_bounds === null && emptyDiag.canonical_meshes === 0,
    JSON.stringify({ bounds: emptyDiag.model_bounds,
      canonical: emptyDiag.canonical_meshes }));

  const FIX = fixtures();
  for (const [fname, fmodel] of FIX) {
    console.log('\n== VISUAL MODEL — ' + fname + ' ==');
    await pg.evaluate(m => { window.ACS.setModel(m); }, fmodel);
    await pg.waitForTimeout(1200);
    await pg.evaluate(() => new Promise(r =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
    const d = await pg.evaluate('window.ACS.renderDiagnosticsDetail()');
    visual(fname + ': canonical bounds are finite and building-scale',
      !!d.model_bounds && isFinite(d.model_bounds.radius)
      && d.model_bounds.radius > 0 && d.model_bounds.radius < 5000,
      JSON.stringify(d.model_bounds));
    visual(fname + ': visible canonical meshes exist',
      d.canonical_meshes > 0 && d.visible_meshes > 0,
      'canonical=' + d.canonical_meshes + ' visible=' + d.visible_meshes);
    visual(fname + ': the renderer actually issued draw calls',
      d.draw_calls > 0, 'calls=' + d.draw_calls);
    visual(fname + ': triangles were rasterised',
      d.triangles > 0, 'triangles=' + d.triangles);
    visual(fname + ': the canvas has non-zero backing and CSS size',
      d.canvas_width > 0 && d.canvas_height > 0
      && d.css_width > 0 && d.css_height > 0,
      JSON.stringify([d.canvas_width, d.canvas_height, d.css_width,
        d.css_height]));
    visual(fname + ': the projection matrix is finite',
      d.projection_matrix_finite === true);
    visual(fname + ': the model intersects the camera frustum',
      d.camera_in_frustum === true,
      JSON.stringify(d.camera_frustum_detail));
    visual(fname + ': near/far clip planes contain the model',
      d.camera_near > 0 && d.camera_far > d.camera_near,
      'near=' + d.camera_near + ' far=' + d.camera_far);
    visual(fname + ': useful illumination reaches the scene',
      d.light_intensity_sum > 0,
      'lights=' + JSON.stringify(d.lights) + ' sum='
      + d.light_intensity_sum);
    const px = await PX.analysePageViewport(pg, 'canvas');
    visual(fname + ': the WebGL viewport is NOT black (decoded RGBA)',
      px.verdict === 'VISIBLE_CONTENT',
      JSON.stringify({ reasons: px.reasons, mean: px.luminance_mean,
        near_black_pct: px.near_black_pct,
        buckets: px.luminance_buckets }));

    /* §13 — جسر التحقّق القرائي: النتيجة الواحدة التي تلخّص «هل يُرى؟» */
    const vv = await pg.evaluate('window.ACS.verifyVisibleModel()');
    visual(fname + ': verifyVisibleModel reports a loaded model with meshes',
      vv.model_loaded === true && vv.canonical_meshes > 0,
      JSON.stringify({ loaded: vv.model_loaded, meshes: vv.canonical_meshes }));
    visual(fname + ': it reports the camera inside the frustum and valid clip',
      vv.camera_in_frustum === true && vv.clip_valid === true,
      JSON.stringify({ frustum: vv.camera_in_frustum, clip: vv.clip_valid,
        near: vv.camera_near, far: vv.camera_far }));
    visual(fname + ': it reports visible pixels',
      vv.pixels_visible === true, vv.pixel_status);
    visual(fname + ': near/far were reconciled for THIS model, not left at the '
      + 'construction defaults 0.05 / 6000',
      !(vv.camera_near === 0.05 && vv.camera_far === 6000),
      'near=' + vv.camera_near + ' far=' + vv.camera_far);
    const rr = await pg.evaluate('window.ACS.renderRecoveryReport()');
    visual(fname + ': the camera reconciliation ran and applied',
      !!(rr.last_fit && rr.last_fit.applied), JSON.stringify(rr.last_fit && {
        applied: rr.last_fit.applied, frustum: rr.last_fit.camera_in_frustum,
        excluded: (rr.last_fit.diagnostics || {}).excluded_invalid_bounds }));
    visual(fname + ': no recovery cycle was needed for a healthy load',
      rr.cycles === 0 || (rr.recovery && rr.recovery.recovered === true),
      JSON.stringify({ cycles: rr.cycles }));
    if (fname === 'live_large_generated_outlier') {
      visual(fname + ': the stray coordinate was excluded from camera bounds '
        + '(this is the reported black-viewport mechanism)',
        ((rr.last_fit || {}).diagnostics || {}).excluded_invalid_bounds > 0,
        JSON.stringify((rr.last_fit || {}).diagnostics));
      visual(fname + ': and the scene radius stayed building-scale anyway',
        vv.scene_radius > 0 && vv.scene_radius < 5000, String(vv.scene_radius));
    }
    const rp = await pg.evaluate('window.ACS.renderResourcePressure()');
    visual(fname + ': resource pressure is measured (calls/tris/geometries)',
      rp.draw_calls !== null && rp.geometries !== null,
      JSON.stringify({ calls: rp.draw_calls, geo: rp.geometries,
        pressure: rp.pressure }));

    /* §3 — مصفوفة الأوضاع: أيّ طبقة تُسوّد الإطار إن سوّدته.
       F-08 — وُسِّعت لتشمل الحالات التسع المطلوبة صراحةً: BASE، PBR OFF،
       PBR ON، POST PROCESS، ARCH DETAIL، SITE CONTEXT، LANDSCAPE،
       ENGINEERING، والمسار الاحتياطي لجهاز يدعم VR. */
    const MODES = [
      ['BASE (no presentation layer applied)', () => {
        if (typeof window.ACS.pbrRestore === 'function') window.ACS.pbrRestore();
        if (typeof window.ACS.adMode === 'function')
          window.ACS.adMode('ENGINEERING');
      }],
      ['PBR OFF / DETAIL OFF', () => { }],
      ['PBR ON (HIGH, REALISTIC, SKY)', () => {
        const c = window.ACS.pbr.config('HIGH', 'CLEAR_NOON', 'REALISTIC',
          'SKY', null, null, window.ACS.pbrCaps(), window.ACS.pbrBounds());
        if (c.valid) window.ACS.pbrApply(c.config);
      }],
      ['POST PROCESS (ULTRA, composer + SSAO)', () => {
        const c = window.ACS.pbr.config('ULTRA', 'STUDIO_DAY', 'REALISTIC',
          'SKY', null, null, window.ACS.pbrCaps(), window.ACS.pbrBounds());
        if (c.valid) window.ACS.pbrApply(c.config);
      }],
      ['ARCHDETAIL STANDARD / CONTEXT NONE', () => {
        const c = window.ACS.archdetail.config('DETAIL_STANDARD', 'REQUESTED',
          'NONE', 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY', null, false, [], window.ACS.adModelSummary());
        if (c.valid) window.ACS.adApply(c.config);
      }],
      ['CONTEXT NEUTRAL', () => {
        const c = window.ACS.archdetail.config('DETAIL_STANDARD', 'REQUESTED',
          'NEUTRAL', 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY', null, false, [], window.ACS.adModelSummary());
        if (c.valid) window.ACS.adApply(c.config);
      }],
      ['CONTEXT SITE', () => {
        const c = window.ACS.archdetail.config('DETAIL_HIGH', 'REQUESTED',
          'SITE', 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY', null, false, [], window.ACS.adModelSummary());
        if (c.valid) window.ACS.adApply(c.config);
      }],
      ['CONTEXT LANDSCAPE', () => {
        const c = window.ACS.archdetail.config('DETAIL_HIGH', 'REQUESTED',
          'LANDSCAPE', 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY', null, false, [], window.ACS.adModelSummary());
        if (c.valid) window.ACS.adApply(c.config);
      }],
      ['ENGINEERING (compare mode restored)', () => {
        if (typeof window.ACS.adMode === 'function')
          window.ACS.adMode('ENGINEERING');
      }],
      ['VR-CAPABLE FALLBACK (xr enabled, not presenting)', () => {
        /* لا جلسة XR حقيقية في مِرقاب بلا نظّارة: نتحقّق من أن مسار العرض
           العادي يبقى حيّاً بينما محرّك XR مفعَّل — أي أن الاحتياطي لا يُسوّد
           الإطار. الجلسة الحقيقية تبقى NOT VERIFIED هنا. */
        window.__ACS_XR_PROBE__ = { xr_enabled: null, presenting: null };
        const d = window.ACS.renderDiagnostics();
        window.__ACS_XR_PROBE__ = d.xr_state;
      }],
      ['CAMERA PRESET EXTERIOR_HERO', () => {
        window.ACS.pbrCameraPreset('EXTERIOR_HERO');
      }]
    ];
    console.log('  --- mode matrix (§3) ---');
    console.log('  ' + 'MODE'.padEnd(38) + 'VISIBLE  NON-BLACK%  CALLS  '
      + 'RESULT');
    for (const [label, fn] of MODES) {
      await pg.evaluate(fn);
      await pg.evaluate(() => new Promise(r =>
        requestAnimationFrame(() => requestAnimationFrame(r))));
      const dd = await pg.evaluate('window.ACS.renderDiagnosticsDetail()');
      const df = await pg.evaluate('window.ACS.renderDiagnostics()');
      const pp = await PX.analysePageViewport(pg, 'canvas');
      const ok = pp.verdict === 'VISIBLE_CONTENT' && dd.draw_calls > 0
        && dd.camera_in_frustum === true;
      console.log('  ' + label.padEnd(38)
        + String(dd.visible_meshes).padEnd(9)
        + String(pp.non_background_pct).padEnd(12)
        + String(dd.draw_calls).padEnd(7)
        + (ok ? 'PASS' : 'FAIL ' + JSON.stringify(pp.reasons)));
      visual(fname + ' · ' + label + ': model visible and viewport not black',
        ok, JSON.stringify(pp.reasons));
      /* F-08 — الشروط الأربعة على كل حالة عرض، من عقد التشخيص مضبوط
         المفاتيح: بكسلات غير صفرية، كاميرا بلا NaN/لانهاية، حدود مشهد
         صالحة، ولا إحداثية غير صالحة. */
      visual(fname + ' · ' + label + ': non-zero visible pixels were probed '
        + 'in the real framebuffer',
        !!df.pixel_probe && df.pixel_probe.non_zero_pixels > 0,
        JSON.stringify(df.pixel_probe));
      visual(fname + ' · ' + label + ': no NaN or infinite camera value',
        Array.isArray(df.camera_position)
        && df.camera_position.every(Number.isFinite)
        && Array.isArray(df.camera_target)
        && df.camera_target.every(Number.isFinite)
        && Number.isFinite(df.near) && Number.isFinite(df.far)
        && df.near > 0 && df.far > df.near,
        JSON.stringify({ p: df.camera_position, t: df.camera_target,
          near: df.near, far: df.far }));
      visual(fname + ' · ' + label + ': scene bounds are finite and '
        + 'building-scale, and no coordinate is invalid',
        !!df.scene_bounds && df.scene_bounds.min.every(Number.isFinite)
        && df.scene_bounds.max.every(Number.isFinite)
        && Number.isFinite(df.scene_bounds.radius)
        && df.scene_bounds.radius > 0
        && df.invalid_coordinate_count === 0,
        JSON.stringify({ bounds: df.scene_bounds,
          invalid: df.invalid_coordinate_count }));
      visual(fname + ' · ' + label + ': the diagnostics contract returns '
        + 'exactly its declared keys',
        Object.keys(df).length === 24,
        JSON.stringify(Object.keys(df)));
    }
    /* الحالة التاسعة: المسار الاحتياطي على جهاز يدعم VR — لا جلسة XR هنا */
    const xrProbe = await pg.evaluate('window.__ACS_XR_PROBE__ || null');
    visual(fname + ' · VR-CAPABLE FALLBACK: the XR state is really read from '
      + 'the renderer and the non-XR path stayed alive (a real headset '
      + 'session is NOT VERIFIED here)',
      !!xrProbe && typeof xrProbe.presenting === 'boolean'
      && xrProbe.presenting === false,
      JSON.stringify(xrProbe));
    /* §6/§13/§15 — محاذاة فعلية بعد كل وضع، وثبات المصفوفات عبر التبديل */
    const align = await pg.evaluate('window.ACS.alignmentDiagnostics()');
    visual(fname + ': every hosted object resolves a transform (none '
      + 'unresolved, none silently at the origin)',
      align.unresolved_transforms === 0,
      JSON.stringify({ checked: align.objects_checked,
        unresolved: align.unresolved_transforms,
        samples: (align.samples || []).slice(0, 3) }));
    visual(fname + ': no object sits outside its canonical host',
      align.outside_host_objects === 0,
      JSON.stringify((align.samples || []).slice(0, 4)));
    visual(fname + ': the roof sits at its canonical elevation',
      !align.roof_alignment || align.roof_alignment.aligned === true,
      JSON.stringify(align.roof_alignment));
    visual(fname + ': every level plate is one level offset apart',
      (align.level_alignment || []).every(l => l.aligned !== false),
      JSON.stringify(align.level_alignment));
    visual(fname + ': the alignment layer moved nothing to make it fit',
      align.objects_moved_to_fit === 0 && align.writes_to_model === false);
    /* §15 — ثبات التحويلات: مصفوفات العالم القانونية بعد سلسلة التبديل
       يجب أن تساوي خط الأساس تماماً، بلا تراكم ولا انجراف */
    const drift = await pg.evaluate(() => {
      /* حالة المحرّك محصورة في نطاق الوحدة عمداً: المِرقاب لا يلمس
         scene/model/renderer/camera مباشرة، بل يقارن بصمة الجسر الضيّق */
      const snap = () => window.ACS.canonicalTransformSnapshot();
      const base = snap();
      const pq = window.ACS.pbr.config('HIGH', 'CLEAR_NOON', 'REALISTIC',
        'SKY', null, null, window.ACS.pbrCaps(), window.ACS.pbrBounds());
      if (pq.valid) window.ACS.pbrApply(pq.config);
      ['NONE', 'SITE', 'LANDSCAPE'].forEach(cx => {
        const c = window.ACS.archdetail.config('DETAIL_STANDARD', 'REQUESTED',
          cx, 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER', 'CLEAR_SKY',
          null, false, [], window.ACS.adModelSummary());
        if (c.valid) window.ACS.adApply(c.config); });
      window.ACS.adMode('ENGINEERING');
      if (window.ACS.pbrRestore) window.ACS.pbrRestore();
      const after = snap();
      return { available: base.available && after.available,
        equal: base.available && after.available
          && base.digest === after.digest && base.count === after.count,
        count: base.count, before: base.digest, afterDigest: after.digest };
    });
    visual(fname + ': canonical world matrices are identical after the full '
      + 'PBR/detail/context toggle sequence — no transform drift',
      drift.available === true && drift.equal === true,
      JSON.stringify(drift));
    /* الهندسة القانونية لم تتغيّر بأي وضع عرض */
    const after = await pg.evaluate('window.ACS.renderDiagnosticsDetail()');
    visual(fname + ': canonical bounds identical after the whole matrix',
      JSON.stringify(after.model_bounds) === JSON.stringify(d.model_bounds),
      JSON.stringify([d.model_bounds, after.model_bounds]));
    await pg.evaluate(() => { window.ACS.adMode('ENGINEERING'); });
  }

  /* §9 — التحجيم */
  console.log('\n== RESIZE MATRIX (§9) ==');
  for (const [w, h] of RESOLUTIONS) {
    await pg.setViewportSize({ width: w, height: h });
    await pg.waitForTimeout(400);
    await pg.evaluate(() => new Promise(r =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
    const d = await pg.evaluate('window.ACS.renderDiagnosticsDetail()');
    const px = await PX.analysePageViewport(pg, 'canvas');
    visual(w + '×' + h + ': canvas sized, aspect updated, viewport not black',
      d.canvas_width > 0 && d.canvas_height > 0 && d.css_width > 0
      && Math.abs(d.camera_aspect - (w / h)) < 0.2
      && d.projection_matrix_finite === true
      && px.verdict === 'VISIBLE_CONTENT',
      'aspect=' + d.camera_aspect + ' canvas=' + d.canvas_width + 'x'
      + d.canvas_height + ' px=' + JSON.stringify(px.reasons));
  }

  boot('no page errors after the full run', errs.length === 0,
    errs.slice(0, 3).join(' | '));
  const cspEnd = await pg.evaluate('(window.__CSPV || []).slice(0, 10)');
  boot('the production CSP raised NO violation across the whole run either',
    Array.isArray(cspEnd) && cspEnd.length === 0, JSON.stringify(cspEnd));
  await b.close(); if (srv) srv.close();
  summarise();
})().catch(e => {
  console.log('\nharness error: ' + String(e && e.message).slice(0, 300));
  process.exit(1);
});

function summarise() {
  const bf = BOOT.filter(x => !x.ok).length;
  const vf = VISUAL.filter(x => !x.ok).length;
  console.log('\n──────────────────────────────────────────────');
  console.log('BOOT: ' + (bf ? 'FAIL' : 'PASS')
    + '  (' + (BOOT.length - bf) + '/' + BOOT.length + ')');
  console.log('VISUAL MODEL: ' + (VISUAL.length === 0 ? 'FAIL (not exercised)'
    : (vf ? 'FAIL' : 'PASS'))
    + '  (' + (VISUAL.length - vf) + '/' + VISUAL.length + ')');
  process.exit((bf || vf || VISUAL.length === 0) ? 1 : 0);
}
