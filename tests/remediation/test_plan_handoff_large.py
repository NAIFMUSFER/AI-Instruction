#!/usr/bin/env python3
"""Regression: large valid glTF artifacts must not inherit the 900 kB plan-input cap."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_handoff as H
from acs_plan_review import PlanWorkspace


def model():
    return {
        "meta": {"type": "residential"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "room", "role": "living", "rect": [0.0, 0.0, 5.0, 5.0],
             "doors": [], "windows": []}
        ]}},
    }


class LargeGltfHandoffRegression(unittest.TestCase):
    def test_large_gltf_is_hash_bound_without_plan_size_rejection(self):
        ws = PlanWorkspace(lambda _m: {
            "scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": [],
        })
        brief = "أرض بعرض 20 متر"
        rev = ws.propose(model(), brief=brief,
                         requirements=[{"id": "w", "metric": "site_width_m",
                                        "expected": 20.0, "source": "requested",
                                        "evidence": "20"}],
                         expected_head=None, note="initial")
        ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
                   confirmed=True, acknowledge_concept_only=True)

        def large_compiler(_building, path):
            # > 900 kB on purpose: canonical plan payloads are bounded, compiled
            # artifacts are not. The old serializer incorrectly applied that
            # input ceiling to glTF and rejected a valid large artifact.
            payload = {"asset": {"version": "2.0"},
                       "extras": {"fixture_padding": "x" * 950_000},
                       "nodes": []}
            Path(path).write_text(json.dumps(payload), encoding="utf-8")
            return 1, 950_000

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "large.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=large_compiler)
            self.assertGreater(out.stat().st_size, 900_000)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertTrue(H.verify_compiled_artifact(out)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
