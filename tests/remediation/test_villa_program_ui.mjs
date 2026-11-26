// Step 01 villa program: the fields (Arabic, Arabic-Indic digits, defaults),
// the three villa option cards and the confirmed requirement rows they send,
// checked against the server (acs_plan_projection, acs_plan_review._program,
// acs_villa_program) on a minimal DOM. No browser or network.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {villaProgram,villaSummary,villaRows,villaOptions,readVilla,VILLA_ISSUE_NAMES,VILLA_SCOPE_NAMES,VILLA_SOURCE} from '../../public/app/core/residential-program.mjs';
import {briefSays,villaBrief} from '../../public/app/core/plot-rules.mjs';
import {requirementLabel} from '../../public/app/core/brief-program.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let passed = 0;
const check = async (name, fn) => { await fn(); passed++; console.log('PASS', name); };
const python = (code, input) => {
  const out = spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,' + JSON.stringify(ROOT) + ');' + code],
    {input: JSON.stringify(input), encoding: 'utf8', cwd: ROOT});
  assert.equal(out.status, 0, out.stderr);
  return JSON.parse(out.stdout);
};
const STARTER = 'أبغى فيلا عائلية في جدة. عرض الأرض ١٨ متر وعمق الأرض ٢٨ متر. عدد الأدوار ٢ شاملة الأرضي.\n'
  + 'أبغى مجلس الضيوف قريب من المدخل، وصالة الأسرة تطل على الحديقة. خلّ غرف النوم في الدور العلوي والمطبخ قريب من غرفة الطعام.'
  + '\n\nنوع المشروع: سكني / عمارة / فيلا';
const cp = s => Array.from(s).length;

await check('villa program defaults: 4 bedrooms, master suite, bedrooms + 1 bathrooms, no service rooms', () => {
  assert.deepEqual(villaProgram({}), {bedrooms: 4, master: true, bathrooms: 5, autoBathrooms: true, maid: false, driver: false});
  assert.deepEqual(villaProgram({bedrooms: '٥', bathrooms: '', maid: 'yes'}),
    {bedrooms: 5, master: true, bathrooms: 7, autoBathrooms: true, maid: true, driver: false}, 'one WC per service room');
  assert.equal(villaProgram({bedrooms: '۳', bathrooms: '٤'}).bathrooms, 4, 'a typed count wins');
  assert.throws(() => villaProgram({bedrooms: '٢٫٥'}), /غرف النوم: أدخل عددًا صحيحًا من 1 إلى 10/);
  assert.throws(() => villaProgram({bedrooms: '11'}), /من 1 إلى 10/);
  assert.throws(() => villaProgram({bathrooms: '1'}), /أقل من الحد الأدنى.*حمام خاص لغرفة النوم الرئيسية/);
  assert.equal(villaProgram({master: 'no', bathrooms: '1'}).bathrooms, 1);
  assert.match(villaSummary(villaProgram({})), /^4 غرف نوم، منها غرفة نوم رئيسية بحمام خاص؛ 5 حمامات ودورات مياه منها دورة مياه للضيوف/);
  assert.deepEqual(readVilla('فيلا فيها ٥ غرف نوم وغرفة خادمة وغرفة سائق'), {bedrooms: 5, maid: 'yes', driver: 'yes'});
});

await check('rows the server accepts: room_count per role and ensuite_bedroom_count', () => {
  const rows = villaRows(villaProgram({maid: 'yes', driver: 'yes'}));
  assert.deepEqual(rows.map(r => [r.metric, r.role || null, r.expected]), [
    ['room_count', 'bedroom', 4], ['ensuite_bedroom_count', null, 1], ['room_count', 'bathroom', 7],
    ['room_count', 'maid_room', 1], ['room_count', 'driver_room', 1]]);
  const metrics = python('import acs_requirement_metrics as M;print(json.dumps(sorted(M.METRICS)))', null);
  for (const r of rows) assert.ok(metrics.includes(r.metric), r.metric);
  assert.equal(villaRows(villaProgram({master: 'no'})).some(r => r.metric === 'ensuite_bedroom_count'), false);
  assert.equal(requirementLabel({metric: 'room_count', role: 'maid_room'}), 'غرف الخادمة');
  assert.equal(requirementLabel({metric: 'ensuite_bedroom_count'}), 'غرف نوم بحمام خاص');
});

