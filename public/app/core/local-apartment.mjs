// Authored local residential scheme. Coordinates are metres, x east and z south.
// The apartment wing is mirrored about the common entrance. All floor/room
// instances, apertures, furniture and stairs are part of the exported model.
import { withDefaultStairs } from './stairs.mjs';
import { withContextDetails } from './context-details.mjs';
import { withDefaultRoof } from './roof.mjs';
import { apartmentDoorPairs } from './apartment-door-pairs.mjs';
export { apartmentDoorPairs };

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
  // Round the shared centre once: rounding each room's offset separately left
  // the two leaves of one door up to 1 mm apart, which the access check rejects.
  const center = round((start+end)/2);
  const door = (room, other, side, origin) => ({
    id: room.id+'_to_'+other.id, edge: side, offset: round(center-origin), width, height: 2.18, material,
    acs_door_pair:{id:'door|'+[room.id,other.id].sort().join('|'),peer_room_id:other.id}
  });
  a.doors.push(door(a,b,edge,fromA));
  b.doors.push(door(b,a,opposite[edge],fromB));
}

function windowAt(room,edge,fraction,width,sill=0.76,height=1.78) {
  const span = room.rect[['N','S'].includes(edge) ? 2 : 3];
  const offset = fraction*span;
  room.windows.push({id:room.id+'_window_'+room.windows.length,edge,offset:round(offset),
    width:round(Math.min(width,2*Math.min(offset,span-offset)-0.28)),sill,height});
}

