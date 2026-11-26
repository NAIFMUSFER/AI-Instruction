'use strict';
// Hiding the roof is a view choice: the roof leaves the screen, never the
// design, the saved draft or the downloaded model.
const assert=require('node:assert/strict');
const PW=require('../../tools/pw_chromium.js');
const L=require('./lib_guest_browser.cjs');
const ORIGIN='https://acs-guest-roof.test';
const meshes=page=>page.evaluate(async()=>{
 const live=await import('/app/ui/workspace-ui-wiring.js');
 const roof=new Set(window.ACS.exportModel().levels.filter(l=>l.kind==='roof').map(l=>'F'+l.index));
 let roofShown=0,roofTotal=0,otherShown=0;
 for(const layer of Object.values(live.registry))for(const m of layer.meshes){
  if(roof.has(m.userData.floor)){roofTotal++;if(m.visible)roofShown++;}else if(m.visible)otherShown++;}
 return {roofShown,roofTotal,otherShown};
});
async function openModelTab(page,size){
 if(size.hasTouch&&await page.locator('#panelToggle').getAttribute('aria-expanded')!=='true')await L.press(page,size,'#panelToggle');
 await L.press(page,size,'#acsTabModel');await page.locator('#localRoofToggle').waitFor({state:'visible'});
}
async function run(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const size of L.SIZES){
   const {context,backend}=await L.guestContext(browser,size,ORIGIN);
   const {page,errors}=await L.openGuest(context,ORIGIN);
   const model=await page.evaluate(()=>window.ACS.exportModel());
   assert.ok(model.levels.some(l=>l.kind==='roof'),'the sample has its default roof');
   await openModelTab(page,size);
   const toggle=page.locator('#localRoofToggle');
   assert.equal((await toggle.textContent()).trim(),'إخفاء السطح');
   assert.equal(await toggle.getAttribute('aria-pressed'),'false');
   assert.match(await page.locator('#localRoofDisclosure').textContent(),/للعرض فقط/);
   const shown=await meshes(page);assert.ok(shown.roofTotal>0&&shown.roofShown===shown.roofTotal);

   await L.press(page,size,'#localRoofToggle');
   assert.equal((await toggle.textContent()).trim(),'إظهار السطح');
   assert.equal(await toggle.getAttribute('aria-pressed'),'true');
   assert.equal(await page.evaluate(()=>document.activeElement?.id),'localRoofToggle','focus stays on the toggle');
   const hidden=await meshes(page);
   assert.equal(hidden.roofShown,0,size.name+': no roof mesh is drawn');
   assert.equal(hidden.otherShown,shown.otherShown,size.name+': every occupied floor stays visible');
   assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,size.name+': the design keeps its roof');
   assert.equal(await page.locator('#localRoofRestore').count(),0,'nothing to restore: the roof was never removed');
   const [download]=await Promise.all([page.waitForEvent('download'),page.evaluate(()=>document.getElementById('bJson').click())]);
   const chunks=[];for await(const c of await download.createReadStream())chunks.push(c);
   const exported=JSON.parse(Buffer.concat(chunks).toString('utf8'));
   assert.match(JSON.stringify(exported),/"kind":"roof"/,size.name+': the downloaded model keeps the roof');

   // Choosing the roof floor itself shows it; «الكل» hides it again.
   await page.locator('#floors').getByRole('button',{name:'السطح',exact:true}).click();
   assert.ok((await meshes(page)).roofShown>0,size.name+': the roof floor is visible when chosen');
   await page.locator('#floors').getByRole('button',{name:'الكل',exact:true}).click();
   assert.equal((await meshes(page)).roofShown,0);

   // The saved draft and a reload keep the roof in the design.
   assert.equal((await page.evaluate(()=>window.ACS.persistence.save('ROOF_VIEW_TEST'))).ok,true);
   await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
   assert.ok((await page.evaluate(()=>window.ACS.exportModel())).levels.some(l=>l.kind==='roof'),size.name+': reload keeps the roof');
   await openModelTab(page,size);
   await L.press(page,size,'#localRoofToggle');await L.press(page,size,'#localRoofToggle');
   const again=await meshes(page);assert.equal(again.roofShown,again.roofTotal,size.name+': showing the roof again draws it');
   assert.deepEqual(errors,[]);assert.deepEqual(backend,[]);
   passed++;console.log('GUEST ROOF VIEW '+size.name+': ok');
   await context.close();
  }
 }finally{await browser.close();}
 assert.equal(passed,2);console.log('PASS test_guest_roof_view (393x852 + 1440x900)');
}
run().catch(error=>{console.error(error);process.exit(1);});
