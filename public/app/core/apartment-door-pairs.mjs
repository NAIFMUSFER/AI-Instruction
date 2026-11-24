// Pure shared-door projection. No generator, renderer, or mutable model dependencies.
const opposite = { N: 'S', S: 'N', E: 'W', W: 'E' };

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
