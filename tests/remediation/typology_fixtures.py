"""Hand-made compliant layouts for the typology packs (tests/remediation/test_typology_packs.py).

Built in Python on purpose: test_validate_against_real_models.py scans every
tests/**/*.json for building models, and the seeded violations derived from
these fixtures must never join that corpus. Each builder returns a fresh
canonical Building JSON (rect = [x, z, w, d], x east, z south, z=0 north)
with matching doors on both sides of every passage, exterior doors, windows on
exterior walls only and a light point per room, so acs_validate reports no
issue on it either.
"""
import copy

import acs_typology_common as C

DOOR_H = 2.1
WALL_H = 3.4


def room(rid, name, role, rect, **extra):
    out = {'id': rid, 'name': name, 'role': role, 'rect': [float(v) for v in rect],
           'walls': ['N', 'S', 'E', 'W'], 'doors': [], 'windows': [], 'points': []}
    out.update(extra)
    return out


def _door(r, side, centre, width, material='wood'):
    _, origin, _ = C.edge(r, side)
    r['doors'].append({'id': r['id'] + '_d' + str(len(r['doors']) + 1), 'edge': side,
                       'offset': round(centre - origin, 3), 'width': width, 'height': DOOR_H,
                       'material': material})


def connect(rooms, a, b, width=0.9, at=None):
    """Matching doors on both sides of the wall a and b share (centre or ``at``)."""
    ra, rb = rooms[a], rooms[b]
    touching = C.contact(ra, rb)
    if not touching:
        raise ValueError('%s and %s do not share a wall' % (a, b))
    side, lo, hi = max(touching, key=lambda t: t[2] - t[1])
    centre = (lo + hi) / 2.0 if at is None else at
    if centre - width / 2.0 < lo - 1e-9 or centre + width / 2.0 > hi + 1e-9:
        raise ValueError('door does not fit the wall between %s and %s' % (a, b))
    _door(ra, side, centre, width)
    _door(rb, C.OPPOSITE[side], centre, width)


def outside_door(rooms, rid, side, width=1.0, material='glass'):
    r = rooms[rid]
    runs = C.exterior_runs(r, list(rooms.values()), side)
    lo, hi = max(runs, key=lambda t: t[1] - t[0])
    _door(r, side, (lo + hi) / 2.0, width, material)


def finish(rooms, window_roles=None, skip_windows=()):
    """Windows centred on each exterior run of 2 m or more, one light per room."""
    rooms_list = list(rooms.values())
    for r in rooms_list:
        r['points'].append({'id': r['id'] + '_l1', 'type': 'light', 'x': round(r['rect'][2] / 2, 3),
                            'z': round(r['rect'][3] / 2, 3)})
        if r['id'] in skip_windows or (window_roles is not None and C.role(r) not in window_roles):
            continue
        for side in C.EDGES:
            _, origin, _ = C.edge(r, side)
            for lo, hi in C.exterior_runs(r, rooms_list, side):
                if hi - lo < 2.0:
                    continue
                centre = (lo + hi) / 2.0
                width = min(2.4, hi - lo - 0.8)
                taken = [(o['offset'] + origin - o['width'] / 2, o['offset'] + origin + o['width'] / 2)
                         for o in r['doors'] if o['edge'] == side]
                if any(min(q, centre + width / 2) - max(p, centre - width / 2) > -0.1 for p, q in taken):
                    continue
                r['windows'].append({'id': r['id'] + '_w' + str(len(r['windows']) + 1), 'edge': side,
                                     'offset': round(centre - origin, 3), 'width': round(width, 3),
                                     'height': 1.5, 'sill': 0.9})


def building(kind, site, storeys, meta=None):
    """storeys: [(template, rooms dict, level count)] from the ground up."""
    levels, floors, index = [], {}, 0
    for template, rooms, count in storeys:
        floors[template] = {'rooms': list(rooms.values())}
        for _ in range(count):
            levels.append({'index': index, 'name': C.floor_name(index), 'template': template})
            index += 1
    out = {'meta': dict({'name': kind, 'type': kind, 'north': '-Z'}, **(meta or {})),
           'site': {'w': float(site[0]), 'd': float(site[1])},
           'floor_height': 3.8, 'wall_h': WALL_H, 'wall_t': 0.2, 'levels': levels, 'floors': floors}
    return copy.deepcopy(out)


def _index(*rooms):
    return {r['id']: r for r in rooms}


