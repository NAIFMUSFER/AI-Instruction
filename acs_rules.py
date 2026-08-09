# -*- coding: utf-8 -*-
# =============================================================================
# acs_rules.py — أساس محرّك قواعد الكود (بنية فقط، بلا أي محتوى تنظيمي).
#
# يجيب فقط: هل *قاعدة موصوفة ببيانات موثّقة* تنطبق على موضوع معيّن، وهل
# مدخلاتها متوفّرة بجودة كافية، وما نتيجة تقييمها؟
# ولا يجيب إطلاقاً: ما الذي يشترطه كود البناء؟ — لا قيمة تنظيمية واحدة هنا.
#
# مبادئ صارمة:
#   • القواعد بيانات لا شيفرة: لا eval/exec ولا تنفيذ تعابير ديناميكية.
#   • لا قاعدة تنظيمية بلا دليل كامل (مصدر موثّق + إصدار + بند + تحقّق).
#   • نقص البيانات لا يصير PASS ولا FAIL أبداً.
#   • المحرّك للقراءة فقط: لا يعدّل الهندسة ولا يصلح شيئاً.
#   • القواعد الاصطناعية (TEST_ONLY) لا تُنتج CODE_REQUIRED ولا تظهر كمطابقة.
# =============================================================================
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_rules.json"), "r", encoding="utf-8") as _f:
    REG = json.load(_f)

SCHEMA = REG["schema"]
ENGINE_VERSION = REG["engine_version"]
STATES = tuple(REG["evaluation_states"])
APPLICABILITY = tuple(REG["applicability_states"])
DATA_QUALITY = tuple(REG["data_quality_states"])
SUBJECT_TYPES = tuple(REG["subject_types"])
UNITS = REG["units"]
OPERATORS = REG["operators"]
CONTRACTS = REG["input_contracts"]
SEVERITIES = tuple(REG["severities"])
COMPLETENESS = tuple(REG["completeness_states"])

# مفاتيح ممنوعة في ملف قواعد مستورد — القواعد بيانات، لا شيفرة
_FORBIDDEN_KEYS = ("script", "code", "js", "eval", "exec", "expression", "fn", "function",
                   "__proto__", "constructor", "prototype")



# ------------------------------------------------------------------ الوحدات --
def unit_dim(u):
    d = UNITS.get(u)
    return d["dim"] if d else None


def to_base(value, unit):
    """يحوّل إلى وحدة الأساس للبُعد. لا مقارنة عبر أبعاد مختلفة."""
    if value is None:
        return None
    u = UNITS.get(unit)
    if u is None:
        return None
    if u.get("div"):
        return float(value) / float(u["div"])
    return float(value) * float(u.get("mul", 1))


def from_base(value, unit):
    if value is None:
        return None
    u = UNITS.get(unit)
    if u is None:
        return None
    if u.get("div"):
        return float(value) * float(u["div"])
    return float(value) / float(u.get("mul", 1))


def _display(value, unit, digits=3):
    """قيمة العرض فقط — لا تُستعمل أبداً في المقارنة."""
    if value is None:
        return None
    v = from_base(value, unit) if unit in UNITS else value
    return round(v, digits) if isinstance(v, (int, float)) else v


# ------------------------------------------------- التحقّق من تعريف القاعدة --
def _has_forbidden(obj, depth=0):
    if depth > 12:
        return True
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in _FORBIDDEN_KEYS:
                return True
            if _has_forbidden(v, depth + 1):
                return True
    elif isinstance(obj, list):
        for v in obj:
            if _has_forbidden(v, depth + 1):
                return True
    elif isinstance(obj, str):
        if obj.strip().lower().startswith(("javascript:", "data:")):
            return True
    return False


def _check_expected(op, expected, issues, prefix=""):
    spec = OPERATORS.get(op)
    if spec is None:
        issues.append(prefix + "unknown operator: %s" % op)
        return
    vt = spec["value_type"]
    if vt == "number":
        if not isinstance(expected.get("value"), (int, float)) or isinstance(expected.get("value"), bool):
            issues.append(prefix + "operator %s requires a numeric expected.value" % op)
        if spec["needs_unit"] and expected.get("unit") not in UNITS:
            issues.append(prefix + "operator %s requires a known unit" % op)
    elif vt == "range":
        for k in ("min", "max"):
            if not isinstance(expected.get(k), (int, float)) or isinstance(expected.get(k), bool):
                issues.append(prefix + "numeric_range requires numeric %s" % k)
        if expected.get("unit") not in UNITS:
            issues.append(prefix + "numeric_range requires a known unit")
    elif vt == "boolean":
        if not isinstance(expected.get("value"), bool):
            issues.append(prefix + "operator %s requires a boolean expected.value" % op)
    elif vt == "list":
        if not isinstance(expected.get("values"), list) or not expected["values"]:
            issues.append(prefix + "operator %s requires a non-empty expected.values list" % op)
    elif vt == "clauses":
        cl = expected.get("clauses")
        if not isinstance(cl, list) or not cl:
            issues.append(prefix + "operator %s requires expected.clauses" % op)
            return
        for i, c in enumerate(cl):
            sub = c.get("operator")
            if sub in ("all_of", "any_of"):
                issues.append(prefix + "clause %d: nested composite operators are not supported" % i)
                continue
            if not c.get("input"):
                issues.append(prefix + "clause %d: missing input key" % i)
            _check_expected(sub, c.get("expected") or {}, issues, prefix + "clause %d: " % i)


