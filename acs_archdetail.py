# -*- coding: utf-8 -*-
"""طبقة الأمانة البصرية المعمارية — المرحلة 9.2.

الطبقة الحتمية لتفصيل العرض المعماري: تصنيف التفاصيل، تقسيم خامات الواجهة،
تجميعات النوافذ والأبواب، إنارة LED العرضية، التأثيث العرضي، مكتبة الكائنات
العرضية العامة (مركبات، معدات مناولة، تنسيق، موقع)، التنويع الحتمي للخامات،
مفسّر الطلبات البصرية، التشخيص البصري وتغطية الطلبات — كلها دوالّ نقيّة على
JSON تُقارَن حرفاً بحرف مع مرآة المتصفح.

القانون الحاكم واحد لا يتغيّر: النموذج الهندسي القانوني هو مصدر الحقيقة
الوحيد، وهذه الطبقة في اتجاه المصبّ دائماً — لا سهم عائد، ولا ترقية صامتة
لأي افتراض عرضي إلى حقيقة هندسية.
"""
import hashlib
import json
import math
import os

import acs_pbr as P
import acs_ingest as ING

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_archdetail.json"), "r",
          encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
ISSUE_CODES = tuple(SPEC["issue_codes"])
BLOCKING = tuple(SPEC["blocking_issue_codes"])
MATERIALS = {m["id"]: m for m in SPEC["presentation_materials"]}
PROFILES = SPEC["detail_profiles"]
STAGING = SPEC["staging_modes"]
CAMERAS_ARCH = SPEC["camera_presets_arch"]
ENVIRONMENTS = SPEC["environment_presets"]
RECIPES_VEHICLE = SPEC["vehicle_recipes"]
RECIPES_FORKLIFT = SPEC["forklift_recipes"]
RECIPES_FURNITURE = SPEC["furniture_recipes"]
RECIPES_LANDSCAPE = SPEC["landscape_recipes"]
LIBRARY = SPEC["object_library"]
KEYMAP = SPEC["request_interpretation"]["keyword_map"]
DETAIL_CLASSES = tuple(SPEC["detail_classes"])
AUTHORITY_CLASSES = tuple(SPEC["object_authority_classes"])
STATUSES = tuple(SPEC["diagnostic_statuses"])

_canon = ING.canonical_json
_q = P._q
_num = P._num


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def issue(code, severity, element_id, message):
    if code not in ISSUE_CODES:
        raise ValueError("undeclared archdetail issue code: %s" % code)
    return {"code": code, "severity": severity, "element_id": element_id,
            "message": message, "blocking": code in BLOCKING}


def _flags(source_element_id, provenance, confidence, reason, context=False):
    """الأعلام الإلزامية على كل كائن عرضي (§1)."""
    f = {"visual_only": True, "source_element_id": source_element_id,
         "provenance": provenance, "confidence": confidence,
         "reason": reason}
    if context:
        f["presentation_context"] = True
    return f


# ------------------------------------------------------ خامات العرض ----
def material(mid, override=None):
    """خامة عرضية معمارية بمصدر كل حقل — نفس دلالات المرحلة 9.1 حرفياً."""
    if mid not in MATERIALS:
        return {"valid": False, "material": None,
                "issues": [issue("AD_INVALID_MATERIAL", "ERROR", mid,
                                 "presentation material is not declared")]}
    base = MATERIALS[mid]
    out = {}
    prov = {}
    issues = []
    for k in sorted(base):
        if k in ("name_en", "name_ar"):
            out[k] = base[k]
            continue
        out[k] = base[k]
        if k in P._OVERRIDABLE:
            prov[k] = "PRESENTATION_DEFAULT"
    ov = override if isinstance(override, dict) else {}
    for k in sorted(ov):
        if not P.safe_key(k) or k not in P._OVERRIDABLE:
            issues.append(issue("AD_INVALID_MATERIAL", "ERROR", mid,
                                "override key refused: %s" % k))
            return {"valid": False, "material": None, "issues": issues}
        v = ov[k]
        if k in ("base_color", "emissive"):
            s = v if isinstance(v, str) else ""
            ok = (len(s) == 7 and s[0] == "#"
                  and all(c in "0123456789abcdefABCDEF" for c in s[1:]))
            if not ok:
                issues.append(issue("AD_INVALID_MATERIAL", "ERROR", mid,
                                    "invalid color for %s" % k))
                return {"valid": False, "material": None, "issues": issues}
            out[k] = s.lower()
        else:
            n = _num(v)
            if n is None or n < 0 or n > 20:
                issues.append(issue("AD_INVALID_MATERIAL", "ERROR", mid,
                                    "out-of-range override for %s" % k))
                return {"valid": False, "material": None, "issues": issues}
            out[k] = _q(n)
        prov[k] = "USER_VISUAL_OVERRIDE"
    out["provenance"] = prov
    out["is_engineering_truth"] = False
    return {"valid": True, "material": out, "issues": issues}


