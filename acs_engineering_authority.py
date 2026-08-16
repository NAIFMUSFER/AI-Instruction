# -*- coding: utf-8 -*-
# =============================================================================
# acs_engineering_authority.py — سلطة التغيير الهندسي.
#
# المبدأ الوحيد: النظام لا يملك سلطة هندسية.
#   • ما كان تطبيعاً ميكانيكياً معلناً (SAFE_NORMALIZATION) يُطبَّق ويُوثَّق مصدره.
#   • ما مسّ نيّة التصميم (ENGINEERING_PROPOSAL) يصير اقتراحاً لا يُودَع إلا بموافقة
#     صريحة، ويمرّ عندها بمسار التأليف الواحد لا بمسار ثانٍ.
#
# الحدّ القانوني: النموذج القانوني يبدأ عند خرج التوليد المقبول. كل ما بعده —
# وعلى رأسه المصلِح الحسابي في acs_layout — خارج الحدّ.
#
# بصمة النموذج المستعملة هنا هي acs_authoring.model_hash عمداً: هي البصمة التي
# تحرسها بوّابة الإيداع نفسها، فالمقارنة قبل/بعد تقيس ما تقيسه البوّابة بالضبط.
# (acs_revision.model_hash بصمة أخرى تُجرّد المتغيّرات الزائلة — لا تُخلَط بها.)
# =============================================================================
import hashlib
import json
import os

import acs_ingest as _ing

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_engineering_changes.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
CLASSES = tuple(SPEC["classes"])
SAFE = "SAFE_NORMALIZATION"
PROPOSAL = "ENGINEERING_PROPOSAL"
RULES = {r["change_id"]: r for r in SPEC["rules"]}
REMOVED = {r["id"]: r for r in SPEC["removed_behaviours"]}

# أوضاع المصلِح الحسابي
AUTHORITY_PROPOSE = "PROPOSE"   # الافتراضي: لا كتابة هندسية إطلاقاً
AUTHORITY_APPLY = "APPLY"       # بعد موافقة صريحة فقط، أو في اختبار مرجعي معلن

SOURCE_SYSTEM = "SYSTEM"


# --------------------------------------------------------------- أدوات ----
def _canon(o):
    return _ing.canonical_json(o)


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _copy(v):
    return json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v


def classify(change_id):
    """يعيد قاعدة السجلّ. المعرّف غير المسجَّل ليس تغييراً مسموحاً."""
    rule = RULES.get(change_id)
    if rule is None:
        raise KeyError(
            "unregistered engineering change '%s' — every change must be declared in "
            "acs_engineering_changes.json before any code may perform it" % change_id)
    return rule


def is_safe(change_id):
    return classify(change_id)["class"] == SAFE


def model_hash(model, building_id="bld_0"):
    """بصمة النموذج القانوني — نفس ترميز بوّابة الإيداع بالضبط.

    الحساب مكرَّر هنا عمداً بدل استيراد acs_authoring: طبقة التأليف مرآة متصفّح
    ولا تُشحَن في صورة الخادم، واستيرادها هنا كان يجرّها إلى إغلاق الاستيراد.
    التطابق ليس ادّعاءً — يُثبَت في اختبار تكافؤ صريح مقابل acs_authoring.model_hash.
    """
    return hashlib.sha256(_canon({"scope": "building",
                                  "building_id": building_id,
                                  "model": model}).encode("utf-8")).hexdigest()


# ------------------------------------------------------------ الاقتراح ----
def proposal(change_id, target_ids, before, after, reason=None,
             base_revision=None, model_hash_before=None, detail=None):
    """يبني ENGINEERING_CHANGE_PROPOSAL بالشكل المُعلَن. لا يودع شيئاً."""
    rule = classify(change_id)
    if rule["class"] != PROPOSAL:
        raise ValueError("'%s' is declared %s — it must not become a proposal"
                         % (change_id, rule["class"]))
    body = {
        "type": change_id,
        "target_ids": sorted(str(t) for t in (target_ids or [])),
        "before": before,
        "after": after,
        "base_revision": base_revision,
        "model_hash_before": model_hash_before,
    }
    return {
        "proposal_id": "prop:" + _sha16(body),
        "type": change_id,
        "target_ids": body["target_ids"],
        "before": before,
        "after": after,
        "reason": reason or rule["reason"],
        "detail": detail,
        "source": SOURCE_SYSTEM,
        "engineering_authority": False,
        "committed": False,
        "requires_explicit_confirmation": True,
        "base_revision": base_revision,
        "model_hash_before": model_hash_before,
        "authoring_command": rule.get("authoring_command"),
        "provenance": {"registry": SCHEMA, "change_id": change_id,
                       "source_module": rule["source_module"],
                       "class": rule["class"]},
    }


