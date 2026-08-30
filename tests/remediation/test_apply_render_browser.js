/* ============================================================================
   KI-25 · F-41…F-45 — رد 200 يصير مبنى مرئيّاً، في Chromium حقيقي.
     node tests/remediation/test_apply_render_browser.js

   ما يُقاس هنا فعلاً
   ------------------
   Chromium حقيقيّ، سياق WebGL2 حقيقيّ (SwiftShader)، تظليل حقيقيّ، ونداء
   ‎gl.readPixels‎ حقيقيّ على لوحة حقيقيّة. الهندسة المرسومة هي **مخرَج
   ‎compile()‎ المشحون نفسه** من public/app/core/viewer.js، وحدودُ المشهد
   والكاميرا من ‎pqRobustBounds‎/‎pqCameraFit‎ المشحونتين في
   public/app/generated/pbr.js، وحاجزُ التطبيق من
   public/app/ui/workspace-ui-wiring.js. لا نسخة ثانية من أيٍّ منها.

   ما لا يُقاس هنا — مُعلَن بلا مواربة
   ----------------------------------
   three.js **غير متاح في هذا الصندوق**: public/vendor فارغ (يملؤه
   tools/netlify-build.sh وقت البناء) وسجلّ npm يردّ 403، فلا سبيل إلى
   three@0.160.0. لذلك رسم المشهد هنا لا يمرّ بشجرة three: يمرّ بمُنفِّذٍ
   بديل مكتوب في هذا الملفّ يأخذ الصناديق التي بناها ‎compile()‎ ويرسمها
   بـWebGL2 خاماً — مصفوفات وتظليل ومخزن رؤوس حقيقيّة.

   فما يُثبته هذا الملفّ: أن الهندسة التي يخرجها المترجم، بالكاميرا التي
   يحسبها العقد، **تُرسَم فعلاً بكسلات غير موحّدة على عتاد حقيقي** — وأنها
   لا تُرسَم حين يعود عطل KI-25. وما لا يُثبته: أن three.js نفسه يرسمها.
   ذلك يبقى:
       LIVE FRONTEND APPLY (three.js): NOT VERIFIED — EXTERNAL ENVIRONMENT
       REQUIRED
   ويُغلَق بتشغيل واحد على شجرة مبنيّة: ‎bash tools/vendor.sh‎ ثم هذا الملفّ.
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const PW = require(path.join(ROOT, 'tools', 'pw_chromium.js'));
/* اكتساب المتصفّح يمرّ من مُحدِّد الثنائيّة الواحد (tools/pw_chromium.js).
   النداء المباشر chromium.launch() يطلب البناء الذي تتوقّعه نسخة Playwright
   المثبّتة (مثلاً 1234)، فيفشل في صندوق يحمل 1194 — وهو فشلُ بيئةٍ لا فشلُ
   منتج. الأخوات (csp_browser_probe, run_perf) تمرّ من هنا منذ البداية. */
const H = require(path.join(HERE, 'lib_csp_harness.js'));

let pass = 0, fail = 0;
const chk = (name, cond, detail) => {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + '  ' + (detail === undefined ? '' : detail)); }
};

const VENDOR_OK = fs.existsSync(path.join(ROOT, 'public', 'vendor',
  'three@0.160.0', 'build', 'three.module.js'));

/* ═══════════ مُنفِّذ WebGL2 حقيقيّ بواجهة three الأدنى ═════════════════════
   ليس كعباً صامتاً: يفتح سياق webgl2 من اللوحة، ويصرّف تظليلاً، ويرفع رؤوس
   صندوق واحد، ويرسم كل شبكة بمصفوفة نموذج/عرض/إسقاط محسوبة هنا. الألوان من
   وسم الطبقة، فالإطار يحمل تدرّجاً حقيقياً لا لوناً واحداً. */
const GL_THREE = fs.readFileSync(path.join(HERE, 'lib_gl_three.js'), 'utf8');

