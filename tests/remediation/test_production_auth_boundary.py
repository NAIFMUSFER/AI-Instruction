#!/usr/bin/env python3
"""Red-first production authentication boundary for cost-bearing ACS API routes.

The public production service holds the provider credential server-side.  Before release,
unauthenticated callers must be rejected before rate-limit/provider/upload work begins.
This test never calls a provider: ``guard`` is replaced with a sentinel response path.
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-test-key")
os.environ.setdefault("ACS_ENV", "test")

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
        self.assertIn(
            response.status_code,
            (401, 403),
            "%s reached route/rate-limit work without authentication (status=%s body=%s)"
            % (path, response.status_code, response.text[:240]),
        )

    def test_text_generation_requires_auth_before_guard(self):
        r = self.client.post("/v1/understand", json={"text": "test"})
        self.assert_auth_rejected(r, "/v1/understand")

    def test_edit_requires_auth_before_guard(self):
        r = self.client.post(
            "/v1/edit",
            json={"building": {}, "notes": [{"text": "test"}]},
        )
        self.assert_auth_rejected(r, "/v1/edit")

    def test_image_generation_requires_auth_before_guard(self):
        r = self.client.post(
            "/v1/understand/image",
            files=[("files", ("probe.png", b"not-an-image", "image/png"))],
        )
        self.assert_auth_rejected(r, "/v1/understand/image")

    def test_pdf_generation_requires_auth_before_guard(self):
        r = self.client.post(
            "/v1/understand/pdf",
            files={"file": ("probe.pdf", b"not-a-pdf", "application/pdf")},
        )
        self.assert_auth_rejected(r, "/v1/understand/pdf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
