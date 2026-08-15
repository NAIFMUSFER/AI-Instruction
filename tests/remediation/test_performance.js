/* ============================================================================
   F-14 — عقد الأداء: ميزانيات معلنة، حاكم جودة لا يمسّ الهندسة، ومِرقاب لا
   يكذب حين يعجز.

   يُشغَّل هكذا:
     node tests/remediation/test_performance.js                (كما في run_all.sh)
     node tests/lib/run.js tests/remediation/test_performance.js

   أربعة أشياء تُثبَت:
     §1 ميزانيات tests/performance/budgets.json تُحلَّل، ومعلَنة أهدافاً لا
        نتائج، ولا رقم فيها يُقدَّم على أنه مقيس.
     §2 tests/performance/quality_governor.json لا يسمح — بأي مستوى جودة —
        بحذف أي هندسة دلالية. يُطبَّق عقد التحقّق المكتوب داخل الملفّ نفسه على
        الملفّ، ثم على نسخ معادية منه يجب أن يرفضها.
     §3 tests/performance/run_perf.js يخرج بالرمز 2 لا 0 حين يعجز عن القياس،
        ويكتب مخرَجاً يقول صراحةً إنه لم يقس شيئاً.
     §4 برهان اللاعقامة موجود بأرقام حقيقية: المِرقاب قاس صفحة WebGL2 صغيرة
        وأنتج FPS ومئينات زمن إطار وقراءة كومة، وتغيّرت مع الحمل.
   ========================================================================== */
const fs = require('fs'), _np = require('path');
const { spawnSync } = require('child_process');
const HERE = __dirname, ROOT = _np.resolve(HERE, '..', '..');
const PERFDIR = _np.join(ROOT, 'tests', 'performance');
let pass = 0, fail = 0;
const chk = (n, c, d) => { c ? (pass++, console.log('  ✓', n))
  : (fail++, console.log('  ✗', n, d === undefined ? '' : String(d).slice(0, 240))); };
const readJSON = p => JSON.parse(fs.readFileSync(p, 'utf8'));