class Recorder(object):
    """يلتقط كل تغيير يحاوله المصلِح الحسابي: المعرّف، الهدف، قبل، بعد.

    الوسم إجباري: تغيير بلا change_id مسجَّل يرفع KeyError عند التصنيف، فلا يوجد
    مسار صامت يمكن أن يتسلّل منه تعديل غير معلن."""

    def __init__(self):
        self.events = []

    def record(self, change_id, target_id, field, before, after, detail=None):
        rule = classify(change_id)
        if before == after:
            return
        self.events.append({"change_id": change_id, "class": rule["class"],
                            "target_id": str(target_id), "field": field,
                            "before": before, "after": after, "detail": detail})

    # فرز الأحداث إلى مجموعات اقتراح واحدة لكل (change_id, target_id)
    def grouped(self):
        out = {}
        for e in self.events:
            key = (e["change_id"], e["target_id"])
            g = out.setdefault(key, {"change_id": e["change_id"],
                                     "target_id": e["target_id"],
                                     "class": e["class"],
                                     "before": {}, "after": {}, "details": []})
            # أوّل "قبل" هو الحالة الأصلية، وآخر "بعد" هو الحالة النهائية.
            # القيم المسجَّلة قواميس حالة أصلاً، فتُدمَج ولا تُعشَّش تحت اسم الحقل.
            b = e["before"] if isinstance(e["before"], dict) else {e["field"]: e["before"]}
            a = e["after"] if isinstance(e["after"], dict) else {e["field"]: e["after"]}
            for k, v in b.items():
                g["before"].setdefault(k, v)
            for k, v in a.items():
                if k in ("points", "doors", "windows") and isinstance(v, list) \
                        and isinstance(g["after"].get(k), list):
                    g["after"][k] = list(g["after"][k]) + list(v)
                else:
                    g["after"][k] = v
            if e["detail"]:
                g["details"].append(e["detail"])
        return [out[k] for k in sorted(out.keys())]

    def safe_events(self):
        return [e for e in self.events if e["class"] == SAFE]

    def proposal_events(self):
        return [e for e in self.events if e["class"] == PROPOSAL]


# ------------------------------------------------- توليد الاقتراحات -------
def _issue_targets(building):
    """أوّل قالب دور وأوّل غرفة صالحة — هدف افتراضي لاقتراحات مستوى المبنى."""
    for tmpl, fdef in sorted((building.get("floors") or {}).items()):
        for r in (fdef.get("rooms") or []):
            if r.get("rect") and len(r["rect"]) == 4:
                return tmpl, str(r.get("id") or "")
    return None, None


def _all_points(building):
    out = []
    for tmpl, fdef in sorted((building.get("floors") or {}).items()):
        for r in (fdef.get("rooms") or []):
            for p in (r.get("points") or []):
                out.append((tmpl, str(r.get("id") or ""), p))
    return out


