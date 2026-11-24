// Authored local residential scheme. Coordinates are metres, x east and z south.
// The apartment wing is mirrored about the common entrance. All floor/room
// instances, apertures, furniture and stairs are part of the exported model.
import { withDefaultStairs } from './stairs.mjs';
import { withContextDetails } from './context-details.mjs';

const round = value => Math.round(value * 1000) / 1000;
const wallThickness=0.18;
const levelsAr = ['الأرضي', 'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس'];
const opposite = { N: 'S', S: 'N', E: 'W', W: 'E' };

function unsupported(message) {
  const error = new Error(message);
  error.code = 'LOCAL_APARTMENT_UNSUPPORTED';
  throw error;
}

function rectangle(id, name, role, rect, unit) {
  const room = {id, name, role, rect, wall_color: '#deccb0', floor_color: '#d6c3a7', doors: [], windows: []};
  if (unit) room.unit_id = unit;
  return room;
}

function sharedWall(a, b) {
  const [x,z,w,d] = a.rect, [bx,bz,bw,bd] = b.rect;
  const eq = (m,n) => Math.abs(m - n) < 0.002;
  if (eq(x+w,bx) || eq(x,bx+bw)) return [eq(x+w,bx) ? 'E':'W', Math.max(z,bz), Math.min(z+d,bz+bd), z, bz];
  if (eq(z+d,bz) || eq(z,bz+bd)) return [eq(z+d,bz) ? 'S':'N', Math.max(x,bx), Math.min(x+w,bx+bw), x, bx];
  throw new Error('LOCAL_APARTMENT_ROOMS_NOT_ADJACENT');
}

// Emit corresponding real cuts in both room shells at the same world position.
function connect(a,b,desired = 0.95, material = 'wood') {
  const [edge,start,end,fromA,fromB] = sharedWall(a,b);
  const width = round(Math.min(desired, end-start-0.24));
  if (width < 0.75) throw new Error('LOCAL_APARTMENT_DOOR_TOO_NARROW');
  const center = (start+end)/2;
  const door = (room, other, side, origin) => ({
    id: room.id+'_to_'+other.id, edge: side, offset: round(center-origin), width, height: 2.18, material,
    acs_door_pair:{id:'door|'+[room.id,other.id].sort().join('|'),peer_room_id:other.id}
  });
  a.doors.push(door(a,b,edge,fromA));
  b.doors.push(door(b,a,opposite[edge],fromB));
}

// A pair owns a single physical leaf. Both cuts and both original IDs stay on
// their host walls. Validate at projection time, including for edited/imported JSON.
const leafKeys = new Set(['id','edge','offset','width','height','material','color','acs_door_pair']);
function doorPairPoint(room,door) {
  if(!Array.isArray(room.rect)||room.rect.length!==4||!room.rect.every(Number.isFinite)||
     !Object.hasOwn(opposite,door.edge)||!Number.isFinite(door.width)||!Number.isFinite(door.height)||
     !Number.isFinite(door.offset)||door.width<=0||door.height<=0||
     Object.keys(door).some(key=>!leafKeys.has(key))) return null;
  const [x,z,w,d]=room.rect, side=door.edge==='E'||door.edge==='W', span=side?d:w;
  if(w<=0||d<=0||door.offset<door.width/2||door.offset+door.width/2>span) return null;
  return side?[x+(door.edge==='E'?w:0),z+door.offset]:[x+door.offset,z+(door.edge==='S'?d:0)];
}

export function apartmentDoorPairs(rooms) {
  const groups=new Map(), ids=new Set(), duplicates=new Set(), result=new Map();
  for(const room of rooms) {
    if(!room||typeof room.id!=='string') continue;
    if(ids.has(room.id)) duplicates.add(room.id);
    ids.add(room.id);
    if(!Array.isArray(room.doors)) continue;
    room.doors.forEach((door,index)=>{
      const id=door?.acs_door_pair?.id;
      if(typeof id!=='string'||!id||id.length>160) return;
      if(!groups.has(id)) groups.set(id,[]);
      groups.get(id).push({room,door,index});
    });
  }
  for(const [pair_id,claims] of groups) {
    if(claims.length!==2) continue;
    claims.sort((a,b)=>a.room.id<b.room.id?-1:a.room.id>b.room.id?1:0);
    const [a,b]=claims;
    if(a.room.id===b.room.id||duplicates.has(a.room.id)||duplicates.has(b.room.id)||
       a.door.acs_door_pair.peer_room_id!==b.room.id||b.door.acs_door_pair.peer_room_id!==a.room.id||
       typeof a.door.id!=='string'||typeof b.door.id!=='string'||!a.door.id||!b.door.id||a.door.id===b.door.id||
       opposite[a.door.edge]!==b.door.edge||
       ['width','height','material','color'].some(k=>a.door[k]!==b.door[k])) continue;
    const p=doorPairPoint(a.room,a.door), q=doorPairPoint(b.room,b.door);
    // The local model records offsets to the nearest millimetre.
    if(!p||!q||p.some((v,i)=>Math.abs(v-q[i])>0.00101)) continue;
    const hosts=claims.map(c=>({room_id:c.room.id,door_id:c.door.id,door_index:c.index}));
    for(const claim of claims) result.set(claim.door,{primary:claim===a,pair_id,hosts});
  }
  return result;
}

