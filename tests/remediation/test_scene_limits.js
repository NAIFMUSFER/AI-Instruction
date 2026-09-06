/* ============================================================================
   KI-26 · F-46 — حدود المشهد: ما لا نبنيه يجب أن يُعدّ ويُقال.
     node tests/lib/run.js tests/remediation/test_scene_limits.js

   العطل الذي يغلقه هذا الملفّ
   ---------------------------
   بعد KI-25 صار المترجم لا يبني هندسةً تالفة ولا يهدم مشهداً بغرفةٍ واحدة.
   بقي العطل المعاكس تماماً، وهو أهدأ منه وأخطر: **المترجم يبني أقلّ ممّا
   أُعطي، أو لا يبني على الإطلاق، ولا يقول**.

     · ثمانية عشر حدّاً مدفوناً في أجسام الدوالّ — ‎Math.min(+o.count||1,200)‎
       و‎Math.min(rows,40)‎ و‎DQ(8,2,20)‎ … — لا يعرف أحدها الآخر، وكلٌّ منها
       يقصّ صامتاً. ولا سقف كلّياً فوقها: حاصل ضربها ملايين الشبكات.
     · موضعٌ واحد بلا حدٍّ إطلاقاً: ‎es=Math.max(1,Math.floor(len/12))‎ في السير
       الناقل. عنصر lane واحد بعرضٍ ضخم = آلاف نقاط الإيقاف من سطر JSON.
     · أربعة ‎catch(e){}‎ في ‎compile‎ تبتلع تخصّصاً كاملاً. أخطرها
       ‎ARCH=null‎: تختفي **كل فراغات النوى** من بلاطات المبنى — لا مَنور مصعد
       ولا فتحة درج — والمشهد يبدو سليماً تماماً.
     · و‎slabStrips‎ زمنه مكعّب في عدد النوى: ٢٥٦ نواة = ١٤١ مللي ثانية لكل
       دور، و٥١٢ = ٩١٩ مللي ثانية، بلا حدٍّ على العدد.

   نطاق هذا الملفّ — مُعلَن بدقّة
   -----------------------------
   نفس نمط tests/remediation/test_model_apply.js: بديل هندسة معلَن يسجّل
   الصناديق ولا يرسمها، فالمقيس هنا **الهندسة المنبعثة** لا البكسلات، وحاجزُ
   التطبيق يُقاس بمنطقه المنتزَع من الوحدة المشحونة على محيطٍ قابل للإبدال.
   ما لا يُقاس هنا: البكسلات والكاميرا (tests/remediation/test_apply_render_browser.js)
   وما في الواجهة من DOM (يُقاس نصّياً من المصدر المشحون كما في §ح هناك).
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

const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');
const VIEWER_SRC = fs.readFileSync(
  path.join(ROOT, 'public', 'app', 'core', 'viewer.js'), 'utf8');
const WIRING_SRC = fs.readFileSync(
  path.join(ROOT, 'public', 'app', 'ui', 'workspace-ui-wiring.js'), 'utf8');
/* شيفرةٌ بلا تعليقات الكتل. لازمٌ لا زينة: تعليقات هذا المستودع تقتبس السطر
   القديم حرفياً («كان Math.min(+R.levels||K.levels,10)»)، فبحثٌ نصّي عن الرقم
   المدفون يجده في **شرح إزالته** ويعلن فشلاً كاذباً — أو أسوأ، يجد السطر
   القديم في تعليقٍ فيظنّه قائماً. تُزال تعليقات ‎/* … *​/‎ وحدها؛ تعليقات
   السطر تبقى فلا يُقتَص من الشيفرة شيء بسبب «//» داخل نصّ. */
