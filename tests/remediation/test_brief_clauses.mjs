// The free reader on a comma-joined owner sentence (live QA): a per-floor clause
// holds back only itself, so the plot size and the floor count beside it are read;
// «في كل دور شقتان» is the flats on each floor (unit_count_per_level), which fills
// «الشقق واحتياجات الأسرة»; a per-floor room count is still a question, never a
// building total. No browser, network or provider call.
import assert from 'node:assert/strict';
import {analyzeBrief, buildBriefProgram} from '../../public/app/core/brief-program.mjs';
import {requirementMetrics} from '../../public/app/generated/requirement-metrics.mjs';

let passed = 0;
const check = async (name, fn) => { await fn(); passed++; console.log('PASS', name); };
const read = text => analyzeBrief(text).candidates.map(c => [c.metric, c.expected]);
const spans = text => { for (const c of analyzeBrief(text).candidates) assert.equal(Array.from(text).slice(c.source_span.start, c.source_span.end).join(''), c.evidence); };
const form = (brief, extra = {}) => ({brief, type: 'residential', width: '20', depth: '25', levels: '3', rows: [], ...extra});
const LIVE = 'عمارة سكنية من ٣ أدوار على أرض ٢٠×٢٥ متر، في كل دور شقتان، مع درج مركزي وحوش خلفي';
const LATIN = 'عمارة سكنية من 3 أدوار على أرض 20×25 متر، في كل دور شقتان، مع درج مركزي وحوش خلفي';

await check('the live sentence gives the plot, the floors and the flats on each floor, in both digit sets', () => {
  for (const [text, digits] of [[LIVE, ['٣', '٢٠×٢٥']], [LATIN, ['3', '20×25']]]) {
    const a = analyzeBrief(text);
    assert.deepEqual(a.candidates.map(c => [c.metric, c.expected, c.evidence]), [
      ['level_count', 3, digits[0] + ' أدوار'], ['site_width_m', 20, 'أرض ' + digits[1] + ' متر'],
      ['site_depth_m', 25, 'أرض ' + digits[1] + ' متر'], ['unit_count_per_level', 2, 'في كل دور شقتان']]);
    assert.deepEqual(a.questions, [], 'nothing left to ask');
    spans(text);
  }
  assert.equal(requirementMetrics.unit_count_per_level.brief_supported, true);
});

await check('the flats on every floor, in the usual phrasings', () => {
  for (const [text, n] of [['في كل دور شقتان', 2], ['وفي كل دور شقتين', 2], ['شقتين في كل دور', 2], ['شقتان لكل طابق', 2],
    ['لكل دور ٢ شقة', 2], ['لكل دور 2 شقق', 2], ['٤ شقق في كل دور', 4], ['كل دور فيه شقتين', 2], ['شقة واحدة في كل دور', 1],
    ['في كل دور شقة واحدة', 1], ['ثلاث شقق في كل دور', 3], ['أبغى عمارة بشقتين في كل دور.', 2], ['١٢ شقة في كل دور', 12]]) {
    assert.deepEqual(read(text), [['unit_count_per_level', n]], text);
    assert.deepEqual(analyzeBrief(text).questions, [], text);
    spans(text);
  }
  // A floor count beside it on the same clause is still read; a room count there is asked about.
  assert.deepEqual(read('عمارة ٣ أدوار في كل دور شقتين'), [['unit_count_per_level', 2], ['level_count', 3]]);
  const rooms = analyzeBrief('في كل دور شقتان و٣ غرف نوم');
  assert.deepEqual(rooms.candidates.map(c => c.metric), ['unit_count_per_level']);
  assert.match(rooms.questions[0], /لا للمبنى كله/);
});

await check('a qualified flat count is not one count for every floor', () => {
  for (const text of ['حوالي شقتين في كل دور', 'شقتين أو ثلاث في كل دور', '٢-٣ شقق في كل دور', 'في كل دور شقتين إلى ثلاث',
    'شقتين في كل دور علوي', 'شقتين في كل دور من الأدوار العلوية', 'شقتان في كل دور عدا الدور الأخير فيه ٣ شقق', 'لا أريد شقتين في كل دور',
    'إذا أمكن شقتين في كل دور', 'على الأقل شقتين في كل دور', 'وفي كل دور شقة بمدخل مستقل', 'عمارة ٣ أدوار، شقتين في كل دور، عدا الأرضي',
    'مئة وثلاث شقق في كل دور'])
    assert.ok(!read(text).some(([m]) => m === 'unit_count_per_level'), text);
  assert.match(analyzeBrief('٢-٣ شقق في كل دور').questions[0], /نطاق أرقام/);
});

