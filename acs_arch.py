# -*- coding: utf-8 -*-
# =============================================================================
# acs_arch.py — مصرِّف الهندسة المعمارية: من نموذج دلالي إلى عناصر معمارية.
#
# ينتج عناصر عامّة: جدار · باب · نافذة · فتحة · بلاطة · فراغ في البلاطة · سقف
# داخلي · سطح · درج · بئر مصعد · نواة · غلاف. النوع نفسه لكل أنواع المباني:
# جدار الفندق وجدار الفيلا من النموذج ذاته.
#
# مبادئ صارمة:
#   • لا هندسة إنشائية ولا ميكانيكا ولا حريق ولا مطابقة: كل شيء هنا معماري.
#   • قيمة العرض ليست قيمة هندسية: ما لم يذكره النموذج يبقى null ويُعرض
#     الاحتياط باسم render_fallback_* منفصلاً.
#   • لكل خاصية مصدر معلن (user/imported/ai_inference/system_default/unknown).
#   • الجدار المشترك يُعرَّف مرّة واحدة ويشير إليه الفراغان.
#   • الخارجية لا تُستنتج من صندوق الإحاطة وحده: الفناء الداخلي يبقى unresolved.
#   • لا تحويل شكل غير مدعوم إلى مستطيل بصمت — يُبلَّغ عنه.
#   • المصرِّف حتمي: نفس النموذج ⇒ نفس المعرّفات والنتائج.
# =============================================================================
import json
import os
import re
import acs_polygon as POLY

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_arch.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
COMPILER_VERSION = SPEC["compiler_version"]
ELEMENT_TYPES = tuple(SPEC["element_types"])
PROVENANCE = tuple(SPEC["provenance_values"])
EXPOSURE = tuple(SPEC["exposure_values"])
EVIDENCE = tuple(SPEC["evidence_status"])
LEVEL_KINDS = tuple(SPEC["level_kinds"])
HOST_STATUS = tuple(SPEC["host_status"])
DEFAULTS = SPEC["defaults"]
ISSUE_CODES = tuple(SPEC["geometry_issue_codes"])

_EPS = 1e-6
_PROBE = 0.05


def _q(v):
    """تقريب موحّد لمفاتيح الهندسة فقط — لا يُستعمل في أي قيمة منشورة."""
    return round(float(v), 6) + 0.0


def _rect(room):
    rc = room.get("rect")
    if not rc or len(rc) < 4:
        return None
    return [float(v) for v in rc[:4]]


def _shape_supported(room):
    if "polygon" in room:
        try:
            POLY.room_ring(room)
            return not (room.get("shape") or room.get("vertices"))
        except ValueError:
            return False
    return not (room.get("polygon") or room.get("shape") or room.get("vertices"))


def _space_id(bid, tmpl, room, i):
    return room.get("space_id") or "%s.%s.%s" % (bid, tmpl, room.get("id") or ("sp_%d" % i))


def _edge_segment(edge, rc):
    """حافة مستطيل كمقطع محلي: (محور، ثابت، بداية، نهاية، اتجاه الفراغ)."""
    x, z, w, d = rc
    e = str(edge or "N").upper()[:1]
    if e == "N":
        return ("x", z, x, x + w, +1)         # الفراغ إلى z الأكبر
    if e == "S":
        return ("x", z + d, x, x + w, -1)
    if e == "W":
        return ("z", x, z, z + d, +1)         # الفراغ إلى x الأكبر
    return ("z", x + w, z, z + d, -1)


def _open_u(edge, rc, off):
    x, z = rc[0], rc[1]
    e = str(edge or "N").upper()[:1]
    return (x + float(off)) if e in ("N", "S") else (z + float(off))


def _val(stated, default, source_hint=None):
    """قيمة دلالية + احتياط عرض + مصدر. الاحتياط لا يصير حقيقة هندسية أبداً."""
    if stated is None:
        return {"value": None, "render_fallback": default, "source": "unknown"}
    return {"value": float(stated), "render_fallback": default,
            "source": source_hint or "imported"}


def _levels(building, bid):
    out = []
    fh = building.get("floor_height")
    for l in (building.get("levels") or []):
        idx = int(l.get("index", 0))
        tmpl = l.get("template")
        kind = l.get("kind")
        if not kind:
            t = str(tmpl or "").lower()
            kind = "roof" if "roof" in t or "سطح" in str(l.get("name") or "") else (
                "technical" if ("tech" in t or "mech" in t) else "occupied")
        elev = l.get("elevation")
        elev_src = "imported" if elev is not None else ("system_default" if fh is not None else "unknown")
        if elev is None and fh is not None:
            elev = idx * float(fh)
        out.append({"id": l.get("id") or ("%s.flr_%d" % (bid, idx)), "index": idx,
                    "template": tmpl, "name": l.get("name"), "kind": kind,
                    "elevation_m": float(elev) if elev is not None else None,
                    "elevation_source": elev_src,
                    "auto_added": l.get("auto") is True})
    out.sort(key=lambda l: (l["index"], str(l["id"])))
    return out


