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
    const side=Math.abs(fixed)<.06?-1:Math.abs(fixed-far)<.06?1:0;
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

export function fitGuestCamera(box,mode,camera,orbit,viewport,groundY){
  const {width,height,right,top,bottom}=viewport;
  const availableW=Math.max(width*.28,width-right),availableH=Math.max(height*.4,height-top-bottom);
  // Same optical centre and physical FOV in the unobstructed screen region.
  camera.setViewOffset(width,height,right/2,(bottom-top)/2,width,height);
  const effective=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*availableH/height));
  const direction=mode==='cutaway'?new THREE.Vector3(-.62,1.1,-1):
    mode==='aerial'?new THREE.Vector3(.48,1.65,-1):new THREE.Vector3(.56,.48,-1);
  const target=box.getCenter(new THREE.Vector3());
  if(mode==='street'){
    target.y=groundY+1.7;
    direction.set(.24,0,-1);
  }
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
