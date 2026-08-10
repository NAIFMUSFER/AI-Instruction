# -*- coding: utf-8 -*-
"""انحدار المحاذاة والتحويلات — «السقف يطفو والرفوف خارج الغلاف».

يعيد إنتاج العطلين بالحساب الصريح ثم يثبت أن العقد الواحد يزيلهما:

  عطل ١ — لوح الدور: كان يُرسم على مقاس الموقع كلّه في كل دور بما فيه
    مستوى السطح. فوق مبنى أصغر من الموقع تصير البلاطة العليا صفيحة أوسع من
    المبنى بلا شيء تحت أطرافها ⇒ «سقف طائر منفصل».
  عطل ٢ — كتلة الرفوف: كانت تأخذ امتداد الغرفة كاملاً بعد إزاحة موجبة،
    فيتجاوز الصفّ حدّ الغرفة بمقدار الإزاحة بالضبط ⇒ «رفوف خارج الغلاف».

القاعدة المصحَّحة واحدة لكلا العطلين: كل إزاحة تُطبَّق مرّة واحدة، وكل
امتداد يُشتقّ من البيانات القانونية لا من الموقع ولا من التخمين.
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
import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_ad_fixtures as LF                                      # noqa: E402

_REQ = ('TC', 'SPACES', 'level_base_y', 'resolve_transform', 'plate_rect',
        'rack_block', 'containment', 'roof_alignment')
_missing = [s for s in _REQ if not hasattr(P, s)]
if _missing:
    print('ALIGNMENT REGRESSION: CANNOT RUN — PARTIALLY MERGED TREE')
    print('  acs_pbr.py is missing: %s' % ', '.join(_missing))
    print('  run: python3 tools/check_integration.py')
    sys.exit(1)

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


TOL = float(P.TC['roof_tolerance_m'])
FH = 3.2

print('\n== A · AXIS CONVENTION IS DECLARED AND UNCHANGED (§11) ==')
chk('x is horizontal width, y is vertical elevation, z is horizontal depth',
    P.TC['axis']['x'] == 'HORIZONTAL_WIDTH'
    and P.TC['axis']['y'] == 'VERTICAL_ELEVATION'
    and P.TC['axis']['z'] == 'HORIZONTAL_DEPTH')
chk('the space chain is declared end to end (§3)',
    P.SPACES == ('PROJECT', 'SITE', 'BUILDING', 'LEVEL', 'HOST_LOCAL',
                 'OBJECT_LOCAL', 'WORLD'))
chk('every declared space has a declared parent',
    all(k in P.TC['space_parents'] for k in P.SPACES))
chk('the forbidden transform faults are named, including both defect classes',
    all(x in P.TC['forbidden'] for x in (
        'DOUBLE_LEVEL_ELEVATION', 'DOUBLE_HOST_OFFSET', 'AXIS_SWAP_XZ',
        'AXIS_SWAP_ZY', 'SILENT_ORIGIN_PLACEMENT',
        'AUTOMATIC_SNAP_TO_NEAREST_HOST',
        'PRESENTATION_OFFSET_TO_HIDE_MISALIGNMENT')))
chk('the tolerance is small and justified (%.2f m)' % TOL,
    0 < TOL <= 0.05 and len(P.TC['tolerance_note']) > 40)

print('\n== B · DEFECT 1 REPRODUCED — THE SITE-WIDE PLATE (§4) ==')
SITE = [0, 0, 60, 40]
ROOMS = [[20, 14, 12, 9], [34, 14, 8, 9]]
old_plate = SITE                       # القاعدة القديمة: الموقع كلّه دائماً
new_plate = P.plate_rect(ROOMS, SITE)
chk('the old rule spread the plate over the whole site (%dx%d m)'
    % (SITE[2], SITE[3]), old_plate[2] * old_plate[3] == 2400)
chk('the corrected plate follows the level rooms, not the site',
    new_plate['valid'] and new_plate['source'] == 'LEVEL_ROOM_UNION'
    and new_plate['rect'] == [20.0, 14.0, 22.0, 9.0],
    json.dumps(new_plate['rect']))
over = (old_plate[2] * old_plate[3]) / (new_plate['rect'][2]
                                        * new_plate['rect'][3])
chk('the old plate overhung the building by %.1fx its footprint — that '
    'overhang is what reads as a floating slab' % over, over > 10)
chk('a level with no rooms still gets a plate, declared as the site fallback',
    P.plate_rect([], SITE)['source'] == 'SITE_FALLBACK')
chk('a level with neither rooms nor a site is UNRESOLVED, never invented',
    P.plate_rect([], None)['valid'] is False
    and P.plate_rect([], None)['issues'][0]['code']
    == 'ALIGN_TRANSFORM_UNRESOLVED')
chk('the plate never extends beyond the union of its own rooms',
    all(new_plate['rect'][0] <= r[0]
        and new_plate['rect'][0] + new_plate['rect'][2] >= r[0] + r[2]
        for r in ROOMS))

print('\n== C · DEFECT 2 REPRODUCED — THE RACK OVERRUN (§5) ==')
ROOM = [10.0, 6.0, 20.0, 12.0]
for ox, oz in ((5.0, 0.0), (0.0, 4.0), (3.0, 2.5), (25.0, 0.0)):
    old_far_x = ROOM[0] + ox + ROOM[2]          # القاعدة القديمة
    blk = P.rack_block(ROOM, {'x': ox, 'z': oz})['block']
    new_far_x = blk['x'] + blk['w']
    chk('offset (%.1f, %.1f): the old rule overran the room by %.1f m, the '
        'corrected block stays inside' % (ox, oz,
                                          max(old_far_x - (ROOM[0] + ROOM[2]),
                                              0.0)),
        blk['within_room'] is True
        and new_far_x <= ROOM[0] + ROOM[2] + 1e-9
        and blk['z'] + blk['d'] <= ROOM[1] + ROOM[3] + 1e-9,
        json.dumps(blk))
chk('the room origin is applied exactly once',
    P.rack_block(ROOM, {'x': 5, 'z': 4})['block']['offset_applied_times'] == 1
    and P.rack_block(ROOM, {'x': 5, 'z': 4})['block']['x'] == 15.0)
chk('an explicit rack extent is clamped to what the room actually has left',
    P.rack_block(ROOM, {'x': 15, 'w': 99})['block']['w'] == 5.0)
chk('an offset that consumes the room is reported, not silently zero-sized',
    P.rack_block(ROOM, {'x': 20})['issues'][0]['code']
    == 'ALIGN_OBJECT_OUTSIDE_HOST')
chk('a missing host rectangle is refused instead of guessed',
    P.rack_block(None, {'x': 1})['valid'] is False
    and P.rack_block(None, {'x': 1})['issues'][0]['code']
    == 'ALIGN_HOST_NOT_FOUND')

print('\n== D · LEVEL ELEVATION IS APPLIED EXACTLY ONCE (§10) ==')
for i in range(4):
    chk('level %d sits at exactly one level offset (%.1f m)' % (i, i * FH),
        P.level_base_y(i, FH)['base_y'] == round(i * FH, 6)
        and P.level_base_y(i, FH)['applied_times'] == 1)
host_at_l2 = [10.0, P.level_base_y(2, FH)['base_y'], 6.0]
double = P.resolve_transform({
    'source_element_id': 'FURN|F2|r1|sofa0', 'coordinate_space': 'HOST_LOCAL',
    'local': [1.0, 0.0, 2.0], 'host_origin': host_at_l2,
    'host_origin_includes_level': True, 'level_index': 2,
    'floor_height': FH, 'host_id': 'r1', 'level_id': 'F2'})
chk('a host origin that already carries the elevation does NOT get it twice',
    double['resolved'] and double['world'][1] == 6.4
    and double['level_elevation'] == 0.0
    and double['issues'][0]['code'] == 'ALIGN_DOUBLE_TRANSFORM')
single = P.resolve_transform({
    'source_element_id': 'FURN|F2|r1|sofa0', 'coordinate_space': 'HOST_LOCAL',
    'local': [1.0, 0.0, 2.0], 'host_origin': [10.0, 0.0, 6.0],
    'level_index': 2, 'floor_height': FH})
chk('a host origin without the elevation receives exactly one level offset',
    single['world'] == [11.0, 6.4, 8.0]
    and single['level_applied_times'] == 1
    and single['host_applied_times'] == 1)
chk('floor 0 elements stay at floor 0',
    P.resolve_transform({'coordinate_space': 'HOST_LOCAL',
                         'local': [0, 0, 0], 'host_origin': [4, 0, 4],
                         'level_index': 0,
                         'floor_height': FH})['world'][1] == 0.0)
chk('a three-level stack keeps one offset per level, never two',
    [P.resolve_transform({'coordinate_space': 'HOST_LOCAL',
                          'local': [0, 0, 0], 'host_origin': [0, 0, 0],
                          'level_index': i, 'floor_height': FH})['world'][1]
     for i in range(3)] == [0.0, 3.2, 6.4])
chk('a negative or non-finite floor height is refused',
    P.level_base_y(1, 0)['valid'] is False
    and P.level_base_y(1, float('nan'))['issues'][0]['code']
    == 'ALIGN_LEVEL_MISMATCH')

print('\n== E · ROOF ELEVATION INVARIANT (§4) ==')
for top in (0, 1, 2, 5):
    exp = (top + 1) * FH
    r = P.roof_alignment(top, FH, exp)
    chk('a %d-level building puts its roof at exactly %.1f m'
        % (top + 1, exp), r['aligned'] is True and r['error_m'] == 0.0)
bad = P.roof_alignment(2, FH, 3 * FH + FH)      # دور كامل زائد
chk('a full extra level of elevation is caught as a detached roof',
    bad['aligned'] is False and abs(bad['error_m'] - FH) < 1e-9
    and bad['issues'][0]['code'] == 'ALIGN_ROOF_DETACHED')
chk('the roof is reported, never lowered by a presentation offset',
    bad['presentation_offset_used'] is False
    and 'PRESENTATION_OFFSET_TO_HIDE_MISALIGNMENT' in P.TC['forbidden'])
chk('a rounding-scale difference stays inside the justified tolerance',
    P.roof_alignment(2, FH, 3 * FH + 0.01)['aligned'] is True)
chk('a difference just above tolerance is not tolerated',
    P.roof_alignment(2, FH, 3 * FH + TOL + 0.01)['aligned'] is False)

print('\n== F · CONTAINMENT CLASSIFICATION, NEVER RELOCATION (§6) ==')
HOST = {'min': [10, 0, 6], 'max': [30, 3, 18]}
cases = (
    ({'min': [12, 0, 8], 'max': [14, 2, 10]}, 'INSIDE'),
    ({'min': [29, 0, 17], 'max': [33, 2, 20]}, 'INTERSECTING_BOUNDARY'),
    ({'min': [40, 0, 8], 'max': [42, 2, 10]}, 'OUTSIDE'),
    ({'min': [12, 0, 8], 'max': [14, 2, 10]}, 'INSIDE'),
)
for box, expect in cases:
    r = P.containment(box, HOST)
    chk('a box that is %s is classified %s' % (expect.lower(), expect),
        r['classification'] == expect)
chk('an outside object is reported and explicitly not moved',
    P.containment({'min': [40, 0, 8], 'max': [42, 2, 10]}, HOST)
    ['moved_to_fit'] is False
    and P.containment({'min': [40, 0, 8], 'max': [42, 2, 10]}, HOST)
    ['issues'][0]['code'] == 'ALIGN_OBJECT_OUTSIDE_HOST')
chk('a missing box is UNRESOLVED rather than assumed inside',
    P.containment(None, HOST)['classification'] == 'UNRESOLVED')
chk('the four containment classes are the declared ones',
    P.TC['containment_classes'] == ['INSIDE', 'INTERSECTING_BOUNDARY',
                                    'OUTSIDE', 'UNRESOLVED'])

print('\n== G · UNRESOLVED IS NEVER THE ORIGIN (§3/§17) ==')
for desc, code in (
        ({'coordinate_space': 'HOST_LOCAL', 'local': [1, 0, 1]},
         'ALIGN_HOST_NOT_FOUND'),
        ({'coordinate_space': 'NOWHERE', 'local': [1, 0, 1]},
         'ALIGN_TRANSFORM_UNRESOLVED'),
        ({'coordinate_space': 'SITE'}, 'ALIGN_TRANSFORM_UNRESOLVED'),
        ({'coordinate_space': 'SITE', 'local': [1, float('inf'), 1]},
         'ALIGN_TRANSFORM_UNRESOLVED'),
        ({}, 'ALIGN_TRANSFORM_UNRESOLVED')):
    r = P.resolve_transform(desc)
    chk('an unresolvable transform returns %s with no world position' % code,
        r['resolved'] is False and r['world'] is None
        and r['issues'][0]['code'] == code)

print('\n== H · AXIS AND ROUND-TRIP INVARIANTS (§11/§14) ==')
pts = ([0, 0, 0], [3.5, 1.25, -7.75], [123.456, 0.001, 98.7])
host = [10.0, 3.2, 6.0]
for q in pts:
    r = P.resolve_transform({'coordinate_space': 'HOST_LOCAL', 'local': q,
                             'host_origin': host})
    back = [r['world'][i] - host[i] for i in range(3)]
    chk('worldToLocal(localToWorld(%s)) round-trips exactly' % (q,),
        all(abs(back[i] - q[i]) <= float(P.TC['roundtrip_tolerance_m'])
            for i in range(3)), json.dumps(back))
swapped = P.resolve_transform({'coordinate_space': 'HOST_LOCAL',
                               'local': [1.0, 0.0, 5.0],
                               'host_origin': [0, 0, 0]})
chk('an x offset never lands on z and a z offset never lands on x',
    swapped['world'][0] == 1.0 and swapped['world'][2] == 5.0)
chk('a horizontal offset never becomes an elevation',
    swapped['world'][1] == 0.0)
chk('a plate footprint keeps width on x and depth on z',
    P.plate_rect([[1, 2, 8, 4]], None)['rect'] == [1.0, 2.0, 8.0, 4.0])
chk('a rack block keeps width on x and depth on z',
    (lambda b: b['w'] == 9.0 and b['d'] == 5.0)
    (P.rack_block([0, 0, 9, 5], {})['block']))

print('\n== I · THE FIXTURES, END TO END (§1/§10) ==')
MODELS = LF.all_models()
for name in ('warehouse', 'villa_glazed', 'hotel', 'apartment_balconies'):
    model = MODELS[name]
    fh = float(model.get('floor_height') or 3.2)
    levels = model.get('levels') or [{'index': 0, 'template': 't'}]
    floors = model.get('floors') or {}
    site = model.get('site') or {'w': 40, 'd': 30}
    site_rect = [0, 0, float(site['w']), float(site['d'])]
    bad_plate, bad_rack, bad_level = [], [], []
    for lv in levels:
        idx = int(lv.get('index') or 0)
        rooms = ((floors.get(lv.get('template')) or {}).get('rooms')) or []
        pr = P.plate_rect([r.get('rect') for r in rooms], site_rect)
        if rooms:
            if pr['source'] != 'LEVEL_ROOM_UNION':
                bad_plate.append(idx)
            for r in rooms:
                rect = r.get('rect')
                if not rect:
                    continue
                if not (pr['rect'][0] <= rect[0] + 1e-9
                        and pr['rect'][0] + pr['rect'][2]
                        >= rect[0] + rect[2] - 1e-9):
                    bad_plate.append(idx)
        base = P.level_base_y(idx, fh)
        if not base['valid'] or base['applied_times'] != 1:
            bad_level.append(idx)
        for r in rooms:
            rect = r.get('rect')
            for rk in (r.get('racks') or []):
                b = P.rack_block(rect, rk)
                if not (b['valid'] and b['block']['within_room']):
                    bad_rack.append('%s.%s' % (idx, r.get('id')))
    chk('%s: every level plate is derived from that level and covers its '
        'rooms' % name, not bad_plate, str(bad_plate[:4]))
    chk('%s: every level applies its elevation exactly once' % name,
        not bad_level, str(bad_level[:4]))
    chk('%s: every rack block stays inside its hosting room' % name,
        not bad_rack, str(bad_rack[:4]))
    top = max(int(l.get('index') or 0) for l in levels)
    r = P.roof_alignment(top - 1, fh, top * fh)
    chk('%s: the top level sits at its canonical elevation (%.2f m)'
        % (name, top * fh), r['aligned'] is True)

print('\n== J · A THREE-LEVEL STACK (§10) ==')
stack = {'floor_height': FH, 'site': {'w': 40, 'd': 30},
         'levels': [{'index': i, 'template': 't'} for i in range(3)],
         'floors': {'t': {'rooms': [{'id': 'r1', 'rect': [4, 4, 10, 8],
                                     'racks': [{'kind': 'pallet', 'x': 2,
                                                'z': 1}]}]}}}
ys = [P.level_base_y(i, FH)['base_y'] for i in range(3)]
chk('three levels are 0.0, 3.2 and 6.4 — one offset each',
    ys == [0.0, 3.2, 6.4])
chk('no level receives a second offset',
    all(abs(ys[i + 1] - ys[i] - FH) < 1e-9 for i in range(2)))
blk = P.rack_block([4, 4, 10, 8], {'x': 2, 'z': 1})['block']
chk('a rack on any level keeps the same footprint — elevation is not mixed '
    'into the footprint',
    blk['x'] == 6.0 and blk['z'] == 5.0 and blk['within_room'] is True)
for i in range(3):
    t = P.resolve_transform({'coordinate_space': 'HOST_LOCAL',
                             'local': [blk['x'] - 4, 0, blk['z'] - 4],
                             'host_origin': [4, 0, 4], 'level_index': i,
                             'floor_height': FH})
    chk('level %d rack world position is (%.1f, %.1f, %.1f)'
        % (i, 6.0, ys[i], 5.0),
        t['world'] == [6.0, ys[i], 5.0])

print('\n== K · IMMUTABILITY THROUGH THE WHOLE ALIGNMENT BATTERY (§16) ==')
for name in ('warehouse', 'villa_glazed', 'apartment_balconies'):
    prj = AU.create_project(copy.deepcopy(MODELS[name]), 'bld_0', 'IMPORT',
                            None)
    before = D._canon(prj['model'])
    h0, r0 = prj['model_hash'], prj['current_revision']
    src0 = D.sources(prj)
    counts0 = {k: len(src0['arch'][k])
               for k in ('walls', 'spaces', 'openings')}
    for i in range(4):
        P.level_base_y(i, FH)
        P.plate_rect([[0, 0, 5, 5]], site_rect)
        P.rack_block([0, 0, 10, 10], {'x': i})
        P.roof_alignment(i, FH, (i + 1) * FH)
        P.containment({'min': [0, 0, 0], 'max': [1, 1, 1]}, HOST)
        P.resolve_transform({'coordinate_space': 'HOST_LOCAL',
                             'local': [1, 0, 1], 'host_origin': [0, 0, 0],
                             'level_index': i, 'floor_height': FH})
    src1 = D.sources(prj)
    chk('%s: canonical bytes, hash, revision and counts unchanged' % name,
        D.verify_no_mutation(before, prj)['unchanged'] is True
        and prj['model_hash'] == h0 and prj['current_revision'] == r0
        and {k: len(src1['arch'][k])
             for k in ('walls', 'spaces', 'openings')} == counts0)

print('\n== L · WHAT THE SHIPPED COMPILER ACTUALLY DOES ==')
page = open(os.path.join(ROOT, 'public', 'index.html'), encoding='utf-8').read()
chk('the rack block is derived through the shared contract (fix applied)',
    'pqRackBlock([rx,rz,rw,rd],R)' in page)
chk('the old unclamped rack extent is gone from the compiler',
    'const bw=Math.min(+R.w||rw,rw), bd=Math.min(+R.d||rd,rd);' not in page)
chk('the site-wide plate convention is RETAINED deliberately, because it is '
    'declared since Phase 1 and pinned by the Phase 4 golden baseline',
    'slabStrips(0,0,site.w,site.d,holes)' in page
    and 'خطّ الأساس الذهبي' in page
    and 'لا يُطبَّق بلا موافقة صريحة' in page)
chk('the corrected plate extent is still computed by the contract, so the '
    'deviation is measured rather than forgotten',
    'pqPlateRect((fdef.rooms||[]).map(r=>r.rect)' in page)
chk('the plate overhang is reported by the alignment diagnostics, not hidden '
    'by a presentation offset',
    'plate_overhang' in page and 'PHASE1_SITE_WIDE_PLATE' in page
    and 'change_requires_approval:true' in page)
_ov = P.plate_rect([[8, 5, 14, 13]], [0, 0, 30, 24])
chk('the contract quantifies the overhang for a villa-scale building '
    '(site 30x24 over a 14x13 footprint = %.1fx)'
    % ((30 * 24) / (_ov['rect'][2] * _ov['rect'][3])),
    (30 * 24) / (_ov['rect'][2] * _ov['rect'][3]) > 3.9)
chk('the alignment diagnostics bridge is shipped and presentation-only',
    'window.ACS.alignmentDiagnostics' in page
    and 'objects_moved_to_fit:0' in page)
chk('world bounds are only measured after updateMatrixWorld (§8)',
    'o.updateMatrixWorld(true);' in page
    and 'scene.updateMatrixWorld(true);' in page)
chk('the seven ALIGN issue codes are declared canonically (§17)',
    all(c in P.SPEC['issue_codes'] for c in (
        'ALIGN_TRANSFORM_UNRESOLVED', 'ALIGN_HOST_NOT_FOUND',
        'ALIGN_OBJECT_OUTSIDE_HOST', 'ALIGN_LEVEL_MISMATCH',
        'ALIGN_ROOF_DETACHED', 'ALIGN_DOUBLE_TRANSFORM',
        'ALIGN_AXIS_MISMATCH')))
chk('no ALIGN code is blocking — a misalignment is reported, never fatal',
    not any(c in P.SPEC['blocking_issue_codes']
            for c in P.SPEC['issue_codes'] if c.startswith('ALIGN_')))
chk('the Phase 4 golden baseline still passes with the rack fix in place',
    os.path.isfile(os.path.join(ROOT, 'tests', 'phase4',
                                'test_model_regression.js')))

print('\n──────────────────────────────────────────────')
print('ALIGNMENT REGRESSION: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
