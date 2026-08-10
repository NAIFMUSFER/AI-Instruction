# -*- coding: utf-8 -*-
"""طبقة الجودة البصرية — المرحلة 9.1.

الطبقة الحتمية من ترقية العرض: حلّ خامات PBR العرضية بمصدر كل حقل، وحلّ
إعدادات الإضاءة والظلال والبيئة والكاميرا وملفّات الجودة مع سلسلة التراجع،
وبيانات لقطة العرض — كلّها دوالّ نقيّة على JSON تُقارَن حرفاً بحرف مع مرآة
المتصفّح. تطبيق الإعدادات على WebGL يعيش في جسر المتصفّح وحده.

القانون الحاكم: هذه الطبقة تغيّر كيف يبدو النموذج، لا ما هو النموذج. لا قيمة
هنا تدخل بصمة النموذج، ولا خامة عرضية تصير خاصّية هندسية.
"""
import json
import math
import os

import acs_ingest as ING

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_pbr.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
LIMITS = SPEC["limits"]
ISSUE_CODES = tuple(SPEC["issue_codes"])
BLOCKING = tuple(SPEC["blocking_issue_codes"])
MATERIALS = {m["id"]: m for m in SPEC["materials"]}
LIGHTING = SPEC["lighting_presets"]
QUALITY = SPEC["quality_profiles"]
REQUIREMENTS = SPEC["quality_requirements"]
CHAIN = SPEC["quality_fallback_chain"]
SHADOWS = SPEC["shadow_tiers"]
CAMERAS = SPEC["camera_presets"]
ENVIRONMENTS = SPEC["environment_modes"]
MAT_MAP = SPEC["engineering_material_map"]

_canon = ING.canonical_json


def _q(v):
    return round(float(v), 6) + 0.0


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _sha16(o):
    import hashlib
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def issue(code, severity, element_id, message):
    if code not in ISSUE_CODES:
        raise ValueError("undeclared pbr issue code: %s" % code)
    return {"code": code, "severity": severity, "element_id": element_id,
            "message": message, "blocking": code in BLOCKING}


def safe_key(k):
    import re
    if not isinstance(k, str) or not k or len(k) > 64:
        return False
    if k in SPEC["forbidden_property_keys"]:
        return False
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k) is not None


# ------------------------------------------------------------- الخامات ----
_OVERRIDABLE = ("base_color", "roughness", "metalness", "opacity",
                "transmission", "ior", "thickness_m", "emissive",
                "emissive_intensity", "normal_scale", "texture_scale_m")


def material(mid, override=None):
    """خامة عرضية محلولة، مع مصدر كل حقل. لا حقل يصير قيمة هندسية."""
    if mid not in MATERIALS:
        return {"valid": False, "material": None,
                "issues": [issue("PQ_INVALID_MATERIAL", "ERROR", mid,
                                 "presentation material is not declared")]}
    base = MATERIALS[mid]
    issues = []
    out = {}
    prov = {}
    for k in _OVERRIDABLE:
        out[k] = base.get(k)
        prov[k] = "PRESENTATION_DEFAULT"
    ov = override if isinstance(override, dict) else {}
    if len(ov) > int(LIMITS["max_override_fields"]):
        return {"valid": False, "material": None,
                "issues": [issue("PQ_INVALID_OVERRIDE", "ERROR", mid,
                                 "too many override fields")]}
    for k in sorted(ov):
        if not safe_key(k):
            issues.append(issue("PQ_PROPERTY_REFUSED", "WARNING", k,
                                "the override key is refused"))
            continue
        if k not in _OVERRIDABLE:
            issues.append(issue("PQ_INVALID_OVERRIDE", "WARNING", k,
                                "this field is not visually overridable"))
            continue
        v = ov[k]
        if k in ("base_color", "emissive"):
            if not (isinstance(v, str) and len(v) == 7 and v.startswith("#")
                    and all(c in "0123456789abcdefABCDEF" for c in v[1:])):
                issues.append(issue("PQ_INVALID_OVERRIDE", "WARNING", k,
                                    "not a hex colour"))
                continue
            out[k] = v.lower()
        else:
            n = _num(v)
            if n is None or n < 0 or n > 20:
                issues.append(issue("PQ_INVALID_OVERRIDE", "WARNING", k,
                                    "not a finite value in range"))
                continue
            out[k] = _q(n)
        prov[k] = "USER_VISUAL_OVERRIDE"
    resolved = dict(base)
    resolved.update(out)
    resolved["provenance"] = prov
    resolved["visual_only"] = True
    resolved["engineering_authority"] = False
    resolved["writes_to_model"] = False
    return {"valid": True, "material": resolved, "issues": issues}


def material_for_engineering(mesh_material_name):
    """الخامة العرضية المقابلة لاسم خامة هندسية في المشهد — أو لا شيء.

    غير المذكور يحتفظ بمظهره الهندسي: لا اختراع مظهر لما لم يُصنَّف.
    """
    mid = MAT_MAP.get(mesh_material_name)
    if mid is None:
        return {"mapped": False, "material_id": None,
                "policy": SPEC["unmapped_material_policy"]}
    return {"mapped": True, "material_id": mid,
            "policy": "MAPPED"}


