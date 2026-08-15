# -*- coding: utf-8 -*-
"""المرحلة 6 §75 — قياس أداء مساحة العمل (بايثون).

أرقام حقيقية من هذه الآلة لنفس الحالات التي يقيسها benchmark_workspace.js.
لا ادّعاء إطارات في الثانية ولا أداء بطاقة رسوميات — لا شيء منه مقيس هنا.
"""
import copy
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import acs_authoring as AU                                       # noqa: E402
import acs_workspace as W                                        # noqa: E402
import acs_arch as ARCH                                          # noqa: E402
import acs_coord as COORD                                        # noqa: E402
import acs_visual as VIS                                         # noqa: E402
import acs_runtime as RT                                         # noqa: E402
import lib_workspace_fixtures as LIB                             # noqa: E402

FX = LIB.models()
AT = '2026-01-01T00:00:00Z'
SPEC = W.SPEC


def gen_project(n):
    cols = int(math.ceil(math.sqrt(n)))
    rooms = []
    for i in range(n):
        r, c = divmod(i, cols)
        rooms.append({'id': 'sp_%d' % i, 'rect': [c * 6, r * 5, 6, 5], 'height': 3,
                      'doors': [{'edge': 'N', 'offset': 3, 'width': 1, 'height': 2.1}],
                      'windows': ([{'edge': 'S', 'offset': 3, 'width': 1.4,
                                    'height': 1.4, 'sill': 0.9}] if i % 3 == 0 else [])})
    return {'meta': {'type': 'office', 'name': 'synthetic_%d' % n},
            'wall_h': 3, 'wall_t': 0.2, 'floor_height': 3.2,
            'site': {'w': cols * 6, 'd': int(math.ceil(n / float(cols))) * 5},
            'levels': [{'index': 0, 'template': 'g'}, {'index': 1, 'template': 'g'}],
            'floors': {'g': {'rooms': rooms}}}


CASES = [('villa', copy.deepcopy(FX['villa']), 'g.majlis'),
         ('hotel', copy.deepcopy(FX['hotel']), None),
         ('project_1000', gen_project(1000), 'g.sp_0')]


def ms(fn, reps=1):
    t0 = time.time()
    for i in range(reps):
        fn()
    return int(round((time.time() - t0) * 1000))


rows = []
for name, model, wanted in CASES:
    load_ms = ms(lambda: AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None))
    project = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    arch_ms = ms(lambda: ARCH.compile_architecture(copy.deepcopy(model), 'bld_0', None, 0))
    arch = ARCH.compile_architecture(copy.deepcopy(model), 'bld_0', None, 0)

    coord = [None]

    def _coord():
        try:
            coord[0] = COORD.compile_coordination(copy.deepcopy(model), 'bld_0', None, 0)
        except Exception:
            coord[0] = None
    coord_ms = ms(_coord)
    try:
        runtime = RT.compile_runtime_scene(
            VIS.compile_visual_scene(copy.deepcopy(model), 'bld_0', None, 0,
                                     {'mode': 'ENGINEERING'}), None)
    except Exception:
        runtime = None

    W.project_tree(project, arch, coord[0], 'en')                 # إحماء
    tree_ms = ms(lambda: W.project_tree(project, arch, coord[0], 'en'))
    tree = W.project_tree(project, arch, coord[0], 'en')

    # الشجرة تُفتح بكاملها: أسوأ حالة حقيقية للتسطيح، ولا تخفي كلفة
    expanded = []

    def walk(n):
        expanded.append(n['node_id'])
        for c in n.get('children') or []:
            walk(c)
    walk(tree['root'])
    flatten_ms = ms(lambda: W.flatten_tree(tree, expanded, None, None), 10)
    flat = W.flatten_tree(tree, expanded, None, None)['rows']

    target = wanted
    if not target:
        spaces = [r for r in flat if r['kind'] == 'SPACE']
        target = spaces[0]['node_id'] if spaces else None

    inspector_ms = (ms(lambda: W.inspector_model(project, target, arch, None,
                                                 coord[0], 'en'), 10)
                    if target else None)
    issues_ms = ms(lambda: W.issue_center(project, arch, coord[0], runtime, None, 'bld_0'))
    issues = W.issue_center(project, arch, coord[0], runtime, None, 'bld_0')

    preview_ms = commit_ms = None
    committed = False
    if target:
        cmd = {'type': 'RESIZE_SPACE', 'target_id': target, 'parameters': {'w': 6, 'd': 4}}
        preview_ms = ms(lambda: AU.preview_command(project['model'], copy.deepcopy(cmd),
                                                   None, 'bld_0'))
        txn = AU.validate_transaction(project, [copy.deepcopy(cmd)], 'bld_0')
        t0 = time.time()
        c = AU.commit_transaction(project, [copy.deepcopy(cmd)],
                                  confirm=(txn.get('transaction') or {})
                                  .get('confirmation_digest'),
                                  acknowledge_warnings=True, created_at=AT)
        commit_ms = int(round((time.time() - t0) * 1000))
        committed = c.get('committed') is True

    summary_ms = ms(lambda: W.workspace_summary(project, W.ui_state_default(),
                                                tree, issues), 10)

    rows.append({'case': name,
                 'tree_nodes': tree['node_count'],
                 'visible_rows': len(flat),
                 'issue_total': issues['total'],
                 'project_load_ms': load_ms,
                 'architecture_compile_ms': arch_ms,
                 'coordination_compile_ms': coord_ms,
                 'tree_build_ms': tree_ms,
                 'tree_flatten_ms_per_10': flatten_ms,
                 'inspector_open_ms_per_10': inspector_ms,
                 'issue_centre_ms': issues_ms,
                 'edit_preview_ms': preview_ms,
                 'commit_ms': commit_ms,
                 'summary_ms_per_10': summary_ms,
                 'committed': committed})

print(json.dumps(rows, ensure_ascii=False, indent=1))
print('WORKSPACE BENCHMARK ROWS: %d' % len(rows))
print('declared measurable metrics: %s'
      % json.dumps(SPEC.get('performance_metrics') or []))
print(SPEC.get('performance_note'))
print('measured on this machine: project load, discipline compilation, tree build and '
      'flatten, inspector open, issue centre, edit preview and commit. NOT MEASURED: '
      'frames per second, GPU behaviour, pixel output, render latency — no such claim '
      'is made anywhere in this phase.')
ok = all(r['tree_nodes'] > 3 and r['visible_rows'] > 0 and r['committed'] for r in rows)
print('every benchmarked case built a real tree and committed a revision: %s' % ok)
if not ok:
    raise SystemExit(1)
