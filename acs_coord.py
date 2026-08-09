# -*- coding: utf-8 -*-
# =============================================================================
# acs_coord.py — أساس التنسيق بين التخصّصات وكشف التعارضات: كشف وتتبّع فقط.
#
# يقرأ النماذج المصرَّفة (معماري · إنشائي · MEP · حريق) ويقول أين تتعارض.
# ولا يقول أبداً كيف تُصمَّم من جديد.
#
# مبادئ صارمة:
#   • لا إصلاح تلقائي: لا تحريك مسار ولا تكبير جسر ولا نقل باب ولا إنشاء فتحة
#     ولا تحجيم غلاف ولا إعادة توجيه ولا نقل معدّة.
#   • التعارض ليس مخالفة كود ولا حكم سلامة ولا استنتاج كفاية إنشائية.
#   • لا يُكتب شيء في أي نموذج: الطبقة مشتقّة بالكامل.
#   • كل تعارض يجب أن يستند إلى هندسة أو مرجع فعليّ في النموذج — لا تعارض
#     بلا دليل، ولا تعارض من مجرّد قرب.
#   • الإحداثيات تُحلّ إلى إطار عالمي واحد قبل أي فحص: لا اختصار محاور.
#   • الاستثناءات دلالية لا نوعية: لا يُسقَط تعارض لمجرّد نوعَي العنصرين.
# =============================================================================
import hashlib
import json
import math
import os

import acs_arch as ARCH
import acs_struct as STRUCT
import acs_mep as MEP
import acs_fls as FLS
import acs_revision as REV

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_coord.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
DETECTOR_VERSION = SPEC["detector_version"]
DISCIPLINES = tuple(SPEC["disciplines"])
CLASH_TYPES = tuple(SPEC["clash_types"])
CLASH_STATUSES = tuple(SPEC["clash_statuses"])
RECONCILIATION_STATES = tuple(SPEC["reconciliation_states"])
SEVERITIES = tuple(SPEC["severities"])
CLASH_SEVERITY = SPEC["clash_severity"]
SNAPSHOT_STATUSES = tuple(SPEC["snapshot_statuses"])
DISCIPLINE_PAIRS = [tuple(p) for p in SPEC["discipline_pairs"]]
ELEMENT_KINDS = tuple(SPEC["element_kinds"])
EXEMPTION_KINDS = tuple(SPEC["exemption_kinds"])
CELL = float(SPEC["grid_cell_m"])

_EPS = 1e-9
_VOL_EPS = 1e-9


def severity_of(ctype):
    return CLASH_SEVERITY.get(ctype, "WARNING")


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


def _q(v):
    """تقريب قانوني للإحداثيات المنشورة — يمنع انحراف الفاصلة بين اللغتين."""
    return round(float(v), 6) + 0.0


def _canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fmt6(v):
    """تمثيل نصّي ثابت للأرقام داخل مفاتيح البصمات — يمنع اختلاف تنسيق الأرقام
    بين بايثون وجافاسكربت من تغيير البصمة."""
    return "%.6f" % (float(v) + 0.0)


def _project_key(hashes):
    """مفتاح بصمة المشروع: نصوص فقط، فلا يدخل تنسيق الأرقام في الهوية."""
    return [[str(h["building_id"]), str(h["model_hash"]),
             _fmt6(h["position"]["x"]), _fmt6(h["position"]["z"]),
             _fmt6(h["rotation_deg"])] for h in hashes]


def _clash_id(ctype, da, ea, db, eb):
    key = _canon([ctype, da, ea, db, eb])
    return "clash_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------- هندسة عالمية موحّدة --
def _rot(px, pz, rot_deg, ox=0.0, oz=0.0):
    r = math.radians(float(rot_deg or 0.0))
    ca, sa = math.cos(r), math.sin(r)
    return [ox + px * ca - pz * sa, oz + px * sa + pz * ca]


def _obb(cx, cy, cz, ex, ey, ez, rot_y_rad, transform):
    """صندوق موجّه في الإحداثيات العالمية: مركز + أنصاف أبعاد + دوران حول Y.
    يجمع دوران العنصر ودوران المبنى معاً قبل أي فحص."""
    t = transform or {}
    brot = float(t.get("rotation_deg") or 0.0)
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    wx, wz = _rot(cx, cz, brot, px, pz)
    yaw = float(rot_y_rad or 0.0) + math.radians(brot)
    return {"cx": _q(wx), "cy": _q(cy), "cz": _q(wz),
            "hx": _q(abs(ex) / 2.0), "hy": _q(abs(ey) / 2.0), "hz": _q(abs(ez) / 2.0),
            "yaw": _q(yaw)}


def _aabb_of(o):
    ca, sa = abs(math.cos(o["yaw"])), abs(math.sin(o["yaw"]))
    rx = o["hx"] * ca + o["hz"] * sa
    rz = o["hx"] * sa + o["hz"] * ca
    return [_q(o["cx"] - rx), _q(o["cy"] - o["hy"]), _q(o["cz"] - rz),
            _q(o["cx"] + rx), _q(o["cy"] + o["hy"]), _q(o["cz"] + rz)]


def _aabb_overlap(a, b):
    lo = [max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])]
    hi = [min(a[3], b[3]), min(a[4], b[4]), min(a[5], b[5])]
    if hi[0] - lo[0] <= _EPS or hi[1] - lo[1] <= _EPS or hi[2] - lo[2] <= _EPS:
        return None
    return {"min": [_q(lo[0]), _q(lo[1]), _q(lo[2])],
            "max": [_q(hi[0]), _q(hi[1]), _q(hi[2])],
            "volume_m3": _q((hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2]))}


def _obb_overlap(a, b):
    """فصل محاور لصندوقين مدارين حول Y فقط (نظرية المحور الفاصل، 2D + Y)."""
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
        ra = _proj(a, ax, az)
        rb = _proj(b, ax, az)
        if abs(dx * ax + dz * az) >= ra + rb - 1e-9:
            return False
    return True


def _proj(o, ax, az):
    c, s = math.cos(o["yaw"]), math.sin(o["yaw"])
    return abs((c * ax + s * az)) * o["hx"] + abs((-s * ax + c * az)) * o["hz"]


_NON_SOLID = ("ARCH_VOID", "ARCH_CORE")


