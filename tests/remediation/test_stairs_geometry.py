"""Canonical physical stair regression corpus; synthetic geometry, no compliance claim."""
import copy
import unittest
from unittest import mock

from acs_stairs import with_default_stairs, resolve_stair_geometry, stair_connections


def model(levels=None, edge='N'):
    return {'site': {'w': 4, 'd': 4}, 'wall_h': 3, 'wall_t': .2, 'floor_height': 3.2,
            'levels': levels or [{'index': 0, 'template': 'shared', 'elevation': 0},
                                 {'index': 1, 'template': 'shared', 'elevation': 3.2}],
            'floors': {'shared': {'rooms': [{'id': 'stairs', 'role': 'stairs', 'core_id': 'core',
                'rect': [0, 0, 4, 4], 'doors': [{'id': 'entry', 'edge': edge, 'offset': 2, 'width': 1, 'height': 2.1}],
                'windows': [], 'points': [], 'floor_color': '#cccccc', 'ceiling_color': '#ffffff'}]}}}


class PhysicalStairs(unittest.TestCase):
    def test_two_flights_midlanding_and_no_outbound_top(self):
        b = model(); original = copy.deepcopy(b)
        out, report, reason = with_default_stairs(b)
        self.assertIsNone(reason); self.assertEqual(b, original)
        self.assertEqual(report['generated_connections'], 1)
        connections = stair_connections(out)
        self.assertEqual(len(connections), 1)
        obj = connections[0]['object']; geometry = resolve_stair_geometry(obj)
        self.assertEqual([p['role'] for p in geometry['components']].count('tread'), 16)
        self.assertEqual([p['role'] for p in geometry['components']].count('mid_landing'), 1)
        self.assertEqual(obj['h'], 3.2)
        self.assertFalse(out['floors'][out['levels'][1]['template']]['rooms'][0].get('objects'))
        self.assertEqual(with_default_stairs(out)[0], out)

    def test_order_is_elevation_roof_excluded_and_unknowns_preserved(self):
        b = model([{'index': 9, 'template': 'shared', 'elevation': -3.2},
                   {'index': -2, 'template': 'shared', 'elevation': 0},
                   {'index': 3, 'template': 'shared', 'elevation': 3.6},
                   {'index': 10, 'template': 'deck', 'kind': 'roof', 'elevation': 6.8}])
        b['floors']['deck'] = {'rooms': [{'id': 'deck', 'rect': [0,0,4,4], 'walls': 'none'}]}
        out, _, _ = with_default_stairs(b)
        cs = stair_connections(out)
        self.assertEqual([(c['source_level_index'], c['target_level_index']) for c in cs], [(9,-2),(-2,3)])
        self.assertEqual([c['object']['h'] for c in cs], [3.2,3.6])
        self.assertEqual(out['floors']['deck'], b['floors']['deck'])

    def test_narrow_or_unstated_core_is_not_resized(self):
        b = model(); b['floors']['shared']['rooms'][0]['rect'] = [0,0,2,3]
        out, report, _ = with_default_stairs(b)
        self.assertEqual(report['generated_connections'], 0)
        self.assertEqual(report['unsupported'][0]['code'], 'STAIR_CORE_TOO_SMALL')
        self.assertEqual(out['floors'], b['floors'])

    def test_rotation_opening_and_arrival_preserved(self):
        for edge in ['N','E','S','W']:
            with self.subTest(edge=edge):
                out, _, _ = with_default_stairs(model(edge=edge))
                c = stair_connections(out)[0]
                self.assertEqual(c['target_level_index'], 1)
                self.assertAlmostEqual(c['opening'][2]*c['opening'][3], 1.9*2.9)
                self.assertAlmostEqual(c['arrival'][2]*c['arrival'][3], 1.9*.9)
                obj=copy.deepcopy(c['object']); obj['rot']=45
                with self.assertRaisesRegex(ValueError, 'STAIR_ROTATION_UNSUPPORTED'):
                    resolve_stair_geometry(obj)

    def test_stale_connection_fails_without_repair(self):
        out, _, _ = with_default_stairs(model())
        out['levels'][1]['elevation']=4
        with self.assertRaisesRegex(ValueError, 'STAIR_CONNECTION_STALE'):
            stair_connections(out)

    def test_actual_compiler_uses_u_components_and_physical_target_opening(self):
        import acs_compiler, acs_arch
        out, _, _ = with_default_stairs(model([{'index':9,'template':'shared','elevation':-3.2},
                                              {'index':-2,'template':'shared','elevation':0}]))
        obj=stair_connections(out)[0]['object']; builder=acs_compiler.Builder()
        acs_compiler.build_object(builder,obj,'stairs',2,2,-3.2,'F9','stairs',0)
        self.assertEqual(len(builder.parts),17)
        arch=acs_arch.compile_architecture(out)
        self.assertEqual([v['level_index'] for v in arch['voids']],[-2])
        self.assertEqual(arch['voids'][0]['rect'],stair_connections(out)[0]['opening'])

    def test_coverage_accepts_incoming_arrival_and_ignores_roof(self):
        from acs_roof import add_flat_roof_level
        from acs_plan_review import vertical_geometry_coverage
        out, _, _ = with_default_stairs(model())
        out,_=add_flat_roof_level(out)
        coverage=vertical_geometry_coverage(out,'PASS')
        self.assertEqual(coverage['geometry'],'PRESENT')
        self.assertEqual(coverage['physical_traversal'],'NOT_VERIFIED')

    def test_existing_nested_identity_and_authored_alias_are_preserved(self):
        b=model();room=b['floors']['shared']['rooms'][0]
        room['objects']=[{'id':'stairs_core_0_1','kind':'chair'}]
        out,_,_=with_default_stairs(b)
        ids=[o['id'] for o in out['floors']['shared']['rooms'][0]['objects']]
        self.assertEqual(ids,['stairs_core_0_1','stairs_core_0_1_2'])
        for declared in ({'name':'درج'},{'kind':'staircase'},{'name':'سلم'}):
            room['objects']=[{'id':'authored',**declared}]
            out,report,_=with_default_stairs(b)
            self.assertEqual(out['floors'],b['floors'])
            self.assertEqual(report['generated_connections'],0)
            self.assertEqual(report['unsupported'][0]['code'],'STAIR_AUTHORED_GEOMETRY_PRESERVED')

    def test_roof_shared_template_never_receives_stairs(self):
        b=model();b['levels'].append({'index':2,'template':'shared','elevation':6.4,'kind':'roof'})
        out,_,_=with_default_stairs(b)
        self.assertEqual(out['floors']['shared'],b['floors']['shared'])
        self.assertEqual(len(stair_connections(out)),1)

    def test_invalid_report_roof_connection_and_huge_numbers_fail_closed(self):
        b=model();b['meta']={'acs_stairs':{'generated_connections':999,'physical_traversal':'VERIFIED'}}
        self.assertEqual(with_default_stairs(b)[2],'STAIR_REPORT_INVALID')
        out,_,_=with_default_stairs(model());out['levels'][0]['kind']='roof'
        with self.assertRaisesRegex(ValueError,'STAIR_ROOF_ACCESS_UNSUPPORTED'):stair_connections(out)
        out,_,_=with_default_stairs(model());stair_connections(out)[0]['object']['x']=10**10000
        with self.assertRaisesRegex(ValueError,'STAIR_GEOMETRY_NOT_SPECIFIED'):stair_connections(out)

    def test_requirement_scope_covers_all_physical_variants_and_rejects_forgery(self):
        from acs_plan_review import _program
        b=model();brief='2 stairs at least16'
        req=[{'id':'count','metric':'room_count','template':'shared','role':'stairs','expected':2,'source':'requested','evidence':'2'},
             {'id':'area','metric':'min_room_area_m2','room':['shared','stairs'],'expected':16,'source':'requested','evidence':'16'}]
        self.assertEqual(_program(b,brief,req),[])
        out,_,_=with_default_stairs(b)
        self.assertEqual(_program(out,brief,req),[])
        out['floors'][out['levels'][1]['template']]['rooms'][0]['rect'][2]=3.9
        findings=_program(out,brief,req)
        self.assertTrue(any(i['requirement_id']=='area' and i['code']=='REQUIREMENT_MISMATCH' for i in findings))
        out['levels'][1].pop('stair_template_instance')
        self.assertEqual(_program(out,brief,req)[0]['code'],'STAIR_TEMPLATE_SCOPE_INVALID')

    def test_malformed_generation_shape_is_preserved_with_controlled_reason(self):
        cases=[]
        for key,value in [('floors',None),('floors',[]),('meta',[]),('levels',[None])]:
            b=model();b[key]=value;cases.append(b)
        for key,value in [('rooms',[None]),('rooms',None)]:
            b=model();b['floors']['shared'][key]=value;cases.append(b)
        for value in (None,{},[None]):
            b=model();b['floors']['shared']['rooms'][0]['objects']=value;cases.append(b)
        for b in cases:
            with self.subTest(model=b):
                before=copy.deepcopy(b);out,report,reason=with_default_stairs(b)
                self.assertEqual(reason,'STAIR_MODEL_INVALID');self.assertIsNone(report)
                self.assertIs(out,b);self.assertEqual(b,before)
        b=model();b['levels'][0].pop('elevation');b['levels'][0]['index']=10**400
        self.assertEqual(with_default_stairs(b)[2],'STAIR_LEVEL_INVALID')

    def test_declared_unsupported_form_never_falls_back_to_straight(self):
        import acs_compiler
        from acs_plan_review import _geometry
        from tools.acs_plan_handoff import _require_explicit_object_geometry
        for form in ('U_RETURN','spiral',None):
            with self.subTest(form=form):
                out,_,_=with_default_stairs(model());obj=stair_connections(out)[0]['object']
                obj['form']=form;out.pop('meta');obj.pop('stair_provenance')
                with self.assertRaisesRegex(ValueError,'STAIR_FORM_UNSUPPORTED'):stair_connections(out)
                self.assertTrue(any(i['code']=='STAIR_FORM_UNSUPPORTED' for i in _geometry(out)[0]))
                with self.assertRaises(ValueError):_require_explicit_object_geometry(out)
                with self.assertRaisesRegex(ValueError,'STAIR_FORM_UNSUPPORTED'):
                    acs_compiler.build_object(acs_compiler.Builder(),obj,'stairs',2,2,0,'F0','stairs',0)

    def test_stale_dimensions_and_moved_arrival_door_fail_at_review_and_handoff(self):
        from acs_plan_review import _geometry
        from tools.acs_plan_handoff import _require_explicit_object_geometry
        out,_,_=with_default_stairs(model())
        out['floors'][out['levels'][1]['template']]['rooms'][0]['doors'][0]['edge']='S'
        before=copy.deepcopy(out)
        self.assertTrue(any(i['code']=='STAIR_ENTRY_CHANGED' for i in _geometry(out)[0]))
        with self.assertRaises(ValueError):_require_explicit_object_geometry(out)
        self.assertEqual(out,before)

    def test_prospective_resources_reject_before_core_search_or_deepcopy(self):
        cases=[]
        # Compact source,1984 prospective connections: do not allocate or search
        # those chains merely to discover the final canonical document is huge.
        b=model([{'index':i,'template':'shared','elevation':i*3.2} for i in range(32)])
        sample=b['floors']['shared']['rooms'][0]
        b['floors']['shared']['rooms']=[{**copy.deepcopy(sample),'id':'s'+str(i),'core_id':'c'+str(i)} for i in range(64)]
        cases.append(b)
        # One core and large room content also exceeds prospective output size
        # after instancing, despite the compact source fitting admission limits.
        b=model([{'index':i,'template':'shared','elevation':i*3.2} for i in range(4)])
        b['floors']['shared']['rooms'][0]['description']='x'*100_000;cases.append(b)
        for b in cases:
            original=copy.deepcopy(b)
            with mock.patch('acs_stairs._cores',side_effect=AssertionError('core search preceded admission')), \
                 mock.patch('acs_stairs.copy.deepcopy',side_effect=AssertionError('cloning preceded admission')):
                out,report,reason=with_default_stairs(b)
            self.assertEqual(reason,'STAIR_RESOURCE_LIMIT')
            self.assertEqual(report['unsupported'],[{'code':'STAIR_RESOURCE_LIMIT'}])
            self.assertEqual(report['generated_connections'],0)
            self.assertIs(out,b);self.assertEqual(b,original)

    def test_resource_threshold_is_identical_for_integer_and_float_lexemes(self):
        from acs_stairs import _resource_limited, _levels
        integer=model();floating=model()
        room=floating['floors']['shared']['rooms'][0]
        room['rect']=[0.0,0.0,4.0,4.0];room['doors'][0]['offset']=2.0;room['doors'][0]['width']=1.0
        def limited(b,size):
            b['floors']['shared']['rooms'][0]['description']='x'*size
            return _resource_limited(b,_levels(b))
        low,high=0,300_000
        self.assertFalse(limited(integer,low));self.assertTrue(limited(integer,high))
        while high-low>1:
            mid=(low+high)//2
            if limited(integer,mid):high=mid
            else:low=mid
        for b in (integer,floating):
            self.assertFalse(limited(b,low));self.assertTrue(limited(b,high))
        # A no-core warehouse has no expansion to budget and is never deep-copied
        # just to attach the unsupported-geometry disclosure.
        b=model();b['floors']['shared']['rooms'][0].pop('role')
        original_deepcopy=copy.deepcopy
        def bounded_copy(value):
            self.assertIsNot(value,b)
            self.assertIsNot(value,b['floors'])
            return original_deepcopy(value)
        with mock.patch('acs_stairs.copy.deepcopy',side_effect=bounded_copy):
            out,report,_=with_default_stairs(b)
        self.assertIs(out['floors'],b['floors']);self.assertNotIn('meta',b)
        self.assertEqual(report['unsupported'][0]['code'],'STAIR_CORE_NOT_DECLARED')

if __name__ == '__main__': unittest.main()
