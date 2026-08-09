# -*- coding: utf-8 -*-
import json, copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
import acs_visual as V
import acs_arch as A

OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(tempfile.gettempdir(),
                                                      'acs_parity_py.json')
SC = json.load(open(os.path.join(PHASE, 'fixtures', 'visual_scenarios.json'),
                    encoding='utf-8'))
AT = '2026-01-01T00:00:00Z'
out = {}
for q in SC["queries"]:
    m = copy.deepcopy(SC["models"][q["m"]])
    before = json.dumps(m, sort_keys=True)
    s = V.compile_visual_scene(m, q["bid"], q.get("pos"), q.get("rot") or 0,
                               mode=q["mode"], theme=q["theme"], lighting=q["light"],
                               quality=q["quality"],
                               include_decoration=bool(q.get("deco")),
                               include_entourage=bool(q.get("ent")),
                               entourage_count=q.get("entn") or 0,
                               clash_overlay=bool(q.get("clash")), at=AT)
    if json.dumps(m, sort_keys=True) != before:
        raise SystemExit("compiler mutated the model: " + q["n"])
    arch = A.compile_architecture(copy.deepcopy(SC["models"][q["m"]]), q["bid"],
                                  q.get("pos"), q.get("rot") or 0)
    req = V.snapshot_request(s, 2560, 1440, "PNG")
    out[q["n"]] = {"scene": s, "summary": V.summary(s), "rule_inputs": V.rule_inputs(s),
                   "validate": V.validate_scene(s), "instancing": V.instancing_plan(s),
                   "lod": V.lod_plan(s, None), "block": V.presentation_block(s),
                   "export_eng": V.export_scene(s, False),
                   "export_pres": V.export_scene(s, True),
                   "buffers": V.control_buffers(s, None),
                   "signature": V.geometry_signature(s, arch),
                   "snapshot": req,
                   "render": V.render_metadata(s, req, "DETERMINISTIC_RENDER", AT, None)}
for d in SC["drawings"]:
    arch = A.compile_architecture(copy.deepcopy(SC["models"][d["m"]]), "bld_0", None, 0)
    if d["kind"] == "plan":
        out["draw:" + d["n"]] = V.floor_plan(arch, d["level"], d.get("style"), "bld_0")
    elif d["kind"] == "section":
        out["draw:" + d["n"]] = V.section_view(arch, d["axis"], d.get("position"), "bld_0")
    else:
        out["draw:" + d["n"]] = V.elevation_view(arch, d["face"], "bld_0")
v = V.compile_visual_scene(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0,
                           mode="PRESENTATION", at=AT)
arch = A.compile_architecture(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0)
req = V.ai_enhancement_request(v, "warm evening light", None, 0.4, arch)
eng = V.compile_visual_scene(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0,
                             mode="ENGINEERING", at=AT)
pres = V.compile_visual_scene(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0,
                              mode="PRESENTATION", at=AT)