# ------------------------------------------------------------- الإضاءة ----
def lighting(preset):
    if preset not in LIGHTING:
        return {"valid": False, "lighting": None,
                "issues": [issue("PQ_INVALID_PRESET", "ERROR", preset,
                                 "lighting preset is not declared")]}
    cfg = dict(LIGHTING[preset])
    cfg["preset"] = preset
    cfg["fills"] = [dict(f) for f in cfg.get("fills", [])][
        :int(LIMITS["max_fill_lights"])]
    for f in cfg["fills"]:
        f["visual_only"] = True
    cfg["mep_fixture_reused"] = False
    cfg["visual_only"] = True
    return {"valid": True, "lighting": cfg, "issues": []}


def exposure_clamp(v):
    n = _num(v)
    if n is None:
        return {"value": None, "clamped": False,
                "issues": [issue("PQ_INVALID_EXPOSURE", "ERROR", v,
                                 "exposure is not a finite number")]}
    lo, hi = float(SPEC["exposure_min"]), float(SPEC["exposure_max"])
    c = min(max(n, lo), hi)
    return {"value": _q(c), "clamped": c != n, "issues": []}


# ------------------------------------------------------------- الظلال ----
def shadow_config(tier, bounds):
    """إعداد الظلال من حدود النموذج الحقيقية — لا حجم مبنى مثبَّت."""
    if tier not in SHADOWS:
        return {"valid": False, "shadow": None,
                "issues": [issue("PQ_INVALID_PROFILE", "ERROR", tier,
                                 "shadow tier is not declared")]}
    t = SHADOWS[tier]
    b = bounds if isinstance(bounds, dict) else {}
    r = _num(b.get("radius"))
    if r is None or r <= 0:
        r = 25.0
    m = float(SPEC["shadow_camera_margin"])
    e = _q(r * m)
    return {"valid": True, "issues": [], "shadow": {
        "tier": tier, "map_size": int(t["map_size"]),
        "bias": t["bias"], "normal_bias": t["normal_bias"],
        "radius_px": t["radius"], "type": SPEC["shadow_type"],
        "camera": {"left": -e, "right": e, "top": e, "bottom": -e,
                   "near": 0.5, "far": _q(4.0 * e)},
        "bounds_radius_m": _q(r), "margin": m, "hardcoded_size": False}}


# ------------------------------------------------------------- الجودة ----
def capabilities_normalise(caps):
    c = caps if isinstance(caps, dict) else {}
    mt = _num(c.get("max_texture_size"))
    pr = _num(c.get("device_pixel_ratio"))
    return {"webgl2": bool(c.get("webgl2")),
            "max_texture_size": int(mt) if mt else 2048,
            "device_pixel_ratio": _q(min(pr if pr else 1.0,
                                         float(LIMITS["max_pixel_ratio"])))}


def _meets(profile, caps):
    req = REQUIREMENTS[profile]
    if req["webgl2"] and not caps["webgl2"]:
        return False
    return caps["max_texture_size"] >= int(req["min_max_texture_size"])


def quality(profile, caps=None):
    """ملفّ الجودة الفعلي بعد سلسلة التراجع المعلنة. التراجع يُبلَّغ لا يُخفى."""
    if profile not in QUALITY:
        return {"valid": False, "quality": None,
                "issues": [issue("PQ_INVALID_PROFILE", "ERROR", profile,
                                 "quality profile is not declared")]}
    c = capabilities_normalise(caps)
    issues = []
    chain = list(CHAIN)
    idx = chain.index(profile)
    effective = None
    for p in chain[idx:]:
        if _meets(p, c):
            effective = p
            break
        issues.append(issue("PQ_FALLBACK_APPLIED", "INFO", p,
                            "capability requirement not met; degrading"))
    if effective is None:
        effective = "PERFORMANCE"
    cfg = dict(QUALITY[effective])
    cfg["requested"] = profile
    cfg["effective"] = effective
    cfg["degraded"] = effective != profile
    cfg["pixel_ratio"] = _q(min(c["device_pixel_ratio"],
                                float(cfg["pixel_ratio_max"])))
    cfg["auto_max_profile"] = SPEC["auto_max_profile"]
    cfg["blank_viewport_allowed"] = False
    return {"valid": True, "quality": cfg, "issues": issues}


def auto_profile(caps=None):
    """الاختيار التلقائي لا يتجاوز الحدّ المعلَن أبداً — ULTRA اختيار مستعمل."""
    c = capabilities_normalise(caps)
    cap = SPEC["auto_max_profile"]
    chain = list(CHAIN)
    for p in chain[chain.index(cap):]:
        if _meets(p, c):
            return {"profile": p, "auto": True, "ultra_auto_selected": False}
    return {"profile": "PERFORMANCE", "auto": True,
            "ultra_auto_selected": False}


