"""Deterministic warehouse planning: dock layout, truck-court placement and cited review notes.

No provider call, no randomness. The planner (acs_warehouse_generation) decides
the zones and, per dock zone, which wall gets how many dock doors; this module
turns that intent into exact dock geometry and measures the zone plan against
published planning dimensions.

The numbers below are typical planning dimensions from industry guidance and
the IBC (SBC 201 is derived from it), each tied to a SOURCES entry. They become
disclosed assumptions and non-blocking review notes, never code-compliance
results, approvals or repair errors. docs/research/warehouse_planning.md holds
the research behind every value.
"""
from __future__ import annotations

import copy
import math

# Dock doors and their spacing (metres).
DOCK_DOOR_W = 3.0           # 9-10 ft wide openings (2.74-3.05 m)        [dock]
DOCK_DOOR_H = 3.0           # 10 ft high openings (3.05 m)                [dock]
DOCK_PITCH = 4.0            # door centres, 12-14 ft (3.66-4.27 m)        [dock]
DOCK_PITCH_MIN = 3.66       # 12 ft minimum centres                       [dock]
MAX_DOCKS_PER_GROUP = 24    # canonical dock-group count limit (scorecard/handoff)
# Planning depths (metres).
STAGING_DEPTH_MIN = 16.0    # floor-drop one 53 ft / 13.6 m trailer load  [staging]
TRUCK_COURT_MIN = 35.0      # 2 x 16.5 m articulated truck + 1.5 m        [apron]
CLEAR_HEIGHT_MIN = 6.0      # below it, about three pallet levels at most [height]
EGRESS_TRAVEL_M = 76.0      # S-1 sprinklered exit access travel, 250 ft  [egress]
EGRESS_TRAVEL_ONE_STOREY_M = 122.0  # 400 ft: one storey, >= 7.3 m high, sprinklered
SPRINKLER_CLEARANCE = 0.46  # 18 in below deflectors; ESFR needs 36 in    [sprinkler]
PALLET_AISLE_MIN = 2.4      # reach truck lower bound, 96 in              [aisle]

SOURCES = {
    'dock': 'Blue Giant / Rite-Hite dock planning guides: 9-10 ft doors, 12-14 ft centres',
    'staging': 'Rite-Hite dock design: 53-57 ft to floor-drop a trailer load; 60 ft speed bays',
    'apron': 'American Trucking Associations rule via Rite-Hite: approach = 2 x longest truck + 5-15 ft',
    'height': 'Industrial market practice: 28-40 ft (8.5-12.2 m) clear heights',
    'egress': 'IBC 2015/2018 Table 1017.2 and 1017.2.2 (SBC 201 is derived from the IBC)',
    'sprinkler': 'NFPA 13: 18 in (0.46 m) clearance to storage; 36 in (0.91 m) for ESFR',
    'aisle': 'OSHA powered industrial trucks eTool; Toyota aisle-width guide',
}

DOCK_ROLES = frozenset({'receiving', 'shipping', 'crossdock', 'dock', 'dispatch',
                        'inbound', 'outbound', 'loading'})
_INBOUND = frozenset({'receiving', 'inbound'})
_OUTBOUND = frozenset({'shipping', 'dispatch', 'outbound'})
_INDUSTRIAL = frozenset({'warehouse', 'industrial', 'factory', 'logistics', 'مستودع'})
EDGES = ('N', 'E', 'S', 'W')
SIDE_AR = {'N': 'الشمالية', 'S': 'الجنوبية', 'E': 'الشرقية', 'W': 'الغربية'}
PROBE = 0.05                # metres outside an edge to look for a neighbouring room
MIN_RUN = 0.5               # shorter exterior stretches are wall corners, not frontage
MAX_ADVISORIES = 16
_EGRESS_MAX_ROOMS = 200
_EGRESS_MAX_SAMPLES = 2500


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def _rect(room):
    rect = room.get('rect') if isinstance(room, dict) else None
    if (isinstance(rect, list) and len(rect) == 4 and all(_num(v) for v in rect)
            and rect[2] > 0 and rect[3] > 0):
        return [float(v) for v in rect]
    return None


