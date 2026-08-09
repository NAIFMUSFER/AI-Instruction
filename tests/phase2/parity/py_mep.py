# -*- coding: utf-8 -*-
import json, copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(tempfile.gettempdir(), 'acs_parity_py_mep.json')
import acs_mep as M

SC = json.load(open(os.path.join(PHASE, 'fixtures', 'mep_scen.json'), encoding='utf-8'))
out = {}
for q in SC["queries"]:
    m = copy.deepcopy(SC["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    mep = M.compile_mep(m, q["bid"], q.get("pos"), q.get("rot") or 0)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("compiler mutated the model: " + q["n"])
    out[q["n"]] = {"mep": mep, "summary": M.summary(mep), "render": M.render_items(mep),
                   "rule_inputs": M.rule_inputs(mep), "interferences": M.interferences(mep),
                   "validate": M.validate_mep(mep)}
v = M.compile_mep(copy.deepcopy(SC["models"]["villa_mep"]), "bld_0")
out["__lookup__"] = {"byId": M.element_by_id(v, "bld_0.mep.eq_db"),
                     "sys": M.system_by_id(v, "sys_cw"),
                     "none": M.element_by_id(v, "nope"),
                     "world": M.to_world(M.compile_mep(
                         copy.deepcopy(SC["models"]["villa_mep"]), "bld_0",
                         {"x": 4, "z": -6}, 33), 3, 7),
                     "no_adapter": M.summary(M.compile_mep(
                         copy.deepcopy(SC["models"]["phase1_points"]), "bld_0", None, 0,
                         None, None, False))}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
print("py mep scenarios:", len(out))