# ------------------------------------------------------------ الكاميرا ----
def camera(preset, bounds):
    """كاميرا معمارية من حدود النموذج الحقيقية. FOV مقيَّد ولا تأطير عشوائي."""
    if preset not in CAMERAS:
        return {"valid": False, "camera": None,
                "issues": [issue("PQ_INVALID_PRESET", "ERROR", preset,
                                 "camera preset is not declared")]}
    p = CAMERAS[preset]
    b = bounds if isinstance(bounds, dict) else {}
    cx = _num(b.get("cx")) or 0.0
    cy = _num(b.get("cy")) or 0.0
    cz = _num(b.get("cz")) or 0.0
    r = _num(b.get("radius"))
    if r is None or r <= 0:
        r = 20.0
    fov = min(max(float(p["fov"]), float(SPEC["fov_min"])),
              float(SPEC["fov_max"]))
    az = math.radians(float(p["azimuth_deg"]))
    el = math.radians(float(p["elevation_deg"]))
    d = r * float(p["distance_factor"])
    eye_h = p.get("eye_height_m")
    px = cx + d * math.cos(el) * math.sin(az)
    pz = cz + d * math.cos(el) * math.cos(az)
    py = cy + d * math.sin(el)
    ty = cy
    if p.get("target") == "EYE" and eye_h is not None:
        base_y = _num(b.get("min_y")) or 0.0
        py = base_y + float(eye_h)
        ty = base_y + float(eye_h)
    return {"valid": True, "issues": [], "camera": {
        "preset": preset, "fov": _q(fov),
        "position": [_q(px), _q(py), _q(pz)],
        "target": [_q(cx), _q(ty), _q(cz)],
        "bounds_radius_m": _q(r), "deterministic": True,
        "fisheye": False}}


# ------------------------------------------------------------- البيئة ----
def environment(mode):
    if mode not in ENVIRONMENTS:
        return {"valid": False, "environment": None,
                "issues": [issue("PQ_INVALID_ENVIRONMENT", "ERROR", mode,
                                 "environment mode is not declared")]}
    e = dict(ENVIRONMENTS[mode])
    e["mode"] = mode
    e["remote_fetch"] = False
    e["changes_geometry"] = False
    return {"valid": True, "environment": e, "issues": []}


# ------------------------------------------------------------ المسارات ----
def texture_path_ok(path):
    """قائمة سماح لا قائمة حظر: جذر الأصول المحلي وحده، وضمن القائمة المعلنة."""
    import re
    pol = SPEC["texture_policy"]
    if not isinstance(path, str) or not path:
        return {"ok": False, "issues": [issue("PQ_UNSAFE_ASSET_PATH", "ERROR",
                                              path, "empty asset path")]}
    if len(path) > int(LIMITS["max_asset_path_length"]):
        return {"ok": False, "issues": [issue("PQ_UNSAFE_ASSET_PATH", "ERROR",
                                              path[:40], "asset path too long")]}
    if "://" in path or path.startswith("//"):
        return {"ok": False, "issues": [issue("PQ_REMOTE_ASSET_REFUSED", "ERROR",
                                              path[:40],
                                              "remote assets are refused")]}
    if re.match(pol["safe_asset_pattern"], path) is None:
        return {"ok": False, "issues": [issue("PQ_UNSAFE_ASSET_PATH", "ERROR",
                                              path[:40],
                                              "path is outside the allowed "
                                              "asset root")]}
    listed = any(path in (s.get("files") or []) for s in pol["local_texture_sets"])
    if not listed:
        return {"ok": False, "listed": False,
                "issues": [issue("PQ_UNSAFE_ASSET_PATH", "WARNING", path[:40],
                                 "path is shaped correctly but not in the "
                                 "declared texture set; procedural fallback "
                                 "is used instead")]}
    return {"ok": True, "listed": True, "issues": []}


