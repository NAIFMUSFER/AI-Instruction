'use strict';
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {chromium, webkit} = require('playwright');

const ROOT = path.resolve(__dirname, '../../public');
let checks = 0;
function ok(name, value){ assert.ok(value, name); checks++; console.log('PASS '+name); }

const HARNESS = `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'"><link rel="stylesheet" href="/harness.css"></head><body><canvas id="c" width="800" height="600"></canvas><div id="acsLiveRegion" role="status"></div><script type="module" src="/harness.mjs"></script></body></html>`;
const CSS = `html,body{margin:0}#c{display:block;width:100vw;height:80vh}#acsLiveRegion{min-height:20px}`;
const JS = `
import {installWorkspaceViewportSelection} from '/app/ui/workspace-viewport-selection.js';
class Vector2 { constructor(){this.x=0;this.y=0;} }
class Raycaster { setFromCamera(){} intersectObject(){return window.__hitMesh ? [{object:window.__hitMesh}] : [];} }
class BoxHelper { constructor(mesh,color){this.source=mesh;this.color=color;this.name='';this.userData={};this.geometry={dispose(){}};this.material={dispose(){}};} }
const THREE={Vector2,Raycaster,BoxHelper};
const canvas=document.getElementById('c');
canvas.getBoundingClientRect=()=>({left:0,top:0,width:800,height:600,right:800,bottom:600});
const make=(name,userData={})=>({name,userData,isMesh:true,visible:true,parent:null,children:[]});
const wall=make('WALL|F0|majlis|wN0'), floor=make('FLOOR|F0|majlis'), door=make('DOOR|F0|majlis|0'), upper=make('WALL|F1|bed1|wN0');
const visual=make('VISUAL|ARCHITECTURE|x',{acs_visual_only:true});
const meshes=[wall,floor,door,upper,visual];
const root={visible:true,children:meshes,traverse(fn){fn(this);meshes.forEach(m=>{m.parent=this;fn(m);});}};
const building={meta:{name:'browser fixture'},levels:[{index:0,template:'ground'},{index:1,template:'upper'}],floors:{ground:{rooms:[{id:'majlis',rect:[0,0,6,5],doors:[{id:'door_guest'}],windows:[]}]},upper:{rooms:[{id:'bed1',rect:[0,0,4,4],doors:[],windows:[]}]}}};
window.__fixture={building,meshes,wall,floor,door,upper,visual,before:JSON.stringify(building)};
window.__scene={items:[],add(x){this.items.push(x)},remove(x){this.items=this.items.filter(y=>y!==x)}};
window.__openCount=0;
window.ACS={};
async function openWorkspace(){window.__openCount++; if(!window.ACS.workspace){window.ACS.workspace={selected:null,opened:false,select(id){this.selected=id;if(window.__ACS_ON_SELECT)window.__ACS_ON_SELECT(id);return id;},open(){this.opened=true;},project(){return {building_id:'bld_0'}}};} return true;}
window.__hitMesh=door;
window.__bridge=installWorkspaceViewportSelection({THREE,renderer:{domElement:canvas},scene:window.__scene,late:{model:root,camera:{},lastBuilding:building},openWorkspace});
`;

