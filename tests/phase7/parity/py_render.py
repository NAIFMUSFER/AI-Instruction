# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 7.

يبني نفس مخرجات العرض على نفس النماذج ويكتب النتيجة القانونية إلى JSON يقارنه
compare.js. لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس.
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

import acs_render as R                                            # noqa: E402
import acs_visual as VIS                                          # noqa: E402
import acs_arch as ARCH                                           # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_render_fixtures as LIB                                 # noqa: E402

OUT = os.environ.get('ACS_PARITY_RENDER_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_render_py.json')
AT = '2026-01-01T00:00:00Z'

ALL = LIB.all_models()
MODEL_KEYS = sorted(ALL.keys())
CAMS = ['FRONT_EXTERIOR', 'FRONT_CORNER', 'BIRDS_EYE', 'DOLLHOUSE', 'TOP',
        'STREET_VIEW', 'REAR_CORNER']
BUF_W, BUF_H = 96, 64

out = {}
for key in MODEL_KEYS:
    model = copy.deepcopy(ALL[key])
    before = json.dumps(model, sort_keys=True)
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    scene = VIS.compile_visual_scene(copy.deepcopy(model), 'bld_0', None, 0,
                                     {'mode': 'PRESENTATION'})
    arch = ARCH.compile_architecture(copy.deepcopy(model), 'bld_0', None, 0)

    entry = {'model_hash': project['model_hash']}
    entry['requests'] = {
        vt: R.render_request(project, vt, {'theme': 'LUXURY',
                                           'lighting': 'GOLDEN_HOUR',
                                           'quality': 'HIGH'},
                             'rreq_fixed')
        for vt in list(R.VIEW_TYPES) + ['NOT_A_VIEW']}
    entry['cameras'] = {c: R.camera_for(scene, c) for c in CAMS}
    entry['materials'] = {t: R.assign_materials(scene, t) for t in R.THEMES}
    entry['lighting'] = {p: R.lighting(p) for p in R.LIGHTING_PRESETS}
    entry['lighting_oriented'] = R.lighting('DAY', 30.0)
    entry['quality'] = {q: R.quality_profile(q, c)
                        for q in R.QUALITIES for c in (False,)}
    entry['quality_constrained'] = R.quality_profile('ULTRA', True)
    entry['environment'] = {q: R.environment(q, False) for q in R.QUALITIES}
    entry['transforms'] = {
        'ROOF_HIDE': R.visual_transform(scene, 'ROOF_HIDE'),
        'WALL_CLIP': R.visual_transform(scene, 'WALL_CLIP', {'height_m': 1.4}),
        'LEVEL_ISOLATION': R.visual_transform(scene, 'LEVEL_ISOLATION',
                                              {'level_index': 0}),
        'CLIP_PLANE': R.visual_transform(scene, 'CLIP_PLANE',
                                         {'axis': 'x', 'offset_m': 5.0}),
        'LEVEL_EXPLODE': R.visual_transform(scene, 'LEVEL_EXPLODE', {'gap_m': 4.0}),
        'BAD': R.visual_transform(scene, 'NOT_A_TRANSFORM'),
    }
    entry['plans'] = {str(lv): R.plan_drawing(scene, arch, lv, st)
                      for lv in (0, 1) for st in ('CLEAN',)}
    entry['plan_styles'] = {st: R.plan_drawing(scene, arch, 0, st)['drawing']
                            for st in R.SPEC['plan_styles']}
    entry['elevations'] = {f: R.elevation_drawing(scene, f)
                           for f in R.SPEC['elevation_faces']}
    entry['sections'] = {a: R.section_drawing(scene, a) for a in R.SPEC['section_axes']}
    entry['plan_svg'] = R.plan_svg(R.plan_drawing(scene, arch, 0, 'CLEAN')['drawing'])
    entry['elevation_svg'] = R.elevation_svg(
        R.elevation_drawing(scene, 'NORTH')['drawing'])
    entry['section_svg'] = R.section_svg(R.section_drawing(scene, 'x')['drawing'])
    entry['separate'] = R.separate_visual(scene)

    cam = R.camera_for(scene, 'FRONT_EXTERIOR')['camera']
    bufs = R.control_buffers(scene, cam, BUF_W, BUF_H)
    entry['buffers'] = bufs
    if bufs['valid']:
        entry['features'] = R.geometry_features(bufs['buffers'])
        entry['png_len'] = {k: len(R.buffer_png(bufs['buffers'], k) or b'')
                            for k in R.BUFFER_KINDS}
        entry['png_sha'] = {k: R._sha16(list(R.buffer_png(bufs['buffers'], k) or b''))
                            for k in R.BUFFER_KINDS}
        entry['self_drift'] = R.detect_drift(entry['features']['features'],
                                             entry['features']['features'])

    req = R.render_request(project, 'EXTERIOR', {'theme': 'MODERN'}, 'rreq_fixed')
    entry['descriptor'] = R.render_descriptor(req['request'], cam,
                                              'DETERMINISTIC_RENDER',
                                              {'created_at': AT})
    entry['staleness_current'] = R.staleness(entry['descriptor'], project)
    entry['variant'] = R.variant(req['request'], 'Luxury', {'floor': 'r_marble_white'})
    entry['gallery'] = R.gallery([entry['descriptor']], project)

    if json.dumps(model, sort_keys=True) != before:
        raise SystemExit('a render operation mutated the model: ' + key)
    if project['model_hash'] != entry['model_hash']:
        raise SystemExit('the project hash changed during rendering: ' + key)
    out[key] = entry

