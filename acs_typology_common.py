"""Shared geometry, findings and table rules for the typology instruction packs.

The packs (acs_typology_office, _retail, _school, _mosque, _hotel) give the
planner professional rules for building types ACS does not generate yet. This
module holds what they share: room geometry on the canonical Building JSON
(rect = [x, z, w, d], x east, z south, z=0 the north facade), storey handling,
door-aware connectivity, an egress approximation, occupant loads, plumbing
fixture counts and the table-driven room checks.

Nothing here is wired into generation, review or the UI (see
docs/research/typologies_integration_plan.md). Every number is a planning
reference with a cited source (SOURCES), never a compliance verdict: a finding
says the layout misses a stated reference, not that a code is met when it is
silent. Severity follows the evidence: 'error' for a defining program or
geometry failure, 'advisory' for practice and for code limits whose inputs
(sprinklers, the real occupancy) the plan does not state.
"""
import math
from collections import defaultdict

EPS = 1e-4
SHARED_EDGE_MIN_M = 0.6        # same as acs_validate.SHARED_EDGE_MIN: a wall, not a corner touch
FT = 0.3048                    # metres per foot
SQFT = FT * FT                 # square metres per square foot
EDGES = ('N', 'S', 'E', 'W')
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
SEVERITIES = ('error', 'advisory')
BASES = ('program', 'code', 'saudi_guide', 'practice')
MAX_FINDINGS = 128

# Roles every pack shares. Outdoor spaces are exterior for daylight and doors.
CORE_ROLES = frozenset({'stairs', 'elevator', 'service_elevator'})
STAIR_ROLES = frozenset({'stairs'})
CIRCULATION_ROLES = frozenset({'corridor', 'lobby', 'entrance', 'reception', 'stairs', 'elevator',
                               'service_elevator', 'women_entrance', 'shoe_area', 'residential_lobby'})
ENTRANCE_ROLES = frozenset({'entrance', 'lobby', 'women_entrance', 'residential_lobby'})
OUTDOOR_ROLES = frozenset({'courtyard', 'terrace', 'balcony', 'parking', 'yard', 'garden', 'playground',
                           'roof_deck', 'sahn'})
TOILET_ROLES = frozenset({'toilet', 'toilet_male', 'toilet_female', 'toilet_accessible',
                          'toilet_students', 'toilet_staff', 'bathroom'})

# Sources cited by the tables. Each pack adds its own; keys are stable.
SOURCES = {
    'IBC2015_T1004.1.2': {
        'title': 'IBC 2015 Table 1004.1.2 Maximum floor area allowances per occupant '
                 '(base code of SBC 201-2018)',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2021_T1004.5': {
        'title': 'IBC 2021 Table 1004.5 (business 150 gross, mercantile 60 gross)',
        'url': 'https://codes.iccsafe.org/content/IBC2021P2/chapter-10-means-of-egress'},
    'IBC2015_1005.3': {
        'title': 'IBC 2015 1005.3.1/1005.3.2 egress capacity 7.6 / 5.1 mm per occupant',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2015_T1006.3.1': {
        'title': 'IBC 2015 Table 1006.3.1 exits per storey (2 / 3 / 4) and Table 1006.3.2(2) single exits',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2015_1007.1.1': {
        'title': 'IBC 2015 1007.1.1 exit separation: 1/2 of the diagonal, 1/3 sprinklered',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2015_1011.2': {
        'title': 'IBC 2015 1011.2 stair width 1118 mm (914 mm below 50 occupants)',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2015_T1017.2': {
        'title': 'IBC 2015 Table 1017.2 exit access travel distance',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IBC2015_T1020.2': {
        'title': 'IBC 2015 Table 1020.2 minimum corridor width; 1020.4 dead ends',
        'url': 'https://codes.iccsafe.org/content/IBC2015/chapter-10-means-of-egress'},
    'IPC2015_T403.1': {
        'title': 'IPC 2015 Table 403.1 minimum plumbing fixtures; 403.2 separate facilities; '
                 '403.3.3 within one storey and 152 m (base of SBC 701)',
        'url': 'https://codes.iccsafe.org/content/IPC2015/chapter-4-fixtures-faucets-and-fixture-fittings'},
    'SBC201_BASE': {
        'title': 'SBC 201-2018 is adapted from IBC 2015 (ICC; Japan MLIT summary)',
        'url': 'https://www.mlit.go.jp/common/001404290.pdf'},
    'ACS_STAIRS': {
        'title': 'ACS U-stair geometry (acs_stairs.resolve_stair_geometry): width = 2 flights + gap',
        'url': 'acs_stairs.py'},
}


# ── geometry ────────────────────────────────────────────────────────────────
def num(value):
    return type(value) in (int, float) and math.isfinite(value)


