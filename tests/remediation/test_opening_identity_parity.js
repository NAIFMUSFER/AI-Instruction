const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const {execFileSync}=require('child_process');
const root=path.resolve(__dirname,'..','..');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'acs-opening-identity-'));
try{
  const output=path.join(tmp,'js.json');
  const js=execFileSync(process.execPath,[path.join(root,'tests/lib/run.js'),
    path.join(__dirname,'test_opening_identity.js')],{cwd:root,encoding:'utf8',
    env:{...process.env,ACS_OPENING_IDENTITY_PARITY:output}});
  process.stdout.write(js);
  const py=JSON.parse(execFileSync('python3',[path.join(__dirname,'test_opening_identity.py'),'--snapshot'],
    {cwd:root,encoding:'utf8',maxBuffer:8*1024*1024}));
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(output,'utf8')),py);
  console.log('OPENING IDENTITY PARITY: 1 passed, 0 failed (model, history, audit, architecture, tree, exchange, resolution)');
}finally{fs.rmSync(tmp,{recursive:true,force:true});}
