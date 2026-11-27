// An early, honest refusal before the paid confirmation (live QA): a 20 × 25 m
// plot with six flats assumed 9 stalls (1.5 per flat) where about 6 fit in the
// front setback. The server refused the request after the owner had confirmed the
// paid dialog, and the page called that refusal a lost confirmation to recover.
// Here: the client preflight gives the server's verdict on the same request, before
// the dialog; a 4xx refusal releases the request and keeps the inputs; only a real
// loss after sending keeps the recovery flow; the dialog states the call ceiling sent.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import {plotPreflight, preview, summaryText} from '../../public/app/core/plot-rules.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let passed = 0;
const check = async (name, fn) => { await fn(); passed++; console.log('PASS', name); };
const python = (code, input) => {
  const out = spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,' + JSON.stringify(ROOT) + ');' + code],
    {input: JSON.stringify(input), encoding: 'utf8', cwd: ROOT});
  assert.equal(out.status, 0, out.stderr);
  return JSON.parse(out.stdout);
};
const rows = ({w = 20, d = 25, levels = 3, units = 6, bw, bd} = {}) => [
  {metric: 'site_width_m', expected: w}, {metric: 'site_depth_m', expected: d}, {metric: 'level_count', expected: levels},
  ...(units != null ? [{metric: 'unit_count', expected: units}] : []),
  ...(bw != null ? [{metric: 'building_width_m', expected: bw}, {metric: 'building_depth_m', expected: bd}] : [])];
const plot = (extra = {}) => ({streets: [], setbacks_m: {}, parking: {placement: 'front_setback'}, landing_entries: false, ...extra});
const LIVE = {brief: 'عمارة سكنية من ٣ أدوار على أرض ٢٠×٢٥ متر، في كل دور شقتان، مع درج مركزي وحوش خلفي\n\nنوع المشروع: سكني / عمارة / فيلا',
  requirements: rows(), plot: plot()};

await check('the client preflight gives the server verdict on the same request', () => {
  const ground = use => ({levels: [{name: 'الدور الأرضي', use, units: []}, {name: 'الأول', use: 'residential', units: [{name: 'أ'}]}]});
  const cases = [
    LIVE,
    {...LIVE, plot: plot({parking: {placement: 'front_setback', count: 6}})},
    {...LIVE, plot: plot({parking: {placement: 'front_setback', count: 7}})},
    {...LIVE, requirements: rows({units: 4}), plot: plot({parking: {placement: 'pilotis'}})},
    {...LIVE, plot: plot({parking: {placement: 'none'}})},
    {...LIVE, requirements: rows({units: null})},
    {...LIVE, plot: plot({setbacks_m: {N: 12, S: 12}})},
    {...LIVE, requirements: rows({bw: 18, bd: 20})},
    {...LIVE, requirements: rows({levels: 1, units: 4}), plot: plot({parking: {placement: 'pilotis'}})},
    {...LIVE, requirements: rows({w: 12, d: 20, units: 8}), plot: plot({parking: {placement: 'pilotis'}})},
    {...LIVE, plot: plot({streets: ['E']}), requirements: rows({d: 30})},
    // A confirmed program card fills what the plot block leaves empty, as on the server.
    {...LIVE, requirements: rows({d: 30}), program: {site: {street_sides: ['E']}}},
    {...LIVE, program: {parking: {count: 6, stall_width_m: 2.7, stall_depth_m: 5.2}}},
    {...LIVE, program: {parking: {count: 6}}},
    {...LIVE, requirements: rows({units: 4}), program: ground('parking')},
    {...LIVE, requirements: rows({w: 12, d: 20, units: 8}), program: ground('parking')},
    {...LIVE, plot: plot({parking: {placement: 'pilotis'}}), program: {site: {footprint: {width_m: 14, depth_m: 16, position: null}}}},
    {...LIVE, requirements: rows({units: 9}), plot: plot({parking: {placement: 'pilotis'}})},
    // One villa: one stall up to 400 m² of land, two above.
    {brief: 'أبغى فيلا عائلية في جدة', requirements: rows({w: 15, d: 20, levels: 2, units: null}), plot: plot()},
    {brief: 'أبغى فيلا عائلية في جدة', requirements: rows({w: 6, d: 30, levels: 2, units: null}), plot: plot()},
    {...LIVE, requirements: rows({w: 0})},
  ];
  const server = python(`
import acs_plot_rules as P
from acs_plan_review import PlanError
out=[]
for c in json.load(sys.stdin):
    try:
        P.resolve(c['plot'], c['brief'], c['requirements'], None, program=c.get('program'))
        out.append(None)
    except PlanError as e:
        out.append(e.code)
print(json.dumps(out))`, cases);
  const client = cases.map(c => plotPreflight(c)?.code ?? null);
  assert.deepEqual(client, server);
  assert.ok(server.filter(Boolean).length >= 8 && server.filter(c => c === null).length >= 7, JSON.stringify(server));
  assert.equal(server[0], 'PLOT_PARKING_DOES_NOT_FIT', 'the live request');
});

