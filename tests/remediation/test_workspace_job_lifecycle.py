"""Workspace job lifecycle: one request, one terminal state, one charge record.

Synthetic stores only: no identity provider, no Supabase, no model provider.
Each test names the production failure it reproduces.
"""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_generation_job as JOBS
import acs_workspace_http as H
from acs_plan_review import PlanError
from test_connected_workspace import ACTOR, PROJECT, command

JOB = "33333333-3333-4333-8333-333333333333"
OTHER = "44444444-4444-4444-8444-444444444444"


class JobsTable:
    """acs_workspace_jobs as PostgREST + RLS expose it to the job owner."""

    def __init__(self):
        self.rows, self.lock = {}, threading.Lock()
        self.fail_progress = 0

    def _request(self, method, path, payload=None, **kwargs):
        job_id = path.rsplit("id=eq.", 1)[-1]
        with self.lock:
            if method == "GET":
                return [copy.deepcopy(self.rows[job_id])] if job_id in self.rows else []
            if method == "POST":
                if payload["id"] in self.rows:
                    return []
                self.rows[payload["id"]] = dict(copy.deepcopy(payload), provider_calls=payload.get("provider_calls", 0),
                                                created_at=datetime.now(timezone.utc).isoformat())
                return [copy.deepcopy(self.rows[payload["id"]])]
            if method == "PATCH":
                if "phase" in payload and self.fail_progress:
                    self.fail_progress -= 1
                    raise PlanError("STORE_UNAVAILABLE", "Supabase plan store is unavailable")
                row = self.rows.get(job_id)
                if row is not None and row["state"] == "RUNNING":   # RLS: only RUNNING rows update
                    row.update(copy.deepcopy(payload))
                return None
        raise AssertionError(method)


class Workspace:
    def __init__(self, head=None, history=()):
        self.head, self._history = head, list(history)

    def history(self):
        return list(self._history)


async def call(middleware, payload):
    scope = {"type": "http", "path": "/v1/projects/%s/workspace" % PROJECT, "method": "POST",
             "headers": [], "state": {}, "client": ("127.0.0.1", 1)}
    events = []

    async def receive():
        return {"type": "http.request", "body": json.dumps(payload).encode(), "more_body": False}

    async def send(message):
        events.append(message)

    await middleware(scope, receive, send)
    return events[0]["status"], json.loads(events[1]["body"])


async def authorize(scope, send):
    scope["state"]["authenticated_user_id"] = ACTOR
    return True


class Allow:
    def __init__(self):
        self.calls = []

    def check(self, identity, kind="gen", now=None):
        self.calls.append(kind)
        return {"allowed": True}