def variation(model_hash, element_id, material_id):
    """تنويع حتمي محكوم: نفس النموذج → نفس التنويع دائماً (§23)."""
    seed = "%s|%s|%s" % (model_hash, element_id, material_id)
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    r_max = float(SPEC["variation"]["roughness_jitter_max"])
    a_max = float(SPEC["variation"]["albedo_jitter_max"])
    n_max = float(SPEC["variation"]["normal_perturb_max"])

    def frac(a, b):
        return int(h[a:b], 16) / float(16 ** (b - a) - 1)

    return {"seed": h[:16], "deterministic": True,
            "roughness_delta": _q((frac(0, 8) * 2.0 - 1.0) * r_max),
            "albedo_delta": _q((frac(8, 16) * 2.0 - 1.0) * a_max),
            "normal_delta": _q(frac(16, 24) * n_max)}


# ------------------------------------------------------ ملفات التفصيل ----
def detail_profile(name, mobile=False):
    if name not in PROFILES:
        return {"valid": False, "profile": None,
                "issues": [issue("AD_INVALID_PROFILE", "ERROR", name,
                                 "detail profile is not declared")]}
    issues = []
    eff = name
    if mobile and name in SPEC["mobile_detail_fallback"]:
        eff = SPEC["mobile_detail_fallback"][name]
        issues.append(issue("AD_MOBILE_FALLBACK_APPLIED", "INFO", name,
                            "constrained device: %s -> %s" % (name, eff)))
    p = dict(PROFILES[eff])
    p["requested"] = name
    p["effective"] = eff
    p["canonical_objects_removed"] = False
    p["blank_viewport_allowed"] = False
    return {"valid": True, "profile": p, "issues": issues}


def classify_detail(kind):
    return kind if kind in DETAIL_CLASSES else "UNRESOLVED"


def object_authority(obj, context_enabled=False):
    """تصنيف سلطة الكائن (14B) — لا اختلاق عند الغموض."""
    o = obj if isinstance(obj, dict) else {}
    if o.get("canonical") is True:
        return "CANONICAL_OBJECT"
    if o.get("requested") is True:
        return "USER_REQUESTED_OBJECT"
    if context_enabled and o.get("context") is True:
        return "PRESENTATION_CONTEXT_OBJECT"
    return "UNRESOLVED_OBJECT"


# ------------------------------------------------------ تقسيم الواجهة ----
def facade_zoning(surfaces, request):
    """تقسيم خامات الواجهة على أسطح ممثَّلة فعلاً — لا اختراع جدران (§5)."""
    req = request if isinstance(request, dict) else {}
    primary = req.get("primary")
    accent = req.get("accent")
    issues = []
    assigns = []
    if primary is not None and primary not in SPEC["facade_zone_materials"]:
        return {"valid": False, "zones": None,
                "issues": [issue("AD_INVALID_MATERIAL", "ERROR", primary,
                                 "facade zone material is not declared")]}
    if accent is not None and accent not in SPEC["facade_zone_materials"]:
        return {"valid": False, "zones": None,
                "issues": [issue("AD_INVALID_MATERIAL", "ERROR", accent,
                                 "facade zone material is not declared")]}
    prim_surfaces = [s for s in (surfaces or [])
                     if isinstance(s, dict)
                     and s.get("role") == "exterior_wall"]
    accent_surfaces = [s for s in (surfaces or [])
                       if isinstance(s, dict)
                       and s.get("role") in ("parapet", "base_course",
                                             "accent_band")]
    if primary:
        for s in prim_surfaces:
            assigns.append({
                "surface_id": s.get("id"), "material": primary,
                "detail_class": "REQUESTED_PRESENTATION_DETAIL",
                "flags": _flags(s.get("id"), "USER_VISUAL_OVERRIDE", "HIGH",
                                "requested facade appearance")})
        if not prim_surfaces:
            issues.append(issue("AD_VISUAL_DETAIL_UNRESOLVED", "WARNING",
                                primary,
                                "no represented exterior wall surface"))
    if accent:
        if accent_surfaces:
            for s in accent_surfaces:
                assigns.append({
                    "surface_id": s.get("id"), "material": accent,
                    "detail_class": "REQUESTED_PRESENTATION_DETAIL",
                    "flags": _flags(s.get("id"), "USER_VISUAL_OVERRIDE",
                                    "MEDIUM",
                                    "requested accent on represented band")})
        else:
            issues.append(issue("AD_VISUAL_DETAIL_UNRESOLVED", "WARNING",
                                accent,
                                "no safe accent zone can be derived; "
                                "not fabricated"))
    return {"valid": True, "issues": issues,
            "zones": {"assignments": assigns,
                      "invented_walls": False,
                      "wall_thickness_changed": False,
                      "accent_resolved": bool(accent and accent_surfaces)}}


