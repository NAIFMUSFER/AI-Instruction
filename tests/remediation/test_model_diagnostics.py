"""Captured generation regression; no provider request is made.

The fixture retains the geometry that returned issues=0 in production while
the architecture compiler reported seven invalid walls. API tests cross the
real CPU worker boundary; only the paid generation job is replaced.
"""
import asyncio
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import acs_arch as AR
import acs_engineering_authority as EA
import acs_understand_api as API
import acs_validate as V
from fastapi.testclient import TestClient

FIXTURE = {
    "meta": {"name": "ACS Acceptance Warehouse 20260906", "type": "warehouse",
             "strict": True, "acs_issues": 0},
    "site": {"w": 20, "d": 15}, "floor_height": 4, "wall_h": 4, "wall_t": 0,
    "levels": [{"index": 0, "name": "Ground", "template": "ground", "id": "L0"}],
    "floors": {"ground": {"rooms": [
        {"id": "storage", "rect": [0, 0, 15, 15]},
        {"id": "receiving", "rect": [15, 0, 5, 15], "doors": [
            {"edge": "S", "offset": 2.5, "width": 2, "height": 2.4},
            {"edge": "W", "offset": 7.5, "width": 1.2, "height": 2.1}]}]}}
}


class DiagnosticsTests(unittest.TestCase):
    def test_capture_exposes_seven_wall_findings(self):
        result = EA.model_diagnostics(copy.deepcopy(FIXTURE))
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["issue_count"], 7)
        self.assertEqual(result["scopes"]["architecture"]["findings"],
                         AR.compile_architecture(FIXTURE)["issues"])
        self.assertEqual({x["code"] for x in result["scopes"]["architecture"]["findings"]},
                         {"WALL_NEGATIVE_THICKNESS"})
        self.assertTrue(result["review_required"])

    def test_diagnostics_do_not_change_captured_geometry_or_metadata(self):
        model = copy.deepcopy(FIXTURE)
        before = json.dumps(model, sort_keys=True)
        result = EA.model_diagnostics(model)
        self.assertEqual(json.dumps(model, sort_keys=True), before)
        self.assertEqual(result["model_hash"], EA.model_hash(model))
        self.assertEqual(model["wall_t"], 0)  # do not silently repair uncertainty

    def test_diagnostics_are_deterministic(self):
        self.assertEqual(EA.model_diagnostics(FIXTURE), EA.model_diagnostics(FIXTURE))

    def test_semantic_diagnostics_are_recomputed_not_read_from_stale_meta(self):
        model = copy.deepcopy(FIXTURE)
        model["site"]["w"] = 10
        result = EA.model_diagnostics(model)
        self.assertGreater(len(result["scopes"]["semantic"]["findings"]), 0)
        self.assertGreater(result["issue_count"], 7)

    def test_no_findings_is_not_a_regulatory_or_provenance_approval(self):
        model = copy.deepcopy(FIXTURE)
        model["wall_t"] = 0.2
        result = EA.model_diagnostics(model)
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["compliance"], "NOT_EVALUATED")
        self.assertNotIn("approved", result)

    def test_compiler_failure_has_unknown_count_and_no_exception_leak(self):
        with patch.object(AR, "compile_architecture", side_effect=ValueError("private-input")):
            result = EA.model_diagnostics(FIXTURE)
        self.assertEqual(result["status"], "NOT_EVALUATED")
        self.assertIsNone(result["issue_count"])
        self.assertTrue(result["review_required"])
        self.assertNotIn("private-input", json.dumps(result))

    def test_partial_failure_retains_known_architecture_findings(self):
        with patch.object(V, "validate_building", side_effect=ValueError("private-input")):
            result = EA.model_diagnostics(FIXTURE)
        self.assertIsNone(result["issue_count"])
        self.assertEqual(result["known_issue_count"], 7)
        self.assertEqual(result["scopes"]["architecture"]["status"], "COMPLETED")

    def test_normalised_model_and_diagnostics_have_the_same_hash(self):
        model = copy.deepcopy(FIXTURE)
        model.pop("floor_height")
        result = EA.plan_with_model(model)
        self.assertEqual(result["model_validation"]["model_hash"],
                         EA.model_hash(result["building"]))
        self.assertEqual(result["plan"]["model_hash_after"],
                         result["model_validation"]["model_hash"])


class ApiDiagnosticsTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        API._CPU.shutdown(wait=True)

    def test_payload_crosses_real_cpu_worker_and_exposes_findings(self):
        result = asyncio.run(API._understand_payload(copy.deepcopy(FIXTURE)))
        self.assertEqual(result["issues"], 7)
        self.assertEqual(result["model_validation"]["model_hash"],
                         EA.model_hash(result["building"]))
        self.assertEqual(result["model_validation"]["scopes"]["architecture"]["status"],
                         "COMPLETED")
        self.assertEqual(API._CPU.health_status()["executor"], "process")

    def test_http_response_uses_captured_job_and_real_validation(self):
        with patch.object(API, "run_job", new=AsyncMock(return_value=copy.deepcopy(FIXTURE))) as job:
            client = TestClient(API.app)
            response = client.post("/v1/understand", json={
                "text": "Synthetic captured model replay", "strict": True, "deep": False})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(job.await_count, 1)
        self.assertEqual(response.json()["issues"], 7)
        self.assertEqual(response.json()["compliance"]["status"], "NOT_EVALUATED")

    def test_planner_failure_is_not_reported_as_zero_issues(self):
        with patch.object(API, "_validate", new=AsyncMock(side_effect=RuntimeError("private-input"))):
            result = asyncio.run(API._understand_payload(copy.deepcopy(FIXTURE)))
        self.assertIsNone(result["issues"])
        self.assertEqual(result["model_validation"]["status"], "NOT_EVALUATED")
        self.assertNotIn("private-input", json.dumps(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