await check('three villa cards that differ in program and estimated area', () => {
  const cards = villaOptions(villaProgram({}), {levels: 2, buildable: 275});
  assert.deepEqual(cards.map(c => c.title), ['بيت عائلي مدمج', 'فصل الضيوف عن العائلة', 'جناح رئيسي واسع']);
  assert.equal(new Set(cards.map(c => c.estimatedArea)).size, 3);
  assert.ok(cards.every(c => c.available === 550 && c.feasible));
  assert.ok(cards[0].estimatedArea < cards[2].estimatedArea && cards[2].estimatedArea < cards[1].estimatedArea);
  assert.deepEqual(cards.map(c => c.recommended), [true, false, false]);
  assert.deepEqual(villaOptions(villaProgram({}), {levels: 2, buildable: 275, guests: 'separate'}).map(c => c.recommended), [false, true, false]);
  assert.ok(villaOptions(villaProgram({bedrooms: '10'}), {levels: 1, buildable: 120}).every(c => !c.feasible));
  assert.ok(villaOptions(villaProgram({}), {levels: 2}).every(c => c.available === null && c.feasible), 'unknown plot: no refusal');
});

await check('a villa brief is read as the server reads it (_brief_says)', () => {
  const texts = ['أبغى فيلا عائلية في جدة.', 'فيلتي في الرياض', 'بيت دورين', 'منزل العائلة', 'my house', 'Villa',
    'فلل للبيع', 'فيلتين متلاصقتين', 'بيت الدرج على السطح', 'عمارة سكنية', 'فيلا فيها شقة للإيجار', 'شقتين في كل دور',
    'وحدات سكنية', 'مبيت العمال', 'مبنى من دورين', STARTER, 'عمارة\n\nنوع المشروع: سكني / عمارة / فيلا', 'للبيت حديقة',
    'apartments for rent', 'قصر', 'البيتزا'];
  const server = python('from acs_residential_access import _brief_says\nprint(json.dumps([_brief_says(t) for t in json.load(sys.stdin)]))', texts);
  assert.deepEqual(texts.map(briefSays), server);
  assert.equal(villaBrief(STARTER, null), true);
  assert.equal(villaBrief(STARTER, 2), false);
});

await check('every villa finding code and the scope have Arabic labels', () => {
  const codes = python(`
import re
print(json.dumps(sorted(set(re.findall(r"'(VILLA_[A-Z_]+)'", open('acs_villa_program.py',encoding='utf-8').read())))))`, null);
  assert.ok(codes.length >= 8, codes);
  for (const code of codes) assert.ok(VILLA_ISSUE_NAMES[code], code);
  assert.ok(VILLA_SCOPE_NAMES.dwelling_program);
});

// ── minimal DOM for the step-01 module ──────────────────────────────────────
const registry = new Map();
class Node {
  constructor(tag, attrs = {}) {
    Object.assign(this, {tagName: tag.toUpperCase(), listeners: {}, hidden: false, textContent: '', placeholder: '', value: '',
      checked: false, disabled: false, dataset: {}, children: [], options: []}, attrs);
  }
  addEventListener(kind, fn) { (this.listeners[kind] ||= []).push(fn); }
  fire(kind) { for (const node of [this, this.parent].filter(Boolean)) for (const fn of node.listeners[kind] || []) fn({target: this}); }
  after(node) { node.placed = true; }
  closest(sel) { return sel === 'article' ? this.card : this; }
  append(...nodes) { for (const n of nodes) { this.children.push(n); n.parent ||= this; } }
  insertBefore(node) { this.children.push(node); }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  remove() { if (this.card) this.card.children = this.card.children.filter(n => n !== this); }
  querySelector(sel) {
    if (sel === '[data-residential-detail]') return this.children.find(n => 'residentialDetail' in n.dataset) || null;
    return this.children.find(n => n.tagName === sel.toUpperCase()) || null;
  }
  get selectedOptions() { return [this.options.find(o => o.value === this.value) || {textContent: ''}]; }
  set innerHTML(html) {
    for (const m of html.matchAll(/<(\w+)\b([^>]*)>/g)) {
      const id = /id="([^"]+)"/.exec(m[2])?.[1];
      if (!id) continue;
      const node = new Node(m[1], {id, type: /type="([^"]+)"/.exec(m[2])?.[1] || m[1], parent: this, hidden: /\bhidden\b/.test(m[2]),
        placeholder: /placeholder="([^"]*)"/.exec(m[2])?.[1] || ''});
      if (m[1] === 'select') {
        const body = html.slice(m.index, html.indexOf('</select>', m.index));
        node.options = [...body.matchAll(/<option value="([^"]*)">([^<]*)</g)].map(o => ({value: o[1], textContent: o[2]}));
        node.value = node.options[0]?.value ?? '';
      }
      registry.set(id, node);
    }
  }
}
const fields = {cwType: 'residential', cwBrief: STARTER, cwWidth: '١٨', cwDepth: '٢٨', cwLevels: '2', cwBldWidth: '', cwBldDepth: ''};
for (const [id, value] of Object.entries(fields)) registry.set(id, new Node(id === 'cwBrief' ? 'textarea' : 'input', {id, value}));
registry.set('cwConfirmed', new Node('input', {id: 'cwConfirmed', type: 'checkbox', checked: true}));
registry.set('cwReadBrief', new Node('button', {id: 'cwReadBrief'}));
registry.set('cwBuildingFields', new Node('div', {id: 'cwBuildingFields'}));
const panel = new Node('section');
const cards = ['A', 'B', 'C'].map(id => {
  const card = new Node('article'), button = new Node('button', {textContent: 'توليد البديل ' + id, card});
  button.dataset.option = id;
  card.append(new Node('h2', {textContent: 'عنوان ' + id}), new Node('p', {textContent: 'وصف ' + id}), button);
  return {card, button};
});
const store = new Map();
globalThis.localStorage = {getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v))};
globalThis.document = {createElement: tag => { const n = new Node(tag); return n; }};
const root = {
  querySelector(sel) {
    if (sel.startsWith('#')) return registry.get(sel.slice(1)) || null;
    if (sel === '[data-step-panel="2"]') return panel;
    const option = /\[data-option="(\w)"\]/.exec(sel);
    return option ? cards.find(c => c.button.dataset.option === option[1]).button : null;
  },
  querySelectorAll: sel => sel === '[data-option]' ? cards.map(c => c.button) : [],
};
// Cards get their detail paragraph through el(...,card) (append) and then insertBefore.
for (const {card} of cards) card.children.forEach(child => { child.card = card; });
const $ = id => registry.get(id);
const {createResidentialOptions} = await import('../../public/app/ui/residential-options.mjs');
const issueNames = {OTHER: 'x'}, scopeNames = {};
const options = createResidentialOptions(root, {storageKey: () => 'draft:residential', api: async () => ({message: '', sources: []}),
  onError: e => { throw e; }, buildable: () => 275, issueNames, scopeNames});
