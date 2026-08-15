/* ============================================================================
   KI-25 · F-41…F-45 — رد 200 صالح لا يُعرَض.
     node tests/lib/run.js tests/remediation/test_model_apply.js

   العطل الإنتاجي
   --------------
     POST /v1/understand → 200 OK
     ok:true · building صالح · site 22×16 · levels L0/L1/L2 · مستودع كامل
     acs_plan_report: strategy=staged · chunks_executed=10 · failed_chunks=[]
     والنافذة لا تعرض شيئاً. لا خطأ في الكونسول ولا لوحة عطل.

   السبب: العقد المُعلَن في acs_understand.py يقول
       "levels": [ {"index": int, "name": str, "template": str} ]
   والعارض يبني عليه حرفياً: ‎baseY = index × floor_height‎ و‎fkey = 'F'+index‎.
   حين ضاق توجيه البيان في KI-24 صار يطلب ‎{"id","template","elevation"}‎ بلا
   `index`، و‎merge_plan‎ يمرّر غلاف البيان كما هو. فصار كل مبنى كبير يعود من
   الخادم بمستويات بلا index: ‎undefined × 4 = NaN‎ لكل دور، و‎'Fundefined'‎
   مفتاحاً واحداً للأدوار كلّها.

   ولماذا لم يظهر خطأ: لأن **لا أحد يرمي**. عقد الحدود المتين (KI-3) يستبعد
   الشبكات التالفة بحقّ، والعدّاد يعدّها، فتُكتب «تم التوليد ✓ 2001 عنصر» فوق
   نافذة فارغة. نجاحٌ مُعلَن على لا شيء — وهو أخطر من استثناء.

   نطاق هذا الملفّ — مُعلَن بدقّة
   -----------------------------
   يُشغَّل ‎compile()‎ المشحون نفسه على بديل هندسة معلَن (نفس نمط
   tests/phase3/mesh_invariance_dump.js): البديل يسجّل الصناديق ولا يرسمها،
   فالمقيس هنا **الهندسة المنبعثة** لا البكسلات. وحاجزُ التطبيق يُقاس بمنطقه
   الحقيقي المنتزَع من الوحدة المشحونة، على setModel وverifyVisibleModel
   قابلين للإبدال — فيُقاس تصنيفه لا رسمه.

   البكسلات والكاميرا في عتاد حقيقي: tests/remediation/test_apply_render_browser.js
   ========================================================================== */
'use strict';

let pass = 0, fail = 0;
const chk = (name, cond, detail) => {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + '  ' + (detail === undefined ? '' : detail)); }
};

/* ═══════════ بديل الهندسة: يسجّل ولا يرسم ═══════════════════════════════ */
const boxes = [];
globalThis.THREE = {
  Group: function () { this.children = []; this.name = ''; this.userData = {};
    this.add = function (o) { this.children.push(o); };
    this.traverse = function (f) { f(this); this.children.forEach(c => f(c)); }; },
  BoxGeometry: function (x, y, z) { this.p = [x, y, z]; },
  Mesh: function (g, m) { this.g = g; this.m = m; this.name = ''; this.isMesh = true;
    this.castShadow = false; this.receiveShadow = false; this.rotation = { y: 0 };
    this.visible = true; this.userData = {};
    this.position = { x: 0, y: 0, z: 0,
      set: (a, b, c) => { this.position.x = a; this.position.y = b; this.position.z = c; } };
    boxes.push(this); }
};
getMat = () => ({ userData: {} });
scaleBoxUV = () => {};
if (typeof getMat('x').userData !== 'object' || getMat('x').map !== undefined)
  throw new Error('the material stub did not take effect — a real material needs a '
    + 'WebGL context and would make this a pixel claim, not a geometry one');

/* ═══════════ نموذج بشكل الإنتاج ═══════════════════════════════════════════
   22×16، ثلاثة مستويات، مستودع بأرفف وممرّات ونقاط وأثاث — نفس أشكال الرد
   الذي وصف بلاغ الإنتاج. `withIndex=false` يعيد ما كان الخادم يُعيده فعلاً. */