def _rooms_of(building, tmpl, bid):
    rooms = []
    for i, r in enumerate(((building.get("floors") or {}).get(tmpl) or {}).get("rooms") or []):
        rooms.append((_space_id(bid, tmpl, r, i), r, i))
    return rooms


# ------------------------------------------------------------- الجدران --
def _polygon_wall_segments(rooms):
    groups = {}
    for sid, room, _ in rooms:
        if not _shape_supported(room) or _rect(room) is None:
            continue
        ring = POLY.room_ring(room)
        winding = 1 if POLY.signed_area(ring) > 0 else -1
        for index, (a, b) in enumerate(POLY.edges(ring)):
            f = POLY.segment_frame(a, b)
            key = (f["axis"], _q(f["fixed"]), *map(_q, f["direction"]))
            interior = [-(b[1]-a[1])*winding, (b[0]-a[0])*winding]
            side = 1 if sum(interior[i]*f["normal"][i] for i in (0,1)) > 0 else -1
            entry = {"u0": f["u0"], "u1": f["u1"], "space": sid,
                     "edge": index, "side": side, "height": room.get("wall_h")}
            groups.setdefault(key, {"frame": f, "items": []})["items"].append(entry)
    walls = []
    for key in sorted(groups):
        group = groups[key]; f, items = group["frame"], group["items"]
        cuts = sorted({_q(u) for it in items for u in (it["u0"],it["u1"])})
        for a,b in zip(cuts,cuts[1:]):
            if b-a <= _EPS:
                continue
            owners = [it for it in items if it["u0"] <= a+_EPS and it["u1"] >= b-_EPS]
            if not owners:
                continue
            heights = [it["height"] for it in owners if it["height"] is not None]
            walls.append({"axis": f["axis"], "fixed": f["fixed"], "u0": a, "u1": b,
                          "direction": f["direction"], "normal": f["normal"],
                          "spaces": sorted({it["space"] for it in owners}),
                          "sides": {it["space"]:it["side"] for it in owners},
                          "edges": {it["space"]:it["edge"] for it in owners},
                          "height_stated": max(heights) if heights else None})
    return walls


def _polygon_exposure(wall, rooms, unsupported):
    if len(wall["spaces"]) > 1:
        return "interior", "confirmed", "bounded_by_two_spaces"
    side = wall["sides"][wall["spaces"][0]]
    point = POLY.frame_point(wall, (wall["u0"]+wall["u1"])/2)
    probe = [point[i]-side*_PROBE*wall["normal"][i] for i in (0,1)]
    if any(_shape_supported(r) and _rect(r) is not None
           and POLY.contains_point(POLY.room_ring(r),probe) for _,r,_ in rooms):
        return "interior", "inferred", "opposite_side_inside_another_space"
    if _point_in_rects(*probe, unsupported):
        return "unresolved", "unresolved", "opposite_side_near_a_space_with_unsupported_outline"
    bbox = _bbox([_rect(r) for _,r,_ in rooms if _rect(r) is not None])
    if bbox and bbox[0]-_EPS <= probe[0] <= bbox[2]+_EPS and bbox[1]-_EPS <= probe[1] <= bbox[3]+_EPS:
        return "unresolved", "unresolved", "opposite_side_is_void_inside_the_footprint"
    return "exterior", "inferred", "opposite_side_outside_declared_polygon_union"


def _wall_segments(rooms, wall_h_default, thickness):
    """يبني مقاطع جدران أوّلية: كل حدّ مشترك يُقسَّم عند كل نقطة انكسار،
    فيُعرَّف الجدار المشترك مرّة واحدة ويشير إليه الفراغان."""
    if any("polygon" in r for _, r, _ in rooms):
        return _polygon_wall_segments(rooms)
    groups = {}
    for sid, room, _ in rooms:
        rc = _rect(room)
        if rc is None or not _shape_supported(room):
            continue
        h = room.get("wall_h")
        for e in ("N", "S", "E", "W"):
            axis, fixed, u0, u1, side = _edge_segment(e, rc)
            key = (axis, _q(fixed))
            groups.setdefault(key, []).append(
                {"u0": _q(u0), "u1": _q(u1), "space": sid, "edge": e, "side": side,
                 "height": h, "rect": rc})
    walls = []
    for (axis, fixed), items in groups.items():
        cuts = sorted({v for it in items for v in (it["u0"], it["u1"])})
        for a, b in zip(cuts, cuts[1:]):
            if b - a <= _EPS:
                continue
            owners = [it for it in items if it["u0"] <= a + _EPS and it["u1"] >= b - _EPS]
            if not owners:
                continue
            heights = [o["height"] for o in owners if o["height"] is not None]
            walls.append({"axis": axis, "fixed": fixed, "u0": a, "u1": b,
                          "spaces": sorted({o["space"] for o in owners}),
                          "sides": {o["space"]: o["side"] for o in owners},
                          "edges": {o["space"]: o["edge"] for o in owners},
                          "height_stated": max(heights) if heights else None})
    # ترتيب حتمي حسب هندسة الجدار نفسه، لا حسب ترتيب الغرف
    walls.sort(key=lambda w: (w["axis"], w["fixed"], w["u0"], w["u1"]))
    return walls