const siteRows = () => [['site_width_m', 18, 'عرض الأرض ١٨ متر'], ['site_depth_m', 28, 'عمق الأرض ٢٨ متر'], ['level_count', 2, 'عدد الأدوار ٢']]
  .map(([metric, expected, evidence], i) => {
    const start = cp(STARTER.slice(0, STARTER.indexOf(evidence)));
    return {id: 'brief-' + i, metric, expected, source: 'requested', source_id: 'brief:text', evidence,
      source_span: {start, end: start + cp(evidence)}, confirmed: true};
  });

await check('a villa brief shows the villa program fields instead of the apartment fields', () => {
  assert.equal(issueNames.VILLA_AGGREGATE_ROOM, 'فراغ واحد يجمع عدة غرف');
  assert.equal(issueNames.OTHER, 'x');
  assert.equal(scopeNames.dwelling_program, 'برنامج الفيلا وصلاحية السكن');
  $('cwBrief').fire('input');
  assert.equal($('cwResidentialTitle').textContent, 'برنامج الفيلا');
  assert.equal($('cwVillaFields').hidden, false);
  assert.equal($('cwApartmentFields').hidden, true);
  assert.equal($('cwFlatFields').hidden, true);
  assert.equal($('cwVillaBedrooms').placeholder, 'افتراضي 4');
  assert.deepEqual([$('cwVillaMaster').value, $('cwVillaMaid').value, $('cwVillaDriver').value], ['yes', 'no', 'no']);
  assert.match($('cwVillaSummary').textContent, /^البرنامج: 4 غرف نوم، منها غرفة نوم رئيسية بحمام خاص؛ 5 حمامات/);
  assert.equal($('cwVillaBathrooms').placeholder, 'تلقائي: 5');
  $('cwVillaBedrooms').value = '٥'; $('cwVillaBedrooms').fire('input');
  assert.match($('cwVillaSummary').textContent, /5 غرف نوم.*6 حمامات/);
  assert.equal($('cwConfirmed').checked, false, 'changing the program needs a new confirmation');
  assert.equal(JSON.parse(store.get('draft:residential')).cwVillaBedrooms, '٥');
  $('cwVillaBathrooms').value = '١'; $('cwVillaBathrooms').fire('input');
  assert.throws(() => options.validate(), /أقل من الحد الأدنى/);
  assert.match($('cwVillaSummary').textContent, /أقل من الحد الأدنى/);
  $('cwVillaBedrooms').value = ''; $('cwVillaBathrooms').value = ''; $('cwVillaBathrooms').fire('input');
  options.validate();
});

