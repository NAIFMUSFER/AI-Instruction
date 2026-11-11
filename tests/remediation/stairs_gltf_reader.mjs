// Independent consumer of Python-serialized glTF. The display engine also uses
// Three; this is an independent parser path, not a claim of a second renderer.
import fs from 'node:fs';
import {Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
globalThis.ProgressEvent ??= class ProgressEvent { constructor(type, values={}) { this.type=type;Object.assign(this,values); } };
const raw=fs.readFileSync(process.argv[2]);
const loaded=await new GLTFLoader().parseAsync(raw.toString('utf8'),'');
loaded.scene.updateMatrixWorld(true);
const meshes=[];
loaded.scene.traverse(node=>{
  if(!node.isMesh)return;
  const p=node.geometry.getAttribute('position'),index=node.geometry.getIndex();
  if(!p||!index)throw new Error('Expected indexed serialized geometry');
  const vertices=Array.from({length:p.count},(_,i)=>new Vector3().fromBufferAttribute(p,i).applyMatrix4(node.matrixWorld).toArray());
  meshes.push({name:node.name,extras:node.userData,vertices,indices:Array.from(index.array)});
});
if(!meshes.length)throw new Error('No serialized meshes decoded');
console.log(JSON.stringify({reader:'Three 0.160.0 GLTFLoader',format:'gltf',scene:loaded.scene.userData,meshes}));
