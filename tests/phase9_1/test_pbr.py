# -*- coding: utf-8 -*-
"""المرحلة 9.1 — عقد الجودة البصرية: خامات PBR، إضاءة، ظلال، جودة، كاميرا،
حصانة النموذج، وأمن الأصول."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'phase9'))

import acs_pbr as P                                               # noqa: E402
import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_docs_fixtures as LIB                                   # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


ALL = LIB.all_models()
CANON = json.load(open(os.path.join(ROOT, 'acs_pbr.json'), encoding='utf-8'))

print('\n== §30 — THE ARROW THAT NEVER REVERSES ==')
chk('the layer is presentation only',
    P.SPEC['presentation_only'] is True and P.SPEC['writes_to_model'] is False
    and P.SPEC['reverse_write_allowed'] is False)
chk('the pipeline ends at the screen and no reverse arrow exists',
    P.SPEC['pipeline'][0] == 'CANONICAL_ENGINEERING_MODEL'
    and P.SPEC['pipeline'][-1] == 'SCREEN_OR_IMAGE_OUTPUT'
    and P.SPEC['reverse_arrow_exists'] is False)
chk('model hash inputs are the model alone; config hash is separate',
    P.SPEC['model_hash_inputs'] == ['model']
    and P.SPEC['presentation_config_hash_inputs'] == ['config'])
chk('no photorealism, path-tracing or offline-render claim is made',
    P.SPEC['photorealism_claimed'] is False
    and P.SPEC['path_tracing_claimed'] is False
    and P.SPEC['offline_render_claimed'] is False)

print('\n== §3 — THE PBR MATERIAL SYSTEM ==')
chk('exactly twenty presentation materials are declared',
    len(P.MATERIALS) == 20 and P.SPEC['material_count'] == 20)
REQUIRED_IDS = ['plaster', 'painted_wall', 'concrete_exposed',
                'concrete_polished', 'ceramic_tile', 'stone', 'wood',
                'steel_structural', 'steel_painted', 'aluminum', 'glass_clear',
                'glass_tinted', 'roof_membrane', 'asphalt', 'soil', 'fabric',
                'plastic', 'rack_steel', 'carton', 'safety_paint']
for mid in REQUIRED_IDS:
    chk('material %s is declared and resolves' % mid,
        P.material(mid)['valid'])
for mid in REQUIRED_IDS:
    m = P.material(mid)['material']
    chk('material %s carries roughness, metalness and world texture scale' % mid,
        isinstance(m['roughness'], float) and isinstance(m['metalness'], float)
        and m['texture_scale_m'] > 0)
chk('every material is visual-only with no engineering authority',
    all(P.material(mid)['material']['engineering_authority'] is False
        and P.material(mid)['material']['visual_only'] is True
        for mid in REQUIRED_IDS))
chk('no material carries a fire rating, structural grade or U-value',
    not any(k in m for mid in REQUIRED_IDS
            for m in [P.MATERIALS[mid]]
            for k in ('fire_rating', 'structural_grade', 'u_value')))
chk('an unknown material is refused',
    P.material('gold_leaf')['issues'][0]['code'] == 'PQ_INVALID_MATERIAL')

print('\n== §3 — PROVENANCE: DEFAULTS, OVERRIDES AND THE LINE NOT CROSSED ==')
m = P.material('plaster')['material']
chk('an untouched field is PRESENTATION_DEFAULT',
    all(v == 'PRESENTATION_DEFAULT' for v in m['provenance'].values()))
m2 = P.material('plaster', {'roughness': 0.3})['material']
chk('an overridden field is USER_VISUAL_OVERRIDE and only that field',
    m2['provenance']['roughness'] == 'USER_VISUAL_OVERRIDE'
    and m2['provenance']['metalness'] == 'PRESENTATION_DEFAULT'
    and m2['roughness'] == 0.3)
chk('ENGINEERING_VALUE never originates in this layer',
    'ENGINEERING_VALUE' in P.SPEC['provenance_classes']
    and not any(v == 'ENGINEERING_VALUE'
                for v in m2['provenance'].values()))
chk('a prototype key in an override is refused, not stored',
    any(i['code'] == 'PQ_PROPERTY_REFUSED'
        for i in P.material('plaster', {'__proto__': 1})['issues']))
chk('a non-overridable field is refused',
    any(i['code'] == 'PQ_INVALID_OVERRIDE'
        for i in P.material('plaster', {'three_material': 'basic'})['issues']))

print('\n== §5 — GLASS ==')
g = P.material('glass_clear')['material']
chk('clear glass is a physical material with transmission and IOR',
    g['three_material'] == 'physical' and g['transmission'] == 0.85
    and g['ior'] == 1.52 and g['thickness_m'] == 0.01)
chk('glass stays transparent enough to inspect interiors',
    g['opacity'] is not None and g['opacity'] <= 0.5
    and g['roughness'] <= 0.1)
chk('tinted glass is separately declared',
    P.material('glass_tinted')['material']['transmission'] == 0.6)
chk('the window mesh class maps to clear glass; geometry is untouched',
    P.material_for_engineering('window')['material_id'] == 'glass_clear')

print('\n== §3 — ENGINEERING MAP AND THE UNMAPPED POLICY ==')
for name, want in (('wall', 'painted_wall'), ('floor', 'ceramic_tile'),
                   ('door', 'wood'), ('frame', 'rack_steel'),
                   ('goods', 'carton'), ('guard', 'safety_paint'),
                   ('deck', 'steel_painted'), ('ac', 'aluminum')):
    chk('mesh class %s maps to %s' % (name, want),
        P.material_for_engineering(name)['material_id'] == want)
chk('an unmapped class keeps its engineering appearance',
    P.material_for_engineering('robot')['policy']
    == 'KEEP_ENGINEERING_APPEARANCE')
chk('warehouse rack, carton and safety paint are first-class materials',
    all(x in P.MATERIALS for x in ('rack_steel', 'carton', 'safety_paint')))

print('\n== §6 — LIGHTING PRESETS ==')
for preset in ('STUDIO_DAY', 'CLEAR_NOON', 'GOLDEN_HOUR', 'OVERCAST',
               'INTERIOR_DAY', 'INTERIOR_NIGHT', 'WAREHOUSE',
               'PRESENTATION_SOFT'):
    r = P.lighting(preset)
    chk('preset %s resolves' % preset, r['valid'])
    chk('preset %s reuses no MEP fixture and its fills are visual-only'
        % preset,
        r['lighting']['mep_fixture_reused'] is False
        and all(fl['visual_only'] for fl in r['lighting']['fills']))
chk('an unknown preset is refused',
    P.lighting('DISCO')['issues'][0]['code'] == 'PQ_INVALID_PRESET')
chk('golden hour is a warm low sun',
    P.lighting('GOLDEN_HOUR')['lighting']['sun_elevation_deg'] < 20)
chk('interior night turns the sun off rather than faking one',
    P.lighting('INTERIOR_NIGHT')['lighting']['sun_intensity'] == 0.0)
chk('exposure is clamped into the declared range',
    P.exposure_clamp(9.0)['value'] == P.SPEC['exposure_max']
    and P.exposure_clamp(0.1)['value'] == P.SPEC['exposure_min']
    and P.exposure_clamp(float('nan'))['value'] is None)

print('\n== §8 — SHADOWS FROM REAL BOUNDS, NOT A HARD-CODED BUILDING ==')
small = P.shadow_config('HIGH', {'radius': 8})['shadow']
big = P.shadow_config('HIGH', {'radius': 80})['shadow']
chk('the shadow camera scales with the model bounds',
    big['camera']['right'] == 10 * small['camera']['right']
    and small['hardcoded_size'] is False)
chk('all four tiers are declared with bias and normal bias',
    all(P.shadow_config(t, {'radius': 10})['valid']
        for t in ('LOW', 'MEDIUM', 'HIGH', 'ULTRA')))
chk('tier resolution increases monotonically',
    P.SHADOWS['LOW']['map_size'] < P.SHADOWS['MEDIUM']['map_size']
    < P.SHADOWS['HIGH']['map_size'] < P.SHADOWS['ULTRA']['map_size'])
chk('soft PCF shadows are the declared type',
    P.SPEC['shadow_type'] == 'PCF_SOFT')

print('\n== §17/§18 — QUALITY PROFILES AND GRACEFUL DEGRADATION ==')
strong = {'webgl2': True, 'max_texture_size': 16384, 'device_pixel_ratio': 2}
weak = {'webgl2': False, 'max_texture_size': 2048, 'device_pixel_ratio': 1}
chk('ULTRA on a strong GPU stays ULTRA',
    P.quality('ULTRA', strong)['quality']['effective'] == 'ULTRA')
q = P.quality('ULTRA', weak)
chk('ULTRA on a weak device degrades down the declared chain',
    q['quality']['effective'] == 'PERFORMANCE'
    and q['quality']['degraded'] is True)
chk('every degradation step is reported, never silent',
    len([i for i in q['issues'] if i['code'] == 'PQ_FALLBACK_APPLIED']) == 3)
chk('ULTRA is never selected automatically',
    P.auto_profile(strong)['profile'] == 'HIGH'
    and P.auto_profile(strong)['ultra_auto_selected'] is False)
chk('a phone-class device auto-selects a runnable profile',
    P.auto_profile(weak)['profile'] == 'PERFORMANCE')
chk('a blank viewport is never an allowed outcome',
    P.quality('HIGH', weak)['quality']['blank_viewport_allowed'] is False)
chk('PERFORMANCE caps pixel ratio at one and disables SSAO',
    P.QUALITY['PERFORMANCE']['pixel_ratio_max'] == 1.0
    and P.QUALITY['PERFORMANCE']['ssao'] is False)
chk('an unknown profile is refused',
    P.quality('CINEMATIC')['issues'][0]['code'] == 'PQ_INVALID_PROFILE')

print('\n== §13 — CAMERA PRESETS FROM MODEL BOUNDS ==')
b = {'cx': 7, 'cy': 3, 'cz': 6.5, 'radius': 12, 'min_y': 0}
for preset in ('EXTERIOR_HERO', 'EXTERIOR_CORNER', 'EYE_LEVEL', 'AERIAL',
               'INTERIOR_WIDE', 'INTERIOR_EYE_LEVEL', 'WAREHOUSE_OVERVIEW',
               'DOLLHOUSE'):
    r = P.camera(preset, b)
    chk('camera %s frames deterministically from bounds' % preset,
        r['valid'] and r['camera']['deterministic'] is True)
    chk('camera %s has a sane FOV, no fisheye' % preset,
        P.SPEC['fov_min'] <= r['camera']['fov'] <= P.SPEC['fov_max']
        and r['camera']['fisheye'] is False)
eye = P.camera('EYE_LEVEL', b)['camera']
chk('eye level really stands at eye height above the model base',
    abs(eye['position'][1] - 1.6) < 1e-9)
big_b = dict(b, radius=120)
chk('the same preset scales with a ten-times larger model',
    P.camera('EXTERIOR_HERO', big_b)['camera']['position']
    != P.camera('EXTERIOR_HERO', b)['camera']['position'])
chk('the same inputs give the identical camera twice',
    P.camera('AERIAL', b) == P.camera('AERIAL', b))

print('\n== §7/§14 — ENVIRONMENT AND PRESENTATION CONTEXT ==')
for mode in ('NEUTRAL', 'SKY', 'STUDIO'):
    r = P.environment(mode)
    chk('environment %s resolves locally with no remote fetch' % mode,
        r['valid'] and r['environment']['remote_fetch'] is False
        and r['environment']['changes_geometry'] is False)
chk('an unknown environment is refused',
    P.environment('HDRI_URL')['issues'][0]['code']
    == 'PQ_INVALID_ENVIRONMENT')
gc = P.SPEC['ground_context']
chk('ground context is visual-only and structurally excluded everywhere',
    gc['visual_only'] is True
    and all(x in gc['excluded_from'] for x in
            ('BIM', 'DOCUMENTATION', 'QUANTITIES', 'ENGINEERING_GLB',
             'MODEL_HASH')))
chk('no roads, parking, landscaping or neighbours are generated',
    gc['roads_generated'] is False and gc['parking_generated'] is False
    and gc['landscaping_generated'] is False
    and gc['neighboring_buildings_generated'] is False)

print('\n== §4/§22 — TEXTURE SYSTEM SECURITY ==')
chk('textures are local-only from the declared root',
    P.SPEC['texture_policy']['local_only'] is True
    and P.SPEC['texture_policy']['allowed_asset_root'] == 'assets/materials/')
chk('the shipped texture set is empty so zero fetches happen',
    P.SPEC['texture_policy']['local_texture_sets'] == []
    and P.SPEC['texture_policy']['missing_texture_fallback']
    == 'PROCEDURAL_PBR')
for bad in ('https://cdn.evil/x.png', '//evil/x.png',
            'assets/materials/../../.env', '../x.png', '/etc/passwd',
            'assets/materials/ok.png.exe', 'javascript:alert(1)',
            'assets/other/x.png', ''):
    chk('hostile texture path %r is refused' % bad[:32],
        P.texture_path_ok(bad)['ok'] is False)
chk('a well-shaped but unlisted path falls back to procedural, not a fetch',
    P.texture_path_ok('assets/materials/brick.png')['ok'] is False
    and P.texture_path_ok('assets/materials/brick.png')['issues'][0]
    ['severity'] == 'WARNING')
chk('world-scale tiling is declared so textures never stretch per mesh',
    P.SPEC['texture_policy']['world_scale_tiling'] is True)

print('\n== §20 — CAPTURE IS PRESENTATION OUTPUT, NOT EVIDENCE ==')
cfg = P.config('HIGH', 'GOLDEN_HOUR', 'REALISTIC', 'SKY', 1.2, None,
               strong, {'radius': 12})['config']
md = P.capture_metadata(cfg, 'model_hash_abc', 1920, 1080, None)
chk('capture metadata is typed PRESENTATION_OUTPUT',
    md['valid'] and md['metadata']['type'] == 'PRESENTATION_OUTPUT')
chk('capture explicitly denies being engineering evidence',
    md['metadata']['is_engineering_evidence'] is False)
chk('capture binds both the model hash and the presentation config hash',
    md['metadata']['model_hash'] == 'model_hash_abc'
    and md['metadata']['presentation_config_hash']
    == cfg['presentation_config_hash'])
chk('an oversized capture resolution is refused',
    P.capture_metadata(cfg, 'x', 99999, 1080)['issues'][0]['code']
    == 'PQ_INVALID_RESOLUTION')

print('\n== §12 — COLOR MANAGEMENT ==')
chk('ACES filmic tone mapping with sRGB output is declared',
    P.SPEC['tone_mapping'] == 'ACES_FILMIC'
    and P.SPEC['output_color_space'] == 'SRGB')
chk('the exposure range guards against washed-out and crushed output',
    0.5 == P.SPEC['exposure_min'] and P.SPEC['exposure_max'] == 1.8)

print('\n== §21 — IMMUTABILITY: THE CRITICAL TEST ==')
for name in ('villa_glazed', 'warehouse', 'hotel', 'clash_mep'):
    prj = AU.create_project(copy.deepcopy(ALL[name]), 'bld_0', 'IMPORT', None)
    before_bytes = D._canon(prj['model'])
    h0, r0 = prj['model_hash'], prj['current_revision']
    bounds = {'cx': 7, 'cy': 3, 'cz': 6.5, 'radius': 14, 'min_y': 0}
    caps = {'webgl2': True, 'max_texture_size': 16384,
            'device_pixel_ratio': 2}
    for profile in ('PERFORMANCE', 'BALANCED', 'HIGH', 'ULTRA'):
        for preset in ('CLEAR_NOON', 'GOLDEN_HOUR', 'INTERIOR_NIGHT',
                       'WAREHOUSE'):
            c = P.config(profile, preset, 'REALISTIC', 'SKY', 1.1,
                         {'plaster': {'roughness': 0.4},
                          'glass_clear': {'transmission': 0.9}},
                         caps, bounds)
            assert c['valid']
            P.capture_metadata(c['config'], h0, 1920, 1080, None)
    for preset in P.CAMERAS:
        P.camera(preset, bounds)
    ok = D.verify_no_mutation(before_bytes, prj)
    chk('%s: canonical model bytes identical after every visual operation'
        % name, ok['unchanged'] is True)
    chk('%s: model hash and revision unchanged' % name,
        prj['model_hash'] == h0 and prj['current_revision'] == r0)
src_meta = D.sources(AU.create_project(copy.deepcopy(ALL['warehouse']),
                                       'bld_0', 'IMPORT', None))
counts_before = {k: len(src_meta[k2][k]) for k2, k in
                 (('arch', 'walls'), ('arch', 'spaces'), ('struct', 'columns'),
                  ('mep', 'equipment'), ('fls', 'devices'))}
chk('object, structural, MEP and FLS counts are untouched by the layer',
    counts_before == {k: len(src_meta[k2][k]) for k2, k in
                      (('arch', 'walls'), ('arch', 'spaces'),
                       ('struct', 'columns'), ('mep', 'equipment'),
                       ('fls', 'devices'))})

print('\n== §24 — THE OLD ENGINEERING RENDER MODE SURVIVES ==')
chk('ENGINEERING remains the default materials mode',
    P.SPEC['default_materials_mode'] == 'ENGINEERING')
cfg_e = P.config('BALANCED', 'CLEAR_NOON', 'ENGINEERING', None, None, None,
                 None, {'radius': 10})
chk('an engineering-mode config is valid and marks the mode',
    cfg_e['valid'] and cfg_e['config']['materials_mode'] == 'ENGINEERING')
chk('the same config twice gives the identical presentation hash',
    cfg_e['config']['presentation_config_hash']
    == P.config('BALANCED', 'CLEAR_NOON', 'ENGINEERING', None, None, None,
                None, {'radius': 10})['config']['presentation_config_hash'])
chk('a different lighting preset gives a different presentation hash',
    cfg_e['config']['presentation_config_hash']
    != P.config('BALANCED', 'OVERCAST', 'ENGINEERING', None, None, None,
                None, {'radius': 10})['config']['presentation_config_hash'])

print('\n─' * 46)
print('PBR QUALITY: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
