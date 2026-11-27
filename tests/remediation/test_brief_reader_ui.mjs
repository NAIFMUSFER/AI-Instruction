// Smart brief reading in step 01, without a browser or network: the free
// reader on the owner's real brief, the program checks' parity with the server
// (acs_brief_reader.checks), the field mapping, and the card module wiring on a
// minimal DOM (paid confirmation, one read, poll, editable card, confirm fills
// the existing fields, staleness before generation, fallback to the free reader).
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {analyzeBrief,buildBriefProgram} from '../../public/app/core/brief-program.mjs';
import {readResidential} from '../../public/app/core/residential-program.mjs';
import {programChecks,programFields,checkProgram,levelSummary} from '../../public/app/core/brief-reader.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const FIX = path.join(ROOT, 'tests/remediation/fixtures/brief_reader');
const BRIEF = readFileSync(path.join(FIX, 'owner_brief.txt'), 'utf8');
const RAW = JSON.parse(readFileSync(path.join(FIX, 'owner_program.json'), 'utf8'));
let passed = 0;
const check = async (name, fn) => { await fn(); passed++; console.log('PASS', name); };
const python = (code, input) => {
  const out = spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,' + JSON.stringify(ROOT) + ');' + code],
    {input: JSON.stringify(input), encoding: 'utf8', cwd: ROOT});
  assert.equal(out.status, 0, out.stderr);
  return JSON.parse(out.stdout);
};
// The program as the server returns it (validated, with checks and cannot_do).
const PROGRAM = python('import acs_brief_reader as B;print(json.dumps(B.validate_program(json.load(sys.stdin)),ensure_ascii=False))', RAW);
const copy = v => JSON.parse(JSON.stringify(v));
// One villa over two floors: one unit per floor, a master suite, maid's and driver's rooms.
const room = (role, name, count = 1, extra = {}) => ({role, name, count, width_m: null, depth_m: null, approx: false, ensuite: false, note: null, ...extra});
const VILLA = python('import acs_brief_reader as B;print(json.dumps(B.validate_program(json.load(sys.stdin)),ensure_ascii=False))', {
  ...copy(RAW), building_type: 'villa', city: 'جدة', outdoor: [], other_requests: [],
  site: {width_m: 18, depth_m: 28, area_m2: null, street_sides: ['W'], street_width_m: null, setbacks_m: {N: null, E: null, S: null, W: null},
    footprint: {width_m: null, depth_m: null, position: null}},
  parking: {count: 2, stall_width_m: null, stall_depth_m: null, placement: 'front_setback', note: null},
  levels: [
    {name: 'الدور الأرضي', use: 'residential', note: null, units: [{name: 'الفيلا', bedrooms: null, bathrooms: null, rooms: [
      room('majlis', 'مجلس الرجال'), room('bathroom', 'دورة مياه الضيوف'), room('kitchen', 'المطبخ'), room('maid_room', 'غرفة الخادمة'),
      room('driver_room', 'غرفة السائق'), room('bathroom', 'حمام الخدمة', 2), room('bedroom', 'غرفة نوم الضيوف')]}]},
    {name: 'الدور الأول', use: 'residential', note: null, units: [{name: 'الفيلا', bedrooms: null, bathrooms: null, rooms: [
      room('bedroom', 'غرفة النوم الرئيسية', 1, {ensuite: true}), room('bathroom', 'حمام الرئيسية'), room('bedroom', 'غرف الأبناء', 3),
      room('bathroom', 'حمام مشترك', 2), room('living', 'الصالة العلوية')]}]}]});

