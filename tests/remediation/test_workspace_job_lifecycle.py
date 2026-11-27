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
        self.fail_kept = 0

    def _request(self, method, path, payload=None, **kwargs):
        job_id = path.rsplit("id=eq.", 1)[-1]
        with self.lock:
            if method == "GET":
                if "&id=eq." not in path:   # generated-version listing
                    wanted = [r for r in self.rows.values() if r.get("error_code") == "GENERATION_CONFLICT"
                              and r.get("state") == "FAILED"]
                    wanted.sort(key=lambda r: r.get("created_at", ""), reverse=True)
                    return [{k: r.get(k) for k in ("id", "created_at", "expected_head")} for r in wanted][:5]
                return [copy.deepcopy(self.rows[job_id])] if job_id in self.rows else []
            if method == "POST":
                if payload["id"] in self.rows:
                    return []
                self.rows[payload["id"]] = dict(copy.deepcopy(payload), provider_calls=payload.get("provider_calls", 0),
                                                created_at=datetime.now(timezone.utc).isoformat())
                return [copy.deepcopy(self.rows[payload["id"]])]
            if method == "PATCH":
                if self.fail_kept and (payload.get("checkpoint") or {}).get("kind") == "generated_version":
                    self.fail_kept -= 1
                    raise PlanError("STORE_UNAVAILABLE", "Supabase plan store is unavailable")
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
        # A workspace job has its own (longer) deadline than one HTTP request.
        deadline = max(JOBS.DEFAULT_TIMEOUT_S, JOBS.WORKSPACE_JOB_TIMEOUT_S) + H.ORPHAN_GRACE_S
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


class ChatEditAccounting(Harness):
    """Chat edits ran without the progress channel: provider_calls stayed 0."""

    async def test_chat_edit_provider_calls_reach_the_receipt(self):
        self.workspace = Workspace("plan_head")
        seen = []

        def chat(store, project_id, actor_id, cmd, *, on_progress=None):
            seen.append(on_progress is not None)
            if on_progress:
                on_progress({"phase": "UNDERSTANDING", "provider_calls": 1})
            return "plan_edited"
        payload = {"action": "chat_edit", "job_id": JOB, "expected_head": "plan_head",
                   "notes": [{"text": "وسّع الغرفة"}], "confirmed": True, "max_provider_calls": 3}
        with patch.object(H.SERVICE, "chat_and_save", chat):
            status, body = await call(self.middleware, payload)
            self.assertEqual(status, 202, body)
            await asyncio.gather(*list(self.middleware.tasks))
        row = self.table.rows[JOB]
        self.assertEqual(seen, [True])
        self.assertEqual((row["state"], row["provider_calls"]), ("SUCCEEDED", 1))
        self.assertEqual(self.limiter.calls, ["edit"])


class OnePaidJobPerProject(Harness):
    """Two tabs (or two resumes of one failed job) each paid the provider; only
    one could ever pass the head compare-and-swap."""

    def setUp(self):
        super().setUp()
        self.gate = asyncio.Event()
        self.started = []

        async def finish(store, project_id, actor_id, cmd):
            self.started.append(cmd["job_id"])
            await self.gate.wait()
        p = patch.object(self.middleware, "_finish", finish)
        p.start()
        self.addCleanup(p.stop)

    async def drain(self):
        self.gate.set()
        await asyncio.gather(*list(self.middleware.tasks))
        self.assertEqual(H.ACTIVE_PROJECTS, {})

    async def test_concurrent_jobs_with_different_ids_admit_only_one(self):
        first, second = await asyncio.gather(call(self.middleware, command()),
                                             call(self.middleware, dict(command(), job_id=OTHER)))
        statuses = sorted([first[0], second[0]])
        self.assertEqual(statuses, [202, 409])
        refused = first[1] if first[0] == 409 else second[1]
        self.assertEqual(refused["error"]["code"], "GENERATION_IN_PROGRESS")
        self.assertEqual(len(self.started), 1)
        self.assertEqual(len(self.table.rows), 1)
        self.assertEqual(len(self.limiter.calls), 1)          # the refused tab spent no quota
        await self.drain()
        status, _ = await call(self.middleware, dict(command(), job_id=OTHER))
        self.assertEqual(status, 202)                          # free again once the job ended
        await self.drain()

    async def test_same_job_id_resubmitted_still_reattaches(self):
        first, second = await asyncio.gather(call(self.middleware, command()), call(self.middleware, command()))
        self.assertEqual((first[0], second[0]), (202, 202))
        self.assertEqual(first[1]["job"]["id"], second[1]["job"]["id"])
        self.assertEqual(self.started, [JOB])
        await self.drain()

    async def test_failed_admission_releases_the_project(self):
        self.workspace = Workspace("someone-else-saved")      # stale tab: refused before any spend
        status, body = await call(self.middleware, command())
        self.assertEqual((status, body["error"]["code"]), (409, "STALE_REVISION"))
        self.assertEqual(H.ACTIVE_PROJECTS, {})
        self.workspace = Workspace()
        self.assertEqual((await call(self.middleware, command()))[0], 202)
        await self.drain()

    async def test_non_member_can_neither_probe_nor_hold_the_reservation(self):
        self.assertEqual((await call(self.middleware, command()))[0], 202)     # member's job running

        def denied(*a):
            raise PlanError("PROJECT_ACCESS_DENIED", "Authenticated actor lacks project access")
        with patch.object(H.SERVICE, "workspace", denied):
            status, body = await call(self.middleware, dict(command(), job_id=OTHER))
        self.assertEqual((status, body["error"]["code"]), (403, "PROJECT_ACCESS_DENIED"))
        self.assertEqual(H.ACTIVE_PROJECTS, {PROJECT: JOB})
        await self.drain()

    async def test_resuming_one_failed_job_twice_admits_one(self):
        old = "55555555-5555-4555-8555-555555555555"
        self.table.rows[old] = {"id": old, "project_id": PROJECT, "created_by": ACTOR, "state": "FAILED",
                                "error_code": "PLAN_LAYOUT_INCOMPLETE", "checkpoint": {"kind": "start"},
                                "provider_calls": 1, "resume_command": command(), "input_hash": "0" * 64}
        resume = lambda job: {"action": "resume", "job_id": job, "resume_job_id": old,
                              "confirmed": True, "max_provider_calls": 3}
        first, second = await asyncio.gather(call(self.middleware, resume(JOB)), call(self.middleware, resume(OTHER)))
        self.assertEqual(sorted([first[0], second[0]]), [202, 409])
        self.assertEqual(len(self.started), 1)
        await self.drain()


