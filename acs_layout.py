# -*- coding: utf-8 -*-
# =============================================================================
# acs_layout.py  --  حلّ التداخلات المكانية حسابياً (بلا LLM)
# النماذج اللغوية ضعيفة في رصّ المستطيلات؛ نحلّها هنا بخوارزمية فصل تكرارية
# تُزيح الغرف أقلّ إزاحة ممكنة حتى تختفي التداخلات، مع إبقائها داخل الأرض.
#
# سلطة التغيير (F-01):
#   كل ما في هذا الملفّ يقع خارج الحدّ القانوني: النموذج القانوني هو خرج التوليد
#   المقبول، وهذا المصلِح يأتي بعده. لذلك الوضع الافتراضي AUTHORITY_PROPOSE:
#   لا يُكتَب شيء في النموذج، وتُولَّد اقتراحات ENGINEERING_CHANGE_PROPOSAL.
#   الوضع AUTHORITY_APPLY لا يُستعمل إلا داخل حساب الاقتراحات على نسخة، أو بعد
#   موافقة صريحة عبر مسار التأليف الواحد.
#   كل تغيير يُوسَم بمعرّف مسجَّل في acs_engineering_changes.json — والوسم إجباري:
#   معرّف غير مسجَّل يرفع KeyError عند التصنيف، فلا يوجد تعديل صامت ممكن.
# =============================================================================

EPS = 0.02

AUTHORITY_PROPOSE = "PROPOSE"
AUTHORITY_APPLY = "APPLY"


class _NullRecorder(object):
    """مسجّل لا يفعل شيئاً — يبقي المسار الحسابي واحداً بلا فروع شرطية."""

    __slots__ = ()

    def record(self, *a, **k):
        return None


_NULL = _NullRecorder()


def _rects_overlap(a, b):
    ax, az, aw, ad = a; bx, bz, bw, bd = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oz = min(az + ad, bz + bd) - max(az, bz)
    return (ox, oz) if (ox > EPS and oz > EPS) else None


def _clamp(r, W, D):
    x, z, w, d = r
    w = min(w, W); d = min(d, D)
    x = max(0.0, min(x, W - w))
    z = max(0.0, min(z, D - d))
    return [round(x, 2), round(z, 2), round(w, 2), round(d, 2)]


def _tid(ctx, room):
    return "%s.%s" % (ctx or "?", room.get("id") if isinstance(room, dict) else room)


def resolve_overlaps(rooms, W, D, iterations=400, skip=("parapet", "سور"),
                     rec=_NULL, ctx=None):
    """يُزيح الغرف المتداخلة أقلّ إزاحة. يعيد (عدد التداخلات المتبقية, عدد المحرّكة)."""
    idx = [i for i, r in enumerate(rooms)
           if not any(s in str(r.get("id", "")).lower() for s in skip)]
    rects = {i: [float(v) for v in rooms[i]["rect"]] for i in idx}
    original = {i: list(v) for i, v in rects.items()}

    for _ in range(iterations):
        moved = False
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                ov = _rects_overlap(rects[i], rects[j])
                if not ov:
                    continue
                ox, oz = ov
                ri, rj = rects[i], rects[j]
                if ox <= oz:                      # افصل أفقياً (الأقل تكلفة)
                    push = ox / 2 + EPS
                    if ri[0] < rj[0]:
                        ri[0] -= push; rj[0] += push
                    else:
                        ri[0] += push; rj[0] -= push
                else:                             # افصل رأسياً
                    push = oz / 2 + EPS
                    if ri[1] < rj[1]:
                        ri[1] -= push; rj[1] += push
                    else:
                        ri[1] += push; rj[1] -= push
                moved = True
        # أبقِ الجميع داخل الأرض
        for i in idx:
            x, z, w, d = rects[i]
            rects[i] = [max(0.0, min(x, W - min(w, W))),
                        max(0.0, min(z, D - min(d, D))),
                        min(w, W), min(d, D)]
        if not moved:
            break

    # اكتب النتائج
    n_moved = 0
    for i in idx:
        new = _clamp(rects[i], W, D)
        old = original[i]
        if any(abs(new[k] - old[k]) > 0.03 for k in range(4)):
            n_moved += 1
        # اقتطاع القياس (w أو d) تغيير أبعاد لا إزاحة: يُسجَّل باسمه
        if abs(new[2] - old[2]) > 0.005 or abs(new[3] - old[3]) > 0.005:
            rec.record("LAYOUT_CLAMP_TO_SITE", _tid(ctx, rooms[i]), "rect",
                       {"rect": list(old)}, {"rect": list(new)},
                       detail="clamped inside the site rectangle")
        elif abs(new[0] - old[0]) > 0.005 or abs(new[1] - old[1]) > 0.005:
            rec.record("LAYOUT_RESOLVE_OVERLAPS", _tid(ctx, rooms[i]), "rect",
                       {"rect": list(old)}, {"rect": list(new)},
                       detail="separated from an overlapping neighbour")
        rooms[i]["rect"] = new

    # عُدّ المتبقي
    remaining = 0
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if _rects_overlap([float(v) for v in rooms[idx[a]]["rect"]],
                              [float(v) for v in rooms[idx[b]]["rect"]]):
                remaining += 1
    return remaining, n_moved