def _point_in_rects(px, pz, rects):
    for rc in rects:
        if rc[0] - _EPS <= px <= rc[0] + rc[2] + _EPS and rc[1] - _EPS <= pz <= rc[1] + rc[3] + _EPS:
            return True
    return False


def _classify_exposure(wall, rects, unsupported, bbox):
    """داخلي إن حدّه فراغان. وإلا نفحص الجانب الآخر:
    داخل فراغ آخر ⇒ داخلي · بجوار فراغ شكله غير مدعوم ⇒ unresolved (لا نعامل
    مستطيله المعلن كأنه حدوده) · خارج المسطح كلّه ⇒ خارجي (استنتاج) ·
    داخل صندوق الإحاطة لكن خارج كل الفراغات ⇒ unresolved (قد يكون فناءً)."""
    if len(wall["spaces"]) > 1:
        return "interior", "confirmed", "bounded_by_two_spaces"
    sid = wall["spaces"][0]
    side = wall["sides"][sid]
    mid = (wall["u0"] + wall["u1"]) / 2.0
    if wall["axis"] == "x":
        px, pz = mid, wall["fixed"] - side * _PROBE
    else:
        px, pz = wall["fixed"] - side * _PROBE, mid
    if _point_in_rects(px, pz, rects):
        return "interior", "inferred", "opposite_side_inside_another_space"
    if _point_in_rects(px, pz, unsupported):
        # الجانب الآخر يقع في المستطيل المعلن لفراغ شكله غير مدعوم: لا نجزم
        return "unresolved", "unresolved", "opposite_side_near_a_space_with_unsupported_outline"
    if bbox and (bbox[0] - _EPS <= px <= bbox[2] + _EPS
                 and bbox[1] - _EPS <= pz <= bbox[3] + _EPS):
        # داخل مسطح الدور لكن خارج كل الفراغات: قد يكون فناءً أو بهواً — لا نجزم
        return "unresolved", "unresolved", "opposite_side_is_void_inside_the_footprint"
    return "exterior", "inferred", "opposite_side_outside_the_level_footprint"


def _bbox(rects):
    if not rects:
        return None
    return [min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)]


# ------------------------------------------------------------ الفتحات --
def _openings_of(room, sid, kind):
    out = []
    src = room.get("doors") if kind == "door" else room.get("windows")
    for i, o in enumerate(src or []):
        rc = _rect(room)
        if rc is None:
            continue
        frame = None
        if "polygon" in room:
            edge_index = None
            if _shape_supported(room):
                try:
                    edge_index = POLY.edge_index(room, o)
                except ValueError:
                    pass  # retained below as an unresolved opening, never hosted on a guessed edge
            if edge_index is not None:
                frame = POLY.segment_frame(*POLY.edges(POLY.room_ring(room))[edge_index])
        axis, fixed, u0, u1, side = _edge_segment(o.get("edge"), rc)
        uc = _open_u(o.get("edge"), rc, o.get("offset") or 0)
        if frame is not None:
            axis, fixed = frame["axis"],frame["fixed"]
            uc = frame["first_u"]+frame["sense"]*float(o.get("offset") or 0)
        w = o.get("width")
        default_w = DEFAULTS["door_width_m"] if kind == "door" else DEFAULTS["window_width_m"]
        default_h = DEFAULTS["door_height_m"] if kind == "door" else DEFAULTS["window_height_m"]
        el = {"id": "%s.%s_%d" % (sid, kind, i), "type": kind.upper(), "space_id": sid,
              "axis": axis, "fixed": fixed, "u_center": uc,
              "edge": str(o.get("edge") or "N").upper()[:1],
              "offset_stated": o.get("offset") is not None,
              "width_m": _val(w, default_w),
              "height_m": _val(o.get("height"), default_h),
              "host_wall_id": None, "host_status": "unresolved", "host_note": None}
        if kind == "door":
            # العرض الحرّ يبقى منفصلاً عن العرض الاسمي — ولا يُشتق منه
            cw = o.get("clear_width_m")
            el["clear_width_m"] = {"value": float(cw) if cw is not None else None,
                                   "render_fallback": None,
                                   "source": "imported" if cw is not None else "unknown"}
            el["hinge_side"] = o.get("hinge_side") or None
            el["swing_direction"] = o.get("swing_direction") or None
            el["swing_angle_deg"] = o.get("swing_angle_deg")
            el["swing_status"] = "specified" if (o.get("hinge_side") or o.get("swing_direction")) \
                else "not_specified"
            el["exit_flag"] = o.get("exit") is True
            el["destination"] = o.get("destination")
        else:
            sill = o.get("sill")
            el["sill_m"] = _val(sill, DEFAULTS["window_sill_m"])
        el["source"] = o.get("source") or "unknown"
        if "polygon" in room:
            el["edge"] = None
            el["edge_index"] = edge_index
            el["boundary_basis"] = "polygon_edges"
            el["position_resolved"] = frame is not None
            if frame is not None:
                el["direction"],el["normal"] = frame["direction"],frame["normal"]
                el["center"] = [_q(v) for v in POLY.frame_point(frame,uc)]
        out.append(el)
    return out


