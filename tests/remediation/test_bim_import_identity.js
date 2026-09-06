// C20: the shipped browser must target the same storey as the server diff.
if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict'),path=require('path'),cp=require('child_process');
  const root=path.resolve(__dirname,'../..');
  const cases=JSON.parse(cp.execFileSync('python3',['-c',
    'import json,sys;sys.path.insert(0,"tests/remediation");from test_bim_import_identity import parity_cases;print(json.dumps(parity_cases()))'],
    {cwd:root,encoding:'utf8'}));
  let passed=0,failed=0;
  for(const c of cases){
    try{
      const before=JSON.stringify([c.project,c.staging]),result=bxImportDiff(c.project,c.staging);
      assert.equal(result.valid,true);
      assert.equal(JSON.stringify([c.project,c.staging]),before);
      const entries=result.diff.entries;
      assert.equal(entries.length,c.label==='identical'?0:1);
      if(entries.length){
        assert.equal(entries[0].canonical_id,'bld_0.flr_0.plan.polygon');
        assert.equal(entries[0].authoring_id,'plan.polygon');
        assert.equal(entries[0].mapping_basis,c.label==='rename'?'SOURCE_GLOBAL_ID':'SEMANTIC_AND_GEOMETRY');
        assert.equal(entries[0].proposed_value,'Edited ground');
      }
      assert.deepEqual(result,c.result);
      passed++;console.log('PASS IFC import identity '+c.label);
    }catch(e){failed++;console.error('FAIL IFC import identity '+c.label+'\n'+e.stack);}
  }
  console.log(`IFC IMPORT IDENTITY: ${passed} passed, ${failed} failed`);
  if(failed)process.exitCode=1;
}
