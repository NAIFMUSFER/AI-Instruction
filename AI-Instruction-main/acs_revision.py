# -*- coding: utf-8 -*-
# =============================================================================
# acs_revision.py — أساس تثبيت النتائج على مراجعة النموذج التي أنتجتها.
#
# يجيب سؤالين فقط:
#   • أي حالة نموذج بالضبط أنتجت هذه النتيجة؟
#   • هل تغيّر النموذج منذ ذلك التقييم؟
#
# مبادئ صارمة:
#   • البصمة هي المرساة، لا الوقت: الطابع الزمني ليس هوية نموذج.
#   • تقنين حتمي قبل التجزئة: ترتيب المفاتيح والمسافات لا يغيّر البصمة،
#     لكن ترتيب المصفوفات ذات المعنى الموضعي يغيّرها.
#   • حالة العرض (كاميرا/واجهة/تحديد) لا تُبطل تقييماً هندسياً أبداً.
#   • لا إعادة تقييم صامتة: النتيجة القديمة تُوسم STALE وتبقى كما هي.
#   • لا تعديل للنموذج من أجل حساب بصمة — التقنين يعمل على نسخة عميقة.
#   • ما هو مشتقّ (علاقات/تنقّل/مخارج/مسافات) لا يُجزَّأ؛ تُجزَّأ مصادره.
# =============================================================================
import json
import os

import acs_ingest as ING
import acs_project as PROJ
import acs_rules as RULES

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_revision.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
CANONICALIZATION_VERSION = SPEC["canonicalization_version"]
HASH_ALGORITHM = SPEC["hash_algorithm"]
SCOPES = tuple(SPEC["scopes"])
STATUSES = tuple(SPEC["integrity_statuses"])
PRECEDENCE = tuple(SPEC["status_precedence"])
VOLATILE_KEYS = tuple(k.lower() for k in SPEC["volatile_keys"])
_ORDER_INSENSITIVE = {e["path"]: e for e in SPEC["order_insensitive"]}


# ------------------------------------------------------------- التقنين --
def _strip_volatile(v):
    """يزيل حالة العرض/الجلسة أينما وردت. كل ما عداها يدخل البصمة عمداً."""
    if isinstance(v, dict):
        return {k: _strip_volatile(v[k]) for k in v
                if str(k).lower() not in VOLATILE_KEYS}
    if isinstance(v, list):
        return [_strip_volatile(x) for x in v]
    return v


def _sort_key(item, fields):
    out = []
    for f in fields:
        val = item.get(f) if isinstance(item, dict) else None
        out.append((val is None, ING.canonical_json(val) if val is not None else ""))
    return out


def _order_insensitive(items, path):
    spec = _ORDER_INSENSITIVE.get(path)
    if spec is None or not isinstance(items, list):
        return items
    return sorted(items, key=lambda it: _sort_key(it, spec["sort_by"]))


def canonical_building(building, building_id="bld_0"):
    """إسقاط حتمي لمبنى واحد. لا يمسّ الأصل: كل العمل على نسخة عميقة."""
    b = json.loads(json.dumps(building))
    PROJ.ensure_element_ids(b, building_id)          # على النسخة فقط
    b = _strip_volatile(b)
    if isinstance(b.get("levels"), list):
        b["levels"] = _order_insensitive(b["levels"], "levels")
    return b


def _buildings_container(project):
    """المشروع في هذا النظام: {schema, project:{... buildings:[{id, building:{...}}]}}.
    نقبل أيضاً شكلاً مسطّحاً {buildings:[...]} حتى لا نكسر مستهلكاً مستقبلياً."""
    inner = project.get("project")
    return inner if isinstance(inner, dict) and isinstance(inner.get("buildings"), list) else project


def _entry_model(entry):
    return entry.get("building") if isinstance(entry.get("building"), dict) else entry


def canonical_project(project):
    """إسقاط حتمي لمشروع. المباني تُرتَّب بمعرّفاتها، وكل مبنى يُقنَّن بنفسه."""
    p = json.loads(json.dumps(project))
    p = _strip_volatile(p)
    container = _buildings_container(p)
    blds = container.get("buildings")
    if isinstance(blds, list):
        canon = []
        for entry in blds:
            e = dict(entry)
            bid = e.get("id") or e.get("building_id") or "bld_0"
            if isinstance(e.get("building"), dict):
                e["building"] = canonical_building(e["building"], bid)
            else:
                e = canonical_building(e, bid)
            canon.append(e)
        container["buildings"] = _order_insensitive(canon, "buildings")
    return p