const stripBlockComments = t => t.replace(/\/\*[\s\S]*?\*\//g, ' ');
const VIEWER_CODE = stripBlockComments(VIEWER_SRC);
const WIRING_CODE = stripBlockComments(WIRING_SRC);

/* نصّ تصريحٍ عليٍّ واحد من المصدر: من ‎function NAME(‎ إلى أوّل تصريحٍ عليٍّ
   بعده (عمود صفر). يُستعمل لإثبات أن رقماً مدفوناً لم يبقَ في دالّةٍ بعينها. */
function fnSrc(name, src) {
  const t = src || VIEWER_SRC;
  const i = t.indexOf('function ' + name + '(');
  if (i < 0) return '';
  const rest = t.slice(i + 1);
  const m = /\n(?:function |const |let |\/\* =)/.exec(rest);
  return m ? rest.slice(0, m.index + 1) : rest;
}
/* ‎Math.min(x, <عدد من رقمين فأكثر>)‎ — شكلُ الحدّ المدفون الذي نُقل إلى العقد */
const BURIED = /Math\.min\([^()]*,\s*\d{2,}\s*\)/;

/* ═══════════ نماذج بشكل الإنتاج ═══════════════════════════════════════════ */
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
/* غرفةٌ واحدة فيها كل عائلة تكرار: رفوف · سير · محطات · أرصفة · عناصر · نقاط.
   كل حقل هنا مدخلٌ لحلقةٍ يقودها النموذج، وهو ما تُعبث به §د. */
function repModel() {
  return { meta: { type: 'warehouse' }, site: { w: 120, d: 80 },
    floor_height: 12, wall_h: 10, wall_t: 0.25,
    levels: [{ index: 0, template: 'ops' }],
    floors: { ops: { rooms: [{ id: 'ops_all', rect: [0, 0, 110, 70],
      role: 'storage', walls: 'none',
      racks: [{ kind: 'pallet', x: 1, z: 1, w: 60, d: 40, dir: 'x',
                aisle: 3.4, depth: 1.1, bay: 2.7, levels: 4, h: 8 }],
      lanes: [{ kind: 'conveyor', x: 1, z: 50, w: 60, d: 1, dir: 'x', h: 0.9 },
              { kind: 'forklift', x: 1, z: 55, w: 60, d: 3, dir: 'x' }],
      stations: [{ kind: 'pack', x: 1, z: 60, count: 6, pitch: 2.7, dir: 'x' }],
      docks: [{ edge: 'N', offset: 4, width: 3.6, height: 4.2, count: 4, pitch: 6 }],
      objects: [{ kind: 'pallet', x: 5, z: 65, count: 5, pitch: 1.4 }],
      points: [{ type: 'light', x: 20, z: 20 }] }] } } };
}
/* نموذج يتجاوز السقف الكلّي: غرفتان × أربعون رفّاً × أربعون صفّاً × عشرة
   مستويات. كل حدٍّ محلّي محترَم، وحاصل ضربها ربعُ مليون شبكة. */
function overCapModel() {
  const rooms = [];
  for (let i = 0; i < 2; i++) {
    const racks = [];
    for (let k = 0; k < 40; k++)
      racks.push({ kind: 'pallet', x: 0.5, z: 0.5, w: 190, d: 190, dir: 'x',
                   aisle: 3.4, depth: 1.1, bay: 2.7, levels: 10, h: 9, rows: 40 });
    rooms.push({ id: 'big' + i, rect: [i * 220, 0, 200, 200], role: 'storage',
                 walls: 'none', racks: racks });
  }
  return { meta: { type: 'warehouse' }, site: { w: 460, d: 200 },
    floor_height: 12, wall_h: 10, wall_t: 0.25,
    levels: [{ index: 0, template: 'ops' }], floors: { ops: { rooms: rooms } } };
}

function build(model) {
  boxes.length = 0;
  let err = null;
  try { compile(model); } catch (e) { err = e; }
  return { err: err, meshes: boxes.length, defects: acsBuildDefects(),
    summary: err ? null : acsCompileSummary(),
    names: boxes.map(b => String(b.name)) };
}

/* ═══════════ العرّاف: خوارزمية slabStrips كما كانت قبل F-46 حرفياً ═════════
   منقولة من ‎git show 02cf7e3:public/app/core/viewer.js‎ بلا حرفٍ واحد من
   التغيير. هي مرجع التطابق: النسخة الجديدة أسرع، ويجب أن تكون مطابقةً لها
   بايتاً ببايت لأي مجموعة نوى عند الحدّ أو دونه. */
function oracleSlabStrips(x0, z0, W, D, holes) {
  const cut = (lo, hi, vals) => { const s = new Set([lo, hi]);
    vals.forEach(v => { if (v > lo + 1e-6 && v < hi - 1e-6) s.add(v); });
    return Array.from(s).sort((a, b) => a - b); };
  const hs = (holes || []).map(h => [Math.max(x0, h[0]), Math.max(z0, h[1]),
    Math.min(x0 + W, h[0] + h[2]), Math.min(z0 + D, h[1] + h[3])])
    .filter(h => h[2] > h[0] + 1e-6 && h[3] > h[1] + 1e-6);
  if (!hs.length) return [[x0, z0, W, D]];
  const xs = cut(x0, x0 + W, hs.flatMap(h => [h[0], h[2]]));
  const zs = cut(z0, z0 + D, hs.flatMap(h => [h[1], h[3]]));
  const out = [];
  for (let i = 0; i + 1 < zs.length; i++) {
    let run = null;
    for (let j = 0; j + 1 < xs.length; j++) {
      const cx = (xs[j] + xs[j + 1]) / 2, cz = (zs[i] + zs[i + 1]) / 2;
      const solid = !hs.some(h => cx > h[0] && cx < h[2] && cz > h[1] && cz < h[3]);
      if (solid) { if (run) run[1] = xs[j + 1]; else run = [xs[j], xs[j + 1]]; }
      else if (run) { out.push([run[0], zs[i], run[1] - run[0], zs[i + 1] - zs[i]]); run = null; }
    }
    if (run) out.push([run[0], zs[i], run[1] - run[0], zs[i + 1] - zs[i]]);
  }
  return out;
}
/* مولّد نوى مُبذَّر لكن **حتميّ**: نفس البذرة تعطي نفس النوى في كل تشغيل،
   فالمقارنة بين النسختين تجري على المُدخَل نفسه بالضبط. */
function seededHoles(V, seed, W, D) {
  let s = (seed >>> 0) || 1;
  const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  const out = [];
  for (let i = 0; i < V; i++) {
    const w = 0.4 + r() * 5, d = 0.4 + r() * 5;
    out.push([r() * (W - w), r() * (D - d), w, d]);
  }
  return out;
}
function msOf(fn, reps) {
  let best = Infinity;
  for (let k = 0; k < 5; k++) {
    const t0 = process.hrtime.bigint();
    for (let i = 0; i < reps; i++) fn();
    const t1 = process.hrtime.bigint();
    best = Math.min(best, Number(t1 - t0) / 1e6 / reps);
  }
  return best;
}

function main() {

/* حارسُ المُجرِّد نفسه: لو أفسد الاقتصاصُ الشيفرة لصارت كل نفياتٍ أعلاه
   تمرّ بلا معنى. يُقاس قبل أي شيء آخر. */
chk('مجرِّد التعليقات لم يبتلع الشيفرة',
    VIEWER_CODE.indexOf('function slabStrips(') > 0
    && VIEWER_CODE.indexOf('function addBox(') > 0
    && WIRING_CODE.indexOf('function acsApplyBuilding(') > 0
    && VIEWER_CODE.length > VIEWER_SRC.length * 0.55,
    VIEWER_CODE.length + ' / ' + VIEWER_SRC.length);

// ═══════════════ أ · عقد الحدود: مُعلَن، مجمَّد، ومقروء فعلاً ════════════════
console.log('\n== أ · SCENE_LIMITS عقدٌ واحد مُعلَن، لا أرقام مدفونة ==');
chk('العقد موجود ومجمَّد', typeof SCENE_LIMITS === 'object'
    && Object.isFrozen(SCENE_LIMITS), String(typeof SCENE_LIMITS));
chk('وله رقم إصدار مُعلَن', SCENE_LIMITS.contract === 'acs.scene-limits/1.0.0',
    String(SCENE_LIMITS.contract));
const LIMIT_KEYS = Object.keys(SCENE_LIMITS).filter(k => k !== 'contract');
chk('وفيه حدود فعلية لا كائن فارغ', LIMIT_KEYS.length >= 18,
    String(LIMIT_KEYS.length));
chk('كل حدٍّ عددٌ صحيح منتهٍ موجب',
    LIMIT_KEYS.every(k => typeof SCENE_LIMITS[k] === 'number'
      && isFinite(SCENE_LIMITS[k]) && SCENE_LIMITS[k] > 0
      && SCENE_LIMITS[k] === Math.floor(SCENE_LIMITS[k])),
    JSON.stringify(LIMIT_KEYS.filter(k => !(typeof SCENE_LIMITS[k] === 'number'
      && isFinite(SCENE_LIMITS[k]) && SCENE_LIMITS[k] > 0
      && SCENE_LIMITS[k] === Math.floor(SCENE_LIMITS[k])))));
chk('ولا حدَّ مُعلَنٍ لا تقرؤه الشيفرة (كلّها مستعملة بالاسم)',
    LIMIT_KEYS.every(k => VIEWER_SRC.indexOf('SCENE_LIMITS.' + k) >= 0),
    JSON.stringify(LIMIT_KEYS.filter(k =>
      VIEWER_SRC.indexOf('SCENE_LIMITS.' + k) < 0)));

/* لكل دالّة: الحدّ الذي كان مدفوناً فيها صار اسماً، ولم يبقَ في جسمها
   ‎Math.min(…, <عدد>)‎ واحد. */
const MOVED = [
  ['acsAcceptMesh', ['max_total_meshes']],
  ['buildRoom', ['max_points_per_room']],
  ['buildRacks', ['max_racks_per_room', 'max_rack_levels', 'max_rack_rows',
                  'max_rack_bays', 'max_rack_segments', 'max_rack_posts']],
  ['buildLanes', ['max_lanes_per_room', 'max_lane_arrows']],
  ['buildConveyor', ['max_conveyor_parts']],
  ['buildStations', ['max_stations_per_room']],
  ['buildDocks', ['max_docks_per_room']],
  ['dockOpenings', ['max_docks_per_room']],
  ['buildObjects', ['max_objects_per_room', 'max_object_count']],
  ['buildObject', ['max_object_parts']],
  ['slabStrips', ['max_cores_per_level', 'max_slab_strips_per_level']],
  ['compile', ['max_levels', 'max_rooms_per_level']],
  ['acsSpan', ['max_generator_span_m']],
  ['parseDescription', ['max_text_repeats']]
];
chk('الصندوق والمضلع يستعملان حارس عدد الشبكات نفسه',
    fnSrc('addBox').includes('acsAcceptMesh(name)')
    && fnSrc('addPolygonPrism').includes('acsAcceptMesh(name)'));
MOVED.forEach(([fn, keys]) => {
  const src = fnSrc(fn);
  chk((fn + ' — نصّه انتُزع من المصدر').padEnd(52), src.length > 40,
      String(src.length));
  chk((fn + ' — يقرأ ' + keys.join(', ')).padEnd(52),
      keys.every(k => src.indexOf('SCENE_LIMITS.' + k) >= 0),
      JSON.stringify(keys.filter(k => src.indexOf('SCENE_LIMITS.' + k) < 0)));
  const code = fnSrc(fn, VIEWER_CODE);
  chk((fn + ' — لا حدَّ رقميّاً مدفوناً باقياً').padEnd(52), !BURIED.test(code),
      String((BURIED.exec(code) || [''])[0]));
});
/* الموضع الذي لم يكن له حدّ أصلاً: نقاط إيقاف السير */
chk('وسطر نقاط إيقاف السير لم يعد بلا سقف',
    /const es=acsFit\(Math\.floor\(len\/12\)/.test(fnSrc('buildConveyor'))
    && !/const es=Math\.max\(1,Math\.floor\(len\/12\)\);/.test(VIEWER_CODE));

// ═══════════════ ب · السقف الكلّي: يكبت، يَعُدّ، ولا يرمي ════════════════════
console.log('\n== ب · F-46: سقفٌ كلّي واحد فوق كل الحدود المحلّية ==');
const CAP = build(overCapModel());
chk('نموذجٌ يتجاوز السقف يُبنى بلا استثناء', CAP.err === null,
    String((CAP.err || {}).message || ''));
chk('وعدد الشبكات يقف عند الحدّ بالضبط لا فوقه',
    CAP.meshes === SCENE_LIMITS.max_total_meshes,
    CAP.meshes + ' / ' + SCENE_LIMITS.max_total_meshes);
chk('وما كُبت مُحصى بعدده لا مُهمَل',
    CAP.summary.suppressed_meshes > 0
    && CAP.summary.accepted_objects === SCENE_LIMITS.max_total_meshes,
    'suppressed=' + CAP.summary.suppressed_meshes);
chk('والقرار مُسجَّل برمزه SCENE_COMPLEXITY_LIMIT مرّةً واحدة (لا سطر لكل عنصر)',
    CAP.defects.reasons.SCENE_COMPLEXITY_LIMIT === 1
    && CAP.summary.degradation_reasons.indexOf('SCENE_COMPLEXITY_LIMIT') >= 0,
    String(CAP.defects.reasons.SCENE_COMPLEXITY_LIMIT));
chk('والمشهد يُعلَن متدهوراً لا ناجحاً', CAP.summary.degraded === true);
const CAP2 = build(overCapModel());
chk('ونفس المُدخَل يُكبَت عند نفس النقطة بالضبط — حتميّ لا عشوائي',
    CAP2.meshes === CAP.meshes
    && CAP2.summary.suppressed_meshes === CAP.summary.suppressed_meshes,
    CAP.summary.suppressed_meshes + ' / ' + CAP2.summary.suppressed_meshes);
chk('وأسماء أوّل ألف عنصر متطابقة بين التشغيلين (نفس ترتيب البناء)',
    CAP.names.slice(0, 1000).join('§') === CAP2.names.slice(0, 1000).join('§'));

// ═══════════════ ج · slabStrips: مطابقٌ للعرّاف، ومحدود الزمن ════════════════
console.log('\n== ج · F-46: قصّ البلاطة أسرع، ومخرجُه مطابقٌ بايتاً ببايت ==');
let identical = 0, compared = 0;
for (const V of [1, 2, 3, 4, 5, 8, 11, 16, 23, 32, 47, 64]) {
  for (const seed of [7, 101, 9973]) {
    const holes = seededHoles(V, seed * 31 + V, 120, 80);
    const a = JSON.stringify(oracleSlabStrips(0, 0, 120, 80, holes));
    const b = JSON.stringify(slabStrips(0, 0, 120, 80, holes));
    compared++; if (a === b) identical++;
    else console.log('     ✗ V=' + V + ' seed=' + seed + '\n       old=' + a.slice(0, 160)
                     + '\n       new=' + b.slice(0, 160));
  }
}
chk('٣٦ مجموعة نوى مبذَّرة عند ١..٦٤ — المخرج مطابق للعرّاف حرفياً',
    identical === compared && compared === 36, identical + ' / ' + compared);
chk('ومطابقٌ أيضاً عند صفر نوى وعند نوىً كلّها خارج البلاطة',
    JSON.stringify(slabStrips(0, 0, 120, 80, []))
      === JSON.stringify(oracleSlabStrips(0, 0, 120, 80, []))
    && JSON.stringify(slabStrips(0, 0, 120, 80, [[500, 500, 3, 3]]))
      === JSON.stringify(oracleSlabStrips(0, 0, 120, 80, [[500, 500, 3, 3]])),
    JSON.stringify(slabStrips(0, 0, 120, 80, [[500, 500, 3, 3]])));
chk('ونواةٌ تلامس الحافّة أو تخرج منها جزئياً تُقصّ كما كانت تماماً',
    JSON.stringify(slabStrips(0, 0, 120, 80, [[-5, -5, 20, 20], [110, 70, 30, 30]]))
      === JSON.stringify(oracleSlabStrips(0, 0, 120, 80,
            [[-5, -5, 20, 20], [110, 70, 30, 30]])));

const H16 = seededHoles(16, 1016, 120, 80);
const H64 = seededHoles(64, 1064, 120, 80);
const H256 = seededHoles(256, 1256, 120, 80);
const t16 = msOf(() => slabStrips(0, 0, 120, 80, H16), 40);
const t64 = msOf(() => slabStrips(0, 0, 120, 80, H64), 40);
const t256 = msOf(() => slabStrips(0, 0, 120, 80, H256), 20);
const o64 = msOf(() => oracleSlabStrips(0, 0, 120, 80, H64), 20);
const o256 = msOf(() => oracleSlabStrips(0, 0, 120, 80, H256), 3);
console.log('     ملّي ثانية (أفضل ٥): V=16 ' + t16.toFixed(3)
            + ' · V=64 ' + t64.toFixed(3) + ' (العرّاف ' + o64.toFixed(3) + ')'
            + ' · V=256 ' + t256.toFixed(3) + ' (العرّاف ' + o256.toFixed(3) + ')');
chk('زمن ٦٤ نواة أقلّ من مللي ثانية واحدة (كان ~٢٫٥)', t64 < 1.0, t64.toFixed(3));
chk('وزمن ٦٤ لا يتجاوز اثني عشر ضعف زمن ١٦ — نموٌّ مربّع لا مكعّب',
    t64 <= Math.max(0.6, t16 * 12), t64.toFixed(3) + ' vs ' + t16.toFixed(3));
chk('وأسرع من الخوارزمية القديمة عند ٦٤ نواة بمرّتين على الأقلّ',
    t64 * 2 < o64, t64.toFixed(3) + ' vs ' + o64.toFixed(3));
chk('و٢٥٦ نواة تبقى دون مللي ثانية بفضل حدّ النوى (العرّاف عندها ~١٤١)',
    t256 < 1.0, t256.toFixed(3));

acsBuildDefectsReset();
slabStrips(0, 0, 120, 80, seededHoles(SCENE_LIMITS.max_cores_per_level + 1, 5, 120, 80));
chk('ونوىً فوق الحدّ تُقصّ وتُحصى برمزها لا تُبتلع',
    acsBuildDefects().reasons.SLAB_CORES_CAPPED === 1
    && acsCompileSummary().degraded === true,
    JSON.stringify(acsBuildDefects().reasons));
acsBuildDefectsReset();
slabStrips(0, 0, 120, 80, seededHoles(SCENE_LIMITS.max_cores_per_level, 5, 120, 80));
chk('ونوىً عند الحدّ بالضبط لا تُقصّ ولا تُحصى',
    acsBuildDefects().reasons.SLAB_CORES_CAPPED === undefined
    && acsCompileSummary().degraded === false,
    JSON.stringify(acsBuildDefects().reasons));

// ═══════════════ د · كل حلقةٍ يقودها النموذج محدودة ومُحصاة ══════════════════
console.log('\n== د · F-46: سالب · NaN · ∞ · صفر · 1e9 · خطوة دقيقة ==');
const BAD = [['سالب', -7], ['NaN', 'ليست رقماً'], ['لانهاية', Infinity],
             ['صفر', 0], ['مليار', 1e9], ['كسر دقيق', 1e-9]];
/* كل مسار حقلٍ هنا مدخلُ حلقةٍ حقيقية في المترجم */
const PATHS = [
  ['racks[0].levels', (r, v) => { r.racks[0].levels = v; }],
  ['racks[0].rows', (r, v) => { r.racks[0].rows = v; }],
  ['racks[0].bay', (r, v) => { r.racks[0].bay = v; }],
  ['racks[0].aisle', (r, v) => { r.racks[0].aisle = v; }],
  ['racks[0].depth', (r, v) => { r.racks[0].depth = v; }],
  ['lanes[0].w (سير)', (r, v) => { r.lanes[0].w = v; }],
  ['lanes[1].w (أسهم)', (r, v) => { r.lanes[1].w = v; }],
  ['stations[0].count', (r, v) => { r.stations[0].count = v; }],
  ['stations[0].pitch', (r, v) => { r.stations[0].pitch = v; }],
  ['docks[0].count', (r, v) => { r.docks[0].count = v; }],
  ['docks[0].pitch', (r, v) => { r.docks[0].pitch = v; }],
  ['objects[0].count', (r, v) => { r.objects[0].count = v; }],
  ['objects[0].pitch', (r, v) => { r.objects[0].pitch = v; }],
  ['objects[0].h (درج)', (r, v) => { r.objects[0].kind = 'stairs'; r.objects[0].h = v; }],
  ['objects[0].w (درابزين)', (r, v) => { r.objects[0].kind = 'railing'; r.objects[0].w = v; }]
];
const BASE = build(repModel());
chk('النموذج المرجعي للعبث يُبنى سليماً وغير متدهور',
    BASE.err === null && BASE.meshes > 100 && BASE.summary.degraded === false,
    BASE.meshes + ' meshes');
/* سقفٌ سخيّ: أي قيمة شاذّة يجب أن تبقى تحت خمسة أضعاف المرجع بكثير */
const SANE = 20000;
let badRuns = 0, badThrew = 0, badUnbounded = 0;
PATHS.forEach(([label, mutate]) => {
  let ok = true, detail = '';
  BAD.forEach(([bl, v]) => {
    const m = repModel();
    mutate(m.floors.ops.rooms[0], v);
    const R = build(m);
    badRuns++;
    if (R.err) { badThrew++; ok = false; detail = bl + ': ' + R.err.message; }
    else if (!(R.meshes >= 0 && R.meshes < SANE)) {
      badUnbounded++; ok = false; detail = bl + ': ' + R.meshes + ' شبكة';
    }
  });
  chk((label + ' — الستّة كلّها بلا استثناء وبعدد محدود').padEnd(52), ok, detail);
});
chk('ولا واحدة من ' + badRuns + ' حالة رمت استثناءً', badThrew === 0,
    String(badThrew));
chk('ولا واحدة تجاوزت ' + SANE + ' شبكة', badUnbounded === 0, String(badUnbounded));

/* القيم التي **يجب** أن تُحصى: ما فوق الحدّ صراحةً، وما ليس عدداً */
const COUNTED = [
  ['racks[0].levels = 1e9', r => { r.racks[0].levels = 1e9; }, 'capped_expansion'],
  ['racks[0].levels = -7', r => { r.racks[0].levels = -7; }, 'rejected_field'],
  ['racks[0].levels = "نص"', r => { r.racks[0].levels = 'نص'; }, 'rejected_field'],
  ['racks[0].rows = Infinity', r => { r.racks[0].rows = Infinity; }, 'capped_expansion'],
  ['racks[0].bay = 1e-9', r => { r.racks[0].bay = 1e-9; }, 'capped_expansion'],
  ['stations[0].count = 1e9', r => { r.stations[0].count = 1e9; }, 'capped_expansion'],
  ['stations[0].count = 0', r => { r.stations[0].count = 0; }, 'rejected_field'],
  ['docks[0].count = 1e9', r => { r.docks[0].count = 1e9; }, 'capped_expansion'],
  ['objects[0].count = 1e9', r => { r.objects[0].count = 1e9; }, 'capped_expansion'],
  ['objects[0].count = NaN', r => { r.objects[0].count = NaN; }, 'rejected_field'],
  ['lanes[0].w = 1e6 (سير)', r => { r.lanes[0].w = 1e6; }, 'capped_expansion'],
  ['objects[0].h = 1e9 (درج)',
   r => { r.objects[0].kind = 'stairs'; r.objects[0].h = 1e9; }, 'capped_expansion']
];
COUNTED.forEach(([label, mutate, kind]) => {
  const m = repModel(); mutate(m.floors.ops.rooms[0]);
  const R = build(m);
  chk((label + ' → يُحصى في ' + kind).padEnd(52),
      R.err === null && R.defects[kind] > BASE.defects[kind],
      kind + '=' + (R.err ? 'ERR' : R.defects[kind]));
});

/* نقطة إيقاف السير: العطل المسمّى في التقرير — سطرٌ بلا سقف */
(() => {
  const m = repModel();
  m.floors.ops.rooms[0].rect = [0, 0, 2000, 70];
  m.floors.ops.rooms[0].lanes = [{ kind: 'conveyor', x: 1, z: 50, w: 1990, d: 1,
                                   dir: 'x', h: 0.9 }];
  m.site = { w: 2000, d: 80 };
  const R = build(m);
  const es = R.names.filter(n => n.indexOf('|estop') >= 0).length;
  const legs = R.names.filter(n => n.indexOf('|convleg') >= 0).length;
  chk('سيرٌ بطول ١٩٩٠ م: نقاط الإيقاف محصورة بالحدّ لا ١٦٥ نقطة',
      R.err === null && es === SCENE_LIMITS.max_conveyor_parts,
      es + ' / ' + SCENE_LIMITS.max_conveyor_parts);
  chk('والأرجل محصورة بنفس الحدّ كما كانت',
      legs === SCENE_LIMITS.max_conveyor_parts, String(legs));
  chk('والقصّ مُحصى لا صامت', R.defects.capped_expansion > 0
      && R.summary.degraded === true, String(R.defects.capped_expansion));
})();

/* أطوال القوائم — رفوف · ممرّات · عناصر · نقاط · غرف · مستويات */
(() => {
  const cases = [
    ['racks × 5000', m => { const r = m.floors.ops.rooms[0];
      r.racks = []; for (let i = 0; i < 5000; i++)
        r.racks.push({ kind: 'bin', x: 1, z: 1, w: 4, d: 4, dir: 'x' }); },
     'RACKS_CAPPED'],
    ['lanes × 5000', m => { const r = m.floors.ops.rooms[0];
      r.lanes = []; for (let i = 0; i < 5000; i++)
        r.lanes.push({ kind: 'zone', x: 1, z: 1, w: 4, d: 4, dir: 'x' }); },
     'LANES_CAPPED'],
    ['objects × 5000', m => { const r = m.floors.ops.rooms[0];
      r.objects = []; for (let i = 0; i < 5000; i++)
        r.objects.push({ kind: 'box', x: 1, z: 1 }); }, 'OBJECTS_CAPPED'],
    ['points × 9000', m => { const r = m.floors.ops.rooms[0];
      r.points = []; for (let i = 0; i < 9000; i++)
        r.points.push({ type: 'light', x: 1, z: 1 }); }, 'POINTS_CAPPED'],
    ['rooms × 3000', m => { const rs = m.floors.ops.rooms;
      for (let i = 0; i < 3000; i++)
        rs.push({ id: 'r' + i, rect: [0, 0, 2, 2], walls: 'full' }); },
     'ROOMS_CAPPED'],
    ['levels × 500', m => { for (let i = 1; i < 500; i++)
        m.levels.push({ index: i, template: 'ops' }); }, 'LEVELS_CAPPED']
  ];
  cases.forEach(([label, mutate, reason]) => {
    const m = repModel(); mutate(m);
    const R = build(m);
    chk((label + ' → يُقصّ ويُحصى بـ' + reason).padEnd(52),
        R.err === null && R.defects.reasons[reason] > 0 && R.meshes < 400000,
        (R.err ? 'ERR ' + R.err.message : reason + '='
          + R.defects.reasons[reason] + ' meshes=' + R.meshes));
  });
})();

/* حقلٌ يُنتظَر قائمةً فجاء عدداً — كان يمرّ الحارس ثم يرمي */
(() => {
  const m = repModel(); m.levels = 12;
  const R = build(m);
  chk('levels عدداً لا مصفوفة → لا استثناء ويُحصى',
      R.err === null && R.defects.rejected_field > 0,
      String((R.err || {}).message || R.defects.rejected_field));
})();

/* امتداد الأرض في المولّدين: كان ‎Math.max(30,+W||120)‎ يمرّر ‎Infinity‎ */
(() => {
  acsBuildDefectsReset();
  const a = warehouseModel(Infinity, 80);
  chk('warehouseModel(∞) يعود بنموذج محدود بدل حلقة لا نهائية',
      !!a && a.site.w === SCENE_LIMITS.max_generator_span_m,
      String((a || {}).site && a.site.w));
  chk('والقصّ مُحصى', acsBuildDefects().reasons.GENERATOR_SPAN_CAPPED > 0,
      JSON.stringify(acsBuildDefects().reasons));
  acsBuildDefectsReset();
  const b = warehouseModel(120, 80);
  chk('ومقاسٌ عاديّ لا يُمَسّ ولا يُحصى',
      b.site.w === 120 && b.site.d === 80
      && acsBuildDefects().reasons.GENERATOR_SPAN_CAPPED === undefined,
      b.site.w + '×' + b.site.d);
})();

// ═══════════════ هـ · سقوط تخصّص: مرئيّ في الخلاصة وفي الحاجز ═══════════════
console.log('\n== هـ · F-46: تخصّصٌ يسقط لا يُبتلع في catch فارغ ==');
(() => {
  const saved = {};
  ['compileArchitecture', 'compileStructure', 'compileMep', 'compileFls']
    .forEach(k => { saved[k] = __ACS_LATE[k]; });
  const boom = () => { throw new Error('discipline compiler failed on purpose'); };

  __ACS_LATE.compileStructure = boom;
  let R = build(prodModel(true));
  chk('انهيار مصرِّف الإنشائي → لا استثناء يصعد', R.err === null,
      String((R.err || {}).message || ''));
  chk('ويُحصى في specialization_failures برمزه',
      R.summary.specialization_failures === 1
      && R.summary.degradation_reasons.indexOf('STRUCT_COMPILE_FAILED') >= 0,
      JSON.stringify(R.summary.degradation_reasons));
  chk('والخلاصة تعلن التدهور صراحةً', R.summary.degraded === true);
  __ACS_LATE.compileStructure = saved.compileStructure;

  __ACS_LATE.compileMep = boom; __ACS_LATE.compileFls = boom;
  R = build(prodModel(true));
  chk('MEP والحريق معاً → سقوطان محصيّان ولا استثناء',
      R.err === null && R.summary.specialization_failures === 2
      && R.summary.degradation_reasons.indexOf('MEP_COMPILE_FAILED') >= 0
      && R.summary.degradation_reasons.indexOf('FLS_COMPILE_FAILED') >= 0,
      JSON.stringify(R.summary.degradation_reasons));
  __ACS_LATE.compileMep = saved.compileMep;
  __ACS_LATE.compileFls = saved.compileFls;

  /* الحالة المسمّاة في التقرير: ARCH=null يمحو كل فراغات النوى من البلاطات */
  __ACS_LATE.compileArchitecture = boom;
  R = build(prodModel(true));
  chk('ARCH=null → يُحصى سقوط التخصّص **وضياع فراغات النوى** بسببين متمايزين',
      R.err === null
      && R.summary.degradation_reasons.indexOf('ARCH_COMPILE_FAILED') >= 0
      && R.summary.degradation_reasons.indexOf('SLAB_VOIDS_LOST') >= 0,
      JSON.stringify(R.summary.degradation_reasons));
  chk('ولم يعد في compile قوسُ catch يبتلع ARCH بلا أثر',
      !/catch\(e\)\{ ARCH=null; \}/.test(VIEWER_CODE));
  /* المسح الشامل: لا قوس ابتلاعٍ فارغ باقياً في مسار المترجم/العارض كلّه */
  const EMPTY_CATCH = /catch\s*\(\s*\w*\s*\)\s*\{\s*\}/g;
  chk('ولا قوسَ catch فارغاً واحداً باقياً في public/app/core/viewer.js',
      (VIEWER_CODE.match(EMPTY_CATCH) || []).length === 0,
      JSON.stringify((VIEWER_CODE.match(EMPTY_CATCH) || []).slice(0, 4)));
  chk('وبطاقات التخصّصات الثلاث في الواجهة تُحصي سقوط مصرِّفها بدل ابتلاعه',
      /INFOCARD_STRUCT_COMPILE_FAILED/.test(WIRING_CODE)
      && /INFOCARD_MEP_COMPILE_FAILED/.test(WIRING_CODE)
      && /INFOCARD_FLS_COMPILE_FAILED/.test(WIRING_CODE)
      && !/mepSystemById\(MP,el\.system_id\):null; \}catch\(e\)\{\}/.test(WIRING_CODE));
  __ACS_LATE.compileArchitecture = saved.compileArchitecture;

  R = build(prodModel(true));
  chk('وبعد استعادة المصرِّفات يعود المبنى غير متدهور — لا أثر لاصق',
      R.err === null && R.summary.degraded === false
      && R.summary.specialization_failures === 0,
      JSON.stringify(R.summary.degradation_reasons));
})();

console.log('\n== هـ٢ · الحاجز يصنّف التدهور DEGRADED لا MODEL_LOAD_ERROR ==');
globalThis.window = globalThis.window || {};
window.ACS = window.ACS || {};
let SCENE_STATE = null, DEFECTS = null;
setModel = function () {};
const REAL_DEFECTS = acsBuildDefects;
acsBuildDefects = function () { return DEFECTS; };
window.ACS.verifyVisibleModel = function () { return SCENE_STATE; };
const CLEAN = { non_finite_box: 0, rejected_room: 0, rejected_field: 0,
  derived_level_index: 0, unknown_object: 0, accepted_box: 2001,
  suppressed_box: 0, capped_expansion: 0, specialization_failed: 0,
  complexity_degraded: 0, reasons: {}, degradation_reasons: [], samples: [] };
const GOOD = { canonical_meshes: 2001, included_in_bounds: 2001,
  excluded_invalid_bounds: 0, bounds_valid: true, scene_radius: 10.34,
  camera_in_frustum: true, clip_valid: true, camera_near: 0.05, camera_far: 200,
  draw_calls: 41, webgl_context_ok: true };
function applyWith(defects) {
  SCENE_STATE = JSON.parse(JSON.stringify(GOOD));
  DEFECTS = defects;
  return acsApplyBuilding(prodModel(true), {});
}
chk('فئة الفشل الجديدة معلَنة في ACS_FAIL',
    ACS_FAIL.MODEL_DEGRADED_RENDER === 'MODEL_DEGRADED_RENDER');
chk('ولا تُنسَب إلى الشبكة ولا إلى الخادم',
    ACS_FAIL.MODEL_DEGRADED_RENDER.indexOf('API_') !== 0);

let r = applyWith(Object.assign({}, CLEAN));
chk('نموذج سليم → لا تدهور ولا فئة',
    r.ok === true && r.degraded === false && r.class === null, String(r.class));

r = applyWith(Object.assign({}, CLEAN, { specialization_failed: 1,
  reasons: { MEP_COMPILE_FAILED: 1 }, degradation_reasons: ['MEP_COMPILE_FAILED'] }));
chk('سقوط تخصّص → MODEL_DEGRADED_RENDER لا MODEL_LOAD_ERROR',
    r.class === ACS_FAIL.MODEL_DEGRADED_RENDER
    && r.class !== ACS_FAIL.MODEL_LOAD_ERROR && r.degraded === true,
    String(r.class));
chk('والنموذج يبقى معروضاً — التدهور ليس فشل تحميل', r.ok === true);
chk('والخطوة مسجَّلة باسمها في المسار',
    r.steps.indexOf('COMPLEXITY_DEGRADED') >= 0, r.steps.join('>'));
chk('والسبب مُرفَق بالنتيجة لا مطموس',
    (r.degradation.reasons || []).indexOf('MEP_COMPILE_FAILED') >= 0,
    JSON.stringify(r.degradation));
chk('وخلاصة المترجم مرفقة بعقدها',
    (r.summary || {}).contract === SCENE_LIMITS.contract,
    String((r.summary || {}).contract));

r = applyWith(Object.assign({}, CLEAN, { complexity_degraded: 1,
  suppressed_box: 41011, reasons: { SCENE_COMPLEXITY_LIMIT: 1 },
  degradation_reasons: ['SCENE_COMPLEXITY_LIMIT'] }));
chk('قرار تدهور تعقيد → MODEL_DEGRADED_RENDER مع عدد المكبوت',
    r.class === ACS_FAIL.MODEL_DEGRADED_RENDER
    && r.degradation.suppressed_meshes === 41011, String(r.class));

r = applyWith(Object.assign({}, CLEAN, { capped_expansion: 3,
  reasons: { COUNT_ABOVE_LIMIT: 3 }, degradation_reasons: ['COUNT_ABOVE_LIMIT'] }));
chk('توسّعٌ مقصوص → تدهورٌ أيضاً (بُني أقلّ ممّا طُلب)',
    r.class === ACS_FAIL.MODEL_DEGRADED_RENDER && r.degraded === true);

r = applyWith(Object.assign({}, CLEAN, { rejected_room: 2,
  specialization_failed: 1, degradation_reasons: ['MEP_COMPILE_FAILED'] }));
chk('وغرفةٌ مرفوضة تبقى MODEL_LOAD_ERROR — التدهور لا يخفّف عطلاً أشدّ',
    r.ok === false && r.class === ACS_FAIL.MODEL_LOAD_ERROR
    && r.reached === 'MODEL_ELEMENTS_REJECTED', r.class + '/' + r.reached);

r = applyWith(Object.assign({}, CLEAN, { specialization_failed: 1,
  degradation_reasons: ['MEP_COMPILE_FAILED'] }));
window.ACS.viewportBlank = () => ({ blank: false,
  probe: { method: 'READ_PIXELS', non_zero_pct: 61.2, max_luminance: 212 } });
let f = acsApplyFirstFrame(r);
chk('وبعد إطارٍ مرسوم لا يُكتب VISIBLE على مبنًى ناقص',
    f.reached === 'VISIBLE_DEGRADED' && f.pixels_verified === true, f.reached);
const blob = JSON.stringify(f);
chk('ولا يُسرَّب محتوى مبنى في حمولة التدهور',
    blob.indexOf('"rect"') < 0 && blob.indexOf('مستودع') < 0
    && (f.degradation.reasons || []).every(s => /^[A-Z_]+$/.test(s)),
    JSON.stringify(f.degradation.reasons));
acsBuildDefects = REAL_DEFECTS;

console.log('\n== هـ٣ · الواجهة لا تدّعي اكتمالاً بعد تدهور (مصدر مشحون) ==');
chk('setModel يقرأ الخلاصة قبل كتابة سطر الحالة',
    /acsCompileSummary\(\)/.test(WIRING_SRC)
    && /_deg\?'⚠ بُني ناقصاً/.test(WIRING_SRC));
chk('و«تم التوليد ✓» لم تعد تُكتب بلا شرط',
    !/statusEl\.textContent=`تم التوليد ✓/.test(WIRING_SRC));
chk('و«✓ بُني من وصفك» مسبوقةٌ بحارس التدهور',
    WIRING_SRC.indexOf('if(fr.degraded){')
      < WIRING_SRC.indexOf("statusEl.textContent='✓ بُني من وصفك"),
    String(WIRING_SRC.indexOf('if(fr.degraded){')));
chk('ولوحة عطل ما بعد 200 تعرض عنواناً مختلفاً للتدهور',
    WIRING_SRC.indexOf('⚠ عُرض النموذج ناقصاً — سقط منه جزء') > 0
    && WIRING_SRC.indexOf('وصل النموذج من الخادم ولم يُعرَض') > 0);
chk('وتعرض أسباب التدهور وأعداده لا وصفاً مبهماً',
    /تخصّصاً سقط كاملاً/.test(WIRING_SRC) && /عنصراً مكبوتاً/.test(WIRING_SRC)
    && /الأسباب: /.test(WIRING_SRC));

// ═══════════════ و · الأدوار: ترتيبٌ طبيعي وأسماءٌ بلا سقف ═══════════════════
console.log('\n== و · F-46: F0,F1,…,F9,F10 لا F0,F1,F10,F2 ==');
function keysFor(n) { const a = []; for (let i = 0; i < n; i++) a.push('F' + i); return a; }
function shuffled(n, seed) {
  let s = (seed >>> 0) || 1;
  const a = keysFor(n);
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 1664525 + 1013904223) >>> 0;
    const j = s % (i + 1); const t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}
[1, 7, 12, 50].forEach(n => {
  const want = keysFor(n).join(',');
  const got = acsFloorOrder(shuffled(n, n * 977 + 13)).join(',');
  const lexi = [...shuffled(n, n * 977 + 13)].sort().join(',');
  chk((n + ' دوراً → ترتيب عدديّ صارم').padEnd(40), got === want,
      got.slice(0, 90));
  if (n >= 12)
    chk((n + ' دوراً → والترتيب المعجميّ القديم كان يختلف فعلاً').padEnd(40),
        lexi !== want, lexi.slice(0, 60));
});
chk('ومفتاحٌ غير قياسي لا يختفي من الشريط بل يوضع بعد المرقَّمة',
    acsFloorOrder(['F10', 'SITE', 'F2', 'F0']).join(',') === 'F0,F2,F10,SITE',
    acsFloorOrder(['F10', 'SITE', 'F2', 'F0']).join(','));
chk('وترتيبٌ سليم أصلاً لا يتغيّر',
    acsFloorOrder(['F0', 'F1', 'F2']).join(',') === 'F0,F1,F2');
chk('وشريط الأدوار في الواجهة يستعمل العقد لا sort() النصّية',
    /acsFloorOrder\(floorsFound\)/.test(WIRING_SRC)
    && !/\[\.\.\.floorsFound\]\.sort\(\)/.test(WIRING_CODE));

console.log('\n== و٢ · أسماء الأدوار: غير فارغة، فريدة، وبلا سطحٍ كاذب ==');
(() => {
  const names = [];
  for (let i = 0; i < 50; i++) names.push(acsFloorName('F' + i, 50));
  chk('٥٠ اسماً كلّها نصوص غير فارغة',
      names.every(s => typeof s === 'string' && s.trim().length > 0
        && s !== 'undefined' && s !== 'null'),
      JSON.stringify(names.filter(s => !s || !String(s).trim())));
  chk('وكلّها فريدة — لا اسمان لدورين', new Set(names).size === 50,
      String(new Set(names).size));
  chk('والأرضي أرضيّ والأعلى سطح',
      names[0] === 'الأرضي' && names[49] === 'السطح',
      names[0] + ' / ' + names[49]);
  chk('ولا «السطح» في الوسط ولو مرّة',
      names.slice(0, 49).indexOf('السطح') < 0,
      String(names.slice(0, 49).indexOf('السطح')));
})();
chk('والعطل بعينه: F6 في مبنى من ١٢ دوراً ليس «السطح»',
    acsFloorName('F6', 12) === 'السادس' && acsFloorName('F11', 12) === 'السطح',
    acsFloorName('F6', 12) + ' / ' + acsFloorName('F11', 12));
chk('وفي مبنى من ٧ أدوار يبقى F6 سطحاً بحقّ',
    acsFloorName('F6', 7) === 'السطح', acsFloorName('F6', 7));
chk('وجدول الأسماء لم يعد يحمل «السطح» لرقمٍ ثابت',
    Object.keys(FLOOR_NAMES).every(k => FLOOR_NAMES[k] !== 'السطح'),
    JSON.stringify(FLOOR_NAMES));
chk('ولا يُعاد اسمٌ فارغ لأي رقم مهما كبر',
    [0, 6, 7, 11, 49, 99, 1000].every(i =>
      String(acsFloorName('F' + i, 0) || '').trim().length > 0),
    JSON.stringify([0, 6, 7, 11, 49, 99, 1000].map(i => acsFloorName('F' + i, 0))));
chk('ومفتاح غير قياسي لا يُنتج قيمة فارغة',
    acsFloorName('Fundefined', 3) === 'Fundefined' && acsFloorName('', 3) === '—',
    acsFloorName('Fundefined', 3) + ' / ' + acsFloorName('', 3));
chk('وacsFloorIndex يميّز المفتاح القياسي من غيره',
    acsFloorIndex('F12') === 12 && acsFloorIndex('F0') === 0
    && acsFloorIndex('Fundefined') === null && acsFloorIndex(null) === null);

/* البناء الفعلي: مبنى من ١٢ دوراً يُنتج اثني عشر مفتاحاً مرتّباً */
(() => {
  const m = smallModel();
  m.levels = []; m.floors = {};
  for (let i = 0; i < 12; i++) {
    m.levels.push({ index: i, template: 'f' + i });
    m.floors['f' + i] = { rooms: [{ id: 'r' + i, rect: [0, 0, 5, 4] }] };
  }
  const R = build(m);
  const keys = [...new Set(R.names.map(n => n.split('|')[1]))].filter(k => /^F\d+$/.test(k));
  chk('مبنى ١٢ دوراً يُبنى ومفاتيحه F0..F11',
      R.err === null && keys.length === 12, JSON.stringify(keys));
  chk('وترتيبها الطبيعي يطابق المبنى',
      acsFloorOrder(keys).join(',') === keysFor(12).join(','),
      acsFloorOrder(keys).join(','));
})();

// ═══════════════ ز · ما كان قائماً لم يتحرّك ═════════════════════════════════
console.log('\n== ز · SMALL و MEDIUM و LARGE: نفس العدد بالضبط ==');
/* الأرقام مرصودة قبل F-46 على نفس النماذج. أي حركة فيها تعني أن حدّاً جديداً
   لمس مبنًى قائماً — وهو ما يمنعه العقد صراحةً. */
[['SMALL', smallModel(), 14], ['MEDIUM', mediumModel(), 891],
 ['LARGE', prodModel(true), 2001], ['LARGE بلا index', prodModel(false), 2001]
].forEach(([label, m, want]) => {
  const R = build(m);
  chk((label + ' → ' + want + ' شبكة كما قبل الحدود').padEnd(46),
      R.err === null && R.meshes === want, R.meshes + ' / ' + want);
  chk((''.padEnd(46) + ' → ولا تدهور ولا قصّ'),
      R.err === null && R.summary.degraded === false
      && R.summary.capped_expansions === 0 && R.summary.suppressed_meshes === 0,
      JSON.stringify((R.summary || {}).degradation_reasons));
  chk((''.padEnd(46) + ' → وعدّاد المقبول يطابق العدد المبنيّ'),
      R.err === null && R.summary.accepted_objects === R.meshes,
      R.summary.accepted_objects + ' / ' + R.meshes);
});
(() => {
  const R = build(warehouseModel(120, 80, { clear: 12 }));
  chk('ومستودع ١٢٠×٨٠ المشحون: ٣٨٠٢ شبكة بلا تدهور',
      R.err === null && R.meshes === 3802 && R.summary.degraded === false,
      R.meshes + ' degraded=' + (R.summary || {}).degraded);
})();
(() => {
  const savedDetail = __ACS_SHARED.DETAIL;
  __ACS_SHARED.DETAIL = 0.5;
  const R = build(prodModel(false));
  __ACS_SHARED.DETAIL = savedDetail;
  chk('ومسار الجوال (DETAIL=0.5) يبقى كما كان بلا تدهور',
      R.err === null && R.meshes === 2001 && R.summary.degraded === false,
      R.meshes + ' degraded=' + (R.summary || {}).degraded);
})();
chk('وسجلّ العيوب واحد لا اثنان — لا آليّة موازية أُنشئت',
    typeof acsBuildDefectsReset === 'function'
    && typeof acsBuildDefect === 'function'
    && typeof acsBuildDefects === 'function'
    && acsCompileSummary().contract === SCENE_LIMITS.contract);

console.log('\n' + '─'.repeat(62));
console.log('PIXELS AND REAL WEBGL: measured in '
  + 'tests/remediation/test_apply_render_browser.js, not here');
console.log('SCENE LIMITS: %d passed, %d failed', pass, fail);
if (fail) process.exit(1);

}

main();
