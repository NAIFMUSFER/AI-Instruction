/* ============================================================================
   tests/remediation/lib_csp_harness.js — بيئة قياس واحدة لسياسة الأمن.

   يخدم public/ على 127.0.0.1 برأس Content-Security-Policy **المقروء من
   netlify.toml نفسه** لا من نسخة مكتوبة يدوياً: لو ضعّف أحدٌ السياسة في ملفّ
   النشر، ضعفت هنا أيضاً وظهر ذلك في نتيجة القياس بدل أن يختبئ.

   كعب three.js: public/vendor فارغ في المستودع (تملؤه tools/netlify-build.sh
   وقت البناء) ولا شبكة هنا. وحدات ES كلٌّ أو لا شيء — فشل جلب وحدة واحدة يمنع
   تنفيذ الرسم كلّه — و core/viewer.js يستورد `three` وستّ إضافات. الكعب أدنى
   ما يجعل الرسم يُقيَّم، ولا يدّعي رسماً: بكسلات WebGL خارج نطاق أي قياس هنا.
   ما يُقاس هو DOM وCSSOM وخروق السياسة، وكلّها لا تمرّ عبر GPU.
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..', '..');
const PUB = path.join(ROOT, 'public');

function productionCSP() {
  const nt = fs.readFileSync(path.join(ROOT, 'netlify.toml'), 'utf8');
  const m = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(nt);
  if (!m) throw new Error('no Content-Security-Policy in netlify.toml');
  return m[1];
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
};

const THREE_STUB = `
export class Vector3{constructor(x=0,y=0,z=0){this.x=x;this.y=y;this.z=z;}
  set(x,y,z){this.x=x;this.y=y;this.z=z;return this;}
  copy(v){this.x=v.x;this.y=v.y;this.z=v.z;return this;}
  clone(){return new Vector3(this.x,this.y,this.z);}
  add(){return this;}sub(){return this;}addVectors(){return this;}
  subVectors(){return this;}multiplyScalar(){return this;}
  addScaledVector(){return this;}normalize(){return this;}
  applyQuaternion(){return this;}applyMatrix4(){return this;}
  crossVectors(){return this;}cross(){return this;}dot(){return 0;}
  length(){return 0;}distanceTo(){return 0;}lerp(){return this;}
  setFromSphericalCoords(){return this;}setScalar(){return this;}
  setFromMatrixPosition(){return this;}project(){return this;}
  unproject(){return this;}toArray(){return [this.x,this.y,this.z];}}
export class Vector2{constructor(x=0,y=0){this.x=x;this.y=y;}
  set(x,y){this.x=x;this.y=y;return this;}copy(){return this;}}
export class Color{constructor(c){this.c=c;}set(){return this;}
  setHex(){return this;}getHexString(){return '000000';}clone(){return this;}
  copy(){return this;}convertSRGBToLinear(){return this;}}
export class Object3D{constructor(){this.children=[];this.parent=null;
  this.position=new Vector3();this.rotation=new Vector3();
  this.scale=new Vector3(1,1,1);this.userData={};this.name='';
  this.visible=true;this.castShadow=false;this.receiveShadow=false;
  this.matrixWorld={elements:new Array(16).fill(0)};this.layers={set(){},enable(){}};}
  add(o){if(o){o.parent=this;this.children.push(o);}return this;}
  remove(o){const i=this.children.indexOf(o);if(i>=0)this.children.splice(i,1);return this;}
  traverse(fn){if(fn)fn(this);for(const c of this.children)if(c&&c.traverse)c.traverse(fn);}
  addEventListener(){}removeEventListener(){}dispatchEvent(){}
  getObjectByName(){return null;}lookAt(){}updateMatrixWorld(){}
  getWorldPosition(v){return v||new Vector3();}
  localToWorld(v){return v;}worldToLocal(v){return v;}
  rotateY(){return this;}translateZ(){return this;}clear(){this.children=[];return this;}}
export class Group extends Object3D{}
export class Scene extends Object3D{constructor(){super();this.environment=null;
  this.background=null;this.fog=null;}}
export class Mesh extends Object3D{constructor(g,m){super();this.geometry=g;
  this.material=m;this.isMesh=true;}}
export class PerspectiveCamera extends Object3D{constructor(f,a,n,fr){super();
  this.fov=f||50;this.aspect=a||1;this.near=n||0.1;this.far=fr||1000;
  this.isPerspectiveCamera=true;this.projectionMatrix={elements:new Array(16).fill(0)};}
  updateProjectionMatrix(){}getWorldDirection(v){return v||new Vector3();}}
export class OrthographicCamera extends PerspectiveCamera{}
export class Box3{constructor(){this.min=new Vector3();this.max=new Vector3();}
  setFromObject(){return this;}expandByObject(){return this;}
  getCenter(v){return v||new Vector3();}getSize(v){return v||new Vector3();}
  getBoundingSphere(s){return s||new Sphere();}isEmpty(){return false;}
  makeEmpty(){return this;}union(){return this;}}
export class Sphere{constructor(){this.center=new Vector3();this.radius=0;}}
export class Frustum{setFromProjectionMatrix(){return this;}
  containsPoint(){return true;}intersectsObject(){return true;}
  intersectsSphere(){return true;}}
export class Raycaster{constructor(){this.ray={origin:new Vector3(),
  direction:new Vector3()};this.far=Infinity;this.near=0;this.params={};}
  setFromCamera(){}intersectObjects(){return [];}intersectObject(){return [];}}
export class Clock{constructor(){this.elapsedTime=0;}getDelta(){return 0;}
  getElapsedTime(){return 0;}}
export class Matrix4{constructor(){this.elements=new Array(16).fill(0);}
  multiplyMatrices(){return this;}identity(){return this;}copy(){return this;}
  makeRotationY(){return this;}invert(){return this;}}
export class Euler{constructor(){this.x=0;this.y=0;this.z=0;}set(){return this;}}
export class Quaternion{setFromEuler(){return this;}copy(){return this;}
  setFromAxisAngle(){return this;}multiply(){return this;}}
export class Spherical{setFromVector3(){return this;}}
export class Texture{constructor(){this.wrapS=0;this.wrapT=0;this.repeat=new Vector2(1,1);
  this.needsUpdate=false;this.colorSpace='';this.anisotropy=1;}dispose(){}}
export class CanvasTexture extends Texture{}
export class DataTexture extends Texture{}
export class PMREMGenerator{constructor(){}fromScene(){return {texture:null};}
  compileEquirectangularShader(){}dispose(){}}
export class WebGLRenderer{constructor(){
  this.domElement=document.createElement('canvas');
  this.shadowMap={enabled:false,type:0};
  this.xr={enabled:false,addEventListener(){},getSession(){return null;},
    setReferenceSpaceType(){},getCamera(){return new PerspectiveCamera();},
    isPresenting:false,getController(){return new Object3D();},
    getControllerGrip(){return new Object3D();}};
  this.info={render:{calls:0,triangles:0},memory:{},reset(){}};
  this.capabilities={getMaxAnisotropy:()=>1,isWebGL2:true};
  this.toneMapping=0;this.toneMappingExposure=1;this.outputColorSpace='srgb';
  this.localClippingEnabled=false;this.clippingPlanes=[];}
  setSize(){}setPixelRatio(){}getPixelRatio(){return 1;}render(){}
  setAnimationLoop(){}dispose(){}setClearColor(){}clear(){}compile(){}
  getContext(){return null;}readRenderTargetPixels(){}setRenderTarget(){}
  getSize(v){return v||new Vector2(800,600);}}
export class WebGLRenderTarget{constructor(){this.texture=new Texture();}dispose(){}}
export class Plane{constructor(){this.normal=new Vector3();this.constant=0;}
  set(){return this;}setFromNormalAndCoplanarPoint(){return this;}}
const _NAMES=['BoxGeometry','PlaneGeometry','CylinderGeometry','SphereGeometry',
  'ConeGeometry','CircleGeometry','TorusGeometry','BufferGeometry','EdgesGeometry',
  'ShapeGeometry','ExtrudeGeometry','LatheGeometry','TubeGeometry','RingGeometry',
  'MeshStandardMaterial','MeshBasicMaterial','MeshPhysicalMaterial',
  'MeshLambertMaterial','MeshDepthMaterial','MeshNormalMaterial',
  'LineBasicMaterial','LineDashedMaterial','SpriteMaterial','ShaderMaterial',
  'PointsMaterial','AmbientLight','DirectionalLight','HemisphereLight',
  'PointLight','SpotLight','RectAreaLight','Line','LineSegments','LineLoop',
  'Sprite','Points','GridHelper','AxesHelper','BoxHelper','Fog','FogExp2',
  'Shape','Path','Float32BufferAttribute','Uint16BufferAttribute',
  'InstancedMesh','TextureLoader','CubeTextureLoader','LoadingManager',
  'ShapePath','Curve','CatmullRomCurve3','Line3','Triangle'];
function _stubClass(name){
  const C=function(){
    this.__stub=name;this.name='';this.visible=true;this.userData={};
    this.children=[];this.parent=null;
    this.position=new Vector3();this.rotation=new Vector3();
    this.scale=new Vector3(1,1,1);this.up=new Vector3(0,1,0);
    this.castShadow=false;this.receiveShadow=false;this.intensity=1;
    this.color=new Color();this.parameters={};
    var _attr=function(){return {setXY:function(){},setXYZ:function(){},
      getX:function(){return 0;},getY:function(){return 0;},
      getZ:function(){return 0;},count:0,array:[],needsUpdate:false};};
    this.attributes={uv:_attr(),position:_attr(),normal:_attr(),uv2:_attr()};
    this.boundingBox=null;this.boundingSphere=null;
    this.shadow={mapSize:{set:function(){},width:0,height:0},
      camera:{left:0,right:0,top:0,bottom:0,near:0,far:0,
        updateProjectionMatrix:function(){}},
      bias:0,normalBias:0,radius:0};
    this.target=new Object3D();this.material=null;this.geometry=null;
    this.map=null;this.transparent=false;this.opacity=1;this.side=0;
    this.emissive=new Color();this.emissiveIntensity=1;
    this.metalness=0;this.roughness=1;this.clippingPlanes=null;
    this.needsUpdate=false;this.depthWrite=true;this.depthTest=true;
    this.wireframe=false;this.vertexColors=false;this.toneMapped=true;
    this.dispose=()=>{};this.add=()=>this;this.remove=()=>this;
    this.traverse=(fn)=>{if(fn)fn(this);};
    this.setAttribute=()=>this;this.getAttribute=()=>null;
    this.setFromPoints=()=>this;this.setDrawRange=()=>this;
    this.setIndex=()=>this;this.computeVertexNormals=()=>{};
    this.computeBoundingBox=()=>{};this.computeBoundingSphere=()=>{};
    this.translate=()=>this;this.rotateX=()=>this;this.rotateY=()=>this;
    this.rotateZ=()=>this;this.scaleGeo=()=>this;this.applyMatrix4=()=>this;
    this.lookAt=()=>{};this.clone=()=>new C();this.copy=()=>this;
    this.load=(u,ok)=>{if(ok)ok(new Texture());return new Texture();};
    this.moveTo=()=>this;this.lineTo=()=>this;this.absarc=()=>this;
    this.getPoints=()=>[];this.holes=[];
    this.setColorAt=()=>{};this.setMatrixAt=()=>{};this.count=0;
    this.instanceMatrix={needsUpdate:false};
  };
  Object.defineProperty(C,'name',{value:name});
  return C;
}
const _ns={};
for(const n of _NAMES) _ns[n]=_stubClass(n);
export const BoxGeometry=_ns.BoxGeometry, PlaneGeometry=_ns.PlaneGeometry,
  CylinderGeometry=_ns.CylinderGeometry, SphereGeometry=_ns.SphereGeometry,
  ConeGeometry=_ns.ConeGeometry, CircleGeometry=_ns.CircleGeometry,
  TorusGeometry=_ns.TorusGeometry, BufferGeometry=_ns.BufferGeometry,
  EdgesGeometry=_ns.EdgesGeometry, ShapeGeometry=_ns.ShapeGeometry,
  ExtrudeGeometry=_ns.ExtrudeGeometry, LatheGeometry=_ns.LatheGeometry,
  TubeGeometry=_ns.TubeGeometry, RingGeometry=_ns.RingGeometry,
  MeshStandardMaterial=_ns.MeshStandardMaterial,
  MeshBasicMaterial=_ns.MeshBasicMaterial,
  MeshPhysicalMaterial=_ns.MeshPhysicalMaterial,
  MeshLambertMaterial=_ns.MeshLambertMaterial,
  MeshDepthMaterial=_ns.MeshDepthMaterial,
  MeshNormalMaterial=_ns.MeshNormalMaterial,
  LineBasicMaterial=_ns.LineBasicMaterial,
  LineDashedMaterial=_ns.LineDashedMaterial,
  SpriteMaterial=_ns.SpriteMaterial, ShaderMaterial=_ns.ShaderMaterial,
  PointsMaterial=_ns.PointsMaterial, AmbientLight=_ns.AmbientLight,
  DirectionalLight=_ns.DirectionalLight, HemisphereLight=_ns.HemisphereLight,
  PointLight=_ns.PointLight, SpotLight=_ns.SpotLight,
  RectAreaLight=_ns.RectAreaLight, Line=_ns.Line, LineSegments=_ns.LineSegments,
  LineLoop=_ns.LineLoop, Sprite=_ns.Sprite, Points=_ns.Points,
  GridHelper=_ns.GridHelper, AxesHelper=_ns.AxesHelper, BoxHelper=_ns.BoxHelper,
  Fog=_ns.Fog, FogExp2=_ns.FogExp2, Shape=_ns.Shape, Path=_ns.Path,
  Float32BufferAttribute=_ns.Float32BufferAttribute,
  Uint16BufferAttribute=_ns.Uint16BufferAttribute,
  InstancedMesh=_ns.InstancedMesh, TextureLoader=_ns.TextureLoader,
  CubeTextureLoader=_ns.CubeTextureLoader, LoadingManager=_ns.LoadingManager,
  ShapePath=_ns.ShapePath, Curve=_ns.Curve,
  CatmullRomCurve3=_ns.CatmullRomCurve3, Line3=_ns.Line3, Triangle=_ns.Triangle;
export const DoubleSide=2, FrontSide=0, BackSide=1,
  SRGBColorSpace='srgb', LinearSRGBColorSpace='srgb-linear',
  NoColorSpace='', ACESFilmicToneMapping=4, NoToneMapping=0,
  LinearToneMapping=1, ReinhardToneMapping=2, CineonToneMapping=3,
  PCFSoftShadowMap=2, PCFShadowMap=1, BasicShadowMap=0, VSMShadowMap=3,
  RepeatWrapping=1000, ClampToEdgeWrapping=1001, MirroredRepeatWrapping=1002,
  EquirectangularReflectionMapping=303, AdditiveBlending=2, NormalBlending=1,
  MultiplyBlending=4, NearestFilter=1003, LinearFilter=1006,
  LinearMipmapLinearFilter=1008, RGBAFormat=1023, UnsignedByteType=1009,
  FloatType=1015, HalfFloatType=1016;
export const MathUtils={degToRad:(d)=>d*Math.PI/180,
  radToDeg:(r)=>r*180/Math.PI,clamp:(v,a,b)=>Math.min(b,Math.max(a,v)),
  lerp:(a,b,t)=>a+(b-a)*t,randFloat:(a)=>a,generateUUID:()=>'stub-uuid',
  euclideanModulo:(n,m)=>((n%m)+m)%m};
export const REVISION='160';
`;

const ADDON_STUBS = {
  'controls/OrbitControls.js':
    'export class OrbitControls{constructor(){'
    + 'this.target={set(){},copy(){},clone(){return this;},x:0,y:0,z:0};'
    + 'this.enableDamping=false;this.dampingFactor=0.05;this.enabled=true;'
    + 'this.minDistance=0;this.maxDistance=Infinity;this.maxPolarAngle=Math.PI;'
    + 'this.enablePan=true;this.screenSpacePanning=false;}'
    + 'update(){}addEventListener(){}removeEventListener(){}dispose(){}'
    + 'saveState(){}reset(){}}',
  'webxr/VRButton.js':
    'export class VRButton{static createButton(){'
    + 'const b=document.createElement("button");b.textContent="VR";return b;}}',
  'webxr/ARButton.js':
    'export class ARButton{static createButton(){'
    + 'const b=document.createElement("button");b.textContent="AR";return b;}}',
  'exporters/GLTFExporter.js':
    'export class GLTFExporter{parse(s,ok){if(ok)ok({});}'
    + 'parseAsync(){return Promise.resolve({});}}',
  'objects/Sky.js':
    'const _u=()=>({turbidity:{value:0},rayleigh:{value:0},'
    + 'mieCoefficient:{value:0},mieDirectionalG:{value:0},'
    + 'sunPosition:{value:{copy(){},set(){}}},up:{value:{set(){},copy(){}}}});'
    + 'export class Sky{constructor(){this.material={uniforms:_u()};'
    + 'this.scale={setScalar(){}};this.name="";this.userData={};'
    + 'this.position={set(){}};}}',
  'environments/RoomEnvironment.js': 'export class RoomEnvironment{}',
  'postprocessing/EffectComposer.js':
    'export class EffectComposer{constructor(){this.passes=[];}'
    + 'addPass(p){this.passes.push(p);}removePass(){}setSize(){}render(){}'
    + 'dispose(){}}',
  'postprocessing/RenderPass.js':
    'export class RenderPass{constructor(){this.enabled=true;}dispose(){}}',
  'postprocessing/ShaderPass.js':
    'export class ShaderPass{constructor(){this.enabled=true;'
    + 'this.uniforms={resolution:{value:{set(){},x:0,y:0}}};}dispose(){}}',
  'postprocessing/OutputPass.js':
    'export class OutputPass{constructor(){this.enabled=true;}dispose(){}}',
  'postprocessing/SSAOPass.js':
    'export const SSAOPass=Object.assign(function(){this.enabled=true;'
    + 'this.kernelRadius=8;this.minDistance=0.001;this.maxDistance=0.1;'
    + 'this.output=0;this.dispose=()=>{};},{OUTPUT:{Default:0,SSAO:1}});',
  'shaders/FXAAShader.js':
    'export const FXAAShader={uniforms:{resolution:{value:{set(){},x:0,y:0}}},'
    + 'vertexShader:"",fragmentShader:""};',
  'shaders/CopyShader.js':
    'export const CopyShader={uniforms:{},vertexShader:"",fragmentShader:""};',
  'shaders/SSAOShader.js':
    'export const SSAOShader={uniforms:{},vertexShader:"",fragmentShader:""};'
    + 'export const SSAODepthShader={uniforms:{},vertexShader:"",fragmentShader:""};'
    + 'export const SSAOBlurShader={uniforms:{},vertexShader:"",fragmentShader:""};',
};

/* يبدأ خادماً محلياً يخدم public/ بالسياسة الإنتاجية، ويردّ كعب three
   على /vendor/three@*. يعيد {port, close()}. */
