import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),SEG=require('../lib/js_segment.js'),APP=require('../lib/app_source.js');
const source=APP.stripModuleSyntax(fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8'),'connected');
const fn=name=>{const match=new RegExp('^(?:async )?function '+name+'\\(','m').exec(source);assert.ok(match,'actual shipped '+name);const tail=source.slice(match.index),row=SEG.topLevelStatements(tail)[0];return tail.slice(row.start,row.end);};
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,{hidden:false,disabled:false,checked:false,value:'R1',textContent:''});return nodes.get(id);};
const sourceTuple={kind:'element',collection:'objects',template:'ground',room_id:'porch',level_index:0,element_id:'column-1'};
const chosen={revision_id:'R1',model_hash:'hash1',source_id:'source-column',source:sourceTuple,repeat_index:0};
const actions={revision_id:'R1',model_hash:'hash1',requires_new_draft:true,items:[{template:'ground',room_id:'porch',object_id:'column-1',level_index:0,kind:'column',count:1,supported:true,reason:null}],truncated:false};
const requests=[],messages=[];const ctx=vm.createContext({$,root:{},state:{revision_id:'R1',head:'R1',object_actions:actions},packet:{revision:{id:'R1',model_hash:'hash1'}},revisionEpoch:3,viewerEpoch:2,objectSelection:null,busy:false,pendingJob:null,
 api:async(body,commands)=>{requests.push({body,commands});return{revision_id:'R2'};},renderState:async()=>{ctx.objectSelection=null;},status:text=>messages.push(text),step(){}});
vm.runInContext(['loadedRevisionSelected','headRevisionSelected','objectRemovalTarget','selectApprovedObject','syncObjectSelection','removeSelectedObject'].map(fn).join('\n'),ctx);
ctx.selectApprovedObject(chosen);assert.equal($('cwObjectRemove').disabled,true,'approved object needs explicit new-draft confirmation');
await assert.rejects(ctx.removeSelectedObject(),/أكد/);assert.equal(requests.length,0);
$('cwObjectConfirm').checked=true;ctx.syncObjectSelection();assert.equal($('cwObjectRemove').disabled,false);
await ctx.removeSelectedObject();assert.equal(requests.length,1);assert.equal(requests[0].commands,true);assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body)),{action:'remove_object',expected_head:'R1',room_ref:['ground','porch'],object_id:'column-1',confirm_new_draft:true});
assert.match(messages.at(-1),/مسودة/);
for(const mutation of [()=>{ctx.state.head='R2';},()=>{ctx.revisionEpoch++;},()=>{ctx.viewerEpoch++;},()=>{$('cwRevision').value='old';},()=>{ctx.state.object_actions={...actions,model_hash:'other'};},()=>{ctx.state.object_actions={...actions,items:[],truncated:true};}]){
 ctx.state={head:'R1',revision_id:'R1',object_actions:actions};ctx.revisionEpoch=3;ctx.viewerEpoch=2;$('cwRevision').value='R1';ctx.selectApprovedObject(chosen);$('cwObjectConfirm').checked=true;mutation();ctx.syncObjectSelection();assert.equal($('cwObjectRemove').disabled,true);await assert.rejects(ctx.removeSelectedObject());assert.equal(requests.length,1,'stale or unbound selection sends zero commands');
}
ctx.state={head:'R1',revision_id:'R1',object_actions:actions};ctx.revisionEpoch=3;ctx.viewerEpoch=2;$('cwRevision').value='R1';
for(const item of [{...actions.items[0],supported:false,reason:'OBJECT_TEMPLATE_SHARED'},{...actions.items[0],count:2},{...actions.items[0],kind:'stairs'}]){
 ctx.state.object_actions={...actions,items:[item]};ctx.selectApprovedObject(chosen);$('cwObjectConfirm').checked=true;ctx.syncObjectSelection();assert.equal($('cwObjectRemove').disabled,true);await assert.rejects(ctx.removeSelectedObject());
}
ctx.state.object_actions=actions;ctx.selectApprovedObject(chosen);$('cwObjectConfirm').checked=true;ctx.selectApprovedObject(null);assert.equal($('cwObjectSelection').hidden,true);assert.equal($('cwObjectConfirm').checked,false);
vm.runInContext(fn('contextDefaultsText'),ctx);
const marked={...actions.items[0],context_detail_provenance:{schema:'acs.context-detail/1',source:'system_default',conceptual_only:true,context:'porch',assumptions:['synthetic']}};
assert.match(ctx.contextDefaultsText({...actions,items:[marked]},ctx.packet.revision),/1 أعمدة/);
assert.equal(ctx.contextDefaultsText({...actions,items:[],generated_count:999},ctx.packet.revision),'','report counters cannot fabricate geometry');
assert.equal(ctx.contextDefaultsText({...actions,revision_id:'foreign',items:[marked]},ctx.packet.revision),'');
assert.match(ctx.contextDefaultsText({...actions,truncated:true,items:[marked]},ctx.packet.revision),/جزئية/);
ctx.state={head:'R1',revision_id:'R1',object_actions:actions};ctx.selectApprovedObject(chosen);$('cwObjectConfirm').checked=true;
ctx.api=async()=>({revision_id:'R2',revision_comparison_unavailable:{reason:'OPTION_TYPOLOGY_UNKNOWN'}});
await ctx.removeSelectedObject();assert.match(messages.at(-1),/نوع المبنى غير محدد.*فرق حذف العنصر محفوظ/,'optional scorecard comparison loss is disclosed without inventing a typology');
// Execute the actual artifact-loader race guard: a late R1 response after the
// selected revision/epoch becomes R2 cannot mount even a valid old artifact.
let release,mounted=0;ctx.viewerDispose=null;$('cwViewer').replaceChildren=()=>{};$('cwViewer').dataset={};
ctx.packet.projections=[{level_index:0}];ctx.showApprovedGLTF=async()=>{mounted++;return()=>{};};ctx.api=async()=>new Promise(resolve=>{release=resolve;});
vm.runInContext(fn('clearViewer')+'\n'+fn('exportFile'),ctx);
const late=ctx.exportFile('gltf',true);ctx.revisionEpoch++;ctx.viewerEpoch++;ctx.state={head:'R2',revision_id:'R2'};ctx.packet={revision:{id:'R2',model_hash:'hash2'}};
release({data_base64:'old R1 bytes'});await late;assert.equal(mounted,0,'late R1 must never mount after R2');assert.equal(ctx.objectSelection,null);
console.log('PASS contextual object controls: exact source summary, draft confirmation, stale revision/epoch/selection, unsupported scope and provider-free command');
