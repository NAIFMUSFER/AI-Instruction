import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Exercise the actual wall builder using a recording sink for geometry.
const src=fs.readFileSync('public/app/core/viewer.js','utf8');
const build=src.slice(src.indexOf('function buildRoom('),src.indexOf('/* ===',src.indexOf('function buildRoom(')));
const sides=[];
const context={acsRoomRect:r=>r.rect,acsList:(r,k)=>r[k]||[],normHex:s=>s,ROLE_COLOR:{},acsCapList:a=>a,SCENE_LIMITS:{},
  edgeGeom:()=>['x',0,0,5],wallOpenings:(...args)=>sides.push(args[11]),dockOpenings:()=>({N:[],S:[],E:[],W:[]})};
const room=vm.runInNewContext(build+'\nbuildRoom',context);
for(const [walls,expected] of [[[],[]],[['N','W'],['wN','wW']],['full',['wN','wS','wE','wW']]]){
  sides.length=0;room({}, {id:'roof',rect:[0,0,5,5],walls},'F3',9,{wall_h:.8,wall_t:.2});
  assert.deepEqual(sides,expected,'roof parapets must follow the authored exposed edges');
}
console.log('PASS roof walls follow canonical edge subsets');
const cutStart=src.indexOf('function hostedDockCuts(');
assert.ok(cutStart>=0,'compiled outside envelope must respect the loading bays declared in its operational zones');
const dockCode=src.slice(cutStart,src.indexOf('\n}',cutStart)+2);
const cuts=vm.runInNewContext(dockCode+'\nhostedDockCuts',{
  acsRoomRect:r=>r.rect,edgeGeom:(e,[x,z,w,d])=>e==='N'?['x',z,x,x+w]:['x',z+d,x,x+w],
  dockOpenings:r=>({N:r.dockIntervals,S:[],W:[],E:[]})
});
const shell={id:'envelope',rect:[10,8,100,60]};
const dock=(x,z,ds)=>({rect:[x,z,20,12],docks:[{}],dockIntervals:ds});
const result=cuts(shell,[shell,dock(10,8,[[15,3,0,4]]),dock(10,18,[[19,2,0,3]]),dock(130,8,[[135,3,0,4]])]);
assert.deepEqual(JSON.parse(JSON.stringify(result.N)),[[15,3,0,4]],'only a dock co-planar with and inside the host edge cuts its wall');
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {fitGuestCamera,keepGuestAboveGrade,visibleInGuestCut,apartmentJoinery,disposeGuestJoinery} from '../../public/app/render/guest-presentation.mjs';
const samples=[
  {name:'apartment',bounds:[-.1,-.15,-.1,20.1,11.2,25.1]},
  {name:'warehouse',bounds:[-1.75,-.15,-1.75,121.75,13.2,81.75]},
];
for(const {bounds} of samples){
  const box=new THREE.Box3(new THREE.Vector3(...bounds.slice(0,3)),new THREE.Vector3(...bounds.slice(3)));
  for(const viewport of [{width:393,height:852,right:0,top:87,bottom:76},{width:1440,height:900,right:360,top:70,bottom:0}]){
    for(const preset of ['street','exterior','cutaway','aerial','top']){
      const camera=new THREE.PerspectiveCamera(52,viewport.width/viewport.height,.05,2000);
      const orbit={target:new THREE.Vector3(),update(){camera.lookAt(this.target);camera.updateMatrixWorld();}};
      fitGuestCamera(box,preset,camera,orbit,viewport,-.1);
      assert.ok(camera.position.y>1.5&&orbit.maxPolarAngle<Math.PI/2);
      if(preset==='top'){
        assert.ok(camera.position.clone().sub(orbit.target).normalize().y>.99999);
      }
      const pixels=[];
      for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
        const point=new THREE.Vector3(x,y,z).project(camera);
        const px=(point.x+1)*viewport.width/2,py=(1-point.y)*viewport.height/2;
        assert.ok(point.z<1&&px>=0&&px<=viewport.width-viewport.right&&py>=viewport.top&&py<=viewport.height-viewport.bottom);
        pixels.push(px);
      }
      assert.ok((Math.max(...pixels)-Math.min(...pixels))/(viewport.width-viewport.right)>.44);
      camera.position.y=-9;orbit.target.y=-7;
      keepGuestAboveGrade(camera,orbit,-.1);
      assert.ok(camera.position.y>-.1&&orbit.target.y>-.1);
    }
  }
}
// A guest requesting an east-facing entrance should approach it from the east.
const streetBox=new THREE.Box3(new THREE.Vector3(0,0,0),new THREE.Vector3(24,14,28));
for(const [edge,axis,sign] of [['N','z',-1],['E','x',1],['S','z',1],['W','x',-1]]){
  const camera=new THREE.PerspectiveCamera(52,1,.05,1000);
  const orbit={target:new THREE.Vector3(),update(){}};
  fitGuestCamera(streetBox,'street',camera,orbit,{width:900,height:900,right:0,top:0,bottom:0},0,edge);
  assert.ok(camera.position.clone().sub(orbit.target).normalize()[axis]*sign>.95);
}
for(const name of ['WALL|F0|envelope|wNs0','WALL|F0|envelope|wWs2','FLOOR|F0|office|ceil2']){
  assert.equal(visibleInGuestCut(name,true),false);
}
for(const name of ['WALL|F0|envelope|wSs0','WALL|F0|admin|wNs2','FURN|F0|storage|rack0r0L1','DOOR|F0|inbound|dock0_0']){
  assert.equal(visibleInGuestCut(name,true),true);
}
const model=new THREE.Group();
const pane=new THREE.Mesh(new THREE.BoxGeometry(2,1.3,.05),new THREE.MeshStandardMaterial());
pane.name='WINDOW|F1|west_bed|0';pane.position.set(3,5,0);model.add(pane);
const authored={wall_t:.18,site:{w:20,d:25},meta:{acs_apartment:{schema:'acs.local-apartment/1'}}};
model.updateMatrixWorld(true);
const baseline=JSON.stringify(model.toJSON());
const trim=apartmentJoinery(model,authored);
assert.equal(trim.children.length,2);
assert.ok(trim.children.every(mesh=>mesh.isInstancedMesh&&mesh.userData.floor==='F1'&&mesh.userData.sourceLayer==='WINDOW'));
assert.equal(apartmentJoinery(model,{}).children.length,0);
assert.equal(JSON.stringify(model.toJSON()),baseline,'the presentation is never added to or saved in BUILDING');
let disposed=0;trim.children[0].geometry.addEventListener('dispose',()=>disposed++);
disposeGuestJoinery(trim);assert.equal(disposed,1);
console.log('PASS shell dock apertures, 20 fits above grade, all four facade directions, cutaway predicates and disposable joinery');
const {guestFocus}=await import('../../public/app/render/guest-presentation.mjs');
const a={levels:[{index:0,template:'ground',elevation:.4}],floors:{ground:{rooms:[{id:'family',role:'living',rect:[3,2,6,5]}]}}};
const inventory=new THREE.Group(),glass=new THREE.MeshStandardMaterial({transparent:true});
const bay=(name,x,y,z,w,h,d,mat=glass)=>{
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);mesh.name=name;
  mesh.position.set(x,y,z);inventory.add(mesh);return mesh;
};
bay('DOOR|F0|lobby|3',10,1.6,1.35,1.8,2.4,.05);
bay('DOOR|F0|inbound_docks|dock0_0',4,2.1,0,3,4.2,.1);
bay('FURN|F0|storage|rack0r0L0',14,.52,12,20,.05,1);
bay('FURN|F0|storage|rack0r1L0',14,.52,16,20,.05,1);
inventory.updateMatrixWorld(true);
const homeEye=guestFocus(inventory,a,'interior',false);
assert.ok(homeEye.position.x>3&&homeEye.position.x<9&&homeEye.position.z>2&&homeEye.position.z<7);
assert.equal(homeEye.position.y,2.05);assert.equal(homeEye.source,'F0|family');
const aisle=guestFocus(inventory,a,'interior',true);
assert.equal(aisle.position.z,14);assert.ok(aisle.position.x<aisle.target.x);
for(const warehouse of [false,true]){
  const focus=guestFocus(inventory,a,'detail',warehouse);
  assert.ok(focus.source.startsWith('DOOR|F0|'));assert.equal(focus.box.isEmpty(),false);
}
assert.equal(guestFocus(new THREE.Group(),a,'detail',false),null);
console.log('PASS actual entrance, dock, living room and rack aisle close views, explicit missing anchor');