def valid_rect(room):
    rect = room.get('rect') if isinstance(room, dict) else None
    return (isinstance(rect, list) and len(rect) == 4 and all(num(v) for v in rect)
            and rect[2] > 0 and rect[3] > 0)


def role(room):
    value = room.get('role') if isinstance(room, dict) else None
    return value.strip().lower() if isinstance(value, str) else ''


def area(room):
    return room['rect'][2] * room['rect'][3]


def min_side(room):
    return min(room['rect'][2], room['rect'][3])


def centre(room):
    x, z, w, d = room['rect']
    return (x + w / 2.0, z + d / 2.0)


def edge(room, side):
    """(line, lo, hi) of one side: N/S lines are z values, E/W lines x values."""
    x, z, w, d = room['rect']
    if side == 'N':
        return z, x, x + w
    if side == 'S':
        return z + d, x, x + w
    if side == 'W':
        return x, z, z + d
    return x + w, z, z + d


def enclosed(room):
    walls = room.get('walls')
    if isinstance(walls, str) and walls.lower() in ('none', 'line'):
        return False
    if isinstance(walls, list) and not walls:
        return False
    return role(room) not in OUTDOOR_ROLES


def contact(a, b):
    """Touching sides of a: [(side, lo, hi)] where b lies directly across."""
    out = []
    for side, other in OPPOSITE.items():
        line, lo, hi = edge(a, side)
        line2, lo2, hi2 = edge(b, other)
        low, high = max(lo, lo2), min(hi, hi2)
        if abs(line - line2) <= EPS and high - low > EPS:
            out.append((side, low, high))
    return out


def shared_length(a, b):
    return sum(hi - lo for _, lo, hi in contact(a, b))


def point_on(room, side, along):
    """Plan point on one side of a room at a coordinate along that side."""
    line = edge(room, side)[0]
    return (along, line) if side in ('N', 'S') else (line, along)


def door_spans(room, side):
    """Global (lo, hi) spans of the room's doors on one side."""
    _, origin, _ = edge(room, side)
    out = []
    for door in room.get('doors') or []:
        if not isinstance(door, dict) or door.get('edge') != side:
            continue
        off, width = door.get('offset'), door.get('width')
        if num(off) and num(width) and width > 0:
            out.append((origin + off - width / 2.0, origin + off + width / 2.0))
    return out


def has_doors(rooms):
    return any(isinstance(r.get('doors'), list) and r['doors'] for r in rooms)


def portal(a, b, doors):
    """A plan point where one can pass from a to b, or None.

    Without door data (a layout before openings) a shared wall of at least
    SHARED_EDGE_MIN_M is a potential passage. With door data a door on either
    side must lie on the shared segment; an open (wall-less) side passes."""
    for side, lo, hi in contact(a, b):
        if hi - lo < (EPS if doors else SHARED_EDGE_MIN_M - EPS):
            continue
        if not doors or not enclosed(a) or not enclosed(b):
            return point_on(a, side, (lo + hi) / 2.0)
        spans = door_spans(a, side) + door_spans(b, OPPOSITE[side])
        for p, q in spans:
            if min(q, hi) - max(p, lo) > EPS:
                return point_on(a, side, (max(p, lo) + min(q, hi)) / 2.0)
    return None


def exterior_runs(room, rooms, side):
    """Spans of one side not covered by an enclosed indoor neighbour."""
    line, lo, hi = edge(room, side)
    covered = []
    for other in rooms:
        if other is room or not enclosed(other):
            continue
        line2, lo2, hi2 = edge(other, OPPOSITE[side])
        if abs(line - line2) <= EPS and min(hi, hi2) - max(lo, lo2) > EPS:
            covered.append((max(lo, lo2), min(hi, hi2)))
    runs, cursor = [], lo
    for a, b in sorted(covered):
        if a - cursor > EPS:
            runs.append((cursor, a))
        cursor = max(cursor, b)
    if hi - cursor > EPS:
        runs.append((cursor, hi))
    return runs


def exterior_length(room, rooms, sides=EDGES):
    return sum(b - a for side in sides for a, b in exterior_runs(room, rooms, side))


def longest_exterior_run(room, rooms, sides=EDGES):
    return max([b - a for side in sides for a, b in exterior_runs(room, rooms, side)] or [0.0])


def exterior_sides(room, rooms, min_run=1.0):
    return [s for s in EDGES if any(b - a >= min_run - EPS for a, b in exterior_runs(room, rooms, s))]


def daylight_depth(room, rooms, min_run=1.0):
    """Room depth behind its best window wall, or None without an exterior side.

    The depth is measured square to an exterior side with a run of at least
    ``min_run``; opposite exterior sides halve it (daylight from both). A
    planning approximation of the distance from a workplace to a window."""
    sides = exterior_sides(room, rooms, min_run)
    if not sides:
        return None
    w, d = room['rect'][2], room['rect'][3]
    depths = []
    for s in sides:
        depth = d if s in ('N', 'S') else w
        if OPPOSITE[s] in sides:
            depth /= 2.0
        depths.append(depth)
    return min(depths)


