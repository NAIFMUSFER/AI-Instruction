from __future__ import annotations

import asyncio
import json
import unittest

import acs_plan_http as HTTP
from acs_plan_review import PlanError


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_ID = "22222222-2222-4222-8222-222222222222"
TOKEN = "secret-user-bearer"


def _scope(path: str, *, method: str = "POST", headers=None):
    return {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers or [(b"authorization", ("Bearer " + TOKEN).encode("ascii"))],
        "state": {},
    }


def _receive_for(payload: object, *, on_read=None):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if on_read:
            on_read()
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


async def _capture_send(messages):
    async def send(message):
        messages.append(message)
    return send


def _json_response(messages):
    start = next(m for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return start["status"], json.loads(body.decode("utf-8"))


class PlanHttpCommandBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.orig_authorize = HTTP.AUTH.authorize_asgi
        self.orig_factory = HTTP.SESSION.authenticated_supabase_plan_store
        self.orig_execute = HTTP.PERSIST.execute_persisted_plan_command
        self.orig_verifier = HTTP.BRIDGE.existing_geometry_verifier

    def tearDown(self):
        HTTP.AUTH.authorize_asgi = self.orig_authorize
        HTTP.SESSION.authenticated_supabase_plan_store = self.orig_factory
        HTTP.PERSIST.execute_persisted_plan_command = self.orig_execute
        HTTP.BRIDGE.existing_geometry_verifier = self.orig_verifier

    def _middleware(self, fallback_calls):
        async def fallback(scope, receive, send):
            fallback_calls.append(scope.get("path"))
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        return HTTP.PlanCommandMiddleware(fallback)

    def test_unrelated_route_passes_through_without_auth_or_body_read(self):
        events = []

        async def forbidden_auth(scope, send):
            events.append("auth")
            raise AssertionError("unrelated route must not invoke plan auth")

        HTTP.AUTH.authorize_asgi = forbidden_auth
        fallback = []
        middleware = self._middleware(fallback)
        messages = []

        async def receive():
            events.append("read")
            raise AssertionError("fallback test must not read body")

        asyncio.run(middleware(_scope("/health", method="GET"), receive, asyncio.run(_capture_send(messages))))
        self.assertEqual(fallback, ["/health"])
        self.assertEqual(events, [])

    def test_authentication_happens_before_body_read(self):
        order = []

        async def reject(scope, send):
            order.append("auth")
            await send({"type": "http.response.start", "status": 401, "headers": []})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})
            return False

        HTTP.AUTH.authorize_asgi = reject
        middleware = self._middleware([])
        messages = []
        receive = _receive_for({"action": "review", "revision_id": "r1"}, on_read=lambda: order.append("body"))
        asyncio.run(middleware(
            _scope(f"/v1/projects/{PROJECT_ID}/plan/commands"),
            receive,
            asyncio.run(_capture_send(messages)),
        ))
        self.assertEqual(order, ["auth"])
        self.assertEqual(messages[0]["status"], 401)

    def test_authenticated_non_provider_command_binds_verified_actor_and_path_project(self):
        calls = {}
        store = object()
        verifier = object()

        async def authorize(scope, send):
            scope.setdefault("state", {})["authenticated_user_id"] = ACTOR_ID
            return True

        def factory(scope):
            calls["factory_actor"] = scope["state"]["authenticated_user_id"]
            return store

        def execute(got_store, project_id, command, *, actor_id, provider_model=None, verifier=None):
            calls.update({
                "store": got_store,
                "project_id": project_id,
                "command": command,
                "actor_id": actor_id,
                "provider_model": provider_model,
                "verifier": verifier,
            })
            return {"schema": "acs.plan-persisted-command-result/1.0", "action": command["action"]}

        HTTP.AUTH.authorize_asgi = authorize
        HTTP.SESSION.authenticated_supabase_plan_store = factory
        HTTP.PERSIST.execute_persisted_plan_command = execute
        HTTP.BRIDGE.existing_geometry_verifier = verifier

        middleware = self._middleware([])
        messages = []
        command = {"action": "review", "revision_id": "r1"}
        asyncio.run(middleware(
            _scope(f"/v1/projects/{PROJECT_ID}/plan/commands"),
            _receive_for(command),
            asyncio.run(_capture_send(messages)),
        ))
        status, body = _json_response(messages)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(calls["store"], store)
        self.assertEqual(calls["project_id"], PROJECT_ID)
        self.assertEqual(calls["actor_id"], ACTOR_ID)
        self.assertEqual(calls["command"], command)
        self.assertIsNone(calls["provider_model"])
        self.assertIs(calls["verifier"], verifier)
        self.assertNotIn(ACTOR_ID, json.dumps(body))
        self.assertNotIn(TOKEN, json.dumps(body))

    def test_chat_edit_is_fail_closed_before_store_or_provider_work(self):
        touched = []

        async def authorize(scope, send):
            scope.setdefault("state", {})["authenticated_user_id"] = ACTOR_ID
            return True

        HTTP.AUTH.authorize_asgi = authorize
        HTTP.SESSION.authenticated_supabase_plan_store = lambda scope: touched.append("store")
        HTTP.PERSIST.execute_persisted_plan_command = lambda *a, **k: touched.append("execute")

        middleware = self._middleware([])
        messages = []
        asyncio.run(middleware(
            _scope(f"/v1/projects/{PROJECT_ID}/plan/commands"),
            _receive_for({"action": "chat_edit", "expected_head": "r1", "notes": [{"text": "كبر المجلس"}]}),
            asyncio.run(_capture_send(messages)),
        ))
        status, body = _json_response(messages)
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "PLAN_PROVIDER_COMMAND_REQUIRES_ISOLATED_JOB")
        self.assertEqual(touched, [])

    def test_client_cannot_smuggle_project_authority_inside_command(self):
        async def authorize(scope, send):
            scope.setdefault("state", {})["authenticated_user_id"] = ACTOR_ID
            return True

        HTTP.AUTH.authorize_asgi = authorize
        HTTP.SESSION.authenticated_supabase_plan_store = lambda scope: object()

        def execute(*args, **kwargs):
            raise PlanError("CLIENT_PROJECT_AUTHORITY", "Project/workspace authority must come from authenticated host session")

        HTTP.PERSIST.execute_persisted_plan_command = execute
        middleware = self._middleware([])
        messages = []
        asyncio.run(middleware(
            _scope(f"/v1/projects/{PROJECT_ID}/plan/commands"),
            _receive_for({"action": "review", "revision_id": "r1", "project_id": "attacker"}),
            asyncio.run(_capture_send(messages)),
        ))
        status, body = _json_response(messages)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "CLIENT_PROJECT_AUTHORITY")

    def test_route_requires_canonical_uuid_project_identity(self):
        touched = []

        async def authorize(scope, send):
            touched.append("auth")
            return True

        HTTP.AUTH.authorize_asgi = authorize
        middleware = self._middleware([])
        messages = []
        asyncio.run(middleware(
            _scope("/v1/projects/not-a-uuid/plan/commands"),
            _receive_for({"action": "review", "revision_id": "r1"}),
            asyncio.run(_capture_send(messages)),
        ))
        status, body = _json_response(messages)
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "PLAN_PROJECT_ROUTE_NOT_FOUND")
        self.assertEqual(touched, [])

    def test_body_limit_fails_before_store_construction(self):
        async def authorize(scope, send):
            scope.setdefault("state", {})["authenticated_user_id"] = ACTOR_ID
            return True

        HTTP.AUTH.authorize_asgi = authorize
        HTTP.SESSION.authenticated_supabase_plan_store = lambda scope: (_ for _ in ()).throw(AssertionError("store must not be constructed"))
        middleware = self._middleware([])
        messages = []
        huge = {"action": "review", "revision_id": "x" * (HTTP.MAX_BODY_BYTES + 100)}
        asyncio.run(middleware(
            _scope(f"/v1/projects/{PROJECT_ID}/plan/commands"),
            _receive_for(huge),
            asyncio.run(_capture_send(messages)),
        ))
        status, body = _json_response(messages)
        self.assertEqual(status, 413)
        self.assertEqual(body["error"]["code"], "PLAN_COMMAND_BODY_TOO_LARGE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