class Harness(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.table = JobsTable()
        self.workspace = Workspace()
        self.limiter = Allow()
        self.middleware = H.WorkspaceMiddleware(None)
        for p in (patch.object(H.AUTH, "authorize_asgi", authorize),
                  patch.object(H.SESSION, "authenticated_supabase_plan_store", lambda scope: self.table),
                  patch.object(H.SERVICE, "workspace", lambda *a: self.workspace),
                  patch.object(H.RL, "default_limiter", lambda: self.limiter)):
            p.start()
            self.addCleanup(p.stop)

    def running(self, *, age_s, worker=None, job=JOB):
        created = datetime.now(timezone.utc) - timedelta(seconds=age_s)
        self.table.rows[job] = {"id": job, "project_id": PROJECT, "created_by": ACTOR, "state": "RUNNING",
                                "worker_id": worker or "00000000-0000-4000-8000-0000000000aa",
                                "input_hash": "0" * 64, "phase": "LAYOUT", "provider_calls": 2,
                                "created_at": created.isoformat()}

    async def poll(self, job=JOB):
        status, body = await call(self.middleware, {"action": "job", "job_id": job})
        self.assertEqual(status, 200, body)
        return body["job"]


class OrphanedReceipts(Harness):
    """Deploy/OOM/crash, or a lost terminal write, used to leave RUNNING forever."""

    async def test_dead_process_receipt_becomes_interrupted_after_the_worker_deadline(self):
        deadline = JOBS.DEFAULT_TIMEOUT_S + H.ORPHAN_GRACE_S
        self.running(age_s=deadline - 30)          # another process may still be finishing it
        self.assertEqual((await self.poll())["state"], "RUNNING")
        self.running(age_s=deadline + 30)          # nobody can still write its receipt
        job = await self.poll()
        self.assertEqual(job["state"], "INTERRUPTED")
        self.assertEqual(job["error_code"], "PROVIDER_OUTCOME_UNKNOWN")
        self.assertIn("لا يمكن الجزم", job["error_message"])
        self.assertFalse(job["can_resume"])
        self.assertEqual(job["provider_calls"], 2)
        self.assertEqual(self.table.rows[JOB]["state"], "RUNNING")   # read-only: nothing rewritten
        self.assertEqual(self.limiter.calls, [])                       # and nothing resubmitted

    async def test_own_finished_task_without_receipt_is_interrupted_but_live_task_is_not(self):
        self.running(age_s=H.OWN_ORPHAN_AFTER_S + 5, worker=H.WORKER_ID)
        H.ACTIVE_JOBS.add(JOB)
        try:
            self.assertEqual((await self.poll())["state"], "RUNNING")
        finally:
            H.ACTIVE_JOBS.discard(JOB)
        self.assertEqual((await self.poll())["state"], "INTERRUPTED")

    async def test_saved_revision_marker_still_wins_over_interruption(self):
        self.running(age_s=JOBS.DEFAULT_TIMEOUT_S + H.ORPHAN_GRACE_S + 30)
        self.workspace = Workspace("plan_saved", [{"revision_id": "plan_saved", "note": "البديل A · task:" + JOB}])
        job = await self.poll()
        self.assertEqual((job["state"], job["revision_id"]), ("SUCCEEDED", "plan_saved"))

    async def test_receipt_without_start_time_keeps_previous_behaviour(self):
        self.running(age_s=10 ** 6)
        del self.table.rows[JOB]["created_at"]
        self.assertEqual((await self.poll())["state"], "RUNNING")


class ProgressReceipts(Harness):
    """A progress PATCH is advisory; losing one must not discard paid work."""

    async def run_job(self, execute, payload=None):
        with patch.object(H.SERVICE, "generate_and_save", execute), patch.object(H.SERVICE, "chat_and_save", execute):
            status, body = await call(self.middleware, payload or command())
            self.assertEqual(status, 202, body)
            await asyncio.gather(*list(self.middleware.tasks))
        return self.table.rows[(payload or command())["job_id"]]

    async def test_transient_progress_failure_after_a_paid_request_keeps_the_result(self):
        self.table.fail_progress = 1

        def execute(store, project_id, actor_id, cmd, *, on_progress):
            on_progress({"phase": "UNDERSTANDING", "provider_calls": 1})   # this write is lost
            on_progress({"phase": "LAYOUT", "provider_calls": 2})
            return "plan_saved"
        row = await self.run_job(execute)
        self.assertEqual((row["state"], row["revision_id"]), ("SUCCEEDED", "plan_saved"))
        self.assertEqual(row["provider_calls"], 2)

    async def test_terminal_receipt_keeps_the_last_count_when_the_last_progress_write_is_lost(self):
        def execute(store, project_id, actor_id, cmd, *, on_progress):
            on_progress({"phase": "UNDERSTANDING", "provider_calls": 1})
            self.table.fail_progress = 1
            on_progress({"phase": "REVIEW", "provider_calls": 3})          # lost
            raise PlanError("PLAN_GEOMETRY_ROOM_OVERLAP", "synthetic")
        row = await self.run_job(execute)
        self.assertEqual((row["state"], row["error_code"], row["provider_calls"]),
                         ("FAILED", "PLAN_GEOMETRY_ROOM_OVERLAP", 3))

    async def test_authorization_failure_still_stops_the_job(self):
        def denied(*a, **k):
            raise PlanError("PROJECT_ACCESS_DENIED", "Authenticated actor lacks project access")
        reached = []

        def execute(store, project_id, actor_id, cmd, *, on_progress):
            with patch.object(self.table, "_request", denied):
                on_progress({"phase": "UNDERSTANDING", "provider_calls": 1})
            reached.append(True)
            return "plan_saved"
        row = await self.run_job(execute)
        self.assertEqual(reached, [])
        self.assertEqual((row["state"], row["error_code"]), ("FAILED", "PROJECT_ACCESS_DENIED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
