# -*- coding: utf-8 -*-
"""قياس أداء توليد التوثيق. أزمنة معالج بالمللي ثانية مع أعداد العناصر بجانب
كل زمن. لا إطار في الثانية، ولا بطاقة رسوميات، ولا رسم ثلاثي الأبعاد."""
import copy
import json
import os
import sys
import time

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


def _t(fn):
    t0 = time.perf_counter()
    r = fn()
    return r, (time.perf_counter() - t0) * 1000.0


def measure(name, model):
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    src, ms_src = _t(lambda: D.sources(project))
    lv = src['arch']['levels'][0]['id']
    vd = D.view_definition(project, {'view_type': 'FLOOR_PLAN', 'level_id': lv,
                                     'dimension_policy': 'FULL_CHAIN',
                                     'annotation_policy': 'TAGS_ONLY'},
                           src['arch'])['view']
    geom, ms_view = _t(lambda: D.plan_geometry(project, vd, src))
    dims, ms_dim = _t(lambda: D.dimensions(project, vd, geom, src))
    anns, ms_ann = _t(lambda: D.annotations(project, vd, geom, None, src))
    _, ms_sec = _t(lambda: D.section_geometry(
        project, D.view_definition(project, {'view_type': 'SECTION',
                                             'cut_plane': {'axis': 'x', 'at': 3.0},
                                             'view_depth': 8.0},
                                   src['arch'])['view'], src))
    _, ms_elev = _t(lambda: D.elevation_geometry(
        project, D.view_definition(project, {'view_type': 'ELEVATION',
                                             'orientation': 'NORTH'},
                                   src['arch'])['view'], src))
    sch, ms_sch = _t(lambda: [D.schedule(project, s, {}, src)
                              for s in D.SPEC['schedule_types']])
    qty, ms_qty = _t(lambda: D.quantities(project, {}, src))
    byid = {vd['view_id']: vd}
    sheet, ms_sheet = _t(lambda: D.compose_sheet(
        project, {'paper_size': 'A3', 'sheet_number': 'A-001',
                  'title_block': {'project': name},
                  'viewports': [{'view_id': vd['view_id'], 'x': 10, 'y': 10,
                                 'width': 180, 'height': 120}]}, byid))
    svg, ms_svg = _t(lambda: D.view_svg(vd, geom, dims, anns, {'paper_size': 'A3'}))
    ops = D.draw_ops(vd, geom, dims, anns, 420.0, 297.0, 12.0, 'MONOCHROME')
    pdf, ms_pdf = _t(lambda: D.sheet_pdf([sheet['sheet']],
                                         {vd['view_id']: ops}, AT))
    doc = D.documentation_project(project, [vd], [sheet['sheet']],
                                  [s['schedule'] for s in sch if s['schedule']],
                                  qty['report'])
    pkg, ms_json = _t(lambda: D.export_package(doc, [], AT))
    rows = sum(s['schedule']['row_count'] for s in sch if s['schedule'])
    return {'model': name,
            'spaces': len(src['arch']['spaces']),
            'walls': len(src['arch']['walls']),
            'openings': len(src['arch']['openings']),
            'drawn_elements': len(geom['elements']),
            'dimensions': dims['counts']['total'],
            'annotations': anns['counts']['total'],
            'schedule_rows': rows,
            'quantities': qty['report']['count'],
            'svg_bytes': svg['byte_length'],
            'pdf_bytes': pdf['byte_length'],
            'ms': {'compile_sources': round(ms_src, 2),
                   'view_generation_ms': round(ms_view, 2),
                   'section_generation_ms': round(ms_sec, 2),
                   'elevation_generation_ms': round(ms_elev, 2),
                   'dimension_ms': round(ms_dim, 2),
                   'annotation_ms': round(ms_ann, 2),
                   'schedule_ms': round(ms_sch, 2),
                   'quantity_ms': round(ms_qty, 2),
                   'sheet_composition_ms': round(ms_sheet, 2),
                   'svg_export_ms': round(ms_svg, 2),
                   'pdf_export_ms': round(ms_pdf, 2),
                   'json_export_ms': round(ms_json, 2)}}


def main():
    models = LIB.all_models()
    rows = []
    for k in ('villa', 'villa_glazed', 'hotel', 'clinic', 'warehouse',
              'office', 'clash_mep', 'villa_fls'):
        rows.append(measure(k, models[k]))
    for n in (100, 500, 1000):
        rows.append(measure('grid_%d' % n, LIB.grid_model(n)))
    hdr = ('%-16s %7s %7s %8s %8s %8s %8s %8s %8s %8s'
           % ('model', 'spaces', 'drawn', 'view', 'section', 'dims', 'sched',
              'qty', 'svg', 'pdf'))
    print('\n== DOCUMENTATION BENCHMARK (CPU, deterministic; no FPS, no GPU) ==')
    print(hdr)
    print('-' * len(hdr))
    for r in rows:
        m = r['ms']
        print('%-16s %7d %7d %7.1fm %7.1fm %7.1fm %7.1fm %7.1fm %7.1fm %7.1fm'
              % (r['model'], r['spaces'], r['drawn_elements'],
                 m['view_generation_ms'], m['section_generation_ms'],
                 m['dimension_ms'], m['schedule_ms'], m['quantity_ms'],
                 m['svg_export_ms'], m['pdf_export_ms']))
    big = rows[-1]
    print('\nlargest model: %d spaces, %d drawn elements, %d schedule rows, '
          'SVG %d bytes, PDF %d bytes'
          % (big['spaces'], big['drawn_elements'], big['schedule_rows'],
             big['svg_bytes'], big['pdf_bytes']))
    print('every timing is milliseconds of CPU work in this sandbox on this run; '
          'no frame rate, no GPU and no 3D rendering is measured or claimed by '
          'this layer.')
    with open(os.path.join(OUT, 'benchmark_docs.json'), 'w',
              encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