def validate_rule(rule):
    """فحص بنيوي + فحص دليل. يعيد قائمة مشاكل (فارغة = تعريف صالح)."""
    issues = []
    if not isinstance(rule, dict):
        return ["rule is not an object"]
    if _has_forbidden(rule):
        issues.append("rule contains a forbidden executable/script field or URL scheme")
    for k in ("rule_id", "operator", "expected", "subject_type", "applies_to", "inputs"):
        if rule.get(k) in (None, "", [], {}):
            if not (k == "inputs" and isinstance(rule.get(k), list)):
                issues.append("missing mandatory field: %s" % k)
    if rule.get("subject_type") not in SUBJECT_TYPES:
        issues.append("unknown subject_type: %s" % rule.get("subject_type"))
    if rule.get("severity") is not None and rule.get("severity") not in SEVERITIES:
        issues.append("unknown severity: %s" % rule.get("severity"))
    inputs = rule.get("inputs") or []
    if not isinstance(inputs, list) or not inputs:
        issues.append("rule declares no inputs")
    else:
        for i in inputs:
            key = (i or {}).get("key")
            if key not in CONTRACTS:
                issues.append("input outside the declared contract: %s" % key)
            u = (i or {}).get("unit")
            if u is not None and u not in UNITS:
                issues.append("unknown input unit: %s" % u)
    _check_expected(rule.get("operator"), rule.get("expected") or {}, issues)
    src = rule.get("source") or {}
    url = src.get("url")
    if url and not str(url).startswith("https://"):
        issues.append("source.url must be https")

    regulatory = rule.get("regulatory") is True
    if regulatory:
        # دليل إلزامي كامل — بغيره لا تُنفَّذ كقاعدة تنظيمية إطلاقاً
        for k in ("standard", "edition", "section"):
            if not rule.get(k):
                issues.append("regulatory rule missing evidence field: %s" % k)
        if not (src.get("document_id") or src.get("url")):
            issues.append("regulatory rule missing source document reference")
        if src.get("verified") is not True:
            issues.append("regulatory rule source is not verified")
        if src.get("type") == "synthetic_test":
            issues.append("regulatory rule may not use a synthetic_test source")
        if rule.get("namespace") == "TEST_ONLY":
            issues.append("regulatory rule may not live in the TEST_ONLY namespace")
    else:
        if rule.get("namespace") != "TEST_ONLY":
            issues.append("non-regulatory rule must declare namespace TEST_ONLY")
        if src.get("type") != "synthetic_test":
            issues.append("non-regulatory rule must declare source.type synthetic_test")
        if not str(rule.get("rule_id") or "").startswith("TEST_ONLY."):
            issues.append("synthetic rule_id must be namespaced TEST_ONLY.")
    return issues


def rule_uid(rule):
    """هوية القاعدة تشمل المعيار والإصدار والبند والمراجعة — لا يتغيّر معناها بصمت."""
    return "|".join([str(rule.get("standard")), str(rule.get("edition")),
                     str(rule.get("section")), str(rule.get("rule_id")),
                     "r%s" % rule.get("revision")])


# ----------------------------------------------------------- سجلّ المصادر --
def sources():
    return [dict(s) for s in REG["sources"]]


def source_by_id(sid):
    for s in REG["sources"]:
        if s["source_id"] == sid:
            return dict(s)
    return None


def validate_ruleset(rs):
    """أمن الاستيراد: يُرفض الملف كاملاً عند مخالفة بنيوية/أمنية."""
    issues = []
    if not isinstance(rs, dict):
        return ["ruleset is not an object"]
    for k in ("ruleset_id", "ruleset_version", "standard", "edition", "rules"):
        if rs.get(k) in (None, ""):
            issues.append("ruleset missing field: %s" % k)
    if rs.get("completeness") not in COMPLETENESS:
        issues.append("unknown completeness: %s" % rs.get("completeness"))
    if rs.get("completeness") == "complete_for_declared_scope" and not rs.get("coverage_scope"):
        issues.append("completeness=complete_for_declared_scope requires a declared coverage_scope")
    if _has_forbidden(rs):
        issues.append("ruleset contains a forbidden executable/script field or URL scheme")
    seen = set()
    for r in (rs.get("rules") or []):
        uid = rule_uid(r)
        if uid in seen:
            issues.append("duplicate rule identity: %s" % uid)
        seen.add(uid)
        if OPERATORS.get(r.get("operator")) is None:
            issues.append("unknown operator in %s: %s" % (r.get("rule_id"), r.get("operator")))
    return issues


