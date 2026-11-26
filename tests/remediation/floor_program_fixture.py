"""A hand-drawn model that follows the owner's confirmed floor program.

The owner's brief (fixtures/brief_reader/owner_brief.txt) asks for three
different flats on a 20 × 25 m plot: the building block 13 × 16 m placed west
(1.5 m service lane), a 5.5 m front yard with two stalls, and a shared stair
and lift core at the north-west corner on every floor. This module draws one
plan that follows that program floor by floor, with every target size within
its tolerance, so the per-floor checks have a passing model; the failing
variants in test_floor_program.py are edits of it.

Rooms are given in a local frame (x east, z south) from the block's
north-west corner; openings are added from the listed connections. Any area
the listed rooms leave uncovered becomes part of an adjacent corridor, so no
upper room hangs over a void.
"""
import copy

ORIGIN = (1.5, 5.5)          # the block's north-west corner on the land
BLOCK = (13.0, 16.0)

CORE = [('stairs', 'الدرج', [0, 0, 2.6, 5.0], {'core_id': 'stairs_core'}),
        ('elevator', 'المصعد', [2.6, 2.8, 2.0, 2.2], {'core_id': 'elevator_core'})]

# (key, role, name, local rect). Keys are short room ids within a floor.
GROUND = [
    ('lobby', 'entrance', 'بهو مدخل العمارة', [2.6, 0, 2.0, 2.8]),
    ('foyer', 'entrance', 'ردهة مدخل الضيوف', [4.6, 0, 1.2, 2.8]),
    ('hall', 'corridor', 'ممر الشقة', [4.6, 2.8, 1.2, 13.2]),
    ('majlis', 'majlis', 'مجلس الضيوف', [5.8, 0, 4.0, 4.5]),
    ('guest_wc', 'bathroom', 'مغاسل ودورة مياه الضيوف', [9.8, 0, 3.2, 3.3]),
    ('pool_bath', 'bathroom', 'حمام المسبح', [9.8, 3.3, 3.2, 1.2]),
    ('living', 'living', 'الصالة العائلية', [5.8, 4.5, 4.0, 5.0]),
    ('dining', 'dining', 'السفرة', [9.8, 4.5, 3.2, 3.4]),
    ('kitchen', 'kitchen', 'المطبخ الرئيسي', [0, 5.0, 4.6, 2.8]),
    ('pantry', 'pantry', 'مستودع المؤن', [0, 7.8, 1.4, 1.8]),
    ('laundry', 'laundry', 'الغسيل والتخزين', [1.4, 7.8, 1.8, 1.8]),
    ('service', 'corridor', 'ممر الخدمة', [3.2, 7.8, 1.4, 1.8]),
    ('kid_1', 'bedroom', 'غرفة نوم للأبناء 1', [0, 9.6, 4.6, 2.45]),
    ('family_bath', 'bathroom', 'الحمام العائلي', [0, 12.05, 4.6, 1.5]),
    ('kid_2', 'bedroom', 'غرفة نوم للأبناء 2', [0, 13.55, 4.6, 2.45]),
    ('master', 'bedroom', 'غرفة النوم الرئيسية', [5.8, 9.5, 4.0, 3.8]),
    ('master_bath', 'bathroom', 'حمام غرفة النوم الرئيسية', [9.8, 9.5, 3.2, 3.8]),
]
GROUND_LINKS = [('lobby', 'stairs'), ('lobby', 'elevator'), ('lobby', 'foyer'), ('foyer', 'hall'), ('foyer', 'majlis'),
                ('majlis', 'guest_wc'), ('hall', 'living'), ('living', 'dining'), ('dining', 'pool_bath'),
                ('hall', 'kitchen'), ('kitchen', 'pantry'), ('kitchen', 'laundry'), ('hall', 'service'),
                ('hall', 'kid_1'), ('hall', 'family_bath'), ('hall', 'kid_2'), ('hall', 'master'),
                ('master', 'master_bath')]

FIRST = [
    ('landing', 'lobby', 'بسطة الدرج', [2.6, 0, 2.0, 2.8]),
    ('foyer', 'entrance', 'مدخل الشقة', [4.6, 0, 1.2, 2.8]),
    ('hall', 'corridor', 'ممر الشقة', [4.6, 2.8, 1.2, 13.2]),
    ('majlis', 'majlis', 'مجلس أمامي', [5.8, 0, 4.0, 3.6]),
    ('majlis_wc', 'bathroom', 'دورة مياه المجلس', [9.8, 0, 3.2, 2.2]),
    ('living', 'living', 'الصالة والسفرة', [5.8, 3.6, 4.0, 6.6]),
    ('extra_1', 'bedroom', 'غرفة نوم إضافية 1', [9.8, 2.2, 3.2, 3.3]),
    ('extra_2', 'bedroom', 'غرفة نوم إضافية 2', [9.8, 5.5, 3.2, 3.3]),
    ('second', 'bedroom', 'غرفة نوم ثانية', [9.8, 8.8, 3.2, 3.6]),
    ('kitchen', 'kitchen', 'مطبخ مغلق', [0, 5.0, 4.6, 2.7]),
    ('pantry', 'pantry', 'خزانة مؤن', [0, 7.7, 1.6, 1.6]),
    ('extra_bath', 'bathroom', 'حمام إضافي', [0, 12.0, 4.6, 1.6]),
    ('laundry', 'laundry', 'غرفة غسيل', [1.6, 7.7, 1.8, 1.6]),
    ('master', 'bedroom', 'جناح الوالدين', [5.8, 10.2, 4.0, 3.8]),
    ('master_bath', 'bathroom', 'حمام جناح الوالدين', [9.8, 12.4, 3.2, 3.6]),
]
FIRST_LINKS = [('landing', 'stairs'), ('landing', 'elevator'), ('landing', 'foyer'), ('foyer', 'hall'),
               ('foyer', 'majlis'), ('majlis', 'majlis_wc'), ('hall', 'living'), ('living', 'extra_1'),
               ('living', 'extra_2'), ('living', 'second'), ('hall', 'kitchen'), ('kitchen', 'pantry'),
               ('kitchen', 'laundry'), ('hall', 'extra_bath'), ('hall', 'master'), ('master', 'master_bath')]

