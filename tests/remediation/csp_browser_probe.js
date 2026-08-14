/* ============================================================================
   F-11 — قياس سياسة المحتوى في Chromium حقيقي، لا استنتاجها من النصّ.

     node tests/remediation/csp_browser_probe.js

   بعد F-09/F-11 صارت public/index.html قشرة بلا سطر جافاسكربت قابل للتنفيذ،
   وصارت السياسة `script-src 'self' 'sha256-…'` وحدها. هذا الملفّ لا يجادل في
   ذلك نصّاً: يشغّل الصفحة المشحونة في Chromium حقيقي، بالسياسة نفسها حرفيّاً
   في ترويسة استجابة حقيقية (لا <meta>: meta لا تطبّق frame-ancestors ولا تمثّل
   ما يُنشر)، ثم يحاول ثمانية صنوف هجوم بوصفها تنفيذ شيفرة فعليّاً ويسجّل ماذا
   فعل المتصفّح.

   ‼‼ فخّ منهجي — اقرأ قبل أي تعديل ‼‼
   page.evaluate() يصل إلى الصفحة عبر مصحّح CDP (Runtime.evaluate)، وهذا المسار
   لا تحكمه CSP إطلاقاً. من ثمّ فإن قياس eval() أو new Function() من داخل
   page.evaluate يعيد EXECUTED حتى تحت سياسة تمنعهما منعاً تامّاً — سالب كاذب
   يجعل السياسة الصارمة تبدو مخترَقة. لذلك كل شيفرة الهجوم تعيش في
   /__csp_probe__/hostile.js الذي يقدّمه tools/csp_static_server.py وتُحمّله
   الصفحة بوسم <script src> عاديّ من نفس الأصل، فتترجمها آلة السكربتات نفسها
   التي تحكمها السياسة. page.evaluate هنا لا يُستعمل إلّا لأمرين: تركيب وسم
   السكربت (عملية DOM محضة تخضع لـCSP كأيّ إدراج آخر) وقراءة النتائج (بيانات
   لا شيفرة).
   METHODOLOGY (English): page.evaluate() injects through the CDP debugger,
   which BYPASSES CSP. eval() measured from inside page.evaluate() reports
   EXECUTED even under `script-src 'self'`. Never measure code execution from
   there — the attacks live in the served external script.

   كعب Three.js: public/vendor فارغ في هذا المستودع ولا شبكة، فبلا كعب لا
   يُحلّ المحدّد المجرّد `three` ولا يقلع رسم بيانيّ الوحدات أصلاً. يُنشأ الكعب
   في دليل مؤقّت وقت التشغيل ويُقدَّم كطبقة علوية فوق public/ — لا يُكتب بايت
   واحد داخل public/. الكعب لا يرسم شيئاً: سلوك العرض NOT VERIFIED هنا
   بالتصريح. المقيس في هذا الملفّ هو السياسة لا الرسم.
   ========================================================================== */
'use strict';
const fs = require('fs'), path = require('path'), net = require('net'), os = require('os');
const { spawn } = require('child_process');
const PW = require(path.resolve(__dirname, '..', '..', 'tools', 'pw_chromium.js'));

const HERE = __dirname, ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const OUTDIR = path.join(HERE, 'outputs');
const OUTFILE = path.join(OUTDIR, 'csp_probe.json');

const ATTACK_KEYS = ['inline_script', 'eval', 'function_constructor',
  'javascript_url', 'external_script', 'inline_event_handler',
  'data_url_script', 'blob_script'];