def _gsrc(*fields):
    """هل أبعاد العنصر مذكورة في النموذج أم احتياط عرض؟ لا يُرقّى الاحتياط أبداً."""
    for f in fields:
        if not isinstance(f, dict) or f.get("value") is None:
            return "display_fallback"
    return "model"


def _vol(discipline, kind, eid, obb, **meta):
    e = {"discipline": discipline, "kind": kind, "element_id": eid,
         "obb": obb, "aabb": _aabb_of(obb), "solid": kind not in _NON_SOLID}
    e.update(meta)
    return e


def _seg_box(a, b, w, h, transform):
    dx, dz = b[0] - a[0], b[2] - a[2]
    ay = a[1] if a[1] is not None else 0.0
    by = b[1] if b[1] is not None else 0.0
    ln = math.sqrt(dx * dx + dz * dz)
    dy = by - ay
    if ln <= 1e-9:                      # مقطع رأسي: صندوق قائم
        return _obb((a[0] + b[0]) / 2.0, (ay + by) / 2.0, (a[2] + b[2]) / 2.0,
                    max(w, 1e-3), max(abs(dy), 1e-3), max(h, 1e-3), 0.0, transform)
    return _obb((a[0] + b[0]) / 2.0, (ay + by) / 2.0, (a[2] + b[2]) / 2.0,
                math.sqrt(ln * ln + dy * dy), max(h, 1e-3), max(w, 1e-3),
                math.atan2(-dz, dx), transform)


# ------------------------------------------------- استخراج أحجام النماذج --
def _arch_volumes(arch, transform, bid):
    out = []
    if not arch:
        return out
    lv = {l["index"]: l for l in arch.get("levels") or []}
    for w in arch.get("walls") or []:
        h = w["height_m"]["value"] or w["height_m"]["render_fallback"]
        t = w["thickness_m"]["value"] or w["thickness_m"]["render_fallback"]
        base = (lv.get(w["level_index"]) or {}).get("elevation_m")
        if base is None:
            continue
        a, b = w["start"], w["end"]
        obb = _seg_box([a["x"], base + h / 2.0, a["z"]], [b["x"], base + h / 2.0, b["z"]],
                       t, h, transform)
        out.append(_vol("ARCHITECTURE", "ARCH_WALL", w["id"], obb,
                        level_index=w["level_index"], spaces=list(w["spaces"]),
                        source_ref=w["id"], host_of=list(w["openings"]),
                        geometry_source=_gsrc(w["height_m"], w["thickness_m"])))
    for o in arch.get("openings") or []:
        wdt = o["width_m"]["value"] or o["width_m"]["render_fallback"]
        hgt = o["height_m"]["value"] or o["height_m"]["render_fallback"]
        base = (lv.get(o.get("level_index")) or {}).get("elevation_m")
        if base is None:
            continue
        sill = 0.0
        if o["type"] == "WINDOW":
            sill = o["sill_m"]["value"] if o["sill_m"]["value"] is not None \
                else o["sill_m"]["render_fallback"]
        cy = base + sill + hgt / 2.0
        if o["axis"] == "x":
            obb = _obb(o["u_center"], cy, o["fixed"], wdt, hgt, 0.2, 0.0, transform)
        else:
            obb = _obb(o["fixed"], cy, o["u_center"], 0.2, hgt, wdt, 0.0, transform)
        out.append(_vol("ARCHITECTURE", "ARCH_OPENING", o["id"], obb,
                        level_index=o.get("level_index"), space_id=o.get("space_id"),
                        host_wall_id=o.get("host_wall_id"), source_ref=o["id"],
                        geometry_source=_gsrc(o["width_m"], o["height_m"])))
    for s in arch.get("slabs") or []:
        o = s["outline"]
        t = s["thickness_m"]["value"] or s["thickness_m"]["render_fallback"]
        if o is None or s["elevation_m"] is None:
            continue
        out.append(_vol("ARCHITECTURE", "ARCH_SLAB", s["id"],
                        _obb(o[0] + o[2] / 2.0, s["elevation_m"] - t / 2.0, o[1] + o[3] / 2.0,
                             o[2], t, o[3], 0.0, transform),
                        level_index=s["level_index"], source_ref=s["id"],
                        geometry_source=_gsrc(s["thickness_m"])))
    for v in arch.get("voids") or []:
        r = v["rect"]
        base = (lv.get(v["level_index"]) or {}).get("elevation_m")
        if base is None:
            continue
        out.append(_vol("ARCHITECTURE", "ARCH_VOID", v["id"],
                        _obb(r[0] + r[2] / 2.0, base, r[1] + r[3] / 2.0, r[2], 0.4, r[3],
                             0.0, transform),
                        level_index=v["level_index"], core_id=v.get("core_id"),
                        source_ref=v["id"]))
    for c in arch.get("cores") or []:
        fw = c["footprint_w_m"]["value"] or c["footprint_w_m"]["render_fallback"]
        fd = c["footprint_d_m"]["value"] or c["footprint_d_m"]["render_fallback"]
        served = c.get("served_levels") or []
        if not served:
            continue
        base = (lv.get(min(served)) or {}).get("elevation_m")
        top = (lv.get(max(served)) or {}).get("elevation_m")
        if base is None or top is None or top - base <= 0:
            continue
        out.append(_vol("ARCHITECTURE", "ARCH_CORE", c["id"],
                        _obb(c["x"], base + (top - base) / 2.0, c["z"], fw, top - base, fd,
                             0.0, transform),
                        core_type=c["type"], source_ref=c["id"],
                        geometry_source=_gsrc(c["footprint_w_m"], c["footprint_d_m"])))
    return out


