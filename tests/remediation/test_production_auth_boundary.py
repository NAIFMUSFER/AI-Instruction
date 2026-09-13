#!/usr/bin/env python3
"""Regression for the production authentication admission boundary.

No provider call is possible: ``guard`` is replaced with a sentinel. Unauthenticated
requests must be rejected before route, rate-limit, upload-body, job-reservation, or
provider work. The async submission aliases are protected by the same boundary.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-test-key")
os.environ.setdefault("ACS_ENV", "test")
os.environ.setdefault("ACS_AUTH_MODE", "test")
os.environ.setdefault("ACS_AUTH_TEST_TOKEN", "ci-only-auth-token")

from fastapi import HTTPException
from fastapi.testclient import TestClient
import acs_understand_api as API


class ProductionAuthenticationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._guard = API.guard

        def must_not_reach_rate_limit_or_provider(*_args, **_kwargs):
            raise HTTPException(status_code=418, detail="AUTH_BOUNDARY_MISSING")

        API.guard = must_not_reach_rate_limit_or_provider
        cls.client = TestClient(API.app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        API.guard = cls._guard
        cls.client.close()

    def assert_auth_rejected(self, response, path):
        self.assertEqual(
            response.status_code,
            401,
            "%s reached protected work without authentication (status=%s body=%s)"
            % (path, response.status_code, response.text[:240]),
        )
        body = response.json()
        self.assertEqual(body["error"]["code"], "ACS_AUTH_REQUIRED")
        self.assertEqual(body["contract"], "acs-error-envelope/1.0.0")
        self.assertEqual(response.headers.get("www-authenticate"), "Bearer")

    def test_text_generation_requires_auth_before_guard(self):
        self.assert_auth_rejected(
            self.client.post("/v1/understand", json={"text": "test"}),
            "/v1/understand",
        )

    def test_edit_requires_auth_before_guard(self):
        self.assert_auth_rejected(
            self.client.post(
                "/v1/edit",
                json={"building": {}, "notes": [{"text": "test"}]},
            ),
            "/v1/edit",
        )

    def test_image_generation_requires_auth_before_upload_parse(self):
        self.assert_auth_rejected(
            self.client.post(
                "/v1/understand/image",
                files=[("files", ("probe.png", b"not-an-image", "image/png"))],
            ),
            "/v1/understand/image",
        )

    def test_pdf_generation_requires_auth_before_upload_parse(self):
        self.assert_auth_rejected(
            self.client.post(
                "/v1/understand/pdf",
                files={"file": ("probe.pdf", b"not-a-pdf", "application/pdf")},
            ),
            "/v1/understand/pdf",
        )

    def test_async_text_submission_requires_same_auth_boundary(self):
        # Invalid/missing job capability must not be evaluated before authentication.
        self.assert_auth_rejected(
            self.client.post("/v1/jobs/understand", json={"text": "test"}),
            "/v1/jobs/understand",
        )

    def test_valid_test_identity_reaches_original_guard_after_auth(self):
        r = self.client.post(
            "/v1/understand",
            json={"text": "test"},
            headers={"Authorization": "Bearer ci-only-auth-token"},
        )
        self.assertEqual(r.status_code, 418, r.text)
        self.assertIn("AUTH_BOUNDARY_MISSING", r.text)

    def test_health_remains_public(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200, r.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)