'use strict';
// Actual shipped UI + actual workspace routes, with a controlled CI-only identity
// and provider. The backend lifecycle is also tested independently in Python.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn,execFileSync}=require('node:child_process');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
// Read the actual authorized workspace state, independently of visible button labels.
async function workspaceState(page){return page.evaluate(async()=>{const session=await window.ACS_AUTH.freshSession();return window.ACS_AUTH.acsFetchJSON('/v1/projects/'+window.ACS.projectId+'/workspace',{action:'state'},session.access_token);});}
const roofRows=view=>JSON.parse(view.review_packet.payload_json).projections.filter(p=>p.level_kind==='roof');
const revisionState=(view,id=view.head)=>view.history.find(row=>row.revision_id===id)?.state;
function assertConceptApproval(view,stage){
 const blockers=(view.review_findings||[]).slice(0,16).map(issue=>{
  const requirement=view.requirements?.find(row=>row.id===issue.requirement_id);
  return {code:issue.code,requirement_id:issue.requirement_id,metric:requirement?.metric,expected:requirement?.expected};
 });
 assert.equal(view.authority?.can_approve_concept,true,stage+' must satisfy the actual canonical review: '+JSON.stringify(blockers));
}

(async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'acs-ui-')),port=8891;
 const child=spawn(process.env.PYTHON||'python',['tests/remediation/connected_workspace_browser_server.py','--port',String(port),'--database',path.join(tmp,'plans.sqlite3')],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
 let backendLog='';const appendBackend=b=>{backendLog=(backendLog+String(b)).slice(-12000);};
 child.stdout.on('data',appendBackend);child.stderr.on('data',appendBackend);
 let browser,activePage,activeCase;
 const networkEvents=[],pageErrors=[];
 const recordNetwork=event=>{networkEvents.push(event);if(networkEvents.length>36)networkEvents.shift();};
 try{
  const pdfFixture=path.join(tmp,'two-page-plan.pdf');
  execFileSync(process.env.PYTHON||'python',['-c',`import sys
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
w=PdfWriter()
for x in (20,100):
 p=w.add_blank_page(width=300,height=300)
 s=DecodedStreamObject(); s.set_data(('0 0 0 RG %s 20 80 100 re S' % x).encode())
 p[NameObject('/Contents')]=w._add_object(s)
w.write(sys.argv[1])`,pdfFixture]);
  let ready=false;for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:'+port+'/health')).ok){ready=true;break;}}catch(e){}await delay(250);}
  assert.ok(ready,'fixture backend did not start: '+backendLog);browser=await PW.launch();
  for(const {width,noWebGL} of [{width:393},{width:1280},{width:393,noWebGL:true}]){
   const context=await browser.newContext({viewport:{width,height:900},acceptDownloads:true}),page=await context.newPage();
   activePage=page;activeCase={width,noWebGL:!!noWebGL};networkEvents.length=0;pageErrors.length=0;
   let blockJobPoll=false,comparisonPause=null,comparisonStarted=null;
   const workspaceActions=[];
   const errors=[];page.on('pageerror',e=>{errors.push(e.message);pageErrors.push(e.message.slice(0,1000));if(pageErrors.length>12)pageErrors.shift();});
   if(noWebGL)await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/i.test(type)?null:original.call(this,type,...args);};});
   await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.hostname==='acs-engine.onrender.com'){
      const body=req.method()==='POST'&&/\/(?:workspace|plan\/commands)$/.test(url.pathname)?req.postDataJSON():null;
      if(url.pathname.endsWith('/workspace'))workspaceActions.push(body?.action);
      if(comparisonPause&&url.pathname.endsWith('/plan/commands')&&body?.action==='compare'){comparisonStarted?.();await comparisonPause;}
      if(blockJobPoll&&url.pathname.endsWith('/workspace')&&req.method()==='POST'&&req.postDataJSON()?.action==='job'){recordNetwork({action:body?.action,outcome:'intentional_poll_disconnect'});return route.abort('failed');}
      const response=await route.fetch({url:'http://127.0.0.1:'+port+url.pathname+url.search});
      if(body){
       const receipt={action:body.action,status:response.status()};
       try{const reply=await response.json();receipt.error_code=reply.error?.code;receipt.head=reply.head;receipt.revision_id=reply.revision_id;if(reply.job){receipt.job={};for(const key of ['id','state','phase','revision_id','error_code','can_resume'])receipt.job[key]=reply.job[key];}}catch(e){receipt.invalid_json=true;}
       recordNetwork(receipt);
      }
      return route.fulfill({response});
    }
    if(url.hostname!=='acs-ui.test')return route.abort();
    const f=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(f)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(f)});
   });
   await page.goto('https://acs-ui.test/?signin=1');
   assert.equal(await page.locator('#app canvas').count(),0,'public sign-in allocates no hidden legacy renderer');
   await page.locator('#lgEmail').fill('fixture@example.test');await page.locator('#lgPassword').fill('fixture-password');await page.locator('#lgGo').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
   await page.locator('#cwNewProject').click();await page.locator('#cwProjectName').fill('مشروع قبول '+width);
   await Promise.all([page.waitForEvent('framenavigated',frame=>frame===page.mainFrame()),page.locator('#cwNewProjectForm button[type=submit]').click()]);
   await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
   assert.equal(await page.locator('#cwProject option:checked').textContent(),'مشروع قبول '+width);
   await page.locator('#cwBrief').waitFor({state:'visible'});
   await page.locator('#cwType').selectOption(width===393?'warehouse':'residential');
   const dimensionEvidence=width===393?'٢٠ متر في ٢٠ متر':'عرض الموقع ٢٠ متر';
   const description=width===393?'🏭 مستودع تجريبي\n٢٠ متر في ٢٠ متر\nعدد الأدوار ١':'🏡 مشروع سكني تجريبي؛ عرض الموقع ٢٠ متر؛ عمق الموقع ٢٠ متر؛ عدد الأدوار ١';
   await page.locator('#cwBrief').fill(description);
   const beforeRead=(await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation;
   await page.locator('#cwReadBrief').click();
   assert.equal(await page.locator('#cwBriefCandidates article').count(),3);
   for(const metric of ['site_width_m','site_depth_m','level_count'])await page.locator('[data-brief-metric="'+metric+'"]').click();
   assert.equal(await page.locator('#cwWidth').inputValue(),'20');
   assert.equal(await page.locator('#cwDepth').inputValue(),'20');
   assert.equal(await page.locator('#cwLevels').inputValue(),'1');
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,beforeRead,'reading or accepting requirements must not call a provider');
   await page.locator('#cwConfirmed').check();await page.locator('#cwWidth').fill('21');
   assert.equal(await page.locator('#cwConfirmed').isChecked(),false,'changing a quantity invalidates confirmation');
   await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();
   assert.ok(await page.locator('#cwBrief').isVisible(),'contradiction must keep the requirements form open');
   assert.ok((await page.locator('#cwStatus').textContent()).includes('تعارض'));
   await page.locator('#cwWidth').fill('20');
   await page.reload();await page.locator('#cwBrief').waitFor({state:'visible'});
   assert.equal(await page.locator('#cwBrief').inputValue(),description,'unsubmitted brief survives reload');
   assert.equal(await page.locator('#cwConfirmed').isChecked(),false,'reopening must not restore confirmation');
   assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false,'brief evidence fits mobile width');
   if(!noWebGL){
    if(width===1280){
     await page.locator('#cwUnits').fill('2');
     await page.locator('#cwUnitsScope').selectOption('total');
     await page.locator('#cwConfirmed').check();
     await page.locator('#cwBriefForm button[type=submit]').click();
     await page.locator('[data-option="A"]').waitFor({state:'visible'});
     assert.ok((await page.locator('[data-residential-detail]').first().textContent()).includes('2 شقق'));
     assert.ok((await page.locator('.cw-options').textContent()).includes('خصوصية الضيوف'));
     assert.equal(await page.locator('[data-option="A"]').isEnabled(),true);
     await page.locator('[data-step="1"]').click();
     await page.locator('#cwUnits').fill('50');await page.locator('#cwConfirmed').check();
     await page.locator('#cwBriefForm button[type=submit]').click();
     assert.equal(await page.locator('[data-option="A"]').isDisabled(),true,'oversized apartment programs must not start paid generation');
     await page.locator('[data-step="1"]').click();await page.locator('#cwUnits').fill('2');
    }
    const inputFile=width===393?path.join(ROOT,'tests/phase7/outputs/warehouse_buffer_depth.png'):pdfFixture;
    await page.locator('#cwStartMode').selectOption('upload');
    await page.locator('#cwPlanFile').setInputFiles(inputFile);
    await page.waitForFunction(()=>!document.querySelector('#cwSaveSource').disabled);
    if(width===1280){assert.equal(await page.locator('#cwPdfPage option').count(),2);const firstPreview=await page.locator('#cwSourcePreview').getAttribute('src');await page.locator('#cwPdfPage').selectOption('2');await page.waitForFunction(()=>!document.querySelector('#cwSaveSource').disabled);assert.notEqual(await page.locator('#cwSourcePreview').getAttribute('src'),firstPreview,'page selection changes the preview');}
    const beforeUpload=(await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation;
    await page.locator('#cwSaveSource').click();
    await page.waitForFunction(()=>document.querySelector('#cwSourceStatus').textContent.includes('حُفظ الأصل'));
    assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,beforeUpload,'uploading does not call the provider');
    const sourceId=await page.locator('#cwSavedSource').inputValue();assert.ok(sourceId);
    await page.reload();await page.waitForFunction(()=>document.querySelector('#cwSavedSource')?.value);
    assert.equal(await page.locator('#cwSavedSource').inputValue(),sourceId,'stored source is available after reload');
    const originalPromise=page.waitForEvent('download');await page.locator('#cwDownloadSource').click();
    const original=await originalPromise;assert.deepEqual(fs.readFileSync(await original.path()),fs.readFileSync(inputFile),'original bytes survive cloud-source roundtrip');
    assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false,'upload fits mobile');
   }
   await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();
   const before=(await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation;
   assert.equal(await page.locator('#cwJobProgress').isVisible(),false,'idle projects show no running activity');
   await page.locator(noWebGL?'[data-option=A]':'#cwGenerateSource').click();await page.locator('#cwRecoverJob').waitFor({state:'visible'});
   await page.locator('#cwJobProgress').waitFor({state:'visible'});
   assert.equal(await page.locator('#cwJobActivity').getAttribute('value'),null,'activity has no invented completion percentage');
   await page.waitForFunction(()=>Number(document.querySelector('#cwJobElapsed').dataset.seconds)>=1);
   const startedAt=await page.locator('#cwJobProgress').getAttribute('data-started-at');
   blockJobPoll=true;await page.reload();
   await page.waitForFunction(()=>document.querySelector('#cwJobProgress')?.dataset.phase==='UNKNOWN');
   assert.equal(await page.locator('#cwJobProgress').getAttribute('data-started-at'),startedAt,'elapsed time keeps the original submission time after reload');
   assert.equal(await page.locator('#cwJobActivity').isVisible(),false,'a failed status fetch must stop claiming current activity');
   assert.ok((await page.locator('#cwJobPhase').textContent()).includes('تعذّر التحقق'));
   blockJobPoll=false;await page.locator('#cwRecoverJob').click();
   await page.locator('#cwReviewContent').waitFor({state:'visible',timeout:45000});
   if(width===393){const metricText=await page.locator('#cwMetrics').textContent();assert.ok(metricText.includes('المواضع الهندسية للرفوف عبر المستويات'));assert.ok(metricText.includes('غير متاح / غير قابل للقياس'));assert.ok(metricText.includes('not usable or load-rated storage capacity'));}
   await page.waitForFunction(()=>document.querySelector('#cwJobProgress').hidden);
   const program=JSON.parse(await page.locator('#cwRequirementEvidence').textContent());
   assert.equal(program.find(r=>r.metric==='site_width_m').evidence,dimensionEvidence);
   assert.ok(program.every(r=>r.source_span&&r.confirmed));
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,before+1,'reload must not submit a second paid job');
   assert.ok(await page.locator('#cwPlan g[role=button]').count());
   assert.equal(await page.locator('#app canvas').count(),0,'private 2D review allocates no hidden legacy renderer');
   // Actual cwRoof journey: an approved automatic roof is removed as a new
   // draft, survives reload and another controlled generation, then is restored.
   const initialRoof=await workspaceState(page);assert.equal(roofRows(initialRoof).length,1);assert.equal(roofRows(initialRoof)[0].level_auto,true);assertConceptApproval(initialRoof,'Initial source/sample fixture');
   assert.equal(await page.locator('#cwRoof').textContent(),'إزالة السطح الافتراضي');
   const roofProviderBefore=(await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation;
   await page.locator('#cwApproveConfirm').check();await page.locator('#cwApprove').click();await page.locator('#cwShow3D').waitFor({state:'visible'});
   const approvedRoof=await workspaceState(page);assert.equal(revisionState(approvedRoof),'APPROVED');
   await page.locator('[data-step="3"]').click();await page.locator('#cwRoof').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('أكد إنشاء مسودة'));
   assert.equal((await workspaceState(page)).head,approvedRoof.head,'roof editing needs explicit approval-invalidation acknowledgement');
   await page.locator('#cwEditApprovalConfirm').check();await page.locator('#cwRoof').click();
   await page.waitForFunction(id=>document.querySelector('#cwRevision').value!==id&&document.querySelector('#cwRoof').dataset.enabled==='false',approvedRoof.head);
   const removedRoof=await workspaceState(page);assert.notEqual(removedRoof.head,approvedRoof.head);assert.equal(removedRoof.history.length,approvedRoof.history.length+1);assert.notEqual(revisionState(removedRoof),'APPROVED');assert.equal(revisionState(removedRoof,approvedRoof.head),'APPROVED');assert.equal(roofRows(removedRoof).length,0);
   assert.equal(await page.locator('#cwShow3D').isDisabled(),true,'the new roofless draft cannot borrow the old approval');
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,roofProviderBefore,'roof removal must not invoke the controlled provider');
   await page.reload();await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('مشروعك جاهز'));
   assert.equal((await workspaceState(page)).head,removedRoof.head);assert.equal(await page.locator('#cwRoof').textContent(),'إضافة سطح افتراضي');
   await page.locator('[data-step="1"]').click();await page.locator('#cwStartMode').selectOption('describe');await page.locator('#cwConfirmed').check();await page.locator('#cwBriefForm button[type=submit]').click();await page.locator('[data-option="A"]').click();
   await page.waitForFunction(id=>document.querySelector('#cwRevision').value!==id&&document.querySelector('#cwJobProgress').hidden,removedRoof.head,{timeout:45000});
   const regeneratedBare=await workspaceState(page);assert.equal(roofRows(regeneratedBare).length,0,'a later generated revision respects the saved roof-removal preference');assert.notEqual(regeneratedBare.head,removedRoof.head);assert.equal(regeneratedBare.history.length,removedRoof.history.length+1);
   if(width===1280)assert.equal(regeneratedBare.requirements.find(row=>row.metric==='unit_count')?.expected,2,'desktop regeneration must retain the selected two-apartment program');
   assertConceptApproval(regeneratedBare,'Regenerated residential/warehouse fixture');
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,roofProviderBefore+1,'the explicit regeneration invokes the controlled provider exactly once');
   await page.locator('#cwRoof').click();await page.waitForFunction(()=>document.querySelector('#cwRoof').dataset.enabled==='true');
   const restoredRoof=await workspaceState(page);assert.equal(roofRows(restoredRoof).length,1);assert.equal(roofRows(restoredRoof)[0].level_auto,true);assert.notEqual(restoredRoof.head,regeneratedBare.head);assert.equal(restoredRoof.history.length,regeneratedBare.history.length+1);assert.notEqual(revisionState(restoredRoof),'APPROVED');
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,roofProviderBefore+1,'restoring a roof must not invoke the controlled provider');
   // The nested-lock panel was mounted while this project was empty. It must
   // follow the newly generated revision without asking the owner to reload.
   await page.waitForFunction(()=>document.querySelectorAll('#cwSemanticLockTarget option').length>=2);
   await page.locator('#cwSemanticLockTarget').selectOption(JSON.stringify(['element','ground','a','points','light-a']));
   await page.locator('#cwSemanticLockScope').selectOption('position');
   await page.locator('#cwSemanticLockToggle').click();
   await page.waitForFunction(()=>document.querySelector('#cwSemanticLockScope option:checked')?.textContent.includes('🔒')&&document.querySelector('#cwSemanticLockToggle')?.textContent==='إلغاء هذا القفل'&&!document.querySelector('#cwSemanticLockToggle').disabled);
   assert.equal(await page.locator('#cwApprove').isEnabled(),false);
   await page.locator('#cwSpaces button').first().click();await page.locator('#cwLock').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('القفل'));
   await page.locator('#cwSpaces button').first().click();assert.equal(await page.locator('#cwSaveGeometry').isEnabled(),false);
   const lockedBeforeRoof=await workspaceState(page);await page.locator('#cwRoof').click();
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('فكّ أقفال الفراغات'));
   const lockedAfterRoof=await workspaceState(page);assert.equal(lockedAfterRoof.head,lockedBeforeRoof.head);assert.deepEqual(lockedAfterRoof.history,lockedBeforeRoof.history,'server refusal leaves immutable history unchanged');assert.equal(roofRows(lockedAfterRoof).length,1);
   assertConceptApproval(lockedAfterRoof,'Locked fixture after rejected roof removal');
   assert.equal((await (await fetch('http://127.0.0.1:'+port+'/test-stats')).json()).generation,roofProviderBefore+1,'locked roof refusal never invokes a provider');

   await page.locator('#cwApproveConfirm').check();await page.locator('#cwApprove').click();
   await page.locator('#cwShow3D').waitFor({state:'visible'});assert.equal(await page.locator('#cwShow3D').isEnabled(),true);
   const downloadPromise=page.waitForEvent('download');await page.locator('[data-format=svg]').click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'acs-approved.svg');
   await page.locator('#cwShow3D').click();
   if(noWebGL){
    await page.waitForFunction(()=>document.querySelector('#cwStatus')?.textContent.includes('العرض ثلاثي الأبعاد غير متاح'));
    assert.equal(await page.locator('#cwViewer canvas').count(),0);
    assert.equal(await page.locator('[data-format=svg]').isEnabled(),true);
   }else{
    await page.locator('#cwViewer canvas').waitFor({state:'visible',timeout:45000});
    assert.ok((await page.locator('#cwViewer canvas').boundingBox()).width>100);
    const names=await page.locator('#cwViewer .av-label').allTextContents();assert.ok(names.includes('A')&&names.includes('B'),'the connected viewer uses exact review-packet labels, not lowercase artifact room IDs');
   }
   assert.equal(await page.evaluate(()=>document.querySelector('#designWorkspace').scrollWidth>innerWidth),false);
   const revisionsBeforeChat=await page.locator('#cwRevision option').count();
   const chatReferenceRevision=await page.locator('#cwRevision').inputValue();
   await page.locator('[data-step="3"]').click();await page.locator('#cwEditApprovalConfirm').check();await page.locator('#cwChat').fill('غيّر عرض الفراغ B مع تثبيت الفراغ المقفل.');await page.locator('#cwChatSubmit').click();
   assert.equal(await page.locator('#cwSemanticLockToggle').isDisabled(),true,'pending generation disables nested lock writes');
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('تم حفظ المخطط'),{},{timeout:45000});
   assert.equal(await page.locator('#cwRevision option').count(),revisionsBeforeChat+1,'one chat edit must append one revision; approval itself preserves the selected version');
   assert.ok((await page.locator('#cwRevision option').allTextContents()).some(t=>t.includes('معتمدة')),'the previous approval remains in history');
   await page.locator('#cwComparison').waitFor({state:'visible'});
   assert.equal(await page.locator('#cwCompareRevision').inputValue(),chatReferenceRevision,'the async receipt must select the exact source revision, not an inferred neighbor');
   assert.ok(await page.locator('#cwComparisonRows tr').count()>2);
   // Hold the real comparison response: a visible existing comparison is not
   // evidence that the latest request completed. Revision selection must stay
   // disabled until the serialized request has settled, rather than be dropped.
   let releaseComparison,comparisonTimer;comparisonPause=new Promise(resolve=>{releaseComparison=resolve;});
   const comparisonEntered=new Promise(resolve=>{comparisonStarted=resolve;});
   try{
    await page.locator('#cwCompare').click();
    await Promise.race([comparisonEntered,new Promise((resolve,reject)=>{comparisonTimer=setTimeout(()=>reject(new Error('comparison did not reach the controlled route')),10000);})]);
    assert.equal(await page.locator('#cwRevision').isDisabled(),true,'comparison cannot silently drop a concurrent revision selection');
   }finally{clearTimeout(comparisonTimer);releaseComparison();comparisonPause=null;comparisonStarted=null;}
   await page.waitForFunction(()=>document.querySelector('#designWorkspace').getAttribute('aria-busy')==='false');
   await page.locator('#cwComparison').waitFor({state:'visible'});
   const firstRevision=await page.locator('#cwRevision option').first().getAttribute('value');
   await page.locator('#cwRevision').selectOption(firstRevision);
   await page.waitForFunction(()=>document.querySelector('#cwSemanticLockStatus')?.textContent.includes('تاريخية'));
   assert.equal(await page.locator('#cwSemanticLockToggle').isDisabled(),true,'a historical revision must stay read only');
   assert.equal(await page.locator('#cwRoof').isDisabled(),true,'a historical revision cannot change the current roof');
   await page.waitForFunction(()=>document.querySelector('#designWorkspace').getAttribute('aria-busy')==='false');
   assert.equal(await page.locator('#cwRevision').inputValue(),firstRevision,'the selected historical revision must finish loading');
   const beforeHistoricalClick=await workspaceState(page),roofRequests=workspaceActions.filter(action=>action==='set_roof').length;
   await page.evaluate(()=>document.querySelector('#cwRoof').dispatchEvent(new MouseEvent('click',{bubbles:true})));
   await page.waitForFunction(()=>document.querySelector('#cwStatus').textContent.includes('اختر آخر نسخة قبل تعديل السطح'));
   assert.equal(workspaceActions.filter(action=>action==='set_roof').length,roofRequests,'a forced historical roof event sends no write request');
   const afterHistoricalClick=await workspaceState(page);assert.equal(afterHistoricalClick.head,beforeHistoricalClick.head);assert.deepEqual(afterHistoricalClick.history,beforeHistoricalClick.history,'historical roof refusal preserves immutable history');
   await page.locator('#cwLogout').click();await page.locator('#lgEmail').waitFor({state:'visible'});
   if(noWebGL)assert.ok(errors.every(e=>/WebGL context/.test(e)),JSON.stringify(errors));
   else assert.deepEqual(errors,[]);
   console.log('PASS connected workspace '+width+(noWebGL?' without WebGL: 2D, save, approve, SVG, recover and logout remain available':': generation, reload, lock, approval, SVG, exact 3D, chat revision, logout'));
   await context.close();
  }
 }catch(error){
  // Preserve the original assertion/timeout. Diagnostics are independently
  // bounded and contain only this synthetic fixture's state, never auth data.
  const evidence={case:activeCase,network:networkEvents,page_errors:pageErrors,
   backend_process:{exit_code:child.exitCode,signal:child.signalCode},backend_log:backendLog};
  if(activePage&&!activePage.isClosed()){
   let timer;
   try{evidence.ui=await Promise.race([activePage.evaluate(()=>({
    status:document.querySelector('#cwStatus')?.textContent,
    busy:document.querySelector('#designWorkspace')?.getAttribute('aria-busy'),
    active_step:document.querySelector('[data-step][aria-current]')?.dataset.step,
    review_hidden:document.querySelector('#cwReviewContent')?.hidden,
    review_panel_hidden:document.querySelector('[data-step-panel="3"]')?.hidden,
    revision:document.querySelector('#cwRevision')?.value,
    job_phase:document.querySelector('#cwJobProgress')?.dataset.phase,
    job_hidden:document.querySelector('#cwJobProgress')?.hidden,
    recover_disabled:document.querySelector('#cwRecoverJob')?.disabled,
    recover_hidden:document.querySelector('#cwRecoverJob')?.hidden
   })),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('UI diagnostic timeout')),2000);})]);}
   catch(e){evidence.ui_error=e.message;}finally{clearTimeout(timer);}
  }
  try{const response=await fetch('http://127.0.0.1:'+port+'/test-diagnostics',{signal:AbortSignal.timeout(2000)});evidence.backend=await response.json();}
  catch(e){evidence.backend_error=e.message;}
  const logDir=path.join(ROOT,'logs');fs.mkdirSync(logDir,{recursive:true});
  fs.writeFileSync(path.join(logDir,'connected-workspace-failure.json'),JSON.stringify(evidence,null,2));
  console.error('CONNECTED WORKSPACE FAILURE DIAGNOSTICS '+JSON.stringify(evidence));
  if(activePage&&!activePage.isClosed())try{await activePage.screenshot({path:path.join(logDir,'connected-workspace-failure.png'),fullPage:true,timeout:5000});}catch(e){console.error('Connected failure screenshot unavailable: '+e.message);}
  throw error;
 }finally{if(browser)await browser.close();child.kill('SIGTERM');fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
