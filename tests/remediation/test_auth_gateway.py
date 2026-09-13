#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import asyncio
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import acs_auth_gateway as G


class AuthGatewayTests(unittest.TestCase):
    def test_signup_normalizes_raw_and_obfuscated_rest_users_without_a_session(self):
        # GoTrue REST returns the User itself while confirmation is pending,
        # including its indistinguishable repeated-signup response.
        for identities in [[{'id': 'email-identity', 'provider': 'email'}], []]:
            user = {'id': '11111111-1111-4111-8111-111111111111',
                    'aud': 'authenticated', 'email': 'fixture@example.test',
                    'identities': identities}
            with self.subTest(identities=identities), patch.object(G, '_request', return_value=(200, user)):
                status, result = G._signup({'email': 'fixture@example.test', 'password': 'fixture-password'})
            self.assertEqual(status, 200)
            self.assertEqual(result, {'user': user, 'session': None})
            self.assertNotIn('access_token', result)
            self.assertNotIn('refresh_token', result)

    def test_signup_receipt_does_not_normalize_partial_tokens_or_signin(self):
        for partial in [{'access_token': 'incomplete'}, {'refresh_token': 'incomplete'}]:
            upstream = {'id': 'fixture-user', **partial}
            with patch.object(G, '_request', return_value=(200, upstream)):
                self.assertEqual(G._signup({'email': 'a@example.test', 'password': 'fixture-password'})[1], upstream)
        user = {'id': 'fixture-user', 'email': 'a@example.test'}
        with patch.object(G, '_request', return_value=(200, user)):
            self.assertEqual(G._signin({'email': 'a@example.test', 'password': 'fixture-password'})[1], user)

    def test_raw_signup_receipt_crosses_http_gateway_without_project_creation(self):
        user = {'id': '11111111-1111-4111-8111-111111111111', 'email': 'fixture@example.test'}
        messages = []
        async def receive():
            return {'type': 'http.request', 'body': json.dumps({'email': 'fixture@example.test',
                    'password': 'fixture-password'}).encode()}
        async def send(message):
            messages.append(message)
        with patch.object(G, '_request', return_value=(200, user)) as request:
            handled = asyncio.run(G.maybe_handle({'type': 'http', 'method': 'POST',
                'path': '/v1/auth/signup', 'headers': []}, receive, send))
        self.assertTrue(handled)
        self.assertEqual(messages[0]['status'], 200)
        self.assertEqual(json.loads(messages[1]['body']), {'user': user, 'session': None})
        self.assertEqual(request.call_count, 1)
        self.assertTrue(request.call_args.args[1].startswith('/auth/v1/signup?'))

    def test_default_email_callback_is_the_exact_production_root(self):
        with patch.dict(G.os.environ, {'ACS_AUTH_SITE_URL': ''}):
            query = G.urllib.parse.parse_qs(G._email_redirect()[1:])
        self.assertEqual(query, {'redirect_to': ['https://sprightly-selkie-d906c3.netlify.app/']})

    def test_recovery_and_confirmation_are_fixed_origin_and_email_only(self):
        for confirmation, path in [(False, '/auth/v1/recover?'), (True, '/auth/v1/resend?')]:
            with patch.object(G, '_request', return_value=(200, {})) as request:
                status, result = G._email_action({'email': ' a@example.test ', 'redirect_to': 'https://untrusted.invalid/', 'password': 'unused'}, confirmation=confirmation)
                self.assertEqual(status, 200)
                self.assertTrue(result['ok'])
                self.assertTrue(request.call_args.args[1].startswith(path))
                self.assertNotIn('untrusted', request.call_args.args[1])
                self.assertEqual(request.call_args.kwargs['payload'], {'email': 'a@example.test', **({'type': 'signup'} if confirmation else {})})

    def test_password_update_cannot_select_another_user(self):
        with patch.object(G, '_request', return_value=(200, {'id': 'verified-user'})) as request:
            status, result = G._update_password('verified-session', {'password': 'new-fixture-password', 'user_id': 'other', 'email': 'other@example.test'})
            self.assertEqual((status, result), (200, {'ok': True}))
            self.assertEqual(request.call_args.args, ('PUT', '/auth/v1/user'))
            self.assertEqual(request.call_args.kwargs, {'token': 'verified-session', 'payload': {'password': 'new-fixture-password'}})
        with patch.object(G, '_request') as request:
            self.assertEqual(G._update_password('', {'password': 'new-fixture-password'})[0], 401)
            request.assert_not_called()

    def test_selected_project_denial_never_creates_a_replacement(self):
        with patch.object(G, '_request', side_effect=[(200, {'id': 'u'}), (200, [])]) as request:
            result = G._bootstrap_project('session', {'project_id': '11111111-1111-4111-8111-111111111111', 'name': 'do not create'})
            self.assertEqual(result[0], 404)
            self.assertEqual(request.call_count, 2)

    def test_additional_project_uses_verified_owner(self):
        with patch.object(G, '_request', side_effect=[(200, {'id': 'verified'}), (201, [{'id': 'p'}])]) as request:
            self.assertEqual(G._projects('session', {'action': 'create', 'name': 'Second', 'owner_id': 'other'})[0], 200)
            self.assertEqual(request.call_args.kwargs['payload'], {'owner_id': 'verified', 'name': 'Second'})

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

    def test_signin_accepts_existing_short_password_but_signup_keeps_minimum(self):
        with patch.object(G, '_request', return_value=(200, {})) as request:
            self.assertEqual(G._signin({'email': 'n@example.com', 'password': 'legacy'})[0], 200)
            self.assertEqual(request.call_args.kwargs['payload']['password'], 'legacy')
        with self.assertRaises(ValueError):
            G._signup({'email': 'n@example.com', 'password': 'legacy'})

    def test_user_service_outage_is_not_reported_as_invalid_session(self):
        with patch.object(G, '_request', return_value=(503, {'error': 'AUTH_UPSTREAM_UNAVAILABLE'})):
            status, payload = G._bootstrap_project('real-token', {'name': 'First'})
        self.assertEqual(status, 503)
        self.assertEqual(payload['error']['code'], 'AUTH_UPSTREAM_UNAVAILABLE')

    def test_malformed_project_list_does_not_create_a_duplicate(self):
        with patch.object(G, '_request', side_effect=[(200, {'id': 'u'}), (200, {})]) as request:
            status, _ = G._bootstrap_project('real-token', {'name': 'First'})
        self.assertEqual(status, 502)
        self.assertEqual(request.call_count, 2)

    def test_errors_use_arabic_messages_and_do_not_reflect_sql_or_provider_details(self):
        status, payload = G._safe_auth_error(500, {'message': 'private database details'})
        self.assertEqual(status, 500)
        self.assertNotIn('private', str(payload))
        self.assertIn('مؤقتًا', payload['error']['message'])
        self.assertEqual(G._safe_auth_error(400, {'error_code': 'invalid_credentials'})[1]['error']['message'],
                         'البريد الإلكتروني أو كلمة المرور غير صحيحة.')

    def test_unexpected_transport_failure_keeps_json_error_contract(self):
        messages = []
        async def receive():
            return {'type': 'http.request', 'body': b'{"email":"n@example.com","password":"12345678"}'}
        async def send(message):
            messages.append(message)
        with patch.object(G, '_request', side_effect=RuntimeError('private detail')):
            handled = asyncio.run(G.maybe_handle({'type': 'http', 'method': 'POST',
                'path': '/v1/auth/signin', 'headers': []}, receive, send))
        self.assertTrue(handled)
        self.assertEqual(messages[0]['status'], 502)
        self.assertNotIn(b'private detail', messages[1]['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
