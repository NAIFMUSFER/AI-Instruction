"""Livability of one villa or house: the confirmed villa program and its checks.

Step 01 of the signed-in form sends a villa's program as confirmed requirement
rows whose ``source_id`` is VILLA_PROGRAM_SOURCE (residential-options.mjs):
``room_count`` for bedroom, bathroom, maid_room and driver_room, and
``ensuite_bedroom_count`` for the master suite. acs_plan_review._program
measures those counts like any confirmed count. This module checks what a count
cannot see: one room drawn for several rooms («غرف النوم»), a bedroom of an
implausible size, a storey with bedrooms and no bathroom, the guest WC, the
majlis beside the entrance and the kitchen on an exterior wall.

Severity follows the evidence. A failure that is unambiguous in any dwelling
blocks every revision, old ones included: an aggregate room, a house without
any bathroom, a bedroom of BEDROOM_UNAMBIGUOUS_M2 or more. A check that rests on
the owner's program blocks only when the revision carries the confirmed villa
program, or when the brief asked for that feature; otherwise it is advisory.
Every threshold below is a stated planning assumption, not a regulation, and
nothing here claims code compliance.
"""
from collections import Counter
import re

import acs_plot_rules as P
from acs_residential_access import OPPOSITE, edge, enclosed, shared

VILLA_PROGRAM_SOURCE = 'brief:villa-program'
BEDROOM_MAX_M2 = 30.0          # assumption: one bedroom; its bath and closet are separate rooms
BEDROOM_UNAMBIGUOUS_M2 = 45.0  # no single bedroom is this large: several rooms drawn as one
WINDOW_RUN_M = 0.9             # assumption: exterior wall run long enough for a window
EPS = 1e-4
BATH_ROLES = {'bathroom', 'wc', 'toilet', 'guest_wc', 'ensuite', 'en_suite', 'powder_room', 'restroom', 'bath'}
BED_ROLES = {'bedroom', 'master_bedroom'}
PROGRAM_ROLES = ('bedroom', 'bathroom', 'maid_room', 'driver_room')  # the villa form's room_count roles
OUTDOOR_ROLES = {'courtyard', 'porch', 'terrace', 'balcony', 'garden', 'yard', 'patio', 'parking', 'roof_deck'}

_TASHKEEL = re.compile('[ـً-ْ]')
# Plural room nouns at the head of a name: «غرف النوم»، «الحمامات»، «دورات المياه».
_PLURAL_HEADS = {'غرف', 'حمامات', 'دورات', 'مجالس', 'صالات', 'مطابخ'}
# «منطقة النوم»، «جناح غرف النوم»: a zone of rooms, not a room.
_ZONE_HEADS = {'منطقه', 'جناح', 'قسم'}
_ZONE_OF = {'نوم', 'غرف'}
_EN_AGGREGATE = re.compile(r'\b(?:bedrooms|bathrooms|toilets|wcs|rooms|(?:sleeping|bedroom)\s+(?:area|zone|wing))\b')
_AGGREGATE_ROLES = {'bedrooms', 'bathrooms', 'rooms', 'toilets', 'wcs', 'kitchens', 'majlises', 'living_rooms',
                    'sleeping_area', 'sleeping_zone', 'bedroom_area', 'bedroom_zone', 'bedroom_wing'}
_GUEST_WC = re.compile(r'(?:دوره\s+(?:ال)?مياه|حمام|wc|toilet)\s+(?:لل|ال)?ضيوف|guest\s+(?:wc|toilet|bath)')
_KITCHEN_OUT = re.compile(r'مطبخ[^.\n،]{0,30}?(?:جدار\s+خارجي|واجه|نافذ|شباك|تهوي|يطل)')


def _norm(text):
    text = _TASHKEEL.sub('', text).replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return text.replace('ة', 'ه').replace('ى', 'ي').lower()


def _words(text):
    return [w[2:] if w.startswith('ال') and len(w) > 3 else w for w in re.findall(r'\w+', _norm(text))]


def role(room):
    """Canonical role: explicit Arabic aliases mapped, otherwise the role as written."""
    from acs_residential_generation import _canonical_role
    value = room.get('role')
    return _canonical_role(value) or (value.strip().lower() if isinstance(value, str) else '')


