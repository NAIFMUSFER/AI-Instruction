#!/usr/bin/env python3
"""Receipt-to-row regressions. Only isolated temporary databases are modified.

The topology verifier is a test double, as in test_plan_store.py. These tests
prove persistence identity checks, not engineering approval or live auth.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore, approval_document
from test_plan_store import element, reqs, verifier, warehouse


class PlanStoreRowBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'plans.sqlite3'
        self.store = SQLitePlanStore(self.db)
        self.store.create_project('p1', owner_id='owner-1')
        self.ws = PlanLockWorkspace(verifier=verifier)
        initial = self.ws.propose(warehouse(), brief='site width 30 warehouse',
                                  requirements=reqs(), expected_head=None)
        self.store.save_revision('p1', actor_id='owner-1', revision=initial,
                                 expected_head=None)
        self.first = self.ws.replace_semantic_locks(
            [element('racks', 'rack_a', 'storage'),
             element('docks', 'dock_n1', 'receiving')],
            expected_head=initial.id, note='lock warehouse anchors')
        self.store.save_revision('p1', actor_id='owner-1', revision=self.first,
                                 expected_head=initial.id)
        self.first_approval = self.approve(self.first)
        changed = copy.deepcopy(self.first.model)
        changed['floors']['ground']['rooms'][2]['rect'] = [20., 0., 10., 17.]
        changed['floors']['ground']['rooms'][3]['rect'] = [20., 17., 10., 13.]
        self.second = self.ws.propose(changed, brief=self.first.brief,
                                     requirements=reqs(), expected_head=self.first.id,
                                     note='expand staging without moving anchors')
        self.store.save_revision('p1', actor_id='owner-1', revision=self.second,
                                 expected_head=self.first.id)

    def approve(self, revision):
        receipt = self.ws.approve(revision.id, expected_head=revision.id,
                                  actor_label='Test engineer', confirmed=True,
                                  acknowledge_concept_only=True)
        self.store.save_approval('p1', actor_id='owner-1', approval=receipt,
                                 expected_head=revision.id)
        return receipt

    def sql(self, statement, params=()):
        con = sqlite3.connect(self.db)
        try:
            rows = con.execute(statement, params).fetchall()
            con.commit()
            return rows
        finally:
            con.close()

    def raw_revision(self, revision):
        return self.sql('SELECT revision_json FROM plan_revisions WHERE project_id=? AND revision_id=?',
                        ('p1', revision.id))[0][0]

    def replace_revision_json(self, target, raw):
        self.sql('UPDATE plan_revisions SET revision_json=? WHERE project_id=? AND revision_id=?',
                 (raw, 'p1', target.id))

    def load(self, revision):
        return self.store.load_revision('p1', actor_id='owner-1', revision_id=revision.id)

    def handoff(self):
        return self.store.approved_handoff('p1', actor_id='owner-1', revision_id=self.first.id)

    def assertCode(self, code, call):
        with self.assertRaises(PlanError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_pristine_receipts_and_frozen_baseline_survive_reopen(self):
        self.store = SQLitePlanStore(self.db)
        self.assertEqual(self.load(self.second)['model'], self.second.model)
        before = self.handoff()
        self.approve(self.second)
        self.assertEqual(self.handoff(), before)
        self.assertEqual(before['building'], self.first.model)
        self.assertEqual(before['baseline']['semantic_lock_count'], 2)

    def test_valid_revision_cannot_be_substituted_into_another_row(self):
        self.replace_revision_json(self.first, self.raw_revision(self.second))
        self.assertCode('STORED_REVISION_TAMPERED', lambda: self.load(self.first))

    def test_matching_foreign_receipt_pair_cannot_relabel_frozen_baseline(self):
        self.approve(self.second)
        other = self.sql('SELECT approval_json FROM plan_approvals WHERE project_id=? AND revision_id=?',
                         ('p1', self.second.id))[0][0]
        self.replace_revision_json(self.first, self.raw_revision(self.second))
        self.sql('UPDATE plan_approvals SET approval_json=? WHERE project_id=? AND revision_id=?',
                 (other, 'p1', self.first.id))
        self.assertCode('STORED_REVISION_TAMPERED', self.handoff)

    def test_revision_metadata_columns_are_bound_to_document(self):
        changes = {'number': 99, 'parent_id': 'wrong-parent', 'model_hash': '0' * 64,
                   'content_hash': '0' * 64, 'bound_content_hash': '0' * 64,
                   'semantic_lock_manifest_hash': '0' * 64, 'created_at': 'wrong-time'}
        for column, value in changes.items():
            with self.subTest(column=column):
                original = self.sql(f'SELECT {column} FROM plan_revisions WHERE revision_id=?',
                                    (self.first.id,))[0][0]
                self.sql(f'UPDATE plan_revisions SET {column}=? WHERE revision_id=?',
                         (value, self.first.id))
                try:
                    self.assertCode('STORED_REVISION_TAMPERED', lambda: self.load(self.first))
                finally:
                    self.sql(f'UPDATE plan_revisions SET {column}=? WHERE revision_id=?',
                             (original, self.first.id))

    def test_handoff_checks_revision_metadata_not_only_json(self):
        self.sql('UPDATE plan_revisions SET bound_content_hash=? WHERE revision_id=?',
                 ('0' * 64, self.first.id))
        self.assertCode('STORED_REVISION_TAMPERED', self.handoff)

    def test_approval_document_identity_must_match_requested_baseline(self):
        raw = approval_document(self.first_approval)
        raw['revision_id'] = self.second.id
        self.sql('UPDATE plan_approvals SET approval_json=? WHERE revision_id=?',
                 (json.dumps(raw), self.first.id))
        self.assertCode('STORED_APPROVAL_TAMPERED', self.handoff)

    def test_approval_timestamp_must_match_persisted_receipt(self):
        self.sql('UPDATE plan_approvals SET approved_at=? WHERE revision_id=?',
                 ('wrong-time', self.first.id))
        self.assertCode('STORED_APPROVAL_TAMPERED', self.handoff)

    def test_approval_write_rejects_self_consistent_revision_row_substitution(self):
        self.replace_revision_json(self.second, self.raw_revision(self.first))
        relabelled = approval_document(self.first_approval)
        relabelled['revision_id'] = self.second.id
        state_before = self.store.project_state('p1', actor_id='owner-1')
        self.assertCode('STORED_REVISION_TAMPERED', lambda: self.store.save_approval(
            'p1', actor_id='owner-1', approval=SimpleNamespace(**relabelled),
            expected_head=self.second.id))
        self.assertEqual(self.store.project_state('p1', actor_id='owner-1'), state_before)
        self.assertEqual(self.sql('SELECT count(*) FROM plan_approvals')[0][0], 1)

    def test_child_write_validates_parent_receipt_before_extending_history(self):
        child = self.ws.propose(self.second.model, brief=self.second.brief,
                                requirements=reqs(), expected_head=self.second.id,
                                note='next review draft')
        self.replace_revision_json(self.second, self.raw_revision(self.first))
        state_before = self.store.project_state('p1', actor_id='owner-1')
        self.assertCode('STORED_REVISION_TAMPERED', lambda: self.store.save_revision(
            'p1', actor_id='owner-1', revision=child, expected_head=self.second.id))
        self.assertEqual(self.store.project_state('p1', actor_id='owner-1'), state_before)

    def test_malformed_revision_json_is_a_plan_error_during_approval(self):
        self.replace_revision_json(self.second, '{invalid-json')
        receipt = self.ws.approve(self.second.id, expected_head=self.second.id,
                                  actor_label='Test engineer', confirmed=True,
                                  acknowledge_concept_only=True)
        self.assertCode('STORED_REVISION_TAMPERED', lambda: self.store.save_approval(
            'p1', actor_id='owner-1', approval=receipt, expected_head=self.second.id))

    def test_malformed_parent_json_is_rejected_before_revision_write(self):
        child = self.ws.propose(self.second.model, brief=self.second.brief,
                                requirements=reqs(), expected_head=self.second.id)
        self.replace_revision_json(self.second, '{invalid-json')
        self.assertCode('STORED_REVISION_TAMPERED', lambda: self.store.save_revision(
            'p1', actor_id='owner-1', revision=child, expected_head=self.second.id))

    def test_outsider_is_rejected_before_corrupted_receipts_are_read(self):
        self.replace_revision_json(self.first, '{invalid-json')
        self.assertCode('PROJECT_ACCESS_DENIED', lambda: self.store.load_revision(
            'p1', actor_id='outsider', revision_id=self.first.id))
        self.assertCode('PROJECT_ACCESS_DENIED', lambda: self.store.approved_handoff(
            'p1', actor_id='outsider', revision_id=self.first.id))


if __name__ == '__main__':
    unittest.main(verbosity=2)
