/* ============================================================================
   tests/remediation/lib_gl_three.js — بديل `three` **يرسم فعلاً** بـWebGL2.

   لماذا يوجد هذا الملفّ
   ---------------------
   السؤال في KI-25 سؤال بكسلات: هل الهندسة التي يخرجها ‎compile()‎ المشحون،
   بالكاميرا التي يحسبها عقد ‎pqCameraFit‎ المشحون، تُرسَم فعلاً؟ كعبٌ صامت لا
   يجيب عنه بحال. يستخدم الاختبار هذا المنفّذ صراحةً حتى لو توفّر three؛
   وجود المكتبة في public/vendor لا يحوّل هذا المنفّذ إلى three.js.

   فبدل الادّعاء أو الصمت: يفتح هذا الملفّ سياق ‎webgl2‎ حقيقياً من اللوحة،
   ويصرّف زوج تظليل حقيقيّاً، ويرفع رؤوس مكعّب وحدة إلى مخزن حقيقيّ، ويرسم كل
   ‎Mesh‎ بمصفوفة نموذج×عرض×إسقاط محسوبة هنا. ‎readPixels‎ بعده يقرأ ما رسمه
   العتاد لا ما نزعمه.

   حدوده معلَنة: هذا ليس three.js. لا يقيس شجرة مشهد three ولا خاماتها ولا
   ظلالها ولا معالجتها اللاحقة. يقيس أن **هندسة المترجم قابلة للرسم** وأن
   عودة عطل KI-25 تجعلها غير قابلة له. ما بقي:
       LIVE FRONTEND APPLY (three.js): NOT VERIFIED — EXTERNAL ENVIRONMENT
       REQUIRED
   ========================================================================== */

export const __ACS_REAL_THREE = false;
export const __ACS_GL_SUBSTITUTE = 'acs.gl-three/1.0.0';

/* A context object survives context loss. Never count a zero-initialized
   readback buffer or attempted draw calls as evidence of a rendered frame. */
export function assertGLContext(gl, stage) {
  if (!gl) throw new Error('WEBGL_CONTEXT_UNAVAILABLE: ' + stage);
  if (gl.isContextLost()) throw new Error('WEBGL_CONTEXT_LOST: ' + stage);
  const error = gl.getError();
  if (error !== gl.NO_ERROR)
    throw new Error('WEBGL_ERROR: ' + stage + ' (0x' + error.toString(16) + ')');
  return gl;
}

export function readGLPixels(gl, width, height) {
  assertGLContext(gl, 'before readPixels');
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0)
    throw new Error('WEBGL_READBACK_SIZE_INVALID');
  const pixels = new Uint8Array(width * height * 4);
  gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
  assertGLContext(gl, 'after readPixels');
  return pixels;
}

export class Vector3 {
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  copy(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this; }
  clone() { return new Vector3(this.x, this.y, this.z); }
  add(v) { this.x += v.x; this.y += v.y; this.z += v.z; return this; }
  sub(v) { this.x -= v.x; this.y -= v.y; this.z -= v.z; return this; }
  subVectors(a, b) { this.x = a.x - b.x; this.y = a.y - b.y; this.z = a.z - b.z; return this; }
  addVectors(a, b) { this.x = a.x + b.x; this.y = a.y + b.y; this.z = a.z + b.z; return this; }
  multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
  addScaledVector(v, s) { this.x += v.x * s; this.y += v.y * s; this.z += v.z * s; return this; }
  length() { return Math.hypot(this.x, this.y, this.z); }
  normalize() { const l = this.length() || 1; return this.multiplyScalar(1 / l); }
  distanceTo(v) { return Math.hypot(this.x - v.x, this.y - v.y, this.z - v.z); }
  dot(v) { return this.x * v.x + this.y * v.y + this.z * v.z; }
  crossVectors(a, b) { const x = a.y * b.z - a.z * b.y, y = a.z * b.x - a.x * b.z,
    z = a.x * b.y - a.y * b.x; return this.set(x, y, z); }
  cross(v) { return this.crossVectors(this.clone(), v); }
  setFromSphericalCoords() { return this; }
  setScalar(s) { return this.set(s, s, s); }
  applyQuaternion() { return this; } applyMatrix4() { return this; }
  lerp() { return this; } project() { return this; } unproject() { return this; }
  setFromMatrixPosition() { return this; }
  toArray() { return [this.x, this.y, this.z]; }
}
export class Vector2 { constructor(x = 0, y = 0) { this.x = x; this.y = y; }
  set(x, y) { this.x = x; this.y = y; return this; } copy() { return this; } }

