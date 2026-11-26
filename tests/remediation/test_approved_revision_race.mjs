import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash, webcrypto} from 'node:crypto';
// Execute the production export boundary with delayed artifact and loader replies.
const source=fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8');
const body=source.slice(source.indexOf('async function exportFile('),source.indexOf('function showViewerFallback('));
const defer=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
const revision={id:'R1',model_hash:'a'.repeat(64),content_hash:'b'.repeat(64)};
const bytes=new TextEncoder().encode('approved artifact');
const receipt={revision_id:'R1',model_hash:revision.model_hash,content_hash:revision.content_hash,
 artifact_bytes:bytes.length,artifact_sha256:createHash('sha256').update(bytes).digest('hex')};
const response={revision_id:'R1',data_base64:Buffer.from(bytes).toString('base64'),filename:'R1.gltf',mime:'model/gltf+json',receipt};
function setup(){
 const nodes=new Map(),mounted=[],downloads=[],replies=defer();let disposed=0;
 const $=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,value:'0',dataset:{},replaceChildren(){}});return nodes.get(id);};
 const context=vm.createContext({$,state:{revision_id:'R1'},packet:{revision,projections:[{level_index:0}]},revisionEpoch:1,viewerEpoch:1,activeStep:4,viewerDispose:null,api:()=>replies.promise,bytes64:s=>new Uint8Array(Buffer.from(s,'base64')),crypto:webcrypto,Uint8Array,showApprovedGLTF:async(c,b,id,options)=>{assert.equal(options.isCurrent(),true);mounted.push(id);return()=>{disposed++;};},status(){},download:(...args)=>downloads.push(args),clearViewer:()=>{context.viewerEpoch++;},showViewerFallback(){throw new Error('unexpected fallback');},JSON});
 vm.runInContext(body+';globalThis.invoke=exportFile',context);return{context,mounted,downloads,replies,get disposed(){return disposed;}};
}
for(const [name,change,display]of[
 ['late R1 after R2',c=>{c.state={revision_id:'R2'};c.revisionEpoch++;c.viewerEpoch++;},true],
 ['leaving 3D while artifact pending',c=>{c.activeStep=3;c.viewerEpoch++;},true],
 ['download after revision change',c=>{c.state={revision_id:'R2'};c.revisionEpoch++;},false],
 ['sign out while pending',c=>{c.state=null;c.revisionEpoch++;},true],
]){
 const run=setup(),work=run.context.invoke('gltf',display);change(run.context);run.replies.resolve(response);await work;
 assert.deepEqual(run.mounted,[],name);assert.deepEqual(run.downloads,[],name);console.log('PASS: '+name);
}
{
 const run=setup(),work=run.context.invoke('gltf',true);run.replies.resolve(response);await work;
 assert.deepEqual(run.mounted,['R1']);assert.equal(typeof run.context.viewerDispose,'function');console.log('PASS: current revision mounts with captured R1 identity');
}
{
 const run=setup(),loader=defer(),started=defer();let disposed=0;
 run.context.showApprovedGLTF=()=>{started.resolve();return loader.promise;};
 const work=run.context.invoke('gltf',true);run.replies.resolve(response);await started.promise;
 run.context.revisionEpoch++;run.context.state={revision_id:'R2'};loader.resolve(()=>{disposed++;});await work;
 assert.equal(disposed,1);assert.equal(run.context.viewerDispose,null);console.log('PASS: late viewer construction is disposed and never retained');
}

for(const [label,changed] of [
 ['another response revision',{...response,revision_id:'R2'}],
 ['wrong canonical model',{...response,receipt:{...receipt,model_hash:'c'.repeat(64)}}],
 ['different locked content',{...response,receipt:{...receipt,content_hash:'d'.repeat(64)}}],
 ['wrong attached bytes',{...response,data_base64:Buffer.from('changed! artifact').toString('base64')}],
 ['missing receipt',{...response,receipt:null}],
]){
 for(const display of [true,false]){
  const run=setup(),work=run.context.invoke('gltf',display);
  run.replies.resolve(changed);
  await assert.rejects(work,undefined,label+' must be refused before presentation or download');
  assert.equal(run.mounted.length,0);assert.equal(run.downloads.length,0);
 }
 console.log('PASS: approved delivery rejects '+label);
}

for(const fmt of ['svg','dxf']){
 const run=setup(),work=run.context.invoke(fmt,false);
 run.replies.resolve({...response,receipt:{...receipt,format:fmt.toUpperCase(),level_index:0}});
 await work;assert.equal(run.downloads.length,1,'one file per tap for the owner');assert.match(run.downloads[0][1],new RegExp('^مخطط'+(fmt==='dxf'?'-CAD':'')+'(?:-|\\.)'));
 const engineer=setup();engineer.context.$('cwEngineerIds').checked=true;const both=engineer.context.invoke(fmt,false);
 engineer.replies.resolve({...response,receipt:{...receipt,format:fmt.toUpperCase(),level_index:0}});await both;
 assert.equal(engineer.downloads.length,2,'the engineer view also downloads the receipt manifest');assert.match(engineer.downloads[1][1],/-manifest\.json$/);
 const wrong=setup(),pending=wrong.context.invoke(fmt,false);
 wrong.replies.resolve({...response,receipt:{...receipt,format:fmt.toUpperCase(),level_index:1}});
 await assert.rejects(pending);assert.equal(wrong.downloads.length,0);
 console.log('PASS: '+fmt.toUpperCase()+' delivery binds the requested floor and format');
}