SECOND = [
    ('landing', 'lobby', 'بسطة الدرج', [2.6, 0, 2.0, 2.8]),
    ('foyer', 'entrance', 'مدخل الشقة', [4.6, 0, 1.2, 2.8]),
    ('hall', 'corridor', 'ممر الشقة', [4.6, 2.8, 1.2, 13.2]),
    ('office', 'office', 'مكتب', [5.8, 0, 3.0, 3.2]),
    ('terrace', 'terrace', 'تراس شمالي', [8.8, 0, 4.2, 4.7]),
    ('living', 'living', 'الصالة والسفرة', [5.8, 4.7, 4.5, 6.0]),
    ('kitchen', 'kitchen', 'مطبخ شبه مفتوح', [0, 5.0, 4.6, 3.0]),
    ('bath', 'bathroom', 'حمام كامل', [0, 8.0, 4.6, 1.6]),
    ('second', 'bedroom', 'غرفة نوم ثانية', [0, 9.6, 4.6, 2.65]),
    ('master', 'bedroom', 'الجناح الرئيسي', [5.8, 10.7, 4.0, 4.2]),
    ('dressing', 'dressing', 'غرفة الملابس', [9.8, 10.7, 3.2, 2.0]),
    ('master_bath', 'bathroom', 'حمام الجناح', [9.8, 12.7, 3.2, 2.2]),
]
SECOND_LINKS = [('landing', 'stairs'), ('landing', 'elevator'), ('landing', 'foyer'), ('foyer', 'hall'),
                ('foyer', 'office'), ('office', 'terrace'), ('hall', 'living'), ('living', 'terrace'),
                ('hall', 'kitchen'), ('hall', 'bath'), ('hall', 'second'), ('hall', 'master'),
                ('master', 'dressing'), ('master', 'master_bath')]

FLOORS = (('level_0', GROUND, GROUND_LINKS), ('level_1', FIRST, FIRST_LINKS), ('level_2', SECOND, SECOND_LINKS))
OPEN = {'terrace'}


def _edge(rect, side):
    x, z, w, d = rect
    return (z if side == 'N' else z + d, x, x + w) if side in 'NS' else (x if side == 'W' else x + w, z, z + d)


OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}


def _door(a, b):
    for side, other in OPPOSITE.items():
        line, lo, hi = _edge(a['rect'], side)
        line2, lo2, hi2 = _edge(b['rect'], other)
        low, high = max(lo, lo2), min(hi, hi2)
        if abs(line - line2) < 1e-6 and high - low >= 1.1 - 1e-6:
            c = (low + high) / 2
            if a.get('walls') != 'none':
                a['doors'].append({'id': a['id'] + '_d' + str(len(a['doors'])), 'edge': side, 'offset': round(c - lo, 4),
                                   'width': 0.9, 'height': 2.1, 'material': 'wood'})
            if b.get('walls') != 'none':
                b['doors'].append({'id': b['id'] + '_d' + str(len(b['doors'])), 'edge': other, 'offset': round(c - lo2, 4),
                                   'width': 0.9, 'height': 2.1, 'material': 'wood'})
            return
    raise AssertionError('no shared wall for ' + a['id'] + ' / ' + b['id'])


def _fill(rooms, template):
    """Cover what the listed rooms leave open with corridor pieces (0.1 m grid)."""
    W, D = int(BLOCK[0] * 10), int(BLOCK[1] * 10)
    free = [[True] * W for _ in range(D)]
    cell = lambda v: int(v * 10 + 0.5 + 1e-6)
    for r in rooms:
        x, z, w, d = r['rect']
        for j in range(cell(z), cell(z + d)):
            for i in range(cell(x), cell(x + w)):
                free[j][i] = False
    pieces = []
    for j in range(D):
        for i in range(W):
            if not free[j][i]:
                continue
            w = 0
            while i + w < W and free[j][i + w]:
                w += 1
            d = 0
            while j + d < D and all(free[j + d][i:i + w]):
                d += 1
            for jj in range(j, j + d):
                for ii in range(i, i + w):
                    free[jj][ii] = False
            pieces.append([i / 10, j / 10, w / 10, d / 10])
    return [{'id': template + '_filler_' + str(n + 1), 'role': 'corridor', 'name': 'ممر', 'rect': p}
            for n, p in enumerate(pieces)]


