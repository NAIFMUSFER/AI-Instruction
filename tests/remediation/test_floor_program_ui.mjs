// Step 02 option cards for a confirmed floor program (core/floor-program.mjs,
// ui/residential-options.mjs): the cards describe three layouts of the same
// rooms and send per-floor rows equal to the server's; they no longer add the
// uniform per-flat rows that contradicted an uneven program (option B used to
// add «room_count majlis 0»). Checked against the server on a minimal DOM.
// No browser or network.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {programRows,programConflicts,programOptions,floorText,floorName,ROLE_LABEL,ENSUITE_LABEL,PROGRAM_ISSUE_NAMES,PROGRAM_SCOPE_NAMES} from '../../public/app/core/floor-program.mjs';
import {requirementKey,requirementLabel} from '../../public/app/core/brief-program.mjs';
import {programFields} from '../../public/app/core/brief-reader.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let passed = 0;
const check = async (name, fn) => { await fn(); passed++; console.log('PASS', name); };
const python = (code, input) => {
  const out = spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,' + JSON.stringify(ROOT) + ');' + code],
    {input: JSON.stringify(input), encoding: 'utf8', cwd: ROOT});
  assert.equal(out.status, 0, out.stderr);
  return JSON.parse(out.stdout);
};
const FIX = path.join(ROOT, 'tests/remediation/fixtures/brief_reader');
const BRIEF = readFileSync(path.join(FIX, 'owner_brief.txt'), 'utf8');
const validated = python('import acs_brief_reader as B\nprint(json.dumps(B.validate_program(json.load(sys.stdin)), ensure_ascii=False))',
  JSON.parse(readFileSync(path.join(FIX, 'owner_program.json'), 'utf8')));

await check('the per-floor rows equal the server rows, with Arabic labels and floor-aware keys', () => {
  const rows = programRows(validated);
  const server = python('import acs_floor_program as F\nprint(json.dumps(F.requirement_rows(json.load(sys.stdin)), ensure_ascii=False))', validated);
  assert.deepEqual(rows, server);
  assert.equal(rows.length, 25);
  const first = rows.find(r => r.id === 'program-l1-bedroom');
  assert.deepEqual([first.metric, first.level, first.expected, first.evidence], ['room_count_by_level', 1, 4, 'غرف النوم في الدور الأول: 4']);
  assert.equal(requirementLabel(first), 'غرف النوم في الدور الأول');
  assert.equal(requirementLabel({metric: 'ensuite_bedroom_count_by_level', level: 2}), ENSUITE_LABEL + ' في ' + floorName(2));
  for (const [role, label] of Object.entries(ROLE_LABEL))
    for (const level of [0, 3, 12]) assert.equal(requirementLabel({metric: 'room_count_by_level', role, level}), label + ' في ' + floorName(level));
  assert.notEqual(requirementKey(first), requirementKey({...first, level: 2}), 'one row per floor');
  assert.equal(requirementKey({metric: 'room_count', role: 'bedroom'}), JSON.stringify(['room_count', 'bedroom']), 'old keys unchanged');
});

await check('contradictions read the same as on the server', () => {
  const rows = [{metric: 'room_count', role: 'majlis', expected: 0}, {metric: 'room_count_per_unit', role: 'bedroom', expected: 3},
    {metric: 'room_count_by_level', level: 1, role: 'bedroom', expected: 3}, {metric: 'unit_count', expected: 3}];
  const server = python('import acs_floor_program as F\nc=json.load(sys.stdin)\nprint(json.dumps(F.contradictions(c["p"], c["r"]), ensure_ascii=False))',
    {p: validated, r: rows});
  assert.deepEqual(programConflicts(validated, rows), server);
  assert.equal(server.length, 3);
  assert.deepEqual(programConflicts(validated, programRows(validated)), []);
});

await check('the card fills one flat per floor; its totals agree with the per-floor rows', () => {
  const f = programFields(validated);
  assert.deepEqual(f.units, {units: 1, scope: 'per_level'});
  assert.equal(f.bedrooms, null);
  assert.deepEqual(f.rows, [{metric: 'room_count', role: 'bedroom', expected: 9}, {metric: 'room_count', role: 'bathroom', expected: 9}]);
  assert.deepEqual(programConflicts(validated, f.rows), [], 'what the card fills never contradicts the program');
  assert.match(f.notes.join(' '), /يُرسم كل دور ببرنامجه/);
});

await check('three layout cards for the same rooms, one line per floor', () => {
  const cards = programOptions(validated, {buildable: 208});
  assert.deepEqual(cards.map(c => c.title), ['مخطط مدمج حول النواة', 'وضوح الحركة', 'فصل الضيوف عن الأسرة']);
  assert.ok(cards.every(c => c.feasible && c.floorProgram && c.available === 208));
  assert.deepEqual(cards[0].floors, ['الدور الأرضي: 3 غرف نوم، 4 حمامات، مجلس', 'الدور الأول: 4 غرف نوم، 3 حمامات، مجلس',
    'الدور الثاني: غرفتا نوم، حمامان، مكتب، تراس']);
  assert.deepEqual(cards.map(c => c.recommended), [false, false, true], 'a majlis: guest separation first');
  const tight = structuredClone(validated); tight.site.footprint = {width_m: 8, depth_m: 10, position: 'W'};
  assert.ok(programOptions(tight).every(c => !c.feasible));
  assert.equal(floorText({use: 'parking', units: []}, 0), 'الدور الأرضي: مواقف');
});

