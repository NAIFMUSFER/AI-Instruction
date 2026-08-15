# -*- coding: utf-8 -*-
"""F-07 — امتداد لوح الدور: لا صفيحة طائرة، ولا كمّية تتغيّر (يُغلق KI-3).

يعيد إنتاج العيب ثم يثبت زواله:

  منذ المرحلة 1 كان لوح كل دور يُبنى على مستطيل الموقع كاملاً
  (`slabStrips(0,0,site.w,site.d,holes)` في الصفحة، و
  `bld.add_box(site["w"]/2, ..., site["w"], 0.15, site["d"], ...)` في
  `acs_compiler.build_level`). فوق مبنًى أصغر من قطعة الأرض يبرز اللوح خارج
  غلاف المبنى بلا شيء تحت حوافّه، وهذا بالضبط ما يُقرأ «سقفاً/بلاطة طائرة».
  الاصطلاح كان مُبقًى ومثبَّتاً بخطّ أساس المرحلة 4، والامتداد الصحيح محسوباً
  ومُبلَّغاً في التشخيص فقط — لا مطبَّقاً.

  الآن: PHASE10_FOOTPRINT_PLATE. امتداد كل لوح = اتحاد بصمات غرف الدور نفسه،
  محسوباً بعقد الامتداد الوحيد `acs_pbr.plate_rect` (توأمه في المتصفّح
  `pqPlateRect`) — لا حاسب امتداد ثانٍ — وفراغات النوى تُقصّ منه، ومستوى
  الموقع العرضي يبقى منفصلاً وبمقاس الموقع.

الأقسام:
  أ) السياسة معلَنة ومُسنَدة: اسمها، واسم سابقتها، وما ثبّتها، وسببها.
  ب) عقد الامتداد نفسه: اتحاد الغرف، والموقع بديلٌ أخير معلَن، وUNRESOLVED.
  ج) العيب مُعاد إنتاجه على كل تجهيزة: القاعدة القديمة تسقط، والجديدة تنجح.
  د) ما يبعثه `build_level` فعلاً: لا هندسة لوح تتجاوز بصمة دورها.
  هـ) مستوى الموقع منفصل وبمقاس الموقع، وليس لوح دور.
  و) الفراغات ما زالت مقصوصة — مساحةً وموضعاً.
  ز) القانونية: مستطيلات الغرف ومساحاتها والنموذج كلّه متطابق قبل وبعد.
  ح) تكافؤ بايثون/جافاسكربت: نصّ الصفحة يستدعي العقد نفسه، ولا يبقى النصّ القديم.
"""
import copy
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_arch as ARCH                                           # noqa: E402
import acs_compiler as C                                          # noqa: E402
import acs_ingest as ING                                          # noqa: E402
import acs_pbr as P                                               # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def rd(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8') as fh:
        return fh.read()


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True)


FIXDIR = os.path.join(HERE, 'fixtures', 'plate')
FIXTURES = {}
for _p in sorted(glob.glob(os.path.join(FIXDIR, '*.json'))):
    if os.path.basename(_p).startswith('mesh_baseline'):
        continue
    with open(_p, 'r', encoding='utf-8') as fh:
        _m = json.load(fh)
    FIXTURES[_m['_fixture']['id']] = _m

TOL = 1e-6


class Cap(object):
    """بديل Builder يلتقط كل صندوق يُبعث بدل تصديره — لا ملفّ ولا glTF."""

    def __init__(self):
        self.boxes = []

    def add_box(self, cx, cy, cz, ex, ey, ez, mat, name):
        if ex <= 0 or ey <= 0 or ez <= 0:
            return
        self.boxes.append({'c': (cx, cy, cz), 'e': (ex, ey, ez),
                           'mat': mat, 'name': name,
                           'rect': (cx - ex / 2.0, cz - ez / 2.0, ex, ez)})

    def slabs(self, fkey=None):
        pre = 'FLOOR|%s|slab|' % fkey if fkey else 'FLOOR|'
        return [b for b in self.boxes
                if b['name'].startswith(pre) and '|slab|' in b['name']]

    def site_planes(self):
        return [b for b in self.boxes if b['name'].startswith('SITE|')]