let command;
await check('villa cards replace the generic A/B/C text, each with its own estimate', () => {
  const base = {brief: STARTER, requirements: siteRows()};
  options.prepare(base);
  assert.deepEqual(cards.map(c => c.card.querySelector('h2').textContent),
    ['بيت عائلي مدمج · مقترح لك', 'فصل الضيوف عن العائلة', 'جناح رئيسي واسع']);
  const details = cards.map(c => c.card.querySelector('[data-residential-detail]').textContent);
  assert.ok(details.every(t => /تقدير المساحة المبنية ≈ \d+ م² على دورين من نحو 550 م²/.test(t)), details.join('\n'));
  assert.equal(new Set(details).size, 3);
  assert.ok(cards.every(c => !/وصف|عنوان/.test(c.card.querySelector('p').textContent + c.card.querySelector('h2').textContent)));
  assert.equal(cards[1].button.textContent, 'اختيار «فصل الضيوف عن العائلة» والتوليد');
  command = options.program(base, 'B');
  const villaRowsSent = command.requirements.filter(r => r.source_id === VILLA_SOURCE);
  assert.deepEqual(villaRowsSent.map(r => [r.metric, r.role || null, r.expected]),
    [['room_count', 'bedroom', 4], ['ensuite_bedroom_count', null, 1], ['room_count', 'bathroom', 5]]);
  for (const r of command.requirements) assert.equal(Array.from(command.brief).slice(r.source_span.start, r.source_span.end).join(''), r.evidence);
  assert.ok(villaRowsSent.every(r => r.confirmed === true && r.source === 'inferred'));
  assert.match(command.brief, /\nبرنامج الفيلا: 4 غرف نوم/);
  assert.match(command.brief, /\nتصور الفيلا المختار: فصل الضيوف عن العائلة/);
  assert.throws(() => options.program({brief: STARTER + ' ', requirements: siteRows()}, 'B'), /تغيّرت المدخلات/);
});

await check('the server admits the rows and the livable villa fixture meets them', () => {
  const out = python(`
from types import SimpleNamespace
from acs_plan_projection import _requirements
from acs_plan_review import _program, canonical
from acs_villa_program import confirmed_program
import acs_workspace_service as S
c = json.load(sys.stdin)
_requirements(SimpleNamespace(requirements_json=canonical(c['requirements']), brief=c['brief']))
S.generation_command({'action':'generate','job_id':'00000000-0000-4000-8000-000000000001','brief':c['brief'],
    'requirements':c['requirements'],'option':'B','confirmed':True,'max_provider_calls':8,'expected_head':None})
model = json.load(open('tests/remediation/fixtures/villa_program/villa_livable.json'))['model']
print(json.dumps({'program': confirmed_program(c['requirements']), 'issues': _program(model, c['brief'], c['requirements'])}))`, command);
  assert.deepEqual(out.program, {bedroom: 4, bathroom: 5, maid_room: 0, driver_room: 0, ensuite: 1});
  assert.deepEqual(out.issues, []);
});

await check('a confirmed count in the requirements table is used, a different field value is refused', () => {
  const rows = siteRows();
  rows.push({id: 'brief-9', metric: 'room_count', role: 'bedroom', expected: 3, source: 'requested', source_id: 'brief:form',
    evidence: 'غرف النوم (bedroom): 3', source_span: {start: 0, end: 1}, confirmed: true});
  options.prepare({brief: STARTER, requirements: rows});
  assert.match(cards[0].card.querySelector('p').textContent, /^3 غرف نوم/);
  $('cwVillaBedrooms').value = '٤';
  assert.throws(() => options.prepare({brief: STARTER, requirements: rows}), /يختلف عن المتطلب المؤكد \(3\)/);
  $('cwVillaBedrooms').value = '';
});

await check('an apartment brief keeps the apartment fields and cards', () => {
  $('cwBrief').value = 'أبغى عمارة سكنية في الرياض.'; $('cwBrief').fire('input');
  assert.equal($('cwVillaFields').hidden, true);
  assert.equal($('cwApartmentFields').hidden, false);
  assert.equal($('cwResidentialTitle').textContent, 'الشقق واحتياجات الأسرة');
  $('cwUnits').value = '4';
  options.prepare({brief: 'عمارة', requirements: []});
  assert.deepEqual(cards.map(c => c.card.querySelector('h2').textContent.replace(/ · مقترح لك$/, '')), ['صالة أوسع', 'غرف أكثر للأسرة', 'خصوصية الضيوف']);
  $('cwUnits').value = '';
  options.prepare({brief: 'عمارة', requirements: []});
  assert.deepEqual(cards.map(c => c.card.querySelector('h2').textContent), ['عنوان A', 'عنوان B', 'عنوان C'], 'generic text restored');
});

console.log('VILLA PROGRAM UI: ' + passed + ' passed, 0 failed');