await check('the live refusal names the assumption, the capacity and the three fixes, in Arabic', () => {
  const {message} = plotPreflight(LIVE);
  for (const part of ['المواقف المطلوبة 9', '1.5 موقف لكل شقة × 6 شقق', 'إلا لنحو 6', '«عدد المواقف»', 'افتراض قابل للتعديل',
    '«تحت المبنى في الدور الأرضي (بيلوتي)»', '«بدون مواقف في هذا المقترح', 'لم يُرسل أي طلب ولم يُستهلك أي رصيد', 'الخطوة 01'])
    assert.ok(message.includes(part), part + ' in ' + message);
  assert.ok(!/[A-Z]{3,}/.test(message), 'no raw code');
  // Step 01 shows the requirement against the capacity whether it fits or not.
  const fits = preview({levels: 3, units: 4, width: 20, depth: 25, placement: 'pilotis'});
  assert.match(summaryText(fits, 'pilotis'), /المواقف المطلوبة 6 \(افتراض نظامي: 1\.5 موقف لكل شقة × 4 شقق مقربة للأعلى\)؛ السعة التقديرية 11 في الدور الأرضي\./);
  const typed = preview({levels: 3, units: 6, width: 20, depth: 25, count: 8});
  assert.match(summaryText(typed, 'front_setback'), /المواقف المطلوبة 8 \(من إدخالك\) ولا يتسع الارتداد الأمامي بطول 20 م إلا لنحو 6.*قلّل «عدد المواقف» إلى 6 أو أقل/);
});

// ── the shipped generate handler, run on stubs ──────────────────────────────
const source = readFileSync(new URL('../../public/app/ui/connected-workspace.mjs', import.meta.url), 'utf8');
const start = source.indexOf('function generationCalls(program){');
const handler = source.slice(start, source.indexOf('async function handleJob(', start));
assert.ok(start > 0 && handler.includes('async function generation('), 'generate handler found');
assert.match(source, /if\(!session\)throw Object\.assign\(new Error\('انتهت جلسة الدخول[^']*'\),\{code:'AUTH_REQUIRED',status:401\}\)/,
  'a missing session fails before sending, as a refusal');

function setup({request = LIVE, answer, budget = '8', reading = {}} = {}) {
  const nodes = new Map(), storage = new Map(), t = {confirms: [], requests: [], statuses: [], steps: [], shown: 0, handled: []};
  const $ = id => { if (!nodes.has(id)) nodes.set(id, {id, hidden: true, checked: true, value: id === 'cwBudget' ? budget : id === 'cwType' ? 'residential' : ''}); return nodes.get(id); };
  const context = vm.createContext({
    $, root: {querySelector: () => null}, state: {head: 'R1'}, pendingJob: null, pollTimer: null,
    crypto: {randomUUID: () => 'J1'}, jobKey: () => 'job',
    localStorage: {setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k)},
    planUpload: {command: () => ({}), calls: () => null, confirm: () => null},
    plotRules: {command: () => ({plot: request.plot}), preflight: plotPreflight, show: () => { t.shown++; }},
    residentialOptions: {program: base => base}, briefProgram: () => ({brief: request.brief, requirements: request.requirements}),
    briefReader: {command: () => reading},
    confirmPaid: async text => { t.confirms.push(text); return true; },
    beginJob: id => { context.pendingJob = id; storage.set('job', id); $('cwJobProgress').hidden = false; },
    stopProgress: () => { $('cwJobProgress').hidden = true; }, progressPhase() {}, setBusy() {}, clearTimeout() {},
    status: (text, bad) => t.statuses.push([!!bad, text]), step: n => t.steps.push(n),
    ownerMessage: (code, message, fallback) => typeof message === 'string' && /[؀-ۿ]/.test(message) ? message : fallback,
    api: async body => { t.requests.push(body); if (answer instanceof Error) throw answer; return answer; },
    handleJob: async job => { t.handled.push(job); },
  });
  vm.runInContext(handler, context);
  return {t, context, storage, $};
}
const failure = (status, code, message) => Object.assign(new Error(message), {status, code});
const FITS = {...LIVE, plot: plot({parking: {placement: 'front_setback', count: 6}})};

await check('a refusal the client can see stops before the paid dialog, with nothing pending', async () => {
  const {t, context, storage} = setup();
  await assert.rejects(context.generation('A'), e => e.message.includes('ولا يتسع الارتداد الأمامي') && e.message.includes('لم يُرسل أي طلب'));
  assert.equal(t.confirms.length, 0, 'the paid dialog never opens');
  assert.equal(t.requests.length, 0, 'nothing is sent');
  assert.equal(context.pendingJob, null); assert.equal(storage.has('job'), false, 'no pending job id is stored');
  assert.deepEqual(t.steps, [1], 'back to step 01'); assert.equal(t.shown, 1, 'the plot inputs are opened');
});