# ── office: two storeys, central corridor, two stair cores ──────────────────
def office():
    def south_band(suffix=''):
        return [room('stairs_a', 'الدرج أ', 'stairs', (3, 9.5, 2.4, 6), core_id='core_a'),
                room('open_office_s', 'مكاتب مفتوحة جنوب', 'open_office', (5.4, 9.5, 7.6, 6)),
                room('pantry', 'مطبخ صغير', 'pantry', (13, 9.5, 2, 6)),
                room('prayer_room', 'مصلى', 'prayer_room', (15, 9.5, 3.5, 6)),
                room('it', 'غرفة الخوادم', 'it', (18.5, 9.5, 2, 6)),
                room('wc_men', 'دورة مياه الرجال', 'toilet_male', (20.5, 9.5, 2, 6)),
                room('wc_women', 'دورة مياه النساء', 'toilet_female', (22.5, 9.5, 2.1, 6)),
                room('stairs_b', 'الدرج ب', 'stairs', (24.6, 9.5, 2.4, 6), core_id='core_b')]

    g = _index(room('open_office_n', 'مكاتب مفتوحة شمال', 'open_office', (3, 2, 9, 6)),
               room('lobby', 'بهو المدخل', 'lobby', (12, 2, 5, 6)),
               room('reception', 'الاستقبال', 'reception', (17, 2, 3, 6)),
               room('meeting', 'غرفة اجتماعات', 'meeting_room', (20, 2, 4, 6)),
               room('office_ne', 'مكتب المدير', 'office', (24, 2, 3, 6)),
               room('corridor', 'الممر', 'corridor', (3, 8, 24, 1.5)),
               *south_band())
    for rid in g:
        if rid not in ('corridor',):
            connect(g, rid, 'corridor', 1.0)
    connect(g, 'lobby', 'reception', 0.9)
    outside_door(g, 'lobby', 'N', 1.8)
    outside_door(g, 'stairs_a', 'S', 1.0, 'metal')
    outside_door(g, 'stairs_b', 'S', 1.0, 'metal')
    finish(g, skip_windows={'stairs_a', 'stairs_b', 'wc_men', 'wc_women', 'it', 'lobby'})

    u = _index(room('open_office_n', 'مكاتب مفتوحة شمال', 'open_office', (3, 2, 12, 6)),
               room('meeting', 'غرفة اجتماعات', 'meeting_room', (15, 2, 4, 6)),
               room('office_a', 'مكتب أ', 'office', (19, 2, 4, 6)),
               room('office_b', 'مكتب ب', 'office', (23, 2, 4, 6)),
               room('corridor', 'الممر', 'corridor', (3, 8, 24, 1.5)),
               *south_band())
    for rid in u:
        if rid != 'corridor':
            connect(u, rid, 'corridor', 1.0)
    finish(u, skip_windows={'stairs_a', 'stairs_b', 'wc_men', 'wc_women', 'it'})
    return building('office', (30, 18), [('ground', g, 1), ('typical', u, 1)])