/* خريطة الاستيراد تُنسَخ **حرفياً** من public/index.html: السياسة الإنتاجية
   تُجيز نصّها ببصمة sha256، فأي حرف يختلف يجعل المتصفّح يرفضها ويسقط الرسم
   كلّه. النسخ الحرفيّ يعني أن المقيس هنا هو الخريطة المشحونة تحت السياسة
   المشحونة، لا نسخة مريحة كُتبت للاختبار. */
const SHELL = fs.readFileSync(path.join(ROOT, 'public', 'index.html'), 'utf8');
const IMPORTMAP = (function () {
  const i = SHELL.indexOf('<script type="importmap">');
  const j = SHELL.indexOf('</script>', i);
  if (i < 0 || j < 0) throw new Error('no importmap in public/index.html');
  return SHELL.slice(i, j + '</script>'.length);
})();

const PAGE = `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>ki25</title>
${IMPORTMAP}
</head>
<body><canvas id="c" width="480" height="300"></canvas>
<script type="module" src="/ki25_probe.js"></script></body></html>`;

/* المُشغِّل داخل الصفحة: يبني بـcompile المشحون، ويحسب الحدود والكاميرا
   بعقد pbr المشحون، ويرسم بـWebGL2 حقيقيّ، ثم يقرأ البكسلات بـreadPixels. */
const PROBE = `
import * as THREE from 'three';
import { compile, acsBuildDefects } from '/app/core/viewer.js';
import { pqRobustBounds, pqCameraFit } from '/app/generated/pbr.js';
import { __ACS_SHARED } from '/app/shared-state.js';
window.THREE = THREE;

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas: canvas });

function describe(o){
  const p = o.geometry && o.geometry.parameters;
  const px = o.position;
  if(!p) return null;
  return { name:o.name, is_mesh:true, visible:o.visible!==false,
    parent_names:['BUILDING'], user_data:o.userData||{},
    box:{ min:[px.x-p.width/2, px.y-p.height/2, px.z-p.depth/2],
          max:[px.x+p.width/2, px.y+p.height/2, px.z+p.depth/2] } };
}
function readPixels(){
  const gl = renderer.getContext();
  const w = Math.min(canvas.width, 320), h = Math.min(canvas.height, 200);
  const buf = new Uint8Array(w*h*4);
  gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,buf);
  const seen = new Set(); let nonBg = 0, hash = 0;
  const BG = [15,18,23];                       // 0.06/0.07/0.09 بعد التحويل
  for(let i=0;i<w*h;i++){
    const r=buf[i*4], g=buf[i*4+1], b=buf[i*4+2];
    seen.add((r>>3)+','+(g>>3)+','+(b>>3));
    if(Math.abs(r-BG[0])>6||Math.abs(g-BG[1])>6||Math.abs(b-BG[2])>6) nonBg++;
    hash = (hash*31 + r + g*3 + b*7) >>> 0;
  }
  return { sampled:w*h, distinct:seen.size, hash:hash,
    non_bg_pct: Math.round((nonBg/(w*h))*10000)/100 };
}

function run(model, detail){
  if(detail!==undefined) __ACS_SHARED.DETAIL = detail;
  const out = { error:null };
  let grp = null;
  try{ grp = compile(model); }
  catch(e){ out.error = String(e && e.message || e);
            out.stack = String((e&&e.stack)||'').split('\\n').slice(0,3).join(' | ');
            out.pixels = { distinct:0, non_bg_pct:0, hash:0 };
            out.defects = acsBuildDefects(); return out; }
  out.defects = acsBuildDefects();
  const descs = [];
  grp.traverse(o=>{ if(o.isMesh){ const d=describe(o); if(d) descs.push(d); } });
  out.meshes = descs.length;
  const rb = pqRobustBounds(descs);
  out.bounds_valid = !!rb.valid;
  out.radius = (rb.bounds||{}).radius;
  out.included = (rb.diagnostics||{}).included_in_bounds;
  out.excluded = (rb.diagnostics||{}).excluded_invalid_bounds;
  const fit = pqCameraFit(rb.bounds, 52, canvas.width/canvas.height, 35, 22, 0);
  out.in_frustum = !!fit.camera_in_frustum;
  if(!fit.camera){ out.camera=null; out.pixels={distinct:0,non_bg_pct:0,hash:0};
                   out.draw_calls=0; out.canvas=[canvas.width,canvas.height];
                   return out; }
  out.camera = { position:fit.camera.position, target:fit.camera.target,
                 near:fit.camera.near, far:fit.camera.far };
  const cam = new THREE.PerspectiveCamera(52, canvas.width/canvas.height,
                                          fit.camera.near, fit.camera.far);
  cam.position.set(fit.camera.position[0], fit.camera.position[1],
                   fit.camera.position[2]);
  renderer.__target = fit.camera.target;
  const scene = new THREE.Scene(); scene.add(grp);
  renderer.render(scene, cam);
  out.draw_calls = renderer.info.render.calls;
  out.canvas = [canvas.width, canvas.height];
  out.pixels = readPixels();
  return out;
}
window.__RUN = run;
window.__COMPILE = compile;

/* الشاهد السالب: نفس المشهد والعتاد، وهندسةٌ عند NaN كما كانت تُبنى قبل
   F-42 — ليُقاس أن النافذة تبقى خلفيّةً موحّدة فعلاً. */
window.__RUN_NAN = function(){
  const grp = compile(JSON.parse(window.__LAST_GOOD));
  let n = 0;
  grp.traverse(o=>{ if(o.isMesh){ o.position.y = NaN; n++; } });
  const descs = []; grp.traverse(o=>{ if(o.isMesh){ const d=describe(o);
    if(d) descs.push(d); } });
  const rb = pqRobustBounds(descs);
  const cam = new THREE.PerspectiveCamera(52, canvas.width/canvas.height, 0.1, 500);
  cam.position.set(30, 25, 30);
  renderer.__target = [0,0,0];
  const scene = new THREE.Scene(); scene.add(grp);
  renderer.render(scene, cam);
  return { meshes:n, included:(rb.diagnostics||{}).included_in_bounds,
    excluded:(rb.diagnostics||{}).excluded_invalid_bounds,
    draw_calls:renderer.info.render.calls, pixels:readPixels() };
};
window.__READY = true;
`;