def canonical_code_context(project_ctx):
    c = _strip_volatile(json.loads(json.dumps(project_ctx or {})))
    cc = c.get("code_context")
    if isinstance(cc, dict):
        for key in ("rulepacks", "classification_packs"):
            if isinstance(cc.get(key), list):
                cc[key] = _order_insensitive(cc[key], "code_context." + key)
    # القوائم المشتقّة من التفعيل لا تُجزَّأ: التثبيت هو الحقيقة
    c.pop("occupancy", None)
    return c


def canonical_occupancy(occ_store, subject_ids=None):
    """يقنّن التصنيفات المتحقَّق منها فقط — الاقتراحات لا تُثبَّت كحقائق."""
    rows = []
    for c in ((occ_store or {}).get("classifications") or []):
        if c.get("status") != "VERIFIED":
            continue
        if subject_ids is not None and c.get("subject_id") not in subject_ids:
            continue
        rows.append({"subject_id": c.get("subject_id"), "subject_type": c.get("subject_type"),
                     "group": c.get("group"), "subgroup": c.get("subgroup"),
                     "standard": c.get("standard"), "edition": c.get("edition"),
                     "classification_system": c.get("classification_system"),
                     "pack_id": c.get("pack_id"), "pack_version": c.get("pack_version"),
                     "jurisdiction": c.get("jurisdiction")})
    rows.sort(key=lambda r: ING.canonical_json(r))
    return {"verified_classifications": rows}


# ------------------------------------------------------------- البصمات --
def hash_of(canonical):
    return ING.sha256_hex(ING.canonical_json(canonical))


def model_hash(model, scope="building", building_id="bld_0"):
    if scope == "project":
        return hash_of(canonical_project(model))
    return hash_of(canonical_building(model, building_id))


def building_hashes(project):
    out = {}
    container = _buildings_container(project)
    for entry in (container.get("buildings") or []):
        bid = entry.get("id") or entry.get("building_id") or "bld_0"
        out[bid] = hash_of(canonical_building(_entry_model(entry), bid))
    return out


def code_context_hash(project_ctx):
    return hash_of(canonical_code_context(project_ctx))


def occupancy_hash(occ_store, subject_ids=None):
    return hash_of(canonical_occupancy(occ_store, subject_ids))


def revision(model, scope="building", building_id="bld_0", created_at=None):
    """مراجعة مشتقّة عند الطلب — لا تُكتب في النموذج ولا تعتمد على الوقت كهوية."""
    h = model_hash(model, scope, building_id)
    rev = {"revision_id": SPEC["revision_id_prefix"] + h[:16],
           "model_hash": h, "hash_algorithm": HASH_ALGORITHM,
           "canonicalization_version": CANONICALIZATION_VERSION,
           "created_at": created_at, "scope": scope}
    if scope == "project":
        rev["building_hashes"] = building_hashes(model)
    else:
        rev["building_id"] = building_id
    return rev


# ------------------------------------------------------- لقطة النتيجة --
def _source_hashes(rule, ingest_store):
    src = (rule or {}).get("source") or {}
    did = src.get("document_id")
    if not did or ingest_store is None:
        return {}
    doc = ING.document(ingest_store, did)
    if doc is None:
        return {did: None}
    return {did: (doc.get("integrity") or {}).get("sha256")}


def snapshot_result(result, model, scope="building", building_id="bld_0",
                    rule=None, ruleset=None, occupancy_store=None, occupancy_subjects=None,
                    project_ctx=None, ingest_store=None, created_at=None):
    """يربط نتيجة تقييم بالحالة الدقيقة التي أنتجتها. إضافي بالكامل."""
    integ = {
        "status": "CURRENT",
        "model_hash": model_hash(model, scope, building_id) if model is not None else None,
        "model_scope": scope,
        "building_id": building_id if scope == "building" else None,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "rule_hash": ING.rule_definition_hash(rule) if rule else None,
        "rule_id": (rule or {}).get("rule_id") if rule else (result or {}).get("rule_id"),
        "rule_revision": (rule or {}).get("revision") if rule else (result or {}).get("rule_revision"),
        "rulepack_id": (ruleset or {}).get("ruleset_id") if ruleset else (result or {}).get("ruleset_id"),
        "rulepack_version": (ruleset or {}).get("ruleset_version") if ruleset
                            else (result or {}).get("ruleset_version"),
        "source_document_hashes": _source_hashes(rule, ingest_store),
        "occupancy_refs": sorted(occupancy_subjects) if occupancy_subjects else [],
        "occupancy_hash": occupancy_hash(occupancy_store, occupancy_subjects)
                          if occupancy_store is not None else None,
        "code_context_hash": code_context_hash(project_ctx) if project_ctx is not None else None,
        "engine_version": RULES.ENGINE_VERSION,
        "evaluated_at": created_at if created_at is not None else (result or {}).get("evaluated_at"),
    }
    return {"result": json.loads(json.dumps(result)) if result is not None else None,
            "integrity": integ}