await check('free reader: the owner brief now yields plot, depth and floors with exact evidence', () => {
  const a = analyzeBrief(BRIEF);
  assert.deepEqual(a.candidates.map(c => [c.metric, c.expected, c.evidence]),
    [['level_count', 3, 'أرضي وأول وثانٍ'], ['site_width_m', 20, 'عرض الواجهة الشمالية ٢٠ م'], ['site_depth_m', 25, 'عمق الأرض ٢٥ م']]);
  for (const c of a.candidates) assert.equal(Array.from(BRIEF).slice(c.source_span.start, c.source_span.end).join(''), c.evidence);
  assert.deepEqual(a.site_area_m2, {value: 500, evidence: 'أرض مستطيلة مساحتها ٥٠٠ م²', matches: true});
  // Two specific questions instead of six generic ones: the approximate block and a per-floor count.
  assert.equal(a.questions.length, 2);
  assert.match(a.questions[0], /^القيمة تقريبية في «- كتلة المبنى: ١٣ × ١٦ م/);
  assert.match(a.questions[1], /لدور أو لشقة، لا للمبنى كله/);
  assert.ok(!a.questions.some(q => q.includes('السفرة') || q.includes('غرفتا الأبناء')), 'room sizes are not requirement questions');
  assert.deepEqual(readResidential(BRIEF), {units: 1, scope: 'per_level', unitEvidence: 'كل دور شقه', street: 'N'});
  const p = buildBriefProgram({brief: BRIEF, type: 'residential', width: '20', depth: '25', levels: '3', rows: []});
  assert.deepEqual(p.requirements.map(r => [r.metric, r.expected, r.source_id]),
    [['site_width_m', 20, 'brief:text'], ['site_depth_m', 25, 'brief:text'], ['level_count', 3, 'brief:text']]);
});

await check('free reader: common owner phrasings', () => {
  const read = t => analyzeBrief(t).candidates.map(c => [c.metric, c.expected]);
  assert.deepEqual(read('عمارة أرضي + ٢'), [['level_count', 3]]);
  assert.deepEqual(read('دور أرضي ودور أول ودور ثانٍ'), [['level_count', 3]]);
  assert.deepEqual(read('أرضي وأول أو ثاني'), [], 'an alternative is not a list');
  assert.deepEqual(read('الشقق في الأرضي والأول'), [], 'a reference to floors is not a count');
  assert.deepEqual(read('عرض الأرض ٢٠ م وعمق الأرض ٢٥ م'), [['site_width_m', 20], ['site_depth_m', 25]]);
  assert.deepEqual(read('الأرض عرضها ٢٠ مترًا وعمقها ٢٥ مترا'), [['site_width_m', 20], ['site_depth_m', 25]]);
  assert.deepEqual(read('عرض الأرض ٢٠٫٥ م'), [['site_width_m', 20.5]]);
  assert.deepEqual(read('أرض مساحتها ٥٠٠ م² وعرض الأرض ٢٠ م'), [['site_width_m', 20], ['site_depth_m', 25]], 'area supplies the missing side');
  assert.match(analyzeBrief('أرض مساحتها ٦٠٠ م²؛ عرض الأرض ٢٠ م؛ عمق الأرض ٢٥ م').questions[0], /لا تساوي العرض × العمق/);
  assert.deepEqual(read('عرض الواجهة الشرقية ٢٠ م على الشارع'), [], 'an east frontage is the depth: asked, not guessed');
  assert.match(analyzeBrief('عرض الواجهة الشرقية ٢٠ م على الشارع').questions[0], /عمق الموقع/);
  assert.deepEqual(read('نحو ٣ غرف نوم'), [], 'approximate is not exact');
  assert.equal(readResidential('شقة واحدة في كل دور').units, 1);
  assert.equal(readResidential('الشارع من جهة الغرب').street, 'W');
  assert.equal(readResidential('أرض شمالية').street, 'N');
  assert.equal(readResidential('على شارعين: الشارع الشمالي والشارع الشرقي').street, undefined, 'two streets: the owner picks the primary');
});

