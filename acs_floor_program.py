"""Per-floor programs and target sizes from a confirmed brief program.

A program confirmed in step 01 (acs_brief_reader, schema acs.brief-program/1)
lists each floor's own rooms, with target net sizes where the brief gave them.
This module turns that program into:

* per-floor requirement rows (``room_count_by_level``, ``ensuite_bedroom_count_by_level``)
  with deterministic ids, the same rows the step-01 option cards send
  (public/app/core/floor-program.mjs; a parity test keeps them equal);
* a deterministic zone manifest for the bounded planner: one floor template per
  distinct floor program, every room of that floor as a zone carrying its
  Arabic name and target size, and the stair/elevator core pre-placed at the
  same rectangle on every floor when the brief states its position;
* compact, server-built program context for the layout repair and the
  openings stage (only the floor a call works on);
* review findings with Arabic messages: room counts per floor (where no
  requirement row measures them), floors drawn alike although their programs
  differ, target sizes and wet rooms that do not stack.

Target sizes: a room's rectangle area is compared with its target area. Beyond
the advisory tolerance the review notes it; beyond the blocking tolerance it
blocks approval. A size the brief gives as approximate («نحو»، «تقريبًا») has a
wider stated tolerance. Every threshold is a planning assumption, not a
regulation. Revisions without a confirmed program are not read here.
"""
from __future__ import annotations

from collections import Counter
from itertools import permutations
import json
import math
import re

FLOOR_NOT_FITTED = 'PLAN_PROGRAM_FLOOR_NOT_FITTED_L'   # + floor index: the fallback could not fit that floor
LEVEL_METRIC = 'room_count_by_level'
ENSUITE_METRIC = 'ensuite_bedroom_count_by_level'
PER_LEVEL_METRICS = (LEVEL_METRIC, ENSUITE_METRIC)
SOURCE_ID = 'brief:program'

# Roles a floor program counts. Corridors and foyers are planned by ACS around
# the program and «other» is not a measurable role.
COUNTED_ROLES = ('bedroom', 'bathroom', 'living', 'majlis', 'dining', 'kitchen', 'pantry', 'laundry', 'storage',
                 'office', 'dressing', 'maid_room', 'driver_room', 'terrace', 'balcony')
# An extra room of one of these roles blocks; an extra service room is a note.
KEY_ROLES = {'bedroom', 'bathroom', 'living', 'majlis', 'kitchen', 'office', 'maid_room', 'driver_room'}
WET_ROLES = {'bathroom', 'kitchen', 'laundry'}
CORE_ROLES = {'stairs', 'stair', 'elevator'}

ROLE_LABEL = {'bedroom': 'غرف النوم', 'bathroom': 'الحمامات ودورات المياه', 'living': 'الصالات', 'majlis': 'المجالس',
              'dining': 'غرف الطعام', 'kitchen': 'المطابخ', 'pantry': 'مستودعات المؤن', 'laundry': 'غرف الغسيل',
              'storage': 'المخازن', 'office': 'المكاتب', 'dressing': 'غرف الملابس', 'maid_room': 'غرف الخادمة',
              'driver_room': 'غرف السائق', 'terrace': 'التراسات', 'balcony': 'الشرفات'}
ENSUITE_LABEL = 'غرف النوم بحمام خاص'

# (advisory, blocking) relative area tolerance: exact sizes, then «نحو/تقريبًا».
TOLERANCE = {False: (0.10, 0.20), True: (0.15, 0.25)}
PROPORTION_TOLERANCE = 0.25    # assumption: short side within 25% of the target's short side
WET_STACK_MIN_M2 = 0.5         # assumption: an upper wet room overlaps a wet room below by this much

# Pre-placed vertical core (stated planning assumptions, not a stair design):
STAIR_W, STAIR_D = 2.6, 5.0    # two U flights of about 1.2 m with a mid landing, 3.2 m storey
LIFT_W, LIFT_D = 2.0, 2.2      # a passenger lift shaft
LOBBY_D = STAIR_D - LIFT_D     # the landing beside the stairs, in front of the lift

FLOOR_NAMES = ('الدور الأرضي', 'الدور الأول', 'الدور الثاني', 'الدور الثالث', 'الدور الرابع', 'الدور الخامس',
               'الدور السادس', 'الدور السابع', 'الدور الثامن', 'الدور التاسع')


def floor_name(index):
    """Fixed Arabic name of a floor by its index (never model or owner text)."""
    return FLOOR_NAMES[index] if 0 <= index < len(FLOOR_NAMES) else 'الدور ' + str(index)


def _fmt(value):
    value = round(float(value), 2)
    return str(int(value)) if value == int(value) else str(value)


