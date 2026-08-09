# -*- coding: utf-8 -*-
# =============================================================================
# acs_render.py — محرّك العرض التقديمي.
#
# هذه الطبقة لا تحسب هندسة ولا تنشئ هندسة. تقرأ المشهد البصري المصرَّف من
# المرحلة 3 وتشتقّ منه مخرجات عرض: طلب عرض مُوثَّق، كاميرا، مواد، إضاءة،
# تحويلات عرض (بيت الدمية، القطع، تفجير الأدوار)، رسومات ثنائية الأبعاد
# (مسقط، مقطع، واجهة)، ومخازن تحكّم مُنقَّطة على المعالج بشكل حتمي.
#
# مبادئ صارمة:
#   • لا كتابة عكسية إطلاقاً: صورة لا تصير نموذجاً.
#   • العرض الحتمي هو المرجع الهندسي؛ التحسين بالذكاء الاصطناعي اختياري ولاحق.
#   • المادة البصرية مظهر فقط: لا متانة ولا مقاومة حريق ولا أداء حراري ولا مطابقة.
#   • الأثاث والنبات والأشخاص العرضيّون ليسوا أجساماً دلالية.
#   • كل ناتج مثبَّت على بصمة نموذج ومراجعة، ويُوسم قديماً حين تتقدّم المراجعة.
#   • لا ادّعاء واقعية ولا ادّعاء دقّة بكسل ولا ادّعاء تحليل شمسي.
# =============================================================================
import hashlib
import json
import math
import os

import acs_ingest as ING
import acs_visual as VIS

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_render.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
COMPILER = SPEC["compiler_version"]
VIEW_TYPES = tuple(SPEC["view_types"])
VECTOR_VIEWS = tuple(SPEC["vector_view_types"])
RASTER_VIEWS = tuple(SPEC["raster_view_types"])
QUALITIES = tuple(SPEC["qualities"])
THEMES = tuple(SPEC["themes"])
LIGHTING_PRESETS = tuple(SPEC["lighting_presets"])
CAMERA_PRESETS = tuple(SPEC["camera_presets"])
MATERIAL_CLASSES = tuple(SPEC["visual_material_classes"])
BUFFER_KINDS = tuple(SPEC["control_buffer_kinds"])
SEMANTIC_CLASSES = tuple(SPEC["semantic_classes"])
DRIFT_TYPES = tuple(SPEC["drift_types"])
FIDELITY = tuple(SPEC["fidelity_statuses"])
UNSAFE = tuple(SPEC["unsafe_patterns"])
MATERIALS = {m["id"]: m for m in SPEC["material_library"]}
THRESH = SPEC["drift_thresholds"]
_SEM_WALL = SEMANTIC_CLASSES.index("WALL")
_SEM_OPENING = SEMANTIC_CLASSES.index("OPENING")
# سماكة جدار معلنة: المدى الذي تُعدّ فيه الفتحة مقطوعة في مضيفها لا خلفه
_OPENING_BIAS_M = 0.6


# ----------------------------------------------------------------- أدوات ----
def _q(v):
    """تقريب موحّد — يمنع انحراف الفاصلة العائمة بين بايثون وجافاسكربت."""
    return round(float(v), 6) + 0.0


def _num(v):
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
    """المرمِّز القانوني المشترك: يوحّد الرمز الرقمي فلا يفترق 14 عن 14.0 بين
    بايثون وجافاسكربت — نفس الدالّة التي تستعملها الطبقات السابقة."""
    return ING.canonical_json(o)


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _copy(v):
    return json.loads(json.dumps(v))


def _issue(code, subject, detail, severity="ERROR"):
    return {"code": code, "severity": severity, "subject": subject, "detail": detail}


_SAFE_ID = SPEC["safe_id_pattern"]
_SCHEMES = tuple(SPEC["allowed_uri_schemes"])


def is_safe_id(v):
    """معرّف مقبول بقائمة سماح لا بقائمة حظر: ما ليس معرّفاً معقولاً يُرفض،
    وافقنا على نمط هجومه أم لم نعرفه بعد."""
    import re as _re
    return isinstance(v, str) and _re.match(_SAFE_ID, v) is not None


def is_allowed_uri(v):
    """مصدر مرجع مقبول بمخطّط من قائمة سماح. أي مخطّط آخر مرفوض افتراضاً."""
    if not isinstance(v, str) or not v:
        return False
    low = v.strip().lower()
    if is_unsafe(low):
        return False
    if low.startswith("https:") or low.startswith("http:"):
        return True
    if low.startswith("blob:"):
        return True
    if low.startswith("data:"):
        return low.startswith("data:image/") and ";base64," in low \
            and "svg" not in low.split(",")[0]
    if ":" in low.split("/")[0]:
        return False
    # مسار نسبي: يُقبل بقائمة سماح لمحارف المسار، فلا يمرّ نصّ ليس مساراً أصلاً
    import re as _re
    return _re.match(r"^[a-z0-9._~/\-]+$", low) is not None


_PROSE_MAX = int(SPEC["visual_intent_max_chars"])
_PROSE_BAD = tuple(SPEC["forbidden_prose_chars"])


def is_safe_prose(v):
    """وصف طراز قصير مقبول بقائمة سماح: حروف عربية وإنجليزية وأرقام ومسافات
    وفواصل وشرطات فقط. ما ليس وصف طراز معقولاً يُرفض، عرفنا نمط هجومه أم لا."""
    import re as _re
    if not isinstance(v, str) or len(v) > _PROSE_MAX:
        return False
    return _re.match(SPEC["visual_intent_pattern"], v) is not None


def is_unsafe(*values):
    """أي قيمة نصّية تحمل وسماً أو مخطّطاً تنفيذياً تُرفض — لا تُنظَّف ولا تُمرَّر."""
    for v in values:
        if not isinstance(v, str):
            continue
        low = v.lower()
        for p in UNSAFE:
            if p.lower() in low:
                return True
    return False


# ------------------------------------------------------ طلب العرض (§1) ------
def render_request(project, view_type, options=None, request_id=None):
    """طلب عرض مُوثَّق ومثبَّت على بصمة النموذج والمراجعة. حالة عرض لا غير."""
    o = options or {}
    issues = []
    vt = str(view_type).upper() if isinstance(view_type, str) else None
    if vt not in VIEW_TYPES:
        issues.append(_issue("INVALID_VIEW_TYPE", view_type, "unknown view type"))
    quality = str(o.get("quality") or SPEC["default_quality"]).upper()
    if quality not in QUALITIES:
        issues.append(_issue("INVALID_QUALITY", o.get("quality"), "unknown quality"))
    theme = str(o.get("theme") or SPEC["default_theme"]).upper()
    if theme not in THEMES:
        issues.append(_issue("INVALID_THEME", o.get("theme"), "unknown theme"))
    lighting = str(o.get("lighting") or SPEC["default_lighting"]).upper()
    if lighting not in LIGHTING_PRESETS:
        issues.append(_issue("INVALID_LIGHTING", o.get("lighting"), "unknown lighting preset"))
    refs = o.get("reference_ids") or []
    if not isinstance(refs, list):
        refs = []
    refs = [str(r) for r in refs if isinstance(r, (str, int))]
    if not all(is_safe_id(str(r)) for r in refs):
        issues.append(_issue("PAYLOAD_REJECTED", "reference_ids",
                             "a reference identifier is not a plausible identifier"))
    res = o.get("resolution")
    if res is not None:
        if (not isinstance(res, list) or len(res) != 2
                or _num(res[0]) is None or _num(res[1]) is None
                or int(res[0]) <= 0 or int(res[1]) <= 0):
            issues.append(_issue("INVALID_RESOLUTION", res, "resolution must be two positive integers"))
        elif int(res[0]) * int(res[1]) > int(SPEC["max_render_px"]):
            issues.append(_issue("INVALID_RESOLUTION", res, "resolution exceeds the declared maximum"))

    req = {
        "schema": SCHEMA,
        "request_id": None,
        "model_hash": project.get("model_hash"),
        "revision_id": project.get("current_revision"),
        "building_id": project.get("building_id") or "bld_0",
        "level_id": o.get("level_id"),
        "space_id": o.get("space_id"),
        "view_type": vt,
        "camera": o.get("camera"),
        "quality": quality if quality in QUALITIES else None,
        "theme": theme if theme in THEMES else None,
        "lighting": lighting if lighting in LIGHTING_PRESETS else None,
        "ai_enhancement": bool(o.get("ai_enhancement")),
        "reference_ids": refs,
        "resolution": [int(res[0]), int(res[1])] if (res and not issues) else None,
        "context_flags": sorted(set(
            [c for c in (o.get("context_flags") or SPEC["context_default_enabled"])
             if c in SPEC["context_flags"]])),
        "writes_to_model": False,
        "is_presentation_state": True,
    }
    req["request_id"] = request_id or ("rreq_" + _sha16(
        {k: req[k] for k in SPEC["request_fields"] if k in req}))
    if issues:
        return {"valid": False, "issues": issues, "request": None}
    return {"valid": True, "issues": [], "request": req}


# ------------------------------------------------------- المواد (§4-§7) -----
def material(mid):
    m = MATERIALS.get(mid)
    return _copy(m) if m else None


def material_library():
    return [_copy(m) for m in SPEC["material_library"]]


def _slot_for(kind, obj=None):
    """الفتحة المادّية لنوع جسم. الجدار الخارجي يُميَّز عن الداخلي حين يُعلَن."""
    k = str(kind).upper()
    if k == "WALL" and isinstance(obj, dict):
        meta = obj.get("meta") or {}
        if meta.get("exterior") is True or obj.get("exterior") is True:
            return "exterior_wall"
    return SPEC["kind_slot"].get(k)