def _host(opening, walls):
    if opening.get("position_resolved") is False:
        return None, "unresolved", "polygon opening has no valid edge_index"
    w = opening["width_m"]["value"]
    if w is None:
        w = opening["width_m"]["render_fallback"]
    a, b = opening["u_center"] - w / 2.0, opening["u_center"] + w / 2.0
    cands = [x for x in walls if x["axis"] == opening["axis"]
             and abs(x["fixed"] - opening["fixed"]) <= _EPS
             and (opening.get("direction") is None or
                  all(abs(x.get("direction", opening["direction"])[i]-opening["direction"][i]) <= _EPS for i in (0,1)))
             and x["u1"] > a + _EPS and x["u0"] < b - _EPS]
    if not cands:
        return None, "unresolved", "no wall segment hosts this opening"
    host = None
    for c in cands:
        if c["u0"] - _EPS <= opening["u_center"] <= c["u1"] + _EPS:
            host = c
            break
    host = host or cands[0]
    if host["u0"] - _EPS <= a and b <= host["u1"] + _EPS:
        return host, "resolved", None
    if len(cands) > 1:
        return host, "partial", "opening spans %d wall segments" % len(cands)
    return host, "partial", "opening extends beyond the single wall segment that hosts it"


# ------------------------------------------------------- النوى الرأسية --
_STAIR_WORDS = ("stair", "درج", "سلم")
_LIFT_WORDS = ("elevator", "lift", "مصعد")


def _core_kind(obj):
    k = str(obj.get("kind") or obj.get("name") or "").lower()
    if any(w in k for w in _STAIR_WORDS):
        return "STAIR"
    if any((re.search(r"(^|[^a-z])lift([^a-z]|$)", k) if w == "lift" else w in k)
           for w in _LIFT_WORDS):
        return "ELEVATOR_SHAFT"
    return None


def _cores(building, bid, levels):
    """نواة رأسية = عنصر درج/مصعد له موضع مستقر ومستويات يخدمها."""
    by_pos = {}
    for lvl in levels:
        for sid, room, _ in _rooms_of(building, lvl["template"], bid):
            rc = _rect(room)
            if rc is None:
                continue
            for j, obj in enumerate(room.get("objects") or []):
                kind = _core_kind(obj)
                if kind is None:
                    continue
                stated = obj.get("x") is not None and obj.get("z") is not None
                px = rc[0] + float(obj.get("x")) if stated else rc[0] + rc[2] / 2.0
                pz = rc[1] + float(obj.get("z")) if stated else rc[1] + rc[3] / 2.0
                fw, fd = (DEFAULTS["stair_footprint_m"] if kind == "STAIR"
                          else DEFAULTS["elevator_footprint_m"])
                w = obj.get("w")
                d = obj.get("d")
                key = (kind, _q(px), _q(pz))
                entry = by_pos.setdefault(key, {
                    "type": kind, "x": px, "z": pz,
                    "position_source": "imported" if stated else "system_default",
                    "footprint_w_m": _val(w, fw), "footprint_d_m": _val(d, fd),
                    "served_levels": [], "spaces": [], "via": []})
                entry["served_levels"].append(lvl["index"])
                entry["spaces"].append(sid)
                entry["via"].append("%s.%s_%d" % (sid, "stairs" if kind == "STAIR" else "elevator", j))
    cores = []
    for n, key in enumerate(sorted(by_pos)):
        c = by_pos[key]
        c["served_levels"] = sorted(set(c["served_levels"]))
        c["spaces"] = sorted(set(c["spaces"]))
        c["id"] = "%s.core_%d" % (bid, n)
        cores.append(c)
    return cores