function windowAt(room,edge,fraction,width,sill=0.76,height=1.78) {
  const span = room.rect[['N','S'].includes(edge) ? 2 : 3];
  const offset = fraction*span;
  room.windows.push({id:room.id+'_window_'+room.windows.length,edge,offset:round(offset),
    width:round(Math.min(width,2*Math.min(offset,span-offset)-0.28)),sill,height});
}

function object(room,kind,name,x,z,w,d,h,rot=0,y=0) {
  (room.objects ||= []).push({id:room.id+'_'+kind+'_'+room.objects.length,
    kind,name,x:round(x),z:round(z),w:round(w),d:round(d),h:round(h),rot,y:round(y)});
}

function furnish(r) {
  function place(room,kind,name,fx,fz,w,d,h,rot=0) {
    object(room,kind,name,room.rect[2]*fx,room.rect[3]*fz,w,d,h,rot);
  }
  place(r.living,'sofa','كنبة المعيشة',0.38,0.34,2.35,0.92,0.82);
  place(r.living,'armchair','كرسي',0.27,0.59,0.85,0.86,0.8,90);
  place(r.living,'table','طاولة القهوة',0.56,0.53,1.05,0.55,0.42);
  place(r.majlis,'sofa','كنبة الضيوف',0.49,0.26,2.3,0.82,0.78);
  place(r.majlis,'armchair','كرسي ضيافة',0.25,0.56,0.78,0.8,0.78,90);
  place(r.dining,'dining','طاولة لستة',0.43,0.5,1.76,0.85,0.76);
  for(const side of [-1,1]) for(const dx of [-0.60,0,0.60]) {
    object(r.dining,'chair','كرسي طعام',r.dining.rect[2]*0.43+dx,r.dining.rect[3]/2+side*0.7,0.42,0.43,0.84,side<0?180:0);
  }
  place(r.kitchen,'cabinet','سطح تحضير',0.13,0.40,0.55,1.95,0.9);
  place(r.kitchen,'fridge','ثلاجة',0.16,0.84,0.72,0.66,1.8);
  place(r.kitchen,'oven','فرن',0.40,0.85,0.60,0.65,0.90);
  place(r.kitchen,'sink','حوض المطبخ',0.15,0.21,0.50,0.46,0.94);
  for(const room of [r.master,r.bed1,r.bed2]) {
    place(room,'bed','سرير',0.43,0.48,room===r.master?1.70:1.14,1.95,0.55);
    place(room,'wardrobe','خزانة',0.24,0.87,1.38,0.54,2.15);
  }
}

