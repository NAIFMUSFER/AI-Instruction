# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 9.1 — الطبقة الحتمية كاملة."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)

import acs_pbr as P                                               # noqa: E402

OUT = os.environ.get('ACS_PARITY_PBR_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_pbr_py.json')

CAPS = [
    {'webgl2': True, 'max_texture_size': 16384, 'device_pixel_ratio': 2},
    {'webgl2': True, 'max_texture_size': 8192, 'device_pixel_ratio': 3},
    {'webgl2': True, 'max_texture_size': 4096, 'device_pixel_ratio': 1.5},
    {'webgl2': False, 'max_texture_size': 2048, 'device_pixel_ratio': 1},
    {}, None,
]
BOUNDS = [
    {'cx': 7, 'cy': 3, 'cz': 6.5, 'radius': 12, 'min_y': 0},
    {'cx': 20, 'cy': 15, 'cz': 12, 'radius': 60, 'min_y': 0},
    {'cx': 0, 'cy': 0, 'cz': 0, 'radius': 0}, {}, None,
]
out = {}
out['materials'] = {m: P.material(m) for m in sorted(P.MATERIALS)}
out['material_bad'] = [P.material('nope'),
                       P.material('plaster', {'__proto__': 1}),
                       P.material('plaster', {'roughness': 99}),
                       P.material('plaster', {'base_color': 'red'}),
                       P.material('plaster', {'roughness': 0.31,
                                              'base_color': '#A1B2C3'}),
                       P.material('glass_clear', {'transmission': 0.9})]
out['map'] = {n: P.material_for_engineering(n) for n in
              sorted(list(P.MAT_MAP) + ['robot', 'skin', 'nope'])}
out['lighting'] = {k: P.lighting(k) for k in sorted(P.LIGHTING)}
out['lighting_bad'] = P.lighting('DISCO')
out['exposure'] = [P.exposure_clamp(v) for v in
                   [0.1, 0.5, 1.0, 1.8, 9.0, -1, None, 'x']]
out['shadows'] = [P.shadow_config(t, b) for t in
                  ('LOW', 'MEDIUM', 'HIGH', 'ULTRA', 'NOPE')
                  for b in BOUNDS]
out['quality'] = [P.quality(pr, c) for pr in
                  ('PERFORMANCE', 'BALANCED', 'HIGH', 'ULTRA', 'NOPE')
                  for c in CAPS]
out['auto'] = [P.auto_profile(c) for c in CAPS]
out['cameras'] = [P.camera(pr, b) for pr in sorted(P.CAMERAS)
                  for b in BOUNDS] + [P.camera('NOPE', BOUNDS[0])]
out['environments'] = [P.environment(m) for m in
                       ('NEUTRAL', 'SKY', 'STUDIO', 'HDRI_URL')]
out['textures'] = [[x, P.texture_path_ok(x)] for x in
                   ['https://cdn.evil/x.png', '//evil/x.png', '../x.png',
                    'assets/materials/../../.env', '/etc/passwd',
                    'assets/materials/brick.png', 'assets/materials/x.svg',
                    'assets/materials/' + 'a' * 200 + '.png',
                    'javascript:alert(1)', '', 'assets/other/x.png']]
out['configs'] = [P.config('HIGH', 'GOLDEN_HOUR', 'REALISTIC', 'SKY', 1.2,
                           {'plaster': {'roughness': 0.5},
                            'glass_clear': {'transmission': 0.9}},
                           CAPS[0], BOUNDS[0]),
                  P.config('ULTRA', 'INTERIOR_NIGHT', 'ENGINEERING', None,
                           None, None, CAPS[3], BOUNDS[1]),
                  P.config('BALANCED', 'WAREHOUSE', 'REALISTIC', 'NEUTRAL',
                           0.9, {'nope': {'roughness': 1}}, None, None),
                  P.config('NOPE', None, None, None, None, None, None, None),
                  P.config(None, None, 'CARTOON', None, None, None, None,
                           None)]
out['captures'] = [P.capture_metadata(
    (out['configs'][0]['config'] if out['configs'][0]['valid'] else None),
    'hash_abc', w, h, None) for (w, h) in
    [(1280, 720), (1920, 1080), (2560, 1440), (99999, 10), (0, 0),
     (None, None)]]
SKY = {'name': 'SKY_DOME', 'is_mesh': True, 'parent_names': [],
       'box': {'min': [-22500, -22500, -22500],
               'max': [22500, 22500, 22500]}}
UNNAMED_SKY = {'name': '', 'is_mesh': True, 'parent_names': [],
               'box': SKY['box']}