def _struct_volumes(struct, transform):
    out = []
    if not struct:
        return out
    kinds = {"COLUMN": "STRUCT_COLUMN", "BEAM": "STRUCT_BEAM",
             "STRUCTURAL_SLAB": "STRUCT_SLAB", "STRUCTURAL_WALL": "STRUCT_WALL",
             "FOUNDATION": "STRUCT_FOUNDATION", "STRUCTURAL_CORE": "STRUCT_CORE"}
    supports = {}
    for r in struct.get("relationships") or []:
        if r["type"] == "COLUMN_SUPPORTS":
            supports.setdefault(r["to"], set()).add(r["from"])
            supports.setdefault(r["from"], set()).add(r["to"])
    for it in STRUCT.render_items(struct):
        if it["kind"] == "GRID_LINE":
            continue
        kind = kinds.get(it["kind"], "STRUCT_COLUMN")
        el = STRUCT.element_by_id(struct, it["id"])
        meta = {"source_ref": it["id"],
                "connected": sorted(supports.get(it["id"], set())),
                "geometry_source": it["geometry_source"]}
        if el is not None:
            meta["level_index"] = el.get("level_index")
            meta["base_level_index"] = el.get("base_level_index")
            meta["top_level_index"] = el.get("top_level_index")
            meta["level_indexes"] = el.get("level_indexes")
            cl = _num((el.get("properties") or {}).get("clearance_m")) if isinstance(
                el.get("properties"), dict) else None
            if cl is not None:
                meta["clearance_m"] = cl
        out.append(_vol("STRUCTURE", kind, it["id"],
                        _obb(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"],
                             it.get("rot_y") or 0.0, transform), **meta))
    return out


def _mep_volumes(mep, transform, bid):
    out = []
    if not mep:
        return out
    seg_by_id = {s["id"]: s for s in mep.get("segments") or []}
    for it in MEP.render_items(mep):
        if it["kind"] == "SEGMENT":
            s = seg_by_id.get(it["id"])
            out.append(_vol("MEP", "MEP_SEGMENT", it["name"],
                            _obb(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"],
                                 it.get("rot_y") or 0.0, transform),
                            segment_id=it["id"], source_ref=it["id"],
                            level_index=(s or {}).get("level_index"),
                            system_id=(s or {}).get("system_id"),
                            geometry_source=it["geometry_source"]))
            continue
        kind = {"EQUIPMENT": "MEP_EQUIPMENT", "TERMINAL": "MEP_TERMINAL",
                "RISER": "MEP_RISER"}.get(it["kind"], "MEP_EQUIPMENT")
        el = MEP.element_by_id(mep, it["id"])
        meta = {"source_ref": it["id"], "geometry_source": it["geometry_source"]}
        if el is not None:
            meta["level_index"] = el.get("level_index")
            meta["space_id"] = el.get("space_id")
            meta["system_id"] = el.get("system_id")
            props = el.get("properties") or {}
            cl = _num((props.get("clearance_m") or {}).get("value")) \
                if isinstance(props.get("clearance_m"), dict) else None
            if cl is not None:
                meta["clearance_m"] = cl
        out.append(_vol("MEP", kind, it["id"],
                        _obb(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"],
                             it.get("rot_y") or 0.0, transform), **meta))
    return out


def _fls_volumes(fls, transform):
    """العناصر المُشار إليها لا تُدرَج: هندستها مملوكة لطبقة MEP، وإدراجها هنا
    كان سيصنع تعارضاً وهمياً مع نفسها."""
    out = []
    if not fls:
        return out
    for it in FLS.render_items(fls):
        if it["render_mode"] != "emitted":
            continue
        el = FLS.element_by_id(fls, it["id"])
        kind = {"DEVICE": "FLS_DEVICE", "SIGN": "FLS_SIGN",
                "ASSEMBLY_POINT": "FLS_ASSEMBLY_POINT"}.get(it["kind"], "FLS_DEVICE")
        meta = {"source_ref": (el or {}).get("mep_element_id") or it["id"],
                "device_type": it.get("device_type")}
        if el is not None:
            meta["level_index"] = el.get("level_index")
            meta["space_id"] = el.get("space_id")
        out.append(_vol("FLS", kind, it["id"],
                        _obb(it["cx"], it["cy"], it["cz"], it["ex"], it["ey"], it["ez"],
                             0.0, transform), **meta))
    return out


# ---------------------------------------------------------- الاختراقات --
def _penetrations(mep, arch, struct, bid, transform):
    out = []
    for n, p in enumerate(sorted((mep or {}).get("penetrations") or [],
                                 key=lambda x: str(x["id"]))):
        host = None
        for key, src in (("walls", arch), ("slabs", arch), ("beams", struct),
                         ("columns", struct), ("slabs", struct), ("walls", struct)):
            for e in (src or {}).get(key) or []:
                if e["id"] == p.get("host_id"):
                    host = e
                    break
            if host is not None:
                break
        seg = None
        for s in (mep or {}).get("segments") or []:
            if s["id"] == p.get("segment_id") or \
               s["id"] == MEP._nid(bid, p.get("segment_id"), "seg", 0):
                seg = s
                break
        out.append({"id": "%s.coord.pen_%d" % (bid, n), "penetration_id": p["id"],
                    "host_element": p.get("host_id"), "host_type": p.get("host_type"),
                    "host_resolved": host is not None,
                    "service_element": seg["id"] if seg else p.get("segment_id"),
                    "service_resolved": seg is not None,
                    "x": p.get("x"), "z": p.get("z"), "level_index": p.get("level_index"),
                    "size": p.get("size"), "source": p.get("source"),
                    "status": "REPRESENTED",
                    "note": "a represented penetration is not a structurally approved opening, "
                            "is not firestopped and is not code compliant"})
    return out


def _pen_covers(pen, inter):
    """هل يغطّي الاختراق المعلن موضع العبور فعلاً؟ بلا موضع معلن لا نجزم."""
    if pen.get("x") is None or pen.get("z") is None:
        return None
    sz = pen.get("size") or {}
    r = _num(sz.get("diameter_m")) or _num(sz.get("width_m")) or 0.6
    cx = (inter["min"][0] + inter["max"][0]) / 2.0
    cz = (inter["min"][2] + inter["max"][2]) / 2.0
    return abs(cx - float(pen["x"])) <= r + 0.5 and abs(cz - float(pen["z"])) <= r + 0.5


