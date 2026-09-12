"""Real ACS validator integration; run in the full repository, no LLM calls."""
import runpy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_review import PlanWorkspace, PlanError


def fixture():
    get_clean = runpy.run_path(str(Path(__file__).with_name('test_validate_topology.py')))['clean']
    m = get_clean()
    m.update(floor_height=3.2, wall_h=3.0, wall_t=.15)
    for floor in m['floors'].values():
        for room in floor['rooms']:
            if room['id'] == 'stair_1':
                room.update(role='stair', core_id='stairs-1')
            for kind in ('doors', 'windows'):
                for opening in room.setdefault(kind, []):
                    opening.update(w=.9 if kind == 'doors' else 1.2,
                                   h=2.1 if kind == 'doors' else 1.2)
    return m


class ExistingValidatorIntegration(unittest.TestCase):
    def candidate(self, m):
        ws = PlanWorkspace(existing_geometry_verifier)
        rev = ws.propose(m, brief='two levels', requirements=[{
            'id': 'levels', 'metric': 'level_count', 'source': 'requested',
            'evidence': 'two levels', 'expected': 2}], expected_head=None,
            note='synthetic integration fixture; not a client design')
        return ws, rev

    def test_real_validator_allows_known_clean_concept_then_exact_handoff(self):
        m = fixture()
        ws, rev = self.candidate(m)
        review = ws.review(rev.id)
        self.assertTrue(review['can_approve'], review)
        ws.approve(rev.id, expected_head=rev.id, actor_label='test-only',
                   confirmed=True, acknowledge_concept_only=True)
        self.assertEqual(ws.handoff(rev.id)['building'], m)

    def test_real_validator_blocks_misaligned_core(self):
        m = fixture(); m['floors']['f1']['rooms'][0]['rect'][0] += .9
        ws, rev = self.candidate(m)
        self.assertFalse(ws.review(rev.id)['can_approve'])
        with self.assertRaises(PlanError):
            ws.approve(rev.id, expected_head=rev.id, actor_label='test-only',
                       confirmed=True, acknowledge_concept_only=True)

    def test_omitted_opening_dimensions_remain_unverified(self):
        m = fixture(); del m['floors']['g']['rooms'][0]['doors'][0]['w']
        ws, rev = self.candidate(m)
        self.assertEqual(ws.review(rev.id)['scopes']['topology'], 'NOT_VERIFIED')
        self.assertFalse(ws.review(rev.id)['can_approve'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