# --------------------------------------------------- تجميعة النافذة ----
def window_assembly(opening, finish=None):
    """إطار + زجاج + جلسة من فتحة ممثَّلة — الفتحة نفسها لا تُمسّ (§7)."""
    o = opening if isinstance(opening, dict) else {}
    w = _num(o.get("width"))
    h = _num(o.get("height"))
    if w is None or h is None or w <= 0 or h <= 0:
        return {"valid": False, "assembly": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", "window",
                                 "opening width/height missing")]}
    wa = SPEC["window_assembly"]
    fin = finish or wa["default_frame_finish"]
    if fin not in wa["frame_finishes"]:
        return {"valid": False, "assembly": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", fin,
                                 "frame finish is not declared")]}
    t = min(max(min(w, h) * wa["frame_thickness_ratio"],
                wa["frame_thickness_min_m"]), wa["frame_thickness_max_m"])
    return {"valid": True, "issues": [], "assembly": {
        "opening": {"width": _q(w), "height": _q(h),
                    "sill": _q(_num(o.get("sill")) or 0.0)},
        "opening_size_changed": False, "opening_position_changed": False,
        "window_count_changed": False,
        "detail_class": "DERIVED_PRESENTATION_DETAIL",
        "frame": {"material": wa["frame_material"],
                  "finish": fin, "color": wa["frame_finishes"][fin],
                  "thickness_m": _q(t), "depth_m": wa["frame_depth_m"],
                  "parts": ["top", "bottom", "left", "right"]},
        "glass": {"material": "glass_clear", "three_material": "physical"},
        "sill": {"depth_m": wa["sill_depth_m"], "drop_m": wa["sill_drop_m"]},
        "flags": _flags(o.get("id"), "PRESENTATION_DEFAULT", "HIGH",
                        "frame derived from the represented opening")}}


def door_visual(door):
    """صنف باب عرضي من نوع ممثَّل فقط — لا استدلال مقاومة حريق أو أمن (§8)."""
    d = door if isinstance(door, dict) else {}
    ev = d.get("material") or d.get("kind") or "door"
    cls = SPEC["door_class_evidence_map"].get(ev, "generic")
    if d.get("entrance") is True:
        cls = "entrance_door"
    spec = SPEC["door_visual_classes"][cls]
    return {"valid": True, "issues": [], "door": {
        "visual_class": cls, "material": spec["material"],
        "glass": bool(spec.get("glass")),
        "fire_rating_inferred": False, "security_rating_inferred": False,
        "engineering_material_truth": False,
        "detail_class": "DERIVED_PRESENTATION_DETAIL",
        "flags": _flags(d.get("id"), "PRESENTATION_DEFAULT",
                        "HIGH" if cls != "generic" else "LOW",
                        "visual class mapped from represented evidence")}}


def balcony_visual(represented, requested):
    """بلكونة: تحسين الممثَّل فقط؛ الطلب بلا تمثيل يُصنَّف ولا يُختلق (§9)."""
    if represented:
        return {"status": "ENHANCED" if requested
                else "CANONICAL_GEOMETRY_PRESENT",
                "engineering_geometry_created": False, "issues": [],
                "enhancements": SPEC["balcony_rules"]["enhancements"]}
    if requested:
        return {"status": "REQUESTED_BUT_NOT_REPRESENTED",
                "engineering_geometry_created": False,
                "ui_note_en": SPEC["balcony_rules"]["ui_note_en"],
                "ui_note_ar": SPEC["balcony_rules"]["ui_note_ar"],
                "issues": [issue("AD_BALCONY_NOT_REPRESENTED", "WARNING",
                                 "balcony", "requested but not represented "
                                 "in canonical geometry")]}
    return {"status": "NOT_REQUESTED",
            "engineering_geometry_created": False, "issues": []}