def assign_materials(scene, theme=None, overrides=None):
    """يسند مادّة بصرية لكل جسم. لا يلمس النموذج ولا المشهد المصدر."""
    th = str(theme or SPEC["default_theme"]).upper()
    if th not in THEMES:
        th = SPEC["default_theme"]
    table = SPEC["theme_material"][th]
    ov = overrides if isinstance(overrides, dict) else {}
    out = []
    defaults_applied = 0
    for obj in scene.get("objects") or []:
        oid = obj.get("id")
        slot = _slot_for(obj.get("kind"), obj)
        chosen = None
        source = None
        if oid in ov and ov[oid] in MATERIALS:
            chosen, source = ov[oid], "USER_VISUAL_OVERRIDE"
        elif slot and slot in ov and ov[slot] in MATERIALS:
            chosen, source = ov[slot], "USER_VISUAL_OVERRIDE"
        elif slot and table.get(slot) in MATERIALS:
            chosen, source = table[slot], "THEME_DEFAULT"
        else:
            chosen, source = "r_default", "VISUAL_DEFAULT"
        if source in ("THEME_DEFAULT", "VISUAL_DEFAULT"):
            defaults_applied += 1
        m = MATERIALS[chosen]
        out.append({
            "object_id": oid,
            "kind": obj.get("kind"),
            "slot": slot,
            "material_id": chosen,
            "visual_class": m["visual_class"],
            "assignment_source": source,
            "visual_default_applied": source in ("THEME_DEFAULT", "VISUAL_DEFAULT"),
            "semantic_finish_unchanged": True,
            "visual_only": True,
        })
    return {
        "schema": SCHEMA, "theme": th,
        "assignments": out,
        "visual_default_applied": defaults_applied > 0,
        "visual_default_count": defaults_applied,
        "materials_used": sorted(set(a["material_id"] for a in out)),
        "writes_to_model": False,
        "note": "a visual material describes appearance only; it never implies structural "
                "strength, fire rating, thermal performance or code compliance",
    }


def visual_override(overrides, scope, target, material_id, intent="VISUAL_OVERRIDE"):
    """تجاوز مادّي. النيّة التقديمية مسموحة هنا؛ نيّة المواصفة تُحال للتأليف."""
    issues = []
    if scope not in SPEC["material_override_scopes"]:
        issues.append(_issue("INVALID_TARGET", scope, "unknown override scope"))
    if material_id not in MATERIALS:
        issues.append(_issue("INVALID_TARGET", material_id, "unknown visual material"))
    if is_unsafe(str(target), str(material_id)):
        issues.append(_issue("PAYLOAD_REJECTED", "override", "an override carried markup"))
    if intent == "PROJECT_SPECIFICATION":
        return {"valid": False, "applied": False, "overrides": _copy(overrides or {}),
                "requires_authoring": True,
                "issues": [_issue("NOT_IMPLEMENTED", "intent",
                                  "changing the project specification is an authoring "
                                  "command and must go through the authoring path")],
                "note": "a visual override and a specification change are never merged"}
    if intent not in SPEC["override_kinds"]:
        issues.append(_issue("INVALID_TARGET", intent, "unknown override intent"))
    if issues:
        return {"valid": False, "applied": False, "overrides": _copy(overrides or {}),
                "requires_authoring": False, "issues": issues}
    new = _copy(overrides or {})
    new[str(target)] = material_id
    return {"valid": True, "applied": True, "overrides": new,
            "requires_authoring": False, "issues": [],
            "intent": "VISUAL_OVERRIDE", "writes_to_model": False}


# ------------------------------------------------------ الإضاءة (§11-§13) ---
def lighting(preset, orientation_deg=None):
    """إعداد إضاءة تقديمي. اتجاه الشمس المستمَدّ من إعداد يُوسَم عرضياً."""
    p = str(preset).upper() if isinstance(preset, str) else None
    if p not in LIGHTING_PRESETS:
        return {"valid": False, "issues": [_issue("INVALID_LIGHTING", preset,
                                                  "unknown lighting preset")],
                "lighting": None}
    params = _copy(SPEC["lighting_params"][p])
    known = _num(orientation_deg) is not None
    if known:
        params["azimuth_deg"] = _q((_num(orientation_deg) + params["azimuth_deg"]) % 360.0)
    return {"valid": True, "issues": [], "lighting": {
        "preset": p,
        "params": params,
        "sun_mode": "PROJECT_ORIENTATION" if known else "VISUAL_PRESET",
        "is_solar_analysis": False,
        "environment": SPEC["environment_fallback"],
        "note": "sun direction from a preset is a presentation choice and is never "
                "presented as solar analysis",
    }}


def environment(quality, has_local_env_map=False):
    q = str(quality).upper()
    if q not in QUALITIES:
        q = SPEC["default_quality"]
    wanted = SPEC["quality_profile"][q]["env_quality"]
    used = wanted if (wanted != "ENVIRONMENT_MAP" or has_local_env_map) \
        else SPEC["environment_fallback"]
    return {"requested": wanted, "used": used,
            "fell_back": used != wanted,
            "remote_dependency": False,
            "note": "the procedural sky is always available, so a render never fails for "
                    "want of a downloadable asset"}


def quality_profile(q, constrained=False):
    """ملف الجودة. التقييد يخفض التكلفة البصرية ولا يحذف هندسة دلالية أبداً."""
    qq = str(q).upper()
    if qq not in QUALITIES:
        qq = SPEC["default_quality"]
    prof = _copy(SPEC["quality_profile"][qq])
    prof["quality"] = qq
    prof["degraded"] = False
    if constrained:
        order = list(QUALITIES)
        idx = max(0, order.index(qq) - 2)
        low = _copy(SPEC["quality_profile"][order[idx]])
        low["quality"] = order[idx]
        low["degraded"] = True
        low["degraded_from"] = qq
        prof = low
    prof["shadow_params"] = _copy(SPEC["shadow_params"][prof["shadow_mode"]])
    prof["removes_semantic_geometry"] = False
    return prof


# ------------------------------------------------------ الكاميرا (§28-§30) --
def _bounds(scene):
    b = scene.get("bounds")
    if not b or len(b) != 6:
        return None
    return [float(x) for x in b]


def _lens(preset):
    return _copy(SPEC["lens_presets"][preset])


def _clamp_fov(f):
    lim = SPEC["fov_limits"]
    return _q(min(max(float(f), lim["min_deg"]), lim["max_deg"]))


def _fit_distance(size, fov_deg, aspect=1.7777778):
    """مسافة تُبقي المبنى كاملاً داخل الإطار مع هامش معلن."""
    half = max(size[0], size[1] * aspect, size[2]) * 0.5
    if half <= 0:
        half = 1.0
    f = math.radians(max(1e-6, float(fov_deg))) * 0.5
    return _q((half / math.tan(f)) * float(SPEC["camera_margin"]))


def camera_for(scene, preset, space_id=None, aspect=1.7777778):
    """كاميرا مشتقّة من حدود المشهد الحقيقية. لا موضع مخترَع ولا هدف مخترَع."""
    p = str(preset).upper() if isinstance(preset, str) else None
    if p not in CAMERA_PRESETS:
        return {"valid": False, "issues": [_issue("INVALID_CAMERA", preset,
                                                  "unknown camera preset")], "camera": None}
    b = _bounds(scene)
    if b is None:
        return {"valid": False, "issues": [_issue("INVALID_CAMERA", "bounds",
                                                  "the scene declares no bounds")],
                "camera": None}
    cx, cy, cz = _q((b[0] + b[3]) / 2.0), _q((b[1] + b[4]) / 2.0), _q((b[2] + b[5]) / 2.0)
    sx, sy, sz = _q(b[3] - b[0]), _q(b[4] - b[1]), _q(b[5] - b[2])
    issues = []

    if p in ("INTERIOR_WIDE", "INTERIOR_EYE_LEVEL"):
        space = None
        for s in scene.get("spaces_index") or []:
            if s.get("space_id") == space_id or s.get("id") == space_id \
                    or s.get("name") == space_id:
                space = s
                break
        if space is None:
            return {"valid": False,
                    "issues": [_issue("INVALID_TARGET", space_id,
                                      "no such space in the compiled scene")],
                    "camera": None}
        r = space.get("rect") or [0, 0, 0, 0]
        clear = float(SPEC["interior_camera_clearance_m"])
        if float(r[2]) <= clear * 2.2 or float(r[3]) <= clear * 2.2:
            return {"valid": False,
                    "issues": [_issue("SPACE_TOO_SMALL", space_id,
                                      "the space is too small for a safe interior camera; "
                                      "no camera is guessed")],
                    "camera": None}
        elev = float(space.get("_elev") or 0.0)
        eye = _q(elev + float(SPEC["eye_level_m"]))
        lens = _lens("INTERIOR_WIDE" if p == "INTERIOR_WIDE" else "STREET")
        # الكاميرا داخل الحدّ الحقيقي للفراغ، بعيدة عن الجدار بمسافة معلنة
        px = _q(float(r[0]) + clear + 0.001)
        pz = _q(float(r[1]) + clear + 0.001)
        tx = _q(float(r[0]) + float(r[2]) - clear)
        tz = _q(float(r[1]) + float(r[3]) - clear)
        cam = {"preset": p, "projection": lens["projection"],
               "fov_deg": _clamp_fov(lens["fov_deg"]),
               "position": [px, eye, pz], "target": [tx, eye, tz],
               "up": [0.0, 1.0, 0.0],
               "inside_space": space.get("space_id"),
               "clearance_m": _q(clear)}
    elif p == "TOP":
        lens = _lens("ORTHOGRAPHIC")
        cam = {"preset": p, "projection": "orthographic", "fov_deg": 0.0,
               "ortho_height": _q(max(sz, sx / aspect) * float(SPEC["camera_margin"])),
               "position": [cx, _q(b[4] + max(sx, sz) + 10.0), cz],
               "target": [cx, cy, cz], "up": [0.0, 0.0, 1.0]}
    else:
        lens = _lens("STREET" if p == "STREET_VIEW" else "ARCHITECTURAL_EXTERIOR")
        fov = _clamp_fov(lens["fov_deg"])
        d = _fit_distance([sx, sy, sz], fov, aspect)
        if p == "FRONT_EXTERIOR":
            pos = [cx, _q(cy + sy * 0.35), _q(b[2] - d)]
        elif p == "REAR_EXTERIOR":
            pos = [cx, _q(cy + sy * 0.35), _q(b[5] + d)]
        elif p == "FRONT_CORNER":
            pos = [_q(b[0] - d * 0.62), _q(cy + sy * 0.45), _q(b[2] - d * 0.62)]
        elif p == "REAR_CORNER":
            pos = [_q(b[3] + d * 0.62), _q(cy + sy * 0.45), _q(b[5] + d * 0.62)]
        elif p == "BIRDS_EYE":
            pos = [_q(cx - d * 0.35), _q(b[4] + d * 0.85), _q(b[2] - d * 0.35)]
        elif p == "DOLLHOUSE":
            pos = [_q(cx - d * 0.45), _q(b[4] + d * 0.55), _q(b[2] - d * 0.45)]
        elif p == "STREET_VIEW":
            pos = [cx, _q(b[1] + float(SPEC["eye_level_m"])), _q(b[2] - d * 1.15)]
        else:
            pos = [cx, _q(cy + sy * 0.35), _q(b[2] - d)]
        cam = {"preset": p, "projection": lens["projection"], "fov_deg": fov,
               "position": [_q(pos[0]), _q(pos[1]), _q(pos[2])],
               "target": [cx, cy, cz], "up": [0.0, 1.0, 0.0],
               "fit_distance_m": d}
    cam.update({
        "aspect": _q(aspect), "near_m": 0.05, "far_m": 4000.0,
        "fit_bounds": [_q(x) for x in b],
        "is_presentation_state": True, "writes_to_model": False,
    })
    cam["camera_id"] = "cam_" + _sha16(cam)
    return {"valid": True, "issues": issues, "camera": cam}


