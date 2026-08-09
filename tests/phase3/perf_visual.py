# -*- coding: utf-8 -*-
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import acs_arch as A, acs_visual as V
FX = json.load(open(os.path.join(HERE, 'fixtures', 'base_fixtures.json'), encoding='utf-8'))

def gen(n):
    cols = int(math.ceil(math.sqrt(n)))
    rooms = []
    for i in range(n):
        r, c = i // cols, i % cols
        rooms.append({"id": "sp_%d" % i, "rect": [c * 6, r * 5, 6, 5], "height": 3,
                      "doors": [{"edge": "N", "offset": 3, "width": 1, "height": 2.1}],
                      "windows": ([{"edge": "S", "offset": 3, "width": 1.4,
                                    "height": 1.4, "sill": 0.9}] if i % 3 == 0 else [])})
    return {"meta": {"type": "office", "name": "big"}, "wall_h": 3, "wall_t": 0.2,
            "floor_height": 3.2,
            "site": {"w": cols * 6, "d": int(math.ceil(n / float(cols))) * 5},
            "levels": [{"index": 0, "template": "g"}, {"index": 1, "template": "g"}],
            "floors": {"g": {"rooms": rooms}}}

rows = []
for name, m in (("villa", FX["villa"]), ("hotel", FX["hotel"]),
                ("warehouse", FX["warehouse"]), ("project_1000", gen(1000))):
    arch = A.compile_architecture(json.loads(json.dumps(m)), "bld_0", None, 0)
    V.compile_visual_scene(json.loads(json.dumps(m)), "bld_0", None, 0, mode="PRESENTATION")
    t0 = time.time()
    s = V.compile_visual_scene(json.loads(json.dumps(m)), "bld_0", None, 0,
                               mode="PRESENTATION", quality="HIGH")
    t1 = time.time()
    d0 = time.time()
    dec = V.compile_visual_scene(json.loads(json.dumps(m)), "bld_0", None, 0,
                                 mode="DOLLHOUSE", include_decoration=True, quality="HIGH")
    d1 = time.time()
    p0 = time.time(); V.floor_plan(arch, 0, "TECHNICAL", "bld_0"); p1 = time.time()
    x0 = time.time(); V.section_view(arch, "x", None, "bld_0"); x1 = time.time()
    e0 = time.time(); V.elevation_view(arch, "NORTH", "bld_0"); e1 = time.time()
    inst = V.instancing_plan(dec)
    rows.append({"model": name, "spaces": len(arch["spaces"]),
                 "scene_objects": s["counts"]["objects"],
                 "modelled": s["counts"]["semantic_objects"],
                 "visual_only": s["counts"]["visual_only_objects"],
                 "instance_groups": len(inst["groups"]),
                 "scene_build_ms": int((t1 - t0) * 1000),
                 "dollhouse_with_decor_ms": int((d1 - d0) * 1000),
                 "plan_ms": int((p1 - p0) * 1000), "section_ms": int((x1 - x0) * 1000),
                 "elevation_ms": int((e1 - e0) * 1000)})
print(json.dumps(rows, indent=1))
print("VISUAL PERF ROWS:", len(rows))