# ---------------------------------------------------------- الإعداد الكلّي --
def config(profile=None, lighting_preset=None, materials_mode=None,
           environment_mode=None, exposure=None, overrides=None, caps=None,
           bounds=None):
    """الإعداد العرضي الكامل + بصمته المستقلّة عن النموذج والزمن."""
    issues = []
    q = quality(profile or "BALANCED", caps)
    if not q["valid"]:
        return {"valid": False, "config": None, "issues": q["issues"]}
    issues += q["issues"]
    lp = lighting_preset or "CLEAR_NOON"
    lg = lighting(lp)
    if not lg["valid"]:
        return {"valid": False, "config": None, "issues": lg["issues"]}
    mm = materials_mode or SPEC["default_materials_mode"]
    if mm not in SPEC["materials_modes"]:
        return {"valid": False, "config": None,
                "issues": [issue("PQ_INVALID_MODE", "ERROR", mm,
                                 "materials mode is not declared")]}
    em = environment_mode or q["quality"]["environment"]
    ev = environment(em)
    if not ev["valid"]:
        return {"valid": False, "config": None, "issues": ev["issues"]}
    ex = exposure_clamp(exposure if exposure is not None
                        else lg["lighting"]["exposure"])
    if ex["value"] is None:
        return {"valid": False, "config": None, "issues": ex["issues"]}
    sh = shadow_config(q["quality"]["shadow_tier"], bounds)
    issues += sh["issues"]
    ov_out = {}
    for mid in sorted((overrides or {})):
        if mid not in MATERIALS:
            issues.append(issue("PQ_INVALID_MATERIAL", "WARNING", mid,
                                "override for an undeclared material"))
            continue
        r = material(mid, (overrides or {})[mid])
        issues += r["issues"]
        if r["valid"]:
            ov_out[mid] = {k: r["material"][k] for k in _OVERRIDABLE}
            ov_out[mid]["provenance"] = r["material"]["provenance"]
    cfg = {"schema": SCHEMA, "version": VERSION,
           "quality": q["quality"], "lighting": lg["lighting"],
           "materials_mode": mm, "environment": ev["environment"],
           "exposure": ex["value"], "exposure_clamped": ex["clamped"],
           "shadow": sh["shadow"] if sh["valid"] else None,
           "material_overrides": ov_out,
           "tone_mapping": SPEC["tone_mapping"],
           "output_color_space": SPEC["output_color_space"],
           "ground_context_enabled": SPEC["ground_context"]["enabled_default"],
           "writes_to_model": False, "visual_only": True}
    cfg["presentation_config_hash"] = _sha16(cfg)
    return {"valid": True, "config": cfg, "issues": issues}


def capture_metadata(cfg, model_hash, width_px, height_px, generated_at=None):
    """بيانات لقطة العرض: ناتج عرض لا دليل هندسي، مربوط ببصمتين منفصلتين."""
    issues = []
    w, h = _num(width_px), _num(height_px)
    mx = float(SPEC["capture"]["max_dimension_px"])
    if w is None or h is None or w <= 0 or h <= 0 or w > mx or h > mx:
        return {"valid": False, "metadata": None,
                "issues": [issue("PQ_INVALID_RESOLUTION", "ERROR",
                                 [width_px, height_px],
                                 "capture resolution is out of range")]}
    c = cfg or {}
    md = {"type": SPEC["capture"]["type"],
          "camera_preset": c.get("camera_preset"),
          "quality_profile": (c.get("quality") or {}).get("effective"),
          "lighting_preset": (c.get("lighting") or {}).get("preset"),
          "materials_mode": c.get("materials_mode"),
          "environment": (c.get("environment") or {}).get("mode"),
          "exposure": c.get("exposure"),
          "model_hash": model_hash,
          "presentation_config_hash": c.get("presentation_config_hash"),
          "width_px": int(w), "height_px": int(h),
          "generated_at": generated_at,
          "is_engineering_evidence": False}
    return {"valid": True, "metadata": md, "issues": issues}


# ------------------------------------ حدود العرض والقصّ (علاج الشاشة السوداء) --
VB = SPEC["viewport_bounds"]
CLIP = SPEC["camera_clip"]
VIEWPORT_CONTRACT = SPEC["viewport_contract_version"]
VIEWPORT_CONTRACT_SYMBOLS = tuple(SPEC["viewport_contract_symbols"])


def bounds_member(desc):
    """هل يدخل هذا الكائن في حدود المشهد القانونية؟

    القاعدة: الهندسة القانونية وحدها. قبّة السماء والأرضية السياقية وحامل
    اللاعب وعلامات التصحيح وكل مجموعة عرضية تُستبعد صراحةً. إدخال قبّة
    السماء (مقياس 45000) يضخّم نصف القطر آلاف الأضعاف، فتُوضع كاميرا
    الإعدادات خارج القبّة وخلف مستوى القصّ البعيد — وهذه هي الشاشة السوداء.
    """
    d = desc if isinstance(desc, dict) else {}
    name = d.get("name")
    name = name if isinstance(name, str) else ""
    parents = [p for p in (d.get("parent_names") or []) if isinstance(p, str)]
    flags = d.get("user_data") if isinstance(d.get("user_data"), dict) else {}
    if not d.get("is_mesh"):
        return {"included": False, "reason": "NOT_A_MESH"}
    for f in VB["excluded_userdata_flags"]:
        if flags.get(f):
            return {"included": False, "reason": "PRESENTATION_FLAG:%s" % f}
    for n in [name] + parents:
        if n in VB["excluded_object_names"]:
            return {"included": False, "reason": "EXCLUDED_NAME:%s" % n}
        for pre in VB["excluded_name_prefixes"]:
            if n.startswith(pre):
                return {"included": False, "reason": "EXCLUDED_PREFIX:%s" % pre}
    root = VB["canonical_root_name"]
    sep = VB["canonical_tag_separator"]
    if root in parents or name == root:
        return {"included": True, "reason": "CANONICAL_ROOT"}
    if sep in name:
        return {"included": True, "reason": "CANONICAL_TAG"}
    if VB["require_canonical_membership"]:
        return {"included": False, "reason": "NOT_CANONICAL_GEOMETRY"}
    return {"included": True, "reason": "DEFAULT"}


