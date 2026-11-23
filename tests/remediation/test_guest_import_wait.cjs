'use strict';
// Real JSON handler and the browser test's wait predicate; only file I/O timing
// and the renderer boundary are controlled. No browser/provider/network calls.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const APP=require('../lib/app_source.js'),SEG=require('../lib/js_segment.js');
function declaration(source,name){
 const statement=SEG.topLevelStatements(source).map(row=>source.slice(row.start,row.end))
  .find(row=>new RegExp('^(?:async )?function '+name+'\\(').test(SEG.head(row)));
 assert.ok(statement,'actual function '+name+' exists');return statement;
}
const app=APP.stripModuleSyntax(fs.readFileSync('public/app/ui/workspace-ui-wiring.js','utf8'),'wiring');
const browser=fs.readFileSync('tests/remediation/test_guest_workspace.cjs','utf8');
const oldModel={meta:{name:'authored-roof-1280'},site:{w:24},levels:[{index:1,template:'roof',kind:'roof',auto:false}],floors:{roof:{rooms:[]}}};
const recovered={meta:{name:'legacy-recovery-1280'},site:{w:24},levels:[{index:0,template:'g'}],floors:{g:{rooms:[]}}};
const info={textContent:''};let visible=oldModel,release,readStarted=false;
const context={window:{ACS:{guest:true,exportModel:()=>visible}},document:{getElementById:id=>id==='impInfo'?info:{value:'1'}},setModel:model=>{visible=model;}};
vm.createContext(context);vm.runInContext(declaration(app,'handleImport')+'\n'+declaration(browser,'recoveryImportReady')+'\nObject.assign(globalThis,{handleImport,recoveryImportReady});',context);
(async()=>{
 const pending=context.handleImport({name:'restored-local.json',text(){readStarted=true;return new Promise(resolve=>{release=resolve;});}});
 assert.equal(readStarted,true,'actual import handler has started its asynchronous read');
 assert.equal(visible,oldModel,'the authored model remains visible until file reading completes');
 assert.equal(visible.site.w,24,'old width-only wait is already true for the wrong model');
 assert.equal(context.recoveryImportReady(recovered.meta.name),false,'pending import must not be marked ready merely because the previous model also has width24');
 release(JSON.stringify(recovered));await pending;
 assert.deepEqual(JSON.parse(JSON.stringify(visible)),recovered,'actual handler commits the exact legacy JSON');
 assert.equal(context.recoveryImportReady(recovered.meta.name),true,'wait becomes ready after the intended import commits');
 assert.equal(context.recoveryImportReady('another-draft'),false,'unrelated model identity never satisfies this wait');
 console.log('PASS guest import wait: pending actual file.text read cannot satisfy the recovery-model identity guard');
})().catch(error=>{console.error(error);process.exitCode=1;});