function floorPlan(width,depth,index,storeyHeight,{courtyard=false}={}) {
  // The compiler centres walls on room boundaries. Specify the external
  // envelope first, then locate the wall axes one half-thickness inside it.
  const axisX=x=>round(wallThickness/2+x*(width-wallThickness)/20);
  // In a narrow building turned to the side, reserve enough length for the
  // fixed stair flights and landings, distributing the rest to the two wings.
  const clearDepth=depth-wallThickness;
  const coreDepth=Math.max(4,4.8*clearDepth/25), wingScale=(clearDepth-coreDepth)/(25-4.8);
  const axisZ=z=>{
    const inCore=Math.max(0,Math.min(z-7.2,4.8));
    return round(wallThickness/2+(z-inCore)*wingScale+inCore*coreDepth/4.8);
  };
  const rect=(x,z,w,d)=>[axisX(x),axisZ(z),round(axisX(x+w)-axisX(x)),round(axisZ(z+d)-axisZ(z))];
  const entranceDepth=index?0:1.35;
  const lobby=rectangle('lobby',index?'بسطة وبهو مشترك':'بهو المدخل','lobby',rect(8,entranceDepth,4,7.2-entranceDepth));
  const stair=rectangle('stair','الدرج المشترك','stairs',rect(8,7.2,2.4,4.8));
  // With a court, the lift moves one bay east to give the shared lobby a
  // route to the garden without passing through either private apartment.
  const lift=rectangle('lift','حيّز المصعد المقترح','elevator',courtyard?rect(12,9.5,1.8,2.5):rect(10.4,7.2,1.6,4.8));
  stair.core_id='central'; lift.core_id='lift';
  lobby.wall_color='#bfab90'; lobby.floor_color='#b6a286';
  const rooms=[lobby,stair,lift];
  connect(lobby,stair,1.0);
  if(courtyard) {
    const passage=rectangle('court_passage','ممر الفناء المشترك','corridor',rect(10.4,7.2,1.6,4.8));
    rooms.push(passage);
    connect(lobby,passage,1.16); connect(passage,lift,0.90,'metal');
    if(index===0) {
      passage.doors.push({id:'court_ground_door',edge:'S',offset:round(passage.rect[2]/2),width:1.05,height:2.18,material:'glass'});
    } else {
      windowAt(passage,'S',0.5,1.05,0.95,1.32);
    }
  } else {
    connect(lobby,lift,0.90,'metal');
  }
  if(index===0) {
    const porch=rectangle('entrance_porch','رواق المدخل','porch',rect(8,0,4,entranceDepth));
    porch.walls=[]; porch.floor_color='#9c8265'; rooms.push(porch);
    connect(lobby,porch,1.90,'glass');
    const [,,pw,pd]=porch.rect;
    const canopyHeight=Math.min(2.67,storeyHeight-0.32);
    object(porch,'box','مظلة المدخل',pw/2,pd/2,pw-0.06,pd-0.04,0.15,0,canopyHeight);
    porch.objects.at(-1).color='#795c42';
    for(const px of [0.20,pw-0.20]) {
      object(porch,'column','دعامة الرواق',px,0.22,0.20,0.24,canopyHeight);
      porch.objects.at(-1).color='#b6a186';
    }
    windowAt(lobby,'N',0.105,0.50,0.30,2.15);
    windowAt(lobby,'N',0.895,0.50,0.30,2.15);
  } else windowAt(lobby,'N',0.5,3.0,0.28,2.15);

  for(const unit of ['west','east']) {
    const r={}, side=unit==='west'?'W':'E';
    const add=(id,name,role,x,z,w,d) => {
      const pos=rect(unit==='west'?x:20-x-w,z,w,d);
      const room=rectangle(unit+'_'+id,name,role,pos,unit);
      r[id]=room; rooms.push(room);
      return room;
    };
    const balconyDepth=index ? 1.6 : 0;
    if(index) {
      const balcony=add('balcony','شرفة غائرة','balcony',0,0,4.4,balconyDepth);
      balcony.walls=[]; balcony.floor_color='#aa8460';
      const [,,bw,bd]=balcony.rect, exteriorX=unit==='west'?0.09:bw-0.09;
      object(balcony,'railing','حاجز الشرفة الأمامي',bw/2,0.09,bw-0.12,0.08,1.10);
      object(balcony,'railing','حاجز الشرفة الجانبي',exteriorX,bd/2,bd-0.12,0.08,1.10,90);
      // A permeable screen shades only the end bay, keeping the sliding door and view clear.
      const screenWidth=bw*0.31;
      const slats=Math.ceil(screenWidth/0.17);
      for(let i=0;i<slats;i++) {
        const x=0.16+(i+0.5)*(screenWidth-0.16)/slats;
        object(balcony,'box','ريشة تظليل',unit==='west'?x:bw-x,0.22,0.065,0.15,storeyHeight-0.25,15);
        balcony.objects.at(-1).color='#865d3b';
      }
    }
    add('living','صالة عائلية','living',0,balconyDepth,4.4,7.2-balconyDepth);
    add('majlis','مجلس الضيوف','majlis',4.4,0,3.6,5);
    add('foyer','مدخل الشقة','entry',4.4,5,3.6,2.2);
    add('dining','صالة الطعام','dining',0,7.2,4.4,3.6);
    add('kitchen','مطبخ','kitchen',0,10.8,4.4,4);
    add('hall','ممر النوم','corridor',4.4,7.2,1.8,12.8);
    add('guest_wc','دورة مياه الضيوف','bathroom',6.2,7.2,1.8,2.3);
    const relocatedLaundry=courtyard && unit==='east';
    const serviceWidth=courtyard?1.8:3.8;
    add('laundry','غرفة غسيل','laundry',6.2,relocatedLaundry?12:9.5,1.8,relocatedLaundry?1.5:2.5);
    const storeStart=relocatedLaundry?13.5:12, bathStart=relocatedLaundry?15:14;
    add('store','مخزن','storage',6.2,storeStart,serviceWidth,bathStart-storeStart);
    add('bath','حمام مشترك','bathroom',6.2,bathStart,serviceWidth,17-bathStart);
    if(courtyard) {
      windowAt(r.bath,opposite[side],0.5,0.9,1.55,0.65);
      windowAt(r.store,opposite[side],0.5,0.75,1.32,0.8);
    }
    add('wardrobe','غرفة ملابس','closet',6.2,17,1.9,3);
    add('ensuite','حمام الجناح','bathroom',8.1,17,1.9,3);
    add('bed1','غرفة نوم ١','bedroom',0,14.8,4.4,3.7);
    add('bed2','غرفة نوم ٢','bedroom',0,18.5,4.4,6.5);
    add('master','غرفة النوم الرئيسية','bedroom',4.4,20,5.6,5);
    connect(lobby,r.foyer,1.05);
    connect(r.foyer,r.majlis); connect(r.foyer,r.guest_wc,0.8);
    connect(r.foyer,r.living,1.15); connect(r.foyer,r.hall);
    connect(r.living,r.dining,1.65); connect(r.dining,r.kitchen,1.08);
    for (const id of ['kitchen','laundry','store','bath','bed1','bed2','master']) connect(r.hall,r[id]);
    connect(r.master,r.wardrobe,0.85); connect(r.master,r.ensuite,0.85);
    if(index) connect(r.living,r.balcony,2.45,'glass');
    else windowAt(r.living,'N',0.5,3.05,0.52,2.04);
    windowAt(r.majlis,'N',0.5,2.53,0.61,1.96);
    for(const id of ['living','dining','kitchen','bed1','bed2']) windowAt(r[id],side,0.5,id==='living'?3.15:2.1,id==='kitchen'?1.08:0.78,id==='kitchen'?1.28:1.77);
    windowAt(r.bed2,'S',0.5,2.6); windowAt(r.master,'S',0.53,3.12);
    if(!index && unit==='west') furnish(r);
  }
  if(!courtyard) return {rooms};
  return {rooms,courtyards:[{id:'central_courtyard',name:'فناء مفتوح للسماء',rect:rect(8,12,4,5)}]};
}