def code_gap_proposals(building, base_revision=None, building_id="bld_0",
                       hash_before=None):
    """يحوّل نواقص السلامة والأمن التي يرصدها acs_validate إلى اقتراحات.

    لا يُطبَّق منها شيء. القرار للمستخدم، والنظام يعرض النقص والبديل فقط.
    هذه هي الاستجابة الصحيحة لِما كان يُغري بالإصلاح التلقائي."""
    import acs_validate as V
    hb = hash_before if hash_before is not None else model_hash(building, building_id)
    props = []
    tmpl, rid = _issue_targets(building)
    if tmpl is None:
        return props
    target = "%s.%s" % (tmpl, rid)
    pts = [p.get("type") for (_t, _r, p) in _all_points(building)]

    site = building.get("site") or {}
    try:
        area = float(site.get("w", 0)) * float(site.get("d", 0))
    except (TypeError, ValueError):
        area = 0.0

    def add(change_id, before, after, reason, detail=None):
        props.append(proposal(change_id, [target], before, after, reason=reason,
                              base_revision=base_revision, model_hash_before=hb,
                              detail=detail))

    n_exit = pts.count("exit")
    if n_exit < 4:
        add("FLS_ADD_EXIT", {"exit_count": n_exit}, {"exit_count": 4},
            "المخارج المذكورة %d من 4. الإضافة قرار سلامة أرواح ولا تتمّ آلياً."
            % n_exit,
            detail={"missing": 4 - n_exit, "point_type": "exit"})

    n_cam = pts.count("camera")
    if n_cam < 6:
        add("SEC_ADD_CAMERA", {"camera_count": n_cam}, {"camera_count": 6},
            "الكاميرات المذكورة %d من 6. تغيير العدد قرار أمني يحتاج موافقة."
            % n_cam,
            detail={"missing": 6 - n_cam, "point_type": "camera"})

    need_ext = max(1, int(area / 200) + 1) if area > 0 else 1
    n_ext = pts.count("extinguisher")
    if n_ext < need_ext:
        add("FLS_ADD_EXTINGUISHER", {"extinguisher_count": n_ext},
            {"extinguisher_count": need_ext},
            "الطفّايات المذكورة %d والمطلوب %d لمساحة %.0f م²."
            % (n_ext, need_ext, area),
            detail={"missing": need_ext - n_ext, "point_type": "extinguisher"})

    if "assembly" not in pts:
        add("FLS_ADD_ASSEMBLY_POINT", {"assembly_count": 0}, {"assembly_count": 1},
            "لا توجد نقطة تجمّع (assembly) خارج مسار الحركة.",
            detail={"missing": 1, "point_type": "assembly"})

    # ممرّات صناعية دون الحدّ الأدنى — تُرصَد ولا تُوسَّع أبداً
    for tmpl2, fdef in sorted((building.get("floors") or {}).items()):
        for r in (fdef.get("rooms") or []):
            rid2 = str(r.get("id") or "")
            low = rid2.lower()
            if not any(k in low for k in ("aisle", "corridor", "ممر", "lane")):
                continue
            rect = r.get("rect")
            if not (isinstance(rect, list) and len(rect) == 4):
                continue
            try:
                w, d = float(rect[2]), float(rect[3])
            except (TypeError, ValueError):
                continue
            width = min(w, d)
            need = float(V.IND_AISLE.get("forklift", 3.4)) \
                if "forklift" in low or "رافع" in low else float(V.MIN_CORRIDOR_W)
            if width + 1e-9 < need:
                t2 = "%s.%s" % (tmpl2, rid2)
                props.append(proposal(
                    "LAYOUT_AISLE_WIDTH", [t2],
                    {"rect": [float(v) for v in rect], "width_m": round(width, 3)},
                    {"width_m": round(need, 3)},
                    reason="عرض الممرّ %.2f م دون الحدّ المذكور %.2f م. التوسيع "
                           "يزيح ما حوله ولا يتمّ آلياً." % (width, need),
                    base_revision=base_revision, model_hash_before=hb,
                    detail={"axis": "w" if w <= d else "d", "required_m": need}))
    return props


def site_expansion_proposal(building, base_revision=None, building_id="bld_0",
                            hash_before=None):
    """البديل غير الهدّام للتقليص: توسيع الأرض بدل تصغير كل الغرف."""
    import acs_layout as L
    site = building.get("site") or {}
    try:
        W = float(site.get("w", 0)); D = float(site.get("d", 0))
    except (TypeError, ValueError):
        return None
    if W <= 0 or D <= 0:
        return None
    from acs_validate import _is_envelope
    worst = None
    for tmpl, fdef in sorted((building.get("floors") or {}).items()):
        rooms = [r for r in (fdef.get("rooms") or [])
                 if r.get("rect") and len(r["rect"]) == 4
                 and not _is_envelope(r.get("id", ""))]
        if not rooms:
            continue
        fits, total, cap = L.area_fits(rooms, W, D)
        if not fits and (worst is None or total > worst[0]):
            worst = (total, cap, tmpl)
    if worst is None:
        return None
    total, cap, tmpl = worst
    # أصغر تكبير متناسب يجعل المجموع يتّسع بهامش الجدران نفسه (0.92)
    factor = (total / (W * D * 0.92)) ** 0.5
    nw = round(W * factor + 0.005, 2)
    nd = round(D * factor + 0.005, 2)
    hb = hash_before if hash_before is not None else model_hash(building, building_id)
    return proposal(
        "LAYOUT_SITE_EXPANSION", ["site"],
        {"w": W, "d": D, "area_m2": round(W * D, 2)},
        {"w": nw, "d": nd, "area_m2": round(nw * nd, 2)},
        reason="مجموع مساحات القالب %s يبلغ %.0f م² والأرض %.0f م². التوسيع بديل "
               "غير هدّام لتقليص الغرف — كلاهما اقتراح لا يُطبَّق آلياً."
               % (tmpl, total, cap),
        base_revision=base_revision, model_hash_before=hb,
        detail={"template": tmpl, "rooms_area_m2": round(total, 2),
                "alternative_to": "LAYOUT_PROPORTIONAL_SHRINK"})


