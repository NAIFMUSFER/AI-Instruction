import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {understand,generate} from '../shared/model.js';
import {createRenderScene} from '../shared/render-scene.js';
import {visualExportDescriptor,inspectLocalGLB,VISUAL_EXPORT_LIMIT} from '../src/material-downloads.js';
const model=generate(understand(readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8')));
const scene=createRenderScene(model,'visual-test-revision');
function envelope(doc={asset:{version:'2.0'},meshes:[{}]}) {
    const raw=new TextEncoder().encode(JSON.stringify(doc)),n=Math.ceil(raw.length/4)*4,buffer=new ArrayBuffer(20+n),v=new DataView(buffer);
    v.setUint32(0,0x46546c67,true);v.setUint32(4,2,true);v.setUint32(8,buffer.byteLength,true);v.setUint32(12,n,true);v.setUint32(16,0x4e4f534a,true);
    new Uint8Array(buffer,20).fill(32);new Uint8Array(buffer,20,raw.length).set(raw);return buffer;
}
test('local descriptor binds exact model revision and full roof without exposing private fields',()=>{
    const s=structuredClone(scene);s.source.prompt='PRIVATE_MARKER';s.comments=['PRIVATE_MARKER'];const before=JSON.stringify(s);
    const d=visualExportDescriptor(s);assert.equal(d.modelId,model.id);assert.equal(d.revisionId,'visual-test-revision');assert.equal(d.roof,'included');assert.equal(d.units,'m');assert.equal(d.objectCount,s.objects.length);
    assert.ok(!JSON.stringify(d).includes('PRIVATE_MARKER'));assert.equal(JSON.stringify(s),before);
});
test('local export rejects wrong schemas empty sources and unsupported settings',()=>{
    for(const change of [s=>s.schema='other',s=>s.units='cm',s=>s.source.revisionId='',s=>s.settings.finish='url',s=>s.settings.furniture='true']) {const s=structuredClone(scene);change(s);assert.throws(()=>visualExportDescriptor(s));}
});
test('local export refuses empty excessive repeated and invalid geometry before allocating meshes',()=>{
    for(const objects of [[],Array(VISUAL_EXPORT_LIMIT+1).fill(scene.objects[0]),[scene.objects[0],scene.objects[0]],[{...scene.objects[0],size:[1,0,1]}],[{...scene.objects[0],min:[NaN,1,1]}]])assert.throws(()=>visualExportDescriptor({...scene,objects}));
});
test('binary envelope guard accepts only the self-contained v2 mesh envelope (not full glTF validation)',()=>{
    const d=inspectLocalGLB(envelope());assert.equal(d.asset.version,'2.0');
    for(const change of [v=>v.setUint32(0,1,true),v=>v.setUint32(4,1,true),v=>v.setUint32(8,1,true),v=>v.setUint32(12,0xffffffff,true),v=>v.setUint32(16,0,true)]){const b=envelope();change(new DataView(b));assert.throws(()=>inspectLocalGLB(b));}
    assert.throws(()=>inspectLocalGLB(new ArrayBuffer(4)));assert.throws(()=>inspectLocalGLB('not binary'));
});
test('binary envelope guard rejects external resources and unsupported required extensions',()=>{
    for(const extra of [{buffers:[{uri:'https://example.invalid/payload'}]},{images:[{uri:'file:///private'}]},{extensionsRequired:['UNKNOWN']},{meshes:[]}])assert.throws(()=>inspectLocalGLB(envelope({asset:{version:'2.0'},meshes:[{}],...extra})));
});
test('finish and furniture options change only export presentation descriptors',()=>{
    const before=JSON.stringify(model);for(const finish of ['warm','white','slate'])for(const furniture of [false,true]){const s=createRenderScene(model,'rev',{finish,furniture});const d=visualExportDescriptor(s);assert.equal(d.finish,finish);assert.equal(d.furniture,furniture);assert.equal(d.modelId,model.id);}assert.equal(JSON.stringify(model),before);
});
