#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import acs_auth_gateway as G


class AuthGatewayTests(unittest.TestCase):
    def test_only_declared_auth_routes_are_intercepted(self):
        self.assertTrue(G.matches('/v1/auth/signup'))
        self.assertTrue(G.matches('/v1/auth/signin'))
        self.assertTrue(G.matches('/v1/auth/bootstrap-project'))
        self.assertFalse(G.matches('/v1/understand'))
        self.assertFalse(G.matches('/v1/projects/x/plan/commands'))

    def test_signup_forwards_bounded_identity_without_project_authority(self):
        calls = []
        def fake(method, path, **kwargs):
            calls.append((method, path, kwargs))
            return 200, {'access_token': 'a', 'refresh_token': 'r', 'user': {'id': 'u'}}
        with patch.object(G, '_request', side_effect=fake):
            status, payload = G._signup({
                'name': 'Naif', 'email': 'n@example.com', 'password': '12345678',
                'owner_id': 'attacker', 'project_id': 'attacker',
            })
        self.assertEqual(status, 200)
        self.assertEqual(payload['access_token'], 'a')
        sent = calls[0][2]['payload']
        self.assertEqual(set(sent), {'email', 'password', 'data'})
        self.assertEqual(sent['data'], {'name': 'Naif'})

    def test_bootstrap_derives_owner_from_verified_user_and_creates_first_project(self):
        calls = []
        def fake(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == '/auth/v1/user':
                return 200, {'id': 'verified-user', 'email': 'n@example.com'}
            if method == 'GET' and path.startswith('/rest/v1/acs_projects?'):
                return 200, []
            if method == 'POST' and path == '/rest/v1/acs_projects':
                self.assertEqual(kwargs['payload'], {'owner_id': 'verified-user', 'name': 'Real Project'})
                self.assertEqual(kwargs['prefer'], 'return=representation')
                return 201, [{'id': 'project-1', 'owner_id': 'verified-user', 'name': 'Real Project'}]
            raise AssertionError((method, path, kwargs))
        with patch.object(G, '_request', side_effect=fake):
            status, payload = G._bootstrap_project('real-token', {
                'name': 'Real Project', 'owner_id': 'attacker', 'user_id': 'attacker'
            })
        self.assertEqual(status, 200)
        self.assertTrue(payload['created'])
        self.assertEqual(payload['project']['owner_id'], 'verified-user')
        self.assertTrue(all(c[2].get('token') == 'real-token' for c in calls))

    def test_existing_project_is_reused_not_duplicated(self):
        def fake(method, path, **kwargs):
            if path == '/auth/v1/user':
                return 200, {'id': 'verified-user', 'email': 'n@example.com'}
            if method == 'GET' and path.startswith('/rest/v1/acs_projects?'):
                return 200, [{'id': 'p1', 'name': 'Existing', 'owner_id': 'verified-user'}]
            self.fail('unexpected project creation')
        with patch.object(G, '_request', side_effect=fake):
            status, payload = G._bootstrap_project('real-token', {'name': 'Ignored'})
        self.assertEqual(status, 200)
        self.assertFalse(payload['created'])
        self.assertEqual(payload['project']['id'], 'p1')

    def test_duplicate_authorization_headers_are_rejected_fail_closed(self):
        scope = {'headers': [
            (b'authorization', b'Bearer first-token'),
            (b'authorization', b'Bearer second-token'),
        ]}
        self.assertEqual(G._bearer(scope), '')

    def test_single_authorization_header_remains_case_insensitive(self):
        scope = {'headers': [
            (b'x-request-id', b'example'),
            (b'Authorization', b'Bearer real-token'),
        ]}
        self.assertEqual(G._bearer(scope), 'real-token')

    def test_malformed_asgi_header_sequence_fails_closed(self):
        scope = {'headers': [(b'authorization', 'Bearer not-bytes')]}
        self.assertEqual(G._bearer(scope), '')

    def test_gateway_reads_only_publishable_auth_configuration(self):
        text = Path(G.__file__).read_text(encoding='utf-8')
        self.assertIn('ACS_AUTH_SUPABASE_PUBLISHABLE_KEY', text)
        self.assertNotIn('SUPABASE_SERVICE_ROLE_KEY', text)
        self.assertNotIn('ACS_SUPABASE_SERVICE_ROLE', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