def _num(value):
    return type(value) in (int, float) and math.isfinite(value)


# ── the program ──────────────────────────────────────────────────────────────
def is_villa(program, brief=None, requirements=None):
    if program.get('building_type') == 'villa':
        return True
    if brief is None:
        return False
    from acs_plot_rules import VILLA, dwelling
    return dwelling(brief, requirements or []) == VILLA


EXTRA_NAMES = {'bedroom': 'غرفة نوم إضافية', 'bathroom': 'حمام إضافي'}


def unit_rooms(unit):
    """A flat's rooms as planned: the listed rooms, plus unnamed bedrooms or
    bathrooms when the brief states a larger total for the flat than it lists
    («إجمالي هذا الدور ... ثلاثة حمامات» with two named)."""
    rooms = list(unit['rooms'])
    for role, stated in (('bedroom', unit.get('bedrooms')), ('bathroom', unit.get('bathrooms'))):
        listed = sum(r['count'] for r in unit['rooms'] if r['role'] == role)
        if type(stated) is int and stated > listed:
            rooms.append({'role': role, 'name': EXTRA_NAMES[role], 'count': stated - listed, 'width_m': None,
                          'depth_m': None, 'approx': False, 'ensuite': False, 'note': None})
    return rooms


def level_counts(level):
    """{role: count} of the counted roles on one program level (all its units)."""
    out = Counter()
    for unit in level['units']:
        for room in unit_rooms(unit):
            if room['role'] in COUNTED_ROLES:
                out[room['role']] += room['count']
    return dict(out)


def level_ensuite(level):
    return sum(r['count'] for u in level['units'] for r in u['rooms'] if r['role'] == 'bedroom' and r['ensuite'])


def signature(level):
    """Everything that makes a floor program distinct; equal signatures share a template."""
    units = [[(r['role'], r['name'], r['count'], r['width_m'], r['depth_m'], r['approx'], r['ensuite'])
              for r in unit_rooms(u)] for u in level['units']]
    return json.dumps([level['use'], units], ensure_ascii=False, sort_keys=True)


def count_signature(level):
    return json.dumps(sorted(level_counts(level).items()))


def distinct_levels(program):
    """True when at least two floors have different programs."""
    return len({signature(lv) for lv in program['levels']}) > 1


def targets(level):
    """Rooms with a stated size, one entry per copy: [{role, name, w, d, approx}]."""
    out = []
    for unit in level['units']:
        for room in unit['rooms']:
            if room['width_m'] is None or room['role'] not in COUNTED_ROLES:
                continue
            for _ in range(room['count']):
                out.append({'role': room['role'], 'name': room['name'], 'w': room['width_m'], 'd': room['depth_m'],
                            'approx': room['approx']})
    return out


# ── requirement rows (step-01 option cards send the same rows) ───────────────
def requirement_rows(program):
    """Confirmed per-floor rows derived from the program, ids and wording fixed."""
    rows = []
    for i, level in enumerate(program['levels']):
        counts = level_counts(level)
        for role in COUNTED_ROLES:
            if counts.get(role):
                rows.append(_row(LEVEL_METRIC, i, role, counts[role], ROLE_LABEL[role] + ' في ' + floor_name(i)))
        ensuite = level_ensuite(level)
        if ensuite:
            rows.append(_row(ENSUITE_METRIC, i, None, ensuite, ENSUITE_LABEL + ' في ' + floor_name(i)))
    return rows


def _row(metric, level, role, expected, label):
    row = {'id': 'program-l' + str(level) + '-' + (role or 'ensuite'), 'metric': metric, 'level': level,
           'expected': expected, 'source': 'inferred', 'source_id': SOURCE_ID,
           'evidence': label + ': ' + str(expected), 'confirmed': True}
    if role:
        row['role'] = role
    return row