def bounds_from_descriptors(objects):
    """حدود قانونية من أوصاف كائنات — تعيد None عند غياب أي هندسة قانونية."""
    mins = [None, None, None]
    maxs = [None, None, None]
    used = 0
    for o in (objects or []):
        if not bounds_member(o)["included"]:
            continue
        box = o.get("box") if isinstance(o, dict) else None
        if not (isinstance(box, dict)
                and all(isinstance(box.get(k), (list, tuple))
                        and len(box[k]) == 3 for k in ("min", "max"))):
            continue
        ok = True
        for i in range(3):
            a, b = _num(box["min"][i]), _num(box["max"][i])
            if a is None or b is None:
                ok = False
                break
        if not ok:
            continue
        for i in range(3):
            a, b = _num(box["min"][i]), _num(box["max"][i])
            mins[i] = a if mins[i] is None else min(mins[i], a)
            maxs[i] = b if maxs[i] is None else max(maxs[i], b)
        used += 1
    if not used:
        return {"valid": False, "bounds": None, "member_count": 0,
                "issues": [issue("PQ_BOUNDS_UNAVAILABLE", "WARNING", None,
                                 "no canonical geometry is present in the "
                                 "scene")]}
    size = [maxs[i] - mins[i] for i in range(3)]
    return {"valid": True, "member_count": used, "issues": [], "bounds": {
        "cx": _q((mins[0] + maxs[0]) / 2.0),
        "cy": _q((mins[1] + maxs[1]) / 2.0),
        "cz": _q((mins[2] + maxs[2]) / 2.0),
        "min_y": _q(mins[1]),
        "size": [_q(v) for v in size],
        "radius": _q(max(max(size) / 2.0, 0.5))}}


def camera_clip(bounds, position):
    """مستويا القصّ يحتويان النموذج دائماً، والمسافة تبقى داخل قبّة السماء."""
    b = bounds if isinstance(bounds, dict) else {}
    r = _num(b.get("radius"))
    if r is None or r <= 0:
        r = 20.0
    cx = _num(b.get("cx")) or 0.0
    cy = _num(b.get("cy")) or 0.0
    cz = _num(b.get("cz")) or 0.0
    p = position if isinstance(position, (list, tuple)) and len(position) == 3 \
        else [cx, cy + r, cz + r * 2.0]
    px, py, pz = [(_num(v) or 0.0) for v in p]
    dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2)
    issues = []
    sky_limit = float(CLIP["sky_dome_radius_m"]) \
        * float(CLIP["max_distance_ratio_of_sky"])
    clamped = False
    if dist > sky_limit:
        k = sky_limit / dist if dist > 0 else 0.0
        px, py, pz = (cx + (px - cx) * k, cy + (py - cy) * k,
                      cz + (pz - cz) * k)
        dist = sky_limit
        clamped = True
        issues.append(issue("PQ_CAMERA_CLAMPED", "INFO", None,
                            "camera distance clamped inside the sky dome"))
    near = max(float(CLIP["near_min"]),
               min(dist * float(CLIP["near_ratio_of_distance"]),
                   max(dist - r * 1.5, float(CLIP["near_min"]))))
    far = min(max((dist + r * float(CLIP["far_margin_factor"])),
                  float(CLIP["far_min"])), float(CLIP["far_max"]))
    return {"valid": True, "issues": issues, "clip": {
        "near": _q(near), "far": _q(far), "distance": _q(dist),
        "position": [_q(px), _q(py), _q(pz)],
        "clamped": clamped, "inside_sky_dome": dist <= sky_limit,
        "camera_inside_bounds": dist <= r,
        # النموذج مشمول إذا غطّى المستوى البعيد أقصاه، والقريب لم يقطع مقدّمته.
        # الكاميرا داخل الكرة (مشهد داخلي) ⇒ المقدّمة خلف القريب حتماً.
        "contains_model": bool(far > dist + r - 1e-9
                               and (dist <= r
                                    or near < dist - r + 1e-9))}}