# ── mixed use: three shops on the street, two apartments above ──────────────
def mixed_use():
    g = _index(room('shop_01', 'محل 1', 'shop', (2, 2, 5, 12)),
               room('shop_02', 'محل 2', 'shop', (7, 2, 5, 12)),
               room('res_lobby', 'مدخل السكن', 'residential_lobby', (12, 2, 3, 6)),
               room('stairs', 'الدرج', 'stairs', (12, 8, 3, 6), core_id='core'),
               room('shop_03', 'محل 3', 'shop', (15, 2, 7, 12)),
               room('store_01', 'مستودع محل 1', 'shop_storage', (2, 14, 3, 2)),
               room('wc_01', 'دورة مياه محل 1', 'toilet', (5, 14, 2, 2)),
               room('store_02', 'مستودع محل 2', 'shop_storage', (7, 14, 3, 2)),
               room('wc_02', 'دورة مياه محل 2', 'toilet', (10, 14, 2, 2)),
               room('store_03', 'مستودع محل 3', 'shop_storage', (15, 14, 4, 2)),
               room('wc_03', 'دورة مياه محل 3', 'toilet', (19, 14, 3, 2)))
    for shop, store, wc in (('shop_01', 'store_01', 'wc_01'), ('shop_02', 'store_02', 'wc_02'),
                            ('shop_03', 'store_03', 'wc_03')):
        connect(g, shop, store, 0.9)
        connect(g, shop, wc, 0.8)
        outside_door(g, shop, 'N', 2.4)
    connect(g, 'res_lobby', 'stairs', 1.0)
    outside_door(g, 'res_lobby', 'N', 1.2)
    finish(g, window_roles={'shop'})

    u = _index(room('landing', 'بسطة الدرج', 'corridor', (12, 2, 3, 6)),
               room('stairs', 'الدرج', 'stairs', (12, 8, 3, 6), core_id='core'),
               room('a_hall', 'ممر الشقة أ', 'corridor', (10.8, 2, 1.2, 14), unit_id='A'),
               room('a_living', 'صالة الشقة أ', 'living', (2, 2, 8.8, 5), unit_id='A'),
               room('a_kitchen', 'مطبخ الشقة أ', 'kitchen', (2, 7, 4, 4), unit_id='A'),
               room('a_bath', 'حمام الشقة أ', 'bathroom', (6, 7, 4.8, 4), unit_id='A'),
               room('a_bed', 'غرفة نوم الشقة أ', 'bedroom', (2, 11, 8.8, 5), unit_id='A'),
               room('b_hall', 'ممر الشقة ب', 'corridor', (15, 2, 1.2, 14), unit_id='B'),
               room('b_living', 'صالة الشقة ب', 'living', (16.2, 2, 5.8, 5), unit_id='B'),
               room('b_kitchen', 'مطبخ الشقة ب', 'kitchen', (16.2, 7, 5.8, 3), unit_id='B'),
               room('b_bath', 'حمام الشقة ب', 'bathroom', (16.2, 10, 5.8, 2), unit_id='B'),
               room('b_bed', 'غرفة نوم الشقة ب', 'bedroom', (16.2, 12, 5.8, 4), unit_id='B'))
    connect(u, 'landing', 'stairs', 1.0)
    connect(u, 'landing', 'a_hall', 1.0)
    connect(u, 'landing', 'b_hall', 1.0)
    for rid in ('a_living', 'a_bath', 'a_bed'):
        connect(u, rid, 'a_hall', 0.9)
    connect(u, 'a_kitchen', 'a_living', 0.9)
    for rid in ('b_living', 'b_kitchen', 'b_bath', 'b_bed'):
        connect(u, rid, 'b_hall', 0.9)
    finish(u, window_roles={'living', 'bedroom', 'kitchen'})
    return building('mixed_use', (24, 18), [('ground', g, 1), ('flats', u, 1)])


# ── boys' school: eight classrooms on two storeys ───────────────────────────
def school():
    def ends():
        return [room('stairs_w', 'الدرج الغربي', 'stairs', (2, 12.4, 2.6, 7.6), core_id='core_w'),
                room('stairs_e', 'الدرج الشرقي', 'stairs', (35.4, 12.4, 2.6, 7.6), core_id='core_e'),
                room('corridor', 'الممر', 'corridor', (2, 10, 36, 2.4))]

    g = _index(room('lobby', 'بهو المدخل', 'lobby', (2, 2, 6, 8)),
               *[room('class_g%d' % (k + 1), 'فصل %d' % (k + 1), 'classroom', (8 + 7.5 * k, 2, 7.5, 8))
                 for k in range(4)],
               room('office', 'الإدارة', 'office', (4.6, 12.4, 4, 7.6)),
               room('staff_room', 'غرفة المعلمين', 'staff_room', (8.6, 12.4, 4.4, 7.6)),
               room('wc_staff', 'دورة مياه المعلمين', 'toilet_staff', (13, 12.4, 2, 7.6)),
               room('health', 'الوحدة الصحية', 'health_room', (15, 12.4, 3, 7.6)),
               room('wc_students', 'دورات مياه الطلاب', 'toilet_students', (18, 12.4, 6, 7.6)),
               room('prayer', 'المصلى', 'prayer_room', (24, 12.4, 6, 7.6)),
               room('canteen', 'المقصف', 'canteen', (30, 12.4, 5.4, 7.6)),
               *ends())
    for rid in g:
        if rid != 'corridor':
            connect(g, rid, 'corridor', 1.0)
    outside_door(g, 'lobby', 'N', 1.8)
    outside_door(g, 'stairs_w', 'S', 1.0, 'metal')
    outside_door(g, 'stairs_e', 'S', 1.0, 'metal')
    finish(g, skip_windows={'stairs_w', 'stairs_e', 'wc_staff', 'wc_students', 'corridor'})

    u = _index(room('lab', 'مختبر العلوم', 'science_lab', (2, 2, 10, 8)),
               *[room('class_1%s' % c, 'فصل %s' % c, 'classroom', (12 + 7 * k, 2, 7, 8))
                 for k, c in enumerate('abc')],
               room('lab_store', 'مخزن المختبر', 'storage', (33, 2, 5, 8)),
               room('library', 'مصادر التعلم', 'library', (4.6, 12.4, 8, 7.6)),
               room('class_1d', 'فصل د', 'classroom', (12.6, 12.4, 7.4, 7.6)),
               room('wc_students', 'دورات مياه الطلاب', 'toilet_students', (20, 12.4, 4, 7.6)),
               room('computer_lab', 'معمل الحاسب', 'computer_lab', (24, 12.4, 8, 7.6)),
               room('store', 'مخزن', 'storage', (32, 12.4, 3.4, 7.6)),
               *ends())
    for rid in u:
        if rid != 'corridor':
            connect(u, rid, 'corridor', 1.0)
    finish(u, skip_windows={'stairs_w', 'stairs_e', 'wc_students', 'corridor', 'store', 'lab_store'})
    return building('school', (42, 32), [('ground', g, 1), ('upper', u, 1)])


