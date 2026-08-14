/* ============================================================================
   F-08 — عقد تشخيص العرض الدائم، وF-07 — تكافؤ عقد امتداد اللوح.

   يُشغَّل هكذا:   node tests/lib/run.js tests/remediation/test_webgl_diagnostics.js

   ما يمكن إثباته هنا يُثبَت فعلاً لا نصّاً: تُستخرَج كتلة التشخيص المكتوبة يدوياً
   من public/index.html وتُنفَّذ في نطاق مضبوط، فيه مُصيِّر ومشهد وكاميرا وسياق
   WebGL مزيَّفة، وكل قيمة فيها بصمة مميّزة. ثم يُتحقّق أن كل مفتاح في المخرَج
   يعود إلى تلك البصمة بالضبط — وهذا ما يثبت أنّ القيم مقيسة لا مختلَقة.

   ما لا يمكن إثباته هنا لا يُدَّعى: العرض الحقيقي على WebGL يحتاج Three.js
   المُعبَّأ في public/vendor، وهو غائب في هذا الصندوق بلا شبكة. الحالات التسع
   للعرض تبقى NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED، ومِرقابها
   tests/deploy/verify_page_boot.js يخرج بالرمز 2 بدل أن ينجح زوراً.
   ========================================================================== */
const fs = require('fs'), _np = require('path');
const { execFileSync } = require('child_process');
const HERE = __dirname, ROOT = _np.resolve(HERE, '..', '..');
let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
  : (fail++, console.log('  ✗', n, d === undefined ? '' : d)); };
/* F-09 — الواجهة لم تعد ملفّاً واحداً. المصدر الواحد الذي يعرف التخطيط هو
   tests/lib/app_source.js: SHELL للعلامة، APP للشيفرة، PAGE لِما كان يُقرأ
   قبل التفكيك على أنه «الصفحة» (قشرة + شيفرة). البحث عن رمز يجري على APP،
   والبحث عن عنصر DOM يجري على SHELL — خلطهما هو ما جعل الملفّ الواحد يمرّ. */
const AS = require(_np.join(ROOT, 'tests', 'lib', 'app_source.js'));
const SHELL = AS.shell();
const APP = AS.appText();
const BOOTJS = (function () {
  const m = AS.modules(), out = {};
  Object.keys(m).forEach(k => { if (k.indexOf('boot/') === 0) out[k] = m[k]; });
  return out;
})();
const PAGE = AS.pageText();
const py = (code) => execFileSync('python3', ['-c', code],
  { cwd: ROOT, encoding: 'utf8', maxBuffer: 1 << 26 });

const REQUIRED = ['build_sha', 'model_hash', 'revision_id', 'canvas_size',
  'device_pixel_ratio', 'webgl_version', 'renderer', 'object_count',
  'mesh_count', 'triangle_count', 'draw_calls', 'scene_bounds',
  'camera_position', 'camera_target', 'near', 'far', 'frustum_intersections',
  'invalid_coordinate_count', 'max_coordinate_abs', 'render_mode',
  'postprocessing', 'xr_state', 'context_lost', 'pixel_probe'];

/* ---------------------------------------------------------- استخراج ---- */
const MARK_A = '/* ==== ACS RUNTIME RENDER DIAGNOSTICS '
  + '(F-08 · hand-written, NOT generated) ====';
const MARK_B = '/* ==== END ACS RUNTIME RENDER DIAGNOSTICS ==== */';
console.log('\n== §1 — THE DIAGNOSTICS CONTRACT SHIPS IN THE HAND-WRITTEN '
  + 'MODULE ==');
chk('the block exists exactly once in the shipped application code',
    APP.split(MARK_A).length - 1 === 1
    && APP.split(MARK_B).length - 1 === 1);
const iA = APP.indexOf(MARK_A), iB = APP.indexOf(MARK_B);
const BLOCK = (iA >= 0 && iB > iA) ? APP.slice(iA, iB + MARK_B.length) : '';
chk('the block carries real code, not a stub', BLOCK.length > 4000,
    String(BLOCK.length));