WALL = {'name': 'WALL|F0|r1|s0', 'is_mesh': True,
        'parent_names': ['BUILDING'],
        'box': {'min': [0, 0, 0], 'max': [12, 3, 9]}}
TAGGED = {'name': 'FLOOR|F0|r1|plate', 'is_mesh': True, 'parent_names': [],
          'box': {'min': [-2, -0.1, -2], 'max': [14, 0.1, 11]}}
CTX = {'name': 'AD_CONTEXT_PLANE0', 'is_mesh': True,
       'parent_names': ['AD_CONTEXT'],
       'user_data': {'visual_only': True},
       'box': {'min': [-200, -1, -200], 'max': [200, -0.9, 200]}}
DBG = {'name': 'COORD_DEBUG_MARKER', 'is_mesh': True, 'parent_names': [],
       'user_data': {'acs_debug_only': True},
       'box': {'min': [0, 0, 0], 'max': [1, 1, 1]}}
NOTMESH = {'name': 'PLAYER', 'is_mesh': False, 'parent_names': []}
OBJS = [SKY, UNNAMED_SKY, WALL, TAGGED, CTX, DBG, NOTMESH]
out['bounds_member'] = [P.bounds_member(o) for o in OBJS] \
    + [P.bounds_member({}), P.bounds_member(None)]
out['bounds_sets'] = [P.bounds_from_descriptors(x) for x in
                      (OBJS, [WALL], [SKY, CTX], [], None,
                       [dict(WALL, box={'min': ['a', 0, 0],
                                        'max': [1, 1, 1]})])]
out['camera_clip'] = [P.camera_clip(b, pos) for b in
                      ({'cx': 6, 'cy': 1.5, 'cz': 4.5, 'radius': 7.5},
                       {'cx': 0, 'cy': 0, 'cz': 0, 'radius': 0}, {}, None)
                      for pos in ([0, 20000, 54000], [6, 20, 30],
                                  [6, 1.5, 4.5], None)]
out['frustum'] = [P.frustum_contains(c, b) for c in
                  ({'position': [0, 20000, 54000], 'target': [6, 1.5, 4.5],
                    'fov': 45, 'aspect': 1.6, 'near': 0.05, 'far': 6000},
                   {'position': [30, 20, 30], 'target': [6, 1.5, 4.5],
                    'fov': 45, 'aspect': 1.6, 'near': 0.1, 'far': 500},
                   {'position': [6, 1.5, 4.5], 'target': [60, 1.5, 4.5],
                    'fov': 60, 'aspect': 1.6, 'near': 0.05, 'far': 500},
                   {}, None)
                  for b in ({'cx': 6, 'cy': 1.5, 'cz': 4.5, 'radius': 7.5},
                            {}, None)]
out['material_safe'] = [P.material_safe(P.material(m)['material'])
                        for m in sorted(P.MATERIALS)] \
    + [P.material_safe(x) for x in
       ({'id': 'a', 'base_color': '#ffffff', 'opacity': 0.0},
        {'id': 'b', 'base_color': 'red'},
        {'id': 'c', 'base_color': '#ffffff', 'metalness': 9},
        {'id': 'd', 'base_color': '#ffffff', 'roughness': None},
        {}, None)]
ROOMS_A = [[2, 2, 8, 6], [12, 2, 6, 6]]
SITE_A = [0, 0, 40, 30]
ROOM_A = [10.0, 6.0, 20.0, 12.0]
out['level_base_y'] = [P.level_base_y(i, fh) for i in (0, 1, 2, 5, -1)
                       for fh in (3.2, 0, None, float('nan'))]
out['plate_rect'] = [P.plate_rect(r, s2) for r in
                     (ROOMS_A, [], [[0, 0, 0, 0]], None)
                     for s2 in (SITE_A, None)]
out['rack_block'] = [P.rack_block(rr, rk) for rr in (ROOM_A, None)
                     for rk in ({'x': 5, 'z': 0}, {'x': 0, 'z': 4},
                                {'x': 15, 'w': 99}, {'x': 25}, {}, None)]
out['containment'] = [P.containment(c, h, t) for c in
                      ({'min': [12, 0, 8], 'max': [14, 2, 10]},
                       {'min': [29, 0, 17], 'max': [33, 2, 20]},
                       {'min': [40, 0, 8], 'max': [42, 2, 10]}, None)
                      for h in ({'min': [10, 0, 6], 'max': [30, 3, 18]},
                                None)
                      for t in (None, 0.5)]
out['roof_alignment'] = [P.roof_alignment(t, 3.2, y) for t in (0, 1, 2, 5)
                         for y in (3.2, 6.4, 9.6, 12.8, None)]
