# -*- coding: utf-8 -*-
# =============================================================================
# acs_layout.py  --  حلّ التداخلات المكانية حسابياً (بلا LLM)
# النماذج اللغوية ضعيفة في رصّ المستطيلات؛ نحلّها هنا بخوارزمية فصل تكرارية
# تُزيح الغرف أقلّ إزاحة ممكنة حتى تختفي التداخلات، مع إبقائها داخل الأرض.
# =============================================================================

EPS = 0.02


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


def resolve_overlaps(rooms, W, D, iterations=400, skip=("parapet", "سور")):
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
        if any(abs(new[k] - original[i][k]) > 0.03 for k in range(4)):
            n_moved += 1
        rooms[i]["rect"] = new

    # عُدّ المتبقي
    remaining = 0
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if _rects_overlap([float(v) for v in rooms[idx[a]]["rect"]],
                              [float(v) for v in rooms[idx[b]]["rect"]]):
                remaining += 1
    return remaining, n_moved


def fix_openings(room):
    """يبقي الأبواب/النوافذ ضمن طول الحافة."""
    x, z, w, d = [float(v) for v in room["rect"]]
    for kind in ("doors", "windows"):
        for o in (room.get(kind) or []):
            e = o.get("edge", "N")
            span = w if e in ("N", "S") else d
            ow = min(float(o.get("width", 0.9)), max(span - 0.2, 0.3))
            o["width"] = round(ow, 2)
            o["offset"] = round(min(max(float(o.get("offset", span / 2)), ow / 2 + 0.05),
                                    span - ow / 2 - 0.05), 2)
    return room


def fix_points(room):
    """يبقي نقاط الكهرباء/الإنارة داخل حدود الغرفة، ويضبط ارتفاعاتها القياسية."""
    x, z, w, d = [float(v) for v in room["rect"]]
    H = {"outlet": 0.40, "switch": 1.20, "network": 0.40, "usb": 0.55}
    for p in (room.get("points") or []):
        p["x"] = round(min(max(float(p.get("x", w / 2)), 0.1), max(w - 0.1, 0.1)), 2)
        p["z"] = round(min(max(float(p.get("z", d / 2)), 0.1), max(d - 0.1, 0.1)), 2)
        t = p.get("type")
        if t in H and p.get("height") is not None:
            p["height"] = H[t]
    for f in (room.get("furniture") or []):
        f["x"] = round(min(max(float(f.get("x", w / 2)), 0.2), max(w - 0.2, 0.2)), 2)
        f["z"] = round(min(max(float(f.get("z", d / 2)), 0.2), max(d - 0.2, 0.2)), 2)
    return room


def shelf_pack(rooms, W, D, margin=0.15, gap=0.05):
    """رصّ صفّي مضمون بلا تداخل: يحافظ على الترتيب المكاني الأصلي (صفوف من الشمال للجنوب).
    يعيد True إن نجح رصّ الجميع داخل الأرض."""
    order = sorted(range(len(rooms)),
                   key=lambda i: (float(rooms[i]["rect"][1]), float(rooms[i]["rect"][0])))
    cx = margin; cz = margin; row_d = 0.0; ok = True
    for i in order:
        w, d = float(rooms[i]["rect"][2]), float(rooms[i]["rect"][3])
        w = min(w, W - 2 * margin); d = min(d, D - 2 * margin)
        if cx + w > W - margin:                 # ابدأ صفاً جديداً
            cx = margin; cz += row_d + gap; row_d = 0.0
        if cz + d > D - margin:                 # لا مساحة كافية
            ok = False
            cz = max(margin, D - margin - d)    # ضعها في آخر صف متاح
        rooms[i]["rect"] = [round(cx, 2), round(cz, 2), round(w, 2), round(d, 2)]
        cx += w + gap; row_d = max(row_d, d)
    return ok


def area_fits(rooms, W, D, factor=0.92):
    """هل مجموع مساحات الغرف يسع داخل الأرض (مع هامش للجدران)؟"""
    total = sum(float(r["rect"][2]) * float(r["rect"][3]) for r in rooms)
    return total <= W * D * factor, round(total, 1), round(W * D, 1)


