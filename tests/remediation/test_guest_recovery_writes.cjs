'use strict';
// Run the shipped guest entry with a delayed storage result, preserving the
// real order of its button handlers and recovery continuation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('public/app/ui/guest-workspace.js', 'utf8');

async function guest(recovery, interact, scope = 'acs_guest_project_v1') {
  const nodes = new Map(), events = new Map();
  let boot, release;
  function element(id) {
    if (nodes.has(id)) return nodes.get(id);
    const listeners = {};
    const node = {
      dataset: {}, classList: { add() {}, remove() {} },
      setAttribute() {}, closest() { return null; }, before() {}, focus() {},
      addEventListener(name, fn) { listeners[name] = fn; },
      click() { listeners.click?.(); },
    };
    nodes.set(id, node);
    return node;
  }
  const document = {
    readyState: 'loading',
    body: { classList: { add() {} }, append(banner) { nodes.set(banner.id, banner); } },
    createElement: () => element('banner'),
    getElementById: id => id === 'acsGuestBanner' ? nodes.get(id) : element(id),
    querySelector: () => null,
    addEventListener(name, fn) { if (name === 'DOMContentLoaded') boot = fn; },
    removeEventListener() {},
  };
  const ACS = {
    guest: true, showExample() {}, setModel() {},
    persistence: { recover: () => new Promise(resolve => { release = resolve; }) },
  };
  vm.runInNewContext(source, { document, window: { addEventListener: (name, callback) => events.set(name, callback), ACS, ACS_AUTH: { storageScope: () => scope } }, innerWidth: 1440, setTimeout, clearTimeout });
  const ready = boot();
  if (interact) ACS.guestWorkspace.sample('warehouse');
  release(recovery);
  await ready;
  return { ACS, element, emit: (name, detail) => events.get(name)?.({ detail }) };
}

// A committed selection must match the sample that the guest labels as ready.
function verifyWarehouseSelection() {
  const moduleText = fs.readFileSync('public/app/ui/workspace-ui-wiring.js', 'utf8');
  const wiring = require('../lib/app_source.js').stripModuleSyntax(moduleText, 'wiring');
  const statements = require('../lib/js_segment.js').topLevelStatements(wiring);
  const start = "document.getElementById('loadWarehouse').onclick=";
  const handler = statements.map(s => wiring.slice(s.start, s.end)).find(s => s.trimStart().startsWith(start));
  assert.ok(handler, 'shipped warehouse button handler exists');
  const button = {}, tasks = [], residential = { type: 'residential' };
  let visible = residential;
  const context = {
    document: { getElementById: () => button }, statusEl: {},
    setTimeout: fn => tasks.push(fn), warehouseModel: () => ({ type: 'warehouse' }),
    localGeneratedModel: model => model, setModel: model => { visible = model; },
  };
  vm.runInNewContext(handler, context);
  button.onclick();
  assert.equal(visible.type, 'warehouse', 'presentation and the ready label must select the new warehouse before returning');
  visible = residential; // A subsequent sample/import is authoritative.
  tasks.forEach(fn => fn());
  assert.equal(visible, residential, 'an older deferred selection must not replace a newer one');
}

(async () => {
  verifyWarehouseSelection();
  for (const interact of [true, false]) {
    const { ACS, element } = await guest({ ok: false, code: 'STORAGE_UNAVAILABLE' }, interact);
    assert.equal(ACS.guestAutosaveReady, false, 'a failed read keeps writes disabled even after an interaction');
    ACS.guestWorkspace.sample('residential');
    element('genText').click();
    assert.equal(ACS.guestAutosaveReady, false, 'a subsequent edit cannot rearm autosave');
  }
  // A click or rejected build must not relabel the existing sample as generated.
  const studio = await guest({ ok: false, code: 'NO_RECORDS' }, false, 'acs_guest_apartment_20x25_v1');
  assert.equal(studio.element('guestSignin').href, '/?signin=1&example=apartment-20x25');
  assert.equal(studio.element('guestStorageNote').hidden, false);
  studio.element('genText').click();
  studio.emit('acs:local-generation', { ok: false, message: 'لم يكتمل الوصف' });
  assert.equal(studio.element('acsGuestStatus').textContent, 'عمارة تجريبية');
  assert.equal(studio.element('guestFeedback').textContent, 'لم يكتمل الوصف');
  studio.emit('acs:local-generation', { ok: true });
  assert.equal(studio.element('acsGuestStatus').textContent, 'تصميم محلي أولي');
  assert.equal(studio.element('guestFeedback').textContent, '');
  for (const result of [{ ok: false, code: 'NO_RECORDS' }, { ok: true, project: { model: { site: {} } } }]) {
    const { ACS } = await guest(result, true);
    assert.equal(ACS.guestAutosaveReady, true, 'successful storage resolution admits local saves');
  }
  console.log('PASS guest recovery gates writes after failed reads, before and after editing');
})().catch(error => { console.error(error); process.exitCode = 1; });
