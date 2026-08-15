# -*- coding: utf-8 -*-
# =============================================================================
# acs_mep.py — أساس نموذج أنظمة الكهروميكانيك: تمثيل فقط، لا تصميم.
#
# يمثّل: أنظمة · عقد · مقاطع (مواسير/مجاري هواء/مواسير كهرباء/صواني) · معدّات ·
# نهايات · مناور رأسية · اختراقات · علاقات. النوع نفسه لكل أنواع المباني.
#
# مبادئ صارمة:
#   • لا حساب أحمال كهربائية ولا هبوط جهد ولا تحجيم كوابل/قواطع/محوّلات.
#   • لا حساب أحمال تبريد/تدفئة ولا تدفّق هواء ولا تحجيم مجاري ولا ضغط ثابت.
#   • لا وحدات تجهيزات ولا طلب مياه ولا تحجيم مواسير ولا ضاغط مضخّة.
#   • لا هيدروليك مرشّات ولا طلب مياه حريق ولا تصميم إنذار — تمثيل بيانات فقط.
#   • لا ادّعاء مطابقة SBC/NFPA/NEC/IEC/ASHRAE/SMACNA/IPC ولا أي معيار.
#   • النظام لا يُستنتج من نوع المبنى: لا مرشّات لأنها فيلا، ولا طوارئ لأنه فندق.
#   • ما لم يذكره النموذج يبقى null، والاحتياط يظهر منفصلاً بمصدر display_fallback.
#   • وجود نهاية في فراغ = تمثيل، لا كفاية خدمة.
#   • التعارض يُبلَّغ ولا يُصحَّح: لا قصّ للإنشاء ولا إعادة توجيه للمسار.
# =============================================================================
import json
import math
import os

import acs_arch as ARCH
import acs_struct as STRUCT

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_mep.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
COMPILER_VERSION = SPEC["compiler_version"]
ELEMENT_TYPES = tuple(SPEC["element_types"])
MODEL_STATUS = tuple(SPEC["model_status"])
PROVENANCE = tuple(SPEC["provenance_values"])
VERIFIED_SOURCES = tuple(SPEC["verified_sources"])
SYSTEM_TYPES = tuple(SPEC["system_types"])
DISCIPLINE_OF = SPEC["system_disciplines"]
DISCIPLINES = tuple(SPEC["disciplines"])
MEDIA = tuple(SPEC["media"])
NODE_KINDS = tuple(SPEC["node_kinds"])
SEGMENT_KINDS = tuple(SPEC["segment_kinds"])
ROUTING_STATUSES = tuple(SPEC["routing_statuses"])
EQUIPMENT_TYPES = tuple(SPEC["equipment_types"])
TERMINAL_TYPES = tuple(SPEC["terminal_types"])
PORT_TYPES = tuple(SPEC["port_types"])
RISER_KINDS = tuple(SPEC["riser_kinds"])
PENETRATION_HOSTS = tuple(SPEC["penetration_host_types"])
REL_TYPES = tuple(SPEC["relationship_types"])
REL_STATUSES = tuple(SPEC["relationship_statuses"])
SEVERITIES = tuple(SPEC["issue_severities"])
ISSUE_CODES = SPEC["issue_codes"]
FALLBACKS = SPEC["display_fallbacks"]

_EPS = 1e-6
_TOL = 0.15          # تسامح هندسي عام (م) — للتلامس لا للحكم الهندسي

# محوّل نقاط المرحلة 1 → نهايات ممثَّلة. الإسناد يُنقل كما هو ولا يُرقّى أبداً.
_P1_TERMINAL = {"outlet": ("socket", "ELECTRICAL_POWER"),
                "switch": ("switch", "LIGHTING"),
                "network": ("data_outlet", "DATA_NETWORK"),
                "usb": ("socket", "ELECTRICAL_POWER"),
                "tv": ("tv_outlet", "LOW_CURRENT"),
                "ev": ("equipment_connection", "ELECTRICAL_POWER"),
                "light": ("light_fixture", "LIGHTING"),
                "spot": ("light_fixture", "LIGHTING"),
                "ptl": ("light_fixture", "LIGHTING"),
                "camera": ("cctv", "SECURITY"),
                "ac": ("equipment_connection", "HVAC_SUPPLY"),
                "vent": ("grille", "HVAC_EXHAUST"),
                "smoke": ("smoke_detector", "FIRE_ALARM"),
                "sprinkler": ("sprinkler_head", "SPRINKLER")}


def severity_of(code):
    return ISSUE_CODES.get(code, "WARNING")


def _num(v):
    """رقم حقيقي أو None. NaN/inf ليست أرقاماً ولا تمرّ بصمت."""
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
    return v is not None and not isinstance(v, bool) and _num(v) is None


def _src(v, default="unknown"):
    s = str(v).lower() if v is not None else default
    return s if s in PROVENANCE else "unknown"


def _fallback(value, key):
    """قيمة دلالية + احتياط عرض منفصل. الاحتياط ليس قيمة هندسية أبداً."""
    n = _num(value)
    if n is None:
        return {"value": None, "render_fallback": FALLBACKS[key],
                "source": "unknown", "render_source": "display_fallback"}
    return {"value": n, "render_fallback": FALLBACKS[key],
            "source": "imported", "render_source": "model"}


def _prop_map(props, source):
    """خصائص اختيارية مذكورة صراحةً فقط — كل واحدة بمصدرها."""
    out = {}
    if isinstance(props, dict):
        for k in sorted(props.keys()):
            out[str(k)] = {"value": props[k], "source": _src(source, "imported")}
    return out


def _raw(building):
    m = building.get("mep")
    return m if isinstance(m, dict) else {}


def _nid(bid, given, prefix, n):
    if given:
        s = str(given)
        if s.startswith(bid + "."):
            return s
        head = s.split(".")[0]
        if head.startswith("bld_") and head != bid:
            return s          # بادئة مبنى آخر تُترك ليكشفها التحقّق
        return "%s.mep.%s" % (bid, s)
    return "%s.mep.%s_%d" % (bid, prefix, n)


def _levels_index(building, bid):
    idx = {}
    for l in ARCH._levels(building, bid):
        idx[l["index"]] = l
        idx[str(l["id"])] = l
    return idx


def _level_of(levels_idx, ref):
    if ref is None or isinstance(ref, bool):
        return None
    if isinstance(ref, (int, float)):
        return levels_idx.get(int(ref))
    return levels_idx.get(str(ref))


def _space_index(arch):
    idx = {}
    for s in (arch or {}).get("spaces") or []:
        idx[s["id"]] = s
        if s.get("space_id"):
            idx.setdefault(s["space_id"], s)
    return idx


def _point3(v, default_y=None):
    """نقطة ثلاثية: {x,y,z} أو [x,y,z] أو [x,z]. الارتفاع الغائب يأخذ منسوب المستوى."""
    if isinstance(v, dict):
        x, y, z = _num(v.get("x")), _num(v.get("y")), _num(v.get("z"))
    elif isinstance(v, (list, tuple)) and len(v) >= 3:
        x, y, z = _num(v[0]), _num(v[1]), _num(v[2])
    elif isinstance(v, (list, tuple)) and len(v) == 2:
        x, y, z = _num(v[0]), None, _num(v[1])
    else:
        return None
    if x is None or z is None:
        return None
    return [x, default_y if y is None else y, z]


