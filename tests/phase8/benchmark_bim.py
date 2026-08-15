# -*- coding: utf-8 -*-
"""قياس أداء طبقة التبادل على ملفّات IFC حقيقية.

ما يُقاس هنا زمن معالجة نصّ STEP فعلي على معالج هذه البيئة، وتُذكر أعداد
الكيانات بجانب كل زمن. لا يُذكر إطار في الثانية، ولا أداء بطاقة رسوميات، ولا
يُقاس رسم ثلاثي الأبعاد — لا شيء من ذلك يجري في هذه الطبقة أصلاً.
"""
import copy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_bim as B                                               # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_bim_fixtures as LIB                                    # noqa: E402
from lib_large_fixture import large_model                         # noqa: E402

AT = '2026-01-01T00:00:00Z'
OUTDIR = os.path.join(HERE, 'outputs')
os.makedirs(OUTDIR, exist_ok=True)


def _t(fn):
    t0 = time.perf_counter()
    r = fn()
    return r, (time.perf_counter() - t0) * 1000.0


def measure(name, model):
    rows = []
    project, ms = _t(lambda: AU.create_project(copy.deepcopy(model), 'bld_0',
                                               'IMPORT', None))
    built, ms_build = _t(lambda: B.build_exchange(project, {}))
    if not built['valid']:
        return {'model': name, 'valid': False,
                'issues': [i['code'] for i in built['issues']]}
    ex = built['exchange']
    obj = (len(ex['walls']) + len(ex['slabs']) + len(ex['doors'])
           + len(ex['windows']) + len(ex['stairs']) + len(ex['spaces']))
    _, ms_val = _t(lambda: B.validate_exchange(ex))
    ser, ms_ser = _t(lambda: B.serialise_ifc(ex, None))
    text = ser['text']
    path = os.path.join(OUTDIR, name + '.ifc')
    _, ms_write = _t(lambda: open(path, 'w', encoding='utf-8').write(text))
    read, ms_read = _t(lambda: open(path, encoding='utf-8').read())
    parsed, ms_parse = _t(lambda: B.parse_step(read, name + '.ifc'))
    step = parsed['step']
    units, ms_units = _t(lambda: B.resolve_units(step))
    lf = (units['length'] or {}).get('to_metre', 1.0) if units.get('length') else 1.0
    rel, ms_graph = _t(lambda: B.extract_relationships(step))
    _, ms_place = _t(lambda: B.resolve_placements(step, lf))
    staged, ms_stage = _t(lambda: B.stage_import(read, name + '.ifc', {}, None, AT))
    st = staged['staging']
    _, ms_diff = _t(lambda: B.import_diff(project, st, {}))
    _, ms_round = _t(lambda: B.roundtrip_report(project, st, {}))
    rows = {
        'model': name, 'valid': True,
        'canonical_objects': obj,
        'ifc_entities': ser['entity_count'],
        'file_bytes': len(text.encode('utf-8')),
        'parsed_entities': st['counts']['parsed_entities'],
        'staged_entities': st['counts']['entities'],
        'levels': st['counts']['levels'], 'spaces': st['counts']['spaces'],
        'relationships': sum(len(v) for v in rel['relationships'].values())
        if isinstance(rel.get('relationships'), dict) else None,
        'ms': {
            'create_project': round(ms, 2),
            'build_exchange': round(ms_build, 2),
            'validate_exchange': round(ms_val, 2),
            'serialise_step': round(ms_ser, 2),
            'write_file': round(ms_write, 2),
            'read_file': round(ms_read, 2),
            'parse_step': round(ms_parse, 2),
            'resolve_units': round(ms_units, 2),
            'build_relationship_graph': round(ms_graph, 2),
            'resolve_placements': round(ms_place, 2),
            'stage_import_total': round(ms_stage, 2),
            'import_diff': round(ms_diff, 2),
            'roundtrip_compare': round(ms_round, 2),
        },
    }
    return rows


def main():
    models = LIB.models()
    out = []
    for k in sorted(models):
        out.append(measure(k, models[k]))
    big = large_model()
    out.append(measure('synthetic_grid', big))
    bigger = large_model(levels=12, cols=10, rows=10)
    out.append(measure('synthetic_grid_large', bigger))

    print('\n== BIM EXCHANGE BENCHMARK (CPU, deterministic; no FPS, no GPU) ==')
    hdr = ('%-22s %8s %8s %9s %8s %8s %8s %8s %8s'
           % ('model', 'objects', 'entities', 'bytes', 'export', 'parse',
              'place', 'stage', 'round'))
    print(hdr)
    print('-' * len(hdr))
    for r in out:
        if not r['valid']:
            print('%-22s  NOT MEASURED — %s' % (r['model'], r['issues'][:2]))
            continue
        m = r['ms']
        print('%-22s %8d %8d %9d %7.1fm %7.1fm %7.1fm %7.1fm %7.1fm'
              % (r['model'], r['canonical_objects'], r['ifc_entities'],
                 r['file_bytes'],
                 m['build_exchange'] + m['serialise_step'], m['parse_step'],
                 m['resolve_placements'], m['stage_import_total'],
                 m['roundtrip_compare']))
    lim = B.LIMITS
    big_rows = [r for r in out if r['valid']]
    mx = max(r['ifc_entities'] for r in big_rows)
    mb = max(r['file_bytes'] for r in big_rows)
    print('\nlargest measured file: %d entities, %d bytes — declared limits are '
          '%d entities and %d bytes, so the largest fixture uses %.2f%% of the '
          'entity budget'
          % (mx, mb, lim['max_entity_count'], lim['max_file_bytes'],
             100.0 * mx / float(lim['max_entity_count'])))
    print('every timing above is milliseconds of CPU work in this sandbox on '
          'this run; no frame rate, no GPU and no rendering is measured or '
          'claimed by this layer.')
    with open(os.path.join(OUTDIR, 'benchmark_bim.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    if not big_rows:
        raise SystemExit('nothing was measured')


if __name__ == '__main__':
    main()