async function serve(options) {
  const opts = options || {};
  const csp = opts.csp === undefined ? productionCSP() : opts.csp;
  const overrides = opts.overrides || {};   // مسار → نصّ
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';

    if (Object.prototype.hasOwnProperty.call(overrides, p)) {
      const body = Buffer.from(overrides[p], 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length,
        ...(csp ? { 'Content-Security-Policy': csp } : {}) });
      return res.end(body);
    }

    if (p.indexOf('/vendor/three@') === 0) {
      const isBuild = p.indexOf('/build/') >= 0;
      const rel = p.split('/examples/jsm/')[1];
      const src = isBuild ? THREE_STUB
        : (Object.prototype.hasOwnProperty.call(ADDON_STUBS, rel)
          ? ADDON_STUBS[rel] : null);
      if (src === null || src === undefined) { res.writeHead(404); return res.end('nf'); }
      const body = Buffer.from(src, 'utf8');
      res.writeHead(200, { 'Content-Type': MIME['.js'],
        'Content-Length': body.length,
        ...(csp ? { 'Content-Security-Policy': csp } : {}) });
      return res.end(body);
    }

    const f = path.join(PUB, p);
    if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) {
      res.writeHead(404); return res.end('nf');
    }
    const body = fs.readFileSync(f);
    const headers = { 'Content-Type': MIME[path.extname(f)]
      || 'application/octet-stream', 'Content-Length': body.length };
    if (csp) headers['Content-Security-Policy'] = csp;
    res.writeHead(200, headers);
    res.end(body);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return { port: server.address().port, close: () => server.close() };
}

