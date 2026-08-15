# -*- coding: utf-8 -*-
# =============================================================================
# acs_runtime.py — أساس التجوّل التفاعلي وزمن التشغيل الحتمي: تفاعل للقراءة فقط.
#
# يقرأ المشهد البصري المشتقّ ويبني مشهد زمن تشغيل مشتقّاً وحالة زمن تشغيل زائلة:
# أسطح قابلة للمشي · عوائق · بوّابات · قدرات تفاعل · فهرس مكاني · تحديد · إظهار
# وإخفاء · قياس · كاميرا.
#
# مبادئ صارمة:
#   • زمن التشغيل زائل، والنموذج الهندسي غير قابل للتعديل.
#   • التدفّق باتّجاه واحد: نموذج → تنسيق → بصري → مشهد تشغيل → حالة تشغيل.
#     لا مسار كتابة عكسي إطلاقاً.
#   • لا محرّك محاكاة: لا إخلاء ولا حشود ولا حريق ولا دخان ولا موائع ولا حرارة
#     ولا تحليل إنشائي ولا مركبات ولا روبوتات ولا ذكاء اصطناعي ولا تمهيد مسارات.
#   • لا خاصية هندسية تُختلق: ما لا ينصّ عليه المصدر يُعلَن NOT_SPECIFIED.
#   • كل معرّف حتميّ: لا وقت ولا عشوائية ولا UUID ولا ترتيب تكرار.
# =============================================================================
import hashlib
import json
import math
import os

# مصدر واحد للترميز الرقمي القانوني — نفس الرمز الذي تنتجه شيفرة المتصفّح.
import acs_ingest as _ing

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_runtime.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
COMPILER_VERSION = SPEC["compiler_version"]
NAVIGATION_MODES = tuple(SPEC["navigation_modes"])
NAVIGATION_CONTRACTS = SPEC["navigation_contracts"]
DEFAULT_NAVIGATION_MODE = SPEC["default_navigation_mode"]
ORBIT_TARGET_KINDS = tuple(SPEC["orbit_target_kinds"])
CAPSULE_DEFAULTS = SPEC["player_capsule_defaults"]
CAPSULE_LIMITS = SPEC["player_capsule_limits"]
COLLISION_POLICY = SPEC["collision_policy"]
LAYER_DEFAULT_POLICY = SPEC["layer_default_policy"]
DECORATION_COLLISION = SPEC["decoration_collision"]
DECORATION_COLLISION_OPTIONS = tuple(SPEC["decoration_collision_options"])
PORTAL_STATES = tuple(SPEC["portal_states"])
DEFAULT_PORTAL_STATE = SPEC["default_portal_state"]
EXTERIOR_SPACE_ID = SPEC["exterior_space_id"]
VERTICAL_CONNECTION_KINDS = tuple(SPEC["vertical_connection_kinds"])
INTERACTION_ACTIONS = tuple(SPEC["interaction_actions"])
ACTION_TARGETS = SPEC["action_targets"]
INTERACTION_CAPABILITIES = tuple(SPEC["interaction_capabilities"])
VISIBILITY_MODES = tuple(SPEC["visibility_modes"])
DISCIPLINES = tuple(SPEC["disciplines"])
MEASUREMENT_TYPES = tuple(SPEC["measurement_types"])
VALIDATION_CODES = tuple(SPEC["validation_codes"])
SEVERITIES = tuple(SPEC["severities"])
CODE_SEVERITY = SPEC["code_severity"]
MODEL_WRITE_INTENTS = tuple(SPEC["model_write_intents"])
CELL = float(SPEC["spatial_index"]["cell_size_m"])
MAX_CELLS = int(SPEC["spatial_index"]["max_cells_per_entry"])
MAX_ABS_COORD = float(SPEC["spatial_index"]["max_abs_coordinate_m"])

NOT_SPECIFIED = "NOT_SPECIFIED"
_EPS = 1e-9


# ------------------------------------------------------------- أدوات -------
def _enum(v):
    """قيمة تعداد صالحة: نصّ فقط. القوائم والأرقام والكائنات لا تُكرَه على نصّ،
    كي لا يقبل تطبيق ما يرفضه الآخر."""
    return v.upper() if isinstance(v, str) else None


def _q(v):
    """تقريب موحّد للقيم المنشورة — يمنع انحراف الفاصلة بين اللغتين."""
    return round(float(v), 6) + 0.0