# ------------------------------------------------------------ الاستثناء --
def _exempt(a, b, pens, openings):
    """استثناءات دلالية مبرَّرة بعلاقة معلنة — لا استثناء بحسب النوع وحده."""
    if a.get("source_ref") and a.get("source_ref") == b.get("source_ref"):
        return "SAME_SOURCE_ELEMENT"
    if a["discipline"] == "FLS" and b["discipline"] == "MEP" and \
       a.get("source_ref") == b.get("element_id"):
        return "FLS_REFERENCES_MEP_ELEMENT"
    if b["discipline"] == "FLS" and a["discipline"] == "MEP" and \
       b.get("source_ref") == a.get("element_id"):
        return "FLS_REFERENCES_MEP_ELEMENT"
    for x, y in ((a, b), (b, a)):
        if x["kind"] == "ARCH_OPENING" and y["kind"] == "ARCH_WALL" and \
           x.get("host_wall_id") == y["element_id"]:
            return "OPENING_IN_ITS_HOST_WALL"
        if x["kind"] == "STRUCT_COLUMN" and y["kind"] in ("ARCH_SLAB", "STRUCT_SLAB"):
            lo, hi = x.get("base_level_index"), x.get("top_level_index")
            li = y.get("level_index")
            if lo is not None and hi is not None and li is not None and lo <= li <= hi:
                return "COLUMN_THROUGH_ITS_OWN_LEVEL_SLAB"
        if x["kind"] == "STRUCT_BEAM" and y["kind"] == "STRUCT_COLUMN" and \
           y["element_id"] in (x.get("connected") or []):
            return "BEAM_MEETS_COLUMN_AT_NODE"
        # فراغ معلن لا مادّة فيه: لا شيء يصطدم به، والزوج يُسجَّل بدل أن يُخفى
        if not y.get("solid") and x.get("solid"):
            return "ELEMENT_INSIDE_DECLARED_VOID_OR_CORE"
        # مقطع يعبر الجدار داخل فتحة معلنة في الجدار نفسه — لا فتحة جديدة مطلوبة
        if x["kind"] == "MEP_SEGMENT" and y["kind"] == "ARCH_WALL" and openings:
            for oid in (y.get("host_of") or []):
                ov = openings.get(oid)
                if ov is not None and _aabb_overlap(x["aabb"], ov["aabb"]):
                    return "SEGMENT_THROUGH_EXISTING_OPENING"
    if not a.get("solid") and not b.get("solid"):
        return "ELEMENT_INSIDE_DECLARED_VOID_OR_CORE"
    return None


def _pen_exempt(a, b, pens, inter):
    """مقطع MEP داخل اختراق معلن يغطّي موضع العبور فعلاً."""
    for x, y in ((a, b), (b, a)):
        if x["kind"] != "MEP_SEGMENT":
            continue
        for p in pens:
            if p["service_element"] != x.get("segment_id"):
                continue
            if p["host_element"] != y["element_id"]:
                continue
            cov = _pen_covers(p, inter)
            if cov is None or cov:
                return ("SEGMENT_IN_DECLARED_PENETRATION", p, cov)
            return (None, p, False)
    return (None, None, None)


# ------------------------------------------------- الفهرسة والمرحلة العريضة --
def _cell_span(aabb):
    """عدد الخلايا التي يغطّيها الصندوق — يُحسب قبل توليدها كي لا يُبنى ملايين
    المفاتيح لعنصر ضخم واحد."""
    nx = int(math.floor(aabb[3] / CELL)) - int(math.floor(aabb[0] / CELL)) + 1
    ny = int(math.floor(aabb[4] / CELL)) - int(math.floor(aabb[1] / CELL)) + 1
    nz = int(math.floor(aabb[5] / CELL)) - int(math.floor(aabb[2] / CELL)) + 1
    return nx * ny * nz


def _cells(aabb):
    out = []
    for ix in range(int(math.floor(aabb[0] / CELL)), int(math.floor(aabb[3] / CELL)) + 1):
        for iy in range(int(math.floor(aabb[1] / CELL)), int(math.floor(aabb[4] / CELL)) + 1):
            for iz in range(int(math.floor(aabb[2] / CELL)), int(math.floor(aabb[5] / CELL)) + 1):
                out.append((ix, iy, iz))
    return out


_PAIR_SET = {tuple(sorted(p)) for p in DISCIPLINE_PAIRS}


_MAX_CELLS = 4096


def _index_aabb(v):
    """صندوق الفهرسة يتّسع بالخلوص المذكور فقط — كي لا يفوت تعارض خلوص في
    المرحلة العريضة. لا خلوص مُخترع، ومن لا يذكر خلوصاً يُفهرس بصندوقه كما هو."""
    cl = v.get("clearance_m")
    if cl is None or cl <= 0:
        return v["aabb"]
    a = v["aabb"]
    return [a[0] - cl, a[1] - cl, a[2] - cl, a[3] + cl, a[4] + cl, a[5] + cl]


def broad_phase(volumes):
    """تجزئة مكانية موحّدة: مرشّحون هم أزواج التخصّصات المختلفة في خلية مشتركة.
    العنصر الذي يغطي خلايا أكثر من الحدّ يوضع في قائمة كبيرة الحجم ويُقارن بالكل —
    فلا يُسقَط أي زوج، والعدد يُبلَّغ في الإحصاء بدل أن يُخفى."""
    grid, oversized = {}, []
    for i, v in enumerate(volumes):
        box = _index_aabb(v)
        if _cell_span(box) > _MAX_CELLS:
            oversized.append(i)
            continue
        for c in _cells(box):
            grid.setdefault(c, []).append(i)
    pairs = set()

    def _consider(a, b):
        da, db = volumes[a]["discipline"], volumes[b]["discipline"]
        if da == db:
            return
        if tuple(sorted((da, db))) not in _PAIR_SET:
            return
        pairs.add((a, b) if a < b else (b, a))

    busiest = 0
    for c in sorted(grid):
        idxs = grid[c]
        if len(idxs) > busiest:
            busiest = len(idxs)
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                _consider(idxs[i], idxs[j])
    for a in oversized:
        for b in range(len(volumes)):
            if a != b:
                _consider(a, b)
    return sorted(pairs), {"cells": len(grid), "oversized_elements": len(oversized),
                           "busiest_cell": busiest}


# ------------------------------------------------------------- التصريف --
def _elements_index(arch, struct, mep, fls):
    ids = set()
    for src, keys in ((arch, ("walls", "openings", "slabs", "voids", "cores", "spaces")),
                      (struct, ("columns", "beams", "slabs", "walls", "foundations",
                                "cores", "nodes", "materials")),
                      (mep, ("systems", "nodes", "segments", "equipment", "terminals",
                             "risers", "penetrations")),
                      (fls, ("zones", "barriers", "openings", "exits", "stairs", "shafts",
                             "devices", "systems", "signs", "assembly_points",
                             "refuge_areas", "smoke_control"))):
        for k in keys:
            for e in (src or {}).get(k) or []:
                ids.add(e["id"])
    return ids


