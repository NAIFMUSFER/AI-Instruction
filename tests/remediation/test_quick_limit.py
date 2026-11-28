"""The quick generator's call cap: no dead-end resume, and the way to the designer.

The owner's warehouse brief (24 zones) used its 8 calls and placed 8 zones.
Its «استئناف» then failed at once: the cap counts the calls already used, and
a quick generation may use at most 12. Now a job that cannot finish under the
cap offers no resume and says why (the page then offers the full designer),
and a resume adds the calls the owner chooses on top of those already used.
"""
import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import acs_workspace_http as H  # noqa: E402
from test_connected_workspace import command  # noqa: E402
from test_workspace_job_lifecycle import ACTOR, PROJECT, Harness, call  # noqa: E402

OLD = "66666666-6666-4666-8666-666666666666"
NEW = "77777777-7777-4777-8777-777777777777"
OUTLINE = {"kind": "outline", "zones": [], "envelope": {}, "issues": [], "results": [], "pending": [],
           "rate": None, "index": 7}
ZONES = [{"id": "zone_%02d" % n, "role": "storage", "order": n, "template": "t%d" % n} for n in range(24)]
WAREHOUSE = dict(OUTLINE, zones=ZONES, pending=ZONES[8:])      # as saved: 24 zones, 16 still to place


class QuickLimit(Harness):
    def setUp(self):
        super().setUp()
        self.started = []

        async def finish(store, project_id, actor_id, cmd):
            self.started.append(cmd)
        p = patch.object(self.middleware, "_finish", finish)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(H.ACTIVE_PROJECTS.clear)

    def failed(self, *, code="ACS_PROVIDER_BUDGET_EXHAUSTED", calls, progress=None, checkpoint=OUTLINE):
        self.table.rows[OLD] = {"id": OLD, "project_id": PROJECT, "created_by": ACTOR, "state": "FAILED",
                                "error_code": code, "checkpoint": checkpoint, "provider_calls": calls,
                                "progress": progress, "phase": "LAYOUT", "resume_command": command(),
                                "input_hash": "0" * 64}

    async def resume(self, extra):
        return await call(self.middleware, {"action": "resume", "job_id": NEW, "resume_job_id": OLD,
                                            "confirmed": True, "max_provider_calls": extra})

    async def test_the_owners_warehouse_offers_no_resume_that_could_never_finish(self):
        self.failed(calls=8, progress={"total": 24, "completed": 8}, checkpoint=WAREHOUSE)
        self.assertEqual(H._calls_to_finish(self.table.rows[OLD]), 15, "16 zones at 8 per 7 calls, then openings")
        job = await self.poll(OLD)
        self.assertEqual((job["can_resume"], job["beyond_quick"], job["error_message"]),
                         (False, True, H.BEYOND_QUICK_MESSAGE))
        status, body = await self.resume(4)
        self.assertEqual((status >= 400, body["error"]["code"]), (True, "INVALID_RESUME"))
        self.assertIn("أكبر مما يرسمه التوليد السريع", body["error"]["message"])
        self.assertEqual((sorted(self.table.rows), self.started), ([OLD], []), "nothing written, nothing paid")

    async def test_its_failed_resume_without_progress_is_read_from_the_saved_layout(self):
        self.failed(calls=8, progress=None, checkpoint=WAREHOUSE)
        job = await self.poll(OLD)
        self.assertEqual((job["can_resume"], job["beyond_quick"]), (False, True))

    async def test_a_job_that_used_every_call_is_beyond_the_quick_generator(self):
        self.failed(calls=12, checkpoint={"kind": "start"})
        self.assertEqual((await self.poll(OLD))["beyond_quick"], True)

    async def test_a_small_layout_that_ran_out_still_resumes_with_more_calls(self):
        self.failed(calls=5, progress={"total": 6, "completed": 4})
        job = await self.poll(OLD)
        self.assertEqual((job["can_resume"], "beyond_quick" in job), (True, False), "5 used + 3 needed fit in 12")
        status, body = await self.resume(4)
        await asyncio.gather(*list(self.middleware.tasks))
        self.assertEqual(status, 202, body)
        [resumed] = self.started
        self.assertEqual((resumed["max_provider_calls"], resumed["resume_job_id"]), (9, OLD),
                         "the 4 calls chosen come on top of the 5 already used")

    async def test_a_resume_never_passes_the_cap(self):
        self.failed(code="PLAN_LAYOUT_INCOMPLETE", calls=5, checkpoint={"kind": "start"})
        status, body = await self.resume(12)
        await asyncio.gather(*list(self.middleware.tasks))
        self.assertEqual((status, self.started[0]["max_provider_calls"]), (202, 12))

    async def test_an_invalid_number_of_extra_calls_is_refused_before_anything_starts(self):
        self.failed(code="PLAN_LAYOUT_INCOMPLETE", calls=2, checkpoint={"kind": "start"})
        for extra in (0, 13, "4", 2.0):
            status, body = await self.resume(extra)
            self.assertEqual(body["error"]["code"], "INVALID_BUDGET", extra)
        self.assertEqual((sorted(self.table.rows), self.started), ([OLD], []))

    def test_unknown_progress_says_nothing_about_the_calls_left(self):
        for row in ({"checkpoint": {"kind": "start"}, "progress": {"total": 24, "completed": 8}, "provider_calls": 8},
                    {"checkpoint": OUTLINE, "progress": None, "provider_calls": 8},
                    {"checkpoint": OUTLINE, "progress": {"total": 24, "completed": 0}, "provider_calls": 8},
                    {"checkpoint": OUTLINE, "progress": {"total": 24, "completed": 8}, "provider_calls": 1}):
            self.assertIsNone(H._calls_to_finish(row), row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
