# -*- coding: utf-8 -*-
"""الشاشة السوداء لنموذج مولَّد حيّ — علاج render-recovery/1.0.0.

البلاغ الإنتاجي: الواجهة حيّة، شجرة الطبقات ممتلئة (٥٦٤ جداراً · ٦ أدوار ·
٨٢ باباً · ٣٥ نافذة · ٢٤٣ نقطة كهرباء · ١٠٨ إنارة · ٢٦ كاميرا · ٤٤ تكييف ·
٧٨ سلامة · ١٧٢ أثاث · ١٨٨ عنصراً) — والمشهد أسود بالكامل.

الآلية، مثبتة بالحساب هنا لا بالظنّ:

  setModel كان يؤطّر الكاميرا هكذا:
      box    = new THREE.Box3().setFromObject(model)   ← كل شبكة، بلا فحص صلاحية
      bounds = box.getBoundingSphere()
      camera.position = center + (1.4R, 0.85R, 1.4R)   ← المسافة = 2.1546 R
  و**لا يمسّ camera.near/far إطلاقاً**: يبقيان على قيمتَي إنشاء الكاميرا في
  السطر `new THREE.PerspectiveCamera(52, aspect, 0.05, 6000)`.

  نتيجتان مباشرتان:
    1. سقف حجم مسكوت عنه: المشهد يخرج من مستوى القصّ عند نصف قطر ≈ 1902 م،
       لأن 2.1546R + R يتجاوز 6000.
    2. وهي الأهمّ: **إحداثيّة واحدة تالفة** بين مئات العناصر المولَّدة تكفي.
       نقطة كهرباء عند x=99999 ترفع نصف القطر من ٨٤ م إلى ٥٠ كم، فتصير الكاميرا
       على بُعد ١٠٧ كم بينما المستوى البعيد ٦ كم — فلا يتقاطع شيء مع الهرم
       ويُمسح الإطار أسود، والواجهة والعدّادات على حالها تماماً.

  عقد أمان المشهد (bounds_from_descriptors → camera_clip → frustum_contains)
  الذي بُني في هذه المرحلة نفسها كان موصولاً بمسار إعدادات الكاميرا وحده،
  ولم يكن موصولاً بمسار تحميل النموذج — وهو المسار الذي يعمل فعلاً عند الزائر.
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_pbr as P                                               # noqa: E402
import acs_generation as G                                        # noqa: E402

FIX = os.path.join(HERE, 'fixtures')
SHIPPED_FOV, SHIPPED_ASPECT = 52.0, 1.6
SHIPPED_NEAR, SHIPPED_FAR = 0.05, 6000.0        # سطر إنشاء الكاميرا المشحون
OLD_DIST_K = math.sqrt(1.4 ** 2 + 0.85 ** 2 + 1.4 ** 2)

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def load(name):
    with io.open(os.path.join(FIX, name), encoding='utf-8') as fh:
        return json.load(fh)


def descriptors(building, wall_h=None):
    """أوصاف الهندسة القانونية من نموذج — أربعة جدران لكل حيّز، ونقاطه وأثاثه.

    ليست محاكاةً للمصرِّف: هي التمثيل نفسه الذي يراه عقد الحدود (اسم بفواصل
    أنبوبية داخل مجموعة BUILDING، وصندوق عالمي) — وهو كل ما يحتاجه التأطير.
    """
    out = []
    wh = float(wall_h if wall_h is not None else building.get('wall_h') or 3.0)
    fh = float(building.get('floor_height') or 3.2)
    for li, lv in enumerate(building.get('levels') or []):
        base = li * fh
        tmpl = str(lv.get('template'))
        fdef = (building.get('floors') or {}).get(tmpl) or {}
        for r in (fdef.get('rooms') or []):
            x, z, w, d = [float(v) for v in r['rect']]
            for si, (mn, mx) in enumerate((
                    ([x, base, z], [x + w, base + wh, z + 0.2]),
                    ([x, base, z + d - 0.2], [x + w, base + wh, z + d]),
                    ([x, base, z], [x + 0.2, base + wh, z + d]),
                    ([x + w - 0.2, base, z], [x + w, base + wh, z + d]))):
                out.append({'is_mesh': True, 'parent_names': ['BUILDING'],
                            'name': 'WALL|F%d|%s|%d' % (li, r['id'], si),
                            'box': {'min': mn, 'max': mx}})
            for j, pt in enumerate(r.get('points') or []):
                px, pz = float(pt.get('x', x)), float(pt.get('z', z))
                out.append({'is_mesh': True, 'parent_names': ['BUILDING'],
                            'name': 'ELEC|F%d|%s|%d' % (li, r['id'], j),
                            'box': {'min': [px, base + 0.4, pz],
                                    'max': [px + 0.1, base + 0.5, pz + 0.1]}})
            for j, fu in enumerate(r.get('furniture') or []):
                fx, fz = float(fu.get('x', x)), float(fu.get('z', z))
                fw, fd = float(fu.get('w', 1)), float(fu.get('d', 1))
                out.append({'is_mesh': True, 'parent_names': ['BUILDING'],
                            'name': 'FURN|F%d|%s|%d' % (li, r['id'], j),
                            'box': {'min': [fx, base, fz],
                                    'max': [fx + fw, base + 0.9, fz + fd]}})
    return out


def old_camera(bounds):
    """تأطير setModel قبل العلاج، حرفياً: موضع من الحدود، وقصٌّ من الإنشاء."""
    R = bounds['radius']
    return {'position': [bounds['cx'] + R * 1.4, bounds['cy'] + R * 0.85,
                         bounds['cz'] + R * 1.4],
            'target': [bounds['cx'], bounds['cy'], bounds['cz']],
            'fov': SHIPPED_FOV, 'aspect': SHIPPED_ASPECT,
            'near': SHIPPED_NEAR, 'far': SHIPPED_FAR}


# ═════════════════════════ أ) الحيازة الحقيقية للنموذج المُبلَّغ ════════════
print('\n── أ · النموذج الكبير: حيازة مطابقة للعدّادات المبلَّغة ──')

BIG = load('live_large_generated.json')
OUT = load('live_large_generated_outlier.json')
prov = BIG.get('_provenance') or {}
census = prov.get('target_census') or {}

chk('the fixture states plainly that it is reconstructed, not captured',
    prov.get('kind', '').startswith('RECONSTRUCTED')
    and prov.get('captured_from_live_backend') is False)
chk('and that it was not hand-simplified until the failure went away',
    prov.get('hand_simplified') is False)

rooms = [r for fd in (BIG['floors'] or {}).values() for r in (fd['rooms'] or [])]
chk('it carries %d levels, as reported' % census.get('floors', 0),
    len(BIG['levels']) == census['floors'], str(len(BIG['levels'])))
chk('it carries %d wall segments (4 per space x %d spaces)'
    % (census['walls'], len(rooms)),
    len(rooms) * 4 == census['walls'], str(len(rooms) * 4))
POINTS = {}
for r in rooms:
    for pt in (r.get('points') or []):
        POINTS[pt['type']] = POINTS.get(pt['type'], 0) + 1
chk('the electrical point census matches (%d)' % census['electrical'],
    POINTS.get('outlet', 0) == census['electrical'], str(POINTS.get('outlet')))
chk('the lighting census matches (%d)' % census['lighting'],
    POINTS.get('light', 0) == census['lighting'], str(POINTS.get('light')))
chk('the camera census matches (%d)' % census['cameras'],
    POINTS.get('camera', 0) == census['cameras'], str(POINTS.get('camera')))
chk('the HVAC census matches (%d)' % census['hvac'],
    POINTS.get('ac', 0) == census['hvac'], str(POINTS.get('ac')))
chk('the safety census matches (%d)' % census['safety'],
    POINTS.get('smoke', 0) + POINTS.get('sprinkler', 0) == census['safety'])
chk('furniture and equipment censuses match (%d / %d)'
    % (census['furniture'], census['objects']),
    sum(len(r.get('furniture') or []) for r in rooms) == census['furniture']
    and sum(len(r.get('objects') or []) for r in rooms) == census['objects'])
chk('door and window censuses match (%d / %d)'
    % (census['doors'], census['windows']),
    sum(len(r.get('doors') or []) for r in rooms) == census['doors']
    and sum(len(r.get('windows') or []) for r in rooms) == census['windows'])

DESC = descriptors(BIG)
DESC_OUT = descriptors(OUT)
chk('the fixture yields hundreds of canonical descriptors (%d)' % len(DESC),
    len(DESC) > 1500, str(len(DESC)))
chk('THIS IS NOT AN EMPTY MODEL — every count above is non-zero',
    all(v > 0 for v in census.values()))


# ═════════════════ ب) العطل: أول حالة سيئة، محسوبة لا مخمَّنة ══════════════
print('\n── ب · تحديد أول حالة تنقلب فيها الصورة إلى السواد ──')

clean = P.bounds_from_descriptors(DESC)['bounds']
dirty = P.bounds_from_descriptors(DESC_OUT)['bounds']
chk('the clean large model has a sane radius (%s m)' % clean['radius'],
    clean['radius'] < 200)
chk('ONE stray coordinate inflates the radius to %s m' % dirty['radius'],
    dirty['radius'] > 40000, str(dirty['radius']))
chk('the old framing then puts the camera %.0f m away while far stays 6000 m'
    % (dirty['radius'] * OLD_DIST_K),
    dirty['radius'] * OLD_DIST_K > SHIPPED_FAR * 10)

fr_clean = P.frustum_contains(old_camera(clean), clean)
fr_dirty = P.frustum_contains(old_camera(dirty), dirty)
chk('OLD PATH · clean large model: the model IS in the frustum '
    '(so size alone was never the reported failure)', fr_clean['contains'])
chk('OLD PATH · one stray coordinate: the model is NOT in the frustum '
    '⇒ black viewport with a fully populated UI', not fr_dirty['contains'])
chk('the old path\'s silent size ceiling is R = far / (%.4f + 1) = %.0f m'
    % (OLD_DIST_K, SHIPPED_FAR / (OLD_DIST_K + 1)),
    abs(SHIPPED_FAR / (OLD_DIST_K + 1) - 1902.0) < 1.0)
chk('above that ceiling the old path loses the model too',
    not P.frustum_contains(
        old_camera({'cx': 0, 'cy': 0, 'cz': 0, 'radius': 46000.0}),
        {'cx': 0, 'cy': 0, 'cz': 0, 'radius': 46000.0})['contains'])
chk('the first bad state is therefore MODEL LOAD (camera reconciliation), '
    'before any PBR, post-processing or architectural-detail layer runs',
    not fr_dirty['contains'] and fr_clean['contains'])


# ═══════════════════════ ج) العقد المصحَّح والنتيجة ═════════════════════════
print('\n── ج · عقد الاسترداد: الحدود المحصّنة ومصالحة الكاميرا ──')

chk('the render-recovery contract is declared and versioned',
    P.RENDER_RECOVERY_CONTRACT == 'render-recovery/1.0.0')
chk('it declares its five symbols',
    set(P.RENDER_RECOVERY_SYMBOLS) == {'element_valid', 'robust_bounds',
                                       'fit_distance', 'camera_fit',
                                       'recovery_plan'})

rb_clean = P.robust_bounds(DESC)
rb_dirty = P.robust_bounds(DESC_OUT)
# الحيّز الذي يحمل النقطة الشاردة ينتمي إلى قالب يستعمله مستويان، فالنقطة
# الواحدة في المصدر تنتج وصفَين في المشهد. هذا بعينه ما يجعل خطأً مصدرياً
# واحداً يبدو أكبر مما هو في العدّادات — ويُحسب هنا كما هو لا كما نتمنّاه.
chk('NEW PATH · the stray element is excluded and named (2 scene instances '
    'from 1 source point, because its template serves 2 levels)',
    rb_dirty['diagnostics']['excluded_invalid_bounds'] == 2
    and any(i['code'] == 'RENDER_INVALID_ELEMENT' for i in rb_dirty['issues']),
    str(rb_dirty['diagnostics']['excluded_invalid_bounds']))
chk('NEW PATH · the radius is identical with and without the stray element',
    rb_clean['bounds']['radius'] == rb_dirty['bounds']['radius'],
    '%s vs %s' % (rb_clean['bounds']['radius'], rb_dirty['bounds']['radius']))
chk('the diagnostics report every field §7 asks for',
    set(rb_dirty['diagnostics']) >= {'canonical_mesh_count', 'included_in_bounds',
                                     'excluded_invalid_bounds',
                                     'max_element_extent', 'scene_radius',
                                     'outliers'})

fit_clean = P.camera_fit(rb_clean['bounds'], SHIPPED_FOV, SHIPPED_ASPECT)
fit_dirty = P.camera_fit(rb_dirty['bounds'], SHIPPED_FOV, SHIPPED_ASPECT)
chk('NEW PATH · the large model is in the frustum', fit_clean['camera_in_frustum'])
chk('NEW PATH · the model WITH the stray coordinate is also in the frustum '
    '— the reported failure is gone', fit_dirty['camera_in_frustum'])
chk('near and far are now derived per model, not frozen at 0.05 / 6000',
    fit_clean['camera']['far'] != SHIPPED_FAR
    and fit_clean['camera']['near'] != SHIPPED_NEAR)
chk('near is positive and strictly less than far',
    0 < fit_clean['camera']['near'] < fit_clean['camera']['far'])
chk('the camera target is the finite bounds centre, never a stale one',
    all(math.isfinite(v) for v in fit_clean['camera']['target']))

# سقف الحجم القديم لم يعد قائماً
for R in (500.0, 1902.0, 5000.0, 20000.0):
    b = {'cx': 0.0, 'cy': 0.0, 'cz': 0.0, 'radius': R}
    fit = P.camera_fit(b, SHIPPED_FOV, SHIPPED_ASPECT)
    chk('a %s m-radius model is framed correctly (old path failed above 1902 m)'
        % int(R), fit['camera_in_frustum'], str(fit['camera']))

chk('a legitimately huge building is NEVER excluded from its own bounds',
    P.robust_bounds([{'is_mesh': True, 'parent_names': ['BUILDING'],
                      'name': 'WALL|F0|big', 'box': {'min': [0, 0, 0],
                                                     'max': [400, 18, 300]}}]
                    )['diagnostics']['excluded_invalid_bounds'] == 0)
chk('only genuinely impossible geometry is excluded, and each exclusion says why',
    [P.element_valid({'box': {'min': m, 'max': x}})['reason'] for m, x in (
        ([0, 0, 0], [1, 3, 6]),
        ([float('nan'), 0, 0], [1, 1, 1]),
        ([0, 0, 0], [99999, 1, 1]),
        ([99999, 0, 0], [99999.2, .2, .2]),
        ([5, 5, 5], [1, 1, 1]))]
    == ['OK', 'NON_FINITE', 'EXTENT_ABSURD', 'COORDINATE_ABSURD', 'INVERTED_BOX'])
chk('an outlier that is still valid is REPORTED, not deleted',
    any(i['code'] == 'RENDER_BOUNDS_OUTLIER' for i in P.robust_bounds(
        [{'is_mesh': True, 'parent_names': ['BUILDING'], 'name': 'WALL|F0|a',
          'box': {'min': [0, 0, 0], 'max': [1, 1, 1]}}] * 8
        + [{'is_mesh': True, 'parent_names': ['BUILDING'], 'name': 'WALL|F0|big',
            'box': {'min': [0, 0, 0], 'max': [400, 10, 10]}}])['issues']))

chk('§12 · the sky dome, ground plane and every presentation group stay out of '
    'canonical bounds',
    P.robust_bounds(DESC + [
        {'is_mesh': True, 'name': 'SKY_DOME', 'parent_names': [],
         'box': {'min': [-45000, -45000, -45000], 'max': [45000, 45000, 45000]}},
        {'is_mesh': True, 'name': 'GROUND_PLANE', 'parent_names': [],
         'box': {'min': [-5000, -1, -5000], 'max': [5000, 0, 5000]}},
        {'is_mesh': True, 'name': 'PQ_CONTEXT_ground', 'parent_names': [],
         'box': {'min': [-900, -1, -900], 'max': [900, 0, 900]}},
        {'is_mesh': True, 'name': 'AD_tree_01', 'parent_names': ['PQ_CONTEXT'],
         'box': {'min': [-50, 0, -50], 'max': [-40, 12, -40]}},
    ])['bounds']['radius'] == rb_clean['bounds']['radius'])


# ══════════════════════════ د) الفتح الآمن والاسترداد ══════════════════════
print('\n── د · المعالجة اللاحقة تفشل مفتوحةً، والاسترداد دورة واحدة ──')

plan = P.recovery_plan({'canonical_meshes': 1500, 'draw_calls': 212,
                        'viewport_black': True, 'composer_active': True,
                        'materials_replaced': True})
chk('§14 · a black frame with geometry and draw calls triggers recovery',
    plan['needed'] and plan['steps'][0] == 'DISABLE_COMPOSER')
chk('§8 · disabling the composer is always the first step — a black composer '
    'is never preserved', plan['steps'][0] == 'DISABLE_COMPOSER')
chk('the full deterministic sequence is composer → materials → camera → base',
    plan['steps'] == ['DISABLE_COMPOSER', 'RESTORE_ENGINEERING_MATERIALS',
                      'REFIT_CAMERA', 'RENDER_BASE'])
chk('recovery is capped at exactly one cycle — no endless loop',
    plan['max_cycles'] == 1 and P.RR['max_recovery_cycles'] == 1)
chk('steps that cannot apply are skipped, not attempted blindly',
    P.recovery_plan({'canonical_meshes': 10, 'draw_calls': 5,
                     'viewport_black': True, 'composer_active': False,
                     'materials_replaced': False})['steps']
    == ['REFIT_CAMERA', 'RENDER_BASE'])
chk('a visible viewport never triggers recovery',
    not P.recovery_plan({'canonical_meshes': 10, 'draw_calls': 5,
                         'viewport_black': False})['needed'])
chk('zero draw calls is reported as its own condition, not "recovered"',
    P.recovery_plan({'canonical_meshes': 10, 'draw_calls': 0,
                     'viewport_black': True})['reason'] == 'NO_DRAW_CALLS')
chk('an empty scene is not mistaken for a render failure',
    P.recovery_plan({'canonical_meshes': 0, 'draw_calls': 0,
                     'viewport_black': True})['reason'] == 'NO_CANONICAL_GEOMETRY')


# ═══════════════════════ هـ) الطبقة المشحونة فعلاً ═════════════════════════
print('\n── هـ · ما شُحن في الصفحة، لا ما نُوي شحنه ──')

# بعد F-09: ما شُحن صار وحدات ES تحت public/app/، والقشرة لا تحمل شيفرة.
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import app_source as _APPSRC                                      # noqa: E402
PAGE = _APPSRC.app_text()
assert len(PAGE) > 1000000, 'the application code did not load'
chk('setModel now reconciles the camera through the canonical contract',
    'acsReconcileCamera' in PAGE
    and PAGE.index('function setModel') < PAGE.rindex('acsReconcileCamera'))
# سلطةُ حدودٍ واحدة (مقيس في CI على live_large_generated_outlier: كانت
# renderDiagnosticsDetail().model_bounds بنصف قطر ٥٠ كم من اتّحاد Box3 ساذج
# بينما الكاميرا مُصالَحة على الحدود المحصَّنة نفسها التي استبعدت الشاردة).
_BRIDGE = PAGE.split('function _pqSceneBounds(){')[1].split('\n\n')[0]
chk('_pqSceneBounds — the bounds every consumer reads (ground context, SSAO, '
    'camera presets, diagnostics) — is the ROBUST layer, not a second naive '
    'Box3 union', '_pqRobustSceneBounds()' in _BRIDGE
    and 'expandByObject' not in _BRIDGE)
chk('and it keeps the shape its consumers read (radius, centre, member_count)',
    'member_count' in _BRIDGE and 'radius' in _BRIDGE)
chk('setModel no longer frames from a raw unfiltered Box3 as its primary path',
    PAGE.split('function setModel')[1].split('buildFloors()')[0]
    .index('acsReconcileCamera')
    < PAGE.split('function setModel')[1].split('buildFloors()')[0]
    .index('new THREE.Box3().setFromObject(model)'))
chk('even the fallback path now assigns near and far — the original defect '
    'cannot survive there either',
    'camera.near=Math.max(0.05,bounds.r*0.002)' in PAGE
    and 'camera.far=Math.max(200,bounds.r*8)' in PAGE)
chk('the shipped camera is still constructed with the same defaults, so the '
    'test above describes the real starting state',
    'new THREE.PerspectiveCamera(52,innerWidth/innerHeight,0.05,6000)' in PAGE)
for sym in ('pqElementValid', 'pqRobustBounds', 'pqFitDistance', 'pqCameraFit',
            'pqRecoveryPlan'):
    chk('the browser mirror ships %s' % sym, sym in PAGE)
chk('§13 · the read-only verification bridge ships',
    'window.ACS.verifyVisibleModel' in PAGE
    and 'exposes_coordinates:false' in PAGE)
chk('§13 · it reports every field the contract asks for',
    all(k in PAGE for k in ('model_loaded:', 'canonical_meshes:', 'draw_calls:',
                            'triangles:', 'bounds_valid:', 'camera_in_frustum:',
                            'clip_valid:', 'webgl_context_ok:', 'pixels_visible:',
                            'fallback_used:')))
chk('§14 · the auto-recovery runs after two animation frames, once',
    'requestAnimationFrame(()=>requestAnimationFrame(' in PAGE
    and 'acsRecoverBlackViewport' in PAGE)
chk('§11 · resource pressure is measured and warned about, never "fixed" by '
    'dropping geometry',
    'window.ACS.renderResourcePressure' in PAGE
    and 'correctness unaffected' in PAGE)
chk('§15 · render failure classes exist and are separate from transport classes',
    'RENDER_BLACK_VIEWPORT' in PAGE and 'ACS_TRANSPORT_CLASSES' in PAGE
    and 'window.ACS.lastFailure' in PAGE)
chk('§15 · a black viewport is classified RENDER_*, never NETWORK_DNS',
    'acsFail(rec.recovered?ACS_FAIL.RENDER_POSTPROCESS_ERROR' in PAGE
    and 'ACS_FAIL.RENDER_BLACK_VIEWPORT' in PAGE)
chk('engine state was still not promoted to globals to make any of this work',
    'window.scene' not in PAGE and 'window.camera' not in PAGE
    and 'window.renderer' not in PAGE)


# ═════════════ و) §16 تغطية المتطلّبات و §17 سلامة العدد ══════════════════
print('\n── و · لم يضع بندٌ تحت اسم اقتصاد المخرج، ولا تكرار صامت ──')

PROMPT = ("مستودع من ستة أدوار: مناطق تخزين والتقاط وتغليف واستقبال وشحن، "
          "مكاتب إدارة، ورشة صيانة، استراحة موظفين، ممرات، فرز.")
cov = G.coverage_report(PROMPT, BIG)
chk('the coverage report returns the four counts §16 asks for',
    set(cov) >= {'requested_count', 'represented_count', 'unresolved_count',
                 'omitted_count'})
chk('every requested item in this prompt is represented in the model (%d/%d)'
    % (cov['represented_count'], cov['requested_count']),
    cov['unresolved_count'] == 0, str(cov['unresolved']))
chk('coverage is measured against the model itself, not against a promise',
    cov['requested_count'] > 5 and cov['coverage_ratio'] == 1.0)
chk('an item genuinely absent from the model IS reported unresolved',
    G.coverage_report('أضف مهبطاً للطائرات المروحية', BIG)['unresolved_count'] >= 1)
chk('the compact-output rule never mentions removing or reducing requirements',
    not any(w in G.COMPACT_RULE for w in ('احذف', 'قلّل عدد', 'تجاهل')))
chk('and it explicitly protects per-instance data the client asked for',
    'إلا إذا طلب العميل' in G.COMPACT_RULE)

dup = G.duplication_report(BIG)
chk('the duplication report counts elements per array',
    dup['element_totals']['points'] == sum(len(r.get('points') or [])
                                           for r in rooms))
chk('this fixture contains no exact duplicate within any space',
    dup['exact_duplicates_within_room'] == 0,
    str(dup['duplicate_sites'][:3]))
chk('no room id is duplicated across the model',
    dup['duplicate_room_ids'] == [], str(dup['duplicate_room_ids']))
chk('§17 · a shared floor template used by several levels is reported as REUSE, '
    'not as duplication',
    dup['template_count'] == 3 and dup['level_count'] == 6
    and max(dup['template_reuse'].values()) == 2)
chk('a real duplicate IS detected when one exists',
    G.duplication_report({'levels': [{'template': 't'}], 'floors': {'t': {'rooms': [
        {'id': 'a', 'points': [{'type': 'light', 'x': 1, 'z': 1},
                               {'type': 'light', 'x': 1, 'z': 1}]}]}}}
    )['exact_duplicates_within_room'] == 1)
chk('nothing is deduplicated automatically — the report says so in words',
    'never deduplicated automatically' in dup['note'])

print('\n──────────────────────────────────────────────')
print('LIVE RENDER RECOVERY: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