def frustum_contains(cam, bounds):
    """هل يتقاطع صندوق النموذج مع هرم الرؤية فعلاً؟ حساب صريح لا ظنّ."""
    c = cam if isinstance(cam, dict) else {}
    b = bounds if isinstance(bounds, dict) else {}
    pos = c.get("position") or [0.0, 0.0, 0.0]
    tgt = c.get("target") or [0.0, 0.0, 0.0]
    fov = _num(c.get("fov")) or 50.0
    aspect = _num(c.get("aspect")) or 1.6
    near = _num(c.get("near"))
    far = _num(c.get("far"))
    near = 0.05 if near is None else near
    far = 1000.0 if far is None else far
    cx = _num(b.get("cx")) or 0.0
    cy = _num(b.get("cy")) or 0.0
    cz = _num(b.get("cz")) or 0.0
    r = _num(b.get("radius"))
    if r is None or r <= 0:
        r = 1.0
    fx, fy, fz = tgt[0] - pos[0], tgt[1] - pos[1], tgt[2] - pos[2]
    flen = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / flen, fy / flen, fz / flen
    vx, vy, vz = cx - pos[0], cy - pos[1], cz - pos[2]
    depth = vx * fx + vy * fy + vz * fz
    dist = math.sqrt(vx * vx + vy * vy + vz * vz)
    # كاميرا داخل كرة النموذج (المشاهد الداخلية والمشي) تتقاطع معه حتماً
    inside_bounds = dist <= r
    facing = depth > 0 or inside_bounds
    half_v = math.radians(float(fov)) / 2.0
    half_h = math.atan(math.tan(half_v) * float(aspect))
    # مسافة مركز الكرة عن المحور البصري
    lat = math.sqrt(max(dist * dist - depth * depth, 0.0))
    in_near_far = (depth + r > near) and (depth - r < far)
    # نصف عرض الهرم عند هذا العمق + هامش نصف القطر
    limit_v = abs(depth) * math.tan(half_v) + r / max(math.cos(half_v), 1e-6)
    limit_h = abs(depth) * math.tan(half_h) + r / max(math.cos(half_h), 1e-6)
    in_cone = lat <= max(limit_v, limit_h)
    if inside_bounds:
        in_near_far = True
        in_cone = True
    inside = bool(facing and in_near_far and in_cone)
    return {"contains": inside, "facing": facing,
            "inside_bounds": bool(inside_bounds),
            "depth": _q(depth), "distance": _q(dist),
            "lateral": _q(lat), "near": _q(near), "far": _q(far),
            "within_clip": bool(in_near_far), "within_cone": bool(in_cone),
            "issues": [] if inside else
            [issue("PQ_MODEL_OUT_OF_FRUSTUM", "WARNING", None,
                   "the model bounding sphere does not intersect the view "
                   "frustum")]}


def material_safe(mat):
    """بوّابة الأمان: خامة عرضية غير صالحة تسقط مفتوحةً إلى خامة الهندسة،
    لا إلى جسم أسود أو غير مرئي (§7)."""
    m = mat if isinstance(mat, dict) else {}
    reasons = []
    col = m.get("base_color")
    if not (isinstance(col, str) and len(col) == 7 and col[0] == "#"
            and all(ch in "0123456789abcdefABCDEF" for ch in col[1:])):
        reasons.append("INVALID_COLOR")
    for k, lo, hi in (("roughness", 0.0, 1.0), ("metalness", 0.0, 1.0),
                      ("opacity", 0.0, 1.0), ("transmission", 0.0, 1.0)):
        if k not in m or m.get(k) is None:
            continue          # غير مضبوط = يبقى على قيمة المحرّك، وهذا آمن
        v = _num(m.get(k))
        if v is None or v < lo or v > hi:
            reasons.append("INVALID_%s" % k.upper())
    op = _num(m.get("opacity"))
    if m.get("opacity") is not None and op is not None and op <= 0.0:
        reasons.append("FULLY_TRANSPARENT")
    safe = not reasons
    return {"safe": safe, "reasons": reasons,
            "fallback": None if safe else "ENGINEERING_MATERIAL",
            "issues": [] if safe else
            [issue("PQ_MATERIAL_FAIL_OPEN", "WARNING", m.get("id"),
                   "presentation material refused (%s); keeping the "
                   "engineering material" % ",".join(reasons))]}


# ------------------------------ عقد التحويلات والمحاذاة (المرحلة 9.2) ------
TC = SPEC["transform_contract"]
SPACES = tuple(TC["spaces"])


def level_base_y(level_index, floor_height):
    """ارتفاع أرضية الدور — يُطبَّق مرّة واحدة فقط في حياة العنصر."""
    i = _num(level_index)
    fh = _num(floor_height)
    if i is None or fh is None or fh <= 0:
        return {"valid": False, "base_y": None,
                "issues": [issue("ALIGN_LEVEL_MISMATCH", "WARNING",
                                 str(level_index),
                                 "level index or floor height is not a "
                                 "finite positive number")]}
    return {"valid": True, "issues": [], "base_y": _q(i * fh),
            "space": "BUILDING", "applied_times": 1}


