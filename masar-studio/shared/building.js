/**
 * MASAR derived building graph and exchange helpers.
 * These functions derive coordination/BIM-lite elements from the canonical room model.
 * The canonical model remains the source of truth; derived elements never write back.
 */
import { area, centroid, doorPoint, roomPolygon, windowPoint, requirementStatus, round, totals, validate } from './model.js';
import { effectiveAuthoring, wallTypeFor, windowTypeFor } from './authoring.js';

const EPS = 0.002;
const q = n => round(Number(n));
const keyNum = n => q(n).toFixed(3);
// STEP uses UCS-2 for BMP and UCS-4 for supplementary characters, never UTF-16 surrogate pairs.
const escStep = value => "'"+Array.from(String(value??'').replace(/[\r\n]/g,' ')).map(c=>{
  if(c==="'")return "''";if(c==='\\')return '\\\\';const point=c.codePointAt(0);
  if(point>0xffff)return '\\X4\\'+point.toString(16).toUpperCase().padStart(8,'0')+'\\X0\\';
  return point>126||point<32?'\\X2\\'+point.toString(16).toUpperCase().padStart(4,'0')+'\\X0\\':c;
}).join('')+"'";
export function csvCell(value) {
  let text=String(value??'');
  // User labels are data, never spreadsheet formulas. Numeric geometry remains numeric.
  if(typeof value==='string'&&/^[\s\u0000-\u001f]*[=+@-]/.test(text))text="'"+text;
  return '"'+text.replaceAll('"','""')+'"';
}
const csv=csvCell;

function roomEdges(room) {
  if (!room.footprint) return [
    { side:'south', axis:'h', coord:q(room.y), start:q(room.x), end:q(room.x + room.w) },
    { side:'north', axis:'h', coord:q(room.y + room.d), start:q(room.x), end:q(room.x + room.w) },
    { side:'west', axis:'v', coord:q(room.x), start:q(room.y), end:q(room.y + room.d) },
    { side:'east', axis:'v', coord:q(room.x + room.w), start:q(room.y), end:q(room.y + room.d) }
  ];
  const poly=roomPolygon(room), out=[];
  for(let i=0;i<poly.length;i++){
    const a=poly[i],b=poly[(i+1)%poly.length];
    if(Math.abs(a[1]-b[1])<=EPS) out.push({side:`edge-${i}`,axis:'h',coord:q(a[1]),start:q(Math.min(a[0],b[0])),end:q(Math.max(a[0],b[0]))});
    else out.push({side:`edge-${i}`,axis:'v',coord:q(a[0]),start:q(Math.min(a[1],b[1])),end:q(Math.max(a[1],b[1]))});
  }
  return out;
}

function edgeContains(edge, axis, coord, start, end) {
  return edge.axis === axis && Math.abs(edge.coord - coord) <= EPS && start >= edge.start - EPS && end <= edge.end + EPS;
}

/**
 * Atomize room edges into non-overlapping wall segments. A segment knows every adjacent room.
 * Stable IDs are geometry-derived; they remain stable while the underlying wall geometry is unchanged.
 */
export function deriveWalls(model) {
  const walls = [];
  for (const level of model.levels) {
    const edges = level.rooms.flatMap(room => roomEdges(room).map(edge => ({ ...edge, roomId:room.id, roomName:room.name })));
    const grouped = new Map();
    for (const e of edges) {
      const k = `${e.axis}:${keyNum(e.coord)}`;
      if (!grouped.has(k)) grouped.set(k, []);
      grouped.get(k).push(e);
    }
    for (const [lineKey, lineEdges] of grouped) {
      const points = [...new Set(lineEdges.flatMap(e => [keyNum(e.start), keyNum(e.end)]))].map(Number).sort((a,b)=>a-b);
      for (let i=1;i<points.length;i++) {
        const start=q(points[i-1]), end=q(points[i]);
        if (end-start <= EPS) continue;
        const mid=(start+end)/2;
        const touching=lineEdges.filter(e=>mid >= e.start-EPS && mid <= e.end+EPS);
        if (!touching.length) continue;
        const [axis,coordText]=lineKey.split(':'), coord=Number(coordText);
        const roomIds=[...new Set(touching.map(e=>e.roomId))].sort();
        const sideByRoom=Object.fromEntries(touching.map(e=>[e.roomId,e.side]));
        const id=`wall:${level.id}:${axis}:${keyNum(coord)}:${keyNum(start)}:${keyNum(end)}`;
        const external=roomIds.length===1, wallType=wallTypeFor(model,external);
        walls.push({
          id, levelId:level.id, axis, coord:q(coord), start, end, length:q(end-start), height:q(level.height || 3), thickness:q(wallType.totalThickness), wallTypeId:wallType.id, wallTypeName:wallType.name, layers:structuredClone(wallType.layers),
          external, adjacentRoomIds:roomIds, sideByRoom, provenance:'derived-from-space-boundaries+authoring-wall-type'
        });
      }
    }
  }
  return walls.sort((a,b)=>a.levelId.localeCompare(b.levelId)||a.id.localeCompare(b.id));
}

