'use strict';
// Drag vs tap on the 3D view (phone touch and desktop mouse). Orbiting the
// building must never select a room: agent 20 opened the inspector with a drag
// that ended 3 px from where it began. Only a short, still, single-pointer tap
// selects; a drag (even out and back), a hold, or a pinch do not.
const assert=require('node:assert/strict');
const PW=require('../../tools/pw_chromium.js');
const L=require('./lib_guest_browser.cjs');
const ORIGIN='https://acs-guest-tap.test';
const opened=page=>page.evaluate(()=>({
 inspector:document.getElementById('acsWorkspace')?.classList.contains('on')===true,
 card:document.getElementById('guestRoomCard')?.hidden===false,
 info:getComputedStyle(document.getElementById('info')).display!=='none',
 live:document.getElementById('acsLiveRegion').textContent}));
async function reset(page){
 await page.evaluate(()=>{window.ACS.workspace?.close?.();window.ACS.guestRoomCard?.close?.();
  const info=document.getElementById('info');info.replaceChildren();info.style.display='none';
  document.getElementById('acsLiveRegion').textContent='';});
}
async function run(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const size of L.SIZES){
   const {context,backend}=await L.guestContext(browser,size,ORIGIN);
   const {page,errors}=await L.openGuest(context,ORIGIN);
   await L.press(page,size,'#guestViewToggle');            // «كشف الدور»: rooms face the camera
   await page.waitForFunction(()=>window.ACS.guestViewState().mode==='cutaway');
   const point=await L.roomPoint(page);assert.ok(point,size.name+': a room is under the pointer');
   const nothing={inspector:false,card:false,info:false,live:''};

   await reset(page);
   await L.gesture(page,size,L.outAndBack(point.x,point.y));
   await page.waitForTimeout(700);
   assert.deepEqual(await opened(page),nothing,size.name+': a drag that ends 3 px from its start is an orbit, not a tap');

   await reset(page);
   await L.gesture(page,size,[[point.x,point.y],[point.x+1,point.y],[point.x+1,point.y+1]],{stepMs:400});
   await page.waitForTimeout(700);
   assert.deepEqual(await opened(page),nothing,size.name+': a still press held for 800 ms is not a tap');

   await reset(page);
   await L.gesture(page,size,[[point.x,point.y],[point.x+30,point.y+4],[point.x+60,point.y+8]]);
   await page.waitForTimeout(700);
   assert.deepEqual(await opened(page),nothing,size.name+': a plain drag is not a tap');

   await reset(page);
   await L.tapAt(page,size,point.x,point.y);
   await page.waitForFunction(()=>document.getElementById('acsLiveRegion').textContent!=='');
   const tapped=await opened(page);
   assert.ok(tapped.inspector||tapped.card,size.name+': a real tap still selects the room');
   assert.deepEqual(errors,[]);assert.deepEqual(backend,[],'guest taps make no backend call');
   passed++;console.log('GUEST TAP GESTURE '+size.name+': ok');
   await context.close();
  }
 }finally{await browser.close();}
 assert.equal(passed,2);console.log('PASS test_guest_tap_gesture (phone touch + desktop mouse)');
}
run().catch(error=>{console.error(error);process.exit(1);});