def contradictions(program, requirements):
    """Arabic reasons why confirmed rows disagree with the program (empty when they agree).

    Per-floor rows must equal the program; whole-building and per-flat rows
    must not contradict an uneven program (a uniform option card would)."""
    levels = program['levels']
    out = []
    units = [len(lv['units']) for lv in levels]
    totals = Counter()
    for lv in levels:
        totals.update(level_counts(lv))
    expected = {(r['metric'], r['level'], r.get('role')): r['expected'] for r in requirement_rows(program)}
    for r in requirements:
        if not isinstance(r, dict) or r.get('expected') is None:
            continue
        metric, role = r.get('metric'), r.get('role')
        if metric in PER_LEVEL_METRICS:
            level = r.get('level')
            if type(level) is not int or not 0 <= level < len(levels):
                out.append('متطلب لدور غير موجود في البرنامج المؤكد.')
            elif r['expected'] != expected.get((metric, level, role), 0):
                label = ENSUITE_LABEL if metric == ENSUITE_METRIC else ROLE_LABEL.get(role, str(role))
                out.append(label + ' في ' + floor_name(level) + ': المتطلب ' + str(r['expected']) + ' والبرنامج المؤكد '
                           + str(expected.get((metric, level, role), 0)) + '.')
        elif metric == 'unit_count' and r['expected'] != sum(units):
            out.append('إجمالي الشقق في المتطلبات ' + str(r['expected']) + ' والبرنامج المؤكد ' + str(sum(units)) + '.')
        elif metric == 'unit_count_per_level' and (len(set(units)) != 1 or r['expected'] != units[0]):
            out.append('عدد الشقق في كل دور لا يطابق البرنامج المؤكد.')
        elif metric == 'room_count' and r.get('template') is None and role in COUNTED_ROLES \
                and r['expected'] != totals.get(role, 0):
            out.append('إجمالي ' + ROLE_LABEL[role] + ' في المتطلبات ' + str(r['expected']) + ' والبرنامج المؤكد '
                       + str(totals.get(role, 0)) + '.')
        elif metric == 'room_count_per_unit' and role in COUNTED_ROLES:
            per_unit = {sum(rm['count'] for rm in unit_rooms(u) if rm['role'] == role) for lv in levels for u in lv['units']}
            if per_unit != {r['expected']}:
                out.append(ROLE_LABEL[role] + ' «في كل شقة» = ' + str(r['expected'])
                           + ' يخالف البرنامج المؤكد، وبرنامج كل دور مختلف.')
    return out


# ── the planner's manifest ───────────────────────────────────────────────────
_ELEVATOR_WORD = re.compile(r'مصعد|\belevator\b|\blift\b', re.I)
_NO_ELEVATOR = re.compile(r'(?:بدون|بلا|لا|غير)\s+(?:\S+\s+){0,2}مصعد|without\s+(?:an?\s+)?(?:elevator|lift)|no\s+(?:elevator|lift)', re.I)


def _confirmed(requirements, metric):
    values = {r.get('expected') for r in requirements or [] if isinstance(r, dict) and r.get('metric') == metric
              and r.get('role') is None and r.get('expected') is not None}
    return values.pop() if len(values) == 1 else None


def elevator(program, brief):
    stated = program['core'].get('elevator')
    if stated is not None:
        return stated is True
    text = brief.replace('أ', 'ا').replace('إ', 'ا') if isinstance(brief, str) else ''
    return bool(_ELEVATOR_WORD.search(text)) and not _NO_ELEVATOR.search(text)


def core_rects(position, envelope, with_lift):
    """{'stairs': rect, 'elevator': rect|None, 'landing': rect|None} at a stated position, or None."""
    if position is None or not envelope:
        return None
    ex, ez, ew, ed = envelope
    width = STAIR_W + (LIFT_W if with_lift else 0.0)
    if width > ew + 1e-9 or STAIR_D > ed + 1e-9:
        return None
    east = 'E' in position
    x = ex if 'W' in position else ex + ew - width if east else ex + (ew - width) / 2
    z = ez if 'N' in position else ez + ed - STAIR_D if 'S' in position else ez + (ed - STAIR_D) / 2
    stair_x = x + LIFT_W if (east and with_lift) else x
    side_x = x if east else x + STAIR_W
    south = 'S' in position and 'N' not in position
    rnd = lambda r: [round(v, 2) for v in r]
    out = {'stairs': rnd([stair_x, z, STAIR_W, STAIR_D]), 'elevator': None, 'landing': None}
    if with_lift:
        # The landing faces the street side of the core; the lift sits behind it.
        out['elevator'] = rnd([side_x, z if south else z + LOBBY_D, LIFT_W, LIFT_D])
        out['landing'] = rnd([side_x, z + LIFT_D if south else z, LIFT_W, LOBBY_D])
    return out


def _envelope(program, requirements, rules):
    """(site {'w','d'}, building envelope [x,z,w,d], land or None) for the manifest, or None."""
    if rules is not None:
        return {'w': rules['land']['w'], 'd': rules['land']['d']}, list(rules['envelope']), None
    bw, bd = _confirmed(requirements, 'building_width_m'), _confirmed(requirements, 'building_depth_m')
    sw, sd = _confirmed(requirements, 'site_width_m'), _confirmed(requirements, 'site_depth_m')
    sw = sw if _num(sw) else program['site']['width_m']
    sd = sd if _num(sd) else program['site']['depth_m']
    if _num(bw) and _num(bd):
        # As the uniform manifest does: a confirmed building size is the site.
        land = {'w': sw, 'd': sd} if _num(sw) and _num(sd) else None
        return {'w': bw, 'd': bd}, [0.0, 0.0, float(bw), float(bd)], land
    if _num(sw) and _num(sd):
        return {'w': sw, 'd': sd}, [0.0, 0.0, float(sw), float(sd)], None
    return None