def _pick(statuses):
    for s in PRECEDENCE:
        if s in statuses:
            return s
    return "CURRENT"


def check_result_integrity(snapshot, model=None, rule=None, ruleset=None,
                           occupancy_store=None, project_ctx=None, ingest_store=None):
    """يقارن كل مرساة مسجَّلة بالحالة الحالية ويعيد أسباباً دقيقة، لا حكماً واحداً غامضاً."""
    integ = (snapshot or {}).get("integrity") or {}
    reasons, found, unchecked = [], set(), []

    if integ.get("canonicalization_version") != CANONICALIZATION_VERSION:
        reasons.append({"anchor": "canonicalization_version", "reason": "CANONICALIZATION_VERSION_MISMATCH",
                        "stored": integ.get("canonicalization_version"),
                        "current": CANONICALIZATION_VERSION})
        return {"status": "UNVERIFIABLE", "reasons": reasons, "unchecked": ["all"],
                "canonicalization_version": CANONICALIZATION_VERSION}
    if integ.get("hash_algorithm") != HASH_ALGORITHM:
        reasons.append({"anchor": "hash_algorithm", "reason": "HASH_ALGORITHM_MISMATCH"})
        return {"status": "UNVERIFIABLE", "reasons": reasons, "unchecked": ["all"],
                "canonicalization_version": CANONICALIZATION_VERSION}

    if model is not None and integ.get("model_hash"):
        cur = model_hash(model, integ.get("model_scope") or "building",
                         integ.get("building_id") or "bld_0")
        if cur != integ["model_hash"]:
            found.add("STALE_MODEL_CHANGED")
            reasons.append({"anchor": "model_hash", "reason": "MODEL_CHANGED",
                            "stored": integ["model_hash"], "current": cur})
    else:
        unchecked.append("model_hash")

    if rule is not None and integ.get("rule_hash"):
        cur = ING.rule_definition_hash(rule)
        if cur != integ["rule_hash"]:
            found.add("STALE_RULE_CHANGED")
            reasons.append({"anchor": "rule_hash", "reason": "RULE_MEANING_CHANGED",
                            "stored": integ["rule_hash"], "current": cur})
    elif integ.get("rule_hash"):
        unchecked.append("rule_hash")

    if ruleset is not None and integ.get("rulepack_id"):
        if (ruleset.get("ruleset_id") != integ.get("rulepack_id")
                or ruleset.get("ruleset_version") != integ.get("rulepack_version")):
            found.add("STALE_RULEPACK_CHANGED")
            reasons.append({"anchor": "rulepack", "reason": "RULEPACK_CHANGED",
                            "stored": "%s@%s" % (integ.get("rulepack_id"), integ.get("rulepack_version")),
                            "current": "%s@%s" % (ruleset.get("ruleset_id"),
                                                  ruleset.get("ruleset_version"))})
    elif integ.get("rulepack_id"):
        unchecked.append("rulepack")

    if occupancy_store is not None and integ.get("occupancy_hash") is not None:
        cur = occupancy_hash(occupancy_store, integ.get("occupancy_refs") or None)
        if cur != integ["occupancy_hash"]:
            found.add("STALE_OCCUPANCY_CHANGED")
            reasons.append({"anchor": "occupancy_hash", "reason": "OCCUPANCY_CLASSIFICATION_CHANGED",
                            "stored": integ["occupancy_hash"], "current": cur})
    elif integ.get("occupancy_hash") is not None:
        unchecked.append("occupancy_hash")

    if project_ctx is not None and integ.get("code_context_hash") is not None:
        cur = code_context_hash(project_ctx)
        if cur != integ["code_context_hash"]:
            found.add("STALE_CODE_CONTEXT_CHANGED")
            reasons.append({"anchor": "code_context_hash", "reason": "CODE_CONTEXT_CHANGED",
                            "stored": integ["code_context_hash"], "current": cur})
    elif integ.get("code_context_hash") is not None:
        unchecked.append("code_context_hash")

    stored_src = integ.get("source_document_hashes") or {}
    if stored_src:
        if ingest_store is None:
            unchecked.append("source_document_hashes")
        else:
            for did, h in stored_src.items():
                doc = ING.document(ingest_store, did)
                cur = (doc.get("integrity") or {}).get("sha256") if doc else None
                if cur != h:
                    found.add("STALE_SOURCE_CHANGED")
                    reasons.append({"anchor": "source_document", "reason": "SOURCE_BYTES_CHANGED",
                                    "document_id": did, "stored": h, "current": cur})

    if found:
        status = _pick(found)
    elif unchecked:
        status = "CURRENT_UNDER_SAME_HASH"
        reasons.append({"anchor": "coverage", "reason": "ANCHORS_NOT_SUPPLIED_FOR_CHECK",
                        "unchecked": sorted(set(unchecked))})
    else:
        status = "CURRENT"
    return {"status": status, "reasons": reasons, "unchecked": sorted(set(unchecked)),
            "canonicalization_version": CANONICALIZATION_VERSION}


