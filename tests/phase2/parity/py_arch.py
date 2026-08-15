# -*- coding: utf-8 -*-
import json
import copy
import sys

import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_arch.json')
import acs_arch as A

S = json.load(open(os.path.join(PHASE, 'fixtures', 'arch_scen.json'), encoding='utf-8'))
out = {}
for q in S["queries"]:
    m = copy.deepcopy(S["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    arch = A.compile_architecture(m, q["bid"], q.get("pos"), q.get("rot") or 0)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("compiler mutated the model: " + q["n"])
    anchors, doors = {}, {}
    for o in arch.get("openings") or []:
        anchors[o["id"]] = A.opening_anchor(arch, o["id"])
        if o["type"] == "DOOR":
            doors[o["id"]] = A.door_connects_confirmed(arch, o["id"])
    world = [[w["id"], A.to_world(arch, w["start"]["x"], w["start"]["z"]),
              A.to_world(arch, w["end"]["x"], w["end"]["z"])] for w in arch.get("walls") or []]
    out[q["n"]] = {"arch": arch, "summary": A.summary(arch), "anchors": anchors,
                   "doors": doors, "world": world,
                   "validate": A.validate_architecture(arch)}
a = A.compile_architecture(copy.deepcopy(S["models"]["shared"]), "bld_0", None, 0)
out["__shared__"] = {"w": A.shared_wall_between(a, "bld_0.g.a", "bld_0.g.b"),
                     "missing": A.shared_wall_between(a, "bld_0.g.a", "nope"),
                     "byId": A.element_by_id(a, "bld_0.flr_0.wall_0"),
                     "envelopeById": A.element_by_id(a, "bld_0.envelope"),
                     "none": A.element_by_id(a, "no_such_id")}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
print("py arch scenarios:", len(out))
