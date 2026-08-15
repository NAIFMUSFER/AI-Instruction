# -*- coding: utf-8 -*-
"""المرحلة 9.2 — عقد الأمانة البصرية المعمارية: تصنيف التفاصيل، الواجهة،
النوافذ والأبواب، LED، التأثيث، مكتبة الكائنات، التفسير، التشخيص،
وحصانة النموذج القانوني الكاملة."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'phase9'))
sys.path.insert(0, HERE)

import acs_archdetail as A                                        # noqa: E402
import acs_pbr as P                                               # noqa: E402
import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_ad_fixtures as LF                                      # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


FIX = LF.fixtures()
CANON = json.load(open(os.path.join(ROOT, 'acs_archdetail.json'),
                       encoding='utf-8'))

print('\n== §1 — THE AUTHORITY BOUNDARY NEVER REVERSES ==')
chk('the layer is presentation only and downstream',
    A.SPEC['presentation_only'] is True
    and A.SPEC['writes_to_model'] is False
    and A.SPEC['reverse_write_allowed'] is False
    and A.SPEC['reverse_arrow_exists'] is False)
chk('the pipeline starts at the canonical model and ends at the viewport',
    A.SPEC['pipeline'][0] == 'CANONICAL_ENGINEERING_MODEL'
    and A.SPEC['pipeline'][-1] == 'VIEWPORT_OR_IMAGE'
    and 'ARCHITECTURAL_PRESENTATION_DETAIL_LAYER' in A.SPEC['pipeline'])
chk('it extends the 9.1 layer instead of replacing it',
    A.SPEC['extends'] == 'acs.pbr'
    and A.SPEC['model_hash_inputs'] == ['model'])
chk('no false implementation claim exists (§45)',
    all(A.SPEC[k] is False for k in (
        'photorealism_claimed', 'path_tracing_claimed',
        'ray_tracing_claimed', 'global_illumination_claimed',
        'physically_simulated_sunlight_claimed',
        'bim_grade_facade_detailing_claimed',
        'construction_detailing_claimed', 'code_compliance_claimed',
        'parking_engineering_claimed', 'landscape_design_claimed',
        'lighting_design_claimed')))
chk('two-point perspective is honestly NOT IMPLEMENTED (§31)',
    A.SPEC['two_point_perspective']['implemented'] is False
    and A.SPEC['two_point_perspective']['status'] == 'NOT IMPLEMENTED')

print('\n== §4 — DETAIL CLASSIFICATION ==')
for k in ('CANONICAL_GEOMETRY', 'DERIVED_PRESENTATION_DETAIL',
          'REQUESTED_PRESENTATION_DETAIL', 'DEFAULT_PRESENTATION_CONTEXT',
          'UNRESOLVED'):
    chk('class %s is declared and classifies' % k,
        A.classify_detail(k) == k)
chk('an undeclared class falls to UNRESOLVED, never promoted',
    A.classify_detail('ENGINEERING_TRUTH') == 'UNRESOLVED'
    and A.SPEC['detail_class_promotion_allowed'] is False)
chk('object authority classes are the declared four (14B)',
    sorted(A.AUTHORITY_CLASSES) == ['CANONICAL_OBJECT',
                                    'PRESENTATION_CONTEXT_OBJECT',
                                    'UNRESOLVED_OBJECT',
                                    'USER_REQUESTED_OBJECT'])
chk('ambiguity resolves to UNRESOLVED_OBJECT, not to invention',
    A.object_authority({}, True) == 'UNRESOLVED_OBJECT'
    and A.object_authority({'context': True}, False) == 'UNRESOLVED_OBJECT')

print('\n== 14F — PRESENTATION MATERIALS ==')
chk('twenty-seven presentation materials are declared',
    len(A.MATERIALS) == 27
    and A.SPEC['presentation_material_count'] == 27)
for mid in ('automotive_paint', 'vehicle_glass', 'tire_rubber', 'chrome',
            'forklift_body', 'road_asphalt', 'parking_paint', 'grass',
            'foliage', 'tree_bark', 'stone_beige', 'led_strip'):
    r = A.material(mid)
    chk('material %s resolves with provenance' % mid,
        r['valid'] and r['material']['is_engineering_truth'] is False
        and all(v == 'PRESENTATION_DEFAULT'
                for v in r['material']['provenance'].values()))
chk('an override changes provenance to USER_VISUAL_OVERRIDE',
    A.material('stone_beige', {'roughness': 0.5})['material']
    ['provenance']['roughness'] == 'USER_VISUAL_OVERRIDE')
chk('a prototype-pollution override key is refused',
    A.material('stone_beige', json.loads('{"__proto__": 1}'))
    ['valid'] is False)
chk('an out-of-range override is refused',
    A.material('stone_beige', {'roughness': 99})['valid'] is False)
chk('vehicle glass is physical with transmission',
    A.MATERIALS['vehicle_glass']['three_material'] == 'physical'
    and A.MATERIALS['vehicle_glass']['transmission'] > 0)

print('\n== §23 — DETERMINISTIC MATERIAL VARIATION ==')
v1 = A.variation('mh', 'WALL|f0|r0|s0', 'stone_beige')
v2 = A.variation('mh', 'WALL|f0|r0|s0', 'stone_beige')
v3 = A.variation('mh', 'WALL|f0|r0|s1', 'stone_beige')
chk('same model, element and material → identical variation', v1 == v2)
chk('a different element varies differently', v1 != v3)
chk('variation is bounded by the declared maxima',
    abs(v1['roughness_delta']) <= 0.08 and abs(v1['albedo_delta']) <= 0.05
    and 0 <= v1['normal_delta'] <= 0.3)
chk('seed inputs are model_hash + element_id + material_id',
    A.SPEC['variation']['seed_inputs'] == ['model_hash', 'element_id',
                                           'material_id'])

print('\n== §40/§41 — DETAIL PROFILES AND MOBILE ==')
for name in ('DETAIL_OFF', 'DETAIL_STANDARD', 'DETAIL_HIGH'):
    chk('profile %s resolves' % name,
        A.detail_profile(name)['valid'])
chk('DETAIL_OFF is exactly the Phase 9.1 appearance',
    A.detail_profile('DETAIL_OFF')['profile']['window_frames'] is False
    and A.detail_profile('DETAIL_OFF')['profile']['facade_zoning'] is False)
chk('an undeclared profile is refused',
    A.detail_profile('DETAIL_ULTRA')['valid'] is False)
m = A.detail_profile('DETAIL_HIGH', mobile=True)
chk('mobile degrades HIGH → STANDARD with a reported issue',
    m['profile']['effective'] == 'DETAIL_STANDARD'
    and m['issues'][0]['code'] == 'AD_MOBILE_FALLBACK_APPLIED')
chk('canonical objects are never removed and no blank viewport',
    m['profile']['canonical_objects_removed'] is False
    and m['profile']['blank_viewport_allowed'] is False)

print('\n== §5/§6 — FAÇADE ZONING AND BOUNDED OFFSETS ==')
z = A.facade_zoning([{'id': 'w1', 'role': 'exterior_wall'},
                     {'id': 'w2', 'role': 'exterior_wall'}],
                    {'primary': 'stone_beige', 'accent': 'panel_gray'})
chk('the requested primary maps onto represented exterior walls only',
    z['valid'] and len([a for a in z['zones']['assignments']
                        if a['material'] == 'stone_beige']) == 2)
chk('an accent with no safe zone is UNRESOLVED, not fabricated',
    z['zones']['accent_resolved'] is False
    and z['issues'][0]['code'] == 'AD_VISUAL_DETAIL_UNRESOLVED')
z2 = A.facade_zoning([{'id': 'p1', 'role': 'parapet'},
                      {'id': 'w1', 'role': 'exterior_wall'}],
                     {'primary': 'stone_beige', 'accent': 'panel_gray'})
chk('an accent resolves on a represented band',
    z2['zones']['accent_resolved'] is True)
chk('no wall is invented and no thickness changes',
    z['zones']['invented_walls'] is False
    and z['zones']['wall_thickness_changed'] is False)
chk('an undeclared zone material is refused',
    A.facade_zoning([], {'primary': 'granite'})['valid'] is False)
chk('every visual offset is bounded by the spec (§6)',
    A.SPEC['presentation_offset_max_m'] == 0.06)
chk('zoning assignments carry the mandatory flags',
    all(a['flags']['visual_only'] is True
        and a['flags']['source_element_id'] is not None
        for a in z['zones']['assignments']))

print('\n== §7 — WINDOW FRAME + GLASS ASSEMBLY ==')
w = A.window_assembly({'width': 1.4, 'height': 1.4, 'sill': 0.9,
                       'id': 'WINDOW|f0|r0|0'})
chk('a frame derives proportionally from the represented opening',
    w['valid'] and w['assembly']['frame']['thickness_m'] == 0.063)
chk('tiny and huge openings clamp to the declared bounds',
    A.window_assembly({'width': 0.4, 'height': 0.4})['assembly']
    ['frame']['thickness_m'] == 0.03
    and A.window_assembly({'width': 4.0, 'height': 4.0})['assembly']
    ['frame']['thickness_m'] == 0.09)
chk('the opening itself is never changed',
    w['assembly']['opening_size_changed'] is False
    and w['assembly']['opening_position_changed'] is False
    and w['assembly']['window_count_changed'] is False)
chk('the glass pane uses the physical glass of Phase 9.1',
    w['assembly']['glass']['material'] == 'glass_clear'
    and w['assembly']['glass']['three_material'] == 'physical')
chk('the assembly is a DERIVED_PRESENTATION_DETAIL with source id',
    w['assembly']['detail_class'] == 'DERIVED_PRESENTATION_DETAIL'
    and w['assembly']['flags']['source_element_id'] == 'WINDOW|f0|r0|0')
chk('three frame finishes exist and an unknown one is refused',
    A.window_assembly({'width': 1, 'height': 1}, 'gray')['valid']
    and A.window_assembly({'width': 1, 'height': 1}, 'gold')
    ['valid'] is False)
chk('a degenerate opening is refused, not guessed',
    A.window_assembly({'width': 0, 'height': 1})['valid'] is False)

print('\n== §8 — DOORS ==')
chk('a represented glass door maps to alu_glass',
    A.door_visual({'material': 'door_glass'})['door']
    ['visual_class'] == 'alu_glass')
chk('a represented dock door maps to warehouse_dock_door',
    A.door_visual({'material': 'dockdoor'})['door']
    ['visual_class'] == 'warehouse_dock_door')
chk('the main entrance gets entrance emphasis',
    A.door_visual({'material': 'door', 'entrance': True})['door']
    ['visual_class'] == 'entrance_door')
d = A.door_visual({'material': 'mystery'})
chk('an unknown type falls to the generic presentation door',
    d['door']['visual_class'] == 'generic'
    and d['door']['flags']['confidence'] == 'LOW')
chk('no fire or security rating is ever inferred',
    all(A.door_visual({'material': m})['door'][k] is False
        for m in ('door', 'dockdoor', 'mystery')
        for k in ('fire_rating_inferred', 'security_rating_inferred',
                  'engineering_material_truth')))

print('\n== §9 — BALCONIES ==')
chk('a represented balcony is ENHANCED when requested',
    A.balcony_visual(True, True)['status'] == 'ENHANCED')
g = A.balcony_visual(False, True)
chk('a requested unrepresented balcony is classified, never created',
    g['status'] == 'REQUESTED_BUT_NOT_REPRESENTED'
    and g['engineering_geometry_created'] is False
    and g['issues'][0]['code'] == 'AD_BALCONY_NOT_REPRESENTED')
chk('the UI note exists in both languages',
    'canonical' in g['ui_note_en'] and len(g['ui_note_ar']) > 5)

print('\n== §11 — LED IS VISUAL ONLY, NEVER MEP ==')
led = A.led('facade_strip', {'represented': True, 'id': 'WALL|f0|r0|Ns0'})
chk('a strip on a represented host is visual only',
    led['valid'] and led['light']['visual_only'] is True
    and led['light']['mep_fixture_reused'] is False)
chk('it creates no circuit, load, panel, route or schedule entry',
    all(led['light'][k] is False for k in (
        'creates_electrical_circuit', 'creates_load',
        'creates_panel_assignment', 'creates_cable_route',
        'creates_mep_schedule_entry')))
chk('an unrepresented host refuses with a typed warning',
    A.led('facade_strip', {'represented': False})['issues'][0]['code']
    == 'AD_HOST_NOT_REPRESENTED')
chk('an undeclared light type is refused',
    A.led('disco_ball', {'represented': True})['valid'] is False)
chk('all six declared types resolve on represented hosts',
    all(A.led(t, {'represented': True})['valid']
        for t in A.SPEC['led_lighting']['types']))

print('\n== §13 — STAGING ==')
chk('the default staging mode is REQUESTED_ONLY',
    A.SPEC['default_staging_mode'] == 'STAGING_REQUESTED_ONLY')
s = A.staging_plan('STAGING_REQUESTED_ONLY',
                   [{'kind': 'sofa', 'id': 'o1'}],
                   [{'kind': 'bed', 'id': 'o2'}])
chk('requested-only improves requested and canonical objects, adds none',
    s['valid'] and len(s['plan']['improve']) == 2
    and s['plan']['additions'] == [])
sd = A.staging_plan('STAGING_PRESENTATION_DEFAULT', [], [])
chk('presentation-default additions are context objects outside BIM',
    all(a['authority'] == 'PRESENTATION_CONTEXT_OBJECT'
        and a['flags']['presentation_context'] is True
        and a['enters_bim'] is False and a['enters_quantities'] is False
        for a in sd['plan']['additions']))
chk('no staging mode ever changes the canonical object count',
    all(A.staging_plan(m, [], [])['plan']
        ['canonical_object_count_changed'] is False
        for m in A.STAGING))
chk('an undeclared staging mode is refused',
    A.staging_plan('STAGING_PARTY', [], [])['valid'] is False)

print('\n== 14A/14C/14D/14E — THE PRESENTATION OBJECT LIBRARY ==')
kinds = (list(A.LIBRARY['vehicles']) + list(A.LIBRARY['material_handling'])
         + list(A.LIBRARY['logistics']) + list(A.LIBRARY['landscape'])
         + list(A.LIBRARY['site'])
         + list(A.LIBRARY['construction_requested_only']))
ok = [A.object_recipe(k)['valid'] for k in kinds]
chk('every declared library kind resolves to a recipe (%d kinds)'
    % len(kinds), all(ok))
car = A.object_recipe('car')['recipe']
chk('a car reads as a car: body, cabin, four wheels, glazing, lights',
    car['parts'].count('wheel') == 4 and 'body' in car['parts']
    and 'cabin' in car['parts'] and 'glazing' in car['parts'])
chk('no make, model, plate, engine or VIN is invented',
    car['invented_attributes'] == {k: False for k in (
        'make', 'model', 'license_plate', 'engine', 'vin',
        'manufacturer_specific_geometry')})
fl = A.object_recipe('forklift')['recipe']
chk('a forklift has chassis, guard, mast, forks and counterweight',
    all(x in fl['parts'] for x in ('chassis', 'overhead_guard', 'mast',
                                   'counterweight'))
    and fl['parts'].count('fork') == 2)
chk('no capacity, mast rating, battery or manufacturer is inferred',
    fl['invented_attributes'] == {k: False for k in (
        'lifting_capacity', 'mast_height_rating', 'battery_type',
        'fuel_type', 'manufacturer', 'rated_load')})
chk('an unknown forklift variant falls to the generic presentation',
    A.object_recipe('forklift', variant='HOVERBOARD')['recipe']
    ['recipe_id'] == 'GENERIC_FORKLIFT_PRESENTATION')
bed = A.object_recipe('bed')['recipe']
sofa = A.object_recipe('sofa')['recipe']
ward = A.object_recipe('wardrobe')['recipe']
rack = A.object_recipe('warehouse_rack')['recipe']
chk('furniture reads as its category: bed, sofa, wardrobe, rack',
    'mattress' in bed['parts'] and 'headboard' in bed['parts']
    and sofa['parts'].count('arm') == 2
    and ward['parts'].count('door') == 2
    and rack['parts'].count('upright') == 2)
tree = A.object_recipe('tree')['recipe']
palm = A.object_recipe('palm')['recipe']
chk('landscape assets are parametric: tree canopy clusters, palm fronds',
    tree['parts'].count('canopy_cluster') == 3
    and palm['parts'].count('frond') == 6)
chk('landscape LODs are declared LOW/STANDARD/HIGH',
    A.SPEC['landscape']['lods'] == ['LOW', 'STANDARD', 'HIGH']
    and A.SPEC['landscape']['default'] == 'OFF')
chk('an unknown object kind is refused, not faked',
    A.object_recipe('dragon')['valid'] is False)
chk('repeated context classes are marked for instancing (14G)',
    A.object_recipe('car')['recipe']['instanced'] is True
    and A.object_recipe('tree')['recipe']['instanced'] is True)

print('\n== 14H — SCALE AND PLACEMENT PRIORITY ==')
chk('canonical dimensions win over user and defaults',
    A.object_recipe('car', dims=[2, 5, 1.5],
                    canonical_dims=[1.9, 4.6, 1.5])['recipe']
    ['dims_source'] == 'CANONICAL')
r = A.object_recipe('car')
chk('default dimensions are flagged as presentation fallback',
    r['recipe']['dims_source'] == 'PRESENTATION_DEFAULT'
    and r['issues'][0]['code'] == 'AD_PRESENTATION_DEFAULT_DIMENSIONS')
chk('placement priority: canonical → user → zone → UNRESOLVED',
    A.placement({'canonical_pos': [1, 0, 2]})['source'] == 'CANONICAL'
    and A.placement({'user_pos': [3, 0, 4]})['source'] == 'USER'
    and A.placement({'zone': {'x': 0, 'z': 0, 'w': 10, 'd': 5},
                     'index': 0, 'of': 2})['source']
    == 'ZONE_DETERMINISTIC')
un = A.placement({'kind': 'forklift'})
chk('no zone, no coordinates → UNRESOLVED, never auto-placed',
    un['resolved'] is False
    and un['issues'][0]['code'] == 'AD_PLACEMENT_UNRESOLVED'
    and A.SPEC['auto_populate_spaces'] is False)

print('\n== 14I — SITE EXAMPLES ==')
vb = A.vehicles_to_bays(10, [{'id': 'b%d' % i} for i in range(10)])
chk('«ضع 10 سيارات في المواقف» fills ten represented bays',
    len(vb['placed']) == 10 and vb['unplaced'] == 0
    and all(x['status'] == 'APPLIED_TO_CANONICAL_PARKING'
            for x in vb['placed']))
vb6 = A.vehicles_to_bays(10, [{'id': 'b%d' % i} for i in range(6)])
chk('with six bays only six cars land and the gap is reported',
    len(vb6['placed']) == 6 and vb6['unplaced'] == 4
    and vb6['issues'][0]['code'] == 'AD_PARKING_NOT_RESOLVED')
chk('parking requested with no bays is geometrically unresolved (§18)',
    A.parking(True, 0)['status']
    == 'REQUESTED_NOT_GEOMETRICALLY_RESOLVED'
    and A.parking(True, 0)['invented_count'] is False)
chk('represented parking renders professionally',
    A.parking(True, 8)['status'] == 'APPLIED_TO_CANONICAL_PARKING')

print('\n== §15/§16 — KITCHEN AND BATHROOM ==')
k = A.kitchen_layout('L أو U حسب الدور', None)
chk('an ambiguous kitchen phrase is UNRESOLVED, never guessed',
    k['layout'] is None
    and k['issues'][0]['code'] == 'AD_KITCHEN_LAYOUT_UNRESOLVED')
chk('a canonical layout is honoured',
    A.kitchen_layout(True, 'L')['layout'] == 'L'
    and A.kitchen_layout(True, 'T')['layout'] is None)
chk('bathroom fixtures are never placed if absent',
    A.SPEC['bathroom_rules']['place_if_absent'] is False
    and A.SPEC['bathroom_rules']['infer_plumbing'] is False)

print('\n== §27 — GLASS REFLECTION ENVIRONMENTS ==')
for e in ('NEUTRAL_STUDIO', 'CLEAR_SKY', 'OVERCAST_SKY', 'SUNSET_SKY'):
    r = A.environment(e)
    chk('environment %s resolves through the existing PMREM path' % e,
        r['valid'] and r['environment']['runtime_cdn'] is False
        and r['environment']['remote_hdri'] is False)
chk('an undeclared environment is refused',
    A.environment('MARS_SKY')['valid'] is False)

print('\n== §30 — PROFESSIONAL CAMERA COMPOSITION ==')
B = {'cx': 7, 'cy': 3, 'cz': 6.5, 'radius': 14, 'min_y': 0}
for preset in sorted(A.CAMERAS_ARCH):
    c = A.camera(preset, B)
    chk('camera %s frames deterministically without fisheye' % preset,
        c['valid'] and 20 <= c['camera']['fov'] <= 75
        and c['camera']['fisheye'] is False
        and c['camera']['deterministic'] is True)
chk('street level sits at human eye height',
    A.camera('EXTERIOR_STREET_LEVEL', B)['camera']['position'][1] == 1.6)
chk('the Phase 9.1 presets still resolve through the same resolver',
    A.camera('EXTERIOR_HERO', B)['valid']
    and A.camera('DOLLHOUSE', B)['valid'])
chk('an undeclared preset is refused',
    A.camera('SELFIE', B)['valid'] is False)
chk('the exterior hero favours a three-quarter view',
    A.SPEC['exterior_hero_three_quarter'] is True
    and 0 < A.CAMERAS_ARCH['EXTERIOR_HERO_CORNER']['azimuth_deg'] < 90)

print('\n== §32 — AUTO PRESENTATION ==')
for t, cam in (('warehouse', 'WAREHOUSE_OVERVIEW_92'),
               ('villa', 'EXTERIOR_HERO_CORNER'),
               ('clinic', 'EXTERIOR_HERO_FRONT'),
               ('hotel', 'EXTERIOR_HERO_CORNER')):
    a = A.auto_presentation({'type': t})
    chk('auto mode for %s picks presentation settings only' % t,
        a['auto']['camera_preset'] == cam
        and a['auto']['engineering_geometry_changed'] is False)
chk('auto never selects ULTRA',
    A.auto_presentation({'type': 'villa'})['auto']
    ['ultra_auto_selected'] is False)
chk('an interior scene picks the interior mode',
    A.auto_presentation({'indoor': True})['auto']
    ['camera_preset'] == 'INTERIOR_LIVING')

print('\n== §33 — VISUAL REQUEST INTERPRETATION ==')
i = A.interpret(FIX['A_villa_stone']['request'])
cls = {x['intent']: x['classification'] for x in i['intents']}
chk('«حجر طبيعي بيج» is a SAFE_VISUAL_OVERRIDE facade preference',
    cls.get('facade_material') == 'SAFE_VISUAL_OVERRIDE')
chk('«زجاج عاكس» is a safe glass appearance preference',
    cls.get('glass_appearance') == 'SAFE_VISUAL_OVERRIDE')
chk('«بلكونات أكبر» REQUIRES_ENGINEERING_CHANGE — not presentation-safe',
    A.interpret('بلكونات أكبر')['intents'][0]['classification']
    == 'REQUIRES_ENGINEERING_CHANGE')
chk('«إنارة LED مخفية» is a presentation-light request',
    A.interpret('إنارة LED مخفية')['intents'][0]['intent']
    == 'led_lighting')
chk('«دور إضافي» is an engineering massing change',
    any(x['classification'] == 'REQUIRES_ENGINEERING_CHANGE'
        for x in A.interpret('دور إضافي')['intents']))
chk('descriptive language never grants engineering permission',
    all(A.interpret(t)['engineering_permission_granted'] is False
        for t in ('حجر بيج', 'بلكونات أكبر', '')))
chk('hostile text yields no intents and no crash',
    A.interpret(LF.HOSTILE_TEXT[0])['intents'] == [])

print('\n== §34/§35 — DIAGNOSTIC AND COVERAGE OVER THE FIXTURES ==')
for name in sorted(FIX):
    fx = FIX[name]
    req = A.interpret(fx['request'])['intents']
    d = A.diagnostic(req, fx['summary'])
    chk('%s: diagnostic accounts for every request, none dropped' % name,
        d['valid']
        and len(d['diagnostic']['features'])
        == len(d['diagnostic']['requested_visual_features'])
        and d['diagnostic']['silently_dropped'] == [])
dg = A.diagnostic(A.interpret(FIX['G_unresolved_balcony']['request'])
                  ['intents'], FIX['G_unresolved_balcony']['summary'])
chk('G: the balcony request surfaces as not represented',
    any(ft['status'] == 'REQUESTED_BUT_NOT_REPRESENTED'
        for ft in dg['diagnostic']['features']))
dh = A.diagnostic(A.interpret(FIX['H_unresolved_parking']['request'])
                  ['intents'], FIX['H_unresolved_parking']['summary'])
chk('H: parking is REQUESTED_NOT_GEOMETRICALLY_RESOLVED',
    any(ft['status'] == 'REQUESTED_NOT_GEOMETRICALLY_RESOLVED'
        for ft in dh['diagnostic']['features']))
di = A.diagnostic(A.interpret(FIX['I_led_request']['request'])['intents'],
                  FIX['I_led_request']['summary'])
chk('I: concealed LED is VISUAL_ONLY_APPLIED',
    any(ft['status'] == 'VISUAL_ONLY_APPLIED'
        for ft in di['diagnostic']['features']))
dj = A.diagnostic(A.interpret(FIX['J_ambiguous_kitchen']['request'])
                  ['intents'], FIX['J_ambiguous_kitchen']['summary'])
chk('J: the ambiguous kitchen stays UNRESOLVED',
    any(i2['code'] == 'AD_KITCHEN_LAYOUT_UNRESOLVED'
        for i2 in dj['issues']))
db = A.diagnostic(A.interpret(FIX['B_apartment_balconies']['request'])
                  ['intents'], FIX['B_apartment_balconies']['summary'])
chk('B: represented balconies are enhanced, LED applies',
    any(ft['status'] == 'ENHANCED'
        for ft in db['diagnostic']['features'])
    and any(ft['status'] == 'VISUAL_ONLY_APPLIED'
            for ft in db['diagnostic']['features']))
dl = A.diagnostic([], FIX['L_malicious']['summary'])
chk('L: hostile object kinds resolve to UNRESOLVED_OBJECT, no crash',
    len(dl['diagnostic']['unresolved_objects']) == 2)
cov = A.coverage(A.diagnostic(
    A.interpret(FIX['A_villa_stone']['request'])['intents'],
    FIX['A_villa_stone']['summary']))
chk('coverage counts requested/represented/unresolved honestly',
    cov['name'] == 'VISUAL_REQUEST_COVERAGE'
    and cov['requested'] == cov['represented'] + cov['unresolved']
    + cov['requires_engineering_change']
    and cov['is_engineering_completeness'] is False
    and cov['has_compliance_meaning'] is False)

print('\n== §38 — CAPTURE METADATA EXTENSION ==')
pbr_cfg = P.config('HIGH', 'CLEAR_NOON', 'REALISTIC', 'SKY', 1.1,
                   None, None, B)['config']
ad_cfg = A.config('DETAIL_HIGH', 'REQUESTED', 'SITE',
                  'STAGING_REQUESTED_ONLY', 'EXTERIOR_HERO_FRONT',
                  'CLEAR_SKY')['config']
md = A.capture_metadata(pbr_cfg, ad_cfg, 'mh_1', 5, 1920, 1080)
chk('the capture carries the architectural extension fields',
    md['valid']
    and md['metadata']['presentation_layer_version'] == '9.2.0'
    and md['metadata']['architectural_detail_level'] == 'DETAIL_HIGH'
    and md['metadata']['context_mode'] == 'SITE'
    and md['metadata']['staging_mode'] == 'STAGING_REQUESTED_ONLY'
    and md['metadata']['revision'] == 5)
chk('a capture is never engineering evidence',
    md['metadata']['is_engineering_evidence'] is False)

print('\n== §43/§44 — IMMUTABILITY: THE CRITICAL TEST ==')
MODELS = LF.all_models()
for name in ('villa_glazed', 'hotel', 'clinic', 'warehouse',
             'apartment_balconies'):
    prj = AU.create_project(copy.deepcopy(MODELS[name]), 'bld_0',
                            'IMPORT', None)
    before_bytes = D._canon(prj['model'])
    h0, r0 = prj['model_hash'], prj['current_revision']
    src0 = D.sources(prj)
    counts0 = {k2 + '.' + k: len(src0[k2][k]) for k2, k in
               (('arch', 'walls'), ('arch', 'spaces'),
                ('arch', 'openings'), ('struct', 'columns'),
                ('mep', 'equipment'), ('fls', 'devices'))}
    qty0 = D.quantities(prj, {}, src0)['report']['count']
    obj0 = json.dumps(prj['model'].get('floors'), sort_keys=True)
    req = A.interpret('واجهة حجر بيج مع لمسات رمادية وزجاج عاكس '
                      'وإنارة LED مخفية')['intents']
    summary = {'exterior_walls': 4, 'windows': 6, 'accent_band': 0}
    for detail in ('DETAIL_OFF', 'DETAIL_STANDARD', 'DETAIL_HIGH'):
        for ctx in ('NONE', 'NEUTRAL', 'SITE', 'LANDSCAPE'):
            c = A.config(detail, 'REQUESTED', ctx,
                         'STAGING_PRESENTATION_DEFAULT',
                         'EXTERIOR_HERO_CORNER', 'SUNSET_SKY',
                         None, False, req, summary)
            assert c['valid']
            A.capture_metadata(pbr_cfg, c['config'], h0, r0, 1920, 1080)
    A.facade_zoning([{'id': 'w1', 'role': 'exterior_wall'}],
                    {'primary': 'stone_beige'})
    A.window_assembly({'width': 1.4, 'height': 1.4})
    A.led('facade_strip', {'represented': True})
    A.staging_plan('STAGING_PRESENTATION_DEFAULT', [], [])
    for kind in ('car', 'forklift', 'tree', 'sofa'):
        A.object_recipe(kind)
    for preset in sorted(A.CAMERAS_ARCH):
        A.camera(preset, B)
    ok = D.verify_no_mutation(before_bytes, prj)
    chk('%s: canonical bytes identical after the full visual battery'
        % name, ok['unchanged'] is True)
    src1 = D.sources(prj)
    counts1 = {k2 + '.' + k: len(src1[k2][k]) for k2, k in
               (('arch', 'walls'), ('arch', 'spaces'),
                ('arch', 'openings'), ('struct', 'columns'),
                ('mep', 'equipment'), ('fls', 'devices'))}
    chk('%s: hash, revision, discipline counts and quantities unchanged'
        % name,
        prj['model_hash'] == h0 and prj['current_revision'] == r0
        and counts1 == counts0
        and D.quantities(prj, {}, src1)['report']['count'] == qty0)
    chk('%s: canonical object identity preserved (§44)' % name,
        json.dumps(prj['model'].get('floors'), sort_keys=True) == obj0)

print('\n== §24 — DEFAULTS: ENGINEERING MODE FIRST ==')
c0 = A.config()
chk('the default configuration is DETAIL_OFF engineering appearance',
    c0['valid'] and c0['config']['detail']['effective'] == 'DETAIL_OFF'
    and c0['config']['facade_mode'] == 'ENGINEERING'
    and c0['config']['context_mode'] == 'NONE')
chk('the configuration hash is deterministic and model-independent',
    A.config()['config']['presentation_config_hash']
    == c0['config']['presentation_config_hash'])
chk('different settings hash differently',
    A.config('DETAIL_HIGH')['config']['presentation_config_hash']
    != c0['config']['presentation_config_hash'])
chk('invalid modes are refused with typed errors',
    A.config('DETAIL_MEGA')['valid'] is False
    and A.config('DETAIL_OFF', 'CARTOON')['valid'] is False
    and A.config('DETAIL_OFF', None, 'MOON')['valid'] is False)

print('\n──────────────────────────────────────────────')
print('ARCH DETAIL: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
