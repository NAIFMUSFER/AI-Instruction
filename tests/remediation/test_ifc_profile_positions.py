"""C14: inspect actual IFC profile references, independently of round-trip mapping."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import acs_bim as B
import acs_authoring as A


def project():
    return A.create_project({"site":{"w":20,"d":25},"wall_h":3,"wall_t":.15,
        "floor_height":3.2,"levels":[{"index":0,"template":"g","elevation":7}],
        "floors":{"g":{"rooms":[{"id":"one","rect":[10,5,6,6],
          "doors":[{"edge":"N","offset":2,"width":1,"height":2.1}],
          "windows":[{"edge":"E","offset":3,"width":1.2,"height":1.1,"sill":1}],
          "objects":[{"kind":"stairs","x":1,"z":4,"w":1,"d":1}]}]}}})


def exported():
    p=project();before=copy.deepcopy(p)
    result=B.export_ifc(p,generated_at='2026-09-06T00:00:00Z')
    assert result['valid'],result['issues']
    parsed=B.parse_step(result['file']);assert parsed['valid'],parsed['issues']
    assert p==before,'IFC export must preserve the authored project'
    return result,parsed['step']


class IfcProfilePositions(unittest.TestCase):
    def test_all_nine_rectangular_profiles_have_two_dimensional_positions(self):
        _,step=exported()
        profiles=[e for e in step['entities'].values() if e['type']=='IFCRECTANGLEPROFILEDEF']
        self.assertEqual(len(profiles),9)  # space, four walls, slab, door, window, stairs
        for p in profiles:
            with self.subTest(profile=p['id']):
                pos=B._deref(step,B._arg(p,2));self.assertEqual(pos['type'],'IFCAXIS2PLACEMENT2D')
                location=B._deref(step,B._arg(pos,0));direction=B._deref(step,B._arg(pos,1))
                self.assertEqual(len(B._arg(location,0)),2)
                self.assertEqual(B._arg(direction,0),[1,0])

    def test_profile_offset_is_kept_and_product_placements_remain_3d(self):
        _,step=exported();space=next(e for e in step['entities'].values() if e['type']=='IFCSPACE')
        rep=B._deref(step,B._arg(space,6));shape=B._deref(step,B._arg(rep,2)[0])
        solid=B._deref(step,B._arg(shape,3)[0]);profile=B._deref(step,B._arg(solid,0))
        pos=B._deref(step,B._arg(profile,2));pt=B._deref(step,B._arg(pos,0))
        self.assertEqual(B._arg(pt,0),[3,3])
        placement=B._deref(step,B._arg(space,5));axes=B._deref(step,B._arg(placement,1))
        self.assertEqual(axes['type'],'IFCAXIS2PLACEMENT3D')
        self.assertEqual(B._arg(B._deref(step,B._arg(axes,0)),0),[10,5,0])
        self.assertEqual(B._deref(step,B._arg(solid,1))['type'],'IFCAXIS2PLACEMENT3D')

    def test_profile_axes_are_geometry_references_not_imported_products(self):
        result,step=exported()
        self.assertTrue(any(e['type']=='IFCAXIS2PLACEMENT2D' for e in step['entities'].values()))
        staged=B.stage_import(result['file'])
        self.assertTrue(staged['valid'])
        self.assertEqual([e['entity_type'] for e in staged['staging']['entities']
                          if e['entity_type']=='IFCAXIS2PLACEMENT2D'],[])


if __name__=='__main__':unittest.main(verbosity=2)
