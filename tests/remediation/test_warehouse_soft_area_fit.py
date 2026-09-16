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

if __name__=='__main__': unittest.main()
