"""Deterministic fallback for a confirmed per-floor program (after the provider failed).

Used only when the layout or openings stage could not finish for a confirmed
apartment program (acs_floor_program). Each floor is laid out from its own
program; floors with the same program share a template, and no floor ever
copies another floor's program. When a floor cannot be fitted, or a fitted
building fails a check, the job fails with an error code that names the floor
(acs_floor_program.FLOOR_NOT_FITTED + index) instead of saving identical or
wrong floors.

The layout is a disclosed concept, in a local frame whose north is the street
and whose west holds the core:

* the core block in front: stairs, the landing (the building lobby on the
  ground floor, with its door on the street) and the lift behind it;
* the flat's foyer beside the landing, then a corridor running to the back;
* a service column under the core (kitchen, wet rooms, stores) and a main
  column across the corridor (majlis and living rooms in front, bedrooms at
  the back), one room per row, each with a door on the corridor; an en-suite
  bathroom, a dressing room or a pantry sits beside its host room and opens
  only into it.

Every dimension below is an editable planning assumption, not a regulation.
"""
from __future__ import annotations

import copy

from acs_plan_review import PlanError, _geometry, _program
import acs_floor_program as F

CORRIDOR_W = 1.2
CORE_W = F.STAIR_W + F.LIFT_W            # stairs + landing/lift column
MIN_HABITABLE = 2.7                       # assumption: shortest side of a room people live in
MIN_SERVICE = 1.5                         # assumption: shortest side of a bathroom or store
HABITABLE = {'bedroom', 'living', 'majlis', 'dining', 'office', 'maid_room', 'driver_room', 'kitchen'}
DEFAULT_M2 = {'bedroom': 12.0, 'majlis': 16.0, 'living': 18.0, 'dining': 10.0, 'office': 9.0, 'kitchen': 10.0,
              'bathroom': 4.5, 'laundry': 4.0, 'pantry': 2.5, 'storage': 3.0, 'dressing': 4.0, 'maid_room': 8.0,
              'driver_room': 8.0, 'terrace': 10.0, 'balcony': 5.0, 'other': 6.0}
MAIN = ('terrace', 'balcony', 'majlis', 'living', 'dining', 'office', 'bedroom')
SERVICE = ('kitchen', 'laundry', 'storage', 'bathroom', 'maid_room', 'driver_room', 'other')
OPEN_ROLES = {'terrace', 'balcony'}
EPS = 1e-6


class _NotFitted(Exception):
    pass


def _r2(value):
    return round(value + 0.0, 2)


def _rooms_of(level):
    """Expanded program rooms of a single-flat floor, in program order."""
    out = []
    for room in level['units'][0]['rooms']:
        for k in range(room['count']):
            out.append({'role': room['role'], 'name': room['name'] + (' ' + str(k + 1) if room['count'] > 1 else ''),
                        'target': (room['width_m'], room['depth_m']) if room['width_m'] is not None else None,
                        'approx': room['approx'], 'ensuite': room['ensuite'], 'deps': []})
    return out


def _rows(rooms):
    """Host rows with their dependents (en-suite bath, dressing, pantry)."""
    hosts, free = [], list(rooms)
    for i, room in enumerate(rooms):
        if room['role'] == 'bedroom' and room['ensuite']:
            bath = next((r for r in rooms[i + 1:] + rooms[:i] if r['role'] == 'bathroom' and r in free), None)
            if bath is not None:
                free.remove(bath)
                room['deps'].append(bath)
            dressing = next((r for r in rooms[i + 1:] if r['role'] == 'dressing' and r in free), None)
            if dressing is not None:
                free.remove(dressing)
                room['deps'].append(dressing)
    # A pantry opens from its kitchen, a dining room from the living room and
    # a guest WC from the majlis: each sits beside its host and opens into it.
    for host_role, dep_role, word in (('kitchen', 'pantry', None), ('living', 'dining', None),
                                      ('majlis', 'bathroom', ('ضيوف', 'مجلس'))):
        host = next((r for r in free if r['role'] == host_role and not r['deps']), None)
        dep = next((r for r in free if r['role'] == dep_role and (word is None or any(w in r['name'] for w in word))), None)
        if host is not None and dep is not None:
            free.remove(dep)
            host['deps'].append(dep)
    for room in free:
        if room['role'] in ('entrance', 'corridor'):
            continue
        if room['role'] in ('pantry', 'dressing'):
            room['role_slot'] = 'service'
        hosts.append(room)
    return hosts


