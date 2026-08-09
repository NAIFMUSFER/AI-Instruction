# -*- coding: utf-8 -*-
# =============================================================================
# acs_struct.py — أساس النموذج الإنشائي: تمثيل فقط، لا تصميم.
#
# يمثّل: شبكات محاور · أعمدة · جسور · بلاطات إنشائية · جدران إنشائية · أساسات ·
# نوى إنشائية · عقد · علاقات. النوع نفسه لكل أنواع المباني.
#
# مبادئ صارمة:
#   • لا حساب أحمال (ميتة/حية/رياح/زلازل) ولا تصميم مقاطع ولا تسليح ولا أساسات.
#   • لا ادّعاء سلامة أو كفاية أو مطابقة كود. لا قيم SBC/ACI/ASCE/AISC/Eurocode.
#   • النظام الإنشائي لا يُستنتج من نوع المبنى: لا خرسانة لأنها فيلا، ولا حديد
#     لأنه مستودع.
#   • ما لم يذكره النموذج يبقى null، ويظهر احتياط العرض منفصلاً بمصدر
#     display_fallback ولا يُرقّى أبداً إلى بيانات إنشائية.
#   • الاتصال الهندسي ليس مسار حمل. لا نستنتج مسارات أحمال.
#   • الجدار المعماري ليس جداراً إنشائياً، وبئر المصعد ليس نواة قص، بلا دليل.
#   • المصرِّف حتمي: نفس النموذج ⇒ نفس المعرّفات والنتائج.
# =============================================================================
import json
import math
import os

import acs_arch as ARCH

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_struct.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
COMPILER_VERSION = SPEC["compiler_version"]
ELEMENT_TYPES = tuple(SPEC["element_types"])
MODEL_STATUS = tuple(SPEC["model_status"])
PROVENANCE = tuple(SPEC["provenance_values"])
VERIFIED_SOURCES = tuple(SPEC["verified_sources"])
MATERIALS = tuple(SPEC["materials"])
SECTION_SHAPES = tuple(SPEC["section_shapes"])
FOUNDATION_TYPES = tuple(SPEC["foundation_types"])
STRUCTURAL_ROLES = tuple(SPEC["structural_roles"])
ALIGNMENT_STATES = tuple(SPEC["alignment_states"])
REL_TYPES = tuple(SPEC["relationship_types"])
REL_STATUSES = tuple(SPEC["relationship_statuses"])
SEVERITIES = tuple(SPEC["issue_severities"])
ISSUE_CODES = SPEC["issue_codes"]
FALLBACKS = SPEC["display_fallbacks"]

_EPS = 1e-6
_POS_TOL = 0.01        # تسامح تطابق الموضع بين مستويين (م) — هندسي بحت
_OFFSET_TOL = 1.00     # ما دون هذا يوصف إزاحة، وما فوقه انقطاع محور (م)


def severity_of(code):
    return ISSUE_CODES.get(code, "WARNING")


