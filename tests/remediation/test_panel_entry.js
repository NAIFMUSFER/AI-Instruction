/* ============================================================================
   F-27 — مداخل لوحات المراحل ٦…٩٫٢، في Chromium حقيقي.
     node tests/remediation/test_panel_entry.js

   العطل الذي يثبّته هذا الملفّ
   ---------------------------
   قبل F-27 كانت اللوحات الستّ (مساحة العمل، العرض، تبادل BIM، التوثيق، جودة
   العرض، التفصيل المعماري) مشحونة كاملةً — علاماتها في public/index.html
   ومنطقها في public/app/generated/‎ — وبلا أي مدخل. لا سطر في الشيفرة
   المشحونة يستدعي ‎init()‎ ولا ‎open()‎ لأيٍّ منها؛ الاستدعاء الوحيد في
   المستودع كلّه كان داخل tests/‎. النتيجة: ‎#acsWorkspace‎ لا يفارق
   ‎display:none‎ أبداً، وأزرار شريطه الإحدى عشرة بلا معالِج، واختصارات
   B/E/I/F و Ctrl+Z وحارس ‎beforeunload‎ للعمل غير المحفوظ — كلّها داخل
   ‎bind()‎ التي لا تُستدعى — غير مركّبة إطلاقاً.

   لماذا لم تكشفه الحزم القائمة: كلّها تستدعي ‎init()‎ بنفسها قبل الفحص، فتُثبت
   أن اللوحة تعمل **إن استُدعيت**، لا أن أحداً يستدعيها. الملفّ الوحيد الذي كان
   سيكشفه هو tests/production/verify_live_browser.js (يبحث عن ‎#wsBtnTree‎ في
   الصفحة الحيّة) ولم يُشغَّل قطّ: ‎NOT VERIFIED — EXTERNAL ENVIRONMENT
   REQUIRED‎.

   نطاق هذا التشغيل — مُعلَن بدقّة
   ------------------------------
   Three.js غير مُعبَّأ هنا (‎public/vendor‎ فارغ، لا شبكة)، ولا شيء في هذا
   الملفّ يدّعي خلاف ذلك. يُبنى رسمٌ بيانيٌّ للوحدات يطابق ترتيب
   ‎public/app/main.js‎ مع ثلاثة فروق مُعلَنة:

     · ‎render/scene.js‎ و‎generated/pbr-bridge.js‎ و
       ‎generated/arch-detail-bridge.js‎ و‎trust/wiring.js‎ مستبعَدة: هي
       الطبقات التي ترسم فعلاً، وبلا three حقيقيّ لا معنى لتقييمها. ولا تنشر
       أيّاً ممّا يقرؤه مدخل اللوحات.
     · ‎ui/workspace-ui-wiring.js‎ يُستبدَل بكعب يكشف ‎window.ACS.exportModel‎
       وحدها — وهي الشيء الوحيد الذي يقرؤه ‎ui/panels-entry.js‎ من تلك الوحدة.
     · المحدّد المجرّد `three` وإضافاته الستّ تُخدَم من كعبٍ أدنى، لأن وحدات
       ES كلٌّ أو لا شيء: فشل جلب وحدة واحدة يمنع تنفيذ الرسم كلّه، و
       ‎core/viewer.js‎ يستوردها (وإن كان لا يبني منها شيئاً عند التقييم).

   ما عدا ذلك بلا تعديل: القشرة نفسها، وسياسة الأمن الإنتاجية من netlify.toml
   كرأس استجابة حقيقيّ، وكل وحدات اللوحات كما هي مشحونة.

   ما يُقاس هنا: أن الصفحة المشحونة تحوي الأزرار، وأن الوحدة المشحونة توصلها،
   وأن النقر يفتح اللوحة فعلاً في DOM حقيقي. ما لا يُقاس هنا: بكسلات WebGL —
   وهي NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED كما في بقيّة الحزمة.
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');
const APP = path.join(PUB, 'app');
const { chromium } = require(path.join(ROOT, 'node_modules', 'playwright'));

let pass = 0, fail = 0;
const chk = (name, cond, detail) => {
  if (cond) { pass++; console.log('  ✓', name); }
  else { fail++; console.log('  ✗', name, detail === undefined ? '' : detail); }
};

/* ── ١ · فحص ساكن: المدخل موجود في الرسم البياني الفعليّ للإقلاع ──────────── */
console.log('\n== 1 · الفحص الساكن: المدخل داخل رسم الإقلاع ==');
const MAIN = fs.readFileSync(path.join(APP, 'main.js'), 'utf8');
const ORDER = [];
{
  const re = /^import\s+'\.\/(.+?)';$/gm;
  let m;
  while ((m = re.exec(MAIN))) ORDER.push(m[1]);
}
chk('public/app/main.js يستورد ui/panels-entry.js (استيراد ساكن، لا كسول)',
  ORDER.indexOf('ui/panels-entry.js') >= 0, ORDER.join(', '));