_SEMANTIC_SOURCE = {
    "ARCHITECTURE": (),
    "STRUCTURE": ("INVALID_LEVEL_REF", "INVALID_NODE_REF", "INVALID_MATERIAL_REF",
                  "INVALID_GRID_REF", "CROSS_BUILDING_REF", "FOUNDATION_TARGET_UNRESOLVED"),
    "MEP": ("INVALID_SYSTEM_REF", "INVALID_NODE_REF", "INVALID_EQUIPMENT_REF",
            "INVALID_LEVEL_REF", "INVALID_SPACE_REF", "CROSS_BUILDING_REF",
            "PENETRATION_HOST_UNRESOLVED", "PENETRATION_SEGMENT_UNRESOLVED"),
    "FLS": ("INVALID_SYSTEM_REF", "INVALID_MEP_ELEMENT_REF", "INVALID_LEVEL_REF",
            "INVALID_SPACE_REF", "INVALID_EXIT_REF", "INVALID_HOST_WALL_REF",
            "INVALID_HOST_OPENING_REF", "INVALID_CORE_REF", "INVALID_ZONE_SPACE_REF",
            "INVALID_BARRIER_REF", "CROSS_BUILDING_REF", "SIGN_TARGET_MISSING",
            "FIRE_DOOR_NOT_HOSTED", "BARRIER_WITHOUT_HOST")}

_SEMANTIC_PARTNER = {"FLS": "ARCHITECTURE", "MEP": "ARCHITECTURE", "STRUCTURE": "ARCHITECTURE"}
_SEMANTIC_MEP = ("INVALID_MEP_ELEMENT_REF", "INVALID_SYSTEM_REF")


def _semantic_conflicts(bid, arch, struct, mep, fls):
    """تعارضات مرجعية بين التخصّصات — مأخوذة من فحوص كل طبقة، لا مُختلقة."""
    out = []
    for disc, model in (("STRUCTURE", struct), ("MEP", mep), ("FLS", fls)):
        for i in (model or {}).get("issues") or []:
            if i["code"] not in _SEMANTIC_SOURCE[disc]:
                continue
            partner = "MEP" if (disc == "FLS" and i["code"] in _SEMANTIC_MEP) \
                else _SEMANTIC_PARTNER[disc]
            ctype = "INVALID_REFERENCE" if i["code"].startswith("INVALID") \
                else "SEMANTIC_CONFLICT"
            ref = i.get("ref") if i.get("ref") is not None else i.get("refs")
            out.append({"type": ctype, "discipline_a": disc, "element_a": i.get("subject"),
                        "discipline_b": partner, "element_b": (str(ref) if ref is not None
                                                               else None),
                        "code": i["code"], "detail": i.get("detail"),
                        "evidence": {"kind": "reference", "reported_by": disc,
                                     "source_code": i["code"]}})
    out.sort(key=lambda e: (str(e["type"]), str(e["discipline_a"]), str(e["element_a"]),
                            str(e["code"]), str(e["element_b"])))
    return out


def compile_coordination(building, building_id="bld_0", position=None, rotation_deg=0.0,
                         arch=None, struct=None, mep=None, fls=None, at=None):
    """يبني لقطة تنسيق مشتقّة. لا يعدّل أي نموذج ولا يصلح أي تعارض."""
    return compile_project_coordination(
        [{"id": building_id, "building": building, "position": position,
          "rotation_deg": rotation_deg, "arch": arch, "struct": struct, "mep": mep,
          "fls": fls}], at=at)