def _num(v):
    """رقم حقيقي منتهٍ أو None. NaN و ±inf ليست أرقاماً ولا تُمرَّر بصمت."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _canon(o):
    """صياغة قانونية واحدة عبر اللغتين. الأرقام تُرمَّز برمز موحّد (acs_ingest)
    لأن بايثون تكتب 14.0 وجافاسكربت تكتب 14 — والبصمة لا تحتمل هذا الفارق."""
    return _ing.canonical_json(o)


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _copy(v):
    """نسخة عميقة: زمن التشغيل لا يحتفظ بأي مرجع مشترك مع المصدر."""
    return json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v


def severity_of(code):
    return CODE_SEVERITY.get(code, "ERROR")


def _issue(code, subject=None, detail=None):
    return {"code": code, "severity": severity_of(code),
            "subject": None if subject is None else str(subject),
            "detail": None if detail is None else str(detail),
            "writes_to_model": False}


def _sorted_issues(issues):
    """ترتيب حتميّ: الشدّة ثم الرمز ثم الموضوع ثم التفصيل."""
    return sorted(issues, key=lambda i: (SEVERITIES.index(i["severity"]), str(i["code"]),
                                         str(i.get("subject")), str(i.get("detail"))))


def _ok(issues, **extra):
    out = {"valid": len(issues) == 0, "issues": _sorted_issues(issues),
           "writes_to_model": False}
    out.update(extra)
    return out


# --------------------------------------------------------- هندسة ----------
def _obb(cx, cy, cz, ex, ey, ez, rot_y):
    return {"cx": _q(cx), "cy": _q(cy), "cz": _q(cz),
            "hx": _q(abs(ex) / 2.0), "hy": _q(abs(ey) / 2.0), "hz": _q(abs(ez) / 2.0),
            "yaw": _q(rot_y or 0.0)}


def _aabb_of(o):
    ca, sa = abs(math.cos(o["yaw"])), abs(math.sin(o["yaw"]))
    rx = o["hx"] * ca + o["hz"] * sa
    rz = o["hx"] * sa + o["hz"] * ca
    return [_q(o["cx"] - rx), _q(o["cy"] - o["hy"]), _q(o["cz"] - rz),
            _q(o["cx"] + rx), _q(o["cy"] + o["hy"]), _q(o["cz"] + rz)]


def _aabb_overlap(a, b):
    return not (a[3] <= b[0] + _EPS or b[3] <= a[0] + _EPS or
                a[4] <= b[1] + _EPS or b[4] <= a[1] + _EPS or
                a[5] <= b[2] + _EPS or b[5] <= a[2] + _EPS)


def _proj(o, ax, az):
    c, s = math.cos(o["yaw"]), math.sin(o["yaw"])
    return abs(c * ax + s * az) * o["hx"] + abs(-s * ax + c * az) * o["hz"]


def _obb_overlap(a, b):
    """محور فاصل لصندوقين مدارين حول Y فقط — الهندسة المدارة تُعامَل كما هي."""
    if a["cy"] + a["hy"] <= b["cy"] - b["hy"] + _EPS or \
       b["cy"] + b["hy"] <= a["cy"] - a["hy"] + _EPS:
        return False
    axes = []
    for o in (a, b):
        c, s = math.cos(o["yaw"]), math.sin(o["yaw"])
        axes.append((c, s))
        axes.append((-s, c))
    dx, dz = b["cx"] - a["cx"], b["cz"] - a["cz"]
    for (ax, az) in axes:
        if abs(dx * ax + dz * az) >= _proj(a, ax, az) + _proj(b, ax, az) - 1e-9:
            return False
    return True


def _inv_transform(x, z, transform):
    """يعيد نقطة عالمية إلى إحداثيات النموذج المحلية — لا تقدير ولا تقريب."""
    t = transform or {}
    rot = float(t.get("rotation_deg") or 0.0)
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    r = math.radians(-rot)
    ca, sa = math.cos(r), math.sin(r)
    dx, dz = x - px, z - pz
    return [dx * ca - dz * sa, dx * sa + dz * ca]


def _fwd_transform(x, z, transform):
    t = transform or {}
    rot = float(t.get("rotation_deg") or 0.0)
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    r = math.radians(rot)
    ca, sa = math.cos(r), math.sin(r)
    return [px + x * ca - z * sa, pz + x * sa + z * ca]


def _in_rect(x, z, rect, tol=0.0):
    return (rect[0] - tol <= x <= rect[0] + rect[2] + tol and
            rect[1] - tol <= z <= rect[1] + rect[3] + tol)


# ------------------------------------------------- سياسة الاصطدام ---------
def _policy(obj, decoration_collision):
    """سياسة معلنة لكل نوع: لا استنتاج من اسم شبكة ولا من مادة ولا من حجم."""
    kind = obj.get("kind")
    layer = obj.get("layer")
    declared = COLLISION_POLICY.get(kind)
    if declared is not None:
        blocking = bool(declared["blocking"])
        walkable = bool(declared["walkable"])
        basis = "declared_kind_policy"
    else:
        d = LAYER_DEFAULT_POLICY.get(layer) or {"blocking": False, "walkable": False}
        blocking = bool(d["blocking"])
        walkable = bool(d["walkable"])
        basis = "layer_default_policy"
    if obj.get("visual_only"):
        walkable = False
        if layer == "FURNITURE":
            blocking = (decoration_collision == "BLOCKING")
            basis = "declared_decoration_policy"
        else:
            blocking = False
            basis = "visual_only_never_blocking"
    return (blocking, walkable, basis)


# --------------------------------------------- تصريف مشهد زمن التشغيل ----
def _rid(pattern_key, *parts):
    pat = SPEC["runtime_id_patterns"][pattern_key]
    prefix = pat.split("<")[0]
    return prefix + ":".join(str(p) for p in parts) if False else prefix + str(parts[0])


def compile_runtime_scene(visual_scene, runtime_config=None):
    """يبني مشهد زمن تشغيل مشتقّاً وحتمياً. لا يعدّل المشهد البصري ولا أي نموذج."""
    issues = []
    cfg = runtime_config if isinstance(runtime_config, dict) else {}
    if runtime_config is not None and not isinstance(runtime_config, dict):
        issues.append(_issue("RUNTIME_CONFIG_INVALID", "runtime_config",
                             "configuration must be an object"))
    if visual_scene is None:
        return _runtime_failure(issues + [_issue("RUNTIME_SOURCE_SCENE_MISSING",
                                                 "visual_scene", "no source scene supplied")])
    if not isinstance(visual_scene, dict) or not isinstance(visual_scene.get("objects"), list) \
       or not visual_scene.get("scene_id"):
        return _runtime_failure(issues + [_issue("RUNTIME_SOURCE_SCENE_INVALID", "visual_scene",
                                                 "source scene is not a compiled visual scene")])
    if cfg.get("writes_to_model"):
        issues.append(_issue("RUNTIME_MODEL_WRITE_ATTEMPT", "runtime_config",
                             "writes_to_model may never be requested"))

    _dc = cfg.get("decoration_collision")
    deco = DECORATION_COLLISION if _dc is None or _dc == "" else _enum(_dc)
    if deco not in DECORATION_COLLISION_OPTIONS:
        issues.append(_issue("RUNTIME_CONFIG_INVALID", "decoration_collision", deco))
        deco = DECORATION_COLLISION

    transform = _copy(visual_scene.get("transform")) or {"position": {"x": 0.0, "z": 0.0},
                                                         "rotation_deg": 0.0}
    src_objects = visual_scene.get("objects") or []
    spaces_src = visual_scene.get("spaces_index") or []

    # ------------------------------------------------ أجسام زمن التشغيل --
    objects, obstacles, seen_ids = [], [], {}
    door_objects = []
    for o in src_objects:
        if not isinstance(o, dict) or not o.get("id") or not isinstance(o.get("geometry"), dict):
            issues.append(_issue("RUNTIME_SOURCE_OBJECT_INVALID",
                                 (o or {}).get("id") if isinstance(o, dict) else None,
                                 "object is missing an id or a geometry"))
            continue
        g = o["geometry"]
        vals = [_num(g.get(k)) for k in ("cx", "cy", "cz", "ex", "ey", "ez")]
        if any(v is None for v in vals):
            issues.append(_issue("RUNTIME_SOURCE_OBJECT_INVALID", o["id"],
                                 "geometry carries a non-finite or missing value"))
            continue
        rot = _num(g.get("rot_y"))
        if rot is None:
            issues.append(_issue("RUNTIME_SOURCE_OBJECT_INVALID", o["id"],
                                 "geometry carries a non-finite rotation"))
            continue
        rid = "runtime:obj:" + str(o["id"])
        if rid in seen_ids:
            issues.append(_issue("RUNTIME_ID_DUPLICATE", rid, "duplicate runtime object id"))
            continue
        seen_ids[rid] = True
        blocking, walkable, basis = _policy(o, deco)
        box = _obb(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], rot)
        visual_only = bool(o.get("visual_only"))
        ro = {"runtime_object_id": rid,
              "source_element_id": o.get("source_element_id"),
              "visual_object_id": o["id"],
              "kind": o.get("kind"), "discipline": o.get("layer"),
              "level_index": o.get("level_index") if o.get("level_index") is not None else None,
              "space_id": o.get("space_id"),
              "visual_only": visual_only,
              "visual_class": o.get("visual_class"),
              "obb": box, "aabb": _aabb_of(box),
              "collision": {"blocking": blocking, "walkable": walkable, "basis": basis},
              "interaction": {"selectable": True, "inspectable": True,
                              "focusable": True, "measurable": True, "hideable": True},
              "geometry_source": o.get("geometry_source"),
              "source_scene": visual_scene.get("scene_id")}
        objects.append(ro)
        if blocking:
            obstacles.append({"obstacle_id": "obstacle:" + str(o["id"]),
                              "runtime_object_id": rid,
                              "source_element_id": o.get("source_element_id"),
                              "kind": o.get("kind"), "discipline": o.get("layer"),
                              "level_index": ro["level_index"],
                              "blocking": True, "basis": basis,
                              "obb": _copy(box), "bounds": _copy(ro["aabb"])})
        if o.get("kind") == "DOOR":
            door_objects.append(o)
    objects.sort(key=lambda r: str(r["runtime_object_id"]))
    obstacles.sort(key=lambda r: str(r["obstacle_id"]))

    # ------------------------------------------------- الأسطح والغرف ----
    rooms, surfaces = [], []
    for s in spaces_src:
        rect = s.get("rect") if isinstance(s.get("rect"), list) else None
        if not rect or len(rect) != 4 or any(_num(v) is None for v in rect) \
           or _num(rect[2]) <= 0 or _num(rect[3]) <= 0:
            issues.append(_issue("WALKABLE_SURFACE_INVALID", (s or {}).get("id"),
                                 "space rectangle is missing or not positive"))
            continue
        elev = _num(s.get("_elev"))
        if elev is None:
            issues.append(_issue("WALKABLE_SURFACE_INVALID", s.get("id"),
                                 "space carries no finite level elevation"))
            continue
        sid = s.get("id")
        support = None
        for ro in objects:
            if ro["collision"]["walkable"] and ro["kind"] in ("SLAB", "STRUCTURAL_SLAB") \
               and ro["level_index"] == s.get("level_index"):
                support = ro["source_element_id"]
                break
        rooms.append({"runtime_room_id": "runtime:room:" + str(sid),
                      "space_id": s.get("space_id"), "space_instance_id": sid,
                      "name": s.get("name"), "level_index": s.get("level_index"),
                      "rect_local": [_q(v) for v in rect],
                      "elevation_m": _q(elev), "area_m2": _num(s.get("area_m2")),
                      "source_scene": visual_scene.get("scene_id")})
        surfaces.append({"surface_id": "walk:space:" + str(sid),
                         "source_element_id": sid,
                         "runtime_room_id": "runtime:room:" + str(sid),
                         "space_id": s.get("space_id"),
                         "level_id": s.get("level_index"),
                         "level_index": s.get("level_index"),
                         "walkable": True, "basis": "space_rectangle",
                         "rect_local": [_q(v) for v in rect],
                         "elevation_m": _q(elev),
                         "support_element_id": support})
    rooms.sort(key=lambda r: str(r["runtime_room_id"]))
    surfaces.sort(key=lambda r: str(r["surface_id"]))

    # ----------------------------------------------------- البوّابات ----
    portals, seen_portals = [], {}
    wall_by_id = {}
    for o in src_objects:
        if isinstance(o, dict) and o.get("kind") == "WALL" and o.get("source_element_id"):
            wall_by_id[o["source_element_id"]] = o
    for d in sorted(door_objects, key=lambda x: str(x["id"])):
        pid = "portal:" + str(d.get("source_element_id") or d["id"])
        if pid in seen_portals:
            issues.append(_issue("PORTAL_DUPLICATE", pid, "duplicate portal id"))
            continue
        seen_portals[pid] = True
        host_id = d.get("host_wall_id")
        host = wall_by_id.get(host_id)
        g = d["geometry"]
        thin_x = _num(g.get("ex")) <= _num(g.get("ez"))
        # الفتحة رقيقة على محور واحد: ذلك المحور هو ناظم الجدار
        probe = 0.6
        wx, wz = _num(g.get("cx")), _num(g.get("cz"))
        if thin_x:
            probes = [(wx - probe, wz), (wx + probe, wz)]
        else:
            probes = [(wx, wz - probe), (wx, wz + probe)]
        lvl = d.get("level_index")
        found = []
        for (px, pz) in probes:
            lx, lz = _inv_transform(px, pz, transform)
            hit = None
            for r in rooms:
                if r["level_index"] != lvl:
                    continue
                if _in_rect(lx, lz, r["rect_local"]):
                    hit = r["space_id"]
                    break
            found.append(hit)
        sides = [f for f in found if f]
        exterior_host = bool(host and host.get("exposure") == "exterior")
        if len(sides) == 2 and sides[0] != sides[1]:
            frm, to, basis, resolved = sides[0], sides[1], "two_space_probe", True
        elif len(sides) == 1 and exterior_host:
            frm, to, basis, resolved = sides[0], EXTERIOR_SPACE_ID, \
                "one_space_probe_exterior", True
        else:
            frm = sides[0] if sides else None
            to, basis, resolved = None, "unresolved", False
        p = {"portal_id": pid,
             "source_element_id": d.get("source_element_id"),
             "visual_object_id": d["id"],
             "host_wall_id": host_id,
             "host_wall_resolved": host is not None,
             "level_index": lvl,
             "from_space": frm, "to_space": to,
             "connectivity_basis": basis, "connectivity_resolved": resolved,
             "default_state": DEFAULT_PORTAL_STATE,
             "aperture": _copy(_obb(wx, _num(g.get("cy")), wz,
                                    _num(g.get("ex")) + (0.0 if thin_x else 0.0),
                                    _num(g.get("ey")),
                                    _num(g.get("ez")), _num(g.get("rot_y")))),
             "source_scene": visual_scene.get("scene_id"),
             "note": "a runtime portal derived from a modelled door; the door itself is "
                     "untouched and no access control is implied"}
        if host_id and host is None:
            issues.append(_issue("PORTAL_REFERENCE_INVALID", pid,
                                 "host wall %s does not resolve in the source scene" % host_id))
        portals.append(p)
    portals.sort(key=lambda p: str(p["portal_id"]))

    # ------------------------------------------- الوصلات الرأسية -------
    vertical = []
    for ro in objects:
        if ro["kind"] not in VERTICAL_CONNECTION_KINDS:
            continue
        vertical.append({"vertical_id": "vertical:" + str(ro["source_element_id"] or
                                                          ro["visual_object_id"]),
                         "source_element_id": ro["source_element_id"],
                         "kind": ro["kind"],
                         "bounds": _copy(ro["aabb"]),
                         "note": "a modelled vertical connection; no lift or escalator "
                                 "operation is simulated"})
    vertical.sort(key=lambda v: str(v["vertical_id"]))

    # --------------------------------------------------- الفهرس المكاني -
    index = _build_index(obstacles, surfaces, transform)

    scene = {
        "schema": SCHEMA, "version": VERSION, "compiler_version": COMPILER_VERSION,
        "runtime_id": "runtime:" + str(visual_scene.get("scene_id")),
        "source_scene": visual_scene.get("scene_id"),
        "source_signature": _sha16({"scene": visual_scene.get("scene_id"),
                                    "model_hash": visual_scene.get("model_hash"),
                                    "objects": len(src_objects)}),
        "model_hash": visual_scene.get("model_hash"),
        "building_id": visual_scene.get("building_id"),
        "transform": transform,
        "walkability": {"surfaces": surfaces, "obstacles": obstacles,
                        "portals": portals, "vertical_connections": vertical},
        "objects": objects,
        "rooms": rooms,
        "spatial_index": index,
        "defaults": {"navigation_mode": DEFAULT_NAVIGATION_MODE,
                     "player_capsule": _copy(CAPSULE_DEFAULTS),
                     "decoration_collision": deco,
                     "spawn": {}},
        "issues": _sorted_issues(issues),
        "writes_to_model": False,
        "meta": {"note": SPEC["note"], "derivation": SPEC["derivation_note"],
                 "ephemerality": SPEC["ephemerality_note"],
                 "compliance": "NOT_EVALUATED"}}
    scene["defaults"]["spawn"] = _default_spawn(scene)
    scene["counts"] = _counts(scene)
    # القبول معلن صراحةً: مشهد يحمل خطأ واحداً لا يُقدَّم على أنه صالح.
    scene["accepted"] = all(i["severity"] != "ERROR" for i in scene["issues"])
    return scene


def _runtime_failure(issues):
    return {"schema": SCHEMA, "version": VERSION, "compiler_version": COMPILER_VERSION,
            "runtime_id": None, "source_scene": None, "source_signature": None,
            "model_hash": None, "building_id": None,
            "transform": {"position": {"x": 0.0, "z": 0.0}, "rotation_deg": 0.0},
            "walkability": {"surfaces": [], "obstacles": [], "portals": [],
                            "vertical_connections": []},
            "objects": [], "rooms": [],
            "spatial_index": {"cell_size_m": CELL, "cells": 0, "entries": 0,
                              "oversized": 0, "buckets": {}},
            "defaults": {"navigation_mode": DEFAULT_NAVIGATION_MODE,
                         "player_capsule": _copy(CAPSULE_DEFAULTS),
                         "decoration_collision": DECORATION_COLLISION, "spawn": {}},
            "issues": _sorted_issues(issues), "writes_to_model": False,
            "accepted": False,
            "counts": {"objects": 0, "obstacles": 0, "surfaces": 0, "portals": 0,
                       "portals_unresolved": 0, "rooms": 0, "vertical_connections": 0},
            "meta": {"note": SPEC["note"], "derivation": SPEC["derivation_note"],
                     "ephemerality": SPEC["ephemerality_note"],
                     "compliance": "NOT_EVALUATED"}}


def _counts(scene):
    w = scene["walkability"]
    return {"objects": len(scene["objects"]), "obstacles": len(w["obstacles"]),
            "surfaces": len(w["surfaces"]), "portals": len(w["portals"]),
            "portals_unresolved": sum(1 for p in w["portals"]
                                      if not p["connectivity_resolved"]),
            "rooms": len(scene["rooms"]),
            "vertical_connections": len(w["vertical_connections"]),
            "visual_only_objects": sum(1 for o in scene["objects"] if o["visual_only"]),
            "issues": len(scene["issues"])}


# ------------------------------------------------------ الفهرس المكاني ---
def _finite_box(aabb):
    """صندوق صالح للفهرسة: ستّة أعداد منتهية. غير ذلك لا يُعدّ خلايا إطلاقاً."""
    if not isinstance(aabb, (list, tuple)) or len(aabb) != 6:
        return None
    vals = [_num(v) for v in aabb]
    if any(v is None for v in vals):
        return None
    if any(abs(v) > MAX_ABS_COORD for v in vals):
        return None
    return vals


def _cells_of(aabb):
    box = _finite_box(aabb)
    if box is None:
        return []
    out = []
    for ix in range(int(math.floor(box[0] / CELL)), int(math.floor(box[3] / CELL)) + 1):
        for iz in range(int(math.floor(box[2] / CELL)), int(math.floor(box[5] / CELL)) + 1):
            out.append("%d|%d" % (ix, iz))
    return out


def _cell_span(aabb):
    box = _finite_box(aabb)
    if box is None:
        return float("inf")
    nx = int(math.floor(box[3] / CELL)) - int(math.floor(box[0] / CELL)) + 1
    nz = int(math.floor(box[5] / CELL)) - int(math.floor(box[2] / CELL)) + 1
    return nx * nz


def _surface_world_aabb(s, transform):
    r = s["rect_local"]
    pts = [_fwd_transform(r[0], r[1], transform), _fwd_transform(r[0] + r[2], r[1], transform),
           _fwd_transform(r[0], r[1] + r[3], transform),
           _fwd_transform(r[0] + r[2], r[1] + r[3], transform)]
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return [_q(min(xs)), _q(s["elevation_m"]), _q(min(zs)),
            _q(max(xs)), _q(s["elevation_m"]), _q(max(zs))]


def _build_index(obstacles, surfaces, transform):
    buckets, oversized, entries = {}, [], []
    for o in obstacles:
        entries.append(("obstacle", o["obstacle_id"], o["bounds"]))
    for s in surfaces:
        entries.append(("surface", s["surface_id"], _surface_world_aabb(s, transform)))
    for kind, eid, box in entries:
        if _cell_span(box) > MAX_CELLS:
            oversized.append(eid)
            continue
        for c in _cells_of(box):
            buckets.setdefault(c, []).append(eid)
    for c in buckets:
        buckets[c] = sorted(buckets[c])
    return {"cell_size_m": CELL, "cells": len(buckets), "entries": len(entries),
            "oversized": len(sorted(oversized)),
            "oversized_ids": sorted(oversized),
            "buckets": {k: buckets[k] for k in sorted(buckets)}}


def query_spatial_index(runtime_scene, aabb):
    """مرشّحون من الخلايا التي يلامسها الاستعلام فقط — لا مسح لكل الأجسام."""
    idx = runtime_scene.get("spatial_index") or {}
    buckets = idx.get("buckets") or {}
    hit = {}
    # صندوق استعلام أوسع من سقف الخلايا المعلن لا يُعدّ خليةً خلية — يُعلَن مسحاً
    # كاملاً صراحةً بدل تفجير الذاكرة أو ادّعاء تسريع لم يحدث.
    span = _cell_span(aabb)
    if span != span or span in (float("inf"), float("-inf")) or span > MAX_CELLS:
        for c in buckets:
            for eid in buckets[c]:
                hit[eid] = True
        for eid in idx.get("oversized_ids") or []:
            hit[eid] = True
        all_ids = sorted(hit.keys())
        return {"candidate_ids": all_ids, "candidate_count": len(all_ids),
                "scanned_cells": 0, "total_entries": idx.get("entries", 0),
                "full_scan": True}
    cells = _cells_of(aabb)
    for c in cells:
        for eid in buckets.get(c, []):
            hit[eid] = True
    for eid in idx.get("oversized_ids") or []:
        hit[eid] = True
    ids = sorted(hit.keys())
    return {"candidate_ids": ids, "candidate_count": len(ids),
            "scanned_cells": len(cells),
            "total_entries": idx.get("entries", 0),
            "full_scan": False}


# -------------------------------------------------------- كبسولة اللاعب --
def validate_capsule(capsule):
    """كبسولة مُتحقَّق منها — لا نقطة كاميرا بلا حجم، ولا ثوابت خفيّة."""
    issues = []
    c = capsule if isinstance(capsule, dict) else {}
    if capsule is not None and not isinstance(capsule, dict):
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "capsule", "capsule must be an object"))
    r = _num(c.get("radius_m", CAPSULE_DEFAULTS["radius_m"]))
    h = _num(c.get("height_m", CAPSULE_DEFAULTS["height_m"]))
    e = _num(c.get("eye_height_m", CAPSULE_DEFAULTS["eye_height_m"]))
    if r is None:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "radius_m", "not a finite number"))
    elif r <= 0:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "radius_m", "must be greater than zero"))
    elif r < CAPSULE_LIMITS["min_radius_m"] or r > CAPSULE_LIMITS["max_radius_m"]:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "radius_m", "outside the declared limits"))
    if h is None:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "height_m", "not a finite number"))
    elif h <= 0:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "height_m", "must be greater than zero"))
    elif h < CAPSULE_LIMITS["min_height_m"] or h > CAPSULE_LIMITS["max_height_m"]:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "height_m", "outside the declared limits"))
    if r is not None and h is not None and r > 0 and h > 0 and h <= 2.0 * r:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "height_m",
                             "height must exceed twice the radius"))
    if e is None:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "eye_height_m", "not a finite number"))
    elif e <= 0:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "eye_height_m",
                             "must be greater than zero"))
    elif h is not None and e > h:
        issues.append(_issue("PLAYER_CAPSULE_INVALID", "eye_height_m",
                             "must not exceed the capsule height"))
    resolved = None
    if not issues:
        resolved = {"radius_m": _q(r), "height_m": _q(h), "eye_height_m": _q(e)}
    return _ok(issues, capsule=resolved)


def _capsule_box(position, capsule):
    r, h = capsule["radius_m"], capsule["height_m"]
    return _obb(position[0], position[1] + h / 2.0, position[2], 2 * r, h, 2 * r, 0.0)


# --------------------------------------------------------- الملاحة -------
def validate_navigation(mode, target=None, runtime_scene=None):
    """كل وضع تنقّل عقد معلن. الوضع المجهول يفشل حتمياً ولا يُستبدَل بصمت."""
    issues = []
    m = _enum(mode)
    if m not in NAVIGATION_MODES:
        issues.append(_issue("NAVIGATION_MODE_INVALID", mode, "unknown navigation mode"))
        return _ok(issues, mode=None, contract=None)
    contract = _copy(NAVIGATION_CONTRACTS[m])
    if contract["targeted"] and target is not None:
        tk = _enum((target or {}).get("kind")) or ""
        tid = (target or {}).get("id")
        if tk not in ORBIT_TARGET_KINDS:
            issues.append(_issue("NAVIGATION_TARGET_INVALID", tk or None,
                                 "target kind is not a declared orbit target"))
        elif tk != "BUILDING" and runtime_scene is not None:
            if not _target_exists(runtime_scene, tk, tid):
                issues.append(_issue("NAVIGATION_TARGET_INVALID", tid,
                                     "target does not resolve in the runtime scene"))
    if (not contract["targeted"]) and target is not None:
        issues.append(_issue("NAVIGATION_TARGET_INVALID", (target or {}).get("id"),
                             "this navigation mode accepts no target"))
    return _ok(issues, mode=m if not issues else None,
               contract=contract if not issues else None)


def _target_exists(scene, kind, tid):
    if kind == "OBJECT":
        return any(o["runtime_object_id"] == tid or o["visual_object_id"] == tid
                   or o["source_element_id"] == tid for o in scene.get("objects") or [])
    if kind == "ROOM":
        return any(r["runtime_room_id"] == tid or r["space_instance_id"] == tid
                   or r["space_id"] == tid for r in scene.get("rooms") or [])
    if kind == "FLOOR":
        return any(r["level_index"] == tid for r in scene.get("rooms") or [])
    return False


# ------------------------------------------------ الظهور والدخول ---------
def validate_spawn(runtime_scene, position, capsule=None, level_index=None):
    """يرفض الظهور داخل جدار أو عمود أو عائق، وخارج مساحة قابلة للمشي."""
    issues = []
    cap = validate_capsule(capsule)
    if not cap["valid"]:
        return _ok(cap["issues"] + [_issue("SPAWN_INVALID", "capsule",
                                           "spawn requires a valid capsule")],
                   position=None, surface_id=None)
    c = cap["capsule"]
    if not isinstance(position, (list, tuple)) or len(position) != 3 \
       or any(_num(v) is None for v in position):
        issues.append(_issue("SPAWN_INVALID", "position",
                             "position must be three finite numbers"))
        return _ok(issues, position=None, surface_id=None)
    p = [_num(v) for v in position]
    surface = _surface_at(runtime_scene, p, level_index)
    if surface is None:
        issues.append(_issue("SPAWN_OUTSIDE_WALKABLE_AREA", "position",
                             "no walkable surface supports this position"))
    box = _capsule_box(p, c)
    box_aabb = _aabb_of(box)
    cand = query_spatial_index(runtime_scene, box_aabb)["candidate_ids"]
    by_id = {o["obstacle_id"]: o for o in runtime_scene["walkability"]["obstacles"]}
    for eid in cand:
        ob = by_id.get(eid)
        if ob is None:
            continue
        if _aabb_overlap(box_aabb, ob["bounds"]) and _obb_overlap(box, ob["obb"]):
            issues.append(_issue("SPAWN_INSIDE_OBSTACLE", ob["obstacle_id"],
                                 "capsule intersects %s" % (ob["kind"],)))
    return _ok(issues, position=[_q(p[0]), _q(p[1]), _q(p[2])] if not issues else None,
               surface_id=surface["surface_id"] if surface else None,
               candidate_count=cand.__len__())


def _surface_at(runtime_scene, p, level_index=None):
    lx, lz = _inv_transform(p[0], p[2], runtime_scene.get("transform"))
    best = None
    for s in runtime_scene["walkability"]["surfaces"]:
        if level_index is not None and s["level_index"] != level_index:
            continue
        if not _in_rect(lx, lz, s["rect_local"]):
            continue
        if p[1] + 1e-6 < s["elevation_m"] - 0.05:
            continue                       # تحت البلاطة الحاملة: غير مدعوم
        if p[1] - s["elevation_m"] > 3.5:
            continue                       # فوق المستوى بما يتجاوز طابقاً
        if best is None or s["elevation_m"] > best["elevation_m"]:
            best = s
    return best


def _default_spawn(scene):
    surfaces = scene["walkability"]["surfaces"]
    if not surfaces:
        return {"position": None, "surface_id": None,
                "basis": "no walkable surface exists in this scene"}
    s = sorted(surfaces, key=lambda x: (x["level_index"] if x["level_index"] is not None else 0,
                                        str(x["surface_id"])))[0]
    r = s["rect_local"]
    wx, wz = _fwd_transform(r[0] + r[2] / 2.0, r[1] + r[3] / 2.0, scene.get("transform"))
    return {"position": [_q(wx), _q(s["elevation_m"]), _q(wz)],
            "surface_id": s["surface_id"], "basis": "centre of the first walkable surface"}


def find_nearest_valid_spawn(runtime_scene, position, capsule=None, level_index=None,
                             max_radius_m=6.0, step_m=0.5):
    """بحث حتميّ عن أقرب موضع صالح — ترتيب ثابت، ولا تحريك لأي هندسة."""
    base = validate_spawn(runtime_scene, position, capsule, level_index)
    if base["valid"]:
        return _ok([], position=base["position"], surface_id=base["surface_id"],
                   moved=False, search_steps=0)
    if not isinstance(position, (list, tuple)) or len(position) != 3 \
       or any(_num(v) is None for v in position):
        return _ok([_issue("SPAWN_INVALID", "position",
                           "position must be three finite numbers")],
                   position=None, surface_id=None, moved=False, search_steps=0)
    p = [_num(v) for v in position]
    r = _num(max_radius_m) or 6.0
    st = _num(step_m) or 0.5
    if st <= 0:
        st = 0.5
    steps = 0
    ring = 1
    while ring * st <= r:
        offs = []
        n = max(8, ring * 8)
        for k in range(n):
            ang = 2.0 * math.pi * k / n
            offs.append((_q(math.cos(ang) * ring * st), _q(math.sin(ang) * ring * st)))
        for (dx, dz) in sorted(offs):
            steps += 1
            cand = [p[0] + dx, p[1], p[2] + dz]
            res = validate_spawn(runtime_scene, cand, capsule, level_index)
            if res["valid"]:
                return _ok([], position=res["position"], surface_id=res["surface_id"],
                           moved=True, search_steps=steps)
        ring += 1
    return _ok([_issue("SPAWN_NO_VALID_POSITION_FOUND", "position",
                       "no valid position within the search radius")],
               position=None, surface_id=None, moved=False, search_steps=steps)


# -------------------------------------------------------- الحركة --------
def move_query(runtime_scene, runtime_state, start, end):
    """استعلام حركة: مرشّحون من الفهرس ثم فحص دقيق. البوّابة المفتوحة تسمح
    بالمرور عبر جدارها المضيف، والمغلقة تمنعه."""
    issues = []
    cap = (runtime_state or {}).get("player_capsule") or _copy(CAPSULE_DEFAULTS)
    cv = validate_capsule(cap)
    if not cv["valid"]:
        return _ok(cv["issues"], allowed=False, blocked_by=None, reason="invalid capsule")
    c = cv["capsule"]
    for name, pt in (("start", start), ("end", end)):
        if not isinstance(pt, (list, tuple)) or len(pt) != 3 \
           or any(_num(v) is None for v in pt):
            issues.append(_issue("SPAWN_INVALID", name, "point must be three finite numbers"))
    if issues:
        return _ok(issues, allowed=False, blocked_by=None, reason="invalid point")
    s = [_num(v) for v in start]
    e = [_num(v) for v in end]
    mode = (runtime_state or {}).get("navigation_mode") or DEFAULT_NAVIGATION_MODE
    contract = NAVIGATION_CONTRACTS.get(mode) or NAVIGATION_CONTRACTS[DEFAULT_NAVIGATION_MODE]

    sweep = _sweep_box(s, e, c)
    sweep_aabb = _aabb_of(sweep)
    q = query_spatial_index(runtime_scene, sweep_aabb)
    if not contract["collision"]:
        return _ok([], allowed=True, blocked_by=None, reason="collision disabled by contract",
                   candidate_count=q["candidate_count"], mode=mode)

    portal_states = (runtime_state or {}).get("portal_states") or {}
    open_walls = {}
    for p in runtime_scene["walkability"]["portals"]:
        st = portal_states.get(p["portal_id"], p["default_state"])
        if st == "OPEN" and p["host_wall_id"]:
            open_walls.setdefault(p["host_wall_id"], []).append(p)

    by_id = {o["obstacle_id"]: o for o in runtime_scene["walkability"]["obstacles"]}
    for eid in q["candidate_ids"]:
        ob = by_id.get(eid)
        if ob is None:
            continue
        if not _aabb_overlap(sweep_aabb, ob["bounds"]):
            continue
        if not _obb_overlap(sweep, ob["obb"]):
            continue
        if ob["kind"] == "WALL" and ob["source_element_id"] in open_walls:
            passed = None
            for p in open_walls[ob["source_element_id"]]:
                ap = dict(p["aperture"])
                ap["hx"] = ap["hx"] + c["radius_m"]
                ap["hz"] = ap["hz"] + c["radius_m"]
                if _obb_overlap(sweep, ap):
                    passed = p
                    break
            if passed is not None:
                continue
        return _ok([], allowed=False, blocked_by=ob["obstacle_id"],
                   blocked_kind=ob["kind"], reason="obstacle intersects the swept capsule",
                   candidate_count=q["candidate_count"], mode=mode)
    if contract["requires_walkable_surface"]:
        sup = _surface_at(runtime_scene, e)
        if sup is None:
            return _ok([], allowed=False, blocked_by=None,
                       reason="no walkable surface supports the destination",
                       candidate_count=q["candidate_count"], mode=mode)
    return _ok([], allowed=True, blocked_by=None, reason="clear",
               candidate_count=q["candidate_count"], mode=mode)


def _sweep_box(s, e, c):
    lo = [min(s[i], e[i]) for i in range(3)]
    hi = [max(s[i], e[i]) for i in range(3)]
    r, h = c["radius_m"], c["height_m"]
    return _obb((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0 + h / 2.0,
                (lo[2] + hi[2]) / 2.0,
                (hi[0] - lo[0]) + 2 * r, (hi[1] - lo[1]) + h, (hi[2] - lo[2]) + 2 * r, 0.0)


# -------------------------------------------------------- حالة التشغيل ---
def create_runtime_state(runtime_scene, navigation_mode=None, capsule=None, spawn=None):
    """حالة زمن تشغيل زائلة، منفصلة تماماً عن مشهد زمن التشغيل."""
    issues = []
    mode = navigation_mode if navigation_mode is not None else \
        (runtime_scene.get("defaults") or {}).get("navigation_mode") or DEFAULT_NAVIGATION_MODE
    nv = validate_navigation(mode)
    if not nv["valid"]:
        issues.extend(nv["issues"])
        mode = DEFAULT_NAVIGATION_MODE
    cv = validate_capsule(capsule if capsule is not None
                          else (runtime_scene.get("defaults") or {}).get("player_capsule"))
    if not cv["valid"]:
        issues.extend(cv["issues"])
        cap = _copy(CAPSULE_DEFAULTS)
    else:
        cap = cv["capsule"]
    pos = spawn if spawn is not None else \
        ((runtime_scene.get("defaults") or {}).get("spawn") or {}).get("position")
    state = {"schema": SCHEMA, "version": VERSION,
             "runtime_id": runtime_scene.get("runtime_id"),
             "source_scene": runtime_scene.get("source_scene"),
             "camera": {"position": _copy(pos), "target": None,
                        "eye_height_m": cap["eye_height_m"], "orientation_deg": 0.0},
             "navigation_mode": mode,
             "player_capsule": cap,
             "selection": None,
             "visibility": {"hidden_object_ids": [], "hidden_rooms": [],
                            "hidden_levels": [], "hidden_disciplines": [],
                            "isolated": None},
             "measurements": [],
             "portal_states": {},
             "simulation_time": 0.0,
             "issues": _sorted_issues(issues),
             "writes_to_model": False,
             "note": "ephemeral runtime state; it is never written into the visual scene "
                     "or into any canonical engineering model"}
    return state


def advance_simulation_time(runtime_state, delta_s):
    """ساعة أساس فقط: لا محرّك محاكاة مرتبط بها في هذه المرحلة."""
    d = _num(delta_s)
    if d is None or d < 0:
        return _ok([_issue("SIMULATION_TIME_INVALID", "delta_s",
                           "delta must be a finite non-negative number")],
                   simulation_time=runtime_state.get("simulation_time"))
    runtime_state["simulation_time"] = _q(float(runtime_state.get("simulation_time") or 0.0) + d)
    return _ok([], simulation_time=runtime_state["simulation_time"])


# -------------------------------------------------------- البوّابات ------
def set_portal_state(runtime_state, runtime_scene, portal_id, new_state):
    """تغيير حالة بوّابة يغيّر حالة التشغيل وحدها. الباب الهندسي لا يُمسّ."""
    issues = []
    st = _enum(new_state)
    if st not in PORTAL_STATES:
        issues.append(_issue("PORTAL_STATE_INVALID", new_state, "unknown portal state"))
    p = None
    for x in runtime_scene["walkability"]["portals"]:
        if x["portal_id"] == portal_id:
            p = x
            break
    if p is None:
        issues.append(_issue("PORTAL_REFERENCE_INVALID", portal_id,
                             "portal does not resolve in the runtime scene"))
    if issues:
        return _ok(issues, portal_id=portal_id, state=None)
    runtime_state.setdefault("portal_states", {})[portal_id] = st
    return _ok([], portal_id=portal_id, state=st, runtime_only=True)


def room_connectivity_graph(runtime_scene):
    """رسم اتّصال مشتقّ من البوّابات الصالحة فقط. أساس لا تخطيط مسارات."""
    spaces, edges, unresolved = {}, [], []
    for r in runtime_scene.get("rooms") or []:
        spaces[r["space_id"]] = True
    for p in runtime_scene["walkability"]["portals"]:
        if not p["connectivity_resolved"]:
            unresolved.append({"portal_id": p["portal_id"],
                               "from_space": p["from_space"], "to_space": p["to_space"],
                               "basis": p["connectivity_basis"]})
            continue
        if p["to_space"] == EXTERIOR_SPACE_ID:
            spaces[EXTERIOR_SPACE_ID] = True
        edges.append({"portal_id": p["portal_id"], "from": p["from_space"],
                      "to": p["to_space"], "basis": p["connectivity_basis"]})
    edges.sort(key=lambda e: (str(e["from"]), str(e["to"]), str(e["portal_id"])))
    unresolved.sort(key=lambda e: str(e["portal_id"]))
    return {"spaces": sorted(spaces.keys()), "edges": edges, "unresolved": unresolved,
            "note": "a connectivity foundation only — no route planning, evacuation routing "
                    "or pathfinding exists in this phase"}


# ------------------------------------------------- التحديد والفحص -------
def select_runtime_object(runtime_state, runtime_scene, target_id):
    issues = []
    o = _find_object(runtime_scene, target_id)
    if o is None:
        issues.append(_issue("INTERACTION_TARGET_INVALID", target_id,
                             "target does not resolve in the runtime scene"))
        return _ok(issues, selection=None)
    if not o["interaction"]["selectable"]:
        issues.append(_issue("INTERACTION_TARGET_INVALID", target_id, "target is not selectable"))
        return _ok(issues, selection=None)
    sel = {"runtime_object_id": o["runtime_object_id"],
           "source_element_id": o["source_element_id"],
           "visual_object_id": o["visual_object_id"],
           "discipline": o["discipline"], "kind": o["kind"],
           "visual_only": o["visual_only"]}
    runtime_state["selection"] = sel
    return _ok([], selection=_copy(sel), runtime_only=True)


def deselect_runtime_object(runtime_state):
    runtime_state["selection"] = None
    return _ok([], selection=None, runtime_only=True)


def _is_id(target_id):
    """معرّف صالح: نصّ غير فارغ. المعرّف الغائب لا يطابق حقلاً غائباً أبداً —
    وإلا لطابق target_id=None جسماً بصريّاً لا مصدر هندسي له."""
    return isinstance(target_id, str) and target_id != ""


def _find_object(runtime_scene, target_id):
    if not _is_id(target_id):
        return None
    for o in runtime_scene.get("objects") or []:
        if target_id in (o["runtime_object_id"], o["visual_object_id"],
                         o["source_element_id"]):
            return o
    return None


def _find_room(runtime_scene, target_id):
    if not _is_id(target_id):
        return None
    for r in runtime_scene.get("rooms") or []:
        if target_id in (r["runtime_room_id"], r["space_instance_id"], r["space_id"]):
            return r
    return None


def inspect_runtime_object(runtime_scene, target_id, visual_scene=None):
    """يعرض ما ينصّ عليه المصدر فقط. الغائب يُعلَن NOT_SPECIFIED ولا يُستبدَل
    بقيمة افتراضية تبدو حقيقة هندسية."""
    o = _find_object(runtime_scene, target_id)
    if o is None:
        r = _find_room(runtime_scene, target_id)
        if r is None:
            return _ok([_issue("INTERACTION_TARGET_INVALID", target_id,
                               "target does not resolve in the runtime scene")],
                       inspection=None)
        return _ok([], inspection={
            "runtime_room_id": r["runtime_room_id"], "kind": "ROOM",
            "source_element_id": r["space_instance_id"],
            "space_id": r["space_id"],
            "name": r["name"] if r["name"] is not None else NOT_SPECIFIED,
            "level_index": r["level_index"] if r["level_index"] is not None else NOT_SPECIFIED,
            "elevation_m": r["elevation_m"],
            "area_m2": r["area_m2"] if r["area_m2"] is not None else NOT_SPECIFIED,
            "width_m": _q(r["rect_local"][2]), "depth_m": _q(r["rect_local"][3]),
            "source_backed": True,
            "note": "values are taken from the canonical space record; nothing is invented"},
            runtime_only=True)
    src = None
    if isinstance(visual_scene, dict):
        for v in visual_scene.get("objects") or []:
            if v.get("id") == o["visual_object_id"]:
                src = v
                break
    box = o["obb"]
    insp = {"runtime_object_id": o["runtime_object_id"], "kind": o["kind"],
            "discipline": o["discipline"],
            "source_element_id": o["source_element_id"] if o["source_element_id"]
            else NOT_SPECIFIED,
            "visual_object_id": o["visual_object_id"],
            "visual_only": o["visual_only"],
            "visual_class": o["visual_class"] if o["visual_class"] else NOT_SPECIFIED,
            "level_index": o["level_index"] if o["level_index"] is not None else NOT_SPECIFIED,
            "space_id": o["space_id"] if o["space_id"] else NOT_SPECIFIED,
            "position": [box["cx"], box["cy"], box["cz"]],
            "orientation_rad": box["yaw"],
            "dimensions_m": {"width": _q(box["hx"] * 2), "height": _q(box["hy"] * 2),
                             "depth": _q(box["hz"] * 2)},
            "geometry_source": o["geometry_source"] if o["geometry_source"] else NOT_SPECIFIED,
            "collision": _copy(o["collision"]),
            "source_backed": not o["visual_only"],
            "note": "runtime inspection of source-backed values only; an absent property is "
                    "reported NOT_SPECIFIED and never replaced by a plausible default"}
    for key, field in (("host_wall_id", "host_wall_id"), ("material", "material"),
                       ("material_provenance", "material_provenance"),
                       ("asset_id", "asset_id"), ("exposure", "exposure")):
        val = (src or {}).get(field)
        insp[key] = val if val not in (None, "") else NOT_SPECIFIED
    if o["visual_only"]:
        insp["engineering_source"] = NOT_SPECIFIED
        insp["visual_metadata_only"] = True
    return _ok([], inspection=insp, runtime_only=True)


# ------------------------------------------------------------ الرؤية -----
def set_visibility(runtime_state, runtime_scene, mode, target_id=None):
    """رؤية زائلة: مجموعة إخفاء صريحة. لا حذف عنصر ولا كتابة في النموذج."""
    issues = []
    m = _enum(mode)
    if m not in VISIBILITY_MODES:
        issues.append(_issue("VISIBILITY_MODE_INVALID", mode, "unknown visibility mode"))
        return _ok(issues, visibility=None)
    vis = runtime_state.setdefault("visibility", {"hidden_object_ids": [], "hidden_rooms": [],
                                                  "hidden_levels": [], "hidden_disciplines": [],
                                                  "isolated": None})
    if m == "RESTORE_VISIBILITY":
        vis["hidden_object_ids"] = []
        vis["hidden_rooms"] = []
        vis["hidden_levels"] = []
        vis["hidden_disciplines"] = []
        vis["isolated"] = None
        return _ok([], visibility=_copy(vis), runtime_only=True)

    if m.endswith("OBJECT"):
        o = _find_object(runtime_scene, target_id)
        if o is None:
            issues.append(_issue("VISIBILITY_TARGET_INVALID", target_id, "unknown object"))
        else:
            _toggle(vis["hidden_object_ids"], o["runtime_object_id"], m.startswith("HIDE"))
    elif m.endswith("ROOM"):
        r = _find_room(runtime_scene, target_id)
        if r is None:
            issues.append(_issue("VISIBILITY_TARGET_INVALID", target_id, "unknown room"))
        elif m.startswith("ISOLATE"):
            vis["isolated"] = {"kind": "ROOM", "id": r["runtime_room_id"]}
            vis["hidden_rooms"] = sorted(x["runtime_room_id"] for x in runtime_scene["rooms"]
                                         if x["runtime_room_id"] != r["runtime_room_id"])
        else:
            _toggle(vis["hidden_rooms"], r["runtime_room_id"], m.startswith("HIDE"))
    elif m.endswith("FLOOR"):
        lv = target_id
        levels = sorted({x["level_index"] for x in runtime_scene["rooms"]
                         if x["level_index"] is not None})
        if lv not in levels:
            issues.append(_issue("VISIBILITY_TARGET_INVALID", target_id, "unknown level"))
        elif m.startswith("ISOLATE"):
            vis["isolated"] = {"kind": "FLOOR", "id": lv}
            vis["hidden_levels"] = [x for x in levels if x != lv]
        else:
            _toggle(vis["hidden_levels"], lv, m.startswith("HIDE"))
    elif m.endswith("DISCIPLINE"):
        d = _enum(target_id)
        if d not in DISCIPLINES:
            issues.append(_issue("VISIBILITY_TARGET_INVALID", target_id, "unknown discipline"))
        elif m.startswith("ISOLATE"):
            present = sorted({o["discipline"] for o in runtime_scene["objects"]
                              if o["discipline"]})
            vis["isolated"] = {"kind": "DISCIPLINE", "id": d}
            vis["hidden_disciplines"] = [x for x in present if x != d]
        else:
            _toggle(vis["hidden_disciplines"], d, m.startswith("HIDE"))
    if issues:
        return _ok(issues, visibility=_copy(vis))
    for k in ("hidden_object_ids", "hidden_rooms", "hidden_disciplines"):
        vis[k] = sorted(vis[k], key=str)
    vis["hidden_levels"] = sorted(vis["hidden_levels"], key=lambda x: (str(type(x)), str(x)))
    return _ok([], visibility=_copy(vis), runtime_only=True)


def _toggle(lst, value, hide):
    if hide:
        if value not in lst:
            lst.append(value)
    elif value in lst:
        lst.remove(value)


def restore_visibility(runtime_state, runtime_scene):
    return set_visibility(runtime_state, runtime_scene, "RESTORE_VISIBILITY")


def effective_visibility(runtime_state, runtime_scene):
    """حساب الرؤية الفعّالة — مشتقّ بحت، ولا يكتب في أي جسم."""
    vis = runtime_state.get("visibility") or {}
    hidden_obj = set(vis.get("hidden_object_ids") or [])
    hidden_rooms = set(vis.get("hidden_rooms") or [])
    hidden_levels = set(vis.get("hidden_levels") or [])
    hidden_disc = set(vis.get("hidden_disciplines") or [])
    room_space = {r["runtime_room_id"]: r["space_id"] for r in runtime_scene["rooms"]}
    hidden_spaces = {room_space[r] for r in hidden_rooms if r in room_space}
    out = []
    for o in runtime_scene["objects"]:
        visible = True
        if o["runtime_object_id"] in hidden_obj:
            visible = False
        if o["discipline"] in hidden_disc:
            visible = False
        if o["level_index"] is not None and o["level_index"] in hidden_levels:
            visible = False
        if o["space_id"] and o["space_id"] in hidden_spaces:
            visible = False
        out.append({"runtime_object_id": o["runtime_object_id"], "visible": visible})
    out.sort(key=lambda x: str(x["runtime_object_id"]))
    return {"objects": out, "hidden_count": sum(1 for x in out if not x["visible"]),
            "runtime_only": True}


# ------------------------------------------------------------ القياس -----
def create_measurement(runtime_scene, mtype, start=None, end=None, target_id=None,
                       other_id=None):
    """قياس زمن تشغيل فقط. المسافة تُحسب من إحداثيات مُتحقَّق منها، ولا تُصدَّق
    من المستدعي أبداً."""
    issues = []
    t = _enum(mtype)
    if t not in MEASUREMENT_TYPES:
        issues.append(_issue("MEASUREMENT_INVALID", mtype, "unknown measurement type"))
        return _ok(issues, measurement=None)

    def pt(name, v):
        if not isinstance(v, (list, tuple)) or len(v) != 3:
            issues.append(_issue("MEASUREMENT_INVALID", name,
                                 "point must be a vector of three numbers"))
            return None
        vals = [_num(x) for x in v]
        if any(x is None for x in vals):
            issues.append(_issue("MEASUREMENT_INVALID", name,
                                 "point carries a non-finite value"))
            return None
        return vals

    body = None
    if t == "POINT_TO_POINT":
        a = pt("start", start)
        b = pt("end", end)
        if issues:
            return _ok(issues, measurement=None)
        d = math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))
        body = {"start": [_q(x) for x in a], "end": [_q(x) for x in b], "distance_m": _q(d)}
    elif t in ("OBJECT_WIDTH", "OBJECT_HEIGHT"):
        o = _find_object(runtime_scene, target_id)
        if o is None:
            issues.append(_issue("MEASUREMENT_TARGET_INVALID", target_id, "unknown object"))
            return _ok(issues, measurement=None)
        box = o["obb"]
        d = box["hx"] * 2 if t == "OBJECT_WIDTH" else box["hy"] * 2
        body = {"target_id": o["runtime_object_id"],
                "source_element_id": o["source_element_id"],
                "axis": "WIDTH" if t == "OBJECT_WIDTH" else "HEIGHT",
                "distance_m": _q(d)}
    elif t == "ROOM_DIMENSION":
        r = _find_room(runtime_scene, target_id)
        if r is None:
            issues.append(_issue("MEASUREMENT_TARGET_INVALID", target_id, "unknown room"))
            return _ok(issues, measurement=None)
        body = {"target_id": r["runtime_room_id"], "source_element_id": r["space_instance_id"],
                "width_m": _q(r["rect_local"][2]), "depth_m": _q(r["rect_local"][3]),
                "distance_m": _q(max(r["rect_local"][2], r["rect_local"][3]))}
    else:                                            # CLEARANCE
        a = _find_object(runtime_scene, target_id)
        b = _find_object(runtime_scene, other_id)
        if a is None or b is None:
            issues.append(_issue("MEASUREMENT_TARGET_INVALID",
                                 target_id if a is None else other_id, "unknown object"))
            return _ok(issues, measurement=None)
        d = _aabb_gap(a["aabb"], b["aabb"])
        body = {"target_id": a["runtime_object_id"], "other_id": b["runtime_object_id"],
                "source_element_id": a["source_element_id"],
                "other_source_element_id": b["source_element_id"],
                "distance_m": _q(d)}
    if body["distance_m"] < 0 or _num(body["distance_m"]) is None:
        issues.append(_issue("MEASUREMENT_INVALID", t, "computed distance is not valid"))
        return _ok(issues, measurement=None)
    ident = dict(body)
    ident["type"] = t
    m = dict(body)
    m["measurement_id"] = "measure:" + _sha16(ident)
    m["type"] = t
    m["runtime_only"] = True
    m["source_scene"] = runtime_scene.get("source_scene")
    m["note"] = ("a runtime measurement; it is never a code check, a clearance requirement "
                 "or a compliance statement")
    return _ok([], measurement=m)


def _aabb_gap(a, b):
    dx = max(0.0, max(a[0] - b[3], b[0] - a[3]))
    dy = max(0.0, max(a[1] - b[4], b[1] - a[4]))
    dz = max(0.0, max(a[2] - b[5], b[2] - a[5]))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def validate_measurement(measurement):
    issues = []
    m = measurement if isinstance(measurement, dict) else {}
    if not isinstance(measurement, dict):
        issues.append(_issue("MEASUREMENT_INVALID", "measurement", "must be an object"))
        return _ok(issues)
    if m.get("type") not in MEASUREMENT_TYPES:
        issues.append(_issue("MEASUREMENT_INVALID", m.get("type"), "unknown measurement type"))
    if m.get("runtime_only") is not True:
        issues.append(_issue("MEASUREMENT_INVALID", m.get("measurement_id"),
                             "runtime_only must be true"))
    _d = m.get("distance_m")
    if isinstance(_d, bool) or not isinstance(_d, (int, float)) \
       or _num(_d) is None or _num(_d) < 0:
        issues.append(_issue("MEASUREMENT_INVALID", m.get("measurement_id"),
                             "distance must be a finite non-negative number"))
    return _ok(issues)


def add_measurement(runtime_state, runtime_scene, mtype, **kw):
    res = create_measurement(runtime_scene, mtype, **kw)
    if res["valid"]:
        runtime_state.setdefault("measurements", []).append(_copy(res["measurement"]))
    return res


# ---------------------------------------------- التحقّق من الأفعال -------
def validate_runtime_action(action, target_kind=None, target_id=None, payload=None):
    """كل فعل عقد معلن. أي نيّة كتابة في النموذج تُرفض صراحةً."""
    issues = []
    a = _enum(action)
    if a not in INTERACTION_ACTIONS:
        issues.append(_issue("INTERACTION_ACTION_INVALID", action, "unknown runtime action"))
        return _ok(issues, action=None, writes_to_model=False)
    allowed = ACTION_TARGETS[a]
    tk = "NONE" if target_kind is None else (_enum(target_kind) or "")
    if tk not in allowed:
        issues.append(_issue("INTERACTION_TARGET_INVALID", target_kind,
                             "target kind is not valid for %s" % a))
    p = payload if isinstance(payload, dict) else {}
    for key in p.keys():
        k = str(key).lower()
        if k in MODEL_WRITE_INTENTS or k.startswith("set_") or k.startswith("write_") \
           or k in ("geometry", "source_element_id", "vertices", "transform"):
            issues.append(_issue("RUNTIME_MODEL_WRITE_ATTEMPT", key,
                                 "the runtime exposes no model-write path"))
    if p.get("writes_to_model"):
        issues.append(_issue("RUNTIME_MODEL_WRITE_ATTEMPT", "writes_to_model",
                             "the runtime exposes no model-write path"))
    return _ok(issues, action=a if not issues else None, target_kind=tk,
               target_id=target_id)


# ---------------------------------------------------------- التحقّق ------
def validate_runtime_scene(runtime_scene):
    """فحوص نزاهة المشهد: معرّفات فريدة وأسطح وعوائق وبوّابات صالحة."""
    issues = list(runtime_scene.get("issues") or [])
    seen = {}
    for o in runtime_scene.get("objects") or []:
        rid = o.get("runtime_object_id")
        if rid in seen:
            issues.append(_issue("RUNTIME_ID_DUPLICATE", rid, "duplicate runtime object id"))
        seen[rid] = True
        if not o.get("visual_only") and not o.get("source_element_id"):
            issues.append(_issue("RUNTIME_SOURCE_OBJECT_INVALID", rid,
                                 "a model-derived runtime object must name its source"))
    w = runtime_scene.get("walkability") or {}
    for s in w.get("surfaces") or []:
        r = s.get("rect_local")
        if not r or len(r) != 4 or _num(r[2]) is None or _num(r[3]) is None \
           or r[2] <= 0 or r[3] <= 0 or _num(s.get("elevation_m")) is None:
            issues.append(_issue("WALKABLE_SURFACE_INVALID", s.get("surface_id"),
                                 "surface bounds are not valid"))
    for o in w.get("obstacles") or []:
        b = o.get("bounds")
        if not b or len(b) != 6 or any(_num(v) is None for v in b) \
           or b[3] < b[0] or b[4] < b[1] or b[5] < b[2]:
            issues.append(_issue("OBSTACLE_INVALID", o.get("obstacle_id"),
                                 "obstacle bounds are not valid"))
    seenp = {}
    space_ids = {r["space_id"] for r in runtime_scene.get("rooms") or []}
    space_ids.add(EXTERIOR_SPACE_ID)
    for p in w.get("portals") or []:
        pid = p.get("portal_id")
        if pid in seenp:
            issues.append(_issue("PORTAL_DUPLICATE", pid, "duplicate portal id"))
        seenp[pid] = True
        if p.get("default_state") not in PORTAL_STATES:
            issues.append(_issue("PORTAL_STATE_INVALID", pid, "unknown default portal state"))
        if p.get("connectivity_resolved"):
            for side in ("from_space", "to_space"):
                if p.get(side) not in space_ids:
                    issues.append(_issue("PORTAL_SPACE_REFERENCE_INVALID", pid,
                                         "%s does not resolve" % side))
            if p.get("from_space") == p.get("to_space"):
                issues.append(_issue("PORTAL_SPACE_REFERENCE_INVALID", pid,
                                     "a portal may not connect a space to itself"))
    if runtime_scene.get("writes_to_model"):
        issues.append(_issue("RUNTIME_MODEL_WRITE_ATTEMPT", "runtime_scene",
                             "writes_to_model must be false"))
    return _ok(issues)


def rule_inputs(runtime_scene):
    c = runtime_scene.get("counts") or {}
    return {"building": {"runtime.object.count": c.get("objects", 0),
                         "runtime.obstacle.count": c.get("obstacles", 0),
                         "runtime.walkable_surface.count": c.get("surfaces", 0),
                         "runtime.portal.count": c.get("portals", 0),
                         "runtime.portal.unresolved_count": c.get("portals_unresolved", 0)}}


def summary(runtime_scene):
    c = runtime_scene.get("counts") or {}
    idx = runtime_scene.get("spatial_index") or {}
    return {"compiler_version": COMPILER_VERSION, "runtime_id": runtime_scene.get("runtime_id"),
            "source_scene": runtime_scene.get("source_scene"),
            "model_hash": runtime_scene.get("model_hash"),
            "objects": c.get("objects", 0), "obstacles": c.get("obstacles", 0),
            "surfaces": c.get("surfaces", 0), "rooms": c.get("rooms", 0),
            "portals": c.get("portals", 0),
            "portals_unresolved": c.get("portals_unresolved", 0),
            "vertical_connections": c.get("vertical_connections", 0),
            "spatial_cells": idx.get("cells", 0),
            "issues": len(runtime_scene.get("issues") or []),
            "engineering_geometry_modified": False,
            "writes_to_model": False,
            "compliance": "NOT_EVALUATED",
            "note": "deterministic read-only interaction runtime; ephemeral state only, no "
                    "simulation engine, and no write path to any engineering model"}
