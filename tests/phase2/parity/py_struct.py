# -*- coding: utf-8 -*-
import json, copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(tempfile.gettempdir(), 'acs_parity_py_struct.json')
import acs_struct as S

SC = json.load(open(os.path.join(PHASE, 'fixtures', 'struct_scen.json'), encoding='utf-8'))
out = {}
for q in SC["queries"]:
    m = copy.deepcopy(SC["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    st = S.compile_structure(m, q["bid"], q.get("pos"), q.get("rot") or 0)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("compiler mutated the model: " + q["n"])
    world = [[S.grid_to_world(st, gs, g, 50) for g in gs["grids"]]
             for gs in st.get("grid_systems") or []]
    out[q["n"]] = {"struct": st, "summary": S.summary(st), "render": S.render_items(st),
                   "rule_inputs": S.rule_inputs(st), "grids_world": world,
                   "validate": S.validate_structure(st)}
out["__suggest__"] = {
    "none": S.suggest_structural_grid(copy.deepcopy(SC["models"]["no_struct"]), None, None, "bld_0"),
    "xz": S.suggest_structural_grid(copy.deepcopy(SC["models"]["no_struct"]), 5, 4, "bld_0"),
    "x_only": S.suggest_structural_grid(copy.deepcopy(SC["models"]["no_struct"]), 6, None, "bld_0"),
    "empty": S.suggest_structural_grid({"levels": [], "floors": {}}, 5, 5, "bld_0")}
v = S.compile_structure(copy.deepcopy(SC["models"]["villa_struct"]), "bld_0")
out["__lookup__"] = {"byId": S.element_by_id(v, "bld_0.C_A1"),
                     "grid": S.element_by_id(v, "bld_0.grid_x_A"),
                     "none": S.element_by_id(v, "nope"),
                     "world": S.to_world(S.compile_structure(
                         copy.deepcopy(SC["models"]["villa_struct"]), "bld_0",
                         {"x": 3, "z": -2}, 60), 4, 5)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
print("py structural scenarios:", len(out))
