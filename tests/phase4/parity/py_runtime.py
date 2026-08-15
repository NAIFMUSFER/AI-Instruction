# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 4.

يشغّل نفس الاستعلامات والحالات الخصومية التي يشغّلها js_runtime_body.js على
نفس ملفّ التجهيزات، ويكتب النتيجة القانونية إلى ملفّ JSON يقارنه compare.js.
لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس.
"""
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
sys.path.insert(0, PHASE)

import acs_visual as V                                     # noqa: E402
import acs_runtime as R                                    # noqa: E402
import lib_runtime_fixtures as LIB                          # noqa: E402

OUT = os.environ.get('ACS_PARITY_RUNTIME_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_runtime_py.json')
SC = LIB.load()
AT = '2026-01-01T00:00:00Z'
DECO_LAYERS = list(V.VISUAL_LAYERS)


def visual(q):
    m = copy.deepcopy(SC['models'][q['m']])
    return V.compile_visual_scene(m, q['bid'], q.get('pos'), q.get('rot') or 0,
                                  mode=q['mode'],
                                  include_decoration=bool(q.get('deco')),
                                  layers=DECO_LAYERS if q.get('deco') else None,
                                  at=AT)


out = {}
for q in SC['queries']:
    before = json.dumps(SC['models'][q['m']], sort_keys=True)
    vs = visual(q)
    vs_before = json.dumps(vs, sort_keys=True)
    scene = R.compile_runtime_scene(vs, q.get('cfg'))
    if json.dumps(SC['models'][q['m']], sort_keys=True) != before:
        raise SystemExit('the runtime compiler mutated the model: ' + q['n'])
    if json.dumps(vs, sort_keys=True) != vs_before:
        raise SystemExit('the runtime compiler mutated the visual scene: ' + q['n'])

    state = R.create_runtime_state(scene)
    objects = scene['objects']
    rooms = scene['rooms']
    portals = scene['walkability']['portals']
    first_obj = objects[0]['runtime_object_id'] if objects else 'none'
    first_room = rooms[0]['runtime_room_id'] if rooms else 'none'
    first_portal = portals[0]['portal_id'] if portals else 'none'
    spawn = (scene['defaults'].get('spawn') or {}).get('position') or [0.0, 0.0, 0.0]

    sel_state = R.create_runtime_state(scene)
    vis_state = R.create_runtime_state(scene)
    meas_state = R.create_runtime_state(scene)
    portal_state = R.create_runtime_state(scene)

    entry = {
        'scene': scene,
        'summary': R.summary(scene),
        'rule_inputs': R.rule_inputs(scene),
        'validate': R.validate_runtime_scene(scene),
        'state': state,
        'connectivity': R.room_connectivity_graph(scene),
        'nav': {m: R.validate_navigation(m, None, scene) for m in R.NAVIGATION_MODES},
        'nav_bad': R.validate_navigation('TELEPORT', None, scene),
        'capsule_default': R.validate_capsule(None),
        'capsule_bad': R.validate_capsule({'radius_m': -1, 'height_m': 0,
                                           'eye_height_m': 99}),
        'spawn_default': R.validate_spawn(scene, spawn),
        'spawn_far': R.validate_spawn(scene, [999.0, 0.0, 999.0]),
        'spawn_nearest': R.find_nearest_valid_spawn(scene, [0.0, 0.0, 0.0]),
        'query_local': R.query_spatial_index(scene, [0.0, 0.0, 0.0, 4.0, 3.0, 4.0]),
        'query_wide': R.query_spatial_index(scene, [-1e9, -1e9, -1e9, 1e9, 1e9, 1e9]),
        'query_bad': R.query_spatial_index(scene, [float('nan'), 0, 0, 1, 1, 1]),
        'move_short': R.move_query(scene, state, [0.0, 0.9, 0.0], [1.0, 0.9, 1.0]),
        'move_long': R.move_query(scene, state, [0.0, 0.9, 0.0], [20.0, 0.9, 20.0]),
        'move_bad': R.move_query(scene, state, None, [0.0, 0.0, 0.0]),
        'select': R.select_runtime_object(sel_state, scene, first_obj),
        'select_bad': R.select_runtime_object(sel_state, scene, 'no_such_object'),
        'select_null': R.select_runtime_object(sel_state, scene, None),
        'inspect': R.inspect_runtime_object(scene, first_obj, vs),
        'inspect_no_visual': R.inspect_runtime_object(scene, first_obj, None),
        'inspect_room': R.inspect_runtime_object(scene, first_room, vs),
        'inspect_bad': R.inspect_runtime_object(scene, 'no_such_object', vs),
        'hide_object': R.set_visibility(vis_state, scene, 'HIDE_OBJECT', first_obj),
        'isolate_room': R.set_visibility(vis_state, scene, 'ISOLATE_ROOM', first_room),
        'hide_discipline': R.set_visibility(vis_state, scene, 'HIDE_DISCIPLINE', 'MEP'),
        'visibility_bad_mode': R.set_visibility(vis_state, scene, 'X_RAY', None),
        'visibility_bad_target': R.set_visibility(vis_state, scene, 'HIDE_ROOM', 'nope'),
        'effective': R.effective_visibility(vis_state, scene),
        'restore': R.restore_visibility(vis_state, scene),
        'effective_after_restore': R.effective_visibility(vis_state, scene),
        'measure_points': R.create_measurement(scene, 'POINT_TO_POINT',
                                               start=[0, 0, 0], end=[3, 4, 0]),
        'measure_width': R.create_measurement(scene, 'OBJECT_WIDTH', target_id=first_obj),
        'measure_height': R.create_measurement(scene, 'OBJECT_HEIGHT', target_id=first_obj),
        'measure_room': R.create_measurement(scene, 'ROOM_DIMENSION', target_id=first_room),
        'measure_clearance': R.create_measurement(
            scene, 'CLEARANCE', target_id=first_obj,
            other_id=(objects[-1]['runtime_object_id'] if objects else 'none')),
        'measure_bad_type': R.create_measurement(scene, 'AREA', start=[0, 0, 0],
                                                 end=[1, 1, 1]),
        'measure_bad_vector': R.create_measurement(scene, 'POINT_TO_POINT',
                                                   start=[0, 0], end=[1, 1, 1]),
        'measure_bad_target': R.create_measurement(scene, 'OBJECT_WIDTH',
                                                   target_id='nope'),
        'portal_open': R.set_portal_state(portal_state, scene, first_portal, 'OPEN'),
        'portal_closed': R.set_portal_state(portal_state, scene, first_portal, 'CLOSED'),
        'portal_bad_state': R.set_portal_state(portal_state, scene, first_portal, 'AJAR'),
        'portal_bad_id': R.set_portal_state(portal_state, scene, 'nope', 'OPEN'),
        'portal_states_after': portal_state['portal_states'],
        'time_ok': R.advance_simulation_time(meas_state, 1.5),
        'time_bad': R.advance_simulation_time(meas_state, -1.0),
        'time_after': meas_state['simulation_time'],
        'sel_state_after': sel_state,
        'vis_state_after': vis_state,
    }
    entry['add_measure'] = R.add_measurement(meas_state, scene, 'OBJECT_WIDTH',
                                             target_id=first_obj)
    entry['meas_state_after'] = meas_state
    out[q['n']] = entry

adv = {}
for name, scene_in in SC['adversarial']:
    s = R.compile_runtime_scene(LIB.hydrate(scene_in))
    st = R.create_runtime_state(s)
    adv[name] = {
        'scene': s,
        'accepted': s.get('accepted'),
        'issues': s.get('issues'),
        'summary': R.summary(s),
        'validate': R.validate_runtime_scene(s),
        'connectivity': R.room_connectivity_graph(s),
        'state': st,
        'select': R.select_runtime_object(st, s, 'anything'),
        'visibility': R.set_visibility(st, s, 'HIDE_OBJECT', 'anything'),
        'measure': R.create_measurement(s, 'OBJECT_WIDTH', target_id='anything'),
        'portal': R.set_portal_state(st, s, 'anything', 'OPEN'),
    }
out['__adversarial__'] = adv

out['__ops__'] = {
    'navigation_modes': list(R.NAVIGATION_MODES),
    'navigation_contracts': R.NAVIGATION_CONTRACTS,
    'visibility_modes': list(R.VISIBILITY_MODES),
    'measurement_types': list(R.MEASUREMENT_TYPES),
    'actions': list(R.INTERACTION_ACTIONS),
    'validation_codes': list(R.VALIDATION_CODES),
    'capsules': [R.validate_capsule(c) for c in (
        None, {}, {'radius_m': 0.3, 'height_m': 1.8, 'eye_height_m': 1.6},
        {'radius_m': 0, 'height_m': 1.8, 'eye_height_m': 1.6},
        {'radius_m': 0.3, 'height_m': 1.8, 'eye_height_m': 99},
        {'radius_m': 1e9, 'height_m': 1e9, 'eye_height_m': 1e9})],
    'navigation': [R.validate_navigation(m, None, None) for m in (
        None, '', 'WALK', 'walk', 'TELEPORT', 'FLY')],
    'actions_checked': [R.validate_runtime_action(a, t, 'x', p) for a, t, p in (
        ('SELECT', 'OBJECT', None), ('SELECT', 'OBJECT', {'set_geometry': 1}),
        ('INSPECT', 'OBJECT', {'writes_to_model': True}),
        ('MEASURE', 'OBJECT', None), ('FLY_AWAY', 'OBJECT', None),
        ('SELECT', 'GALAXY', None), (None, None, None))],
    'measurements_validated': [R.validate_measurement(m) for m in (
        None, 'x', {'type': 'AREA', 'runtime_only': True, 'distance_m': 1},
        {'type': 'OBJECT_WIDTH', 'runtime_only': False, 'distance_m': 1},
        {'type': 'OBJECT_WIDTH', 'runtime_only': True, 'distance_m': -1},
        {'type': 'OBJECT_WIDTH', 'runtime_only': True, 'distance_m': '3'},
        {'type': 'OBJECT_WIDTH', 'runtime_only': True, 'distance_m': 2.5})],
    'times': [R.advance_simulation_time(R.create_runtime_state(
        R.compile_runtime_scene(visual(SC['queries'][0]))), d)
        for d in (0.0, 1.0, -1.0, float('nan'), float('inf'), '5')],
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
print('python runtime parity written: %s (%d keys)' % (OUT, len(out)))
