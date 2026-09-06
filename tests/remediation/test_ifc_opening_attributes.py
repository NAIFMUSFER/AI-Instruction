"""C15: optional IFC4 attributes still require a positional $ in STEP."""
import unittest
from test_ifc_profile_positions import exported


class IfcOpeningAttributes(unittest.TestCase):
    def test_door_and_window_each_serialize_all_thirteen_ifc4_attributes(self):
        _,step=exported()
        openings=[e for e in step['entities'].values() if e['type'] in ('IFCDOOR','IFCWINDOW')]
        self.assertEqual({e['type'] for e in openings},{'IFCDOOR','IFCWINDOW'})
        for e in openings:
            with self.subTest(entity=e['type']):
                self.assertEqual(len(e['args']),13)

    def test_unstated_types_remain_unknown_after_stated_height_and_width(self):
        _,step=exported()
        for kind,height,width in [('IFCDOOR',2.1,1),('IFCWINDOW',1.1,1.2)]:
            with self.subTest(entity=kind):
                e=next(e for e in step['entities'].values() if e['type']==kind)
                self.assertAlmostEqual(e['args'][8],height)
                self.assertAlmostEqual(e['args'][9],width)
                self.assertEqual(e['args'][10:],[None,None,None])


if __name__=='__main__':unittest.main(verbosity=2)
