"""C04: keep LLM repair available for review; never replace geometry silently."""
import asyncio
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_understand as U
import acs_understand_api as A
import acs_cpu_pool as CPU
import acs_validate as V


def models():
    original = {"site": {"w": 20, "d": 25}, "meta": {"type": "residential"},
        "levels": [{"index": 0, "template": "g"}], "floors": {"g": {"rooms": [
            {"id": "room", "rect": [0, 0, 6, 6],
             "doors": [{"edge": "N", "offset": 3, "width": 1}]}]}}}
    fixed = copy.deepcopy(original)
    fixed["floors"]["g"]["rooms"][0].update(rect=[0, 0, 5, 5], points=[
        {"type": "light", "x": 2, "z": 2}, {"type": "smoke", "x": 2, "z": 2}])
    return original, fixed


class RepairProposal(unittest.TestCase):
    def generate(self, original, fixed):
        with patch.object(U, "call_llm", return_value=json.dumps(original)), \
             patch.object(U, "call_llm_repair", return_value=json.dumps(fixed)) as repair:
            result = U.understand("غرفة 6×6 م، احتفظ بالمقاس", deep=False,
                                  repair_rounds=1, strict=False)
        repair.assert_called_once()
        return result

    def test_better_issue_count_does_not_authorise_dimension_change(self):
        original, fixed = models()
        result = self.generate(original, fixed)
        self.assertEqual(result["floors"], original["floors"])
        self.assertEqual(result["meta"]["acs_issues"], len(V.validate_building(original)[0]))
        proposal = result["meta"]["acs_repair_proposal"]
        self.assertEqual(proposal["building"]["floors"], fixed["floors"])
        self.assertFalse(proposal["applied"])
        self.assertTrue(proposal["requires_confirmation"])
        self.assertLess(len(proposal["issues_after"]), len(proposal["issues_before"]))

    def test_clean_model_does_not_request_repair(self):
        _, clean = models()
        with patch.object(U, "call_llm", return_value=json.dumps(clean)), \
             patch.object(U, "call_llm_repair") as repair:
            result = U.understand("غرفة", deep=False, repair_rounds=1)
        repair.assert_not_called()
        self.assertNotIn("acs_repair_proposal", result["meta"])
        self.assertEqual(result["floors"], clean["floors"])

    def test_repair_prompt_contains_the_original_request(self):
        original, _ = models()
        description = "احتفظ بالمقاس المطلوب ولا تضف غرفة فرز"
        with patch.object(U, "call_llm", return_value="{}") as call:
            U.call_llm_repair(description, original, ["test issue"])
        self.assertIn(description, call.call_args.args[0])

    def test_api_returns_review_diff_outside_the_canonical_model(self):
        original, fixed = models()
        result = self.generate(original, fixed)
        async def run():
            async def authority(model):
                return {"proposals": []}, model
            async def dispatch(target, args):
                worker = CPU._worker(target, args, {})
                self.assertTrue(worker["ok"])
                return worker["value"]
            with patch.object(A, "_engineering_authority", AsyncMock(side_effect=authority)), \
                 patch.object(CPU, "run", AsyncMock(side_effect=dispatch)):
                return await A._understand_payload(result)
        payload = asyncio.run(run())
        self.assertEqual(payload["building"]["floors"], original["floors"])
        self.assertNotIn("acs_repair_proposal", payload["building"]["meta"])
        proposal = payload["report"]["repair_proposal"]
        self.assertFalse(proposal["applied"])
        self.assertTrue(proposal["requires_confirmation"])
        diff = proposal["engineering_diff"]
        self.assertTrue(diff["available"])
        self.assertTrue(any(item["path"].endswith("rect[2]") and item["before"] == 6
                            and item["after"] == 5 for item in diff["changed"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
