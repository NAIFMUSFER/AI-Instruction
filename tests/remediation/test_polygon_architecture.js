// C09c: actual shipped architecture and Python parity on the polygon fixtures.
if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict'),path=require('path'),cp=require('child_process');
  const root=path.resolve(__dirname,'../..');
  const result=JSON.parse(cp.execFileSync('python3',['-c',
    'import json,sys;sys.path.insert(0,"tests/remediation");from test_polygon_architecture import model,adjacent_triangles;import acs_arch as A;b=model(objects=[{"kind":"stairs","x":1,"z":3,"w":1,"d":1}]);b["levels"].append({"index":1,"template":"plan","elevation":10.2});cases=[model(),adjacent_triangles(),b];print(json.dumps([{ "model":m,"arch":A.compile_architecture(m)} for m in cases]))'],
    {cwd:root,encoding:'utf8'}));
  const rounded=v=>Array.isArray(v)?v.map(rounded):(v&&typeof v==='object'?
    Object.fromEntries(Object.entries(v).map(([k,x])=>[k,rounded(x)])):
    typeof v==='number'?Math.round(v*1e6)/1e6:v);
  let passed=0,failed=0;
  for(let i=0;i<result.length;i++){
    try{
      const before=JSON.stringify(result[i].model),arch=compileArchitecture(result[i].model);
      assert.equal(JSON.stringify(result[i].model),before);
      assert.deepEqual(rounded(arch),rounded(result[i].arch));
      assert.ok(arch.walls.length>=5);
      if(i===0)assert.equal(arch.spaces[0].area_m2,20);
      if(i===1){const door=arch.openings[0];assert.deepEqual(archOpeningAnchor(arch,door.id),[3,3]);
        assert.equal(archDoorConnectsConfirmed(arch,door.id).spaces.length,2);}
      if(i===2)assert.deepEqual(arch.slabs.map(s=>s.area_m2),[20,19]);
      passed++;console.log('PASS polygon architecture '+i);
    }catch(e){failed++;console.error('FAIL polygon architecture '+i+'\n'+e.stack);}
  }
  try{
    const court=JSON.parse(require('fs').readFileSync(path.join(root,'tests/phase2/fixtures/arch_scen.json'),'utf8')).models.court;
    const room=court.floors.g.rooms[0];room.polygon=ACS_POLYGON.rect_ring(room.rect);
    const arch=compileArchitecture(court),uncertain=arch.walls.filter(w=>w.exposure==='unresolved');
    assert.equal(uncertain.length,4);assert.ok(uncertain.every(w=>w.exposure_basis==='opposite_side_is_void_inside_the_footprint'));
    passed++;console.log('PASS polygon courtyard exposure');
  }catch(e){failed++;console.error(e.stack);}
  console.log(`POLYGON ARCHITECTURE: ${passed} passed, ${failed} failed`);
  if(failed)process.exitCode=1;
}
