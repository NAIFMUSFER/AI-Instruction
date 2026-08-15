# -*- coding: utf-8 -*-
"""جانب بايثون من تكافؤ المرحلة 9.

يبني التوثيق نفسه على النماذج نفسها ويكتب النتيجة القانونية إلى JSON يقارنه
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

import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_docs_fixtures as LIB                                   # noqa: E402

OUT = os.environ.get('ACS_PARITY_DOCS_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_docs_py.json')
AT = '2026-01-01T00:00:00Z'

ALL = LIB.all_models()
KEYS = sorted(ALL.keys())
SPECS = [
    {'view_type': 'FLOOR_PLAN', 'discipline': 'ARCHITECTURE', 'scale': '1:100',
     'dimension_policy': 'FULL_CHAIN', 'annotation_policy': 'TAGS_AND_NOTES'},
    {'view_type': 'ELEVATION', 'orientation': 'NORTH', 'scale': '1:100'},
    {'view_type': 'ELEVATION', 'orientation': 'EAST', 'scale': '1:200'},
    {'view_type': 'SECTION', 'cut_plane': {'axis': 'x', 'at': 3.0},
     'view_depth': 6.0, 'scale': '1:100'},
    {'view_type': 'SECTION', 'cut_plane': {'axis': 'z', 'at': 2.0},
     'view_depth': 4.0, 'dimension_policy': 'OVERALL_AND_SPACES'},
    {'view_type': 'STRUCTURAL_PLAN', 'discipline': 'STRUCTURE', 'scale': '1:100'},
    {'view_type': 'MEP_PLAN', 'discipline': 'MECHANICAL', 'scale': '1:100'},
    {'view_type': 'FLS_PLAN', 'discipline': 'FIRE_PROTECTION', 'scale': '1:100'},
    {'view_type': 'COORDINATION_PLAN', 'discipline': 'COORDINATION'},
    {'view_type': 'SITE_PLAN', 'discipline': 'ARCHITECTURE'},
    {'view_type': 'THREE_D_REFERENCE'},
    {'view_type': 'NOT_A_VIEW'},
]
NOTES = [{'text': 'a user note'}, {'text': '__proto__'}, {'text': 'مجلس'}]

out = {}
for key in KEYS:
    model = copy.deepcopy(ALL[key])
    before = D._canon(model)
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    src = D.sources(project)
    lv = src['arch']['levels'][0]['id'] if src['arch']['levels'] else None
    entry = {'model_hash': project['model_hash'], 'level_id': lv}
    views, drawings = [], {}
    vlist = []
    for i, sp in enumerate(SPECS):
        s = dict(sp)
        if 'level_id' not in s and s['view_type'] in (
                'FLOOR_PLAN', 'STRUCTURAL_PLAN', 'MEP_PLAN', 'FLS_PLAN',
                'COORDINATION_PLAN', 'SITE_PLAN'):
            s['level_id'] = lv
        r = D.build_view(project, s, src, NOTES)
        rec = {'valid': r['valid'],
               'issues': sorted(i2['code'] for i2 in r['issues'])}
        if r['valid']:
            rec['view'] = r['view']
            rec['geometry'] = r['geometry']
            rec['dimensions'] = r['dimensions']
            rec['annotations'] = r['annotations']
            svg = D.view_svg(r['view'], r['geometry'], r['dimensions'],
                             r['annotations'], {'paper_size': 'A3'})
            rec['svg'] = svg['svg']
            rec['svg_hash'] = svg['file_hash']
            rec['svg_bytes'] = svg['byte_length']
            rec['ops'] = D.draw_ops(r['view'], r['geometry'], r['dimensions'],
                                    r['annotations'], 420.0, 297.0, 12.0,
                                    'MONOCHROME')
            drawings[r['view']['view_id']] = rec['ops']
            views.append(r['view'])
            vlist.append(r)
        vlist_key = 'v%02d' % i
        entry[vlist_key] = rec
    entry['schedules'] = {}
    for stype in D.SPEC['schedule_types']:
        sr = D.schedule(project, stype, {}, src)
        entry['schedules'][stype] = {
            'valid': sr['valid'],
            'schedule': sr['schedule'],
            'issues': sorted(i2['code'] for i2 in sr['issues'])}
    entry['quantities'] = D.quantities(project, {}, src)['report']
    byid = {v['view_id']: v for v in views}
    sheets = []
    if views:
        sh = D.compose_sheet(project, {
            'paper_size': 'A3', 'orientation': 'LANDSCAPE',
            'sheet_number': 'A-001', 'sheet_name': 'Plan',
            'title_block': {'project': key, 'status': 'DRAFT'},
            'notes': [{'text': 'sheet note'}],
            'viewports': [{'view_id': views[0]['view_id'], 'x': 10, 'y': 10,
                           'width': 180, 'height': 120}]
            + ([{'view_id': views[1]['view_id'], 'x': 200, 'y': 10,
                 'width': 190, 'height': 120}] if len(views) > 1 else [])},
            byid)
        entry['sheet'] = {'valid': sh['valid'], 'sheet': sh['sheet'],
                          'issues': sorted(i2['code'] for i2 in sh['issues'])}
        if sh['sheet']:
            sheets.append(sh['sheet'])
        collide = D.compose_sheet(project, {
            'paper_size': 'A3', 'sheet_number': 'A-002',
            'viewports': [{'view_id': views[0]['view_id'], 'x': 10, 'y': 10,
                           'width': 180, 'height': 120},
                          {'view_id': views[0]['view_id'], 'x': 100, 'y': 50,
                           'width': 180, 'height': 120}]}, byid)
        entry['sheet_collision'] = sorted(i2['code'] for i2 in collide['issues'])
    entry['title_block_restricted'] = D.title_block(
        project, {'status': 'APPROVED_FOR_CONSTRUCTION'})['title_block']
    doc = D.documentation_project(
        project, views, sheets,
        [entry['schedules'][s]['schedule'] for s in sorted(entry['schedules'])
         if entry['schedules'][s]['schedule']],
        entry['quantities'], [], 'A', None, [])
    entry['document'] = {k: doc[k] for k in
                         ('documentation_id', 'documentation_revision',
                          'model_hash', 'source_revision', 'drawing_index',
                          'legends', 'metadata')}
    entry['pdf'] = ({k: v for k, v in
                     D.sheet_pdf(sheets, drawings, AT).items()
                     if k in ('page_count', 'media_boxes', 'content_streams',
                              'sheet_ids', 'semantic_hash',
                              'cad_interoperability_claimed')}
                    if sheets else None)
    files = [{'file_name': 'plan.svg', 'format': 'SVG',
              'artifact_id': views[0]['view_id'] if views else None,
              'byte_length': 10, 'file_hash': 'abc',
              'generation_mode': 'DETERMINISTIC_VECTOR'},
             {'file_name': '../escape.svg', 'format': 'SVG',
              'byte_length': 1, 'file_hash': 'x'},
             {'file_name': 'doc.json', 'format': 'JSON', 'byte_length': 2,
              'file_hash': 'y', 'generation_mode': 'DETERMINISTIC_PACKAGE'}]
    ex = D.export_package(doc, files, AT)
    entry['export'] = {'valid': ex['valid'], 'package': ex['package'],
                       'manifest': ex['manifest'],
                       'package_hash': ex['package_hash'],
                       'issues': sorted(i2['code'] for i2 in ex['issues'])}
    entry['export_set'] = D.export_set('Permit Review', 'review',
                                       [s['sheet_id'] for s in sheets],
                                       ['SVG', 'PDF', 'DXF'], AT)['export_set']
    entry['staleness'] = {
        'current': D.staleness(views[0], project) if views else None,
        'moved': D.staleness(views[0], dict(project, model_hash='moved',
                                            current_revision='rev:moved'))
        if views else None}
    entry['regenerate'] = D.regenerate(doc, project, AT)
    entry['impact'] = D.impact(doc, project,
                               dict(project, model_hash='moved',
                                    current_revision='rev:moved'))
    entry['model_untouched'] = (D._canon(project['model']) == before
                                and project['model_hash'] == entry['model_hash'])
    out[key] = entry

out['__spec'] = {'schema': D.SPEC['schema'], 'version': D.SPEC['version'],
                 'read_only': D.SPEC['documentation_is_read_only'],
                 'writes_to_model': D.SPEC['writes_to_model'],
                 'limits': D.SPEC['limits'],
                 'line_weights': D.SPEC['line_weights'],
                 'paper_sizes': D.SPEC['paper_sizes'],
                 'scales': D.SPEC['scales']}
out['__safety'] = {
    'unsafe': [[t, D.is_unsafe(t)] for t in LIB.HOSTILE_TEXT + LIB.INERT_TEXT],
    'safe_key': [[k, D.safe_key(k)] for k in
                 ['LoadBearing', '__proto__', 'constructor', 'prototype',
                  '__defineGetter__', 'a b', '']],
    'safe_filename': [[n, D.safe_filename(n)] for n in
                      LIB.HOSTILE_FILENAMES + ['A-001_plan.svg', 'a.pdf']],
    'tags': [[i, D.tag_for(i, 'DOOR')] for i in
             ['bld_0.g.majlis.door_0@0', 'x', 'مجلس']],
}
# التسمية بالفهرس لا بنصّ JSON: تنسيق json.dumps يختلف عن JSON.stringify في
# المسافات وحدها، وهو فرق في تسمية الحالة لا في منطقها
out['__stated'] = [
    ['case_%d' % i, D.stated(t)] for i, t in enumerate(
    [{'value': None, 'source': 'unknown', 'render_fallback': 0.15},
     {'value': 3.0, 'source': 'imported', 'render_fallback': 3.0},
     {'value': None, 'source': None}, None, 2.5,
     {'value': 'x', 'source': 'y'}])]

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, sort_keys=True)
print('parity written: %d models' % len(KEYS))
