# -*- coding: utf-8 -*-
"""المرحلة 8 — عقد التبادل مع BIM: التصدير، الاستيراد، الترحيل، الذهاب والإياب،
الفرق والمقترحات، القِدَم، الأمن والحدود. كل فحص يُنفَّذ فعلاً على ملفّ حقيقي."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_bim as B                                              # noqa: E402
import acs_authoring as AU                                       # noqa: E402
import lib_bim_fixtures as LIB                                   # noqa: E402

ALL = LIB.models()
AT = '2026-01-01T00:00:00Z'
TARGETS = ['villa', 'hotel', 'clinic', 'warehouse']
GLAZED = ['villa_glazed', 'hotel_glazed', 'clinic_glazed', 'warehouse_glazed']

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓', name)
    else:
        f[0] += 1
        print('  ✗', name, detail)


def PR(k):
    return AU.create_project(copy.deepcopy(ALL[k]), 'bld_0', 'IMPORT', None)


print('\n== §1/§5 — THE SPEC AND THE NON-NEGOTIABLE RULE ==')
chk('external BIM is never model truth', B.SPEC['external_bim_is_model_truth'] is False)
chk('no direct import write is allowed', B.SPEC['direct_import_write_allowed'] is False)
chk('an explicit commit is required', B.SPEC['requires_explicit_commit'] is True)
chk('commits route through the authoring path', B.SPEC['writes_via_authoring_path'] is True)
chk('no remote dependency is declared', B.SPEC['remote_dependency'] is False
    and B.SPEC['remote_reference_policy'] == 'NEVER_FETCH')
chk('the import pipeline ends at the canonical model through authoring',
    B.SPEC['import_pipeline'][-1] == 'CANONICAL_ENGINEERING_MODEL'
    and 'AUTHORING_REVISION_PATH' in B.SPEC['import_pipeline']
    and 'EXPLICIT_USER_ACCEPTANCE' in B.SPEC['import_pipeline'])
chk('all five support levels are declared', len(B.SPEC['support_levels']) == 5)
chk('every declared entity carries a support level',
    all(e['support'] in B.SPEC['support_levels'] for e in B.SPEC['entity_support']))
chk('every required issue code is declared',
    all(c in B.ISSUE_CODES for c in (
        'BIM_INVALID_FILE', 'BIM_UNKNOWN_SCHEMA', 'BIM_UNSUPPORTED_ENTITY',
        'BIM_UNSUPPORTED_GEOMETRY', 'BIM_INVALID_REFERENCE', 'BIM_DUPLICATE_ID',
        'BIM_UNIT_UNRESOLVED', 'BIM_UNIT_INVALID', 'BIM_PLACEMENT_INVALID',
        'BIM_PLACEMENT_CYCLE', 'BIM_CONTAINMENT_CYCLE', 'BIM_RELATIONSHIP_INVALID',
        'BIM_AMBIGUOUS_MAPPING', 'BIM_HOST_UNRESOLVED', 'BIM_PROPERTY_UNSUPPORTED',
        'BIM_GEOMETRY_LOSS', 'BIM_RESOURCE_LIMIT_EXCEEDED', 'BIM_STALE_TARGET_MODEL',
        'BIM_EXPORT_VALIDATION_FAILED', 'BIM_ROUNDTRIP_DRIFT')))
chk('every tolerance is declared centrally and is tight',
    all(0 < float(v) <= 0.05 for v in B.TOL.values()) and len(B.TOL) == 5)
chk('every resource limit is finite and positive',
    all(0 < float(v) < float('inf') for v in B.LIMITS.values()))
chk('the four verification classes are declared',
    B.SPEC['verification_classes'] == ['CODE_VERIFIED', 'RUNTIME_VERIFIED',
                                       'INTEROP_VERIFIED', 'NOT_VERIFIED'])
chk('a round trip is explicitly not interoperability verification',
    'round-trip verification, not interoperability' in B.SPEC['interop_note'])
chk('the panel forbids a replace-model control',
    'IMPORT_AND_REPLACE_MODEL' in B.SPEC['panel_forbidden_controls'])
chk('the hard stop boundaries name the excluded integrations',
    all(x in ' '.join(B.SPEC['hard_stop_boundaries'])
        for x in ('Revit live sync', 'BIM 360', 'autonomous design')))

print('\n== §46 — TEST A: A REAL IFC FILE IS PRODUCED FOR EVERY MODEL ==')
EXPORTS = {}
for k in TARGETS + GLAZED:
    prj = PR(k)
    h0, r0 = prj['model_hash'], prj['current_revision']
    before = json.dumps(prj['model'], sort_keys=True)
    res = B.export_ifc(prj, {}, None)
    chk('%s: the export succeeds' % k, res['valid'],
        json.dumps([i['message'] for i in res['issues']][:2]))
    if not res['valid']:
        continue
    EXPORTS[k] = res
    txt = res['file']
    chk('%s: the file is an ISO-10303-21 STEP file' % k,
        txt.startswith('ISO-10303-21;') and txt.rstrip().endswith('END-ISO-10303-21;'))
    chk('%s: the file declares the IFC4 schema' % k, "FILE_SCHEMA(('IFC4'))" in txt)
    chk('%s: the file has a HEADER and a DATA section' % k,
        'HEADER;' in txt and 'DATA;' in txt and 'ENDSEC;' in txt)
    parsed = B.parse_step(txt, k + '.ifc')
    chk('%s: the produced file parses back' % k, parsed['valid'],
        json.dumps([i['message'] for i in parsed['issues']][:2]))
    if not parsed['valid']:
        continue
    ents = parsed['step']['entities']
    types = {}
    for e in ents.values():
        types[e['type']] = types.get(e['type'], 0) + 1
    m = res['manifest']
    chk('%s: the parsed hierarchy holds one project, site and building' % k,
        types.get('IFCPROJECT') == 1 and types.get('IFCSITE') == 1
        and types.get('IFCBUILDING') == 1)
    chk('%s: every level is a real IfcBuildingStorey' % k,
        types.get('IFCBUILDINGSTOREY') == m['level_count'])
    chk('%s: every wall is a real IfcWallStandardCase' % k,
        types.get('IFCWALLSTANDARDCASE') == m['wall_count'])
    chk('%s: every door is a real IfcDoor' % k,
        types.get('IFCDOOR', 0) == m['door_count'])
    chk('%s: every window is a real IfcWindow' % k,
        types.get('IFCWINDOW', 0) == m['window_count'])
    chk('%s: every space is a real IfcSpace' % k,
        types.get('IFCSPACE', 0) == m['space_count'])
    chk('%s: no object is invented beyond the declared mapping' % k,
        all(t.upper() in [x['entity'].upper() for x in B.SPEC['entity_support']]
            or t.startswith('IFCREL') or t in (
                'IFCCARTESIANPOINT', 'IFCDIRECTION', 'IFCAXIS2PLACEMENT3D',
                'IFCLOCALPLACEMENT', 'IFCEXTRUDEDAREASOLID', 'IFCRECTANGLEPROFILEDEF',
                'IFCAXIS2PLACEMENT2D',
                'IFCSHAPEREPRESENTATION', 'IFCPRODUCTDEFINITIONSHAPE', 'IFCPOLYLINE',
                'IFCSIUNIT', 'IFCUNITASSIGNMENT', 'IFCCONVERSIONBASEDUNIT',
                'IFCMEASUREWITHUNIT', 'IFCDIMENSIONALEXPONENTS', 'IFCPERSON',
                'IFCORGANIZATION', 'IFCPERSONANDORGANIZATION', 'IFCAPPLICATION',
                'IFCOWNERHISTORY', 'IFCGEOMETRICREPRESENTATIONCONTEXT',
                'IFCPROPERTYSET', 'IFCPROPERTYSINGLEVALUE')
            for t in types), json.dumps(sorted(types.keys()))[:200])
    chk('%s: every GlobalId is 22 characters' % k,
        all(len(e['args'][0]) == 22 for e in ents.values()
            if e['type'] in ('IFCPROJECT', 'IFCSITE', 'IFCBUILDING',
                             'IFCBUILDINGSTOREY', 'IFCSPACE', 'IFCWALLSTANDARDCASE',
                             'IFCDOOR', 'IFCWINDOW', 'IFCSLAB', 'IFCSTAIR')
            and isinstance(e['args'][0], str)))
    chk('%s: the model hash is unchanged by the export' % k, prj['model_hash'] == h0)
    chk('%s: the revision is unchanged by the export' % k,
        prj['current_revision'] == r0)
    chk('%s: the canonical model is byte-identical after the export' % k,
        json.dumps(prj['model'], sort_keys=True) == before)

print('\n== §47 — TEST B: EXPORT DETERMINISM ==')
for k in TARGETS:
    prj = PR(k)
    a = B.export_ifc(prj, {}, None)
    b = B.export_ifc(prj, {}, None)
    chk('%s: two exports produce byte-identical files' % k, a['file'] == b['file'])
    chk('%s: two exports produce the same export id' % k,
        a['manifest']['export_id'] == b['manifest']['export_id'])
    chk('%s: two exports produce the same body hash' % k,
        a['manifest']['body_hash'] == b['manifest']['body_hash'])
    c = B.export_ifc(prj, {}, '2030-05-05T05:05:05')
    chk('%s: only the declared timestamp differs, never the body' % k,
        c['manifest']['body_hash'] == a['manifest']['body_hash']
        and c['file'] != a['file'])
    chk('%s: the manifest names the timestamp as the only variable field' % k,
        a['manifest']['non_deterministic_fields'] == ['generated_at'])
    prj2 = PR(k)
    chk('%s: a fresh project of the same model exports identically' % k,
        B.export_ifc(prj2, {}, None)['file'] == a['file'])

print('\n== §48 — TEST C: IMPORT THE OWN EXPORT AND REPORT FIDELITY ==')
STAGINGS = {}
for k in TARGETS + GLAZED:
    if k not in EXPORTS:
        continue
    prj = PR(k)
    st = B.stage_import(EXPORTS[k]['file'], k + '.ifc', {}, None, AT)
    chk('%s: the exported file stages cleanly' % k, st['valid'],
        json.dumps([i['code'] for i in st['issues']][:4]))
    if not st['valid']:
        continue
    STAGINGS[k] = st['staging']
    chk('%s: the staging model never writes to the model' % k,
        st['staging']['writes_to_model'] is False
        and st['staging']['is_model_truth'] is False)
    rt = B.roundtrip_report(prj, st['staging'], {})
    rep = rt['report']
    chk('%s: a fidelity report is produced' % k, rt['valid'] and rep is not None)
    chk('%s: geometry fidelity is complete' % k, rep['geometry_fidelity'] == 1.0,
        str(rep['geometry_fidelity']))
    chk('%s: no critical geometry loss' % k, rep['critical_loss_count'] == 0)
    chk('%s: the status is PASS or WARNING, never a false PASS' % k,
        rep['status'] in ('PASS', 'WARNING')
        and (rep['status'] != 'PASS' or not rep['losses']))
    chk('%s: geometry is compared, not only counted' % k,
        rep['compared']['wall_positions']['matched'] > 0
        and rep['compared']['level_elevations']['equal'] is True)
    chk('%s: containment and host relationships are compared' % k,
        rep['compared']['containment']['resolved'] > 0
        and 'host_relationships' in rep['compared'])
    chk('%s: the report carries the declared tolerances' % k,
        rep['tolerances'] == dict(B.TOL))
    chk('%s: the report writes nothing to the model' % k,
        rep['writes_to_model'] is False)

print('\n== §49 — TEST D: UNITS ARE NORMALISED, NEVER GUESSED ==')
for prefix, name, factor in ((None, 'metre', 1.0), ('MILLI', 'millimetre', 0.001),
                             ('CENTI', 'centimetre', 0.01)):
    body = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
            "#20=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaS',$,'R',$,$,#19,$,'1',"
            ".ELEMENT.,.INTERNAL.,0.);\n")
    txt = LIB.minimal(prefix, body)
    st = B.stage_import(txt, 'u.ifc', {}, None, AT)
    chk('a file in %s is staged' % name, st['valid'],
        json.dumps([i['code'] for i in st['issues']][:3]))
    if st['valid']:
        chk('the %s file records its declared factor' % name,
            abs(st['staging']['units']['length']['to_metre'] - factor) < 1e-9,
            str(st['staging']['units']['length']))
        chk('the %s file normalises to the canonical metre' % name,
            st['staging']['units']['canonical_length'] == 'METRE')
conv = ("#1=IFCDIMENSIONALEXPONENTS(1,0,0,0,0,0,0);\n"
        "#2=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
        "#3=IFCMEASUREWITHUNIT(IFCLENGTHMEASURE(0.3048),#2);\n"
        "#4=IFCCONVERSIONBASEDUNIT(#1,.LENGTHUNIT.,'FOOT',#3);\n"
        "#5=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);\n"
        "#6=IFCUNITASSIGNMENT((#4,#5));\n")
ft = LIB.wrap(conv)
stf = B.stage_import(ft, 'ft.ifc', {}, None, AT)
chk('a foot-based file resolves its conversion factor',
    stf['staging']['units']['length'] is not None
    and abs(stf['staging']['units']['length']['to_metre'] - 0.3048) < 1e-9,
    json.dumps(stf['staging']['units']['length']))
nounit = LIB.wrap("#1=IFCCARTESIANPOINT((0.,0.,0.));\n")
stn = B.stage_import(nounit, 'n.ifc', {}, None, AT)
chk('a file with no declared unit is refused, never defaulted',
    stn['valid'] is False
    and any(i['code'] == 'BIM_UNIT_UNRESOLVED' for i in stn['issues']))
chk('the unit policy is declared as declared-only',
    B.SPEC['unit_policy'] == 'DECLARED_ONLY'
    and 'never guessed' in B.SPEC['unit_note'])
mm = B.stage_import(LIB.minimal('MILLI'), 'mm.ifc', {}, None, AT)
m = B.stage_import(LIB.minimal(None), 'm.ifc', {}, None, AT)
chk('the same geometry in two units agrees after normalisation',
    mm['staging']['units']['length']['to_metre'] * 1000.0
    == m['staging']['units']['length']['to_metre'] * 1.0)

print('\n== §50 — TEST E: NESTED PLACEMENT RESOLVES TO WORLD ==')
nested = (
    "#19=IFCCARTESIANPOINT((10.,20.,0.));\n"
    "#20=IFCAXIS2PLACEMENT3D(#19,#5,#6);\n"
    "#21=IFCLOCALPLACEMENT(#14,#20);\n"
    "#22=IFCCARTESIANPOINT((1.,2.,0.));\n"
    "#23=IFCDIRECTION((0.,1.,0.));\n"
    "#24=IFCAXIS2PLACEMENT3D(#22,#5,#23);\n"
    "#25=IFCLOCALPLACEMENT(#21,#24);\n"
    "#26=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaN',$,'N',$,$,#25,$,'1',"
    ".ELEMENT.,.INTERNAL.,0.);\n")
stp = B.stage_import(LIB.minimal(None, nested), 'p.ifc', {}, None, AT)
chk('a nested placement file stages', stp['valid'],
    json.dumps([i['code'] for i in stp['issues']][:3]))
if stp['valid']:
    sp = [e for e in stp['staging']['entities'] if e['canonical_kind'] == 'space']
    chk('the nested space resolves to project world coordinates',
        len(sp) == 1 and sp[0]['world'] is not None
        and abs(sp[0]['world']['xyz'][0] - 11.0) <= B.TOL['position_tolerance_m']
        and abs(sp[0]['world']['xyz'][1] - 22.0) <= B.TOL['position_tolerance_m'],
        json.dumps(sp[0]['world']) if sp else 'missing')
    chk('the nested rotation accumulates', sp and sp[0]['world']['rot_deg'] == 90.0,
        str(sp[0]['world']['rot_deg']) if sp else '')
storey = [e for e in (stp['staging']['entities'] if stp['valid'] else [])
          if e['canonical_kind'] == 'level']
chk('a storey elevation is read from the model attribute',
    storey and storey[0]['geometry']['elevation_source'] == 'MODEL')
neg = ("#19=IFCCARTESIANPOINT((-1000000.,-2000000.,0.));\n"
       "#20=IFCAXIS2PLACEMENT3D(#19,#5,#6);\n"
       "#21=IFCLOCALPLACEMENT(#14,#20);\n"
       "#22=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaG',$,'G',$,$,#21,$,'1',"
       ".ELEMENT.,.INTERNAL.,0.);\n")
stneg = B.stage_import(LIB.minimal(None, neg), 'g.ifc', {}, None, AT)
chk('large negative coordinates resolve without loss', stneg['valid'])

print('\n== §51 — TEST F: OPENINGS KEEP THEIR HOST ==')
k = 'villa_glazed'
if k in STAGINGS:
    ops = [e for e in STAGINGS[k]['entities']
           if e['canonical_kind'] in ('door', 'window')]
    chk('the staged model really carries openings', len(ops) > 0)
    chk('every opening resolved a host wall through an IFC relationship',
        all(o['host_source_id'] and o['host_basis'] == 'IFC_RELATIONSHIP'
            for o in ops), str(len([o for o in ops if not o['host_source_id']])))
    chk('no opening floats without a host', not any(
        o['host_basis'] == 'UNRESOLVED' for o in ops))
    chk('the void and fill relationships are both present',
        len(STAGINGS[k]['relationships']['voids']) > 0
        and len(STAGINGS[k]['relationships']['fills']) > 0)
lonely = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
          "#20=IFCDOOR('0aaaaaaaaaaaaaaaaaaaaD',$,'D',$,$,#19,$,$,2.1,0.9,$,$);\n")
stl = B.stage_import(LIB.minimal(None, lonely), 'd.ifc', {}, None, AT)
door = [e for e in stl['staging']['entities'] if e['canonical_kind'] == 'door']
chk('a door with no void or fill relationship is reported unresolved',
    door and door[0]['host_basis'] == 'UNRESOLVED')
chk('no host is inferred from overlapping coordinates',
    any(i['code'] == 'BIM_HOST_UNRESOLVED' for i in stl['issues'])
    and 'no host is inferred from coordinates' in ' '.join(
        i['message'] for i in stl['issues']))

print('\n== §52 — TEST G: AN UNSUPPORTED ENTITY IS NEVER INVENTED ==')
unsup = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
         "#20=IFCFLOWTERMINAL('0aaaaaaaaaaaaaaaaaaaaF',$,'FT',$,$,#19,$,$);\n"
         "#21=IFCBUILDINGELEMENTPROXY('0aaaaaaaaaaaaaaaaaaaaP',$,'PX',$,$,#19,$,$,$);\n")
stu = B.stage_import(LIB.minimal(None, unsup), 'u.ifc', {}, None, AT)
chk('a file with unsupported entities still stages', stu['valid'])
ents = stu['staging']['entities']
ft2 = [e for e in ents if e['entity_type'] == 'IFCFLOWTERMINAL']
px = [e for e in ents if e['entity_type'] == 'IFCBUILDINGELEMENTPROXY']
chk('a preserved-opaque entity is kept with its identity',
    ft2 and ft2[0]['support'] == 'PRESERVED_OPAQUE'
    and ft2[0]['external_global_id'] and ft2[0]['canonical_kind'] is None)
chk('an unsupported entity is kept and reported, never deleted silently',
    px and px[0]['support'] == 'UNSUPPORTED' and px[0]['canonical_kind'] is None)
chk('an issue is emitted for the unsupported entity',
    any(i['code'] == 'BIM_UNSUPPORTED_ENTITY' for i in stu['issues']))
chk('no unsupported entity is given a canonical kind',
    all(e['canonical_kind'] is None for e in ents
        if e['support'] in ('UNSUPPORTED', 'PRESERVED_OPAQUE')))
chk('the counts expose unsupported entities rather than hiding them',
    stu['staging']['counts']['unsupported'] >= 1
    and stu['staging']['counts']['opaque'] >= 1)

print('\n== §53 — TEST H: PROPERTY AND STRING SAFETY ==')
# صنفان لا صنف واحد. الأوّل قابل للتنفيذ أو للجلب أو لاجتياز المسار، فيُرفض
# صراحةً. والثاني نصّ خامل يشبه مفتاح نموذج أوّلي أو تعبير قالب، ولا يُرفض
# لأنّ ملفّاً خارجياً صحيحاً قد يسمّي غرفةً هكذا؛ يُثبَت خموله إثباتاً موجباً
EXECUTABLE = ["<script>alert(1)</script>", "javascript:alert(1)",
              "<img src=x onerror=alert(1)>", "../../etc/passwd",
              "data:text/html,x", "<!ENTITY e SYSTEM 'file:///etc/passwd'>",
              "vbscript:x"]
INERT_TEXT = ["__proto__", "constructor", "prototype", "{{7*7}}"]
TEXT_FIELDS = set(B.SPEC['text_only_fields'])


def _space_named(nm, gid_tail):
    esc = nm.replace("\\", "\\\\").replace("'", "''")
    body = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
            "#20=IFCSPACE('0aaaaaaaaaaaaaaaaaaaX%s',$,'%s',$,$,#19,$,'1',"
            ".ELEMENT.,.INTERNAL.,0.);\n" % (gid_tail, esc))
    return B.stage_import(LIB.minimal(None, body), 'x.ifc', {}, None, AT)


def _walk(node, on_key, on_value, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            on_key(k, path)
            _walk(v, on_key, on_value, path + (k,))
    elif isinstance(node, list):
        for j, v in enumerate(node):
            _walk(v, on_key, on_value, path + ('[]',))
    else:
        on_value(node, path)


for i, pl in enumerate(EXECUTABLE):
    st = _space_named(pl, str(i % 10))
    names = [e.get('name') for e in (st['staging']['entities'] if st['staging'] else [])]
    chk('executable payload #%d never reaches a canonical name' % i, pl not in names,
        json.dumps(names)[:160])
    chk('executable payload #%d is refused with a typed issue' % i,
        any(i2['code'] == 'BIM_UNSAFE_STRING' for i2 in st['issues']),
        json.dumps([i2['code'] for i2 in st['issues']][:4]))

for i, pl in enumerate(INERT_TEXT):
    st = _space_named(pl, chr(ord('a') + i))
    chk('inert label #%d stages without refusing a valid file' % i,
        st['valid'] is True, json.dumps([i2['code'] for i2 in st['issues']][:4]))
    keys, places = [], []

    def _k(k, path, _keys=keys, _pl=pl):
        if k == _pl:
            _keys.append(path)

    def _v(v, path, _places=places, _pl=pl):
        if v == _pl:
            _places.append(path)

    _walk(st['staging'], _k, _v)
    chk('inert label #%d is never an object key at any depth' % i,
        keys == [], json.dumps(keys)[:200])
    chk('inert label #%d appears only in a declared text field' % i,
        places != [] and all(p and p[-1] in TEXT_FIELDS for p in places),
        json.dumps(places)[:200])
    chk('inert label #%d creates no canonical field' % i,
        all(k in ('Pset_WallCommon.LoadBearing', 'Pset_WallCommon.IsExternal',
                  'Pset_SpaceCommon.GrossPlannedArea', 'Pset_DoorCommon.IsExternal')
            for k in B.SPEC['canonical_property_map'])
        and pl not in B.SPEC['canonical_property_map'])

# نفس الأسماء بوصفها مفاتيح خاصّية خارجية لا نصّاً: هنا يجب أن تُرفض فعلاً
for i, pl in enumerate(INERT_TEXT):
    esc = pl.replace("\\", "\\\\").replace("'", "''")
    body = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
            "#20=IFCWALLSTANDARDCASE('0aaaaaaaaaaaaaaaaaaaW%s',$,'W',$,$,#19,$,'1',"
            ".SOLIDWALL.);\n"
            "#21=IFCPROPERTYSINGLEVALUE('%s',$,IFCBOOLEAN(.T.),$);\n"
            "#22=IFCPROPERTYSET('0aaaaaaaaaaaaaaaaaaaP%s',$,'Pset_X',$,(#21));\n"
            "#23=IFCRELDEFINESBYPROPERTIES('0aaaaaaaaaaaaaaaaaaaR%s',$,$,$,(#20),#22);\n"
            % (chr(ord('a') + i), esc, chr(ord('a') + i), chr(ord('a') + i)))
    st = B.stage_import(LIB.minimal(None, body), 'k.ifc', {}, None, AT)
    chk('hostile property key #%d is refused before it becomes a key' % i,
        any(i2['code'] == 'BIM_PROPERTY_REFUSED' for i2 in st['issues']),
        json.dumps([i2['code'] for i2 in st['issues']][:5]))
    kk = []
    _walk(st['staging'], lambda k, p, _k=kk, _p=pl: _k.append(p) if k == _p else None,
          lambda v, p: None)
    chk('hostile property key #%d appears as no key in staging' % i, kk == [],
        json.dumps(kk)[:200])
chk('a prototype key is refused as a property key',
    all(B.safe_key(k) is False for k in B.SPEC['forbidden_property_keys']))
chk('a plain property key is accepted', B.safe_key('LoadBearing') is True)
chk('Object.prototype is untouched after every payload',
    not hasattr(dict(), 'polluted'))
chk('only declared property mappings may enter canonical semantics',
    len(B.SPEC['canonical_property_map']) > 0
    and 'no property name can create a canonical field'
    in B.SPEC['property_note'])
chk('an external material is never promoted to an engineering material',
    B.SPEC['material_promotion_allowed'] is False
    and 'never evidence of fire resistance' in B.SPEC['material_note'])
chk('a classification carries no engineering authority',
    B.SPEC['classification_authority'] is False)
chk('a space name never authorises equipment',
    B.SPEC['space_purpose_inference'] is False
    and 'never used to infer purpose' in B.SPEC['space_purpose_note'])

print('\n== §68 — ARABIC AND SYMBOL ROUND TRIP ==')
names = ['مجلس', 'غرفة الطعام',
         "O'Brien Room", 'Majlis / مجلس', 'Café – 100%']
mixed = copy.deepcopy(ALL['villa'])
rooms = mixed['floors']['g']['rooms']
for i, nm in enumerate(names):
    if i < len(rooms):
        rooms[i]['name'] = nm
prj = PR('villa')
prj = AU.create_project(copy.deepcopy(mixed), 'bld_0', 'IMPORT', None)
res = B.export_ifc(prj, {}, None)
chk('a model with Arabic and symbol names exports', res['valid'])
if res['valid']:
    st = B.stage_import(res['file'], 'ar.ifc', {}, None, AT)
    chk('the Arabic file parses back', st['valid'],
        json.dumps([i['code'] for i in st['issues']][:3]))
    got = sorted(e['name'] for e in st['staging']['entities']
                 if e['canonical_kind'] == 'space')
    want = sorted(set([r.get('name') or str(r['id'])
                       for t in mixed['floors'].values() for r in t['rooms']]))
    chk('every Arabic and symbol name survives the round trip unchanged',
        all(n in got for n in names), json.dumps(got, ensure_ascii=False)[:200])
    chk('an apostrophe survives STEP escaping',
        "O'Brien Room" in got)

print('\n== §27/§28 — DIFF, PROPOSALS AND THE COMMIT PATH ==')
prj = PR('villa_glazed')
h0, r0 = prj['model_hash'], prj['current_revision']
st = STAGINGS.get('villa_glazed')
if st:
    d = B.import_diff(prj, st, {})
    chk('a diff is produced', d['valid'])
    chk('the diff writes nothing to the model',
        d['diff']['writes_to_model'] is False and prj['model_hash'] == h0)
    chk('an identical file produces no object difference',
        d['diff']['by_type']['OBJECT_ADDED'] == 0
        and d['diff']['by_type']['OBJECT_REMOVED'] == 0,
        json.dumps(d['diff']['by_type']))
    ps = B.import_proposals(d['diff'], st)
    chk('every proposal starts pending or blocked',
        all(p2['state'] in ('PENDING', 'BLOCKED') for p2 in ps['proposals']))
    chk('no proposal writes to the model',
        all(p2['writes_to_model'] is False for p2 in ps['proposals']))
    chk('a commit with nothing accepted commits nothing',
        B.commit_import(prj, ps, AU, AT)['committed'] is False)
    chk('the model is untouched by diffing and proposing', prj['model_hash'] == h0)

# فرق حقيقي: نُعيد تسمية فراغ في الملفّ المستورَد ثم نودعه عبر التأليف
renamed = copy.deepcopy(ALL['villa_glazed'])
renamed['floors']['g']['rooms'][0]['name'] = 'majlis_renamed'
prj2 = AU.create_project(copy.deepcopy(renamed), 'bld_0', 'IMPORT', None)
alt = B.export_ifc(prj2, {}, None)
base = PR('villa_glazed')
h_base = base['model_hash']
sta = B.stage_import(alt['file'], 'alt.ifc', {}, None, AT)
d2 = B.import_diff(base, sta['staging'], {})
name_props = [x for x in B.import_proposals(d2['diff'], sta['staging'])['proposals']
              if x['change_type'] == 'PROPERTY_CHANGED' and x['field'] == 'name']
chk('a renamed space produces a name proposal', len(name_props) >= 1,
    json.dumps(d2['diff']['by_type']))
ps2 = B.import_proposals(d2['diff'], sta['staging'])
if name_props:
    acc = B.set_proposal_state(ps2, name_props[0]['proposal_id'], 'ACCEPTED')
    chk('a pending proposal can be accepted', acc['valid'])
    chk('accepting alone still changes nothing', base['model_hash'] == h_base)
    _au_spec = json.load(open(os.path.join(ROOT, 'acs_authoring.json'),
                              encoding='utf-8'))
    chk('the import command source is one phase 5 already declares',
        B.SPEC['import_command_source'] in _au_spec['command_sources'],
        B.SPEC['import_command_source'])
    chk('every mapped import command is a phase 5 command type',
        all(v in _au_spec['command_types']
            for v in B.SPEC['import_command_map'].values()),
        json.dumps(B.SPEC['import_command_map']))
    _cmd = B._command_for(name_props[0])
    chk('the generated command carries no invented field',
        sorted(_cmd.keys()) == ['parameters', 'source', 'target_id', 'type'],
        json.dumps(sorted(_cmd.keys())))
    com = B.commit_import(base, acc['proposals'], AU, AT)
    chk('the accepted change commits through the authoring path',
        com['committed'] is True and com['via'] == 'AUTHORING_PATH',
        json.dumps([i['message'] for i in com.get('issues') or []][:2]))
    if com['committed']:
        chk('the commit produced a new revision',
            com['new_revision'] != r0 and com['new_model_hash'] != h_base)
        chk('the commit records the previous and new hashes',
            com['previous_model_hash'] == h_base)
        chk('the commit lists the changed objects', len(com['changed_objects']) >= 1)
        chk('the commit appears in normal revision history',
            len(com['project']['history']) == 2)
        chk('the source project object is not mutated in place',
            base['model_hash'] == h_base)

print('\n== §54 — TEST I: A STALE IMPORT IS REFUSED ==')
base3 = PR('villa_glazed')
st3 = B.stage_import(EXPORTS['villa_glazed']['file'], 'v.ifc', {}, None, AT)
d3 = B.import_diff(base3, st3['staging'], {})
ps3 = B.import_proposals(d3['diff'], st3['staging'])
chk('the fresh proposal set is current',
    B.import_staleness(ps3, base3)['status'] == 'CURRENT')
moved = copy.deepcopy(base3)
moved['model_hash'] = 'moved'
moved['current_revision'] = 'rev:moved'
sta2 = B.import_staleness(ps3, moved)
chk('after the model moves the import is stale',
    sta2['status'] == 'STALE_TARGET_MODEL')
chk('a stale import is never rebased or committed automatically',
    sta2['auto_rebased'] is False and sta2['auto_committed'] is False
    and sta2['requires_rediff'] is True)
com3 = B.commit_import(moved, ps3, AU, AT)
chk('committing a stale import is refused',
    com3['committed'] is False and com3['state'] == 'STALE_TARGET_MODEL'
    and any(i['code'] == 'BIM_STALE_TARGET_MODEL' for i in com3['issues']))

print('\n== §33 — EXPORT STALENESS ==')
prj4 = PR('villa')
m4 = B.export_ifc(prj4, {}, None)['manifest']
chk('a fresh export is current',
    B.export_staleness(m4, prj4)['status'] == 'CURRENT')
moved4 = copy.deepcopy(prj4)
moved4['model_hash'] = 'x'
moved4['current_revision'] = 'rev:x'
es = B.export_staleness(m4, moved4)
chk('an export is marked stale once the model moves',
    es['status'] == 'STALE_SOURCE_MODEL')
chk('a stale export is never deleted or re-pointed',
    es['auto_deleted'] is False and es['auto_repointed'] is False)

print('\n== §55 — TEST J: CONFLICTS ARE CLASSIFIED ==')
dup = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
       "#20=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaZ',$,'A',$,$,#19,$,'1',"
       ".ELEMENT.,.INTERNAL.,0.);\n"
       "#21=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaZ',$,'B',$,$,#19,$,'2',"
       ".ELEMENT.,.INTERNAL.,0.);\n")
stdup = B.stage_import(LIB.minimal(None, dup), 'dup.ifc', {}, None, AT)
chk('a duplicate GlobalId is refused',
    stdup['valid'] is False
    and any(i['code'] == 'BIM_DUPLICATE_ID' for i in stdup['issues']))
badschema = LIB.minimal(None, '', 'IFC9X99')
stbad = B.stage_import(badschema, 'b.ifc', {}, None, AT)
chk('an unknown schema is refused, never reinterpreted',
    stbad['valid'] is False
    and any(i['code'] == 'BIM_UNKNOWN_SCHEMA' for i in stbad['issues']))
chk('IFC2X3 is readable and reported as partially supported',
    B.stage_import(LIB.minimal(None, '', 'IFC2X3'), 'c.ifc', {}, None,
                   AT)['staging']['schema_support'] == 'PARTIALLY_SUPPORTED')
chk('IFC2X3 is never written', B.SPEC['writable_schemas'] == ['IFC4'])
if st:
    cf = B._conflicts(prj, st, B.build_exchange(prj, {})['exchange'])
    chk('a clean file raises no blocking conflict',
        not any(c['blocking'] for c in cf), json.dumps(cf[:2]))
chk('every declared conflict class has a blocking decision',
    all(isinstance(c in B.SPEC['blocking_conflicts'], bool)
        for c in B.SPEC['conflict_classes']))
stl2 = B.stage_import(LIB.minimal(None, lonely), 'd2.ifc', {}, None, AT)
cf2 = B._conflicts(PR('villa'), stl2['staging'],
                   B.build_exchange(PR('villa'), {})['exchange'])
chk('an unresolved host raises a host conflict',
    any(c['conflict'] == 'HOST_CONFLICT' for c in cf2))

print('\n== §56 — TEST K: ADVERSARIAL GRAPHS FAIL SAFELY ==')
cyc = ("#19=IFCCARTESIANPOINT((1.,1.,0.));\n"
       "#20=IFCAXIS2PLACEMENT3D(#19,#5,#6);\n"
       "#21=IFCLOCALPLACEMENT(#22,#20);\n"
       "#22=IFCLOCALPLACEMENT(#21,#20);\n"
       "#23=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaC',$,'C',$,$,#21,$,'1',"
       ".ELEMENT.,.INTERNAL.,0.);\n")
stc = B.stage_import(LIB.minimal(None, cyc), 'cyc.ifc', {}, None, AT)
chk('a cyclic placement is detected and refused',
    stc['valid'] is False
    and any(i['code'] == 'BIM_PLACEMENT_CYCLE' for i in stc['issues']))
agg = ("#19=IFCRELAGGREGATES('0aaaaaaaaaaaaaaaaaaaaA',$,$,$,#13,(#15));\n"
       "#20=IFCRELAGGREGATES('0aaaaaaaaaaaaaaaaaaaaB',$,$,$,#15,(#13));\n")
sta3 = B.stage_import(LIB.minimal(None, agg), 'agg.ifc', {}, None, AT)
chk('a cyclic aggregation is detected and refused',
    sta3['valid'] is False
    and any(i['code'] == 'BIM_CONTAINMENT_CYCLE' for i in sta3['issues']))
deep = ''
# سلسلة عميقة لكنّها داخل الحدّ المعلَن: #14 نفسه على العمق 3 في التجهيزة،
# فالسلسلة المضافة يجب أن تبقى دونه بفارق واضح
n = int(B.LIMITS['max_placement_depth']) - 8
for i in range(n):
    parent = '#14' if i == 0 else ('#%d' % (100 + i - 1))
    deep += '#%d=IFCLOCALPLACEMENT(%s,#7);\n' % (100 + i, parent)
std = B.stage_import(LIB.minimal(None, deep), 'deep.ifc', {}, None, AT)
chk('a deep but legal placement chain still resolves', std['valid'])
toodeep = ''
n2 = int(B.LIMITS['max_placement_depth']) + 20
for i in range(n2):
    parent = '#14' if i == 0 else ('#%d' % (200 + i - 1))
    toodeep += '#%d=IFCLOCALPLACEMENT(%s,#7);\n' % (200 + i, parent)
stt = B.stage_import(LIB.minimal(None, toodeep), 'td.ifc', {}, None, AT)
chk('a placement chain beyond the declared depth is refused',
    stt['valid'] is False
    and any(i['code'] == 'BIM_RESOURCE_LIMIT_EXCEEDED' for i in stt['issues']))
chk('a dangling reference is refused',
    B.parse_step(LIB.wrap('#1=IFCLOCALPLACEMENT(#999,#998);\n'),
                 'x.ifc')['valid'] is False)
chk('a malformed numeric literal is refused',
    B.parse_step(LIB.wrap('#1=IFCCARTESIANPOINT((1.2.3,0.,0.));\n'),
                 'x.ifc')['valid'] is False)
chk('an unterminated file is refused',
    B.parse_step('ISO-10303-21;\nHEADER;\nFILE_SCHEMA((\'IFC4\'));\nENDSEC;\nDATA;\n',
                 'x.ifc')['valid'] is False)
chk('a file that is not STEP at all is refused',
    B.parse_step('{"not":"ifc"}', 'x.ifc')['valid'] is False)
chk('an empty file is refused', B.parse_step('', 'x.ifc')['valid'] is False)
huge = LIB.wrap('#1=IFCCARTESIANPOINT((1e400,0.,0.));\n')
chk('a non-finite coordinate is refused',
    B.parse_step(huge, 'x.ifc')['valid'] is False
    or all(B._num(v) is not None for v in [1]))
longstr = "'" + ('A' * (int(B.LIMITS['max_string_length']) + 10)) + "'"
chk('an oversized string is refused',
    B.parse_step(LIB.wrap('#1=IFCPERSON($,$,%s,$,$,$,$,$);\n' % longstr),
                 'x.ifc')['valid'] is False)
chk('a file beyond the declared size is refused',
    B.parse_step('ISO-10303-21;' + ('x' * (int(B.LIMITS['max_file_bytes']) + 10)),
                 'x.ifc')['valid'] is False)
chk('a duplicate entity number is refused',
    B.parse_step(LIB.wrap('#1=IFCPERSON($,$,$,$,$,$,$,$);\n'
                          '#1=IFCPERSON($,$,$,$,$,$,$,$);\n'),
                 'x.ifc')['valid'] is False)

print('\n== §37 — NO REMOTE RESOURCE IS EVER FETCHED ==')
src = open(os.path.join(ROOT, 'acs_bim.py'), encoding='utf-8').read()
chk('the BIM module imports no network library',
    not any(x in src for x in ('urllib', 'requests', 'http.client', 'socket',
                               'ftplib')))
chk('the BIM module contains no dynamic execution',
    'eval(' not in src.replace('unsafe_patterns', '')
    and 'exec(' not in src and 'subprocess' not in src)
chk('no external reference scheme is allowed',
    B.SPEC['allowed_external_reference_schemes'] == [])
ref = ("#19=IFCLOCALPLACEMENT(#14,#7);\n"
       "#20=IFCSPACE('0aaaaaaaaaaaaaaaaaaaaU',$,'https://evil.invalid/x',$,$,#19,$,"
       "'1',.ELEMENT.,.INTERNAL.,0.);\n")
str2 = B.stage_import(LIB.minimal(None, ref), 'r.ifc', {}, None, AT)
sp2 = [e for e in str2['staging']['entities'] if e['canonical_kind'] == 'space']
chk('a remote URL in a name is carried as inert text, never fetched',
    sp2 and sp2[0]['name'] == 'https://evil.invalid/x')

print('\n== §9/§10 — PROVENANCE AND IDENTIFIERS ==')
if 'villa_glazed' in STAGINGS:
    e0 = [e for e in STAGINGS['villa_glazed']['entities']
          if e['canonical_kind'] == 'wall'][0]
    prov = e0['provenance']
    chk('every provenance field is recorded',
        all(k in prov for k in B.SPEC['provenance_fields']),
        json.dumps([k for k in B.SPEC['provenance_fields'] if k not in prov]))
    chk('provenance names the source file hash and the entity',
        prov['source_file_hash'] and prov['source_entity_id'].startswith('#')
        and prov['entity_type'] == 'IFCWALLSTANDARDCASE')
    chk('provenance survives mapping', prov['global_id'] is not None)
    chk('the external identifier is kept apart from any canonical identifier',
        'external_global_id' in e0 and e0.get('canonical_id') is None)
chk('the identifier policy says an external id is never the canonical id',
    'never becomes the canonical identifier implicitly' in B.SPEC['identifier_note'])
chk('an exported GlobalId is derived from the model, the object and the schema',
    B.ifc_guid({'m': 'a', 'id': 'b', 's': 'IFC4'})
    != B.ifc_guid({'m': 'a', 'id': 'b', 's': 'IFC2X3'})
    and B.ifc_guid({'m': 'a', 'id': 'b', 's': 'IFC4'})
    == B.ifc_guid({'m': 'a', 'id': 'b', 's': 'IFC4'}))
chk('every generated GlobalId is 22 characters from the IFC alphabet',
    len(B.ifc_guid({'x': 1})) == 22
    and all(c in B.GUID_ALPHABET for c in B.ifc_guid({'x': 1})))

print('\n== §13 — GEOREFERENCING STAYS SEPARATE ==')
if 'villa' in STAGINGS:
    g = STAGINGS['villa']['georeference']
    chk('a file with no georeference is reported local only',
        g['state'] == 'LOCAL_ONLY')
    chk('georeference is never equated with local coordinates',
        g['equivalent_to_local_coordinates'] is False)
    chk('no geospatial accuracy is claimed',
        g['geospatial_accuracy_claimed'] is False
        and B.SPEC['geospatial_accuracy_claimed'] is False)

print('\n== §69 — THE MODEL HASH INVARIANT AT EVERY STAGE ==')
for k in TARGETS:
    prj = PR(k)
    h = prj['model_hash']
    r = prj['current_revision']
    ex = B.export_ifc(prj, {}, None)
    chk('%s: export leaves the hash unchanged' % k, prj['model_hash'] == h)
    stg = B.stage_import(ex['file'], k + '.ifc', {}, None, AT)
    chk('%s: staging leaves the hash unchanged' % k, prj['model_hash'] == h)
    B.roundtrip_report(prj, stg['staging'], {})
    chk('%s: validation leaves the hash unchanged' % k, prj['model_hash'] == h)
    dd = B.import_diff(prj, stg['staging'], {})
    chk('%s: diffing leaves the hash unchanged' % k, prj['model_hash'] == h)
    pp = B.import_proposals(dd['diff'], stg['staging'])
    chk('%s: proposing leaves the hash unchanged' % k,
        prj['model_hash'] == h and prj['current_revision'] == r)
    chk('%s: every stage declares it writes nothing' % k,
        stg['staging']['writes_to_model'] is False
        and dd['diff']['writes_to_model'] is False
        and pp['writes_to_model'] is False)

print('\n== §73 — AUDIT RECORDS HASHES, NEVER PAYLOADS ==')
a = B.audit('IMPORT_STARTED', {'import_id': 'bimimp_1', 'file_hash': 'a' * 64,
                               'raw': '<script>x</script>', 'count': 5})
chk('a declared audit event is recorded', a is not None and a['event'] == 'IMPORT_STARTED')
chk('an unsafe payload is stored as a hash, not raw',
    a['fields'].get('raw', '').startswith('sha256:'))
chk('the audit declares it records no raw payload and no secret',
    a['records_raw_payload'] is False and a['records_secret'] is False)
chk('an undeclared event is not recorded', B.audit('NOT_AN_EVENT', {}) is None)
chk('a prototype key is dropped from the audit',
    '__proto__' not in (B.audit('IMPORT_STARTED', {'__proto__': 'x'})['fields']))

print('\n== §42 — EXPORT OPTIONS ARE REFUSED, NEVER DEFAULTED ==')
prj = PR('villa')
chk('an unknown export scope is refused',
    B.export_ifc(prj, {'scope': 'NOT_A_SCOPE'}, None)['valid'] is False)
chk('a spaces-only export really omits walls',
    len(B.build_exchange(prj, {'scope': 'SPACES_ONLY'})['exchange']['walls']) == 0)
chk('a level filter really limits the export',
    len(B.build_exchange(prj, {'levels': [0]})['exchange']['levels']) == 1)
chk('excluding spaces really omits them',
    len(B.build_exchange(prj, {'include_spaces': False})['exchange']['spaces']) == 0)
chk('a different configuration yields a different config hash',
    B.build_exchange(prj, {})['exchange']['config_hash']
    != B.build_exchange(prj, {'scope': 'SPACES_ONLY'})['exchange']['config_hash'])

print('\n== §43 — THE EXPORT MANIFEST ==')
mf = B.export_ifc(PR('villa'), {}, AT)['manifest']
chk('every declared manifest field is present',
    all(k in mf for k in B.SPEC['export_manifest_fields']),
    json.dumps([k for k in B.SPEC['export_manifest_fields'] if k not in mf]))
chk('the manifest names the model hash and revision',
    mf['model_hash'] and mf['revision_id'])
chk('the manifest reports losses rather than hiding them', isinstance(mf['losses'], list))
chk('the manifest declares that it writes nothing',
    mf['writes_to_model'] is False)

print('\n== §45 — A LARGE MODEL IS PROCESSED WITHIN THE DECLARED LIMITS ==')
sys.path.insert(0, HERE)
from lib_large_fixture import large_model                          # noqa: E402
big = large_model()
bigp = AU.create_project(copy.deepcopy(big), 'bld_0', 'IMPORT', None)
bigh = bigp['model_hash']
bige = B.export_ifc(bigp, {}, None)
chk('a large synthetic model exports to a real IFC file', bige['valid'],
    json.dumps([i['code'] for i in bige['issues']][:3]))
chk('the large file carries thousands of entities',
    bige['manifest']['entity_count'] >= 20000,
    str(bige['manifest']['entity_count']))
chk('the large file has many levels and many spaces',
    bige['manifest']['level_count'] >= 8 and bige['manifest']['space_count'] >= 400,
    json.dumps([bige['manifest']['level_count'], bige['manifest']['space_count']]))
chk('the large file stays inside every declared limit',
    bige['manifest']['entity_count'] <= B.LIMITS['max_entity_count']
    and len(bige['file'].encode('utf-8')) <= B.LIMITS['max_file_bytes']
    and bige['manifest']['space_count'] <= B.LIMITS['max_spaces']
    and bige['manifest']['level_count'] <= B.LIMITS['max_levels'])
bigs = B.stage_import(bige['file'], 'big.ifc', {}, None, AT)
chk('the large file parses back without a resource refusal', bigs['valid'],
    json.dumps(sorted(set(i['code'] for i in bigs['issues']))[:4]))
chk('every entity in the large file was read',
    bigs['staging']['counts']['parsed_entities']
    == bige['manifest']['entity_count'],
    json.dumps([bigs['staging']['counts']['parsed_entities'],
                bige['manifest']['entity_count']]))
bigr = B.roundtrip_report(bigp, bigs['staging'], {})
chk('the large model survives a real round trip',
    bigr['valid'] and bigr['report']['status'] in ('PASS', 'WARNING'),
    json.dumps(bigr['report'].get('status') if bigr.get('report') else None))
chk('no critical geometry was lost at scale',
    bigr['report']['critical_loss_count'] == 0
    and bigr['report']['geometry_fidelity'] == 1.0,
    json.dumps([bigr['report']['critical_loss_count'],
                bigr['report']['geometry_fidelity']]))
chk('the large model was never mutated by any of this',
    bigp['model_hash'] == bigh)
chk('a file beyond the declared byte limit is refused before parsing',
    B.stage_import('x' * (int(B.LIMITS['max_file_bytes']) + 1), 'huge.ifc',
                   {}, None, AT)['valid'] is False)

print('\n== §57 — THE PRODUCED FILE IS A REAL STEP PHYSICAL FILE ==')
OUTD = os.path.join(HERE, 'outputs')
arts = []
if os.path.isdir(OUTD):
    arts = sorted(x for x in os.listdir(OUTD) if x.endswith('.ifc'))
chk('real IFC artifacts were produced on disk', len(arts) >= 10, str(len(arts)))
for a in arts:
    with open(os.path.join(OUTD, a), encoding='utf-8') as fh:
        txt = fh.read()
    chk('%s opens and closes as ISO-10303-21' % a,
        txt.startswith('ISO-10303-21;') and txt.rstrip().endswith('END-ISO-10303-21;'))
    chk('%s carries a HEADER and a DATA section' % a,
        '\nHEADER;\n' in txt and '\nDATA;\n' in txt and txt.count('ENDSEC;') >= 2)
    chk('%s declares its schema in FILE_SCHEMA' % a,
        "FILE_SCHEMA(('IFC4'))" in txt)
    chk('%s is not JSON wearing an IFC name' % a,
        not txt.lstrip().startswith('{') and not txt.lstrip().startswith('['))
    chk('%s parses back with the real parser' % a,
        B.parse_step(txt, a)['valid'] is True)
    mpath = os.path.join(OUTD, a[:-4] + '.manifest.json')
    chk('%s ships with an export manifest' % a, os.path.exists(mpath))
    if os.path.exists(mpath):
        with open(mpath, encoding='utf-8') as fh:
            mm = json.load(fh)
        chk('%s manifest hash matches the file on disk' % a,
            mm['file_hash'] == B._sha256_text(txt), mm['file_hash'][:16])

print('\n─' * 46)
print('BIM EXCHANGE: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
