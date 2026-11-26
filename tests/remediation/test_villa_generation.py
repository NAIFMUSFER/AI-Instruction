"""The villa prompt carries the confirmed program; the repair keeps villas livable.

Offline: the model is stubbed (no key, no network). The fixtures are the
sanitized live villa job bc82d27f and a livable villa on the same plot
(fixtures/villa_program). The outline call shows the planning prompt and policy
a villa generation sends; a resumed layout shows the repair stage receiving the
villa findings and, when it cannot fix them, the job still saving a plan whose
review states why it is not approvable.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acs_residential_generation as R
import acs_understand as U
import acs_workspace_service as S
from acs_provider_budget import consume
from acs_workspace_progress import planning_system
from test_villa_program import PLOT, codes, fixture, review


# ── offline generation: the model is stubbed ────────────────────────────────
class Stop(Exception):
    pass


def layout_of(model):
    """The pre-openings layout a generation holds before the detail stage."""
    keep = ('id', 'name', 'role', 'rect', 'walls', 'wall_h', 'unit_id', 'core_id')
    return {t: {'rooms': [{k: r[k] for k in keep if k in r} for r in model['floors'][t]['rooms']]}
            for t in ('ground', 'upper')}


def building_of(model):
    return {'site': dict(model['site']), 'floor_height': 3.2, 'wall_h': 3.0, 'wall_t': 0.2,
            'levels': [{'id': 'L0', 'index': 0, 'template': 'ground'}, {'id': 'L1', 'index': 1, 'template': 'upper'}],
            'floors': layout_of(model), 'meta': {}}


class Provider:
    """Stands in for the model: repairs with ``repair`` and details from ``openings``."""
    def __init__(self, openings, repair=None):
        self.openings, self.repair, self.calls = openings, repair, []

    def __call__(self, text, **kwargs):
        stage = kwargs['stage']
        self.calls.append((stage, text, kwargs.get('system_override') or planning_system(stage)))
        consume()
        if stage == 'repair':
            return json.dumps({'floors': self.repair} if self.repair is not None else {}, ensure_ascii=False)
        if stage == 'detail':
            context = json.loads(text)
            rooms = {r['id']: r for r in self.openings['floors'][context['target_template']]['rooms']}
            return json.dumps({'rooms': [{k: rooms[i].get(k, []) for k in ('doors', 'windows', 'points')} | {'id': i}
                                         for i in context['requested_ids']]}, ensure_ascii=False)
        raise Stop(stage)


class VillaGeneration(unittest.TestCase):
    def setUp(self):
        self.live, self.livable = fixture('job_bc82d27f'), fixture('villa_livable')
        self.brief, self.rows = self.livable['brief'], self.livable['requirements']

    def test_the_villa_prompt_and_policy_carry_the_confirmed_program(self):
        provider = Provider(self.livable['model'])
        with patch.object(U, 'call_llm', side_effect=provider), self.assertRaises(Stop):
            S.generate_plan_candidate(self.brief, self.rows, 'B', 8, plot=PLOT)
        stage, prompt, policy = provider.calls[0]
        self.assertEqual(stage, 'outline')
        for text in ('برنامج الفيلا المؤكد', '- غرف النوم: 4 غرف مستقلة role=bedroom، منها 1 بحمام خاص',
                     '- الحمامات ودورات المياه: 5 بالضبط role=bathroom', 'دورة مياه الضيوف في الدور الأرضي',
                     '«غرف النوم»', 'المطبخ على جدار خارجي', '- غرفة خادمة: لا.'):
            self.assertIn(text, prompt)
        self.assertTrue(policy.startswith(R.PLANNING_SYSTEM + R.SINGLE_DWELLING_PLANNING))
        self.assertIn('Every bedroom is its own room', policy)

    def test_apartment_prompts_are_unchanged(self):
        rows = [{'id': m, 'metric': m, 'expected': v, 'confirmed': True, 'source': 'inferred'}
                for m, v in (('site_width_m', 20), ('site_depth_m', 25), ('level_count', 3), ('unit_count', 6))]
        provider = Provider(self.livable['model'])
        with patch.object(U, 'call_llm', side_effect=provider), self.assertRaises(Stop):
            S.generate_plan_candidate('عمارة سكنية بست شقق', rows, 'A', 8)
        stage, prompt, policy = provider.calls[0]
        self.assertEqual(policy, R.PLANNING_SYSTEM)
        self.assertNotIn('برنامج الفيلا', prompt)
        self.assertNotIn(R.VILLA_ROOM_PROGRAM, prompt)

    def test_the_repair_turns_the_live_layout_into_the_livable_villa(self):
        provider = Provider(self.livable['model'], repair=layout_of(self.livable['model']))
        brief, rows = self.brief, self.rows
        with patch.object(U, 'call_llm', side_effect=provider):
            out = S.generate_plan_candidate(brief, rows, 'B', 8, plot=PLOT,
                                            resume={'kind': 'layout', 'building': building_of(self.live['model'])})
        self.assertEqual([c[0] for c in provider.calls], ['repair', 'detail', 'detail'])
        context = json.loads(provider.calls[0][1])
        found = {f['code'] for f in context['findings']}
        self.assertTrue({'VILLA_AGGREGATE_ROOM', 'VILLA_NO_BATHROOM', 'REQUIREMENT_MISMATCH'} <= found, found)
        self.assertIn('Correct every VILLA_* finding', provider.calls[0][2])
        self.assertIn('en-suite bathroom opens only into the master', provider.calls[1][2])
        result = review(out['building'], brief, rows)
        self.assertTrue(result['can_approve'], result['issues'][:4])

    def test_villa_findings_never_fail_the_job(self):
        # A repair that answers nothing usable keeps the layout; the review says why.
        provider = Provider(self.live['model'])
        with patch.object(U, 'call_llm', side_effect=provider):
            out = S.generate_plan_candidate(self.brief, self.rows, 'B', 8, plot=PLOT,
                                            resume={'kind': 'layout', 'building': building_of(self.live['model'])})
        self.assertEqual([c[0] for c in provider.calls], ['repair', 'detail', 'detail'])
        result = review(out['building'], self.brief, self.rows)
        self.assertFalse(result['can_approve'])
        self.assertIn('VILLA_AGGREGATE_ROOM', codes(result['issues']))
        # Without budget for both a repair and the openings, no repair is spent.
        provider = Provider(self.live['model'])
        with patch.object(U, 'call_llm', side_effect=provider):
            S.generate_plan_candidate(self.brief, self.rows, 'B', 2, plot=PLOT,
                                      resume={'kind': 'layout', 'building': building_of(self.live['model'])})
        self.assertEqual([c[0] for c in provider.calls], ['detail', 'detail'])


if __name__ == '__main__':
    unittest.main()
