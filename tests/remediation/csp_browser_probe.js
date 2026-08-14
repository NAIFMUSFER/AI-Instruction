/* ============================================================================
   F-11 — قياس سياسة المحتوى في Chromium حقيقي، لا استنتاجها من النصّ.

     node tests/remediation/csp_browser_probe.js

   يخدم public/ من 127.0.0.1 عبر tools/csp_static_server.py (صنف فرعي يضع
   الترويسة نفسها التي تضعها Netlify — لا <meta>، لأن meta لا يطبّق
   frame-ancestors ولا يمثّل ما يُنشر)، ثم يحمّل الصفحة المشحونة مرّتين:

     CURRENT   — السياسة المنشورة اليوم حرفياً من netlify.toml.
     HARDENED  — نفس السياسة بلا 'unsafe-inline' وبلا 'unsafe-eval'.

   في كل مرّة يُسجَّل: كل حدث securitypolicyviolation، وكل خطأ صفحة، وكل رسالة
   console، وهل نُفِّذ سكربت مضمَّن معادٍ حُقِن عمداً، وهل نُفِّذ eval() معادٍ.

   تحت السياسة الحالية سينفّذان — وهذا يُسجَّل سطراً بعنوان KNOWN-WEAKNESS، لا
   «نجاحاً». الفرق بين القياسين هو الدليل الذي تقوم عليه خطة الترحيل في
   CSP-HARDENING.md.

   بلا Three.js مُعبَّأ لا يكتمل إقلاع الوحدة — وهذا لا يُخفى: يُسجَّل صراحةً
   وتبقى كل نتيجة تعتمد على إطار مرسوم NOT VERIFIED — EXTERNAL ENVIRONMENT
   REQUIRED. مخالفات CSP نفسها لا تحتاج إطاراً مرسوماً: المتصفّح يقرّرها عند
   التحليل والتنفيذ، فهي مقيسة فعلاً هنا.
   ========================================================================== */
const fs = require('fs'), path = require('path'), net = require('net');
const { spawn } = require('child_process');
const PW = require(require('path').resolve(__dirname, '..', '..', 'tools', 'pw_chromium.js'));

const HERE = __dirname, ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const OUTDIR = path.join(HERE, 'outputs');
const OUTFILE = path.join(OUTDIR, 'csp_probe.json');

/* ------------------------------------------------- السياسة من ملف النشر --- */
function currentCSP() {
  const nt = fs.readFileSync(path.join(ROOT, 'netlify.toml'), 'utf8');
  const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
  if (!m) throw new Error('netlify.toml declares no Content-Security-Policy');
  return m[1];
}
/* السياسة التجريبية المشدَّدة: حذف 'unsafe-inline' و'unsafe-eval' فقط.
   لا شيء آخر يتغيّر — حتى يكون الفرق المقيس منسوباً إليهما وحدهما. */
function hardenedCSP(csp) {
  return csp.split(';').map(function (d) {
    return d.split(/\s+/).filter(function (t) {
      return t !== "'unsafe-inline'" && t !== "'unsafe-eval'";
    }).join(' ').trim();
  }).filter(Boolean).join('; ');
}

function freePort() {
  return new Promise(function (res, rej) {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', function () {
      const p = s.address().port; s.close(function () { res(p); });
    });
    s.on('error', rej);
  });
}

function serve(port, csp) {
  return new Promise(function (res, rej) {
    const p = spawn('python3',
      [path.join(ROOT, 'tools', 'csp_static_server.py'), String(port), PUB, csp],
      { cwd: ROOT, stdio: ['ignore', 'ignore', 'pipe'] });
    let buf = '';
    const to = setTimeout(function () { rej(new Error('server did not start')); },
      15000);
    p.stderr.on('data', function (d) {
      buf += String(d);
      if (buf.indexOf('CSP_SERVER_READY') >= 0) { clearTimeout(to); res(p); }
    });
    p.on('exit', function (c) { clearTimeout(to); rej(new Error('server exited ' + c)); });
  });
}