# ------------------------------------------------------------ التصريف --
def compile_architecture(building, building_id="bld_0", position=None, rotation_deg=0.0):
    """يبني نموذج العناصر المعمارية من النموذج الدلالي. حتمي وقابل للتكرار."""
    bid = building_id
    levels = _levels(building, bid)
    wall_t = building.get("wall_t")
    wall_t_src = building.get("wall_t_source") or ("system_default" if wall_t is not None else "unknown")
    thickness = _val(wall_t, DEFAULTS["wall_thickness_m"], wall_t_src)
    wall_h_default = building.get("wall_h")

    out = {"schema": SCHEMA, "compiler_version": COMPILER_VERSION, "building_id": bid,
           "transform": {"position": position or {"x": 0.0, "z": 0.0},
                         "rotation_deg": float(rotation_deg or 0.0),
                         "applied": "local coordinates; world transform is applied on read"},
           "levels": levels, "walls": [], "openings": [], "slabs": [], "voids": [],
           "ceilings": [], "roofs": [], "cores": [], "spaces": [], "envelope": None,
           "approximations": [], "issues": []}

    for lvl in levels:
        rooms = _rooms_of(building, lvl["template"], bid)
        rects, unsupported, all_rects = [], [], []
        polygon_level = any("polygon" in room for _,room,_ in rooms)
        polygons = []
        for sid, room, i in rooms:
            rc = _rect(room)
            supported = rc is not None and _shape_supported(room)
            # هوية النسخة الفيزيائية = هوية عقدة الملاحة نفسها (space@level):
            # قالب دور واحد على مستويين هو غرفتان حقيقيتان لا غرفة واحدة.
            out["spaces"].append({
                "id": "%s@%s" % (sid, lvl["index"]), "space_id": sid,
                "level_id": lvl["id"], "level_index": lvl["index"],
                "name": room.get("id"), "rect": rc,
                "boundary_basis": ("polygon_edges" if "polygon" in room else "rectangle_edges") if supported else "unsupported_shape",
                "area_m2": (abs(POLY.signed_area(POLY.room_ring(room))) if "polygon" in room else rc[2]*rc[3]) if supported else None,
                "wall_height_m": _val(room.get("wall_h") if room.get("wall_h") is not None
                                      else wall_h_default, DEFAULTS["wall_height_m"],
                                      "imported" if room.get("wall_h") is not None else
                                      ("imported" if wall_h_default is not None else "unknown"))})
            if supported and "polygon" in room:
                out["spaces"][-1]["polygon"] = POLY.room_ring(room)
            if supported and polygon_level:
                polygons.append(POLY.room_ring(room))
            if rc is not None:
                all_rects.append(rc)
                if supported:
                    rects.append(rc)
                else:
                    unsupported.append(rc)
            if not supported and rc is not None:
                out["approximations"].append({"space_id": sid, "reason": "SPACE_SHAPE_UNSUPPORTED",
                                              "detail": "a non-rectangular outline is present; "
                                                        "it was NOT approximated as a rectangle"})
                out["issues"].append({"code": "SPACE_SHAPE_UNSUPPORTED", "subject": sid})
        bbox = _bbox(all_rects)

        segs = _wall_segments(rooms, wall_h_default, thickness)
        lvl_walls = []
        for n, s in enumerate(segs):
            exposure, status, basis = (_polygon_exposure(s, rooms, unsupported) if polygon_level
                                       else _classify_exposure(s, rects, unsupported, bbox))
            # إعلان الفراغ الخارجي لا يُبطل جداراً يفصل فراغين — الحقيقة الهندسية أقوى
            if len(s["spaces"]) == 1:
                room = next((r for (i2, r, _) in rooms if i2 == s["spaces"][0]), None)
                if room is not None and room.get("exterior") is True:
                    exposure, status, basis = "exterior", "confirmed", "declared_by_model"
            h = s["height_stated"] if s["height_stated"] is not None else wall_h_default
            w = {"id": "%s.wall_%d" % (lvl["id"], n), "type": "WALL", "building_id": bid,
                 "level_id": lvl["id"], "level_index": lvl["index"],
                 "axis": s["axis"], "fixed": s["fixed"], "u0": s["u0"], "u1": s["u1"],
                 "length_m": s["u1"] - s["u0"],
                 "start": ({"x": s["u0"], "z": s["fixed"]} if s["axis"] == "x"
                           else {"x": s["fixed"], "z": s["u0"]}),
                 "end": ({"x": s["u1"], "z": s["fixed"]} if s["axis"] == "x"
                         else {"x": s["fixed"], "z": s["u1"]}),
                 "height_m": _val(h, DEFAULTS["wall_height_m"],
                                  "imported" if h is not None else "unknown"),
                 "thickness_m": dict(thickness),
                 "spaces": s["spaces"], "shared": len(s["spaces"]) > 1,
                 "exposure": exposure, "exposure_status": status, "exposure_basis": basis,
                 "openings": []}
            if polygon_level:
                w["direction"], w["normal"] = s["direction"],s["normal"]
                w["start"] = dict(zip(("x","z"), map(_q,POLY.frame_point(s,s["u0"]))))
                w["end"] = dict(zip(("x","z"), map(_q,POLY.frame_point(s,s["u1"]))))
            lvl_walls.append(w)
            out["walls"].append(w)

        for sid, room, i in rooms:
            for kind in ("door", "window"):
                for op in _openings_of(room, sid, kind):
                    op["building_id"] = bid
                    op["level_id"] = lvl["id"]
                    op["level_index"] = lvl["index"]
                    # opening_ref هو المرجع الدلالي الذي تستعمله العلاقات (via)
                    op["opening_ref"] = op["id"]
                    op["id"] = "%s@%s" % (op["id"], lvl["index"])
                    host, hstatus, note = _host(op, lvl_walls)
                    op["host_wall_id"] = host["id"] if host else None
                    op["host_status"] = hstatus
                    op["host_note"] = note
                    if host:
                        host["openings"].append(op["id"])
                    out["openings"].append(op)

        if bbox:
            slab = {"id": "%s.slab" % lvl["id"], "type": "FLOOR_SLAB", "building_id": bid,
                    "level_id": lvl["id"], "level_index": lvl["index"],
                    "outline": [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]],
                    "outline_basis": "bounding_box_of_spaces",
                    "elevation_m": lvl["elevation_m"], "elevation_source": lvl["elevation_source"],
                    "thickness_m": _val(building.get("slab_t"), DEFAULTS["slab_thickness_m"],
                                        "imported" if building.get("slab_t") is not None
                                        else "system_default"),
                    "structural": False, "note": "architectural slab only — not a structural design"}
            if polygon_level:
                slab["polygons"] = polygons
                slab["outline_basis"] = "polygon_union" if not unsupported else "partial_polygon_union"
            out["slabs"].append(slab)
            covered = sum(r[2] * r[3] for r in rects)
            if not polygon_level and covered < (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) - 1e-6:
                out["approximations"].append(
                    {"level_id": lvl["id"], "reason": "SLAB_OUTLINE_IS_BOUNDING_BOX",
                     "detail": "spaces do not tile the level footprint; the slab outline is their "
                               "bounding box and is reported as an approximation"})

        if lvl["kind"] == "roof":
            out["roofs"].append({"id": "%s.roof" % lvl["id"], "type": "ROOF", "building_id": bid,
                                 "level_id": lvl["id"], "level_index": lvl["index"],
                                 "form": "flat", "outline": (out["slabs"][-1]["outline"]
                                                             if out["slabs"] else None),
                                 "elevation_m": lvl["elevation_m"],
                                 "source": "system_default" if lvl["auto_added"] else "imported",
                                 "occupied_floor": False,
                                 "note": "a roof level is never an occupied floor"})
        else:
            for sid, room, i in rooms:
                rc = _rect(room)
                if rc is None:
                    continue
                h = room.get("wall_h") if room.get("wall_h") is not None else wall_h_default
                out["ceilings"].append(
                    {"id": "%s.ceiling_%s" % (lvl["id"], room.get("id") or sid.split(".")[-1]),
                     "type": "CEILING", "building_id": bid, "level_id": lvl["id"],
                     "space_id": sid, "outline": rc,
                     "elevation_m": (lvl["elevation_m"] + float(h))
                                    if (lvl["elevation_m"] is not None and h is not None) else None,
                     "thickness_m": {"value": None, "render_fallback": 0.05, "source": "unknown"}})

    out["cores"] = _cores(building, bid, levels)
    # فراغ في البلاطة عند كل مستوى تخترقه نواة — الدرج لا يمرّ عبر بلاطة صمّاء
    vn = 0
    for core in out["cores"]:
        served = core["served_levels"]
        if not served:
            out["issues"].append({"code": "CORE_WITHOUT_SERVED_LEVELS", "subject": core["id"]})
            continue
        fw = core["footprint_w_m"]["value"] or core["footprint_w_m"]["render_fallback"]
        fd = core["footprint_d_m"]["value"] or core["footprint_d_m"]["render_fallback"]
        for lvl in levels:
            if lvl["index"] <= min(served) or lvl["index"] > max(served):
                continue
            out["voids"].append({"id": "%s.void_%d" % (lvl["id"], vn), "type": "FLOOR_OPENING",
                                 "building_id": bid, "level_id": lvl["id"],
                                 "level_index": lvl["index"], "core_id": core["id"],
                                 "core_type": core["type"],
                                 "rect": [core["x"] - fw / 2.0, core["z"] - fd / 2.0, fw, fd],
                                 "footprint_source": core["position_source"],
                                 "note": "architectural void only — no structural framing implied"})
            vn += 1
        if core["position_source"] != "imported":
            out["issues"].append({"code": "CORE_POSITION_NOT_STATED", "subject": core["id"]})

    # After cores: canonical polygon plates and finishes retain their real voids.
    for slab in out["slabs"]:
        if "polygons" not in slab:
            continue
        holes = [POLY.rect_ring(v["rect"]) for v in out["voids"] if v["level_id"] == slab["level_id"]]
        slab["cells"] = POLY.cells(slab["polygons"],holes)
        slab["area_m2"] = sum(abs(POLY.signed_area(c)) for c in slab["cells"])
        for roof in out["roofs"]:
            if roof["level_id"] == slab["level_id"]:
                roof["polygons"],roof["cells"] = slab["polygons"],slab["cells"]
                roof["outline_basis"] = slab["outline_basis"]
        for ceiling in out["ceilings"]:
            if ceiling["level_id"] != slab["level_id"]:
                continue
            space = next(s for s in out["spaces"] if s["space_id"] == ceiling["space_id"] and s["level_id"] == slab["level_id"])
            if space["boundary_basis"] == "unsupported_shape":
                continue
            ring = space.get("polygon") or POLY.rect_ring(space["rect"])
            ceiling["polygons"],ceiling["cells"] = [ring],POLY.cells([ring],holes)
            ceiling["outline_basis"] = "polygon_union"
    ext = [w for w in out["walls"] if w["exposure"] == "exterior"]
    ext_open = [o for o in out["openings"]
                if any(o["id"] in w["openings"] for w in ext)]
    out["envelope"] = {
        "id": "%s.envelope" % bid, "type": "ENVELOPE", "building_id": bid,
        "exterior_walls": [w["id"] for w in ext],
        "unresolved_walls": [w["id"] for w in out["walls"] if w["exposure"] == "unresolved"],
        "external_openings": [o["id"] for o in ext_open],
        "roof_boundary": out["roofs"][-1]["outline"] if out["roofs"] else
                         (out["slabs"][-1]["outline"] if out["slabs"] else None),
        "ground_interface": out["slabs"][0]["outline"] if out["slabs"] else None,
        "note": "derived envelope for later facade/exposure work — no analysis is performed here"}
    if out["slabs"] and "polygons" in out["slabs"][0]:
        out["envelope"]["ground_polygons"] = out["slabs"][0]["polygons"]
    if out["slabs"] and "polygons" in out["slabs"][-1]:
        out["envelope"]["roof_polygons"] = out["slabs"][-1]["polygons"]
    out["issues"].extend(validate_architecture(out))
    return out