chk('المدخل يأتي بعد كل وحدة ينشر عليها اعتماده',
  ORDER.indexOf('ui/panels-entry.js')
    > Math.max(ORDER.indexOf('generated/workspace-ui.js'),
      ORDER.indexOf('generated/render-engine.js'),
      ORDER.indexOf('generated/bim.js'), ORDER.indexOf('generated/docs.js'),
      ORDER.indexOf('generated/pbr.js'), ORDER.indexOf('generated/arch-detail.js'),
      ORDER.indexOf('ui/workspace-ui-wiring.js')));

const ENTRY = fs.readFileSync(path.join(APP, 'ui', 'panels-entry.js'), 'utf8');
chk('المدخل لا يحوي eval ولا new Function (سياسة script-src)',
  !/\beval\s*\(/.test(ENTRY) && !/new\s+Function\s*\(/.test(ENTRY));
chk('المدخل يوصّل بـaddEventListener لا بـon* داخل العلامة',
  ENTRY.indexOf('addEventListener') >= 0);

const SHELL = fs.readFileSync(path.join(PUB, 'index.html'), 'utf8');
const BUTTONS = ['acsOpenWorkspace', 'acsOpenRender', 'acsOpenBim',
  'acsOpenDocs', 'acsOpenPbr', 'acsOpenDetail'];
for (const id of BUTTONS) {
  chk('القشرة تحوي الزرّ #' + id, SHELL.indexOf('id="' + id + '"') >= 0);
}
chk('كل زرّ مدخل يحمل اسماً متاحاً لقارئ الشاشة',
  BUTTONS.every((id) => {
    const at = SHELL.indexOf('id="' + id + '"');
    return at >= 0 && /aria-label="/.test(SHELL.slice(at, at + 320));
  }));
chk('لا معالِج داخل العلامة في القشرة (CSP تمنعه)',
  !/\son(click|change|input|submit|load|error)\s*=/.test(SHELL));

/* ── ٢ · ضابط سالب: بلا هذا المدخل لا شيء آخر يفتح أي لوحة ───────────────── */
console.log('\n== 2 · الضابط السالب: لا مدخل ثانٍ في الشيفرة المشحونة ==');
function walk(dir, acc) {
  for (const f of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walk(p, acc);
    else if (p.endsWith('.js')) acc.push(p);
  }
  return acc;
}
const SHIPPED = walk(APP, []).filter((p) => !p.endsWith('panels-entry.js'));
const CALLERS = SHIPPED.filter((p) => {
  const src = fs.readFileSync(p, 'utf8');
  return /\bWS\.init\s*\(|workspace\.init\s*\(|\.panel\.open\s*\(/.test(src);
});
chk('لا وحدة مشحونة أخرى تستدعي WS.init أو panel.open — المدخل واحد لا اثنان',
  CALLERS.length === 0, CALLERS.map((p) => path.relative(ROOT, p)).join(', '));

/* ── ٣ · القياس الحيّ في Chromium ────────────────────────────────────────── */
/* الطبقات التي ترسم فعلاً مستبعَدة: بلا three حقيقي لا معنى لتقييمها، ولا
   تنشر شيئاً يقرؤه مدخل اللوحات. ui/workspace-ui-wiring.js يُستبدَل بكعب
   يكشف window.ACS.exportModel والأسماء الأربعة التي يستوردها trust/wiring.js
   وحدها — وهي حدود ما يحتاجه المدخل من تلك الوحدة. */
const THREE_DEPENDENT = new Set(['render/scene.js', 'generated/pbr-bridge.js',
  'generated/arch-detail-bridge.js', 'trust/wiring.js']);
const GRAPH = ORDER.filter((f) => !THREE_DEPENDENT.has(f));

/* كعب three.js — أدنى ما يجعل رسم الوحدات **يُقيَّم**.
   وحدات ES كلٌّ أو لا شيء: فشل جلب وحدة واحدة يمنع تنفيذ الرسم كلّه، و
   core/viewer.js يستورد `three` وستّ إضافات. لكنّه لا يبني أي كائن three عند
   التقييم (جداول بيانات فقط)، فالكعب أدناه كافٍ ولا يزيّف شيئاً: لا رسم هنا
   ولا ادّعاء رسم. الطبقات التي ترسم فعلاً مستبعَدة من الرسم أصلاً. */
const THREE_STUB = `
export class Vector3{constructor(x=0,y=0,z=0){this.x=x;this.y=y;this.z=z;}
  set(x,y,z){this.x=x;this.y=y;this.z=z;return this;}clone(){return new Vector3(this.x,this.y,this.z);}}
export class Vector2{constructor(x=0,y=0){this.x=x;this.y=y;}}
export class Color{constructor(c){this.c=c;}}
export class Object3D{constructor(){this.children=[];this.position=new Vector3();
  this.rotation=new Vector3();this.scale=new Vector3(1,1,1);this.userData={};}
  add(){return this;}remove(){return this;}traverse(){}}
export class Group extends Object3D{}
export class Scene extends Object3D{}
export class Mesh extends Object3D{constructor(g,m){super();this.geometry=g;this.material=m;this.isMesh=true;}}
export class PerspectiveCamera extends Object3D{constructor(){super();this.near=0.1;this.far=1000;}
  updateProjectionMatrix(){}}
export class Box3{setFromObject(){return this;}getCenter(v){return v||new Vector3();}
  getSize(v){return v||new Vector3();}}
export class Sphere{constructor(){this.center=new Vector3();this.radius=0;}}
export class Raycaster{constructor(){this.ray={origin:new Vector3(),direction:new Vector3()};}
  setFromCamera(){}intersectObjects(){return [];}}
export class Clock{getDelta(){return 0;}getElapsedTime(){return 0;}}
export class Matrix4{}
export class Euler{}
export class Quaternion{}
export class Texture{}
export class CanvasTexture extends Texture{}
export class DataTexture extends Texture{}
export class PMREMGenerator{constructor(){}fromScene(){return {texture:null};}dispose(){}}
export class WebGLRenderer{constructor(){this.domElement=document.createElement('canvas');
  this.shadowMap={};this.xr={enabled:false,addEventListener(){},
    getSession(){return null;},setReferenceSpaceType(){}};
  this.info={render:{},memory:{}};this.capabilities={getMaxAnisotropy:()=>1};
  this.toneMappingExposure=1;this.outputColorSpace='srgb';}
  setSize(){}setPixelRatio(){}render(){}setAnimationLoop(){}dispose(){}
  getPixelRatio(){return 1;}getContext(){return null;}
  setClearColor(){}clear(){}compile(){}}
const _cls=['BoxGeometry','PlaneGeometry','CylinderGeometry','SphereGeometry',
  'ConeGeometry','CircleGeometry','TorusGeometry','BufferGeometry','EdgesGeometry',
  'ShapeGeometry','ExtrudeGeometry','LatheGeometry','TubeGeometry',
  'MeshStandardMaterial','MeshBasicMaterial','MeshPhysicalMaterial',
  'MeshLambertMaterial','LineBasicMaterial','SpriteMaterial','ShaderMaterial',
  'AmbientLight','DirectionalLight','HemisphereLight','PointLight','SpotLight',
  'Line','LineSegments','LineLoop','Sprite','GridHelper','AxesHelper','Fog',
  'Shape','Path','Float32BufferAttribute','InstancedMesh','TextureLoader'];
const _mk=(n)=>{const C=function(){this.__stub=n;this.dispose=()=>{};
  this.position=new Vector3();this.rotation=new Vector3();this.scale=new Vector3(1,1,1);
  this.userData={};this.children=[];this.add=()=>this;this.traverse=()=>{};
  this.name='';this.visible=true;this.castShadow=false;this.receiveShadow=false;
  this.shadow={mapSize:{set(){}},camera:{},bias:0,normalBias:0};
  this.target=new Object3D();this.intensity=1;this.color=new Color();
  this.setAttribute=()=>this;this.computeVertexNormals=()=>{};
  this.translate=()=>this;this.rotateX=()=>this;this.rotateY=()=>this;
  this.attributes={};this.parameters={};this.lookAt=()=>{};};
  Object.defineProperty(C,'name',{value:n});return C;};
const _ns={};
for(const n of _cls) _ns[n]=_mk(n);
export const {${['BoxGeometry', 'PlaneGeometry', 'CylinderGeometry',
    'SphereGeometry', 'ConeGeometry', 'CircleGeometry', 'TorusGeometry',
    'BufferGeometry', 'EdgesGeometry', 'ShapeGeometry', 'ExtrudeGeometry',
    'LatheGeometry', 'TubeGeometry', 'MeshStandardMaterial', 'MeshBasicMaterial',
    'MeshPhysicalMaterial', 'MeshLambertMaterial', 'LineBasicMaterial',
    'SpriteMaterial', 'ShaderMaterial', 'AmbientLight', 'DirectionalLight',
    'HemisphereLight', 'PointLight', 'SpotLight', 'Line', 'LineSegments',
    'LineLoop', 'Sprite', 'GridHelper', 'AxesHelper', 'Fog', 'Shape', 'Path',
    'Float32BufferAttribute', 'InstancedMesh', 'TextureLoader'].join(',')}} = _ns;
export const DoubleSide=2, FrontSide=0, BackSide=1, sRGBEncoding=3001,
  SRGBColorSpace='srgb', LinearSRGBColorSpace='srgb-linear',
  ACESFilmicToneMapping=4, PCFSoftShadowMap=2, RepeatWrapping=1000,
  EquirectangularReflectionMapping=303, NoToneMapping=0, LinearToneMapping=1,
  AdditiveBlending=2, NormalBlending=1;
export const MathUtils={degToRad:(d)=>d*Math.PI/180,radToDeg:(r)=>r*180/Math.PI,
  clamp:(v,a,b)=>Math.min(b,Math.max(a,v)),lerp:(a,b,t)=>a+(b-a)*t};
export const REVISION='160';
`;
const ADDON_STUBS = {
  'controls/OrbitControls.js':
    'export class OrbitControls{constructor(){this.target={set(){},copy(){}};'
    + 'this.enableDamping=false;}update(){}addEventListener(){}dispose(){}}',
  'webxr/VRButton.js':
    'export class VRButton{static createButton(){return document.createElement("button");}}',
  'webxr/ARButton.js':
    'export class ARButton{static createButton(){return document.createElement("button");}}',
  'exporters/GLTFExporter.js':
    'export class GLTFExporter{parse(s,ok){ok&&ok({});}}',
  'objects/Sky.js':
    'const _u=()=>({turbidity:{value:0},rayleigh:{value:0},'
    + 'mieCoefficient:{value:0},mieDirectionalG:{value:0},'
    + 'sunPosition:{value:{copy(){},set(){}}},up:{value:{set(){}}}});'
    + 'export class Sky{constructor(){this.material={uniforms:_u()};'
    + 'this.scale={setScalar(){}};this.name="";this.userData={};}}',
  'environments/RoomEnvironment.js':
    'export class RoomEnvironment{}',
};

const MIME = { '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' };

function productionCSP() {
  try {
    const nt = fs.readFileSync(path.join(ROOT, 'netlify.toml'), 'utf8');
    const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
    return m ? m[1] : '';
  } catch (e) { return ''; }
}

/* كعب ui/workspace-ui-wiring.js: الشيء الوحيد الذي يقرؤه المدخل من تلك الوحدة
   هو window.ACS.exportModel. نموذج المبنى أدناه أصغر ما يقبله auCreateProject. */
const WIRING_STUB = `
window.ACS = window.ACS || {};
window.__ACS_TEST_MODEL = null;
window.ACS.exportModel = () => window.__ACS_TEST_MODEL;
window.ACS.ready = true;
`;

const PAGE_SUFFIX = GRAPH.map((f) => `import '/app/${f}';`).join('\n');

async function live() {
  const csp = productionCSP();
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    if (p === '/__graph.js') {
      const body = Buffer.from(PAGE_SUFFIX, 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length });
      return res.end(body);
    }
    if (p === '/app/ui/workspace-ui-wiring.js') {
      const body = Buffer.from(WIRING_STUB, 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length });
      return res.end(body);
    }
    if (p === '/app/main.js') {
      const body = Buffer.from(PAGE_SUFFIX, 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length });
      return res.end(body);
    }
    if (p.indexOf('/vendor/three@') === 0) {
      const rel = p.split('/build/')[1] ? 'BUILD'
        : p.split('/examples/jsm/')[1] || null;
      const src = (rel === 'BUILD') ? THREE_STUB
        : (ADDON_STUBS[rel] !== undefined ? ADDON_STUBS[rel] : null);
      if (src === null) { res.writeHead(404); return res.end('nf'); }
      const body = Buffer.from(src, 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length });
      return res.end(body);
    }
    const f = path.join(PUB, p);
    if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) {
      res.writeHead(404); return res.end('nf');
    }
    const body = fs.readFileSync(f);
    const headers = { 'Content-Type':
      MIME[path.extname(f)] || 'application/octet-stream',
    'Content-Length': body.length };
    if (csp) headers['Content-Security-Policy'] = csp;
    res.writeHead(200, headers);
    res.end(body);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message + '\n'
    + (e.stack || '').split('\n').slice(0, 4).join('\n')));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 160));
  });

  await page.addInitScript(() => {
    window.__cspViolations = [];
    document.addEventListener('securitypolicyviolation', (e) => {
      window.__cspViolations.push({ directive: e.violatedDirective,
        blocked: e.blockedURI, sample: (e.sample || '').slice(0, 100) });
    });
  });
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'load' });
  await page.waitForTimeout(1200);

  const result = await page.evaluate(() => {
    const ids = ['acsOpenWorkspace', 'acsOpenRender', 'acsOpenBim',
      'acsOpenDocs', 'acsOpenPbr', 'acsOpenDetail'];
    const panels = ['acsWorkspace', 'rvPanel', 'bxPanel', 'dcPanel',
      'pqPanel', 'adPanel'];
    const openState = () => {
      const o = {};
      for (const id of panels) {
        const el = document.getElementById(id);
        o[id] = el ? el.classList.contains('on') : null;
      }
      return o;
    };
    const R = { loaded: !!(window.ACS && window.ACS.openWorkspace) };
    R.before = openState();

    // (أ) بلا نموذج: رفضٌ مُفسَّر لا لوحة فارغة ولا استثناء
    let threw = false;
    try { document.getElementById('acsOpenWorkspace').click(); }
    catch (e) { threw = true; R.noModelThrow = String(e.message || e); }
    R.noModelThrew = threw;
    R.noModelMessage = (document.getElementById('acsPanelsState') || {}).textContent || '';
    R.afterNoModel = openState();

    // (ب) نموذج حاضر: كل زرّ يفتح لوحته
    window.__ACS_TEST_MODEL = {
      site: { w: 30, d: 24 },
      levels: [{ index: 0, template: 'typical' }],
      floors: { typical: { rooms: [
        { id: 'hall', name: 'صالة', rect: [0, 0, 12, 9] },
        { id: 'room1', name: 'غرفة', rect: [12, 0, 6, 5] }] } },
      meta: { requirements: [], excluded: [] },
    };
    R.clickErrors = {};
    for (const id of ids) {
      try { document.getElementById(id).click(); }
      catch (e) { R.clickErrors[id] = String(e.message || e); }
    }
    R.after = openState();
    R.stateMessage = (document.getElementById('acsPanelsState') || {}).textContent || '';

    // (ج) init ركّبت أزرار الشريط فعلاً
    R.wsToolbarWired = ['wsBtnTree', 'wsBtnInsp', 'wsBtnMode', 'wsBtnUndo',
      'wsBtnRedo', 'wsBtnHistory', 'wsBtnIssues', 'wsBtnAI', 'wsBtnExport',
      'wsBtnLang'].filter((id) => {
      const el = document.getElementById(id);
      return !!(el && typeof el.onclick === 'function');
    });

    // (د) Escape يغلق اللوحات
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    R.afterEscape = openState();
    return R;
  });

  const violations = await page.evaluate(() => window.__cspViolations || []);
  await browser.close();
  server.close();
  return { result, errors, violations };
}

