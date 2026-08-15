# -*- coding: utf-8 -*-
"""قياس أداء زمن التشغيل (بايثون) — نظير benchmark_runtime.js.

أرقام حقيقية من هذه الآلة: زمن التصريف، زمن بناء الفهرس، زمن الاستعلام،
عدد المرشّحين، وأعداد الأجسام والبوّابات والأسطح.
لا ادّعاء إطارات في الثانية، ولا ادّعاء أداء بطاقة رسوميات، ولا ادّعاء بكسل.
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

import acs_visual as V                                      # noqa: E402
import acs_runtime as R                                     # noqa: E402
import lib_runtime_fixtures as LIB                          # noqa: E402

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


CASES = [("small · villa", copy.deepcopy(SC["models"]["villa"])),
         ("medium · hotel", copy.deepcopy(SC["models"]["hotel"])),
         ("large · synthetic 400", gen_project(400)),
         ("very large · synthetic 1500", gen_project(1500))]

REPS = 200
rows = []
for name, m in CASES:
    vs = V.compile_visual_scene(copy.deepcopy(m), "bld_0", None, 0,
                                mode="ENGINEERING", at=AT)
    R.compile_runtime_scene(vs)                     # إحماء، لا يُقاس

    t0 = time.time()
    rs = R.compile_runtime_scene(vs)
    t1 = time.time()

    i0 = time.time()
    idx = R._build_index(rs["walkability"]["obstacles"], rs["walkability"]["surfaces"],
                         rs["transform"])
    i1 = time.time()

    obstacles = rs["walkability"]["obstacles"]
    if obstacles:
        cx = (min(o["bounds"][0] for o in obstacles)
              + max(o["bounds"][3] for o in obstacles)) / 2.0
        cz = (min(o["bounds"][2] for o in obstacles)
              + max(o["bounds"][5] for o in obstacles)) / 2.0
    else:
        cx = cz = 0.0
    box = [cx - 2, -1, cz - 2, cx + 2, 4, cz + 2]

    q0 = time.time()
    last = None
    for _ in range(REPS):
        last = R.query_spatial_index(rs, box)
    q1 = time.time()

    st = R.create_runtime_state(rs)
    m0 = time.time()
    for _ in range(REPS):
        R.move_query(rs, st, [cx, 0.9, cz], [cx + 3, 0.9, cz + 3])
    m1 = time.time()

    spawn = (rs["defaults"].get("spawn") or {}).get("position") or [0.0, 0.0, 0.0]
    s0 = time.time()
    for _ in range(REPS):
        R.validate_spawn(rs, spawn)
    s1 = time.time()

    v0 = time.time()
    R.effective_visibility(st, rs)
    v1 = time.time()

    ms = lambda a, b: int(round((b - a) * 1000))            # noqa: E731
    total = last["total_entries"]
    rows.append({
        "model": name,
        "objects": rs["counts"]["objects"],
        "obstacles": rs["counts"]["obstacles"],
        "surfaces": rs["counts"]["surfaces"],
        "portals": rs["counts"]["portals"],
        "portals_unresolved": rs["counts"]["portals_unresolved"],
        "rooms": rs["counts"]["rooms"],
        "vertical_connections": rs["counts"]["vertical_connections"],
        "compile_ms": ms(t0, t1),
        "index_build_ms": ms(i0, i1),
        "index_cells": idx["cells"],
        "index_entries": idx["entries"],
        "index_oversized": idx["oversized"],
        "query_total_ms_over_200": ms(q0, q1),
        "query_candidates": last["candidate_count"],
        "query_scanned_cells": last["scanned_cells"],
        "query_full_scan": last["full_scan"],
        "candidate_reduction": (round(1 - (last["candidate_count"] / float(total)), 4)
                                if total else None),
        "move_total_ms_over_200": ms(m0, m1),
        "spawn_total_ms_over_200": ms(s0, s1),
        "effective_visibility_ms": ms(v0, v1)})

print(json.dumps(rows, ensure_ascii=False, indent=1))
print("RUNTIME BENCHMARK ROWS: %d" % len(rows))
print("measured on this machine: compile time, index build time, query time, "
      "candidate count. NOT MEASURED: frames per second, GPU behaviour, pixel output — "
      "no such claim is made anywhere in this phase.")

proven = all((not r["query_full_scan"])
             and (r["index_entries"] == 0 or r["query_candidates"] <= r["index_entries"])
             for r in rows)
print("spatial candidate reduction demonstrated on every case: %s" % proven)
sys.exit(0 if proven else 1)
