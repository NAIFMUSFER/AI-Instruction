# -*- coding: utf-8 -*-
# =============================================================================
# acs_visual.py — أساس العرض البصري والتقديم: تصوير يحفظ الهندسة، لا أكثر.
#
# يقرأ النماذج المصرَّفة (معماري · إنشائي · MEP · حريق · تنسيق) ويبني مشهداً
# بصرياً مشتقّاً: أجسام ومواد وإضاءة وكاميرات وبيئة وحالة تقديم.
#
# مبادئ صارمة:
#   • لا تعديل هندسي إطلاقاً: لا جدار يُزحزح ولا باب ولا نافذة ولا درج ولا عنصر
#     إنشائي ولا مسار MEP ولا جهاز حريق، ولا غرفة تُضاف أو تُحذف، ولا عدد أدوار
#     يتغيّر، ولا مسطح مبنى يتبدّل.
#   • المادة البصرية مظهر فقط: ليست مادة إنشائية ولا تصنيف حريق ولا خاصية حرارية.
#   • الديكور والعناصر التزيينية VISUAL_ONLY ولا تُحتسب في أي عدّ هندسي.
#   • احتياط العرض لا يصير بيانات هندسية أبداً.
#   • صورة الذكاء الاصطناعي تحسين مظهر، وليست حقيقة هندسية ولا تُكتب في نموذج.
#   • الطبقة مشتقّة بالكامل: تصريفها يترك كل نموذج تخصّص مطابقاً بايت ببايت.
# =============================================================================
import hashlib
import json
import math
import os

import acs_arch as ARCH
import acs_struct as STRUCT
import acs_mep as MEP
import acs_fls as FLS
import acs_coord as COORD
import acs_revision as REV

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_visual.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
COMPILER_VERSION = SPEC["compiler_version"]
VISUAL_MODES = tuple(SPEC["visual_modes"])
ENGINEERING_MODES = tuple(SPEC["engineering_modes"])
PRESENTATION_MODES = tuple(SPEC["presentation_modes"])
ORTHOGRAPHIC_MODES = tuple(SPEC["orthographic_modes"])
VISUAL_LAYERS = tuple(SPEC["visual_layers"])
MODE_DEFAULT_LAYERS = SPEC["mode_default_layers"]
MATERIALS = SPEC["materials"]
MATERIAL_CLASS = SPEC["material_class"]
MATERIAL_PROVENANCE = tuple(SPEC["material_provenance"])
THEMES = tuple(SPEC["themes"])
THEME_PALETTE = SPEC["theme_palette"]
DEFAULT_THEME = SPEC["default_theme"]
ENGINEERING_PALETTE = SPEC["engineering_palette"]
DECORATION_CLASS = SPEC["decoration_class"]
DECORATION_KINDS = tuple(SPEC["decoration_kinds"])
ENTOURAGE_CLASS = SPEC["entourage_class"]
LANDSCAPE_CLASS = SPEC["landscape_class"]
WATER_KINDS = tuple(SPEC["water_kinds"])
CAMERA_PRESETS = tuple(SPEC["camera_presets"])
CAMERA_DEFAULTS = SPEC["camera_defaults"]
LIGHTING_PRESETS = tuple(SPEC["lighting_presets"])
LIGHTING_PARAMS = SPEC["lighting_preset_params"]
DEFAULT_LIGHTING = SPEC["default_lighting"]
QUALITY_PROFILES = tuple(SPEC["quality_profiles"])
QUALITY_PARAMS = SPEC["quality_params"]
DEFAULT_QUALITY = SPEC["default_quality"]
LOD_LEVELS = tuple(SPEC["lod_levels"])
FLOOR_PLAN_STYLES = tuple(SPEC["floor_plan_styles"])
SECTION_AXES = tuple(SPEC["section_axes"])
ELEVATION_FACES = tuple(SPEC["elevation_faces"])
CUTAWAY_METHODS = tuple(SPEC["cutaway_methods"])
SNAPSHOT_FORMATS = tuple(SPEC["snapshot_formats"])
SNAPSHOT_DEFAULTS = SPEC["snapshot_defaults"]
SNAPSHOT_MAX_PX = int(SPEC["snapshot_max_px"])
RENDER_KINDS = tuple(SPEC["render_kinds"])
RENDER_AUTHORITY = SPEC["render_authority"]
CONTROL_BUFFERS = tuple(SPEC["control_buffers"])
AI_STAGES = tuple(SPEC["ai_enhancement_stages"])
AI_MAY_CHANGE = tuple(SPEC["ai_may_change"])
AI_MAY_NOT_CHANGE = tuple(SPEC["ai_may_not_change"])
DRIFT_CODES = tuple(SPEC["drift_codes"])
VALIDATION_CODES = tuple(SPEC["validation_codes"])
DRIFT_SEVERITIES = tuple(SPEC["drift_severities"])
DRIFT_CODE_SEVERITY = SPEC["drift_code_severity"]
ASSET_CLASSES = tuple(SPEC["asset_classes"])
ASSET_LICENSES = tuple(SPEC["asset_licenses"])
PRESENTATION_BLOCK_KEY = SPEC["presentation_block_key"]

_EPS = 1e-9


# ------------------------------------------------------------- أدوات --------
def _q(v):
    """تقريب موحّد للإحداثيات المنشورة — يمنع انحراف الفاصلة بين اللغتين."""
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
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _val(field, fallback_ok=True):
    """قيمة مذكورة إن وُجدت، وإلّا احتياط عرض — مع الإفصاح عن أيّهما استُعمل."""
    if not isinstance(field, dict):
        return (None, "unknown")
    if field.get("value") is not None:
        return (float(field["value"]), "model")
    if fallback_ok and field.get("render_fallback") is not None:
        return (float(field["render_fallback"]), "display_fallback")
    return (None, "unknown")


def _mode(m):
    m = str(m or "PRESENTATION").upper()
    return m if m in VISUAL_MODES else "PRESENTATION"


def _theme(t):
    t = str(t or DEFAULT_THEME)
    return t if t in THEMES else DEFAULT_THEME


def _light(p):
    p = str(p or DEFAULT_LIGHTING).upper()
    return p if p in LIGHTING_PRESETS else DEFAULT_LIGHTING


def _quality(p):
    p = str(p or DEFAULT_QUALITY).upper()
    return p if p in QUALITY_PROFILES else DEFAULT_QUALITY


def _style(s):
    s = str(s or "TECHNICAL").upper()
    return s if s in FLOOR_PLAN_STYLES else "TECHNICAL"


# ----------------------------------------------------- مكتبة الأصول --------
_ASSETS = [
    {"id": "asset.proc.box", "type": "generic", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.0, "d": 1.0, "h": 1.0},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.sofa", "type": "sofa", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 2.0, "d": 0.9, "h": 0.8},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.table", "type": "table", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.4, "d": 0.8, "h": 0.75},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.chair", "type": "chair", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 0.5, "d": 0.5, "h": 0.9},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.bed", "type": "bed", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.6, "d": 2.0, "h": 0.5},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.cabinet", "type": "cabinet", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.2, "d": 0.5, "h": 1.8},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.tv", "type": "tv", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.2, "d": 0.08, "h": 0.7},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.rug", "type": "rug", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 2.4, "d": 1.6, "h": 0.02},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.plant", "type": "plant", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 0.6, "d": 0.6, "h": 1.2},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.lamp", "type": "lamp", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 0.35, "d": 0.35, "h": 1.5},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.tree", "type": "tree", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 3.0, "d": 3.0, "h": 5.0},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.shrub", "type": "shrub", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.0, "d": 1.0, "h": 0.8},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.person", "type": "person", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 0.5, "d": 0.35, "h": 1.7},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
    {"id": "asset.proc.car", "type": "car", "asset_class": "VISUAL_ONLY",
     "dimensions_m": {"w": 1.8, "d": 4.4, "h": 1.5},
     "license": "PROCEDURAL", "source": "acs_visual", "author": None},
]
_ASSET_INDEX = {a["id"]: a for a in _ASSETS}
_ASSET_BY_TYPE = {}
for _a in _ASSETS:
    _ASSET_BY_TYPE.setdefault(_a["type"], _a["id"])


def asset_library():
    """نسخة من مكتبة الأصول المحلّية. لا تنزيل ولا مصدر خارجي ولا تنفيذ."""
    return [dict(a) for a in _ASSETS]


def asset_by_id(aid):
    a = _ASSET_INDEX.get(aid)
    return dict(a) if a else None


def _asset_for(kind):
    """أصل من المكتبة إن وُجد، وإلّا صندوق إجرائي مُعلَن كاحتياط."""
    aid = _ASSET_BY_TYPE.get(kind)
    if aid:
        return (aid, False)
    return ("asset.proc.box", True)


def validate_asset(asset):
    """يرفض الأصل الناقص أو مجهول الرخصة أو الذي يحاول حمل شيفرة."""
    issues = []
    if not isinstance(asset, dict):
        return ["ASSET_NOT_AN_OBJECT"]
    for f in SPEC["asset_required_fields"]:
        if asset.get(f) in (None, ""):
            issues.append("ASSET_FIELD_MISSING:" + f)
    if asset.get("asset_class") not in ASSET_CLASSES:
        issues.append("ASSET_CLASS_INVALID")
    if asset.get("license") not in ASSET_LICENSES:
        issues.append("ASSET_LICENSE_INVALID")
    if asset.get("license") == "UNKNOWN":
        issues.append("ASSET_LICENSE_UNKNOWN_NOT_EMITTED")
    d = asset.get("dimensions_m")
    if not isinstance(d, dict) or any(_num(d.get(k)) is None or _num(d.get(k)) <= 0
                                      for k in ("w", "d", "h")):
        issues.append("ASSET_DIMENSIONS_INVALID")
    # بيانات الأصل بيانات، لا تُنفَّذ أبداً — أي حقل شيفرة يُرفض صراحةً
    for k in ("script", "code", "eval", "onload", "src", "url", "href", "exec"):
        if k in asset:
            issues.append("ASSET_METADATA_MUST_NOT_CARRY_CODE:" + k)
    return sorted(issues)


# ---------------------------------------------------------- المواد ---------
def material(mid):
    m = MATERIALS.get(mid)
    if m is None:
        return None
    out = dict(m)
    out["id"] = mid
    out["material_class"] = MATERIAL_CLASS
    out["structural_material"] = False
    out["fire_rating"] = None
    out["thermal_property"] = None
    out["note"] = ("visual material only — no structural, fire or thermal property is "
                   "implied by its appearance or its name")
    return out