# ------------------------------------------------------------- الأنظمة --
def _systems(raw, bid, levels_idx):
    out = []
    for n, s in enumerate(raw.get("systems") or []):
        t = str(s.get("type") or "OTHER").upper()
        known = t in SYSTEM_TYPES
        med = str(s.get("medium") or "unknown").lower()
        med_known = med in MEDIA
        lv = [_level_of(levels_idx, r) for r in (s.get("serves_levels") or [])]
        out.append({
            "id": _nid(bid, s.get("id"), "sys", n), "type": "MEP_SYSTEM", "building_id": bid,
            "system_type": t if known else "OTHER", "declared_type": s.get("type"),
            "system_type_recognised": known,
            "discipline": DISCIPLINE_OF.get(t if known else "OTHER", "OTHER"),
            "name": s.get("name"),
            "medium": med if med_known else "unknown", "declared_medium": s.get("medium"),
            "medium_recognised": med_known,
            "serves_level_refs": list(s.get("serves_levels") or []),
            "serves_level_ids": [l["id"] for l in lv if l],
            "levels_resolved": all(l is not None for l in lv),
            "metadata": _prop_map(s.get("metadata"), s.get("source")),
            "status": str(s.get("status")).upper() if s.get("status") else None,
            "source": _src(s.get("source")),
            "note": "represented MEP system — no capacity, adequacy or compliance is implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# --------------------------------------------------------------- العقد --
def _nodes(raw, bid, levels_idx, space_idx, sys_ids):
    out = []
    for n, nd in enumerate(raw.get("nodes") or []):
        lvl = _level_of(levels_idx, nd.get("level"))
        kind = str(nd.get("kind") or "junction").lower()
        pos = nd.get("position") if isinstance(nd.get("position"), dict) else nd
        y = _num(pos.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        sid = nd.get("system_id")
        sp = nd.get("space") or nd.get("space_id")
        out.append({
            "id": _nid(bid, nd.get("id"), "node", n), "type": "MEP_NODE", "building_id": bid,
            "system_id": sid, "system_resolved": sid is None or _nid(bid, sid, "sys", 0) in sys_ids,
            "kind": kind if kind in NODE_KINDS else "other", "declared_kind": nd.get("kind"),
            "x": _num(pos.get("x")), "y": y, "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "y_source": ("imported" if _num(pos.get("y")) is not None else
                         ("architectural_level" if lvl is not None else "unknown")),
            "level_ref": nd.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or nd.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "source": _src(nd.get("source")),
            "note": "a node carries no capacity"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------- المقاطع --
def _size(sz, kind):
    """مقاس معلن فقط. لا نختار قطراً ولا مقطع مجرى من أجل الرسم."""
    if not isinstance(sz, dict):
        return None
    out = {"diameter_m": _num(sz.get("diameter_m") if sz.get("diameter_m") is not None
                              else sz.get("diameter")),
           "width_m": _num(sz.get("width_m") if sz.get("width_m") is not None else sz.get("width")),
           "height_m": _num(sz.get("height_m") if sz.get("height_m") is not None
                            else sz.get("height")),
           "source": _src(sz.get("source"), "imported")}
    if out["diameter_m"] is None and out["width_m"] is None and out["height_m"] is None:
        return None
    return out


def _render_size(size, kind):
    if size and size.get("diameter_m") is not None:
        d = size["diameter_m"]
        return {"w": d, "h": d, "source": "model"}
    if size and (size.get("width_m") is not None or size.get("height_m") is not None):
        w = size.get("width_m")
        h = size.get("height_m")
        if w is None:
            w = h
        if h is None:
            h = w
        return {"w": w, "h": h, "source": "model"}
    if kind == "duct":
        return {"w": FALLBACKS["duct_width_m"], "h": FALLBACKS["duct_height_m"],
                "source": "display_fallback"}
    if kind == "conduit":
        return {"w": FALLBACKS["conduit_diameter_m"], "h": FALLBACKS["conduit_diameter_m"],
                "source": "display_fallback"}
    if kind == "cable_tray":
        return {"w": FALLBACKS["cable_tray_width_m"], "h": FALLBACKS["cable_tray_height_m"],
                "source": "display_fallback"}
    return {"w": FALLBACKS["pipe_diameter_m"], "h": FALLBACKS["pipe_diameter_m"],
            "source": "display_fallback"}


def _polyline(v, default_y):
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    pts = []
    for p in v:
        q = _point3(p, default_y)
        if q is None:
            return None
        pts.append(q)
    return pts


def _segments(raw, bid, levels_idx, node_idx, sys_ids):
    out = []
    for n, s in enumerate(raw.get("segments") or []):
        lvl = _level_of(levels_idx, s.get("level"))
        base_y = lvl["elevation_m"] if lvl else None
        kind = str(s.get("kind") or "other").lower()
        ends = []
        for key in ("from_node", "to_node"):
            ref = s.get(key) if s.get(key) is not None else s.get(key.split("_")[0])
            node = node_idx.get(str(ref)) or node_idx.get(_nid(bid, ref, "node", 0)) if ref else None
            if node is not None:
                ends.append({"ref": ref, "node_id": node["id"],
                             "x": node["x"], "y": node["y"], "z": node["z"],
                             "basis": "mep_node"})
            else:
                ends.append({"ref": ref, "node_id": None, "x": None, "y": None, "z": None,
                             "basis": "unknown_node" if ref is not None else "unresolved"})
        poly = _polyline(s.get("polyline") or s.get("geometry"), base_y)
        if poly is None and all(e["x"] is not None for e in ends):
            # لا نختلق مساراً: نقطتا الطرف فقط، ويبقى الوصف صادقاً بأنه غير موجَّه
            poly = None
        length = None
        if poly:
            length = 0.0
            for a, b in zip(poly, poly[1:]):
                ay = a[1] if a[1] is not None else 0.0
                by = b[1] if b[1] is not None else 0.0
                length += math.sqrt((b[0] - a[0]) ** 2 + (by - ay) ** 2 + (b[2] - a[2]) ** 2)
        declared_routing = str(s.get("routing_status") or "").upper()
        if declared_routing in ROUTING_STATUSES:
            routing = declared_routing
        elif poly:
            routing = "ROUTED"
        elif any(e["basis"] == "unknown_node" for e in ends):
            routing = "UNRESOLVED"
        else:
            routing = "UNROUTED"
        size = _size(s.get("size"), kind)
        sid = s.get("system_id")
        out.append({
            "id": _nid(bid, s.get("id"), "seg", n), "type": "MEP_SEGMENT", "building_id": bid,
            "system_id": sid, "system_resolved": sid is None or _nid(bid, sid, "sys", 0) in sys_ids,
            "kind": kind if kind in SEGMENT_KINDS else "other", "declared_kind": s.get("kind"),
            "kind_recognised": kind in SEGMENT_KINDS,
            "level_ref": s.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or s.get("level") is None,
            "start": ends[0], "end": ends[1],
            "polyline": poly, "length_m": length,
            "routing_status": routing,
            "size": size, "render_size": _render_size(size, kind),
            "material": s.get("material"),
            "source": _src(s.get("source")),
            "note": "represented route — no sizing, flow, pressure or capacity is implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ المعدّات --
def _ports(v, source):
    out = []
    for p in (v or []):
        if isinstance(p, dict):
            t = str(p.get("type") or "").lower()
            out.append({"id": p.get("id"), "port_type": t,
                        "port_type_recognised": t in PORT_TYPES,
                        "source": _src(p.get("source") or source)})
        elif isinstance(p, str):
            out.append({"id": None, "port_type": p.lower(),
                        "port_type_recognised": p.lower() in PORT_TYPES,
                        "source": _src(source)})
    return out


def _dims(d):
    if not isinstance(d, dict):
        return None
    out = {"w_m": _num(d.get("w") if d.get("w") is not None else d.get("w_m")),
           "d_m": _num(d.get("d") if d.get("d") is not None else d.get("d_m")),
           "h_m": _num(d.get("h") if d.get("h") is not None else d.get("h_m"))}
    if out["w_m"] is None and out["d_m"] is None and out["h_m"] is None:
        return None
    return out


def _equipment(raw, bid, levels_idx, space_idx, sys_ids):
    out = []
    for n, e in enumerate(raw.get("equipment") or []):
        lvl = _level_of(levels_idx, e.get("level"))
        t = str(e.get("type") or "other").lower()
        pos = e.get("position") if isinstance(e.get("position"), dict) else e
        y = _num(pos.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        sp = e.get("space") or e.get("space_id")
        sid = e.get("system_id")
        dims = _dims(e.get("dimensions"))
        out.append({
            "id": _nid(bid, e.get("id"), "eq", n), "type": "MEP_EQUIPMENT", "building_id": bid,
            "system_id": sid, "system_resolved": sid is None or _nid(bid, sid, "sys", 0) in sys_ids,
            "equipment_type": t if t in EQUIPMENT_TYPES else "other",
            "declared_type": e.get("type"), "equipment_type_recognised": t in EQUIPMENT_TYPES,
            "x": _num(pos.get("x")), "y": y, "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "level_ref": e.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or e.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "dimensions": dims,
            "render_dimensions": ({"w": dims["w_m"] if dims and dims["w_m"] is not None
                                   else FALLBACKS["equipment_w_m"],
                                   "d": dims["d_m"] if dims and dims["d_m"] is not None
                                   else FALLBACKS["equipment_d_m"],
                                   "h": dims["h_m"] if dims and dims["h_m"] is not None
                                   else FALLBACKS["equipment_h_m"],
                                   "source": ("model" if dims and None not in
                                              (dims["w_m"], dims["d_m"], dims["h_m"])
                                              else "display_fallback")}),
            # لا قدرة ولا جهد ولا تيار ولا تدفّق يُختلق: ما لم يُذكر يبقى غائباً
            "properties": _prop_map(e.get("properties"), e.get("source")),
            "ports": _ports(e.get("ports"), e.get("source")),
            "connections": list(e.get("connections") or []),
            "source": _src(e.get("source")),
            "note": "represented equipment — no rating, capacity or duty is implied"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ النهايات --
def _terminals(raw, bid, levels_idx, space_idx, sys_ids):
    out = []
    for n, t in enumerate(raw.get("terminals") or []):
        lvl = _level_of(levels_idx, t.get("level"))
        tt = str(t.get("type") or "other").lower()
        pos = t.get("position") if isinstance(t.get("position"), dict) else t
        y = _num(pos.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        sp = t.get("space") or t.get("space_id")
        sid = t.get("system_id")
        out.append({
            "id": _nid(bid, t.get("id"), "term", n), "type": "MEP_TERMINAL", "building_id": bid,
            "system_id": sid, "system_resolved": sid is None or _nid(bid, sid, "sys", 0) in sys_ids,
            "terminal_type": tt if tt in TERMINAL_TYPES else "other",
            "declared_type": t.get("type"), "terminal_type_recognised": tt in TERMINAL_TYPES,
            "x": _num(pos.get("x")), "y": y, "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "level_ref": t.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or t.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "node_ref": t.get("node"), "circuit_ref": t.get("circuit"),
            "properties": _prop_map(t.get("properties"), t.get("source")),
            "adapted": False, "origin": "model",
            "source": _src(t.get("source")),
            "note": "a represented terminal in a space is not a claim of adequate service"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def adapt_phase1_terminals(building, bid="bld_0", arch=None):
    """يمثّل نقاط المرحلة 1 (إنارة/مقابس/مكيّف/دخان) كنهايات ممثَّلة.
    لا يُنشئ عنصراً دلالياً مكرّراً: كل نهاية تشير إلى نقطتها الأصلية، وإسنادها
    ينتقل كما هو. نقطة أضافها النظام تبقى system_default ولا تصير أبداً
    مطلوبة بقاعدة."""
    if arch is None:
        try:
            arch = ARCH.compile_architecture(building, bid)
        except Exception:
            arch = None
    out = []
    levels = ARCH._levels(building, bid)
    for lvl in levels:
        for sid, room, _i in ARCH._rooms_of(building, lvl["template"], bid):
            rc = ARCH._rect(room)
            for pi, p in enumerate(room.get("points") or []):
                kind = str(p.get("type") or "").lower()
                mapped = _P1_TERMINAL.get(kind)
                if mapped is None:
                    continue
                tt, systype = mapped
                px = _num(p.get("x"))
                pz = _num(p.get("z"))
                out.append({
                    "id": "%s.mep.p1_%s_%d@%s" % (bid, sid, pi, lvl["index"]),
                    "type": "MEP_TERMINAL", "building_id": bid,
                    "system_id": None, "system_resolved": True,
                    "suggested_system_type": systype,
                    "terminal_type": tt, "declared_type": p.get("type"),
                    "terminal_type_recognised": True,
                    "x": (rc[0] + px) if (rc and px is not None) else None,
                    "y": lvl["elevation_m"],
                    "z": (rc[1] + pz) if (rc and pz is not None) else None,
                    "raw_x": p.get("x"), "raw_z": p.get("z"),
                    "level_ref": lvl["index"], "level_id": lvl["id"],
                    "level_index": lvl["index"], "level_resolved": True,
                    "space_ref": sid, "space_id": "%s@%s" % (sid, lvl["index"]),
                    "space_resolved": True,
                    "node_ref": None, "circuit_ref": None,
                    "properties": {},
                    "adapted": True, "origin": "phase1_point",
                    "origin_ref": "%s.point_%d" % (sid, pi),
                    # الإسناد الأصلي ينتقل كما هو ولا يُرقّى إطلاقاً
                    "original_source": _src(p.get("source"), "system_default"),
                    "source": "phase1_adapter",
                    "note": "adapted from an existing Phase 1 point; the original provenance is "
                            "carried through unchanged and is never raised"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# -------------------------------------------------------------- المناور --
def _risers(raw, bid, levels_idx, arch, sys_ids):
    out = []
    cores = {c["id"]: c for c in (arch or {}).get("cores") or []}
    for n, r in enumerate(raw.get("risers") or []):
        refs = list(r.get("levels") or [])
        lv = [_level_of(levels_idx, x) for x in refs]
        kind = str(r.get("kind") or "other").lower()
        pos = r.get("position") if isinstance(r.get("position"), dict) else r
        core_id = r.get("arch_core_id")
        core = cores.get(core_id) if core_id else None
        sids = list(r.get("system_ids") or [])
        out.append({
            "id": _nid(bid, r.get("id"), "riser", n), "type": "MEP_RISER", "building_id": bid,
            "riser_kind": kind if kind in RISER_KINDS else "other", "declared_kind": r.get("kind"),
            "x": _num(pos.get("x")), "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "w_m": _fallback(r.get("w_m"), "riser_w_m"),
            "d_m": _fallback(r.get("d_m"), "riser_d_m"),
            "level_refs": refs, "level_ids": [l["id"] for l in lv if l],
            "level_indexes": sorted(l["index"] for l in lv if l),
            "levels_resolved": all(l is not None for l in lv) and len(refs) > 0,
            "system_ids": sids,
            "unresolved_system_ids": [s for s in sids if _nid(bid, s, "sys", 0) not in sys_ids],
            # مناور المعماري ليست مناور MEP تلقائياً: الربط يحتاج دليلاً معلناً
            "arch_core_id": core_id,
            "arch_core_resolved": core is not None if core_id else None,
            "arch_core_link_source": _src(r.get("arch_core_link_source")) if core_id else "unknown",
            "source": _src(r.get("source")),
            "note": "an architectural shaft or core is not an MEP riser without explicit evidence"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ---------------------------------------------------------- الاختراقات --
def _penetrations(raw, bid, levels_idx, seg_ids, arch, struct):
    hosts = set()
    for key in ("walls", "slabs"):
        for e in (arch or {}).get(key) or []:
            hosts.add(e["id"])
    for key in ("beams", "columns", "slabs", "walls"):
        for e in (struct or {}).get(key) or []:
            hosts.add(e["id"])
    out = []
    for n, p in enumerate(raw.get("penetrations") or []):
        lvl = _level_of(levels_idx, p.get("level"))
        ht = str(p.get("host_type") or "OTHER").upper()
        seg = p.get("segment_id")
        host = p.get("host_id")
        out.append({
            "id": _nid(bid, p.get("id"), "pen", n), "type": "MEP_PENETRATION", "building_id": bid,
            "segment_id": seg,
            "segment_resolved": seg is not None and _nid(bid, seg, "seg", 0) in seg_ids,
            "host_type": ht if ht in PENETRATION_HOSTS else "OTHER",
            "declared_host_type": p.get("host_type"),
            "host_id": host, "host_resolved": host in hosts if host else False,
            "x": _num(p.get("x")), "z": _num(p.get("z")),
            "level_ref": p.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "size": _size(p.get("size"), "pipe"),
            "source": _src(p.get("source")),
            "note": "a represented opening only — no fire stopping, sleeve or reinforcement "
                    "requirement is inferred"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ العلاقات --
def _relationships(bid, systems, nodes, segments, equipment, terminals, risers, pens,
                   arch, raw, issues):
    rels = []
    seq = [0]

    def add(rtype, frm, to, status, basis, meta=None):
        seq[0] += 1
        e = {"id": "%s.mep.rel_%d" % (bid, seq[0]), "type": rtype, "from": frm, "to": to,
             "source": "model_declaration" if status == "confirmed" else "geometry_inference",
             "status": status, "basis": basis,
             "note": "model topology and factual location only — no service adequacy is claimed"}
        if meta:
            e["meta"] = meta
        rels.append(e)
        return e

    node_ids = {n["id"] for n in nodes}
    eq_ids = {e["id"] for e in equipment}
    for s in segments:
        for end in (s["start"], s["end"]):
            if end["node_id"]:
                add("SEGMENT_CONNECTS", s["id"], end["node_id"], "confirmed",
                    "segment endpoint references a declared MEP node")
            else:
                add("SEGMENT_CONNECTS", s["id"], None, "unresolved",
                    "segment endpoint could not be resolved", {"ref": end["ref"]})
        if s["routing_status"] == "UNROUTED":
            add("SEGMENT_CONNECTS", s["id"], None, "unresolved",
                "endpoints exist but no route geometry was supplied — no path is fabricated",
                {"routing_status": "UNROUTED"})
    for e in equipment:
        for ref in e["connections"]:
            tgt = _nid(bid, ref, "node", 0)
            known = tgt in node_ids or tgt in eq_ids
            add("EQUIPMENT_CONNECTED_TO", e["id"], tgt if known else None,
                "confirmed" if known else "unresolved",
                "declared by the model" if known else "declared connection was not found")
    for t in terminals:
        if t.get("node_ref"):
            tgt = _nid(bid, t["node_ref"], "node", 0)
            known = tgt in node_ids
            add("TERMINAL_CONNECTED_TO", t["id"], tgt if known else None,
                "confirmed" if known else "unresolved",
                "declared by the model" if known else "declared node was not found")
        if t.get("circuit_ref"):
            # الدائرة تُذكر ولا تُصمَّم: لا تجميع تلقائي لمقابس في دوائر
            add("TERMINAL_ON_CIRCUIT", t["id"], str(t["circuit_ref"]), "confirmed",
                "declared by the model", {"disclaimer": "circuits are never grouped automatically"})
    for c in (raw.get("circuits") or []):
        pref = c.get("panel")
        if pref:
            add("PANEL_FEEDS", _nid(bid, pref, "eq", 0), str(c.get("id")), "confirmed",
                "declared by the model")
        for ref in (c.get("terminals") or []):
            add("CIRCUIT_FEEDS", str(c.get("id")), _nid(bid, ref, "term", 0), "confirmed",
                "declared by the model")
    for r in risers:
        if len(r["level_indexes"]) > 1:
            add("RISER_CONNECTS_LEVELS", r["id"], None, "confirmed", "declared by the model",
                {"levels": list(r["level_indexes"])})
        if r.get("arch_core_id"):
            add("RISER_IN_SHAFT", r["id"], r["arch_core_id"],
                "confirmed" if r.get("arch_core_resolved") else "unresolved",
                "declared association with an architectural core",
                {"link_source": r["arch_core_link_source"]})
    for p in pens:
        add("PENETRATION_THROUGH", p["id"], p.get("host_id"),
            "confirmed" if p["host_resolved"] else "unresolved",
            "declared by the model",
            {"segment_id": p.get("segment_id"), "host_type": p["host_type"]})

    # موقع النهاية داخل فراغ معماري — واقعة مكانية، لا كفاية خدمة
    spaces = {s["id"]: s for s in (arch or {}).get("spaces") or []}
    sys_by_id = {s["id"]: s for s in systems}
    seen = set()
    for t in terminals:
        sp = t.get("space_id")
        if not sp and t.get("x") is not None and t.get("level_index") is not None:
            for s in (arch or {}).get("spaces") or []:
                rc = s.get("rect")
                if rc and s.get("level_index") == t["level_index"] and \
                   rc[0] - _EPS <= t["x"] <= rc[0] + rc[2] + _EPS and \
                   rc[1] - _EPS <= t["z"] <= rc[1] + rc[3] + _EPS:
                    sp = s["id"]
                    break
        if not sp or sp not in spaces:
            continue
        add("SYSTEM_HAS_TERMINAL_IN", t["id"], sp, "confirmed",
            "the terminal lies inside this architectural space",
            {"disclaimer": "a represented terminal is not a claim of adequate service"})
        sysid = t.get("system_id")
        key = (str(sysid), sp)
        if sysid and _nid(bid, sysid, "sys", 0) in sys_by_id and key not in seen:
            seen.add(key)
            add("SYSTEM_SERVES_SPACE", _nid(bid, sysid, "sys", 0), sp, "confirmed",
                "the system has a represented terminal in this space",
                {"disclaimer": "representation only — no adequacy of airflow, water, light or "
                               "power is claimed"})
    return rels


# --------------------------------------------------- التعارض والاختراق --
def _seg2d(p, q):
    return (p[0], p[2], q[0], q[2])


def _cross(a, b):
    """تقاطع مقطعين ثنائيي الأبعاد تقاطعاً حقيقياً (لا مجرّد تلامس طرف)."""
    x1, z1, x2, z2 = a
    x3, z3, x4, z4 = b
    d = (x2 - x1) * (z4 - z3) - (z2 - z1) * (x4 - x3)
    if abs(d) < 1e-12:
        return False
    t = ((x3 - x1) * (z4 - z3) - (z3 - z1) * (x4 - x3)) / d
    u = ((x3 - x1) * (z2 - z1) - (z3 - z1) * (x2 - x1)) / d
    return 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9


def _interference(bid, segments, equipment, terminals, risers, pens, arch, struct, building,
                  issues):
    """تعارضات هندسية واضحة فقط — ليست كشف تصادم BIM ولا حكم مطابقة."""
    pen_hosts = {(str(p.get("segment_id")), str(p.get("host_id"))) for p in pens}
    pen_any = {str(p.get("segment_id")) for p in pens}

    if arch:
        walls = arch.get("walls") or []
        voids = arch.get("voids") or []
        for s in segments:
            if not s["polyline"]:
                continue
            for a, b in zip(s["polyline"], s["polyline"][1:]):
                seg = _seg2d(a, b)
                for w in walls:
                    if s["level_index"] is not None and w["level_index"] != s["level_index"]:
                        continue
                    wl = (w["start"]["x"], w["start"]["z"], w["end"]["x"], w["end"]["z"])
                    if _cross(seg, wl):
                        raw_id = str(s["id"]).split(".mep.")[-1]
                        if (str(s["id"]), w["id"]) in pen_hosts or (raw_id, w["id"]) in pen_hosts:
                            continue
                        issues.append({"code": "SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION",
                                       "subject": s["id"], "other": w["id"],
                                       "detail": "no penetration is represented at this crossing; "
                                                 "nothing is cut and nothing is rerouted"})
                # اختراق بلاطة: المقطع يعبر منسوب مستوى رأسياً
                ay = a[1] if a[1] is not None else None
                by = b[1] if b[1] is not None else None
                if ay is not None and by is not None and abs(by - ay) > _TOL:
                    lo, hi = min(ay, by), max(ay, by)
                    for sl in arch.get("slabs") or []:
                        el = sl.get("elevation_m")
                        if el is None or not (lo + _EPS < el < hi - _EPS):
                            continue
                        raw_id = str(s["id"]).split(".mep.")[-1]
                        if (str(s["id"]), sl["id"]) in pen_hosts or (raw_id, sl["id"]) in pen_hosts:
                            continue
                        issues.append({"code": "SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION",
                                       "subject": s["id"], "other": sl["id"],
                                       "detail": "no penetration is represented at this level"})
                for v in voids:
                    r = v["rect"]
                    for pt in (a, b):
                        if r[0] <= pt[0] <= r[0] + r[2] and r[1] <= pt[2] <= r[1] + r[3]:
                            issues.append({"code": "MEP_ELEMENT_IN_FLOOR_OPENING",
                                           "subject": s["id"], "other": v["id"]})
                            break
        # عنصر خارج الفراغ المسنَد إليه
        spaces = {s["id"]: s for s in arch.get("spaces") or []}
        for e in equipment + terminals:
            sp = spaces.get(e.get("space_id"))
            if not sp or not sp.get("rect") or e.get("x") is None:
                continue
            rc = sp["rect"]
            if not (rc[0] - _TOL <= e["x"] <= rc[0] + rc[2] + _TOL and
                    rc[1] - _TOL <= e["z"] <= rc[1] + rc[3] + _TOL):
                issues.append({"code": ("EQUIPMENT_OUTSIDE_SPACE" if e["type"] == "MEP_EQUIPMENT"
                                        else "TERMINAL_OUTSIDE_SPACE"),
                               "subject": e["id"], "other": sp["id"]})
        # مسار خارج مسطح المبنى
        rects = [s["rect"] for s in arch.get("spaces") or [] if s.get("rect")]
        if rects:
            bb = [min(r[0] for r in rects), min(r[1] for r in rects),
                  max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)]
            for s in segments:
                if not s["polyline"]:
                    continue
                if any(not (bb[0] - 1.0 <= p[0] <= bb[2] + 1.0 and
                            bb[1] - 1.0 <= p[2] <= bb[3] + 1.0) for p in s["polyline"]):
                    issues.append({"code": "ROUTE_OUTSIDE_BUILDING", "subject": s["id"],
                                   "footprint": bb})
        # منور خارج النواة المعمارية التي يشير إليها
        cores = {c["id"]: c for c in arch.get("cores") or []}
        for r in risers:
            c = cores.get(r.get("arch_core_id"))
            if not c or r.get("x") is None:
                continue
            fw = c["footprint_w_m"]["value"] or c["footprint_w_m"]["render_fallback"]
            fd = c["footprint_d_m"]["value"] or c["footprint_d_m"]["render_fallback"]
            if abs(r["x"] - c["x"]) > fw / 2.0 + _TOL or abs(r["z"] - c["z"]) > fd / 2.0 + _TOL:
                issues.append({"code": "RISER_OUTSIDE_SHAFT", "subject": r["id"],
                               "other": c["id"]})

    if struct:
        for s in segments:
            if not s["polyline"]:
                continue
            for a, b in zip(s["polyline"], s["polyline"][1:]):
                seg = _seg2d(a, b)
                for bm in struct.get("beams") or []:
                    if bm["start"]["x"] is None or bm["end"]["x"] is None:
                        continue
                    if s["level_index"] is not None and bm["level_index"] != s["level_index"]:
                        continue
                    bl = (bm["start"]["x"], bm["start"]["z"], bm["end"]["x"], bm["end"]["z"])
                    if _cross(seg, bl):
                        issues.append({"code": "SEGMENT_CROSSES_STRUCTURAL_BEAM",
                                       "subject": s["id"], "other": bm["id"],
                                       "detail": "reported only — the structural member is not "
                                                 "cut and the route is not redesigned"})
                for c in struct.get("columns") or []:
                    if c["x"] is None:
                        continue
                    rs = c["render_section"]
                    known = rs["source"] == "model"
                    hw = rs["w"] / 2.0 if known else _TOL
                    hd = rs["d"] / 2.0 if known else _TOL
                    box = [c["x"] - hw, c["z"] - hd, c["x"] + hw, c["z"] + hd]
                    if _seg_hits_box(a, b, box):
                        issues.append({"code": "SEGMENT_CROSSES_STRUCTURAL_COLUMN",
                                       "subject": s["id"], "other": c["id"],
                                       "basis": ("column_section_footprint" if known
                                                 else "column_axis_proximity")})
                ay = a[1] if a[1] is not None else None
                by = b[1] if b[1] is not None else None
                if ay is not None and by is not None and abs(by - ay) > _TOL:
                    lo, hi = min(ay, by), max(ay, by)
                    for sl in struct.get("slabs") or []:
                        el = sl.get("elevation_m")
                        if el is None or not (lo + _EPS < el < hi - _EPS):
                            continue
                        if str(s["id"]) in pen_any:
                            continue
                        issues.append({"code": "SEGMENT_CROSSES_STRUCTURAL_SLAB",
                                       "subject": s["id"], "other": sl["id"]})


def _seg_hits_box(a, b, box):
    """هل يمرّ مقطع ثنائي الأبعاد داخل مستطيل؟ فحص بسيط بالعيّنات والأطراف."""
    if (box[0] <= a[0] <= box[2] and box[1] <= a[2] <= box[3]) or \
       (box[0] <= b[0] <= box[2] and box[1] <= b[2] <= box[3]):
        return True
    edges = [(box[0], box[1], box[2], box[1]), (box[2], box[1], box[2], box[3]),
             (box[2], box[3], box[0], box[3]), (box[0], box[3], box[0], box[1])]
    seg = (a[0], a[2], b[0], b[2])
    return any(_cross(seg, e) for e in edges)


# ------------------------------------------------------------- التصريف --
def compile_mep(building, building_id="bld_0", position=None, rotation_deg=0.0,
                arch=None, struct=None, adapt_phase1=True):
    """يبني النموذج الكهروميكانيكي من بيانات مذكورة فقط. حتمي ولا يعدّل النموذج."""
    bid = building_id
    raw = _raw(building)
    if arch is None:
        try:
            arch = ARCH.compile_architecture(building, bid, position, rotation_deg)
        except Exception:
            arch = None
    if struct is None:
        try:
            struct = STRUCT.compile_structure(building, bid, position, rotation_deg, arch)
        except Exception:
            struct = None
    levels_idx = _levels_index(building, bid)
    space_idx = _space_index(arch)

    issues = []
    known_keys = {"status", "synthetic", "meta", "systems", "nodes", "segments", "equipment",
                  "terminals", "risers", "penetrations", "circuits",
                  "layer_visibility", "visible_layers"}
    for k in sorted(raw.keys()):
        if k not in known_keys:
            issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": k,
                           "detail": "this collection is not part of the MEP schema and was "
                                     "NOT interpreted"})

    systems = _systems(raw, bid, levels_idx)
    sys_ids = {s["id"] for s in systems}
    nodes = _nodes(raw, bid, levels_idx, space_idx, sys_ids)
    node_idx = {n["id"]: n for n in nodes}
    segments = _segments(raw, bid, levels_idx, node_idx, sys_ids)
    seg_ids = {s["id"] for s in segments}
    equipment = _equipment(raw, bid, levels_idx, space_idx, sys_ids)
    terminals = _terminals(raw, bid, levels_idx, space_idx, sys_ids)
    risers = _risers(raw, bid, levels_idx, arch, sys_ids)
    pens = _penetrations(raw, bid, levels_idx, seg_ids, arch, struct)
    adapted = adapt_phase1_terminals(building, bid, arch) if adapt_phase1 else []

    counted = (len(systems) + len(nodes) + len(segments) + len(equipment) + len(terminals)
               + len(risers) + len(pens))
    declared = str(raw.get("status") or "").upper()
    if declared in MODEL_STATUS:
        status = declared
    elif counted == 0:
        status = "NOT_DEFINED"
    else:
        verified = all(e["source"] in VERIFIED_SOURCES
                       for e in systems + nodes + segments + equipment + terminals + risers)
        status = "REPRESENTED" if verified else "PARTIAL"

    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "building_id": bid,
           "status": status,
           "status_basis": ("declared_by_model" if declared in MODEL_STATUS
                            else ("no MEP element is present" if counted == 0
                                  else "derived from element provenance")),
           "synthetic": raw.get("synthetic") is True, "regulatory": False,
           "transform": {"position": position or {"x": 0.0, "z": 0.0},
                         "rotation_deg": float(rotation_deg or 0.0),
                         "applied": "local coordinates; world transform is applied on read"},
           "levels": [{"id": l["id"], "index": l["index"], "elevation_m": l["elevation_m"]}
                      for l in ARCH._levels(building, bid)],
           "systems": systems, "nodes": nodes, "segments": segments, "equipment": equipment,
           "terminals": terminals, "adapted_terminals": adapted, "risers": risers,
           "penetrations": pens, "relationships": [], "issues": [],
           "meta": {"note": SPEC["note"], "fire_note": SPEC["fire_note"],
                    "elements": counted, "adapted_terminals": len(adapted),
                    "levels_source": "architectural level table",
                    "spaces_source": "architectural space table",
                    "service_adequacy": "not evaluated — representation only",
                    "navigation_impact": SPEC["navigation_note"]}}

    out["relationships"] = _relationships(bid, systems, nodes, segments, equipment,
                                          terminals + adapted, risers, pens, arch, raw, issues)
    _interference(bid, segments, equipment, terminals, risers, pens, arch, struct, building, issues)
    issues.extend(validate_mep(out))
    for i in issues:
        i["severity"] = severity_of(i["code"])
    issues.sort(key=lambda i: (SEVERITIES.index(i["severity"]) * -1, str(i["code"]),
                               str(i.get("subject"))))
    out["issues"] = issues
    return out


# ------------------------------------------------------------- التحقّق --
def validate_mep(mep):
    """فحوص سلامة نموذج — ليست فحوص كود MEP إطلاقاً."""
    issues = []
    bid = mep.get("building_id")
    groups = ("systems", "nodes", "segments", "equipment", "terminals", "risers", "penetrations")
    seen = {}
    for key in groups:
        for e in mep.get(key) or []:
            if e["id"] in seen:
                issues.append({"code": "DUPLICATE_ELEMENT_ID", "subject": e["id"],
                               "other": seen[e["id"]]})
            seen[e["id"]] = key
            if e.get("type") not in ELEMENT_TYPES:
                issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": e["id"],
                               "declared": e.get("type")})
            if bid and not str(e["id"]).startswith(str(bid) + "."):
                issues.append({"code": "CROSS_BUILDING_REF", "subject": e["id"]})

    for s in mep.get("systems") or []:
        if not s["system_type_recognised"]:
            issues.append({"code": "UNKNOWN_SYSTEM_TYPE", "subject": s["id"],
                           "declared": s.get("declared_type")})
        if not s["medium_recognised"]:
            issues.append({"code": "UNKNOWN_MEDIUM", "subject": s["id"],
                           "declared": s.get("declared_medium")})
        if not s["levels_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": s["id"],
                           "refs": s.get("serves_level_refs")})
    for n in mep.get("nodes") or []:
        if _is_bad_number(n.get("raw_x")) or _is_bad_number(n.get("raw_z")) or \
           n["x"] is None or n["z"] is None:
            issues.append({"code": "NAN_COORDINATE", "subject": n["id"]})
        if not n["system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": n["id"],
                           "ref": n.get("system_id")})
        if not n["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": n["id"],
                           "ref": n.get("level_ref")})
        if not n["space_resolved"]:
            issues.append({"code": "INVALID_SPACE_REF", "subject": n["id"],
                           "ref": n.get("space_ref")})
    used_nodes = set()
    for s in mep.get("segments") or []:
        for end in (s["start"], s["end"]):
            if end["node_id"]:
                used_nodes.add(end["node_id"])
            elif end["basis"] == "unknown_node":
                issues.append({"code": "INVALID_NODE_REF", "subject": s["id"], "ref": end["ref"]})
                issues.append({"code": "SEGMENT_ENDPOINT_UNRESOLVED", "subject": s["id"],
                               "ref": end["ref"]})
            else:
                issues.append({"code": "SEGMENT_ENDPOINT_UNRESOLVED", "subject": s["id"],
                               "ref": end["ref"]})
        if not s["system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": s["id"],
                           "ref": s.get("system_id")})
        if not s["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": s["id"],
                           "ref": s.get("level_ref")})
        if not s["kind_recognised"]:
            issues.append({"code": "UNKNOWN_SEGMENT_KIND", "subject": s["id"],
                           "declared": s.get("declared_kind")})
        if s["length_m"] is not None and s["length_m"] <= _EPS:
            issues.append({"code": "SEGMENT_ZERO_LENGTH", "subject": s["id"]})
        if s["routing_status"] == "UNROUTED":
            issues.append({"code": "SEGMENT_UNROUTED", "subject": s["id"],
                           "detail": "endpoints exist but no route geometry was supplied; "
                                     "no path is fabricated"})
        if s["size"] is None:
            issues.append({"code": "SIZE_UNKNOWN", "subject": s["id"]})
        else:
            for f in ("diameter_m", "width_m", "height_m"):
                if s["size"].get(f) is not None and s["size"][f] <= 0:
                    issues.append({"code": "NEGATIVE_DIMENSION", "subject": s["id"], "field": f})
    for n in mep.get("nodes") or []:
        if n["id"] not in used_nodes and n["kind"] not in ("terminal", "equipment_connection"):
            issues.append({"code": "ORPHAN_NODE", "subject": n["id"],
                           "detail": "no segment references this node"})
    node_ids = {n["id"] for n in mep.get("nodes") or []}
    for e in mep.get("equipment") or []:
        if _is_bad_number(e.get("raw_x")) or _is_bad_number(e.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": e["id"]})
        if not e["system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": e["id"],
                           "ref": e.get("system_id")})
        if not e["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": e["id"],
                           "ref": e.get("level_ref")})
        if not e["space_resolved"]:
            issues.append({"code": "INVALID_SPACE_REF", "subject": e["id"],
                           "ref": e.get("space_ref")})
        if not e["equipment_type_recognised"]:
            issues.append({"code": "UNKNOWN_EQUIPMENT_TYPE", "subject": e["id"],
                           "declared": e.get("declared_type")})
        if e["dimensions"]:
            for f in ("w_m", "d_m", "h_m"):
                if e["dimensions"].get(f) is not None and e["dimensions"][f] <= 0:
                    issues.append({"code": "NEGATIVE_DIMENSION", "subject": e["id"], "field": f})
        for p in e["ports"]:
            if not p["port_type_recognised"]:
                issues.append({"code": "INVALID_PORT_TYPE", "subject": e["id"],
                               "declared": p["port_type"]})
        for ref in e["connections"]:
            if _nid(bid, ref, "node", 0) not in node_ids and \
               _nid(bid, ref, "eq", 0) not in {x["id"] for x in mep.get("equipment") or []}:
                issues.append({"code": "INVALID_EQUIPMENT_REF", "subject": e["id"], "ref": ref})
    for t in mep.get("terminals") or []:
        if _is_bad_number(t.get("raw_x")) or _is_bad_number(t.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": t["id"]})
        if not t["system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": t["id"],
                           "ref": t.get("system_id")})
        if not t["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": t["id"],
                           "ref": t.get("level_ref")})
        if not t["space_resolved"]:
            issues.append({"code": "INVALID_SPACE_REF", "subject": t["id"],
                           "ref": t.get("space_ref")})
        if not t["terminal_type_recognised"]:
            issues.append({"code": "UNKNOWN_TERMINAL_TYPE", "subject": t["id"],
                           "declared": t.get("declared_type")})
        if t.get("system_id") is None and t.get("node_ref") is None:
            issues.append({"code": "ORPHAN_TERMINAL", "subject": t["id"],
                           "detail": "the terminal names neither a system nor a node"})
    for r in mep.get("risers") or []:
        if not r["levels_resolved"]:
            issues.append({"code": "RISER_LEVELS_UNRESOLVED", "subject": r["id"],
                           "refs": r.get("level_refs")})
        for s in r["unresolved_system_ids"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": r["id"], "ref": s})
        if _is_bad_number(r.get("raw_x")) or _is_bad_number(r.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": r["id"]})
    for p in mep.get("penetrations") or []:
        if not p["segment_resolved"]:
            issues.append({"code": "PENETRATION_SEGMENT_UNRESOLVED", "subject": p["id"],
                           "ref": p.get("segment_id")})
        if not p["host_resolved"]:
            issues.append({"code": "PENETRATION_HOST_UNRESOLVED", "subject": p["id"],
                           "ref": p.get("host_id")})
    return issues


# -------------------------------------------------------- بيانات الرسم --
_DISC_TAG = {d: d for d in DISCIPLINES}


def _discipline_of(mep, system_id, fallback="OTHER"):
    for s in mep.get("systems") or []:
        if s["id"] == system_id or s["id"] == _nid(mep.get("building_id"), system_id, "sys", 0):
            return s["discipline"]
    return fallback


def render_items(mep):
    """هندسة عرض فقط. كل عنصر يعلن هل أبعاده من النموذج أم احتياط عرض."""
    items = []
    for s in mep.get("segments") or []:
        if not s["polyline"] or len(s["polyline"]) < 2:
            continue
        disc = _discipline_of(mep, s.get("system_id"))
        rs = s["render_size"]
        for i, (a, b) in enumerate(zip(s["polyline"], s["polyline"][1:])):
            ay = a[1] if a[1] is not None else 0.0
            by = b[1] if b[1] is not None else 0.0
            dx, dy, dz = b[0] - a[0], by - ay, b[2] - a[2]
            ln = math.sqrt(dx * dx + dy * dy + dz * dz)
            if ln <= _EPS:
                continue
            items.append({"name": "MEP|%s|%s|%d" % (_DISC_TAG.get(disc, "OTHER"), s["id"], i),
                          "kind": "SEGMENT", "id": s["id"], "discipline": disc,
                          "cx": (a[0] + b[0]) / 2.0, "cy": (ay + by) / 2.0,
                          "cz": (a[2] + b[2]) / 2.0,
                          "ex": ln, "ey": rs["h"], "ez": rs["w"],
                          "rot_y": math.atan2(-dz, dx),
                          "vertical": abs(dy) > abs(dx) + abs(dz),
                          "geometry_source": rs["source"], "element_source": s["source"]})
    for e in mep.get("equipment") or []:
        if e["x"] is None or e["y"] is None:
            continue
        rd = e["render_dimensions"]
        disc = _discipline_of(mep, e.get("system_id"))
        items.append({"name": "MEP|%s|%s|eq" % (_DISC_TAG.get(disc, "OTHER"), e["id"]),
                      "kind": "EQUIPMENT", "id": e["id"], "discipline": disc,
                      "cx": e["x"], "cy": e["y"] + rd["h"] / 2.0, "cz": e["z"],
                      "ex": rd["w"], "ey": rd["h"], "ez": rd["d"],
                      "geometry_source": rd["source"], "element_source": e["source"]})
    for t in (mep.get("terminals") or []) + (mep.get("adapted_terminals") or []):
        if t["x"] is None or t["y"] is None:
            continue
        disc = _discipline_of(mep, t.get("system_id"),
                              DISCIPLINE_OF.get(t.get("suggested_system_type") or "OTHER", "OTHER"))
        sz = FALLBACKS["terminal_size_m"]
        items.append({"name": "MEP|%s|%s|term" % (_DISC_TAG.get(disc, "OTHER"), t["id"]),
                      "kind": "TERMINAL", "id": t["id"], "discipline": disc,
                      "terminal_type": t["terminal_type"],
                      "cx": t["x"], "cy": t["y"] + sz / 2.0, "cz": t["z"],
                      "ex": sz, "ey": sz, "ez": sz,
                      "geometry_source": "display_fallback",
                      "element_source": t["source"], "adapted": t.get("adapted") is True})
    for r in mep.get("risers") or []:
        if r["x"] is None or not r["level_indexes"]:
            continue
        lv = {l["index"]: l for l in mep.get("levels") or []}
        base = (lv.get(min(r["level_indexes"])) or {}).get("elevation_m")
        top = (lv.get(max(r["level_indexes"])) or {}).get("elevation_m")
        if base is None or top is None or top - base <= _EPS:
            continue
        w = r["w_m"]["value"]
        d = r["d_m"]["value"]
        src = "model" if (w is not None and d is not None) else "display_fallback"
        w = w if w is not None else r["w_m"]["render_fallback"]
        d = d if d is not None else r["d_m"]["render_fallback"]
        items.append({"name": "MEP|RISER|%s|riser" % r["id"], "kind": "RISER", "id": r["id"],
                      "discipline": "OTHER", "cx": r["x"], "cy": base + (top - base) / 2.0,
                      "cz": r["z"], "ex": w, "ey": top - base, "ez": d,
                      "geometry_source": src, "element_source": r["source"]})
    items.sort(key=lambda i: str(i["name"]))
    return items


# --------------------------------------------------------------- خدمات --
def element_by_id(mep, eid):
    for key in ("systems", "nodes", "segments", "equipment", "terminals", "adapted_terminals",
                "risers", "penetrations"):
        for el in mep.get(key) or []:
            if el.get("id") == eid:
                return el
    for r in mep.get("relationships") or []:
        if r.get("id") == eid:
            return r
    return None


def system_by_id(mep, sid):
    for s in mep.get("systems") or []:
        if s["id"] == sid or s["id"] == _nid(mep.get("building_id"), sid, "sys", 0):
            return s
    return None


def interferences(mep):
    codes = ("SEGMENT_CROSSES_WALL_WITHOUT_PENETRATION",
             "SEGMENT_CROSSES_SLAB_WITHOUT_PENETRATION",
             "SEGMENT_CROSSES_STRUCTURAL_BEAM", "SEGMENT_CROSSES_STRUCTURAL_COLUMN",
             "SEGMENT_CROSSES_STRUCTURAL_SLAB", "RISER_OUTSIDE_SHAFT",
             "EQUIPMENT_OUTSIDE_SPACE", "TERMINAL_OUTSIDE_SPACE",
             "MEP_ELEMENT_IN_FLOOR_OPENING", "ROUTE_OUTSIDE_BUILDING")
    return [i for i in (mep.get("issues") or []) if i["code"] in codes]


def to_world(mep, x, z):
    t = mep.get("transform") or {}
    rot = math.radians(float(t.get("rotation_deg") or 0.0))
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    ca, sa = math.cos(rot), math.sin(rot)
    return [px + x * ca - z * sa, pz + x * sa + z * ca]


def rule_inputs(mep):
    """حقائق MEP معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية هنا،
    والاحتياط لا يدخل أبداً: ما لم يُذكر يبقى null."""
    out = {"building": {}}
    present = {}
    for s in mep.get("systems") or []:
        present[s["system_type"]] = True
    for t in SYSTEM_TYPES:
        out["building"]["mep.system.exists." + t] = bool(present.get(t))
    terms = (mep.get("terminals") or []) + (mep.get("adapted_terminals") or [])
    out["building"]["mep.terminal.count"] = len(terms)
    out["building"]["mep.equipment.count"] = len(mep.get("equipment") or [])
    for e in mep.get("equipment") or []:
        out[e["id"]] = {"mep.equipment.type": e["equipment_type"],
                        "mep.equipment.system": e.get("system_id"),
                        "mep.member.source": e["source"]}
    for s in mep.get("segments") or []:
        sz = s.get("size") or {}
        out[s["id"]] = {"mep.segment.kind": s["kind"],
                        "mep.segment.size.diameter_m": sz.get("diameter_m"),
                        "mep.segment.size.width_m": sz.get("width_m"),
                        "mep.segment.size.height_m": sz.get("height_m"),
                        "mep.segment.routing_status": s["routing_status"],
                        "mep.member.source": s["source"]}
    served = {}
    for r in mep.get("relationships") or []:
        if r["type"] == "SYSTEM_SERVES_SPACE":
            served.setdefault(r["to"], []).append(r["from"])
    for sp, sys in sorted(served.items()):
        out.setdefault(sp, {})["mep.system.serves_space"] = sorted(sys)
    return out


def summary(mep):
    iss = mep.get("issues") or []
    by_disc = {}
    for s in mep.get("systems") or []:
        by_disc[s["discipline"]] = by_disc.get(s["discipline"], 0) + 1
    return {"building_id": mep.get("building_id"), "compiler_version": mep.get("compiler_version"),
            "status": mep.get("status"), "synthetic": mep.get("synthetic") is True,
            "regulatory": False,
            "systems": len(mep.get("systems") or []), "systems_by_discipline": by_disc,
            "nodes": len(mep.get("nodes") or []), "segments": len(mep.get("segments") or []),
            "routed_segments": sum(1 for s in mep.get("segments") or []
                                   if s["routing_status"] == "ROUTED"),
            "unrouted_segments": sum(1 for s in mep.get("segments") or []
                                     if s["routing_status"] == "UNROUTED"),
            "segments_with_size": sum(1 for s in mep.get("segments") or [] if s["size"]),
            "equipment": len(mep.get("equipment") or []),
            "terminals": len(mep.get("terminals") or []),
            "adapted_terminals": len(mep.get("adapted_terminals") or []),
            "risers": len(mep.get("risers") or []),
            "penetrations": len(mep.get("penetrations") or []),
            "relationships": len(mep.get("relationships") or []),
            "interferences": len(interferences(mep)),
            "issues": len(iss),
            "errors": sum(1 for i in iss if i.get("severity") == "ERROR"),
            "warnings": sum(1 for i in iss if i.get("severity") == "WARNING"),
            "infos": sum(1 for i in iss if i.get("severity") == "INFO"),
            "note": "MEP representation only — no design, no load or flow calculation, "
                    "no sizing, no code compliance"}
