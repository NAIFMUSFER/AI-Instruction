// C09e: shipped BIM exchange geometry and independent Python mirror execution.
if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict'),path=require('path'),cp=require('child_process');
  const root=path.resolve(__dirname,'../..');
  const cases=JSON.parse(cp.execFileSync('python3',['-c',
    'import json,sys;sys.path.insert(0,"tests/remediation");from test_polygon_gltf import model;from test_polygon_architecture import adjacent_triangles;import acs_bim as B,acs_authoring as A;b=model(objects=[{"kind":"stairs","core_id":"A","x":1,"z":3,"w":1,"d":1}]);b["levels"].append({"index":1,"template":"plan","elevation":10.2});cases=[model(),adjacent_triangles(),b];print(json.dumps([{ "project":A.create_project(m),"result":B.build_exchange(A.create_project(m))} for m in cases]))'],
    {cwd:root,encoding:'utf8'}));
  const rounded=v=>Array.isArray(v)?v.map(rounded):(v&&typeof v==='object'?
    Object.fromEntries(Object.entries(v).map(([k,x])=>[k,rounded(x)])):
    typeof v==='number'?Math.round(v*1e6)/1e6:v);
  let passed=0,failed=0;
  for(let i=0;i<cases.length;i++){
    try{
      const before=JSON.stringify(cases[i].project),result=bxBuildExchange(cases[i].project);
      assert.equal(result.valid,true);assert.equal(JSON.stringify(cases[i].project),before);
      const ex=result.exchange;
      if(i===0){assert.equal(ex.spaces[0].area_m2,20);assert.equal(ex.walls.length,6);}
      if(i===1){assert.equal(ex.walls.length,5);assert.deepEqual([ex.doors[0].x,ex.doors[0].z],[3,3]);}
      if(i===2)assert.deepEqual(ex.slabs.map(s=>Math.round(s.cells.reduce((a,c)=>a+Math.abs(ACS_POLYGON.signed_area(c)),0))),[20,19]);
      assert.deepEqual(rounded(result),rounded(cases[i].result));
      passed++;console.log('PASS polygon BIM exchange '+i);
    }catch(e){failed++;console.error('FAIL polygon BIM exchange '+i+'\n'+e.stack);}
  }
  console.log(`POLYGON BIM EXCHANGE: ${passed} passed, ${failed} failed`);
  if(failed)process.exitCode=1;
}
