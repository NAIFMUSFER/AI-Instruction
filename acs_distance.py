# -*- coding: utf-8 -*-
# =============================================================================
# acs_distance.py — أساس قياس المسافة الهندسية الحقيقية للمسار.
#
# يقيس فقط: كم متراً يمكن قياسه فعلياً من هندسة النموذج على مسار موجود أصلاً.
# لا يجيب إطلاقاً: هل المسافة نظامية/ضمن الحد/آمنة/مطابقة؟ — لا محرّك أكواد هنا.
#
# مبادئ صارمة:
#   • الهندسة تَقيس مساراً موجوداً، ولا تُنشئ اتصالاً. العلاقات تبقى مصدر الحقيقة.
#   • ممنوع تحويل مسافة مراكز الفراغات إلى مسافة مشي.
#   • ممنوع اختراع هندسة درج (ارتفاع قائمة/عمق نائمة/عدد درجات) غير موجودة.
#   • رحلة المصعد ليست مشياً ولا تُجمع في walking_distance_m.
#   • COMPLETE لا تُستعمل إن كان أي مقطع مطلوب غير مقيس.
#   • الأشكال غير المستطيلة: لا نقطع خطاً مستقيماً عبر الجدران ⇒ GEOMETRY_NOT_SUPPORTED.
# =============================================================================
import math
import re

STATUSES = ("COMPLETE", "PARTIAL", "NOT_MEASURED", "GEOMETRY_NOT_SUPPORTED", "INVALID_PATH")
BASES = ("door_geometry", "straight_line_inside_rect", "corridor_centerline",
         "stair_geometry", "centroid_fallback", "unmeasured")
CORRIDOR_ASPECT = 3.0          # نسبة طول/عرض تُعامل بها المساحة كممر (هندسي، لا اسمي)


def _rooms_index(building, building_id="bld_0"):
    idx = {}
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, r in enumerate(((fdef or {}).get("rooms") or [])):
            sid = r.get("space_id") or "%s.%s.%s" % (building_id, tmpl, r.get("id") or ("sp_%d" % i))
            idx[sid] = r
    return idx


def _rect(r):
    rc = r.get("rect")
    if not rc or len(rc) < 4:
        return None
    return [float(v) for v in rc[:4]]


def _is_rectangular(r):
    """النموذج الحالي مستطيلات. أي شكل آخر (polygon/shape) غير مدعوم للقياس."""
    if r.get("polygon") or r.get("shape") or r.get("vertices"):
        return False
    return _rect(r) is not None


def _centroid(rc):
    return [rc[0] + rc[2] / 2.0, rc[1] + rc[3] / 2.0]


def architecture_of(building, building_id="bld_0"):
    """يصرّف الهندسة المعمارية إن أمكن. غيابها لا يمنع القياس ولا يغيّر نتيجة."""
    try:
        import acs_arch as _AR
        return _AR.compile_architecture(building, building_id)
    except Exception:
        return None


def door_anchor(room, door_index, arch=None, space_id=None, level_index=None):
    """نقطة عبور الباب من هندسته الفعلية (الحافة + الإزاحة)، لا من مركز الغرفة.
    حين تتوفّر هندسة الفتحة المصرَّفة نقرأ المرساة منها: هي المصدر المفضّل لأنها
    نفس المصدر الذي يرسم الجدار. للمستطيلات المحاذية للمحاور القيمتان متطابقتان
    رياضياً — والاختبار يثبت التطابق على كل النماذج، ولا يُفترض."""
    if not isinstance(room, dict):
        return None
    rc = _rect(room)
    doors = room.get("doors") or []
    if rc is None or door_index is None or door_index >= len(doors):
        return None
    d = doors[door_index]
    # لا نختلق موضع باب: الحافة والإزاحة يجب أن تكونا مصرَّحتين في النموذج
    if d.get("edge") is None or d.get("offset") is None:
        return None
    if arch is not None and space_id is not None:
        try:
            import acs_arch as _AR
            pt = _AR.opening_anchor(arch, "%s.door_%d" % (space_id, door_index), level_index)
        except Exception:
            pt = None
        if pt is not None:
            return [float(pt[0]), float(pt[1])]
    x, z, w, dep = rc
    off = float(d.get("offset") or 0)
    e = str(d.get("edge") or "N").upper()[:1]
    if e == "N":
        return [x + off, z]
    if e == "S":
        return [x + off, z + dep]
    if e == "W":
        return [x, z + off]
    return [x + w, z + off]


