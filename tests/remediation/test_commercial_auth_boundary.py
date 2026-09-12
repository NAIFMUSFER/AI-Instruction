#!/usr/bin/env python3
"""Commercial ACS authentication boundary regressions.

No live Supabase project is contacted here. The verifier is exercised against a
small injected async HTTP client so the contracts prove identity/error semantics
without secrets, production users, or network access.

Red proof: focused run #1 on head 4355a8ef failed at import because the auth
boundary did not exist. One-time implementation run 34680042771 then created the
fail-closed verifier/error contract and passed the initial suite before committing.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import acs_api_errors as E
import acs_auth as A


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    def __init__(self, response=None, exc=None):
        self.response = response or FakeResponse()
        self.exc = exc
        self.calls = []

    async def get(self, url, *, headers):
        self.calls.append((url, dict(headers)))
        if self.exc:
            raise self.exc
        return self.response


def run(coro):
    return asyncio.run(coro)


class CommercialAuthBoundaryTests(unittest.TestCase):
    def verifier(self, client):
        return A.SupabaseAuthVerifier(
            base_url="https://acs-test.supabase.co",
            publishable_key="sb_publishable_test_only",
            client=client,
        )

    def assert_error(self, code, fn):
        with self.assertRaises(E.AcsApiError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    def test_missing_bearer_is_401_without_network(self):
        client = FakeClient()
        err = self.assert_error(E.ACS_AUTH_REQUIRED,
                                lambda: run(self.verifier(client).actor_id(None)))
        self.assertEqual(err.status, 401)
        self.assertEqual(client.calls, [])

    def test_malformed_bearer_is_401_without_echoing_token(self):
        client = FakeClient()
        secretish = "very-secret-user-token-value"
        err = self.assert_error(
            E.ACS_AUTH_INVALID,
            lambda: run(self.verifier(client).actor_id("Basic " + secretish)))
        self.assertEqual(err.status, 401)
        self.assertNotIn(secretish, str(err))
        self.assertEqual(client.calls, [])

    def test_verified_permanent_user_id_becomes_actor_authority(self):
        client = FakeClient(FakeResponse(200, {
            "id": "0f4c753e-91c0-4c39-bcf8-87b89fa49d3c",
            "email": "not-used-for-authority@example.invalid",
            "is_anonymous": False,
        }))
        actor = run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc"))
        self.assertEqual(actor, "0f4c753e-91c0-4c39-bcf8-87b89fa49d3c")
        self.assertEqual(len(client.calls), 1)
        url, headers = client.calls[0]
        self.assertEqual(url, "https://acs-test.supabase.co/auth/v1/user")
        self.assertEqual(headers["apikey"], "sb_publishable_test_only")
        self.assertEqual(headers["Authorization"], "Bearer aaa.bbb.ccc")

    def test_anonymous_session_cannot_authorize_durable_project(self):
        client = FakeClient(FakeResponse(200, {
            "id": "35970b6c-f670-44cf-bfc4-2387dfbdb24c",
            "is_anonymous": True,
        }))
        err = self.assert_error(
            E.ACS_AUTH_PERMANENT_IDENTITY_REQUIRED,
            lambda: run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc")))
        self.assertEqual(err.status, 403)

    def test_missing_anonymous_claim_fails_closed(self):
        client = FakeClient(FakeResponse(200, {
            "id": "6df7873c-bcd0-4cd3-910d-3c516da697e2",
        }))
        err = self.assert_error(
            E.ACS_AUTH_UNAVAILABLE,
            lambda: run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc")))
        self.assertEqual(err.status, 503)

    def test_non_uuid_user_id_fails_closed(self):
        client = FakeClient(FakeResponse(200, {
            "id": "not-a-supabase-uuid",
            "is_anonymous": False,
        }))
        err = self.assert_error(
            E.ACS_AUTH_UNAVAILABLE,
            lambda: run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc")))
        self.assertEqual(err.status, 503)

    def test_rejected_or_expired_token_is_401(self):
        client = FakeClient(FakeResponse(401, {"message": "invalid token"}))
        err = self.assert_error(
            E.ACS_AUTH_INVALID,
            lambda: run(self.verifier(client).actor_id("Bearer expired.token.value")))
        self.assertEqual(err.status, 401)

    def test_auth_service_failure_is_retryable_503(self):
        client = FakeClient(FakeResponse(503, {"message": "unavailable"}))
        err = self.assert_error(
            E.ACS_AUTH_UNAVAILABLE,
            lambda: run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc")))
        self.assertEqual(err.status, 503)
        self.assertTrue(err.retryable)

    def test_malformed_success_payload_fails_closed(self):
        client = FakeClient(FakeResponse(200, {"id": ""}))
        err = self.assert_error(
            E.ACS_AUTH_UNAVAILABLE,
            lambda: run(self.verifier(client).actor_id("Bearer aaa.bbb.ccc")))
        self.assertEqual(err.status, 503)

    def test_missing_server_configuration_is_not_client_auth_failure(self):
        with self.assertRaises(E.AcsApiError) as ctx:
            A.SupabaseAuthVerifier(base_url="", publishable_key="")
        self.assertEqual(ctx.exception.code, E.ACS_NOT_CONFIGURED)
        self.assertEqual(ctx.exception.status, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
