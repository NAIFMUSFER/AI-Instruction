/** Optional PBR viewer. Bundled/self-hosted; does not change the canonical model. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
export function createViewer(canvas, onSelect=()=>{}) {
    const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
    renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,1.5));
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
    renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    const scene=new THREE.Scene();scene.background=new THREE.Color('#e4e7e8');
    const camera=new THREE.PerspectiveCamera(45,1,.05,3000), controls=new OrbitControls(camera,canvas);
    const hemisphere=new THREE.HemisphereLight('#ecf4ff','#8c806b',2.3);scene.add(hemisphere);
    const sun=new THREE.DirectionalLight('#fff4df',3);sun.position.set(20,35,15);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-100;sun.shadow.camera.right=100;sun.shadow.camera.top=100;sun.shadow.camera.bottom=-100;sun.shadow.camera.far=400;sun.shadow.bias=-.0003;sun.shadow.normalBias=.02;scene.add(sun,sun.target);
    let root=null,disposed=false,selection=null,currentSpec=null,originals=new Map();
    const draw=()=>{if(!disposed)renderer.render(scene,camera);};
    const resize=()=>{if(disposed)return;const r=canvas.getBoundingClientRect();if(r.width<1||r.height<1)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();};
    const observer=new ResizeObserver(resize);observer.observe(canvas);controls.addEventListener('change',draw);
    const cleanup=()=>{if(!root)return;const materials=new Set(),textures=new Set();root.traverse(o=>{o.geometry?.dispose();const original=originals.get(o)||o.material;for(const m of (Array.isArray(original)?original:[original])){if(m&&m!==pickedMaterial)materials.add(m);}});for(const m of materials){for(const v of Object.values(m))if(v?.isTexture)textures.add(v);m.dispose();}for(const t of textures)t.dispose();scene.remove(root);root=null;originals.clear();};
    function install(group) {
        cleanup();root=group;scene.add(group);
        const bounds=new THREE.Box3().setFromObject(group),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),radius=size.length();
        // Fit shadow precision to this model, not a fixed 200-metre-wide map.
        const span=Math.max(radius*.6,5);sun.position.copy(center).add(new THREE.Vector3(.5,1,.4).normalize().multiplyScalar(radius*1.5));sun.target.position.copy(center);Object.assign(sun.shadow.camera,{left:-span,right:span,top:span,bottom:-span,near:.1,far:Math.max(radius*4,50)});sun.shadow.camera.updateProjectionMatrix();
        controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(radius*.6,radius*.52,radius*.7));camera.far=Math.max(300,radius*12);camera.updateProjectionMatrix();controls.update();controls.saveState();
        root.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;originals.set(o,o.material);}});
        canvas.dataset.ready='true';canvas.dataset.renderer='three-pbr';canvas.dataset.objects=String(originals.size);resize();
    }
    const keyDown=e=>{if(e.key==='Escape'){highlight(null);onSelect(null);}if(e.key==='Home'&&root){controls.reset();draw();}};
    const raycaster=new THREE.Raycaster(),ndc=new THREE.Vector2();let down=null;
    const onDown=e=>{down=[e.clientX,e.clientY];};
    const onUp=e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;down=null;const r=canvas.getBoundingClientRect();ndc.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(ndc,camera);for(const hit of raycaster.intersectObjects(root?[root]:[],true)){const d=hit.object.userData;const id=d.roomId || (Array.isArray(d.roomIds)&&d.roomIds.length===1?d.roomIds[0]:null);if(id){highlight(id);onSelect(id,d.elementId);break;}}};
    const pickedMaterial=new THREE.MeshStandardMaterial({color:'#74b49b',roughness:.65});
    function highlight(roomId){selection=roomId;root?.traverse(o=>{if(o.isMesh)o.material=roomId&&(o.userData.roomId===roomId||o.userData.roomIds?.includes(roomId))?pickedMaterial:originals.get(o)||o.material;});draw();}
    canvas.addEventListener('pointerdown',onDown);canvas.addEventListener('pointerup',onUp);canvas.addEventListener('keydown',keyDown);
    return {
        setScene(spec){
            if(disposed)throw Error('المعاينة مغلقة.');
            currentSpec=structuredClone(spec);
            const group=new THREE.Group();
            for(const o of spec.objects){const m=spec.materials[o.material],material=new THREE.MeshStandardMaterial({color:m.color,roughness:m.roughness,metalness:m.metallic,transparent:m.alpha!==undefined,opacity:m.alpha??1,depthWrite:m.alpha===undefined});const mesh=new THREE.Mesh(new THREE.BoxGeometry(o.size[0],o.size[2],o.size[1]),material);mesh.position.set(o.min[0]+o.size[0]/2,o.min[2]+o.size[2]/2,-o.min[1]-o.size[1]/2);mesh.userData={...o,objectId:o.id};group.add(mesh);}
            install(group);canvas.dataset.source='masar-snapshot';
        },
        async loadGLB(buffer){
            if(buffer.byteLength>24_000_000)throw Error('المجسم أكبر من الحد المسموح.');
            const view=new DataView(buffer);if(buffer.byteLength<24||view.getUint32(0,true)!==0x46546c67||view.getUint32(4,true)!==2||view.getUint32(8,true)!==buffer.byteLength)throw Error('GLB غير صالح.');
            const doc=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,view.getUint32(12,true))));
            if((doc.buffers||[]).some(b=>b.uri)||(doc.images||[]).some(i=>i.uri)||doc.extensionsRequired?.length)throw Error('يجب أن يكون GLB ذاتي المحتوى.');
            const manager=new THREE.LoadingManager();manager.setURLModifier(()=>{throw Error('لا يُسمح بتحميل ملفات خارجية للمجسم.');});
            const gltf=await new GLTFLoader(manager).parseAsync(buffer,'');
            if(disposed){gltf.scene.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});return;}
            install(gltf.scene);currentSpec=null;canvas.dataset.source='blender-glb';
        },
        async exportGLB(descriptor) {
            if(disposed||!currentSpec||!root)throw Error('أعد إنشاء معاينة المشروع قبل تصدير GLB.');
            const spec=structuredClone(currentSpec);
            if(spec.objects.length>4000)throw Error('المشهد يتجاوز حد التنزيل المحلي (4,000 عنصر).');
            if(descriptor.modelId!==spec.source.modelId||descriptor.revisionId!==spec.source.revisionId)throw Error('مرجع تصدير GLB لا يطابق المعاينة.');
            // A separate complete group excludes cutaway state and selection colour.
            const group=new THREE.Group();group.name='MASAR concept visual';group.userData={...descriptor};
            try {
                for(const o of spec.objects){
                    const m=spec.materials[o.material];
                    const material=new THREE.MeshStandardMaterial({color:m.color,roughness:m.roughness,metalness:m.metallic,transparent:m.alpha!==undefined,opacity:m.alpha??1,depthWrite:m.alpha===undefined});
                    const mesh=new THREE.Mesh(new THREE.BoxGeometry(o.size[0],o.size[2],o.size[1]),material);
                    mesh.name=o.id;mesh.position.set(o.min[0]+o.size[0]/2,o.min[2]+o.size[2]/2,-o.min[1]-o.size[1]/2);
                    const metadata={objectId:o.id};
                    for(const key of ['elementId','roomId','levelId','hostWallId','category'])if(typeof o[key]==='string')metadata[key]=o[key];
                    if(Array.isArray(o.roomIds))metadata.roomIds=o.roomIds.filter(x=>typeof x==='string');
                    if(typeof o.displayOnly==='boolean')metadata.displayOnly=o.displayOnly;
                    mesh.userData=metadata;group.add(mesh);
                }
                group.updateMatrixWorld(true);
                const buffer=await new GLTFExporter().parseAsync(group,{binary:true,onlyVisible:false,includeCustomExtensions:false});
                if(!(buffer instanceof ArrayBuffer)||buffer.byteLength>24_000_000)throw Error('حجم الملف يتجاوز الحد المدعوم.');
                return buffer;
            } finally {group.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});}
        },
        async capturePNG({width=1280,height=960,revisionId,modelId}={}) {
            if(disposed||!root||!currentSpec||renderer.getContext().isContextLost())throw Error('عارض الصورة غير جاهز.');
            if(currentSpec.source.revisionId!==revisionId||currentSpec.source.modelId!==modelId)throw Error('مرجع الصورة لا يطابق المعاينة.');
            if(![[640,480],[1280,960]].some(s=>s[0]===width&&s[1]===height))throw Error('دقة صورة غير مدعومة.');
            const output=document.createElement('canvas');output.width=width;output.height=height;
            const ctx=output.getContext('2d');if(!ctx)throw Error('تعذر إنشاء صورة على هذا الجهاز.');
            const oldSize=renderer.getSize(new THREE.Vector2()),oldRatio=renderer.getPixelRatio(),oldAspect=camera.aspect,selectedMaterials=new Map();
            const footer=height===480?44:64;
            try {
                root.traverse(o=>{if(o.isMesh){selectedMaterials.set(o,o.material);o.material=originals.get(o)||o.material;}});
                renderer.setPixelRatio(1);renderer.setSize(width,height-footer,false);camera.aspect=width/(height-footer);camera.updateProjectionMatrix();renderer.render(scene,camera);
                // Copy pixels before WebGL clears the buffer, without preserveDrawingBuffer.
                ctx.drawImage(canvas,0,0,width,height-footer);
                ctx.fillStyle='#ffffff';ctx.fillRect(0,height-footer,width,footer);ctx.fillStyle='#233f35';
                ctx.font=`${width===640?11:17}px sans-serif`;ctx.fillText('MASAR | CONCEPT PREVIEW - NOT A BLENDER RENDER',12,height-footer+18);
                ctx.font=`${width===640?10:14}px monospace`;ctx.fillText('Revision: '+revisionId,12,height-10);
            } finally {
                for(const [mesh,material] of selectedMaterials)mesh.material=material;
                renderer.setPixelRatio(oldRatio);renderer.setSize(oldSize.x,oldSize.y,false);camera.aspect=oldAspect;camera.updateProjectionMatrix();draw();
            }
            return new Promise((resolve,reject)=>{
                const timer=setTimeout(()=>reject(Error('انتهت مهلة تجهيز الصورة؛ جرّب دقة تجريبية.')),10000);
                output.toBlob(blob=>{clearTimeout(timer);if(blob)resolve(blob);else reject(Error('تعذر ترميز الصورة.'));},'image/png');
            });
        },
        // End of staged export methods; the existing selection API follows.
        select:highlight,
        cutaway(value){root?.traverse(o=>{if(['roof','ceiling'].includes(o.userData.category))o.visible=!value;});draw();},
        dispose(){disposed=true;observer.disconnect();controls.dispose();canvas.removeEventListener('pointerdown',onDown);canvas.removeEventListener('pointerup',onUp);canvas.removeEventListener('keydown',keyDown);cleanup();pickedMaterial.dispose();renderer.dispose();renderer.forceContextLoss();}
    };
}