def led(kind, host):
    """إنارة معمارية عرضية فقط — لا دائرة، لا حمل، لا جدول MEP (§11)."""
    L = SPEC["led_lighting"]
    if kind not in L["types"]:
        return {"valid": False, "light": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", kind,
                                 "led type is not declared")]}
    h = host if isinstance(host, dict) else {}
    if not h.get("represented"):
        return {"valid": False, "light": None,
                "issues": [issue("AD_HOST_NOT_REPRESENTED", "WARNING", kind,
                                 "no represented host edge for this light")]}
    return {"valid": True, "issues": [], "light": {
        "type": kind, "visual_only": True, "mep_fixture_reused": False,
        "creates_electrical_circuit": False, "creates_load": False,
        "creates_panel_assignment": False, "creates_cable_route": False,
        "creates_mep_schedule_entry": False,
        "emissive_intensity": L["emissive_intensity"],
        "strip_height_m": L["strip_height_m"],
        "strip_depth_m": L["strip_depth_m"],
        "material": "led_strip",
        "detail_class": "REQUESTED_PRESENTATION_DETAIL",
        "flags": _flags(h.get("id"), "USER_VISUAL_OVERRIDE", "HIGH",
                        "visual-only architectural light on a represented "
                        "host")}}


# ------------------------------------------------------ التأثيث العرضي ----
def staging_plan(mode, requested_objects, canonical_objects):
    """خطة التأثيث: التحسين للممثَّل والمطلوب؛ الإضافة الافتراضية لا تكون
    إلا باختيار صريح، وتبقى عرضية بحتة (§13)."""
    if mode not in STAGING:
        return {"valid": False, "plan": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", mode,
                                 "staging mode is not declared")]}
    req = [o for o in (requested_objects or []) if isinstance(o, dict)]
    can = [o for o in (canonical_objects or []) if isinstance(o, dict)]
    improve = ([{"kind": o.get("kind"), "id": o.get("id"),
                 "authority": "CANONICAL_OBJECT"} for o in can]
               + ([{"kind": o.get("kind"), "id": o.get("id"),
                    "authority": "USER_REQUESTED_OBJECT"} for o in req]
                  if mode != "STAGING_OFF" else []))
    additions = []
    if mode == "STAGING_PRESENTATION_DEFAULT":
        additions = [{"kind": k, "authority": "PRESENTATION_CONTEXT_OBJECT",
                      "flags": _flags(None, "PRESENTATION_DEFAULT", "LOW",
                                      "presentation staging default",
                                      context=True),
                      "enters_bim": False, "enters_quantities": False,
                      "enters_engineering_exports": False,
                      "enters_documentation_schedules": False}
                     for k in ("sofa", "dining_table", "bed")]
    return {"valid": True, "issues": [], "plan": {
        "mode": mode, "improve": improve, "additions": additions,
        "silent_population": False,
        "canonical_object_count_changed": False}}


def _category(kind):
    for cat, kinds in sorted(LIBRARY.items()):
        if kind in kinds:
            return cat
    return None


def _expand(parts):
    out = []
    for p in parts:
        if ":" in p:
            name, n = p.split(":")
            out += [name] * int(n)
        else:
            out.append(p)
    return out


def object_recipe(kind, dims=None, canonical_dims=None, variant=None):
    """وصفة كائن عرضي حتمية بمصدر مقياس صريح (14C/14D/14E/14H)."""
    issues = []
    cat = _category(kind)
    if cat is None:
        return {"valid": False, "recipe": None,
                "issues": [issue("AD_INVALID_OBJECT_KIND", "ERROR", kind,
                                 "object kind is not in the presentation "
                                 "library")]}
    if cat == "vehicles" and kind == "emergency_vehicle" \
            and SPEC["emergency_vehicle_requires_explicit_request"]:
        pass  # يُتحقّق من الطلب الصريح في سلطة الكائن، لا هنا
    if kind == "forklift" or kind in ("reach_truck", "pallet_jack",
                                      "order_picker", "stacker"):
        vmap = {"forklift": "COUNTERBALANCE_FORKLIFT",
                "reach_truck": "REACH_TRUCK", "pallet_jack": "PALLET_JACK",
                "order_picker": "ORDER_PICKER", "stacker": "STACKER"}
        v = variant or vmap.get(kind)
        if v not in RECIPES_FORKLIFT:
            v = "GENERIC_FORKLIFT_PRESENTATION"
        r = RECIPES_FORKLIFT[v]
        parts, default = _expand(r["parts"]), r["dims_m"]
        recipe_id = v
    elif kind in RECIPES_VEHICLE:
        r = RECIPES_VEHICLE[kind]
        parts, default = _expand(r["parts"]), r["dims_m"]
        recipe_id = kind
    elif kind in RECIPES_LANDSCAPE:
        r = RECIPES_LANDSCAPE[kind]
        parts, default = _expand(r["parts"]), [2.4, 2.4, 4.5]
        recipe_id = kind
    elif kind in RECIPES_FURNITURE:
        parts, default = _expand(RECIPES_FURNITURE[kind]), [1.0, 1.0, 1.0]
        recipe_id = kind
    else:
        parts, default = ["box"], [0.8, 0.8, 0.8]
        recipe_id = "generic_" + kind
    def _dims_ok(v):
        return (isinstance(v, (list, tuple)) and len(v) == 3
                and all(_num(x) is not None and _num(x) > 0 for x in v))
    if _dims_ok(canonical_dims):
        use, source = [_q(_num(x)) for x in canonical_dims], "CANONICAL"
    elif _dims_ok(dims):
        use, source = [_q(_num(x)) for x in dims], "USER"
    else:
        use, source = [_q(x) for x in default], "PRESENTATION_DEFAULT"
        issues.append(issue("AD_PRESENTATION_DEFAULT_DIMENSIONS", "INFO",
                            kind, "default dimensions are a presentation "
                            "fallback, not engineering measurements"))
    forbidden = {}
    if cat == "vehicles":
        forbidden = {k: False for k in SPEC["vehicle_invention_forbidden"]}
    if recipe_id in RECIPES_FORKLIFT:
        forbidden = {k: False
                     for k in SPEC["forklift_inference_forbidden"]}
    return {"valid": True, "issues": issues, "recipe": {
        "kind": kind, "category": cat, "recipe_id": recipe_id,
        "parts": parts, "dims_m": use, "dims_source": source,
        "invented_attributes": forbidden,
        "instanced": kind in SPEC["instancing"]["instanced_classes"],
        "visual_only": True}}