const assumptions = [
  'مخطط محلي مفاهيمي بشقتين وثلاث غرف نوم لكل شقة. أبعاد الغرف الفعلية مشتقة من المخطط وقد تختلف عن الأهداف النصية.',
  'الدرجات والبسطات وفتحات البلاطات ممثلة بين الأدوار السكنية. المصعد حيّز مقترح، والوصول إلى سطح الخدمات يحتاج إلى تصميم.',
  'الأثاث والتشطيبات اقتراحات للمقياس. مجاري الخدمات والمواقف والارتدادات والتحقق الإنشائي والتنظيمي تحتاج إلى مراجعة مستقلة.'
];

const compass = ['N','E','S','W'];

// Rotate the actual plan in the fixed north-up coordinate system, including
// room-local aperture offsets, furniture and voids. Stairs are fitted later
// against the transformed door and landing, using their normal authoring path.
function turnFloor(floor, depth) {
  const turnRect = ([x,z,w,d]) => [round(depth-z-d),x,d,w];
  for (const room of floor.rooms) {
    const roomDepth = room.rect[3];
    for (const opening of [...room.doors, ...room.windows]) {
      if (opening.edge === 'E' || opening.edge === 'W') opening.offset = round(roomDepth-opening.offset);
      opening.edge = compass[(compass.indexOf(opening.edge)+1)%4];
    }
    for (const object of room.objects || []) {
      [object.x,object.z] = [round(roomDepth-object.z),object.x];
      object.rot = ((object.rot || 0)+90)%360;
    }
    if (Array.isArray(room.walls)) room.walls = room.walls.map(edge => compass[(compass.indexOf(edge)+1)%4]);
    room.rect = turnRect(room.rect);
  }
  for (const court of floor.courtyards || []) court.rect = turnRect(court.rect);
}