/* يسجّل كل خرق سياسة وكل رسالة كونسول من أوّل بايت — قبل أي سكربت للصفحة. */
const VIOLATION_RECORDER = () => {
  window.__cspViolations = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    window.__cspViolations.push({
      directive: e.violatedDirective,
      effective: e.effectiveDirective,
      blocked: e.blockedURI,
      sample: (e.sample || '').slice(0, 160),
      source: e.sourceFile || '',
      line: e.lineNumber || 0,
      column: e.columnNumber || 0,
      /* لسمة style لا يملأ المتصفّح sourceFile. العنصر نفسه هو الدليل:
         نسجّل هويّته وأوّل سمة style عليه فيُسمّى المصدر بدقّة. */
      target: (function () {
        var t = e.target;
        if (!t || t.nodeType !== 1) return null;
        return {
          tag: t.tagName ? t.tagName.toLowerCase() : '?',
          id: t.id || null,
          cls: String((t.className && t.className.baseVal !== undefined)
            ? t.className.baseVal : (t.className || '')).slice(0, 70),
          style: t.getAttribute ? String(t.getAttribute('style') || '').slice(0, 90) : '',
          parent: t.parentElement
            ? (t.parentElement.id || t.parentElement.tagName.toLowerCase()) : null,
        };
      })(),
    });
  });
};

function attachConsole(page, sink) {
  page.on('console', (m) => sink.push({ type: m.type(),
    text: m.text().slice(0, 400),
    location: m.location() ? (m.location().url || '') + ':'
      + (m.location().lineNumber || 0) : '' }));
  page.on('pageerror', (e) => sink.push({ type: 'pageerror',
    text: String(e.message).slice(0, 400),
    location: (e.stack || '').split('\n')[1] || '' }));
  page.on('requestfailed', (r) => sink.push({ type: 'requestfailed',
    text: r.url(), location: (r.failure() && r.failure().errorText) || '' }));
}

module.exports = { ROOT, PUB, productionCSP, serve, THREE_STUB, ADDON_STUBS,
  VIOLATION_RECORDER, attachConsole, MIME };
