# -*- coding: utf-8 -*-
# =============================================================================
# acs_occupancy.py — أساس التصنيف النظامي للإشغال وسياق الكود للمشروع.
#
# يفصل بصرامة بين أربعة أشياء تُخلط عادةً:
#   BUILDING PROGRAM ≠ REGULATORY OCCUPANCY ≠ PROJECT JURISDICTION ≠ RULESET ACTIVATION
#
# مبادئ صارمة:
#   • برنامج المبنى (فيلا/فندق/عيادة/مستودع) لا يُنشئ تصنيفاً نظامياً أبداً؛
#     أقصى ما يفعله: اقتراح مرشّحين يحتاجون مراجعة.
#   • الذكاء الاصطناعي يقترح ولا يوثّق: AI_SUGGESTED لا يصير VERIFIED تلقائياً.
#   • إعلان المستخدم ليس تحقّقاً: USER_DECLARED يحتاج عملية تحقّق صريحة.
#   • لا اسم مجموعة إشغال يُخترع: يجب أن يكون موجوداً في حزمة تصنيف محمّلة.
#   • تصنيف تحت إصدار لا يخدم قاعدة من إصدار آخر (لا غسيل عبر الإصدارات).
#   • تعارض بين تصنيفين متحقَّقين ⇒ CONFLICT ⇒ القاعدة NOT_EVALUATED، بلا ترجيح صامت.
#   • لا محرّك حريق ولا حِمل إشغال ولا رشّاشات: الحقائق فقط كما هي ممثَّلة.
# =============================================================================
import json
import os

import acs_ingest as ING

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_occupancy.json"), "r", encoding="utf-8") as _f:
    REG = json.load(_f)

SCHEMA = REG["schema"]
LAYER_VERSION = REG["layer_version"]
STATES = tuple(REG["classification_states"])
TRANSITIONS = {k: tuple(v) for k, v in REG["classification_transitions"].items()}
SOURCES = tuple(REG["provenance_sources"])
NEVER_AUTO_VERIFIED = tuple(REG["never_auto_verified"])
SUBJECT_TYPES = tuple(REG["subject_types"])
PACK_STATES = tuple(REG["pack_states"])
PACK_TRANSITIONS = {k: tuple(v) for k, v in REG["pack_transitions"].items()}
VERIFICATION_METHODS = tuple(REG["verification_methods"])
FACTS = tuple(REG["classification_facts"])
PACK_ACTIVE_STATES = ("VERIFIED_PARTIAL", "VERIFIED_FOR_DECLARED_SCOPE")


# ---------------------------------------------------------------- المخزن --
def empty_store():
    return {"classifications": [], "packs": []}


def fixture_store():
    """حزم التصنيف الاصطناعية المشحونة (لا مجموعة إشغال حقيقية إطلاقاً)."""
    return {"classifications": [], "packs": json.loads(json.dumps(REG["packs"]))}


def packs(store):
    return store.get("packs") or []


def pack(store, pack_id, version=None):
    for p in packs(store):
        if p.get("pack_id") == pack_id and (version is None or p.get("version") == version):
            return p
    return None


def classification(store, cid):
    for c in store.get("classifications") or []:
        if c.get("id") == cid:
            return c
    return None


def classifications_for(store, subject_id):
    return [c for c in (store.get("classifications") or []) if c.get("subject_id") == subject_id]


def real_classification_count(store):
    """تصنيفات نظامية حقيقية متحقَّق منها — يجب أن تكون صفراً في هذه المرحلة."""
    return sum(1 for c in (store.get("classifications") or [])
               if c.get("status") == "VERIFIED" and c.get("regulatory") is True)


