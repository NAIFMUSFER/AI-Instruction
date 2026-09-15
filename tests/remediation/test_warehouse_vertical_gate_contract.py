#!/usr/bin/env python3
"""RED contract for live warehouse Pipeline v2 vertical-geometry gap.

A warehouse brief may deliberately leave final clear height / wall build-up to
engineering. The design-option / 2D draft stage must not invent those values,
and must not misclassify their absence as a failed horizontal layout. Exact
vertical values become mandatory only at the approved downstream 3D boundary.

This test is intentionally RED until the stage-aware admission contract exists.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class WarehouseVerticalGateContract(unittest.TestCase):
    def test_stage_aware_vertical_geometry_contract_exists(self):
        """The shared review module must expose a stage-aware vertical gate.

        Do not satisfy this by adding defaults. The implementation must allow a
        warehouse PLAN_DRAFT with unknown vertical engineering values while the
        approved 3D handoff continues to fail closed until they are explicit.
        """
        import acs_plan_review as review
        self.assertTrue(
            hasattr(review, "warehouse_vertical_stage_gate"),
            "RED: warehouse draft currently has no explicit stage-aware vertical-geometry gate",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
