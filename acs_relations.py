# -*- coding: utf-8 -*-
# =============================================================================
# acs_relations.py — طبقة العلاقات العامة (Relationships Graph).
#
# ترسم رسماً بيانياً عاماً يمثّل كيف ترتبط الفراغات والمستويات ببعضها.
# عامّة لكل أنواع المباني (سكني/فندقي/صحي/تعليمي/مكتبي/صناعي…) بلا أي تخصيص.
#
# ما لا تفعله هذه الطبقة (بحسب نطاق المرحلة):
#   لا إخلاء · لا حريق · لا MEP · لا إنشائي · لا إتاحة · لا مطابقة أكواد ·
#   لا إيجاد مسارات (pathfinding). حواف بيانات فقط.
#
# مبدأ حاكم: وجود مجسّم لا يُثبت اتصالاً.
#   باب لا يُعرف الفراغ المقابل له  → status="unresolved" و to=None (لا تلفيق).
#   درج على مستوى واحد فقط          → لا تُنشأ حافة رأسية إطلاقاً.
#   لا نُصدر أرقام ثقة (confidence) لأننا لا نملك أساساً كمّياً صادقاً لها.
# =============================================================================

TOUCH_EPS = 0.02      # تلامس فعلي (م)
ADJ_TOL = 0.20        # سماحية بسماكة جدار: ضمنها نعدّها تجاوراً "مُستنتَجاً" (م)
DOOR_PROBE = 0.15     # مسافة الفحص خارج الحافة لتحديد الفراغ المقابل (م)
CORE_TOL = 1.50       # تسامح محاذاة النواة الرأسية بين المستويات (م)

TYPES = ("SPACE_ADJACENT", "SPACE_CONNECTED", "DOOR_CONNECTS",
         "VERTICAL_CONNECTS", "LEVEL_CONNECTS", "BUILDING_ON_SITE")

SOURCES = ("user", "ai_inference", "system_generated", "geometry_inference", "rule")
STATUSES = ("confirmed", "inferred", "unresolved")

_STAIR_WORDS = ("stairs", "stair", "درج", "سلم", "staircase")
_LIFT_WORDS = ("elevator", "lift", "مصعد")


def _kind_of(o):
    raw = str(o.get("kind") or o.get("name") or "").strip().lower()
    for w in _LIFT_WORDS:
        if w in raw:
            return "elevator"
    for w in _STAIR_WORDS:
        if w in raw:
            return "stairs"
    return None


def _rect(r):
    try:
        x, z, w, d = [float(v) for v in (r.get("rect") or [])[:4]]
        return x, z, w, d
    except Exception:
        return None


def _is_container(a, b):
    """هل a يحتوي b كلياً؟ (الغلاف الصناعي مثلاً يحتوي كل المناطق)"""
    ax, az, aw, ad = a
    bx, bz, bw, bd = b
    return (ax - 0.01 <= bx and az - 0.01 <= bz and
            ax + aw + 0.01 >= bx + bw and az + ad + 0.01 >= bz + bd and
            (aw * ad) > (bw * bd))


def _space_id(building_id, tmpl, room, i):
    return room.get("space_id") or "%s.%s.%s" % (building_id, tmpl, room.get("id") or ("sp_%d" % i))


def _gap_and_overlap(a, b):
    """يعيد (الفجوة بين الحافتين المتقابلتين, طول التداخل) أو (None, 0) إن لم يتقابلا."""
    ax, az, aw, ad = a
    bx, bz, bw, bd = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)          # تداخل على X
    oz = min(az + ad, bz + bd) - max(az, bz)          # تداخل على Z
    best = (None, 0.0)
    if oz > TOUCH_EPS:                                # حافتان رأسيتان (شرق/غرب)
        for gap in (abs(bx - (ax + aw)), abs(ax - (bx + bw))):
            if best[0] is None or gap < best[0]:
                best = (gap, oz)
    if ox > TOUCH_EPS:                                # حافتان أفقيتان (شمال/جنوب)
        for gap in (abs(bz - (az + ad)), abs(az - (bz + bd))):
            if best[0] is None or gap < best[0]:
                best = (gap, ox)
    return best


