#!/usr/bin/env python3
import hashlib
import json
from types import SimpleNamespace

from acs_plan_review import PlanError, canonical, digest
from acs_supabase_plan_store import SupabasePlanStore

ACTOR = "11111111-1111-4111-8111-111111111111"
PROJECT = "22222222-2222-4222-8222-222222222222"

calls = []
responses = []

def transport(**kwargs):
    calls.append(kwargs)
    if not responses:
        raise AssertionError("unexpected transport call")
    status, payload = responses.pop(0)
    raw = payload if isinstance(payload, bytes) else json.dumps(payload, separators=(",", ":")).encode()
    return status, raw

store = SupabasePlanStore(
    "https://example.supabase.co", "sb_publishable_test", "user-access-token",
    actor_id=ACTOR, transport=transport,
)

# Actor authority is bound to the verified session subject, never caller input.
try:
    store.project_state(PROJECT, actor_id="33333333-3333-4333-8333-333333333333")
    raise AssertionError("actor mismatch accepted")
except PlanError as exc:
    assert exc.code == "PROJECT_ACCESS_DENIED"
assert not calls

responses.append((200, {
    "schema": "acs.plan-store/1.0", "project_id": PROJECT, "role": "owner",
    "head_revision_id": None, "baseline_revision_id": None, "revisions": [],
}))
state = store.project_state(PROJECT, actor_id=ACTOR)
assert state["role"] == "owner"
req = calls[-1]
assert req["url"].endswith("/rest/v1/rpc/acs_plan_project_state")
assert req["headers"]["Authorization"] == "Bearer user-access-token"
assert req["headers"]["apikey"] == "sb_publishable_test"
assert "service_role" not in json.dumps(req).lower()

# Build a real self-consistent canonical revision receipt, not a fixture that
# bypasses receipt validation.
model = {"levels": [], "floors": {}}
requirements = []
locks = []
model_hash = hashlib.sha256(canonical(model).encode("utf-8")).hexdigest()
content_hash = digest({"model": model, "requirements": requirements, "brief": {}, "locks": locks})
bound_hash = digest({
    "schema": "acs.plan-lock-binding/1.0",
    "revision_id": "rev-1",
    "revision_content_hash": content_hash,
    "model_hash": model_hash,
    "semantic_lock_manifest_hash": None,
})
revision = SimpleNamespace(
    id="rev-1", number=1, parent_id=None, model=model,
    requirements_json=json.dumps(requirements), brief={}, note="initial",
    locked_rooms=tuple(), created_at="2026-09-13T00:00:00+00:00",
    model_hash=model_hash, content_hash=content_hash,
    semantic_lock_manifest=None, semantic_lock_manifest_hash=None,
    semantic_lock_count=0, bound_content_hash=bound_hash,
)
from acs_plan_store import revision_document, approval_document
rev_doc = revision_document(revision)
responses.append((200, rev_doc))
out = store.save_revision(PROJECT, actor_id=ACTOR, revision=revision, expected_head=None)
assert out == rev_doc
payload = json.loads(calls[-1]["body"])
assert payload["p_project"] == PROJECT
assert payload["p_expected_head"] is None
assert payload["p_revision"]["model_hash"] == model_hash

approval = SimpleNamespace(
    revision_id="rev-1", revision_content_hash=content_hash,
    bound_content_hash=bound_hash, model_hash=model_hash,
    semantic_lock_manifest_hash=None, semantic_lock_count=0,
    actor_label=ACTOR, approved_at="2026-09-13T00:01:00+00:00",
    scope="CONCEPTUAL_DESIGN_ONLY",
)
app_doc = approval_document(approval)
responses.append((200, app_doc))
assert store.save_approval(PROJECT, actor_id=ACTOR, approval=approval, expected_head="rev-1") == app_doc
assert calls[-1]["url"].endswith("/rest/v1/rpc/acs_save_plan_approval")

# Known atomic RPC errors map to existing Plan-first error contracts; unknown
# backend errors fail closed without reflecting remote text.
responses.append((400, {"message": "ACS_STALE_REVISION"}))
try:
    store.save_revision(PROJECT, actor_id=ACTOR, revision=revision, expected_head=None)
    raise AssertionError("stale write accepted")
except PlanError as exc:
    assert exc.code == "STALE_REVISION"

responses.append((500, {"message": "database internals must never leak"}))
try:
    store.project_state(PROJECT, actor_id=ACTOR)
    raise AssertionError("backend failure accepted")
except PlanError as exc:
    assert exc.code == "STORE_UNAVAILABLE"
    assert "database internals" not in str(exc)

print("ACS Supabase PlanStore adapter contract: PASS")
