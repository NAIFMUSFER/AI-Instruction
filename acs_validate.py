# -*- coding: utf-8 -*-
# =============================================================================
# acs_validate.py  --  طبقة التحقّق الهندسي + الإصلاح الذاتي
# تفحص Building JSON قبل البناء وتُعيد قائمة مخالفات مفهومة، لتُرسَل للنموذج ليصلحها.
# القواعد مستمدة من الممارسة الشائعة وكود البناء السعودي (SBC) المرجعي.
# =============================================================================

import math

OPENING_EDGE_TOLERANCE_M = 0.05  # existing horizontal tolerance, metres
GEOMETRY_EPSILON_M = 1e-6        # floating-point comparisons, not a code limit

MIN_ROOM_AREA = 1.0        # م² — أصغر من ذلك غالباً خطأ
SPLIT_AREA = 30.0          # م² — حيّز أكبر من هذا يجب تفتيته لغرف (سكني فقط)
MIN_CORRIDOR_W = 1.2       # م — أقل عرض ممر
OUTLET_H = 0.40            # م
SWITCH_H = 1.20            # م
GENERIC_IDS = ("apt", "apartment", "unit", "flat", "shaqqa", "شقة")
# أحياز خارجية/غير مشغولة: لا تتطلّب باباً أو إنارة أو كاشف دخان
OUTDOOR = ("parapet", "balcony", "terrace", "solar", "tank", "condenser", "ac_unit",
           "seating", "garden", "yard", "roof_", "سور", "بلكونة", "شمسي", "خزان", "حديقة")
# غلاف المبنى: مستطيل يحيط بكل شيء — يُستثنى من فحص التداخل
ENVELOPE = ("envelope", "shell", "perimeter", "parapet", "building_shell", "غلاف", "سور")

# أقل عرض ممرّات صناعية (م)
IND_AISLE = {"forklift": 3.4, "amr": 1.2, "pedestrian": 1.2, "one_way": 3.0}


def _is_envelope(rid):
    low = str(rid).lower()
    return any(k in low for k in ENVELOPE)


def _is_outdoor(rid):
    low = str(rid).lower()
    return any(k in low for k in OUTDOOR)


def _is_open_zone(r):
    """منطقة تشغيلية مفتوحة (مستودع/مصنع): محدّدة بدهان أرضي لا بجدران —
    لا تُطالَب بباب ولا كاشف دخان لكل حيّز، ولها أن تكون كبيرة جداً."""
    return str(r.get("walls", "")).lower() in ("none", "line", "low", "rail") or bool(r.get("role"))


def building_type(b):
    return str((b.get("meta") or {}).get("type", "residential")).lower()