def apply_integrity(snapshot, *args, **kwargs):
    """يوسم اللقطة بحالتها الحالية دون إعادة تقييم أي شيء — لا حساب صامت."""
    chk = check_result_integrity(snapshot, *args, **kwargs)
    snap = json.loads(json.dumps(snapshot))
    snap["integrity"]["status"] = chk["status"]
    snap["integrity"]["integrity_reasons"] = chk["reasons"]
    snap["integrity"]["unchecked_anchors"] = chk["unchecked"]
    return snap


def stale_results(snapshots, **kwargs):
    """يعيد اللقطات التي لم تعد جارية، مع سببها. لا يُعاد حساب أي نتيجة."""
    out = []
    for s in (snapshots or []):
        chk = check_result_integrity(s, **kwargs)
        if chk["status"] not in ("CURRENT", "CURRENT_UNDER_SAME_HASH"):
            out.append({"rule_id": (s.get("integrity") or {}).get("rule_id"),
                        "result": ((s.get("result") or {}).get("status")),
                        "integrity_status": chk["status"], "reasons": chk["reasons"]})
    return out


def export_snapshot(snapshot):
    """تصدير النتيجة مع بيانات النزاهة — النتيجة القديمة لا تظهر أبداً كأنها جارية."""
    integ = dict((snapshot or {}).get("integrity") or {})
    res = (snapshot or {}).get("result") or {}
    return {"rule_id": integ.get("rule_id"), "result": res.get("status"),
            "reason": res.get("reason"),
            "presented_as_current": integ.get("status") in ("CURRENT", "CURRENT_UNDER_SAME_HASH"),
            "integrity": {"status": integ.get("status"), "model_hash": integ.get("model_hash"),
                          "model_scope": integ.get("model_scope"), "rule_hash": integ.get("rule_hash"),
                          "rulepack_id": integ.get("rulepack_id"),
                          "rulepack_version": integ.get("rulepack_version"),
                          "source_document_hashes": integ.get("source_document_hashes"),
                          "occupancy_hash": integ.get("occupancy_hash"),
                          "code_context_hash": integ.get("code_context_hash"),
                          "canonicalization_version": integ.get("canonicalization_version"),
                          "engine_version": integ.get("engine_version"),
                          "evaluated_at": integ.get("evaluated_at"),
                          "integrity_reasons": integ.get("integrity_reasons")}}


# --------------------------------------------------------- فروق المراجعة --
def _diff(a, b, path, out, limit):
    if len(out) >= limit:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = "%s.%s" % (path, k) if path else str(k)
            if k not in a:
                out.append({"path": p, "change": "added"})
            elif k not in b:
                out.append({"path": p, "change": "removed"})
            else:
                _diff(a[k], b[k], p, out, limit)
        return
    if isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = "%s[%d]" % (path, i)
            if i >= len(a):
                out.append({"path": p, "change": "added"})
            elif i >= len(b):
                out.append({"path": p, "change": "removed"})
            else:
                _diff(a[i], b[i], p, out, limit)
        return
    if a != b:
        out.append({"path": path, "change": "changed", "from": a, "to": b})


def revision_diff(model_a, model_b, scope="building", building_id="bld_0", limit=200):
    """فروق واقعية بين مراجعتين — للتدقيق فقط، بلا أي استنتاج هندسي."""
    ca = canonical_project(model_a) if scope == "project" else canonical_building(model_a, building_id)
    cb = canonical_project(model_b) if scope == "project" else canonical_building(model_b, building_id)
    out = []
    _diff(ca, cb, "", out, limit)
    return {"scope": scope, "hash_a": hash_of(ca), "hash_b": hash_of(cb),
            "identical": hash_of(ca) == hash_of(cb),
            "changes": out, "truncated": len(out) >= limit,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "note": "factual differences only — no engineering conclusion is drawn"}
