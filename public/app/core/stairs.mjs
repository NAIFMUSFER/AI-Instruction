/* Canonical U-return stairs. Pure synchronous twin of acs_stairs.py; no DOM,
   renderer, storage, authentication or provider dependencies. Metres; object
   local +X rotates toward +Z. Geometry never certifies safe traversal or codes. */
const STAIR_EPS=1e-6;
const stairDict=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const stairNumber=v=>typeof v==='number'&&Number.isFinite(v);
const stairClone=v=>structuredClone(v);
function stairError(code){const error=new Error(code);error.code=code;throw error;}
// The established Python-round and SHA algorithms are private here to keep the
// compiler dependency leaf acyclic. Exact Python/JS parity covers their results.
function stairRound(x){
  if(Math.abs(x)>=1e21)return x;
  const neg=x<0,s=Math.abs(x).toFixed(20),dot=s.indexOf('.'),fp=s.slice(dot+1);
  let n=parseInt(s.slice(0,dot)+fp.slice(0,6),10);const rest=fp.slice(6),first=rest.charCodeAt(0)-48;
  if(first>5||(first===5&&(/[1-9]/.test(rest.slice(1))||n%2===1)))n++;
  return (neg?-n:n)/1e6;
}
function stairId(value){const text=String(value),points=Array.from(text);return points.length<=160?text:points.slice(0,139).join('')+'_'+stairHash(text).slice(0,20);}
function stairShapeValid(model){
  if(!stairDict(model)||!stairDict(model.floors)||!Array.isArray(model.levels)||(Object.hasOwn(model,'meta')&&!stairDict(model.meta)))return false;
  for(const floor of Object.values(model.floors)){
    if(!stairDict(floor)||!Array.isArray(floor.rooms))return false;
    for(const room of floor.rooms)if(!stairDict(room)||(Object.hasOwn(room,'objects')&&(!Array.isArray(room.objects)||room.objects.some(obj=>!stairDict(obj)))))return false;
  }
  return model.levels.every(stairDict);
}
function stairObject(obj){return stairDict(obj)&&['stair','درج','سلم'].some(word=>String(obj.kind||obj.name||'').toLowerCase().includes(word));}
function validateStairForms(model){
  for(const floor of Object.values(model.floors))for(const room of floor.rooms)for(const obj of room.objects||[])if(stairObject(obj)&&Object.hasOwn(obj,'form')&&obj.form!=='u_return')stairError('STAIR_FORM_UNSUPPORTED');
}
function stairElevation(level,model){
  if(!Number.isInteger(level.index))stairError('STAIR_LEVEL_INVALID');
  const v=Object.hasOwn(level,'elevation')?level.elevation:stairNumber(model.floor_height)?level.index*model.floor_height:null;
  if(!stairNumber(v))stairError('STAIR_ELEVATION_NOT_SPECIFIED');return v;
}
function stairLevels(model){
  const raw=model.levels;if(!Array.isArray(raw)||raw.length>64)stairError('STAIR_LEVEL_INVALID');
  const seen=new Set(),levels=[];
  for(const level of raw){
    if(!stairDict(level)||typeof level.template!=='string'||!Number.isSafeInteger(level.index)||!Object.hasOwn(model.floors||{},level.template)||seen.has(level.index))stairError('STAIR_LEVEL_INVALID');
    seen.add(level.index);if(level.kind!=='roof')levels.push([level,stairElevation(level,model)]);
  }
  levels.sort((a,b)=>a[1]-b[1]||a[0].index-b[0].index);
  for(let i=1;i<levels.length;i++)if(Math.abs(levels[i-1][1]-levels[i][1])<STAIR_EPS)stairError('STAIR_LEVEL_ELEVATION_AMBIGUOUS');
  return levels;
}
function resolveStairGeometry(obj){
  if(!stairDict(obj)||obj.kind!=='stairs'||obj.form!=='u_return')stairError('STAIR_FORM_UNSUPPORTED');
  if(typeof obj.id!=='string'||!obj.id.trim()||Array.from(obj.id).length>160)stairError('STAIR_ID_NOT_SPECIFIED');
  const s=obj.stair;if(!stairDict(s)||s.schema!=='acs.stair/1')stairError('STAIR_GEOMETRY_NOT_SPECIFIED');
  const fields=['flight_width_m','gap_m','tread_m','entry_landing_m','mid_landing_m','landing_thickness_m'];
  if(fields.some(k=>!stairNumber(s[k])||s[k]<=0))stairError('STAIR_GEOMETRY_INVALID');
  if(['x','y','z','w','d','h','rot'].some(k=>!stairNumber(obj[k])))stairError('STAIR_GEOMETRY_NOT_SPECIFIED');
  if(obj.rot%90!==0)stairError('STAIR_ROTATION_UNSUPPORTED');
  const n=s.risers_per_flight;if(!Number.isInteger(n)||n<2||n>32)stairError('STAIR_RISER_COUNT_INVALID');
  if(obj.count!==1||obj.dir!=='x'||obj.pitch!==1)stairError('STAIR_REPETITION_UNSUPPORTED');
  if(['source_level_index','target_level_index'].some(k=>!Number.isInteger(s[k]))||['source_elevation_m','target_elevation_m'].some(k=>!stairNumber(s[k])))stairError('STAIR_CONNECTION_NOT_SPECIFIED');
  const h=s.target_elevation_m-s.source_elevation_m,[fw,gap,tread,entry,mid,thick]=fields.map(k=>s[k]),w=2*fw+gap,d=entry+(n-1)*tread+mid;
  if(h<=0||obj.y!==0||h/2<thick||[[obj.h,h],[obj.w,w],[obj.d,d]].some(([a,b])=>Math.abs(a-b)>STAIR_EPS))stairError('STAIR_DIMENSION_MISMATCH');
  const rise=h/(2*n),start=-d/2+entry,run=(n-1)*tread,components=[];
  for(const flight of [1,2])for(let i=1;i<n;i++){
    const top=flight===1?i*rise:h/2+i*rise,z=flight===1?start+(i-.5)*tread:start+run-(i-.5)*tread;
    components.push({id:'f'+flight+'_t'+String(i).padStart(2,'0'),role:'tread',center:[flight===1?-(fw+gap)/2:(fw+gap)/2,top-rise/2,z].map(stairRound),size:[fw,rise,tread].map(stairRound)});
  }
  components.push({id:'mid_landing',role:'mid_landing',center:[0,stairRound(h/2-thick/2),stairRound(d/2-mid/2)],size:[w,thick,mid].map(stairRound)});
  return {components,opening:[-w/2,start,w,d-entry].map(stairRound),arrival:[-w/2,-d/2,w,entry].map(stairRound)};
}
function stairWorldRect(rect,obj,room){
  const [x,z,w,d]=rect,turns=((obj.rot/90)%4+4)%4;
  const points=[[x,z],[x+w,z],[x+w,z+d],[x,z+d]].map(([a,b])=>[[a,b],[-b,a],[-a,-b],[b,-a]][turns]);
  const xs=points.map(p=>p[0]+room.rect[0]+obj.x),zs=points.map(p=>p[1]+room.rect[1]+obj.z);
  return [Math.min(...xs),Math.min(...zs),Math.max(...xs)-Math.min(...xs),Math.max(...zs)-Math.min(...zs)].map(stairRound);
}
function hasUStairs(model){
  return Object.values(model?.floors||{}).some(floor=>Array.isArray(floor?.rooms)&&floor.rooms.some(room=>Array.isArray(room?.objects)&&room.objects.some(obj=>obj?.form==='u_return')));
}
function hasStairForms(model){
  if(!stairDict(model?.floors))return false;
  return Object.values(model.floors).some(floor=>Array.isArray(floor?.rooms)&&floor.rooms.some(room=>Array.isArray(room?.objects)&&room.objects.some(obj=>stairDict(obj)&&(obj.form==='u_return'||(stairObject(obj)&&Object.hasOwn(obj,'form'))))));
}
function stairEntryMatches(room,arrival,rotation,wall){
  const doors=room.doors||[];if(doors.length!==1||!stairDict(doors[0]))return false;
  const door=doors[0],edge=['N','E','S','W'][((rotation/90)%4+4)%4];
  if(door.edge!==edge||!stairNumber(door.offset)||!stairNumber(door.width)||door.width<=0)return false;
  const [x,z,w,d]=room.rect,[ax,az,aw,ad]=arrival;
  const fixed={N:[az,z+wall/2],S:[az+ad,z+d-wall/2],E:[ax+aw,x+w-wall/2],W:[ax,x+wall/2]}[edge];
  if(Math.abs(fixed[0]-fixed[1])>STAIR_EPS)return false;
  const center=(['N','S'].includes(edge)?x:z)+door.offset,[a0,a1]=['N','S'].includes(edge)?[ax,ax+aw]:[az,az+ad];
  return center-door.width/2>=a0-STAIR_EPS&&center+door.width/2<=a1+STAIR_EPS;
}
function stairConnections(model){
  if(!stairShapeValid(model))stairError('STAIR_MODEL_INVALID');
  validateStairForms(model);
  if(!hasUStairs(model))return [];
  templateScopeAliases(model);
  for(const level of model.levels||[])if(stairDict(level)&&level.kind==='roof'){
    const floor=model.floors?.[level.template]||{};
    if((floor.rooms||[]).some(room=>(room.objects||[]).some(obj=>stairDict(obj)&&obj.form==='u_return')))stairError('STAIR_ROOF_ACCESS_UNSUPPORTED');
  }
  const levels=stairLevels(model),byIndex=new Map(levels.map(row=>[row[0].index,row])),out=[];
  for(const [position,[level,elev]]of levels.entries())for(const room of model.floors[level.template].rooms||[])for(const obj of room.objects||[]){
    if(!stairDict(obj)||obj.form!=='u_return')continue;
    const geometry=resolveStairGeometry(obj),s=obj.stair,target=byIndex.get(s.target_level_index);
    if(s.source_level_index!==level.index||Math.abs(s.source_elevation_m-elev)>STAIR_EPS||!target||Math.abs(target[1]-s.target_elevation_m)>STAIR_EPS||position+1>=levels.length||levels[position+1][0].index!==target[0].index)stairError('STAIR_CONNECTION_STALE');
    const candidates=(model.floors[target[0].template].rooms||[]).filter(r=>r.core_id&&r.core_id===room.core_id&&['stair','stairs'].includes(r.role));
    if(candidates.length!==1||JSON.stringify(candidates[0].rect)!==JSON.stringify(room.rect))stairError('STAIR_CORE_ALIGNMENT_CHANGED');
    const rc=room.rect,wall=model.wall_t;
    if(!Array.isArray(rc)||rc.length!==4||rc.some(v=>!stairNumber(v))||!stairNumber(wall)||wall<=0)stairError('STAIR_CORE_DIMENSION_NOT_SPECIFIED');
    const box=stairWorldRect([-obj.w/2,-obj.d/2,obj.w,obj.d],obj,room);
    if(box[0]<rc[0]+wall/2-STAIR_EPS||box[1]<rc[1]+wall/2-STAIR_EPS||box[0]+box[2]>rc[0]+rc[2]-wall/2+STAIR_EPS||box[1]+box[3]>rc[1]+rc[3]-wall/2+STAIR_EPS)stairError('STAIR_CORE_TOO_SMALL');
    const arrival=stairWorldRect(geometry.arrival,obj,room);
    if(![room,candidates[0]].every(r=>stairEntryMatches(r,arrival,obj.rot,wall)))stairError('STAIR_ENTRY_CHANGED');
    out.push({source_level_index:level.index,target_level_index:target[0].index,room_id:room.id??null,target_room_id:candidates[0].id??null,core_id:room.core_id??null,source_object_id:obj.id??null,object:obj,opening:stairWorldRect(geometry.opening,obj,room),arrival});
  }
  return out;
}
function stairCores(model,level){return (model.floors[level.template].rooms||[]).filter(r=>['stair','stairs'].includes(r.role));}
function stairRoomMappingsEqual(a,b){
  return Array.isArray(b)&&a.length===b.length&&a.every((row,i)=>stairDict(b[i])&&Object.keys(b[i]).length===2&&Object.hasOwn(b[i],'id')&&Object.hasOwn(b[i],'role')&&row.id===b[i].id&&row.role===b[i].role);
}
function templateScopeAliases(model){
  const result={},levels=model.levels||[],floors=model.floors||{};
  for(const level of levels){
    if(!stairDict(level)||(!Object.hasOwn(level,'stair_source_template')&&!Object.hasOwn(level,'stair_template_instance')))continue;
    const source=level.stair_source_template,template=level.template,record=level.stair_template_instance;
    if(typeof source!=='string'||!source.trim()||Array.from(source).length>160||!Object.hasOwn(floors,source)||typeof template!=='string'||!Object.hasOwn(floors,template)||source===template||!stairDict(record)||record.schema!=='acs.stair-template-instance/1'||record.source_template!==source||record.template!==template||!Number.isInteger(record.level_index)||record.level_index!==level.index||levels.filter(l=>stairDict(l)&&l.template===template).length!==1||!levels.some(l=>stairDict(l)&&l.template===source&&!Object.hasOwn(l,'stair_source_template')))stairError('STAIR_TEMPLATE_SCOPE_INVALID');
    const mapping=key=>(floors[key].rooms||[]).map(room=>({id:room.id??null,role:room.role??null}));
    const original=mapping(source),variant=mapping(template);
    if(!original.length||original.some(row=>typeof row.id!=='string'||!row.id.trim()||Array.from(row.id).length>160)||new Set(original.map(row=>row.id)).size!==original.length||!stairRoomMappingsEqual(original,variant)||!stairRoomMappingsEqual(original,record.room_mapping))stairError('STAIR_TEMPLATE_SCOPE_CHANGED');
    if(!Object.hasOwn(result,template))Object.defineProperty(result,template,{value:new Set(),enumerable:true});result[template].add(source);
  }
  return result;
}
function validateStairReport(model){
  const meta=model?.meta;if(!stairDict(meta)||!Object.hasOwn(meta,'acs_stairs'))return;
  const report=meta.acs_stairs,connections=stairConnections(model);
  if(connections.some(c=>Object.hasOwn(c.object,'stair_provenance')&&!stairDict(c.object.stair_provenance)))stairError('STAIR_PROVENANCE_INVALID');
  const generated=connections.filter(c=>c.object.stair_provenance?.source==='system_default').length;
  if(!stairDict(report)||report.schema!=='acs.stairs/1'||report.source!=='system_default'||report.physical_traversal!=='NOT_VERIFIED'||!Number.isInteger(report.generated_connections)||report.generated_connections!==generated||!Array.isArray(report.unsupported))stairError('STAIR_REPORT_INVALID');
}
// Prospective default-authoring limits, not limits on imported canonical models.
const STAIR_MAX_CONNECTIONS=128,STAIR_MAX_ROOM_INSTANCES=512,STAIR_MAX_BYTES=600000,STAIR_MAX_NODES=30000;
function stairStringBytes(value){
  // Exact UTF8 JSON string cost, without allocating a whole-model JSON string.
  let bytes=2;
  for(let i=0;i<value.length;i++){
    const c=value.charCodeAt(i);
    if(c===34||c===92||[8,9,10,12,13].includes(c))bytes+=2;
    else if(c<32)bytes+=6;
    else if(c<128)bytes++;
    else if(c<2048)bytes+=2;
    else if(c>=0xD800&&c<=0xDBFF){
      const low=value.charCodeAt(++i);if(!(low>=0xDC00&&low<=0xDFFF))throw new Error('STAIR_RESOURCE_LIMIT');bytes+=4;
    }else if(c>=0xDC00&&c<=0xDFFF)throw new Error('STAIR_RESOURCE_LIMIT');
    else bytes+=3;
  }
  return bytes;
}
function stairResourceLimited(model,levels){
  const physicalRooms=levels.reduce((sum,[level])=>sum+model.floors[level.template].rooms.length,0);
  const cores=model.floors[levels[0][0].template].rooms.filter(room=>['stair','stairs'].includes(room.role)).length;
  const prospective=cores*(levels.length-1);if(prospective===0)return false;
  if(physicalRooms>STAIR_MAX_ROOM_INSTANCES||prospective>STAIR_MAX_CONNECTIONS)return true;
  let nodes=0,textSize=0;const stack=[[model,0]];
  const textFits=text=>{for(const _ of text){textSize++;if(textSize>STAIR_MAX_BYTES)return false;}return true;};
  while(stack.length){
    const [value,depth]=stack.pop();nodes++;
    if(nodes>STAIR_MAX_NODES||depth>32)return true;
    if(stairDict(value)||Array.isArray(value)){
      const values=Object.values(value);if(nodes+stack.length+values.length>STAIR_MAX_NODES)return true;
      if(stairDict(value))for(const key of Object.keys(value))if(!textFits(key))return true;
      for(const child of values)stack.push([child,depth+1]);
    }else if(typeof value==='string'){if(!textFits(value))return true;}
    else if(typeof value==='number'){if(!stairNumber(value)||Math.abs(value)>Number.MAX_SAFE_INTEGER)return true;}
    else if(value!==null&&typeof value!=='boolean')return true;
  }
  const weights=new Map();
  const weight=value=>{
    if(stairDict(value)){
      const entries=Object.entries(value);let size=2+Math.max(0,entries.length-1),count=1;
      for(const [key,child]of entries){const [b,n]=weight(child);size+=stairStringBytes(key)+1+b;count+=n;}
      const result=[size,count];weights.set(value,result);return result;
    }
    if(Array.isArray(value)){
      let size=2+Math.max(0,value.length-1),count=1;for(const child of value){const [b,n]=weight(child);size+=b;count+=n;}
      const result=[size,count];weights.set(value,result);return result;
    }
    if(value===null)return [4,1];if(typeof value==='boolean')return [value?4:5,1];
    if(typeof value==='number')return [32,1];return [stairStringBytes(value),1];
  };
  let size;try{[size,nodes]=weight(model);}catch(error){return true;}
  const counts=new Map();for(const [level]of levels)counts.set(level.template,(counts.get(level.template)||0)+1);
  const preserve=new Set(model.levels.filter(level=>level.kind==='roof').map(level=>level.template));
  for(const [template,count]of counts){
    const extra=Math.max(0,count-(preserve.has(template)?0:1));if(!extra)continue;
    const [bytes,floorNodes]=weights.get(model.floors[template]);size+=extra*(2*bytes+2048);nodes+=extra*(2*floorNodes+32);
  }
  size+=prospective*4096+2048;nodes+=prospective*96+64;
  return size>STAIR_MAX_BYTES||nodes>STAIR_MAX_NODES;
}

