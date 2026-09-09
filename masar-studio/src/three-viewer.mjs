/** Optional PBR viewer. Bundled/self-hosted; does not change the canonical model. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { fitPerspectiveBounds, visualLevelIds, visibleInView, visibleForPicking } from '../shared/view-navigation.js';
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
    let viewLevel=null,viewPreset='iso',cutawayEnabled=false,autoFit=true,programmatic=false;
    const draw=()=>{if(!disposed)renderer.render(scene,camera);};
    const resize=()=>{if(disposed)return;const r=canvas.getBoundingClientRect();if(r.width<1||r.height<1)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();if(root&&autoFit)fitView();else draw();};
    const observer=new ResizeObserver(resize);observer.observe(canvas);controls.addEventListener('change',draw);
    controls.addEventListener('start',()=>{if(!programmatic){autoFit=false;canvas.dataset.viewPreset='free';}});
    function visibleBounds() {
        const box=new THREE.Box3();root?.updateMatrixWorld(true);
        root?.traverseVisible(o=>{if(o.isMesh){o.geometry.computeBoundingBox();box.union(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld));}});
        return box;
    }
    function fitView() {
        if(!root||disposed)return;
        const bounds=visibleBounds();if(bounds.isEmpty())throw Error('لا توجد عناصر ظاهرة لعرضها.');
        const fitted=fitPerspectiveBounds({min:bounds.min.toArray(),max:bounds.max.toArray()},viewPreset,camera.aspect,camera.fov);
        programmatic=true;
        try {
            controls.target.fromArray(fitted.target);camera.position.fromArray(fitted.position);
            camera.near=fitted.near;camera.far=fitted.far;camera.updateProjectionMatrix();
            controls.update();controls.saveState();
        } finally {programmatic=false;}
        canvas.dataset.viewPreset=viewPreset;draw();
    }
    function applyVisibility() {
        root?.traverse(o=>{if(o.isMesh)o.visible=visibleInView(o.userData,{levelId:viewLevel,cutaway:cutawayEnabled});});
        const ids=[];root?.traverseVisible(o=>{if(o.isMesh)ids.push(o.userData.objectId||o.name);});
        canvas.dataset.viewLevel=viewLevel||'all';canvas.dataset.visibleObjects=String(ids.length);
        canvas.dataset.cutaway=String(cutawayEnabled);
    }
    function setView({levelId=viewLevel,preset=viewPreset}={}) {
        if(disposed||!root)throw Error('أنشئ المعاينة بالخامات أولًا.');
        if(levelId!==null&&(!currentSpec||!visualLevelIds(currentSpec).includes(levelId)))throw Error('الدور غير موجود في المعاينة.');
        // Validate the preset before touching visibility/camera state.
        fitPerspectiveBounds({min:[0,0,0],max:[1,1,1]},preset,camera.aspect,camera.fov);
        viewLevel=levelId;viewPreset=preset;autoFit=true;highlight(null);applyVisibility();fitView();
    }
    const cleanup=()=>{if(!root)return;const materials=new Set(),textures=new Set();root.traverse(o=>{o.geometry?.dispose();const original=originals.get(o)||o.material;for(const m of (Array.isArray(original)?original:[original])){if(m&&m!==pickedMaterial)materials.add(m);}});for(const m of materials){for(const v of Object.values(m))if(v?.isTexture)textures.add(v);m.dispose();}for(const t of textures)t.dispose();scene.remove(root);root=null;originals.clear();};
    function install(group) {
        cleanup();root=group;scene.add(group);
        const bounds=new THREE.Box3().setFromObject(group),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),radius=size.length();
        // Fit shadow precision to this model, not a fixed 200-metre-wide map.
        const span=Math.max(radius*.6,5);sun.position.copy(center).add(new THREE.Vector3(.5,1,.4).normalize().multiplyScalar(radius*1.5));sun.target.position.copy(center);Object.assign(sun.shadow.camera,{left:-span,right:span,top:span,bottom:-span,near:.1,far:Math.max(radius*4,50)});sun.shadow.camera.updateProjectionMatrix();
        viewLevel=null;viewPreset='iso';cutawayEnabled=false;autoFit=true;selection=null;
        root.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;originals.set(o,o.material);}});
        canvas.dataset.ready='true';canvas.dataset.renderer='three-pbr';canvas.dataset.objects=String(originals.size);applyVisibility();resize();
    }
    const keyDown=e=>{if(e.key==='Escape'){highlight(null);onSelect(null);}if(e.key==='Home'&&root){e.preventDefault();autoFit=true;fitView();}};
    const raycaster=new THREE.Raycaster(),ndc=new THREE.Vector2();let down=null;
    const onDown=e=>{down=[e.clientX,e.clientY];};
    const onUp=e=>{const start=down;down=null;if(!start||Math.hypot(e.clientX-start[0],e.clientY-start[1])>5)return;const r=canvas.getBoundingClientRect();ndc.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(ndc,camera);for(const hit of raycaster.intersectObjects(root?[root]:[],true)){if(!visibleForPicking(hit.object))continue;const d=hit.object.userData;const id=d.roomId || (Array.isArray(d.roomIds)&&d.roomIds.length===1?d.roomIds[0]:null);if(id){highlight(id);onSelect(id,d.elementId);break;}}};
    const pickedMaterial=new THREE.MeshStandardMaterial({color:'#74b49b',roughness:.65});
    function highlight(roomId){selection=roomId;root?.traverse(o=>{if(o.isMesh)o.material=roomId&&(o.userData.roomId===roomId||o.userData.roomIds?.includes(roomId))?pickedMaterial:originals.get(o)||o.material;});draw();}
    const onCancel=()=>{down=null;};
    canvas.addEventListener('pointercancel',onCancel);
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
            const footer=height===480?60:84;
            const floorLabel=viewLevel===null?'ALL FLOORS':'FLOOR '+(visualLevelIds(currentSpec).indexOf(viewLevel)+1);
            try {
                root.traverse(o=>{if(o.isMesh){selectedMaterials.set(o,o.material);o.material=originals.get(o)||o.material;}});
                renderer.setPixelRatio(1);renderer.setSize(width,height-footer,false);camera.aspect=width/(height-footer);camera.updateProjectionMatrix();renderer.render(scene,camera);
                // Copy pixels before WebGL clears the buffer, without preserveDrawingBuffer.
                ctx.drawImage(canvas,0,0,width,height-footer);
                ctx.fillStyle='#ffffff';ctx.fillRect(0,height-footer,width,footer);ctx.fillStyle='#233f35';
                ctx.font=`${width===640?11:17}px sans-serif`;ctx.fillText('MASAR | CONCEPT PREVIEW - NOT A BLENDER RENDER',12,height-footer+18);
                ctx.font=`${width===640?10:14}px monospace`;ctx.fillText('View: '+floorLabel+' | Roof/ceilings '+(cutawayEnabled?'hidden':'shown'),12,height-footer+(width===640?34:44));
                ctx.fillText('Revision: '+revisionId,12,height-10);
            } finally {
                for(const [mesh,material] of selectedMaterials)mesh.material=material;
                renderer.setPixelRatio(oldRatio);renderer.setSize(oldSize.x,oldSize.y,false);camera.aspect=oldAspect;camera.updateProjectionMatrix();draw();
            }
            return new Promise((resolve,reject)=>{
                const timer=setTimeout(()=>reject(Error('انتهت مهلة تجهيز الصورة؛ جرّب دقة تجريبية.')),10000);
                output.toBlob(blob=>{clearTimeout(timer);if(blob)resolve(blob);else reject(Error('تعذر ترميز الصورة.'));},'image/png');
            });
        },
        // Presentation state never changes currentSpec, model geometry or complete GLB.
        setView,
        viewState(){const ids=[];root?.traverseVisible(o=>{if(o.isMesh)ids.push(o.userData.objectId||o.name);});return {levelId:viewLevel,preset:canvas.dataset.viewPreset||viewPreset,cutaway:cutawayEnabled,visibleObjectIds:ids};},
        select:highlight,
        cutaway(value){cutawayEnabled=!!value;applyVisibility();if(autoFit)fitView();else draw();},
        dispose(){disposed=true;observer.disconnect();controls.dispose();canvas.removeEventListener('pointercancel',onCancel);canvas.removeEventListener('pointerdown',onDown);canvas.removeEventListener('pointerup',onUp);canvas.removeEventListener('keydown',keyDown);cleanup();pickedMaterial.dispose();renderer.dispose();renderer.forceContextLoss();}
    };
}