def rulesets():
    return [dict(r) for r in REG["rulesets"]]


def ruleset_by_id(rid):
    for r in REG["rulesets"]:
        if r["ruleset_id"] == rid:
            return r
    return None


def all_rules(extra_rulesets=None):
    out = []
    for rs in list(REG["rulesets"]) + list(extra_rulesets or []):
        for r in (rs.get("rules") or []):
            out.append((rs, r))
    return out


def rule_matches(rid, extra_rulesets=None):
    """كل القواعد التي تحمل هذا المعرّف — قد تتعدّد عبر الإصدارات."""
    return [(rs, r) for rs, r in all_rules(extra_rulesets) if r.get("rule_id") == rid]


def rule_by_id(rid, extra_rulesets=None, ruleset_id=None):
    """معرّف القاعدة وحده قد يكون ملتبساً عبر الإصدارات — يُحدَّد بمجموعة عند اللزوم."""
    hits = rule_matches(rid, extra_rulesets)
    if ruleset_id is not None:
        hits = [h for h in hits if h[0].get("ruleset_id") == ruleset_id]
    return hits[0] if hits else (None, None)


def regulatory_rule_count(extra_rulesets=None):
    """عدد القواعد التنظيمية الفعلية القابلة للتنفيذ — يجب أن يكون صفراً في هذه المرحلة."""
    n = 0
    for rs, r in all_rules(extra_rulesets):
        if r.get("regulatory") is True and not validate_rule(r):
            n += 1
    return n


def code_required_allowed(rule_id, extra_rulesets=None):
    """بوّابة CODE_REQUIRED: قاعدة تنظيمية محمّلة، مصدرها موثّق، وتعريفها صالح."""
    hits = rule_matches(rule_id, extra_rulesets)
    if len(hits) != 1:
        return False                     # غير موجودة، أو ملتبسة عبر الإصدارات
    r = hits[0][1]
    if r.get("regulatory") is not True:
        return False
    if ((r.get("source") or {}).get("verified") is not True):
        return False
    return not validate_rule(r)


# --------------------------------------------------------- حلّ المواضيع --
def resolve_subject(building, relationships, subject_id, building_id="bld_0",
                    nav=None, egress=None, distance=None, occupancy_index=None):
    """يحوّل معرّف موضوع نصّي إلى بيانات فعلية من النموذج. لا يخترع بيانات."""
    sid = str(subject_id or "")
    if ":" not in sid:
        return None
    kind, _, ref = sid.partition(":")
    kind = kind.upper()
    if kind not in SUBJECT_TYPES:
        return None
    data = {"building": building, "relationships": relationships, "building_id": building_id}
    if occupancy_index:
        data["occupancy"] = occupancy_index.get(sid)
    if kind == "BUILDING":
        return {"type": kind, "id": sid, "data": data}
    if kind == "SPACE":
        room = _room_of(building, ref, building_id)
        if room is None:
            return None
        data["space_id"] = ref
        data["room"] = room
        return {"type": kind, "id": sid, "data": data}
    if kind == "DOOR":
        sp, _, tail = ref.rpartition(".door_")
        room = _room_of(building, sp, building_id)
        if room is None or not tail.isdigit():
            return None
        doors = room.get("doors") or []
        di = int(tail)
        if di >= len(doors):
            return None
        data["space_id"] = sp
        data["room"] = room
        data["door"] = doors[di]
        data["door_index"] = di
        return {"type": kind, "id": sid, "data": data}
    if kind == "ROUTE":
        if ">" not in ref or nav is None or distance is None:
            return None
        a, _, b = ref.partition(">")
        path = nav.find_path(building, relationships, a, b, building_id)
        data["path"] = path
        data["measurement"] = distance.measure_path(building, path, building_id)
        return {"type": kind, "id": sid, "data": data}
    if kind == "EGRESS":
        if egress is None:
            return None
        res = egress.find_egress(building, relationships, ref, building_id)
        data["egress"] = res
        data["exits"] = egress.extract_exits(building, relationships, building_id)
        data["usable_exits"] = egress.usable_exits(data["exits"])
        return {"type": kind, "id": sid, "data": data}
    return {"type": kind, "id": sid, "data": data}


def _room_of(building, space_id, building_id):
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, r in enumerate(((fdef or {}).get("rooms") or [])):
            sid = r.get("space_id") or "%s.%s.%s" % (building_id, tmpl, r.get("id") or ("sp_%d" % i))
            if sid == space_id:
                return r
    return None


# ------------------------------------------------------- حلّ المدخلات --
_MISSING = {"present": False, "value": None, "unit": None, "provenance": None, "evidence": []}