function notVerified(why) {
  console.log('\nCSP BROWSER PROBE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  reason: ' + why);
  try {
    fs.mkdirSync(OUTDIR, { recursive: true });
    fs.writeFileSync(OUTFILE, JSON.stringify({
      status: 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
      reason: why, measured: false, generated_at_utc: new Date().toISOString()
    }, null, 2) + '\n', 'utf8');
  } catch (e) { /* لا شيء يُدَّعى */ }
  process.exit(2);
}

/* ------------------------------------------------------ قياس سياسة واحدة --- */
async function measure(label, csp) {
  const port = await freePort();
  const srv = await serve(port, csp);
  const base = 'http://127.0.0.1:' + port + '/index.html';
  const b = await PW.launch();
  const pg = await b.newPage({ viewport: { width: 1280, height: 800 } });

  const pageErrors = [], consoleErrors = [], failedReqs = [];
  /* المستمع يُركَّب قبل أي تنقّل، وداخل الصفحة نفسها، فيلتقط مخالفات التحليل
     المبكّرة أيضاً (سكربتات <head> تُحلَّل قبل أن ينفَّذ أي شيء آخر). */
  await pg.addInitScript(function () {
    window.__CSP_VIOLATIONS__ = [];
    document.addEventListener('securitypolicyviolation', function (e) {
      window.__CSP_VIOLATIONS__.push({
        directive: e.effectiveDirective || e.violatedDirective,
        blocked: String(e.blockedURI || '').slice(0, 120),
        sample: String(e.sample || '').slice(0, 90),
        line: e.lineNumber || null,
        disposition: e.disposition || null
      });
    });
  });
  pg.on('pageerror', function (e) { pageErrors.push(String(e.message).slice(0, 200)); });
  pg.on('console', function (m) {
    if (m.type() === 'error') consoleErrors.push(String(m.text()).slice(0, 220));
  });
  pg.on('requestfailed', function (r) {
    failedReqs.push(r.url().slice(0, 120) + ' :: '
      + ((r.failure() || {}).errorText || '?'));
  });

  let loaded = true, loadError = null;
  try { await pg.goto(base, { waitUntil: 'load', timeout: 60000 }); }
  catch (e) { loaded = false; loadError = String(e.message).slice(0, 160); }
  await pg.waitForTimeout(1500);

  /* هل نفّذت سكربتات الصفحة المضمَّنة أصلاً؟ window.ACS يُعرَّف في سكربت
     كلاسيكي مضمَّن — وجوده دليل تنفيذ المضمَّن، وغيابه دليل حجبه. */
  const appInline = await pg.evaluate(function () {
    return { acs_object_defined: typeof window.ACS === 'object' && window.ACS !== null,
             acs_ready: !!(window.ACS && window.ACS.ready) };
  });

  /* ---- الحقن المعادي: سكربت مضمَّن، ثم سكربت خارجي من نفس الأصل يجرّب eval --- */
  await pg.evaluate(function () {
    window.__HOSTILE_INLINE__ = false;
    const s = document.createElement('script');
    /* لا يُستعمل eval هنا: هذا اختبار 'unsafe-inline' وحده. */
    s.textContent = 'window.__HOSTILE_INLINE__ = true;'
      + 'window.__HOSTILE_INLINE_MARK__ = document.title.length;';
    document.head.appendChild(s);
  });
  await pg.waitForTimeout(200);
  await pg.evaluate(function () {
    return new Promise(function (res) {
      const s = document.createElement('script');
      s.src = '/__csp_probe__/hostile.js';
      s.onload = function () { res(); };
      s.onerror = function () { res(); };
      document.head.appendChild(s);
      setTimeout(res, 3000);
    });
  });
  await pg.waitForTimeout(400);

  const hostile = await pg.evaluate(function () {
    return {
      inline_executed: window.__HOSTILE_INLINE__ === true,
      external: window.__CSP_PROBE_EXTERNAL__ || null
    };
  });
  const vio = await pg.evaluate(function () { return window.__CSP_VIOLATIONS__ || []; });

  await b.close();
  srv.kill();

  /* تجميع المخالفات حسب التوجيه — الرقم الذي يُقارَن بين السياستين */
  const byDirective = {}, linesByDirective = {};
  vio.forEach(function (v) {
    byDirective[v.directive] = (byDirective[v.directive] || 0) + 1;
    const L = linesByDirective[v.directive] || (linesByDirective[v.directive] = []);
    if (L.indexOf(v.line) < 0) L.push(v.line);
  });
  Object.keys(linesByDirective).forEach(function (k) {
    linesByDirective[k].sort(function (a, b) { return (a || 0) - (b || 0); });
  });

  return {
    label: label,
    csp: csp,
    page_loaded: loaded,
    load_error: loadError,
    violations_total: vio.length,
    violations_by_directive: byDirective,
    distinct_source_lines_by_directive: linesByDirective,
    violations: vio.slice(0, 300),
    page_errors: pageErrors.slice(0, 20),
    page_error_count: pageErrors.length,
    console_errors: consoleErrors.slice(0, 20),
    console_error_count: consoleErrors.length,
    failed_requests: failedReqs.slice(0, 20),
    failed_request_count: failedReqs.length,
    application_inline_scripts_executed: appInline.acs_object_defined,
    application_ready: appInline.acs_ready,
    hostile_inline_executed: hostile.inline_executed,
    hostile_external_script_ran: !!(hostile.external
      && hostile.external.external_script_ran),
    hostile_eval_executed: hostile.external ? hostile.external.eval_ran : null,
    hostile_function_ctor_executed: hostile.external
      ? hostile.external.function_ctor_ran : null,
    hostile_eval_error: hostile.external ? hostile.external.eval_error : null
  };
}

