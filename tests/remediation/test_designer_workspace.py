"""The ACS Designer in the signed-in workspace: start, follow, save, download.

Offline: the Managed Agents API is the mock transport of test_agent_designer,
the jobs table is the PostgREST stand-in of test_workspace_job_lifecycle, and
the revision store is SQLite. The fixture is the villa the pilot designed on
2026-11-28 (tests/remediation/fixtures/designer/villa_pilot.building).
"""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import acs_agent_designer as D  # noqa: E402
import acs_designer_workspace as DW  # noqa: E402
import acs_workspace_service as S  # noqa: E402
from acs_plan_store import SQLitePlanStore  # noqa: E402
from acs_plan_store_port import SQLitePlanStoreAdapter  # noqa: E402
from test_agent_designer import FakeAPI, KEY  # noqa: E402
from test_workspace_job_lifecycle import ACTOR, PROJECT, Allow, JobsTable, Workspace, authorize, call  # noqa: E402
import acs_workspace_http as H  # noqa: E402

VILLA = (HERE / "fixtures" / "designer" / "villa_pilot.building").read_bytes()
JOB = "55555555-5555-4555-8555-555555555555"


class DesignerAPI(FakeAPI):
    """FakeAPI whose session files carry real contents."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.contents = {}

    def __call__(self, request):
        if request.url.path.startswith("/v1/files/") and request.url.path.endswith("/content"):
            fid = request.url.path.split("/")[3]
            if fid in self.contents:
                self.sent.append(request)
                return httpx.Response(200, content=self.contents[fid])
        return super().__call__(request)

    def finish(self, sid, result="satisfied", building=VILLA):
        self.sessions[sid].update(status="idle", outcome_evaluations=[{"result": result, "iteration": 0}])
        self.files[sid] = [{"id": "file_bld0000001", "filename": "building.json", "size_bytes": len(building)},
                           {"id": "file_pdf0000001", "filename": "plans.pdf", "size_bytes": 14},
                           {"id": "file_chk0000001", "filename": "acs_validate.py", "size_bytes": 10},
                           {"id": "file_scr0000001", "filename": "design.py", "size_bytes": 10}]
        self.contents["file_bld0000001"] = building


class Normalise(unittest.TestCase):
    def test_the_pilot_villa_becomes_approvable_once_normalised(self):
        raw = json.loads(VILLA)
        cores = [r for f in raw["floors"].values() for r in f["rooms"] if r["role"] in ("stairs", "elevator")]
        self.assertTrue(cores and not any(r.get("core_id") for r in cores), "the pilot drew cores without ids")
        building = D.normalise_building(copy.deepcopy(raw))
        ids = {(r["role"], r["core_id"]) for f in building["floors"].values() for r in f["rooms"]
               if r["role"] in ("stairs", "elevator")}
        self.assertEqual(ids, {("stairs", "core_stairs_1"), ("elevator", "core_lift_1")}, "one id per core, every floor")
        self.assertTrue(all("doors" in r and "windows" in r for f in building["floors"].values() for r in f["rooms"]))
        with tempfile.TemporaryDirectory() as tmp:
            db = SQLitePlanStore(Path(tmp) / "p.sqlite3")
            db.create_project(PROJECT, owner_id=ACTOR)
            store = SQLitePlanStoreAdapter(db)
            row = {"id": JOB, "expected_head": None, "resume_command": {"brief": "فيلا دورين"}}
            rid = DW.admit(store, PROJECT, ACTOR, row, building)
            review = S.workspace(store, PROJECT, ACTOR).review(rid)
            history = S.workspace(store, PROJECT, ACTOR).history()
        self.assertTrue(review["can_approve"], review.get("issues"))
        self.assertTrue(history[-1]["note"].endswith("task:" + JOB))

    def test_existing_core_ids_and_lists_are_kept(self):
        building = {"floors": {"a": {"rooms": [
            {"id": "s", "role": "stairs", "rect": [0, 0, 2, 4], "core_id": "mine", "doors": [{"edge": "N"}]},
            {"id": "o", "role": "other", "walls": "none", "rect": [2, 0, 2, 2]}]}}}
        D.normalise_building(building)
        stairs, open_area = building["floors"]["a"]["rooms"]
        self.assertEqual((stairs["core_id"], stairs["doors"], stairs["windows"]), ("mine", [{"edge": "N"}], []))
        self.assertNotIn("doors", open_area)

    def test_requirements_are_the_plot_and_the_occupied_floors(self):
        rows = D.requirements_for(json.loads(VILLA))
        self.assertEqual({r["metric"]: r["expected"] for r in rows},
                         {"site_width_m": 20, "site_depth_m": 30, "level_count": 3})
        self.assertTrue(all(r["source"] == "inferred" and r["confirmed"] for r in rows))


class Http(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        D._UPLOADED.clear()
        DW._LAST.clear()
        self.api = DesignerAPI()
        self.table = JobsTable()
        self.workspace = Workspace()
        self.limiter = Allow()
        self.middleware = H.WorkspaceMiddleware(None)
        self.admitted = []

        def admit(store, project_id, actor_id, row, building):
            self.admitted.append(building)
            return "plan_designed"
        real = D.Client
        for p in (patch.object(H.AUTH, "authorize_asgi", authorize),
                  patch.object(H.SESSION, "authenticated_supabase_plan_store", lambda scope: self.table),
                  patch.object(H.SERVICE, "workspace", lambda *a: self.workspace),
                  patch.object(H.RL, "default_limiter", lambda: self.limiter),
                  patch.object(D, "Client", lambda *a, **k: real(key=KEY, transport=httpx.MockTransport(self.api))),
                  patch.object(DW, "admit", admit),
                  patch.dict("os.environ", {"ACS_DESIGNER_USER_IDS": ACTOR})):
            p.start()
            self.addCleanup(p.stop)

    async def design(self, **extra):
        body = {"action": "design", "job_id": JOB, "brief": "فيلا دورين على أرض ٢٠×٣٠", "expected_head": None,
                "confirmed": True}
        body.update(extra)
        return await call(self.middleware, body)

    async def poll(self):
        DW._LAST.clear()
        return await call(self.middleware, {"action": "job", "job_id": JOB})

    async def test_only_beta_accounts_may_start_and_nothing_is_spent_otherwise(self):
        with patch.dict("os.environ", {"ACS_DESIGNER_USER_IDS": "someone-else"}):
            status, body = await self.design()
        self.assertEqual((status, body["error"]["code"]), (403, "DESIGNER_NOT_ENABLED"))
        self.assertEqual((self.table.rows, self.api.sent), ({}, []))
        with patch.object(H.SERVICE, "view", lambda *a: {"ok": True}):
            status, body = await call(self.middleware, {"action": "state"})
            self.assertEqual(body["designer_enabled"], True, "the beta account sees the button")
            with patch.dict("os.environ", {"ACS_DESIGNER_USER_IDS": ""}):
                status, body = await call(self.middleware, {"action": "state"})
            self.assertEqual(body["designer_enabled"], False)

    async def test_a_design_opens_one_capped_session_recorded_in_its_job(self):
        status, body = await self.design()
        self.assertEqual((status, body["job"]["state"], body["job"]["kind"]), (202, "RUNNING", "design"))
        [session] = self.api.posted("/v1/sessions")
        self.assertEqual(session["metadata"], {"acs": "designer", "project": PROJECT, "job": JOB})
        self.assertEqual(session["budget"]["max_list_cost"]["amount"], "1000")
        self.assertIn("<brief>\nفيلا دورين على أرض ٢٠×٣٠\n</brief>", session["initial_events"][0]["description"])
        row = self.table.rows[JOB]
        self.assertEqual((row["state"], row["checkpoint"]["kind"], row["resume_command"]["action"]),
                         ("RUNNING", "designer", "design"))
        self.assertTrue(row["checkpoint"]["session_id"].startswith("sesn_"))
        self.assertEqual(self.limiter.calls, ["gen"])

    async def test_polls_follow_the_session_and_save_the_design_when_it_passes(self):
        await self.design()
        sid = self.table.rows[JOB]["checkpoint"]["session_id"]
        self.api.sessions[sid]["usage"] = {"active_seconds": 610}
        self.table.rows[JOB]["created_at"] = "2020-01-01T00:00:00+00:00"   # long past any worker deadline
        status, body = await self.poll()
        self.assertEqual((body["job"]["state"], body["job"]["phase"], body["job"]["progress"]),
                         ("RUNNING", "LAYOUT", {"completed": 10, "total": 30}), "never INTERRUPTED while it runs")
        self.api.finish(sid)
        status, body = await self.poll()
        self.assertEqual((body["job"]["state"], body["job"]["revision_id"]), ("SUCCEEDED", "plan_designed"))
        [building] = self.admitted
        self.assertTrue(all(r.get("core_id") for f in building["floors"].values() for r in f["rooms"]
                            if r["role"] in ("stairs", "elevator")), "normalised before it is admitted")

    async def test_a_failed_run_fails_the_job_with_a_plain_message(self):
        await self.design()
        sid = self.table.rows[JOB]["checkpoint"]["session_id"]
        self.api.finish(sid, result="failed")
        status, body = await self.poll()
        self.assertEqual((body["job"]["state"], body["job"]["error_code"]), ("FAILED", "DESIGNER_FAILED"))
        self.assertEqual(body["job"]["error_message"], DW.message("DESIGNER_FAILED"))
        self.assertEqual(self.admitted, [])

    async def test_only_the_designs_deliverables_are_listed_and_served(self):
        await self.design()
        self.api.finish(self.table.rows[JOB]["checkpoint"]["session_id"])
        status, body = await call(self.middleware, {"action": "designer_files", "job_id": JOB})
        self.assertEqual(sorted(f["filename"] for f in body["files"]), ["building.json", "plans.pdf"])
        status, body = await call(self.middleware, {"action": "designer_file", "job_id": JOB, "file_id": "file_bld0000001"})
        self.assertEqual((status, body["name"]), (200, "building.json"))
        status, body = await call(self.middleware, {"action": "designer_file", "job_id": JOB, "file_id": "file_chk0000001"})
        self.assertEqual((status, body["error"]["code"]), (404, "REVISION_NOT_FOUND"), "ACS's own checks are not a deliverable")

    async def test_the_daily_cap_refuses_before_any_session_is_opened(self):
        with patch.dict("os.environ", {"ACS_DESIGNER_DAILY_CAP_CENTS": "500"}):
            status, body = await self.design()
        self.assertEqual(body["job"]["state"] if "job" in body else body["error"]["code"], "DESIGNER_DAILY_CAP_REACHED")
        self.assertEqual(self.api.posted("/v1/sessions"), [])
        self.assertEqual(self.table.rows[JOB]["state"], "FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
