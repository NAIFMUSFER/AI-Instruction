"""Audit P0-3 in the server: two instances never run two paid jobs for one project.

The database refuses a second RUNNING job of a project
(supabase/migrations/20261128180000_acs_one_running_job_per_project.sql, proven
on PostgreSQL by test_one_running_job_postgres.py). Here: the Supabase store
reports that refusal as GENERATION_IN_PROGRESS, the workspace releases a job no
worker can finish and retries once, and a second instance (its own empty
process memory) is refused before any provider request.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import acs_supabase_plan_store as STORE  # noqa: E402
import acs_workspace_http as H  # noqa: E402
from acs_plan_review import PlanError  # noqa: E402
from test_workspace_job_lifecycle import ACTOR, PROJECT, Allow, JobsTable, Workspace, authorize, call  # noqa: E402
from test_connected_workspace import command  # noqa: E402

JOB_A = "33333333-3333-4333-8333-333333333333"
JOB_B = "44444444-4444-4444-8444-444444444444"
DUPLICATE = {"code": "23505", "details": "Key (project_id)=(%s) already exists." % PROJECT, "hint": None,
             "message": 'duplicate key value violates unique constraint "acs_workspace_jobs_one_running"'}


def store(status, body):
    def transport(**kw):
        return status, json.dumps(body).encode()
    return STORE.SupabasePlanStore("https://example.supabase.co", "sb_publishable_x", "token", actor_id=ACTOR,
                                   transport=transport)


class StoreMapping(unittest.TestCase):
    def test_the_one_running_index_is_reported_as_a_project_in_progress(self):
        with self.assertRaises(PlanError) as refused:
            store(409, DUPLICATE)._request("POST", "/rest/v1/acs_workspace_jobs?on_conflict=id", {"id": JOB_A})
        self.assertEqual(refused.exception.code, "GENERATION_IN_PROGRESS")

    def test_any_other_conflict_still_fails_closed(self):
        other = dict(DUPLICATE, message='duplicate key value violates unique constraint "acs_workspace_jobs_pkey"')
        with self.assertRaises(PlanError) as refused:
            store(409, other)._request("POST", "/rest/v1/acs_workspace_jobs?on_conflict=id", {"id": JOB_A})
        self.assertEqual(refused.exception.code, "STORE_UNAVAILABLE")


class SharedJobsTable(JobsTable):
    """acs_workspace_jobs with the one-running index and the release RPC."""

    def __init__(self):
        super().__init__()
        self.released = 0
        self.stale = set()

    def _request(self, method, path, payload=None, **kwargs):
        if path == "/rest/v1/rpc/acs_release_stale_job":
            freed = 0
            for row in self.rows.values():
                if row["project_id"] == payload["p_project"] and row["state"] == "RUNNING" and row["id"] in self.stale:
                    row.update(state="FAILED", error_code="PROVIDER_OUTCOME_UNKNOWN")
                    freed += 1
            self.released += freed
            return freed
        if method == "POST" and any(r["project_id"] == payload["project_id"] and r["state"] == "RUNNING"
                                    and r["id"] != payload["id"] for r in self.rows.values()):
            raise PlanError("GENERATION_IN_PROGRESS", "Another job is already running for this project")
        return super()._request(method, path, payload, **kwargs)


class InsertJob(unittest.TestCase):
    def row(self, job):
        return {"id": job, "project_id": PROJECT, "state": "RUNNING"}

    def test_a_dead_workers_job_is_released_once_and_the_write_retried(self):
        table = SharedJobsTable()
        H._insert_job(table, PROJECT, self.row(JOB_A))
        table.stale.add(JOB_A)
        inserted = H._insert_job(table, PROJECT, self.row(JOB_B))
        self.assertEqual((inserted[0]["id"], table.released, table.rows[JOB_A]["state"]), (JOB_B, 1, "FAILED"))

    def test_a_live_job_keeps_the_project_and_says_so_in_arabic(self):
        table = SharedJobsTable()
        H._insert_job(table, PROJECT, self.row(JOB_A))
        with self.assertRaises(PlanError) as refused:
            H._insert_job(table, PROJECT, self.row(JOB_B))
        self.assertEqual(refused.exception.code, "GENERATION_IN_PROGRESS")
        self.assertIn("لم يُرسل أي طلب", str(refused.exception))
        self.assertNotIn(JOB_B, table.rows)

    def test_a_store_without_the_release_function_releases_nothing(self):
        class Old(SharedJobsTable):
            def _request(inner, method, path, payload=None, **kw):
                if path.endswith("acs_release_stale_job"):
                    raise PlanError("STORE_UNAVAILABLE", "no such function")
                return SharedJobsTable._request(inner, method, path, payload, **kw)
        table = Old()
        H._insert_job(table, PROJECT, self.row(JOB_A))
        table.stale.add(JOB_A)
        with self.assertRaises(PlanError) as refused:
            H._insert_job(table, PROJECT, self.row(JOB_B))
        self.assertEqual(refused.exception.code, "GENERATION_IN_PROGRESS")


class TwoInstances(unittest.IsolatedAsyncioTestCase):
    """Instance A runs a generation; instance B, whose process memory knows
    nothing of it, is refused by the database before any provider request."""

    async def asyncSetUp(self):
        self.table = SharedJobsTable()
        self.workspace = Workspace()
        self.started = []
        for p in (patch.object(H.AUTH, "authorize_asgi", authorize),
                  patch.object(H.SESSION, "authenticated_supabase_plan_store", lambda scope: self.table),
                  patch.object(H.SERVICE, "workspace", lambda *a: self.workspace),
                  patch.object(H.RL, "default_limiter", lambda: Allow()),
                  patch.object(H.WorkspaceMiddleware, "_finish", self.finish)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(H.ACTIVE_PROJECTS.clear)
        self.addCleanup(H.ACTIVE_JOBS.clear)

    async def finish(inner_self, store, project_id, actor_id, command):
        pass

    async def test_the_second_instance_is_refused_and_starts_no_worker(self):
        a, b = H.WorkspaceMiddleware(None), H.WorkspaceMiddleware(None)
        first = dict(command(), job_id=JOB_A)
        status, body = await call(a, first)
        self.assertEqual((status, body["job"]["state"]), (202, "RUNNING"))
        H.ACTIVE_PROJECTS.clear()          # instance B: its own, empty process memory
        H.ACTIVE_JOBS.clear()
        second = dict(command(), job_id=JOB_B)
        status, body = await call(b, second)
        self.assertEqual((status, body["error"]["code"]), (409, "GENERATION_IN_PROGRESS"))
        self.assertEqual(sorted(self.table.rows), [JOB_A], "the refused job wrote nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