export function deriveOpenings(model, walls = deriveWalls(model)) {
  const byLevel = new Map();
  for (const w of walls) { if (!byLevel.has(w.levelId)) byLevel.set(w.levelId, []); byLevel.get(w.levelId).push(w); }
  const openings=[];
  const addOpening=(level,room,item,type)=>{
    const point=type==='door'?doorPoint(room,item):windowPoint(room,item), [px,py]=point, vertical=['west','east'].includes(item.side), axis=vertical?'v':'h', coord=vertical?px:py, along=vertical?py:px;
    const host=(byLevel.get(level.id)||[]).find(w=>w.axis===axis&&Math.abs(w.coord-coord)<=EPS&&along-item.width/2>=w.start-EPS&&along+item.width/2<=w.end+EPS&&w.adjacentRoomIds.includes(room.id));
    const base={id:item.id,type,levelId:level.id,roomId:room.id,hostWallId:host?.id||null,side:item.side,width:q(item.width),height:q(item.height??(type==='door'?2.15:windowTypeFor(model,item.typeId)?.height||1.2)),offset:q(item.offset),x:q(px),y:q(py),z:q(level.elevation),provenance:item.provenance||room.provenance||'generated-concept'};
    if(type==='door') Object.assign(base,{entry:!!item.entry,sill:0}); else Object.assign(base,{entry:false,sill:q(item.sill??0.9),typeId:item.typeId||effectiveAuthoring(model).defaults.windowTypeId});
    openings.push(base);
  };
  for(const level of model.levels) for(const room of level.rooms){ for(const door of room.doors||[])addOpening(level,room,door,'door'); for(const win of room.windows||[])addOpening(level,room,win,'window'); }
  return openings.sort((a,b)=>a.levelId.localeCompare(b.levelId)||a.id.localeCompare(b.id));
}
function levelBounds(level) {
  const xs=level.rooms.flatMap(r=>[r.x,r.x+r.w]), ys=level.rooms.flatMap(r=>[r.y,r.y+r.d]);
  return { x:q(Math.min(...xs)), y:q(Math.min(...ys)), w:q(Math.max(...xs)-Math.min(...xs)), d:q(Math.max(...ys)-Math.min(...ys)) };
}

function levelEnvelopes(level) {
  const groups=new Map();
  for(const room of level.rooms){const key=room.buildingGroup||'main';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(room);}
  return [...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([group,rooms])=>({...levelBounds({rooms}),buildingGroup:group}));
}
export function deriveBuildingGraph(model) {
  const walls=deriveWalls(model), openings=deriveOpenings(model,walls);
  const spaces=model.levels.flatMap(level=>level.rooms.map(room=>({ id:room.id, levelId:level.id, type:'space', name:room.name, kind:room.kind, x:room.x,y:room.y,z:level.elevation,w:room.w,d:room.d,h:room.height,area:area(room),footprint:room.footprint?structuredClone(room.footprint):null,locked:!!room.locked,provenance:room.provenance || 'unknown' })));
  const slabs=model.levels.flatMap(level=>levelEnvelopes(level).map((bounds,i)=>({id:`slab:${level.id}${i?':part-'+i:''}`,levelId:level.id,type:'slab',name:`بلاطة ${level.name}`, ...bounds,z:q(level.elevation-.16),h:.16,provenance:'derived-building-group-envelope'})));
  const top=model.levels.at(-1),roofs=levelEnvelopes(top).map((bounds,i)=>({id:`roof:${top.id}${i?':part-'+i:''}`,levelId:top.id,type:'roof',name:'سطح/سقف علوي مفاهيمي',...bounds,z:q(top.elevation+(top.height||3)),h:.16,provenance:'derived-building-group-envelope'}));
  const siteFeatures=(model.site.features || []).map(f=>({ ...f, id:f.id || `feature:${f.type}:${f.x}:${f.y}`, type:f.type, levelId:null, provenance:f.provenance || 'generated-concept' }));
  const elements={ walls, openings, spaces, slabs, roofs, siteFeatures };
  const counts=Object.fromEntries(Object.entries(elements).map(([k,v])=>[k,v.length])); counts.doors=openings.filter(o=>o.type==='door').length; counts.windows=openings.filter(o=>o.type==='window').length;
  return { schema:'masar-derived-building-2', modelId:model.id, title:model.title, generatedAt:new Date().toISOString(), sourceSchemaVersion:model.schemaVersion, units:'m', counts, elements, disclaimer:'Derived coordination model. Not a construction or code-compliance model.' };
}

