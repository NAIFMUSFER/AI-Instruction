"""No uncited regulatory threshold may become a repair or executable proposal."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_engineering_authority as EA
import acs_engineering_approval as AP
import acs_authoring as A
import acs_validate as V


def model(strict=False):
    return {"meta": {"type": "warehouse", "strict": strict},
            "site": {"w": 20, "d": 15}, "floor_height": 4, "wall_h": 4, "wall_t": 0.2,
            "levels": [{"index": 0, "template": "g", "id": "L0"}],
            "floors": {"g": {"rooms": [{"id": "forklift_aisle", "role": "aisle",
                "rect": [0, 0, 20, 0.8], "walls": "none", "lanes": [
                    {"kind": "forklift", "w": 20, "d": 0.8}],
                "points": [{"type": "light", "x": 1, "z": 0.4},
                           {"type": "outlet", "x": 2, "z": 0.4, "height": 1.9}]}]}}}


class RuleSourceTests(unittest.TestCase):
    def test_legacy_validator_does_not_instruct_uncited_repairs(self):
        for strict in (True, False):
            with self.subTest(strict=strict):
                issues, _stats = V.validate_building(model(strict))
                self.assertEqual(issues, [])

    def test_planning_exposes_six_unresolved_reviews(self):
        result = EA.plan(model())
        self.assertEqual(len(result["review_requirements"]), 6)
        for task in result["review_requirements"]:
            self.assertEqual(task["status"], "NOT_EVALUATED")
            self.assertEqual(task["required_value"], {"value": None, "status": "UNKNOWN"})
            self.assertEqual(task["rule_sources"], [])
            self.assertNotIn("after", task)
            self.assertNotIn("authoring_command", task)

    def test_no_unsourced_proposal_in_either_mode(self):
        for strict in (True, False):
            result = EA.plan(model(strict))
            self.assertFalse({p["type"] for p in result["proposals"]} &
                             EA.UNSOURCED_RULE_CHANGES)

    def test_legacy_code_gap_entrypoint_does_not_supply_thresholds(self):
        self.assertEqual(EA.code_gap_proposals(model()), [])

    def test_observations_are_template_records_not_required_quantities(self):
        m = model()
        m["floors"]["g"]["rooms"][0]["points"].append({"type": "exit", "x": 0, "z": 0})
        tasks = EA.code_review_requirements(m)
        exits = next(t for t in tasks if t["requirement_id"] == "review:fire_exits")
        self.assertEqual(exits["observed_template_records"], {"exit": 1})
        self.assertIsNone(exits["required_value"]["value"])

    def test_larger_inventory_does_not_establish_adequacy(self):
        m = model()
        m["floors"]["g"]["rooms"][0]["points"] += [
            {"type": "exit", "x": 1, "z": 0.5} for _ in range(100)]
        self.assertTrue(all(t["status"] == "NOT_EVALUATED"
                            for t in EA.code_review_requirements(m)))

    def test_review_requirements_are_deterministic_and_non_mutating(self):
        m = model()
        before = json.dumps(m, sort_keys=True)
        self.assertEqual(EA.code_review_requirements(m), EA.code_review_requirements(m))
        self.assertEqual(json.dumps(m, sort_keys=True), before)

    def test_eight_legacy_threshold_types_are_explicitly_blocked(self):
        expected = {"FLS_ADD_EXIT", "FLS_ADD_EXTINGUISHER", "FLS_ADD_ASSEMBLY_POINT",
                    "SEC_ADD_CAMERA", "LAYOUT_AISLE_WIDTH", "LAYOUT_ADD_SMOKE_DETECTOR",
                    "LAYOUT_ADD_SPRINKLER", "LAYOUT_POINT_HEIGHT_STANDARD"}
        self.assertEqual(EA.UNSOURCED_RULE_CHANGES, expected)
        for kind in expected:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                EA.proposal(kind, ["g.forklift_aisle"], {}, {"count": 4})

    def test_old_saved_proposals_cannot_bypass_boundary_by_claiming_a_rule(self):
        project = A.create_project(model(), "bld_0", source="TEST", actor_id="tester")
        before = copy.deepcopy(project)
        for kind in EA.UNSOURCED_RULE_CHANGES:
            p = {"type": kind, "proposal_id": "prop:stored", "authoring_command": "ADD_POINT",
                 "target_ids": ["g.forklift_aisle"], "after": {"exit_count": 4},
                 "detail": {"point_type": "exit", "missing": 4},
                 "provenance": {"rule_id": "AI-made-up", "version": "1", "verified": True}}
            result = AP.approve(project, [p], [p["proposal_id"]])
            self.assertFalse(result["committed"])
            self.assertEqual(result["issues"][0]["code"], "RULE_SOURCE_REQUIRED")
            self.assertEqual(project, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