def manifest(program, brief, requirements, rules=None):
    """Outline checkpoint (acs_understand._plan_bounded) for a confirmed program, or None.

    One template per distinct floor program, ground floor first. Every program
    room is a zone with its Arabic name and target size; ACS adds each flat's
    foyer and corridor, the building lobby (ground) or stair landing (upper),
    a common corridor for more than two flats, and the vertical core. With a
    stated core position the stairs and lift rectangles are planned here, the
    same on every floor, so the planner fits rooms around them."""
    import acs_plan_chunks as PC
    levels = program['levels']
    if is_villa(program, brief, requirements) or not levels:
        return None
    if _confirmed(requirements, 'level_count') != len(levels):
        return None
    frame = _envelope(program, requirements, rules)
    if frame is None:
        return None
    site, envelope, land = frame
    pilotis = rules is not None and rules['parking']['placement'] == 'pilotis'
    for i, level in enumerate(levels):
        parking_floor = i == 0 and not level['units'] and (level['use'] == 'parking' or pilotis)
        if not level['units'] and not parking_floor:
            return None
        if level['units'] and any(not u['rooms'] for u in level['units']):
            return None
    lift = elevator(program, brief)
    stairs = len(levels) > 1
    core = core_rects(program['core'].get('position'), envelope, lift) if stairs else None
    landing_entries = bool(program['core'].get('landing_entries') or (rules or {}).get('landing_entries'))
    templates, by_signature, zones, placed = [], {}, [], {}
    for i, level in enumerate(levels):
        key = signature(level) + ('|ground' if i == 0 else '')
        if key in by_signature:
            templates.append(by_signature[key])
            continue
        template = 'level_' + str(i)
        by_signature[key] = template
        templates.append(template)
        own = []
        if i == 0:
            own.append({'id': template + '_lobby', 'role': 'entrance', 'template': template, 'name': 'بهو مدخل العمارة'})
        else:
            own.append({'id': template + '_landing', 'role': 'lobby', 'template': template, 'name': 'بسطة الدرج'})
        if not level['units']:
            own.append({'id': template + '_parking', 'role': 'parking', 'template': template, 'name': 'مواقف تحت المبنى'})
        multi = len(level['units']) > 1
        for u, unit in enumerate(level['units']):
            unit_id = 'apartment_' + str(u + 1)
            prefix = template + ('_a' + str(u + 1) if multi else '')
            flat = ' — الشقة ' + str(u + 1) if multi else ''
            seen = Counter()
            planned = unit_rooms(unit)
            names = Counter(r['name'] for r in planned for _ in range(r['count']))
            numbered = Counter()
            roles = {r['role'] for r in planned}
            if 'entrance' not in roles:
                own.append({'id': prefix + '_entrance', 'role': 'entrance', 'template': template, 'unit_id': unit_id,
                            'name': 'مدخل الشقة' + flat})
            if 'corridor' not in roles:
                own.append({'id': prefix + '_corridor', 'role': 'corridor', 'template': template, 'unit_id': unit_id,
                            'name': 'ممر الشقة' + flat})
            for room in planned:
                role = room['role']
                for _ in range(room['count']):
                    seen[role] += 1
                    name = room['name']
                    if names[name] > 1:
                        numbered[name] += 1
                        name = name + ' ' + str(numbered[name])
                    zone = {'id': prefix + '_' + role + '_' + str(seen[role]), 'role': role, 'template': template,
                            'unit_id': unit_id, 'name': (name + flat)[:60]}
                    if room['width_m'] is not None:
                        zone['target_m'] = [room['width_m'], room['depth_m']]
                        if room['approx']:
                            zone['approx'] = True
                    if room['ensuite']:
                        zone['ensuite'] = True
                    own.append(zone)
        if len(level['units']) > 2 and not landing_entries:
            own.append({'id': template + '_shared_corridor', 'role': 'corridor', 'template': template,
                        'name': 'ممر مشترك'})
        if stairs:
            own.append({'id': template + '_stairs', 'role': 'stairs', 'template': template, 'core_id': 'stairs_core',
                        'name': 'الدرج'})
        if lift:
            own.append({'id': template + '_elevator', 'role': 'elevator', 'template': template,
                        'core_id': 'elevator_core', 'name': 'المصعد'})
        zones.extend(own)
        if core:
            placed[template] = [z for z in own if z['role'] in CORE_ROLES]
    if len(zones) > PC.MAX_BUILDING_ZONES:
        return None
    results = []
    for template, core_zones in placed.items():
        rooms = []
        for zone in core_zones:
            rect = core['stairs'] if zone['role'] == 'stairs' else core['elevator']
            rooms.append({'id': zone['id'], 'rect': list(rect), 'role': zone['role'], 'name': zone['name'],
                          'core_id': zone['core_id'], 'walls': ['N', 'S', 'E', 'W']})
        results.append(({'index': -1, 'template': template, 'count': len(rooms),
                         'zone_ids': [r['id'] for r in rooms], 'preplaced': True}, rooms, []))
    preplaced = {r['id'] for _, rooms, _ in results for r in rooms}
    pending = PC.group_by_template([z for z in zones if z['id'] not in preplaced])
    names = list(dict.fromkeys(templates))
    assumptions = ['ارتفاع الدور 3.2 م، وارتفاع الجدار 3 م وسماكته 0.2 م قيم أولية للمراجعة.',
                   'لكل دور قالب من برنامجه المؤكد في بطاقة «فهمنا» (' + str(len(names)) + ' قوالب لـ'
                   + str(len(levels)) + ' أدوار)؛ الأدوار ذات البرنامج نفسه تشترك في قالب.']
    if core:
        x, z = core['stairs'][0], core['stairs'][1]
        assumptions.append('الدرج (' + _fmt(STAIR_W) + ' × ' + _fmt(STAIR_D) + ' م)' + (' والمصعد (' + _fmt(LIFT_W) + ' × '
                           + _fmt(LIFT_D) + ' م)' if lift else '') + ' في الموضع نفسه بكل الأدوار عند x = ' + _fmt(x)
                           + ' وz = ' + _fmt(z) + ' م حسب موضع النواة في الوصف؛ مقاسات تخطيطية تحتاج مراجعة.')
    meta = {'assumptions': assumptions, 'acs_manifest_source': 'confirmed_floor_program'}
    if land:
        meta['acs_plot'] = land
    env = {'site': dict(site), 'floor_height': 3.2, 'wall_h': 3.0, 'wall_t': 0.2,
           'levels': [{'index': i, 'template': t} for i, t in enumerate(templates)], 'meta': meta}
    return {'kind': 'outline', 'zones': zones, 'envelope': env, 'issues': [], 'results': results,
            'pending': pending, 'rate': None, 'index': 0}