def _overlap(a, b, tol=0.05):
    ax, az, aw, ad = a; bx, bz, bw, bd = b
    return not (ax + aw <= bx + tol or bx + bw <= ax + tol or
                az + ad <= bz + tol or bz + bd <= az + tol)


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _opening_issues(room, template, width, depth, wall_height):
    issues = []
    host_height = _finite_number(room.get("wall_h", wall_height))
    for kind in ("doors", "windows"):
        for index, opening in enumerate(room.get(kind) or []):
            label = "[%s/%s/%s/%d]" % (template, room.get("id", "?"), kind, index)
            def add(code, message):
                issues.append("%s %s: %s" % (label, code, message))
            if not isinstance(opening, dict):
                add("OPENING_INVALID", "تعريف الفتحة ليس كائناً.")
                continue
            edge = opening.get("edge")
            if edge not in ("N", "S", "E", "W"):
                add("OPENING_EDGE_INVALID", "الحافة يجب أن تكون N أو S أو E أو W.")
            values = {"offset": opening.get("offset"),
                      "width": opening.get("width", 0.9 if kind == "doors" else 1.2),
                      "height": opening.get("height", 2.1 if kind == "doors" else 1.6),
                      "sill": opening.get("sill", 0.9) if kind == "windows" else 0}
            numbers = {key: _finite_number(value) for key, value in values.items()}
            for key, value in numbers.items():
                if value is None:
                    add("OPENING_NUMBER_INVALID", "%s يجب أن يكون عدداً منتهياً." % key)
            if any(value is None for value in numbers.values()):
                continue
            off, ow, oh, sill = (numbers[key] for key in ("offset", "width", "height", "sill"))
            if ow <= 0:
                add("OPENING_WIDTH_NON_POSITIVE", "عرض الفتحة يجب أن يكون موجباً.")
            if oh <= 0:
                add("OPENING_HEIGHT_NON_POSITIVE", "ارتفاع الفتحة يجب أن يكون موجباً.")
            if sill < 0:
                add("WINDOW_SILL_NEGATIVE", "أسفل النافذة يقع تحت منسوب الأرضية.")
            if edge in ("N", "S", "E", "W") and ow > 0:
                span = width if edge in ("N", "S") else depth
                if off - ow / 2 < -OPENING_EDGE_TOLERANCE_M or off + ow / 2 > span + OPENING_EDGE_TOLERANCE_M:
                    add("OPENING_OUTSIDE_WALL", "الفتحة خارج طول الجدار المضيف.")
            if host_height is None or host_height <= 0:
                add("OPENING_HOST_HEIGHT_INVALID", "ارتفاع الجدار المضيف غير صالح.")
            elif oh > 0 and sill + oh > host_height + GEOMETRY_EPSILON_M:
                add("OPENING_ABOVE_WALL", "أعلى الفتحة يتجاوز ارتفاع الجدار المضيف.")
    return issues


def _item_geometry_issues(room, template, width, depth, stats):
    issues = []
    for kind in ("furniture", "objects"):
        for index, item in enumerate(room.get(kind) or []):
            label = "[%s/%s/%s/%d]" % (template, room.get("id", "?"), kind, index)
            if not isinstance(item, dict):
                issues.append(label + " ITEM_INVALID: تعريف العنصر ليس كائناً.")
                continue
            dimensions = {key: _finite_number(item[key]) for key in ("w", "d", "h") if key in item}
            if any(value is None or value <= 0 for value in dimensions.values()):
                issues.append(label + " ITEM_DIMENSION_INVALID: أبعاد العنصر يجب أن تكون موجبة ومنتهية.")
                continue
            x = _finite_number(item.get("x", width / 2 if kind == "objects" else None))
            z = _finite_number(item.get("z", depth / 2 if kind == "objects" else None))
            count = _finite_number(item.get("count", 1)) if kind == "objects" else 1
            pitch = _finite_number(item.get("pitch", 1.2)) if kind == "objects" else 0
            rot = _finite_number(item.get("rot", 0)) if kind == "objects" else 0
            if x is None or z is None or pitch is None or rot is None:
                issues.append(label + " ITEM_NUMBER_INVALID: إحداثيات العنصر وتكراره يجب أن تكون منتهية.")
                continue
            if count is None or count < 1 or count != int(count):
                issues.append(label + " ITEM_COUNT_INVALID: عدد النسخ يجب أن يكون عدداً صحيحاً موجباً.")
                continue
            if kind == "furniture":
                # build_room renders the legacy furniture box with these defaults.
                fw, fd = dimensions.get("w", 0.8), dimensions.get("d", 0.8)
            else:
                # No invented catalogue size: when a footprint is unstated,
                # check the centre and disclose the incomplete footprint scope.
                fw, fd = dimensions.get("w", 0), dimensions.get("d", 0)
                if "w" not in dimensions or "d" not in dimensions:
                    stats["object_footprints_unstated"] = stats.get("object_footprints_unstated", 0) + 1
            angle = math.radians(rot)
            half_x = (abs(math.cos(angle)) * fw + abs(math.sin(angle)) * fd) / 2
            half_z = (abs(math.sin(angle)) * fw + abs(math.cos(angle)) * fd) / 2
            # Linear repetition has constant footprint. Its union is contained
            # iff both endpoints are contained; no unbounded count-sized loop.
            for instance in sorted({0, int(count) - 1}):
                px = x + (pitch * instance if item.get("dir") != "z" else 0)
                pz = z + (pitch * instance if item.get("dir") == "z" else 0)
                if (px - half_x < -GEOMETRY_EPSILON_M or pz - half_z < -GEOMETRY_EPSILON_M
                        or px + half_x > width + GEOMETRY_EPSILON_M
                        or pz + half_z > depth + GEOMETRY_EPSILON_M):
                    issues.append(label[:-1] + "/instance/%d] ITEM_OUTSIDE_ROOM: بصمة العنصر خارج الغرفة." % instance)
    return issues