# ------------------------------------------------------- حزمة التصنيفات --
def validate_pack(p):
    issues = []
    if not isinstance(p, dict):
        return ["classification pack is not an object"]
    if ING._has_executable(p):
        issues.append("classification pack contains executable/script-like content")
    for k in ("pack_id", "version", "classification_system", "standard", "edition"):
        if not p.get(k):
            issues.append("classification pack missing field: %s" % k)
    st = (p.get("verification") or {}).get("status")
    if st not in PACK_STATES:
        issues.append("unknown classification pack status: %s" % st)
    if p.get("completeness") not in ("partial", "complete_for_declared_scope", "unknown"):
        issues.append("unknown completeness: %s" % p.get("completeness"))
    scope = p.get("coverage_scope")
    if not isinstance(scope, list) or not scope:
        issues.append("classification pack must declare a coverage_scope list")
    seen = set()
    cl = p.get("classifications")
    if not isinstance(cl, list) or not cl:
        issues.append("classification pack declares no classifications")
    else:
        for c in cl:
            cid = c.get("id")
            if not cid:
                issues.append("classification without an id")
            if cid in seen:
                issues.append("duplicate classification id: %s" % cid)
            seen.add(cid)
            if not c.get("group"):
                issues.append("classification %s has no group" % cid)
            for ex in (c.get("exceptions") or []):
                if ex.get("resolution") not in ("open", "resolved", "declared_unsupported"):
                    issues.append("classification %s has an exception with an unknown resolution" % cid)
    for did in (p.get("source_documents") or []):
        if not isinstance(did, str) or not did:
            issues.append("invalid source document reference in classification pack")
    if p.get("regulatory") is True and not (p.get("source_documents") or []):
        issues.append("a regulatory classification pack must cite source documents")
    if st in PACK_ACTIVE_STATES and not (p.get("verification") or {}).get("method"):
        issues.append("verified classification pack requires a verification method")
    return issues


def can_transition_pack(frm, to):
    return to in PACK_TRANSITIONS.get(frm, ())


def verify_pack(p, to="VERIFIED_PARTIAL", verifier=None, at=None,
                method="explicit_manual_approval", notes=None):
    if to not in PACK_STATES:
        return False, "UNKNOWN_TARGET_STATE"
    v = p.setdefault("verification", {"status": "DRAFT"})
    frm = v.get("status")
    if not can_transition_pack(frm, to):
        return False, "INVALID_TRANSITION: %s -> %s" % (frm, to)
    if method == "ai_suggestion":
        return False, "AI_MAY_NOT_VERIFY"
    if method not in VERIFICATION_METHODS:
        return False, "UNKNOWN_VERIFICATION_METHOD"
    issues = validate_pack(p)
    if issues:
        return False, "PACK_INVALID: %s" % issues[0]
    if to == "VERIFIED_FOR_DECLARED_SCOPE" and p.get("completeness") != "complete_for_declared_scope":
        return False, "SCOPE_COMPLETENESS_NOT_DECLARED"
    v.update(status=to, method=method, verified_at=at, verified_by=verifier, notes=notes)
    p.setdefault("history", []).append({"from": frm, "to": to, "method": method, "at": at})
    return True, None


def pack_classification(p, group, subgroup=None):
    for c in (p.get("classifications") or []):
        if c.get("group") == group and (subgroup is None or c.get("subgroup") == subgroup):
            return c
    return None


def active_packs(project, store):
    """لا تفعيل ضمني: حزمة التصنيف تعمل فقط إن ثبّتها سياق كود المشروع صراحةً."""
    out = {"packs": [], "rejected": []}
    ctx = ((project or {}).get("code_context") or {})
    for ref in (ctx.get("classification_packs") or []):
        if ref.get("enabled") is not True:
            out["rejected"].append({"pack_id": ref.get("pack_id"), "version": ref.get("version"),
                                    "reason": "NOT_ENABLED"})
            continue
        p = pack(store, ref.get("pack_id"), ref.get("version"))
        if p is None:
            out["rejected"].append({"pack_id": ref.get("pack_id"), "version": ref.get("version"),
                                    "reason": "CLASSIFICATION_PACK_NOT_FOUND"})
            continue
        st = (p.get("verification") or {}).get("status")
        if st not in PACK_ACTIVE_STATES:
            out["rejected"].append({"pack_id": p.get("pack_id"), "version": p.get("version"),
                                    "reason": "CLASSIFICATION_PACK_NOT_VERIFIED (%s)" % st})
            continue
        issues = validate_pack(p)
        if issues:
            out["rejected"].append({"pack_id": p.get("pack_id"), "version": p.get("version"),
                                    "reason": "CLASSIFICATION_PACK_INVALID", "detail": issues[0]})
            continue
        out["packs"].append(p)
    return out