# ------------------------------------------------------------ التحقّق --
def validate_architecture(arch):
    """فحوص سلامة نموذج معماري — ليست فحوص كود بناء إطلاقاً."""
    issues = []
    for w in arch.get("walls") or []:
        if w["length_m"] <= _EPS:
            issues.append({"code": "WALL_ZERO_LENGTH", "subject": w["id"]})
        t = w["thickness_m"]["value"]
        if t is not None and t <= 0:
            issues.append({"code": "WALL_NEGATIVE_THICKNESS", "subject": w["id"]})
    seen = {}
    for w in arch.get("walls") or []:
        k = (w["level_id"], w["axis"], _q(w["fixed"]), _q(w["u0"]), _q(w["u1"]))
        if w.get("direction") is not None:
            k += tuple(map(_q,w["direction"]))
        if k in seen:
            issues.append({"code": "WALL_DUPLICATE_OVERLAP", "subject": w["id"], "other": seen[k]})
        seen[k] = w["id"]
    walls = {w["id"]: w for w in (arch.get("walls") or [])}
    for o in arch.get("openings") or []:
        if o["host_status"] == "unresolved":
            issues.append({"code": "OPENING_HOST_UNRESOLVED", "subject": o["id"]})
            continue
        host = walls.get(o["host_wall_id"])
        if host is None:
            issues.append({"code": "OPENING_HOST_UNRESOLVED", "subject": o["id"]})
            continue
        w = o["width_m"]["value"] or o["width_m"]["render_fallback"]
        a, b = o["u_center"] - w / 2.0, o["u_center"] + w / 2.0
        if a < host["u0"] - _EPS or b > host["u1"] + _EPS:
            # أعرض من مضيفه شيء، ومنزاح عن طرفه شيء آخر — لا نخلط بينهما
            wider = w > (host["u1"] - host["u0"]) + _EPS
            issues.append({"code": "OPENING_WIDER_THAN_HOST" if wider else "OPENING_OUTSIDE_HOST",
                           "subject": o["id"], "host": host["id"]})
        wh = host["height_m"]["value"] or host["height_m"]["render_fallback"]
        oh = o["height_m"]["value"] or o["height_m"]["render_fallback"]
        if o["type"] == "WINDOW":
            sill = o["sill_m"]["value"] if o["sill_m"]["value"] is not None else o["sill_m"]["render_fallback"]
            if sill < -_EPS:
                issues.append({"code": "WINDOW_BELOW_FLOOR", "subject": o["id"]})
            if sill + oh > wh + _EPS:
                issues.append({"code": "WINDOW_ABOVE_WALL_HEIGHT", "subject": o["id"]})
        elif oh > wh + _EPS:
            issues.append({"code": "DOOR_TALLER_THAN_WALL", "subject": o["id"]})
    by_level = {}
    for s in arch.get("spaces") or []:
        by_level.setdefault(s["level_id"], []).append(s)
    for lid, spaces in by_level.items():
        for i in range(len(spaces)):
            for j in range(i + 1, len(spaces)):
                a, b = spaces[i].get("rect"), spaces[j].get("rect")
                if not a or not b:
                    continue
                if spaces[i].get("polygon") or spaces[j].get("polygon"):
                    pa,pb = spaces[i].get("polygon") or POLY.rect_ring(a), spaces[j].get("polygon") or POLY.rect_ring(b)
                    aa,ab = abs(POLY.signed_area(pa)),abs(POLY.signed_area(pb))
                    union = sum(abs(POLY.signed_area(c)) for c in POLY.cells([pa,pb]))
                    overlap = max(0,aa+ab-union)
                    if overlap > 1e-6:
                        inside = abs(overlap-min(aa,ab)) <= 1e-6
                        issues.append({"code":"SPACE_CONTAINED" if inside else "SPACE_OVERLAP",
                                       "subject":spaces[i]["id"],"other":spaces[j]["id"],
                                       "overlap_m2":round(overlap,6)})
                    continue
                ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
                oz = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                if ox > 1e-3 and oz > 1e-3:
                    inside = ((a[0] >= b[0] - _EPS and a[1] >= b[1] - _EPS
                               and a[0] + a[2] <= b[0] + b[2] + _EPS
                               and a[1] + a[3] <= b[1] + b[3] + _EPS)
                              or (b[0] >= a[0] - _EPS and b[1] >= a[1] - _EPS
                                  and b[0] + b[2] <= a[0] + a[2] + _EPS
                                  and b[1] + b[3] <= a[1] + a[3] + _EPS))
                    # احتواء كامل نمط تخطيط مشروع (منطقة داخل غلاف)، لا تداخل خاطئ
                    issues.append({"code": "SPACE_CONTAINED" if inside else "SPACE_OVERLAP",
                                   "subject": spaces[i]["id"], "other": spaces[j]["id"],
                                   "overlap_m2": round(ox * oz, 6)})
    lv = sorted([l for l in (arch.get("levels") or []) if l["elevation_m"] is not None],
                key=lambda l: l["index"])
    for a, b in zip(lv, lv[1:]):
        if b["elevation_m"] <= a["elevation_m"] + _EPS:
            issues.append({"code": "LEVEL_ELEVATION_INCONSISTENT", "subject": b["id"],
                           "below": a["id"]})
    cores = {c["id"]: c for c in (arch.get("cores") or [])}
    voided = {v["core_id"] for v in (arch.get("voids") or [])}
    for cid, c in cores.items():
        if len(c["served_levels"]) > 1 and cid not in voided:
            issues.append({"code": "VOID_MISSING_FOR_CORE", "subject": cid})
    return issues