def defaults_of(m):
    return {'site': m['site'], 'wall_h': m.get('wall_h', 3.0),
            'wall_t': m.get('wall_t', 0.15), 'industrial': False}


def voids_of(m, idx):
    try:
        a = ARCH.compile_architecture(m, 'bld_0', None, 0)
    except Exception:
        return []
    return [v['rect'] for v in (a.get('voids') or [])
            if v.get('level_index') == idx]


def union_of(rooms):
    rs = [r['rect'] for r in rooms]
    x0 = min(r[0] for r in rs)
    z0 = min(r[1] for r in rs)
    x1 = max(r[0] + r[2] for r in rs)
    z1 = max(r[1] + r[3] for r in rs)
    return [x0, z0, x1 - x0, z1 - z0]


def emit_level(m, lvl):
    """يشغّل build_level الحقيقي ويعيد (الصناديق، مستطيل البصمة، الفراغات)."""
    cap = Cap()
    fdef = m['floors'][lvl['template']]
    holes = voids_of(m, lvl['index'])
    C.build_level(cap, lvl, fdef, lvl['index'] * m['floor_height'],
                  defaults_of(m), 'F%d' % lvl['index'], holes)
    return cap, union_of(fdef['rooms']), holes


print('\n== أ · THE POLICY IS DECLARED AND PROVENANCED, NOT SILENT ==')
POL = P.PLATE_POLICY
chk('the new plate policy is named', POL['policy'] == 'PHASE10_FOOTPRINT_PLATE')
chk('the policy it replaces is recorded by name',
    POL['previous_policy'] == 'PHASE1_SITE_WIDE_PLATE')
chk('what pinned the previous policy is recorded',
    POL['previous_pinned_by'] == 'PHASE4_GOLDEN_BASELINE')
chk('the reason for the change is recorded in the same object',
    isinstance(POL['reason'], str) and len(POL['reason']) > 60
    and 'KI-3' in POL['reason'])
chk('the policy names ONE extent source, so there is no second calculator',
    POL['extent_source'] == 'plate_rect'
    and POL['level_slab_extent'] == 'LEVEL_ROOM_UNION'
    and POL['level_slab_fallback'] == 'SITE_FALLBACK')
chk('the policy declares the site plane separate and site-sized',
    POL['site_plane_separate'] is True
    and POL['site_plane_extent'] == 'SITE_RECT')
chk('the policy declares itself presentational: no model, no areas, no '
    'quantities, no hash',
    POL['presentation_only'] is True
    and POL['changes_canonical_model'] is False
    and POL['changes_room_rects'] is False
    and POL['changes_areas'] is False
    and POL['changes_quantities'] is False
    and POL['changes_model_hash'] is False)
chk('the policy accessor hands out a copy, so a caller cannot mutate it',
    P.plate_policy() == POL and P.plate_policy() is not POL)
chk('the canonical transform contract already declares the same rule',
    'floating plate' in P.SPEC['transform_contract']['plate_rule']
    and "union of that level's own room footprints"
    in P.SPEC['transform_contract']['plate_rule'])

print('\n== ب · THE SINGLE EXTENT CONTRACT ==')
chk('rooms present ⇒ the extent is the level room union, declared as such',
    P.plate_rect([[20, 14, 12, 9], [34, 14, 8, 9]], [0, 0, 60, 40])['source']
    == 'LEVEL_ROOM_UNION')
chk('the union is exact, not padded',
    P.plate_rect([[20, 14, 12, 9], [34, 14, 8, 9]],
                 [0, 0, 60, 40])['rect'] == [20.0, 14.0, 22.0, 9.0])
chk('no rooms ⇒ the site is used, and the fallback is DECLARED not silent',
    P.plate_rect([], [0, 0, 30, 24])['source'] == 'SITE_FALLBACK'
    and P.plate_rect([], [0, 0, 30, 24])['rect'] == [0.0, 0.0, 30.0, 24.0])
chk('neither rooms nor site ⇒ UNRESOLVED, never an invented rectangle',
    P.plate_rect([], None)['valid'] is False
    and P.plate_rect([], None)['rect'] is None
    and P.plate_rect([], None)['issues'][0]['code']
    == 'ALIGN_TRANSFORM_UNRESOLVED')