function prodModel(withIndex, nZonesPerLevel) {
  const per = nZonesPerLevel === undefined ? 18 : nZonesPerLevel;
  const tmpl = ['t0', 't1', 't2'];
  const levels = tmpl.map((t, i) => {
    const l = { id: 'L' + i, template: t, elevation: +(i * 4.0).toFixed(3) };
    if (withIndex) { l.index = i; l.name = 'المستوى ' + i; }
    return l;
  });
  const floors = {};
  tmpl.forEach((t, ti) => {
    const rooms = [];
    for (let k = 0; k < per; k++) {
      const col = k % 6, row = (k / 6) | 0;
      rooms.push({ id: 'zone_' + String(ti * per + k).padStart(3, '0'),
        rect: [0.5 + col * 3.5, 0.5 + row * 5.0, 3.0, 4.5],
        role: 'storage', walls: 'none',
        racks: [{ kind: 'pallet', x: 0.3, z: 0.3, w: 2.4, d: 3.9, dir: 'x',
                  aisle: 1.2, levels: 4, h: 3.0 }],
        lanes: [{ x: 0.1, z: 0.1, w: 2.8, d: 0.8, dir: 'x' }],
        points: [{ type: 'light', x: 1.5, z: 2.2 }],
        furniture: [{ kind: 'desk', x: 0.5, z: 0.5, w: 1.2, d: 0.6 }] });
    }
    floors[t] = { rooms: rooms };
  });
  return { meta: { type: 'warehouse', requirements: [] },
    site: { w: 22, d: 16 }, floor_height: 4.0, wall_h: 3.6, wall_t: 0.2,
    levels: levels, floors: floors };
}
function smallModel() {
  return { meta: { type: 'residential' }, site: { w: 12, d: 10 },
    floor_height: 3.2, wall_h: 3.0, wall_t: 0.15,
    levels: [{ index: 0, name: 'الأرضي', template: 'g' }],
    floors: { g: { rooms: [
      { id: 'majlis', rect: [0.5, 0.5, 5, 4], role: 'majlis',
        doors: [{ edge: 'N', offset: 2.5, width: 0.9, height: 2.1 }],
        points: [{ type: 'light', x: 2.5, z: 2 }] },
      { id: 'kitchen', rect: [6, 0.5, 4, 4], role: 'kitchen' }] } } };
}
function mediumModel() {
  const m = prodModel(true, 8); m.site = { w: 30, d: 25 }; return m;
}

/* أوصاف على شكل _pqDescribeBoxed تماماً، ليُقاس عقد الحدود المشحون نفسه. */
function descriptors() {
  return boxes.map(b => {
    const p = b.position, g = b.g ? b.g.p : [0, 0, 0];
    return { name: b.name, is_mesh: true, visible: b.visible,
      parent_names: ['BUILDING'], user_data: b.userData || {},
      box: { min: [p.x - g[0] / 2, p.y - g[1] / 2, p.z - g[2] / 2],
             max: [p.x + g[0] / 2, p.y + g[1] / 2, p.z + g[2] / 2] } };
  });
}
function build(model) {
  boxes.length = 0;
  let err = null, grp = null;
  try { grp = compile(model); } catch (e) { err = e; }
  const rb = err ? null : pqRobustBounds(descriptors());
  return { err: err, group: grp, meshes: boxes.length, bounds: rb,
    defects: acsBuildDefects(),
    kept: rb ? (rb.diagnostics || {}).included_in_bounds : 0,
    dropped: rb ? (rb.diagnostics || {}).excluded_invalid_bounds : 0,
    floorKeys: [...new Set(boxes.map(b => String(b.name).split('|')[1]))] };
}