await check('a per-floor room count stays a question, never a building total', () => {
  for (const text of ['في كل دور ٣ غرف', 'في كل دور ٣ غرف نوم', 'في كل دور، ٣ غرف نوم', 'في كل دور، وثلاث غرف نوم']) {
    const a = analyzeBrief(text);
    assert.deepEqual(a.candidates, [], text);
    assert.equal(a.questions.length, 1, text);
    assert.match(a.questions[0], /لدور أو لشقة، لا للمبنى كله/, text);
  }
  const mixed = analyzeBrief('عرض الأرض ٢٠ م، في كل دور ٣ غرف');
  assert.deepEqual(mixed.candidates.map(c => [c.metric, c.expected]), [['site_width_m', 20]]);
  assert.deepEqual(mixed.questions.length, 1);
  assert.match(mixed.questions[0], /«في كل دور ٣ غرف»/, 'the question quotes the qualified clause only');
  // A clause beside a per-floor clause keeps its room counts as questions: the scope may cover them.
  const beside = analyzeBrief('في كل دور، عرض الأرض ٢٠ م، ٤ غرف نوم');
  assert.deepEqual(beside.candidates.map(c => [c.metric, c.expected]), [['site_width_m', 20]]);
  assert.equal(beside.questions.length, 1);
});

await check('clauses split on «،» and «,» but never inside a number or a «×» pair, and not across a condition', () => {
  const grouped = analyzeBrief('في كل دور 1,000 غرف، وعرض الأرض ٢٠ م');
  assert.deepEqual(grouped.candidates.map(c => [c.metric, c.expected]), [['site_width_m', 20]]);
  assert.ok(grouped.questions[0].includes('«في كل دور 1,000 غرف،»'), grouped.questions[0]);
  const pair = analyzeBrief('في كل دور ٣ غرف ٤ ×، ٥ م، وعرض الأرض ٢٠ م');
  assert.deepEqual(pair.candidates.map(c => [c.metric, c.expected]), [['site_width_m', 20]]);
  assert.ok(pair.questions[0].includes('٤ ×، ٥ م'), pair.questions[0]);
  assert.deepEqual(read('عرض الأرض ٢٠ م, في كل دور شقتان'), [['site_width_m', 20], ['unit_count_per_level', 2]], 'a Latin comma');
  // A condition, an alternative or an exception reaches across the comma: the sentence stays held back.
  for (const text of ['إذا كانت الأرض ٢٠×٢٥ متر، في كل دور شقتان', '٣ أدوار، أو ٤ أدوار، في كل دور شقتان'])
    assert.deepEqual(read(text), [], text);
  // «٣ أدوار غير الأرضي» counts floors; it is not an exception to the flats.
  assert.deepEqual(read('عرض الأرض ٢٤ م، ٣ أدوار غير الأرضي، شقتين في كل دور'),
    [['site_width_m', 24], ['level_count', 4], ['unit_count_per_level', 2]]);
});

await check('the flats on each floor are confirmed in «الشقق واحتياجات الأسرة», not as a required row', () => {
  const p = buildBriefProgram(form(LIVE));
  assert.deepEqual(p.requirements.map(r => [r.metric, r.expected, r.source_id]),
    [['site_width_m', 20, 'brief:text'], ['site_depth_m', 25, 'brief:text'], ['level_count', 3, 'brief:text']]);
  assert.doesNotThrow(() => buildBriefProgram(form(LIVE, {units: '٢', unitsScope: 'per_level'})));
  assert.doesNotThrow(() => buildBriefProgram(form(LIVE, {units: '6', unitsScope: 'total'})));
  assert.throws(() => buildBriefProgram(form(LIVE, {units: '3', unitsScope: 'per_level'})), /تعارض بين الوصف وعدد الشقق: الوصف يذكر 2 في كل دور/);
  // A requirement row stays the confirmed value, as before.
  assert.equal(buildBriefProgram(form(LIVE, {rows: [{metric: 'unit_count_per_level', expected: '2'}]})).requirements.at(-1).evidence, 'في كل دور شقتان');
  assert.throws(() => buildBriefProgram(form(LIVE, {rows: [{metric: 'unit_count_per_level', expected: '3'}]})), /تعارض/);
  assert.throws(() => buildBriefProgram(form('في كل دور شقتان. لكل دور ٣ شقق.')), /ورد بأكثر من قيمة/);
});

