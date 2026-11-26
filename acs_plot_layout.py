"""Bounded, disclosed rectangular fallback inside the plot's buildable envelope.

Used only after a provider layout/detail fails, like acs_residential_layout,
for confirmed two-apartment floors under plot rules. The ground storey has the
entrance lobby with its external door on the street (or, with pilotis, the
parking hall); the typical upper storeys have only the stair landing, and both
flats open directly onto it next to their majlis. Every proportion below is an
editable concept assumption, not a regulation.
"""
import copy
import math
import re

from acs_plan_review import _geometry, _program
from acs_residential_access import EPS, OPPOSITE, detail_issues, edge
from acs_residential_manifest import manifest

NAMES = {'bedroom': 'غرفة نوم', 'living': 'صالة', 'majlis': 'مجلس', 'kitchen': 'مطبخ', 'bathroom': 'دورة مياه',
         'corridor': 'ممر', 'entrance': 'مدخل', 'stairs': 'درج', 'elevator': 'مصعد', 'lobby': 'بسطة الدرج',
         'parking': 'مواقف تحت المبنى'}
WEIGHTS = {'bedroom': 1, 'living': 1.3, 'majlis': 1.1, 'kitchen': 1.7, 'bathroom': .7, 'entrance': .6}
CORE_DEPTH, LOBBY_DEPTH, STAIR_W, LIFT_W, PRIVATE_W = 4., 2.5, 4., 3., 1.4
OPEN_ROLES = {'corridor', 'entrance', 'stairs', 'elevator', 'lobby', 'parking'}


def _local_to_land(rect, front, env):
    """Map a rect from the street-facing local frame into land coordinates."""
    x, z, w, d = rect
    ex, ez, ew, ed = env
    if front == 'N':
        return [ex + x, ez + z, w, d]
    if front == 'S':
        return [ex + x, ez + ed - z - d, w, d]
    if front == 'E':
        return [ex + ew - z - d, ez + x, d, w]
    return [ex + z, ez + ed - x - w, d, w]  # W


def _floor(template, zones, rules, kind):
    """kind: 'ground' (entrance lobby + flats), 'pilotis' (lobby + parking) or 'typical'."""
    import acs_plot_rules as P
    front = rules['streets'][0]
    env = rules['envelope']
    width, depth = (env[3], env[2]) if front in ('E', 'W') else (env[2], env[3])
    has_lift = any(z['role'] == 'elevator' for z in zones)
    has_stairs = any(z['role'] == 'stairs' for z in zones)
    # A single storey has no stair core: the front band is only the lobby.
    core_depth = CORE_DEPTH if has_stairs or has_lift else LOBBY_DEPTH
    # Centimetre boundaries: the plan contract rounds rectangles, and rounded
    # neighbours must still touch without overlapping.
    unit_width = math.floor(width / 2 * 100) / 100
    unit_depth = round(depth - core_depth, 2)
    outer_width = round((unit_width - PRIVATE_W) * .58, 2)
    inner_width = round(unit_width - PRIVATE_W - outer_width, 2)
    if outer_width < 2.7 or inner_width < 2 or unit_depth < 8:
        return None
    landing_x0 = round(unit_width - inner_width, 2)
    landing_x1 = round(unit_width + inner_width, 2)
    if (has_stairs and landing_x0 - STAIR_W < 0) or (has_lift and landing_x1 + LIFT_W > width):
        return None
    rooms, connections = [], []

    def add(zone, rect, name=None):
        r = {k: v for k, v in zone.items() if k != 'template'}
        r.update(name=name or NAMES[r['role']], rect=list(rect), walls=['N', 'S', 'E', 'W'], doors=[], windows=[], points=[])
        if r.get('unit_id'):
            ordinal = re.search(r'_(\d+)$', r['id'])
            r['name'] += (' ' + ordinal.group(1) if ordinal else '') + ' — الشقة ' + r['unit_id'].rsplit('_', 1)[-1]
        rooms.append(r)
        return r

    hub_zone = next((z for z in zones if z['role'] in ('entrance', 'lobby') and not z.get('unit_id')), None)
    if hub_zone is None:
        return None
    hub = add(hub_zone, [landing_x0, 0, landing_x1 - landing_x0, core_depth],
              'مدخل العمارة' if kind != 'typical' else 'بسطة الدرج')
    for role, x, w in (('stairs', landing_x0 - STAIR_W, STAIR_W), ('elevator', landing_x1, LIFT_W)):
        zone = next((z for z in zones if z['role'] == role), None)
        if zone is not None:
            connections.append((hub, add(zone, [x, 0, w, core_depth])))
    if kind == 'pilotis':
        park = add(next(z for z in zones if z['role'] == 'parking'), [0, core_depth, width, unit_depth])
        park['walls'] = 'none'
        connections.append((hub, park))
    else:
        for number in (1, 2):
            unit = 'apartment_' + str(number)
            own = [z for z in zones if z.get('unit_id') == unit]
            local = []

            def unit_add(zone, rect):
                room = add(zone, rect)
                local.append(room)
                return room
            corridor = unit_add(next(z for z in own if z['role'] == 'corridor'), [outer_width, core_depth, PRIVATE_W, unit_depth])
            # Guest zone first: the majlis faces the flat entrance, bedrooms stay at the back.
            outer = sorted((z for z in own if z['role'] in {'living', 'majlis', 'bedroom'}),
                           key=lambda z: ({'majlis': 0, 'living': 1, 'bedroom': 2}[z['role']], z['id']))
            entrance = next((z for z in own if z['role'] == 'entrance'), None)
            if entrance is None:
                return None
            inner = [entrance] + [z for z in own if z['role'] in {'kitchen', 'bathroom'}]
            for column, x, w in ((outer, 0, outer_width), (inner, outer_width + PRIVATE_W, inner_width)):
                total = sum(WEIGHTS[z['role']] for z in column)
                cursor = core_depth
                for i, zone in enumerate(column):
                    end = depth if i == len(column) - 1 else round(cursor + unit_depth * WEIGHTS[zone['role']] / total, 2)
                    if min(w, end - cursor) < (2.7 if zone['role'] in {'bedroom', 'living', 'majlis'} else 1.5):
                        return None
                    room = unit_add(zone, [x, cursor, w, end - cursor])
                    connections.append((corridor, room))
                    if zone['role'] == 'entrance':
                        connections.append((hub, room))
                    cursor = end
            if number == 2:
                for room in local:
                    room['rect'][0] = round(width - room['rect'][0] - room['rect'][2], 2)
    for room in rooms:
        room['rect'] = _local_to_land(room['rect'], front, env)

    def opening(room, kind_, side, offset, w, h, sill=None):
        item = {'id': room['id'] + '_' + kind_ + '_' + str(len(room[kind_])), 'edge': side,
                'offset': round(offset, 4), 'width': w, 'height': h}
        if kind_ == 'doors':
            item['material'] = 'wood'
        if sill is not None:
            item['sill'] = sill
        room[kind_].append(item)
    for a, c in connections:
        for side, other in OPPOSITE.items():
            line, lo, hi = edge(a, side)
            line2, lo2, hi2 = edge(c, other)
            low, high = max(lo, lo2), min(hi, hi2)
            if abs(line - line2) < EPS and high - low >= 1.1:
                center = (low + high) / 2
                opening(a, 'doors', side, center - lo, .9, 2.1)
                if c.get('walls') != 'none':
                    opening(c, 'doors', other, center - lo2, .9, 2.1)
                break
        else:
            return None
    if kind != 'typical':
        _, lo, hi = edge(hub, front)
        opening(hub, 'doors', front, (hi - lo) / 2, 1.2, 2.1)
    for room in rooms:
        x, z, w, d = room['rect']
        room['points'] = [{'id': room['id'] + '_light', 'type': 'light', 'x': round(w / 2, 4), 'z': round(d / 2, 4)}]
        if room['role'] in OPEN_ROLES:
            continue
        for side in ('N', 'S', 'W', 'E'):
            line, lo, hi = edge(room, side)
            if hi - lo < 1.8 or any(o['edge'] == side for o in room['doors']):
                continue
            probe = {'edge': side, 'offset': (hi - lo) / 2}
            other, _ = P._across(rooms, room, probe)
            gap = P._plot_distance(rules, room, side)
            limit = min(rules['setbacks_m'][side], rules['window_min_m'])
            if other is not None or (side not in rules['streets'] and (gap < P.EPS or gap < limit - P.EPS)):
                continue
            bath = room['role'] == 'bathroom'
            opening(room, 'windows', side, (hi - lo) / 2, .6 if bath else 1.2, .6 if bath else 1.2, 1.5 if bath else .9)
            break
    return rooms


