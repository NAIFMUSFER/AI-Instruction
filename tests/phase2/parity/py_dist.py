# -*- coding: utf-8 -*-
import json, sys, copy
import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_dist.json')
import acs_relations as REL, acs_navigation as NAV, acs_egress as EG, acs_distance as DIST
S = json.load(open(os.path.join(PHASE, 'fixtures', 'dist_scen.json'), encoding='utf-8'))
out = {}
for q in S['queries']:
    b = copy.deepcopy(S['models'][q['m']])
    rels = REL.build_relationships(b, 'bld_0')
    if q['kind'] == 'path':
        p = NAV.find_path(b, rels, q['from'], q['to'], 'bld_0')
        m = DIST.measure_path(b, p, 'bld_0', q.get('origin'), q.get('dest'))
        out[q['n']] = {'m': m, 'issues': DIST.validate_measurement(m), 'summary': DIST.summary(m)}
    else:
        r = EG.find_egress(b, rels, q['from'], 'bld_0')
        dm = r.get('distance_measurement')
        out[q['n']] = {'status': r['status'], 'distance': r['distance'],
                       'distance_status': r['distance_status'],
                       'selection_basis': r.get('selection_basis'),
                       'selection_basis_reason': r.get('selection_basis_reason'),
                       'alternative_exits': r.get('alternative_exits'),
                       'measurement': dm,
                       'issues': DIST.validate_measurement(dm) if dm else [],
                       'summary': EG.egress_summary(r)}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py scenarios computed:', len(out))