await check('program checks match the server for the same programs', () => {
  const variants = [copy(RAW)];
  const a = copy(RAW); a.site.area_m2 = 600; a.site.setbacks_m.E = 4; variants.push(a);
  const b = copy(RAW); b.levels[0].units[0].rooms[0].width_m = 12; b.levels[0].units[0].rooms[0].depth_m = 12; b.levels[2].units[0].bedrooms = 5; variants.push(b);
  const c = copy(RAW); c.site.footprint = {width_m: null, depth_m: null, position: null}; c.site.setbacks_m.S = 10; variants.push(c);
  const server = python('import acs_brief_reader as B\nprint(json.dumps([B.validate_program(p)["checks"] for p in json.load(sys.stdin)],ensure_ascii=False))', variants);
  variants.forEach((v, i) => assert.deepEqual(programChecks(v), server[i], 'variant ' + i));
  assert.equal(server[0].length, 1);
  assert.ok(server[2].some(n => n.code === 'LEVEL_AREA'));
});

await check('confirmed program maps onto the existing step-01 fields', () => {
  const f = programFields(PROGRAM);
  assert.deepEqual({...f, notes: f.notes.length}, {
    width: 20, depth: 25, levels: 3, buildingWidth: 13, buildingDepth: 16, street: 'N', street2: null, streetWidth: null,
    setbacks: {N: 5.5, E: 5.5, S: 3.5, W: 1.5}, units: {units: 1, scope: 'per_level'}, bedrooms: null, bathrooms: null,
    guests: 'suggest', city: 'الرياض', parking: {placement: 'front_setback', count: 2}, landing: true,
    rows: [{metric: 'room_count', role: 'bedroom', expected: 9}, {metric: 'room_count', role: 'bathroom', expected: 9}], notes: 1, villa: null});
  const uniform = copy(PROGRAM); uniform.levels = [uniform.levels[1], copy(uniform.levels[1])];
  const u = programFields(uniform);
  assert.equal(u.bedrooms, 4); assert.equal(u.bathrooms, 3); assert.deepEqual(u.rows, []); assert.equal(u.guests, 'separate');
  const v = programFields(VILLA);
  assert.equal(v.units, null, 'a villa is one dwelling, not a flat count');
  assert.deepEqual(v.rows, [], 'the villa fields carry its program');
  assert.deepEqual(v.villa, {bedrooms: 5, master: 'yes', bathrooms: 6, maid: 'yes', driver: 'yes'});
  assert.deepEqual([v.width, v.depth, v.levels, v.street], [18, 28, 2, 'W']);
  assert.equal(levelSummary(PROGRAM.levels[0]), 'شقة واحدة · 3 غرف نوم · 4 حمامات · 13 بندًا');
  const bad = copy(PROGRAM); bad.levels[0].units[0].rooms[0].count = 0;
  assert.throws(() => checkProgram(bad), /العدد من 1 إلى 12/);
  const wide = copy(PROGRAM); wide.site.footprint.width_m = 25;
  assert.throws(() => checkProgram(wide), /كتلة المبنى أكبر من الأرض/);
});

