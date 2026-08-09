# -*- coding: utf-8 -*-
# =============================================================================
# acs_ingest.py — أساس استيراد المصادر الرسمية والتحقّق من حِزَم القواعد.
#
# يبني الأنبوب المتحكَّم به:
#   OFFICIAL SOURCE → SOURCE DOCUMENT → METADATA → CLAUSE/FRAGMENT →
#   CANDIDATE RULE → EXPLICIT VERIFICATION → VERIFIED RULE → RULE PACK →
#   PROJECT ACTIVATION → RULE ENGINE
#
# مبادئ صارمة:
#   • الاستخراج ليس تحقّقاً: لا مرشّح يصبح قابلاً للتنفيذ لمجرّد استخراجه.
#   • لا تفعيل تلقائي: الحزمة المتحقَّق منها لا تعمل حتى يربطها المشروع صراحةً.
#   • الذكاء الاصطناعي يساعد ولا يوثّق: ai_assisted لا يخفّف أي شرط دليل.
#   • كل وثيقة تُثبَّت ببصمة SHA-256؛ تغيّر البايتات يُبطل التحقّق.
#   • لا نسخ معايير محميّة: مقتطفات قصيرة + مؤشّرات موضع + بصمات فقط.
#   • المستندات بيانات لا شيفرة: لا eval ولا exec ولا استدعاء نظام.
#   • عند تعارض غير محسوم: RULE_CONFLICT ⇒ NOT_EVALUATED، لا اختيار عشوائي.
# =============================================================================
import json
import os
import hashlib

import acs_rules as RULES

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_ingest.json"), "r", encoding="utf-8") as _f:
    FIXTURES = json.load(_f)

SCHEMA = FIXTURES["schema"]
PIPELINE_VERSION = FIXTURES["pipeline_version"]

DOC_STATES = tuple(FIXTURES["document_states"])
DOC_TRANSITIONS = {k: tuple(v) for k, v in FIXTURES["document_transitions"].items()}
FRAGMENT_STATES = tuple(FIXTURES["fragment_states"])
FRAGMENT_KINDS = tuple(FIXTURES["fragment_kinds"])
CANDIDATE_STATES = tuple(FIXTURES["candidate_states"])
CANDIDATE_TRANSITIONS = {k: tuple(v) for k, v in FIXTURES["candidate_transitions"].items()}
PACK_STATES = tuple(FIXTURES["pack_states"])
PACK_TRANSITIONS = {k: tuple(v) for k, v in FIXTURES["pack_transitions"].items()}
PIPELINE_STAGES = tuple(FIXTURES["pipeline_stages"])
ORIGIN_TYPES = tuple(FIXTURES["origin_types"])
EXTRACTION_METHODS = tuple(FIXTURES["extraction_methods"])
VERIFICATION_METHODS = tuple(FIXTURES["verification_methods"])
RELATION_TYPES = tuple(FIXTURES["relation_types"])
EXCEPTION_RESOLUTIONS = tuple(FIXTURES["exception_resolutions"])
ORIGIN_AUTHORITIES = tuple(FIXTURES["origin_authorities"])
# سلسلة الحيازة المقبولة لوسم وثيقة بأنها رسمية
OFFICIAL_CHAIN = ("issuing_authority", "authorized_distributor")

# حدّ المقتطف: البنية تدعم التدقيق بلا استنساخ المعيار كاملاً
EXCERPT_MAX_CHARS = FIXTURES["excerpt_max_chars"]
# فحص القيم النصّية يستهدف أنماط تنفيذ فعلية فقط (أسماء المفاتيح تُفحص على حدة)،
# حتى لا يُرفض نصّ مشروع مثل "manual_transcription" لمجرّد احتوائه سلسلة حروف.
_FORBIDDEN = ("javascript:", "data:text/html", "<script", "eval(", "exec(",
              "new function(", "system(", "subprocess.", "os.popen")


# ------------------------------------------------------------ بصمات وتقنين --
def sha256_hex(text):
    """بصمة بايتات UTF-8 — تثبيت الوثيقة على بايتاتها لا على اسم ملفها."""
    if text is None:
        return None
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _sci(s):
    """يعيد صياغة أقصر تمثيل عشري إلى صورة علمية موحّدة.
    لغتا التنفيذ تنتجان الأرقام نفسها لكن بتنسيق مختلف (5e-07 مقابل 5e-7،
    و1e-05 مقابل 0.00001)، فنوحّد التنسيق بدل الاعتماد على تنسيق كل لغة."""
    s = s.strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    low = s.lower()
    if "e" in low:
        mant, _, exp = low.partition("e")
        exp = int(exp)
    else:
        mant, exp = low, 0
    ip, _, fp = mant.partition(".")
    alld = ip + fp
    digits = alld.lstrip("0")
    if digits == "":
        return "0"
    lead_zeros = len(alld) - len(digits)
    e10 = exp + (len(ip) - 1) - lead_zeros
    digits = digits.rstrip("0") or "0"
    out = digits[0] + ("." + digits[1:] if len(digits) > 1 else "") + "e" + str(e10)
    return ("-" if neg else "") + out