/* ══════════════════════════════════════════════════════ §1 — الميزانيات ══ */
console.log('\n== §1 — THE BUDGETS ARE DECLARED, AND DECLARED AS TARGETS ==');
const BPATH = _np.join(PERFDIR, 'budgets.json');
chk('tests/performance/budgets.json exists', fs.existsSync(BPATH));
let B = null;
try { B = readJSON(BPATH); chk('it parses as JSON', true); }
catch (e) { chk('it parses as JSON', false, e.message); }
if (B) {
  chk('it declares a schema', typeof B.schema === 'string' && /budgets/.test(B.schema));
  chk('its status says the budgets are TARGETS ONLY and NOT MEASURED',
      /TARGET/i.test(B.status) && /NOT MEASURED/i.test(B.status), B.status);
  chk('measured === false at the top level', B.measured === false);
  chk('it explains in words that a budget with no measurement is a promise, '
      + 'not a result', /promise, not a result/i.test(B.measured_note || ''));
  chk('it states NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
      (B.not_verified || {}).statement
      === 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  chk('it names the real reason (empty public/vendor, no network)',
      /vendor/i.test((B.not_verified || {}).reason || '')
      && /network/i.test((B.not_verified || {}).reason || ''));
  const all = [];
  Object.keys(B.budgets || {}).forEach(g =>
    (B.budgets[g] || []).forEach(x => all.push([g, x])));
  chk('at least 12 individual budgets are declared', all.length >= 12,
      String(all.length));
  chk('every budget has an id, a metric, an operator, a numeric target and a '
      + 'unit',
      all.every(([, x]) => x.id && x.metric && x.operator
        && typeof x.target === 'number' && x.unit),
      JSON.stringify(all.filter(([, x]) => !(x.id && x.metric && x.operator
        && typeof x.target === 'number' && x.unit)).map(([, x]) => x.id)));
  chk('EVERY budget is individually flagged measured:false — not one is '
      + 'presented as an achieved number',
      all.every(([, x]) => x.measured === false),
      JSON.stringify(all.filter(([, x]) => x.measured !== false)
        .map(([, x]) => x.id)));
  chk('every operator is a real comparison', all.every(([, x]) =>
    ['<=', '>=', '<', '>', '=='].indexOf(x.operator) >= 0));
  const byId = {};
  all.forEach(([, x]) => { byId[x.id] = x; });
  chk('the required desktop budget exists: >= 45 fps on a MEDIUM fixture',
      !!byId.FPS_DESKTOP_MEDIUM
      && byId.FPS_DESKTOP_MEDIUM.device_class === 'DESKTOP'
      && byId.FPS_DESKTOP_MEDIUM.fixture_class === 'MEDIUM'
      && byId.FPS_DESKTOP_MEDIUM.metric === 'fps_average'
      && byId.FPS_DESKTOP_MEDIUM.operator === '>='
      && byId.FPS_DESKTOP_MEDIUM.target === 45,
      JSON.stringify(byId.FPS_DESKTOP_MEDIUM));
  chk('the required mid-range mobile navigation budget exists: >= 24 fps',
      !!byId.FPS_MOBILE_NAVIGATION
      && byId.FPS_MOBILE_NAVIGATION.device_class === 'MID_RANGE_MOBILE'
      && byId.FPS_MOBILE_NAVIGATION.operator === '>='
      && byId.FPS_MOBILE_NAVIGATION.target === 24
      && /navigation/i.test(byId.FPS_MOBILE_NAVIGATION.scenario || ''),
      JSON.stringify(byId.FPS_MOBILE_NAVIGATION));
  ['FRAME_TIME_P95_DESKTOP_MEDIUM', 'FRAME_TIME_P95_MOBILE',
   'FIRST_VISIBLE_FRAME_MEDIUM', 'MODEL_BUILD_MEDIUM', 'THREE_INIT_DESKTOP',
   'JS_PARSE_INIT_DESKTOP', 'FIRST_CONTENT_LOAD_DESKTOP', 'DRAW_CALLS_MEDIUM',
   'TRIANGLES_MEDIUM', 'WEBGL_CONTEXT_COUNT', 'CONTEXT_LOSS_EVENTS',
   'RENDER_LOOP_COUNT', 'DUPLICATE_EVENT_LISTENERS',
   'GEOMETRIES_RETURN_TO_BASELINE', 'TEXTURES_RETURN_TO_BASELINE',
   'HEAP_AFTER_20_PROJECT_SWITCHES'].forEach(id =>
    chk('budget ' + id + ' is declared', !!byId[id]));
  chk('a p95 frame-time budget accompanies each fps budget, so an average '
      + 'cannot be reached by alternating fast and stalled frames',
      !!byId.FRAME_TIME_P95_DESKTOP_MEDIUM && !!byId.FRAME_TIME_P95_MOBILE);
  chk('context loss is budgeted at exactly zero',
      byId.CONTEXT_LOSS_EVENTS.target === 0
      && byId.CONTEXT_LOSS_EVENTS.operator === '<=');
  chk('the fixture classes name the required fixtures',
      JSON.stringify(B.fixture_classes).indexOf('warehouse') >= 0
      && JSON.stringify(B.fixture_classes).indexOf('spaces_1000') >= 0
      && JSON.stringify(B.fixture_classes).indexOf('villa') >= 0);
  chk('every budget offers a justification or is a self-evident zero',
      all.every(([, x]) => !!x.justification || x.target === 0
        || !!x.scenario),
      JSON.stringify(all.filter(([, x]) => !x.justification && x.target !== 0
        && !x.scenario).map(([, x]) => x.id)));
}

/* ═══════════════════════════════════════════════════ §2 — حاكم الجودة ═══ */
console.log('\n== §2 — THE QUALITY GOVERNOR CAN NEVER DROP SEMANTIC GEOMETRY ==');
const GPATH = _np.join(PERFDIR, 'quality_governor.json');
chk('tests/performance/quality_governor.json exists', fs.existsSync(GPATH));
let G = null;
try { G = readJSON(GPATH); chk('it parses as JSON', true); }
catch (e) { chk('it parses as JSON', false, e.message); }

/* عقد التحقّق مكتوب داخل الملفّ. نُنفّذه هنا حرفياً — فالفحص ليس رأياً، بل
   تطبيق للقاعدة التي أعلنها الملفّ عن نفسه. */
function validateGovernor(spec) {
  const bad = [];
  const C = spec.validation_contract || {};
  const inv = spec.invariants || {};
  if (inv.never_removes_semantic_geometry !== true)
    bad.push('invariant never_removes_semantic_geometry is not true');
  if (inv.writes_to_model !== false) bad.push('invariant writes_to_model is not false');
  if (inv.changes_model_hash !== false) bad.push('invariant changes_model_hash is not false');
  if (inv.changes_element_count !== false)
    bad.push('invariant changes_element_count is not false');
  const prefixes = C.parameter_key_allowlist_prefixes || [];
  const forbidden = C.parameter_key_forbidden_substrings || [];
  const tiers = spec.tiers || {};
  if (!Object.keys(tiers).length) bad.push('no tier is declared');
  Object.keys(tiers).forEach(name => {
    const t = tiers[name];
    (C.every_tier_must_declare || []).forEach(k => {
      if (!(k in t)) bad.push(name + ': missing required key ' + k);
    });
    Object.keys(C.every_tier_must_have || {}).forEach(k => {
      if (t[k] !== C.every_tier_must_have[k])
        bad.push(name + ': ' + k + ' must be '
          + JSON.stringify(C.every_tier_must_have[k]));
    });
    Object.keys(t.parameters || {}).forEach(p => {
      const lower = p.toLowerCase();
      const hit = forbidden.filter(sub => lower.indexOf(sub) >= 0
        && lower.indexOf('decorative_context') !== 0);
      if (hit.length) bad.push(name + ': parameter `' + p
        + '` uses forbidden vocabulary ' + JSON.stringify(hit));
      if (!prefixes.some(pre => p.indexOf(pre) === 0))
        bad.push(name + ': parameter `' + p + '` is outside the allowlist');
    });
    /* أي مفتاح على مستوى المستوى نفسه يوحي بحذف — مرفوض */
    Object.keys(t).forEach(k => {
      if (k === 'removes_semantic_geometry') return;
      if (/(^|_)(remove|drop|cull|omit|decimate|prune|skip|hide)/i.test(k))
        bad.push(name + ': tier-level key `' + k + '` implies removal');
    });
  });
  /* لا فعل محظور مذكور كقدرة مسموحة */
  const allowed = JSON.stringify(inv.allowed_action_domains || []);
  (inv.forbidden_actions_at_every_tier || []).forEach(a => {
    if (allowed.indexOf(a) >= 0)
      bad.push('forbidden action ' + a + ' also appears as an allowed domain');
  });
  return bad;
}

if (G) {
  chk('the governor declares itself a specification, not an implementation',
      G.implemented === false && /NOT IMPLEMENTED/i.test(G.status), G.status);
  chk('it states plainly that it is not wired into public/index.html',
      /index\.html/.test(G.implementation_note || ''));
  chk('a MID_RANGE_MOBILE tier exists', !!(G.tiers || {}).MID_RANGE_MOBILE);
  const M = ((G.tiers || {}).MID_RANGE_MOBILE || {}).parameters || {};
  const F = ((G.tiers || {}).FULL || {}).parameters || {};
  chk('MID_RANGE_MOBILE declares an exact reduced shadow resolution',
      typeof M.shadow_map_size === 'number' && M.shadow_map_size < F.shadow_map_size,
      'full=' + F.shadow_map_size + ' mobile=' + M.shadow_map_size);
  chk('MID_RANGE_MOBILE declares an exact reduced SSAO quality',
      typeof M.ssao_kernel_samples === 'number'
      && M.ssao_kernel_samples < F.ssao_kernel_samples
      && M.ssao_render_scale < F.ssao_render_scale,
      'samples ' + F.ssao_kernel_samples + '→' + M.ssao_kernel_samples
      + ', scale ' + F.ssao_render_scale + '→' + M.ssao_render_scale);
  chk('MID_RANGE_MOBILE declares an exact lower device-pixel-ratio cap',
      typeof M.device_pixel_ratio_cap === 'number'
      && M.device_pixel_ratio_cap < F.device_pixel_ratio_cap,
      F.device_pixel_ratio_cap + ' → ' + M.device_pixel_ratio_cap);
  chk('MID_RANGE_MOBILE declares an exact reduced context LOD',
      typeof M.decorative_context_lod === 'number'
      && M.decorative_context_lod < F.decorative_context_lod,
      F.decorative_context_lod + ' → ' + M.decorative_context_lod);
  chk('every mobile parameter delta is written down with its reasoning',
      Object.keys(((G.tiers || {}).MID_RANGE_MOBILE || {})
        .parameter_deltas_from_FULL || {}).length >= 10);
  chk('the reduced context LOD is explicitly scoped to DECORATIVE, '
      + 'non-canonical dressing only — never to model geometry',
      /visual_only/.test(JSON.stringify(G.decorative_context_lod || {}))
      && /source_element_id/.test(JSON.stringify(G.decorative_context_lod || {}))
      && /decorative/i.test(G.invariants.decorative_context_is_not_semantic || ''));
  chk('the invariant is stated in words a reviewer can hold the code to',
      /NO QUALITY TIER MAY EVER REMOVE/.test(G.invariants.statement || ''));
  chk('the protected element classes cover the load-bearing and life-safety '
      + 'elements',
      ['wall', 'slab', 'column', 'beam', 'door', 'window', 'stair',
       'sprinkler', 'egress_path'].every(
        c => (G.invariants.protected_element_classes || []).indexOf(c) >= 0));
  chk('every tier declares removes_semantic_geometry:false',
      Object.keys(G.tiers).every(k => G.tiers[k].removes_semantic_geometry === false),
      JSON.stringify(Object.keys(G.tiers).map(
        k => [k, G.tiers[k].removes_semantic_geometry])));
  chk('every tier declares writes_to_model:false',
      Object.keys(G.tiers).every(k => G.tiers[k].writes_to_model === false));
  const v = validateGovernor(G);
  chk('THE SPEC PASSES ITS OWN VALIDATION CONTRACT — no tier permits dropping '
      + 'semantic geometry', v.length === 0, JSON.stringify(v));
  chk('even the MINIMUM_SAFE last-resort tier removes no geometry',
      (G.tiers.MINIMUM_SAFE || {}).removes_semantic_geometry === false
      && /every wall, slab, opening and fixture is still drawn/i
        .test(G.tiers.MINIMUM_SAFE.note || ''));
  chk('tier switching declares hysteresis, so the governor cannot oscillate',
      typeof ((G.tier_detection || {}).measured_frame_time || {})
        .min_seconds_between_tier_changes === 'number');
  chk('the governor states that no tier was measured here',
      /NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED/
        .test((G.not_measured || {}).statement || ''));

  console.log('\n  -- the validator is not vacuous: hostile specs must fail --');
  const clone = () => JSON.parse(JSON.stringify(G));
  [['a tier that admits it removes semantic geometry',
    s => { s.tiers.MID_RANGE_MOBILE.removes_semantic_geometry = true; }],
   ['a tier that writes to the model',
    s => { s.tiers.MID_RANGE_MOBILE.writes_to_model = true; }],
   ['a parameter that culls walls',
    s => { s.tiers.MID_RANGE_MOBILE.parameters.wall_cull_distance_m = 40; }],
   ['a parameter that drops rooms',
    s => { s.tiers.MID_RANGE_MOBILE.parameters.drop_rooms_beyond = 50; }],
   ['a parameter that decimates geometry',
    s => { s.tiers.MID_RANGE_MOBILE.parameters.geometry_decimate_ratio = 0.5; }],
   ['a parameter that hides MEP',
    s => { s.tiers.MINIMUM_SAFE.parameters.hide_mep = true; }],
   ['a parameter that skips element classes',
    s => { s.tiers.MINIMUM_SAFE.parameters.skip_element_classes = ['door']; }],
   ['an innocuous-looking parameter outside the allowlist',
    s => { s.tiers.FULL.parameters.max_visible_rooms = 200; }],
   ['a weakened top-level invariant',
    s => { s.invariants.never_removes_semantic_geometry = false; }],
   ['a governor that may change the model hash',
    s => { s.invariants.changes_model_hash = true; }],
   ['a tier-level removal switch',
    s => { s.tiers.MINIMUM_SAFE.drop_decorative_and_semantic = true; }]
  ].forEach(([label, mutate]) => {
    const s = clone(); mutate(s);
    const r = validateGovernor(s);
    chk('the validator rejects ' + label, r.length > 0, JSON.stringify(r));
  });
}

/* ════════════════════════════════ §3 — المِرقاب يخرج بـ2 حين يعجز ═══════ */
console.log('\n== §3 — THE HARNESS EXITS 2, NOT 0, WHEN IT CANNOT MEASURE ==');
const RUNPERF = _np.join(PERFDIR, 'run_perf.js');
chk('tests/performance/run_perf.js exists', fs.existsSync(RUNPERF));
const SRC = fs.existsSync(RUNPERF) ? fs.readFileSync(RUNPERF, 'utf8') : '';
chk('it declares NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED in the source',
    SRC.indexOf('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED') >= 0);
chk('it can never exit 0 on the not-verified path (process.exit(2) is the '
    + 'only exit in notVerified)',
    /function notVerified[\s\S]*?process\.exit\(2\);\s*\n\}/.test(SRC));