def _route_provenance(path):
    """أضعف مصدر على المسار — لا تُرقّى البيانات المستنتجة إلى مؤكَّدة."""
    srcs = {str(e.get("source")) for e in (path.get("edges") or []) if e.get("source")}
    for weak in ("system_generated", "geometry_inference", "ai_inference"):
        if weak in srcs:
            return weak
    return "user" if srcs else "system_default"


def resolve_input(key, subject):
    """يحلّ مفتاح مدخل من واجهات النموذج القائمة. لا ينشئ حقيقة غير موجودة."""
    if key not in CONTRACTS:
        return dict(_MISSING, reason="INPUT_NOT_IN_CONTRACT")
    d = subject.get("data") or {}
    t = subject.get("type")
    c = CONTRACTS[key]
    if c["subject"] not in (t, "ANY"):
        return dict(_MISSING, reason="SUBJECT_TYPE_MISMATCH")

    if key.startswith("occupancy."):
        occ = d.get("occupancy")
        field = key.split(".", 1)[1]
        ev = [{"type": "occupancy", "ref": (subject or {}).get("id"),
               "detail": "status=%s records=%s" % ((occ or {}).get("status"),
                                                   (occ or {}).get("records"))}]
        if not occ:
            return dict(_MISSING, reason="OCCUPANCY_NOT_RESOLVED", evidence=ev)
        val = occ.get(field)
        # المجموعة لا تُنشر إلا من تصنيف متحقَّق منه فعلاً
        if field in ("group", "subgroup", "standard", "edition", "jurisdiction_country") \
                and occ.get("status") != "VERIFIED":
            return dict(_MISSING, reason="OCCUPANCY_NOT_VERIFIED", evidence=ev)
        prov = {"USER_DECLARED": "user", "MANUAL_VERIFIED": "user",
                "AUTHORITATIVE_MAPPING": "rule", "AI_SUGGESTED": "ai_inference"}.get(
                    occ.get("source") or "", "system_default")
        return {"present": val is not None, "value": val, "unit": None,
                "provenance": prov, "evidence": ev}

    def ok(v, unit=None, prov="geometry_inference", ev=None):
        return {"present": v is not None, "value": v, "unit": unit,
                "provenance": prov, "evidence": ev or []}

    if t == "ROUTE":
        p = d.get("path") or {}
        m = d.get("measurement") or {}
        prov = _route_provenance(p)
        ev = [{"type": "path", "ref": p.get("from"), "detail": "%s hops" % p.get("hops")}]
        if key == "route.walking_distance_m":
            # قيمة التقييم بدقّة كاملة — لا تُقرَّب قبل المقارنة
            return ok(m.get("walking_distance_exact_m"), "m", prov,
                      ev + [{"type": "measurement", "ref": m.get("distance_status"),
                             "detail": "%d segments" % len(m.get("segments") or [])}])
        if key == "route.distance_status":
            return ok(m.get("distance_status"), None, prov, ev)
        if key == "route.hops":
            return ok(p.get("hops"), "count", prov, ev)
        if key == "route.resolution":
            return ok(p.get("resolution"), None, prov, ev)
        tr = p.get("transitions") or []
        verts = [x for x in tr if x.get("type") == "vertical"]
        if key == "route.door_count":
            return ok(sum(1 for x in tr if x.get("type") == "door"), "count", prov, ev)
        if key == "route.vertical_transition_count":
            return ok(len(verts), "count", prov, ev)
        if key == "route.levels_crossed":
            lv = set()
            for x in verts:
                lv.add(x.get("from_level")); lv.add(x.get("to_level"))
            return ok(max(0, len(lv) - 1) if lv else 0, "count", prov, ev)
        if key == "route.uses_stairs":
            return ok(any(x.get("kind") == "stairs" for x in verts), None, prov, ev)
        if key == "route.uses_elevator":
            return ok(any(x.get("kind") == "elevator" for x in verts), None, prov, ev)

    if t == "EGRESS":
        e = d.get("egress") or {}
        ev = [{"type": "egress", "ref": e.get("status"),
               "detail": "selection_basis=%s" % e.get("selection_basis")}]
        if key == "egress.status":
            return ok(e.get("status"), None, "geometry_inference", ev)
        if key == "egress.walking_distance_m":
            dm = e.get("distance_measurement") or {}
            return ok(dm.get("walking_distance_exact_m"), "m", "geometry_inference", ev)
        if key == "egress.distance_status":
            return ok(e.get("distance_status"), None, "geometry_inference", ev)
        if key == "egress.exit_count":
            return ok(len(d.get("exits") or []), "count", "geometry_inference", ev)
        if key == "egress.usable_exit_count":
            return ok(len(d.get("usable_exits") or []), "count", "geometry_inference", ev)

    if t == "DOOR":
        door = d.get("door") or {}
        ev = [{"type": "door", "ref": subject.get("id"), "detail": "edge=%s" % door.get("edge")}]
        if key == "door.clear_width":
            # حقل مصرَّح فقط — لا يُشتق العرض الحرّ من عرض فتحة أو أي قيمة أخرى
            v = door.get("clear_width_m")
            prov = str(door.get("source") or "user")
            return ok(v, "m", prov, ev) if v is not None else dict(
                _MISSING, reason="FIELD_NOT_PRESENT_IN_MODEL", evidence=ev)
        if key == "door.edge":
            return ok(door.get("edge"), None, str(door.get("source") or "user"), ev)

    if t == "SPACE":
        room = d.get("room") or {}
        rc = room.get("rect") or []
        ev = [{"type": "space", "ref": d.get("space_id"), "detail": "rect=%s" % (rc[:4] if rc else None)}]
        if key == "space.area":
            return ok(float(rc[2]) * float(rc[3]) if len(rc) >= 4 else None, "m2",
                      "geometry_inference", ev)
        if key == "space.level":
            return dict(_MISSING, reason="FIELD_NOT_PRESENT_IN_MODEL", evidence=ev)

    if t == "BUILDING":
        b = d.get("building") or {}
        ev = [{"type": "building", "ref": d.get("building_id"), "detail": "levels=%d"
               % len(b.get("levels") or [])}]
        if key == "building.program":
            v = (b.get("meta") or {}).get("type")
            prov = (b.get("meta") or {}).get("type_source") or "ai_inference"
            return ok(v, None, prov, ev)
        if key == "building.levels_count":
            return ok(len(b.get("levels") or []), "count", "system_default", ev)
        if key == "building.wall_thickness":
            return ok(b.get("wall_t"), "m", "system_default", ev)
    return dict(_MISSING, reason="UNRESOLVED_INPUT")