def fix_openings(room, rec=_NULL, ctx=None):
    """يبقي الأبواب/النوافذ ضمن طول الحافة."""
    x, z, w, d = [float(v) for v in room["rect"]]
    for kind in ("doors", "windows"):
        for i, o in enumerate(room.get(kind) or []):
            e = o.get("edge", "N")
            span = w if e in ("N", "S") else d
            old_w = o.get("width")
            old_off = o.get("offset")
            ow = min(float(o.get("width", 0.9)), max(span - 0.2, 0.3))
            new_w = round(ow, 2)
            new_off = round(min(max(float(o.get("offset", span / 2)), ow / 2 + 0.05),
                                span - ow / 2 - 0.05), 2)
            tid = o.get("id") or "%s.%s_%d" % (_tid(ctx, room), kind[:-1], i)
            if old_w is None or abs(float(old_w) - new_w) > 0.005:
                rec.record("LAYOUT_OPENING_WIDTH_FIT", tid, "width",
                           {"width": old_w}, {"width": new_w},
                           detail="shrunk to fit the host edge (%s, span %.2f m)"
                                  % (e, span))
            if old_off is None or abs(float(old_off) - new_off) > 0.005:
                rec.record("LAYOUT_OPENING_OFFSET_SET", tid, "offset",
                           {"offset": old_off}, {"offset": new_off},
                           detail="offset invented" if old_off is None
                           else "offset clamped into the edge")
            o["width"] = new_w
            o["offset"] = new_off
    return room


def fix_points(room, rec=_NULL, ctx=None):
    """يبقي نقاط الكهرباء/الإنارة داخل حدود الغرفة، ويضبط ارتفاعاتها القياسية."""
    x, z, w, d = [float(v) for v in room["rect"]]
    H = {"outlet": 0.40, "switch": 1.20, "network": 0.40, "usb": 0.55}
    for i, p in enumerate(room.get("points") or []):
        old_x, old_z, old_h = p.get("x"), p.get("z"), p.get("height")
        nx = round(min(max(float(p.get("x", w / 2)), 0.1), max(w - 0.1, 0.1)), 2)
        nz = round(min(max(float(p.get("z", d / 2)), 0.1), max(d - 0.1, 0.1)), 2)
        tid = "%s.point_%d" % (_tid(ctx, room), i)
        if old_x is None or old_z is None \
                or abs(float(old_x) - nx) > 0.005 or abs(float(old_z) - nz) > 0.005:
            rec.record("LAYOUT_POINT_CLAMP", tid, "position",
                       {"x": old_x, "z": old_z, "type": p.get("type")},
                       {"x": nx, "z": nz, "type": p.get("type")},
                       detail="kept inside the host space")
        p["x"] = nx
        p["z"] = nz
        t = p.get("type")
        if t in H and p.get("height") is not None:
            if abs(float(old_h) - H[t]) > 0.005:
                rec.record("LAYOUT_POINT_HEIGHT_STANDARD", tid, "height",
                           {"height": old_h, "type": t}, {"height": H[t], "type": t},
                           detail="a user-stated height replaced by the standard table")
            p["height"] = H[t]
    for i, f in enumerate(room.get("furniture") or []):
        old_x, old_z = f.get("x"), f.get("z")
        nx = round(min(max(float(f.get("x", w / 2)), 0.2), max(w - 0.2, 0.2)), 2)
        nz = round(min(max(float(f.get("z", d / 2)), 0.2), max(d - 0.2, 0.2)), 2)
        if old_x is None or old_z is None \
                or abs(float(old_x) - nx) > 0.005 or abs(float(old_z) - nz) > 0.005:
            rec.record("LAYOUT_FURNITURE_CLAMP",
                       "%s.furniture_%d" % (_tid(ctx, room), i), "position",
                       {"x": old_x, "z": old_z}, {"x": nx, "z": nz},
                       detail="kept inside the host space")
        f["x"] = nx
        f["z"] = nz
    return room