def aggregate(room):
    """One room drawn and named for several rooms (plural or zone name or role)."""
    value = room.get('role')
    if isinstance(value, str) and value.strip().lower() in _AGGREGATE_ROLES:
        return True
    for text in (room.get('name'), value):
        if not isinstance(text, str) or not text.strip():
            continue
        words = _words(text)
        if words and (words[0] in _PLURAL_HEADS
                      or (words[0] in _ZONE_HEADS and len(words) > 1 and words[1] in _ZONE_OF)):
            return True
        if _EN_AGGREGATE.search(_norm(text)):
            return True
    return False


def confirmed_program(requirements):
    """The villa program the owner confirmed, or None.

    {'bedroom', 'bathroom', 'maid_room', 'driver_room', 'ensuite'}: counts, 0 when
    not asked. The program is present when whole-building bedroom and bathroom
    counts are both confirmed, as the step-01 villa fields always send them
    (rows with source_id VILLA_PROGRAM_SOURCE) or as an owner typed them."""
    out = {'bedroom': None, 'bathroom': None, 'maid_room': 0, 'driver_room': 0, 'ensuite': 0}
    for r in requirements or []:
        if not isinstance(r, dict) or r.get('confirmed') is not True or type(r.get('expected')) is not int:
            continue
        if r.get('metric') == 'room_count' and r.get('role') in PROGRAM_ROLES and r.get('template') is None:
            out[r['role']] = r['expected']
        elif r.get('metric') == 'ensuite_bedroom_count':
            out['ensuite'] = r['expected']
    return out if out['bedroom'] is not None and out['bathroom'] is not None else None


def guest_wc_requested(brief):
    return isinstance(brief, str) and bool(_GUEST_WC.search(_norm(brief)))


def kitchen_exterior_requested(brief):
    return isinstance(brief, str) and bool(_KITCHEN_OUT.search(_norm(brief)))


# ── geometry ─────────────────────────────────────────────────────────────────
def _storeys(building):
    """Occupied storeys: (ordered unique templates, first level index of each)."""
    first = {}
    for level in P._occupied(building):
        first.setdefault(level['template'], level['index'] if type(level.get('index')) is int else 0)
    return list(first), first


def _floor_name(index):
    names = {0: 'الدور الأرضي', 1: 'الدور الأول', 2: 'الدور الثاني', 3: 'الدور الثالث'}
    return names.get(index, 'الدور ' + str(index))


def _area(room):
    return room['rect'][2] * room['rect'][3]


def _doors(room):
    return [d for d in room.get('doors') or [] if isinstance(d, dict) and d.get('edge') in OPPOSITE]


def private_bedroom(bath, rooms):
    """The bedroom an en-suite bathroom opens into, and nothing else; or None."""
    doors = _doors(bath)
    if not doors:
        return None
    across = set()
    for door in doors:
        other, _ = P._across(rooms, bath, door)
        if other is None:
            return None
        across.add(id(other))
    if len(across) != 1:
        return None
    bed = next(r for r in rooms if id(r) in across)
    return bed if role(bed) in BED_ROLES and shared(bath, bed, True) else None


def ensuite_bedroom_count(model):
    """Bedrooms with a private bathroom, over every occupied storey instance.

    None when the model has no door data yet (a layout before openings)."""
    levels = P._occupied(model)
    instances = Counter(level['template'] for level in levels)
    rooms = {t: P._rooms(model, t) for t in instances}
    if not any(_doors(r) for floor in rooms.values() for r in floor):
        return None
    total = 0
    for template, floor in rooms.items():
        beds = {id(b) for b in (private_bedroom(r, floor) for r in floor if role(r) in BATH_ROLES) if b is not None}
        total += len(beds) * instances[template]
    return total


def _exterior_run(room, rooms):
    """Longest run of the room's perimeter not shared with an enclosed indoor room."""
    best = 0.0
    for side, other_side in OPPOSITE.items():
        line, lo, hi = edge(room, side)
        covered = []
        for other in rooms:
            if other is room or not enclosed(other) or role(other) in OUTDOOR_ROLES:
                continue
            line2, lo2, hi2 = edge(other, other_side)
            if abs(line - line2) <= EPS and min(hi, hi2) - max(lo, lo2) > EPS:
                covered.append((max(lo, lo2), min(hi, hi2)))
        cursor = lo
        for a, b in sorted(covered):
            best = max(best, a - cursor)
            cursor = max(cursor, b)
        best = max(best, hi - cursor)
    return best