# ------------------------------------------- تحويلات العرض (§21-§23) --------
def visual_transform(scene, kind, options=None):
    """تحويل عرض قابل للعكس. لا يغيّر هندسة ولا منسوب دور في النموذج."""
    o = options or {}
    k = str(kind).upper() if isinstance(kind, str) else None
    if k not in SPEC["visual_transforms"]:
        return {"valid": False, "issues": [_issue("INVALID_TARGET", kind,
                                                  "unknown visual transform")],
                "transform": None}
    hidden, offsets, plane = [], {}, None
    objs = scene.get("objects") or []
    if k == "ROOF_HIDE":
        hidden = sorted(o["id"] for o in objs
                        if str(o.get("kind")).upper() in ("ROOF", "ROOF_CAP"))
    elif k == "WALL_CLIP":
        cut = _num(o.get("height_m"))
        cut = 1.2 if cut is None else cut
        hidden = sorted(ob["id"] for ob in objs
                        if str(ob.get("kind")).upper() in ("CEILING", "ROOF", "ROOF_CAP"))
        plane = {"axis": "y", "offset_m": _q(cut), "keep": "BELOW"}
    elif k == "LEVEL_ISOLATION":
        lv = o.get("level_index")
        keep = []
        for ob in objs:
            meta = ob.get("meta") or {}
            li = meta.get("level_index", ob.get("level_index"))
            if lv is not None and li is not None and int(li) != int(lv):
                keep.append(ob["id"])
        hidden = sorted(keep)
    elif k == "CLIP_PLANE":
        ax = str(o.get("axis") or "x").lower()
        if ax not in SPEC["cut_axes"]:
            return {"valid": False,
                    "issues": [_issue("INVALID_TARGET", o.get("axis"), "unknown cut axis")],
                    "transform": None}
        off = _num(o.get("offset_m"))
        b = _bounds(scene) or [0, 0, 0, 1, 1, 1]
        mid = {"x": (b[0] + b[3]) / 2.0, "y": (b[1] + b[4]) / 2.0,
               "z": (b[2] + b[5]) / 2.0}[ax]
        plane = {"axis": ax, "offset_m": _q(mid if off is None else off),
                 "keep": str(o.get("keep") or "BELOW").upper()}
    elif k == "LEVEL_EXPLODE":
        gap = _num(o.get("gap_m"))
        gap = float(SPEC["explode_gap_m"]) if gap is None else gap
        for ob in objs:
            meta = ob.get("meta") or {}
            li = meta.get("level_index", ob.get("level_index"))
            if li is None:
                continue
            offsets[ob["id"]] = [0.0, _q(float(li) * gap), 0.0]
    return {"valid": True, "issues": [], "transform": {
        "kind": k, "hidden_object_ids": hidden, "clip_plane": plane,
        "display_offsets": offsets,
        "reversible": True, "duplicates_geometry": False,
        "changes_level_elevation": False, "writes_to_model": False,
        "note": "a visual transform hides or offsets objects for presentation only; the "
                "engineering geometry and level elevations are untouched",
    }}


# ------------------------------------------ رسومات ثنائية الأبعاد (§24-§27) -
def _fv(field, fallback=None):
    """قيمة حقل معماري: المذكور أوّلاً، ثم احتياط العرض، مع الإفصاح عن أيّهما."""
    if isinstance(field, dict):
        if field.get("value") is not None:
            return (_q(field["value"]), "MODEL")
        if field.get("render_fallback") is not None:
            return (_q(field["render_fallback"]), "DISPLAY_FALLBACK")
        return (fallback if fallback is None else _q(fallback), "UNKNOWN")
    n = _num(field)
    if n is not None:
        return (_q(n), "MODEL")
    return (fallback if fallback is None else _q(fallback), "UNKNOWN")


def _plan_walls(arch, level_index):
    out = []
    for w in (arch.get("walls") or []):
        if level_index is not None and w.get("level_index") is not None \
                and int(w["level_index"]) != int(level_index):
            continue
        a, b = w.get("start"), w.get("end")
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        t, tsrc = _fv(w.get("thickness_m"))
        out.append({"id": w.get("id"),
                    "x1": _q(a.get("x", 0.0)), "y1": _q(a.get("z", 0.0)),
                    "x2": _q(b.get("x", 0.0)), "y2": _q(b.get("z", 0.0)),
                    "thickness_m": t, "thickness_source": tsrc,
                    "exposure": w.get("exposure")})
    return sorted(out, key=lambda r: str(r["id"]))


def _plan_openings(arch, level_index, kind):
    """فتحات المسقط من العمارة المصرَّفة وحدها — لا فتحة تُستنتج ولا تُخترع."""
    out = []
    for o in (arch.get("openings") or []):
        if str(o.get("type", "")).upper() != kind:
            continue
        if level_index is not None and o.get("level_index") is not None \
                and int(o["level_index"]) != int(level_index):
            continue
        ax = str(o.get("axis") or "x").lower()
        fixed = _num(o.get("fixed"))
        u = _num(o.get("u_center"))
        if fixed is None or u is None:
            continue
        x, y = (u, fixed) if ax == "x" else (fixed, u)
        wv, wsrc = _fv(o.get("width_m"))
        out.append({"id": o.get("id"), "x": _q(x), "y": _q(y),
                    "axis": ax, "width_m": wv, "width_source": wsrc,
                    "edge": o.get("edge"), "space_id": o.get("space_id"),
                    "host_wall_id": o.get("host_wall_id")})
    return sorted(out, key=lambda r: str(r["id"]))


def plan_drawing(scene, arch, level_index=0, style="CLEAN", options=None):
    """مسقط مشتقّ من العمارة المصرَّفة. رسم تقديمي لا مخطّط تنفيذ."""
    o = options or {}
    st = str(style).upper()
    if st not in SPEC["plan_styles"]:
        return {"valid": False, "issues": [_issue("INVALID_TARGET", style,
                                                  "unknown plan style")], "drawing": None}
    spaces = [s for s in (scene.get("spaces_index") or [])
              if level_index is None or int(s.get("level_index", 0)) == int(level_index)]
    walls = _plan_walls(arch or {}, level_index)
    doors = _plan_openings(arch or {}, level_index, "DOOR")
    windows = _plan_openings(arch or {}, level_index, "WINDOW")
    stairs = []
    for ob in (scene.get("objects") or []):
        if str(ob.get("kind")).upper() != "STAIR":
            continue
        g = ob.get("geometry") or {}
        stairs.append({"id": ob.get("id"), "x": _q(g.get("cx", 0)), "y": _q(g.get("cz", 0)),
                       "w": _q(g.get("ex", 1)), "d": _q(g.get("ez", 1))})
    furniture = []
    if o.get("furniture"):
        for ob in (scene.get("objects") or []):
            if ob.get("semantic") and str(ob.get("layer")).upper() == "OBJECT":
                g = ob.get("geometry") or {}
                furniture.append({"id": ob.get("id"), "kind": ob.get("kind"),
                                  "x": _q(g.get("cx", 0)), "y": _q(g.get("cz", 0)),
                                  "w": _q(g.get("ex", 0.5)), "d": _q(g.get("ez", 0.5))})
    orientation = _num((o.get("orientation_deg")))
    dims = []
    for s in spaces:
        r = s.get("rect") or [0, 0, 0, 0]
        dims.append({"space_id": s.get("space_id"),
                     "w_m": _q(r[2]), "d_m": _q(r[3]),
                     "area_m2": _q(_num(s.get("area_m2")) or (float(r[2]) * float(r[3]))),
                     "source": "MODEL"})
    drawing = {
        "schema": SCHEMA, "kind": "FLOOR_PLAN", "style": st,
        "level_index": level_index,
        "units": "m",
        "extent": _plan_extent(spaces, walls),
        "walls": walls, "doors": doors, "windows": windows, "stairs": stairs,
        "spaces": [{"space_id": s.get("space_id"), "name": s.get("name"),
                    "rect": [_q(x) for x in (s.get("rect") or [0, 0, 0, 0])],
                    "area_m2": _q(_num(s.get("area_m2")) or 0.0)} for s in spaces],
        "dimensions": dims, "furniture": furniture,
        "north_deg": _q(orientation) if orientation is not None else None,
        "north_shown": orientation is not None,
        "is_construction_drawing": False,
        "writes_to_model": False,
        "note": "a presentation plan derived from the compiled architecture; it is not a "
                "construction drawing and carries no code annotation",
    }
    drawing["drawing_id"] = "rdrw_" + _sha16(drawing)
    return {"valid": True, "issues": [], "drawing": drawing}


def _plan_extent(spaces, walls):
    xs, ys = [], []
    for s in spaces:
        r = s.get("rect") or [0, 0, 0, 0]
        xs += [float(r[0]), float(r[0]) + float(r[2])]
        ys += [float(r[1]), float(r[1]) + float(r[3])]
    for w in walls:
        xs += [w["x1"], w["x2"]]
        ys += [w["y1"], w["y2"]]
    if not xs:
        return [0.0, 0.0, 1.0, 1.0]
    return [_q(min(xs)), _q(min(ys)), _q(max(xs)), _q(max(ys))]


