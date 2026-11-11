/* Canonical flat roofs. Pure synchronous twin of acs_roof.py; no scene/storage writes. */
import {sha256Hex} from './standards.js';
import {_pyRound} from './viewer.js';

export const EDGES=Object.freeze(['N','S','W','E']);
export const ROOF_ROOM_PREFIX='roof_';
export const DEFAULT_PARAPET_H=.9;
const EPS=1e-6;
const dict=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const own=(value,key)=>Object.prototype.hasOwnProperty.call(value,key);
const clone=value=>structuredClone(value);
const error=code=>{const failure=new Error(code);failure.code=code;throw failure;};
const round=value=>_pyRound(value,6);
const str=value=>value===null||value===undefined?'None':value===true?'True':value===false?'False':String(value);
function number(value){
  if(typeof value==='number')return value;
  if(typeof value==='boolean')return Number(value);
  if(typeof value!=='string')throw new TypeError('not a number');
  // Python float accepts Unicode decimal digits and underscores between digits.
  // This mirrors the pure helper only; canonical geometry admission stays strict.
  const text=value.trim().replace(/\p{Decimal_Number}/gu,character=>{
    const point=character.codePointAt(0);let start=point;
    while(start>0&&/\p{Decimal_Number}/u.test(String.fromCodePoint(start-1)))start--;
    return String((point-start)%10);
  });
  if(!/^[+-]?(?:(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?|inf(?:inity)?|nan)$/i.test(text))throw new TypeError('not a number');
  return /^[+-]?inf(?:inity)?$/i.test(text)?(text.startsWith('-')?-Infinity:Infinity):Number(text.replaceAll('_',''));
}
function rect(room){
  const r=room?.rect;if(!Array.isArray(r)||r.length!==4)return null;
  try{const values=r.map(number);return values.every(Number.isFinite)&&values[2]>0&&values[3]>0?values:null;}catch(e){return null;}
}
function positiveHeight(value){
  if(value===null||value===undefined)error('ROOF_HEIGHT_NOT_SPECIFIED');
  if(typeof value!=='number'||!Number.isFinite(value)||value<=0)error('ROOF_HEIGHT_INVALID');
  return value;
}
function levelIndex(level){
  const index=level.index;
  if(index===null||index===undefined)error('ROOF_LEVEL_ELEVATION_NOT_SPECIFIED');
  if(!Number.isInteger(index))error('ROOF_LEVEL_ELEVATION_INVALID');
  return index;
}
function elevation(level,floorHeight){
  const index=levelIndex(level),value=own(level,'elevation')?level.elevation:index*floorHeight;
  if(value===null||value===undefined)error('ROOF_LEVEL_ELEVATION_NOT_SPECIFIED');
  if(typeof value!=='number'||!Number.isFinite(value))error('ROOF_LEVEL_ELEVATION_INVALID');
  return value;
}
function edgeSpan(edge,[x,z,w,d]){
  if(edge==='N')return ['x',z,x,x+w];if(edge==='S')return ['x',z+d,x,x+w];
  if(edge==='W')return ['z',x,z,z+d];return ['z',x+w,z,z+d];
}
function sharedLength(edge,r,others){
  const [axis,fixed,a0,a1]=edgeSpan(edge,r),opposite={N:'S',S:'N',W:'E',E:'W'}[edge];let total=0;
  for(const other of others){const [otherAxis,otherFixed,b0,b1]=edgeSpan(opposite,other);if(otherAxis===axis&&Math.abs(otherFixed-fixed)<=EPS)total+=Math.max(0,Math.min(a1,b1)-Math.max(a0,b0));}
  return total;
}
function compareText(a,b){const aa=Array.from(a),bb=Array.from(b);for(let i=0;i<Math.min(aa.length,bb.length);i++){const delta=aa[i].codePointAt(0)-bb[i].codePointAt(0);if(delta)return delta;}return aa.length-bb.length;}
const caveats=()=>['structure','drainage','waterproofing','roof access','code compliance'];
const disclosure=height=>({schema:'acs.roof/1',source:'system_default',form:'flat',parapet_height_m:height,occupied_floor:false});
export function isRoofLevel(level){return dict(level)&&level.kind==='roof';}
export function hasRoofLevel(model){return (model?.levels||[]).some(isRoofLevel);}
export function autoRoofLevels(model){return (model?.levels||[]).filter(level=>isRoofLevel(level)&&level.auto===true);}
export function addFlatRoofLevel(model,parapetH=DEFAULT_PARAPET_H){
  try{parapetH=number(parapetH);}catch(e){error('ROOF_PARAPET_HEIGHT_INVALID');}
  if(!(parapetH>=0&&parapetH<=2))error('ROOF_PARAPET_HEIGHT_INVALID');
  if(!dict(model))error('ROOF_MODEL_INVALID');if(hasRoofLevel(model))error('ROOF_LEVEL_EXISTS');
  const out=clone(model),levels=out.levels||[],floors=out.floors||{};
  const occupied=levels.filter(level=>dict(level)&&own(floors,level.template));
  if(!occupied.length)error('ROOF_NO_OCCUPIED_LEVEL');
  const wallH=positiveHeight(out.wall_h),floorHeight=positiveHeight(out.floor_height);
  for(const level of occupied)elevation(level,floorHeight);
  const top=occupied.reduce((a,b)=>{
    const order=elevation(a,floorHeight)-elevation(b,floorHeight)||levelIndex(a)-levelIndex(b)||compareText(str(a.template??''),str(b.template??''));return order>=0?a:b;
  });
  const roofIndex=Math.max(...levels.filter(dict).map(levelIndex))+1;
  const topRooms=(floors[top.template].rooms||[]).map(room=>[room,rect(room)]).filter(([,r])=>r!==null);
  if(!topRooms.length)error('ROOF_TOP_LEVEL_HAS_NO_ROOMS');
  const topWall=Math.max(...topRooms.map(([room])=>positiveHeight(own(room,'wall_h')?room.wall_h:wallH)));
  const rise=floorHeight>=topWall+.15-EPS?floorHeight:topWall+.15,roofElevation=round(elevation(top,floorHeight)+rise);
  let template='roof',n=2;while(own(floors,template))template='roof_'+n++;
  const rects=topRooms.map(([,r])=>r),roofRooms=[],gaps=[],used=new Set();let parapetM=0;
  for(const [room,r]of topRooms){
    const others=rects.filter(other=>other!==r),walls=[],roomGaps=[];
    for(const edge of EDGES){const [,,a0,a1]=edgeSpan(edge,r),length=a1-a0,shared=sharedLength(edge,r,others);
      if(shared<=EPS){walls.push(edge);parapetM+=length;}
      else if(shared<length-EPS){const gap={edge,open_length_m:round(length-shared)};gaps.push({room_id:room.id??null,...gap});roomGaps.push(gap);}
    }
    let base=ROOF_ROOM_PREFIX+str(room.id||'deck');
    if(Array.from(base).length>160)base=Array.from(base).slice(0,139).join('')+'_'+sha256Hex(base).slice(0,20);
    let id=base,k=2;while(used.has(id)){const suffix='_'+k++;id=Array.from(base).slice(0,160-suffix.length).join('')+suffix;}used.add(id);
    const roofRoom={id,name:'سطح',role:'roof_deck',auto:true,rect:r.slice(),walls:parapetH>0?walls:'none',doors:[],windows:[],points:[],roof_provenance:{source:'system_default',source_room_id:room.id??null,parapet_gaps:parapetH>0?roomGaps:[]}};
    if(parapetH>0)roofRoom.wall_h=parapetH;roofRooms.push(roofRoom);
  }
  floors[template]={rooms:roofRooms};levels.push({index:roofIndex,template,kind:'roof',auto:true,name:'السطح',elevation:roofElevation});out.levels=levels;out.floors=floors;
  return [out,{schema:'acs.roof/1',form:'flat',source:'system_default',level_index:roofIndex,template,elevation_m:roofElevation,parapet_height_m:parapetH,parapet_length_m:round(parapetH>0?parapetM:0),deck_area_m2:round(rects.reduce((sum,r)=>sum+r[2]*r[3],0)),parapet_gaps:gaps,occupied_floor:false,not_verified:caveats()}];
}
export function withDefaultRoof(model,parapetH=DEFAULT_PARAPET_H){
  if(!dict(model))return [model,null,'ROOF_MODEL_INVALID'];if(hasRoofLevel(model))return [model,null,'ROOF_LEVEL_EXISTS'];
  let out,report;try{[out,report]=addFlatRoofLevel(model,parapetH);}catch(e){if(e.code?.startsWith('ROOF_'))return [model,null,e.code];throw e;}
  out.meta={...(dict(out.meta)?out.meta:{}),acs_roof:disclosure(report.parapet_height_m)};return [out,report,null];
}
function parapetOf(model){
  for(const level of autoRoofLevels(model))for(const room of model.floors?.[level.template]?.rooms||[]){
    if(dict(room)&&room.wall_h!==null&&room.wall_h!==undefined){try{return number(room.wall_h);}catch(e){break;}}
    if(dict(room)&&room.walls==='none')return 0;
  }return DEFAULT_PARAPET_H;
}
export function isAutoRoofTemplate(model,template){return autoRoofLevels(model).some(level=>level.template===template);}
export function roofRemovedByUser(model){return dict(model?.meta)&&dict(model.meta.acs_roof)&&model.meta.acs_roof.removed_by_user===true;}
export function markRoofRemoved(model){const out=clone(model);out.meta={...(dict(out.meta)?out.meta:{}),acs_roof:{schema:'acs.roof/1',source:'user',removed_by_user:true}};return out;}
function stripAutoLevels(out,previous){
  const templates=new Set(previous.map(level=>level.template));out.levels=(out.levels||[]).filter(level=>!(isRoofLevel(level)&&level.auto===true));
  const floors=dict(out.floors)?out.floors:{},stillUsed=new Set(out.levels.filter(dict).map(level=>level.template));
  for(const template of templates)if(!stillUsed.has(template))delete floors[template];out.floors=floors;
}
export function carryAutoRoof(beforeModel,candidate){
  if(roofRemovedByUser(beforeModel)&&dict(candidate)){if(hasRoofLevel(candidate))error('ROOF_PREFERENCE_CONFLICT');return markRoofRemoved(candidate);}
  const previous=autoRoofLevels(beforeModel);if(!previous.length||!dict(candidate))return candidate;
  const height=parapetOf(beforeModel);let out=clone(candidate);stripAutoLevels(out,previous);
  const meta={...(dict(out.meta)?out.meta:{})};delete meta.acs_roof;
  if(!hasRoofLevel(out)){
    try{[out]=addFlatRoofLevel(out,height);meta.acs_roof=disclosure(height);}
    catch(e){if(!e.code?.startsWith('ROOF_'))throw e;meta.acs_roof={schema:'acs.roof/1',source:'system_default',omitted:e.code};}
  }
  if(Object.keys(meta).length||dict(candidate.meta))out.meta=meta;return out;
}
export function removeAutoRoof(model){const previous=autoRoofLevels(model);if(!previous.length)error('ROOF_NOT_AUTOMATIC');const out=clone(model);stripAutoLevels(out,previous);return markRoofRemoved(out);}
export function restoreDefaultRoof(model,parapetH=DEFAULT_PARAPET_H){
  if(hasRoofLevel(model))error('ROOF_LEVEL_EXISTS');const base=clone(model);if(dict(base.meta))delete base.meta.acs_roof;
  const [out,,reason]=withDefaultRoof(base,parapetH);if(reason)error(reason);return out;
}
export function roofDisclosure(model,level){
  if(!isRoofLevel(level))return null;const rooms=model?.floors?.[level.template]?.rooms||[],gaps=[];let complete=!!rooms.length;
  for(const room of rooms){const provenance=dict(room)?room.roof_provenance:null;if(!dict(provenance)||provenance.source!=='system_default'){complete=false;continue;}
    const declared=provenance.parapet_gaps;if(!Array.isArray(declared)){complete=false;continue;}
    for(const gap of declared){const length=dict(gap)?gap.open_length_m:null;if(!dict(gap)||!EDGES.includes(gap.edge)||typeof length!=='number'||!Number.isFinite(length)||length<=0){complete=false;continue;}
      gaps.push({room_id:room.id??null,source_room_id:provenance.source_room_id??null,edge:gap.edge,open_length_m:length});}
  }
  return {source:level.auto===true?'system_default':'declared',parapet_gaps:gaps,gap_coverage:complete?'DECLARED_AUTO_ROOF_EDGES':'NOT_VERIFIED',not_verified:caveats()};
}
