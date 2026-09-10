# -*- coding: utf-8 -*-
# =============================================================================
# acs_validate.py  --  طبقة التحقّق الهندسي + الإصلاح الذاتي
# تفحص Building JSON قبل البناء وتُعيد قائمة مخالفات مفهومة، لتُرسَل للنموذج ليصلحها.
# Model geometry and legacy planning hints only. No regulatory evaluation is
# performed: no authoritative jurisdiction, rule source or version is loaded.
#
# نطاق الفحص (F-51): كان هذا الملفّ يفحص كل قالب طابق **معزولاً** — يمرّ على
# b["floors"] ولا يقرأ b["levels"] إطلاقاً. نتيجة ذلك أن فئتين كاملتين من
# الأعطال كانتا غير مرئيتين بالبناء لا بالمصادفة:
#
#   • كل ما هو **رأسيّ**: عمود درج أو مصعد لا يتطابق بين الأدوار، طابق يشير
#     إلى قالب غير معرَّف، حيّز في الأعلى بلا ما يسنده أسفله. المدقّق كان
#     يعلن «٠ مشاكل» على نموذج فيه ٢٢، أخطرها من هذه الفئة بالضبط.
#   • كل ما هو **طوبولوجيّ**: فراغ لا يوصل إليه باب، باب يفتح على لا شيء،
#     نافذة على جدار داخلي، فتحتان تتراكبان على الحافة نفسها.
#
# الحدّ لم يتغيّر: هندسة وطوبولوجيا فقط. لا عتبة تنظيمية ولا كمّية مطلوبة
# تدخل من هنا — تلك مهامّ مراجعة يكشفها acs_engineering_authority بحالة
# NOT_EVALUATED، ولا تُصنَّع هنا كأخطاء إصلاح.
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


# أحياز النواة الرأسية: يجب أن تتطابق رأسياً بين الأدوار لأن الدرج والمصعد
# والمنور تمرّ خلال البلاطات. القائمة أسماء لا عتبات.
CORE_IDS = ("stair", "staircase", "lift", "elevator", "shaft", "duct", "riser",
            "core", "درج", "سلم", "مصعد", "منور", "ناظور")

# أدنى تراكب يُعدّ جداراً مشتركاً حقيقياً لا ملامسة ركن (م).
SHARED_EDGE_MIN = 0.60
# تفاوت هندسي: نصف سماكة الجدار المعتادة. تحته رقمٌ لا مسافة.
GEOM_TOL = 0.05
# تفاوت التطابق الرأسي: أوسع قليلاً — انزياح سنتيمترات بين الأدوار تقريبٌ،
# وانزياح حقيقي في عمود درج لا يقلّ عن عرض قدم.
CORE_TOL = 0.10
# سقف بلاغات كل فحص على حدة: التقرير للنموذج ليصلح، لا لِيُغرَق.
PER_CHECK_CAP = 8


def _is_core(rid, r=None):
    low = str(rid).lower()
    if any(k in low for k in CORE_IDS):
        return True
    role = str((r or {}).get("role", "")).lower()
    return any(k in role for k in CORE_IDS)


def _finite(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return f == f and f not in (float("inf"), float("-inf"))


def _core_key(rid):
    """مفتاح يجمع 'stair_1' و'STAIR_1' و'stair_1_l2' في نواة واحدة."""
    low = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(rid).lower())
    for suffix in ("_l0", "_l1", "_l2", "_l3", "_l4", "_l5", "_g", "_ground",
                   "_typical", "_roof"):
        if low.endswith(suffix):
            low = low[:-len(suffix)]
            break
    return low


