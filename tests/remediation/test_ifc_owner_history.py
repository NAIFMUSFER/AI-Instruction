"""C16: an export timestamp is not evidence of an authored modification history."""
import unittest
from test_ifc_profile_positions import project
import acs_bim as B


class IfcOwnerHistory(unittest.TestCase):
    def test_missing_modification_history_is_not_claimed_as_added(self):
        for stamp in (None,'2026-09-06T00:00:00Z'):
            with self.subTest(export_timestamp=stamp):
                p=project();result=B.export_ifc(p,generated_at=stamp)
                self.assertTrue(result['valid'])
                step=B.parse_step(result['file'])['step']
                owners=[e for e in step['entities'].values() if e['type']=='IFCOWNERHISTORY']
                self.assertEqual(len(owners),1)
                owner=owners[0]
                self.assertIsNone(B._arg(owner,4),'do not invent an authored modification date')
                self.assertIn(B._enum(B._arg(owner,3)),(None,'NOTDEFINED','NOCHANGE'))


if __name__=='__main__':unittest.main(verbosity=2)
