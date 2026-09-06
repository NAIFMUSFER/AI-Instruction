// C05. Run: node tests/lib/run.js tests/remediation/test_level_elevation.js
// Actual Three.js meshes in Node; no GPU or pixel claim.
const assertElevation = require('assert/strict');
const elevationRoot = require('path').resolve(__dirname, '../..');
globalThis.THREE = require(require('path').join(elevationRoot, 'node_modules/three/build/three.cjs'));
getMat = () => new THREE.MeshStandardMaterial();
scaleBoxUV = () => {};
const elevationBase = {site:{w:20,d:25},floor_height:3.2,wall_h:3,wall_t:.15,
  meta:{strict:true},levels:[{index:1,template:'upper'}],
  floors:{upper:{rooms:[{id:'room',rect:[1,2,6,6],walls:'full',
    doors:[{edge:'N',offset:3,width:1,height:2.1}],
    windows:[{edge:'S',offset:3,width:1.2,height:1.2,sill:1.1}],
    furniture:[{name:'desk',x:2,z:2,w:1,d:1,h:.8}]}]}}};
function elevationBounds(model){
  const group=compile(model), result={};
  group.updateMatrixWorld(true);
  group.traverse(o=>{
    if(!o.isMesh || !o.name.includes('|F1|')) return;
    const b=new THREE.Box3().setFromObject(o);
    result[o.name]={min:b.min.toArray(),max:b.max.toArray()};
  });
  return result;
}
const originalElevationBounds=elevationBounds(elevationBase);
let elevationChecks=0;
for(const [elevation,expected] of [[7.5,7.5],[0,0],[-3.5,-3.5],[undefined,3.2]]){
  const model=JSON.parse(JSON.stringify(elevationBase));
  if(elevation!==undefined) model.levels[0].elevation=elevation;
  const snapshot=JSON.stringify(model), actual=elevationBounds(model);
  assertElevation.deepEqual(Object.keys(actual).sort(),Object.keys(originalElevationBounds).sort());
  assertElevation.ok(Object.keys(actual).some(n=>n.startsWith('WINDOW|')));
  assertElevation.ok(Object.keys(actual).some(n=>n.startsWith('FLOOR|')));
  for(const name of Object.keys(actual)){
    for(const edge of ['min','max']){
      assertElevation.ok(Math.abs(actual[name][edge][1]-originalElevationBounds[name][edge][1]-(expected-3.2))<1e-5,name);
      assertElevation.equal(actual[name][edge][0],originalElevationBounds[name][edge][0],name);
      assertElevation.equal(actual[name][edge][2],originalElevationBounds[name][edge][2],name);
      elevationChecks+=3;
    }
  }
  assertElevation.equal(JSON.stringify(model),snapshot);
}
console.log('LEVEL ELEVATION: '+elevationChecks+' passed, 0 failed (actual meshes, no pixels)');
