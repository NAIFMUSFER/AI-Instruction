'use strict';
// Operator-authorized ONE synthetic live generation, only after release gates.
// No provider credentials, customer inputs, raw model or job capabilities logged.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const PW = require('./pw_chromium.js');
const FRONT = 'https://sprightly-selkie-d906c3.netlify.app';
const API = 'https://acs-engine.onrender.com';
const EXPECTED = process.env.ACS_EXPECTED_SHA || '';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let browser, page, phase = 'preflight', posts = 0, receipt = null;
let receiptFailed = false, postStart = null, pageErrors = 0;
const output = {scope:'one synthetic live job; real browser reload; not a physical iPhone test'};
async function jsonGet(path) {
  const response = await fetch(API + path, {signal:AbortSignal.timeout(15000),cache:'no-store'});
  assert.equal(response.status, 200, path + ' unavailable');
  return response.json();
}
async function projectPanel() {
  await page.waitForFunction(() => window.ACS && window.ACS.ready && window.ACS.asyncGeneration,
    null, {timeout:45000});
  if (await page.locator('#lgGo').isVisible()) await page.locator('#lgGo').click();
  if (await page.locator('#panelToggle').getAttribute('aria-expanded') !== 'true')
    await page.locator('#panelToggle').click();
  await page.locator('#acsTabMake').click();
}
(async () => {
  assert.match(EXPECTED, /^[a-f0-9]{40}$/);
  // Reruns must not silently generate another billable request.
  assert.equal(process.env.GITHUB_RUN_ATTEMPT || '1','1','Live generation check is not rerunnable');
  fs.mkdirSync('logs', {recursive:true});
  const version = await jsonGet('/version');
  assert.equal(version.git_sha, EXPECTED, 'Wrong live backend version');
  const health = await jsonGet('/health');
  assert.equal(health.async_generation?.contract, 'acs.async-generation/1.0');
  output.backend_sha = version.git_sha;
  output.storage = health.async_generation.storage;
  output.retention_seconds = health.async_generation.result_retention_seconds;
  output.survives_server_restart = health.async_generation.survives_server_restart;
  output.provider = health.llm?.llm_provider;
  const preflight = await fetch(API + '/v1/jobs/understand', {method:'OPTIONS',
    headers:{Origin:FRONT,'Access-Control-Request-Method':'POST',
      'Access-Control-Request-Headers':'content-type,x-acs-job-id,x-acs-job-token'},
    signal:AbortSignal.timeout(15000)});
  assert.equal(preflight.status, 200);
  assert.equal(preflight.headers.get('access-control-allow-origin'), FRONT);
  const denied = await fetch(API + '/v1/jobs/understand', {method:'OPTIONS',
    headers:{Origin:'https://untrusted.example','Access-Control-Request-Method':'POST'},
    signal:AbortSignal.timeout(15000)});
  assert.equal(denied.status,400);
  assert.equal(denied.headers.get('access-control-allow-origin'),null);
  output.cors = {production:preflight.status,untrusted:denied.status};

  browser = await PW.launch();
  const context = await browser.newContext({viewport:{width:393,height:852},hasTouch:true});
  page = await context.newPage();
  page.on('pageerror', () => pageErrors++);
  page.on('dialog', dialog => dialog.accept());
  phase = 'page_boot';
  await page.goto(FRONT,{waitUntil:'domcontentloaded',timeout:45000});
  await projectPanel();
  const frontSha = await page.evaluate(() => window.ACS_BUILD_INFO.git_sha);
  assert.equal(frontSha, EXPECTED, 'Wrong live frontend version');
  output.frontend_sha = frontSha;
  // Prove the browser itself can read the live service, not only the HTTP client.
  assert.equal(await page.evaluate(async url => {
    const response=await fetch(url,{signal:AbortSignal.timeout(15000)});return response.status;
  },API+'/health'),200);

  // Deliver ONE real POST, deliberately lose its receipt, then reload the tab.
  // Status and result GET requests remain real browser requests, not mocked.
  await page.route(API+'/v1/jobs/understand',async route => {
    if (route.request().method() !== 'POST') return route.continue();
    posts++;
    if(posts>1){receiptFailed=true;return route.abort('failed');}
    postStart=Date.now();
    try {
      const response=await route.fetch({timeout:20000,maxRetries:0});
      const data=await response.json();
      receipt={http:response.status(),id:data.job?.id,state:data.job?.state,
        contract:data.contract,accepted_ms:Date.now()-postStart};
    } catch(e) {receiptFailed=true;}
    await route.abort('failed');
  });
  await page.locator('#siteW').fill('8');
  await page.locator('#siteD').fill('10');
  await page.locator('#nFloors').fill('1');
  await page.locator('#bType').selectOption('residential');
  await page.locator('#descText').fill('اختبار تقني اصطناعي لاستلام النتيجة، لا يمثل مشروع عميل. أنشئ مبنى سكنياً صغيراً من دور واحد داخل أرض 8 في 10 أمتار. غرفة معيشة واحدة فقط أبعادها 4 في 4 أمتار عند x=2 وz=2، بارتفاع 3 أمتار، باب واحد ونافذة واحدة. لا تضف غرفاً أو أدواراً أخرى، ولا أثاثاً أو تفاصيل إضافية.');
  phase='one_live_submission';
  await page.locator('#genLLM').click();
  const deadline=Date.now()+30000;
  while(!receipt && !receiptFailed && Date.now()<deadline)await delay(100);
  assert.ok(receipt && !receiptFailed,'Receipt not verified; never resubmit automatically');
  assert.equal(receipt.http,202);
  assert.equal(receipt.contract,'acs.async-generation/1.0');
  assert.match(receipt.id,/^job_[a-f0-9]{32}$/);
  output.receipt=receipt;
  console.log('LIVE_ACCEPTED',JSON.stringify(receipt));
  phase='reload_and_recover';
  await page.reload({waitUntil:'domcontentloaded',timeout:45000});
  await projectPanel();
  assert.equal((await page.evaluate(()=>window.ACS.asyncGeneration.state())).id,receipt.id);
  await page.locator('#acsJobRecovery button').first().click();
  await page.waitForFunction(()=>window.ACS.asyncGeneration.state()?.delivered===true,
    null,{timeout:600000});
  const state=await page.evaluate(()=>window.ACS.asyncGeneration.state());
  assert.equal(state.id,receipt.id);
  assert.equal(state.state,'SUCCEEDED','Live job completed with a declared error');
  phase='model_application';
  await page.waitForFunction(async()=>{
    const ui=await import('/app/ui/workspace-ui-wiring.js');
    return ui.ACS_LAST_APPLY && !['AWAITING_FIRST_FRAME','CAMERA_FIT_COMPLETE'].includes(ui.ACS_LAST_APPLY.reached);
  },null,{timeout:45000});
  const proof=await page.evaluate(async()=>{
    const ui=await import('/app/ui/workspace-ui-wiring.js');
    const ap=ui.ACS_LAST_APPLY || {};
    const model=window.ACS.exportModel();
    const scene=window.ACS.verifyVisibleModel();
    return {ok:ap.ok,reached:ap.reached,pixels_verified:ap.pixels_verified,
      canonical_meshes:scene.canonical_meshes,levels:model?.levels?.length,
      rooms:Object.values(model?.floors||{}).reduce((n,f)=>n+(f.rooms||[]).length,0)};
  });
  output.proof=proof;output.post_count=posts;output.page_errors=pageErrors;
  assert.equal(posts,1,'More than one submission attempted');
  assert.equal(proof.ok,true,'Live delivery succeeded but model application failed');
  assert.equal(proof.reached,'VISIBLE');
  assert.equal(proof.pixels_verified,true);
  assert.ok(proof.canonical_meshes>0);
  assert.equal(pageErrors,0);
  await page.screenshot({path:'logs/live-synthetic-recovery.png',fullPage:false});
  output.verdict='PASS';phase='complete';
  console.log('LIVE_DELIVERY_VERIFIED',JSON.stringify(output));
})().catch(async error=>{
  output.verdict='FAIL';output.phase=phase;output.post_count=posts;
  output.error_name=String(error?.name||'Error');
  // No exception dump, request headers, capability or raw generated response.
  console.error('LIVE_CHECK_FAILED',JSON.stringify(output));
  process.exitCode=1;
}).finally(async()=>{
  fs.mkdirSync('logs',{recursive:true});
  fs.writeFileSync('logs/live-delivery-proof.json',JSON.stringify(output,null,2));
  if(browser)await browser.close();
});