chk('degenerate room rectangles are dropped, not turned into extent',
    P.plate_rect([[0, 0, 0, 5], [1, 1, 'x', 2]],
                 [0, 0, 9, 9])['source'] == 'SITE_FALLBACK')

print('\n== ج · THE DEFECT REPRODUCED ON EVERY FIXTURE ==')
chk('the regression fixtures ship with the tests', len(FIXTURES) >= 5,
    '%d fixture(s)' % len(FIXTURES))
chk('every fixture declares its provenance honestly and none claims to be a '
    'captured production model',
    all(m['_fixture']['provenance'] == 'SYNTHETIC_REGRESSION'
        and m['_fixture']['reconstructed'] is False
        for m in FIXTURES.values()))
for _name in sorted(FIXTURES):
    _m = FIXTURES[_name]
    _site = [0.0, 0.0, float(_m['site']['w']), float(_m['site']['d'])]
    _sa = _site[2] * _site[3]
    for _lvl in _m['levels']:
        _u = union_of(_m['floors'][_lvl['template']]['rooms'])
        _ua = _u[2] * _u[3]
        _new = P.plate_rect(
            [r['rect'] for r in _m['floors'][_lvl['template']]['rooms']],
            _site)['rect']
        if _name == 'footprint_equals_site':
            chk('%s L%d: the footprint EQUALS the site, so the plate stays '
                'site-sized — the policy shrinks nothing it should not'
                % (_name, _lvl['index']),
                _new == _site and abs(_ua - _sa) < TOL)
            continue
        chk('%s L%d: the OLD site-wide rule overhung the footprint by %.1fx — '
            'this is the reported floating plate'
            % (_name, _lvl['index'], _sa / _ua), _sa / _ua > 1.5,
            'site=%s union=%s' % (_site, _u))
        chk('%s L%d: the NEW rule equals the level room union exactly'
            % (_name, _lvl['index']),
            [round(v, 6) for v in _new] == [round(v, 6) for v in _u],
            '%s vs %s' % (_new, _u))

print('\n== د · WHAT build_level ACTUALLY EMITS ==')
for _name in sorted(FIXTURES):
    _m = FIXTURES[_name]
    for _lvl in _m['levels']:
        cap, u, holes = emit_level(_m, _lvl)
        sl = cap.slabs('F%d' % _lvl['index'])
        chk('%s L%d: the level emitted slab geometry at all'
            % (_name, _lvl['index']), len(sl) >= 1, str(len(sl)))
        out = [b for b in sl
               if b['rect'][0] < u[0] - TOL or b['rect'][1] < u[1] - TOL
               or b['rect'][0] + b['rect'][2] > u[0] + u[2] + TOL
               or b['rect'][1] + b['rect'][3] > u[1] + u[3] + TOL]
        chk('%s L%d: NO slab geometry extends beyond the level room-footprint '
            'union' % (_name, _lvl['index']), out == [],
            json.dumps([b['rect'] for b in out]))
        chk('%s L%d: every slab keeps the declared 0.15 m thickness and sits '
            'at its own level elevation, applied exactly once'
            % (_name, _lvl['index']),
            all(abs(b['e'][1] - 0.15) < TOL for b in sl)
            and all(abs(b['c'][1]
                        - (_lvl['index'] * _m['floor_height'] - 0.075)) < TOL
                    for b in sl))
        chk('%s L%d: every slab is tagged FLOOR|F%d|slab|k, never SITE'
            % (_name, _lvl['index'], _lvl['index']),
            all(b['name'].startswith('FLOOR|F%d|slab|' % _lvl['index'])
                for b in sl))
        if _name != 'footprint_equals_site':
            chk('%s L%d: the emitted plate is strictly smaller than the site '
                'rectangle' % (_name, _lvl['index']),
                max(b['rect'][2] for b in sl) < float(_m['site']['w']) - TOL
                or max(b['rect'][3] for b in sl) < float(_m['site']['d']) - TOL)
# مقاومة التفاهة: القاعدة القديمة كانت لتسقط في نفس الفحص أعلاه
_vm = FIXTURES['villa_small_on_large_plot']
_vu = union_of(_vm['floors']['g']['rooms'])
_old_rect = (0.0, 0.0, float(_vm['site']['w']), float(_vm['site']['d']))
chk('the check above is not vacuous: the OLD site-wide plate WOULD have '
    'failed it', _old_rect[2] > _vu[0] + _vu[2] + TOL
    or _old_rect[3] > _vu[1] + _vu[3] + TOL)