# ------------------------------------------------------------- خدمات --
def element_by_id(arch, eid):
    for key in ("walls", "openings", "slabs", "voids", "ceilings", "roofs", "cores", "spaces"):
        for el in arch.get(key) or []:
            if el.get("id") == eid:
                return el
    if (arch.get("envelope") or {}).get("id") == eid:
        return arch["envelope"]
    return None


def opening_by_ref(arch, ref, level_index=None):
    """يقبل الهوية الكاملة (ref@level) أو المرجع الدلالي (ref) كما تستعمله العلاقات.
    بلا مستوى محدّد: أوّل نسخة بترتيب المستويات — الهندسة نفسها في كل نسخ القالب."""
    if ref is None:
        return None
    for op in arch.get("openings") or []:
        if op.get("id") == ref and (level_index is None or op.get("level_index") == level_index):
            return op
    for op in arch.get("openings") or []:
        if op.get("opening_ref") == ref and (level_index is None
                                             or op.get("level_index") == level_index):
            return op
    return None


def opening_anchor(arch, opening_id, level_index=None):
    """مرساة الفتحة من هندسة الجدار المضيف — أدقّ مصدر متاح لقياس المسافة."""
    op = opening_by_ref(arch, opening_id, level_index)
    if op is None or op.get("type") not in ("DOOR", "WINDOW"):
        return None
    if op.get("position_resolved") is False:
        return None
    if op.get("center") is not None:
        return list(op["center"])
    if op["axis"] == "x":
        return [op["u_center"], op["fixed"]]
    return [op["fixed"], op["u_center"]]