def compile_project_coordination(entries, at=None):
    """تنسيق على مستوى المشروع: كل مبنى يُحلّ إلى الإحداثيات العالمية أولاً،
    فلا يتصادم مبنيان لمجرّد تشابه إحداثياتهما المحلية."""
    volumes, pens, disciplines, hashes, semantic = [], [], [], [], []
    for ent in entries:
        bid = ent.get("id") or "bld_0"
        b = ent.get("building") or {}
        pos = ent.get("position")
        rot = ent.get("rotation_deg") or 0.0
        transform = {"position": pos or {"x": 0.0, "z": 0.0}, "rotation_deg": float(rot)}
        arch = ent.get("arch")
        if arch is None:
            try:
                arch = ARCH.compile_architecture(b, bid, pos, rot)
            except Exception:
                arch = None
        struct = ent.get("struct")
        if struct is None:
            try:
                struct = STRUCT.compile_structure(b, bid, pos, rot, arch)
            except Exception:
                struct = None
        mep = ent.get("mep")
        if mep is None:
            try:
                mep = MEP.compile_mep(b, bid, pos, rot, arch, struct)
            except Exception:
                mep = None
        fls = ent.get("fls")
        if fls is None:
            try:
                fls = FLS.compile_fls(b, bid, pos, rot, arch, mep)
            except Exception:
                fls = None
        try:
            mh = REV.model_hash(b, "building", bid)
        except Exception:
            mh = None
        # الوضع والدوران جزء من الهوية: مبنى تحرّك يُبطل اللقطة ولو لم يتغيّر نموذجه
        hashes.append({"building_id": bid, "model_hash": mh,
                       "position": {"x": _q(transform["position"].get("x") or 0.0),
                                    "z": _q(transform["position"].get("z") or 0.0)},
                       "rotation_deg": _q(transform["rotation_deg"])})
        disciplines.append({"building_id": bid,
                            "ARCHITECTURE": bool(arch), "STRUCTURE": bool(struct),
                            "MEP": bool(mep), "FLS": bool(fls),
                            "transform": transform})
        # وسم المبنى لكل حجم عند إدراجه — لا يُستنتج لاحقاً من الترتيب
        mine = []
        mine.extend(_arch_volumes(arch, transform, bid))
        mine.extend(_struct_volumes(struct, transform))
        mine.extend(_mep_volumes(mep, transform, bid))
        mine.extend(_fls_volumes(fls, transform))
        for v in mine:
            v["building_id"] = bid
        volumes.extend(mine)
        pens.extend(_penetrations(mep, arch, struct, bid, transform))
        semantic.extend(_semantic_conflicts(bid, arch, struct, mep, fls))
    volumes.sort(key=lambda v: (str(v["building_id"]), str(v["discipline"]),
                                str(v["kind"]), str(v["element_id"])))

    openings = {v["element_id"]: v for v in volumes if v["kind"] == "ARCH_OPENING"}
    pairs, gstats = broad_phase(volumes)
    clashes, clearance, suppressed = [], [], []
    seen_source = {}
    for (i, j) in pairs:
        a, b = volumes[i], volumes[j]
        ex = _exempt(a, b, pens, openings)
        inter = _aabb_overlap(a["aabb"], b["aabb"])
        if ex:
            if inter:
                suppressed.append({"exemption": ex, "element_a": a["element_id"],
                                   "element_b": b["element_id"]})
            if ex == "SAME_SOURCE_ELEMENT" and a["element_id"] != b["element_id"]:
                key = str(a.get("source_ref"))
                if key not in seen_source:
                    seen_source[key] = True
                    clashes.append(_mk("DUPLICATE_OCCUPANCY", a, b,
                                       {"kind": "shared_source_element",
                                        "source_ref": a.get("source_ref")},
                                       "the same underlying element is represented twice; "
                                       "no clash is reported for it"))
            continue
        if inter is None:
            cl = _clearance(a, b)
            if cl is not None:
                clearance.append(cl)
            continue
        if not _obb_overlap(a["obb"], b["obb"]):
            continue
        pen_ex, pen, cov = _pen_exempt(a, b, pens, inter)
        if pen_ex:
            suppressed.append({"exemption": pen_ex, "element_a": a["element_id"],
                               "element_b": b["element_id"],
                               "penetration": pen["penetration_id"]})
            continue
        if pen is not None and cov is False:
            clashes.append(_mk("PENETRATION_UNRESOLVED", a, b, inter,
                               "a penetration is declared for this crossing but does not cover "
                               "it; nothing is created or moved",
                               penetration=pen["penetration_id"]))
            continue
        host = _host_kind(a, b)
        if host == "arch":
            clashes.append(_mk("OPENING_REQUIRED", a, b, inter,
                               "a route crosses this host with no represented penetration; "
                               "this is a coordination finding, not an instruction, and no "
                               "opening is created"))
        else:
            clashes.append(_mk("HARD_CLASH", a, b, inter,
                               "a real volume intersection in resolved world coordinates; "
                               "nothing is moved, resized or rerouted"))
    out_clashes = clashes + clearance + [
        _mk_semantic(s) for s in semantic]
    for c in out_clashes:
        c["severity"] = severity_of(c["type"])
    out_clashes.sort(key=lambda c: (SEVERITIES.index(c["severity"]), str(c["type"]),
                                    str(c["element_a"]), str(c["element_b"])))
    mh = hashes[0]["model_hash"] if len(hashes) == 1 else None
    ph = hashlib.sha256(_canon(_project_key(hashes)).encode("utf-8")).hexdigest()
    snap = {"schema": SCHEMA, "detector_version": DETECTOR_VERSION,
            "created_at": at, "model_hashes": hashes, "revision_hash": mh,
            "project_hash": ph,
            "snapshot_id": "coord_" + ((mh[:16]) if mh else ph[:16]),
            "disciplines": disciplines,
            "clashes": out_clashes,
            "penetrations": pens,
            "clearance_issues": [c for c in out_clashes if c["type"] == "CLEARANCE_CLASH"],
            "semantic_conflicts": [c for c in out_clashes
                                   if c["type"] in ("SEMANTIC_CONFLICT", "INVALID_REFERENCE")],
            "suppressed": sorted(suppressed, key=lambda s: (str(s["exemption"]),
                                                            str(s["element_a"]),
                                                            str(s["element_b"]))),
            "statistics": {"elements": len(volumes), "candidate_pairs": len(pairs),
                           "grid_cells": gstats["cells"], "grid_cell_m": CELL,
                           "oversized_elements": gstats["oversized_elements"],
                           "busiest_cell": gstats["busiest_cell"],
                           "suppressed_by_exemption": len(suppressed)},
            "meta": {"note": SPEC["note"], "derivation": SPEC["derivation_note"],
                     "navigation_impact": SPEC["navigation_note"],
                     "broad_phase": SPEC["broad_phase"], "narrow_phase": SPEC["narrow_phase"],
                     "compliance": "NOT_EVALUATED"}}
    snap["summary"] = summary(snap)
    return snap


def _mk(ctype, a, b, evidence, note, penetration=None):
    da, db = a["discipline"], b["discipline"]
    ea, eb = a["element_id"], b["element_id"]
    if (da, ea) > (db, eb):
        a, b, da, db, ea, eb = b, a, db, da, eb, ea
    c = {"id": _clash_id(ctype, da, ea, db, eb), "type": ctype,
         "discipline_a": da, "element_a": ea, "kind_a": a["kind"],
         "discipline_b": db, "element_b": eb, "kind_b": b["kind"],
         "building_a": a.get("building_id"), "building_b": b.get("building_id"),
         "cross_building": bool(a.get("building_id") != b.get("building_id")),
         "geometry": {"aabb_a": a["aabb"], "aabb_b": b["aabb"], "intersection": evidence},
         "level_index": a.get("level_index") if a.get("level_index") is not None
                        else b.get("level_index"),
         "status": "OPEN", "note": note,
         "evidence": {"kind": "geometry", "detector_version": DETECTOR_VERSION}}
    fb = [e["element_id"] for e in (a, b)
          if e.get("geometry_source") not in (None, "model", "imported", "stated")]
    c["geometry_confidence"] = "display_fallback" if fb else "stated"
    c["evidence"]["geometry_source_a"] = a.get("geometry_source")
    c["evidence"]["geometry_source_b"] = b.get("geometry_source")
    if fb:
        c["evidence"]["fallback_geometry"] = sorted(fb)
        c["evidence"]["confidence_note"] = (
            "at least one side is sized from a display fallback, not from stated model "
            "dimensions; the intersection is reported as found and the fallback is never "
            "promoted to an engineering dimension")
    if penetration:
        c["penetration"] = penetration
    return c


