'use strict';
// First-day guest UI polish: four small, visible defects found on the live site
// (phone 393x852 and desktop 1440x900). The shipped page is served on a
// production-like origin with the real CSP; every backend request is aborted.
//  1. The isolated floor button must look selected and expose aria-pressed.
//  2. Layer visibility checkboxes and colour pickers need accessible names.
//  3. «إزالة السطح الافتراضي» must fit inside its button at phone width.
//  4. The guest revision dialog is centred and the light dialogs' titles are
//     readable (the dark side panel's muted h2 rule must not leak into them).
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.jpg':'image/jpeg','.svg':'image/svg+xml','.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json'};
const ORIGIN='https://acs-guest-polish.test';

function contrast(fg,bg){
 const lum=c=>{const [r,g,b]=c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4;});return .2126*r+.7152*g+.0722*b;};
 const [a,b]=[lum(fg),lum(bg)];return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}
async function openModelTab(page,width){
 if(width<=820&&await page.locator('#panelToggle').getAttribute('aria-expanded')!=='true')await page.locator('#panelToggle').click();
 await page.locator('#acsTabModel').click();
 await page.locator('#floors [data-floor]').first().waitFor({state:'visible'});
}
async function floorStates(page){
 return page.locator('#floors [data-floor]').evaluateAll(buttons=>buttons.map(b=>({
  floor:b.dataset.floor,active:b.classList.contains('active'),pressed:b.getAttribute('aria-pressed'),
  background:getComputedStyle(b).backgroundColor})));
}
function assertSelected(states,floor,stage){
 const active=states.filter(s=>s.active);
 assert.deepEqual(active.map(s=>s.floor),[floor],stage+': exactly one floor is selected');
 for(const s of states)assert.equal(s.pressed,String(s.floor===floor),stage+': aria-pressed mirrors the selection for '+s.floor);
 const selected=states.find(s=>s.floor===floor),other=states.find(s=>s.floor!==floor);
 assert.notEqual(selected.background,other.background,stage+': the selected floor is visibly different');
}

async function run(){
 const browser=await PW.launch();let passed=0;
 try{
  for(const width of [393,1440]){
   const context=await browser.newContext({viewport:{width,height:width===393?852:900}});
   context.setDefaultTimeout(30000);
   const page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==ORIGIN||/^\/(?:v1|auth|rest|functions)(?:\/|$)/.test(url.pathname))return route.abort();
    const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
    if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
    return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
   });
   await page.goto(ORIGIN+'/');
   await page.waitForFunction(()=>window.ACS?.guestWorkspace&&window.ACS.exportModel());
   await page.waitForFunction(()=>document.getElementById('acsGuestBanner').dataset.recovery==='complete');

   // 1 · floor selection is visible and announced, through both entry points.
   await openModelTab(page,width);
   assertSelected(await floorStates(page),'all',width+' initial');
   await page.locator('#floors [data-floor="F1"]').click();
   assertSelected(await floorStates(page),'F1',width+' panel floor');
   if(width<=820)await page.locator('#projectPanelClose').click();
   await page.locator('#guestViewToggle').click();   // «الواجهة» returns to all floors
   await openModelTab(page,width);
   assertSelected(await floorStates(page),'all',width+' banner exterior');
   passed++;

   // 2 · every layer control has a name a screen reader can say.
   const layers=await page.locator('#layers .lay').evaluateAll(rows=>rows.map(row=>{
    const [box,colour]=row.querySelectorAll('input');const name=row.querySelector('.nm').textContent.trim();
    return {name,box:box.getAttribute('aria-label'),colour:colour.getAttribute('aria-label')};}));
   assert.ok(layers.length>=4,'the sample has its layer rows');
   for(const row of layers){
    assert.ok(row.box&&row.box.includes(row.name),'checkbox is named after its layer: '+row.name);
    assert.ok(row.colour&&row.colour.includes(row.name),'colour picker is named after its layer: '+row.name);
   }
   const snapshot=await page.locator('#layers').ariaSnapshot();
   assert.doesNotMatch(snapshot,/- checkbox \[checked\]\s*$/m,'no unnamed checkbox remains');
   passed++;

   // 3 · the roof control's label stays inside its button.
   const spill=await page.locator('#localRoofToggle').evaluate(button=>{
    const range=document.createRange();range.selectNodeContents(button);
    const text=range.getBoundingClientRect(),box=button.getBoundingClientRect();
    return {text:[text.left,text.right],box:[box.left,box.right],height:box.height};});
   assert.ok(spill.text[0]>=spill.box[0]-1&&spill.text[1]<=spill.box[1]+1,width+': roof label fits its button '+JSON.stringify(spill));
   assert.ok(spill.height>=44,'roof control keeps a 44px target');
   passed++;
   if(width<=820)await page.locator('#projectPanelClose').click();

   // 4 · dialogs: centred revision dialog, readable titles.
   await page.locator('#guestTools').click();
   await page.locator('#guestReviseExisting').click();
   const revise=await page.locator('#guestRevisionDialog').evaluate(dialog=>{
    const r=dialog.getBoundingClientRect(),title=document.getElementById('guestRevisionTitle'),s=getComputedStyle(title);
    return {left:r.left,right:innerWidth-r.right,top:r.top,bottom:innerHeight-r.bottom,fg:s.color,bg:getComputedStyle(dialog).backgroundColor,size:parseFloat(s.fontSize)};});
   assert.ok(Math.abs(revise.left-revise.right)<=2,width+': revision dialog is horizontally centred '+JSON.stringify(revise));
   assert.ok(Math.abs(revise.top-revise.bottom)<=2,width+': revision dialog is vertically centred '+JSON.stringify(revise));
   assert.ok(contrast(revise.fg,revise.bg)>=4.5,width+': revision title contrast '+contrast(revise.fg,revise.bg).toFixed(2));
   assert.ok(revise.size>=16,width+': revision title is a heading, not 12px muted text');
   await page.locator('#guestCancelRevision').click();
   await page.locator('#guestPlan').click();
   const plan=await page.locator('#guestPlanDialog').evaluate(dialog=>{
    const s=getComputedStyle(document.getElementById('guestPlanTitle'));
    return {fg:s.color,bg:getComputedStyle(dialog).backgroundColor};});
   assert.ok(contrast(plan.fg,plan.bg)>=4.5,width+': plan title contrast '+contrast(plan.fg,plan.bg).toFixed(2));
   await page.locator('#guestPlanClose').click();
   passed++;

   assert.deepEqual(errors,[],'no page errors');
   await context.close();
   console.log('GUEST UI POLISH '+width+': ok');
  }
 }finally{await browser.close();}
 console.log('PASS test_guest_ui_polish ('+passed+' checks)');
}
run().catch(error=>{console.error(error);process.exit(1);});
