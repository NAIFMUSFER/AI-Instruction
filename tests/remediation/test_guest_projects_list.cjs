'use strict';
// «مشاريعي على هذا الجهاز»: a draft started from «ابدأ تصميم مبناك» (its own
// URL) must stay findable from the main link, and the page must say how to move
// a project to another device (download the JSON, import it there).
const assert=require('node:assert/strict');
const PW=require('../../tools/pw_chromium.js');
const L=require('./lib_guest_browser.cjs');
const ORIGIN='https://acs-guest-projects.test';
async function run(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const size of L.SIZES){
   const {context,backend}=await L.guestContext(browser,size,ORIGIN);
   // 1. The main link: the sample project, saved on this device.
   const root=await L.openGuest(context,ORIGIN,'?guest=1');
   assert.equal((await root.page.evaluate(()=>window.ACS.persistence.save('PROJECTS_ROOT'))).ok,true);
   const sample=await root.page.evaluate(()=>window.ACS.exportModel());
   // 2. A separate draft with its own URL, holding a 24 m building.
   const draft=await L.openGuest(context,ORIGIN,'?guest=1&new=1');
   const draftUrl=draft.page.url();assert.match(draftUrl,/project=[0-9a-f-]{36}/);
   const model=JSON.parse(JSON.stringify(sample));model.meta.name='عمارة أبو فهد';model.meta.acs_apartment.source='local_brief';model.meta.acs_apartment.width_m=24;model.site.w=24;
   await draft.page.locator('#impFile').setInputFiles({name:'draft.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(model))});
   await draft.page.waitForFunction(()=>window.ACS.exportModel()?.meta?.name==='عمارة أبو فهد');
   assert.equal((await draft.page.evaluate(()=>window.ACS.persistence.save('PROJECTS_DRAFT'))).ok,true);
   await draft.page.close();

   // 3. Back on the main link, the list shows both and links to the draft.
   const page=root.page;await page.reload();
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete');
   await L.press(page,size,'#guestTools');
   const entry=page.locator('#guestProjects');
   assert.equal((await entry.textContent()).trim(),'مشاريعي على هذا الجهاز');
   const box=await entry.boundingBox();assert.ok(box.height>=44,'44px menu entry');
   await L.press(page,size,'#guestProjects');
   const dialog=page.locator('#guestProjectsDialog');await dialog.waitFor({state:'visible'});
   await page.waitForFunction(()=>document.getElementById('guestProjectsList').getAttribute('aria-busy')==='false');
   const rows=await page.locator('#guestProjectsList > li').evaluateAll(items=>items.map(li=>({text:li.innerText,current:li.getAttribute('aria-current'),href:li.querySelector('a')?.getAttribute('href')||null})));
   assert.equal(rows.length,2,size.name+': both local projects are listed '+JSON.stringify(rows));
   assert.equal(rows[0].current,'true');assert.match(rows[0].text,/المشروع المفتوح الآن/);assert.match(rows[0].text,/العمارة التجريبية/);
   const other=rows[1];
   assert.match(other.text,/عمارة أبو فهد/);assert.match(other.text,/24 × 25 م/);assert.match(other.text,/آخر حفظ/);
   assert.equal(other.href,new URL(draftUrl).pathname+new URL(draftUrl).search,size.name+': the row links to the draft');
   // How to move a project to another device, with both actions in place.
   const help=await dialog.innerText();
   assert.match(help,/على هذا الجهاز فقط/);assert.match(help,/نقل مشروع إلى جهاز آخر/);assert.match(help,/JSON/);
   const [download]=await Promise.all([page.waitForEvent('download'),L.press(page,size,'#guestProjectsDownload')]);
   assert.match(download.suggestedFilename(),/\.json$/,'download names a JSON file');
   const [chooser]=await Promise.all([page.waitForEvent('filechooser'),L.press(page,size,'#guestProjectsImport')]);
   assert.ok(chooser,'import opens the file picker');
   await dialog.waitFor({state:'detached'});
   // Following the link opens the draft itself.
   await L.press(page,size,'#guestTools');await L.press(page,size,'#guestProjects');
   await page.waitForFunction(()=>document.getElementById('guestProjectsList').getAttribute('aria-busy')==='false');
   await L.press(page,size,'#guestProjectsList a');
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner').dataset.recovery==='complete'&&window.ACS.exportModel()?.meta?.name==='عمارة أبو فهد');
   assert.equal(page.url(),draftUrl);
   // From the draft, the main project is listed and linked back.
   await L.press(page,size,'#guestTools');await L.press(page,size,'#guestProjects');
   await page.waitForFunction(()=>document.getElementById('guestProjectsList').getAttribute('aria-busy')==='false');
   const back=await page.locator('#guestProjectsList > li').evaluateAll(items=>items.map(li=>({text:li.innerText,current:li.getAttribute('aria-current'),href:li.querySelector('a')?.getAttribute('href')||null})));
   assert.equal(back.length,2,size.name+': the draft lists both projects too');
   assert.match(back[0].text,/عمارة أبو فهد/);assert.equal(back[0].current,'true');
   assert.equal(back[1].href,'/?guest=1',size.name+': the draft links back to the main project');
   assert.match(back[1].text,/3 أدوار · 6 شقق/,size.name+': counts read as Arabic');
   await L.press(page,size,'#guestProjectsClose');
   // A second device, before its first save, describes what is on screen.
   const fresh=await L.guestContext(browser,size,ORIGIN);const device2=await L.openGuest(fresh.context,ORIGIN,'?guest=1');
   await device2.page.evaluate(()=>indexedDB.deleteDatabase('acs_guest_project_v1'));
   await L.press(device2.page,size,'#guestTools');await L.press(device2.page,size,'#guestProjects');
   await device2.page.waitForFunction(()=>document.getElementById('guestProjectsList').getAttribute('aria-busy')==='false');
   const only=await device2.page.locator('#guestProjectsList > li').allInnerTexts();
   assert.equal(only.length,1,size.name+': a new device lists only its own project');
   assert.match(only[0],/العمارة التجريبية/);assert.match(only[0],/لم يُحفظ بعد|آخر حفظ/);assert.doesNotMatch(only[0],/مسودة فارغة/);
   await fresh.context.close();
   assert.deepEqual(root.errors,[]);assert.deepEqual(backend,[]);
   passed++;console.log('GUEST PROJECTS LIST '+size.name+': ok');
   await context.close();
  }
 }finally{await browser.close();}
 assert.equal(passed,2);console.log('PASS test_guest_projects_list (393x852 + 1440x900)');
}
run().catch(error=>{console.error(error);process.exit(1);});
