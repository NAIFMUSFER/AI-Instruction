"""ACS Designer (Claude Managed Agents) against an offline stand-in for the API.

No network and no paid call: httpx.MockTransport answers every request the way
the Managed Agents API reference documents, and records what was sent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import acs_agent_designer as D  # noqa: E402

KEY = "sk-ant-test-0000000000000000000000000000"


class FakeAPI:
    def __init__(self, sessions=(), agents=(), environments=()):
        self.sent, self.files, self.uploads = [], {}, 0
        self.sessions = {s["id"]: s for s in sessions}
        self.agents, self.environments = list(agents), list(environments)

    def __call__(self, request):
        self.sent.append(request)
        path, method = request.url.path, request.method
        body = json.loads(request.content) if request.headers.get("content-type") == "application/json" else None
        if path == "/v1/environments" and method == "GET":
            return httpx.Response(200, json={"data": self.environments})
        if path == "/v1/environments" and method == "POST":
            env = {"id": "env_0123456789", "name": body["name"]}
            self.environments.append(env)
            return httpx.Response(200, json=env)
        if path == "/v1/agents" and method == "GET":
            return httpx.Response(200, json={"data": self.agents})
        if path == "/v1/agents" and method == "POST":
            agent = dict(body, id="agent_0123456789", version=1)
            self.agents.append(agent)
            return httpx.Response(200, json=agent)
        if path.startswith("/v1/agents/") and method == "POST":
            agent = next(a for a in self.agents if a["id"] == path.rsplit("/", 1)[1])
            agent.update(body, version=agent["version"] + 1)
            return httpx.Response(200, json=agent)
        if path == "/v1/files" and method == "POST":
            self.uploads += 1
            return httpx.Response(200, json={"id": "file_up%010d" % self.uploads})
        if path == "/v1/files" and method == "GET":
            sid = request.url.params.get("scope_id")
            return httpx.Response(200, json={"data": self.files.get(sid, [])})
        if path.startswith("/v1/files/") and path.endswith("/content"):
            return httpx.Response(200, content=b"%PDF-1.7 plans")
        if path == "/v1/sessions" and method == "GET":
            return httpx.Response(200, json={"data": list(self.sessions.values())})
        if path == "/v1/sessions" and method == "POST":
            sid = "sesn_%010d" % (len(self.sessions) + 1)
            self.sessions[sid] = dict(body, id=sid, status="running", usage={})
            return httpx.Response(200, json=self.sessions[sid])
        if path.startswith("/v1/sessions/") and path.endswith("/events") and method == "POST":
            sid = path.split("/")[3]
            self.sessions[sid]["status"] = "running"
            return httpx.Response(200, json={"data": []})
        if path.startswith("/v1/sessions/") and method == "GET":
            s = self.sessions.get(path.rsplit("/", 1)[1])
            return httpx.Response(200, json=s) if s else httpx.Response(404, json={"error": {}})
        return httpx.Response(500, json={"error": {"message": "unexpected " + method + " " + path}})

    def client(self):
        return D.Client(key=KEY, transport=httpx.MockTransport(self))

    def posted(self, path):
        return [json.loads(r.content) for r in self.sent if r.method == "POST" and r.url.path == path
                and r.headers.get("content-type") == "application/json"]


def spent(sid, cents, status="idle", cap=800):
    return {"id": sid, "status": status, "metadata": {"acs": D.PILOT_TAG},
            "usage": {"list_cost": {"amount": str(cents), "currency": "USD"}},
            "budget": {"type": "limit", "max_list_cost": {"amount": str(cap), "currency": "USD"}}}


class StartSession(unittest.TestCase):
    def setUp(self):
        D._UPLOADED.clear()
        self.api = FakeAPI()
        self.out = D.start("عمارة سكنية ٤ أدوار على أرض ٣٠ في ٢٥ متر", "apt4", client=self.api.client())
        self.session = self.api.posted("/v1/sessions")[0]

    def test_one_session_with_a_hard_budget_an_outcome_and_the_checks(self):
        self.assertEqual(self.out, {"session_id": "sesn_0000000001", "status": "running", "budget_cents": 800})
        self.assertEqual(self.session["budget"], {"type": "limit", "max_list_cost": {"amount": "800", "currency": "USD"}})
        self.assertEqual(self.session["metadata"], {"acs": D.PILOT_TAG})
        [event] = self.session["initial_events"]
        self.assertEqual(event["type"], "user.define_outcome")
        self.assertEqual(event["max_iterations"], 3)
        self.assertIn("<brief>\nعمارة سكنية ٤ أدوار على أرض ٣٠ في ٢٥ متر\n</brief>", event["description"])
        self.assertEqual(event["rubric"], {"type": "text", "content": D.RUBRIC})
        mounts = sorted(r["mount_path"] for r in self.session["resources"])
        self.assertEqual(mounts, sorted("/acs_checks/" + n for n in ("README.md",) + D.CHECK_FILES))

    def test_the_agent_is_opus_with_sandbox_tools_and_no_web(self):
        [agent] = self.api.posted("/v1/agents")
        self.assertEqual(agent["model"], "claude-opus-5-5")
        self.assertEqual(agent["metadata"]["fingerprint"], D.agent_fingerprint())
        [toolset] = agent["tools"]
        self.assertEqual({c["name"]: c["enabled"] for c in toolset["configs"]}, {"web_fetch": False, "web_search": False})
        self.assertEqual(self.session["agent"], {"type": "agent", "id": "agent_0123456789", "version": 1})
        [env] = self.api.posted("/v1/environments")
        self.assertEqual(env["config"]["networking"], {"type": "limited", "allow_package_managers": True})

    def test_headers_carry_the_version_and_beta_but_never_the_key_in_a_body(self):
        for r in self.api.sent:
            self.assertEqual(r.headers["anthropic-version"], D.API_VERSION)
            self.assertEqual(r.headers["x-api-key"], KEY)
            self.assertNotIn(KEY.encode(), r.content)
        betas = {r.url.path: r.headers.get("anthropic-beta") for r in self.api.sent}
        self.assertEqual(betas["/v1/sessions"], D.BETA)
        self.assertIsNone(betas["/v1/files"], "uploads go to the stable Files API")

    def test_a_second_session_reuses_the_agent_the_environment_and_the_uploads(self):
        before = self.api.uploads
        D.start("فيلا دورين", client=self.api.client())
        self.assertEqual(len(self.api.posted("/v1/agents")), 1)
        self.assertEqual(len(self.api.posted("/v1/environments")), 1)
        self.assertEqual(self.api.uploads, before)

    def test_a_changed_prompt_updates_the_agent_in_place(self):
        with patch.object(D, "SYSTEM", D.SYSTEM + "\nExtra."):
            D.start("فيلا", client=self.api.client())
        updates = [r for r in self.api.sent if r.method == "POST" and r.url.path == "/v1/agents/agent_0123456789"]
        self.assertEqual(len(updates), 1)
        self.assertEqual(self.api.posted("/v1/sessions")[-1]["agent"]["version"], 2)


class Spend(unittest.TestCase):
    def test_the_pilot_cap_counts_spent_and_running_caps(self):
        api = FakeAPI(sessions=[spent("sesn_a000000001", 1500), spent("sesn_a000000002", 900, "running", 1000),
                                dict(spent("sesn_a000000003", 9999), metadata={})])
        self.assertEqual(D.committed_cents(api.client()), 2500, "another project's session is not the pilot's")
        D.start("مستودع", budget_cents=800, client=api.client())      # 2500 + 800 <= 4000
        api = FakeAPI(sessions=[spent("sesn_a000000001", 3300)])
        with self.assertRaises(D.DesignerError) as refused:
            D.start("مستودع", budget_cents=800, client=api.client())
        self.assertEqual(refused.exception.code, "DESIGNER_PILOT_CAP_REACHED")
        self.assertEqual(api.posted("/v1/sessions"), [])

    def test_budgets_and_briefs_out_of_bounds_are_refused_before_any_call(self):
        api = FakeAPI()
        for kwargs, code in (({"budget_cents": 50}, "DESIGNER_BUDGET_INVALID"),
                             ({"budget_cents": 1001}, "DESIGNER_BUDGET_INVALID"),
                             ({"budget_cents": 8.0}, "DESIGNER_BUDGET_INVALID")):
            with self.assertRaises(D.DesignerError) as refused:
                D.start("فيلا", client=api.client(), **kwargs)
            self.assertEqual(refused.exception.code, code)
        for brief, code in (("   ", "DESIGNER_BRIEF_REQUIRED"), ("x" * 8001, "DESIGNER_BRIEF_TOO_LONG"),
                            (None, "DESIGNER_BRIEF_REQUIRED")):
            with self.assertRaises(D.DesignerError) as refused:
                D.start(brief, client=api.client())
            self.assertEqual(refused.exception.code, code)
        self.assertEqual(api.sent, [])


class Results(unittest.TestCase):
    def setUp(self):
        s = spent("sesn_b000000001", 512)
        s["outcome_evaluations"] = [{"result": "needs_revision", "iteration": 0, "explanation": "criterion 4"},
                                    {"result": "satisfied", "iteration": 1, "explanation": "all met"}]
        s["usage"]["active_seconds"] = 1260
        self.api = FakeAPI(sessions=[s, dict(spent("sesn_c000000001", 1), metadata={"acs": "other"})])
        self.api.files["sesn_b000000001"] = [{"id": "file_p000000001", "filename": "plans.pdf", "size_bytes": 14}]

    def test_status_reports_cost_time_and_grading(self):
        out = D.status("sesn_b000000001", client=self.api.client())
        self.assertEqual((out["cost_cents"], out["budget_cents"], out["active_seconds"]), (512, 800, 1260))
        self.assertEqual([o["result"] for o in out["outcomes"]], ["needs_revision", "satisfied"])

    def test_only_the_pilots_sessions_and_their_own_files_are_served(self):
        self.assertEqual(D.download("sesn_b000000001", "file_p000000001", client=self.api.client()),
                         ("plans.pdf", b"%PDF-1.7 plans"))
        for sid, fid, code in (("sesn_c000000001", "file_p000000001", "DESIGNER_NOT_FOUND"),
                               ("sesn_b000000001", "file_x000000009", "DESIGNER_NOT_FOUND"),
                               ("../v1/agents", "file_p000000001", "DESIGNER_SESSION_INVALID"),
                               ("sesn_b000000001", "file_p/../x", "DESIGNER_FILE_INVALID")):
            with self.assertRaises(D.DesignerError) as refused:
                D.download(sid, fid, client=self.api.client())
            self.assertEqual(refused.exception.code, code)

    def test_provider_errors_carry_only_a_fixed_code(self):
        api = httpx.MockTransport(lambda r: httpx.Response(400, json={"error": {"message": "echo: سر"}}))
        with self.assertRaises(D.DesignerError) as refused:
            D.status("sesn_b000000001", client=D.Client(key=KEY, transport=api))
        self.assertEqual(str(refused.exception), "DESIGNER_UPSTREAM_400")


class Resume(unittest.TestCase):
    """Live 2026-11-28: the account's credit ran out and five pilot sessions
    stopped mid-work. A new outcome on the same session keeps its files."""

    def test_an_idle_session_gets_a_continue_outcome_within_its_own_budget(self):
        api = FakeAPI(sessions=[spent("sesn_d000000001", 369)])
        out = D.resume("sesn_d000000001", client=api.client())
        self.assertEqual(out, {"session_id": "sesn_d000000001", "status": "running", "headroom_cents": 431})
        [sent] = api.posted("/v1/sessions/sesn_d000000001/events")
        [event] = sent["events"]
        self.assertEqual(event["type"], "user.define_outcome")
        self.assertIn("Do not start over", event["description"])
        self.assertEqual(event["rubric"]["content"], D.RUBRIC)

    def test_busy_spent_foreign_or_over_the_pilot_total_is_refused(self):
        cases = ((spent("sesn_d000000001", 100, "running"), "DESIGNER_SESSION_BUSY"),
                 (spent("sesn_d000000001", 790), "DESIGNER_SESSION_BUDGET_SPENT"),
                 (dict(spent("sesn_d000000001", 100), metadata={}), "DESIGNER_NOT_FOUND"))
        for session, code in cases:
            api = FakeAPI(sessions=[session])
            with self.assertRaises(D.DesignerError) as refused:
                D.resume("sesn_d000000001", client=api.client())
            self.assertEqual(refused.exception.code, code)
            self.assertEqual(api.posted("/v1/sessions/sesn_d000000001/events"), [])
        api = FakeAPI(sessions=[spent("sesn_d000000001", 100), spent("sesn_d000000002", 3500)])
        with self.assertRaises(D.DesignerError) as refused:   # 3600 spent + 700 headroom > 4000
            D.resume("sesn_d000000001", client=api.client())
        self.assertEqual(refused.exception.code, "DESIGNER_PILOT_CAP_REACHED")


class Checks(unittest.TestCase):
    def test_every_check_module_imports_alone_as_the_sandbox_mounts_it(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for name, data in D.check_bundle():
                (Path(tmp) / name).write_bytes(data)
            names = [n[:-3] for n in D.CHECK_FILES]
            code = "import sys; sys.path.insert(0, %r); import %s" % (tmp, ", ".join(names))
            run = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=tmp)
            self.assertEqual(run.returncode, 0, run.stderr[-800:])

    def test_the_readme_names_every_module_and_the_prompt_every_output(self):
        for name in D.CHECK_FILES:
            self.assertIn(name[:-3], D.CHECKS_README)
        for out in ("program.json", "building.json", "checks.json", "plans.dxf", "plans.pdf", "model.glb",
                    "report.md", "renders/"):
            self.assertIn(out, D.SYSTEM)
            self.assertIn(out, D.RUBRIC)


class Routes(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        import acs_understand_api as API
        self.http = TestClient(API.app)

    def test_every_route_is_absent_without_a_configured_and_presented_token(self):
        token = "t" * 40
        cases = ({}, {"ACS_DESIGNER_ADMIN_TOKEN": "short"}, {"ACS_DESIGNER_ADMIN_TOKEN": token})
        for env in cases:
            with patch.dict(os.environ, env, clear=False):
                if "ACS_DESIGNER_ADMIN_TOKEN" not in env:
                    os.environ.pop("ACS_DESIGNER_ADMIN_TOKEN", None)
                headers = {"X-ACS-Admin-Token": "wrong"} if env.get("ACS_DESIGNER_ADMIN_TOKEN") == token else {}
                self.assertEqual(self.http.get("/admin/designer/sessions/sesn_b000000001", headers=headers).status_code, 404)
                self.assertEqual(self.http.post("/admin/designer/sessions", json={"brief": "فيلا"},
                                                headers=headers).status_code, 404)

    def test_a_presented_token_reaches_the_designer(self):
        token = "t" * 40
        with patch.dict(os.environ, {"ACS_DESIGNER_ADMIN_TOKEN": token}), \
                patch.object(D, "status", lambda sid: {"session_id": sid, "status": "idle"}), \
                patch.object(D, "start", side_effect=D.DesignerError("DESIGNER_PILOT_CAP_REACHED", 409)):
            ok = self.http.get("/admin/designer/sessions/sesn_b000000001", headers={"X-ACS-Admin-Token": token})
            self.assertEqual(ok.json(), {"session_id": "sesn_b000000001", "status": "idle"})
            refused = self.http.post("/admin/designer/sessions", json={"brief": "فيلا"},
                                     headers={"X-ACS-Admin-Token": token})
            self.assertEqual((refused.status_code, refused.json()), (409, {"error": {"code": "DESIGNER_PILOT_CAP_REACHED"}}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
