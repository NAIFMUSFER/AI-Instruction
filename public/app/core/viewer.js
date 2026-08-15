/* ============================================================
   public/app/core/viewer.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { __ACS_SHARED } from '../shared-state.js';
import { __ACS_LATE } from '../late-bindings.js';

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { ARButton } from 'three/addons/webxr/ARButton.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

/* ========================= المواد (palette) ========================= */
const MAT = {
  wall:{c:0xd0ccc4,m:0.0,r:0.9}, floor:{c:0x9a9a9e,m:0.0,r:0.85}, ceiling:{c:0xe6e6ea,m:0,r:0.9},
  door:{c:0x734620,m:0.0,r:0.55}, door_glass:{c:0x8cb8d8,m:0,r:0.1,o:0.35},
  window:{c:0x8cb8e0,m:0.0,r:0.08,o:0.30},
  outlet:{c:0xe01a1a,m:0.2,r:0.5}, switch:{c:0x1ab83d,m:0.2,r:0.5}, network:{c:0x1a5af2,m:0.2,r:0.5},
  tv:{c:0x0d0d0f,m:0.3,r:0.35}, usb:{c:0x9a4de6,m:0.2,r:0.5}, ev:{c:0xf2bf1a,m:0.3,r:0.4},
  light:{c:0xffdb59,m:0,r:0.4,e:0.6}, camera:{c:0x080808,m:0.4,r:0.3},
  ac:{c:0x40d2eb,m:0.1,r:0.4}, safety:{c:0xff7300,m:0.1,r:0.5},
  furn:{c:0x8c8072,m:0,r:0.7}, furn_soft:{c:0x5a6b8c,m:0,r:0.85}, counter:{c:0x34383f,m:0.1,r:0.35},
  /* ---- صناعي / لوجستي ---- */
  steel:{c:0x2f6fd0,m:0.55,r:0.42},        // قوائم الرفوف (أزرق صناعي)
  beam:{c:0xf59e0b,m:0.5,r:0.45},          // عوارض الرفوف (برتقالي)
  deck:{c:0x8f9298,m:0.3,r:0.6},           // ألواح الأرفف
  goods:{c:0xb08a52,m:0,r:0.85},           // كراتين/بضاعة
  pallet:{c:0x9c7b4d,m:0,r:0.9},
  belt:{c:0x2a2d33,m:0.2,r:0.55},          // سير ناقل
  frame:{c:0x9aa0a8,m:0.6,r:0.35},         // هياكل معدنية
  guard:{c:0xfacc15,m:0.3,r:0.5},          // حواجز أمان صفراء
  paint_lane:{c:0xf59e0b,m:0,r:0.95},      // دهان ممر رافعات
  paint_ped:{c:0xfacc15,m:0,r:0.95},       // ممر مشاة
  paint_amr:{c:0x8b5cf6,m:0,r:0.95},       // مسار روبوت
  paint_zone:{c:0x2563eb,m:0,r:0.95},      // ترقيم مناطق
  paint_fire:{c:0xef4444,m:0,r:0.95},      // سلامة
  dockdoor:{c:0x51565e,m:0.5,r:0.45},      // باب رصيف منزلق
  bumper:{c:0x1b1d21,m:0.1,r:0.85},
  screen:{c:0x0b3d2e,m:0.2,r:0.3,e:0.25},  // شاشات محطات
  robot:{c:0x111318,m:0.5,r:0.35},
  /* ---- عناصر عامة (بشر · مركبات · نباتات · خرسانة) ---- */
  skin:{c:0xc8a07a,m:0,r:0.75}, leaf:{c:0x3f7d3a,m:0,r:0.85},
  paint_car:{c:0x2f4f7a,m:0.55,r:0.28}, concrete_m:{c:0x9a9a97,m:0,r:0.9}
};
/* ترميز لوني صناعي حسب وظيفة المنطقة */
const ROLE_COLOR={
  receiving:'#14b8a6', inbound:'#14b8a6', crossdock:'#0ea5e9', qc:'#f97316', inspection:'#f97316',
  storage:'#2563eb', bulk:'#1d4ed8', bin:'#3b82f6', shelf:'#3b82f6',
  picking:'#22c55e', batch:'#22c55e', wave:'#16a34a', zone_pick:'#4ade80',
  packing:'#f59e0b', labeling:'#fbbf24', consolidation:'#eab308',
  sorting:'#a855f7', conveyor:'#7c3aed', robot:'#8b5cf6',
  outbound:'#8b5cf6', shipping:'#8b5cf6', dispatch:'#a78bfa',
  safety:'#ef4444', fire:'#ef4444', office:'#94a3b8', admin:'#94a3b8',
  it:'#64748b', maintenance:'#78716c', staff:'#a8a29e', circulation:'#facc15', aisle:'#facc15'
};
const POINT_KINDS = {
  outlet:['ELEC','outlet',0.40,[0.09,0.09,0.03]], switch:['ELEC','switch',1.20,[0.09,0.12,0.03]],
  network:['ELEC','network',0.40,[0.08,0.08,0.03]], usb:['ELEC','usb',0.55,[0.06,0.06,0.03]],
  tv:['ELEC','tv',1.40,[0.9,0.55,0.05]], ev:['ELEC','ev',0.90,[0.15,0.25,0.10]],
  light:['LIGHT','light',null,[0.30,0.30,0.06]], spot:['LIGHT','light',null,[0.12,0.12,0.05]],
  camera:['CAMERA','camera',null,[0.12,0.12,0.12]], ac:['HVAC','ac',null,[0.8,0.2,0.2]],
  vent:['HVAC','ac',null,[0.3,0.3,0.06]], smoke:['SAFETY','safety',null,[0.14,0.14,0.05]],
  sprinkler:['SAFETY','safety',null,[0.1,0.1,0.08]], exit:['SAFETY','safety',2.10,[0.30,0.14,0.05]],
  /* ---- معدات صناعية/لوجستية ---- */
  scanner:['ELEC','frame',1.10,[0.14,0.22,0.10]],       // ماسح باركود
  printer:['ELEC','frame',0.95,[0.32,0.20,0.30]],       // طابعة ملصقات
  scale:['ELEC','frame',0.15,[0.60,0.10,0.60]],         // ميزان
  monitor:['ELEC','screen',1.45,[0.55,0.35,0.05]],      // شاشة تحقّق
  ptl:['LIGHT','light',1.35,[0.10,0.06,0.04]],          // pick-to-light
  charger:['ELEC','ev',0.35,[0.50,0.45,0.40]],          // شاحن روبوت
  robot:['FURN','robot',0.15,[0.75,0.28,0.55]],         // AMR
  forklift:['FURN','guard',0.55,[1.15,1.10,2.10]],
  palletjack:['FURN','frame',0.10,[0.60,0.20,1.50]],
  cage:['FURN','frame',0.55,[1.20,1.10,0.85]],          // قفص طرود
  pallet:['FURN','pallet',0.07,[1.20,0.14,1.00]],
  diverter:['FURN','frame',0.95,[0.80,0.20,0.80]],      // محوّل فرز
  chute:['FURN','frame',0.60,[0.70,1.20,0.70]],         // منزلق فرز
  bin:['FURN','goods',0.30,[0.60,0.60,0.80]],           // صندوق رفض/فرز
  extinguisher:['SAFETY','safety',1.00,[0.16,0.50,0.16]],
  hydrant:['SAFETY','safety',0.60,[0.24,0.80,0.24]],
  eyewash:['SAFETY','safety',1.10,[0.30,0.35,0.30]],
  assembly:['SAFETY','safety',0.02,[2.50,0.03,2.50]],   // نقطة تجمّع
  gate:['SAFETY','frame',1.10,[0.15,2.20,1.20]],        // بوابة أمنية
  estop:['SAFETY','safety',1.05,[0.16,0.16,0.08]],
  server:['ELEC','frame',1.00,[0.60,2.00,0.90]],        // رف سيرفرات
  locker:['FURN','frame',0.95,[0.90,1.90,0.50]],
  sign:['SAFETY','paint_zone',2.60,[1.40,0.45,0.06]]    // لوحة تعريف منطقة
};
const LAYER_NAMES={WALL:'جدران',FLOOR:'أرضيات',DOOR:'أبواب',WINDOW:'نوافذ',ELEC:'كهرباء',
  LIGHT:'إنارة',CAMERA:'كاميرات',HVAC:'تكييف',SAFETY:'سلامة',FURN:'أثاث',OBJ:'عناصر ومجسّمات',
  STRUCT:'إنشائي (عرض هندسي — لا تصميم)',
  MEP_ELECTRICAL:'كهرباء (تمثيل — لا تصميم)', MEP_LIGHTING:'إنارة MEP (تمثيل)',
  MEP_ICT:'تيار خفيف/بيانات (تمثيل)', MEP_PLUMBING:'سباكة (تمثيل)',
  MEP_DRAINAGE:'صرف (تمثيل)', MEP_HVAC:'تكييف (تمثيل)',
  MEP_FIRE:'أنظمة حريق — بيانات فقط (لا محرّك سلامة)', MEP_OTHER:'MEP أخرى',
  MEP_RISER:'مناور MEP (تمثيل)',
  FLS_DETECTION:'كشف حريق (بيانات — لا تغطية)', FLS_ALARM:'إنذار (بيانات — لا تصميم)',
  FLS_SUPPRESSION:'إطفاء (بيانات — لا هيدروليك)', FLS_FIRE_WATER:'مياه حريق (بيانات)',
  FLS_EMERGENCY_LIGHTING:'إنارة طوارئ (بيانات — لا لوكس)',
  FLS_SIGNAGE:'لافتات مخارج (بيانات — لا كفاية)',
  FLS_BARRIER:'حواجز حريق (مصرَّحة فقط)', FLS_FIRE_DOOR:'أبواب حريق (مصرَّحة فقط)',
  FLS_ZONE:'مناطق حريق (مصرَّحة فقط)', FLS_OTHER:'حريق/سلامة أخرى'};
const LAYER_ORDER=['WALL','FLOOR','DOOR','WINDOW','ELEC','LIGHT','CAMERA','HVAC','SAFETY','FURN','OBJ','STRUCT',
  'MEP_ELECTRICAL','MEP_LIGHTING','MEP_ICT','MEP_PLUMBING','MEP_DRAINAGE','MEP_HVAC','MEP_FIRE',
  'MEP_RISER','MEP_OTHER',
  'FLS_DETECTION','FLS_ALARM','FLS_SUPPRESSION','FLS_FIRE_WATER','FLS_EMERGENCY_LIGHTING',
  'FLS_SIGNAGE','FLS_BARRIER','FLS_FIRE_DOOR','FLS_ZONE','FLS_OTHER'];
/* ألوان تمييز نوع العنصر فقط — لا لون هنا يعني آمن أو مخالف أو مطابق */
const FLS_LAYER_COLOR={FLS_DETECTION:'#f472b6',FLS_ALARM:'#fb923c',
  FLS_SUPPRESSION:'#60a5fa',FLS_FIRE_WATER:'#0ea5e9',FLS_EMERGENCY_LIGHTING:'#fbbf24',
  FLS_SIGNAGE:'#34d399',FLS_BARRIER:'#c084fc',FLS_FIRE_DOOR:'#a78bfa',
  FLS_ZONE:'#94a3b8',FLS_OTHER:'#9ca3af'};
/* ألوان تمييز التخصّص فقط — لا ترمز إلى سلامة ولا كفاية ولا مطابقة */
const MEP_DISC_COLOR={ELECTRICAL:'#eab308',LIGHTING:'#fde047',ICT:'#38bdf8',
  PLUMBING:'#2563eb',DRAINAGE:'#78716c',HVAC:'#14b8a6',FIRE:'#dc2626',
  OTHER:'#94a3b8',RISER:'#a855f7'};
/* ألوان تمييز نوع العنصر الإنشائي فقط — لا ترمز إلى سلامة ولا حالة ولا مطابقة */
const STRUCT_KIND_COLOR={COLUMN:'#b45309',BEAM:'#0f766e',STRUCTURAL_SLAB:'#475569',
  STRUCTURAL_WALL:'#7c3aed',STRUCTURAL_CORE:'#a16207',FOUNDATION:'#334155'};
const FLOOR_NAMES={F0:'الأرضي',F1:'الأول',F2:'الثاني',F3:'الثالث',F4:'الرابع',F5:'الخامس',F6:'السطح'};

/* ---------- مولّد خامات إجرائية واقعية (بلا إنترنت، بلا حقوق) ---------- */
const texCache={};
function noiseCanvas(size, fn){
  const c=document.createElement('canvas'); c.width=c.height=size;
  const x=c.getContext('2d'); fn(x,size,c); return c;
}
function rnd(seed){let s=seed;return()=>{s=(s*16807)%2147483647;return s/2147483647;};}
function grain(ctx,size,amount,base){
  const img=ctx.getImageData(0,0,size,size), d=img.data, r=rnd(7);
  for(let i=0;i<d.length;i+=4){ const n=(r()-0.5)*amount;
    d[i]=Math.max(0,Math.min(255,d[i]+n)); d[i+1]=Math.max(0,Math.min(255,d[i+1]+n));
    d[i+2]=Math.max(0,Math.min(255,d[i+2]+n)); }
  ctx.putImageData(img,0,0);
}
const TEX_GEN={
  plaster:(x,s)=>{x.fillStyle='#e9e6e0';x.fillRect(0,0,s,s);
    const r=rnd(3); for(let i=0;i<900;i++){x.fillStyle='rgba(0,0,0,'+(r()*0.03)+')';
      x.beginPath();x.arc(r()*s,r()*s,r()*6+1,0,7);x.fill();} grain(x,s,14);},
  concrete:(x,s)=>{x.fillStyle='#b9b7b2';x.fillRect(0,0,s,s);
    const r=rnd(11); for(let i=0;i<400;i++){x.fillStyle='rgba(0,0,0,'+(r()*0.07)+')';
      x.beginPath();x.arc(r()*s,r()*s,r()*22+3,0,7);x.fill();} grain(x,s,22);},
  tile:(x,s)=>{const n=4,t=s/n; x.fillStyle='#d8d5cf';x.fillRect(0,0,s,s);
    const r=rnd(5);
    for(let i=0;i<n;i++)for(let j=0;j<n;j++){
      const g=228+r()*18; x.fillStyle='rgb('+g+','+(g-3)+','+(g-8)+')';
      x.fillRect(i*t+2,j*t+2,t-4,t-4);
      for(let k=0;k<10;k++){x.strokeStyle='rgba(150,145,138,'+(r()*0.10)+')';x.lineWidth=1;
        x.beginPath();x.moveTo(i*t+r()*t,j*t+r()*t);x.lineTo(i*t+r()*t,j*t+r()*t);x.stroke();}}
    x.strokeStyle='#a9a49c'; x.lineWidth=3;
    for(let i=0;i<=n;i++){x.beginPath();x.moveTo(i*t,0);x.lineTo(i*t,s);x.stroke();
      x.beginPath();x.moveTo(0,i*t);x.lineTo(s,i*t);x.stroke();} grain(x,s,8);},
  wood:(x,s)=>{const g=x.createLinearGradient(0,0,0,s);
    g.addColorStop(0,'#7a4a22');g.addColorStop(1,'#5f381a');x.fillStyle=g;x.fillRect(0,0,s,s);
    const r=rnd(13);
    for(let i=0;i<70;i++){x.strokeStyle='rgba(40,22,8,'+(0.05+r()*0.22)+')';x.lineWidth=r()*3+0.6;
      const y=r()*s; x.beginPath(); x.moveTo(0,y);
      for(let px=0;px<=s;px+=16) x.lineTo(px, y+Math.sin(px/48+i)*4+ (r()-0.5)*2);
      x.stroke();} grain(x,s,12);},
  marble:(x,s)=>{x.fillStyle='#efece6';x.fillRect(0,0,s,s); const r=rnd(23);
    for(let i=0;i<26;i++){x.strokeStyle='rgba(120,120,130,'+(0.05+r()*0.16)+')';x.lineWidth=r()*3+0.5;
      let px=r()*s, py=0; x.beginPath(); x.moveTo(px,py);
      while(py<s){px+=(r()-0.5)*36; py+=14; x.lineTo(px,py);} x.stroke();} grain(x,s,7);},
  asphalt:(x,s)=>{x.fillStyle='#3a3a3d';x.fillRect(0,0,s,s); const r=rnd(31);
    for(let i=0;i<2600;i++){const g=30+r()*70; x.fillStyle='rgba('+g+','+g+','+(g+4)+',0.8)';
      x.fillRect(r()*s,r()*s,r()*3+1,r()*3+1);} grain(x,s,16);},
  metal:(x,s)=>{x.fillStyle='#9aa0a8';x.fillRect(0,0,s,s); const r=rnd(41);
    for(let i=0;i<700;i++){x.strokeStyle='rgba(255,255,255,'+(r()*0.08)+')';x.lineWidth=1;
      const y=r()*s; x.beginPath();x.moveTo(0,y);x.lineTo(s,y+(r()-0.5)*3);x.stroke();} grain(x,s,6);},
  fabric:(x,s)=>{x.fillStyle='#5b6a86';x.fillRect(0,0,s,s); const r=rnd(53);
    for(let i=0;i<s;i+=3){x.strokeStyle='rgba(0,0,0,0.06)';x.beginPath();x.moveTo(i,0);x.lineTo(i,s);x.stroke();
      x.strokeStyle='rgba(255,255,255,0.05)';x.beginPath();x.moveTo(0,i);x.lineTo(s,i);x.stroke();}
    grain(x,s,14);},
};
function getTex(kind){
  if(texCache[kind]) return texCache[kind];
  const gen=TEX_GEN[kind]; if(!gen) return null;
  const t=new THREE.CanvasTexture(noiseCanvas(512,gen));
  t.wrapS=t.wrapT=THREE.RepeatWrapping; t.colorSpace=THREE.SRGBColorSpace;
  t.anisotropy=8; texCache[kind]=t; return t;
}
// خامة + مقياس بالمتر لكل نوع مادة
const TEXMAP={ wall:['plaster',2.2], ceiling:['plaster',2.5], floor:['tile',1.6],
  door:['wood',1.2], counter:['marble',1.4], furn:['wood',1.4], furn_soft:['fabric',1.0],
  ac:['metal',0.8], camera:['metal',0.4], tv:['metal',1.0] };

__ACS_SHARED.USE_TEX=true;
const matCache={};
/* getMat(name, tint) — tint لون سداسي اختياري ('#22c55e') لصبغ الخامة نفسها.
   كل لون يحصل على مادة مستقلة في الذاكرة، فلا يتلوّن باقي المبنى معه. */