def _num(v):
    """رقم حقيقي أو None. NaN/inf ليست أرقاماً ولا تُمرَّر بصمت."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _is_bad_number(v):
    """قيمة مذكورة لكنها ليست رقماً صالحاً (NaN/inf/نص)."""
    return v is not None and not isinstance(v, bool) and _num(v) is None


def _src(v, default="unknown"):
    s = str(v).lower() if v is not None else default
    return s if s in PROVENANCE else "unknown"


def _prop(stated, source):
    """خاصية اختيارية: قيمة + مصدرها. الغياب يبقى غياباً."""
    n = _num(stated)
    if n is None:
        return {"value": None, "source": "unknown"}
    return {"value": n, "source": _src(source, "imported")}


def _fallback(value, key):
    """قيمة دلالية + احتياط عرض منفصل. الاحتياط ليس حقيقة إنشائية أبداً."""
    n = _num(value)
    if n is None:
        return {"value": None, "render_fallback": FALLBACKS[key],
                "source": "unknown", "render_source": "display_fallback"}
    return {"value": n, "render_fallback": FALLBACKS[key],
            "source": "imported", "render_source": "model"}


def _raw(building):
    st = building.get("structural")
    return st if isinstance(st, dict) else {}


def _levels_index(building, bid):
    idx = {}
    for l in ARCH._levels(building, bid):
        idx[l["index"]] = l
        idx[str(l["id"])] = l
    return idx


def _level_of(levels_idx, ref):
    if ref is None:
        return None
    if isinstance(ref, bool):
        return None
    if isinstance(ref, (int, float)):
        return levels_idx.get(int(ref))
    return levels_idx.get(str(ref)) or levels_idx.get(ref)


def _nid(bid, given, prefix, n):
    if given:
        s = str(given)
        if s.startswith(bid + "."):
            return s
        # معرّف يحمل بادئة مبنى آخر يُترك كما هو ليكشفه التحقّق بدل أن نخفيه
        head = s.split(".")[0]
        if head.startswith("bld_") and head != bid:
            return s
        return "%s.%s" % (bid, s)
    return "%s.%s_%d" % (bid, prefix, n)


def _sortkey(*vals):
    out = []
    for v in vals:
        if v is None:
            out.append((2, 0.0, ""))
        elif isinstance(v, str):
            out.append((1, 0.0, v))
        else:
            out.append((0, float(v), ""))
    return tuple(out)


# ------------------------------------------------------------- المواد --
def _materials(raw, bid):
    out = []
    for n, m in enumerate(raw.get("materials") or []):
        mat = str(m.get("material") or "unknown").lower()
        known = mat in MATERIALS
        out.append({
            "id": _nid(bid, m.get("id"), "mat", n), "type": "MATERIAL",
            "building_id": bid,
            "material": mat if known else "other",
            "declared_material": m.get("material"),
            "material_recognised": known,
            # التسمية وحدها لا تحمل مقاومة ولا معايرة: كل خاصية تُذكر صراحةً
            "grade": ({"value": None, "source": "unknown"} if m.get("grade") is None
                      else {"value": m.get("grade"),
                            "source": _src(m.get("source"), "imported")}),
            "strength": _prop(m.get("strength"), m.get("source")),
            "density": _prop(m.get("density"), m.get("source")),
            "elastic_modulus": _prop(m.get("elastic_modulus"), m.get("source")),
            "source": _src(m.get("source")),
            "note": "a material label implies no strength, grade, modulus or capacity"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ الشبكات --
def _grids(raw, bid):
    systems = raw.get("grid_systems")
    if not systems:
        flat = raw.get("grids") or []
        systems = [{"id": "gs_0", "label": None, "grids": flat}] if flat else []
    out = []
    for n, gs in enumerate(systems):
        lines = []
        for k, g in enumerate(gs.get("grids") or []):
            axis = str(g.get("axis") or "X").upper()[:1]
            axis = axis if axis in ("X", "Z") else "X"
            label = g.get("label")
            gid = g.get("id") or ("grid_%s_%s" % (axis.lower(), label if label is not None else k))
            lines.append({"id": _nid(bid, gid, "grid", k), "type": "GRID_LINE",
                          "building_id": bid, "axis": axis, "label": label,
                          "position_m": _num(g.get("position_m")),
                          "position_stated": _num(g.get("position_m")) is not None,
                          "source": _src(g.get("source") or gs.get("source"))})
        lines.sort(key=lambda e: _sortkey(e["axis"], e["position_m"], str(e["id"])))
        out.append({"id": _nid(bid, gs.get("id"), "gs", n), "type": "GRID_SYSTEM",
                    "building_id": bid, "label": gs.get("label"),
                    "origin": {"x": _num((gs.get("origin") or {}).get("x")) or 0.0,
                               "z": _num((gs.get("origin") or {}).get("z")) or 0.0},
                    "rotation_deg": _num(gs.get("rotation_deg")) or 0.0,
                    "rotation_stated": _num(gs.get("rotation_deg")) is not None,
                    "source": _src(gs.get("source")), "grids": lines})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _grid_index(systems):
    idx = {}
    for gs in systems:
        for g in gs["grids"]:
            idx[g["id"]] = g
    return idx


# -------------------------------------------------------------- العقد --
def _nodes(raw, bid, levels_idx):
    out = []
    for n, nd in enumerate(raw.get("nodes") or []):
        lvl = _level_of(levels_idx, nd.get("level"))
        y = _num(nd.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        out.append({"id": _nid(bid, nd.get("id"), "node", n), "type": "STRUCTURAL_NODE",
                    "building_id": bid,
                    "x": _num(nd.get("x")), "y": y, "z": _num(nd.get("z")),
                    "y_source": ("imported" if _num(nd.get("y")) is not None else
                                 ("architectural_level" if lvl is not None else "unknown")),
                    "level_ref": nd.get("level"),
                    "level_id": lvl["id"] if lvl else None,
                    "level_index": lvl["index"] if lvl else None,
                    "level_resolved": lvl is not None or nd.get("level") is None,
                    "raw_x": nd.get("x"), "raw_z": nd.get("z"),
                    "source": _src(nd.get("source"))})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ الأعمدة --
def _section(sec):
    """مقطع معلن فقط. لا نختار بُعداً إنشائياً من أجل الرسم."""
    if not isinstance(sec, dict):
        return None
    shape = str(sec.get("shape") or "unknown").lower()
    if shape not in SECTION_SHAPES:
        shape = "other"
    out = {"shape": shape,
           "width_m": _num(sec.get("width") if sec.get("width") is not None else sec.get("width_m")),
           "depth_m": _num(sec.get("depth") if sec.get("depth") is not None else sec.get("depth_m")),
           "diameter_m": _num(sec.get("diameter") if sec.get("diameter") is not None
                              else sec.get("diameter_m")),
           "source": _src(sec.get("source"), "imported")}
    if out["width_m"] is None and out["depth_m"] is None and out["diameter_m"] is None:
        return None
    return out


def _render_section(section, wkey, dkey, dia_key=None):
    """هندسة الرسم فقط. تُوسم دائماً بمصدرها ولا تُكتب في النموذج الدلالي."""
    if section and section.get("diameter_m") is not None:
        d = section["diameter_m"]
        return {"shape": section["shape"], "w": d, "d": d, "source": "model"}
    if section and (section.get("width_m") is not None or section.get("depth_m") is not None):
        w = section.get("width_m")
        d = section.get("depth_m")
        if w is None:
            w = d
        if d is None:
            d = w
        return {"shape": section["shape"], "w": w, "d": d, "source": "model"}
    return {"shape": "unknown", "w": FALLBACKS[wkey], "d": FALLBACKS[dkey],
            "source": "display_fallback"}


def _columns(raw, bid, levels_idx, grid_idx):
    out = []
    for n, c in enumerate(raw.get("columns") or []):
        base = _level_of(levels_idx, c.get("base_level"))
        top = _level_of(levels_idx, c.get("top_level"))
        pos = c.get("position") if isinstance(c.get("position"), dict) else c
        x, z = _num(pos.get("x")), _num(pos.get("z"))
        be = _num(c.get("base_elevation_m"))
        te = _num(c.get("top_elevation_m"))
        if be is None and base is not None:
            be = base["elevation_m"]
        if te is None and top is not None:
            te = top["elevation_m"]
        h = (te - be) if (be is not None and te is not None) else None
        sec = _section(c.get("section"))
        refs = [r for r in (c.get("grid_refs") or [])]
        out.append({
            "id": _nid(bid, c.get("id"), "col", n), "type": "COLUMN", "building_id": bid,
            "x": x, "z": z, "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "base_level_ref": c.get("base_level"), "top_level_ref": c.get("top_level"),
            "base_level_id": base["id"] if base else None,
            "top_level_id": top["id"] if top else None,
            "base_level_index": base["index"] if base else None,
            "top_level_index": top["index"] if top else None,
            "levels_resolved": (base is not None or c.get("base_level") is None)
                               and (top is not None or c.get("top_level") is None),
            "base_elevation_m": be, "top_elevation_m": te, "height_m": h,
            "height_basis": ("architectural_levels" if (_num(c.get("base_elevation_m")) is None
                                                       and be is not None) else
                             ("stated_elevations" if be is not None else "unresolved")),
            "declared_height_m": _num(c.get("height_m")),
            "section": sec,
            "render_section": _render_section(sec, "column_width_m", "column_depth_m"),
            "material_ref": c.get("material_ref"),
            "grid_refs": refs,
            "unresolved_grid_refs": [r for r in refs if r and _nid(bid, r, "grid", 0) not in grid_idx
                                     and r not in grid_idx],
            "structural_role": (str(c.get("structural_role")).lower()
                                if c.get("structural_role") else "unknown"),
            "source": _src(c.get("source")),
            "status": None, "stack": None,
            "note": "represented structural column — no capacity, sizing or adequacy is implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------- الجسور --
def _beams(raw, bid, levels_idx, node_idx, grid_idx):
    out = []
    for n, b in enumerate(raw.get("beams") or []):
        lvl = _level_of(levels_idx, b.get("level"))
        ends, refs = [], []
        for key, pkey in (("from", "from_point"), ("to", "to_point")):
            ref = b.get(key)
            pt = b.get(pkey)
            node = node_idx.get(str(ref)) or node_idx.get(_nid(bid, ref, "node", 0)) if ref else None
            if node is not None:
                ends.append({"ref": ref, "node_id": node["id"],
                             "x": node["x"], "z": node["z"], "basis": "structural_node"})
            elif isinstance(pt, dict) and _num(pt.get("x")) is not None and _num(pt.get("z")) is not None:
                ends.append({"ref": None, "node_id": None, "x": _num(pt.get("x")),
                             "z": _num(pt.get("z")), "basis": "stated_point"})
            else:
                ends.append({"ref": ref, "node_id": None, "x": None, "z": None,
                             "basis": "unknown_node" if ref is not None else "unresolved"})
            refs.append(ref)
        length = None
        if all(e["x"] is not None and e["z"] is not None for e in ends):
            dx = ends[1]["x"] - ends[0]["x"]
            dz = ends[1]["z"] - ends[0]["z"]
            length = math.sqrt(dx * dx + dz * dz)
        sec = _section(b.get("section"))
        grefs = [r for r in (b.get("grid_refs") or [])]
        out.append({
            "id": _nid(bid, b.get("id"), "beam", n), "type": "BEAM", "building_id": bid,
            "level_ref": b.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or b.get("level") is None,
            "elevation_m": _num(b.get("elevation_m")) if _num(b.get("elevation_m")) is not None
                           else (lvl["elevation_m"] if lvl else None),
            "start": ends[0], "end": ends[1], "length_m": length,
            "section": sec,
            "render_section": _render_section(sec, "beam_width_m", "beam_depth_m"),
            "material_ref": b.get("material_ref"),
            "grid_refs": grefs,
            "unresolved_grid_refs": [r for r in grefs if r and r not in grid_idx
                                     and _nid(bid, r, "grid", 0) not in grid_idx],
            "structural_role": (str(b.get("structural_role")).lower()
                                if b.get("structural_role") else "unknown"),
            "source": _src(b.get("source")), "status": None,
            "note": "represented structural beam — no span, sizing or capacity is implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------ البلاطات والجدران والنوى --
def _outline(v):
    if isinstance(v, (list, tuple)) and len(v) >= 4:
        vals = [_num(x) for x in v[:4]]
        return vals if all(x is not None for x in vals) else None
    return None


def _slabs(raw, bid, levels_idx):
    out = []
    for n, s in enumerate(raw.get("slabs") or []):
        lvl = _level_of(levels_idx, s.get("level"))
        # البلاطة المعمارية ليست بلاطة إنشائية: التصنيف يأتي من النموذج لا منّا
        cls = str(s.get("classification") or ("supplied" if s.get("source") in
                                              ("user", "imported", "manual_verified")
                                              else "unverified")).lower()
        out.append({
            "id": _nid(bid, s.get("id"), "sslab", n), "type": "STRUCTURAL_SLAB",
            "building_id": bid,
            "level_ref": s.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or s.get("level") is None,
            "elevation_m": lvl["elevation_m"] if lvl else None,
            "outline": _outline(s.get("outline")),
            "thickness_m": _fallback(s.get("thickness_m"), "structural_slab_thickness_m"),
            "system": s.get("system"),
            "material_ref": s.get("material_ref"),
            "classification": cls,
            "supported_by": list(s.get("supported_by") or []),
            "structural_role": (str(s.get("structural_role")).lower()
                                if s.get("structural_role") else "unknown"),
            "source": _src(s.get("source")),
            "note": "a structural slab is a separate element from the architectural floor slab"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _swalls(raw, bid, levels_idx):
    out = []
    for n, w in enumerate(raw.get("walls") or []):
        refs = w.get("levels") if isinstance(w.get("levels"), list) else (
            [w.get("level")] if w.get("level") is not None else [])
        lv = [_level_of(levels_idx, r) for r in refs]
        st = w.get("start") if isinstance(w.get("start"), dict) else {}
        en = w.get("end") if isinstance(w.get("end"), dict) else {}
        sx, sz = _num(st.get("x")), _num(st.get("z"))
        ex, ez = _num(en.get("x")), _num(en.get("z"))
        length = (math.sqrt((ex - sx) ** 2 + (ez - sz) ** 2)
                  if None not in (sx, sz, ex, ez) else None)
        out.append({
            "id": _nid(bid, w.get("id"), "swall", n), "type": "STRUCTURAL_WALL",
            "building_id": bid,
            "level_refs": refs,
            "level_ids": [l["id"] for l in lv if l],
            "level_indexes": sorted(l["index"] for l in lv if l),
            "levels_resolved": all(l is not None for l in lv) and (len(refs) > 0),
            "start": {"x": sx, "z": sz}, "end": {"x": ex, "z": ez}, "length_m": length,
            "thickness_m": _fallback(w.get("thickness_m"), "structural_wall_thickness_m"),
            "material_ref": w.get("material_ref"),
            # لا يصير جداراً حاملاً ولا جدار قص إلا بذكر صريح
            "structural_role": (str(w.get("structural_role")).lower()
                                if w.get("structural_role") else "unknown"),
            "arch_wall_id": w.get("arch_wall_id"),
            "supported_by": list(w.get("supported_by") or []),
            "source": _src(w.get("source")),
            "note": "an architectural wall never becomes structural without explicit evidence"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _score(raw, bid, levels_idx):
    out = []
    for n, c in enumerate(raw.get("cores") or []):
        refs = list(c.get("levels") or [])
        lv = [_level_of(levels_idx, r) for r in refs]
        out.append({
            "id": _nid(bid, c.get("id"), "score", n), "type": "STRUCTURAL_CORE",
            "building_id": bid,
            "level_refs": refs, "level_ids": [l["id"] for l in lv if l],
            "level_indexes": sorted(l["index"] for l in lv if l),
            "levels_resolved": all(l is not None for l in lv) and (len(refs) > 0),
            "outline": _outline(c.get("outline")),
            "thickness_m": _fallback(c.get("thickness_m"), "structural_wall_thickness_m"),
            "material_ref": c.get("material_ref"),
            "arch_core_id": c.get("arch_core_id"),
            "arch_core_link_source": _src(c.get("arch_core_link_source")) if c.get("arch_core_id")
                                     else "unknown",
            "structural_role": (str(c.get("structural_role")).lower()
                                if c.get("structural_role") else "unknown"),
            "source": _src(c.get("source")),
            "note": "an architectural stair or elevator core is not a lateral core "
                    "unless the model says so"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ----------------------------------------------------------- الأساسات --
def _foundations(raw, bid, levels_idx):
    out = []
    for n, f in enumerate(raw.get("foundations") or []):
        t = str(f.get("type") or "unknown").lower()
        if t not in FOUNDATION_TYPES:
            t = "other"
        pos = f.get("position") if isinstance(f.get("position"), dict) else f
        out.append({
            "id": _nid(bid, f.get("id"), "fnd", n), "type": "FOUNDATION", "building_id": bid,
            "foundation_type": t, "declared_type": f.get("type"),
            "x": _num(pos.get("x")), "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "outline": _outline(f.get("outline")),
            "width_m": _fallback(f.get("width_m"), "foundation_width_m"),
            "depth_m": _fallback(f.get("depth_m"), "foundation_depth_m"),
            "thickness_m": _fallback(f.get("thickness_m"), "foundation_thickness_m"),
            "embedment_m": _fallback(f.get("embedment_m"), "foundation_embedment_m"),
            "top_elevation_m": _num(f.get("top_elevation_m")),
            "material_ref": f.get("material_ref"),
            "supports": list(f.get("supports") or []),
            # لا تربة ولا قدرة تحمّل: لا شيء من ذلك يُستنتج هنا
            "soil": None,
            "source": _src(f.get("source")),
            "note": "represented foundation — no size, soil property or bearing capacity "
                    "is calculated or implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ---------------------------------------------------- تكديس الأعمدة --
def _stacks(columns, issues):
    """استمرارية هندسية بين مستويين. ليست حكماً بصحّة إنشائية إطلاقاً."""
    rels = []
    by_top = {}
    for c in columns:
        if c["top_level_index"] is not None:
            by_top.setdefault(c["top_level_index"], []).append(c)
    for c in columns:
        bi = c["base_level_index"]
        if bi is None or c["x"] is None or c["z"] is None:
            c["stack"] = {"state": "unresolved",
                          "reason": "base level or position is not resolved"}
            continue
        below = [d for d in by_top.get(bi, []) if d["id"] != c["id"]
                 and d["x"] is not None and d["z"] is not None]
        if not below:
            c["stack"] = {"state": "unresolved", "reason": "no column terminates at this base level",
                          "supported_by": None, "offset_m": None}
            continue
        best, dist = None, None
        for d in below:
            g = math.sqrt((d["x"] - c["x"]) ** 2 + (d["z"] - c["z"]) ** 2)
            if dist is None or g < dist or (g == dist and str(d["id"]) < str(best["id"])):
                best, dist = d, g
        if dist <= _POS_TOL:
            state = "aligned"
        elif dist <= _OFFSET_TOL:
            state = "offset"
            issues.append({"code": "COLUMN_OFFSET", "subject": c["id"], "other": best["id"],
                           "offset_m": round(dist, 6),
                           "detail": "the column below is offset; no transfer element is designed "
                                     "or assumed"})
        else:
            state = "unresolved"
            issues.append({"code": "STRUCTURAL_ALIGNMENT_BREAK", "subject": c["id"],
                           "nearest": best["id"], "distance_m": round(dist, 6),
                           "detail": "no column terminates under this column within tolerance; "
                                     "reported as a factual condition only"})
        c["stack"] = {"state": state, "supported_by": best["id"], "offset_m": round(dist, 6),
                      "reason": None}
        rels.append(("COLUMN_STACKS", best["id"], c["id"],
                     "confirmed" if state == "aligned" else "inferred",
                     "geometric_continuity_between_levels",
                     {"alignment": state, "offset_m": round(dist, 6)}))
    return rels


# ----------------------------------------------------------- العلاقات --
def _relationships(bid, cols, beams, slabs, walls, cores, fnds, stack_rels, arch, issues):
    rels = []
    seq = [0]

    def add(rtype, frm, to, status, basis, meta=None):
        seq[0] += 1
        e = {"id": "%s.srel_%d" % (bid, seq[0]), "type": rtype, "from": frm, "to": to,
             "source": "geometry_inference" if status != "confirmed" else "model_declaration",
             "status": status, "basis": basis,
             "note": "geometric connectivity only — this is not a load path"}
        if meta:
            e["meta"] = meta
        rels.append(e)
        return e

    for t, a, b, st, basis, meta in stack_rels:
        add(t, a, b, st, basis, meta)

    col_by_id = {c["id"]: c for c in cols}
    for b in beams:
        for end in (b["start"], b["end"]):
            if end["node_id"]:
                add("BEAM_CONNECTS", b["id"], end["node_id"], "confirmed",
                    "beam endpoint references a declared structural node")
            elif end["basis"] == "stated_point":
                add("BEAM_CONNECTS", b["id"], None, "inferred",
                    "beam endpoint is a stated point with no node",
                    {"x": end["x"], "z": end["z"]})
            else:
                add("BEAM_CONNECTS", b["id"], None, "unresolved",
                    "beam endpoint could not be resolved", {"ref": end["ref"]})
        # تلامس عمود/جسر: اتصال هندسي فقط، ولا يعني أنّ العمود يحمل الجسر
        if b["level_index"] is not None:
            for end in (b["start"], b["end"]):
                if end["x"] is None:
                    continue
                for c in cols:
                    if c["x"] is None or c["top_level_index"] != b["level_index"]:
                        continue
                    if math.sqrt((c["x"] - end["x"]) ** 2 + (c["z"] - end["z"]) ** 2) <= _POS_TOL:
                        add("COLUMN_SUPPORTS", c["id"], b["id"], "confirmed",
                            "beam endpoint coincides with the column axis at this level",
                            {"disclaimer": "geometric connectivity, not a load path"})

    for s in slabs:
        for ref in s["supported_by"]:
            tgt = _nid(bid, ref, "x", 0)
            known = tgt in col_by_id or any(tgt == e["id"] for e in beams + walls + cores)
            add("SLAB_SUPPORTED_BY", s["id"], tgt if known else None,
                "confirmed" if known else "unresolved",
                "declared by the model" if known else "declared support was not found")
    for w in walls:
        for ref in w["supported_by"]:
            tgt = _nid(bid, ref, "x", 0)
            known = tgt in col_by_id or any(tgt == e["id"] for e in beams + walls + fnds)
            add("WALL_SUPPORTED_BY", w["id"], tgt if known else None,
                "confirmed" if known else "unresolved",
                "declared by the model" if known else "declared support was not found")
    all_ids = {e["id"] for e in cols + beams + slabs + walls + cores}
    for f in fnds:
        if not f["supports"]:
            issues.append({"code": "FOUNDATION_REF_MISSING", "subject": f["id"],
                           "detail": "this foundation declares no member it is placed under"})
        for ref in f["supports"]:
            tgt = _nid(bid, ref, "x", 0)
            if tgt in all_ids:
                add("FOUNDATION_SUPPORTS", f["id"], tgt, "confirmed",
                    "declared by the model",
                    {"disclaimer": "placement relationship only — no bearing check is performed"})
            else:
                issues.append({"code": "FOUNDATION_TARGET_UNRESOLVED", "subject": f["id"],
                               "ref": ref})
                add("FOUNDATION_SUPPORTS", f["id"], None, "unresolved",
                    "declared support target was not found")
    for c in cores:
        if len(c["level_indexes"]) > 1:
            add("CORE_SPANS_LEVELS", c["id"], None, "confirmed",
                "declared by the model", {"levels": list(c["level_indexes"])})

    # موقع العضو داخل فراغ معماري — علاقة مكانية فقط، لا حكم بالقبول
    if arch:
        for c in cols:
            if c["x"] is None or c["base_level_index"] is None:
                continue
            for sp in arch.get("spaces") or []:
                rc = sp.get("rect")
                if not rc or sp.get("level_index") != c["base_level_index"]:
                    continue
                if rc[0] - _EPS <= c["x"] <= rc[0] + rc[2] + _EPS and \
                   rc[1] - _EPS <= c["z"] <= rc[1] + rc[3] + _EPS:
                    add("MEMBER_IN_SPACE", c["id"], sp["id"], "confirmed",
                        "the column axis lies inside this architectural space",
                        {"space_id": sp.get("space_id"),
                         "disclaimer": "spatial location only — acceptability is not judged here"})
    return rels


# ------------------------------------------------- تداخل مع المعماري --
def _interference(cols, beams, fnds, arch, building, issues):
    """تعارضات هندسية واضحة فقط — ليست كشف تصادم BIM كاملاً ولا فحص كود."""
    if not arch:
        return
    for c in cols:
        if c["x"] is None or c["base_level_index"] is None:
            continue
        rs = c["render_section"]
        known = rs["source"] == "model"
        hw = (rs["w"] / 2.0) if known else 0.0
        hd = (rs["d"] / 2.0) if known else 0.0
        basis = "column_section_footprint" if known else "column_axis_point"
        for v in arch.get("voids") or []:
            if v.get("level_index") != c["base_level_index"] and \
               v.get("level_index") != c.get("top_level_index"):
                continue
            r = v["rect"]
            if c["x"] + hw > r[0] and c["x"] - hw < r[0] + r[2] and \
               c["z"] + hd > r[1] and c["z"] - hd < r[1] + r[3]:
                code = ("COLUMN_IN_ELEVATOR_CORE" if v.get("core_type") == "ELEVATOR_SHAFT"
                        else "COLUMN_IN_FLOOR_OPENING")
                issues.append({"code": code, "subject": c["id"], "other": v["id"],
                               "basis": basis})
        for o in arch.get("openings") or []:
            if o.get("level_index") != c["base_level_index"]:
                continue
            w = o["width_m"]["value"]
            if w is None:
                w = o["width_m"]["render_fallback"]
            a, b = o["u_center"] - w / 2.0, o["u_center"] + w / 2.0
            if o["axis"] == "x":
                cu, cf, hu, hf = c["x"], c["z"], hw, hd
            else:
                cu, cf, hu, hf = c["z"], c["x"], hd, hw
            if cu + hu > a and cu - hu < b and abs(cf - o["fixed"]) <= max(hf, 0.15):
                issues.append({"code": "COLUMN_BLOCKS_OPENING", "subject": c["id"],
                               "other": o["id"], "basis": basis})
    for b in beams:
        if b["start"]["x"] is None or b["end"]["x"] is None or b["level_index"] is None:
            continue
        for o in arch.get("openings") or []:
            if o.get("level_index") != b["level_index"] or o["type"] != "DOOR":
                continue
            w = o["width_m"]["value"] or o["width_m"]["render_fallback"]
            ax = o["axis"]
            p0, p1 = (b["start"]["x"], b["start"]["z"]), (b["end"]["x"], b["end"]["z"])
            fu0, fu1 = (p0[0], p1[0]) if ax == "x" else (p0[1], p1[1])
            ff0, ff1 = (p0[1], p1[1]) if ax == "x" else (p0[0], p1[0])
            if abs(ff0 - o["fixed"]) <= 0.15 and abs(ff1 - o["fixed"]) <= 0.15:
                lo, hi = min(fu0, fu1), max(fu0, fu1)
                if lo < o["u_center"] + w / 2.0 and hi > o["u_center"] - w / 2.0:
                    issues.append({"code": "BEAM_CROSSES_OPENING", "subject": b["id"],
                                   "other": o["id"],
                                   "detail": "the beam runs along the wall line carrying this "
                                             "opening; head clearance is NOT evaluated"})
    site = building.get("site") if isinstance(building.get("site"), dict) else None
    if site:
        sw, sd = _num(site.get("w")), _num(site.get("d"))
        for f in fnds:
            if f["x"] is None or sw is None or sd is None:
                continue
            if f["x"] < -_EPS or f["z"] < -_EPS or f["x"] > sw + _EPS or f["z"] > sd + _EPS:
                issues.append({"code": "FOUNDATION_OUTSIDE_SITE", "subject": f["id"],
                               "site": [sw, sd]})


# ----------------------------------------------------------- التصريف --
def compile_structure(building, building_id="bld_0", position=None, rotation_deg=0.0, arch=None):
    """يبني النموذج الإنشائي من بيانات مذكورة فقط. حتمي ولا يعدّل النموذج."""
    bid = building_id
    raw = _raw(building)
    levels = ARCH._levels(building, bid)
    levels_idx = _levels_index(building, bid)
    if arch is None:
        try:
            arch = ARCH.compile_architecture(building, bid, position, rotation_deg)
        except Exception:
            arch = None

    issues = []
    known_keys = {"status", "synthetic", "meta", "grid_systems", "grids", "materials", "nodes",
                  "columns", "beams", "slabs", "walls", "cores", "foundations",
                  "layer_visibility", "visible_layers"}
    for k in sorted(raw.keys()):
        if k not in known_keys:
            issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": k,
                           "detail": "this collection is not part of the structural schema and "
                                     "was NOT interpreted"})
    materials = _materials(raw, bid)
    grid_systems = _grids(raw, bid)
    grid_idx = _grid_index(grid_systems)
    nodes = _nodes(raw, bid, levels_idx)
    node_idx = {}
    for nd in nodes:
        node_idx[nd["id"]] = nd
    cols = _columns(raw, bid, levels_idx, grid_idx)
    beams = _beams(raw, bid, levels_idx, node_idx, grid_idx)
    slabs = _slabs(raw, bid, levels_idx)
    walls = _swalls(raw, bid, levels_idx)
    cores = _score(raw, bid, levels_idx)
    fnds = _foundations(raw, bid, levels_idx)

    counted = (len(cols) + len(beams) + len(slabs) + len(walls) + len(cores)
               + len(fnds) + len(nodes) + sum(len(g["grids"]) for g in grid_systems))
    declared = str(raw.get("status") or "").upper()
    if declared in MODEL_STATUS:
        status = declared
    elif counted == 0:
        status = "NOT_DEFINED"
    else:
        verified = all(e["source"] in VERIFIED_SOURCES
                       for e in cols + beams + slabs + walls + cores + fnds)
        status = "REPRESENTED" if verified else "PARTIAL"

    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "building_id": bid,
           "status": status,
           "status_basis": ("declared_by_model" if declared in MODEL_STATUS
                            else ("no structural element is present" if counted == 0
                                  else "derived from element provenance")),
           "synthetic": raw.get("synthetic") is True,
           "regulatory": False,
           "transform": {"position": position or {"x": 0.0, "z": 0.0},
                         "rotation_deg": float(rotation_deg or 0.0),
                         "applied": "local coordinates; world transform is applied on read"},
           "levels": [{"id": l["id"], "index": l["index"], "elevation_m": l["elevation_m"],
                       "elevation_source": l["elevation_source"]} for l in levels],
           "grid_systems": grid_systems, "materials": materials, "nodes": nodes,
           "columns": cols, "beams": beams, "slabs": slabs, "walls": walls,
           "cores": cores, "foundations": fnds,
           "relationships": [], "issues": [],
           "meta": {"note": SPEC["note"],
                    "elements": counted,
                    "levels_source": "architectural level table",
                    "load_path": "not derived — geometric connectivity only",
                    "navigation_impact": "none — structural members are not navigation obstacles "
                                         "in this phase"}}

    stack_rels = _stacks(cols, issues)
    out["relationships"] = _relationships(bid, cols, beams, slabs, walls, cores, fnds,
                                          stack_rels, arch, issues)
    _interference(cols, beams, fnds, arch, building, issues)
    for i in check_columns_inside(out, arch):
        i.pop("severity", None)
        issues.append(i)
    issues.extend(validate_structure(out))
    for i in issues:
        i["severity"] = severity_of(i["code"])
    issues.sort(key=lambda i: (SEVERITIES.index(i["severity"]) * -1, str(i["code"]),
                               str(i.get("subject"))))
    out["issues"] = issues
    return out


# ------------------------------------------------------------ التحقّق --
def validate_structure(struct):
    """فحوص سلامة نموذج — ليست فحوص كود إنشائي إطلاقاً."""
    issues = []
    bid = struct.get("building_id")
    groups = ("nodes", "columns", "beams", "slabs", "walls", "cores", "foundations", "materials")
    seen = {}
    for key in groups:
        for e in struct.get(key) or []:
            if e["id"] in seen:
                issues.append({"code": "DUPLICATE_ELEMENT_ID", "subject": e["id"],
                               "other": seen[e["id"]]})
            seen[e["id"]] = key
            if e.get("type") not in ELEMENT_TYPES:
                issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": e["id"],
                               "declared": e.get("type")})
            if bid and not str(e["id"]).startswith(str(bid) + "."):
                issues.append({"code": "CROSS_BUILDING_REF", "subject": e["id"]})
    for gs in struct.get("grid_systems") or []:
        for g in gs["grids"]:
            if g["id"] in seen:
                issues.append({"code": "DUPLICATE_ELEMENT_ID", "subject": g["id"],
                               "other": seen[g["id"]]})
            seen[g["id"]] = "grids"

    mat_ids = {m["id"] for m in struct.get("materials") or []}
    for key in ("columns", "beams", "slabs", "walls", "cores", "foundations"):
        for e in struct.get(key) or []:
            ref = e.get("material_ref")
            if ref is None:
                issues.append({"code": "MATERIAL_UNKNOWN", "subject": e["id"]})
            elif _nid(bid, ref, "mat", 0) not in mat_ids and str(ref) not in mat_ids:
                issues.append({"code": "INVALID_MATERIAL_REF", "subject": e["id"], "ref": ref})

    for n in struct.get("nodes") or []:
        if _is_bad_number(n.get("raw_x")) or _is_bad_number(n.get("raw_z")) or \
           n["x"] is None or n["z"] is None:
            issues.append({"code": "NAN_COORDINATE", "subject": n["id"]})
        if not n["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": n["id"],
                           "ref": n.get("level_ref")})

    arch_levels = {l["index"] for l in struct.get("levels") or []}
    for c in struct.get("columns") or []:
        if _is_bad_number(c.get("raw_x")) or _is_bad_number(c.get("raw_z")) or \
           c["x"] is None or c["z"] is None:
            issues.append({"code": "NAN_COORDINATE", "subject": c["id"]})
        if not c["levels_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": c["id"],
                           "base": c.get("base_level_ref"), "top": c.get("top_level_ref")})
        if c["height_m"] is not None and abs(c["height_m"]) <= _EPS:
            issues.append({"code": "COLUMN_ZERO_HEIGHT", "subject": c["id"]})
        elif c["height_m"] is not None and c["height_m"] < 0:
            issues.append({"code": "NEGATIVE_DIMENSION", "subject": c["id"], "field": "height_m"})
        if c["declared_height_m"] is not None and c["height_m"] is not None and \
           abs(c["declared_height_m"] - c["height_m"]) > 1e-3:
            issues.append({"code": "COLUMN_HEIGHT_MISMATCH", "subject": c["id"],
                           "declared": c["declared_height_m"], "from_levels": c["height_m"]})
        if c["section"] is None:
            issues.append({"code": "SECTION_UNKNOWN", "subject": c["id"]})
        else:
            for f in ("width_m", "depth_m", "diameter_m"):
                if c["section"].get(f) is not None and c["section"][f] <= 0:
                    issues.append({"code": "NEGATIVE_DIMENSION", "subject": c["id"], "field": f})
        for r in c["unresolved_grid_refs"]:
            issues.append({"code": "INVALID_GRID_REF", "subject": c["id"], "ref": r})
        if c["base_level_index"] is not None and c["base_level_index"] not in arch_levels:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": c["id"],
                           "base": c["base_level_index"]})

    for b in struct.get("beams") or []:
        for end in (b["start"], b["end"]):
            if end["basis"] == "unknown_node":
                issues.append({"code": "INVALID_NODE_REF", "subject": b["id"],
                               "ref": end["ref"]})
                issues.append({"code": "BEAM_ENDPOINT_UNRESOLVED", "subject": b["id"],
                               "ref": end["ref"]})
            elif end["basis"] == "unresolved":
                issues.append({"code": "BEAM_ENDPOINT_UNRESOLVED", "subject": b["id"],
                               "ref": end["ref"]})
            elif end["node_id"] is None and end["basis"] == "stated_point":
                issues.append({"code": "BEAM_FLOATING", "subject": b["id"],
                               "detail": "endpoint is a bare point with no structural node"})
        if not b["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": b["id"],
                           "ref": b.get("level_ref")})
        if b["length_m"] is not None and b["length_m"] <= _EPS:
            issues.append({"code": "MEMBER_ZERO_LENGTH", "subject": b["id"]})
        if b["section"] is None:
            issues.append({"code": "SECTION_UNKNOWN", "subject": b["id"]})
        else:
            for f in ("width_m", "depth_m", "diameter_m"):
                if b["section"].get(f) is not None and b["section"][f] <= 0:
                    issues.append({"code": "NEGATIVE_DIMENSION", "subject": b["id"], "field": f})
        for r in b["unresolved_grid_refs"]:
            issues.append({"code": "INVALID_GRID_REF", "subject": b["id"], "ref": r})

    for s in struct.get("slabs") or []:
        if not s["level_resolved"]:
            issues.append({"code": "SLAB_LEVEL_UNRESOLVED", "subject": s["id"],
                           "ref": s.get("level_ref")})
        if s["thickness_m"]["value"] is not None and s["thickness_m"]["value"] <= 0:
            issues.append({"code": "NEGATIVE_DIMENSION", "subject": s["id"], "field": "thickness_m"})
    for w in struct.get("walls") or []:
        if not w["levels_resolved"]:
            issues.append({"code": "WALL_LEVELS_UNRESOLVED", "subject": w["id"],
                           "refs": w.get("level_refs")})
        if w["length_m"] is not None and w["length_m"] <= _EPS:
            issues.append({"code": "MEMBER_ZERO_LENGTH", "subject": w["id"]})
        if w["thickness_m"]["value"] is not None and w["thickness_m"]["value"] <= 0:
            issues.append({"code": "NEGATIVE_DIMENSION", "subject": w["id"], "field": "thickness_m"})
    for c in struct.get("cores") or []:
        if not c["levels_resolved"]:
            issues.append({"code": "CORE_LEVELS_UNRESOLVED", "subject": c["id"],
                           "refs": c.get("level_refs")})
    for f in struct.get("foundations") or []:
        if _is_bad_number(f.get("raw_x")) or _is_bad_number(f.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": f["id"]})
        for key in ("width_m", "depth_m", "thickness_m", "embedment_m"):
            if f[key]["value"] is not None and f[key]["value"] <= 0:
                issues.append({"code": "NEGATIVE_DIMENSION", "subject": f["id"], "field": key})
    return issues


# --------------------------------------------------- خارج حدود المبنى --
def check_columns_inside(struct, arch):
    """عمود خارج مسطح المبنى — واقعة هندسية تُبلَّغ ولا تُصحَّح."""
    out = []
    if not arch:
        return out
    boxes = {}
    for s in arch.get("spaces") or []:
        rc = s.get("rect")
        if not rc:
            continue
        li = s.get("level_index")
        b = boxes.get(li)
        r = [rc[0], rc[1], rc[0] + rc[2], rc[1] + rc[3]]
        boxes[li] = r if b is None else [min(b[0], r[0]), min(b[1], r[1]),
                                         max(b[2], r[2]), max(b[3], r[3])]
    for c in struct.get("columns") or []:
        b = boxes.get(c.get("base_level_index"))
        if b is None or c["x"] is None:
            continue
        if not (b[0] - 0.5 <= c["x"] <= b[2] + 0.5 and b[1] - 0.5 <= c["z"] <= b[3] + 0.5):
            out.append({"code": "COLUMN_OUTSIDE_BUILDING", "subject": c["id"],
                        "severity": severity_of("COLUMN_OUTSIDE_BUILDING"),
                        "footprint": b})
    return out


# ------------------------------------------------------- بيانات الرسم --
def render_items(struct):
    """هندسة عرض فقط. كل عنصر يعلن هل أبعاده من النموذج أم احتياط عرض."""
    items = []
    for c in struct.get("columns") or []:
        if c["x"] is None or c["base_elevation_m"] is None or c["height_m"] is None:
            continue
        rs = c["render_section"]
        items.append({"name": "STRUCT|COLUMN|%s" % c["id"], "kind": "COLUMN", "id": c["id"],
                      "cx": c["x"], "cy": c["base_elevation_m"] + c["height_m"] / 2.0,
                      "cz": c["z"], "ex": rs["w"], "ey": abs(c["height_m"]), "ez": rs["d"],
                      "geometry_source": rs["source"], "material_ref": c["material_ref"],
                      "element_source": c["source"]})
    for b in struct.get("beams") or []:
        if b["start"]["x"] is None or b["end"]["x"] is None or b["elevation_m"] is None \
           or not b["length_m"]:
            continue
        rs = b["render_section"]
        mx = (b["start"]["x"] + b["end"]["x"]) / 2.0
        mz = (b["start"]["z"] + b["end"]["z"]) / 2.0
        dx = b["end"]["x"] - b["start"]["x"]
        dz = b["end"]["z"] - b["start"]["z"]
        items.append({"name": "STRUCT|BEAM|%s" % b["id"], "kind": "BEAM", "id": b["id"],
                      "cx": mx, "cy": b["elevation_m"] - rs["d"] / 2.0, "cz": mz,
                      "ex": b["length_m"], "ey": rs["d"], "ez": rs["w"],
                      "rot_y": math.atan2(-dz, dx),
                      "geometry_source": rs["source"], "material_ref": b["material_ref"],
                      "element_source": b["source"]})
    for s in struct.get("slabs") or []:
        o = s["outline"]
        if not o or s["elevation_m"] is None:
            continue
        t = s["thickness_m"]["value"]
        src = "model" if t is not None else "display_fallback"
        t = t if t is not None else s["thickness_m"]["render_fallback"]
        items.append({"name": "STRUCT|SLAB|%s" % s["id"], "kind": "STRUCTURAL_SLAB", "id": s["id"],
                      "cx": o[0] + o[2] / 2.0, "cy": s["elevation_m"] - t / 2.0,
                      "cz": o[1] + o[3] / 2.0, "ex": o[2], "ey": t, "ez": o[3],
                      "geometry_source": src, "material_ref": s["material_ref"],
                      "element_source": s["source"]})
    for w in struct.get("walls") or []:
        if w["start"]["x"] is None or w["end"]["x"] is None or not w["length_m"] \
           or not w["level_indexes"]:
            continue
        t = w["thickness_m"]["value"]
        src = "model" if t is not None else "display_fallback"
        t = t if t is not None else w["thickness_m"]["render_fallback"]
        lv = {l["index"]: l for l in struct.get("levels") or []}
        base = lv.get(min(w["level_indexes"]), {}).get("elevation_m")
        topl = lv.get(max(w["level_indexes"]), {}).get("elevation_m")
        if base is None or topl is None:
            continue
        h = max(topl - base, 0.0)
        if h <= _EPS:
            continue
        dx = w["end"]["x"] - w["start"]["x"]
        dz = w["end"]["z"] - w["start"]["z"]
        items.append({"name": "STRUCT|WALL|%s" % w["id"], "kind": "STRUCTURAL_WALL", "id": w["id"],
                      "cx": (w["start"]["x"] + w["end"]["x"]) / 2.0, "cy": base + h / 2.0,
                      "cz": (w["start"]["z"] + w["end"]["z"]) / 2.0,
                      "ex": w["length_m"], "ey": h, "ez": t,
                      "rot_y": math.atan2(-dz, dx),
                      "geometry_source": src, "material_ref": w["material_ref"],
                      "element_source": w["source"]})
    for c in struct.get("cores") or []:
        o = c["outline"]
        if not o or not c["level_indexes"]:
            continue
        lv = {l["index"]: l for l in struct.get("levels") or []}
        base = lv.get(min(c["level_indexes"]), {}).get("elevation_m")
        topl = lv.get(max(c["level_indexes"]), {}).get("elevation_m")
        if base is None or topl is None or topl - base <= _EPS:
            continue
        items.append({"name": "STRUCT|CORE|%s" % c["id"], "kind": "STRUCTURAL_CORE", "id": c["id"],
                      "cx": o[0] + o[2] / 2.0, "cy": base + (topl - base) / 2.0,
                      "cz": o[1] + o[3] / 2.0, "ex": o[2], "ey": topl - base, "ez": o[3],
                      "geometry_source": "model", "material_ref": c["material_ref"],
                      "element_source": c["source"]})
    for f in struct.get("foundations") or []:
        if f["x"] is None:
            continue
        w = f["width_m"]["value"]
        d = f["depth_m"]["value"]
        t = f["thickness_m"]["value"]
        src = "model" if (w is not None and d is not None and t is not None) else "display_fallback"
        w = w if w is not None else f["width_m"]["render_fallback"]
        d = d if d is not None else f["depth_m"]["render_fallback"]
        t = t if t is not None else f["thickness_m"]["render_fallback"]
        top = f["top_elevation_m"]
        top_src = "model"
        if top is None:
            top = -(f["embedment_m"]["value"] if f["embedment_m"]["value"] is not None
                    else f["embedment_m"]["render_fallback"])
            top_src = "display_fallback"
        if f["outline"]:
            o = f["outline"]
            cx, cz, w, d, src = o[0] + o[2] / 2.0, o[1] + o[3] / 2.0, o[2], o[3], "model"
        else:
            cx, cz = f["x"], f["z"]
        items.append({"name": "STRUCT|FOUNDATION|%s" % f["id"], "kind": "FOUNDATION", "id": f["id"],
                      "cx": cx, "cy": top - t / 2.0, "cz": cz, "ex": w, "ey": t, "ez": d,
                      "geometry_source": src if top_src == "model" else "display_fallback",
                      "material_ref": f["material_ref"], "element_source": f["source"]})
    for gs in struct.get("grid_systems") or []:
        for g in gs["grids"]:
            if g["position_m"] is None:
                continue
            items.append({"name": "STRUCT|GRID|%s" % g["id"], "kind": "GRID_LINE", "id": g["id"],
                          "axis": g["axis"], "position_m": g["position_m"],
                          "origin": gs["origin"], "rotation_deg": gs["rotation_deg"],
                          "label": g["label"], "geometry_source": "model",
                          "element_source": g["source"]})
    items.sort(key=lambda i: str(i["name"]))
    return items


# --------------------------------------------------------- اقتراحات --
def suggest_structural_grid(building, spacing_x_m=None, spacing_z_m=None, building_id="bld_0",
                            basis="explicitly requested spacing"):
    """اقتراح شبكة مفاهيمية — ليس تصميماً إنشائياً ولا يُكتب في النموذج."""
    if spacing_x_m is None and spacing_z_m is None:
        return {"kind": "SUGGESTION", "applied": False, "persisted": False,
                "reason": "NO_SPACING_SUPPLIED",
                "detail": "a grid is not invented; a spacing must be supplied explicitly"}
    try:
        arch = ARCH.compile_architecture(building, building_id)
    except Exception:
        arch = None
    rects = [s["rect"] for s in (arch or {}).get("spaces") or [] if s.get("rect")]
    if not rects:
        return {"kind": "SUGGESTION", "applied": False, "persisted": False,
                "reason": "NO_FOOTPRINT",
                "detail": "no architectural footprint is available to lay a grid over"}
    bb = [min(r[0] for r in rects), min(r[1] for r in rects),
          max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)]
    lines = []

    def lay(axis, lo, hi, step, labels):
        if not step or step <= 0:
            return
        n, p = 0, lo
        while p <= hi + _EPS:
            lab = labels(n)
            lines.append({"id": "%s.grid_%s_%s" % (building_id, axis.lower(), lab),
                          "type": "GRID_LINE", "building_id": building_id, "axis": axis,
                          "label": lab, "position_m": round(p, 6), "position_stated": False,
                          "source": "system_suggested"})
            n += 1
            p = lo + n * step
    lay("X", bb[0], bb[2], _num(spacing_x_m), lambda i: chr(ord("A") + i % 26) + ("" if i < 26 else str(i // 26)))
    lay("Z", bb[1], bb[3], _num(spacing_z_m), lambda i: str(i + 1))
    return {"kind": "SUGGESTION", "applied": False, "persisted": False,
            "source": "system_suggested", "basis": basis,
            "footprint": bb, "spacing_x_m": _num(spacing_x_m), "spacing_z_m": _num(spacing_z_m),
            "grid_system": {"id": "%s.gs_suggested" % building_id, "type": "GRID_SYSTEM",
                            "building_id": building_id, "label": "suggested",
                            "origin": {"x": 0.0, "z": 0.0}, "rotation_deg": 0.0,
                            "rotation_stated": False, "source": "system_suggested",
                            "grids": lines},
            "note": "a suggested grid is a proposal, not structural design and not model truth; "
                    "nothing is written into the model"}


# ------------------------------------------------------------- خدمات --
def element_by_id(struct, eid):
    for key in ("columns", "beams", "slabs", "walls", "cores", "foundations", "nodes",
                "materials", "grid_systems"):
        for el in struct.get(key) or []:
            if el.get("id") == eid:
                return el
            if key == "grid_systems":
                for g in el.get("grids") or []:
                    if g.get("id") == eid:
                        return g
    for r in struct.get("relationships") or []:
        if r.get("id") == eid:
            return r
    return None


def to_world(struct, x, z):
    t = struct.get("transform") or {}
    rot = math.radians(float(t.get("rotation_deg") or 0.0))
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    ca, sa = math.cos(rot), math.sin(rot)
    return [px + x * ca - z * sa, pz + x * sa + z * ca]


def grid_to_world(struct, grid_system, grid_line, span=100.0):
    """خطّ محور في الإحداثيات العامة — يحترم دوران الشبكة ودوران المبنى معاً."""
    if grid_line.get("position_m") is None:
        return None
    o = grid_system.get("origin") or {"x": 0.0, "z": 0.0}
    rot = math.radians(float(grid_system.get("rotation_deg") or 0.0))
    ca, sa = math.cos(rot), math.sin(rot)
    p = float(grid_line["position_m"])
    if grid_line["axis"] == "X":
        a, b = (p, -span), (p, span)
    else:
        a, b = (-span, p), (span, p)
    out = []
    for (lx, lz) in (a, b):
        gx = o["x"] + lx * ca - lz * sa
        gz = o["z"] + lx * sa + lz * ca
        out.append(to_world(struct, gx, gz))
    return out


def rule_inputs(struct):
    """حقائق إنشائية معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية هنا."""
    out = {}
    for c in struct.get("columns") or []:
        sec = c.get("section") or {}
        out[c["id"]] = {
            "structural.column.section_shape": sec.get("shape"),
            "structural.column.section_width": sec.get("width_m"),
            "structural.column.section_depth": sec.get("depth_m"),
            "structural.column.section_diameter": sec.get("diameter_m"),
            "structural.member.material": _material_name(struct, c.get("material_ref")),
            "structural.column.height_m": c.get("height_m"),
            "structural.member.source": c.get("source")}
    for b in struct.get("beams") or []:
        sec = b.get("section") or {}
        out[b["id"]] = {
            "structural.beam.section_width": sec.get("width_m"),
            "structural.beam.section_depth": sec.get("depth_m"),
            "structural.beam.length_m": b.get("length_m"),
            "structural.member.material": _material_name(struct, b.get("material_ref")),
            "structural.member.source": b.get("source")}
    for f in struct.get("foundations") or []:
        out[f["id"]] = {
            "structural.foundation.type": f.get("foundation_type"),
            "structural.member.material": _material_name(struct, f.get("material_ref")),
            "structural.member.source": f.get("source")}
    return out


def _material_name(struct, ref):
    if ref is None:
        return None
    bid = struct.get("building_id")
    for m in struct.get("materials") or []:
        if m["id"] == ref or m["id"] == _nid(bid, ref, "mat", 0):
            return m["material"]
    return None


def summary(struct):
    iss = struct.get("issues") or []
    cols = struct.get("columns") or []
    return {"building_id": struct.get("building_id"),
            "compiler_version": struct.get("compiler_version"),
            "status": struct.get("status"), "synthetic": struct.get("synthetic") is True,
            "regulatory": False,
            "grid_systems": len(struct.get("grid_systems") or []),
            "grid_lines": sum(len(g["grids"]) for g in struct.get("grid_systems") or []),
            "materials": len(struct.get("materials") or []),
            "nodes": len(struct.get("nodes") or []),
            "columns": len(cols), "beams": len(struct.get("beams") or []),
            "slabs": len(struct.get("slabs") or []), "walls": len(struct.get("walls") or []),
            "cores": len(struct.get("cores") or []),
            "foundations": len(struct.get("foundations") or []),
            "relationships": len(struct.get("relationships") or []),
            "columns_with_section": sum(1 for c in cols if c.get("section")),
            "columns_aligned": sum(1 for c in cols if (c.get("stack") or {}).get("state") == "aligned"),
            "columns_offset": sum(1 for c in cols if (c.get("stack") or {}).get("state") == "offset"),
            "columns_unresolved": sum(1 for c in cols
                                      if (c.get("stack") or {}).get("state") == "unresolved"),
            "issues": len(iss),
            "errors": sum(1 for i in iss if i.get("severity") == "ERROR"),
            "warnings": sum(1 for i in iss if i.get("severity") == "WARNING"),
            "infos": sum(1 for i in iss if i.get("severity") == "INFO"),
            "note": "structural representation only — no design, no load calculation, "
                    "no sizing, no code compliance"}