def local_floor(template, spec, links):
    rooms = []
    for role_key, (role, name, rect, extra) in zip(('stairs', 'elevator'), CORE):
        rooms.append({'id': template + '_' + role_key, 'role': role, 'name': name, 'rect': list(rect), **extra})
    for key, role, name, rect in spec:
        rooms.append({'id': template + '_' + key, 'role': role, 'name': name, 'rect': list(rect)})
    return rooms


def owner_model():
    """The passing model in land coordinates, with openings, lights and plot meta."""
    floors = {}
    for template, spec, links in FLOORS:
        rooms = local_floor(template, spec, links)
        rooms += _fill(rooms, template)
        by_key = {r['id'][len(template) + 1:]: r for r in rooms}
        for r in rooms:
            r.update(walls='none' if r['id'].endswith('terrace') else ['N', 'S', 'E', 'W'], doors=[], windows=[], points=[])
            if r['role'] not in ('stairs', 'elevator', 'lobby') and not (template == 'level_0' and r['id'].endswith('lobby')):
                r['unit_id'] = 'apartment_1'
        for a, b in links:
            _door(by_key[a], by_key[b])
        for piece in (r for r in rooms if '_filler_' in r['id']):
            hall = next((h for h in rooms if h['role'] in ('corridor', 'living') and '_filler_' not in h['id']
                         and _touches(h, piece)), None) or next(
                (h for h in rooms if h['role'] in ('corridor', 'living') and h is not piece and _touches(h, piece)), None)
            assert hall is not None, piece
            _door(hall, piece)
        for r in rooms:
            x, z, w, d = r['rect']
            r['points'] = [{'id': r['id'] + '_light', 'type': 'light', 'x': round(w / 2, 3), 'z': round(d / 2, 3)}]
        floors[template] = {'rooms': rooms}
    ground = {r['id']: r for r in floors['level_0']['rooms']}
    # The building door on the street (north) and the kitchen's service door on the west lane.
    ground['level_0_lobby']['doors'].append({'id': 'level_0_lobby_street', 'edge': 'N', 'offset': 1.0, 'width': 1.2,
                                             'height': 2.1, 'material': 'wood'})
    _windows(floors)
    for floor in floors.values():
        for r in floor['rooms']:
            x, z, w, d = r['rect']
            r['rect'] = [round(x + ORIGIN[0], 4), round(z + ORIGIN[1], 4), w, d]
    return {'site': {'w': 20, 'd': 25}, 'floor_height': 3.2, 'wall_h': 3.0, 'wall_t': 0.2,
            'levels': [{'id': 'L' + str(i), 'index': i, 'template': t} for i, (t, _, _) in enumerate(FLOORS)],
            'floors': floors, 'meta': {'assumptions': ['نموذج اختبار مرسوم يدويًا يتبع برنامج المالك.']}}


def _touches(a, b):
    for side, other in OPPOSITE.items():
        line, lo, hi = _edge(a['rect'], side)
        line2, lo2, hi2 = _edge(b['rect'], other)
        if abs(line - line2) < 1e-6 and min(hi, hi2) - max(lo, lo2) >= 1.1 - 1e-6:
            return True
    return False


def _windows(floors):
    """One window per habitable room on an outside wall facing a street or a setback over 1.5 m."""
    gaps = {'N': 5.5, 'E': 5.5, 'S': 3.5, 'W': 1.5}
    for floor in floors.values():
        rooms = floor['rooms']
        for r in rooms:
            if r['role'] in ('corridor', 'entrance', 'lobby', 'stairs', 'elevator', 'pantry', 'terrace') or r.get('walls') == 'none':
                continue
            for side in ('N', 'E', 'S', 'W'):
                line, lo, hi = _edge(r['rect'], side)
                outside = {'N': line <= 1e-6, 'S': line >= BLOCK[1] - 1e-6, 'W': line <= 1e-6, 'E': line >= BLOCK[0] - 1e-6}[side]
                if not outside or hi - lo < 1.8 or any(o['edge'] == side for o in r['doors']):
                    continue
                if side == 'W' and r['role'] in ('bedroom', 'living', 'majlis', 'kitchen', 'dining', 'office'):
                    pass  # a 1.5 m lane: allowed (advisory below the 2 m default)
                bath = r['role'] in ('bathroom', 'laundry')
                r['windows'].append({'id': r['id'] + '_w', 'edge': side, 'offset': round((hi - lo) / 2, 4),
                                     'width': 0.6 if bath else 1.2, 'height': 0.6 if bath else 1.2,
                                     'sill': 1.5 if bath else 0.9})
                break


def owner_variant(edit):
    """A deep copy of the passing model changed by ``edit(model)``."""
    model = copy.deepcopy(owner_model())
    edit(model)
    return model