// A 20 m gross facade has its hosted pane 90 mm inside the outer face.
pane.position.z=.09;model.updateMatrixWorld(true);
const measuredTrim=apartmentJoinery(model,authored);
assert.equal(measuredTrim.children.length,2,'both bronze frame and stone sill must follow measured exterior axes');
const sill=measuredTrim.children.find(o=>o.name.endsWith('|stone'));
const sillMatrix=new THREE.Matrix4();sill.getMatrixAt(0,sillMatrix);
assert.ok(Math.abs(new THREE.Vector3().setFromMatrixPosition(sillMatrix).z-(.09-.075))<1e-6);
pane.position.z=1.35;model.updateMatrixWorld(true);
const recessed=apartmentJoinery(model,authored);
assert.equal(recessed.children.length,1,'a recessed interior pane must not acquire an exterior projecting hood');
disposeGuestJoinery(measuredTrim);disposeGuestJoinery(recessed);
console.log('PASS hosted trim follows exterior wall centre on gross footprint and leaves recessed opening clear');

// Execute the shipped browser buildRoom/wallOpenings, then read the emitted
// wall solids with Three. Gross dimensions must include the exterior skin.
const {apartmentSample,apartmentDoorPairs}=await import('../../public/app/core/local-apartment.mjs');
const sample=apartmentSample(),rendered=new THREE.Group(),wallBounds=new THREE.Box3();
const openingMath=src.slice(src.indexOf('function normEdge('),src.indexOf('/* KI-25/F-42',src.indexOf('function wallOpenings(')));
const actualRoom=vm.runInNewContext(openingMath+'\n'+build+'\nbuildRoom',{
  ...context,buildObjects(){},slabStrips(){return [];},
  addBox:(group,x,y,z,w,h,d,mat,name)=>{
    if(!/^(WALL|WINDOW|DOOR)\|/.test(name))return;
    const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({transparent:mat==='window'||mat==='door_glass'}));
    m.name=name;m.position.set(x,y,z);group.add(m);
    if(name.startsWith('WALL|'))wallBounds.union(new THREE.Box3().setFromObject(m));
    return m;
  }
});
for(const level of sample.levels){
  const rooms=sample.floors[level.template].rooms,doorPairs=apartmentDoorPairs(rooms);
  for(const r of rooms)
    actualRoom(rendered,r,'F'+level.index,level.elevation,{wall_t:sample.wall_t,wall_h:sample.wall_h,doorPairs});
  const leaves=rendered.children.filter(m=>m.name.startsWith('DOOR|F'+level.index+'|'));
  assert.equal(leaves.length,doorPairs.size/2);
  assert.ok(leaves.every(m=>m.userData.acs_door_pair?.hosts?.length===2));
}
assert.equal(rendered.children.filter(m=>m.name.startsWith('DOOR|')).length,107);
const footprint=wallBounds.getSize(new THREE.Vector3());
assert.ok(Math.abs(footprint.x-20)<1e-5&&Math.abs(footprint.z-25)<1e-5);
assert.ok(Math.abs(wallBounds.min.x)+Math.abs(wallBounds.min.z)<1e-5);
for(const mode of ['interior','detail'])assert.ok(guestFocus(rendered,sample,mode,false)?.source);
const authoredTrim=apartmentJoinery(rendered,sample);
assert.ok(authoredTrim.children.filter(o=>o.name.endsWith('|stone')).length>=3,'all three original storeys have hosted sill/cornice detail');
console.log('PASS actual browser-built wall faces span '+footprint.x.toFixed(3)+' m × '+footprint.z.toFixed(3)+' m and all occupied floors retain hosted trim');
const pairA={id:'a',rect:[0,0,3,4],walls:'full',doors:[{id:'a_to_b',edge:'E',offset:2,width:1,height:2.2}]};
const pairB={id:'b',rect:[3,0,3,4],walls:'full',doors:[{id:'b_to_a',edge:'W',offset:2,width:1,height:2.2}]};
const hosts=[{room_id:'a',door_id:'a_to_b',door_index:0},{room_id:'b',door_id:'b_to_a',door_index:0}];
const registered=new Map([[pairA.doors[0],{pair_id:'door|a|b',primary:true,hosts}],[pairB.doors[0],{pair_id:'door|a|b',primary:false,hosts}]]);
function leaves(doorPairs){
  const g=new THREE.Group();
  for(const r of [pairB,pairA])actualRoom(g,r,'F0',0,{wall_t:.18,wall_h:3.18,doorPairs});
  return g;
}
const pairModel=leaves(registered);
const pairLeaves=pairModel.children.filter(o=>o.name.startsWith('DOOR|'));
assert.equal(pairLeaves.length,1,'one physical leaf must serve two registered co-planar openings');
assert.deepEqual(pairLeaves[0].userData.acs_door_pair.hosts,hosts);
assert.equal(pairLeaves[0].userData.acs_door_pair.floor_key,'F0');
assert.equal(leaves(null).children.filter(o=>o.name.startsWith('DOOR|')).length,2,'unrelated or historical inputs retain both leaves');
for(const name of ['a','b']){
  const wall=pairModel.children.filter(o=>o.name.match(new RegExp('^WALL\\|F0\\|'+name+'\\|w[EW]')));
  assert.ok(wall.length>0&&wall.every(o=>!new THREE.Box3().setFromObject(o).containsPoint(new THREE.Vector3(3,1,2))));
}
console.log('PASS one reciprocal leaf, two hosted apertures, both source references and legacy inputs');
// Self-finish of the single displayed leaf updates both registered sources
// so the next build can still validate their fit/material compatibility.
const wiring=fs.readFileSync('public/app/ui/workspace-ui-wiring.js','utf8');
const finishBlock=wiring.slice(wiring.indexOf('function applyFinish('),wiring.indexOf('/* ===',wiring.indexOf('function applyFinish(')));
const roomSet={rooms:[pairA,pairB]};
const change=vm.runInNewContext(finishBlock+'\napplyFinish',{
  normHex:c=>c,getMat:()=>({}),roomOfTag:()=>({room:pairA,rid:'a',fkey:'F0'}),isolateTemplate:()=>roomSet});