// ── minimal DOM for the step-01 card module ─────────────────────────────────
globalThis.Event = class { constructor(type, o = {}) { this.type = type; this.bubbles = !!o.bubbles; this.stopped = false; } stopPropagation() { this.stopped = true; } };
class El {
  constructor(tag) {
    Object.assign(this, {tagName: tag.toUpperCase(), children: [], parent: null, listeners: {}, attrs: {}, dataset: {}, hidden: false, _text: '',
      value: '', checked: false, className: '', id: '', disabled: false, open: false, type: '', inputMode: ''});
    this.classList = {toggle: (c, on) => { const s = new Set(this.className.split(' ').filter(Boolean)); (on ?? !s.has(c)) ? s.add(c) : s.delete(c); this.className = [...s].join(' '); },
      contains: c => this.className.split(' ').includes(c)};
  }
  get textContent() { return this._text + this.children.map(c => typeof c === 'string' ? c : c.textContent).join(''); }
  set textContent(t) { this._text = String(t); this.children = []; }
  get lastChild() { return this.children[this.children.length - 1]; }
  append(...nodes) { for (const n of nodes) { if (typeof n !== 'string') { n.detach(); n.parent = this; } this.children.push(n); } }
  after(...nodes) { const list = this.parent.children; let i = list.indexOf(this); for (const n of nodes) { n.detach(); n.parent = this.parent; list.splice(++i, 0, n); } }
  detach() { if (this.parent) { this.parent.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; } }
  replaceChildren(...nodes) { this.children = []; this._text = ''; this.append(...nodes); }
  addEventListener(kind, fn) { (this.listeners[kind] ||= []).push(fn); }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    for (let n = this; n; n = n.parent) { for (const fn of n.listeners[event.type] || []) fn(event); if (!event.bubbles || event.stopped) break; }
  }
  click() { if (!this.disabled) this.dispatchEvent(new Event('click', {bubbles: true})); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] ?? null; }
  *walk() { for (const c of this.children) if (typeof c !== 'string') { yield c; yield* c.walk(); } }
  matches(sel) {
    const m = /^([a-z]+)?(?:#([\w-]+))?(?:\.([\w-]+))?(?:\[data-([\w-]+)\])?$/.exec(sel);
    return !!m && (!m[1] || this.tagName === m[1].toUpperCase()) && (!m[2] || this.id === m[2])
      && (!m[3] || this.className.split(' ').includes(m[3])) && (!m[4] || this.dataset[m[4]] !== undefined);
  }
  querySelectorAll(sel) {
    const [first, ...rest] = sel.split(' ');
    let found = [...this.walk()].filter(n => n.matches(first));
    for (const part of rest) found = found.flatMap(n => [...n.walk()].filter(c => c.matches(part)));
    return found;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  scrollIntoView() {}
}
globalThis.document = {createElement: tag => new El(tag)};
const storage = new Map();
globalThis.localStorage = {getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, String(v)), removeItem: k => storage.delete(k)};
const root = new El('section'), form = new El('form'); form.id = 'cwBriefForm'; root.append(form);
const ids = ['cwType', 'cwBrief', 'cwReadBrief', 'cwBriefReview', 'cwWidth', 'cwDepth', 'cwLevels', 'cwBldWidth', 'cwBldDepth', 'cwUnits', 'cwUnitsScope',
  'cwBedrooms', 'cwBathrooms', 'cwGuests', 'cwCity', 'cwStreet', 'cwPlotStreet2', 'cwPlotStreetWidth', 'cwPlotSetbackN', 'cwPlotSetbackE',
  'cwPlotSetbackS', 'cwPlotSetbackW', 'cwPlotParking', 'cwPlotParkingCount', 'cwPlotLanding',
  'cwVillaBedrooms', 'cwVillaMaster', 'cwVillaBathrooms', 'cwVillaMaid', 'cwVillaDriver'];
for (const id of ids) { const n = new El(id === 'cwReadBrief' ? 'button' : 'input'); n.id = id; form.append(n); }
const $ = id => root.querySelector('#' + id);
const reset = () => { for (const id of ids) $(id).value = ''; $('cwType').value = 'residential'; $('cwStreet').value = 'unknown'; $('cwPlotLanding').checked = false; $('cwBrief').value = BRIEF;
  for (const id of ['cwVillaMaster']) $(id).value = 'yes'; for (const id of ['cwVillaMaid', 'cwVillaDriver']) $(id).value = 'no'; };