def _core_alignment_issues(building, stats):
    import acs_arch
    issues, groups, unresolved = [], {}, []
    for level in building.get("levels") or []:
        template = level.get("template")
        index = _finite_number(level.get("index"))
        if index is None:
            continue
        for room in (building.get("floors", {}).get(template, {}).get("rooms") or []):
            rect = room.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) != 4:
                continue
            rect = [_finite_number(value) for value in rect]
            if any(value is None for value in rect) or rect[2] <= 0 or rect[3] <= 0:
                continue
            for oi, obj in enumerate(room.get("objects") or []):
                if not isinstance(obj, dict):
                    continue
                kind = acs_arch._core_kind(obj)
                if kind is None:
                    continue
                ref = "levels/%s/%s/%s/objects/%d" % (level.get("index"), template, room.get("id", "?"), oi)
                core_id = obj.get("core_id") or obj.get("id")
                x, z = _finite_number(obj.get("x")), _finite_number(obj.get("z"))
                if not core_id or x is None or z is None or obj.get("count", 1) != 1:
                    unresolved.append({"subject": ref, "reason": "identity_position_or_single_instance_not_stated"})
                    continue
                w, d = _finite_number(obj.get("w")), _finite_number(obj.get("d"))
                rot = _finite_number(obj.get("rot", 0))
                footprint = None
                if w is not None and d is not None and rot is not None and w > 0 and d > 0:
                    angle = math.radians(rot)
                    footprint = (abs(math.cos(angle)) * w + abs(math.sin(angle)) * d,
                                 abs(math.sin(angle)) * w + abs(math.cos(angle)) * d)
                else:
                    unresolved.append({"subject": ref, "reason": "footprint_not_stated"})
                groups.setdefault((kind, str(core_id)), []).append({
                    "index": index, "subject": ref, "position": (rect[0] + x, rect[1] + z),
                    "footprint": footprint})
    checked = 0
    for (kind, core_id), instances in sorted(groups.items()):
        instances.sort(key=lambda item: item["index"])
        if len({item["index"] for item in instances}) < 2:
            unresolved.append({"subject": core_id, "reason": "no_second_level_for_comparison"})
            continue
        checked += 1
        reference = instances[0]
        for item in instances[1:]:
            if any(abs(a - b) > GEOMETRY_EPSILON_M for a, b in zip(reference["position"], item["position"])):
                issues.append("[%s/core/%s] CORE_VERTICAL_MISALIGNMENT: موضع النواة لا يطابق المستوى %s."
                              % (item["subject"], core_id, reference["index"]))
            if reference["footprint"] is not None and item["footprint"] is not None:
                if any(abs(a - b) > GEOMETRY_EPSILON_M for a, b in zip(reference["footprint"], item["footprint"])):
                    issues.append("[%s/core/%s] CORE_FOOTPRINT_MISMATCH: بصمة النواة تختلف بين المستويات."
                                  % (item["subject"], core_id))
    stats["vertical_alignment"] = {"status": ("PARTIAL" if checked and unresolved else
        "COMPLETED" if checked else "NOT_EVALUATED" if unresolved else "NOT_APPLICABLE"),
        "checked_groups": checked, "unresolved": unresolved,
        "scope": "stated identity and horizontal footprint; not structural or stair-flight design"}
    return issues