function object(room,kind,name,x,z,w,d,h,rot=0,y=0) {
  (room.objects ||= []).push({id:room.id+'_'+kind+'_'+room.objects.length,
    kind,name,x:round(x),z:round(z),w:round(w),d:round(d),h:round(h),rot,y:round(y),
    // A single instance, stated explicitly with the compiler's repeat defaults
    // so approved 3D does not have to assume them.
    count:1,pitch:1.2,dir:'x'});
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

function floorPlan(width,depth,index,storeyHeight) {
  // The compiler centres walls on room boundaries. Specify the external
  // envelope first, then locate the wall axes one half-thickness inside it.
  const axisX=x=>round(wallThickness/2+x*(width-wallThickness)/20);
  // Side-facing variants can have less front-to-back depth. Keep the physical
  // stair bay at least 4 m long, distributing that difference across the wings.
  // For the original sample, retain the original coordinates byte for byte.
  const clearDepth=depth-wallThickness, needsStairSpace=4.8*clearDepth/25<4;
  const wingScale=(clearDepth-4)/(25-4.8);
  const axisZ=z=>{
    if(!needsStairSpace) return round(wallThickness/2+z*clearDepth/25);
    const inCore=Math.max(0,Math.min(z-7.2,4.8));
    return round(wallThickness/2+(z-inCore)*wingScale+inCore*4/4.8);
  };
  const rect=(x,z,w,d)=>[axisX(x),axisZ(z),round(axisX(x+w)-axisX(x)),round(axisZ(z+d)-axisZ(z))];
  const entranceDepth=index?0:1.35;
  const lobby=rectangle('lobby',index?'بسطة وبهو مشترك':'بهو المدخل','lobby',rect(8,entranceDepth,4,7.2-entranceDepth));
  const stair=rectangle('stair','الدرج المشترك','stairs',rect(8,7.2,2.4,4.8));
  const lift=rectangle('lift','حيّز المصعد المقترح','elevator',rect(10.4,7.2,1.6,4.8));
  stair.core_id='central'; lift.core_id='lift';
  lobby.wall_color='#bfab90'; lobby.floor_color='#b6a286';
  const rooms=[lobby,stair,lift];
  connect(lobby,stair,1.0); connect(lobby,lift,0.90,'metal');
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
    add('foyer','مدخل الشقة','entrance',4.4,5,3.6,2.2);
    add('dining','صالة الطعام','dining',0,7.2,4.4,3.6);
    add('kitchen','مطبخ','kitchen',0,10.8,4.4,4);
    add('hall','ممر النوم','corridor',4.4,7.2,1.8,12.8);
    add('guest_wc','دورة مياه الضيوف','bathroom',6.2,7.2,1.8,2.3);
    add('laundry','غرفة غسيل','laundry',6.2,9.5,1.8,2.5);
    add('store','مخزن','storage',6.2,12,3.8,2);
    add('bath','حمام مشترك','bathroom',6.2,14,3.8,3);
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
  return {rooms};
}

// The courtyard is absent from every room footprint. Floor plates and the
// canonical roof use those footprints, so they cannot fill this reservation.
// A common enclosed gallery goes all the way around the opening; the stair
// and lift are reached through that gallery, without crossing either unit.
function courtyardPlan(width,depth,index,storeyHeight,courtyard) {
  const half=wallThickness/2, left=half, top=half, bottom=round(depth-half);
  const voidW=round(courtyard.width+wallThickness), voidD=round(courtyard.depth+wallThickness);
  const vx=round((width-voidW)/2), vz=round((depth-voidD)/2), farZ=round(vz+voidD);
  const gallery=1.5, hallWidth=1.6, coreDepth=4.2, stairWidth=2.4;
  const galleryX=round(vx-gallery), galleryZ=round(vz-gallery), galleryBack=round(farZ+gallery);
  const hallX=round(galleryX-hallWidth), coreBack=round(galleryBack+coreDepth);
  const foyerEnd=round(galleryZ-2.2), foyerStart=round(foyerEnd-2.2);
  const masterDepth=round(bottom-coreBack), rearBathSplit=round((coreBack+bottom)/2);
  if(hallX-left<3.5 || voidW-stairWidth<1.3 || foyerStart-top<2.8 || masterDepth<3.2)
    unsupported('لا تتسع الأبعاد المحددة للفناء وممره المشترك وغرف الشقتين. زِد عرض المبنى أو عمقه، أو صغّر الفناء.');
  const bounds=(x0,z0,x1,z1)=>[round(x0),round(z0),round(x1-x0),round(z1-z0)];
  const make=(id,name,role,x0,z0,x1,z1,unit)=>rectangle(id,name,role,bounds(x0,z0,x1,z1),unit);
  const porchEnd=round(top+1.35);
  const lobby=make('lobby',index?'بهو مشترك':'بهو المدخل','lobby',vx,index?top:porchEnd,vx+voidW,galleryZ);
  const north=make('courtyard_gallery_north','رواق الفناء الأمامي','corridor',galleryX,galleryZ,width-galleryX,vz);
  const west=make('courtyard_gallery_west','رواق الفناء الغربي','corridor',galleryX,vz,vx,farZ);
  const east=make('courtyard_gallery_east','رواق الفناء الشرقي','corridor',vx+voidW,vz,width-galleryX,farZ);
  const south=make('courtyard_gallery_south','رواق الفناء الخلفي','corridor',galleryX,farZ,width-galleryX,galleryBack);
  const stair=make('stair','الدرج المشترك','stairs',vx,galleryBack,vx+stairWidth,coreBack);
  const lift=make('lift','حيّز المصعد المقترح','elevator',vx+stairWidth,galleryBack,vx+voidW,coreBack);
  stair.core_id='central'; lift.core_id='lift';
  const rooms=[lobby,north,west,east,south,stair,lift];
  connect(lobby,north,1.65); connect(north,west,1.05); connect(north,east,1.05);
  connect(west,south,1.05); connect(east,south,1.05);
  connect(south,stair,1.0); connect(south,lift,0.90,'metal');
  for(const [room,edge] of [[north,'S'],[west,'E'],[east,'W'],[south,'N']]) {
    if(index===0 && room===north)
      room.doors.push({id:'court_ground_door',edge,offset:round(room.rect[2]/2),width:1.05,height:2.18,material:'glass'});
    else windowAt(room,edge,0.5,Math.min(courtyard.width,courtyard.depth)-0.5,0.85,Math.min(1.8,storeyHeight-1.05));
  }
  if(index===0) {
    const porch=make('entrance_porch','رواق المدخل','porch',vx,top,vx+voidW,porchEnd);
    porch.walls=[]; porch.floor_color='#9c8265'; rooms.push(porch);
    connect(lobby,porch,1.90,'glass');
    const [,,pw,pd]=porch.rect, canopyHeight=Math.min(2.67,storeyHeight-0.32);
    object(porch,'box','مظلة المدخل',pw/2,pd/2,pw-0.06,pd-0.04,0.15,0,canopyHeight);
    porch.objects.at(-1).color='#795c42';
    for(const px of [0.20,pw-0.20]) {
      object(porch,'column','دعامة الرواق',px,0.22,0.20,0.24,canopyHeight);
      porch.objects.at(-1).color='#b6a186';
    }
  } else windowAt(lobby,'N',0.5,Math.min(3.0,voidW-0.4),0.28,2.15);
  const outerRun=coreBack-foyerEnd;
  const diningEnd=round(foyerEnd+outerRun*0.22), kitchenEnd=round(foyerEnd+outerRun*0.46);
  const bed1End=round(foyerEnd+outerRun*0.72), branchStart=round(coreBack-1.25);
  const utilitySplit=round((galleryBack+branchStart)/2);
  for(const unit of ['west','east']) {
    const r={}, side=unit==='west'?'W':'E';
    const add=(id,name,role,x0,z0,x1,z1)=>{
      const room=make(unit+'_'+id,name,role,unit==='west'?x0:width-x1,z0,unit==='west'?x1:width-x0,z1,unit);
      r[id]=room; rooms.push(room); return room;
    };
    const balconyEnd=index?round(top+1.6):top;
    if(index) {
      const balcony=add('balcony','شرفة غائرة','balcony',left,top,hallX,balconyEnd);
      balcony.walls=[]; balcony.floor_color='#aa8460';
      const [,,bw,bd]=balcony.rect;
      object(balcony,'railing','حاجز الشرفة الأمامي',bw/2,0.09,bw-0.12,0.08,1.10);
      object(balcony,'railing','حاجز الشرفة الجانبي',unit==='west'?0.09:bw-0.09,bd/2,bd-0.12,0.08,1.10,90);
    }
    add('living','صالة عائلية','living',left,balconyEnd,hallX,foyerEnd);
    add('majlis','مجلس الضيوف','majlis',hallX,top,vx,foyerStart);
    add('foyer','مدخل الشقة','entrance',hallX,foyerStart,vx,foyerEnd);
    add('hall','ممر النوم','corridor',hallX,foyerEnd,galleryX,coreBack);
    add('guest_wc','دورة مياه الضيوف','bathroom',galleryX,foyerEnd,vx,galleryZ);
    add('dining','صالة الطعام','dining',left,foyerEnd,hallX,diningEnd);
    add('kitchen','مطبخ','kitchen',left,diningEnd,hallX,kitchenEnd);
    add('bed1','غرفة نوم ١','bedroom',left,kitchenEnd,hallX,bed1End);
    add('bed2','غرفة نوم ٢','bedroom',left,bed1End,hallX,coreBack);
    add('laundry','غرفة غسيل','laundry',galleryX,galleryBack,vx,utilitySplit);
    add('store','مخزن','storage',galleryX,utilitySplit,vx,branchStart);
    add('rear_hall','بهو الحمام العائلي','corridor',galleryX,branchStart,vx,coreBack);
    add('bath','حمام مشترك','bathroom',galleryX,coreBack,width/2,rearBathSplit);
    add('ensuite','حمام الجناح','bathroom',galleryX,rearBathSplit,width/2,bottom);
    add('master','غرفة النوم الرئيسية','bedroom',left,coreBack,galleryX,bottom);
    connect(lobby,r.foyer,1.05); connect(r.foyer,r.majlis); connect(r.foyer,r.guest_wc,0.8);
    connect(r.foyer,r.living,1.15); connect(r.foyer,r.hall);
    connect(r.living,r.dining,1.65); connect(r.dining,r.kitchen,1.08);
    for(const id of ['kitchen','bed1','bed2','laundry','store','rear_hall','master']) connect(r.hall,r[id]);
    connect(r.rear_hall,r.bath,0.85); connect(r.master,r.ensuite,0.85);
    if(index) connect(r.living,r.balcony,2.45,'glass');
    else windowAt(r.living,'N',0.5,3.05,0.52,2.04);
    windowAt(r.majlis,'N',0.5,2.53,0.61,1.96);
    for(const id of ['living','dining','kitchen','bed1','bed2','master'])
      windowAt(r[id],side,0.5,id==='living'?3.15:2.1,id==='kitchen'?1.08:0.78,id==='kitchen'?1.28:1.77);
    windowAt(r.master,'S',0.53,3.12); windowAt(r.ensuite,'S',0.5,1.0,1.2,1.0);
    if(!index && unit==='west') furnish(r);
  }
  return {rooms,courtyards:[{id:'central_courtyard',name:'فناء مفتوح للسماء',rect:[vx,vz,voidW,voidD],
    clear_rect:[round(vx+half),round(vz+half),courtyard.width,courtyard.depth],open_to_sky:true}]};
}

const cardinalEdges=['N','E','S','W'];
function orientedPoint(x,z,turns,width,depth) {
  return [[x,z],[depth-z,x],[width-x,depth-z],[z,width-x]][turns].map(round);
}
function orientedRect([x,z,w,d],turns,width,depth) {
  const p=orientedPoint(x,z,turns,width,depth), q=orientedPoint(x+w,z+d,turns,width,depth);
  return [Math.min(p[0],q[0]),Math.min(p[1],q[1]),round(Math.abs(q[0]-p[0])),round(Math.abs(q[1]-p[1]))];
}
// Every room declares the ceiling light the approval gate requires; the
// fixture sits at the room centre and is a conceptual default, not a design.
function withCeilingLights(floor) {
  for(const room of floor.rooms)
    (room.points ||= []).push({id:'ceiling_light',type:'light',x:round(room.rect[2]/2),z:round(room.rect[3]/2)});
  return floor;
}

// Projects saved before generated lights, the 'entrance' role and exact
// paired-door centres differ from today's baseline only by those conventions.
function withLegacyConventions(current,baseline) {
  const copy=structuredClone(current);
  for(const [key,floor] of Object.entries(copy.floors||{})) {
    const reference=new Map((baseline.floors?.[key]?.rooms||[]).map(room=>[room.id,room]));
    for(const room of floor.rooms||[]) {
      const ref=reference.get(room.id);
      if(!ref) continue;
      if(room.role==='entry'&&ref.role==='entrance') room.role='entrance';
      const light=(ref.points||[]).find(point=>point.id==='ceiling_light');
      if(light&&!(room.points||[]).some(point=>point.type==='light')) room.points=[...(room.points||[]),light];
      for(const door of room.doors||[]) {
        const twin=(ref.doors||[]).find(item=>item.id===door.id);
        if(twin&&Math.abs(twin.offset-door.offset)<=0.0015) door.offset=twin.offset;
      }
      for(const obj of room.objects||[]) {
        const twin=(ref.objects||[]).find(item=>item.id===obj.id);
        if(twin&&twin.count===1&&!('count' in obj)&&!('pitch' in obj)&&!('dir' in obj))
          Object.assign(obj,{count:twin.count,pitch:twin.pitch,dir:twin.dir});
      }
    }
  }
  return copy;
}

function orientFloor(floor,turns,width,depth) {
  if(!turns) return floor;
  const edge=e=>cardinalEdges[(cardinalEdges.indexOf(e)+turns)%4];
  for(const room of floor.rooms) {
    const previous=room.rect, next=orientedRect(previous,turns,width,depth);
    for(const aperture of [...room.doors,...room.windows]) {
      const [x,z,w,d]=previous, side=aperture.edge;
      const point=['N','S'].includes(side)?[x+aperture.offset,z+(side==='S'?d:0)]:[x+(side==='E'?w:0),z+aperture.offset];
      const rotated=orientedPoint(...point,turns,width,depth);
      aperture.edge=edge(side);
      aperture.offset=round(['N','S'].includes(aperture.edge)?rotated[0]-next[0]:rotated[1]-next[1]);
    }
    for(const obj of room.objects||[]) {
      const point=orientedPoint(previous[0]+obj.x,previous[1]+obj.z,turns,width,depth);
      obj.x=round(point[0]-next[0]); obj.z=round(point[1]-next[1]);
      obj.rot=((obj.rot||0)+turns*90)%360;
    }
    if(Array.isArray(room.walls)) room.walls=room.walls.map(edge);
    room.rect=next;
  }
  for(const court of floor.courtyards||[]) {
    court.rect=orientedRect(court.rect,turns,width,depth);
    court.clear_rect=orientedRect(court.clear_rect,turns,width,depth);
  }
  return floor;
}

const assumptions = [
  'مخطط محلي مفاهيمي بشقتين وثلاث غرف نوم لكل شقة. أبعاد الغرف الفعلية مشتقة من المخطط وقد تختلف عن الأهداف النصية.',
  'الدرجات والبسطات وفتحات البلاطات ممثلة بين الأدوار السكنية. المصعد حيّز مقترح، والوصول إلى سطح الخدمات يحتاج إلى تصميم.',
  'الأثاث والتشطيبات اقتراحات للمقياس. مجاري الخدمات والمواقف والارتدادات والتحقق الإنشائي والتنظيمي تحتاج إلى مراجعة مستقلة.'
];

// Each stated value is checked against the supported range; undefined values are left for a question.
function supportedEnvelope(width,depth,levels,height) {
  const known=value=>value!==undefined;
  if((known(width)&&(!Number.isFinite(width)||width<18||width>32))||(known(depth)&&(!Number.isFinite(depth)||depth<22||depth>36)))
    unsupported('أدخل أبعاد المبنى الخارجية. يدعم هذا التوزيع عرضاً بين 18 و32 م وعمقاً بين 22 و36 م.');
  if(known(levels)&&(!Number.isInteger(levels)||levels<1||levels>6))
    unsupported('يدعم مخطط الشقق المحلي من دور سكني واحد إلى ستة أدوار شاملة الأرضي.');
  if(known(height)&&(!Number.isFinite(height)||height<2.8||height>3.6))
    unsupported('يدعم الدرج المحلي ارتفاع دور موحّداً بين 2.8 و3.6 م.');
}

function design(width,depth,levels,height,source,{entrance='N',courtyard=null}={}) {
  const turns=cardinalEdges.indexOf(entrance), side=turns%2===1;
  const planWidth=side?depth:width, planDepth=side?width:depth;
  if(!Number.isFinite(width)||!Number.isFinite(depth))
    unsupported('أدخل أبعاد المبنى الخارجية. يدعم هذا التوزيع عرضاً بين 18 و32 م وعمقاً بين 22 و36 م.');
  supportedEnvelope(width,depth,levels,height);
  const title='عمارة سكنية '+width+' × '+depth+' م';
  const model={
    meta:{name:title,type:'residential',north:'-Z',acs_apartment:{schema:'acs.local-apartment/1',source,width_m:width,depth_m:depth,
      occupied_levels:levels,units_per_floor:2,units_total:2*levels,bedrooms_per_unit:3,street_edge:entrance,
      wall_reference:'room_wall_centrelines',outer_face_offset_m:wallThickness/2,assumptions:[...assumptions]}},
    site:{w:width,d:depth},floor_height:height,wall_h:round(height-0.18),wall_t:wallThickness,levels:[],floors:{}
  };
  const planCourtyard=courtyard?{width:side?courtyard.depth:courtyard.width,depth:side?courtyard.width:courtyard.depth}:null;
  if(planCourtyard && (planCourtyard.width<3.6||planCourtyard.width>5||planCourtyard.depth<4||planCourtyard.depth>6))
    unsupported('يدعم هذا التوزيع فناءً صافياً بين 3.6 و5 م موازياً لواجهة المدخل، وبين 4 و6 م عمودياً عليها.');
  if(turns) {
    const labels=[{west:'الشقة الغربية',east:'الشقة الشرقية'},{west:'الشقة الشمالية',east:'الشقة الجنوبية'},
      {west:'الشقة الشرقية',east:'الشقة الغربية'},{west:'الشقة الجنوبية',east:'الشقة الشمالية'}];
    model.meta.acs_apartment.unit_labels=labels[turns];
    model.meta.acs_apartment.unit_edges={west:cardinalEdges[(3+turns)%4],east:cardinalEdges[(1+turns)%4]};
    model.meta.acs_apartment.assumptions.push('اتجاه المدخل '+({E:'شرقي',S:'جنوبي',W:'غربي'}[entrance])+'. أبعاد المخطط تقاس شرقاً وغرباً ثم شمالاً وجنوباً، ويعاد توزيع الغرف والفتحات والدرج باتجاه المدخل ضمن هذا المحيط.');
  }
  if(planCourtyard) {
    const cw=planCourtyard.width, cd=planCourtyard.depth;
    const clear=[round((planWidth-cw)/2),round((planDepth-cd)/2),cw,cd];
    const reserve=[round(clear[0]-wallThickness/2),round(clear[1]-wallThickness/2),round(cw+wallThickness),round(cd+wallThickness)];
    model.meta.acs_apartment.courtyard={schema:'acs.courtyard/1',open_to_sky:true,occupied_floor:false,
      rect_m:orientedRect(clear,turns,planWidth,planDepth),footprint_void_m:orientedRect(reserve,turns,planWidth,planDepth),
      circulation:'enclosed_gallery_ring',size_source:courtyard.size_source??'not_recorded'};
    const sizeNote={default_assumption:' افتراضاً لأنك لم تحدد أبعاده',partly_default_assumption:'، وأحد البعدين افتراضي لأنك لم تحدده'}[courtyard.size_source]??'';
    model.meta.acs_apartment.assumptions.push('فناء مركزي مفتوح للسماء بأبعاد صافية '+courtyard.width+' × '+courtyard.depth+' م'+sizeNote+'، تحيط به أروقة مشتركة تصل المدخل بالدرج والمصعد. لا توجد غرفة أو بلاطة أو سطح فوق الفناء، وحول فتحته على السطح حاجز مثل حاجز الواجهة.');
  }
  for(let i=0;i<levels;i++) {
    const template='level_'+i;
    model.levels.push({index:i,name:levelsAr[i],elevation:round(i*height),template});
    const floor=planCourtyard?courtyardPlan(planWidth,planDepth,i,height,planCourtyard):floorPlan(planWidth,planDepth,i,height);
    model.floors[template]=withCeilingLights(orientFloor(floor,turns,planWidth,planDepth));
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
  // «واجهتها/واجهته» keep the suffixed ت of واجهة; read them as واجهه + pronoun.
  return String(text||'').toLowerCase().replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)%16))
    .replace(/[\u064b-\u065f\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/٫/g,'.')
    .replace(/واجهت(?=ها|ه(?![ء-ي]))/g,'واجهه');
}
const numberWord={'واحد':1,'واحده':1,'اثنان':2,'اثنين':2,'ثلاث':3,'ثلاثه':3,'اربع':4,'اربعه':4,'خمس':5,'خمسه':5,'ست':6,'سته':6,'سبع':7,'سبعه':7,'ثمانيه':8,'ثماني':8,'ثمان':8,'تسعه':9,'تسع':9,'عشره':10,'عشر':10};
// Number words that can only be read reliably as digits in a dimension.
const dimensionWord='(?:(?:احد|احدى|اثنا|اثني|اثنتا|ثلاث|اربع|خمس|ست|سبع|ثمان|تسع)\\s*عشر|عشر(?:ه|ين|ون)?|(?:ثلاث|اربع|خمس|ست)(?:ين|ون)|ثلاثه|اربعه|خمسه|سته|سبعه|ثمانيه|تسعه)(?![ء-ي])';
const count='(\\d+|'+Object.keys(numberWord).sort((a,b)=>b.length-a.length).join('|')+')';
const asCount = value=>Number.isNaN(Number(value))?numberWord[value]:Number(value);
const decimal='(\\d+(?:\\.\\d+)?)';
function singleRequestedValue(values,label) {
  const unique=[...new Set(values.filter(value=>value!==undefined))];
  if(unique.length>1) unsupported('وردت قيم متعارضة تحدد '+label+' ('+unique.join(' و')+'). اختر رقماً واحداً لهذا الشرط ثم أعد التوليد.');
  return unique[0];
}

