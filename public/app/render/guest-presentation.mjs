import * as THREE from 'three';
import {frameBounds} from './frame-bounds.mjs';

// Presentation lives in the scene, outside BUILDING and its GLB/export tree.
// The authored local apartment discloses assumed finishes; every frame below
// is fitted to an actual pane. Imported, incomplete geometry is left alone.
export function apartmentJoinery(model,building){
  const group=new THREE.Group();
  group.name='PQ_GUEST_JOINERY';
  group.userData.presentation_context=true;
  if(building?.meta?.acs_apartment?.schema!=='acs.local-apartment/1')return group;
  const buckets=new Map();
  const origin=new THREE.Vector3(),size=new THREE.Vector3(),pose=new THREE.Matrix4(),identity=new THREE.Quaternion();
  const width=Number(building.site?.w),depth=Number(building.site?.d);
  // Both early drafts (axis at gross boundary) and measured new apartments
  // (exterior face at gross boundary) are valid local presentation anchors.
  const perimeterTolerance=.012+Math.min(.25,Math.max(0,Number(building.wall_t)||.15)/2);
  model.updateMatrixWorld(true);
  model.traverse(node=>{
    if(!node.isMesh)return;
    const [layer,floor]=node.name.split('|');
    const entrance=layer==='DOOR'&&node.material.transparent;
    if(layer!=='WINDOW'&&!entrance)return;
    const box=new THREE.Box3().setFromObject(node);
    box.getCenter(origin);box.getSize(size);
    const alongX=size.x>size.z;
    const span=alongX?size.x:size.z;
    const fixed=alongX?origin.z:origin.x;
    const far=alongX?depth:width;
    // Recessed glazed openings get joinery on the pane. Only perimeter
    // windows and street entrances receive projecting exterior profiles.
    const side=Math.abs(fixed)<=perimeterTolerance?-1:Math.abs(fixed-far)<=perimeterTolerance?1:0;
    function piece(finish,along,y,normal,w,h,d){
      const key=[floor,layer,finish].join('|');
      if(!buckets.has(key))buckets.set(key,[]);
      const position=origin.clone();
      position.y+=y;
      position[alongX?'x':'z']+=along;
      position[alongX?'z':'x']+=side*normal;
      const scale=new THREE.Vector3(alongX?w:d,h,alongX?d:w);
      buckets.get(key).push(pose.compose(position,identity,scale).clone());
    }
    const h=size.y,t=.065;
    for(const sign of [-1,1]){
      piece('bronze',sign*(span-t)/2,0,.015,t,h,.13);
      piece('bronze',0,sign*(h-t)/2,.015,span,t,.13);
    }
    if(span>1.35)piece('bronze',0,0,.015,t,h,.13);
    if(side&&layer==='WINDOW'){
      piece('stone',0,-h/2-.045,.075,span+.24,.09,.34);
      piece('stone',0,h/2+.055,.10,span+.32,.11,.38);
    }
  });
  if(!buckets.size)return group;
  const geometry=new THREE.BoxGeometry(1,1,1);
  const finishes={
    bronze:new THREE.MeshStandardMaterial({color:0x584736,metalness:.35,roughness:.44}),
    stone:new THREE.MeshStandardMaterial({color:0xd6c4ab,roughness:.84})
  };
  for(const [key,matrices] of buckets){
    const [floor,layer,finish]=key.split('|');
    const mesh=new THREE.InstancedMesh(geometry,finishes[finish],matrices.length);
    mesh.name='PQ_ASSUMED_JOINERY_'+key;
    Object.assign(mesh.userData,{presentation_context:true,floor,sourceLayer:layer});
    matrices.forEach((m,i)=>mesh.setMatrixAt(i,m));mesh.computeBoundingSphere();
    mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
  }
  for(const mat of Object.values(finishes)){
    if(!group.children.some(mesh=>mesh.material===mat))mat.dispose();
  }
  return group;
}

export function disposeGuestJoinery(group){
  if(!group)return;
  group.removeFromParent();
  const geometries=new Set(),materials=new Set();
  for(const node of group.children){
    geometries.add(node.geometry);materials.add(node.material);node.dispose();
  }
  for(const g of geometries)g.dispose();
  for(const m of materials)m.dispose();
}

// A low-contrast two-metre paving module gives scale without geometry calls.
export function guestPaving(size){
  const n=128,data=new Uint8Array(n*n*4);
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){
    const i=(y*n+x)*4;
    const joint=y%32===0||(x+(Math.floor(y/32)%2)*32)%64===0;
    const grain=(Math.imul(x+1,73856093)^Math.imul(y+1,19349663))>>>28;
    const tone=joint?-24:(grain-7)*.62;
    data[i]=191+tone;data[i+1]=184+tone;data[i+2]=169+tone;data[i+3]=255;
  }
  const tex=new THREE.DataTexture(data,n,n,THREE.RGBAFormat);
  tex.colorSpace=THREE.SRGBColorSpace;tex.wrapS=tex.wrapT=THREE.RepeatWrapping;
  tex.repeat.set(size/2,size/2);tex.generateMipmaps=true;
  tex.minFilter=THREE.LinearMipmapLinearFilter;tex.magFilter=THREE.LinearFilter;
  tex.anisotropy=4;tex.needsUpdate=true;return tex;
}

export function visibleInGuestCut(name,warehouse){
  const [layer,,room,part='']=name.split('|');
  if(layer==='FLOOR'&&/^ceil\d*$/.test(part))return false;
  // This northwest quarter opens the actual logistics shell for inspection.
  return !(warehouse&&layer==='WALL'&&room==='envelope'&&/^w[NW]s\d+$/.test(part));
}

