#!/usr/bin/env python3
"""Red-first contract for ACS ↔ Supabase Auth integration.

No network call and no real user are used.  The fake User endpoint models
Supabase ``/auth/v1/user``: it requires the browser-safe publishable ``apikey``
header, receives the user's Bearer access token, and returns the stable user
``id``.  Generic OIDC ``sub`` behavior must remain intact.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ACS_ENV", "test")
os.environ.setdefault("ACS_AUTH_MODE", "oidc")

import acs_auth as AUTH


class _Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return json.dumps(self.payload).encode("utf-8")


class _Opener:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def open(self, request, timeout=None):
        self.request = request
        return _Response(self.payload)


class SupabaseAuthIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "ACS_ENV": "test",
            "ACS_AUTH_MODE": "oidc",
            "ACS_AUTH_PROVIDER": "supabase",
            "ACS_AUTH_USERINFO_URL": "https://example.supabase.co/auth/v1/user",
            "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_ci_only",
        }, clear=False)
        self.env.start()
        AUTH._CACHE.clear()

    def tearDown(self):
        self.env.stop()
        AUTH._CACHE.clear()

    def test_supabase_user_endpoint_uses_apikey_and_user_id(self):
        opener = _Opener({"id": "11111111-2222-3333-4444-555555555555"})
        with mock.patch.object(AUTH.urllib.request, "build_opener", return_value=opener):
            subject = AUTH._verify_oidc_userinfo("user-access-token")

        self.assertEqual(subject, "11111111-2222-3333-4444-555555555555")
        headers = {k.lower(): v for k, v in opener.request.header_items()}
        self.assertEqual(headers.get("apikey"), "sb_publishable_ci_only")
        self.assertEqual(headers.get("authorization"), "Bearer user-access-token")

    def test_supabase_mode_is_not_ready_without_publishable_key(self):
        with mock.patch.dict(os.environ, {"ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": ""}, clear=False):
            self.assertIn("ACS_AUTH_SUPABASE_PUBLISHABLE_KEY", AUTH.readiness_missing())

    def test_generic_oidc_still_uses_sub_without_supabase_header(self):
        opener = _Opener({"sub": "oidc-user"})
        with mock.patch.dict(os.environ, {
            "ACS_AUTH_PROVIDER": "oidc",
            "ACS_AUTH_USERINFO_URL": "https://identity.example.test/userinfo",
            "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": "",
        }, clear=False), mock.patch.object(
            AUTH.urllib.request, "build_opener", return_value=opener
        ):
            subject = AUTH._verify_oidc_userinfo("oidc-token")
        self.assertEqual(subject, "oidc-user")
        headers = {k.lower(): v for k, v in opener.request.header_items()}
        self.assertNotIn("apikey", headers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