function design(width,depth,levels,height,source,{entrance='N',courtyard=false}={}) {
  if(!Number.isFinite(width)||width<18||width>32||!Number.isFinite(depth)||depth<22||depth>36)
    unsupported('أدخل أبعاد المبنى الخارجية. يدعم هذا التوزيع واجهة بين 18 و32 م وعمقاً بين 22 و36 م.');
  if(!Number.isInteger(levels)||levels<1||levels>6)
    unsupported('يدعم مخطط الشقق المحلي من دور سكني واحد إلى ستة أدوار شاملة الأرضي.');
  if(!Number.isFinite(height)||height<2.8||height>3.6)
    unsupported('يدعم الدرج المحلي ارتفاع دور موحّداً بين 2.8 و3.6 م.');
  const title='عمارة سكنية '+width+' × '+depth+' م';
  const turns=compass.indexOf(entrance);
  const model={
    meta:{name:title,type:'residential',north:'-Z',acs_apartment:{schema:'acs.local-apartment/1',source,width_m:width,depth_m:depth,
      occupied_levels:levels,units_per_floor:2,units_total:2*levels,bedrooms_per_unit:3,street_edge:entrance,
      courtyard,unit_edges:{west:compass[(3+turns)%4],east:compass[(1+turns)%4]},
      wall_reference:'room_wall_centrelines',outer_face_offset_m:wallThickness/2,assumptions:[...assumptions]}},
    site:{w:width,d:depth},floor_height:height,wall_h:round(height-0.18),wall_t:wallThickness,levels:[],floors:{}
  };
  for(let i=0;i<levels;i++) {
    const template='level_'+i;
    model.levels.push({index:i,name:levelsAr[i],elevation:round(i*height),template});
    const startWidth=turns%2 ? depth : width;
    const startDepth=turns%2 ? width : depth;
    const floor=floorPlan(startWidth,startDepth,i,height,{courtyard});
    for(let turn=0;turn<turns;turn++) turnFloor(floor,turn%2 ? startWidth : startDepth);
    model.floors[template]=floor;
  }
  if(levels===1) return model;
  const [result,report,reason]=withDefaultStairs(model);
  if(reason || report.generated_connections!==levels-1) unsupported('تعذّر وصل الدرج ضمن الأبعاد المحددة. راجع عرض المبنى وعمقه وارتفاع الدور.');
  return result;
}

export function apartmentSample() {
  return design(20,25,3,3.4,'synthetic_sample');
}

function normalize(text) {
  return String(text||'').toLowerCase().replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)%16))
    .replace(/[\u064b-\u065f\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/٫/g,'.');
}
const numberWord={'واحد':1,'واحده':1,'اثنان':2,'اثنين':2,'ثلاث':3,'ثلاثه':3,'اربع':4,'اربعه':4,'خمس':5,'خمسه':5,'ست':6,'سته':6,'سبع':7,'سبعه':7,'ثمانيه':8,'ثمان':8,'تسعه':9,'عشره':10};
const count='(\\d+|'+Object.keys(numberWord).sort((a,b)=>b.length-a.length).join('|')+')';
const asCount = value=>Number.isNaN(Number(value))?numberWord[value]:Number(value);
const decimal='(\\d+(?:\\.\\d+)?)';
function singleRequestedValue(values,label) {
  const unique=[...new Set(values)];
  if(unique.length>1) unsupported('ورد في وصفك أكثر من رقم يحدد '+label+' ('+unique.join(' و')+'). اختر رقماً واحداً لهذا الشرط ثم أعد التوليد.');
  return unique[0];
}

function dimensions(text) {
  // Only the building introduction supplies exterior dimensions. Room goals
  // and numbered programme headings in subsequent paragraphs are unrelated.
  const intro=text.split(/\n\s*\n|(?:مجلس|غرفه نوم|صاله عائليه|مطبخ)/)[0].slice(0,650);
  const lot=/(?:قطعه\s+(?:ال)?ارض|(?:على|ابعاد|مساحه)\s+(?:ال)?ارض|(?:^|[\s،.,])(?:ال)?ارض\s+(?=\d|بمقاس|بابعاد|مساحتها|مقاسها))/.test(intro);
  const buildingTerms=/(?:ابعاد|مقاس|مسطح|بصمه|عرض|عمق|طول)\s+(?:المبنى|العماره|البنايه)/.exec(intro);
  if(lot && !buildingTerms) unsupported('ذكرت أبعاد الأرض. حدّد عرض المبنى وعمقه بعد الارتدادات لاستخدام مخطط الشقق المحلي.');
  const first=buildingTerms?intro.slice(buildingTerms.index):intro;
  const pair = first.match(new RegExp(decimal+'\\s*(?:متر|م)?\\s*(?:[×x*]|في|بـ?)\\s*'+decimal+'(?:\\s*(?:متر|م))?'));
  const frontage = first.match(new RegExp(decimal+'\\s*(?:مترا?|م)?\\s*(?:على\\s+)?واجهه'));
  const depth = first.match(new RegExp(decimal+'\\s*(?:مترا?|م)?\\s*عمق'));
  const qualified='(?:ها|ه|\\s+(?:المبنى|العماره|البنايه))?\\s*[:=]?\\s*';
  const dw=first.match(new RegExp('(?:عرض|واجهه)'+qualified+decimal));
  const dd=first.match(new RegExp('(?:عمق|طول)'+qualified+decimal));
  const building='\\s+(?:المبنى|العماره|البنايه)(?:\\s+الخارجيه?)?\\s*[:=]?\\s*';
  const namedValues=axis=>[...text.matchAll(new RegExp(axis+building+decimal,'g'))].map(m=>Number(m[1]));
  const namedSizes=[...text.matchAll(new RegExp('(?:ابعاد|مقاس|بصمه)'+building+decimal+'\\s*(?:مترا?|م)?\\s*(?:[×x*]|في)\\s*'+decimal,'g'))];
  const labelW=singleRequestedValue([...namedValues('عرض'),...namedSizes.map(m=>Number(m[1]))],'عرض المبنى');
  const labelD=singleRequestedValue([...namedValues('(?:عمق|طول)'),...namedSizes.map(m=>Number(m[2]))],'عمق المبنى');
  return [labelW??(dw||frontage)?.[1]??pair?.[1],labelD??(dd||depth)?.[1]??pair?.[2]].map(v=>v===undefined?undefined:Number(v));
}

