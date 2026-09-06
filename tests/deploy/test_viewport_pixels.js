/* ============================================================================
   اختبارات محلّل بكسلات نافذة العرض — موجبة وسالبة، في متصفّح حقيقي.

   هذا هو الفحص الذي كان زائفاً: كان يقيس حجم PNG وتنوّع بايتاته، فيمرّ على
   واجهة ملوّنة فوق نافذة عرض سوداء. هنا تُرسم مشاهد اصطناعية محدّدة في
   Chromium حقيقي وتُفكّ بكسلاتها فعلاً، ويُتحقّق من الحكم في كل حالة:

     · كانفس أسود تماماً                       ⇒ يجب أن يفشل
     · واجهة ملوّنة فوق كانفس أسود              ⇒ يجب أن يفشل (البكسلات من
       مستطيل الكانفس وحده، فلا ينقذه شريط الأدوات)
     · إطار داكن شبه موحّد (#010203)            ⇒ يجب أن يفشل
     · مشهد ليلي داكن لكن فيه هندسة مضاءة        ⇒ يجب أن ينجح
     · مشهد نهاري كامل                          ⇒ يجب أن ينجح
     · إطار من WebGL حقيقي (بلا Three.js)        ⇒ يجب أن ينجح
   ========================================================================== */
const path = require('path');
const PX = require(path.join(__dirname, 'lib_viewport_pixels.js'));
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js).
   كان هذا الملفّ يخبز executablePath:'/opt/pw-browsers/chromium' — مسار
   صورة هذا الصندوق — فكان يفشل في GitHub Actions حيث لا وجود لذلك المسار
   أصلاً، والثنائيّة المُدارة التي نزّلها `playwright install` تنتظر بلا
   مستعمل. المُحدِّد يسأل Playwright عن ثنائيّتها أوّلاً، ولا يبلغ جذر
   الصورة إلا حين تعجز — أي في صندوقٍ بلا شبكة. */
const PW = require(path.resolve(__dirname, '..', '..', 'tools', 'pw_chromium.js'));
let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
  : (fail++, console.log('  ✗', n, d === undefined ? '' : d)); };

/* ---------------------------- 1) وحدات المحلّل بلا متصفّح ---------------- */
console.log('\n== ANALYSER UNIT BEHAVIOUR ==');
function frame(w, h, fn) {
  const a = new Uint8Array(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const c = fn(x, y, w, h); const i = (y * w + x) * 4;
    a[i] = c[0]; a[i + 1] = c[1]; a[i + 2] = c[2]; a[i + 3] = 255;
  }
  return a;
}
const W = 64, H = 36;
const black = PX.analyse(frame(W, H, () => [0, 0, 0]), W, H);
chk('a fully black frame is EFFECTIVELY_BLACK',
  black.verdict === 'EFFECTIVELY_BLACK'
  && black.near_black_pct === 100, JSON.stringify(black.reasons));
const nearlyBlack = PX.analyse(frame(W, H, () => [1, 2, 3]), W, H);
chk('a uniform very dark frame (#010203) is EFFECTIVELY_BLACK',
  nearlyBlack.verdict === 'EFFECTIVELY_BLACK',
  JSON.stringify(nearlyBlack.reasons));
const oneBright = PX.analyse(frame(W, H,
  (x, y) => (x === 0 && y === 0) ? [255, 255, 255] : [0, 0, 0]), W, H);
chk('a black frame with a single bright pixel is still EFFECTIVELY_BLACK',
  oneBright.verdict === 'EFFECTIVELY_BLACK',
  JSON.stringify(oneBright.reasons));
const night = PX.analyse(frame(W, H, (x, y, w, h) => {
  const sky = 6 + Math.round(4 * (y / h));
  if (y > h * 0.45 && x > w * 0.2 && x < w * 0.8) {
    const lit = (Math.floor(x / 4) % 3 === 0) ? 92 : 34;
    return [lit, lit - 6, lit - 14];
  }
  return [sky, sky + 1, sky + 5];
}), W, H);
chk('a dark NIGHT scene that still has lit geometry is VISIBLE_CONTENT',
  night.verdict === 'VISIBLE_CONTENT',
  JSON.stringify(night.reasons) + ' mean=' + night.luminance_mean);