function main() {

// ═══════════════ أ · إعادة إنتاج العطل الإنتاجي ═════════════════════════════
console.log('\n== أ · إعادة إنتاج: مستوىً بلا index يبني عند NaN ==');
/* الإثبات لا يعتمد على الإصلاح: يُحسب هنا ما كان السطر القديم يحسبه بالضبط. */
const _fh = 4.0, _legacyBaseY = (undefined) * _fh, _legacyKey = 'F' + (undefined);
chk('الحساب القديم ‎lvl.index*fh‎ يعطي NaN لمستوى بلا index',
    Number.isNaN(_legacyBaseY), String(_legacyBaseY));
chk('ومفتاح الدور يصير ‎Fundefined‎ لكل الأدوار', _legacyKey === 'Fundefined', _legacyKey);
chk('وحارس addBox القديم ‎ex<=0‎ لا يوقف NaN ولا undefined',
    !(NaN <= 0) && !(undefined <= 0));

const A = build(prodModel(true));
const B = build(prodModel(false));
chk('لا استثناء في الحالتين — ولذلك لم يظهر خطأ في الإنتاج',
    A.err === null && B.err === null,
    String((A.err || B.err || '').message || ''));
chk('العدّاد نفسه في الحالتين — ولذلك بدت الرسالة صادقة',
    A.meshes === B.meshes && A.meshes > 1000, A.meshes + ' / ' + B.meshes);
console.log('     with index: ' + A.meshes + ' شبكة · وصل الحدود ' + A.kept
            + ' · سقط ' + A.dropped + ' · أدوار ' + JSON.stringify(A.floorKeys));
console.log('     no index  : ' + B.meshes + ' شبكة · وصل الحدود ' + B.kept
            + ' · سقط ' + B.dropped + ' · أدوار ' + JSON.stringify(B.floorKeys));

// ═══════════════ ب · الإصلاح: العارض لا يثق بحقل غائب ═══════════════════════
console.log('\n== ب · F-42: رقم الدور مشتقّ لا مُفترَض ==');
chk('لا شبكة واحدة بإحداثيّة غير منتهية', B.defects.non_finite_box === 0,
    String(B.defects.non_finite_box));
chk('والأدوار الثلاثة منفصلة لا مدموجة في Fundefined',
    B.floorKeys.indexOf('F0') >= 0 && B.floorKeys.indexOf('F1') >= 0
    && B.floorKeys.indexOf('F2') >= 0 && B.floorKeys.indexOf('Fundefined') < 0,
    JSON.stringify(B.floorKeys));
chk('والهندسة كلّها تصل الحدود كما لو صرّح البيان بالأرقام',
    B.kept === A.kept && B.dropped === 0, B.kept + ' / ' + A.kept);
chk('ونصف قطر المشهد واحد في الحالتين — النموذج نفسه لا نموذجان',
    Math.abs((A.bounds.bounds || {}).radius - (B.bounds.bounds || {}).radius) < 1e-9,
    (A.bounds.bounds || {}).radius + ' / ' + (B.bounds.bounds || {}).radius);
chk('والاشتقاق مُحصى لا صامت', B.defects.derived_level_index === 3,
    String(B.defects.derived_level_index));
chk('ولا يُحصى شيء حين يصرّح البيان بالأرقام',
    A.defects.derived_level_index === 0, String(A.defects.derived_level_index));

// ═══════════════ ج · غرفة تالفة لا تهدم مبنى ════════════════════════════════
console.log('\n== ج · F-42: مدخل تالف يُرفَض ويُحصى، ولا يرمي ==');
const badCases = [
  ['غرفة بلا rect', r => { delete r.rect; }, 'rejected_room'],
  ['rect بثلاثة عناصر', r => { r.rect = [0, 0, 3]; }, 'rejected_room'],
  ['rect كائناً لا مصفوفة', r => { r.rect = { x: 0, z: 0 }; }, 'rejected_room'],
  ['rect بقيمة نصّية', r => { r.rect = [0, 0, 'wide', 4]; }, 'rejected_room'],
  ['rect بعرض صفر', r => { r.rect = [0, 0, 0, 4]; }, 'rejected_room'],
  ['racks عدداً لا مصفوفة', r => { r.racks = 12; }, 'rejected_field'],
  ['docks كائناً لا مصفوفة', r => { r.docks = { count: 8 }; }, 'rejected_field'],
  ['points نصّاً', r => { r.points = 'كثيرة'; }, 'rejected_field']
];
badCases.forEach(([label, mutate, kind]) => {
  const m = prodModel(true);
  mutate(m.floors.t1.rooms[0]);
  const R = build(m);
  chk(('%s'.replace('%s', label) + ' → لا استثناء').padEnd(46),
      R.err === null, String((R.err || {}).message || '').slice(0, 90));
  chk(''.padEnd(46) + ' → يُحصى بسببه',
      R.err === null && R.defects[kind] > 0,
      kind + '=' + (R.err ? '-' : R.defects[kind]));
  chk(''.padEnd(46) + ' → وبقيّة المبنى تُبنى',
      R.err === null && R.meshes > A.meshes * 0.9,
      R.meshes + ' / ' + A.meshes);
});

/* حارس addBox هو آخر خطّ الدفاع وله مدخله الخاصّ: مستطيلٌ صالحٌ تماماً
   وعنصرٌ داخله بإحداثيّة غير عدديّة. لولا الحارس لدخلت شبكةٌ عند NaN إلى
   المشهد، فتُعدّ في «٢٠٠١ عنصر» ولا يرسمها العتاد — عطل KI-25 بعينه في
   مدخلٍ آخر. (‎fu.w||0.8‎ يعالج المقاس ولا يعالج الموضع.) */
console.log('\n== ج٢ · F-42: الحارس الأخير في addBox ==');
(() => {
  const m = prodModel(true);
  m.floors.t1.rooms[0].furniture = [{ kind: 'desk', x: 'قرب الباب', z: 0.5,
                                      w: 1.2, d: 0.6 }];
  const R = build(m);
  chk('إحداثيّة غير عدديّة داخل غرفة سليمة → لا استثناء', R.err === null,
      String((R.err || {}).message || ''));
  chk('ولا تدخل المشهد شبكةٌ عند NaN', R.err === null && R.dropped === 0
      && R.kept === R.meshes, R.kept + '/' + R.meshes + ' dropped=' + R.dropped);
  chk('وتُحصى بسببها', R.err === null && R.defects.non_finite_box > 0,
      String(R.defects.non_finite_box));
  chk('والعدّاد المعروض لا يعدّ ما لم يدخل',
      R.err === null && R.meshes === R.kept, R.meshes + '/' + R.kept);
})();

// ═══════════════ د · الأحجام: صغير ومتوسّط وكبير ═════════════════════════════
console.log('\n== د · SMALL · MEDIUM · LARGE تبقى خضراء ==');
[['SMALL', smallModel()], ['MEDIUM', mediumModel()], ['LARGE', prodModel(true)],
 ['LARGE بلا index', prodModel(false)]].forEach(([label, m]) => {
  const R = build(m);
  chk((label + ' → يُبنى ويصل الحدود كاملاً').padEnd(46),
      R.err === null && R.meshes > 0 && R.dropped === 0 && R.kept === R.meshes,
      'err=' + (R.err ? R.err.message : '-') + ' meshes=' + R.meshes
      + ' kept=' + R.kept + ' dropped=' + R.dropped);
});

// ═══════════════ هـ · حاجز التطبيق: التصنيف ═════════════════════════════════
console.log('\n== هـ · F-44: حاجز ما بعد 200 يُصنِّف ولا يسكت ==');
/* المنطق المُقاس هنا هو المنتزَع من الوحدة المشحونة نفسها. ما يُبدَّل هو
   setModel و verifyVisibleModel و acsBuildDefects — أي محيط الحاجز لا هو. */
globalThis.window = globalThis.window || {};
window.ACS = window.ACS || {};
let SCENE_STATE = null, SET_MODEL_BEHAVIOUR = null, DEFECTS = null;
setModel = function (b) {
  if (typeof SET_MODEL_BEHAVIOUR === 'function') return SET_MODEL_BEHAVIOUR(b);
};
acsBuildDefects = function () { return DEFECTS; };
window.ACS.verifyVisibleModel = function () { return SCENE_STATE; };

const CLEAN_DEFECTS = { non_finite_box: 0, rejected_room: 0, rejected_field: 0,
  derived_level_index: 0, unknown_object: 0, reasons: {}, samples: [] };
const GOOD_SCENE = { canonical_meshes: 2001, included_in_bounds: 2001,
  excluded_invalid_bounds: 0, bounds_valid: true, scene_radius: 10.34,
  camera_in_frustum: true, clip_valid: true, camera_near: 0.05, camera_far: 200,
  draw_calls: 41, webgl_context_ok: true };
function applyWith(scene, defects, behaviour, seq) {
  SCENE_STATE = scene; DEFECTS = defects; SET_MODEL_BEHAVIOUR = behaviour;
  return acsApplyBuilding(prodModel(true), seq === undefined ? {} : { seq: seq });
}
const OK = () => JSON.parse(JSON.stringify(GOOD_SCENE));

let r = applyWith(OK(), CLEAN_DEFECTS, () => {});
chk('نموذج سليم → يمرّ إلى انتظار أوّل إطار',
    r.ok === true && r.reached === 'AWAITING_FIRST_FRAME', r.reached);
chk('والخطوات مسجَّلة بأسمائها بالترتيب',
    r.steps.join('>') === 'RESPONSE_RECEIVED>BUILDING_ACCEPTED>SET_MODEL_COMPLETE'
      + '>GEOMETRY_VERIFIED>CAMERA_FIT_COMPLETE>AWAITING_FIRST_FRAME',
    r.steps.join('>'));

r = applyWith(OK(), CLEAN_DEFECTS, () => {
  const e = new Error('rect is not iterable'); throw e; });
chk('setModel يرمي → MODEL_LOAD_ERROR حتميّاً',
    r.ok === false && r.class === ACS_FAIL.MODEL_LOAD_ERROR
    && r.reached === 'SET_MODEL_THREW', r.class + '/' + r.reached);
chk('ونصّ الاستثناء محفوظ للتشخيص',
    /rect is not iterable/.test(r.error || ''), r.error);
chk('ورأس المكدّس محفوظ', String(r.stack || '').length > 0);

r = applyWith(Object.assign(OK(), { included_in_bounds: 54 }), CLEAN_DEFECTS, () => {});
chk('هندسة بُنيت ولم تصل الحدود → MODEL_LOAD_ERROR (عطل KI-25 بالضبط)',
    r.ok === false && r.class === ACS_FAIL.MODEL_LOAD_ERROR
    && r.reached === 'GEOMETRY_LOST', r.class + '/' + r.reached);
chk('والرسالة تحمل العددين لا وصفاً مبهماً',
    /2001/.test(r.error || '') && /54/.test(r.error || ''), r.error);

r = applyWith(OK(), Object.assign({}, CLEAN_DEFECTS, { rejected_room: 3 }), () => {});
chk('غرف مرفوضة → MODEL_LOAD_ERROR لا نجاح جزئيّ صامت',
    r.ok === false && r.class === ACS_FAIL.MODEL_LOAD_ERROR
    && r.reached === 'MODEL_ELEMENTS_REJECTED', r.class + '/' + r.reached);

r = applyWith(Object.assign(OK(), { canonical_meshes: 0, included_in_bounds: 0 }),
              CLEAN_DEFECTS, () => {});
chk('رد فيه مناطق ولا هندسة → MODEL_LOAD_ERROR',
    r.ok === false && r.reached === 'NO_GEOMETRY_BUILT', r.reached);

r = applyWith(Object.assign(OK(), { clip_valid: false }), CLEAN_DEFECTS, () => {});
chk('مستويا قصّ غير صالحين → RENDER_CAMERA_ERROR',
    r.class === ACS_FAIL.RENDER_CAMERA_ERROR && r.reached === 'CAMERA_FIT_FAILED',
    r.class + '/' + r.reached);
r = applyWith(Object.assign(OK(), { camera_near: NaN }), CLEAN_DEFECTS, () => {});
chk('قصّ غير منتهٍ (NaN) → RENDER_CAMERA_ERROR', r.class === ACS_FAIL.RENDER_CAMERA_ERROR);
r = applyWith(Object.assign(OK(), { scene_radius: Infinity }), CLEAN_DEFECTS, () => {});
chk('نصف قطر لا نهائيّ → RENDER_CAMERA_ERROR', r.class === ACS_FAIL.RENDER_CAMERA_ERROR);
r = applyWith(Object.assign(OK(), { camera_in_frustum: false }), CLEAN_DEFECTS, () => {});
chk('النموذج خارج هرم الرؤية → RENDER_CAMERA_ERROR',
    r.class === ACS_FAIL.RENDER_CAMERA_ERROR);
r = applyWith(Object.assign(OK(), { bounds_valid: false }), CLEAN_DEFECTS, () => {});
chk('حدود غير صالحة → RENDER_CAMERA_ERROR', r.class === ACS_FAIL.RENDER_CAMERA_ERROR);

chk('ولا تصنيف واحد من هذه ينسب العطل إلى الشبكة أو الخادم',
    [ACS_FAIL.MODEL_LOAD_ERROR, ACS_FAIL.RENDER_CAMERA_ERROR,
     ACS_FAIL.RENDER_BLACK_VIEWPORT].every(c =>
      c.indexOf('API_') !== 0));

// ═══════════════ و · الإطار الحقيقيّ شرطٌ للنجاح ════════════════════════════
console.log('\n== و · F-44: لا نجاح قبل إطار مرسوم ==');
r = applyWith(OK(), CLEAN_DEFECTS, () => {});
window.ACS.viewportBlank = () => ({ blank: true,
  probe: { method: 'READ_PIXELS', non_zero_pct: 0, max_luminance: 0 } });
let f = acsApplyFirstFrame(r);
chk('نافذة خالية بعد بناء سليم → RENDER_BLACK_VIEWPORT',
    f.ok === false && f.class === ACS_FAIL.RENDER_BLACK_VIEWPORT
    && f.reached === 'VIEWPORT_EMPTY', f.class + '/' + f.reached);

r = applyWith(OK(), CLEAN_DEFECTS, () => {});
window.ACS.viewportBlank = () => ({ blank: false,
  probe: { method: 'READ_PIXELS', non_zero_pct: 61.2, max_luminance: 212 } });
f = acsApplyFirstFrame(r);
chk('نافذة مرسومة → VISIBLE ونجاح مُقاس لا مُدّعى',
    f.ok === true && f.reached === 'VISIBLE' && f.pixels_verified === true,
    f.reached);
chk('وقياس البكسلات مُرفَق بالنتيجة',
    (f.pixel_probe || {}).method === 'READ_PIXELS'
    && f.pixel_probe.non_zero_pct === 61.2);

r = applyWith(OK(), CLEAN_DEFECTS, () => {});
window.ACS.viewportBlank = () => { throw new Error('no webgl'); };
f = acsApplyFirstFrame(r);
chk('لا عتاد بكسلات → NOT VERIFIED صراحةً، لا نجاح ولا فشل مُدّعى',
    f.ok === true && f.reached === 'FIRST_FRAME_NOT_VERIFIED'
    && f.pixels_verified === false, f.reached);

// ═══════════════ ز · الجيل: ردٌّ قديم لا يكتب فوق أحدث ══════════════════════
console.log('\n== ز · F-45: سباق ما بعد نداء طويل ==');
const t1 = acsApplyTicket();
const t2 = acsApplyTicket();
chk('كل نداء يسحب تذكرة أحدث', t2 === t1 + 1, t1 + ' → ' + t2);
let applied = 0;
r = applyWith(OK(), CLEAN_DEFECTS, () => { applied++; }, t1);
chk('ردّ التذكرة الأقدم يُهمَل ولا يُطبَّق',
    r.stale === true && r.class === 'STALE_RESPONSE_IGNORED' && applied === 0,
    r.class + ' applied=' + applied);
chk('وإهماله ليس فشلاً يُعرَض للمستخدم', r.ok === false && r.error === null);
r = applyWith(OK(), CLEAN_DEFECTS, () => { applied++; }, t2);
chk('وردّ التذكرة الحالية يُطبَّق', r.stale === false && applied === 1,
    'applied=' + applied);

// ═══════════════ ح · التراجع: القديم لا يُهدَم قبل نجاح الجديد ═══════════════
console.log('\n== ح · F-43: بناءٌ قبل هدم، وتراجع معرَّف ==');
const src = require('fs').readFileSync(
  require('path').join(__dirname, '..', '..', 'public', 'app', 'ui',
                       'workspace-ui-wiring.js'), 'utf8');
const setModelSrc = src.slice(src.indexOf('function setModel(data){'),
                              src.indexOf('/* الأدوار */'));
const iCompile = setModelSrc.indexOf('_next=compile(incoming)');
const iRemove = setModelSrc.indexOf('scene.remove(model)');
const iDispose = setModelSrc.indexOf('m.dispose()');
chk('compile يسبق scene.remove في المصدر المشحون',
    iCompile > 0 && iRemove > iCompile, iCompile + ' < ' + iRemove);
chk('وإتلاف الخامات القديمة يقع بعد نجاح البناء',
    iDispose > iCompile, iDispose + ' > ' + iCompile);
chk('وهناك مسار تراجع صريح يعيد الخامات عند الاستثناء',
    /catch\(e\)\{[\s\S]{0,200}_prevMats\[k\][\s\S]{0,80}throw e;/.test(setModelSrc));
chk('و lastBuilding لا يُحدَّث إلّا بعد نجاح compile',
    setModelSrc.indexOf('lastBuilding=data') > iCompile,
    setModelSrc.indexOf('lastBuilding=data') + ' > ' + iCompile);

// ═══════════════ ط · مسار الجوال ═══════════════════════════════════════════
console.log('\n== ط · مسار الجوال (تفصيل خفيف) يبني نفس المبنى ==');
const savedDetail = __ACS_SHARED.DETAIL;
__ACS_SHARED.DETAIL = 0.5;
const M = build(prodModel(false));
__ACS_SHARED.DETAIL = savedDetail;
chk('DETAIL=0.5 → لا استثناء ولا شبكة تالفة',
    M.err === null && M.defects.non_finite_box === 0,
    String((M.err || {}).message || ''));
chk('والهندسة كلّها تصل الحدود', M.dropped === 0 && M.kept === M.meshes,
    M.kept + '/' + M.meshes);
chk('والأدوار الثلاثة قائمة',
    M.floorKeys.indexOf('F2') >= 0, JSON.stringify(M.floorKeys));
/* قياسٌ لا أمنية: ‎__ACS_SHARED.DETAIL‎ يصل تعبيرين اثنين في المستودع كلّه
   (segs و posts في buildRacks) وكلاهما محصور بـ Math.max(2,…). فعند هذه
   الأرفف يقع الطرفان على القيمة المحصورة نفسها، فلا ينقص عدد الشبكات. هذا
   محدوديّةُ تغطية معلومة لا عطلٌ في مسار الجوال — والمُختبَر هنا أن المسار
   يبني المبنى نفسه سليماً، وهو ما ثبت أعلاه. */
chk('وعدد الشبكات لا يزيد في الوضع الخفيف',
    M.meshes <= A.meshes, M.meshes + ' ≤ ' + A.meshes);
console.log('     ملاحظة مقيسة: DETAIL=0.5 لم يغيّر العدد هنا ('
            + M.meshes + ' = ' + A.meshes + ') — أثره محصور في segs/posts '
            + 'وكلاهما عند حدّه الأدنى أصلاً بهذه الأرفف.');

// ═══════════════ ي · لا يُسرَّب محتوى مبنى في التشخيص ════════════════════════
console.log('\n== ي · التشخيص أعداد ورموز، لا محتوى مبنى ==');
r = applyWith(Object.assign(OK(), { included_in_bounds: 54 }),
              Object.assign({}, CLEAN_DEFECTS, { non_finite_box: 1947,
                reasons: { NON_FINITE_GEOMETRY: 1947 },
                samples: ['FLOOR|F0|slab|0'] }), () => {});
const blob = JSON.stringify(r);
chk('لا مستطيل غرفة في حمولة الحاجز', blob.indexOf('"rect"') < 0);
chk('ولا وصف العميل', blob.indexOf('مستودع') < 0);
chk('ولا معرّف منطقة كاملاً بمقاساته', !/zone_\d+".*rect/.test(blob));
chk('والعيّنات وسومُ طبقات لا محتوى',
    (r.defects.samples || []).every(s => /^[A-Z]+\|/.test(s)),
    JSON.stringify(r.defects.samples));

// ═══════════════ ك · ما كان قائماً لم يضعف ══════════════════════════════════
console.log('\n== ك · العقود القائمة لم تُمَسّ ==');
chk('KI-3 قائم: عقد الحدود ما زال يستبعد التالف لا يقبله',
    /NON_FINITE/.test(String(pqElementValid)));
const _tc = (src.match(/const ACS_TRANSPORT_CLASSES=\[([\s\S]*?)\];/) || [])[1] || '';
chk('وحاجز التطبيق لا يمسّ تصنيفات النقل العشرة',
    (_tc.match(/'/g) || []).length / 2 === 10 && /'SUCCESS'/.test(_tc),
    String((_tc.match(/'/g) || []).length / 2));
chk('و 200 بلا building يبقى فشلاً كما كان',
    /if\(!data\.building\)/.test(src) && /MODEL_VALIDATION_ERROR/.test(src));
chk('ولوحة عطل الخادم بقيت منفصلة عن لوحة عطل التطبيق',
    /acsErrorPanel/.test(src) && /acsApplyErrorPanel/.test(src)
    && src.indexOf('لم يُنفَّذ التوليد على الخادم') > 0
    && src.indexOf('وصل النموذج من الخادم ولم يُعرَض') > 0);
chk('ورد فاشل ما زال لا يستدعي setModel إطلاقاً',
    /لا setModel هنا إطلاقاً/.test(src));

/* حارسٌ أضيف لأن غيابه كلّف صفحةً كاملة أثناء هذا الإصلاح: ‎__ACS_SHARED‎
   مختوم بـ‎Object.seal‎، فإسناد مفتاح غير مُصرَّح به يرمي **وقت تقييم
   الوحدة** فيسقط رسم الصفحة كلّه — ولا يظهر ذلك في أي حزمة Node لأن
   shared-state.js ليس فيها. الفحص هنا يقارن ما تكتبه طبقة الربط بما يصرّح
   به الكائن المختوم. */
const sharedSrc = require('fs').readFileSync(
  require('path').join(__dirname, '..', '..', 'public', 'app',
                       'shared-state.js'), 'utf8');
const declared = new Set((sharedSrc.match(/^\s{2}([A-Za-z_$][\w$]*)\s*:/gm) || [])
  .map(s => s.trim().replace(':', '')));
const written = [...new Set((src.match(/__ACS_SHARED\.([A-Za-z_$][\w$]*)\s*=/g) || [])
  .map(s => s.replace('__ACS_SHARED.', '').replace(/\s*=$/, '')))];
chk('كل مفتاح تكتبه طبقة الربط على __ACS_SHARED مُصرَّح به في الكائن المختوم',
    written.every(k => declared.has(k)),
    JSON.stringify(written.filter(k => !declared.has(k))));
chk('ومنها مفتاح لوحة عطل ما بعد 200',
    declared.has('acsApplyErrorPanel') && written.indexOf('acsApplyErrorPanel') >= 0);

console.log('\n' + '─'.repeat(62));
console.log('PIXELS AND REAL WEBGL: measured in '
  + 'tests/remediation/test_apply_render_browser.js, not here');
console.log('MODEL APPLY: %d passed, %d failed', pass, fail);
if (fail) process.exit(1);

}

main();
