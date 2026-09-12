# -*- coding: utf-8 -*-
"""Request-scoped authenticated PlanStore session factory for ACS.

This is the narrow trust bridge between the already-verified ASGI authentication
boundary and the durable Supabase PlanStore adapter.  It does not register an
HTTP route, parse project authority, or accept actor identity from request data.

The verified Supabase subject comes only from ``scope.state`` populated by
``acs_auth.authorize_asgi``.  The corresponding bearer token is read only from
the current request's Authorization header and is handed directly to the
request-scoped store adapter.  The token is never copied into ``scope.state``,
logged, serialized, or persisted by this module.

Canonical ACS Model authority is unchanged: this factory only creates a durable
PlanStore transport.  CAD/BIM/3D artifacts never become authoring state here.
"""
from __future__ import annotations

import os
from typing import Any, Callable

import acs_auth as AUTH
from acs_plan_review import PlanError
from acs_supabase_plan_store import SupabasePlanStore


_AUTH_REQUIRED = "AUTH_REQUIRED"
_STORE_UNAVAILABLE = "STORE_UNAVAILABLE"
_MAX_BEARER_BYTES = 8192


def _env(name: str) -> str:
    return str(os.environ.get(name, "") or "").strip()


def _header(scope: dict[str, Any], name: bytes) -> str:
    """Return one ASGI header as text without reflecting it into any error."""
    values = []
    for key, value in scope.get("headers") or ():
        if isinstance(key, bytes) and key.lower() == name:
            values.append(value)
    # Multiple Authorization fields are ambiguous and therefore rejected.
    if len(values) != 1 or not isinstance(values[0], bytes):
        return ""
    return values[0].decode("latin-1", "ignore")


def _bearer_token(scope: dict[str, Any]) -> str:
    raw = _header(scope, b"authorization")
    scheme, sep, token = raw.partition(" ")
    token = token.strip()
    if (
        sep != " "
        or scheme.lower() != "bearer"
        or not token
        or len(token.encode("utf-8", "ignore")) > _MAX_BEARER_BYTES
    ):
        raise PlanError(_AUTH_REQUIRED, "Authenticated PlanStore session is required")
    return token


def _verified_actor(scope: dict[str, Any]) -> str:
    state = scope.get("state")
    actor = state.get("authenticated_user_id") if isinstance(state, dict) else None
    if not isinstance(actor, str) or not actor.strip():
        raise PlanError(_AUTH_REQUIRED, "Authenticated PlanStore session is required")
    return actor.strip()


def authenticated_supabase_plan_store(
    scope: dict[str, Any],
    *,
    transport: Callable[..., tuple[int, bytes]] | None = None,
) -> SupabasePlanStore:
    """Construct one actor-bound durable PlanStore from an authorized ASGI scope.

    The caller must be inside the existing authentication middleware.  This
    function deliberately has no ``actor_id`` argument: project/user authority
    cannot be selected by JSON, query string, route parameters, or another host
    input.  ``SupabasePlanStore`` independently validates that the verified
    subject is a UUID before any network request can be issued.
    """
    actor_id = _verified_actor(scope)
    access_token = _bearer_token(scope)

    # The durable adapter is valid only when the same auth boundary that verified
    # the token is explicitly configured for Supabase.  Do not silently fall
    # back to generic OIDC or a local store in production.
    if AUTH.auth_mode() != "oidc" or AUTH.auth_provider() != "supabase":
        raise PlanError(
            _STORE_UNAVAILABLE,
            "Supabase PlanStore requires the authenticated Supabase provider",
        )

    project_url = _env("ACS_AUTH_SUPABASE_URL")
    publishable_key = _env("ACS_AUTH_SUPABASE_PUBLISHABLE_KEY")
    if not project_url or not publishable_key or AUTH.readiness_missing():
        raise PlanError(_STORE_UNAVAILABLE, "Supabase PlanStore is not configured")

    kwargs: dict[str, Any] = {}
    if transport is not None:
        kwargs["transport"] = transport
    return SupabasePlanStore(
        project_url,
        publishable_key,
        access_token,
        actor_id=actor_id,
        **kwargs,
    )
