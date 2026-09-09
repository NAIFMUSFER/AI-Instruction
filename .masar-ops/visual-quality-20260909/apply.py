from pathlib import Path
import subprocess
root=Path('masar-studio')
expected={'shared/render-scene.js':'d3f6b75430e5095a81f4f847d508caaade6c2967','src/three-viewer.mjs':'42d7db96c0f96339cec1e7f0447886c0027caa3b'}
for name,blob in expected.items():
    got=subprocess.check_output(['git','hash-object',str(root/name)],text=True).strip()
    assert got==blob,(name,got,blob)
p=root/'shared/render-scene.js';s=p.read_text()
old="""        exterior: { color:finish.wall, roughness:.78, metallic:0 }, interior: {color:finish.interior,roughness:.82,metallic:0},
        floor: {color:finish.floor,roughness:.55,metallic:0}, frame: {color:finish.frame,roughness:.32,metallic:.65},
        glass: {color:'#b0d0d5',roughness:.12,metallic:0,alpha:.28}, wood: {color:'#98724d',roughness:.48,metallic:0},
        fabric: {color:'#e2d7c7',roughness:.92,metallic:0}, site: {color:'#82946f',roughness:1,metallic:0},
        paving: {color:'#c6c2b7',roughness:.9,metallic:0}, water:{color:'#478e9f',roughness:.18,metallic:.1}
"""
new="""        exterior: { color:finish.wall, roughness:.7, metallic:0 }, interior: {color:finish.interior,roughness:.8,metallic:0},
        floor: {color:finish.floor,roughness:.42,metallic:0,clearcoat:.08}, frame: {color:finish.frame,roughness:.26,metallic:.72},
        glass: {color:'#c4e2e6',roughness:.07,metallic:0,alpha:.38,transmission:.58,ior:1.45,clearcoat:.35,thickness:.015},
        wood: {color:'#98724d',roughness:.4,metallic:0,clearcoat:.12}, fabric: {color:'#e2d7c7',roughness:.95,metallic:0},
        site: {color:'#7f966d',roughness:1,metallic:0}, paving: {color:'#c6c2b7',roughness:.82,metallic:0},
        coping: {color:'#d9d4c9',roughness:.72,metallic:0}, water:{color:'#4b9bad',roughness:.08,metallic:0,alpha:.88,transmission:.12,ior:1.333,clearcoat:1,clearcoatRoughness:.06,thickness:.08}
"""
assert s.count(old)==1;s=s.replace(old,new)
old="""    for(const f of graph.elements.siteFeatures) box(`presentation:${f.id}`,[f.x,f.y,-.155],[f.w,f.d,.035],f.type==='pool'?'water':'paving',{elementId:f.id,category:'site-feature',displayOnly:true});
"""
new="""    for(const f of graph.elements.siteFeatures) {
        const meta={elementId:f.id,category:'site-feature',displayOnly:true};
        if(f.type==='pool') {
            const edge=Math.min(.18,f.w*.12,f.d*.12);
            box(`presentation:${f.id}:water`,[f.x+edge,f.y+edge,-.152],[Math.max(.05,f.w-edge*2),Math.max(.05,f.d-edge*2),.028],'water',{...meta,category:'pool-water'});
            box(`presentation:${f.id}:coping:n`,[f.x,f.y+f.d-edge,-.153],[f.w,edge,.03],'coping',{...meta,category:'pool-coping'});
            box(`presentation:${f.id}:coping:s`,[f.x,f.y,-.153],[f.w,edge,.03],'coping',{...meta,category:'pool-coping'});
            if(f.d>edge*2){
                box(`presentation:${f.id}:coping:e`,[f.x+f.w-edge,f.y+edge,-.153],[edge,f.d-edge*2,.03],'coping',{...meta,category:'pool-coping'});
                box(`presentation:${f.id}:coping:w`,[f.x,f.y+edge,-.153],[edge,f.d-edge*2,.03],'coping',{...meta,category:'pool-coping'});
            }
        } else box(`presentation:${f.id}`,[f.x,f.y,-.155],[f.w,f.d,.035],'paving',meta);
    }
"""
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
p=root/'src/three-viewer.mjs';s=p.read_text()
old="""    const hemisphere=new THREE.HemisphereLight('#ecf4ff','#8c806b',2.3);scene.add(hemisphere);
    const sun=new THREE.DirectionalLight('#fff4df',3);sun.position.set(20,35,15);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-100;sun.shadow.camera.right=100;sun.shadow.camera.top=100;sun.shadow.camera.bottom=-100;sun.shadow.camera.far=400;sun.shadow.bias=-.0003;sun.shadow.normalBias=.02;scene.add(sun,sun.target);
"""
new="""    const hemisphere=new THREE.HemisphereLight('#edf5ff','#7f725f',2.05);scene.add(hemisphere);
    const sun=new THREE.DirectionalLight('#fff1d7',3.15);sun.position.set(20,35,15);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-100;sun.shadow.camera.right=100;sun.shadow.camera.top=100;sun.shadow.camera.bottom=-100;sun.shadow.camera.far=400;sun.shadow.bias=-.0003;sun.shadow.normalBias=.02;scene.add(sun,sun.target);
    const fill=new THREE.DirectionalLight('#dce9ff',.7);fill.position.set(-18,14,-22);scene.add(fill);
    function makeMaterial(m){
        const base={color:m.color,roughness:m.roughness,metalness:m.metallic,transparent:m.alpha!==undefined||!!m.transmission,opacity:m.alpha??1,depthWrite:m.alpha===undefined&&!m.transmission};
        if(m.transmission!==undefined||m.ior!==undefined||m.clearcoat!==undefined)return new THREE.MeshPhysicalMaterial({...base,transmission:m.transmission??0,ior:m.ior??1.5,clearcoat:m.clearcoat??0,clearcoatRoughness:m.clearcoatRoughness??.15,thickness:m.thickness??.01});
        return new THREE.MeshStandardMaterial(base);
    }
"""
assert s.count(old)==1;s=s.replace(old,new)
old="""for(const o of spec.objects){const m=spec.materials[o.material],material=new THREE.MeshStandardMaterial({color:m.color,roughness:m.roughness,metalness:m.metallic,transparent:m.alpha!==undefined,opacity:m.alpha??1,depthWrite:m.alpha===undefined});const mesh="""
new="""for(const o of spec.objects){const m=spec.materials[o.material],material=makeMaterial(m);const mesh="""
assert s.count(old)==1;s=s.replace(old,new)
old="""                    const material=new THREE.MeshStandardMaterial({color:m.color,roughness:m.roughness,metalness:m.metallic,transparent:m.alpha!==undefined,opacity:m.alpha??1,depthWrite:m.alpha===undefined});
"""
new="""                    const material=makeMaterial(m);
"""
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
test=root/'tests/visual-materials.test.mjs'
test.write_text("""import test from 'node:test';
import assert from 'node:assert/strict';
import {generate,understand} from '../shared/model.js';
import {createRenderScene} from '../shared/render-scene.js';
test('presentation contract exposes physical glass and water without changing canonical geometry',()=>{
 const model=generate(understand('شاليه دور واحد على أرض 20×25 مع ثلاث غرف نوم ومسبح'));
 const before=JSON.stringify(model); const scene=createRenderScene(model,'visual-quality-test',{finish:'warm',furniture:true});
 assert.equal(JSON.stringify(model),before);
 assert.ok(scene.materials.glass.transmission>=.5); assert.equal(scene.materials.glass.ior,1.45);
 assert.equal(scene.materials.water.ior,1.333); assert.equal(scene.materials.water.clearcoat,1);
 assert.ok(scene.objects.length>0);
});
""")
print('candidate applied')