// A street's width («شارع عرضه ١٥ م») is neither the building's width nor part of its side.
const withoutStreetWidth=text=>text.replace(/(شوارع|شارعين|شارع)\s+(?:(?:عرضه|عرضها|بعرض|عرض)\s*[:=]?\s*)?\d+(?:\.\d+)?\s*(?:مترا?|امتار|م(?![ء-ي]))?/g,'$1');

function dimensions(text) {
  // Only the building introduction supplies exterior dimensions. Room goals
  // and numbered programme headings in subsequent paragraphs are unrelated.
  text=text.replace(/(?:من\s+دون\s+|بدون\s+|بلا\s*|لا\s+(?:يوجد|توجد|اريد)\s+)(?:اي\s*)?(?:ال)?(?:فناء|حوش|باحه|courtyard|atrium)/g,'');
  text=withoutStreetWidth(text);
  const owner='(?:المبنى|العماره|البناء|البنايه)';
  // «والمبنى ٢٠×٢٥» and «عمارة سكنية أبعادها ٢٠×٢٥» also name the building's own size.
  const sizeOfBuilding=new RegExp('(?:ابعاد|مقاس|مسطح|بصمه|واجهه|عرض|طول|عمق)\\s+'+owner+
    '|(?:^|[\\s،.,])و?(?:ال)?(?:مبنى|عماره|بنايه)(?:\\s+سكني(?:ه)?)?\\s+(?:(?:ابعادها|ابعاده|مقاسها|مقاسه|بمقاس|بابعاد)\\s*)?(?=\\d)');
  // «قطعة ٢٠×٣٠» and deed («صك») dimensions describe the plot, not the building.
  const lotTerms=/(?:قطعه\s+(?:ال)?ارض|(?:^|[\s،.,])(?:ال)?قطعه(?:\s+(?:ال)?ارض)?(?![ء-ي])|(?:^|[\s،.,])(?:ال)?صك(?:ها|ه)?(?![ء-ي])|(?:على|ابعاد|مساحه)\s+(?:ال)?ارض|(?:^|[\s،.,])(?:ال)?ارض\s+(?=\d|بمقاس|بابعاد|مساحتها|مقاسها))/;
  const opening=s=>s.split(/\n\s*\n|(?:مجلس|غرفه نوم|صاله عائليه|مطبخ|فناء|حوش|باحه|courtyard|atrium)/,1)[0].slice(0,650);
  const intro=opening(text), lot=lotTerms.exec(intro), building=sizeOfBuilding.exec(text);
  // The plot is context for the building, never its envelope.
  const plotPair=lot&&intro.slice(lot.index+lot[0].length).slice(0,30).match(new RegExp('^\\s*'+decimal+'\\s*(?:مترا?|امتار|م)?\\s*(?:[×x*]|في|بـ?)\\s*'+decimal));
  const plot=plotPair?{w:+plotPair[1],d:+plotPair[2]}:null;
  let scope=lot?intro.slice(0,lot.index):intro;
  // Later named building dimensions are admissible even if a separate lot or
  // room programme came first. Stop again at any following lot description.
  if(building&&building.index>=scope.length) scope+='، '+opening(text.slice(building.index)).split(lotTerms,1)[0];
  const metres='(?:مترا?|امتار|م)?';
  if(/\d\s*(?:قدم|اقدام|يارد|سم|سنتيمتر|مم|ملم|feet|foot|ft|cm|mm)/.test(scope))
    unsupported('أدخل أبعاد المبنى بالمتر لاستخدام التوزيع المحلي.');
  // «22,5» would otherwise be read as 22. Ask instead of truncating a dimension.
  if(/\d,\d{1,2}(?!\d)/.test(scope))
    unsupported('في الأبعاد رقم بفاصلة قد يكون كسراً عشرياً أو رقمين. اكتب الكسر بنقطة، مثل 22.5 م أو ٢٢٫٥ م، وافصل العرض عن العمق بـ ×.');
  const pair=scope.match(new RegExp(decimal+'\\s*'+metres+'\\s*(?:[×x*]|في|بـ?)\\s*'+decimal));
  // Dimensions written in words («مقاسها عشرين في خمسة وعشرين») must not fall back to defaults.
  if(!pair && !new RegExp('(?:عرض|واجهه|عمق|طول)(?:ها|ه)?(?:\\s+'+owner+')?\\s*[:=]?\\s*\\d').test(scope) &&
    (new RegExp(dimensionWord+'\\s*(?:مترا?\\s*)?(?:في|[×x*])\\s*'+dimensionWord).test(scope) ||
     new RegExp('(?:ابعاد|مقاس|مسطح|بصمه|عرض|عمق|طول|واجهه)(?:ها|ه)?(?:\\s+'+owner+')?\\s+'+dimensionWord).test(scope)))
    unsupported('اكتب عرض المبنى وعمقه بالأرقام وبالمتر، مثل عرض المبنى ٢٤ م وعمقه ٢٨ م.');
  function namedDimension(label,postfix,explicit){
    const before=new RegExp(label+'(?:ها|ه)?(?:\\s+'+owner+')?\\s*[:=]?\\s*'+decimal);
    const after=new RegExp(decimal+'\\s*'+metres+'\\s*(?:على\\s+)?(?:'+postfix+')');
    const values=[...scope.matchAll(new RegExp(before,'g')),...scope.matchAll(new RegExp(after,'g'))].map(m=>Number(m[1]));
    if(new Set(values).size>1) unsupported('وردت أبعاد متعارضة للمبنى. حدّد عرضاً وعمقاً واحدين بالمتر.');
    if(!values.length&&explicit.test(scope))
      unsupported('اكتب عرض المبنى وعمقه بالأرقام وبالمتر، مثل عرض المبنى ٢٤ م وعمقه ٢٨ م.');
    return values[0];
  }
  const w=namedDimension('(?:عرض|واجهه)','عرضا?|واجهه',/عرض\s+(?:المبنى|العماره)|(?:عرضه|عرضها)\s/);
  const d=namedDimension('(?:عمق|طول)','عمقا?|طولا?',/(?:طول|عمق)\s+(?:المبنى|العماره)|(?:طوله|طولها|عمقه|عمقها)\s/);
  if(pair&&((w!==undefined&&w!==+pair[1])||(d!==undefined&&d!==+pair[2])))
    unsupported('وردت أبعاد متعارضة للمبنى. حدّد عرضاً وعمقاً واحدين بالمتر.');
  // Repeated, explicitly named building dimensions remain binding after the
  // introduction, while room and courtyard sizes cannot become the envelope.
  const buildingQualifier='\\s+'+owner+'(?:\\s+الخارجيه?)?\\s*[:=]?\\s*';
  const namedValues=axis=>[...text.matchAll(new RegExp(axis+buildingQualifier+decimal,'g'))].map(m=>Number(m[1]));
  const namedSizes=[...text.matchAll(new RegExp('(?:ابعاد|مقاس|بصمه)'+buildingQualifier+decimal+'\\s*'+metres+'\\s*(?:[×x*]|في)\\s*'+decimal,'g'))];
  return {
    width:singleRequestedValue([w,pair?+pair[1]:undefined,...namedValues('(?:عرض|واجهه)'),...namedSizes.map(m=>+m[1])],'عرض المبنى'),
    depth:singleRequestedValue([d,pair?+pair[2]:undefined,...namedValues('(?:عمق|طول)'),...namedSizes.map(m=>+m[2])],'عمق المبنى'),
    plot,plotMentioned:Boolean(lot)
  };
}

