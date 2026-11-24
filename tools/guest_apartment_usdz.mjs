// Project the compiler's actual indexed meshes and constant PBR materials to
// Quick Look. Batching by storey and material reduces draw calls on phones.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { Box3, DoubleSide, FrontSide, Group, Mesh } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { USDZExporter } from 'three/addons/exporters/USDZExporter.js';
import { USDZLoader } from 'three/addons/loaders/USDZLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { unzipSync, strFromU8, strToU8, zipSync } from 'three/addons/libs/fflate.module.js';

globalThis.ProgressEvent??=class { constructor(type,detail){this.type=type;Object.assign(this,detail);} };
const [sourceFile, targetFile]=process.argv.slice(2);
const bytes=fs.readFileSync(sourceFile);
const isGlb=bytes.subarray(0,4).toString()==='glTF';
const raw=isGlb?bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength):bytes.toString('utf8');
const {scene,parser}=await new GLTFLoader().parseAsync(raw,'');
scene.updateMatrixWorld(true);
const byMaterialAndFloor=new Map();
const sourceBounds=new Box3();
let componentCount=0,triangleCount=0;
scene.traverse(object=>{
  if(!object.isMesh)return;
  const material=object.material;
  assert.ok(material.isMeshStandardMaterial&&!material.map,'Named apartment supports the compiler’s constant PBR materials');
  const rawNode=parser.json.nodes[parser.associations.get(object).nodes];
  const floor=rawNode.name.split('|')[1];
  const id=floor+'_'+material.id;
  if(!byMaterialAndFloor.has(id)) byMaterialAndFloor.set(id,{floor,material,geometries:[],sources:[]});
  const batch=byMaterialAndFloor.get(id);
  const geometry=object.geometry.clone().applyMatrix4(object.matrixWorld);
  sourceBounds.expandByObject(object,true);
  assert.ok(geometry.index&&geometry.index.count%3===0);
  batch.geometries.push(geometry);
  batch.sources.push({name:rawNode.name,triangles:geometry.index.count/3});
  componentCount++;triangleCount+=geometry.index.count/3;
});
const display=new Group(),groups=[];
for(const batch of byMaterialAndFloor.values()){
  const geometry=mergeGeometries(batch.geometries);
  assert.ok(geometry);
  const mesh=new Mesh(geometry,batch.material);
  display.add(mesh);groups.push({mesh,...batch});
}
display.updateMatrixWorld(true);
// The upstream exporter omits doubleSided. This compiler emits closed boxes
// with double-sided materials, which we restore on their USD meshes below.
const materials=new Set(groups.map(group=>group.material));
for(const material of materials){
  assert.equal(material.side,DoubleSide);
  material.side=FrontSide;
}
const exported=await new USDZExporter().parse(display,{quickLookCompatible:true});
const files=unzipSync(exported),usd='model.usda';
let stage=strFromU8(files[usd]);
for(const group of groups){
  const {mesh,floor,sources}=group;
  // Preserve the input component identity and face ranges after batching.
  const name='Object_'+mesh.id;
  const anchor='def Xform "'+name+'" (';
  assert.ok(stage.includes(anchor));
  const props=stage.indexOf('matrix4d xformOp:transform',stage.indexOf(anchor));
  stage=stage.slice(0,props)+'custom string acs:floor = '+JSON.stringify(floor)+'\n'+
    'custom string[] acs:componentNames = '+JSON.stringify(sources.map(s=>s.name))+'\n'+
    'custom int[] acs:componentTriangleCounts = '+JSON.stringify(sources.map(s=>s.triangles))+'\n'+stage.slice(props);
  const ref='geometries/Geometry_'+mesh.geometry.id+'.usda';
  let meshUsd=strFromU8(files[ref]).replace('defaultPrim = "Root"','defaultPrim = "Geometry"');
  meshUsd=meshUsd.replace('uniform token subdivisionScheme', 'uniform bool doubleSided = true\n\t\tuniform token subdivisionScheme');
  files[ref]=strToU8(meshUsd);
}
files[usd]=strToU8(stage);
// The USDZ profile uses stored entries with each payload 64-byte aligned.
// Fixing ZIP dates also makes releases byte-reproducible.
const zipFiles={};let offset=0;
for(const [name,data] of Object.entries(files)){
  const headerEnd=offset+30+Buffer.byteLength(name);
  let padding=(64-headerEnd%64)%64;
  if(padding&&padding<4)padding+=64;
  const options={mtime:new Date(1980,0,1,0,0,0)};
  if(padding)options.extra={12345:new Uint8Array(padding-4)};
  zipFiles[name]=[data,options];offset=headerEnd+padding+data.length;
}
const archive=zipSync(zipFiles,{level:0});
const readback=new USDZLoader().parse(archive.buffer.slice(archive.byteOffset,archive.byteOffset+archive.byteLength));
const decodedBounds=new Box3();
let decoded=0,triangles=0;
const batchesByName=new Map(groups.map(g=>['Object_'+g.mesh.id,g]));
readback.traverse(obj=>{
  if(!obj.isMesh)return;
  const group=batchesByName.get(obj.name);
  assert.ok(group,'Each decoded batch must resolve to its source group');
  decoded++;decodedBounds.expandByObject(obj,true);
  const count=(obj.geometry.index?.count??obj.geometry.attributes.position.count)/3;
  assert.equal(count,group.sources.reduce((total,s)=>total+s.triangles,0));triangles+=count;
  const projected=group.mesh.geometry;
  assert.deepEqual(Array.from(obj.geometry.index.array),Array.from(projected.index.array));
  for(const key of ['position','normal']){
    const decodedValues=obj.geometry.attributes[key].array, expected=projected.attributes[key].array;
    assert.equal(decodedValues.length,expected.length);
    assert.ok(decodedValues.every((v,i)=>Math.abs(v-expected[i])<0.00001),'USD '+key+' differs from actual glTF geometry');
  }
  assert.ok(obj.material.color.toArray().every((v,i)=>Math.abs(v-group.material.color.toArray()[i])<1e-6));
  assert.ok(Math.abs(obj.material.metalness-group.material.metalness)<1e-6);
  assert.ok(Math.abs(obj.material.roughness-group.material.roughness)<1e-6);
  // Three r160's USDZLoader does not read scalar opacity. Check the actual
  // UsdPreviewSurface input in the binding referenced by the exported stage.
  const shader=stage.split('def Material "Material_'+group.material.id+'"')[1].split('def Material')[0];
  assert.equal(Number(shader.match(/float inputs:opacity = ([\d.e+-]+)/)[1]),group.material.opacity);
});
assert.equal(decoded,groups.length);assert.equal(triangles,triangleCount);
for(const key of ['min','max'])assert.ok(decodedBounds[key].distanceTo(sourceBounds[key])<0.0001);
assert.ok(stage.includes('metersPerUnit = 1')&&stage.includes('upAxis = "Y"'));
fs.writeFileSync(targetFile,archive);
console.log(JSON.stringify({sourceComponents:componentCount,triangles,batches:decoded,bytes:archive.length,
  bounds:[decodedBounds.min.toArray(),decodedBounds.max.toArray()]}));