(async function () {
  try { require('playwright'); }
  catch (e) { notVerified('playwright is not installed'); }
  if (!PW.executable()) {
    notVerified('no Chromium binary is available (playwright expects a build '
      + 'that is not present and there is no network to download it)');
  }

  const CUR = currentCSP();
  const HARD = hardenedCSP(CUR);
  console.log('CSP BROWSER PROBE — real Chromium, real response header\n');
  console.log('CURRENT  : ' + CUR + '\n');
  console.log('HARDENED : ' + HARD + '\n');

  const vendorPresent = fs.existsSync(path.join(PUB, 'vendor',
    'three@0.160.0', 'build', 'three.module.js'));
  if (!vendorPresent) {
    console.log('NOTE: public/vendor is empty in this checkout — the ES module '
      + 'graph cannot resolve `three`, so the 3D runtime never boots and NO '
      + 'FRAME IS RENDERED. Everything below that depends on a rendered frame '
      + 'is NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED. CSP decisions '
      + 'themselves are decided by the browser at parse/execute time and ARE '
      + 'measured here.\n');
  }

  const results = [];
  for (const [label, csp] of [['CURRENT', CUR], ['HARDENED_TRIAL', HARD]]) {
    console.log('── measuring ' + label + ' ──');
    const r = await measure(label, csp);
    results.push(r);
    console.log('  page loaded                       : ' + r.page_loaded);
    console.log('  CSP violations (total)            : ' + r.violations_total);
    console.log('  CSP violations by directive       : '
      + JSON.stringify(r.violations_by_directive));
    console.log('  distinct source lines per directive: '
      + JSON.stringify(r.distinct_source_lines_by_directive));
    console.log('  page errors                       : ' + r.page_error_count);
    console.log('  console errors                    : ' + r.console_error_count);
    console.log('  failed requests                   : ' + r.failed_request_count);
    console.log('  application inline scripts ran    : '
      + r.application_inline_scripts_executed);
    console.log('  hostile INLINE script executed    : ' + r.hostile_inline_executed);
    console.log('  hostile external script loaded    : ' + r.hostile_external_script_ran);
    console.log('  hostile eval() executed           : ' + r.hostile_eval_executed);
    console.log('  hostile new Function() executed   : ' + r.hostile_function_ctor_executed);
    console.log('');
  }

  const cur = results[0], hard = results[1];
  const weaknesses = [];
  if (cur.hostile_inline_executed) {
    weaknesses.push("KNOWN-WEAKNESS · CSP-INLINE-EXEC · script-src 'unsafe-inline' "
      + 'is present, and a hostile inline <script> injected into the live page '
      + 'EXECUTED under the deployed policy (measured, not assumed). Any XSS '
      + 'sink in the application is therefore directly exploitable. Tracked in '
      + 'CSP-HARDENING.md; removal is blocked on F-09.');
  }
  if (cur.hostile_eval_executed === true) {
    weaknesses.push("KNOWN-WEAKNESS · CSP-EVAL-EXEC · script-src 'unsafe-eval' "
      + 'is present, and a hostile eval() called from same-origin page code '
      + 'EXECUTED under the deployed policy (measured, not assumed). Tracked in '
      + 'CSP-HARDENING.md; removal requires dropping es-module-shims, which '
      + 'drops iOS Safari < 16.4.');
  }
  if (cur.hostile_function_ctor_executed === true) {
    weaknesses.push('KNOWN-WEAKNESS · CSP-FUNCTION-CTOR · new Function() '
      + 'EXECUTED under the deployed policy (same root cause as CSP-EVAL-EXEC).');
  }

  console.log('── the difference the hardened policy makes ──');
  console.log('  violations   CURRENT=' + cur.violations_total
    + '  HARDENED=' + hard.violations_total
    + '   (delta ' + (hard.violations_total - cur.violations_total) + ')');
  console.log('  hostile inline executed   CURRENT=' + cur.hostile_inline_executed
    + '  HARDENED=' + hard.hostile_inline_executed);
  console.log('  hostile eval executed     CURRENT=' + cur.hostile_eval_executed
    + '  HARDENED=' + hard.hostile_eval_executed);
  console.log('  application inline ran    CURRENT='
    + cur.application_inline_scripts_executed + '  HARDENED='
    + hard.application_inline_scripts_executed
    + '   ← this is exactly what breaks: the whole application is inline');
  console.log('');
  weaknesses.forEach(function (w) { console.log(w + '\n'); });
  if (!weaknesses.length) {
    console.log('no inline/eval weakness measured under the deployed policy.\n');
  }

  fs.mkdirSync(OUTDIR, { recursive: true });
  const out = {
    status: 'MEASURED',
    generated_at_utc: new Date().toISOString(),
    chromium: 'playwright ' + require('playwright/package.json').version,
    vendor_present: vendorPresent,
    frame_rendered: false,
    frame_rendered_note: vendorPresent ? 'vendor present but no frame was '
      + 'asserted by this probe' : 'NOT VERIFIED — EXTERNAL ENVIRONMENT '
      + 'REQUIRED: public/vendor is empty, Three.js cannot load, no frame can '
      + 'be rendered in this sandbox',
    current_policy: CUR,
    hardened_trial_policy: HARD,
    results: results,
    known_weaknesses: weaknesses,
    hardening_status: 'NOT COMPLETE — F-09 (frontend modularisation) is a '
      + 'prerequisite for removing script-src \'unsafe-inline\''
  };
  fs.writeFileSync(OUTFILE, JSON.stringify(out, null, 2) + '\n', 'utf8');
  console.log('written: ' + path.relative(ROOT, OUTFILE));
  console.log('\nCSP BROWSER PROBE: MEASURED (weaknesses are recorded, not passed)');
})().catch(function (e) {
  console.error('CSP BROWSER PROBE FAILED: ' + (e && e.stack || e));
  process.exit(1);
});