def _mk_semantic(s):
    c = {"id": _clash_id(s["type"], s["discipline_a"], s["element_a"],
                         s["discipline_b"], s["element_b"]),
         "type": s["type"], "discipline_a": s["discipline_a"], "element_a": s["element_a"],
         "kind_a": None, "discipline_b": s["discipline_b"], "element_b": s["element_b"],
         "kind_b": None, "geometry": None, "level_index": None,
         "status": "OPEN", "code": s["code"], "detail": s.get("detail"),
         "note": "a reference in one discipline does not resolve in another; this is a "
                 "coordination integrity finding, not a code or safety judgement",
         "evidence": s["evidence"]}
    return c


def _clearance(a, b):
    """تعارض خلوص فقط حيث ذُكر خلوص صراحةً — لا خلوص مُخترع إطلاقاً."""
    for x, y in ((a, b), (b, a)):
        cl = x.get("clearance_m")
        if cl is None or cl <= 0:
            continue
        grown = [x["aabb"][0] - cl, x["aabb"][1] - cl, x["aabb"][2] - cl,
                 x["aabb"][3] + cl, x["aabb"][4] + cl, x["aabb"][5] + cl]
        inter = _aabb_overlap(grown, y["aabb"])
        if inter:
            c = _mk("CLEARANCE_CLASH", x, y, inter,
                    "an element states a clearance and another element lies inside it; "
                    "no clearance is ever invented and none is applied here")
            c["clearance_m"] = cl
            return c
    return None


def _host_kind(a, b):
    """هل الطرف المضيف عنصر معماري يمكن اختراقه (جدار/بلاطة) والطرف الآخر خدمة؟"""
    for x, y in ((a, b), (b, a)):
        if x["kind"] in ("ARCH_WALL", "ARCH_SLAB") and y["kind"] == "MEP_SEGMENT":
            return "arch"
    return None


# ----------------------------------------------- نزاهة اللقطة والمصالحة --
def check_project_snapshot(snapshot, entries):
    """نظير check_snapshot على مستوى المشروع: يشمل وضع كل مبنى ودورانه،
    فمبنى تحرّك يُبطل اللقطة حتى لو بقي نموذجه كما هو."""
    try:
        cur = []
        for ent in entries or []:
            bid = ent.get("id") or "bld_0"
            pos = ent.get("position") or {"x": 0.0, "z": 0.0}
            cur.append({"building_id": bid,
                        "model_hash": REV.model_hash(ent.get("building") or {}, "building", bid),
                        "position": {"x": _q(pos.get("x") or 0.0), "z": _q(pos.get("z") or 0.0)},
                        "rotation_deg": _q(ent.get("rotation_deg") or 0.0)})
        now = hashlib.sha256(_canon(_project_key(cur)).encode("utf-8")).hexdigest()
    except Exception:
        return {"status": "UNVERIFIABLE", "reason": "the project hash could not be computed",
                "presented_as_current": False}
    stored = snapshot.get("project_hash")
    if stored is None:
        return {"status": "UNVERIFIABLE", "reason": "the snapshot carries no project hash",
                "presented_as_current": False}
    if stored != now:
        return {"status": "STALE_MODEL_CHANGED", "stored_hash": stored, "current_hash": now,
                "presented_as_current": False,
                "reason": "a model or a building placement changed after this coordination run; "
                          "its clash count is not the current clash count"}
    return {"status": "CURRENT", "stored_hash": stored, "current_hash": now,
            "presented_as_current": True}


def check_snapshot(snapshot, building, building_id="bld_0"):
    """يقارن بصمة النموذج الحالية ببصمة اللقطة. لا يعيد الكشف ولا يخفي القِدَم."""
    try:
        now = REV.model_hash(building, "building", building_id)
    except Exception:
        return {"status": "UNVERIFIABLE", "reason": "model hash could not be computed",
                "presented_as_current": False}
    stored = snapshot.get("revision_hash")
    if stored is None:
        return {"status": "UNVERIFIABLE", "reason": "the snapshot carries no model hash",
                "presented_as_current": False}
    if stored != now:
        return {"status": "STALE_MODEL_CHANGED", "stored_hash": stored, "current_hash": now,
                "presented_as_current": False,
                "reason": "the model changed after this coordination run; its clash count is "
                          "not the current clash count"}
    return {"status": "CURRENT", "stored_hash": stored, "current_hash": now,
            "presented_as_current": True}


def reconcile(snapshot_a, snapshot_b):
    """يصنّف تعارضات لقطتين. RESOLVED_BY_MODEL_CHANGE يعني أنّ الهندسة اختفت،
    لا أنّ التصميم صحّ."""
    a = {c["id"]: c for c in (snapshot_a or {}).get("clashes") or []}
    b = {c["id"]: c for c in (snapshot_b or {}).get("clashes") or []}
    out = []
    for cid in sorted(set(a) | set(b)):
        if cid in a and cid in b:
            state = "PERSISTING"
        elif cid in b:
            state = "NEW"
        else:
            state = ("OBSOLETE" if a[cid].get("status") in
                     ("ACKNOWLEDGED", "FALSE_POSITIVE", "RESOLVED_EXTERNALLY")
                     else "RESOLVED_BY_MODEL_CHANGE")
        src = b.get(cid) or a.get(cid)
        out.append({"id": cid, "state": state, "type": src["type"],
                    "discipline_a": src["discipline_a"], "element_a": src["element_a"],
                    "discipline_b": src["discipline_b"], "element_b": src["element_b"],
                    "previous_status": a[cid]["status"] if cid in a else None,
                    "note": "RESOLVED_BY_MODEL_CHANGE states only that the geometry that "
                            "produced this finding is no longer present"})
    counts = {}
    for r in out:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {"detector_version": DETECTOR_VERSION,
            "hash_a": (snapshot_a or {}).get("revision_hash"),
            "hash_b": (snapshot_b or {}).get("revision_hash"),
            "results": out, "counts": counts,
            "note": "no reconciliation state asserts that a change was correct, adequate or "
                    "engineered"}


