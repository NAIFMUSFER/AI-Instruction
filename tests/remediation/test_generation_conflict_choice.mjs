import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// A paid generation finished after the owner saved a manual edit (another tab).
// The shipped job handler must show a plain Arabic two-option choice, never a
// raw code, never silently discard the paid version and never write it over the
// manual edit. Choosing makes no paid request; the other option stays recoverable.
const source=fs.readFileSync('public/app/ui/connected-workspace.mjs','utf8');
const start=source.indexOf('async function handleJob(');
const handlerSource=source.slice(start,source.indexOf('function download(',start));
assert.ok(start>0&&handlerSource.length>0,'job handler source found');

const JOB='33333333-3333-4333-8333-333333333333';
const conflict=(extra={})=>({id:JOB,state:'FAILED',error_code:'GENERATION_CONFLICT',
  error_message:'حُفظ تعديل أحدث أثناء التوليد، فاحتفظنا بالنسخة المولّدة منفصلة دون أن تستبدل تعديلك. اختر ما تريد اعتماده؛ الخيار الآخر يبقى محفوظًا، ولن يُحسب توليد جديد.',
  phase:'REVIEW',provider_calls:1,can_resume:false,revision_id:null,reference_revision_id:'R1',
  choice:{kind:'generated_version',options:['keep_edit','use_generated'],current_head:'R2',adopted_revision_id:null,generated_summary:{levels:1,rooms:2}},...extra});

function setup({versions=[]}={}){
  const nodes=new Map(),requests=[],statuses=[],refreshed=[],storage=new Map([['job','x']]);
  const node=id=>{if(!nodes.has(id))nodes.set(id,{id,hidden:id==='cwChoice'||id==='cwGeneratedVersions',dataset:{},children:[],textContent:'',
    replaceChildren(){this.children=[];},append(child){this.children.push(child);},addEventListener(name,fn){this['on'+name]=fn;}});return nodes.get(id);};
  const context=vm.createContext({
    $:node,pendingJob:JOB,pollTimer:null,state:{head:'R2',revision_id:'R2'},
    stopProgress(){},clearTimeout(){},setTimeout(){},progressPhase(){},setBusy(){},safeError(e){statuses.push(['error',e.message]);},
    jobKey:()=>'job',localStorage:{removeItem:key=>storage.delete(key),setItem:(key,value)=>storage.set(key,value)},
    status:(text,error)=>statuses.push([error?'error':'info',text]),
    refresh:async rid=>{refreshed.push(rid??'head');},
    showComparison(){},
    el:(tag,text,parent)=>{const n={tag,textContent:text,dataset:{},addEventListener(name,fn){this['on'+name]=fn;}};parent?.append(n);return n;},
    run:async fn=>fn(),
    api:async body=>{requests.push(body);
      if(body.action==='adopt_generated')return {ok:true,revision_id:'R3'};
      if(body.action==='generated_versions')return {ok:true,versions};
      throw new Error('unexpected '+body.action);},
  });
  vm.runInContext(handlerSource,context);
  return {context,node,requests,statuses,refreshed,storage};
}
const plain=value=>JSON.parse(JSON.stringify(value));  // objects from the vm realm
const rawCode=/[A-Z][A-Z0-9]*_[A-Z0-9_]+/;
const paid=requests=>requests.filter(r=>['generate','chat_edit','resume'].includes(r.action));

{
  const t=setup();
  await t.context.handleJob(conflict());
  const shown=t.statuses.map(s=>s[1]).join(' ');
  assert.equal(t.node('cwChoice').hidden,false,'the owner is offered an explicit two-option choice');
  assert.equal(t.node('cwChoice').dataset.job,JOB,'the choice is bound to the paid job');
  assert.ok(!rawCode.test(shown),'no raw error code is shown: '+shown);
  assert.ok(shown.includes('تعديلك')&&shown.includes('النسخة المولّدة'),'plain Arabic names both options');
  assert.equal(t.context.pendingJob,null,'the finished job no longer blocks new work');
  assert.deepEqual(t.refreshed,['head'],'the current head (the manual edit) stays on screen');
  assert.equal(t.requests.length,0,'showing the choice makes no request at all');
  console.log('PASS: a conflict shows a plain Arabic keep-or-use choice without a raw code');
}
{
  const t=setup();
  await t.context.handleJob(conflict());
  await t.context.useGenerated(t.node('cwChoice').dataset.job);
  assert.deepEqual(plain(t.requests.filter(r=>r.action==='adopt_generated')),
    [{action:'adopt_generated',job_id:JOB,expected_head:'R2',confirmed:true}],'one explicit, head-bound adoption');
  assert.equal(paid(t.requests).length,0,'choosing the generated version starts no paid work');
  assert.deepEqual(t.refreshed,['head','R3'],'the adopted version is opened');
  assert.equal(t.node('cwChoice').hidden,true);
  assert.ok(t.statuses.at(-1)[1].includes('يمكن استعادته'),'the manual edit is said to be recoverable');
  console.log('PASS: "use the generated version" adopts it once, with no new generation');
}
{
  const t=setup({versions:[{job_id:JOB,created_at:'2026-11-25T00:00:00Z',adopted_revision_id:null}]});
  await t.context.handleJob(conflict());
  await t.context.keepEdit();
  assert.equal(t.requests.some(r=>r.action==='adopt_generated'),false,'keeping the edit writes nothing');
  assert.equal(paid(t.requests).length,0);
  assert.equal(t.node('cwChoice').hidden,true);
  const kept=t.node('cwGeneratedVersions');
  assert.equal(kept.hidden,false,'the generated version stays reachable after keeping the edit');
  const button=kept.children.find(c=>c.tag==='button');
  assert.ok(button,'a recovery button is offered');
  await button.onclick();
  assert.deepEqual(plain(t.requests.filter(r=>r.action==='adopt_generated').map(r=>r.job_id)),[JOB],'it can still be adopted later');
  console.log('PASS: "keep my edit" changes nothing and leaves the generated version recoverable');
}
{
  const t=setup();
  await t.context.handleJob(conflict({choice:{...conflict().choice,adopted_revision_id:'R3'}}));
  assert.equal(t.node('cwChoice').hidden,true,'an already adopted version is not offered twice');
  assert.deepEqual(t.refreshed,['R3']);
  console.log('PASS: a choice already made elsewhere is shown as done');
}
{
  const t=setup();
  t.context.$('cwResumeJob');
  await t.context.handleJob({id:JOB,state:'FAILED',error_code:'PLAN_LAYOUT_INCOMPLETE',error_message:'لم يكتمل توزيع الغرف.',can_resume:true,choice:null});
  assert.equal(t.node('cwChoice').hidden,true,'ordinary failures keep their existing handling');
  assert.equal(t.node('cwResumeJob').hidden,false);
  console.log('PASS: ordinary failed jobs are unchanged');
}
