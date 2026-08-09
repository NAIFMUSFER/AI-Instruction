# -*- coding: utf-8 -*-
"""قياس أداء التأليف (بايثون) — نظير benchmark_authoring.js.

أرقام حقيقية من هذه الآلة. لا ادّعاء إطارات في الثانية ولا أداء بطاقة رسوميات.
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

import acs_authoring as A                                     # noqa: E402
import lib_authoring_fixtures as LIB                           # noqa: E402

SC = LIB.load()
AT = '2026-01-01T00:00:00Z'


def gen_project(n):
    cols = int(math.ceil(math.sqrt(n)))
    rooms = []
    for i in range(n):
        r, c = i // cols, i % cols
        rooms.append({"id": "sp_%d" % i, "rect": [c * 6, r * 5, 6, 5], "height": 3,
                      "doors": [{"edge": "N", "offset": 3, "width": 1, "height": 2.1}],
                      "windows": ([{"edge": "S", "offset": 3, "width": 1.4,
                                    "height": 1.4, "sill": 0.9}] if i % 3 == 0 else [])})
    return {"meta": {"type": "office", "name": "synthetic_%d" % n},
            "wall_h": 3, "wall_t": 0.2, "floor_height": 3.2,
            "site": {"w": cols * 6, "d": int(math.ceil(n / float(cols))) * 5},
            "levels": [{"index": 0, "template": "g"}, {"index": 1, "template": "g"}],
            "floors": {"g": {"rooms": rooms}}}


CASES = [('villa', copy.deepcopy(SC['models']['villa']), 'g.majlis',
          'bld_0.g.majlis.door_0'),
         ('hotel', copy.deepcopy(SC['models']['hotel']), 'g.lobby', None),
         ('project_1000', gen_project(1000), 'g.sp_0', None)]

rows = []
for name, model, space, door in CASES:
    project = A.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    wall_cmd = {'type': 'MOVE_WALL', 'target_id': 'bld_0.flr_0.wall_0',
                'parameters': {'delta_m': 0.25,
                               'hosted_strategy': 'KEEP_RELATIVE_POSITION'}}
    door_cmd = ({'type': 'MOVE_DOOR', 'target_id': door,
                 'parameters': {'offset': 3.0}} if door else None)
    resize_cmd = {'type': 'RESIZE_SPACE', 'target_id': space,
                  'parameters': {'w': 6, 'd': 4}}

    def rename_of(i):
        return {'type': 'RENAME_SPACE', 'target_id': space,
                'parameters': {'name': 'n%d' % i}}

    A.normalise_command(wall_cmd)                              # إحماء
    A.preview_command(project['model'], resize_cmd, None, 'bld_0')

    def t(fn, reps=1):
        t0 = time.time()
        for i in range(reps):
            fn(i)
        return int(round((time.time() - t0) * 1000))

    normalise = t(lambda i: A.normalise_command(resize_cmd), 100)
    wall_preview = t(lambda i: A.preview_command(project['model'], wall_cmd, None, 'bld_0'))
    door_preview = (t(lambda i: A.preview_command(project['model'], door_cmd, None, 'bld_0'))
                    if door_cmd else None)
    resize_preview = t(lambda i: A.preview_command(project['model'], resize_cmd,
                                                   None, 'bld_0'))
    validate = t(lambda i: A.validate_model_integrity(project['model'], 'bld_0'))
    impact = t(lambda i: A.dependency_impact(resize_cmd, project['model'], 'bld_0'))

    batch10 = [rename_of(i) for i in range(10)]
    batch100 = [rename_of(i) for i in range(100)]
    b10 = t(lambda i: A.validate_transaction(project, batch10, 'bld_0'))
    b100 = t(lambda i: A.validate_transaction(project, batch100, 'bld_0'))

    commit = t(lambda i: A.commit_transaction(project, [rename_of(1)], created_at=AT))
    committed = A.commit_transaction(project, [rename_of(1)], created_at=AT)
    hashing = t(lambda i: A.model_hash(project['model'], 'building', 'bld_0'), 20)
    diff = (t(lambda i: A.revision_diff(project['model'], committed['project']['model']))
            if committed.get('committed') else None)
    serialise = t(lambda i: A.serialise_project(project, True, False))

    rooms = sum(len((model.get('floors') or {}).get(k, {}).get('rooms') or [])
                for k in (model.get('floors') or {}))
    rows.append({'model': name, 'spaces': rooms, 'levels': len(model.get('levels') or []),
                 'normalise_ms_per_100': normalise,
                 'wall_edit_preview_ms': wall_preview,
                 'door_edit_preview_ms': door_preview,
                 'space_resize_preview_ms': resize_preview,
                 'model_integrity_validate_ms': validate,
                 'dependency_impact_ms': impact,
                 'batch_10_validate_ms': b10,
                 'batch_100_validate_ms': b100,
                 'commit_with_revision_hash_ms': commit,
                 'model_hash_ms_per_20': hashing,
                 'revision_diff_ms': diff,
                 'serialise_ms': serialise,
                 'committed': committed.get('committed') is True})

print(json.dumps(rows, ensure_ascii=False, indent=1))
print('AUTHORING BENCHMARK ROWS: %d' % len(rows))
print('measured on this machine: normalisation, preview, validation, dependency impact, '
      'batch validation, commit and revision hashing. NOT MEASURED: frames per second, '
      'GPU behaviour, pixel output — no such claim is made anywhere in this phase.')
ok = all(r['committed'] and r['spaces'] > 0 for r in rows)
print('every benchmarked case actually committed a revision: %s' % ok)
sys.exit(0 if ok else 1)