def propose(brief, requirements, rules):
    """Return a checked fallback building inside the envelope, or None."""
    if re.search(r'منور|فناء|حوش|ماستر|حمام داخلي|جناح|دوبلكس|مفتوح|شمالي[ةه]?|جنوبي[ةه]?|master|ensuite|en-suite|courtyard|duplex',
                 brief, re.I):
        return None
    if re.search(r'(?:غرف[ةه]|مجلس|مطبخ|صال[ةه]|حمام|درج|مصعد|ممر|مدخل)[^\n]{0,25}\d\s*[×x*]\s*\d', brief, re.I):
        return None
    allowed = {'site_width_m', 'site_depth_m', 'building_width_m', 'building_depth_m', 'level_count', 'unit_count',
               'unit_count_per_level', 'room_count', 'room_count_per_unit'}
    if any(r.get('metric') not in allowed for r in requirements):
        return None
    cp = manifest(brief, requirements, rules)
    if not cp:
        return None
    b = copy.deepcopy(cp['envelope'])
    pilotis = rules['parking']['placement'] == 'pilotis'
    floors = {}
    levels = b['levels']
    for level in levels:
        template = level['template']
        if template in floors:
            continue
        zones = [z for z in cp['zones'] if z['template'] == template]
        units = {z['unit_id'] for z in zones if z.get('unit_id')}
        kind = 'pilotis' if pilotis and level['index'] == 0 else 'ground' if level['index'] == 0 else 'typical'
        if (kind == 'pilotis') != (not units) or (units and len(units) != 2):
            return None
        rooms = _floor(template, zones, rules, kind)
        if rooms is None:
            return None
        floors[template] = {'rooms': rooms}
    b['floors'] = floors
    b['meta']['assumptions'] += [
        'توزيع بديل محسوب بعد تعذر المقترح داخل المساحة القابلة للبناء: الدرج وبسطته في واجهة الشارع، '
        'والشقتان تفتحان مباشرة على البسطة بجوار المجلس، وغرف النوم في الخلف؛ يحتاج مراجعة معمارية.',
        'عرض الممر الخاص 1.4 م وأبعاد النواة والبسطة ونسب الغرف افتراضات تصميمية قابلة للتعديل وليست اشتراطات موثقة.',
        'لا يتضمن هذا التوزيع إثبات الإنشاء أو الإخلاء أو الحريق أو كفاية الإضاءة والتهوية.',
    ]
    b['meta']['acs_layout_method'] = 'bounded_plot_envelope_fallback_v1'
    import acs_plot_rules as P
    P.stamp(b, rules)
    from acs_residential_generation import check_rooms
    check_rooms(b)
    if _geometry(b)[0] or _program(b, brief, requirements) or detail_issues(b):
        return None
    if P.check(b, rules)[0]:
        return None
    return b
