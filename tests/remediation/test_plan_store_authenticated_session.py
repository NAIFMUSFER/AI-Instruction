#!/usr/bin/env python3
"""Regression for the authenticated host -> Supabase PlanStore trust bridge."""
import json
import os

from acs_plan_review import PlanError
from acs_plan_session import authenticated_supabase_plan_store

ACTOR = "11111111-1111-4111-8111-111111111111"
ATTACKER = "22222222-2222-4222-8222-222222222222"
TOKEN = "header.payload.signature"
URL = "https://example.supabase.co"
KEY = "sb_publishable_regression_only"

os.environ["ACS_ENV"] = "production"
os.environ["ACS_AUTH_MODE"] = "oidc"
os.environ["ACS_AUTH_PROVIDER"] = "supabase"
os.environ["ACS_AUTH_SUPABASE_URL"] = URL
os.environ["ACS_AUTH_SUPABASE_PUBLISHABLE_KEY"] = KEY


def expect_error(code, scope):
    try:
        authenticated_supabase_plan_store(scope)
        raise AssertionError("invalid authenticated PlanStore scope was accepted")
    except PlanError as exc:
        assert exc.code == code, (exc.code, code)
        # Admission failures must never reflect a bearer token.
        assert TOKEN not in str(exc)


# No verified auth subject: bearer presence alone must never create a store.
expect_error("AUTH_REQUIRED", {
    "type": "http",
    "state": {},
    "headers": [(b"authorization", ("Bearer " + TOKEN).encode())],
})

# A verified subject without its current request bearer is also insufficient.
expect_error("AUTH_REQUIRED", {
    "type": "http",
    "state": {"authenticated_user_id": ACTOR},
    "headers": [],
})

# Ambiguous duplicate Authorization headers fail closed.
expect_error("AUTH_REQUIRED", {
    "type": "http",
    "state": {"authenticated_user_id": ACTOR},
    "headers": [
        (b"authorization", ("Bearer " + TOKEN).encode()),
        (b"authorization", b"Bearer attacker-token"),
    ],
})

calls = []
responses = [(200, {
    "schema": "acs.plan-store/1.0",
    "project_id": "33333333-3333-4333-8333-333333333333",
    "role": "owner",
    "head_revision_id": None,
    "baseline_revision_id": None,
    "revisions": [],
})]


def transport(**kwargs):
    calls.append(kwargs)
    status, payload = responses.pop(0)
    return status, json.dumps(payload, separators=(",", ":")).encode()


# Deliberately include attacker-controlled project/actor-looking values in other
# ASGI fields.  The factory has no actor argument and must ignore all of them.
scope = {
    "type": "http",
    "path": "/v1/plan/projects/attacker-selected",
    "query_string": ("actor_id=" + ATTACKER).encode(),
    "state": {"authenticated_user_id": ACTOR},
    "headers": [
        (b"content-type", b"application/json"),
        (b"authorization", ("Bearer " + TOKEN).encode()),
        (b"x-actor-id", ATTACKER.encode()),
    ],
}
store = authenticated_supabase_plan_store(scope, transport=transport)
assert store.actor_id == ACTOR
assert TOKEN not in repr(store)

PROJECT = "33333333-3333-4333-8333-333333333333"
state = store.project_state(PROJECT, actor_id=ACTOR)
assert state["role"] == "owner"
req = calls[-1]
assert req["url"] == URL + "/rest/v1/rpc/acs_plan_project_state"
assert req["headers"]["Authorization"] == "Bearer " + TOKEN
assert req["headers"]["apikey"] == KEY
wire = json.dumps({
    "url": req["url"],
    "headers": req["headers"],
    "body": req["body"].decode(),
}, separators=(",", ":"))
assert "service_role" not in wire.lower()
assert ATTACKER not in wire

# Store methods remain actor-bound even after the session bridge is created.
try:
    store.project_state(PROJECT, actor_id=ATTACKER)
    raise AssertionError("caller changed the authenticated PlanStore actor")
except PlanError as exc:
    assert exc.code == "PROJECT_ACCESS_DENIED"
assert len(calls) == 1

# Generic OIDC must not silently acquire Supabase persistence authority.
os.environ["ACS_AUTH_PROVIDER"] = "oidc"
os.environ["ACS_AUTH_USERINFO_URL"] = "https://identity.example.test/userinfo"
expect_error("STORE_UNAVAILABLE", scope)

print("ACS authenticated PlanStore session boundary: PASS")