print('\n== هـ · THE SITE PLANE IS SEPARATE AND STILL SITE-SIZED ==')
for _name in sorted(FIXTURES):
    _m = FIXTURES[_name]
    cap = Cap()
    C.build_site_plane(cap, defaults_of(_m))
    sp = cap.site_planes()
    chk('%s: exactly one site/ground presentation plane is emitted' % _name,
        len(sp) == 1, str(len(sp)))
    if len(sp) == 1:
        b = sp[0]
        chk('%s: the site plane spans the FULL site rectangle' % _name,
            abs(b['rect'][2] - float(_m['site']['w'])) < TOL
            and abs(b['rect'][3] - float(_m['site']['d'])) < TOL
            and abs(b['rect'][0]) < TOL and abs(b['rect'][1]) < TOL,
            json.dumps(b['rect']))
        chk('%s: the site plane is NOT a level slab — separate tag, separate '
            'elevation, below every level plate' % _name,
            b['name'] == 'SITE|GROUND|plane|0'
            and '|slab|' not in b['name']
            and b['c'][1] < -0.075)
        chk('%s: the level slabs never carry the SITE tag' % _name,
            all(not x['name'].startswith('SITE|')
                for lv in _m['levels']
                for x in emit_level(_m, lv)[0].slabs()))
_nosite = dict(FIXTURES['l_shaped_footprint'])
_nosite = copy.deepcopy(_nosite)
_nosite['site'] = {'w': 0, 'd': 0}
_cap0 = Cap()
chk('a model with no usable site rectangle gets NO invented site plane',
    C.build_site_plane(_cap0, defaults_of(_nosite)) is False
    and _cap0.site_planes() == [])

print('\n== و · VOIDS ARE STILL SUBTRACTED ==')
_sv = FIXTURES['stair_void_footprint']
_lv1 = [lv for lv in _sv['levels'] if lv['index'] == 1][0]
cap, u, holes = emit_level(_sv, _lv1)
sl = cap.slabs('F1')
chk('the stair core really produces a void on the upper level',
    len(holes) == 1, json.dumps(holes))
chk('the void forces the plate to be cut into several strips',
    len(sl) > 1, str(len(sl)))
_h = holes[0]
_hcx, _hcz = _h[0] + _h[2] / 2.0, _h[1] + _h[3] / 2.0
chk('no slab strip covers the centre of the void — the opening is really open',
    not any(b['rect'][0] < _hcx < b['rect'][0] + b['rect'][2]
            and b['rect'][1] < _hcz < b['rect'][1] + b['rect'][3]
            for b in sl))
_area = sum(b['rect'][2] * b['rect'][3] for b in sl)
chk('the slab area equals the footprint area MINUS the void area exactly '
    '(%.3f m²)' % _area,
    abs(_area - (u[2] * u[3] - _h[2] * _h[3])) < 1e-6,
    'strips=%.6f expected=%.6f' % (_area, u[2] * u[3] - _h[2] * _h[3]))
_lv0 = [lv for lv in _sv['levels'] if lv['index'] == 0][0]
cap0, u0, holes0 = emit_level(_sv, _lv0)
chk('the ground level, which has no void, is still ONE whole plate',
    len(cap0.slabs('F0')) == 1 and holes0 == [])
_direct = P.slab_strips(u[0], u[1], u[2], u[3], holes)
_emit = [[b['rect'][0], b['rect'][1], b['rect'][2], b['rect'][3]] for b in sl]
# المقارنة على عدد الشرائح وترتيبها وقيمها ضمن 1e-9 — الفرق الوحيد الممكن هو
# دورة مركز/امتداد داخل add_box، لا اختلاف منطق.
chk('the emitted strips ARE the shared contract output, strip for strip',
    len(_direct) == len(_emit)
    and all(abs(a - b) < 1e-9
            for da, db in zip(_direct, _emit) for a, b in zip(da, db)),
    '%s vs %s' % (_direct, _emit))