def placement(obj):
    """أولوية الموضع (14H): قانوني → صريح من المستخدم → منطقة مطلوبة →
    غير محسوم. لا وضع تلقائي لمجرد وجود الفراغ."""
    o = obj if isinstance(obj, dict) else {}
    if isinstance(o.get("canonical_pos"), (list, tuple)) \
            and len(o["canonical_pos"]) >= 2:
        return {"resolved": True, "source": "CANONICAL",
                "position": [_q(_num(v) or 0.0)
                             for v in o["canonical_pos"][:3]], "issues": []}
    if isinstance(o.get("user_pos"), (list, tuple)) \
            and len(o["user_pos"]) >= 2:
        return {"resolved": True, "source": "USER",
                "position": [_q(_num(v) or 0.0)
                             for v in o["user_pos"][:3]], "issues": []}
    z = o.get("zone")
    if isinstance(z, dict) and all(_num(z.get(k)) is not None
                                   for k in ("x", "z", "w", "d")):
        zx, zz = _num(z.get("x")), _num(z.get("z"))
        zw, zd = _num(z.get("w")), _num(z.get("d"))
        i = int(_num(o.get("index")) or 0)
        n = max(1, int(_num(o.get("of")) or 1))
        return {"resolved": True, "source": "ZONE_DETERMINISTIC",
                "position": [_q(zx + zw * (i + 0.5) / n),
                             0.0, _q(zz + zd * 0.5)], "issues": []}
    return {"resolved": False, "source": "UNRESOLVED", "position": None,
            "issues": [issue("AD_PLACEMENT_UNRESOLVED", "WARNING",
                             o.get("kind"), "no safe placement can be "
                             "derived; not fabricated")]}


def vehicles_to_bays(count_requested, bays):
    """«ضع 10 سيارات في المواقف»: سيارة لكل موقف ممثَّل صالح فقط (14I)."""
    n = max(0, int(_num(count_requested) or 0))
    valid = [b for b in (bays or []) if isinstance(b, dict)
             and b.get("id") is not None]
    placed = [{"bay_id": valid[i]["id"], "kind": "car",
               "authority": "USER_REQUESTED_OBJECT",
               "status": "APPLIED_TO_CANONICAL_PARKING"}
              for i in range(min(n, len(valid)))]
    issues = []
    if n > len(valid):
        issues.append(issue("AD_PARKING_NOT_RESOLVED", "WARNING", "cars",
                            "%d requested, %d represented bays"
                            % (n, len(valid))))
    return {"placed": placed, "requested": n,
            "represented_bays": len(valid),
            "unplaced": max(0, n - len(valid)), "issues": issues}


def parking(requested, bays_count):
    b = max(0, int(_num(bays_count) or 0))
    if b > 0:
        return {"status": "APPLIED_TO_CANONICAL_PARKING" if requested
                else "CANONICAL_GEOMETRY_PRESENT",
                "bays": b, "invented_count": False, "issues": []}
    if requested:
        return {"status": "REQUESTED_NOT_GEOMETRICALLY_RESOLVED", "bays": 0,
                "invented_count": False,
                "issues": [issue("AD_PARKING_NOT_RESOLVED", "WARNING",
                                 "parking", "requested but no represented "
                                 "bays")]}
    return {"status": "NOT_REQUESTED", "bays": 0, "invented_count": False,
            "issues": []}