def _rule_field(rule, path):
    cur = rule
    for part in str(path or "").split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _context_input(key, subject, context):
    """مدخلات الانطباق قد تُحلّ من موضوع آخر (مثلاً برنامج المبنى لمسار)."""
    r = resolve_input(key, subject)
    if r.get("present"):
        return r
    c = CONTRACTS.get(key) or {}
    alt = (context or {}).get("subjects", {}).get(c.get("subject"))
    if alt is not None:
        return resolve_input(key, alt)
    return r


# --------------------------------------------------------- المقيِّمات --
def _cmp_numeric(op, actual_base, expected):
    if op == "numeric_max":
        return actual_base <= to_base(expected["value"], expected["unit"])
    if op == "numeric_min":
        return actual_base >= to_base(expected["value"], expected["unit"])
    if op == "numeric_range":
        return (to_base(expected["min"], expected["unit"]) <= actual_base
                <= to_base(expected["max"], expected["unit"]))
    return None


def _eval_primitive(op, value, unit, expected):
    """يعيد (satisfied, actual_base, required_base) أو (None, ...) عند عدم الدعم."""
    if op in ("numeric_max", "numeric_min", "numeric_range"):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None, None, None
        eu = expected.get("unit")
        if unit_dim(unit) != unit_dim(eu):
            return None, None, None                 # لا مقارنة عبر أبعاد مختلفة
        ab = to_base(value, unit)
        rb = (to_base(expected.get("min"), eu), to_base(expected.get("max"), eu)) \
            if op == "numeric_range" else to_base(expected.get("value"), eu)
        return _cmp_numeric(op, ab, expected), ab, rb
    if op in ("count_min", "count_max"):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None, None, None
        rv = expected.get("value")
        return (value >= rv if op == "count_min" else value <= rv), value, rv
    if op == "boolean_required":
        if not isinstance(value, bool):
            return None, None, None
        return (value is expected.get("value")), value, expected.get("value")
    if op == "existence":
        want = expected.get("value") is not False
        present = value is not None and value != 0 and value is not False
        return (present == want), present, want
    if op == "enumeration":
        return (value in (expected.get("values") or [])), value, list(expected.get("values") or [])
    return None, None, None