function occupiedFloorCount(text) {
  const counts=[];
  const intro=text.split(/\n\s*\n/)[0];
  const numberPhrase=new RegExp(count+'\\s*(?:ادوار|طوابق|floors|storeys)|(?:دورين|دوران|طابقين|طابقان)(?![ء-ي])|(?:دور|طابق)\\s+واحد','g');
  for(const match of text.matchAll(numberPhrase)) {
    const before=text.slice(0,match.index), after=text.slice(match.index+match[0].length);
    // "في الدورين الأول والثاني" describes access to balconies, not the
    // occupied floor count. A fresh clause or "من دورين" declares a count.
    if(!match[1]&&(match.index>=intro.length || /(?:ال|(?:كل|مخطط|توزيع|عزل|اختيار)\s+)$/.test(before))) continue;
    const countValue=match[1]?asCount(match[1]):match[0].endsWith('واحد')?1:2;
    const addsGround=/(?:^|[\s،.,])(?:ال)?ارضي\s*[,،]?\s*(?:و\s*(?:(?:فوقه|فوقها)\s*)?|زائد\s*|بالاضافه\s+الى\s*)$/.test(before) ||
      /^(?:\s+(?:علويه?|اضافيه?))?\s+فوق(?:ه|ها|(?:\s+(?:(?:الدور|الطابق)\s+)?الارضي))/.test(after);
    const inclusive=/^\s+(?:تشمل|تتضمن|شامله?|بما\s+فيها?)(?:\s+(?:الدور|الطابق))?\s+الارضي/.test(after);
    if(addsGround&&inclusive) unsupported('ذكرت الأرضي منفصلاً ثم شملته في العدد. حدّد إجمالي الأدوار شاملاً الأرضي، أو اذكر الأدوار التي تعلوه.');
    counts.push(countValue+(addsGround?1:0));
  }
  return singleRequestedValue(counts,'إجمالي الأدوار شاملة الأرضي');
}

const directions={شمال:'N',شرق:'E',جنوب:'S',غرب:'W'};
const directionWord='(شمال|شرق|جنوب|غرب)(?:ي(?:ه)?|ا)?';
const orientationPrefix='(?:(?:ال|لل|ب)?(?:مبنى|عماره|بنايه|شارع|رئيسي|واحد|مدخل|واجهه|جهه|ناحيه|طرف|منتصف|وسط)|يكون|تكون|من|في|على|الي|الى|نحو|باتجاه|بالاتجاه|علي)\\s*';
function entranceDirection(text) {
  const edges=new Set();
  // In a relocation the trailing direction is the goal, the first is the origin.
  const target=text.replace(new RegExp('من\\s+(?:جهه\\s+)?(?:ال)?'+directionWord+'\\s+(?:الي|الى|لـ?)\\s*','g'),'الى ');
  const pattern=new RegExp('(?:مدخل|دخول|واجهه|شارع)(?:ها|ه)?\\s*(?:'+orientationPrefix+'){0,10}(?:ال|لل|ب)?'+directionWord,'g');
  for(const match of target.matchAll(pattern)) {
    edges.add(directions[match[1]]);
    const alternative=target.slice(match.index+match[0].length).match(new RegExp('^\\s*(?:او|و|/)\\s*(?:ال)?'+directionWord));
    if(alternative) edges.add(directions[alternative[1]]);
  }
  if(edges.size>1) unsupported('ذكرت أكثر من جهة للمدخل أو واجهة الشارع. حدّد جهة واحدة للمدخل الرئيسي، أو احتفظ بالتوزيع الحالي.');
  if(edges.size && /(?:شمال|جنوب)(?:ي(?:ه)?)?\s+(?:ال)?(?:شرق|غرب)/.test(target))
    unsupported('يدعم هذا المخطط مدخلاً على إحدى الواجهات الأربع. اختر الشمال أو الشرق أو الجنوب أو الغرب.');
  return [...edges][0];
}