def shelf_pack(rooms, W, D, margin=0.15, gap=0.05, rec=_NULL, ctx=None):
    """رصّ صفّي مضمون بلا تداخل: يحافظ على الترتيب المكاني الأصلي (صفوف من الشمال للجنوب).
    يعيد True إن نجح رصّ الجميع داخل الأرض."""
    order = sorted(range(len(rooms)),
                   key=lambda i: (float(rooms[i]["rect"][1]), float(rooms[i]["rect"][0])))
    cx = margin; cz = margin; row_d = 0.0; ok = True
    for i in order:
        old = [float(v) for v in rooms[i]["rect"]]
        w, d = float(rooms[i]["rect"][2]), float(rooms[i]["rect"][3])
        w = min(w, W - 2 * margin); d = min(d, D - 2 * margin)
        if cx + w > W - margin:                 # ابدأ صفاً جديداً
            cx = margin; cz += row_d + gap; row_d = 0.0
        if cz + d > D - margin:                 # لا مساحة كافية
            ok = False
            cz = max(margin, D - margin - d)    # ضعها في آخر صف متاح
        new = [round(cx, 2), round(cz, 2), round(w, 2), round(d, 2)]
        if any(abs(new[k] - old[k]) > 0.005 for k in range(4)):
            rec.record("LAYOUT_SHELF_PACK", _tid(ctx, rooms[i]), "rect",
                       {"rect": old}, {"rect": new},
                       detail="repositioned by the shelf packer")
        rooms[i]["rect"] = new
        cx += w + gap; row_d = max(row_d, d)
    return ok


def area_fits(rooms, W, D, factor=0.92):
    """هل مجموع مساحات الغرف يسع داخل الأرض (مع هامش للجدران)؟"""
    total = sum(float(r["rect"][2]) * float(r["rect"][3]) for r in rooms)
    return total <= W * D * factor, round(total, 1), round(W * D, 1)