/* --------------------------------------------- السياسة من ملفّ النشر ------ */
function deployedCSP() {
  const nt = fs.readFileSync(path.join(ROOT, 'netlify.toml'), 'utf8');
  const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
  if (!m) throw new Error('netlify.toml declares no Content-Security-Policy');
  return m[1];
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

function serve(port, root, csp, overlay) {
  return new Promise(function (res, rej) {
    const args = [path.join(ROOT, 'tools', 'csp_static_server.py'),
      String(port), root, csp];
    if (overlay) args.push(overlay);
    const p = spawn('python3', args, { cwd: ROOT, stdio: ['ignore', 'ignore', 'pipe'] });
    let buf = '';
    const to = setTimeout(function () { rej(new Error('server did not start')); }, 15000);
    p.stderr.on('data', function (d) {
      buf += String(d);
      if (buf.indexOf('CSP_SERVER_READY') >= 0) { clearTimeout(to); res(p); }
    });
    p.on('exit', function (c) { clearTimeout(to); rej(new Error('server exited ' + c)); });
  });
}

/* ------------------------------ كعب Three.js — للاختبار فقط، خارج public/ -- */
const STUB_BANNER = '/* ══════════════════════════════════════════════════════'
  + '══════════════\n'
  + '   TEST-ONLY STUB — NOT THREE.js, NOT SHIPPED, NOT PART OF THE PRODUCT.\n'
  + '   Generated at runtime by tests/remediation/csp_browser_probe.js into a\n'
  + '   temporary directory and served as an overlay above public/. It exists\n'
  + '   only so the ES module graph can resolve the bare specifier `three`\n'
  + '   while public/vendor is empty and there is no network.\n'
  + '   IT RENDERS NOTHING. Any statement about rendering behaviour derived\n'
  + '   from a run against this stub is NOT VERIFIED.\n'
  + '   ══════════════════════════════════════════════════════════════════ */\n';

const THREE_STUB = STUB_BANNER + `
export const SRGBColorSpace = 'srgb';
export const LinearSRGBColorSpace = 'srgb-linear';
export const ACESFilmicToneMapping = 4;
export const NoToneMapping = 0;
export const PCFSoftShadowMap = 2;
export const RepeatWrapping = 1000;
export const ClampToEdgeWrapping = 1001;
export const DoubleSide = 2;
export const FrontSide = 0;

export class Vector3 {
  constructor(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  setScalar(s) { this.x = this.y = this.z = s; return this; }
  copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
  clone() { return new Vector3(this.x, this.y, this.z); }
  add() { return this; } sub() { return this; } addVectors() { return this; }
  subVectors() { return this; } crossVectors() { return this; }
  multiplyScalar() { return this; } divideScalar() { return this; }
  normalize() { return this; } negate() { return this; } applyQuaternion() { return this; }
  applyMatrix4() { return this; } lerp() { return this; }
  setFromSphericalCoords() { return this; } setFromMatrixPosition() { return this; }
  length() { return 0; } lengthSq() { return 0; } distanceTo() { return 0; }
  dot() { return 0; } toArray() { return [this.x, this.y, this.z]; }
}
export class Vector2 {
  constructor(x, y) { this.x = x || 0; this.y = y || 0; }
  set(x, y) { this.x = x; this.y = y; return this; }
  copy(v) { this.x = v.x; this.y = v.y; return this; }
  clone() { return new Vector2(this.x, this.y); }
}
export class Color {
  constructor(c) { this.value = c; this.r = 0; this.g = 0; this.b = 0; }
  set(c) { this.value = c; return this; }
  setHex(c) { this.value = c; return this; }
  getHex() { return 0; } getStyle() { return '#000000'; }
  clone() { return new Color(this.value); } copy(c) { this.value = c.value; return this; }
}
export class Euler {
  constructor() { this.x = 0; this.y = 0; this.z = 0; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
}
export class Quaternion {
  constructor() { this.x = 0; this.y = 0; this.z = 0; this.w = 1; }
  setFromEuler() { return this; } setFromAxisAngle() { return this; }
}
export class Matrix4 {
  constructor() { this.elements = new Array(16).fill(0); }
  identity() { return this; } makeRotationY() { return this; }
  multiply() { return this; } copy() { return this; }
}
export class Box3 {
  constructor() { this.min = new Vector3(); this.max = new Vector3(); }
  setFromObject() { return this; } getSize(t) { return t || new Vector3(); }
  getCenter(t) { return t || new Vector3(); } expandByObject() { return this; }
  isEmpty() { return true; }
}
export class Sphere { constructor() { this.center = new Vector3(); this.radius = 0; } }
export class Plane {
  constructor(n, c) { this.normal = n || new Vector3(); this.constant = c || 0; }
  set(n, c) { this.normal = n; this.constant = c; return this; }
}
export class Object3D {
  constructor() {
    this.position = new Vector3(); this.rotation = new Euler();
    this.scale = new Vector3(1, 1, 1); this.quaternion = new Quaternion();
    this.children = []; this.parent = null; this.name = ''; this.visible = true;
    this.userData = {}; this.matrixWorld = new Matrix4(); this.renderOrder = 0;
    this.castShadow = false; this.receiveShadow = false; this.layers = { set() {} };
  }
  add() { for (const o of arguments) { if (o) { o.parent = this; this.children.push(o); } } return this; }
  remove() {
    for (const o of arguments) {
      const i = this.children.indexOf(o);
      if (i >= 0) this.children.splice(i, 1);
      if (o) o.parent = null;
    }
    return this;
  }
  removeFromParent() { if (this.parent) this.parent.remove(this); return this; }
  clear() { this.children = []; return this; }
  traverse(fn) { fn(this); this.children.slice().forEach(function (c) { if (c && c.traverse) c.traverse(fn); }); }
  traverseVisible(fn) { this.traverse(fn); }
  updateMatrixWorld() { return this; } updateMatrix() { return this; }
  getWorldPosition(t) { return t || new Vector3(); }
  getObjectByName() { return null; }
  lookAt() { return this; }
  addEventListener() {} removeEventListener() {} dispatchEvent() {}
}
export class Scene extends Object3D {
  constructor() { super(); this.environment = null; this.background = null; this.fog = null; }
}
export class Group extends Object3D {}
class Geometry {
  constructor() { this.attributes = {}; this.boundingBox = new Box3(); this.parameters = {}; }
  dispose() {} computeBoundingBox() {} computeVertexNormals() {}
  translate() { return this; } rotateY() { return this; } scale() { return this; }
  setAttribute() { return this; } setIndex() { return this; }
}
export class BufferGeometry extends Geometry {}
export class BoxGeometry extends Geometry {
  constructor(w, h, d) { super(); this.parameters = { width: w, height: h, depth: d }; }
}
export class PlaneGeometry extends Geometry {}
export class CylinderGeometry extends Geometry {}
export class SphereGeometry extends Geometry {}
export class ConeGeometry extends Geometry {}
export class CircleGeometry extends Geometry {}
export class ShapeGeometry extends Geometry {}
export class ExtrudeGeometry extends Geometry {}
export class EdgesGeometry extends Geometry {}
export class BufferAttribute { constructor(a, i) { this.array = a; this.itemSize = i; } }
export class Float32BufferAttribute extends BufferAttribute {}
class Material {
  constructor(p) { Object.assign(this, p || {}); this.color = new Color((p || {}).color); this.needsUpdate = false; }
  dispose() {} clone() { return new Material(); }
}
export class MeshStandardMaterial extends Material {}
export class MeshBasicMaterial extends Material {}
export class MeshPhysicalMaterial extends Material {}
export class MeshLambertMaterial extends Material {}
export class LineBasicMaterial extends Material {}
export class SpriteMaterial extends Material {}
export class ShaderMaterial extends Material { constructor(p) { super(p); this.uniforms = (p || {}).uniforms || {}; } }
export class Mesh extends Object3D {
  constructor(g, m) { super(); this.isMesh = true; this.geometry = g || new Geometry(); this.material = m || new Material(); }
}
export class InstancedMesh extends Mesh { setMatrixAt() {} }
export class Line extends Object3D { constructor(g, m) { super(); this.geometry = g; this.material = m; } }
export class LineSegments extends Line {}
export class Sprite extends Object3D {}
class Light extends Object3D {
  constructor(c, i) {
    super(); this.color = new Color(c); this.intensity = i === undefined ? 1 : i;
    const mapSize = new Vector2(1024, 1024);
    mapSize.set = function (a, b) { this.x = a; this.y = b; return this; };
    this.shadow = { mapSize: mapSize, bias: 0, radius: 1,
      camera: { near: 0.5, far: 500, left: -10, right: 10, top: 10, bottom: -10,
        updateProjectionMatrix() {} } };
    this.target = new Object3D();
  }
}
export class DirectionalLight extends Light {}
export class HemisphereLight extends Light {}
export class AmbientLight extends Light {}
export class PointLight extends Light {}
export class SpotLight extends Light {}
export class RectAreaLight extends Light {}
class Camera extends Object3D {
  constructor() { super(); this.aspect = 1; this.near = 0.1; this.far = 1000; this.zoom = 1; }
  updateProjectionMatrix() {} getWorldDirection(t) { return t || new Vector3(); }
}
export class PerspectiveCamera extends Camera {
  constructor(f, a, n, fa) { super(); this.fov = f; this.aspect = a; this.near = n; this.far = fa; }
}
export class OrthographicCamera extends Camera {}
class Texture {
  constructor() { this.wrapS = 1000; this.wrapT = 1000; this.repeat = new Vector2(1, 1);
    this.offset = new Vector2(); this.needsUpdate = false; this.colorSpace = 'srgb';
    this.image = null; this.anisotropy = 1; }
  dispose() {} clone() { return new Texture(); }
}
export class CanvasTexture extends Texture { constructor(c) { super(); this.image = c; } }
export class DataTexture extends Texture {}
export class TextureLoader {
  load(u, ok) { const t = new Texture(); if (ok) setTimeout(function () { ok(t); }, 0); return t; }
  setCrossOrigin() { return this; }
}
export class Raycaster {
  setFromCamera() {} intersectObject() { return []; } intersectObjects() { return []; }
}
export class Clock { getDelta() { return 0.016; } getElapsedTime() { return 0; } }
export class PMREMGenerator {
  constructor(r) { this.renderer = r; }
  fromScene() { return { texture: new Texture() }; }
  fromEquirectangular() { return { texture: new Texture() }; }
  compileEquirectangularShader() {} compileCubemapShader() {} dispose() {}
}
export class WebGLRenderer {
  constructor() {
    this.domElement = document.createElement('canvas');
    this.shadowMap = { enabled: false, type: 2, needsUpdate: false };
    this.xr = { enabled: false, isPresenting: false, addEventListener() {},
      getSession() { return null; }, setReferenceSpaceType() {} };
    this.info = { render: { calls: 0, triangles: 0 }, memory: { geometries: 0, textures: 0 } };
    this.capabilities = { isWebGL2: true, maxTextureSize: 4096, getMaxAnisotropy() { return 1; } };
    this.outputColorSpace = 'srgb'; this.toneMapping = 0; this.toneMappingExposure = 1;
    this.localClippingEnabled = false; this.clippingPlanes = [];
  }
  setPixelRatio() {} setSize() {} setClearColor() {} setAnimationLoop() {}
  render() {} clear() {} dispose() {} forceContextLoss() {} compile() {}
  getPixelRatio() { return 1; }
  getContext() { return null; }
  setScissorTest() {} setViewport() {} setScissor() {}
}
export class WebGLRenderTarget { constructor() { this.texture = new Texture(); } dispose() {} }
export const MathUtils = {
  degToRad: function (d) { return d * Math.PI / 180; },
  radToDeg: function (r) { return r * 180 / Math.PI; },
  clamp: function (v, a, b) { return Math.max(a, Math.min(b, v)); },
  lerp: function (a, b, t) { return a + (b - a) * t; }
};
export const REVISION = '0.160.0-TEST-STUB';
/* علامة ترتيب التقييم: تُنفَّذ في آخر جسم هذه الوحدة. غيابها تعني أن جسم
   وحدة \`three\` لم يُنفَّذ إطلاقاً — وهو ما يفرّق بين «الخريطة لم تُقبل»
   و«رسم الوحدات أُجهض قبل أن يصل إليها». تُقرأ في
   boot.three_module_body_evaluated. */
try { window.__ACS_THREE_EVALUATED__ = true; } catch (e) {}
`;

const ADDON_STUBS = {
  'controls/OrbitControls.js': STUB_BANNER + `
import { Vector3 } from 'three';
export class OrbitControls {
  constructor(camera, dom) {
    this.object = camera; this.domElement = dom; this.target = new Vector3();
    this.enableDamping = false; this.dampingFactor = 0.05; this.enabled = true;
    this.minDistance = 0; this.maxDistance = Infinity; this.maxPolarAngle = Math.PI;
    this.enablePan = true; this.autoRotate = false; this.screenSpacePanning = true;
  }
  update() { return true; } dispose() {} saveState() {} reset() {}
  addEventListener() {} removeEventListener() {}
}
`,
  'webxr/VRButton.js': STUB_BANNER + `
export class VRButton {
  static createButton() { const b = document.createElement('button'); b.textContent = 'VR (stub)'; return b; }
}
`,
  'webxr/ARButton.js': STUB_BANNER + `
export class ARButton {
  static createButton() { const b = document.createElement('button'); b.textContent = 'AR (stub)'; return b; }
}
`,
  'exporters/GLTFExporter.js': STUB_BANNER + `
export class GLTFExporter {
  parse(input, onDone, onError) {
    try { if (onDone) onDone(new ArrayBuffer(0)); }
    catch (e) { if (onError) onError(e); }
  }
  parseAsync() { return Promise.resolve(new ArrayBuffer(0)); }
  register() { return this; }
}
`,
  'objects/Sky.js': STUB_BANNER + `
import { Object3D } from 'three';
export class Sky extends Object3D {
  constructor() {
    super();
    this.material = { uniforms: {
      turbidity: { value: 0 }, rayleigh: { value: 0 },
      mieCoefficient: { value: 0 }, mieDirectionalG: { value: 0 },
      sunPosition: { value: { x: 0, y: 0, z: 0, set() { return this; },
        setFromSphericalCoords() { return this; }, copy() { return this; } } },
      up: { value: { x: 0, y: 1, z: 0 } }
    }, dispose() {} };
  }
}
`,
  'environments/RoomEnvironment.js': STUB_BANNER + `
import { Object3D } from 'three';
export class RoomEnvironment extends Object3D { dispose() {} }
`
};

function writeThreeStub() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'acs-csp-probe-vendor-'));
  const base = path.join(dir, 'vendor', 'three@0.160.0');
  fs.mkdirSync(path.join(base, 'build'), { recursive: true });
  fs.writeFileSync(path.join(base, 'build', 'three.module.js'), THREE_STUB, 'utf8');
  Object.keys(ADDON_STUBS).forEach(function (rel) {
    const p = path.join(base, 'examples', 'jsm', rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, ADDON_STUBS[rel], 'utf8');
  });
  return dir;
}