export function fitGuestCamera(box,mode,camera,orbit,viewport,groundY,streetEdge='N'){
  const {width,height,right,top,bottom}=viewport;
  const availableW=Math.max(width*.28,width-right),availableH=Math.max(height*.4,height-top-bottom);
  // Same optical centre and physical FOV in the unobstructed screen region.
  camera.setViewOffset(width,height,right/2,(bottom-top)/2,width,height);
  const effective=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*availableH/height));
  const direction=mode==='top'?new THREE.Vector3(0,1,.0001):mode==='cutaway'?new THREE.Vector3(-.62,1.1,-1):
    mode==='detail'?new THREE.Vector3(.18,.12,-1):mode==='aerial'?new THREE.Vector3(.48,1.65,-1):new THREE.Vector3(.56,.48,-1);
  const target=box.getCenter(new THREE.Vector3());
  if(mode==='street'){
    target.y=groundY+1.7;
    direction.set(.24,0,-1);
  }
  // Show the requested facade and keep north at the top in the overhead view.
  const turn={N:0,E:-Math.PI/2,S:Math.PI,W:Math.PI/2}[streetEdge]||0;
  if(mode!=='top'&&turn)direction.applyAxisAngle(new THREE.Vector3(0,1,0),turn);
  const frame=frameBounds(box,direction,effective,availableW/availableH,1.1,target);
  const radius=box.getBoundingSphere(new THREE.Sphere()).radius;
  const distance=frame.position.distanceTo(frame.target);
  camera.near=Math.max(.025,Math.min(.3,radius*.001));
  camera.far=Math.max(350,distance+radius*15);
  orbit.minDistance=.35;
  orbit.maxDistance=Math.max(120,radius*9,distance*2);
  orbit.maxPolarAngle=Math.PI/2-.001;
  camera.position.copy(frame.position);orbit.target.copy(frame.target);
  camera.updateProjectionMatrix();orbit.update();
}

// OrbitControls limits pitch, but two-finger panning also shifts its target.
export function keepGuestAboveGrade(camera,orbit,groundY){
  const lift=Math.max(0,groundY+.08-orbit.target.y,groundY+.16-camera.position.y);
  if(lift){orbit.target.y+=lift;camera.position.y+=lift;}
}

// Supported close views use the authored door, living room or two real rack
// rows. A broken/missing anchor leaves the previous camera untouched.
export function guestFocus(model,building,kind,warehouse){
  const level=building?.levels?.find(l=>l?.index===0)||building?.levels?.find(l=>l?.index>=0);
  if(!level)return null;
  const rooms=building.floors?.[level.template]?.rooms||[];
  const floor='F'+level.index;
  const base=Number.isFinite(level.elevation)?level.elevation:level.index*(Number(building.floor_height)||3.2);
  const meshes=model.children.filter(o=>o.isMesh&&o.name.split('|')[1]===floor);
  if(kind==='detail'){
    const door=warehouse?meshes.find(o=>/^DOOR\|[^|]+\|inbound_docks\|dock/.test(o.name)):
      meshes.filter(o=>o.name.startsWith('DOOR|')&&o.material.transparent&&
        (o.name.startsWith('DOOR|'+floor+'|lobby|')||o.userData.acs_door_pair?.hosts?.some(h=>h.room_id==='lobby')))
        .sort((a,b)=>a.position.z-b.position.z)[0];
    if(!door)return null;
    const box=new THREE.Box3().setFromObject(door),mid=box.getCenter(new THREE.Vector3());
    const extent=box.getSize(new THREE.Vector3());
    const alongX=extent.x>=extent.z,span=Math.max(extent.x,extent.z,1.8)*1.1;
    const dx=alongX?span:.55,dz=alongX?.55:span;
    return {source:door.name,box:new THREE.Box3(
      new THREE.Vector3(mid.x-dx,base,mid.z-dz),
      new THREE.Vector3(mid.x+dx,base+extent.y+.55,mid.z+dz))};
  }
  const eye=base+1.65;
  if(warehouse){
    const first=meshes.find(o=>/^FURN\|[^|]+\|[^|]+\|rack\d+r0L0$/.test(o.name));
    const next=first&&meshes.find(o=>o.name===first.name.replace('r0L0','r1L0'));
    if(!next)return null;
    const box=new THREE.Box3().setFromObject(first),size=box.getSize(new THREE.Vector3());
    const along=size.x>=size.z?'x':'z',across=along==='x'?'z':'x';
    if(Math.abs(first.position[across]-next.position[across])-size[across]<.6)return null;
    const position=box.getCenter(new THREE.Vector3());
    position[across]=(first.position[across]+next.position[across])/2;
    position[along]=box.min[along]+size[along]*.10;position.y=eye;
    const target=position.clone();target[along]+=Math.min(12,size[along]*.73);
    target[across]+=(first.position[across]-position[across])*.48;target.y-=.1;
    return {source:first.name,position,target};
  }
  const room=rooms.find(r=>r?.role==='living'&&Array.isArray(r.rect));
  if(!room)return null;
  const [x,z,w,d]=room.rect;
  if(![x,z,w,d].every(Number.isFinite)||w<2||d<2)return null;
  return {source:floor+'|'+room.id,position:new THREE.Vector3(x+w*.83,eye,z+d*.87),
    target:new THREE.Vector3(x+w*.30,base+1.06,z+d*.22)};
}
