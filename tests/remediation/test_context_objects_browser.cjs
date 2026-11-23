'use strict';
// Actual shipped private workspace, real compiler/store/commands, synthetic identity.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process'),PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const output=path.resolve(process.env.ACS_CONTEXT_OUTPUT||path.join(os.tmpdir(),'acs-context-objects'));fs.mkdirSync(output,{recursive:true});
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function bounded(promise,label,ms=15000){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error(label+' timed out after '+ms+'ms')),ms);})]);}finally{clearTimeout(timer);}}
const state=page=>page.evaluate(async()=>{const s=await window.ACS_AUTH.freshSession();return window.ACS_AUTH.acsFetchJSON('/v1/projects/'+window.ACS.projectId+'/workspace',{action:'state'},s.access_token);});
const command=(page,body)=>page.evaluate(async body=>{const s=await window.ACS_AUTH.freshSession();return window.ACS_AUTH.acsFetchJSON('/v1/projects/'+window.ACS.projectId+'/plan/commands',body,s.access_token);},body);
const approved=(view,id)=>view.history.find(row=>row.revision_id===id)?.state==='APPROVED';
async function idle(page){await page.waitForFunction(()=>document.querySelector('#designWorkspace')?.getAttribute('aria-busy')==='false');}
async function show(page){await page.locator('[data-step="4"]').click();await page.locator('#cwShow3D').click();await page.waitForFunction(()=>document.querySelector('#cwViewer')?.acsViewer?.objectGroups?.length>0);await idle(page);await page.locator('[data-view="aerial"]').click();await page.waitForFunction(()=>!document.querySelector('#cwViewer').acsViewer.activeAnimation);}
async function pick(page,record){
 await page.locator('#cwViewer canvas').scrollIntoViewIfNeeded();
 const point=await page.evaluate(async record=>{
  const stats=document.querySelector('#cwViewer').acsViewer.inspect(),group=stats.objectGroups.find(g=>g.source.template===record.template&&g.source.room_id===record.room_id&&g.source.element_id===record.object_id&&g.source.level_index===record.level_index);
  if(!group)throw new Error('Actual canonical object group missing');
  const THREE=await import('three'),camera=new THREE.PerspectiveCamera(stats.fov,stats.aspect,.001,10000);camera.position.fromArray(stats.camera);camera.lookAt(new THREE.Vector3().fromArray(stats.target));camera.updateMatrixWorld();
  const p=new THREE.Vector3().fromArray(group.center).project(camera),box=document.querySelector('#cwViewer canvas').getBoundingClientRect();return {x:box.x+(p.x+1)*box.width/2,y:box.y+(1-p.y)*box.height/2,canvas:{left:box.left,right:box.right,top:box.top,bottom:box.bottom},viewport:{width:innerWidth,height:innerHeight}};
 },record);
 assert.ok(point.x>Math.max(0,point.canvas.left)&&point.x<Math.min(point.viewport.width,point.canvas.right)&&point.y>Math.max(0,point.canvas.top)&&point.y<Math.min(point.viewport.height,point.canvas.bottom),'canonical object pick must lie inside the visible canvas and viewport');
 await page.mouse.click(point.x,point.y);await page.locator('#cwObjectSelection').waitFor({state:'visible'});await page.waitForFunction(id=>document.querySelector('#cwObjectDescription')?.textContent.includes(id),record.object_id);
}
(async()=>{let browser,child,page;const evidence=[];try{
 browser=await PW.launch({headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 for(const width of [393,1440]){
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'acs-context-')),port=8893;let backend='';
  child=spawn(process.env.PYTHON||'python',['tests/remediation/context_objects_browser_server.py','--port',String(port),'--database',path.join(tmp,'plans.sqlite3')],{cwd:ROOT,stdio:['ignore','pipe','pipe']});child.stdout.on('data',b=>backend=(backend+String(b)).slice(-12000));child.stderr.on('data',b=>backend=(backend+String(b)).slice(-12000));
  let ready=false;for(let n=0;n<60;n++){try{if((await fetch('http://127.0.0.1:'+port+'/health')).ok){ready=true;break;}}catch(e){}await delay(250);}assert.ok(ready,'fixture backend failed: '+backend);
  const context=await browser.newContext({viewport:{width,height:width===393?852:900}});page=await context.newPage();page.setDefaultTimeout(15000);
  const errors=[],requests=[],foreign=[];let holdRevision=null,releaseArtifact,startedArtifact,finishedArtifact;
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(url.hostname==='acs-engine.onrender.com'){
    const body=req.method()==='POST'&&/\/(workspace|plan\/commands)$/.test(url.pathname)?req.postDataJSON():null;
    if(body)requests.push({path:url.pathname,action:body.action,body});
    const response=await route.fetch({url:'http://127.0.0.1:'+port+url.pathname+url.search});
    if(body?.action==='artifact'&&body.revision_id===holdRevision){
     startedArtifact?.();await bounded(new Promise(resolve=>{releaseArtifact=resolve;}),'held artifact release');
     await route.fulfill({response});finishedArtifact?.();return;
    }
    return route.fulfill({response});
   }
   if(url.hostname!=='acs-ui.test'){foreign.push(url.origin);return route.abort();}
   let file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
   if(url.pathname.startsWith('/vendor/three@0.160.0/'))file=path.join(ROOT,'node_modules','three',url.pathname.slice('/vendor/three@0.160.0/'.length));
   if(!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
   return route.fulfill({headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP},body:fs.readFileSync(file)});
  });
  await page.goto('https://acs-ui.test/?signin=1');await page.locator('#lgEmail').fill('fixture@example.test');await page.locator('#lgPassword').fill('fixture-password');await page.locator('#lgGo').click();
  await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
  const first=await state(page),r1=first.head;assert.ok(approved(first,r1));
  const column=first.object_actions.items.find(row=>row.kind==='column'&&row.supported);assert.ok(column);assert.ok(column.context_detail_provenance);
  assert.match(await page.locator('#cwAssumptions').textContent(),/عناصر افتراضية/);
  await show(page);
  for(const kind of ['railing','plant']){
   const record=first.object_actions.items.find(row=>row.kind===kind&&row.supported);assert.ok(record,'synthetic fixture includes canonical '+kind);
   await pick(page,record);const group=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect().detailGroupSize);assert.ok(group>1,'all '+kind+' components select the same canonical object');
  }
  await pick(page,column);assert.equal(await page.locator('#cwObjectRemove').isDisabled(),true);
  assert.equal(requests.filter(r=>r.action==='remove_object').length,0,'selecting an object makes no mutation');
  await page.locator('#cwObjectConfirm').check();assert.equal(await page.locator('#cwObjectRemove').isDisabled(),false);
  await page.locator('#cwObjectSelection').screenshot({path:path.join(output,'context-'+width+'-confirmed.png')});
  await page.locator('#cwObjectRemove').click();await idle(page);
  assert.match(await page.locator('#cwStatus').textContent(),/نوع المبنى غير محدد.*فرق حذف العنصر محفوظ/);
  const removed=await state(page),r2=removed.head;assert.notEqual(r2,r1);assert.equal(approved(removed,r2),false);assert.equal(approved(removed,r1),true);
  assert.ok(!removed.object_actions.items.some(row=>row.object_id===column.object_id&&row.room_id===column.room_id&&row.template===column.template));
  assert.equal(await page.locator('#cwViewer canvas').count(),0,'new draft immediately clears old approved geometry');
  const deletion=requests.find(r=>r.action==='remove_object');assert.equal(deletion.body.confirm_new_draft,true);assert.equal(deletion.body.expected_head,r1);assert.equal(deletion.body.object_id,column.object_id);
  assert.equal(requests.some(r=>['generate','chat_edit','resume'].includes(r.action)),false,'object removal never starts a paid job');
  await page.reload();await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
  const reopened=await state(page);assert.equal(reopened.head,r2);assert.deepEqual(reopened.object_actions,removed.object_actions,'reopen does not recreate removed defaults');
  // A late historical artifact cannot reappear after the actual user leaves 3D.
  await page.locator('#cwRevision').selectOption(r1);await idle(page);await page.locator('[data-step="4"]').click();
  holdRevision=r1;const started=new Promise(resolve=>{startedArtifact=resolve;}),finished=new Promise(resolve=>{finishedArtifact=resolve;});await page.locator('#cwShow3D').click();await bounded(started,'historical artifact dispatch');
  await page.locator('[data-step="3"]').click();
  // The shipped run(exportFile) is still pending. Its finally sets aria-busy
  // false only after the released response has passed the actual epoch guard.
  assert.equal(await page.locator('#designWorkspace').getAttribute('aria-busy'),'true','the artifact loader remains pending before its response');
  releaseArtifact();holdRevision=null;await bounded(finished,'historical artifact response delivery');await idle(page);
  assert.equal(await page.locator('#cwViewer canvas').count(),0);assert.equal(await page.locator('#cwObjectSelection').isVisible(),false,'late R1 cannot restore an actionable source');
  await page.locator('#cwRevision').selectOption(r2);await idle(page);await page.locator('#cwApproveConfirm').check();await page.locator('#cwApprove').click();await idle(page);await show(page);
  const current=await page.evaluate(()=>document.querySelector('#cwViewer').acsViewer.inspect());assert.equal(current.revisionId,r2);assert.ok(!current.objectGroups.some(g=>g.source.element_id===column.object_id));
  await page.locator('#cwViewer').screenshot({path:path.join(output,'context-'+width+'-removed.png')});
  // Capability is not authorization: a real room lock still blocks this action.
  const remaining=(await state(page)).object_actions.items.find(row=>row.kind==='column'&&row.supported);assert.ok(remaining);
  const locked=(await command(page,{action:'set_room_lock',expected_head:r2,room_ref:[remaining.template,remaining.room_id],locked:true})).result;
  await page.locator('#cwReload').click();await idle(page);await page.locator('[data-step="3"]').click();await page.locator('#cwApproveConfirm').check();await page.locator('#cwApprove').click();await idle(page);await show(page);await pick(page,remaining);await page.locator('#cwObjectConfirm').check();await page.locator('#cwObjectRemove').click();await idle(page);
  assert.match(await page.locator('#cwStatus').textContent(),/مقفل|قفل/);const denied=await state(page);assert.equal(denied.head,locked.head);assert.ok(denied.object_actions.items.some(row=>row.object_id===remaining.object_id));
  const provider=await(await fetch('http://127.0.0.1:'+port+'/test-stats')).json();assert.deepEqual(provider,{generation:0,chat:0});assert.deepEqual(errors,[]);assert.deepEqual(foreign,[]);
  evidence.push({viewport:{width,height:width===393?852:900},r1,r2,removed_source:column,final_revision:denied.head,provider_calls:provider,request_actions:requests.map(r=>r.action),claim:'Synthetic fixture, actual shipped UI/compiler/commands; no live provider or physical mobile test'});
  await context.close();await new Promise(resolve=>{child.once('exit',resolve);child.kill('SIGTERM');});child=null;
 }
 fs.writeFileSync(path.join(output,'context-objects-browser.json'),JSON.stringify(evidence,null,2));console.log('PASS contextual object journey: real ray selection, explicit draft confirmation, exact removal/reopen, late historical artifact, lock refusal, zero provider jobs');
}catch(error){fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:error.message,completed:evidence},null,2));if(page)await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});throw error;}finally{if(browser)await browser.close();if(child)child.kill('SIGTERM');}})().catch(error=>{console.error(error);process.exitCode=1;});