def _assign(theme, slot, overrides, subject):
    """اختيار مادة مع إسناد صريح: المستخدم أوّلاً، ثم السمة، ثم افتراض النظام."""
    ov = (overrides or {}).get(subject)
    if isinstance(ov, dict) and ov.get("material") in MATERIALS:
        prov = str(ov.get("provenance") or "USER").upper()
        return (ov["material"], prov if prov in MATERIAL_PROVENANCE else "USER")
    if isinstance(ov, str) and ov in MATERIALS:
        return (ov, "USER")
    pal = THEME_PALETTE.get(theme) or {}
    mid = pal.get(slot)
    if mid in MATERIALS:
        return (mid, "VISUAL_THEME" if theme != DEFAULT_THEME else "SYSTEM_DEFAULT")
    return ("paint_white", "SYSTEM_DEFAULT")


# ------------------------------------------------------- هندسة عالمية ------
def _rot(px, pz, rot_deg, ox=0.0, oz=0.0):
    r = math.radians(float(rot_deg or 0.0))
    ca, sa = math.cos(r), math.sin(r)
    return [ox + px * ca - pz * sa, oz + px * sa + pz * ca]


def _world(cx, cy, cz, ex, ey, ez, rot_y, transform):
    t = transform or {}
    brot = float(t.get("rotation_deg") or 0.0)
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    wx, wz = _rot(cx, cz, brot, px, pz)
    return {"type": "box", "cx": _q(wx), "cy": _q(cy), "cz": _q(wz),
            "ex": _q(abs(ex)), "ey": _q(abs(ey)), "ez": _q(abs(ez)),
            "rot_y": _q(float(rot_y or 0.0) + math.radians(brot))}