/* لونٌ حقيقيّ: العرض يحتاج ثلاثة أعداد، لا سلسلة صامتة. */
function hexToRgb(h) {
  if (typeof h === 'number') return [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255];
  const s = String(h == null ? '#888888' : h).replace('#', '');
  const n = parseInt(s.length === 3 ? s.split('').map(c => c + c).join('') : s, 16);
  if (!isFinite(n)) return [0.53, 0.53, 0.53];
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}
export class Color {
  constructor(c) { const v = hexToRgb(c === undefined ? '#888888' : c);
    this.r = v[0]; this.g = v[1]; this.b = v[2]; }
  set(c) { const v = hexToRgb(c); this.r = v[0]; this.g = v[1]; this.b = v[2]; return this; }
  setHex(c) { return this.set(c); }
  copy(c) { this.r = c.r; this.g = c.g; this.b = c.b; return this; }
  clone() { const c = new Color(); return c.copy(this); }
  getHexString() { const f = v => Math.round(v * 255).toString(16).padStart(2, '0');
    return f(this.r) + f(this.g) + f(this.b); }
  convertSRGBToLinear() { return this; }
}

export class Object3D {
  constructor() { this.children = []; this.parent = null;
    this.position = new Vector3(); this.rotation = { x: 0, y: 0, z: 0 };
    this.scale = new Vector3(1, 1, 1); this.userData = {}; this.name = '';
    this.visible = true; this.castShadow = false; this.receiveShadow = false;
    this.matrixWorld = { elements: new Array(16).fill(0) };
    this.layers = { set() {}, enable() {} }; }
  add(o) { if (o) { o.parent = this; this.children.push(o); } return this; }
  remove(o) { const i = this.children.indexOf(o); if (i >= 0) this.children.splice(i, 1); return this; }
  traverse(fn) { if (fn) fn(this); for (const c of this.children) if (c && c.traverse) c.traverse(fn); }
  addEventListener() {} removeEventListener() {} dispatchEvent() {}
  getObjectByName() { return null; } lookAt() {} updateMatrixWorld() {}
  getWorldPosition(v) { return v || new Vector3(); }
  localToWorld(v) { return v; } worldToLocal(v) { return v; }
  rotateY() { return this; } translateZ() { return this; }
  clear() { this.children = []; return this; }
}
export class Group extends Object3D {}
export class Scene extends Object3D {
  constructor() { super(); this.environment = null; this.background = null; this.fog = null; } }

export class BoxGeometry {
  constructor(x = 1, y = 1, z = 1) { this.parameters = { width: x, height: y, depth: z };
    this.attributes = { uv: { count: 0, getX() { return 0; }, getY() { return 0; },
      setXY() {}, needsUpdate: false } }; }
  dispose() {}
}
export class PlaneGeometry extends BoxGeometry {}
export class CylinderGeometry extends BoxGeometry {}
export class SphereGeometry extends BoxGeometry {}
export class BufferGeometry extends BoxGeometry { setAttribute() { return this; }
  setFromPoints() { return this; } }

export class Material { constructor(p) { const o = p || {};
  this.color = new Color(o.color); this.map = null; this.userData = {};
  this.transparent = !!o.transparent; this.opacity = o.opacity === undefined ? 1 : o.opacity;
  this.needsUpdate = false; this.side = 0; }
  clone() { const m = new Material(); m.color = this.color.clone(); return m; }
  dispose() {} }
export class MeshStandardMaterial extends Material {}
export class MeshBasicMaterial extends Material {}
export class MeshPhysicalMaterial extends Material {}
export class MeshLambertMaterial extends Material {}
export class LineBasicMaterial extends Material {}
export class ShaderMaterial extends Material {}
export class SpriteMaterial extends Material {}

export class Mesh extends Object3D {
  constructor(g, m) { super(); this.geometry = g || new BoxGeometry();
    this.material = m || new MeshStandardMaterial(); this.isMesh = true; } }
export class Line extends Object3D {} export class Sprite extends Object3D {}
export class Points extends Object3D {}

export class PerspectiveCamera extends Object3D {
  constructor(f, a, n, fr) { super(); this.fov = f || 50; this.aspect = a || 1;
    this.near = n || 0.1; this.far = fr || 1000; this.isPerspectiveCamera = true;
    this.projectionMatrix = { elements: new Array(16).fill(0) };
    this.quaternion = { setFromEuler() {} }; }
  updateProjectionMatrix() {} getWorldDirection(v) { return v || new Vector3(); } }