export function elementSchedule(model) {
  const g=deriveBuildingGraph(model), levels=new Map(model.levels.map(l=>[l.id,l.name]));
  const rows=[];
  for (const r of g.elements.spaces) rows.push({category:'Space',id:r.id,level:levels.get(r.levelId),name:r.name,type:r.kind,length:'',width:r.w,height:r.h,area:r.area,external:'',host:'',provenance:r.provenance});
  for (const w of g.elements.walls) rows.push({category:'Wall',id:w.id,level:levels.get(w.levelId),name:w.external?'جدار خارجي مشتق':'جدار داخلي مشتق',type:w.axis==='h'?'horizontal':'vertical',length:w.length,width:w.thickness,height:w.height,area:q(w.length*w.height),external:w.external?'yes':'no',host:w.adjacentRoomIds.join('|'),provenance:w.provenance});
  for (const o of g.elements.openings) rows.push({category:o.type==='window'?'Window':'Door',id:o.id,level:levels.get(o.levelId),name:o.type==='window'?'نافذة':(o.entry?'باب دخول':'باب'),type:o.type,length:'',width:o.width,height:o.height,area:q(o.width*o.height),external:o.type==='window'||o.entry?'yes':'',host:o.hostWallId || '',provenance:o.provenance});
  for (const s of g.elements.slabs) rows.push({category:'Slab',id:s.id,level:levels.get(s.levelId),name:s.name,type:'slab',length:s.d,width:s.w,height:s.h,area:q(s.w*s.d),external:'',host:'',provenance:s.provenance});
  for (const r of g.elements.roofs) rows.push({category:'Roof',id:r.id,level:levels.get(r.levelId),name:r.name,type:'roof',length:r.d,width:r.w,height:r.h,area:q(r.w*r.d),external:'yes',host:'',provenance:r.provenance});
  return rows;
}

export function elementScheduleCSV(model) {
  const headers=['Category','ID','Level','Name','Type','Length_m','Width_m','Height_m','Area_m2','External','Host_or_Adjacent','Provenance'];
  const rows=elementSchedule(model).map(r=>[r.category,r.id,r.level,r.name,r.type,r.length,r.width,r.height,r.area,r.external,r.host,r.provenance]);
  return '\uFEFF'+[headers,...rows].map(row=>row.map(csv).join(',')).join('\r\n');
}

export function requirementMatrix(model) {
  return (model.requirements || []).map(req=>{
    const status=requirementStatus(model,req);
    return { id:req.id, label:req.label, type:req.type, source:req.source || 'unknown', locked:!!req.locked, measurable:!!status.measurable, satisfied:status.measurable ? !!status.satisfied : null, detail:status.detail || '', review:status.measurable ? (status.satisfied?'satisfied':'needs-improvement') : 'human-review' };
  });
}

export function requirementMatrixCSV(model) {
  const rows=[['Requirement_ID','Label','Type','Source','Locked','Measurable','Satisfied','Review','Detail'],...requirementMatrix(model).map(r=>[r.id,r.label,r.type,r.source,r.locked,r.measurable,r.satisfied===null?'':r.satisfied,r.review,r.detail])];
  return '\uFEFF'+rows.map(row=>row.map(csv).join(',')).join('\r\n');
}