def _seg(a, b, w, h, transform):
    dx, dz = b[0] - a[0], b[2] - a[2]
    ln = math.sqrt(dx * dx + dz * dz)
    if ln <= 1e-9:
        return _world((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, (a[2] + b[2]) / 2.0,
                      max(w, 1e-3), max(h, 1e-3), max(w, 1e-3), 0.0, transform)
    return _world((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, (a[2] + b[2]) / 2.0,
                  ln, max(h, 1e-3), max(w, 1e-3), math.atan2(-dz, dx), transform)


def _obj(oid, kind, layer, geom, material_id, provenance, **meta):
    o = {"id": oid, "kind": kind, "layer": layer, "geometry": geom,
         "material": material_id, "material_provenance": provenance,
         "semantic": True, "visual_only": False, "lod": "FULL",
         "asset_id": None, "asset_fallback": False, "instance_key": None,
         "geometry_source": "model", "visible": True,
         "source_layer": None, "source_element_id": None}
    o.update(meta)
    return o


# --------------------------------------------------- أجسام المعماري -------
def _arch_objects(arch, transform, bid, theme, overrides, mode):
    out = []
    if not arch:
        return out
    lv = {l["index"]: l for l in arch.get("levels") or []}
    wall_m, wall_p = _assign(theme, "wall", overrides, "wall")
    floor_m, floor_p = _assign(theme, "floor", overrides, "floor")
    ceil_m, ceil_p = _assign(theme, "ceiling", overrides, "ceiling")
    glass_m, glass_p = _assign(theme, "glass", overrides, "glass")
    frame_m, frame_p = _assign(theme, "frame", overrides, "frame")
    roof_m, roof_p = _assign(theme, "roof", overrides, "roof")
    eng = mode in ENGINEERING_MODES

    for w in arch.get("walls") or []:
        h, hs = _val(w["height_m"])
        t, ts = _val(w["thickness_m"])
        base = (lv.get(w["level_index"]) or {}).get("elevation_m")
        if h is None or t is None or base is None:
            continue
        a, b = w["start"], w["end"]
        g = _seg([a["x"], base + h / 2.0, a["z"]], [b["x"], base + h / 2.0, b["z"]],
                 t, h, transform)
        out.append(_obj(w["id"], "WALL", "ARCHITECTURE", g,
                        "technical" if eng else wall_m,
                        "SYSTEM_DEFAULT" if eng else wall_p,
                        source_layer="ARCHITECTURE", source_element_id=w["id"],
                        level_index=w["level_index"], exposure=w["exposure"],
                        geometry_source="model" if (hs == "model" and ts == "model")
                        else "display_fallback",
                        engineering_color=ENGINEERING_PALETTE["ARCH_WALL"]))

    for o in arch.get("openings") or []:
        wdt, ws = _val(o["width_m"])
        hgt, hs = _val(o["height_m"])
        base = (lv.get(o.get("level_index")) or {}).get("elevation_m")
        if wdt is None or hgt is None or base is None:
            continue
        sill = 0.0
        if o["type"] == "WINDOW":
            s, _ss = _val(o["sill_m"])
            sill = s if s is not None else 0.0
        cy = base + sill + hgt / 2.0
        if o["axis"] == "x":
            g = _world(o["u_center"], cy, o["fixed"], wdt, hgt, 0.12, 0.0, transform)
        else:
            g = _world(o["fixed"], cy, o["u_center"], 0.12, hgt, wdt, 0.0, transform)
        is_win = o["type"] == "WINDOW"
        out.append(_obj(o["id"], o["type"], "ARCHITECTURE", g,
                        "technical" if eng else (glass_m if is_win else frame_m),
                        "SYSTEM_DEFAULT" if eng else (glass_p if is_win else frame_p),
                        source_layer="ARCHITECTURE", source_element_id=o["id"],
                        level_index=o.get("level_index"), host_wall_id=o.get("host_wall_id"),
                        space_id=o.get("space_id"),
                        geometry_source="model" if (ws == "model" and hs == "model")
                        else "display_fallback",
                        engineering_color=ENGINEERING_PALETTE["ARCH_OPENING"]))

    for s in arch.get("slabs") or []:
        o = s["outline"]
        t, ts = _val(s["thickness_m"])
        if o is None or s["elevation_m"] is None or t is None:
            continue
        g = _world(o[0] + o[2] / 2.0, s["elevation_m"] - t / 2.0, o[1] + o[3] / 2.0,
                   o[2], t, o[3], 0.0, transform)
        out.append(_obj(s["id"], "SLAB", "ARCHITECTURE", g,
                        "technical" if eng else floor_m,
                        "SYSTEM_DEFAULT" if eng else floor_p,
                        source_layer="ARCHITECTURE", source_element_id=s["id"],
                        level_index=s["level_index"],
                        geometry_source="model" if ts == "model" else "display_fallback",
                        engineering_color=ENGINEERING_PALETTE["ARCH_SLAB"]))

    if mode != "ENGINEERING":
        for c in arch.get("ceilings") or []:
            o = c["outline"]
            t, ts = _val(c["thickness_m"])
            if o is None or c["elevation_m"] is None or t is None:
                continue
            g = _world(o[0] + o[2] / 2.0, c["elevation_m"] + t / 2.0, o[1] + o[3] / 2.0,
                       o[2], t, o[3], 0.0, transform)
            out.append(_obj(c["id"], "CEILING", "ARCHITECTURE", g, ceil_m, ceil_p,
                            source_layer="ARCHITECTURE", source_element_id=c["id"],
                            space_id=c.get("space_id"),
                            geometry_source="model" if ts == "model" else "display_fallback"))

    for r in arch.get("roofs") or []:
        o = r.get("outline")
        t, ts = _val(r.get("thickness_m"))
        if o is None or r.get("elevation_m") is None or t is None:
            continue
        g = _world(o[0] + o[2] / 2.0, r["elevation_m"] + t / 2.0, o[1] + o[3] / 2.0,
                   o[2], t, o[3], 0.0, transform)
        out.append(_obj(r["id"], "ROOF", "ARCHITECTURE", g, roof_m, roof_p,
                        source_layer="ARCHITECTURE", source_element_id=r["id"],
                        geometry_source="model" if ts == "model" else "display_fallback"))

    # درج مرئي عند نواة معلنة — موضعه وأبعاده من النموذج، لا من تقدير
    for c in arch.get("cores") or []:
        if c["type"] != "STAIR":
            continue
        fw, fws = _val(c["footprint_w_m"])
        fd, fds = _val(c["footprint_d_m"])
        served = c.get("served_levels") or []
        if fw is None or fd is None or not served:
            continue
        base = (lv.get(min(served)) or {}).get("elevation_m")
        top = (lv.get(max(served)) or {}).get("elevation_m")
        if base is None or top is None or top - base <= 0:
            continue
        g = _world(c["x"], base + (top - base) / 2.0, c["z"], fw, top - base, fd,
                   0.0, transform)
        out.append(_obj(c["id"], "STAIR", "ARCHITECTURE", g,
                        "technical" if eng else floor_m,
                        "SYSTEM_DEFAULT" if eng else floor_p,
                        source_layer="ARCHITECTURE", source_element_id=c["id"],
                        core_type=c["type"],
                        geometry_source="model" if (fws == "model" and fds == "model")
                        else "display_fallback"))
    return out


def _roof_cap(arch, transform, bid, theme, overrides):
    """غطاء سقف بصريّ فوق أعلى مستوى حين لا يذكر النموذج سقفاً.
    مُعلَن visual_only واحتياط عرض — ولا يصير سقفاً هندسياً أبداً."""
    if not arch or (arch.get("roofs") or []):
        return []
    lv = sorted([l for l in (arch.get("levels") or []) if l["elevation_m"] is not None],
                key=lambda l: l["index"])
    slabs = [s for s in (arch.get("slabs") or []) if s["outline"]]
    if not lv or not slabs:
        return []
    top = lv[-1]
    tops = [s for s in slabs if s["level_index"] == top["index"]] or slabs[-1:]
    o = tops[0]["outline"]
    hs = [_val(w["height_m"])[0] for w in (arch.get("walls") or [])
          if w["level_index"] == top["index"] and _val(w["height_m"])[0] is not None]
    h = max(hs) if hs else 3.0
    y = top["elevation_m"] + h
    roof_m, roof_p = _assign(theme, "roof", overrides, "roof")
    g = _world(o[0] + o[2] / 2.0, y + 0.1, o[1] + o[3] / 2.0, o[2], 0.2, o[3], 0.0, transform)
    return [_obj("%s.vis.roof_cap" % bid, "ROOF_CAP", "ARCHITECTURE", g, roof_m, roof_p,
                 semantic=False, visual_only=True, geometry_source="display_fallback",
                 source_layer=None, source_element_id=None,
                 note="visual roof cap — the model states no roof; this is appearance only "
                      "and is never engineering geometry")]


# ------------------------------------- أجسام التخصّصات الأخرى (كما هي) ----
def _discipline_objects(items, layer, transform, colour):
    out = []
    for it in items:
        if not (it.get("ex") and it.get("ey") and it.get("ez")):
            continue
        g = _world(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"],
                   it.get("rot_y") or 0.0, transform)
        out.append(_obj(it.get("name") or it["id"], it["kind"], layer, g,
                        "technical", "SYSTEM_DEFAULT",
                        source_layer=layer, source_element_id=it["id"],
                        geometry_source=it.get("geometry_source") or "model",
                        engineering_color=colour))
    return out


def _fls_objects(fls, transform):
    out = []
    if not fls:
        return out
    for it in FLS.render_items(fls):
        if it["render_mode"] != "emitted":
            continue
        g = _world(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"], 0.0, transform)
        out.append(_obj(it["id"], it["kind"], "FLS", g, "technical", "SYSTEM_DEFAULT",
                        source_layer="FLS", source_element_id=it["id"],
                        geometry_source=it.get("geometry_source") or "model",
                        engineering_color=ENGINEERING_PALETTE["FLS"]))
    return out


# ------------------------------------------------- الموقع والمناظر --------
def _site_objects(building, arch, transform, bid, theme, overrides, bbox):
    """أرضية بصرية ومناظر — بلا اختراع أي هندسة موقع."""
    out = []
    site = building.get("site") if isinstance(building.get("site"), dict) else None
    w = _num((site or {}).get("w"))
    d = _num((site or {}).get("d"))
    stated = w is not None and d is not None and w > 0 and d > 0
    if not stated and bbox:
        w = max(bbox[3] - bbox[0], 1.0) * 3.0
        d = max(bbox[5] - bbox[2], 1.0) * 3.0
    if w is None or d is None:
        return out
    cx = w / 2.0 if stated else ((bbox[0] + bbox[3]) / 2.0 if bbox else 0.0)
    cz = d / 2.0 if stated else ((bbox[2] + bbox[5]) / 2.0 if bbox else 0.0)
    g = _world(cx, -0.05, cz, w, 0.1, d, 0.0, transform)
    out.append(_obj("%s.vis.ground" % bid, "GROUND", "SITE", g, "grass", "SYSTEM_DEFAULT",
                    semantic=False, visual_only=True, geometry_source="display_fallback",
                    site_dimensions_stated=bool(stated),
                    note="visual ground plane — appearance only; no site geometry is "
                         "invented and its extent is not a stated site boundary"
                         if not stated else
                         "visual ground plane drawn to the stated site dimensions"))
    return out


def _water_objects(building, transform, bid):
    """ماء مرئي للعناصر المائية المذكورة صراحةً فقط. لا مسبح يُختلق."""
    out = []
    n = 0
    for f in (building.get("site_features") or []) if isinstance(
            building.get("site_features"), list) else []:
        k = str(f.get("kind") or "").lower()
        if k not in WATER_KINDS:
            continue
        x, z = _num(f.get("x")), _num(f.get("z"))
        fw, fd = _num(f.get("w")), _num(f.get("d"))
        if None in (x, z, fw, fd):
            continue
        g = _world(x + fw / 2.0, 0.02, z + fd / 2.0, fw, 0.04, fd, 0.0, transform)
        out.append(_obj("%s.vis.water_%d" % (bid, n), "WATER", "SITE", g,
                        "water", "SYSTEM_DEFAULT",
                        source_layer="SITE", source_element_id=f.get("id"),
                        water_kind=k, geometry_source="model",
                        note="visual water for a represented water feature"))
        n += 1
    return out


def _landscape_objects(bbox, transform, bid, count):
    """نباتات بصرية فقط حول المسطح — VISUAL_ONLY وموضعها حتمي لا عشوائي."""
    out = []
    if not bbox or count <= 0:
        return out
    x0, z0, x1, z1 = bbox[0], bbox[2], bbox[3], bbox[5]
    per = max(1, count // 4)
    n = 0
    for side in range(4):
        for i in range(per):
            f = (i + 1.0) / (per + 1.0)
            if side == 0:
                x, z = x0 + (x1 - x0) * f, z0 - 4.0
            elif side == 1:
                x, z = x0 + (x1 - x0) * f, z1 + 4.0
            elif side == 2:
                x, z = x0 - 4.0, z0 + (z1 - z0) * f
            else:
                x, z = x1 + 4.0, z0 + (z1 - z0) * f
            aid, fb = _asset_for("tree" if (n % 3) else "shrub")
            a = _ASSET_INDEX[aid]["dimensions_m"]
            g = _world(x, a["h"] / 2.0, z, a["w"], a["h"], a["d"], 0.0, transform)
            out.append(_obj("%s.vis.land_%d" % (bid, n), "TREE" if (n % 3) else "SHRUB",
                            "LANDSCAPE", g, "grass", "SYSTEM_DEFAULT",
                            semantic=False, visual_only=True, asset_id=aid,
                            asset_fallback=fb, geometry_source="display_fallback",
                            instance_key="LANDSCAPE|" + aid + "|grass",
                            visual_class=LANDSCAPE_CLASS,
                            note="visual-only landscape placeholder; not project site geometry"))
            n += 1
    return out


# ------------------------------------------------------------ الديكور -----
_DECOR_BY_NAME = (
    ("majlis", ("sofa", "table", "rug", "plant")),
    ("living", ("sofa", "table", "tv", "rug")),
    ("family", ("sofa", "table", "tv")),
    ("bed", ("bed", "cabinet", "lamp")),
    ("lobby", ("sofa", "table", "plant")),
    ("kitchen", ("cabinet", "table")),
    ("office", ("table", "chair", "cabinet")),
    ("room", ("bed", "cabinet")),
    ("reception", ("table", "chair", "plant")),
    ("waiting", ("chair", "plant")),
)


def _decor_kinds(name):
    n = str(name or "").lower()
    for key, kinds in _DECOR_BY_NAME:
        if key in n:
            return kinds
    return ()


def _decoration_objects(arch, transform, bid, theme, overrides):
    """ديكور بصريّ حتميّ داخل الفراغات المذكورة. VISUAL_ONLY دائماً، ولا يدخل
    أي عدّ هندسي، ولا يُخلط بعنصر طلبه المستخدم."""
    out = []
    if not arch:
        return out
    lv = {l["index"]: l for l in arch.get("levels") or []}
    accent_m, accent_p = _assign(theme, "accent", overrides, "decoration")
    n = 0
    for sp in sorted(arch.get("spaces") or [], key=lambda s: str(s["id"])):
        kinds = _decor_kinds(sp.get("name"))
        if not kinds:
            continue
        r = sp["rect"]
        base = (lv.get(sp["level_index"]) or {}).get("elevation_m")
        if base is None or r[2] <= 0.6 or r[3] <= 0.6:
            continue
        for k, kind in enumerate(kinds):
            aid, fb = _asset_for(kind)
            a = _ASSET_INDEX[aid]["dimensions_m"]
            if a["w"] + 0.4 > r[2] or a["d"] + 0.4 > r[3]:
                continue
            fx = (k + 1.0) / (len(kinds) + 1.0)
            x = r[0] + r[2] * fx
            z = r[1] + r[3] * (0.3 if k % 2 == 0 else 0.7)
            g = _world(x, base + a["h"] / 2.0, z, a["w"], a["h"], a["d"], 0.0, transform)
            out.append(_obj("%s.vis.deco_%d" % (bid, n), kind.upper(), "FURNITURE", g,
                            accent_m, accent_p,
                            semantic=False, visual_only=True, asset_id=aid,
                            asset_fallback=fb, geometry_source="display_fallback",
                            instance_key="FURNITURE|" + aid + "|" + accent_m,
                            visual_class=DECORATION_CLASS,
                            space_id=sp["id"], level_index=sp["level_index"],
                            note="visual decoration only — never an engineering object, "
                                 "never an occupant, never a coverage or load input"))
            n += 1
    return out


def _entourage_objects(bbox, transform, bid, count):
    out = []
    if not bbox or count <= 0:
        return out
    for i in range(count):
        kind = "person" if i % 2 == 0 else "car"
        aid, fb = _asset_for(kind)
        a = _ASSET_INDEX[aid]["dimensions_m"]
        f = (i + 1.0) / (count + 1.0)
        x = bbox[0] + (bbox[3] - bbox[0]) * f
        z = bbox[2] - 6.0 - (2.0 if kind == "car" else 0.0)
        g = _world(x, a["h"] / 2.0, z, a["w"], a["h"], a["d"], 0.0, transform)
        out.append(_obj("%s.vis.ent_%d" % (bid, i), kind.upper(), "ENTOURAGE", g,
                        "fabric" if kind == "person" else "metal_steel", "SYSTEM_DEFAULT",
                        semantic=False, visual_only=True, asset_id=aid, asset_fallback=fb,
                        geometry_source="display_fallback",
                        instance_key="ENTOURAGE|" + aid,
                        visual_class=ENTOURAGE_CLASS,
                        note="visual-only entourage; never an occupant and never counted"))
    return out


# ------------------------------------------------------------ الإضاءة -----
def _lights(preset, bbox, mep, transform, bid):
    p = LIGHTING_PARAMS[preset]
    out = [
        {"id": "%s.vis.light_sun" % bid, "kind": "SUN", "visual_only": True,
         "elevation_deg": p["sun_elevation_deg"], "azimuth_deg": p["sun_azimuth_deg"],
         "intensity": p["sun_intensity"], "color": p["sun_color"], "casts_shadow": True,
         "note": "presentation light rig — not an MEP luminaire and no illuminance implied"},
        {"id": "%s.vis.light_sky" % bid, "kind": "SKY", "visual_only": True,
         "intensity": p["sky_intensity"], "color": p["ambient_color"],
         "casts_shadow": False,
         "note": "presentation light rig — not an MEP luminaire and no illuminance implied"},
        {"id": "%s.vis.light_ambient" % bid, "kind": "AMBIENT", "visual_only": True,
         "intensity": p["ambient_intensity"], "color": p["ambient_color"],
         "casts_shadow": False,
         "note": "presentation light rig — not an MEP luminaire and no illuminance implied"},
    ]
    if preset == "NIGHT" and mep:
        n = 0
        for t in sorted((mep.get("terminals") or []), key=lambda x: str(x["id"])):
            if str(t.get("terminal_type") or "").lower() not in ("light_fixture", "luminaire"):
                continue
            if t.get("x") is None or t.get("z") is None:
                continue
            y = _num(t.get("y"))
            wx, wz = _rot(float(t["x"]), float(t["z"]),
                          float((transform or {}).get("rotation_deg") or 0.0),
                          float(((transform or {}).get("position") or {}).get("x") or 0.0),
                          float(((transform or {}).get("position") or {}).get("z") or 0.0))
            out.append({"id": "%s.vis.light_%d" % (bid, n), "kind": "INTERIOR_VISUAL",
                        "visual_only": True, "intensity": 0.6, "color": "#ffe9c4",
                        "casts_shadow": False,
                        "x": _q(wx), "y": _q(y if y is not None else 2.7), "z": _q(wz),
                        "at_mep_element": t["id"],
                        "note": "a visual emitter placed at a represented fixture; it asserts "
                                "nothing about that fixture's output or adequacy"})
            n += 1
    return out


# --------------------------------------------------------- الكاميرات ------
def _bbox_of(objects):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    found = False
    for o in objects:
        if o.get("visual_only"):
            continue
        g = o["geometry"]
        c = math.cos(g["rot_y"])
        s = math.sin(g["rot_y"])
        rx = abs(g["ex"] / 2.0 * c) + abs(g["ez"] / 2.0 * s)
        rz = abs(g["ex"] / 2.0 * s) + abs(g["ez"] / 2.0 * c)
        for i, (c0, r) in enumerate(((g["cx"], rx), (g["cy"], g["ey"] / 2.0), (g["cz"], rz))):
            lo[i] = min(lo[i], c0 - r)
            hi[i] = max(hi[i], c0 + r)
        found = True
    if not found:
        return None
    return [_q(lo[0]), _q(lo[1]), _q(lo[2]), _q(hi[0]), _q(hi[1]), _q(hi[2])]


def _fit_distance(bbox, fov_deg, margin):
    """مسافة تُظهر المبنى كاملاً بهامش معلن — محسوبة من حجم النموذج نفسه."""
    w = max(bbox[3] - bbox[0], 1e-3)
    h = max(bbox[4] - bbox[1], 1e-3)
    d = max(bbox[5] - bbox[2], 1e-3)
    radius = math.sqrt(w * w + h * h + d * d) / 2.0
    half = math.radians(float(fov_deg)) / 2.0
    dist = radius / max(math.tan(half), 1e-6)
    return max(dist * float(margin), float(CAMERA_DEFAULTS["min_distance_m"]))


def _camera(preset, bbox, bid, spaces, transform, room_id=None):
    fov = float(CAMERA_DEFAULTS["fov_deg"])
    margin = float(CAMERA_DEFAULTS["margin"])
    cx = (bbox[0] + bbox[3]) / 2.0
    cy = (bbox[1] + bbox[4]) / 2.0
    cz = (bbox[2] + bbox[5]) / 2.0
    dist = _fit_distance(bbox, fov, margin)
    target = [_q(cx), _q(cy), _q(cz)]
    proj = "orthographic" if preset in ("SECTION", "ELEVATION") else "perspective"
    if preset == "EXTERIOR_FRONT":
        pos = [cx, cy + dist * 0.25, cz - dist]
    elif preset == "EXTERIOR_REAR":
        pos = [cx, cy + dist * 0.25, cz + dist]
    elif preset == "EXTERIOR_CORNER":
        pos = [cx - dist * 0.72, cy + dist * 0.45, cz - dist * 0.72]
    elif preset == "TOP":
        pos = [cx, cy + dist * 1.4, cz + 0.001]
    elif preset == "DOLLHOUSE":
        pos = [cx - dist * 0.55, cy + dist * 0.9, cz - dist * 0.55]
    elif preset == "PANORAMA_360":
        pos = [cx, bbox[1] + float(CAMERA_DEFAULTS["eye_height_m"]), cz]
    elif preset in ("INTERIOR_ROOM", "WALKTHROUGH"):
        sp = None
        for s in spaces or []:
            if room_id is None or s["id"] == room_id or s.get("space_id") == room_id \
               or s.get("name") == room_id:
                sp = s
                break
        if sp is None:
            pos = [cx, bbox[1] + float(CAMERA_DEFAULTS["eye_height_m"]), cz]
        else:
            r = sp["rect"]
            base = 0.0
            wx, wz = _rot(r[0] + r[2] * 0.5, r[1] + r[3] * 0.5,
                          float((transform or {}).get("rotation_deg") or 0.0),
                          float(((transform or {}).get("position") or {}).get("x") or 0.0),
                          float(((transform or {}).get("position") or {}).get("z") or 0.0))
            tx, tz = _rot(r[0] + r[2] * 0.5, r[1] + r[3] * 0.9,
                          float((transform or {}).get("rotation_deg") or 0.0),
                          float(((transform or {}).get("position") or {}).get("x") or 0.0),
                          float(((transform or {}).get("position") or {}).get("z") or 0.0))
            base = sp.get("_elev") or 0.0
            pos = [wx, base + float(CAMERA_DEFAULTS["eye_height_m"]), wz]
            target = [_q(tx), _q(base + 1.5), _q(tz)]
    elif preset == "SECTION":
        pos = [cx, cy, cz - dist]
    else:                                   # ELEVATION
        pos = [cx, cy, cz - dist]
    return {"id": "%s.vis.cam_%s" % (bid, preset), "preset": preset,
            "projection": proj, "fov_deg": _q(fov) if proj == "perspective" else None,
            "position": [_q(pos[0]), _q(pos[1]), _q(pos[2])],
            "target": target,
            "up": [0.0, 1.0, 0.0],
            "near_m": CAMERA_DEFAULTS["near_m"], "far_m": CAMERA_DEFAULTS["far_m"],
            "margin": _q(margin), "fit_bbox": list(bbox),
            "presentation_state": True,
            "note": "camera state is presentation state, never model truth"}


def frame_camera(scene, preset, room_id=None):
    """إعادة تأطير كاميرا على المشهد نفسه — بلا أي إعادة توليد للهندسة."""
    preset = str(preset or "EXTERIOR_CORNER").upper()
    if preset not in CAMERA_PRESETS:
        return None
    bbox = scene.get("bounds")
    if not bbox:
        return None
    return _camera(preset, bbox, scene["building_id"], scene.get("spaces_index") or [],
                   scene.get("transform"), room_id)


# --------------------------------------------------- القص والدمى ---------
def _dollhouse(arch, mode, cut_level):
    """توجيهات إخفاء وقصّ — لا تعديل هندسة ولا نموذج ثانٍ."""
    if mode != "DOLLHOUSE":
        return None
    lv = sorted([l for l in (arch or {}).get("levels") or []
                 if l["elevation_m"] is not None], key=lambda l: l["index"])
    if not lv:
        return None
    idx = cut_level if cut_level is not None else lv[-1]["index"]
    top = None
    for l in lv:
        if l["index"] == idx:
            top = l
    if top is None:
        top = lv[-1]
    return {"hide_roof": True, "hide_ceilings": True,
            "clip_above_m": _q(top["elevation_m"] + 1.2),
            "cut_level_index": top["index"],
            "reversible": True,
            "note": "dollhouse hides the roof and clips enclosure above a stated height; "
                    "the model geometry is untouched and every room keeps its exact "
                    "position and size"}


def _cutaway(mode, method, plane):
    if mode != "CUTAWAY":
        return None
    method = str(method or "CLIP_PLANE").upper()
    if method not in CUTAWAY_METHODS:
        method = "CLIP_PLANE"
    p = plane if isinstance(plane, dict) else {}
    return {"method": method,
            "normal": [_q(_num(p.get("nx")) or 0.0), _q(_num(p.get("ny")) or 0.0),
                       _q(_num(p.get("nz")) if _num(p.get("nz")) is not None else 1.0)],
            "constant_m": _q(_num(p.get("constant")) or 0.0),
            "level_index": p.get("level_index"),
            "reversible": True,
            "note": "reversible rendering state only; no model geometry is modified and "
                    "restoring the scene restores the full view exactly"}


# ------------------------------------------------------ المشهد البصري ----
def compile_visual_scene(building, building_id="bld_0", position=None, rotation_deg=0.0,
                         mode="PRESENTATION", theme=None, lighting=None, quality=None,
                         arch=None, struct=None, mep=None, fls=None, coord=None,
                         layers=None, materials=None, include_decoration=False,
                         include_landscape=None, include_entourage=False,
                         landscape_count=12, entourage_count=0,
                         camera=None, room_id=None, cut_level=None, cutaway=None,
                         clash_overlay=False, scale=1.0, at=None):
    """يبني مشهداً بصرياً مشتقّاً. لا يعدّل أي نموذج ولا يولّد هندسة."""
    bid = building_id or "bld_0"
    b = building or {}
    mode = _mode(mode)
    theme = _theme(theme)
    lighting = _light(lighting)
    quality = _quality(quality)
    transform = {"position": position or {"x": 0.0, "z": 0.0},
                 "rotation_deg": float(rotation_deg or 0.0)}

    if arch is None:
        try:
            arch = ARCH.compile_architecture(b, bid, position, rotation_deg)
        except Exception:
            arch = None
    if struct is None:
        try:
            struct = STRUCT.compile_structure(b, bid, position, rotation_deg, arch)
        except Exception:
            struct = None
    if mep is None:
        try:
            mep = MEP.compile_mep(b, bid, position, rotation_deg, arch, struct)
        except Exception:
            mep = None
    if fls is None:
        try:
            fls = FLS.compile_fls(b, bid, position, rotation_deg, arch, mep)
        except Exception:
            fls = None

    active = [l for l in (layers if layers is not None
                          else MODE_DEFAULT_LAYERS.get(mode) or ["ARCHITECTURE"])
              if l in VISUAL_LAYERS]
    if mode in ENGINEERING_MODES:
        # العرض الهندسي لا يخفي تخصّصاً: إخفاؤه تحريف لا تقديم
        for l in ("ARCHITECTURE", "STRUCTURE", "MEP", "FLS"):
            if l not in active:
                active.append(l)
    active = sorted(set(active))

    objects = []
    if "ARCHITECTURE" in active:
        objects.extend(_arch_objects(arch, transform, bid, theme, materials, mode))
        if mode != "ENGINEERING":
            objects.extend(_roof_cap(arch, transform, bid, theme, materials))
    if "STRUCTURE" in active and struct:
        objects.extend(_discipline_objects(
            [it for it in STRUCT.render_items(struct) if it["kind"] != "GRID_LINE"],
            "STRUCTURE", transform, ENGINEERING_PALETTE["STRUCTURE"]))
    if "MEP" in active and mep:
        objects.extend(_discipline_objects(MEP.render_items(mep), "MEP", transform,
                                           ENGINEERING_PALETTE["MEP"]))
    if "FLS" in active and fls:
        objects.extend(_fls_objects(fls, transform))

    bbox_model = _bbox_of(objects)
    if "SITE" in active:
        objects.extend(_site_objects(b, arch, transform, bid, theme, materials, bbox_model))
        objects.extend(_water_objects(b, transform, bid))
    want_land = include_landscape if include_landscape is not None else ("LANDSCAPE" in active)
    if want_land and "LANDSCAPE" in active:
        objects.extend(_landscape_objects(bbox_model, transform, bid, int(landscape_count or 0)))
    if include_decoration and "FURNITURE" in active:
        objects.extend(_decoration_objects(arch, transform, bid, theme, materials))
    if include_entourage and "ENTOURAGE" in active:
        objects.extend(_entourage_objects(bbox_model, transform, bid, int(entourage_count or 0)))

    objects.sort(key=lambda o: (str(o["layer"]), str(o["kind"]), str(o["id"])))

    used = sorted({o["material"] for o in objects})
    mats = []
    for mid in used:
        m = material(mid)
        if m:
            prov = sorted({o["material_provenance"] for o in objects if o["material"] == mid})
            m["provenance"] = prov
            mats.append(m)

    bbox = bbox_model or _bbox_of(objects) or [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
    spaces = []
    lvmap = {l["index"]: l for l in (arch or {}).get("levels") or []}
    for s in sorted((arch or {}).get("spaces") or [], key=lambda x: str(x["id"])):
        spaces.append({"id": s["id"], "space_id": s.get("space_id"), "name": s.get("name"),
                       "rect": [_q(v) for v in s["rect"]],
                       "level_index": s["level_index"], "area_m2": _q(s["area_m2"]),
                       "_elev": _q((lvmap.get(s["level_index"]) or {}).get("elevation_m") or 0.0)})

    cams = [_camera(p, bbox, bid, spaces, transform,
                    room_id if p in ("INTERIOR_ROOM", "WALKTHROUGH") else None)
            for p in CAMERA_PRESETS]
    lights = _lights(lighting, bbox, mep, transform, bid)

    p = LIGHTING_PARAMS[lighting]
    qp = QUALITY_PARAMS[quality]
    try:
        mh = REV.model_hash(b, "building", bid)
    except Exception:
        mh = None

    sc = _num(scale)
    sc = 1.0 if sc is None or sc <= 0 else sc

    scene = {
        "schema": SCHEMA, "compiler_version": COMPILER_VERSION,
        "building_id": bid, "model_hash": mh,
        "scene_id": ("vscene_%s_%s" % (mh[:16], mode)) if mh else None,
        "created_at": at, "mode": mode, "transform": transform,
        "bounds": bbox,
        "objects": objects, "materials": mats, "lights": lights,
        "cameras": cams,
        "active_camera": (str(camera).upper() if str(camera or "").upper() in CAMERA_PRESETS
                          else ("DOLLHOUSE" if mode == "DOLLHOUSE" else "EXTERIOR_CORNER")),
        "environment": {
            "background": p["background"], "exposure": p["exposure"],
            "tone_mapping": qp["tone_mapping"], "environment_quality": qp["environment"],
            "ground_plane": any(o["kind"] == "GROUND" for o in objects),
            "note": "sky, background and ground plane are appearance only"},
        "presentation": {
            "theme": theme, "lighting_preset": lighting, "quality": quality,
            "quality_params": dict(qp), "layers": active,
            "layer_visibility": {l: (l in active) for l in VISUAL_LAYERS},
            "clash_overlay": bool(clash_overlay) and mode in tuple(SPEC["clash_overlay_modes"]),
            "dollhouse": _dollhouse(arch, mode, cut_level),
            "cutaway": _cutaway(mode, (cutaway or {}).get("method") if isinstance(cutaway, dict)
                                else cutaway, cutaway if isinstance(cutaway, dict) else None),
            "scale": _q(sc), "scale_is_explicit": sc != 1.0,
            "decoration_included": bool(include_decoration),
            "entourage_included": bool(include_entourage),
            "note": "presentation state only; none of it is model truth and none of it "
                    "enters a revision hash"},
        "counts": {},
        "meta": {"note": SPEC["note"], "derivation": SPEC["derivation_note"],
                 "authority": SPEC["authority_note"],
                 "material_class": MATERIAL_CLASS,
                 "compliance": "NOT_EVALUATED"},
        "spaces_index": spaces,
    }
    if scene["presentation"]["clash_overlay"] and coord is None:
        try:
            coord = COORD.compile_coordination(b, bid, position, rotation_deg,
                                               arch, struct, mep, fls)
        except Exception:
            coord = None
    if scene["presentation"]["clash_overlay"] and coord:
        scene["clash_overlay"] = [
            {"clash_id": c["id"], "type": c["type"], "severity": c["severity"],
             "elements": [c["element_a"], c["element_b"]],
             "intersection": (c.get("geometry") or {}).get("intersection"),
             "visual_only": True,
             "note": "coordination overlay drawn on the engineering view; it is never "
                     "hidden to make an image attractive and never baked into geometry"}
            for c in (coord.get("clashes") or []) if c.get("geometry")]
    # الأوضاع المسقطة تحمل الرسم المشتقّ من الهندسة نفسها — لا نموذج ثانٍ
    if mode == "FLOOR_PLAN_2D":
        li = cut_level if cut_level is not None else (
            min((l["index"] for l in (arch or {}).get("levels") or []), default=0))
        scene["drawing"] = floor_plan(arch, li, (cutaway or {}).get("style")
                                      if isinstance(cutaway, dict) else None, bid)
    elif mode == "SECTION":
        ax = (cutaway or {}).get("axis") if isinstance(cutaway, dict) else None
        po = (cutaway or {}).get("position_m") if isinstance(cutaway, dict) else None
        scene["drawing"] = section_view(arch, ax or "x", po, bid)
    elif mode == "ELEVATION":
        fc = (cutaway or {}).get("face") if isinstance(cutaway, dict) else None
        scene["drawing"] = elevation_view(arch, fc or "NORTH", bid)
    else:
        scene["drawing"] = None
    if mode in ORTHOGRAPHIC_MODES:
        scene["active_camera"] = "SECTION" if mode == "SECTION" else (
            "ELEVATION" if mode == "ELEVATION" else "TOP")
    scene["counts"] = _counts(scene)
    scene["summary"] = summary(scene)
    return scene


def _counts(scene):
    objs = scene.get("objects") or []
    by_layer, by_kind = {}, {}
    for o in objs:
        by_layer[o["layer"]] = by_layer.get(o["layer"], 0) + 1
        by_kind[o["kind"]] = by_kind.get(o["kind"], 0) + 1
    return {"objects": len(objs),
            "semantic_objects": sum(1 for o in objs if o["semantic"]),
            "visual_only_objects": sum(1 for o in objs if o["visual_only"]),
            "decoration_objects": sum(1 for o in objs if o.get("visual_class")
                                      == DECORATION_CLASS),
            "entourage_objects": sum(1 for o in objs if o.get("visual_class")
                                     == ENTOURAGE_CLASS),
            "landscape_objects": sum(1 for o in objs if o.get("visual_class")
                                     == LANDSCAPE_CLASS),
            "by_layer": by_layer, "by_kind": by_kind,
            "materials": len(scene.get("materials") or []),
            "lights": len(scene.get("lights") or []),
            "cameras": len(scene.get("cameras") or []),
            "display_fallback_objects": sum(1 for o in objs
                                            if o["geometry_source"] == "display_fallback")}


# ------------------------------------------------- المسقط ثنائي الأبعاد ---
def floor_plan(arch, level_index=0, style="TECHNICAL", building_id="bld_0"):
    """مسقط مشتقّ من الهندسة المعمارية نفسها. لا ادّعاء CAD ولا قياس مُختلق."""
    style = _style(style)
    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "kind": "FLOOR_PLAN_2D",
           "building_id": building_id, "level_index": level_index, "style": style,
           "walls": [], "openings": [], "spaces": [], "stairs": [], "fixtures": [],
           "dimensions": [], "extent": None,
           "note": "a derived drawing projected from the same architectural geometry as the "
                   "3D view; it makes no CAD-grade claim"}
    if not arch:
        return out
    lv = None
    for l in arch.get("levels") or []:
        if l["index"] == level_index:
            lv = l
    if lv is None:
        out["level_exists"] = False
        return out
    out["level_exists"] = True
    out["level_id"] = lv["id"]
    out["level_name"] = lv.get("name")

    for w in sorted((arch.get("walls") or []), key=lambda x: str(x["id"])):
        if w["level_index"] != level_index:
            continue
        t, ts = _val(w["thickness_m"])
        out["walls"].append({"id": w["id"],
                             "x1": _q(w["start"]["x"]), "z1": _q(w["start"]["z"]),
                             "x2": _q(w["end"]["x"]), "z2": _q(w["end"]["z"]),
                             "thickness_m": None if t is None else _q(t),
                             "thickness_source": ts,
                             "length_m": _q(w["length_m"]),
                             "exposure": w["exposure"]})
    for o in sorted((arch.get("openings") or []), key=lambda x: str(x["id"])):
        if o.get("level_index") != level_index:
            continue
        wdt, ws = _val(o["width_m"])
        if o["axis"] == "x":
            x1, z1 = (o["u_center"] - (wdt or 0) / 2.0), o["fixed"]
            x2, z2 = (o["u_center"] + (wdt or 0) / 2.0), o["fixed"]
        else:
            x1, z1 = o["fixed"], (o["u_center"] - (wdt or 0) / 2.0)
            x2, z2 = o["fixed"], (o["u_center"] + (wdt or 0) / 2.0)
        out["openings"].append({"id": o["id"], "type": o["type"],
                                "x1": _q(x1), "z1": _q(z1), "x2": _q(x2), "z2": _q(z2),
                                "width_m": None if wdt is None else _q(wdt),
                                "width_source": ws,
                                "host_wall_id": o.get("host_wall_id"),
                                "swing_direction": o.get("swing_direction"),
                                "swing_status": o.get("swing_status")})
    for s in sorted((arch.get("spaces") or []), key=lambda x: str(x["id"])):
        if s["level_index"] != level_index:
            continue
        r = s["rect"]
        out["spaces"].append({"id": s["id"], "space_id": s.get("space_id"),
                              "name": s.get("name"),
                              "x": _q(r[0]), "z": _q(r[1]), "w": _q(r[2]), "d": _q(r[3]),
                              "area_m2": _q(s["area_m2"]),
                              "boundary_basis": s["boundary_basis"],
                              "label_x": _q(r[0] + r[2] / 2.0), "label_z": _q(r[1] + r[3] / 2.0)})
        out["dimensions"].append({"subject": s["id"], "kind": "space_width",
                                  "value_m": _q(r[2]), "source": "model"})
        out["dimensions"].append({"subject": s["id"], "kind": "space_depth",
                                  "value_m": _q(r[3]), "source": "model"})
    for c in sorted((arch.get("cores") or []), key=lambda x: str(x["id"])):
        if level_index not in (c.get("served_levels") or []):
            continue
        fw, fws = _val(c["footprint_w_m"])
        fd, fds = _val(c["footprint_d_m"])
        out["stairs"].append({"id": c["id"], "type": c["type"],
                              "x": _q(c["x"]), "z": _q(c["z"]),
                              "w": None if fw is None else _q(fw),
                              "d": None if fd is None else _q(fd),
                              "w_source": fws, "d_source": fds})
    for w in out["walls"]:
        out["dimensions"].append({"subject": w["id"], "kind": "wall_length",
                                  "value_m": w["length_m"], "source": "model"})
    for o in out["openings"]:
        out["dimensions"].append({"subject": o["id"], "kind": "opening_width",
                                  "value_m": o["width_m"],
                                  "source": "model" if o["width_source"] == "model"
                                  else "unknown"})
    xs = [v for w in out["walls"] for v in (w["x1"], w["x2"])]
    zs = [v for w in out["walls"] for v in (w["z1"], w["z2"])]
    if xs and zs:
        out["extent"] = [_q(min(xs)), _q(min(zs)), _q(max(xs)), _q(max(zs))]
    out["dimensions"].sort(key=lambda d: (str(d["kind"]), str(d["subject"])))
    out["counts"] = {"walls": len(out["walls"]), "openings": len(out["openings"]),
                     "spaces": len(out["spaces"]), "stairs": len(out["stairs"]),
                     "dimensions": len(out["dimensions"]),
                     "unknown_dimensions": sum(1 for d in out["dimensions"]
                                               if d["source"] != "model")}
    return out


# --------------------------------------------------------- القطاع --------
def section_view(arch, axis="x", position_m=None, building_id="bld_0"):
    """قطاع معماري على مستوى مذكور. بلا أي تفسير إنشائي أو كودي."""
    axis = str(axis or "x").lower()
    if axis not in SECTION_AXES:
        axis = "x"
    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "kind": "SECTION",
           "building_id": building_id, "axis": axis, "position_m": None,
           "levels": [], "slabs": [], "walls": [], "openings": [], "stairs": [],
           "note": "an orthographic cut of the same architectural geometry; no structural "
                   "or code interpretation is made"}
    if not arch:
        return out
    walls = arch.get("walls") or []
    # الافتراضي: منتصف مسطح المبنى على المحور العرضي — قطع يمرّ بالمبنى فعلاً
    if position_m is None:
        outs = [s["outline"] for s in (arch.get("slabs") or []) if s.get("outline")]
        if outs:
            lo = min((o[1] if axis == "x" else o[0]) for o in outs)
            hi = max((o[1] + o[3]) if axis == "x" else (o[0] + o[2]) for o in outs)
            position_m = (lo + hi) / 2.0
        else:
            position_m = 0.0
    pos = float(position_m)
    out["position_m"] = _q(pos)
    for l in sorted((arch.get("levels") or []), key=lambda x: x["index"]):
        out["levels"].append({"id": l["id"], "index": l["index"], "name": l.get("name"),
                              "elevation_m": None if l["elevation_m"] is None
                              else _q(l["elevation_m"]),
                              "elevation_source": l["elevation_source"]})
    lv = {l["index"]: l for l in arch.get("levels") or []}
    for s in sorted((arch.get("slabs") or []), key=lambda x: str(x["id"])):
        o = s["outline"]
        if not o or s["elevation_m"] is None:
            continue
        lo = o[0] if axis == "x" else o[1]
        hi = lo + (o[2] if axis == "x" else o[3])
        cut_lo = o[1] if axis == "x" else o[0]
        cut_hi = cut_lo + (o[3] if axis == "x" else o[2])
        if not (cut_lo - _EPS <= pos <= cut_hi + _EPS):
            continue
        t, ts = _val(s["thickness_m"])
        out["slabs"].append({"id": s["id"], "level_index": s["level_index"],
                             "u0": _q(lo), "u1": _q(hi),
                             "y0": _q(s["elevation_m"] - (t or 0.0)),
                             "y1": _q(s["elevation_m"]),
                             "thickness_m": None if t is None else _q(t),
                             "thickness_source": ts})
    # مستوى القطع عمودي على المحور الآخر عند pos، والرسم الأفقي على المحور axis.
    # الجدار الممتد عبر المستوى يُقطَع، والجدار الواقع داخل المستوى يُرى في وجهه.
    for w in sorted(walls, key=lambda x: str(x["id"])):
        h, hs = _val(w["height_m"])
        t = _val(w["thickness_m"])[0] or 0.2
        base = (lv.get(w["level_index"]) or {}).get("elevation_m")
        if h is None or base is None:
            continue
        if w["axis"] == axis:
            # يمتد على محور الرسم: يقع داخل المستوى فقط إن كان fixed عند pos
            if abs(w["fixed"] - pos) > t / 2.0 + _EPS:
                continue
            u0, u1, cut = w["u0"], w["u1"], True
        else:
            # يعبر المستوى: يُقطَع إن احتوى امتداده موضع القطع
            if not (min(w["u0"], w["u1"]) - _EPS <= pos <= max(w["u0"], w["u1"]) + _EPS):
                continue
            u0, u1, cut = w["fixed"] - t / 2.0, w["fixed"] + t / 2.0, True
        out["walls"].append({"id": w["id"], "level_index": w["level_index"],
                             "u0": _q(u0), "u1": _q(u1),
                             "y0": _q(base), "y1": _q(base + h),
                             "cut": cut, "height_source": hs})
    for o in sorted((arch.get("openings") or []), key=lambda x: str(x["id"])):
        wdt, ws = _val(o["width_m"])
        hgt, hs = _val(o["height_m"])
        base = (lv.get(o.get("level_index")) or {}).get("elevation_m")
        if wdt is None or hgt is None or base is None:
            continue
        if o["axis"] == axis:
            if abs(o["fixed"] - pos) > 0.35:
                continue
            u0, u1 = o["u_center"] - wdt / 2.0, o["u_center"] + wdt / 2.0
        else:
            if not (o["u_center"] - wdt / 2.0 - _EPS <= pos
                    <= o["u_center"] + wdt / 2.0 + _EPS):
                continue
            u0, u1 = o["fixed"] - 0.1, o["fixed"] + 0.1
        sill = _val(o["sill_m"])[0] if o["type"] == "WINDOW" else 0.0
        sill = sill if sill is not None else 0.0
        out["openings"].append({"id": o["id"], "type": o["type"],
                                "u0": _q(u0), "u1": _q(u1),
                                "y0": _q(base + sill), "y1": _q(base + sill + hgt),
                                "width_source": ws, "height_source": hs})
    for c in sorted((arch.get("cores") or []), key=lambda x: str(x["id"])):
        fw, _a = _val(c["footprint_w_m"])
        fd, _b = _val(c["footprint_d_m"])
        served = c.get("served_levels") or []
        if fw is None or fd is None or not served:
            continue
        half = (fd if axis == "x" else fw) / 2.0
        centre_cross = c["z"] if axis == "x" else c["x"]
        if abs(centre_cross - pos) > half + _EPS:
            continue
        base = (lv.get(min(served)) or {}).get("elevation_m")
        top = (lv.get(max(served)) or {}).get("elevation_m")
        if base is None or top is None:
            continue
        u = c["x"] if axis == "x" else c["z"]
        half_u = (fw if axis == "x" else fd) / 2.0
        out["stairs"].append({"id": c["id"], "type": c["type"],
                              "u0": _q(u - half_u), "u1": _q(u + half_u),
                              "y0": _q(base), "y1": _q(top)})
    out["counts"] = {"levels": len(out["levels"]), "slabs": len(out["slabs"]),
                     "walls": len(out["walls"]), "openings": len(out["openings"]),
                     "stairs": len(out["stairs"])}
    return out


# ------------------------------------------------------- الواجهة ---------
_FACE_AXIS = {"NORTH": ("z", "min", "x"), "SOUTH": ("z", "max", "x"),
              "WEST": ("x", "min", "z"), "EAST": ("x", "max", "z")}


def elevation_view(arch, face="NORTH", building_id="bld_0"):
    """واجهة مسقطة من الغلاف الفعلي وفتحاته الفعلية. لا فتحة تُختلق."""
    face = str(face or "NORTH").upper()
    if face not in ELEVATION_FACES:
        face = "NORTH"
    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "kind": "ELEVATION",
           "building_id": building_id, "face": face,
           "walls": [], "openings": [], "levels": [], "outline": None,
           "note": "the real envelope and its real openings are projected; no opening is "
                   "ever added to balance a facade"}
    if not arch:
        return out
    env = arch.get("envelope") or {}
    ext = set(env.get("exterior_walls") or [])
    lv = {l["index"]: l for l in arch.get("levels") or []}
    axis, side, u_axis = _FACE_AXIS[face]
    cand = [w for w in (arch.get("walls") or [])
            if w["id"] in ext and w["axis"] != axis]
    if not cand:
        cand = [w for w in (arch.get("walls") or []) if w["axis"] != axis]
    if not cand:
        return out
    fixed_vals = [w["fixed"] for w in cand]
    target = min(fixed_vals) if side == "min" else max(fixed_vals)
    picked = [w for w in cand if abs(w["fixed"] - target) <= 0.6]
    ids = {w["id"] for w in picked}
    for l in sorted((arch.get("levels") or []), key=lambda x: x["index"]):
        out["levels"].append({"id": l["id"], "index": l["index"],
                              "elevation_m": None if l["elevation_m"] is None
                              else _q(l["elevation_m"])})
    ys = []
    for w in sorted(picked, key=lambda x: str(x["id"])):
        h, hs = _val(w["height_m"])
        base = (lv.get(w["level_index"]) or {}).get("elevation_m")
        if h is None or base is None:
            continue
        out["walls"].append({"id": w["id"], "level_index": w["level_index"],
                             "u0": _q(w["u0"]), "u1": _q(w["u1"]),
                             "y0": _q(base), "y1": _q(base + h),
                             "height_source": hs})
        ys.extend([base, base + h])
    for o in sorted((arch.get("openings") or []), key=lambda x: str(x["id"])):
        if o.get("host_wall_id") not in ids:
            continue
        wdt, ws = _val(o["width_m"])
        hgt, hs = _val(o["height_m"])
        base = (lv.get(o.get("level_index")) or {}).get("elevation_m")
        if wdt is None or hgt is None or base is None:
            continue
        sill = _val(o["sill_m"])[0] if o["type"] == "WINDOW" else 0.0
        sill = sill if sill is not None else 0.0
        out["openings"].append({"id": o["id"], "type": o["type"],
                                "u0": _q(o["u_center"] - wdt / 2.0),
                                "u1": _q(o["u_center"] + wdt / 2.0),
                                "y0": _q(base + sill), "y1": _q(base + sill + hgt),
                                "host_wall_id": o["host_wall_id"],
                                "width_source": ws, "height_source": hs})
    us = [v for w in out["walls"] for v in (w["u0"], w["u1"])]
    if us and ys:
        out["outline"] = [_q(min(us)), _q(min(ys)), _q(max(us)), _q(max(ys))]
    out["counts"] = {"walls": len(out["walls"]), "openings": len(out["openings"]),
                     "levels": len(out["levels"])}
    return out


# ----------------------------------------------- الأداء: التكرار والتفاصيل -
def instancing_plan(scene):
    """مرشّحو التكرار من الأجسام البصرية فقط — لا يُدمَج عنصر مُنمذَج أبداً."""
    groups = {}
    for o in scene.get("objects") or []:
        if not o.get("visual_only") or not o.get("instance_key"):
            continue
        g = groups.setdefault(o["instance_key"], {"instance_key": o["instance_key"],
                                                  "asset_id": o.get("asset_id"),
                                                  "material": o["material"],
                                                  "count": 0, "object_ids": []})
        g["count"] += 1
        g["object_ids"].append(o["id"])
    out = [dict(g, object_ids=sorted(g["object_ids"])) for g in groups.values()
           if g["count"] > 1]
    out.sort(key=lambda g: str(g["instance_key"]))
    return {"groups": out,
            "instanced_objects": sum(g["count"] for g in out),
            "modelled_objects_merged": 0,
            "note": "only visual-only objects are instanced; merging a modelled element "
                    "would destroy per-element selection and traceability"}


def lod_plan(scene, budget=None):
    """خطة تفاصيل: يُخفَّض البصريّ أوّلاً، ولا يُسقَط عنصر مُنمذَج في العرض الهندسي."""
    objs = scene.get("objects") or []
    q = (scene.get("presentation") or {}).get("quality_params") or {}
    cap = int(budget if budget is not None else q.get("max_visual_objects") or 12000)
    eng = scene.get("mode") in ENGINEERING_MODES
    plan, dropped, simplified = [], 0, 0
    visual = [o for o in objs if o.get("visual_only")]
    modelled = [o for o in objs if not o.get("visual_only")]
    over = max(0, len(objs) - cap)
    drop_ids = set()
    if over > 0:
        for o in sorted(visual, key=lambda x: str(x["id"]))[::-1][:over]:
            drop_ids.add(o["id"])
    for o in objs:
        if o["id"] in drop_ids:
            plan.append({"id": o["id"], "lod": "MASSING", "emitted": False,
                         "reason": "visual-only object beyond the quality budget"})
            dropped += 1
        elif o.get("visual_only") and len(objs) > cap * 0.8:
            plan.append({"id": o["id"], "lod": "SIMPLIFIED", "emitted": True,
                         "reason": "visual-only object simplified near the budget"})
            simplified += 1
        else:
            plan.append({"id": o["id"], "lod": "FULL", "emitted": True, "reason": None})
    plan.sort(key=lambda e: str(e["id"]))
    return {"budget": cap, "objects": len(objs), "modelled_objects": len(modelled),
            "visual_only_objects": len(visual),
            "dropped_visual_only": dropped, "simplified_visual_only": simplified,
            "dropped_modelled": 0, "engineering_mode": bool(eng), "plan": plan,
            "note": "a modelled architectural, structural, MEP or fire element is never "
                    "removed by LOD; only visual-only detail degrades"}


# --------------------------------------------------- اللقطة وبياناتها ----
def snapshot_request(scene, width=None, height=None, fmt=None, quality=None,
                     transparent=None, camera=None):
    """طلب لقطة عالية الدقة — وصف قابل للتحقّق، والتنفيذ في المتصفّح."""
    w = int(_num(width) or SNAPSHOT_DEFAULTS["width"])
    h = int(_num(height) or SNAPSHOT_DEFAULTS["height"])
    issues = []
    if w <= 0 or h <= 0:
        issues.append("SNAPSHOT_DIMENSIONS_INVALID")
        w, h = SNAPSHOT_DEFAULTS["width"], SNAPSHOT_DEFAULTS["height"]
    if w * h > SNAPSHOT_MAX_PX:
        issues.append("SNAPSHOT_EXCEEDS_MAX_PIXELS")
        scale = math.sqrt(float(SNAPSHOT_MAX_PX) / float(w * h))
        w, h = max(1, int(w * scale)), max(1, int(h * scale))
    f = str(fmt or SNAPSHOT_DEFAULTS["format"]).upper()
    if f not in SNAPSHOT_FORMATS:
        issues.append("SNAPSHOT_FORMAT_UNSUPPORTED")
        f = SNAPSHOT_DEFAULTS["format"]
    cam = str(camera or scene.get("active_camera") or "EXTERIOR_CORNER").upper()
    if cam not in CAMERA_PRESETS:
        issues.append("SNAPSHOT_CAMERA_UNKNOWN")
        cam = "EXTERIOR_CORNER"
    q = _num(quality)
    q = SNAPSHOT_DEFAULTS["quality"] if q is None else min(max(q, 0.1), 1.0)
    return {"width": w, "height": h, "format": f, "quality": _q(q),
            "transparent": bool(SNAPSHOT_DEFAULTS["transparent"] if transparent is None
                                else transparent),
            "camera": cam, "mode": scene.get("mode"),
            "issues": sorted(issues),
            "note": "a snapshot is an image of the deterministic scene; it carries the "
                    "model hash it was produced from"}


def render_metadata(scene, request=None, kind="DETERMINISTIC_RENDER", at=None,
                    ai=None):
    """بيانات تتبّع كل صورة — بصمة النموذج والوضع والسمة والكاميرا والإضاءة."""
    kind = str(kind or "DETERMINISTIC_RENDER").upper()
    if kind not in RENDER_KINDS:
        kind = "DETERMINISTIC_RENDER"
    req = request or snapshot_request(scene)
    pres = scene.get("presentation") or {}
    body = {"model_hash": scene.get("model_hash"), "building_id": scene.get("building_id"),
            "scene_id": scene.get("scene_id"),
            "visual_mode": scene.get("mode"), "camera": req.get("camera"),
            "theme": pres.get("theme"), "material_preset": pres.get("theme"),
            "lighting_preset": pres.get("lighting_preset"),
            "quality": pres.get("quality"),
            "width": req.get("width"), "height": req.get("height"),
            "format": req.get("format"), "kind": kind,
            "compiler_version": COMPILER_VERSION}
    meta = dict(body)
    meta["render_id"] = "vrender_" + _sha16(body)
    meta["created_at"] = at
    meta["authority"] = RENDER_AUTHORITY[kind]
    meta["is_engineering_model"] = kind == "DETERMINISTIC_RENDER"
    meta["ai_enhanced"] = kind == "AI_ENHANCED_VISUALISATION"
    if meta["ai_enhanced"]:
        meta["ai"] = ai or {}
        meta["note"] = ("AI-enhanced VISUALISATION — appearance only. It is not the "
                        "engineering model, it is not as-built, and no geometry in it is "
                        "authoritative")
    else:
        meta["note"] = ("deterministic render of the compiled geometry; it depicts the "
                        "model at the stated model hash and nothing else")
    return meta


def check_render_currency(render_meta, building, building_id="bld_0"):
    """هل الصورة ما زالت تمثّل النموذج الحالي؟ القِدَم يُعلَن ولا يُخفى."""
    try:
        now = REV.model_hash(building or {}, "building", building_id or "bld_0")
    except Exception:
        return {"status": "UNVERIFIABLE", "presented_as_current": False,
                "reason": "the model hash could not be computed"}
    stored = (render_meta or {}).get("model_hash")
    if stored is None:
        return {"status": "UNVERIFIABLE", "presented_as_current": False,
                "reason": "the render carries no model hash"}
    if stored != now:
        return {"status": "STALE_MODEL_CHANGED", "stored_hash": stored, "current_hash": now,
                "presented_as_current": False,
                "reason": "the building changed after this render; the image remains "
                          "historical and is not relabelled current"}
    return {"status": "CURRENT", "stored_hash": stored, "current_hash": now,
            "presented_as_current": True}


# --------------------------------------------- ممرات التحكّم والذكاء ------
def control_buffers(scene, kinds=None):
    """أوصاف ممرّات تحكّم حتمية من الهندسة الحقيقية — لا تحسين بذاتها."""
    want = [k for k in (kinds or CONTROL_BUFFERS) if k in CONTROL_BUFFERS]
    objs = scene.get("objects") or []
    ids = [o["id"] for o in objs if not o.get("visual_only")]
    rooms = sorted({o.get("space_id") for o in objs if o.get("space_id")})
    out = []
    for k in sorted(want):
        entry = {"kind": k, "deterministic": True, "from_model": True,
                 "source_scene": scene.get("scene_id"),
                 "note": "a deterministic pass over the compiled geometry"}
        if k == "object_id":
            entry["ids"] = sorted(ids)
            entry["count"] = len(ids)
        elif k == "room_id":
            entry["ids"] = rooms
            entry["count"] = len(rooms)
        elif k == "semantic_mask":
            entry["classes"] = sorted({o["kind"] for o in objs if not o.get("visual_only")})
            entry["count"] = len(entry["classes"])
        else:
            entry["count"] = len(objs)
        out.append(entry)
    return {"scene_id": scene.get("scene_id"), "model_hash": scene.get("model_hash"),
            "buffers": out, "available": sorted(want),
            "note": SPEC["control_buffer_note"]}


def geometry_signature(scene, arch=None):
    """بصمة السمات التي يُمنع على الذكاء الاصطناعي تغييرها — أساس كشف الانحراف."""
    objs = scene.get("objects") or []
    b = scene.get("bounds") or [0, 0, 0, 0, 0, 0]
    lvl = set()
    for o in objs:
        if o.get("level_index") is not None:
            lvl.add(o["level_index"])
    if arch:
        lvl = {l["index"] for l in arch.get("levels") or []}
    rooms = len({o.get("space_id") for o in objs if o.get("space_id")})
    if arch:
        rooms = len(arch.get("spaces") or [])
    return {"door_count": sum(1 for o in objs if o["kind"] == "DOOR"),
            "window_count": sum(1 for o in objs if o["kind"] == "WINDOW"),
            "wall_count": sum(1 for o in objs if o["kind"] == "WALL"),
            "stair_count": sum(1 for o in objs if o["kind"] == "STAIR"),
            "floor_count": len(lvl), "room_count": rooms,
            "footprint": [_q(b[0]), _q(b[2]), _q(b[3]), _q(b[5])],
            "model_hash": scene.get("model_hash")}


def ai_enhancement_request(scene, prompt=None, buffers=None, strength=0.35, arch=None):
    """واجهة تحسين بصريّ. لا تولّد صورة ولا تتّصل بشبكة ولا تملك أي مسار كتابة."""
    st = _num(strength)
    st = 0.35 if st is None else min(max(st, 0.0), 1.0)
    cb = control_buffers(scene, buffers)
    # كل ممرّ مطلوب يسافر مع واصفه الحتميّ، لا باسمه وحده. لا بكسل يُولَّد هنا.
    descriptors = {}
    for b in cb["buffers"]:
        descriptors[b["kind"]] = dict(b)
    return {"stage_pipeline": list(AI_STAGES),
            "scene_id": scene.get("scene_id"), "model_hash": scene.get("model_hash"),
            "building_id": scene.get("building_id"),
            "base_render_required": True,
            "requested_control_buffers": list(cb["available"]),
            "control_buffers": descriptors,
            "geometry_signature": geometry_signature(scene, arch),
            "prompt": None if prompt is None else str(prompt),
            "strength": _q(st),
            "may_change": list(AI_MAY_CHANGE),
            "may_not_change": list(AI_MAY_NOT_CHANGE),
            "writes_to_model": False,
            "generator_shipped": False,
            "network_call": False,
            "authority": RENDER_AUTHORITY["AI_ENHANCED_VISUALISATION"],
            "note": SPEC["ai_note"]}


def _requested_buffers(request):
    """أسماء الممرّات المطلوبة سواء وردت كخريطة واصفات أو كقائمة أسماء."""
    r = request or {}
    names = r.get("requested_control_buffers")
    if isinstance(names, (list, tuple)):
        return list(names)
    cb = r.get("control_buffers")
    if isinstance(cb, dict):
        return sorted(cb.keys())
    if isinstance(cb, (list, tuple)):
        return list(cb)
    return []


def check_visual_consistency(request, reported, tolerance_m=0.5):
    """يقارن ما تدّعيه صورة محسّنة بما ينصّ عليه النموذج. لا يكتب في النموذج أبداً."""
    sig = (request or {}).get("geometry_signature") or {}
    rep = reported or {}
    findings = []

    def add(code, subject, expected, observed):
        findings.append({"code": code, "severity": DRIFT_CODE_SEVERITY[code],
                         "subject": subject, "expected": expected, "observed": observed,
                         "writes_to_model": False,
                         "note": "the image disagrees with the model it claims to depict; "
                                 "the model is never rewritten and the image is never "
                                 "accepted as geometry"})

    for key, subject in (("door_count", "doors"), ("window_count", "windows"),
                         ("floor_count", "levels"), ("room_count", "rooms"),
                         ("stair_count", "stairs"), ("wall_count", "walls")):
        if key not in rep:
            continue
        exp, obs = sig.get(key), rep.get(key)
        if exp is None or obs is None or exp == obs:
            continue
        code = ("VISUAL_LEVEL_COUNT_MISMATCH" if key == "floor_count"
                else "VISUAL_FEATURE_COUNT_MISMATCH")
        add(code, subject, exp, obs)
    if "footprint" in rep and sig.get("footprint"):
        exp, obs = sig["footprint"], rep["footprint"]
        try:
            if len(obs) == 4 and any(abs(float(obs[i]) - float(exp[i])) > float(tolerance_m)
                                     for i in range(4)):
                add("VISUAL_FOOTPRINT_MISMATCH", "footprint", exp, obs)
        except (TypeError, ValueError):
            add("VISUAL_FOOTPRINT_MISMATCH", "footprint", exp, obs)
    if "model_hash" in rep and sig.get("model_hash") and rep["model_hash"] != sig["model_hash"]:
        add("VISUAL_SOURCE_HASH_MISMATCH", "model_hash", sig["model_hash"], rep["model_hash"])
    if not _requested_buffers(request):
        add("VISUAL_CONTROL_BUFFER_MISSING", "control_buffers", ">=1", 0)
    # طلب بلا بصمة هندسية ليس طلباً مقيَّداً: يُرفض ولا يُمرَّر بصمت
    if not sig:
        add("VISUAL_SIGNATURE_MISSING", "geometry_signature",
            "a geometry signature is required to constrain an AI enhancement", None)
    findings.sort(key=lambda f: (DRIFT_SEVERITIES.index(f["severity"]), str(f["code"]),
                                 str(f["subject"])))
    if findings:
        findings.insert(0, {"code": "VISUAL_GEOMETRY_DRIFT",
                            "severity": DRIFT_CODE_SEVERITY["VISUAL_GEOMETRY_DRIFT"],
                            "subject": "scene", "expected": "image matches the model",
                            "observed": "%d inconsistency(ies)" % len(findings),
                            "writes_to_model": False,
                            "note": "major layout features in the image are inconsistent "
                                    "with the model; the image is not authoritative geometry"})
    return {"drift": bool(findings), "findings": findings,
            "model_modified": False, "image_accepted_as_geometry": False,
            "authority": RENDER_AUTHORITY["AI_ENHANCED_VISUALISATION"],
            "note": SPEC["drift_note"]}


# ------------------------------------------------------- تصدير وخدمات ----
def presentation_block(scene):
    """كتلة إضافية منفصلة — لا تُدمَج في JSON الهندسي ولا تدخل بصمة المراجعة."""
    pres = scene.get("presentation") or {}
    return {PRESENTATION_BLOCK_KEY: {
        "schema": SCHEMA, "compiler_version": COMPILER_VERSION,
        "building_id": scene.get("building_id"), "model_hash": scene.get("model_hash"),
        "mode": scene.get("mode"), "theme": pres.get("theme"),
        "lighting_preset": pres.get("lighting_preset"), "quality": pres.get("quality"),
        "layers": pres.get("layers"), "active_camera": scene.get("active_camera"),
        "scale": pres.get("scale"),
        "derived": True, "affects_revision_hash": False,
        "note": "an additive presentation block; engineering JSON is never polluted with "
                "visual scene state and no visual value enters a revision hash"}}


def export_scene(scene, presentation_glb=False):
    """تصدير صريح للمشهد البصري. لا يستبدل تصدير GLB الهندسي ولا يغيّر دلالته."""
    objs = scene.get("objects") or []
    keep = objs if presentation_glb else [o for o in objs if not o.get("visual_only")]
    return {"schema": SCHEMA, "compiler_version": COMPILER_VERSION,
            "kind": "PRESENTATION_GLB" if presentation_glb else "ENGINEERING_GLB",
            "building_id": scene.get("building_id"), "model_hash": scene.get("model_hash"),
            "scene_id": scene.get("scene_id"), "mode": scene.get("mode"),
            "objects": [{"id": o["id"], "kind": o["kind"], "layer": o["layer"],
                         "semantic": o["semantic"], "visual_only": o["visual_only"],
                         "source_element_id": o.get("source_element_id"),
                         "material": o["material"],
                         "material_provenance": o["material_provenance"],
                         "geometry": o["geometry"]} for o in keep],
            "includes_visual_only": bool(presentation_glb),
            "derived": True,
            "note": "the engineering export keeps its semantics; a presentation export is "
                    "separate, explicitly requested, and never replaces it"}


def object_by_id(scene, oid):
    for o in scene.get("objects") or []:
        if o["id"] == oid:
            return o
    return None


def objects_by_layer(scene, layer):
    return [o for o in scene.get("objects") or [] if o["layer"] == layer]


def set_layer_visible(scene, layer, on):
    """تبديل رؤية طبقة — حالة عرض بحتة. العرض الهندسي لا يخفي تخصّصاً."""
    layer = str(layer or "").upper()
    if layer not in VISUAL_LAYERS:
        return (False, "LAYER_UNKNOWN", None)
    if scene.get("mode") in ENGINEERING_MODES and not on and \
       layer in ("ARCHITECTURE", "STRUCTURE", "MEP", "FLS"):
        return (False, "ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE", None)
    scene["presentation"]["layer_visibility"][layer] = bool(on)
    for o in scene.get("objects") or []:
        if o["layer"] == layer:
            o["visible"] = bool(on)
    return (True, None, scene["presentation"]["layer_visibility"])


def validate_scene(scene):
    """فحوص نزاهة المشهد: تصنيف المواد، فصل الديكور، غياب أي ادّعاء ممنوع."""
    issues = []
    for m in scene.get("materials") or []:
        if m.get("material_class") != MATERIAL_CLASS:
            issues.append({"code": "MATERIAL_NOT_VISUAL_CLASS", "subject": m.get("id")})
        if m.get("fire_rating") is not None or m.get("thermal_property") is not None \
           or m.get("structural_material"):
            issues.append({"code": "MATERIAL_CARRIES_ENGINEERING_PROPERTY",
                           "subject": m.get("id")})
    for o in scene.get("objects") or []:
        if o.get("visual_only") and o.get("semantic"):
            issues.append({"code": "VISUAL_OBJECT_MARKED_SEMANTIC", "subject": o["id"]})
        # قاعدة المصدر متناظرة وشاملة: لا تعتمد على التصنيف ولا المادة ولا السمة
        # ولا الأصل ولا مستوى التفاصيل ولا التخصّص ولا فئة الديكور.
        if o.get("visual_only"):
            if o.get("source_element_id") is not None:
                issues.append({"code": "VISUAL_ONLY_OBJECT_WITH_SOURCE", "subject": o["id"]})
                # تخصيص إضافي للديكور — يُبلَّغ فوق القاعدة العامة لا بدلاً منها
                if o.get("visual_class") == DECORATION_CLASS:
                    issues.append({"code": "DECORATION_LINKED_TO_MODEL_ELEMENT",
                                   "subject": o["id"]})
        elif not o.get("source_element_id"):
            issues.append({"code": "MODELLED_OBJECT_WITHOUT_SOURCE", "subject": o["id"]})
        if o.get("material") not in MATERIALS:
            issues.append({"code": "MATERIAL_NOT_IN_LIBRARY", "subject": o["id"]})
        if o.get("material_provenance") not in MATERIAL_PROVENANCE:
            issues.append({"code": "MATERIAL_PROVENANCE_INVALID", "subject": o["id"]})
    issues.sort(key=lambda i: (str(i["code"]), str(i["subject"])))
    return issues


def rule_inputs(scene):
    c = scene.get("counts") or _counts(scene)
    return {"building": {"visual.scene.object_count": c["objects"],
                         "visual.scene.visual_only_count": c["visual_only_objects"],
                         "visual.scene.mode": scene.get("mode"),
                         "visual.render.exists": bool(scene.get("scene_id"))}}


def summary(scene):
    c = scene.get("counts") or _counts(scene)
    pres = scene.get("presentation") or {}
    return {"compiler_version": COMPILER_VERSION, "building_id": scene.get("building_id"),
            "model_hash": scene.get("model_hash"), "scene_id": scene.get("scene_id"),
            "mode": scene.get("mode"), "theme": pres.get("theme"),
            "lighting_preset": pres.get("lighting_preset"), "quality": pres.get("quality"),
            "layers": pres.get("layers"),
            "objects": c["objects"], "semantic_objects": c["semantic_objects"],
            "visual_only_objects": c["visual_only_objects"],
            "decoration_objects": c["decoration_objects"],
            "entourage_objects": c["entourage_objects"],
            "landscape_objects": c["landscape_objects"],
            "materials": c["materials"], "lights": c["lights"], "cameras": c["cameras"],
            "display_fallback_objects": c["display_fallback_objects"],
            "engineering_geometry_modified": False,
            "compliance": "NOT_EVALUATED",
            "note": "geometry-preserving visualisation only — no engineering mutation, no "
                    "AI geometry, and visual decoration is never engineering data"}