# ----------------------------------------------------------- التخطيط ------
def plan(building, base_revision=None, building_id="bld_0", include_code_gaps=True):
    """يحسب كل ما كان النظام سيغيّره — بلا أن يغيّر شيئاً منه.

    يعيد:
      {"model_hash_before", "model_hash_after", "proposals":[...],
       "safe_changes":[...], "report":{...}, "unchanged": bool}

    ضمانة صريحة: `building` يخرج من هذه الدالّة ببصمة مطابقة تماماً لبصمته عند
    الدخول، فيما عدا تطبيعات SAFE_NORMALIZATION المعلنة في السجلّ."""
    import acs_layout as L
    # التطبيعات الآمنة أوّلاً — فتصير البصمة المرجعية بصمة النموذج القانوني نفسه
    # التي ستُقارَن بها بعد التخطيط، ويصير معنى unchanged حرفياً: لم يتغيّر شيء.
    safe = apply_safe_normalisations(building, building_id=building_id)
    hb = model_hash(building, building_id)
    rec = Recorder()
    work = _copy(building)
    report = L.autofix(work, authority=AUTHORITY_APPLY, recorder=rec)

    props = []
    for g in rec.grouped():
        if g["class"] != PROPOSAL:
            continue
        props.append(proposal(
            g["change_id"], [g["target_id"]], g["before"], g["after"],
            base_revision=base_revision, model_hash_before=hb,
            detail={"events": len(g["details"]) or None,
                    "notes": g["details"][:4] or None}))

    if include_code_gaps:
        props.extend(code_gap_proposals(building, base_revision, building_id, hb))
        sp = site_expansion_proposal(building, base_revision, building_id, hb)
        if sp is not None:
            props.append(sp)

    ha = model_hash(building, building_id)
    return {"model_hash_before": hb, "model_hash_after": ha,
            "unchanged": ha == hb,
            "proposals": props, "safe_changes": safe,
            "report": report,
            "registry": {"schema": SCHEMA, "version": VERSION}}


def plan_with_model(building, base_revision=None, building_id="bld_0",
                    include_code_gaps=True):
    """`plan()` مع النموذج الذي طُبِّقت عليه التطبيعات الآمنة فعلاً.

    W1-B. `plan()` يطبّق SAFE_NORMALIZATION **على الكائن الممرَّر** — وهذا
    عقده المُعلَن. لكنه يعمل داخل عامل CPU منفصل (KI-14/F-46)، والعامل يستلم
    نسخةً مُسلسَلة، فالتطبيع يقع على نسخة الابن وحدها. ما يعود إلى الأب هو
    قاموس النتيجة فقط، فكان الردّ يقول «طُبِّقت أربع تطبيعات آمنة» ويُرجع
    نموذجاً لا يحوي واحدة منها — و`model_hash_before` يصف كائن العامل لا
    الكائن المُعاد.

    مُقاس: نموذج بـ rect=[0,0,10.004,8.0079] وبلا floor_height يعود إلى
    العميل بـ rect غير مُدوَّر و`floor_height=None`، بينما الردّ يعلن
    UNDERSTAND_STRUCTURAL_DEFAULTS و LAYOUT_ROUND_RECT مطبَّقتين. وغياب
    `floor_height` بالذات هو عائلة عطل KI-25 نفسها: العارض يشتقّ
    `baseY = index × floor_height`.

    لا يتغيّر نموذج السلطة: SAFE_NORMALIZATION تُطبَّق كما كانت،
    وENGINEERING_PROPOSAL تبقى اقتراحاً لا يُودَع. الفرق الوحيد أن النموذج
    الذي طُبِّقت عليه هو النموذج الذي يعود.
    """
    out = plan(building, base_revision=base_revision, building_id=building_id,
               include_code_gaps=include_code_gaps)
    return {"plan": out, "building": building}