def _fmt(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def is_warehouse(model):
    meta = model.get('meta') if isinstance(model, dict) else None
    raw = str((meta or {}).get('type') or (meta or {}).get('building_type') or '').strip().lower()
    return raw in _INDUSTRIAL


def _role(room):
    return str(room.get('role') or '').strip().lower()


def ground_template(model):
    """Template of the lowest occupied level, or None."""
    levels = [lv for lv in model.get('levels') or []
              if isinstance(lv, dict) and lv.get('kind') != 'roof' and type(lv.get('index')) is int
              and isinstance(lv.get('template'), str) and lv['template'] in (model.get('floors') or {})]
    return min(levels, key=lambda lv: lv['index'])['template'] if levels else None


def _rooms(model, template):
    floor = (model.get('floors') or {}).get(template)
    rooms = floor.get('rooms') if isinstance(floor, dict) else None
    return [r for r in rooms if _rect(r)] if isinstance(rooms, list) else []


def exterior_runs(room, others, edge):
    """Stretches of one edge with no neighbouring room just outside it.

    Returned as (lo, hi) offsets from the edge's low end (x for N/S, z for E/W),
    the same measure a dock or door ``offset`` uses.
    """
    x, z, w, d = _rect(room)
    if edge in ('N', 'S'):
        probe, span, lo0 = (z - PROBE if edge == 'N' else z + d + PROBE), w, x
    else:
        probe, span, lo0 = (x - PROBE if edge == 'W' else x + w + PROBE), d, z
    covered = []
    for other in others:
        if other is room:
            continue
        o = _rect(other)
        if o is None:
            continue
        ox, oz, ow, od = o
        if edge in ('N', 'S'):
            if oz < probe < oz + od:
                covered.append((ox - lo0, ox + ow - lo0))
        elif ox < probe < ox + ow:
            covered.append((oz - lo0, oz + od - lo0))
    runs, cursor = [], 0.0
    for a, b in sorted(covered):
        if a > cursor:
            runs.append((cursor, min(a, span)))
        cursor = max(cursor, b)
        if cursor >= span:
            break
    if cursor < span:
        runs.append((cursor, span))
    return [(round(a, 6), round(b, 6)) for a, b in runs if b - a >= MIN_RUN]


def _longest_run(room, others, edge):
    runs = exterior_runs(room, others, edge)
    return max(runs, key=lambda r: (r[1] - r[0], -r[0])) if runs else None


def court_depth(room, edge, site):
    """Open site depth outward from one edge of a room to the plot boundary."""
    x, z, w, d = _rect(room)
    return {'N': z, 'S': site['d'] - (z + d), 'W': x, 'E': site['w'] - (x + w)}[edge]


def _site(model):
    site = model.get('site')
    if isinstance(site, dict) and _num(site.get('w')) and _num(site.get('d')) and site['w'] > 0 and site['d'] > 0:
        return {'w': float(site['w']), 'd': float(site['d'])}
    return None


def _confirmed(requirements, metric):
    values = [r.get('expected') for r in requirements or []
              if isinstance(r, dict) and r.get('metric') == metric and r.get('edge') is None and r.get('role') is None]
    return values[0] if len(values) == 1 and _num(values[0]) else None


def site_is_building(requirements):
    """A confirmed building width/depth makes the model's site the building itself."""
    return any(isinstance(r, dict) and r.get('metric') in ('building_width_m', 'building_depth_m')
               for r in requirements or [])


def dock_target(requirements):
    """(count, exact): the confirmed dock total, or (None, False) when unstated.

    Edge-scoped dock rows stay with the planner: totals are not rebalanced then.
    """
    if any(isinstance(r, dict) and r.get('metric') in ('dock_count', 'min_dock_count') and r.get('edge') is not None
           for r in requirements or []):
        return None, False
    exact, minimum = _confirmed(requirements, 'dock_count'), _confirmed(requirements, 'min_dock_count')
    if type(exact) is int and exact >= 0:
        return exact, True
    if type(minimum) is int and minimum > 0:
        return minimum, False
    return None, False


# --------------------------------------------------------------- docks ----
def stash_dock_intents(building):
    """Take the planner's ``docks: [{edge, count}]`` intents off the rooms.

    Room geometry is fitted and repaired position-only before docks exist; the
    intents come back as exact dock groups in ``layout_docks``.
    """
    out = copy.deepcopy(building)
    intents = []
    for template, floor in (out.get('floors') or {}).items():
        for room in floor.get('rooms') or [] if isinstance(floor, dict) else []:
            if not isinstance(room, dict) or 'docks' not in room:
                continue
            for item in room.pop('docks') or []:
                if (isinstance(item, dict) and item.get('edge') in EDGES and type(item.get('count')) is int
                        and 1 <= item['count'] <= MAX_DOCKS_PER_GROUP and isinstance(room.get('id'), str)):
                    intents.append({'template': template, 'room': room['id'], 'edge': item['edge'],
                                    'count': item['count']})
    return out, intents


def _capacity(length):
    return int(math.floor(length / DOCK_PITCH_MIN + 1e-9))


def _group(run, n):
    """Pitch and first-door offset for n doors centred in one exterior run."""
    length = run[1] - run[0]
    pitch = DOCK_PITCH if n * DOCK_PITCH <= length + 1e-9 else math.floor(length / n * 100) / 100
    first = run[0] + (length - n * pitch) / 2 + pitch / 2
    return round(pitch, 2), round(first, 3)


def _best_edge(room, others, site):
    """The room's longest exterior edge; ties go to the deeper truck court."""
    best = None
    for edge in EDGES:
        run = _longest_run(room, others, edge)
        if run is None:
            continue
        key = (round(run[1] - run[0], 3), round(court_depth(room, edge, site), 3) if site else 0.0)
        if best is None or key > best[0]:
            best = (key, edge, run)
    return (best[1], best[2]) if best else (None, None)


def _allocate(total, slots):
    """Split ``total`` doors over slots [(key, capacity, group)] deterministically.

    Inbound and outbound zones share the doors half and half; inside a group the
    split follows frontage capacity. Capacity is never exceeded.
    """
    groups = {}
    for key, cap, group in slots:
        groups.setdefault(group, []).append((key, cap))
    order = sorted(groups)
    share, left = {}, total
    for i, group in enumerate(order):
        want = left if i == len(order) - 1 else int(math.ceil(left / (len(order) - i)))
        caps = sum(c for _, c in groups[group])
        share[group] = min(want, caps)
        left -= share[group]
    out = {}
    for group in order:
        n, members = share[group], groups[group]
        caps = sum(c for _, c in members) or 1
        assigned = {k: min(c, int(math.floor(n * c / caps))) for k, c in members}
        rest = n - sum(assigned.values())
        for k, c in sorted(members, key=lambda m: (-m[1], m[0])):
            take = min(rest, c - assigned[k])
            assigned[k] += take
            rest -= take
        out.update(assigned)
    # Anything a full group could not hold goes to any slot with room left.
    rest = total - sum(out.values())
    for key, cap, _ in slots:
        take = min(rest, cap - out[key])
        out[key] += take
        rest -= take
    return out


def layout_docks(building, requirements, intents):
    """Place dock groups on dock zones' exterior walls (deterministic, free).

    Returns (building, notes). The planner's per-zone intents decide which wall
    and how many doors; a confirmed dock total is then met exactly (or reached
    for a minimum) on the frontage the zones offer. Doors that do not fit are
    reported, never squeezed below 12 ft centres.
    """
    out = copy.deepcopy(building)
    template = ground_template(out)
    site = _site(out)
    if template is None or site is None:
        return out, []
    target, exact = dock_target(requirements)
    if sum(1 for lv in out.get('levels') or [] if isinstance(lv, dict) and lv.get('template') == template
           and lv.get('kind') != 'roof') != 1:
        # Docks on a template shared by several storeys would repeat on every one.
        return out, (['تنبيه: الدور الأرضي يشارك قالبه أدوارًا أخرى، فلم تُرتَّب أبواب الأرصفة تلقائيًا؛ '
                      'أضفها للدور الأرضي وحده.'] if intents or target else [])
    rooms = _rooms(out, template)
    by_id = {r.get('id'): r for r in rooms if isinstance(r.get('id'), str)}
    wanted = {}
    for item in intents:
        room = by_id.get(item['room']) if item['template'] == template else None
        if room is None:
            continue
        edge = item['edge'] if _longest_run(room, rooms, item['edge']) else _best_edge(room, rooms, site)[0]
        if edge is not None:
            wanted[(room['id'], edge)] = wanted.get((room['id'], edge), 0) + item['count']
    named = list(by_id.values())
    zones = [r for r in named if _role(r) in DOCK_ROLES] or [r for r in named if _role(r) == 'staging']
    slots = []
    for room in zones:
        edges = [e for (rid, e) in wanted if rid == room['id']] or [_best_edge(room, rooms, site)[0]]
        for edge in edges:
            run = _longest_run(room, rooms, edge) if edge else None
            if run:
                group = 0 if _role(room) in _INBOUND else 1 if _role(room) in _OUTBOUND else 2
                slots.append(((room['id'], edge), min(MAX_DOCKS_PER_GROUP, _capacity(run[1] - run[0])), group))
    for key in wanted:  # a planner intent on a non-dock zone keeps its own slot
        if key not in {s[0] for s in slots}:
            run = _longest_run(by_id[key[0]], rooms, key[1])
            slots.append((key, min(MAX_DOCKS_PER_GROUP, _capacity(run[1] - run[0])), 2))
    caps = {k: c for k, c, _ in slots}
    counts = {k: min(n, caps.get(k, 0)) for k, n in wanted.items()}
    planned = sum(wanted.values())
    if target is not None and (planned != target if exact else planned < target):
        if not wanted:
            counts = _allocate(target, slots)
        elif planned < target:
            rest = target - sum(counts.values())
            for key, cap, _ in sorted(slots, key=lambda s: (s[0] not in wanted, s[2], s[0])):
                take = min(rest, cap - counts.get(key, 0))
                if take > 0:
                    counts[key] = counts.get(key, 0) + take
                    rest -= take
        else:
            extra = sum(counts.values()) - target
            for key in sorted(counts, key=lambda k: (-counts[k], k)):
                take = min(extra, counts[key])
                counts[key] -= take
                extra -= take
    placed, notes = 0, []
    wall_h = out.get('wall_h')
    for (rid, edge), n in sorted(counts.items(), key=lambda kv: (list(by_id).index(kv[0][0]), EDGES.index(kv[0][1]))):
        if n <= 0:
            continue
        room = by_id[rid]
        existing = room.setdefault('docks', [])
        if not isinstance(existing, list) or any(isinstance(d, dict) and d.get('edge') == edge for d in existing):
            continue  # authored dock data on this wall is never replaced
        run = _longest_run(room, rooms, edge)
        pitch, first = _group(run, n)
        height = DOCK_DOOR_H
        own_h = room.get('wall_h') if _num(room.get('wall_h')) else wall_h
        if _num(own_h) and own_h > 0:
            height = min(DOCK_DOOR_H, round(own_h * 0.9, 2))
        existing.append({
            'id': 'dock-' + edge.lower(), 'edge': edge, 'offset': first, 'width': DOCK_DOOR_W,
            'height': height, 'count': n, 'pitch': pitch})
        placed += n
        name = room.get('name') or rid
        notes.append('افتراض: أبواب أرصفة «%s» على الواجهة %s عددها %d، مقاس الباب %s × %s م وتباعد المراكز %s م '
                     '(الشائع 2.7–3.0 م عرضًا و3.7–4.3 م بين المراكز)؛ قيم تخطيطية قابلة للتعديل.'
                     % (name, SIDE_AR[edge], n, _fmt(DOCK_DOOR_W), _fmt(height), _fmt(pitch)))
    if target is not None and (placed != target if exact else placed < target):
        notes.append('تنبيه: عدد الأرصفة المؤكد %d، ووضع النظام منها %d على الواجهات الخارجية لمناطق الأرصفة '
                     'بتباعد مراكز 3.66 م على الأقل. وسّع واجهة الأرصفة أو عدّل العدد.' % (target, placed))
    if placed or notes:
        out.setdefault('meta', {}).setdefault('acs_stage_diagnostics', []).append(
            {'code': 'WAREHOUSE_DOCKS_LAID_OUT', 'placed': placed, 'requested': target,
             'planner_intents': planned, 'source': 'system_default'})
    return out, notes


def place_for_truck_court(building, requirements):
    """Shift every room (all levels, one offset) so dock walls keep a truck court.

    Only when the site is the plot (no confirmed building size), only along an
    axis whose dock walls lack the court, and only when one shift satisfies every
    dock wall on that axis while all rooms stay inside the site. Sizes never change.
    """
    out = copy.deepcopy(building)
    template, site = ground_template(out), _site(out)
    if template is None or site is None or site_is_building(requirements):
        return out, []
    rooms = _rooms(out, template)
    faces = [(room, d['edge']) for room in rooms for d in room.get('docks') or []
             if isinstance(d, dict) and d.get('edge') in EDGES]
    every = [r for t in (out.get('floors') or {}) for r in _rooms(out, t)]
    if not faces or not every:
        return out, []
    shift, notes = [0.0, 0.0], []
    for axis, (lo_edge, hi_edge, size) in enumerate((('W', 'E', site['w']), ('N', 'S', site['d']))):
        lo_faces = [_rect(r)[axis] for r, e in faces if e == lo_edge]
        hi_faces = [_rect(r)[axis] + _rect(r)[axis + 2] for r, e in faces if e == hi_edge]
        if not lo_faces and not hi_faces:
            continue
        low = -min(_rect(r)[axis] for r in every)
        high = size - max(_rect(r)[axis] + _rect(r)[axis + 2] for r in every)
        if lo_faces:
            low = max(low, TRUCK_COURT_MIN - min(lo_faces))
        if hi_faces:
            high = min(high, size - TRUCK_COURT_MIN - max(hi_faces))
        if low > high + 1e-9 or (low <= 1e-9 and high >= -1e-9):
            continue  # infeasible (reported by the review) or already satisfied
        shift[axis] = round(min(max(0.0, low), high), 3)
    if shift == [0.0, 0.0]:
        return out, []
    for floor in (out.get('floors') or {}).values():
        for room in floor.get('rooms') or []:
            if _rect(room):
                room['rect'][0] = round(room['rect'][0] + shift[0], 4)
                room['rect'][1] = round(room['rect'][1] + shift[1], 4)
    moves = []
    if shift[0]:
        moves.append('%s م %s' % (_fmt(abs(shift[0])), 'شرقًا' if shift[0] > 0 else 'غربًا'))
    if shift[1]:
        moves.append('%s م %s' % (_fmt(abs(shift[1])), 'جنوبًا' if shift[1] > 0 else 'شمالًا'))
    notes.append('نُقل المبنى بكل أدواره %s دون تغيير أبعاد الفراغات، لتبقى أمام كل واجهة أرصفة ساحة شاحنات '
                 'بعمق %s م على الأقل داخل الأرض (ضعف طول شاحنة مفصلية 16.5 م).'
                 % (' و'.join(moves), _fmt(TRUCK_COURT_MIN)))
    out.setdefault('meta', {}).setdefault('acs_stage_diagnostics', []).append(
        {'code': 'WAREHOUSE_TRUCK_COURT_PLACEMENT', 'shift_m': shift, 'court_min_m': TRUCK_COURT_MIN})
    return out, notes


def disclose(building, notes):
    """Append Arabic planning notes to meta.assumptions (the review's assumptions card)."""
    if not notes:
        return building
    meta = building.setdefault('meta', {})
    if not isinstance(meta.get('assumptions'), list):
        meta['assumptions'] = []
    for text in notes:
        if text not in meta['assumptions']:
            meta['assumptions'].append(text)
    return building


# --------------------------------------------------------------- review ----
def _segments(rooms):
    """Exterior wall segments of one floor as ((x1, z1), (x2, z2))."""
    segs = []
    for room in rooms:
        x, z, w, d = _rect(room)
        for edge in EDGES:
            for a, b in exterior_runs(room, rooms, edge):
                if edge == 'N':
                    segs.append(((x + a, z), (x + b, z)))
                elif edge == 'S':
                    segs.append(((x + a, z + d), (x + b, z + d)))
                elif edge == 'W':
                    segs.append(((x, z + a), (x, z + b)))
                else:
                    segs.append(((x + w, z + a), (x + w, z + b)))
    return segs


def _point_segment(px, pz, seg):
    (ax, az), (bx, bz) = seg
    dx, dz = bx - ax, bz - az
    length = dx * dx + dz * dz
    t = 0.0 if length <= 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / length))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def farthest_from_exterior(rooms):
    """Largest sampled straight-line distance from a floor point to an exterior wall.

    Exit travel is never shorter than this, so it is a lower bound of the travel
    distance any perimeter exit can give. None when the floor is too large to sample.
    """
    if not rooms or len(rooms) > _EGRESS_MAX_ROOMS:
        return None
    segs = _segments(rooms)
    if not segs:
        return None
    area = sum(_rect(r)[2] * _rect(r)[3] for r in rooms)
    step = max(1.0, math.sqrt(area / _EGRESS_MAX_SAMPLES))
    best = 0.0
    for room in rooms:
        x, z, w, d = _rect(room)
        nx, nz = max(1, int(w / step)), max(1, int(d / step))
        for i in range(nx):
            for j in range(nz):
                px, pz = x + (i + 0.5) * w / nx, z + (j + 0.5) * d / nz
                best = max(best, min(_point_segment(px, pz, s) for s in segs))
    return best


