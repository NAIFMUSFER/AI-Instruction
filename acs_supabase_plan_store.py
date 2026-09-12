"""Authenticated Supabase/PostgREST adapter for ACS Plan-first v2.

The adapter implements :class:`acs_plan_store_port.PlanStorePort` without a
service-role key. Each instance is request/session scoped to one already-verified
Supabase user access token and subject. Database RLS plus the atomic RPC boundary
provide the durable authorization/concurrency enforcement; the Python side keeps
all canonical receipt/hash validation authoritative before any write.

No CAD/BIM/3D artifact is accepted as authoring state here. Only canonical plan
revision and engineer approval receipts cross this boundary.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Callable

from acs_plan_review import PlanError
from acs_plan_store import (
    approval_document,
    revision_document,
    _validate_approval_shape,
    _validate_revision_document,
)
from acs_plan_store_port import SNAPSHOT_SCHEMA

SCHEMA = "acs.plan-store/1.0"
_MAX_RESPONSE_BYTES = 3_000_000

_ERROR_MAP = {
    "ACS_PROJECT_NOT_FOUND": ("PROJECT_NOT_FOUND", "Project does not exist or is not accessible"),
    "ACS_PROJECT_ACCESS_DENIED": ("PROJECT_ACCESS_DENIED", "Authenticated actor lacks the required project role"),
    "ACS_STALE_REVISION": ("STALE_REVISION", "Persisted project head changed; rebase explicitly"),
    "ACS_INVALID_REVISION_CHAIN": ("INVALID_REVISION_CHAIN", "Revision chain does not match persisted head"),
    "ACS_REVISION_EXISTS": ("REVISION_EXISTS", "Revision/version already exists in this project"),
    "ACS_REVISION_NOT_FOUND": ("REVISION_NOT_FOUND", "Approval revision is not persisted"),
    "ACS_APPROVAL_RECEIPT_CHANGED": ("APPROVAL_RECEIPT_CHANGED", "Approval does not match persisted revision/lock receipt"),
    "ACS_APPROVAL_EXISTS": ("APPROVAL_EXISTS", "Approval receipt is immutable once persisted"),
}


def _uuid(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise PlanError("INVALID_IDENTITY", f"{label} must be a UUID string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise PlanError("INVALID_IDENTITY", f"{label} must be a UUID string") from exc
    if str(parsed) != value.lower():
        value = str(parsed)
    return value


def _bounded_text(value: Any, label: str, *, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise PlanError("INVALID_STORED_VALUE", f"{label} must be non-empty and bounded")
    return value.strip()


class SupabasePlanStore:
    """PlanStorePort implemented over Supabase PostgREST with user JWT identity."""

    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        access_token: str,
        *,
        actor_id: str,
        timeout_s: float = 8.0,
        transport: Callable[..., tuple[int, bytes]] | None = None,
    ):
        try:
            parsed = urllib.parse.urlsplit(project_url)
        except Exception as exc:
            raise PlanError("INVALID_STORE", "Supabase project URL is invalid") from exc
        if (
            parsed.scheme.lower() != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise PlanError("INVALID_STORE", "Supabase project URL must be an HTTPS origin")
        self._base = project_url.rstrip("/")
        self._publishable_key = _bounded_text(publishable_key, "publishable_key", limit=4096)
        self._access_token = _bounded_text(access_token, "access_token", limit=8192)
        self._actor_id = _uuid(actor_id, "actor_id")
        self._timeout_s = min(20.0, max(1.0, float(timeout_s)))
        self._transport = transport or self._urllib_transport

    @property
    def actor_id(self) -> str:
        return self._actor_id

    def _assert_actor(self, actor_id: str) -> None:
        if _uuid(actor_id, "actor_id") != self._actor_id:
            raise PlanError(
                "PROJECT_ACCESS_DENIED",
                "Store actor must match the authenticated Supabase subject",
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self._access_token,
            "apikey": self._publishable_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "acs-plan-store/2.0",
        }

    @staticmethod
    def _urllib_transport(*, method: str, url: str, headers: dict[str, str],
                          body: bytes | None, timeout: float) -> tuple[int, bytes]:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
                return int(response.status), raw
        except urllib.error.HTTPError as exc:
            raw = exc.read(_MAX_RESPONSE_BYTES + 1)
            return int(exc.code), raw
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PlanError("STORE_UNAVAILABLE", "Supabase plan store is unavailable") from exc

    def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        body = None
        if payload is not None:
            try:
                body = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"), allow_nan=False).encode("utf-8")
            except (TypeError, ValueError, OverflowError, RecursionError) as exc:
                raise PlanError("INVALID_STORED_VALUE", "Supabase payload is not valid JSON") from exc
        status, raw = self._transport(
            method=method,
            url=self._base + path,
            headers=self._headers(),
            body=body,
            timeout=self._timeout_s,
        )
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise PlanError("STORE_UNAVAILABLE", "Supabase response exceeded the bounded store contract")
        if status in (401, 403):
            raise PlanError("PROJECT_ACCESS_DENIED", "Authenticated actor lacks project access")
        if status < 200 or status >= 300:
            marker = None
            try:
                err = json.loads(raw.decode("utf-8")) if raw else {}
                msg = err.get("message") if isinstance(err, dict) else None
                marker = msg if isinstance(msg, str) else None
            except Exception:
                marker = None
            mapped = _ERROR_MAP.get(marker)
            if mapped:
                raise PlanError(mapped[0], mapped[1])
            raise PlanError("STORE_UNAVAILABLE", "Supabase plan-store request failed closed")
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise PlanError("STORE_UNAVAILABLE", "Supabase returned malformed JSON") from exc

    def _rpc(self, name: str, payload: dict) -> dict:
        result = self._request("POST", "/rest/v1/rpc/" + name, payload)
        if not isinstance(result, dict):
            raise PlanError("STORE_UNAVAILABLE", "Supabase RPC returned an invalid document")
        return result

    def create_project(self, *, name: str) -> dict:
        """Create a cloud store aggregate for this authenticated user.

        The generated UUID is storage/session identity only; it is not injected into
        the Canonical ACS Model and therefore cannot become geometry/source authority.
        """
        name = _bounded_text(name, "project_name", limit=200)
        result = self._request(
            "POST",
            "/rest/v1/acs_projects?select=id,owner_id,name,head_revision_id,baseline_revision_id",
            {"owner_id": self._actor_id, "name": name},
        )
        if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
            raise PlanError("STORE_UNAVAILABLE", "Supabase project creation returned an invalid receipt")
        row = result[0]
        project_id = _uuid(row.get("id"), "project_id")
        if _uuid(row.get("owner_id"), "owner_id") != self._actor_id:
            raise PlanError("STORED_PROJECT_TAMPERED", "Created project owner receipt is inconsistent")
        return {
            "schema": SCHEMA,
            "project_id": project_id,
            "owner_id": self._actor_id,
            "name": row.get("name"),
            "head_revision_id": row.get("head_revision_id"),
            "baseline_revision_id": row.get("baseline_revision_id"),
        }

    def project_state(self, project_id: str, *, actor_id: str) -> dict:
        self._assert_actor(actor_id)
        project_id = _uuid(project_id, "project_id")
        state = self._rpc("acs_plan_project_state", {"p_project": project_id})
        if state.get("schema") != SCHEMA or _uuid(state.get("project_id"), "project_id") != project_id:
            raise PlanError("STORED_PROJECT_TAMPERED", "Supabase project-state receipt is inconsistent")
        if state.get("role") not in {"owner", "editor", "viewer"}:
            raise PlanError("STORED_PROJECT_TAMPERED", "Supabase project role is malformed")
        if not isinstance(state.get("revisions"), list):
            raise PlanError("STORED_PROJECT_TAMPERED", "Supabase revision summary is malformed")
        return state

    def workspace_snapshot(self, project_id: str, *, actor_id: str) -> dict:
        self._assert_actor(actor_id)
        project_id = _uuid(project_id, "project_id")
        snapshot = self._rpc("acs_plan_workspace_snapshot", {"p_project": project_id})
        if snapshot.get("schema") != SNAPSHOT_SCHEMA or _uuid(snapshot.get("project_id"), "project_id") != project_id:
            raise PlanError("STORED_PROJECT_TAMPERED", "Supabase workspace snapshot identity is inconsistent")
        revisions = snapshot.get("revisions")
        approvals = snapshot.get("approvals")
        if not isinstance(revisions, list) or not isinstance(approvals, list):
            raise PlanError("STORED_PROJECT_TAMPERED", "Supabase workspace snapshot is malformed")
        for doc in revisions:
            _validate_revision_document(doc)
        for doc in approvals:
            _validate_approval_shape(doc)
        return snapshot

    def save_revision(self, project_id: str, *, actor_id: str,
                      revision: Any, expected_head: str | None) -> dict:
        self._assert_actor(actor_id)
        project_id = _uuid(project_id, "project_id")
        doc = revision_document(revision)
        if expected_head is not None:
            _bounded_text(expected_head, "expected_head", limit=160)
        result = self._rpc("acs_save_plan_revision", {
            "p_project": project_id,
            "p_expected_head": expected_head,
            "p_revision": doc,
        })
        _validate_revision_document(result)
        if result != doc:
            raise PlanError("STORED_REVISION_TAMPERED", "Supabase write receipt changed the canonical revision")
        return result

    def save_approval(self, project_id: str, *, actor_id: str,
                      approval: Any, expected_head: str) -> dict:
        self._assert_actor(actor_id)
        project_id = _uuid(project_id, "project_id")
        expected_head = _bounded_text(expected_head, "expected_head", limit=160)
        doc = approval_document(approval)
        result = self._rpc("acs_save_plan_approval", {
            "p_project": project_id,
            "p_expected_head": expected_head,
            "p_approval": doc,
        })
        _validate_approval_shape(result)
        if result != doc:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Supabase write receipt changed the approval")
        return result