await check('every per-floor finding code and the scope have Arabic labels', () => {
  const codes = python(`
import re
print(json.dumps(sorted(set(re.findall(r"'(PROGRAM_[A-Z_]+)'", open('acs_floor_program.py',encoding='utf-8').read())))))`, null);
  assert.ok(codes.length >= 7, codes);
  for (const code of codes) assert.ok(PROGRAM_ISSUE_NAMES[code], code);
  assert.ok(PROGRAM_SCOPE_NAMES.brief_program);
});

// ── minimal DOM for the step-01/02 module ───────────────────────────────────
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
  remove() { const holder = this.card || this.parent; if (holder) holder.children = holder.children.filter(n => n !== this); }
  querySelector(sel) {
    if (sel === '[data-residential-detail]') return this.children.find(n => 'residentialDetail' in n.dataset) || null;
    return this.children.find(n => n.tagName === sel.toUpperCase()) || null;
  }
  get selectedOptions() { return [this.options.find(o => o.value === this.value) || {textContent: ''}]; }
  set innerHTML(html) {
    for (const m of html.matchAll(/<(\w+)\b([^>]*)>/g)) {
      const id = /id="([^"]+)"/.exec(m[2])?.[1];
      if (!id) continue;
      const node = new Node(m[1], {id, type: /type="([^"]+)"/.exec(m[2])?.[1] || m[1], parent: this, hidden: /\bhidden\b/.test(m[2])});
      if (m[1] === 'select') {
        const body = html.slice(m.index, html.indexOf('</select>', m.index));
        node.options = [...body.matchAll(/<option value="([^"]*)">([^<]*)</g)].map(o => ({value: o[1], textContent: o[2]}));
        node.value = node.options[0]?.value ?? '';
      }
      registry.set(id, node);
    }
  }
}
const fields = {cwType: 'residential', cwBrief: BRIEF, cwWidth: '20', cwDepth: '25', cwLevels: '3', cwBldWidth: '13', cwBldDepth: '16'};
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
globalThis.document = {createElement: tag => new Node(tag)};
const root = {
  querySelector(sel) {
    if (sel.startsWith('#')) return registry.get(sel.slice(1)) || null;
    if (sel === '[data-step-panel="2"]') return panel;
    const option = /\[data-option="(\w)"\]/.exec(sel);
    return option ? cards.find(c => c.button.dataset.option === option[1]).button : null;
  },
  querySelectorAll: sel => sel === '[data-option]' ? cards.map(c => c.button) : [],
};
for (const {card} of cards) card.children.forEach(child => { child.card = card; });
const $ = id => registry.get(id);
let card = null;   // what the smart-reading card reports (ui/brief-reader.mjs current())
const {createResidentialOptions} = await import('../../public/app/ui/residential-options.mjs');
const issueNames = {}, scopeNames = {};
const options = createResidentialOptions(root, {storageKey: () => 'draft:residential', api: async () => ({message: '', sources: []}),
  onError: e => { throw e; }, buildable: () => 208, issueNames, scopeNames, confirmedProgram: () => card});
const siteRows = () => [['site_width_m', 20], ['site_depth_m', 25], ['level_count', 3], ['building_width_m', 13], ['building_depth_m', 16]]
  .map(([metric, expected], i) => ({id: 'brief-' + i, metric, expected, source: 'inferred', source_id: 'brief:form',
    evidence: metric + ': ' + expected, confirmed: true}));
const filled = () => [...siteRows(), ...programFields(validated).rows.map((r, i) => ({...r, id: 'card-' + i, source: 'inferred',
  source_id: 'brief:form', evidence: r.role + ': ' + r.expected, confirmed: true}))];

await check('without a confirmed program the per-flat cards and their rows are unchanged', () => {
  assert.equal(issueNames.PROGRAM_ROOM_SIZE_OFF, 'مقاس غرفة بعيد عن المقاس المطلوب');
  assert.equal(scopeNames.brief_program, 'برنامج كل دور والمقاسات المستهدفة');
  $('cwUnits').value = '1'; $('cwUnitsScope').value = 'per_level';
  options.prepare({brief: BRIEF, requirements: siteRows()});
  assert.deepEqual(cards.map(c => c.card.querySelector('h2').textContent.replace(/ · مقترح لك$/, '')), ['صالة أوسع', 'غرف أكثر للأسرة', 'خصوصية الضيوف']);
  const old = options.program({brief: BRIEF, requirements: siteRows()}, 'B');
  assert.ok(old.requirements.some(r => r.metric === 'room_count' && r.role === 'majlis' && r.expected === 0),
    'the per-flat card B still adds «room_count majlis 0» for a plain apartment brief');
  card = {program: structuredClone(validated), confirmed: false, source: 'ai'};
  options.prepare({brief: BRIEF, requirements: siteRows()});
  assert.equal(cards[0].card.querySelector('h2').textContent.replace(/ · مقترح لك$/, ''), 'صالة أوسع', 'an unconfirmed card changes nothing');
});

