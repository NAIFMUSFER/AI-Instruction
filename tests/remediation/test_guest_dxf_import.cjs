'use strict';
// DXF import keeps the drawing's declared size, its north and its room labels.
// The ACS DXF export writes CAD Y = -plan Z (north up) with $INSUNITS=6 (metres);
// importing that convention back must not mirror the plan or rescale it to the site.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'),PUB=path.join(ROOT,'public');
const CSP=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
const MIME={'.jpg':'image/jpeg','.svg':'image/svg+xml','.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.woff2':'font/woff2'};
const ORIGIN='https://acs-guest.test';

function dxf({insunits,rooms}){
  const out=['0','SECTION','2','HEADER'];
  if(insunits!=null)out.push('9','$INSUNITS','70',String(insunits));
  out.push('0','ENDSEC','0','SECTION','2','ENTITIES');
  for(const r of rooms){
    out.push('0','LWPOLYLINE','8','ACS_SPACE_BOUNDARIES','90','4','70','1');
    for(const [x,y] of r.pts)out.push('10',String(x),'20',String(y));
    if(r.label)out.push('0','TEXT','8','ACS_SPACE_LABELS','10',String(r.label[0]),'20',String(r.label[1]),'40','0.3','1',r.label[2]);
  }
  out.push('0','ENDSEC','0','EOF');
  return out.join('\n')+'\n';
}
// North room A (4 x 4 m) above south room B (4 x 6 m), CAD north up.
const rooms=[
  {pts:[[0,0],[4,0],[4,-4],[0,-4]],label:[1,-2,'غرفة شمالية']},
  {pts:[[0,-4],[4,-4],[4,-10],[0,-10]],label:[1,-7,'غرفة جنوبية']},
];
const near=(a,b)=>Math.abs(a-b)<1e-6;

(async()=>{
  const browser=await PW.launch();
  try{
    const ctx=await browser.newContext({viewport:{width:1280,height:860},serviceWorkers:'block'});
    const denied=[];
    await ctx.route('**/*',route=>{
      const u=new URL(route.request().url());
      if(u.origin!==ORIGIN){denied.push(u.href);return route.abort();}
      const file=path.resolve(PUB,'.'+(u.pathname==='/'?'/index.html':u.pathname));
      if(!file.startsWith(PUB+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:''});
      return route.fulfill({body:fs.readFileSync(file),headers:{'content-type':MIME[path.extname(file)]||'application/octet-stream','content-security-policy':CSP}});
    });
    const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(ORIGIN+'/');
    await page.waitForFunction(()=>window.ACS?.exportModel?.()&&document.querySelector('#acsGuestBanner')?.dataset.recovery==='complete',null,{timeout:60000});
    async function importDxf(name,text){
      await page.locator('#impFile').setInputFiles({name,mimeType:'application/dxf',buffer:Buffer.from(text,'utf8')});
      await page.waitForFunction(()=>/DXF ✓/.test(document.getElementById('impInfo')?.textContent||''),null,{timeout:30000});
      return page.evaluate(()=>({model:window.ACS.exportModel(),info:document.getElementById('impInfo').textContent}));
    }
    // 1. Metres declared: true size, north stays north, labels kept.
    const metric=await importDxf('north-south.dxf',dxf({insunits:6,rooms}));
    const [a,b]=metric.model.floors.typical.rooms;
    assert.deepEqual([a.rect[2],a.rect[3]],[4,4],'declared metres keep the north room size');
    assert.deepEqual([b.rect[2],b.rect[3]],[4,6],'declared metres keep the south room size');
    assert.ok(a.rect[1]<b.rect[1],'the CAD-north room stays north (smaller plan Z): '+JSON.stringify([a.rect,b.rect]));
    assert.ok(near(a.rect[1]+a.rect[3],b.rect[1]),'rooms that share a CAD edge still share it');
    assert.equal(a.name,'غرفة شمالية');assert.equal(b.name,'غرفة جنوبية');
    assert.equal(metric.model.meta.north,'-Z');
    assert.equal(metric.model.meta.acs_dxf_import.true_scale,true);
    assert.match(metric.info,/بالأبعاد الفعلية/);
    // 2. Millimetres declared: converted, not fitted to the site.
    const mm=await importDxf('north-south-mm.dxf',dxf({insunits:4,rooms:rooms.map(r=>({...r,pts:r.pts.map(([x,y])=>[x*1000,y*1000]),label:[r.label[0]*1000,r.label[1]*1000,r.label[2]]}))}));
    const [am,bm]=mm.model.floors.typical.rooms;
    assert.ok(near(am.rect[2],4)&&near(am.rect[3],4)&&near(bm.rect[3],6),'millimetre drawings convert to metres');
    assert.ok(am.rect[1]<bm.rect[1]);
    // 3. No declared unit: previous fit-to-site behaviour, disclosed, still not mirrored.
    const unitless=await importDxf('unitless.dxf',dxf({insunits:null,rooms}));
    const [au,bu]=unitless.model.floors.typical.rooms;
    assert.equal(unitless.model.meta.acs_dxf_import.true_scale,false);
    assert.ok(au.rect[2]>4,'a unit-less drawing is still fitted to the site');
    assert.ok(au.rect[1]<bu.rect[1],'a unit-less drawing is not mirrored either');
    assert.match(unitless.info,/بلا وحدة معلنة/);
    assert.deepEqual(errors,[]);assert.deepEqual(denied,[]);
    console.log('guest DXF import: true scale, north and labels preserved');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