def shared_wall_between(arch, space_a, space_b):
    for w in arch.get("walls") or []:
        if w["shared"] and space_a in w["spaces"] and space_b in w["spaces"]:
            return w
    return None


def door_connects_confirmed(arch, opening_id, level_index=None):
    """باب مستضاف على جدار يفصل فراغين بالضبط = دليل اتصال مؤكَّد.
    يبقى None لأي حالة أقلّ من ذلك — الاستنتاج الهندسي القديم لا يُستبدل به."""
    op = opening_by_ref(arch, opening_id, level_index)
    if op is None or op.get("type") != "DOOR" or op.get("host_status") != "resolved":
        return None
    host = element_by_id(arch, op.get("host_wall_id"))
    if host is None or not host.get("shared") or len(host["spaces"]) != 2:
        return None
    return {"wall_id": host["id"], "spaces": list(host["spaces"]),
            "opening_id": op["id"], "opening_ref": op.get("opening_ref"),
            "level_id": op.get("level_id"), "level_index": op.get("level_index"),
            "basis": "door_hosted_on_a_wall_shared_by_exactly_two_spaces"}


def to_world(arch, x, z):
    """تحويل محلي→عالمي: إزاحة المبنى ودورانه داخل إحداثيات الموقع."""
    import math
    t = arch.get("transform") or {}
    rot = math.radians(float(t.get("rotation_deg") or 0.0))
    px = float((t.get("position") or {}).get("x") or 0.0)
    pz = float((t.get("position") or {}).get("z") or 0.0)
    ca, sa = math.cos(rot), math.sin(rot)
    return [px + x * ca - z * sa, pz + x * sa + z * ca]


def summary(arch):
    return {"building_id": arch.get("building_id"), "compiler_version": arch.get("compiler_version"),
            "levels": len(arch.get("levels") or []), "spaces": len(arch.get("spaces") or []),
            "walls": len(arch.get("walls") or []),
            "shared_walls": sum(1 for w in (arch.get("walls") or []) if w["shared"]),
            "exterior_walls": sum(1 for w in (arch.get("walls") or []) if w["exposure"] == "exterior"),
            "unresolved_walls": sum(1 for w in (arch.get("walls") or []) if w["exposure"] == "unresolved"),
            "openings": len(arch.get("openings") or []),
            "unresolved_openings": sum(1 for o in (arch.get("openings") or [])
                                       if o["host_status"] == "unresolved"),
            "slabs": len(arch.get("slabs") or []), "voids": len(arch.get("voids") or []),
            "ceilings": len(arch.get("ceilings") or []), "roofs": len(arch.get("roofs") or []),
            "cores": len(arch.get("cores") or []),
            "approximations": len(arch.get("approximations") or []),
            "issues": len(arch.get("issues") or []),
            "note": "architectural geometry only — no structural, MEP, fire or code content"}