export const MASAR_RULE_PACK = Object.freeze({
  id:'masar-authoring-quality-2026.2', version:'2026.2', name:'MASAR Authoring Quality',
  authority:'product-heuristic', compliance:false,
  disclaimer:'قواعد جودة مفاهيمية داخل MASAR وليست اشتراطات SBC أو اعتمادًا هندسيًا.',
  rules:[
    {id:'space-positive',label:'المساحات موجبة',scope:'space',severity:'error'},
    {id:'door-host',label:'كل باب مرتبط بجدار مشتق',scope:'door',severity:'error'},
    {id:'door-concept-width',label:'عرض الباب المفاهيمي 0.80م أو أكثر',scope:'door',severity:'warning'},
    {id:'window-host',label:'كل نافذة مرتبطة بجدار مشتق',scope:'window',severity:'error'},
    {id:'window-external',label:'النافذة المفاهيمية على جدار خارجي',scope:'window',severity:'warning'},
    {id:'wall-layer-sum',label:'مجموع طبقات نوع الجدار يطابق سماكته',scope:'wall-type',severity:'error'},
    {id:'small-room',label:'تنبيه للمساحات الأصغر من حد الراحة المفاهيمي',scope:'space',severity:'warning'},
    {id:'circulation-share',label:'نسبة الحركة لا تتجاوز 25% كمؤشر كفاءة مفاهيمي',scope:'project',severity:'warning'},
    {id:'requirements',label:'المتطلبات القابلة للقياس محققة',scope:'requirement',severity:'warning'}
  ]
});

const minimumConceptArea={ bedroom:7, majlis:10, living:9, kitchen:5, dining:6, office:5, meeting:7, bath:2, retail:8, warehouse:20, reception:5 };
export function evaluateRulePack(model, pack=MASAR_RULE_PACK) {
  if (!pack || pack.compliance !== false || pack.authority !== 'product-heuristic') throw Error('حزمة القواعد غير مصرح بها كمؤشرات مفاهيمية.');
  const g=deriveBuildingGraph(model), results=[];
  for (const space of g.elements.spaces) {
    results.push({ruleId:'space-positive',status:space.area>0?'pass':'fail',severity:'error',targets:[space.id],message:space.area>0?`${space.name}: مساحة موجبة.`:`${space.name}: مساحة غير صالحة.`});
    const min=minimumConceptArea[space.kind];
    if (min) results.push({ruleId:'small-room',status:space.area>=min?'pass':'review',severity:'warning',targets:[space.id],message:space.area>=min?`${space.name}: ${space.area} م² ضمن حد الراحة المفاهيمي الداخلي.`:`${space.name}: ${space.area} م² أقل من ${min} م² كتنبيه جودة مفاهيمي، وليس مخالفة كود.`});
  }
  for (const opening of g.elements.openings) {
    if(opening.type==='door'){
      results.push({ruleId:'door-host',status:opening.hostWallId?'pass':'fail',severity:'error',targets:[opening.id,opening.roomId],message:opening.hostWallId?'الباب مرتبط بجدار مشتق.':'الباب بلا جدار مضيف مشتق.'});
      results.push({ruleId:'door-concept-width',status:opening.width>=.8?'pass':'review',severity:'warning',targets:[opening.id,opening.roomId],message:opening.width>=.8?`عرض الباب ${opening.width}م.`:`عرض الباب ${opening.width}م أقل من 0.80م كتنبيه مفاهيمي فقط.`});
    } else {
      const host=g.elements.walls.find(w=>w.id===opening.hostWallId);
      results.push({ruleId:'window-host',status:opening.hostWallId?'pass':'fail',severity:'error',targets:[opening.id,opening.roomId],message:opening.hostWallId?'النافذة مرتبطة بجدار مشتق.':'النافذة بلا جدار مضيف مشتق.'});
      results.push({ruleId:'window-external',status:host?.external?'pass':'review',severity:'warning',targets:[opening.id,opening.roomId],message:host?.external?'النافذة على حد خارجي مشتق.':'النافذة ليست على جدار خارجي في النموذج الحالي؛ راجعها.'});
    }
  }
  for(const wt of effectiveAuthoring(model).wallTypes){const sum=wt.layers.reduce((n,l)=>n+Number(l.thickness),0),ok=Math.abs(sum-wt.totalThickness)<=.002;results.push({ruleId:'wall-layer-sum',status:ok?'pass':'fail',severity:'error',targets:[wt.id],message:ok?`${wt.name}: مجموع الطبقات ${q(sum)}م يطابق السماكة.`:`${wt.name}: مجموع الطبقات لا يطابق السماكة الكلية.`});}
  const t=totals(model);
  results.push({ruleId:'circulation-share',status:t.circulationPct<=25?'pass':'review',severity:'warning',targets:[],message:`نسبة الحركة ${t.circulationPct}%؛ حد المقارنة الداخلي 25% وليس اشتراطًا تنظيميًا.`});
  for (const req of requirementMatrix(model).filter(r=>r.measurable)) results.push({ruleId:'requirements',status:req.satisfied?'pass':'review',severity:'warning',targets:[req.id],message:`${req.label}: ${req.satisfied?'محقق في النموذج الحالي':'يحتاج تحسينًا في النموذج الحالي'}.`});
  const structural=validate(model).filter(i=>i.status==='error').map(i=>({ruleId:'canonical-validation',status:'fail',severity:'error',targets:i.targets,message:i.message}));
  results.push(...structural);
  const summary={pass:results.filter(r=>r.status==='pass').length,review:results.filter(r=>r.status==='review').length,fail:results.filter(r=>r.status==='fail').length,unchecked:validate(model).filter(i=>i.status==='unchecked').length};
  return { pack:{id:pack.id,version:pack.version,name:pack.name,authority:pack.authority,compliance:false,disclaimer:pack.disclaimer}, summary, results, evaluatedAt:new Date().toISOString(), modelId:model.id };
}