class GeneratedVersionChoice(unittest.IsolatedAsyncioTestCase):
    """A manual edit saved while a paid generation runs used to void the paid
    result (STALE_REVISION, raw code). It is now kept as a separate generated
    version; the owner chooses; nothing is paid twice and nothing is lost."""

    def setUp(self):
        import tempfile
        from acs_plan_store import SQLitePlanStore
        from acs_plan_store_port import SQLitePlanStoreAdapter
        from test_connected_workspace import model
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db = SQLitePlanStore(Path(self.temp.name) / "plans.sqlite3")
        db.create_project(PROJECT, owner_id=ACTOR)
        table = JobsTable()

        class Store(SQLitePlanStoreAdapter):
            def _request(inner, *a, **k):
                return table._request(*a, **k)
        self.store, self.table, self.limiter = Store(db), table, Allow()
        self.generated = model("warehouse")
        self.runs, self.during = [], None
        case = self

        class Runner:
            def run(inner, target, kwargs, **controls):
                case.runs.append(target)
                if case.during:
                    case.during()
                return {"building": copy.deepcopy(case.generated), "provider_calls": 1}
        self.middleware = H.WorkspaceMiddleware(None)
        for p in (patch.object(H.AUTH, "authorize_asgi", authorize),
                  patch.object(H.SESSION, "authenticated_supabase_plan_store", lambda scope: self.store),
                  patch.object(H.RL, "default_limiter", lambda: self.limiter),
                  patch.object(JOBS, "default_runner", lambda: Runner())):
            p.start()
            self.addCleanup(p.stop)

    def head(self):
        return H.SERVICE.workspace(self.store, PROJECT, ACTOR).head

    def history(self):
        return [r["revision_id"] for r in H.SERVICE.workspace(self.store, PROJECT, ACTOR).history()]

    async def job(self, payload):
        status, body = await call(self.middleware, payload)
        self.assertEqual(status, 202, body)
        await asyncio.gather(*list(self.middleware.tasks))

    async def poll(self, job=JOB):
        status, body = await call(self.middleware, {"action": "job", "job_id": job})
        self.assertEqual(status, 200, body)
        return body["job"]

    def manual_edit(self, rect):
        head = self.head()
        H.SERVICE.edit_geometry(self.store, PROJECT, ACTOR, {"action": "edit_geometry", "expected_head": head,
                                                             "room_ref": ["ground", "a"], "rect": rect})

    async def conflict(self):
        await self.job(dict(command(), job_id=OTHER))                  # first version (head R1)
        base = self.head()
        self.during = lambda: self.manual_edit([0, 0, 7, 7])           # other tab, while paid job runs
        await self.job(dict(command(), expected_head=base))
        self.during = None
        return base

    async def test_conflict_keeps_the_generated_version_and_the_manual_edit_stays_head(self):
        base = await self.conflict()
        manual = self.head()
        self.assertNotEqual(manual, base)
        row = self.table.rows[JOB]
        self.assertEqual((row["state"], row["error_code"]), ("FAILED", "GENERATION_CONFLICT"))
        self.assertEqual(row["checkpoint"]["kind"], "generated_version")
        self.assertEqual(row["checkpoint"]["current_head"], manual)
        job = await self.poll()
        self.assertEqual(job["choice"]["options"], ["keep_edit", "use_generated"])
        self.assertIsNone(job["choice"]["adopted_revision_id"])
        self.assertIn("النسخة المولّدة", job["error_message"])
        self.assertFalse(job["can_resume"])
        self.assertEqual(len(self.runs), 2)
        self.assertEqual(self.limiter.calls, ["gen", "gen"])

    async def test_use_generated_appends_once_without_provider_or_quota(self):
        await self.conflict()
        manual, runs, quota = self.head(), len(self.runs), list(self.limiter.calls)
        choose = {"action": "adopt_generated", "job_id": JOB, "expected_head": manual, "confirmed": True}
        first = await call(self.middleware, choose)
        again = await call(self.middleware, choose)                    # lost reply, retried
        self.assertEqual((first[0], again[0]), (200, 200), (first, again))
        adopted = first[1]["revision_id"]
        self.assertEqual(again[1]["revision_id"], adopted)
        self.assertEqual(self.head(), adopted)
        self.assertIn(manual, self.history())                          # the manual edit stays recoverable
        ws = H.SERVICE.workspace(self.store, PROJECT, ACTOR)
        rooms = {r["id"]: r["rect"] for r in ws.get(adopted).model["floors"]["ground"]["rooms"]}
        self.assertEqual(rooms["a"], [0, 0, 8, 8])                     # the generated geometry
        self.assertEqual((len(self.runs), self.limiter.calls), (runs, quota))
        job = await self.poll()
        self.assertEqual(job["choice"]["adopted_revision_id"], adopted)
        self.assertIn("يمكن استعادته", job["error_message"])

    async def test_keep_edit_leaves_the_version_recoverable_later(self):
        await self.conflict()
        status, body = await call(self.middleware, {"action": "generated_versions"})
        self.assertEqual(status, 200, body)
        self.assertEqual([(v["job_id"], v["adopted_revision_id"]) for v in body["versions"]], [(JOB, None)])
        self.manual_edit([0, 0, 6, 6])                                 # owner keeps editing
        later = self.head()
        status, body = await call(self.middleware, {"action": "adopt_generated", "job_id": JOB,
                                                    "expected_head": later, "confirmed": True})
        self.assertEqual(status, 200, body)
        self.assertIn(later, self.history())

    async def test_choice_is_bound_to_the_current_head_and_to_a_kept_version(self):
        base = await self.conflict()
        before = self.history()
        status, body = await call(self.middleware, {"action": "adopt_generated", "job_id": JOB,
                                                    "expected_head": base, "confirmed": True})
        self.assertEqual((status, body["error"]["code"]), (409, "STALE_REVISION"))
        status, body = await call(self.middleware, {"action": "adopt_generated", "job_id": OTHER,
                                                    "expected_head": self.head(), "confirmed": True})
        self.assertEqual((status, body["error"]["code"]), (404, "GENERATED_VERSION_NOT_FOUND"))
        status, body = await call(self.middleware, {"action": "adopt_generated", "job_id": JOB,
                                                    "expected_head": self.head()})
        self.assertEqual(body["error"]["code"], "EXPLICIT_CONFIRMATION_REQUIRED")
        self.assertEqual(self.history(), before)

    async def test_a_version_that_could_not_be_kept_is_never_offered(self):
        self.table.fail_kept = 1
        await self.conflict()
        row = self.table.rows[JOB]
        self.assertEqual((row["state"], row["error_code"]), ("FAILED", "STALE_REVISION"))
        job = await self.poll()
        self.assertIsNone(job["choice"])
        self.assertIn("افتح آخر نسخة", job["error_message"])          # plain Arabic, not a raw code

    async def test_room_locks_of_the_current_head_still_apply(self):
        from acs_plan_persisted_commands import execute_persisted_plan_command
        await self.conflict()
        execute_persisted_plan_command(self.store, PROJECT, {"action": "set_room_lock", "expected_head": self.head(),
                                       "room_ref": ["ground", "a"], "locked": True},
                                       actor_id=ACTOR, verifier=H.SERVICE.existing_geometry_verifier)
        locked, before = self.head(), self.history()
        status, body = await call(self.middleware, {"action": "adopt_generated", "job_id": JOB,
                                                    "expected_head": locked, "confirmed": True})
        self.assertEqual(status, 400, body)
        self.assertIn(body["error"]["code"], {"LOCK_VIOLATION", "LOCK_CONTEXT_CHANGED"})
        self.assertEqual(self.history(), before)
        self.assertIsNone((await self.poll())["choice"]["adopted_revision_id"])   # still offered


if __name__ == "__main__":
    unittest.main(verbosity=2)
