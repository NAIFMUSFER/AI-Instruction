/* دخول لوحات العمل بلوحة المفاتيح: قياس DOM حقيقي تحت CSP الإنتاج.
   نستعمل اللوحات المولّدة كما هي؛ يُستبدل جسر الرسم فقط لأن هذا اختبار
   تركيز، لا قياس بكسلات أو GPU. لا اتصال بالخادم ولا نداء توليد مدفوع. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const PW = require('../../tools/pw_chromium.js');
const H = require('./lib_csp_harness.js');
const ROOT = path.resolve(__dirname, '../..');
const ENTRY = fs.readFileSync(path.join(ROOT, 'public/app/ui/panels-entry.js'), 'utf8');
const GRAPH = [
  'shared-state.js', 'late-bindings.js', 'core/viewer.js', 'core/standards.js',
  'core/disciplines.js', 'generated/runtime.js', 'generated/authoring.js',
  'generated/pbr.js', 'ui/panels-entry.js',
];
const MAIN = GRAPH.map(name => "import '/app/" + name + "';").join('\n')
  + '\nwindow.ACS.exportModel = () => window.__ACS_AUDIT_MODEL || null;';
const PANELS = [
  ['pbr', 'acsOpenPbr', 'pqPanel', 'pqClose'],
  ['workspace', 'acsOpenWorkspace', 'acsWorkspace', null],
  ['render', 'acsOpenRender', 'rvPanel', 'rvClose'],
  ['bim', 'acsOpenBim', 'bxPanel', 'bxClose'],
  ['docs', 'acsOpenDocs', 'dcPanel', 'dcClose'],
  ['archdetail', 'acsOpenDetail', 'adPanel', 'adClose'],
];

async function measure(browser, entrySource) {
  const server = await H.serve({ overrides: {
    '/app/main.js': MAIN,
    '/app/ui/panels-entry.js': entrySource,
    '/app/generated/arch-detail-bridge.js': '/* الرسم خارج نطاق اختبار التركيز */',
  } });
  const page = await browser.newPage();
  const rows = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.addInitScript(H.VIOLATION_RECORDER);
    await page.goto('http://127.0.0.1:' + server.port + '/', { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.ACS?.openWorkspace);
    await page.locator('#lgGo').click();
    await page.evaluate(() => {
      // مصدر النموذج فقط بديل؛ مسار النقر واللوحات والأنماط هي المشحونة.
      document.getElementById('acsPanelShow').classList.remove('acs-hidden');
      document.getElementById('left').classList.remove('acs-hidden');
      document.getElementById('left').classList.add('open');
    });
    rows.push(await page.evaluate(() => {
      const button = document.getElementById('acsOpenPbr');
      button.focus(); button.click();
      return { check: 'no-model leaves focus on opener and gives immediate reason',
        ok: document.activeElement === button
          && !document.getElementById('pqPanel').classList.contains('on')
          && /نموذج/.test(document.getElementById('acsPanelsState').textContent) };
    }));
    await page.evaluate(() => {
      window.__ACS_AUDIT_MODEL = {
        site: { w: 30, d: 24 }, levels: [{ index: 0, template: 'typical' }],
        floors: { typical: { rooms: [
          { id: 'hall', name: 'صالة', rect: [0, 0, 12, 9] },
          { id: 'room1', name: 'غرفة', rect: [12, 0, 6, 5] },
        ] } }, meta: { requirements: [], excluded: [] },
      };
    });
    for (const [ns, buttonId, panelId, closeId] of PANELS) {
      const before = await page.evaluate(([ns, buttonId, panelId]) => {
        const b = document.getElementById(buttonId); b.focus(); b.click();
        const p = document.getElementById(panelId);
        return { ns, sameTickOpen: p.classList.contains('on'),
          sameTickFocus: p.contains(document.activeElement),
          status: document.getElementById('acsPanelsState').textContent };
      }, [ns, buttonId, panelId]);
      rows.push({ check: ns + ' first-open timing stays eager-or-lazy',
        ok: ns === 'pbr' ? before.sameTickOpen : !before.sameTickOpen && /تحميل/.test(before.status) });
      await page.waitForFunction(id => document.getElementById(id).classList.contains('on'), panelId);
      rows.push(await page.evaluate(([ns, panelId]) => ({
        check: ns + ' focus enters opened panel',
        ok: document.getElementById(panelId).contains(document.activeElement),
        actual: document.activeElement.id,
      }), [ns, panelId]));
      if (ns === 'archdetail') rows.push(...await page.evaluate(() => {
        const panel = document.getElementById('adPanel');
        const fields = ['adDetail', 'adFacade', 'adContext', 'adStaging', 'adCamera'];
        const actions = ['adClose', 'adApplyBtn', 'adCompareE', 'adCompareP', 'adCompareA'];
        const namedField = id => Array.from(document.getElementById(id).labels || [])
          .some(label => label.textContent.trim().length > 1);
        const namedAction = id => (document.getElementById(id).getAttribute('aria-label') || '').trim().length > 2;
        const namedDialog = () => panel.getAttribute('role') === 'dialog'
          && panel.getAttribute('aria-labelledby') === 'adTitle'
          && document.getElementById('adTitle').textContent.trim().length > 1;
        const checks = [
          { check: 'architectural panel exposes its dialog title',
            ok: namedDialog() },
          { check: 'architectural choices have associated labels',
            ok: fields.every(namedField), actual: fields.filter(id => !namedField(id)) },
          { check: 'architectural icon actions have meaningful names',
            ok: actions.every(namedAction), actual: actions.filter(id => !namedAction(id)) },
        ];
        const label = document.getElementById('adDetailLbl');
        const priorFor = label.getAttribute('for'); label.removeAttribute('for');
        checks.push({ check: 'label guard rejects removed association', ok: !namedField('adDetail') });
        if (priorFor !== null) label.setAttribute('for', priorFor);
        const button = document.getElementById('adClose');
        const priorName = button.getAttribute('aria-label'); button.removeAttribute('aria-label');
        checks.push({ check: 'name guard rejects removed action name', ok: !namedAction('adClose') });
        if (priorName !== null) button.setAttribute('aria-label', priorName);
        const priorRole = panel.getAttribute('role'); panel.removeAttribute('role');
        checks.push({ check: 'dialog guard rejects removed role', ok: !namedDialog() });
        if (priorRole !== null) panel.setAttribute('role', priorRole);
        return checks;
      }));
      await page.keyboard.press('Escape');
      rows.push(await page.evaluate(([ns, buttonId, panelId]) => ({
        check: ns + ' Escape closes and restores opener',
        ok: !document.getElementById(panelId).classList.contains('on')
          && document.activeElement.id === buttonId,
        actual: document.activeElement.id,
      }), [ns, buttonId, panelId]));
      rows.push(await page.evaluate(([ns, buttonId, panelId]) => {
        const b = document.getElementById(buttonId); b.focus(); b.click();
        const p = document.getElementById(panelId);
        return { check: ns + ' cached open and focus are synchronous',
          ok: p.classList.contains('on') && p.contains(document.activeElement) };
      }, [ns, buttonId, panelId]));
      if (closeId) {
        await page.locator('#' + closeId).click();
        rows.push(await page.evaluate(([ns, buttonId]) => ({
          check: ns + ' close control returns focus', ok: document.activeElement.id === buttonId,
          actual: document.activeElement.id,
        }), [ns, buttonId]));
      } else await page.keyboard.press('Escape');
    }
    // لوحة غير مشروطة: إن غادر المستخدم إلى تحكّم آخر، الإغلاق لا يخطف التركيز.
    rows.push(await page.evaluate(async () => {
      document.getElementById('acsOpenPbr').focus();
      document.getElementById('acsOpenPbr').click();
      const other = document.getElementById('acsOpenBim'); other.focus();
      window.ACS.pbr.panel.close();
      await Promise.resolve();
      return { check: 'closing a panel preserves deliberately moved focus',
        ok: document.activeElement === other };
    }));
    rows.push({ check: 'no page errors', ok: errors.length === 0, actual: errors });
    const violations = await page.evaluate(() => window.__cspViolations || []);
    rows.push({ check: 'production CSP stays intact', ok: violations.length === 0, actual: violations });
    return rows;
  } finally { await page.close(); server.close(); }
}