def ensure_essentials(room, W=None, D=None, industrial=False, strict=False,
                      rec=_NULL, ctx=None):
    """يُكمل النواقص الإلزامية: باب، إنارة، كاشف دخان، أفياش — بلا LLM.

    كل ما يُضاف هنا يُوسَم "auto": true ويُسجَّل بمعرّف تغيير مصنّف اقتراحاً هندسياً.
    وفي الوضع الصارم (strict) لا نُضيف شيئاً إطلاقاً — وصف العميل هو المرجع الوحيد.
    """
    if strict:
        return room
    from acs_validate import _is_outdoor, _is_open_zone, _is_envelope
    rid = str(room.get("id", ""))
    low = rid.lower()
    if _is_outdoor(rid) or "parking" in low:
        return room
    x, z, w, d = [float(v) for v in room["rect"]]
    area = w * d
    tid = _tid(ctx, room)

    def _added(change_id, items, field, note):
        rec.record(change_id, tid, field, {field: []}, {field: items}, detail=note)

    if industrial:
        # منطقة مفتوحة/غلاف: لا أبواب ولا أفياش لكل حيّز — لكن إنارة وإنذار إلزاميان
        if _is_open_zone(room) or _is_envelope(rid):
            pts = room.setdefault("points", [])
            kinds = [p.get("type") for p in pts]
            if area >= 3.0 and not any(k in ("light", "spot") for k in kinds):
                # شبكة إنارة صناعية: نقطة لكل ~100 م² بحد أقصى معقول
                n = max(1, min(int(area / 110) + 1, 24))
                cols = max(1, int(round((n * w / max(d, 0.1)) ** 0.5)))
                rows = max(1, int(round(n / cols)))
                new = []
                for i in range(cols):
                    for j in range(rows):
                        new.append({"type": "light", "auto": True,
                                    "x": round(w * (i + 0.5) / cols, 2),
                                    "z": round(d * (j + 0.5) / rows, 2)})
                pts.extend(new)
                _added("LAYOUT_ADD_INDUSTRIAL_LIGHT", new, "points",
                       "generated industrial lighting grid (%d points)" % len(new))
            if area >= 6.0 and "smoke" not in kinds and "sprinkler" not in kinds:
                n = max(1, min(int(area / 140) + 1, 20))
                new = [{"type": "sprinkler", "auto": True,
                        "x": round(w * (i + 0.5) / n, 2), "z": round(d / 2, 2)}
                       for i in range(n)]
                pts.extend(new)
                _added("LAYOUT_ADD_SPRINKLER", new, "points",
                       "generated %d sprinkler points in an open industrial zone" % n)
            return room
        # غرف إدارية داخل المستودع تُعامل معاملة الغرف العادية (تكمل بالأسفل)

    # باب على الحافة الأطول (يفتح نحو الممر غالباً)
    if not room.get("doors"):
        edge = "N" if w >= d else "W"
        span = w if edge in ("N", "S") else d
        wid = 0.8 if any(k in low for k in ("bath", "wc", "toilet", "حمام", "دورة")) else 0.9
        wid = min(wid, max(span - 0.3, 0.6))
        new = [{"edge": edge, "offset": round(span / 2, 2), "auto": True,
                "width": round(wid, 2), "height": 2.1, "material": "wood"}]
        room["doors"] = new
        _added("LAYOUT_ADD_DOOR", new, "doors",
               "the space declared no door; one was invented on edge %s" % edge)

    pts = room.setdefault("points", [])
    kinds = [p.get("type") for p in pts]

    if area >= 3.0 and not any(k in ("light", "spot") for k in kinds):
        new = [{"type": "light", "auto": True, "x": round(w / 2, 2), "z": round(d / 2, 2)}]
        pts.extend(new)
        _added("LAYOUT_ADD_LIGHT", new, "points", "no lighting point was declared")

    if area >= 6.0 and "smoke" not in kinds:
        new = [{"type": "smoke", "auto": True, "x": round(w / 2, 2), "z": round(d / 2, 2)}]
        pts.extend(new)
        _added("LAYOUT_ADD_SMOKE_DETECTOR", new, "points",
               "no smoke detector was declared for a %.1f m² space" % area)

    # أفياش أساسية إن لم توجد (غرف معيشة/نوم)
    if area >= 6.0 and "outlet" not in kinds:
        new = [{"type": "outlet", "auto": True, "x": fx,
                "z": round(max(d - 0.25, 0.2), 2)}
               for fx in (round(w * 0.25, 2), round(w * 0.75, 2))]
        pts.extend(new)
        _added("LAYOUT_ADD_OUTLET", new, "points", "no socket outlet was declared")

    # مفتاح إنارة عند الباب
    if area >= 4.0 and "switch" not in kinds:
        dr = room["doors"][0]
        e = dr.get("edge", "N"); off = float(dr.get("offset", w / 2))
        if e in ("N", "S"):
            new = [{"type": "switch", "auto": True,
                    "x": round(min(max(off + 0.6, 0.2), w - 0.2), 2),
                    "z": round(0.3 if e == "N" else d - 0.3, 2)}]
        else:
            new = [{"type": "switch", "auto": True,
                    "x": round(0.3 if e == "W" else w - 0.3, 2),
                    "z": round(min(max(off + 0.6, 0.2), d - 0.2), 2)}]
        pts.extend(new)
        _added("LAYOUT_ADD_SWITCH", new, "points", "no light switch was declared")

    return room