def _area(room):
    return room['target'][0] * room['target'][1] if room['target'] else DEFAULT_M2.get(room['role'], 6.0)


def _dep_width(dep):
    return min(max(dep['target'][0] if dep['target'] else 1.8, 1.2), 3.6)


def _dep_depth(dep):
    return max(_area(dep) / _dep_width(dep), MIN_SERVICE) if dep['target'] else MIN_SERVICE


def _row_depth(room, width):
    """(depth, dependent strip width) of a host row across a column of ``width``.

    Dependents share one strip on the outer side, stacked along the row."""
    dep_w = max([_dep_width(dep) for dep in room['deps']] or [0.0])
    host_w = width - dep_w
    minimum = MIN_HABITABLE if room['role'] in HABITABLE else MIN_SERVICE
    if host_w < minimum - EPS:
        raise _NotFitted()
    depth = max(_area(room) / host_w, minimum, sum(_dep_depth(dep) for dep in room['deps']))
    return depth, dep_w


def _pack(rows, width, depth):
    """Place rows down a column; leftover depth goes to rows without a target size first."""
    if not rows:
        return []
    sized = [(room,) + _row_depth(room, width) for room in rows]
    used = sum(d for _, d, _ in sized)
    if used > depth + EPS:
        raise _NotFitted()
    slack = depth - used
    flexible = [i for i, (room, _, _) in enumerate(sized) if not room['target']] or \
               [i for i, (room, _, _) in enumerate(sized) if room['approx']] or list(range(len(sized)))
    weights = sum(sized[i][1] for i in flexible)
    out = []
    for i, (room, d, dep_w) in enumerate(sized):
        out.append((room, d + (slack * d / weights if i in flexible else 0.0), dep_w))
    return out