(async()=>{
  const server=http.createServer((req,res)=>{
    try{
      const u=new URL(req.url,'http://localhost');
      if(u.pathname==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(HARNESS);}
      if(u.pathname==='/harness.css'){res.writeHead(200,{'Content-Type':'text/css; charset=utf-8'});return res.end(CSS);}
      if(u.pathname==='/harness.mjs'){res.writeHead(200,{'Content-Type':'text/javascript; charset=utf-8'});return res.end(JS);}
      const file=path.resolve(ROOT,'.'+decodeURIComponent(u.pathname));
      if(!file.startsWith(ROOT+path.sep)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
      res.writeHead(200,{'Content-Type':'text/javascript; charset=utf-8'});fs.createReadStream(file).pipe(res);
    }catch(e){res.writeHead(400);res.end();}
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+server.address().port;
  try{
    for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
      const browser=await engine.launch({headless:true});
      try{
        const page=await browser.newPage({viewport:{width:393,height:852}});
        const errors=[]; page.on('pageerror',e=>errors.push(String(e)));
        await page.goto(base+'/');
        await page.waitForFunction(()=>window.__bridge&&window.__bridge.installed===true);
        ok(name+' bridge installs on mobile viewport',await page.evaluate(()=>window.__bridge.installed===true));
        await page.locator('#c').dispatchEvent('pointerdown',{clientX:100,clientY:100,pointerId:1,button:0,isPrimary:true});
        await page.locator('#c').dispatchEvent('pointerup',{clientX:100,clientY:100,pointerId:1,button:0,isPrimary:true});
        await page.waitForFunction(()=>window.ACS.workspace&&window.ACS.workspace.selected==='door_guest');
        ok(name+' exact door click opens existing workspace and selects canonical door',await page.evaluate(()=>window.__openCount===1&&window.ACS.workspace.opened&&window.ACS.workspace.selected==='door_guest'));
        ok(name+' selection writes an accessible status without changing model',await page.evaluate(()=>document.getElementById('acsLiveRegion').textContent.includes('door_guest')&&JSON.stringify(window.__fixture.building)===window.__fixture.before));
        ok(name+' selection highlight is presentation-only outside canonical model',await page.evaluate(()=>window.__scene.items.length===1&&window.__scene.items[0].userData.presentation_context===true&&window.__scene.items[0].source===window.__fixture.door));

        await page.evaluate(()=>{window.__hitMesh=window.__fixture.wall;});
        await page.locator('#c').dispatchEvent('pointerdown',{clientX:100,clientY:100,pointerId:2,button:0,isPrimary:true});
        await page.locator('#c').dispatchEvent('pointerup',{clientX:140,clientY:130,pointerId:2,button:0,isPrimary:true});
        ok(name+' orbit-like drag does not become an engineering selection',await page.evaluate(()=>window.ACS.workspace.selected==='door_guest'));

        await page.locator('#c').dispatchEvent('pointerdown',{clientX:120,clientY:120,pointerId:3,button:0,isPrimary:true});
        await page.locator('#c').dispatchEvent('pointerup',{clientX:121,clientY:121,pointerId:3,button:0,isPrimary:true});
        await page.waitForFunction(()=>window.ACS.workspace.selected==='bld_0.ground.majlis');
        ok(name+' derived wall click selects owning canonical space honestly',await page.evaluate(()=>window.ACS.workspace.selected==='bld_0.ground.majlis'&&document.getElementById('acsLiveRegion').textContent.includes('جزء مشتق')));
        ok(name+' owning-space highlight finds wall/floor only, not opening',await page.evaluate(()=>window.__scene.items.length===2&&window.__scene.items.every(h=>/^(WALL|FLOOR)\|F0\|majlis/.test(h.source.name))));

        await page.evaluate(()=>window.ACS.workspace.select('bld_0.upper.bed1'));
        ok(name+' tree/inspector selection drives the same viewport highlight identity',await page.evaluate(()=>window.__scene.items.length===1&&window.__scene.items[0].source===window.__fixture.upper));

        await page.evaluate(()=>{window.__hitMesh=window.__fixture.visual;});
        const visualResult=await page.evaluate(()=>window.__bridge.hitAt(50,50));
        ok(name+' visual-only hit fails closed',visualResult===null);
        ok(name+' canonical model remains byte-identical through all selection paths',await page.evaluate(()=>JSON.stringify(window.__fixture.building)===window.__fixture.before));
        ok(name+' no browser script errors',errors.length===0);
        await page.close();
      } finally { await browser.close(); }
    }
    console.log(`WORKSPACE VIEWPORT BROWSER: ${checks} assertions passed in Chromium + WebKit.`);
  } finally { await new Promise(r=>server.close(r)); }
})().catch(e=>{console.error(e);process.exitCode=1;});