def resolve_transform(desc):
    """يحلّ موضع عنصر واحد إلى فضاء العالم بمصدر صريح لكل خطوة.

    لا تخمين: إذا نقص مضيف أو دور أو إزاحة، يُعاد UNRESOLVED_TRANSFORM
    ولا يُوضَع الجسم في نقطة الأصل صامتاً (§3/§17).
    """
    d = desc if isinstance(desc, dict) else {}
    issues = []
    space = d.get("coordinate_space")
    if space not in SPACES:
        return {"resolved": False, "world": None,
                "coordinate_space": space, "provenance": "UNRESOLVED",
                "issues": [issue("ALIGN_TRANSFORM_UNRESOLVED", "WARNING",
                                 d.get("source_element_id"),
                                 "undeclared coordinate space")]}
    local = d.get("local")
    if not (isinstance(local, (list, tuple)) and len(local) == 3
            and all(_num(v) is not None for v in local)):
        return {"resolved": False, "world": None,
                "coordinate_space": space, "provenance": "UNRESOLVED",
                "issues": [issue("ALIGN_TRANSFORM_UNRESOLVED", "WARNING",
                                 d.get("source_element_id"),
                                 "local transform is missing or not finite")]}
    lx, ly, lz = [_num(v) for v in local]
    host = d.get("host_origin")
    needs_host = space in ("HOST_LOCAL", "OBJECT_LOCAL")
    if needs_host:
        if not (isinstance(host, (list, tuple)) and len(host) == 3
                and all(_num(v) is not None for v in host)):
            return {"resolved": False, "world": None,
                    "coordinate_space": space, "provenance": "UNRESOLVED",
                    "issues": [issue("ALIGN_HOST_NOT_FOUND", "WARNING",
                                     d.get("source_element_id"),
                                     "a HOST_LOCAL transform without a "
                                     "resolvable host origin is never "
                                     "placed at the origin")]}
        hx, hy, hz = [_num(v) for v in host]
    else:
        hx = hy = hz = 0.0
    lev = d.get("level_index")
    fh = d.get("floor_height")
    base = 0.0
    if lev is not None:
        r = level_base_y(lev, fh)
        if not r["valid"]:
            return {"resolved": False, "world": None,
                    "coordinate_space": space, "provenance": "UNRESOLVED",
                    "issues": r["issues"]}
        base = r["base_y"]
    # الارتفاع يُضاف مرّة واحدة: إمّا من الدور أو لأن أصل المضيف يحمله أصلاً
    if d.get("host_origin_includes_level") and lev is not None:
        base = 0.0
        issues.append(issue("ALIGN_DOUBLE_TRANSFORM", "INFO",
                            d.get("source_element_id"),
                            "the host origin already carries the level "
                            "elevation; it was not added a second time"))
    world = [_q(hx + lx), _q(hy + ly + base), _q(hz + lz)]
    return {"resolved": True, "world": world, "issues": issues,
            "source_element_id": d.get("source_element_id"),
            "coordinate_space": space,
            "parent_space": TC["space_parents"].get(space),
            "local": [_q(lx), _q(ly), _q(lz)],
            "host_id": d.get("host_id"),
            "level_id": d.get("level_id"),
            "level_elevation": _q(base),
            "provenance": "CANONICAL" if not d.get("presentation")
            else "PRESENTATION_DERIVED",
            "level_applied_times": 0 if lev is None else 1,
            "host_applied_times": 1 if needs_host else 0}


def plate_rect(room_rects, site_rect):
    """امتداد لوح الدور: اتحاد بصمات غرف الدور نفسه، والموقع بديلٌ أخير.

    لوحٌ يمتدّ على الموقع كلّه فوق مبنى أصغر هو ما يجعل البلاطة العليا تبدو
    صفيحة طائرة منفصلة عن المبنى — وهذا اشتقاق من بيانات قانونية لا اختراع.
    """
    rects = [r for r in (room_rects or [])
             if isinstance(r, (list, tuple)) and len(r) == 4
             and all(_num(v) is not None for v in r)
             and _num(r[2]) > 0 and _num(r[3]) > 0]
    if not rects:
        s = site_rect if isinstance(site_rect, (list, tuple)) \
            and len(site_rect) == 4 else None
        if s is None or any(_num(v) is None for v in s):
            return {"valid": False, "rect": None, "source": "UNRESOLVED",
                    "issues": [issue("ALIGN_TRANSFORM_UNRESOLVED", "WARNING",
                                     "plate", "neither rooms nor a site "
                                     "rectangle are available")]}
        return {"valid": True, "rect": [_q(_num(v)) for v in s],
                "source": "SITE_FALLBACK", "issues": []}
    x0 = min(_num(r[0]) for r in rects)
    z0 = min(_num(r[1]) for r in rects)
    x1 = max(_num(r[0]) + _num(r[2]) for r in rects)
    z1 = max(_num(r[1]) + _num(r[3]) for r in rects)
    return {"valid": True, "issues": [], "source": "LEVEL_ROOM_UNION",
            "rect": [_q(x0), _q(z0), _q(x1 - x0), _q(z1 - z0)],
            "room_count": len(rects)}


