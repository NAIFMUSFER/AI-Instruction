'use strict';
// Real browsers + real local HTTP, using the shipped transport/job client and
// ASGI job adapter. Generation and rendering are controlled fixtures, not LLMs.
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const net=require('node:net');
const path=require('node:path');
const playwright=require('playwright');
const ROOT=path.resolve(__dirname,'../..');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const listener=net.createServer();
 await new Promise(r=>listener.listen(0,'127.0.0.1',r));
 const port=listener.address().port; await new Promise(r=>listener.close(r));
 const proc=spawn('python3',[path.join(__dirname,'async_job_browser_server.py'),String(port)],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
 let diagnostic='';proc.stderr.on('data',d=>{diagnostic=(diagnostic+d).slice(-3000);});
 const base='http://127.0.0.1:'+port;
 let browser;
 try{
  let ready=false;
  for(let n=0;n<100;n++){try{if((await fetch(base+'/counts')).ok){ready=true;break;}}catch(e){}await delay(100);}
  assert.ok(ready,'local server did not boot: '+diagnostic);
  const name=process.env.ACS_TEST_BROWSER||'chromium';
  browser=await playwright[name].launch({headless:true});
  const context=await browser.newContext({viewport:{width:393,height:852}});
  const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);
  await page.click('#genLLM');
  await page.waitForFunction(()=>window.ACS.asyncGeneration.state()?.state==='RUNNING');
  await page.reload();
  await page.locator('#acsJobRecovery').waitFor();
  await page.locator('#acsJobRecovery button').first().click();
  await page.waitForFunction(()=>window.applied?.meta?.type==='villa',{},{timeout:20000});
  assert.equal((await (await fetch(base+'/counts')).json()).calls,1);
  console.log('PASS '+name+' mobile refresh restores the previous job through GET, exactly one generation');
  await context.close();
  const c2=await browser.newContext({viewport:{width:393,height:852}});
  const p2=await c2.newPage();p2.on('pageerror',e=>errors.push(e.message));
  let broken=false;
  await p2.route('**/v1/jobs/*/result',route=>{
   if(!broken){broken=true;return route.abort('connectionfailed');}
   return route.continue();
  });
  await p2.goto(base);await p2.click('#genLLM');
  await p2.waitForFunction(()=>window.ACS.asyncGeneration.state()?.state==='RUNNING');
  await c2.setOffline(true);await delay(3500);await c2.setOffline(false);
  await p2.waitForFunction(()=>window.result?.body?.building?.meta?.type==='villa',{},{timeout:30000});
  assert.ok(broken,'result download interruption was exercised');
  assert.equal((await (await fetch(base+'/counts')).json()).calls,2);
  console.log('PASS '+name+' offline/reconnect and interrupted result download do not duplicate generation');
  assert.deepEqual(errors,[]);
  console.log('PASS '+name+' no page errors');
  await c2.close();
 }finally{if(browser)await browser.close();proc.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
