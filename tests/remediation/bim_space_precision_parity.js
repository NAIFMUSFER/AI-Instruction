// Full exchange parity for test_bim_space_precision.py, using shipped functions.
const fs=require('fs'),assert=require('assert');
const project=JSON.parse(fs.readFileSync(0,'utf8')),before=JSON.stringify(project);
const result=bxBuildExchange(project,{scope:'SPACES_ONLY'});
assert.equal(result.valid,true);
assert.equal(JSON.stringify(project),before);
process.stdout.write(JSON.stringify(result.exchange));
