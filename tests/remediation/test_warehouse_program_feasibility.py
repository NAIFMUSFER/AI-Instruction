#!/usr/bin/env python3
"""RED contract for #159: warehouse options need a program feasibility budget."""
import unittest

from warehouse_program_feasibility import classify_warehouse_program, warehouse_program_feasibility


class WarehouseProgramFeasibilityTests(unittest.TestCase):
    def test_outdoor_operations_are_not_indoor_program_area(self):
        program = [
            {"id":"storage","role":"storage","area_m2":1200,"scope":"indoor","hard":False},
            {"id":"receiving","role":"receiving","area_m2":300,"scope":"indoor","hard":False},
            {"id":"truck_yard","role":"truck_yard","area_m2":1800,"scope":"outdoor","hard":False},
            {"id":"parking","role":"parking","area_m2":600,"scope":"outdoor","hard":False},
        ]
        classified = classify_warehouse_program(program)
        self.assertEqual(classified["indoor_area_m2"], 1500)
        self.assertEqual(classified["outdoor_area_m2"], 2400)

    def test_soft_indoor_target_is_bounded_by_explicit_building_target(self):
        result = warehouse_program_feasibility(
            site_area_m2=5000,
            building_target_m2=2000,
            program=[
                {"id":"storage","role":"storage","area_m2":1900,"scope":"indoor","hard":False},
                {"id":"staging","role":"staging","area_m2":500,"scope":"indoor","hard":False},
                {"id":"admin","role":"admin","area_m2":300,"scope":"indoor","hard":False},
                {"id":"yard","role":"truck_yard","area_m2":1800,"scope":"outdoor","hard":False},
            ])
        self.assertEqual(result["status"], "ADJUSTABLE")
        self.assertLessEqual(result["indoor_budget_m2"], 2000)
        self.assertEqual(result["outdoor_program_m2"], 1800)
        self.assertTrue(result["adjustment_required"])

    def test_hard_indoor_program_over_target_fails_structured(self):
        result = warehouse_program_feasibility(
            site_area_m2=5000,
            building_target_m2=2000,
            program=[
                {"id":"storage","role":"storage","area_m2":1800,"scope":"indoor","hard":True},
                {"id":"receiving","role":"receiving","area_m2":500,"scope":"indoor","hard":True},
            ])
        self.assertEqual(result["status"], "INFEASIBLE_HARD_PROGRAM")
        self.assertEqual(result["hard_indoor_area_m2"], 2300)
        self.assertFalse(result["may_generate_layout"])

    def test_unknown_buildable_envelope_is_not_invented_from_site(self):
        result = warehouse_program_feasibility(
            site_area_m2=5000, building_target_m2=None,
            program=[{"id":"storage","role":"storage","area_m2":1200,"scope":"indoor","hard":False}])
        self.assertEqual(result["status"], "BUILDABLE_ENVELOPE_NOT_VERIFIED")
        self.assertIsNone(result["indoor_budget_m2"])
        self.assertFalse(result["may_generate_layout"])


if __name__ == "__main__":
    unittest.main()