def exterior_door(room, rooms):
    """A door on an exterior run of the room (opens to the outside)."""
    for side in EDGES:
        runs = exterior_runs(room, rooms, side)
        for p, q in door_spans(room, side):
            if any(min(q, b) - max(p, a) > EPS for a, b in runs):
                return True
    return False


# ── storeys ─────────────────────────────────────────────────────────────────
def occupied_levels(building):
    levels = building.get('levels') if isinstance(building, dict) else None
    out = [l for l in levels or [] if isinstance(l, dict) and l.get('kind') != 'roof'
           and isinstance(l.get('template'), str)]
    return sorted(out, key=lambda l: l['index'] if type(l.get('index')) is int else 0)


def storeys(building):
    """[(template, first level index, instance count)] from the ground up."""
    first, count = {}, defaultdict(int)
    for level in occupied_levels(building):
        t = level['template']
        first.setdefault(t, level['index'] if type(level.get('index')) is int else 0)
        count[t] += 1
    return [(t, first[t], count[t]) for t in first]


def template_indices(building):
    """{template: [every occupied level index that uses it]}."""
    out = defaultdict(list)
    for level in occupied_levels(building):
        out[level['template']].append(level['index'] if type(level.get('index')) is int else 0)
    return out


def rooms_of(building, template):
    floor = (building.get('floors') or {}).get(template)
    rooms = floor.get('rooms') if isinstance(floor, dict) else None
    return [r for r in rooms or [] if isinstance(r, dict) and valid_rect(r)]


def floor_name(index):
    names = {0: 'الدور الأرضي', 1: 'الدور الأول', 2: 'الدور الثاني', 3: 'الدور الثالث',
             4: 'الدور الرابع', 5: 'الدور الخامس'}
    return names.get(index, 'الدور ' + str(index))


def label(template, room):
    name = room.get('name') if isinstance(room.get('name'), str) and room['name'].strip() else room.get('id')
    return '[' + str(template) + '/' + str(room.get('id')) + '] «' + str(name).strip()[:60] + '» '


def fmt(value):
    return ('%.2f' % value).rstrip('0').rstrip('.')


def finding(code, severity, message, basis, source=None, template=None, room=None, fix=None, **data):
    if severity not in SEVERITIES or basis not in BASES:
        raise ValueError('invalid finding severity or basis')
    out = {'code': code, 'severity': severity, 'basis': basis, 'message': message}
    if source:
        out['source'] = source
    if template is not None and room is not None:
        out['room_ref'] = [template, room.get('id')]
    if fix:
        out['fix'] = fix
    out.update(data)
    return out


def split(findings):
    """(blocking, advisory), each bounded."""
    blocking = [f for f in findings if f['severity'] == 'error'][:MAX_FINDINGS]
    advisory = [f for f in findings if f['severity'] == 'advisory'][:MAX_FINDINGS]
    return blocking, advisory


# ── connectivity ────────────────────────────────────────────────────────────
def graph(rooms):
    """Passages between rooms of one storey: {i: {j: plan point}}."""
    doors = has_doors(rooms)
    links = defaultdict(dict)
    for i, a in enumerate(rooms):
        for j in range(i + 1, len(rooms)):
            p = portal(a, rooms[j], doors)
            if p is not None:
                links[i][j] = p
                links[j][i] = p
    return links


def reachable(start, allowed, links):
    seen = {i for i in start if i in allowed}
    stack = list(seen)
    while stack:
        for j in links[stack.pop()]:
            if j in allowed and j not in seen:
                seen.add(j)
                stack.append(j)
    return seen


def linked_roles(index, rooms, links):
    return {role(rooms[j]) for j in links[index]}


# ── occupant load and egress ────────────────────────────────────────────────
def occupant_load(rooms, loads):
    """Occupants of one storey from {role: (m2 per occupant, 'net'|'gross')}.

    Net factors apply to the room's own area. Gross factors apply to the room
    plus the storey's support area (circulation, toilets, cores, service rooms
    without a factor) shared in proportion: conservative, never below net."""
    net = gross = 0.0
    gross_area = support = 0.0
    gross_parts = []
    for room in rooms:
        if not enclosed(room) and role(room) in OUTDOOR_ROLES:
            continue
        factor = loads.get(role(room))
        if factor is None:
            support += area(room)
        elif factor[1] == 'net':
            net += area(room) / factor[0]
        else:
            gross_area += area(room)
            gross_parts.append((area(room), factor[0]))
    for a, f in gross_parts:
        gross += (a + support * a / gross_area) / f
    return int(math.ceil(net + gross - 1e-9))


