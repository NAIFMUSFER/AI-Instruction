'use strict';
// Exercise the actual fallback only when WebGL creation fails. Both desktop
// and mobile CI jobs retain their own before/after images and upper-floor SVG.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const PW=require('../../tools/pw_chromium.js');
const {serve,origin,sourceSHA,sourceTreeDirty}=require('./test_public_apartment_journey.cjs');
const {inspect}=require('./test_guest_brief_variations.cjs');
const width=Number(process.env.ACS_APARTMENT_VIEWPORT)||393;
assert.ok([393,1440].includes(width),'software fallback viewport must be 393 or 1440');
const out=path.resolve(process.env.ACS_APARTMENT_EVIDENCE||'logs/public-apartment','software-courtyard-'+width+'-'+sourceSHA.slice(0,12));
const brief='أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور';
const change='خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق';

async function run(){
  fs.mkdirSync(out,{recursive:true});
  const denied=[],errors=[];
  const report={sourceSHA,sourceTreeDirty,width,rendering:'canvas with WebGL disabled',syntheticBrief:true,result:'INCOMPLETE',phase:'browser_launch'};
  let page;
  const browser=await PW.launch({args:['--disable-webgl']});
  try{
    const context=await browser.newContext({viewport:{width,height:width<600?852:900},serviceWorkers:'block'});
    await serve(context,denied);
    page=await context.newPage();
    page.on('pageerror',error=>errors.push(error.name+': '+error.message));
    page.setDefaultTimeout(60000);
    report.phase='open_blank_project';
    await page.goto(origin+'/?guest=1&new=1');
    const loaded='#guestSoftwareStudio[data-recovery="complete"]';
    await page.locator(loaded).waitFor();
    const initialUrl=page.url();
    report.checkedBuild=await page.evaluate(()=>window.ACS_BUILD_INFO?.git_sha||null);
    assert.equal(report.checkedBuild,sourceSHA,'fallback runs against the exact candidate or published source SHA');
    assert.match(initialUrl,/project=[a-f0-9-]{36}/);
    assert.equal(await page.evaluate(()=>window.ACS.exportModel()),null);
    assert.equal(await page.locator('#descText').inputValue(),'');
    report.phase='generate_from_blank';
    await page.locator('#descText').fill(brief);
    await page.locator('#guestSoftwareSubmit').click();
    await page.locator('#guestSoftwareResult').waitFor();
    const canvas=page.locator('#guestSoftwareCanvas');
    await page.locator('#guestSoftwareView').selectOption('top');
    const before=await canvas.evaluate(el=>el.toDataURL());
    const beforeModel=await page.evaluate(()=>window.ACS.exportModel());
    assert.equal(beforeModel.meta.acs_apartment.units_total,8);
    report.before=inspect(beforeModel,{width:24,depth:28,floors:4});
    await page.screenshot({path:path.join(out,'before.png')});
    report.phase='revise_same_project_courtyard';
    await page.locator('#guestRevise').click();
    await page.locator('#guestRevisionText').fill(change);
    await page.locator('#guestApplyRevision').click();
    await page.locator('#guestRevisionDialog').waitFor({state:'hidden'});
    await page.locator('#guestSoftwareView').selectOption('top');
    assert.notEqual(await canvas.evaluate(el=>el.toDataURL()),before);
    await page.screenshot({path:path.join(out,'after.png')});
    const model=await page.evaluate(()=>window.ACS.exportModel());
    assert.equal(model.meta.acs_apartment.units_total,8);
    report.after=inspect(model,{width:24,depth:28,floors:4,courtyard:true});
    for(const row of model.levels.filter(row=>row.kind!=='roof'))assert.equal(model.floors[row.template].courtyards.length,1);
    report.phase='upper_floor_plan';
    await page.locator('#guestSoftwareLevel').selectOption('1');
    assert.equal(await page.locator('#guestSoftwareView').inputValue(),'cutaway');
    await page.locator('#guestPlan').click();
    const svg=page.locator('#guestPlanViewport svg');
    assert.equal(await svg.getAttribute('data-level-index'),'1');
    assert.equal(await svg.locator('[data-courtyard-id]').count(),1);
    // Wait for a usable rendered sheet, including its asynchronously loaded
    // styling. This checks the actual dialog, not a stylesheet/link marker.
    await page.waitForFunction(()=>{
      const dialog=document.getElementById('guestPlanDialog');
      return dialog?.open && parseFloat(getComputedStyle(dialog).borderRadius)>=6 &&
        [...dialog.querySelectorAll('button,select')].every(el=>el.getBoundingClientRect().height>=43);
    });
    report.planLayout=await page.evaluate(()=>{
      const dialog=document.getElementById('guestPlanDialog'),view=document.getElementById('guestPlanViewport');
      const rect=el=>{const r=el.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
      const style=getComputedStyle(dialog);
      return {modal:dialog.matches(':modal'),viewport:{width:innerWidth,height:innerHeight},
        documentWidth:document.documentElement.scrollWidth,bounds:rect(dialog),view:rect(view),svg:rect(view.querySelector('svg')),
        scrollWidth:dialog.scrollWidth,clientWidth:dialog.clientWidth,
        style:{fontSize:parseFloat(style.fontSize),borderWidth:parseFloat(style.borderTopWidth),borderRadius:parseFloat(style.borderRadius),display:style.display},
        controls:[...dialog.querySelectorAll('button,select')].map(el=>{
          const box=rect(el),hit=document.elementFromPoint((box.left+box.right)/2,(box.top+box.bottom)/2);
          return {id:el.id,...box,enabled:!el.disabled,reachable:el===hit||el.contains(hit)};
        })};
    });
    await page.screenshot({path:path.join(out,'upper-plan.png')});
    const layout=report.planLayout;
    assert.equal(layout.modal,true,'upper-floor plan must be a real visible modal');
    assert.ok(layout.style.fontSize>=14&&layout.style.borderWidth<=2&&layout.style.borderRadius>=6,'plan must display readable application styling, not an unstyled native dialog');
    assert.ok(layout.bounds.left>=4&&layout.bounds.right<=layout.viewport.width-4&&layout.bounds.top>=0&&layout.bounds.bottom<=layout.viewport.height+1,'whole plan dialog must fit the actual viewport');
    assert.ok(Math.abs((layout.bounds.left+layout.bounds.right)/2-layout.viewport.width/2)<=2,'plan dialog must be centered at both viewport sizes');
    assert.ok(layout.scrollWidth<=layout.clientWidth+1&&layout.documentWidth<=layout.viewport.width+1,'plan must not cause horizontal page or dialog overflow');
    assert.ok(layout.view.height>=120&&layout.svg.width>200&&layout.svg.left>=layout.view.left-1&&layout.svg.right<=layout.view.right+1,'upper-floor drawing must be visible and fit the plan viewport');
    for(const control of layout.controls){
      assert.ok(control.height>=43&&control.width>=43&&control.enabled&&control.reachable,'plan control must be usable: '+control.id);
      assert.ok(control.left>=layout.bounds.left&&control.right<=layout.bounds.right+1&&control.top>=layout.bounds.top&&control.bottom<=layout.bounds.bottom+1,'plan control must remain within dialog: '+control.id);
    }
    fs.writeFileSync(path.join(out,'upper-plan.svg'),await svg.evaluate(el=>el.outerHTML));
    await page.locator('#guestPlanClose').click();
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model,'software plan view must not modify source');
    report.phase='reject_unsupported_revision';
    await page.locator('#guestRevise').click();
    await page.locator('#guestRevisionText').fill('خل في كل دور ثلاث شقق');
    await page.locator('#guestApplyRevision').click();
    await page.locator('#guestRevisionError').waitFor({state:'visible'});
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model);
    await page.locator('#guestCancelRevision').click();
    report.phase='reload_exact_saved_project';
    await page.waitForFunction(()=>document.getElementById('guestSaveStatus').textContent==='محفوظ على هذا الجهاز');
    await page.reload();
    await page.locator(loaded).waitFor();
    assert.equal(page.url(),initialUrl);
    assert.deepEqual(await page.evaluate(()=>window.ACS.exportModel()),model);
    assert.deepEqual(denied,[]);assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'models.json'),JSON.stringify({sourceSHA,brief,change,before:beforeModel,after:model}));
    report.result='PASS';
    console.log('PASS software guest studio: blank to eight apartments, changed sky view, upper plan, conflict preserves design, exact saved model restored.');
  }catch(error){
    report.result='FAIL';report.error=String(error.stack||error);
    if(page)await page.screenshot({path:path.join(out,'failure.png'),timeout:8000}).catch(()=>{});
    throw error;
  }finally{
    report.forbiddenRequests=denied;report.pageErrors=errors;
    fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify(report,null,2));
    await browser.close();
  }
}
if(require.main===module)run().catch(error=>{console.error(error);process.exitCode=1;});
