"""The brief, review and paid preflight share one supported metric vocabulary."""
import json, subprocess, unittest
from pathlib import Path
from acs_requirement_metrics import METRICS, unsupported_metrics
from acs_plan_review import PlanWorkspace
from acs_plan_bridge import existing_geometry_verifier
from test_geometry_delivery import model
ROOT=Path(__file__).resolve().parents[2]
class Vocabulary(unittest.TestCase):
    def test_browser_generated_contract_matches_source(self):
        js="import {requirementMetrics} from './public/app/generated/requirement-metrics.mjs';console.log(JSON.stringify(requirementMetrics));"
        got=json.loads(subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT,text=True))
        self.assertEqual(got,METRICS)
    def test_every_registered_metric_is_understood_by_review(self):
        for metric in METRICS:
            ws=PlanWorkspace();b=model();q=[{'id':'q','metric':metric,'expected':1,'source':'requested','evidence':'1'}]
            rev=ws.propose(b,brief='1',requirements=q,expected_head=None,note='synthetic')
            self.assertNotIn('REQUIREMENT_METRIC_NOT_SUPPORTED',[x['code'] for x in ws.review(rev.id)['issues']],metric)
    def test_feasible_area_can_be_conceptually_approved(self):
        b=model();b['levels']=[{'index':0,'template':'f','elevation':0}];b['floors']['f']['rooms'][0]['points']=[{'id':'light','type':'light','x':2.5,'z':2.5}]
        q=[{'id':'area','metric':'building_target_area_m2','expected':25,'source':'requested','evidence':'25'}]
        ws=PlanWorkspace(existing_geometry_verifier);rev=ws.propose(b,brief='25',requirements=q,expected_head=None,note='synthetic warehouse')
        review=ws.review(rev.id);self.assertTrue(review['can_approve'],review)
        ws.approve(rev.id,expected_head=rev.id,confirmed=True,acknowledge_concept_only=True,actor_label='synthetic reviewer')
    def test_unknown_is_disclosed(self):
        self.assertEqual(unsupported_metrics([{'metric':'permit_readiness'},{'metric':'level_count'}]),['permit_readiness'])
if __name__=='__main__':unittest.main()