[['first content load', 'first_content_load_ms'],
 ['JS parse/init', 'js_parse_init_ms'],
 ['Three init', 'three_init_ms'],
 ['model build', 'model_build_ms'],
 ['first visible frame', 'first_visible_frame_ms'],
 ['FPS average', 'fps_average'],
 ['frame-time p5', 'frame_time_p5_ms'],
 ['frame-time p95', 'frame_time_p95_ms'],
 ['draw calls', 'draw_calls'],
 ['triangles', 'triangles'],
 ['JS heap', 'performance.memory'],
 ['memory after repeated loads', 'js_heap_after_repeated_loads'],
 ['memory after dispose', 'js_heap_after_dispose'],
 ['WebGL context count', 'webgl_context_count'],
 ['context loss events', 'context_lost'],
 ['geometry disposal via renderer.info.memory', 'geometries'],
 ['texture disposal', 'textures'],
 ['duplicate render loops', 'render_loop_count'],
 ['duplicate event listeners', 'duplicate_event_listener_count']
].forEach(([label, token]) =>
  chk('the harness implements a measurement for ' + label,
      SRC.indexOf(token) >= 0));
['SWITCH_20_PROJECTS', 'PBR_ENTER_EXIT', 'CONTEXT_LANDSCAPE_TOGGLE',
 'SCREENSHOT_CREATE_DISPOSE', 'VR_ENTER_EXIT'].forEach(id =>
  chk('leak scenario ' + id + ' is implemented', SRC.indexOf(id) >= 0));
