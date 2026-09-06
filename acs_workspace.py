# -*- coding: utf-8 -*-
# =============================================================================
# acs_workspace.py — نماذج العرض المشتقّة لمساحة عمل المنتج.
#
# هذه الطبقة لا تحسب هندسة ولا تبني محرّكاً جديداً. تقرأ مخرجات المحرّكات
# القائمة وتشتقّ منها نماذج عرض قابلة للاختبار: شجرة المشروع، الفاحص، مركز
# الملاحظات، تغطية المتطلّبات، والعمليات المتاحة لعنصر مختار.
#
# مبادئ صارمة:
#   • الواجهة لا تعدّل النموذج الهندسي أبداً؛ كل تعديل يمرّ بأمر تأليف المرحلة 5.
#   • حالة الواجهة وحالة زمن التشغيل لا تدخلان بصمة النموذج إطلاقاً.
#   • المجهول يبقى مجهولاً: لا صفر ولا افتراضي ولا تقدير مكان قيمة غير مذكورة.
#   • المشتقّ للقراءة فقط، والعرضي عرضيّ ولا يصير بياناً هندسياً.
#   • لا مطابقة أنظمة ولا حالة "آمن" ولا "معتمد" في أي مكان.
# =============================================================================
import json
import os

import acs_authoring as AU

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_workspace.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
UI_VERSION = SPEC["compiler_version"]
STATE_CLASSES = tuple(SPEC["state_classes"])
STATE_OWNERSHIP = SPEC["state_ownership"]
PANELS = tuple(SPEC["panels"])
BREAKPOINTS = SPEC["breakpoints"]
TREE_NODE_KINDS = tuple(SPEC["tree_node_kinds"])
TREE_DISCIPLINES = tuple(SPEC["tree_disciplines"])
INSPECTOR_SECTIONS = tuple(SPEC["inspector_sections"])
EDITABILITY_CLASSES = tuple(SPEC["editability_classes"])
UNKNOWN_LABEL = SPEC["unknown_label"]
PROVENANCE_LABELS = SPEC["provenance_labels"]
FORBIDDEN_PROVENANCE = tuple(SPEC["forbidden_provenance_labels"])
UI_MODES = tuple(SPEC["ui_modes"])
ELEMENT_OPERATIONS = SPEC["element_operations"]
ISSUE_CATEGORIES = tuple(SPEC["issue_categories"])
ISSUE_SEVERITIES = tuple(SPEC["issue_severities"])
RULE_STATUSES = tuple(SPEC["rule_statuses"])
FORBIDDEN_STATUS_WORDS = tuple(SPEC["forbidden_status_words"])
REQUIREMENT_CLASSES = tuple(SPEC["requirement_classes"])
FORBIDDEN_COVERAGE_WORDS = tuple(SPEC["forbidden_coverage_words"])
EXPORT_KINDS = tuple(SPEC["export_kinds"])
EXPORT_SOURCES = tuple(SPEC["export_sources"])
REFERENCE_KINDS = tuple(SPEC["reference_kinds"])
REFERENCE_SCOPES = tuple(SPEC["reference_scopes"])
VISUAL_INTENT_FIELDS = tuple(SPEC["visual_intent_fields"])
ASSISTANT_CAPABILITIES = tuple(SPEC["assistant_capabilities"])
ASSISTANT_CLAIM_CLASSES = tuple(SPEC["assistant_claim_classes"])
CAMERA_PRESETS = tuple(SPEC["camera_presets"])
MEASUREMENT_KINDS = tuple(SPEC["measurement_kinds"])
DISPLAY_UNITS = tuple(SPEC["display_units"])
CANONICAL_UNIT = SPEC["canonical_unit"]
LANGUAGES = tuple(SPEC["languages"])
REFERENCE_UNSAFE = tuple(SPEC["reference_unsafe_patterns"])
NOT_SPECIFIED = "NOT_SPECIFIED"


# ------------------------------------------------------------- أدوات ------
def _copy(v):
    return json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v


def _num(v):
    return AU._num(v)


def _rooms(model):
    return AU._all_rooms(model)


def label(key, lang="en"):
    """تسمية معلنة. أي تسمية توحي بمطابقة نظام تُرفض لا تُتجنّب فقط."""
    lg = lang if lang in LANGUAGES else "en"
    entry = PROVENANCE_LABELS.get(key)
    if entry is None:
        return PROVENANCE_LABELS["unknown"][lg]
    return entry[lg]


def is_forbidden_label(text):
    t = str(text).strip().lower()
    return any(t == str(f).strip().lower() for f in FORBIDDEN_PROVENANCE)


