'use strict';
// Shared harness for guest browser tests: the shipped public/ tree on a
// production-like HTTPS origin with the real CSP. Every backend request is
// aborted, so no account, provider or cloud call can happen.
const fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.jpg':'image/jpeg','.svg':'image/svg+xml','.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.usdz':'model/vnd.usdz+zip'};
const SIZES=[
 {name:'phone',viewport:{width:393,height:852},isMobile:true,hasTouch:true},
 {name:'desktop',viewport:{width:1440,height:900}},
];
async function guestContext(browser,size,origin,options={}){
 const {name,...device}=size;
 const context=await browser.newContext({...device,acceptDownloads:true,...options});
 context.setDefaultTimeout(30000);
 const backend=[];
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin!==origin||/^\/(?:v1|auth|rest|functions)(?:\/|$)/.test(url.pathname)){backend.push(url.href);return route.abort();}
  const file=path.resolve(PUB,'.'+(url.pathname==='/'?'/index.html':url.pathname));
  if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
  return route.fulfill({status:200,headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP,'x-content-type-options':'nosniff'},body:fs.readFileSync(file)});
 });
 return {context,backend};
}
async function openGuest(context,origin,query=''){
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/'+query);
 await page.waitForFunction(()=>window.ACS?.guestWorkspace&&document.getElementById('acsGuestBanner')?.dataset.recovery==='complete',null,{timeout:60000});
 return {page,errors};
}
// A real finger: CDP touch events produce pointerType=touch pointer events.
async function touchPath(page,points,{stepMs=16}={}){
 const cdp=await page.context().newCDPSession(page);
 const at=p=>[{x:p[0],y:p[1],id:1,radiusX:4,radiusY:4,force:1}];
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:at(points[0])});
 for(const p of points.slice(1)){await page.waitForTimeout(stepMs);await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:at(p)});}
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await cdp.detach();
}
async function mousePath(page,points,{stepMs=16}={}){
 await page.mouse.move(points[0][0],points[0][1]);await page.mouse.down();
 for(const p of points.slice(1)){await page.waitForTimeout(stepMs);await page.mouse.move(p[0],p[1],{steps:2});}
 await page.mouse.up();
}
// Out and back: the finger travels far, then ends 3 px from where it began.
function outAndBack(x,y){return [[x,y],[x+20,y+8],[x+60,y+20],[x+90,y+30],[x+40,y+12],[x+3,y]];}
async function gesture(page,size,points,options){return size.hasTouch?touchPath(page,points,options):mousePath(page,points,options);}
// A screen point over a room wall/floor in the live scene, not under any UI.
async function roomPoint(page){
 return page.evaluate(async()=>{
  const {model,camera}=await import('/app/ui/workspace-ui-wiring.js');
  const {Raycaster,Vector2}=await import('three'),ray=new Raycaster();
  const canvas=document.querySelector('#app canvas');
  for(const ry of [.5,.45,.55,.4,.6])for(const rx of [.4,.45,.35,.5,.3,.55]){
   const x=Math.round(innerWidth*rx),y=Math.round(innerHeight*ry);
   if(document.elementFromPoint(x,y)!==canvas)continue;
   ray.setFromCamera(new Vector2(x/innerWidth*2-1,-y/innerHeight*2+1),camera);
   const hit=ray.intersectObject(model,true).find(h=>h.object.visible);
   const tag=hit?.object.userData.tag||'';
   if(/^(WALL|FLOOR)\|F\d+\|/.test(tag))return {x,y,tag};
  }
  return null;
 });
}
async function press(page,size,selector){return size.hasTouch?page.locator(selector).tap():page.locator(selector).click();}
async function tapAt(page,size,x,y){return size.hasTouch?page.touchscreen.tap(x,y):page.mouse.click(x,y);}
module.exports={ROOT,PUB,SIZES,guestContext,openGuest,touchPath,mousePath,outAndBack,gesture,roomPoint,press,tapAt};