['villa', 'apartment', 'hotel', 'clinic', 'warehouse', 'spaces_100',
 'spaces_500', 'spaces_1000', 'live_large_generated'].forEach(fx =>
  chk('fixture ' + fx + ' is present in the harness', SRC.indexOf(fx) >= 0));
chk('the real fixtures are read from the repository, not re-typed',
    SRC.indexOf('tests/phase3/fixtures/base_fixtures.json') >= 0
    || SRC.indexOf("'base_fixtures.json'") >= 0);

console.log('  (running the harness for real — this takes ~30 s)');
const run = spawnSync(process.execPath, [RUNPERF], { cwd: ROOT,
  encoding: 'utf8', timeout: 420000, maxBuffer: 1 << 26 });
const out = String(run.stdout || '') + String(run.stderr || '');
chk('the harness exits 2 (NOT VERIFIED), not 0 (pass) and not 1 (crash)',
    run.status === 2, 'exit=' + run.status + ' :: ' + out.slice(-300));
chk('it prints NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
    out.indexOf('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED') >= 0);
chk('it says in words that exit 2 must not be counted as a pass',
    /must never be counted as one|not a pass/i.test(out));
const PERFOUT = _np.join(PERFDIR, 'outputs', 'perf.json');
chk('it wrote tests/performance/outputs/perf.json', fs.existsSync(PERFOUT));
let P = null;
if (fs.existsSync(PERFOUT)) {
  P = readJSON(PERFOUT);
  chk('the output records that nothing about the application was measured',
      P.measured === false && P.application_measured === false
      && P.status === 'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED',
      JSON.stringify({ m: P.measured, a: P.application_measured, s: P.status }));
  chk('the output records exit_code 2', P.exit_code === 2);
  chk('the reason names the empty public/vendor and the absent network',
      /vendor/i.test(P.reason) && /network/i.test(P.reason), P.reason);
  chk('the output contains no fps/frame-time number attributed to the '
      + 'application',
      !P.application && (P.fixtures_that_would_be_measured || [])
        .every(f => f.measured === false));
  chk('the fixture matrix is listed with provenance so nothing is silently '
      + 'invented',
      (P.fixtures_that_would_be_measured || []).length >= 9
      && P.fixtures_that_would_be_measured.every(f => !!f.provenance),
      String((P.fixtures_that_would_be_measured || []).length));
  chk('every synthetic fixture declares that it was generated, not real',
      P.fixtures_that_would_be_measured
        .filter(f => /spaces_|apartment/.test(f.name))
        .every(f => /generated|synthetic/i.test(f.provenance)));
  chk('the leak scenarios are listed and all marked unmeasured',
      (P.leak_scenarios_that_would_be_run || []).length === 5
      && P.leak_scenarios_that_would_be_run.every(s => s.measured === false));
  chk('the budgets are referenced by file, and their TARGET status is carried '
      + 'into the output',
      P.budgets_source === 'tests/performance/budgets.json'
      && /TARGET/i.test(P.budgets_status || ''));
}