def _shared_edge(a, b):
    """هل يتلامس المستطيلان على جدار مشترك بطول كافٍ؟ يعيد الطول أو 0."""
    ax, az, aw, ad = a
    bx, bz, bw, bd = b
    # جدار رأسي (يتشاركان قيمة x)
    if abs(ax + aw - bx) <= GEOM_TOL or abs(bx + bw - ax) <= GEOM_TOL:
        ov = min(az + ad, bz + bd) - max(az, bz)
        return ov if ov > 0 else 0.0
    # جدار أفقي (يتشاركان قيمة z)
    if abs(az + ad - bz) <= GEOM_TOL or abs(bz + bd - az) <= GEOM_TOL:
        ov = min(ax + aw, bx + bw) - max(ax, bx)
        return ov if ov > 0 else 0.0
    return 0.0


def _on_site_boundary(rect, W, D):
    """الحوافّ التي تقع على حدّ الأرض — الأبواب عليها أبواب خارجية مشروعة."""
    x, z, w, d = rect
    out = set()
    if abs(z) <= GEOM_TOL:
        out.add("N")
    if abs(z + d - D) <= GEOM_TOL:
        out.add("S")
    if abs(x) <= GEOM_TOL:
        out.add("W")
    if abs(x + w - W) <= GEOM_TOL:
        out.add("E")
    return out


