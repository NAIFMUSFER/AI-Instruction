/* ============================================================================
   F-14 — مِرقاب الأداء الحقيقي (Chromium حقيقي، أرقام مقيسة، بلا تقدير).

     node tests/performance/run_perf.js                  # الصفحة المشحونة محلياً
     node tests/performance/run_perf.js --target <url>   # ضدّ النشر الحقيقي
     node tests/performance/run_perf.js --self-test      # برهان اللاعقامة فقط

   ما يقيسه لكل نموذج: زمن أوّل تحميل، زمن تحليل/تهيئة JS، تهيئة Three، بناء
   النموذج، أوّل إطار مرئي، متوسّط FPS، مئينات زمن الإطار p5/p95، نداءات الرسم،
   المثلّثات، كومة JS، الذاكرة بعد تحميلات متكرّرة، الذاكرة بعد التخلّص، عدد
   سياقات WebGL، وأحداث فقد السياق. ثم سيناريوهات التسريب: 20 مشروعاً بالتتابع،
   دخول/خروج PBR، تبديل السياق/المشهد 50 مرّة، لقطات تُنشأ وتُتلَف، ودخول/خروج
   VR حيث يتوفّر.

   ─────────────────────────────────────────────────────────────────────────────
   الحقيقة غير المريحة، مكتوبة قبل أي رقم:

   public/vendor فارغ في هذه النسخة ولا شبكة في هذا الصندوق، فـThree.js لا
   يُحمَّل ولا يُرسَم إطار واحد. لذلك لا يمكن قياس التطبيق هنا إطلاقاً. هذا
   الملفّ يخرج بالرمز 2 معلناً:

       NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED

   ويكتب tests/performance/outputs/perf.json يسجّل أنه لم يُقَس شيء. لا رقم
   مخترَع، ولا رقم «تقديري»، ولا نجاح مزيَّف.

   ومِرقابٌ لا يقيس إلّا العدم لا يُفرَّق عن مِرقابٍ معطوب. لذلك — قبل الخروج —
   يُوجَّه المِرقاب إلى صفحة WebGL2 صغيرة كتبناها بأنفسنا (vacuity_page.html:
   كانفس + getContext('webgl2') + حلقة requestAnimationFrame، بلا Three.js)
   تُخدَم من 127.0.0.1، ويُقاس عليها بنفس شيفرة القياس تماماً. الأرقام الناتجة
   حقيقية وتثبت أن آلة القياس تعمل. ولا تقول شيئاً عن أداء التطبيق.
   ========================================================================== */
'use strict';
const fs = require('fs'), path = require('path'), http = require('http');

const HERE = __dirname, ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const OUTDIR = path.join(HERE, 'outputs');
const OUTFILE = path.join(OUTDIR, 'perf.json');
const PW = require(path.join(ROOT, 'tools', 'pw_chromium.js'));

const ARGV = process.argv.slice(2);
const TARGET = (function () {
  const i = ARGV.indexOf('--target');
  return i >= 0 ? ARGV[i + 1] : null;
})();
const SELF_TEST_ONLY = ARGV.indexOf('--self-test') >= 0;

const BUDGETS = JSON.parse(fs.readFileSync(path.join(HERE, 'budgets.json'), 'utf8'));
const GOVERNOR = JSON.parse(fs.readFileSync(
  path.join(HERE, 'quality_governor.json'), 'utf8'));

/* ═════════════════════════════════════════════ خادم محلّي (127.0.0.1 فقط) ══ */
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript',
  '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.svg': 'image/svg+xml', '.wasm': 'application/wasm' };

