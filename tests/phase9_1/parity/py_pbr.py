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
out['spec_view'] = {'schema': P.SPEC['schema'],
                    'chain': P.SPEC['quality_fallback_chain'],
                    'auto_max': P.SPEC['auto_max_profile'],
                    'provenance': P.SPEC['provenance_classes'],
                    'tone': P.SPEC['tone_mapping'],
                    'limits': P.SPEC['limits']}

with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, sort_keys=True)
print('parity written: %d groups' % len(out))