def _autofix_apply(building, rec):
    """الخوارزمية الحسابية كما هي — تُشغَّل على نسخة عند حساب الاقتراحات، أو على
    النموذج نفسه بعد موافقة صريحة. لا تُستدعى تلقائياً من أي مسار توليد."""
    from acs_validate import _is_envelope, building_type
    industrial = building_type(building) in ("warehouse", "industrial", "factory", "logistics")
    strict = bool((building.get("meta") or {}).get("strict"))
    site = building.get("site", {})
    W = float(site.get("w", 30)); D = float(site.get("d", 25))
    report = {"moved": 0, "remaining": 0, "templates": 0, "packed": [], "tight": [],
              "industrial": industrial}
    for tmpl, fdef in (building.get("floors") or {}).items():
        allr = [r for r in (fdef.get("rooms") or []) if r.get("rect") and len(r["rect"]) == 4]
        if not allr:
            continue
        report["templates"] += 1
        # استثنِ الغلاف الخارجي/الأسوار من الرصّ (تحتوي البقية بطبيعتها)
        rooms = [r for r in allr if not _is_envelope(r.get("id", ""))]

        if industrial:
            rem, mv = resolve_overlaps(rooms, W, D, rec=rec, ctx=tmpl)
            report["moved"] += mv; report["remaining"] += rem
            for r in allr:
                ensure_essentials(r, W, D, industrial=True, strict=strict,
                                  rec=rec, ctx=tmpl)
                fix_openings(r, rec=rec, ctx=tmpl); fix_points(r, rec=rec, ctx=tmpl)
            continue

        if strict:            # لا نُعيد رصّ ما رسمه العميل، نكتفي بفضّ التداخل الحقيقي
            rem, mv = resolve_overlaps(rooms, W, D, rec=rec, ctx=tmpl)
            report["moved"] += mv; report["remaining"] += rem
            for r in allr:
                ensure_essentials(r, W, D, strict=True, rec=rec, ctx=tmpl)
                fix_openings(r, rec=rec, ctx=tmpl); fix_points(r, rec=rec, ctx=tmpl)
            continue

        fits, total, cap = area_fits(rooms, W, D)
        if not fits:
            report["tight"].append("%s: مجموع الغرف %.0f م² > الأرض %.0f م²" % (tmpl, total, cap))

        rem, mv = resolve_overlaps(rooms, W, D, rec=rec, ctx=tmpl)
        if rem > 0:                 # الفصل لم يكفِ → رصّ صفّي مضمون
            shelf_pack(rooms, W, D, rec=rec, ctx=tmpl)
            rem, _ = resolve_overlaps(rooms, W, D, iterations=60, rec=rec, ctx=tmpl)
            report["packed"].append(tmpl)
            # ما زال متداخلاً → قلّص الغرف تناسبياً حتى تتّسع (يحفظ النِسَب)
            shrink = 1.0
            for _ in range(8):
                if rem == 0:
                    break
                shrink *= 0.93
                for r in rooms:
                    x, z, w, d = [float(v) for v in r["rect"]]
                    new = [x, z, round(w * 0.93, 2), round(d * 0.93, 2)]
                    rec.record("LAYOUT_PROPORTIONAL_SHRINK", _tid(tmpl, r), "rect",
                               {"rect": [x, z, w, d]}, {"rect": new},
                               detail="shrunk 7%% so the template fits the site")
                    r["rect"] = new
                shelf_pack(rooms, W, D, rec=rec, ctx=tmpl)
                rem, _ = resolve_overlaps(rooms, W, D, iterations=40, rec=rec, ctx=tmpl)
            if shrink < 1.0:
                report["tight"].append("%s: قُلّصت الغرف %.0f%% لتتّسع في مسطح البناء"
                                       % (tmpl, (1 - shrink) * 100))
        report["moved"] += mv; report["remaining"] += rem
        for r in allr:
            ensure_essentials(r, W, D, strict=strict, rec=rec, ctx=tmpl)
            fix_openings(r, rec=rec, ctx=tmpl); fix_points(r, rec=rec, ctx=tmpl)
    return report


def autofix(building, authority=AUTHORITY_PROPOSE, recorder=None):
    """المدخل الوحيد للمصلِح الحسابي.

    AUTHORITY_PROPOSE (الافتراضي): لا يُكتَب حرف في النموذج الهندسي. يُحسَب ما كان
        سيتغيّر على نسخة، ويعود التقرير ومعه قائمة اقتراحات.
    AUTHORITY_APPLY: يطبّق فعلاً. لا يُستعمل إلا داخل حساب الاقتراحات على نسخة،
        أو من مسار موافقة صريحة. تمريره من مسار توليد يعني تغييراً صامتاً.
    """
    if authority == AUTHORITY_APPLY:
        return _autofix_apply(building, recorder or _NULL)
    if authority != AUTHORITY_PROPOSE:
        raise ValueError("unknown engineering authority mode: %r" % (authority,))
    import acs_engineering_authority as EA
    planned = EA.plan(building)
    report = dict(planned["report"])
    report["authority"] = AUTHORITY_PROPOSE
    report["applied"] = False
    report["proposals"] = planned["proposals"]
    report["safe_changes"] = planned["safe_changes"]
    report["model_hash_before"] = planned["model_hash_before"]
    report["model_hash_after"] = planned["model_hash_after"]
    return report