def rack_block(room_rect, rack):
    """كتلة الرفوف داخل الغرفة — الامتداد المتاح = امتداد الغرفة ناقص الإزاحة.

    الخطأ المُصحَّح: أخذ امتداد الغرفة كاملاً بعد إزاحة موجبة، فيتجاوز الصفّ
    حدّ الغرفة بمقدار الإزاحة بالضبط (رفوف خارج غلاف المبنى).
    """
    rr = room_rect if isinstance(room_rect, (list, tuple)) \
        and len(room_rect) == 4 else None
    if rr is None or any(_num(v) is None for v in rr):
        return {"valid": False, "block": None,
                "issues": [issue("ALIGN_HOST_NOT_FOUND", "WARNING", "rack",
                                 "the hosting room rectangle is missing")]}
    R = rack if isinstance(rack, dict) else {}
    rx, rz, rw, rd = [_num(v) for v in rr]
    ox = _num(R.get("x")) or 0.0
    oz = _num(R.get("z")) or 0.0
    ox = min(max(ox, 0.0), rw)
    oz = min(max(oz, 0.0), rd)
    avail_w = max(rw - ox, 0.0)
    avail_d = max(rd - oz, 0.0)
    w = _num(R.get("w"))
    d = _num(R.get("d"))
    w = avail_w if w is None or w <= 0 else min(w, avail_w)
    d = avail_d if d is None or d <= 0 else min(d, avail_d)
    issues = []
    if avail_w <= 0 or avail_d <= 0:
        issues.append(issue("ALIGN_OBJECT_OUTSIDE_HOST", "WARNING", "rack",
                            "the declared rack offset leaves no room extent"))
    return {"valid": True, "issues": issues, "block": {
        "x": _q(rx + ox), "z": _q(rz + oz), "w": _q(w), "d": _q(d),
        "room_far_x": _q(rx + rw), "room_far_z": _q(rz + rd),
        "within_room": bool(rx + ox + w <= rx + rw + 1e-9
                            and rz + oz + d <= rz + rd + 1e-9),
        "offset_applied_times": 1}}


def containment(child_box, host_box, tolerance=None):
    """تصنيف احتواء صندوقين في فضاء العالم — بلا تحريك تلقائي لأي جسم."""
    tol = _num(tolerance)
    if tol is None:
        tol = float(TC["containment_tolerance_m"])

    def ok(b):
        return (isinstance(b, dict)
                and all(isinstance(b.get(k), (list, tuple)) and len(b[k]) == 3
                        and all(_num(v) is not None for v in b[k])
                        for k in ("min", "max")))
    if not (ok(child_box) and ok(host_box)):
        return {"classification": "UNRESOLVED", "overlap": None,
                "issues": [issue("ALIGN_TRANSFORM_UNRESOLVED", "WARNING",
                                 None, "a world-space box is missing")]}
    cmin = [_num(v) for v in child_box["min"]]
    cmax = [_num(v) for v in child_box["max"]]
    hmin = [_num(v) for v in host_box["min"]]
    hmax = [_num(v) for v in host_box["max"]]
    inside = all(cmin[i] >= hmin[i] - tol and cmax[i] <= hmax[i] + tol
                 for i in range(3))
    disjoint = any(cmin[i] > hmax[i] + tol or cmax[i] < hmin[i] - tol
                   for i in range(3))
    cls = "INSIDE" if inside else ("OUTSIDE" if disjoint
                                   else "INTERSECTING_BOUNDARY")
    out = [_q(max(0.0, min(cmax[i], hmax[i]) - max(cmin[i], hmin[i])))
           for i in range(3)]
    return {"classification": cls, "overlap": out, "tolerance": _q(tol),
            "moved_to_fit": False,
            "issues": [] if cls in ("INSIDE", "INTERSECTING_BOUNDARY")
            else [issue("ALIGN_OBJECT_OUTSIDE_HOST", "WARNING", None,
                        "the object lies outside its host; it is reported, "
                        "never snapped")]}


def roof_alignment(top_level_index, floor_height, roof_base_y,
                   tolerance=None):
    """خطأ ارتفاع السطح مقابل الارتفاع القانوني المتوقَّع — لا إنزال بصري."""
    tol = _num(tolerance)
    if tol is None:
        tol = float(TC["roof_tolerance_m"])
    exp = level_base_y((_num(top_level_index) or 0) + 1, floor_height)
    if not exp["valid"]:
        return {"aligned": False, "expected_y": None, "error_m": None,
                "issues": exp["issues"]}
    got = _num(roof_base_y)
    if got is None:
        return {"aligned": False, "expected_y": exp["base_y"],
                "error_m": None,
                "issues": [issue("ALIGN_TRANSFORM_UNRESOLVED", "WARNING",
                                 "roof", "the roof base elevation is not a "
                                 "finite number")]}
    err = abs(got - exp["base_y"])
    aligned = err <= tol
    return {"aligned": bool(aligned), "expected_y": exp["base_y"],
            "actual_y": _q(got), "error_m": _q(err), "tolerance": _q(tol),
            "presentation_offset_used": False,
            "issues": [] if aligned else
            [issue("ALIGN_ROOF_DETACHED", "WARNING", "roof",
                   "the roof sits %.3f m from its canonical elevation; it is "
                   "reported, never lowered by a presentation offset" % err)]}
