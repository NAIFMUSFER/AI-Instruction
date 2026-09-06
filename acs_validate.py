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


def validate_building(b):
    """يعيد (issues, stats). issues = قائمة نصوص عربية موجّهة للنموذج."""
    issues = []
    site = b.get("site", {})
    W = float(site.get("w", 0)); D = float(site.get("d", 0))
    if W <= 0 or D <= 0:
        issues.append("site.w و site.d يجب أن يكونا أكبر من صفر.")
        return issues, {}

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
        for r in rooms:
            rid = r.get("id", "?")
            rect = r.get("rect")
            if not rect or len(rect) != 4:
                issues.append("[%s/%s] rect غير صالح." % (tmpl, rid)); continue
            x, z, w, d = [float(v) for v in rect]
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
            for p in pts:
                h = p.get("height")
                if h is None:
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
            for p in pts:
                px, pz = float(p.get("x", w / 2)), float(p.get("z", d / 2))
                if px < -0.05 or pz < -0.05 or px > w + 0.05 or pz > d + 0.05:
                    issues.append("[%s/%s] نقطة %s خارج حدود الغرفة (x=%.2f z=%.2f)."
                                  % (tmpl, rid, p.get("type"), px, pz))
                    break

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

    return issues, stats


def format_issues(issues, limit=40):
    head = issues[:limit]
    txt = "\n".join("- " + s for s in head)
    if len(issues) > limit:
        txt += "\n- (و %d مخالفة أخرى مشابهة)" % (len(issues) - limit)
    return txt