function hash128(text) {
  const bytes=new Uint8Array(16);
  let a=0x811c9dc5>>>0,b=0x9e3779b9>>>0,c=0x85ebca6b>>>0,d=0xc2b2ae35>>>0;
  for (let i=0;i<text.length;i++) { const x=text.charCodeAt(i); a=Math.imul(a^x,0x01000193)>>>0; b=Math.imul(b+(x^i),0x85ebca6b)>>>0; c=Math.imul(c^(x+a),0xc2b2ae35)>>>0; d=Math.imul(d+(x^b),0x27d4eb2d)>>>0; }
  for (const [j,n] of [a,b,c,d].entries()) { bytes[j*4]=(n>>>24)&255; bytes[j*4+1]=(n>>>16)&255; bytes[j*4+2]=(n>>>8)&255; bytes[j*4+3]=n&255; }
  return bytes;
}
const IFC64='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$';
export function ifcGuid(seed) {
  const bytes=hash128(String(seed)); let n=0n; for (const b of bytes) n=(n<<8n)|BigInt(b); let out=''; for (let i=0;i<22;i++) { out=IFC64[Number(n&63n)]+out; n>>=6n; } return out;
}

/**
 * IFC4 coordination export. It intentionally exports conceptual spaces/walls/slabs/roof geometry.
 * It is not advertised as an IFC authoring round-trip or code-compliant BIM model.
 */
