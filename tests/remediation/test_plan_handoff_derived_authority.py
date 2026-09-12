#!/usr/bin/env python3
"""Red-first authority contracts for approved Frozen-Baseline 3D artifacts."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acs_plan_review import PlanError
from test_plan_handoff import workspace_with, residential_model
from tools import acs_plan_handoff as H


class Approved3DDerivedAuthorityTests(unittest.TestCase):
    @staticmethod
    def _compiler(building, path):
        Path(path).write_text(json.dumps({"asset": {"version": "2.0"}, "nodes": []}), encoding="utf-8")
        return len(building.get("levels") or []), 16

    def test_receipt_explicitly_keeps_canonical_model_authoritative(self):
        ws, rev = workspace_with(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "authority.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=self._compiler)
            self.assertIs(receipt.get("canonical_model_is_source_of_truth"), True)
            self.assertIs(receipt.get("three_d_is_source_of_truth"), False)
            self.assertEqual(receipt.get("replanning_calls"), 0)
            self.assertTrue(H.verify_compiled_artifact(out)["ok"])

    def test_verifier_rejects_receipt_that_promotes_3d_authority(self):
        ws, rev = workspace_with(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "authority-tamper.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=self._compiler)
            receipt["three_d_is_source_of_truth"] = True
            with self.assertRaises(PlanError) as got:
                H.verify_compiled_artifact(out, receipt)
            self.assertEqual(got.exception.code, "INVALID_BASELINE_RECEIPT")

    def test_verifier_rejects_receipt_that_claims_replanning(self):
        ws, rev = workspace_with(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "replan-tamper.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=self._compiler)
            receipt["replanning_calls"] = 1
            with self.assertRaises(PlanError) as got:
                H.verify_compiled_artifact(out, receipt)
            self.assertEqual(got.exception.code, "INVALID_BASELINE_RECEIPT")

    def test_authority_verification_does_not_mutate_frozen_baseline(self):
        model = residential_model()
        before = copy.deepcopy(model)
        ws, rev = workspace_with(model)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "immutable-authority.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=self._compiler)
            self.assertTrue(H.verify_compiled_artifact(out, receipt)["ok"])
        self.assertEqual(model, before)
        self.assertEqual(ws.get(rev.id).model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