function getMat(name, tint){
  tint = normHex(tint);
  const key=name+(__ACS_SHARED.USE_TEX?'#t':'#p')+(tint?('@'+tint):'');
  if(matCache[key]) return matCache[key];
  const d=MAT[name]||{c:0x999999,m:0,r:0.7};
  const p={color:d.c,metalness:d.m||0,roughness:d.r==null?0.7:d.r};
  if(d.o!=null){p.transparent=true;p.opacity=d.o;}
  if(d.e){p.emissive=d.c;p.emissiveIntensity=d.e;}
  const m=new THREE.MeshStandardMaterial(p);
  if(__ACS_SHARED.USE_TEX&&TEXMAP[name]){
    const [kind,scale]=TEXMAP[name];
    const t=getTex(kind);
    if(t){ m.map=t; m.bumpMap=t; m.bumpScale=0.06; m.color.setHex(0xffffff);
      if(name==='wall'||name==='ceiling') m.color.setHex(d.c);   // صبغة خفيفة للجدران
      m.userData.texScale=scale; }
  }
  if(tint){ m.color.set(tint); if(d.e) m.emissive.set(tint); }
  m.userData.matName=name; m.userData.tint=tint||null;
  matCache[key]=m; return m;
}
function normHex(h){
  if(!h) return null;
  h=String(h).trim();
  if(/^[0-9a-fA-F]{6}$/.test(h)) h='#'+h;
  if(/^#[0-9a-fA-F]{3}$/.test(h)) h='#'+h[1]+h[1]+h[2]+h[2]+h[3]+h[3];
  return /^#[0-9a-fA-F]{6}$/.test(h)? h.toLowerCase() : null;
}
/* تحجيم UV حسب أبعاد الصندوق ليظهر مقياس الخامة صحيحاً على كل الأوجه */
function scaleBoxUV(geo,w,h,d,scale){
  const uv=geo.attributes.uv; const S=scale||2;
  const dims=[[d,h],[d,h],[w,d],[w,d],[w,h],[w,h]];   // +X,-X,+Y,-Y,+Z,-Z
  for(let f=0;f<6;f++){ const [su,sv]=dims[f];
    for(let k=0;k<4;k++){ const i=f*4+k;
      uv.setXY(i, uv.getX(i)*(su/S), uv.getY(i)*(sv/S)); } }
  uv.needsUpdate=true;
}

/* ========================= المترجم الهندسي (JS) ========================= */

/* KI-25/F-42 — سجلّ عيوب البناء: ما رُفض وما سقط، بالعدد والسبب.
   لم يكن في المترجم موضعٌ واحد يقول «الذي بنيتُه ليس الذي أُعطيت». كان
   العنصر التالف يُبنى صامتاً بإحداثيّة NaN، أو تُلقى الغرفة كلّها باستثناء
   يهدم المشهد. كلاهما يُحصى هنا الآن، وطبقةُ الربط تقرأ السجلّ قبل أن تعلن
   نجاحاً. لا محتوى مبنى فيه: أعداد ورموز أسباب وأسماء وسوم فقط. */
let BUILD_DEFECTS=null;
function acsBuildDefectsReset(){
  BUILD_DEFECTS={non_finite_box:0, rejected_room:0, rejected_field:0,
                 derived_level_index:0, unknown_object:0, reasons:{}, samples:[]};
  return BUILD_DEFECTS;
}
function acsBuildDefect(kind, reason, sample){
  if(!BUILD_DEFECTS) acsBuildDefectsReset();
  BUILD_DEFECTS[kind]=(BUILD_DEFECTS[kind]||0)+1;
  BUILD_DEFECTS.reasons[reason]=(BUILD_DEFECTS.reasons[reason]||0)+1;
  if(sample&&BUILD_DEFECTS.samples.length<12)
    BUILD_DEFECTS.samples.push(String(sample).slice(0,64));
}
function acsBuildDefects(){ return BUILD_DEFECTS||acsBuildDefectsReset(); }

function addBox(group, cx,cy,cz, ex,ey,ez, mat, name, shadow, tint, rotY){
  /* KI-25/F-42 — الحارس القديم ‎ex<=0‎ لا يوقف NaN ولا undefined: كلاهما
     يعطي false في المقارنة، فتُبنى شبكة بإحداثيّات غير معرَّفة. العتاد لا
     يرسمها، وعقدُ الحدود يستبعدها، وعدّاد الواجهة يعدّها — فيرى المستخدم
     «تم التوليد ✓ ٢٠٠١ عنصر» ونافذةً فارغة. هذا هو عطل KI-25 بالحرف.
     الآن: ما ليس عدداً منتهياً لا يدخل المشهد، ويُحصى بسببه. */
  if(!(isFinite(ex)&&isFinite(ey)&&isFinite(ez)
       &&isFinite(cx)&&isFinite(cy)&&isFinite(cz))){
    acsBuildDefect('non_finite_box','NON_FINITE_GEOMETRY',name);
    return;
  }
  if(ex<=0||ey<=0||ez<=0) return;
  const g=new THREE.BoxGeometry(ex,ey,ez);
  const m=getMat(mat,tint);
  if(m.map&&m.userData.texScale) scaleBoxUV(g,ex,ey,ez,m.userData.texScale);
  const mesh=new THREE.Mesh(g,m);
  mesh.position.set(cx,cy,cz); mesh.name=name;
  if(rotY) mesh.rotation.y=rotY;
  if(shadow){mesh.castShadow=true;mesh.receiveShadow=true;}
  group.add(mesh);
  return mesh;
}
function normEdge(e){ const c=String(e==null?'N':e).trim().toUpperCase()[0];
  return (c==='N'||c==='S'||c==='E'||c==='W')?c:'N'; }
function edgeGeom(edge, rect){const[x,z,w,d]=rect; edge=normEdge(edge);
  if(edge==='N')return['x',z,x,x+w]; if(edge==='S')return['x',z+d,x,x+w];
  if(edge==='W')return['z',x,z,z+d]; if(edge==='E')return['z',x+w,z,z+d];}
function openU(edge,rect,off){const[x,z]=rect; edge=normEdge(edge);
  return (edge==='N'||edge==='S')?x+off:z+off;}

function wallOpenings(group,axis,fixed,u0,u1,y0,H,t,openings,fkey,room,tag,tint,glass){
  const segs=openings.filter(o=>o[1]>0).sort((a,b)=>a[0]-b[0]);
  const solids=[]; let cur=u0;
  for(const[uc,w,bottom,top]of segs){
    const a=Math.max(u0,uc-w/2), b=Math.min(u1,uc+w/2);
    if(a>cur) solids.push([cur,a,y0,y0+H]);
    if(bottom>0) solids.push([a,b,y0,y0+bottom]);
    if(y0+top<y0+H) solids.push([a,b,y0+top,y0+H]);
    cur=Math.max(cur,b);
  }
  if(cur<u1) solids.push([cur,u1,y0,y0+H]);
  solids.forEach(([a,b,yb,yt],k)=>{
    const w=b-a,h=yt-yb; if(w<=0.002||h<=0.002)return;
    const cu=(a+b)/2,cy=(yb+yt)/2;
    const wm=glass?'window':'wall';
    if(axis==='x') addBox(group,cu,cy,fixed,w,h,t,wm,`WALL|${fkey}|${room}|${tag}s${k}`,!glass,tint);
    else addBox(group,fixed,cy,cu,t,h,w,wm,`WALL|${fkey}|${room}|${tag}s${k}`,!glass,tint);
  });
}
/* KI-25/F-42 — مستطيل صالح أو لا شيء. كان ‎const[x,z,w,d]=room.rect‎ يرمي
   ‎TypeError: rect is not iterable‎ على أوّل غرفة بلا rect، والاستثناء يصعد
   من compile إلى setModel — وقد **حُذف المشهد القديم قبله** — فتبقى النافذة
   فارغة وشريط الحالة على «يقرأ وصفك…» بلا خطأ ولا زرّ إعادة. غرفةٌ واحدة
   تالفة لا يجوز أن تهدم مبنى كاملاً: تُرفَض وتُحصى وتُعلَن. */
function acsRoomRect(room){
  const r=(room||{}).rect;
  if(!Array.isArray(r)||r.length<4) return null;
  const v=[Number(r[0]),Number(r[1]),Number(r[2]),Number(r[3])];
  if(!v.every(isFinite)) return null;
  if(!(v[2]>0&&v[3]>0)) return null;
  return v;
}
/* حقلٌ يُنتظَر مصفوفةً وقد يأتي عدداً أو كائناً من مولّد لغوي. كان
   ‎if(room.racks) (room.racks||[]).forEach‎ يمرّ الحارس ثم يرمي. */
function acsList(room,key){
  const v=(room||{})[key];
  if(v==null||v===false) return [];
  if(Array.isArray(v)) return v;
  acsBuildDefect('rejected_field','FIELD_NOT_A_LIST',
                 String((room||{}).id||'?')+'.'+key);
  return [];
}
function buildRoom(group,room,fkey,baseY,def){
  const rect=acsRoomRect(room);
  if(!rect){
    acsBuildDefect('rejected_room','ROOM_RECT_INVALID',(room||{}).id||'?');
    return;
  }
  const [x,z,w,d]=rect;
  const H=room.wall_h||def.wall_h, t=def.wall_t, name=room.id||'room';
  /* تشطيبات الغرفة: لون خاص بهذه الغرفة وحدها */
  const wcol=normHex(room.wall_color), fcol=normHex(room.floor_color), ccol=normHex(room.ceiling_color);
  const per={N:[],S:[],E:[],W:[]};
  acsList(room,'doors').forEach(dr=>{dr.edge=normEdge(dr.edge);
    per[dr.edge].push([openU(dr.edge,rect,dr.offset),dr.width||0.9,0,dr.height||2.1]);});
  acsList(room,'windows').forEach(wn=>{const s=wn.sill==null?0.9:wn.sill,h=wn.height||1.6;
    wn.edge=normEdge(wn.edge);
    per[wn.edge].push([openU(wn.edge,rect,wn.offset),wn.width||1.2,s,s+h]);});
  const dk=dockOpenings(room);
  for(const e of['N','S','E','W']) per[e]=per[e].concat(dk[e]);

  /* نمط الجدار: مناطق المستودع وحدها مفتوحة (دهان أرضي).
     الغرف السكنية/المكتبية تبقى بجدران كاملة حتى لو حملت role. */
  const wallsMode=room.walls||((def.industrial&&room.role&&!ADMIN_ROLES[room.role])?'none':'full');
  const WH={none:0, line:0, low:1.10, half:1.80, rail:1.10, glass:H, full:H};
  const hW=(WH[wallsMode]==null?H:WH[wallsMode]);
  if(wallsMode==='none'||wallsMode==='line'){
    /* حدّ المنطقة: شريط دهان أرضي بلون الوظيفة + لوحة اسم المنطقة */
    const zc=wcol||ROLE_COLOR[room.role]||'#2563eb';
    for(const e of['N','S','E','W']){
      const[axis,fixed,u0,u1]=edgeGeom(e,rect);
      if(axis==='x') addBox(group,(u0+u1)/2,baseY+0.006,fixed,u1-u0,0.012,0.15,'paint_zone',
            `FLOOR|${fkey}|${name}|zone${e}`,false,zc);
      else addBox(group,fixed,baseY+0.006,(u0+u1)/2,0.15,0.012,u1-u0,'paint_zone',
            `FLOOR|${fkey}|${name}|zone${e}`,false,zc);
    }
    addBox(group,x+w/2,baseY+0.01,z+d/2,Math.min(w*0.5,6),0.014,Math.min(d*0.22,2.2),'paint_zone',
      `FLOOR|${fkey}|${name}|label`,false,zc);
  }else{
    for(const e of['N','S','E','W']){const[axis,fixed,u0,u1]=edgeGeom(e,rect);
      wallOpenings(group,axis,fixed,u0,u1,baseY,hW,t,per[e],fkey,name,'w'+e,
        wcol||(room.role?ROLE_COLOR[room.role]:null), wallsMode==='glass');}
  }
  /* أرضية الغرفة: تُبنى فقط عند طلب لون/تشطيب خاص بها (فوق بلاطة الدور) */
  if(fcol) addBox(group,x+w/2,baseY+0.012,z+d/2,Math.max(w-t,0.1),0.024,Math.max(d-t,0.1),
                  'floor',`FLOOR|${fkey}|${name}|plate`,false,fcol);
  if(ccol) addBox(group,x+w/2,baseY+H-0.03,z+d/2,Math.max(w-t,0.1),0.05,Math.max(d-t,0.1),
                  'ceiling',`FLOOR|${fkey}|${name}|ceil`,false,ccol);
  acsList(room,'doors').forEach((dr,i)=>{const uc=openU(dr.edge,rect,dr.offset),wd=dr.width||0.9,dh=dr.height||2.1;
    const mat=dr.material==='glass'?'door_glass':'door';const[axis,fixed]=edgeGeom(dr.edge,rect);const cy=baseY+dh/2;
    const dcol=normHex(dr.color);
    if(axis==='x')addBox(group,uc,cy,fixed,wd,dh,0.06,mat,`DOOR|${fkey}|${name}|${i}`,true,dcol);
    else addBox(group,fixed,cy,uc,0.06,dh,wd,mat,`DOOR|${fkey}|${name}|${i}`,true,dcol);});
  acsList(room,'windows').forEach((wn,i)=>{const uc=openU(wn.edge,rect,wn.offset),wd=wn.width||1.2,s=wn.sill==null?0.9:wn.sill,h=wn.height||1.6;
    const[axis,fixed]=edgeGeom(wn.edge,rect);const cy=baseY+s+h/2;
    if(axis==='x')addBox(group,uc,cy,fixed,wd,h,0.05,'window',`WINDOW|${fkey}|${name}|${i}`,false);
    else addBox(group,fixed,cy,uc,0.05,h,wd,'window',`WINDOW|${fkey}|${name}|${i}`,false);});
  acsList(room,'points').forEach((pt,j)=>{const kind=pt.type||'outlet';const K=POINT_KINDS[kind]||POINT_KINDS.outlet;
    const[layer,mat,defH,size]=K;const px=x+(pt.x==null?w/2:pt.x),pz=z+(pt.z==null?d/2:pt.z);let py;
    if(defH==null){ if(kind==='camera')py=baseY+H-0.15; else if(kind==='ac')py=baseY+H-0.35; else py=baseY+H-size[1]/2-0.02; }
    else py=baseY+(pt.height==null?defH:pt.height);
    addBox(group,px,py,pz,size[0],size[1],size[2],mat,`${layer}|${fkey}|${name}|${kind}${j}`,false);});
  acsList(room,'furniture').forEach((fu,k)=>{const fx=x+fu.x,fz=z+fu.z,fw=fu.w||0.8,fd=fu.d||0.8,fh=fu.h||0.8;
    addBox(group,fx,baseY+fh/2,fz,fw,fh,fd,fu.mat||'furn',`FURN|${fkey}|${name}|${fu.name||'obj'}${k}`,true);});
  /* العناصر الصناعية المضغوطة */
  if(room.racks)    buildRacks(group,room,fkey,baseY,def);
  if(room.lanes)    buildLanes(group,room,fkey,baseY,def);
  if(room.stations) buildStations(group,room,fkey,baseY,def);
  if(room.docks)    buildDocks(group,room,fkey,baseY,def);
  if(room.objects)  buildObjects(group,room,fkey,baseY);
}
/* ==================================================================
   نظام العناصر العام — أي شيء يذكره العميل يُبنى، ولا يُسقَط أبداً.
   بشر · روبوتات · مركبات · أثاث · درج · مصعد · أعمدة · نباتات ·
   وأي كائن مجهول يُبنى بصندوق بأبعاده واسمه بدل أن يُهمَل.
   ================================================================== */
const OBJ_LIB = {
  /* kind: [w,d,h, builder] — الأبعاد افتراضية يغلبها ما يذكره العميل */
  person:   [0.50,0.35,1.72,'person'],  worker:[0.52,0.36,1.74,'person'],
  visitor:  [0.50,0.35,1.70,'person'],  engineer:[0.52,0.36,1.75,'person'],
  child:    [0.36,0.26,1.20,'person'],
  robot:    [0.75,0.55,0.35,'robot'],   amr:[0.80,0.60,0.32,'robot'],
  cobot:    [0.40,0.40,1.30,'robot'],
  forklift: [1.20,2.20,2.30,'forklift'],reachtruck:[1.10,2.40,2.60,'forklift'],
  car:      [1.85,4.55,1.45,'car'],     van:[2.00,5.40,2.20,'car'],
  truck:    [2.55,12.0,4.00,'truck'],   trailer:[2.55,13.6,4.10,'truck'],
  stairs:   [1.20,4.20,3.20,'stairs'],  elevator:[2.10,2.30,3.20,'elevator'],
  column:   [0.45,0.45,3.20,'column'],  railing:[3.00,0.06,1.10,'railing'],
  tree:     [2.40,2.40,4.50,'tree'],    palm:[2.60,2.60,6.00,'palm'],
  plant:    [0.60,0.60,1.20,'plant'],   planter:[1.60,0.60,0.55,'box'],
  sofa:     [2.20,0.90,0.80,'sofa'],    armchair:[0.90,0.85,0.80,'sofa'],
  bed:      [1.90,2.10,0.55,'bed'],     bed_single:[1.05,2.05,0.50,'bed'],
  table:    [1.60,0.90,0.75,'table'],   dining:[2.20,1.10,0.76,'table'],
  desk:     [1.50,0.75,0.75,'table'],   chair:[0.48,0.50,0.90,'chair'],
  wardrobe: [2.00,0.60,2.30,'box'],     cabinet:[1.20,0.55,0.90,'box'],
  fridge:   [0.75,0.70,1.85,'box'],     oven:[0.60,0.60,0.90,'box'],
  washer:   [0.60,0.60,0.85,'box'],     sink:[0.60,0.50,0.90,'box'],
  toilet:   [0.40,0.70,0.80,'box'],     bath:[1.70,0.75,0.55,'box'],
  counter:  [2.40,0.65,0.90,'box'],     tv:[1.30,0.08,0.75,'panel'],
  rug:      [2.40,1.60,0.02,'panel'],   curtain:[2.00,0.10,2.40,'panel'],
  shelf:    [1.00,0.40,2.00,'shelfobj'],pallet:[1.20,1.00,0.15,'pallet'],
  box:      [0.60,0.40,0.40,'box'],     crate:[1.10,1.10,1.00,'box'],
  sign:     [1.40,0.06,0.45,'panel'],   barrier:[1.50,0.30,1.05,'box']
};
const OBJ_AR = {  // مرادفات عربية → kind
  'شخص':'person','رجل':'person','امرأة':'person','عامل':'worker','موظف':'worker',
  'زائر':'visitor','مهندس':'engineer','طفل':'child','أشخاص':'person','بشر':'person',
  'روبوت':'robot','ربوت':'robot','آلي':'robot','رافعة':'forklift','رافعة شوكية':'forklift',
  'سيارة':'car','سيارات':'car','مركبة':'car','فان':'van','شاحنة':'truck','مقطورة':'trailer',
  'درج':'stairs','سلم':'stairs','مصعد':'elevator','عمود':'column','أعمدة':'column',
  'درابزين':'railing','حاجز':'barrier','شجرة':'tree','أشجار':'tree','نخلة':'palm',
  'نبات':'plant','نباتات':'plant','حوض نباتات':'planter','كنبة':'sofa','أريكة':'sofa',
  'كرسي':'chair','سرير':'bed','طاولة':'table','مكتب':'desk','طاولة طعام':'dining',
  'خزانة':'wardrobe','دولاب':'wardrobe','ثلاجة':'fridge','فرن':'oven','غسالة':'washer',
  'مغسلة':'sink','مرحاض':'toilet','بانيو':'bath','مغطس':'bath','شاشة':'tv','تلفزيون':'tv',
  'سجادة':'rug','ستارة':'curtain','رف':'shelf','رفوف':'shelf','بالتة':'pallet',
  'صندوق':'box','كرتون':'crate','لوحة':'sign','كاونتر':'counter'
};
const OBJ_MAT = {person:'skin', robot:'robot', car:'paint_car', truck:'paint_car',
  forklift:'guard', tree:'leaf', palm:'leaf', plant:'leaf', column:'concrete_m',
  stairs:'concrete_m', elevator:'frame', railing:'frame', shelfobj:'deck',
  pallet:'pallet', panel:'tv', sofa:'furn_soft', bed:'furn_soft', chair:'furn',
  table:'furn', box:'furn'};

let OBJ_UNKNOWN=[];
/* مطابقة بحدود الكلمة — «أعرفه» يجب ألّا تطابق «رف»، و«المبنى» ألّا تطابق «بني» */
const _AL='\u0621-\u064a';
function _wordIn(hay, key){
  const esc=key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  return new RegExp('(^|[^'+_AL+'\\w])(?:ال|بال|لل|وال|و|ب|ل)?'+esc+
                    '(?:ة|ه|ات|ين|ان|ي)?([^'+_AL+'\\w]|$)').test(' '+hay+' ');
}
const _AR_KEYS=Object.keys(OBJ_AR).sort((a,b)=>b.length-a.length);
const _EN_KEYS=Object.keys(OBJ_LIB).sort((a,b)=>b.length-a.length);
function objKind(o){
  const raw=String(o.kind||o.name||'').trim().toLowerCase();
  if(OBJ_LIB[raw]) return raw;
  for(const k of _AR_KEYS){ if(_wordIn(raw,k)) return OBJ_AR[k]; }
  for(const k of _EN_KEYS){ if(_wordIn(raw,k)) return k; }
  return null;                       // مجهول → صندوق بأبعاده واسمه (لا يُسقَط أبداً)
}
/* يبني كائناً واحداً في موضعه (إحداثيات عالمية) */
function buildObject(g, o, kind, cx, cz, baseY, fkey, room, idx){
  const def=OBJ_LIB[kind]||[0.6,0.6,0.9,'box'];
  const w=+o.w||def[0], d=+o.d||def[1], h=+o.h||def[2], shape=def[3];
  const rot=(+o.rot||0)*Math.PI/180;
  const col=normHex(o.color)||null;
  const tag=`OBJ|${fkey}|${room}|${(o.name||kind)}${idx}`;
  const B=(dx,dy,dz,ex,ey,ez,mat,c)=>{
    const s=Math.sin(rot), co=Math.cos(rot);
    addBox(g, cx+dx*co-dz*s, baseY+dy, cz+dx*s+dz*co, ex,ey,ez, mat, tag, true, c||col, rot);
  };
  const M=OBJ_MAT[shape]||'furn';
  if(shape==='person'){
    const sk=col||'#c8a07a';
    B(0,h*0.22,0, w*0.28,h*0.44,d*0.7,'skin',sk);            // ساقان ككتلة
    B(0,h*0.62,0, w,h*0.34,d,'fabric',col||'#3b5b8c');        // جذع
    B(0,h*0.90,0, w*0.42,h*0.15,d*0.62,'skin',sk);            // رأس
  }else if(shape==='robot'){
    B(0,h*0.5,0, w,h,d,'robot');
    B(0,h+0.16,0, w*0.5,0.30,d*0.5,'frame');
    B(0,h+0.34,0, 0.10,0.14,0.10,'safety','#22c55e');
  }else if(shape==='forklift'){
    B(0,0.55,-d*0.15, w,1.05,d*0.6,'guard');
    B(0,1.55,-d*0.15, w*0.8,0.9,d*0.45,'frame');
    B(0,h*0.5,d*0.42, w*0.75,h,0.12,'frame');
    B(0,0.12,d*0.5, w*0.7,0.10,0.9,'frame');
  }else if(shape==='car'||shape==='truck'){
    const body=col||(shape==='truck'?'#e8e8ea':'#2f4f7a');
    B(0,h*0.33,0, w,h*0.46,d,'paint_car',body);
    B(0,h*0.70,shape==='truck'?-d*0.34:0, w*0.9,h*0.36,shape==='truck'?d*0.24:d*0.55,'window');
    for(const sx of[-1,1]) for(const sz of[-1,1])
      B(sx*w*0.46,0.33,sz*d*0.34, 0.22,0.62,0.62,'bumper');
  }else if(shape==='stairs'){
    const n=Math.max(4,Math.round(h/0.17)), rise=h/n, run=d/n;
    for(let i=0;i<n;i++) B(0,rise*(i+0.5),-d/2+run*(i+0.5), w,rise,run,'concrete_m');
    for(const sx of[-1,1]) B(sx*(w/2+0.03),h*0.55,0, 0.06,0.06,d,'frame');
  }else if(shape==='elevator'){
    B(0,h*0.5,0, w,h,d,'frame');
    B(0,h*0.45,-d/2, w*0.62,h*0.85,0.06,'window');
  }else if(shape==='column'){
    B(0,h*0.5,0, w,h,d,'concrete_m');
  }else if(shape==='railing'){
    B(0,h,0, w,0.06,0.06,'frame');
    const n=Math.max(2,Math.round(w/1.1));
    for(let i=0;i<=n;i++) B(-w/2+w*i/n,h*0.5,0, 0.05,h,0.05,'frame');
  }else if(shape==='tree'||shape==='palm'){
    const th=shape==='palm'?h*0.72:h*0.42;
    B(0,th*0.5,0, w*0.16,th,d*0.16,'pallet','#6b4a2a');
    if(shape==='palm'){ for(let i=0;i<6;i++){ const a=i*Math.PI/3;
        B(Math.cos(a)*w*0.32,th+0.18,Math.sin(a)*d*0.32, w*0.7,0.10,d*0.2,'leaf'); } }
    else { B(0,th+(h-th)*0.45,0, w,(h-th)*0.9,d,'leaf'); }
  }else if(shape==='plant'){
    B(0,0.18,0, w*0.55,0.36,d*0.55,'furn','#8a5a3a');
    B(0,h*0.62,0, w,h*0.7,d,'leaf');
  }else if(shape==='sofa'){
    B(0,0.22,0, w,0.44,d,'fabric',col||'#5a6b8c');
    B(0,0.55,-d*0.36, w,0.62,d*0.28,'fabric',col||'#5a6b8c');
    for(const sx of[-1,1]) B(sx*(w/2-0.09),0.52,0, 0.18,0.5,d,'fabric',col||'#5a6b8c');
  }else if(shape==='bed'){
    B(0,0.18,0, w,0.36,d,'furn','#7a6a54');
    B(0,0.44,0, w*0.98,0.20,d*0.94,'fabric',col||'#e8e4dc');
    B(0,0.72,-d*0.44, w,0.85,0.10,'furn','#6a5a44');
  }else if(shape==='table'){
    B(0,h-0.04,0, w,0.08,d,'furn');
    for(const sx of[-1,1]) for(const sz of[-1,1])
      B(sx*(w/2-0.08),h*0.5,sz*(d/2-0.08), 0.07,h,0.07,'frame');
  }else if(shape==='chair'){
    B(0,0.44,0, w,0.07,d,'furn');
    B(0,0.68,-d*0.42, w,0.46,0.06,'furn');
    for(const sx of[-1,1]) for(const sz of[-1,1])
      B(sx*(w/2-0.05),0.22,sz*(d/2-0.05), 0.05,0.44,0.05,'frame');
  }else if(shape==='shelfobj'){
    for(let i=0;i<4;i++) B(0,0.15+i*(h-0.2)/4,0, w,0.05,d,'deck');
    for(const sx of[-1,1]) B(sx*(w/2-0.03),h*0.5,0, 0.05,h,d,'frame');
  }else if(shape==='pallet'){
    B(0,h*0.5,0, w,h,d,'pallet');
  }else if(shape==='panel'){
    B(0,(+o.height!=null?+o.height:(kind==='rug'?0.01:1.35)),0, w,h,Math.max(d,0.04),M,col);
  }else{
    B(0,h*0.5,0, w,h,d, o.mat||M, col);          // مجهول → صندوق بأبعاده
  }
}
/* يبني كل عناصر الغرفة، مع التكرار (count/pitch) */
function buildObjects(group, room, fkey, baseY){
  const [rx,rz,rw,rd]=room.rect, nm=room.id||'room';
  acsList(room,'objects').forEach((o,i)=>{
    const kind=objKind(o);
    const n=Math.max(1,Math.min(+o.count||1,200));
    const pitch=+o.pitch||1.2, dir=(o.dir==='z')?'z':'x';
    for(let k=0;k<n;k++){
      const ox=(+o.x||rw/2)+(dir==='x'?pitch*k:0);
      const oz=(+o.z||rd/2)+(dir==='z'?pitch*k:0);
      if(ox>rw+2||oz>rd+2) break;
      buildObject(group,o,kind||'box',rx+ox,rz+oz,baseY+(+o.y||0),fkey,nm,i*1000+k);
    }
    if(!kind){ OBJ_UNKNOWN.push(o.name||o.kind||'?');
      /* KI-25/F-42: كان هذا السجلّ يُكتَب ولا يُقرأ في أي ملفّ منشور —
         نوعٌ لم يعرفه المترجم يُبنى صندوقاً عامّاً ولا يعلم به أحد. */
      acsBuildDefect('unknown_object','OBJECT_KIND_UNKNOWN',o.name||o.kind); }
  });
}

/* ==================================================================
   عناصر صناعية/لوجستية مضغوطة — سطر JSON واحد يولّد مئات القطع.
   هذا ما يسمح بتنفيذ طلب ضخم كاملاً بلا انقطاع مخرج النموذج.
   ================================================================== */
/* مستوى التفصيل: يوازن بين واقعية المشهد وسلاسة الحركة على الجهاز */
__ACS_SHARED.DETAIL=1.0;
const DQ=(v,min,max)=>Math.max(min,Math.min(Math.round(v*__ACS_SHARED.DETAIL),max));
const RACK_DEF={
  pallet:{depth:1.10, bay:2.70, h:8.0, levels:4, aisle:3.40},
  shelf: {depth:0.60, bay:1.20, h:2.40, levels:5, aisle:1.40},
  bin:   {depth:0.45, bay:0.90, h:2.10, levels:6, aisle:1.10},
  mezz:  {depth:1.20, bay:3.00, h:5.00, levels:2, aisle:2.50},
  flow:  {depth:1.20, bay:1.50, h:2.20, levels:4, aisle:1.60},
  cage:  {depth:1.00, bay:1.20, h:1.80, levels:1, aisle:1.20}
};
/* رفوف: صفوف متكرّرة بممرّات بينها */
function buildRacks(group, room, fkey, baseY, def){
  const [rx,rz,rw,rd]=room.rect, nm=room.id||'room';
  acsList(room,'racks').forEach((R,ri)=>{
    const K=RACK_DEF[R.kind]||RACK_DEF.pallet;
    const depth=+R.depth||K.depth, bay=+R.bay||K.bay, H=+R.h||K.h;
    const lv=Math.max(1,Math.min(+R.levels||K.levels,10)), aisle=+R.aisle||K.aisle;
    const dir=(R.dir==='z')?'z':'x';                 // اتجاه امتداد صف الرفّ
    /* عقد المحاذاة: الامتداد المتاح = امتداد الغرفة ناقص الإزاحة. أخذ
       الامتداد كاملاً بعد إزاحة موجبة كان يُخرج الصفّ خارج الغرفة بمقدار
       الإزاحة بالضبط — وهو سبب ظهور الرفوف خارج غلاف المبنى. */
    const _rb=__ACS_LATE.pqRackBlock([rx,rz,rw,rd],R).block;
    const bx=_rb.x, bz=_rb.z;
    const bw=_rb.w, bd=_rb.d;
    const runLen = dir==='x'? bw : bd;               // طول الصف
    const across = dir==='x'? bd : bw;               // العمق المتاح للصفوف
    const pitch  = depth+aisle;
    let rows=+R.rows||Math.max(1,Math.floor((across+aisle)/pitch));
    rows=Math.max(1,Math.min(rows,40));
    const bays=Math.max(1,Math.min(Math.floor(runLen/bay),60));
    const segs=Math.min(bays,DQ(8,2,20));            // تقسيم البضاعة (حدّ للأداء)
    const posts=Math.min(bays+1,DQ(6,2,14));
    const tint=normHex(R.color);
    for(let r=0;r<rows;r++){
      const off=r*pitch+depth/2;
      if(off-depth/2>across-0.05) break;
      const cA = dir==='x' ? (bz+off) : (bx+off);    // مركز الصف عبر الاتجاه
      const c0 = dir==='x' ? bx : bz;                // بداية الصف
      // ألواح كل مستوى
      for(let L=0;L<lv;L++){
        const y=baseY+0.12+(H-0.2)*(L/(lv));
        if(dir==='x') addBox(group,c0+runLen/2,y,cA,runLen,0.07,depth,'deck',
              `FURN|${fkey}|${nm}|rack${ri}r${r}L${L}`,false,tint);
        else addBox(group,cA,y,c0+runLen/2,depth,0.07,runLen,'deck',
              `FURN|${fkey}|${nm}|rack${ri}r${r}L${L}`,false,tint);
        // بضاعة/بالتات على المستوى
        const segL=runLen/segs;
        for(let s=0;s<segs;s++){
          if((s+r+L)%4===3) continue;                // فراغات واقعية
          const cu=c0+segL*(s+0.5), gh=Math.min((H-0.2)/lv-0.25,1.15);
          if(gh<0.2) continue;
          if(dir==='x') addBox(group,cu,y+0.05+gh/2,cA,segL*0.86,gh,depth*0.86,'goods',
                `FURN|${fkey}|${nm}|goods${ri}r${r}L${L}s${s}`,false);
          else addBox(group,cA,y+0.05+gh/2,cu,depth*0.86,gh,segL*0.86,'goods',
                `FURN|${fkey}|${nm}|goods${ri}r${r}L${L}s${s}`,false);
        }
      }
      // قوائم رأسية
      for(let p=0;p<posts;p++){
        const cu=c0+runLen*(p/(posts-1||1));
        for(const sgn of [-1,1]){
          const ca=cA+sgn*(depth/2-0.05);
          if(dir==='x') addBox(group,cu,baseY+H/2,ca,0.10,H,0.10,'steel',
                `FURN|${fkey}|${nm}|post${ri}r${r}p${p}`,true);
          else addBox(group,ca,baseY+H/2,cu,0.10,H,0.10,'steel',
                `FURN|${fkey}|${nm}|post${ri}r${r}p${p}`,true);
        }
      }
      // عارضة سفلية برتقالية (تمييز صناعي)
      if(dir==='x') addBox(group,c0+runLen/2,baseY+0.32,cA,runLen,0.10,depth*1.02,'beam',
            `FURN|${fkey}|${nm}|beam${ri}r${r}`,false);
      else addBox(group,cA,baseY+0.32,c0+runLen/2,depth*1.02,0.10,runLen,'beam',
            `FURN|${fkey}|${nm}|beam${ri}r${r}`,false);
    }
  });
}
/* ممرّات ودهانات أرضية + أسهم اتجاه + سيور ناقلة */
const LANE_MAT={forklift:'paint_lane',pedestrian:'paint_ped',amr:'paint_amr',robot:'paint_amr',
  one_way:'paint_lane',zone:'paint_zone',fire:'paint_fire',safety:'paint_fire'};
function buildLanes(group, room, fkey, baseY, def){
  const [rx,rz]=room.rect, nm=room.id||'room';
  acsList(room,'lanes').forEach((L,li)=>{
    const kind=L.kind||'forklift';
    const x=rx+(+L.x||0), z=rz+(+L.z||0), w=+L.w||2.5, d=+L.d||2.5;
    const dir=(L.dir==='z')?'z':'x';
    const len=dir==='x'?w:d, wid=dir==='x'?d:w;
    if(kind==='conveyor'){ buildConveyor(group,x,z,w,d,dir,baseY,fkey,nm,li,L); return; }
    const tint=normHex(L.color);
    // بساط الدهان
    addBox(group,x+w/2,baseY+0.008,z+d/2,w,0.016,d,LANE_MAT[kind]||'paint_lane',
      `SAFETY|${fkey}|${nm}|lane${li}`,false,tint);
    // خطّان جانبيان (حدود الممر)
    if(kind==='pedestrian'||kind==='forklift'||kind==='one_way'){
      for(const sgn of [-1,1]){
        if(dir==='x') addBox(group,x+w/2,baseY+0.018,z+d/2+sgn*(d/2-0.06),w,0.012,0.12,'paint_ped',
              `SAFETY|${fkey}|${nm}|lane${li}edge`,false);
        else addBox(group,x+w/2+sgn*(w/2-0.06),baseY+0.018,z+d/2,0.12,0.012,d,'paint_ped',
              `SAFETY|${fkey}|${nm}|lane${li}edge`,false);
      }
    }
    // أسهم اتجاه الحركة
    if(L.arrow!==false&&kind!=='zone'){
      const n=Math.max(1,Math.min(Math.floor(len/6),20));
      const sign=(L.reverse?-1:1);
      for(let i=0;i<n;i++){
        const u=len*((i+0.5)/n);
        const cx=dir==='x'? x+u : x+w/2, cz=dir==='x'? z+d/2 : z+u;
        const a=Math.min(wid*0.28,0.55);
        for(const s of [-1,1]){
          const rot=(dir==='x'? (s*sign*Math.PI/4) : (Math.PI/2 + s*sign*Math.PI/4));
          addBox(group,cx,baseY+0.024,cz,a*1.6,0.012,0.13,'paint_ped',
            `SAFETY|${fkey}|${nm}|arrow${li}_${i}`,false,null,rot);
        }
      }
    }
  });
}
function buildConveyor(group,x,z,w,d,dir,baseY,fkey,nm,li,L){
  const h=+L.h||0.85, len=dir==='x'?w:d, wid=dir==='x'?d:w;
  const cx=x+w/2, cz=z+d/2;
  addBox(group,cx,baseY+h,cz,w,0.10,d,'belt',`FURN|${fkey}|${nm}|conv${li}`,true);
  for(const sgn of [-1,1]){                     // حواجز أمان جانبية
    if(dir==='x') addBox(group,cx,baseY+h+0.16,cz+sgn*(d/2-0.03),w,0.22,0.06,'guard',
          `SAFETY|${fkey}|${nm}|convrail${li}`,false);
    else addBox(group,cx+sgn*(w/2-0.03),baseY+h+0.16,cz,0.06,0.22,d,'guard',
          `SAFETY|${fkey}|${nm}|convrail${li}`,false);
  }
  const legs=Math.max(2,Math.min(Math.floor(len/2.5),24));
  for(let i=0;i<legs;i++){
    const u=len*(i/(legs-1||1));
    const lx=dir==='x'? x+u : cx, lz=dir==='x'? cz : z+u;
    addBox(group,lx,baseY+h/2,lz,0.09,h,0.09,'frame',`FURN|${fkey}|${nm}|convleg${li}_${i}`,false);
  }
  // نقاط إيقاف الطوارئ كل ~12م
  const es=Math.max(1,Math.floor(len/12));
  for(let i=0;i<es;i++){
    const u=len*((i+0.5)/es);
    const ex2=dir==='x'? x+u : cx+wid/2, ez2=dir==='x'? cz+wid/2 : z+u;
    addBox(group,ex2,baseY+1.05,ez2,0.16,0.16,0.08,'safety',`SAFETY|${fkey}|${nm}|estop${li}_${i}`,false);
  }
}
/* محطات عمل متكرّرة (تغليف/فحص/ملصقات/فرز) */
const STA_DEF={pack:{w:1.8,d:0.9,h:0.9,pitch:2.6,screen:true,printer:true},
  inspect:{w:1.6,d:0.9,h:0.9,pitch:2.4,screen:true,printer:false},
  label:{w:1.2,d:0.8,h:0.9,pitch:1.8,screen:true,printer:true},
  qa:{w:1.4,d:0.9,h:0.9,pitch:2.2,screen:true,printer:false},
  sort:{w:2.2,d:1.0,h:0.85,pitch:3.0,screen:false,printer:false},
  void:{w:1.2,d:1.0,h:1.3,pitch:2.0,screen:false,printer:false},
  desk:{w:1.5,d:0.75,h:0.75,pitch:2.0,screen:true,printer:false},
  charger:{w:0.7,d:0.5,h:0.5,pitch:1.2,screen:false,printer:false},
  locker:{w:0.9,d:0.5,h:1.9,pitch:0.95,screen:false,printer:false},
  wrap:{w:1.6,d:1.6,h:2.0,pitch:3.0,screen:false,printer:false}};
function buildStations(group, room, fkey, baseY, def){
  const [rx,rz,rw,rd]=room.rect, nm=room.id||'room';
  acsList(room,'stations').forEach((S,si)=>{
    const K=STA_DEF[S.kind]||STA_DEF.pack;
    const w=+S.w||K.w, d=+S.d||K.d, h=+S.h||K.h, pitch=+S.pitch||K.pitch;
    const dir=(S.dir==='z')?'z':'x';
    const n=Math.max(1,Math.min(+S.count||1,60));
    const x0=rx+(+S.x||0.6), z0=rz+(+S.z||0.6);
    const tint=normHex(S.color);
    for(let i=0;i<n;i++){
      const cx=dir==='x'? x0+pitch*i+w/2 : x0+w/2;
      const cz=dir==='x'? z0+d/2 : z0+pitch*i+d/2;
      if(cx>rx+rw+0.2||cz>rz+rd+0.2) break;
      addBox(group,cx,baseY+h-0.04,cz,w,0.08,d,'counter',`FURN|${fkey}|${nm}|st${si}_${i}`,true,tint);
      for(const sx of [-1,1]) for(const sz of [-1,1])
        addBox(group,cx+sx*(w/2-0.08),baseY+h/2,cz+sz*(d/2-0.08),0.07,h,0.07,'frame',
          `FURN|${fkey}|${nm}|stleg${si}_${i}`,false);
      if(K.screen) addBox(group,cx,baseY+h+0.28,cz-d/2+0.1,0.52,0.34,0.04,'screen',
          `ELEC|${fkey}|${nm}|stscr${si}_${i}`,false);
      if(K.printer) addBox(group,cx+w/2-0.22,baseY+h+0.11,cz,0.3,0.18,0.28,'frame',
          `ELEC|${fkey}|${nm}|stprn${si}_${i}`,false);
      if(S.kind==='void') addBox(group,cx,baseY+h+0.3,cz,w*0.8,0.55,d*0.8,'goods',
          `FURN|${fkey}|${nm}|stvoid${si}_${i}`,false);
      if(S.kind==='charger') addBox(group,cx,baseY+0.1,cz+d/2+0.35,0.55,0.2,0.55,'robot',
          `FURN|${fkey}|${nm}|strobot${si}_${i}`,false);
    }
  });
}
/* أرصفة التحميل: باب منزلق + لوح تسوية + مصدّات */
function buildDocks(group, room, fkey, baseY, def){
  const rect=room.rect, nm=room.id||'room';
  acsList(room,'docks').forEach((D,di)=>{
    const n=Math.max(1,Math.min(+D.count||1,24));
    const pitch=+D.pitch||(( +D.width||3.0)+1.8);
    for(let i=0;i<n;i++){
      const off=(+D.offset||3)+pitch*i, wd=+D.width||3.0, dh=+D.height||4.0;
      const e=normEdge(D.edge);
      const [axis,fixed]=edgeGeom(e,rect);
      const uc=openU(e,rect,off);
      const outw=(e==='N'||e==='W')?-1:1;
      if(axis==='x'){
        addBox(group,uc,baseY+dh/2,fixed,wd,dh,0.10,'dockdoor',`DOOR|${fkey}|${nm}|dock${di}_${i}`,true);
        addBox(group,uc,baseY+0.06,fixed+outw*0.9,wd,0.12,1.7,'frame',`FLOOR|${fkey}|${nm}|leveler${di}_${i}`,false);
        for(const s of [-1,1]) addBox(group,uc+s*(wd/2+0.12),baseY+0.55,fixed+outw*0.12,0.22,0.5,0.3,'bumper',
              `SAFETY|${fkey}|${nm}|bump${di}_${i}`,false);
      }else{
        addBox(group,fixed,baseY+dh/2,uc,0.10,dh,wd,'dockdoor',`DOOR|${fkey}|${nm}|dock${di}_${i}`,true);
        addBox(group,fixed+outw*0.9,baseY+0.06,uc,1.7,0.12,wd,'frame',`FLOOR|${fkey}|${nm}|leveler${di}_${i}`,false);
        for(const s of [-1,1]) addBox(group,fixed+outw*0.12,baseY+0.55,uc+s*(wd/2+0.12),0.3,0.5,0.22,'bumper',
              `SAFETY|${fkey}|${nm}|bump${di}_${i}`,false);
      }
    }
  });
}
/* فتحات الأرصفة تُحسَب ضمن فتحات الجدار حتى لا يُبنى جدار مصمت مكانها */
function dockOpenings(room){
  const out={N:[],S:[],E:[],W:[]};
  acsList(room,'docks').forEach(D=>{
    const n=Math.max(1,Math.min(+D.count||1,24));
    const wd=+D.width||3.0, dh=+D.height||4.0, pitch=+D.pitch||(wd+1.8), e=normEdge(D.edge);
    for(let i=0;i<n;i++) out[e].push([openU(e,room.rect,(+D.offset||3)+pitch*i),wd,0,dh]);
  });
  return out;
}

const ADMIN_ROLES={office:1,admin:1,it:1,staff:1,maintenance:1,meeting:1};
/* يقصّ مستطيلات الفراغ من بلاطة مستطيلة بشرائح محاذية للمحاور — لا CSG ولا
   تقريب: كل شريحة صلبة فعلاً، وما تحت النواة يبقى مفتوحاً. */
function slabStrips(x0,z0,W,D,holes){
  const cut=(lo,hi,vals)=>{ const s=new Set([lo,hi]);
    vals.forEach(v=>{ if(v>lo+1e-6&&v<hi-1e-6) s.add(v); });
    return Array.from(s).sort((a,b)=>a-b); };
  const hs=(holes||[]).map(h=>[Math.max(x0,h[0]),Math.max(z0,h[1]),
    Math.min(x0+W,h[0]+h[2]),Math.min(z0+D,h[1]+h[3])]).filter(h=>h[2]>h[0]+1e-6&&h[3]>h[1]+1e-6);
  if(!hs.length) return [[x0,z0,W,D]];
  const xs=cut(x0,x0+W,hs.flatMap(h=>[h[0],h[2]]));
  const zs=cut(z0,z0+D,hs.flatMap(h=>[h[1],h[3]]));
  const out=[];
  for(let i=0;i+1<zs.length;i++){
    let run=null;
    for(let j=0;j+1<xs.length;j++){
      const cx=(xs[j]+xs[j+1])/2, cz=(zs[i]+zs[i+1])/2;
      const solid=!hs.some(h=>cx>h[0]&&cx<h[2]&&cz>h[1]&&cz<h[3]);
      if(solid){ if(run) run[1]=xs[j+1]; else run=[xs[j],xs[j+1]]; }
      else if(run){ out.push([run[0],zs[i],run[1]-run[0],zs[i+1]-zs[i]]); run=null; }
    }
    if(run) out.push([run[0],zs[i],run[1]-run[0],zs[i+1]-zs[i]]);
  }
  return out;
}
function compile(data){
  OBJ_UNKNOWN=[]; acsBuildDefectsReset();
  const grp=new THREE.Group(); grp.name='BUILDING';
  const site=data.site||{w:30,d:25};
  const bt=String(((data.meta||{}).type)||'residential').toLowerCase();
  const industrial=/warehouse|industrial|factory|logistic/.test(bt);
  const def={site,wall_h:data.wall_h||3.0,wall_t:data.wall_t||0.15,industrial:industrial};
  const fh=data.floor_height||(def.wall_h+0.2);
  /* البلاطة تُقرأ من المصرِّف المعماري: نفس مصدر الحقيقة الذي تقرأه العلاقات
     والمسافات، وفراغات النوى تُقصّ منها فعلاً. */
  let ARCH=null;
  try{ ARCH=__ACS_LATE.compileArchitecture(data,'bld_0',null,0); }catch(e){ ARCH=null; }
  /* KI-25/F-42 — رقم الدور مشتقّ لا مُفترَض.
     كان: ‎const baseY=lvl.index*fh; const fkey='F'+lvl.index;‎ بلا فحص. عقد
     النموذج يوجب `index` صحيحاً، لكن العارض يقرأ نماذج من مصادر لا يحكمها
     عقد الخادم (استيراد JSON، DXF، نموذج محفوظ من نسخة أقدم) — وقد قرأ فعلاً
     نموذجاً من خادمنا نفسه بعد أن ضاق توجيه البيان في KI-24. النتيجة كانت
     ‎undefined × 4 = NaN‎ لكل دور و‎'Fundefined'‎ مفتاحاً واحداً للأدوار
     كلّها: ألفا شبكة تُبنى عند إحداثيّة غير معرَّفة، والعدّاد يقول «تمّ».
     الآن: رقم صحيح موجود يُحترَم، وغيابه يُشتقّ من ترتيب المصفوفة ويُحصى. */
  const _levels=(data.levels||[]).map((lvl,i)=>{
    const raw=(lvl&&typeof lvl==='object')?lvl:{};
    let idx=Number(raw.index);
    if(!(isFinite(idx)&&idx>=0&&idx===Math.floor(idx))){
      idx=i;
      acsBuildDefect('derived_level_index','LEVEL_INDEX_MISSING',
                     String(raw.id||('#'+i)));
    }
    return {raw:raw,index:idx};
  });
  _levels.forEach(_lv=>{
    const lvl=_lv.raw, li=_lv.index;
    const fdef=(data.floors||{})[lvl.template]||{}; const baseY=li*fh; const fkey='F'+li;
    const holes=ARCH?ARCH.voids.filter(v=>v.level_index===li).map(v=>v.rect):[];
    /* PHASE10_FOOTPRINT_PLATE (KI-3 / F-07) — كان اللوح يُبنى على مستطيل
       الموقع كاملاً (المُدخَل السابق: صفر، صفر، عرض الموقع، عمق الموقع)
       تحت الاصطلاح السابق PHASE1_SITE_WIDE_PLATE المثبَّت بخطّ أساس المرحلة 4،
       فيمتدّ لوح كل دور على الموقع كلّه ويبدو فوق مبنًى أصغر من قطعة الأرض
       صفيحةً طائرة معلَّقة بلا شيء تحت حوافّها. صار الامتداد اتحاد بصمات غرف
       الدور نفسه، محسوباً بعقد الامتداد الوحيد pqPlateRect (توأمه في بايثون
       acs_pbr.plate_rect) — لا حاسب امتداد ثانٍ — والموقع بديلٌ أخير معلَن
       (SITE_FALLBACK) حين لا يصرّح الدور بغرفة. مستوى الموقع العرضي يبقى
       منفصلاً وبمقاس الموقع (ensureGround). التغيير عرضيّ بحت: لا مستطيل غرفة
       ولا مساحة ولا كمية ولا بصمة نموذج يتغيّر به. السياسة وسابقتها وسببها
       معلَنة في acs_pbr.PLATE_POLICY / PQ_PLATE_POLICY. */
    const _pp=__ACS_LATE.pqPlateRect((fdef.rooms||[]).map(r=>r.rect),[0,0,site.w,site.d]);
    const _pr=(_pp&&_pp.valid&&Array.isArray(_pp.rect))?_pp.rect:[0,0,site.w,site.d];
    slabStrips(_pr[0],_pr[1],_pr[2],_pr[3],holes).forEach((s,k)=>
      addBox(grp,s[0]+s[2]/2,baseY-0.075,s[1]+s[3]/2,s[2],0.15,s[3],'floor',
             `FLOOR|${fkey}|slab|${k}`,true));
    (fdef.rooms||[]).forEach(r=>buildRoom(grp,r,fkey,baseY,def));
  });
  /* طبقة العرض الإنشائي — منفصلة ومخفيّة افتراضياً. أبعادها قد تكون احتياط عرض،
     ولذلك يحمل كل جسم مصدر هندسته صراحةً في userData ولا يُصدَّر كحقيقة إنشائية. */
  try{
    const ST=__ACS_LATE.compileStructure(data,'bld_0',null,0,ARCH);
    __ACS_LATE.structRenderItems(ST).forEach(it=>{
      if(it.kind==='GRID_LINE'||!(it.ex>0&&it.ey>0&&it.ez>0)) return;
      const m=addBox(grp,it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,'frame',it.name,false,
                     STRUCT_KIND_COLOR[it.kind]||'#64748b',it.rot_y||0);
      if(m){ m.visible=false;
        m.userData.struct={id:it.id,kind:it.kind,geometry_source:it.geometry_source,
          element_source:it.element_source,material_ref:it.material_ref}; } });
  }catch(e){ /* غياب بيانات إنشائية لا يمنع العرض المعماري إطلاقاً */ }
  /* طبقات عرض MEP — منفصلة لكل تخصّص ومخفيّة افتراضياً. كثير من الأبعاد هنا
     احتياط عرض، ولذلك يحمل كل جسم مصدر هندسته صراحةً ولا يُصدَّر كقيمة هندسية. */
  try{
    const MP=__ACS_LATE.compileMep(data,'bld_0',null,0,ARCH,null,true);
    __ACS_LATE.mepRenderItems(MP).forEach(it=>{
      if(!(it.ex>0&&it.ey>0&&it.ez>0)) return;
      const disc=(it.kind==='RISER')?'RISER':it.discipline;
      const m=addBox(grp,it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,'frame',it.name,false,
                     MEP_DISC_COLOR[disc]||'#94a3b8',it.rot_y||0);
      if(m){ m.visible=false;
        m.userData.mep={id:it.id,kind:it.kind,discipline:it.discipline,
          geometry_source:it.geometry_source,element_source:it.element_source,
          terminal_type:it.terminal_type||null,adapted:it.adapted===true}; } });
  }catch(e){ /* غياب بيانات MEP لا يمنع العرض المعماري ولا الإنشائي */ }
  /* طبقات عرض الحريق وسلامة الأرواح — مخفيّة افتراضياً. ما رسمته طبقة MEP
     يبقى لها: العنصر المُشار إليه هنا يُوسم referenced ولا يُرسم مرّة ثانية. */
  try{
    const FL=__ACS_LATE.compileFls(data,'bld_0',null,0,ARCH,null,null);
    __ACS_LATE.flsRenderItems(FL).forEach(it=>{
      if(it.render_mode!=='emitted') return;          // لا تكرار لهندسة MEP
      if(!(it.ex>0&&it.ey>0&&it.ez>0)) return;
      const m=addBox(grp,it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,'frame',it.name,false,
                     FLS_LAYER_COLOR[it.layer]||'#9ca3af',0);
      if(m){ m.visible=false;
        m.userData.fls={id:it.id,kind:it.kind,device_type:it.device_type,
          category:it.category,layer:it.layer,render_mode:it.render_mode,
          geometry_source:it.geometry_source,element_source:it.element_source}; } });
  }catch(e){ /* غياب بيانات الحريق لا يمنع أي عرض آخر */ }
  return grp;
}

/* ========================= محلّل الوصف العربي (best-effort) ========================= */
const AR_NUM={'صفر':0,'واحد':1,'واحدة':1,'اثنين':2,'اثنان':2,'اثنتين':2,'ثلاث':3,'ثلاثة':3,'اربع':4,'أربع':4,'اربعة':4,'أربعة':4,
  'خمس':5,'خمسة':5,'ست':6,'ستة':6,'سبع':7,'سبعة':7,'ثمان':8,'ثمانية':8,'ثماني':8,'تسع':9,'تسعة':9,'عشر':10,'عشرة':10};
function normDigits(s){return s
  .replace(/[٠-٩]/g,d=>String(d.charCodeAt(0)-0x0660))
  .replace(/[۰-۹]/g,d=>String(d.charCodeAt(0)-0x06F0))
  .replace(/٫/g,'.').replace(/٬/g,'');}
const ROOM_KW=['مجلس','صالة','صاله','صالون','مطبخ','نوم','حمام','دورة','مدخل','فوييه','فوية','مالبس','ملابس',
  'خادمة','غسيل','بلكونة','بلكونه','مكتب','مكتبة','غرفة','مخزن','لوبي','استقبال','استوديو','مصلى','حارس','ممر'];
function stripBidi(s){return s.replace(/[‎‏‪-‮⁦-⁩ـ]/g,'');}
function hasRoomKW(s){return ROOM_KW.some(k=>s.includes(k));}
function cleanName(s){return stripBidi(s).replace(/\d+(\.\d+)?\s*م²?/g,' ')
  .replace(/[()\[\]:،؛\/\-–—|]/g,' ').replace(/\s+/g,' ').trim();}
function detectMeta(text){const t=stripBidi(normDigits(text)); let W=null,D=null,nF=null,m;
  if((m=t.match(/واجهة\s*(\d+(?:\.\d+)?)/)))W=parseFloat(m[1]);
  if((m=t.match(/عمق\s*(\d+(?:\.\d+)?)/)))D=parseFloat(m[1]);
  if((m=t.match(/(\d+)[\s+]*أدوار?\s*متكرر/)))nF=parseInt(m[1]);
  return {W,D,nF};}
function countNear(block,kw){
  // يبحث عن رقم (رقم أو كلمة عربية) قبل/بعد الكلمة المفتاحية، وإلا 1
  const re=new RegExp('([\\u0600-\\u06ff]+|\\d+)\\s+'+kw+'|'+kw+'\\s*(\\d+)?','g');
  let m,total=0,found=false;
  while((m=re.exec(block))){found=true;
    let n=1; const pre=m[1],post=m[2];
    if(post&&/\d+/.test(post))n=parseInt(post);
    else if(pre){ if(/\d+/.test(pre))n=parseInt(pre); else if(AR_NUM[pre]!=null)n=AR_NUM[pre]; }
    total+=n;
  }
  return found?Math.max(total,1):0;
}
function parseDescription(text, siteW, siteD, nFloors){
  text=normDigits(text);
  const lines=text.split(/\n|،/).map(s=>s.trim()).filter(Boolean);
  const dim=/(\d+(?:\.\d+)?)\s*[×xX*]\s*(\d+(?:\.\d+)?)/;
  const rooms=[];
  for(const ln of lines){
    const dm=ln.match(dim); if(!dm) continue;
    const w=parseFloat(dm[1]), d=parseFloat(dm[2]);
    if(!(w>=0.8&&w<=15&&d>=0.8&&d<=15)) continue;   // مقاسات غرف بالأمتار فقط (تستبعد سم والأرض)
    const before=cleanName(ln.slice(0,dm.index));
    const after=cleanName(ln.slice(dm.index+dm[0].length));
    let name = hasRoomKW(after)?after : hasRoomKW(before)?before : '';
    if(!name) continue;                             // لازم اسم غرفة معروف (يستبعد الأعمدة/الأبواب/المواقف)
    name=name.split(/\s+/).slice(0,5).join(' ');
    let id=name.replace(/\s+/g,'_').slice(0,22)||('r'+(rooms.length+1));
    if(rooms.some(r=>r.id===id)) continue;          // تفادي التكرار من جدول المساحات
    rooms.push({id,name,w,d,block:stripBidi(ln)});
  }
  const clean=rooms;
  // تخطيط تلقائي (shelf packing) داخل الأرض
  const margin=1, gap=0.4; let cx=margin, rowZ=margin, rowMaxD=0;
  clean.forEach(r=>{
    if(cx+r.w>siteW-margin){ cx=margin; rowZ+=rowMaxD+gap; rowMaxD=0; }
    r.rect=[cx,rowZ,r.w,r.d]; cx+=r.w+gap; rowMaxD=Math.max(rowMaxD,r.d);
    // أبواب/نوافذ/نقاط من النص
    r.doors=[{edge:'N',offset:r.w/2,width:/بلوط|خشب|مصفح/.test(r.block)?1.0:0.9,height:2.1,
              material:/زجاج/.test(r.block)?'glass':'wood'}];
    r.windows=[]; if(/نافذة|نوافذ|شباك/.test(r.block)){const wm=r.block.match(dim);
      r.windows.push({edge:'S',offset:r.d/2>0?r.w/2:1,width:Math.min(r.w-1,/(\d+(?:\.\d+)?)\s*متر/.test(r.block)?parseFloat(RegExp.$1):2),sill:0.9,height:1.6});}
    r.points=[]; r.furniture=[];
    const put=(type,n,spread)=>{for(let i=0;i<n;i++){const fx=0.5+((i+1)/(n+1))*(r.w-1);
      r.points.push({type, x:fx, z:spread});}};
    const nOut=countNear(r.block,'(?:أفياش|افياش|فيش|فيشين|مخارج|مخرج)'); if(nOut)put('outlet',Math.min(nOut,10),0.3);
    if(/مفتاح/.test(r.block))r.points.push({type:'switch',x:r.w-0.5,z:0.5});
    if(/شبكة|RJ45|إنترنت|انترنت/.test(r.block))r.points.push({type:'network',x:0.3,z:r.d/2});
    if(/شاشة|تلفزيون|تلفاز/.test(r.block))r.points.push({type:'tv',x:r.w-0.3,z:r.d/2});
    const nCam=countNear(r.block,'(?:كاميرات|كاميرا)'); for(let i=0;i<nCam;i++)r.points.push({type:'camera',x:0.3+i,z:0.3});
    if(/ثريا|إنارة|انارة|سبوت|لمبة|إضاءة/.test(r.block))r.points.push({type:'light',x:r.w/2,z:r.d/2});
    else r.points.push({type:'light',x:r.w/2,z:r.d/2});
    if(/تكييف|مكيف|VRF|سبليت/.test(r.block))r.points.push({type:'ac',x:r.w/2,z:0.2});
    if(/دخان/.test(r.block))r.points.push({type:'smoke',x:r.w/2,z:r.d/2});
    if(/رشاش/.test(r.block))r.points.push({type:'sprinkler',x:r.w/2,z:r.d*0.7});
    delete r.block; delete r._pending; delete r.w; delete r.d; delete r.name;
  });
  // مبنى: أرضي بسيط + أدوار نموذجية مكرّرة + سطح
  const levels=[{index:0,name:'الأرضي',template:'ground'}];
  for(let i=1;i<=nFloors;i++)levels.push({index:i,name:FLOOR_NAMES['F'+i]||('الدور '+i),template:'typical'});
  levels.push({index:nFloors+1,name:'السطح',template:'roof'});
  const ground={rooms:[{id:'lobby',rect:[siteW/2-4,1,8,7],
    doors:[{edge:'N',offset:4,width:2.5,height:2.5,material:'glass'}],
    windows:[{edge:'N',offset:1.5,width:2,sill:1,height:1.6}],
    points:[{type:'light',x:4,z:3.5},{type:'camera',x:0.3,z:0.3},{type:'tv',x:7.7,z:3.5}],
    furniture:[{name:'reception',x:4,z:3.5,w:2.4,d:0.8,h:1.1,mat:'counter'}]}]};
  const roof={rooms:[{id:'parapet',rect:[0.2,0.2,siteW-0.4,siteD-0.4],wall_h:1.4},
    {id:'tanks',rect:[1,1,4,3],furniture:[{name:'tank',x:2,z:1.5,w:1.6,d:1.6,h:2,mat:'furn'}]},
    {id:'solar',rect:[siteW-12,siteD-8,10,6],furniture:[{name:'panel',x:5,z:3,w:8,d:4,h:0.15,mat:'tv'}]}]};
  return {site:{w:siteW,d:siteD},floor_height:3.2,wall_h:3.0,wall_t:0.15,
    levels, floors:{ground, typical:{rooms:clean}, roof}};
}

/* توليد قياسي سريع */
/* ==================================================================
   مولّد مستودع تجارة إلكترونية كامل — محلي، بلا خادم، بأي مقاس أرض.
   يغطّي البنود التسعة: استلام · تخزين · التقاط · تغليف · فرز · شحن ·
   حركة وسلامة · إدارة وخدمات · ترميز لوني وقياسات واقعية.
   ================================================================== */
function warehouseModel(W,D,opt){
  opt=opt||{}; W=Math.max(30,+W||120); D=Math.max(25,+D||80);
  const H=Math.max(6,Math.min(+opt.clear||12,16));      // ارتفاع صافٍ
  const OPT_DOCK=+opt.docks||0, OPT_PACK=+opt.pack||0, OPT_AISLE=+opt.aisle||0;
  const R=[], P=(t,x,z,h)=>{const o={type:t,x:+x.toFixed(2),z:+z.toFixed(2)};if(h!=null)o.height=h;return o;};
  const Z=(id,rect,role,extra)=>{const r=Object.assign({id,rect:rect.map(v=>+v.toFixed(2)),
    role:role||undefined,walls:'none'},extra||{}); R.push(r); return r;};
  const fx=f=>W*f, fz=f=>D*f;
  // حزم أفقية (نِسَب مأخوذة من تخطيط 120×80 المرجعي)
  const b={in0:0, in1:fz(0.1125), un1:fz(0.1875), st1:fz(0.275),
           sto1:fz(0.675), pick1:fz(0.80), pack1:fz(0.9125), out1:D};

  /* غلاف المبنى + سلامة محيطية */
  const shell=[];
  for(let i=0;i<Math.max(5,Math.round(W/25));i++){const x=W*(i+0.5)/Math.max(5,Math.round(W/25));
    shell.push(P('camera',x,1),P('camera',x,D-1));}
  for(let i=0;i<Math.max(8,Math.round(W/12));i++){const x=W*(i+0.5)/Math.max(8,Math.round(W/12));
    shell.push(P('extinguisher',x,0.6),P('extinguisher',x,D-0.6));}
  shell.push(P('exit',2,0.4,2.4),P('exit',W-2,0.4,2.4),P('exit',2,D-0.4,2.4),P('exit',W-2,D-0.4,2.4),
    P('exit',0.4,D/2,2.4),P('exit',W-0.4,D/2,2.4),P('gate',1,D*0.5),P('gate',W-1,D*0.5),
    P('camera',1,D*0.25),P('camera',1,D*0.75),P('camera',W-1,D*0.25),P('camera',W-1,D*0.75),
    P('hydrant',0.6,D*0.15),P('hydrant',0.6,D*0.5),P('hydrant',0.6,D*0.85),
    P('hydrant',W-0.6,D*0.15),P('hydrant',W-0.6,D*0.5),P('hydrant',W-0.6,D*0.85));
  Z('envelope',[0,0,W,D],null,{walls:'full',wall_h:H,points:shell});

  /* ١ — الاستلام والوارد */
  const nDock=OPT_DOCK||Math.max(3,Math.floor(fx(0.43)/6.2));
  Z('inbound_docks',[0,0,fx(0.433),b.in1],'receiving',{
    docks:[{edge:'N',offset:4.5,width:3.6,height:4.2,count:nDock,pitch:6.2}],
    lanes:[{kind:'forklift',x:0.5,z:b.in1-3.8,w:fx(0.433)-1,d:3.4,dir:'x'}],
    points:[...Array(nDock)].map((_,i)=>P('scanner',3+6.2*i,1.2))
      .concat([...Array(nDock)].map((_,i)=>P('sign',4.5+6.2*i,0.6,3.2)))
      .concat([P('camera',fx(0.21),1),P('extinguisher',fx(0.42),b.in1-0.6),P('estop',fx(0.1),b.in1-0.6)])});
  Z('fast_unload',[0,b.in1,fx(0.433),b.un1-b.in1],'receiving',{
    lanes:[{kind:'conveyor',x:2,z:1.4,w:fx(0.38),d:0.9,dir:'x',h:0.85},
           {kind:'pedestrian',x:0.5,z:(b.un1-b.in1)-1.9,w:fx(0.42),d:1.4,dir:'x'}],
    points:[P('palletjack',fx(0.05),2.6),P('palletjack',fx(0.15),2.6),P('palletjack',fx(0.25),2.6),
            P('forklift',fx(0.1),1),P('forklift',fx(0.3),1),P('smoke',fx(0.21),2)]});
  const nLane=Math.max(6,Math.floor(fx(0.65)/6.4));
  Z('inbound_staging',[0,b.un1,fx(0.65),b.st1-b.un1],'receiving',{
    lanes:[...Array(nLane)].map((_,i)=>({kind:'zone',x:6.4*i+0.3,z:0.3,w:6,d:(b.st1-b.un1)-0.6,dir:'z',arrow:false})),
    points:[...Array(nLane)].map((_,i)=>P('sign',6.4*i+3.3,0.5,2.6))
      .concat([P('camera',fx(0.32),0.8),P('smoke',fx(0.32),(b.st1-b.un1)/2)])});
  Z('qc_inspection',[fx(0.433),0,fx(0.217),b.un1],'qc',{
    stations:[{kind:'inspect',x:1.5,z:1.5,count:Math.max(3,Math.floor(fx(0.2)/4)),pitch:4,dir:'x'},
              {kind:'qa',x:1.5,z:b.un1*0.6,count:Math.max(3,Math.floor(fx(0.2)/4.6)),pitch:4.6,dir:'x'}],
    points:[P('scale',fx(0.19),3),P('printer',fx(0.19),7),P('monitor',fx(0.1),0.6),
            P('bin',3,b.un1-1.2),P('bin',9,b.un1-1.2),P('bin',15,b.un1-1.2),
            P('camera',fx(0.1),1),P('smoke',fx(0.1),b.un1/2),P('extinguisher',fx(0.2),b.un1-0.8)]});
  Z('crossdock',[fx(0.65),0,W-fx(0.65),b.un1],'crossdock',{
    docks:[{edge:'N',offset:4,width:3.6,height:4.2,count:Math.max(2,Math.floor((W-fx(0.65))/7.5)),pitch:7.5}],
    lanes:[{kind:'conveyor',x:2,z:b.un1*0.5,w:(W-fx(0.65))-4,d:0.9,dir:'x',h:0.9},
           {kind:'forklift',x:1,z:b.un1-4.2,w:(W-fx(0.65))-2,d:3.6,dir:'x'}],
    points:[P('diverter',10,b.un1*0.55),P('diverter',20,b.un1*0.55),P('diverter',30,b.un1*0.55),
            P('camera',(W-fx(0.65))/2,1),P('smoke',(W-fx(0.65))/2,b.un1/2)]});
  Z('replenishment',[fx(0.65),b.un1,W-fx(0.65)-fx(0.133),b.st1-b.un1],'circulation',{
    lanes:[{kind:'one_way',x:0.4,z:0.6,w:W-fx(0.65)-fx(0.133)-0.8,d:Math.max(3.2,(b.st1-b.un1)-1.2),dir:'x'}],
    points:[P('sign',(W-fx(0.65)-fx(0.133))/2,0.5,2.8)]});
  Z('maintenance',[W-fx(0.133),b.un1,fx(0.133),b.st1-b.un1],'maintenance',{
    walls:'full',wall_h:4,doors:[{edge:'W',offset:(b.st1-b.un1)/2,width:1.2,height:2.4,material:'wood'}],
    stations:[{kind:'desk',x:1,z:1,count:3,pitch:2.4,dir:'x'}],
    points:[P('light',fx(0.066),(b.st1-b.un1)/2),P('smoke',fx(0.066),(b.st1-b.un1)/2),
            P('outlet',2,(b.st1-b.un1)-0.4,0.40),P('switch',fx(0.12),(b.st1-b.un1)-1,1.20),
            P('extinguisher',fx(0.12),1),P('eyewash',1,(b.st1-b.un1)-1)]});

  /* ٢ — التخزين + العمود الإداري */
  const sd=b.sto1-b.st1, adm=fx(0.133), sx=W-adm;
  const cols=[['bulk_pallet_A','storage',0.283,{kind:'pallet',aisle:Math.max(OPT_AISLE||3.4,3.4),levels:4,h:Math.min(H-3,9)}],
              ['medium_shelf_B','shelf',0.217,{kind:'shelf',aisle:1.6,levels:5,h:2.6}],
              ['bin_storage_C','bin',0.167,{kind:'bin',aisle:1.2,levels:6,h:2.2}],
              ['flow_racks_fast','storage',0.15,{kind:'flow',aisle:1.8,levels:4,h:2.4}]];
  let cx=0;
  cols.forEach(([id,role,frac,rk])=>{
    const cw=sx*frac/0.817*0.94;
    Z(id,[cx,b.st1,cw,sd],role,{
      racks:[Object.assign({x:0.6,z:0.6,w:cw-1.2,d:sd-1.2,dir:'x'},rk)],
      points:[P('sign',cw/2,0.8,3.6),P('camera',cw/2,0.8),P('extinguisher',1,sd-1),
              P('extinguisher',cw-1,sd-1)]});
    cx+=cw;
  });
  Z('replen_aisle_main',[cx,b.st1,Math.max(4,sx-cx),sd],'circulation',{
    lanes:[{kind:'one_way',x:0.6,z:0.5,w:Math.max(3.2,sx-cx-1.2),d:sd-1,dir:'z'}],
    points:[P('sign',Math.max(2,(sx-cx)/2),1,3)]});
  const off=[['inventory_office','office',0.25,'glass'],['it_server_room','it',0.1875,'full'],
             ['meeting_room','admin',0.1875,'full'],['rest_area','staff',0.21875,'full'],
             ['lockers','staff',0.15625,'full']];
  let oz=b.st1;
  off.forEach(([id,role,frac,wl])=>{
    const oh=sd*frac;
    const ex={walls:wl,wall_h:3.2,
      doors:[{edge:'W',offset:oh/2,width:1.0,height:2.1,material:wl==='glass'?'glass':'wood'}],
      points:[P('light',adm/2,oh/2),P('smoke',adm/2,oh/2),P('ac',adm/2,0.4),
              P('outlet',2,oh-0.4,0.40),P('outlet',adm-2,oh-0.4,0.40),P('switch',adm*0.28,oh-0.5,1.20)]};
    if(id==='inventory_office'){ ex.windows=[{edge:'W',offset:oh*0.8,width:Math.min(4,oh*0.4),sill:0.9,height:1.8}];
      ex.stations=[{kind:'desk',x:1,z:1,count:4,pitch:2.6,dir:'x'}]; ex.points.push(P('monitor',adm/2,0.6)); }
    if(id==='it_server_room') ex.points.push(P('server',3,1),P('server',6,1),P('server',9,1),P('network',1,oh/2,0.40));
    if(id==='meeting_room') ex.furniture=[{name:'table',x:adm/2,z:oh/2,w:Math.min(4,adm*0.5),d:1.4,h:0.75,mat:'furn'}];
    if(id==='rest_area') ex.furniture=[{name:'counter',x:adm/2,z:0.7,w:adm*0.5,d:0.7,h:0.9,mat:'counter'},
      {name:'sofa',x:adm*0.7,z:oh-1,w:2.4,d:0.8,h:0.8,mat:'furn_soft'}];
    if(id==='lockers') ex.stations=[{kind:'locker',x:0.6,z:0.4,count:Math.floor(adm/0.98),pitch:0.98,dir:'x'}];
    Z(id,[sx,oz,adm,oh],role,ex); oz+=oh;
  });

  /* ٣ — الالتقاط */
  const pd=b.pick1-b.sto1;
  const pk=[['batch_picking','picking',0.20,{kind:'shelf',aisle:1.5,levels:4,h:2.2}],
            ['wave_picking','wave',0.20,{kind:'flow',aisle:1.6,levels:4,h:2.2}],
            ['zone_picking','zone_pick',0.217,{kind:'shelf',aisle:1.5,levels:5,h:2.4}],
            ['amr_field','robot',0.183,null],
            ['human_picking','picking',0.20,{kind:'bin',aisle:1.3,levels:5,h:2.0}]];
  let px=0;
  pk.forEach(([id,role,frac,rk])=>{
    const cw=W*frac, ex={points:[P('sign',cw/2,0.6,3),P('camera',cw/2,0.8),P('smoke',cw/2,pd/2),
      P('extinguisher',cw-1,pd-0.8)]};
    if(rk){ ex.racks=[Object.assign({x:0.6,z:0.6,w:cw-1.2,d:pd*0.55,dir:'x'},rk)];
      ex.lanes=[{kind:'pedestrian',x:0.4,z:pd*0.66,w:cw-0.8,d:Math.max(1.2,pd*0.16),dir:'x'}];
      ex.stations=[{kind:'desk',x:1,z:pd*0.85,count:Math.max(3,Math.floor(cw/3.6)),pitch:3.6,dir:'x'}]; }
    else { ex.lanes=[{kind:'amr',x:0.5,z:pd*0.1,w:cw-1,d:1.4,dir:'x'},
                     {kind:'amr',x:0.5,z:pd*0.4,w:cw-1,d:1.4,dir:'x',reverse:true},
                     {kind:'amr',x:0.5,z:pd*0.7,w:cw-1,d:1.4,dir:'x'}];
           ex.stations=[{kind:'charger',x:1,z:pd*0.88,count:Math.max(4,Math.floor(cw/2)),pitch:2,dir:'x'}];
           ex.points.push(P('robot',cw*0.2,pd*0.17),P('robot',cw*0.5,pd*0.17),P('robot',cw*0.8,pd*0.47),
                          P('estop',cw-0.6,pd/2)); }
    if(id==='wave_picking') for(let i=0;i<Math.floor(cw/1.6);i++) ex.points.push(P('ptl',1.6*i+1,1.2));
    Z(id,[px,b.sto1,cw,pd],role,ex); px+=cw;
  });

  /* ٤+٥ — التغليف والفرز */
  const kd=b.pack1-b.pick1;
  const nPack=OPT_PACK||Math.max(4,Math.floor(W*0.266/2.7));
  Z('packing',[0,b.pick1,W*0.266,kd],'packing',{
    stations:[{kind:'pack',x:1,z:1,count:nPack,pitch:2.7,dir:'x'},
              {kind:'pack',x:1,z:kd*0.6,count:nPack,pitch:2.7,dir:'x'}],
    points:[...Array(nPack)].map((_,i)=>P('scale',2.4+2.7*i,kd*0.3))
      .concat([...Array(nPack)].map((_,i)=>P('printer',2.4+2.7*i,kd*0.85)))
      .concat([P('sign',W*0.133,0.5,3),P('camera',W*0.133,0.8),P('smoke',W*0.133,kd/2),
               P('extinguisher',W*0.26,kd-0.6)])});
  Z('labeling_qa',[W*0.266,b.pick1,W*0.133,kd],'labeling',{
    stations:[{kind:'label',x:1,z:1,count:Math.max(3,Math.floor(W*0.133/2)),pitch:2,dir:'x'}],
    points:[P('scanner',3,kd*0.3),P('scanner',7,kd*0.3),P('monitor',W*0.066,kd*0.75),
            P('printer',W*0.11,kd*0.75),P('sign',W*0.066,0.5,3),P('smoke',W*0.066,kd/2)]});
  Z('void_fill',[W*0.4,b.pick1,W*0.1,kd],'packing',{
    stations:[{kind:'void',x:1,z:1,count:Math.max(2,Math.floor(W*0.1/2.2)),pitch:2.2,dir:'x'}],
    points:[P('sign',W*0.05,0.5,3),P('smoke',W*0.05,kd/2),P('light',W*0.05,kd/2)]});
  Z('consolidation',[W*0.5,b.pick1,W*0.15,kd],'consolidation',{
    racks:[{kind:'cage',x:0.6,z:0.6,w:W*0.15-1.2,d:kd-1.2,dir:'x',aisle:1.2,levels:2,h:2}],
    points:[P('sign',W*0.075,0.5,2.6),P('camera',W*0.075,0.8),P('smoke',W*0.075,kd/2)]});
  Z('auto_sorter',[W*0.65,b.pick1,W*0.233,kd],'sorting',{
    lanes:[{kind:'conveyor',x:1,z:kd*0.14,w:W*0.233-2,d:1,dir:'x',h:0.95},
           {kind:'conveyor',x:1,z:kd*0.5,w:W*0.233-2,d:1,dir:'x',h:0.85},
           {kind:'pedestrian',x:0.5,z:kd*0.8,w:W*0.233-1,d:1.4,dir:'x'}],
    points:[...Array(Math.max(4,Math.floor(W*0.233/3)))].map((_,i)=>P('diverter',3.5+3*i,kd*0.3))
      .concat([...Array(Math.max(4,Math.floor(W*0.233/3)))].map((_,i)=>P('chute',3.5+3*i,kd*0.68)))
      .concat([P('estop',5,kd*0.12),P('estop',W*0.12,kd*0.12),P('sign',W*0.116,0.4,3.2),
               P('camera',W*0.116,0.8),P('smoke',W*0.116,kd/2),P('extinguisher',W*0.22,kd-0.6)])});
  Z('manual_sort',[W*0.883,b.pick1,W*0.117,kd],'sorting',{
    stations:[{kind:'sort',x:1,z:1,count:Math.max(2,Math.floor(W*0.117/3.1)),pitch:3.1,dir:'x'}],
    points:[P('bin',3,kd*0.7),P('bin',7,kd*0.7),P('sign',W*0.058,0.5,3),P('light',W*0.058,kd/2),
            P('smoke',W*0.058,kd/2)]});

  /* ٦ — الشحن والصادر */
  const od=D-b.pack1;
  [['dispatch_dhl',0,0.167],['dispatch_aramex',0.167,0.167],['dispatch_smsa',0.334,0.15]].forEach(([id,x0,fw])=>{
    const cw=W*fw, n=Math.max(2,Math.floor(cw/4.6));
    Z(id,[W*x0,b.pack1,cw,od],'dispatch',{
      lanes:[...Array(n)].map((_,j)=>({kind:'zone',x:4.6*j+0.3,z:0.3,w:4.2,d:od-0.6,dir:'z',arrow:false})),
      points:[P('sign',cw/2,0.5,2.8),P('camera',cw/2,0.8),P('smoke',cw/2,od/2)]});
  });
  Z('lastmile_lanes',[W*0.484,b.pack1,W*0.183,od],'shipping',{
    racks:[{kind:'cage',x:0.6,z:0.6,w:W*0.183-1.2,d:od-1.2,dir:'x',aisle:1.2,levels:1,h:1.8}],
    points:[P('sign',W*0.09,0.5,2.8),P('camera',W*0.09,0.8),P('smoke',W*0.09,od/2)]});
  Z('pallet_wrapping',[W*0.667,b.pack1,W*0.1,od],'shipping',{
    stations:[{kind:'wrap',x:1,z:Math.max(1,od*0.2),count:Math.max(2,Math.floor(W*0.1/3.4)),pitch:3.4,dir:'x'}],
    points:[P('sign',W*0.05,0.5,2.8),P('smoke',W*0.05,od/2),P('light',W*0.05,od/2)]});
  const nOut=Math.max(3,Math.floor(W*0.233/4.2));
  Z('outbound_docks',[W*0.767,b.pack1,W*0.233,od],'shipping',{
    docks:[{edge:'S',offset:3.5,width:3.6,height:4.2,count:nOut,pitch:4.2}],
    lanes:[{kind:'forklift',x:0.5,z:0.6,w:W*0.233-1,d:3.4,dir:'x'}],
    points:[...Array(nOut)].map((_,i)=>P('scanner',3+4.2*i,od-1))
      .concat([P('camera',W*0.116,od-0.8),P('smoke',W*0.116,od/2),P('assembly',W*0.116,od*0.7),
               P('extinguisher',W*0.22,1)])});

  return {meta:{name:`مستودع تجارة إلكترونية ${Math.round(W)}×${Math.round(D)}`,
                city:'الرياض',north:'-Z',type:'warehouse'},
          site:{w:W,d:D}, floor_height:H+1, wall_h:H, wall_t:0.25,
          levels:[{index:0,name:'صالة التشغيل',template:'ops'}],
          floors:{ops:{rooms:R}}};
}
/* ==================================================================
   مولّد صناعي **مقاد بالوصف** — لا قالب محفوظ.
   يبني فقط المناطق التي ذكرها العميل، بأعداده ومقاساته، ولا يُقحم غيرها.
   يعيد {building, coverage} حيث coverage تُظهر لكل بند أين نُفّذ.
   ================================================================== */
const ZONE_LIB=[
  // band = ترتيب تدفّق العمل من الشمال (0) للجنوب (5)
  {id:'inbound_docks',   ar:'أرصفة الاستلام',      role:'receiving',   band:0,
   re:/رصيف|أرصفة|ارصفة|dock|تحميل|تفريغ|استلام|وارد|inbound|receiv/i, kind:'dock'},
  {id:'unloading',       ar:'التفريغ السريع',       role:'receiving',   band:0,
   re:/تفريغ سريع|unload|رافعة يدوية|pallet ?jack/i, kind:'unload'},
  {id:'inbound_staging', ar:'تجهيز الوارد',         role:'receiving',   band:1,
   re:/تجهيز|staging|انتظار الوارد|فرز أولي|مرقّم|مرقم/i, kind:'staging'},
  {id:'qc_inspection',   ar:'فحص الجودة',           role:'qc',          band:1,
   re:/فحص|جودة|تفتيش|inspect|quality|qc\b|رفض/i, kind:'inspect'},
  {id:'crossdock',       ar:'كروس دوك',             role:'crossdock',   band:1,
   re:/كروس|cross ?dock|عبور مباشر/i, kind:'cross'},
  {id:'pallet_storage',  ar:'تخزين بالتات',         role:'storage',     band:2,
   re:/بالت|pallet|رفوف ثقيلة|تخزين ضخم|bulk|رفوف عالية/i, kind:'rack', rack:'pallet'},
  {id:'shelf_storage',   ar:'أرفف متوسطة',          role:'shelf',       band:2,
   re:/أرفف|ارفف|shelf|shelving|متوسط/i, kind:'rack', rack:'shelf'},
  {id:'bin_storage',     ar:'صناديق صغيرة',         role:'bin',         band:2,
   re:/صناديق|بن\b|bin |قطع صغيرة|كثافة عالية|high ?density/i, kind:'rack', rack:'bin'},
  {id:'flow_racks',      ar:'رفوف انسيابية',        role:'storage',     band:2,
   re:/انسياب|flow ?rack|جاذبية|carton ?flow/i, kind:'rack', rack:'flow'},
  {id:'cold_storage',    ar:'تخزين مبرّد',          role:'storage',     band:2,
   re:/مبرد|مبرّد|تبريد|مجمد|cold|freez|chill/i, kind:'rack', rack:'pallet', color:'#38bdf8'},
  {id:'replenishment',   ar:'ممر التعبئة',          role:'circulation', band:2,
   re:/تعبئة|replenish|إعادة تزويد|اتجاه واحد|one ?way/i, kind:'aisle'},
  {id:'batch_picking',   ar:'التقاط بالدفعات',      role:'picking',     band:3,
   re:/دفعات|batch/i, kind:'pick', rack:'shelf'},
  {id:'wave_picking',    ar:'التقاط بالموجات',      role:'wave',        band:3,
   re:/موجات|wave|pick ?to ?light|بيك تو لايت/i, kind:'pick', rack:'flow', ptl:true},
  {id:'zone_picking',    ar:'التقاط بالمناطق',      role:'zone_pick',   band:3,
   re:/التقاط بالمناطق|zone ?pick|حسب الفئة/i, kind:'pick', rack:'shelf'},
  {id:'amr_field',       ar:'مسارات الروبوت',       role:'robot',       band:3,
   re:/روبوت|robot|amr|agv|آلي ذاتي|شحن روبوت/i, kind:'amr'},
  {id:'picking',         ar:'الالتقاط',             role:'picking',     band:3,
   re:/التقاط|pick|تجميع الطلب|order pick/i, kind:'pick', rack:'bin'},
  {id:'packing',         ar:'التغليف',              role:'packing',     band:4,
   re:/تغليف|تعبئة الطلب|pack(?!et)|كرتون|تغليق/i, kind:'station', sta:'pack'},
  {id:'labeling_qa',     ar:'الملصقات والتحقّق',    role:'labeling',    band:4,
   re:/ملصق|باركود|label|barcode|طباعة/i, kind:'station', sta:'label'},
  {id:'void_fill',       ar:'حشو الفراغ',           role:'packing',     band:4,
   re:/حشو|void|وسائد هواء|ورق حشو/i, kind:'station', sta:'void'},
  {id:'consolidation',   ar:'تجميع الطلبات',        role:'consolidation',band:4,
   re:/تجميع|consolidat|دمج الطلبات/i, kind:'rack', rack:'cage'},
  {id:'auto_sorter',     ar:'الفرز الآلي',          role:'sorting',     band:4,
   re:/فرز|sort|سير|ناقل|conveyor|منزلق|chute|محوّل|diverter/i, kind:'conveyor'},
  {id:'manual_sort',     ar:'الفرز اليدوي',         role:'sorting',     band:4,
   re:/فرز يدوي|manual sort|طرود كبيرة|oversize/i, kind:'station', sta:'sort'},
  {id:'dispatch',        ar:'تجهيز الشحن',          role:'dispatch',    band:5,
   re:/شحن|ناقل|dispatch|dhl|aramex|أرامكس|سمسا|smsa|fedex|ups\b/i, kind:'staging'},
  {id:'lastmile',        ar:'الميل الأخير',         role:'shipping',    band:5,
   re:/ميل أخير|last ?mile|أقفاص|cage|طرود صغيرة/i, kind:'rack', rack:'cage'},
  {id:'wrapping',        ar:'لفّ البالتات',         role:'shipping',    band:5,
   re:/لف|لفّ|stretch|wrap|تغليف بالتات/i, kind:'station', sta:'wrap'},
  {id:'outbound_docks',  ar:'أرصفة الصادر',         role:'shipping',    band:5,
   re:/صادر|outbound|أرصفة الشحن|shipping dock/i, kind:'dock', edge:'S'},
  {id:'inventory_office',ar:'مكتب المخزون',         role:'office',      band:2, adm:true,
   re:/مكتب|office|مراقبة المخزون|إدارة/i, walls:'glass'},
  {id:'it_server_room',  ar:'غرفة السيرفرات',       role:'it',          band:2, adm:true,
   re:/سيرفر|server|wms|شبكة|it\b|داتا/i, walls:'full'},
  {id:'meeting_room',    ar:'غرفة اجتماعات',        role:'admin',       band:2, adm:true,
   re:/اجتماع|meeting|قاعة/i, walls:'glass'},
  {id:'rest_area',       ar:'استراحة الموظفين',     role:'staff',       band:2, adm:true,
   re:/استراحة|رست|break ?room|مطعم|كافي|canteen|صلاة|مصلى/i, walls:'full'},
  {id:'lockers',         ar:'خزائن الملابس',        role:'staff',       band:2, adm:true,
   re:/خزائن|locker|ملابس|تبديل/i, walls:'full'},
  {id:'maintenance',     ar:'ورشة الصيانة',         role:'maintenance', band:2, adm:true,
   re:/صيانة|ورشة|maintenance|workshop|إصلاح/i, walls:'full'},
  {id:'returns',         ar:'المرتجعات',            role:'qc',          band:1,
   re:/مرتجع|return|استرجاع|rma/i, kind:'station', sta:'inspect'},
  {id:'hazmat',          ar:'المواد الخطرة',        role:'safety',      band:2,
   re:/خطرة|hazmat|كيماوي|قابل للاشتعال/i, kind:'rack', rack:'shelf', color:'#ef4444'},
  {id:'value_added',     ar:'خدمات مضافة',          role:'packing',     band:4,
   re:/خدمات مضافة|value ?added|vas\b|تجميع منتجات|kitting/i, kind:'station', sta:'desk'}
];

/* يستخرج عدداً مذكوراً قرب كلمة (٨ أرصفة / 12 محطة تغليف / أرصفة 8) */
function numNear(txt, re){
  const m=re.exec(txt); if(!m) return null;
  const i=m.index, win=txt.slice(Math.max(0,i-28), Math.min(txt.length,i+m[0].length+28));
  const d=win.match(/(\d{1,3})/);
  if(d){ const v=+d[1]; if(v>0&&v<=400) return v; }
  for(const k in AR_NUM){ if(win.indexOf(k)>=0) return AR_NUM[k]; }
  return null;
}
/* النفي جزء من احترام الوصف: «بدون فرز» أو «لا أريد روبوت» يعني ألّا نبنيه.
   يسري النفي من موضعه حتى نهاية الجملة، فـ«أريد فرز بدون روبوت» تبني الفرز وتستبعد الروبوت. */
const NEG_RE=/بدون|بلا\s|من\s+غير|لا\s*(?:أريد|اريد|أبغى|ابغى|أبي|ابي|نريد|نحتاج|حاجة|يوجد|تضع|تضف|تحتاج)|ما\s*(?:أريد|اريد|أبغى|ابغى|أبي|ابي|نحتاج|في)|غير\s+مطلوب|ليس\s+هناك|مستثن|ألغِ|احذف|no\s|without|exclude|not\s+needed/i;
const CLAUSE_SEP=/[.\n؟?!؛;،,]/g;
function clauseMap(t){
  /* يقسّم النص لجُمَل قصيرة ويحسب بداية النفي في كل جملة،
     مع استمرار النفي إلى الجملة التالية إن بدأت بـ«ولا» (لا أريد س ولا ص). */
  const cl=[]; let s=0, m; CLAUSE_SEP.lastIndex=0;
  while((m=CLAUSE_SEP.exec(t))!==null){ cl.push([s,m.index]); s=m.index+1; }
  cl.push([s,t.length]);
  let prevNeg=false;
  return cl.map(([a,b])=>{
    const seg=t.slice(a,b);
    let n=seg.search(NEG_RE);
    if(n<0 && prevNeg && /^\s*(?:و\s*)?لا\b/.test(seg)) n=0;   // استمرار النفي
    prevNeg = n>=0;
    return {a:a, b:b, neg: n<0 ? Infinity : a+n};
  });
}
function negatedAt(cmap, idx){
  for(const c of cmap) if(idx>=c.a && idx<=c.b) return idx>=c.neg;
  return false;
}
function warehouseFromText(txt, W, D, opt){
  opt=opt||{}; const t=normDigits(stripBidi(txt||''));
  W=Math.max(20,+W||100); D=Math.max(15,+D||60);
  const found=[], excluded=[], cmap=clauseMap(t);
  for(const Zd of ZONE_LIB){
    const re=new RegExp(Zd.re.source,'ig');
    let m, positive=null, sawNeg=false;
    while((m=re.exec(t))!==null){
      if(negatedAt(cmap,m.index)) sawNeg=true; else { positive=m.index; break; }
    }
    if(positive===null){ if(sawNeg) excluded.push(Zd.ar); continue; }
    found.push(Object.assign({}, Zd, {count:numNear(t, new RegExp(Zd.re.source,'i'))}));
  }
  if(!found.length) return null;              // لا شيء معروف في الوصف → لا نفرض قالباً

  const H=Math.max(4,Math.min(+opt.clear|| (function(){
    const m=t.match(/ارتفاع\s*(?:صاف[يٍ]?|clear)?\s*(\d{1,2})/); return m?+m[1]:12; })(),18));
  const R=[], cov=[];
  const P=(k,x,z,h)=>{const o={type:k,x:+x.toFixed(2),z:+z.toFixed(2)};if(h!=null)o.height=h;return o;};
  const auto=p=>Object.assign({},p,{auto:true});

  // وزّع المناطق على الحزم التي ظهرت فقط (لا حزم فارغة)
  const adm=found.filter(f=>f.adm), ops=found.filter(f=>!f.adm);
  const bands=[...new Set(ops.map(f=>f.band))].sort((a,b)=>a-b);
  const admW=adm.length? Math.min(W*0.16, 18) : 0;
  const opsW=W-admW;
  const bandH=D/(bands.length||1);

  bands.forEach((b,bi)=>{
    const list=ops.filter(f=>f.band===b);
    const z0=bi*bandH, hz=bandH;
    let x=0;
    list.forEach((f,fi)=>{
      const w=opsW/list.length, rect=[x,z0,w,hz]; x+=w;
      const ex={points:[]}, half=[w/2,hz/2];
      if(f.color) ex.wall_color=f.color;
      if(f.kind==='dock'){
        const n=f.count||Math.max(2,Math.floor(w/6.2));
        ex.docks=[{edge:f.edge||'N',offset:Math.min(4.5,w/4),width:3.6,height:4.2,
                   count:Math.min(n,Math.max(1,Math.floor(w/4.2))),pitch:Math.max(4.2,w/(n+0.5))}];
        ex.lanes=[{kind:'forklift',x:0.5,z:hz-4,w:Math.max(3,w-1),d:3.4,dir:'x'}];
        for(let i=0;i<Math.min(n,10);i++) ex.points.push(P('scanner',Math.min(3+6.2*i,w-1),1.2));
        cov.push({req:f.ar+(f.count?(' ('+f.count+')'):''),where:f.id,how:'أرصفة بمسويات ومصدّات وممر رافعات'});
      }else if(f.kind==='rack'){
        const RD={pallet:[3.4,4,Math.min(H-3,9)],shelf:[1.6,5,2.6],bin:[1.2,6,2.2],
                  flow:[1.8,4,2.4],cage:[1.2,2,2.0]}[f.rack]||[1.6,4,2.4];
        ex.racks=[{kind:f.rack,x:0.6,z:0.6,w:Math.max(1,w-1.2),d:Math.max(1,hz-1.2),
                   dir:'x',aisle:RD[0],levels:f.count&&f.count<=10?f.count:RD[1],h:RD[2]}];
        ex.points.push(P('sign',half[0],0.8,3.2));
        cov.push({req:f.ar+(f.count?(' — '+f.count+' مستويات'):''),where:f.id,
                  how:'صفوف رفوف '+f.rack+' بممر '+RD[0]+' م'});
      }else if(f.kind==='pick'){
        ex.racks=[{kind:f.rack||'shelf',x:0.6,z:0.6,w:Math.max(1,w-1.2),d:Math.max(1,hz*0.55),
                   dir:'x',aisle:1.5,levels:4,h:2.3}];
        ex.lanes=[{kind:'pedestrian',x:0.4,z:hz*0.68,w:Math.max(2,w-0.8),d:Math.max(1.2,hz*0.16),dir:'x'}];
        if(f.ptl) for(let i=0;i<Math.min(Math.floor(w/1.6),24);i++) ex.points.push(P('ptl',1.6*i+1,1.2));
        ex.points.push(P('sign',half[0],0.6,3));
        cov.push({req:f.ar,where:f.id,how:'رفوف التقاط + ممر مشاة'+(f.ptl?' + pick-to-light':'')});
      }else if(f.kind==='amr'){
        const n=Math.max(2,Math.min(f.count||3,6));
        ex.lanes=[]; for(let i=0;i<n;i++) ex.lanes.push({kind:'amr',x:0.5,z:hz*(i+0.5)/(n+0.6),
          w:Math.max(2,w-1),d:1.4,dir:'x',reverse:i%2===1});
        ex.stations=[{kind:'charger',x:1,z:hz-1.2,count:Math.max(2,Math.floor(w/2)),pitch:2,dir:'x'}];
        ex.points.push(P('robot',w*0.3,hz*0.3),P('estop',Math.max(0.6,w-0.6),hz/2));
        cov.push({req:f.ar+(f.count?(' — '+f.count+' مسارات'):''),where:f.id,how:n+' مسارات AMR + محطات شحن'});
      }else if(f.kind==='conveyor'){
        ex.lanes=[{kind:'conveyor',x:1,z:hz*0.2,w:Math.max(2,w-2),d:1,dir:'x',h:0.95},
                  {kind:'conveyor',x:1,z:hz*0.55,w:Math.max(2,w-2),d:1,dir:'x',h:0.85},
                  {kind:'pedestrian',x:0.5,z:hz*0.85,w:Math.max(2,w-1),d:1.4,dir:'x'}];
        const nd=Math.max(2,Math.min(f.count||Math.floor(w/3),16));
        for(let i=0;i<nd;i++){ ex.points.push(P('diverter',Math.min(3+3*i,w-1),hz*0.35));
                               ex.points.push(P('chute',Math.min(3+3*i,w-1),hz*0.72)); }
        cov.push({req:f.ar+(f.count?(' — '+f.count+' مخارج'):''),where:f.id,
                  how:'سيور بحواجز وإيقاف طوارئ + محوّلات ومنزلقات'});
      }else if(f.kind==='station'){
        const n=f.count||Math.max(2,Math.floor(w/2.7));
        ex.stations=[{kind:f.sta,x:1,z:1,count:Math.min(n,Math.max(1,Math.floor(w/2))),
                      pitch:Math.max(1.8,Math.min(2.7,(w-2)/Math.max(n,1))),dir:'x'}];
        if(f.sta==='pack'){ for(let i=0;i<Math.min(n,14);i++) ex.points.push(P('scale',Math.min(2.4+2.7*i,w-1),hz*0.4)); }
        if(f.sta==='label'){ for(let i=0;i<Math.min(n,14);i++) ex.points.push(P('scanner',Math.min(2+2*i,w-1),hz*0.4)); }
        ex.points.push(P('sign',half[0],0.5,3));
        cov.push({req:f.ar+(f.count?(' — '+f.count+' محطة'):''),where:f.id,how:n+' محطة '+f.sta});
      }else if(f.kind==='aisle'){
        ex.lanes=[{kind:'one_way',x:0.4,z:Math.max(0.4,hz*0.25),w:Math.max(3,w-0.8),
                   d:Math.max(3.2,hz*0.5),dir:'x'}];
        cov.push({req:f.ar,where:f.id,how:'ممر باتجاه واحد بأسهم أرضية'});
      }else if(f.kind==='staging'){
        const n=f.count||Math.max(3,Math.floor(w/5));
        ex.lanes=[]; for(let i=0;i<Math.min(n,20);i++)
          ex.lanes.push({kind:'zone',x:(w/Math.min(n,20))*i+0.3,z:0.3,
                         w:Math.max(1,w/Math.min(n,20)-0.6),d:Math.max(1,hz-0.6),dir:'z',arrow:false});
        ex.points.push(P('sign',half[0],0.5,2.8));
        cov.push({req:f.ar+(f.count?(' — '+f.count+' مسار'):''),where:f.id,how:'مسارات مرقّمة بدهان أرضي'});
      }else if(f.kind==='inspect'||f.kind==='unload'){
        ex.stations=[{kind:'inspect',x:1,z:1,count:Math.max(2,Math.floor(w/4)),pitch:4,dir:'x'}];
        ex.points.push(P('scale',half[0],hz*0.5),P('sign',half[0],0.5,3));
        cov.push({req:f.ar,where:f.id,how:'محطات فحص بموازين وماسحات'});
      }else if(f.kind==='cross'){
        ex.lanes=[{kind:'conveyor',x:1,z:hz*0.45,w:Math.max(2,w-2),d:0.9,dir:'x',h:0.9},
                  {kind:'forklift',x:0.5,z:hz-4,w:Math.max(3,w-1),d:3.4,dir:'x'}];
        cov.push({req:f.ar,where:f.id,how:'سير عبور مباشر + ممر رافعات'});
      }
      R.push(Object.assign({id:f.id,rect:rect.map(v=>+v.toFixed(2)),role:f.role,walls:'none'},ex));
    });
  });

  // العمود الإداري: فقط إن ذُكر
  if(adm.length){
    const hz=D/adm.length;
    adm.forEach((f,i)=>{
      const rect=[W-admW,i*hz,admW,hz];
      const ex={walls:f.walls||'full',wall_h:Math.min(3.2,H),
        doors:[{edge:'W',offset:hz/2,width:1.0,height:2.1,material:f.walls==='glass'?'glass':'wood'}],
        points:[P('light',admW/2,hz/2),P('smoke',admW/2,hz/2),P('ac',admW/2,0.4),
                P('outlet',1.5,hz-0.4,0.40),P('switch',admW*0.3,hz-0.6,1.20)]};
      if(f.id==='it_server_room') ex.points.push(P('server',2,1),P('server',4,1),P('network',1,hz/2,0.40));
      if(f.id==='lockers') ex.stations=[{kind:'locker',x:0.6,z:0.4,count:Math.max(3,Math.floor(admW/0.98)),pitch:0.98,dir:'x'}];
      if(f.id==='meeting_room') ex.furniture=[{name:'table',x:admW/2,z:hz/2,w:Math.min(3.4,admW*0.6),d:1.3,h:0.75,mat:'furn'}];
      if(f.id==='inventory_office'){ ex.stations=[{kind:'desk',x:1,z:1,count:Math.max(2,Math.floor(admW/2.6)),pitch:2.6,dir:'x'}];
        ex.windows=[{edge:'W',offset:hz*0.8,width:Math.min(3,hz*0.35),sill:0.9,height:1.6}]; }
      R.push(Object.assign({id:f.id,rect:rect.map(v=>+v.toFixed(2)),role:f.role},ex));
      cov.push({req:f.ar,where:f.id,how:'غرفة مغلقة'+(f.walls==='glass'?' بزجاج مطلّ':'')+' بإنارة وتكييف وأفياش'});
    });
  }

  // الغلاف + السلامة: إضافات كود موسومة auto (لا تُنقص من طلب العميل)
  const added=[];
  if(!opt.strict){
    const shell=[];
    const nc=Math.max(4,Math.round(W/28));
    for(let i=0;i<nc;i++){const x=W*(i+0.5)/nc; shell.push(auto(P('camera',x,1)),auto(P('camera',x,D-1)));}
    const ne=Math.max(6,Math.round(W/14));
    for(let i=0;i<ne;i++){const x=W*(i+0.5)/ne; shell.push(auto(P('extinguisher',x,0.6)),auto(P('extinguisher',x,D-0.6)));}
    shell.push(auto(P('exit',2,0.4,2.4)),auto(P('exit',W-2,0.4,2.4)),auto(P('exit',2,D-0.4,2.4)),
      auto(P('exit',W-2,D-0.4,2.4)),auto(P('assembly',W*0.5,D-2)),
      auto(P('hydrant',0.6,D*0.5)),auto(P('hydrant',W-0.6,D*0.5)));
    R.unshift({id:'envelope',rect:[0,0,W,D],walls:'full',wall_h:H,points:shell});
    // صياغة صادقة: هذه إعدادات افتراضية للمولّد، لا نتيجة تحقّق مطابقة لكود
    added.push('غلاف المبنى وجدرانه الخارجية','مخارج طوارئ وطفايات وحنفيات ونقطة تجمّع (إعداد افتراضي للنظام)',
               'كاميرات محيطية');
  }

  return {building:{
    meta:{name:'منشأة حسب وصف العميل', city:'الرياض', north:'-Z', type:'warehouse',
          requirements:cov, added:added, excluded:excluded,
          strict:!!opt.strict, source:'local-from-text'},
    site:{w:W,d:D}, floor_height:H+1, wall_h:H, wall_t:0.25,
    levels:[{index:0,name:'صالة التشغيل',template:'ops'}],
    floors:{ops:{rooms:R}}}, coverage:cov, added:added, excluded:excluded};
}

/* ==================================================================
   استخراج العناصر المطلوبة من نص العميل — للمسار المحلي (بلا خادم).
   يملأ room.objects بنفس صيغة مسار الذكاء تماماً، فلا يُسقَط بشر أو
   روبوتات أو رافعات صامتةً حين يكون محرّك الفهم غير متاح. يحترم النفي
   (لا/بدون)، ويعدّ الأرقام (١٢٣) وكلمات العدد (ستة) والمثنّى (روبوتين=٢).
   ملاحظة: هذا ليس «إضافة كائنات وهمية» — بل قراءة طلب العميل الفعلي
   وتحويله إلى بيانات العناصر التي يرسمها buildObjects أصلاً.
   ================================================================== */
const OBJ_KIND_AR = {  // kind -> تسمية عربية للتقرير
  person:'أشخاص', worker:'عمّال', visitor:'زوّار', engineer:'مهندسون', child:'أطفال',
  robot:'روبوتات', amr:'روبوتات AMR', cobot:'كوبوت', forklift:'رافعات شوكية',
  reachtruck:'رافعات', car:'سيارات', van:'فان', truck:'شاحنات', trailer:'مقطورات',
  stairs:'درج', elevator:'مصاعد', column:'أعمدة', railing:'درابزين', tree:'أشجار',
  palm:'نخيل', plant:'نباتات', sofa:'كنب', bed:'أسِرّة', table:'طاولات', desk:'مكاتب',
  chair:'كراسي', wardrobe:'خزائن', fridge:'ثلاجات', oven:'أفران', washer:'غسّالات',
  sink:'مغاسل', toilet:'مراحيض', bath:'أحواض', tv:'شاشات', shelf:'رفوف', pallet:'بالتات' };
/* المثنّى العربي: عاملين/روبوتين/سيارتين → ٢ */
function _dualCount(w){ return /(?:ين|ان|تين)$/.test(w) ? 2 : 1; }
/* التخصّص: النوع الخاص «يبتلع» الأب العامّ المجاور (روبوتين AMR → ٢ AMR لا ٢+١) */
const OBJ_PARENT = {amr:'robot', cobot:'robot', reachtruck:'forklift',
  trailer:'truck', van:'car', bed_single:'bed', dining:'table', desk:'table', armchair:'sofa'};
/* جموع تكسير وصيغ شائعة لا يلتقطها اشتقاق المفرد+لاحقة */
const OBJ_SYN_EXTRA = {
  'عمال':'worker','عمّال':'worker','عمالة':'worker','موظفون':'worker','موظفين':'worker',
  'مصاعد':'elevator','رافعات':'forklift','روبوتات':'robot','ربوتات':'robot',
  'شاحنات':'truck','مهندسون':'engineer','مهندسين':'engineer','زوار':'visitor','زوّار':'visitor',
  'كراسي':'chair','طاولات':'table','مكاتب':'desk','خزائن':'wardrobe','ثلاجات':'fridge',
  'شاشات':'tv','أسرّة':'bed','أسرة':'bed','مغاسل':'sink','مراحيض':'toilet','رفوف':'shelf'};
const _OBJ_ALL_KEYS = [
  ...Object.keys(OBJ_AR).map(k=>({key:k, kind:OBJ_AR[k]})),
  ...Object.keys(OBJ_SYN_EXTRA).map(k=>({key:k, kind:OBJ_SYN_EXTRA[k]})),
  ...Object.keys(OBJ_LIB).map(k=>({key:k, kind:k}))
].sort((a,b)=>b.key.length-a.key.length);
function objectsFromText(txt){
  const t = normDigits(stripBidi(txt||''));
  const tl = t.toLowerCase();                 // مطابقة حروف لاتينية بلا حساسية لحالة الأحرف (AMR)
  const cmap = clauseMap(t);
  const matches = [], excluded = [], covered = [];
  for(const ent of _OBJ_ALL_KEYS){
    // المؤنّث المنتهي بـ«ة»: الجمع/المثنّى يبدّل الـة تاءً (سيارة→سيارتان/سيارات، رافعة→رافعتان)
    const fem = /ة$/.test(ent.key);
    const stem = fem ? ent.key.slice(0,-1) : ent.key;
    const esc = stem.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const suf = fem ? '(?:ة|ه|ات|تان|تين|تي)?' : '(?:ة|ه|ات|ين|ان|تين|ي)?';
    const re = new RegExp('(^|[^'+_AL+'\\w])((?:ال|بال|لل|وال|و|ب|ل)?'+esc+suf+
                          ')([^'+_AL+'\\w]|$)','g');
    let m;
    while((m=re.exec(tl))!==null){
      const at = m.index + m[1].length, word = m[2];
      if(covered.some(c=> at < c[1] && at+word.length > c[0])) continue;  // موضع مُستهلَك
      covered.push([at, at+word.length]);
      if(negatedAt(cmap, at)){ if(!excluded.includes(ent.key)) excluded.push(ent.key); continue; }
      /* العدّ بالمجاورة: رقم/كلمة عدد ملاصقة قبل الاسم (ستة عمال)، أو رقم بعده،
         أو المثنّى (روبوتين=٢)، وإلا ١ — بلا التقاط رقم يخصّ عنصراً آخر. */
      const before = t.slice(Math.max(0,at-12), at);
      const after  = t.slice(at+word.length, at+word.length+12);
      let n=null, mb=before.match(/(\d{1,3})\s*$/);
      if(mb){ const v=+mb[1]; if(v>0&&v<=200) n=v; }
      if(n==null){ const bw=(before.trim().split(/\s+/).pop()||'');
        const bw2=bw.replace(/^(?:و|ف|ب|ل)/,'');
        if(AR_NUM[bw]!=null) n=AR_NUM[bw]; else if(AR_NUM[bw2]!=null) n=AR_NUM[bw2]; }
      if(n==null){ const ma=after.match(/^\s*(\d{1,3})/); if(ma){ const v=+ma[1]; if(v>0&&v<=200) n=v; } }
      if(n==null) n=_dualCount(word);
      matches.push({kind:ent.kind, at:at, count:n});
    }
  }
  // دمج النوع الخاص مع أبيه العامّ المجاور (≤14 حرفاً)
  for(const sp of matches){
    const par = OBJ_PARENT[sp.kind]; if(!par) continue;
    for(const g of matches){
      if(g!==sp && g.kind===par && Math.abs(g.at-sp.at)<=14){
        sp.count = Math.max(sp.count, g.count); g._drop = true;
      }
    }
  }
  const acc = {};
  for(const mm of matches){ if(mm._drop) continue;
    if(!acc[mm.kind]) acc[mm.kind]={kind:mm.kind, count:0};
    acc[mm.kind].count += mm.count; }
  const objects = Object.values(acc).map(o=>({kind:o.kind, count:o.count, dir:'x',
    pitch:(OBJ_LIB[o.kind]?OBJ_LIB[o.kind][0]:0.6)+1.2}));
  return {objects, excluded};
}
/* يثبّت تقرير التغطية داخل building.meta ليحمله تصدير JSON (لا يقتصر على مسار المستودع).
   يحافظ على تمايز الفئات: requirements(طُلب ونُفِّذ) · excluded(مُستبعَد) · added(أُضيف تلقائياً) ·
   extras(مُثِّل بطريقة بديلة — من مسار الذكاء). */
function stampMeta(building, type, requirements, excluded, added){
  if(!building) return building;
  const M = building.meta = building.meta || {};
  if(!M.type) M.type = type || 'unknown';
  if(!M.source) M.source = 'local';
  M.requirements = (M.requirements||[]).concat(requirements||[]);
  M.excluded     = (M.excluded||[]).concat(excluded||[]);
  M.added        = (M.added||[]).concat(added||[]);
  if(!('extras' in M)) M.extras = M.extras || [];
  return building;
}
/* ==================================================================
   طبقة المصدر (Provenance) لتقرير التغطية — لا يدّعي التقرير أكثر مما تُثبته
   البيانات. يفصل: طلب المستخدم · استنتاج · إضافة تلقائية من النظام · مطلوب
   بقاعدة موثّقة (بدليل فقط) · تمثيل بديل · غير مدعوم · مستبعَد.
   لا يغيّر النموذج الداخلي ولا الهندسة — يصحّح دلالات التقرير فقط.
   عام لكل أنواع المشاريع (سكني/فندقي/صحي/تعليمي/مكتبي/صناعي…).
   ================================================================== */
const PROV = {USER:'user', AI:'ai_inference', SYSTEM:'system_default',
              AUTO:'autofix', RULE:'rule'};
__ACS_SHARED.LAST_REQUEST_TEXT = '';        // نص طلب المستخدم الأخير (للتحقّق من الادّعاءات)

/* CODE_REQUIRED لا يُسمح به إلا بدليل قاعدة نُفِّذت فعلاً، ولا يكفي وجود الحقول:
   يجب أن تكون القاعدة محمّلة في سجلّ القواعد، تنظيمية، مصدرها موثّق، وتعريفها صالح.
   القواعد الاصطناعية (TEST_ONLY) لا تُنتج CODE_REQUIRED إطلاقاً. */
__ACS_SHARED.ACS_EXTRA_RULESETS = [];
/* مخزن الاستيراد وسياق أكواد المشروع — يبدآن بالتجهيزات الاصطناعية وبلا أي تفعيل */
__ACS_SHARED.ACS_INGEST_STORE = {documents:[],fragments:[],candidates:[],rulepacks:[]};
let ACS_PROJECT_CODE_CONTEXT = {jurisdiction:null, rulepacks:[],
  code_context:{standard:null, edition:null, rulepacks:[], classification_packs:[]},
  occupancy:{status:'UNCLASSIFIED', classifications:[]}};
__ACS_SHARED.ACS_OCCUPANCY_STORE = {classifications:[], packs:[]};
function hasRuleEvidence(it){
  if(!(it && it.rule_id && it.standard && it.condition && it.result)) return false;
  if(typeof __ACS_LATE.codeRequiredAllowed!=='function') return false;
  return __ACS_LATE.codeRequiredAllowed(it.rule_id, __ACS_SHARED.ACS_EXTRA_RULESETS);
}
/* عبارات تدّعي مطابقة كود أو تحقّقاً هندسياً لم يحدث */
const CLAIM_RE = /\(?\s*(?:متطلّب|متطلب|مطلوب)\s*(?:نظام\s*\/?\s*)?كود\s*\)?|وفق\s+الكود|حسب\s+الكود|مطابق\s+للكود|متوافق\s+مع\s+الكود|مطلوب\s+نظامي(?:اً|ا)?|code[- ]?compliant|code[- ]?required|تم\s+التحقق\s+هندسي(?:اً|ا)?|إصلاح\s*:/gi;
/* وجود مجسّم درج/مصعد لا يُثبت ربطاً رأسياً مُتحقَّقاً منه */
const CONNECT_RE = /يربط\s+(?:بين\s+)?(?:الطوابق|الأدوار|الادوار)|يصل\s+بين\s+(?:الأدوار|الادوار|الطوابق)|vertical\s+connectivity/gi;
function truthify(s){
  return String(s==null?'':s)
    .replace(CLAIM_RE,'')
    .replace(CONNECT_RE,'مُمثَّل بصرياً على المستويات المعنيّة (لم يُتحقَّق من الربط الرأسي)')
    .replace(/\s{2,}/g,' ').replace(/^[\s،:—-]+/,'').trim();
}
/* الأعداد التي ذكرها العميل فعلاً (أرقام + كلمات عدد + مثنّى) */
function statedNumbers(t){
  const s=new Set(), x=normDigits(stripBidi(t||''));
  (x.match(/\d{1,4}/g)||[]).forEach(n=>s.add(+n));
  for(const k in AR_NUM) if(x.indexOf(k)>=0) s.add(AR_NUM[k]);
  if(/(?:ين|ان|تين)(?:[^ء-ي\w]|$)/.test(x)) s.add(2);
  return s;
}
/* عدد الأدوار الذي ذكره العميل صراحةً — عامّ لكل أنواع المباني */
function requestedFloorsFromText(t){
  const x=normDigits(stripBidi(t||''));
  let m=x.match(/(\d{1,3})\s*(?:أدوار|ادوار|طوابق|دور|طابق)/);
  if(m) return +m[1];
  m=x.match(/([ء-ي]+)\s+(?:أدوار|ادوار|طوابق)/);
  if(m&&AR_NUM[m[1]]!=null) return AR_NUM[m[1]];
  if(/دورين|طابقين|دوران|طابقان/.test(x)) return 2;
  if(/دور\s*واحد|طابق\s*واحد/.test(x)) return 1;
  return null;
}
/* يصنّف بنود التقرير حسب مصدرها الفعلي — لا يرفع شيئاً إلى «طلب المستخدم» بلا إثبات */
function classifyReport(rep, userText){
  const out={user:[],ai:[],system:[],rule:[],alt:[],unsupported:[],excluded:[],floors:null};
  const nums=statedNumbers(userText), uf=requestedFloorsFromText(userText);
  out.floors={requested:uf};
  ((rep&&rep.requirements)||[]).forEach(r=>{
    const it={req:truthify(r.req), where:r.where||'', how:truthify(r.how||''),
              source:r.source||null, rule_id:r.rule_id, standard:r.standard,
              condition:r.condition, result:r.result};
    if(hasRuleEvidence(it)){ it.source=PROV.RULE; out.rule.push(it); return; }
    // ادّعاء عدد الأدوار يُقارَن بما ذكره العميل (المستويات التقنية ليست طلباً)
    const fm=String(it.req).match(/(?:عدد\s*)?(?:الأدوار|الادوار|الطوابق|floors?)\D{0,8}(\d{1,3})/i);
    if(fm && uf!=null && +fm[1]!==uf){
      it.req='عدد المستويات في النموذج: '+fm[1]+' — طلب المستخدم: '+uf
            +' (المستويات الإضافية أضافها النظام)';
      it.source=PROV.SYSTEM; out.system.push(it); return;
    }
    if(it.source===PROV.SYSTEM||it.source===PROV.AUTO){ out.system.push(it); return; }
    if(it.source===PROV.AI){ out.ai.push(it); return; }
    // كل رقم في البند يجب أن يكون مذكوراً في نص العميل، وإلا فهو استنتاج لا طلب
    const claimed=(String(it.req).match(/\d{1,4}/g)||[]).map(Number);
    if(it.source===PROV.USER || claimed.every(n=>nums.has(n))){ it.source=PROV.USER; out.user.push(it); }
    else { it.source=PROV.AI; out.ai.push(it); }
  });
  ((rep&&rep.extras)||[]).forEach(t=>out.alt.push(truthify(t)));
  ((rep&&rep.unsupported)||[]).forEach(t=>out.unsupported.push(truthify(t)));
  ((rep&&rep.excluded)||[]).forEach(t=>out.excluded.push(String(t)));
  ((rep&&rep.added)||[]).forEach(t=>{
    if(t && typeof t==='object'){ const o=Object.assign({},t,{req:truthify(t.req||t.item||'')});
      if(hasRuleEvidence(o)){ o.source=PROV.RULE; out.rule.push(o); } else { o.source=o.source||PROV.SYSTEM; out.system.push(o); }
      return; }
    out.system.push({req:truthify(t), source:PROV.SYSTEM});
  });
  return out;
}
/* بنود التقرير للعناصر المُمثَّلة */
function objCoverage(objects){
  // مصدرها نص العميل مباشرةً ⇒ source=user (إثبات مصدر، لا ادّعاء مطابقة كود)
  return (objects||[]).map(o=>({
    req:(o.count>1?o.count+' ':'')+(OBJ_KIND_AR[o.kind]||o.kind),
    where:'المشهد', how:'مُثِّل كمجسّم ثلاثي الأبعاد بأبعاده وعدده', source:PROV.USER}));
}
/* يُرفق العناصر بأكبر غرفة في أوّل مستوى يحوي غرفاً (تُرسَم عبر buildObjects) */
function attachObjects(building, objects){
  if(!objects || !objects.length || !building) return;
  const floors = building.floors||{};
  let host=null, hostArea=-1;
  for(const lv of (building.levels||[])){
    const rooms=(floors[lv.template]||{}).rooms||[];
    for(const r of rooms){ if(!r.rect) continue;
      const a=r.rect[2]*r.rect[3]; if(a>hostArea){ hostArea=a; host=r; } }
    if(host) break;                       // أوّل مستوى فيه غرف
  }
  if(!host){ return; }
  host.objects = host.objects || [];
  const rd = host.rect[3]; let z = Math.min(2, rd*0.2);
  objects.forEach(o=>{
    host.objects.push(Object.assign({}, o, {x:1.5, z:+Math.min(z, Math.max(1,rd-1)).toFixed(2)}));
    z += 2.4; if(z > rd-1) z = Math.min(2, rd*0.2);
  });
}

/* ==================================================================
   المرحلة 2 — أساس: طبقة المشروع PROJECT → SITE → BUILDINGS → FLOORS → SPACES.
   مُحوِّل إضافي بالكامل: نموذج المرحلة 1 (site/levels/floors) يبقى كما هو
   ويصبح عقدة مبنى داخل المشروع — بلا كسر ولا فقدان بيانات.
   الإحداثيات (كما هي منذ المرحلة 1): X عرض شرق-غرب · Z عمق شمال-جنوب (z=0 شمال)
   · Y ارتفاع لأعلى · متر · منسوب الدور = index × floor_height
   · موضع المبنى داخل الموقع: position{x,z,rotation°}
   ================================================================== */
const ACS_PROJECT_SCHEMA='acs.project/1';
function isProjectModel(o){ return !!(o && typeof o==='object' && o.project && typeof o.project==='object'); }
function isBuildingModel(o){ return !!(o && typeof o==='object' && !isProjectModel(o) && o.floors && typeof o.floors==='object'); }
function ensureElementIds(b, bid){
  const fh=+(b.floor_height||((+b.wall_h||3)+0.2));
  (b.levels||[]).forEach(l=>{ const i=+(l.index||0);
    if(l.id==null) l.id=bid+'.flr_'+i;
    if(l.elevation==null) l.elevation=+(i*fh).toFixed(3); });
  Object.keys(b.floors||{}).forEach(tm=>{
    ((b.floors[tm]||{}).rooms||[]).forEach((r,i)=>{
      if(r.space_id==null) r.space_id=bid+'.'+tm+'.'+(r.id||('sp_'+i)); }); });
  return b;
}
/* يلفّ مبنى المرحلة 1 في مشروع (أو يعيد المشروع كما هو) */
function toProject(data, name){
  if(isProjectModel(data)) return data;
  if(!isBuildingModel(data)) return null;
  const meta=data.meta||{}, bt=String(meta.type||'residential').toLowerCase(), bid='bld_0';
  ensureElementIds(data,bid);
  const site=Object.assign({}, data.site||{w:30,d:25});
  if(site.id==null) site.id='site_0';
  if(site.units==null) site.units='m';
  if(site.north==null) site.north=meta.north||'-Z';
  if(site.origin==null) site.origin={x:0,y:0,z:0};
  return {schema:ACS_PROJECT_SCHEMA, project:{
    id:'prj_0', name:name||meta.name||'مشروع', site:site,
    buildings:[{id:bid, name:meta.name||'مبنى 1', building_type:bt, programs:[bt],
      position:{x:0,z:0,rotation:0}, active:true, building:data}],
    meta:{created_from:'phase1_building'}}};
}
/* يعيد عقدة المبنى بصيغة المرحلة 1 (يستهلكها العارض/المصدّر بلا تغيير) */
function activeBuilding(data){
  if(isBuildingModel(data)) return data;
  if(!isProjectModel(data)) return null;
  const bs=(data.project.buildings)||[];
  const a=bs.find(b=>b.active&&b.building)||bs[0];
  return a?a.building:null;
}
/* غلاف تصدير: هرمية المشروع + حقول المرحلة 1 في مكانها (توافق كامل للخلف) */
function projectEnvelope(b){
  const pr=toProject(b); if(!pr) return b;
  const bt=String((b.meta||{}).type||'residential').toLowerCase();
  const env=Object.assign({}, b);                       // كل حقول المرحلة 1 كما هي
  env.schema=ACS_PROJECT_SCHEMA;
  env.project={ id:pr.project.id, name:pr.project.name, site:pr.project.site,
    buildings:[{ id:'bld_0', name:(b.meta||{}).name||'مبنى 1', building_type:bt,
      programs:[bt], space_categories:__ACS_LATE.spaceCategories(bt),
      position:{x:0,z:0,rotation:0}, active:true, self:true }],
    meta:{created_from:'phase1_building',
          note:'حقول المبنى النشط في جذر الملف نفسه (توافق مع مستهلكي المرحلة 1)'}};
  // طبقة العلاقات (إضافية بالكامل) — قد تكون فارغة إن لم تُثبِتها البيانات
  try{
    env.relationships = buildRelationships(b,'bld_0');
    env.project.relationships = buildProjectRelationships(pr);
  }catch(e){ env.relationships=[]; env.project.relationships=[]; }
  /* النموذج الإنشائي المصرَّف يُصدَّر إضافةً ولا يستبدل أي تمثيل معماري.
     احتياطات العرض لا تُصدَّر كبيانات إنشائية: كل عنصر يحمل مصدره. */
  try{
    if(b.structural){ env.structural = b.structural;            // كما ورد، بلا تعديل
      env.structural_compiled = __ACS_LATE.compileStructure(b,'bld_0'); }
  }catch(e){ }
  /* نموذج MEP المصرَّف يُصدَّر إضافةً ولا يستبدل أي تمثيل معماري أو إنشائي.
     احتياطات العرض لا تُصدَّر كبيانات هندسية: كل عنصر يحمل مصدره. */
  try{
    if(b.mep){ env.mep = b.mep;                                 // كما ورد، بلا تعديل
      env.mep_compiled = __ACS_LATE.compileMep(b,'bld_0'); }
  }catch(e){ }
  /* نموذج الحريق وسلامة الأرواح يُصدَّر إضافةً ولا يستبدل أي تمثيل آخر،
     ولا يُصدَّر احتياط عرض كبيانات هندسية. */
  try{
    if(b.fire_life_safety){ env.fire_life_safety = b.fire_life_safety;
      env.fire_life_safety_compiled = __ACS_LATE.compileFls(b,'bld_0'); }
  }catch(e){ }
  return env;
}
/* ==================================================================
   المرحلة 2 — طبقة العلاقات العامة (Relationships Graph).
   رسم بياني عام يمثّل ارتباط الفراغات والمستويات — لكل أنواع المباني.
   لا إخلاء · لا حريق · لا MEP · لا إنشائي · لا إتاحة · لا مطابقة أكواد ·
   لا إيجاد مسارات. حواف بيانات فقط.
   مبدأ حاكم: وجود مجسّم لا يُثبت اتصالاً — الباب المجهول مقابله يبقى
   "unresolved"، والدرج على مستوى واحد لا يُنشئ حافة رأسية. ولا نُصدر أرقام ثقة.
   (نسخة مطابقة لـ acs_relations.py — يفرض التطابقَ اختبارُ التكافؤ.)
   ================================================================== */
const REL_TOUCH_EPS=0.02, REL_ADJ_TOL=0.20, REL_DOOR_PROBE=0.15, REL_CORE_TOL=1.50;
const REL_TYPES=['SPACE_ADJACENT','SPACE_CONNECTED','DOOR_CONNECTS','VERTICAL_CONNECTS','LEVEL_CONNECTS','BUILDING_ON_SITE'];
const REL_SOURCES=['user','ai_inference','system_generated','geometry_inference','rule'];
const REL_STATUSES=['confirmed','inferred','unresolved'];
function _relKind(o){
  const raw=String(o.kind||o.name||'').trim().toLowerCase();
  if(['elevator','lift','مصعد'].some(w=>raw.indexOf(w)>=0)) return 'elevator';
  if(['stairs','stair','درج','سلم','staircase'].some(w=>raw.indexOf(w)>=0)) return 'stairs';
  return null;
}
function _relRect(r){ const a=(r.rect||[]).slice(0,4).map(Number);
  return (a.length===4&&a.every(v=>isFinite(v)))?a:null; }
function _relContains(a,b){ return (a[0]-0.01<=b[0] && a[1]-0.01<=b[1] &&
  a[0]+a[2]+0.01>=b[0]+b[2] && a[1]+a[3]+0.01>=b[1]+b[3] && (a[2]*a[3])>(b[2]*b[3])); }
function _relSpaceId(bid,tmpl,room,i){ return room.space_id||(bid+'.'+tmpl+'.'+(room.id||('sp_'+i))); }
function _relGapOverlap(a,b){
  const ox=Math.min(a[0]+a[2],b[0]+b[2])-Math.max(a[0],b[0]);
  const oz=Math.min(a[1]+a[3],b[1]+b[3])-Math.max(a[1],b[1]);
  let bestGap=null,bestOv=0;
  if(oz>REL_TOUCH_EPS) for(const g of [Math.abs(b[0]-(a[0]+a[2])),Math.abs(a[0]-(b[0]+b[2]))])
    if(bestGap===null||g<bestGap){bestGap=g;bestOv=oz;}
  if(ox>REL_TOUCH_EPS) for(const g of [Math.abs(b[1]-(a[1]+a[3])),Math.abs(a[1]-(b[1]+b[3]))])
    if(bestGap===null||g<bestGap){bestGap=g;bestOv=ox;}
  return [bestGap,bestOv];
}
function _relLevelsFor(b,tmpl){ return (b.levels||[]).filter(l=>l.template===tmpl)
  .map(l=>+(l.index||0)).sort((x,y)=>x-y); }
function _relLevelId(b,bid,idx){ const l=(b.levels||[]).find(l=>+(l.index||0)===idx);
  return (l&&l.id)||(bid+'.flr_'+idx); }
/* يبني حواف العلاقات لمبنى واحد — لا يعدّل الهندسة ولا يضيف عنصراً */
function buildRelationships(building,bid){
  bid=bid||'bld_0'; const rels=[]; let seq=0;
  const add=(t,frm,to,source,status,via,meta)=>{ seq++;
    const e={id:bid+'.rel_'+seq,type:t,from:frm,to:to,source:source,status:status};
    if(via!==undefined&&via!==null) e.via=via;
    if(meta) e.meta=meta; rels.push(e); return e; };
  const floors=building.floors||{};
  /* دليل معماري اختياري: إن أمكن تصريف الهندسة، فالباب المستضاف على جدار يفصل
     فراغين بالضبط يرفع الحافة من inferred إلى confirmed. غيابه لا يخفض شيئاً
     ولا يحذف حافة — الاستنتاج الهندسي القديم يبقى كما هو. */
  let _arch=null;
  try{ _arch=__ACS_LATE.compileArchitecture(building,bid); }catch(e){ _arch=null; }
  const _doorEvidence=(via,sid,other)=>{
    if(!_arch) return null;
    const ev=__ACS_LATE.archDoorConnectsConfirmed(_arch,via);
    if(!ev) return null;
    const s=ev.spaces.slice().sort();
    const want=[sid,other].sort();
    return (s.length===want.length&&s[0]===want[0]&&s[1]===want[1])?ev:null; };
  Object.keys(floors).forEach(tmpl=>{
    const rooms=((floors[tmpl]||{}).rooms||[]).filter(r=>_relRect(r));
    const recs=rooms.map((r,i)=>[_relSpaceId(bid,tmpl,r,i),_relRect(r),r]);
    for(let i=0;i<recs.length;i++) for(let j=i+1;j<recs.length;j++){
      const ra=recs[i][1], rb=recs[j][1];
      if(_relContains(ra,rb)||_relContains(rb,ra)) continue;
      const go=_relGapOverlap(ra,rb), gap=go[0], ov=go[1];
      if(gap===null||gap>REL_ADJ_TOL||ov<=REL_TOUCH_EPS) continue;
      add('SPACE_ADJACENT',recs[i][0],recs[j][0],'geometry_inference',
          gap<=REL_TOUCH_EPS?'confirmed':'inferred',null,
          {gap:+gap.toFixed(3),overlap:+ov.toFixed(2),template:tmpl});
    }
    recs.forEach(rec=>{
      const sid=rec[0], rc=rec[1], room=rec[2];
      const x=rc[0],z=rc[1],w=rc[2],d=rc[3];
      (room.doors||[]).forEach((dr,di)=>{
        const e=String(dr.edge||'N').toUpperCase().slice(0,1);
        const off=+(dr.offset||0); let px,pz;
        if(e==='N'){px=x+off; pz=z-REL_DOOR_PROBE;}
        else if(e==='S'){px=x+off; pz=z+d+REL_DOOR_PROBE;}
        else if(e==='W'){px=x-REL_DOOR_PROBE; pz=z+off;}
        else {px=x+w+REL_DOOR_PROBE; pz=z+off;}
        const via=sid+'.door_'+di, cands=[];
        recs.forEach(r2=>{ if(r2[0]===sid||_relContains(r2[1],rc)) return;
          const b=r2[1];
          if(b[0]-0.01<=px&&px<=b[0]+b[2]+0.01&&b[1]-0.01<=pz&&pz<=b[1]+b[3]+0.01) cands.push(r2[0]); });
        if(cands.length===1){
          const ev=_doorEvidence(via,sid,cands[0]);
          const meta={edge:e,template:tmpl};
          if(ev){ meta.wall_id=ev.wall_id; meta.evidence_basis=ev.basis; }
          add('DOOR_CONNECTS',sid,cands[0],'geometry_inference',ev?'confirmed':'inferred',via,meta);
        }
        else add('DOOR_CONNECTS',sid,null,'geometry_inference','unresolved',via,
          {edge:e,template:tmpl,reason:cands.length?'ambiguous':'no_adjacent_space',candidates:cands.length});
      });
    });
  });
  // الاتصال الرأسي: تجميع "نوى رأسية" بالموضع عبر المستويات (مطابق لبايثون)
  const inst=[];
  Object.keys(floors).forEach(tmpl=>{
    const lv=_relLevelsFor(building,tmpl);
    ((floors[tmpl]||{}).rooms||[]).forEach((room,i)=>{
      const rc=_relRect(room); if(!rc) return;
      const sid=_relSpaceId(bid,tmpl,room,i);
      (room.objects||[]).forEach((o,oi)=>{
        const k=_relKind(o); if(!k) return;
        const ox=(o.x!==undefined&&o.x!==null)?+o.x:rc[2]/2;
        const oz=(o.z!==undefined&&o.z!==null)?+o.z:rc[3]/2;
        const via=sid+'.'+k+'_'+oi;
        (lv.length?lv:[null]).forEach(li=>inst.push({level:li,kind:k,x:rc[0]+ox,z:rc[1]+oz,via:via,space:sid}));
      });
    });
  });
  const cores=[];
  inst.forEach(it=>{
    let hit=null;
    for(const c of cores) if(c.kind===it.kind&&Math.abs(c.x-it.x)<=REL_CORE_TOL&&Math.abs(c.z-it.z)<=REL_CORE_TOL){hit=c;break;}
    if(hit) hit.items.push(it); else cores.push({kind:it.kind,x:it.x,z:it.z,items:[it]});
  });
  const pairs={};
  cores.forEach(c=>{
    const lvls=Array.from(new Set(c.items.filter(i=>i.level!==null).map(i=>i.level))).sort((a,b)=>a-b);
    const via=Array.from(new Set(c.items.map(i=>i.via))).sort()[0];
    if(lvls.length<2){
      add('VERTICAL_CONNECTS', lvls.length?_relLevelId(building,bid,lvls[0]):null, null,
          'geometry_inference','unresolved',via,
          {kind:c.kind,serviced_levels:lvls,reason:'single_level_instance'});
      return; }
    const ep={};
    c.items.forEach(i=>{ if(i.level!==null&&ep[String(i.level)]===undefined) ep[String(i.level)]=i.space; });
    for(let n=0;n<lvls.length-1;n++){
      const fa=_relLevelId(building,bid,lvls[n]), fb=_relLevelId(building,bid,lvls[n+1]);
      add('VERTICAL_CONNECTS',fa,fb,'geometry_inference','inferred',via,
          {kind:c.kind,serviced_levels:lvls,from_space:ep[String(lvls[n])],to_space:ep[String(lvls[n+1])],
           from_level:lvls[n],to_level:lvls[n+1]});
      const key=fa+'||'+fb; (pairs[key]=pairs[key]||new Set()).add(c.kind);
    }
  });
  Object.keys(pairs).sort().forEach(key=>{ const p=key.split('||');
    add('LEVEL_CONNECTS',p[0],p[1],'system_generated','inferred',null,
        {kinds:Array.from(pairs[key]).sort()}); });
  return rels;
}
/* علاقات مستوى المشروع: BUILDING_ON_SITE */
function buildProjectRelationships(project){
  const pr=(project||{}).project||{}, siteId=(pr.site||{}).id||'site_0';
  return (pr.buildings||[]).map((b,i)=>({
    id:(pr.id||'prj_0')+'.rel_'+(i+1), type:'BUILDING_ON_SITE',
    from:b.id, to:siteId, source:'system_generated', status:'confirmed',
    meta:{position:b.position||{x:0,z:0,rotation:0}, building_type:b.building_type}}));
}
/* فحوص بنيوية فقط — لا قواعد هندسية */
function validateRelationships(rels,building,bid,allowCross){
  bid=bid||'bld_0'; const issues=[], spaces=new Set(), levels=new Set();
  if(building){
    Object.keys(building.floors||{}).forEach(tmpl=>
      ((building.floors[tmpl]||{}).rooms||[]).forEach((r,i)=>spaces.add(_relSpaceId(bid,tmpl,r,i))));
    (building.levels||[]).forEach(l=>levels.add(l.id||(bid+'.flr_'+(+(l.index||0)))));
  }
  const seen=new Set(), ids=new Set();
  (rels||[]).forEach(e=>{
    if(ids.has(e.id)) issues.push('duplicate relationship id: '+e.id); ids.add(e.id);
    if(REL_TYPES.indexOf(e.type)<0) issues.push('unknown relationship type: '+e.type);
    if(REL_SOURCES.indexOf(e.source)<0) issues.push('['+e.id+'] invalid source: '+e.source);
    if(REL_STATUSES.indexOf(e.status)<0) issues.push('['+e.id+'] invalid status: '+e.status);
    if(e.source==='rule') issues.push('['+e.id+'] source=rule requires real rule evidence (none in this phase)');
    if(e.from&&e.to&&e.from===e.to) issues.push('['+e.id+'] self-link: '+e.from);
    if(e.status!=='unresolved'&&(e.from==null||e.to==null)) issues.push('['+e.id+'] resolved edge missing endpoint');
    if(e.type==='DOOR_CONNECTS'&&!e.via) issues.push('['+e.id+"] DOOR_CONNECTS requires 'via'");
    const key=[e.type,e.from,e.to,e.via].join('|');
    if(seen.has(key)) issues.push('['+e.id+'] duplicate edge '+key); seen.add(key);
    if(building) [e.from,e.to].forEach(ep=>{ if(!ep) return;
      if(e.type==='VERTICAL_CONNECTS'||e.type==='LEVEL_CONNECTS'){
        if(!levels.has(ep)) issues.push('['+e.id+'] dangling level ref: '+ep);
      }else if(['SPACE_ADJACENT','SPACE_CONNECTED','DOOR_CONNECTS'].indexOf(e.type)>=0){
        if(!spaces.has(ep)) issues.push('['+e.id+'] dangling space ref: '+ep);
      }
      if(!allowCross && String(ep).indexOf(bid+'.')!==0)
        issues.push('['+e.id+'] cross-building reference without permission: '+ep);
    });
  });
  return issues;
}
function relationshipSummary(rels){
  const out={}; (rels||[]).forEach(e=>{ out[e.type]=(out[e.type]||0)+1; });
  out.unresolved=(rels||[]).filter(e=>e.status==='unresolved').length;
  out.total=(rels||[]).length; return out;
}
/* ==================================================================
   المرحلة 2 — أساس التنقّل والمسارات (Circulation / Pathfinding).
   يشتقّ رسم تنقّل من رسم العلاقات ويجيب فقط: هل يوجد مسار اتصال؟
   لا إخلاء · لا حريق · لا إتاحة · لا مطابقة كود · لا مسافات ملفّقة · لا ثقة رقمية.
   SPACE_ADJACENT ليس عبوراً · unresolved لا يدخل المسار · BUILDING_ON_SITE ليست مشياً.
   عقدة = فراغ على مستوى: "<space_id>@<level>"  (نسخة مطابقة لـ acs_navigation.py)
   ================================================================== */
const NAV_TRAVERSABLE=['confirmed','inferred'];
function navNodeId(sp,lv){ return sp+'@'+lv; }
function _navLevelsForTemplate(b,tmpl){ return (b.levels||[]).filter(l=>l.template===tmpl)
  .map(l=>+(l.index||0)).sort((x,y)=>x-y); }
function _navCentroids(b,bid){ const out={};
  Object.keys(b.floors||{}).forEach(tmpl=>((b.floors[tmpl]||{}).rooms||[]).forEach((r,i)=>{
    const rc=r.rect; if(!rc||rc.length<4) return;
    const sid=r.space_id||(bid+'.'+tmpl+'.'+(r.id||('sp_'+i)));
    out[sid]=[+rc[0]+ +rc[2]/2, +rc[1]+ +rc[3]/2]; })); return out; }
function knownSpaces(b,bid){ const out=new Set();
  Object.keys(b.floors||{}).forEach(tmpl=>((b.floors[tmpl]||{}).rooms||[]).forEach((r,i)=>
    out.add(r.space_id||(bid+'.'+tmpl+'.'+(r.id||('sp_'+i)))))); return out; }
function buildNavGraph(building,rels,bid,includeUnresolved){
  bid=bid||'bld_0'; const nodes={},adj={},edges=[],cent=_navCentroids(building,bid);
  const ensure=(nid,sp,lv)=>{ if(!nodes[nid]){nodes[nid]={id:nid,space:sp,level:lv,centroid:cent[sp]||null};adj[nid]=[];} };
  const link=(a,b,e)=>{ edges.push(e); adj[a].push({to:b,edge:e}); adj[b].push({to:a,edge:e}); };
  const ok=NAV_TRAVERSABLE.concat(includeUnresolved?['unresolved']:[]);
  (rels||[]).forEach(rel=>{ const t=rel.type, st=rel.status, meta=rel.meta||{};
    if(t==='DOOR_CONNECTS'){
      if(ok.indexOf(st)<0||!rel.from||!rel.to) return;
      _navLevelsForTemplate(building,meta.template).forEach(lv=>{
        const a=navNodeId(rel.from,lv), b=navNodeId(rel.to,lv);
        ensure(a,rel.from,lv); ensure(b,rel.to,lv);
        link(a,b,{type:'door',via:rel.via,rel_id:rel.id,source:rel.source,status:st,level:lv}); });
    }else if(t==='VERTICAL_CONNECTS'){
      if(ok.indexOf(st)<0) return;
      const fs=meta.from_space, ts=meta.to_space, fl=meta.from_level, tl=meta.to_level;
      if(fs==null||ts==null||fl==null||tl==null) return;
      const a=navNodeId(fs,fl), b=navNodeId(ts,tl);
      ensure(a,fs,fl); ensure(b,ts,tl);
      link(a,b,{type:'vertical',kind:meta.kind,via:rel.via,rel_id:rel.id,source:rel.source,
                status:st,from_level:fl,to_level:tl});
    } /* غير ذلك: ليست حواف مشي */ });
  return {nodes:nodes,adj:adj,edges:edges,building_id:bid};
}
function _navResolve(nav,ref,spaces){
  if(!ref) return [null,'empty_reference','invalid'];
  ref=String(ref); const base=ref.split('@')[0];
  if(ref.indexOf('@')>=0){
    if(nav.nodes[ref]) return [ref,null,'ok'];
    return spaces.has(base)?[null,'space_has_no_eligible_edges','no_edges']:[null,'unknown_space','invalid']; }
  const c=Object.keys(nav.nodes).filter(n=>nav.nodes[n].space===ref);
  if(!c.length) return spaces.has(ref)?[null,'space_has_no_eligible_edges','no_edges']:[null,'unknown_space','invalid'];
  if(c.length>1) return [null,'ambiguous_level:specify space@level ('+c.sort().join(',')+')','invalid'];
  return [c[0],null,'ok'];
}
function findPath(building,rels,frm,to,bid,includeUnresolved){
  bid=bid||'bld_0';
  const res={status:null,from:frm,to:to,nodes:[],edges:[],transitions:[],hops:null,
             resolution:null,distance:null,distance_status:'NOT_MEASURED',metrics:{},reason:null};
  const bof=x=>x?String(x).split('.')[0]:null;
  if(bof(frm)&&bof(to)&&bof(frm)!==bof(to)){
    res.status='NOT_SUPPORTED_INTER_BUILDING';
    res.reason='physical inter-building circulation is not implemented'; return res; }
  const nav=buildNavGraph(building,rels,bid,includeUnresolved), spaces=knownSpaces(building,bid);
  const A=_navResolve(nav,frm,spaces); if(A[0]===null){ res.status=A[2]==='no_edges'?'NO_PATH':'INVALID_SOURCE'; res.reason=A[1]; return res; }
  const B=_navResolve(nav,to,spaces);  if(B[0]===null){ res.status=B[2]==='no_edges'?'NO_PATH':'INVALID_TARGET'; res.reason=B[1]; return res; }
  const a=A[0], b=B[0];
  if(a===b){ res.status='FOUND'; res.from=a; res.to=b; res.nodes=[a]; res.hops=0;
    res.resolution='confirmed';
    res.metrics={horizontal_centroid_m:0,vertical_transitions:0,measured_segments:'0/0'}; return res; }
  const prev={}, seen=new Set([a]); prev[a]=null; const q=[a];
  while(q.length){ const cur=q.shift(); if(cur===b) break;
    (nav.adj[cur]||[]).slice().sort((x,y)=>(x.to<y.to?-1:x.to>y.to?1:
        (String(x.edge.rel_id)<String(y.edge.rel_id)?-1:1))).forEach(nb=>{
      if(seen.has(nb.to)) return; seen.add(nb.to); prev[nb.to]=[cur,nb.edge]; q.push(nb.to); }); }
  if(prev[b]===undefined){
    res.status='NO_PATH';
    res.reason='no eligible edge chain (unresolved edges are never traversed)';
    if(!includeUnresolved){ const alt=findPath(building,rels,frm,to,bid,true);
      res.unresolved_alternative_exists=(alt.status==='FOUND'); }
    return res; }
  const chain=[]; let cur=b;
  while(prev[cur]!==null){ const pe=prev[cur]; chain.push([pe[0],pe[1],cur]); cur=pe[0]; }
  chain.reverse();
  const nodes=[a].concat(chain.map(c=>c[2])), edges=chain.map(c=>c[1]);
  let horiz=0,measured=0,verticals=0; const transitions=[];
  chain.forEach(c=>{ const p=c[0],e=c[1],n=c[2];
    if(e.type==='door'){
      transitions.push({type:'door',via:e.via,from:nav.nodes[p].space,to:nav.nodes[n].space,
        level:e.level,source:e.source,status:e.status});
      const ca=nav.nodes[p].centroid, cb=nav.nodes[n].centroid;
      if(ca&&cb){ horiz+=Math.sqrt(Math.pow(ca[0]-cb[0],2)+Math.pow(ca[1]-cb[1],2)); measured++; }
    }else{ verticals++;
      transitions.push({type:'vertical',kind:e.kind,via:e.via,
        from_level:nav.nodes[p].level,to_level:nav.nodes[n].level,
        from:nav.nodes[p].space,to:nav.nodes[n].space,source:e.source,status:e.status,
        distance_measurable:false}); } });
  const sts=new Set(edges.map(e=>e.status));
  res.status='FOUND'; res.from=a; res.to=b; res.nodes=nodes; res.edges=edges;
  res.transitions=transitions; res.hops=edges.length;
  res.resolution = sts.has('unresolved')?'unresolved'
                 : (sts.size===1&&sts.has('confirmed'))?'confirmed':'contains_inferred_edges';
  res.distance=null; res.distance_status=measured?'PARTIAL':'NOT_MEASURED';
  res.metrics={horizontal_centroid_m:+horiz.toFixed(2),vertical_transitions:verticals,
    measured_segments:measured+'/'+edges.length,
    note:'مسافة بين مراكز الفراغات — ليست مسافة مشي، والانتقال الرأسي غير مقيس'};
  return res;
}
function validatePath(building,rels,result,bid){
  bid=bid||'bld_0'; const issues=[]; if(result.status!=='FOUND') return issues;
  const nav=buildNavGraph(building,rels,bid,false), nodes=result.nodes||[];
  if(!nodes.length){ issues.push('empty path'); return issues; }
  if(nodes[0]!==result.from) issues.push('first node != requested source');
  if(nodes[nodes.length-1]!==result.to) issues.push('last node != requested target');
  nodes.forEach(n=>{ if(!nav.nodes[n]) issues.push('unknown node in path: '+n); });
  for(let i=0;i<nodes.length-1;i++)
    if(!(nav.adj[nodes[i]]||[]).some(x=>x.to===nodes[i+1]))
      issues.push('no eligible edge between '+nodes[i]+' and '+nodes[i+1]);
  (result.edges||[]).forEach(e=>{ if(e.status==='unresolved') issues.push('path traverses an unresolved edge (forbidden)'); });
  (result.transitions||[]).forEach(t=>{ if(t.type==='vertical'&&(t.from_level==null||t.to_level==null))
    issues.push('vertical transition without valid levels'); });
  if(new Set(nodes.map(n=>String(n).split('.')[0])).size>1) issues.push('path crosses buildings');
  return issues;
}
function navIssues(building,rels,bid){ bid=bid||'bld_0';
  const nav=buildNavGraph(building,rels,bid,false);
  return {isolated_nodes:Object.keys(nav.nodes).filter(n=>!(nav.adj[n]||[]).length).sort(),
          node_count:Object.keys(nav.nodes).length, edge_count:nav.edges.length}; }
function pathSummary(r){
  if(r.status!=='FOUND') return 'لا يوجد مسار اتصال: '+r.status+' ('+(r.reason||'')+')';
  const parts=[String(r.nodes[0]).split('@')[0]];
  (r.transitions||[]).forEach(t=>{
    if(t.type==='door'){ parts.push('باب '+(t.via||'')); parts.push(t.to); }
    else { parts.push((t.kind==='stairs'?'درج ':'مصعد ')+(t.via||'')+' (مستوى '+t.from_level+' ← '+t.to_level+')'); parts.push(t.to); } });
  return 'مسار تنقّل حسب العلاقات الحالية ('+(r.hops||0)+' انتقال، '+r.resolution+'): '+parts.join(' → ');
}
/* ==================================================================
   المرحلة 2 — أساس المخارج والإخلاء (طوبولوجيا فقط).
   يجيب: ما المخارج المُمثَّلة؟ وأي الفراغات تصل إليها عبر رسم الاتصال؟
   لا يجيب: آمن؟ مطابق؟ نظامي؟ مسافة ضمن الحد؟ عدد المخارج كافٍ؟ درج محمي؟
   مصعد يجوز؟ — كلها تحتاج محرّك قواعد غير موجود. compliance = NOT_EVALUATED.
   يعيد استخدام رسم التنقّل بلا تكرار. (نسخة مطابقة لـ acs_egress.py)
   ================================================================== */
const EG_DESTINATIONS=['exterior','site','protected_area','unknown'];
const EG_SOURCES=['user','ai_inference','system_generated','geometry_inference','rule'];
const EG_STATUSES=['confirmed','inferred','unresolved'];
const EG_USABLE=['confirmed','inferred'];
const EG_PEOPLE=['person','worker','visitor','engineer','child'];
const EG_PROBE=0.15, EG_MARGIN=0.05;
function _egRect(r){ const rc=r.rect; return (rc&&rc.length>=4)?rc.slice(0,4).map(Number):null; }
function _egSid(bid,tmpl,room,i){ return room.space_id||(bid+'.'+tmpl+'.'+(room.id||('sp_'+i))); }
function _egFootprint(rooms){ let xs=[],zs=[],xe=[],ze=[];
  rooms.forEach(r=>{ const rc=_egRect(r); if(rc){xs.push(rc[0]);zs.push(rc[1]);xe.push(rc[0]+rc[2]);ze.push(rc[1]+rc[3]);} });
  return xs.length?[Math.min(...xs),Math.min(...zs),Math.max(...xe),Math.max(...ze)]:null; }
function _egProbe(rc,edge,off){ const x=rc[0],z=rc[1],w=rc[2],d=rc[3];
  const e=String(edge||'N').toUpperCase().slice(0,1);
  if(e==='N') return [x+off,z-EG_PROBE]; if(e==='S') return [x+off,z+d+EG_PROBE];
  if(e==='W') return [x-EG_PROBE,z+off]; return [x+w+EG_PROBE,z+off]; }
function extractExits(building,rels,bid){
  bid=bid||'bld_0'; const exits=[]; let seq=0;
  const resolvedVia=new Set((rels||[]).filter(r=>r.type==='DOOR_CONNECTS'&&r.to).map(r=>r.via));
  const add=(lv,sp,via,dest,src,st,meta)=>{ seq++;
    const e={id:bid+'.exit_'+seq,type:'exit',building_id:bid,
      level_id:(lv!=null?bid+'.flr_'+lv:null),level:lv,space_id:sp,via:via,
      destination:dest,source:src,status:st}; if(meta) e.meta=meta; exits.push(e); };
  Object.keys(building.floors||{}).forEach(tmpl=>{
    const rooms=(building.floors[tmpl]||{}).rooms||[], fp=_egFootprint(rooms);
    const levels=(building.levels||[]).filter(l=>l.template===tmpl).map(l=>+(l.index||0)).sort((a,b)=>a-b);
    rooms.forEach((room,i)=>{ const rc=_egRect(room); if(!rc) return;
      const sid=_egSid(bid,tmpl,room,i); let hasExt=false;
      (room.doors||[]).forEach((dr,di)=>{ const via=sid+'.door_'+di;
        if(dr.exit===true||dr.destination){
          const d=dr.destination||'exterior';
          levels.forEach(lv=>add(lv,sid,via,EG_DESTINATIONS.indexOf(d)>=0?d:'unknown',
            dr.source||'user','confirmed',{basis:'explicit_door_flag'}));
          hasExt=true; return; }
        if(resolvedVia.has(via)||!fp) return;
        const p=_egProbe(rc,dr.edge,+(dr.offset||0));
        const outside=(p[0]<fp[0]-EG_MARGIN||p[0]>fp[2]+EG_MARGIN||p[1]<fp[1]-EG_MARGIN||p[1]>fp[3]+EG_MARGIN);
        if(outside){ levels.forEach(lv=>add(lv,sid,via,'exterior','geometry_inference','inferred',
            {basis:'door_probe_outside_level_footprint'})); hasExt=true; } });
      if(!hasExt) (room.points||[]).forEach((pt,pi)=>{ if(String(pt.type)!=='exit') return;
        const src=pt.auto?'system_generated':'user';
        levels.forEach(lv=>add(lv,sid,sid+'.exitpoint_'+pi,'unknown',src,'unresolved',
          {basis:'exit_marker_without_proven_exterior_door'})); });
    });
  });
  return exits;
}
function usableExits(ex){ return (ex||[]).filter(e=>EG_USABLE.indexOf(e.status)>=0); }
function _egPeople(building,spaceId,bid){ bid=bid||'bld_0'; let n=0;
  Object.keys(building.floors||{}).forEach(tmpl=>((building.floors[tmpl]||{}).rooms||[]).forEach((r,i)=>{
    if(_egSid(bid,tmpl,r,i)!==spaceId) return;
    (r.objects||[]).forEach(o=>{ if(EG_PEOPLE.indexOf(String(o.kind||'').toLowerCase())>=0) n+=Math.max(1,+(o.count||1)); }); }));
  return n; }
function _egChars(route){ const tr=route.transitions||[], v=tr.filter(t=>t.type==='vertical');
  const lv=new Set(); v.forEach(t=>{lv.add(t.from_level);lv.add(t.to_level);});
  return {door_count:tr.filter(t=>t.type==='door').length, vertical_transition_count:v.length,
    uses_stairs:v.some(t=>t.kind==='stairs'), uses_elevator:v.some(t=>t.kind==='elevator'),
    levels_crossed:lv.size?Math.max(0,lv.size-1):0,
    contains_inferred_edges:route.resolution==='contains_inferred_edges',
    contains_unresolved_edges:false}; }
function findEgress(building,rels,origin,bid){
  bid=bid||'bld_0';
  const out={status:null,origin:origin,exit:null,route:null,alternative_exits:[],
    unreachable_exits:[],resolution:null,distance:null,distance_status:'NOT_MEASURED',
    compliance:'NOT_EVALUATED',selection_basis:'minimum_hops',selection_basis_reason:null,
    distance_measurement:null,characteristics:null,represented_people_count:0,reason:null};
  if(origin&&String(origin).indexOf(bid+'.')!==0){
    out.status='NOT_SUPPORTED_INTER_BUILDING';
    out.reason='egress is evaluated within one building only'; return out; }
  const exits=extractExits(building,rels,bid);
  if(!exits.length){ out.status='NO_EXIT_DEFINED';
    out.reason='no exit is represented in the model (none was invented)'; return out; }
  const ok=usableExits(exits);
  if(!ok.length){ out.status='UNRESOLVED_EXIT';
    out.reason='exit markers exist but their destination is not proven';
    out.unreachable_exits=exits.map(e=>e.id); return out; }
  const probe=findPath(building,rels,origin,origin,bid);
  if(probe.status==='INVALID_SOURCE'||probe.status==='INVALID_TARGET'){
    out.status=/ambiguous_level/.test(String(probe.reason))?'AMBIGUOUS_ORIGIN':'INVALID_ORIGIN';
    out.reason=probe.reason; return out; }
  const cands=[], unreach=[];
  ok.forEach(e=>{ const target=(e.level!=null)?navNodeId(e.space_id,e.level):e.space_id;
    const r=findPath(building,rels,origin,target,bid);
    if(r.status==='FOUND') cands.push({exit:e,route:r,hops:r.hops});
    else unreach.push({exit_id:e.id,status:r.status,reason:r.reason}); });
  out.unreachable_exits=unreach;
  if(!cands.length){ out.status='NO_PATH'; out.reason='NO_PATH_TO_REPRESENTED_EXIT'; return out; }
  /* قياس هندسي إضافي (لا يُنشئ اتصالاً ولا يغيّر الطوبولوجيا).
     نقطة الوجهة هي مرساة باب المخرج نفسه من هندسة النموذج، لا مركز الفراغ. */
  const roomsIdx=_dsRooms(building,bid);
  const _egArch=architectureOf(building,bid);      /* مرّة واحدة لكل المرشّحين */
  cands.forEach(c=>{ const vd=_viaDoor(c.exit.via), sp=vd[0], di=vd[1];
    const destPt=(sp!==null&&Object.prototype.hasOwnProperty.call(roomsIdx,sp))
      ?doorAnchor(roomsIdx[sp],di,_egArch,sp):null;
    c.measurement=measurePath(building,c.route,bid,null,destPt,_egArch); });
  const allComplete=cands.every(c=>c.measurement.distance_status==='COMPLETE');
  let selBasis,selReason;
  if(allComplete){
    // مسموح فقط لأن كل المرشّحين مقيسون بالكامل من هندسة النموذج
    cands.sort((a,b)=>a.measurement.walking_distance_m-b.measurement.walking_distance_m||
                      (a.exit.id<b.exit.id?-1:(a.exit.id>b.exit.id?1:0)));
    selBasis='minimum_measured_walking_distance';
    selReason='all candidate routes measured COMPLETE from model geometry';
  } else {
    cands.sort((a,b)=>a.hops-b.hops||(a.exit.id<b.exit.id?-1:(a.exit.id>b.exit.id?1:0)));
    selBasis='minimum_hops';
    const by={}; cands.forEach(c=>{ const st=c.measurement.distance_status;
      if(st!=='COMPLETE') by[st]=(by[st]||0)+1; });
    selReason='geometric shortest route not claimed: '+
      Object.keys(by).sort().map(k=>by[k]+' '+k).join(', '); }
  const best=cands[0], m=best.measurement;
  out.status='FOUND'; out.exit=best.exit; out.route=best.route; out.resolution=best.route.resolution;
  out.distance=(m.walking_distance_m===undefined?null:m.walking_distance_m);
  out.distance_status=m.distance_status;
  out.distance_measurement=m;
  out.selection_basis=selBasis; out.selection_basis_reason=selReason;
  out.characteristics=_egChars(best.route);
  out.represented_people_count=_egPeople(building,String(origin).split('@')[0],bid);
  out.metrics=best.route.metrics;
  out.alternative_exits=cands.slice(1).map(c=>({exit_id:c.exit.id,hops:c.hops,
    characteristics:_egChars(c.route),distance_status:c.measurement.distance_status,
    walking_distance_m:(c.measurement.walking_distance_m===undefined?null:c.measurement.walking_distance_m)}));
  return out;
}
function auditEgress(building,rels,bid){
  bid=bid||'bld_0';
  const exits=extractExits(building,rels,bid), ok=usableExits(exits);
  const nav=buildNavGraph(building,rels,bid,false);
  const starts=ok.map(e=>navNodeId(e.space_id,e.level)).filter(n=>nav.nodes[n]);
  const seen=new Set(starts); const q=starts.slice();
  while(q.length){ const cur=q.shift();
    (nav.adj[cur]||[]).forEach(nb=>{ if(!seen.has(nb.to)){seen.add(nb.to);q.push(nb.to);} }); }
  const nodes=Object.keys(nav.nodes), total=knownSpaces(building,bid).size;
  const covered=new Set(nodes.map(n=>nav.nodes[n].space));
  return {spaces:total,nav_nodes:nodes.length,exits_total:exits.length,
    confirmed_exits:exits.filter(e=>e.status==='confirmed').length,
    inferred_exits:exits.filter(e=>e.status==='inferred').length,
    unresolved_exits:exits.filter(e=>e.status==='unresolved').length,
    nodes_with_reachable_exit:nodes.filter(n=>seen.has(n)).length,
    nodes_without_reachable_exit:nodes.filter(n=>!seen.has(n)).length,
    spaces_without_nav_edges:Math.max(0,total-covered.size),
    compliance:'NOT_EVALUATED'}; }
function validateExits(building,exits,bid){
  bid=bid||'bld_0'; const issues=[],ids=new Set(),seen=new Set();
  const spaces=knownSpaces(building,bid);
  const levels=new Set((building.levels||[]).map(l=>+(l.index||0)));
  (exits||[]).forEach(e=>{
    if(ids.has(e.id)) issues.push('duplicate exit id: '+e.id); ids.add(e.id);
    if(EG_SOURCES.indexOf(e.source)<0) issues.push('['+e.id+'] invalid source: '+e.source);
    if(e.source==='rule') issues.push('['+e.id+'] source=rule requires real rule evidence (none in this phase)');
    if(EG_STATUSES.indexOf(e.status)<0) issues.push('['+e.id+'] invalid status: '+e.status);
    if(EG_DESTINATIONS.indexOf(e.destination)<0) issues.push('['+e.id+'] invalid destination: '+e.destination);
    if(!spaces.has(e.space_id)) issues.push('['+e.id+'] dangling space: '+e.space_id);
    if(e.level!=null&&!levels.has(e.level)) issues.push('['+e.id+'] invalid level: '+e.level);
    if(!e.via) issues.push('['+e.id+'] exit without via element');
    if(e.building_id!==bid||String(e.space_id).indexOf(bid+'.')!==0) issues.push('['+e.id+'] exit points to another building');
    const key=[e.space_id,e.via,e.level].join('|');
    if(seen.has(key)) issues.push('['+e.id+'] duplicate exit definition '+key); seen.add(key);
  });
  return issues; }
function egressSummary(r){
  if(r.status==='FOUND'){ const c=r.characteristics||{};
    const head='مسار مرشّح إلى مخرج ممثّل في النموذج ('+((r.route||{}).hops||0)+' انتقال، أبواب '+
      (c.door_count||0)+'، انتقالات رأسية '+(c.vertical_transition_count||0)+
      (c.uses_stairs?'، يستخدم درجاً':(c.uses_elevator?'، يستخدم مصعداً':''))+') — ';
    if(r.distance_status==='COMPLETE'&&r.distance!==null&&r.distance!==undefined)
      return head+'المسافة الهندسية المقاسة '+_fx2(r.distance)+' م من هندسة النموذج، ولم تُقيَّم أي مطابقة.';
    return head+'المسافة الفعلية للمشي لم تُحسب، ولم تُقيَّم أي مطابقة.'; }
  if(r.status==='NO_EXIT_DEFINED') return 'لا يوجد مخرج ممثّل في النموذج (لم يُختلق أي مخرج).';
  if(r.status==='NO_PATH') return 'لا يوجد مسار اتصال معروف إلى أي مخرج ممثّل.';
  if(r.status==='UNRESOLVED_EXIT') return 'توجد علامات مخارج لكن وجهتها غير مُثبتة — لا تُعتمد مقصداً.';
  return 'تعذّر التقييم الطوبولوجي: '+r.status+' ('+(r.reason||'')+')'; }
/* ==================================================================
   المرحلة 2 — أساس قياس المسافة الهندسية الحقيقية (نسخة مطابقة لـ acs_distance.py).
   يقيس فقط: كم متراً يمكن قياسه فعلياً من هندسة النموذج على مسار موجود أصلاً.
   لا يجيب إطلاقاً: هل المسافة نظامية/ضمن الحد/آمنة/مطابقة؟ — لا محرّك أكواد هنا.
   مبادئ: الهندسة تَقيس مساراً موجوداً ولا تُنشئ اتصالاً • ممنوع تحويل مسافة
   مراكز الفراغات إلى مسافة مشي • ممنوع اختراع هندسة درج • رحلة المصعد ليست
   مشياً • COMPLETE لا تُستعمل إن كان أي مقطع مطلوب غير مقيس • الأشكال غير
   المستطيلة ⇒ GEOMETRY_NOT_SUPPORTED (لا خط مستقيم عبر الجدران).
   ================================================================== */
const DIST_STATUSES=['COMPLETE','PARTIAL','NOT_MEASURED','GEOMETRY_NOT_SUPPORTED','INVALID_PATH'];
const DIST_BASES=['door_geometry','straight_line_inside_rect','corridor_centerline',
                  'stair_geometry','centroid_fallback','unmeasured'];
const CORRIDOR_ASPECT=3.0;   // نسبة طول/عرض تُعامل بها المساحة كممر (هندسي، لا اسمي)
/* تقريب مطابق لسلوك round() في بايثون (نصف إلى الزوجي على القيم المتعادلة تماماً) */
function _pyRound(x,nd){
  if(x===null||x===undefined||typeof x!=='number'||!isFinite(x)) return x;
  /* toFixed تنتج صيغة أسّية عند 1e21 فما فوق، فيتحوّل التحليل إلى قيمة خاطئة
     تماماً (1e308 كانت تصير 0.000001). عند هذا الحجم لا يبقى للتقريب العشري
     أثر رياضي، فتُعاد القيمة كما هي — وهو ما تفعله round في بايثون بالضبط. */
  if(Math.abs(x)>=1e21) return x;
  const neg=x<0, v=Math.abs(x), s=v.toFixed(20), dot=s.indexOf('.');
  const ip=s.slice(0,dot), fp=s.slice(dot+1);
  const keep=fp.slice(0,nd), rest=fp.slice(nd);
  let n=parseInt(ip+keep,10); const first=rest.charCodeAt(0)-48;
  if(first>5) n+=1;
  else if(first===5){ if(/[1-9]/.test(rest.slice(1))) n+=1; else if(n%2===1) n+=1; }
  const r=n/Math.pow(10,nd); return neg?-r:r;
}
const _r3=x=>_pyRound(x,3);
const _fx2=x=>_pyRound(x,2).toFixed(2);
function _dsRect(r){ const rc=r.rect; return (rc&&rc.length>=4)?rc.slice(0,4).map(Number):null; }
function _dsIsRect(r){ if(r.polygon||r.shape||r.vertices) return false; return _dsRect(r)!==null; }
function _dsCentroid(rc){ return [rc[0]+rc[2]/2.0, rc[1]+rc[3]/2.0]; }
function _dsRooms(building,bid){ bid=bid||'bld_0'; const idx={};
  Object.keys(building.floors||{}).forEach(tmpl=>{
    (((building.floors||{})[tmpl]||{}).rooms||[]).forEach((r,i)=>{
      const sid=r.space_id||(bid+'.'+tmpl+'.'+(r.id||('sp_'+i))); idx[sid]=r; }); });
  return idx; }
/* يصرّف الهندسة المعمارية إن أمكن. غيابها لا يمنع القياس ولا يغيّر نتيجة */
function architectureOf(building,bid){
  try{ return __ACS_LATE.compileArchitecture(building,bid||'bld_0'); }catch(e){ return null; } }
/* نقطة عبور الباب من هندسته الفعلية (الحافة + الإزاحة)، لا من مركز الغرفة.
   حين تتوفّر هندسة الفتحة المصرَّفة نقرأ المرساة منها: هي المصدر المفضّل لأنها
   نفس المصدر الذي يرسم الجدار. للمستطيلات المحاذية للمحاور القيمتان متطابقتان
   رياضياً — والاختبار يثبت التطابق على كل النماذج، ولا يُفترض. */
function doorAnchor(room,doorIndex,arch,spaceId,levelIndex){
  if(!room||typeof room!=='object') return null;
  const rc=_dsRect(room), doors=room.doors||[];
  if(rc===null||doorIndex===null||doorIndex===undefined||doorIndex>=doors.length) return null;
  const d=doors[doorIndex];
  // لا نختلق موضع باب: الحافة والإزاحة يجب أن تكونا مصرَّحتين في النموذج
  if(d.edge===null||d.edge===undefined||d.offset===null||d.offset===undefined) return null;
  if(arch&&spaceId!==null&&spaceId!==undefined){
    const pt=__ACS_LATE.archOpeningAnchor(arch,spaceId+'.door_'+doorIndex,levelIndex);
    if(pt!==null&&pt!==undefined) return [Number(pt[0]),Number(pt[1])]; }
  const x=rc[0], z=rc[1], w=rc[2], dep=rc[3];
  const off=Number(d.offset||0), e=String(d.edge||'N').toUpperCase().slice(0,1);
  if(e==='N') return [x+off,z];
  if(e==='S') return [x+off,z+dep];
  if(e==='W') return [x,z+off];
  return [x+w,z+off]; }
function _viaDoor(via){                     // '<space_id>.door_<i>' → [space_id, i]
  if(!via) return [null,null];
  const s=String(via), p=s.lastIndexOf('.door_');
  if(p<0) return [null,null];
  const tail=s.slice(p+6); if(!/^-?\d+$/.test(tail)) return [null,null];
  return [s.slice(0,p), parseInt(tail,10)]; }
function _dsDist(a,b){ const dx=a[0]-b[0], dz=a[1]-b[1]; return Math.sqrt(dx*dx+dz*dz); }
function _inSpaceLength(room,a,b){
  const rc=_dsRect(room); if(rc===null) return [null,'unmeasured'];
  const w=rc[2], d=rc[3];
  const longSide=(w>=d)?w:d, shortSide=(w>=d)?d:w;
  if(shortSide>0 && (longSide/shortSide)>=CORRIDOR_ASPECT){
    if(w>=d){ const mid=rc[1]+d/2.0;
      return [Math.abs(a[0]-b[0])+Math.abs(a[1]-mid)+Math.abs(b[1]-mid),'corridor_centerline']; }
    const mid=rc[0]+w/2.0;
    return [Math.abs(a[1]-b[1])+Math.abs(a[0]-mid)+Math.abs(b[0]-mid),'corridor_centerline']; }
  return [_dsDist(a,b),'straight_line_inside_rect']; }
/* طول سير الدرج من قيم موجودة فعلاً في النموذج فقط — لا اختراع هندسة درج */
function _stairGeometry(obj){
  if(!obj||typeof obj!=='object') return null;
  let run=(obj.run_m===undefined?null:obj.run_m), rise=(obj.rise_m===undefined?null:obj.rise_m);
  if(run===null && obj.risers && obj.tread_m){
    run=Number(obj.risers)*Number(obj.tread_m);
    if(obj.riser_m) rise=Number(obj.risers)*Number(obj.riser_m); }
  if(run===null) return null;
  run=Number(run); if(rise===null) return run;
  rise=Number(rise); return Math.sqrt(run*run+rise*rise); }
function _dsFindObject(room,kind){
  const objs=(room&&room.objects)||[];
  for(let i=0;i<objs.length;i++){ const k=String(objs[i].kind||objs[i].name||'').toLowerCase();
    if(kind==='stairs'&&(k.indexOf('stair')>=0||k.indexOf('درج')>=0||k.indexOf('سلم')>=0)) return objs[i];
    if(kind==='elevator'&&(k.indexOf('elevator')>=0||k.indexOf('lift')>=0||k.indexOf('مصعد')>=0)) return objs[i]; }
  return null; }
/* موضع عنصر (درج/مصعد) بالإحداثيات العامة — فقط إن كان مصرَّحاً في النموذج.
   إحداثيات العناصر نسبية لركن الفراغ. الغياب لا يُعوَّض بمركز الفراغ. */
function _objPoint(room,obj){
  if(!room||typeof room!=='object'||!obj||typeof obj!=='object') return null;
  const rc=_dsRect(room);
  if(rc===null||obj.x===null||obj.x===undefined||obj.z===null||obj.z===undefined) return null;
  return [rc[0]+Number(obj.x), rc[1]+Number(obj.z)]; }
function _levelElevation(building,levelIndex){
  const lv=building.levels||[];
  for(let i=0;i<lv.length;i++){
    if(Number(lv[i].index===undefined?0:lv[i].index)===Number(levelIndex)){
      if(lv[i].elevation!==undefined&&lv[i].elevation!==null) return Number(lv[i].elevation); } }
  const fh=building.floor_height;
  return (fh!==undefined&&fh!==null)?Number(levelIndex)*Number(fh):null; }
/* يقيس هندسة مسار ناتج عن محرّك التنقّل. مشتقّ بالكامل — لا يُحفظ كبيانات مبنى */
function measurePath(building,pathResult,bid,originPoint,destinationPoint,arch){
  bid=bid||'bld_0';
  const out={status:null,segments:[],horizontal_m:0.0,stair_walking_m:0.0,
    walking_distance_m:null,walking_distance_exact_m:null,
    vertical_transport:[],vertical_elevation_change_m:null,
    distance_status:'NOT_MEASURED',measurement_basis:[],unmeasured_segments:[],
    origin_basis:null,units:'m',compliance:'NOT_EVALUATED'};
  if(!pathResult||pathResult.status!=='FOUND'){
    out.status='INVALID_PATH'; out.distance_status='INVALID_PATH';
    out.reason='distance is measured only for a FOUND topological path'; return out; }
  const roomsIdx=_dsRooms(building,bid);
  const RG=s=>Object.prototype.hasOwnProperty.call(roomsIdx,s)?roomsIdx[s]:null;
  const transitions=pathResult.transitions||[], nodes=pathResult.nodes||[];
  if(!nodes.length){ out.status='INVALID_PATH'; out.distance_status='INVALID_PATH'; return out; }
  const spaceOf=n=>String(n).split('@')[0];
  let unsupported=false, curSpace=spaceOf(nodes[0]);
  const room0=RG(curSpace);
  if(room0===null||!_dsIsRect(room0)) unsupported=unsupported||(room0!==null);
  let curPt;
  if(originPoint&&originPoint.length){ curPt=originPoint.slice(); out.origin_basis='explicit_origin_point'; }
  else if(room0!==null&&_dsRect(room0)){ curPt=_dsCentroid(_dsRect(room0)); out.origin_basis='space_centroid_fallback'; }
  else { curPt=null; out.origin_basis='unmeasured'; }
  let curPtReason=(curPt!==null)?null:'origin_anchor_unavailable';
  const wallT=Number(building.wall_t||0.0);
  transitions.forEach(t=>{
    if(t.type==='door'){
      const vd=_viaDoor(t.via), sp=vd[0], di=vd[1];
      const room=(sp===null)?null:RG(sp);
      if(arch===undefined||arch===null) arch=architectureOf(building,bid);  /* مرّة واحدة لكل قياس */
      const anchor=(room!==null)?doorAnchor(room,di,arch,sp):null;
      const fromRoom=RG(curSpace);
      if(anchor===null||fromRoom===null||curPt===null){
        const r_=(anchor===null)?'door_anchor_not_derivable_from_model':
                 ((fromRoom===null)?'space_geometry_missing':(curPtReason||'origin_anchor_unavailable'));
        out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:r_});
        out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
        curPt=null; curPtReason='previous_anchor_unavailable';
      } else if(!_dsIsRect(fromRoom)){
        unsupported=true;
        out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:'non_rectangular_geometry_not_supported'});
        out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
        curPt=anchor; curPtReason=null;
      } else {
        const res=_inSpaceLength(fromRoom,curPt,anchor), ln=res[0], basis=res[1];
        if(ln===null){
          out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
          out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:'geometry_missing'});
        } else {
          out.segments.push({type:'in_space',space:curSpace,from:curPt,to:anchor,
                             length_m:_r3(ln),basis:basis});
          out.horizontal_m+=ln; out.measurement_basis.push(basis); }
        curPt=anchor; curPtReason=null; }
      if(wallT>0){
        out.segments.push({type:'door_transition',via:t.via,length_m:_r3(wallT),basis:'door_geometry'});
        out.horizontal_m+=wallT; out.measurement_basis.push('door_geometry');
      } else {
        out.segments.push({type:'door_transition',via:t.via,length_m:null,basis:'unmeasured'});
        out.unmeasured_segments.push({type:'door_transition',via:t.via,reason:'wall_thickness_unknown'}); }
      curSpace=t.to||curSpace;
    } else {                                   // انتقال رأسي
      const kind=t.kind, room=RG(curSpace);
      const obj=(room!==null)?_dsFindObject(room,kind):null;
      const ap=_objPoint(room,obj);
      // المشي داخل الفراغ حتى العنصر الرأسي جزء حقيقي من المسار — لا يُسقَط بصمت
      if(room!==null&&!_dsIsRect(room)){
        unsupported=true;
        out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
        out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:'non_rectangular_geometry_not_supported'});
      } else if(ap!==null&&curPt!==null&&room!==null){
        const rs=_inSpaceLength(room,curPt,ap), ln=rs[0], basis=rs[1];
        if(ln===null){
          out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
          out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:'geometry_missing'});
        } else {
          out.segments.push({type:'in_space',space:curSpace,from:curPt,to:ap,
                             length_m:_r3(ln),basis:basis});
          out.horizontal_m+=ln; out.measurement_basis.push(basis); }
      } else {
        const r_=(ap===null)?'vertical_element_position_not_stated':
                 ((room===null)?'space_geometry_missing':(curPtReason||'origin_anchor_unavailable'));
        out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
        out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:r_}); }
      let dz=null;
      const ea=_levelElevation(building,t.from_level), eb=_levelElevation(building,t.to_level);
      if(ea!==null&&eb!==null) dz=Math.abs(eb-ea);
      if(kind==='stairs'){
        const sl=_stairGeometry(obj);
        if(sl===null){
          out.segments.push({type:'stair',via:t.via,length_m:null,basis:'unmeasured'});
          out.unmeasured_segments.push({type:'stair',via:t.via,
            reason:'stair_geometry_absent (no risers/tread/run in model)'});
        } else {
          out.segments.push({type:'stair',via:t.via,length_m:_r3(sl),basis:'stair_geometry'});
          out.stair_walking_m+=sl; out.measurement_basis.push('stair_geometry'); }
      } else {                                 // مصعد: نقل رأسي، ليس مشياً
        out.segments.push({type:'vertical_transport',via:t.via,kind:kind,length_m:null,
                           basis:'not_walking_distance'});
        out.vertical_transport.push({kind:kind,via:t.via,from_level:t.from_level,
          to_level:t.to_level,elevation_change_m:dz}); }
      if(dz!==null) out.vertical_elevation_change_m=(out.vertical_elevation_change_m||0.0)+dz;
      curSpace=t.to||curSpace;
      const r2=RG(curSpace);
      // نقطة الوصول هي موضع العنصر الرأسي في الفراغ الجديد — لا مركز الفراغ
      const p2=_objPoint(r2,(r2!==null)?_dsFindObject(r2,kind):null);
      if(p2!==null){ curPt=p2; curPtReason=null; }
      else { curPt=null; curPtReason='vertical_element_arrival_position_not_stated'; } }
  });
  const lastRoom=RG(curSpace);
  let destPt;
  if(destinationPoint&&destinationPoint.length) destPt=destinationPoint.slice();
  else if(lastRoom!==null&&_dsRect(lastRoom)) destPt=_dsCentroid(_dsRect(lastRoom));
  else destPt=null;
  if(curPt!==null&&destPt!==null&&lastRoom!==null){
    if(!_dsIsRect(lastRoom)){
      unsupported=true;
      out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
      out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:'non_rectangular_geometry_not_supported'});
    } else {
      const res=_inSpaceLength(lastRoom,curPt,destPt), ln=res[0], basis=res[1];
      out.segments.push({type:'in_space',space:curSpace,from:curPt,to:destPt,
                         length_m:_r3(ln),basis:basis});
      out.horizontal_m+=ln; out.measurement_basis.push(basis); }
  } else if(curPt===null||destPt===null){
    const r_=(curPt===null)?(curPtReason||'origin_anchor_unavailable'):'destination_anchor_unavailable';
    out.segments.push({type:'in_space',space:curSpace,length_m:null,basis:'unmeasured'});
    out.unmeasured_segments.push({type:'in_space',space:curSpace,reason:r_}); }
  // قيم التقييم بدقّة كاملة تُحفظ منفصلة عن قيم العرض المقرَّبة (§دقّة)
  out.horizontal_exact_m=out.horizontal_m;
  out.stair_walking_exact_m=out.stair_walking_m;
  out.horizontal_m=_r3(out.horizontal_m);
  out.stair_walking_m=_r3(out.stair_walking_m);
  out.measurement_basis=Array.from(new Set(out.measurement_basis)).sort();
  if(unsupported){
    out.status='GEOMETRY_NOT_SUPPORTED'; out.distance_status='GEOMETRY_NOT_SUPPORTED';
    out.measured_horizontal_m=out.horizontal_m;
  } else if(out.unmeasured_segments.length){
    out.status='PARTIAL'; out.distance_status='PARTIAL';
    out.measured_horizontal_m=out.horizontal_m;
  } else if(!out.segments.length){
    out.status='NOT_MEASURED'; out.distance_status='NOT_MEASURED';
  } else {
    out.status='MEASURED'; out.distance_status='COMPLETE';
    // walking_distance_m = مقاطع المشي الأفقية + سير الدرج المقيس فقط،
    // واستبعاد رحلة المصعد والقيم التشخيصية والمقاطع غير المقيسة.
    out.walking_distance_m=_r3(out.horizontal_m+out.stair_walking_m);
    out.walking_distance_exact_m=out.horizontal_exact_m+out.stair_walking_exact_m; }
  if(out.origin_basis==='space_centroid_fallback'&&out.distance_status==='COMPLETE')
    out.note='نقطة البداية/النهاية افتراضها مركز الفراغ — المسافة مقاسة من هندسة النموذج بهذا الافتراض المعلَن.';
  return out; }