export function exportIFC(model) {
  const g=deriveBuildingGraph(model);
  if(g.elements.openings.some(o=>!o.hostWallId))throw Error('IFC: فتحة تعبر نهاية جدار مضيف؛ راجع موضعها قبل التصدير.');
  const lines=[], add=x=>{lines.push(`#${lines.length+1}=${x};`);return lines.length;};
  const origin=add("IFCCARTESIANPOINT((0.,0.,0.))"), axis=add(`IFCAXIS2PLACEMENT3D(#${origin},$,$)`), person=add(`IFCPERSON($,$,'MASAR',$,$,$,$,$)`), org=add(`IFCORGANIZATION($,'MASAR Studio',$,$,$)`), pao=add(`IFCPERSONANDORGANIZATION(#${person},#${org},$)`), app=add(`IFCAPPLICATION(#${org},'4.1.0','MASAR Studio','MASAR')`), owner=add(`IFCOWNERHISTORY(#${pao},#${app},$,.ADDED.,${Math.floor(Date.now()/1000)},#${pao},#${app},${Math.floor(Date.now()/1000)})`);
  const lengthUnit=add("IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.)"), areaUnit=add("IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)"), volumeUnit=add("IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)"), units=add(`IFCUNITASSIGNMENT((#${lengthUnit},#${areaUnit},#${volumeUnit}))`), context=add(`IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#${axis},$)`);
  const project=add(`IFCPROJECT(${escStep(ifcGuid('project:'+model.id))},#${owner},${escStep(model.title)},'MASAR authoring coordination export',$,$,$,(#${context}),#${units})`), sitePlacement=add(`IFCLOCALPLACEMENT($,#${axis})`), site=add(`IFCSITE(${escStep(ifcGuid('site:'+model.id))},#${owner},'Site',$,$,#${sitePlacement},$,$,.ELEMENT.,$,$,$,$,$)`), buildingPlacement=add(`IFCLOCALPLACEMENT(#${sitePlacement},#${axis})`), building=add(`IFCBUILDING(${escStep(ifcGuid('building:'+model.id))},#${owner},${escStep(model.title)},$,$,#${buildingPlacement},$,$,.ELEMENT.,$,$,$)`);
  add(`IFCRELAGGREGATES(${escStep(ifcGuid('rel:project-site:'+model.id))},#${owner},$,$,#${project},(#${site}))`); add(`IFCRELAGGREGATES(${escStep(ifcGuid('rel:site-building:'+model.id))},#${owner},$,$,#${site},(#${building}))`);
  const storeyRefs=new Map(), storeyChildren=new Map(), storeySpaces=new Map();
  const upDirection=add('IFCDIRECTION((0.,0.,1.))');
  for(const level of model.levels){const p=add(`IFCCARTESIANPOINT((0.,0.,${Number(level.elevation).toFixed(3)}))`),a=add(`IFCAXIS2PLACEMENT3D(#${p},$,$)`),lp=add(`IFCLOCALPLACEMENT(#${buildingPlacement},#${a})`),st=add(`IFCBUILDINGSTOREY(${escStep(ifcGuid('storey:'+level.id))},#${owner},${escStep(level.name)},$,$,#${lp},$,$,.ELEMENT.,${Number(level.elevation).toFixed(3)})`);storeyRefs.set(level.id,{ref:st,placement:lp});storeyChildren.set(level.id,[]);storeySpaces.set(level.id,[]);}
  add(`IFCRELAGGREGATES(${escStep(ifcGuid('rel:building-storeys:'+model.id))},#${owner},$,$,#${building},(${[...storeyRefs.values()].map(x=>'#'+x.ref).join(',')}))`);
  const rectShape=(w,d,h)=>{const p2=add(`IFCCARTESIANPOINT((0.,0.))`),ax2=add(`IFCAXIS2PLACEMENT2D(#${p2},$)`),prof=add(`IFCRECTANGLEPROFILEDEF(.AREA.,$,#${ax2},${Number(w).toFixed(3)},${Number(d).toFixed(3)})`);return solidShape(prof,h);};
  const polyShape=(points,h)=>{const pts=points.map(p=>add(`IFCCARTESIANPOINT((${Number(p[0]).toFixed(3)},${Number(p[1]).toFixed(3)}))`)),pline=add(`IFCPOLYLINE((${[...pts,pts[0]].map(x=>'#'+x).join(',')}))`),prof=add(`IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,$,#${pline})`);return solidShape(prof,h);};
  const shapeRectProduct=(placementRef,w,d,h,name,type='IFCBUILDINGELEMENTPROXY',predefined='.NOTDEFINED.',identity=null)=>{const pds=rectShape(w,d,h);return add(`${type}(${escStep(ifcGuid(identity||name+':'+placementRef))},#${owner},${escStep(name)},$,$,#${placementRef},#${pds},$,${predefined})`);};
  function solidShape(profile,h){const dir=add(`IFCDIRECTION((0.,0.,1.))`),pos=add(`IFCAXIS2PLACEMENT3D(#${origin},$,$)`),solid=add(`IFCEXTRUDEDAREASOLID(#${profile},#${pos},#${dir},${Number(h).toFixed(3)})`),rep=add(`IFCSHAPEREPRESENTATION(#${context},'Body','SweptSolid',(#${solid}))`);return add(`IFCPRODUCTDEFINITIONSHAPE($,$,(#${rep}))`);}
  for(const space of g.elements.spaces){const st=storeyRefs.get(space.levelId);let lp,pds;if(space.footprint){const cp=add(`IFCCARTESIANPOINT((0.,0.,0.))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},$,$)`);lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`);pds=polyShape(space.footprint,space.h);}else{const cp=add(`IFCCARTESIANPOINT((${Number(space.x+space.w/2).toFixed(3)},${Number(space.y+space.d/2).toFixed(3)},0.))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},$,$)`);lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`);pds=rectShape(space.w,space.d,space.h);}const ref=add(`IFCSPACE(${escStep(ifcGuid('space:'+space.id))},#${owner},${escStep(space.name)},$,$,#${lp},#${pds},${escStep('MASAR_ROOM:'+space.id)},.ELEMENT.,.INTERNAL.,$)`);storeySpaces.get(space.levelId).push(ref);}
  const wallRefs=new Map(),wallsByType=new Map();
  for(const wall of g.elements.walls){const st=storeyRefs.get(wall.levelId),x=wall.axis==='v'?wall.coord:wall.start+wall.length/2,y=wall.axis==='v'?wall.start+wall.length/2:wall.coord,cp=add(`IFCCARTESIANPOINT((${Number(x).toFixed(3)},${Number(y).toFixed(3)},0.))`),dir=wall.axis==='v'?add(`IFCDIRECTION((0.,1.,0.))`):add(`IFCDIRECTION((1.,0.,0.))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},#${upDirection},#${dir})`),lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`),ref=shapeRectProduct(lp,wall.length,wall.thickness,wall.height,wall.wallTypeName||'Wall','IFCWALL','.NOTDEFINED.',wall.id);wallRefs.set(wall.id,ref);storeyChildren.get(wall.levelId).push(ref);if(!wallsByType.has(wall.wallTypeId))wallsByType.set(wall.wallTypeId,[]);wallsByType.get(wall.wallTypeId).push(ref);}
  for(const wt of effectiveAuthoring(model).wallTypes){const refs=wallsByType.get(wt.id)||[];if(!refs.length)continue;const layerRefs=wt.layers.map(layer=>{const mat=add(`IFCMATERIAL(${escStep(layer.name)},$,$)`);return add(`IFCMATERIALLAYER(#${mat},${Number(layer.thickness).toFixed(3)},$,$,${escStep(layer.name)},$,$)`);}),set=add(`IFCMATERIALLAYERSET((${layerRefs.map(x=>'#'+x).join(',')}),${escStep(wt.name)},$)`),usage=add(`IFCMATERIALLAYERSETUSAGE(#${set},.AXIS2.,.POSITIVE.,0.,$)`);add(`IFCRELASSOCIATESMATERIAL(${escStep(ifcGuid('material:'+wt.id))},#${owner},${escStep(wt.name)},$,( ${refs.map(x=>'#'+x).join(',')} ),#${usage})`);}
  for(const slab of g.elements.slabs){const st=storeyRefs.get(slab.levelId),cp=add(`IFCCARTESIANPOINT((${Number(slab.x+slab.w/2).toFixed(3)},${Number(slab.y+slab.d/2).toFixed(3)},${Number(-slab.h).toFixed(3)}))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},$,$)`),lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`),ref=shapeRectProduct(lp,slab.w,slab.d,slab.h,slab.name,'IFCSLAB','.FLOOR.',slab.id);storeyChildren.get(slab.levelId).push(ref);}
  for(const roof of g.elements.roofs){const st=storeyRefs.get(roof.levelId),cp=add(`IFCCARTESIANPOINT((${Number(roof.x+roof.w/2).toFixed(3)},${Number(roof.y+roof.d/2).toFixed(3)},${Number((model.levels.find(l=>l.id===roof.levelId)?.height||3)).toFixed(3)}))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},$,$)`),lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`),ref=shapeRectProduct(lp,roof.w,roof.d,roof.h,roof.name,'IFCSLAB','.ROOF.',roof.id);storeyChildren.get(roof.levelId).push(ref);}
  for(const opening of g.elements.openings){const st=storeyRefs.get(opening.levelId),vertical=['west','east'].includes(opening.side),z=opening.type==='window'?opening.sill:0,cp=add(`IFCCARTESIANPOINT((${Number(opening.x).toFixed(3)},${Number(opening.y).toFixed(3)},${Number(z).toFixed(3)}))`),dir=vertical?add(`IFCDIRECTION((0.,1.,0.))`):add(`IFCDIRECTION((1.,0.,0.))`),ax=add(`IFCAXIS2PLACEMENT3D(#${cp},#${upDirection},#${dir})`),lp=add(`IFCLOCALPLACEMENT(#${st.placement},#${ax})`),pds=rectShape(opening.width,.08,opening.height),voidPds=rectShape(opening.width,(g.elements.walls.find(w=>w.id===opening.hostWallId)?.thickness||.24)+.02,opening.height),op=add(`IFCOPENINGELEMENT(${escStep(ifcGuid('void:'+opening.id))},#${owner},${escStep('Opening '+opening.id)},$,$,#${lp},#${voidPds},${escStep(opening.id)},.OPENING.)`),wallRef=wallRefs.get(opening.hostWallId);if(wallRef)add(`IFCRELVOIDSELEMENT(${escStep(ifcGuid('void-rel:'+opening.id))},#${owner},$,$,#${wallRef},#${op})`);let ref;if(opening.type==='window')ref=add(`IFCWINDOW(${escStep(ifcGuid('window:'+opening.id))},#${owner},'Window',$,$,#${lp},#${pds},${escStep('MASAR_ROOM:'+opening.roomId+'|'+opening.id)},${Number(opening.height).toFixed(3)},${Number(opening.width).toFixed(3)},.WINDOW.,.SINGLE_PANEL.,$)`);else ref=add(`IFCDOOR(${escStep(ifcGuid('door:'+opening.id))},#${owner},${escStep(opening.entry?'Entrance door':'Door')},$,$,#${lp},#${pds},${escStep('MASAR_ROOM:'+opening.roomId+'|'+opening.id)},${Number(opening.height).toFixed(3)},${Number(opening.width).toFixed(3)},.DOOR.,.SINGLE_SWING_LEFT.,$)`);add(`IFCRELFILLSELEMENT(${escStep(ifcGuid('fill-rel:'+opening.id))},#${owner},$,$,#${op},#${ref})`);storeyChildren.get(opening.levelId).push(ref);}
  for(const [levelId,spaces] of storeySpaces)if(spaces.length)add(`IFCRELAGGREGATES(${escStep(ifcGuid('spaces:'+levelId))},#${owner},$,$,#${storeyRefs.get(levelId).ref},(${spaces.map(x=>'#'+x).join(',')}))`);
  for(const [levelId,children] of storeyChildren)if(children.length)add(`IFCRELCONTAINEDINSPATIALSTRUCTURE(${escStep(ifcGuid('contain:'+levelId))},#${owner},$,$,(${children.map(x=>'#'+x).join(',')}),#${storeyRefs.get(levelId).ref})`);
  const now=new Date().toISOString(), meta=`/* MASAR_SITE ${Number(model.site.width).toFixed(3)} ${Number(model.site.depth).toFixed(3)} ${model.site.street}; MASAR_MODEL ${model.id}; AUTHORING ${effectiveAuthoring(model).schema}; NOT FOR CONSTRUCTION */`;
  return `ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('MASAR IFC4 architectural subset (not MVD-certified)','MASAR authoring coordination export; NOT FOR CONSTRUCTION'),'2;1');\nFILE_NAME(${escStep((model.title||'MASAR')+'.ifc')},${escStep(now)},('MASAR User'),('MASAR Studio'),'MASAR Studio 4.1.0','MASAR Studio','');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n${meta}\n${lines.join('\n')}\nENDSEC;\nEND-ISO-10303-21;\n`;
}

