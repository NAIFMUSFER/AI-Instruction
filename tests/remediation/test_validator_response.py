"""C03: the response count and findings describe the exact outgoing model."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_understand_api as A
import acs_cpu_pool as CPU
import acs_validate as V
import acs_api_errors as E


def building(stale_count=0, outside=False):
    return {"site": {"w": 10, "d": 10}, "meta": {"strict": True,
            "acs_issues": stale_count}, "levels": [{"index": 0, "template": "g"}],
            "floors": {"g": {"rooms": [{"id": "room", "rect":
                [9 if outside else 1, 1, 4, 4],
                "doors": [{"edge": "N", "offset": 2}]}]}}}


class ValidatorResponse(unittest.IsolatedAsyncioTestCase):
    async def payload(self, source, outgoing):
        checked = []
        async def dispatch(target, args):
            self.assertEqual(target, "validate_building")
            checked.append(copy.deepcopy(args[0]))
            result = CPU._worker(target, args, {})
            self.assertTrue(result["ok"])
            return result["value"]
        with patch.object(A, "_engineering_authority", AsyncMock(
                return_value=({"proposals": []}, outgoing))), \
             patch.object(CPU, "run", AsyncMock(side_effect=dispatch)) as run:
            result = await A._understand_payload(source)
        expected, stats = V.validate_building(result["building"])
        self.assertEqual(result["issues"], len(expected))
        self.assertEqual(result["model_validation"], {"status": "COMPLETED",
            "scope": "acs_validate", "issues": expected, "stats": stats})
        run.assert_awaited_once()
        self.assertEqual(checked, [result["building"]])
        return result

    async def test_stale_zero_does_not_hide_outside_room(self):
        result = await self.payload(building(0, True), building(0, True))
        self.assertGreater(result["issues"], 0)
        self.assertTrue(any("خارج مسطح البناء" in s
                            for s in result["model_validation"]["issues"]))

    async def test_stale_positive_does_not_invent_issues_on_valid_model(self):
        result = await self.payload(building(22), building(22))
        self.assertEqual(result["issues"], 0)
        self.assertEqual(result["model_validation"]["issues"], [])

    async def test_validator_sees_normalised_model_without_mutating_source(self):
        source, outgoing = building(0), building(0, True)
        before = copy.deepcopy(source)
        result = await self.payload(source, outgoing)
        self.assertEqual(result["building"], outgoing)
        self.assertEqual(source, before)
        self.assertGreater(result["issues"], 0)

    async def test_validator_failure_cannot_be_reported_as_zero(self):
        with patch.object(A, "_engineering_authority", AsyncMock(
                return_value=({"proposals": []}, building()))), \
             patch.object(CPU, "run", AsyncMock(side_effect=CPU.WorkerCrashed("test"))):
            with self.assertRaises(E.AcsApiError) as caught:
                await A._understand_payload(building())
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_UNKNOWN)

    async def test_validator_is_an_explicit_cpu_worker_target(self):
        self.assertEqual(CPU.TARGETS.get("validate_building"),
                         ("acs_validate", "validate_building"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
