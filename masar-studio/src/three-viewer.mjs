/** Optional PBR viewer. Bundled/self-hosted; does not change the canonical model. */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
export function createViewer(canvas, onSelect=()=>{}) {
    const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
    renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,1.5));
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
    renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    const scene=new THREE.Scene();scene.background=new THREE.Color('#e4e7e8');
    const camera=new THREE.PerspectiveCamera(45,1,.05,3000), controls=new OrbitControls(camera,canvas);
    const hemisphere=new THREE.HemisphereLight('#ecf4ff','#8c806b',2.3);scene.add(hemisphere);
    const sun=new THREE.DirectionalLight('#fff4df',3);sun.position.set(20,35,15);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-100;sun.shadow.camera.right=100;sun.shadow.camera.top=100;sun.shadow.camera.bottom=-100;sun.shadow.camera.far=400;scene.add(sun);
    let root=null,disposed=false,selection=null,originals=new Map();
    const draw=()=>{if(!disposed)renderer.render(scene,camera);};
    const resize=()=>{if(disposed)return;const r=canvas.getBoundingClientRect();if(r.width<1||r.height<1)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();draw();};
    const observer=new ResizeObserver(resize);observer.observe(canvas);controls.addEventListener('change',draw);
    const cleanup=()=>{if(!root)return;const materials=new Set(),textures=new Set();root.traverse(o=>{o.geometry?.dispose();const original=originals.get(o)||o.material;for(const m of (Array.isArray(original)?original:[original])){if(m&&m!==pickedMaterial)materials.add(m);}});for(const m of materials){for(const v of Object.values(m))if(v?.isTexture)textures.add(v);m.dispose();}for(const t of textures)t.dispose();scene.remove(root);root=null;originals.clear();};
    function install(group) {
        cleanup();root=group;scene.add(group);
        const bounds=new THREE.Box3().setFromObject(group),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),radius=size.length();
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
            install(gltf.scene);canvas.dataset.source='blender-glb';
        },
        select:highlight,
        cutaway(value){root?.traverse(o=>{if(['roof','ceiling'].includes(o.userData.category))o.visible=!value;});draw();},
        dispose(){disposed=true;observer.disconnect();controls.dispose();canvas.removeEventListener('pointerdown',onDown);canvas.removeEventListener('pointerup',onUp);canvas.removeEventListener('keydown',keyDown);cleanup();pickedMaterial.dispose();renderer.dispose();renderer.forceContextLoss();}
    };
}
