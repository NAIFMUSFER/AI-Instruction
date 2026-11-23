/* Fresh conceptual context defaults; synchronous Python twin. No renderer,
   storage/auth/provider dependencies. Actual component AABBs, not nominal size. */
import {stairConnections} from './stairs.mjs';
const CD_MARKER={schema:'acs.context-details/1',source:'system_default',conceptual_only:true};
const CD_MAX_ADDED=12,CD_MAX_ROOMS=512,CD_MAX_OBJECTS=256,CD_MAX_EXPANDED_PARTS=4096,CD_EPS=1e-8;
const cdDict=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const cdNum=v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=1e12;
const cdRect=v=>Array.isArray(v)&&v.length===4&&v.every(cdNum)&&v[2]>0&&v[3]>0;
function cdShape(model){
 if(!cdDict(model)||!cdDict(model.floors)||!Array.isArray(model.levels)||(Object.hasOwn(model,'meta')&&!cdDict(model.meta)))return false;
 for(const floor of Object.values(model.floors)){
  if(!cdDict(floor)||!Array.isArray(floor.rooms))return false;
  for(const room of floor.rooms){if(!cdDict(room))return false;
   for(const key of ['objects','doors','windows','lanes','racks','docks','stations'])if(Object.hasOwn(room,key)&&(!Array.isArray(room[key])||room[key].some(v=>!cdDict(v))))return false;
  }
 }
 return model.levels.every(cdDict);
}
function cdUtf8(text){
 // TextEncoder silently replaces lone UTF-16 surrogates. Python's canonical
 // boundary rejects them, so preserve that error instead of repairing input.
 for(let i=0;i<text.length;i++){
  const code=text.charCodeAt(i);
  if(code>=0xd800&&code<=0xdbff){const next=text.charCodeAt(i+1);if(!(next>=0xdc00&&next<=0xdfff))cdError('CONTEXT_DETAILS_INPUT_UNSUPPORTED');i++;}
  else if(code>=0xdc00&&code<=0xdfff)cdError('CONTEXT_DETAILS_INPUT_UNSUPPORTED');
 }
 return new TextEncoder().encode(text);
}
function cdBounded(model){
 const stack=[model];let nodes=0,size=0;
 while(stack.length){const value=stack.pop();if(++nodes>30000)return false;
  if(cdDict(value)){size+=2+Object.keys(value).length*2;for(const [key,child]of Object.entries(value)){size+=cdUtf8(key).length*6+2;stack.push(child);}}
  else if(Array.isArray(value)){size+=2+value.length;for(const child of value)stack.push(child);}
  else if(typeof value==='string')size+=cdUtf8(value).length*6+2;
  else if(value===null||typeof value==='boolean')size+=5;
  else if(cdNum(value))size+=32;else return false;
  if(size>600000)return false;
 }return true;
}
function cdError(code){const error=new Error(code);error.code=code;throw error;}
function cdRoundEven(value){const lo=Math.floor(value),fraction=value-lo;return fraction===.5?(lo%2===0?lo:lo+1):Math.round(value);}
function cdParts(obj){
 if(!cdDict(obj)||!['column','railing','plant','planter','box'].includes(obj.kind))cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');
 if(['x','y','z','w','d','h','rot','pitch'].some(k=>!cdNum(obj[k])))cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');
 const {w,d,h}=obj;
 if(Math.min(w,d,h,obj.pitch)<=0||Math.max(w,d,h)>1000||!Number.isInteger(obj.count)||obj.count<1||obj.count>200||!['x','z'].includes(obj.dir))cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');
 if(obj.kind==='railing'){
  const n=Math.max(2,cdRoundEven(w/1.1));if(n>62)cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');
  return [[0,h,0,w,.06,.06],...Array.from({length:n+1},(_,i)=>[-w/2+w*i/n,h*.5,0,.05,h,.05])];
 }
 if(obj.kind==='plant')return [[0,.18,0,w*.55,.36,d*.55],[0,h*.62,0,w,h*.7,d]];
 return [[0,h*.5,0,w,h,d]];
}
function getActualBounds(obj){
 const parts=cdParts(obj),angle=obj.rot*(Math.PI/180),co=Math.cos(angle),sn=Math.sin(angle),out=[];
 if(parts.length*obj.count>1000)cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');
 for(let k=0;k<obj.count;k++)for(const [dx,dy,dz,w,h,d]of parts){
  const cx=obj.x+dx*co-dz*sn+(obj.dir==='x'?obj.pitch*k:0),cz=obj.z+dx*sn+dz*co+(obj.dir==='z'?obj.pitch*k:0),hx=(Math.abs(co)*w+Math.abs(sn)*d)/2,hz=(Math.abs(sn)*w+Math.abs(co)*d)/2,cy=obj.y+dy;
  out.push({min:[cx-hx,cy-h/2,cz-hz],max:[cx+hx,cy+h/2,cz+hz]});
 }
 return {min:[0,1,2].map(i=>Math.min(...out.map(p=>p.min[i]))),max:[0,1,2].map(i=>Math.max(...out.map(p=>p.max[i]))),parts:out};
}
const contextDetailBounds=getActualBounds;
function cdOverlap(a,b,pad=0){return Math.min(a[0]+a[2],b[0]+b[2]+pad)>Math.max(a[0],b[0]-pad)+CD_EPS&&Math.min(a[1]+a[3],b[1]+b[3]+pad)>Math.max(a[1],b[1]-pad)+CD_EPS;}
function cdFootprints(obj,room){return getActualBounds(obj).parts.map(p=>[p.min[0]+room.rect[0],p.min[2]+room.rect[1],p.max[0]-p.min[0],p.max[2]-p.min[2]]);}
function cdDoorReservations(room){
 const [x,z,w,d]=room.rect,out=[];
 for(const door of room.doors||[]){const {edge,offset,width}=door;
  if(!['N','E','S','W'].includes(edge)||!cdNum(offset)||!cdNum(width)||width<=0)cdError('DOOR_GEOMETRY_UNKNOWN');
  const length=['N','S'].includes(edge)?w:d;if(offset-width/2<0||offset+width/2>length)cdError('DOOR_GEOMETRY_UNKNOWN');
  const half=width/2+.2;
  if(['N','S'].includes(edge)){const zz=edge==='N'?z:z+d-1.2;out.push([x+offset-half,zz,2*half,1.2]);out.push([Math.min(x+offset,x+w/2)-.6,Math.min(zz,z+d/2)-.6,Math.abs(offset-w/2)+1.2,Math.abs(zz-z-d/2)+1.2]);}
  else{const xx=edge==='W'?x:x+w-1.2;out.push([xx,z+offset-half,1.2,2*half]);out.push([Math.min(xx,x+w/2)-.6,Math.min(z+offset,z+d/2)-.6,Math.abs(xx-x-w/2)+1.2,Math.abs(offset-d/2)+1.2]);}
 }return out;
}
function cdOpenEdge(room,edge,rooms){
 let walls=room.walls;if(walls==='none')walls=[];
 if(!Array.isArray(walls)||walls.some(v=>!['N','E','S','W'].includes(v))||walls.includes(edge)||(room.doors||[]).some(door=>door.edge===edge))return false;
 const [x,z,w,d]=room.rect;
 for(const other of rooms){if(other===room)continue;const [a,b,c,e]=other.rect;
  const shared=((edge==='N'&&Math.abs(b+e-z)<CD_EPS)||(edge==='S'&&Math.abs(b-z-d)<CD_EPS))&&Math.min(x+w,a+c)>Math.max(x,a)+CD_EPS;
  const shared2=((edge==='W'&&Math.abs(a+c-x)<CD_EPS)||(edge==='E'&&Math.abs(a-x-w)<CD_EPS))&&Math.min(z+d,b+e)>Math.max(z,b)+CD_EPS;
  if(shared||shared2)return false;
 }return true;
}
function cdId(seed){let value=2166136261;for(const byte of cdUtf8(seed))value=Math.imul(value^byte,16777619)>>>0;return 'context_'+value.toString(16).padStart(8,'0');}
function cdProvenance(context){return {schema:'acs.context-detail/1',source:'system_default',conceptual_only:true,context,assumptions:['conceptual_dimensions','not_structurally_designed','door_route_reservation_1.2m','actual_component_bounds']};}
function cdValidProvenance(v){return cdDict(v)&&Object.keys(v).length===5&&['schema','source','conceptual_only','context','assumptions'].every(k=>Object.hasOwn(v,k))&&v.schema==='acs.context-detail/1'&&v.source==='system_default'&&v.conceptual_only===true&&['porch','balcony','courtyard'].includes(v.context)&&Array.isArray(v.assumptions)&&v.assumptions.length<=8&&v.assumptions.every(a=>typeof a==='string'&&Array.from(a).length<=80);}
function listContextDetails(model){
 if(!cdShape(model))return [];const out=[];let scanned=0;
 for(const level of model.levels.slice(0,64)){const template=level.template,floor=typeof template==='string'?model.floors[template]:null;if(!floor)continue;
  for(const room of floor.rooms.slice(0,CD_MAX_ROOMS))for(const obj of (room.objects||[]).slice(0,CD_MAX_OBJECTS)){
   if(++scanned>2048)return out;
   if(cdValidProvenance(obj.context_detail_provenance)&&['column','railing','plant','planter'].includes(obj.kind)&&typeof obj.id==='string'){
   out.push({template,level_index:level.index??null,room_id:room.id??null,element_id:obj.id,kind:obj.kind,count:obj.count??null,context_detail_provenance:structuredClone(obj.context_detail_provenance)});if(out.length===CD_MAX_OBJECTS)return out;
  }}
 }return out;
}
function withContextDetails(model){
 if(!cdShape(model))return [model,null,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'];
 const report={schema:'acs.context-details-report/1',conceptual_only:true,added:[],skipped:[]};
 if(Object.hasOwn(model.meta||{},'acs_context_details')){const m=model.meta.acs_context_details;return cdDict(m)&&Object.keys(m).length===3&&Object.entries(CD_MARKER).every(([k,v])=>m[k]===v)?[model,report,null]:[model,null,'CONTEXT_DETAILS_PROVENANCE_INVALID'];}
 let bounded;try{bounded=cdBounded(model);}catch(error){if(error.code==='CONTEXT_DETAILS_INPUT_UNSUPPORTED')return [model,null,error.code];throw error;}
 if(model.levels.length>64||!bounded)return [model,null,'CONTEXT_DETAILS_RESOURCE_LIMIT'];
 const floors=model.floors,allRooms=Object.values(floors).flatMap(f=>f.rooms);
 if(allRooms.length>CD_MAX_ROOMS||allRooms.reduce((n,r)=>n+(r.objects||[]).length,0)>CD_MAX_OBJECTS)return [model,null,'CONTEXT_DETAILS_RESOURCE_LIMIT'];
 for(const floor of Object.values(floors)){const ids=floor.rooms.map(r=>r.id);if(ids.some(v=>typeof v!=='string'||!v.trim())||ids.length!==new Set(ids).size)return [model,null,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'];}
 const levels=model.levels,uses=new Map(),indices=new Set();
 for(const level of levels){const t=level.template,i=level.index;if(typeof t!=='string'||!Object.hasOwn(floors,t)||!Number.isSafeInteger(i)||indices.has(i))return [model,null,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'];uses.set(t,(uses.get(t)||0)+1);indices.add(i);}
 const reservations=new Map();
 if(allRooms.some(r=>(r.objects||[]).some(o=>o.form==='u_return'))){try{for(const c of stairConnections(model))for(const index of [c.source_level_index,c.target_level_index]){if(!reservations.has(index))reservations.set(index,[]);reservations.get(index).push(c.opening,c.arrival);}}catch{return [model,null,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'];}}
 const planned=[],blockerCache=new Map();let expandedParts=0;
 for(const level of levels){const template=level.template,rooms=floors[template].rooms;if(level.kind==='roof')continue;
  for(const room of rooms){const role=room.role,context=['porch','portico'].includes(role)?'porch':role==='balcony'?'balcony':['courtyard','patio'].includes(role)?'courtyard':null;if(context===null)continue;
   const source={template,level_index:level.index,room_id:room.id??null};const skip=reason=>{if(report.skipped.length<128)report.skipped.push({...source,reason});};
   if(planned.length>=CD_MAX_ADDED){skip('ADDITION_LIMIT');continue;}
   if(uses.get(template)!==1){skip('SHARED_TEMPLATE');continue;}
   if(typeof room.id!=='string'||!room.id.trim()||rooms.some(r=>!cdRect(r.rect))){skip('ROOM_GEOMETRY_UNKNOWN');continue;}
   const walls=room.walls;if(walls!=='none'&&(!Array.isArray(walls)||walls.some(v=>!['N','E','S','W'].includes(v)))){skip('WALL_SEMANTICS_UNKNOWN');continue;}
   if(context==='porch'&&room.covered!==true||context==='courtyard'&&room.outdoor!==true){skip('CONTEXT_UNCONFIRMED');continue;}
   const wall=model.wall_t,height=Object.hasOwn(room,'wall_h')?room.wall_h:model.wall_h;
   if(!cdNum(wall)||wall<=0||context==='porch'&&(!cdNum(height)||height<=0||height>1000)){skip('DIMENSION_UNKNOWN');continue;}
   if(rooms.some(other=>other!==room&&cdOverlap(room.rect,other.rect))){skip('ROOM_OVERLAP');continue;}
   const index=level.index;
   if(!blockerCache.has(index)){
    const existingBlockers=[...(reservations.get(index)||[])];let unknown=false;
    try{
     const objects=[];let prospective=0;
     for(const other of rooms)for(const obj of other.objects||[]){if(obj.form==='u_return')continue;const parts=cdParts(obj).length*obj.count;if(parts>1000)cdError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED');prospective+=parts;if(expandedParts+prospective>CD_MAX_EXPANDED_PARTS)return [model,null,'CONTEXT_DETAILS_RESOURCE_LIMIT'];objects.push([obj,other]);}
     for(const other of rooms){existingBlockers.push(...cdDoorReservations(other));if(['stairs','stair','elevator','lift'].includes(other.role)||['lanes','racks','docks','stations'].some(k=>other[k]?.length))existingBlockers.push(other.rect);}
     for(const [obj,other]of objects)existingBlockers.push(...cdFootprints(obj,other));expandedParts+=prospective;
    }catch{unknown=true;}
    blockerCache.set(index,[existingBlockers,unknown]);
   }
   const [cached,unknown]=blockerCache.get(index),blockers=[...cached];
   if(unknown){skip('OBSTACLE_GEOMETRY_UNKNOWN');continue;}
   const [x,z,w,d]=room.rect,candidates=[],margin=wall/2+.15;
   if(['porch','courtyard'].includes(context)){
    const size=context==='porch'?.45:.6,inset=margin+size/2;if(Math.min(w,d)<2*inset+1.2){skip('INSUFFICIENT_SPACE');continue;}
    for(const [px,pz]of [[inset,inset],[w-inset,inset],[inset,d-inset],[w-inset,d-inset]])candidates.push({kind:context==='porch'?'column':'plant',x:px,z:pz,y:0,w:size,d:size,h:context==='porch'?height:1.2,rot:0,count:1,pitch:1,dir:'x'});
   }else{
    for(const edge of ['N','E','S','W']){if(!cdOpenEdge(room,edge,rooms))continue;const span=(['N','S'].includes(edge)?w:d)-2*margin-.05;if(span<1.2||span>50)continue;
     candidates.push({kind:'railing',x:['N','S'].includes(edge)?w/2:edge==='W'?margin+.03:w-margin-.03,z:['E','W'].includes(edge)?d/2:edge==='N'?margin+.03:d-margin-.03,y:0,w:span,d:.06,h:1.1,rot:['N','S'].includes(edge)?0:90,count:1,pitch:1,dir:'x'});
    }
   }
   let made=0;const reservedIds=new Set(Object.values(room).filter(Array.isArray).flatMap(v=>v).filter(v=>cdDict(v)&&typeof v.id==='string').map(v=>v.id));
   for(const [position,obj]of candidates.entries()){
    if(made>=2||planned.length>=CD_MAX_ADDED)break;const feet=cdFootprints(obj,room);
    if(feet.some(p=>p[0]<x+margin-CD_EPS||p[1]<z+margin-CD_EPS||p[0]+p[2]>x+w-margin+CD_EPS||p[1]+p[3]>z+d-margin+CD_EPS||blockers.some(b=>cdOverlap(p,b,.1))))continue;
    const base=cdId(template+'\0'+level.index+'\0'+room.id+'\0'+context+'\0'+position);let identity=base,suffix=2;while(reservedIds.has(identity))identity=base+'_'+suffix++;
    reservedIds.add(identity);obj.id=identity;obj.context_detail_provenance=cdProvenance(context);planned.push([template,room.id,obj]);report.added.push({...source,element_id:identity,kind:obj.kind});blockers.push(...feet);made++;
   }
   if(!made)skip('NO_CLEAR_SUPPORTED_PLACEMENT');
  }
 }
 if(!planned.length)return [model,report,null];const out=structuredClone(model);
 for(const [template,rid,obj]of planned){const room=out.floors[template].rooms.find(r=>r.id===rid);if(!room.objects)room.objects=[];room.objects.push(obj);}
 if(!out.meta)out.meta={};out.meta.acs_context_details={...CD_MARKER};return [out,report,null];
}
export {withContextDetails,listContextDetails,getActualBounds,contextDetailBounds};