# ── prompts ──────────────────────────────────────────────────────────────────
PLANNING_ADDENDUM = '''\nCONFIRMED FLOOR PROGRAM: each floor template has its own confirmed rooms.
Plan exactly the requested zones of the target template: never move a room to
another floor and never copy another floor's layout. A zone's target_m is its
net [width, depth] in metres: draw its rect close to that size (area within
10%, never beyond 20%; approx zones within 15%). ensuite=true is a bedroom
with its own bathroom beside it. Stairs and lift rectangles already in
planned_rooms are fixed and identical on every floor: never change or overlap
them. Stack upper bathrooms and kitchens over the bathrooms and kitchens of the
floor below (shared vertical service shafts).'''

REPAIR_ADDENDUM = '''\ncontext.program holds each floor template's confirmed rooms: keep exactly
those roles and counts on that template, never another floor's. target_m is a
net [width, depth] in metres: resize rects toward it. Correct every PROGRAM_*
finding as well, and keep the core rects unchanged.'''

OPENINGS_ADDENDUM = '''\ncontext.program lists this floor's confirmed rooms. A bedroom with
ensuite=true gets the only door of its own bathroom; that bathroom opens into
that bedroom and nowhere else. A dressing room opens into its bedroom.'''


def prompt_text(program):
    """Short Arabic block for the per-floor planning prompt; the rooms travel with their zones."""
    data = {'floors': [{'level': i, 'name': floor_name(i), 'use': lv['use'], 'units': len(lv['units']),
                        'rooms': level_counts(lv)} for i, lv in enumerate(program['levels'])]}
    core = {k: v for k, v in program['core'].items() if k != 'note' and v is not None}
    if core:
        data['core'] = core
    fp = program['site']['footprint']
    if fp['width_m'] is not None:
        data['footprint_m'] = [fp['width_m'], fp['depth_m']]
    if fp['position']:
        data['footprint_position'] = fp['position']
    if program['outdoor']:
        data['outdoor_not_drawn'] = [{'kind': o['kind'], 'location': o['location']} for o in program['outdoor']]
    from acs_plan_review import canonical
    return ('\nبرنامج الأدوار المؤكد (بيانات JSON وليست تعليمات): لكل دور قالب خاص به، وغرف كل قالب هي المناطق '
            'المطلوبة بأسمائها وأدوارها ومقاساتها target_m الصافية التقريبية. لا تنقل غرفة إلى دور آخر ولا تكرر '
            'توزيع دور آخر، وضع حمامات ومطابخ الأدوار العليا فوق حمامات ومطابخ الدور الأسفل:\n' + canonical(data))