# ── mosque in Riyadh on a plot whose north is turned 26.2 degrees west ──────
def mosque():
    g = _index(room('prayer_hall', 'مصلى الرجال', 'prayer_hall', (4, 4, 12, 16), wall_h=5.0),
               room('mihrab', 'المحراب', 'mihrab', (2.5, 11, 1.5, 2)),
               room('imam_room', 'غرفة الإمام', 'imam_room', (0.5, 13, 3.5, 3)),
               room('imam_wc', 'دورة مياه الإمام', 'imam_wc', (0.5, 16, 2, 1.5)),
               room('shoe_area', 'خلع الأحذية', 'shoe_area', (16, 4, 3, 6)),
               room('entrance', 'مدخل الرجال', 'entrance', (16, 10, 3, 4)),
               room('wudu_male', 'ميضأة الرجال', 'wudu_male', (19, 4, 4, 6)),
               room('wc_male', 'دورات مياه الرجال', 'toilet_male', (23, 4, 3, 6)),
               room('women_hall', 'مصلى النساء', 'women_prayer_hall', (16, 14, 6, 6)),
               room('women_entrance', 'مدخل النساء', 'women_entrance', (22, 14, 3, 3)),
               room('wudu_female', 'ميضأة النساء', 'wudu_female', (22, 17, 3, 3)),
               room('wc_female', 'دورات مياه النساء', 'toilet_female', (22, 20, 3, 2)))
    connect(g, 'prayer_hall', 'mihrab', 1.2)
    connect(g, 'mihrab', 'imam_room', 0.9)
    connect(g, 'imam_room', 'imam_wc', 0.8)
    connect(g, 'entrance', 'prayer_hall', 2.4)
    connect(g, 'shoe_area', 'entrance', 1.2)
    connect(g, 'shoe_area', 'prayer_hall', 1.8)
    connect(g, 'shoe_area', 'wudu_male', 1.2)
    connect(g, 'wudu_male', 'wc_male', 1.0)
    connect(g, 'women_entrance', 'women_hall', 1.2)
    connect(g, 'women_entrance', 'wudu_female', 1.0)
    connect(g, 'wudu_female', 'wc_female', 0.9)
    outside_door(g, 'entrance', 'E', 2.4, 'wood')
    outside_door(g, 'women_entrance', 'E', 1.2, 'wood')
    outside_door(g, 'imam_room', 'W', 0.9, 'wood')
    outside_door(g, 'prayer_hall', 'N', 1.8, 'wood')
    outside_door(g, 'prayer_hall', 'S', 1.8, 'wood')
    finish(g, window_roles={'women_prayer_hall', 'imam_room'})
    for side in ('N', 'S'):   # windows on the two side walls of the hall, none on the qibla wall
        hall = g['prayer_hall']
        for centre in (3.0, 9.0):
            hall['windows'].append({'id': 'prayer_hall_w%s%d' % (side, int(centre)), 'edge': side,
                                    'offset': centre, 'width': 1.6, 'height': 1.6, 'sill': 1.2})
    return building('mosque', (28, 24), [('ground', g, 1)],
                    meta={'city': 'الرياض', 'qibla': {'plot_north_deg': -26.2}})


