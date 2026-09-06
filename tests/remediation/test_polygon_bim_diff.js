if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict'),path=require('path'),cp=require('child_process');
  const root=path.resolve(__dirname,'../..');
  const cases=JSON.parse(cp.execFileSync('python3',['-c',
    'import json,sys;sys.path.insert(0,"tests/remediation");from test_polygon_bim_diff import parity_cases;print(json.dumps(parity_cases()))'],
    {cwd:root,encoding:'utf8'}));
  let passed=0,failed=0;
  for(const c of cases){
    try{
      const before=JSON.stringify([c.project,c.staging]),result=bxImportDiff(c.project,c.staging);
      assert.equal(result.valid,true);assert.equal(JSON.stringify([c.project,c.staging]),before);
      const entries=result.diff.entries;
      assert.equal(entries.length,c.label==='identical'?0:1);
      if(c.label==='area')assert.deepEqual([entries[0].field,entries[0].old_value,entries[0].proposed_value],['area_m2',20,27]);
      if(c.label==='shape')assert.equal(entries[0].field,'footprint');
      assert.deepEqual(result,c.result);
      passed++;console.log('PASS polygon IFC diff '+c.label);
    }catch(e){failed++;console.error('FAIL polygon IFC diff '+c.label+'\n'+e.stack);}
  }
  console.log(`POLYGON IFC DIFF: ${passed} passed, ${failed} failed`);
  if(failed)process.exitCode=1;
}