(async () => {
  if (!PW.executable()) {
    console.error('AUDIT FRONTEND PANELS: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (Chromium unavailable)');
    process.exitCode = 2;
    return;
  }
  const browser = await PW.launch();
  try {
    const rows = await measure(browser, ENTRY);
    rows.forEach(row => console.log((row.ok ? 'PASS ' : 'FAIL ') + row.check
      + (row.actual ? ' ' + JSON.stringify(row.actual) : '')));
    assert.equal(rows.filter(row => !row.ok).length, 0, 'panel focus contract must hold');
    if (process.argv.includes('--mutations')) {
      for (const [label, original] of [
        ['entry-focus', 'target.focus({ preventScroll: true });'],
        ['return-focus', 'state.opener.focus({ preventScroll: true });'],
      ]) {
        assert.equal(ENTRY.split(original).length - 1, 1, 'mutation anchor is unique');
        const mutant = await measure(browser, ENTRY.replace(original, '/* mutation: focus omitted */'));
        const rejected = mutant.filter(row => !row.ok);
        assert.ok(rejected.length > 0, label + ' mutant must be rejected');
        assert.ok(mutant.filter(row => /no page errors|CSP|no-model|deliberately moved/.test(row.check))
          .every(row => row.ok), 'mutation must fail the focus assertion, not its environment');
        console.log('MUTATION REJECTED ' + label + ': ' + rejected.map(row => row.check).join('; '));
      }
    }
    console.log('AUDIT FRONTEND PANELS: ' + rows.length + ' passed, 0 failed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