def kitchen_layout(requested_text, canonical_layout):
    """المطبخ: لا اختيار تخطيط هندسي من عبارة غامضة (§15)."""
    if canonical_layout in SPEC["kitchen_layouts"]:
        return {"layout": canonical_layout, "source": "CANONICAL",
                "issues": []}
    if requested_text:
        return {"layout": None, "source": "UNRESOLVED",
                "issues": [issue("AD_KITCHEN_LAYOUT_UNRESOLVED", "WARNING",
                                 "kitchen", "ambiguous request; no "
                                 "canonical layout selected")]}
    return {"layout": None, "source": "NOT_REQUESTED", "issues": []}


# ------------------------------------------------------ البيئة والكاميرا --
def environment(preset):
    if preset not in ENVIRONMENTS:
        return {"valid": False, "environment": None,
                "issues": [issue("AD_INVALID_ENVIRONMENT", "ERROR", preset,
                                 "environment preset is not declared")]}
    e = ENVIRONMENTS[preset]
    base = P.environment(e["base_mode"])
    if not base["valid"]:
        return base
    env = dict(base["environment"])
    env["arch_preset"] = preset
    env["sun_tint"] = e["sun_tint"]
    env["runtime_cdn"] = False
    env["remote_hdri"] = False
    return {"valid": True, "environment": env, "issues": []}


def camera(preset, bounds):
    """سجل الكاميرا الموسَّع: إعدادات 9.2 بنفس محلّ 9.1 نفسه — لا سجل ثانٍ."""
    if preset in P.CAMERAS:
        return P.camera(preset, bounds)
    if preset not in CAMERAS_ARCH:
        return {"valid": False, "camera": None,
                "issues": [issue("AD_INVALID_CAMERA", "ERROR", preset,
                                 "camera preset is not declared")]}
    p = CAMERAS_ARCH[preset]
    b = bounds if isinstance(bounds, dict) else {}
    cx = _num(b.get("cx")) or 0.0
    cy = _num(b.get("cy")) or 0.0
    cz = _num(b.get("cz")) or 0.0
    r = _num(b.get("radius"))
    if r is None or r <= 0:
        r = 20.0
    fov = min(max(float(p["fov"]), float(P.SPEC["fov_min"])),
              float(P.SPEC["fov_max"]))
    az = math.radians(float(p["azimuth_deg"]))
    el = math.radians(float(p["elevation_deg"]))
    d = r * float(p["distance_factor"])
    px = cx + d * math.cos(el) * math.sin(az)
    pz = cz + d * math.cos(el) * math.cos(az)
    py = cy + d * math.sin(el)
    ty = cy
    if p.get("target") == "EYE" and p.get("eye_height_m") is not None:
        base_y = _num(b.get("min_y")) or 0.0
        py = base_y + float(p["eye_height_m"])
        ty = base_y + float(p["eye_height_m"])
    return {"valid": True, "issues": [], "camera": {
        "preset": preset, "fov": _q(fov),
        "position": [_q(px), _q(py), _q(pz)],
        "target": [_q(cx), _q(ty), _q(cz)],
        "bounds_radius_m": _q(r), "deterministic": True,
        "fisheye": False}}


def auto_presentation(meta):
    """الوضع التلقائي: إعدادات عرض فقط — لا يلمس الهندسة أبداً (§32)."""
    m = meta if isinstance(meta, dict) else {}
    table = SPEC["auto_presentation"]
    if m.get("indoor") is True:
        pick = table["interior_mode"]
    else:
        t = m.get("type") if m.get("type") in table["by_building_type"] \
            else "generic"
        pick = table["by_building_type"][t]
    q = P.auto_profile(m.get("caps"))
    return {"valid": True, "issues": [], "auto": {
        "camera_preset": pick["camera"], "lighting_preset": pick["lighting"],
        "environment": pick["environment"], "detail_profile": pick["detail"],
        "quality_profile": q["profile"],
        "ultra_auto_selected": False,
        "materials_mode": "REALISTIC",
        "engineering_geometry_changed": False}}


# --------------------------------------------------- تفسير الطلبات ----
def interpret(text):
    """استخلاص نيّة العرض من نص المستخدم وتصنيفها — الوصف ليس إذناً
    بتعديل الهندسة (§33)."""
    s = (text or "")
    low = s.lower()
    found = []
    seen = set()
    for entry in KEYMAP:
        keys = list(entry["keys_ar"]) + list(entry["keys_en"])
        hit = None
        for k in sorted(keys, key=len, reverse=True):
            if k.lower() in low:
                hit = k
                break
        if hit is None:
            continue
        if entry["intent"] in seen:
            continue
        seen.add(entry["intent"])
        found.append({"intent": entry["intent"], "value": entry["value"],
                      "classification": entry["class"], "matched": hit})
    return {"text_len": len(s), "intents": found,
            "engineering_permission_granted": False}


