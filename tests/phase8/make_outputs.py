# -*- coding: utf-8 -*-
"""ينتج مصنوعات تبادل حقيقية: ملفّات IFC4 بصيغة ISO-10303-21، وبياناً لكل
ملفّ، وتقرير ذهاب وإياب مقروءاً، وتقرير استيراد لملفّ مختلف.

كل ملفّ هنا خرج من المسلسِل ثم قُرئ بالمحلّل نفسه. لا شيء منها مكتوب بيد.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_bim as B                                               # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_bim_fixtures as LIB                                    # noqa: E402
from lib_large_fixture import large_model                         # noqa: E402

OUT = os.path.join(HERE, 'outputs')
os.makedirs(OUT, exist_ok=True)
AT = '2026-01-01T00:00:00Z'

models = LIB.models()
models['synthetic_grid'] = large_model()
models['synthetic_grid_large'] = large_model(levels=12, cols=10, rows=10)

index = []
for key in sorted(models):
    prj = AU.create_project(copy.deepcopy(models[key]), 'bld_0', 'IMPORT', None)
    h0 = prj['model_hash']
    exp = B.export_ifc(prj, {}, AT)
    if not exp['valid']:
        index.append({'model': key, 'exported': False,
                      'issues': [i['code'] for i in exp['issues']]})
        continue
    with open(os.path.join(OUT, key + '.ifc'), 'w', encoding='utf-8') as f:
        f.write(exp['file'])
    with open(os.path.join(OUT, key + '.manifest.json'), 'w',
              encoding='utf-8') as f:
        json.dump(exp['manifest'], f, ensure_ascii=False, indent=1,
                  sort_keys=True)
    st = B.stage_import(exp['file'], key + '.ifc', {}, None, AT)
    rt = B.roundtrip_report(prj, st['staging'], {})
    with open(os.path.join(OUT, key + '.roundtrip.json'), 'w',
              encoding='utf-8') as f:
        json.dump(rt, f, ensure_ascii=False, indent=1, sort_keys=True)
    rep = rt.get('report') or {}
    index.append({
        'model': key, 'exported': True,
        'file': key + '.ifc', 'manifest': key + '.manifest.json',
        'roundtrip': key + '.roundtrip.json',
        'schema': exp['manifest']['schema'],
        'entity_count': exp['manifest']['entity_count'],
        'object_count': exp['manifest']['object_count'],
        'file_hash': exp['manifest']['file_hash'],
        'roundtrip_status': rep.get('status'),
        'semantic_fidelity': rep.get('semantic_fidelity'),
        'geometry_fidelity': rep.get('geometry_fidelity'),
        'relationship_fidelity': rep.get('relationship_fidelity'),
        'property_fidelity': rep.get('property_fidelity'),
        'critical_loss_count': rep.get('critical_loss_count'),
        'model_hash_before': h0, 'model_hash_after': prj['model_hash'],
    })

# تقرير استيراد حقيقي لملفّ يختلف عن النموذج
renamed = copy.deepcopy(models['villa_glazed'])
renamed['floors']['g']['rooms'][0]['name'] = 'majlis_renamed'
alt = B.export_ifc(AU.create_project(copy.deepcopy(renamed), 'bld_0', 'IMPORT',
                                     None), {}, AT)
with open(os.path.join(OUT, 'villa_glazed_edited.ifc'), 'w',
          encoding='utf-8') as f:
    f.write(alt['file'])
with open(os.path.join(OUT, 'villa_glazed_edited.manifest.json'), 'w',
          encoding='utf-8') as f:
    json.dump(alt['manifest'], f, ensure_ascii=False, indent=1, sort_keys=True)
base = AU.create_project(copy.deepcopy(models['villa_glazed']), 'bld_0',
                         'IMPORT', None)
sta = B.stage_import(alt['file'], 'villa_glazed_edited.ifc', {}, None, AT)
dif = B.import_diff(base, sta['staging'], {})
prop = B.import_proposals(dif['diff'], sta['staging'])
with open(os.path.join(OUT, 'villa_glazed_import_report.json'), 'w',
          encoding='utf-8') as f:
    json.dump({'staging_summary': {
        'file': sta['staging']['source']['file_name'],
        'file_hash': sta['staging']['source']['file_hash'],
        'schema': sta['staging']['bim_schema'],
        'counts': sta['staging']['counts'],
        'issues': sta['staging']['issues'],
        'writes_to_model': sta['staging']['writes_to_model']},
        'diff': dif['diff'], 'proposals': prop}, f,
        ensure_ascii=False, indent=1, sort_keys=True)

with open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=1, sort_keys=True)

ok = [i for i in index if i.get('exported')]
print('phase 8 artifacts: %d IFC files, %d manifests, %d round-trip reports, '
      '1 import report — total %d entities'
      % (len(ok), len(ok), len(ok), sum(i['entity_count'] for i in ok)))
for i in ok:
    print('  %-22s %6d entities  round trip %s'
          % (i['model'], i['entity_count'], i['roundtrip_status']))
