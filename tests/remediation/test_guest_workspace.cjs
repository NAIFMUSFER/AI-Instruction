'use strict';
// Exercise the shipped public page on a production-like HTTPS origin with strict
// CSP. Every backend request is intercepted and counted; no real user/provider.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const ORIGIN='https://acs-guest.test';
const roofLevels=model=>(model.levels||[]).filter(level=>level.kind==='roof');
function assertDefaultRoof(model,stage){
 const roofs=roofLevels(model);assert.equal(roofs.length,1,stage+': one canonical roof, without stacking');
 const roof=roofs[0],rooms=model.floors[roof.template]?.rooms;
 assert.equal(roof.auto,true,stage+': generated roof is explicitly automatic');
 assert.ok(Number.isFinite(roof.elevation),stage+': roof has an explicit elevation');
 assert.equal(model.meta?.acs_roof?.schema,'acs.roof/1');
 assert.equal(model.meta.acs_roof.source,'system_default');
 assert.equal(model.meta.acs_roof.form,'flat');
 assert.equal(model.meta.acs_roof.parapet_height_m,.9);
 assert.equal(model.meta.acs_roof.occupied_floor,false,'default roof is not another occupied storey');
 assert.ok(rooms?.length,stage+': default has canonical deck geometry');
 const occupied=model.levels.filter(level=>level.kind!=='roof');
 const elevation=level=>level.elevation??level.index*model.floor_height;
 const top=[...occupied].sort((a,b)=>elevation(b)-elevation(a)||b.index-a.index)[0];
 const sourceRooms=model.floors[top.template].rooms;
 assert.equal(rooms.length,sourceRooms.length,stage+': deck follows every top-floor rectangle');
 for(const room of rooms){
  assert.equal(room.auto,true);assert.equal(room.role,'roof_deck');assert.equal(room.wall_h,.9);
  assert.equal(room.roof_provenance?.source,'system_default');
  const source=sourceRooms.find(item=>item.id===room.roof_provenance.source_room_id);
  assert.ok(source,stage+': roof identifies its source room');assert.deepEqual(room.rect,source.rect);
  for(const key of ['doors','windows','points'])assert.deepEqual(room[key],[]);
 }
}
function assertExactRoof(actual,expected,stage){
 assert.deepEqual(roofLevels(actual),roofLevels(expected),stage+': roof instance identity/elevation stays exact');
 assert.deepEqual(actual.meta?.acs_roof,expected.meta?.acs_roof,stage+': roof provenance stays exact');
 for(const level of roofLevels(expected))assert.deepEqual(actual.floors[level.template],expected.floors[level.template],stage+': deck/parapet geometry stays exact');
}
function occupiedModel(model){
 const copy=JSON.parse(JSON.stringify(model)),templates=new Set(roofLevels(copy).map(level=>level.template));
 copy.levels=copy.levels.filter(level=>level.kind!=='roof');
 for(const template of templates)if(!copy.levels.some(level=>level.template===template))delete copy.floors[template];
 if(copy.meta)delete copy.meta.acs_roof;
 return copy;
}
function currentGuestRecord(snapshot){
 const record=snapshot.records.find(row=>row.record_id===snapshot.pointer);
 assert.ok(record,'an explicit local save must have a current record');
 assert.equal(typeof record.model_hash,'string');assert.ok(record.model_hash);
 return record;
}
async function assertOccupiedCounts(page,model){
 const rooms=model.levels.filter(level=>level.kind!=='roof').reduce((sum,level)=>sum+model.floors[level.template].rooms.length,0);
 const values=await page.locator('#statCount b').allTextContents();
 assert.equal(Number(values[1]),rooms,'visible occupied-room count excludes every roof deck instance');
 assert.ok((await page.locator('#statCount').textContent()).includes(roofLevels(model).length+' سطح غير مشغول'),'the added roof is disclosed separately from occupied rooms');
}
function recoveryImportReady(expectedName){
 // The preceding authored fixture is also 24 m wide. Wait for this file's
 // unique identity before saving; its asynchronous read may still be pending.
 const model=window.ACS.exportModel();
 return model?.site.w===24&&model.meta?.name===expectedName;
}
async function assertGuestQuality(page,width,stage){
 const quality=await page.evaluate(()=>window.ACS.legacyRenderQuality());
 assert.ok(quality.renderer===null||typeof quality.renderer==='string');
 if(quality.renderer===null)assert.equal(quality.reason,'RENDERER_ID_UNAVAILABLE');
 assert.ok(Number.isFinite(quality.pixel_ratio)&&quality.pixel_ratio>0);
 if(/swiftshader|llvmpipe|softpipe|swrast|software rasterizer|microsoft basic render/i.test(quality.renderer||'')){
  assert.equal(quality.profile,'SOFTWARE_CONSERVATIVE','actual software rendering selects the bounded production profile');
  assert.ok(quality.pixel_ratio<=.75,'automatic sample/draft work must retain its software pixel budget');
  assert.ok(Number.isFinite(quality.shadow_map_size)&&quality.shadow_map_size<=512,'automatic presentation must not restore expensive shadows');
 }
 console.log('GUEST RENDER QUALITY '+JSON.stringify({width,stage,...quality}));
}
// Test-only timing probes retain the real handlers/rendering and every budget.
// Evidence contains fixed event names, durations and synthetic site width only.
const DIAG_PREFIX='[ACS-GUEST-DIAG] ';
function instrumentGuestSource(file,body){
 const relative=path.relative(PUB,file).split(path.sep).join('/');
 const probes={
  'app/ui/workspace-ui-wiring.js':[
   ['function setModel(data){',"function setModel(data){window.__ACS_GUEST_DIAG__?.mark('model:start');"],
   ['_next=compile(incoming);',"window.__ACS_GUEST_DIAG__?.mark('compile:start');_next=compile(incoming);window.__ACS_GUEST_DIAG__?.mark('compile:end');"],
   ['model=_next; scene.add(model);',"model=_next; scene.add(model);window.__ACS_GUEST_DIAG__?.mark('model:committed');"],
   ["  if(window.__ACS_PQ__&&window.__ACS_PQ__.composer&&!renderer.xr.isPresenting){window.__ACS_PQ__.composer.render();}else{renderer.render(scene,camera);}","  window.__ACS_GUEST_DIAG__?.mark('render:start');\n  if(window.__ACS_PQ__&&window.__ACS_PQ__.composer&&!renderer.xr.isPresenting){window.__ACS_PQ__.composer.render();}else{renderer.render(scene,camera);}\n  window.__ACS_GUEST_DIAG__?.mark('render:end');"]
  ],
  'app/generated/pbr-bridge.js':[
   ['gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);',"window.__ACS_GUEST_DIAG__?.mark('pixels:start');gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,px);window.__ACS_GUEST_DIAG__?.mark('pixels:end');"]
  ]
 };
 if(!probes[relative])return body;
 let source=body.toString('utf8');
 for(const [from,to] of probes[relative]){
  assert.equal(source.split(from).length,2,'guest diagnostic anchor must match exactly once: '+relative);
  source=source.replace(from,to);
 }
 return source;
}
async function guestDiagnostics(context,width){
 const records=[],pages=[];let phase='created';
 const record=(kind,data)=>{const row={at:new Date().toISOString(),width,phase,kind,...data};records.push(row);if(records.length>160)records.shift();console.log(DIAG_PREFIX+JSON.stringify(row));};
 context.on('page',page=>{
  const id=pages.length;pages.push(page);
  page.on('console',message=>{const text=message.text();if(!text.startsWith(DIAG_PREFIX))return;
   try{const data=JSON.parse(text.slice(DIAG_PREFIX.length));if(data?.contract==='guest-timing/1')record('page',{page:id,...data});}catch{}
  });
  page.on('crash',()=>record('crash',{page:id}));
 });
 await context.addInitScript(()=>{
  const state={raf:0,longtasks:0,longtaskMaxMs:0,active:{},maxMs:{},calls:{},siteWidth:null},now=()=>Math.round(performance.now());
  let logs=0,framesToLog=6,lastModel,longtaskReports=0,heartbeats=0,lastSlowRenderLog=-Infinity;
  const snapshot=()=>JSON.parse(JSON.stringify(state));
  const emit=(event,extra={})=>{if(logs++<120)console.log('[ACS-GUEST-DIAG] '+JSON.stringify({contract:'guest-timing/1',event,t:now(),...extra}));};
  const mark=name=>{
   const [part,edge]=name.split(':'),time=now();state.calls[name]=(state.calls[name]||0)+1;
   if(edge==='start')state.active[part]=time;
   let duration;
   if((edge==='end'||name==='model:committed')&&state.active[part]!==undefined){duration=time-state.active[part];delete state.active[part];state.maxMs[part]=Math.max(state.maxMs[part]||0,duration);}
   if(name==='model:start')framesToLog=6;
   const slowRender=part==='render'&&duration>250&&time-lastSlowRenderLog>=5000;
   if(slowRender)lastSlowRenderLog=time;
   if(part!=='render'||framesToLog>0||slowRender)emit(name,duration===undefined?{}:{duration});
   if(name==='render:end'&&framesToLog>0)framesToLog--;
  };
  window.__ACS_GUEST_DIAG__={mark,snapshot};
  const ids=new Set(['guestWarehouse','loadWarehouse','guestExample','guestCreate','genText','guestSignin']);
  for(const capture of [true,false])document.addEventListener('click',event=>{
   const id=event.target?.closest?.('button,a')?.id;if(!ids.has(id))return;
   framesToLog=6;emit(capture?'click:capture':'click:bubble',{target:id});
  },capture);
  try{new PerformanceObserver(list=>{for(const entry of list.getEntries()){
   state.longtasks++;state.longtaskMaxMs=Math.max(state.longtaskMaxMs,Math.round(entry.duration));
   if(entry.duration>250&&longtaskReports++<4)emit('longtask',{duration:Math.round(entry.duration)});
  }}).observe({type:'longtask',buffered:true});}catch{}
  function frame(){state.raf++;
   let model;try{model=window.ACS?.exportModel?.();}catch{}
   if(model&&model!==lastModel){lastModel=model;state.siteWidth=Number.isFinite(model.site?.w)?model.site.w:null;emit('model:observed',{siteWidth:state.siteWidth});}
   requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);setInterval(()=>{if(heartbeats++<24)emit('heartbeat',snapshot());},5000);
  emit('document:start');
 });
 return {
  phase(name){phase=name;record('phase',{});},
  async failure(error){
   const snapshots=[];
   for(const [id,page]of pages.entries()){
    if(page.isClosed())continue;
    let timer;
    try{snapshots.push({page:id,value:await Promise.race([
     page.evaluate(()=>window.__ACS_GUEST_DIAG__?.snapshot()||null),
     new Promise(resolve=>{timer=setTimeout(()=>resolve({unavailable:'PAGE_UNRESPONSIVE'}),1000);})
    ])});}catch{snapshots.push({page:id,value:{unavailable:'PAGE_CLOSED_OR_UNREACHABLE'}});}finally{clearTimeout(timer);}
   }
   const output=path.join(ROOT,'logs','guest-diagnostics');fs.mkdirSync(output,{recursive:true});
   fs.writeFileSync(path.join(output,width+'.json'),JSON.stringify({contract:'guest-failure/1',width,phase,errorType:['TimeoutError','AssertionError','TypeError','Error'].includes(error?.name)?error.name:'Error',records,snapshots},null,2));
  }
 };
}
async function guestSnapshot(page){
 return page.evaluate(()=>new Promise((resolve,reject)=>{
  const open=indexedDB.open('acs_guest_project_v1',2);
  open.onerror=()=>reject(open.error);
  open.onsuccess=()=>{
   const db=open.result,tx=db.transaction(['records','meta'],'readonly');
   let records=[],pointer=null;
   tx.objectStore('records').getAll().onsuccess=e=>{records=e.target.result;};
   tx.objectStore('meta').get('pointer').onsuccess=e=>{pointer=e.target.result;};
   tx.oncomplete=()=>{db.close();resolve({pointer,records:records.sort((a,b)=>a.record_id.localeCompare(b.record_id))});};
   tx.onerror=()=>{db.close();reject(tx.error);};
  };
 }));
}
// Local JSON export adds only absent stable instance identifiers and explicit
// fallback elevations. Predict that documented contract without calling exporter
// code, retaining all supplied dimensions, room IDs, heights and object data.
function normalizedLocalModel(model){
 const result=JSON.parse(JSON.stringify(model));
 const height=Number(result.floor_height||((Number(result.wall_h)||3)+.2));
 for(const level of result.levels||[]){
  const index=Number(level.index||0);
  if(level.id==null)level.id='bld_0.flr_'+index;
  if(level.elevation==null)level.elevation=Number((index*height).toFixed(3));
 }
 for(const [template,floor] of Object.entries(result.floors||{})){
  (floor.rooms||[]).forEach((room,index)=>{
   if(room.space_id==null)room.space_id='bld_0.'+template+'.'+(room.id||('sp_'+index));
  });
 }
 return result;
}
async function downloadedJSON(page,button){
 const event=page.waitForEvent('download',{timeout:15000});
 await page.locator(button).click();
 const download=await event;
 assert.match(download.suggestedFilename(),/\.json$/i);
 assert.equal(await download.failure(),null);
 const stream=await download.createReadStream();
 assert.ok(stream,'download must contain a real readable file');
 const parts=[];for await(const part of stream)parts.push(part);
 return JSON.parse(Buffer.concat(parts).toString('utf8'));
}
async function runGuestWorkspaceTests(){
 const browser=await PW.launch();let passed=0;const diagnostics=[];
 try{
  for(const width of [393,1280]){
   const context=await browser.newContext({viewport:{width,height:852},acceptDownloads:true});
   context.setDefaultTimeout(15000);
   const diagnostic=await guestDiagnostics(context,width);diagnostics.push(diagnostic);
   const page=await context.newPage(),calls=[],errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{
    window.__guestAuthEvents=0;
    document.addEventListener('acs:authenticated',()=>window.__guestAuthEvents++);
   });
   await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==ORIGIN||/^\/(?:v1|auth|rest|functions)(?:\/|$)/.test(url.pathname)){calls.push(url.pathname);return route.abort();}
    const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:instrumentGuestSource(file,fs.readFileSync(file))});
   });
   diagnostic.phase('fresh-entry');
   await page.goto(ORIGIN+'/');
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete');
   await assertGuestQuality(page,width,'fresh-entry');
   const freshSample=await page.evaluate(()=>window.ACS.exportModel());
   assertDefaultRoof(freshSample,'fresh residential sample');await assertOccupiedCounts(page,freshSample);
   assert.equal(await page.locator('#login').isVisible(),false);
   assert.equal(await page.locator('#acsGuestBanner').isVisible(),true);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.evaluate(()=>window.__guestAuthEvents),0);
   assert.equal(await page.evaluate(()=>window.ACS.authSession),undefined);
   assert.equal(await page.evaluate(()=>window.ACS.projectId),undefined);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   if(width<=820)assert.equal(await page.locator('#panelToggle').getAttribute('aria-expanded'),'false');
   assert.equal(await page.locator('#genLLM').isEnabled(),false);
   assert.equal(await page.locator('#bNotesApply').isEnabled(),false);
   diagnostic.phase('first-warehouse-click');
   await page.locator('#guestWarehouse').click();
   diagnostic.phase('first-warehouse-click-returned');
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
   const warehouseSample=await page.evaluate(()=>window.ACS.exportModel());
   assertDefaultRoof(warehouseSample,'warehouse sample switch');await assertOccupiedCounts(page,warehouseSample);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/تجريبي/);
   diagnostic.phase('local-edit');
   await page.locator('#guestCreate').click();
   await page.locator('#descText').fill('غرفة معيشة 5×4 ومطبخ 4×3 وغرفة نوم 4×4');
   await page.locator('#siteW').fill('24');await page.locator('#siteD').fill('18');await page.locator('#nFloors').fill('1');
   await page.locator('#genText').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===24);
   const generatedLocal=await page.evaluate(()=>window.ACS.exportModel());
   assertDefaultRoof(generatedLocal,'local description generation');await assertOccupiedCounts(page,generatedLocal);
   const saved=await page.evaluate(()=>window.ACS.persistence.save('GUEST_TEST'));
   assert.equal(saved.ok,true);
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.site.w===24);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/استُعيد/);
   assertExactRoof(await page.evaluate(()=>window.ACS.exportModel()),generatedLocal,'saved local draft reload');
   diagnostic.phase('local-roof-remove-edit-restore');
   const withRoofRecord=currentGuestRecord(await guestSnapshot(page));
   await page.locator('#guestCreate').click();await page.locator('#acsTabModel').click();
   await page.locator('#localRoofToggle').waitFor({state:'visible'});
   const roofTarget=await page.locator('#localRoofToggle').boundingBox();
   assert.ok(roofTarget.width>=44&&roofTarget.height>=44,'contextual roof action is a real 44 CSS-pixel touch target');
   assert.equal(await page.locator('#localRoofToggle').getAttribute('aria-describedby'),'localRoofDisclosure');
   assert.match(await page.locator('#localRoofDisclosure').textContent(),/افتراض|افتراضي|مفترض/);
   await page.locator('#floors').getByRole('button',{name:'السطح',exact:true}).click();
   assert.equal(await page.locator('#floors button.active').textContent(),'السطح','exercise removal while the roof is isolated');
   await page.locator('#localRoofToggle').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.meta?.acs_roof?.removed_by_user===true);
   assert.equal(await page.evaluate(()=>document.activeElement?.id),'localRoofToggle','focus survives rebuilding the roof controls');
   const removedLocal=await page.evaluate(()=>window.ACS.exportModel());
   assert.equal(roofLevels(removedLocal).length,0);
   assert.equal(await page.locator('#floors button.active').textContent(),'الكل','removal resets the visible floor control');
   const visibility=await page.evaluate(async()=>{
    const live=await import('/app/ui/workspace-ui-wiring.js');
    const floors=new Set(window.ACS.exportModel().levels.filter(level=>level.kind!=='roof').map(level=>'F'+level.index));
    const diagnostics=window.ACS.renderDiagnosticsDetail();
    return {selected:live.floorSel,visible_occupied_meshes:Object.values(live.registry).reduce((sum,layer)=>sum+layer.meshes.filter(mesh=>mesh.visible&&floors.has(mesh.userData.floor)).length,0),
     canonical_meshes:diagnostics.canonical_meshes,webgl_context_ok:diagnostics.webgl_context_ok};
   });
   assert.equal(visibility.selected,'all','actual filter agrees with the all-floors label');
   assert.ok(visibility.visible_occupied_meshes>0,'occupied canonical geometry stays visible after its isolated roof is removed');
   assert.ok(visibility.canonical_meshes>0);assert.equal(visibility.webgl_context_ok,true);
   assert.equal(removedLocal.meta.acs_roof.source,'user');
   assert.deepEqual(occupiedModel(removedLocal),occupiedModel(generatedLocal),'removing the roof preserves all occupied geometry, identities and other provenance');
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_ROOF_REMOVED'))).ok,true);
   const removedRecord=currentGuestRecord(await guestSnapshot(page));
   assert.notEqual(removedRecord.model_hash,withRoofRecord.model_hash,'canonical removal changes the actual saved model hash');
   assert.deepEqual(JSON.parse(removedRecord.payload).model,removedLocal);
   await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.meta?.acs_roof?.removed_by_user===true);
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),removedLocal,'owner removal survives exact local recovery');
   await page.locator('#guestCreate').click();
   await page.locator('#descText').fill('غرفة معيشة 5×4 ومطبخ 4×3 وغرفة نوم 4×4');
   await page.locator('#siteW').fill('25');await page.locator('#siteD').fill('18');await page.locator('#nFloors').fill('1');
   await page.locator('#genText').click();await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===25);
   const editedBare=await page.evaluate(()=>window.ACS.exportModel());
   assert.equal(editedBare.meta?.acs_roof?.removed_by_user,true,'local generation in the same project respects explicit removal');
   assert.equal(roofLevels(editedBare).length,0,'local edit does not silently restore the removed roof');
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_ROOF_EDIT_WITHOUT'))).ok,true);
   const editedRecord=currentGuestRecord(await guestSnapshot(page));
   assert.notEqual(editedRecord.model_hash,removedRecord.model_hash,'the requested site edit changes its saved canonical model');
   await page.locator('#guestCreate').click();await page.locator('#acsTabModel').click();
   await page.locator('#localRoofToggle').focus();await page.locator('#localRoofToggle').press('Enter');
   await page.waitForFunction(()=>window.ACS.exportModel()?.levels?.some(level=>level.kind==='roof'&&level.auto===true));
   const restoredLocal=await page.evaluate(()=>window.ACS.exportModel());
   assert.equal(await page.evaluate(()=>document.activeElement?.id),'localRoofToggle','keyboard restoration retains contextual focus');
   assertDefaultRoof(restoredLocal,'explicit owner restoration');
   assert.deepEqual(occupiedModel(restoredLocal),occupiedModel(editedBare),'restoring the roof preserves all occupied source geometry');
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_ROOF_RESTORED'))).ok,true);
   const restoredRecord=currentGuestRecord(await guestSnapshot(page));
   assert.notEqual(restoredRecord.model_hash,editedRecord.model_hash,'explicit roof restoration changes its saved canonical model');
   assert.deepEqual(JSON.parse(restoredRecord.payload).model,restoredLocal);
   await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.site.w===25);
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),restoredLocal,'restored roof and provenance survive recovery exactly');
   assert.deepEqual(calls,[],'roof removal, local editing and restoration must make no identity/private/provider requests');
   // Resume the original 24 m import/recovery fixture through the real importer.
   await page.locator('#impFile').setInputFiles({name:'roof-journey-return.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(generatedLocal))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===24);
   // Local file inputs and downloads exercise the actual handlers and bytes.
   // This fixture is synthetic; no real account files or credentials are read.
   diagnostic.phase('local-import-download');
   const originalModel=await page.evaluate(()=>window.ACS.exportModel());
   const importedModel=JSON.parse(JSON.stringify(originalModel));
   importedModel.site.w=23;importedModel.meta={...importedModel.meta,name:'guest-import-'+width};
   importedModel.levels[0].id='explicit-guest-level';importedModel.levels[0].elevation=.45;
   const firstTemplate=importedModel.levels[0].template;
   importedModel.floors[firstTemplate].rooms[0].space_id='explicit-guest-space';
   await page.locator('#impFile').setInputFiles({name:'synthetic-building.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(importedModel))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===23&&document.getElementById('impInfo').textContent.includes('JSON ✓'));
   const importedVisible=await page.evaluate(()=>window.ACS.exportModel());
   assert.deepEqual(importedVisible.floors,importedModel.floors);
   assert.deepEqual(importedVisible.levels,importedModel.levels);
   assertExactRoof(importedVisible,importedModel,'import existing automatic roof without duplication');
   await page.locator('#guestCreate').click();
   await page.locator('#acsTabShow').click();
   const exported=await downloadedJSON(page,'#bJson');
   const normalized=normalizedLocalModel(importedVisible);
   assert.deepEqual(exported.site,normalized.site);
   assert.deepEqual(exported.levels,normalized.levels,'export may only add the declared missing level IDs/elevations');
   assert.deepEqual(exported.floors,normalized.floors,'all room geometry, object data and explicit IDs must survive export');
   assert.equal(exported.levels[0].id,'explicit-guest-level');
   assert.equal(exported.levels[0].elevation,.45);
   assert.equal(exported.floors[firstTemplate].rooms[0].space_id,'explicit-guest-space');
   assert.equal(exported.meta.name,'guest-import-'+width);
   assertExactRoof(exported,normalized,'downloaded canonical roof');
   // Reimport the downloaded envelope, preserving the normalized canonical
   // dimensions/identities rather than comparing with the pre-export raw form.
   await page.locator('#impFile').setInputFiles({name:'download-roundtrip.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(exported))});
   await page.waitForFunction(()=>window.ACS.exportModel()?.schema==='acs.project/1'&&document.getElementById('impInfo').textContent.includes('JSON ✓'));
   const roundtrip=await page.evaluate(()=>window.ACS.exportModel());
   assert.deepEqual(roundtrip.levels,normalized.levels);
   assert.deepEqual(roundtrip.floors,normalized.floors);
   assert.deepEqual(roundtrip.site,normalized.site);
   assertExactRoof(roundtrip,normalized,'download reimport');
   // Input accept filters are not enforcement: intentionally submit a PDF.
   await page.locator('#impFile').setInputFiles({name:'unsupported.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 synthetic unsupported guest fixture')});
   await page.waitForFunction(()=>document.getElementById('impInfo').textContent.includes('سجّل الدخول'));
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),roundtrip,'unsupported guest import must preserve the visible model');
   await page.locator('#impFile').setInputFiles({name:'malformed.json',mimeType:'application/json',buffer:Buffer.from('{"levels":[')});
   await page.waitForFunction(()=>document.getElementById('impInfo').textContent.startsWith('خطأ:'));
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),roundtrip,'malformed JSON must preserve the exact roof and visible model');
   assert.deepEqual(calls,[],'local import and download must not call private/provider services');
   // Old local files are evidence, not new generation. Import/recovery must
   // neither invent a roof nor turn an authored one into a system default.
   diagnostic.phase('legacy-and-authored-roof-import-recovery');
   const legacy=occupiedModel(originalModel);legacy.meta.name='legacy-without-roof-'+width;
   const authored=JSON.parse(JSON.stringify(originalModel));
   authored.meta.name='authored-roof-'+width;
   authored.meta.acs_roof={schema:'acs.roof/1',source:'user',form:'flat',parapet_height_m:1.25,occupied_floor:false};
   for(const level of roofLevels(authored)){
    level.auto=false;level.name='سطح خاص مستورد';
    for(const room of authored.floors[level.template].rooms){room.auto=false;room.wall_h=1.25;room.roof_provenance={source:'user'};}
   }
   for(const [name,fixture] of [['legacy',legacy],['authored',authored]]){
    await page.locator('#impFile').setInputFiles({name:name+'.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture))});
    await page.waitForFunction(expected=>window.ACS.exportModel()?.meta?.name===expected,fixture.meta.name);
    const imported=await page.evaluate(()=>window.ACS.exportModel());
    assert.deepEqual(imported.levels,fixture.levels,name+' import retains all level declarations');
    assert.deepEqual(imported.floors,fixture.floors,name+' import retains all canonical geometry');
    assertExactRoof(imported,fixture,name+' imported roof policy');
    assert.equal(await page.locator('#localRoofToggle').count(),0,name+' imported roof is not offered as an automatically editable system roof');
    assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_ROOF_IMPORT_TEST'))).ok,true);
    await page.reload();
    await page.waitForFunction(expected=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.meta?.name===expected,fixture.meta.name);
    const recovered=await page.evaluate(()=>window.ACS.exportModel());
    assert.deepEqual(recovered.levels,fixture.levels,name+' recovery must not add or reclassify a roof');
    assert.deepEqual(recovered.floors,fixture.floors,name+' recovery must not rewrite geometry');
    assertExactRoof(recovered,fixture,name+' recovered roof policy');
    assert.equal(await page.locator('#localRoofToggle').count(),0,name+' recovery keeps its roof authority');
   }
   assert.deepEqual(calls,[],'roof imports/recovery remain local without auth/private/provider work');
   // The later two-tab/slow-read checks use an older roofless draft: displaying
   // a newly roofed sample must not silently augment the recovered snapshot.
   const recoveryModel=occupiedModel(originalModel);recoveryModel.meta.name='legacy-recovery-'+width;
   await page.locator('#impFile').setInputFiles({name:'restored-local.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(recoveryModel))});
   await page.waitForFunction(recoveryImportReady,recoveryModel.meta.name);
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_IMPORT_TEST'))).ok,true);
   if(width===1280){
    diagnostic.phase('two-tabs-storage-denied');
    // A second real tab shares only the guest draft namespace. Its visible
    // sample choice must not overwrite the first tab's in-memory project.
    const second=await context.newPage();second.on('pageerror',e=>errors.push(e.message));
    await second.goto(ORIGIN+'/?guest=1');
    await second.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
    await assertGuestQuality(second,width,'second-tab-recovered-draft');
    assert.equal(await second.evaluate(()=>window.ACS.exportModel().site.w),24);
    assert.deepEqual(await second.evaluate(()=>window.ACS.exportModel()),recoveryModel,'second tab recovers the older roofless draft exactly');
    await page.waitForFunction(()=>window.ACS.tabs().owner.tabs>=2);
    await second.waitForFunction(()=>window.ACS.tabs().owner.tabs>=2);
    assert.notEqual(await second.evaluate(()=>window.ACS.tabs().self),await page.evaluate(()=>window.ACS.tabs().self));
    assert.equal(await second.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
    await second.locator('#guestWarehouse').click();
    await second.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
    assertDefaultRoof(await second.evaluate(()=>window.ACS.exportModel()),'second tab warehouse sample');
    assert.equal(await page.evaluate(()=>window.ACS.exportModel().site.w),24,'a sample selected in another guest tab must not replace this visible project');
    assert.equal(await second.evaluate(()=>window.ACS.authSession),undefined);
    assert.equal(await second.evaluate(()=>window.ACS.projectId),undefined);
    await second.close();
    // Restore the explicit current draft after closing the second tab; shared
    // guest persistence is disclosed, not claimed to be a private per-tab DB.
    assert.equal((await page.evaluate(()=>window.ACS.persistence.save('GUEST_AFTER_TWO_TABS'))).ok,true);
    const existing=await guestSnapshot(page);
    const denied=await context.newPage();denied.on('pageerror',e=>errors.push(e.message));
    await denied.addInitScript(()=>{
     window.__guestDeniedStorageAttempts=0;
     IDBFactory.prototype.open=function(){window.__guestDeniedStorageAttempts++;throw new DOMException('Synthetic storage denial','SecurityError');};
    });
    await denied.goto(ORIGIN+'/?guest=1');
    await denied.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
    assert.ok(await denied.evaluate(()=>window.__guestDeniedStorageAttempts>0));
    assert.equal(await denied.locator('#login').isVisible(),false);
    assert.ok(await denied.evaluate(()=>window.ACS.exportModel()?.floors));
    assertDefaultRoof(await denied.evaluate(()=>window.ACS.exportModel()),'storage-denied temporary sample');
    assert.match(await denied.locator('#acsGuestStatus').textContent(),/تنزيل JSON/);
    assert.equal(await denied.evaluate(()=>window.ACS.guestAutosaveReady),false);
    await denied.locator('#guestCreate').click();await denied.locator('#acsTabShow').click();
    await denied.locator('#acsSaveNow').click();
    await denied.waitForFunction(()=>document.getElementById('acsSaveState').dataset.acsSave==='FAILED');
    assert.notEqual(await denied.locator('#acsSaveState').getAttribute('data-acs-save'),'SAVED');
    const deniedModel=await denied.evaluate(()=>window.ACS.exportModel());
    const backup=await downloadedJSON(denied,'#acsExportBackup');
    assert.equal(backup.contract,'acs-project-backup/1');
    assert.equal(backup.storage,'LOCAL_FILE_DOWNLOAD');
    assert.deepEqual(JSON.parse(backup.record.payload).model,deniedModel,'storage denial still allows an exact local backup download');
    await denied.close();
    const afterDenied=await guestSnapshot(page);
    const originalRecord=existing.records.find(record=>record.record_id===existing.pointer);
    assert.ok(originalRecord,'a real prior guest snapshot exists before denial');
    assert.deepEqual(afterDenied.records.find(record=>record.record_id===existing.pointer),originalRecord,'failed recovery/save must preserve the original guest record');
    assert.deepEqual(calls,[],'two tabs and denied storage must never invoke identity/private/provider requests');
   }
   // Delay the real IndexedDB recovery result, then act before it completes.
   // This instruments only scheduling; the shipped page and saved data are real.
   diagnostic.phase('delayed-recovery');
   await page.evaluate(()=>sessionStorage.setItem('acs_test_delay_guest_recovery','1'));
   await page.addInitScript(()=>{
    let current;const seen=new WeakSet();
    Object.defineProperty(window,'ACS',{configurable:true,get(){return current;},set(value){
     current=value;if(!value||typeof value!=='object'||seen.has(value))return;seen.add(value);
     let persistence;
     Object.defineProperty(value,'persistence',{configurable:true,get(){return persistence;},set(api){
      persistence=api;
      if(sessionStorage.getItem('acs_test_delay_guest_recovery')==='1'){
       const original=api.recover;
       api.recover=()=>{
        const result=original();result.then(()=>{window.__guestRecoveryReadDone=true;});
        return new Promise(resolve=>{window.__releaseGuestRecovery=()=>result.then(resolve);});
       };
      }
     }});
    }});
   });
   // Cross the UI's slow-read notice without releasing the genuine IndexedDB
   // result. This used to discard recovery and autosave the temporary sample.
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.__guestRecoveryReadDone);
   const beforeSlowRecovery=await guestSnapshot(page);
   assert.ok(beforeSlowRecovery.records.some(record=>JSON.parse(record.payload).model.site.w===24));
   assert.deepEqual(JSON.parse(currentGuestRecord(beforeSlowRecovery).payload).model,recoveryModel,'the current pending snapshot is the original roofless draft');
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recoveryStatus==='slow');
   assert.equal(await page.locator('#acsGuestBanner').getAttribute('data-recovery'),'pending');
   assert.notEqual(await page.evaluate(()=>window.ACS.exportModel().site.w),24,'a real temporary sample is visible while saved work is still loading');
   assertDefaultRoof(await page.evaluate(()=>window.ACS.exportModel()),'temporary sample during slow recovery');
   assert.deepEqual(await page.evaluate(()=>window.ACS.persistence.save('AUTOSAVE')),{ok:false,code:'RECOVERY_PENDING'});
   assert.deepEqual(await page.evaluate(()=>window.ACS.persistence.save('MANUAL')),{ok:false,code:'RECOVERY_PENDING'});
   await page.evaluate(()=>{
    Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});
    document.dispatchEvent(new Event('visibilitychange'));
    delete document.visibilityState;
   });
   assert.deepEqual(await guestSnapshot(page),beforeSlowRecovery,'pending recovery must preserve all saved records and the pointer');
   await page.evaluate(()=>window.__releaseGuestRecovery());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.site.w===24);
   assert.match(await page.locator('#acsGuestStatus').textContent(),/استُعيد/);
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),recoveryModel,'late recovery without interaction preserves the exact roofless draft');
   // A second slow read must not overwrite a new sample chosen by the visitor.
   await page.reload();await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.__guestRecoveryReadDone);
   await page.locator('#guestWarehouse').click();
   await page.waitForFunction(()=>window.ACS.exportModel()?.site.w===120);
   await page.evaluate(()=>window.__releaseGuestRecovery());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete');
   assert.equal(await page.evaluate(()=>window.ACS.exportModel().site.w),120,'a late recovery must not replace the visitor sample choice');
   assertDefaultRoof(await page.evaluate(()=>window.ACS.exportModel()),'late recovery keeps new sample roof');
   await page.evaluate(()=>sessionStorage.removeItem('acs_test_delay_guest_recovery'));
   // Cloud auth helpers fail closed even if invoked outside the disabled UI.
   const guard=await page.evaluate(async()=>{
    let code;try{await ACS_AUTH.acsFetchJSON('/v1/auth/projects',{});}catch(e){code=e.code;}
    return {code,session:await ACS_AUTH.freshSession()};
   });
   assert.deepEqual(guard,{code:'GUEST_SIGNIN_REQUIRED',session:null});
   assert.deepEqual(calls,[],'guest must never request health/auth/private/provider services');
   assert.deepEqual(errors,[],'the actual shipped guest must boot without page errors');
   // A saved account is preserved but not read/used in explicit guest mode.
   diagnostic.phase('explicit-guest-with-stored-account');
   const privateSession={access_token:'private-access',refresh_token:'private-refresh',expires_at:1,user:{id:'private-user'}};
   await page.evaluate(s=>{localStorage.setItem('acs_supabase_session_v1',JSON.stringify(s));localStorage.setItem('acs_project_v1',JSON.stringify({id:'private-project'}));localStorage.setItem('acs_password_recovery_v1','private-user');},privateSession);
   await page.addInitScript(()=>{
    const original=Storage.prototype.getItem;window.__guestCredentialReads=0;
    Storage.prototype.getItem=function(key){if(key==='acs_supabase_session_v1'||key==='acs_project_v1')window.__guestCredentialReads++;return original.call(this,key);};
   });
   await page.goto(ORIGIN+'/?guest=1');await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   assert.equal(await page.evaluate(()=>window.__guestCredentialReads),0);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.loadSession()),null);
   assert.equal(await page.evaluate(()=>window.ACS_AUTH.storageScope()),'acs_guest_project_v1');
   assert.deepEqual(calls,[]);
   const preserved=await page.evaluate(()=>JSON.parse(localStorage.getItem('acs_supabase_session_v1')));
   assert.deepEqual(preserved,privateSession);
   await page.evaluate(()=>{localStorage.removeItem('acs_supabase_session_v1');localStorage.removeItem('acs_project_v1');localStorage.removeItem('acs_password_recovery_v1');});
   await page.locator('#guestSignin').click();await page.locator('#acsAuthGoogle').waitFor({state:'visible'});
   assert.equal(new URL(page.url()).searchParams.get('signin'),'1');
   assert.equal(await page.evaluate(()=>window.ACS.guest),false);
   assert.equal(await page.locator('#acsGuestBanner').count(),0);
   diagnostic.phase('journey-passed');
   passed++;await context.close();
  }
  // A real browser with WebGL deliberately unavailable must retain useful,
  // honest 2D content and navigation independently of the failed ESM graph.
  const noGl=await browser.newContext({viewport:{width:393,height:852}}),fallback=await noGl.newPage();
  const fallbackCalls=[];
  await fallback.addInitScript(()=>{
   const original=HTMLCanvasElement.prototype.getContext;
   HTMLCanvasElement.prototype.getContext=function(kind,...args){
    if(['webgl','webgl2','experimental-webgl'].includes(kind))return null;
    return original.call(this,kind,...args);
   };
  });
  await fallback.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.origin!==ORIGIN){fallbackCalls.push(url.pathname);return route.abort();}
   const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
   if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
   return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
  });
  await fallback.goto(ORIGIN+'/');
  await fallback.locator('#acsGuestFallback').waitFor({state:'visible'});
  await fallback.waitForFunction(()=>document.getElementById('acsGuestFallback')?.dataset.engineState==='unavailable');
  assert.equal(await fallback.locator('#acsGuestFallbackPlan rect').count(),4);
  assert.equal(await fallback.locator('#genLLM').isEnabled(),false);
  assert.equal(await fallback.locator('#impFile').isEnabled(),false);
  assert.equal(await fallback.locator('#acsGuestFallback').getAttribute('data-engine-state'),'unavailable');
  await fallback.locator('[data-guest-room]').first().click();
  assert.match(await fallback.locator('#acsGuestFallbackRoom').textContent(),/42/);
  assert.deepEqual(fallbackCalls,[]);
  assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await fallback.locator('#guestFallbackSignin').click();
  await fallback.locator('#acsAuthGoogle').waitFor({state:'visible'});
  assert.equal(new URL(fallback.url()).searchParams.get('signin'),'1');
  await noGl.close();passed++;
  console.log('GUEST WORKSPACE: '+passed+' production-origin journeys passed (desktop/mobile JSON import/download and unsupported files; two guest tabs; denied-storage backup; recovery; no-WebGL)');
 }catch(error){
  for(const diagnostic of diagnostics){try{await diagnostic.failure(error);}catch{console.error('[ACS-GUEST-DIAG] evidence write failed');}}
  throw error;
 }finally{await browser.close();}
}
module.exports={runGuestWorkspaceTests};
if(require.main===module)runGuestWorkspaceTests().catch(e=>{console.error(e);process.exitCode=1;});