// «أرضي وأول وثاني وثالث» lists every occupied floor: count them instead of assuming three.
const floorOrdinals=['اول','ثان','ثالث','رابع','خامس'];
function listedFloorCount(text) {
  const item='(?:(?:ال)?(?:دور|طابق)\\s+)?(?:ال)?';
  const list=text.match(new RegExp('(?:^|[\\s،.,:])'+item+'ارضي((?:\\s*(?:[،,+]\\s*)?و?\\s*'+item+'(?:اول|ثان(?:ي)?|ثالث|رابع|خامس)(?![ء-ي]))+)'));
  if(!list) return undefined;
  const named=[...list[1].matchAll(/(اول|ثان|ثالث|رابع|خامس)/g)].map(m=>m[1]);
  return named.every((name,i)=>name===floorOrdinals[i]) ? 1+named.length : undefined;
}

function occupiedFloorCount(text) {
  const counts=[],intro=text.split(/\n\s*\n/)[0];
  const numberPhrase=new RegExp(count+'\\s*(?:ادوار|طوابق|floors|storeys)|(?:دورين|دوران|طابقين|طابقان)(?![ء-ي])|(?:دور|طابق)\\s+واحد|عدد\\s+(?:ال)?(?:ادوار|طوابق)\\s*[:=]?\\s*'+count+'(?![ء-ي\\d])','g');
  for(const match of text.matchAll(numberPhrase)) {
    const before=text.slice(0,match.index),after=text.slice(match.index+match[0].length);
    // "في الدورين الأول والثاني" describes access, not an occupied count.
    if(!(match[1]??match[2])&&(match.index>=intro.length || /(?:ال|(?:كل|مخطط|توزيع|عزل|اختيار)\s+)$/.test(before))) continue;
    const stated=match[1]??match[2];
    const countValue=stated?asCount(stated):match[0].endsWith('واحد')?1:2;
    // «أرضي + دورين», «ثلاثة أدوار غير/بدون/عدا الأرضي» add the ground floor to the count.
    const addsGround=/(?:^|[\s،.,])(?:ال)?ارضي\s*[,،]?\s*(?:و\s*(?:(?:فوقه|فوقها)\s*)?|زائد\s*|\+\s*|بالاضافه\s+الى\s*)$/.test(before) ||
      /^(?:\s+(?:علويه?|اضافيه?))?\s+فوق(?:ه|ها|(?:\s+(?:(?:الدور|الطابق)\s+)?الارضي))/.test(after) ||
      /^\s+(?:غير|بدون|دون|عدا|ماعدا|ما\s+عدا|بخلاف|من\s+غير|من\s+دون|علاوه\s+على|بالاضافه\s+الى|زائد|\+)\s*(?:(?:ال)?(?:دور|طابق)\s+)?(?:ال)?ارضي/.test(after) ||
      // «ثلاث أدوار والأرضي»: the ground floor is named in addition to the count.
      /^\s+و\s*(?:(?:ال)?(?:دور|طابق)\s+)?الارضي(?![ء-ي])/.test(after) ||
      // «بالإضافة للأرضي», «علاوة على الدور الأرضي».
      /^\s+(?:بالاضافه|اضافه|علاوه)\s+(?:(?:الى|على)\s+(?:ال)?|لل)(?:(?:دور|طابق)\s+(?:ال)?)?ارضي(?![ء-ي])/.test(after);
    const inclusive=/^\s+(?:تشمل|تتضمن|شامله?|بما\s+فيها?)(?:\s+(?:الدور|الطابق))?\s+الارضي/.test(after);
    if(addsGround&&inclusive) unsupported('ذكرت الأرضي منفصلاً ثم شملته في العدد. حدّد إجمالي الأدوار شاملاً الأرضي، أو اذكر الأدوار التي تعلوه.');
    counts.push({value:countValue+(addsGround?1:0),ground:addsGround?'added':inclusive?'stated_inclusive':'read_inclusive'});
  }
  const value=singleRequestedValue(counts.map(c=>c.value),'إجمالي الأدوار شاملة الأرضي');
  if(value===undefined) return undefined;
  const ground=['added','stated_inclusive','read_inclusive'].find(rule=>counts.some(c=>c.ground===rule));
  return {value,ground};
}