# --------------------------------------------------------- سياق الكود --
def new_code_context():
    """سياق كود فارغ تماماً — لا اختصاص ولا معيار ولا حزم، ولا إشغال."""
    return {"jurisdiction": {"country": None, "region": None, "authority": None},
            "code_context": {"standard": None, "edition": None,
                             "rulepacks": [], "classification_packs": []},
            "occupancy": {"status": "UNCLASSIFIED", "classifications": []}}


def validate_code_context(ctx):
    issues = []
    if not isinstance(ctx, dict):
        return ["code context is not an object"]
    if ING._has_executable(ctx):
        issues.append("code context contains executable/script-like content")
    j = ctx.get("jurisdiction")
    if not isinstance(j, dict):
        issues.append("code context needs a jurisdiction object (may be all null)")
    cc = ctx.get("code_context")
    if not isinstance(cc, dict):
        issues.append("code context needs a code_context object")
    else:
        for key in ("rulepacks", "classification_packs"):
            if not isinstance(cc.get(key), list):
                issues.append("code_context.%s must be a list" % key)
        for ref in (cc.get("classification_packs") or []):
            if not ref.get("pack_id") or not ref.get("version"):
                issues.append("classification pack reference needs pack_id and version")
            if ref.get("enabled") not in (True, False):
                issues.append("classification pack reference must state enabled explicitly")
    return issues


# ------------------------------------------------------- التصنيف نفسه --
def new_classification(subject_id, subject_type, group=None, subgroup=None,
                       source="AI_SUGGESTED", pack_id=None, pack_version=None,
                       standard=None, edition=None, classification_system=None,
                       jurisdiction=None, evidence=None, regulatory=False, synthetic=True,
                       cid=None):
    return {
        "id": cid or ("occ_%s_%s" % (subject_id, group or "none")),
        "subject_id": subject_id, "subject_type": subject_type,
        "classification_system": classification_system, "standard": standard, "edition": edition,
        "jurisdiction": jurisdiction or {"country": None, "region": None, "authority": None},
        "group": group, "subgroup": subgroup,
        "pack_id": pack_id, "pack_version": pack_version,
        "source": source, "status": "UNCLASSIFIED",
        "evidence": list(evidence or []),
        "declared_value": None, "declared_by": None, "declaration_time": None,
        "verification": None, "regulatory": bool(regulatory), "synthetic": bool(synthetic),
        "history": []}


def validate_classification(c, store):
    issues = []
    if not isinstance(c, dict):
        return ["classification is not an object"]
    if ING._has_executable(c):
        issues.append("classification contains executable/script-like content")
    for k in ("id", "subject_id", "subject_type", "source"):
        if not c.get(k):
            issues.append("classification missing field: %s" % k)
    if c.get("subject_type") not in SUBJECT_TYPES:
        issues.append("unknown classification subject_type: %s" % c.get("subject_type"))
    if c.get("source") not in SOURCES:
        issues.append("unknown classification source: %s" % c.get("source"))
    if c.get("status") not in STATES:
        issues.append("unknown classification status: %s" % c.get("status"))
    p = pack(store, c.get("pack_id"), c.get("pack_version")) if c.get("pack_id") else None
    if c.get("group"):
        if p is None:
            issues.append("classification cites no loaded classification pack for group %s" % c.get("group"))
        elif pack_classification(p, c.get("group"), c.get("subgroup")) is None:
            # اسم مجموعة غير موجود في النظام المحمَّل = اختراع تصنيف
            issues.append("group %s/%s does not exist in classification pack %s"
                          % (c.get("group"), c.get("subgroup"), c.get("pack_id")))
    if p is not None:
        for field in ("standard", "edition", "classification_system"):
            if c.get(field) and p.get(field) and c[field] != p[field]:
                issues.append("classification %s does not match its pack (%s vs %s)"
                              % (field, c.get(field), p.get(field)))
    if c.get("status") == "VERIFIED":
        v = c.get("verification") or {}
        if not v:
            issues.append("VERIFIED classification without a verification record")
        elif not c.get("evidence"):
            issues.append("VERIFIED classification without recorded evidence")
        if c.get("source") == "AI_SUGGESTED":
            issues.append("an AI_SUGGESTED classification may never carry VERIFIED status")
    if c.get("source") == "USER_DECLARED" and c.get("declared_value") is None:
        issues.append("USER_DECLARED classification must record declared_value")
    return issues


