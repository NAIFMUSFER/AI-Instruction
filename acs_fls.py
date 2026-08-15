# -*- coding: utf-8 -*-
# =============================================================================
# acs_fls.py — أساس نموذج بيانات الحريق وسلامة الأرواح: تمثيل وطوبولوجيا فقط.
#
# يربط ويوحّد ما هو موجود أصلاً: مخارج من طبقة الإخلاء · أجهزة من نموذج MEP ·
# جدران وفتحات ونوى من النموذج المعماري · نقاط المرحلة 1. ولا يكرّر شيئاً منها.
#
# مبادئ صارمة:
#   • لا هندسة حريق ولا محاكاة: لا تباعد مرشّات ولا تغطية ولا هيدروليك ولا
#     طلب مياه ولا تحجيم مضخّات/خزّانات ولا تباعد كواشف ولا مناطق إنذار.
#   • لا مقاومة حريق تُحسب ولا تُستنتج من مادة. المجهول يبقى null.
#   • الباب المعماري ليس باب حريق، والجدار ليس حاجز حريق، والدرج ليس محمياً،
#     والمنور ليس مقاوماً — بلا تصريح معلن.
#   • الجهاز موجود ≠ التغطية مؤكّدة. النظام موجود ≠ النظام كافٍ.
#     المخرج موجود ≠ الإخلاء مطابق. الحاجز موجود ≠ الفصل مطابق.
#   • الغياب ليس مخالفة: لا خطأ لمجرّد عدم وجود مرشّات أو إنذار أو باب حريق.
#   • CODE_REQUIRED غير موجود في هذه الطبقة إطلاقاً.
#   • لا تعديل للمعماري ولا للإنشائي ولا لـ MEP، ولا إصلاح تلقائي.
# =============================================================================
import json
import math
import os

import acs_arch as ARCH
import acs_mep as MEP
import acs_relations as REL
import acs_egress as EG

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_fls.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
COMPILER_VERSION = SPEC["compiler_version"]
ELEMENT_TYPES = tuple(SPEC["element_types"])
MODEL_STATUS = tuple(SPEC["model_status"])
PROVENANCE = tuple(SPEC["provenance_values"])
FORBIDDEN_PROVENANCE = tuple(SPEC["forbidden_provenance"])
VERIFIED_SOURCES = tuple(SPEC["verified_sources"])
ADAPTER_ORIGINS = tuple(SPEC["adapter_origins"])
DEVICE_TYPES = tuple(SPEC["device_types"])
DEVICE_CATEGORY = SPEC["device_categories"]
DEVICE_CATEGORIES = tuple(SPEC["device_categories_list"])
MEP_DEVICE_MAP = SPEC["mep_device_map"]
MEP_EQUIPMENT_MAP = SPEC["mep_equipment_map"]
REFERENCED_MEP_SYSTEMS = tuple(SPEC["referenced_mep_systems"])
BARRIER_TYPES = tuple(SPEC["barrier_types"])
OPENING_TYPES = tuple(SPEC["opening_types"])
PROTECTION_STATUSES = tuple(SPEC["protection_statuses"])
SMOKE_CONTROL_KINDS = tuple(SPEC["smoke_control_kinds"])
REL_TYPES = tuple(SPEC["relationship_types"])
REL_STATUSES = tuple(SPEC["relationship_statuses"])
SEVERITIES = tuple(SPEC["issue_severities"])
ISSUE_CODES = SPEC["issue_codes"]
FALLBACKS = SPEC["display_fallbacks"]
RENDER_LAYERS = tuple(SPEC["render_layers"])

_EPS = 1e-6
_TOL = 0.15

_LAYER_OF = {"DETECTION": "FLS_DETECTION", "ALARM": "FLS_ALARM",
             "SUPPRESSION": "FLS_SUPPRESSION", "FIRE_WATER": "FLS_FIRE_WATER",
             "EMERGENCY_LIGHTING": "FLS_EMERGENCY_LIGHTING", "SIGNAGE": "FLS_SIGNAGE",
             "OTHER": "FLS_OTHER"}


def severity_of(code):
    return ISSUE_CODES.get(code, "WARNING")


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


def _is_bad_number(v):
    return v is not None and not isinstance(v, bool) and _num(v) is None


def _src(v, default="unknown"):
    s = str(v).lower() if v is not None else default
    # CODE_REQUIRED و RULE ممنوعتان هنا: لا دليل قاعدة حريق مُتحقَّق منه في المنصّة
    if s in FORBIDDEN_PROVENANCE:
        return "unknown"
    return s if s in PROVENANCE else "unknown"


def _raw(building):
    f = building.get("fire_life_safety")
    return f if isinstance(f, dict) else {}


def _nid(bid, given, prefix, n):
    if given:
        s = str(given)
        if s.startswith(bid + "."):
            return s
        head = s.split(".")[0]
        if head.startswith("bld_") and head != bid:
            return s
        return "%s.fls.%s" % (bid, s)
    return "%s.fls.%s_%d" % (bid, prefix, n)


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


def _rating(v):
    """مدّة المقاومة المذكورة فقط. لا تُستنتج من مادة ولا تُحسب ولا تُتحقّق."""
    n = _num(v)
    if n is None:
        return {"value": None, "source": "unknown",
                "note": "rating is never inferred from a material or an element type"}
    return {"value": n, "source": "imported",
            "note": "stated by the model; not verified and not calculated"}


def _props(props, source):
    out = {}
    if isinstance(props, dict):
        for k in sorted(props.keys()):
            out[str(k)] = {"value": props[k], "source": _src(source, "imported")}
    return out