change(pairLeaves[0].name,'self','#906c46',pairLeaves[0]);
assert.equal(pairA.doors[0].color,'#906c46');assert.equal(pairB.doors[0].color,'#906c46');
console.log('PASS selected physical leaf finish persists on both matched canonical host records');

const {guestFrameScheduler}=await import('../../public/app/render/guest-presentation.mjs');
assert.equal(typeof guestFrameScheduler,'function','a static public model must stop submitting frames');
{
 let available=true,moving=false,drawn=0,sequence=0,damping=0;
 const callbacks=new Map();
 const q=guestFrameScheduler({available:()=>available,moving:()=>moving,
   paint(){drawn++;if(damping-->0)q.request();},
   schedule:cb=>{callbacks.set(++sequence,cb);return sequence;},cancel:id=>callbacks.delete(id)});
 function next(){const callbacksThisTick=[...callbacks.values()];callbacks.clear();for(const cb of callbacksThisTick)cb();}
 q.request();q.request();next();for(let i=0;i<12;i++)next();
 assert.equal(drawn,1,'static scene must remain idle');
 damping=2;q.request();next();next();next();next();assert.equal(drawn,4,'Orbit damping draws until the last change');
 moving=true;q.request();next();next();moving=false;next();next();assert.equal(drawn,7,'walk and tour continue until they stop');
 q.request();available=false;q.stop();next();q.request();next();assert.equal(drawn,7,'hidden or lost context cannot redraw or retain work');
 available=true;q.request();next();assert.equal(drawn,8);assert.equal(q.pending(),false);
}
console.log('PASS guest frame ownership, idle, damping, animation and visibility recovery');

