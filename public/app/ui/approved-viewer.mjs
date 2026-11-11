import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

// Convert the compiler's self-contained glTF buffer into GLB in memory. The
// loader receives no external URI and therefore needs no additional CSP origin.
export function embeddedGLB(bytes, revisionId) {
  const document=JSON.parse(new TextDecoder().decode(bytes));
  if(document.extras?.acs_plan_baseline?.revision_id!==revisionId)throw new Error('ملف 3D لا يطابق النسخة المختارة.');
  if(document.buffers?.length!==1||document.images?.length||document.extensionsRequired?.length)throw new Error('تركيب ملف 3D غير مدعوم في العارض.');
  const buffer=document.buffers[0], prefix='data:application/octet-stream;base64,';
  if(typeof buffer.uri!=='string'||!buffer.uri.startsWith(prefix))throw new Error('ملف 3D يجب أن يحتوي بياناته كاملة.');
  const raw=Uint8Array.from(atob(buffer.uri.slice(prefix.length)),c=>c.charCodeAt(0));
  if(raw.length!==buffer.byteLength||raw.length>24*1024*1024)throw new Error('حجم بيانات 3D غير صالح.');
  delete buffer.uri;
  const json=new TextEncoder().encode(JSON.stringify(document)), jsonSize=(json.length+3)&~3, binSize=(raw.length+3)&~3;
  const out=new Uint8Array(12+8+jsonSize+8+binSize), view=new DataView(out.buffer);
  view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,out.length,true);
  view.setUint32(12,jsonSize,true);view.setUint32(16,0x4e4f534a,true);out.fill(32,20,20+jsonSize);out.set(json,20);
  view.setUint32(20+jsonSize,binSize,true);view.setUint32(24+jsonSize,0x004e4942,true);out.set(raw,28+jsonSize);
  return out.buffer;
}

const VIEW_LABELS={exterior:'منظور خارجي',aerial:'من الأعلى',street:'مستوى الشارع',interior:'داخل الفراغ',cutaway:'قص الدور',detail:'تفصيل قريب'};
const KIND_LABELS={WALL:'جدار',FLOOR:'أرضية',ROOF:'سقف',DOOR:'باب',WINDOW:'نافذة',FURN:'عنصر',MEP:'خدمة',SITE:'موقع'};
export function nodeIdentity(name){
  const parts=String(name||'').split('|'),match=/^F(-?\d+)$/.exec(parts[1]||'');
  return {name:String(name||''),kind:parts[0],level:match?Number(match[1]):null,room:parts[2]||null};
}
// One derived assembly may be serialized as many meshes. Group only the exact
// compiler identity, preserving level and owner; this is not a new canonical ID.
export function detailGroupKey(name){
  const parts=String(name||'').split('|');
  const rack=parts[0]==='FURN'&&/^(?:rack|goods|post|beam)(\d+)r(\d+)(?:L\d+(?:s\d+)?|p\d+)?$/.exec(parts[3]||'');
  return rack?[...parts.slice(0,3),'rack'+rack[1]+'r'+rack[2]].join('|'):String(name||'');
}
export function frameBounds(box,direction,fov,aspect,margin=1.12,target=null){
  const center=target?target.clone():box.getCenter(new THREE.Vector3()),forward=direction.clone().normalize();
  const right=new THREE.Vector3(0,1,0).cross(forward).normalize(),up=forward.clone().cross(right).normalize();
  const tanV=Math.tan(THREE.MathUtils.degToRad(fov/2)),tanH=tanV*Math.max(aspect,.1);
  let distance=.1;
  for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
    const point=new THREE.Vector3(x,y,z).sub(center),depth=point.dot(forward);
    distance=Math.max(distance,Math.abs(point.dot(right))*margin/tanH+depth,Math.abs(point.dot(up))*margin/tanV+depth);
  }
  return {position:center.clone().addScaledVector(forward,distance),target:center};
}
export function chooseQuality(sampleMs=0){
  // Conservative initial quality; only measured slow frames reduce it.
  return sampleMs>45?{name:'اقتصادي',pixelRatio:1,shadow:512}:{name:'متوازن',pixelRatio:1.5,shadow:1024};
}
function releaseObject(root){
  const geometry=new Set(),materials=new Set(),textures=new Set();
  root.traverse(object=>{if(object.geometry)geometry.add(object.geometry);for(const material of object.material?(Array.isArray(object.material)?object.material:[object.material]):[]){materials.add(material);for(const value of Object.values(material))if(value?.isTexture)textures.add(value);}});
  geometry.forEach(value=>value.dispose());textures.forEach(value=>value.dispose());materials.forEach(value=>value.dispose());
}
// Presentation-only backdrop. It carries no model data and is never exported.
function skyTexture(){
  const canvas=document.createElement('canvas');canvas.width=4;canvas.height=256;
  const context=canvas.getContext('2d'),gradient=context.createLinearGradient(0,0,0,256);
  gradient.addColorStop(0,'#86aed6');gradient.addColorStop(.5,'#d3e0e8');gradient.addColorStop(1,'#d9dedb');
  context.fillStyle=gradient;context.fillRect(0,0,4,256);
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;return texture;
}
function lineSet(values,color,opacity){
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(values,3));
  const line=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({color,transparent:true,opacity,depthWrite:false}));
  line.userData.presentationOnly=true;return line;
}
function element(tag,text,host,className){const node=document.createElement(tag);if(text!=null)node.textContent=text;if(className)node.className=className;if(host)host.append(node);return node;}

