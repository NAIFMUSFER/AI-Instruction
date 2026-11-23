// Executed by test_roof_ifc_semantics.py using the actual shipped exchange code.
const fs=require('fs'),assert=require('assert');
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(rows.map(row=>{
  const before=JSON.stringify(row.project);
  const result=bxBuildExchange(row.project,row.options);
  assert.equal(JSON.stringify(row.project),before);
  const descriptor=result.valid?bxExportDescriptor(row.project,result.exchange,null,null):null;
  const keys=['level_count','space_count','roof_level_count','roof_reference_count',
              'object_count','content_scope','roof_policy','roof_reference_metadata',
              'roof_reference_height_policy'];
  return {built:result,metadata:descriptor?Object.fromEntries(keys.map(k=>[k,descriptor[k]])):null};
})));