// Exercise the actual frame handler, ownership transitions, scheduler and
// pinned OrbitControls. The negative witness restores fixed per-frame damping;
// the corrected path must settle by elapsed time at both fast and slow rates.
const frameSource=wiring.slice(wiring.indexOf('let last2=performance.now();'),wiring.indexOf('const acsLegacyVisibility='));
const controlSource=wiring.slice(wiring.indexOf("orbit.addEventListener?.('start'"),wiring.indexOf("for(const event of ['input'"));
assert.ok(frameSource.startsWith('let last2=performance.now();')&&controlSource.includes("'change'"));
function orbitIdleFixture(width,pointerType,frameMs,oldDamping=false){
  const height=width===393?852:900,listeners=new Map(),callbacks=new Map(),classes=new Set(['acs-entered']);
  let sequence=0,clock=0,rendered=0;
  const element={style:{},clientWidth:width,clientHeight:height,
    setPointerCapture(){},releasePointerCapture(){},
    getBoundingClientRect:()=>({left:0,top:0,width,height}),
    addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},
    removeEventListener(type,fn){listeners.get(type)?.delete(fn);}};
  const camera=new THREE.PerspectiveCamera(52,width/height,.05,6000);
  camera.position.set(46.1662,36.4746,-52.0825);
  const orbit=new OrbitControls(camera,element);orbit.enableDamping=true;orbit.dampingFactor=.17;
  orbit.target.set(10,5.475,12.5);orbit.update();
  const state={orbit,camera,guestFrameScheduler,keepGuestAboveGrade,
    performance:{now:()=>clock},window:{ACS:{guest:true}},
    document:{hidden:false,querySelector:()=>null,body:{classList:{contains:name=>classes.has(name)}}},
    renderer:{xr:{isPresenting:false},info:{render:{frame:0}},setAnimationLoop(fn){this.loop=fn;},
      render(){rendered++;this.info.render.frame++;}},
    scene:{},ground:{position:{y:-.1}},headLamp:{position:new THREE.Vector3()},
    walkState:{active:false},fly:{on:false},mode:'orbit',flyStep:()=>false,
    vrStep(){},walkStep(){},tourStep(){},camWorld:()=>camera.position,
    requestAnimationFrame:fn=>{callbacks.set(++sequence,{fn,at:clock+frameMs});return sequence;},
    cancelAnimationFrame:id=>callbacks.delete(id)};
  const controls=vm.runInNewContext(frameSource+'\n'+controlSource+'\n({sync:syncLegacyRendering,frame:acsLegacyFrame})',state);
  const stats=state.window.ACS.guestRenderStats;
  function advance(ms){
    const end=clock+ms;
    while(callbacks.size){
      const at=Math.min(...[...callbacks.values()].map(row=>row.at));
      if(at>end)break;
      clock=at;const tick=[...callbacks].filter(([,row])=>row.at===at);
      for(const [id,row] of tick){callbacks.delete(id);row.fn();}
    }
    clock=end;
  }
  function event(type,x,y,extra={}){
    const e={pointerType,pointerId:1,button:0,clientX:x,clientY:y,pageX:x,pageY:y,preventDefault(){},...extra};
    [...listeners.get(type)||[]].forEach(fn=>fn(e));
  }
  controls.sync();advance(frameMs);assert.equal(stats().pending,false,'initial view must settle');
  if(oldDamping){
    // Recreate the old public policy using the real controls: their factor
    // cannot adapt to elapsed time and remains at its previous default .05.
    Object.defineProperty(orbit,'dampingFactor',{configurable:true,get:()=>.05,set(){}});
  }
  const before=camera.position.clone(),beforeStats=stats(),x=Math.round(width*.35),y=Math.round(height*.52);
  event('pointerdown',x,y);
  for(let i=1;i<=5;i++){advance(16);event('pointermove',x+28*i/5,y-10*i/5);}
  event('pointerup',x+28,y-10);
  const released=clock;
  if(oldDamping){
    advance(64*frameMs);
    assert.equal(stats().pending,true,'fixed damping must reproduce the still-running slow-frame tail');
  }else{
    while(stats().pending&&clock-released<6000)advance(frameMs);
    assert.equal(stats().pending,false,'elapsed-time guest inertia must settle within six seconds even on a slow renderer');
  }
  assert.ok(camera.position.distanceTo(before)>.1,'actual pointer gesture must move the camera');
  assert.ok(stats().draws>beforeStats.draws&&stats().rendererFrames>beforeStats.rendererFrames,'actual frame handler must draw the gesture');
  const outcome={width,pointerType,frameMs,elapsedMs:clock-released,frames:stats().draws-beforeStats.draws,position:camera.position.toArray()};
  if(!oldDamping){
    assert.equal(orbit.enableDamping,true,'elapsed-time policy retains smooth guest inertia');
    const radius=camera.position.distanceTo(orbit.target),wheelFrames=rendered;
    event('wheel',x,y,{deltaY:-120});advance(frameMs);
    assert.ok(camera.position.distanceTo(orbit.target)<radius,'wheel zoom must still move the actual camera');
    assert.ok(rendered>wheelFrames,'wheel zoom must receive its actual redraw');
    const settled=stats();advance(6000);
    assert.deepEqual(stats(),settled,'settled controls must submit no more frames');
    // A connected/hidden route restores the original factor even while the
    // guest flag still exists; a stray control event must not overwrite it.
    classes.add('acs-connected');controls.sync();
    assert.equal(orbit.dampingFactor,.17,'connected ownership must restore the original factor');
    event('pointerdown',x,y);event('pointerup',x,y);
    assert.equal(orbit.dampingFactor,.17,'inactive guest input cannot overwrite the restored factor');
    classes.delete('acs-connected');state.window.ACS.guest=false;controls.sync();
    assert.equal(orbit.enableDamping,true);
    assert.equal(orbit.dampingFactor,.17,'legacy ownership must retain its configured damping');
    assert.equal(state.renderer.loop,controls.frame,'legacy frame ownership remains intact');
    clock+=frameMs;controls.frame();assert.equal(orbit.dampingFactor,.17,'legacy frames cannot reuse a guest factor');
    orbit.dampingFactor=.23;state.window.ACS.guest=true;controls.sync();advance(frameMs);
    state.window.ACS.guest=false;controls.sync();
    assert.equal(orbit.dampingFactor,.23,'a later guest visit must restore the latest legacy preference');
  }
  state.window.ACS.guest=false;controls.sync();orbit.dispose();
  return outcome;
}
const previousControlWindow=globalThis.window,settling=[];
try{
  // The real controls read browser DPR when normalizing a wheel delta.
  globalThis.window={devicePixelRatio:1};
  for(const width of [393,1440])for(const pointerType of ['mouse','touch']){
    orbitIdleFixture(width,pointerType,400,true);
    const rates=[1000/60,400,800].map(ms=>orbitIdleFixture(width,pointerType,ms));
    const reference=new THREE.Vector3(...rates[0].position);
    assert.ok(rates.every(row=>new THREE.Vector3(...row.position).distanceTo(reference)<.03),'fast and slow frame rates must converge to the same user-requested view');
    settling.push(...rates.map(({position,...row})=>row));
  }
}finally{
  if(previousControlWindow===undefined)delete globalThis.window;
  else globalThis.window=previousControlWindow;
}
console.log('PASS real pinned orbit controls: elapsed-time settling, fixed-frame negative witness, gestures, idle and original legacy damping restored '+JSON.stringify(settling));
const {warehouseDockFinish}=await import('../../public/app/render/guest-presentation.mjs');
const shutters=warehouseDockFinish(inventory,{site:{w:40,d:30}});
assert.equal(shutters.children.length,3,'one batched sheet, seams and guide profile for actual dock gate');
assert.ok(shutters.children.every(o=>o.userData.sourceLayer==='DOOR'&&o.userData.floor==='F0'));
assert.equal(shutters.children.find(o=>o.name.endsWith('|shutter')).count,1);
assert.equal(warehouseDockFinish(new THREE.Group(),{site:{}}).children.length,0);
const phone=new THREE.PerspectiveCamera(52,393/852,.01,400),controller={target:new THREE.Vector3(),update(){}};
const viewport={width:393,height:852,right:0,top:79,bottom:76},roomBounds=new THREE.Box3(new THREE.Vector3(0,0,0),new THREE.Vector3(4,3,7));
fitGuestCamera(roomBounds,'interior',phone,controller,viewport,-.1);
const hfov=2*THREE.MathUtils.radToDeg(Math.atan(Math.tan(THREE.MathUtils.degToRad(phone.fov/2))*393/852));
assert.ok(hfov>=48.9,'portrait indoor field must show a meaningful room width');
fitGuestCamera(roomBounds,'exterior',phone,controller,viewport,-.1);assert.equal(phone.fov,52);
disposeGuestJoinery(shutters);
console.log('PASS measured portrait interior lens and non-exported, gate-hosted shutter finish');