function withDefaultStairs(model){
  if(!stairShapeValid(model))return [model,null,'STAIR_MODEL_INVALID'];
  try{validateStairForms(model);}catch(error){return [model,null,error.message];}
  if(stairDict(model.meta)&&Object.hasOwn(model.meta,'acs_stairs')){
    try{validateStairReport(model);return [model,model.meta.acs_stairs,null];}
    catch(error){return [model,null,error.message];}
  }
  let levels;try{levels=stairLevels(model);}catch(error){return [model,null,error.message];}
  const report={schema:'acs.stairs/1',source:'system_default',generated_connections:0,unsupported:[],physical_traversal:'NOT_VERIFIED',not_verified:['structure','guards','headroom','accessibility','fire escape','code compliance']};
  if(levels.length<2)return [model,report,'STAIR_NOT_APPLICABLE'];
  if(stairResourceLimited(model,levels)){report.unsupported=[{code:'STAIR_RESOURCE_LIMIT'}];return [model,report,'STAIR_RESOURCE_LIMIT'];}
  const firstCores=stairCores(model,levels[0][0]);let plans=[];
  for(const first of firstCores){
    const core=first.core_id??null,chain=[];let code=null;
    if(typeof core!=='string'||!core.trim()||Array.from(core).length>160)code='STAIR_CORE_ID_NOT_SPECIFIED';
    for(const [level,elev]of levels){
      const candidates=stairCores(model,level).filter(r=>(r.core_id??null)===core);
      if(candidates.length!==1){code=code||'STAIR_CORE_ALIGNMENT_CHANGED';break;}
      const room=candidates[0];chain.push([level,elev,room]);
      if(JSON.stringify(room.rect)!==JSON.stringify(first.rect))code=code||'STAIR_CORE_ALIGNMENT_CHANGED';
      if((room.objects||[]).some(o=>stairDict(o)&&(o.form==='u_return'||['stair','درج','سلم'].some(word=>String(o.kind||o.name||'').toLowerCase().includes(word)))))code=code||'STAIR_AUTHORED_GEOMETRY_PRESERVED';
    }
    const proposed=[];
    if(!code)for(let i=0;i<chain.length-1;i++){
      const [level,elev,room]=chain[i],[target,targetElev]=chain[i+1],rc=room.rect,wall=model.wall_t;
      if(!Array.isArray(rc)||rc.length!==4||rc.some(v=>!stairNumber(v))||!stairNumber(wall)||wall<=0){code='STAIR_CORE_DIMENSION_NOT_SPECIFIED';break;}
      const doors=room.doors||[],edges=new Set(doors.filter(stairDict).map(d=>d.edge)),edge=Array.from(edges)[0];
      if(edges.size!==1||doors.length!==1||!['N','E','S','W'].includes(edge)){code='STAIR_ENTRY_UNSUPPORTED';break;}
      const door=doors[0],rot={N:0,E:90,S:180,W:270}[edge],h=targetElev-elev;
      if(h<2.4-STAIR_EPS||h>3.6+STAIR_EPS){code='STAIR_DEFAULT_RISE_UNSUPPORTED';break;}
      const w=1.9,d=3.8,[fw,fd]=rot%180===0?[w,d]:[d,w];
      if(rc[2]<fw+wall-STAIR_EPS||rc[3]<fd+wall-STAIR_EPS){code='STAIR_CORE_TOO_SMALL';break;}
      const offset=door.offset,width=door.width;
      if(!stairNumber(offset)||!stairNumber(width)||width<=0||width>w){code='STAIR_ENTRY_UNSUPPORTED';break;}
      const x=['N','S'].includes(edge)?offset:edge==='W'?wall/2+d/2:rc[2]-wall/2-d/2;
      const z=['E','W'].includes(edge)?offset:edge==='N'?wall/2+d/2:rc[3]-wall/2-d/2;
      if(x-fw/2<wall/2-STAIR_EPS||x+fw/2>rc[2]-wall/2+STAIR_EPS||z-fd/2<wall/2-STAIR_EPS||z+fd/2>rc[3]-wall/2+STAIR_EPS){code='STAIR_ENTRY_UNSUPPORTED';break;}
      const base=stairId('stairs_'+core+'_'+level.index+'_'+target.index),usedIds=new Set(Object.values(room).filter(Array.isArray).flatMap(values=>values.filter(item=>stairDict(item)&&typeof item.id==='string').map(item=>item.id)));
      let objectId=base,n=2;while(usedIds.has(objectId)){const suffix='_'+n;objectId=Array.from(base).slice(0,160-suffix.length).join('')+suffix;n++;}
      const obj={id:objectId,kind:'stairs',form:'u_return',x:stairRound(x),z:stairRound(z),y:0,w,d,h:stairRound(h),rot,count:1,pitch:1,dir:'x',
        stair:{schema:'acs.stair/1',source_level_index:level.index,target_level_index:target.index,source_elevation_m:elev,target_elevation_m:targetElev,flight_width_m:.9,gap_m:.1,tread_m:.25,risers_per_flight:9,entry_landing_m:.9,mid_landing_m:.9,landing_thickness_m:.15},
        stair_provenance:{source:'system_default',source_room_id:room.id??null,core_id:core}};
      const geometry=resolveStairGeometry(obj),arrival=stairWorldRect(geometry.arrival,obj,room),targetRoom=stairCores(model,target).find(r=>r.core_id===core);
      if(!stairEntryMatches(targetRoom,arrival,rot,wall)){code='STAIR_ENTRY_UNSUPPORTED';break;}
      proposed.push([level.index,room.id??null,obj]);
    }
    if(code)report.unsupported.push({core_id:core,room_id:first.id??null,code});else plans.push(...proposed);
  }
  if(!firstCores.length)report.unsupported.push({code:'STAIR_CORE_NOT_DECLARED'});
  const affectedTemplates=new Set(levels.filter(([level])=>plans.some(p=>p[0]===level.index)).map(([level])=>level.template));
  const preservedTemplates=new Set(model.levels.filter(level=>level.kind==='roof').map(level=>level.template));
  const extra=Array.from(affectedTemplates).reduce((sum,template)=>sum+Math.max(0,levels.filter(([level])=>level.template===template).length-(preservedTemplates.has(template)?0:1))*model.floors[template].rooms.length,0);
  if(Object.values(model.floors).reduce((sum,floor)=>sum+floor.rooms.length,0)+extra>2048){plans=[];report.unsupported.push({code:'STAIR_INSTANCE_LIMIT_EXCEEDED'});}
  if(!plans.length)return [{...model,meta:{...(model.meta||{}),acs_stairs:stairClone(report)}},report,null];
  const out=stairClone(model);
  if(plans.length){
    const used=new Set(out.levels.filter(l=>l.kind==='roof').map(l=>l.template)),sources=stairClone(out.floors),affected=new Set(levels.filter(([level])=>plans.some(p=>p[0]===level.index)).map(([level])=>level.template));
    for(const [level]of levels){
      const template=level.template;if(!affected.has(template))continue;let key;
      if(used.has(template)){
        key=stairId(template+'__stairs_'+level.index);let n=2;
        while(Object.hasOwn(out.floors,key)){key=stairId(template+'__stairs_'+level.index+'_'+n);n++;}
        out.floors[key]=stairClone(sources[template]);const targetLevel=out.levels.find(l=>l.index===level.index);targetLevel.template=key;targetLevel.stair_source_template=template;
        targetLevel.stair_template_instance={schema:'acs.stair-template-instance/1',source_template:template,template:key,level_index:level.index,room_mapping:sources[template].rooms.map(room=>({id:room.id??null,role:room.role??null}))};
      }else{key=template;used.add(template);}
      for(const [index,rid,obj]of plans)if(index===level.index){const room=out.floors[key].rooms.find(r=>r.id===rid);if(!Object.hasOwn(room,'objects'))room.objects=[];room.objects.push(obj);}
    }
    report.generated_connections=plans.length;stairConnections(out);
  }
  if(!Object.hasOwn(out,'meta'))out.meta={};if(!stairDict(out.meta))return [model,null,'STAIR_MODEL_INVALID'];
  out.meta.acs_stairs=stairClone(report);return [out,report,null];
}
export { hasStairForms, hasUStairs, resolveStairGeometry, stairConnections, templateScopeAliases, validateStairReport, withDefaultStairs };