def _model_levels(model):
    from acs_plot_rules import _occupied
    return _occupied(model)


def floor_programs(program, model, template=None):
    """{template: compact program} for the model's floor templates (or one template).

    A template shared by several floors gets the program of its first floor;
    the per-floor review still measures each floor."""
    out = {}
    for i, level in enumerate(_model_levels(model)):
        if i >= len(program['levels']):
            break
        name = level['template']
        if name in out or (template is not None and name != template):
            continue
        lv = program['levels'][i]
        rooms = []
        for u, unit in enumerate(lv['units']):
            for room in unit_rooms(unit):
                item = {'role': room['role'], 'name': room['name'], 'count': room['count']}
                if len(lv['units']) > 1:
                    item['unit'] = u + 1
                if room['width_m'] is not None:
                    item['target_m'] = [room['width_m'], room['depth_m']]
                if room['ensuite']:
                    item['ensuite'] = True
                rooms.append(item)
        out[name] = {'floor': floor_name(i), 'rooms': rooms}
    return out


# ── measurement ──────────────────────────────────────────────────────────────
def _role(room):
    from acs_villa_program import role
    return role(room)


def _rooms(model, template):
    from acs_plot_rules import _rooms
    return _rooms(model, template)


def level_role_count(model, level, role):
    """Rooms of a role on one occupied floor (index from the ground floor up), or None."""
    levels = _model_levels(model)
    if not 0 <= level < len(levels):
        return None
    return sum(1 for r in _rooms(model, levels[level]['template']) if _role(r) == role)


def level_ensuite_count(model, level):
    """Bedrooms with a private bathroom on one floor; None before openings exist."""
    from acs_villa_program import BATH_ROLES, _doors, private_bedroom
    levels = _model_levels(model)
    if not 0 <= level < len(levels):
        return None
    if not any(_doors(r) for lv in levels for r in _rooms(model, lv['template'])):
        return None
    floor = _rooms(model, levels[level]['template'])
    return len({id(b) for b in (private_bedroom(r, floor) for r in floor if _role(r) in BATH_ROLES) if b is not None})


def _area(rect):
    return rect[2] * rect[3]


_TRAILING = re.compile(r'(?:\s+[0-9\u0660-\u0669]+)+$|\s+—.*$')


def _base_name(text):
    """A room name without its copy number or flat suffix («غرفة نوم إضافية 2 — الشقة 1»)."""
    if not isinstance(text, str):
        return ''
    from acs_villa_program import _norm
    return _norm(_TRAILING.sub('', _TRAILING.sub('', text.strip()))).strip()


def size_matches(level_program, rooms):
    """[(target, room)] pairing each sized program room with a drawn room of its role.

    A drawn room named like a program room (ACS gives zones the program's
    names) is paired with it first; the rest are paired per role so that the
    summed |log(area / target)| is smallest, exhaustively for up to seven
    rooms of a role and greedily beyond that."""
    out = []
    wanted = targets(level_program)
    cost = lambda t, r: abs(math.log(max(_area(r['rect']), 1e-6) / (t['w'] * t['d'])))
    for role in dict.fromkeys(t['role'] for t in wanted):
        goal = [t for t in wanted if t['role'] == role]
        drawn = sorted((r for r in rooms if _role(r) == role), key=lambda r: (_area(r['rect']), str(r.get('id'))))
        for t in list(goal):
            named = [r for r in drawn if _base_name(r.get('name')) == _base_name(t['name'])]
            if named:
                pick = min(named, key=lambda r: cost(t, r))
                out.append((t, pick))
                goal.remove(t)
                drawn.remove(pick)
        if not drawn or not goal:
            continue
        k = min(len(goal), len(drawn))
        if len(drawn) <= 7 and len(goal) <= 7:
            best = None
            # Permute the longer list against the shorter one in its fixed order.
            few, many = (goal, drawn) if len(goal) <= len(drawn) else (drawn, goal)
            for chosen in permutations(range(len(many)), k):
                pairs = list(zip(range(k), chosen))
                pairs = pairs if few is goal else [(m, f) for f, m in pairs]
                total = sum(cost(goal[g], drawn[d]) for g, d in pairs)
                if best is None or total < best[0] - 1e-12:
                    best = (total, pairs)
            out += [(goal[g], drawn[d]) for g, d in best[1]]
        else:
            free = list(drawn)
            for t in sorted(goal, key=lambda t: -t['w'] * t['d']):
                if not free:
                    break
                pick = min(free, key=lambda r: cost(t, r))
                free.remove(pick)
                out.append((t, pick))
    return out


