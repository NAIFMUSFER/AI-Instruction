import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
// Execute the production export boundary with delayed artifact and loader replies.
const source=fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8');
const body=source.slice(source.indexOf('async function exportFile('),source.indexOf('function showViewerFallback('));
const defer=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
const response={data_base64:'',filename:'R1.gltf',mime:'model/gltf+json'};
function setup(){
 const nodes=new Map(),mounted=[],downloads=[],replies=defer();let disposed=0;
 const $=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,value:'0',dataset:{},replaceChildren(){}});return nodes.get(id);};
 const context=vm.createContext({$,state:{revision_id:'R1'},packet:{projections:[{level_index:0}]},revisionEpoch:1,viewerEpoch:1,activeStep:4,viewerDispose:null,api:()=>replies.promise,bytes64:()=>new Uint8Array(),showApprovedGLTF:async(c,b,id,options)=>{assert.equal(options.isCurrent(),true);mounted.push(id);return()=>{disposed++;};},status(){},download:(...args)=>downloads.push(args),clearViewer:()=>{context.viewerEpoch++;},showViewerFallback(){throw new Error('unexpected fallback');},JSON});
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