function courtyardChoice(text) {
  const noun='(?:فناء|حوش|باحه)';
  if(!new RegExp(noun).test(text)) return undefined;
  const removed=new RegExp('(?:بدون|بلا|من دون|احذف|ازل|الغ|شيل|ما ابي|لا اريد)\\s*(?:ال)?'+noun);
  if(removed.test(text)) {
    if(new RegExp(noun).test(text.replace(removed,''))) unsupported('ورد طلب بإزالة الفناء والإبقاء عليه في الوصف نفسه. اختر إضافة الفناء أو حذفه.');
    return false;
  }
  const courtScope=text.match(/(?:فناء|باحه|حوش)[^،,.!\n]{0,70}/)?.[0]||'';
  if(/مسقوف|مغط[ىي]|جانبي|امامي|خلفي|ب(?:ابعاد|مقاس|مساحه)|\d+\s*(?:[×x*]|في|متر)/.test(courtScope))
    unsupported('يدعم هذا التوزيع فناءً في الوسط مفتوحاً للسماء، بأبعاد تتناسب مع مساحة المبنى. اختر هذا الفناء أو احتفظ بالتوزيع الحالي.');
  if(/(?:حافظ|احتفظ|نفس|دون تغيير|بدون تغيير)[^،,.!\n]{0,14}(?:مساحات|ابعاد|مساحه)\s+(?:(?:جميع|كل)\s+)?(?:الغرف|غرف|الشقتين|الشقق)/.test(text))
    unsupported('يأخذ الفناء مساحة من غرف الخدمات داخل المحيط الحالي. اختر السماح بتغيير مساحاتها مع حفظ عدد الشقق، أو احتفظ بالمخطط الحالي.');
  return true;
}

export function apartmentFromBrief(text,defaults={}) {
  const t=normalize(text);
  if(!/(?:عماره|عمار[هة]|مبنى\s+سكني|بنايه\s+سكنيه|apartment\s+building|residential\s+building)/.test(t.slice(0,260))) return null;
  if(/^(?:صمم\s+|انشئ\s+|ابن\s+)?(?:مستودع|مصنع|فيلا|مدرسه)/.test(t.trim())) return null;
  const model=buildRequestedApartment(t,defaults,{entrance:entranceDirection(t),courtyard:courtyardChoice(t)});
  model.meta.acs_apartment.brief=String(text);
  return model;
}