(async () => {
  console.log('\n== 3 · القياس الحيّ في Chromium ==');
  let live_;
  try {
    live_ = await live();
  } catch (e) {
    console.log('  ! تعذّر تشغيل Chromium: ' + (e && e.message));
    console.log('PANEL ENTRY: %d passed, %d failed  '
      + '(الطبقة الحيّة: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED)',
    pass, fail);
    process.exit(fail ? 1 : 0);
  }
  const R = live_.result;
  chk('المدخل قُيّم فعلاً في المتصفّح (window.ACS.openWorkspace موجودة)',
    R.loaded === true);
  chk('لا لوحة مفتوحة قبل أي نقرة (الفحص غير عبثي)',
    Object.keys(R.before).every((k) => R.before[k] === false),
    JSON.stringify(R.before));

  chk('النقر بلا نموذج لا يرفع استثناءً', R.noModelThrew === false,
    R.noModelThrow);
  chk('النقر بلا نموذج يشرح ما ينقص بدل فتح لوحة فارغة',
    /نموذج/.test(R.noModelMessage), JSON.stringify(R.noModelMessage));
  chk('ولا يفتح أي لوحة',
    Object.keys(R.afterNoModel).every((k) => R.afterNoModel[k] === false),
    JSON.stringify(R.afterNoModel));

  chk('لا استثناء من أي زرّ بعد وجود النموذج',
    Object.keys(R.clickErrors).length === 0, JSON.stringify(R.clickErrors));

  const OPENED = { acsWorkspace: 'مساحة العمل', rvPanel: 'العرض',
    bxPanel: 'تبادل BIM', dcPanel: 'التوثيق', pqPanel: 'جودة العرض',
    adPanel: 'التفصيل المعماري' };
  for (const id of Object.keys(OPENED)) {
    chk('النقر يفتح ' + OPENED[id] + ' فعلاً (#' + id + '.on)',
      R.after[id] === true, JSON.stringify(R.after));
  }
  chk('init ركّبت معالِجات أزرار شريط مساحة العمل العشرة',
    R.wsToolbarWired.length === 10, R.wsToolbarWired.join(','));
  chk('Escape يغلق اللوحات المولَّدة الخمس',
    ['rvPanel', 'bxPanel', 'dcPanel', 'pqPanel', 'adPanel']
      .every((k) => R.afterEscape[k] === false),
    JSON.stringify(R.afterEscape));
  /* KI-13 — قياسٌ لا ادّعاء: فتح اللوحات يكشف أن `style-src 'self'` يُسقط
     سمات style التي تحقنها الطبقات المولَّدة عبر innerHTML. هذا عطلٌ قائم
     سابقٌ على F-27 (لم يكن يظهر لأن اللوحات لم تكن تُفتح أصلاً)، وهو مسجَّل
     في KNOWN-ISSUES.md. ما يُثبَّت هنا: لا خرق من أي توجيه آخر — لا script-src
     ولا connect-src ولا غيرهما — أي أن المدخل الجديد نفسه نظيف. */
  const styleAttr = live_.violations.filter(
    (v) => String(v.directive).indexOf('style-src') === 0);
  const other = live_.violations.filter(
    (v) => String(v.directive).indexOf('style-src') !== 0);
  chk('لا خرق لأي توجيه غير style-src-attr (المدخل الجديد لا يخرق شيئاً)',
    other.length === 0, JSON.stringify(other.slice(0, 3)));
  console.log('  · KI-13 (قائم، مقيس هنا): %d خرقاً لـstyle-src-attr من سمات '
    + 'style تحقنها الطبقات المولَّدة عبر innerHTML.', styleAttr.length);
  const real = live_.errors.filter((t) => !/favicon|404/i.test(t)
    && !/Refused to apply inline style/i.test(t));
  chk('لا خطأ صفحة غير متوقَّع', real.length === 0,
    JSON.stringify(real.slice(0, 3)));

  console.log('\n──────────────────────────────────────────────');
  console.log('نطاق مُعلَن: طبقات three.js الثلاث مستبعَدة من الرسم هنا '
    + '(public/vendor فارغ، لا شبكة). بكسلات WebGL: '
    + 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.');
  console.log('PANEL ENTRY: %d passed, %d failed', pass, fail);
  if (fail) process.exit(1);
})();
