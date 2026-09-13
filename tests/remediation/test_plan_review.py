"""Plan-review contracts; synthetic fixtures, no provider/network/auth claims."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P

BRIEF = 'أرض 20 في 25، دورين، غرفة نوم في كل دور.'


def model():
    return {'site': {'w': 20, 'd': 25}, 'floor_height': 3.2, 'wall_h': 3, 'wall_t': .15,
            'meta': {'type': 'residential'},
            'levels': [{'index': 0, 'template': 'g'}, {'index': 1, 'template': 'g'}],
            'floors': {'g': {'rooms': [
                {'id': 'bed', 'role': 'bedroom', 'rect': [0, 0, 4, 4],
                 'doors': [{'id': 'door_1', 'edge': 'E', 'offset': 1, 'w': .9}]},
                {'id': 'hall', 'role': 'corridor', 'rect': [4, 0, 2, 4]}
            ]}}}


def program():
    return [
        {'id': 'width', 'metric': 'site_width_m', 'expected': 20,
         'source': 'requested', 'evidence': '20'},
        {'id': 'floors', 'metric': 'level_count', 'expected': 2,
         'source': 'requested', 'evidence': 'دورين'},
        {'id': 'beds', 'metric': 'room_count', 'role': 'bedroom', 'expected': 2,
         'source': 'requested', 'evidence': 'غرفة نوم في كل دور'}]


def verified(_):
    # Controlled verifier, NOT evidence of real architectural/topological validity.
    return {'scopes': {'topology': 'PASS', 'vertical_circulation': 'PASS'}, 'issues': []}


class PlanReviewTests(unittest.TestCase):
    def setUp(self):
        self.ws = P.PlanWorkspace(verified)
        self.rev = self.ws.propose(model(), brief=BRIEF, requirements=program(),
                                   expected_head=None, note='Initial proposal')

    def propose(self, value=None, **kw):
        return self.ws.propose(model() if value is None else value, brief=BRIEF,
                               requirements=kw.pop('requirements', program()),
                               expected_head=kw.pop('expected_head', self.ws.head),
                               note='Engineer requested change', **kw)

    def approve(self, revision=None, **kw):
        rid = revision or self.ws.head
        options = dict(expected_head=self.ws.head, actor_label='test-engineer',
                       confirmed=True, acknowledge_concept_only=True)
        options.update(kw)
        return self.ws.approve(rid, **options)

    def assertCode(self, code, action):
        with self.assertRaises(P.PlanError) as got:
            action()
        self.assertEqual(got.exception.code, code)

    def codes(self, rev):
        return {x['code'] for x in self.ws.review(rev.id)['issues']}

    def test_initial_draft_never_has_implicit_approval(self):
        self.assertIsNone(self.ws.baseline)
        self.assertCode('APPROVAL_REQUIRED', lambda: self.ws.handoff(self.rev.id))

    def test_approved_handoff_is_exact_original_without_generation(self):
        self.approve()
        out = self.ws.handoff(self.rev.id)
        self.assertEqual(out['building'], model())
        self.assertEqual(P.digest(out['building']), out['baseline']['model_hash'])
        self.assertEqual(len(out['source_map']), 4)
        self.assertEqual({x['level_index'] for x in out['source_map']}, {0, 1})

    def test_no_regulatory_or_structural_approval_claim(self):
        review = self.ws.review(self.rev.id)
        self.assertFalse(review['construction_approved'])
        self.assertEqual(review['scopes']['regulatory_compliance'], 'NOT_VERIFIED')
        self.assertEqual(review['scopes']['structural_safety'], 'NOT_VERIFIED')
        self.assertEqual(self.approve().scope, 'CONCEPTUAL_DESIGN_ONLY')

    def test_unknown_commercial_metrics_are_null_not_zero(self):
        metrics = self.ws.review(self.rev.id)['metrics']
        self.assertEqual(metrics['space_rect_area_m2'], 48)
        self.assertEqual(metrics['space_instance_count'], 4)
        for key in ('gross_floor_area_m2', 'net_floor_area_m2', 'efficiency'):
            self.assertIsNone(metrics[key])

    def test_new_candidate_keeps_previous_approved_baseline(self):
        receipt = self.approve()
        original = self.ws.handoff(self.rev.id)
        changed = model()
        changed['floors']['g']['rooms'][0]['rect'][2] = 3
        new = self.propose(changed)
        self.assertEqual(self.ws.baseline, receipt.revision_id)
        self.assertEqual(self.ws.handoff(self.rev.id), original)
        self.assertCode('APPROVAL_REQUIRED', lambda: self.ws.handoff(new.id))
        self.approve(new.id)
        self.assertEqual(self.ws.baseline, new.id)
        self.assertEqual(self.ws.handoff(self.rev.id), original)

    def test_revisions_have_monotonic_versions_and_parent(self):
        next_rev = self.propose()
        self.assertEqual(next_rev.number, 2)
        self.assertEqual(next_rev.parent_id, self.rev.id)
        self.assertEqual([r['version'] for r in self.ws.history()], [1, 2])

    def test_duplicate_approval_is_idempotent(self):
        self.assertEqual(self.approve(), self.approve())
        self.assertEqual(len(self.ws.history()), 1)

    def test_explicit_confirmation_required(self):
        for value in (False, None, 1, 'yes'):
            with self.subTest(value=value):
                self.assertCode('EXPLICIT_APPROVAL_REQUIRED', lambda: self.approve(confirmed=value))
        self.assertCode('EXPLICIT_APPROVAL_REQUIRED', lambda: self.approve(acknowledge_concept_only=False))
        self.assertCode('EXPLICIT_APPROVAL_REQUIRED', lambda: self.approve(actor_label=''))

    def test_stale_proposal_and_approval_are_rejected(self):
        old = self.ws.head
        self.propose()
        self.assertCode('STALE_REVISION', lambda: self.propose(expected_head=old))
        self.assertCode('STALE_REVISION', lambda: self.approve(self.rev.id, expected_head=old))

    def test_concurrent_proposals_have_one_winner(self):
        head = self.ws.head
        def attempt(_):
            try:
                return self.propose(expected_head=head).id
            except P.PlanError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(results.count('STALE_REVISION'), 1)
        self.assertEqual(len(self.ws.history()), 2)

    def test_input_output_and_history_are_detached(self):
        raw = model()
        rev = self.propose(raw)
        raw['site']['w'] = 50
        rev.model['site']['w'] = 60
        with self.assertRaises(FrozenInstanceError):
            rev.brief = 'changed'
        self.approve(rev.id)
        self.ws.handoff(rev.id)['building']['site']['w'] = 70
        self.ws.history()[0]['state'] = 'BROKEN'
        self.assertEqual(rev.model['site']['w'], 20)
        self.assertEqual(self.ws.handoff(rev.id)['building']['site']['w'], 20)
        self.assertEqual(self.ws.history()[0]['state'], 'DRAFT')

    def test_metadata_program_and_locks_are_bound_into_receipt(self):
        base = self.rev.content_hash
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        self.assertNotEqual(self.ws.get(self.ws.head).content_hash, base)
        self.assertEqual(self.ws.get(self.ws.head).model_hash, self.rev.model_hash)

    def test_moved_resized_renamed_removed_locked_room_rejected(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        changed_models = []
        for field, value in [('rect', [1, 0, 3, 4]), ('id', 'renamed'), ('role', 'kitchen'),
                             ('doors', [])]:
            m = model(); m['floors']['g']['rooms'][0][field] = value; changed_models.append(m)
        m = model(); m['floors']['g']['rooms'].pop(0); changed_models.append(m)
        for m in changed_models:
            with self.subTest(model=m):
                self.assertCode('LOCK_VIOLATION', lambda: self.propose(m))
        self.assertEqual(len(self.ws.history()), 2)

    def test_lock_cannot_be_bypassed_by_changing_enclosing_geometry(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        for key, val in [('floor_height', 4), ('site', {'w': 21, 'd': 25}),
                         ('levels', [{'index': 2, 'template': 'g'}])]:
            m = model(); m[key] = val
            self.assertCode('LOCK_CONTEXT_CHANGED', lambda: self.propose(m))
        m = model(); m['floors']['g']['offset_x'] = 20
        self.assertCode('LOCK_CONTEXT_CHANGED', lambda: self.propose(m))

    def test_unlocked_room_can_change_but_original_is_preserved(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        m = model(); m['floors']['g']['rooms'][1]['rect'][2] = 3
        new = self.propose(m)
        self.assertEqual(new.model['floors']['g']['rooms'][1]['rect'][2], 3)
        self.assertEqual(self.rev.model['floors']['g']['rooms'][1]['rect'][2], 2)

    def test_unlock_is_explicit_revision_then_changes_are_possible(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        self.ws.set_room_lock(('g', 'bed'), locked=False, expected_head=self.ws.head)
        m = model(); m['floors']['g']['rooms'][0]['rect'][2] = 3
        self.assertEqual(self.propose(m).number, 4)

    def test_template_scoped_identity_survives_reordering(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        m = model(); m['floors']['g']['rooms'].reverse()
        new = self.propose(m)
        self.assertEqual(new.locked_rooms, (('g', 'bed'),))

    def test_unknown_room_cannot_be_locked(self):
        self.assertCode('ROOM_NOT_FOUND', lambda: self.ws.set_room_lock(('g', 'missing'), locked=True, expected_head=self.ws.head))

    def test_missing_verifier_is_fail_closed(self):
        self.ws._verifier = None
        self.assertFalse(self.ws.review(self.rev.id)['can_approve'])
        self.assertCode('PLAN_NOT_READY', self.approve)

    def test_failing_mutating_and_malformed_verifiers_are_fail_closed(self):
        def throwing(m): raise RuntimeError('internal detail must not leak')
        def mutating(m): m['site']['w'] = 100; return verified(m)
        for fn in (throwing, mutating, lambda _: {}, lambda _: {'scopes': {}, 'issues': []},
                   lambda _: {'scopes': {'topology': 'PASS', 'vertical_circulation': 'PASS'}, 'issues': [None]}):
            self.ws._verifier = fn
            report = self.ws.review(self.rev.id)
            self.assertFalse(report['can_approve'])
            self.assertIn('VERIFICATION_UNAVAILABLE', {x['code'] for x in report['issues']})
            self.assertNotIn('internal detail', json.dumps(report))
            self.assertEqual(self.rev.model, model())

    def test_verifier_issue_blocks_approval_even_with_pass_scope(self):
        self.ws._verifier = lambda _: dict(verified(_), issues=[{'code': 'ISOLATED_ROOM'}])
        self.assertCode('PLAN_NOT_READY', self.approve)

    def test_baseline_tampering_detected_before_handoff(self):
        self.approve()
        changed = model(); changed['site']['w'] = 21
        self.ws._revisions[self.rev.id] = replace(self.rev, model_json=P.canonical(changed))
        self.assertCode('BASELINE_CHANGED', lambda: self.ws.handoff(self.rev.id))

    def test_empty_program_and_missing_sources_block_approval(self):
        for requirements, code in [([], 'PROGRAM_NOT_CONFIRMED'),
                                   ([dict(program()[0], evidence='not in brief')], 'MISSING_SOURCE_EVIDENCE')]:
            rev = self.propose(requirements=requirements)
            self.assertIn(code, self.codes(rev))
            self.assertCode('PLAN_NOT_READY', self.approve)

    def test_inference_needs_explicit_confirmation(self):
        req = dict(program()[0], source='inferred', confirmed=False)
        rev = self.propose(requirements=[req])
        self.assertIn('INFERENCE_NOT_CONFIRMED', self.codes(rev))
        req['confirmed'] = True
        rev = self.propose(requirements=[req])
        self.assertNotIn('INFERENCE_NOT_CONFIRMED', self.codes(rev))

    def test_unknown_requirement_is_not_replaced_by_zero(self):
        req = dict(program()[0], expected=None, source='unknown')
        rev = self.propose(requirements=[req])
        self.assertIn('REQUIREMENT_NOT_SPECIFIED', self.codes(rev))
        self.assertIsNone(json.loads(rev.requirements_json)[0]['expected'])

    def test_program_counts_instances_not_just_templates(self):
        req = dict(program()[2], expected=1)
        rev = self.propose(requirements=[req])
        self.assertIn('REQUIREMENT_MISMATCH', self.codes(rev))

    def test_minimum_area_is_measured_from_geometry(self):
        req = {'id': 'area', 'metric': 'min_room_area_m2', 'room': ['g', 'bed'],
               'expected': 17, 'source': 'inferred', 'confirmed': True}
        rev = self.propose(requirements=[req])
        self.assertIn('REQUIREMENT_MISMATCH', self.codes(rev))
        req['expected'] = 16
        rev = self.propose(requirements=[req])
        self.assertNotIn('REQUIREMENT_MISMATCH', self.codes(rev))

    def test_invalid_requirement_types_report_not_crash(self):
        for req in [None, [], {}, dict(program()[0], expected=True),
                    dict(program()[2], template=[]), dict(program()[0], metric='unknown')]:
            with self.subTest(req=req):
                rev = self.propose(requirements=[req])
                self.assertFalse(self.ws.review(rev.id)['can_approve'])

    def test_geometry_rejects_overlap_outside_unresolved_or_empty(self):
        for change, code in [(lambda m: m['floors']['g']['rooms'][1].update(rect=[1, 1, 2, 2]), 'ROOM_OVERLAP'),
                              (lambda m: m['floors']['g']['rooms'][0].update(rect=[19, 0, 4, 4]), 'OUTSIDE_SITE'),
                              (lambda m: m['floors']['g']['rooms'][0].update(acs_unresolved=True), 'UNRESOLVED_SPACE'),
                              (lambda m: m['floors']['g'].update(rooms=[]), 'EMPTY_TEMPLATE')]:
            m = model(); change(m); rev = self.propose(m)
            self.assertIn(code, self.codes(rev))
            self.assertIsNone(self.ws.review(rev.id)['metrics']['space_rect_area_m2'])

    def test_invalid_dimensions_never_invent_defaults(self):
        for value in (None, 0, -1, True, '3'):
            m = model(); m['floor_height'] = value; rev = self.propose(m)
            self.assertIn('DIMENSION_NOT_SPECIFIED', self.codes(rev))
            self.assertEqual(rev.model['floor_height'], value)
        m = model(); del m['wall_h']; rev = self.propose(m)
        self.assertNotIn('wall_h', rev.model)

    def test_invalid_rects_and_levels_fail_closed(self):
        for rect in (None, [0, 0, 4], [0, 0, -4, 4], [0, 0, True, 4], ['0', 0, 4, 4]):
            m = model(); m['floors']['g']['rooms'][0]['rect'] = rect
            self.assertIn('INVALID_RECT', self.codes(self.propose(m)))
        for level in (None, {}, {'index': 1, 'template': []}, {'index': True, 'template': 'g'}):
            m = model(); m['levels'] = [level]
            self.assertIn('INVALID_LEVEL', self.codes(self.propose(m)))

    def test_duplicate_room_or_level_identity_rejected(self):
        m = model(); m['floors']['g']['rooms'].append(copy.deepcopy(m['floors']['g']['rooms'][0]))
        self.assertCode('AMBIGUOUS_ROOM_ID', lambda: self.propose(m))
        m = model(); m['levels'][1]['index'] = 0
        self.assertIn('INVALID_LEVEL', self.codes(self.propose(m)))

    def test_unreferenced_template_reported(self):
        m = model(); m['floors']['unused'] = copy.deepcopy(m['floors']['g'])
        self.assertIn('UNREFERENCED_TEMPLATE', self.codes(self.propose(m)))

    def test_touching_rooms_are_not_overlap(self):
        self.assertNotIn('ROOM_OVERLAP', self.codes(self.rev))

    def test_nonfinite_prototype_nested_and_oversize_input_rejected(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            self.assertCode('NON_FINITE', lambda: P.canonical({'x': value}))
        self.assertCode('INVALID_JSON_KEY', lambda: P.canonical({'x': {'__proto__': {}}}))
        nested = {}
        for _ in range(40): nested = {'x': nested}
        self.assertCode('INPUT_LIMIT', lambda: P.canonical(nested))
        self.assertCode('INPUT_LIMIT', lambda: P.canonical('x' * (P.MAX_BYTES + 1)))

    def test_level_and_requirement_limits_fail_without_changing_history(self):
        with patch.object(P, 'MAX_LEVELS', 1):
            self.assertCode('INPUT_LIMIT', self.propose)
        with patch.object(P, 'MAX_REQUIREMENTS', 1):
            self.assertCode('INPUT_LIMIT', self.propose)
        self.assertEqual(self.ws.head, self.rev.id)

    def test_aggregate_area_overflow_blocks_approval(self):
        m = model()
        m['site'] = {'w': 1e154, 'd': 1e154}
        m['floors']['g']['rooms'] = [{'id': 'bed', 'role': 'bedroom', 'rect': [0, 0, 1e154, 1e154]}]
        reqs = [dict(program()[1]), dict(program()[2])]
        rev = self.propose(m, requirements=reqs)
        review = self.ws.review(rev.id)
        self.assertFalse(review['can_approve'])
        self.assertIsNone(review['metrics']['space_rect_area_m2'])
        self.assertIn('NON_FINITE_MEASUREMENT', self.codes(rev))

    def test_unknown_revision_is_reported(self):
        self.assertCode('REVISION_NOT_FOUND', lambda: self.ws.get('missing'))

    def test_limit_never_prunes_approved_revision(self):
        self.approve()
        with patch.object(P, 'MAX_REVISIONS', 1):
            self.assertCode('HISTORY_LIMIT', self.propose)
        self.assertEqual(self.ws.handoff(self.rev.id)['building'], model())

    def test_approval_rechecks_after_reentrant_verifier_change(self):
        def changed_during_review(m):
            self.propose()
            return verified(m)
        self.ws._verifier = changed_during_review
        self.assertCode('STALE_REVISION', self.approve)
        self.assertIsNone(self.ws.baseline)


if __name__ == '__main__':
    unittest.main(verbosity=2)