chk('a hole outside the plate changes nothing',
    P.slab_strips(0, 0, 10, 10, [[50, 50, 2, 2]]) == [[0.0, 0.0, 10.0, 10.0]])
chk('no holes ⇒ exactly one strip covering the whole plate',
    P.slab_strips(2, 3, 10, 8, []) == [[2.0, 3.0, 10.0, 8.0]])

print('\n== ز · THE QUANTITIES STAY CANONICAL ==')
for _name in sorted(FIXTURES):
    _m = FIXTURES[_name]
    before = canon(_m)
    before_rects = canon({lv['template']:
                          [r['rect'] for r in _m['floors'][lv['template']]
                           ['rooms']] for lv in _m['levels']})
    before_areas = canon({lv['template']:
                          [round(r['rect'][2] * r['rect'][3], 9)
                           for r in _m['floors'][lv['template']]['rooms']]
                          for lv in _m['levels']})
    before_hash = ING.canonical_json(_m)
    work = copy.deepcopy(_m)
    for lv in work['levels']:
        emit_level(work, lv)
        C.build_site_plane(Cap(), defaults_of(work))
    after_rects = canon({lv['template']:
                         [r['rect'] for r in work['floors'][lv['template']]
                          ['rooms']] for lv in work['levels']})
    after_areas = canon({lv['template']:
                         [round(r['rect'][2] * r['rect'][3], 9)
                          for r in work['floors'][lv['template']]['rooms']]
                         for lv in work['levels']})
    chk('%s: every room rectangle is byte-identical after compilation' % _name,
        after_rects == before_rects)
    chk('%s: every room area is byte-identical after compilation' % _name,
        after_areas == before_areas)
    chk('%s: the whole model is byte-identical — compilation reads, never '
        'writes' % _name,
        canon(work) == before and ING.canonical_json(work) == before_hash)

print('\n== ح · PYTHON AND THE BROWSER SHARE ONE CONTRACT ==')
src = rd('acs_compiler.py')
# F-09 — شيفرة المتصفّح لم تعد داخل الصفحة: تُقرأ من وحداتها عبر المصدر الواحد
# tools/app_source.py. البحث عن رمز يجري على الشيفرة (app_text) لا على القشرة،
# فلا يمرّ رمزٌ لأنه صادف وجوده في العلامة.
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import app_source as AS                                           # noqa: E402
page = AS.app_text()
chk('the browser compiler lives in a shipped module, not in the page shell',
    'pqPlateRect(' not in AS.shell() and 'pqPlateRect(' in page)
chk('the Python compiler imports the shared contract instead of computing its '
    'own extent',
    'import acs_pbr as PBR' in src and 'PBR.plate_rect(' in src
    and 'PBR.slab_strips(' in src)
chk('the OLD site-wide plate line is gone from the Python compiler',
    'site["w"], 0.15, site["d"], "floor", "FLOOR|%s|slab|0" % fkey'
    not in src)
chk('the OLD site-wide plate call is gone from the shipped page',
    'slabStrips(0,0,site.w,site.d,holes)' not in page)
chk('the shipped page derives the plate from the same contract',
    'pqPlateRect((fdef.rooms||[]).map(r=>r.rect),[0,0,site.w,site.d])' in page
    and 'slabStrips(_pr[0],_pr[1],_pr[2],_pr[3],holes)' in page)
chk('the page ships the policy object and its predecessor, so the browser can '
    'report the provenance too',
    'PQ_PLATE_POLICY' in page and 'PHASE10_FOOTPRINT_PLATE' in page
    and 'PHASE1_SITE_WIDE_PLATE' in page)
chk('the alignment reporter measures the RENDERED plate, not the convention',
    'rendered_plate' in page and 'avoided_site_overhang_m' in page)
chk('the browser site plane is declared separate and outside the building '
    'group', 'acs_site_plane' in page and 'in_building_group:false' in page)
_js = page[page.index('function slabStrips('):]
_js = _js[:_js.index('\nfunction compile(data){')]
chk('the browser strip routine still subtracts holes and is not a stub',
    'hs.some(' in _js and 'if(!hs.length) return [[x0,z0,W,D]];' in _js)

print('\n' + '─' * 62)
print('PLATE EXTENT: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
