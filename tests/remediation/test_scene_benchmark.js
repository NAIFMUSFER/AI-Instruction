/* ============================================================================
   ميزانيات الأداء المعلنة — Chromium حقيقي، WebGL2 حقيقي، سطح مكتب وجوال.
     node tests/remediation/test_scene_benchmark.js

   ما يُقاس
   --------
   خمس حمولات حتميّة (SMALL · MEDIUM · LARGE · VERY_LARGE · ADVERSARIAL)،
   لكلٍّ منها على مقاسَي نافذة (سطح مكتب 1440×900 · جوال 390×844) وعلى
   نافذة لوحيّة واحدة (820×1180):

     زمن compile · زمن حدود المشهد · زمن مصالحة الكاميرا · زمن أوّل إطار
     مرسوم · عدد الشبكات · نداءات الرسم · كومة JS إن أتاحها المتصفّح ·
     زمن الإطار · نسبة البكسلات غير الخلفيّة · قرارات التدهور

   الميزانيات المعلنة هنا **لا تُخفَّض بعد القياس**. مقياسها هو ما يقع بعد
   وصول رد HTTP: البناء والعرض. زمن الشبكة والتوليد ليس منها.

   نطاق مُعلَن
   -----------
   الرسم يمرّ دائماً بمنفّذ WebGL2 مكتوب في tests/remediation/lib_gl_three.js يرسم هندسة
   ‎compile()‎ المشحونة بتظليل حقيقيّ. فما يُقاس هنا زمن **المترجم والعقد
   والرسم الخام** لا زمن شجرة three. ولذلك:
       LIVE THREE.JS BENCHMARK: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
   وجود three في public/vendor لا يغيّر نطاق هذا الاختبار.
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
const chk = (n, c, d) => {
  if (c) { pass++; console.log('  ✓ ' + n); }
  else { fail++; console.log('  ✗ ' + n + '  ' + (d === undefined ? '' : d)); }
};

/* ═══ الميزانيات المعلنة — زمن أوّل إطار مرسوم بعد وصول رد HTTP ═══════════ */
const BUDGET_MS = Object.freeze({
  SMALL: 2000, MEDIUM: 4000, LARGE: 8000,
  VERY_LARGE: 8000,          // أو تدهورٌ حتميّ مُعلَن بدل التجميد
  ADVERSARIAL: 8000,
});
const MAX_MAIN_THREAD_STALL_MS = 1000;

const VIEWPORTS = [
  ['desktop', 1440, 900],
  ['mobile', 390, 844],
  ['tablet', 820, 1180],
];

/* ═══ حمولات حتميّة — لا عشوائية، فالأرقام قابلة للمقارنة عبر التشغيلات ═══ */
function fixture(name) {
  const S = {
    SMALL: { levels: 1, per: 4, racks: 0, lanes: 0, cores: 0, objs: 1 },
    MEDIUM: { levels: 2, per: 12, racks: 1, lanes: 1, cores: 2, objs: 2 },
    LARGE: { levels: 3, per: 18, racks: 1, lanes: 1, cores: 4, objs: 3 },
    VERY_LARGE: { levels: 6, per: 30, racks: 2, lanes: 2, cores: 8, objs: 4 },
    ADVERSARIAL: { levels: 8, per: 40, racks: 3, lanes: 3, cores: 64, objs: 6 },
  }[name];
  const tmpl = [];
  for (let i = 0; i < S.levels; i++) tmpl.push('t' + i);
  const levels = tmpl.map((t, i) => ({ id: 'L' + i, index: i,
    name: 'المستوى ' + i, template: t, elevation: +(i * 4.5).toFixed(3) }));
  const floors = {};
  tmpl.forEach((t, ti) => {
    const rooms = [];
    for (let k = 0; k < S.per; k++) {
      const col = k % 8, row = (k / 8) | 0;
      const r = { id: 'zone_' + String(ti * S.per + k).padStart(3, '0'),
        rect: [1 + col * 7.0, 1 + row * 8.0, 6.0, 7.0],
        role: 'storage', walls: 'none',
        points: [{ type: 'light', x: 3, z: 3.5 },
                 { type: 'sprinkler', x: 1.5, z: 1.5 }],
        furniture: [{ kind: 'desk', x: 0.5, z: 0.5, w: 1.2, d: 0.6 }] };
      if (S.racks) r.racks = Array.from({ length: S.racks }, (_v, j) => ({
        kind: 'pallet', x: 0.3 + j * 0.2, z: 0.3, w: 5.0, d: 6.2, dir: 'x',
        aisle: 3.4, levels: 4, h: 8.0 }));
      if (S.lanes) r.lanes = Array.from({ length: S.lanes }, (_v, j) => ({
        kind: j % 2 ? 'conveyor' : 'forklift', x: 0.2, z: 0.2 + j * 0.5,
        w: 5.4, d: 0.9, dir: 'x' }));
      if (S.objs) r.objects = Array.from({ length: S.objs }, (_v, j) => ({
        kind: ['pallet', 'box', 'sign', 'stair', 'railing', 'bollard'][j % 6],
        x: 1 + j, z: 1, count: 6, pitch: 0.8 }));
      if (k === 0) { r.stations = [{ kind: 'pack', x: 1, z: 1, count: 8 }]; }
      if (k === 1) { r.docks = [{ edge: 'N', x: 1, z: 0, count: 4 }]; }
      rooms.push(r);
    }
    // النوى: أجسام درج/مصعد تنتج فراغات في بلاطات الأدوار فوقها
    for (let c = 0; c < S.cores; c++) {
      rooms.push({ id: 'core_' + ti + '_' + c,
        rect: [1 + (c % 8) * 7.0, 60 + ((c / 8) | 0) * 6.0, 3.0, 3.0],
        role: 'core', walls: 'full',
        objects: [{ kind: 'stair', x: 0.3, z: 0.3, w: 2.4, d: 2.4, h: 4.2 }] });
    }
    floors[t] = { rooms: rooms };
  });
  return { meta: { type: 'warehouse', requirements: [] },
    site: { w: 60, d: 90 }, floor_height: 4.5, wall_h: 4.0, wall_t: 0.2,
    levels: levels, floors: floors };
}

