# -*- coding: utf-8 -*-
"""Fail-closed authentication admission for ACS cost-bearing routes.

Production defaults to OIDC UserInfo verification. Development may run with auth
turned off, but production may not. Test-token mode is accepted only when
``ACS_ENV=test``. Raw bearer tokens are never logged, returned, or stored; the
short cache is keyed only by SHA-256(token) and stores the verified subject.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import acs_api_errors as E

DIRECT_PROTECTED_PATHS = frozenset({
    "/v1/understand",
    "/v1/edit",
    "/v1/understand/image",
    "/v1/understand/pdf",
})
AUTH_ERROR_CODE = "ACS_AUTH_REQUIRED"
AUTH_UNAVAILABLE_CODE = "ACS_AUTH_UNAVAILABLE"
REQUEST_ID_HEADER = b"x-request-id"
_MAX_USERINFO_BYTES = 32768
_CACHE = {}
_CACHE_LOCK = threading.Lock()


class AuthRejected(Exception):
    pass


class AuthUnavailable(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _env(name, default=""):
    return str(os.environ.get(name, default) or "").strip()


def auth_mode():
    env = _env("ACS_ENV", "development").lower()
    raw = _env("ACS_AUTH_MODE").lower()
    if not raw:
        raw = "oidc" if env == "production" else "off"
    if raw not in {"off", "oidc", "test"}:
        return "invalid"
    if env == "production" and raw == "off":
        return "invalid"
    if raw == "test" and env != "test":
        return "invalid"
    return raw


def _timeout_s():
    try:
        value = float(_env("ACS_AUTH_TIMEOUT_S", "5"))
    except ValueError:
        value = 5.0
    return min(15.0, max(1.0, value))


def _cache_ttl_s():
    try:
        value = int(_env("ACS_AUTH_CACHE_TTL_S", "30"))
    except ValueError:
        value = 30
    return min(300, max(0, value))


def _userinfo_url():
    raw = _env("ACS_AUTH_USERINFO_URL")
    if not raw:
        return None
    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return None
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    if parsed.username or parsed.password or parsed.fragment:
        return None
    return raw


def readiness_missing():
    mode = auth_mode()
    if mode == "invalid":
        return ["ACS_AUTH_MODE"]
    if mode == "oidc" and not _userinfo_url():
        return ["ACS_AUTH_USERINFO_URL"]
    if mode == "test" and not _env("ACS_AUTH_TEST_TOKEN"):
        return ["ACS_AUTH_TEST_TOKEN"]
    return []


def health_status():
    mode = auth_mode()
    missing = readiness_missing()
    return {
        "mode": mode,
        "required": mode != "off",
        "configured": not missing,
        "verifier": ("oidc_userinfo" if mode == "oidc" else
                     "test_only" if mode == "test" else
                     "disabled" if mode == "off" else "invalid"),
        "protected_routes": len(DIRECT_PROTECTED_PATHS),
        "cache_ttl_s": _cache_ttl_s(),
    }


def _request_id(scope):
    state = scope.setdefault("state", {})
    rid = state.get("request_id")
    if rid:
        return str(rid)[:64]
    headers = dict(scope.get("headers", []))
    rid = headers.get(REQUEST_ID_HEADER, b"").decode("ascii", "ignore").strip()[:64]
    if not rid:
        rid = E.new_request_id()
    state["request_id"] = rid
    return rid


def _error_body(code, message, request_id):
    return json.dumps({
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "retryable": False,
            "upstream": None,
        },
        "contract": E.ERROR_CONTRACT_VERSION,
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def _send_error(scope, send, status, code, message):
    rid = _request_id(scope)
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"cache-control", b"no-store, private"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-request-id", rid.encode("ascii", "ignore")),
    ]
    if status == 401:
        headers.append((b"www-authenticate", b"Bearer"))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body",
                "body": _error_body(code, message, rid), "more_body": False})


def _cached_subject(token):
    ttl = _cache_ttl_s()
    if ttl <= 0:
        return None
    key = hashlib.sha256(token.encode("utf-8")).digest()
    now = time.monotonic()
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item and item[0] > now:
            return item[1]
        if item:
            _CACHE.pop(key, None)
    return None


def _cache_subject(token, subject):
    ttl = _cache_ttl_s()
    if ttl <= 0:
        return
    key = hashlib.sha256(token.encode("utf-8")).digest()
    now = time.monotonic()
    with _CACHE_LOCK:
        if len(_CACHE) >= 1024:
            expired = [k for k, v in _CACHE.items() if v[0] <= now]
            for k in expired[:512]:
                _CACHE.pop(k, None)
            if len(_CACHE) >= 1024:
                _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (now + ttl, subject)


def _verify_test_token(token):
    expected = _env("ACS_AUTH_TEST_TOKEN")
    if not expected:
        raise AuthUnavailable()
    if not hmac.compare_digest(token, expected):
        raise AuthRejected()
    return "ci-authenticated-user"


def _verify_oidc_userinfo(token):
    url = _userinfo_url()
    if not url:
        raise AuthUnavailable()
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/json",
                 "User-Agent": "acs-auth/1.0"},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=_timeout_s()) as response:
            status = int(getattr(response, "status", 0) or 0)
            if status != 200:
                if status in (401, 403):
                    raise AuthRejected()
                raise AuthUnavailable()
            raw = response.read(_MAX_USERINFO_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) in (401, 403):
            raise AuthRejected() from None
        raise AuthUnavailable() from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AuthUnavailable() from None
    if len(raw) > _MAX_USERINFO_BYTES:
        raise AuthUnavailable()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise AuthUnavailable() from None
    subject = payload.get("sub") if isinstance(payload, dict) else None
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 256:
        raise AuthRejected()
    return subject.strip()


async def _verify(token, mode):
    cached = _cached_subject(token)
    if cached:
        return cached
    if mode == "test":
        subject = _verify_test_token(token)
    elif mode == "oidc":
        subject = await asyncio.to_thread(_verify_oidc_userinfo, token)
    else:
        raise AuthUnavailable()
    _cache_subject(token, subject)
    return subject


async def authorize_asgi(scope, send):
    """Authorize one protected ASGI request before any request-body read.

    Returns ``True`` only when downstream work may continue. On rejection it emits
    the complete JSON response itself and returns ``False``.
    """
    mode = auth_mode()
    if mode == "off":
        return True
    if mode == "invalid":
        await _send_error(scope, send, 503, AUTH_UNAVAILABLE_CODE,
                          "خدمة التحقق من الهوية غير جاهزة حالياً.")
        return False

    headers = dict(scope.get("headers", []))
    raw = headers.get(b"authorization", b"").decode("latin-1", "ignore")
    scheme, sep, token = raw.partition(" ")
    token = token.strip()
    if sep != " " or scheme.lower() != "bearer" or not token or len(token) > 8192:
        await _send_error(scope, send, 401, AUTH_ERROR_CODE,
                          "يلزم تسجيل الدخول لاستخدام هذه العملية.")
        return False
    try:
        subject = await _verify(token, mode)
    except AuthRejected:
        await _send_error(scope, send, 401, AUTH_ERROR_CODE,
                          "يلزم تسجيل الدخول لاستخدام هذه العملية.")
        return False
    except AuthUnavailable:
        await _send_error(scope, send, 503, AUTH_UNAVAILABLE_CODE,
                          "خدمة التحقق من الهوية غير جاهزة حالياً.")
        return False

    scope.setdefault("state", {})["authenticated_user_id"] = subject
    return True