def set_status(snapshot, clash_id, status, by=None, at=None, note=None):
    """قرار بشري صريح فقط. لا حالة تُغيَّر تلقائياً بناءً على الهندسة."""
    if status not in CLASH_STATUSES or status == "OPEN":
        return (False, "STATUS_NOT_ALLOWED", None)
    if status == "OBSOLETE":
        return (False, "OBSOLETE_IS_DERIVED_NOT_SET", None)
    for c in snapshot.get("clashes") or []:
        if c["id"] == clash_id:
            c["status"] = status
            c["decision"] = {"by": by, "at": at, "note": note,
                             "basis": "explicit human decision; never derived from geometry"}
            return (True, None, c)
    return (False, "CLASH_NOT_FOUND", None)


# ---------------------------------------------------------------- خدمات --
def clash_by_id(snapshot, cid):
    for c in snapshot.get("clashes") or []:
        if c["id"] == cid:
            return c
    return None


def filter_clashes(snapshot, discipline_a=None, discipline_b=None, level_index=None,
                   building_id=None, ctype=None, status=None, severity=None):
    out = []
    for c in snapshot.get("clashes") or []:
        pair = {c["discipline_a"], c["discipline_b"]}
        if discipline_a and discipline_a not in pair:
            continue
        if discipline_b and discipline_b not in pair:
            continue
        if level_index is not None and c.get("level_index") != level_index:
            continue
        if building_id and building_id not in (c.get("building_a"), c.get("building_b")):
            continue
        if ctype and c["type"] != ctype:
            continue
        if status and c["status"] != status:
            continue
        if severity and c["severity"] != severity:
            continue
        out.append(c)
    return out


def debug_view(snapshot, clash_id):
    """بيانات إبراز للتصحيح — لا تغيّر مظهر النموذج الطبيعي إطلاقاً."""
    c = clash_by_id(snapshot, clash_id)
    if c is None:
        return None
    g = c.get("geometry") or {}
    return {"clash_id": c["id"], "highlight": [c["element_a"], c["element_b"]],
            "isolate": [c["element_a"], c["element_b"]],
            "aabb_a": g.get("aabb_a"), "aabb_b": g.get("aabb_b"),
            "intersection": g.get("intersection"),
            "marker": (None if not g.get("intersection") else
                       {"cx": _q((g["intersection"]["min"][0] + g["intersection"]["max"][0]) / 2.0),
                        "cy": _q((g["intersection"]["min"][1] + g["intersection"]["max"][1]) / 2.0),
                        "cz": _q((g["intersection"]["min"][2] + g["intersection"]["max"][2]) / 2.0),
                        "ex": _q(g["intersection"]["max"][0] - g["intersection"]["min"][0]),
                        "ey": _q(g["intersection"]["max"][1] - g["intersection"]["min"][1]),
                        "ez": _q(g["intersection"]["max"][2] - g["intersection"]["min"][2])}),
            "note": "debug overlay only — the normal model appearance is never changed and "
                    "no clash geometry is baked into the standard export"}


def export_snapshot(snapshot):
    """تصدير صريح للقطة تنسيق. مشتقّة لا حقيقة نموذج، ولا تُدمَج في التصدير العادي."""
    return {"schema": snapshot.get("schema"),
            "detector_version": snapshot.get("detector_version"),
            "revision_hash": snapshot.get("revision_hash"),
            "project_hash": snapshot.get("project_hash"),
            "model_hashes": snapshot.get("model_hashes"),
            "snapshot_id": snapshot.get("snapshot_id"),
            "created_at": snapshot.get("created_at"),
            "clashes": [{"id": c["id"], "type": c["type"], "severity": c["severity"],
                         "status": c["status"],
                         "discipline_a": c["discipline_a"], "element_a": c["element_a"],
                         "discipline_b": c["discipline_b"], "element_b": c["element_b"],
                         "building_a": c.get("building_a"), "building_b": c.get("building_b"),
                         "cross_building": c.get("cross_building"),
                         "geometry_confidence": c.get("geometry_confidence"),
                         "geometry": c.get("geometry"), "evidence": c.get("evidence")}
                        for c in snapshot.get("clashes") or []],
            "penetrations": snapshot.get("penetrations"),
            "summary": snapshot.get("summary"),
            "derived": True,
            "note": "a derived coordination snapshot; it is never persisted as core model "
                    "truth and never modifies any discipline model"}


def rule_inputs(snapshot):
    s = snapshot.get("summary") or summary(snapshot)
    out = {"building": {"coordination.clash.count": s["clashes"],
                        "coordination.issue.exists": s["clashes"] > 0,
                        "coordination.penetration.count": s["penetrations"],
                        "coordination.penetration.exists": s["penetrations"] > 0}}
    for t in CLASH_TYPES:
        out["building"]["coordination.clash.count_by_type." + t] = s["by_type"].get(t, 0)
    return out


def summary(snapshot):
    cl = snapshot.get("clashes") or []
    by_type, by_pair, by_status, by_conf, by_exempt = {}, {}, {}, {}, {}
    for c in cl:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
        k = " ↔ ".join(sorted([c["discipline_a"], c["discipline_b"]]))
        by_pair[k] = by_pair.get(k, 0) + 1
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        gc = c.get("geometry_confidence") or "not_applicable"
        by_conf[gc] = by_conf.get(gc, 0) + 1
    for x in snapshot.get("suppressed") or []:
        by_exempt[x["exemption"]] = by_exempt.get(x["exemption"], 0) + 1
    st = snapshot.get("statistics") or {}
    return {"detector_version": snapshot.get("detector_version"),
            "revision_hash": snapshot.get("revision_hash"),
            "clashes": len(cl), "by_type": by_type, "by_discipline_pair": by_pair,
            "by_status": by_status, "by_geometry_confidence": by_conf,
            "by_exemption": by_exempt,
            "errors": sum(1 for c in cl if c.get("severity") == "ERROR"),
            "warnings": sum(1 for c in cl if c.get("severity") == "WARNING"),
            "infos": sum(1 for c in cl if c.get("severity") == "INFO"),
            "penetrations": len(snapshot.get("penetrations") or []),
            "suppressed_by_exemption": st.get("suppressed_by_exemption", 0),
            "elements": st.get("elements", 0), "candidate_pairs": st.get("candidate_pairs", 0),
            "compliance": "NOT_EVALUATED",
            "geometry_confidence_note": "display_fallback means at least one side of the "
                                        "intersection is sized from a render fallback rather "
                                        "than a stated model dimension",
            "note": "coordination detection and traceability only — no auto-fix, no rerouting, "
                    "no redesign, no code compliance and no safety claim"}
