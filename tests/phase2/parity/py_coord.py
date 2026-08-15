# -*- coding: utf-8 -*-
import json, copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(tempfile.gettempdir(), 'acs_parity_py_coord.json')
import acs_coord as C

SC = json.load(open(os.path.join(PHASE, 'fixtures', 'coord_scen.json'), encoding='utf-8'))
AT = '2026-01-01T00:00:00Z'
out = {}
for q in SC["queries"]:
    m = copy.deepcopy(SC["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    s = C.compile_coordination(m, q["bid"], q.get("pos"), q.get("rot") or 0, at=AT)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("detector mutated the model: " + q["n"])
    out[q["n"]] = {"snapshot": s, "summary": C.summary(s), "rule_inputs": C.rule_inputs(s),
                   "export": C.export_snapshot(s),
                   "check": C.check_snapshot(s, copy.deepcopy(SC["models"][q["m"]]), q["bid"])}
for pr in SC["projects"]:
    ents = [{"id": e["id"], "building": copy.deepcopy(SC["models"][e["model"]]),
             "position": e["pos"], "rotation_deg": e["rot"]} for e in pr["entries"]]
    s = C.compile_project_coordination(ents, at=AT)
    out["project:" + pr["n"]] = {
        "snapshot": s, "summary": C.summary(s),
        "check": C.check_project_snapshot(s, ents),
        "moved": C.check_project_snapshot(s, [
            {"id": e["id"], "building": e["building"],
             "position": {"x": ((e["position"] or {}).get("x") or 0) + 5,
                          "z": ((e["position"] or {}).get("z") or 0)},
             "rotation_deg": e["rotation_deg"]} for e in ents])}
A = C.compile_coordination(copy.deepcopy(SC["models"]["A_duct_through_beam"]), "bld_0",
                           None, 0, at=AT)
H = C.compile_coordination(copy.deepcopy(SC["models"]["H_beam_removed"]), "bld_0", None, 0,
                           at='2026-01-02T00:00:00Z')
out["__ops__"] = {
    "reconcile": C.reconcile(A, H),
    "reconcile_reverse": C.reconcile(H, A),
    "byId": C.clash_by_id(A, A["clashes"][0]["id"]), "none": C.clash_by_id(A, "nope"),
    "debug": C.debug_view(A, A["clashes"][0]["id"]), "debug_missing": C.debug_view(A, "nope"),
    "filter_pair": C.filter_clashes(A, discipline_a="MEP", discipline_b="STRUCTURE"),
    "filter_level": C.filter_clashes(A, level_index=1),
    "filter_building": len(C.filter_clashes(A, building_id="bld_0")),
    "filter_other_building": len(C.filter_clashes(A, building_id="bld_9")),
    "filter_severity": len(C.filter_clashes(A, severity="ERROR")),
    "set_open": list(C.set_status(copy.deepcopy(A), A["clashes"][0]["id"], "OPEN")),
    "set_obsolete": list(C.set_status(copy.deepcopy(A), A["clashes"][0]["id"], "OBSOLETE")),
    "set_bogus": list(C.set_status(copy.deepcopy(A), A["clashes"][0]["id"], "RESOLVED")),
    "set_missing": list(C.set_status(copy.deepcopy(A), "nope", "ACKNOWLEDGED")),
    "broad": list(C.broad_phase([])),
    "severity_unknown": C.severity_of("NOT_A_TYPE"),
    "stale": C.check_snapshot(A, copy.deepcopy(SC["models"]["B_pipe_through_wall_no_pen"]),
                              "bld_0")}
ack = copy.deepcopy(A)
C.set_status(ack, ack["clashes"][0]["id"], "ACKNOWLEDGED", by="reviewer",
             at="2026-01-03", note="reviewed")
out["__ack__"] = {"snapshot": ack, "reconcile": C.reconcile(ack, H)}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py coord scenarios:', len(out))