export class OrthographicCamera extends PerspectiveCamera {}

export class Box3 {
  constructor() { this.min = new Vector3(Infinity, Infinity, Infinity);
    this.max = new Vector3(-Infinity, -Infinity, -Infinity); }
  makeEmpty() { return new Box3(); }
  setFromObject(o) { const b = this; b.min.set(Infinity, Infinity, Infinity);
    b.max.set(-Infinity, -Infinity, -Infinity);
    o.traverse(n => { if (!n.isMesh) return;
      const p = n.geometry && n.geometry.parameters; if (!p) return;
      const hx = p.width / 2, hy = p.height / 2, hz = p.depth / 2;
      b.min.x = Math.min(b.min.x, n.position.x - hx);
      b.min.y = Math.min(b.min.y, n.position.y - hy);
      b.min.z = Math.min(b.min.z, n.position.z - hz);
      b.max.x = Math.max(b.max.x, n.position.x + hx);
      b.max.y = Math.max(b.max.y, n.position.y + hy);
      b.max.z = Math.max(b.max.z, n.position.z + hz); });
    return b; }
  expandByObject(o) { return this.setFromObject(o); }
  getCenter(v) { const t = v || new Vector3();
    return t.set((this.min.x + this.max.x) / 2, (this.min.y + this.max.y) / 2,
                 (this.min.z + this.max.z) / 2); }
  getSize(v) { const t = v || new Vector3();
    return t.set(this.max.x - this.min.x, this.max.y - this.min.y,
                 this.max.z - this.min.z); }
  getBoundingSphere(s) { const t = s || new Sphere(); this.getCenter(t.center);
    const sz = this.getSize(new Vector3());
    t.radius = Math.hypot(sz.x, sz.y, sz.z) / 2; return t; }
  isEmpty() { return !(this.max.x >= this.min.x); }
  union() { return this; }
}
export class Sphere { constructor() { this.center = new Vector3(); this.radius = 0; } }
export class Frustum { setFromProjectionMatrix() { return this; }
  containsPoint() { return true; } intersectsObject() { return true; }
  intersectsSphere() { return true; } }
export class Raycaster { constructor() { this.ray = { origin: new Vector3(),
  direction: new Vector3() }; this.far = Infinity; this.near = 0; this.params = {}; }
  setFromCamera() {} intersectObjects() { return []; } intersectObject() { return []; } }
export class Clock { constructor() { this.elapsedTime = 0; }
  getDelta() { return 0; } getElapsedTime() { return 0; } }
export class Matrix4 { constructor() { this.elements = new Array(16).fill(0); }
  multiplyMatrices() { return this; } identity() { return this; }
  copy() { return this; } makeRotationY() { return this; } invert() { return this; } }
export class Euler { constructor() { this.x = 0; this.y = 0; this.z = 0; }
  set() { return this; } }
export class Quaternion { setFromEuler() { return this; } copy() { return this; }
  setFromAxisAngle() { return this; } multiply() { return this; } }
export class Spherical { setFromVector3() { return this; } }
export class Texture { constructor() { this.wrapS = 0; this.wrapT = 0;
  this.repeat = new Vector2(1, 1); this.needsUpdate = false; this.colorSpace = '';
  this.anisotropy = 1; } dispose() {} clone() { return new Texture(); } }
export class CanvasTexture extends Texture {}
export class DataTexture extends Texture {}
export class TextureLoader { load(u, cb) { if (cb) cb(new Texture()); return new Texture(); } }
export class PMREMGenerator { constructor() {} fromScene() { return { texture: null }; }
  compileEquirectangularShader() {} dispose() {} }
export class Light extends Object3D { constructor() { super();
  this.shadow = { camera: { left: 0, right: 0, top: 0, bottom: 0, near: 0, far: 0,
    updateProjectionMatrix() {} }, mapSize: new Vector2(1, 1), bias: 0 };
  this.target = new Object3D(); this.intensity = 1; } }
export class DirectionalLight extends Light {}
export class AmbientLight extends Light {}
export class HemisphereLight extends Light {}
export class PointLight extends Light {}
export class SpotLight extends Light {}
export class GridHelper extends Object3D {}
export class AxesHelper extends Object3D {}
export class Fog { constructor() {} }
export const MathUtils = {
  degToRad: d => d * Math.PI / 180, radToDeg: r => r * 180 / Math.PI,
  clamp: (v, a, b) => Math.max(a, Math.min(b, v)),
  lerp: (a, b, t) => a + (b - a) * t, randFloat: (a, b) => (a + b) / 2 };
