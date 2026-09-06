# -*- coding: utf-8 -*-
"""طبقة التوثيق الإنشائي — المرحلة 9.

تحوّل النموذج القانوني إلى مناظر ومقاسات وتأشيرات وجداول وكمّيات ولوحات
ومخرجات متّجهة، دون أن تكتب إليه ودون أن تخترع فيه شيئاً.

المبدأ الذي يحكم الملفّ كلّه: الطبقات القانونية تحمل القيمة مع مصدرها ومع
render_fallback منفصل للعرض. التوثيق يقرأ القيمة المعلَنة وحدها. القيمة الغائبة
تُوثَّق مجهولةً، ولا تُستبدل ببديل العرض أبداً.
"""
import json
import math
import os

import acs_ingest as ING
import acs_polygon as POLY

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_docs.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
COMPILER = SPEC["compiler_version"]
LIMITS = SPEC["limits"]
ISSUE_CODES = tuple(SPEC["issue_codes"])
BLOCKING = tuple(SPEC["blocking_issue_codes"])
UNSAFE = tuple(SPEC["unsafe_patterns"])
FORBIDDEN_KEYS = tuple(SPEC["forbidden_property_keys"])
PAPER = SPEC["paper_sizes"]
SCALES = tuple(SPEC["scales"])
VIEW_SUPPORT = {v["view_type"]: v for v in SPEC["view_support"]}
PREFIX = SPEC["id_prefixes"]
LINE_W = SPEC["line_weights"]
DISC_CATS = SPEC["discipline_categories"]

_MM_PER_M = 1000.0
_PT_PER_MM = 72.0 / 25.4


# ------------------------------------------------------------------ أدوات ----
def _q(v):
    return round(float(v), 6) + 0.0


