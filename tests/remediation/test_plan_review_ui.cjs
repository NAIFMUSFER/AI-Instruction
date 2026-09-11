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
// Playwright 1.62.1 injects a temporary `body {}` stylesheet when preparing
// WebKit screenshots. Keep that tooling side effect out of the interaction page;
// do not weaken CSP or discard violations from the page under test.
async function captureReviewEvidence(browser,name,width,base) {
  const page=await browser.newPage({viewport:{width,height:900}});
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(String(e)));
  try {
    await page.route('**/*',route=>{if(route.request().url().startsWith(base+'/'))return route.continue();external.push(route.request().url());return route.abort();});
    await page.addInitScript(()=>{
      window.__captureViolations=[];window.__captureStyles=[];
      document.addEventListener('securitypolicyviolation',e=>window.__captureViolations.push({directive:e.violatedDirective,blockedURI:e.blockedURI,sourceFile:e.sourceFile,disposition:e.disposition}));
      new MutationObserver(records=>{
        for(const r of records)for(const n of r.addedNodes)
          if(n.nodeName==='STYLE')window.__captureStyles.push(n.textContent);
      }).observe(document,{childList:true,subtree:true});
    });
    await page.goto(base+'/plan-review/');
    await page.locator('#files').setInputFiles(path.join(FIX,'warehouse.acs-review.json'));
    await page.waitForSelector('#workspace:not([hidden])');
    await page.locator('#plan .space').nth(1).focus();await page.keyboard.press('Enter');
    check(name+width+' isolated screenshot starts CSP-clean',await page.evaluate(()=>window.__captureViolations.length===0&&window.__captureStyles.length===0));
    const drawing=await page.locator('#plan').evaluate(e=>e.outerHTML);
    await page.screenshot({path:`logs/review-screenshots/${name}-${width}.png`,fullPage:true,caret:'initial'});
    const evidence=await page.evaluate(()=>({violations:window.__captureViolations,insertedStyles:window.__captureStyles}));
    fs.writeFileSync(`logs/review-screenshots/${name}-${width}-capture.json`,JSON.stringify(evidence,null,2));
    const knownWebKitInjector=name==='webkit'&&evidence.violations.length===1
      &&evidence.insertedStyles.length===1&&evidence.insertedStyles[0]==='body {}'
      &&evidence.violations.every(e=>e.directive==='style-src-elem'&&e.blockedURI==='inline'&&e.sourceFile===''&&e.disposition==='enforce');
    check(name+width+' screenshot diagnostic is empty or the exact Playwright injector',evidence.violations.length===0||knownWebKitInjector);
    console.log('SCREENSHOT_TOOLING '+name+width+' '+JSON.stringify(evidence));
    check(name+width+' screenshot preserves exact SVG',drawing===await page.locator('#plan').evaluate(e=>e.outerHTML));
    check(name+width+' screenshot has no script errors or external requests',errors.length===0&&external.length===0);
  } finally { await page.close(); }
}
async function verifyCspNegativeControl(browser,name,base) {
  // A separate local page proves that a genuine injected inline stylesheet is
  // still denied and observed. No violations are erased from interaction pages.
  const page=await browser.newPage();
  try {
    await page.addInitScript(()=>{
      window.__controlViolations=[];
      document.addEventListener('securitypolicyviolation',e=>window.__controlViolations.push({directive:e.violatedDirective,blockedURI:e.blockedURI}));
    });
    await page.goto(base+'/plan-review/');
    check(name+' CSP negative control starts clean',await page.evaluate(()=>window.__controlViolations.length===0));
    const before=await page.evaluate(()=>getComputedStyle(document.body).color);
    await page.evaluate(()=>{const s=document.createElement('style');s.textContent='body { color: rgb(1, 2, 3) !important; }';document.head.append(s);});
    await page.waitForFunction(()=>window.__controlViolations.length>0,null,{timeout:5000});
    check(name+' CSP still rejects actual inline styles',await page.evaluate(()=>window.__controlViolations.some(e=>e.directive.startsWith('style-src')&&e.blockedURI==='inline')));
    check(name+' blocked style cannot change page appearance',before===await page.evaluate(()=>getComputedStyle(document.body).color));
  } finally { await page.close(); }
}
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
          page.on('console',m=>{if(m.text().startsWith('REVIEW_CSP_DIAGNOSTIC '))console.log(name+width+' '+m.text());});
          await page.addInitScript(()=>{
            window.__violations=[];window.__testPhase='startup';
            document.addEventListener('securitypolicyviolation',e=>{
              const detail={phase:window.__testPhase,directive:e.violatedDirective,effectiveDirective:e.effectiveDirective,blockedURI:e.blockedURI,sourceFile:e.sourceFile,line:e.lineNumber,disposition:e.disposition};
              window.__violations.push(detail);console.error('REVIEW_CSP_DIAGNOSTIC '+JSON.stringify(detail));
            });
          });
          const phase=async stage=>page.evaluate(stage=>{window.__testPhase=stage;},stage);
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
          if(width===393||width===1280)await captureReviewEvidence(browser,name,width,base);
          await phase('revision-import');
          await page.locator('#files').setInputFiles([path.join(FIX,'warehouse.acs-review.json'),path.join(FIX,'residential.acs-review.json')]);
          await page.waitForFunction(()=>document.querySelector('#revision').options.length===2);
          await page.locator('#revision').selectOption('1');
          check(name+width+' residential version selection',(await page.locator('#spaces').textContent()).includes('المجلس')&&await page.locator('#plan .space').count()===2);
          await phase('corrupt-file');
          const f=JSON.parse(fs.readFileSync(path.join(FIX,'residential.acs-review.json'),'utf8'));f.payload_json+=' ';
          await page.locator('#files').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(f))});
          await page.waitForSelector('#error:not([hidden])');
          check(name+width+' corrupt file clears stale drawing',await page.locator('#plan .space').count()===0&&await page.locator('#workspace').isHidden());
          if(width===393){
            await phase('plain-text-label');
            const p=JSON.parse(JSON.parse(fs.readFileSync(path.join(FIX,'residential.acs-review.json'),'utf8')).payload_json);
            p.projections[0].primitives[0].label='<img src=x onerror="window.PWNED=true">';
            await page.locator('#files').setInputFiles({name:'text.json',mimeType:'application/json',buffer:Buffer.from(encoded(p))});
            await page.waitForSelector('#workspace:not([hidden])');
            check(name+' model labels are text, not markup',await page.locator('#plan img').count()===0&&!await page.evaluate(()=>window.PWNED));
            await phase('dynamic-import-race-harness');
            const raw=encoded(p);
            await page.evaluate(async raw=>{const m=await import('/plan-review/review.mjs');window.__pending=m.importFiles([{size:raw.length,text:()=>new Promise(resolve=>{window.__release=()=>resolve(raw);})}]);},raw);
            await page.locator('#clear').click();await page.evaluate(async()=>{window.__release();await window.__pending;});
            check(name+' late import cannot resurrect cleared data',await page.locator('#workspace').isHidden());
          }
          check(name+width+' no API uploads or outside requests',external.length===0);
          const cspEvidence=await page.evaluate(()=>window.__violations);
          fs.writeFileSync(`logs/review-screenshots/${name}-${width}-csp.json`,JSON.stringify(cspEvidence,null,2));
          check(name+width+' no CSP violations',await page.evaluate(()=>window.__violations.length===0));
          check(name+width+' no script errors',errors.length===0);
          check(name+width+' no browser persistence',await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
          await page.close();
        }
        await verifyCspNegativeControl(browser,name,base);
      }finally{await browser.close();}
    }
    console.log(`PLAN REVIEW UI: ${assertions} assertions passed; 2 engines, 4 viewport widths. Synthetic input, no production/provider claim.`);
  }finally{await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