def _bath_adjacent(bed, rooms):
    return any(role(r) in BATH_ROLES and shared(bed, r, False) for r in rooms if r is not bed)


def _finding(code, severity, message, template=None, room=None):
    out = {'code': code, 'severity': severity, 'message': message}
    if template is not None and room is not None:
        out['room_ref'] = [template, room.get('id')]
    return out


def _label(template, room):
    name = room.get('name') if isinstance(room.get('name'), str) and room['name'].strip() else room.get('id')
    return '[' + template + '/' + str(room.get('id')) + '] «' + str(name).strip()[:60] + '» '


def _fmt(value):
    return P._fmt(value)


# ── review ───────────────────────────────────────────────────────────────────
def check(building, brief, requirements, plot=None):
    """(blocking, advisory) livability findings for one villa or house.

    The caller has established a single dwelling and valid geometry. ``plot``
    is the revision's plot-rules block: its own zoning check already reports a
    majlis far from the entrance, so that check runs here only without it."""
    program = confirmed_program(requirements)
    blocking, advisory = [], []
    def add(hard, item):
        item['severity'] = 'error' if hard else 'advisory'
        (blocking if hard else advisory).append(item)
    templates, first = _storeys(building)
    if not templates:
        return blocking, advisory
    rooms = {t: P._rooms(building, t) for t in templates}
    ground = templates[0]
    merged = set()
    for t in templates:
        for room in rooms[t]:
            if aggregate(room):
                merged.add(id(room))
                add(True, _finding('VILLA_AGGREGATE_ROOM', 'error', _label(t, room) + 'فراغ واحد مساحته '
                    + _fmt(_area(room)) + ' م² باسم أو استخدام يجمع عدة غرف. ارسم كل غرفة نوم وكل حمام فراغًا '
                    'مستقلًا باسم مفرد (غرفة نوم ١، غرفة نوم ٢، حمام…) بأبعاده وبابه. (' + _floor_name(first[t]) + ')', t, room))
    for t in templates:
        for room in rooms[t]:
            area = _area(room)
            if id(room) in merged or role(room) not in BED_ROLES or area <= BEDROOM_MAX_M2 + EPS:
                continue
            hard = program is not None or area >= BEDROOM_UNAMBIGUOUS_M2 - EPS
            add(hard, _finding('VILLA_BEDROOM_OVERSIZED', '', _label(t, room) + 'غرفة نوم مساحتها ' + _fmt(area)
                + ' م²، أكبر من ' + _fmt(BEDROOM_MAX_M2) + ' م² المفترضة لغرفة نوم واحدة. قسّمها إلى غرف أو صغّرها، '
                'واجعل الحمام الخاص وغرفة الملابس فراغين منفصلين. (' + _floor_name(first[t]) + ')', t, room))
    baths = {t: [r for r in rooms[t] if role(r) in BATH_ROLES] for t in templates}
    beds = {t: [r for r in rooms[t] if role(r) in BED_ROLES] for t in templates}
    if not any(baths.values()):
        floors = [_floor_name(first[t]) for t in templates if beds[t]]
        add(True, _finding('VILLA_NO_BATHROOM', 'error', 'لا يوجد في المسكن أي حمام أو دورة مياه'
            + (' (غرف النوم في ' + ' و'.join(floors) + ')' if floors else '') + '. أضف حمامًا في كل دور فيه '
            'غرف نوم، وحمامًا خاصًا لغرفة النوم الرئيسية، ودورة مياه للضيوف في الدور الأرضي قرب المجلس.'))
    else:
        for t in templates:
            if beds[t] and not baths[t]:
                add(program is not None, _finding('VILLA_FLOOR_WITHOUT_BATHROOM', '', _label(t, beds[t][0])
                    + _floor_name(first[t]) + ' فيه ' + str(len(beds[t])) + ' من غرف النوم بلا أي حمام. أضف حمامًا '
                    'مشتركًا في هذا الدور أو حمامًا خاصًا لغرفة النوم الرئيسية.', t, beds[t][0]))
        guest = [b for b in baths[ground] if private_bedroom(b, rooms[ground]) is None]
        if not guest:
            # The confirmed bathroom count includes the guest WC (villa form).
            asked = program is not None or guest_wc_requested(brief)
            add(asked, _finding('VILLA_GUEST_WC_MISSING', '', 'لا توجد دورة مياه للضيوف في الدور الأرضي '
                '(حمام لا يُدخل إليه من غرفة نوم). أضفها قرب المجلس أو بهو المدخل حتى لا يعبر الضيوف منطقة الأسرة.'
                + ('' if asked else ' لم يذكرها الوصف صراحة، فهي ملاحظة لا تمنع الاعتماد.')))
    if plot is None:
        hard = P.zoning_requested(brief)
        found_hard, found_soft = [], []
        P._zoning(building, {'zoning_requested': hard, 'dwelling': P.VILLA}, found_hard, found_soft)
        for item in found_hard + found_soft:
            if item.get('code') == 'PLOT_ZONING_MAJLIS_FAR':
                add(hard, dict(item, code='VILLA_MAJLIS_FAR'))
    asked = kitchen_exterior_requested(brief)
    for t in templates:
        for room in rooms[t]:
            if role(room) == 'kitchen' and _exterior_run(room, rooms[t]) < WINDOW_RUN_M - EPS:
                add(asked, _finding('VILLA_KITCHEN_INTERIOR', '', _label(t, room) + 'المطبخ لا يقع على جدار خارجي، '
                    'فلا نافذة ولا تهوية طبيعية له. انقله إلى واجهة خارجية بجوار غرفة الطعام. ('
                    + _floor_name(first[t]) + ')', t, room))
    return blocking[:128], advisory[:128]


