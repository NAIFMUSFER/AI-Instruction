"""Fail-closed authenticated actor boundary for durable ACS projects.

The browser supplies a Supabase user access token. The server validates
that token against Supabase Auth's `/auth/v1/user` endpoint using only the
project's publishable key. No service-role/secret key is required here,
and no caller-provided actor/project identity is trusted.

This module deliberately returns only the authenticated immutable user id.
Email/profile metadata is not authorization authority. Anonymous sessions
are rejected for durable projects because they cannot reliably recover the
same identity after sign-out.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

import acs_api_errors as E

MAX_BEARER_CHARS = 8192
MAX_ACTOR_ID_CHARS = 160
MAX_PUBLISHABLE_KEY_CHARS = 4096
DEFAULT_TIMEOUT_S = 5.0


def _configured_url(value: str | None) -> str:
    raw = str(value or "").strip().rstrip("/")
    try:
        parsed = urlsplit(raw)
    except Exception as exc:
        raise E.AcsApiError(E.ACS_NOT_CONFIGURED) from exc
    if (not raw or parsed.scheme != "https" or not parsed.netloc
            or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise E.AcsApiError(E.ACS_NOT_CONFIGURED)
    return raw


def _configured_key(value: str | None) -> str:
    raw = str(value or "").strip()
    if (not raw or len(raw) > MAX_PUBLISHABLE_KEY_CHARS
            or any(ch.isspace() for ch in raw)):
        raise E.AcsApiError(E.ACS_NOT_CONFIGURED)
    return raw


def _bearer(authorization: str | None) -> str:
    if authorization is None or not str(authorization).strip():
        raise E.AcsApiError(E.ACS_AUTH_REQUIRED)
    value = str(authorization).strip()
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise E.AcsApiError(E.ACS_AUTH_INVALID)
    token = parts[1]
    if (not token or len(token) > MAX_BEARER_CHARS
            or any(ch.isspace() or ord(ch) < 0x21 for ch in token)):
        raise E.AcsApiError(E.ACS_AUTH_INVALID)
    return token


def _actor_id(payload) -> str:
    if not isinstance(payload, dict):
        raise E.AcsApiError(E.ACS_AUTH_UNAVAILABLE, retryable=True)
    value = payload.get("id")
    if (not isinstance(value, str) or not value
            or value != value.strip()
            or len(value) > MAX_ACTOR_ID_CHARS):
        raise E.AcsApiError(E.ACS_AUTH_UNAVAILABLE, retryable=True)
    if payload.get("is_anonymous") is True:
        raise E.AcsApiError(E.ACS_AUTH_PERMANENT_IDENTITY_REQUIRED)
    return value


class SupabaseAuthVerifier:
    """Resolve a Bearer session to the permanent Supabase user id only."""

    def __init__(self, *, base_url: str | None = None,
                 publishable_key: str | None = None,
                 client=None, timeout_s: float = DEFAULT_TIMEOUT_S):
        if base_url is None:
            base_url = os.environ.get("ACS_SUPABASE_URL")
        if publishable_key is None:
            publishable_key = os.environ.get("ACS_SUPABASE_PUBLISHABLE_KEY")
        self.base_url = _configured_url(base_url)
        self.publishable_key = _configured_key(publishable_key)
        self.client = client
        try:
            timeout = float(timeout_s)
        except (TypeError, ValueError) as exc:
            raise E.AcsApiError(E.ACS_NOT_CONFIGURED) from exc
        if not (0.2 <= timeout <= 30.0):
            raise E.AcsApiError(E.ACS_NOT_CONFIGURED)
        self.timeout_s = timeout

    async def _get_user(self, token: str):
        url = self.base_url + "/auth/v1/user"
        headers = {
            "apikey": self.publishable_key,
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        }
        try:
            if self.client is not None:
                return await self.client.get(url, headers=headers)
            # Lazy import keeps the injected-client regression suite
            # stdlib-only under `python -S`; production has pinned httpx.
            import httpx
            async with httpx.AsyncClient(
                    timeout=self.timeout_s, follow_redirects=False) as client:
                return await client.get(url, headers=headers)
        except E.AcsApiError:
            raise
        except Exception as exc:
            # Never include the exception text: request exceptions can
            # carry the Authorization header or full request URL.
            raise E.AcsApiError(
                E.ACS_AUTH_UNAVAILABLE, retryable=True) from exc

    async def actor_id(self, authorization: str | None) -> str:
        token = _bearer(authorization)
        response = await self._get_user(token)
        status = getattr(response, "status_code", None)
        if status in (400, 401, 403):
            raise E.AcsApiError(E.ACS_AUTH_INVALID)
        if status != 200:
            raise E.AcsApiError(E.ACS_AUTH_UNAVAILABLE, retryable=True)
        try:
            payload = response.json()
        except Exception as exc:
            raise E.AcsApiError(
                E.ACS_AUTH_UNAVAILABLE, retryable=True) from exc
        return _actor_id(payload)
