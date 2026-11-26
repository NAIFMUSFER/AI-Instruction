"""Replay of the failed review-note jobs: GENERATION_WORKER_FAILED in under a
second, phase UNDERSTANDING, provider_calls 0.

Production jobs 1b21c5d2 (project 8220892e, head plan_284e77fa…) and f598b371
(project 1d78c484, head plan_98ccb56d…) sent one plan-review note back to the AI.
The worker raised ValueError("invalid opening identity contract") inside
acs_understand.apply_notes, before its first model call: the saved plans repeat
opening IDs (stair-template variants copy their source template's doors and
windows; plan_284e77fa also gives both faces of each door one ID), revision
admission accepts that, but the chat worker demanded globally unique IDs. The
job runner turned the unclassified ValueError into JobError, and the log said
only error_class=JobError.

Offline: temporary SQLite store, no Supabase, no provider. The model call is
stubbed; a notes job must reach it without a live model. The fixtures are the
stored models with free text replaced (see each fixture's "about").
"""
from __future__ import annotations

import asyncio
from collections import Counter
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_api_errors as E
import acs_generation_job as JOBS
import acs_understand as U
import acs_validate as V
import acs_workspace_http as H
import acs_workspace_service as S
from acs_opening_identity import inherited_collisions, opening_identity_issues
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_store_reload import load_workspace

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "notes_job"
CASES = ("job_1b21c5d2", "job_f598b371")
PROJECT = "11111111-1111-4111-8111-111111111111"
ACTOR = "22222222-2222-4222-8222-222222222222"
MARK = "\n\nالنموذج الحالي:\n"


def fixture(name):
    return json.loads((FIXTURES / (name + ".json")).read_text(encoding="utf-8"))


def opening_ids(model):
    return Counter(op.get("id") for floor in model["floors"].values() for room in floor["rooms"]
                   for key in ("doors", "windows") for op in room.get(key) or [])


def provider(calls, change=None):
    """Stands in for the model: returns the building it was shown, optionally changed."""
    def call(prompt, *args, **kwargs):
        calls.append(prompt)
        building = json.loads(prompt[prompt.index(MARK) + len(MARK):])
        if change:
            change(building)
        return json.dumps(building, ensure_ascii=False)
    return call


class StoredPlans(unittest.TestCase):
    def test_saved_plans_repeat_opening_ids_and_nothing_else(self):
        for name in CASES:
            with self.subTest(name=name):
                model = fixture(name)["model"]
                codes = {i["code"] for i in opening_identity_issues(model)}
                self.assertEqual(codes, {"ID_COLLISION"})
                variants = [l["template"] for l in model["levels"] if l.get("stair_source_template")]
                self.assertEqual(len(variants), 2, "two stair-template variants copy the ground template")
                self.assertTrue(all(count >= 3 for count in inherited_collisions(model).values()))
        faces = Counter(op["id"] for room in fixture("job_1b21c5d2")["model"]["floors"]["residential_2"]["rooms"]
                        for op in room.get("doors") or [])
        self.assertEqual(faces["a1_bed1_corr_door"], 2, "one ID on both faces of a door")

    def test_review_never_asks_to_split_the_automatic_roof(self):
        for name in CASES:
            with self.subTest(name=name):
                model = fixture(name)["model"]
                roof = [l["template"] for l in model["levels"] if l.get("kind") == "roof"]
                self.assertEqual(roof, ["roof"])
                issues, _ = V.validate_building(model)
                self.assertFalse([i for i in issues if i.startswith("[roof/") and "حيّز عام" in i], issues)
                # These roof notes were the plans' only findings, and any finding
                # fails both scopes: a roof false positive read as a stair problem
                # and blocked concept approval.
                evidence = S.existing_geometry_verifier(model)
                self.assertEqual(evidence["issues"], [])
                self.assertEqual(evidence["scopes"], {"topology": "PASS", "vertical_circulation": "PASS"})

    def test_a_generic_apartment_space_is_still_flagged(self):
        model = fixture("job_1b21c5d2")["model"]
        model["floors"]["residential_2"]["rooms"].append(
            {"id": "apt_a", "rect": [0, 0, 6.7, 9.5], "walls": "all", "doors": [], "windows": [], "points": []})
        issues, _ = V.validate_building(model)
        self.assertTrue([i for i in issues if i.startswith("[residential_2/apt_a]") and "حيّز عام" in i])
        # The exemption is the unoccupied roof (template and role), not the
        # "roof_" id: the same rooms on an occupied storey with no role are flagged.
        model["levels"][-1].pop("kind")
        for room in model["floors"]["roof"]["rooms"]:
            room.pop("role")
        issues, _ = V.validate_building(model)
        self.assertTrue([i for i in issues if i.startswith("[roof/roof_residential_2_apartment_1_bedroom_1]")
                         and "حيّز عام" in i])