def required_exits(load, storey_index, single_exit_max):
    """IBC 2015 Table 1006.3.1 and Table 1006.3.2(2), by storey position."""
    if load <= 0:
        return 0
    allowance = single_exit_max.get(min(storey_index, 2), 0)
    if load <= allowance:
        return 1
    return 2 if load <= 500 else 3 if load <= 1000 else 4


def exits(rooms, at_ground, ground_roles=ENTRANCE_ROLES):
    """Indices of rooms that count as an exit on this storey.

    Above ground: each stairs room (an exit stair). On the ground storey: a
    room with a door to the outside, or before doors exist a room of
    ``ground_roles`` (entrances, lobbies; shops for retail) or a stair that
    can discharge outside, with an exterior wall run of at least one metre."""
    doors = has_doors(rooms)
    out = []
    for i, room in enumerate(rooms):
        if not at_ground:
            if role(room) in STAIR_ROLES:
                out.append(i)
        elif doors:
            if enclosed(room) and exterior_door(room, rooms):
                out.append(i)
        elif (role(room) in ground_roles or role(room) in STAIR_ROLES) \
                and longest_exterior_run(room, rooms) >= 1.0 - EPS:
            out.append(i)
    return out


def travel_distances(rooms, exit_ids):
    """Approximate exit-access travel per room: {index: metres}.

    Nodes are passage points; travel inside a rectangle is straight (it is
    convex). A room's distance is its farthest corner to the best passage plus
    that passage's distance to an exit room. Travel inside the exit room itself
    (a lobby to its street door, a shop to its own door) counts as 0, which
    favours large lobbies. A planning approximation, not a code measurement."""
    links = graph(rooms)
    nodes = {}
    for i in links:
        for j, p in links[i].items():
            nodes.setdefault((min(i, j), max(i, j)), p)
    dist = {key: 0.0 if (key[0] in exit_ids or key[1] in exit_ids) else math.inf for key in nodes}
    by_room = defaultdict(list)
    for key in nodes:
        by_room[key[0]].append(key)
        by_room[key[1]].append(key)
    changed = True
    rounds = 0
    while changed and rounds < len(nodes) + 2:
        changed, rounds = False, rounds + 1
        for i, keys in by_room.items():
            if i in exit_ids:
                continue
            for a in keys:
                for b in keys:
                    if a is b or dist[b] == math.inf:
                        continue
                    pa, pb = nodes[a], nodes[b]
                    value = dist[b] + math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                    if value < dist[a] - 1e-9:
                        dist[a], changed = value, True
    out = {}
    for i, room in enumerate(rooms):
        if i in exit_ids:
            out[i] = 0.0
            continue
        x, z, w, d = room['rect']
        corners = ((x, z), (x + w, z), (x, z + d), (x + w, z + d))
        out[i] = max(min((math.hypot(c[0] - nodes[k][0], c[1] - nodes[k][1]) + dist[k]
                          for k in by_room.get(i, ()) if dist[k] < math.inf), default=math.inf)
                     for c in corners)
    return out


def storey_diagonal(rooms):
    xs = [r['rect'][0] for r in rooms] + [r['rect'][0] + r['rect'][2] for r in rooms]
    zs = [r['rect'][1] for r in rooms] + [r['rect'][1] + r['rect'][3] for r in rooms]
    return math.hypot(max(xs) - min(xs), max(zs) - min(zs)) if rooms else 0.0