def _via_door(via):
    """'<space_id>.door_<i>' → (space_id, i)"""
    if not via or ".door_" not in str(via):
        return None, None
    sp, _, i = str(via).rpartition(".door_")
    try:
        return sp, int(i)
    except ValueError:
        return None, None


def _dist(a, b):
    # sqrt(dx²+dz²) صراحةً (لا hypot) لضمان تطابق بايت-بايت مع نسخة المتصفّح
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _in_space_length(room, a, b):
    """طول المقطع داخل فراغ. مستطيل ⇒ خط مستقيم بين المرساتين (يُوسم صراحةً).
    المساحات الطويلة الرفيعة (ممرّات هندسياً) ⇒ مسار على المحور الأوسط."""
    rc = _rect(room)
    if rc is None:
        return None, "unmeasured"
    w, d = rc[2], rc[3]
    long_side, short_side = (w, d) if w >= d else (d, w)
    if short_side > 0 and (long_side / short_side) >= CORRIDOR_ASPECT:
        # محور أوسط حقيقي مشتقّ من المستطيل نفسه
        if w >= d:
            mid = rc[1] + d / 2.0
            return abs(a[0] - b[0]) + abs(a[1] - mid) + abs(b[1] - mid), "corridor_centerline"
        mid = rc[0] + w / 2.0
        return abs(a[1] - b[1]) + abs(a[0] - mid) + abs(b[0] - mid), "corridor_centerline"
    return _dist(a, b), "straight_line_inside_rect"


def _stair_geometry(obj):
    """طول سير الدرج من قيم موجودة فعلاً في النموذج فقط.
    يقبل: run_m(+rise_m) أو risers+tread_m(+riser_m). وإلا لا يُقاس."""
    if not isinstance(obj, dict):
        return None
    run = obj.get("run_m")
    rise = obj.get("rise_m")
    if run is None and obj.get("risers") and obj.get("tread_m"):
        run = float(obj["risers"]) * float(obj["tread_m"])
        if obj.get("riser_m"):
            rise = float(obj["risers"]) * float(obj["riser_m"])
    if run is None:
        return None
    run = float(run)
    if rise is None:
        return run
    rise = float(rise)
    return math.sqrt(run * run + rise * rise)


def _find_object(room, kind, index_hint=None):
    for i, o in enumerate(room.get("objects") or []):
        k = str(o.get("kind") or o.get("name") or "").lower()
        if kind == "stairs" and ("stair" in k or "درج" in k or "سلم" in k):
            return o
        if kind == "elevator" and ("elevator" in k or re.search(r"(^|[^a-z])lift([^a-z]|$)", k) or "مصعد" in k):
            return o
    return None


def _obj_point(room, obj):
    """موضع عنصر (درج/مصعد) بالإحداثيات العامة — فقط إن كان مصرَّحاً في النموذج.
    إحداثيات العناصر نسبية لركن الفراغ. الغياب لا يُعوَّض بمركز الفراغ."""
    if not isinstance(room, dict) or not isinstance(obj, dict):
        return None
    rc = _rect(room)
    if rc is None or obj.get("x") is None or obj.get("z") is None:
        return None
    return [rc[0] + float(obj["x"]), rc[1] + float(obj["z"])]


def _level_elevation(building, level_index):
    for l in building.get("levels") or []:
        if int(l.get("index", 0)) == int(level_index):
            if l.get("elevation") is not None:
                return float(l["elevation"])
    fh = building.get("floor_height")
    return float(level_index) * float(fh) if fh is not None else None


