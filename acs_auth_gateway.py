# -*- coding: utf-8 -*-
"""Narrow browser-facing Supabase Auth gateway for ACS production.

The browser talks only to the already-pinned ACS backend origin. This module
forwards bounded auth requests to the configured Supabase project using the
browser-safe publishable key, never a service-role key. Passwords/tokens are
never logged or persisted by the ACS server.
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_MAX_BODY = 32 * 1024
_MAX_UPSTREAM = 256 * 1024
_AUTH_PATHS = frozenset({
    "/v1/auth/signup",
    "/v1/auth/signin",
    "/v1/auth/refresh",
    "/v1/auth/signout",
    "/v1/auth/bootstrap-project",
})


def _env(name: str) -> str:
    return str(os.environ.get(name, "") or "").strip()


def _base() -> str:
    raw = _env("ACS_AUTH_SUPABASE_URL").rstrip("/")
    if not raw.startswith("https://"):
        return ""
    return raw


def _key() -> str:
    return _env("ACS_AUTH_SUPABASE_PUBLISHABLE_KEY")


def matches(path: Any) -> bool:
    return isinstance(path, str) and path in _AUTH_PATHS


async def _read_json(receive) -> dict:
    chunks: list[bytes] = []
    size = 0
    while True:
        msg = await receive()
        if not isinstance(msg, dict):
            raise ValueError("invalid request")
        if msg.get("type") == "http.disconnect":
            raise ValueError("disconnected")
        if msg.get("type") != "http.request":
            continue
        body = msg.get("body", b"")
        if not isinstance(body, (bytes, bytearray)):
            raise ValueError("invalid body")
        size += len(body)
        if size > _MAX_BODY:
            raise OverflowError("body too large")
        if body:
            chunks.append(bytes(body))
        if not msg.get("more_body", False):
            break
    try:
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid json") from exc
    if not isinstance(value, dict):
        raise ValueError("json object required")
    return value


async def _send(send, status: int, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"cache-control", b"no-store, private"),
            (b"pragma", b"no-cache"),
            (b"x-content-type-options", b"nosniff"),
            (b"content-length", str(len(raw)).encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": raw, "more_body": False})


def _request(method: str, path: str, *, payload: dict | None = None,
             token: str | None = None, prefer: str | None = None) -> tuple[int, Any]:
    base, key = _base(), _key()
    if not base or not key:
        return 503, {"error": "AUTH_NOT_CONFIGURED"}
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "apikey": key,
        "accept": "application/json",
        "user-agent": "acs-auth-gateway/1.0",
    }
    if data is not None:
        headers["content-type"] = "application/json"
    if token:
        headers["authorization"] = "Bearer " + token
    if prefer:
        headers["prefer"] = prefer
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = int(getattr(response, "status", 200) or 200)
            raw = response.read(_MAX_UPSTREAM + 1)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 502) or 502)
        raw = exc.read(_MAX_UPSTREAM + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 503, {"error": "AUTH_UPSTREAM_UNAVAILABLE"}
    if len(raw) > _MAX_UPSTREAM:
        return 502, {"error": "AUTH_UPSTREAM_RESPONSE_TOO_LARGE"}
    if not raw:
        return status, {}
    try:
        return status, json.loads(raw.decode("utf-8"))
    except Exception:
        return 502, {"error": "AUTH_UPSTREAM_INVALID_RESPONSE"}


def _bearer(scope: dict) -> str:
    headers = dict(scope.get("headers", []))
    raw = headers.get(b"authorization", b"").decode("latin-1", "ignore")
    scheme, sep, token = raw.partition(" ")
    if sep != " " or scheme.lower() != "bearer":
        return ""
    token = token.strip()
    return token if token and len(token) <= 8192 else ""


def _email_password(body: dict) -> tuple[str, str]:
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or "@" not in email or len(email) > 320:
        raise ValueError("invalid email")
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        raise ValueError("invalid password")
    return email.strip(), password


def _safe_auth_error(status: int, payload: Any) -> tuple[int, dict]:
    if status < 400:
        return status, payload if isinstance(payload, dict) else {}
    code = "AUTH_FAILED"
    message = "تعذّر إكمال تسجيل الدخول. تحقّق من البيانات وحاول مجدداً."
    if isinstance(payload, dict):
        upstream_code = payload.get("error_code") or payload.get("code")
        if isinstance(upstream_code, str) and len(upstream_code) <= 80:
            code = upstream_code
        raw = payload.get("msg") or payload.get("message") or payload.get("error_description")
        if isinstance(raw, str) and raw.strip() and len(raw) <= 300:
            message = raw.strip()
    return status, {"ok": False, "error": {"code": code, "message": message}}


def _signup(body: dict) -> tuple[int, dict]:
    email, password = _email_password(body)
    name = body.get("name")
    data = {"name": name.strip()[:160]} if isinstance(name, str) and name.strip() else {}
    status, payload = _request("POST", "/auth/v1/signup", payload={
        "email": email,
        "password": password,
        "data": data,
    })
    return _safe_auth_error(status, payload)


def _signin(body: dict) -> tuple[int, dict]:
    email, password = _email_password(body)
    status, payload = _request(
        "POST", "/auth/v1/token?grant_type=password",
        payload={"email": email, "password": password},
    )
    return _safe_auth_error(status, payload)


def _refresh(body: dict) -> tuple[int, dict]:
    refresh = body.get("refresh_token")
    if not isinstance(refresh, str) or not refresh or len(refresh) > 8192:
        raise ValueError("invalid refresh token")
    status, payload = _request(
        "POST", "/auth/v1/token?grant_type=refresh_token",
        payload={"refresh_token": refresh},
    )
    return _safe_auth_error(status, payload)


def _signout(token: str) -> tuple[int, dict]:
    if not token:
        return 401, {"ok": False, "error": {"code": "AUTH_REQUIRED", "message": "يلزم تسجيل الدخول."}}
    status, payload = _request("POST", "/auth/v1/logout", token=token)
    if status >= 400:
        return _safe_auth_error(status, payload)
    return 200, {"ok": True}


def _bootstrap_project(token: str, body: dict) -> tuple[int, dict]:
    if not token:
        return 401, {"ok": False, "error": {"code": "AUTH_REQUIRED", "message": "يلزم تسجيل الدخول."}}
    status, user = _request("GET", "/auth/v1/user", token=token)
    if status != 200 or not isinstance(user, dict) or not isinstance(user.get("id"), str):
        return 401, {"ok": False, "error": {"code": "AUTH_REQUIRED", "message": "جلسة الدخول غير صالحة."}}
    uid = user["id"]
    q = "/rest/v1/acs_projects?select=id,name,owner_id,created_at&order=created_at.asc&limit=1"
    p_status, projects = _request("GET", q, token=token)
    if p_status >= 400:
        return _safe_auth_error(p_status, projects)
    if isinstance(projects, list) and projects:
        return 200, {"ok": True, "project": projects[0], "created": False, "user": {"id": uid, "email": user.get("email")}}
    name = body.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
        return 400, {"ok": False, "error": {"code": "PROJECT_NAME_REQUIRED", "message": "اكتب اسم المشروع الأول."}}
    c_status, created = _request(
        "POST", "/rest/v1/acs_projects",
        payload={"owner_id": uid, "name": name.strip()}, token=token,
        prefer="return=representation",
    )
    if c_status >= 400:
        return _safe_auth_error(c_status, created)
    row = created[0] if isinstance(created, list) and created else created
    return 200, {"ok": True, "project": row, "created": True, "user": {"id": uid, "email": user.get("email")}}


async def maybe_handle(scope, receive, send) -> bool:
    """Handle one ACS auth route and return True; otherwise return False."""
    if scope.get("type") != "http" or not matches(scope.get("path")):
        return False
    if str(scope.get("method") or "").upper() != "POST":
        await _send(send, 405, {"ok": False, "error": {"code": "METHOD_NOT_ALLOWED", "message": "POST فقط."}})
        return True
    try:
        body = await _read_json(receive)
        path = scope.get("path")
        token = _bearer(scope)
        if path == "/v1/auth/signup":
            status, payload = await asyncio.to_thread(_signup, body)
        elif path == "/v1/auth/signin":
            status, payload = await asyncio.to_thread(_signin, body)
        elif path == "/v1/auth/refresh":
            status, payload = await asyncio.to_thread(_refresh, body)
        elif path == "/v1/auth/signout":
            status, payload = await asyncio.to_thread(_signout, token)
        else:
            status, payload = await asyncio.to_thread(_bootstrap_project, token, body)
    except OverflowError:
        status, payload = 413, {"ok": False, "error": {"code": "INPUT_LIMIT", "message": "الطلب أكبر من الحد المسموح."}}
    except ValueError:
        status, payload = 400, {"ok": False, "error": {"code": "INVALID_AUTH_REQUEST", "message": "بيانات الدخول غير مكتملة أو غير صالحة."}}
    await _send(send, status, payload if isinstance(payload, dict) else {"ok": False})
    return True