def egress_findings(building, loads, limits, options=None):
    """Exits per storey, exit separation, travel distance, corridor and stair widths.

    ``limits``: {'travel_m': (unsprinklered, sprinklered), 'single_exit': {storey: max load},
    'corridor_m': callable(load) -> min width, optional 'ground_exit_roles' and
    'exits': callable(rooms, load, highest storey index) -> required exits}. ``options['sprinklered']``
    is True, False or None (unknown). Unknown sprinklers use the sprinklered limits as
    advisories: the stricter unsprinklered limits apply until the system is designed."""
    options = options or {}
    sprinklered = options.get('sprinklered')
    sev = 'advisory' if sprinklered is None else 'error'
    use_spr = sprinklered is not False
    out = []
    tops = {t: max(ix) for t, ix in template_indices(building).items()}
    ground_roles = limits.get('ground_exit_roles', ENTRANCE_ROLES)
    for template, index, _ in storeys(building):
        rooms = rooms_of(building, template)
        if not rooms:
            continue
        load = occupant_load(rooms, loads)
        at_ground = index == 0
        # A template repeated over several storeys is judged at its highest one.
        need = (limits['exits'](rooms, load, tops[template]) if 'exits' in limits
                else required_exits(load, tops[template], limits['single_exit']))
        found = exits(rooms, at_ground, ground_roles)
        if need and len(found) < need:
            out.append(finding('EGRESS_EXITS_SHORT', 'error',
                floor_name(index) + ': حمل الإشغال التقديري ' + str(load) + ' شخصًا يحتاج ' + str(need)
                + ' مخرجين على الأقل ' + ('(أبواب خارجية أو مداخل على الواجهة)' if at_ground else '(أدراج هروب)')
                + ' والمتوفر ' + str(len(found)) + '. أضف مخرجًا أو درجًا مستقلًا متباعدًا.',
                'code', 'IBC2015_T1006.3.1', fix='add independent exits: ' + str(need) + ' needed for load '
                + str(load), template=template, storey=index, occupant_load=load, required=need,
                provided=len(found)))
        if need >= 2 and len(found) >= 2:
            pts = [centre(rooms[i]) for i in found]
            gap = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in pts for b in pts)
            ratio = 3.0 if use_spr else 2.0
            minimum = storey_diagonal(rooms) / ratio
            if gap < minimum - EPS:
                out.append(finding('EGRESS_EXITS_TOO_CLOSE', sev,
                    floor_name(index) + ': المسافة بين المخرجين ' + fmt(gap) + ' م أقل من '
                    + ('ثلث' if use_spr else 'نصف') + ' قطر الدور (' + fmt(minimum) + ' م). باعد بين الدرجين أو المخرجين.',
                    'code', 'IBC2015_1007.1.1', fix='move exits apart: >= ' + fmt(minimum) + ' m',
                    template=template, storey=index, separation_m=round(gap, 2), minimum_m=round(minimum, 2)))
        if found:
            limit = limits['travel_m'][1 if use_spr else 0]
            far = travel_distances(rooms, set(found))
            worst = max(((d, i) for i, d in far.items() if role(rooms[i]) not in CIRCULATION_ROLES),
                        default=(0.0, None))
            if worst[1] is not None and worst[0] == math.inf:
                room = rooms[worst[1]]
                out.append(finding('EGRESS_NO_PATH', 'error', label(template, room)
                    + 'لا يتصل هذا الفراغ بمخرج عبر جدران مشتركة أو أبواب. اربطه بممر يؤدي إلى مخرج.',
                    'program', fix='connect the room to circulation that leads to an exit',
                    template=template, room=room))
            elif worst[1] is not None and worst[0] > limit + EPS:
                room = rooms[worst[1]]
                out.append(finding('EGRESS_TRAVEL_TOO_LONG', sev, label(template, room)
                    + 'مسافة الوصول التقريبية إلى أقرب مخرج ' + fmt(worst[0]) + ' م تتجاوز ' + fmt(limit)
                    + ' م. أضف مخرجًا أو قرّب الدرج.', 'code', 'IBC2015_T1017.2',
                    fix='travel ' + fmt(worst[0]) + ' m > ' + fmt(limit) + ' m: add or move an exit',
                    template=template, room=room, travel_m=round(worst[0], 1), limit_m=limit))
        width = limits['corridor_m'](load)
        for room in rooms:
            if role(room) == 'corridor' and min_side(room) < width - EPS:
                out.append(finding('EGRESS_CORRIDOR_NARROW', 'error', label(template, room)
                    + 'عرض الممر ' + fmt(min_side(room)) + ' م أقل من ' + fmt(width) + ' م لحمل الدور.',
                    'code', 'IBC2015_T1020.2', fix='widen corridor to >= ' + fmt(width) + ' m',
                    template=template, room=room, width_m=round(min_side(room), 2), minimum_m=width))
        stairs = [r for r in rooms if role(r) in STAIR_ROLES]
        if stairs and len(storeys(building)) > 1:
            per_occ = (0.0051 if options.get('voice_alarm') and sprinklered else 0.0076)
            flight = max(1.118 if load >= 50 else 0.914, load * per_occ / len(stairs))
            needed = 2 * flight + 0.1
            for room in stairs:
                if min_side(room) < needed - EPS:
                    out.append(finding('EGRESS_STAIR_NARROW', 'error', label(template, room)
                        + 'عرض بيت الدرج ' + fmt(min_side(room)) + ' م لا يسع قلبتين بعرض ' + fmt(flight)
                        + ' م لكل منهما (المطلوب ' + fmt(needed) + ' م).', 'code', 'IBC2015_1011.2',
                        fix='stair room min side >= ' + fmt(needed) + ' m (two flights of ' + fmt(flight) + ' m)',
                        template=template, room=room, width_m=round(min_side(room), 2), minimum_m=round(needed, 2)))
    return out


def dead_end_findings(building, sprinklered=None):
    """Corridors that join circulation at one end only, longer than the limit."""
    limit = 15.24 if sprinklered else 6.096
    out = []
    for template, index, _ in storeys(building):
        rooms = rooms_of(building, template)
        links = graph(rooms)
        for i, room in enumerate(rooms):
            if role(room) != 'corridor':
                continue
            circ = [j for j in links[i] if role(rooms[j]) in CIRCULATION_ROLES]
            length = max(room['rect'][2], room['rect'][3])
            if len(circ) <= 1 and length > limit + EPS and length >= 2.5 * min_side(room) - EPS:
                out.append(finding('EGRESS_DEAD_END', 'advisory', label(template, room)
                    + 'ممر مسدود الطرف بطول ' + fmt(length) + ' م يتجاوز ' + fmt(limit)
                    + ' م. اجعله يصل بين مخرجين أو قصّره.', 'code', 'IBC2015_T1020.2',
                    fix='dead-end corridor ' + fmt(length) + ' m > ' + fmt(limit) + ' m',
                    template=template, room=room, length_m=round(length, 1), limit_m=limit))
    return out