def can_transition(frm, to):
    return to in TRANSITIONS.get(frm, ())


def _move(c, to, note=None):
    frm = c.get("status")
    if not can_transition(frm, to):
        return False, "INVALID_TRANSITION: %s -> %s" % (frm, to)
    c["status"] = to
    c.setdefault("history", []).append({"from": frm, "to": to, "note": note})
    return True, None


def add_classification(store, c):
    if classification(store, c.get("id")) is not None:
        return False, "DUPLICATE_CLASSIFICATION_ID"
    store.setdefault("classifications", []).append(c)
    return True, None


# ---------------------------------------------------- اقتراح من البرنامج --
def suggest_from_program(subject_id, subject_type, program, store, project, at=None):
    """برنامج المبنى يقترح ولا يُثبت. أقصى حالة ممكنة: CANDIDATE.
    المرشّحون يأتون من حزمة تصنيف مفعَّلة، لا من جدول ثابت غير موثَّق."""
    out = []
    act = active_packs(project, store)
    for p in act["packs"]:
        for hint in (p.get("program_hints") or []):
            if hint.get("program") != program:
                continue
            for gid in (hint.get("candidates") or []):
                cd = pack_classification(p, gid)
                if cd is None:
                    continue
                c = new_classification(
                    subject_id, subject_type, group=cd.get("group"), subgroup=cd.get("subgroup"),
                    source="AI_SUGGESTED", pack_id=p.get("pack_id"), pack_version=p.get("version"),
                    standard=p.get("standard"), edition=p.get("edition"),
                    classification_system=p.get("classification_system"),
                    jurisdiction=p.get("jurisdiction"),
                    regulatory=p.get("regulatory") is True, synthetic=p.get("synthetic") is True,
                    cid="occ_%s_%s_%s" % (subject_id, p.get("pack_id"), cd.get("group")),
                    evidence=[{"type": "program_hint", "ref": program,
                               "detail": hint.get("note") or "program suggestion only"},
                              {"type": "classification_pack", "ref": p.get("pack_id"),
                               "detail": "group defined in the loaded classification system"}])
                _move(c, "CANDIDATE", note="suggested from building program at %s" % at)
                out.append(c)
    return out


def declare(subject_id, subject_type, group, store, project, subgroup=None,
            declared_by=None, at=None, note=None):
    """إعلان صريح من مستخدم/مهندس. لا يُعتبر تحقّقاً بذاته."""
    act = active_packs(project, store)
    for p in act["packs"]:
        cd = pack_classification(p, group, subgroup)
        if cd is None:
            continue
        c = new_classification(
            subject_id, subject_type, group=cd.get("group"), subgroup=cd.get("subgroup"),
            source="USER_DECLARED", pack_id=p.get("pack_id"), pack_version=p.get("version"),
            standard=p.get("standard"), edition=p.get("edition"),
            classification_system=p.get("classification_system"), jurisdiction=p.get("jurisdiction"),
            regulatory=p.get("regulatory") is True, synthetic=p.get("synthetic") is True,
            cid="occ_%s_%s_%s_declared" % (subject_id, p.get("pack_id"), cd.get("group")),
            evidence=[{"type": "user_declaration", "ref": declared_by,
                       "detail": note or "declared by the project team"}])
        c["declared_value"] = group
        c["declared_by"] = declared_by
        c["declaration_time"] = at
        _move(c, "CANDIDATE", note="user declaration recorded at %s" % at)
        return c, None
    return None, "GROUP_NOT_IN_ANY_ACTIVE_CLASSIFICATION_PACK"