def _levels_for(building, tmpl):
    return sorted(int(l.get("index", 0)) for l in (building.get("levels") or [])
                  if l.get("template") == tmpl)


def _level_id(building, building_id, index):
    for l in building.get("levels") or []:
        if int(l.get("index", 0)) == index:
            return l.get("id") or "%s.flr_%d" % (building_id, index)
    return "%s.flr_%d" % (building_id, index)


def build_relationships(building, building_id="bld_0"):
    """يبني حواف العلاقات لمبنى واحد. لا يعدّل الهندسة ولا يضيف أي عنصر."""
    rels = []
    seq = [0]

    def add(rtype, frm, to, source, status, via=None, meta=None):
        seq[0] += 1
        e = {"id": "%s.rel_%d" % (building_id, seq[0]), "type": rtype,
             "from": frm, "to": to, "source": source, "status": status}
        if via is not None:
            e["via"] = via
        if meta:
            e["meta"] = meta
        rels.append(e)
        return e

    floors = building.get("floors") or {}

    # دليل معماري اختياري: إن أمكن تصريف الهندسة، فالباب المستضاف على جدار
    # يفصل فراغين بالضبط يرفع الحافة من inferred إلى confirmed. غيابه لا يخفض
    # شيئاً ولا يحذف حافة — الاستنتاج الهندسي القديم يبقى كما هو.
    try:
        import acs_arch as _AR
        _arch = _AR.compile_architecture(building, building_id)
    except Exception:
        _AR, _arch = None, None

    def _door_evidence(via, sid, other):
        if _AR is None or _arch is None:
            return None
        ev = _AR.door_connects_confirmed(_arch, via)
        if not ev or set(ev.get("spaces") or []) != {sid, other}:
            return None
        return ev

    # ---- 1) تجاور الفراغات + أبوابها (لكل قالب دور على حدة) ----
    for tmpl, fdef in floors.items():
        rooms = [r for r in ((fdef or {}).get("rooms") or []) if _rect(r)]
        recs = [(_space_id(building_id, tmpl, r, i), _rect(r), r) for i, r in enumerate(rooms)]

        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                sid_a, ra, _ = recs[i]
                sid_b, rb, _ = recs[j]
                if _is_container(ra, rb) or _is_container(rb, ra):
                    continue                                   # الغلاف ليس تجاوراً
                gap, ov = _gap_and_overlap(ra, rb)
                if gap is None or gap > ADJ_TOL or ov <= TOUCH_EPS:
                    continue
                add("SPACE_ADJACENT", sid_a, sid_b, "geometry_inference",
                    "confirmed" if gap <= TOUCH_EPS else "inferred",
                    meta={"gap": round(gap, 3), "overlap": round(ov, 2), "template": tmpl})

        # أبواب: نحدّد الفراغ المقابل هندسياً، وإلا نتركها unresolved
        for sid, rc, room in recs:
            x, z, w, d = rc
            for di, dr in enumerate(room.get("doors") or []):
                e = str(dr.get("edge") or "N").upper()[:1]
                off = float(dr.get("offset") or 0)
                if e == "N":
                    px, pz = x + off, z - DOOR_PROBE
                elif e == "S":
                    px, pz = x + off, z + d + DOOR_PROBE
                elif e == "W":
                    px, pz = x - DOOR_PROBE, z + off
                else:
                    px, pz = x + w + DOOR_PROBE, z + off
                via = dr.get("id") or "%s.door_%d" % (sid, di)
                cands = []
                for sid2, rc2, _r2 in recs:
                    if sid2 == sid or _is_container(rc2, rc):
                        continue
                    bx, bz, bw, bd = rc2
                    if bx - 0.01 <= px <= bx + bw + 0.01 and bz - 0.01 <= pz <= bz + bd + 0.01:
                        cands.append(sid2)
                if len(cands) == 1:
                    ev = _door_evidence(via, sid, cands[0])
                    meta = {"edge": e, "template": tmpl}
                    if ev:
                        meta["wall_id"] = ev["wall_id"]
                        meta["evidence_basis"] = ev["basis"]
                    add("DOOR_CONNECTS", sid, cands[0], "geometry_inference",
                        "confirmed" if ev else "inferred", via=via, meta=meta)
                else:
                    add("DOOR_CONNECTS", sid, None, "geometry_inference", "unresolved",
                        via=via, meta={"edge": e, "template": tmpl,
                                       "reason": "ambiguous" if cands else "no_adjacent_space",
                                       "candidates": len(cands)})

    # ---- 2) الاتصال الرأسي: تجميع "نوى رأسية" حسب الموضع عبر المستويات ----
    # الدليل الهندسي = عنصر رأسي (درج/مصعد) يظهر في الموضع نفسه على مستويين
    # متتاليين (سواء تكرّر قالب الدور أو تطابق موضعه في قالبين مختلفين).
    # ظهوره على مستوى واحد فقط لا يُثبت شيئاً ⇒ unresolved بلا حافة.
    inst = []
    for tmpl, fdef in floors.items():
        lv = _levels_for(building, tmpl)
        for i, room in enumerate(((fdef or {}).get("rooms") or [])):
            rc = _rect(room)
            if not rc:
                continue
            sid = _space_id(building_id, tmpl, room, i)
            for oi, o in enumerate(room.get("objects") or []):
                k = _kind_of(o)
                if not k:
                    continue
                ox = float(o.get("x")) if o.get("x") is not None else rc[2] / 2.0
                oz = float(o.get("z")) if o.get("z") is not None else rc[3] / 2.0
                via = "%s.%s_%d" % (sid, k, oi)
                for li in (lv or [None]):
                    inst.append({"level": li, "kind": k, "x": rc[0] + ox, "z": rc[1] + oz,
                                 "via": via, "space": sid})

    cores = []                                        # تجميع بالموضع (تسامح CORE_TOL)
    for it in inst:
        for c in cores:
            if c["kind"] == it["kind"] and abs(c["x"] - it["x"]) <= CORE_TOL and abs(c["z"] - it["z"]) <= CORE_TOL:
                c["items"].append(it)
                break
        else:
            cores.append({"kind": it["kind"], "x": it["x"], "z": it["z"], "items": [it]})

    level_pairs = {}
    for c in cores:
        lvls = sorted({i["level"] for i in c["items"] if i["level"] is not None})
        via = sorted({i["via"] for i in c["items"]})[0]
        if len(lvls) < 2:
            add("VERTICAL_CONNECTS",
                _level_id(building, building_id, lvls[0]) if lvls else None, None,
                "geometry_inference", "unresolved", via=via,
                meta={"kind": c["kind"], "serviced_levels": lvls,
                      "reason": "single_level_instance"})
            continue
        ep = {}
        for i in c["items"]:
            if i["level"] is not None and str(i["level"]) not in ep:
                ep[str(i["level"])] = i["space"]
        for a, b in zip(lvls, lvls[1:]):
            fa, fb = _level_id(building, building_id, a), _level_id(building, building_id, b)
            add("VERTICAL_CONNECTS", fa, fb, "geometry_inference", "inferred", via=via,
                meta={"kind": c["kind"], "serviced_levels": lvls,
                      "from_space": ep.get(str(a)), "to_space": ep.get(str(b)),
                      "from_level": a, "to_level": b})
            level_pairs.setdefault((fa, fb), set()).add(c["kind"])

    # ---- 3) LEVEL_CONNECTS مشتقّة من الحواف الرأسية المُثبتة ----
    for (fa, fb), kinds in sorted(level_pairs.items()):
        add("LEVEL_CONNECTS", fa, fb, "system_generated", "inferred",
            meta={"kinds": sorted(kinds)})

    return rels


