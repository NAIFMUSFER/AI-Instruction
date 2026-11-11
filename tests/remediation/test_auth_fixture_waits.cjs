'use strict';
// Regression for intermediate OAuth documents and secondary waiter rejection.
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const fixture=require('./test_auth_shipped_page.cjs');
const entered=document=>vm.runInNewContext('('+fixture.workspaceEntered.toString()+')()',{document});
(async()=>{
  assert.equal(entered({body:null}),false,'an intermediate redirect has no body yet');
  assert.equal(entered({body:{classList:{contains:()=>false}}}),false,'a sign-in document is not a private workspace');
  let checkedClass;
  assert.equal(entered({body:{classList:{contains:value=>(checkedClass=value,true)}}}),true);
  assert.equal(checkedClass,'acs-entered','the private workspace readiness requirement remains exact');
  const witness=spawnSync(process.execPath,['-e',`
    const {sourceResponse}=require(${JSON.stringify(require.resolve('./test_auth_shipped_page.cjs'))});
    sourceResponse({waitForResponse:()=>new Promise((resolve,reject)=>setImmediate(()=>reject(new Error('synthetic context close'))))});
    setImmediate(()=>setImmediate(()=>console.log('primary failure preserved')));
  `],{encoding:'utf8'});
  assert.equal(witness.status,0,witness.stderr);
  assert.match(witness.stdout,/primary failure preserved/);
  const original=new Error('synthetic source request failed');
  await assert.rejects(fixture.sourceResponse({waitForResponse:()=>Promise.reject(original)}),error=>error===original,'an awaited source failure still fails the browser test');
  console.log('PASS auth fixture waits: null-body redirect, exact readiness, pending rejection and awaited failure');
})().catch(error=>{console.error(error);process.exitCode=1;});