function buildRequestedApartment(t,{width=20,depth=25,levels=3,height=3.4},options) {
  const explicitSize=dimensions(t);
  width=explicitSize[0]??width; depth=explicitSize[1]??depth;
  const statedFloors=occupiedFloorCount(t);
  if(statedFloors!==undefined) levels=statedFloors;
  else if(/(?:دور\s+|طابق\s+)?ارضي[^.\n]{0,70}(?:اول)[^.\n]{0,40}(?:ثان)/.test(t)) levels=3;
  const perFloor=t.match(new RegExp(count+'\\s*شقق?\\s*(?:في|ب|لكل)\\s*(?:كل\\s+)?(?:دور|طابق)')) || t.match(new RegExp('(?:في|ب)\\s*كل\\s*(?:دور|طابق)\\s*'+count+'\\s*شقق?'));
  const total=t.match(new RegExp('(?:ب?اجمالي|مجموع(?:ها)?)\\s*'+count+'\\s*شقق?'));
  if((perFloor&&asCount(perFloor[1])!==2)||(total&&asCount(total[1])!==2*levels)||/(?:شقه\s+(?:واحده\s+)?(?:بكل|لكل|في كل)\s+دور|كل دور\s+شقه\s+واحده)/.test(t))
    unsupported('يدعم هذا المخطط المحلي شقتين في كل دور. راجع عدد الشقق والأدوار قبل الإنشاء.');
  const bedroomCount=t.match(new RegExp(count+'\\s*غرف(?:ه)?\\s*نوم(?:\\s+(?:في|ب|لكل)\\s*(?:كل\\s+)?شقه)')) ||
    t.match(new RegExp('(?:في كل شقه|لكل شقه|تتكون كل شقه من)\\s*'+count+'\\s*غرف(?:ه)?\\s*نوم'));
  if(bedroomCount && asCount(bedroomCount[1])!==3)
    unsupported('يدعم هذا التوزيع ثلاث غرف نوم في كل شقة. يلزم توزيع آخر لعدد غرف النوم المطلوب.');
  if(/قبو|بدروم/.test(t.replace(/(?:لا\s+(?:يوجد|اريد|يتضمن|يشمل)?\s*|بلا\s*|بدون\s*|من دون\s*)(?:اي\s*)?(?:قبو|بدروم)/g,'')))
    unsupported('يتضمن وصفك قبواً. يدعم مخطط الشقق المحلي الأدوار فوق الأرض فقط.');
  const storey=t.match(new RegExp('ارتفاع\\s+(?:(?:كل|بين)\\s+)?(?:ال)?(?:دور|طابق)(?:\\s+الواحد)?\\s*[:=]?\\s*'+decimal));
  if(storey) height=+storey[1];
  // Respect the declared first-floor datum and flag inconsistent level series.
  const datum=(name)=>t.match(new RegExp('(?:منسوب\\s+|و)?'+name+'\\s*[:=]?\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*م'));
  const first=datum('الاول'), second=datum('الثاني'), roof=datum('(?:بلاطه\\s+)?السطح'), ground=datum('الارضي');
  if(first && !storey) height=+first[1];
  if((ground&&+ground[1]!==0)||(first&&Math.abs(+first[1]-height)>0.01)||(second&&Math.abs(+second[1]-2*height)>0.01)||(roof&&Math.abs(+roof[1]-levels*height)>0.01))
    unsupported('المناسيب المحددة غير منتظمة. يدعم مخطط الشقق المحلي ارتفاعاً موحّداً يبدأ من منسوب أرضي 0.00 م.');
  return design(width,depth,levels,height,'local_brief',options);
}

export function apartmentFromRevision(text,currentModel) {
  const prior=currentModel?.meta?.acs_apartment;
  if(prior?.schema!=='acs.local-apartment/1') unsupported('أنشئ أولاً عمارة سكنية محلية حتى تتمكن من تعديل مخططها.');
  const t=normalize(text), courtyard=courtyardChoice(t), entrance=entranceDirection(t);
  if(courtyard===undefined && entrance===undefined)
    unsupported('يمكنك تعديل الفناء أو تحديد جهة المدخل الرئيسي. اختر التعديل المطلوب أو اكتب وصفاً جديداً للمبنى.');
  const existing={width:prior.width_m,depth:prior.depth_m,levels:prior.occupied_levels,height:currentModel.floor_height};
  const options={courtyard:courtyard??Boolean(prior.courtyard),entrance:entrance??prior.street_edge};
  let model=buildRequestedApartment(t,existing,options);
  if(model.site.w!==existing.width || model.site.d!==existing.depth || model.levels.length!==existing.levels || model.floor_height!==existing.height)
    unsupported('تعديل المدخل والفناء يحافظ على أبعاد المبنى والأدوار والشقق. اختر هذا التعديل أو أنشئ وصفاً جديداً بالمقاسات والعدد الجديدين.');
  // Parameter revisions can regenerate the authored apartment. If rooms or
  // stairs were edited manually, a fresh layout would discard those changes.
  let baseline=design(existing.width,existing.depth,existing.levels,existing.height,prior.source,
    {courtyard:Boolean(prior.courtyard),entrance:prior.street_edge});
  if(currentModel.meta.acs_context_details){
    baseline=withContextDetails(baseline)[0];
    model=withContextDetails(model)[0];
  }
  const occupied=currentModel.levels.filter(level=>level.kind!=='roof');
  const matches=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  if(!matches(occupied,baseline.levels) || !matches(currentModel.site,baseline.site) ||
    currentModel.wall_t!==baseline.wall_t || currentModel.wall_h!==baseline.wall_h ||
    occupied.some(level=>!matches(currentModel.floors[level.template],baseline.floors[level.template])) ||
    currentModel.levels.some(level=>level.kind==='roof'&&!level.auto))
    unsupported('يتضمن مشروعك تعديلات يدوية على الهندسة. احتفظ بها في المشروع الحالي، أو نزّل نسخته ثم ابدأ وصفاً جديداً للتوزيع المطلوب.');
  model.meta={...currentModel.meta,...model.meta};
  // The caller reapplies the actual roof preference to this newly built shell.
  delete model.meta.acs_roof;
  if(prior.brief) model.meta.acs_apartment.brief=prior.brief;
  model.meta.acs_apartment.last_revision=String(text);
  return model;
}