out['resolve_transform'] = [P.resolve_transform(d) for d in (
    {'coordinate_space': 'HOST_LOCAL', 'local': [1, 0, 2],
     'host_origin': [10, 0, 6], 'level_index': 2, 'floor_height': 3.2,
     'host_id': 'r1', 'level_id': 'F2', 'source_element_id': 'FURN|F2|r1|0'},
    {'coordinate_space': 'HOST_LOCAL', 'local': [1, 0, 2],
     'host_origin': [10, 6.4, 6], 'host_origin_includes_level': True,
     'level_index': 2, 'floor_height': 3.2},
    {'coordinate_space': 'SITE', 'local': [1, 0, 2]},
    {'coordinate_space': 'HOST_LOCAL', 'local': [1, 0, 1]},
    {'coordinate_space': 'NOWHERE', 'local': [1, 0, 1]},
    {'coordinate_space': 'SITE'},
    {'coordinate_space': 'SITE', 'local': [1, float('inf'), 1]},
    {}, None)]
out['spec_view'] = {'schema': P.SPEC['schema'],
                    'chain': P.SPEC['quality_fallback_chain'],
                    'auto_max': P.SPEC['auto_max_profile'],
                    'provenance': P.SPEC['provenance_classes'],
                    'tone': P.SPEC['tone_mapping'],
                    'limits': P.SPEC['limits']}

# ── تكافؤ عقد استرداد العرض (render-recovery/1.0.0) ─────────────────────────
_RR_BOXES = [
    {"min": [0, 0, 0], "max": [1, 3, 6]},
    {"min": [0, 0, 0], "max": [400, 18, 300]},
    {"min": [99999.0, 0, 0], "max": [99999.2, 0.2, 0.2]},
    {"min": [0, 0, 0], "max": [99999.0, 1, 1]},
    {"min": [5, 5, 5], "max": [1, 1, 1]},
    {"min": [0, 0, 0], "max": [0, 0, 0]},
    None,
]
out['element_valid'] = [P.element_valid({"box": b} if b else {})
                        for b in _RR_BOXES] + [P.element_valid(None)]
_RR_SETS = [
    [{"is_mesh": True, "parent_names": ["BUILDING"], "name": "WALL|F0|a",
      "box": {"min": [0, 0, 0], "max": [10, 3, 8]}}],
    [{"is_mesh": True, "parent_names": ["BUILDING"], "name": "WALL|F0|a",
      "box": {"min": [0, 0, 0], "max": [10, 3, 8]}},
     {"is_mesh": True, "parent_names": ["BUILDING"], "name": "ELEC|F0|p",
      "box": {"min": [99999, 0, 0], "max": [99999.2, 0.2, 0.2]}}],
    [{"is_mesh": True, "parent_names": ["BUILDING"], "name": "WALL|F0|a",
      "box": {"min": [0, 0, 0], "max": [1, 1, 1]}}] * 8
    + [{"is_mesh": True, "parent_names": ["BUILDING"], "name": "WALL|F0|big",
        "box": {"min": [0, 0, 0], "max": [400, 10, 10]}}],
    [{"is_mesh": True, "name": "SKY_DOME", "parent_names": [],
      "box": {"min": [-45000, -45000, -45000], "max": [45000, 45000, 45000]}}],
    [],
]
out['robust_bounds'] = [P.robust_bounds(s) for s in _RR_SETS]
out['fit_distance'] = [P.fit_distance(r, f, a)
                       for r in (0.5, 20, 84, 1902, 46000, None)
                       for f in (40, 52, 75)
                       for a in (0.6, 1.6, 3.2)]
out['camera_fit'] = [P.camera_fit({"cx": 0, "cy": 0, "cz": 0, "radius": r}, f, a)
                     for r in (15, 84, 500, 1902, 20000)
                     for f in (42, 52)
                     for a in (0.6, 1.6)] \
    + [P.camera_fit({"radius": 0}, 52, 1.6), P.camera_fit(None, 52, 1.6)]
out['recovery_plan'] = [P.recovery_plan(s) for s in (
    {"canonical_meshes": 1500, "draw_calls": 212, "viewport_black": True,
     "composer_active": True, "materials_replaced": True},
    {"canonical_meshes": 1500, "draw_calls": 212, "viewport_black": True,
     "composer_active": False, "materials_replaced": False},
    {"canonical_meshes": 0, "draw_calls": 0, "viewport_black": True},
    {"canonical_meshes": 10, "draw_calls": 0, "viewport_black": True},
    {"canonical_meshes": 10, "draw_calls": 5, "viewport_black": False},
    {}, None)]

with open(OUT, 'w', encoding='utf-8') as fh:



    json.dump(out, fh, ensure_ascii=False, sort_keys=True)
print('parity written: %d groups' % len(out))