function serve(rootDir) {
  return new Promise(res => {
    const srv = http.createServer((rq, rs) => {
      const u = decodeURIComponent(rq.url.split('?')[0]);
      const p = path.normalize(path.join(rootDir, u === '/' ? 'index.html' : u));
      if (!p.startsWith(rootDir) || !fs.existsSync(p)
        || fs.statSync(p).isDirectory()) { rs.writeHead(404); rs.end(); return; }
      rs.writeHead(200, { 'Content-Type':
        MIME[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rs);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

/* ═══════════════════════════════ أدوات القياس — مشتركة بين المسارين حرفياً ══
   هذه الدوالّ نفسها تُستعمل على التطبيق وعلى صفحة اللاعقامة. لا نسخة ثانية
   «مبسّطة» للبرهان: لو كان القياس مكسوراً لظهر في البرهان أيضاً. */

/* حَقن قبل أي سكربت في الصفحة: يعدّ سياقات WebGL، وأحداث فقد السياق، وحلقات
   العرض المتمايزة، والمستمعين المكرّرين. كله من داخل الصفحة، بلا افتراض عن
   بنيتها — فيصلح للتطبيق ولصفحة اختبار صغيرة سواءً. */
function instrumentationSource() {
  return function () {
    const P = window.__ACS_PERF__ = {
      contexts: [], context_lost: 0, context_restored: 0,
      raf_loops: {}, harness_loops: {}, listeners: {}, listener_dupes: 0,
      errors: []
    };
    /* المِرقاب نفسه يفتح حلقة rAF ليأخذ العيّنة. لو عُدَّت لكان كل قياس يبلّغ
       عن حلقة زائدة لا وجود لها في الصفحة. تُستبعَد ببصمتها الصريحة. */
    const isHarness = src => src.indexOf('__ACS_PERF_FRAMES__') >= 0;
    const hash = s => {
      let h = 5381;
      for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0;
      return String(h);
    };
    /* 1) عدّ سياقات WebGL الحيّة + أحداث الفقد */
    const realGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type) {
      const ctx = realGetContext.apply(this, arguments);
      if (ctx && /webgl/i.test(String(type))) {
        if (P.contexts.indexOf(ctx) < 0) {
          P.contexts.push(ctx);
          this.addEventListener('webglcontextlost', () => { P.context_lost++; });
          this.addEventListener('webglcontextrestored',
            () => { P.context_restored++; });
        }
      }
      return ctx;
    };
    /* 2) حلقات العرض: نُعرّف الحلقة بأنها ردّ نداء rAF يعيد جدولة نفسه.
          عدد الحلقات المتمايزة = عدد بصمات الشيفرة التي فعلت ذلك. */
    const realRAF = window.requestAnimationFrame;
    let inFlight = null;
    window.requestAnimationFrame = function (cb) {
      const key = hash(String(cb).slice(0, 400));
      const harness = isHarness(String(cb));
      return realRAF.call(window, function (t) {
        const prev = inFlight; inFlight = key;
        const bucket = harness ? P.harness_loops : P.raf_loops;
        const before = bucket[key] || (bucket[key] =
          { calls: 0, self_rescheduled: 0 });
        before.calls++;
        const guard = window.requestAnimationFrame;
        window.requestAnimationFrame = function (c2) {
          if (hash(String(c2).slice(0, 400)) === key) before.self_rescheduled++;
          return guard.call(window, c2);
        };
        try { cb(t); } catch (e) { P.errors.push(String(e && e.message)); }
        window.requestAnimationFrame = guard;
        inFlight = prev;
      });
    };
    /* 3) المستمعون المكرّرون: نفس الهدف + نفس النوع + نفس بصمة الدالّة */
    const realAdd = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function (type, fn, opts) {
      try {
        const tag = (this === window ? 'window'
          : this === document ? 'document'
            : (this.tagName || this.constructor.name || 'obj'))
          + '#' + (this.id || '');
        const key = tag + '|' + type + '|' + hash(String(fn).slice(0, 300));
        P.listeners[key] = (P.listeners[key] || 0) + 1;
        if (P.listeners[key] > 1) P.listener_dupes++;
      } catch (e) { /* لا يعطّل الصفحة أبداً */ }
      return realAdd.apply(this, arguments);
    };
    /* 4) بصمة زمنية للتحميل الأوّل */
    P.nav_start = performance.timeOrigin || 0;
  };
}

/* عيّنة إطارات حقيقية: تُجمع طوابع rAF داخل الصفحة ثم تُحسب المئينات هنا. */
async function sampleFrames(page, ms) {
  await page.evaluate(dur => new Promise(res => {
    const t = [];
    const t0 = performance.now();
    (function tick(now) {
      t.push(now);
      if (now - t0 < dur) requestAnimationFrame(tick);
      else { window.__ACS_PERF_FRAMES__ = t; res(); }
    })(performance.now());
  }), ms);
  const stamps = await page.evaluate(() => window.__ACS_PERF_FRAMES__ || []);
  return frameStats(stamps, ms);
}

function percentile(sorted, q) {
  if (!sorted.length) return null;
  const i = Math.min(sorted.length - 1,
    Math.max(0, Math.round((sorted.length - 1) * q)));
  return sorted[i];
}

function frameStats(stamps, requestedMs) {
  if (!stamps || stamps.length < 3) {
    return { frames: stamps ? stamps.length : 0, measured: false,
      reason: 'fewer than 3 frames were produced' };
  }
  const deltas = [];
  for (let i = 1; i < stamps.length; i++) deltas.push(stamps[i] - stamps[i - 1]);
  const sorted = deltas.slice().sort((a, b) => a - b);
  const span = stamps[stamps.length - 1] - stamps[0];
  const mean = deltas.reduce((a, b) => a + b, 0) / deltas.length;
  const p5 = percentile(sorted, 0.05), p95 = percentile(sorted, 0.95);
  const r = x => x === null ? null : Math.round(x * 1000) / 1000;
  return {
    measured: true,
    requested_window_ms: requestedMs,
    actual_window_ms: r(span),
    frames: stamps.length,
    fps_average: r(deltas.length / (span / 1000)),
    frame_time_mean_ms: r(mean),
    frame_time_min_ms: r(sorted[0]),
    frame_time_max_ms: r(sorted[sorted.length - 1]),
    frame_time_p5_ms: r(p5),
    frame_time_p50_ms: r(percentile(sorted, 0.50)),
    frame_time_p95_ms: r(p95),
    fps_at_p5_frame_time: r(1000 / p5),
    fps_at_p95_frame_time: r(1000 / p95)
  };
}

async function heap(page) {
  return page.evaluate(() => {
    const m = performance.memory;
    if (!m) return null;
    return { used_js_heap_bytes: m.usedJSHeapSize,
      total_js_heap_bytes: m.totalJSHeapSize,
      js_heap_limit_bytes: m.jsHeapSizeLimit };
  });
}

async function perfCounters(page) {
  return page.evaluate(() => {
    const P = window.__ACS_PERF__ || {};
    const loops = Object.keys(P.raf_loops || {})
      .filter(k => P.raf_loops[k].self_rescheduled > 0);
    const harnessLoops = Object.keys(P.harness_loops || {}).length;
    return {
      webgl_context_count: (P.contexts || []).length,
      context_lost_events: P.context_lost || 0,
      context_restored_events: P.context_restored || 0,
      render_loop_count: loops.length,
      render_loop_detail: loops.map(k => ({ id: k,
        calls: P.raf_loops[k].calls,
        self_rescheduled: P.raf_loops[k].self_rescheduled })),
      duplicate_event_listener_count: P.listener_dupes || 0,
      harness_own_sampling_loops_excluded: harnessLoops,
      in_page_errors: (P.errors || []).slice(0, 10)
    };
  });
}

/* موارد GPU: من renderer.info في التطبيق، ومن عدّاد الصفحة في برهان اللاعقامة.
   شكل المخرَج واحد، والمصدر مُعلَن دائماً — فلا يُخلط قياسٌ بآخر. */
async function gpuStats(page) {
  return page.evaluate(() => {
    if (window.ACS && typeof window.ACS.renderDiagnosticsDetail === 'function') {
      const d = window.ACS.renderDiagnosticsDetail();
      const info = (window.ACS.renderResourcePressure
        && window.ACS.renderResourcePressure()) || {};
      return { source: 'THREE renderer.info via window.ACS',
        draw_calls: d.draw_calls, triangles: d.triangles,
        geometries: info.geometries === undefined ? null : info.geometries,
        textures: info.textures === undefined ? null : info.textures,
        programs: info.programs === undefined ? null : info.programs,
        canonical_meshes: d.canonical_meshes, visible_meshes: d.visible_meshes };
    }
    if (window.__VACUITY__) {
      const V = window.__VACUITY__;
      return { source: 'plain WebGL2 page counters (vacuity proof)',
        draw_calls: V.drawCalls, triangles: V.triangles,
        geometries: null, textures: null, programs: null,
        canonical_meshes: null, visible_meshes: null,
        frames_drawn: V.frames };
    }
    return { source: 'none', draw_calls: null, triangles: null,
      geometries: null, textures: null, programs: null };
  });
}

async function navigationTiming(page) {
  return page.evaluate(() => {
    const n = performance.getEntriesByType('navigation')[0];
    if (!n) return null;
    const r = x => Math.round(x * 1000) / 1000;
    return {
      response_end_ms: r(n.responseEnd),
      dom_interactive_ms: r(n.domInteractive),
      dom_content_loaded_ms: r(n.domContentLoadedEventEnd),
      load_event_end_ms: r(n.loadEventEnd),
      transfer_size_bytes: n.transferSize,
      decoded_body_bytes: n.decodedBodySize
    };
  });
}

/* ═══════════════════════════════════ برهان اللاعقامة (يعمل دائماً هنا) ════ */
async function vacuityProof(browser) {
  const srv = await serve(HERE);
  const url = 'http://127.0.0.1:' + srv.address().port + '/vacuity_page.html';
  const pg = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await pg.addInitScript(instrumentationSource());
  const errs = [];
  pg.on('pageerror', e => errs.push(String(e.message).slice(0, 160)));
  const t0 = Date.now();
  await pg.goto(url, { waitUntil: 'load', timeout: 60000 });
  const loadMs = Date.now() - t0;
  const ok = await pg.evaluate(() => !!(window.__VACUITY__
    && window.__VACUITY__.webgl2 && !window.__VACUITY__.error));
  if (!ok) {
    const why = await pg.evaluate(() => (window.__VACUITY__ || {}).error
      || 'no webgl2');
    await pg.close(); srv.close();
    return { proved: false, reason: 'the minimal WebGL2 page itself could not '
      + 'run in this Chromium: ' + why };
  }
  /* يُترك ليستقرّ ثم تُؤخذ عيّنتان بحملين مختلفين: لو كانت الأرقام مطبوعة
     لما تحرّكت مع الحمل. تحرّكها هو البرهان. */
  await pg.waitForTimeout(700);
  await pg.evaluate(() => { window.__VACUITY__.quadsPerFrame = 64; });
  const light = await sampleFrames(pg, 2500);
  const glLight = await gpuStats(pg);
  const heapBefore = await heap(pg);
  await pg.evaluate(() => { window.__VACUITY__.quadsPerFrame = 2400; });
  await pg.waitForTimeout(400);
  const heavy = await sampleFrames(pg, 2500);
  const glHeavy = await gpuStats(pg);
  /* الكومة: تُقاس، ثم يُخصَّص 64 ميغابايت، ثم تُقاس ثانية. */
  const allocated = await pg.evaluate(() => window.__VACUITY_ALLOC__(64));
  await pg.waitForTimeout(300);
  const heapAfterAlloc = await heap(pg);
  await pg.evaluate(() => window.__VACUITY_FREE__());
  const counters = await perfCounters(pg);
  const nav = await navigationTiming(pg);
  await pg.close(); srv.close();

  const heapMoved = !!(heapBefore && heapAfterAlloc
    && heapAfterAlloc.used_js_heap_bytes > heapBefore.used_js_heap_bytes);
  const fpsMoved = !!(light.measured && heavy.measured
    && heavy.fps_average < light.fps_average);
  return {
    proved: light.measured && heavy.measured
      && light.fps_average > 0 && counters.webgl_context_count === 1,
    url_scheme: 'http://127.0.0.1 (loopback, never proxied)',
    page: 'tests/performance/vacuity_page.html — canvas + getContext(\'webgl2\')'
      + ' + requestAnimationFrame loop, no Three.js, no framework',
    measurement_code: 'IDENTICAL to the application path: sampleFrames(), '
      + 'heap(), gpuStats(), perfCounters(), navigationTiming()',
    page_load_ms: loadMs,
    navigation_timing: nav,
    light_load: { quads_per_frame: 64, frames: light,
      gpu: glLight },
    heavy_load: { quads_per_frame: 2400, frames: heavy, gpu: glHeavy },
    heap_before_alloc: heapBefore,
    heap_after_alloc_64mb: heapAfterAlloc,
    heap_alloc_blocks: allocated,
    heap_delta_bytes: (heapBefore && heapAfterAlloc)
      ? heapAfterAlloc.used_js_heap_bytes - heapBefore.used_js_heap_bytes : null,
    counters: counters,
    page_errors: errs,
    sensitivity_checks: {
      fps_falls_when_the_gpu_load_rises: fpsMoved,
      heap_rises_when_memory_is_allocated: heapMoved,
      exactly_one_webgl_context_seen: counters.webgl_context_count === 1,
      exactly_one_render_loop_seen: counters.render_loop_count === 1,
      note: 'These are the checks that separate a real measurement from a '
        + 'printed constant. If the numbers did not move with the load, the '
        + 'harness would be reporting fiction.'
    },
    what_this_proves: 'The measurement code produces real, load-sensitive FPS, '
      + 'frame-time percentile and heap numbers in this Chromium.',
    what_this_does_not_prove: 'Nothing at all about the ACS application. The '
      + 'application was NOT measured — see status.'
  };
}

/* ═════════════════════════════════════════════════════ نماذج القياس ═══════ */
function realFixtures() {
  const out = [];
  const basePath = path.join(ROOT, 'tests', 'phase3', 'fixtures',
    'base_fixtures.json');
  if (fs.existsSync(basePath)) {
    const base = JSON.parse(fs.readFileSync(basePath, 'utf8'));
    [['villa', 'SMALL', 'small villa'],
     ['clinic', 'SMALL', 'clinic'],
     ['hotel', 'MEDIUM', 'hotel'],
     ['office', 'MEDIUM', 'office'],
     ['warehouse', 'LARGE', 'warehouse']].forEach(([k, cls, label]) => {
      if (base[k]) out.push({ name: k, label, klass: cls,
        provenance: 'tests/phase3/fixtures/base_fixtures.json', model: base[k] });
    });
  }
  const big = path.join(ROOT, 'tests', 'phase9_2', 'fixtures',
    'live_large_generated.json');
  if (fs.existsSync(big)) {
    out.push({ name: 'live_large_generated', label: 'large generated model',
      klass: 'STRESS', provenance: 'tests/phase9_2/fixtures/'
        + 'live_large_generated.json', model: JSON.parse(fs.readFileSync(big, 'utf8')) });
  }
  return out;
}

/* نماذج تركيبية — تُبنى برمجياً وحتميّاً (بلا عشوائية) حتى تكون قابلة للإعادة.
   كل غرفة هنا اصطناعية ومُعلَنة كذلك: لا قيمة تصميمية ولا تنظيمية لأي منها. */
function syntheticSpaces(n, name, klass) {
  const PER_LEVEL = 50;
  const levels = [], floors = {};
  let made = 0, li = 0;
  while (made < n) {
    const count = Math.min(PER_LEVEL, n - made);
    const tpl = 'lvl' + li;
    const cols = Math.ceil(Math.sqrt(count));
    const rooms = [];
    for (let i = 0; i < count; i++) {
      const cx = i % cols, cz = Math.floor(i / cols);
      rooms.push({
        id: 'sp_' + li + '_' + i,
        rect: [cx * 5, cz * 5, 4.6, 4.6],
        doors: [{ edge: (i % 2 === 0) ? 'S' : 'N', offset: 2.3, width: 0.9 }],
        windows: (i % 3 === 0)
          ? [{ edge: 'E', offset: 2.3, width: 1.4, height: 1.4, sill: 0.9 }] : [],
        synthetic: true, source: 'perf_fixture'
      });
      made++;
    }
    floors[tpl] = { rooms };
    levels.push({ index: li, name: 'level_' + li, template: tpl });
    li++;
  }
  const side = Math.ceil(Math.sqrt(Math.min(n, PER_LEVEL))) * 5 + 5;
  return {
    name, label: n + '-space synthetic', klass,
    provenance: 'generated programmatically by tests/performance/run_perf.js '
      + '(deterministic, no randomness); every room carries synthetic:true and '
      + 'source:perf_fixture and has no design or regulatory meaning',
    model: {
      meta: { type: 'other', name: name, synthetic: true,
        source: 'perf_fixture' },
      site: { w: side, d: side },
      floor_height: 3.2, wall_h: 3.0, wall_t: 0.15,
      levels, floors
    }
  };
}

/* شقة سكنية متعدّدة الأدوار: base_fixtures.json لا يحوي «apartment»، فيُبنى
   تركيبياً ويُعلَن ذلك بدل ادّعاء أنه نموذج حقيقي. */
function apartmentFixture() {
  const unit = (i, x, z) => ({
    id: 'apt_' + i, rect: [x, z, 9, 7],
    doors: [{ edge: 'S', offset: 4.5, width: 1.0 }],
    windows: [{ edge: 'N', offset: 4.5, width: 2.0, height: 1.5, sill: 0.9 }],
    synthetic: true, source: 'perf_fixture'
  });
  const rooms = [];
  for (let i = 0; i < 6; i++) rooms.push(unit(i, (i % 3) * 10, Math.floor(i / 3) * 8));
  rooms.push({ id: 'core', rect: [30, 0, 4, 16],
    objects: [{ kind: 'elevator', count: 2, x: 1, z: 2 },
      { kind: 'stairs', count: 1, x: 1, z: 10 }],
    doors: [{ edge: 'W', offset: 8, width: 1.2 }],
    synthetic: true, source: 'perf_fixture' });
  const levels = [], floors = { typ: { rooms } };
  for (let l = 0; l < 6; l++) levels.push({ index: l, name: 'level_' + l,
    template: 'typ' });
  return { name: 'apartment_generated', label: 'apartment (6 levels × 6 units)',
    klass: 'MEDIUM',
    provenance: 'generated programmatically — base_fixtures.json contains no '
      + 'apartment fixture; declared synthetic rather than passed off as real',
    model: { meta: { type: 'apartment', name: 'apartment_generated',
      synthetic: true, source: 'perf_fixture' },
      site: { w: 40, d: 20 }, floor_height: 3.1, wall_h: 2.9, wall_t: 0.15,
      levels, floors } };
}

function allFixtures() {
  const real = realFixtures();
  const byName = {};
  real.forEach(f => { byName[f.name] = f; });
  const list = [];
  if (byName.villa) list.push(byName.villa);
  list.push(apartmentFixture());
  ['hotel', 'clinic', 'warehouse', 'office'].forEach(k => {
    if (byName[k]) list.push(byName[k]);
  });
  list.push(syntheticSpaces(100, 'spaces_100', 'LARGE'));
  list.push(syntheticSpaces(500, 'spaces_500', 'LARGE'));
  list.push(syntheticSpaces(1000, 'spaces_1000', 'STRESS'));
  if (byName.live_large_generated) list.push(byName.live_large_generated);
  return list;
}

/* ═══════════════════════════════════ سيناريوهات التسريب (على التطبيق فقط) ══ */
const LEAK_SCENARIOS = [
  { id: 'SWITCH_20_PROJECTS',
    budget_id: 'HEAP_AFTER_20_PROJECT_SWITCHES',
    description: 'load 20 different models sequentially into the same viewer',
    iterations: 20 },
  { id: 'PBR_ENTER_EXIT',
    budget_id: 'PBR_ENTER_EXIT_LEAK',
    description: 'enter and exit PBR presentation repeatedly',
    iterations: 10 },
  { id: 'CONTEXT_LANDSCAPE_TOGGLE',
    budget_id: 'CONTEXT_LANDSCAPE_TOGGLE_LEAK',
    description: 'toggle site context and landscape 50 times',
    iterations: 50 },
  { id: 'SCREENSHOT_CREATE_DISPOSE',
    budget_id: 'SCREENSHOT_LEAK',
    description: 'create and dispose screenshots, checking revokeObjectURL',
    iterations: 20 },
  { id: 'VR_ENTER_EXIT',
    budget_id: null,
    description: 'enter and exit VR where the device supports it; on a machine '
      + 'with no XR device this is reported as UNSUPPORTED, never as a pass',
    iterations: 3 }
];

async function runLeakScenarios(pg, fixtures) {
  const results = [];
  const base = await gpuStats(pg);
  const baseHeap = await heap(pg);

  /* 1) 20 مشروعاً بالتتابع */
  const cycle = [];
  for (let i = 0; i < 20; i++) cycle.push(fixtures[i % fixtures.length]);
  for (const f of cycle) {
    await pg.evaluate(m => window.ACS.setModel(m), f.model);
    await pg.evaluate(() => new Promise(r =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
  }
  await pg.waitForTimeout(1200);
  const afterSwitch = await gpuStats(pg);
  const heapSwitch = await heap(pg);
  results.push({ id: 'SWITCH_20_PROJECTS', ran: true,
    geometries_delta: (afterSwitch.geometries === null || base.geometries === null)
      ? null : afterSwitch.geometries - base.geometries,
    textures_delta: (afterSwitch.textures === null || base.textures === null)
      ? null : afterSwitch.textures - base.textures,
    heap_growth_pct: (baseHeap && heapSwitch)
      ? Math.round(10000 * (heapSwitch.used_js_heap_bytes
        - baseHeap.used_js_heap_bytes) / baseHeap.used_js_heap_bytes) / 100 : null,
    counters: await perfCounters(pg) });

  /* 2) دخول/خروج PBR */
  const pbrBase = await gpuStats(pg);
  for (let i = 0; i < 10; i++) {
    await pg.evaluate(() => {
      if (!window.ACS.pbr) return;
      const c = window.ACS.pbr.config('HIGH', 'CLEAR_NOON', 'REALISTIC', 'SKY',
        null, null, window.ACS.pbrCaps(), window.ACS.pbrBounds());
      if (c.valid) window.ACS.pbrApply(c.config);
    });
    await pg.evaluate(() => { if (window.ACS.pbrRestore) window.ACS.pbrRestore(); });
  }
  await pg.waitForTimeout(800);
  const pbrAfter = await gpuStats(pg);
  results.push({ id: 'PBR_ENTER_EXIT', ran: true,
    geometries_delta: (pbrAfter.geometries === null || pbrBase.geometries === null)
      ? null : pbrAfter.geometries - pbrBase.geometries,
    textures_delta: (pbrAfter.textures === null || pbrBase.textures === null)
      ? null : pbrAfter.textures - pbrBase.textures });

  /* 3) تبديل السياق/المشهد 50 مرّة */
  const ctxBase = await gpuStats(pg);
  for (let i = 0; i < 50; i++) {
    const ctx = (i % 2 === 0) ? 'SITE' : 'LANDSCAPE';
    await pg.evaluate(c => {
      if (!window.ACS.archdetail) return;
      const cfg = window.ACS.archdetail.config('DETAIL_STANDARD', 'REQUESTED',
        c, 'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_CORNER', 'CLEAR_SKY',
        null, false, [], window.ACS.adModelSummary());
      if (cfg.valid) window.ACS.adApply(cfg.config);
    }, ctx);
  }
  await pg.waitForTimeout(800);
  const ctxAfter = await gpuStats(pg);
  results.push({ id: 'CONTEXT_LANDSCAPE_TOGGLE', ran: true,
    geometries_delta: (ctxAfter.geometries === null || ctxBase.geometries === null)
      ? null : ctxAfter.geometries - ctxBase.geometries,
    textures_delta: (ctxAfter.textures === null || ctxBase.textures === null)
      ? null : ctxAfter.textures - ctxBase.textures });

  /* 4) لقطات تُنشأ وتُتلَف */
  const shotHeap = await heap(pg);
  const shots = await pg.evaluate(() => {
    let created = 0, revoked = 0;
    const realCreate = URL.createObjectURL, realRevoke = URL.revokeObjectURL;
    URL.createObjectURL = function () { created++; return realCreate.apply(URL, arguments); };
    URL.revokeObjectURL = function () { revoked++; return realRevoke.apply(URL, arguments); };
    for (let i = 0; i < 20; i++) {
      const c = document.querySelector('canvas');
      if (c) c.toDataURL('image/png');
    }
    URL.createObjectURL = realCreate; URL.revokeObjectURL = realRevoke;
    return { object_urls_created: created, object_urls_revoked: revoked };
  });
  await pg.waitForTimeout(600);
  const shotHeapAfter = await heap(pg);
  results.push({ id: 'SCREENSHOT_CREATE_DISPOSE', ran: true,
    object_urls_created: shots.object_urls_created,
    object_urls_revoked: shots.object_urls_revoked,
    unrevoked_object_urls: shots.object_urls_created - shots.object_urls_revoked,
    heap_growth_pct: (shotHeap && shotHeapAfter)
      ? Math.round(10000 * (shotHeapAfter.used_js_heap_bytes
        - shotHeap.used_js_heap_bytes) / shotHeap.used_js_heap_bytes) / 100 : null });

  /* 5) VR — حيث يدعمه الجهاز فقط */
  const xr = await pg.evaluate(async () => {
    if (!navigator.xr) return { supported: false, reason: 'navigator.xr absent' };
    try {
      const ok = await navigator.xr.isSessionSupported('immersive-vr');
      return { supported: !!ok, reason: ok ? null : 'no immersive-vr device' };
    } catch (e) { return { supported: false, reason: String(e && e.message) }; }
  });
  if (!xr.supported) {
    results.push({ id: 'VR_ENTER_EXIT', ran: false,
      status: 'UNSUPPORTED — NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
      reason: xr.reason,
      note: 'A headless browser has no XR device. This scenario is reported as '
        + 'unsupported, never as a pass.' });
  } else {
    const vrBase = await gpuStats(pg);
    for (let i = 0; i < 3; i++) {
      await pg.evaluate(async () => {
        const s = await navigator.xr.requestSession('immersive-vr');
        await s.end();
      });
    }
    const vrAfter = await gpuStats(pg);
    results.push({ id: 'VR_ENTER_EXIT', ran: true,
      geometries_delta: vrAfter.geometries - vrBase.geometries,
      counters: await perfCounters(pg) });
  }
  return results;
}

/* ═════════════════════════════════ قياس التطبيق (يحتاج vendor أو هدفاً) ═══ */
async function measureApplication(browser, baseUrl, fixtures) {
  const pg = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await pg.addInitScript(instrumentationSource());
  const errs = [];
  pg.on('pageerror', e => errs.push(String(e.message).slice(0, 200)));

  const t0 = Date.now();
  await pg.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
  const firstContentMs = Date.now() - t0;
  const jsParseInitMs = await pg.evaluate(() => new Promise(res => {
    const s = performance.now();
    (function w() {
      if (typeof window.ACS === 'object') return res(performance.now());
      if (performance.now() - s > 30000) return res(null);
      setTimeout(w, 10);
    })();
  }));
  const tThree = Date.now();
  let ready = false;
  try {
    await pg.waitForFunction('window.ACS && window.ACS.ready === true', null,
      { timeout: 60000 });
    ready = true;
  } catch (e) { /* مُبلَّغ عنه أدناه */ }
  const threeInitMs = Date.now() - tThree;
  const nav = await navigationTiming(pg);

  if (!ready) {
    await pg.close();
    return { booted: false,
      status: 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
      reason: 'window.ACS.ready never became true — the 3D runtime did not '
        + 'boot (Three.js absent or failed to import). No frame was rendered, '
        + 'so nothing is measured and nothing is claimed.',
      first_content_load_ms: firstContentMs,
      js_parse_init_ms: jsParseInitMs,
      navigation_timing: nav, page_errors: errs.slice(0, 10) };
  }

  const perFixture = [];
  for (const f of fixtures) {
    const tBuild = Date.now();
    await pg.evaluate(m => window.ACS.setModel(m), f.model);
    const modelBuildMs = Date.now() - tBuild;
    const tFrame = Date.now();
    await pg.evaluate(() => new Promise(r =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
    const firstVisibleFrameMs = Date.now() - tFrame;
    await pg.waitForTimeout(400);
    const frames = await sampleFrames(pg, 5000);
    const gpu = await gpuStats(pg);
    const h1 = await heap(pg);
    /* الذاكرة بعد تحميلات متكرّرة للنموذج نفسه، ثم بعد التخلّص */
    for (let i = 0; i < 5; i++) {
      await pg.evaluate(m => window.ACS.setModel(m), f.model);
      await pg.evaluate(() => new Promise(r => requestAnimationFrame(r)));
    }
    await pg.waitForTimeout(500);
    const h2 = await heap(pg);
    const gpu2 = await gpuStats(pg);
    await pg.evaluate(() => {
      if (typeof window.ACS.disposeModel === 'function') window.ACS.disposeModel();
      else if (typeof window.ACS.setModel === 'function') window.ACS.setModel(null);
    });
    await pg.waitForTimeout(600);
    const h3 = await heap(pg);
    const gpu3 = await gpuStats(pg);
    const counters = await perfCounters(pg);
    perFixture.push({
      fixture: f.name, label: f.label, class: f.klass,
      provenance: f.provenance,
      first_content_load_ms: firstContentMs,
      js_parse_init_ms: jsParseInitMs,
      three_init_ms: threeInitMs,
      model_build_ms: modelBuildMs,
      first_visible_frame_ms: firstVisibleFrameMs,
      frames: frames,
      gpu: gpu,
      js_heap: h1,
      js_heap_after_repeated_loads: h2,
      js_heap_after_dispose: h3,
      gpu_after_repeated_loads: gpu2,
      gpu_after_dispose: gpu3,
      geometries_delta_after_dispose:
        (gpu3.geometries === null || gpu.geometries === null)
          ? null : gpu3.geometries - gpu.geometries,
      textures_delta_after_dispose:
        (gpu3.textures === null || gpu.textures === null)
          ? null : gpu3.textures - gpu.textures,
      counters: counters
    });
  }
  const leaks = await runLeakScenarios(pg, fixtures);
  const final = await perfCounters(pg);
  await pg.close();
  return { booted: true, status: 'MEASURED', navigation_timing: nav,
    fixtures: perFixture, leak_scenarios: leaks, final_counters: final,
    page_errors: errs.slice(0, 10) };
}

/* ══════════════════════════════════════════════════════════ المخرَج ═══════ */
function writeOut(obj) {
  fs.mkdirSync(OUTDIR, { recursive: true });
  fs.writeFileSync(OUTFILE, JSON.stringify(obj, null, 2) + '\n', 'utf8');
  console.log('\nwritten: ' + path.relative(ROOT, OUTFILE));
}

function printVacuity(v) {
  console.log('\n── VACUITY PROOF — the harness measured a page it can reach ──');
  if (!v || v.proved === false) {
    console.log('  NOT PROVED: ' + ((v && v.reason) || 'no result'));
    return;
  }
  console.log('  page                        : ' + v.page);
  console.log('  measurement code            : ' + v.measurement_code);
  const L = v.light_load.frames, H = v.heavy_load.frames;
  console.log('  light load (64 quads/frame) : ' + L.frames + ' frames, '
    + L.fps_average + ' fps avg, frame time p5=' + L.frame_time_p5_ms
    + ' ms p50=' + L.frame_time_p50_ms + ' ms p95=' + L.frame_time_p95_ms + ' ms');
  console.log('  heavy load (2400 quads/frm) : ' + H.frames + ' frames, '
    + H.fps_average + ' fps avg, frame time p5=' + H.frame_time_p5_ms
    + ' ms p50=' + H.frame_time_p50_ms + ' ms p95=' + H.frame_time_p95_ms + ' ms');
  console.log('  draw calls (cumulative)     : light=' + v.light_load.gpu.draw_calls
    + '  heavy=' + v.heavy_load.gpu.draw_calls
    + '  (cumulative triangles heavy=' + v.heavy_load.gpu.triangles + ')');
  console.log('  JS heap used                : '
    + (v.heap_before_alloc ? v.heap_before_alloc.used_js_heap_bytes : 'null')
    + ' B → after allocating 64 MiB → '
    + (v.heap_after_alloc_64mb ? v.heap_after_alloc_64mb.used_js_heap_bytes : 'null')
    + ' B  (delta ' + v.heap_delta_bytes + ' B)');
  console.log('  WebGL contexts / render loops / duplicate listeners : '
    + v.counters.webgl_context_count + ' / ' + v.counters.render_loop_count
    + ' / ' + v.counters.duplicate_event_listener_count);
  console.log('  sensitivity: fps falls under load='
    + v.sensitivity_checks.fps_falls_when_the_gpu_load_rises
    + ', heap rises on allocation='
    + v.sensitivity_checks.heap_rises_when_memory_is_allocated);
  console.log('  → the measurement code is REAL. It says nothing about the '
    + 'application.');
}

function notVerified(why, vacuity, extra) {
  const fixtures = allFixtures();
  const out = Object.assign({
    schema: 'acs.performance.perf/1',
    status: 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
    measured: false,
    application_measured: false,
    reason: why,
    nothing_was_measured:
      'No FPS, no frame time, no draw call, no triangle count and no memory '
      + 'figure for the ACS application appears anywhere in this file. Not one '
      + 'number was estimated, interpolated or carried over from another run.',
    budgets_source: 'tests/performance/budgets.json',
    budgets_status: BUDGETS.status,
    quality_governor_source: 'tests/performance/quality_governor.json',
    quality_governor_status: GOVERNOR.status,
    fixtures_that_would_be_measured: fixtures.map(f => ({
      name: f.name, label: f.label, class: f.klass, provenance: f.provenance,
      levels: (f.model.levels || []).length,
      rooms: Object.keys(f.model.floors || {}).reduce(
        (n, k) => n + ((f.model.floors[k].rooms || []).length), 0),
      measured: false })),
    leak_scenarios_that_would_be_run: LEAK_SCENARIOS.map(s => ({
      id: s.id, description: s.description, iterations: s.iterations,
      budget_id: s.budget_id, measured: false })),
    vacuity_proof: vacuity || null,
    exit_code: 2
  }, extra || {});
  writeOut(out);
  console.log('\n══════════════════════════════════════════════════════════');
  console.log('PERFORMANCE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  reason: ' + why);
  console.log('  ' + fixtures.length + ' fixture(s) and ' + LEAK_SCENARIOS.length
    + ' leak scenario(s) were prepared and NOT measured.');
  console.log('  Budgets in tests/performance/budgets.json are TARGETS and are '
    + 'NOT MEASURED here.');
  console.log('  exit 2 — this is not a pass and must never be counted as one.');
  process.exit(2);
}

/* ══════════════════════════════════════════════════════════ التشغيل ═══════ */
(async function () {
  console.log('ACS PERFORMANCE HARNESS (F-14) — real Chromium, real numbers or '
    + 'none at all\n');
  try { require('playwright'); }
  catch (e) { notVerified('playwright is not installed', null); }
  if (!PW.executable()) {
    notVerified('no Chromium binary is available in this sandbox and there is '
      + 'no network to download one', null);
  }

  const browser = await PW.launch({
    args: ['--enable-precise-memory-info', '--js-flags=--expose-gc',
      '--use-gl=swiftshader', '--enable-unsafe-swiftshader']
  });

  /* برهان اللاعقامة يجري دائماً وأوّلاً: بلا وجود آلة قياس مثبتة، الإعلان عن
     «غير متحقَّق» لا قيمة له. */
  let vacuity = null;
  try { vacuity = await vacuityProof(browser); }
  catch (e) { vacuity = { proved: false, reason: String(e && e.message) }; }
  printVacuity(vacuity);

  if (SELF_TEST_ONLY) {
    writeOut({ schema: 'acs.performance.perf/1',
      status: 'SELF-TEST ONLY — the application was not measured',
      measured: false, application_measured: false,
      vacuity_proof: vacuity, exit_code: vacuity && vacuity.proved ? 0 : 1 });
    await browser.close();
    process.exit(vacuity && vacuity.proved ? 0 : 1);
  }

  /* هل يمكن قياس التطبيق أصلاً؟ */
  const three = path.join(PUB, 'vendor', 'three@0.160.0', 'build',
    'three.module.js');
  if (!TARGET && (!fs.existsSync(three) || fs.statSync(three).size < 100000)) {
    await browser.close();
    notVerified('public/vendor is empty: the vendored Three.js runtime '
      + '(three@0.160.0 + addons) is absent and this sandbox has no network, '
      + 'so the 3D runtime cannot boot and no frame can be rendered. Run '
      + '`sh tools/vendor.sh` on a networked machine, or pass --target <url> '
      + 'to measure the deployment.', vacuity);
  }

  const srv = TARGET ? null : await serve(PUB);
  const baseUrl = TARGET
    || ('http://127.0.0.1:' + srv.address().port + '/index.html');
  const fixtures = allFixtures();
  console.log('\n── measuring the application at ' + baseUrl + ' ──');
  const app = await measureApplication(browser, baseUrl, fixtures);
  await browser.close();
  if (srv) srv.close();

  if (!app.booted) {
    notVerified(app.reason, vacuity, { application_boot_attempt: app });
  }

  app.fixtures.forEach(r => {
    console.log('  ' + r.fixture.padEnd(24)
      + String(r.frames.fps_average).padEnd(9)
      + 'p95=' + String(r.frames.frame_time_p95_ms).padEnd(9)
      + 'calls=' + String(r.gpu.draw_calls).padEnd(8)
      + 'tris=' + r.gpu.triangles);
  });
  writeOut({ schema: 'acs.performance.perf/1', status: 'MEASURED',
    measured: true, application_measured: true, target: baseUrl,
    budgets_source: 'tests/performance/budgets.json',
    quality_governor_source: 'tests/performance/quality_governor.json',
    vacuity_proof: vacuity, application: app, exit_code: 0 });
  console.log('\nPERFORMANCE: MEASURED');
  process.exit(0);
})().catch(e => {
  console.error('PERFORMANCE HARNESS FAILED: ' + (e && e.stack || e));
  process.exit(1);
});
