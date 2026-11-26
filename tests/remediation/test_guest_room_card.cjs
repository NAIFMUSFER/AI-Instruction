'use strict';
// Tapping a room keeps the building on screen and shows a plain Arabic card:
// name, floor, area and dimensions (the same numbers as the floor plan). The
// engineering inspector opens only from «تفاصيل هندسية».
const assert=require('node:assert/strict');
const PW=require('../../tools/pw_chromium.js');
const L=require('./lib_guest_browser.cjs');
const ORIGIN='https://acs-guest-room.test';
async function run(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const size of L.SIZES){
   const {context,backend}=await L.guestContext(browser,size,ORIGIN);
   const {page,errors}=await L.openGuest(context,ORIGIN);
   await L.press(page,size,'#guestViewToggle');
   await page.waitForFunction(()=>window.ACS.guestViewState().mode==='cutaway');
   const point=await L.roomPoint(page);assert.ok(point,size.name+': a room is under the pointer');
   const [,floorKey,roomId]=point.tag.split('|');
   const before=await page.evaluate(()=>JSON.stringify(window.ACS.exportModel()));
   await L.tapAt(page,size,point.x,point.y);
   const card=page.locator('#guestRoomCard');
   await card.waitFor({state:'visible'});

   // The building stays: no full-screen inspector, the canvas keeps most of the screen.
   assert.equal(await page.locator('#acsWorkspace').isVisible(),false,size.name+': the inspector does not cover the building');
   const view=await page.evaluate(()=>{
    const c=document.getElementById('guestRoomCard').getBoundingClientRect(),canvas=document.querySelector('#app canvas');
    let free=0,total=0;
    for(let y=8;y<innerHeight;y+=16)for(let x=8;x<innerWidth;x+=16){total++;if(document.elementFromPoint(x,y)===canvas)free++;}
    return {cardShare:c.width*c.height/(innerWidth*innerHeight),canvasShare:free/total,highlights:0};
   });
   assert.ok(view.cardShare<=0.4,size.name+': the card covers at most 40% of the screen '+view.cardShare.toFixed(2));
   assert.ok(view.canvasShare>=0.4,size.name+': at least 40% of the screen still shows the 3D view '+view.canvasShare.toFixed(2));

   // Plain Arabic facts for the tapped room.
   const facts=await page.evaluate(({floorKey,roomId})=>{
    const model=window.ACS.exportModel(),index=Number(floorKey.slice(1));
    const level=model.levels.find(l=>l.index===index),room=model.floors[level.template].rooms.find(r=>r.id===roomId);
    const t=id=>document.getElementById(id).textContent.trim();
    return {roomName:room.name,name:t('guestRoomName'),where:t('guestRoomWhere'),area:t('guestRoomArea'),size:t('guestRoomSize'),text:document.getElementById('guestRoomCard').innerText};
   },{floorKey,roomId});
   assert.equal(facts.name,facts.roomName,size.name+': card names the tapped room');
   assert.match(facts.where,/الدور|السطح/,size.name+': card names the floor');
   assert.match(facts.area,/^[\d.,]+ م²$/,size.name+': area in m²');
   assert.match(facts.size,/^[\d.,]+ × [\d.,]+ م$/,size.name+': width × depth in metres');
   assert.doesNotMatch(facts.text,/[A-Za-z_]{3,}/,size.name+': no engineering identifiers or English labels on the card');
   assert.equal(await page.locator('#guestRoomClose').getAttribute('aria-label'),'إغلاق بطاقة الغرفة');
   for(const id of ['guestRoomClose','guestRoomPlan','guestRoomDetails']){
    const box=await page.locator('#'+id).boundingBox();assert.ok(box.width>=44&&box.height>=44,size.name+': 44px target '+id);
   }
   assert.match(await page.locator('#acsLiveRegion').textContent(),new RegExp(facts.name),size.name+': selection is announced in Arabic');

   // The plan opens on the same room and agrees on its numbers.
   await L.press(page,size,'#guestRoomPlan');
   await page.locator('#guestPlanDialog').waitFor({state:'visible'});
   const plan=await page.locator('#guestPlanDetails').textContent();
   assert.ok(plan.includes(facts.size)&&plan.includes(facts.area),size.name+': plan and card agree: '+plan);
   await L.press(page,size,'#guestPlanClose');

   // The engineering inspector is one explicit step away.
   await L.press(page,size,'#guestRoomDetails');
   await page.locator('#acsWorkspace').waitFor({state:'visible'});
   assert.equal(await card.isVisible(),false);
   await L.press(page,size,'#guestReturnToModel');
   await page.locator('#acsWorkspace').waitFor({state:'hidden'});

   // Closing and replacing the model retire the card and its colour handlers.
   await L.tapAt(page,size,point.x,point.y);await card.waitFor({state:'visible'});
   await page.keyboard.press('Escape');await card.waitFor({state:'hidden'});
   await L.tapAt(page,size,point.x,point.y);await card.waitFor({state:'visible'});
   assert.ok(await page.locator('#guestRoomColours input[type=color]').count()===1,size.name+': colour actions live on the card');
   await page.evaluate(()=>window.ACS.guestWorkspace.sample('warehouse'));
   await page.waitForFunction(()=>window.ACS.exportModel().site.w===120);
   assert.equal(await card.isVisible(),false,size.name+': a new model retires the card');
   assert.equal(await page.locator('#guestRoomColours').evaluate(el=>el.childElementCount),0);
   assert.notEqual(await page.evaluate(()=>JSON.stringify(window.ACS.exportModel())),before);
   assert.deepEqual(errors,[]);assert.deepEqual(backend,[]);
   passed++;console.log('GUEST ROOM CARD '+size.name+': ok');
   await context.close();
  }
 }finally{await browser.close();}
 assert.equal(passed,2);console.log('PASS test_guest_room_card (393x852 + 1440x900)');
}
run().catch(error=>{console.error(error);process.exit(1);});