# --------------------------------------------------------- التقييم --
def evaluate_rule(rule, subject, context=None, ruleset=None, extra_rulesets=None):
    """تقييم قاعدة واحدة على موضوع واحد. قراءة فقط — لا تعديل للنموذج."""
    context = context or {}
    res = {
        "rule_id": rule.get("rule_id") if isinstance(rule, dict) else None,
        "rule_uid": rule_uid(rule) if isinstance(rule, dict) else None,
        "rule_revision": rule.get("revision") if isinstance(rule, dict) else None,
        "namespace": rule.get("namespace") if isinstance(rule, dict) else None,
        "regulatory": bool(isinstance(rule, dict) and rule.get("regulatory") is True),
        "ruleset_id": (ruleset or {}).get("ruleset_id"),
        "ruleset_version": (ruleset or {}).get("ruleset_version"),
        "standard": rule.get("standard") if isinstance(rule, dict) else None,
        "edition": rule.get("edition") if isinstance(rule, dict) else None,
        "section": rule.get("section") if isinstance(rule, dict) else None,
        "severity": rule.get("severity") if isinstance(rule, dict) else None,
        "status": None, "subject_type": (subject or {}).get("type"),
        "subject_id": (subject or {}).get("id"),
        "applicability": "UNDETERMINED", "data_quality": "NOT_REQUIRED",
        "reason": None, "actual": None, "required": None,
        "input_provenance": {}, "inputs": {}, "evidence": [],
        "applicability_trace": [],
        "engine_version": ENGINE_VERSION, "evaluated_at": context.get("evaluated_at"),
        "code_required_eligible": False,
        "definition_issues": [],
    }

    issues = validate_rule(rule) if isinstance(rule, dict) else ["rule is not an object"]
    if issues:
        res.update(status="INVALID_RULE_DEFINITION", reason="RULE_EVIDENCE_INCOMPLETE",
                   definition_issues=issues)
        return res
    if rule.get("enabled") is False:
        res.update(status="NOT_APPLICABLE", applicability="NOT_APPLICABLE", reason="RULE_DISABLED")
        return res
    if subject is None:
        res.update(status="NOT_EVALUATED", reason="SUBJECT_NOT_RESOLVED")
        return res

    res["evidence"].append({"type": "rule_source", "ref": (rule.get("source") or {}).get("source_id"),
                            "detail": "%s %s %s (verified=%s)" % (
                                rule.get("standard"), rule.get("edition"), rule.get("section"),
                                (rule.get("source") or {}).get("verified"))})

    # --- إصدار مثبّت: مشروع مربوط بإصدار لا يستعمل إصداراً آخر بصمت ---
    pin = context.get("edition_pin") or {}
    if pin.get(rule.get("standard")) not in (None, rule.get("edition")):
        res["applicability_trace"].append(
            {"factor": "edition_pin", "expected": rule.get("edition"),
             "actual": pin.get(rule.get("standard")), "satisfied": False})
        res.update(status="NOT_APPLICABLE", applicability="NOT_APPLICABLE",
                   reason="EDITION_NOT_PINNED")
        return res
    res["applicability_trace"].append(
        {"factor": "edition_pin", "expected": rule.get("edition"),
         "actual": pin.get(rule.get("standard")), "satisfied": True})

    # --- الاختصاص ---
    if rule.get("jurisdiction_required") is True:
        j = context.get("jurisdiction") or {}
        if not j.get("country"):
            res.update(status="NOT_EVALUATED", reason="JURISDICTION_NOT_SET")
            return res
        rj = rule.get("jurisdiction") or {}
        if rj.get("country") and rj["country"] != j.get("country"):
            res["applicability_trace"].append(
                {"factor": "jurisdiction.country", "expected": rj.get("country"),
                 "actual": j.get("country"), "satisfied": False})
            res.update(status="NOT_APPLICABLE", applicability="NOT_APPLICABLE",
                       reason="JURISDICTION_MISMATCH")
            return res
        res["applicability_trace"].append(
            {"factor": "jurisdiction.country", "expected": rj.get("country"),
             "actual": j.get("country"), "satisfied": True})
        res["evidence"].append({"type": "jurisdiction", "ref": j.get("country"),
                                "detail": "declared by project context"})

    # --- الانطباق ---
    at = rule.get("applies_to") or {}
    if at.get("subject_type") and at["subject_type"] != subject.get("type"):
        res["applicability_trace"].append(
            {"factor": "subject_type", "expected": at.get("subject_type"),
             "actual": subject.get("type"), "satisfied": False})
        res.update(status="NOT_APPLICABLE", applicability="NOT_APPLICABLE",
                   reason="SUBJECT_TYPE_MISMATCH")
        return res
    res["applicability_trace"].append(
        {"factor": "subject_type", "expected": at.get("subject_type"),
         "actual": subject.get("type"), "satisfied": True})
    for cond in (at.get("conditions") or []):
        got = _context_input(cond.get("input"), subject, context)
        if not got.get("present"):
            res.update(status="INSUFFICIENT_DATA", applicability="UNDETERMINED",
                       data_quality="MISSING",
                       reason="APPLICABILITY_INPUT_MISSING: %s" % cond.get("input"))
            return res
        v, op, want = got["value"], cond.get("op"), cond.get("value")
        okc = (v in want) if op == "in" else (v == want) if op == "equals" else \
              (v not in want) if op == "not_in" else None
        if okc is None:
            res.update(status="UNSUPPORTED", reason="UNSUPPORTED_APPLICABILITY_OPERATOR: %s" % op)
            return res
        res["applicability_trace"].append(
            {"factor": cond.get("input"), "op": op, "expected": want, "actual": v,
             "satisfied": bool(okc)})
        if not okc:
            res.update(status="NOT_APPLICABLE", applicability="NOT_APPLICABLE",
                       reason="CONDITION_NOT_MET: %s" % cond.get("input"))
            return res
    res["applicability"] = "APPLICABLE"

    # --- حلّ المدخلات ثم بوّابة الجودة ثم وجود المدخلات المطلوبة ---
    # الترتيب مقصود: "الجودة غير كافية" تفسّر غياب القيمة، فهي أصدق من "قيمة مفقودة".
    vals = {}
    for spec in (rule.get("inputs") or []):
        key = spec.get("key")
        got = resolve_input(key, subject)
        vals[key] = got
        res["inputs"][key] = {"present": got.get("present"), "value": got.get("value"),
                              "unit": spec.get("unit") or got.get("unit")}
        if got.get("provenance"):
            res["input_provenance"][key] = got["provenance"]
        for e in (got.get("evidence") or []):
            if e not in res["evidence"]:
                res["evidence"].append(e)

    for spec in (rule.get("inputs") or []):
        q = spec.get("quality")
        if not q:
            continue
        st = resolve_input(q["status_key"], subject)
        res["inputs"][q["status_key"]] = {"present": st.get("present"), "value": st.get("value"),
                                          "unit": None}
        if not st.get("present"):
            res.update(status="INSUFFICIENT_DATA", data_quality="MISSING",
                       reason="MISSING_QUALITY_STATUS: %s" % q["status_key"])
            return res
        if st["value"] not in (q.get("accept") or []):
            res.update(status="NOT_EVALUATED", data_quality="INCOMPLETE",
                       reason=(q.get("reasons") or {}).get(st["value"], "INPUT_QUALITY_INSUFFICIENT"))
            res["evidence"].append({"type": "data_quality", "ref": q["status_key"],
                                    "detail": "actual=%s accept=%s" % (st["value"], q.get("accept"))})
            return res

    # محاذاة معلَنة: قيمة مدخل يجب أن تطابق حقلاً في القاعدة نفسها
    for spec in (rule.get("inputs") or []):
        for al in (spec.get("alignment") or []):
            want = _rule_field(rule, al.get("rule_field"))
            if want is None:
                continue
            got = resolve_input(al.get("input"), subject)
            res["inputs"][al.get("input")] = {"present": got.get("present"),
                                              "value": got.get("value"), "unit": None}
            if not got.get("present"):
                res.update(status="INSUFFICIENT_DATA", data_quality="MISSING",
                           reason="MISSING_ALIGNMENT_INPUT: %s" % al.get("input"))
                return res
            if got.get("value") != want:
                res.update(status="NOT_EVALUATED", data_quality="INCOMPLETE",
                           reason=al.get("reason") or "ALIGNMENT_MISMATCH")
                res["evidence"].append({"type": "alignment", "ref": al.get("input"),
                                        "detail": "actual=%s rule=%s" % (got.get("value"), want)})
                return res

    for spec in (rule.get("inputs") or []):
        key = spec.get("key")
        if spec.get("required") and not vals[key].get("present"):
            res.update(status="INSUFFICIENT_DATA", data_quality="MISSING",
                       reason="MISSING_REQUIRED_INPUT: %s (%s)" % (key, vals[key].get("reason")))
            return res
    res["data_quality"] = "COMPLETE"

    # --- التنفيذ (تصريحي بالكامل — بلا eval) ---
    op = rule.get("operator")
    expected = rule.get("expected") or {}
    if op in ("all_of", "any_of"):
        sub = []
        for c in expected.get("clauses") or []:
            spec = next((s for s in (rule.get("inputs") or []) if s.get("key") == c.get("input")), None)
            got = vals.get(c.get("input")) or {}
            unit = (spec or {}).get("unit") or got.get("unit")
            sat, ab, rb = _eval_primitive(c.get("operator"), got.get("value"), unit,
                                          c.get("expected") or {})
            if sat is None:
                res.update(status="UNSUPPORTED",
                           reason="UNSUPPORTED_CLAUSE: %s/%s" % (c.get("operator"), c.get("input")))
                return res
            sub.append({"input": c.get("input"), "operator": c.get("operator"),
                        "satisfied": bool(sat),
                        "actual": _display(ab, (c.get("expected") or {}).get("unit") or unit),
                        "required": _display(rb, (c.get("expected") or {}).get("unit") or unit)})
        satisfied = all(s["satisfied"] for s in sub) if op == "all_of" \
            else any(s["satisfied"] for s in sub)
        res["actual"] = {"clauses": sub}
        res["required"] = {"operator": op, "clauses": len(sub)}
        res["status"] = "PASS" if satisfied else "FAIL"
    else:
        spec = (rule.get("inputs") or [])[0]
        got = vals.get(spec.get("key")) or {}
        unit = spec.get("unit") or got.get("unit")
        sat, ab, rb = _eval_primitive(op, got.get("value"), unit, expected)
        if sat is None:
            res.update(status="UNSUPPORTED", reason="UNSUPPORTED_OPERATOR_FOR_INPUT: %s" % op)
            return res
        du = expected.get("unit") if OPERATORS[op]["needs_unit"] else None
        res["actual"] = {"value": ab, "unit": (du or unit),
                         "display_value": _display(ab, du) if du else ab,
                         "display_unit": du or unit, "input": spec.get("key")}
        if op == "numeric_range":
            res["required"] = {"operator": op, "min": rb[0], "max": rb[1], "unit": du,
                               "display_min": _display(rb[0], du), "display_max": _display(rb[1], du),
                               "display_unit": du}
        else:
            res["required"] = {"operator": op, "value": rb, "unit": du,
                               "display_value": _display(rb, du) if du else rb,
                               "display_unit": du}
        res["status"] = "PASS" if sat else "FAIL"

    res["code_required_eligible"] = bool(
        res["regulatory"] and res["status"] in ("PASS", "FAIL")
        and (rule.get("source") or {}).get("verified") is True)
    return res