def _floor(level, frame, kind, left_w=CORE_W):
    """Rooms of one floor in the local frame, or raise _NotFitted.

    ``left_w`` is the service column's width (at least the core's): the foyer
    widens to reach the corridor beside it."""
    lw, ld, stairs, lift = frame['lw'], frame['ld'], frame['stairs'], frame['lift']
    if lw < left_w + CORRIDOR_W + MIN_HABITABLE - EPS or ld < F.STAIR_D + MIN_SERVICE - EPS:
        raise _NotFitted()
    rooms, links = [], []

    def add(role, name, rect, **extra):
        room = {'role': role, 'name': name, 'rect': [_r2(v) for v in rect], 'walls': ['N', 'S', 'E', 'W'],
                'doors': [], 'windows': [], 'points': [], **extra}
        rooms.append(room)
        return room
    core_d = F.STAIR_D if (stairs or lift) else F.LOBBY_D
    hub = add('entrance' if kind != 'upper' else 'lobby', 'بهو مدخل العمارة' if kind != 'upper' else 'بسطة الدرج',
              [F.STAIR_W, 0, F.LIFT_W, F.LOBBY_D if lift else core_d], slot='hub')
    if stairs:
        links.append((hub, add('stairs', 'الدرج', [0, 0, F.STAIR_W, F.STAIR_D], core_id='stairs_core', slot='stairs')))
    if lift:
        links.append((hub, add('elevator', 'المصعد', [F.STAIR_W, F.LOBBY_D, F.LIFT_W, F.LIFT_D], core_id='elevator_core',
                               slot='elevator')))
    if kind == 'parking':
        park = add('parking', 'مواقف تحت المبنى', [CORE_W, 0, lw - CORE_W, ld], slot='parking')
        park['walls'] = 'none'
        links.append((hub, park))
        return rooms, links
    program_rooms = _rooms_of(level)
    own = lambda role: next((r for r in program_rooms if r['role'] == role), None)
    entrance, corridor_room = own('entrance'), own('corridor')
    foyer = add('entrance', entrance['name'] if entrance else 'مدخل الشقة',
                [CORE_W, 0, left_w - CORE_W + CORRIDOR_W, F.LOBBY_D], unit=True, slot='foyer')
    corridor = add('corridor', corridor_room['name'] if corridor_room else 'ممر الشقة',
                   [left_w, F.LOBBY_D, CORRIDOR_W, ld - F.LOBBY_D], unit=True, slot='corridor')
    links += [(hub, foyer), (foyer, corridor)]
    hosts = _rows([r for r in program_rooms if r is not entrance and r is not corridor_room])
    main = [r for r in hosts if r['role'] in MAIN and r.get('role_slot') != 'service']
    main.sort(key=lambda r: MAIN.index(r['role']))
    service = [r for r in hosts if r not in main]
    service.sort(key=lambda r: SERVICE.index(r['role']) if r['role'] in SERVICE else len(SERVICE))
    right_w = lw - left_w - CORRIDOR_W
    right_d, left_d = ld, ld - core_d
    # Overflow moves the last rows of a full column to the other one.
    for _ in range(len(hosts) + 1):
        try:
            right, left = _pack(main, right_w, right_d), _pack(service, left_w, left_d)
            break
        except _NotFitted:
            need = lambda rows, w: sum(_row_depth(r, w)[0] for r in rows)
            if main and need(main, right_w) > right_d + EPS and need(service + main[-1:], left_w) <= left_d + EPS:
                service.append(main.pop())
            elif service and need(service, left_w) > left_d + EPS and need(main + service[-1:], right_w) <= right_d + EPS:
                main.append(service.pop())
            else:
                raise
    else:
        raise _NotFitted()
    for column, x0, width, z0, corridor_side in ((right, left_w + CORRIDOR_W, right_w, 0.0, 'W'),
                                                 (left, 0.0, left_w, core_d, 'E')):
        z = z0
        for room, depth, dep_w in column:
            host_x = x0 if corridor_side == 'W' else x0 + dep_w
            host = add(room['role'], room['name'], [host_x, z, width - dep_w, depth], unit=True, program=room)
            if room['role'] in OPEN_ROLES:
                host['walls'] = 'none'
            # The corridor when the row runs along it for a door's width, else the foyer.
            links.append((corridor if z + depth - max(z, F.LOBBY_D) >= 1.1 else foyer, host))
            dz = z
            for n, dep in enumerate(room['deps']):
                # The last dependent takes what is left of the row's depth.
                dd = z + depth - dz if n == len(room['deps']) - 1 and not dep['target'] else _dep_depth(dep)
                if dd < MIN_SERVICE - EPS or dz + dd > z + depth + EPS:
                    raise _NotFitted()
                dx = x0 + width - dep_w if corridor_side == 'W' else x0
                links.append((host, add(dep['role'], dep['name'], [dx, dz, dep_w, dd], unit=True, program=dep)))
                dz += dd
            z += depth
    return rooms, links


def _penalty(level, rooms):
    """How far a candidate floor's sizes are beyond their advisory tolerance."""
    if not level['units']:
        return 0.0
    total = 0.0
    for target, room in F.size_matches(level, [r for r in rooms if r.get('program') is not None]):
        soft, hard = F.TOLERANCE[bool(target['approx'])]
        off = abs(F._deviation(target, room))
        total += max(0.0, off - soft) + (10.0 if off > hard + 1e-9 else 0.0)
    return total


def _widths(frame):
    """Service-column widths to try, in 0.2 m steps from the core's width."""
    out, width = [], CORE_W
    while width <= frame['lw'] - CORRIDOR_W - MIN_HABITABLE + EPS:
        out.append(round(width, 2))
        width += 0.2
    return out


