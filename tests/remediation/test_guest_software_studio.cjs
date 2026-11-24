'use strict';
// Exercise the actual fallback only when WebGL creation fails. Both desktop
// and mobile CI jobs retain their own before/after images and upper-floor SVG.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const {serve,origin}=require('./test_public_apartment_journey.cjs');
const width=Number(process.env.ACS_APARTMENT_VIEWPORT)||393;
const out=path.resolve(process.env.ACS_APARTMENT_EVIDENCE||'logs/public-apartment','software-'+width);
const brief='أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور';
const change='خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق';

async function run(){
  fs.mkdirSync(out,{recursive:true});
  const browser=await PW.launch({args:['--disable-webgl']});
  try{
    const context=await browser.newContext({viewport:{width,height:width<600?852:900},serviceWorkers:'block'});
    const denied=[];
    await serve(context,denied);
    const page=await context.newPage();
    page.setDefaultTimeout(60000);
    await page.goto(origin+'/?guest=1&new=1');
    const loaded='#guestSoftwareStudio[data-recovery="complete"]';
    await page.locator(loaded).waitFor();
    const initialUrl=page.url();
    assert.match(initialUrl,/project=[a-f0-9-]{36}/);
    assert.equal(await page.evaluate(()=>window.ACS.exportModel()),null);
    assert.equal(await page.locator('#descText').inputValue(),'');
    await page.locator('#descText').fill(brief);
    await page.locator('#guestSoftwareSubmit').click();
    await page.locator('#guestSoftwareResult').waitFor();
    const canvas=page.locator('#guestSoftwareCanvas');
    await page.locator('#guestSoftwareView').selectOption('top');
    const before=await canvas.evaluate(el=>el.toDataURL());
    const beforeModel=await page.evaluate(()=>window.ACS.exportModel());
    assert.equal(beforeModel.meta.acs_apartment.units_total,8);
    await page.screenshot({path:path.join(out,'before.png')});
    await page.locator('#guestRevise').click();
    await page.locator('#guestRevisionText').fill(change);
    await page.locator('#guestApplyRevision').click();
    await page.locator('#guestRevisionDialog').waitFor({state:'hidden'});
    await page.locator('#guestSoftwareView').selectOption('top');
    assert.notEqual(await canvas.evaluate(el=>el.toDataURL()),before);
    await page.screenshot({path:path.join(out,'after.png')});
    const model=await page.evaluate(()=>window.ACS.exportModel());
    assert.equal(model.meta.acs_apartment.units_total,8);
    for(const row of model.levels.filter(row=>row.kind!=='roof'))assert.equal(model.floors[row.template].courtyards.length,1);
    await page.locator('#guestSoftwareLevel').selectOption('1');
    assert.equal(await page.locator('#guestSoftwareView').inputValue(),'cutaway');
    await page.locator('#guestPlan').click();
    const svg=page.locator('#guestPlanViewport svg');
    assert.equal(await svg.getAttribute('data-level-index'),'1');
    assert.equal(await svg.locator('[data-courtyard-id]').count(),1);
    fs.writeFileSync(path.join(out,'upper-plan.svg'),await svg.evaluate(el=>el.outerHTML));
    await page.locator('#guestPlanClose').click();
    await page.locator('#guestRevise').click();
    await page.locator('#guestRevisionText').fill('خل في كل دور ثلاث شقق');
    await page.locator('#guestApplyRevision').click();
    await page.locator('#guestRevisionError').waitFor({state:'visible'});
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model);
    await page.locator('#guestCancelRevision').click();
    await page.waitForFunction(()=>document.getElementById('guestSaveStatus').textContent==='محفوظ على هذا الجهاز');
    await page.reload();
    await page.locator(loaded).waitFor();
    assert.equal(page.url(),initialUrl);
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model);
    assert.deepEqual(denied,[]);
    fs.writeFileSync(path.join(out,'models.json'),JSON.stringify({brief,change,before:beforeModel,after:model}));
    console.log('PASS software guest studio: blank to eight apartments, changed sky view, upper plan, conflict preserves design, exact saved model restored.');
  }finally{await browser.close();}
}
run().catch(error=>{console.error(error);process.exitCode=1;});