out["__ops__"] = {
    "frame": [V.frame_camera(v, p, None) for p in V.CAMERA_PRESETS],
    "frame_room": V.frame_camera(v, "INTERIOR_ROOM", "bld_0.g.majlis@0"),
    "frame_unknown": V.frame_camera(v, "NOPE", None),
    "object": V.object_by_id(v, v["objects"][0]["id"]),
    "object_missing": V.object_by_id(v, "nope"),
    "by_layer": len(V.objects_by_layer(v, "ARCHITECTURE")),
    "ai": req,
    "ai_ok": V.check_visual_consistency(req, {
        "door_count": req["geometry_signature"]["door_count"],
        "floor_count": req["geometry_signature"]["floor_count"],
        "footprint": req["geometry_signature"]["footprint"],
        "model_hash": req["geometry_signature"]["model_hash"]}),
    "ai_drift": V.check_visual_consistency(req, {
        "door_count": 99, "window_count": 7, "floor_count": 5, "room_count": 100,
        "stair_count": 9, "wall_count": 2, "footprint": [0, 0, 999, 999],
        "model_hash": "deadbeef"}, 0.5),
    "ai_no_buffers": V.check_visual_consistency(
        {"geometry_signature": req["geometry_signature"], "control_buffers": []},
        {"door_count": req["geometry_signature"]["door_count"]}),
    "currency": V.check_render_currency(V.render_metadata(v, None, None, AT, None),
                                        copy.deepcopy(SC["models"]["villa"]), "bld_0"),
    "currency_stale": V.check_render_currency(V.render_metadata(v, None, None, AT, None),
                                              copy.deepcopy(SC["models"]["hotel"]), "bld_0"),
    "currency_nohash": V.check_render_currency({}, copy.deepcopy(SC["models"]["villa"]),
                                               "bld_0"),
    "snapshot_huge": V.snapshot_request(v, 20000, 20000, "TIFF", 5, None, "NOPE"),
    "snapshot_zero": V.snapshot_request(v, 0, 0),
    "render_ai": V.render_metadata(v, None, "AI_ENHANCED_VISUALISATION", AT,
                                   {"model": "none"}),
    "render_bogus": V.render_metadata(v, None, "MAGIC", AT, None),
    "assets": V.asset_library(), "asset_one": V.asset_by_id("asset.proc.tree"),
    "asset_missing": V.asset_by_id("nope"),
    "asset_bad": V.validate_asset({"id": "x", "type": "y", "asset_class": "NOPE",
                                   "license": "UNKNOWN", "dimensions_m": {"w": 0, "d": 1,
                                                                          "h": 1},
                                   "source": "s", "script": "alert(1)"}),
    "asset_good": V.validate_asset(V.asset_by_id("asset.proc.tree")),
    "asset_not_object": V.validate_asset("nope"),
    "material": V.material("marble"), "material_missing": V.material("nope"),
    "lod_tight": V.lod_plan(v, 10),
    "layer_eng": list(V.set_layer_visible(eng, "MEP", False))[:2],
    "layer_pres": list(V.set_layer_visible(pres, "MEP", False))[:2],
    "layer_unknown": list(V.set_layer_visible(copy.deepcopy(v), "NOPE", False))[:2],
    "bad_mode": V.compile_visual_scene(copy.deepcopy(SC["models"]["villa"]), "bld_0",
                                       None, 0, mode="NOPE", theme="NOPE",
                                       lighting="NOPE", quality="NOPE", at=AT)["summary"]}

# ---- حالات خصومية: مشاهد صالحة وباطلة متطابقة تمرّ على المدقّقَين ----
def adv_visual(**over):
    o = {"id": "vo_1", "kind": "TREE", "layer": "LANDSCAPE",
         "geometry": {"type": "box", "cx": 0, "cy": 1, "cz": 0, "ex": 1, "ey": 2,
                      "ez": 1, "rot_y": 0},
         "material": "grass", "material_provenance": "SYSTEM_DEFAULT",
         "semantic": False, "visual_only": True, "source_element_id": None}
    o.update(over)
    return o


def adv_model(**over):
    o = {"id": "mo_1", "kind": "WALL", "layer": "ARCHITECTURE",
         "geometry": {"type": "box", "cx": 0, "cy": 1.5, "cz": 0, "ex": 6, "ey": 3,
                      "ez": 0.2, "rot_y": 0},
         "material": "paint_white", "material_provenance": "SYSTEM_DEFAULT",
         "semantic": True, "visual_only": False,
         "source_element_id": "bld_0.flr_0.wall_0"}
    o.update(over)
    return o


