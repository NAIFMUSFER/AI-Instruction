#!/usr/bin/env python3
"""Shared ACS Design Pipeline v2 lifecycle regressions for every registered typology.

This test deliberately proves only the shared authority boundary. It does not claim
that one generic fixture exercises each typology's specialist planning policy,
design quality, regulatory compliance or construction readiness.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import acs_plan_scorecard as SCORE
from acs_plan_review import PlanError, PlanWorkspace
from tools import acs_plan_handoff as HANDOFF

BRIEF = "موقع بعرض 20 متر وعمق 20 متر؛ يجب اعتماد المخطط قبل اشتقاق النموذج ثلاثي الأبعاد."


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def requirements():
    return [{
        "id": "site-width",
        "metric": "site_width_m",
        "expected": 20.0,
        "source": "requested",
        "evidence": "20",
    }]


def minimal_model(program_id: str) -> dict:
    return {
        "meta": {"type": program_id, "name": f"lifecycle-{program_id}"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2,
        "wall_h": 3.0,
        "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {
            "ground": {
                "rooms": [{
                    "id": "primary",
                    "role": "primary",
                    "rect": [0.0, 0.0, 10.0, 10.0],
                    "doors": [],
                    "windows": [],
                }]
            }
        },
    }


def registry_programs() -> list[dict]:
    data = json.loads((ROOT / "acs_programs.json").read_text(encoding="utf-8"))
    programs = data.get("programs")
    if not isinstance(programs, list) or not programs:
        raise AssertionError("acs_programs.json must contain registered typologies")
    return programs


class RegisteredTypologyLifecycleTests(unittest.TestCase):
    def assert_plan_error(self, code: str, fn) -> None:
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_every_registered_typology_requires_approval_before_exact_baseline_3d(self):
        programs = registry_programs()
        ids = [row.get("id") for row in programs]
        self.assertEqual(len(ids), len(set(ids)), "registered program ids must remain unique")
        self.assertTrue({"residential", "villa", "apartment", "warehouse", "industrial"}.issubset(set(ids)))

        for program in programs:
            program_id = program["id"]
            with self.subTest(program=program_id):
                model = minimal_model(program_id)
                ws = PlanWorkspace(verified)
                rev = ws.propose(
                    copy.deepcopy(model),
                    brief=BRIEF,
                    requirements=requirements(),
                    expected_head=None,
                    note=f"shared Pipeline v2 lifecycle fixture for {program_id}",
                )

                compiler_calls = []

                def fake_compiler(building, path):
                    compiler_calls.append(copy.deepcopy(building))
                    Path(path).write_text(
                        json.dumps({"asset": {"version": "2.0"}, "nodes": []}),
                        encoding="utf-8",
                    )
                    return 0, 0

                with tempfile.TemporaryDirectory() as td:
                    draft = Path(td) / f"{program_id}-draft.gltf"
                    self.assert_plan_error(
                        "APPROVAL_REQUIRED",
                        lambda: HANDOFF.compile_approved_baseline(
                            ws, rev.id, draft, compiler=fake_compiler
                        ),
                    )
                    self.assertEqual(compiler_calls, [], "draft must fail before compiler invocation")
                    self.assertFalse(draft.exists())

                    approval = ws.approve(
                        rev.id,
                        expected_head=rev.id,
                        actor_label="test-engineer",
                        confirmed=True,
                        acknowledge_concept_only=True,
                    )
                    self.assertEqual(approval.revision_id, rev.id)
                    self.assertEqual(ws.baseline, rev.id)

                    approved = Path(td) / f"{program_id}-approved.gltf"
                    receipt = HANDOFF.compile_approved_baseline(
                        ws, rev.id, approved, compiler=fake_compiler
                    )
                    self.assertEqual(compiler_calls, [model])
                    self.assertEqual(receipt["revision_id"], rev.id)
                    self.assertEqual(receipt["model_hash"], rev.model_hash)
                    self.assertEqual(receipt["provider_calls"], 0)
                    self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
                    self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
                    self.assertTrue(HANDOFF.verify_compiled_artifact(approved)["ok"])

    def test_scorecard_uses_registry_typology_without_borrowing_warehouse_claims(self):
        for program in registry_programs():
            program_id = program["id"]
            with self.subTest(program=program_id):
                result = SCORE.measure_plan(minimal_model(program_id))
                if program.get("domain") == "industrial":
                    self.assertEqual(result["typology"], "warehouse")
                    self.assertIn("dock_count", result["metrics"])
                else:
                    self.assertEqual(result["typology"], program_id)
                    self.assertNotIn("dock_count", result["metrics"])
                self.assertFalse(result["claims_regulatory_compliance"])
                self.assertFalse(result["claims_structural_safety"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