def _note(code, message, source, room_ref=None):
    item = {'code': code, 'severity': 'advisory', 'message': message + ' المرجع: ' + SOURCES[source] + '.',
            'source': source}
    if room_ref is not None:
        item['room_ref'] = room_ref
    return item


def check(model, requirements=None):
    """Cited, non-blocking warehouse planning notes for one revision.

    Measures only canonical geometry: dock frontage and spacing, staging depth,
    truck court, clear height, a lower bound of egress travel, rack aisles and
    sprinkler clearance. It never claims compliance and never blocks approval.
    """
    if not isinstance(model, dict) or not is_warehouse(model):
        return []
    template, site = ground_template(model), _site(model)
    if template is None or site is None:
        return []
    rooms = _rooms(model, template)
    notes = []
    plot = not site_is_building(requirements)
    frontage = 0
    for room in rooms:
        rid = room.get('id')
        ref = [template, rid]
        name = room.get('name') or rid
        docks = [d for d in room.get('docks') or [] if isinstance(d, dict) and d.get('edge') in EDGES]
        if not docks:
            if _role(room) in DOCK_ROLES:
                best, run = _best_edge(room, rooms, site)
                frontage += _capacity(run[1] - run[0]) if run else 0
                if best is None:
                    notes.append(_note('WAREHOUSE_DOCK_ZONE_INTERIOR',
                                       '«%s» منطقة أرصفة بلا أي ضلع على واجهة خارجية؛ أبواب الأرصفة تحتاج جدارًا خارجيًا.'
                                       % name, 'dock', ref))
            continue
        for edge in sorted({d['edge'] for d in docks}):
            run = _longest_run(room, rooms, edge)
            frontage += _capacity(run[1] - run[0]) if run else 0
            if run is None:
                notes.append(_note('WAREHOUSE_DOCK_ON_INTERIOR_WALL',
                                   'أرصفة «%s» على الواجهة %s، وهي جدار يلاصق فراغًا آخر لا واجهة خارجية.'
                                   % (name, SIDE_AR[edge]), 'dock', ref))
                continue
            depth = _rect(room)[3] if edge in ('N', 'S') else _rect(room)[2]
            if depth + 1e-6 < STAGING_DEPTH_MIN:
                notes.append(_note('WAREHOUSE_STAGING_SHALLOW',
                                   'عمق «%s» خلف الواجهة %s هو %s م، أقل من %s م اللازمة لتفريغ حمولة شاحنة كاملة على الأرض.'
                                   % (name, SIDE_AR[edge], _fmt(depth), _fmt(STAGING_DEPTH_MIN)), 'staging', ref))
            court = court_depth(room, edge, site)
            if plot and court + 1e-6 < TRUCK_COURT_MIN:
                notes.append(_note('WAREHOUSE_TRUCK_COURT_SHALLOW',
                                   'ساحة الشاحنات أمام الواجهة %s لـ«%s» بعمق %s م داخل الأرض، أقل من %s م (ضعف طول شاحنة مفصلية 16.5 م).'
                                   % (SIDE_AR[edge], name, _fmt(max(0.0, court)), _fmt(TRUCK_COURT_MIN)), 'apron', ref))
        for d in docks:
            if type(d.get('count')) is int and d['count'] > 1 and _num(d.get('pitch')) and d['pitch'] + 1e-6 < DOCK_PITCH_MIN:
                notes.append(_note('WAREHOUSE_DOCK_SPACING_TIGHT',
                                   'تباعد مراكز أبواب أرصفة «%s» %s م، أقل من 3.66 م (12 قدمًا) التي تسع شاحنة بمراياها.'
                                   % (name, _fmt(d['pitch'])), 'dock', ref))
    target, _ = dock_target(requirements)
    if target and frontage < target:
        notes.append(_note('WAREHOUSE_DOCK_FRONTAGE_SHORT',
                           'الواجهات الخارجية لمناطق الأرصفة تسع %d بابًا بتباعد 3.66 م، والعدد المؤكد %d.' % (frontage, target),
                           'dock'))
    wall_h = model.get('wall_h')
    if _num(wall_h) and 0 < wall_h < CLEAR_HEIGHT_MIN:
        notes.append(_note('WAREHOUSE_CLEAR_HEIGHT_LOW',
                           'ارتفاع الجدار %s م أقل من %s م؛ يتسع لنحو ثلاثة مستويات بالتات على الأكثر. أكّد الارتفاع الصافي المطلوب.'
                           % (_fmt(wall_h), _fmt(CLEAR_HEIGHT_MIN)), 'height'))
    far = farthest_from_exterior(rooms)
    if far is not None and far > EGRESS_TRAVEL_M:
        notes.append(_note('WAREHOUSE_EGRESS_DISTANCE',
                           'أبعد نقطة في الدور الأرضي تبعد %s م في خط مستقيم عن أقرب جدار خارجي، فمسار الهروب إلى مخرج على المحيط أطول من %s م '
                           '(حد S-1 المرشوش)؛ وحد %s م مشروط بدور واحد وارتفاع ≥ 7.3 م ورشاشات كاملة. عند تطبيق الحد يلزم مخرج داخلي محمي أو تقسيم الكتلة.'
                           % (_fmt(far), _fmt(EGRESS_TRAVEL_M), _fmt(EGRESS_TRAVEL_ONE_STOREY_M)), 'egress'))
    for t in (model.get('floors') or {}):
        for room in _rooms(model, t):
            own_h = room.get('wall_h') if _num(room.get('wall_h')) else wall_h
            for rack in room.get('racks') or []:
                if not isinstance(rack, dict):
                    continue
                name = room.get('name') or room.get('id')
                aisle = rack.get('aisle')
                if str(rack.get('kind') or 'pallet') == 'pallet' and _num(aisle) and 0 < aisle < PALLET_AISLE_MIN:
                    notes.append(_note('WAREHOUSE_RACK_AISLE_NARROW',
                                       'ممر رفوف البالتات في «%s» بعرض %s م، أضيق من أقل ممر لرافعة ريتش (2.4 م)؛ يحتاج رافعات VNA موجّهة.'
                                       % (name, _fmt(aisle)), 'aisle', [t, room.get('id')]))
                if _num(rack.get('h')) and _num(own_h) and rack['h'] > own_h - SPRINKLER_CLEARANCE + 1e-6:
                    notes.append(_note('WAREHOUSE_RACK_SPRINKLER_CLEARANCE',
                                       'قمة رفوف «%s» (%s م) تترك أقل من 0.46 م تحت سقف ارتفاعه %s م؛ رشاشات ESFR تحتاج 0.91 م.'
                                       % (name, _fmt(rack['h']), _fmt(own_h)), 'sprinkler', [t, room.get('id')]))
    return notes[:MAX_ADVISORIES]