export const SRGBColorSpace = 'srgb';
export const LinearSRGBColorSpace = 'srgb-linear';
export const RepeatWrapping = 1000;
export const DoubleSide = 2; export const FrontSide = 0; export const BackSide = 1;
export const PCFSoftShadowMap = 2; export const ACESFilmicToneMapping = 4;
export const EquirectangularReflectionMapping = 303;

/* ══════════════ المُنفِّذ: WebGL2 حقيقيّ ═══════════════════════════════════ */
const VS = `#version 300 es
in vec3 aPos; in vec3 aNrm;
uniform mat4 uMVP; uniform mat4 uModel;
out vec3 vNrm;
void main(){ vNrm = mat3(uModel) * aNrm; gl_Position = uMVP * vec4(aPos,1.0); }`;
const FS = `#version 300 es
precision highp float;
in vec3 vNrm; uniform vec3 uColor; out vec4 oColor;
void main(){
  vec3 n = normalize(vNrm);
  float d = 0.35 + 0.65 * max(0.0, dot(n, normalize(vec3(0.4,0.9,0.3))));
  oColor = vec4(uColor * d, 1.0);
}`;

function m4identity() { const m = new Float32Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; }
function m4mul(a, b) { const o = new Float32Array(16);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0;
    for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; o[i * 4 + j] = s; }
  return o; }
function m4perspective(fovY, asp, n, f) { const t = 1 / Math.tan(fovY / 2);
  const m = new Float32Array(16);
  m[0] = t / asp; m[5] = t; m[10] = (f + n) / (n - f); m[11] = -1;
  m[14] = 2 * f * n / (n - f); return m; }
function m4lookAt(eye, tgt, up) {
  const z = [eye[0] - tgt[0], eye[1] - tgt[1], eye[2] - tgt[2]];
  let l = Math.hypot(z[0], z[1], z[2]) || 1; z[0] /= l; z[1] /= l; z[2] /= l;
  const x = [up[1] * z[2] - up[2] * z[1], up[2] * z[0] - up[0] * z[2],
             up[0] * z[1] - up[1] * z[0]];
  l = Math.hypot(x[0], x[1], x[2]) || 1; x[0] /= l; x[1] /= l; x[2] /= l;
  const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2],
             z[0] * x[1] - z[1] * x[0]];
  const m = m4identity();
  m[0] = x[0]; m[4] = x[1]; m[8] = x[2];
  m[1] = y[0]; m[5] = y[1]; m[9] = y[2];
  m[2] = z[0]; m[6] = z[1]; m[10] = z[2];
  m[12] = -(x[0] * eye[0] + x[1] * eye[1] + x[2] * eye[2]);
  m[13] = -(y[0] * eye[0] + y[1] * eye[1] + y[2] * eye[2]);
  m[14] = -(z[0] * eye[0] + z[1] * eye[1] + z[2] * eye[2]);
  return m; }
function m4trs(p, s) { const m = m4identity();
  m[0] = s[0]; m[5] = s[1]; m[10] = s[2];
  m[12] = p[0]; m[13] = p[1]; m[14] = p[2]; return m; }

/* رؤوس مكعّب الوحدة مع نواظمها — ٣٦ رأساً، بلا فهرسة، أبسط ما يرسم صلباً. */
function unitCube() {
  const F = [
    [[0, 0, 1], [-.5, -.5, .5], [.5, -.5, .5], [.5, .5, .5], [-.5, .5, .5]],
    [[0, 0, -1], [.5, -.5, -.5], [-.5, -.5, -.5], [-.5, .5, -.5], [.5, .5, -.5]],
    [[0, 1, 0], [-.5, .5, .5], [.5, .5, .5], [.5, .5, -.5], [-.5, .5, -.5]],
    [[0, -1, 0], [-.5, -.5, -.5], [.5, -.5, -.5], [.5, -.5, .5], [-.5, -.5, .5]],
    [[1, 0, 0], [.5, -.5, .5], [.5, -.5, -.5], [.5, .5, -.5], [.5, .5, .5]],
    [[-1, 0, 0], [-.5, -.5, -.5], [-.5, -.5, .5], [-.5, .5, .5], [-.5, .5, -.5]]];
  const out = [];
  F.forEach(f => { const n = f[0], q = [f[1], f[2], f[3], f[4]];
    [[0, 1, 2], [0, 2, 3]].forEach(t => t.forEach(i =>
      out.push(q[i][0], q[i][1], q[i][2], n[0], n[1], n[2]))); });
  return new Float32Array(out);
}