// With no GPU, a real court changes pixels in the central roof field. The
// preserved facade and the surrounding site keep the same color and position.
const {drawGuestSoftwareView}=await import('../../public/app/render/guest-software-view.mjs');
const {apartmentFromRevision}=await import('../../public/app/core/local-apartment.mjs');
const {withDefaultRoof}=await import('../../public/app/core/roof.mjs');
const images=[];
const context2d={
  createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),
  putImageData:image=>images.push(image.data)
};
const canvas2d={clientWidth:300,clientHeight:200,getContext(type){assert.equal(type,'2d');return context2d;}};
const court=apartmentFromRevision('خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق',sample);
for(const project of [sample,court]){
  const renderedRoof=drawGuestSoftwareView(canvas2d,withDefaultRoof(project)[0],{view:'top'});
  assert.ok(renderedRoof.meshCount>100);
}
let changedRoofPixels=0,changedOutside=0;
for(let y=0;y<200;y++)for(let x=0;x<300;x++){
  const offset=4*(300*y+x);
  if(Math.abs(images[0][offset]-images[1][offset])<3)continue;
  if(x>100&&x<200&&y>50&&y<150)changedRoofPixels++;
  else changedOutside++;
}
assert.ok(changedRoofPixels>200);
assert.ok(changedOutside<10);
console.log('PASS CPU-only 3D renderer distinguishes the physical sky court at the center of the same roof');