class NotesJobReplay(unittest.TestCase):
    def setUp(self):
        self.fresh_store()

    def fresh_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = SQLitePlanStore(Path(tmp.name) / "plans.sqlite3")
        db.create_project(PROJECT, owner_id=ACTOR)
        self.store = SQLitePlanStoreAdapter(db)

    def seed(self, case):
        ws = load_workspace(self.store, PROJECT, actor_id=ACTOR, verifier=S.existing_geometry_verifier)
        ws.propose(case["model"], brief=case["brief"], requirements=case["requirements"],
                   expected_head=None, note="replay fixture")
        self.store.save_revision(PROJECT, actor_id=ACTOR, revision=ws.get(ws.head), expected_head=None)
        head = ws.head
        if case["semantic_locks"]:   # f598b371's head was a whole-door lock on a stair variant
            head = execute_persisted_plan_command(self.store, PROJECT, {
                "action": "replace_semantic_locks", "expected_head": head,
                "selectors": case["semantic_locks"], "note": "lock whole element from connected design review",
            }, actor_id=ACTOR, verifier=S.existing_geometry_verifier)["head"]
        return head

    def run_job(self, case, head, reply):
        command = dict(copy.deepcopy(case["command"]), expected_head=head)
        runner = JOBS.JobRunner(executor="thread")   # same _unpack_err/JobError path as a process
        with patch("acs_generation_job.default_runner", return_value=runner), \
                patch.object(U, "call_llm", side_effect=reply):
            return S.chat_and_save(self.store, PROJECT, ACTOR, command)

    def revisions(self):
        return self.store.workspace_snapshot(PROJECT, actor_id=ACTOR)["revisions"]

    def test_the_failed_notes_jobs_reach_the_model_and_save_a_revision(self):
        for name in CASES:
            with self.subTest(name=name):
                self.fresh_store()
                case = fixture(name)
                head = self.seed(case)
                calls = []
                saved = self.run_job(case, head, provider(calls))
                self.assertEqual(len(calls), 1, "exactly one model call, reached without a live model")
                self.assertIn(case["command"]["notes"][0]["text"], calls[0])
                docs = self.revisions()
                self.assertEqual((docs[-1]["revision_id"], docs[-1]["parent_id"]), (saved, head))
                # The edit keeps every saved opening ID, repeats included.
                self.assertEqual(opening_ids(docs[-1]["model"]), opening_ids(case["model"]))
                self.assertEqual(docs[-1]["semantic_lock_count"], len(case["semantic_locks"]))

    def test_the_reply_may_not_add_a_repeated_opening_id(self):
        case = fixture("job_1b21c5d2")
        head = self.seed(case)
        before = self.revisions()

        def copy_a_door(building):
            rooms = building["floors"]["residential_2"]["rooms"]
            kitchen = next(r for r in rooms if r["id"] == "residential_2_apartment_1_kitchen_1")
            kitchen["doors"].append(dict(kitchen["doors"][0], offset=1.0))
        with self.assertRaises(E.AcsApiError) as caught:
            self.run_job(case, head, provider([], copy_a_door))
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_INVALID_JSON)
        self.assertEqual(self.revisions(), before)

    def test_a_plan_with_an_invalid_opening_id_fails_classified_before_the_model(self):
        case = fixture("job_1b21c5d2")
        model = copy.deepcopy(case["model"])
        model["floors"]["residential_2"]["rooms"][0]["doors"][0].pop("id")   # marker present: no repair
        calls = []
        with patch.object(U, "call_llm", side_effect=provider(calls)), self.assertRaises(PlanError) as caught:
            S.budgeted_chat_candidate(model, case["command"]["notes"], 3)
        self.assertEqual(caught.exception.code, "OPENING_IDENTITY_INVALID")
        self.assertEqual(calls, [])
        self.assertTrue(S.geometry_failure_message("OPENING_IDENTITY_INVALID"))


class WorkerFailureLog(unittest.TestCase):
    """The production log said error_class=JobError and nothing else."""

    def test_job_error_carries_the_worker_class_and_position(self):
        for executor in ("thread", "process"):
            with self.subTest(executor=executor):
                runner = JOBS.JobRunner(capacity=1, executor=executor, start_method="spawn")
                with self.assertRaises(JOBS.JobError) as caught:
                    runner.run("acs_generation_job:_boom", {"message": "invalid opening identity contract"})
                exc = caught.exception
                self.assertEqual(exc.error_class, "RuntimeError")
                self.assertRegex(exc.error_at or "", r"^acs_generation_job\.py:\d+$")
                self.assertEqual(exc.safe_message, "invalid opening identity contract")

    def test_messages_that_may_hold_user_text_are_withheld(self):
        for text in ("غرفة بلا rect صحيح", "'bedroom'", "room residential_2_apartment_1 failed",
                     "sk-" + "ant-api03-secret", "sk-" + "ant-abcdefghijklmnopqrstuvwxyz", "line one\nline two"):
            with self.subTest(text=text):
                self.assertIsNone(JOBS.JobError(text, "ValueError").safe_message)

    def test_workspace_log_names_the_worker_failure(self):
        class Jobs:
            def __init__(self):
                self.patches = []

            def _request(self, method, path, payload=None, **kwargs):
                self.patches.append(payload)

        note = "عالج الملاحظة التالية: [roof/roof_residential_2_apartment_1_bedroom_1]"
        command = {"action": "chat_edit", "job_id": "1b21c5d2-b41c-4694-9e90-9166c7d8230c",
                   "expected_head": "plan_head", "notes": [{"text": note}],
                   "confirmed": True, "max_provider_calls": 3}

        def failing(*args, **kwargs):
            raise JOBS.JobError("invalid opening identity contract", "ValueError",
                                "acs_opening_identity.py:76")
        stream, jobs = io.StringIO(), Jobs()
        with patch.object(H.SERVICE, "chat_and_save", failing), patch.object(H.LOG, "_stream", stream):
            asyncio.run(H.WorkspaceMiddleware(None)._finish(jobs, PROJECT, ACTOR, command))
        record = next(json.loads(line) for line in stream.getvalue().splitlines()
                      if json.loads(line)["event"] == "workspace_worker_failed")
        self.assertEqual((record["error_class"], record["error_code"]), ("JobError", "GENERATION_WORKER_FAILED"))
        self.assertEqual((record["worker_error_class"], record["worker_error_at"], record["worker_error_message"]),
                         ("ValueError", "acs_opening_identity.py:76", "invalid opening identity contract"))
        self.assertNotIn("roof_residential", stream.getvalue())
        self.assertEqual(jobs.patches[-1]["error_code"], "GENERATION_WORKER_FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