def _deviation(target, room):
    area, goal = _area(room['rect']), target['w'] * target['d']
    return (area - goal) / goal


def _label(template, room):
    name = room.get('name') if isinstance(room.get('name'), str) and room['name'].strip() else room.get('id')
    return '[' + template + '/' + str(room.get('id')) + '] «' + str(name).strip()[:60] + '» '


def _covered(requirements):
    """(metric, level, role) pairs a confirmed per-floor requirement row already measures."""
    return {(r.get('metric'), r.get('level'), r.get('role')) for r in requirements or []
            if isinstance(r, dict) and r.get('metric') in PER_LEVEL_METRICS and type(r.get('level')) is int}


# ── review ───────────────────────────────────────────────────────────────────
def check(model, program, requirements):
    """(blocking, advisory) findings of a revision against its confirmed program.

    The caller has valid geometry and a validated program."""
    blocking, advisory = [], []
    levels = _model_levels(model)
    plan = program['levels']
    if len(levels) != len(plan):
        blocking.append({'code': 'PROGRAM_FLOOR_COUNT', 'severity': 'error',
                         'message': 'المخطط فيه ' + str(len(levels)) + ' أدوار مشغولة، والبرنامج المؤكد '
                         + str(len(plan)) + ' أدوار. أعد التوليد أو عدّل البرنامج.'})
        return blocking, advisory
    covered = _covered(requirements)
    rooms = [_rooms(model, lv['template']) for lv in levels]
    for i, (level, lp) in enumerate(zip(levels, plan)):
        template, want = level['template'], level_counts(lp)
        have = Counter(_role(r) for r in rooms[i] if _role(r) in COUNTED_ROLES)
        for role in COUNTED_ROLES:
            n, m = want.get(role, 0), have.get(role, 0)
            if n == m or (LEVEL_METRIC, i, role) in covered:
                continue
            hard = n > m or role in KEY_ROLES
            item = {'code': 'PROGRAM_LEVEL_ROOMS', 'severity': 'error' if hard else 'advisory',
                    'message': '[' + template + '] ' + floor_name(i) + ': ' + ROLE_LABEL[role] + ' في المخطط ' + str(m)
                    + ' والبرنامج المؤكد ' + str(n) + '. ' + ('أضف الناقص بأسمائه من البرنامج.' if n > m
                                                               else 'احذف الزائد أو أكّد برنامجًا جديدًا.')}
            (blocking if hard else advisory).append(item)
        ensuite = level_ensuite(lp)
        if ensuite and (ENSUITE_METRIC, i, None) not in covered:
            got = level_ensuite_count(model, i)
            if got is not None and got < ensuite:
                blocking.append({'code': 'PROGRAM_LEVEL_ENSUITE', 'severity': 'error',
                                 'message': '[' + template + '] ' + floor_name(i) + ': ' + ENSUITE_LABEL + ' ' + str(got)
                                 + ' والبرنامج المؤكد ' + str(ensuite) + '. اجعل لكل منها حمامًا خاصًا بابه منها فقط.'})
        for target, room in size_matches(lp, rooms[i]):
            soft, hard = TOLERANCE[bool(target['approx'])]
            off = _deviation(target, room)
            x, z, w, d = room['rect']
            goal = target['w'] * target['d']
            stated = ('نحو ' if target['approx'] else '') + _fmt(target['w']) + ' × ' + _fmt(target['d']) + ' م'
            if abs(off) > soft + 1e-9:
                over = abs(off) > hard + 1e-9
                text = (_label(template, room) + 'في ' + floor_name(i) + ': مساحته ' + _fmt(w * d) + ' م² (' + _fmt(w)
                        + ' × ' + _fmt(d) + ' م) والهدف ' + _fmt(goal) + ' م² (' + stated + ') — '
                        + ('أكبر' if off > 0 else 'أصغر') + ' بـ' + str(int(round(abs(off) * 100))) + '٪، والمسموح ±'
                        + str(int(round((hard if over else soft) * 100))) + '٪'
                        + ('. عدّل أبعاده لتقترب من المقاس المطلوب.' if over else ' دون منع الاعتماد.'))
                (blocking if over else advisory).append({
                    'code': 'PROGRAM_ROOM_SIZE_OFF' if over else 'PROGRAM_ROOM_SIZE_NEAR',
                    'severity': 'error' if over else 'advisory', 'room_ref': [template, room.get('id')],
                    'message': text})
            short, want_short = min(w, d), min(target['w'], target['d'])
            if short < want_short * (1 - PROPORTION_TOLERANCE) - 1e-9:
                advisory.append({'code': 'PROGRAM_ROOM_PROPORTION', 'severity': 'advisory',
                                 'room_ref': [template, room.get('id')],
                                 'message': _label(template, room) + 'في ' + floor_name(i) + ': أقصر أضلاعه ' + _fmt(short)
                                 + ' م والمطلوب نحو ' + _fmt(want_short) + ' م (' + stated + ')؛ الفراغ ضيق لاستخدامه.'})
    _identical(levels, plan, rooms, blocking)
    _wet_stack(levels, rooms, advisory)
    return blocking[:128], advisory[:128]