def elevation_drawing(scene, face="NORTH", options=None):
    """واجهة من الغلاف الحقيقي. لا فتحة مخترَعة ولا عنصر واجهة مضاف."""
    f = str(face).upper()
    if f not in SPEC["elevation_faces"]:
        return {"valid": False, "issues": [_issue("INVALID_TARGET", face,
                                                  "unknown elevation face")],
                "drawing": None}
    b = _bounds(scene)
    if b is None:
        return {"valid": False, "issues": [_issue("INVALID_CAMERA", "bounds",
                                                  "the scene declares no bounds")],
                "drawing": None}
    horiz = 0 if f in ("NORTH", "SOUTH") else 2          # x أو z
    shapes = []
    for ob in (scene.get("objects") or []):
        g = ob.get("geometry") or {}
        if g.get("type") != "box":
            continue
        kind = str(ob.get("kind")).upper()
        if ob.get("visual_only"):
            continue
        c = [_num(g.get("cx")), _num(g.get("cy")), _num(g.get("cz"))]
        e = [_num(g.get("ex")), _num(g.get("ey")), _num(g.get("ez"))]
        if None in c or None in e:
            continue
        u = c[horiz] - e[horiz] / 2.0
        w = e[horiz]
        y0 = c[1] - e[1] / 2.0
        shapes.append({"id": ob.get("id"), "kind": kind,
                       "u": _q(u), "w": _q(w), "y": _q(y0), "h": _q(e[1]),
                       "depth": _q(c[2] if horiz == 0 else c[0])})
    shapes.sort(key=lambda s: (s["depth"] if f in ("NORTH", "WEST") else -s["depth"],
                               str(s["id"])))
    # مدى الواجهة من الأشكال المرسومة نفسها: حدود المشهد تشمل النبات والأرض
    # العرضية، فلو استُعملت لظهر المبنى صغيراً وسط فراغ لا يخصّه
    if shapes:
        u0 = min(sh["u"] for sh in shapes)
        u1 = max(sh["u"] + sh["w"] for sh in shapes)
        y0 = min(sh["y"] for sh in shapes)
        y1 = max(sh["y"] + sh["h"] for sh in shapes)
    else:
        u0, u1 = (b[0], b[3]) if horiz == 0 else (b[2], b[5])
        y0, y1 = b[1], b[4]
    drawing = {
        "schema": SCHEMA, "kind": "ELEVATION", "face": f, "units": "m",
        "extent": [_q(u0), _q(y0), _q(u1), _q(y1)],
        "shapes": shapes,
        "opening_count": len([s for s in shapes if s["kind"] in ("DOOR", "WINDOW")]),
        "invented_features": 0,
        "writes_to_model": False,
        "note": "only openings present in the model appear; no facade feature is invented",
    }
    drawing["drawing_id"] = "rdrw_" + _sha16(drawing)
    return {"valid": True, "issues": [], "drawing": drawing}


def section_drawing(scene, axis="x", offset_m=None, options=None):
    """مقطع حقيقي عبر المشهد. يقصّ الأجسام المصرَّفة، ولا يبني هندسة جديدة."""
    ax = str(axis).lower()
    if ax not in SPEC["section_axes"]:
        return {"valid": False, "issues": [_issue("INVALID_TARGET", axis,
                                                  "unknown section axis")],
                "drawing": None}
    b = _bounds(scene)
    if b is None:
        return {"valid": False, "issues": [_issue("INVALID_CAMERA", "bounds",
                                                  "the scene declares no bounds")],
                "drawing": None}
    ai = 0 if ax == "x" else 2
    cut = _num(offset_m)
    if cut is None:
        cut = (b[ai] + b[ai + 3]) / 2.0
    horiz = 2 if ax == "x" else 0
    cut_shapes, beyond = [], []
    for ob in (scene.get("objects") or []):
        g = ob.get("geometry") or {}
        if g.get("type") != "box" or ob.get("visual_only"):
            continue
        c = [_num(g.get("cx")), _num(g.get("cy")), _num(g.get("cz"))]
        e = [_num(g.get("ex")), _num(g.get("ey")), _num(g.get("ez"))]
        if None in c or None in e:
            continue
        lo, hi = c[ai] - e[ai] / 2.0, c[ai] + e[ai] / 2.0
        rec = {"id": ob.get("id"), "kind": str(ob.get("kind")).upper(),
               "u": _q(c[horiz] - e[horiz] / 2.0), "w": _q(e[horiz]),
               "y": _q(c[1] - e[1] / 2.0), "h": _q(e[1])}
        if lo <= cut <= hi:
            rec["cut"] = True
            cut_shapes.append(rec)
        else:
            rec["cut"] = False
            beyond.append(rec)
    cut_shapes.sort(key=lambda s: str(s["id"]))
    beyond.sort(key=lambda s: str(s["id"]))
    allsh = cut_shapes + beyond
    if allsh:
        u0 = min(sh["u"] for sh in allsh)
        u1 = max(sh["u"] + sh["w"] for sh in allsh)
        y0 = min(sh["y"] for sh in allsh)
        y1 = max(sh["y"] + sh["h"] for sh in allsh)
    else:
        u0, u1, y0, y1 = b[horiz], b[horiz + 3], b[1], b[4]
    drawing = {
        "schema": SCHEMA, "kind": "SECTION", "axis": ax, "offset_m": _q(cut),
        "units": "m",
        "extent": [_q(u0), _q(y0), _q(u1), _q(y1)],
        "cut_shapes": cut_shapes, "beyond_shapes": beyond,
        "cut_count": len(cut_shapes),
        "levels": sorted(set(
            _q(_num((ob.get("geometry") or {}).get("cy")) or 0.0)
            for ob in (scene.get("objects") or [])
            if str(ob.get("kind")).upper() == "SLAB")),
        "writes_to_model": False,
        "note": "a section through the compiled scene; nothing is drawn that is not in the "
                "model",
    }
    drawing["drawing_id"] = "rdrw_" + _sha16(drawing)
    return {"valid": True, "issues": [], "drawing": drawing}


# ------------------------------------------- مخازن التحكّم (§35-§36) --------
def _project(cam, p, w, h):
    """إسقاط نقطة عالمية إلى بكسل. حتمي بالكامل ومطابق بين التطبيقين."""
    px, py, pz = float(p[0]), float(p[1]), float(p[2])
    ex, ey, ez = [float(v) for v in cam["position"]]
    tx, ty, tz = [float(v) for v in cam["target"]]
    fx, fy, fz = tx - ex, ty - ey, tz - ez
    fl = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / fl, fy / fl, fz / fl
    # يمين = تطبيع(أمام × أعلى)
    ux, uy, uz = 0.0, 1.0, 0.0
    rx, ry, rz = fy * uz - fz * uy, fz * ux - fx * uz, fx * uy - fy * ux
    rl = math.sqrt(rx * rx + ry * ry + rz * rz)
    if rl < 1e-9:
        rx, ry, rz, rl = 1.0, 0.0, 0.0, 1.0
    rx, ry, rz = rx / rl, ry / rl, rz / rl
    # أعلى = يمين × أمام
    vx, vy, vz = ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx
    dx, dy, dz = px - ex, py - ey, pz - ez
    cxx = dx * rx + dy * ry + dz * rz
    cyy = dx * vx + dy * vy + dz * vz
    czz = dx * fx + dy * fy + dz * fz
    if cam.get("projection") == "orthographic":
        oh = float(cam.get("ortho_height") or 1.0)
        if oh <= 0:
            oh = 1.0
        sy = (cyy / (oh / 2.0))
        sx = (cxx / ((oh * float(cam.get("aspect") or 1.0)) / 2.0))
        return (sx, sy, czz)
    if czz <= 0.01:
        return None
    t = math.tan(math.radians(float(cam["fov_deg"])) / 2.0)
    if t <= 0:
        return None
    sy = cyy / (czz * t)
    sx = cxx / (czz * t * float(cam.get("aspect") or 1.0))
    return (sx, sy, czz)


def _box_corners(g):
    cx, cy, cz = float(g["cx"]), float(g["cy"]), float(g["cz"])
    hx, hy, hz = float(g["ex"]) / 2.0, float(g["ey"]) / 2.0, float(g["ez"]) / 2.0
    rot = math.radians(float(g.get("rot_y") or 0.0))
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for sxg in (-1, 1):
        for syg in (-1, 1):
            for szg in (-1, 1):
                lx, ly, lz = hx * sxg, hy * syg, hz * szg
                wx = lx * ca + lz * sa
                wz = -lx * sa + lz * ca
                pts.append((cx + wx, cy + ly, cz + wz))
    return pts


def _semantic_class(obj):
    k = str(obj.get("kind")).upper()
    if obj.get("visual_only"):
        return "VISUAL_ONLY"
    if k in ("WALL", "EXTERIOR_WALL"):
        return "WALL"
    if k in ("DOOR", "WINDOW", "OPENING", "GLAZING"):
        return "OPENING"
    if k in ("SLAB", "FLOOR", "CEILING"):
        return "SLAB"
    if k in ("ROOF", "ROOF_CAP"):
        return "ROOF"
    if k == "STAIR":
        return "STAIR"
    if k in ("GROUND", "PAVING", "PARKING"):
        return "GROUND"
    return "OBJECT"