function validateMeasurement(m){
  const issues=[]; if(!m||!Object.keys(m).length) return ['empty measurement'];
  if(m.units!=='m') issues.push('units must be metres');
  let total=0.0;
  (m.segments||[]).forEach(s=>{
    const ln=s.length_m; if(ln===null||ln===undefined) return;
    if(typeof ln!=='number'||ln!==ln){ issues.push('NaN length in segment '+s.type); return; }
    if(ln<0) issues.push('negative length in segment '+s.type);
    if(DIST_BASES.indexOf(s.basis)<0&&s.basis!=='not_walking_distance')
      issues.push('unknown measurement basis: '+s.basis);
    if(s.type==='in_space'||s.type==='door_transition') total+=ln; });
  if(Math.abs(total-Number(m.horizontal_m||0.0))>0.01)
    issues.push('segment sum '+total.toFixed(3)+' != horizontal_m '+Number(m.horizontal_m||0).toFixed(3));
  if(m.distance_status==='COMPLETE'&&(m.unmeasured_segments||[]).length)
    issues.push('COMPLETE with unmeasured segments');
  if(m.distance_status!=='COMPLETE'&&m.walking_distance_m!==null&&m.walking_distance_m!==undefined)
    issues.push('walking_distance_m must be null unless COMPLETE');
  (m.vertical_transport||[]).forEach(v=>{
    if(v.kind==='elevator'&&v.length_m) issues.push('elevator travel must not carry walking length'); });
  return issues; }