// ── step 01 on a minimal DOM: «استخدام» fills the flat count of the residential editor ──
globalThis.Event = class { constructor(type, o = {}) { this.type = type; this.bubbles = !!o.bubbles; } };
class El {
  constructor(tag) { Object.assign(this, {tagName: tag.toUpperCase(), children: [], parent: null, listeners: {}, attrs: {}, dataset: {}, hidden: false, _text: '', value: '', checked: false, className: '', id: '', type: ''}); }
  get textContent() { return this._text + this.children.map(c => c.textContent).join(''); }
  set textContent(t) { this._text = String(t); this.children = []; }
  append(...nodes) { for (const n of nodes) { n.parent?.children.splice(n.parent.children.indexOf(n), 1); n.parent = this; this.children.push(n); } }
  after(...nodes) { const list = this.parent.children; let i = list.indexOf(this); for (const n of nodes) { n.parent = this.parent; list.splice(++i, 0, n); } }
  before(...nodes) { const list = this.parent.children; for (const n of nodes) { n.parent = this.parent; list.splice(list.indexOf(this), 0, n); } }
  remove() { this.parent?.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; }
  replaceChildren(...nodes) { this.children = []; this._text = ''; this.append(...nodes); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(kind, fn) { (this.listeners[kind] ||= []).push(fn); }
  dispatchEvent(event) { event.target ??= this; for (let n = this; n; n = n.parent) { for (const fn of n.listeners[event.type] || []) fn(event); if (!event.bubbles) break; } }
  click() { this.dispatchEvent(new Event('click', {bubbles: true})); }
  focus() {}
  matches(sel) {
    const m = /^([a-z]+)?(?:#([\w-]+))?(?:\.([\w-]+))?(?:\[([\w-]+)(?:="([^"]*)")?\])?$/.exec(sel);
    if (!m) return false;
    const attr = m[4] && (m[4].startsWith('data-') ? this.dataset[m[4].slice(5)] : this.attrs[m[4]] ?? this[m[4] === 'for' ? 'htmlFor' : m[4]]);
    return (!m[1] || this.tagName === m[1].toUpperCase()) && (!m[2] || this.id === m[2]) && (!m[3] || this.className.split(' ').includes(m[3]))
      && (!m[4] || (m[5] === undefined ? attr !== undefined : attr === m[5]));
  }
  closest(sel) { for (let n = this; n; n = n.parent) if (n.matches(sel)) return n; return null; }
  *walk() { for (const c of this.children) { yield c; yield* c.walk(); } }
  querySelector(sel) { return [...this.walk()].find(n => n.matches(sel)) || null; }
}
globalThis.document = {createElement: tag => new El(tag)};
const store = new Map();
globalThis.localStorage = {getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k)};
const root = new El('section'), formEl = new El('form'); formEl.id = 'cwBriefForm'; root.append(formEl);
const node = (tag, id, parent = formEl) => { const n = new El(tag); n.id = id; parent.append(n); return n; };
const label = new El('label'); label.htmlFor = 'cwBrief'; formEl.append(label);
for (const id of ['cwType', 'cwBrief']) node(id === 'cwBrief' ? 'textarea' : 'select', id);
const sizes = new El('div'); sizes.className = 'cw-fields'; formEl.append(sizes);
for (const id of ['cwWidth', 'cwDepth', 'cwLevels']) node('input', id, sizes);
for (const id of ['cwUnits', 'cwUnitsScope', 'cwCity', 'cwConfirmed', 'cwAddRequirement']) node('input', id);
node('tbody', 'cwRequirements');
const $ = id => root.querySelector('#' + id);
$('cwType').value = 'residential'; $('cwUnitsScope').value = 'total';
const flatEvents = [];
$('cwUnits').addEventListener('change', () => flatEvents.push([$('cwUnits').value, $('cwUnitsScope').value]));
const errors = [];
const {createBriefEditor} = await import('../../public/app/ui/brief-review.mjs');
const editor = createBriefEditor(root, {storageKey: () => 'draft:brief', onError: e => errors.push(e)});

await check('«استخدام» on the flats card fills the flat count per floor; a different typed count is a conflict', () => {
  $('cwBrief').value = LIVE;
  $('cwReadBrief').click();
  const offered = [...root.walk()].filter(n => n.dataset.briefMetric).map(b => b.dataset.briefMetric);
  assert.deepEqual(offered, ['level_count', 'site_width_m', 'site_depth_m', 'unit_count_per_level']);
  $('cwUseAllBrief').click();
  assert.deepEqual(['cwWidth', 'cwDepth', 'cwLevels', 'cwUnits', 'cwUnitsScope'].map(id => String($(id).value)), ['20', '25', '3', '2', 'per_level']);
  assert.deepEqual(flatEvents, [['2', 'per_level']], 'the residential editor and the plot step hear the change');
  assert.equal($('cwRequirements').children.length, 0, 'no requirement row: the chosen option confirms the flat count');
  const asked = [...$('cwBriefQuestions').children].map(n => n.textContent);
  assert.deepEqual(asked, ['ما عرض المبنى وعمقه بعد الارتدادات؟ إن تركتهما فارغين فسيُرسم المبنى بحجم الأرض كاملة.'], 'only the optional building size: ' + asked.join(' | '));
  assert.equal(editor.program().requirements.length, 3);
  $('cwUnits').value = '3';
  assert.throws(() => editor.program(), /تعارض بين الوصف وعدد الشقق/);
  assert.deepEqual(errors, []);
});

console.log('BRIEF CLAUSES: ' + passed + ' passed');