export async function showApprovedGLTF(container, bytes, revisionId, options={}) {
  const current=options.isCurrent||(()=>true),buffer=embeddedGLB(bytes,revisionId);
  const original=JSON.parse(new TextDecoder().decode(bytes));
  const marker=original.extras.acs_plan_baseline;
  const gltf=await new GLTFLoader().parseAsync(buffer,'');
  if(!current()){releaseObject(gltf.scene);return()=>{};}
  const scene=new THREE.Scene();scene.background=new THREE.Color('#dce5e9');scene.add(gltf.scene);
  const bounds=new THREE.Box3().setFromObject(gltf.scene);
  if(bounds.isEmpty()){releaseObject(gltf.scene);throw new Error('لم يتضمن الملف عناصر قابلة للعرض.');}
  const center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),extent=Math.max(size.x,size.y,size.z,1);
  const camera=new THREE.PerspectiveCamera(43,1,Math.max(.015,extent/10000),extent*40);
  const meshes=[],levels=new Map(),roomBounds=new Map(),groups=new Map(),built=new THREE.Box3(),envelope=new THREE.Box3(),kinds=new Set(),obstacles=[];let triangles=0;
  gltf.scene.updateMatrixWorld(true);
  // One clipping plane always exists on the artifact materials, so entering or
  // leaving the cutaway never recompiles them, and cut parts stop casting shadows.
  const clipOff=bounds.max.y+1e4,clipPlane=new THREE.Plane(new THREE.Vector3(0,-1,0),clipOff),clipPlanes=[clipPlane];
  gltf.scene.traverse(object=>{
    if(!object.isMesh)return;
    const association=gltf.parser.associations.get(object);
    const name=original.nodes?.[association?.nodes]?.name||object.userData.name||object.name;
    const identity=nodeIdentity(name),box=new THREE.Box3().setFromObject(object);
    object.userData.acsViewerIdentity=identity;
    const groupKey=detailGroupKey(name);if(!groups.has(groupKey))groups.set(groupKey,[]);groups.get(groupKey).push(object);
    object.castShadow=true;object.receiveShadow=true;meshes.push(object);kinds.add(identity.kind);
    if(identity.kind!=='SITE')built.union(box);
    if(identity.kind==='WALL')envelope.union(box);
    if(['FURN','OBJ','SAFETY'].includes(identity.kind))obstacles.push({level:identity.level,box});
    triangles+=(object.geometry.index?.count||object.geometry.attributes.position?.count||0)/3;
    if(identity.level!==null){
      if(!levels.has(identity.level))levels.set(identity.level,new THREE.Box3());levels.get(identity.level).union(box);
      if(identity.room&&identity.room!=='slab'){
        const key=identity.level+'|'+identity.room;if(!roomBounds.has(key))roomBounds.set(key,{identity,box:new THREE.Box3()});roomBounds.get(key).box.union(box);
      }
    }
    // Keep supplied colors/alpha/roughness and UVs: these are the exact artifact's
    // materials. Lighting/environment is presentation only, never model data.
    for(const material of Array.isArray(object.material)?object.material:[object.material]){
      if(!material.isMeshStandardMaterial)continue;
      // Reflection strength and shadow clipping are presentation settings.
      material.envMapIntensity=material.transparent?1.3:.75;material.clippingPlanes=clipPlanes;material.clipShadows=true;
      if(material.transparent)material.depthWrite=false;
    }
  });
  if(built.isEmpty())built.copy(bounds);
  if(envelope.isEmpty())envelope.copy(built);
  const builtCenter=built.getCenter(new THREE.Vector3()),builtSize=built.getSize(new THREE.Vector3());
  // Entrance side: exterior doors on the building perimeter decide which facade
  // the hero/street cameras face. This only chooses a camera; it adds no geometry.
  const facade={px:0,nx:0,pz:0,nz:0};
  for(const mesh of meshes){
    if(mesh.userData.acsViewerIdentity.kind!=='DOOR')continue;
    const box=new THREE.Box3().setFromObject(mesh),span=box.getSize(new THREE.Vector3()),area=Math.max(span.x,span.z)*span.y,near=.65;
    if(span.x<span.z){if(Math.abs(box.max.x-envelope.max.x)<near)facade.px+=area;if(Math.abs(box.min.x-envelope.min.x)<near)facade.nx+=area;}
    else{if(Math.abs(box.max.z-envelope.max.z)<near)facade.pz+=area;if(Math.abs(box.min.z-envelope.min.z)<near)facade.nz+=area;}
  }
  const facadeKey=Object.entries(facade).sort((a,b)=>b[1]-a[1])[0],frontKey=facadeKey[1]>0?facadeKey[0]:'pz';
  const front=new THREE.Vector3(frontKey==='px'?1:frontKey==='nx'?-1:0,0,frontKey==='pz'?1:frontKey==='nz'?-1:0),side=new THREE.Vector3(front.z,0,-front.x),up=new THREE.Vector3(0,1,0);
  // Edge articulation derived from the exact approved meshes (one draw per level).
  const edgeLines=new Map();let edgeSegments=0;
  if(triangles<=400000){
    const buckets=new Map(),point=new THREE.Vector3();
    for(const mesh of meshes){
      const identity=mesh.userData.acsViewerIdentity;if(identity.kind==='SITE'||identity.kind==='LIGHT')continue;
      const edges=new THREE.EdgesGeometry(mesh.geometry,30),positions=edges.attributes.position,key=identity.level===null?'all':String(identity.level);
      if(!buckets.has(key))buckets.set(key,[]);const values=buckets.get(key);
      for(let index=0;index<positions.count;index++){point.fromBufferAttribute(positions,index).applyMatrix4(mesh.matrixWorld);values.push(point.x,point.y,point.z);}
      edgeSegments+=positions.count/2;edges.dispose();
    }
    for(const [key,values]of buckets){const line=lineSet(values,0x1f2d36,.34);line.material.clippingPlanes=clipPlanes;line.renderOrder=2;scene.add(line);edgeLines.set(key,line);}
  }
  // Architectural dressing of elements that EXIST in the approved artifact: frames,
  // mullions and sills around approved windows, frames/handles/ribs on approved
  // doors. Plus two clearly labelled assumptions: a flat roof over the top floor
  // plate and two human scale figures at the entrance. None of it is selectable,
  // counted, exported or added to the approved mesh list.
  const detailMaterials={
    frame:new THREE.MeshStandardMaterial({color:0x353c43,roughness:.36,metalness:.7}),
    timber:new THREE.MeshStandardMaterial({color:0x4b3019,roughness:.58,metalness:0}),
    metal:new THREE.MeshStandardMaterial({color:0xc2c7cc,roughness:.22,metalness:.92}),
    sill:new THREE.MeshStandardMaterial({color:0xd2cdc3,roughness:.86,metalness:0}),
    roof:new THREE.MeshStandardMaterial({color:0xd6d2c8,roughness:.93,metalness:0}),
    figure:new THREE.MeshStandardMaterial({color:0xf3f5f6,roughness:.9,metalness:0,transparent:true,opacity:.6,depthWrite:false})};
  for(const material of Object.values(detailMaterials)){material.clippingPlanes=clipPlanes;material.clipShadows=true;material.envMapIntensity=.75;}
  const detailBoxes=new Map(),detailObjects=[];let detailInstances=0,roofPieces=0;
  const put=(group,level,material,cx,cy,cz,sx,sy,sz)=>{
    if(!(sx>0&&sy>0&&sz>0))return;const key=group+'|'+(level===null?'all':level)+'|'+material;
    if(!detailBoxes.has(key))detailBoxes.set(key,[]);
    detailBoxes.get(key).push(new THREE.Matrix4().compose(new THREE.Vector3(cx,cy,cz),new THREE.Quaternion(),new THREE.Vector3(sx,sy,sz)));
  };
  if(meshes.length<=20000)for(const mesh of meshes){
    const identity=mesh.userData.acsViewerIdentity;if(identity.kind!=='WINDOW'&&identity.kind!=='DOOR')continue;
    const box=new THREE.Box3().setFromObject(mesh),d=box.getSize(new THREE.Vector3()),c=box.getCenter(new THREE.Vector3());
    const alongX=d.x>=d.z,width=alongX?d.x:d.z,thin=alongX?d.z:d.x;
    if(thin>width*.35||width<.3||d.y<.3)continue;   // only flat, axis-aligned openings are dressed
    const bar=THREE.MathUtils.clamp(Math.min(width,d.y)*.06,.045,.09);
    const at=(u,y,su,sy,sd,material)=>put('detail',identity.level,material,alongX?c.x+u:c.x,y,alongX?c.z:c.z+u,alongX?su:sd,sy,alongX?sd:su);
    if(identity.kind==='WINDOW'){
      const depth=Math.max(thin+.08,.12),panes=Math.max(1,Math.round(width/1.1));
      at(0,box.max.y-bar/2,width,bar,depth,'frame');at(0,box.min.y+bar/2,width,bar,depth,'frame');
      at(-width/2+bar/2,c.y,bar,d.y,depth,'frame');at(width/2-bar/2,c.y,bar,d.y,depth,'frame');
      for(let index=1;index<panes;index++)at(-width/2+width*index/panes,c.y,bar*.7,d.y-bar,depth*.8,'frame');
      if(d.y>1.7)at(0,box.min.y+d.y*.62,width-bar,bar*.7,depth*.8,'frame');
      at(0,box.min.y-.03,width+.14,.06,depth+.2,'sill');
    }else{
      const large=width>2.2,proud=Math.max(thin+.1,.27),jamb=bar*1.5,material=large?'frame':'timber';
      at(-width/2,c.y+jamb/4,jamb,d.y+jamb/2,proud,material);at(width/2,c.y+jamb/4,jamb,d.y+jamb/2,proud,material);at(0,box.max.y,width+jamb,jamb,proud,material);
      if(large){const ribs=Math.max(2,Math.floor(d.y/.55));for(let index=1;index<ribs;index++)at(0,box.min.y+d.y*index/ribs,width-jamb,.03,thin+.05,'frame');}
      else{at(width/2-.15,box.min.y+Math.min(1.02,d.y*.48),.16,.035,thin+.11,'metal');at(0,box.min.y+d.y*.5,width-.34,.028,thin+.02,'timber');}
    }
  }
  const roofLevel=levels.size?Math.max(...levels.keys()):null;
  if(roofLevel!==null&&!kinds.has('ROOF')){
    const top=levels.get(roofLevel).max.y;
    for(const mesh of meshes){
      const identity=mesh.userData.acsViewerIdentity;if(identity.kind!=='FLOOR'||identity.level!==roofLevel||!identity.name.includes('|slab|'))continue;
      const box=new THREE.Box3().setFromObject(mesh),d=box.getSize(new THREE.Vector3()),c=box.getCenter(new THREE.Vector3());
      put('roof',roofLevel,'roof',c.x,top+.11,c.z,d.x+.5,.22,d.z+.5);roofPieces++;
    }
  }
  const unitBox=new THREE.BoxGeometry(1,1,1);
  for(const [key,matrices]of detailBoxes){
    const [group,level,material]=key.split('|'),instances=new THREE.InstancedMesh(unitBox,detailMaterials[material],matrices.length);
    matrices.forEach((matrix,index)=>instances.setMatrixAt(index,matrix));instances.instanceMatrix.needsUpdate=true;
    instances.castShadow=true;instances.receiveShadow=true;instances.frustumCulled=false;instances.userData.presentationOnly=true;scene.add(instances);
    detailObjects.push({object:instances,group,level:level==='all'?null:Number(level)});if(group==='detail')detailInstances+=matrices.length;
  }
  const figures=new THREE.Group();figures.userData.presentationOnly=true;scene.add(figures);
  {
    const entrance=meshes.find(mesh=>mesh.userData.acsViewerIdentity.kind==='DOOR'&&onFront(mesh));
    if(entrance){
      const box=new THREE.Box3().setFromObject(entrance),c=box.getCenter(new THREE.Vector3());
      const clearOfDoor=Math.max(box.max.x-box.min.x,box.max.z-box.min.z)/2;
      // Beside the entrance, never in front of it: they give scale without hiding the door.
      for(const [offset,height]of [[clearOfDoor+1.1,1.76],[clearOfDoor+1.75,1.6]]){
        const foot=new THREE.Vector3(c.x,box.min.y,c.z).addScaledVector(front,1.5+(height-1.6)*2).addScaledVector(side,offset);
        const body=new THREE.Mesh(new THREE.CylinderGeometry(.13,.17,height-.26,14),detailMaterials.figure),head=new THREE.Mesh(new THREE.SphereGeometry(.11,14,10),detailMaterials.figure);
        body.position.set(foot.x,foot.y+(height-.26)/2,foot.z);head.position.set(foot.x,foot.y+height-.12,foot.z);
        for(const part of [body,head]){part.castShadow=true;part.receiveShadow=true;part.userData.presentationOnly=true;figures.add(part);}
      }
    }
  }
  let renderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:false});}
  catch(error){releaseObject(scene);throw new Error('العرض ثلاثي الأبعاد غير متاح في هذا المتصفح. يمكنك متابعة المخطط ثنائي الأبعاد والحفظ والتصدير.');}
  const gl=renderer.getContext(),debug=gl.getExtension('WEBGL_debug_renderer_info');
  const rendererName=String(debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):'unavailable'),software=/swiftshader|llvmpipe|software|microsoft basic render/i.test(rendererName);
  let quality=chooseQuality(software?46:0),disposed=false,lost=false,frame=0,transition=null,selected=null,currentPreset='exterior';
  renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,quality.pixelRatio));
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.localClippingEnabled=true;
  const environmentScene=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromScene(environmentScene,.04);
  scene.environment=environment.texture;environmentScene.dispose();pmrem.dispose();
  const sky=skyTexture();scene.background=sky;scene.fog=new THREE.Fog(0xd3dbd9,extent*4,extent*17);
  scene.add(new THREE.HemisphereLight(0xdcebff,0x8a7b68,.55));
  const sun=new THREE.DirectionalLight(0xfff0d8,2.9);sun.position.copy(center).addScaledVector(front,extent*.75).addScaledVector(side,extent*.9).addScaledVector(up,extent*1.35);
  let sunHour=10;
  // A presentation sun, not a solar study: the artifact declares no north.
  function applySun(hour){
    sunHour=THREE.MathUtils.clamp(Number(hour)||10,6,18);
    const t=(sunHour-6)/12,elevation=THREE.MathUtils.degToRad(9+62*Math.sin(Math.PI*t)),azimuth=THREE.MathUtils.degToRad((t-.5)*150+40);
    const flat=new THREE.Vector3().addScaledVector(front,Math.cos(azimuth)).addScaledVector(side,Math.sin(azimuth));
    sun.position.copy(center).addScaledVector(flat,extent*1.6*Math.cos(elevation)).addScaledVector(up,extent*1.6*Math.sin(elevation));
    const warm=1-Math.sin(Math.PI*t);sun.color.setRGB(1,.94-.2*warm,.85-.42*warm);sun.intensity=2.9-1.1*warm;
  }
  applySun(sunHour);
  sun.target.position.copy(center);sun.castShadow=true;sun.shadow.mapSize.set(quality.shadow,quality.shadow);sun.shadow.bias=-.00018;sun.shadow.normalBias=.03;
  Object.assign(sun.shadow.camera,{left:-extent*.85,right:extent*.85,top:extent*.85,bottom:-extent*.85,near:.1,far:extent*5});scene.add(sun,sun.target);
  const fill=new THREE.DirectionalLight(0xcfe2ff,.5);fill.position.copy(center).addScaledVector(front,-extent).addScaledVector(side,-extent).addScaledVector(up,extent*.4);scene.add(fill);
  // One room lamp for the interior view only. It always exists (fixed light count,
  // no shader recompiles) and is off in every other view.
  const lamp=new THREE.PointLight(0xfff1dc,0,0,2);lamp.userData.presentationOnly=true;scene.add(lamp);
  // Context plane is explicitly separate; it is not selectable/exported/quantified.
  const ground=new THREE.Mesh(new THREE.CircleGeometry(extent*18,72),new THREE.MeshStandardMaterial({color:0xb4b7ae,roughness:.97,metalness:0,envMapIntensity:.35}));
  ground.rotation.x=-Math.PI/2;ground.position.set(center.x,bounds.min.y-.035,center.z);ground.receiveShadow=true;ground.userData.presentationOnly=true;scene.add(ground);
  // Scale cue: a metric reference grid around the building. Presentation only.
  const gridCell=Math.max(builtSize.x,builtSize.z)>60?5:1,gridMajor=gridCell*5,gridPad=Math.max(gridMajor,Math.ceil(Math.max(builtSize.x,builtSize.z)*.3/gridMajor)*gridMajor);
  const gx0=Math.floor((built.min.x-gridPad)/gridMajor)*gridMajor,gx1=Math.ceil((built.max.x+gridPad)/gridMajor)*gridMajor,gz0=Math.floor((built.min.z-gridPad)/gridMajor)*gridMajor,gz1=Math.ceil((built.max.z+gridPad)/gridMajor)*gridMajor;
  let siteTop=bounds.min.y;for(const mesh of meshes)if(mesh.userData.acsViewerIdentity.kind==='SITE')siteTop=Math.max(siteTop,new THREE.Box3().setFromObject(mesh).max.y);
  const gridY=siteTop+.012,minor=[],major=[];
  for(let x=gx0;x<=gx1+1e-6;x+=gridCell)(Math.round(x/gridCell)%5===0?major:minor).push(x,gridY,gz0,x,gridY,gz1);
  for(let z=gz0;z<=gz1+1e-6;z+=gridCell)(Math.round(z/gridCell)%5===0?major:minor).push(gx0,gridY,z,gx1,gridY,z);
  const gridMinor=lineSet(minor,0x43535c,.13),gridMajorLines=lineSet(major,0x43535c,.3);scene.add(gridMinor,gridMajorLines);
  // Sun and model are static: the shadow map is refreshed only when visibility
  // or the cut changes, not on every camera frame.
  renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true;
  const shell=element('div',null,null,'av-shell'),stage=element('div',null,shell,'av-stage');
  const canvas=renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('aria-label','عرض تفاعلي للنسخة المعتمدة. الأسهم لتدوير العرض، زائد وناقص للتقريب، Home لإعادة الضبط.');stage.append(canvas);
  const toolbar=element('div',null,shell,'av-toolbar');toolbar.setAttribute('role','toolbar');toolbar.setAttribute('aria-label','زوايا عرض المخطط');
  const buttons={};for(const [name,label]of Object.entries(VIEW_LABELS)){const button=element('button',label,toolbar);button.type='button';button.dataset.view=name;buttons[name]=button;}
  const floorLabel=element('label','الدور المعروض',toolbar);const floors=element('select',null,floorLabel);floors.setAttribute('aria-label','الدور المعروض في 3D');
  const all=element('option','جميع الأدوار',floors);all.value='all';
  [...levels.keys()].sort((a,b)=>a-b).forEach(index=>{const option=element('option',index<0?'القبو '+Math.abs(index):index===0?'الأرضي':'الدور '+index,floors);option.value=String(index);});
  floors.disabled=!levels.size;
  const reset=element('button','إعادة الضبط',toolbar);reset.type='button';
  const tourButton=element('button','جولة تلقائية',toolbar);tourButton.type='button';tourButton.setAttribute('aria-pressed','false');
  const more=element('details',null,toolbar,'av-more');element('summary','خيارات العرض',more);const moreBody=element('div',null,more,'av-more-body');
  const qualityButton=element('button','الجودة: '+quality.name,moreBody);qualityButton.type='button';
  const labelButton=element('button','أسماء الفراغات',moreBody);labelButton.type='button';labelButton.setAttribute('aria-pressed','true');
  const detailButton=element('button','تفاصيل الفتحات',moreBody);detailButton.type='button';detailButton.setAttribute('aria-pressed','true');
  const roofButton=element('button','سقف افتراضي',moreBody);roofButton.type='button';roofButton.setAttribute('aria-pressed',String(roofPieces>0));roofButton.disabled=!roofPieces;
  const sunLabel=element('label','الشمس',moreBody),sunRange=element('input',null,sunLabel);sunRange.type='range';sunRange.min='6';sunRange.max='18';sunRange.step='0.5';sunRange.value=String(sunHour);sunRange.setAttribute('aria-label','موضع الشمس للعرض، من الصباح إلى المساء');
  const badge=element('div',null,stage,'av-badge');element('strong','نسخة معتمدة · عرض مشتق',badge);element('bdi',revisionId,badge);badge.title='بصمة النموذج: '+marker.model_hash;
  const inspector=element('div','اختر عنصرًا لعرض هويته ودوره.',stage,'av-inspector');inspector.setAttribute('role','status');inspector.setAttribute('aria-live','polite');
  const hint=element('p','اسحب للدوران · إصبعان للتحريك والتقريب · الأسهم للدوران · +/− للتقريب. مربع الشبكة = '+gridCell+' م. الكاميرا حرة وليست إثباتًا لقابلية المشي.',shell,'av-help');
  const disclosure=element('details',null,shell,'av-evidence');element('summary','النسخة وحدود العرض',disclosure);
  element('p','الهندسة والأبعاد من الملف المعتمد. أرضية السياق والسماء والإضاءة وشبكة القياس وخطوط الحواف وأسماء الفراغات عرض فقط ولا تدخل في التصدير أو الكميات. الخامات الظاهرة لا تؤكد تشطيبًا هندسيًا. القص يخفي أجزاء للعرض ولا يعدّل النسخة.',disclosure);
  element('p','إطارات النوافذ والأبواب ومقابضها مشتقة من فتحات موجودة في النسخة لتوضيحها فقط. شخصا المقياس بجانب المدخل ومصباح المشهد الداخلي وموضع الشمس عرض فقط؛ الملف لا يحدد اتجاه الشمال، فالظلال ليست دراسة شمسية.',disclosure);
  if(!kinds.has('ROOF'))element('p','هذا الملف لا يحتوي سقفًا علويًا. «سقف افتراضي» بلاطة مسطحة للعرض فقط فوق بلاطة الدور الأخير، يمكن إخفاؤها، ولا تدخل في النسخة أو التصدير أو الكميات.',disclosure);
  const evidence=element('output','',disclosure);evidence.dir='ltr';
  // Short room names anchored to the approved rooms. Names come from the review
  // packet when supplied, otherwise from the artifact's own room identifiers.
  const labelLayer=element('div',null,stage,'av-labels');labelLayer.setAttribute('aria-hidden','true');
  const labels=[],projected=new THREE.Vector3();let labelsOn=true;
  for(const row of roomBounds.values()){
    if(labels.length>=80)break;
    const source=options.projections?.find(p=>p.level_index===row.identity.level)?.primitives?.find(p=>p.source?.room_id===row.identity.room);
    const node=element('span',source?.label||row.identity.room,labelLayer,'av-label');node.dir='auto';node.hidden=true;
    labels.push({node,row,center:row.box.getCenter(new THREE.Vector3())});
  }
  function placeLabels(){
    const show=labelsOn&&['exterior','aerial','cutaway'].includes(currentPreset),floor=floors.value==='all'?null:Number(floors.value),w=stage.clientWidth,h=stage.clientHeight;
    for(const label of labels){
      const box=label.row.box;let visible=show&&(floor===null||label.row.identity.level===floor);
      // With every floor visible only the top instance is named, so stacked names do not collide.
      if(visible&&floor===null&&currentPreset!=='exterior'&&label.row.identity.level!==topLevel)visible=false;
      if(visible){
        projected.set(label.center.x,currentPreset==='cutaway'?Math.min(box.max.y,clipPlane.constant):box.max.y,label.center.z).project(camera);
        visible=projected.z>-1&&projected.z<1&&Math.abs(projected.x)<.97&&Math.abs(projected.y)<.94;
        if(visible)label.node.style.transform=`translate(-50%,-50%) translate(${((projected.x+1)/2*w).toFixed(1)}px,${((1-projected.y)/2*h).toFixed(1)}px)`;
      }
      label.node.hidden=!visible;
    }
  }
  const controls=new OrbitControls(camera,canvas);controls.target.copy(center);controls.minDistance=.05;controls.maxDistance=extent*8;controls.enableDamping=false;controls.maxPolarAngle=Math.PI*.98;
  let selectionBox=null,samples=[],measuredMs=null,autoAdjusted=false,slowDevice=false,detailOn=true,roofOn=roofPieces>0,tour=0,tourIndex=0,updatingControls=false,framedBounds=null;
  const updateControls=()=>{updatingControls=true;try{controls.update();}finally{updatingControls=false;}};
  const controlsChanged=()=>{if(!updatingControls)render();};
  const topLevel=levels.size?Math.max(...levels.keys()):null;
  const telemetry={revisionId,modelHash:marker.model_hash,meshCount:meshes.length,triangleCount:triangles,quality:quality.name,qualityReason:software?'reported software renderer; canonical geometry unchanged':'conservative initial quality; optional measured adjustment',rendererName,renderCalls:0,activeAnimation:false,frameIntervalsMs:[],frameIntervalScope:'consecutive requestAnimationFrame callbacks within one active preset transition; excludes idle/screenshot gaps',detailGroupSize:0,
    rackGroups:[...groups.entries()].filter(([key,items])=>/^FURN\|F-?\d+\|[^|]+\|rack\d+r\d+$/.test(key)&&items.length>1).map(([name,items])=>{const box=new THREE.Box3();for(const mesh of items)box.union(new THREE.Box3().setFromObject(mesh));return{name,meshCount:items.length,center:box.getCenter(new THREE.Vector3()).toArray()};}),
    presentation:{detailInstances,roofPieces,assumedRoofShown:roofPieces>0,figures:figures.children.length/2,sunHour,tour:false,edgeSegments,edgeLayers:edgeLines.size,roomLabels:labels.length,gridCellM:gridCell,clippingPlanes:1,animatedTransitions:true,roofInArtifact:kinds.has('ROOF'),entranceSide:frontKey,entranceDetected:facadeKey[1]>0}};
  container.acsViewer=telemetry;container.dataset.revision=revisionId;
  const info=()=>{evidence.textContent=`revision=${revisionId}\nmodel=${marker.model_hash}\nmeshes=${meshes.length}; triangles=${triangles}; quality=${quality.name}\nrender CPU submission (ms)=${measuredMs===null?'not measured':measuredMs.toFixed(2)}; device/browser=${navigator.userAgent}\nviewport=${stage.clientWidth}x${stage.clientHeight}; DPR=${renderer.getPixelRatio()}`;};
  function render(){
    if(disposed||lost||document.hidden||!current()||!container.isConnected||!stage.clientWidth||!stage.clientHeight)return;
    const start=performance.now();renderer.render(scene,camera);const ms=performance.now()-start;telemetry.renderCalls++;placeLabels();
    if(samples.length<12){samples.push(ms);measuredMs=samples.reduce((a,b)=>a+b,0)/samples.length;}
    info();
    if(!autoAdjusted&&samples.length===12){
      autoAdjusted=true;const stable=samples.slice(2).sort((a,b)=>a-b);
      if(stable[Math.floor(stable.length/2)]>45&&quality.pixelRatio>1)Promise.resolve().then(()=>{if(!disposed)applyQuality(true);});
    }
  }
  function stopMotion(){if(frame)cancelAnimationFrame(frame);frame=0;transition=null;telemetry.activeAnimation=false;}
  function animate(now){
    if(disposed||lost||document.hidden||!current()){stopMotion();return;}
    if(transition.previousFrame&&telemetry.frameIntervalsMs.length<600)telemetry.frameIntervalsMs.push(now-transition.previousFrame);
    // A frame gap above 120 ms means this device cannot animate smoothly: finish
    // this move at once and stop animating later moves. Geometry is unaffected.
    if(transition.previousFrame&&now-transition.previousFrame>120){slowDevice=true;telemetry.presentation.animatedTransitions=false;}
    transition.previousFrame=now;
    const t=slowDevice?1:Math.min(1,(now-transition.start)/450),ease=t*t*(3-2*t);
    camera.position.lerpVectors(transition.fromPosition,transition.position,ease);controls.target.lerpVectors(transition.fromTarget,transition.target,ease);updateControls();render();
    if(t<1)frame=requestAnimationFrame(animate);else stopMotion();
  }
  function move(position,target,smooth=true){
    stopMotion();if(!smooth||slowDevice||globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches){camera.position.copy(position);controls.target.copy(target);updateControls();render();return;}
    transition={start:performance.now(),fromPosition:camera.position.clone(),fromTarget:controls.target.clone(),position,target};telemetry.activeAnimation=true;frame=requestAnimationFrame(animate);
  }
  function chosenBounds(){return floors.value==='all'?built:levels.get(Number(floors.value))||built;}
  function detailMeshes(object){return groups.get(detailGroupKey(object.userData.acsViewerIdentity.name))||[object];}
  function detailBounds(object){const box=new THREE.Box3();for(const mesh of detailMeshes(object))box.union(new THREE.Box3().setFromObject(mesh));return box;}
  function chosenRoom(){
    if(selected){const identity=selected.userData.acsViewerIdentity;const match=roomBounds.get(identity.level+'|'+identity.room);if(match)return match;}
    return [...roomBounds.values()].filter(row=>floors.value==='all'||row.identity.level===Number(floors.value)).sort((a,b)=>{const x=a.box.getSize(new THREE.Vector3()),y=b.box.getSize(new THREE.Vector3());return y.x*y.z-x.x*x.z;})[0];
  }
  function setVisibility(){
    const floor=floors.value==='all'?null:Number(floors.value);
    for(const mesh of meshes){const id=mesh.userData.acsViewerIdentity;mesh.visible=floor===null||id.level===null||id.level===floor;}
    for(const [key,line]of edgeLines)line.visible=floor===null||key==='all'||Number(key)===floor;
    const cut=chosenBounds();clipPlane.constant=currentPreset==='cutaway'?cut.min.y+Math.min(1.5,cut.getSize(new THREE.Vector3()).y*.65):clipOff;renderer.shadowMap.needsUpdate=true;
    const roofVisible=roofOn&&!['aerial','cutaway'].includes(currentPreset);
    for(const item of detailObjects)item.object.visible=(item.group==='roof'?roofVisible:detailOn)&&(floor===null||item.level===null||item.level===floor);
    figures.visible=detailOn&&floor===null&&!['detail','interior'].includes(currentPreset);telemetry.presentation.assumedRoofShown=roofVisible;
    if(selectionBox)selectionBox.visible=selected?.visible!==false;
  }
  function preset(name,smooth=true){
    currentPreset=name;setVisibility();for(const [key,button]of Object.entries(buttons))button.setAttribute('aria-pressed',String(key===name));
    const box=chosenBounds().clone();if(name==='cutaway')box.max.y=Math.min(box.max.y,clipPlane.constant);framedBounds=box.clone();
    lamp.intensity=0;
    const fov=name==='interior'?64:43;if(camera.fov!==fov){camera.fov=fov;camera.updateProjectionMatrix();}
    const along=(a,b,d)=>new THREE.Vector3().addScaledVector(front,a).addScaledVector(side,b).addScaledVector(up,d).normalize();
    let {position,target}=frameBounds(box,along(1,.82,.5),camera.fov,camera.aspect);
    if(name==='aerial')({position,target}=frameBounds(box,along(.03,0,1),camera.fov,camera.aspect));
    if(name==='cutaway')({position,target}=frameBounds(box,along(.62,.45,1),camera.fov,camera.aspect));
    if(name==='street'){
      // Fit the actual envelope from standing eye height on the entrance side.
      target=box.getCenter(new THREE.Vector3());target.y=box.min.y+1.65;
      ({position,target}=frameBounds(box,along(1,.42,0),camera.fov,camera.aspect,1.12,target));
    }
    if(name==='interior'){
      const room=chosenRoom();if(!room){inspector.textContent='لم يُحدّد الملف فراغًا صالحًا لكاميرا داخلية. اختر عنصرًا أو استخدم القص.';return;}
      framedBounds=null;const r=room.box,rs=r.getSize(new THREE.Vector3());target=r.getCenter(new THREE.Vector3());target.y=r.min.y+Math.min(1.45,Math.max(.2,rs.y*.5));
      const eye=r.min.y+Math.min(1.6,Math.max(.25,rs.y*.6)),inside=obstacles.filter(row=>row.level===room.identity.level&&row.box.intersectsBox(r));
      let best=null;
      for(const [fx,fz]of [[.16,.16],[.84,.16],[.16,.84],[.84,.84],[.5,.16],[.5,.84],[.16,.5],[.84,.5]]){
        const spot=new THREE.Vector3(r.min.x+rs.x*fx,eye,r.min.z+rs.z*fz),clear=inside.reduce((nearest,row)=>Math.min(nearest,row.box.distanceToPoint(spot)),Infinity);
        if(!best||clear>best.clear+.05)best={spot,clear,fx,fz};
      }
      position=best.spot;target.x=r.min.x+rs.x*(1-best.fx*.6-.2);target.z=r.min.z+rs.z*(1-best.fz*.6-.2);
      inspector.textContent='كاميرا داخل '+room.identity.room+' · حركة حرة؛ اتصال الدرج والممرات غير متحقق هنا.';
      const middle=r.getCenter(new THREE.Vector3());lamp.position.set(middle.x,r.min.y+rs.y*.82,middle.z);lamp.intensity=1.6*rs.y*rs.y+.12*rs.x*rs.z;
    }
    if(name==='detail'){
      const shown=meshes.filter(mesh=>mesh.visible),kindOf=mesh=>mesh.userData.acsViewerIdentity.kind;
      const object=selected||shown.find(mesh=>kindOf(mesh)==='DOOR'&&onFront(mesh))||shown.find(mesh=>kindOf(mesh)==='WINDOW')||shown.find(mesh=>kindOf(mesh)==='DOOR')||shown.find(mesh=>['FURN','OBJ'].includes(kindOf(mesh)))||shown[0];
      if(object){
        select(object,false);const detail=detailBounds(object),d=detail.getSize(new THREE.Vector3());framedBounds=detail.clone();target=detail.getCenter(new THREE.Vector3());
        // Face a flat element (door, window, panel) square-on from the side away from the building centre.
        const thinX=d.x<d.z,flat=Math.min(d.x,d.z)<Math.max(d.x,d.z)*.35,normal=flat?new THREE.Vector3(thinX?1:0,0,thinX?0:1):new THREE.Vector3(1,0,1).normalize();
        if(normal.dot(target.clone().sub(builtCenter))<0)normal.negate();
        const tangent=new THREE.Vector3(normal.z,0,-normal.x),direction=normal.clone().addScaledVector(tangent,.16).addScaledVector(up,.16);
        ({position,target}=frameBounds(detail,direction,camera.fov,camera.aspect,1.2));
      }
    }
    move(position,target,smooth);
  }
  function onFront(mesh){const box=new THREE.Box3().setFromObject(mesh),probe=front.x?(front.x>0?envelope.max.x-box.max.x:box.min.x-envelope.min.x):(front.z>0?envelope.max.z-box.max.z:box.min.z-envelope.min.z);return Math.abs(probe)<.65;}
  function select(object,draw=true){
    if(selectionBox){scene.remove(selectionBox);selectionBox.geometry.dispose();selectionBox.material.dispose();selectionBox=null;}
    selected=object;if(!object){inspector.textContent='اختر عنصرًا لعرض هويته ودوره.';if(draw)render();return;}
    telemetry.detailGroupSize=detailMeshes(object).length;selectionBox=new THREE.Box3Helper(detailBounds(object),0x078bba);selectionBox.material.depthTest=false;selectionBox.material.toneMapped=true;selectionBox.material.transparent=true;selectionBox.userData.presentationOnly=true;selectionBox.renderOrder=10;scene.add(selectionBox);
    const identity=object.userData.acsViewerIdentity;
    inspector.replaceChildren();const source=options.projections?.find(p=>p.level_index===identity.level)?.primitives?.find(p=>p.source?.room_id===identity.room);
    element('strong',(KIND_LABELS[identity.kind]||'عنصر')+' · '+(source?.label||identity.room||'الموقع'),inspector);
    if(source?.source_id)element('bdi','الفراغ المصدر: '+source.source_id,inspector);
    element('span',identity.level===null?'لا يحمل معرّف دور':identity.level===0?'الدور الأرضي':'الدور '+identity.level,inspector);
    element('bdi',identity.name,inspector);if(telemetry.detailGroupSize>1)element('span','مجموعة عرض مترابطة · '+telemetry.detailGroupSize+' أجزاء من الملف',inspector);element('small','معرّف ملف العرض · النسخة '+revisionId,inspector);if(draw)render();
  }
  const tourViews=['exterior','street','interior','cutaway','aerial','detail'];
  function stopTour(){if(!tour)return;clearInterval(tour);tour=0;tourButton.setAttribute('aria-pressed','false');telemetry.presentation.tour=false;}
  function startTour(){
    stopTour();tourIndex=0;select(null,false);preset(tourViews[0]);tourButton.setAttribute('aria-pressed','true');telemetry.presentation.tour=true;
    tour=setInterval(()=>{if(disposed||lost||document.hidden||!current()){stopTour();return;}tourIndex=(tourIndex+1)%tourViews.length;select(null,false);preset(tourViews[tourIndex]);},3800);
  }
  const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=null;
  const pointerDown=event=>{down={x:event.clientX,y:event.clientY};stopTour();stopMotion();};
  const pointerUp=event=>{if(!down||Math.hypot(event.clientX-down.x,event.clientY-down.y)>5)return;const rect=canvas.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(meshes.filter(mesh=>mesh.visible),false).find(item=>clipPlane.distanceToPoint(item.point)>=0);select(hit?.object||null);};
  const keydown=event=>{
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Home'].includes(event.key))return;event.preventDefault();stopTour();stopMotion();
    if(event.key==='Home'){preset('exterior');return;}
    const offset=camera.position.clone().sub(controls.target),spherical=new THREE.Spherical().setFromVector3(offset);
    if(event.key==='ArrowLeft')spherical.theta+=.12;if(event.key==='ArrowRight')spherical.theta-=.12;
    if(event.key==='ArrowUp')spherical.phi=Math.max(.03,spherical.phi-.1);if(event.key==='ArrowDown')spherical.phi=Math.min(Math.PI-.03,spherical.phi+.1);
    if(event.key==='+'||event.key==='=')spherical.radius=Math.max(.05,spherical.radius*.85);if(event.key==='-')spherical.radius=Math.min(extent*8,spherical.radius/ .85);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));updateControls();render();
  };
  const resize=()=>{if(disposed||lost)return;const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);render();};
  const visibility=()=>{if(document.hidden){stopTour();stopMotion();}else resize();};
  function applyQuality(low){quality=chooseQuality(low?46:0);telemetry.quality=quality.name;renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,quality.pixelRatio));sun.shadow.mapSize.set(quality.shadow,quality.shadow);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}renderer.shadowMap.needsUpdate=true;qualityButton.textContent='الجودة: '+quality.name;resize();}
  const observer=new ResizeObserver(resize);controls.addEventListener('change',controlsChanged);
  canvas.addEventListener('pointerdown',pointerDown);canvas.addEventListener('pointerup',pointerUp);canvas.addEventListener('keydown',keydown);document.addEventListener('visibilitychange',visibility);
  for(const [name,button]of Object.entries(buttons))button.addEventListener('click',()=>{stopTour();preset(name);});
  tourButton.addEventListener('click',()=>{if(tour)stopTour();else startTour();});
  detailButton.addEventListener('click',()=>{detailOn=!detailOn;detailButton.setAttribute('aria-pressed',String(detailOn));setVisibility();render();});
  roofButton.addEventListener('click',()=>{roofOn=!roofOn;roofButton.setAttribute('aria-pressed',String(roofOn));setVisibility();render();});
  sunRange.addEventListener('input',()=>{applySun(sunRange.value);telemetry.presentation.sunHour=sunHour;renderer.shadowMap.needsUpdate=true;render();});
  floors.addEventListener('change',()=>{select(null);preset(currentPreset);});reset.addEventListener('click',()=>{stopTour();floors.value='all';select(null);preset('exterior');});qualityButton.addEventListener('click',()=>applyQuality(quality.pixelRatio>1));
  labelButton.addEventListener('click',()=>{labelsOn=!labelsOn;labelButton.setAttribute('aria-pressed',String(labelsOn));render();});
  function dispose(){
    if(disposed)return;disposed=true;stopTour();stopMotion();observer.disconnect();controls.dispose();document.removeEventListener('visibilitychange',visibility);
    canvas.removeEventListener('pointerdown',pointerDown);canvas.removeEventListener('pointerup',pointerUp);canvas.removeEventListener('keydown',keydown);canvas.removeEventListener('webglcontextlost',contextLost);canvas.removeEventListener('webglcontextrestored',contextRestored);
    releaseObject(scene);Object.values(detailMaterials).forEach(material=>material.dispose());unitBox.dispose();sky.dispose();scene.background=null;environment.dispose();sun.shadow.map?.dispose();renderer.renderLists.dispose();renderer.dispose();renderer.forceContextLoss();shell.remove();if(container.acsViewer===telemetry)delete container.acsViewer;
  }
  const contextLost=event=>{event.preventDefault();lost=true;stopMotion();dispose();options.onFailure?.('فُقد سياق الرسوم. المخطط ثنائي الأبعاد متاح؛ استخدم إعادة محاولة 3D لاستعادة العرض.');};
  const contextRestored=()=>{lost=false;resize();};canvas.addEventListener('webglcontextlost',contextLost);canvas.addEventListener('webglcontextrestored',contextRestored);
  if(!current()){dispose();return()=>{};}
  container.replaceChildren(shell);observer.observe(stage);resize();preset('exterior',false);
  // This is telemetry, not an FPS/GPU-completion benchmark. First software frames
  // can be slow; the user can choose economy without dropping canonical meshes.
  telemetry.inspect=()=>({...telemetry,inspect:undefined,camera:camera.position.toArray(),target:controls.target.toArray(),visibleMeshCount:meshes.filter(mesh=>mesh.visible).length,view:currentPreset,framedBounds:framedBounds?{min:framedBounds.min.toArray(),max:framedBounds.max.toArray()}:null,aspect:camera.aspect,fov:camera.fov});
  return dispose;
}
