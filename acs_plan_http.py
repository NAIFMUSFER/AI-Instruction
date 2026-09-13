# -*- coding: utf-8 -*-
"""Authenticated ASGI boundary for durable ACS Plan-first commands.

This module is deliberately narrow. It exposes only the already-audited
Plan-first command surface over one project-scoped HTTP route, authenticates
before reading the request body, binds actor identity to the verified Supabase
session, and delegates persistence to the request-scoped ``SupabasePlanStore``.

The Canonical ACS Model remains the source of truth. This boundary has no BIM,
3D, CAD, export, compiler, or post-approval replanning route. Provider-backed
``chat_edit`` is intentionally fail-closed here until it is executed through the
existing isolated job boundary rather than on the request event loop.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import acs_api_errors as E
import acs_auth as AUTH
import acs_plan_bridge as BRIDGE
import acs_plan_persisted_commands as PERSIST
import acs_plan_session as SESSION
from acs_plan_review import PlanError, canonical


MAX_BODY_BYTES = 128 * 1024
_ROUTE_PREFIX = "/v1/projects/"
_ROUTE_SUFFIX = "/plan/commands"
_ALLOWED_NON_PROVIDER_ACTIONS = frozenset({
    "review",
    "replace_semantic_locks",
    "set_room_lock",
    "compare",
    "restore",
    "approve",
})
_PROVIDER_ACTION = "chat_edit"


def _request_id(scope: dict[str, Any]) -> str:
    state = scope.setdefault("state", {})
    rid = state.get("request_id")
    if isinstance(rid, str) and rid:
        return rid[:64]
    rid = E.new_request_id()
    state["request_id"] = rid
    return rid


def _error_status(code: str) -> int:
    if code in {"AUTH_REQUIRED", "ACS_PROJECT_ACCESS_DENIED"}:
        return 403
    if code in {
        "ACS_PROJECT_NOT_FOUND",
        "REVISION_NOT_FOUND",
        "PLAN_PROJECT_ROUTE_NOT_FOUND",
    }:
        return 404
    if code in {
        "STALE_REVISION",
        "ACS_STALE_REVISION",
        "ACS_REVISION_EXISTS",
        "ACS_APPROVAL_EXISTS",
    }:
        return 409
    if code in {
        "STORE_UNAVAILABLE",
        "PLAN_PROVIDER_COMMAND_REQUIRES_ISOLATED_JOB",
    }:
        return 503
    if code in {"INPUT_LIMIT", "PLAN_COMMAND_BODY_TOO_LARGE"}:
        return 413
    return 400


async def _send_json(scope: dict[str, Any], send, status: int, payload: dict) -> None:
    rid = _request_id(scope)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"cache-control", b"no-store, private"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-request-id", rid.encode("ascii", "ignore")),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})


async def _send_plan_error(scope: dict[str, Any], send, exc: PlanError) -> None:
    code = str(getattr(exc, "code", "INVALID_PLAN_COMMAND") or "INVALID_PLAN_COMMAND")
    await _send_json(
        scope,
        send,
        _error_status(code),
        {
            "ok": False,
            "error": {
                "code": code,
                "message": str(exc),
                "request_id": _request_id(scope),
                "retryable": False,
                "upstream": None,
            },
            "contract": E.ERROR_CONTRACT_VERSION,
        },
    )


def _project_from_path(path: Any) -> tuple[bool, str | None]:
    if not isinstance(path, str):
        return False, None
    if not path.startswith(_ROUTE_PREFIX) or not path.endswith(_ROUTE_SUFFIX):
        return False, None
    raw = path[len(_ROUTE_PREFIX):-len(_ROUTE_SUFFIX)]
    if not raw or "/" in raw:
        return True, None
    try:
        project_id = str(uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        return True, None
    # Do not admit alternate textual identities (hyphenless, braced, uppercase).
    # The route is an authorization selector, so one canonical spelling avoids
    # cache/log/audit ambiguity before membership/RPC authorization runs.
    if raw != project_id:
        return True, None
    return True, project_id


async def _read_json(receive) -> dict:
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if not isinstance(message, dict):
            raise PlanError("INVALID_PLAN_COMMAND", "Request body is unavailable")
        if message.get("type") == "http.disconnect":
            raise PlanError("INVALID_PLAN_COMMAND", "Request disconnected before command admission")
        if message.get("type") != "http.request":
            continue
        chunk = message.get("body", b"")
        if not isinstance(chunk, (bytes, bytearray)):
            raise PlanError("INVALID_PLAN_COMMAND", "Request body is malformed")
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise PlanError("PLAN_COMMAND_BODY_TOO_LARGE", "Plan-first command body exceeds the bounded request limit")
        if chunk:
            chunks.append(bytes(chunk))
        if not message.get("more_body", False):
            break
    try:
        raw = b"".join(chunks).decode("utf-8")
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command body must be valid UTF-8 JSON") from None
    if not isinstance(value, dict):
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command body must be one JSON object")
    canonical(value)
    return value


class PlanCommandMiddleware:
    """Intercept exactly one authenticated project command route.

    Authentication runs before ``receive`` is touched. The project UUID is route
    selection only; effective authorization remains the actor-bound Supabase
    membership/RPC contract. Client JSON cannot supply project or actor authority.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        matched, project_id = _project_from_path(scope.get("path"))
        if not matched:
            return await self.app(scope, receive, send)
        if project_id is None:
            return await _send_plan_error(
                scope,
                send,
                PlanError("PLAN_PROJECT_ROUTE_NOT_FOUND", "Plan-first project route requires a canonical UUID"),
            )
        if str(scope.get("method") or "").upper() != "POST":
            return await _send_json(
                scope,
                send,
                405,
                {
                    "ok": False,
                    "error": {
                        "code": "PLAN_COMMAND_METHOD_NOT_ALLOWED",
                        "message": "Plan-first command route accepts POST only",
                        "request_id": _request_id(scope),
                        "retryable": False,
                        "upstream": None,
                    },
                    "contract": E.ERROR_CONTRACT_VERSION,
                },
            )

        # Critical ordering: verify the bearer and establish the trusted subject
        # before any request-body byte is consumed.
        if not await AUTH.authorize_asgi(scope, send):
            return None

        try:
            command = await _read_json(receive)
            action = command.get("action")
            if action == _PROVIDER_ACTION:
                raise PlanError(
                    "PLAN_PROVIDER_COMMAND_REQUIRES_ISOLATED_JOB",
                    "Provider-backed Plan-first edits are not enabled until isolated job execution is wired",
                )
            if action not in _ALLOWED_NON_PROVIDER_ACTIONS:
                raise PlanError(
                    "PLAN_COMMAND_NOT_SUPPORTED",
                    "This command is not exposed by the authenticated HTTP boundary",
                )

            state = scope.get("state")
            actor_id = state.get("authenticated_user_id") if isinstance(state, dict) else None
            if not isinstance(actor_id, str) or not actor_id.strip():
                raise PlanError("AUTH_REQUIRED", "Authenticated PlanStore session is required")

            store = SESSION.authenticated_supabase_plan_store(scope)
            result = await asyncio.to_thread(
                PERSIST.execute_persisted_plan_command,
                store,
                project_id,
                command,
                actor_id=actor_id.strip(),
                provider_model=None,
                verifier=BRIDGE.existing_geometry_verifier,
            )
        except PlanError as exc:
            return await _send_plan_error(scope, send, exc)
        except Exception:
            # Do not reflect transport/provider/database exception details or
            # credentials. The host log/envelope layer may record only its own
            # request identifier around this opaque internal failure.
            return await _send_json(
                scope,
                send,
                500,
                {
                    "ok": False,
                    "error": {
                        "code": "PLAN_COMMAND_INTERNAL",
                        "message": "Plan-first command failed inside the trusted host boundary",
                        "request_id": _request_id(scope),
                        "retryable": False,
                        "upstream": None,
                    },
                    "contract": E.ERROR_CONTRACT_VERSION,
                },
            )

        return await _send_json(
            scope,
            send,
            200,
            {
                "ok": True,
                "result": result,
                "contract": E.ERROR_CONTRACT_VERSION,
            },
        )