def evaluate_ruleset(ruleset_id, subjects, context=None, extra_rulesets=None):
    """يقيّم كل قواعد مجموعة على قائمة مواضيع. لا تجميع مضلِّل — انظر aggregate."""
    rs = ruleset_by_id(ruleset_id)
    if rs is None:
        for x in (extra_rulesets or []):
            if x.get("ruleset_id") == ruleset_id:
                rs = x
                break
    if rs is None:
        return {"ruleset_id": ruleset_id, "results": [], "error": "RULESET_NOT_FOUND"}
    issues = validate_ruleset(rs)
    if issues:
        return {"ruleset_id": ruleset_id, "results": [], "error": "INVALID_RULESET",
                "issues": issues}
    results = []
    for r in (rs.get("rules") or []):
        for s in subjects:
            results.append(evaluate_rule(r, s, context, rs, extra_rulesets))
    return {"ruleset_id": rs["ruleset_id"], "ruleset_version": rs["ruleset_version"],
            "standard": rs["standard"], "edition": rs["edition"],
            "completeness": rs.get("completeness"), "coverage_scope": rs.get("coverage_scope"),
            "results": results}


def aggregate(results, ruleset=None):
    """تجميع محافظ: لا يقول 'المبنى مطابق' أبداً في هذه المرحلة."""
    counts = {k: 0 for k in ("PASS", "FAIL", "NOT_APPLICABLE", "NOT_EVALUATED",
                             "INSUFFICIENT_DATA", "INVALID_RULE_DEFINITION", "UNSUPPORTED")}
    reg = syn = 0
    for r in results or []:
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1
        if r.get("regulatory"):
            reg += 1
        else:
            syn += 1
    completeness = (ruleset or {}).get("completeness") or "unknown"
    out = {
        "ruleset_id": (ruleset or {}).get("ruleset_id"),
        "ruleset_version": (ruleset or {}).get("ruleset_version"),
        "standard": (ruleset or {}).get("standard"),
        "edition": (ruleset or {}).get("edition"),
        "coverage_scope": (ruleset or {}).get("coverage_scope"),
        "completeness": completeness,
        "rules_evaluated": len(results or []),
        "pass": counts["PASS"], "fail": counts["FAIL"],
        "not_applicable": counts["NOT_APPLICABLE"], "not_evaluated": counts["NOT_EVALUATED"],
        "insufficient_data": counts["INSUFFICIENT_DATA"],
        "invalid_rules": counts["INVALID_RULE_DEFINITION"], "unsupported": counts["UNSUPPORTED"],
        "regulatory_results": reg, "synthetic_results": syn,
        "regulatory_rules_loaded": regulatory_rule_count(),
        "overall_compliance": "NOT_DETERMINED",
        "engine_version": ENGINE_VERSION,
    }
    determinable = (reg > 0 and completeness == "complete_for_declared_scope"
                    and out["not_evaluated"] == 0 and out["insufficient_data"] == 0
                    and out["invalid_rules"] == 0 and out["unsupported"] == 0)
    if determinable:
        out["overall_compliance"] = ("COMPLIANT_WITHIN_DECLARED_SCOPE" if out["fail"] == 0
                                     else "NON_COMPLIANT_WITHIN_DECLARED_SCOPE")
    out["statement"] = (
        "تم التقييم مقابل %d قاعدة مُهيّأة (%d تنظيمية، %d اصطناعية للاختبار). "
        "لا يوجد حكم مطابقة: %s." % (out["rules_evaluated"], reg, syn, out["overall_compliance"]))
    return out


def rule_issues(extra_rulesets=None):
    """كل مشاكل التعريف/الاستيراد في السجلّ الحالي — أداة مطوّر."""
    issues = []
    for rs in list(REG["rulesets"]) + list(extra_rulesets or []):
        for i in validate_ruleset(rs):
            issues.append("[%s] %s" % (rs.get("ruleset_id"), i))
        for r in (rs.get("rules") or []):
            for i in validate_rule(r):
                issues.append("[%s/%s] %s" % (rs.get("ruleset_id"), r.get("rule_id"), i))
    return issues