def verify_classification(c, store, project, verifier=None, at=None,
                          method="explicit_manual_approval", evidence=None, notes=None):
    """البوّابة الصريحة الوحيدة إلى VERIFIED. الذكاء الاصطناعي لا يجتازها."""
    if method == "ai_suggestion":
        return False, "AI_MAY_NOT_VERIFY", None
    if method not in VERIFICATION_METHODS:
        return False, "UNKNOWN_VERIFICATION_METHOD", None
    if not evidence:
        return False, "VERIFICATION_EVIDENCE_REQUIRED", None
    p = pack(store, c.get("pack_id"), c.get("pack_version"))
    if p is None:
        return False, "CLASSIFICATION_PACK_NOT_FOUND", None
    if (p.get("verification") or {}).get("status") not in PACK_ACTIVE_STATES:
        return False, "CLASSIFICATION_PACK_NOT_VERIFIED", None
    if pack(  # الحزمة يجب أن تكون مفعَّلة في سياق كود المشروع أيضاً
            {"packs": active_packs(project, store)["packs"]},
            c.get("pack_id"), c.get("pack_version")) is None:
        return False, "CLASSIFICATION_PACK_NOT_ACTIVATED", None
    if pack_classification(p, c.get("group"), c.get("subgroup")) is None:
        return False, "GROUP_NOT_IN_CLASSIFICATION_PACK", None
    issues = [i for i in validate_classification(c, store) if "VERIFIED" not in i]
    if issues:
        return False, "CLASSIFICATION_INVALID: %s" % issues[0], None
    if c.get("status") != "READY_FOR_VERIFICATION":
        ok, why = _move(c, "READY_FOR_VERIFICATION", note="advanced for explicit verification")
        if not ok:
            return False, why, None
    # مسؤولية بشرية صريحة: المصدر يتحوّل ويُحفظ الأصل
    source_before = c.get("source")
    rec = {"verifier": verifier, "method": method, "verified_at": at,
           "pack_id": p.get("pack_id"), "pack_version": p.get("version"),
           "standard": p.get("standard"), "edition": p.get("edition"),
           "source_before": source_before, "notes": notes}
    ok, why = _move(c, "VERIFIED", note="explicitly verified at %s" % at)
    if not ok:
        return False, why, None
    c["source"] = "MANUAL_VERIFIED"
    c["verification"] = rec
    c["evidence"] = list(c.get("evidence") or []) + list(evidence)
    return True, None, rec


# ------------------------------------------------------------ الحلّ --
def resolve_occupancy(subject_id, store):
    """يجمع تصنيفات موضوع واحد إلى حالة واحدة قابلة للاستعمال في القواعد.
    تعارض بين متحقَّقَين ⇒ CONFLICT، ولا تُختار إحداهما."""
    recs = classifications_for(store, subject_id)
    out = {"subject_id": subject_id, "status": "UNCLASSIFIED", "group": None, "subgroup": None,
           "standard": None, "edition": None, "classification_system": None,
           "jurisdiction_country": None, "source": None, "records": len(recs),
           "candidates": [], "reason": None}
    if not recs:
        return out
    verified = [c for c in recs if c.get("status") == "VERIFIED"]
    out["candidates"] = [{"id": c.get("id"), "group": c.get("group"), "status": c.get("status"),
                          "source": c.get("source")} for c in recs]
    if verified:
        keys = {(c.get("standard"), c.get("edition"), c.get("group"), c.get("subgroup"))
                for c in verified}
        if len(keys) > 1:
            out.update(status="CONFLICT", reason="OCCUPANCY_CLASSIFICATION_CONFLICT")
            return out
        v = verified[0]
        out.update(status="VERIFIED", group=v.get("group"), subgroup=v.get("subgroup"),
                   standard=v.get("standard"), edition=v.get("edition"),
                   classification_system=v.get("classification_system"),
                   jurisdiction_country=(v.get("jurisdiction") or {}).get("country"),
                   source=v.get("source"))
        return out
    order = ("READY_FOR_VERIFICATION", "CANDIDATE", "NEEDS_INFORMATION", "NOT_APPLICABLE",
             "CONFLICT", "UNCLASSIFIED")
    present = [s for s in order if any(c.get("status") == s for c in recs)]
    st = present[0] if present else "UNCLASSIFIED"
    out["status"] = "CANDIDATE" if st == "READY_FOR_VERIFICATION" else st
    out["reason"] = "OCCUPANCY_NOT_VERIFIED"
    return out


