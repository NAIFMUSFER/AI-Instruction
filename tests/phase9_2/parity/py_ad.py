# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 9.2 — طبقة التفصيل المعماري كاملة."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)

import acs_archdetail as A                                        # noqa: E402

OUT = os.environ.get('ACS_PARITY_AD_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_ad_py.json')

SURFACES = [
    [{'id': 'w1', 'role': 'exterior_wall'}, {'id': 'w2', 'role': 'exterior_wall'},
     {'id': 'p1', 'role': 'parapet'}],
    [{'id': 'w1', 'role': 'exterior_wall'}],
    [], None,
]
BOUNDS = [
    {'cx': 7, 'cy': 3, 'cz': 6.5, 'radius': 14, 'min_y': 0},
    {'cx': 20, 'cy': 15, 'cz': 12, 'radius': 60, 'min_y': 0},
    {}, None,
]
TEXTS = [
    'واجهة حجر طبيعي بيج مع لمسات رمادية وزجاج عاكس',
    'إنارة LED مخفية وبلكونات أكبر ومواقف أمامية وخلفية',
    'حديقة أمامية بها نخيل وشجيرات',
    'مطبخ L أو U حسب الدور',
    'دور إضافي مع كسوة خشب', 'nothing matches here', '', None,
]
out = {}
out['materials'] = {m: A.material(m) for m in sorted(A.MATERIALS)}
out['material_bad'] = [
    A.material('nope'),
    A.material('stone_beige', json.loads('{"__proto__": 1}')),
    A.material('stone_beige', {'roughness': 99}),
    A.material('stone_beige', {'base_color': 'beige'}),
    A.material('stone_beige', {'roughness': 0.41, 'base_color': '#D6C7AB'}),
    A.material('led_strip', {'emissive_intensity': 2.0}),
]
out['variation'] = [A.variation('h1', 'e%d' % i, 'stone_beige')
                    for i in range(6)] + [A.variation('h2', 'e0', 'wood_accent')]
out['profiles'] = [A.detail_profile(p, m) for p in
                   ('DETAIL_OFF', 'DETAIL_STANDARD', 'DETAIL_HIGH', 'NOPE')
                   for m in (False, True)]
out['classes'] = [A.classify_detail(k) for k in
                  ('CANONICAL_GEOMETRY', 'DERIVED_PRESENTATION_DETAIL',
                   'REQUESTED_PRESENTATION_DETAIL',
                   'DEFAULT_PRESENTATION_CONTEXT', 'UNRESOLVED', 'MADE_UP')]
out['authority'] = [A.object_authority(o, c) for o in
                    ({'canonical': True}, {'requested': True},
                     {'context': True}, {}, None)
                    for c in (False, True)]
out['zoning'] = [A.facade_zoning(s, r) for s in SURFACES for r in
                 ({'primary': 'stone_beige', 'accent': 'panel_gray'},
                  {'primary': 'stone_beige'}, {'accent': 'wood_accent'},
                  {'primary': 'granite'}, {}, None)]
out['windows'] = [A.window_assembly(o, f) for o in
                  ({'width': 1.4, 'height': 1.4, 'sill': 0.9, 'id': 'W1'},
                   {'width': 0.6, 'height': 0.5}, {'width': 4.0, 'height': 2.8},
                   {'width': 0, 'height': 1}, {}, None)
                  for f in (None, 'dark', 'gray', 'light', 'gold')]
out['doors'] = [A.door_visual(d) for d in
                ({'material': 'door'}, {'material': 'door_glass'},
                 {'material': 'dockdoor'}, {'kind': 'door', 'entrance': True},
                 {'material': 'mystery'}, {}, None)]
out['balconies'] = [A.balcony_visual(r, q) for r in (True, False)
                    for q in (True, False)]
out['leds'] = [A.led(k, h) for k in
               ('facade_strip', 'entrance_wash', 'disco_ball')
               for h in ({'represented': True, 'id': 'WALL|x'},
                         {'represented': False}, {}, None)]
out['staging'] = [A.staging_plan(m, req, can) for m in
                  ('STAGING_OFF', 'STAGING_REQUESTED_ONLY',
                   'STAGING_PRESENTATION_DEFAULT', 'STAGING_PARTY')
                  for req, can in
                  (([{'kind': 'sofa', 'id': 'o1'}], [{'kind': 'bed', 'id': 'o2'}]),
                   ([], []), (None, None))]
out['recipes'] = [A.object_recipe(k) for k in
                  ('car', 'suv', 'pickup', 'van', 'truck', 'delivery_truck',
                   'bus', 'forklift', 'reach_truck', 'pallet_jack',
                   'order_picker', 'stacker', 'tree', 'palm', 'shrub',
                   'hedge', 'planter', 'sofa', 'bed', 'wardrobe',
                   'warehouse_rack', 'pallet', 'carton', 'bollard',
                   'wheel_stop', 'traffic_cone', 'parking_bay', 'crane_proxy',
                   'dragon')]
