#!/usr/bin/env python3
"""Red-first IFC derived-authority receipt regressions."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acs_plan_review import PlanError
from test_plan_ifc_export import approved_workspace, residential_model
from tools import acs_plan_ifc_export as X


class IfcDerivedAuthorityReceiptTests(unittest.TestCase):
    def test_receipt_explicitly_keeps_canonical_model_authoritative(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "authority.ifc"
            receipt = X.export_approved_ifc(ws, rev.id, out)
            self.assertIs(receipt.get("canonical_model_is_source_of_truth"), True)
            self.assertIs(receipt.get("ifc_is_source_of_truth"), False)
            self.assertEqual(receipt.get("replanning_calls"), 0)
            self.assertTrue(X.verify_ifc_export(out)["ok"])

    def test_verifier_rejects_receipt_that_promotes_ifc_authority(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "authority-tamper.ifc"
            receipt = X.export_approved_ifc(ws, rev.id, out)
            receipt["ifc_is_source_of_truth"] = True
            with self.assertRaises(PlanError) as got:
                X.verify_ifc_export(out, receipt)
            self.assertEqual(got.exception.code, "INVALID_BASELINE_RECEIPT")

    def test_verifier_rejects_receipt_that_claims_replanning(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "replan-tamper.ifc"
            receipt = X.export_approved_ifc(ws, rev.id, out)
            receipt["replanning_calls"] = 1
            with self.assertRaises(PlanError) as got:
                X.verify_ifc_export(out, receipt)
            self.assertEqual(got.exception.code, "INVALID_BASELINE_RECEIPT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