reset();
const formEvents = [];
form.addEventListener('input', e => formEvents.push(e.target.id));
let freeReads = 0; $('cwReadBrief').addEventListener('click', () => freeReads++);
const calls = [], confirms = [], used = [];
let answers = [], approve = true;
const api = async body => { calls.push(body); const next = answers.shift(); if (next instanceof Error) throw next; return next; };
const confirmPaid = async (text, go, title) => { confirms.push({text, go, title}); return approve; };
const {createBriefReader} = await import('../../public/app/ui/brief-reader.mjs');
const reader = createBriefReader(root, {api, confirmPaid, briefEditor: {useValues: rows => used.push(...rows)},
  storageKey: () => 'draft:program', jobKey: () => 'job:read', localDraftKeys: () => ['draft:brief']});
const settle = () => new Promise(r => setTimeout(r, 0));
const card = $('cwProgramCard');

await check('the paid read starts only after an explicit confirmation', async () => {
  assert.equal($('cwSmartRead').textContent, 'قراءة ذكية (مدفوعة)', 'the button itself says the read is paid');
  assert.match($('cwSmartReadNote').textContent, /طلب واحد مدفوع.*من دقيقة إلى ثلاث دقائق/);
  approve = false; $('cwSmartRead').click(); await settle();
  assert.equal(confirms[0].title, 'قراءة الوصف بالذكاء الاصطناعي؟');
  assert.match(confirms[0].text, /طلب واحد/);
  assert.match(confirms[0].text, /لن تتغير حقولك قبل أن تراجع البطاقة/);
  assert.deepEqual(calls, [], 'cancelled: nothing sent');
  assert.match($('cwProgramStatus').textContent, /لم يُستهلك أي رصيد/);
});

await check('one read, polled to a validated program shown in an editable card', async () => {
  approve = true;
  const realTimeout = globalThis.setTimeout;
  let sent;
  // The submission's reply is lost (status 0): the same job is followed, never resent.
  answers = [Object.assign(new Error('network'), {code: 'AUTH_NETWORK', status: 0})];
  globalThis.setTimeout = fn => realTimeout(fn, 1000);   // hold the poll until the reload below
  try {
    $('cwSmartRead').click(); await settle();
    sent = calls[0];
    assert.deepEqual({...sent, job_id: typeof sent.job_id}, {action: 'read_brief', job_id: 'string', brief: BRIEF.trim(), confirmed: true, max_provider_calls: 1});
    assert.equal(JSON.parse(storage.get('job:read')).jobId, sent.job_id, 'the job id survives a reload');
    assert.match($('cwProgramStatus').textContent, /دون إرسال طلب جديد/);
    calls.length = 0;
    answers = [{job: null}, {job: {id: sent.job_id, state: 'RUNNING', phase: 'UNDERSTANDING'}}, {job: {id: sent.job_id, state: 'SUCCEEDED', program: PROGRAM}}];
    globalThis.setTimeout = fn => realTimeout(fn, 0);   // poll at once
    reader.fill(null);   // reload: the pending job resumes
    for (let i = 0; i < 20 && card.hidden; i++) await new Promise(r => realTimeout(r, 5));
  } finally { globalThis.setTimeout = realTimeout; }
  assert.deepEqual(calls.map(c => [c.action, c.job_id]), [['job', sent.job_id], ['job', sent.job_id], ['job', sent.job_id]]);
  assert.equal(card.hidden, false);
  assert.equal(storage.has('job:read'), false);
  assert.equal($('cwProgramTitle').textContent, 'فهمنا من وصفك:');
  assert.equal($('cwProgramWidth').value, '20');
  assert.equal($('cwProgramSetbackW').value, '1.5');
  assert.match(card.textContent, /من وصفك/);
  assert.match(card.textContent, /سيُرسم لاحقًا/);
  assert.match(card.textContent, /الدور الأول/);
  assert.match($('cwProgramChecks').textContent, /عدد الحمامات في الوصف 3، والمدرج في البرنامج 2/);
  assert.match($('cwProgramUnsupported').textContent, /القطاع الرأسي غير متاح بعد/);
  assert.equal($('cwWidth').value, '', 'nothing is filled before confirmation');
  // The owner first reads a short summary; the editable form is folded under «تعديل التفاصيل».
  assert.match($('cwProgramSummary').textContent, /الأرض 20 × 25 م/);
  assert.equal($('cwProgramEdit').tagName, 'DETAILS');
});