def control_buffers(scene, camera, width=None, height=None, kinds=None,
                    model_hash=None):
    """ينقّط مخازن التحكّم على المعالج بشكل حتمي — لا اعتماد على بطاقة رسوميات.

    كل مخزن مشتقّ من نفس المشهد ونفس الكاميرا ونفس الدقّة، فيكون متطابقاً في
    بايثون وجافاسكربت بايتاً ببايت، وقابلاً للمقارنة لاحقاً بأي مخرج ذكاء
    اصطناعي. هذه ليست عملية تحسين ولا عرضاً نهائياً.
    """
    # صفر صريح ليس "غير محدَّد": استعمال or يبتلعه ويستبدله بالافتراضي صامتاً
    w = int(SPEC["buffer_default_px"]["width"] if width is None else width)
    h = int(SPEC["buffer_default_px"]["height"] if height is None else height)
    if w <= 0 or h <= 0 or w * h > int(SPEC["buffer_max_px"]):
        return {"valid": False,
                "issues": [_issue("INVALID_RESOLUTION", [w, h],
                                  "buffer resolution out of range")], "buffers": None}
    want = [k for k in (kinds or BUFFER_KINDS) if k in BUFFER_KINDS]
    if not want:
        return {"valid": False,
                "issues": [_issue("BUFFER_MISSING", kinds, "no known buffer requested")],
                "buffers": None}
    n = w * h
    INF = 1e30
    depth = [INF] * n
    objid = [0] * n
    roomid = [0] * n
    sem = [0] * n
    nrm = [0] * n
    obj_names = [None]
    room_names = [None]
    room_of = {}
    for s in (scene.get("spaces_index") or []):
        if s.get("space_id") not in room_of:
            room_names.append(s.get("space_id"))
            room_of[s.get("space_id")] = len(room_names) - 1

    for ob in (scene.get("objects") or []):
        g = ob.get("geometry") or {}
        if g.get("type") != "box":
            continue
        pts = _box_corners(g)
        proj = []
        for p in pts:
            q = _project(camera, p, w, h)
            if q is None:
                proj = []
                break
            proj.append(q)
        if not proj:
            continue
        xs = [q[0] for q in proj]
        ys = [q[1] for q in proj]
        zs = [q[2] for q in proj]
        x0 = int(math.floor((min(xs) * 0.5 + 0.5) * w))
        x1 = int(math.ceil((max(xs) * 0.5 + 0.5) * w))
        y0 = int(math.floor((0.5 - max(ys) * 0.5) * h))
        y1 = int(math.ceil((0.5 - min(ys) * 0.5) * h))
        x0, x1 = max(0, x0), min(w, x1)
        y0, y1 = max(0, y0), min(h, y1)
        if x0 >= x1 or y0 >= y1:
            continue
        z = min(zs)
        obj_names.append(ob.get("id"))
        oi = len(obj_names) - 1
        sc = _semantic_class(ob)
        si = SEMANTIC_CLASSES.index(sc)
        meta = ob.get("meta") or {}
        rid = room_of.get(meta.get("space_id"), 0)
        # اتجاه السطح مقرَّب من نسبة أبعاد الصندوق — وصف ثابت لا إضاءة
        ex, ey, ez = float(g["ex"]), float(g["ey"]), float(g["ez"])
        if ey <= ex and ey <= ez:
            ni = 2                      # سطح أفقي
        elif ex <= ez:
            ni = 1                      # يواجه المحور x
        else:
            ni = 3                      # يواجه المحور z
        for yy in range(y0, y1):
            base = yy * w
            for xx in range(x0, x1):
                i = base + xx
                # الفتحة ثقب مقطوع في جدارها: لا يجوز أن يقف الجدار أمامها.
                # ضمن سماكة جدار معلنة تفوز الفتحة في الاتجاهين، وإلا اختفى
                # كل باب ونافذة خلف مضيفهما في كل مشهد خارجي.
                near = abs(z - depth[i]) <= _OPENING_BIAS_M
                if near and si == _SEM_OPENING and sem[i] == _SEM_WALL:
                    depth[i] = z if z < depth[i] else depth[i]
                    objid[i] = oi
                    roomid[i] = rid
                    sem[i] = si
                    nrm[i] = ni
                elif near and si == _SEM_WALL and sem[i] == _SEM_OPENING:
                    pass
                elif z < depth[i]:
                    depth[i] = z
                    objid[i] = oi
                    roomid[i] = rid
                    sem[i] = si
                    nrm[i] = ni

    dmax = 0.0
    for v in depth:
        if v < INF and v > dmax:
            dmax = v
    depth_out = [0 if v >= INF else int(round((v / dmax) * 65535.0)) if dmax > 0 else 0
                 for v in depth]
    edge = [0] * n
    for yy in range(h):
        for xx in range(w):
            i = yy * w + xx
            a = objid[i]
            if (xx + 1 < w and objid[i + 1] != a) or (yy + 1 < h and objid[i + w] != a):
                edge[i] = 1

    made = {}
    for k in want:
        made[k] = {"DEPTH": depth_out, "EDGE": edge, "NORMAL": nrm,
                   "OBJECT_ID": objid, "ROOM_ID": roomid, "SEMANTIC_MASK": sem}[k]
    out = {
        "schema": SCHEMA, "width": w, "height": h,
        "camera_id": camera.get("camera_id"),
        "projection": camera.get("projection"),
        # المشهد البصري يبصم النموذج في فضاء أسماء المصرّف، والمشروع يبصمه في
        # فضاء التأليف. المخزن يحمل الاثنين صراحةً، ويُثبَّت على البصمة التي
        # يمرّرها خطّ الأنابيب كي تُقارَن أشباهٌ بأشباه لا فضاءان مختلفان.
        "model_hash": scene.get("model_hash") if model_hash is None else model_hash,
        "scene_model_hash": scene.get("model_hash"),
        "kinds": list(want),
        "buffers": made,
        "object_names": obj_names, "room_names": room_names,
        "semantic_classes": list(SEMANTIC_CLASSES),
        "rasterised_on": "CPU_DETERMINISTIC",
        "gpu_dependent": False,
        "writes_to_model": False,
    }
    out["buffer_id"] = "rbuf_" + _sha16({k: made[k] for k in want})
    return {"valid": True, "issues": [], "buffers": out}


def buffers_aligned(a, b):
    """محاذاة صارمة: أي اختلاف في الدقّة أو الكاميرا أو البصمة يُعدّ فشلاً."""
    issues = []
    if not isinstance(a, dict) or not isinstance(b, dict):
        return {"aligned": False,
                "issues": [_issue("BUFFER_MISSING", "buffers", "a buffer set is missing")]}
    for f in SPEC["buffer_alignment_fields"]:
        if a.get(f) != b.get(f):
            issues.append(_issue("BUFFER_MISALIGNED", f,
                                 "control buffers disagree on %s" % f))
    return {"aligned": not issues, "issues": issues}


# ------------------------------------- سمات الهندسة وكشف الانحراف (§39-§41) -
def geometry_features(buffers):
    """يستخرج سمات هندسية كبرى من مخازن التحكّم — لا من الطراز ولا من المادّة."""
    b = buffers["buffers"]
    w, h = int(buffers["width"]), int(buffers["height"])
    sem = b.get("SEMANTIC_MASK")
    obj = b.get("OBJECT_ID")
    if sem is None or obj is None:
        return {"valid": False,
                "issues": [_issue("BUFFER_MISSING", "SEMANTIC_MASK/OBJECT_ID",
                                  "feature extraction needs the semantic and object "
                                  "buffers")], "features": None}
    bg = SEMANTIC_CLASSES.index("BACKGROUND")
    ground = SEMANTIC_CLASSES.index("GROUND")
    opening = SEMANTIC_CLASSES.index("OPENING")
    roof = SEMANTIC_CLASSES.index("ROOF")
    slab = SEMANTIC_CLASSES.index("SLAB")

    # ظلّ المبنى يقيس ما يحتويه النموذج فعلاً: الأرض والأجسام العرضية
    # (الأشجار، السياج البصري، غطاء السقف الاحتياطي) خارج القياس، وإلّا صار
    # انحراف الأثر مقيساً على زينة لا على هندسة.
    vis_only = SEMANTIC_CLASSES.index("VISUAL_ONLY")
    silhouette = [1 if (sem[i] != bg and sem[i] != ground and sem[i] != vis_only)
                  else 0 for i in range(w * h)]
    cols_top = []
    for xx in range(w):
        top = None
        for yy in range(h):
            if silhouette[yy * w + xx]:
                top = yy
                break
        cols_top.append(-1 if top is None else top)
    xs = [xx for xx in range(w) if cols_top[xx] >= 0]
    footprint = {"min_x": min(xs) if xs else 0, "max_x": max(xs) if xs else 0,
                 "area_px": sum(silhouette)}
    roof_line = [cols_top[xx] for xx in range(w)]
    roof_px = sum(1 for i in range(w * h) if sem[i] == roof)

    def _bands_from_rows(counts):
        out, run = [], None
        for yy in range(h):
            if counts[yy] > 0 and run is None:
                run = yy
            elif counts[yy] == 0 and run is not None:
                out.append([run, yy - 1])
                run = None
        if run is not None:
            out.append([run, h - 1])
        return out

    # نطاقات الأدوار: صفوف الفتحات هي الإشارة الأولى في مشهد خارجي (كل دور
    # يظهر شريط فتحات)، وصفوف البلاطات احتياط حين لا فتحة ظاهرة.
    open_rows = [sum(1 for xx in range(w) if sem[yy * w + xx] == opening)
                 for yy in range(h)]
    slab_rows = [sum(1 for xx in range(w) if sem[yy * w + xx] == slab)
                 for yy in range(h)]
    bands = _bands_from_rows(open_rows)
    band_basis = "OPENING_ROWS"
    if not bands:
        bands = _bands_from_rows(slab_rows)
        band_basis = "SLAB_ROWS"

    # الفتحات كمكوّنات متّصلة على قناع الفتحات
    seen = [0] * (w * h)
    comps = []
    for start in range(w * h):
        if sem[start] != opening or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        minx = maxx = start % w
        miny = maxy = start // w
        size = 0
        while stack:
            i = stack.pop()
            size += 1
            xx, yy = i % w, i // w
            if xx < minx:
                minx = xx
            if xx > maxx:
                maxx = xx
            if yy < miny:
                miny = yy
            if yy > maxy:
                maxy = yy
            for j in ((i - 1) if xx > 0 else -1, (i + 1) if xx + 1 < w else -1,
                      (i - w) if yy > 0 else -1, (i + w) if yy + 1 < h else -1):
                if j >= 0 and not seen[j] and sem[j] == opening:
                    seen[j] = 1
                    stack.append(j)
        comps.append({"cx": (minx + maxx) // 2, "cy": (miny + maxy) // 2,
                      "w": maxx - minx + 1, "h": maxy - miny + 1, "px": size})
    comps.sort(key=lambda c: (c["cx"], c["cy"]))

    feats = {
        "schema": SCHEMA, "width": w, "height": h,
        "model_hash": buffers.get("model_hash"),
        "camera_id": buffers.get("camera_id"),
        "silhouette_px": sum(silhouette),
        "silhouette_excludes_visual_only": True,
        "footprint": footprint,
        "roof_line": roof_line, "roof_px": roof_px,
        "floor_bands": bands, "floor_band_count": len(bands),
        "floor_band_basis": band_basis,
        "openings": comps, "opening_count": len(comps),
        "wall_px": sum(1 for i in range(w * h)
                       if sem[i] == SEMANTIC_CLASSES.index("WALL")),
        "semantic_object_ids": sorted(set(
            buffers["object_names"][o] for o in obj
            if o and buffers["object_names"][o])),
    }
    feats["feature_id"] = _sha16({k: feats[k] for k in
                                  ("silhouette_px", "footprint", "floor_band_count",
                                   "opening_count", "roof_px")})
    return {"valid": True, "issues": [], "features": feats}


