'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {downloadProject,progressRecorder}=require('../deploy/verify_public_guest.js');

function panelPage(mobile){
 let open=false,tab=false;
 const actions=[];
 const page={
  locator(id){return {
   getAttribute:async name=>{assert.equal(id,'#panelToggle');assert.equal(name,'aria-expanded');return String(open);},
   async click(){
    actions.push(id);
    if(id==='#panelToggle'){assert.ok(mobile);open=true;}
    if(id==='#acsTabShow'){assert.ok(!mobile||open);tab=true;}
    if(id==='#bJson')assert.ok(tab&&(!mobile||open));
    if(id==='#projectPanelClose'){assert.ok(mobile&&open);open=false;}
    if(id==='#guestSignin')assert.ok(!open,'open mobile sheet intercepts the real sign-in link');
   }
  };},
  async waitForEvent(name){assert.equal(name,'download');return {suggestedFilename:()=>'warehouse.json',failure:async()=>null};}
 };
 return {page,actions};
}

(async()=>{
 for(const mobile of [true,false]){
  const {page,actions}=panelPage(mobile),stages=[];
  await downloadProject(page,mobile,stage=>stages.push(stage));
  await page.locator('#guestSignin').click();
  assert.deepEqual(actions,mobile?['#panelToggle','#acsTabShow','#bJson','#projectPanelClose','#guestSignin']:['#acsTabShow','#bJson','#guestSignin']);
  assert.deepEqual(stages,mobile?['open_project_sheet','open_export_tab','json_download','close_project_sheet']:['open_export_tab','json_download']);
 }
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'acs-guest-stage-'));
 try{
  const report=progressRecorder(dir);
  report.begin('browser_launch');report.begin('local_save',393);report.begin('reload_warehouse',393);
  const error=report.failure(Object.assign(new Error('synthetic-private-payload'),{name:'TimeoutError'}));
  let saved=fs.readFileSync(path.join(dir,'progress.json'),'utf8');
  assert.ok(!saved.includes('synthetic-private-payload')&&!error.message.includes('synthetic-private-payload'));
  const failed=JSON.parse(saved);assert.deepEqual(failed.active,{stage:'reload_warehouse',width:393});
  assert.deepEqual(failed.completed.map(s=>s.stage),['browser_launch','local_save']);assert.equal(failed.status,'failed');
  assert.equal(failed.error,'TimeoutError');assert.equal(error.guestProgress.status,'failed');
  const next=progressRecorder(dir);next.begin('write_complete_evidence');next.success();
  const passed=JSON.parse(fs.readFileSync(path.join(dir,'progress.json'),'utf8'));
  assert.equal(passed.status,'passed');assert.equal(passed.active,null);assert.equal(passed.completed.length,1);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
 console.log('PASS public guest monitor: real mobile sheet controls, desktop export, failure stage and redaction, independent completed evidence.');
})().catch(error=>{console.error(error);process.exitCode=1;});