def measure_path(building, path_result, building_id="bld_0",
                 origin_point=None, destination_point=None, arch=None):
    """يقيس هندسة مسار ناتج عن محرّك التنقّل. مشتقّ بالكامل — لا يُحفظ كبيانات مبنى."""
    out = {"status": None, "segments": [], "horizontal_m": 0.0,
           "stair_walking_m": 0.0, "walking_distance_m": None,
           "walking_distance_exact_m": None,
           "vertical_transport": [], "vertical_elevation_change_m": None,
           "distance_status": "NOT_MEASURED", "measurement_basis": [],
           "unmeasured_segments": [], "origin_basis": None,
           "units": "m", "compliance": "NOT_EVALUATED"}
    if not path_result or path_result.get("status") != "FOUND":
        out.update(status="INVALID_PATH", distance_status="INVALID_PATH",
                   reason="distance is measured only for a FOUND topological path")
        return out

    rooms = _rooms_index(building, building_id)
    transitions = path_result.get("transitions") or []
    nodes = path_result.get("nodes") or []
    if not nodes:
        out.update(status="INVALID_PATH", distance_status="INVALID_PATH")
        return out

    def space_of(node):
        return str(node).split("@")[0]

    unsupported = False
    cur_space = space_of(nodes[0])
    room0 = rooms.get(cur_space)
    if room0 is None or not _is_rectangular(room0):
        unsupported = unsupported or (room0 is not None)
    if origin_point:
        cur_pt, out["origin_basis"] = list(origin_point), "explicit_origin_point"
    elif room0 is not None and _rect(room0):
        cur_pt, out["origin_basis"] = _centroid(_rect(room0)), "space_centroid_fallback"
    else:
        cur_pt, out["origin_basis"] = None, "unmeasured"

    cur_pt_reason = None if cur_pt is not None else "origin_anchor_unavailable"
    wall_t = float(building.get("wall_t") or 0.0)

    for t in transitions:
        if t.get("type") == "door":
            sp, di = _via_door(t.get("via"))
            room = rooms.get(sp)
            if arch is None:
                arch = architecture_of(building, building_id)   # مرّة واحدة لكل قياس
            anchor = door_anchor(room, di, arch, sp) if room is not None else None
            from_room = rooms.get(cur_space)
            if anchor is None or from_room is None or cur_pt is None:
                r_ = ("door_anchor_not_derivable_from_model" if anchor is None else
                      ("space_geometry_missing" if from_room is None else
                       (cur_pt_reason or "origin_anchor_unavailable")))
                out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                   "reason": r_})
                out["segments"].append({"type": "in_space", "space": cur_space,
                                        "length_m": None, "basis": "unmeasured"})
                cur_pt = None
                cur_pt_reason = "previous_anchor_unavailable"
            elif not _is_rectangular(from_room):
                unsupported = True
                out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                   "reason": "non_rectangular_geometry_not_supported"})
                out["segments"].append({"type": "in_space", "space": cur_space,
                                        "length_m": None, "basis": "unmeasured"})
                cur_pt, cur_pt_reason = anchor, None
            else:
                ln, basis = _in_space_length(from_room, cur_pt, anchor)
                if ln is None:
                    out["segments"].append({"type": "in_space", "space": cur_space,
                                            "length_m": None, "basis": "unmeasured"})
                    out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                       "reason": "geometry_missing"})
                else:
                    out["segments"].append({"type": "in_space", "space": cur_space,
                                            "from": cur_pt, "to": anchor,
                                            "length_m": round(ln, 3), "basis": basis})
                    out["horizontal_m"] += ln
                    out["measurement_basis"].append(basis)
                cur_pt, cur_pt_reason = anchor, None
            if wall_t > 0:
                out["segments"].append({"type": "door_transition", "via": t.get("via"),
                                        "length_m": round(wall_t, 3), "basis": "door_geometry"})
                out["horizontal_m"] += wall_t
                out["measurement_basis"].append("door_geometry")
            else:
                out["segments"].append({"type": "door_transition", "via": t.get("via"),
                                        "length_m": None, "basis": "unmeasured"})
                out["unmeasured_segments"].append({"type": "door_transition", "via": t.get("via"),
                                                   "reason": "wall_thickness_unknown"})
            cur_space = t.get("to") or cur_space
        else:                                   # انتقال رأسي
            kind = t.get("kind")
            room = rooms.get(cur_space)
            obj = _find_object(room, kind) if room is not None else None
            ap = _obj_point(room, obj)
            # المشي داخل الفراغ حتى العنصر الرأسي جزء حقيقي من المسار — لا يُسقَط بصمت
            if room is not None and not _is_rectangular(room):
                unsupported = True
                out["segments"].append({"type": "in_space", "space": cur_space,
                                        "length_m": None, "basis": "unmeasured"})
                out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                   "reason": "non_rectangular_geometry_not_supported"})
            elif ap is not None and cur_pt is not None and room is not None:
                ln, basis = _in_space_length(room, cur_pt, ap)
                if ln is None:
                    out["segments"].append({"type": "in_space", "space": cur_space,
                                            "length_m": None, "basis": "unmeasured"})
                    out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                       "reason": "geometry_missing"})
                else:
                    out["segments"].append({"type": "in_space", "space": cur_space,
                                            "from": cur_pt, "to": ap,
                                            "length_m": round(ln, 3), "basis": basis})
                    out["horizontal_m"] += ln
                    out["measurement_basis"].append(basis)
            else:
                r_ = ("vertical_element_position_not_stated" if ap is None else
                      ("space_geometry_missing" if room is None else
                       (cur_pt_reason or "origin_anchor_unavailable")))
                out["segments"].append({"type": "in_space", "space": cur_space,
                                        "length_m": None, "basis": "unmeasured"})
                out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                                   "reason": r_})
            dz = None
            ea = _level_elevation(building, t.get("from_level"))
            eb = _level_elevation(building, t.get("to_level"))
            if ea is not None and eb is not None:
                dz = abs(eb - ea)
            if kind == "stairs":
                sl = _stair_geometry(obj)
                if sl is None:
                    out["segments"].append({"type": "stair", "via": t.get("via"),
                                            "length_m": None, "basis": "unmeasured"})
                    out["unmeasured_segments"].append(
                        {"type": "stair", "via": t.get("via"),
                         "reason": "stair_geometry_absent (no risers/tread/run in model)"})
                else:
                    out["segments"].append({"type": "stair", "via": t.get("via"),
                                            "length_m": round(sl, 3), "basis": "stair_geometry"})
                    out["stair_walking_m"] += sl
                    out["measurement_basis"].append("stair_geometry")
            else:                                # مصعد: نقل رأسي، ليس مشياً
                out["segments"].append({"type": "vertical_transport", "via": t.get("via"),
                                        "kind": kind, "length_m": None,
                                        "basis": "not_walking_distance"})
                out["vertical_transport"].append(
                    {"kind": kind, "via": t.get("via"), "from_level": t.get("from_level"),
                     "to_level": t.get("to_level"), "elevation_change_m": dz})
            if dz is not None:
                out["vertical_elevation_change_m"] = (out["vertical_elevation_change_m"] or 0.0) + dz
            cur_space = t.get("to") or cur_space
            r2 = rooms.get(cur_space)
            # نقطة الوصول هي موضع العنصر الرأسي في الفراغ الجديد — لا مركز الفراغ
            p2 = _obj_point(r2, _find_object(r2, kind) if r2 is not None else None)
            if p2 is not None:
                cur_pt, cur_pt_reason = p2, None
            else:
                cur_pt = None
                cur_pt_reason = "vertical_element_arrival_position_not_stated"

    # المقطع الأخير حتى نقطة الوجهة
    last_room = rooms.get(cur_space)
    if destination_point:
        dest_pt = list(destination_point)
    elif last_room is not None and _rect(last_room):
        dest_pt = _centroid(_rect(last_room))
    else:
        dest_pt = None
    if cur_pt is not None and dest_pt is not None and last_room is not None:
        if not _is_rectangular(last_room):
            unsupported = True
            out["segments"].append({"type": "in_space", "space": cur_space,
                                    "length_m": None, "basis": "unmeasured"})
            out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                               "reason": "non_rectangular_geometry_not_supported"})
        else:
            ln, basis = _in_space_length(last_room, cur_pt, dest_pt)
            out["segments"].append({"type": "in_space", "space": cur_space, "from": cur_pt,
                                    "to": dest_pt, "length_m": round(ln, 3), "basis": basis})
            out["horizontal_m"] += ln
            out["measurement_basis"].append(basis)
    elif cur_pt is None or dest_pt is None:
        r_ = (cur_pt_reason or "origin_anchor_unavailable") if cur_pt is None \
            else "destination_anchor_unavailable"
        out["segments"].append({"type": "in_space", "space": cur_space,
                                "length_m": None, "basis": "unmeasured"})
        out["unmeasured_segments"].append({"type": "in_space", "space": cur_space,
                                           "reason": r_})

    # قيم التقييم بدقّة كاملة تُحفظ منفصلة عن قيم العرض المقرَّبة (§دقّة)
    out["horizontal_exact_m"] = out["horizontal_m"]
    out["stair_walking_exact_m"] = out["stair_walking_m"]
    out["horizontal_m"] = round(out["horizontal_m"], 3)
    out["stair_walking_m"] = round(out["stair_walking_m"], 3)
    out["measurement_basis"] = sorted(set(out["measurement_basis"]))

    if unsupported:
        out["status"] = "GEOMETRY_NOT_SUPPORTED"
        out["distance_status"] = "GEOMETRY_NOT_SUPPORTED"
        out["measured_horizontal_m"] = out["horizontal_m"]
    elif out["unmeasured_segments"]:
        out["status"] = "PARTIAL"
        out["distance_status"] = "PARTIAL"
        out["measured_horizontal_m"] = out["horizontal_m"]
    elif not out["segments"]:
        out["status"] = "NOT_MEASURED"
        out["distance_status"] = "NOT_MEASURED"
    else:
        out["status"] = "MEASURED"
        out["distance_status"] = "COMPLETE"
        # تعريف walking_distance_m: مقاطع المشي الأفقية + سير الدرج المقيس فقط،
        # واستبعاد رحلة المصعد والقيم التشخيصية والمقاطع غير المقيسة.
        out["walking_distance_m"] = round(out["horizontal_m"] + out["stair_walking_m"], 3)
        out["walking_distance_exact_m"] = out["horizontal_exact_m"] + out["stair_walking_exact_m"]
    if out["origin_basis"] == "space_centroid_fallback" and out["distance_status"] == "COMPLETE":
        out["note"] = ("نقطة البداية/النهاية افتراضها مركز الفراغ — "
                       "المسافة مقاسة من هندسة النموذج بهذا الافتراض المعلَن.")
    return out