let command;
await check('a confirmed program: layout cards, no contradicting rows, the same per-floor rows on every card', () => {
  card = {program: structuredClone(validated), confirmed: true, source: 'ai'};
  const base = {brief: BRIEF, requirements: filled()};
  options.prepare(base);
  assert.deepEqual(cards.map(c => c.card.querySelector('h2').textContent),
    ['مخطط مدمج حول النواة', 'وضوح الحركة', 'فصل الضيوف عن الأسرة · مقترح لك']);
  for (const c of cards) {
    assert.match(c.card.querySelector('p').textContent, /^الغرف نفسها من برنامجك المؤكد، بتوزيع مختلف/);
    assert.match(c.card.querySelector('[data-residential-detail]').textContent,
      /^الدور الأرضي: 3 غرف نوم، 4 حمامات، مجلس؛ الدور الأول: 4 غرف نوم، 3 حمامات، مجلس؛ الدور الثاني: غرفتا نوم، حمامان، مكتب، تراس\. تُفحص أعداد غرف كل دور ومقاساتها المستهدفة بعد التوليد\.$/);
    assert.equal(c.button.disabled, false);
  }
  const sent = ['A', 'B', 'C'].map(id => options.program(base, id));
  const added = sent.map(s => s.requirements.filter(r => !base.requirements.some(b => b.id === r.id)));
  assert.deepEqual(added[0], added[1]); assert.deepEqual(added[1], added[2]);
  for (const s of sent) {
    assert.equal(s.requirements.filter(r => r.metric === 'room_count_per_unit').length, 0);
    assert.equal(s.requirements.filter(r => r.metric === 'unit_count_per_level').length, 0);
    assert.equal(s.requirements.filter(r => r.metric === 'room_count' && r.role === 'majlis').length, 0, 'no «room_count majlis 0»');
    assert.deepEqual(programConflicts(validated, s.requirements), []);
  }
  assert.deepEqual(added[0].map(r => r.id), ['program-unit_count', ...programRows(validated).map(r => r.id)]);
  assert.match(sent[1].brief, /\nتصور التوزيع المختار: وضوح الحركة — /);
  assert.doesNotMatch(sent[1].brief, /الخيار المختار/, 'no per-flat option line (acs_plot_rules.unit_area_estimate)');
  command = sent[2];
  assert.throws(() => options.program({brief: BRIEF + ' ', requirements: filled()}, 'A'), /تغيّرت المدخلات/);
});

await check('a requirement that contradicts the program is refused in Arabic before any paid call', () => {
  card = {program: structuredClone(validated), confirmed: true, source: 'ai'};
  const rows = [...filled(), {id: 'typed', metric: 'room_count_per_unit', role: 'bedroom', expected: 3, source: 'requested',
    evidence: '3', confirmed: true}];
  options.prepare({brief: BRIEF, requirements: rows});
  for (const c of cards) {
    assert.equal(c.button.disabled, true);
    assert.match(c.card.querySelector('[data-residential-detail]').textContent, /متطلب مؤكد يخالف برنامج الأدوار: غرف النوم «في كل شقة» = 3/);
  }
  assert.throws(() => options.program({brief: BRIEF, requirements: rows}, 'A'), /عدّل البرنامج/, 'a disabled card starts nothing');
});

await check('the server admits the command and plans each floor from it', () => {
  const out = python(`
import acs_workspace_service as S, acs_floor_program as F, acs_plot_rules as P
c = json.load(sys.stdin)
cmd = S.generation_command({'action':'generate','job_id':'00000000-0000-4000-8000-000000000001','brief':c['brief'],
    'requirements':c['requirements'],'option':'C','confirmed':True,'max_provider_calls':12,'expected_head':None,
    'plot':{'streets':['N'],'parking':{'placement':'front_setback'},'landing_entries':True},'program':c['program']})
rules = S.plot_rules(cmd)
m = F.manifest(cmd['program'], cmd['brief'], cmd['requirements'], rules)
print(json.dumps({'templates':[l['template'] for l in m['envelope']['levels']], 'stall':rules['parking']['stall_m'],
                  'footprint':rules['building_footprint']}))`,
    {brief: command.brief, requirements: command.requirements, program: (({checks, cannot_do, ...p}) => p)(validated)});
  assert.deepEqual(out, {templates: ['level_0', 'level_1', 'level_2'], stall: [2.7, 5.2], footprint: [1.5, 5.5, 13, 16]});
});

console.log('FLOOR PROGRAM UI: ' + passed + ' passed, 0 failed');
