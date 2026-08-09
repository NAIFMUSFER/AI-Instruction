# -*- coding: utf-8 -*-
import json, copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(tempfile.gettempdir(), 'acs_parity_py_fls.json')
import acs_fls as F

SC = json.load(open(os.path.join(PHASE, 'fixtures', 'fls_scen.json'), encoding='utf-8'))
out = {}
for q in SC["queries"]:
    m = copy.deepcopy(SC["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    f = F.compile_fls(m, q["bid"], q.get("pos"), q.get("rot") or 0)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("compiler mutated the model: " + q["n"])
    out[q["n"]] = {"fls": f, "summary": F.summary(f), "audit": F.audit(f),
                   "render": F.render_items(f), "rule_inputs": F.rule_inputs(f),
                   "validate": F.validate_fls(f)}
v = F.compile_fls(copy.deepcopy(SC["models"]["villa_fls"]), "bld_0")
out["__lookup__"] = {"byId": F.element_by_id(v, "bld_0.fls.d_sd1"),
                     "none": F.element_by_id(v, "nope"),
                     "world": F.to_world(F.compile_fls(
                         copy.deepcopy(SC["models"]["villa_fls"]), "bld_0",
                         {"x": 6, "z": -2}, 18), 5, 4),
                     "egress": F.egress_facts(copy.deepcopy(SC["models"]["villa_fls"]),
                                              "bld_0", "bld_0.g.majlis"),
                     "egress_missing": F.egress_facts(
                         copy.deepcopy(SC["models"]["villa_fls"]), "bld_0", "nope")}
with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False)
print("py fls scenarios:", len(out))