# ── plumbing fixtures ───────────────────────────────────────────────────────
WC_AREA_M2 = 2.5     # one WC cubicle (1.0 x 1.5 m) with its share of lavatory and circulation
MIN_WC_ROOM_M2 = 1.5


def tiered(count, tiers):
    """Fixtures for ``count`` people from [(up_to, per)] tiers; per of the last tier is open."""
    if count <= 0:
        return 0
    total, done = 0.0, 0
    for up_to, per in tiers:
        top = count if up_to is None else min(count, up_to)
        if top > done:
            total += (top - done) / float(per)
            done = top
        if up_to is None or count <= up_to:
            break
    return int(math.ceil(total - 1e-9))


def wc_capacity(room):
    """WCs a toilet room holds: explicit toilet objects, else its area at WC_AREA_M2."""
    objects = [o for o in room.get('objects') or [] if isinstance(o, dict)
               and str(o.get('kind', '')).lower() in ('toilet', 'wc', 'urinal')]
    if objects:
        return sum(int(o['count']) if type(o.get('count')) is int and o['count'] > 0 else 1 for o in objects)
    if area(room) < MIN_WC_ROOM_M2 - EPS:
        return 0
    return max(1, int(area(room) // WC_AREA_M2))


def toilet_sex(room):
    r = role(room)
    if r.endswith('_male') or r.endswith('_men'):
        return 'male'
    if r.endswith('_female') or r.endswith('_women'):
        return 'female'
    return 'any'


def fixture_findings(building, groups, male_share, source, roles=TOILET_ROLES, separate_above=15, served=None):
    """Required WCs per sex against the toilet rooms' capacity, and storey access.

    ``groups``: [(occupant load, WC tiers male, WC tiers female)], one per use
    (mercantile and business in a mixed building add up). ``male_share`` is the
    share of male occupants (0.5 by IPC 403.1.1; a single-sex school or a men's
    prayer hall states its own share). ``served``: the roles whose storey needs
    toilets within one storey (default: every occupied room)."""
    out = []
    rooms = [(t, i, r) for t, i, _ in storeys(building) for r in rooms_of(building, t) if role(r) in roles]
    instances = {t: n for t, _, n in storeys(building)}
    cap = defaultdict(int)
    for t, _, r in rooms:
        cap[toilet_sex(r)] += wc_capacity(r) * instances[t]
    total_load = need_m = need_f = 0
    for load, tiers_m, tiers_f in groups:
        males = int(math.ceil(load * male_share - 1e-9))
        females = max(0, load - males)
        total_load += load
        need_m += tiered(males, tiers_m)
        need_f += tiered(females, tiers_f)
    have_m, have_f, have_any = cap['male'], cap['female'], cap['any']
    short = max(0, need_m - have_m) + max(0, need_f - have_f)
    if short > have_any:
        out.append(finding('FIXTURES_WC_SHORT', 'error', 'دورات المياه تسع نحو ' + str(have_m + have_f + have_any)
            + ' مرحاضًا والمطلوب ' + str(need_m) + ' للرجال و' + str(need_f) + ' للنساء لحمل إشغال '
            + str(total_load) + ' شخصًا. وسّع دورات المياه أو أضف غيرها.', 'code', source,
            fix='WCs needed male ' + str(need_m) + ' female ' + str(need_f) + '; rooms hold about '
            + str(have_m + have_f + have_any), required_male=need_m, required_female=need_f,
            provided_male=have_m, provided_female=have_f, provided_any=have_any, occupant_load=total_load))
    if total_load > separate_above and need_m and need_f and (not have_m or not have_f):
        out.append(finding('FIXTURES_NOT_SEPARATED', 'error', 'يلزم فصل دورات المياه للرجال والنساء عند حمل إشغال '
            + str(total_load) + ' شخصًا. سمِّ الأدوار toilet_male وtoilet_female.', 'code', 'IPC2015_T403.1',
            fix='separate male and female toilet rooms (role toilet_male / toilet_female)'))
    indices = template_indices(building)
    toilet_storeys = {i for t in {t for t, _, _ in rooms} for i in indices[t]}
    for t, i, _ in storeys(building):
        occupied = [r for r in rooms_of(building, t) if (role(r) in served if served is not None else
                    role(r) not in CIRCULATION_ROLES | TOILET_ROLES | OUTDOOR_ROLES)]
        if occupied and toilet_storeys and any(not ({k - 1, k, k + 1} & toilet_storeys) for k in indices[t]):
            out.append(finding('FIXTURES_TOO_FAR', 'error', floor_name(i) + ' بلا دورات مياه فيه أو في دور ملاصق.'
                + ' أضف دورة مياه في هذا الدور.', 'code', 'IPC2015_T403.1', fix='add toilets on this storey',
                template=t, storey=i))
    if not rooms and total_load > 0:
        out.append(finding('FIXTURES_NONE', 'error', 'لا توجد أي دورة مياه في المبنى وحمل الإشغال ' + str(total_load)
            + ' شخصًا.', 'code', source, fix='add male and female toilets', occupant_load=total_load))
    return out


# ── table-driven room checks ────────────────────────────────────────────────
RULE_KEYS = {'ar', 'min_area_m2', 'min_width_m', 'max_area_m2', 'adjacent_to', 'not_adjacent_to',
             'exterior', 'load', 'source', 'severity', 'basis'}
REQUIRED_RULE_KEYS = {'ar', 'min_area_m2', 'min_width_m', 'adjacent_to', 'exterior', 'source', 'severity', 'basis'}


def table_errors(table, sources):
    """Integrity problems of a room table (empty when sound)."""
    problems = []
    for key, rule in table.items():
        if not isinstance(key, str) or key != key.strip().lower() or not key:
            problems.append(str(key) + ': role must be a lower-case identifier')
        if set(rule) - RULE_KEYS or REQUIRED_RULE_KEYS - set(rule):
            problems.append(key + ': unknown keys ' + str(sorted(set(rule) - RULE_KEYS))
                            + ', missing keys ' + str(sorted(REQUIRED_RULE_KEYS - set(rule))))
            continue
        if not isinstance(rule['ar'], str) or not rule['ar'].strip():
            problems.append(key + ': Arabic name missing')
        for k in ('min_area_m2', 'min_width_m'):
            if not num(rule[k]) or rule[k] < 0:
                problems.append(key + ': ' + k + ' must be a number >= 0')
        if 'max_area_m2' in rule and not (num(rule['max_area_m2']) and rule['max_area_m2'] > rule['min_area_m2']):
            problems.append(key + ': max area must exceed min area')
        for k in ('adjacent_to', 'not_adjacent_to'):
            value = rule.get(k, ())
            if not isinstance(value, tuple) or any(not isinstance(v, str) for v in value):
                problems.append(key + ': ' + k + ' must be a tuple of roles')
        if set(rule['adjacent_to']) & set(rule.get('not_adjacent_to', ())):
            problems.append(key + ': a role is both required and forbidden as neighbour')
        if rule['exterior'] not in ('required', 'preferred', None):
            problems.append(key + ': exterior must be required, preferred or None')
        if 'load' in rule:
            load = rule['load']
            if not (isinstance(load, tuple) and len(load) == 2 and num(load[0]) and load[0] > 0
                    and load[1] in ('net', 'gross')):
                problems.append(key + ': load must be (m2 per occupant, net|gross)')
        if rule['severity'] not in SEVERITIES or rule['basis'] not in BASES:
            problems.append(key + ': severity or basis unknown')
        src = rule['source']
        if not isinstance(src, tuple) or not src or any(s not in sources for s in src):
            problems.append(key + ': unknown source ' + str(src))
    return problems


def table_findings(building, table, known_neighbours=frozenset()):
    """Size, width, access and daylight of every room whose role the table lists."""
    out = []
    for template, index, _ in storeys(building):
        rooms = rooms_of(building, template)
        links = graph(rooms)
        doors = has_doors(rooms)
        for i, room in enumerate(rooms):
            rule = table.get(role(room))
            if rule is None:
                continue
            sev, basis, src = rule['severity'], rule['basis'], rule['source'][0]
            a = area(room)
            if a < rule['min_area_m2'] - EPS:
                out.append(finding('ROOM_TOO_SMALL', sev, label(template, room) + rule['ar'] + ' مساحتها '
                    + fmt(a) + ' م² وأقل حد تخطيطي ' + fmt(rule['min_area_m2']) + ' م².', basis, src,
                    template=template, room=room, fix=role(room) + ' area ' + fmt(a) + ' < '
                    + fmt(rule['min_area_m2']) + ' m2', area_m2=round(a, 2), minimum_m2=rule['min_area_m2']))
            if min_side(room) < rule['min_width_m'] - EPS:
                out.append(finding('ROOM_TOO_NARROW', sev, label(template, room) + rule['ar'] + ' عرضها '
                    + fmt(min_side(room)) + ' م وأقل حد ' + fmt(rule['min_width_m']) + ' م.', basis, src,
                    template=template, room=room, fix=role(room) + ' width ' + fmt(min_side(room)) + ' < '
                    + fmt(rule['min_width_m']) + ' m', width_m=round(min_side(room), 2),
                    minimum_m=rule['min_width_m']))
            if 'max_area_m2' in rule and a > rule['max_area_m2'] + EPS:
                out.append(finding('ROOM_TOO_LARGE', 'advisory', label(template, room) + rule['ar'] + ' مساحتها '
                    + fmt(a) + ' م² وتتجاوز ' + fmt(rule['max_area_m2']) + ' م²؛ قسّمها أو صغّرها.', basis, src,
                    template=template, room=room, fix='split or shrink ' + role(room), area_m2=round(a, 2)))
            wanted = set(rule['adjacent_to'])
            if wanted and not (linked_roles(i, rooms, links) & wanted):
                out.append(finding('ROOM_NOT_CONNECTED', 'error', label(template, room) + rule['ar']
                    + ' لا ' + ('يفتح بباب' if doors else 'يلاصق') + ' أيًّا من: ' + '، '.join(
                        table[r]['ar'] if r in table else r for r in sorted(wanted)) + '.', 'program', src,
                    template=template, room=room, fix=role(room) + ' must ' + ('open to' if doors else 'share a wall with')
                    + ' one of ' + ', '.join(sorted(wanted))))
            # A forbidden neighbour is about a door between them: sharing a wall is fine.
            for j in links[i] if doors else ():
                other = rooms[j]
                if role(other) in rule.get('not_adjacent_to', ()):
                    out.append(finding('ROOM_FORBIDDEN_NEIGHBOUR', 'error', label(template, room) + rule['ar']
                        + ' يفتح على ' + str(other.get('name') or other.get('id')) + '، والفصل بينهما مطلوب.',
                        basis, src, template=template, room=room, fix=role(room) + ' must not open to ' + role(other),
                        neighbour=other.get('id')))
            if rule['exterior'] and longest_exterior_run(room, rooms) < 1.0 - EPS:
                out.append(finding('ROOM_NO_EXTERIOR_WALL', 'error' if rule['exterior'] == 'required' else 'advisory',
                    label(template, room) + rule['ar'] + ' بلا جدار خارجي لنافذة وإضاءة طبيعية. انقلها إلى الواجهة.',
                    basis, src, template=template, room=room, fix='move ' + role(room) + ' onto an exterior wall'))
    return out


def required_role_findings(building, required, table):
    """{role: minimum count} over all occupied storey instances."""
    counts = defaultdict(int)
    for template, _, n in storeys(building):
        for room in rooms_of(building, template):
            counts[role(room)] += n
    out = []
    for r, minimum in required.items():
        if counts[r] < minimum:
            name = table[r]['ar'] if r in table else r
            out.append(finding('PROGRAM_ROLE_MISSING', 'error', 'البرنامج يحتاج ' + str(minimum) + ' من «' + name
                + '» (role=' + r + ') والموجود ' + str(counts[r]) + '.', 'program',
                table[r]['source'][0] if r in table else None, fix='add ' + str(minimum - counts[r]) + ' x ' + r,
                role=r, required=minimum, provided=counts[r]))
    return out


def core_findings(building):
    """Every storey of a multi-storey building has stairs, and cores stack exactly."""
    out = []
    levels = storeys(building)
    if len(levels) < 2:
        return out
    ground = None
    for template, index, _ in levels:
        cores = {}
        for room in rooms_of(building, template):
            if role(room) in CORE_ROLES:
                cores[room.get('core_id') or room.get('id')] = room
        if not any(role(r) in STAIR_ROLES for r in cores.values()):
            out.append(finding('CORE_STAIRS_MISSING', 'error', floor_name(index) + ' بلا درج. لكل دور درج role=stairs '
                'بالمستطيل نفسه وcore_id نفسه في كل الأدوار.', 'program', fix='add the stairs core on this storey',
                template=template, storey=index))
            continue
        if ground is None:
            ground = (template, cores)
            continue
        for key, room in ground[1].items():
            other = cores.get(key)
            if other is not None and other['rect'] != room['rect']:
                out.append(finding('CORE_MISALIGNED', 'error', label(template, other) + 'النواة الرأسية «' + str(key)
                    + '» لا تطابق مستطيلها في الدور الأرضي ' + str(room['rect']) + '.', 'program',
                    fix='copy core rect ' + str(room['rect']) + ' with core_id ' + str(key),
                    template=template, room=other))
            elif other is None and role(room) in CORE_ROLES:
                out.append(finding('CORE_MISSING_ON_STOREY', 'error', floor_name(index) + ': النواة «' + str(key)
                    + '» الموجودة في الأرضي غير موجودة هنا.', 'program',
                    fix='add core ' + str(key) + ' rect ' + str(room['rect']), template=template, storey=index))
    return out


def instruction_sizes(**texts):
    """{name: character count}: the stated size of each instruction text."""
    return {k: len(v) for k, v in texts.items()}