out['recipes_dims'] = [
    A.object_recipe('car', dims=[2, 5, 1.5]),
    A.object_recipe('car', canonical_dims=[1.9, 4.6, 1.5], dims=[2, 5, 1.5]),
    A.object_recipe('car', dims=[2, 5, 0]),
    A.object_recipe('forklift', variant='REACH_TRUCK'),
    A.object_recipe('forklift', variant='HOVERBOARD'),
]
out['placements'] = [A.placement(o) for o in (
    {'canonical_pos': [1, 0, 2]}, {'user_pos': [3.5, 0, '4']},
    {'zone': {'x': 0, 'z': 0, 'w': 10, 'd': 5}, 'index': 2, 'of': 10},
    {'zone': {'x': 0, 'z': 0, 'w': 10}}, {'kind': 'car'}, {}, None)]
out['bays'] = [A.vehicles_to_bays(n, b) for n, b in
               ((10, [{'id': 'b%d' % i} for i in range(10)]),
                (10, [{'id': 'b%d' % i} for i in range(6)]),
                (0, []), (3, None), ('x', [{'id': 'b0'}]))]
out['parking'] = [A.parking(r, c) for r in (True, False)
                  for c in (8, 0, None)]
out['kitchens'] = [A.kitchen_layout(t, c) for t in (True, None)
                   for c in ('L', 'U', 'T', None)]
out['environments'] = [A.environment(e) for e in
                       ('NEUTRAL_STUDIO', 'CLEAR_SKY', 'OVERCAST_SKY',
                        'SUNSET_SKY', 'MARS_SKY')]
out['cameras'] = [A.camera(p, b) for p in
                  sorted(A.CAMERAS_ARCH) + ['EXTERIOR_HERO', 'NOPE']
                  for b in BOUNDS]
out['auto'] = [A.auto_presentation(m) for m in
               ({'type': 'warehouse'}, {'type': 'villa'}, {'type': 'clinic'},
                {'type': 'hotel'}, {'type': 'office'}, {'type': 'spaceship'},
                {'indoor': True}, {}, None)]
out['interpret'] = [A.interpret(t) for t in TEXTS]
_req = A.interpret(TEXTS[0])['intents'] + A.interpret(TEXTS[1])['intents']
_ms = [{'exterior_walls': 4, 'windows': 6, 'accent_band': 1, 'balcony': True,
        'parking_bays': 4, 'kitchen_layout': 'L',
        'objects': [{'kind': 'sofa', 'canonical': True},
                    {'kind': 'forklift', 'requested': True},
                    {'kind': 'tree', 'context': True}, {'kind': 'ghost'}],
        'context_enabled': True},
       {'exterior_walls': 0, 'windows': 0}, {}, None]
out['diagnostics'] = [A.diagnostic(_req, m) for m in _ms]
out['coverage'] = [A.coverage(d) for d in out['diagnostics']] + \
                  [A.coverage(None)]
out['configs'] = [
    A.config('DETAIL_HIGH', 'REQUESTED', 'SITE', 'STAGING_REQUESTED_ONLY',
             'EXTERIOR_HERO_FRONT', 'CLEAR_SKY', None, False, _req, _ms[0]),
    A.config('DETAIL_STANDARD', 'REALISTIC', 'LANDSCAPE',
             'STAGING_PRESENTATION_DEFAULT', 'WAREHOUSE_AISLE', 'SUNSET_SKY',
             None, True, [], {}),
    A.config(None, None, None, None, None, None, None, False, None, None),
    A.config('DETAIL_MEGA', None, None, None, None, None, None, False,
             None, None),
    A.config('DETAIL_OFF', 'CARTOON', None, None, None, None, None, False,
             None, None),
    A.config('DETAIL_OFF', None, 'MOON', None, None, None, None, False,
             None, None),
]
_cfg = out['configs'][0]['config']
import acs_pbr as P                                               # noqa: E402
_pbr = P.config('HIGH', 'CLEAR_NOON', 'REALISTIC', 'SKY', 1.1, None,
                None, BOUNDS[0])['config']
out['captures'] = [
    A.capture_metadata(_pbr, _cfg, 'hash_abc', 7, 1920, 1080, None),
    A.capture_metadata(_pbr, None, 'hash_abc', None, 800, 600, None),
    A.capture_metadata(None, _cfg, 'h', 1, 320, 240, None),
]
out['spec_view'] = {'schema': A.SCHEMA, 'version': A.VERSION,
                    'materials': sorted(A.MATERIALS),
                    'cameras': sorted(A.CAMERAS_ARCH),
                    'classes': sorted(A.DETAIL_CLASSES)}

with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, sort_keys=True)
print('parity written: %s groups' % len(out))