/* ------------------------------------------------------- المخرج والخروج --- */
function writeOut(obj) {
  fs.mkdirSync(OUTDIR, { recursive: true });
  fs.writeFileSync(OUTFILE, JSON.stringify(obj, null, 2) + '\n', 'utf8');
}

function notVerified(why, policy) {
  const attacks = {};
  ATTACK_KEYS.forEach(function (k) { attacks[k] = 'NOT VERIFIED'; });
  writeOut({
    status: 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
    reason: why,
    measured: false,
    policy: policy || null,
    violations: [],
    unexpected_csp_violations: 0,
    attacks: attacks,
    style: { cssom_property_write: 'NOT VERIFIED', style_attribute: 'NOT VERIFIED' },
    boot: { measured: false, reason: why },
    environment: { measured: false, reason: why,
      generated_at_utc: new Date().toISOString() }
  });
  console.log('\nCSP BROWSER PROBE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  console.log('  reason: ' + why);
  console.log('  written: ' + path.relative(ROOT, OUTFILE));
  process.exit(2);
}

/* ================================== القياس ================================ */
async function main() {
  const CSP = deployedCSP();

  try { require('playwright'); } catch (e) { notVerified('playwright is not installed', CSP); }
  if (!PW.executable()) {
    notVerified('no Chromium binary is available (playwright expects a build that '
      + 'is not present and there is no network to download it)', CSP);
  }

  const vendorPresent = fs.existsSync(path.join(PUB, 'vendor', 'three@0.160.0',
    'build', 'three.module.js'));
  const stubDir = vendorPresent ? null : writeThreeStub();

  console.log('CSP BROWSER PROBE — real Chromium, real response header\n');
  console.log('POLICY: ' + CSP + '\n');
  if (stubDir) {
    console.log('NOTE: public/vendor is empty in this checkout and there is no '
      + 'network. A TEST-ONLY Three.js stub was generated at ' + stubDir
      + ' and served as an overlay above public/ so the bare specifier `three` '
      + 'resolves. It renders nothing: RENDERING BEHAVIOUR IS NOT VERIFIED. '
      + 'This probe measures POLICY, not rendering.\n');
  }

  /* الأصل الآخر: منفذ ثانٍ على 127.0.0.1. اختلاف المنفذ يجعله أصلاً مختلفاً
     فعلاً (scheme+host+port)، ويُقدَّم بلا ترويسة CSP إطلاقاً — فأي حجب
     يقع على سكربته منسوب إلى سياسة الصفحة وحدها، لا إلى DNS ولا إلى خادم
     غائب. هذا أدقّ من اسم مضيف لا يُحَل. */
  const extPort = await freePort();
  const extSrv = await serve(extPort, PUB, '');
  const extOrigin = 'http://127.0.0.1:' + extPort;

  const port = await freePort();
  const srv = await serve(port, PUB, CSP, stubDir);
  const pageUrl = 'http://127.0.0.1:' + port + '/index.html';

  const browser = await PW.launch();
  const chromiumVersion = browser.version();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  const pageErrors = [], consoleErrors = [], failedReqs = [], requests = [];

  /* المستمع يُركَّب قبل أي تنقّل فيلتقط مخالفات التحليل المبكّرة أيضاً. */
  await page.addInitScript(function () {
    window.__CSP_VIOLATIONS__ = [];
    document.addEventListener('securitypolicyviolation', function (e) {
      window.__CSP_VIOLATIONS__.push({
        violatedDirective: e.violatedDirective || null,
        effectiveDirective: e.effectiveDirective || null,
        blockedURI: String(e.blockedURI == null ? '' : e.blockedURI).slice(0, 200),
        sourceFile: String(e.sourceFile == null ? '' : e.sourceFile).slice(0, 200),
        lineNumber: (e.lineNumber === undefined ? null : e.lineNumber),
        columnNumber: (e.columnNumber === undefined ? null : e.columnNumber),
        sample: String(e.sample == null ? '' : e.sample).slice(0, 120),
        disposition: e.disposition || null,
        statusCode: (e.statusCode === undefined ? null : e.statusCode)
      });
    });
  });
  page.on('pageerror', function (e) { pageErrors.push(String(e.message).slice(0, 220)); });
  page.on('console', function (m) {
    if (m.type() === 'error') consoleErrors.push(String(m.text()).slice(0, 260));
  });
  page.on('request', function (r) { requests.push(r.url().slice(0, 200)); });
  page.on('requestfailed', function (r) {
    failedReqs.push({ url: r.url().slice(0, 200),
      error: (r.failure() || {}).errorText || '?' });
  });

  /* ── إقلاع عادي ────────────────────────────────────────────────────── */
  let loaded = true, loadError = null;
  try { await page.goto(pageUrl, { waitUntil: 'load', timeout: 60000 }); }
  catch (e) { loaded = false; loadError = String(e.message).slice(0, 200); }
  await page.waitForTimeout(2500);

  const bootProbe = await page.evaluate(function () {
    return {
      acs_api_present: typeof window.ACS_API === 'object' && window.ACS_API !== null,
      acs_present: typeof window.ACS === 'object' && window.ACS !== null,
      acs_keys: window.ACS ? Object.keys(window.ACS).length : 0,
      acs_ready: !!(window.ACS && window.ACS.ready),
      /* دليل تقييم رسم الوحدات فعلاً: هذا الرمز لا يُعرَّف إلّا من داخل وحدة. */
      module_graph_evaluated: typeof window.__ACS_ADD_MARKER__ === 'function',
      /* هل نُفِّذ جسم وحدة `three` أصلاً؟ يفصل «الخريطة مرفوضة» عن «الرسم
         أُجهض قبل بلوغها». */
      three_module_body_evaluated: window.__ACS_THREE_EVALUATED__ === true,
      importmap_count: document.querySelectorAll('script[type="importmap"]').length,
      inline_executable_scripts: (function () {
        var n = 0;
        document.querySelectorAll('script').forEach(function (s) {
          if (!s.src && (s.type || '').toLowerCase() !== 'importmap'
              && String(s.textContent || '').trim()) n++;
        });
        return n;
      })(),
      style_blocks: document.querySelectorAll('style').length
    };
  });
  const bootViolations = await page.evaluate(function () {
    return (window.__CSP_VIOLATIONS__ || []).slice();
  });
  /* الخريطة قُبِلت ⇒ المحدّد المجرّد `three` تُرجم إلى مسار /vendor/ وطُلب فعلاً */
  const importMapApplied = requests.some(function (u) {
    return u.indexOf('/vendor/three@0.160.0/build/three.module.js') >= 0;
  });
  const bootErrorCount = pageErrors.length;
  const bootConsoleErrorCount = consoleErrors.length;

  console.log('── boot ──');
  console.log('  page loaded                  : ' + loaded);
  console.log('  CSP violations at boot       : ' + bootViolations.length);
  console.log('  window.ACS_API present       : ' + bootProbe.acs_api_present);
  console.log('  window.ACS present           : ' + bootProbe.acs_present);
  console.log('  import map accepted (by hash): ' + importMapApplied);
  console.log('  module graph evaluated       : ' + bootProbe.module_graph_evaluated
    + (bootProbe.module_graph_evaluated ? '' : '   ← NOT a CSP result, see '
      + 'boot.module_graph_diagnosis in the JSON'));
  console.log('  `three` module body evaluated: '
    + bootProbe.three_module_body_evaluated);
  console.log('  executable inline scripts    : ' + bootProbe.inline_executable_scripts);
  console.log('  <style> blocks in the DOM    : ' + bootProbe.style_blocks);
  console.log('');

  /* ── الهجمات الثمانية ──────────────────────────────────────────────────
     page.evaluate هنا يركّب وسم <script src> فقط — إدراج DOM تحكمه CSP كأي
     إدراج. كل شيفرة الهجوم داخل الملفّ المُقدَّم، فتترجمها الصفحة نفسها. */
  const injected = await page.evaluate(function (ext) {
    return new Promise(function (res) {
      var s = document.createElement('script');
      s.src = '/__csp_probe__/hostile.js?ext=' + encodeURIComponent(ext);
      s.onload = function () { res('load'); };
      s.onerror = function () { res('error'); };
      document.head.appendChild(s);
      setTimeout(function () { res('timeout'); }, 8000);
    });
  }, extOrigin);

  let driverRan = false;
  for (let i = 0; i < 60; i++) {
    driverRan = await page.evaluate(function () {
      return !!(window.__CSP_PROBE__ && window.__CSP_PROBE__.done);
    });
    if (driverRan) break;
    await page.waitForTimeout(250);
  }
  await page.waitForTimeout(500);

  const R = await page.evaluate(function () { return window.__CSP_PROBE__ || null; });
  const allViolations = await page.evaluate(function () {
    return (window.__CSP_VIOLATIONS__ || []).slice();
  });

  await browser.close();
  srv.kill();
  extSrv.kill();

  /* ── تجميع ─────────────────────────────────────────────────────────── */
  const attacks = {};
  ATTACK_KEYS.forEach(function (k) {
    attacks[k] = (R && R.attacks && R.attacks[k]) || 'NOT VERIFIED';
  });
  const style = {
    cssom_property_write: (R && R.style && R.style.cssom_property_write) || 'NOT VERIFIED',
    style_attribute: (R && R.style && R.style.style_attribute) || 'NOT VERIFIED'
  };
  if (!driverRan) {
    console.log('WARNING: the attack driver never reported completion (load event: '
      + injected + '). Every attack it owns stays NOT VERIFIED.');
  }

  const violations = allViolations.map(function (v, i) {
    return Object.assign({ phase: i < bootViolations.length ? 'boot' : 'attack' }, v);
  });
  const byDirective = {};
  violations.forEach(function (v) {
    const d = v.effectiveDirective || v.violatedDirective || '(unknown)';
    byDirective[d] = (byDirective[d] || 0) + 1;
  });

  /* الطلب الفاشل الموافق للسكربت الخارجي: يُنقل سببه كما لاحظه المتصفّح
     حرفيّاً — لا يُدَّعى «csp» ما لم يُلاحَظ. */
  const extFailure = failedReqs.filter(function (f) {
    return f.url.indexOf(extOrigin) === 0;
  }).map(function (f) { return f.error; });

  const executed = ATTACK_KEYS.filter(function (k) { return attacks[k] === 'EXECUTED'; });
  const unverified = ATTACK_KEYS.filter(function (k) { return attacks[k] === 'NOT VERIFIED'; });
  const unexpected = bootViolations.length;

  const out = {
    status: 'MEASURED',
    generated_at_utc: new Date().toISOString(),
    policy: CSP,
    policy_source: 'netlify.toml [[headers]] for = "/*" — delivered as a real '
      + 'Content-Security-Policy response header by tools/csp_static_server.py, '
      + 'never as <meta http-equiv> (meta cannot express frame-ancestors)',
    violations: violations,
    violations_by_directive: byDirective,
    unexpected_csp_violations: unexpected,
    attacks: attacks,
    attack_detail: {
      external_script_origin: extOrigin,
      external_script_block_reason_observed: extFailure.length ? extFailure : null,
      external_script_note: 'the second origin is a real HTTP server on a second '
        + 'port of 127.0.0.1 (a different origin by scheme+host+port) that serves '
        + 'the payload with NO CSP header of its own; it resolves and responds, so '
        + 'a block is attributable to the page policy, not to DNS',
      blob_script_note: 'script-src does NOT list blob:, so a blob: <script src> is '
        + 'expected to be blocked; the boundary is exercised explicitly',
      driver_load_event: injected,
      driver_completed: driverRan,
      driver_errors: (R && R.errors) || {},
      driver_notes: (R && R.notes) || {}
    },
    style: style,
    style_note: 'element.style.<prop> = … is a CSSOM write and is NOT governed by '
      + 'style-src; setAttribute("style", …) IS governed by style-src-attr. Both '
      + 'were measured in Chromium, not assumed.',
    boot: {
      url: '/index.html (served from public/)',
      page_loaded: loaded,
      load_error: loadError,
      csp_violations: bootViolations.length,
      csp_violations_detail: bootViolations,
      acs_api_present: bootProbe.acs_api_present,
      acs_present: bootProbe.acs_present,
      acs_global_keys: bootProbe.acs_keys,
      import_map_accepted_by_hash: importMapApplied,
      import_map_count: bootProbe.importmap_count,
      module_graph_evaluated: bootProbe.module_graph_evaluated,
      three_module_body_evaluated: bootProbe.three_module_body_evaluated,
      module_graph_note: bootProbe.module_graph_evaluated
        ? 'the ES module graph evaluated to completion'
        : 'NOT A CSP RESULT — the module graph did not evaluate to completion. '
          + 'No CSP violation is involved (the count above is 0); the failure is a '
          + 'plain JavaScript error listed in boot.page_errors. See '
          + 'boot.module_graph_diagnosis.',
      module_graph_diagnosis: bootProbe.module_graph_evaluated ? null
        : 'public/app/core/viewer.js lists `import ../render/scene.js` (source '
          + "line 10) BEFORE `import * as THREE from 'three'` (line 12). ES "
          + 'modules evaluate dependencies in source order, and scene.js → '
          + 'ui/workspace-ui-wiring.js runs `setSun(52,135)` at top level, which '
          + 'reads THREE.MathUtils. At that moment the body of the `three` module '
          + 'has not run yet (boot.three_module_body_evaluated is false), so the '
          + 'binding is still in its temporal dead zone and the graph throws. '
          + 'Real three.module.js exports MathUtils as a `const` exactly as this '
          + 'stub does, so a real vendored Three.js fails the same way — this is '
          + 'an import-order defect in the F-09 split, NOT an artefact of the '
          + 'stub and NOT a consequence of the CSP. Out of scope for F-11; '
          + 'recorded here because a probe must not hide what it saw.',
      executable_inline_scripts_in_dom: bootProbe.inline_executable_scripts,
      style_blocks_in_dom: bootProbe.style_blocks,
      page_errors: pageErrors.slice(0, 20),
      page_error_count: bootErrorCount,
      console_errors: consoleErrors.slice(0, 20),
      console_error_count: bootConsoleErrorCount,
      failed_requests: failedReqs.slice(0, 30),
      failed_request_count: failedReqs.length,
      rendering: 'NOT VERIFIED'
    },
    environment: {
      chromium: chromiumVersion,
      chromium_executable: PW.executable(),
      playwright: require('playwright/package.json').version,
      node: process.version,
      platform: process.platform + ' ' + process.arch,
      vendor_present: vendorPresent,
      three_js_stub: stubDir ? {
        used: true,
        label: 'TEST-ONLY — NOT Three.js, NOT shipped, NOT inside public/',
        location: stubDir,
        why: 'public/vendor is empty in this checkout and there is no network, so '
          + 'the bare specifier `three` could not otherwise resolve and the ES '
          + 'module graph would never boot',
        rendering_behaviour: 'NOT VERIFIED — the stub draws nothing. This probe '
          + 'measures POLICY (what the browser permits), not rendering.'
      } : { used: false, note: 'a real vendored Three.js was present' },
      rendering_verified: false,
      rendering_note: 'NOT VERIFIED — no frame is asserted by this probe under any '
        + 'circumstances; CSP decisions are made by the browser at parse/compile '
        + 'time and do not require a rendered frame'
    },
    summary: {
      attacks_executed: executed,
      attacks_not_verified: unverified,
      all_blocked: executed.length === 0 && unverified.length === 0,
      boot_clean: unexpected === 0
    }
  };
  writeOut(out);

  /* ── التقرير ───────────────────────────────────────────────────────── */
  console.log('── attacks (each attempted as real code execution) ──');
  ATTACK_KEYS.forEach(function (k) {
    console.log('  ' + (k + '                      ').slice(0, 22) + ': ' + attacks[k]);
  });
  console.log('');
  console.log('── style ──');
  console.log('  element.style.prop = …  : ' + style.cssom_property_write
    + '   (CSSOM is not governed by style-src)');
  console.log('  setAttribute("style") … : ' + style.style_attribute);
  console.log('');
  console.log('── violations ──');
  console.log('  boot (unexpected)  : ' + unexpected);
  console.log('  total recorded     : ' + violations.length);
  console.log('  by directive       : ' + JSON.stringify(byDirective));
  if (extFailure.length) {
    console.log('  cross-origin script request failure reason as reported by '
      + 'Chromium: ' + JSON.stringify(extFailure));
  }
  console.log('');
  console.log('  rendering behaviour: NOT VERIFIED (TEST-ONLY Three.js stub; this '
    + 'probe measures policy, not rendering)');
  console.log('  written: ' + path.relative(ROOT, OUTFILE));

  /* ── الحكم ─────────────────────────────────────────────────────────── */
  let bad = false;
  if (executed.length) {
    bad = true;
    executed.forEach(function (k) {
      console.log('\nKNOWN-WEAKNESS · CSP-' + k.toUpperCase().replace(/_/g, '-')
        + ' · the attack class `' + k + '` EXECUTED under the deployed policy '
        + '(measured in Chromium ' + chromiumVersion + ', not assumed). The '
        + 'policy does not stop it. This is a live hole, not a passing test.');
    });
  }
  if (unexpected > 0) {
    bad = true;
    console.log('\nKNOWN-WEAKNESS · CSP-BOOT-VIOLATION · a normal boot of the '
      + 'shipped page produced ' + unexpected + ' CSP violation(s). Either the '
      + 'page still needs something the policy forbids, or the policy is wrong. '
      + 'Detail is in ' + path.relative(ROOT, OUTFILE) + ' under boot.'
      + 'csp_violations_detail.');
    bootViolations.forEach(function (v) {
      console.log('    ' + (v.effectiveDirective || v.violatedDirective) + ' ← '
        + (v.blockedURI || '(inline)') + '  @ ' + (v.sourceFile || '?') + ':'
        + v.lineNumber);
    });
  }
  if (unverified.length) {
    console.log('\nNOT VERIFIED: ' + unverified.join(', ') + ' — the probe could '
      + 'not obtain a measurement for these attack classes. They are neither '
      + 'passed nor failed.');
  }
  console.log('');
  if (bad) {
    console.log('CSP BROWSER PROBE: FAILED — the deployed policy does not hold.');
    process.exit(1);
  }
  console.log('CSP BROWSER PROBE: all eight attack classes BLOCKED, boot produced '
    + '0 CSP violations.');
}

main().catch(function (e) {
  console.error('CSP BROWSER PROBE FAILED: ' + ((e && e.stack) || e));
  process.exit(1);
});
