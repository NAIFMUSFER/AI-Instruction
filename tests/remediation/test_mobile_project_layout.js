'use strict';
// Actual shipped HTML/CSS and navigation under the production CSP.
// The shared harness stubs Three.js: these are layout/interaction checks,
// not WebGL rendering or a live paid generation request.
const assert = require('node:assert/strict');
const H = require('./lib_csp_harness.js');
const PW = require('../../tools/pw_chromium.js');
let passed = 0;
function check(name, value) {
  assert.ok(value, name);
  passed++;
  console.log('  ✓ ' + name);
}

(async () => {
  const server = await H.serve();
  let browser;
  try {
    browser = await PW.launch();
    for (const [width, height] of [[320,740], [393,852], [430,932], [800,390]]) {
      const page = await browser.newPage({viewport:{width,height},hasTouch:true});
      await page.route('https://acs-engine.onrender.com/**', route => route.fulfill({
        contentType:'application/json',
        headers:{'Access-Control-Allow-Origin':'*'},
        body:JSON.stringify({ok:true,api_key_configured:true,limits:{gen_hour:8}}),
      }));
      await page.addInitScript(H.VIOLATION_RECORDER);
      await page.goto('http://127.0.0.1:' + server.port + '/');
      await page.waitForFunction(() => window.ACS && window.ACS.ready);
      await page.locator('#lgGo').click();
      if (await page.locator('#panelToggle').getAttribute('aria-expanded') !== 'true')
        await page.locator('#panelToggle').click();
      await page.locator('#acsTabMake').click();
      await page.locator('#descText').scrollIntoViewIfNeeded();
      // Wait for the real sheet transition before measuring its boundaries.
      await page.waitForTimeout(300);
      const layout = await page.evaluate(() => {
        const box = selector => {
          const r = document.querySelector(selector).getBoundingClientRect();
          return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
        };
        return {
          width:innerWidth,overflow:document.documentElement.scrollWidth > innerWidth,
          panel:box('#left'),dock:box('#panelToggle'),otherDock:box('#mobileToolsToggle'),
          close:box('#projectPanelClose'),tabs:box('#left>.tabs'),body:box('#left>.body'),
          fields:['#siteW','#siteD','#nFloors','#bType','#descText'].map(box),
          tabHeights:Array.from(document.querySelectorAll('#left>.tabs button')).map(b=>b.getBoundingClientRect().height),
          toolsHidden:getComputedStyle(document.getElementById('camBar')).display==='none',
          inputFont:parseFloat(getComputedStyle(document.getElementById('descText')).fontSize),
        };
      });
      const label = width + '×' + height;
      check(label + ': no horizontal page overflow', !layout.overflow);
      check(label + ': project sheet stays inside the viewport',
        layout.panel.left >= 7 && layout.panel.right <= width - 7 && layout.panel.top >= 0);
      check(label + ': dock does not overlap the project sheet',
        layout.panel.bottom <= layout.dock.top - 8 && layout.dock.bottom <= height);
      check(label + ': dock actions do not overlap each other',
        layout.otherDock.right <= layout.dock.left - 8);
      check(label + ': fields fit inside their scroll area',
        layout.fields.every(r=>r.left >= layout.body.left && r.right <= layout.body.right));
      check(label + ': tabs retain compact, usable touch targets',
        layout.tabHeights.every(h=>h >= 44 && h <= 50));
      check(label + ': close button fits in the fixed header',
        layout.close.height >= 44 && layout.close.bottom <= layout.tabs.top);
      check(label + ': form has scroll space and iOS-size text',
        layout.body.height >= 80 && layout.inputFont >= 16);
      check(label + ': project and tools are not layered together', layout.toolsHidden);

      await page.locator('#projectPanelClose').click();
      check(label + ': closing the sheet restores dock focus and removes hidden fields from keyboard navigation',
        await page.evaluate(() => document.activeElement.id==='panelToggle'
          && document.getElementById('left').inert
          && document.getElementById('panelToggle').getAttribute('aria-expanded')==='false'));
      await page.locator('#mobileToolsToggle').click();
      const tools = await page.locator('#camBar button').evaluateAll(buttons => buttons.map(b=>{
        const r=b.getBoundingClientRect();
        return {left:r.left,right:r.right,width:r.width,height:r.height,label:b.querySelector('.cam-label').textContent.trim()};
      }));
      check(label + ': all eleven tools have labels and fit horizontally',
        tools.length===11 && tools.every(b=>b.label && b.left>=8 && b.right<=width-8 && b.width>=44 && b.height>=44));
      await page.locator('#camBar [data-view=orbit]').click();
      check(label + ': selecting a camera closes the tool drawer',
        await page.locator('#mobileToolsToggle').getAttribute('aria-expanded')==='false');
      await page.locator('#mobileToolsToggle').click();
      await page.keyboard.press('Escape');
      check(label + ': Escape closes tools and restores focus',
        await page.evaluate(() => document.activeElement.id==='mobileToolsToggle'
          && document.getElementById('camBar').inert));
      await page.locator('#panelToggle').click();
      await page.locator('#mobileToolsToggle').click();
      check(label + ': switching to tools closes the project sheet',
        await page.locator('#panelToggle').getAttribute('aria-expanded')==='false');
      await page.locator('#cbClip').click();
      check(label + ': section controls reopen the project sheet',
        await page.locator('#panelToggle').getAttribute('aria-expanded')==='true');
      check(label + ': navigation introduces no CSP violations',
        await page.evaluate(() => window.__cspViolations.length===0));

      if(width===393){
        await page.setViewportSize({width:1280,height:900});
        // setViewportSize resolves before the page's resize listener is guaranteed
        // to have normalized `inert`. Wait for the real responsive state rather
        // than racing the event loop; a genuine navigation/CSS regression still
        // times out and fails this gate.
        await page.waitForFunction(() =>
          !document.getElementById('left').inert
          && !document.getElementById('camBar').inert
          && getComputedStyle(document.getElementById('camBar')).display==='flex'
          && getComputedStyle(document.getElementById('mobileToolsToggle')).display==='none',
          null,{timeout:2000});
        check('desktop: toolbar and project panel remain accessible after resizing',
          await page.evaluate(() => !document.getElementById('left').inert
            && !document.getElementById('camBar').inert
            && getComputedStyle(document.getElementById('camBar')).display==='flex'
            && getComputedStyle(document.getElementById('mobileToolsToggle')).display==='none'));
      }
      await page.close();
    }
    console.log('MOBILE PROJECT LAYOUT: ' + passed + ' passed, 0 failed (DOM/CSS; WebGL measured separately)');
  } finally {
    if(browser) await browser.close();
    server.close();
  }
})().catch(e=>{console.error(e);process.exitCode=1;});