# ------------------------------------------------------ التشخيص ----
def diagnostic(requests, model_summary):
    """تقرير الأمانة البصرية (§34، 14J): كل طلب يُحاسَب، لا إسقاط صامت."""
    ms = model_summary if isinstance(model_summary, dict) else {}
    feats = []
    issues = []
    objs = {"requested_objects": [], "canonical_objects": [],
            "presentation_objects": [], "unresolved_objects": [],
            "presentation_default_objects": []}
    for r in (requests or []):
        it = r.get("intent")
        cls = r.get("classification")
        if cls == "REQUIRES_ENGINEERING_CHANGE":
            feats.append({"feature": it,
                          "status": "REQUIRES_ENGINEERING_CHANGE"})
            issues.append(issue("AD_REQUIRES_ENGINEERING_CHANGE", "WARNING",
                                it, "outside the presentation authority"))
            continue
        if cls == "UNSUPPORTED":
            feats.append({"feature": it, "status": "UNRESOLVED"})
            issues.append(issue("AD_REQUEST_UNSUPPORTED", "WARNING", it,
                                "not supported by the presentation layer"))
            continue
        if it == "facade_material":
            ok = bool(ms.get("exterior_walls"))
            feats.append({"feature": it,
                          "status": "APPLIED" if ok else "UNRESOLVED"})
        elif it == "facade_accent":
            ok = bool(ms.get("accent_band"))
            feats.append({"feature": it,
                          "status": "APPLIED" if ok else "UNRESOLVED"})
            if not ok:
                issues.append(issue("AD_VISUAL_DETAIL_UNRESOLVED",
                                    "WARNING", it,
                                    "no safe accent zone"))
        elif it == "glass_appearance":
            ok = bool(ms.get("windows"))
            feats.append({"feature": it,
                          "status": "APPLIED" if ok else "UNRESOLVED"})
        elif it == "led_lighting":
            ok = bool(ms.get("exterior_walls") or ms.get("balcony"))
            feats.append({"feature": it, "status": "VISUAL_ONLY_APPLIED"
                          if ok else "UNRESOLVED"})
        elif it == "balcony_presence":
            b = balcony_visual(bool(ms.get("balcony")), True)
            feats.append({"feature": it, "status": b["status"]})
            issues += b["issues"]
        elif it == "parking":
            pk = parking(True, ms.get("parking_bays"))
            feats.append({"feature": it, "status": pk["status"]})
            issues += pk["issues"]
        elif it == "landscape":
            feats.append({"feature": it, "status": "PRESENTATION_CONTEXT"})
        elif it == "kitchen_layout":
            k = kitchen_layout(True, ms.get("kitchen_layout"))
            feats.append({"feature": it,
                          "status": "APPLIED" if k["layout"]
                          else "UNRESOLVED"})
            issues += k["issues"]
        else:
            feats.append({"feature": it, "status": "UNRESOLVED"})
            issues.append(issue("AD_REQUEST_UNSUPPORTED", "WARNING", it,
                                "unhandled intent"))
    for o in (ms.get("objects") or []):
        a = object_authority(o, bool(ms.get("context_enabled")))
        rec = {"kind": o.get("kind"), "count": o.get("count") or 1,
               "authority": a}
        if a == "CANONICAL_OBJECT":
            objs["canonical_objects"].append(rec)
        elif a == "USER_REQUESTED_OBJECT":
            objs["requested_objects"].append(rec)
        elif a == "PRESENTATION_CONTEXT_OBJECT":
            objs["presentation_objects"].append(rec)
        else:
            objs["unresolved_objects"].append(rec)
            issues.append(issue("AD_OBJECT_UNRESOLVED", "WARNING",
                                o.get("kind"),
                                "object authority cannot be resolved"))
    d = {"requested_visual_features": [f["feature"] for f in feats],
         "features": feats,
         "represented_visual_features":
             [f["feature"] for f in feats
              if f["status"] in ("APPLIED", "ENHANCED",
                                 "CANONICAL_GEOMETRY_PRESENT",
                                 "VISUAL_ONLY_APPLIED",
                                 "APPLIED_TO_CANONICAL_PARKING")],
         "unresolved_visual_features":
             [f["feature"] for f in feats
              if f["status"] in ("UNRESOLVED",
                                 "REQUESTED_NOT_GEOMETRICALLY_RESOLVED",
                                 "REQUESTED_BUT_NOT_REPRESENTED")],
         "engineering_change_required":
             [f["feature"] for f in feats
              if f["status"] == "REQUIRES_ENGINEERING_CHANGE"],
         "presentation_defaults_used":
             [f["feature"] for f in feats
              if f["status"] == "PRESENTATION_CONTEXT"],
         "silently_dropped": []}
    d.update(objs)
    return {"valid": True, "diagnostic": d, "issues": issues}


