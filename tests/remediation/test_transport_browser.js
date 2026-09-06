'use strict';
// Real Chromium fetch/body/CSP behavior using the exact shipped transport block.
// This isolated harness does not claim to exercise WebGL, Safari or paid AI.
const assert = require('assert/strict'), http = require('http');
const fs = require('fs'), path = require('path');
const {source, ROOT} = require('./_transport_source.js');
const {chromium} = require('playwright'); // Playwright-managed browser discovery.
const csp = /Content-Security-Policy\s*=\s*"([^"]+)"/.exec(
  fs.readFileSync(path.join(ROOT,'netlify.toml'),'utf8'))[1];
let passed=0, browser, server;
async function check(name,fn){await fn();passed++;console.log('PASS '+name);}
async function main(){
  const script=`window.violations=[];addEventListener('securitypolicyviolation',e=>window.violations.push(e.violatedDirective));
    const __ACS_SHARED={};
    window.apiBase=location.origin;
    window.ACS_API={base:()=>window.apiBase,host:()=>new URL(window.apiBase).host};
    const apiURL=p=>window.apiBase+p;
    ${source()}
    window.callTransport=__ACS_SHARED.acsFetchJSON;`;
  server=http.createServer((req,res)=>{
    if(req.url==='/'){
      res.writeHead(200,{'Content-Type':'text/html','Content-Security-Policy':csp});
      res.end('<!doctype html><html lang="en"><title>Transport regression</title><script src="/harness.js" defer></script><body>Transport regression</body></html>');
    }else if(req.url==='/harness.js'){
      res.writeHead(200,{'Content-Type':'text/javascript'});res.end(script);
    }else if(req.url==='/slow-body'){
      res.writeHead(200,{'Content-Type':'application/json','X-Request-ID':'req_slow'});
      res.write('{"ok":'); // Headers arrive; body deliberately never completes.
    }else if(req.url==='/slow-headers'){
      // The caller's deadline must abort before headers arrive.
    }else{
      res.writeHead(200,{'Content-Type':'application/json'});res.end('{"ok":true}');
    }
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('http://127.0.0.1:'+server.address().port);
  await page.waitForFunction(()=>typeof window.callTransport==='function');
  const call=p=>page.evaluate(async p=>window.callTransport(p,{},1000),p);
  await check('successful real fetch',async()=>assert.equal((await call('/ok')).status,'SUCCESS'));
  await check('deadline aborts headers',async()=>assert.equal((await call('/slow-headers')).status,'TIMEOUT'));
  await check('deadline aborts body and preserves correlation',async()=>{
    const out=await call('/slow-body');assert.equal(out.status,'TIMEOUT');
    assert.equal(out.http,200);assert.equal(out.request_id,'req_slow');
  });
  await check('normal execution has zero CSP violations and page exceptions',async()=>{
    assert.deepEqual(await page.evaluate(()=>window.violations),[]);assert.deepEqual(errors,[]);
  });
  await page.context().setOffline(true);
  await check('offline preflight',async()=>assert.equal((await call('/ok')).status,'NETWORK_OFFLINE'));
  await page.context().setOffline(false);
  // Fulfil only intercepted requests; no live backend/provider call can occur.
  await page.route('https://acs-engine.onrender.com/**',route=>route.fulfill({
    status:200,contentType:'application/json',body:'{"ok":true}',headers:{'Access-Control-Allow-Origin':'https://untrusted.invalid'}}));
  await page.evaluate(()=>{window.apiBase='https://acs-engine.onrender.com';});
  await check('CORS rejection is not diagnosed as DNS',async()=>{
    assert.equal((await call('/cors-test')).status,'NETWORK_ERROR');
  });
  await page.evaluate(()=>{window.apiBase='https://blocked.invalid';});
  await check('CSP rejection is not diagnosed as DNS',async()=>{
    assert.equal((await call('/test')).status,'NETWORK_ERROR');
    await page.waitForFunction(()=>window.violations.includes('connect-src'));
    assert.ok((await page.evaluate(()=>window.violations)).includes('connect-src'));
  });
  assert.deepEqual(errors,[]);
  console.log(`TRANSPORT CHROMIUM: ${passed} passed, 0 failed (isolated transport, not Safari or paid AI)`);
}
main().catch(e=>{console.error(e);console.error(`TRANSPORT CHROMIUM: ${passed} passed, 1 failed`);process.exitCode=1;})
  .finally(async()=>{if(browser)await browser.close();if(server){server.closeAllConnections();await new Promise(r=>server.close(r));}});
