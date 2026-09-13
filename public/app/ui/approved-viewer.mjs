import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
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

export async function showApprovedGLTF(container, bytes, revisionId) {
  const buffer=embeddedGLB(bytes,revisionId);
  const gltf=await new GLTFLoader().parseAsync(buffer,'');
  const scene=new THREE.Scene();scene.background=new THREE.Color('#101d2c');scene.add(gltf.scene);
  const bounds=new THREE.Box3().setFromObject(gltf.scene);
  if(bounds.isEmpty())throw new Error('لم يتضمن الملف عناصر قابلة للعرض.');
  const center=bounds.getCenter(new THREE.Vector3()), size=bounds.getSize(new THREE.Vector3()), extent=Math.max(size.x,size.y,size.z,1);
  const camera=new THREE.PerspectiveCamera(45,1,Math.max(.01,extent/10000),extent*30);
  camera.position.copy(center).add(new THREE.Vector3(extent,extent*.8,extent));
  scene.add(new THREE.HemisphereLight(0xe4f3ff,0x34424b,2));
  const sun=new THREE.DirectionalLight(0xffffff,2.5);sun.position.copy(center).add(new THREE.Vector3(extent,extent*2,extent));scene.add(sun);
  let renderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true});}
  catch(e){throw new Error('العرض ثلاثي الأبعاد غير متاح في هذا المتصفح. يمكنك متابعة المخطط ثنائي الأبعاد والحفظ والتصدير.');}
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-label','النموذج ثلاثي الأبعاد للنسخة المعتمدة');container.replaceChildren(renderer.domElement);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(center);controls.minDistance=extent*.05;controls.maxDistance=extent*8;controls.update();
  const render=()=>renderer.render(scene,camera);
  const resize=()=>{const w=container.clientWidth,h=container.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);render();};
  const observer=new ResizeObserver(resize);observer.observe(container);controls.addEventListener('change',render);resize();
  return ()=>{observer.disconnect();controls.dispose();gltf.scene.traverse(o=>{o.geometry?.dispose();if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.dispose());});renderer.dispose();renderer.forceContextLoss();container.replaceChildren();};
}