# ------------------------------------------------------------- الأنظمة --
def _systems(raw, bid, mep):
    """مراجع إلى أنظمة MEP ذات دور حريق/سلامة. لا طوبولوجيا موازية."""
    out = []
    mep_sys = {s["id"]: s for s in (mep or {}).get("systems") or []}
    declared = raw.get("systems") or []
    seen = set()
    for n, s in enumerate(declared):
        ref = s.get("mep_system_id") or s.get("system_id")
        full = MEP._nid(bid, ref, "sys", 0) if ref else None
        m = mep_sys.get(full)
        seen.add(full)
        out.append({
            "id": _nid(bid, s.get("id"), "sys", n), "type": "FLS_SYSTEM", "building_id": bid,
            "mep_system_id": full, "mep_system_resolved": m is not None,
            "mep_system_type": m["system_type"] if m else None,
            "role": str(s.get("role") or "unknown").lower(),
            "name": s.get("name"),
            "status": str(s.get("status")).upper() if s.get("status") else None,
            "origin": "model", "source": _src(s.get("source")),
            "note": "a represented system is not an operational, complete or adequate system"})
    # مراجع تلقائية لأنظمة MEP الحريقية الموجودة — إشارة لا تكرار
    for m in (mep or {}).get("systems") or []:
        if m["system_type"] in REFERENCED_MEP_SYSTEMS and m["id"] not in seen:
            out.append({
                "id": "%s.fls.mep_%s" % (bid, str(m["id"]).split(".mep.")[-1]),
                "type": "FLS_SYSTEM", "building_id": bid,
                "mep_system_id": m["id"], "mep_system_resolved": True,
                "mep_system_type": m["system_type"], "role": "unknown",
                "name": m.get("name"),
                "status": None, "origin": "mep_adapter",
                # إسناد نظام MEP ينتقل كما هو ولا يُرقّى
                "original_source": m["source"], "source": "mep_adapter",
                "note": "referenced from the MEP model; the MEP model remains the source of "
                        "truth for its topology"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------- الأجهزة --
def _device_common(bid, dtype, origin):
    cat = DEVICE_CATEGORY.get(dtype, "OTHER")
    return {"type": "FLS_DEVICE", "building_id": bid, "device_type": dtype,
            "device_category": cat, "render_layer": _LAYER_OF.get(cat, "FLS_OTHER"),
            "origin": origin}


def _mep_has(mep, bid, ref):
    if not mep or ref is None:
        return False
    full = MEP._nid(bid, ref, "term", 0)
    for key in ("terminals", "adapted_terminals", "equipment", "nodes", "segments"):
        for e in mep.get(key) or []:
            if e["id"] == ref or e["id"] == full:
                return True
    return False


def _devices(raw, bid, levels_idx, space_idx, sys_ids, mep):
    out = []
    for n, d in enumerate(raw.get("devices") or []):
        lvl = _level_of(levels_idx, d.get("level"))
        t = str(d.get("type") or "OTHER").upper()
        known = t in DEVICE_TYPES
        pos = d.get("position") if isinstance(d.get("position"), dict) else d
        y = _num(pos.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        sp = d.get("space") or d.get("space_id")
        sid = d.get("system_id")
        e = dict(_device_common(bid, t if known else "OTHER", "model"))
        e.update({
            "id": _nid(bid, d.get("id"), "dev", n),
            "declared_type": d.get("type"), "device_type_recognised": known,
            "system_id": _nid(bid, sid, "sys", 0) if sid else None,
            "system_resolved": sid is None or _nid(bid, sid, "sys", 0) in sys_ids,
            # مرجع صريح إلى عنصر MEP قائم — يُتحقّق منه ولا يُختلق
            "mep_element_id": d.get("mep_element_id"),
            "mep_element_resolved": (None if d.get("mep_element_id") is None
                                     else _mep_has(mep, bid, d.get("mep_element_id"))),
            "x": _num(pos.get("x")), "y": y, "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "level_ref": d.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or d.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "loop_ref": d.get("loop"), "panel_ref": d.get("panel"),
            "alarm_zone_ref": d.get("alarm_zone"),
            # لا نصف قطر تغطية ولا حرارة تشغيل ولا K ولا ضغط ولا تدفّق ولا شمعة
            "properties": _props(d.get("properties"), d.get("source")),
            "status": str(d.get("status")).upper() if d.get("status") else None,
            "source": _src(d.get("source")),
            "note": "a represented device is not coverage, protection or compliance"})
        out.append(e)
    # محوّل MEP: كل نهاية/معدّة حريقية موجودة تُشار إليها ولا تُنسخ
    for t in ((mep or {}).get("terminals") or []) + ((mep or {}).get("adapted_terminals") or []):
        mapped = MEP_DEVICE_MAP.get(t.get("terminal_type"))
        if mapped is None:
            continue
        e = dict(_device_common(bid, mapped, "mep_adapter"
                                if t.get("origin") != "phase1_point" else "phase1_adapter"))
        e.update({
            "id": "%s.fls.mep_%s" % (bid, str(t["id"]).split(".mep.")[-1]),
            "declared_type": t.get("terminal_type"), "device_type_recognised": True,
            "system_id": None,
            "system_resolved": True,
            "mep_element_id": t["id"], "mep_element_resolved": True,
            "mep_system_id": t.get("system_id"),
            "x": t.get("x"), "y": t.get("y"), "z": t.get("z"),
            "raw_x": t.get("raw_x"), "raw_z": t.get("raw_z"),
            "level_ref": t.get("level_ref"), "level_id": t.get("level_id"),
            "level_index": t.get("level_index"), "level_resolved": t.get("level_resolved"),
            "space_ref": t.get("space_ref"), "space_id": t.get("space_id"),
            "space_resolved": t.get("space_resolved"),
            "loop_ref": None, "panel_ref": None, "alarm_zone_ref": None,
            "properties": {}, "status": None,
            # إسناد العنصر الأصلي ينتقل كما هو ولا يُرقّى أبداً
            "original_source": t.get("original_source") or t["source"],
            "source": "phase1_adapter" if t.get("origin") == "phase1_point" else "mep_adapter",
            "note": "referenced from the MEP model; no second geometry is created and the "
                    "original provenance is carried through unchanged"})
        out.append(e)
    for eq in (mep or {}).get("equipment") or []:
        mapped = MEP_EQUIPMENT_MAP.get(eq.get("equipment_type"))
        if mapped is None:
            continue
        e = dict(_device_common(bid, mapped, "mep_adapter"))
        e.update({
            "id": "%s.fls.mep_%s" % (bid, str(eq["id"]).split(".mep.")[-1]),
            "declared_type": eq.get("equipment_type"), "device_type_recognised": True,
            "system_id": None, "system_resolved": True,
            "mep_element_id": eq["id"], "mep_element_resolved": True,
            "mep_system_id": eq.get("system_id"),
            "x": eq.get("x"), "y": eq.get("y"), "z": eq.get("z"),
            "raw_x": eq.get("raw_x"), "raw_z": eq.get("raw_z"),
            "level_ref": eq.get("level_ref"), "level_id": eq.get("level_id"),
            "level_index": eq.get("level_index"), "level_resolved": eq.get("level_resolved"),
            "space_ref": eq.get("space_ref"), "space_id": eq.get("space_id"),
            "space_resolved": eq.get("space_resolved"),
            "loop_ref": None, "panel_ref": None, "alarm_zone_ref": None,
            "properties": {}, "status": None,
            "original_source": eq["source"], "source": "mep_adapter",
            "note": "referenced from the MEP model; no second geometry is created"})
        out.append(e)
    out.sort(key=lambda e: str(e["id"]))
    return out


# -------------------------------------------------- المخارج والدرج والمنور --
def _exits(raw, bid, building, rels, arch, levels_idx):
    """المخارج تأتي من أساس الإخلاء وحده. لا محرّك استنتاج مخارج ثانٍ هنا."""
    try:
        eg_exits = EG.extract_exits(building, rels, bid)
    except Exception:
        eg_exits = []
    idx = {e["id"]: e for e in eg_exits}
    out = []
    declared = raw.get("exits") or []
    seen = set()
    for n, x in enumerate(declared):
        ref = x.get("exit_id") or x.get("exit_ref")
        e = idx.get(ref)
        seen.add(ref)
        out.append({
            "id": _nid(bid, x.get("id"), "exit", n), "type": "FLS_EXIT", "building_id": bid,
            "exit_ref": ref, "exit_resolved": e is not None,
            "space_id": (e or {}).get("space") if e else x.get("space"),
            "level_id": (e or {}).get("level") if e else x.get("level"),
            "destination": (e or {}).get("destination") if e else None,
            "egress_status": (e or {}).get("status") if e else None,
            "via": (e or {}).get("via") if e else None,
            "properties": _props(x.get("properties"), x.get("source")),
            "origin": "model", "source": _src(x.get("source")),
            "note": "a represented exit is not a compliant means of egress"})
    for e in eg_exits:
        if e["id"] in seen:
            continue
        out.append({
            "id": "%s.fls.eg_%s" % (bid, str(e["id"]).split(".")[-1]),
            "type": "FLS_EXIT", "building_id": bid,
            "exit_ref": e["id"], "exit_resolved": True,
            "space_id": e.get("space"), "level_id": e.get("level"),
            "destination": e.get("destination"), "egress_status": e.get("status"),
            "via": e.get("via"), "properties": {},
            "origin": "egress_adapter",
            "original_source": e.get("source"), "source": "egress_adapter",
            "note": "referenced from the egress foundation, which remains the source of truth"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _stairs(raw, bid, arch):
    """درج مُشار إليه من النوى المعمارية. لا تصنيف تلقائي كدرج محمي."""
    cores = {c["id"]: c for c in (arch or {}).get("cores") or []}
    out = []
    declared = raw.get("stairs") or []
    seen = set()
    for n, s in enumerate(declared):
        ref = s.get("core_id") or s.get("arch_core_id")
        c = cores.get(ref)
        seen.add(ref)
        prot = str(s.get("protection_status") or "unknown").lower()
        out.append({
            "id": _nid(bid, s.get("id"), "stair", n), "type": "FLS_STAIR", "building_id": bid,
            "core_id": ref, "core_resolved": c is not None,
            "core_type": c["type"] if c else None,
            "served_levels": list((c or {}).get("served_levels") or []),
            # لا يصير محمياً إلا بتصريح معلن
            "protection_status": prot if prot in PROTECTION_STATUSES else "unknown",
            "enclosure_barrier_ref": s.get("enclosure_barrier"),
            "rating_minutes": _rating(s.get("rating_minutes")),
            "origin": "model", "source": _src(s.get("source")),
            "note": "a stair is never classified as a protected stair automatically"})
    for c in (arch or {}).get("cores") or []:
        if c["id"] in seen or c["type"] != "STAIR":
            continue
        out.append({
            "id": "%s.fls.core_%s" % (bid, str(c["id"]).split(".")[-1]),
            "type": "FLS_STAIR", "building_id": bid,
            "core_id": c["id"], "core_resolved": True, "core_type": c["type"],
            "served_levels": list(c.get("served_levels") or []),
            "protection_status": "unknown", "enclosure_barrier_ref": None,
            "rating_minutes": _rating(None),
            "origin": "arch_adapter", "source": "arch_adapter",
            "note": "referenced from the architectural cores; protection is unknown, "
                    "not assumed"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _shafts(raw, bid, arch, mep):
    cores = {c["id"]: c for c in (arch or {}).get("cores") or []}
    risers = {r["id"]: r for r in (mep or {}).get("risers") or []}
    out = []
    for n, s in enumerate(raw.get("shafts") or []):
        ref = s.get("core_id") or s.get("riser_id")
        c = cores.get(ref) or risers.get(ref)
        prot = str(s.get("protection_status") or "unknown").lower()
        out.append({
            "id": _nid(bid, s.get("id"), "shaft", n), "type": "FLS_SHAFT", "building_id": bid,
            "host_ref": ref, "host_resolved": c is not None,
            "host_kind": ("arch_core" if ref in cores else ("mep_riser" if ref in risers
                                                            else "unknown")),
            "protection_status": prot if prot in PROTECTION_STATUSES else "unknown",
            "rating_minutes": _rating(s.get("rating_minutes")),
            "origin": "model", "source": _src(s.get("source")),
            "note": "a shaft is not assumed to be fire-rated"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------- الحواجز وفتحاتها --
def _barriers(raw, bid, arch, levels_idx):
    walls = {w["id"]: w for w in (arch or {}).get("walls") or []}
    out = []
    for n, b in enumerate(raw.get("barriers") or []):
        t = str(b.get("type") or "UNKNOWN").upper()
        host = b.get("host_wall_id") or b.get("host_wall")
        hosts = list(b.get("host_wall_ids") or ([host] if host else []))
        resolved = [h for h in hosts if h in walls]
        out.append({
            "id": _nid(bid, b.get("id"), "barrier", n), "type": "FLS_BARRIER",
            "building_id": bid,
            "barrier_type": t if t in BARRIER_TYPES else "OTHER",
            "declared_type": b.get("type"), "barrier_type_recognised": t in BARRIER_TYPES,
            "host_wall_ids": hosts, "resolved_host_wall_ids": resolved,
            "hosts_resolved": len(hosts) > 0 and len(resolved) == len(hosts),
            "level_refs": list(b.get("levels") or []),
            "rating_minutes": _rating(b.get("rating_minutes")),
            "continuity": str(b.get("continuity") or "unknown").lower(),
            "origin": "model", "source": _src(b.get("source")),
            "note": "an architectural or structural wall is never a fire barrier without "
                    "explicit classification"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _openings(raw, bid, arch, barrier_ids):
    ops = {o["id"]: o for o in (arch or {}).get("openings") or []}
    refs = {}
    for o in (arch or {}).get("openings") or []:
        refs.setdefault(o.get("opening_ref"), o)
    out = []
    for n, p in enumerate(raw.get("openings") or []):
        t = str(p.get("type") or "UNKNOWN").upper()
        host = p.get("arch_opening_id") or p.get("opening_id") or p.get("door_id")
        a = ops.get(host) or refs.get(host)
        bref = p.get("barrier_id")
        out.append({
            "id": _nid(bid, p.get("id"), "open", n), "type": "FLS_OPENING", "building_id": bid,
            "opening_type": t if t in OPENING_TYPES else "OTHER",
            "declared_type": p.get("type"), "opening_type_recognised": t in OPENING_TYPES,
            "arch_opening_id": host, "arch_opening_resolved": a is not None,
            "resolved_opening_id": a["id"] if a else None,
            "arch_opening_type": a["type"] if a else None,
            "barrier_id": _nid(bid, bref, "barrier", 0) if bref else None,
            "barrier_resolved": bref is None or _nid(bid, bref, "barrier", 0) in barrier_ids,
            "fire_door": p.get("fire_door") is True or t == "FIRE_DOOR",
            "rating_minutes": _rating(p.get("rating_minutes")),
            "self_closing": p.get("self_closing") if isinstance(p.get("self_closing"), bool)
                            else None,
            "smoke_controlled": p.get("smoke_controlled")
                                if isinstance(p.get("smoke_controlled"), bool) else None,
            "origin": "model", "source": _src(p.get("source")),
            "note": "a normal architectural door is not a fire door; this classification is "
                    "explicit model data and is not evaluated against any code"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# --------------------------------------------- المناطق واللافتات وغيرها --
def _zones(raw, bid, levels_idx, space_idx):
    out = []
    for n, z in enumerate(raw.get("zones") or []):
        lv = [_level_of(levels_idx, r) for r in (z.get("level_ids") or z.get("levels") or [])]
        sp = list(z.get("space_ids") or z.get("spaces") or [])
        out.append({
            "id": _nid(bid, z.get("id"), "zone", n), "type": "FLS_ZONE", "building_id": bid,
            "name": z.get("name"), "zone_kind": str(z.get("kind") or "fire_compartment").lower(),
            "level_refs": list(z.get("level_ids") or z.get("levels") or []),
            "level_ids": [l["id"] for l in lv if l],
            "levels_resolved": all(l is not None for l in lv),
            "space_ids": sp,
            "resolved_space_ids": [s for s in sp if str(s) in space_idx],
            "spaces_resolved": all(str(s) in space_idx for s in sp),
            "boundary_refs": list(z.get("boundary_refs") or []),
            "rating_minutes": _rating(z.get("rating_minutes")),
            "origin": "model", "source": _src(z.get("source")),
            "note": "a compartment is never inferred from room boundaries"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _signs(raw, bid, levels_idx, space_idx, exit_refs):
    out = []
    for n, s in enumerate(raw.get("signs") or []):
        lvl = _level_of(levels_idx, s.get("level"))
        pos = s.get("position") if isinstance(s.get("position"), dict) else s
        y = _num(pos.get("y"))
        if y is None and lvl is not None:
            y = lvl["elevation_m"]
        sp = s.get("space") or s.get("space_id")
        tgt = s.get("indicates_exit") or s.get("exit_id")
        out.append({
            "id": _nid(bid, s.get("id"), "sign", n), "type": "FLS_SIGN", "building_id": bid,
            "sign_kind": str(s.get("kind") or "exit_sign").lower(),
            "indicates_exit": tgt, "target_resolved": tgt in exit_refs if tgt else None,
            "x": _num(pos.get("x")), "y": y, "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "level_ref": s.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or s.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "illuminated": s.get("illuminated") if isinstance(s.get("illuminated"), bool)
                           else None,
            "origin": "model", "source": _src(s.get("source")),
            "note": "whether signage is required or adequate is never determined here"})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _points(raw, bid, key, prefix, etype, levels_idx, space_idx, note):
    out = []
    for n, p in enumerate(raw.get(key) or []):
        lvl = _level_of(levels_idx, p.get("level"))
        pos = p.get("position") if isinstance(p.get("position"), dict) else p
        sp = p.get("space") or p.get("space_id")
        out.append({
            "id": _nid(bid, p.get("id"), prefix, n), "type": etype, "building_id": bid,
            "name": p.get("name"),
            "scope": str(p.get("scope") or ("site" if etype == "FLS_ASSEMBLY_POINT"
                                            else "building")).lower(),
            "x": _num(pos.get("x")), "z": _num(pos.get("z")),
            "raw_x": pos.get("x"), "raw_z": pos.get("z"),
            "level_ref": p.get("level"), "level_id": lvl["id"] if lvl else None,
            "level_index": lvl["index"] if lvl else None,
            "level_resolved": lvl is not None or p.get("level") is None,
            "space_ref": sp, "space_id": (space_idx.get(str(sp)) or {}).get("id") if sp else None,
            "space_resolved": sp is None or str(sp) in space_idx,
            "capacity_persons": None,
            "properties": _props(p.get("properties"), p.get("source")),
            "origin": "model", "source": _src(p.get("source")), "note": note})
    out.sort(key=lambda e: str(e["id"]))
    return out


def _smoke_control(raw, bid, levels_idx):
    out = []
    for n, s in enumerate(raw.get("smoke_control") or []):
        k = str(s.get("kind") or "other").lower()
        lv = [_level_of(levels_idx, r) for r in (s.get("levels") or [])]
        out.append({
            "id": _nid(bid, s.get("id"), "smoke", n), "type": "FLS_SMOKE_CONTROL",
            "building_id": bid,
            "kind": k if k in SMOKE_CONTROL_KINDS else "other", "declared_kind": s.get("kind"),
            "level_refs": list(s.get("levels") or []),
            "level_ids": [l["id"] for l in lv if l],
            "levels_resolved": all(l is not None for l in lv),
            "space_ids": list(s.get("spaces") or []),
            "system_ref": s.get("system_id"),
            "properties": _props(s.get("properties"), s.get("source")),
            "origin": "model", "source": _src(s.get("source")),
            "note": "a data placeholder only — no smoke modelling, airflow or pressurisation "
                    "analysis exists"})
    out.sort(key=lambda e: str(e["id"]))
    return out


# ------------------------------------------------------------ العلاقات --
def _relationships(bid, systems, devices, exits, stairs, barriers, openings, zones, signs,
                   assembly, refuge, arch, issues):
    rels = []
    seq = [0]

    def add(rtype, frm, to, status, basis, meta=None):
        seq[0] += 1
        e = {"id": "%s.fls.rel_%d" % (bid, seq[0]), "type": rtype, "from": frm, "to": to,
             "source": "model_declaration" if status == "confirmed" else "reference_resolution",
             "status": status, "basis": basis,
             "note": "factual representation and location only — never coverage, protection, "
                     "adequacy or compliance"}
        if meta:
            e["meta"] = meta
        rels.append(e)
        return e

    sys_by_id = {s["id"]: s for s in systems}
    for d in devices:
        if d.get("space_id"):
            add("DEVICE_IN_SPACE", d["id"], d["space_id"], "confirmed",
                "the device lies in this architectural space",
                {"disclaimer": "a represented %s in a space is not coverage or protection of "
                               "that space" % d["device_type"].lower()})
        if d.get("system_id") and d["system_id"] in sys_by_id:
            add("DEVICE_ON_SYSTEM", d["id"], d["system_id"], "confirmed",
                "declared by the model")
            add("SYSTEM_HAS_DEVICE", d["system_id"], d["id"], "confirmed",
                "declared by the model")
        elif d.get("mep_system_id"):
            for s in systems:
                if s.get("mep_system_id") == MEP._nid(bid, d["mep_system_id"], "sys", 0):
                    add("DEVICE_ON_SYSTEM", d["id"], s["id"], "confirmed",
                        "resolved through the MEP system the referenced element belongs to")
                    add("SYSTEM_HAS_DEVICE", s["id"], d["id"], "confirmed",
                        "resolved through the MEP system the referenced element belongs to")
                    break
        elif d.get("origin") == "model":
            # ملاحظة فجوة بيانات تخصّ ما صرّح به النموذج فقط، لا ما أُشير إليه
            issues.append({"code": "DEVICE_WITHOUT_SYSTEM", "subject": d["id"],
                           "detail": "the device names no system; this is a data gap, "
                                     "not a violation"})
        if d.get("loop_ref"):
            add("DEVICE_CONNECTED_TO_LOOP", d["id"], str(d["loop_ref"]), "confirmed",
                "declared by the model", {"disclaimer": "loops are never designed automatically"})
        if d.get("panel_ref"):
            add("PANEL_CONTROLS_DEVICE", str(d["panel_ref"]), d["id"], "confirmed",
                "declared by the model")
        if d.get("alarm_zone_ref"):
            add("DEVICE_IN_ALARM_ZONE", d["id"], str(d["alarm_zone_ref"]), "confirmed",
                "declared by the model",
                {"disclaimer": "alarm zones are never derived from floors or rooms"})
    for x in exits:
        if x.get("level_id"):
            add("EXIT_SERVES_LEVEL", x["id"], x["level_id"], "confirmed",
                "taken from the egress foundation",
                {"disclaimer": "a represented exit is not a compliant means of egress"})
    # هدف اللافتة يجب أن يكون مخرجاً محلولاً فعلاً في أساس الإخلاء، لا مجرّد
    # مرجع مذكور: مرجع لا يقابله مخرج حقيقي يُبلَّغ ولا يُخترع له هدف.
    exit_refs = {x["exit_ref"] for x in exits if x.get("exit_resolved")}
    for s in signs:
        if not s.get("indicates_exit"):
            continue
        ok = s["indicates_exit"] in exit_refs
        add("SIGN_INDICATES_EXIT", s["id"], s["indicates_exit"] if ok else None,
            "confirmed" if ok else "unresolved",
            "declared by the model" if ok else "the referenced exit does not exist")
        if not ok:
            issues.append({"code": "SIGN_TARGET_MISSING", "subject": s["id"],
                           "ref": s["indicates_exit"],
                           "detail": "the target is not invented; the reference is reported"})
    b_by_id = {b["id"]: b for b in barriers}
    for o in openings:
        if o.get("barrier_id") and o["barrier_id"] in b_by_id:
            add("BARRIER_CONTAINS_OPENING", o["barrier_id"], o["id"], "confirmed",
                "declared by the model")
            if o["fire_door"]:
                add("FIRE_DOOR_HOSTED_BY_BARRIER", o["id"], o["barrier_id"], "confirmed",
                    "declared by the model")
    for z in zones:
        for sp in z["resolved_space_ids"]:
            add("ZONE_CONTAINS_SPACE", z["id"], sp, "confirmed", "declared by the model")
    for s in stairs:
        if s.get("core_resolved"):
            add("STAIR_REFERENCES_CORE", s["id"], s["core_id"], "confirmed",
                "referenced from the architectural cores",
                {"protection_status": s["protection_status"]})
    for a in assembly:
        add("ASSEMBLY_POINT_ON_SITE", a["id"], None, "confirmed", "declared by the model",
            {"disclaimer": "no path from a building exit to an assembly point exists "
                           "in this phase"})
    return rels


# ------------------------------------------------- سلامة النموذج والتعارض --
def _integrity(bid, devices, signs, openings, barriers, assembly, arch, building, issues):
    voids = (arch or {}).get("voids") or []
    spaces = {s["id"]: s for s in (arch or {}).get("spaces") or []}
    for d in devices:
        sp = spaces.get(d.get("space_id"))
        if sp and sp.get("rect") and d.get("x") is not None:
            rc = sp["rect"]
            if not (rc[0] - _TOL <= d["x"] <= rc[0] + rc[2] + _TOL and
                    rc[1] - _TOL <= d["z"] <= rc[1] + rc[3] + _TOL):
                issues.append({"code": "DEVICE_OUTSIDE_SPACE", "subject": d["id"],
                               "other": sp["id"]})
        if d.get("x") is None or d.get("level_index") is None:
            continue
        for v in voids:
            if v.get("level_index") != d["level_index"]:
                continue
            r = v["rect"]
            if r[0] <= d["x"] <= r[0] + r[2] and r[1] <= d["z"] <= r[1] + r[3]:
                issues.append({"code": "DEVICE_IN_FLOOR_OPENING", "subject": d["id"],
                               "other": v["id"],
                               "detail": "reported as a factual location, not as a fault"})
    for o in openings:
        if not o["arch_opening_resolved"]:
            issues.append({"code": "FIRE_DOOR_NOT_HOSTED" if o["fire_door"]
                                   else "INVALID_HOST_OPENING_REF",
                           "subject": o["id"], "ref": o.get("arch_opening_id")})
    for b in barriers:
        if not b["hosts_resolved"]:
            issues.append({"code": "BARRIER_WITHOUT_HOST", "subject": b["id"],
                           "refs": b.get("host_wall_ids")})
    rects = [s["rect"] for s in (arch or {}).get("spaces") or [] if s.get("rect")]
    if rects:
        bb = [min(r[0] for r in rects), min(r[1] for r in rects),
              max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)]
        for a in assembly:
            if a.get("x") is None:
                continue
            if bb[0] <= a["x"] <= bb[2] and bb[1] <= a["z"] <= bb[3]:
                issues.append({"code": "ASSEMBLY_POINT_INSIDE_BUILDING", "subject": a["id"],
                               "footprint": bb})


# ------------------------------------------------------------- التصريف --
def compile_fls(building, building_id="bld_0", position=None, rotation_deg=0.0,
                arch=None, mep=None, rels=None):
    """يبني نموذج الحريق وسلامة الأرواح من بيانات مذكورة أو مُشار إليها فقط."""
    bid = building_id
    raw = _raw(building)
    if arch is None:
        try:
            arch = ARCH.compile_architecture(building, bid, position, rotation_deg)
        except Exception:
            arch = None
    if rels is None:
        try:
            rels = REL.build_relationships(building, bid)
        except Exception:
            rels = []
    if mep is None:
        try:
            mep = MEP.compile_mep(building, bid, position, rotation_deg, arch)
        except Exception:
            mep = None
    levels_idx = _levels_index(building, bid)
    space_idx = _space_index(arch)

    issues = []
    known_keys = {"status", "synthetic", "meta", "zones", "barriers", "openings", "exits",
                  "stairs", "shafts", "devices", "systems", "signs", "assembly_points",
                  "refuge_areas", "smoke_control", "layer_visibility", "visible_layers"}
    for k in sorted(raw.keys()):
        if k not in known_keys:
            issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": k,
                           "detail": "this collection is not part of the FLS schema and was "
                                     "NOT interpreted"})

    systems = _systems(raw, bid, mep)
    sys_ids = {s["id"] for s in systems}
    devices = _devices(raw, bid, levels_idx, space_idx, sys_ids, mep)
    exits = _exits(raw, bid, building, rels, arch, levels_idx)
    exit_refs = {x["exit_ref"] for x in exits}
    stairs = _stairs(raw, bid, arch)
    shafts = _shafts(raw, bid, arch, mep)
    barriers = _barriers(raw, bid, arch, levels_idx)
    barrier_ids = {b["id"] for b in barriers}
    openings = _openings(raw, bid, arch, barrier_ids)
    zones = _zones(raw, bid, levels_idx, space_idx)
    signs = _signs(raw, bid, levels_idx, space_idx, exit_refs)
    assembly = _points(raw, bid, "assembly_points", "assembly", "FLS_ASSEMBLY_POINT",
                       levels_idx, space_idx,
                       "an assembly point is represented data only; no site evacuation path "
                       "exists in this phase")
    refuge = _points(raw, bid, "refuge_areas", "refuge", "FLS_REFUGE_AREA",
                     levels_idx, space_idx,
                     "an area of refuge is never inferred from a lobby, landing, stair or "
                     "corridor, and accessibility is never evaluated")
    smoke = _smoke_control(raw, bid, levels_idx)

    declared_count = (len(raw.get("zones") or []) + len(raw.get("barriers") or [])
                      + len(raw.get("openings") or []) + len(raw.get("devices") or [])
                      + len(raw.get("systems") or []) + len(raw.get("signs") or [])
                      + len(raw.get("assembly_points") or []) + len(raw.get("refuge_areas") or [])
                      + len(raw.get("smoke_control") or []) + len(raw.get("shafts") or [])
                      + len(raw.get("stairs") or []) + len(raw.get("exits") or []))
    referenced = len(devices) + len(systems) + len(exits) + len(stairs)
    declared = str(raw.get("status") or "").upper()
    if declared in MODEL_STATUS:
        status = declared
    elif declared_count == 0:
        # لا شيء مُصرَّح به: النموذج غير معرَّف مهما بلغت المراجع، والمراجع تظهر
        # في التدقيق كما هي. الغياب ليس نقصاً ولا مخالفة.
        status = "NOT_DEFINED"
    else:
        verified = all(e["source"] in VERIFIED_SOURCES
                       for e in devices + barriers + openings + zones + signs
                       if e.get("origin") == "model")
        status = "REPRESENTED" if verified else "PARTIAL"

    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "building_id": bid,
           "status": status,
           "status_basis": ("declared_by_model" if declared in MODEL_STATUS
                            else ("no fire or life-safety element is declared; %d element(s) "
                                  "are referenced from other layers" % referenced
                                  if declared_count == 0
                                  else "derived from element provenance")),
           "synthetic": raw.get("synthetic") is True, "regulatory": False,
           "transform": {"position": position or {"x": 0.0, "z": 0.0},
                         "rotation_deg": float(rotation_deg or 0.0),
                         "applied": "local coordinates; world transform is applied on read"},
           "levels": [{"id": l["id"], "index": l["index"], "elevation_m": l["elevation_m"]}
                      for l in ARCH._levels(building, bid)],
           "zones": zones, "barriers": barriers, "openings": openings, "exits": exits,
           "stairs": stairs, "shafts": shafts, "devices": devices, "systems": systems,
           "signs": signs, "assembly_points": assembly, "refuge_areas": refuge,
           "smoke_control": smoke, "relationships": [], "issues": [],
           "meta": {"note": SPEC["note"], "fire_note": SPEC["fire_note"],
                    "semantics": SPEC["semantics"],
                    "declared_elements": declared_count, "referenced_elements": referenced,
                    "sources_of_truth": SPEC["source_of_truth"],
                    "navigation_impact": SPEC["navigation_note"],
                    "distance_impact": SPEC["distance_note"],
                    "occupancy_note": SPEC["occupancy_note"],
                    "compliance": "NOT_EVALUATED"}}

    out["relationships"] = _relationships(bid, systems, devices, exits, stairs, barriers,
                                          openings, zones, signs, assembly, refuge, arch, issues)
    _integrity(bid, devices, signs, openings, barriers, assembly, arch, building, issues)
    issues.extend(validate_fls(out))
    for i in issues:
        i["severity"] = severity_of(i["code"])
    issues.sort(key=lambda i: (SEVERITIES.index(i["severity"]) * -1, str(i["code"]),
                               str(i.get("subject"))))
    out["issues"] = issues
    return out


# ------------------------------------------------------------- التحقّق --
def validate_fls(fls):
    """فحوص سلامة بيانات — ليست فحوص كود حريق، والغياب ليس مخالفة."""
    issues = []
    bid = fls.get("building_id")
    groups = ("zones", "barriers", "openings", "exits", "stairs", "shafts", "devices",
              "systems", "signs", "assembly_points", "refuge_areas", "smoke_control")
    seen = {}
    for key in groups:
        for e in fls.get(key) or []:
            if e["id"] in seen:
                issues.append({"code": "DUPLICATE_ELEMENT_ID", "subject": e["id"],
                               "other": seen[e["id"]]})
            seen[e["id"]] = key
            if e.get("type") not in ELEMENT_TYPES:
                issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": e["id"],
                               "declared": e.get("type")})
            if bid and not str(e["id"]).startswith(str(bid) + "."):
                issues.append({"code": "CROSS_BUILDING_REF", "subject": e["id"]})
            if e.get("source") in FORBIDDEN_PROVENANCE:
                issues.append({"code": "UNSUPPORTED_ELEMENT_TYPE", "subject": e["id"],
                               "declared": e.get("source")})

    for s in fls.get("systems") or []:
        if not s["mep_system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": s["id"],
                           "ref": s.get("mep_system_id")})
    for d in fls.get("devices") or []:
        if _is_bad_number(d.get("raw_x")) or _is_bad_number(d.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": d["id"]})
        if not d["device_type_recognised"]:
            issues.append({"code": "UNKNOWN_DEVICE_TYPE", "subject": d["id"],
                           "declared": d.get("declared_type")})
        if not d["system_resolved"]:
            issues.append({"code": "INVALID_SYSTEM_REF", "subject": d["id"],
                           "ref": d.get("system_id")})
        if d.get("mep_element_resolved") is False:
            issues.append({"code": "INVALID_MEP_ELEMENT_REF", "subject": d["id"],
                           "ref": d.get("mep_element_id")})
        if not d["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": d["id"],
                           "ref": d.get("level_ref")})
        if not d["space_resolved"]:
            issues.append({"code": "INVALID_SPACE_REF", "subject": d["id"],
                           "ref": d.get("space_ref")})
    for x in fls.get("exits") or []:
        if not x["exit_resolved"]:
            issues.append({"code": "INVALID_EXIT_REF", "subject": x["id"],
                           "ref": x.get("exit_ref")})
    for s in fls.get("stairs") or []:
        if not s["core_resolved"]:
            issues.append({"code": "INVALID_CORE_REF", "subject": s["id"],
                           "ref": s.get("core_id")})
        if s["protection_status"] == "unknown" and s.get("origin") == "model":
            issues.append({"code": "PROTECTION_UNKNOWN", "subject": s["id"],
                           "detail": "protection is not assumed; this is a data gap, "
                                     "not a violation"})
    for s in fls.get("shafts") or []:
        if not s["host_resolved"]:
            issues.append({"code": "INVALID_CORE_REF", "subject": s["id"],
                           "ref": s.get("host_ref")})
    for b in fls.get("barriers") or []:
        if not b["barrier_type_recognised"]:
            issues.append({"code": "UNKNOWN_BARRIER_TYPE", "subject": b["id"],
                           "declared": b.get("declared_type")})
        for h in b["host_wall_ids"]:
            if h not in b["resolved_host_wall_ids"]:
                issues.append({"code": "INVALID_HOST_WALL_REF", "subject": b["id"], "ref": h})
        if b["rating_minutes"]["value"] is None:
            issues.append({"code": "RATING_UNKNOWN", "subject": b["id"],
                           "detail": "rating is never inferred; this is a data gap, "
                                     "not a violation"})
        elif b["rating_minutes"]["value"] <= 0:
            issues.append({"code": "INVALID_RATING_VALUE", "subject": b["id"],
                           "value": b["rating_minutes"]["value"]})
    for o in fls.get("openings") or []:
        if not o["opening_type_recognised"]:
            issues.append({"code": "UNKNOWN_OPENING_TYPE", "subject": o["id"],
                           "declared": o.get("declared_type")})
        if not o["barrier_resolved"]:
            issues.append({"code": "INVALID_BARRIER_REF", "subject": o["id"],
                           "ref": o.get("barrier_id")})
        if o["rating_minutes"]["value"] is not None and o["rating_minutes"]["value"] <= 0:
            issues.append({"code": "INVALID_RATING_VALUE", "subject": o["id"],
                           "value": o["rating_minutes"]["value"]})
    for z in fls.get("zones") or []:
        if not z["levels_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": z["id"],
                           "refs": z.get("level_refs")})
        for sp in z["space_ids"]:
            if sp not in z["resolved_space_ids"]:
                issues.append({"code": "INVALID_ZONE_SPACE_REF", "subject": z["id"], "ref": sp})
        if not z["space_ids"]:
            issues.append({"code": "ZONE_WITHOUT_SPACES", "subject": z["id"],
                           "detail": "a compartment is never populated by inference"})
    for s in fls.get("signs") or []:
        if _is_bad_number(s.get("raw_x")) or _is_bad_number(s.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": s["id"]})
        if not s["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": s["id"],
                           "ref": s.get("level_ref")})
        if not s["space_resolved"]:
            issues.append({"code": "INVALID_SPACE_REF", "subject": s["id"],
                           "ref": s.get("space_ref")})
    for p in (fls.get("assembly_points") or []) + (fls.get("refuge_areas") or []):
        if _is_bad_number(p.get("raw_x")) or _is_bad_number(p.get("raw_z")):
            issues.append({"code": "NAN_COORDINATE", "subject": p["id"]})
        if not p["level_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": p["id"],
                           "ref": p.get("level_ref")})
    for s in fls.get("smoke_control") or []:
        if not s["levels_resolved"]:
            issues.append({"code": "INVALID_LEVEL_REF", "subject": s["id"],
                           "refs": s.get("level_refs")})
    return issues


# -------------------------------------------------------- بيانات الرسم --
def render_items(fls):
    """عناصر مُشار إليها لا تُرسم مرّتين: ما رسمه MEP يبقى له، وما لا وجود له
    في أي طبقة أخرى (لافتة · علامة حاجز · نقطة تجمّع) يُرسم هنا مرّة واحدة."""
    items = []
    for d in fls.get("devices") or []:
        if d.get("x") is None or d.get("y") is None:
            continue
        referenced = d["origin"] in ("mep_adapter", "phase1_adapter")
        sz = FALLBACKS["device_size_m"]
        items.append({"name": "FLS|%s|%s" % (d["device_type"], d["id"]),
                      "kind": "DEVICE", "id": d["id"], "device_type": d["device_type"],
                      "category": d["device_category"], "layer": d["render_layer"],
                      "render_mode": "referenced" if referenced else "emitted",
                      "references": d.get("mep_element_id"),
                      "cx": d["x"], "cy": d["y"] + sz / 2.0, "cz": d["z"],
                      "ex": sz, "ey": sz, "ez": sz,
                      "geometry_source": "display_fallback",
                      "element_source": d["source"]})
    for s in fls.get("signs") or []:
        if s.get("x") is None or s.get("y") is None:
            continue
        items.append({"name": "FLS|EXIT_SIGN|%s" % s["id"], "kind": "SIGN", "id": s["id"],
                      "device_type": "EXIT_SIGN", "category": "SIGNAGE",
                      "layer": "FLS_SIGNAGE", "render_mode": "emitted", "references": None,
                      "cx": s["x"], "cy": s["y"] + 2.1, "cz": s["z"],
                      "ex": FALLBACKS["sign_w_m"], "ey": FALLBACKS["sign_h_m"],
                      "ez": 0.04,
                      "geometry_source": "display_fallback", "element_source": s["source"]})
    for a in fls.get("assembly_points") or []:
        if a.get("x") is None:
            continue
        sz = FALLBACKS["assembly_point_size_m"]
        items.append({"name": "FLS|ASSEMBLY_POINT|%s" % a["id"], "kind": "ASSEMBLY_POINT",
                      "id": a["id"], "device_type": "OTHER", "category": "OTHER",
                      "layer": "FLS_OTHER", "render_mode": "emitted", "references": None,
                      "cx": a["x"], "cy": 0.05, "cz": a["z"],
                      "ex": sz, "ey": 0.1, "ez": sz,
                      "geometry_source": "display_fallback", "element_source": a["source"]})
    items.sort(key=lambda i: str(i["name"]))
    return items


# ---------------------------------------------------------------- تدقيق --
def audit(fls):
    """أعداد واقعية فقط. الغياب لا يُعدّ مخالفة، والمطابقة غير مُقيَّمة."""
    devs = fls.get("devices") or []
    by_type = {}
    for d in devs:
        by_type[d["device_type"]] = by_type.get(d["device_type"], 0) + 1
    by_cat = {}
    for d in devs:
        by_cat[d["device_category"]] = by_cat.get(d["device_category"], 0) + 1
    iss = fls.get("issues") or []
    return {"building_id": fls.get("building_id"), "status": fls.get("status"),
            "devices_total": len(devs), "devices_by_type": by_type,
            "devices_by_category": by_cat,
            "smoke_detectors": by_type.get("SMOKE_DETECTOR", 0),
            "heat_detectors": by_type.get("HEAT_DETECTOR", 0),
            "manual_call_points": by_type.get("MANUAL_CALL_POINT", 0),
            "alarm_devices": by_cat.get("ALARM", 0),
            "sprinklers": by_type.get("SPRINKLER_HEAD", 0),
            "extinguishers": by_type.get("FIRE_EXTINGUISHER", 0),
            "hose_reels": by_type.get("HOSE_REEL", 0),
            "represented_exits": len(fls.get("exits") or []),
            "exit_signs": len(fls.get("signs") or []),
            "fire_doors": sum(1 for o in fls.get("openings") or [] if o["fire_door"]),
            "barriers": len(fls.get("barriers") or []),
            "rated_barriers": sum(1 for b in fls.get("barriers") or []
                                  if b["rating_minutes"]["value"] is not None),
            "zones": len(fls.get("zones") or []),
            "stairs": len(fls.get("stairs") or []),
            "protected_stairs_declared": sum(1 for s in fls.get("stairs") or []
                                             if s["protection_status"] == "declared_protected"),
            "shafts": len(fls.get("shafts") or []),
            "assembly_points": len(fls.get("assembly_points") or []),
            "refuge_areas": len(fls.get("refuge_areas") or []),
            "smoke_control_entries": len(fls.get("smoke_control") or []),
            "referenced_systems": len(fls.get("systems") or []),
            "relationships": len(fls.get("relationships") or []),
            "adapted_from_mep": sum(1 for d in devs if d["origin"] == "mep_adapter"),
            "adapted_from_phase1": sum(1 for d in devs if d["origin"] == "phase1_adapter"),
            "issues": len(iss),
            "errors": sum(1 for i in iss if i.get("severity") == "ERROR"),
            "warnings": sum(1 for i in iss if i.get("severity") == "WARNING"),
            "infos": sum(1 for i in iss if i.get("severity") == "INFO"),
            "code_required": 0,
            "coverage": "NOT_EVALUATED", "compliance": "NOT_EVALUATED",
            "note": "counts of represented elements only. A missing element is NOT a violation: "
                    "absence is not a violation without a verified rule, and no coverage, "
                    "protection, adequacy or compliance is evaluated anywhere"}


# --------------------------------------------------------------- خدمات --
def element_by_id(fls, eid):
    for key in ("zones", "barriers", "openings", "exits", "stairs", "shafts", "devices",
                "systems", "signs", "assembly_points", "refuge_areas", "smoke_control"):
        for el in fls.get(key) or []:
            if el.get("id") == eid:
                return el
    for r in fls.get("relationships") or []:
        if r.get("id") == eid:
            return r
    return None


def to_world(fls, x, z):
    t = fls.get("transform") or {}
    rot = math.radians(float(t.get("rotation_deg") or 0.0))
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    ca, sa = math.cos(rot), math.sin(rot)
    return [px + x * ca - z * sa, pz + x * sa + z * ca]


def egress_facts(building, building_id="bld_0", space_id=None, rels=None):
    """يقتبس قياس مسار إخلاء موجود كواقعة. لا مقارنة بأي حدّ ولا حكم مطابقة."""
    if rels is None:
        try:
            rels = REL.build_relationships(building, building_id)
        except Exception:
            rels = []
    try:
        r = EG.find_egress(building, rels, space_id, building_id)
    except Exception:
        return None
    if not r:
        return None
    return {"space_id": space_id, "status": r.get("status"),
            "exit_id": (r.get("exit") or {}).get("id"),
            "distance_status": r.get("distance_status"),
            "walking_distance_m": r.get("distance"),
            "selection_basis": r.get("selection_basis"),
            "compliance": "NOT_EVALUATED",
            "note": "quoted from the egress and distance foundations as factual data; it is "
                    "never compared to any code travel-distance limit"}


def rule_inputs(fls):
    """حقائق معروضة كمدخلات مستقبلية للقواعد. لا قاعدة تنظيمية ولا حدّ هنا."""
    a = audit(fls)
    out = {"building": {}}
    for t in DEVICE_TYPES:
        out["building"]["fls.device.exists." + t] = bool(a["devices_by_type"].get(t))
        out["building"]["fls.device.count." + t] = a["devices_by_type"].get(t, 0)
    out["building"]["fls.device.count"] = a["devices_total"]
    out["building"]["fls.exit.count"] = a["represented_exits"]
    out["building"]["fls.zone.exists"] = a["zones"] > 0
    out["building"]["fls.zone.count"] = a["zones"]
    out["building"]["fls.fire_door.count"] = a["fire_doors"]
    for t in REFERENCED_MEP_SYSTEMS:
        out["building"]["fls.system.exists." + t] = any(
            s.get("mep_system_type") == t for s in fls.get("systems") or [])
    for o in fls.get("openings") or []:
        out[o["id"]] = {"fls.fire_door.rating": o["rating_minutes"]["value"],
                        "fls.fire_door.self_closing": o.get("self_closing"),
                        "fls.member.source": o["source"]}
    for b in fls.get("barriers") or []:
        out[b["id"]] = {"fls.barrier.rating": b["rating_minutes"]["value"],
                        "fls.barrier.type": b["barrier_type"],
                        "fls.member.source": b["source"]}
    return out


def summary(fls):
    a = audit(fls)
    return {"building_id": fls.get("building_id"),
            "compiler_version": fls.get("compiler_version"),
            "status": fls.get("status"), "status_basis": fls.get("status_basis"),
            "synthetic": fls.get("synthetic") is True, "regulatory": False,
            "devices": a["devices_total"], "exits": a["represented_exits"],
            "signs": a["exit_signs"], "fire_doors": a["fire_doors"],
            "barriers": a["barriers"], "zones": a["zones"], "stairs": a["stairs"],
            "shafts": a["shafts"], "systems": a["referenced_systems"],
            "assembly_points": a["assembly_points"], "refuge_areas": a["refuge_areas"],
            "relationships": a["relationships"], "issues": a["issues"],
            "errors": a["errors"], "warnings": a["warnings"], "infos": a["infos"],
            "code_required": 0, "coverage": "NOT_EVALUATED", "compliance": "NOT_EVALUATED",
            "note": "fire and life-safety representation and topology only — no fire design, "
                    "no simulation, no coverage or hydraulic analysis, no code compliance"}