const directions={شمال:'N',شرق:'E',جنوب:'S',غرب:'W'};
const directionWord='(شمال|شرق|جنوب|غرب)(?:ي(?:ه)?|ا)?';
// «غيّر المدخل وخله من الشرق»: an imperative with the entrance as its pronoun may sit before the side.
const orientationPrefix='(?:(?:ال|لل|ب)?(?:مبنى|عماره|بنايه|شارع|رئيسي|واحد|مدخل|واجهه|جهه|ناحيه|طرف|منتصف|وسط)|يكون|تكون|من|في|على|الي|الى|نحو|باتجاه|بالاتجاه|علي|و?(?:خلي|خل|اجعل|حط)(?:ه|ها))\\s*';
function entranceDirection(text) {
  // A side offset is a different plan, not a cardinal rotation. Do not silently
  // return a centred entrance for a request to move it along the same facade.
  if(/(?:مدخل(?:\s+(?:المبنى|العماره|الرئيسي))?|المدخل)[^،.!؟\n]{0,80}(?:يمين|يسار|(?:في|عند)\s+(?:ال)?(?:زاويه|ركن))/.test(text))
    unsupported('يدعم هذا التوزيع مدخلاً في منتصف الواجهة المختارة. نقل المدخل إلى يمين الواجهة أو يسارها يحتاج إلى توزيع آخر.');
  const edges=new Set();
  const target=withoutStreetWidth(text).replace(new RegExp('من\\s+(?:جهه\\s+)?(?:ال)?'+directionWord+'\\s+(?:الي|الى|لـ?)\\s*','g'),'الى ');
  const pattern=new RegExp('(?:مدخل|دخول|واجهه|شارع)(?:ها|ه)?\\s*(?:'+orientationPrefix+'){0,10}(?:ال|لل|ب)?'+directionWord,'g');
  for(const match of target.matchAll(pattern)) {
    edges.add(directions[match[1]]);
    const alternative=target.slice(match.index+match[0].length).match(new RegExp('^\\s*(?:او|و|/)\\s*(?:ال)?'+directionWord));
    if(alternative) edges.add(directions[alternative[1]]);
  }
  for(const match of target.matchAll(/\b(north|east|south|west)[- ]facing\s+(?:street|facade|entrance)\b/g))
    edges.add({north:'N',east:'E',south:'S',west:'W'}[match[1]]);
  if(edges.size>1) unsupported('ذكرت أكثر من جهة للمدخل أو واجهة الشارع. حدّد جهة واحدة للمدخل الرئيسي.');
  if(edges.size && /(?:شمال|جنوب)(?:ي(?:ه)?)?\s*(?:ال)?(?:شرق|غرب)/.test(target))
    unsupported('يدعم هذا المخطط مدخلاً على إحدى الواجهات الأربع. اختر الشمال أو الشرق أو الجنوب أو الغرب.');
  return [...edges][0];
}

function courtyardChoice(text,previous=null) {
  const noun='(?:فناء|افنيه|حوش|باحه|courtyard|atrium)';
  if(!new RegExp(noun).test(text)) return undefined;
  const removed=new RegExp('(?:لا\\s+(?:يوجد|توجد|اريد|يتضمن|يشمل)(?:\\s+(?:بها|فيها|به|فيه))?\\s+|بدون\\s+|بلا\\s*|من دون\\s+|احذف\\s+|ازل\\s+|الغ\\s+|شيل\\s+|ما ابي\\s+|(?:no|without)\\s+)(?:اي\\s*)?(?:ال)?'+noun,'g');
  if(removed.test(text)) {
    removed.lastIndex=0;
    if(new RegExp(noun).test(text.replace(removed,'')))
      unsupported('ورد طلب بإزالة الفناء والإبقاء عليه في الوصف نفسه. اختر إضافة الفناء أو حذفه.');
    return false;
  }
  const start=text.search(new RegExp(noun));
  const scope=text.slice(start,start+240).split(/\n/)[0];
  const positive=scope.replace(/(?:غير\s+(?:مسقوف|مغط[ىي])|(?:بلا|بدون|دون)\s+سقف|لا\s+(?:تغلقه|تغطه|تضع)[^،.!\n]{0,50})/g,'');
  if(/مسقوف|مغط[ىي]|جانبي|امامي|خلفي|سقف\s+زجاجي|covered\s+(?:court|atrium)/.test(positive))
    unsupported('يدعم هذا التوزيع فناءً مركزياً مفتوحاً للسماء. الفناء الجانبي أو المغطى يحتاج إلى توزيع آخر.');
  if(/(?:حافظ|احتفظ|نفس|دون تغيير|بدون تغيير)[^،.!\n]{0,16}(?:مساحات|ابعاد|مساحه)\s+(?:(?:جميع|كل)\s+)?(?:الغرف|غرف|الشقتين|الشقق)/.test(text))
    unsupported('إضافة الفناء تعيد توزيع الغرف داخل محيط المبنى. لا يمكن تثبيت أبعاد جميع الغرف مع هذا التعديل.');
  const pair=scope.match(new RegExp(decimal+'\\s*(?:مترا?|م)?\\s*(?:[×x*]|في)\\s*'+decimal));
  const namedWidth=scope.match(new RegExp('عرض(?:\\s+(?:ال)?فناء|ه)?\\s*[:=]?\\s*'+decimal));
  const namedDepth=scope.match(new RegExp('(?:عمق|طول)(?:\\s+(?:ال)?فناء|ه)?\\s*[:=]?\\s*'+decimal));
  if((pair&&namedWidth&&+pair[1]!==+namedWidth[1])||(pair&&namedDepth&&+pair[2]!==+namedDepth[1]))
    unsupported('وردت أبعاد متعارضة للفناء. حدّد عرضاً وعمقاً صافيين بالمتر.');
  const sizeClaim=new RegExp('(?:ب?(?:ابعاد|مقاس)|(?:ب?(?:عرض|عمق|طول))(?:ه|\\s+الفناء)?|مساح(?:ته|ه))\\s+(?:صافيه\\s+)?(?:\\d|'+Object.keys(numberWord).join('|')+')');
  if(sizeClaim.test(scope) && !pair && !namedWidth && !namedDepth)
    unsupported('اكتب أبعاد الفناء الصافية بالأرقام وبالمتر، مثل فناء ٤ × ٥ م.');
  if(/\d\s*(?:قدم|اقدام|سم|سنتيمتر|مم|ملم|ft|cm|mm)/.test(scope))
    unsupported('أدخل أبعاد الفناء الصافية بالمتر.');
  const old=previous?.rect_m;
  // Record whether each clear dimension is the customer's or the 4 × 5 m default;
  // a dimension carried from the current design keeps that design's provenance.
  const carried={client_stated:'client',default_assumption:'default'}[previous?.size_source]??'unknown';
  const origin=(named,prior)=>named||pair?'client':prior!==undefined?carried:'default';
  const origins=[origin(namedWidth,old?.[2]),origin(namedDepth,old?.[3])];
  const size_source=origins.includes('unknown')?'not_recorded':origins.every(o=>o==='client')?'client_stated':
    origins.every(o=>o==='default')?'default_assumption':'partly_default_assumption';
  return {width:Number(namedWidth?.[1]??pair?.[1]??old?.[2]??4),depth:Number(namedDepth?.[1]??pair?.[2]??old?.[3]??5),size_source,
    sized:Boolean(namedWidth||namedDepth||pair)};
}

