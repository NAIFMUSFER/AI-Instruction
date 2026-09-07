/** Bounded IFC4 architectural-space exchange, not a general BIM round-trip.
 * Unsupported space representations and transformations fail explicitly.
 * Other disciplines are not imported and are disclosed in the import review.
 */
import { VERSION, uid, round, assertModel, normalizeText } from './model.js';
import { authoringDefaults } from './authoring.js';
const reject=message=>{throw Error('IFC: '+message);};
const num=v=>{const s=String(v??'').trim();if(!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[Ee][+-]?\d+)?$/.test(s))return null;const n=Number(s);return Number.isFinite(n)?n:null;};
const ref=v=>{const m=String(v??'').trim().match(/^#(\d+)$/);return m?Number(m[1]):null;};
const refs=v=>[...String(v??'').matchAll(/#(\d+)/g)].map(m=>Number(m[1]));
function unquote(v=''){
 const text=String(v).trim();if(!text.startsWith("'")||!text.endsWith("'"))return '';
 const s=text.slice(1,-1).replaceAll("''", "'");let out='';
 for(let i=0;i<s.length;i++){
  if(s[i]!=='\\'){out+=s[i];continue;}
  if(s[i+1]==='\\'){out+='\\';i++;continue;}
  const marker=s.slice(i,i+4).toUpperCase(),step=marker==='\\X2\\'?4:marker==='\\X4\\'?8:0;
  if(!step)reject('ترميز نص STEP غير مدعوم.');
  const end=s.toUpperCase().indexOf('\\X0\\',i+4),hex=s.slice(i+4,end);
  if(end<0||!hex.length||hex.length%step||!/^[0-9A-F]+$/i.test(hex))reject('ترميز Unicode غير صالح.');
  for(let j=0;j<hex.length;j+=step){const point=parseInt(hex.slice(j,j+step),16);if(step===8&&(point>0x10ffff||(point>=0xd800&&point<=0xdfff)))reject('قيمة Unicode غير صالحة.');out+=step===8?String.fromCodePoint(point):String.fromCharCode(point);}
  i=end+3;
 }
 return out;
}
function splitTop(text){const out=[];let start=0,depth=0,quote=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==="'"){if(quote&&text[i+1]==="'"){i++;continue;}quote=!quote;continue;}if(quote)continue;if(c==='('){if(++depth>64)reject('التداخل يتجاوز الحد المسموح.');}else if(c===')'){if(--depth<0)reject('أقواس STEP غير متوازنة.');}else if(c===','&&depth===0){out.push(text.slice(start,i).trim());start=i+1;}}if(quote||depth)reject('قيمة STEP غير مكتملة.');out.push(text.slice(start).trim());return out;}
function stripComments(text){let out='',quote=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==="'"){out+=c;if(quote&&text[i+1]==="'"){out+=text[++i];continue;}quote=!quote;continue;}if(!quote&&c==='/'&&text[i+1]==='*'){const end=text.indexOf('*/',i+2);if(end<0)reject('تعليق STEP غير مكتمل.');i=end+1;out+=' ';}else out+=c;}if(quote)reject('نص STEP غير مكتمل.');return out;}
function entities(text){const map=new Map();let start=0,quote=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==="'"){if(quote&&text[i+1]==="'"){i++;continue;}quote=!quote;}else if(c===';'&&!quote){const s=text.slice(start,i).trim();start=i+1;if(!s.startsWith('#'))continue;const m=s.match(/^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\(([\s\S]*)\)$/i);if(!m)reject('كيان STEP غير مدعوم.');const id=Number(m[1]);if(map.has(id)||map.size>=60000)reject('معرف كيان مكرر أو عدد كيانات يتجاوز الحد.');map.set(id,{id,type:m[2].toUpperCase(),args:splitTop(m[3])});}}return map;}
function get(map,id,type){const e=map.get(id);if(!e||(type&&e.type!==type))reject(`مرجع مفقود أو نوع غير مدعوم: #${id} (${type||'entity'}).`);return e;}
function vector(map,id,type,dimension=3){const e=get(map,id,type),s=e.args[0];if(!s?.startsWith('(')||!s.endsWith(')'))reject('إحداثيات غير صالحة.');const a=splitTop(s.slice(1,-1)).map(num);if(a.length<2||a.length>dimension||a.some(v=>v===null))reject('إحداثيات غير صالحة.');return dimension===3?[a[0],a[1],a[2]??0]:a;}
const near=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<1e-8);
function axis(map,id,dimension=3,allowQuarterTurn=false){
 const e=get(map,id,dimension===3?'IFCAXIS2PLACEMENT3D':'IFCAXIS2PLACEMENT2D'),p=vector(map,ref(e.args[0]),'IFCCARTESIANPOINT',dimension);
 if(dimension===3&&e.args[1]!=='$'&&!near(vector(map,ref(e.args[1]),'IFCDIRECTION'),[0,0,1]))reject('المحور المائل غير مدعوم.');
 const direction=e.args[dimension===3?2:1];
 if(direction&&direction!=='$'){const d=vector(map,ref(direction),'IFCDIRECTION',dimension),x=dimension===3?[1,0,0]:[1,0],y=dimension===3?[0,1,0]:[0,1];if(!near(d,x)&&!(allowQuarterTurn&&near(d,y)))reject('دوران هذا العنصر غير مدعوم؛ لم تُغيّر إحداثياته بصمت.');}
 return p;
}
function placement(map,id,allowQuarterTurn=false,seen=new Set()){
 if(id===null)return{x:0,y:0,z:0,parent:null};if(seen.has(id)||seen.size>24)reject('دورة أو عمق زائد في مواضع العناصر.');seen.add(id);
 const e=get(map,id,'IFCLOCALPLACEMENT'),parent=ref(e.args[0]);if(parent===null&&e.args[0]!=='$')reject('موضع أب غير صالح.');
 const p=axis(map,ref(e.args[1]),3,allowQuarterTurn),base=placement(map,parent,false,seen);
 return{x:p[0]+base.x,y:p[1]+base.y,z:p[2]+base.z,parent};
}
function shape(map,id){
 const pds=get(map,id,'IFCPRODUCTDEFINITIONSHAPE'),rs=refs(pds.args[2]);
 const bodies=rs.map(r=>get(map,r,'IFCSHAPEREPRESENTATION')).filter(r=>unquote(r.args[1])==='Body');
 if(bodies.length!==1)reject('يجب أن تحتوي المساحة على تمثيل Body واحد مدعوم.');
 const items=refs(bodies[0].args[3]);if(items.length!==1)reject('تعدد مجسمات المساحة غير مدعوم.');
 const solid=get(map,items[0],'IFCEXTRUDEDAREASOLID'),h=num(solid.args[3]);if(!h||h<=0)reject('ارتفاع extrusion غير صالح.');
 if(!near(vector(map,ref(solid.args[2]),'IFCDIRECTION'),[0,0,1]))reject('اتجاه extrusion غير عمودي.');
 const p=solid.args[1]==='$'?[0,0,0]:axis(map,ref(solid.args[1])),profile=get(map,ref(solid.args[0]));
 if(profile.type==='IFCRECTANGLEPROFILEDEF'){
  const w=num(profile.args[3]),d=num(profile.args[4]);if(!w||!d||w<=0||d<=0)reject('أبعاد profile غير صالحة.');
  const c=profile.args[2]==='$'?[0,0]:axis(map,ref(profile.args[2]),2);
  return{kind:'rect',w,d,height:h,x:p[0]+c[0],y:p[1]+c[1],z:p[2]};
 }
 if(profile.type==='IFCARBITRARYCLOSEDPROFILEDEF'){
  const pl=get(map,ref(profile.args[2]),'IFCPOLYLINE'),ids=refs(pl.args[0]);if(ids.length<5||ids.length>25)reject('عدد نقاط المضلع غير مدعوم.');
  let points=ids.map(id=>vector(map,id,'IFCCARTESIANPOINT'));
  if(!near(points[0],points.at(-1)))reject('منحنى profile ليس مغلقًا.');points=points.slice(0,-1);
  if(points.some(pt=>Math.abs(pt[2])>1e-8))reject('profile غير مستوٍ.');
  return{kind:'poly',points:points.map(pt=>[pt[0]+p[0],pt[1]+p[1]]),height:h,z:p[2]};
 }
 reject(`profile غير مدعوم: ${profile.type}.`);
}
function lengthScale(map){
 const projects=[...map.values()].filter(e=>e.type==='IFCPROJECT');if(projects.length!==1)reject('يتطلب المستورد مشروع IFC واحدًا.');
 const units=get(map,ref(projects[0].args[8]),'IFCUNITASSIGNMENT'),lengths=refs(units.args[0]).map(id=>get(map,id)).filter(u=>u.args[1]==='.LENGTHUNIT.');
 if(lengths.length!==1||lengths[0].type!=='IFCSIUNIT'||lengths[0].args[3]!=='.METRE.')reject('وحدة طول SI بالمتر ومضاعفاته مطلوبة.');
 const factor={'$':1,'.MILLI.':.001,'.CENTI.':.01,'.DECI.':.1}[lengths[0].args[2]];if(!factor)reject('بادئة وحدة الطول غير مدعومة.');return factor;
}
function inferKind(name){const t=normalizeText(name);const cases=[['bedroom',/غرفه نوم|bedroom/],['majlis',/مجلس|majlis/],['living',/معيش|living|family/],['kitchen',/مطبخ|kitchen/],['bath',/دوره مياه|حمام|bath|toilet|wc/],['stairs',/درج|stair/],['elevator',/مصعد|lift|elevator/],['hall',/ممر|مدخل|hall|corridor/],['dining',/طعام|dining/],['meeting',/اجتماع|meeting/],['reception',/استقبال|reception/],['warehouse',/مستودع|warehouse/],['loading',/تحميل|loading/],['retail',/تجزئ|صاله العرض|retail|shop/],['office',/مكتب|office/],['storage',/مخزن|storage/]];return cases.find(([,re])=>re.test(t))?.[0]||'service';}
function sideFor(room,p){const candidates=[['west',Math.abs(p.x-room.x)],['east',Math.abs(p.x-room.x-room.w)],['south',Math.abs(p.y-room.y)],['north',Math.abs(p.y-room.y-room.d)]].sort((a,b)=>a[1]-b[1]);if(candidates[0][1]>.003)reject('فتحة موسومة لا تقع على ضلع غرفة مدعوم.');return candidates[0][0];}
export function parseIFC(text){
 if(typeof text!=='string'||text.length>8000000)reject('الملف غير صالح أو يتجاوز 8 ميجابايت.');
 const meta=text.match(/\/\*\s*MASAR_SITE\s+([\d.+-]+)\s+([\d.+-]+)\s+(شمال|جنوب|شرق|غرب)/),clean=stripComments(text);
 if(!/^\s*ISO-10303-21;/i.test(clean)||!/FILE_SCHEMA\s*\(\s*\(\s*'IFC4'\s*\)\s*\)/i.test(clean)||!/END-ISO-10303-21;\s*$/i.test(clean))reject('يتطلب ملف IFC4 STEP كاملًا.');
 const map=entities(clean),scale=lengthScale(map),storeys=[],levelByPlacement=new Map(),rooms=new Map();
 for(const e of map.values())if(e.type==='IFCBUILDINGSTOREY'){
  const lp=ref(e.args[5]),p=placement(map,lp),level={id:`ifc-level-${e.id}`,name:unquote(e.args[2])||`Storey ${e.id}`,elevation:round(p.z*scale),height:3.3,rooms:[]};
  storeys.push(level);levelByPlacement.set(lp,level);
 }
 if(!storeys.length||storeys.length>8)reject('عدد الأدوار غير مدعوم.');storeys.sort((a,b)=>a.elevation-b.elevation);
 for(const e of map.values())if(e.type==='IFCSPACE'){
  const lp=placement(map,ref(e.args[5])),level=levelByPlacement.get(lp.parent);if(!level)reject('المساحة ليست مرتبطة مباشرة بدور مدعوم.');
  const s=shape(map,ref(e.args[6]));if(Math.abs((lp.z+s.z)*scale-level.elevation)>.003)reject('المساحة لها إزاحة رأسية عن الدور غير مدعومة.');
  const tag=unquote(e.args[7]),tagId=tag.startsWith('MASAR_ROOM:')?tag.slice(11):null,id=tagId&&tagId.length<100?tagId:`ifc-space-${e.id}`;
  if(rooms.has(id)||rooms.size>=200)reject('معرف مساحة مكرر أو عدد مساحات زائد.');
  const name=unquote(e.args[2])||`Space ${e.id}`,r={id,name,kind:inferKind(name),height:round(s.height*scale),locked:false,doors:[],windows:[],note:'',provenance:'imported-ifc4-space'};
  if(s.kind==='rect')Object.assign(r,{x:round((lp.x+s.x-s.w/2)*scale),y:round((lp.y+s.y-s.d/2)*scale),w:round(s.w*scale),d:round(s.d*scale)});
  else{r.footprint=s.points.map(p=>[round((p[0]+lp.x)*scale),round((p[1]+lp.y)*scale)]);const xs=r.footprint.map(p=>p[0]),ys=r.footprint.map(p=>p[1]);Object.assign(r,{x:Math.min(...xs),y:Math.min(...ys),w:round(Math.max(...xs)-Math.min(...xs)),d:round(Math.max(...ys)-Math.min(...ys))});}
  level.rooms.push(r);rooms.set(id,{room:r,level});
 }
 if(!rooms.size)reject('لا توجد مساحات IfcSpace مدعومة.');const levels=storeys.filter(l=>l.rooms.length);
 for(let i=0;i<levels.length;i++){const h=Math.max(...levels[i].rooms.map(r=>r.height)),gap=levels[i+1]?.elevation-levels[i].elevation;levels[i].height=round(Number.isFinite(gap)?gap:Math.max(2,h));if(levels[i].height<h-.003)reject('ارتفاع المساحة يتجاوز منسوب الدور التالي.');}
 let skippedOpenings=0;
 for(const e of map.values())if(e.type==='IFCDOOR'||e.type==='IFCWINDOW'){
  const tag=unquote(e.args[7]);if(!tag.startsWith('MASAR_ROOM:')){skippedOpenings++;continue;}
  const [roomId,itemId]=tag.slice(11).split('|'),target=rooms.get(roomId);if(!target)reject('غرفة الفتحة الموسومة غير موجودة.');
  const {room:r,level}=target,lp=placement(map,ref(e.args[5]),true),p={x:lp.x*scale,y:lp.y*scale,z:lp.z*scale},side=sideFor(r,p),offset=round(['east','west'].includes(side)?(p.y-r.y)/r.d:(p.x-r.x)/r.w),width=num(e.args[9]),height=num(e.args[8]);
  if(!width||!height||offset<0||offset>1)reject('أبعاد الفتحة الموسومة غير صالحة.');
  const base={id:itemId||`${r.id}-opening-${e.id}`,side,offset,width:round(width*scale),height:round(height*scale),provenance:'imported-ifc4-opening'};
  if(e.type==='IFCDOOR'){if(Math.abs(p.z-level.elevation)>.003)reject('عتبة الباب غير مدعومة.');r.doors.push({...base,entry:/entrance/i.test(unquote(e.args[2]))});}
  else r.windows.push({...base,sill:round(p.z-level.elevation),typeId:'window-concept-1200',locked:false});
 }
 const all=levels.flatMap(l=>l.rooms),minX=Math.min(...all.map(r=>r.x)),minY=Math.min(...all.map(r=>r.y)),dx=minX<0?round(1-minX):0,dy=minY<0?round(1-minY):0;
 if(dx||dy)for(const r of all){r.x=round(r.x+dx);r.y=round(r.y+dy);if(r.footprint)r.footprint=r.footprint.map(p=>[round(p[0]+dx),round(p[1]+dy)]);}
 const maxX=Math.max(...all.map(r=>r.x+r.w)),maxY=Math.max(...all.map(r=>r.y+r.d)),mw=meta?num(meta[1]):null,md=meta?num(meta[2]):null,width=mw&&mw>=maxX?mw:Math.max(4,Math.ceil(maxX+1)),depth=md&&md>=maxY?md:Math.max(4,Math.ceil(maxY+1)),street=meta?.[3]||'جنوب';
 const notes=['استُوردت المساحات والفتحات الموسومة المدعومة فقط. الجدران أُعيد اشتقاقها بأنواع مفاهيمية وليست طبقات IFC الأصلية. تاريخ المشروع ومتطلباته والتخصصات الأخرى لم تُستورد.',`فتحات غير موسومة لم تُستورد: ${skippedOpenings}.`];
 if(dx||dy)notes.push(`نُقل الأصل المرجعي بمقدار ${dx} م شرقًا و${dy} م شمالًا لإدخاله في مجال الموقع؛ راجع الإحداثيات.`);
 const m={schemaVersion:VERSION,id:uid(),title:'مشروع IFC مستورد',authoring:authoringDefaults(),site:{width,depth,street,north:'up',setback:{front:0,back:0,left:0,right:0},setbackSource:'unknown-from-ifc-import',features:[]},brief:{prompt:'Imported IFC4 subset; original client brief unavailable.',width,depth,floors:levels.length,bedrooms:all.filter(r=>r.kind==='bedroom').length,offices:all.filter(r=>r.kind==='office').length,parking:0,street,projectType:'villa',sources:{width:meta?'imported':'assumed-envelope',depth:meta?'imported':'assumed-envelope',floors:'imported',bedrooms:'inferred-from-name',offices:'inferred-from-name',parking:'unknown',street:meta?'imported':'assumed',projectType:'unknown'},intents:[],unresolved:notes},requirements:[{id:'r-ifc-import',label:'مراجعة الهندسة والأنواع المستنتجة والوحدات وعلاقات IFC قبل الاعتماد',type:'custom',locked:true,source:'imported'}],levels,comments:[],references:[],design:{stage:'development',projectType:'villa',priority:'balanced',style:'unspecified',generatedVariant:0,importMode:'ifc4-space-authoring',importTransform:{scaleToMetres:scale,dx,dy,skippedOpenings}},createdAt:new Date().toISOString()};
 return assertModel(m);
}