function distanceSummary(m){
  if(m.distance_status==='COMPLETE')
    return 'المسافة الهندسية المقاسة للمسار الحالي: '+_fx2(m.walking_distance_m)+' م (من هندسة النموذج).';
  if(m.distance_status==='PARTIAL')
    return 'تم قياس '+_fx2(m.measured_horizontal_m||0.0)+' م أفقياً من هندسة النموذج؛ بعض مقاطع المسار غير قابلة للقياس حالياً ('+
           ((m.unmeasured_segments||[]).length)+' مقطع).';
  if(m.distance_status==='GEOMETRY_NOT_SUPPORTED')
    return 'هندسة أحد الفراغات غير مستطيلة — لا يُقاس المسار عبرها بخط مستقيم.';
  return 'لم تُقَس مسافة المسار.'; }
/* ==================================================================
   المرحلة 2 — أساس محرّك قواعد الكود (بنية فقط، بلا أي محتوى تنظيمي).
   نسخة مطابقة لـ acs_rules.py، والسجلّ منسوخ حرفياً من acs_rules.json
   (يفرض التطابقَ اختبارُ الانحراف، فالمصدر يبقى واحداً).
   القواعد بيانات لا شيفرة: لا eval ولا تنفيذ تعابير ديناميكية إطلاقاً.
   لا قاعدة تنظيمية بلا دليل كامل. نقص البيانات لا يصير PASS ولا FAIL.
   المحرّك للقراءة فقط: لا يعدّل النموذج ولا يصلح شيئاً.
   ================================================================== */


