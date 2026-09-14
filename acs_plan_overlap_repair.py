"""One bounded position-only proposal for rejected, detail-free plan drafts."""
import json
from acs_plan_review import _structure, _geometry, canonical, _number, PlanError


def repair_overlap(building, brief, budget):
    _structure(building)
    issues, _ = _geometry(building)
    if not issues or any(i['code'] != 'ROOM_OVERLAP' for i in issues):
        return building
    if budget['used'] >= budget['limit']:
        return building
    rooms = [(t, r) for t, f in building['floors'].items() for r in f['rooms']]
    # Moving detailed geometry needs a different, explicit edit contract.
    allowed = {'id', 'name', 'role', 'rect', 'brief', 'walls', 'wall_h', 'acs_unresolved',
               'doors', 'windows', 'points'}
    if any(set(r) - allowed or any(r.get(k) for k in ('doors', 'windows', 'points')) for _, r in rooms):
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
