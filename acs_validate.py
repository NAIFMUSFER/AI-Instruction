# -*- coding: utf-8 -*-
# =============================================================================
# acs_validate.py  --  طبقة التحقّق الهندسي + الإصلاح الذاتي
# تفحص Building JSON قبل البناء وتُعيد قائمة مخالفات مفهومة، لتُرسَل للنموذج ليصلحها.
# Model geometry and legacy planning hints only. No regulatory evaluation is
# performed: no authoritative jurisdiction, rule source or version is loaded.
# =============================================================================

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
            # Required fire equipment, aisle widths and electrical heights are
            # unresolved review tasks. Uncited thresholds must not enter the
            # repair prompt as mandatory engineering corrections.

            # النقاط داخل حدود الغرفة
            for p in pts:
                px, pz = float(p.get("x", w / 2)), float(p.get("z", d / 2))
                if px < -0.05 or pz < -0.05 or px > w + 0.05 or pz > d + 0.05:
                    issues.append("[%s/%s] نقطة %s خارج حدود الغرفة (x=%.2f z=%.2f)."
                                  % (tmpl, rid, p.get("type"), px, pz))
                    break

            # الفتحات ضمن طول الحافة
            for kind in ("doors", "windows"):
                for o in (r.get(kind) or []):
                    e = o.get("edge"); off = float(o.get("offset", 0)); ow = float(o.get("width", 0.9))
                    span = w if e in ("N", "S") else d
                    if off - ow / 2 < -0.05 or off + ow / 2 > span + 0.05:
                        issues.append("[%s/%s] %s على الحافة %s خارج حدود الجدار (offset=%.2f عرض=%.2f, الطول=%.2f)."
                                      % (tmpl, rid, "باب" if kind == "doors" else "نافذة", e, off, ow, span))

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

    # Regulatory and security quantities remain NOT_EVALUATED. They are
    # disclosed by the authority planner, never manufactured as repair errors.

    return issues, stats


def format_issues(issues, limit=40):
    head = issues[:limit]
    txt = "\n".join("- " + s for s in head)
    if len(issues) > limit:
        txt += "\n- (و %d مخالفة أخرى مشابهة)" % (len(issues) - limit)
    return txt