/* لا يعيش داخل كتلة مولَّدة: كل الكتل المولَّدة تنتهي قبل بدايته أو تبدأ بعده */
(function () {
  const gen = [];
  const re = /\/\* ===== ACS [A-Z0-9 .]+\(generated[^\n]*\n/g;
  let m;
  while ((m = re.exec(APP)) !== null) gen.push(m.index);
  const ends = [];
  const re2 = /\/\* ===== END ACS [A-Z0-9 .]+ ===== \*\//g;
  while ((m = re2.exec(APP)) !== null) ends.push(m.index);
  const inside = gen.some((g, i) => {
    const e = ends.filter(x => x > g)[0];
    return e !== undefined && iA > g && iA < e;
  });
  chk('the block lives OUTSIDE every generated block, so a regenerate cannot '
      + 'overwrite it', inside === false);
})();
/* F-09 — «داخل سكربت الوحدة» صار «داخل وحدة ES يستوردها main.js». هذا أشدّ:
   الشرط الآن أن تكون الكتلة في ملفّ واحد بعينه، وأن يكون ذلك الملفّ مستورَداً
   فعلاً في رسم الاستيراد — لا مجرّد وجود نصّ بين وسمَي <script>. */
(function () {
  const mods = AS.modules();
  const owners = Object.keys(mods).filter(k => mods[k].indexOf(MARK_A) >= 0);
  chk('the block lives in exactly ONE shipped module', owners.length === 1,
      owners.join(', '));
  chk('that module is imported by public/app/main.js in the boot order — an '
      + 'orphaned file would ship but never run',
      owners.length === 1 && AS.order().indexOf(owners[0]) >= 0,
      owners[0] + ' order=' + JSON.stringify(AS.order()));
  chk('the shell carries no copy of it: the page is a shell, the code is a '
      + 'module', SHELL.indexOf(MARK_A) < 0);
})();

console.log('\n== §2 — NO NETWORK PATH IN captureRenderFailure (STATIC) ==');
const CAP_SRC = (function () {
  const a = BLOCK.indexOf('window.ACS.captureRenderFailure=function');
  if (a < 0) return '';
  const b = BLOCK.indexOf('\n/* زرّ التنزيل', a);
  return BLOCK.slice(a, b < 0 ? BLOCK.length : b);
})();
chk('the capture function was located in the shipped page',
    CAP_SRC.length > 800, String(CAP_SRC.length));
const NET = ['fetch(', 'fetch (', 'XMLHttpRequest', 'sendBeacon', 'WebSocket',
  'EventSource', 'navigator.connection', '.submit(', 'form.action',
  'importScripts', 'new Worker'];
NET.forEach(t => chk('captureRenderFailure contains no `' + t + '`',
  CAP_SRC.indexOf(t) < 0));
chk('captureRenderFailure contains no absolute URL of any scheme',
    !/https?:\/\//.test(CAP_SRC) && !/wss?:\/\//.test(CAP_SRC));
chk('it produces the file the declared way: Blob + createObjectURL + a local '
    + 'download anchor',
    /new Blob\(/.test(CAP_SRC) && /URL\.createObjectURL\(/.test(CAP_SRC)
    && /a\.download\s*=/.test(CAP_SRC));
chk('it revokes the object URL instead of leaking it',
    /revokeObjectURL/.test(CAP_SRC));
chk('it states in its own output that nothing was transmitted',
    /uploaded:false/.test(CAP_SRC) && /transmits_anything:false/.test(CAP_SRC));
chk('the static scan is not vacuous: the same scan DOES find network calls '
    + 'elsewhere in the application code',
    APP.indexOf('fetch(') >= 0 && APP.indexOf('XMLHttpRequest') >= 0);

/* ------------------------------------------------- بيئة تنفيذ مضبوطة ---- */
function makeEnv(opts) {
  const o = opts || {};
  const net = { fetch: 0, xhr: 0, beacon: 0, ws: 0 };
  /* هندسة صغيرة حقيقية بما يكفي لصناديق وحدود وهرم رؤية */
  function V3(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; }
  V3.prototype.set = function (x, y, z) {
    this.x = x; this.y = y; this.z = z; return this; };
  function Box3() {
    this.min = new V3(Infinity, Infinity, Infinity);
    this.max = new V3(-Infinity, -Infinity, -Infinity); }
  Box3.prototype.setFromObject = function (obj) {
    const b = obj.__box;
    this.min.set(b[0], b[1], b[2]); this.max.set(b[3], b[4], b[5]);
    return this; };
  Box3.prototype.union = function (other) {
    this.min.set(Math.min(this.min.x, other.min.x),
      Math.min(this.min.y, other.min.y), Math.min(this.min.z, other.min.z));
    this.max.set(Math.max(this.max.x, other.max.x),
      Math.max(this.max.y, other.max.y), Math.max(this.max.z, other.max.z));
    return this; };
  Box3.prototype.getCenter = function (t) {
    return t.set((this.min.x + this.max.x) / 2, (this.min.y + this.max.y) / 2,
      (this.min.z + this.max.z) / 2); };
  Box3.prototype.getSize = function (t) {
    return t.set(this.max.x - this.min.x, this.max.y - this.min.y,
      this.max.z - this.min.z); };
  Box3.prototype.getBoundingSphere = function (s) {
    s.c = [(this.min.x + this.max.x) / 2, (this.min.y + this.max.y) / 2,
      (this.min.z + this.max.z) / 2];
    s.r = Math.max(this.max.x - this.min.x, this.max.y - this.min.y,
      this.max.z - this.min.z) / 2;
    return s; };
  function Sphere() { this.c = [0, 0, 0]; this.r = 0; }
  function Matrix4() { this.__m = true; }
  Matrix4.prototype.multiplyMatrices = function () { return this; };
  function Frustum() { }
  /* هرم رؤية مبسّط لكنه حقيقي هنا: كل ما مركزه ضمن نصف قطر معلَن يُحسَب داخله */
  Frustum.prototype.setFromProjectionMatrix = function () { return this; };
  Frustum.prototype.intersectsSphere = function (s) {
    return Math.abs(s.c[0]) <= 100 && Math.abs(s.c[1]) <= 100
      && Math.abs(s.c[2]) <= 100; };
  const THREE = { Vector3: V3, Box3: Box3, Sphere: Sphere,
    Matrix4: Matrix4, Frustum: Frustum };

  const meshes = o.meshes || [
    { isMesh: true, __box: [0, 0, 0, 10, 3, 8] },
    { isMesh: true, __box: [10, 0, 0, 14, 3, 8] },
    { isMesh: true, __box: [-4, 0, -4, 0, 3, 0] }
  ];
  const nonMeshes = o.nonMeshes === undefined ? 4 : o.nonMeshes;
  const scene = { updateMatrixWorld: function () { scene.__updated = true; },
    __updated: false,
    traverse: function (fn) {
      for (let i = 0; i < nonMeshes; i++) fn({ isMesh: false });
      meshes.forEach(fn); } };
  const camera = { position: new V3(11, 9, 13), fov: 52, aspect: 1.6,
    near: 0.11, far: 4321, projectionMatrix: new Matrix4(),
    matrixWorldInverse: new Matrix4(),
    updateMatrixWorld: function () { } };
  const orbit = { target: new V3(3.5, 1.5, 4.5) };

  /* سياق WebGL مزيَّف يكتب نمط بكسلات معلوماً بالضبط */
  const PW = 320, PH = 180;
  const gl = {
    RGBA: 6408, UNSIGNED_BYTE: 5121, RENDERER: 7937,
    __lost: !!o.contextLost,
    isContextLost: function () { return this.__lost; },
    getExtension: function (n) { return null; },
    getParameter: function (n) { return 'ACS-STUB-GPU/9.9'; },
    readPixels: function (x, y, w, h, f2, t, buf) {
      if (o.readPixelsThrows) throw new Error('readPixels refused');
      for (let i = 0; i < w * h; i++) {
        const on = (i % 4 === 0);            /* ربع البكسلات غير صفري بالضبط */
        buf[i * 4] = on ? 20 : 0;
        buf[i * 4 + 1] = on ? 40 : 0;
        buf[i * 4 + 2] = on ? 60 : 0;
        buf[i * 4 + 3] = 255; } }
  };
  const domElement = { width: PW, height: PH, clientWidth: 1600,
    clientHeight: 900 };
  const renderer = {
    domElement: domElement,
    getContext: function () { if (o.noContext) throw new Error('no ctx');
      return gl; },
    capabilities: o.noCaps ? null : { isWebGL2: true },
    info: o.noInfo ? {} : { render: { calls: 137, triangles: 246810 } },
    xr: { enabled: true, isPresenting: false, getSession: function () {
      return null; } }
  };
  const anchors = [];
  const doc = { body: { appendChild: function () { } },
    createElement: function (t) {
      if (t === 'a') { const a = { click: function () { a.__clicked = true; },
        remove: function () { }, setAttribute: function () { } };
        anchors.push(a); return a; }
      return { width: 0, height: 0, getContext: function () { return null; } }; },
    getElementById: function () { return null; } };
  const created = [];
  const win = {
    devicePixelRatio: 2.5,
    ACS_BUILD_INFO: o.buildInfo === undefined
      ? { git_sha: 'stub0ffee1234567', label: 'L', substituted: true }
      : o.buildInfo,
    ACS: {},
    __ACS_PQ__: { applied: { profile: 'ULTRA' }, composer: o.composer || null },
    __ACS_AD__: { applied: { detail: 'DETAIL_HIGH' } },
    __ACS_RR__: { postprocess_fail_open: null },
    fetch: function () { net.fetch++; throw new Error('network refused'); },
    XMLHttpRequest: function () { net.xhr++;
      throw new Error('network refused'); },
    WebSocket: function () { net.ws++; throw new Error('network refused'); },
    navigator: { sendBeacon: function () { net.beacon++; return false; },
      xr: {} }
  };
  const scope = {
    window: win, document: doc, THREE: THREE,
    renderer: renderer, scene: scene, camera: camera, orbit: orbit,
    lastBuilding: o.lastBuilding === undefined
      ? { site: { w: 30, d: 24 }, levels: [] } : o.lastBuilding,
    modelRevision: function () {
      return { model_hash: 'stubhash0011223344',
        revision_id: 'rev:stubhash00112233' }; },
    Blob: function (parts) { this.__bytes = String(parts[0]).length;
      created.push(this); },
    URL: { createObjectURL: function () { return 'blob:acs-stub-url'; },
      revokeObjectURL: function () { } },
    setTimeout: function () { return 0; },
    performance: { now: function () { return 1234.5; } },
    navigator: win.navigator,
    devicePixelRatio: win.devicePixelRatio,
    fetch: win.fetch, XMLHttpRequest: win.XMLHttpRequest,
    WebSocket: win.WebSocket
  };
  const names = Object.keys(scope);
  const fn = new Function(names.join(','), BLOCK + '\n;return window.ACS;');
  const api = fn.apply(null, names.map(k => scope[k]));
  return { api: api, net: net, scope: scope, anchors: anchors,
    blobs: created, PW: PW, PH: PH };
}

console.log('\n== §3 — THE CONTRACT RETURNS EXACTLY ITS DECLARED KEYS ==');
let E = null;
try { E = makeEnv({}); } catch (e) {
  chk('the diagnostics block evaluates in a controlled scope', false,
    e.message); }
if (E) {
  chk('the diagnostics block evaluates in a controlled scope', true);
  const D = E.api.renderDiagnostics();
  chk('renderDiagnostics is a function', typeof E.api.renderDiagnostics
    === 'function');
  chk('captureRenderFailure is a function', typeof E.api.captureRenderFailure
    === 'function');
  const keys = Object.keys(D).sort();
  chk('every required key is present (' + REQUIRED.length + ')',
      REQUIRED.every(k => k in D),
      JSON.stringify(REQUIRED.filter(k => !(k in D))));
  chk('there is NO key beyond the declared contract',
      keys.length === REQUIRED.length,
      JSON.stringify(keys.filter(k => REQUIRED.indexOf(k) < 0)));
  chk('the key set is exactly the declared set',
      JSON.stringify(keys) === JSON.stringify(REQUIRED.slice().sort()));

  console.log('\n== §4 — EVERY VALUE IS MEASURED, NOT FABRICATED ==');
  chk('build_sha comes from window.ACS_BUILD_INFO',
      D.build_sha === 'stub0ffee1234567', String(D.build_sha));
  chk('model_hash and revision_id come from the canonical model, not invented',
      D.model_hash === 'stubhash0011223344'
      && D.revision_id === 'rev:stubhash00112233',
      JSON.stringify([D.model_hash, D.revision_id]));
  chk('canvas_size is read from the real canvas backing and CSS size',
      D.canvas_size.width === E.PW && D.canvas_size.height === E.PH
      && D.canvas_size.css_width === 1600 && D.canvas_size.css_height === 900,
      JSON.stringify(D.canvas_size));
  chk('device_pixel_ratio is the browser value, not 1',
      D.device_pixel_ratio === 2.5, String(D.device_pixel_ratio));
  chk('webgl_version comes from renderer.capabilities',
      D.webgl_version === 2, String(D.webgl_version));
  chk('renderer is the string the GL context reports',
      D.renderer === 'ACS-STUB-GPU/9.9', String(D.renderer));
  chk('object_count counts EVERY scene object, not only meshes',
      D.object_count === 7, String(D.object_count));
  chk('mesh_count counts meshes only', D.mesh_count === 3,
      String(D.mesh_count));
  chk('draw_calls comes from renderer.info.render.calls',
      D.draw_calls === 137, String(D.draw_calls));
  chk('triangle_count comes from renderer.info.render.triangles',
      D.triangle_count === 246810, String(D.triangle_count));
  chk('scene_bounds is the real union of the walked mesh boxes',
      JSON.stringify(D.scene_bounds.min) === JSON.stringify([-4, 0, -4])
      && JSON.stringify(D.scene_bounds.max) === JSON.stringify([14, 3, 8]),
      JSON.stringify(D.scene_bounds));
  chk('scene_bounds records how many meshes it actually measured',
      D.scene_bounds.measured_meshes === 3);
  chk('camera_position and camera_target are read from the live camera and '
      + 'orbit target',
      JSON.stringify(D.camera_position) === JSON.stringify([11, 9, 13])
      && JSON.stringify(D.camera_target) === JSON.stringify([3.5, 1.5, 4.5]));
  chk('near and far are the live clip planes',
      D.near === 0.11 && D.far === 4321);
  chk('frustum_intersections is counted against a real frustum test',
      D.frustum_intersections === 3, String(D.frustum_intersections));
  chk('invalid_coordinate_count is zero for a healthy scene',
      D.invalid_coordinate_count === 0);
  chk('max_coordinate_abs is the true largest absolute bound',
      D.max_coordinate_abs === 14, String(D.max_coordinate_abs));
  chk('render_mode reflects the state actually applied',
      typeof D.render_mode === 'string' && D.render_mode.indexOf('PBR:') === 0
      && D.render_mode.indexOf('AD:') > 0, String(D.render_mode));
  chk('postprocessing reports the real composer state',
      D.postprocessing.composer_active === false
      && D.postprocessing.pass_count === null);
  chk('xr_state is read from renderer.xr',
      D.xr_state.enabled === true && D.xr_state.presenting === false
      && D.xr_state.session === false);
  chk('context_lost is read from the GL context', D.context_lost === false);
  chk('the scene world matrices were updated BEFORE anything was measured',
      E.scope.scene.__updated === true);

  console.log('\n== §5 — THE PIXEL PROBE READS REAL PIXELS ==');
  const PB = D.pixel_probe;
  chk('the probe used readPixels on the framebuffer',
      PB.method === 'READ_PIXELS', String(PB.method));
  chk('it sampled the real canvas area (%d)'.replace('%d', E.PW * E.PH),
      PB.sampled === E.PW * E.PH, String(PB.sampled));
  chk('the non-zero pixel count matches the pattern exactly (one in four)',
      PB.non_zero_pixels === (E.PW * E.PH) / 4,
      String(PB.non_zero_pixels));
  chk('the non-zero percentage is computed, not assumed',
      PB.non_zero_pct === 25, String(PB.non_zero_pct));
  const expMean = ((0.2126 * 20 + 0.7152 * 40 + 0.0722 * 60) / 4);
  chk('the mean luminance matches the pattern to three decimals',
      Math.abs(PB.luminance_mean - Math.round(expMean * 1000) / 1000) < 1e-9,
      PB.luminance_mean + ' vs ' + expMean);
  chk('the maximum luminance is the real per-pixel maximum',
      Math.abs(PB.max_luminance
        - Math.round((0.2126 * 20 + 0.7152 * 40 + 0.0722 * 60) * 1000) / 1000)
      < 1e-9, String(PB.max_luminance));
  chk('viewportBlank calls the probe a non-blank viewport at 25% coverage',
      E.api.viewportBlank().blank === false);

  console.log('\n== §6 — WHAT CANNOT BE MEASURED IS null, NEVER A NUMBER ==');
  const E2 = makeEnv({ buildInfo: null, noCaps: true, noInfo: true,
    lastBuilding: null, readPixelsThrows: true, contextLost: false });
  const D2 = E2.api.renderDiagnostics();
  chk('an absent ACS_BUILD_INFO yields build_sha null, not a placeholder',
      D2.build_sha === null, String(D2.build_sha));
  chk('no loaded model yields model_hash and revision_id null',
      D2.model_hash === null && D2.revision_id === null);
  chk('absent renderer capabilities yield webgl_version null, not 1',
      D2.webgl_version === null, String(D2.webgl_version));
  chk('absent renderer.info yields draw_calls and triangle_count null, not 0',
      D2.draw_calls === null && D2.triangle_count === null,
      JSON.stringify([D2.draw_calls, D2.triangle_count]));
  chk('a failing readPixels yields null pixel numbers and a stated reason, '
      + 'never an invented count',
      D2.pixel_probe.non_zero_pixels === null
      && D2.pixel_probe.luminance_mean === null
      && typeof D2.pixel_probe.reason === 'string'
      && D2.pixel_probe.reason.length > 0,
      JSON.stringify(D2.pixel_probe));
  chk('the contract key set is unchanged in the degraded case',
      JSON.stringify(Object.keys(D2).sort())
      === JSON.stringify(REQUIRED.slice().sort()));
  chk('viewportBlank reports null — not "fine" — when it cannot see pixels',
      E2.api.viewportBlank().blank === null);
  const E3 = makeEnv({ contextLost: true });
  const D3 = E3.api.renderDiagnostics();
  chk('a lost context is reported as lost, and the probe says so',
      D3.context_lost === true
      && D3.pixel_probe.non_zero_pixels === null
      && String(D3.pixel_probe.reason).indexOf('CONTEXT_LOST') >= 0,
      JSON.stringify(D3.pixel_probe));
  const E4 = makeEnv({ meshes: [
    { isMesh: true, __box: [0, 0, 0, 10, 3, 8] },
    { isMesh: true, __box: [NaN, 0, 0, 1, 1, 1] },
    { isMesh: true, __box: [0, 0, 0, Infinity, 1, 1] }] });
  const D4 = E4.api.renderDiagnostics();
  chk('a non-finite mesh bound is COUNTED as invalid, not silently averaged in',
      D4.invalid_coordinate_count === 2, String(D4.invalid_coordinate_count));
  chk('and it does not poison the reported bounds',
      D4.scene_bounds.min.every(Number.isFinite)
      && D4.scene_bounds.max.every(Number.isFinite),
      JSON.stringify(D4.scene_bounds));

  console.log('\n== §7 — captureRenderFailure UPLOADS NOTHING (EXECUTED) ==');
  const E5 = makeEnv({});
  const R = E5.api.captureRenderFailure();
  chk('the capture ran and produced a report', !!R && !!R.report_json);
  chk('not one network primitive was called during the capture',
      E5.net.fetch === 0 && E5.net.xhr === 0 && E5.net.beacon === 0
      && E5.net.ws === 0, JSON.stringify(E5.net));
  chk('the trap is not vacuous: calling the trapped fetch DOES register',
      (function () { try { E5.scope.window.fetch(); } catch (e) { }
        return E5.net.fetch === 1; })());
  chk('the report states no upload happened and names no upload target',
      R.uploaded === false && R.upload_target === null
      && R.transmits_anything === false);
  chk('a Blob was created and an object URL handed to a local download anchor',
      E5.blobs.length === 1 && R.download.object_url === 'blob:acs-stub-url'
      && E5.anchors.length === 1 && E5.anchors[0].__clicked === true);
  chk('the report carries the fixed-key diagnostics',
      !!R.diagnostics
      && JSON.stringify(Object.keys(R.diagnostics).sort())
      === JSON.stringify(REQUIRED.slice().sort()));
  chk('the report carries the camera configuration and the render mode',
      !!R.camera && R.camera.near === 0.11 && R.camera.far === 4321
      && R.camera.fov === 52 && typeof R.render_mode === 'string');
  chk('the report carries the current Building JSON when it is safe to attach',
      R.building_json_included === true
      && JSON.stringify(R.building_json.site) === '{"w":30,"d":24}');
  chk('the report carries the build identity',
      !!R.build_info && R.build_info.git_sha === 'stub0ffee1234567');
  chk('the report says whether the viewport was blank, measured not assumed',
      !!R.viewport_blank && R.viewport_blank.blank === false);
  const E6 = makeEnv({ lastBuilding: null });
  const R6 = E6.api.captureRenderFailure();
  chk('with no model loaded the Building JSON is omitted WITH a stated reason',
      R6.building_json_included === false
      && R6.building_json_excluded_reason === 'NO_MODEL_LOADED');
  chk('the produced JSON is valid JSON and self-describing',
      (function () { try { const o = JSON.parse(R.report_json);
        return o.contract === 'acs-render-failure/1.0.0'; }
        catch (e) { return false; } })());
}

function headWindow() {
  const doc = { readyState: 'complete',
    addEventListener: function () { },
    getElementById: function () { return null; },
    createElement: function () { return { click: function () { },
      remove: function () { }, setAttribute: function () { } }; },
    body: { appendChild: function () { } } };
  const w = { ACS_BUILD_INFO: null, ACS_BOOT_ERRORS: null,
    addEventListener: function () { }, __doc: doc };
  return w;
}
console.log('\n== §8 — THE BUILD IDENTITY IS A PLACEHOLDER, NOT A FAKE ==');
/* F-09/F-11 — السكربت الكلاسيكي خرج من الصفحة إلى public/app/boot/build-info.js
   (الصفحة لا تحمل جافاسكربت تنفيذياً مضمّناً بعد الآن). يُقرأ من ملفّه، ويُشترط
   أن تُحمّله القشرة قبل وحدة التطبيق — وإلّا بقيت window.ACS_BUILD_INFO غائبة
   عند إقلاع الوحدات. */
const BUILD_INFO_REL = 'boot/build-info.js';
const BUILD_SRC = BOOTJS[BUILD_INFO_REL] || '';
chk('the build-identity script ships as a classic boot script file',
    BUILD_SRC.length > 800, String(BUILD_SRC.length));
['__ACS_GIT_SHA__', '__ACS_BUILT_AT__', '__ACS_FRONTEND_VERSION__']
  .forEach(t => chk('the exact substitution token ' + t + ' ships in the '
    + 'build-identity boot script', BUILD_SRC.indexOf(t) >= 0));
chk('window.ACS_BUILD_INFO is defined by a classic <head> script that the '
    + 'shell loads BEFORE the application module',
    (function () {
      const s = SHELL.indexOf('<script src="/app/' + BUILD_INFO_REL + '">');
      const m = SHELL.indexOf('<script type="module" src="/app/main.js">');
      return BUILD_SRC.indexOf('window.ACS_BUILD_INFO = INFO;') >= 0
        && s > 0 && m > 0 && s < m
        && SHELL.slice(0, SHELL.indexOf('</head>')).indexOf(
          '<script src="/app/' + BUILD_INFO_REL + '">') >= 0;
    })());
chk('the boot script is classic, not a module — it must run before the module '
    + 'graph, and a deferred module would be too late',
    /<script src="\/app\/boot\/build-info\.js"><\/script>/.test(SHELL)
    && !/type="module"[^>]*build-info/.test(SHELL));
chk('an unsubstituted build reports null for every field and declares itself '
    + 'UNPROVENANCED',
    (function () {
      const s = BUILD_SRC.indexOf('(function(){');
      const src = BUILD_SRC.slice(s);
      const w = headWindow();
      new Function('window', 'document', 'URL', 'Blob', 'setTimeout',
        'navigator', src)(w, w.__doc, {}, function () { },
        function () { return 0; }, { userAgent: 'test' });
      const B = w.ACS_BUILD_INFO;
      return B && B.git_sha === null && B.built_at === null
        && B.frontend_version === null && B.substituted === false
        && B.provenance === 'UNPROVENANCED' && B.fabricated === false;
    })());
chk('a substituted build reports the real values and declares itself '
    + 'provenanced',
    (function () {
      const s = BUILD_SRC.indexOf('(function(){');
      let src = BUILD_SRC.slice(s);
      src = src.replace('"__ACS_GIT_SHA__"', '"abc123def456"')
        .replace('"__ACS_BUILT_AT__"', '"2026-08-14T00:00:00Z"')
        .replace('"__ACS_FRONTEND_VERSION__"', '"10.0.0"');
      const w = headWindow();
      new Function('window', 'document', 'URL', 'Blob', 'setTimeout',
        'navigator', src)(w, w.__doc, {}, function () { },
        function () { return 0; }, { userAgent: 'test' });
      const B = w.ACS_BUILD_INFO;
      return B && B.git_sha === 'abc123def456' && B.substituted === true
        && B.provenance === 'BUILD_SUBSTITUTED' && B.short === 'abc123def456'
        && B.label.indexOf('10.0.0') === 0;
    })());

console.log('\n== §9 — THE VISIBLE, KEYBOARD-REACHABLE UI ACTION ==');
/* العلامة تُقرأ من القشرة وحدها: زرٌّ «موجود» لأن نصّه صادف وقوعه في سلسلة
   جافاسكربت ليس زرّاً في الـDOM. البحث في SHELL يجعل هذه التوكيدات أشدّ. */
const BTN = (function () {
  const i = SHELL.indexOf('id="acsDiagBtn"');
  if (i < 0) return '';
  return SHELL.slice(SHELL.lastIndexOf('<button', i), SHELL.indexOf('</button>', i));
})();
chk('the download action exists in the hand-written DOM', BTN.length > 40);
chk('it is a real <button>, so it is focusable and Enter/Space activate it '
    + 'natively', /^<button/.test(BTN) && /type="button"/.test(BTN));
chk('it is not hidden from the keyboard or the accessibility tree',
    BTN.indexOf('tabindex="-1"') < 0 && BTN.indexOf('aria-hidden') < 0
    && BTN.indexOf('disabled') < 0);
chk('it carries both labels: تنزيل التشخيص and Download diagnostics',
    BTN.indexOf('تنزيل التشخيص') >= 0
    && BTN.indexOf('Download diagnostics') >= 0);
chk('it carries an aria-label', /aria-label="[^"]{5,}"/.test(BTN));
chk('the action lives OUTSIDE every generated DOM block',
    (function () {
      const i = SHELL.indexOf('id="acsDiagBtn"');
      const g = SHELL.indexOf('<!-- ===== ACS WORKSPACE DOM (generated) ===== -->');
      return i > 0 && g > 0 && i < g;
    })());
chk('the build identifier is rendered in a visible system-info area',
    SHELL.indexOf('id="acsBuildId"') >= 0
    && SHELL.indexOf('معلومات النظام والتشخيص') >= 0);
chk('the status line is announced to assistive technology',
    /id="acsDiagState"[^>]*aria-live="polite"/.test(SHELL));
chk('the page tells the user the file is not uploaded anywhere',
    SHELL.indexOf('ولا يُرفع إلى أيّ خادوم') >= 0);
/* F-11 — الزرّ يعمل بلا معالج مضمّن: سياسة الأمن الصارمة تحظر onclick= في
   العلامة، فلو اعتمد عليه لكان زرّاً ميّتاً في الإنتاج. */
chk('the download action carries NO inline event-handler attribute — the '
    + 'strict CSP would make one dead code',
    !/\son[a-z]+=/.test(BTN), BTN.slice(0, 160));

console.log('\n== §10 — F-07 PARITY: ONE PLATE CONTRACT IN BOTH LANGUAGES ==');
const PYPOL = JSON.parse(py(
  'import json,acs_pbr;print(json.dumps(acs_pbr.PLATE_POLICY,sort_keys=True))'));
const JSPOL = (function () {
  const i = APP.indexOf('const PQ_PLATE_POLICY=');
  const j = APP.indexOf(';\n', i);
  return JSON.parse(APP.slice(i + 'const PQ_PLATE_POLICY='.length, j));
})();
chk('the browser policy mirror is byte-identical to the Python source',
    JSON.stringify(JSPOL, Object.keys(JSPOL).sort())
    === JSON.stringify(PYPOL, Object.keys(PYPOL).sort()),
    JSON.stringify(JSPOL));
chk('the policy names the new convention and records the old one',
    JSPOL.policy === 'PHASE10_FOOTPRINT_PLATE'
    && JSPOL.previous_policy === 'PHASE1_SITE_WIDE_PLATE'
    && JSPOL.previous_pinned_by === 'PHASE4_GOLDEN_BASELINE');
chk('pqPlatePolicy is exposed on the browser contract surface',
    APP.indexOf('platePolicy:pqPlatePolicy') >= 0);
/* المطابقة الحقيقية: نفس المُدخَلات إلى plate_rect و pqPlateRect و
   slab_strips و slabStrips، والمخرَجات تُقارَن رقماً برقم. */
const CASES = [
  { rooms: [[8, 5, 6, 5], [14, 5, 8, 5], [8, 10, 6, 8], [14, 10, 8, 8]],
    site: [0, 0, 40, 32] },
  { rooms: [[2, 2, 16, 6], [2, 8, 6, 12]], site: [0, 0, 30, 24] },
  { rooms: [], site: [0, 0, 30, 24] },
  { rooms: [[0, 0, 60, 40]], site: [0, 0, 60, 40] }
];
const PYP = JSON.parse(py('import json,acs_pbr\n'
  + 'cs=json.loads(' + JSON.stringify(JSON.stringify(CASES)) + ')\n'
  + 'print(json.dumps([acs_pbr.plate_rect(c["rooms"],c["site"]) for c in cs],'
  + 'sort_keys=True))'));
CASES.forEach((c, i) => {
  const j = pqPlateRect(c.rooms, c.site);
  chk('plate_rect parity, case ' + (i + 1) + ': same source and same rectangle',
      j.source === PYP[i].source
      && JSON.stringify(j.rect) === JSON.stringify(PYP[i].rect),
      JSON.stringify([j, PYP[i]]));
});
const SCASES = [
  { p: [4, 4, 18, 10], h: [[9.4, 6.9, 1.2, 4.2]] },
  { p: [0, 0, 30, 24], h: [] },
  { p: [0, 0, 10, 10], h: [[50, 50, 2, 2]] },
  { p: [0, 0, 12, 12], h: [[2, 2, 3, 3], [7, 7, 3, 3]] }
];
const PYS = JSON.parse(py('import json,acs_pbr\n'
  + 'cs=json.loads(' + JSON.stringify(JSON.stringify(SCASES)) + ')\n'
  + 'print(json.dumps([acs_pbr.slab_strips(c["p"][0],c["p"][1],c["p"][2],'
  + 'c["p"][3],c["h"]) for c in cs]))'));
SCASES.forEach((c, i) => {
  const j = slabStrips(c.p[0], c.p[1], c.p[2], c.p[3], c.h);
  chk('slab strip parity, case ' + (i + 1) + ': identical strips, same order',
      j.length === PYS[i].length
      && j.every((s, k) => s.every((v, m) =>
        Math.abs(v - PYS[i][k][m]) < 1e-9)),
      JSON.stringify([j, PYS[i]]));
});

console.log('\n== §11 — THE PLATE CHANGE IS CONFINED TO SLAB MESHES ==');
(function () {
  const OLD = _np.join(HERE, 'fixtures', 'plate',
    'mesh_baseline_phase1_site_wide.json');
  const NOW = _np.join(ROOT, 'tests', 'phase3', 'fixtures',
    'mesh_baseline.json');
  if (!fs.existsSync(OLD) || !fs.existsSync(NOW)) {
    chk('the pre-change geometry baseline is archived beside the tests', false);
    return; }
  chk('the pre-change geometry baseline is archived beside the tests', true);
  const a = JSON.parse(fs.readFileSync(OLD, 'utf8'));
  const b = JSON.parse(fs.readFileSync(NOW, 'utf8'));
  chk('both baselines cover the same models',
      JSON.stringify(a.map(r => r.model)) === JSON.stringify(b.map(r => r.model)));
  let nonSlab = [], slabDiffs = 0;
  a.forEach((ra, i) => {
    const ma = {}, mb = {};
    ra.tree.forEach(t => { ma[t[0]] = JSON.stringify(t); });
    b[i].tree.forEach(t => { mb[t[0]] = JSON.stringify(t); });
    const all = new Set(Object.keys(ma).concat(Object.keys(mb)));
    all.forEach(k => {
      if (ma[k] === mb[k]) return;
      if (/^FLOOR\|.*\|slab\|/.test(k)) { slabDiffs++; return; }
      nonSlab.push(ra.model + ' ' + k); }); });
  chk('the change moved real geometry (it is not a no-op)', slabDiffs > 0,
      String(slabDiffs) + ' slab mesh(es) changed');
  chk('NOT ONE non-slab mesh changed name, visibility, position, size or '
      + 'rotation', nonSlab.length === 0,
      JSON.stringify(nonSlab.slice(0, 8)));
})();

console.log('\n== §12 — THE NINE RENDER STATES: WHAT IS AND IS NOT VERIFIED ==');
const BOOT = fs.readFileSync(_np.join(ROOT, 'tests', 'deploy',
  'verify_page_boot.js'), 'utf8');
const STATES = ['BASE (no presentation layer applied)', 'PBR OFF / DETAIL OFF',
  'PBR ON (HIGH, REALISTIC, SKY)', 'POST PROCESS (ULTRA, composer + SSAO)',
  'ARCHDETAIL STANDARD / CONTEXT NONE', 'CONTEXT SITE', 'CONTEXT LANDSCAPE',
  'ENGINEERING (compare mode restored)',
  'VR-CAPABLE FALLBACK (xr enabled, not presenting)'];
STATES.forEach(s => chk('the existing browser matrix was EXTENDED with the '
  + 'state: ' + s, BOOT.indexOf("['" + s + "'") >= 0));
chk('the extended matrix asserts non-zero visible pixels per state',
    BOOT.indexOf('non-zero visible pixels were probed') >= 0);
chk('the extended matrix asserts no NaN or infinite camera per state',
    BOOT.indexOf('no NaN or infinite camera value') >= 0);
chk('the extended matrix asserts valid scene bounds per state',
    BOOT.indexOf('scene bounds are finite and') >= 0);
chk('the extended matrix asserts the fixed-key contract per state',
    BOOT.indexOf('exactly its declared keys') >= 0);
chk('no parallel matrix was created: the states live in the existing harness',
    BOOT.indexOf('const MODES = [') >= 0);
const VENDOR = _np.join(ROOT, 'public', 'vendor');
const HAVE_THREE = fs.existsSync(VENDOR)
  && fs.readdirSync(VENDOR).length > 0;
chk('the harness refuses to pass without a real renderer: it exits 2 rather '
    + 'than claiming a result',
    BOOT.indexOf('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED') >= 0
    && /process\.exit\(2\)/.test(BOOT));
console.log('  ── vendored Three.js present: ' + HAVE_THREE);
if (!HAVE_THREE) {
  console.log('  NINE RENDER STATES: NOT VERIFIED — EXTERNAL ENVIRONMENT '
    + 'REQUIRED');
  console.log('  reason: public/vendor is empty and this sandbox has no '
    + 'network, so Three.js cannot load and no frame can be rendered.');
  console.log('  no pixel was rendered for those states here and none is '
    + 'claimed. Run: sh tools/vendor.sh && node '
    + 'tests/deploy/verify_page_boot.js');
}

/* الجزء الوحيد الذي يمكن تنفيذه في Chromium حقيقي بلا Three.js: السكربت
   الكلاسيكي لهوية البناء، وعنصر DOM المكتوب يدوياً. يُنفَّذ فعلاً هنا. */
console.log('\n== §13 — REAL CHROMIUM: WHAT DOES NOT NEED THREE.js ==');
let CHROME = null;
try {
  CHROME = JSON.parse(execFileSync(process.execPath, ['-e', `
    (async () => {
      const { chromium } = require(${JSON.stringify(
        _np.join(ROOT, 'node_modules', 'playwright'))});
      const path = require('path'), fs = require('fs'), http = require('http');
      const PUB = ${JSON.stringify(_np.join(ROOT, 'public'))};
      /* F-09/F-11 — الصفحة صارت قشرة تحمّل وحدات ES وورقة أنماط خارجية.
         نوع المحتوى الخاطئ يمنع تحميل الوحدة أصلاً (المتصفّح يشترط نوع
         جافاسكربت لـ type="module")، والسياسة تُبَثّ رأساً حقيقياً كما في
         الإنتاج، فما يُقاس هنا هو ما يجري هناك — لا بيئة متساهلة. */
      const CSP = ${JSON.stringify((function () {
        const nt = fs.readFileSync(_np.join(ROOT, 'netlify.toml'), 'utf8');
        const m = /Content-Security-Policy\\s*=\\s*"([^"]+)"/.exec(nt);
        return m ? m[1] : '';
      })())};
      const MIME = { '.html': 'text/html; charset=utf-8',
        '.js': 'text/javascript; charset=utf-8',
        '.mjs': 'text/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8', '.json': 'application/json',
        '.png': 'image/png', '.svg': 'image/svg+xml', '.txt': 'text/plain',
        '.xml': 'application/xml' };
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
      await new Promise(r => srv.listen(0, '127.0.0.1', r));
      const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
      const pg = await b.newPage();
      const bad = [];
      pg.on('response', r => { if (r.status() >= 400)
        bad.push(r.status() + ' ' + r.url()); });
      await pg.addInitScript(() => {
        window.__CSPV = [];
        document.addEventListener('securitypolicyviolation',
          e => window.__CSPV.push(e.violatedDirective + ' ' + e.blockedURI));
      });
      await pg.goto('http://127.0.0.1:' + srv.address().port + '/index.html',
        { waitUntil: 'domcontentloaded' });
      const out = await pg.evaluate(() => {
        const btn = document.getElementById('acsDiagBtn');
        const peer = document.getElementById('bShot');   /* ضابط: زرّ قائم */
        /* يُقاس قبل أي تعديل من الفاحص نفسه، فقياس بعده يقيس أثر الفاحص
           لا الوثيقة المشحونة. */
        const inlineStyleAttrs = document.querySelectorAll('[style]').length;
        /* لوح الأدوات كلّه مخفيّ ما لم يُقلع سكربت الوحدة (لا Three.js هنا).
           نُظهر نفس السلف الذي يُظهره التطبيق عند فتح التبويب، ثم نقيس زرّنا
           وزرّاً قائماً بجانبه بنفس المسطرة — فلا يمرّ زرّ مخفيّ بخصوصية.

           F-11 — الإظهار يجري بنزع الصنف acs-hidden، وهو بالضبط ما يفعله
           التطبيق المشحون (classList.toggle في ui/workspace-ui-wiring.js).
           الحيلة القديمة (e.style.display='block') صارت بلا أثر لسببين معاً:
           القاعدة الخارجية .acs-hidden{display:none!important} تغلب أي
           نمط سطري، والسياسة الصارمة لا تسمح بنمط سطري أصلاً. لو بقيت،
           لقاس هذا الفحص زرّاً لم يُعرَض قطّ وأعلن ذلك فشلاً أبدياً. */
        let e = btn;
        while (e && e !== document.body) {
          e.classList.remove('acs-hidden');
          e = e.parentElement;
        }
        if (getComputedStyle(btn).display === 'none'
            || btn.getBoundingClientRect().width === 0)
          throw new Error('the shipped mechanism did not reveal acsDiagBtn: '
            + 'display=' + getComputedStyle(btn).display
            + ' width=' + btn.getBoundingClientRect().width);
        btn.focus();
        const gl = document.createElement('canvas').getContext('webgl2');
        return {
          build: window.ACS_BUILD_INFO,
          btn_present: !!btn,
          btn_tag: btn ? btn.tagName : null,
          btn_aria: btn ? btn.getAttribute('aria-label') : null,
          btn_focused: document.activeElement === btn,
          btn_visible: btn ? btn.getBoundingClientRect().width > 0 : false,
          btn_tabindex: btn ? btn.tabIndex : null,
          peer_present: !!peer,
          peer_visible: peer ? peer.getBoundingClientRect().width > 0 : false,
          same_pane: !!(peer && btn && peer.closest('div.body')
            === btn.closest('div.body')),
          build_id_el: !!document.getElementById('acsBuildId'),
          build_id_text: (document.getElementById('acsBuildId') || {})
            .textContent || null,
          webgl2: !!gl,
          /* F-09 — الأنماط خرجت من الصفحة إلى ورقة خارجية: إن لم تُحمَّل عاد
             كل قياس تخطيط أعلاه بلا معنى. تُقاس بقاعدة مشحونة فيها. */
          stylesheets: document.styleSheets.length,
          css_rules: (function () { let n = 0;
            for (const s of document.styleSheets) {
              try { n += s.cssRules.length; } catch (e) { }
            } return n; })(),
          inline_style_attrs: inlineStyleAttrs,
          csp_violations: (window.__CSPV || []).slice(0, 8),
          three_loaded: typeof window.ACS === 'object' && !!window.ACS.ready
        };
      });
      /* /vendor/ غائب في هذا الصندوق بلا شبكة — يُفصَل صراحةً عن
         أصول التطبيق حتى لا يخفي غيابُه سقوطَ وحدةٍ حقيقيّ ولا يزيّف نجاحاً */
      out.bad_responses = bad.filter(x => x.indexOf('/vendor/') < 0).slice(0, 8);
      out.bad_vendor = bad.filter(x => x.indexOf('/vendor/') >= 0).length;
      await b.close(); srv.close();
      console.log(JSON.stringify(out));
    })().catch(e => { console.log(JSON.stringify({ error: String(e.message) })); });
  `], { encoding: 'utf8', timeout: 120000 }).trim().split('\n').pop());
} catch (e) { CHROME = { error: String(e.message).slice(0, 200) }; }
if (CHROME && !CHROME.error) {
  chk('real Chromium: the classic build-identity script ran before anything '
      + 'else and produced ACS_BUILD_INFO',
      !!CHROME.build && CHROME.build.contract === 'acs-build-info/1.0.0');
  chk('real Chromium: an unsubstituted build is visibly UNPROVENANCED, not '
      + 'silently fake',
      CHROME.build.git_sha === null && CHROME.build.substituted === false
      && CHROME.build.provenance === 'UNPROVENANCED',
      JSON.stringify(CHROME.build));
  chk('real Chromium: the diagnostics button exists and is a real button',
      CHROME.btn_present && CHROME.btn_tag === 'BUTTON');
  chk('real Chromium: it lives in the SAME shipped panel as the existing '
      + 'export controls — no special placement, no special hiding',
      CHROME.peer_present === true && CHROME.same_pane === true);
  chk('real Chromium: once that panel is shown, the button lays out with a '
      + 'real box, exactly like its neighbour',
      CHROME.btn_visible === true && CHROME.peer_visible === true,
      JSON.stringify([CHROME.btn_visible, CHROME.peer_visible]));
  chk('real Chromium: the button takes keyboard focus and is in the tab order',
      CHROME.btn_focused === true && CHROME.btn_tabindex >= 0,
      JSON.stringify([CHROME.btn_focused, CHROME.btn_tabindex]));
  chk('real Chromium: the build identifier renders visible text',
      typeof CHROME.build_id_text === 'string'
      && CHROME.build_id_text.length > 3, String(CHROME.build_id_text));
  chk('real Chromium: the button carries an aria-label',
      typeof CHROME.btn_aria === 'string' && CHROME.btn_aria.length > 5,
      String(CHROME.btn_aria));
  chk('real Chromium: the build identifier element is rendered',
      CHROME.build_id_el === true);
  chk('real Chromium: WebGL2 IS available here — the missing piece is '
      + 'Three.js, not the GPU stack', CHROME.webgl2 === true);
  /* F-09/F-11 — يُقاس هذا تحت رأس السياسة الإنتاجي الحقيقي ونوع محتوى صحيح */
  chk('real Chromium: the EXTERNAL stylesheet loaded and its rules applied — '
      + 'the layout measured above is the shipped layout, not a bare document',
      CHROME.stylesheets >= 1 && CHROME.css_rules > 200,
      JSON.stringify([CHROME.stylesheets, CHROME.css_rules]));
  chk('real Chromium: not one element carries a style= attribute in the '
      + 'served DOM — the strict CSP forbids it and the utility classes '
      + 'replaced them',
      CHROME.inline_style_attrs === 0, String(CHROME.inline_style_attrs));
  chk('real Chromium: the production CSP raised NO violation while the shell, '
      + 'the boot scripts and the stylesheet loaded',
      Array.isArray(CHROME.csp_violations) && CHROME.csp_violations.length === 0,
      JSON.stringify(CHROME.csp_violations));
  chk('real Chromium: every APPLICATION asset the shell asks for was served — '
      + 'no 404 for a boot script, a module or the stylesheet',
      Array.isArray(CHROME.bad_responses) && CHROME.bad_responses.length === 0,
      JSON.stringify(CHROME.bad_responses));
  console.log('  ── /vendor/ requests that 404ed here: ' + CHROME.bad_vendor
    + ' — NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (public/vendor is '
    + 'empty in this sandbox; Netlify populates it at build time)');
  console.log('  ── real Chromium reports module ready = '
    + CHROME.three_loaded + ' (false is expected without vendored Three.js)');
} else {
  console.log('  REAL CHROMIUM: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED ('
    + ((CHROME || {}).error || 'chromium unavailable') + ')');
}

console.log('\n' + '─'.repeat(62));
if (!HAVE_THREE) {
  console.log('NINE RENDER STATES IN A REAL RENDERER: NOT VERIFIED — '
    + 'EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  this file verifies the diagnostics CONTRACT, not rasterised '
    + 'frames. The real-renderer matrix is '
    + 'tests/deploy/verify_page_boot.js, which exits 2 — never 0 — while '
    + 'Three.js is unvendored. Nothing below counts a rendered frame.');
}
console.log('WEBGL DIAGNOSTICS: ' + pass + ' passed, ' + fail + ' failed'
  + (HAVE_THREE ? '' : '  (nine render states: NOT VERIFIED)'));
if (fail) process.exit(1);