def validate_measurement(m):
    """فحوص بنيوية للقياس — لا فحص مطابقة."""
    issues = []
    if not m:
        return ["empty measurement"]
    if m.get("units") != "m":
        issues.append("units must be metres")
    total = 0.0
    for s in m.get("segments") or []:
        ln = s.get("length_m")
        if ln is None:
            continue
        if not isinstance(ln, (int, float)) or ln != ln:
            issues.append("NaN length in segment %s" % s.get("type"))
            continue
        if ln < 0:
            issues.append("negative length in segment %s" % s.get("type"))
        if s.get("basis") not in BASES and s.get("basis") != "not_walking_distance":
            issues.append("unknown measurement basis: %s" % s.get("basis"))
        if s.get("type") in ("in_space", "door_transition"):
            total += ln
    if abs(total - float(m.get("horizontal_m") or 0.0)) > 0.01:
        issues.append("segment sum %.3f != horizontal_m %.3f" % (total, m.get("horizontal_m") or 0))
    if m.get("distance_status") == "COMPLETE" and m.get("unmeasured_segments"):
        issues.append("COMPLETE with unmeasured segments")
    if m.get("distance_status") != "COMPLETE" and m.get("walking_distance_m") is not None:
        issues.append("walking_distance_m must be null unless COMPLETE")
    for v in m.get("vertical_transport") or []:
        if v.get("kind") == "elevator" and v.get("length_m"):
            issues.append("elevator travel must not carry walking length")
    return issues


def summary(m):
    if m.get("distance_status") == "COMPLETE":
        return "المسافة الهندسية المقاسة للمسار الحالي: %.2f م (من هندسة النموذج)." % m["walking_distance_m"]
    if m.get("distance_status") == "PARTIAL":
        return ("تم قياس %.2f م أفقياً من هندسة النموذج؛ بعض مقاطع المسار غير قابلة للقياس حالياً (%d مقطع)."
                % (m.get("measured_horizontal_m") or 0.0, len(m.get("unmeasured_segments") or [])))
    if m.get("distance_status") == "GEOMETRY_NOT_SUPPORTED":
        return "هندسة أحد الفراغات غير مستطيلة — لا يُقاس المسار عبرها بخط مستقيم."
    return "لم تُقَس مسافة المسار."