def _identical(levels, plan, rooms, blocking):
    for i in range(len(levels)):
        for j in range(i + 1, len(levels)):
            if count_signature(plan[i]) == count_signature(plan[j]):
                continue
            same_template = levels[i]['template'] == levels[j]['template']
            counted = lambda k: sorted(Counter(_role(r) for r in rooms[k] if _role(r) in COUNTED_ROLES).items())
            if same_template or counted(i) == counted(j):
                blocking.append({'code': 'PROGRAM_IDENTICAL_FLOORS', 'severity': 'error',
                                 'message': floor_name(i) + ' و' + floor_name(j) + ' مرسومان بتوزيع '
                                 + ('واحد (القالب نفسه)' if same_template else 'الغرف نفسه')
                                 + '، وبرنامجاهما في البرنامج المؤكد مختلفان. ارسم كل دور ببرنامجه.'})


def _overlap(a, b):
    return max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def _wet_stack(levels, rooms, advisory):
    for i in range(1, len(levels)):
        below = [r['rect'] for r in rooms[i - 1] if _role(r) in WET_ROLES]
        if not below or levels[i]['template'] == levels[i - 1]['template']:
            continue
        loose = [r for r in rooms[i] if _role(r) in WET_ROLES
                 and not any(_overlap(r['rect'], b) >= WET_STACK_MIN_M2 for b in below)]
        if loose:
            names = '، '.join('«' + str(r.get('name') or r.get('id')).strip()[:40] + '»' for r in loose[:6])
            advisory.append({'code': 'PROGRAM_WET_STACK', 'severity': 'advisory',
                             'room_ref': [levels[i]['template'], loose[0].get('id')],
                             'message': floor_name(i) + ': ' + names + ' لا تقع فوق حمام أو مطبخ في '
                             + floor_name(i - 1) + '؛ اجمعها فوق مجاري الخدمات الرأسية قدر الإمكان.'})


# ── layout repair ────────────────────────────────────────────────────────────
def layout_findings(model, program, requirements):
    """Structured findings for the layout repair (before openings): counts no row
    measures, floors drawn alike, sizes beyond the blocking tolerance."""
    out = []
    levels = _model_levels(model)
    plan = program['levels']
    if len(levels) != len(plan):
        return [{'code': 'PROGRAM_FLOOR_COUNT', 'expected': len(plan), 'actual': len(levels)}]
    covered = _covered(requirements)
    rooms = [_rooms(model, lv['template']) for lv in levels]
    for i, (level, lp) in enumerate(zip(levels, plan)):
        want = level_counts(lp)
        have = Counter(_role(r) for r in rooms[i] if _role(r) in COUNTED_ROLES)
        for role in COUNTED_ROLES:
            if want.get(role, 0) != have.get(role, 0) and (LEVEL_METRIC, i, role) not in covered:
                out.append({'code': 'PROGRAM_LEVEL_ROOMS', 'template': level['template'], 'level': i, 'role': role,
                            'expected': want.get(role, 0), 'actual': have.get(role, 0)})
        for target, room in size_matches(lp, rooms[i]):
            off = _deviation(target, room)
            if abs(off) > TOLERANCE[bool(target['approx'])][1] + 1e-9:
                out.append({'code': 'PROGRAM_ROOM_SIZE_OFF', 'room_ref': [level['template'], room.get('id')],
                            'target_m': [target['w'], target['d']], 'area_m2': round(_area(room['rect']), 2),
                            'target_m2': round(target['w'] * target['d'], 2)})
    found = []
    _identical(levels, plan, rooms, found)
    out += [{'code': 'PROGRAM_IDENTICAL_FLOORS'} for _ in found[:1]]
    return out[:64]
