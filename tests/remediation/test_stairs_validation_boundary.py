"""Stair admission is strict for its contract, not a replacement for provenance."""
import copy
import unittest

from acs_plan_review import _geometry, PlanError
from acs_stairs import stair_connections, with_default_stairs
from tools.acs_plan_handoff import _require_explicit_object_geometry
from test_plan_handoff_object_geometry import residential_model
from test_stairs_geometry import model as stair_model


class StairValidationBoundary(unittest.TestCase):
    def malformed_non_stair(self):
        model=residential_model()
        room=model['floors']['ground']['rooms'][0]
        room['objects']={'sofa-a':room['objects'][0]}
        return model

    def test_unmarked_non_stair_collection_keeps_existing_provenance_boundary(self):
        model=self.malformed_non_stair();before=copy.deepcopy(model)
        self.assertEqual(_geometry(model)[0],[])
        # This helper deliberately leaves malformed collections to the existing
        # provenance admission; the unchanged full handoff regression asserts
        # INVALID_PROVENANCE and that no compiler call takes place.
        _require_explicit_object_geometry(model)
        self.assertEqual(model,before)

    def test_stair_forms_inside_malformed_collections_remain_fail_closed(self):
        for form in ('u_return','U_RETURN',None):
            for nested in (True,False):
                with self.subTest(form=form,nested=nested):
                    model=self.malformed_non_stair()
                    declared={'id':'stairs-a','kind':'stairs','form':form}
                    model['floors']['ground']['rooms'][0]['objects']=({'stairs-a':declared} if nested else declared)
                    self.assertTrue(any(i['code']=='STAIR_MODEL_INVALID' for i in _geometry(model)[0]))
                    with self.assertRaises(PlanError):_require_explicit_object_geometry(model)

    def test_stair_report_scope_and_object_provenance_markers_remain_strict(self):
        for marker in ('report','scope','instance','provenance'):
            with self.subTest(marker=marker):
                model=self.malformed_non_stair()
                if marker=='report':model['meta']['acs_stairs']={'generated_connections':999}
                elif marker=='scope':model['levels'][0]['stair_source_template']='forged'
                elif marker=='instance':model['levels'][0]['stair_template_instance']={}
                else:model['floors']['ground']['rooms'][0]['objects']['sofa-a']['stair_provenance']={'source':'system_default'}
                self.assertTrue(any(i['code'].startswith('STAIR_') for i in _geometry(model)[0]))
                with self.assertRaises(PlanError):_require_explicit_object_geometry(model)

    def test_real_stair_connections_still_reject_stale_elevations(self):
        model,_,_=with_default_stairs(stair_model())
        model['levels'][1]['elevation']=4
        self.assertTrue(any(i['code']=='STAIR_CONNECTION_STALE' for i in _geometry(model)[0]))
        with self.assertRaises(PlanError) as error:_require_explicit_object_geometry(model)
        self.assertEqual(error.exception.code,'STAIR_CONNECTION_STALE')

    def test_direct_stair_api_keeps_its_existing_strict_contract(self):
        with self.assertRaisesRegex(ValueError,'STAIR_MODEL_INVALID'):
            stair_connections(self.malformed_non_stair())


if __name__=='__main__':unittest.main()