# ---- المواد والتجاوز
out['__materials__'] = {
    'library': R.material_library(),
    'lookup': {m: R.material(m) for m in sorted(list(R.MATERIALS.keys()) + ['nope'])},
    'override_ok': R.visual_override({}, 'SPACE', 'g.majlis', 'r_wood_oak'),
    'override_spec': R.visual_override({}, 'SPACE', 'g.majlis', 'r_wood_oak',
                                       'PROJECT_SPECIFICATION'),
    'override_bad_scope': R.visual_override({}, 'NOPE', 'x', 'r_wood_oak'),
    'override_bad_mat': R.visual_override({}, 'SPACE', 'x', 'not_a_material'),
    'override_markup': R.visual_override({}, 'SPACE', '<script>x</script>',
                                         'r_wood_oak'),
}

# ---- الكاميرا الداخلية على فراغ حقيقي وآخر ضيّق
_scene = VIS.compile_visual_scene(copy.deepcopy(ALL['villa_glazed']), 'bld_0', None, 0,
                                  {'mode': 'PRESENTATION'})
out['__interior__'] = {
    'majlis': R.camera_for(_scene, 'INTERIOR_WIDE', 'bld_0.g.majlis'),
    'eye': R.camera_for(_scene, 'INTERIOR_EYE_LEVEL', 'bld_0.g.majlis'),
    'missing': R.camera_for(_scene, 'INTERIOR_WIDE', 'no.such.space'),
    'bad_preset': R.camera_for(_scene, 'NOT_A_PRESET'),
}

# ---- حدود الذكاء الاصطناعي
_proj = AU.create_project(copy.deepcopy(ALL['villa_glazed']), 'bld_0', 'IMPORT', None)
_req = R.render_request(_proj, 'EXTERIOR', {'theme': 'MODERN',
                                            'ai_enhancement': True},
                        'rreq_fixed')['request']
_cam = R.camera_for(_scene, 'FRONT_EXTERIOR')['camera']
_bufs = R.control_buffers(_scene, _cam, BUF_W, BUF_H, None,
                          _proj['model_hash'])['buffers']
_desc = R.render_descriptor(_req, _cam, 'DETERMINISTIC_RENDER', {'created_at': AT})
_contract = R.ai_prompt_contract(_req, {'style': 'warm', 'mood': '<script>x</script>'},
                                 [{'reference_id': 'ref_1', 'kind': 'STYLE',
                                   'scope': 'PROJECT',
                                   'uri': 'https://example.invalid/a.png',
                                   'caption': 'ok'},
                                  {'reference_id': 'ref_bad', 'kind': 'STYLE',
                                   'scope': 'PROJECT',
                                   'uri': 'javascript:alert(1)', 'caption': 'x'}])
