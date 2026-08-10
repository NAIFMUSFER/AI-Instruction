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
