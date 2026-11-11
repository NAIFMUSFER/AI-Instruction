'use strict';
// Execute the real source/generated shadow helpers with counted render targets.
// This measures state/resource ownership, not GPU performance or visual quality.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ROOT=path.resolve(__dirname,'../..');
function harness(relative){
 const source=fs.readFileSync(path.join(ROOT,relative),'utf8');
 const start=source.indexOf('function _pqSaveOriginals(){'),end=source.indexOf('window.ACS.pbrApply=function(cfg){');
 const shadowStart=source.indexOf('    const shadowsOn='),shadowEnd=source.indexOf('    /* 2. الشمس',shadowStart);
 assert.ok(start>=0&&end>start&&shadowStart>end&&shadowEnd>shadowStart,'real source anchors exist');
 const canonical=Object.freeze({id:'synthetic-model',site:Object.freeze({w:30,d:25})});
 const camera={left:-17,right:23,top:31,bottom:-13,near:.7,far:450,updateProjectionMatrix(){this.updates=(this.updates||0)+1;}};
 const sun={castShadow:false,intensity:2,color:{getHex:()=>1,setHex(){}},shadow:{mapSize:{x:1024,y:2048,set(x,y){this.x=x;this.y=y;}},bias:-.0007,normalBias:.03,radius:2,camera,map:null,mapPass:null}};
 const state={saved:null,fills:[],context:null,composer:null,applied:null};
 const context={window:{ACS:{},__ACS_PQ__:state},renderer:{toneMappingExposure:1,getPixelRatio:()=>1,setPixelRatio(){},shadowMap:{enabled:false}},sun,scene:{environment:null,background:null,canonical,remove(){},traverse(){}},matCache:{},report:{changed:[]}};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);
 vm.runInContext('function applyShadow(cfg){'+source.slice(shadowStart,shadowEnd)+'}',context);
 const snapshot=()=>({enabled:context.renderer.shadowMap.enabled,castShadow:sun.castShadow,size:[sun.shadow.mapSize.x,sun.shadow.mapSize.y],bias:sun.shadow.bias,normalBias:sun.shadow.normalBias,radius:sun.shadow.radius,camera:Object.fromEntries(['left','right','top','bottom','near','far'].map(key=>[key,camera[key]]))});
 return {context,state,sun,camera,canonical,snapshot};
}
let passed=0;
for(const file of ['tools/_pbr_bridge_block.js','public/app/generated/pbr-bridge.js']){
 const h=harness(file),original=h.snapshot();let oldDisposals=0,newDisposals=0;
 h.sun.shadow.map={dispose(){oldDisposals++;}};h.sun.shadow.mapPass={dispose(){oldDisposals++;}};
 h.context._pqSaveOriginals();
 h.context.applyShadow({lighting:{shadows:true},shadow:{map_size:8192,bias:-.002,normal_bias:.09,radius_px:4,camera:{left:-500,right:500,top:500,bottom:-500,near:1,far:3000}}});
 assert.equal(h.sun.shadow.mapSize.x,8192);
 // Simulate targets allocated by Three after ULTRA. Returning to engineering
 // must release these so Three allocates the restored dimensions next frame.
 h.sun.shadow.map={dispose(){newDisposals++;}};h.sun.shadow.mapPass={dispose(){newDisposals++;}};
 assert.equal(h.context._pqRestore().restored,true);
 assert.deepEqual(h.snapshot(),original,'every mutated shadow setting must return to the captured baseline');
 assert.equal(oldDisposals,2,'applying a new shadow size releases both old render targets');
 assert.equal(newDisposals,2,'restoring a different size releases both current render targets once');
 assert.equal(h.sun.shadow.map,null);assert.equal(h.sun.shadow.mapPass,null);
 assert.equal(h.camera.updates,2,'projection is updated after apply and restore');
 assert.equal(h.context._pqRestore().restored,false);assert.equal(newDisposals,2,'repeat restore does not double-dispose');
 assert.equal(h.state.saved,null,'a restored baseline must release references to the previous model');
 h.sun.shadow.mapSize.set(2048,4096);h.camera.left=-100;h.camera.far=900;
 const next=h.snapshot();h.context._pqSaveOriginals();
 h.context.applyShadow({lighting:{shadows:true},shadow:{map_size:8192,bias:-.002,normal_bias:.09,radius_px:4,camera:{left:-500,right:500,top:500,bottom:-500,near:1,far:3000}}});
 h.context._pqRestore();assert.deepEqual(h.snapshot(),next,'the next apply restores its own baseline, not the first model');
 assert.deepEqual(h.canonical,{id:'synthetic-model',site:{w:30,d:25}});passed++;
 const empty=harness(file);assert.equal(empty.context._pqRestore().restored,false);passed++;
 const same=harness(file);same.context._pqSaveOriginals();let sameDisposals=0;
 same.sun.shadow.map={dispose(){sameDisposals++;}};same.context._pqRestore();
 assert.equal(sameDisposals,0,'unchanged size keeps its reusable shadow target');passed++;
 const shared=harness(file);shared.context._pqSaveOriginals();let once=0;const target={dispose(){once++;}};
 shared.sun.shadow.mapSize.set(8192,8192);shared.sun.shadow.map=target;shared.sun.shadow.mapPass=target;shared.context._pqRestore();
 assert.equal(once,1,'an aliased render target is released once');passed++;
}
console.log('PBR SHADOW RESTORE: '+passed+' source/generated state and resource regressions passed; no GPU claim.');
