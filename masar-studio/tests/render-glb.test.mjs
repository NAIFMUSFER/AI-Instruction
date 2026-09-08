import test from 'node:test';import assert from 'node:assert/strict';
import {verifyRenderGLB} from '../shared/render-glb.js';
const scene={objects:[{id:'room-floor',elementId:'room-1',min:[2,3,4],size:[5,6,7]}]};
function sample(edit=()=>{}){
 const binary=Buffer.alloc(96);let i=0;for(const x of [2,7])for(const y of [4,11])for(const z of [-9,-3]){for(const n of [x,y,z]){binary.writeFloatLE(n,i);i+=4;}}
 const doc={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0,extras:{objectId:'room-floor',elementId:'room-1'}}],meshes:[{primitives:[{attributes:{POSITION:0}}]}],accessors:[{bufferView:0,componentType:5126,count:8,type:'VEC3'}],bufferViews:[{buffer:0,byteOffset:0,byteLength:96}],buffers:[{byteLength:96}]};edit(doc,binary);
 const json=Buffer.from(JSON.stringify(doc)),padding=(4-json.length%4)%4,j=Buffer.concat([json,Buffer.alloc(padding,32)]),h=Buffer.alloc(20),b=Buffer.alloc(8);h.write('glTF');h.writeUInt32LE(2,4);h.writeUInt32LE(28+j.length+binary.length,8);h.writeUInt32LE(j.length,12);h.writeUInt32LE(0x4e4f534a,16);b.writeUInt32LE(binary.length);b.writeUInt32LE(0x004e4942,4);return Buffer.concat([h,j,b,binary]);
}
test('GLB verifier decodes actual +Y-up vertex bounds independently of manifest',()=>assert.deepEqual(verifyRenderGLB(sample(),scene),{objects:1,vertices:8,maximumErrorM:0}));
for(const [name,edit] of [
 ['changed geometry',(_,b)=>b.writeFloatLE(3,0)],
 ['missing room mapping',d=>d.nodes[0].extras.elementId='wrong'],
 ['duplicated objects',d=>{d.nodes.push({...d.nodes[0]});d.scenes[0].nodes.push(1);} ],
 ['hierarchy cycle',d=>d.nodes[0].children=[0]],
 ['external buffer URL',d=>d.buffers[0].uri='https://other.example/private'],
 ['morphed mesh',d=>d.meshes[0].primitives[0].targets=[{}]],
 ['out of buffer accessor',d=>d.accessors[0].count=10000],
 ['non-finite vertex',(_,b)=>b.writeFloatLE(Infinity,0)],
 ['unexpected world transform',d=>d.nodes[0].translation=[1,0,0]],
 ['empty geometry',d=>d.scenes[0].nodes=[]],
])test('GLB rejects '+name,()=>assert.throws(()=>verifyRenderGLB(sample(edit),scene)));
