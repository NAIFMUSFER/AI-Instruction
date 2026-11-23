"""Regression for authenticated reload across separate PostgREST read transactions."""
import copy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import revision_document
from acs_plan_store_reload import load_workspace
from acs_supabase_plan_store import SupabasePlanStore

ACTOR = "11111111-1111-4111-8111-111111111111"
PROJECT = "22222222-2222-4222-8222-222222222222"


def revision_history(count, size):
    workspace = PlanLockWorkspace()
    model = {"floors": {"g": {"rooms": [{"id": "r", "rect": [0, 0, 4, 4]}]}},
             "levels": [{"index": 0, "template": "g"}], "fixture": "x" * size}
    receipts = []
    for number in range(count):
        revision = workspace.propose(model, brief="Synthetic", requirements=[],
                                     expected_head=workspace.head, note=str(number))
        receipts.append(revision_document(revision))
    return receipts


class HistoryTransport:
    """Simulates member-filtered table reads with a fixed response ceiling."""
    def __init__(self, revisions):
        self.revisions = revisions
        self.role = "editor"
        self.present = True
        self.on_document = lambda: None
        self.baseline = None
        self.max_bytes = 0
        self.pages = []

    def __call__(self, *, method, url, body, **kwargs):
        path = urlsplit(url)
        query = {k: v[0] for k, v in parse_qs(path.query).items()}
        if path.path.endswith("/rpc/acs_plan_workspace_snapshot"):
            response = {"schema": "acs.plan-store-workspace-snapshot/1.0", "project_id": PROJECT,
                        "head_revision_id": self.revisions[-1]["revision_id"], "baseline_revision_id": None,
                        "revisions": self.revisions, "approvals": []}
        elif path.path.endswith("/acs_projects"):
            assert method == "GET" and body is None
            assert query["id"] == "eq." + PROJECT and query["memberships.user_id"] == "eq." + ACTOR
            row = {"id": PROJECT, "memberships": [{"user_id": ACTOR, "role": self.role}],
                   "head_revision_id": self.revisions[-1]["revision_id"] if self.revisions else None,
                   "baseline_revision_id": self.baseline}
            if "revisions:" in query["select"]:
                offset = int(query["revisions.revision_number"].removeprefix("gt."))
                limit = int(query["revisions.limit"])
                assert query["revisions.order"] == "revision_number.asc" and limit <= 25
                self.pages.append(offset)
                row["revisions"] = [{k: doc[k] for k in
                                     ("revision_id", "number", "parent_id", "content_hash", "bound_content_hash")}
                                    for doc in self.revisions[offset:offset + limit]]
            response = [row] if self.present else []
        elif path.path.endswith("/acs_plan_revisions"):
            assert method == "GET" and body is None and query["project_id"] == "eq." + PROJECT
            self.on_document()
            ordinal = int(query["revision_number"].removeprefix("eq."))
            doc = self.revisions[ordinal - 1]
            response = [{"project_id": PROJECT, "revision_json": doc, "approval": None}] if self.present else []
        else:
            raise AssertionError("unexpected database route")
        body = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode()
        self.max_bytes = max(self.max_bytes, len(body))
        return 200, body

    def store(self):
        return SupabasePlanStore("https://fixture.invalid", "test-key", "test-token",
                                 actor_id=ACTOR, transport=self)


class HistoryReads(unittest.TestCase):
    def test_five_large_receipts_reopen(self):
        receipts = revision_history(5, 650_000)
        transport = HistoryTransport(receipts)
        restored = load_workspace(transport.store(), PROJECT, actor_id=ACTOR)
        self.assertEqual(restored.head, receipts[-1]["revision_id"])
        self.assertEqual([restored.get(d["revision_id"]).model_hash for d in receipts],
                         [d["model_hash"] for d in receipts])
        self.assertGreater(sum(len(json.dumps(d)) for d in receipts), 3_000_000)
        self.assertLess(transport.max_bytes, 700_000)

    def test_next_page_and_view_only_role(self):
        transport = HistoryTransport(revision_history(26, 10))
        transport.role = "viewer"
        self.assertEqual(len(transport.store().project_state(PROJECT, actor_id=ACTOR)["revisions"]), 26)
        self.assertEqual(transport.pages, [0, 25])
        with self.assertRaises(PlanError) as ctx:
            transport.store().workspace_snapshot(PROJECT, actor_id=ACTOR)
        self.assertEqual(ctx.exception.code, "PROJECT_ACCESS_DENIED")

    def test_approval_changed_during_recovery(self):
        transport = HistoryTransport(revision_history(1, 10))
        transport.on_document = lambda: setattr(transport, "baseline", transport.revisions[0]["revision_id"])
        with self.assertRaises(PlanError) as ctx:
            transport.store().workspace_snapshot(PROJECT, actor_id=ACTOR)
        self.assertEqual(ctx.exception.code, "STALE_REVISION")

    def test_removal_during_recovery(self):
        transport = HistoryTransport(revision_history(1, 10))
        transport.on_document = lambda: setattr(transport, "present", False)
        with self.assertRaises(PlanError) as ctx:
            transport.store().workspace_snapshot(PROJECT, actor_id=ACTOR)
        self.assertEqual(ctx.exception.code, "PROJECT_ACCESS_DENIED")

    def test_corrupt_receipt_fails_closed(self):
        docs = copy.deepcopy(revision_history(1, 10))
        docs[0]["model"]["fixture"] = "altered"
        with self.assertRaises(PlanError) as ctx:
            HistoryTransport(docs).store().workspace_snapshot(PROJECT, actor_id=ACTOR)
        self.assertEqual(ctx.exception.code, "STORED_MODEL_TAMPERED")


if __name__ == "__main__":
    unittest.main()