def resolve_provenance_label(source, lang="en"):
    """يحوّل مصدر قيمة إلى تسمية صادقة. لا يُنتج أبداً تسمية مطابقة."""
    s = str(source or "").strip().lower()
    mapping = {"imported": "imported", "user": "user", "stated": "user",
               "ai": "ai_inference", "ai_inference": "ai_inference",
               "llm": "ai_inference", "inferred": "geometry_inference",
               "geometry": "geometry_inference", "derived": "derived",
               "system_default": "system_default", "default": "system_default",
               "unknown": "unknown"}
    key = mapping.get(s, "unknown")
    out = label(key, lang)
    if is_forbidden_label(out):                                # pragma: no cover
        return label("unknown", lang)
    return out


def display_value(value, editability, lang="en"):
    """المجهول يُعرَض مجهولاً. لا صفر ولا افتراضي مكان قيمة غير مذكورة."""
    lg = lang if lang in LANGUAGES else "en"
    if value is None or value == NOT_SPECIFIED or editability == "UNKNOWN":
        return {"text": UNKNOWN_LABEL[lg], "known": False,
                "editability": editability, "raw": None}
    return {"text": _format(value), "known": True,
            "editability": editability, "raw": value}


def _format(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        n = _num(v)
        if n is None:
            return str(v)
        if float(n).is_integer():
            return str(int(n))
        return ("%." + str(int(SPEC["display_decimals"])) + "f") % n
    if isinstance(v, (list, dict)):
        # الصيغة المضغوطة هي ما تنتجه JSON.stringify في المتصفّح؛ الفواصل
        # ذات المسافة تجعل نصّ العرض يختلف بين التطبيقين
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return str(v)


def convert_display(value_m, unit):
    """تحويل وحدة عرض فقط. لا يكتب شيئاً في النموذج."""
    n = _num(value_m)
    if n is None or unit not in DISPLAY_UNITS:
        return {"value": None, "unit": CANONICAL_UNIT, "converted": False,
                "writes_to_model": False}
    if unit == "METRIC_M":
        out = n
    elif unit == "METRIC_CM":
        out = n * 100.0
    else:                                                       # IMPERIAL_FT
        out = n / 0.3048
    return {"value": round(out, 6) + 0.0, "unit": unit, "canonical_m": n,
            "converted": unit != CANONICAL_UNIT, "writes_to_model": False}


# ------------------------------------------------------ شجرة المشروع -----
def project_tree(project, arch=None, coordination=None, lang="en"):
    """شجرة ملاحة مبنيّة من النموذج القانوني ومخرجات المصرّفات. كل عقدة تحمل
    معرّفاً حقيقياً — لا عقدة نائبة ولا ابن مخترَع."""
    model = project["model"]
    bid = project.get("building_id") or "bld_0"
    # أسماء المجموعات نصّ واجهة لا بيانات نموذج، فتُترجَم من المواصفة وحدها؛
    # أسماء المستعمل (اسم المشروع، اسم الفراغ) تبقى كما كتبها هو
    def _L(key):
        entry = SPEC["ui_labels"][key]
        lg = lang if lang in SPEC["languages"] else SPEC["default_language"]
        return entry[lg]
    levels = sorted((model.get("levels") or []),
                    key=lambda l: (l.get("index") is None, l.get("index")))
    rooms_by_template = {}
    for t, r in _rooms(model):
        rooms_by_template.setdefault(t, []).append(r)

    def node(nid, kind, name, discipline=None, children=None, meta=None):
        return {"node_id": nid, "kind": kind, "name": name,
                "discipline": discipline, "children": children or [],
                "selectable": kind in ("SPACE", "DOOR", "WINDOW", "OBJECT",
                                       "LEVEL", "SITE", "BUILDING"),
                "meta": meta or {}}

    level_nodes = []
    for lv in levels:
        tmpl = lv.get("template")
        idx = lv.get("index")
        rooms = sorted(rooms_by_template.get(tmpl, []), key=lambda r: str(r.get("id")))
        space_nodes, door_nodes, window_nodes, object_nodes = [], [], [], []
        for r in rooms:
            rid = str(r.get("id"))
            space_nodes.append(node("%s.%s.%s" % (bid, tmpl, rid), "SPACE",
                                    r.get("name") or rid, "ARCHITECTURE", None,
                                    {"template": tmpl, "level_index": idx,
                                     "space_id": rid}))
            for j, op in enumerate(r.get("doors") or []):
                door_nodes.append(node(op.get("id") or "%s.%s.%s.door_%d" % (bid, tmpl, rid, j), "DOOR",
                                       "%s · %s %d" % (rid, _L("t_door"), j),
                                       "ARCHITECTURE", None,
                                       {"space_id": rid, "level_index": idx,
                                        "edge": op.get("edge")}))
            for j, op in enumerate(r.get("windows") or []):
                window_nodes.append(node(op.get("id") or "%s.%s.%s.window_%d" % (bid, tmpl, rid, j),
                                         "WINDOW",
                                         "%s · %s %d" % (rid, _L("t_window"), j),
                                         "ARCHITECTURE", None,
                                         {"space_id": rid, "level_index": idx,
                                          "edge": op.get("edge")}))
            for j, o in enumerate(r.get("objects") or []):
                object_nodes.append(node("%s.%s.obj_%d" % (tmpl, rid, j), "OBJECT",
                                         "%s · %s" % (rid, o.get("kind")),
                                         "ARCHITECTURE", None,
                                         {"space_id": rid, "level_index": idx,
                                          "object_kind": o.get("kind")}))
        groups = []
        if space_nodes:
            groups.append(node("%s.flr_%s.spaces" % (bid, idx), "GROUP", _L("t_spaces"),
                               "ARCHITECTURE", space_nodes,
                               {"count": len(space_nodes)}))
        if door_nodes:
            groups.append(node("%s.flr_%s.doors" % (bid, idx), "GROUP", _L("t_doors"),
                               "ARCHITECTURE", door_nodes, {"count": len(door_nodes)}))
        if window_nodes:
            groups.append(node("%s.flr_%s.windows" % (bid, idx), "GROUP", _L("t_windows"),
                               "ARCHITECTURE", window_nodes,
                               {"count": len(window_nodes)}))
        if object_nodes:
            groups.append(node("%s.flr_%s.objects" % (bid, idx), "GROUP", _L("t_objects"),
                               "ARCHITECTURE", object_nodes,
                               {"count": len(object_nodes)}))
        level_nodes.append(node("%s.flr_%s" % (bid, idx), "LEVEL",
                                lv.get("name") or ("%s %s" % (_L("t_level"), idx)),
                                "ARCHITECTURE", groups,
                                {"level_index": idx, "template": tmpl}))

    discipline_groups = []
    if arch is not None:
        walls = arch.get("walls") or []
        if walls:
            discipline_groups.append(node("%s.derived.walls" % bid, "GROUP",
                                          _L("t_walls_derived"), "ARCHITECTURE", [],
                                          {"count": len(walls), "derived": True}))
    # المفتاح القانوني للإنشاء في هذا النموذج هو "structural"؛ يُقبل الاسمان
    for keys, kind, disc, name in ((("structural", "structure"), "STRUCTURE_GROUP",
                                    "STRUCTURE", "t_structure"),
                                   (("mep",), "MEP_GROUP", "MEP", "t_mep"),
                                   (("fls",), "FLS_GROUP", "FLS", "t_fls")):
        key = next((k for k in keys if model.get(k)), keys[0])
        present = model.get(key)
        if present:
            count = sum(len(v) for v in present.values()
                        if isinstance(v, list)) if isinstance(present, dict) else 0
            discipline_groups.append(node("%s.%s" % (bid, key), kind, _L(name), disc, [],
                                          {"count": count, "authorable": False}))
    if coordination is not None:
        findings = ((coordination.get("clashes") or []) +
                    (coordination.get("penetrations") or []) +
                    (coordination.get("clearance_issues") or []) +
                    (coordination.get("semantic_conflicts") or []))
        discipline_groups.append(node("%s.coordination" % bid, "COORDINATION_GROUP",
                                      _L("t_coordination"), "COORDINATION", [],
                                      {"count": len(findings), "derived": True}))

    building = node(bid, "BUILDING", model.get("meta", {}).get("name") or bid,
                    None, level_nodes + discipline_groups,
                    {"levels": len(levels)})
    site = node("site", "SITE", _L("t_site"), "ARCHITECTURE", [building],
                {"w": (model.get("site") or {}).get("w"),
                 "d": (model.get("site") or {}).get("d")})
    root = node("project", "PROJECT",
                model.get("meta", {}).get("name") or _L("t_project"), None, [site],
                {"revision": project.get("current_revision"),
                 "model_hash": str(project.get("model_hash"))[:24]})

    def count(n):
        return 1 + sum(count(c) for c in n["children"])

    return {"schema": SCHEMA, "root": root, "node_count": count(root),
            "levels": [{"index": lv.get("index"), "name": lv.get("name"),
                        "template": lv.get("template")} for lv in levels],
            "disciplines": list(TREE_DISCIPLINES),
            "virtualise": count(root) > int(SPEC["tree_virtualisation_threshold"]),
            "writes_to_model": False,
            "note": "every node carries a real identifier from the canonical model or a "
                    "compiler output; there is no placeholder node"}


def flatten_tree(tree, expanded=None, discipline_filter=None, level_filter=None):
    """يسطّح الشجرة لعرض افتراضي. الترشيح يؤثّر في العرض فقط ولا يمسّ النموذج."""
    exp = set(expanded or [])
    rows = []

    def walk(n, depth, visible):
        disc_ok = (discipline_filter is None or not discipline_filter
                   or n["discipline"] is None
                   or n["discipline"] in discipline_filter)
        lvl = n["meta"].get("level_index")
        level_ok = (level_filter is None or lvl is None or lvl == level_filter)
        show = visible and disc_ok and level_ok
        if show:
            rows.append({"node_id": n["node_id"], "kind": n["kind"], "name": n["name"],
                         "depth": depth, "discipline": n["discipline"],
                         "has_children": bool(n["children"]),
                         "expanded": n["node_id"] in exp,
                         "selectable": n["selectable"]})
        child_visible = show and (n["node_id"] in exp or depth == 0)
        for c in n["children"]:
            walk(c, depth + 1, child_visible)
    walk(tree["root"], 0, True)
    return {"rows": rows, "row_count": len(rows), "writes_to_model": False}


# ---------------------------------------------------------- الفاحص -------
def inspector_model(project, target_id, arch=None, visual_scene=None,
                    coordination=None, lang="en"):
    """نموذج الفاحص: هوية · هندسة · خواصّ · علاقات · ملاحظات · مصدر.
    يستعمل عقد القابلية للتحرير من المرحلة 5 حرفياً."""
    model = project["model"]
    bid = project.get("building_id") or "bld_0"
    props = AU.editable_properties(model, target_id, bid)
    if not props["valid"] or props.get("properties") is None:
        return {"valid": False, "issues": props["issues"], "target_id": target_id,
                "sections": None,
                "note": "the target does not resolve to an inspectable element"}
    p = props["properties"]
    res = AU.resolve_target(model, target_id, bid)

    fields = []
    for f in p["fields"]:
        dv = display_value(None if f["value"] == "NOT_SPECIFIED" else f["value"],
                           f["editability"], lang)
        fields.append({"field": f["field"], "editability": f["editability"],
                       "source": f["source"],
                       "provenance_label": resolve_provenance_label(f["source"], lang),
                       "display": dv, "constraints": f["constraints"],
                       "editable": f["editability"] == "EDITABLE" and not p["locked"]})

    identity = {"id": target_id, "kind": p["kind"],
                "discipline": _discipline_of(p["kind"]),
                "level": _level_of(res, model),
                "locked": p["locked"], "lock_reason": p["lock_reason"]}

    relationships = _relationships(model, res, arch, bid)
    issues = _element_issues(project, target_id, res, coordination, bid)

    return {"valid": True, "target_id": target_id, "identity": identity,
            "sections": {
                "IDENTITY": identity,
                "GEOMETRY": [f for f in fields
                             if f["field"].split(".")[-1] in
                             ("rect", "offset", "edge", "x", "z", "area_m2",
                              "width_m", "height_m", "sill_m", "position",
                              "rotation_deg", "w", "d", "start", "end", "length_m",
                              "axis", "elevation_m")],
                "PROPERTIES": [f for f in fields
                               if f["field"].split(".")[-1] not in
                               ("rect", "offset", "edge", "x", "z", "area_m2",
                                "width_m", "height_m", "sill_m", "position",
                                "rotation_deg", "w", "d", "start", "end", "length_m",
                                "axis", "elevation_m")],
                "RELATIONSHIPS": relationships,
                "ISSUES": issues,
                "PROVENANCE": [{"field": f["field"], "source": f["source"],
                                "label": f["provenance_label"]} for f in fields]},
            "operations": available_operations(p["kind"], p["locked"]),
            "editable_count": len([f for f in fields if f["editable"]]),
            "unknown_count": len([f for f in fields if not f["display"]["known"]]),
            "derived_count": len([f for f in fields if f["editability"] == "DERIVED"]),
            "writes_to_model": False,
            "compliance": "NOT_EVALUATED",
            "note": "an unknown value is reported as not specified and never replaced by "
                    "a default; a derived value is read-only and changes only through its "
                    "source; a display-only value is presentation and never engineering data"}


def _discipline_of(kind):
    if kind in ("SPACE", "DOOR", "WINDOW", "OBJECT", "LEVEL", "WALL"):
        return "ARCHITECTURE"
    if kind in ("SITE", "BUILDING"):
        return "SITE"
    return None


def _level_of(res, model):
    if res.get("kind") == "LEVEL":
        return res.get("level_index")
    tmpl = res.get("template")
    if tmpl is None:
        return None
    for lv in (model.get("levels") or []):
        if lv.get("template") == tmpl:
            return lv.get("index")
    return None


def _relationships(model, res, arch, bid):
    out = []
    kind = res.get("kind")
    if kind == "SPACE":
        room = AU._find_room(model, res["template"], res["room_id"])
        for key, rel in (("doors", "HOSTS_DOOR"), ("windows", "HOSTS_WINDOW"),
                         ("objects", "CONTAINS_OBJECT")):
            for j, _x in enumerate(room.get(key) or []):
                suffix = key[:-1] if key != "objects" else "obj"
                nid = (_x.get("id") or "%s.%s.%s.%s_%d" % (bid, res["template"], res["room_id"],
                                           suffix, j)
                       if key != "objects"
                       else "%s.%s.obj_%d" % (res["template"], res["room_id"], j))
                out.append({"relation": rel, "target_id": nid, "resolved": True})
    elif kind in ("DOOR", "WINDOW"):
        out.append({"relation": "HOSTED_BY_SPACE",
                    "target_id": "%s.%s.%s" % (bid, res["template"], res["room_id"]),
                    "resolved": True})
        host = None
        room = AU._find_room(model, res["template"], res["room_id"])
        source = room[res["opening_key"]][res["opening_index"]]
        oid = source.get("id") or "%s.%s.%s.%s_%d" % (
            bid, res["template"], res["room_id"], kind.lower(), res["opening_index"])
        if arch is not None:
            for op in (arch.get("openings") or []):
                if op.get("opening_ref") == oid:
                    host = op.get("host_wall_id")
                    break
        out.append({"relation": "HOSTED_BY_WALL", "target_id": host,
                    "resolved": host is not None})
    elif kind == "OBJECT":
        out.append({"relation": "CONTAINED_BY_SPACE",
                    "target_id": "%s.%s.%s" % (bid, res["template"], res["room_id"]),
                    "resolved": True})
    return out


def _element_issues(project, target_id, res, coordination, bid):
    out = []
    integ = AU.validate_model_integrity(project["model"], bid)
    key = None
    if res.get("kind") == "SPACE":
        key = "%s.%s" % (res["template"], res["room_id"])
    elif res.get("kind") in ("DOOR", "WINDOW"):
        key = AU._opening_reference(project["model"], res["template"], res["room_id"],
                                    res["kind"].lower() + "s", res["opening_index"])
    for i in integ["issues"]:
        if key and str(i.get("subject") or "").startswith(key):
            out.append({"category": "MODEL_INTEGRITY", "code": i["code"],
                        "severity": i["severity"], "detail": i["detail"]})
    if coordination is not None and key:
        for c in (coordination.get("clashes") or []):
            if target_id in (c.get("element_a"), c.get("element_b")):
                out.append({"category": "COORDINATION", "code": c.get("type"),
                            "severity": c.get("severity") or "WARNING",
                            "detail": c.get("note")})
    return out


def available_operations(kind, locked=False):
    """العمليات المتاحة مشتقّة من مفردات أوامر المرحلة 5 ونوع العنصر.
    ما لا يمكن أن ينجح لا يُعرَض."""
    ops = list(ELEMENT_OPERATIONS.get(kind) or ["INSPECT"])
    out = []
    for op in ops:
        if op == "INSPECT":
            out.append({"operation": op, "enabled": True, "reason": None,
                        "command_type": None})
            continue
        enabled = True
        reason = None
        if locked:
            enabled, reason = False, "TARGET_LOCKED"
        elif op not in AU.IMPLEMENTED:
            enabled, reason = False, "COMMAND_NOT_IMPLEMENTED"
        out.append({"operation": op, "enabled": enabled, "reason": reason,
                    "command_type": op if op in AU.COMMAND_TYPES else None})
    return out


# ------------------------------------------------------ مركز الملاحظات ---
def issue_center(project, arch=None, coordination=None, runtime_scene=None,
                 rule_results=None, bid=None):
    """مركز ملاحظات واحد بفئات منفصلة. لا تُسطَّح دلالات مختلفة في عدّاد واحد."""
    b = bid or project.get("building_id") or "bld_0"
    cats = {c: [] for c in ISSUE_CATEGORIES}

    for i in AU.validate_model_integrity(project["model"], b)["issues"]:
        cats["MODEL_INTEGRITY"].append({"code": i["code"], "severity": i["severity"],
                                        "subject": i["subject"], "detail": i["detail"],
                                        "targets": [i["subject"]] if i["subject"] else []})
    if coordination is not None:
        for c in (coordination.get("clashes") or []):
            cats["COORDINATION"].append({
                "code": c.get("type"), "severity": c.get("severity") or "WARNING",
                "subject": c.get("id"), "detail": c.get("note"),
                "targets": [x for x in (c.get("element_a"), c.get("element_b")) if x],
                "discipline_pair": [c.get("discipline_a"), c.get("discipline_b")],
                "status": c.get("status")})
        for c in (coordination.get("semantic_conflicts") or []):
            cats["UNRESOLVED_RELATIONSHIP"].append({
                "code": c.get("type"), "severity": c.get("severity") or "WARNING",
                "subject": c.get("id"), "detail": c.get("note"),
                "targets": [x for x in (c.get("element_a"), c.get("element_b")) if x]})
    if arch is not None:
        for op in (arch.get("openings") or []):
            if op.get("host_status") and op["host_status"] != "resolved":
                cats["UNRESOLVED_RELATIONSHIP"].append({
                    "code": "OPENING_HOST_UNRESOLVED", "severity": "WARNING",
                    "subject": op.get("id"), "detail": op.get("host_note"),
                    "targets": [op.get("id")]})
    if runtime_scene is not None:
        unresolved = runtime_scene.get("counts", {}).get("portals_unresolved", 0)
        if unresolved:
            cats["NAVIGATION"].append({
                "code": "PORTAL_CONNECTIVITY_UNRESOLVED", "severity": "WARNING",
                "subject": "walkability.portals", "targets": [],
                "detail": "%d portal(s) could not have their connectivity derived"
                          % unresolved})
    for keys, cat in ((("structural", "structure"), "STRUCTURAL_DATA"),
                      (("mep",), "MEP_DATA"), (("fls",), "FLS_DATA")):
        if not any(project["model"].get(k) for k in keys):
            cats[cat].append({"code": "DISCIPLINE_NOT_PRESENT", "severity": "INFO",
                              "subject": keys[0], "targets": [],
                              "detail": "the model carries no %s data" % keys[0]})
    if rule_results is not None:
        for r in (rule_results or []):
            cats["RULE_EVALUATION"].append({
                "code": r.get("rule_id"), "severity": "INFO",
                "subject": r.get("rule_id"), "targets": r.get("targets") or [],
                "detail": r.get("note"),
                "rule_status": r.get("status") if r.get("status") in RULE_STATUSES
                else "NOT_EVALUATED"})

    counts = {}
    for c in ISSUE_CATEGORIES:
        counts[c] = {"total": len(cats[c])}
        for s in ISSUE_SEVERITIES:
            counts[c][s] = len([x for x in cats[c] if x.get("severity") == s])
    return {"schema": SCHEMA, "categories": cats, "counts": counts,
            "total": sum(len(cats[c]) for c in ISSUE_CATEGORIES),
            "rule_evaluation_status": "NOT_EVALUATED" if rule_results is None
            else "EVALUATED_SEPARATELY",
            "compliance": "NOT_EVALUATED",
            "writes_to_model": False,
            "note": "categories are kept apart because they mean different things; "
                    "severity and regulatory status are separate axes and no status "
                    "here means safe, compliant or approved"}


def issue_targets(issue):
    """أهداف قابلة للتحديد فقط. الملاحظة التي لا تمثّل هندسياً لا تدّعي هدفاً."""
    t = [x for x in (issue.get("targets") or []) if isinstance(x, str) and x]
    return {"targets": t, "focusable": len(t) > 0, "writes_to_model": False}


# --------------------------------------------------- تغطية المتطلّبات ----
def requirement_coverage(report, lang="en"):
    """تغطية بالفئات. لا صياغة توحي بتنفيذ كل ما طُلب."""
    classes = {c: [] for c in REQUIREMENT_CLASSES}
    items = []
    if isinstance(report, dict):
        items = report.get("items") or report.get("requirements") or []
    elif isinstance(report, list):
        items = report
    for it in items:
        if not isinstance(it, dict):
            continue
        cls = str(it.get("status") or it.get("class") or "UNRESOLVED").upper()
        if cls not in REQUIREMENT_CLASSES:
            cls = "UNRESOLVED"
        classes[cls].append({"text": it.get("text") or it.get("label"),
                             "evidence": it.get("evidence"),
                             "target_ids": it.get("target_ids") or []})
    counts = {c: len(classes[c]) for c in REQUIREMENT_CLASSES}
    total = sum(counts.values())
    return {"classes": classes, "counts": counts, "total": total,
            "unresolved": counts["UNRESOLVED"] + counts["EXCLUDED"],
            "claims_full_coverage": False,
            "writes_to_model": False,
            "note": "requirements are reported per class. Nothing here states that every "
                    "requested item was implemented; unresolved and excluded items are "
                    "listed and counted separately."}


# ----------------------------------------------- المراجع البصرية --------
def presentation_context(project=None):
    """سياق العرض يعيش بجانب المشروع لا داخل النموذج القانوني."""
    return {"schema": SCHEMA, "references": [], "visual_intent": {},
            "project_revision": (project or {}).get("current_revision"),
            "is_engineering_data": False, "writes_to_model": False,
            "note": "visual references and visual intent are presentation context. They "
                    "are never engineering geometry and never enter a model hash."}


def _allowed_ref_uri(v):
    """مصدر مرجع مقبول بقائمة سماح. أي مخطّط آخر مرفوض افتراضاً، فلا ننتظر
    إضافة نمط هجوم جديد إلى قائمة حظر قبل أن نرفضه."""
    import re as _re
    if not isinstance(v, str) or not v:
        return False
    low = v.strip().lower()
    if _unsafe_ref(low):
        return False
    if low.startswith("https:") or low.startswith("http:") or low.startswith("blob:"):
        return True
    if low.startswith("data:"):
        return low.startswith("data:image/") and ";base64," in low \
            and "svg" not in low.split(",")[0]
    if ":" in low.split("/")[0]:
        return False
    return _re.match(r"^[a-z0-9._~/\-]+$", low) is not None


def _unsafe_ref(*values):
    """مصدر مرجع أو تعليقه لا حاجة فيه لوسم أو شيفرة — يُرفض صراحةً."""
    joined = " ".join(str(v or "") for v in values).lower()
    return any(str(p).lower() in joined for p in REFERENCE_UNSAFE)


def attach_reference(context, kind, scope, scope_id, uri, provenance=None,
                     caption=None):
    """يربط مرجعاً بصرياً. لا يستنتج بعداً هندسياً من صورة، ولا يمسّ النموذج."""
    issues = []
    k = str(kind).upper() if isinstance(kind, str) else None
    s = str(scope).upper() if isinstance(scope, str) else None
    if k not in REFERENCE_KINDS:
        issues.append({"code": "INVALID_PARAMETER", "severity": "ERROR",
                       "subject": kind, "detail": "unknown reference kind"})
    if s not in REFERENCE_SCOPES:
        issues.append({"code": "INVALID_PARAMETER", "severity": "ERROR",
                       "subject": scope, "detail": "unknown reference scope"})
    if not isinstance(uri, str) or not uri:
        issues.append({"code": "INVALID_PARAMETER", "severity": "ERROR",
                       "subject": "uri", "detail": "a reference needs a source"})
    elif (AU._scan_payload({"uri": uri, "caption": caption})
            or _unsafe_ref(uri, caption) or not _allowed_ref_uri(uri)):
        issues.append({"code": "PAYLOAD_REJECTED", "severity": "ERROR",
                       "subject": "uri",
                       "detail": "the reference carries an unsafe or executable value"})
    if issues:
        return {"valid": False, "issues": issues, "context": context,
                "reference": None}
    ref = {"reference_id": "ref:" + AU._sha16({"kind": k, "scope": s,
                                               "scope_id": scope_id, "uri": uri}),
           "kind": k, "scope": s, "scope_id": scope_id, "uri": uri,
           "caption": caption if isinstance(caption, str) else None,
           "provenance": provenance if isinstance(provenance, str) else "user",
           "is_engineering_data": False,
           "affects_geometry": False,
           "note": "visual context only; no dimension is inferred from this image"}
    new_ctx = _copy(context)
    new_ctx["references"] = list(new_ctx.get("references") or []) + [ref]
    return {"valid": True, "issues": [], "context": new_ctx, "reference": ref}


def set_visual_intent(context, field, value):
    """نيّة بصرية — سياق عرض لا معنى هندسي له."""
    if field not in VISUAL_INTENT_FIELDS:
        return {"valid": False, "context": context,
                "issues": [{"code": "INVALID_PARAMETER", "severity": "ERROR",
                            "subject": field, "detail": "unknown visual intent field"}]}
    if AU._scan_payload({field: value}):
        return {"valid": False, "context": context,
                "issues": [{"code": "PAYLOAD_REJECTED", "severity": "ERROR",
                            "subject": field, "detail": "unsafe value"}]}
    new_ctx = _copy(context)
    new_ctx.setdefault("visual_intent", {})
    new_ctx["visual_intent"][field] = value
    return {"valid": True, "context": new_ctx, "issues": [],
            "is_engineering_data": False}


# -------------------------------------------------- حدّ حالة الواجهة ----
def classify_state_key(key):
    return STATE_OWNERSHIP.get(key)


def ui_state_default():
    return {"selected_id": None, "hovered_id": None, "tree_expanded": [],
            "active_panel": SPEC["default_panel"], "language": SPEC["default_language"],
            "theme": "dark", "ui_mode": SPEC["default_ui_mode"],
            "level_filter": None, "discipline_filter": [], "issue_filter": None,
            "reference_panel_open": False, "display_unit": CANONICAL_UNIT,
            "writes_to_model": False}


def model_hash_of(project):
    """بصمة النموذج تُحسب من النموذج القانوني وحده."""
    return AU.model_hash(project["model"], "building",
                         project.get("building_id") or "bld_0")


def assert_ui_state_excluded(project, ui_state):
    """يثبت أن أي مفتاح تملكه الواجهة أو زمن التشغيل لا يدخل بصمة النموذج."""
    before = model_hash_of(project)
    leaked = []
    for key in sorted(ui_state.keys()):
        owner = classify_state_key(key)
        if owner in ("UI_STATE", "RUNTIME_STATE", "PRESENTATION_OUTPUT"):
            if key in project["model"]:
                leaked.append(key)
    after = model_hash_of(project)
    return {"model_hash_before": before, "model_hash_after": after,
            "unchanged": before == after, "leaked_keys": leaked,
            "clean": before == after and not leaked}


# ------------------------------------------------------------ التصدير ---
def export_descriptor(project, kind, source="COMMITTED", view=None, created_at=None):
    """واصف تصدير. الافتراضي من المراجعة المودَعة، والمعاينة تُسمّى معاينة."""
    issues = []
    k = str(kind).upper() if isinstance(kind, str) else None
    s = str(source).upper() if isinstance(source, str) else None
    if k not in EXPORT_KINDS:
        issues.append({"code": "INVALID_PARAMETER", "severity": "ERROR",
                       "subject": kind, "detail": "unknown export kind"})
    if s not in EXPORT_SOURCES:
        issues.append({"code": "INVALID_PARAMETER", "severity": "ERROR",
                       "subject": source, "detail": "unknown export source"})
    if issues:
        return {"valid": False, "issues": issues, "descriptor": None}
    name = str((project["model"].get("meta") or {}).get("name") or "project")
    safe = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")) or "project"
    rev = str(project.get("current_revision") or "").replace(":", "_")
    prefix = "PREVIEW_" if s == "PREVIEW" else ""
    ext = {"PROJECT_JSON": "json", "GLB": "glb", "SNAPSHOT_PNG": "png",
           "REVISION_HISTORY_JSON": "json", "ISSUE_REPORT_JSON": "json"}[k]
    return {"valid": True, "issues": [], "descriptor": {
        "kind": k, "source": s, "is_preview": s == "PREVIEW",
        "filename": "%s%s_%s.%s" % (prefix, safe, rev, ext),
        "metadata": {"project_name": name,
                     "revision_id": project.get("current_revision"),
                     "model_hash": project.get("model_hash"),
                     "view": view, "source": s, "created_at": created_at},
        "certifies_nothing": True,
        "note": "an export is a presentation output taken from the named revision. "
                "It implies no certification, approval or compliance."}}


# ----------------------------------------------------- مساعد المنتج ----
def assistant_claim(kind, text, evidence=None):
    """كل عبارة يقولها المساعد موسومة بنوعها. الاستنتاج ليس حقيقة نموذج."""
    k = str(kind).upper() if isinstance(kind, str) else None
    if k not in ASSISTANT_CLAIM_CLASSES:
        k = "UNKNOWN"
    return {"claim_class": k, "text": text, "evidence": evidence,
            "is_engineering_authority": False,
            "note": "a claim class states what kind of statement this is; an inference "
                    "is never presented as a model fact"}


def assistant_propose_edit(project, phrase, command, rationale=None):
    """يقترح أمر تأليف. لا يودع، ولا يتجاوز أي بوّابة."""
    bid = project.get("building_id") or "bld_0"
    target = AU.resolve_nl_target(project["model"], phrase, bid) if phrase else None
    if target is not None and not target["valid"]:
        return {"valid": False, "issues": target["issues"],
                "candidates": target.get("candidates") or [],
                "proposal": None, "committed": False,
                "note": "target resolution did not produce a single element; the user "
                        "must choose. Nothing is guessed and nothing is committed."}
    prop = AU.propose_command(command, rationale)
    return {"valid": prop["valid"], "issues": prop["issues"],
            "candidates": (target or {}).get("candidates") or [],
            "proposal": prop.get("proposal"), "committed": False,
            "requires_explicit_confirmation": True,
            "note": "a proposal is not a commit; applying it still passes the full "
                    "authoring validation, revision guard and explicit confirmation"}


# ------------------------------------------------------------ الملخّص ---
def workspace_summary(project, ui_state=None, tree=None, issues=None):
    ui = ui_state or ui_state_default()
    return {"schema": SCHEMA, "version": VERSION, "ui_version": UI_VERSION,
            "project_name": (project["model"].get("meta") or {}).get("name"),
            "current_revision": project.get("current_revision"),
            "model_hash": str(project.get("model_hash"))[:24],
            "revisions": len(project.get("history") or []),
            "ui_mode": ui["ui_mode"], "language": ui["language"],
            "selected_id": ui["selected_id"],
            "tree_nodes": (tree or {}).get("node_count"),
            "issue_total": (issues or {}).get("total"),
            "compliance": "NOT_EVALUATED",
            "ui_writes_to_model": False,
            "runtime_writes_to_model": False,
            "note": "the workspace reads engine outputs and calls canonical APIs; it "
                    "performs no engineering calculation of its own"}