const STAIR_SHA_K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
function stairRotr32(x,n){ return ((x>>>n)|(x<<(32-n)))>>>0; }
function stairUtf8Bytes(str){ const b=[];
  for(let i=0;i<str.length;i++){ const c=str.charCodeAt(i);
    if(c<0x80) b.push(c);
    else if(c<0x800) b.push(0xC0|(c>>6),0x80|(c&63));
    else if(c>=0xD800&&c<=0xDBFF){ const c2=str.charCodeAt(++i);
      const cp=0x10000+((c-0xD800)<<10)+(c2-0xDC00);
      b.push(0xF0|(cp>>18),0x80|((cp>>12)&63),0x80|((cp>>6)&63),0x80|(cp&63)); }
    else b.push(0xE0|(c>>12),0x80|((c>>6)&63),0x80|(c&63)); }
  return b; }
function stairHash(text){
  if(text===null||text===undefined) return null;
  const m=stairUtf8Bytes(String(text)), ml=m.length*8;
  m.push(0x80); while(m.length%64!==56) m.push(0);
  const hi=Math.floor(ml/4294967296), lo=ml>>>0;
  m.push((hi>>>24)&255,(hi>>>16)&255,(hi>>>8)&255,hi&255,
         (lo>>>24)&255,(lo>>>16)&255,(lo>>>8)&255,lo&255);
  let H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const w=new Array(64);
  for(let i=0;i<m.length;i+=64){
    for(let t=0;t<16;t++) w[t]=((m[i+t*4]<<24)|(m[i+t*4+1]<<16)|(m[i+t*4+2]<<8)|m[i+t*4+3])>>>0;
    for(let t=16;t<64;t++){
      const s0=(stairRotr32(w[t-15],7)^stairRotr32(w[t-15],18)^(w[t-15]>>>3))>>>0;
      const s1=(stairRotr32(w[t-2],17)^stairRotr32(w[t-2],19)^(w[t-2]>>>10))>>>0;
      w[t]=(((w[t-16]+s0)>>>0)+((w[t-7]+s1)>>>0))>>>0; }
    let a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
    for(let t=0;t<64;t++){
      const S1=(stairRotr32(e,6)^stairRotr32(e,11)^stairRotr32(e,25))>>>0;
      const ch=((e&f)^((~e)&g))>>>0;
      const t1=(((h+S1)>>>0)+((ch+STAIR_SHA_K[t])>>>0)+w[t])>>>0;
      const S0=(stairRotr32(a,2)^stairRotr32(a,13)^stairRotr32(a,22))>>>0;
      const maj=((a&b)^(a&c)^(b&c))>>>0;
      const t2=(S0+maj)>>>0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0; }
    H=[(H[0]+a)>>>0,(H[1]+b)>>>0,(H[2]+c)>>>0,(H[3]+d)>>>0,
       (H[4]+e)>>>0,(H[5]+f)>>>0,(H[6]+g)>>>0,(H[7]+h)>>>0]; }
  return H.map(x=>('0000000'+x.toString(16)).slice(-8)).join(''); }