def _iou(a, b):
    if a <= 0 and b <= 0:
        return 1.0
    lo, hi = (a, b) if a < b else (b, a)
    if hi <= 0:
        return 0.0
    return lo / float(hi)


def detect_drift(reference, candidate, required_semantic_ids=None):
    """يقارن سمات مرجعية حتمية بسمات مخرج ذكاء اصطناعي. لا يعدّل النموذج أبداً."""
    issues, drifts = [], []
    if not isinstance(reference, dict) or not isinstance(candidate, dict):
        return {"valid": False, "status": "REJECTED", "drifts": [],
                "issues": [_issue("BUFFER_MISSING", "features",
                                  "a feature set is missing")],
                "writes_to_model": False}
    if reference.get("width") != candidate.get("width") \
            or reference.get("height") != candidate.get("height"):
        issues.append(_issue("BUFFER_MISALIGNED", "resolution",
                             "the candidate is not at the reference resolution"))
    if reference.get("camera_id") != candidate.get("camera_id"):
        issues.append(_issue("BUFFER_MISALIGNED", "camera_id",
                             "the candidate is not from the reference camera"))
    if reference.get("model_hash") != candidate.get("model_hash"):
        issues.append(_issue("MODEL_HASH_MISMATCH", "model_hash",
                             "the candidate is not pinned to the reference model"))

    def add(t, detail, severity=None):
        drifts.append({"type": t, "severity": severity or SPEC["drift_severity"][t],
                       "detail": detail})

    rb = int(reference.get("floor_band_count") or 0)
    cb = int(candidate.get("floor_band_count") or 0)
    if rb != cb:
        add("FLOOR_COUNT_DRIFT",
            "the reference shows %d floor bands, the candidate shows %d" % (rb, cb))

    ro = int(reference.get("opening_count") or 0)
    co = int(candidate.get("opening_count") or 0)
    if co > ro:
        add("WINDOW_ADDED", "the candidate shows %d openings, the reference %d"
            % (co, ro))
    elif co < ro:
        add("WINDOW_REMOVED", "the candidate shows %d openings, the reference %d"
            % (co, ro))
    else:
        tol = int(THRESH["opening_center_tolerance_px"])
        ra, ca = reference.get("openings") or [], candidate.get("openings") or []
        for i in range(min(len(ra), len(ca))):
            dx = abs(int(ra[i]["cx"]) - int(ca[i]["cx"]))
            dy = abs(int(ra[i]["cy"]) - int(ca[i]["cy"]))
            if dx > tol or dy > tol:
                add("DOOR_MOVED", "an opening centre moved %d,%d px (tolerance %d)"
                    % (dx, dy, tol))
                break

    fi = _iou(int((reference.get("footprint") or {}).get("area_px") or 0),
              int((candidate.get("footprint") or {}).get("area_px") or 0))
    if fi < float(THRESH["footprint_iou_min"]):
        add("FOOTPRINT_DRIFT", "footprint overlap %.3f is below the declared minimum %.3f"
            % (fi, float(THRESH["footprint_iou_min"])))

    wi = _iou(int(reference.get("wall_px") or 0), int(candidate.get("wall_px") or 0))
    if wi < float(THRESH["wall_layout_iou_min"]):
        add("WALL_LAYOUT_DRIFT", "wall coverage overlap %.3f is below the declared "
                                 "minimum %.3f" % (wi, float(THRESH["wall_layout_iou_min"])))

    rl = reference.get("roof_line") or []
    cl = candidate.get("roof_line") or []
    if len(rl) == len(cl) and rl:
        worst = 0
        for i in range(len(rl)):
            if rl[i] < 0 and cl[i] < 0:
                continue
            d = abs(int(rl[i]) - int(cl[i]))
            if d > worst:
                worst = d
        if worst > int(THRESH["roof_line_tolerance_px"]):
            add("ROOF_GEOMETRY_DRIFT",
                "the roof line moved %d px (tolerance %d)"
                % (worst, int(THRESH["roof_line_tolerance_px"])))

    if required_semantic_ids:
        have = set(candidate.get("semantic_object_ids") or [])
        missing = sorted(set(required_semantic_ids) - have)
        if missing:
            add("SEMANTIC_OBJECT_MISSING",
                "requested semantic objects are absent from the candidate: %s"
                % ", ".join(missing[:4]))

    major = [d for d in drifts if d["severity"] == "MAJOR"]
    minor = [d for d in drifts if d["severity"] == "MINOR"]
    if issues or len(major) >= int(THRESH["major_drift_reject_at"]):
        status = "REJECTED"
    elif len(minor) >= int(THRESH["minor_drift_warn_at"]):
        status = "WARNING"
    else:
        status = "PASS"
    return {
        "valid": True, "status": status, "drifts": drifts, "issues": issues,
        "major_count": len(major), "minor_count": len(minor),
        "presented_as_model_faithful": status == "PASS",
        "drift_code": SPEC["drift_rejected_code"] if status == "REJECTED" else None,
        "may_regenerate": status != "PASS",
        "writes_to_model": False,
        "note": "material and detail differences are expected and are not drift; a "
                "rejected image is never presented as model faithful and no drift result "
                "edits the model",
    }


# ------------------------------------------ حدود الذكاء الاصطناعي (§34-§38) -
def ai_prompt_contract(request, visual_intent=None, references=None):
    """عقد التوجيه: ما يجب صونه وما يجوز تحسينه، معلناً حرفياً في كل طلب."""
    refs = [r for r in (references or []) if isinstance(r, dict)]
    safe_refs = []
    for r in refs:
        if not is_allowed_uri(str(r.get("uri") or "")):
            continue
        if is_unsafe(str(r.get("caption") or "")):
            continue
        if not is_safe_id(str(r.get("reference_id") or "")):
            continue
        safe_refs.append({"reference_id": r.get("reference_id"), "kind": r.get("kind"),
                          "scope": r.get("scope")})
    intent = {}
    if isinstance(visual_intent, dict):
        for k, v in sorted(visual_intent.items()):
            if is_safe_prose(v):
                intent[k] = v
    return {
        "schema": SCHEMA,
        "preserve": list(SPEC["ai_preserve"]),
        "may_enhance": list(SPEC["ai_may_enhance"]),
        "visual_intent": intent,
        "reference_ids": [r["reference_id"] for r in safe_refs],
        "references": safe_refs,
        "view_type": request.get("view_type"),
        "theme": request.get("theme"),
        "lighting": request.get("lighting"),
        "text": ("Preserve exactly: " + ", ".join(SPEC["ai_preserve"]) +
                 ". You may enhance only: " + ", ".join(SPEC["ai_may_enhance"]) +
                 ". The supplied control buffers define the geometry; do not depart "
                 "from them."),
        "geometry_control_supplied": None,
        "writes_to_model": False,
    }


def ai_request(request, base_render, buffers, prompt_contract, provider=None):
    """طلب تحسين. لا يُرسَل نصّ وحده ما دامت بيانات التحكّم الهندسية متاحة."""
    issues = []
    if not isinstance(buffers, dict) or not buffers.get("buffers"):
        issues.append(_issue("BUFFER_MISSING", "control_buffers",
                             "control buffers are required before an enhancement request"))
    if base_render is None:
        issues.append(_issue("BUFFER_MISSING", "base_render",
                             "the deterministic base render is required first"))
    if isinstance(base_render, dict) and isinstance(buffers, dict):
        if base_render.get("camera_id") and buffers.get("camera_id") \
                and base_render["camera_id"] != buffers["camera_id"]:
            issues.append(_issue("BUFFER_MISALIGNED", "camera_id",
                                 "the base render and the control buffers use different "
                                 "cameras"))
        if base_render.get("model_hash") and buffers.get("model_hash") \
                and base_render["model_hash"] != buffers["model_hash"]:
            issues.append(_issue("MODEL_HASH_MISMATCH", "model_hash",
                                 "the base render and the control buffers are pinned to "
                                 "different models"))
    contract = _copy(prompt_contract or {})
    contract["geometry_control_supplied"] = bool(
        isinstance(buffers, dict) and buffers.get("kinds"))
    req = {
        "schema": SCHEMA,
        "stage_pipeline": list(SPEC["pipeline"]),
        "model_hash": (buffers or {}).get("model_hash"),
        "revision_id": request.get("revision_id"),
        "building_id": request.get("building_id"),
        "base_render_id": (base_render or {}).get("render_id"),
        "camera_id": (buffers or {}).get("camera_id"),
        "control_buffer_id": (buffers or {}).get("buffer_id"),
        "supplied_buffers": list((buffers or {}).get("kinds") or []),
        "prompt": contract,
        "text_only": not contract["geometry_control_supplied"],
        "reference_ids": list(request.get("reference_ids") or []),
        "provider": provider,
        "writes_to_model": False,
        "engineering_authority": False,
        "generator_shipped": SPEC["photorealistic_engine_shipped"],
    }
    if issues:
        return {"valid": False, "issues": issues, "request": None}
    return {"valid": True, "issues": [], "request": req}


