'use strict';
// Complete shipped UI + real Three.js + actual ASGI delivery, with one controlled
// six-second generation fixture. No live provider call or customer data.
const assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path'), http=require('node:http');
const {spawn}=require('node:child_process');
const PW=require('../../tools/pw_chromium.js');
const ROOT=path.resolve(__dirname,'../..'), PUB=path.join(ROOT,'public');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const PY=String.raw`
import asyncio, json, sys
from pathlib import Path
from fastapi import FastAPI, Request
import uvicorn
from acs_async_jobs import AsyncGenerationMiddleware
app=FastAPI()
calls=0
@app.get('/health')
def health(): return {'ok':True,'api_key_configured':True,'limits':{'gen_hour':8}}
@app.get('/counts')
def counts(): return {'calls':calls}
@app.post('/v1/understand')
async def generate(request:Request):
    global calls
    await request.json()
    calls+=1
    await asyncio.sleep(6)
    building=json.loads(Path('tests/phase3/fixtures/base_fixtures.json').read_text())['villa']
    building['meta']['name']='async-fixture-villa'
    return {'ok':True,'building':building,'rooms':sum(len(f['rooms']) for f in building['floors'].values()),'levels':len(building['levels']),'report':{'requirements':[]}}
app.add_middleware(AsyncGenerationMiddleware)
uvicorn.run(app,host='127.0.0.1',port=int(sys.argv[1]),access_log=False,log_level='warning')
`;
(async()=>{
 const reserved=http.createServer();await new Promise(r=>reserved.listen(0,'127.0.0.1',r));
 const port=reserved.address().port;await new Promise(r=>reserved.close(r));
 const backend='http://127.0.0.1:'+port;
 const proc=spawn('python3',['-c',PY,String(port)],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
 let diagnostic='';proc.stderr.on('data',d=>diagnostic=(diagnostic+d).slice(-3000));
 const csp=/Content-Security-Policy\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
 const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml'};
 const server=http.createServer((rq,rs)=>{
   const u=new URL(rq.url,'http://localhost');
   const f=path.resolve(PUB,'.'+decodeURIComponent(u.pathname==='/'?'/index.html':u.pathname));
   if(!f.startsWith(PUB+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile()){rs.writeHead(404);return rs.end();}
   rs.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream','Content-Security-Policy':csp,'X-Content-Type-Options':'nosniff'});
   fs.createReadStream(f).pipe(rs);
 });
 let browser;
 try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const origin='http://127.0.0.1:'+server.address().port;
  let ready=false;for(let i=0;i<100;i++){try{ready=(await fetch(backend+'/health')).ok;}catch(e){}if(ready)break;await delay(100);}
  assert.ok(ready,'fixture failed to start: '+diagnostic);
  browser=await PW.launch();
  const context=await browser.newContext({viewport:{width:393,height:852},hasTouch:true});
  const page=await context.newPage(), errors=[], submissions=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',d=>d.accept());
  await page.route('https://acs-engine.onrender.com/**',async route=>{
   const req=route.request(), pathname=new URL(req.url()).pathname;
   if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{'access-control-allow-origin':origin,'access-control-allow-headers':'content-type,x-acs-job-id,x-acs-job-token,idempotency-key','access-control-allow-methods':'GET,POST,OPTIONS'}});
   if(req.method()==='POST')submissions.push(pathname);
   const headers=await req.allHeaders();delete headers.host;
   const response=await fetch(backend+pathname,{method:req.method(),headers,
     body:['GET','HEAD'].includes(req.method())?undefined:req.postDataBuffer()});
   const rh=Object.fromEntries(response.headers.entries());
   rh['access-control-allow-origin']=origin;rh['access-control-allow-headers']='content-type,x-acs-job-id,x-acs-job-token,idempotency-key';
   rh['access-control-allow-methods']='GET,POST,OPTIONS';
   await route.fulfill({status:response.status,headers:rh,body:Buffer.from(await response.arrayBuffer())});
  });
  async function openProject(){
   await page.waitForFunction(()=>window.ACS&&window.ACS.ready&&window.ACS.asyncGeneration);
   if(await page.locator('#lgGo').isVisible())await page.locator('#lgGo').click();
   if(await page.locator('#panelToggle').getAttribute('aria-expanded')!=='true')await page.locator('#panelToggle').click();
   await page.locator('#acsTabMake').click();
  }
  await page.goto(origin);await openProject();
  await page.locator('#descText').fill('فيلا اختبار نقل مصطنع، دورين، لا بيانات عميل.');
  await page.locator('#genLLM').click();
  await page.waitForFunction(()=>window.ACS.asyncGeneration.state()?.state==='RUNNING');
  await page.reload();await openProject();
  await page.locator('#acsJobRecovery button').first().click();
  await page.waitForFunction(()=>window.ACS.exportModel()?.meta?.name==='async-fixture-villa',null,{timeout:30000});
  await page.waitForTimeout(1500);
  const proof=await page.evaluate(async()=>{
   const ui=await import('/app/ui/workspace-ui-wiring.js');
   return {apply:ui.ACS_LAST_APPLY,scene:window.ACS.verifyVisibleModel()};
  });
  assert.deepEqual(submissions,['/v1/jobs/understand']);
  assert.equal((await (await fetch(backend+'/counts')).json()).calls,1);
  assert.equal(proof.apply.ok,true,JSON.stringify(proof.apply));
  assert.equal(proof.apply.pixels_verified,true,JSON.stringify(proof.apply));
  assert.ok(proof.scene.canonical_meshes>0);
  assert.deepEqual(errors,[]);
  console.log('PASS shipped mobile page: one POST, reload recovery, canonical model applied and first-frame pixels verified');
  console.log(JSON.stringify({meshes:proof.scene.canonical_meshes,reached:proof.apply.reached,pixels_verified:proof.apply.pixels_verified}));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));proc.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
