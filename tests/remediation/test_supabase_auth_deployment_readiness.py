#!/usr/bin/env python3
"""Red-first deployment contract for ACS production Supabase authentication.

This test does not create users, call Supabase, or expose credentials. It proves
that the production Blueprint and local configuration template declare the
server-side values required by the Supabase verifier introduced in PR #77.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import acs_auth as AUTH


RENDER = ROOT / "render.yaml"
ENV_EXAMPLE = ROOT / ".env.example"


class SupabaseAuthDeploymentReadinessTests(unittest.TestCase):
    def test_render_blueprint_declares_explicit_supabase_auth_contract(self):
        text = RENDER.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s*- key: ACS_AUTH_MODE\s*$")
        self.assertRegex(text, r"(?ms)- key: ACS_AUTH_MODE\s*\n\s*value: oidc\s*$")
        self.assertRegex(text, r"(?ms)- key: ACS_AUTH_PROVIDER\s*\n\s*value: supabase\s*$")
        self.assertRegex(text, r"(?ms)- key: ACS_AUTH_SUPABASE_URL\s*\n\s*sync: false\s*$")
        self.assertRegex(text, r"(?ms)- key: ACS_AUTH_SUPABASE_PUBLISHABLE_KEY\s*\n\s*sync: false\s*$")

    def test_env_template_names_required_auth_configuration_without_values(self):
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        expected = {
            "ACS_AUTH_MODE": "oidc",
            "ACS_AUTH_PROVIDER": "supabase",
            "ACS_AUTH_SUPABASE_URL": "",
            "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": "",
        }
        parsed = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip().strip('"')
        for key, value in expected.items():
            self.assertIn(key, parsed)
            self.assertEqual(parsed[key], value)

    def test_production_supabase_readiness_fails_closed_until_runtime_values_exist(self):
        with mock.patch.dict(os.environ, {
            "ACS_ENV": "production",
            "ACS_AUTH_MODE": "oidc",
            "ACS_AUTH_PROVIDER": "supabase",
            "ACS_AUTH_SUPABASE_URL": "",
            "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": "",
        }, clear=False):
            missing = AUTH.readiness_missing()
            self.assertEqual(missing, [
                "ACS_AUTH_SUPABASE_URL",
                "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY",
            ])
            status = AUTH.health_status()
            self.assertFalse(status["configured"])
            self.assertEqual(status["verifier"], "supabase_user")

    def test_valid_runtime_values_derive_only_the_supabase_user_endpoint(self):
        with mock.patch.dict(os.environ, {
            "ACS_ENV": "production",
            "ACS_AUTH_MODE": "oidc",
            "ACS_AUTH_PROVIDER": "supabase",
            "ACS_AUTH_SUPABASE_URL": "https://project-ref.supabase.co",
            "ACS_AUTH_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_placeholder",
        }, clear=False):
            self.assertEqual(AUTH.readiness_missing(), [])
            self.assertEqual(
                AUTH._userinfo_url(),
                "https://project-ref.supabase.co/auth/v1/user",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