_struct_mat = dict(V.material("concrete")); _struct_mat["structural_material"] = True
_fire_mat = dict(V.material("concrete")); _fire_mat["fire_rating"] = 120
ADV = [
    ("valid_visual", {"materials": [], "objects": [adv_visual()]}),
    ("valid_model", {"materials": [], "objects": [adv_model()]}),
    ("valid_mixed", {"materials": [], "objects": [adv_visual(), adv_model()]}),
    ("visual_with_source", {"materials": [],
                            "objects": [adv_visual(source_element_id="wall-123")]}),
    ("visual_with_empty_source", {"materials": [],
                                  "objects": [adv_visual(source_element_id="")]}),
    ("visual_decoration_with_source", {"materials": [], "objects": [
        adv_visual(visual_class=V.DECORATION_CLASS, layer="FURNITURE",
                   source_element_id="wall-123")]}),
    ("visual_landscape_with_source", {"materials": [], "objects": [
        adv_visual(visual_class=V.LANDSCAPE_CLASS, source_element_id="wall-123")]}),
    ("visual_entourage_with_source", {"materials": [], "objects": [
        adv_visual(visual_class=V.ENTOURAGE_CLASS, source_element_id="wall-123")]}),
    ("visual_asset_with_source", {"materials": [], "objects": [
        adv_visual(asset_id="asset.proc.tree", source_element_id="wall-123")]}),
    ("visual_theme_with_source", {"materials": [], "objects": [
        adv_visual(material="marble", material_provenance="VISUAL_THEME",
                   source_element_id="wall-123")]}),
    ("model_without_source", {"materials": [],
                              "objects": [adv_model(source_element_id=None)]}),
    ("visual_marked_semantic", {"materials": [], "objects": [adv_visual(semantic=True)]}),
    ("material_not_in_library", {"materials": [],
                                 "objects": [adv_model(material="unobtanium")]}),
    ("bad_provenance", {"materials": [],
                        "objects": [adv_model(material_provenance="ENGINEERING")]}),
    ("structural_material", {"materials": [_struct_mat], "objects": []}),
    ("fire_rated_material", {"materials": [_fire_mat], "objects": []}),
]
out["__adversarial__"] = {}
for name, sc in ADV:
    out["__adversarial__"][name] = {"accepted": len(V.validate_scene(sc)) == 0,
                                    "issues": V.validate_scene(sc)}
adv_scene = V.compile_visual_scene(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0,
                                   mode="PRESENTATION", at=AT)
adv_arch = A.compile_architecture(copy.deepcopy(SC["models"]["villa"]), "bld_0", None, 0)
adv_req = V.ai_enhancement_request(adv_scene, "evening", None, 0.4, adv_arch)
out["__ai_contract__"] = {
    "requested": adv_req["requested_control_buffers"],
    "descriptors": adv_req["control_buffers"],
    "subset": V.ai_enhancement_request(adv_scene, "x", ["depth", "object_id"], 0.4, adv_arch),
    "unknown_dropped": V.ai_enhancement_request(adv_scene, "x", ["depth", "xray"], 0.4,
                                                adv_arch)["requested_control_buffers"],
    "no_signature": V.check_visual_consistency({"requested_control_buffers": ["depth"]},
                                               {"door_count": 9}),
    "null_signature": V.check_visual_consistency(
        {"requested_control_buffers": ["depth"], "geometry_signature": None},
        {"door_count": 9}),
    "empty_signature": V.check_visual_consistency(
        {"requested_control_buffers": ["depth"], "geometry_signature": {}},
        {"door_count": 9}),
    "nothing": V.check_visual_consistency({}, {"door_count": 9}),
    "no_buffers": V.check_visual_consistency(
        {"geometry_signature": adv_req["geometry_signature"],
         "requested_control_buffers": []},
        {"door_count": adv_req["geometry_signature"]["door_count"]}),
    "legacy_list_buffers": V.check_visual_consistency(
        {"geometry_signature": adv_req["geometry_signature"],
         "control_buffers": ["depth", "edge"]},
        {"door_count": adv_req["geometry_signature"]["door_count"]})}

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py visual scenarios:', len(out))
