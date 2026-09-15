#!/usr/bin/env python3
"""#155 regression: do not invent warehouse vertical engineering facts in 2D."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_review import PlanError, _geometry
from acs_plan_stage_gate import (draft_geometry_admission,
    require_warehouse_vertical_for_downstream, warehouse_vertical_stage_gate)


def model(kind="warehouse"):
    return {"meta":{"type":kind}, "site":{"w":50.0,"d":100.0},
        "levels":[{"index":0,"name":"Ground","template":"ground"}],
        "floors":{"ground":{"rooms":[
            {"id":"storage","name":"Main storage","role":"storage",
             "rect":[5.0,10.0,40.0,50.0],"walls":"none"},
            {"id":"staging","name":"Staging","role":"staging",
             "rect":[5.0,62.0,40.0,18.0],"walls":"none"}]}}}


class WarehouseVerticalStageGateTests(unittest.TestCase):
    def test_draft_defers_only_the_three_vertical_unknowns(self):
        building=model(); issues,_=_geometry(building)
        self.assertEqual([i["code"] for i in issues],["DIMENSION_NOT_SPECIFIED"]*3)
        result=draft_geometry_admission(building,issues)
        self.assertEqual(result["blocking"],[])
        self.assertEqual([i["path"] for i in result["deferred"]],
                         ["/floor_height","/wall_h","/wall_t"])
        self.assertEqual(result["vertical"]["missing"],
                         ["floor_height","wall_h","wall_t"])

    def test_horizontal_failure_remains_blocking(self):
        building=model(); building["floors"]["ground"]["rooms"][0]["rect"]=[30,10,30,50]
        result=draft_geometry_admission(building,_geometry(building)[0])
        self.assertIn("OUTSIDE_SITE",[i["code"] for i in result["blocking"]])
        self.assertEqual([i["code"] for i in result["deferred"]],["DIMENSION_NOT_SPECIFIED"]*3)

    def test_non_warehouse_does_not_borrow_the_exception(self):
        building=model("residential")
        result=draft_geometry_admission(building,_geometry(building)[0])
        self.assertEqual(result["deferred"],[])
        self.assertEqual([i["code"] for i in result["blocking"]],["DIMENSION_NOT_SPECIFIED"]*3)

    def test_approval_and_3d_are_strict_until_values_are_explicit(self):
        building=model()
        for stage in ("APPROVAL","FROZEN_BASELINE","BIM_3D"):
            with self.assertRaises(PlanError) as caught:
                require_warehouse_vertical_for_downstream(building,stage)
            self.assertEqual(caught.exception.code,"DOWNSTREAM_GEOMETRY_NOT_SPECIFIED")
        building.update(floor_height=8.0,wall_h=8.0,wall_t=0.2)
        for stage in ("APPROVAL","BIM_3D"):
            require_warehouse_vertical_for_downstream(building,stage)

    def test_non_finite_values_never_count_as_resolved(self):
        building=model(); building.update(floor_height=float("nan"),wall_h=float("inf"),wall_t=-1)
        gate=warehouse_vertical_stage_gate(building,"APPROVAL")
        self.assertTrue(gate["blocking"])
        self.assertEqual(gate["missing"],["floor_height","wall_h","wall_t"])


if __name__ == "__main__": unittest.main(verbosity=2)