def _best_width(floors, frame):
    """One service-column width for every floor (wet rooms and walls stack), the
    one whose rooms come closest to their target sizes. Returns
    (width, {index: (rooms, links)}) or (None, index of the first floor that
    fits no width)."""
    best, fits = None, {i: False for i, _, _ in floors}
    for width in _widths(frame):
        laid, score = {}, 0.0
        for i, level, kind in floors:
            try:
                rooms, links = _floor(copy.deepcopy(level), frame, kind, width)
            except _NotFitted:
                laid = None
                continue
            fits[i] = True
            if laid is not None:
                laid[i] = (rooms, links)
                score += _penalty(level, rooms)
        if laid is not None and (best is None or score < best[0] - 1e-9):
            best = (score, width, laid)
    if best is None:
        return None, next((i for i, ok in fits.items() if not ok), floors[0][0])
    return best[1], best[2]


def _to_land(rect, frame):
    """Local frame (street north, core west) to land coordinates."""
    x, z, w, d = rect
    ex, ez, ew, ed = frame['envelope']
    if frame['flip']:
        x = frame['lw'] - x - w
    front = frame['front']
    if front == 'N':
        return [ex + x, ez + z, w, d]
    if front == 'S':
        return [ex + ew - x - w, ez + ed - z - d, w, d]
    if front == 'W':
        return [ex + z, ez + ed - x - w, d, w]
    return [ex + ew - z - d, ez + x, d, w]  # E


def _frame(program, envelope, front, lift, stairs, flip):
    ex, ez, ew, ed = envelope
    lw, ld = (ew, ed) if front in ('N', 'S') else (ed, ew)
    return {'envelope': envelope, 'front': front, 'lw': lw, 'ld': ld, 'lift': lift, 'stairs': stairs, 'flip': flip}


def _best_flip(program, envelope, front, lift, stairs):
    """Put the core on the side the brief states (no statement: the local west)."""
    position = program['core'].get('position') or ''
    best = None
    for flip in (False, True):
        frame = _frame(program, envelope, front, lift, stairs, flip)
        x, z, w, d = _to_land([0, 0, F.STAIR_W, F.STAIR_D], frame)
        cx, cz = x + w / 2, z + d / 2
        ex, ez, ew, ed = envelope
        score = 0.0
        if 'W' in position: score += cx - ex
        if 'E' in position: score += ex + ew - cx
        if 'N' in position: score += cz - ez
        if 'S' in position: score += ez + ed - cz
        if best is None or score < best[0] - EPS:
            best = (score, frame)
    return best[1]


def _doors(a, b, outside=None):
    from acs_residential_access import OPPOSITE, edge
    for side, other in OPPOSITE.items():
        line, lo, hi = edge(a, side)
        line2, lo2, hi2 = edge(b, other)
        low, high = max(lo, lo2), min(hi, hi2)
        if abs(line - line2) < 1e-4 and high - low >= 1.1:
            centre = (low + high) / 2
            a['doors'].append({'id': a['id'] + '_door_' + str(len(a['doors'])), 'edge': side,
                               'offset': round(centre - lo, 4), 'width': 0.9, 'height': 2.1, 'material': 'wood'})
            if b.get('walls') != 'none':
                b['doors'].append({'id': b['id'] + '_door_' + str(len(b['doors'])), 'edge': other,
                                   'offset': round(centre - lo2, 4), 'width': 0.9, 'height': 2.1, 'material': 'wood'})
            return True
    return False