def _edge_neighbours(rect, edge, others):
    """الغرف التي تلامس هذه الحافّة تحديداً — الحافّة المقصودة لا مقابلها.

    الاصطلاح ليس تخميناً: acs_bim.py سطر ٣٣٠ يعرّفه صراحةً
    N=(x,z)→(x+w,z) · S=(x,z+d)→(x+w,z+d) · W على x · E على x+w،
    وهو المصدر الوحيد المعتمد في النظام. نسخةٌ أولى من هذه الدالة قبلت
    الجانبين احتياطاً لاصطلاح ظُنّ غير معلن، فأبلغت عن نوافذ على واجهات
    خارجية لمجرّد أن غرفةً تلامس الجدار **المقابل**. تصحيحه أسقط الإنذارات
    الكاذبة، ولم يُسقط بلاغاً حقيقياً واحداً."""
    x, z, w, d = rect
    hits = []
    for rid, o in others:
        ox, oz, ow, od = o
        if edge == "N":
            touch = abs(oz + od - z) <= GEOM_TOL
            ov = min(x + w, ox + ow) - max(x, ox)
        elif edge == "S":
            touch = abs(z + d - oz) <= GEOM_TOL
            ov = min(x + w, ox + ow) - max(x, ox)
        elif edge == "W":
            touch = abs(ox + ow - x) <= GEOM_TOL
            ov = min(z + d, oz + od) - max(z, oz)
        else:                                    # E
            touch = abs(x + w - ox) <= GEOM_TOL
            ov = min(z + d, oz + od) - max(z, oz)
        if touch and ov > GEOM_TOL:
            hits.append(rid)
    return hits


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

    # يُجمع أثناء المرور لتُستعمل في الفحوص الرأسية والطوبولوجية بعده.
    tmpl_rects = {}          # قالب -> [(rid, rect)]
    tmpl_rooms = {}          # قالب -> {rid: room}

    for tmpl, fdef in (b.get("floors") or {}).items():
        rooms = fdef.get("rooms", []) or []
        tmpl_rects[tmpl] = []
        tmpl_rooms[tmpl] = {}
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
            if not all(_finite(v) for v in rect):
                issues.append("[%s/%s] rect يحوي قيمة غير عددية أو لا نهائية: %s — "
                              "أعِد كتابتها بأربعة أعداد حقيقية [x, z, w, d]."
                              % (tmpl, rid, list(rect)))
                continue
            x, z, w, d = [float(v) for v in rect]
            if w <= 0 or d <= 0:
                issues.append("[%s/%s] عرض أو عمق غير موجب (w=%.2f d=%.2f)."
                              % (tmpl, rid, w, d))
                continue
            if rid in tmpl_rooms[tmpl]:
                issues.append("[%s/%s] المعرّف مكرّر داخل القالب نفسه — "
                              "لكل حيّز معرّف فريد." % (tmpl, rid))
            tmpl_rooms[tmpl][rid] = r
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
            tmpl_rects[tmpl].append((rid, (x, z, w, d)))

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

    # ═════════════════════════════════════════════════════════════════════
    # F-51 · الفحوص التي لا يمكن لقالب واحد معزول أن يراها
    # ═════════════════════════════════════════════════════════════════════
    levels = b.get("levels") or []
    floors = b.get("floors") or {}

    # ── (١) سلامة الإسناد بين الطوابق والقوالب ──────────────────────────
    seen_index = {}
    used_templates = []
    for lv in levels:
        tname = lv.get("template")
        idx = lv.get("index")
        if tname is not None:
            used_templates.append(tname)
            if tname not in floors:
                issues.append(
                    "الطابق %s يشير إلى القالب '%s' وهو غير معرَّف في floors — "
                    "عرّف القالب أو صحّح الإشارة." % (idx if idx is not None else "?", tname))
        if idx is not None:
            if idx in seen_index:
                issues.append("رقم الطابق %s مكرّر (index) — لكل طابق رقم فريد." % idx)
            seen_index[idx] = True
    for tname in floors:
        if levels and tname not in used_templates:
            issues.append("القالب '%s' معرَّف ولا يشير إليه أي طابق — "
                          "اربطه بطابق أو احذفه." % tname)

    # ── (٢) التطابق الرأسي لأعمدة النواة (درج · مصعد · منور) ────────────
    # هذا هو العطل الذي أعلن المدقّق السابق «٠ مشاكل» بوجوده: عمود درج
    # يتحرّك بين دور ودور يجعل البلاطة تُصبّ فوق فراغ الدرج.
    if len([lv for lv in levels if lv.get("template") in floors]) >= 2:
        cores = {}       # مفتاح النواة -> [(قالب, rid, rect)]
        for tname in dict.fromkeys(used_templates):
            for rid, rect in tmpl_rects.get(tname, []):
                if _is_core(rid, tmpl_rooms.get(tname, {}).get(rid)):
                    cores.setdefault(_core_key(rid), []).append((tname, rid, rect))
        reported = 0
        for key, entries in sorted(cores.items()):
            tmpls = {e[0] for e in entries}
            if len(tmpls) < 2:
                continue
            base_t, base_id, base = entries[0]
            for tname, rid, rect in entries[1:]:
                delta = max(abs(rect[i] - base[i]) for i in range(4))
                if delta > CORE_TOL:
                    issues.append(
                        "عمود النواة '%s' غير متطابق رأسياً: في القالب '%s' rect=%s "
                        "وفي '%s' rect=%s (فرق %.2f م) — النواة الرأسية تمرّ خلال "
                        "البلاطات، فيجب أن يكون لها المسقط نفسه في كل دور."
                        % (key, base_t, [round(v, 2) for v in base], tname,
                           [round(v, 2) for v in rect], delta))
                    reported += 1
                    break
            if reported >= PER_CHECK_CAP:
                break

    # ── (٣) الإسناد الإنشائي: حيّز في الأعلى بلا ما تحته ────────────────
    ordered = [lv for lv in sorted(
        (lv for lv in levels if lv.get("template") in floors),
        key=lambda lv: (lv.get("index") if _finite(lv.get("index")) else 0))]
    reported = 0
    for i in range(1, len(ordered)):
        upper = ordered[i].get("template")
        lower = ordered[i - 1].get("template")
        below = tmpl_rects.get(lower, [])
        above = tmpl_rects.get(upper, [])
        if not below or not above or upper == lower:
            continue
        # الحارس الذي أضافته القياسات على ١٦٥ نموذجاً حقيقياً: هذا الفحص سليم
        # فقط إن كان القالب السفلي **بلاطة كاملة**. كثير من النماذج تمثّل
        # طابقاً جزئياً (سيناريو اختبار، أو دوراً لم يُفصَّل بعد)، وحينها كل
        # حيّز في الأعلى يبدو معلّقاً وليس كذلك. القياس: كم من مسقط الأعلى
        # يغطّيه الأسفل إجمالاً. دون ٦٠٪ لا نملك ما يميّز «نموذج ناقص» عن
        # «بروز مقصود» عن «عطل» — والصمت أصدق من ثلاثة احتمالات بلا ترجيح.
        up_area = sum(w * d for _i, (_x, _z, w, d) in above)
        cov_all = 0.0
        for _rid, (x, z, w, d) in above:
            for _bid, (ox, oz, ow, od) in below:
                ix = min(x + w, ox + ow) - max(x, ox)
                iz = min(z + d, oz + od) - max(z, oz)
                if ix > 0 and iz > 0:
                    cov_all += ix * iz
        if up_area <= 0 or cov_all / up_area < 0.60:
            continue
        for rid, rect in above:
            if _is_envelope(rid) or _is_outdoor(rid):
                continue
            x, z, w, d = rect
            # مساحة هذا الحيّز التي يغطّيها أي حيّز أسفله
            covered = 0.0
            for _bid, o in below:
                ox, oz, ow, od = o
                ix = min(x + w, ox + ow) - max(x, ox)
                iz = min(z + d, oz + od) - max(z, oz)
                if ix > 0 and iz > 0:
                    covered += ix * iz
            ratio = covered / (w * d) if w * d > 0 else 1.0
            if ratio < 0.5:
                issues.append(
                    "[%s/%s] معلّق: %.0f%% فقط من مسقطه يقع فوق حيّز في الطابق "
                    "'%s' أسفله — أعِد وضعه فوق مسقط مبنيّ أو أضِف ما يسنده."
                    % (upper, rid, ratio * 100, lower))
                reported += 1
                if reported >= PER_CHECK_CAP:
                    break
        if reported >= PER_CHECK_CAP:
            break

    # ── (٤) الطوبولوجيا داخل كل قالب: أبواب · نوافذ · وصول ──────────────
    for tname, entries in tmpl_rects.items():
        if len(entries) < 2:
            continue        # قالب بحيّز واحد: لا طوبولوجيا تُفحَص
        rooms_of = tmpl_rooms.get(tname, {})
        index = dict(entries)

        # (٤أ) باب يفتح على لا شيء · نافذة على جدار داخلي · فتحتان متراكبتان
        reported_o = 0
        for rid, rect in entries:
            r = rooms_of.get(rid) or {}
            if _is_envelope(rid) or _is_outdoor(rid):
                continue
            boundary = _on_site_boundary(rect, W, D)
            others = [(o_id, o_rect) for o_id, o_rect in entries if o_id != rid]
            for kind in ("doors", "windows"):
                spans = {}
                for o in (r.get(kind) or []):
                    e = o.get("edge")
                    if e not in ("N", "S", "E", "W"):
                        continue
                    off = float(o.get("offset", 0) or 0)
                    ow_ = float(o.get("width", 0.9) or 0.9)
                    lo, hi = off - ow_ / 2.0, off + ow_ / 2.0
                    for plo, phi, pkind in spans.get(e, []):
                        if lo < phi - GEOM_TOL and plo < hi - GEOM_TOL:
                            issues.append(
                                "[%s/%s] فتحتان متراكبتان على الحافّة %s "
                                "(%s عند %.2f و%s عند %.2f) — باعِد بينهما."
                                % (tname, rid, e,
                                   "باب" if kind == "doors" else "نافذة", off,
                                   "باب" if pkind == "doors" else "نافذة",
                                   (plo + phi) / 2.0))
                            reported_o += 1
                            break
                    spans.setdefault(e, []).append((lo, hi, kind))

                    if reported_o >= PER_CHECK_CAP:
                        continue
                    nbrs = _edge_neighbours(rect, e, others)
                    # لا فحص «باب لا يفتح على شيء» هنا. كُتب ثم أُسقط بالقياس:
                    # على ١٦٥ نموذجاً حقيقياً أطلق ٣٣ بلاغاً، كلّها كاذبة. السبب
                    # افتراضٌ لا يصحّ في هذا النظام — أن كل فراغ ممثَّل كغرفة.
                    # في مستودع مولَّد حيّ تشغل الغرف ٨٦٪ من الصندوق المحيط،
                    # والـ١٤٪ الباقية ممرّات وغلاف لا تُمثَّل غرفاً؛ فالباب على
                    # حافّة بلا جار يفتح على ممرّ حقيقي. الإشارة المفيدة التي
                    # كان يُظنّ أنه يحملها — «هذا الحيّز معزول» — يحملها فحص
                    # الوصول أدناه بلا هذا الافتراض: بلاغ واحد في ١٦٥ نموذجاً.
                    if kind == "windows" and nbrs and e not in boundary:
                        issues.append(
                            "[%s/%s] نافذة على الحافّة %s وهي جدار داخلي يفصله عن "
                            "'%s' — النوافذ على الواجهات، أو حوّلها إلى فتحة داخلية."
                            % (tname, rid, e, nbrs[0]))
                        reported_o += 1
                if reported_o >= PER_CHECK_CAP:
                    break
            if reported_o >= PER_CHECK_CAP:
                break

        # (٤ب) الوصول: هل يمكن بلوغ كل حيّز داخلي من مدخل؟
        # المداخل: حيّز فيه باب على حدّ الأرض، أو رصيف تحميل، أو منطقة مفتوحة.
        internal, entrances = [], []
        for rid, rect in entries:
            if _is_envelope(rid):
                continue
            r = rooms_of.get(rid) or {}
            if _is_outdoor(rid) or _is_open_zone(r) or r.get("docks"):
                entrances.append(rid)
                continue
            internal.append(rid)
            boundary = _on_site_boundary(rect, W, D)
            for o in (r.get("doors") or []):
                if o.get("edge") in boundary:
                    entrances.append(rid)
                    break
        # بلا مدخل معروف لا يُدّعى انعزال: الغياب ليس دليلاً.
        if entrances and internal:
            adj = {rid: [] for rid, _ in entries}
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    a_id, a = entries[i]
                    b_id, bb = entries[j]
                    if _shared_edge(a, bb) >= SHARED_EDGE_MIN:
                        adj[a_id].append(b_id)
                        adj[b_id].append(a_id)
            reach, stack = set(entrances), list(entrances)
            while stack:
                cur = stack.pop()
                for nxt in adj.get(cur, []):
                    if nxt in reach:
                        continue
                    # يُعبَر إلى حيّز إن كان له باب أصلاً — حيّز بلا باب
                    # مرصود سلفاً بفحص «بلا باب» أعلاه.
                    if (rooms_of.get(nxt) or {}).get("doors") \
                            or _is_open_zone(rooms_of.get(nxt) or {}):
                        reach.add(nxt)
                        stack.append(nxt)
            unreachable = [rid for rid in internal
                           if rid not in reach and (rooms_of.get(rid) or {}).get("doors")]
            for rid in unreachable[:PER_CHECK_CAP]:
                issues.append(
                    "[%s/%s] لا يوصل إليه: أبوابه لا تتّصل بأي مسار يبدأ من مدخل — "
                    "أضِف باباً على حافّة مشتركة مع ممرّ أو حيّز موصول."
                    % (tname, rid))

    # Regulatory and security quantities remain NOT_EVALUATED. They are
    # disclosed by the authority planner, never manufactured as repair errors.

    return issues, stats


def format_issues(issues, limit=40):
    head = issues[:limit]
    txt = "\n".join("- " + s for s in head)
    if len(issues) > limit:
        txt += "\n- (و %d مخالفة أخرى مشابهة)" % (len(issues) - limit)
    return txt