const IMPORTMAP = (function () {
  const shell = fs.readFileSync(path.join(ROOT, 'public', 'index.html'), 'utf8');
  const i = shell.indexOf('<script type="importmap">');
  return shell.slice(i, shell.indexOf('</script>', i) + '</script>'.length);
})();

const PAGE = `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>bench</title>
${IMPORTMAP}
</head><body><canvas id="c"></canvas>
<script type="module" src="/bench_probe.js"></script></body></html>`;

const PROBE = `
import * as THREE from 'three';
/* ترتيب التحميل كما في public/app/main.js: التخصّصات تسجّل نفسها في
   __ACS_LATE، وبدونها يسقط ARCH وSTRUCT وMEP وFLS — وقد كشف ذلك أوّل تشغيل
   لهذا الملفّ (السجلّ أعلن ARCH_COMPILE_FAILED خمس مرّات)، وهو بالضبط ما
   أضيف سجلّ العيوب لأجله. */
import '/app/core/standards.js';
import '/app/core/disciplines.js';
import { compile, acsBuildDefects, acsCompileSummary, SCENE_LIMITS } from '/app/core/viewer.js';
import { pqRobustBounds, pqCameraFit } from '/app/generated/pbr.js';
window.SCENE_LIMITS = SCENE_LIMITS;
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas: canvas });
window.__RENDERER_SCOPE = {three_js_real:THREE.__ACS_REAL_THREE===true,
  adapter:THREE.__ACS_GL_SUBSTITUTE};
const now = () => performance.now();

function describe(o){
  const p=o.geometry&&o.geometry.parameters, x=o.position;
  if(!p) return null;
  return {name:o.name,is_mesh:true,visible:o.visible!==false,
    parent_names:['BUILDING'],user_data:o.userData||{},
    box:{min:[x.x-p.width/2,x.y-p.height/2,x.z-p.depth/2],
         max:[x.x+p.width/2,x.y+p.height/2,x.z+p.depth/2]}};
}
function pixels(){
  /* تُقرأ اللوحة **كاملة** لا ركنها: أوّل نسخة قرأت 320×200 من الزاوية
     السفلى اليسرى على لوحة 1440×900، فأعطت صفراً بينما المشهد مرسوم في
     وسطها — خطأ قياس لا عطل رسم. */
  const gl=renderer.getContext();
  const w=canvas.width, h=canvas.height;
  const b=THREE.readGLPixels(gl,w,h);
  let nz=0; const seen=new Set(); const BG=[15,18,23];
  for(let i=0;i<w*h;i++){ const r=b[i*4],g=b[i*4+1],bl=b[i*4+2];
    seen.add((r>>3)+','+(g>>3)+','+(bl>>3));
    if(Math.abs(r-BG[0])>6||Math.abs(g-BG[1])>6||Math.abs(bl-BG[2])>6) nz++; }
  return {non_bg_pct:Math.round((nz/(w*h))*10000)/100, distinct:seen.size};
}

window.__BENCH = function(model, w, h){
  canvas.width=w; canvas.height=h;
  const t_all=now();
  const t0=now(); let grp=null, err=null;
  try{ grp=compile(model); }catch(e){ err=String(e&&e.message||e); }
  const t_compile=now()-t0;
  if(err) return {error:err};
  const sum = (typeof acsCompileSummary==='function')?acsCompileSummary():null;
  const t1=now();
  const descs=[]; grp.traverse(o=>{ if(o.isMesh){const d=describe(o); if(d) descs.push(d);} });
  const rb=pqRobustBounds(descs);
  const t_bounds=now()-t1;
  const t2=now();
  const fit=pqCameraFit(rb.bounds,52,w/h,35,22,0);
  const t_camera=now()-t2;
  if(!fit.camera) return {error:'no camera fit', meshes:descs.length};
  const cam=new THREE.PerspectiveCamera(52,w/h,fit.camera.near,fit.camera.far);
  cam.position.set(fit.camera.position[0],fit.camera.position[1],fit.camera.position[2]);
  renderer.__target=fit.camera.target;
  const scene=new THREE.Scene(); scene.add(grp);
  const t3=now(); renderer.render(scene,cam); const t_frame=now()-t3;
  const px=pixels();
  // إطار ثانٍ لقياس زمن الإطار المستقرّ (الأول يشمل رفع الحالة إلى العتاد)
  const t4=now(); renderer.render(scene,cam); const t_frame2=now()-t4;
  const heap=(performance.memory&&performance.memory.usedJSHeapSize)||null;
  return {meshes:descs.length, included:(rb.diagnostics||{}).included_in_bounds,
    excluded:(rb.diagnostics||{}).excluded_invalid_bounds,
    draw_calls:renderer.info.render.calls, triangles:renderer.info.render.triangles,
    radius:(rb.bounds||{}).radius,
    t_compile:Math.round(t_compile), t_bounds:Math.round(t_bounds),
    t_camera:Math.round(t_camera), t_frame:Math.round(t_frame),
    t_frame2:Math.round(t_frame2),
    t_first_visible:Math.round(now()-t_all),
    heap_mb: heap?Math.round(heap/1048576):null,
    pixels:px, degraded: sum?!!sum.degraded:null,
    degradation: sum?(sum.degradation_reasons||[]):[],
    defects: acsBuildDefects()};
};
window.__READY = true;
`;

