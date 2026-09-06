"""C18: no material-layer claim without an authored material layer usage."""
import unittest
from test_ifc_profile_positions import exported
import acs_bim as B


class IfcWallClass(unittest.TestCase):
    def test_general_walls_preserve_geometry_hosts_and_round_trip(self):
        result,step=exported();ents=step['entities']
        walls=[e for e in ents.values() if e['type'] in ('IFCWALL','IFCWALLSTANDARDCASE')]
        self.assertEqual(len(walls),4)
        self.assertEqual({e['type'] for e in walls},{'IFCWALL'})
        self.assertFalse(any(e['type'].startswith('IFCMATERIAL') for e in ents.values()))
        staged=B.stage_import(result['file']);self.assertTrue(staged['valid'],staged['issues'])
        mapped=[e for e in staged['staging']['entities'] if e['canonical_kind']=='wall']
        self.assertEqual(len(mapped),4)
        self.assertTrue(all(e['mapping_class']=='PARAMETRIC_MAPPED' for e in mapped))
        self.assertEqual(sorted((e['geometry']['x'],e['geometry']['z']) for e in mapped),
                         [(10,5),(10,5),(10,11),(16,5)])
        for wall in mapped:
            self.assertEqual(wall['geometry']['length'],6)
            self.assertEqual(wall['geometry']['height'],3)
            self.assertEqual(wall['geometry']['thickness'],.15)
            self.assertEqual(wall['world']['xyz'][2],7)
        voids=[e for e in ents.values() if e['type']=='IFCRELVOIDSELEMENT']
        self.assertEqual(len(voids),2)
        self.assertTrue(all(B._arg(e,4).n in {w['id'] for w in walls} for e in voids))

    def test_existing_standard_case_import_remains_available(self):
        result,_=exported()
        # Shape and axis subset remains readable for external StandardCase walls.
        text=result['file'].replace('=IFCWALL(', '=IFCWALLSTANDARDCASE(')
        staged=B.stage_import(text);self.assertTrue(staged['valid'],staged['issues'])
        walls=[e for e in staged['staging']['entities'] if e['canonical_kind']=='wall']
        self.assertEqual(len(walls),4)
        self.assertTrue(all(e['entity_type']=='IFCWALLSTANDARDCASE' for e in walls))
        self.assertTrue(all(e['geometry']['length']==6 and e['geometry']['height']==3 for e in walls))


if __name__=='__main__':unittest.main(verbosity=2)