// Values the visitor typed in the form: a positive number, or nothing. Never a prefilled default.
function formValues(form) {
  const value=key=>{const n=Number(form?.[key]);return form?.[key]!==''&&form?.[key]!=null&&Number.isFinite(n)&&n>0?n:undefined;};
  // The visitor's choice between a text value and a field value that disagreed.
  const prefer=Object.fromEntries(['width','depth','levels','plot'].filter(key=>['text','form'].includes(form?.prefer?.[key])).map(key=>[key,form.prefer[key]]));
  return {width:value('width'),depth:value('depth'),levels:value('levels'),plotWidth:value('plotWidth'),plotDepth:value('plotDepth'),prefer};
}

// A question, not a refusal: the brief is supported once the missing value is given.
function ask(message,missing) {
  const error=new Error(message);
  error.code='LOCAL_APARTMENT_UNSUPPORTED';error.question=true;error.missing=missing;
  throw error;
}

export function apartmentFromBrief(text,form={}) {
  const t=normalize(text);
  if(!/(?:عماره|عمار[هة]|مبنى\s+سكني|بنايه\s+سكنيه|apartment\s+building|residential\s+building)/.test(t.slice(0,260))) return null;
  if(/^(?:صمم\s+|انشئ\s+|ابن\s+)?(?:مستودع|مصنع|فيلا|مدرسه)/.test(t.trim())) return null;
  const understanding={}, entrance=entranceDirection(t), courtyard=courtyardChoice(t);
  const model=buildRequestedApartment(t,formValues(form),{entrance,courtyard,understanding});
  const meta=model.meta.acs_apartment;
  understanding.entrance={value:meta.street_edge,source:entrance===undefined?'assumed':'text'};
  understanding.courtyard=courtyard?{value:{w:courtyard.width,d:courtyard.depth},source:courtyard.sized?'text':'assumed_size'}:
    {value:null,source:courtyard===false?'text':'none'};
  // The entrance side is the one value still assumed; say so.
  if(entrance===undefined)
    meta.assumptions.push('لم تحدد جهة المدخل؛ وُضع المدخل في الواجهة الشمالية افتراضاً قابلاً للتعديل.');
  meta.understanding=understanding;
  meta.brief=String(text);
  return model;
}

const sideAr={N:'الشمال',E:'الشرق',S:'الجنوب',W:'الغرب'};
const floorsAr=n=>n===1?'دور واحد':n===2?'دوران':n+(n<=10?' أدوار':' دوراً');
const flatsAr=n=>n===2?'شقتان':n+(n<=10?' شقق':' شقة');
const metresAr=n=>String(Number(n.toFixed(2)));
// The guest confirmation card «فهمنا: …», derived from the model that «ارسم» will draw.
// Each row is plain Arabic; assumed rows are flagged for the visitor.
export function apartmentConfirmation(model) {
  const a=model?.meta?.acs_apartment, u=a?.understanding;
  if(!u) return null;
  const levels=a.occupied_levels, rows=[];
  const groundNote={added:'أضفنا الأرضي إلى العدد الذي ذكرته',stated_inclusive:'شاملة الأرضي كما ذكرت',
    listed:'حسب الأدوار التي عددتها',form:'من حقل عدد الأدوار (شاملة الأرضي)',
    read_inclusive:'حسبنا الأرضي ضمن العدد لأنك لم تذكره'}[u.levels.ground];
  rows.push({key:'levels',label:'الأدوار',
    value:levels===1?'دور واحد (الأرضي فقط)':floorsAr(levels)+': الأرضي و'+floorsAr(levels-1)+' فوقه',
    note:groundNote+(u.levels.chosen?' — اخترتَه حين اختلف الوصف عن الحقل':''),assumed:u.levels.ground==='read_inclusive'&&levels>1});
  const from=source=>source==='form'?'من الحقول':'من وصفك';
  rows.push({key:'building',label:'المبنى',value:'عرض '+metresAr(a.width_m)+' م × عمق '+metresAr(a.depth_m)+' م',
    note:(u.width.source===u.depth.source?from(u.width.source):'العرض '+from(u.width.source)+' والعمق '+from(u.depth.source))+
      (u.width.chosen||u.depth.chosen?' — اخترتَه حين اختلف الوصف عن الحقل':''),assumed:false});
  if(u.plot) rows.push({key:'plot',label:'الأرض',value:metresAr(u.plot.w)+' × '+metresAr(u.plot.d)+' م',note:from(u.plot.source),assumed:false});
  rows.push({key:'units',label:'الشقق',value:'شقتان في كل دور، '+flatsAr(a.units_total)+' في المجموع',
    note:u.units.source==='assumed'?'يرسم المخطط المحلي شقتين في كل دور':null,assumed:u.units.source==='assumed'});
  rows.push({key:'bedrooms',label:'غرف النوم',value:'3 في كل شقة',note:u.bedrooms.source==='assumed'?'لم تحدد عددها':null,assumed:u.bedrooms.source==='assumed'});
  rows.push({key:'entrance',label:'المدخل',value:'من '+sideAr[a.street_edge],
    note:u.entrance.source==='assumed'?'لم تحدد الجهة؛ يمكنك تغييرها بعد الرسم':null,assumed:u.entrance.source==='assumed'});
  const court=u.courtyard;
  rows.push({key:'courtyard',label:'الفناء',
    value:court.value?'فناء مفتوح للسماء '+metresAr(court.value.w)+' × '+metresAr(court.value.d)+' م':'لا يوجد',
    note:court.source==='assumed_size'?'لم تحدد مقاسه':null,assumed:court.source==='assumed_size'});
  // Requests the local generator cannot honour yet: the visitor sees them before drawing.
  const notDrawn=(u.not_drawn||[]).map(item=>item.text);
  return {title:'فهمنا:',rows,notDrawn,assumed:rows.filter(row=>row.assumed).length};
}