def _finish(rooms, links, rules, ground, front):
    """Doors, the street door of the ground lobby, windows and one light per room."""
    import acs_plot_rules as P
    from acs_residential_access import edge
    for a, b in links:
        if not _doors(a, b) and a.get('walls') != 'none' and b.get('walls') != 'none':
            raise _NotFitted()
    if ground:
        hub = next(r for r in rooms if r.get('slot') == 'hub')
        _, lo, hi = edge(hub, front)
        hub['doors'].append({'id': hub['id'] + '_door_street', 'edge': front, 'offset': round((hi - lo) / 2, 4),
                             'width': 1.2, 'height': 2.1, 'material': 'wood'})
    streets = set(rules['streets']) if rules else {front}
    for room in rooms:
        x, z, w, d = room['rect']
        room['points'] = [{'id': room['id'] + '_light', 'type': 'light', 'x': round(w / 2, 4), 'z': round(d / 2, 4)}]
        if room['role'] in {'corridor', 'entrance', 'lobby', 'stairs', 'elevator', 'parking', 'pantry', 'storage'} \
                or room.get('walls') == 'none':
            continue
        for side in ('N', 'S', 'E', 'W'):
            line, lo, hi = edge(room, side)
            if hi - lo < 1.8 or any(o['edge'] == side for o in room['doors']):
                continue
            other, _ = P._across(rooms, room, {'edge': side, 'offset': (hi - lo) / 2})
            if other is not None:
                continue
            if rules is not None:
                gap = P._plot_distance(rules, room, side)
                limit = min(rules['setbacks_m'][side], rules['window_min_m'])
                if side not in streets and (gap < P.EPS or gap < limit - P.EPS):
                    continue
            bath = room['role'] in ('bathroom', 'laundry')
            room['windows'].append({'id': room['id'] + '_window', 'edge': side, 'offset': round((hi - lo) / 2, 4),
                                    'width': 0.6 if bath else 1.2, 'height': 0.6 if bath else 1.2,
                                    'sill': 1.5 if bath else 0.9})
            break


def _frame_inputs(program, requirements, rules):
    if rules is not None:
        return list(rules['envelope']), rules['streets'][0], {'w': rules['land']['w'], 'd': rules['land']['d']}
    found = F._envelope(program, requirements, None)
    if found is None:
        return None
    site, envelope, _ = found
    streets = program['site']['street_sides']
    return envelope, streets[0] if streets else 'N', site


def _fail(index, why):
    return PlanError(F.FLOOR_NOT_FITTED + str(index),
                     'تعذّر على التوزيع البديل ترتيب ' + F.floor_name(index) + ' ببرنامجه داخل كتلة المبنى: ' + why)


def propose(program, brief, requirements, rules=None):
    """A checked fallback building for a confirmed per-floor program.

    Raises PlanError FLOOR_NOT_FITTED + index naming the first floor that
    could not be fitted or that fails a check; never returns identical floors
    for different programs."""
    inputs = _frame_inputs(program, requirements, rules)
    levels = program['levels']
    if inputs is None:
        raise _fail(0, 'أبعاد الأرض أو المبنى غير معروفة.')
    envelope, front, site = inputs
    stairs, lift = len(levels) > 1, F.elevator(program, brief)
    frame = _best_flip(program, envelope, front, lift, stairs)
    pilotis = rules is not None and rules['parking']['placement'] == 'pilotis'
    floors, templates, keys, todo = {}, [], {}, []
    for i, level in enumerate(levels):
        key = F.signature(level) + ('|ground' if i == 0 else '')
        if key in keys:
            templates.append(keys[key])
            continue
        template = 'level_' + str(i)
        keys[key] = template
        templates.append(template)
        parking = i == 0 and not level['units'] and (level['use'] == 'parking' or pilotis)
        if not parking and len(level['units']) != 1:
            raise _fail(i, 'التوزيع البديل يرتب شقة واحدة في الدور، وفي هذا الدور ' + str(len(level['units'])) + ' شقق.')
        todo.append((i, level, 'parking' if parking else 'ground' if i == 0 else 'upper'))
    width, laid = _best_width(todo, frame)
    if width is None:
        raise _fail(laid, 'لا تتسع الغرف بمقاساتها الدنيا أو المستهدفة في ' + _dims(envelope) + '.')
    for i, level, kind in todo:
        template = templates[i]
        rooms, links = laid[i]
        seen = {}
        for room in rooms:
            slot = room.get('slot')
            name = slot or room['role']
            seen[name] = seen.get(name, 0) + 1
            room['id'] = template + '_' + name + ('' if slot else '_' + str(seen[name]))
            if room.pop('unit', False):
                room['unit_id'] = 'apartment_1'
            room.pop('program', None)
            room['rect'] = [_r2(v) for v in _to_land(room['rect'], frame)]
        try:
            _finish(rooms, links, rules, kind != 'upper', front)
        except _NotFitted:
            raise _fail(i, 'تعذّر وصل كل الغرف بأبواب في ' + _dims(envelope) + '.') from None
        for room in rooms:
            room.pop('slot', None)
        floors[template] = {'rooms': rooms}
    building = {'site': dict(site), 'floor_height': 3.2, 'wall_h': 3.0, 'wall_t': 0.2,
                'levels': [{'id': 'L' + str(i), 'index': i, 'template': t} for i, t in enumerate(templates)],
                'floors': floors,
                'meta': {'assumptions': [
                    'توزيع بديل حتمي بعد تعذّر مقترح الذكاء الاصطناعي: لكل دور برنامجه المؤكد؛ النواة (الدرج والبسطة '
                    'والمصعد) في الموضع نفسه بكل الأدوار، ومدخل الشقة بجوار البسطة ثم ممر إلى الخلف.',
                    'عمود الخدمات (المطبخ والحمامات والغسيل) تحت النواة في الموضع نفسه بكل الأدوار، والغرف الرئيسية '
                    'في العمود المقابل؛ عرض الممر 1.2 م وأقل ضلع لغرفة سكنية 2.7 م افتراضات تصميمية قابلة للتعديل.',
                    'لا يتضمن هذا التوزيع إثبات الإنشاء أو الإخلاء أو الحريق أو كفاية الإضاءة والتهوية.'],
                    'acs_layout_method': 'floor_program_fallback_v1'}}
    if rules is not None:
        import acs_plot_rules as P
        P.stamp(building, rules)
    _check(building, program, brief, requirements, rules, templates)
    return building


