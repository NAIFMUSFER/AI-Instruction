"""Regression coverage for durable async revision-reference delivery metadata."""
from __future__ import annotations

import unittest

import acs_workspace_http as H


class AsyncJobReferenceReceipt(unittest.TestCase):
    def test_receipt_exposes_only_public_reference_revision_metadata(self):
        reference = "44444444-4444-4444-8444-444444444444"
        target = "55555555-5555-4555-8555-555555555555"
        receipt = H._job_view({
            "id": "33333333-3333-4333-8333-333333333333",
            "state": "SUCCEEDED",
            "revision_id": target,
            "expected_head": reference,
            "input_hash": "private-fingerprint",
            "worker_id": "private-worker",
        })["job"]

        self.assertEqual(receipt["revision_id"], target)
        self.assertEqual(receipt["reference_revision_id"], reference)
        self.assertNotIn("expected_head", receipt)
        self.assertNotIn("input_hash", receipt)
        self.assertNotIn("worker_id", receipt)

    def test_first_generation_keeps_unknown_reference_explicitly_null(self):
        receipt = H._job_view({
            "id": "33333333-3333-4333-8333-333333333333",
            "state": "SUCCEEDED",
            "revision_id": "55555555-5555-4555-8555-555555555555",
            "expected_head": None,
        })["job"]
        self.assertIsNone(receipt["reference_revision_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