function buildRequestedApartment(t,form,options) {
  const brief=options.understanding, size=dimensions(t), stated=occupiedFloorCount(t), listedFloors=listedFloorCount(t);
  // Text and form both stated must agree. A disagreement is never settled silently:
  // it is offered to the visitor, whose choice comes back in form.prefer.
  // (A revision passes the current model instead of a form.)
  const conflicts=[], chosen={};
  const choose=(key,fromText,fromForm,label,unit)=>{
    if(brief&&fromText!==undefined&&fromForm!==undefined&&Math.abs(fromText-fromForm)>1e-9) {
      const pick=form.prefer?.[key];
      if(pick==='form'||pick==='text') { chosen[key]=pick; return pick==='form'?fromForm:fromText; }
      conflicts.push({key,label,unit,text:fromText,form:fromForm});
    }
    return fromText??fromForm;
  };
  let width=choose('width',size.width,form.width,'عرض المبنى',' م'), depth=choose('depth',size.depth,form.depth,'عمق المبنى',' م');
  let levels, ground, height=form.height??3.4;
  if(stated) ({value:levels,ground}=stated);
  else if(listedFloors!==undefined) {levels=listedFloors;ground='listed';}
  else if(/(?:دور\s+|طابق\s+)?ارضي[^.\n]{0,70}(?:اول)[^.\n]{0,40}(?:ثان)/.test(t)) {levels=3;ground='listed';}
  levels=choose('levels',levels,form.levels,'عدد الأدوار','');
  if(levels!==undefined&&(ground===undefined||chosen.levels==='form')) ground='form';
  let plot=size.plot;
  if(brief&&form.plotWidth!==undefined&&form.plotDepth!==undefined) {
    if(plot&&(plot.w!==form.plotWidth||plot.d!==form.plotDepth)&&form.prefer?.plot!=='text') {
      if(form.prefer?.plot==='form') plot={w:form.plotWidth,d:form.plotDepth,source:'form'};
      else conflicts.push({key:'plot',label:'أبعاد الأرض',unit:' م',text:plot.w+' × '+plot.d,form:form.plotWidth+' × '+form.plotDepth});
    } else if(!plot||form.prefer?.plot!=='text') plot={w:form.plotWidth,d:form.plotDepth,source:plot?'text':'form'};
    else plot={...plot,source:'text'};
  } else if(plot) plot={...plot,source:'text'};
  const unitAmount='(?:'+count+'\\s*(?:شقق|شقه|وحدات\\s+سكنيه)|شقتان|شقتين|شقه(?:\\s+واحده)?|وحد(?:تان|تين|ه)\\s+سكني(?:تان|تين|ه))';
  const ordinal='(?:ال)?(?:ارضي|اول|ثان(?:ي)?|ثالث|رابع|خامس|اخير|علوي)';
  const floor='(?:(?:كل\\s+)?(?:ال)?(?:دور|طابق)(?:\\s+'+ordinal+')?|'+ordinal+')';
  const numberOfUnits=phrase=>{
    if(/^(?:شقتان|شقتين|وحدتان|وحدتين)/.test(phrase))return 2;
    return asCount(phrase.match(new RegExp('^'+count))?.[1]??1);
  };
  const distributions=[
    new RegExp('('+unitAmount+')\\s*(?:في|ب|ل)\\s*'+floor,'g'),
    new RegExp(floor+'(?:\\s+(?:فيه|له|يضم|يحوي|يحتوي(?:\\s+على)?|فيها))?\\s*[:،,]?\\s*('+unitAmount+')','g')
  ];
  const totals=new RegExp('(?:ب?اجمالي|مجموع(?:ها)?|المبنى يضم|العماره تضم|(?<![ء-ي])(?<!(?:دور|طابق)(?:\\s+[ء-ي]+)?\\s+)(?:فيها|تضم))\\s*[:=]?\\s*('+unitAmount+')','g');
  if(distributions.some(re=>[...t.matchAll(re)].some(m=>numberOfUnits(m[1])!==2)))
    unsupported('يدعم هذا المخطط المحلي شقتين في كل دور بما فيه الأرضي. يلزم توزيع آخر عند اختلاف عدد الشقق بين الأدوار.');
  const totalsStated=[...t.matchAll(totals)].map(m=>numberOfUnits(m[1]));
  const unitsStated=totalsStated.length>0||distributions.some(re=>[...t.matchAll(re)].length>0);
  const total=levels===undefined?undefined:totalsStated.find(n=>n!==2*levels);
  if(total!==undefined)
    unsupported('ذكرت '+total+' شقق إجمالاً، ويضع هذا المخطط المحلي شقتين في كل دور ('+2*levels+' شقق في '+levels+' أدوار). حدّد عدد الأدوار أو العدد الإجمالي الصحيح، أو اطلب توزيعاً آخر.');
  // Any stated bedroom count («أربع غرف نوم», «كل شقة فيها ٤ غرف نوم») is compared with the plan's three.
  const bedroomCounts=[...t.matchAll(new RegExp('(?<![ء-ي\\d])و?'+count+'\\s*غرف(?:ه)?\\s*(?:ال)?نوم','g'))].map(m=>asCount(m[1]));
  const bedroomsStated=bedroomCounts.length>0;
  const notDrawn=[];
  // In a brief the visitor sees these in «فهمنا» before drawing; a revision has no card, so it still refuses.
  const cannotDraw=(key,text,refusal)=>{ if(brief) { if(!notDrawn.some(item=>item.key===key)) notDrawn.push({key,text}); } else unsupported(refusal); };
  const otherBedrooms=bedroomCounts.find(n=>n!==3);
  if(otherBedrooms!==undefined)
    cannotDraw('bedrooms','غرف النوم: طلبت '+otherBedrooms+'، ويرسم المخطط المحلي 3 غرف نوم في كل شقة','يدعم هذا التوزيع ثلاث غرف نوم في كل شقة. يلزم توزيع آخر لعدد غرف النوم المطلوب.');
  // A restriction explicitly excluded in the brief should not prevent a supported plan.
  const positive=t.replace(/(?:لا\s+(?:يوجد|توجد|اريد|ابي|يتضمن|يشمل)(?:\s+(?:بها|فيها|به|فيه))?\s+|(?<![ء-ي])و?لا\s+|بلا\s*|(?:ب|من\s+)?دون\s+)(?:اي\s*)?(?:ال)?(?:قبو|بدروم|افنيه|فناء|حوش|دوبلكس|دوبليكس|منور|مناور|ملحق|محلات|مواقف|مجلس|مسبح|غرفه\s+(?:خادمه|سائق))/g,'');
  if(/قبو|بدروم/.test(positive)) unsupported('يتضمن وصفك قبواً. يدعم مخطط الشقق المحلي الأدوار فوق الأرض فقط.');
  // Requests the local plan cannot draw are never dropped silently: listed before drawing, or refused.
  if(/(?<![ء-ي])(?:و|ب|ل)?(?:ال)?(?:منور|مناور)(?![ء-ي])/.test(positive))
    cannotDraw('lightwell','منور للتهوية: يرسم المخطط المحلي فناءً مركزياً مفتوحاً للسماء فقط (اكتب «فناء» بأبعاده إن كان هذا مقصودك)',
      'يتضمن وصفك منوراً. يرسم المخطط المحلي فناءً مركزياً مفتوحاً للسماء فقط (بين 3.6 و5 م × بين 4 و6 م)؛ اكتب «فناء» بأبعاده إن كان هذا مقصودك، أو احذف المنور.');
  if(/(?<![ء-ي])(?:و|ب|ل)?(?:ال)?ملحق(?![ء-ي])/.test(positive))
    cannotDraw('annex','ملحق علوي: يضيف المخطط المحلي سطحاً بلا غرف فقط',
      'يتضمن وصفك ملحقاً. يضيف المخطط المحلي سطحاً بلا غرف فقط؛ الملحق العلوي يحتاج إلى توزيع آخر.');
  if(/مجلس\s+(?:لل)?(?:حريم|نساء|السيدات|النساء)|مجلس(?:ين|ان)(?![ء-ي])/.test(positive))
    cannotDraw('ladies_majlis','مجلس حريم منفصل: يرسم المخطط المحلي مجلس ضيوف واحداً في كل شقة','يرسم المخطط المحلي مجلس ضيوف واحداً في كل شقة؛ مجلس الحريم المنفصل يحتاج إلى توزيع آخر.');
  if(/غرف(?:ه|ة)?\s+(?:لل)?(?:خادمه|خدامه|عامله|سائق|سواق)/.test(positive))
    cannotDraw('staff_room','غرفة خادمة أو سائق: لا يرسمها المخطط المحلي','يرسم المخطط المحلي غرف الشقة المعتادة فقط؛ غرفة الخادمة أو السائق تحتاج إلى توزيع آخر.');
  if(/(?<![ء-ي])(?:و|ب)?(?:ال)?مسبح(?![ء-ي])/.test(positive))
    cannotDraw('pool','مسبح: لا يرسمه المخطط المحلي','لا يرسم المخطط المحلي مسبحاً.');
  if(/(?:^|[\s،.,])و?(?:الدور\s+)?(?:ال)?ارضي\s*(?:[:=]|كله|كامل|يكون|عباره\s+عن|فيه|فيها)?\s*(?:محلات|محل\s+تجاري|تجاري|معارض|مواقف|مظلات\s+سيارات)|(?:محلات|مواقف)[^.\n]{0,12}(?:في|ب)\s*(?:الدور\s+)?(?:ال)?ارضي|عماره\s+(?:سكنيه\s+)?تجاريه|تجاريه\s+سكنيه/.test(positive))
    unsupported('يتضمن وصفك أرضياً تجارياً أو مواقف. يضع المخطط المحلي شقتين في كل دور بما فيه الأرضي؛ الاستخدام المختلط يحتاج إلى توزيع آخر.');
  // «كل شقة غرفتين نوم» states two bedrooms per apartment («أضف غرفتي نوم» beside a master room does not).
  if(/(?:(?:في\s+|ل)?كل\s+شقه|لكل\s+شقه)\s*(?:فيها\s+|بها\s+|تتكون\s+من\s+)?(?:غرفتين|غرفتان|غرفتي)\s+نوم(?!\s+(?:اضافيه|اضافيتين|اخري|اخريين))|(?:غرفتين|غرفتان|غرفتي)\s+نوم\s+(?:في|ب|ل)\s*(?:كل\s+)?شقه/.test(positive))
    cannotDraw('bedrooms','غرف النوم: طلبت 2، ويرسم المخطط المحلي 3 غرف نوم في كل شقة','يدعم هذا التوزيع ثلاث غرف نوم في كل شقة. يلزم توزيع آخر لعدد غرف النوم المطلوب.');
  if(/د[وي]بلي?كس|duplex|شقه\s+(?:من|على)\s+(?:طابقين|دورين)/.test(positive))
    unsupported('تتوزع كل شقة محلية على دور واحد. شقق الدوبلكس تحتاج إلى درج وتوزيع خاصين بكل وحدة.');
  const storey=t.match(new RegExp('ارتفاع\\s+(?:(?:كل|بين)\\s+)?(?:ال)?(?:دور|طابق)(?:\\s+الواحد)?\\s*[:=]?\\s*'+decimal));
  if(storey) height=+storey[1];
  // Respect the declared first-floor datum and flag inconsistent level series.
  const datum=(name)=>t.match(new RegExp('(?:منسوب\\s+|و)?'+name+'\\s*[:=]?\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*م'));
  const first=datum('الاول'), second=datum('الثاني'), roof=datum('(?:بلاطه\\s+)?السطح'), groundDatum=datum('الارضي');
  if(first && !storey) height=+first[1];
  if((groundDatum&&+groundDatum[1]!==0)||(first&&Math.abs(+first[1]-height)>0.01)||(second&&Math.abs(+second[1]-2*height)>0.01)||(roof&&levels!==undefined&&Math.abs(+roof[1]-levels*height)>0.01))
    unsupported('المناسيب المحددة غير منتظمة. يدعم مخطط الشقق المحلي ارتفاعاً موحّداً يبدأ من منسوب أرضي 0.00 م.');
  if(conflicts.length) {
    const error=new Error('الوصف والحقول مختلفان في: '+conflicts.map(c=>c.label+' (في الوصف '+c.text+c.unit+'، وفي الحقل '+c.form+c.unit+')').join('، ')+'. أيهما المقصود؟');
    error.code='LOCAL_APARTMENT_UNSUPPORTED';error.question=true;error.conflicts=conflicts;error.missing=[];
    throw error;
  }
  // Refuse what cannot be drawn before asking for what is missing.
  supportedEnvelope(width,depth,levels,height);
  const missing=[...(width===undefined?['width']:[]),...(depth===undefined?['depth']:[]),...(levels===undefined?['levels']:[])];
  if(missing.length) {
    const sizeAsked=width===undefined&&depth===undefined?'كم عرض المبنى وعمقه بالمتر':width===undefined?'كم عرض المبنى بالمتر':depth===undefined?'كم عمق المبنى بالمتر':'';
    const floorsAsked=levels===undefined?(sizeAsked?'، وكم عدد أدواره شاملة الأرضي':'كم عدد الأدوار شاملة الأرضي'):'';
    const example=sizeAsked?' مثل: عرض المبنى ٢٠ م وعمقه ٢٥ م'+(plot?' بعد الارتدادات':'')+'.':'';
    const unitsHint=levels===undefined&&totalsStated.length?' ذكرت '+totalsStated[0]+' شقق، والمخطط المحلي يضع شقتين في كل دور.':'';
    ask((plot||size.plotMentioned)&&sizeAsked?'ذكرت الأرض فقط. '+sizeAsked+floorsAsked+'؟'+example+unitsHint:sizeAsked+floorsAsked+'؟'+example+unitsHint,missing);
  }
  if(plot&&(width>plot.w+1e-9||depth>plot.d+1e-9))
    unsupported('المبنى ('+width+' × '+depth+' م) أكبر من الأرض ('+plot.w+' × '+plot.d+' م). صحّح أبعاد المبنى أو الأرض.');
  const model=design(width,depth,levels,height,'local_brief',options);
  if(notDrawn.length) model.meta.acs_apartment.assumptions.push('لم يُرسم لأنه غير مدعوم في المولّد المحلي بعد: '+notDrawn.map(item=>item.text).join('؛ ')+'.');
  if(brief) Object.assign(brief,{
    width:{value:width,source:size.width!==undefined&&chosen.width!=='form'?'text':'form',...(chosen.width?{chosen:true}:{})},
    depth:{value:depth,source:size.depth!==undefined&&chosen.depth!=='form'?'text':'form',...(chosen.depth?{chosen:true}:{})},
    not_drawn:notDrawn,
    levels:{value:levels,ground,...(chosen.levels?{chosen:true}:{})},
    plot:plot?{w:plot.w,d:plot.d,source:plot.source}:null,
    units:{per_floor:2,total:2*levels,source:unitsStated?'text':'assumed'},
    bedrooms:{per_unit:3,source:bedroomsStated?'text':'assumed'}
  });
  return model;
}

