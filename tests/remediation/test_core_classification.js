/* Real shipped architecture/relations/distance functions, no renderer double. */
const coreAssert = require('assert');
const coreModel = kind => ({site:{w:20,d:25},floor_height:3.2,
  levels:[{index:0,template:'g'},{index:1,template:'g'}],
  floors:{g:{rooms:[{id:'store',rect:[0,0,10,10],walls:'none',
    objects:[{kind,x:3,z:3,w:1.2,d:2.2}]}]}}});
for(const name of ['forklift','electric forklift','forklift_A']){
  const obj={kind:name};
  coreAssert.strictEqual(_aCoreKind(obj),null);
  coreAssert.strictEqual(_relKind(obj),null);
  coreAssert.strictEqual(_dsFindObject({objects:[obj]},'elevator'),null);
}
const modelForklift=coreModel('forklift');
const beforeForklift=JSON.stringify(modelForklift);
coreAssert.deepStrictEqual(compileArchitecture(modelForklift).cores,[]);
coreAssert.deepStrictEqual(compileArchitecture(modelForklift).voids,[]);
coreAssert.deepStrictEqual(buildRelationships(modelForklift).filter(x=>x.type==='VERTICAL_CONNECTS'),[]);
coreAssert.strictEqual(JSON.stringify(modelForklift),beforeForklift);
for(const kind of ['stairs','staircase','درج','elevator','lift','service_lift','مصعد']){
  coreAssert.strictEqual(compileArchitecture(coreModel(kind)).voids.length,1);
  coreAssert.strictEqual(buildRelationships(coreModel(kind)).filter(x=>x.type==='VERTICAL_CONNECTS').length,1);
}
console.log('CORE CLASSIFICATION: 27 checks passed');