await check('a server refusal (4xx with its code) shows its Arabic reason, keeps the inputs and leaves no job to recover', async () => {
  const reason = 'المساحة القابلة للبناء 280 م² في الدور لا تكفي 2 شقق بنحو 130 م² للشقة مع الدرج. قلّل الشقق في الدور أو عدد الغرف، أو راجع الارتدادات ونسبة البناء.';
  for (const [answer, plotStep] of [[failure(400, 'PLOT_ENVELOPE_TOO_SMALL', reason), true],
    [failure(409, 'GENERATION_IN_PROGRESS', 'توجد مهمة توليد أو تعديل جارية لهذا المشروع. تابعها حتى تنتهي ثم افتح آخر نسخة؛ لم يُرسل أي طلب إلى مزود النموذج.'), false],
    [failure(429, 'ACS_RATE_LIMITED', 'تجاوزت حد التوليد. حاول لاحقًا.'), false],
    [failure(401, 'AUTH_REQUIRED', 'انتهت جلسة الدخول. أعد تحميل الصفحة لتسجيل الدخول؛ نسخك محفوظة.'), false]]) {
    const {t, context, storage, $} = setup({request: FITS, answer});
    await context.generation('A');
    assert.equal(t.confirms.length, 1); assert.equal(t.requests.length, 1, 'sent once, never resent');
    const [bad, text] = t.statuses.at(-1);
    assert.ok(bad && text.startsWith(answer.message) && text.includes('لم يبدأ التوليد') && text.includes('مدخلاتك كما هي'), text);
    assert.ok(!/لم يصل تأكيد|متابعة المهمة|استعد/.test(text), 'no lost-confirmation or recovery wording: ' + text);
    assert.equal(context.pendingJob, null, answer.code); assert.equal(storage.has('job'), false, 'the pending job id is released: ' + answer.code);
    assert.equal($('cwRecoverJob').hidden, true); assert.equal($('cwJobProgress').hidden, true);
    assert.deepEqual(t.steps, plotStep ? [1] : [], answer.code);
    assert.equal(t.handled.length, 0);
  }
});

await check('a refused chat edit is released the same way', async () => {
  assert.ok(source.includes("catch(err){if(refusedByServer(err)){refusedGeneration(err,'التعديل');return;}throw err;}"), 'the chat edit tells a refusal from a loss');
  const {t, context, storage} = setup();
  context.pendingJob = 'J2'; storage.set('job', 'J2');
  context.refusedGeneration(failure(409, 'STALE_REVISION', 'افتح آخر نسخة قبل التوليد.'), 'التعديل');
  assert.equal(context.pendingJob, null); assert.equal(storage.has('job'), false);
  assert.equal(t.statuses.at(-1)[1], 'افتح آخر نسخة قبل التوليد. لم يبدأ التعديل، ولم يُرسل أي طلب إلى الذكاء الاصطناعي، ومدخلاتك كما هي.');
});

await check('a loss after sending (no answer, or a 5xx) keeps the recovery flow on the same job', async () => {
  for (const answer of [failure(0, 'AUTH_NETWORK', 'تعذّر الاتصال. تحقق من الإنترنت وحاول مجددًا؛ لم تُحذف جلستك.'),
    failure(503, 'STORE_UNAVAILABLE', 'لم يصل تأكيد حفظ المهمة.'), failure(502, 'AUTH_INVALID_RESPONSE', 'استجابة خدمة الدخول غير مكتملة. حاول مجددًا.'),
    failure(408, 'AUTH_FAILED', 'تعذّر إكمال العملية. حاول مجددًا.')]) {
    const {t, context, storage, $} = setup({request: FITS, answer});
    await context.generation('A');
    const [bad, text] = t.statuses.at(-1);
    assert.ok(bad && text.startsWith('لم يصل تأكيد الطلب. استخدم متابعة المهمة'), text);
    assert.equal(context.pendingJob, 'J1', answer.code); assert.equal(storage.get('job'), 'J1', 'the job id stays for «متابعة المهمة»');
    assert.equal($('cwRecoverJob').hidden, false);
  }
  const ok = setup({request: FITS, answer: {job: {id: 'J1', state: 'RUNNING'}}});
  await ok.context.generation('A');
  assert.deepEqual(JSON.parse(JSON.stringify(ok.t.handled)), [{id: 'J1', state: 'RUNNING'}], 'an admitted job is followed');
});

await check('the paid dialog states the call ceiling the request sends', async () => {
  const three = {program: {levels: [{}, {}, {}]}};
  for (const [budget, reading, calls, words] of [['8', three, 12, 'حتى 12 طلبًا'], ['8', {}, 8, 'حتى 8 طلبات'], ['3', three, 3, 'حتى 3 طلبات'], ['6', {}, 6, 'حتى 6 طلبات']]) {
    const {t, context} = setup({request: FITS, answer: {job: {id: 'J1', state: 'RUNNING'}}, budget, reading});
    await context.generation('A');
    assert.equal(t.requests[0].max_provider_calls, calls);
    assert.ok(t.confirms[0].includes(words) && t.confirms[0].includes('أربع دقائق') && t.confirms[0].includes('رصيد'), t.confirms[0]);
  }
});

console.log('GENERATION PREFLIGHT: ' + passed + ' passed');