export function apartmentFromRevision(text,currentModel) {
  const prior=currentModel?.meta?.acs_apartment;
  if(prior?.schema!=='acs.local-apartment/1') unsupported('أنشئ أولاً عمارة سكنية محلية حتى تتمكن من تعديل مخططها.');
  const t=normalize(text), courtyard=courtyardChoice(t,prior.courtyard), entrance=entranceDirection(t);
  if(courtyard===undefined && entrance===undefined)
    unsupported('يمكنك تعديل الفناء أو تحديد جهة المدخل الرئيسي. اختر التعديل المطلوب أو اكتب وصفاً جديداً للمبنى.');
  if(/(?:احذف|ازل|الغ|شيل|اضف|ضيف|زد|زيد|زود|نقص|انقل|حرك|غير|بدل|وسع|كبر|صغر|قلل|ارفع|خفض)\s+(?:لي\s+)?(?:ال)?(?:غرف|غرفه|مجلس|مطبخ|درج|سلم|مصعد|دورا?|طابقا?|ادوار|طوابق|شقه|شقق|حمام|نافذه|نوافذ)/.test(t))
    unsupported('تعديل الفناء وجهة المدخل لا يشمل تغيير الغرف أو الأدوار أو الدرج. افصل هذا الطلب في وصف جديد حتى لا نفقد جزءاً منه.');
  if(/(?:حافظ|احتفظ|ابق|بقاء|المحافظه|ثبت|دون تغيير|بدون تغيير|لا\s+(?:تغير|تحرك|تبدل|تمس|تعدل))[^،.!\n]{0,80}(?:مواقع|موقع|مواضع|جهه|جهات|اتجاه|جدران|حوائط|ابعاد\s+(?:(?:جميع|كل)\s+)?الغرف)/.test(t))
    unsupported('تغيير الفناء أو جهة المدخل يعيد توزيع الغرف والجدران. لا يمكن في هذا التعديل تثبيت مواقعها أو اتجاهاتها أو أبعادها الحالية.');
  const existing={width:prior.width_m,depth:prior.depth_m,levels:prior.occupied_levels,height:currentModel.floor_height};
  const oldCourt=prior.courtyard?{width:prior.courtyard.rect_m?.[2]??4,depth:prior.courtyard.rect_m?.[3]??5,size_source:prior.courtyard.size_source}:null;
  const options={courtyard:courtyard===undefined?oldCourt:courtyard,entrance:entrance??prior.street_edge};
  let model=buildRequestedApartment(t,existing,options);
  if(model.site.w!==existing.width || model.site.d!==existing.depth || model.levels.length!==existing.levels || model.floor_height!==existing.height)
    unsupported('تعديل المدخل والفناء يحافظ على أبعاد المبنى والأدوار والشقق. أنشئ وصفاً جديداً للمقاسات أو العدد المختلف.');
  // Regeneration must not erase manual rooms, objects, stairs, engineering
  // layers, or edits on an automatically created roof. Compare all authored
  // root fields and actual roof contents; level.auto alone cannot prove that
  // every descendant is still generated. User metadata is carried below.
  let baseline=design(existing.width,existing.depth,existing.levels,existing.height,prior.source,
    {courtyard:oldCourt,entrance:prior.street_edge});
  const roofLevels=currentModel.levels.filter(level=>level.kind==='roof');
  if(roofLevels.length) {
    if(roofLevels.some(level=>!level.auto)) unsupported('يتضمن المشروع سطحاً مؤلفاً يدوياً. احتفظ به أو ابدأ وصفاً جديداً للتوزيع.');
    baseline=withDefaultRoof(baseline)[0];
  }
  if(currentModel.meta.acs_context_details) {
    baseline=withContextDetails(baseline)[0];
    model=withContextDetails(model)[0];
  }
  // Key order is not authored content; compare canonically ordered JSON.
  const ordered=value=>JSON.stringify(value,(key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?
    Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
  const matches=(a,b)=>ordered(a)===ordered(b);
  const current=withLegacyConventions(currentModel,baseline);
  const sourceKeys=new Set([...Object.keys(current),...Object.keys(baseline)]);
  if([...sourceKeys].some(key=>key!=='meta' &&
    (Object.hasOwn(current,key)!==Object.hasOwn(baseline,key) || !matches(current[key],baseline[key]))))
    unsupported('يتضمن مشروعك تعديلات يدوية على الهندسة أو السطح أو بيانات هندسية إضافية. احتفظ بها في المشروع الحالي، أو نزّل نسخته ثم ابدأ وصفاً جديداً للتوزيع المطلوب.');
  model.meta={...currentModel.meta,...model.meta};
  // The UI reapplies the actual roof preference to this newly built shell.
  delete model.meta.acs_roof;
  if(prior.brief) model.meta.acs_apartment.brief=prior.brief;
  // Keep the brief's stated assumptions; drop the entrance one once a side is chosen.
  model.meta.acs_apartment.assumptions.push(...(prior.assumptions||[]).filter(line=>
    line.startsWith('لم تذكر ')||(entrance===undefined&&line.startsWith('لم تحدد جهة المدخل'))));
  model.meta.acs_apartment.last_revision=String(text);
  return model;
}