export class WebGLRenderer {
  constructor(opts) {
    const o = opts || {};
    this.domElement = o.canvas || document.getElementById('c')
      || document.createElement('canvas');
    this.shadowMap = { enabled: false, type: 0 };
    this.xr = { enabled: false, addEventListener() {}, getSession() { return null; },
      setReferenceSpaceType() {}, getCamera() { return new PerspectiveCamera(); },
      isPresenting: false, getController() { return new Object3D(); },
      getControllerGrip() { return new Object3D(); } };
    this.info = { render: { calls: 0, triangles: 0 }, memory: { geometries: 0, textures: 0 },
      reset() { this.render.calls = 0; this.render.triangles = 0; } };
    this.capabilities = { getMaxAnisotropy: () => 1, isWebGL2: true };
    this.toneMapping = 0; this.toneMappingExposure = 1; this.outputColorSpace = 'srgb';
    this._gl = this.domElement.getContext('webgl2', { preserveDrawingBuffer: true,
      antialias: false, alpha: false });
    this._initGL();
  }
  _initGL() {
    const gl = assertGLContext(this._gl, 'initialize renderer');
    const mk = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
        throw new Error('shader: ' + gl.getShaderInfoLog(s));
      return s; };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, VS));
    gl.attachShader(p, mk(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS))
      throw new Error('link: ' + gl.getProgramInfoLog(p));
    this._prog = p;
    this._u = { mvp: gl.getUniformLocation(p, 'uMVP'),
      model: gl.getUniformLocation(p, 'uModel'),
      color: gl.getUniformLocation(p, 'uColor') };
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, unitCube(), gl.STATIC_DRAW);
    const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    const aPos = gl.getAttribLocation(p, 'aPos'), aNrm = gl.getAttribLocation(p, 'aNrm');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 24, 0);
    gl.enableVertexAttribArray(aNrm);
    gl.vertexAttribPointer(aNrm, 3, gl.FLOAT, false, 24, 12);
    this._vao = vao;
    gl.enable(gl.DEPTH_TEST);
    assertGLContext(gl, 'initialize resources');
  }
  getContext() { return this._gl; }
  setSize(w, h) { if (this.domElement) { this.domElement.width = w; this.domElement.height = h; } }
  setPixelRatio() {} setClearColor() {} setAnimationLoop() {} compile() {} dispose() {}
  getPixelRatio() { return 1; }
  render(scene, camera) {
    const gl = assertGLContext(this._gl, 'before render');
    const c = this.domElement;
    gl.viewport(0, 0, c.width, c.height);
    gl.clearColor(0.06, 0.07, 0.09, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this._prog); gl.bindVertexArray(this._vao);
    const eye = [camera.position.x, camera.position.y, camera.position.z];
    const tgt = (this.__target || [0, 0, 0]);
    const view = m4lookAt(eye, tgt, [0, 1, 0]);
    const proj = m4perspective(camera.fov * Math.PI / 180,
      (c.width / c.height) || 1, camera.near, camera.far);
    const vp = m4mul(proj, view);
    this.info.render.calls = 0; this.info.render.triangles = 0;
    const draw = n => {
      if (!n.isMesh || n.visible === false) return;
      const p = n.geometry && n.geometry.parameters; if (!p) return;
      if (![n.position.x, n.position.y, n.position.z, p.width, p.height, p.depth]
            .every(v => typeof v === 'number' && isFinite(v))) return;
      const model = m4trs([n.position.x, n.position.y, n.position.z],
                          [p.width, p.height, p.depth]);
      gl.uniformMatrix4fv(this._u.mvp, false, m4mul(vp, model));
      gl.uniformMatrix4fv(this._u.model, false, model);
      const col = (n.material && n.material.color) || new Color('#888888');
      gl.uniform3f(this._u.color, col.r, col.g, col.b);
      gl.drawArrays(gl.TRIANGLES, 0, 36);
      this.info.render.calls++; this.info.render.triangles += 12;
    };
    scene.traverse(draw);
    assertGLContext(gl, 'after render');
  }
}
export const REVISION = 'acs-gl-substitute';