await check('editing the card stays in the card until confirmation', async () => {
  formEvents.length = 0;
  $('cwProgramSetbackE').value = '٥٫٥'; $('cwProgramSetbackE').dispatchEvent(new Event('input', {bubbles: true}));
  assert.deepEqual(formEvents, [], 'card edits do not reach the requirements form');
  $('cwProgramSetbackS').value = ''; $('cwProgramSetbackS').dispatchEvent(new Event('input', {bubbles: true}));
  assert.match(card.textContent, /افتراض: يحسبه ACS من الاشتراطات/);
  $('cwProgramSetbackS').value = '3.5'; $('cwProgramSetbackS').dispatchEvent(new Event('input', {bubbles: true}));
  assert.equal($('cwWidth').value, '');
});

await check('confirm fills the existing step-01 fields and requirement rows', async () => {
  $('cwProgramConfirm').click();
  const values = Object.fromEntries(['cwWidth', 'cwDepth', 'cwLevels', 'cwBldWidth', 'cwBldDepth', 'cwUnits', 'cwUnitsScope', 'cwCity', 'cwStreet',
    'cwPlotSetbackN', 'cwPlotSetbackE', 'cwPlotSetbackS', 'cwPlotSetbackW', 'cwPlotParking', 'cwPlotParkingCount', 'cwBedrooms'].map(id => [id, $(id).value]));
  assert.deepEqual(values, {cwWidth: '20', cwDepth: '25', cwLevels: '3', cwBldWidth: '13', cwBldDepth: '16', cwUnits: '1', cwUnitsScope: 'per_level',
    cwCity: 'الرياض', cwStreet: 'N', cwPlotSetbackN: '5.5', cwPlotSetbackE: '5.5', cwPlotSetbackS: '3.5', cwPlotSetbackW: '1.5',
    cwPlotParking: 'front_setback', cwPlotParkingCount: '2', cwBedrooms: ''});
  assert.equal($('cwPlotLanding').checked, true);
  assert.deepEqual(used, [{metric: 'room_count', role: 'bedroom', expected: 9}, {metric: 'room_count', role: 'bathroom', expected: 9}]);
  assert.ok(formEvents.includes('cwWidth') && formEvents.includes('cwPlotSetbackN'), 'filled fields announce themselves like typed input');
  assert.match($('cwProgramStatus').textContent, /عبّأنا من البرنامج المؤكد/);
  const sent = reader.command();
  assert.equal(sent.program.schema, 'acs.brief-program/1');
  assert.equal(sent.program.checks, undefined); assert.equal(sent.program.cannot_do, undefined);
  assert.equal(JSON.parse(storage.get('draft:program')).confirmed, true);
  $('cwWidth').value = '22';
  assert.throws(() => reader.command(), /أكّد البطاقة من جديد/);
  $('cwWidth').value = '20';
  assert.doesNotThrow(() => reader.command());
});

await check('a single-dwelling program fills the villa fields, not a flat count', async () => {
  reset(); used.length = 0;
  reader.fill({head: 'plan_villa', brief: 'فيلا', requirements: [], brief_program: null, plot_input: null});
  storage.set('draft:program', JSON.stringify({program: VILLA, confirmed: false, key: null, source: 'ai', brief: null}));
  reader.fill(null);
  $('cwProgramConfirm').click();
  assert.deepEqual(['cwVillaBedrooms', 'cwVillaMaster', 'cwVillaBathrooms', 'cwVillaMaid', 'cwVillaDriver', 'cwUnits', 'cwWidth', 'cwStreet', 'cwCity'].map(id => $(id).value),
    ['5', 'yes', '6', 'yes', 'yes', '', '18', 'W', 'جدة']);
  assert.deepEqual(used, [], 'no flat-count rows for a villa');
  assert.match($('cwProgramStatus').textContent, /برنامج الفيلا/);
  $('cwProgramDismiss').click(); reset();
  storage.set('draft:program', JSON.stringify({program: PROGRAM, confirmed: true, key: JSON.stringify([20, 25, 3, 13, 16]), source: 'ai', brief: null}));
});

