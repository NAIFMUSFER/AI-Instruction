"""C09e: inspect profile geometry in real STEP, not only the exchange metadata."""
import copy
import json
import math
import unittest
from test_polygon_gltf import model, L
from test_polygon_architecture import adjacent_triangles
import acs_bim as B
import acs_authoring as A
import acs_polygon as G


def exported(building):
    project=A.create_project(building);before=copy.deepcopy(project)
    result=B.export_ifc(project,generated_at='2026-09-06T00:00:00Z')
    assert result['valid'],result['issues']
    parsed=B.parse_step(result['file']);assert parsed['valid'],parsed['issues']
    assert project==before,'export altered the project'
    return result,parsed['step']


def product_profiles(step,kind):
    profiles=[]
    for product in step['entities'].values():
        if product['type']!=kind:continue
        rep=B._deref(step,B._arg(product,6))
        for ref in B._arg(rep,2):
            shape=B._deref(step,ref)
            if B._arg(shape,1)!='Body':continue
            for ref in B._arg(shape,3):
                solid=B._deref(step,ref);profile=B._deref(step,B._arg(solid,0))
                if profile['type']=='IFCRECTANGLEPROFILEDEF':
                    w,d=B._arg(profile,3),B._arg(profile,4)
                    profiles.append({'kind':'rectangle','area':w*d,'ring':[[0,0],[w,0],[w,d],[0,d]]})
                elif profile['type']=='IFCARBITRARYCLOSEDPROFILEDEF':
                    curve=B._deref(step,B._arg(profile,2))
                    assert curve['type']=='IFCPOLYLINE'
                    ring=[B._arg(B._deref(step,p),0) for p in B._arg(curve,0)]
                    assert ring[0]==ring[-1],'STEP profile is not closed'
                    assert all(len(p)==2 for p in ring),'profile coordinates must be 2D'
                    profiles.append({'kind':'polygon','area':abs(G.signed_area(ring[:-1])),'ring':ring[:-1]})
                else:raise AssertionError(profile['type'])
    return profiles


class PolygonIfc(unittest.TestCase):
    def test_actual_space_and_slab_profiles_keep_l_area(self):
        result,step=exported(model())
        self.assertEqual(len(result['exchange']['walls']),6)
        for kind in ('IFCSPACE','IFCSLAB'):
            with self.subTest(kind=kind):
                profiles=product_profiles(step,kind)
                self.assertTrue(profiles)
                self.assertAlmostEqual(sum(p['area'] for p in profiles),20,places=5)
                self.assertTrue(all(p['kind']=='polygon' for p in profiles))

    def test_upper_slab_retains_core_hole(self):
        b=model(objects=[{'kind':'stairs','core_id':'A','x':1,'z':3,'w':1,'d':1}])
        b['levels'].append({'index':1,'template':'plan','elevation':10.2})
        _,step=exported(b)
        self.assertAlmostEqual(sum(p['area'] for p in product_profiles(step,'IFCSLAB')),39,places=5)

    def test_diagonal_shared_wall_and_opening_use_canonical_host(self):
        result,_=exported(adjacent_triangles());ex=result['exchange']
        self.assertEqual(len(ex['walls']),5)
        door=ex['doors'][0]
        self.assertAlmostEqual(door['x'],3,places=5);self.assertAlmostEqual(door['z'],3,places=5)
        host=next(w for w in ex['walls'] if w['canonical_id']==door['host_wall_id'])
        self.assertTrue(host.get('shared'))
        self.assertAlmostEqual(math.dist(host['start'],host['end']),math.sqrt(72),places=5)

    def test_negative_origin_preserved_with_local_profile_coordinates(self):
        b=model([[x-100,z+230] for x,z in L]);result,step=exported(b)
        self.assertEqual(result['exchange']['spaces'][0]['footprint'],[-100,230,6,6])
        ring=product_profiles(step,'IFCSPACE')[0]['ring']
        self.assertEqual(ring,L)
        self.assertEqual(result['exchange']['levels'][0]['elevation'],7)

    def test_reverse_edge_offset_is_reported_from_the_canonical_host_start(self):
        b=adjacent_triangles();b['floors']['plan']['rooms'][0]['doors'][0]['offset']=math.sqrt(2)
        result,_=exported(b);door=result['exchange']['doors'][0]
        self.assertAlmostEqual(door['x'],5,places=5)
        self.assertAlmostEqual(door['z'],1,places=5)
        self.assertAlmostEqual(door['offset'],math.sqrt(50),places=5)
        self.assertAlmostEqual(door['source_edge_offset'],math.sqrt(2),places=5)
        self.assertEqual(door['rotation_deg'],-45)

    def test_self_intersection_is_refused_without_rectangular_substitute(self):
        b=model([[0,0],[6,6],[0,6],[6,0]]);p=A.create_project(b);before=copy.deepcopy(p)
        result=B.export_ifc(p)
        self.assertFalse(result['valid']);self.assertIsNone(result['file'])
        self.assertEqual(p,before)

    def test_unresolved_or_out_of_edge_opening_is_not_dropped_or_relocated(self):
        for opening in ({'edge_index':99,'offset':1,'width':1},
                        {'edge_index':0,'width':1},
                        {'edge_index':0,'offset':5.8,'width':1}):
            with self.subTest(opening=opening):
                p=A.create_project(model(doors=[opening]));before=copy.deepcopy(p)
                result=B.export_ifc(p)
                self.assertFalse(result['valid']);self.assertIsNone(result['file'])
                self.assertEqual(p,before)


if __name__=='__main__':unittest.main(verbosity=2)