def _num_token(v):
    """رمز رقمي موحّد عبر اللغتين. البادئة تمنع تصادم رقم مع نصّ يشبهه."""
    if isinstance(v, int):
        return "#n:%d" % v
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):
        raise ValueError("non-finite number cannot be canonicalised")
    if f == int(f) and abs(f) < 1e16:
        return "#n:%d" % int(f)
    return "#n:" + _sci(repr(f))


def _canon(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return _num_token(v)
    if isinstance(v, dict):
        return {k: _canon(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_canon(x) for x in v]
    return v


def canonical_json(o):
    return json.dumps(_canon(o), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


MEANING_FIELDS = ("rule_id", "standard", "edition", "section", "applies_to", "inputs",
                  "operator", "expected", "exceptions", "revision", "subject_type",
                  "jurisdiction", "jurisdiction_required")


def rule_definition_hash(rule):
    """بصمة المعنى التنظيمي — أي تغيير في المعنى يوجب مراجعة جديدة لا تعديلاً صامتاً."""
    if not isinstance(rule, dict):
        return None
    return sha256_hex(canonical_json({k: rule.get(k) for k in MEANING_FIELDS}))


def _is_hex64(h):
    if not isinstance(h, str) or len(h) != 64:
        return False
    return all(c in "0123456789abcdef" for c in h.lower())


def _has_executable(obj, depth=0):
    if depth > 12:
        return True
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in ("script", "code", "eval", "exec", "function", "__proto__"):
                return True
            if _has_executable(v, depth + 1):
                return True
    elif isinstance(obj, list):
        for v in obj:
            if _has_executable(v, depth + 1):
                return True
    elif isinstance(obj, str):
        low = obj.lower()
        for bad in _FORBIDDEN:
            if bad in low:
                return True
    return False


# ------------------------------------------------------------- المخزن --
def empty_store():
    return {"documents": [], "fragments": [], "candidates": [], "rulepacks": []}


def fixture_store():
    """نسخة من التجهيزات الاصطناعية المشحونة (لا محتوى تنظيمي إطلاقاً)."""
    return json.loads(json.dumps(FIXTURES["store"]))


_SOURCES_PATH = os.path.join(_HERE, "acs_sources.json")
with open(_SOURCES_PATH, "r", encoding="utf-8") as _sf:
    SOURCES = json.load(_sf)


def real_store():
    """سجلّ الوثائق الحقيقية: بيانات وصفية وبصمات ومواضع فهرس فقط.
    لا نصّ بنود ولا جداول ولا استثناءات — والمرشّحون والحِزَم فارغة حتى تُسلَّم
    صفحات البنود ويُتحقَّق منها صراحةً."""
    return {"documents": json.loads(json.dumps(SOURCES.get("documents") or [])),
            "fragments": json.loads(json.dumps(SOURCES.get("fragments") or [])),
            "candidates": json.loads(json.dumps(SOURCES.get("candidates") or [])),
            "rulepacks": json.loads(json.dumps(SOURCES.get("rulepacks") or []))}


def _by_id(items, key, val):
    for it in items or []:
        if it.get(key) == val:
            return it
    return None


def document(store, document_id):
    return _by_id(store.get("documents"), "document_id", document_id)


def fragment(store, fragment_id):
    return _by_id(store.get("fragments"), "fragment_id", fragment_id)


def candidate(store, candidate_id):
    return _by_id(store.get("candidates"), "candidate_id", candidate_id)


def rulepack(store, rulepack_id, version=None):
    for p in store.get("rulepacks") or []:
        if p.get("rulepack_id") == rulepack_id and (version is None or p.get("version") == version):
            return p
    return None


# --------------------------------------------------------- وثيقة المصدر --
def validate_document(doc):
    issues = []
    if not isinstance(doc, dict):
        return ["document is not an object"]
    if _has_executable(doc):
        issues.append("document metadata contains executable/script-like content")
    for k in ("document_id", "source_id", "title", "standard", "document_type"):
        if not doc.get(k):
            issues.append("document missing field: %s" % k)
    st = (doc.get("verification") or {}).get("status")
    if st not in DOC_STATES:
        issues.append("unknown document verification status: %s" % st)
    origin = doc.get("origin") or {}
    if origin.get("type") not in ORIGIN_TYPES:
        issues.append("unknown origin type: %s" % origin.get("type"))
    url = origin.get("url")
    if url and not str(url).startswith("https://"):
        issues.append("official source url must be https")
    if origin.get("type") == "official_url" and not url:
        issues.append("origin official_url requires a url")
    if origin.get("type") == "uploaded_file" and not origin.get("filename"):
        issues.append("origin uploaded_file requires a filename")
    integ = doc.get("integrity") or {}
    if not _is_hex64(integ.get("sha256")):
        issues.append("document integrity.sha256 must be a 64-hex digest")
    if integ.get("size_bytes") is not None and not isinstance(integ["size_bytes"], int):
        issues.append("integrity.size_bytes must be an integer or null")
    if doc.get("official") is True and doc.get("synthetic") is True:
        issues.append("a document cannot be both official and synthetic")
    oa = origin.get("origin_authority")
    if oa is not None and oa not in ORIGIN_AUTHORITIES:
        issues.append("unknown origin_authority: %s" % oa)
    # نسخة معاد نشرها من طرف ثالث ليست مصدراً رسمياً مهما بدا محتواها صحيحاً
    if doc.get("official") is True and oa not in OFFICIAL_CHAIN:
        issues.append("a document may not be marked official unless its origin_authority is "
                      "issuing_authority or authorized_distributor (got: %s)" % oa)
    if st in ("OFFICIAL_SOURCE_VERIFIED", "CONTENT_VERIFIED"):
        v = doc.get("verification") or {}
        if v.get("method") not in VERIFICATION_METHODS:
            issues.append("verified document requires a known verification method")
        if not v.get("evidence"):
            issues.append("verified document requires recorded verification evidence")
    for rel in (doc.get("relations") or []):
        if rel.get("type") not in RELATION_TYPES:
            issues.append("unknown document relation: %s" % rel.get("type"))
        if not rel.get("document_id"):
            issues.append("document relation without a target document_id")
    return issues


def can_transition_document(frm, to):
    return to in DOC_TRANSITIONS.get(frm, ())


def transition_document(doc, to, method=None, evidence=None, at=None, by=None):
    """انتقال حالة صريح فقط. الانتقال غير المسموح يُرفض ولا يُنفَّذ."""
    v = doc.setdefault("verification", {"status": "UNVERIFIED"})
    frm = v.get("status")
    if to not in DOC_STATES:
        return False, "UNKNOWN_TARGET_STATE"
    if not can_transition_document(frm, to):
        return False, "INVALID_TRANSITION: %s -> %s" % (frm, to)
    if to in ("SOURCE_IDENTIFIED", "OFFICIAL_SOURCE_VERIFIED", "CONTENT_VERIFIED"):
        if method not in VERIFICATION_METHODS:
            return False, "VERIFICATION_METHOD_REQUIRED"
        if not evidence:
            return False, "VERIFICATION_EVIDENCE_REQUIRED"
        # الرسمية لا تُستنتج من عنوان يبدو رسمياً
        if to == "OFFICIAL_SOURCE_VERIFIED":
            if doc.get("official") is not True:
                return False, "DOCUMENT_NOT_MARKED_OFFICIAL_BY_EVIDENCE"
            if ((doc.get("origin") or {}).get("origin_authority")) not in OFFICIAL_CHAIN:
                return False, "ORIGIN_NOT_IN_OFFICIAL_CHAIN"
    v.update(status=to, method=method, evidence=evidence, verified_at=at, verified_by=by)
    # الدليل يُحفظ مع كل انتقال أيضاً، فلا يضيع دليل خطوة سابقة عند تحديث الحالة
    doc.setdefault("history", []).append({"from": frm, "to": to, "method": method,
                                          "at": at, "evidence": evidence})
    return True, None


def verify_document_bytes(doc, content):
    """يقارن بصمة البايتات المعطاة ببصمة الوثيقة المسجّلة."""
    h = sha256_hex(content)
    rec = ((doc.get("integrity") or {}).get("sha256"))
    return (h == rec), h


def document_usable(doc):
    """قابلة للاستناد إليها في تحقّق قاعدة: محتواها متحقَّق ولم تُنسخ ولم تُلغَ."""
    st = (doc.get("verification") or {}).get("status")
    return st == "CONTENT_VERIFIED"


# --------------------------------------------------------------- الشذرات --
def validate_fragment(frag, store):
    issues = []
    if not isinstance(frag, dict):
        return ["fragment is not an object"]
    if _has_executable(frag):
        issues.append("fragment contains executable/script-like content")
    for k in ("fragment_id", "document_id", "extraction_method"):
        if not frag.get(k):
            issues.append("fragment missing field: %s" % k)
    if frag.get("status") not in FRAGMENT_STATES:
        issues.append("unknown fragment status: %s" % frag.get("status"))
    if frag.get("kind") not in FRAGMENT_KINDS:
        issues.append("unknown fragment kind: %s" % frag.get("kind"))
    if frag.get("extraction_method") not in EXTRACTION_METHODS:
        issues.append("unknown extraction method: %s" % frag.get("extraction_method"))
    doc = document(store, frag.get("document_id"))
    if doc is None:
        issues.append("fragment references a missing document: %s" % frag.get("document_id"))
    elif frag.get("document_hash") and frag["document_hash"] != (doc.get("integrity") or {}).get("sha256"):
        issues.append("fragment document_hash does not match the stored document")
    ex = frag.get("excerpt")
    if ex is not None:
        if not isinstance(ex, str):
            issues.append("excerpt must be text")
        elif len(ex) > EXCERPT_MAX_CHARS:
            issues.append("excerpt exceeds the permitted %d-character limit (copyright-safe storage)"
                          % EXCERPT_MAX_CHARS)
    if not frag.get("text_reference") and ex is None:
        issues.append("fragment needs at least a text_reference pointer")
    loc = frag.get("location") or {}
    if loc.get("start") is not None and loc.get("end") is not None:
        if not isinstance(loc["start"], int) or not isinstance(loc["end"], int) \
                or loc["end"] < loc["start"]:
            issues.append("invalid fragment location range")
    return issues


def fragments_of(store, document_id):
    return [f for f in (store.get("fragments") or []) if f.get("document_id") == document_id]


# ------------------------------------------------------------- المرشّحون --
def _unresolved_refs(cand, store):
    out = []
    for ref in (cand.get("cross_references") or []):
        if ref.get("resolution") == "resolved" and ref.get("fragment_id"):
            if fragment(store, ref["fragment_id"]) is None:
                out.append({"ref": ref.get("label"), "reason": "BROKEN_SOURCE_REFERENCE"})
            continue
        out.append({"ref": ref.get("label"), "reason": "UNRESOLVED_CROSS_REFERENCE"})
    return out


def _open_exceptions(cand):
    out = []
    for ex in (cand.get("exceptions") or []):
        if ex.get("resolution") not in ("resolved", "declared_unsupported"):
            out.append({"condition": ex.get("condition"), "reason": "EXCEPTION_NOT_REVIEWED"})
    return out


def _missing_definitions(cand, store):
    out = []
    for d in (cand.get("definition_refs") or []):
        if not d.get("fragment_id") or fragment(store, d["fragment_id"]) is None:
            out.append({"term": d.get("term"), "reason": "DEFINITION_FRAGMENT_MISSING"})
    return out


def validate_candidate(cand, store):
    """فحص بنيوي/دليلي للمرشّح — لا يجعله متحقَّقاً بحال."""
    issues = []
    if not isinstance(cand, dict):
        return ["candidate is not an object"]
    if _has_executable(cand):
        issues.append("candidate contains executable/script-like content")
    for k in ("candidate_id", "document_id", "extraction_method", "proposed_rule"):
        if not cand.get(k):
            issues.append("candidate missing field: %s" % k)
    if cand.get("status") not in CANDIDATE_STATES:
        issues.append("unknown candidate status: %s" % cand.get("status"))
    if cand.get("extraction_method") not in EXTRACTION_METHODS:
        issues.append("unknown extraction method: %s" % cand.get("extraction_method"))
    if cand.get("ai_assisted") not in (True, False):
        issues.append("candidate must state ai_assisted explicitly")
    doc = document(store, cand.get("document_id"))
    if doc is None:
        issues.append("candidate references a missing document: %s" % cand.get("document_id"))
    else:
        rec = (doc.get("integrity") or {}).get("sha256")
        if cand.get("document_hash") != rec:
            issues.append("SOURCE_HASH_MISMATCH: candidate pinned %s, document is %s"
                          % (cand.get("document_hash"), rec))
    for fid in (cand.get("fragment_ids") or []):
        if fragment(store, fid) is None:
            issues.append("BROKEN_SOURCE_REFERENCE: %s" % fid)
    # لا يُستشهد بوثيقة معيار لتبرير قاعدة معيار آخر أو إصدار آخر
    pr0 = cand.get("proposed_rule") or {}
    if doc is not None:
        if pr0.get("standard") and doc.get("standard") and pr0["standard"] != doc["standard"]:
            issues.append("STANDARD_MISMATCH: rule cites %s but the source document is %s"
                          % (pr0["standard"], doc["standard"]))
        if pr0.get("edition") and doc.get("edition") and str(pr0["edition"]) != str(doc["edition"]):
            issues.append("EDITION_MISMATCH: rule cites edition %s but the source document is edition %s"
                          % (pr0["edition"], doc["edition"]))
    if not (cand.get("fragment_ids") or []):
        issues.append("candidate cites no source fragment")
    # مرشّح يدّعي أنه متحقَّق بلا سجلّ تحقّق = تزوير حالة
    if cand.get("status") == "VERIFIED" and not cand.get("verification"):
        issues.append("candidate claims VERIFIED without a verification record")
    pr = cand.get("proposed_rule") or {}
    for i in RULES.validate_rule(pr):
        issues.append("proposed_rule: %s" % i)
    if pr.get("regulatory") is True and (doc is None or not document_usable(doc)):
        issues.append("regulatory candidate references a document that is not CONTENT_VERIFIED")
    if pr.get("regulatory") is True and doc is not None and doc.get("official") is not True:
        issues.append("regulatory candidate requires an official source document")
    tbl = cand.get("table_context")
    if tbl is not None:
        if not isinstance(tbl, dict) or not tbl.get("table_id"):
            issues.append("table_context requires a table_id")
        elif tbl.get("row") is None and tbl.get("column") is None and not tbl.get("conditions"):
            issues.append("table-derived candidate must keep its row/column/condition context")
    return issues


def assess_candidate(cand, store):
    """يحسب الحالة المستحقّة من الأدلّة — لا يرفع الحالة إلى VERIFIED أبداً."""
    blocking = validate_candidate(cand, store)
    refs = _unresolved_refs(cand, store)
    exc = _open_exceptions(cand)
    defs = _missing_definitions(cand, store)
    if any("BROKEN_SOURCE_REFERENCE" in i or "SOURCE_HASH_MISMATCH" in i for i in blocking):
        return "REJECTED", blocking
    if blocking:
        return "NEEDS_INTERPRETATION", blocking
    if refs:
        return "NEEDS_CROSS_REFERENCE", refs
    if exc:
        return "NEEDS_EXCEPTION_REVIEW", exc
    if defs:
        return "NEEDS_INTERPRETATION", defs
    if not cand.get("interpretation_method"):
        return "NEEDS_INTERPRETATION", [{"reason": "INTERPRETATION_METHOD_MISSING"}]
    return "READY_FOR_VERIFICATION", []


def can_transition_candidate(frm, to):
    return to in CANDIDATE_TRANSITIONS.get(frm, ())


def advance_candidate(cand, store):
    """ينقل المرشّح إلى الحالة التي تستحقّها أدلّته، ضمن الانتقالات المسموحة."""
    state, detail = assess_candidate(cand, store)
    frm = cand.get("status")
    if state == frm:
        return frm, detail
    if not can_transition_candidate(frm, state):
        return frm, [{"reason": "INVALID_TRANSITION: %s -> %s" % (frm, state)}]
    cand["status"] = state
    cand["status_detail"] = detail
    cand.setdefault("history", []).append({"from": frm, "to": state})
    return state, detail


def verify_candidate(cand, store, verifier=None, at=None,
                     method="explicit_manual_approval", notes=None):
    """بوّابة التحقّق الصريحة الوحيدة. الذكاء الاصطناعي لا يستطيع استدعاءها نيابةً عن إنسان."""
    if method not in VERIFICATION_METHODS:
        return False, "UNKNOWN_VERIFICATION_METHOD", None
    if method == "ai_suggestion":
        return False, "AI_MAY_NOT_VERIFY", None
    state, detail = assess_candidate(cand, store)
    if state != "READY_FOR_VERIFICATION":
        return False, state, detail
    doc = document(store, cand.get("document_id"))
    if doc is None:
        return False, "REJECTED", [{"reason": "BROKEN_SOURCE_REFERENCE"}]
    if not document_usable(doc):
        return False, "SOURCE_NOT_VERIFIED", [
            {"reason": "DOCUMENT_STATUS_%s" % ((doc.get("verification") or {}).get("status"))}]
    if cand.get("document_hash") != (doc.get("integrity") or {}).get("sha256"):
        return False, "SOURCE_HASH_MISMATCH", None
    pr = cand.get("proposed_rule") or {}
    if pr.get("regulatory") is True and doc.get("official") is not True:
        return False, "SOURCE_NOT_OFFICIAL", None
    # الأنبوب لا يُختصر: يُنقل المرشّح أولاً إلى الحالة التي تستحقّها أدلّته
    # (EXTRACTED → READY_FOR_VERIFICATION) ثم يُوثَّق. القفز المباشر ممنوع.
    if cand.get("status") != "READY_FOR_VERIFICATION":
        moved, _ = advance_candidate(cand, store)
        if moved != "READY_FOR_VERIFICATION":
            return False, "INVALID_TRANSITION: %s -> READY_FOR_VERIFICATION" % cand.get("status"), None
    if not can_transition_candidate(cand.get("status"), "VERIFIED"):
        return False, "INVALID_TRANSITION: %s -> VERIFIED" % cand.get("status"), None
    rec = {"verifier": verifier, "method": method, "verified_at": at,
           "document_id": doc.get("document_id"),
           "document_hash": (doc.get("integrity") or {}).get("sha256"),
           "rule_definition_hash": rule_definition_hash(pr),
           "fragment_ids": list(cand.get("fragment_ids") or []),
           "ai_assisted": cand.get("ai_assisted") is True,
           "notes": notes}
    frm = cand.get("status")
    cand["status"] = "VERIFIED"
    cand["verification"] = rec
    cand.setdefault("history", []).append({"from": frm, "to": "VERIFIED", "method": method, "at": at})
    return True, None, rec


def verification_still_valid(cand, store):
    """التحقّق مثبَّت على بايتات الوثيقة: تغيّرها يُبطل التحقّق ولا يُحدَّث بصمت."""
    rec = cand.get("verification")
    if not rec:
        return False, "NOT_VERIFIED"
    doc = document(store, rec.get("document_id"))
    if doc is None:
        return False, "BROKEN_SOURCE_REFERENCE"
    if (doc.get("integrity") or {}).get("sha256") != rec.get("document_hash"):
        return False, "SOURCE_HASH_MISMATCH"
    if (doc.get("verification") or {}).get("status") in ("SUPERSEDED", "REVOKED", "INVALID"):
        return False, "SOURCE_%s" % (doc.get("verification") or {}).get("status")
    if rule_definition_hash(cand.get("proposed_rule")) != rec.get("rule_definition_hash"):
        return False, "RULE_DEFINITION_CHANGED"
    for fid in (rec.get("fragment_ids") or []):
        if fragment(store, fid) is None:
            return False, "BROKEN_SOURCE_REFERENCE"
    return True, None


# ------------------------------------------------------------ حِزَم القواعد --
def validate_pack(pack, store):
    issues = []
    if not isinstance(pack, dict):
        return ["rulepack is not an object"]
    if _has_executable(pack):
        issues.append("rulepack contains executable/script-like content")
    for k in ("rulepack_id", "version", "standard", "edition"):
        if not pack.get(k):
            issues.append("rulepack missing field: %s" % k)
    st = (pack.get("verification") or {}).get("status")
    if st not in PACK_STATES:
        issues.append("unknown rulepack status: %s" % st)
    if pack.get("completeness") not in RULES.COMPLETENESS:
        issues.append("unknown completeness: %s" % pack.get("completeness"))
    scope = pack.get("coverage_scope")
    if not isinstance(scope, list) or not scope:
        issues.append("rulepack must declare a coverage_scope list")
    if pack.get("completeness") == "complete_for_declared_scope" and not scope:
        issues.append("complete_for_declared_scope requires a declared coverage_scope")
    seen = set()
    for cid in (pack.get("candidate_ids") or []):
        c = candidate(store, cid)
        if c is None:
            issues.append("rulepack references a missing candidate: %s" % cid)
            continue
        if c.get("status") != "VERIFIED":
            issues.append("rulepack contains a candidate that is not VERIFIED: %s (%s)"
                          % (cid, c.get("status")))
            continue
        ok, why = verification_still_valid(c, store)
        if not ok:
            issues.append("rulepack candidate verification is no longer valid: %s (%s)" % (cid, why))
            continue
        uid = RULES.rule_uid(c.get("proposed_rule") or {})
        if uid in seen:
            issues.append("duplicate rule identity inside rulepack: %s" % uid)
        seen.add(uid)
    for did in (pack.get("source_documents") or []):
        if document(store, did) is None:
            issues.append("rulepack references a missing source document: %s" % did)
    if st in ("VERIFIED_PARTIAL", "VERIFIED_FOR_DECLARED_SCOPE"):
        if not (pack.get("verification") or {}).get("method"):
            issues.append("verified rulepack requires a verification method")
        if not (pack.get("candidate_ids") or []):
            issues.append("verified rulepack contains no verified rules")
    return issues


def can_transition_pack(frm, to):
    return to in PACK_TRANSITIONS.get(frm, ())


def verify_pack(pack, store, to="VERIFIED_PARTIAL", verifier=None, at=None,
                method="explicit_manual_approval", notes=None):
    if to not in PACK_STATES:
        return False, "UNKNOWN_TARGET_STATE"
    v = pack.setdefault("verification", {"status": "DRAFT"})
    frm = v.get("status")
    if not can_transition_pack(frm, to):
        return False, "INVALID_TRANSITION: %s -> %s" % (frm, to)
    if method not in VERIFICATION_METHODS or method == "ai_suggestion":
        return False, "AI_MAY_NOT_VERIFY" if method == "ai_suggestion" else "UNKNOWN_VERIFICATION_METHOD"
    issues = validate_pack(pack, store)
    if issues:
        return False, "PACK_INVALID: %s" % issues[0]
    if to == "VERIFIED_FOR_DECLARED_SCOPE" and pack.get("completeness") != "complete_for_declared_scope":
        return False, "SCOPE_COMPLETENESS_NOT_DECLARED"
    v.update(status=to, method=method, verified_at=at, verified_by=verifier, notes=notes)
    pack.setdefault("history", []).append({"from": frm, "to": to, "method": method, "at": at})
    return True, None


def pack_to_ruleset(pack, store):
    """يحوّل حزمة متحقَّقاً منها إلى الشكل الذي يفهمه محرّك القواعد — بلا تعديل معنى."""
    rules = []
    for cid in (pack.get("candidate_ids") or []):
        c = candidate(store, cid)
        if c is None or c.get("status") != "VERIFIED":
            continue
        ok, _ = verification_still_valid(c, store)
        if not ok:
            continue
        rules.append(json.loads(json.dumps(c.get("proposed_rule"))))
    return {"ruleset_id": "%s@%s" % (pack.get("rulepack_id"), pack.get("version")),
            "ruleset_version": pack.get("version"), "standard": pack.get("standard"),
            "edition": pack.get("edition"), "jurisdiction": pack.get("jurisdiction"),
            "coverage_scope": ", ".join(pack.get("coverage_scope") or []),
            "completeness": pack.get("completeness"),
            "regulatory": pack.get("regulatory") is True, "rules": rules}


PACK_ACTIVE_STATES = ("VERIFIED_PARTIAL", "VERIFIED_FOR_DECLARED_SCOPE")


def resolve_active_rules(project, store):
    """لا تفعيل ضمني: الحزمة تعمل فقط إن ربطها المشروع صراحةً وكانت متحقَّقاً منها."""
    out = {"rulesets": [], "activated": [], "rejected": [], "conflicts": []}
    for ref in ((project or {}).get("rulepacks") or []):
        if ref.get("enabled") is not True:
            out["rejected"].append({"rulepack_id": ref.get("rulepack_id"),
                                    "version": ref.get("version"), "reason": "NOT_ENABLED"})
            continue
        p = rulepack(store, ref.get("rulepack_id"), ref.get("version"))
        if p is None:
            out["rejected"].append({"rulepack_id": ref.get("rulepack_id"),
                                    "version": ref.get("version"), "reason": "RULEPACK_NOT_FOUND"})
            continue
        st = (p.get("verification") or {}).get("status")
        if st not in PACK_ACTIVE_STATES:
            out["rejected"].append({"rulepack_id": p.get("rulepack_id"), "version": p.get("version"),
                                    "reason": "RULEPACK_NOT_VERIFIED (%s)" % st})
            continue
        issues = validate_pack(p, store)
        if issues:
            out["rejected"].append({"rulepack_id": p.get("rulepack_id"), "version": p.get("version"),
                                    "reason": "RULEPACK_INVALID", "detail": issues[0]})
            continue
        rs = pack_to_ruleset(p, store)
        out["rulesets"].append(rs)
        out["activated"].append({"rulepack_id": p.get("rulepack_id"), "version": p.get("version"),
                                 "ruleset_id": rs["ruleset_id"], "rules": len(rs["rules"]),
                                 "completeness": p.get("completeness"),
                                 "coverage_scope": list(p.get("coverage_scope") or [])})
    # تعارض غير محسوم: نفس المعرّف بمعنيين مختلفين ⇒ لا اختيار عشوائي
    seen = {}
    for rs in out["rulesets"]:
        for r in rs["rules"]:
            rid = r.get("rule_id")
            h = rule_definition_hash(r)
            prev = seen.get(rid)
            if prev is None:
                seen[rid] = (h, rs["ruleset_id"])
            elif prev[0] != h:
                out["conflicts"].append({"rule_id": rid, "rulesets": [prev[1], rs["ruleset_id"]],
                                         "reason": "RULE_CONFLICT"})
    return out


def evaluate_project(project, subjects, store, context=None):
    """تقييم مشروع مقابل حزمه المفعَّلة صراحةً فقط. التعارض ⇒ NOT_EVALUATED."""
    context = dict(context or {})
    context.setdefault("jurisdiction", (project or {}).get("jurisdiction"))
    active = resolve_active_rules(project, store)
    conflicted = {c["rule_id"] for c in active["conflicts"]}
    results, packs = [], []
    for rs in active["rulesets"]:
        for r in rs["rules"]:
            if r.get("rule_id") in conflicted:
                results.append({"rule_id": r.get("rule_id"), "rule_uid": RULES.rule_uid(r),
                                "ruleset_id": rs["ruleset_id"], "status": "NOT_EVALUATED",
                                "reason": "RULE_CONFLICT", "regulatory": r.get("regulatory") is True,
                                "applicability": "UNDETERMINED", "data_quality": "NOT_REQUIRED",
                                "engine_version": RULES.ENGINE_VERSION,
                                "evaluated_at": context.get("evaluated_at"),
                                "code_required_eligible": False})
                continue
            for s in subjects:
                results.append(RULES.evaluate_rule(r, s, context, rs, active["rulesets"]))
        packs.append(rs)
    agg = RULES.aggregate(results, {"ruleset_id": ",".join(p["ruleset_id"] for p in packs) or None,
                                    "ruleset_version": None,
                                    "standard": packs[0]["standard"] if packs else None,
                                    "edition": packs[0]["edition"] if packs else None,
                                    "coverage_scope": "; ".join(p["coverage_scope"] for p in packs) or None,
                                    "completeness": packs[0]["completeness"] if packs else "unknown"})
    agg["activated_rulepacks"] = active["activated"]
    agg["rejected_rulepacks"] = active["rejected"]
    agg["conflicts"] = active["conflicts"]
    return {"results": results, "summary": agg, "activation": active}


# ------------------------------------------------------------ الاستيراد --
def validate_import(bundle):
    """أمن الاستيراد: يُرفض الحزم المشبوهة كاملةً قبل أي استعمال."""
    issues = []
    if not isinstance(bundle, dict):
        return ["import bundle is not an object"]
    if _has_executable(bundle):
        issues.append("import bundle contains executable/script-like content")
    store = {"documents": bundle.get("documents") or [], "fragments": bundle.get("fragments") or [],
             "candidates": bundle.get("candidates") or [], "rulepacks": bundle.get("rulepacks") or []}
    for key, idf in (("documents", "document_id"), ("fragments", "fragment_id"),
                     ("candidates", "candidate_id")):
        seen = set()
        for it in store[key]:
            i = it.get(idf)
            if i in seen:
                issues.append("duplicate %s: %s" % (idf, i))
            seen.add(i)
    seen = set()
    for p in store["rulepacks"]:
        k = (p.get("rulepack_id"), p.get("version"))
        if k in seen:
            issues.append("duplicate rulepack id/version: %s@%s" % k)
        seen.add(k)
    for d in store["documents"]:
        for i in validate_document(d):
            issues.append("[%s] %s" % (d.get("document_id"), i))
    for f in store["fragments"]:
        for i in validate_fragment(f, store):
            issues.append("[%s] %s" % (f.get("fragment_id"), i))
    for c in store["candidates"]:
        for i in validate_candidate(c, store):
            issues.append("[%s] %s" % (c.get("candidate_id"), i))
    for p in store["rulepacks"]:
        for i in validate_pack(p, store):
            issues.append("[%s] %s" % (p.get("rulepack_id"), i))
    return issues


def store_issues(store):
    return validate_import({"documents": store.get("documents"), "fragments": store.get("fragments"),
                            "candidates": store.get("candidates"),
                            "rulepacks": store.get("rulepacks")})


def audit_export(store, project=None):
    """بيانات تدقيق فقط — لا نصّ مصدر كامل ولا محتوى محمي."""
    docs = [{"document_id": d.get("document_id"), "standard": d.get("standard"),
             "edition": d.get("edition"), "sha256": (d.get("integrity") or {}).get("sha256"),
             "status": (d.get("verification") or {}).get("status"),
             "official": d.get("official") is True, "synthetic": d.get("synthetic") is True}
            for d in (store.get("documents") or [])]
    cands = []
    for c in (store.get("candidates") or []):
        rec = c.get("verification") or {}
        cands.append({"candidate_id": c.get("candidate_id"), "status": c.get("status"),
                      "document_id": c.get("document_id"), "document_hash": c.get("document_hash"),
                      "fragment_ids": list(c.get("fragment_ids") or []),
                      "ai_assisted": c.get("ai_assisted") is True,
                      "rule_id": (c.get("proposed_rule") or {}).get("rule_id"),
                      "rule_revision": (c.get("proposed_rule") or {}).get("revision"),
                      "rule_definition_hash": rule_definition_hash(c.get("proposed_rule")),
                      "verification": {"method": rec.get("method"), "verified_at": rec.get("verified_at"),
                                       "verified_by": rec.get("verifier"),
                                       "document_hash": rec.get("document_hash"),
                                       "rule_definition_hash": rec.get("rule_definition_hash")}
                      if rec else None})
    packs = [{"rulepack_id": p.get("rulepack_id"), "version": p.get("version"),
              "status": (p.get("verification") or {}).get("status"),
              "completeness": p.get("completeness"),
              "coverage_scope": list(p.get("coverage_scope") or []),
              "regulatory": p.get("regulatory") is True,
              "candidate_ids": list(p.get("candidate_ids") or [])}
             for p in (store.get("rulepacks") or [])]
    out = {"pipeline_version": PIPELINE_VERSION, "engine_version": RULES.ENGINE_VERSION,
           "documents": docs, "candidates": cands, "rulepacks": packs,
           "copyright_note": "metadata, hashes and references only — no full source text is exported"}
    if project is not None:
        out["activation"] = resolve_active_rules(project, store)["activated"]
        out["jurisdiction"] = project.get("jurisdiction")
    return out


def regulatory_rule_count(store):
    """قواعد تنظيمية متحقَّق منها فعلاً داخل خط الاستيراد — يجب أن تكون صفراً."""
    n = 0
    for c in (store.get("candidates") or []):
        pr = c.get("proposed_rule") or {}
        if c.get("status") == "VERIFIED" and pr.get("regulatory") is True:
            n += 1
    return n