def provider_adapter(provider_id, available=False, timeout_s=60):
    """حدّ المزوّد. لا افتراض خاصّ بمزوّد داخل المشهد البصري."""
    return {
        "schema": SCHEMA, "provider_id": provider_id,
        "accepts": ["base_image", "control_buffers", "prompt", "reference_images"],
        "returns": ["presentation_image", "provider_model", "generated_at"],
        "timeout_s": int(timeout_s),
        "available": bool(available),
        "requires_secret": True,
        "secret_location": SPEC["provider_secret_location"],
        "secret_in_client": False,
        "secret_in_metadata": False,
        "secret_in_logs": False,
        "note": "a provider key lives in the server environment only and never appears in "
                "client source, render metadata or a log",
    }


def ai_enhance(adapter, ai_req, provider_result=None):
    """ينفّذ التحسين عبر المحوّل. أي فشل يُبقي العرض الحتمي كما هو."""
    if not adapter.get("available") or provider_result is None:
        return {"valid": False, "used_ai": False,
                "issues": [_issue("PROVIDER_UNAVAILABLE", adapter.get("provider_id"),
                                  "the enhancement provider returned nothing; the "
                                  "deterministic render remains the output",
                                  "WARNING")],
                "fallback": "DETERMINISTIC_BASE_RENDER",
                "base_render_id": ai_req.get("base_render_id"),
                "output": None, "writes_to_model": False}
    out = {
        "type": SPEC["ai_output_type"],
        "engineering_authority": SPEC["ai_engineering_authority"],
        "model_hash": ai_req.get("model_hash"),
        "revision_id": ai_req.get("revision_id"),
        "base_render_id": ai_req.get("base_render_id"),
        "camera_id": ai_req.get("camera_id"),
        "reference_ids": list(ai_req.get("reference_ids") or []),
        "provider": adapter.get("provider_id"),
        "provider_model": provider_result.get("provider_model"),
        "generated_at": provider_result.get("generated_at"),
        "image_ref": provider_result.get("image_ref"),
        "geometry_fidelity": None,
        "writes_to_model": False,
    }
    return {"valid": True, "used_ai": True, "issues": [], "fallback": None,
            "output": out, "writes_to_model": False}


# ------------------------------------------ الناتج والأثر (§57-§58, §61) ----
def render_descriptor(request, camera, kind="DETERMINISTIC_RENDER", options=None):
    """واصف ناتج عرض. مثبَّت على بصمة النموذج والمراجعة، ولا يشهد بشيء."""
    o = options or {}
    d = {
        "schema": SCHEMA,
        "render_id": None,
        "kind": kind,
        "model_hash": request.get("model_hash"),
        "revision_id": request.get("revision_id"),
        "building_id": request.get("building_id"),
        "level_id": request.get("level_id"),
        "space_id": request.get("space_id"),
        "camera": _copy(camera) if camera else None,
        "camera_id": (camera or {}).get("camera_id"),
        "view_type": request.get("view_type"),
        "quality": request.get("quality"),
        "theme": request.get("theme"),
        "lighting": request.get("lighting"),
        "ai_used": kind == "AI_ENHANCED_VISUALIZATION",
        "ai_provider": o.get("ai_provider"),
        "ai_provider_model": o.get("ai_provider_model"),
        "reference_ids": list(request.get("reference_ids") or []),
        "generated_at": o.get("created_at"),
        "geometry_fidelity": o.get("geometry_fidelity"),
        "visual_default_applied": bool(o.get("visual_default_applied")),
        "resolution": o.get("resolution_rendered"),
        "resolution_claimed_rendered": o.get("resolution_rendered") is not None,
        "engineering_authority": False,
        "certifies_nothing": True,
        "writes_to_model": False,
        "note": "a render is a presentation output pinned to one revision. It certifies "
                "nothing and is never engineering truth",
    }
    d["render_id"] = "rnd_" + _sha16({k: d[k] for k in SPEC["metadata_fields"] if k in d})
    return d


def staleness(render, project):
    """قِدَم المصدر. الناتج لا يُحذف ولا يُعاد توجيهه صامتاً إلى مراجعة أخرى."""
    cur = project.get("current_revision")
    ch = project.get("model_hash")
    stale = (render.get("revision_id") != cur) or (render.get("model_hash") != ch)
    return {
        "render_id": render.get("render_id"),
        "status": "STALE_SOURCE_MODEL" if stale else "CURRENT",
        "render_revision": render.get("revision_id"),
        "current_revision": cur,
        "auto_deleted": False,
        "auto_repointed": False,
        "note": "a render stays associated with the revision it was produced from",
    }


def gallery(renders, project):
    cards = []
    for r in (renders or []):
        st = staleness(r, project)
        cards.append({
            "render_id": r.get("render_id"),
            "thumbnail": r.get("thumbnail"),
            "view_type": r.get("view_type"),
            "revision_id": r.get("revision_id"),
            "theme": r.get("theme"),
            "kind": r.get("kind"),
            "geometry_fidelity": r.get("geometry_fidelity"),
            "staleness": st["status"],
        })
    cards.sort(key=lambda c: str(c["render_id"]))
    return {
        "schema": SCHEMA, "cards": cards, "count": len(cards),
        "persistence": SPEC["gallery_persistence"],
        "cloud": SPEC["gallery_cloud"],
        "stale_count": len([c for c in cards if c["staleness"] == "STALE_SOURCE_MODEL"]),
        "writes_to_model": False,
    }


def variant(request, name, overrides=None):
    """نسخة بصرية فوق نفس بصمة النموذج. تبديلها لا ينشئ مراجعة هندسية."""
    v = {
        "variant_id": None,
        "name": str(name),
        "model_hash": request.get("model_hash"),
        "revision_id": request.get("revision_id"),
        "theme": request.get("theme"),
        "lighting": request.get("lighting"),
        "quality": request.get("quality"),
        "material_overrides": _copy(overrides or {}),
        "decor_enabled": bool((request.get("context_flags") or [])
                              and "entourage" in request.get("context_flags")),
        "landscape_enabled": "vegetation" in (request.get("context_flags") or []),
        "entourage_enabled": "entourage" in (request.get("context_flags") or []),
        "creates_revision": False,
        "writes_to_model": False,
    }
    v["variant_id"] = "rvar_" + _sha16(v)
    return v


# ------------------------------------------------ فصل العرضي عن الدلالي ----
def separate_visual(scene):
    """يفصل الأجسام الدلالية عن أجسام العرض. العدّان لا يختلطان أبداً."""
    semantic, visual = [], []
    for ob in (scene.get("objects") or []):
        rec = {"id": ob.get("id"), "kind": ob.get("kind"), "layer": ob.get("layer")}
        if ob.get("visual_only"):
            layer = str(ob.get("layer")).upper()
            rec["tag"] = (SPEC["landscape_tag"] if layer == "LANDSCAPE" else
                          SPEC["entourage_tag"] if layer == "ENTOURAGE" else
                          SPEC["decoration_tag"])
            visual.append(rec)
        else:
            semantic.append(rec)
    semantic.sort(key=lambda r: str(r["id"]))
    visual.sort(key=lambda r: str(r["id"]))
    return {
        "semantic_objects": semantic, "semantic_count": len(semantic),
        "visual_only_objects": visual, "visual_only_count": len(visual),
        "counts_are_separate": True,
        "visual_enters_semantic_count": False,
        "visual_becomes_site_data": False,
        "note": "visual furniture, plants, people and vehicles are presentation objects and "
                "never enter semantic object counts or site engineering data",
    }


def context_enabled(request, flag):
    """سياق العرض اختياري لكل طلب، ولا يُشتقّ أبداً من نوع المبنى."""
    return flag in (request.get("context_flags") or [])


# --------------------------------------------- إخراج متّجه ونقطي (§25/§55) --
def _esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _fmt(v):
    """تنسيق رقم موحّد للمخرج المتّجه — يمنع انحراف النصّ بين التطبيقين."""
    n = round(float(v), 3) + 0.0
    if n == int(n):
        return str(int(n))
    return ("%.3f" % n).rstrip("0").rstrip(".")


_PLAN_STYLE = {
    "TECHNICAL":    {"bg": "#ffffff", "wall": "#111111", "space": "#f6f6f4",
                     "text": "#222222", "open": "#ffffff", "stair": "#dddddd"},
    "CLEAN":        {"bg": "#ffffff", "wall": "#2b2b2b", "space": "#f2efe9",
                     "text": "#3a3a3a", "open": "#ffffff", "stair": "#e3ded3"},
    "MONOCHROME":   {"bg": "#ffffff", "wall": "#000000", "space": "#ffffff",
                     "text": "#000000", "open": "#ffffff", "stair": "#eeeeee"},
    "PRESENTATION": {"bg": "#12161c", "wall": "#e8e6e1", "space": "#1d232c",
                     "text": "#cfd6de", "open": "#12161c", "stair": "#2b3440"},
}