def ensure_essentials(room, W=None, D=None, industrial=False):
    """يُكمل النواقص الإلزامية: باب، إنارة، كاشف دخان، أفياش — بلا LLM."""
    from acs_validate import _is_outdoor, _is_open_zone, _is_envelope
    rid = str(room.get("id", ""))
    low = rid.lower()
    if _is_outdoor(rid) or "parking" in low:
        return room
    x, z, w, d = [float(v) for v in room["rect"]]
    area = w * d

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
                for i in range(cols):
                    for j in range(rows):
                        pts.append({"type": "light",
                                    "x": round(w * (i + 0.5) / cols, 2),
                                    "z": round(d * (j + 0.5) / rows, 2)})
            if area >= 6.0 and "smoke" not in kinds and "sprinkler" not in kinds:
                n = max(1, min(int(area / 140) + 1, 20))
                for i in range(n):
                    pts.append({"type": "sprinkler",
                                "x": round(w * (i + 0.5) / n, 2), "z": round(d / 2, 2)})
            return room
        # غرف إدارية داخل المستودع تُعامل معاملة الغرف العادية (تكمل بالأسفل)

    added = []

    # باب على الحافة الأطول (يفتح نحو الممر غالباً)
    if not room.get("doors"):
        edge = "N" if w >= d else "W"
        span = w if edge in ("N", "S") else d
        wid = 0.8 if any(k in low for k in ("bath", "wc", "toilet", "حمام", "دورة")) else 0.9
        wid = min(wid, max(span - 0.3, 0.6))
        room["doors"] = [{"edge": edge, "offset": round(span / 2, 2),
                          "width": round(wid, 2), "height": 2.1, "material": "wood"}]
        added.append("door")

    pts = room.setdefault("points", [])
    kinds = [p.get("type") for p in pts]

    if area >= 3.0 and not any(k in ("light", "spot") for k in kinds):
        pts.append({"type": "light", "x": round(w / 2, 2), "z": round(d / 2, 2)})
        added.append("light")

    if area >= 6.0 and "smoke" not in kinds:
        pts.append({"type": "smoke", "x": round(w / 2, 2), "z": round(d / 2, 2)})
        added.append("smoke")

    # أفياش أساسية إن لم توجد (غرف معيشة/نوم)
    if area >= 6.0 and "outlet" not in kinds:
        for fx in (round(w * 0.25, 2), round(w * 0.75, 2)):
            pts.append({"type": "outlet", "x": fx, "z": round(max(d - 0.25, 0.2), 2)})
        added.append("outlets")

    # مفتاح إنارة عند الباب
    if area >= 4.0 and "switch" not in kinds:
        dr = room["doors"][0]
        e = dr.get("edge", "N"); off = float(dr.get("offset", w / 2))
        if e in ("N", "S"):
            pts.append({"type": "switch", "x": round(min(max(off + 0.6, 0.2), w - 0.2), 2),
                        "z": round(0.3 if e == "N" else d - 0.3, 2)})
        else:
            pts.append({"type": "switch", "x": round(0.3 if e == "W" else w - 0.3, 2),
                        "z": round(min(max(off + 0.6, 0.2), d - 0.2), 2)})
        added.append("switch")

    return room


def autofix(building):
    """يطبّق الإصلاح الحسابي على كل قوالب الأدوار. يعيد تقريراً.

    المباني الصناعية تختلف جوهرياً: مناطق المستودع *يجب* أن تملأ كامل المسطح
    وتتلامس تماماً — فالرصّ الصفّي والتقليص التناسبي يفسدان المخطط. لذلك نكتفي
    فيها بفضّ التداخلات الحقيقية وإبقاء كل شيء داخل الأرض.
    """
    from acs_validate import _is_envelope, building_type
    industrial = building_type(building) in ("warehouse", "industrial", "factory", "logistics")
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
            rem, mv = resolve_overlaps(rooms, W, D)
            report["moved"] += mv; report["remaining"] += rem
            for r in allr:
                ensure_essentials(r, W, D, industrial=True)
                fix_openings(r); fix_points(r)
            continue

        fits, total, cap = area_fits(rooms, W, D)
        if not fits:
            report["tight"].append("%s: مجموع الغرف %.0f م² > الأرض %.0f م²" % (tmpl, total, cap))

        rem, mv = resolve_overlaps(rooms, W, D)
        if rem > 0:                 # الفصل لم يكفِ → رصّ صفّي مضمون
            shelf_pack(rooms, W, D)
            rem, _ = resolve_overlaps(rooms, W, D, iterations=60)
            report["packed"].append(tmpl)
            # ما زال متداخلاً → قلّص الغرف تناسبياً حتى تتّسع (يحفظ النِسَب)
            shrink = 1.0
            for _ in range(8):
                if rem == 0:
                    break
                shrink *= 0.93
                for r in rooms:
                    x, z, w, d = [float(v) for v in r["rect"]]
                    r["rect"] = [x, z, round(w * 0.93, 2), round(d * 0.93, 2)]
                shelf_pack(rooms, W, D)
                rem, _ = resolve_overlaps(rooms, W, D, iterations=40)
            if shrink < 1.0:
                report["tight"].append("%s: قُلّصت الغرف %.0f%% لتتّسع في مسطح البناء"
                                       % (tmpl, (1 - shrink) * 100))
        report["moved"] += mv; report["remaining"] += rem
        for r in allr:
            ensure_essentials(r, W, D)
            fix_openings(r); fix_points(r)
    return report