def build_project_relationships(project):
    """علاقات على مستوى المشروع: BUILDING_ON_SITE (وتجنّب تصادم المعرّفات)."""
    pr = (project or {}).get("project") or {}
    site_id = (pr.get("site") or {}).get("id") or "site_0"
    out, n = [], 0
    for b in pr.get("buildings") or []:
        n += 1
        out.append({"id": "%s.rel_%d" % (pr.get("id") or "prj_0", n),
                    "type": "BUILDING_ON_SITE",
                    "from": b.get("id"), "to": site_id,
                    "source": "system_generated", "status": "confirmed",
                    "meta": {"position": b.get("position") or {"x": 0, "z": 0, "rotation": 0},
                             "building_type": b.get("building_type")}})
    return out


def validate_relationships(rels, building=None, building_id="bld_0", allow_cross_building=False):
    """فحوص بنيوية فقط (لا قواعد هندسية): معرّفات معلّقة · روابط ذاتية ·
    تكرار · مستويات غير موجودة · via ناقص · روابط عابرة للمباني بلا إذن."""
    issues = []
    known_spaces, known_levels = set(), set()
    if building:
        for tmpl, fdef in (building.get("floors") or {}).items():
            for i, r in enumerate(((fdef or {}).get("rooms") or [])):
                known_spaces.add(_space_id(building_id, tmpl, r, i))
        for l in building.get("levels") or []:
            known_levels.add(l.get("id") or "%s.flr_%d" % (building_id, int(l.get("index", 0))))

    seen, ids = set(), set()
    for e in rels or []:
        rid, t = e.get("id"), e.get("type")
        if rid in ids:
            issues.append("duplicate relationship id: %s" % rid)
        ids.add(rid)
        if t not in TYPES:
            issues.append("unknown relationship type: %s" % t)
        if e.get("source") not in SOURCES:
            issues.append("[%s] invalid source: %s" % (rid, e.get("source")))
        if e.get("status") not in STATUSES:
            issues.append("[%s] invalid status: %s" % (rid, e.get("status")))
        if e.get("status") == "rule" or e.get("source") == "rule":
            issues.append("[%s] source=rule requires real rule evidence (none in this phase)" % rid)

        frm, to = e.get("from"), e.get("to")
        if frm and to and frm == to:
            issues.append("[%s] self-link: %s" % (rid, frm))
        if e.get("status") != "unresolved" and (frm is None or to is None):
            issues.append("[%s] resolved edge missing endpoint" % rid)
        if t == "DOOR_CONNECTS" and not e.get("via"):
            issues.append("[%s] DOOR_CONNECTS requires 'via'" % rid)

        key = (t, frm, to, e.get("via"))
        if key in seen:
            issues.append("[%s] duplicate edge %s" % (rid, str(key)))
        seen.add(key)

        if building:
            for ep in (frm, to):
                if not ep:
                    continue
                if t in ("VERTICAL_CONNECTS", "LEVEL_CONNECTS"):
                    if ep not in known_levels:
                        issues.append("[%s] dangling level ref: %s" % (rid, ep))
                elif t in ("SPACE_ADJACENT", "SPACE_CONNECTED", "DOOR_CONNECTS"):
                    if ep not in known_spaces:
                        issues.append("[%s] dangling space ref: %s" % (rid, ep))
                if not allow_cross_building and not str(ep).startswith(building_id + "."):
                    issues.append("[%s] cross-building reference without permission: %s" % (rid, ep))
    return issues


def summary(rels):
    out = {}
    for e in rels or []:
        out[e.get("type")] = out.get(e.get("type"), 0) + 1
    out["unresolved"] = sum(1 for e in (rels or []) if e.get("status") == "unresolved")
    out["total"] = len(rels or [])
    return out
