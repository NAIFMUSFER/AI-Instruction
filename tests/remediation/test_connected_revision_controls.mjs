import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Execute the shipped control guards and roof event handler. In CI the actual
// browser witnessed a historical selection being ignored during a comparison,
// followed by the previous loaded head enabling the roof mutation button.
const source=fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8');
const between=(start,end)=>source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
const controlSource=between('function setBusy(', 'async function api(')
  +between('async function run(', 'function clearViewer(')
  +between('function briefProgram(', 'async function renderState(')
  +between("{const roof=el('button'", "  $('cwRestore').addEventListener");
const defer=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
function setup(){
  const nodes=new Map(),requests=[],errors=[];
  const $=id=>{
    if(!nodes.has(id))nodes.set(id,{id,disabled:false,checked:false,hidden:false,value:'',dataset:{},parentNode:{},setAttribute(){},addEventListener(name,fn){this[name]=fn;}});
    return nodes.get(id);
  };
  const mutationIds=['cwApprove','cwChatSubmit','cwRestore','cwSaveGeometry','cwLock','cwRoof'];
  $('cwRevision').value='R2';$('cwApproveConfirm').checked=true;$('cwEditApprovalNotice').hidden=true;$('cwCompareRevision').value='R1';
  const context=vm.createContext({$,root:{setAttribute(){},querySelectorAll(selector){return selector==='[data-mutate]'?mutationIds.map($):[$('cwShow3D'),$('exportGLTF')];},querySelector(){return $('exportReview');}},
    state:{head:'R2',revision_id:'R2',authority:{can_approve_concept:true},history:[{revision_id:'R1',state:'APPROVED'},{revision_id:'R2',state:'DRAFT'}]},
    packet:{locks:{rooms:[]}},selected:{source:{template:'floor',room_id:'room'}},objectSelection:null,busy:false,pendingJob:null,planUpload:{sync(){}},
    el:()=>$('cwRoof'),safeError:e=>errors.push(e.message),status(){},api:async body=>{requests.push(body);return {};},renderState:async()=>{}});
  vm.runInContext(controlSource,context);
  return {context,$,requests,errors};
}

{
  const test=setup(),pending=defer();let selectedReads=0;
  const compare=test.context.run(()=>pending.promise);
  // Force the exact old failure independently of browser actionability: a
  // historical option differs from the loaded head while work is in flight.
  test.$('cwRevision').value='R1';
  await test.context.run(async()=>{selectedReads++;});
  assert.equal(selectedReads,0,'the current serialized runner rejects a second concurrent action');
  pending.resolve();await compare;
  for(const id of ['cwRoof','cwApprove','cwChatSubmit','cwSaveGeometry','cwLock'])assert.equal(test.$(id).disabled,true,id+' must fail closed when visible selection differs from loaded head');
  const history=JSON.stringify(test.context.state);
  await test.$('cwRoof').click();
  assert.equal(test.requests.length,0,'even a programmatic stale roof click must make zero mutation requests');
  assert.equal(JSON.stringify(test.context.state),history,'refusal cannot mutate selected state/history');
  assert.ok(test.errors.some(message=>message.includes('آخر نسخة')),'a stale click explains how to recover');
  console.log('PASS: ignored in-flight historical selection cannot enable or issue a head mutation');
}
{
  const test=setup();test.context.setBusy(true);
  assert.equal(test.$('cwRevision').disabled,true,'visible revision selection cannot be silently dropped during serialized work');
  test.context.setBusy(false);
  assert.equal(test.$('cwRevision').disabled,false,'revision selection returns when work completes');
  assert.equal(test.$('cwRoof').disabled,false,'a loaded current head permits the supported roof action');
  await test.$('cwRoof').click();assert.equal(test.requests.length,1);assert.equal(test.requests[0].expected_head,'R2');
  console.log('PASS: busy selection is disabled, then the loaded head remains usable');
}
{
  const test=setup();test.$('cwRevision').value='R1';test.context.state.revision_id='R1';test.context.setBusy(false);
  assert.equal(test.$('cwRoof').disabled,true);assert.equal(test.$('cwRestore').disabled,false,'loaded history can be explicitly restored as a new draft');
  assert.equal(test.$('cwShow3D').disabled,false,'approved loaded history remains readable/exportable');
  await test.$('cwRoof').click();assert.equal(test.requests.length,0);
  test.$('cwRevision').value='R2';test.context.setBusy(false);
  assert.equal(test.$('cwRestore').disabled,true,'a not-yet-loaded selection cannot restore a different revision');
  assert.equal(test.$('cwShow3D').disabled,true,'a not-yet-loaded selection cannot export a different revision');
  console.log('PASS: history stays readable and restorable only for the loaded selection');
}
{
  const test=setup();test.$('cwRoof').dataset.userAuthored='true';test.context.setBusy(false);assert.equal(test.$('cwRoof').disabled,true);
  test.$('cwRoof').dataset.userAuthored='false';test.context.pendingJob='job';test.context.setBusy(false);assert.equal(test.$('cwRoof').disabled,true);
  console.log('PASS: authored roofs and pending jobs keep existing mutation restrictions');
}
