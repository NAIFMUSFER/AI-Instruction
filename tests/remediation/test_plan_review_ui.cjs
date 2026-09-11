'use strict';
// Real Chromium/WebKit + real Python-generated review packets. No live API/LLM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {chromium, webkit} = require('playwright');
const ROOT=path.resolve(__dirname,'../../public');
const FIX=path.resolve(__dirname,'../../logs/review-fixtures');
let assertions=0;
function check(name,value){assert.ok(value,name);assertions++;console.log('PASS '+name);}
function encoded(p){const payload_json=JSON.stringify(p);return JSON.stringify({schema:'acs.plan-review-file/1.0',payload_json,payload_sha256:crypto.createHash('sha256').update(payload_json).digest('hex')});}
(async()=>{
  const server=http.createServer((req,res)=>{
    try{
      let name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(name.endsWith('/'))name+='index.html';
      const file=path.resolve(ROOT,'.'+name);
      if(!file.startsWith(ROOT+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end();}
      const type={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[path.extname(file)]||'application/octet-stream';
      res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});fs.createReadStream(file).pipe(res);
    }catch{res.writeHead(400);res.end();}
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+server.address().port;
  fs.mkdirSync('logs/review-screenshots',{recursive:true});
  try{
    for(const[name,engine]of[['chromium',chromium],['webkit',webkit]]){
      const browser=await engine.launch({headless:true});
      try{
        for(const width of[320,393,800,1280]){
          const page=await browser.newPage({viewport:{width,height:900}});const external=[];const errors=[];
          page.on('pageerror',e=>errors.push(String(e)));
          await page.route('**/*',route=>{if(route.request().url().startsWith(base+'/'))return route.continue();external.push(route.request().url());return route.abort();});
          await page.addInitScript(()=>{window.__violations=[];document.addEventListener('securitypolicyviolation',e=>window.__violations.push(e.violatedDirective));});
          await page.goto(base+'/plan-review/');
          check(name+width+' empty without sample data',await page.locator('#empty').isVisible()&&await page.locator('#plan .space').count()===0);
          await page.locator('#files').setInputFiles(path.join(FIX,'warehouse.acs-review.json'));
          await page.waitForSelector('#workspace:not([hidden])');
          check(name+width+' real warehouse projection',await page.locator('#plan .space').count()===4);
          check(name+width+' recorded warehouse locks visible',(await page.locator('#locks').textContent()).includes('rack_a')&&(await page.locator('#locks').textContent()).includes('dock_n1'));
          await page.locator('#spaces button').first().click();
          check(name+width+' source identity selectable',(await page.locator('#selection').textContent()).includes('source_id'));
          await page.locator('#plan .space').nth(1).focus();await page.keyboard.press('Enter');
          check(name+width+' keyboard selects exact room',await page.locator('#plan .space').nth(1).getAttribute('aria-pressed')==='true');
          const before=await page.locator('#plan').getAttribute('viewBox');await page.locator('#zoomIn').click();
          check(name+width+' zoom only affects viewBox',before!==await page.locator('#plan').getAttribute('viewBox'));
          await page.locator('#fit').click();check(name+width+' fit restores exact viewport',before===await page.locator('#plan').getAttribute('viewBox'));
          check(name+width+' no page horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
          if(width===393||width===1280)await page.screenshot({path:`logs/review-screenshots/${name}-${width}.png`,fullPage:true});
          await page.locator('#files').setInputFiles([path.join(FIX,'warehouse.acs-review.json'),path.join(FIX,'residential.acs-review.json')]);
          await page.waitForFunction(()=>document.querySelector('#revision').options.length===2);
          await page.locator('#revision').selectOption('1');
          check(name+width+' residential version selection',(await page.locator('#spaces').textContent()).includes('المجلس')&&await page.locator('#plan .space').count()===2);
          const f=JSON.parse(fs.readFileSync(path.join(FIX,'residential.acs-review.json'),'utf8'));f.payload_json+=' ';
          await page.locator('#files').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(f))});
          await page.waitForSelector('#error:not([hidden])');
          check(name+width+' corrupt file clears stale drawing',await page.locator('#plan .space').count()===0&&await page.locator('#workspace').isHidden());
          if(width===393){
            const p=JSON.parse(JSON.parse(fs.readFileSync(path.join(FIX,'residential.acs-review.json'),'utf8')).payload_json);
            p.projections[0].primitives[0].label='<img src=x onerror="window.PWNED=true">';
            await page.locator('#files').setInputFiles({name:'text.json',mimeType:'application/json',buffer:Buffer.from(encoded(p))});
            await page.waitForSelector('#workspace:not([hidden])');
            check(name+' model labels are text, not markup',await page.locator('#plan img').count()===0&&!await page.evaluate(()=>window.PWNED));
            const raw=encoded(p);
            await page.evaluate(async raw=>{const m=await import('/plan-review/review.mjs');window.__pending=m.importFiles([{size:raw.length,text:()=>new Promise(resolve=>{window.__release=()=>resolve(raw);})}]);},raw);
            await page.locator('#clear').click();await page.evaluate(async()=>{window.__release();await window.__pending;});
            check(name+' late import cannot resurrect cleared data',await page.locator('#workspace').isHidden());
          }
          check(name+width+' no API uploads or outside requests',external.length===0);
          check(name+width+' no CSP violations',await page.evaluate(()=>window.__violations.length===0));
          check(name+width+' no script errors',errors.length===0);
          check(name+width+' no browser persistence',await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
          await page.close();
        }
      }finally{await browser.close();}
    }
    console.log(`PLAN REVIEW UI: ${assertions} assertions passed; 2 engines, 4 viewport widths. Synthetic input, no production/provider claim.`);
  }finally{await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