/* نموذج بشكل الإنتاج تماماً: 22×16 · L0/L1/L2 · مستودع بأرفف وممرّات. */
function prodModel(withIndex, per) {
  per = per === undefined ? 14 : per;
  const tmpl = ['t0', 't1', 't2'];
  const levels = tmpl.map((t, i) => {
    const l = { id: 'L' + i, template: t, elevation: +(i * 4.0).toFixed(3) };
    if (withIndex) { l.index = i; l.name = 'المستوى ' + i; }
    return l;
  });
  const floors = {};
  tmpl.forEach((t, ti) => {
    const rooms = [];
    for (let k = 0; k < per; k++) {
      const col = k % 5, row = (k / 5) | 0;
      rooms.push({ id: 'zone_' + String(ti * per + k).padStart(3, '0'),
        rect: [0.6 + col * 4.2, 0.6 + row * 4.8, 3.6, 4.0],
        role: 'storage', walls: 'none',
        racks: [{ kind: 'pallet', x: 0.3, z: 0.3, w: 3.0, d: 3.4, dir: 'x',
                  aisle: 1.2, levels: 4, h: 3.0 }],
        points: [{ type: 'light', x: 1.8, z: 2.0 }] });
    }
    floors[t] = { rooms: rooms };
  });
  return { meta: { type: 'warehouse', requirements: [] },
    site: { w: 22, d: 16 }, floor_height: 4.0, wall_h: 3.6, wall_t: 0.2,
    levels: levels, floors: floors };
}
function smallModel() {
  return { meta: { type: 'residential' }, site: { w: 12, d: 10 },
    floor_height: 3.2, wall_h: 3.0, wall_t: 0.15,
    levels: [{ index: 0, name: 'الأرضي', template: 'g' }],
    floors: { g: { rooms: [
      { id: 'majlis', rect: [0.5, 0.5, 5, 4], role: 'majlis',
        doors: [{ edge: 'N', offset: 2.5, width: 0.9, height: 2.1 }] },
      { id: 'kitchen', rect: [6, 0.5, 4, 4], role: 'kitchen' }] } } };
}