def _dims(envelope):
    return 'كتلة ' + F._fmt(envelope[2]) + ' × ' + F._fmt(envelope[3]) + ' م'


def _check(building, program, brief, requirements, rules, templates):
    """Fail closed with the first floor a check names."""
    from acs_residential_access import detail_issues
    from acs_residential_generation import check_rooms
    first = {}
    for i, t in enumerate(templates):
        first.setdefault(t, i)

    def floor_of(finding):
        ref = finding.get('room_ref') if isinstance(finding, dict) else None
        template = ref[0] if isinstance(ref, list) and ref else None
        if template is None and isinstance(finding, dict):
            text = str(finding.get('message') or '')
            template = next((t for t in first if '[' + t + '/' in text or '[' + t + ']' in text), None)
        return first.get(template, 0)
    try:
        check_rooms(building)
    except PlanError:
        raise _fail(0, 'لم تتطابق النواة بين الأدوار.') from None
    geometry, _ = _geometry(building)
    if geometry:
        raise _fail(floor_of(geometry[0]), 'تداخلت الفراغات أو خرجت عن الأرض.')
    access = detail_issues(building)
    if access:
        hanging = 'معلّق' in str(access[0].get('message'))
        raise _fail(floor_of(access[0]), 'جزء من غرفه لا يقع فوق بناء في الدور الأسفل.' if hanging
                    else 'لم تكتمل الأبواب أو مسار الدخول إلى كل الغرف.')
    if rules is not None:
        import acs_plot_rules as P
        blocking, _ = P.check(building, rules)
        if blocking:
            raise _fail(floor_of(blocking[0]), 'خالف التوزيع اشتراطات الأرض (' + str(blocking[0].get('code')) + ').')
    counts = [r for r in requirements if isinstance(r, dict) and r.get('metric') in (
        'level_count', 'unit_count', 'unit_count_per_level', 'room_count', 'room_count_per_unit') + F.PER_LEVEL_METRICS]
    mismatched = _program(building, brief, counts) if counts else []
    if mismatched:
        rid = mismatched[0].get('requirement_id')
        row = next((r for r in counts if r.get('id') == rid), {})
        raise _fail(row.get('level') if type(row.get('level')) is int else 0, 'لم يطابق عدد الغرف المتطلبات المؤكدة.')
    blocking, _ = F.check(building, program, requirements)
    if blocking:
        raise _fail(floor_of(blocking[0]), 'لم تقترب مقاسات الغرف من المقاسات المستهدفة ضمن المسموح.')