const day = PX.analyse(frame(W, H, (x, y, w, h) =>
  y < h * 0.4 ? [140, 175, 220] : [90, 88, 84]), W, H);
chk('an ordinary daylight frame is VISIBLE_CONTENT',
  day.verdict === 'VISIBLE_CONTENT', JSON.stringify(day.reasons));
chk('an empty buffer is refused rather than passed',
  PX.analyse(new Uint8Array(0), 0, 0).valid === false);
chk('a tiny sample is refused as insufficient evidence',
  PX.analyse(frame(8, 8, () => [200, 200, 200]), 8, 8)
    .reasons.indexOf('TOO_FEW_SAMPLES') >= 0);
chk('the thresholds are reported with every verdict (explainable)',
  day.thresholds.near_black_luminance === 8
  && day.thresholds.max_near_black_pct === 98.5);

/* ------------------------- 2) في متصفّح حقيقي عبر الصفحة ---------------- */
(async () => {
  try { require('playwright'); }
  catch (e) {
    console.log('\n(browser fixtures need playwright — NOT VERIFIED here)');
    finish(); return;
  }
  const b = await PW.launch();
  const pg = await b.newPage({ viewport: { width: 900, height: 600 } });
  const fixtureErrors = [];
  pg.on('pageerror', e => fixtureErrors.push(String(e.message).slice(0, 120)));

  const page = (canvasPainter, withUi) => `<!doctype html><meta charset=utf-8>
    <style>body{margin:0;background:#101418}
      #bar{position:fixed;top:0;left:0;right:0;height:64px;
        background:linear-gradient(90deg,#e63946,#f1faee,#457b9d);
        color:#fff;font:20px sans-serif;padding:8px}
      #side{position:fixed;top:64px;left:0;width:220px;bottom:0;
        background:#22303c;color:#eee;font:14px sans-serif;padding:10px}
      canvas{position:fixed;top:64px;left:220px;right:0;bottom:0;
        width:calc(100vw - 220px);height:calc(100vh - 64px)}</style>
    ${withUi ? '<div id=bar>ACS TOOLBAR — ألوان زاهية</div><div id=side>لوحة جانبية<br>عناصر<br>طبقات</div>' : ''}
    <canvas id=c width=640 height=360></canvas>
    <script>(function(){                       /* IIFE: لا تسريب معرّفات بين
        التجهيزات — إعلان عام مكرّر كان يُفشل السكربت فيبدو الإطار «أسود» زوراً */
      var cv=document.getElementById('c');
      var x=cv.getContext('2d');
      (${canvasPainter})(x,cv.width,cv.height);
      window.__PAINTED__=true; })();<\/script>`;

  async function verdictFor(html) {
    fixtureErrors.length = 0;
    await pg.goto('about:blank');            /* سياق نظيف لكل تجهيزة */
    await pg.setContent(html, { waitUntil: 'load' });
    const painted = await pg.evaluate('window.__PAINTED__===true');
    const v = await PX.analysePageViewport(pg, '#c');
    /* لو لم يُرسم المشهد أصلاً لظهر «أسود» زوراً — تُرفض النتيجة صراحةً */
    v.fixture_painted = painted;
    v.fixture_errors = fixtureErrors.slice();
    return v;
  }

  console.log('\n== REAL BROWSER FIXTURES (canvas rect only) ==');
  const blackPage = await verdictFor(page(
    "(x,w,h)=>{x.fillStyle='#000';x.fillRect(0,0,w,h);}", false));
  chk('a black canvas in a real page FAILS',
    blackPage.verdict === 'EFFECTIVELY_BLACK',
    JSON.stringify(blackPage.reasons));
  const uiOverBlack = await verdictFor(page(
    "(x,w,h)=>{x.fillStyle='#000';x.fillRect(0,0,w,h);}", true));
  chk('a BRIGHT UI over a black viewport still FAILS — the exact false pass '
    + 'the old byte-size heuristic produced',
    uiOverBlack.verdict === 'EFFECTIVELY_BLACK',
    JSON.stringify(uiOverBlack.reasons));
  const dim = await verdictFor(page(
    "(x,w,h)=>{x.fillStyle='#010203';x.fillRect(0,0,w,h);}", true));
  chk('a nearly uniform dark viewport under a bright UI FAILS',
    dim.verdict === 'EFFECTIVELY_BLACK', JSON.stringify(dim.reasons));
  const model = await verdictFor(page(`(x,w,h)=>{
      const g=x.createLinearGradient(0,0,0,h);
      g.addColorStop(0,'#6fa8dc'); g.addColorStop(1,'#cfe2f3');
      x.fillStyle=g; x.fillRect(0,0,w,h);
      x.fillStyle='#8d8d86'; x.fillRect(w*0.25,h*0.35,w*0.5,h*0.45);
      x.fillStyle='#5b5b55'; x.fillRect(w*0.25,h*0.35,w*0.5,h*0.05);
      x.fillStyle='#2b3a45';
      for(let i=0;i<6;i++) x.fillRect(w*0.30+i*w*0.07,h*0.45,w*0.04,h*0.10);
    }`, true));
  chk('a rendered building over sky PASSES',
    model.verdict === 'VISIBLE_CONTENT',
    JSON.stringify(model.reasons) + ' mean=' + model.luminance_mean);
  const nightModel = await verdictFor(page(`(x,w,h)=>{
      x.fillStyle='#04060a'; x.fillRect(0,0,w,h);
      x.fillStyle='#17202b'; x.fillRect(w*0.25,h*0.35,w*0.5,h*0.45);
      x.fillStyle='#ffd9a0';
      for(let i=0;i<8;i++)
        x.fillRect(w*0.28+i*w*0.055,h*0.42+((i%2)*h*0.12),w*0.03,h*0.05);
    }`, true));
  chk('a legitimate NIGHT presentation with lit windows PASSES',
    nightModel.verdict === 'VISIBLE_CONTENT',
    JSON.stringify(nightModel.reasons) + ' mean='
    + nightModel.luminance_mean);
  chk('every fixture actually painted and raised no page error — a broken '
    + 'fixture can never masquerade as a black viewport',
    [blackPage, uiOverBlack, dim, model, nightModel]
      .every(v => v.fixture_painted === true && v.fixture_errors.length === 0),
    JSON.stringify([blackPage, uiOverBlack, dim, model, nightModel]
      .map(v => [v.fixture_painted, v.fixture_errors])));
  chk('the sample really came from the canvas rect, not the whole page',
    model.canvas_size.width === 640 && model.canvas_size.height === 360
    && model.sampled >= 1024, JSON.stringify(model.canvas_size));

  /* WebGL حقيقي — بلا Three.js — يثبت أن المسار يعمل على إطار GPU فعلي */
  await pg.setContent(`<!doctype html><meta charset=utf-8>
    <canvas id=c width=640 height=360></canvas><script>
    const O={preserveDrawingBuffer:true};
    const gl=document.getElementById('c').getContext('webgl2',O)
      ||document.getElementById('c').getContext('webgl',O);
    window.__GL__=!!gl;
    if(gl){ gl.clearColor(0.34,0.55,0.78,1); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.SCISSOR_TEST);
      gl.scissor(120,60,400,200); gl.clearColor(0.62,0.60,0.55,1);
      gl.clear(gl.COLOR_BUFFER_BIT); gl.disable(gl.SCISSOR_TEST); }
    <\/script>`, { waitUntil: 'load' });
  const hasGl = await pg.evaluate('window.__GL__');
  if (hasGl) {
    const glShot = await PX.analysePageViewport(pg, '#c');
    chk('an actual WebGL frame with drawn content PASSES',
      glShot.verdict === 'VISIBLE_CONTENT',
      JSON.stringify(glShot.reasons));
    await pg.evaluate(`(()=>{const O={preserveDrawingBuffer:true};
      const gl=document.getElementById('c').getContext('webgl2',O)
        ||document.getElementById('c').getContext('webgl',O);
      gl.clearColor(0,0,0,1); gl.clear(gl.COLOR_BUFFER_BIT);})()`);
    const glBlack = await PX.analysePageViewport(pg, '#c');
    chk('an actual WebGL frame cleared to black FAILS',
      glBlack.verdict === 'EFFECTIVELY_BLACK',
      JSON.stringify(glBlack.reasons));
    /* §C — الانحدار المطلوب حرفياً: كانفس WebGL أسود + شريط أدوات ظاهر
       يجب أن يفشل. هذا هو شكل العطل الإنتاجي بالضبط: المستخدم يرى واجهة
       سليمة ونافذة عرض سوداء، والفحص القديم كان يمرّ لأن بكسلات الواجهة
       دخلت العيّنة. هنا لا تدخل: العيّنة من مستطيل الكانفس وحده. */
    await pg.setContent(`<!doctype html><meta charset=utf-8>
      <style>body{margin:0;background:#101418}
        #bar{position:fixed;top:0;left:0;right:0;height:64px;
          background:linear-gradient(90deg,#e63946,#f1faee,#457b9d);
          color:#fff;font:20px sans-serif;padding:8px}
        #side{position:fixed;top:64px;left:0;width:220px;bottom:0;
          background:#22303c;color:#eee;font:14px sans-serif;padding:10px}
        canvas{position:fixed;top:64px;left:220px;right:0;bottom:0;
          width:calc(100vw - 220px);height:calc(100vh - 64px)}</style>
      <div id=bar>ACS TOOLBAR — شريط أدوات ظاهر وملوّن</div>
      <div id=side>لوحة جانبية<br>طبقات<br>عناصر<br>تصدير</div>
      <canvas id=c width=640 height=360></canvas><script>(function(){
        var O={preserveDrawingBuffer:true};
        var cv=document.getElementById('c');
        var gl=cv.getContext('webgl2',O)||cv.getContext('webgl',O);
        window.__GL__=!!gl;
        if(gl){ gl.clearColor(0,0,0,1); gl.clear(gl.COLOR_BUFFER_BIT); }
        window.__PAINTED__=true; })();<\/script>`,
      { waitUntil: 'load' });
    const blackGlWithUi = await PX.analysePageViewport(pg, '#c');
    const uiVisible = await pg.evaluate(() => {
      const b = document.getElementById('bar');
      const s = document.getElementById('side');
      return !!b && !!s && getComputedStyle(b).display !== 'none'
        && b.getBoundingClientRect().height > 20
        && s.getBoundingClientRect().width > 100;
    });
    chk('the bright toolbar and sidebar really are visible in that fixture',
      uiVisible === true);
    chk('§C REGRESSION — black WebGL canvas + visible toolbar = FAIL',
      blackGlWithUi.verdict === 'EFFECTIVELY_BLACK'
      && blackGlWithUi.near_black_pct === 100
      && blackGlWithUi.non_background_pct === 0,
      JSON.stringify({ verdict: blackGlWithUi.verdict,
        reasons: blackGlWithUi.reasons,
        near_black: blackGlWithUi.near_black_pct,
        non_background: blackGlWithUi.non_background_pct,
        mean: blackGlWithUi.luminance_mean,
        variance: blackGlWithUi.luminance_variance }));
    chk('the UI pixels contributed nothing — the sample is canvas-only',
      blackGlWithUi.canvas_size.width === 640
      && blackGlWithUi.luminance_max === 0,
      'max_luminance=' + blackGlWithUi.luminance_max);
  } else {
    console.log('  · no WebGL context in this browser build: '
      + 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  }
  await b.close();
  finish();
})().catch(e => { console.log('  ✗ browser fixture error', String(e.message)
  .slice(0, 200)); fail++; finish(); });

function finish() {
  console.log('\n──────────────────────────────────────────────');
  console.log('VIEWPORT PIXEL TEST: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}
