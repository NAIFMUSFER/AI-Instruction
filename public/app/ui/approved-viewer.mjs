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
export function chooseQuality(sampleMs=0){
  // Conservative initial quality; only measured slow frames reduce it.
  return sampleMs>45?{name:'اقتصادي',pixelRatio:1,shadow:512}:{name:'متوازن',pixelRatio:1.5,shadow:1024};
}
function releaseObject(root){
  const geometry=new Set(),materials=new Set(),textures=new Set();
  root.traverse(object=>{if(object.geometry)geometry.add(object.geometry);for(const material of object.material?(Array.isArray(object.material)?object.material:[object.material]):[]){materials.add(material);for(const value of Object.values(material))if(value?.isTexture)textures.add(value);}});
  geometry.forEach(value=>value.dispose());textures.forEach(value=>value.dispose());materials.forEach(value=>value.dispose());
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
  const meshes=[],levels=new Map(),roomBounds=new Map();let triangles=0;
  gltf.scene.traverse(object=>{
    if(!object.isMesh)return;
    const association=gltf.parser.associations.get(object);
    const name=original.nodes?.[association?.nodes]?.name||object.userData.name||object.name;
    const identity=nodeIdentity(name),box=new THREE.Box3().setFromObject(object);
    object.userData.acsViewerIdentity=identity;object.castShadow=true;object.receiveShadow=true;meshes.push(object);
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
      if(material.isMeshStandardMaterial)material.envMapIntensity=.55;
    }
  });
  let renderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:false});}
  catch(error){releaseObject(scene);throw new Error('العرض ثلاثي الأبعاد غير متاح في هذا المتصفح. يمكنك متابعة المخطط ثنائي الأبعاد والحفظ والتصدير.');}
  let quality=chooseQuality(),disposed=false,lost=false,frame=0,transition=null,selected=null,currentPreset='exterior';
  renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,quality.pixelRatio));
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.localClippingEnabled=true;
  const environmentScene=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromScene(environmentScene,.04);
  scene.environment=environment.texture;environmentScene.dispose();pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0xeaf4ff,0x85745f,1.6));
  const sun=new THREE.DirectionalLight(0xfff2dc,3.2);sun.position.copy(center).add(new THREE.Vector3(extent*.7,extent*1.4,extent*.6));
  sun.target.position.copy(center);sun.castShadow=true;sun.shadow.mapSize.set(quality.shadow,quality.shadow);sun.shadow.bias=-.00012;sun.shadow.normalBias=.035;
  Object.assign(sun.shadow.camera,{left:-extent*.7,right:extent*.7,top:extent*.7,bottom:-extent*.7,near:.1,far:extent*5});scene.add(sun,sun.target);
  const fill=new THREE.DirectionalLight(0xcde3ff,1.2);fill.position.copy(center).add(new THREE.Vector3(-extent,extent*.3,-extent));scene.add(fill);
  // Context plane is explicitly separate; it is not selectable/exported/quantified.
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(extent*5,extent*5),new THREE.MeshStandardMaterial({color:0xc4cbc6,roughness:.96,metalness:0}));
  ground.rotation.x=-Math.PI/2;ground.position.set(center.x,bounds.min.y-.035,center.z);ground.receiveShadow=true;ground.userData.presentationOnly=true;scene.add(ground);
  const shell=element('div',null,null,'av-shell'),stage=element('div',null,shell,'av-stage');
  const canvas=renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('aria-label','عرض تفاعلي للنسخة المعتمدة. الأسهم لتدوير العرض، زائد وناقص للتقريب، Home لإعادة الضبط.');stage.append(canvas);
  const toolbar=element('div',null,shell,'av-toolbar');toolbar.setAttribute('role','toolbar');toolbar.setAttribute('aria-label','زوايا عرض المخطط');
  const buttons={};for(const [name,label]of Object.entries(VIEW_LABELS)){const button=element('button',label,toolbar);button.type='button';button.dataset.view=name;buttons[name]=button;}
  const floorLabel=element('label','الدور المعروض',toolbar);const floors=element('select',null,floorLabel);floors.setAttribute('aria-label','الدور المعروض في 3D');
  const all=element('option','جميع الأدوار',floors);all.value='all';
  [...levels.keys()].sort((a,b)=>a-b).forEach(index=>{const option=element('option',index<0?'القبو '+Math.abs(index):index===0?'الأرضي':'الدور '+index,floors);option.value=String(index);});
  floors.disabled=!levels.size;
  const reset=element('button','إعادة الضبط',toolbar);reset.type='button';
  const qualityButton=element('button','الجودة: '+quality.name,toolbar);qualityButton.type='button';
  const badge=element('div',null,stage,'av-badge');element('strong','نسخة معتمدة · عرض مشتق',badge);element('bdi',revisionId,badge);badge.title='بصمة النموذج: '+marker.model_hash;
  const inspector=element('div','اختر عنصرًا لعرض هويته ودوره.',stage,'av-inspector');inspector.setAttribute('role','status');inspector.setAttribute('aria-live','polite');
  const hint=element('p','اسحب للدوران · إصبعان للتحريك والتقريب · الأسهم للدوران · +/− للتقريب. الكاميرا حرة وليست إثباتًا لقابلية المشي.',shell,'av-help');
  const disclosure=element('details',null,shell,'av-evidence');element('summary','النسخة وحدود العرض',disclosure);
  element('p','الهندسة والأبعاد من الملف المعتمد. أرضية السياق والإضاءة عرض فقط. الخامات الظاهرة لا تؤكد تشطيبًا هندسيًا. القص يخفي أجزاء للعرض ولا يعدّل النسخة.',disclosure);
  const evidence=element('output','',disclosure);evidence.dir='ltr';
  const controls=new OrbitControls(camera,canvas);controls.target.copy(center);controls.minDistance=.05;controls.maxDistance=extent*8;controls.enableDamping=false;controls.maxPolarAngle=Math.PI*.98;
  let selectionBox=null,samples=[],measuredMs=null,autoAdjusted=false;
  const telemetry={revisionId,modelHash:marker.model_hash,meshCount:meshes.length,triangleCount:triangles,quality:quality.name,renderCalls:0,activeAnimation:false,frameIntervalsMs:[]};
  container.acsViewer=telemetry;container.dataset.revision=revisionId;
  const info=()=>{evidence.textContent=`revision=${revisionId}\nmodel=${marker.model_hash}\nmeshes=${meshes.length}; triangles=${triangles}; quality=${quality.name}\nrender CPU submission (ms)=${measuredMs===null?'not measured':measuredMs.toFixed(2)}; device/browser=${navigator.userAgent}\nviewport=${stage.clientWidth}x${stage.clientHeight}; DPR=${renderer.getPixelRatio()}`;};
  function render(){
    if(disposed||lost||document.hidden||!current()||!container.isConnected||!stage.clientWidth||!stage.clientHeight)return;
    const start=performance.now();renderer.render(scene,camera);const ms=performance.now()-start;telemetry.renderCalls++;
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
    if(transition.previousFrame&&telemetry.frameIntervalsMs.length<600)telemetry.frameIntervalsMs.push(now-transition.previousFrame);transition.previousFrame=now;
    const t=Math.min(1,(now-transition.start)/450),ease=t*t*(3-2*t);
    camera.position.lerpVectors(transition.fromPosition,transition.position,ease);controls.target.lerpVectors(transition.fromTarget,transition.target,ease);controls.update();render();
    if(t<1)frame=requestAnimationFrame(animate);else stopMotion();
  }
  function move(position,target,smooth=true){
    stopMotion();if(!smooth||globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches){camera.position.copy(position);controls.target.copy(target);controls.update();render();return;}
    transition={start:performance.now(),fromPosition:camera.position.clone(),fromTarget:controls.target.clone(),position,target};telemetry.activeAnimation=true;frame=requestAnimationFrame(animate);
  }
  function chosenBounds(){return floors.value==='all'?bounds:levels.get(Number(floors.value))||bounds;}
  function chosenRoom(){
    if(selected){const identity=selected.userData.acsViewerIdentity;const match=roomBounds.get(identity.level+'|'+identity.room);if(match)return match;}
    return [...roomBounds.values()].filter(row=>floors.value==='all'||row.identity.level===Number(floors.value)).sort((a,b)=>{const x=a.box.getSize(new THREE.Vector3()),y=b.box.getSize(new THREE.Vector3());return y.x*y.z-x.x*x.z;})[0];
  }
  function setVisibility(){
    const floor=floors.value==='all'?null:Number(floors.value);
    for(const mesh of meshes){const id=mesh.userData.acsViewerIdentity;mesh.visible=floor===null||id.level===null||id.level===floor;}
    renderer.clippingPlanes=currentPreset==='cutaway'?[new THREE.Plane(new THREE.Vector3(0,-1,0),chosenBounds().min.y+Math.min(1.5,chosenBounds().getSize(new THREE.Vector3()).y*.65))]:[];
    if(selectionBox)selectionBox.visible=selected?.visible!==false;
  }
  function preset(name,smooth=true){
    currentPreset=name;setVisibility();for(const [key,button]of Object.entries(buttons))button.setAttribute('aria-pressed',String(key===name));
    const box=chosenBounds(),c=box.getCenter(new THREE.Vector3()),s=box.getSize(new THREE.Vector3()),e=Math.max(s.x,s.y,s.z,1);
    let target=c.clone(),position=c.clone().add(new THREE.Vector3(e*.95,e*.72,e*.95));
    if(name==='aerial'||name==='cutaway')position=c.clone().add(new THREE.Vector3(e*.02,e*1.6,e*.02));
    if(name==='street'){position.set(c.x+e*.75,box.min.y+1.65,box.max.z+e*.7);target.set(c.x,box.min.y+Math.min(2,s.y*.4),c.z);}
    if(name==='interior'){
      const room=chosenRoom();if(!room){inspector.textContent='لم يُحدّد الملف فراغًا صالحًا لكاميرا داخلية. اختر عنصرًا أو استخدم القص.';return;}
      const r=room.box,rs=r.getSize(new THREE.Vector3());target=r.getCenter(new THREE.Vector3());target.y=r.min.y+Math.min(1.6,Math.max(.2,rs.y*.6));
      position=target.clone();position.x=r.min.x+rs.x*.24;position.z=r.min.z+rs.z*.24;target.x=r.max.x-rs.x*.2;target.z=r.max.z-rs.z*.2;
      inspector.textContent='كاميرا داخل '+room.identity.room+' · حركة حرة؛ اتصال الدرج والممرات غير متحقق هنا.';
    }
    if(name==='detail'){
      const object=selected||meshes.find(mesh=>mesh.visible&&['DOOR','WINDOW','FURN'].includes(mesh.userData.acsViewerIdentity.kind))||meshes.find(mesh=>mesh.visible);
      if(object){select(object);const detail=new THREE.Box3().setFromObject(object);target=detail.getCenter(new THREE.Vector3());const d=Math.max(detail.getSize(new THREE.Vector3()).length(),.6);position=target.clone().add(new THREE.Vector3(d*.8,d*.5,d));}
    }
    move(position,target,smooth);
  }
  function select(object){
    if(selectionBox){scene.remove(selectionBox);selectionBox.geometry.dispose();selectionBox.material.dispose();selectionBox=null;}
    selected=object;if(!object){inspector.textContent='اختر عنصرًا لعرض هويته ودوره.';render();return;}
    selectionBox=new THREE.BoxHelper(object,0x078bba);selectionBox.material.depthTest=false;selectionBox.renderOrder=10;scene.add(selectionBox);
    const identity=object.userData.acsViewerIdentity;
    inspector.replaceChildren();const source=options.projections?.find(p=>p.level_index===identity.level)?.primitives?.find(p=>p.source?.room_id===identity.room);
    element('strong',(KIND_LABELS[identity.kind]||'عنصر')+' · '+(source?.label||identity.room||'الموقع'),inspector);
    if(source?.source_id)element('bdi','الفراغ المصدر: '+source.source_id,inspector);
    element('span',identity.level===null?'لا يحمل معرّف دور':identity.level===0?'الدور الأرضي':'الدور '+identity.level,inspector);
    element('bdi',identity.name,inspector);element('small','معرّف ملف العرض · النسخة '+revisionId,inspector);render();
  }
  const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=null;
  const pointerDown=event=>{down={x:event.clientX,y:event.clientY};stopMotion();};
  const pointerUp=event=>{if(!down||Math.hypot(event.clientX-down.x,event.clientY-down.y)>5)return;const rect=canvas.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(meshes.filter(mesh=>mesh.visible),false).find(item=>renderer.clippingPlanes.every(plane=>plane.distanceToPoint(item.point)>=0));select(hit?.object||null);};
  const keydown=event=>{
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Home'].includes(event.key))return;event.preventDefault();stopMotion();
    if(event.key==='Home'){preset('exterior');return;}
    const offset=camera.position.clone().sub(controls.target),spherical=new THREE.Spherical().setFromVector3(offset);
    if(event.key==='ArrowLeft')spherical.theta+=.12;if(event.key==='ArrowRight')spherical.theta-=.12;
    if(event.key==='ArrowUp')spherical.phi=Math.max(.03,spherical.phi-.1);if(event.key==='ArrowDown')spherical.phi=Math.min(Math.PI-.03,spherical.phi+.1);
    if(event.key==='+'||event.key==='=')spherical.radius=Math.max(.05,spherical.radius*.85);if(event.key==='-')spherical.radius=Math.min(extent*8,spherical.radius/ .85);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));controls.update();render();
  };
  const resize=()=>{if(disposed||lost)return;const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);render();};
  const visibility=()=>{if(document.hidden)stopMotion();else resize();};
  function applyQuality(low){quality=chooseQuality(low?46:0);telemetry.quality=quality.name;renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,quality.pixelRatio));sun.shadow.mapSize.set(quality.shadow,quality.shadow);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}qualityButton.textContent='الجودة: '+quality.name;resize();}
  const observer=new ResizeObserver(resize);controls.addEventListener('change',render);
  canvas.addEventListener('pointerdown',pointerDown);canvas.addEventListener('pointerup',pointerUp);canvas.addEventListener('keydown',keydown);document.addEventListener('visibilitychange',visibility);
  for(const [name,button]of Object.entries(buttons))button.addEventListener('click',()=>preset(name));
  floors.addEventListener('change',()=>{select(null);preset(currentPreset);});reset.addEventListener('click',()=>{floors.value='all';select(null);preset('exterior');});qualityButton.addEventListener('click',()=>applyQuality(quality.pixelRatio>1));
  function dispose(){
    if(disposed)return;disposed=true;stopMotion();observer.disconnect();controls.dispose();document.removeEventListener('visibilitychange',visibility);
    canvas.removeEventListener('pointerdown',pointerDown);canvas.removeEventListener('pointerup',pointerUp);canvas.removeEventListener('keydown',keydown);canvas.removeEventListener('webglcontextlost',contextLost);canvas.removeEventListener('webglcontextrestored',contextRestored);
    releaseObject(scene);environment.dispose();sun.shadow.map?.dispose();renderer.renderLists.dispose();renderer.dispose();renderer.forceContextLoss();shell.remove();if(container.acsViewer===telemetry)delete container.acsViewer;
  }
  const contextLost=event=>{event.preventDefault();lost=true;stopMotion();dispose();options.onFailure?.('فُقد سياق الرسوم. المخطط ثنائي الأبعاد متاح؛ استخدم إعادة محاولة 3D لاستعادة العرض.');};
  const contextRestored=()=>{lost=false;resize();};canvas.addEventListener('webglcontextlost',contextLost);canvas.addEventListener('webglcontextrestored',contextRestored);
  if(!current()){dispose();return()=>{};}
  container.replaceChildren(shell);observer.observe(stage);preset('exterior',false);resize();
  // This is telemetry, not an FPS/GPU-completion benchmark. First software frames
  // can be slow; the user can choose economy without dropping canonical meshes.
  telemetry.inspect=()=>({...telemetry,inspect:undefined,camera:camera.position.toArray(),target:controls.target.toArray(),visibleMeshCount:meshes.filter(mesh=>mesh.visible).length,view:currentPreset});
  return dispose;
}
