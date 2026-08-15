# -*- coding: utf-8 -*-
"""ينتج مصنوعات توثيق حقيقية: مساقط وواجهات وقطاعات SVG، وجداول، وتقارير
كمّيات، ولوحات مركَّبة، وملفّات PDF، وحزم JSON — مع بيان يربط كل ملفّ ببصمة
النموذج الذي أنتجه. كل ملفّ هنا خرج من المولّد فعلاً؛ لا وصف يحلّ محلّ ملفّ."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_docs_fixtures as LIB                                   # noqa: E402

OUT = os.path.join(HERE, 'outputs')
os.makedirs(OUT, exist_ok=True)
AT = '2026-01-01T00:00:00Z'
ALL = LIB.all_models()

PLAN = [
    ('villa_glazed', {'plans': 'all', 'elevations': ['NORTH', 'SOUTH', 'EAST',
                                                     'WEST'],
                      'sections': [('x', 3.0), ('z', 2.0)],
                      'schedules': ['ROOM_SCHEDULE', 'DOOR_SCHEDULE',
                                    'WINDOW_SCHEDULE']}),
    ('hotel', {'plans': 'first', 'elevations': ['NORTH'],
               'sections': [('x', 6.0)],
               'schedules': ['ROOM_SCHEDULE', 'DOOR_SCHEDULE']}),
    ('clinic', {'plans': 'first', 'elevations': [], 'sections': [],
                'schedules': ['ROOM_SCHEDULE', 'DOOR_SCHEDULE']}),
    ('warehouse', {'plans': 'first', 'elevations': [], 'sections': [],
                   'schedules': ['ROOM_SCHEDULE']}),
    ('clash_mep', {'plans': 'first', 'elevations': [], 'sections': [],
                   'schedules': ['COLUMN_SCHEDULE', 'BEAM_SCHEDULE',
                                 'FOUNDATION_SCHEDULE',
                                 'MEP_EQUIPMENT_SCHEDULE'],
                   'disciplines': ['STRUCTURE', 'MECHANICAL', 'COORDINATION']}),
    ('villa_fls', {'plans': 'first', 'elevations': [], 'sections': [],
                   'schedules': ['FLS_DEVICE_SCHEDULE', 'FLS_SIGN_SCHEDULE'],
                   'disciplines': ['FIRE_PROTECTION']}),
]

manifest_rows = []


def _write(name, text, mode='w'):
    path = os.path.join(OUT, name)
    with open(path, mode, encoding=None if 'b' in mode else 'utf-8') as f:
        f.write(text)
    return os.path.getsize(path)


for key, cfg in PLAN:
    project = AU.create_project(copy.deepcopy(ALL[key]), 'bld_0', 'IMPORT', None)
    h0 = project['model_hash']
    src = D.sources(project)
    levels = src['arch']['levels']
    specs = []
    lvs = levels if cfg['plans'] == 'all' else levels[:1]
    for l in lvs:
        specs.append({'view_type': 'FLOOR_PLAN', 'level_id': l['id'],
                      'discipline': 'ARCHITECTURE', 'scale': '1:100',
                      'dimension_policy': 'FULL_CHAIN',
                      'annotation_policy': 'TAGS_ONLY'})
    for d in cfg.get('disciplines', []):
        vt = {'STRUCTURE': 'STRUCTURAL_PLAN', 'MECHANICAL': 'MEP_PLAN',
              'FIRE_PROTECTION': 'FLS_PLAN',
              'COORDINATION': 'COORDINATION_PLAN'}[d]
        for l in levels:
            specs.append({'view_type': vt, 'level_id': l['id'], 'discipline': d,
                          'scale': '1:100', 'annotation_policy': 'TAGS_ONLY'})
    for o in cfg['elevations']:
        specs.append({'view_type': 'ELEVATION', 'orientation': o,
                      'scale': '1:100'})
    for ax, at in cfg['sections']:
        specs.append({'view_type': 'SECTION',
                      'cut_plane': {'axis': ax, 'at': at},
                      'view_depth': 8.0, 'scale': '1:100'})
    views, drawings, built = [], {}, []
    for sp in specs:
        r = D.build_view(project, sp, src)
        if not r['valid']:
            continue
        v = r['view']
        label = v['view_type'].lower()
        if v.get('level_id'):
            label += '_' + str(v['level_id']).split('.')[-1]
        if v.get('orientation'):
            label += '_' + v['orientation'].lower()
        if v.get('cut_plane'):
            label += '_%s%s' % (v['cut_plane']['axis'],
                                str(v['cut_plane']['at']).replace('.', 'p'))
        if v['discipline'] != 'ARCHITECTURE':
            label += '_' + v['discipline'].lower()
        fn = '%s_%s.svg' % (key, label)
        svg = D.view_svg(v, r['geometry'], r['dimensions'], r['annotations'],
                         {'paper_size': 'A3', 'mode': 'MONOCHROME'})
        n = _write(fn, svg['svg'])
        manifest_rows.append({'artifact': fn, 'kind': 'VIEW_SVG', 'model': key,
                              'model_hash': h0, 'view_id': v['view_id'],
                              'sheet_id': None, 'file_hash': svg['file_hash'],
                              'byte_length': n,
                              'generation_mode': 'DETERMINISTIC_VECTOR'})
        views.append(v)
        built.append(r)
        drawings[v['view_id']] = D.draw_ops(v, r['geometry'], r['dimensions'],
                                            r['annotations'], 420.0, 297.0,
                                            12.0, 'MONOCHROME')
    scheds = []
    for stype in cfg['schedules']:
        sr = D.schedule(project, stype, {}, src)
        if not sr['valid']:
            continue
        fn = '%s_%s.json' % (key, stype.lower())
        text = json.dumps(sr['schedule'], ensure_ascii=False, indent=1,
                          sort_keys=True)
        n = _write(fn, text)
        manifest_rows.append({'artifact': fn, 'kind': 'SCHEDULE', 'model': key,
                              'model_hash': h0,
                              'view_id': sr['schedule']['schedule_id'],
                              'sheet_id': None,
                              'file_hash': D._sha256_text(text),
                              'byte_length': n,
                              'generation_mode': 'DETERMINISTIC_TABLE'})
        scheds.append(sr['schedule'])
    qty = D.quantities(project, {}, src)['report']
    fn = '%s_quantities.json' % key
    text = json.dumps(qty, ensure_ascii=False, indent=1, sort_keys=True)
    n = _write(fn, text)
    manifest_rows.append({'artifact': fn, 'kind': 'QUANTITY_REPORT',
                          'model': key, 'model_hash': h0,
                          'view_id': qty['report_id'], 'sheet_id': None,
                          'file_hash': D._sha256_text(text), 'byte_length': n,
                          'generation_mode': 'DETERMINISTIC_TABLE'})
    byid = {v['view_id']: v for v in views}
    sheets = []
    for i in range(0, len(views), 2):
        vps = [{'view_id': views[i]['view_id'], 'x': 10, 'y': 10,
                'width': 180, 'height': 120}]
        if i + 1 < len(views):
            vps.append({'view_id': views[i + 1]['view_id'], 'x': 200, 'y': 10,
                        'width': 190, 'height': 120})
        sh = D.compose_sheet(project, {
            'paper_size': 'A3', 'orientation': 'LANDSCAPE',
            'sheet_number': 'A-%03d' % (i // 2 + 1),
            'sheet_name': '%s sheet %d' % (key, i // 2 + 1),
            'title_block': {'project': key, 'building': 'bld_0',
                            'sheet_title': 'documentation', 'status': 'DRAFT',
                            'scale': '1:100'},
            'viewports': vps}, byid)
        if sh['sheet']:
            sheets.append(sh['sheet'])
    if sheets:
        pdf = D.sheet_pdf(sheets, drawings, AT)
        fn = '%s_sheets.pdf' % key
        path = os.path.join(OUT, fn)
        with open(path, 'wb') as f:
            f.write(pdf['pdf'])
        manifest_rows.append({'artifact': fn, 'kind': 'SHEET_PDF', 'model': key,
                              'model_hash': h0, 'view_id': None,
                              'sheet_id': ','.join(s['sheet_id'] for s in sheets),
                              'file_hash': pdf['file_hash'],
                              'byte_length': os.path.getsize(path),
                              'generation_mode': 'DETERMINISTIC_VECTOR',
                              'page_count': pdf['page_count']})
    doc = D.documentation_project(project, views, sheets, scheds, qty,
                                  documentation_revision='A', generated_at=AT)
    files = [{'file_name': r['artifact'], 'format':
              ('SVG' if r['kind'] == 'VIEW_SVG'
               else ('PDF' if r['kind'] == 'SHEET_PDF' else 'JSON')),
              'artifact_id': r['view_id'], 'sheet_id': r['sheet_id'],
              'byte_length': r['byte_length'], 'file_hash': r['file_hash'],
              'generation_mode': r['generation_mode']}
             for r in manifest_rows if r['model'] == key]
    pkg = D.export_package(doc, files, AT)
    fn = '%s_documentation.json' % key
    n = _write(fn, json.dumps({'package': pkg['package'],
                               'manifest': pkg['manifest']},
                              ensure_ascii=False, indent=1, sort_keys=True))
    manifest_rows.append({'artifact': fn, 'kind': 'DOCUMENTATION_PACKAGE',
                          'model': key, 'model_hash': h0,
                          'view_id': doc['documentation_id'], 'sheet_id': None,
                          'file_hash': pkg['package_hash'], 'byte_length': n,
                          'generation_mode': 'DETERMINISTIC_PACKAGE'})
    if project['model_hash'] != h0:
        raise SystemExit('documentation changed the model for %s' % key)

manifest_rows.sort(key=lambda r: r['artifact'])
with open(os.path.join(OUT, 'ARTIFACT-MANIFEST.json'), 'w',
          encoding='utf-8') as f:
    json.dump({'generated_at': AT, 'spec_version':
               D.SPEC['documentation_spec_version'],
               'artifacts': manifest_rows, 'count': len(manifest_rows)},
              f, ensure_ascii=False, indent=1, sort_keys=True)

kinds = {}
for r in manifest_rows:
    kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
print('phase 9 artifacts: %d files' % len(manifest_rows))
for k in sorted(kinds):
    print('  %-24s %d' % (k, kinds[k]))
