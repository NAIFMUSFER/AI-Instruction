/* بصمة الهندسة المنبعثة فعلاً من compile() — لا بكسل، بل ما يُبنى في الشجرة */
const fs=require('fs');
const boxes=[];
globalThis.THREE={
  Group:function(){ this.children=[]; this.name=''; this.add=function(o){this.children.push(o);}; },
  BoxGeometry:function(x,y,z){ this.p=[x,y,z]; },
  Mesh:function(g,m){ this.g=g; this.m=m; this.name=''; this.castShadow=false;
    this.receiveShadow=false; this.rotation={y:0}; this.visible=true; this.userData={};
    this.position={x:0,y:0,z:0,set:(a,b,c)=>{this.position.x=a;this.position.y=b;this.position.z=c;}};
    boxes.push(this); }
};
globalThis.getMat=()=>({userData:{}});
globalThis.scaleBoxUV=()=>{};
globalThis.OBJ_UNKNOWN=[];

const path=require('path'), HERE=__dirname;
const FIXD=path.join(HERE,'fixtures');
const FX=JSON.parse(fs.readFileSync(path.join(FIXD,'base_fixtures.json'),'utf8'));
const MS=JSON.parse(fs.readFileSync(path.join(FIXD,'mep_fixtures.json'),'utf8'));
const rows=[];
const models={villa:FX.villa,hotel:FX.hotel,clinic:FX.clinic,warehouse:FX.warehouse,
  office:FX.office,villa_mep:MS.models.villa_mep,hotel_mep:MS.models.hotel_mep,
  clash_mep:MS.models.clash_mep};
Object.keys(models).sort().forEach(k=>{
  boxes.length=0;
  compile(JSON.parse(JSON.stringify(models[k])));
  const items=boxes.map(b=>[b.name,b.visible,
    [b.position.x,b.position.y,b.position.z],b.g?b.g.p:null,b.rotation.y]);
  items.sort((a,b)=>String(a[0])<String(b[0])?-1:String(a[0])>String(b[0])?1:0);
  rows.push({model:k,meshes:items.length,tree:items});
});
/* المرحلة 5 — إصلاح معلن لثغرة كتابة فوق المصدر:
   تحت المشغّل الموحّد tests/lib/run.js يكون process.argv[2] هو مسار ملفّ
   الاختبار نفسه، فكان المخرَج يُكتب فوق هذا الملفّ ويمحوه. المنطق كما هو،
   والوجهة وحدها صارت محميّة: لا يُكتب أبداً فوق ملفّ مصدر ‎.js‎. */
const _out=process.env.ACS_GEOM_OUT||process.argv[2]
  ||require('path').join(require('os').tmpdir(),'acs_geometry.json');
if(/\.js$/i.test(String(_out)))
  throw new Error('refusing to write the geometry dump over a JavaScript source file: '
    +_out+' — set ACS_GEOM_OUT to a .json path');
fs.writeFileSync(_out,JSON.stringify(rows));
console.log('geometry dumped:',rows.map(r=>r.model+'='+r.meshes).join(' '));