def validate_building(b):
    """يعيد (issues, stats). issues = قائمة نصوص عربية موجّهة للنموذج."""
    issues = []
    site = b.get("site", {})
    W = _finite_number(site.get("w")); D = _finite_number(site.get("d"))
    if W is None or D is None or W <= 0 or D <= 0:
        issues.append("SITE_DIMENSIONS_INVALID: site.w و site.d يجب أن يكونا موجبين ومنتهيين.")
        return issues, {}

    for field in ("wall_h", "wall_t", "floor_height"):
        if field in b:
            value = _finite_number(b[field])
            if value is None or value <= 0:
                issues.append("BUILDING_NUMBER_INVALID: %s يجب أن يكون موجباً ومنتهياً." % field)
    level_indexes = set()
    for position, level in enumerate(b.get("levels") or []):
        index = _finite_number(level.get("index"))
        if index is None or index != int(index):
            issues.append("[levels/%d] LEVEL_INDEX_INVALID: فهرس الدور يجب أن يكون عدداً صحيحاً." % position)
        elif index in level_indexes:
            issues.append("[levels/%d] LEVEL_INDEX_DUPLICATE: فهرس دور مكرر." % position)
        else:
            level_indexes.add(index)
        if level.get("elevation") is not None and _finite_number(level["elevation"]) is None:
            issues.append("[levels/%d] LEVEL_ELEVATION_INVALID: المنسوب يجب أن يكون منتهياً." % position)

    btype = building_type(b)
    industrial = btype in ("warehouse", "industrial", "factory", "logistics", "مستودع")
    # الوضع الصارم: نلتزم بوصف العميل حرفياً — لا نطالبه بإضافات قياسية،
    # ونكتفي بفحص الهندسة (الحدود، التداخل، الفتحات) دون فرض محتوى.
    strict = bool((b.get("meta") or {}).get("strict"))
    stats = {"levels": len(b.get("levels", [])), "rooms": 0, "points": 0}
    if industrial:
        stats["racks"] = stats["lanes"] = stats["stations"] = stats["docks"] = 0

    for tmpl, fdef in (b.get("floors") or {}).items():
        rooms = fdef.get("rooms", []) or []
        stats["rooms"] += len(rooms)
        if not rooms:
            issues.append("القالب '%s' بلا غرف — أضِف غرفه." % tmpl)
            continue

        rects = []
        room_ids = set()
        for r in rooms:
            rid = r.get("id", "?")
            if str(rid) in room_ids:
                issues.append("[%s/%s] ROOM_ID_DUPLICATE: معرّف غرفة مكرر في القالب." % (tmpl, rid))
            room_ids.add(str(rid))
            rect = r.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) != 4:
                issues.append("[%s/%s] ROOM_RECT_INVALID: rect غير صالح." % (tmpl, rid)); continue
            coordinates = [_finite_number(v) for v in rect]
            if any(value is None for value in coordinates):
                issues.append("[%s/%s] ROOM_RECT_NONFINITE: إحداثيات الغرفة يجب أن تكون منتهية." % (tmpl, rid)); continue
            x, z, w, d = coordinates
            if w <= 0 or d <= 0:
                issues.append("[%s/%s] ROOM_DIMENSIONS_INVALID: العرض والعمق يجب أن يكونا موجبين." % (tmpl, rid)); continue
            area = w * d

            # داخل حدود الأرض
            if x < -0.01 or z < -0.01 or x + w > W + 0.01 or z + d > D + 0.01:
                issues.append("[%s/%s] خارج مسطح البناء (%.1f×%.1f): rect=%s — أعِد وضعها بالداخل."
                              % (tmpl, rid, W, D, [round(v, 2) for v in (x, z, w, d)]))
            if area < MIN_ROOM_AREA:
                issues.append("[%s/%s] مساحتها %.1f م² صغيرة جداً." % (tmpl, rid, area))

            low = str(rid).lower()
            openz = industrial and (_is_open_zone(r) or _is_envelope(rid))

            if industrial:
                stats["racks"] += len(r.get("racks") or [])
                stats["lanes"] += len(r.get("lanes") or [])
                stats["stations"] += len(r.get("stations") or [])
                stats["docks"] += sum(int(dk.get("count", 1) or 1) for dk in (r.get("docks") or []))

            # تفتيت الأحياز الكبيرة العامة (apt_a ...) — سكني فقط
            if (not industrial) and not strict and area > SPLIT_AREA \
                    and any(g in low for g in GENERIC_IDS):
                issues.append(
                    "[%s/%s] حيّز عام مساحته %.0f م² — قسّمه إلى غرف مسمّاة منفصلة "
                    "(مجلس، صالة، مطبخ، غرف نوم، حمامات، ممر) كلٌّ برُكنها وأبعادها."
                    % (tmpl, rid, area))

            outdoor = _is_outdoor(rid)

            # باب لكل غرفة داخلية (عدا الأسوار والمواقف والمناطق المفتوحة)
            if not strict and not r.get("doors") and not outdoor and not openz \
                    and "parking" not in low and not r.get("docks"):
                issues.append("[%s/%s] بلا باب — أضِف باباً على حافة مناسبة." % (tmpl, rid))

            pts = r.get("points", []) or []
            stats["points"] += len(pts)
            kinds = [p.get("type") for p in pts]
            if not strict and area >= 3.0 and not outdoor \
                    and not any(k in ("light", "spot") for k in kinds):
                issues.append("[%s/%s] بلا إنارة — أضِف light أو spot." % (tmpl, rid))
            if not strict and area >= 6.0 and not outdoor and "parking" not in low \
                    and "smoke" not in kinds and "sprinkler" not in kinds:
                issues.append("[%s/%s] بلا كاشف دخان — أضِف smoke (أو sprinkler في المستودعات)."
                              % (tmpl, rid))

            # ---- قواعد صناعية ----
            if industrial:
                for ln in (r.get("lanes") or []):
                    k = ln.get("kind", "forklift")
                    if k in IND_AISLE:
                        wid = min(float(ln.get("w", 99) or 99), float(ln.get("d", 99) or 99))
                        if wid < IND_AISLE[k] - 0.01:
                            issues.append("[%s/%s] عرض ممر %s = %.2f م — يجب ≥ %.1f م."
                                          % (tmpl, rid, k, wid, IND_AISLE[k]))
                for rk in (r.get("racks") or []):
                    ai = float(rk.get("aisle", 0) or 0)
                    if rk.get("kind") == "pallet" and 0 < ai < 3.2:
                        issues.append("[%s/%s] ممر بين رفوف البالتات %.2f م — الرافعة تحتاج ≥ 3.2 م."
                                      % (tmpl, rid, ai))

            # ارتفاعات النقاط المصرّح بها
            for pi, p in enumerate(pts):
                h = p.get("height")
                if h is None:
                    continue
                h = _finite_number(h)
                if h is None:
                    issues.append("[%s/%s/points/%d] POINT_NUMBER_INVALID: ارتفاع النقطة غير منتهٍ." % (tmpl, rid, pi))
                    continue
                t = p.get("type")
                if t == "outlet" and abs(float(h) - OUTLET_H) > 0.15:
                    issues.append("[%s/%s] فيش على ارتفاع %.2f م — يجب ≈%.2f م." % (tmpl, rid, float(h), OUTLET_H))
                if t == "switch" and abs(float(h) - SWITCH_H) > 0.15:
                    issues.append("[%s/%s] مفتاح على ارتفاع %.2f م — يجب ≈%.2f م." % (tmpl, rid, float(h), SWITCH_H))

            # عرض الممر
            if "corridor" in low or "ممر" in low:
                if min(w, d) < MIN_CORRIDOR_W - 0.01:
                    issues.append("[%s/%s] عرض الممر %.2f م — يجب ≥ %.1f م."
                                  % (tmpl, rid, min(w, d), MIN_CORRIDOR_W))

            # النقاط داخل حدود الغرفة
            for pi, p in enumerate(pts):
                px, pz = _finite_number(p.get("x", w / 2)), _finite_number(p.get("z", d / 2))
                if px is None or pz is None:
                    issues.append("[%s/%s/points/%d] POINT_NUMBER_INVALID: إحداثيات النقطة غير منتهية." % (tmpl, rid, pi))
                    continue
                if px < -0.05 or pz < -0.05 or px > w + 0.05 or pz > d + 0.05:
                    issues.append("[%s/%s/points/%d] POINT_OUTSIDE_ROOM: نقطة %s خارج حدود الغرفة (x=%.2f z=%.2f)."
                                  % (tmpl, rid, pi, p.get("type"), px, pz))

            issues.extend(_item_geometry_issues(r, tmpl, w, d, stats))
            issues.extend(_opening_issues(r, tmpl, w, d, b.get("wall_h", 3.0)))

            rects.append((rid, (x, z, w, d)))

        # التداخل — (الغلاف الخارجي يحتوي بقية الأحياز فنستثنيه)
        rects = [rc for rc in rects if not _is_envelope(rc[0])]
        seen = 0
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if _overlap(rects[i][1], rects[j][1]):
                    issues.append("[%s] تداخل بين '%s' و'%s' — أزِح إحداهما."
                                  % (tmpl, rects[i][0], rects[j][0]))
                    seen += 1
                    if seen >= 12:
                        break
            if seen >= 12:
                break

    # ---- فحوص السلامة على مستوى المبنى الصناعي ----
    # (تُتخطّى كلياً في الوضع الصارم: العميل طلب التزاماً حرفياً بوصفه)
    if industrial and not strict:
        allpts, allrooms = [], []
        for fdef in (b.get("floors") or {}).values():
            for r in (fdef.get("rooms") or []):
                allrooms.append(r)
                allpts += [p.get("type") for p in (r.get("points") or [])]
        area = W * D
        need_ext = max(2, int(area / 1000))          # طفاية لكل ~1000 م²
        if allpts.count("extinguisher") < need_ext:
            issues.append("سلامة: عدد الطفايات %d — المطلوب ≥ %d لمساحة %.0f م² (وزّعها على الأعمدة والمخارج)."
                          % (allpts.count("extinguisher"), need_ext, area))
        if allpts.count("exit") < 4:
            issues.append("سلامة: مخارج الطوارئ %d — المطلوب ≥ 4 موزّعة على الواجهات الأربع."
                          % allpts.count("exit"))
        if "assembly" not in allpts:
            issues.append("سلامة: لا توجد نقطة تجمّع (assembly) — أضِف واحدة خارج مسار الحركة.")
        if allpts.count("camera") < 6:
            issues.append("أمن: كاميرات المراقبة %d — غطِّ الأرصفة والممرات الرئيسية (≥ 6)."
                          % allpts.count("camera"))
        if stats.get("docks", 0) < 2:
            issues.append("تشغيل: عدد أرصفة التحميل %d — المطلوب أرصفة استقبال وأخرى للشحن."
                          % stats.get("docks", 0))
        # ملاحظة مهمّة: لا نفرض أدواراً وظيفية (استلام/التقاط/تغليف…) على المبنى.
        # ما يطلبه العميل هو المرجع؛ فمن أراد مخزناً بلا منطقة التقاط فله ذلك.
        # نُبقي فقط ما هو متطلّب سلامة/حياة حقيقي، وهو يُضاف ولا يُنقص من طلبه.

    issues.extend(_core_alignment_issues(b, stats))
    return issues, stats


def format_issues(issues, limit=40):
    head = issues[:limit]
    txt = "\n".join("- " + s for s in head)
    if len(issues) > limit:
        txt += "\n- (و %d مخالفة أخرى مشابهة)" % (len(issues) - limit)
    return txt