# ── layout repair ────────────────────────────────────────────────────────────
def layout_findings(building, requirements):
    """Structured findings for the layout repair, before any opening exists.

    The unambiguous failures always; with the confirmed villa program also a
    bedroom over BEDROOM_MAX_M2, a bedroom storey without a bathroom, no
    bathroom on the ground storey, an interior kitchen and a master bedroom
    with no bathroom beside it. They inform the repair; the review decides."""
    program = confirmed_program(requirements)
    templates, _ = _storeys(building)
    rooms = {t: P._rooms(building, t) for t in templates}
    out = []
    for t in templates:
        for room in rooms[t]:
            area = round(_area(room), 2)
            if aggregate(room):
                out.append({'code': 'VILLA_AGGREGATE_ROOM', 'room_ref': [t, room.get('id')], 'area_m2': area,
                            'fix': 'split into separate rooms: one bedroom or one bathroom each, singular names'})
            elif role(room) in BED_ROLES and (area >= BEDROOM_UNAMBIGUOUS_M2 - EPS
                                              or (program is not None and area > BEDROOM_MAX_M2 + EPS)):
                out.append({'code': 'VILLA_BEDROOM_OVERSIZED', 'room_ref': [t, room.get('id')], 'area_m2': area,
                            'max_m2': BEDROOM_MAX_M2})
    baths = {t: [r for r in rooms[t] if role(r) in BATH_ROLES] for t in templates}
    beds = {t: [r for r in rooms[t] if role(r) in BED_ROLES] for t in templates}
    if templates and not any(baths.values()):
        out.append({'code': 'VILLA_NO_BATHROOM', 'fix': 'add the confirmed bathrooms (role bathroom)'})
    elif program is not None:
        for t in templates:
            if beds[t] and not baths[t]:
                out.append({'code': 'VILLA_FLOOR_WITHOUT_BATHROOM', 'room_ref': [t, beds[t][0].get('id')]})
        if templates and not baths[templates[0]]:
            out.append({'code': 'VILLA_GUEST_WC_MISSING', 'template': templates[0],
                        'fix': 'guest WC (role bathroom) on the ground storey beside the majlis or the entrance'})
        if program.get('ensuite') and not any(_bath_adjacent(b, rooms[t]) for t in templates for b in beds[t]):
            out.append({'code': 'VILLA_ENSUITE_MISSING',
                        'fix': 'a bathroom sharing a wall with the master bedroom, entered only from it'})
    if program is not None:
        for t in templates:
            for room in rooms[t]:
                if role(room) == 'kitchen' and _exterior_run(room, rooms[t]) < WINDOW_RUN_M - EPS:
                    out.append({'code': 'VILLA_KITCHEN_INTERIOR', 'room_ref': [t, room.get('id')],
                                'fix': 'move the kitchen onto an exterior wall'})
    return out[:64]