export function projectReadiness(model) {
  const rules=evaluateRulePack(model), requirements=requirementMatrix(model), graph=deriveBuildingGraph(model), checks=validate(model);
  const measurable=requirements.filter(r=>r.measurable), satisfied=measurable.filter(r=>r.satisfied).length;
  return {
    model:{spaces:graph.counts.spaces,walls:graph.counts.walls,doors:graph.counts.doors,windows:graph.counts.windows,openings:graph.counts.openings,slabs:graph.counts.slabs,roofs:graph.counts.roofs},
    requirements:{total:requirements.length,measurable:measurable.length,satisfied,needsImprovement:measurable.length-satisfied,humanReview:requirements.filter(r=>!r.measurable).length},
    validation:{errors:checks.filter(i=>i.status==='error').length,warnings:checks.filter(i=>i.status==='warning').length,checked:checks.filter(i=>i.status==='checked').length,unchecked:checks.filter(i=>i.status==='unchecked').length},
    rules:rules.summary,
    deliveryReady:checks.every(i=>i.status!=='error') && rules.summary.fail===0,
    complianceReady:false,
    note:'جاهزية التسليم هنا تعني اتساق نموذج MASAR المفاهيمي فقط؛ الاعتماد الهندسي والتنظيمي خارج النطاق.'
  };
}
