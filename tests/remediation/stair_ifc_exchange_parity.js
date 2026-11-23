// Invoked by test_stair_ifc_boundary.py through the shipped-engine Node harness.
const assert=require('assert'), fs=require('fs');
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
const result=rows.map(row=>{
  const before=JSON.stringify(row.project);
  const built=bxBuildExchange(row.project,row.options);
  assert.equal(built.valid,row.valid,'declared unsupported stair form escaped the browser boundary');
  assert.equal(JSON.stringify(row.project),before,'IFC exchange mutated the canonical project');
  if(!row.valid){
    assert.equal(built.exchange,null);
    assert(built.issues.length>0);
    assert(built.issues.every(i=>i.code==='BIM_EXPORT_VALIDATION_FAILED'&&i.blocking));
  }
  return {valid:built.valid,issues:built.issues,
    stair_ids:((built.exchange||{}).stairs||[]).map(s=>s.canonical_id),
    level_ids:((built.exchange||{}).levels||[]).map(s=>s.canonical_id)};
});
process.stdout.write(JSON.stringify(result));
