#!/usr/bin/env python3
"""Regression contracts for measured plan-option comparison."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
from acs_plan_review import PlanError


def warehouse(storage_width=20.0, dock_count=2, rack_levels=4, rack_height=8.0):
    return {
        "meta": {"type": "warehouse", "name": "Option"},
        "site": {"w": 40.0, "d": 25.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "rect": [0.0, 0.0, 10.0, 10.0],
             "docks": [{"edge": "N", "offset": 2.0, "count": dock_count}],
             "lanes": [{"kind": "forklift", "x": 0.0, "z": 0.0, "w": 3.0, "d": 10.0}]},
            {"id": "storage", "role": "storage", "rect": [10.0, 0.0, storage_width, 20.0],
             "racks": [{"kind": "pallet", "x": 1.0, "z": 1.0, "w": 8.0, "d": 18.0,
                        "dir": "z", "rows": 2, "levels": rack_levels, "h": rack_height}]},
            {"id": "shipping", "role": "shipping", "rect": [30.0, 0.0, 10.0, 10.0]},
        ]}},
    }


def warehouse_with_expansion(*, intruding=False):
    model = warehouse()
    model["floors"]["ground"]["rooms"].append({
        "id": "expansion",
        "role": "expansion",
        "rect": [5.0, 5.0, 8.0, 8.0] if intruding else [0.0, 12.0, 8.0, 8.0],
    })
    return model


def residential():
    model = warehouse()
    model["meta"]["type"] = "residential"
    return model


class PlanOptionTests(unittest.TestCase):
    def test_measured_warehouse_deltas_use_first_option_as_reference(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse(storage_width=18.0, dock_count=2,
                                              rack_levels=4, rack_height=8.0)},
            {"id": "B", "model": warehouse(storage_width=20.0, dock_count=3,
                                              rack_levels=5, rack_height=7.0)},
        ], declared_program_receipt="program:sha256:abc")
        self.assertEqual(result["schema"], "acs.plan-options/1.0")
        self.assertEqual(result["reference_option_id"], "A")
        self.assertEqual(result["typology"], "warehouse")
        self.assertFalse(result["claims_best_option"])
        b = result["options"][1]["delta_from_reference"]
        self.assertEqual(b["scalar"]["space_rect_area_m2"], 40.0)
        self.assertEqual(b["scalar"]["dock_count"], 1)
        self.assertEqual(b["scalar"]["rack_declared_level_sum"], 1)
        self.assertEqual(b["scalar"]["rack_declared_height_max_m"], -1.0)
        self.assertEqual(b["mapping"]["zone_area_by_role_m2"]["storage"], 40.0)
        self.assertEqual(b["mapping"]["dock_count_by_edge"]["N"], 1)

    def test_warehouse_options_compare_explicit_route_zone_and_geometric_position_deltas(self):
        option_a = warehouse(storage_width=18.0, rack_levels=4)
        option_b = warehouse(storage_width=20.0, rack_levels=5)
        for model in (option_a, option_b):
            model["floors"]["ground"]["rooms"][1]["racks"][0]["bay"] = 2.0
        option_a["routes"] = [{
            "id": "receiving-to-storage",
            "kind": "material_flow",
            "from_role": "receiving",
            "to_role": "storage",
            "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]],
        }]
        option_b["routes"] = [{
            "id": "receiving-to-storage",
            "kind": "material_flow",
            "from_role": "receiving",
            "to_role": "storage",
            "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0]],
        }]

        result = O.compare_options([
            {"id": "A", "model": option_a},
            {"id": "B", "model": option_b},
        ], declared_program_receipt="program:warehouse:operational-options")
        delta = result["options"][1]["delta_from_reference"]

        self.assertEqual(delta["scalar"]["rack_geometric_bay_level_positions"], 18)
        self.assertEqual(delta["mapping"]["configured_route_length_by_id_m"]
                         ["receiving-to-storage"], -6.0)
        self.assertAlmostEqual(delta["mapping"]["zone_area_ratio_by_role"]["storage"],
                               0.02381, places=6)
        self.assertIn("configured_route_length_by_id_m",
                      delta["availability"]["mapping_comparable"])
        self.assertIn("rack_geometric_bay_level_positions",
                      delta["availability"]["scalar_comparable"])
        for row in result["options"]:
            self.assertIsNone(row["scorecard"]["metrics"]["storage_capacity_positions"])
            self.assertIsNone(row["scorecard"]["metrics"]["throughput_per_hour"])
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_warehouse_options_compare_explicit_mep_and_fire_zone_allocation_without_compliance_claims(self):
        option_a = warehouse()
        option_b = warehouse()
        option_a["floors"]["ground"]["rooms"].extend([
            {"id": "mep", "role": "mep", "rect": [0.0, 10.0, 5.0, 4.0]},
            {"id": "fire", "role": "fire_safety", "rect": [5.0, 10.0, 5.0, 4.0]},
        ])
        option_b["floors"]["ground"]["rooms"].extend([
            {"id": "mep", "role": "mep", "rect": [0.0, 10.0, 6.0, 4.0]},
            {"id": "fire", "role": "fire_safety", "rect": [6.0, 10.0, 4.0, 4.0]},
        ])

        result = O.compare_options([
            {"id": "A", "model": option_a},
            {"id": "B", "model": option_b},
        ], declared_program_receipt="program:warehouse:mep-fire-options")
        delta = result["options"][1]["delta_from_reference"]

        self.assertEqual(delta["mapping"]["zone_area_by_role_m2"]["mep"], 4.0)
        self.assertEqual(delta["mapping"]["zone_area_by_role_m2"]["fire_safety"], -4.0)
        self.assertAlmostEqual(delta["mapping"]["zone_area_ratio_by_role"]["mep"],
                               0.00625, places=6)
        self.assertAlmostEqual(delta["mapping"]["zone_area_ratio_by_role"]["fire_safety"],
                               -0.00625, places=6)
        self.assertIn("zone_area_by_role_m2",
                      delta["availability"]["mapping_comparable"])
        self.assertIn("zone_area_ratio_by_role",
                      delta["availability"]["mapping_comparable"])
        for row in result["options"]:
            self.assertIsNone(row["scorecard"]["metrics"]["fire_life_safety_compliance"])
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_missing_rack_height_makes_height_delta_unknown_not_zero(self):
        incomplete = warehouse()
        del incomplete["floors"]["ground"]["rooms"][1]["racks"][0]["h"]
        result = O.compare_options([
            {"id": "A", "model": warehouse(rack_height=8.0)},
            {"id": "B", "model": incomplete},
        ])
        self.assertIsNone(
            result["options"][1]["delta_from_reference"]["scalar"]
            ["rack_declared_height_max_m"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_comparison_availability_names_measured_and_unknown_dimensions(self):
        incomplete = warehouse()
        del incomplete["floors"]["ground"]["rooms"][1]["racks"][0]["h"]
        result = O.compare_options([
            {"id": "A", "model": warehouse(rack_height=8.0)},
            {"id": "B", "model": incomplete},
        ], declared_program_receipt="program:warehouse:availability")
        availability = result["options"][1]["delta_from_reference"]["availability"]
        self.assertIn("dock_count", availability["scalar_comparable"])
        self.assertIn("rack_declared_height_max_m", availability["scalar_unavailable"])
        self.assertIn("zone_area_by_role_m2", availability["mapping_comparable"])
        self.assertNotIn("rack_declared_height_max_m", availability["scalar_comparable"])
        self.assertTrue(availability["checks_comparable"])
        self.assertNotIn("score", availability)
        self.assertFalse(result["claims_best_option"])

    def test_check_status_transitions_are_exposed_without_quality_ranking(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse_with_expansion(intruding=False)},
            {"id": "B", "model": warehouse_with_expansion(intruding=True)},
        ], declared_program_receipt="program:warehouse:expansion")
        self.assertEqual(result["options"][0]["delta_from_reference"]["checks"], {})
        self.assertEqual(
            result["options"][1]["delta_from_reference"]["checks"],
            {"expansion_reserve_preservation": {"reference": "PASS", "target": "FAIL"}},
        )
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_unavailable_metrics_are_not_converted_into_scores(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": warehouse(storage_width=19.0)},
        ])
        for row in result["options"]:
            metrics = row["scorecard"]["metrics"]
            self.assertIsNone(metrics["storage_capacity_positions"])
            self.assertIsNone(metrics["throughput_per_hour"])
            self.assertIsNone(metrics["travel_distance_m"])
        self.assertNotIn("storage_capacity_positions",
                         result["options"][1]["delta_from_reference"]["scalar"])
        self.assertIn("PROGRAM_EQUIVALENCE_NOT_VERIFIED", result["disclosures"])

    def test_missing_complete_mapping_publishes_null_delta_not_partial_number(self):
        bad = warehouse()
        del bad["floors"]["ground"]["rooms"][0]["lanes"][0]["w"]
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": bad},
        ])
        self.assertIsNone(result["options"][1]["delta_from_reference"]["mapping"]["lane_area_by_kind_m2"])

    def test_new_mapping_key_is_compared_against_measured_zero(self):
        option_b = warehouse()
        option_b["floors"]["ground"]["rooms"][0]["lanes"].append(
            {"kind": "pedestrian", "x": 0.0, "z": 0.0, "w": 1.0, "d": 10.0})
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": option_b},
        ])
        self.assertEqual(result["options"][1]["delta_from_reference"]["mapping"]
                         ["lane_area_by_kind_m2"]["pedestrian"], 10.0)

    def test_different_typologies_are_rejected_instead_of_ranked(self):
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([
                {"id": "A", "model": warehouse()},
                {"id": "B", "model": residential()},
            ])
        self.assertEqual(ctx.exception.code, "OPTION_TYPOLOGY_MISMATCH")

    def test_unknown_typology_is_rejected(self):
        model = warehouse()
        model["meta"].pop("type")
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([{"id": "A", "model": model}, {"id": "B", "model": model}])
        self.assertEqual(ctx.exception.code, "OPTION_TYPOLOGY_UNKNOWN")

    def test_duplicate_ids_and_bad_counts_fail_closed(self):
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([{"id": "A", "model": warehouse()}])
        self.assertEqual(ctx.exception.code, "OPTION_COUNT")
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([
                {"id": "A", "model": warehouse()},
                {"id": "A", "model": warehouse()},
            ])
        self.assertEqual(ctx.exception.code, "DUPLICATE_OPTION")

    def test_site_and_level_differences_are_disclosed_not_scored_as_quality(self):
        b = warehouse()
        b["site"]["w"] = 42.0
        b["levels"].append({"index": 1, "template": "ground"})
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:one")
        self.assertFalse(result["same_site_geometry"])
        self.assertFalse(result["same_level_count"])
        self.assertIn("SITE_CONSTRAINT_DIFFERS", result["disclosures"])
        self.assertIn("LEVEL_COUNT_DIFFERS", result["disclosures"])
        self.assertFalse(result["program_receipt_authenticated"])

    def test_unknown_site_and_levels_are_not_reported_as_same_constraints(self):
        a, b = warehouse(), warehouse()
        a.pop("site")
        b.pop("site")
        a["levels"] = []
        b["levels"] = []
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:unknown-constraints")
        self.assertIsNone(result["same_site_geometry"])
        self.assertIsNone(result["same_level_count"])
        self.assertIsNone(result["same_level_configuration"])
        self.assertIn("SITE_CONSTRAINT_NOT_VERIFIED", result["disclosures"])
        self.assertIn("LEVEL_COUNT_NOT_VERIFIED", result["disclosures"])
        self.assertIn("LEVEL_CONFIGURATION_NOT_VERIFIED", result["disclosures"])
        self.assertNotIn("SITE_CONSTRAINT_DIFFERS", result["disclosures"])
        self.assertNotIn("LEVEL_COUNT_DIFFERS", result["disclosures"])

    def test_same_level_count_with_different_configuration_is_disclosed(self):
        a, b = warehouse(), warehouse()
        a["floors"]["upper"] = copy.deepcopy(a["floors"]["ground"])
        b["floors"]["upper"] = copy.deepcopy(b["floors"]["ground"])
        a["levels"] = [
            {"index": 0, "template": "ground"},
            {"index": 1, "template": "upper"},
        ]
        b["levels"] = [
            {"index": 0, "template": "ground"},
            {"index": 1, "template": "ground"},
        ]
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:level-configuration")
        self.assertTrue(result["same_level_count"])
        self.assertFalse(result["same_level_configuration"])
        self.assertIn("LEVEL_CONFIGURATION_DIFFERS", result["disclosures"])

    def test_level_configuration_comparison_ignores_list_order_but_not_identity(self):
        a, b = warehouse(), warehouse()
        a["floors"]["upper"] = copy.deepcopy(a["floors"]["ground"])
        b["floors"]["upper"] = copy.deepcopy(b["floors"]["ground"])
        a["levels"] = [
            {"index": 0, "template": "ground"},
            {"index": 1, "template": "upper"},
        ]
        b["levels"] = [
            {"index": 1, "template": "upper"},
            {"index": 0, "template": "ground"},
        ]
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:level-order")
        self.assertTrue(result["same_level_count"])
        self.assertTrue(result["same_level_configuration"])
        self.assertNotIn("LEVEL_CONFIGURATION_DIFFERS", result["disclosures"])

    def test_input_models_are_not_mutated(self):
        a, b = warehouse(), warehouse(storage_width=19.0)
        before_a, before_b = copy.deepcopy(a), copy.deepcopy(b)
        result = O.compare_options([{"id": "A", "model": a}, {"id": "B", "model": b}])
        self.assertEqual(a, before_a)
        self.assertEqual(b, before_b)
        self.assertNotEqual(result["options"][0]["model_hash"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
