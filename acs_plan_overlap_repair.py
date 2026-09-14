"""One bounded position-only proposal for rejected, detail-free plan drafts."""
import json
import math
from acs_plan_review import _structure, _geometry, canonical, _number, PlanError



def place_nonoverlapping(building):
    """Bounded greedy placement; failure is not proof that no packing exists.

    Single-level, detail-free drafts only. No rotation, resize, room deletion,
    or changes to site dimensions. Canonical admission remains mandatory.
    """
    if len(building['levels']) != 1 or len(building['floors']) != 1:
        return None
    template, floor = next(iter(building['floors'].items()))
    rooms = floor['rooms']
    w, d = building['site']['w'], building['site']['d']
    if math.fsum(r['rect'][2] * r['rect'][3] for r in rooms) > w*d + 1e-8*max(1, w*d):
        raise PlanError('PLAN_GEOMETRY_AREA_EXCEEDS_SITE',
                        'Generated room areas exceed the site area; positions alone cannot fit them')
    if len(rooms) > 64:
        return None
    orders = [rooms, sorted(rooms, key=lambda r: (-r['rect'][2]*r['rect'][3], r['id'])),
              sorted(rooms, key=lambda r: (-r['rect'][3], -r['rect'][2], r['id']))]
    checks = 0
    for order in orders:
        placed = {}
        for room in order:
            x0, z0, rw, rd = room['rect']
            xs, zs = {0, x0, w-rw}, {0, z0, d-rd}
            for x, z, pw, pd in placed.values():
                xs.update((x+pw, x-rw)); zs.update((z+pd, z-rd))
            candidates = sorted(((x,z) for x in xs for z in zs
                                 if 0 <= x <= w-rw and 0 <= z <= d-rd),
                                key=lambda p: (abs(p[0]-x0)+abs(p[1]-z0), p[1], p[0]))
            for x,z in candidates:
                blocked = False
                for ox,oz,ow,od in placed.values():
                    checks += 1
                    if checks > 100000:
                        return None
                    if min(x+rw,ox+ow) > max(x,ox) and min(z+rd,oz+od) > max(z,oz):
                        blocked = True
                        break
                if not blocked:
                    placed[room['id']] = [x,z,rw,rd]
                    break
            else:
                break
        if len(placed) != len(rooms):
            continue
        candidate = json.loads(canonical(building))
        for room in candidate['floors'][template]['rooms']:
            room['rect'] = placed[room['id']]
        if not _geometry(candidate)[0]:
            return candidate
    return None


def repair_overlap(building, brief, budget):
    _structure(building)
    issues, _ = _geometry(building)
    if not issues or any(i['code'] not in {'ROOM_OVERLAP', 'ADDITIONAL_ISSUES_OMITTED'} for i in issues):
        return building
    rooms = [(t, r) for t, f in building['floors'].items() for r in f['rooms']]
    # Moving detailed geometry needs a different, explicit edit contract.
    allowed = {'id', 'name', 'role', 'rect', 'brief', 'walls', 'wall_h', 'acs_unresolved',
               'doors', 'windows', 'points'}
    if any(set(r) - allowed or any(r.get(k) for k in ('doors', 'windows', 'points')) for _, r in rooms):
        return building
    positioned = place_nonoverlapping(building)
    if positioned is not None:
        return positioned
    if budget['used'] >= budget['limit']:
        return building
    import acs_understand as U
    context = {'site': building['site'], 'levels': building['levels'],
               'rooms': [{'template': t, 'id': r['id'], 'role': r.get('role'),
                          'name': r.get('name'), 'rect': r['rect']} for t, r in rooms],
               'conflicts': issues}
    prompt = ('صحح مواقع الفراغات المتداخلة في مسودة المخطط، مع مراعاة وصف المستخدم. '
              'لا تحذف أو تضف فراغات ولا تغير العرض أو العمق لأي فراغ. '
              'أعد JSON فقط بالشكل {"positions":[{"template":"...","id":"...","x":0,"z":0}]}. '
              'أعد موقع كل فراغ مرة واحدة. جميع الفراغات داخل الموقع ولا تتداخل في القالب نفسه.\n'
              + canonical(context) + '\nوصف المستخدم:\n' + brief)
    reply = U.extract_json(U.call_llm(prompt, max_tokens=U.G.stage_budget('repair'),
        truncate=False, btype=U.detect_type(brief), user_msg='', stage='repair'))
    if not isinstance(reply, dict) or set(reply) != {'positions'} or not isinstance(reply['positions'], list):
        raise PlanError('INVALID_PLAN', 'Invalid position repair response')
    expected = {(t, r['id']) for t, r in rooms}
    positions = {}
    for p in reply['positions']:
        if (not isinstance(p, dict) or set(p) != {'template', 'id', 'x', 'z'}
                or not isinstance(p['template'], str) or not isinstance(p['id'], str)
                or not _number(p['x']) or not _number(p['z'])):
            raise PlanError('INVALID_PLAN', 'Invalid position repair entry')
        key = (p['template'], p['id'])
        if key not in expected or key in positions:
            raise PlanError('INVALID_PLAN', 'Position repair changed room identity')
        positions[key] = p
    if set(positions) != expected:
        raise PlanError('INVALID_PLAN', 'Position repair omitted rooms')
    candidate = json.loads(canonical(building))
    for t, floor in candidate['floors'].items():
        for r in floor['rooms']:
            p = positions[t, r['id']]
            r['rect'][:2] = [p['x'], p['z']]
    # Failed corrections never become a saved revision; the parent still applies
    # its canonical locks, geometry, projection and compare-and-swap admission.
    remaining, _ = _geometry(candidate)
    return building if remaining else candidate
