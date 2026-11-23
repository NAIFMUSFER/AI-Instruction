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
import {fitGuestCamera,keepGuestAboveGrade,visibleInGuestCut,apartmentJoinery,disposeGuestJoinery} from '../../public/app/render/guest-presentation.mjs';
const samples=[
  {name:'apartment',bounds:[-.1,-.15,-.1,20.1,11.2,25.1]},
  {name:'warehouse',bounds:[-1.75,-.15,-1.75,121.75,13.2,81.75]},
];
for(const {bounds} of samples){
  const box=new THREE.Box3(new THREE.Vector3(...bounds.slice(0,3)),new THREE.Vector3(...bounds.slice(3)));
  for(const viewport of [{width:393,height:852,right:0,top:87,bottom:76},{width:1440,height:900,right:360,top:70,bottom:0}]){
    for(const preset of ['street','exterior','cutaway','aerial']){
      const camera=new THREE.PerspectiveCamera(52,viewport.width/viewport.height,.05,2000);
      const orbit={target:new THREE.Vector3(),update(){camera.lookAt(this.target);camera.updateMatrixWorld();}};
      fitGuestCamera(box,preset,camera,orbit,viewport,-.1);
      assert.ok(camera.position.y>1.5&&orbit.maxPolarAngle<Math.PI/2);
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
for(const name of ['WALL|F0|envelope|wNs0','WALL|F0|envelope|wWs2','FLOOR|F0|office|ceil2']){
  assert.equal(visibleInGuestCut(name,true),false);
}
for(const name of ['WALL|F0|envelope|wSs0','WALL|F0|admin|wNs2','FURN|F0|storage|rack0r0L1','DOOR|F0|inbound|dock0_0']){
  assert.equal(visibleInGuestCut(name,true),true);
}
const model=new THREE.Group();
const pane=new THREE.Mesh(new THREE.BoxGeometry(2,1.3,.05),new THREE.MeshStandardMaterial());
pane.name='WINDOW|F1|west_bed|0';pane.position.set(3,5,0);model.add(pane);
const authored={site:{w:20,d:25},meta:{acs_apartment:{schema:'acs.local-apartment/1'}}};
model.updateMatrixWorld(true);
const baseline=JSON.stringify(model.toJSON());
const trim=apartmentJoinery(model,authored);
assert.equal(trim.children.length,2);
assert.ok(trim.children.every(mesh=>mesh.isInstancedMesh&&mesh.userData.floor==='F1'&&mesh.userData.sourceLayer==='WINDOW'));
assert.equal(apartmentJoinery(model,{}).children.length,0);
assert.equal(JSON.stringify(model.toJSON()),baseline,'the presentation is never added to or saved in BUILDING');
let disposed=0;trim.children[0].geometry.addEventListener('dispose',()=>disposed++);
disposeGuestJoinery(trim);assert.equal(disposed,1);
console.log('PASS shell dock apertures, 16 fits above grade, 7 cutaway predicates, source-isolated disposable joinery');