def _num(v):
    """رقم منتهٍ أو None. لا NaN ولا لانهاية تدخل رسماً."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


_canon = ING.canonical_json


def _sha16(o):
    import hashlib
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _sha256_text(t):
    import hashlib
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _scmp(a, b):
    return (a > b) - (a < b)


def issue(code, severity, element_id, message):
    if code not in ISSUE_CODES:
        raise ValueError("undeclared documentation issue code: %s" % code)
    return {"code": code, "severity": severity, "element_id": element_id,
            "message": message, "blocking": code in BLOCKING}


def is_unsafe(v):
    if not isinstance(v, str):
        return False
    low = v.lower()
    return any(p.lower() in low for p in UNSAFE)


def is_safe_id(v):
    import re
    return isinstance(v, str) and re.match(SPEC["safe_id_pattern"], v) is not None


def safe_key(k):
    """مفتاح مقبول: لا مفتاح نموذج أوّلي ولا مسار كائن."""
    if not isinstance(k, str) or not k or len(k) > 255:
        return False
    if k in FORBIDDEN_KEYS:
        return False
    return is_safe_id(k.replace(" ", "_"))


def safe_filename(name):
    """اسم ملفّ لا يخرج من مجلّده. قائمة سماح لا قائمة حظر."""
    import re
    if not isinstance(name, str) or not name:
        return None
    if len(name) > int(LIMITS["max_filename_length"]):
        return None
    if re.match(SPEC["safe_filename_pattern"], name) is None:
        return None
    stem = name.split(".")[0].upper()
    if stem in SPEC["reserved_filenames"]:
        return None
    return name


# --------------------------------------------------------- قراءة القيم ----
def stated(triple):
    """يقرأ ثلاثي {value, source, render_fallback} ويعيد القيمة المعلَنة فقط.

    هنا يعيش القانون الأهمّ في هذه المرحلة: بديل العرض لا يصير قياساً موثَّقاً.
    """
    if triple is None:
        return {"value": None, "status": "UNKNOWN", "source": None}
    if not isinstance(triple, dict):
        n = _num(triple)
        return ({"value": _q(n), "status": "STATED", "source": "literal"}
                if n is not None else {"value": None, "status": "UNKNOWN",
                                       "source": None})
    v = _num(triple.get("value"))
    src = triple.get("source")
    if v is None:
        # القيمة غير مذكورة. قد يوجد render_fallback — ولا نلمسه.
        return {"value": None, "status": "UNKNOWN", "source": src}
    return {"value": _q(v), "status": "STATED", "source": src}


def display_of(st, precision=None):
    """نصّ العرض. التقريب لا يمسّ القيمة المضبوطة إطلاقاً."""
    if st["status"] != "STATED" or st["value"] is None:
        return None
    p = int(SPEC["dimension_precision_m"] if precision is None else precision)
    return ("%." + str(p) + "f") % round(st["value"], p)


# --------------------------------------------------------------- الهوية ----
def artifact_id(kind, payload):
    if kind not in PREFIX:
        raise ValueError("undeclared artifact kind: %s" % kind)
    return PREFIX[kind] + _sha16(payload)


# --------------------------------------------------- تعريف المنظر (§6) ----
def view_definition(project, spec, arch=None):
    """يبني تعريف منظر موثَّق ويرفض ما لا يُدعم بدل أن يخفّضه بصمت."""
    issues = []
    d = spec if isinstance(spec, dict) else {}
    vt = d.get("view_type")
    if vt not in SPEC["view_types"]:
        return {"valid": False, "view": None,
                "issues": [issue("DOC_INVALID_VIEW_TYPE", "ERROR", vt,
                                 "view type is not declared")]}
    sup = VIEW_SUPPORT.get(vt, {}).get("support", "NOT_SUPPORTED")
    if sup == "NOT_SUPPORTED":
        return {"valid": False, "view": None,
                "issues": [issue("DOC_VIEW_NOT_SUPPORTED", "ERROR", vt,
                                 VIEW_SUPPORT[vt]["basis"])]}
    disc = d.get("discipline") or "ARCHITECTURE"
    if disc not in SPEC["disciplines"]:
        return {"valid": False, "view": None,
                "issues": [issue("DOC_INVALID_DISCIPLINE", "ERROR", disc,
                                 "discipline is not declared")]}
    scale = d.get("scale")
    scale_mode = "TRUE_SCALE"
    if scale in (None, "FIT_TO_SHEET"):
        scale, scale_mode = None, "FIT_TO_SHEET"
    elif scale not in SCALES:
        return {"valid": False, "view": None,
                "issues": [issue("DOC_INVALID_SCALE", "ERROR", scale,
                                 "scale is not one of the declared scales")]}
    bid = project.get("building_id") or "bld_0"
    if arch is None:
        arch = _arch_of(project)
    levels = arch["levels"]
    lid = d.get("level_id")
    if vt in ("FLOOR_PLAN", "CEILING_PLAN", "ROOF_PLAN", "STRUCTURAL_PLAN",
              "MEP_PLAN", "FLS_PLAN", "COORDINATION_PLAN"):
        if lid is None and levels:
            lid = levels[0]["id"]
        if not any(l["id"] == lid for l in levels):
            return {"valid": False, "view": None,
                    "issues": [issue("DOC_INVALID_LEVEL", "ERROR", lid,
                                     "no such level in the canonical model")]}
    orient = d.get("orientation")
    if vt == "ELEVATION":
        if orient not in SPEC["orientations"]:
            return {"valid": False, "view": None,
                    "issues": [issue("DOC_INVALID_ORIENTATION", "ERROR", orient,
                                     "elevation needs a declared orientation")]}
    cut = None
    if vt == "SECTION":
        cut = _cut_plane(d.get("cut_plane"), issues)
        if cut is None:
            return {"valid": False, "view": None,
                    "issues": issues or [issue("DOC_MALFORMED_DEFINITION", "ERROR",
                                               None, "section needs a cut plane")]}
    crop = d.get("crop_region")
    if crop is not None:
        c = [_num(x) for x in crop] if isinstance(crop, (list, tuple)) else None
        if not c or len(c) != 4 or any(x is None for x in c):
            return {"valid": False, "view": None,
                    "issues": [issue("DOC_INVALID_CROP", "ERROR", None,
                                     "a crop region needs four finite numbers")]}
        if any(abs(x) > float(LIMITS["max_coordinate_m"]) for x in c):
            return {"valid": False, "view": None,
                    "issues": [issue("DOC_COORDINATE_OUT_OF_BOUNDS", "ERROR", None,
                                     "the crop region leaves the declared bounds")]}
        crop = [_q(x) for x in c]
    depth = _num(d.get("view_depth"))
    ann = d.get("annotation_policy") or "TAGS_ONLY"
    if ann not in SPEC["annotation_policies"]:
        ann = "TAGS_ONLY"
    dim = d.get("dimension_policy") or "OVERALL_ONLY"
    if dim not in SPEC["dimension_policies"]:
        dim = "OVERALL_ONLY"
    vis = DISC_CATS.get(disc, DISC_CATS["ARCHITECTURE"])
    hidden = [c for c in SPEC["categories"] if c not in vis]
    ident = {"t": vt, "b": bid, "l": lid, "d": disc, "o": orient, "c": cut,
             "s": scale, "sm": scale_mode, "cr": crop, "vd": depth,
             "ap": ann, "dp": dim, "h": project.get("model_hash")}
    view = {
        "view_id": artifact_id("view", ident),
        "view_type": vt, "building_id": bid, "level_id": lid,
        "discipline": disc, "orientation": orient, "cut_plane": cut,
        "view_depth": _q(depth) if depth is not None else None,
        "crop_region": crop, "scale": scale, "scale_mode": scale_mode,
        "visible_categories": list(vis), "hidden_categories": hidden,
        "annotation_policy": ann, "dimension_policy": dim,
        "source_model_hash": project.get("model_hash"),
        "source_revision": project.get("current_revision"),
        "support": sup, "support_basis": VIEW_SUPPORT[vt]["basis"],
        "status": "CURRENT", "writes_to_model": False,
        "spec_version": SPEC["documentation_spec_version"],
    }
    return {"valid": True, "view": view, "issues": issues}


def _cut_plane(cp, issues):
    if not isinstance(cp, dict):
        return None
    axis = cp.get("axis")
    if axis not in ("x", "z"):
        issues.append(issue("DOC_MALFORMED_DEFINITION", "ERROR", axis,
                            "a section plane is taken on x or z"))
        return None
    at = _num(cp.get("at"))
    if at is None:
        issues.append(issue("DOC_NON_FINITE_GEOMETRY", "ERROR", None,
                            "the section position is not a finite number"))
        return None
    if abs(at) > float(LIMITS["max_coordinate_m"]):
        issues.append(issue("DOC_COORDINATE_OUT_OF_BOUNDS", "ERROR", None,
                            "the section position leaves the declared bounds"))
        return None
    look = cp.get("look") if cp.get("look") in ("+", "-") else "+"
    return {"axis": axis, "at": _q(at), "look": look}


# ------------------------------------------------------ مصادر النموذج ----
def _arch_of(project):
    import acs_arch as A
    m = project.get("model") if isinstance(project, dict) else None
    return A.compile_architecture(json.loads(json.dumps(m)),
                                  project.get("building_id") or "bld_0", None, 0)


def _struct_of(project):
    import acs_struct as S
    m = project.get("model")
    return S.compile_structure(json.loads(json.dumps(m)),
                               project.get("building_id") or "bld_0", None, 0)


def _mep_of(project):
    import acs_mep as M
    m = project.get("model")
    return M.compile_mep(json.loads(json.dumps(m)),
                         project.get("building_id") or "bld_0", None, 0)


def _fls_of(project):
    import acs_fls as F
    m = project.get("model")
    return F.compile_fls(json.loads(json.dumps(m)),
                         project.get("building_id") or "bld_0", None, 0)


def sources(project):
    """يجمع مخرجات التخصّصات مرّة واحدة. لا يُعدَّل أي منها هنا."""
    return {"arch": _arch_of(project), "struct": _struct_of(project),
            "mep": _mep_of(project), "fls": _fls_of(project)}


# -------------------------------------------------- هندسة المنظر (§8) ----
def _wall_rect(w):
    """مستطيل الجدار في المسقط من هندسة acs_arch وحدها."""
    sx, sz = _num(w["start"]["x"]), _num(w["start"]["z"])
    ex, ez = _num(w["end"]["x"]), _num(w["end"]["z"])
    if None in (sx, sz, ex, ez):
        return None
    th = stated(w.get("thickness_m"))
    # سمك غير مذكور: يُرسم الجدار خطّاً محورياً بلا سمك مُخترع
    t = th["value"] if th["status"] == "STATED" else None
    return {"start": [_q(sx), _q(sz)], "end": [_q(ex), _q(ez)],
            "thickness": (_q(t) if t is not None else None),
            "thickness_status": th["status"]}


def plan_geometry(project, view, src=None):
    """مسقط أفقي حقيقي من الهندسة القانونية — لا تنقيط للمشهد ثلاثي الأبعاد."""
    issues = []
    if src is None:
        src = sources(project)
    arch = src["arch"]
    lid = view["level_id"]
    vis = set(view["visible_categories"])
    lvl = next((l for l in arch["levels"] if l["id"] == lid), None)
    elems = []

    if "WALL" in vis:
        # الجدار المشترك جدار واحد: نعتمد معرّف acs_arch ولا نعيد رسمه لكل فراغ
        seen = set()
        for w in arch["walls"]:
            if w["level_id"] != lid or w["id"] in seen:
                continue
            seen.add(w["id"])
            r = _wall_rect(w)
            if r is None:
                issues.append(issue("DOC_NON_FINITE_GEOMETRY", "WARNING", w["id"],
                                    "wall endpoints are not finite"))
                continue
            elems.append({"category": "WALL", "id": w["id"], "geometry_class": "CUT",
                          "shape": "segment", "start": r["start"], "end": r["end"],
                          "thickness": r["thickness"],
                          "thickness_status": r["thickness_status"],
                          "shared": bool(w.get("shared")),
                          "exposure": w.get("exposure"),
                          "exposure_status": w.get("exposure_status")})
    if "SPACE" in vis:
        for s in arch["spaces"]:
            if s["level_id"] != lid:
                continue
            r = [_num(x) for x in (s.get("rect") or [])]
            if len(r) != 4 or any(x is None for x in r):
                issues.append(issue("DOC_UNRESOLVED_ELEMENT", "WARNING", s["id"],
                                    "space rectangle is not resolvable"))
                continue
            elems.append({"category": "SPACE", "id": s["id"],
                          "space_id": s.get("space_id"),
                          "geometry_class": "CUT", "shape": "rect",
                          "rect": [_q(x) for x in r],
                          "name": s.get("name"),
                          "area_m2": _q(_num(s.get("area_m2")) or 0.0),
                          "area_basis": s.get("boundary_basis")})
            if s.get("boundary_basis") == "polygon_edges":
                elems[-1].update(shape="polygon", polygon=s["polygon"])
    for cat, typ in (("DOOR", "DOOR"), ("WINDOW", "WINDOW")):
        if cat not in vis:
            continue
        for o in arch["openings"]:
            if o["level_id"] != lid or o.get("type") != typ:
                continue
            g = _opening_plan(o, arch)
            if g is None:
                issues.append(issue("DOC_UNRESOLVED_ELEMENT", "WARNING", o["id"],
                                    "opening has no resolvable host position"))
                continue
            g.update({"category": cat, "id": o["id"], "geometry_class": "CUT",
                      "host_wall_id": o.get("host_wall_id"),
                      "host_status": o.get("host_status"),
                      "swing_status": o.get("swing_status"),
                      "swing_direction": o.get("swing_direction")})
            elems.append(g)
    if "VOID" in vis:
        for v in arch["voids"]:
            if v["level_id"] != lid:
                continue
            r = [_num(x) for x in (v.get("rect") or [])]
            if len(r) == 4 and all(x is not None for x in r):
                elems.append({"category": "VOID", "id": v["id"],
                              "geometry_class": "CUT", "shape": "rect",
                              "rect": [_q(x) for x in r],
                              "core_type": v.get("core_type")})
    if "SLAB" in vis:
        for s in arch["slabs"]:
            if s["level_id"] != lid:
                continue
            o = [_num(x) for x in (s.get("outline") or [])]
            if len(o) == 4 and all(x is not None for x in o):
                th = stated(s.get("thickness_m"))
                elems.append({"category": "SLAB", "id": s["id"],
                              "geometry_class": "PROJECTED", "shape": "rect",
                              "rect": [_q(x) for x in o],
                              "thickness": th["value"],
                              "thickness_status": th["status"],
                              "outline_basis": s.get("outline_basis")})
                if "cells" in s:
                    elems[-1].update(shape="cells", cells=s["cells"])
    if "CORE" in vis or "STAIR" in vis:
        for c in arch["cores"]:
            if lvl is not None and lvl["index"] not in (c.get("served_levels") or []):
                continue
            x, z = _num(c.get("x")), _num(c.get("z"))
            w = stated(c.get("footprint_w_m"))
            d = stated(c.get("footprint_d_m"))
            if x is None or z is None:
                continue
            elems.append({"category": "CORE", "id": c["id"],
                          "geometry_class": "CUT", "shape": "point_or_rect",
                          "x": _q(x), "z": _q(z),
                          "w": w["value"], "d": d["value"],
                          "footprint_status": ("STATED" if w["status"] == "STATED"
                                               and d["status"] == "STATED"
                                               else "UNKNOWN"),
                          "core_type": c.get("type")})

    elems += _discipline_elements(view, src, issues)
    elems.sort(key=lambda e: (e["category"], str(e["id"])))
    bounds = _bounds_of(elems)
    return {"valid": True, "elements": elems, "issues": issues,
            "bounds": bounds, "level": lvl,
            "counts": _counts(elems)}


def _opening_plan(o, arch):
    """موقع الفتحة على جدارها المضيف من هندسة acs_arch."""
    host = next((w for w in arch["walls"] if w["id"] == o.get("host_wall_id")), None)
    wd = stated(o.get("width_m"))
    u = _num(o.get("u_center"))
    if host is None or u is None:
        return None
    host_u0 = _num(host.get("u0"))
    if host_u0 is None:
        return None
    # u_center is a global wall-frame coordinate; start already includes u0.
    u -= host_u0
    sx, sz = _num(host["start"]["x"]), _num(host["start"]["z"])
    ex, ez = _num(host["end"]["x"]), _num(host["end"]["z"])
    if None in (sx, sz, ex, ez):
        return None
    ln = math.hypot(ex - sx, ez - sz)
    if ln <= 0:
        return None
    ux, uz = (ex - sx) / ln, (ez - sz) / ln
    w = wd["value"]
    if w is None:
        # عرض غير مذكور: تُوثَّق الفتحة نقطةً على الجدار، ولا يُخترع عرض
        cx, cz = sx + ux * u, sz + uz * u
        return {"shape": "point", "x": _q(cx), "z": _q(cz),
                "width": None, "width_status": "UNKNOWN",
                "axis": host.get("axis")}
    h = w / 2.0
    return {"shape": "segment",
            "start": [_q(sx + ux * (u - h)), _q(sz + uz * (u - h))],
            "end": [_q(sx + ux * (u + h)), _q(sz + uz * (u + h))],
            "width": _q(w), "width_status": "STATED",
            "axis": host.get("axis")}


def _discipline_elements(view, src, issues):
    """عناصر التخصّصات الممثَّلة فقط. غير الممثَّل يبقى غائباً لا مُخترعاً."""
    vis = set(view["visible_categories"])
    lid = view["level_id"]
    out = []
    st, mp, fl = src["struct"], src["mep"], src["fls"]
    if "COLUMN" in vis:
        lvl_index = None
        for l in src["arch"]["levels"]:
            if l["id"] == lid:
                lvl_index = l["index"]
        for c in st["columns"]:
            x, z = _num(c.get("x")), _num(c.get("z"))
            if x is None or z is None:
                node = c.get("position") or {}
                x, z = _num(node.get("x")), _num(node.get("z"))
            if x is None or z is None:
                continue
            # العمود يمتدّ من دوره الأدنى إلى الأعلى كما يصرّح النموذج، فيظهر
            # في مسقط كل دور يعبره. الامتداد مقروء لا مُفترَض
            b = c.get("base_level_index")
            t = c.get("top_level_index")
            if lvl_index is not None and isinstance(b, int) and isinstance(t, int):
                if not (min(b, t) <= lvl_index <= max(b, t)):
                    continue
            elif c.get("base_level_id") not in (lid, None):
                continue
            out.append({"category": "COLUMN", "id": c["id"], "geometry_class": "CUT",
                        "shape": "point", "x": _q(x), "z": _q(z),
                        "section": c.get("section"),
                        "material_ref": c.get("material_ref"),
                        "grid_refs": c.get("grid_refs") or []})
    if "BEAM" in vis:
        for b in st["beams"]:
            if b.get("level_id") != lid:
                continue
            s, e = b.get("start") or {}, b.get("end") or {}
            sx, sz = _num(s.get("x")), _num(s.get("z"))
            ex, ez = _num(e.get("x")), _num(e.get("z"))
            if None in (sx, sz, ex, ez):
                continue
            out.append({"category": "BEAM", "id": b["id"],
                        "geometry_class": "PROJECTED", "shape": "segment",
                        "start": [_q(sx), _q(sz)], "end": [_q(ex), _q(ez)],
                        "section": b.get("section"),
                        "material_ref": b.get("material_ref")})
    if "GRID" in vis:
        for gs in st["grid_systems"]:
            for g in gs.get("grids") or []:
                p = _num(g.get("position_m"))
                if p is None or not g.get("position_stated"):
                    continue
                out.append({"category": "GRID", "id": g["id"],
                            "geometry_class": "PROJECTED", "shape": "grid_line",
                            "axis": g.get("axis"), "position": _q(p),
                            "label": g.get("label")})
    if "FOUNDATION" in vis:
        for f in st["foundations"]:
            x, z = _num(f.get("x")), _num(f.get("z"))
            if x is None or z is None:
                continue
            out.append({"category": "FOUNDATION", "id": f["id"],
                        "geometry_class": "PROJECTED", "shape": "point",
                        "x": _q(x), "z": _q(z),
                        "foundation_type": f.get("foundation_type")})
    if "STRUCTURAL_SLAB" in vis:
        for s in st["slabs"]:
            if s.get("level_id") != lid:
                continue
            o = [_num(x) for x in (s.get("outline") or [])]
            if len(o) == 4 and all(x is not None for x in o):
                out.append({"category": "STRUCTURAL_SLAB", "id": s["id"],
                            "geometry_class": "PROJECTED", "shape": "rect",
                            "rect": [_q(x) for x in o],
                            "material_ref": s.get("material_ref")})
    if "MEP_EQUIPMENT" in vis:
        for e in mp["equipment"]:
            if e.get("level_id") != lid:
                continue
            x, z = _num(e.get("x")), _num(e.get("z"))
            if x is None or z is None:
                continue
            out.append({"category": "MEP_EQUIPMENT", "id": e["id"],
                        "geometry_class": "PROJECTED", "shape": "point",
                        "x": _q(x), "z": _q(z),
                        "equipment_type": e.get("equipment_type"),
                        "system_ref": e.get("system_ref")})
    if "MEP_TERMINAL" in vis:
        for t in mp["terminals"]:
            if t.get("level_id") != lid:
                continue
            x, z = _num(t.get("x")), _num(t.get("z"))
            if x is None or z is None:
                continue
            out.append({"category": "MEP_TERMINAL", "id": t["id"],
                        "geometry_class": "PROJECTED", "shape": "point",
                        "x": _q(x), "z": _q(z),
                        "terminal_type": t.get("terminal_type")
                        or t.get("declared_type"),
                        "system_ref": t.get("system_ref")})
    if "MEP_SEGMENT" in vis:
        for s in mp["segments"]:
            if s.get("level_id") != lid:
                continue
            a, b = s.get("start") or {}, s.get("end") or {}
            ax, az = _num(a.get("x")), _num(a.get("z"))
            bx, bz = _num(b.get("x")), _num(b.get("z"))
            if None in (ax, az, bx, bz):
                # مقطع غير موجَّه: يبقى غير موجَّه ولا يُلفَّق له مسار
                out.append({"category": "MEP_SEGMENT", "id": s["id"],
                            "geometry_class": "UNRESOLVED", "shape": "none",
                            "routed": False, "kind": s.get("kind")})
                issues.append(issue("DOC_UNROUTED_SEGMENT", "WARNING", s["id"],
                                    "the segment has no resolved route; it is "
                                    "reported unrouted and is not drawn"))
                continue
            out.append({"category": "MEP_SEGMENT", "id": s["id"],
                        "geometry_class": "PROJECTED", "shape": "segment",
                        "start": [_q(ax), _q(az)], "end": [_q(bx), _q(bz)],
                        "routed": True, "kind": s.get("kind"),
                        "system_ref": s.get("system_ref")})
    if "MEP_RISER" in vis:
        for r in mp["risers"]:
            x, z = _num(r.get("x")), _num(r.get("z"))
            if x is None or z is None:
                continue
            if lid not in (r.get("level_ids") or []):
                continue
            out.append({"category": "MEP_RISER", "id": r["id"],
                        "geometry_class": "CUT", "shape": "point",
                        "x": _q(x), "z": _q(z), "kind": r.get("kind")})
    if "FLS_DEVICE" in vis:
        for d in fl["devices"]:
            if d.get("level_id") != lid:
                continue
            x, z = _num(d.get("x")), _num(d.get("z"))
            if x is None or z is None:
                x, z = _num(d.get("raw_x")), _num(d.get("raw_z"))
            if x is None or z is None:
                continue
            out.append({"category": "FLS_DEVICE", "id": d["id"],
                        "geometry_class": "PROJECTED", "shape": "point",
                        "x": _q(x), "z": _q(z),
                        "device_type": d.get("device_type"),
                        "device_category": d.get("device_category")})
    if "FLS_SIGN" in vis:
        for s in fl["signs"]:
            if s.get("level_id") != lid:
                continue
            x, z = _num(s.get("x")), _num(s.get("z"))
            if x is None or z is None:
                x, z = _num(s.get("raw_x")), _num(s.get("raw_z"))
            if x is None or z is None:
                continue
            out.append({"category": "FLS_SIGN", "id": s["id"],
                        "geometry_class": "PROJECTED", "shape": "point",
                        "x": _q(x), "z": _q(z),
                        "indicates_exit": s.get("indicates_exit")})
    return out


def _counts(elems):
    c = {}
    for e in elems:
        c[e["category"]] = c.get(e["category"], 0) + 1
    return dict(sorted(c.items()))


def _bounds_of(elems):
    xs, zs = [], []
    for e in elems:
        if e.get("shape") == "rect":
            x, z, w, d = e["rect"]
            xs += [x, x + w]
            zs += [z, z + d]
        elif e.get("shape") == "segment":
            xs += [e["start"][0], e["end"][0]]
            zs += [e["start"][1], e["end"][1]]
        elif e.get("shape") in ("point", "point_or_rect"):
            if e.get("x") is not None:
                xs.append(e["x"])
                zs.append(e["z"])
        elif e.get("shape") in ("polygon", "cells"):
            rings = [e["polygon"]] if e["shape"] == "polygon" else e["cells"]
            for ring in rings:
                xs.extend(p[0] for p in ring)
                zs.extend(p[1] for p in ring)
    if not xs:
        return None
    return {"min_x": _q(min(xs)), "max_x": _q(max(xs)),
            "min_z": _q(min(zs)), "max_z": _q(max(zs))}


def _cell_edges(cells):
    """Union boundary only: split T-junctions and cancel shared cell edges."""
    vertices = [p for ring in cells for p in ring]
    segments = {}
    for ring in cells:
        for a, b in POLY.edges(ring):
            dx, dz = b[0]-a[0], b[1]-a[1]
            length2 = dx*dx+dz*dz
            cuts = {0.0, 1.0}
            for p in vertices:
                if POLY.on_segment(p, a, b):
                    cuts.add(max(0.0, min(1.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dz)/length2)))
            ordered = sorted(cuts)
            for lo, hi in zip(ordered, ordered[1:]):
                if (hi-lo)*math.sqrt(length2) <= POLY.EPS:
                    continue
                ends = sorted([(_q(a[0]+t*dx), _q(a[1]+t*dz)) for t in (lo, hi)])
                key = tuple(ends)
                segments[key] = segments.get(key, 0)+1
    return [[list(a), list(b)] for (a, b), count in sorted(segments.items()) if count == 1]


def _cell_section(cells, axis, at):
    """Intersect convex cells with a vertical plane, then merge their intervals."""
    i = 0 if axis == "x" else 1
    intervals = []
    for ring in cells:
        values = []
        for a, b in POLY.edges(ring):
            delta = b[i]-a[i]
            if abs(delta) <= POLY.EPS:
                if abs(at-a[i]) <= POLY.EPS:
                    values.extend([a[1-i], b[1-i]])
            elif min(a[i], b[i])-POLY.EPS <= at <= max(a[i], b[i])+POLY.EPS:
                values.append(a[1-i]+(at-a[i])/delta*(b[1-i]-a[1-i]))
        if values and max(values)-min(values) > POLY.EPS:
            intervals.append((min(values), max(values)))
    merged = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1]+POLY.EPS:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def _polygon_label(ring):
    # A convex cell's vertex mean is inside it even when the room centroid is not.
    cell = max(POLY.cells([ring]), key=lambda c: abs(POLY.signed_area(c)))
    return [sum(p[i] for p in cell)/len(cell) for i in (0, 1)]


# ------------------------------------------------------ الواجهات (§20) ----
def _rot(x, z, deg, ox=0.0, oz=0.0):
    a = math.radians(deg or 0.0)
    dx, dz = x - ox, z - oz
    return (ox + dx * math.cos(a) - dz * math.sin(a),
            oz + dx * math.sin(a) + dz * math.cos(a))


def elevation_geometry(project, view, src=None):
    """واجهة متّجهة: إسقاط الهندسة القانونية على مستوٍ رأسي، مع دوران المبنى."""
    if src is None:
        src = sources(project)
    arch = src["arch"]
    issues = []
    rot = _num((arch.get("transform") or {}).get("rotation_deg")) or 0.0
    orient = view["orientation"]
    # اتّجاه النظر: نُدير النقاط بعكس دوران المبنى ثم نسقط على المحور المناسب
    base = {"NORTH": 0.0, "EAST": 90.0, "SOUTH": 180.0, "WEST": 270.0}[orient]
    ang = -(base + rot)
    ext = set(arch["envelope"].get("exterior_walls") or [])
    ext_open = set(arch["envelope"].get("external_openings") or [])
    lv_elev = {l["id"]: (_num(l.get("elevation_m")) or 0.0) for l in arch["levels"]}
    elems = []
    for w in arch["walls"]:
        if w["id"] not in ext:
            continue
        sx, sz = _rot(_num(w["start"]["x"]), _num(w["start"]["z"]), ang)
        ex, ez = _rot(_num(w["end"]["x"]), _num(w["end"]["z"]), ang)
        # الجدار المواجه للناظر هو الذي يكاد يوازي محور u بعد الدوران
        if abs(ez - sz) > abs(ex - sx):
            continue
        depth = (sz + ez) / 2.0
        h = stated(w.get("height_m"))
        base_e = lv_elev.get(w["level_id"], 0.0)
        elems.append({"category": "WALL", "id": w["id"], "geometry_class": "PROJECTED",
                      "shape": "rect_uv",
                      "u0": _q(min(sx, ex)), "u1": _q(max(sx, ex)),
                      "v0": _q(base_e),
                      "v1": (_q(base_e + h["value"]) if h["status"] == "STATED"
                             else None),
                      "height_status": h["status"], "depth": _q(depth),
                      "level_id": w["level_id"]})
    walls_by_id = {w["id"]: w for w in arch["walls"]}
    drawn_walls = {e["id"] for e in elems}
    for o in arch["openings"]:
        if o["id"] not in ext_open or o.get("host_wall_id") not in drawn_walls:
            continue
        host = walls_by_id.get(o["host_wall_id"])
        g = _opening_plan(o, arch)
        if g is None or g.get("width") is None:
            issues.append(issue("DOC_UNKNOWN_VALUE", "WARNING", o["id"],
                                "opening width is not stated; it is not drawn "
                                "at an invented size"))
            continue
        s0 = _rot(g["start"][0], g["start"][1], ang)
        s1 = _rot(g["end"][0], g["end"][1], ang)
        h = stated(o.get("height_m"))
        sill = stated(o.get("sill_m"))
        base_e = lv_elev.get(o["level_id"], 0.0)
        v0 = base_e + (sill["value"] if sill["status"] == "STATED" else 0.0)
        elems.append({"category": o["type"], "id": o["id"],
                      "geometry_class": "PROJECTED", "shape": "rect_uv",
                      "u0": _q(min(s0[0], s1[0])), "u1": _q(max(s0[0], s1[0])),
                      "v0": _q(v0),
                      "v1": (_q(v0 + h["value"]) if h["status"] == "STATED" else None),
                      "height_status": h["status"],
                      "sill_status": sill["status"],
                      "level_id": o["level_id"]})
    for l in arch["levels"]:
        elems.append({"category": "LEVEL_LINE", "id": l["id"],
                      "geometry_class": "REFERENCE", "shape": "level",
                      "elevation": _q(lv_elev.get(l["id"], 0.0)),
                      "name": l.get("name"),
                      "elevation_source": l.get("elevation_source")})
    elems.sort(key=lambda e: (e["category"], str(e["id"])))
    us = [e["u0"] for e in elems if "u0" in e] + [e["u1"] for e in elems if "u1" in e]
    vs = ([e["v0"] for e in elems if e.get("v0") is not None]
          + [e["v1"] for e in elems if e.get("v1") is not None]
          + [e["elevation"] for e in elems if e.get("elevation") is not None])
    bounds = ({"min_u": _q(min(us)), "max_u": _q(max(us)),
               "min_v": _q(min(vs)), "max_v": _q(max(vs))} if us and vs else None)
    return {"valid": True, "elements": elems, "issues": issues,
            "bounds": bounds, "rotation_applied_deg": _q(rot),
            "counts": _counts(elems)}


# ------------------------------------------------------- القطاعات (§22) ----
def section_geometry(project, view, src=None):
    """قطاع حقيقي: تقاطع رياضي لمستوٍ رأسي مع الهندسة، لا إسقاط للمسقط."""
    if src is None:
        src = sources(project)
    arch = src["arch"]
    issues = []
    cp = view["cut_plane"]
    axis, at = cp["axis"], cp["at"]
    depth = view.get("view_depth")
    lv_elev = {l["id"]: (_num(l.get("elevation_m")) or 0.0) for l in arch["levels"]}
    elems = []

    def _cross(a0, a1, b0, b1):
        """يعيد إحداثي التقاطع على المحور العرضي أو None."""
        lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
        if lo - 1e-9 <= at <= hi + 1e-9:
            if abs(a1 - a0) < 1e-12:
                return b0
            t = (at - a0) / (a1 - a0)
            return b0 + t * (b1 - b0)
        return None

    for w in arch["walls"]:
        sx, sz = _num(w["start"]["x"]), _num(w["start"]["z"])
        ex, ez = _num(w["end"]["x"]), _num(w["end"]["z"])
        if None in (sx, sz, ex, ez):
            continue
        h = stated(w.get("height_m"))
        base_e = lv_elev.get(w["level_id"], 0.0)
        # مستوى القطع عند axis=at عمودُه على ذلك المحور. الجدار الموازي للمستوى
        # هو الذي لا يتغيّر إحداثيه على المحور نفسه، فلا يعبره أبداً.
        if axis == "x":
            u = _cross(sx, ex, sz, ez)
            along = None if u is None else u
            parallel = abs(ex - sx) < 1e-9
        else:
            u = _cross(sz, ez, sx, ex)
            along = None if u is None else u
            parallel = abs(ez - sz) < 1e-9
        if along is not None and not parallel:
            elems.append({"category": "WALL", "id": w["id"], "geometry_class": "CUT",
                          "shape": "rect_uv", "u0": _q(along - 0.075),
                          "u1": _q(along + 0.075), "v0": _q(base_e),
                          "v1": (_q(base_e + h["value"]) if h["status"] == "STATED"
                                 else None),
                          "height_status": h["status"], "level_id": w["level_id"]})
            continue
        # لا يقطعه المستوى: مُسقَط إن كان ضمن العمق، وإلّا خلفه
        ref = (sz + ez) / 2.0 if axis == "x" else (sx + ex) / 2.0
        cls = "PROJECTED"
        if depth is not None and abs(ref - at) > abs(depth):
            cls = "BEYOND_DEPTH"
        u0 = min(sz, ez) if axis == "x" else min(sx, ex)
        u1 = max(sz, ez) if axis == "x" else max(sx, ex)
        elems.append({"category": "WALL", "id": w["id"], "geometry_class": cls,
                      "shape": "rect_uv", "u0": _q(u0), "u1": _q(u1),
                      "v0": _q(base_e),
                      "v1": (_q(base_e + h["value"]) if h["status"] == "STATED"
                             else None),
                      "height_status": h["status"], "level_id": w["level_id"]})

    for o in arch["openings"]:
        g = _opening_plan(o, arch)
        if g is None or g.get("width") is None:
            elems.append({"category": o["type"], "id": o["id"],
                          "geometry_class": "UNRESOLVED", "shape": "none",
                          "reason": "opening width or host is not stated"})
            continue
        a0 = g["start"][0] if axis == "x" else g["start"][1]
        a1 = g["end"][0] if axis == "x" else g["end"][1]
        b0 = g["start"][1] if axis == "x" else g["start"][0]
        b1 = g["end"][1] if axis == "x" else g["end"][0]
        u = _cross(a0, a1, b0, b1)
        h = stated(o.get("height_m"))
        sill = stated(o.get("sill_m"))
        base_e = lv_elev.get(o["level_id"], 0.0)
        v0 = base_e + (sill["value"] if sill["status"] == "STATED" else 0.0)
        cls = "CUT" if u is not None else "PROJECTED"
        if u is None and depth is not None:
            ref = (b0 + b1) / 2.0
            if abs(ref - at) > abs(depth):
                cls = "BEYOND_DEPTH"
        uu = u if u is not None else (b0 + b1) / 2.0
        elems.append({"category": o["type"], "id": o["id"], "geometry_class": cls,
                      "shape": "rect_uv", "u0": _q(uu - 0.05), "u1": _q(uu + 0.05),
                      "v0": _q(v0),
                      "v1": (_q(v0 + h["value"]) if h["status"] == "STATED" else None),
                      "height_status": h["status"], "level_id": o["level_id"]})

    # البلاطات: شريط مقطوع، مع احترام الفراغات الأرضية — درج لا يعبر بلاطة سليمة
    voids = arch["voids"]
    for s in arch["slabs"]:
        o = [_num(x) for x in (s.get("outline") or [])]
        if len(o) != 4 or any(x is None for x in o):
            continue
        x, z, w_, d_ = o
        a0, a1 = (x, x + w_) if axis == "x" else (z, z + d_)
        if not (a0 - 1e-9 <= at <= a1 + 1e-9):
            continue
        strips = (_cell_section(s["cells"], axis, at) if "cells" in s else
                  ([(z, z + d_)] if axis == "x" else [(x, x + w_)]))
        for v in voids:
            if v.get("level_id") != s.get("level_id"):
                continue
            r = [_num(q) for q in (v.get("rect") or [])]
            if len(r) != 4 or any(q is None for q in r):
                continue
            vx, vz, vw, vd = r
            va0, va1 = (vx, vx + vw) if axis == "x" else (vz, vz + vd)
            if not (va0 - 1e-9 <= at <= va1 + 1e-9):
                continue
            vb0, vb1 = (vz, vz + vd) if axis == "x" else (vx, vx + vw)
            nxt = []
            for (c0, c1) in strips:
                if vb1 <= c0 or vb0 >= c1:
                    nxt.append((c0, c1))
                    continue
                if vb0 > c0:
                    nxt.append((c0, vb0))
                if vb1 < c1:
                    nxt.append((vb1, c1))
            strips = nxt
        th = stated(s.get("thickness_m"))
        e = lv_elev.get(s.get("level_id"), 0.0)
        for (c0, c1) in strips:
            elems.append({"category": "SLAB", "id": s["id"],
                          "geometry_class": "CUT", "shape": "rect_uv",
                          "u0": _q(c0), "u1": _q(c1),
                          "v0": (_q(e - th["value"]) if th["status"] == "STATED"
                                 else None),
                          "v1": _q(e), "thickness_status": th["status"],
                          "level_id": s.get("level_id"),
                          "void_adjusted": len(strips) > 1 or (c0, c1) != (
                              (z, z + d_) if axis == "x" else (x, x + w_))})

    # خطوط المناسيب من مناسيب الأدوار المعمارية الحقيقية (§18)، لا من اصطلاح
    for l in arch["levels"]:
        elems.append({"category": "LEVEL_LINE", "id": l["id"],
                      "geometry_class": "REFERENCE", "shape": "level",
                      "elevation": _q(lv_elev.get(l["id"], 0.0)),
                      "name": l.get("name"),
                      "elevation_source": l.get("elevation_source")})
    elems.sort(key=lambda e: (e["category"], str(e["id"]),
                             e.get("u0") if e.get("u0") is not None else 0.0))
    cut = [e for e in elems if e["geometry_class"] == "CUT"]
    proj = [e for e in elems if e["geometry_class"] == "PROJECTED"]
    beyond = [e for e in elems if e["geometry_class"] == "BEYOND_DEPTH"]
    unres = [e for e in elems if e["geometry_class"] == "UNRESOLVED"]
    us = [e["u0"] for e in elems if e.get("u0") is not None] + \
         [e["u1"] for e in elems if e.get("u1") is not None]
    vs = [e["v0"] for e in elems if e.get("v0") is not None] + \
         [e["v1"] for e in elems if e.get("v1") is not None]
    bounds = ({"min_u": _q(min(us)), "max_u": _q(max(us)),
               "min_v": _q(min(vs)), "max_v": _q(max(vs))} if us and vs else None)
    return {"valid": True, "elements": elems, "issues": issues, "bounds": bounds,
            "cut_count": len(cut), "projected_count": len(proj),
            "beyond_count": len(beyond), "unresolved_count": len(unres),
            "cut_ids": sorted(e["id"] for e in cut),
            "unresolved_ids": sorted(e["id"] for e in unres),
            "counts": _counts(elems)}


# ------------------------------------------------------- المقاسات (§14) ----
def dimensions(project, view, geom, src=None):
    """مقاسات واقعية من الهندسة. ما لا تذكره النموذج يبقى مجهولاً."""
    pol = view["dimension_policy"]
    out = []
    if pol == "NONE":
        return {"dimensions": [], "issues": [], "counts": {}}
    issues = []

    def add(mt, ids, val, status, prov, unit="m"):
        st = {"value": (_q(val) if val is not None else None),
              "status": ("STATED" if val is not None else "UNKNOWN"),
              "source": prov}
        d = {"dimension_id": artifact_id("dimension",
                                         {"v": view["view_id"], "t": mt, "i": ids}),
             "measurement_type": mt, "source_element_ids": list(ids),
             "exact_value": st["value"],
             "display_value": display_of(st),
             "unit": unit, "precision": int(SPEC["dimension_precision_m"]),
             "provenance": prov,
             "measurement_status": "MEASURED" if status == "STATED" else status,
             "view_id": view["view_id"]}
        out.append(d)

    b = geom.get("bounds")
    if b and "min_x" in b:
        add("OVERALL_BUILDING", ["__extent_x"], b["max_x"] - b["min_x"],
            "STATED", "DERIVED_FROM_GEOMETRY")
        add("OVERALL_BUILDING", ["__extent_z"], b["max_z"] - b["min_z"],
            "STATED", "DERIVED_FROM_GEOMETRY")
    elif b and "min_u" in b:
        add("OVERALL_LEVEL", ["__extent_u"], b["max_u"] - b["min_u"],
            "STATED", "DERIVED_FROM_GEOMETRY")

    if pol in ("OVERALL_AND_SPACES", "FULL_CHAIN"):
        for e in geom["elements"]:
            if e["category"] == "SPACE":
                x, z, w, d = e["rect"]
                add("SPACE_WIDTH", [e["id"]], w, "STATED", "MODEL_GEOMETRY")
                add("SPACE_DEPTH", [e["id"]], d, "STATED", "MODEL_GEOMETRY")
    if pol == "FULL_CHAIN":
        for e in geom["elements"]:
            if e["category"] == "WALL" and e.get("shape") == "segment":
                ln = math.hypot(e["end"][0] - e["start"][0],
                                e["end"][1] - e["start"][1])
                add("WALL_SEGMENT_LENGTH", [e["id"]], ln, "STATED", "MODEL_GEOMETRY")
            if e["category"] in ("DOOR", "WINDOW"):
                if e.get("width_status") == "STATED":
                    add("OPENING_WIDTH", [e["id"]], e.get("width"), "STATED",
                        "MODEL_STATED_VALUE")
                else:
                    # عرض غير مذكور: مقاس مجهول معلَن، لا بديل عرض
                    add("OPENING_WIDTH", [e["id"]], None, "UNKNOWN",
                        "MODEL_STATED_VALUE")
                    issues.append(issue("DOC_UNKNOWN_VALUE", "INFO", e["id"],
                                        "opening width is not stated in the model"))
    # مناسيب الأدوار من الهندسة المعمارية وحدها
    if view["view_type"] in ("SECTION", "ELEVATION"):
        for e in geom["elements"]:
            if e["category"] == "LEVEL_LINE":
                add("LEVEL_ELEVATION", [e["id"]], e.get("elevation"),
                    "STATED", "MODEL_GEOMETRY")
    # تباعد المحاور من الشبكات الممثَّلة فقط
    grids = [e for e in geom["elements"] if e["category"] == "GRID"]
    for ax in ("X", "Z"):
        row = sorted((g for g in grids if g.get("axis") == ax),
                     key=lambda g: g["position"])
        for i in range(1, len(row)):
            add("GRID_SPACING", [row[i - 1]["id"], row[i]["id"]],
                row[i]["position"] - row[i - 1]["position"], "STATED",
                "MODEL_GEOMETRY")
    if len(out) > int(LIMITS["max_dimensions_per_view"]):
        issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "ERROR", view["view_id"],
                            "the view exceeds the declared dimension limit"))
        out = out[:int(LIMITS["max_dimensions_per_view"])]
    out.sort(key=lambda d: (d["measurement_type"], d["dimension_id"]))
    known = [d for d in out if d["measurement_status"] == "MEASURED"]
    return {"dimensions": out, "issues": issues,
            "counts": {"total": len(out), "measured": len(known),
                       "unknown": len(out) - len(known)}}


# ------------------------------------------------------- التأشيرات (§29) ----
def annotations(project, view, geom, notes=None, src=None):
    """تأشيرات مصنَّفة بمصدرها. النصّ المولَّد لا يُقدَّم نصّاً كتبه مستعمل."""
    pol = view["annotation_policy"]
    out, issues = [], []
    if pol == "NONE":
        return {"annotations": [], "issues": [], "counts": {}}

    def add(atype, prov, text, ids, x, y):
        if not isinstance(text, str):
            text = "" if text is None else str(text)
        if len(text) > int(LIMITS["max_annotation_length"]):
            issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "WARNING", ids[:1],
                                "annotation text exceeds the declared length"))
            return
        out.append({"annotation_id": artifact_id(
            "annotation", {"v": view["view_id"], "t": atype, "i": ids, "x": x, "y": y}),
            "annotation_type": atype, "provenance": prov, "text": text,
            "source_element_ids": list(ids),
            "x": (_q(x) if x is not None else None),
            "y": (_q(y) if y is not None else None),
            "view_id": view["view_id"]})

    for e in geom["elements"]:
        c = e["category"]
        if c == "SPACE":
            x, z, w, d = e["rect"]
            tag_x, tag_z = (_polygon_label(e["polygon"]) if e.get("shape") == "polygon"
                            else (x + w/2.0, z + d/2.0))
            nm = e.get("name")
            add("ROOM_TAG", "MODEL_DERIVED",
                nm if isinstance(nm, str) and nm else str(e.get("space_id") or e["id"]),
                [e["id"]], tag_x, tag_z)
        elif c in ("DOOR", "WINDOW") and pol in ("TAGS_ONLY", "TAGS_AND_NOTES", "FULL"):
            px = e.get("x")
            pz = e.get("z")
            if px is None and e.get("shape") == "segment":
                px = (e["start"][0] + e["end"][0]) / 2.0
                pz = (e["start"][1] + e["end"][1]) / 2.0
            add("DOOR_TAG" if c == "DOOR" else "WINDOW_TAG", "DOCUMENTATION_DERIVED",
                tag_for(e["id"], c), [e["id"]], px, pz)
        elif c == "GRID":
            add("GRID_TAG", "MODEL_DERIVED", str(e.get("label") or ""), [e["id"]],
                e.get("position"), None)
        elif c in ("MEP_EQUIPMENT", "MEP_TERMINAL") and pol == "FULL":
            add("EQUIPMENT_TAG", "MODEL_DERIVED",
                str(e.get("equipment_type") or e.get("terminal_type") or ""),
                [e["id"]], e.get("x"), e.get("z"))
        elif c == "LEVEL_LINE":
            add("LEVEL_TAG", "MODEL_DERIVED", str(e.get("name") or e["id"]),
                [e["id"]], None, e.get("elevation"))

    if pol in ("TAGS_AND_NOTES", "FULL"):
        for n in (notes or []):
            t = n.get("text") if isinstance(n, dict) else n
            if not isinstance(t, str):
                continue
            if len(t) > int(LIMITS["max_note_length"]):
                issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "WARNING", None,
                                    "a user note exceeds the declared length"))
                continue
            add("GENERAL_NOTE", "USER_AUTHORED", t, [], None, None)

    if len(out) > int(LIMITS["max_annotations_per_view"]):
        issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "ERROR", view["view_id"],
                            "the view exceeds the declared annotation limit"))
        out = out[:int(LIMITS["max_annotations_per_view"])]
    out.sort(key=lambda a: (a["annotation_type"], a["annotation_id"]))
    byp = {}
    for a in out:
        byp[a["provenance"]] = byp.get(a["provenance"], 0) + 1
    return {"annotations": out, "issues": issues,
            "counts": {"total": len(out), "by_provenance": dict(sorted(byp.items()))}}


def tag_for(element_id, category):
    """وسم حتمي يقابل عنصراً قانونياً. لا نوع باب ولا نافذة يُخترع."""
    p = {"DOOR": "D", "WINDOW": "W"}.get(category, "X")
    return p + _sha16({"id": element_id, "c": category})[:6].upper()


# -------------------------------------------------------- الجداول (§35) ----
def _prov(el_id, model_hash, discipline, basis):
    return {"source_element_id": el_id, "source_model_hash": model_hash,
            "discipline": discipline, "provenance": basis}


def _cell(st):
    """خلية جدول: القيمة المعلَنة أو غير محدَّدة. لا استبدال ببديل عرض."""
    if st["status"] == "STATED":
        return {"value": st["value"], "status": "STATED"}
    return {"value": None, "status": "UNKNOWN",
            "display": SPEC["unknown_display"]}


def _text_cell(v):
    if isinstance(v, str) and v:
        return {"value": v, "status": "STATED"}
    return {"value": None, "status": "UNKNOWN", "display": SPEC["unknown_display"]}


def schedule(project, stype, options=None, src=None):
    """جدول = منظر على النموذج. كل صفّ يحمل معرّف عنصره وبصمة النموذج."""
    if stype not in SPEC["schedule_types"]:
        return {"valid": False, "schedule": None,
                "issues": [issue("DOC_MALFORMED_DEFINITION", "ERROR", stype,
                                 "schedule type is not declared")]}
    if src is None:
        src = sources(project)
    o = options if isinstance(options, dict) else {}
    lid = o.get("level_id")
    mh = project.get("model_hash")
    arch, st, mp, fl = src["arch"], src["struct"], src["mep"], src["fls"]
    rows, issues = [], []
    cols = SPEC["schedule_columns"].get(stype, [])

    def keep(rec_level):
        return lid is None or rec_level == lid

    if stype == "ROOM_SCHEDULE":
        for s in arch["spaces"]:
            if not keep(s["level_id"]):
                continue
            rows.append({
                "room_id": _text_cell(s.get("space_id") or s.get("id")),
                "name": _text_cell(s.get("name")),
                "level": _text_cell(s.get("level_id")),
                "area_m2": _cell(stated(s.get("area_m2"))),
                "area_basis": _text_cell(s.get("boundary_basis")),
                "program": _text_cell(s.get("program")),
                "occupancy_status": _text_cell(s.get("occupancy_status")),
                "provenance": _prov(s["id"], mh, "ARCHITECTURE", "MODEL_DERIVED")})
    elif stype in ("DOOR_SCHEDULE", "WINDOW_SCHEDULE"):
        want = "DOOR" if stype == "DOOR_SCHEDULE" else "WINDOW"
        for op in arch["openings"]:
            if op.get("type") != want or not keep(op["level_id"]):
                continue
            if want == "DOOR":
                rows.append({
                    "door_id": _text_cell(op.get("id")),
                    "tag": _text_cell(tag_for(op["id"], "DOOR")),
                    "level": _text_cell(op.get("level_id")),
                    "from_space": _text_cell(op.get("space_id")),
                    "to_space": _text_cell(op.get("destination")),
                    # العرض الاسمي والعرض الصافي قياسان مختلفان ولا يحلّ أحدهما محلّ الآخر
                    "nominal_width_m": _cell(stated(op.get("width_m"))),
                    "clear_width_m": _cell(stated(op.get("clear_width_m"))),
                    "height_m": _cell(stated(op.get("height_m"))),
                    "swing": _text_cell(op.get("swing_direction")),
                    "swing_status": _text_cell(op.get("swing_status")),
                    "fire_rating": _text_cell(op.get("fire_rating")),
                    "material": _text_cell(op.get("material")),
                    "host_status": _text_cell(op.get("host_status")),
                    "provenance": _prov(op["id"], mh, "ARCHITECTURE", "MODEL_DERIVED")})
            else:
                rows.append({
                    "window_id": _text_cell(op.get("id")),
                    "tag": _text_cell(tag_for(op["id"], "WINDOW")),
                    "level": _text_cell(op.get("level_id")),
                    "host_wall": _text_cell(op.get("host_wall_id")),
                    "width_m": _cell(stated(op.get("width_m"))),
                    "height_m": _cell(stated(op.get("height_m"))),
                    "sill_m": _cell(stated(op.get("sill_m"))),
                    "type": _text_cell(op.get("subtype")),
                    "material": _text_cell(op.get("material")),
                    "provenance": _prov(op["id"], mh, "ARCHITECTURE", "MODEL_DERIVED")})
    elif stype == "COLUMN_SCHEDULE":
        for c in st["columns"]:
            rows.append({
                "column_id": _text_cell(c.get("id")),
                "level": _text_cell(c.get("base_level_id")),
                "section": _text_cell(_section_text(c.get("section"))),
                "material": _text_cell(c.get("material_ref")),
                "height_m": _cell(stated(c.get("height_m"))),
                "grid_refs": _text_cell(",".join(c.get("grid_refs") or []) or None),
                "provenance": _prov(c["id"], mh, "STRUCTURE", "MODEL_DERIVED")})
    elif stype == "BEAM_SCHEDULE":
        for b in st["beams"]:
            if not keep(b.get("level_id")):
                continue
            rows.append({
                "beam_id": _text_cell(b.get("id")),
                "level": _text_cell(b.get("level_id")),
                "section": _text_cell(_section_text(b.get("section"))),
                "material": _text_cell(b.get("material_ref")),
                "length_m": _cell(stated(b.get("length_m"))),
                "provenance": _prov(b["id"], mh, "STRUCTURE", "MODEL_DERIVED")})
    elif stype == "SLAB_SCHEDULE":
        for s in st["slabs"]:
            rows.append({
                "slab_id": _text_cell(s.get("id")),
                "level": _text_cell(s.get("level_id")),
                "thickness_m": _cell(stated(s.get("thickness_m"))),
                "material": _text_cell(s.get("material_ref")),
                # المنسّق المشترك لا str(): "0.0" في بايثون مقابل "0" في
                # جافاسكربت فرق حقيقي يظهر في الجدول لا في الرسم وحده
                "outline": _text_cell(",".join(_fmt(x) for x in
                                               (s.get("outline") or [])) or None),
                "provenance": _prov(s["id"], mh, "STRUCTURE", "MODEL_DERIVED")})
    elif stype == "FOUNDATION_SCHEDULE":
        for f in st["foundations"]:
            rows.append({
                "foundation_id": _text_cell(f.get("id")),
                "type": _text_cell(f.get("foundation_type")),
                "depth_m": _cell(stated(f.get("depth_m"))),
                "embedment_m": _cell(stated(f.get("embedment_m"))),
                "material": _text_cell(f.get("material_ref")),
                "provenance": _prov(f["id"], mh, "STRUCTURE", "MODEL_DERIVED")})
    elif stype == "MEP_EQUIPMENT_SCHEDULE":
        for e in mp["equipment"]:
            if not keep(e.get("level_id")):
                continue
            rows.append({
                "equipment_id": _text_cell(e.get("id")),
                "level": _text_cell(e.get("level_id")),
                "type": _text_cell(e.get("equipment_type")),
                "system": _text_cell(e.get("system_ref")),
                "discipline": _text_cell(e.get("discipline")),
                "provenance": _prov(e["id"], mh, "MECHANICAL", "MODEL_DERIVED")})
    elif stype == "MEP_TERMINAL_SCHEDULE":
        for t in mp["terminals"]:
            if not keep(t.get("level_id")):
                continue
            rows.append({
                "terminal_id": _text_cell(t.get("id")),
                "level": _text_cell(t.get("level_id")),
                "type": _text_cell(t.get("terminal_type") or t.get("declared_type")),
                "system": _text_cell(t.get("system_ref")),
                "space": _text_cell(t.get("space_id")),
                "provenance": _prov(t["id"], mh, "MECHANICAL", "MODEL_DERIVED")})
    elif stype == "FLS_DEVICE_SCHEDULE":
        for d in fl["devices"]:
            if not keep(d.get("level_id")):
                continue
            rows.append({
                "device_id": _text_cell(d.get("id")),
                "level": _text_cell(d.get("level_id")),
                "type": _text_cell(d.get("device_type")),
                "category": _text_cell(d.get("device_category")),
                "space": _text_cell(d.get("space_id")),
                "provenance": _prov(d["id"], mh, "FIRE_PROTECTION", "MODEL_DERIVED")})
    elif stype == "FLS_SIGN_SCHEDULE":
        for s in fl["signs"]:
            if not keep(s.get("level_id")):
                continue
            rows.append({
                "sign_id": _text_cell(s.get("id")),
                "level": _text_cell(s.get("level_id")),
                "kind": _text_cell(s.get("kind") or "exit_sign"),
                "indicates_exit": _text_cell(s.get("indicates_exit")),
                "illuminated": _text_cell(str(s.get("illuminated"))
                                          if s.get("illuminated") is not None else None),
                "provenance": _prov(s["id"], mh, "FIRE_PROTECTION", "MODEL_DERIVED")})
    elif stype == "EQUIPMENT_SCHEDULE":
        for e in mp["equipment"]:
            rows.append({"equipment_id": _text_cell(e.get("id")),
                         "level": _text_cell(e.get("level_id")),
                         "type": _text_cell(e.get("equipment_type")),
                         "provenance": _prov(e["id"], mh, "MECHANICAL",
                                             "MODEL_DERIVED")})

    if len(rows) > int(LIMITS["max_schedule_rows"]):
        issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "ERROR", stype,
                            "the schedule exceeds the declared row limit"))
        rows = rows[:int(LIMITS["max_schedule_rows"])]
    if not rows:
        issues.append(issue("DOC_SCHEDULE_SCOPE_EMPTY", "INFO", stype,
                            "no represented element falls in this schedule scope"))
    key = list(rows[0].keys())[0] if rows else "provenance"
    rows.sort(key=lambda r: str((r.get(key) or {}).get("value") or ""))
    unknown = sum(1 for r in rows for k, v in r.items()
                  if isinstance(v, dict) and v.get("status") == "UNKNOWN")
    sch = {"schedule_id": artifact_id("schedule",
                                      {"t": stype, "l": lid, "h": mh}),
           "schedule_type": stype, "columns": cols,
           "level_id": lid, "rows": rows, "row_count": len(rows),
           "unknown_cell_count": unknown,
           "source_model_hash": mh,
           "source_revision": project.get("current_revision"),
           "writes_to_model": False,
           "note": "a schedule is a view over the model; a missing value stays missing",
           "spec_version": SPEC["documentation_spec_version"]}
    return {"valid": True, "schedule": sch, "issues": issues}


def _section_text(sec):
    if not isinstance(sec, dict):
        return None
    shape = sec.get("shape")
    w, d = _num(sec.get("width")), _num(sec.get("depth"))
    if shape and w is not None and d is not None:
        return "%s %sx%s" % (shape, _fmt(w), _fmt(d))
    return shape if isinstance(shape, str) else None


# ------------------------------------------------------- الكمّيات (§42) ----
def quantities(project, options=None, src=None):
    """تقرير كمّيات وقائعي. ليس جدول كمّيات تعاقدياً ولا تقديراً للكلفة."""
    if src is None:
        src = sources(project)
    arch, st, mp, fl = src["arch"], src["struct"], src["mep"], src["fls"]
    mh = project.get("model_hash")
    out, issues = [], []

    def add(qt, value, unit, ids, basis, coverage):
        out.append({"quantity_id": artifact_id("quantity", {"t": qt, "h": mh}),
                    "quantity_type": qt,
                    "quantity": (_q(value) if value is not None else None),
                    "unit": unit, "source_element_ids": sorted(ids),
                    "source_element_count": len(ids),
                    "measurement_basis": basis, "coverage_status": coverage})

    C = "COMPLETE_FOR_REPRESENTED_MODEL"
    add("LEVEL_COUNT", len(arch["levels"]), "count",
        [l["id"] for l in arch["levels"]], "architectural levels", C)
    add("ROOM_COUNT", len(arch["spaces"]), "count",
        [s["id"] for s in arch["spaces"]], "architectural spaces", C)
    doors = [o for o in arch["openings"] if o.get("type") == "DOOR"]
    wins = [o for o in arch["openings"] if o.get("type") == "WINDOW"]
    add("DOOR_COUNT", len(doors), "count", [o["id"] for o in doors],
        "represented door openings", C)
    add("WINDOW_COUNT", len(wins), "count", [o["id"] for o in wins],
        "represented window openings", C)

    # طول الجدران: مجموع أطوال مقاطع محسوبة من الهندسة
    wl, wids = 0.0, []
    for w in arch["walls"]:
        ln = _num(w.get("length_m"))
        if ln is None:
            sx, sz = _num(w["start"]["x"]), _num(w["start"]["z"])
            ex, ez = _num(w["end"]["x"]), _num(w["end"]["z"])
            ln = None if None in (sx, sz, ex, ez) else math.hypot(ex - sx, ez - sz)
        if ln is None:
            continue
        wl += ln
        wids.append(w["id"])
    add("WALL_LENGTH", wl, "m", wids, "sum of compiled wall segment lengths",
        C if len(wids) == len(arch["walls"]) else "PARTIAL")

    areas = [(_num(s.get("area_m2")), s["id"]) for s in arch["spaces"]]
    known = [(a, i) for a, i in areas if a is not None]
    add("SPACE_AREA", sum(a for a, _ in known), "m2", [i for _, i in known],
        "sum of canonical space areas",
        C if len(known) == len(areas) else "PARTIAL")

    slab_known = []
    fa = 0.0
    for s in arch["slabs"]:
        if "cells" in s:
            fa += sum(abs(POLY.signed_area(c)) for c in s["cells"])
            slab_known.append(s["id"])
            continue
        o = [_num(x) for x in (s.get("outline") or [])]
        if len(o) == 4 and all(x is not None for x in o):
            fa += o[2] * o[3]
            slab_known.append(s["id"])
    add("FLOOR_AREA", fa, "m2", slab_known,
        "sum of architectural slab outlines",
        C if len(slab_known) == len(arch["slabs"]) else "PARTIAL")

    def disc(qt, items, unit, basis, discipline_present):
        ids = [x["id"] for x in items]
        cov = C if discipline_present else "NOT_AVAILABLE"
        add(qt, (len(items) if discipline_present else None), unit, ids, basis, cov)
        if not discipline_present:
            issues.append(issue("DOC_QUANTITY_PARTIAL", "INFO", qt,
                                "no represented data for this discipline"))

    st_present = bool(st["columns"] or st["beams"] or st["slabs"]
                      or st["foundations"])
    disc("COLUMN_COUNT", st["columns"], "count", "represented columns", st_present)
    disc("BEAM_COUNT", st["beams"], "count", "represented beams", st_present)
    disc("FOUNDATION_COUNT", st["foundations"], "count",
         "represented foundations", st_present)
    bl, bids = 0.0, []
    for b in st["beams"]:
        ln = _num(b.get("length_m"))
        if ln is not None:
            bl += ln
            bids.append(b["id"])
    add("BEAM_LENGTH", (bl if st_present else None), "m", bids,
        "sum of represented beam lengths",
        (C if st_present and len(bids) == len(st["beams"]) else
         ("PARTIAL" if st_present else "NOT_AVAILABLE")))

    mp_present = bool(mp["equipment"] or mp["terminals"] or mp["segments"])
    disc("MEP_EQUIPMENT_COUNT", mp["equipment"], "count",
         "represented MEP equipment", mp_present)
    disc("MEP_TERMINAL_COUNT", mp["terminals"], "count",
         "represented MEP terminals", mp_present)
    routed = [s for s in mp["segments"] if _num((s.get("start") or {}).get("x"))
              is not None and _num((s.get("end") or {}).get("x")) is not None]
    sl = 0.0
    for s in routed:
        ln = _num(s.get("length_m"))
        if ln is not None:
            sl += ln
    add("MEP_SEGMENT_LENGTH", (sl if mp_present else None), "m",
        [s["id"] for s in routed], "sum of represented routed segment lengths",
        (C if mp_present and len(routed) == len(mp["segments"]) else
         ("PARTIAL" if mp_present else "NOT_AVAILABLE")))
    if mp_present and len(routed) != len(mp["segments"]):
        issues.append(issue("DOC_UNROUTED_SEGMENT", "INFO", "MEP_SEGMENT_LENGTH",
                            "unrouted segments are excluded rather than estimated"))

    fl_present = bool(fl["devices"] or fl["signs"])
    disc("FLS_DEVICE_COUNT", fl["devices"], "count",
         "represented fire and life-safety devices", fl_present)
    disc("FLS_SIGN_COUNT", fl["signs"], "count", "represented signage", fl_present)

    out.sort(key=lambda q: q["quantity_type"])
    report = {"report_id": artifact_id("quantity", {"r": "report", "h": mh}),
              "quantities": out, "count": len(out),
              "source_model_hash": mh,
              "source_revision": project.get("current_revision"),
              "is_bill_of_quantities": False,
              "is_cost_estimate": False,
              "writes_to_model": False,
              "note": "a factual model quantity report. Coverage is stated against "
                      "the represented model only; no cost, rate or price exists here",
              "spec_version": SPEC["documentation_spec_version"]}
    return {"valid": True, "report": report, "issues": issues}


# --------------------------------------------------------- الرسم المتّجه ----
def _fmt(v):
    """تنسيق رقم موحّد للمخرج المتّجه — يمنع انحراف النصّ بين التطبيقين."""
    n = round(float(v), 3) + 0.0
    if n == int(n):
        return str(int(n))
    return ("%.3f" % n).rstrip("0").rstrip(".")


def _esc(s):
    return (str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _fit(bounds, width_mm, height_mm, margin_mm, scale):
    """يحسب تحويل النموذج إلى الورق. المقياس الحقيقي يُعلَن أو يُقال إنه ملاءمة."""
    if bounds is None:
        return None
    if "min_x" in bounds:
        w = bounds["max_x"] - bounds["min_x"]
        h = bounds["max_z"] - bounds["min_z"]
        ox, oy = bounds["min_x"], bounds["min_z"]
    else:
        w = bounds["max_u"] - bounds["min_u"]
        h = bounds["max_v"] - bounds["min_v"]
        ox, oy = bounds["min_u"], bounds["min_v"]
    aw = max(width_mm - 2 * margin_mm, 1.0)
    ah = max(height_mm - 2 * margin_mm, 1.0)
    if scale:
        den = float(scale.split(":")[1])
        k = _MM_PER_M / den
        fits = (w * k <= aw + 1e-9) and (h * k <= ah + 1e-9)
        if fits:
            return {"k": k, "ox": ox, "oy": oy, "mode": "TRUE_SCALE",
                    "scale": scale, "fits": True}
    k = min(aw / w, ah / h) if w > 0 and h > 0 else 1.0
    return {"k": k, "ox": ox, "oy": oy, "mode": "FIT_TO_SHEET",
            "scale": None, "fits": False}


def _P(t, x, y, height_mm, margin_mm):
    """نقطة النموذج إلى إحداثيات الورق. المحور y ينقلب مرّة واحدة هنا فقط."""
    px = margin_mm + (x - t["ox"]) * t["k"]
    py = height_mm - margin_mm - (y - t["oy"]) * t["k"]
    return (px, py)


def _ink(mode):
    if mode == "PRESENTATION":
        return {"paper": "#12161c", "ink": "#e8e6e1", "thin": "#9aa4b0"}
    if mode == "TECHNICAL":
        return {"paper": "#ffffff", "ink": "#111111", "thin": "#555555"}
    return {"paper": SPEC["monochrome_paper"], "ink": SPEC["monochrome_ink"],
            "thin": SPEC["monochrome_ink"]}


def draw_ops(view, geom, dims, anns, width_mm, height_mm, margin_mm=12.0,
             mode=None):
    """يبني عمليات رسم مستقلّة عن الصيغة، فيتقاسمها SVG وPDF بلا ازدواج منطق."""
    mode = mode if mode in SPEC["drawing_modes"] else SPEC["default_drawing_mode"]
    t = _fit(geom.get("bounds"), width_mm, height_mm, margin_mm, view.get("scale"))
    ops = []
    if t is None:
        return {"ops": ops, "transform": None, "mode": mode,
                "scale_mode": "FIT_TO_SHEET", "scale": None}
    plan = "min_x" in (geom.get("bounds") or {})

    def pt(a, b):
        return _P(t, a, b, height_mm, margin_mm)

    def line(a, b, c, d, cls):
        x1, y1 = pt(a, b)
        x2, y2 = pt(c, d)
        ops.append({"op": "line", "x1": _q(x1), "y1": _q(y1), "x2": _q(x2),
                    "y2": _q(y2), "cls": cls})

    def rect(a, b, w, h, cls, fill=False):
        x1, y1 = pt(a, b)
        x2, y2 = pt(a + w, b + h)
        ops.append({"op": "rect", "x": _q(min(x1, x2)), "y": _q(min(y1, y2)),
                    "w": _q(abs(x2 - x1)), "h": _q(abs(y2 - y1)), "cls": cls,
                    "fill": bool(fill)})

    def text(a, b, s, cls, anchor="middle", size=2.6):
        x, y = pt(a, b)
        ops.append({"op": "text", "x": _q(x), "y": _q(y), "text": str(s),
                    "cls": cls, "anchor": anchor, "size": _q(size)})

    def polygon(ring, cls, fill=False):
        points = [[_q(v) for v in pt(*p)] for p in ring]
        ops.append({"op": "polygon", "points": points, "cls": cls, "fill": bool(fill),
                    "x": min(p[0] for p in points), "y": min(p[1] for p in points)})

    for e in geom["elements"]:
        c, gc = e["category"], e.get("geometry_class")
        cls = "CUT" if gc == "CUT" else ("PROJECTED" if gc == "PROJECTED"
                                         else "REFERENCE")
        if c == "SPACE" and plan:
            if e.get("shape") == "polygon":
                polygon(e["polygon"], "REFERENCE", fill=True)
            else:
                x, z, w, d = e["rect"]
                rect(x, z, w, d, "REFERENCE", fill=True)
        elif c == "SLAB" and plan and e.get("shape") == "cells":
            for a, b in _cell_edges(e["cells"]):
                line(*a, *b, "REFERENCE")
        elif c in ("SLAB", "STRUCTURAL_SLAB") and plan and e.get("shape") == "rect":
            x, z, w, d = e["rect"]
            rect(x, z, w, d, "REFERENCE")
        elif c == "VOID" and plan:
            x, z, w, d = e["rect"]
            rect(x, z, w, d, "PROJECTED")
        elif c == "WALL" and plan:
            line(e["start"][0], e["start"][1], e["end"][0], e["end"][1], "CUT")
        elif c in ("DOOR", "WINDOW") and plan:
            if e.get("shape") == "segment":
                line(e["start"][0], e["start"][1], e["end"][0], e["end"][1],
                     "ANNOTATION")
            elif e.get("x") is not None:
                rect(e["x"] - 0.05, e["z"] - 0.05, 0.1, 0.1, "ANNOTATION")
        elif c == "GRID" and plan:
            b = geom["bounds"]
            if e.get("axis") == "X":
                line(e["position"], b["min_z"], e["position"], b["max_z"], "GRID")
            else:
                line(b["min_x"], e["position"], b["max_x"], e["position"], "GRID")
        elif c == "MEP_SEGMENT" and e.get("shape") == "segment":
            line(e["start"][0], e["start"][1], e["end"][0], e["end"][1], "PROJECTED")
        elif c == "BEAM" and e.get("shape") == "segment" and plan:
            line(e["start"][0], e["start"][1], e["end"][0], e["end"][1], "PROJECTED")
        elif e.get("shape") in ("point", "point_or_rect") and plan:
            if e.get("x") is not None:
                rect(e["x"] - 0.15, e["z"] - 0.15, 0.3, 0.3,
                     "COORDINATION" if c == "CLASH" else cls)
        elif e.get("shape") == "rect_uv":
            u0, u1 = e["u0"], e["u1"]
            v0 = e.get("v0")
            v1 = e.get("v1")
            if v0 is None or v1 is None:
                # ارتفاع غير مذكور: يُرسم خطّ القاعدة فقط، ولا يُخترع ارتفاع
                base = v0 if v0 is not None else (v1 if v1 is not None else 0.0)
                line(u0, base, u1, base, "UNRESOLVED" if cls == "CUT" else cls)
                continue
            rect(u0, min(v0, v1), u1 - u0, abs(v1 - v0), cls)
        elif e.get("shape") == "level":
            b = geom.get("bounds") or {}
            if "min_u" in b:
                line(b["min_u"], e["elevation"], b["max_u"], e["elevation"],
                     "REFERENCE")
    for a in anns.get("annotations", []):
        if a["x"] is None or a["y"] is None:
            continue
        text(a["x"], a["y"], a["text"], "ANNOTATION")
    ops.sort(key=lambda o: (o["op"], o.get("cls", ""), o.get("x", o.get("x1", 0)),
                            o.get("y", o.get("y1", 0)), str(o.get("text", ""))))
    return {"ops": ops, "transform": {"k": _q(t["k"]), "ox": _q(t["ox"]),
                                      "oy": _q(t["oy"])},
            "mode": mode, "scale_mode": t["mode"], "scale": t["scale"],
            "paper_mm": [_q(width_mm), _q(height_mm)]}


def view_svg(view, geom, dims, anns, options=None):
    """SVG متّجه حقيقي. لا صورة منقّطة تحلّ محلّ الرسم."""
    o = options if isinstance(options, dict) else {}
    paper = o.get("paper_size") if o.get("paper_size") in PAPER else "A3"
    w_mm, h_mm = PAPER[paper]
    if o.get("orientation") == "PORTRAIT":
        w_mm, h_mm = h_mm, w_mm
    mode = o.get("mode") if o.get("mode") in SPEC["drawing_modes"] else "MONOCHROME"
    d = draw_ops(view, geom, dims, anns, w_mm, h_mm, 12.0, mode)
    col = _ink(mode)
    p = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" '
         'viewBox="0 0 %s %s" data-acs-doc="1" data-view-type="%s" '
         'data-view-id="%s" data-model-hash="%s" data-scale-mode="%s" '
         'data-construction-drawing="false">'
         % (_fmt(w_mm), _fmt(h_mm), _fmt(w_mm), _fmt(h_mm),
            _esc(view["view_type"]), _esc(view["view_id"]),
            _esc(view["source_model_hash"]), _esc(d["scale_mode"]))]
    p.append('<rect x="0" y="0" width="%s" height="%s" fill="%s"/>'
             % (_fmt(w_mm), _fmt(h_mm), col["paper"]))
    for op in d["ops"]:
        cls = op.get("cls", "PROJECTED")
        lw = LINE_W.get(cls, 0.25)
        stroke = col["ink"] if cls in ("CUT", "COORDINATION") else col["thin"]
        dash = ' stroke-dasharray="1.6 1.2"' if SPEC["line_styles"].get(cls) == "dash" \
            else ""
        if op["op"] == "line":
            p.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                     'stroke-width="%s"%s data-cls="%s"/>'
                     % (_fmt(op["x1"]), _fmt(op["y1"]), _fmt(op["x2"]),
                        _fmt(op["y2"]), stroke, _fmt(lw), dash, cls))
        elif op["op"] == "rect":
            fill = col["thin"] if op.get("fill") else "none"
            fo = ' fill-opacity="0.06"' if op.get("fill") else ""
            p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"%s '
                     'stroke="%s" stroke-width="%s"%s data-cls="%s"/>'
                     % (_fmt(op["x"]), _fmt(op["y"]), _fmt(op["w"]), _fmt(op["h"]),
                        fill, fo, stroke, _fmt(lw), dash, cls))
        elif op["op"] == "polygon":
            points = " ".join("%s,%s" % (_fmt(x), _fmt(y)) for x, y in op["points"])
            fill = col["thin"] if op.get("fill") else "none"
            fo = ' fill-opacity="0.06"' if op.get("fill") else ""
            p.append('<polygon points="%s" fill="%s"%s stroke="%s" '
                     'stroke-width="%s"%s data-cls="%s"/>'
                     % (points, fill, fo, stroke, _fmt(lw), dash, cls))
        elif op["op"] == "text":
            p.append('<text x="%s" y="%s" font-family="monospace" font-size="%s" '
                     'text-anchor="%s" fill="%s" data-cls="%s">%s</text>'
                     % (_fmt(op["x"]), _fmt(op["y"]), _fmt(op["size"]),
                        op.get("anchor", "middle"), col["ink"], cls,
                        _esc(op["text"])))
    p.append('<text x="12" y="%s" font-family="monospace" font-size="2.4" '
             'fill="%s">%s</text>'
             % (_fmt(h_mm - 5.0), col["thin"],
                _esc("model-derived documentation — not a construction drawing")))
    p.append('</svg>')
    text = "\n".join(p)
    return {"svg": text, "byte_length": len(text.encode("utf-8")),
            "scale_mode": d["scale_mode"], "scale": d["scale"],
            "op_count": len(d["ops"]), "paper_size": paper,
            "file_hash": _sha256_text(text)}


# --------------------------------------------------------- اللوحات (§45) ----
def title_block(project, fields=None):
    """بلوك عنوان محايد. الحقل المجهول يبقى فارغاً ولا يُخترع اسم ولا ختم."""
    f = fields if isinstance(fields, dict) else {}
    out, issues = {}, []
    for k in SPEC["title_block_fields"]:
        v = f.get(k)
        if v is None:
            out[k] = None
            continue
        if not isinstance(v, str):
            v = str(v)
        if is_unsafe(v):
            issues.append(issue("DOC_UNSAFE_STRING", "ERROR", k,
                                "the title block field is refused as unsafe"))
            out[k] = None
            continue
        out[k] = v[:256]
    for bad in SPEC["forbidden_title_block_content"]:
        if bad in f:
            issues.append(issue("DOC_MALFORMED_DEFINITION", "WARNING", bad,
                                "this field is not part of the neutral title block"))
    st = f.get("status")
    if st in SPEC["restricted_statuses"]:
        issues.append(issue("DOC_RESTRICTED_STATUS_REFUSED", "ERROR", st,
                            "a restricted status requires an explicit authorised "
                            "user action and is not set by the system"))
        out["status"] = None
    elif st not in SPEC["drawing_statuses"]:
        out["status"] = "DRAFT" if st is None else None
        if st is not None:
            issues.append(issue("DOC_MALFORMED_DEFINITION", "WARNING", st,
                                "unknown drawing status"))
    out["title_block_id"] = artifact_id("legend", {"tb": out})
    out["generated_fields_invented"] = False
    return {"valid": not any(i["blocking"] for i in issues),
            "title_block": out, "issues": issues}


def compose_sheet(project, spec, views_by_id, schedules_by_id=None):
    """تركيب لوحة: تصادم المناظر يُكشف ويُبلَّغ، ولا يُزاح محتوى هندسي بصمت."""
    d = spec if isinstance(spec, dict) else {}
    issues = []
    paper = d.get("paper_size")
    if paper not in PAPER:
        return {"valid": False, "sheet": None,
                "issues": [issue("DOC_INVALID_PAPER_SIZE", "ERROR", paper,
                                 "paper size is not declared")]}
    orient = d.get("orientation") or "LANDSCAPE"
    if orient not in SPEC["orientations_sheet"]:
        return {"valid": False, "sheet": None,
                "issues": [issue("DOC_INVALID_ORIENTATION", "ERROR", orient,
                                 "sheet orientation is not declared")]}
    w_mm, h_mm = PAPER[paper]
    if orient == "PORTRAIT":
        w_mm, h_mm = h_mm, w_mm
    name = d.get("sheet_name")
    if isinstance(name, str) and is_unsafe(name):
        issues.append(issue("DOC_UNSAFE_STRING", "ERROR", "sheet_name",
                            "the sheet name is refused as unsafe"))
        name = None
    tb = title_block(project, d.get("title_block"))
    issues += tb["issues"]
    vps, seen_ids = [], set()
    raw = d.get("viewports") or []
    if len(raw) > int(LIMITS["max_viewports_per_sheet"]):
        return {"valid": False, "sheet": None,
                "issues": [issue("DOC_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                                 "too many viewports for one sheet")]}
    for i, v in enumerate(raw):
        vid = v.get("view_id")
        if vid not in views_by_id:
            issues.append(issue("DOC_MALFORMED_DEFINITION", "ERROR", vid,
                                "the viewport references an unknown view"))
            continue
        x, y = _num(v.get("x")), _num(v.get("y"))
        w, h = _num(v.get("width")), _num(v.get("height"))
        if None in (x, y, w, h) or w <= 0 or h <= 0:
            issues.append(issue("DOC_NON_FINITE_GEOMETRY", "ERROR", vid,
                                "the viewport rectangle is not finite and positive"))
            continue
        if x < 0 or y < 0 or x + w > w_mm + 1e-9 or y + h > h_mm + 1e-9:
            issues.append(issue("DOC_VIEWPORT_OUT_OF_SHEET", "ERROR", vid,
                                "the viewport leaves the sheet; it is reported, "
                                "not moved"))
            continue
        vp = {"viewport_id": artifact_id("viewport",
                                         {"v": vid, "x": x, "y": y, "w": w, "h": h}),
              "view_id": vid, "x": _q(x), "y": _q(y), "width": _q(w),
              "height": _q(h),
              "scale": views_by_id[vid].get("scale"),
              "scale_mode": views_by_id[vid].get("scale_mode"),
              "crop": views_by_id[vid].get("crop_region")}
        if vp["viewport_id"] in seen_ids:
            issues.append(issue("DOC_DUPLICATE_ARTIFACT_ID", "ERROR",
                                vp["viewport_id"], "duplicate viewport identity"))
            continue
        seen_ids.add(vp["viewport_id"])
        vps.append(vp)
    for i in range(len(vps)):
        for j in range(i + 1, len(vps)):
            a, b = vps[i], vps[j]
            if (a["x"] < b["x"] + b["width"] - 1e-9
                    and b["x"] < a["x"] + a["width"] - 1e-9
                    and a["y"] < b["y"] + b["height"] - 1e-9
                    and b["y"] < a["y"] + a["height"] - 1e-9):
                issues.append(issue("DOC_VIEWPORT_COLLISION", "WARNING",
                                    a["viewport_id"],
                                    "viewport %s overlaps %s; engineering content "
                                    "is reported, never silently moved"
                                    % (a["view_id"], b["view_id"])))
    sch = [s for s in (d.get("schedules") or [])
           if not schedules_by_id or s in schedules_by_id]
    notes = []
    for n in (d.get("notes") or [])[:int(LIMITS["max_notes_per_sheet"])]:
        t = n.get("text") if isinstance(n, dict) else n
        if isinstance(t, str) and len(t) <= int(LIMITS["max_note_length"]):
            notes.append({"text": t, "provenance": "USER_AUTHORED"})
    ident = {"n": d.get("sheet_number"), "p": paper, "o": orient,
             "v": [v["viewport_id"] for v in vps], "s": sch,
             "h": project.get("model_hash")}
    sheet = {"sheet_id": artifact_id("sheet", ident),
             "sheet_number": d.get("sheet_number"),
             "sheet_name": name, "paper_size": paper, "orientation": orient,
             "paper_mm": [_q(w_mm), _q(h_mm)],
             "title_block_id": tb["title_block"]["title_block_id"],
             "title_block": tb["title_block"],
             "viewports": vps, "views": [v["view_id"] for v in vps],
             "schedules": sch, "legends": [], "notes": notes,
             "revision": d.get("revision") or "A",
             "status": tb["title_block"].get("status"),
             "source_model_hash": project.get("model_hash"),
             "source_revision": project.get("current_revision"),
             "writes_to_model": False,
             "spec_version": SPEC["documentation_spec_version"]}
    return {"valid": not any(i["blocking"] for i in issues),
            "sheet": sheet, "issues": issues}


def legend_for(document):
    """أسطورة من الرموز المستعملة فعلاً في الحزمة، لا من فهرس رموز مُتخيَّل."""
    used = set()
    for v in document.get("views", []):
        for c in (v.get("counts") or {}):
            used.add(c)
    entries = [{"category": c, "line_class": ("CUT" if c in ("WALL", "SLAB")
                                              else "PROJECTED"),
                "line_weight_mm": LINE_W.get("CUT" if c in ("WALL", "SLAB")
                                             else "PROJECTED")}
               for c in sorted(used)]
    return {"legend_id": artifact_id("legend", {"u": sorted(used)}),
            "entries": entries, "count": len(entries),
            "note": "only symbols actually used in this documentation set appear"}


def drawing_index(sheets, prefixes=None):
    """سجلّ لوحات حتمي. البادئات قابلة للتهيئة ولا يُستنتَج وضع إصدار مهني."""
    px = dict(SPEC["discipline_prefixes"])
    if isinstance(prefixes, dict):
        for k, v in prefixes.items():
            if k in px and isinstance(v, str) and v:
                px[k] = v
    rows = []
    for s in sheets:
        rows.append({"sheet_id": s["sheet_id"], "sheet_number": s.get("sheet_number"),
                     "sheet_name": s.get("sheet_name"),
                     "revision": s.get("revision"),
                     "status": s.get("status"),
                     "source_model_hash": s.get("source_model_hash")})
    rows.sort(key=lambda r: str(r["sheet_number"] or r["sheet_id"]))
    return {"index_id": artifact_id("legend", {"idx": [r["sheet_id"] for r in rows]}),
            "prefixes": px, "rows": rows, "count": len(rows),
            "issuance_status_inferred": False}


# --------------------------------------------------- القِدَم وإعادة التوليد ----
def staleness(artifact, project):
    """قِدَم صريح. لا إعادة توليد تلقائية تُخفي أن النموذج تحرّك."""
    a_h = artifact.get("source_model_hash")
    p_h = project.get("model_hash")
    if a_h != p_h:
        return {"status": "STALE_MODEL_CHANGED",
                "artifact_model_hash": a_h, "current_model_hash": p_h,
                "artifact_revision": artifact.get("source_revision"),
                "current_revision": project.get("current_revision"),
                "auto_regenerated": False, "auto_deleted": False}
    return {"status": "CURRENT", "artifact_model_hash": a_h,
            "current_model_hash": p_h,
            "artifact_revision": artifact.get("source_revision"),
            "current_revision": project.get("current_revision"),
            "auto_regenerated": False, "auto_deleted": False}


def documentation_project(project, views=None, sheets=None, schedules=None,
                          quantity_report=None, export_sets=None,
                          documentation_revision="A", generated_at=None,
                          history=None):
    """مشروع توثيق مشتقّ من النموذج القانوني. لا يحمل هندسةً ثانية."""
    v = list(views or [])
    s = list(sheets or [])
    sc = list(schedules or [])
    ident = {"p": project.get("model_hash"),
             "v": sorted(x["view_id"] for x in v),
             "s": sorted(x["sheet_id"] for x in s),
             "sc": sorted(x["schedule_id"] for x in sc),
             "r": documentation_revision}
    doc = {"schema": SCHEMA, "version": VERSION,
           "documentation_id": artifact_id("documentation", ident),
           "project_id": project.get("building_id"),
           "model_hash": project.get("model_hash"),
           "documentation_revision": documentation_revision,
           "source_revision": project.get("current_revision"),
           "documentation_spec_version": SPEC["documentation_spec_version"],
           "views": v, "sheets": s, "schedules": sc,
           "quantity_report": quantity_report,
           "legends": [], "title_blocks": [x.get("title_block") for x in s
                                           if x.get("title_block")],
           "drawing_index": drawing_index(s),
           "export_sets": list(export_sets or []),
           "history": list(history or []),
           "metadata": {"compiler_version": COMPILER,
                        "read_only": True, "writes_to_model": False},
           "generated_at": generated_at,
           "note": "documentation derived from the canonical model. It carries no "
                   "engineering authority and never writes back."}
    doc["legends"] = [legend_for(doc)]
    return doc


def regenerate(document, project, generated_at=None):
    """إعادة التوليد تُنشئ مراجعة توثيق جديدة وتحفظ السابقة."""
    prev = document.get("documentation_revision") or "A"
    nxt = chr(ord(prev[0]) + 1) if len(prev) == 1 and prev.isalpha() else prev + "1"
    record = {"revision": prev,
              "date": document.get("generated_at"),
              "description": "superseded by regeneration",
              "source_model_revision": document.get("source_revision"),
              "source_model_hash": document.get("model_hash"),
              "changed_sheets": [s["sheet_id"] for s in document.get("sheets", [])],
              "documentation_id": document.get("documentation_id"),
              "state": "SUPERSEDED"}
    hist = list(document.get("history") or []) + [record]
    return {"previous_revision": prev, "new_revision": nxt,
            "history": hist, "preserved": True,
            "previous_documentation_id": document.get("documentation_id"),
            "generated_at": generated_at}


def impact(document, project_before, project_after):
    """أثر تعديل النموذج على مصنوعات التوثيق — وقائع لا أحكام هندسية."""
    changed = project_before.get("model_hash") != project_after.get("model_hash")
    aff_v = [v["view_id"] for v in document.get("views", [])
             if v.get("source_model_hash") != project_after.get("model_hash")]
    aff_s = [s["sheet_id"] for s in document.get("sheets", [])
             if s.get("source_model_hash") != project_after.get("model_hash")]
    aff_sc = [s["schedule_id"] for s in document.get("schedules", [])
              if s.get("source_model_hash") != project_after.get("model_hash")]
    qr = document.get("quantity_report") or {}
    aff_q = ([qr.get("report_id")]
             if qr and qr.get("source_model_hash") != project_after.get("model_hash")
             else [])
    return {"model_changed": changed,
            "previous_model_hash": project_before.get("model_hash"),
            "current_model_hash": project_after.get("model_hash"),
            "affected_views": sorted(aff_v),
            "affected_sheets": sorted(aff_s),
            "affected_schedules": sorted(aff_sc),
            "affected_quantities": sorted(x for x in aff_q if x),
            "state": "STALE_MODEL_CHANGED" if changed else "CURRENT",
            "auto_regenerated": False,
            "engineering_validity_claimed": False,
            "note": "impact is reported by model hash only. No claim is made that "
                    "an unaffected drawing is engineering-valid beyond that."}


def revision_clouds(impact_report, geom_before, geom_after):
    """سُحُب مراجعة من فرق حقيقي فقط، وبلا تفسير هندسي للتغيير."""
    if not impact_report.get("model_changed"):
        return {"clouds": [], "basis": "NO_DIFF", "count": 0}
    a = {e["id"]: e for e in (geom_before or {}).get("elements", [])}
    b = {e["id"]: e for e in (geom_after or {}).get("elements", [])}
    clouds = []
    for eid in sorted(set(a) | set(b)):
        ea, eb = a.get(eid), b.get(eid)
        if _canon(ea) == _canon(eb):
            continue
        ref = eb or ea
        box = None
        if ref.get("shape") in ("rect", "polygon", "cells"):
            x, z, w, d = ref["rect"]
            box = [_q(x), _q(z), _q(w), _q(d)]
        elif ref.get("shape") == "segment":
            xs = [ref["start"][0], ref["end"][0]]
            zs = [ref["start"][1], ref["end"][1]]
            box = [_q(min(xs)), _q(min(zs)), _q(max(xs) - min(xs)),
                   _q(max(zs) - min(zs))]
        clouds.append({"element_id": eid, "box": box,
                       "change": ("ADDED" if ea is None else
                                  ("REMOVED" if eb is None else "MODIFIED")),
                       "interpretation": None})
    return {"clouds": clouds, "count": len(clouds), "basis": "DOCUMENTATION_DIFF",
            "engineering_interpretation": False}


# ------------------------------------------------------------- PDF (§70) ----
def _pdf_escape(s):
    return (str(s).replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)"))


def _pdf_text_safe(s):
    """PDF WinAnsi يكتب البايت الواحد. ما خرج عنه يُستبدل بعلامة، ولا يُدَّعى
    أنه رُسم. النصّ الكامل يبقى في حزمة JSON وفي SVG."""
    out = []
    for ch in str(s):
        o = ord(ch)
        out.append(ch if 32 <= o <= 126 else "?")
    return "".join(out)


def sheet_pdf(sheets, drawings, generated_at=None, producer=None):
    """يكتب PDF حقيقياً: ترويسة، فهرس، شجرة صفحات، صفحة لكل لوحة بـ MediaBox
    صريح، تدفّقات محتوى غير مضغوطة من عمليات متّجهة، ثمّ xref ومقطورة."""
    pages = []
    for sh in sheets:
        w_mm, h_mm = sh["paper_mm"]
        w_pt, h_pt = w_mm * _PT_PER_MM, h_mm * _PT_PER_MM
        ops = []
        ops.append("q")
        ops.append("1 1 1 rg 0 0 %s %s re f" % (_fmt(w_pt), _fmt(h_pt)))
        ops.append("0 0 0 RG")
        for vp in sh["viewports"]:
            d = drawings.get(vp["view_id"])
            if not d:
                continue
            sx = vp["width"] / max(d["paper_mm"][0], 1e-9)
            sy = vp["height"] / max(d["paper_mm"][1], 1e-9)
            k = min(sx, sy)
            ox = vp["x"] * _PT_PER_MM
            oy = (h_mm - vp["y"] - vp["height"]) * _PT_PER_MM
            ops.append("q")
            ops.append("%s 0 0 %s %s %s cm" % (_fmt(k * _PT_PER_MM),
                                               _fmt(k * _PT_PER_MM),
                                               _fmt(ox), _fmt(oy)))
            for op in d["ops"]:
                cls = op.get("cls", "PROJECTED")
                lw = LINE_W.get(cls, 0.25)
                ops.append("%s w" % _fmt(lw))
                if op["op"] == "line":
                    ops.append("%s %s m %s %s l S"
                               % (_fmt(op["x1"]), _fmt(d["paper_mm"][1] - op["y1"]),
                                  _fmt(op["x2"]), _fmt(d["paper_mm"][1] - op["y2"])))
                elif op["op"] == "rect":
                    ops.append("%s %s %s %s re S"
                               % (_fmt(op["x"]),
                                  _fmt(d["paper_mm"][1] - op["y"] - op["h"]),
                                  _fmt(op["w"]), _fmt(op["h"])))
                elif op["op"] == "polygon":
                    path = " ".join("%s %s %s" % (_fmt(x), _fmt(d["paper_mm"][1]-y),
                                    "m" if i == 0 else "l")
                                    for i, (x, y) in enumerate(op["points"]))
                    ops.append(path + " h S")
                elif op["op"] == "text":
                    ops.append("BT /F1 %s Tf %s %s Td (%s) Tj ET"
                               % (_fmt(op["size"]), _fmt(op["x"]),
                                  _fmt(d["paper_mm"][1] - op["y"]),
                                  _pdf_escape(_pdf_text_safe(op["text"]))))
            ops.append("Q")
            ops.append("0.2 w %s %s %s %s re S"
                       % (_fmt(ox), _fmt(oy), _fmt(vp["width"] * _PT_PER_MM),
                          _fmt(vp["height"] * _PT_PER_MM)))
        tb = sh.get("title_block") or {}
        y = 10.0
        for key in ("sheet_number", "sheet_title", "revision", "scale", "status"):
            val = tb.get(key)
            ops.append("BT /F1 7 Tf %s %s Td (%s) Tj ET"
                       % (_fmt(10.0), _fmt(y),
                          _pdf_escape(_pdf_text_safe(
                              "%s: %s" % (key, val if val is not None
                                          else SPEC["unknown_display"])))))
            y += 9.0
        ops.append("BT /F1 6 Tf %s %s Td (%s) Tj ET"
                   % (_fmt(10.0), _fmt(y),
                      _pdf_escape("model-derived documentation - "
                                  "not a construction drawing")))
        ops.append("Q")
        pages.append({"w_pt": w_pt, "h_pt": h_pt, "stream": "\n".join(ops),
                      "sheet_id": sh["sheet_id"]})

    objs = []
    n_pages = len(pages)
    font_obj = 3 + 2 * n_pages
    kids = " ".join("%d 0 R" % (3 + 2 * i) for i in range(n_pages))
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pages))
    for i, p in enumerate(pages):
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] "
                    "/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                    % (_fmt(p["w_pt"]), _fmt(p["h_pt"]), font_obj, 4 + 2 * i))
        objs.append("<< /Length %d >>\nstream\n%s\nendstream"
                    % (len(p["stream"].encode("latin-1", "replace")), p["stream"]))
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                "/Encoding /WinAnsiEncoding >>")

    out = "%PDF-" + SPEC["pdf_version"] + "\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    for i, body in enumerate(objs):
        offsets.append(len(out.encode("latin-1", "replace")))
        out += "%d 0 obj\n%s\nendobj\n" % (i + 1, body)
    xref_at = len(out.encode("latin-1", "replace"))
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += "%010d 00000 n \n" % off
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref_at))
    data = out.encode("latin-1", "replace")
    return {"pdf": data, "byte_length": len(data), "page_count": n_pages,
            "media_boxes": [[_q(p["w_pt"]), _q(p["h_pt"])] for p in pages],
            "content_streams": [p["stream"] for p in pages],
            "sheet_ids": [p["sheet_id"] for p in pages],
            "file_hash": _sha256_text(out),
            "semantic_hash": _sha16({"m": [[_q(p["w_pt"]), _q(p["h_pt"])]
                                           for p in pages],
                                     "s": [p["stream"] for p in pages]}),
            "cad_interoperability_claimed": False}


# --------------------------------------------------------- التصدير (§68) ----
def export_package(document, files=None, generated_at=None):
    """حزمة توثيق مقروءة آلياً + بيان يربط كل ملفّ ببصمة النموذج الذي أنتجه."""
    issues = []
    recs = []
    for f in (files or []):
        name = safe_filename(f.get("file_name"))
        if name is None:
            issues.append(issue("DOC_UNSAFE_FILENAME", "ERROR", f.get("file_name"),
                                "the export filename is refused by the allow-list"))
            continue
        raw = f.get("file_name") or ""
        if any(p in raw for p in ("../", "..\\")) or raw.startswith("/"):
            issues.append(issue("DOC_PATH_TRAVERSAL_REFUSED", "ERROR", raw,
                                "the export name attempts to leave its directory"))
            continue
        fmt = f.get("format")
        if fmt not in SPEC["export_formats"]:
            issues.append(issue("DOC_EXPORT_FAILED", "ERROR", name,
                                "unsupported export format"))
            continue
        recs.append({"file_name": name, "format": fmt,
                     "artifact_id": f.get("artifact_id"),
                     "sheet_id": f.get("sheet_id"),
                     "byte_length": int(f.get("byte_length") or 0),
                     "file_hash": f.get("file_hash"),
                     "generation_mode": f.get("generation_mode")
                     or "DETERMINISTIC_VECTOR"})
    if len(recs) > int(LIMITS["max_export_files"]):
        issues.append(issue("DOC_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                            "too many files in one export package"))
        recs = recs[:int(LIMITS["max_export_files"])]
    recs.sort(key=lambda r: r["file_name"])
    pkg = {
        "schema": SCHEMA,
        "documentation_id": document.get("documentation_id"),
        "documentation_revision": document.get("documentation_revision"),
        "model_hash": document.get("model_hash"),
        "source_revision": document.get("source_revision"),
        "spec_version": SPEC["documentation_spec_version"],
        "views": [{"view_id": v["view_id"], "view_type": v["view_type"],
                   "level_id": v.get("level_id"), "discipline": v.get("discipline"),
                   "scale": v.get("scale"), "scale_mode": v.get("scale_mode"),
                   "status": v.get("status"),
                   "source_model_hash": v.get("source_model_hash")}
                  for v in document.get("views", [])],
        "sheets": [{"sheet_id": s["sheet_id"], "sheet_number": s.get("sheet_number"),
                    "paper_size": s.get("paper_size"),
                    "views": s.get("views"), "revision": s.get("revision"),
                    "source_model_hash": s.get("source_model_hash")}
                   for s in document.get("sheets", [])],
        "schedules": [{"schedule_id": s["schedule_id"],
                       "schedule_type": s["schedule_type"],
                       "row_count": s["row_count"],
                       "unknown_cell_count": s.get("unknown_cell_count"),
                       "source_model_hash": s.get("source_model_hash")}
                      for s in document.get("schedules", [])],
        "quantities": (document.get("quantity_report") or {}).get("quantities", []),
        "artifact_ids": sorted(
            [v["view_id"] for v in document.get("views", [])]
            + [s["sheet_id"] for s in document.get("sheets", [])]
            + [s["schedule_id"] for s in document.get("schedules", [])]),
        "provenance": {"compiler_version": COMPILER,
                       "derived_from": "CANONICAL_MODEL",
                       "derived_from_ifc": False,
                       "writes_to_model": False},
        "staleness_state": "CURRENT",
        "is_bill_of_quantities": False,
        "construction_drawing_claimed": False,
    }
    text = _canon(pkg)
    manifest = {
        "manifest_id": artifact_id("manifest",
                                   {"d": pkg["documentation_id"],
                                    "f": [r["file_name"] for r in recs]}),
        "documentation_id": pkg["documentation_id"],
        "documentation_revision": pkg["documentation_revision"],
        "model_hash": pkg["model_hash"],
        "source_revision": pkg["source_revision"],
        "files": recs,
        "artifact_ids": pkg["artifact_ids"],
        "sheet_ids": [s["sheet_id"] for s in document.get("sheets", [])],
        "generated_at": generated_at,
        "spec_version": SPEC["documentation_spec_version"],
    }
    return {"valid": not any(i["blocking"] for i in issues),
            "package": pkg, "package_json": text,
            "package_hash": _sha256_text(text),
            "manifest": manifest, "issues": issues}


def export_set(name, purpose, sheet_ids, formats, created_at=None):
    """حزمة تصدير: اسمها بيانات وصفية للمستعمل ولا تعني سلطةً ولا اعتماداً."""
    issues = []
    if isinstance(name, str) and is_unsafe(name):
        issues.append(issue("DOC_UNSAFE_STRING", "ERROR", "name",
                            "the export set name is refused as unsafe"))
        name = None
    fs = [f for f in (formats or []) if f in SPEC["export_formats"]]
    return {"valid": not any(i["blocking"] for i in issues),
            "export_set": {"export_set_id": artifact_id(
                "export_set", {"n": name, "s": sorted(sheet_ids or []), "f": sorted(fs)}),
                "name": name, "purpose": purpose,
                "sheets": sorted(sheet_ids or []), "formats": sorted(fs),
                "created_at": created_at,
                "implies_authority": False, "implies_approval": False},
            "issues": issues}


# ------------------------------------------------------- التحقّق الشامل ----
def build_view(project, spec, src=None, notes=None):
    """يبني منظراً كاملاً: تعريف، هندسة، مقاسات، تأشيرات — دون لمس النموذج."""
    before = project.get("model_hash")
    if src is None:
        src = sources(project)
    vd = view_definition(project, spec, src["arch"])
    if not vd["valid"]:
        return {"valid": False, "view": None, "issues": vd["issues"]}
    view = vd["view"]
    vt = view["view_type"]
    if vt == "ELEVATION":
        geom = elevation_geometry(project, view, src)
    elif vt == "SECTION":
        geom = section_geometry(project, view, src)
    else:
        geom = plan_geometry(project, view, src)
    dims = dimensions(project, view, geom, src)
    anns = annotations(project, view, geom, notes, src)
    if project.get("model_hash") != before:
        raise RuntimeError("documentation changed the engineering model")
    view = dict(view)
    view["counts"] = geom.get("counts")
    return {"valid": True, "view": view, "geometry": geom, "dimensions": dims,
            "annotations": anns,
            "issues": vd["issues"] + geom["issues"] + dims["issues"]
            + anns["issues"]}


def verify_no_mutation(project_before_json, project):
    """إثبات مباشر أن بايتات النموذج القانوني لم تتغيّر."""
    now = _canon(project.get("model"))
    return {"unchanged": now == project_before_json,
            "model_hash": project.get("model_hash")}