async function main() {
  const srv = await H.serve({ overrides: {
    '/bench_probe.js': PROBE,
    '/vendor/three@0.160.0/build/three.module.js':
      fs.readFileSync(path.join(HERE, 'lib_gl_three.js'), 'utf8') } });
  const base = 'http://127.0.0.1:' + srv.port;
  const browser = await PW.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader',
           '--js-flags=--expose-gc'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e && e.message || e)));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.route('**/bench.html', r =>
    r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8',
      headers: { 'Content-Security-Policy': H.productionCSP() }, body: PAGE }));
  await page.goto(base + '/bench.html', { waitUntil: 'load' });
  await page.waitForFunction(() => window.__READY === true, null, { timeout: 30000 });

  const LIM = await page.evaluate(() => window.SCENE_LIMITS);
  const scope = await page.evaluate(() => window.__RENDERER_SCOPE);
  chk('renderer scope comes from the loaded raw WebGL2 adapter',
      scope.three_js_real===false&&scope.adapter==='acs.gl-three/1.0.0',JSON.stringify(scope));
  console.log('\n== أ · عقد حدود المشهد مشحون ومقروء ==');
  chk('SCENE_LIMITS معلن ومجمَّد في الوحدة المشحونة',
      LIM && typeof LIM.contract === 'string' && LIM.max_total_meshes > 0,
      JSON.stringify(LIM && LIM.contract));
  console.log('     ' + JSON.stringify(LIM));

  const names = ['SMALL', 'MEDIUM', 'LARGE', 'VERY_LARGE', 'ADVERSARIAL'];
  const table = [];
  for (const [vpName, w, h] of VIEWPORTS) {
    await page.setViewportSize({ width: w, height: h });
    console.log('\n== ب · ' + vpName + ' ' + w + 'x' + h + ' ==');
    const pad = (v, n) => String(v).padStart(n);
    const padL = (v, n) => String(v).padEnd(n);
    console.log('     ' + padL('fixture', 13) + pad('compile', 8)
      + pad('bounds', 8) + pad('camera', 8) + pad('frame1', 8)
      + pad('frame2', 8) + pad('visible', 9) + pad('meshes', 8)
      + pad('draws', 9) + pad('px%', 8) + '  degraded');
    for (const name of names) {
      const model = fixture(name);
      const r = await page.evaluate(
        ([m, ww, hh]) => window.__BENCH(m, ww, hh), [model, w, h]);
      if (r.error) { chk(vpName + ' ' + name + ' → بُني بلا خطأ', false, r.error); continue; }
      table.push(Object.assign({ viewport: vpName, fixture: name }, r));
      console.log('     ' + padL(name, 13) + pad(r.t_compile, 8)
        + pad(r.t_bounds, 8) + pad(r.t_camera, 8) + pad(r.t_frame, 8)
        + pad(r.t_frame2, 8) + pad(r.t_first_visible, 9) + pad(r.meshes, 8)
        + pad(r.draw_calls, 9) + pad(r.pixels.non_bg_pct, 8) + '  '
        + (r.degraded ? JSON.stringify(r.degradation) : 'no'));
    }
  }

  console.log('\n== ج · الميزانيات المعلنة ==');
  for (const row of table) {
    const budget = BUDGET_MS[row.fixture];
    const inBudget = row.t_first_visible <= budget;
    const degradedOk = row.degraded === true;   // VERY_LARGE يجوز أن يتدهور
    const ok = inBudget || (row.fixture !== 'SMALL' && row.fixture !== 'MEDIUM'
                            && row.fixture !== 'LARGE' && degradedOk);
    chk(('%s · %s → أوّل إطار ≤ %d ms')
        .replace('%s', row.viewport).replace('%s', row.fixture)
        .replace('%d', budget),
        ok, row.t_first_visible + ' ms'
        + (row.degraded ? (' (degraded: ' + JSON.stringify(row.degradation) + ')') : ''));
  }
  console.log('\n== د · لا تجميد للخيط الرئيس ==');
  for (const row of table) {
    chk(('%s · %s → أطول عمل متّصل ≤ %d ms')
        .replace('%s', row.viewport).replace('%s', row.fixture)
        .replace('%d', MAX_MAIN_THREAD_STALL_MS),
        Math.max(row.t_compile, row.t_frame) <= MAX_MAIN_THREAD_STALL_MS,
        'compile=' + row.t_compile + ' frame=' + row.t_frame);
  }
  console.log('\n== هـ · كل حمولة تُرسَم فعلاً ولا تُهدر هندسة ==');
  for (const row of table) {
    chk(('%s · %s → بكسلات غير خلفيّة > 3%%')
        .replace('%s', row.viewport).replace('%s', row.fixture),
        row.pixels.non_bg_pct > 3 && row.pixels.distinct > 1,
        row.pixels.non_bg_pct + '% · ' + row.pixels.distinct);
    chk(('%s · %s → لا شبكة تسقط من الحدود')
        .replace('%s', row.viewport).replace('%s', row.fixture),
        row.excluded === 0, String(row.excluded));
    chk(('%s · %s → عدد الشبكات تحت السقف المعلن')
        .replace('%s', row.viewport).replace('%s', row.fixture),
        row.meshes <= LIM.max_total_meshes,
        row.meshes + ' / ' + LIM.max_total_meshes);
  }
  console.log('\n== و · الحمولة العدائية محدودة لا منفجرة ==');
  const adv = table.filter(r => r.fixture === 'ADVERSARIAL');
  const lrg = table.filter(r => r.fixture === 'LARGE');
  chk('ADVERSARIAL (٦٤ نواة/دور · ٨ أدوار) يكتمل ولا يعلّق',
      adv.length === VIEWPORTS.length);
  chk('ونموّه على LARGE محدود لا مكعّب',
      adv.length && lrg.length
      && adv[0].t_compile <= Math.max(400, lrg[0].t_compile * 40),
      adv.length ? (lrg[0].t_compile + ' → ' + adv[0].t_compile + ' ms') : '');
  chk('وقراره معلَن إن تدهور',
      adv.every(r => r.degraded === false || (r.degradation || []).length > 0),
      JSON.stringify(adv.map(r => r.degradation)));

  console.log('\n== ز · الكونسول ==');
  const appErr = errors.filter(e => !/content\.js|extension/i.test(e));
  chk('صفر استثناء تطبيقيّ عبر خمس عشرة حمولة', appErr.length === 0,
      JSON.stringify(appErr.slice(0, 3)));

  await browser.close();
  srv.close();

  fs.mkdirSync(path.join(HERE, 'outputs'), { recursive: true });
  fs.writeFileSync(path.join(HERE, 'outputs', 'scene_benchmark.json'),
    JSON.stringify({ budgets: BUDGET_MS, limits: LIM,
      three_js_real: scope.three_js_real, renderer_adapter:scope.adapter, rows: table }, null, 1));

  console.log('\n' + '─'.repeat(62));
  console.log('LIVE THREE.JS BENCHMARK: NOT VERIFIED by this target.');
  console.log('  Measured: shipped compile() + shipped camera contract + raw '
    + 'WebGL2 test adapter. Three.js scene-graph cost requires a separate benchmark.');
  console.log('SCENE BENCHMARK: %d passed, %d failed', pass, fail);
  if (fail) process.exit(1);
}

main().catch(e => { console.error(e); process.exit(1); });