await check('a saved program and a cloud program are restored; dismissing sends nothing', async () => {
  reader.fill(null);
  assert.equal(card.hidden, false);
  assert.equal(reader.current().confirmed, true);
  $('cwProgramDismiss').click();
  assert.deepEqual(reader.command(), {});
  assert.equal(storage.has('draft:program'), false);
  reset();
  reader.fill({head: 'plan_1', brief: BRIEF, requirements: [], brief_program: PROGRAM, plot_input: null});
  assert.equal(reader.current().source, 'cloud');
  assert.equal($('cwPlotSetbackW').value, '1.5', 'another device restores plot inputs from the revision');
  assert.equal($('cwUnits').value, '1');
  assert.equal($('cwWidth').value, '', 'width/depth/levels come back through the requirements, not twice');
  storage.delete('draft:program'); reset();
  reader.fill({head: 'plan_2', brief: 'عمارة\nالمدينة: جدة؛ جهة الشارع: شمال.', brief_program: null,
    requirements: [{metric: 'unit_count_per_level', expected: 2}, {metric: 'room_count_per_unit', role: 'bedroom', expected: 3}],
    plot_input: {streets: ['S'], setbacks_m: {N: 2}, parking: {placement: 'pilotis', count: 6}, landing_entries: true}});
  assert.deepEqual(['cwStreet', 'cwPlotSetbackN', 'cwPlotParking', 'cwPlotParkingCount', 'cwUnits', 'cwUnitsScope', 'cwBedrooms', 'cwCity'].map(id => $(id).value),
    ['S', '2', 'pilotis', '6', '2', 'per_level', '3', 'جدة'], 'older revisions still restore plot and flat inputs');
  assert.equal(card.hidden, true);
});

await check('a failed or refused read falls back to the free reader with an Arabic reason', async () => {
  reset(); const before = freeReads; calls.length = 0;
  const realTimeout = globalThis.setTimeout;
  globalThis.setTimeout = fn => realTimeout(fn, 0);
  try {
    answers = [{job: {id: 'another-job', state: 'RUNNING'}}];
    $('cwSmartRead').click(); await settle();
    // The answer named another job, so the next poll asks for this one.
    answers.push({job: {id: calls[0].job_id, state: 'FAILED', error_code: 'BRIEF_READ_INVALID_JSON', error_message: null}});
    for (let i = 0; i < 20 && freeReads === before; i++) await new Promise(r => realTimeout(r, 5));
  } finally { globalThis.setTimeout = realTimeout; }
  assert.deepEqual(calls.map(c => c.action), ['read_brief', 'job']);
  assert.equal(freeReads, before + 1, 'the free local reader ran');
  assert.match($('cwProgramStatus').textContent, /لم يرجع الذكاء الاصطناعي برنامجًا مقروءًا.*القارئ المحلي المجاني/);
  const refused = Object.assign(new Error('تجاوزت حد التوليد. حاول لاحقًا.'), {code: 'ACS_RATE_LIMITED', status: 429});
  answers = [refused]; calls.length = 0;
  $('cwSmartRead').click(); await settle();
  assert.equal(calls.length, 1);
  assert.equal(freeReads, before + 2);
  assert.match($('cwProgramStatus').textContent, /^تجاوزت حد التوليد/);
  assert.equal(storage.has('job:read'), false, 'a refusal leaves no job to follow');
});

console.log('BRIEF READER UI: ' + passed + ' passed, 0 failed');