/* ═══════════════════════════════ §4 — برهان اللاعقامة بأرقام حقيقية ═════ */
console.log('\n== §4 — THE VACUITY PROOF: THE HARNESS DID MEASURE SOMETHING ==');
const VPAGE = _np.join(PERFDIR, 'vacuity_page.html');
chk('a minimal WebGL page exists and is written here, not borrowed',
    fs.existsSync(VPAGE));
if (fs.existsSync(VPAGE)) {
  const V = fs.readFileSync(VPAGE, 'utf8');
  chk("it uses a plain canvas + getContext('webgl2')",
      /getContext\('webgl2'/.test(V) && /<canvas/.test(V));
  chk('it runs a requestAnimationFrame loop', /requestAnimationFrame/.test(V));
  chk('it contains no Three.js and no framework at all',
      V.indexOf('three') < 0 && V.indexOf('THREE') < 0
      && V.indexOf('import ') < 0);
}
const VP = P && P.vacuity_proof;
chk('the harness output carries a vacuity proof', !!VP);
if (VP) {
  chk('the proof succeeded', VP.proved === true, VP.reason || '');
  chk('it was served from 127.0.0.1 (loopback is not proxied)',
      /127\.0\.0\.1/.test(VP.url_scheme || ''));
  chk('it states that the measurement code is identical to the application '
      + 'path — otherwise the proof would prove a different program',
      /IDENTICAL/.test(VP.measurement_code || ''));
  const L = (VP.light_load || {}).frames || {}, H = (VP.heavy_load || {}).frames || {};
  chk('real FPS numbers exist for the light load',
      L.measured === true && typeof L.fps_average === 'number'
      && L.fps_average > 0 && L.frames > 10,
      JSON.stringify({ fps: L.fps_average, frames: L.frames }));
  chk('real frame-time percentiles exist (p5 / p50 / p95)',
      typeof L.frame_time_p5_ms === 'number'
      && typeof L.frame_time_p50_ms === 'number'
      && typeof L.frame_time_p95_ms === 'number'
      && L.frame_time_p5_ms <= L.frame_time_p50_ms
      && L.frame_time_p50_ms <= L.frame_time_p95_ms,
      JSON.stringify([L.frame_time_p5_ms, L.frame_time_p50_ms,
        L.frame_time_p95_ms]));
  chk('a real JS heap reading exists',
      !!VP.heap_before_alloc
      && typeof VP.heap_before_alloc.used_js_heap_bytes === 'number'
      && VP.heap_before_alloc.used_js_heap_bytes > 0,
      JSON.stringify(VP.heap_before_alloc));
  chk('the FPS number FELL when the GPU load was raised — a printed constant '
      + 'could not do that',
      VP.sensitivity_checks.fps_falls_when_the_gpu_load_rises === true
      && H.fps_average < L.fps_average,
      'light=' + L.fps_average + ' heavy=' + H.fps_average);
  chk('the heap number ROSE by roughly the 64 MiB that was allocated',
      VP.sensitivity_checks.heap_rises_when_memory_is_allocated === true
      && VP.heap_delta_bytes > 50 * 1024 * 1024,
      'delta=' + VP.heap_delta_bytes + ' B');
  chk('draw calls were really counted and rose with the load',
      VP.heavy_load.gpu.draw_calls > VP.light_load.gpu.draw_calls,
      VP.light_load.gpu.draw_calls + ' → ' + VP.heavy_load.gpu.draw_calls);
  chk('exactly one WebGL context and one render loop were detected in a page '
      + 'that has exactly one of each',
      VP.counters.webgl_context_count === 1 && VP.counters.render_loop_count === 1,
      JSON.stringify({ ctx: VP.counters.webgl_context_count,
        loops: VP.counters.render_loop_count }));
  chk("the harness excluded its own sampling loop from the count, so it does "
      + 'not report a leak it caused itself',
      VP.counters.harness_own_sampling_loops_excluded >= 1,
      String(VP.counters.harness_own_sampling_loops_excluded));
  chk('no context was lost during the proof',
      VP.counters.context_lost_events === 0);
  chk('the proof says explicitly what it does NOT prove',
      /Nothing at all about the ACS application/i
        .test(VP.what_this_does_not_prove || ''));
  console.log('\n  MEASURED (vacuity page, real numbers):');
  console.log('    light : ' + L.fps_average + ' fps · p5 ' + L.frame_time_p5_ms
    + ' ms · p50 ' + L.frame_time_p50_ms + ' ms · p95 ' + L.frame_time_p95_ms
    + ' ms · ' + L.frames + ' frames');
  console.log('    heavy : ' + H.fps_average + ' fps · p5 ' + H.frame_time_p5_ms
    + ' ms · p50 ' + H.frame_time_p50_ms + ' ms · p95 ' + H.frame_time_p95_ms
    + ' ms · ' + H.frames + ' frames');
  console.log('    heap  : ' + VP.heap_before_alloc.used_js_heap_bytes + ' B → '
    + VP.heap_after_alloc_64mb.used_js_heap_bytes + ' B (delta '
    + VP.heap_delta_bytes + ' B)');
}

/* ═════════════════════════════ §5 — شكل ما يُشحن فعلاً (F-09) ═══════════ */
/* الرقم الوحيد المتعلّق بالأداء الذي يمكن قياسه هنا بلا متصفّح هو ما يصل إلى
   المستخدم أوّل مرّة. قبل F-09 كانت الصفحة 1,863,894 بايت لا يُخزَّن منها شيء
   بين نشرين لأن كل شيء داخلها. الآن قشرة صغيرة + ملفّات قابلة للتخزين. هذا
   قياس حقيقي على الشجرة، لا هدف معلَن — ويُميَّز عن الميزانيات صراحةً. */
console.log('\n== §5 — WHAT THE FIRST REQUEST ACTUALLY COSTS (MEASURED HERE) ==');
const AS = require(_np.join(ROOT, 'tests', 'lib', 'app_source.js'));
const SHELL_BYTES = Buffer.byteLength(AS.shell(), 'utf8');
const MODS = AS.modules();
const MOD_BYTES = Object.keys(MODS)
  .reduce((n, k) => n + Buffer.byteLength(MODS[k], 'utf8'), 0);
const CSS_BYTES = fs.existsSync(_np.join(ROOT, 'public', 'app', 'styles',
  'app.css')) ? fs.statSync(_np.join(ROOT, 'public', 'app', 'styles',
  'app.css')).size : 0;
const PRE_SPLIT_PAGE_BYTES = 1863894;   /* المقيس على HEAD السابق للتفكيك */
console.log('  MEASURED: shell=' + SHELL_BYTES + ' B · modules='
  + Object.keys(MODS).length + ' file(s)/' + MOD_BYTES + ' B · css='
  + CSS_BYTES + ' B · pre-split single page=' + PRE_SPLIT_PAGE_BYTES + ' B');
chk('the shipped page is a SHELL: it is under 200 KB, and under a tenth of the '
    + 'single file it replaced',
    SHELL_BYTES < 200000 && SHELL_BYTES * 10 < PRE_SPLIT_PAGE_BYTES,
    String(SHELL_BYTES));
chk('the application itself did not shrink — it moved: the modules carry at '
    + 'least as much code as the old page did',
    MOD_BYTES + CSS_BYTES + SHELL_BYTES >= PRE_SPLIT_PAGE_BYTES * 0.9,
    String(MOD_BYTES + CSS_BYTES + SHELL_BYTES));
chk('the code is split into separately cacheable files, not one bundle',
    Object.keys(MODS).length >= 15, String(Object.keys(MODS).length));
chk('the styles left the page too — an external stylesheet is cacheable, a '
    + '<style> block is not', CSS_BYTES > 1000 && !/<style[\s>]/.test(AS.shell()),
    String(CSS_BYTES));
chk('no module is empty — an empty file is a shipped request that buys nothing',
    Object.keys(MODS).every(k => MODS[k].length > 0),
    Object.keys(MODS).filter(k => !MODS[k].length).join(', '));

console.log('\n  NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: no ACS frame was '
  + 'rendered and no application performance number exists. F-14 budgets are '
  + 'TARGETS; the quality governor is a SPECIFICATION and is NOT implemented '
  + 'in the shipped frontend (public/index.html + public/app/). The §5 numbers '
  + 'above are measured bytes on this tree, not a rendering measurement, and '
  + 'transfer size after compression is NOT VERIFIED here.');
console.log('\n──────────────────────────────────────────────');
console.log('PERFORMANCE CONTRACT: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
