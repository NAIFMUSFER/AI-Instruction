'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const APP=require('../lib/app_source.js');
const ctx={structuredClone,THREE:{Group:class{}}};vm.createContext(ctx);
vm.runInContext(APP.nodeBundle(['core/stairs.mjs','core/viewer.js','core/standards.js','core/disciplines.js','generated/pbr.js'])+`
const cdCaptured=[];addBox=(g,cx,cy,cz,w,h,d,material,tag,pick,color,rot)=>cdCaptured.push({center:[cx,cy,cz],size:[w,h,d],rot});
globalThis.contextProbe=(object,room=false)=>{cdCaptured.length=0;if(room)buildObjects({}, {id:'r',rect:[10,20,6,6],objects:[object]},'F0',0);else buildObject({},object,object.kind,0,0,0,'F0','r',0);return JSON.parse(JSON.stringify(cdCaptured));};`,ctx);
const failures=[];
for(const [w,parts]of [[2.75,4],[4.95,6],[3,5]]){
 try{assert.equal(ctx.contextProbe({kind:'railing',w,d:.06,h:1.1}).length,parts,'railing post count must use Python ties-to-even');}catch(e){failures.push(e.message);}
}
try{assert.deepEqual(Array.from(ctx.contextProbe({kind:'column',x:0,z:0,w:.45,d:.45,h:3},true)[0].center),[10,1.5,20],'explicit zero is a canonical coordinate');}catch(e){failures.push(e.message);}
assert.deepEqual(failures,[]);
const budget={structuredClone,TextEncoder};vm.createContext(budget);
vm.runInContext(APP.nodeBundle(['core/stairs.mjs','core/context-details.mjs'])+`
const cdOriginalFootprints=cdFootprints;let cdExistingCalls=0;
cdFootprints=(obj,room)=>{if(obj.id?.startsWith('blocker'))cdExistingCalls++;return cdOriginalFootprints(obj,room);};
globalThis.runBudget=model=>{cdExistingCalls=0;const result=withContextDetails(model);return {result,calls:cdExistingCalls};};
globalThis.refuseBounds=()=>{getActualBounds=()=>{throw new Error('expanded before admission');};};`,budget);
const model={wall_t:.2,wall_h:3,levels:[{index:0,template:'g'}],floors:{g:{rooms:[]}}};
for(let i=0;i<4;i++)model.floors.g.rooms.push({id:'c'+i,role:'courtyard',outdoor:true,rect:[i*10,0,6,6],walls:'none',objects:[{id:'blocker'+i,kind:'planter',x:3,z:3,y:0,w:6,d:6,h:1,rot:0,count:1,pitch:1,dir:'x'}]});
const cached=budget.runBudget(model);assert.equal(cached.calls,4,'actual JS expands each existing object once per physical level');assert.equal(cached.result[0],model);
const overloaded=structuredClone(model);overloaded.floors.g.rooms=overloaded.floors.g.rooms.slice(0,1);overloaded.floors.g.rooms[0].rect=[0,0,250,6];
overloaded.floors.g.rooms[0].objects=Array.from({length:5},(_,i)=>({id:'rail'+i,kind:'railing',x:3,z:i+1,y:0,w:3,d:.06,h:1.1,rot:0,count:200,pitch:1,dir:'x'}));
budget.refuseBounds();const limited=budget.runBudget(overloaded);assert.equal(limited.result[0],overloaded);assert.equal(limited.result[2],'CONTEXT_DETAILS_RESOURCE_LIMIT','aggregate physical component admission precedes expansion');
console.log('PASS actual browser object compiler: ties-to-even railing and explicit zero coordinates');
console.log('PASS shipped JS context work bound: cached existing blockers and aggregate admission before repeated bounds allocation');
