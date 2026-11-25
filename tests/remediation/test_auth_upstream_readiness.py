#!/usr/bin/env python3
"""HTTP contract for sign-in upstream readiness.

`/health` is Render's liveness check and must stay 200, without opening a socket,
while the auth project is unreachable: a restart cannot fix a missing project and
the guest workspace still works. `/ready/auth` is the monitoring verdict: 503 with
the standard error envelope when sign-in cannot reach its project. No response may
carry the project URL or host, the publishable key or exception text.

No network is used: the single outbound function is replaced.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-test-key")
os.environ.setdefault("ACS_ENV", "test")
os.environ.setdefault("ACS_AUTH_MODE", "test")
os.environ.setdefault("ACS_AUTH_TEST_TOKEN", "ci-only-auth-token")

from fastapi.testclient import TestClient
import acs_auth_gateway as G
import acs_understand_api as API

FIXTURE_URL = "https://fixture-auth-project.supabase.co"
FIXTURE_KEY = "sb_publishable_fixture_key_value"
CONFIGURED = {"ACS_AUTH_SUPABASE_URL": FIXTURE_URL,
              "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": FIXTURE_KEY}
ENVELOPE_FIELDS = {"code", "message", "request_id", "retryable", "upstream"}


class AuthUpstreamReadinessHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(API.app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        G._PROBE.update(fingerprint=None, at=None, checked_at=None,
                        value=None, latency_ms=None, worker=None)

    def assert_no_secret(self, text):
        for secret in (FIXTURE_URL, "fixture-auth-project", FIXTURE_KEY):
            self.assertNotIn(secret, text)

    def test_health_stays_live_and_does_not_probe_while_auth_is_down(self):
        with patch.dict(G.os.environ, CONFIGURED), \
             patch.object(G, "_probe_settings", side_effect=AssertionError("liveness probed")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200, response.text)
        block = response.json()["auth_upstream"]
        self.assertEqual((block["configured"], block["state"]), (True, "unchecked"))
        self.assert_no_secret(response.text)

    def test_ready_auth_fails_with_the_standard_envelope_on_the_production_outage(self):
        with patch.dict(G.os.environ, CONFIGURED), \
             patch.object(G, "_probe_settings", return_value=("unreachable", None, None)):
            response = self.client.get("/ready/auth")
            health = self.client.get("/health")
            generation = self.client.get("/ready")
        self.assertEqual(response.status_code, 503, response.text)
        body = response.json()
        self.assertIs(body["ok"], False)
        self.assertEqual(set(body["error"]), ENVELOPE_FIELDS)
        self.assertEqual(body["error"]["code"], "ACS_UPSTREAM_UNAVAILABLE")
        self.assertIs(body["error"]["retryable"], True)
        self.assertEqual(body["error"]["upstream"]["provider"], "acs-auth")
        self.assertEqual(body["error"]["upstream"]["kind"], "unreachable")
        self.assertTrue(response.headers.get("x-request-id"))
        self.assert_no_secret(response.text)
        # Liveness is unchanged and now reports the cached verdict.
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["auth_upstream"]["state"], "unreachable")
        self.assert_no_secret(health.text)
        # Generation readiness keeps its own contract: guests are still served.
        self.assertIn(generation.status_code, (200, 503))
        if generation.status_code == 503:
            self.assertEqual(generation.json()["error"]["code"], "ACS_NOT_CONFIGURED")

    def test_ready_auth_reports_configuration_names_only(self):
        with patch.dict(G.os.environ, {"ACS_AUTH_SUPABASE_URL": "", "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": ""}), \
             patch.object(G, "_probe_settings") as probe:
            response = self.client.get("/ready/auth")
        probe.assert_not_called()
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["error"]["code"], "ACS_NOT_CONFIGURED")
        self.assertIn("ACS_AUTH_SUPABASE_URL", response.json()["error"]["message"])

    def test_google_disabled_and_rejected_key_are_not_ready_and_not_retryable(self):
        for value, kind in ((("ok", 200, False), "google_not_configured"),
                            (("rejected", 401, None), "rejected")):
            with self.subTest(kind=kind):
                G._PROBE.update(fingerprint=None, value=None, worker=None)
                with patch.dict(G.os.environ, CONFIGURED), \
                     patch.object(G, "_probe_settings", return_value=value):
                    response = self.client.get("/ready/auth")
                self.assertEqual(response.status_code, 503)
                error = response.json()["error"]
                self.assertEqual((error["upstream"]["kind"], error["retryable"]), (kind, False))

    def test_ready_auth_is_200_when_sign_in_can_start(self):
        with patch.dict(G.os.environ, CONFIGURED), \
             patch.object(G, "_probe_settings", return_value=("ok", 200, True)) as probe:
            first = self.client.get("/ready/auth")
            second = self.client.get("/ready/auth")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(probe.call_count, 1, "repeated probes must be served from the cache")
        body = second.json()
        self.assertEqual((body["ok"], body["ready"], body["auth"]["state"], body["auth"]["google_enabled"]),
                         (True, True, "ok", True))
        self.assert_no_secret(json.dumps(body))

    def test_ready_auth_is_public_and_get_only(self):
        with patch.dict(G.os.environ, CONFIGURED), \
             patch.object(G, "_probe_settings", return_value=("ok", 200, True)):
            self.assertEqual(self.client.get("/ready/auth").status_code, 200)
            wrong = self.client.post("/ready/auth")
        self.assertEqual(wrong.status_code, 405)
        self.assertEqual(wrong.json()["error"]["code"], "ACS_METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