def coverage(diag):
    """VISUAL_REQUEST_COVERAGE — لا معنى امتثالياً ولا اكتمالاً هندسياً."""
    d = (diag or {}).get("diagnostic") or {}
    req = len(d.get("requested_visual_features") or [])
    rep = len(d.get("represented_visual_features") or [])
    unr = len(d.get("unresolved_visual_features") or [])
    eng = len(d.get("engineering_change_required") or [])
    return {"name": "VISUAL_REQUEST_COVERAGE",
            "requested": req, "represented": rep, "unresolved": unr,
            "requires_engineering_change": eng,
            "coverage_ratio": _q(rep / req) if req else None,
            "is_engineering_completeness": False,
            "has_compliance_meaning": False}


# ------------------------------------------------------ الإعداد الكامل ----
def config(detail=None, facade_mode=None, context_mode=None,
           staging_mode=None, camera_preset=None, environment_preset=None,
           caps=None, mobile=False, requests=None, model_summary=None):
    """إعداد العرض المعماري الكامل + بصمته المستقلة عن النموذج والزمن."""
    issues = []
    dp = detail_profile(detail or SPEC["default_detail_profile"], mobile)
    if not dp["valid"]:
        return {"valid": False, "config": None, "issues": dp["issues"]}
    issues += dp["issues"]
    fm = facade_mode or "ENGINEERING"
    if fm not in ("ENGINEERING", "REQUESTED", "REALISTIC"):
        return {"valid": False, "config": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", fm,
                                 "facade mode is not declared")]}
    cm = context_mode or "NONE"
    if cm not in ("NONE", "NEUTRAL", "SITE", "LANDSCAPE"):
        return {"valid": False, "config": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", cm,
                                 "context mode is not declared")]}
    sm = staging_mode or SPEC["default_staging_mode"]
    if sm not in STAGING:
        return {"valid": False, "config": None,
                "issues": [issue("AD_INVALID_MODE", "ERROR", sm,
                                 "staging mode is not declared")]}
    ev = environment(environment_preset or "NEUTRAL_STUDIO")
    if not ev["valid"]:
        return {"valid": False, "config": None, "issues": ev["issues"]}
    cam = camera_preset or "EXTERIOR_HERO_CORNER"
    if cam not in P.CAMERAS and cam not in CAMERAS_ARCH:
        return {"valid": False, "config": None,
                "issues": [issue("AD_INVALID_CAMERA", "ERROR", cam,
                                 "camera preset is not declared")]}
    diag = diagnostic(requests or [], model_summary or {})
    issues += diag["issues"]
    cov = coverage(diag)
    cfg = {"schema": SCHEMA, "version": VERSION,
           "presentation_layer_version": SPEC["presentation_layer_version"],
           "detail": dp["profile"], "facade_mode": fm,
           "context_mode": cm, "staging_mode": sm,
           "camera_preset": cam,
           "environment": ev["environment"],
           "diagnostic": diag["diagnostic"],
           "visual_request_coverage": cov,
           "writes_to_model": False, "visual_only": True,
           "canonical_object_count_changed": False}
    cfg["presentation_config_hash"] = _sha16(cfg)
    return {"valid": True, "config": cfg, "issues": issues}


def capture_metadata(pbr_cfg, ad_cfg, model_hash, revision, width_px,
                     height_px, generated_at=None):
    """امتداد بيانات اللقطة (§38) — تبقى مخرجات عرض لا دليلاً هندسياً."""
    base = P.capture_metadata(pbr_cfg, model_hash, width_px, height_px,
                              generated_at)
    if not base["valid"]:
        return base
    md = dict(base["metadata"])
    a = (ad_cfg or {})
    md["revision"] = revision
    md["presentation_layer_version"] = SPEC["presentation_layer_version"]
    md["architectural_detail_level"] = ((a.get("detail") or {})
                                        .get("effective"))
    md["context_mode"] = a.get("context_mode")
    md["staging_mode"] = a.get("staging_mode")
    md["visual_request_coverage"] = a.get("visual_request_coverage")
    md["is_engineering_evidence"] = False
    return {"valid": True, "metadata": md, "issues": base["issues"]}