def apply_safe_normalisations(building, building_id="bld_0"):
    """يطبّق التطبيعات المصنّفة آمنة فقط، ويوثّق مصدر كل واحدة.

    لا شيء هنا يغيّر معنى هندسياً: تدوير قيمة موجودة إلى منزلتين، وملء ثابت
    بنيوي غائب أصلاً بقيمة معلنة."""
    applied = []
    prov = building.setdefault("meta", {}).setdefault("acs_provenance", {})
    defaults = prov.setdefault("system_defaults", {})

    # 1) ثوابت بنيوية غائبة — تُملأ ولا تُستبدَل أبداً
    for field, value in (("floor_height", 3.2), ("wall_h", 3.0), ("wall_t", 0.15)):
        if building.get(field) is None:
            building[field] = value
            defaults[field] = {"value": value, "source": "system_default",
                               "change_id": "UNDERSTAND_STRUCTURAL_DEFAULTS"}
            applied.append({"change_id": "UNDERSTAND_STRUCTURAL_DEFAULTS",
                            "target_id": "building", "field": field,
                            "before": None, "after": value})

    # 2) تدوير المستطيلات إلى الترميز القانوني (حدّ التسامح 0.005 م)
    tol = float(classify("LAYOUT_ROUND_RECT")["tolerance_m"])
    for tmpl, fdef in sorted((building.get("floors") or {}).items()):
        for r in (fdef.get("rooms") or []):
            rect = r.get("rect")
            if not (isinstance(rect, list) and len(rect) == 4):
                continue
            new = []
            for v in rect:
                try:
                    new.append(round(float(v), 2) + 0.0)
                except (TypeError, ValueError):
                    new = None
                    break
            if new is None:
                continue
            old = [float(v) for v in rect]
            if new == old:
                continue
            if any(abs(new[k] - old[k]) > tol for k in range(4)):
                # تجاوز التسامح ⇒ ليس تدويراً: لا يُطبَّق هنا إطلاقاً
                continue
            r["rect"] = new
            applied.append({"change_id": "LAYOUT_ROUND_RECT",
                            "target_id": "%s.%s" % (tmpl, r.get("id")),
                            "field": "rect", "before": old, "after": new})
    if not defaults:
        prov.pop("system_defaults", None)
    if not prov:
        building["meta"].pop("acs_provenance", None)
    return applied


# الموافقة والرفض يعيشان في acs_engineering_approval.py — يستوردان طبقة
# التأليف، وهي مرآة متصفّح لا تُشحَن في صورة الخادم. الفصل مقصود.


def _flatten(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for k in sorted(value.keys(), key=str):
            out.update(_flatten(value[k], "%s.%s" % (prefix, k) if prefix else str(k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(_flatten(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = value
    return out


def flat_diff(before, after, limit=400):
    """فرق مُسطَّح بين نموذجين — للعرض قبل أي استبدال، لا للإيداع.

    مكرَّر عمداً عن acs_authoring.revision_diff للسبب نفسه الذي كُرِّرت له البصمة:
    طبقة التأليف لا تُشحَن في صورة الخادوم."""
    a = _flatten(before or {})
    b = _flatten(after or {})
    added, removed, changed = [], [], []
    for k in sorted(set(b) - set(a)):
        added.append({"path": k, "after": b[k]})
    for k in sorted(set(a) - set(b)):
        removed.append({"path": k, "before": a[k]})
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            changed.append({"path": k, "before": a[k], "after": b[k]})
    total = len(added) + len(removed) + len(changed)
    return {"available": True, "added": added[:limit], "removed": removed[:limit],
            "changed": changed[:limit], "total_changes": total,
            "truncated": total > limit}


def health_status():
    """حالة السجلّ — تُعرَض في /health بلا أي سرّ."""
    counts = {SAFE: 0, PROPOSAL: 0}
    for r in SPEC["rules"]:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    return {"schema": SCHEMA, "version": VERSION,
            "rules": len(SPEC["rules"]),
            "safe_normalisations": counts[SAFE],
            "engineering_proposals": counts[PROPOSAL],
            "auto_commit_path": False,
            "default_authority": AUTHORITY_PROPOSE}
