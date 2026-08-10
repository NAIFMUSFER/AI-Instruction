# -*- coding: utf-8 -*-
"""انحدار الشاشة السوداء — «أقلع المحرّك بنجاح والإطار أسود».

هذا الملف يعيد إنتاج العطل الإنتاجي بالحساب الصريح، ثم يثبت أن القاعدة
المصحَّحة تزيله. آلية العطل بالكامل:

  1. حدود المشهد كانت تشمل كل شبكة في المشهد، ومنها قبّة السماء (مقياس 45000)،
     فصار نصف القطر ≈ 22500 م بدل أمتار المبنى.
  2. إعدادات الكاميرا تضع الكاميرا على بُعد radius × distance_factor،
     أي عشرات الآلاف من الأمتار.
  3. مستوى القصّ البعيد يبقى 6000 ⇒ المبنى خارج هرم الرؤية تماماً.
  4. الكاميرا تتجاوز نصف قطر القبّة (22500) ⇒ تصير خارج قبّة السماء،
     وموادّها BackSide فلا تُرسم.
  5. لا خلفية ولا هندسة داخل الهرم ⇒ يُمسح الإطار إلى الأسود.
     المحرّك «مُقلِع» تماماً بينما الإطار أسود — وهو ما بلَّغ عنه الإنتاج.

القاعدة المصحَّحة: الحدود من الهندسة القانونية وحدها، ثم إعادة ملاءمة
مستويي القصّ وقصّ المسافة داخل القبّة، ثم تأكيد التقاطع فعلياً.
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'phase9'))
sys.path.insert(0, HERE)

import acs_pbr as P                                               # noqa: E402
import acs_archdetail as A                                        # noqa: E402

# ---------------------------------------------------------------- preflight --
# لا يُسمح بانفجار AttributeError عميق حين تصل شجرة نصف مدمَجة: يُبلَّغ العطل
# باسم الرمز الناقص وبالإجراء المطلوب، لأن هذا بالضبط ما حدث في الإنتاج
# (acs_pbr has no attribute 'CLIP' من ملف اختبار أحدث من الوحدة).
_REQUIRED = ('VB', 'CLIP', 'VIEWPORT_CONTRACT', 'bounds_member',
             'bounds_from_descriptors', 'camera_clip', 'frustum_contains',
             'material_safe')
_missing = [s for s in _REQUIRED if not hasattr(P, s)]
if _missing:
    print('BLACK VIEWPORT REGRESSION: CANNOT RUN — PARTIALLY MERGED TREE')
    print('  acs_pbr.py is missing: %s' % ', '.join(_missing))
    print('  expected viewport contract: %s'
          % P.SPEC.get('viewport_contract_version', '<not declared>'))
    print('  this test and acs_pbr.py come from different deliveries.')
    print('  run: python3 tools/check_integration.py   for the full report')
    sys.exit(1)
_declared = P.SPEC.get('viewport_contract_version')
if _declared and P.VIEWPORT_CONTRACT != _declared:
    print('BLACK VIEWPORT REGRESSION: CANNOT RUN — CONTRACT MISMATCH')
    print('  python layer: %s   specification: %s'
          % (P.VIEWPORT_CONTRACT, _declared))
    sys.exit(1)
import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_ad_fixtures as LF                                      # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


SKY_SCALE = 45000.0
SKY = {'name': 'SKY_DOME', 'is_mesh': True, 'parent_names': [],
       'box': {'min': [-SKY_SCALE / 2] * 3, 'max': [SKY_SCALE / 2] * 3}}
SKY_UNNAMED = {'name': '', 'is_mesh': True, 'parent_names': [],
               'box': SKY['box']}
GROUND = {'name': 'GROUND_PLANE', 'is_mesh': True, 'parent_names': [],
          'user_data': {'presentation_context': True},
          'box': {'min': [-60, -0.2, -60], 'max': [60, 0.0, 60]}}
CONTEXT = {'name': 'AD_CONTEXT_PLANE0', 'is_mesh': True,
           'parent_names': ['AD_CONTEXT'],
           'user_data': {'visual_only': True, 'presentation_context': True},
           'box': {'min': [-200, -1, -200], 'max': [200, -0.9, 200]}}
DEBUG = {'name': 'COORD_DEBUG_MARKER', 'is_mesh': True, 'parent_names': [],
         'user_data': {'acs_debug_only': True},
         'box': {'min': [0, 0, 0], 'max': [1, 1, 1]}}


def building_descriptors(model_name):
    """أوصاف شبكات قانونية من نموذج قانوني حقيقي (فراغاته وارتفاعه)."""
    models = LF.all_models()
    prj = AU.create_project(copy.deepcopy(models[model_name]), 'bld_0',
                            'IMPORT', None)
    src = D.sources(prj)
    h = float(models[model_name].get('wall_h') or 3.0)
    out = []
    for i, s in enumerate(src['arch']['spaces']):
        r = s.get('rect') or [0, 0, 5, 4]
        lv = 0
        out.append({'name': 'WALL|F%d|%s|%d' % (lv, s.get('id') or i, i),
                    'is_mesh': True, 'parent_names': ['BUILDING'],
                    'box': {'min': [r[0], 0.0, r[1]],
                            'max': [r[0] + r[2], h, r[1] + r[3]]}})
    return prj, out


def old_rule_bounds(objects):
    """القاعدة القديمة: كل شبكة تدخل الحدود — بما فيها قبّة السماء."""
    mins = [None] * 3
    maxs = [None] * 3
    for o in objects:
        if not o.get('is_mesh'):
            continue
        b = o['box']
        for i in range(3):
            mins[i] = b['min'][i] if mins[i] is None \
                else min(mins[i], b['min'][i])
            maxs[i] = b['max'][i] if maxs[i] is None \
                else max(maxs[i], b['max'][i])
    size = [maxs[i] - mins[i] for i in range(3)]
    return {'cx': (mins[0] + maxs[0]) / 2, 'cy': (mins[1] + maxs[1]) / 2,
            'cz': (mins[2] + maxs[2]) / 2, 'min_y': mins[1],
            'radius': max(size) / 2}


print('\n== A · THE DEFECT REPRODUCED BY EXPLICIT CALCULATION ==')
prj_v, villa = building_descriptors('villa_glazed')
scene_objects = [SKY, SKY_UNNAMED, GROUND, CONTEXT, DEBUG] + villa
old_b = old_rule_bounds(scene_objects)
chk('the old rule inflates the radius to sky scale (%.0f m)'
    % old_b['radius'], old_b['radius'] > 20000,
    'radius=%.1f' % old_b['radius'])
old_cam = P.camera('EXTERIOR_HERO', old_b)['camera']
old_dist = math.dist(old_cam['position'],
                     [old_b['cx'], old_b['cy'], old_b['cz']])
chk('the preset camera is then pushed tens of kilometres out (%.0f m)'
    % old_dist, old_dist > 40000, 'distance=%.0f' % old_dist)
chk('the camera ends up OUTSIDE the sky dome — the dome stops drawing',
    old_dist > P.CLIP['sky_dome_radius_m'])
new_res = P.bounds_from_descriptors(scene_objects)
真 = new_res['bounds']
old_frustum = P.frustum_contains(
    {'position': old_cam['position'],
     'target': [真['cx'], 真['cy'], 真['cz']],
     'fov': old_cam['fov'], 'aspect': 16 / 9.0,
     'near': 0.05, 'far': 6000.0}, 真)
chk('with the page far plane at 6000 the building is OUT of the frustum',
    old_frustum['contains'] is False
    and old_frustum['issues'][0]['code'] == 'PQ_MODEL_OUT_OF_FRUSTUM')
chk('nothing is left to draw: no dome, no model — an all-black frame',
    old_frustum['within_clip'] is False and old_dist > 22500)

print('\n== B · THE CORRECTED BOUNDS RULE ==')
chk('the sky dome is refused by name', not P.bounds_member(SKY)['included'])
chk('an UNNAMED sky-sized mesh is refused too (canonical membership rule)',
    not P.bounds_member(SKY_UNNAMED)['included']
    and P.bounds_member(SKY_UNNAMED)['reason'] == 'NOT_CANONICAL_GEOMETRY')
chk('the presentation ground plane is refused',
    not P.bounds_member(GROUND)['included'])
chk('an AD_ context plane is refused',
    not P.bounds_member(CONTEXT)['included'])
chk('a debug marker is refused', not P.bounds_member(DEBUG)['included'])
chk('canonical building geometry is accepted',
    P.bounds_member(villa[0])['included']
    and P.bounds_member(villa[0])['reason'] == 'CANONICAL_ROOT')
chk('a canonically tagged mesh with no BUILDING parent is accepted',
    P.bounds_member({'name': 'FLOOR|F0|r1|plate', 'is_mesh': True,
                     'parent_names': []})['reason'] == 'CANONICAL_TAG')
chk('the corrected radius is building scale, not sky scale',
    new_res['valid'] and 真['radius'] < 200,
    'radius=%s' % 真['radius'])
chk('the corrected member count equals the canonical mesh count',
    new_res['member_count'] == len(villa))
chk('a scene with no canonical geometry reports it instead of inventing '
    'bounds (this is what made the old boot test false-pass)',
    P.bounds_from_descriptors([SKY, GROUND, CONTEXT])['valid'] is False
    and P.bounds_from_descriptors([SKY])['issues'][0]['code']
    == 'PQ_BOUNDS_UNAVAILABLE')

print('\n== C · EVERY PRESET NOW FRAMES THE MODEL — ALL MODELS ==')
MODELS = ('villa_glazed', 'warehouse', 'hotel', 'clinic',
          'apartment_balconies')
PRESETS = sorted(P.CAMERAS) + sorted(A.CAMERAS_ARCH)
for name in MODELS:
    prj, desc = building_descriptors(name)
    res = P.bounds_from_descriptors([SKY, GROUND, CONTEXT] + desc)
    b = res['bounds']
    bad = []
    for preset in PRESETS:
        cam = A.camera(preset, b)
        assert cam['valid'], preset
        clip = P.camera_clip(b, cam['camera']['position'])
        fr = P.frustum_contains(
            {'position': clip['clip']['position'],
             'target': cam['camera']['target'], 'fov': cam['camera']['fov'],
             'aspect': 16 / 9.0, 'near': clip['clip']['near'],
             'far': clip['clip']['far']}, b)
        if not (fr['contains'] and clip['clip']['inside_sky_dome']
                and clip['clip']['contains_model']
                and 0 < clip['clip']['near'] < clip['clip']['far']):
            bad.append(preset)
    chk('%s: all %d camera presets keep the model inside the frustum, the '
        'clip planes and the sky dome' % (name, len(PRESETS)),
        not bad, ','.join(bad[:4]))

print('\n== D · CLIP-PLANE AND DISTANCE SAFETY (§8) ==')
b = P.bounds_from_descriptors(villa)['bounds']
cl = P.camera_clip(b, [0, 20000, 54000])
chk('an absurd camera distance is clamped inside the sky dome',
    cl['clip']['clamped'] is True and cl['clip']['inside_sky_dome'] is True
    and cl['issues'][0]['code'] == 'PQ_CAMERA_CLAMPED')
chk('near stays positive and far always contains the model',
    cl['clip']['near'] > 0 and cl['clip']['contains_model'] is True)
chk('near is never pushed past the model front face',
    all(P.camera_clip(b, [b['cx'], b['cy'] + d, b['cz'] + d])['clip']['near']
        < d for d in (5, 25, 120, 900)))
chk('far never exceeds the declared ceiling',
    P.camera_clip(b, [0, 1e9, 1e9])['clip']['far'] <= P.CLIP['far_max'])
chk('a degenerate camera position falls back to a framing distance',
    P.camera_clip(b, None)['clip']['contains_model'] is True)
chk('a camera looking away from the model is reported, not hidden',
    P.frustum_contains({'position': [b['cx'], b['cy'], b['cz'] + 50],
                        'target': [b['cx'], b['cy'], b['cz'] + 900],
                        'fov': 45, 'aspect': 1.6, 'near': 0.1,
                        'far': 3000}, b)['facing'] is False)
chk('a camera inside the model still counts as intersecting',
    P.frustum_contains({'position': [b['cx'], b['cy'], b['cz']],
                        'target': [b['cx'] + 1, b['cy'], b['cz']],
                        'fov': 60, 'aspect': 1.6, 'near': 0.05,
                        'far': 500}, b)['contains'] is True)

print('\n== E · MATERIAL SAFETY FAILS OPEN, NEVER TO BLACK (§7) ==')
for mid in sorted(P.MATERIALS):
    r = P.material(mid)
    chk('shipped material %s is safe to apply' % mid,
        P.material_safe(r['material'])['safe'] is True)
for mid in sorted(A.MATERIALS):
    r = A.material(mid)
    chk('shipped presentation material %s is safe to apply' % mid,
        P.material_safe(r['material'])['safe'] is True)
bad_cases = (
    ({'id': 'x', 'base_color': '#ffffff', 'opacity': 0.0},
     'FULLY_TRANSPARENT'),
    ({'id': 'x', 'base_color': 'not-a-colour'}, 'INVALID_COLOR'),
    ({'id': 'x', 'base_color': '#ffffff', 'roughness': float('nan')},
     'INVALID_ROUGHNESS'),
    ({'id': 'x', 'base_color': '#ffffff', 'metalness': 9.0},
     'INVALID_METALNESS'),
)
for m, reason in bad_cases:
    r = P.material_safe(m)
    chk('an unsafe material (%s) falls open to the engineering material'
        % reason,
        r['safe'] is False and reason in r['reasons']
        and r['fallback'] == 'ENGINEERING_MATERIAL'
        and r['issues'][0]['code'] == 'PQ_MATERIAL_FAIL_OPEN')

print('\n== F · CANONICAL IMMUTABILITY ACROSS THE REMEDIATION (§11) ==')
for name in MODELS:
    prj, desc = building_descriptors(name)
    before = D._canon(prj['model'])
    h0, r0 = prj['model_hash'], prj['current_revision']
    b = P.bounds_from_descriptors(desc)['bounds']
    for preset in PRESETS:
        cam = A.camera(preset, b)
        cl = P.camera_clip(b, cam['camera']['position'])
        P.frustum_contains({'position': cl['clip']['position'],
                            'target': cam['camera']['target'],
                            'fov': cam['camera']['fov'], 'aspect': 1.6,
                            'near': cl['clip']['near'],
                            'far': cl['clip']['far']}, b)
    for mid in sorted(P.MATERIALS):
        P.material_safe(P.material(mid)['material'])
    P.bounds_member(SKY)
    chk('%s: canonical bytes, hash and revision unchanged by every viewport '
        'operation' % name,
        D.verify_no_mutation(before, prj)['unchanged'] is True
        and prj['model_hash'] == h0 and prj['current_revision'] == r0)

print('\n== G · THE SPEC RECORDS THE RULE, NOT JUST THE CODE ==')
CANON = json.load(open(os.path.join(ROOT, 'acs_pbr.json'), encoding='utf-8'))
chk('viewport bounds exclusions are declared canonically',
    'SKY_DOME' in CANON['viewport_bounds']['excluded_object_names']
    and 'GROUND_PLANE' in CANON['viewport_bounds']['excluded_object_names']
    and CANON['viewport_bounds']['require_canonical_membership'] is True)
chk('the camera clip contract is declared canonically',
    0 < CANON['camera_clip']['max_distance_ratio_of_sky'] < 1
    and CANON['camera_clip']['far_max'] <= 60000)
chk('the four remediation issue codes are declared',
    all(c in CANON['issue_codes'] for c in (
        'PQ_BOUNDS_UNAVAILABLE', 'PQ_CAMERA_CLAMPED',
        'PQ_MODEL_OUT_OF_FRUSTUM', 'PQ_MATERIAL_FAIL_OPEN')))
chk('none of them is a blocking code — a viewport warning never blanks the '
    'application',
    not any(c in CANON['blocking_issue_codes'] for c in (
        'PQ_BOUNDS_UNAVAILABLE', 'PQ_CAMERA_CLAMPED',
        'PQ_MODEL_OUT_OF_FRUSTUM', 'PQ_MATERIAL_FAIL_OPEN')))

print('\n──────────────────────────────────────────────')
print('BLACK VIEWPORT REGRESSION: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
