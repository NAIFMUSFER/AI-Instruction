#!/usr/bin/env python3
import copy, math, unittest
from acs_plan_review import PlanError
from warehouse_program_feasibility import generated_indoor_area
from warehouse_soft_area_fit import fit_soft_area


def model():
    return {'site':{'w':50.0,'d':100.0},'floor_height':8.0,'wall_h':7.5,'wall_t':0.2,
      'levels':[{'id':'L0','index':0,'template':'ground','elevation':0.0}],
      'floors':{'ground':{'rooms':[
        {'id':'storage','role':'storage','rect':[0,0,40,50]},
        {'id':'receiving','role':'receiving','rect':[0,0,20,20]},
        {'id':'admin','role':'admin','rect':[0,0,10,20]}]}},'meta':{'type':'warehouse'}}

class Fit(unittest.TestCase):
 def test_soft_2600_fits_2000_without_identity_loss(self):
    b=model(); out=fit_soft_area(b,[],2000)
    self.assertLessEqual(generated_indoor_area(out),2000.1)
    self.assertEqual([(r['id'],r['role']) for r in b['floors']['ground']['rooms']],[(r['id'],r['role']) for r in out['floors']['ground']['rooms']])
    self.assertEqual(out['meta']['acs_stage_diagnostics'][-1]['code'],'WAREHOUSE_SOFT_AREA_FIT')
 def test_confirmed_role_minimum_survives(self):
    q=[{'id':'req-storage','metric':'min_space_area_by_role_m2','role':'storage','expected':1500,'confirmed':True}]
    out=fit_soft_area(model(),q,2000); storage=next(r for r in out['floors']['ground']['rooms'] if r['role']=='storage')
    self.assertGreaterEqual(storage['rect'][2]*storage['rect'][3],1499.9)
    self.assertIn('req-storage',out['meta']['acs_stage_diagnostics'][-1]['requirement_ids'])
 def test_hard_minima_over_target_fail_without_mutation(self):
    b=model(); before=copy.deepcopy(b); q=[{'id':'r','metric':'min_space_area_by_role_m2','role':'storage','expected':2100,'confirmed':True}]
    with self.assertRaises(PlanError) as c: fit_soft_area(b,q,2000)
    self.assertEqual(c.exception.code,'INFEASIBLE_HARD_PROGRAM'); self.assertEqual(b,before)
 def test_no_target_is_byte_equivalent_object(self):
    b=model(); self.assertIs(fit_soft_area(b,[],None),b)

class OccupiedAreaContract(unittest.TestCase):
    @staticmethod
    def warehouse():
        candidate = model()
        room = candidate["floors"]["ground"]["rooms"][0]
        room.update(rect=[0, 0, 10, 8], walls="none",
                    points=[{"id": "L", "type": "light", "x": 2, "z": 2}])
        candidate["floors"]["ground"]["rooms"] = [room]
        return candidate

    def test_fitted_dimensions_satisfy_confirmed_area_in_approval(self):
        from acs_plan_bridge import existing_geometry_verifier
        from acs_plan_review import PlanWorkspace
        for target in (63, 63.12345678, 79.9999995):
            with self.subTest(target=target):
                evidence = str(target)
                requirements = [{"id": "area", "metric": "building_target_area_m2",
                                 "expected": target, "source": "requested", "evidence": evidence}]
                fitted = fit_soft_area(self.warehouse(), requirements, target)
                workspace = PlanWorkspace(existing_geometry_verifier)
                revision = workspace.propose(fitted, brief=evidence, requirements=requirements,
                                             expected_head=None, note="synthetic fitted warehouse")
                review = workspace.review(revision.id)
                self.assertTrue(review["can_approve"], review["issues"])
                workspace.approve(revision.id, expected_head=revision.id, confirmed=True,
                                  acknowledge_concept_only=True, actor_label="synthetic reviewer")

    def test_role_minimum_uses_the_same_precision_as_the_building_target(self):
        from acs_plan_review import _program
        target = 63.12345625
        evidence = str(target)
        rows = [
            {"id": "area", "metric": "building_target_area_m2", "expected": target,
             "source": "requested", "evidence": evidence},
            {"id": "storage", "metric": "min_space_area_by_role_m2", "role": "storage",
             "expected": target, "source": "requested", "evidence": evidence},
        ]
        fitted = fit_soft_area(self.warehouse(), rows, target)
        self.assertEqual(_program(fitted, evidence, rows), [])

    def test_explicit_roof_does_not_reduce_occupied_area_budget(self):
        candidate = self.warehouse()
        candidate["levels"].extend([
            {"index": 1, "template": "ground", "elevation": 8},
            {"index": 2, "template": "deck", "kind": "roof", "elevation": 16},
        ])
        candidate["floors"]["deck"] = {"rooms": [{"id": "deck", "rect": [0, 0, 10, 8]}]}
        self.assertEqual(generated_indoor_area(candidate), 160)
        self.assertIs(fit_soft_area(candidate, [], 160), candidate)
        fitted = fit_soft_area(candidate, [], 120)
        self.assertAlmostEqual(generated_indoor_area(fitted), 120, places=8)
        self.assertEqual(fitted["floors"]["deck"], candidate["floors"]["deck"])

    def test_partial_or_invalid_levels_cannot_establish_total_area(self):
        from acs_plan_scorecard import measure_plan
        for extra in ({"index": 1, "template": "missing"}, {"index": 0, "template": "ground"}):
            with self.subTest(level=extra):
                candidate = self.warehouse()
                candidate["levels"].append(extra)
                self.assertIsNone(generated_indoor_area(candidate))
                self.assertIsNone(measure_plan(candidate)["metrics"]["space_rect_area_m2"])

if __name__=='__main__': unittest.main()