def plan_svg(drawing, options=None):
    """يحوّل مسقطاً مشتقّاً إلى SVG. كل شكل من الرسم، ولا شكل يُضاف هنا."""
    o = options or {}
    st = _PLAN_STYLE.get(drawing.get("style"), _PLAN_STYLE["CLEAN"])
    px_per_m = float(o.get("px_per_m") or 34.0)
    pad = float(o.get("padding_px") or 46.0)
    ex = drawing.get("extent") or [0, 0, 1, 1]
    w_m, h_m = float(ex[2]) - float(ex[0]), float(ex[3]) - float(ex[1])
    W = int(round(w_m * px_per_m + pad * 2))
    H = int(round(h_m * px_per_m + pad * 2))
    X = lambda x: _fmt((float(x) - float(ex[0])) * px_per_m + pad)
    Y = lambda y: _fmt((float(y) - float(ex[1])) * px_per_m + pad)
    S = lambda v: _fmt(float(v) * px_per_m)
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="system-ui,Segoe UI,Tahoma,sans-serif">'
         % (W, H, W, H),
         '<rect width="%d" height="%d" fill="%s"/>' % (W, H, st["bg"])]
    for s in drawing.get("spaces") or []:
        r = s.get("rect") or [0, 0, 0, 0]
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'stroke="none" data-space="%s"/>'
                 % (X(r[0]), Y(r[1]), S(r[2]), S(r[3]), st["space"],
                    _esc(s.get("space_id"))))
    for w in drawing.get("walls") or []:
        p.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                 'stroke-width="%s" stroke-linecap="square" data-wall="%s"/>'
                 % (X(w["x1"]), Y(w["y1"]), X(w["x2"]), Y(w["y2"]), st["wall"],
                    S(max(0.08, float(w.get("thickness_m") or 0.2))), _esc(w["id"])))
    for d in drawing.get("doors") or []:
        ww = float(d.get("width_m") or 0.9)
        horiz = str(d.get("axis")) == "x"
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'stroke="%s" stroke-width="1" data-door="%s"/>'
                 % (X(float(d["x"]) - (ww / 2 if horiz else 0.13)),
                    Y(float(d["y"]) - (0.13 if horiz else ww / 2)),
                    S(ww if horiz else 0.26), S(0.26 if horiz else ww),
                    st["open"], st["wall"], _esc(d["id"])))
    for d in drawing.get("windows") or []:
        ww = float(d.get("width_m") or 1.2)
        horiz = str(d.get("axis")) == "x"
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'stroke="%s" stroke-width="1.4" data-window="%s"/>'
                 % (X(float(d["x"]) - (ww / 2 if horiz else 0.09)),
                    Y(float(d["y"]) - (0.09 if horiz else ww / 2)),
                    S(ww if horiz else 0.18), S(0.18 if horiz else ww),
                    st["open"], "#4a7d94", _esc(d["id"])))
    for s in drawing.get("stairs") or []:
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'stroke="%s" stroke-width="1" data-stair="%s"/>'
                 % (X(float(s["x"]) - float(s["w"]) / 2),
                    Y(float(s["y"]) - float(s["d"]) / 2),
                    S(s["w"]), S(s["d"]), st["stair"], st["wall"], _esc(s["id"])))
    for f in drawing.get("furniture") or []:
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" '
                 'stroke="%s" stroke-width="1" stroke-dasharray="3 2" '
                 'data-furniture="%s"/>'
                 % (X(float(f["x"]) - float(f["w"]) / 2),
                    Y(float(f["y"]) - float(f["d"]) / 2),
                    S(f["w"]), S(f["d"]), st["text"], _esc(f["id"])))
    for s in drawing.get("spaces") or []:
        r = s.get("rect") or [0, 0, 0, 0]
        cx = float(r[0]) + float(r[2]) / 2.0
        cy = float(r[1]) + float(r[3]) / 2.0
        p.append('<text x="%s" y="%s" fill="%s" font-size="11" text-anchor="middle" '
                 'data-label="%s">%s</text>'
                 % (X(cx), Y(cy), st["text"], _esc(s.get("space_id")),
                    _esc(s.get("name") or s.get("space_id"))))
        p.append('<text x="%s" y="%s" fill="%s" font-size="9" text-anchor="middle" '
                 'opacity="0.75">%s m²</text>'
                 % (X(cx), _fmt(float(Y(cy)) + 13), st["text"],
                    _fmt(s.get("area_m2") or 0)))
    if drawing.get("north_shown"):
        p.append('<g data-north="1"><circle cx="%s" cy="26" r="13" fill="none" '
                 'stroke="%s"/><text x="%s" y="30" fill="%s" font-size="11" '
                 'text-anchor="middle">N</text></g>'
                 % (_fmt(W - 30), st["text"], _fmt(W - 30), st["text"]))
    p.append('<text x="%s" y="%s" fill="%s" font-size="9" opacity="0.7">'
             'presentation drawing — not a construction drawing</text>'
             % (_fmt(pad), _fmt(H - 14), st["text"]))
    p.append('</svg>')
    return "\n".join(p)


def elevation_svg(drawing, options=None):
    """واجهة متّجهة. الأشكال من النموذج وحده — لا فتحة ولا عنصر مضاف هنا."""
    o = options or {}
    px_per_m = float(o.get("px_per_m") or 34.0)
    pad = float(o.get("padding_px") or 46.0)
    ex = drawing.get("extent") or [0, 0, 1, 1]
    w_m, h_m = float(ex[2]) - float(ex[0]), float(ex[3]) - float(ex[1])
    W = int(round(w_m * px_per_m + pad * 2))
    H = int(round(h_m * px_per_m + pad * 2))
    X = lambda x: _fmt((float(x) - float(ex[0])) * px_per_m + pad)
    Y = lambda y: _fmt(H - pad - (float(y) - float(ex[1])) * px_per_m)
    S = lambda v: _fmt(float(v) * px_per_m)
    fill = {"WALL": "#dcd8d0", "SLAB": "#c6c2ba", "DOOR": "#8a6a44",
            "WINDOW": "#9dc4d6", "STAIR": "#cfcabf", "ROOF_CAP": "#b9b4aa",
            "CEILING": "#d2cec6"}
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="system-ui,Segoe UI,Tahoma,sans-serif">'
         % (W, H, W, H),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H)]
    for s in drawing.get("shapes") or []:
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'stroke="#3a3a3a" stroke-width="0.6" data-shape="%s" data-kind="%s"/>'
                 % (X(s["u"]), Y(float(s["y"]) + float(s["h"])), S(s["w"]), S(s["h"]),
                    fill.get(s["kind"], "#e2e0db"), _esc(s["id"]), _esc(s["kind"])))
    p.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#111" stroke-width="1.4"/>'
             % (_fmt(pad * 0.4), Y(0), _fmt(W - pad * 0.4), Y(0)))
    p.append('<text x="%s" y="%s" fill="#333" font-size="10">%s elevation — '
             '%d modelled openings, 0 invented</text>'
             % (_fmt(pad), _fmt(H - 14), _esc(drawing.get("face")),
                int(drawing.get("opening_count") or 0)))
    p.append('</svg>')
    return "\n".join(p)


def section_svg(drawing, options=None):
    """مقطع متّجه. المقطوع مصمت والخلفي باهت — كلاهما من المشهد المصرَّف."""
    o = options or {}
    px_per_m = float(o.get("px_per_m") or 34.0)
    pad = float(o.get("padding_px") or 46.0)
    ex = drawing.get("extent") or [0, 0, 1, 1]
    w_m, h_m = float(ex[2]) - float(ex[0]), float(ex[3]) - float(ex[1])
    W = int(round(w_m * px_per_m + pad * 2))
    H = int(round(h_m * px_per_m + pad * 2))
    X = lambda x: _fmt((float(x) - float(ex[0])) * px_per_m + pad)
    Y = lambda y: _fmt(H - pad - (float(y) - float(ex[1])) * px_per_m)
    S = lambda v: _fmt(float(v) * px_per_m)
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="system-ui,Segoe UI,Tahoma,sans-serif">'
         % (W, H, W, H),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H)]
    for s in drawing.get("beyond_shapes") or []:
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#eeece8" '
                 'stroke="#cfcbc4" stroke-width="0.5" data-beyond="%s"/>'
                 % (X(s["u"]), Y(float(s["y"]) + float(s["h"])), S(s["w"]), S(s["h"]),
                    _esc(s["id"])))
    for s in drawing.get("cut_shapes") or []:
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#2b2b2b" '
                 'stroke="#000" stroke-width="0.8" data-cut="%s" data-kind="%s"/>'
                 % (X(s["u"]), Y(float(s["y"]) + float(s["h"])), S(s["w"]), S(s["h"]),
                    _esc(s["id"]), _esc(s["kind"])))
    p.append('<text x="%s" y="%s" fill="#333" font-size="10">section on %s at %s m — '
             '%d cut elements</text>'
             % (_fmt(pad), _fmt(H - 14), _esc(drawing.get("axis")),
                _fmt(drawing.get("offset_m") or 0), int(drawing.get("cut_count") or 0)))
    p.append('</svg>')
    return "\n".join(p)


# ------------------------------------------------ صورة مخزن تحكّم حتمية ----
_CRC_TABLE = None


def _crc32(data):
    global _CRC_TABLE
    if _CRC_TABLE is None:
        t = []
        for n in range(256):
            c = n
            for _ in range(8):
                c = (0xEDB88320 ^ (c >> 1)) if (c & 1) else (c >> 1)
            t.append(c)
        _CRC_TABLE = t
    c = 0xFFFFFFFF
    for b in data:
        c = _CRC_TABLE[(c ^ b) & 0xFF] ^ (c >> 8)
    return (c ^ 0xFFFFFFFF) & 0xFFFFFFFF


def _adler32(data):
    a, b = 1, 0
    for x in data:
        a = (a + x) % 65521
        b = (b + a) % 65521
    return ((b << 16) | a) & 0xFFFFFFFF


def _be32(n):
    return bytes([(n >> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255])


def _chunk(tag, data):
    body = tag.encode("ascii") + data
    return _be32(len(data)) + body + _be32(_crc32(body))


def buffer_png(buffers, kind):
    """يكتب مخزن تحكّم كصورة PNG رمادية بلا ضغط — بايتات حتمية في كل تطبيق.

    الكتل مخزَّنة لا مضغوطة عمداً: مستويات الضغط تختلف بين المكتبات، وبقاء
    البايتات متطابقة بين بايثون وجافاسكربت شرطٌ في هذه المرحلة.
    """
    if kind not in buffers.get("kinds", []):
        return None
    w, h = int(buffers["width"]), int(buffers["height"])
    src = buffers["buffers"][kind]
    mx = 0
    for v in src:
        if v > mx:
            mx = v
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        row = y * w
        for x in range(w):
            v = src[row + x]
            raw.append(0 if mx == 0 else int((v * 255) // mx) & 255)
    # zlib بكتل مخزَّنة
    z = bytearray([0x78, 0x01])
    i, n = 0, len(raw)
    while i < n:
        blk = min(65535, n - i)
        last = 1 if (i + blk >= n) else 0
        z.append(last)
        z += bytes([blk & 255, (blk >> 8) & 255,
                    (~blk) & 255, ((~blk) >> 8) & 255])
        z += raw[i:i + blk]
        i += blk
    z += _be32(_adler32(raw))
    png = (bytes([137, 80, 78, 71, 13, 10, 26, 10])
           + _chunk("IHDR", _be32(w) + _be32(h) + bytes([8, 0, 0, 0, 0]))
           + _chunk("IDAT", bytes(z))
           + _chunk("IEND", b""))
    return png