# ── hotel: ground floor and two alike guest floors ──────────────────────────
def hotel():
    def cores():
        return [room('svc_elevator', 'مصعد الخدمة', 'service_elevator', (2, 4.6, 2.6, 4), core_id='svc'),
                room('stairs_w', 'الدرج الغربي', 'stairs', (2, 10.4, 2.6, 6.6), core_id='stairs_w'),
                room('elevator', 'مصعد النزلاء', 'elevator', (26.2, 10.4, 2.6, 3), core_id='lift'),
                room('stairs_e', 'الدرج الشرقي', 'stairs', (28.8, 10.4, 2.8, 6.6), core_id='stairs_e'),
                room('corridor', 'الممر', 'corridor', (2, 8.6, 29.6, 1.8))]

    g = _index(room('store_g', 'مخزن المطعم', 'storage', (2, 2, 2.6, 2.6)),
               room('restaurant', 'المطعم', 'restaurant', (4.6, 2, 7.4, 6.6)),
               room('lobby', 'بهو الفندق', 'lobby', (12, 2, 10, 6.6)),
               room('reception', 'الاستقبال', 'reception', (22, 2, 4, 6.6)),
               room('luggage', 'غرفة الأمتعة', 'luggage_room', (26, 2, 2.4, 6.6)),
               room('office', 'مكتب الإدارة', 'office', (28.4, 2, 3.2, 6.6)),
               room('kitchen', 'مطبخ الفندق', 'kitchen', (4.6, 10.4, 7, 6.6)),
               room('wc_m', 'دورة مياه الرجال', 'toilet_male', (11.6, 10.4, 3, 4)),
               room('wc_f', 'دورة مياه النساء', 'toilet_female', (14.6, 10.4, 3, 4)),
               room('store_k', 'مخزن المطبخ', 'storage', (11.6, 14.4, 6, 2.6)),
               room('prayer', 'المصلى', 'prayer_room', (17.6, 10.4, 4, 6.6)),
               room('staff', 'غرفة الموظفين', 'staff_room', (21.6, 10.4, 4.6, 6.6)),
               *cores())
    for rid in ('restaurant', 'lobby', 'office', 'kitchen', 'wc_m', 'wc_f', 'prayer', 'staff', 'svc_elevator',
                'stairs_w', 'elevator', 'stairs_e'):
        connect(g, rid, 'corridor', 1.0)
    connect(g, 'lobby', 'restaurant', 1.8)
    connect(g, 'lobby', 'reception', 1.2)
    connect(g, 'reception', 'luggage', 0.9)
    connect(g, 'restaurant', 'store_g', 0.9)
    connect(g, 'kitchen', 'store_k', 0.9)
    outside_door(g, 'lobby', 'N', 2.4)
    outside_door(g, 'stairs_w', 'S', 1.0, 'metal')
    outside_door(g, 'stairs_e', 'S', 1.0, 'metal')
    finish(g, window_roles={'restaurant', 'lobby', 'office', 'kitchen', 'prayer_room', 'staff_room'})

    rooms = [room('linen', 'غرفة البياضات', 'linen_room', (2, 2, 2.6, 2.6)), *cores()]
    for k in range(5):
        x = 4.6 + 5.4 * k
        rooms += [room('room_n%d' % k, 'غرفة %d' % (101 + k), 'guest_room', (x, 2, 3.6, 6.6), unit_id='n%d' % k),
                  room('bath_n%d' % k, 'حمام %d' % (101 + k), 'bathroom', (x + 3.6, 4.6, 1.8, 4), unit_id='n%d' % k)]
    for k in range(4):
        x = 4.6 + 5.4 * k
        rooms += [room('room_s%d' % k, 'غرفة %d' % (111 + k), 'guest_room', (x, 10.4, 3.6, 6.6), unit_id='s%d' % k),
                  room('bath_s%d' % k, 'حمام %d' % (111 + k), 'bathroom', (x + 3.6, 10.4, 1.8, 4), unit_id='s%d' % k)]
    u = _index(*rooms)
    for rid, r in u.items():
        if C.role(r) in ('guest_room', 'stairs', 'elevator', 'service_elevator'):
            connect(u, rid, 'corridor', 1.0)
        if C.role(r) == 'bathroom':
            connect(u, rid, 'room_' + rid[5:], 0.8)
    connect(u, 'linen', 'svc_elevator', 1.0)
    finish(u, window_roles={'guest_room'})
    return building('hotel', (34, 20), [('ground', g, 1), ('guest', u, 2)])


BUILDERS = {'office': office, 'retail': mixed_use, 'school': school, 'mosque': mosque, 'hotel': hotel}
OPTIONS = {'office': {'sprinklered': True},
           'retail': {'sprinklered': True, 'streets': ['N']},
           'school': {'sprinklered': True, 'gender': 'boys'},
           'mosque': {'sprinklered': True, 'worshippers': 250, 'women': 40},
           'hotel': {'sprinklered': True, 'stars': 4, 'rooms': 18}}