out['__ai__'] = {
    'contract': _contract,
    'request': R.ai_request(_req, _desc, _bufs, _contract, 'provider_x'),
    'request_no_buffers': R.ai_request(_req, _desc, None, _contract),
    'request_no_base': R.ai_request(_req, None, _bufs, _contract),
    'adapter_off': R.provider_adapter('provider_x', False),
    'adapter_on': R.provider_adapter('provider_x', True, 30),
    'enhance_unavailable': R.ai_enhance(R.provider_adapter('provider_x', False),
                                        {'base_render_id': _desc['render_id']}, None),
    'enhance_ok': R.ai_enhance(
        R.provider_adapter('provider_x', True),
        R.ai_request(_req, _desc, _bufs, _contract, 'provider_x')['request'],
        {'provider_model': 'model_y', 'generated_at': AT, 'image_ref': 'img_1'}),
}

# ---- كشف الانحراف على حالات مُصطنعة
_ref = R.geometry_features(_bufs)['features']


def _mut(f, fn):
    g = copy.deepcopy(f)
    fn(g)
    return g


out['__drift__'] = {
    'identical': R.detect_drift(_ref, copy.deepcopy(_ref)),
    'window_added': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g['openings'].append({'cx': 5, 'cy': 5, 'w': 4, 'h': 4, 'px': 16}),
        g.__setitem__('opening_count', g['opening_count'] + 1)))),
    'window_removed': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g['openings'].pop(),
        g.__setitem__('opening_count', g['opening_count'] - 1)))),
    'door_moved': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g['openings'][0].__setitem__('cx', g['openings'][0]['cx'] + 40)))),
    'floor_drift': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g.__setitem__('floor_band_count', g['floor_band_count'] + 1)))),
    'footprint_drift': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g['footprint'].__setitem__('area_px',
                                   int(g['footprint']['area_px'] * 0.5))))),
    'wall_drift': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g.__setitem__('wall_px', int(g['wall_px'] * 0.4))))),
    'roof_drift': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g.__setitem__('roof_line', [(-1 if v < 0 else v + 30)
                                    for v in g['roof_line']])))),
    'semantic_missing': R.detect_drift(_ref, copy.deepcopy(_ref),
                                       ['bld_0.requested.car_1']),
    'wrong_camera': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g.__setitem__('camera_id', 'cam_other')))),
    'wrong_model': R.detect_drift(_ref, _mut(_ref, lambda g: (
        g.__setitem__('model_hash', 'other')))),
    'missing': R.detect_drift(None, None),
}

out['__alignment__'] = {
    'same': R.buffers_aligned(_bufs, _bufs),
    'other_size': R.buffers_aligned(_bufs, R.control_buffers(
        _scene, _cam, 48, 32)['buffers']),
    'none': R.buffers_aligned(None, _bufs),
}

out['__unsafe__'] = {
    ('%d' % i): R.is_unsafe(v) for i, v in enumerate([
        'ok', 'javascript:alert(1)', '<script>x</script>', '<img onerror=x>',
        'data:text/html,x', 'vbscript:x', '<!DOCTYPE x', 'eval(1)', '', None, 5])}

out['__context__'] = {
    'default': R.render_request(_proj, 'EXTERIOR', {}, 'rreq_fixed')['request'
                                                                    ]['context_flags'],
    'industrial': R.render_request(_proj, 'EXTERIOR',
                                   {'context_flags': ['industrial_equipment']},
                                   'rreq_fixed')['request']['context_flags'],
    'bogus': R.render_request(_proj, 'EXTERIOR', {'context_flags': ['not_a_flag']},
                              'rreq_fixed')['request']['context_flags'],
}

out['__spec__'] = {'schema': R.SCHEMA, 'version': R.SPEC['version']}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
print('python render parity written: %s (%d keys)' % (OUT, len(out)))