export { ACS_PROJECT_CODE_CONTEXT, ACS_PROJECT_SCHEMA, ADMIN_ROLES, ARButton, AR_NUM, CLAIM_RE, CLAUSE_SEP, CONNECT_RE, CORRIDOR_ASPECT, DIST_BASES, DIST_STATUSES, DQ, EG_DESTINATIONS, EG_MARGIN, EG_PEOPLE, EG_PROBE, EG_SOURCES, EG_STATUSES, EG_USABLE, FLOOR_NAMES, FLS_LAYER_COLOR, GLTFExporter, LANE_MAT, LAYER_NAMES, LAYER_ORDER, MAT, MEP_DISC_COLOR, NAV_TRAVERSABLE, NEG_RE, OBJ_AR, OBJ_KIND_AR, OBJ_LIB, OBJ_MAT, OBJ_PARENT, OBJ_SYN_EXTRA, OBJ_UNKNOWN, OrbitControls, POINT_KINDS, PROV, RACK_DEF, REL_ADJ_TOL, REL_CORE_TOL, REL_DOOR_PROBE, REL_SOURCES, REL_STATUSES, REL_TOUCH_EPS, REL_TYPES, ROLE_COLOR, ROOM_KW, RoomEnvironment, STA_DEF, STRUCT_KIND_COLOR, Sky, TEXMAP, TEX_GEN, THREE, VRButton, ZONE_LIB, _AL, _AR_KEYS, _EN_KEYS, _OBJ_ALL_KEYS, _dsCentroid, _dsDist, _dsFindObject, _dsIsRect, _dsRect, _dsRooms, _dualCount, _egChars, _egFootprint, _egPeople, _egProbe, _egRect, _egSid, _fx2, _inSpaceLength, _levelElevation, _navCentroids, _navLevelsForTemplate, _navResolve, _objPoint, _pyRound, _r3, _relContains, _relGapOverlap, _relKind, _relLevelId, _relLevelsFor, _relRect, _relSpaceId, _stairGeometry, _viaDoor, _wordIn, activeBuilding, addBox, architectureOf, attachObjects, auditEgress, buildConveyor, buildDocks, buildLanes, buildNavGraph, buildObject, buildObjects, buildProjectRelationships, buildRacks, buildRelationships, buildRoom, buildStations, classifyReport, clauseMap, cleanName, compile, countNear, detectMeta, distanceSummary, dockOpenings, doorAnchor, edgeGeom, egressSummary, ensureElementIds, extractExits, findEgress, findPath, getMat, getTex, grain, hasRoomKW, hasRuleEvidence, isBuildingModel, isProjectModel, knownSpaces, acsBuildDefect, acsBuildDefects, acsBuildDefectsReset, acsList, acsRoomRect, matCache, measurePath, navIssues, navNodeId, negatedAt, noiseCanvas, normDigits, normEdge, normHex, numNear, objCoverage, objKind, objectsFromText, openU, parseDescription, pathSummary, projectEnvelope, relationshipSummary, requestedFloorsFromText, rnd, scaleBoxUV, slabStrips, stampMeta, statedNumbers, stripBidi, texCache, toProject, truthify, usableExits, validateExits, validateMeasurement, validatePath, validateRelationships, wallOpenings, warehouseFromText, warehouseModel };