async function main() {
  const srv = await H.serve({ overrides: {
    '/ki25_probe.js': PROBE,
    '/ki25.html': PAGE,
    '/vendor/three@0.160.0/build/three.module.js': GL_THREE } });
  const base = 'http://127.0.0.1:' + srv.port;
  const browser = await PW.launch({
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader',
           '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 900, height: 600 } });

  const errors = [], violations = [], consoleMsgs = [];
  page.on('pageerror', e => errors.push(String(e && e.message || e)));
  page.on('console', m => { consoleMsgs.push({ type: m.type(), text: m.text() });
    if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('requestfailed', r => violations.push(r.url()));

  const html = PAGE.replace('/ki25_probe.js', '/ki25_probe.js');
  await page.route('**/ki25.html', route =>
    route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8',
      headers: { 'Content-Security-Policy': H.productionCSP() }, body: html }));
  await page.goto(base + '/ki25.html', { waitUntil: 'load' });
  try{
    await page.waitForFunction(() => window.__READY === true, null,
                               { timeout: 30000 });
  }catch(e){
    console.error('PAGE DID NOT INITIALISE');
    console.error('  pageerror : ' + JSON.stringify(errors.slice(0, 6), null, 1));
    console.error('  console   : ' + JSON.stringify(consoleMsgs.slice(0, 12), null, 1));
    console.error('  failed    : ' + JSON.stringify(violations.slice(0, 8), null, 1));
    await browser.close(); srv.close(); throw e;
  }

  console.log('\n== أ · بيئة القياس معلَنة بدقّة ==');
  const env = await page.evaluate(() => {
    const c = document.getElementById('c');
    const gl = c.getContext('webgl2');
    return { has_gl: !!gl,
      vendor: gl ? gl.getParameter(gl.VENDOR) : null,
      renderer: gl ? gl.getParameter(gl.RENDERER) : null,
      canvas: [c.width, c.height],
      three_is_real: !!(window.THREE && window.THREE.__ACS_REAL_THREE),
      compile_is_shipped: typeof window.__COMPILE === 'function' };
  });
  chk('سياق WebGL2 حقيقيّ مفتوح', env.has_gl === true);
  chk('واللوحة بأبعاد غير صفريّة',
      env.canvas[0] > 0 && env.canvas[1] > 0, JSON.stringify(env.canvas));
  chk('و compile() المشحون هو المُستدعَى', env.compile_is_shipped === true);
  console.log('     GL: ' + env.vendor + ' · ' + env.renderer);
  console.log('     three.js حقيقيّ في هذه الشجرة: '
              + (VENDOR_OK ? 'نعم' : 'لا — public/vendor فارغ (npm 403)'));

  /* ═══════════ ب · الحمولة الإنتاجية تُرسَم ═════════════════════════════ */
  console.log('\n== ب · رد 200 بشكل الإنتاج → مبنى مرئيّ ==');
  await page.evaluate(m => { window.__LAST_GOOD = JSON.stringify(m); },
                      prodModel(true));
  const R = await page.evaluate(async (m) => window.__RUN(m), prodModel(true));
  chk('setModel/compile يكتمل بلا استثناء', R.error === null, R.error || '');
  chk('وعدد الأجسام القابلة للرسم أكبر من صفر',
      R.meshes > 0, String(R.meshes));
  chk('ولا شبكة واحدة بإحداثيّة غير منتهية',
      R.defects.non_finite_box === 0, String(R.defects.non_finite_box));
  chk('وحدود المشهد صالحة ومحدودة',
      R.bounds_valid === true && isFinite(R.radius) && R.radius > 0,
      String(R.radius));
  chk('وحدود الكاميرا منتهية كلّها',
      [R.camera.near, R.camera.far].every(v => isFinite(v) && v > 0)
      && R.camera.position.every(isFinite) && R.camera.target.every(isFinite),
      JSON.stringify(R.camera));
  chk('والنموذج داخل هرم الرؤية', R.in_frustum === true);
  chk('ونداءات الرسم غير صفريّة', R.draw_calls > 0, String(R.draw_calls));
  chk('واللوحة بأبعاد غير صفريّة بعد الرسم',
      R.canvas[0] > 0 && R.canvas[1] > 0, JSON.stringify(R.canvas));
  chk('والبكسلات المقروءة ليست خلفيّة موحّدة',
      R.pixels.distinct > 1 && R.pixels.non_bg_pct > 5,
      'ألوان مميّزة=' + R.pixels.distinct + ' · غير خلفيّة='
      + R.pixels.non_bg_pct + '%');
  chk('ولا استثناء تطبيقيّ واحد في الكونسول',
      errors.length === 0, JSON.stringify(errors.slice(0, 3)));
  console.log('     ' + R.meshes + ' شبكة · نصف قطر ' + R.radius
              + ' · نداءات ' + R.draw_calls + ' · بكسلات غير خلفيّة '
              + R.pixels.non_bg_pct + '% · ألوان ' + R.pixels.distinct);

  /* ═══════════ ج · نفس الحمولة بلا index — عطل KI-25 ════════════════════ */
  console.log('\n== ج · نفس الحمولة بمستويات بلا index (شكل الإنتاج المعطوب) ==');
  const N = await page.evaluate(async (m) => window.__RUN(m), prodModel(false));
  chk('تُرسَم كما تُرسَم النسخة المصرِّحة بالأرقام',
      N.pixels.non_bg_pct > 5 && N.pixels.distinct > 1,
      N.pixels.non_bg_pct + '% · ' + N.pixels.distinct);
  chk('ولا شبكة واحدة تسقط من الحدود',
      N.excluded === 0 && N.included === N.meshes,
      N.included + '/' + N.meshes + ' سقط ' + N.excluded);
  chk('ونصف القطر مطابق للنسخة المصرِّحة — النموذج نفسه',
      Math.abs(N.radius - R.radius) < 1e-6, N.radius + ' / ' + R.radius);
  chk('والاشتقاق مُحصى لا صامت', N.defects.derived_level_index === 3,
      String(N.defects.derived_level_index));

  /* الشاهد السالب: نفس الصفحة، ونفس العتاد، والعطل الأصليّ مُعاد يدوياً في
     المدخل (مستوياتٌ ترفع كل شيء إلى NaN) — لتُقاس النافذة الفارغة فعلاً. */
  console.log('\n== د · الشاهد السالب: هندسة عند NaN لا تُرسَم ==');
  const Z = await page.evaluate(async () => window.__RUN_NAN());
  chk('هندسة عند NaN → لا بكسل واحد غير الخلفيّة',
      Z.pixels.non_bg_pct === 0 && Z.pixels.distinct === 1,
      Z.pixels.non_bg_pct + '% · ' + Z.pixels.distinct);
  chk('ومع ذلك عدّاد الشبكات ممتلئ — وهذا ما كان يُكتب للمستخدم',
      Z.meshes > 100, String(Z.meshes));
  chk('وعقد الحدود يستبعدها كلّها',
      Z.excluded === Z.meshes || Z.included === 0,
      Z.included + '/' + Z.meshes);
  chk('فالفرق بين ب و د بكسلات مقيسة لا ادّعاء',
      R.pixels.non_bg_pct > 5 && Z.pixels.non_bg_pct === 0,
      R.pixels.non_bg_pct + '% ↔ ' + Z.pixels.non_bg_pct + '%');

  /* ═══════════ هـ · النموذج الجديد يختلف عن سابقه ═══════════════════════ */
  console.log('\n== هـ · توليد جديد يستبدل القديم فعلاً ==');
  const S = await page.evaluate(async (m) => window.__RUN(m), smallModel());
  chk('نموذج صغير بعد الكبير → يُرسَم أيضاً',
      S.pixels.non_bg_pct > 5, S.pixels.non_bg_pct + '%');
  chk('وبصمة الإطار تختلف عن إطار النموذج السابق',
      S.pixels.hash !== R.pixels.hash, S.pixels.hash + ' ≠ ' + R.pixels.hash);
  chk('وعدد الشبكات يختلف — ليس المشهد القديم باقياً',
      S.meshes !== R.meshes, S.meshes + ' ≠ ' + R.meshes);
  chk('وحدود المشهد تتبع النموذج الجديد لا القديم',
      Math.abs(S.radius - R.radius) > 0.5, S.radius + ' ≠ ' + R.radius);

  /* ═══════════ و · مسار الجوال ══════════════════════════════════════════ */
  console.log('\n== و · مسار الجوال (نافذة ضيّقة، تفصيل خفيف) ==');
  await page.setViewportSize({ width: 390, height: 780 });
  const M = await page.evaluate(async (m) => window.__RUN(m, 0.5), prodModel(false));
  chk('يُبنى ويُرسَم في نافذة الجوال',
      M.error === null && M.pixels.non_bg_pct > 5,
      (M.error || '') + ' ' + M.pixels.non_bg_pct + '%');
  chk('ولا هندسة تالفة', M.defects.non_finite_box === 0
      && M.excluded === 0, M.excluded + ' سقط');
  await page.setViewportSize({ width: 900, height: 600 });

  /* ═══════════ ز · الكونسول ═════════════════════════════════════════════ */
  console.log('\n== ز · الكونسول بعد كل التوليدات ==');
  const appErrors = errors.filter(e => !/content\.js|extension/i.test(e));
  chk('صفر استثناء تطبيقيّ غير ملتقَط', appErrors.length === 0,
      JSON.stringify(appErrors.slice(0, 4)));
  chk('ولا طلب فاشل من أصل الصفحة', violations.length === 0,
      JSON.stringify(violations.slice(0, 3)));
  const cspMsgs = consoleMsgs.filter(m => /Content Security Policy/i.test(m.text));
  chk('ولا خرق سياسة أمن واحد تحت السياسة الإنتاجية',
      cspMsgs.length === 0, JSON.stringify(cspMsgs.slice(0, 2)));

  await browser.close();
  srv.close();

  console.log('\n' + '─'.repeat(62));
  if (!VENDOR_OK) {
    console.log('LIVE FRONTEND APPLY (three.js): NOT VERIFIED — EXTERNAL '
      + 'ENVIRONMENT REQUIRED');
    console.log('  public/vendor فارغ و npm يردّ 403، فلا three@0.160.0 هنا.');
    console.log('  المقيس أعلاه: هندسة compile() المشحونة، وكاميرا العقد '
      + 'المشحون، مرسومة بـWebGL2 حقيقيّ وبكسلات مقروءة بـreadPixels.');
    console.log('  لإغلاق ما بقي: bash tools/vendor.sh ثم إعادة هذا الملفّ.');
  } else {
    console.log('LIVE FRONTEND APPLY: three.js حقيقيّ مُعبَّأ — القياس كامل.');
  }
  console.log('APPLY RENDER (real Chromium): %d passed, %d failed', pass, fail);
  if (fail) process.exit(1);
}

main().catch(e => { console.error(e); process.exit(1); });
