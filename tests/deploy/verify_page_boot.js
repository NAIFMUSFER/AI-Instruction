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

function serve() {
  const MIME = { '.html': 'text/html', '.js': 'text/javascript',
    '.mjs': 'text/javascript', '.css': 'text/css',
    '.json': 'application/json', '.png': 'image/png',
    '.svg': 'image/svg+xml' };
  return new Promise(res => {
    const srv = http.createServer((rq, rs) => {
      const u = decodeURIComponent(rq.url.split('?')[0]);
      const p = path.normalize(path.join(PUB, u === '/' ? 'index.html' : u));
      if (!p.startsWith(PUB) || !fs.existsSync(p)
        || fs.statSync(p).isDirectory()) { rs.writeHead(404); rs.end(); return; }
      rs.writeHead(200, { 'Content-Type':
        MIME[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rs);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

function fixtures() {
  const base = JSON.parse(fs.readFileSync(path.join(ROOT, 'tests', 'phase3',
    'fixtures', 'base_fixtures.json'), 'utf8'));
  return [['villa', base.villa_glazed || base.villa],
          ['warehouse', base.warehouse]];
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
  let chromium;
  try { ({ chromium } = require('playwright')); }
  catch (e) { notVerified('playwright is not installed'); }

  const srv = TARGET ? null : await serve();
  const base = TARGET
    || ('http://127.0.0.1:' + srv.address().port + '/index.html');
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: RESOLUTIONS[0][0],
    height: RESOLUTIONS[0][1] } });
  const errs = [], bad = [];
  pg.on('pageerror', e => errs.push(String(e.message).slice(0, 200)));
  pg.on('response', r => { if (r.status() >= 400)
    bad.push('HTTP ' + r.status() + ' ' + r.url().slice(0, 110)); });

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
  let ready = false;
  try {
    await pg.waitForFunction('window.ACS&&window.ACS.ready===true', null,
      { timeout: 30000 });
    ready = true;
  } catch (e) { /* reported below */ }
  boot('the module script executed and THREE was imported '
    + '(window.ACS.ready)', ready);
  const api = await pg.evaluate(() => ({
    diag: typeof (window.ACS || {}).renderDiagnostics === 'function',
    align: typeof (window.ACS || {}).alignmentDiagnostics === 'function',
    setModel: typeof (window.ACS || {}).setModel === 'function',
    pbr: typeof (window.ACS || {}).pbrApply === 'function',
    ad: typeof (window.ACS || {}).adApply === 'function'
  }));
  boot('the render diagnostics bridge is available', api.diag);
  boot('the alignment diagnostics bridge is available', api.align);
  boot('the model loading entry point is available', api.setModel);
  boot('the 9.1 and 9.2 presentation bridges are live', api.pbr && api.ad);
  boot('no page errors during boot', errs.length === 0, errs.join(' | '));
  boot('no failed asset requests', bad.length === 0, bad.slice(0, 4).join(' | '));

  if (!ready || !api.diag || !api.setModel) {
    await b.close(); if (srv) srv.close();
    summarise(); return;
  }

  /* §6 — نموذج قانوني محدّد يُحمَّل فعلاً؛ لا يصحّ الفحص على ورشة فارغة */
  console.log('\n== EMPTY WORKSPACE IS NOT A PASS (§6) ==');
  const emptyDiag = await pg.evaluate('window.ACS.renderDiagnostics()');
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
    const d = await pg.evaluate('window.ACS.renderDiagnostics()');
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

    /* §3 — مصفوفة الأوضاع: أيّ طبقة تُسوّد الإطار إن سوّدته */
    const MODES = [
      ['PBR OFF / DETAIL OFF', () => { }],
      ['PBR ON (HIGH, REALISTIC, SKY)', () => {
        const c = window.ACS.pbr.config('HIGH', 'CLEAR_NOON', 'REALISTIC',
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
      const dd = await pg.evaluate('window.ACS.renderDiagnostics()');
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
    }
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
      const snap = () => { scene.updateMatrixWorld(true); const o = [];
        model.traverse(m => { if (m.isMesh && m.name && m.name.indexOf('|') > 0)
          o.push(m.name + ':' + m.matrixWorld.elements
            .map(v => Math.round(v * 1e6) / 1e6).join(',')); });
        return o.sort().join('|'); };
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
      return { equal: base === after, len: base.length };
    });
    visual(fname + ': canonical world matrices are identical after the full '
      + 'PBR/detail/context toggle sequence — no transform drift',
      drift.equal === true, JSON.stringify(drift));
    /* الهندسة القانونية لم تتغيّر بأي وضع عرض */
    const after = await pg.evaluate('window.ACS.renderDiagnostics()');
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
    const d = await pg.evaluate('window.ACS.renderDiagnostics()');
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
