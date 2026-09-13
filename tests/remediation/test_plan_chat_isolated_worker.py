"""Provider proposal work is isolated from authenticated PlanStore authority."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import acs_plan_chat_job as J
from acs_plan_review import PlanError


BUILDING = {
    "schema_version": "acs.building/1.0",
    "type": "warehouse",
    "levels": [{"name": "ground", "template": "ground", "elevation": 0.0, "height": 6.0}],
    "floors": {"ground": {"rooms": [{"id": "staging", "name": "Staging", "rect": [0.0, 0.0, 8.0, 10.0]}]}},
}
NOTES = [{"text": "وسّع staging مع إبقاء docks والرفوف المقفلة كما هي"}]


class CapturingRunner:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def run(self, target, kwargs=None, timeout_s=None, request_id=None):
        self.calls.append((target, kwargs, timeout_s, request_id))
        return copy.deepcopy(self.value)


class IsolatedPlanChatWorkerTests(unittest.TestCase):
    def test_parent_runner_payload_contains_geometry_notes_and_model_only(self):
        expected = copy.deepcopy(BUILDING)
        expected["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 10.0, 10.0]
        runner = CapturingRunner(expected)

        result = J.run_isolated_chat_candidate(
            BUILDING,
            NOTES,
            model="provider-model",
            request_id="req_test",
            timeout_s=17,
            runner=runner,
        )

        self.assertEqual(result, expected)
        self.assertEqual(len(runner.calls), 1)
        target, kwargs, timeout_s, request_id = runner.calls[0]
        self.assertEqual(target, J.TARGET)
        self.assertEqual(set(kwargs), {"building", "notes", "model"})
        self.assertEqual(timeout_s, 17)
        self.assertEqual(request_id, "req_test")
        self.assertNotIn("actor_id", kwargs)
        self.assertNotIn("bearer", kwargs)
        self.assertNotIn("token", kwargs)
        self.assertNotIn("store", kwargs)

        # The worker envelope is detached from caller-owned mutable objects.
        self.assertIsNot(kwargs["building"], BUILDING)
        self.assertIsNot(kwargs["notes"], NOTES)

    def test_worker_calls_apply_notes_only_and_returns_detached_canonical_candidate(self):
        original = copy.deepcopy(BUILDING)

        def apply_notes(building, notes, model=None):
            self.assertEqual(notes, NOTES)
            self.assertEqual(model, "provider-model")
            building["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 9.0, 10.0]
            return building

        fake_provider = SimpleNamespace(apply_notes=Mock(side_effect=apply_notes))
        with patch.dict(sys.modules, {"acs_understand": fake_provider}):
            candidate = J.generate_chat_candidate(
                BUILDING, NOTES, model="provider-model")

        self.assertEqual(BUILDING, original)
        self.assertEqual(candidate["floors"]["ground"]["rooms"][0]["rect"], [0.0, 0.0, 9.0, 10.0])
        fake_provider.apply_notes.assert_called_once()

    def test_worker_rejects_malformed_inputs_before_provider_import(self):
        fake_provider = SimpleNamespace(
            apply_notes=Mock(side_effect=AssertionError("provider must not run")))
        with patch.dict(sys.modules, {"acs_understand": fake_provider}):
            for building, notes in ((None, NOTES), (BUILDING, []), (BUILDING, [{"text": ""}])):
                with self.subTest(building=building, notes=notes):
                    with self.assertRaises(PlanError):
                        J.generate_chat_candidate(building, notes)
        fake_provider.apply_notes.assert_not_called()

    def test_worker_rejects_non_object_provider_candidate(self):
        fake_provider = SimpleNamespace(apply_notes=Mock(return_value=[]))
        with patch.dict(sys.modules, {"acs_understand": fake_provider}):
            with self.assertRaises(PlanError) as got:
                J.generate_chat_candidate(BUILDING, NOTES)
        self.assertEqual(got.exception.code, "INVALID_EDIT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