def occupancy_index(store, subject_ids):
    return {sid: resolve_occupancy(sid, store) for sid in subject_ids}


def audit(store, subject_ids=None):
    """جرد تصنيفي — معلومات فقط، ولا عبارة مطابقة."""
    ids = list(subject_ids) if subject_ids is not None else sorted(
        {c.get("subject_id") for c in (store.get("classifications") or [])})
    counts = {k: 0 for k in ("UNCLASSIFIED", "CANDIDATE", "NEEDS_INFORMATION",
                             "READY_FOR_VERIFICATION", "VERIFIED", "CONFLICT", "NOT_APPLICABLE")}
    for sid in ids:
        counts[resolve_occupancy(sid, store)["status"]] += 1
    return {"subjects_total": len(ids), "unclassified": counts["UNCLASSIFIED"],
            "candidate": counts["CANDIDATE"], "needs_information": counts["NEEDS_INFORMATION"],
            "ready_for_verification": counts["READY_FOR_VERIFICATION"],
            "verified": counts["VERIFIED"], "conflict": counts["CONFLICT"],
            "not_applicable": counts["NOT_APPLICABLE"],
            "real_regulatory_verified": real_classification_count(store),
            "layer_version": LAYER_VERSION,
            "note": "classification inventory only — this is not a compliance statement"}


def issues(store, project=None):
    out = []
    for p in packs(store):
        for i in validate_pack(p):
            out.append("[%s@%s] %s" % (p.get("pack_id"), p.get("version"), i))
    seen = set()
    for c in (store.get("classifications") or []):
        if c.get("id") in seen:
            out.append("[%s] duplicate classification id" % c.get("id"))
        seen.add(c.get("id"))
        for i in validate_classification(c, store):
            out.append("[%s] %s" % (c.get("id"), i))
    if project is not None:
        for i in validate_code_context(project):
            out.append("[code_context] %s" % i)
    return out


def export(store, project=None):
    """تصدير إضافي: الحالة والمصدر والدليل — والاقتراحات لا تُصدَّر كحقائق."""
    rows = []
    for c in (store.get("classifications") or []):
        rows.append({"id": c.get("id"), "subject_id": c.get("subject_id"),
                     "subject_type": c.get("subject_type"), "status": c.get("status"),
                     "source": c.get("source"), "group": c.get("group"),
                     "subgroup": c.get("subgroup"), "standard": c.get("standard"),
                     "edition": c.get("edition"),
                     "classification_system": c.get("classification_system"),
                     "regulatory": c.get("regulatory") is True,
                     "synthetic": c.get("synthetic") is True,
                     "authoritative": c.get("status") == "VERIFIED",
                     "evidence": list(c.get("evidence") or []),
                     "verification": c.get("verification"),
                     "declared_value": c.get("declared_value"),
                     "declared_by": c.get("declared_by"),
                     "declaration_time": c.get("declaration_time")})
    out = {"layer_version": LAYER_VERSION, "classifications": rows,
           "packs": [{"pack_id": p.get("pack_id"), "version": p.get("version"),
                      "classification_system": p.get("classification_system"),
                      "standard": p.get("standard"), "edition": p.get("edition"),
                      "status": (p.get("verification") or {}).get("status"),
                      "regulatory": p.get("regulatory") is True,
                      "synthetic": p.get("synthetic") is True}
                     for p in packs(store)],
           "real_regulatory_verified": real_classification_count(store),
           "note": "AI suggestions are exported with their status and are never authoritative"}
    if project is not None:
        out["activated_classification_packs"] = [
            {"pack_id": p.get("pack_id"), "version": p.get("version")}
            for p in active_packs(project, store)["packs"]]
    return out
