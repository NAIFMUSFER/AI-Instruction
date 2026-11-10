"""Authenticated Supabase/PostgREST adapter for ACS Plan-first v2.

The adapter implements :class:`acs_plan_store_port.PlanStorePort` without a
service-role key. Each instance is request/session scoped to one already-verified
Supabase user access token and subject. Database RLS plus the atomic RPC boundary
provide durable authorization/concurrency enforcement. Receipt writes additionally
require a short-lived HMAC capability made only after Python canonical validation.
The dedicated signer is not an identity credential and cannot replace the user JWT.

No CAD/BIM/3D artifact is accepted as authoring state here. Only canonical plan
revision and engineer approval receipts cross this boundary.
"""
from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Callable

from acs_plan_review import MAX_REVISIONS, PlanError, _structure, _validate_provenance_links
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
    "JOB_LEASE_LOST": ("JOB_LEASE_LOST", "Worker no longer owns the durable job lease"),
    "JOB_RATE_LIMITED": ("JOB_RATE_LIMITED", "Durable generation quota is exhausted"),
    "GENERATION_BUSY": ("GENERATION_BUSY", "Durable generation concurrency is full"),
    "INVALID_RESUME": ("INVALID_RESUME", "Job cannot be resumed safely"),
    "INVALID_JOB_COMMAND": ("INVALID_JOB_COMMAND", "Durable job command is invalid"),
    "INVALID_JOB_PROGRESS": ("INVALID_JOB_PROGRESS", "Durable job progress is invalid"),
    "PROJECT_ACCESS_DENIED": ("PROJECT_ACCESS_DENIED", "Authenticated actor lacks project access"),
    "STALE_REVISION": ("STALE_REVISION", "Persisted project head changed; rebase explicitly"),
    "REVISION_NOT_FOUND": ("REVISION_NOT_FOUND", "Requested revision is not persisted"),
    "ACS_INVALID_REVISION_RECEIPT": ("INVALID_REVISION_RECEIPT", "Canonical revision receipt is invalid"),
    "ACS_INVALID_APPROVAL_RECEIPT": ("INVALID_APPROVAL_RECEIPT", "Conceptual approval receipt is invalid"),
    "ACS_VALIDATED_WRITE_REQUIRED": ("PROJECT_ACCESS_DENIED", "Validated backend write capability is required"),
    "ACS_WRITE_BOUNDARY_UNAVAILABLE": ("STORE_UNAVAILABLE", "Validated write boundary is not configured"),
    "ACS_JOB_LEASE_LOST": ("JOB_LEASE_LOST", "Worker no longer owns the durable job lease"),
    "ACS_HISTORY_LIMIT": ("HISTORY_LIMIT", "Workspace has reached its admitted revision limit"),
    "ACS_HISTORY_PAGE_INVALID": ("STORE_UNAVAILABLE", "Invalid history pagination response"),
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
        write_secret: str | None = None,
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
        # Separate backend validation capability, never an auth/service-role key.
        # Reads remain available during signer setup; writes fail before network.
        self._write_secret = (write_secret if write_secret is not None
                              else os.environ.get("ACS_PLAN_WRITE_SECRET", ""))
        self._lease_context = None

    @property
    def actor_id(self) -> str:
        return self._actor_id

    def _assert_actor(self, actor_id: str) -> None:
        if _uuid(actor_id, "actor_id") != self._actor_id:
            raise PlanError(
                "PROJECT_ACCESS_DENIED",
                "Store actor must match the authenticated Supabase subject",
            )

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": "Bearer " + self._access_token,
            "apikey": self._publishable_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "acs-plan-store/2.0",
        }
        if prefer is not None:
            headers["Prefer"] = prefer
        return headers

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

    def _request(self, method: str, path: str, payload: dict | None = None,
                 *, prefer: str | None = None) -> Any:
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
            headers=self._headers(prefer=prefer),
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

    def _signed_rpc(self, name: str, kind: str, project_id: str,
                    expected_head: str | None, doc: dict) -> dict:
        if not isinstance(self._write_secret, str) or not re.fullmatch(r"[0-9a-f]{64}", self._write_secret):
            raise PlanError("STORE_UNAVAILABLE", "Validated write boundary is not configured")
        envelope = {
            "schema": "acs.validated-write/1.0", "kind": kind,
            "actor_id": self._actor_id, "project_id": project_id,
            "expected_head": expected_head, "expires_at": int(time.time()) + 60,
            "document": doc, "write_context": self._lease_context,
        }
        raw = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
        if len(raw.encode("utf-8")) > 2_600_000:
            raise PlanError("STORE_INPUT_LIMIT", "Validated write exceeds its admitted size")
        signature = hmac.new(self._write_secret.encode("ascii"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
        return self._rpc(name, {"p_payload": raw, "p_signature": signature})

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
            prefer="return=representation",
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
        # Metadata is transported in bounded pages; immutable documents are read
        # one at a time. Total project history no longer shares one 3 MB response.
        after = 0
        head = baseline = None
        metadata = []
        while True:
            page = self._rpc("acs_plan_revision_page", {
                "p_project": project_id, "p_after": after, "p_limit": 25, "p_head": head,
            })
            if (page.get("schema") != "acs.plan-revision-page/1.0"
                    or page.get("project_id") != project_id
                    or not isinstance(page.get("revisions"), list)
                    or len(page["revisions"]) > 25):
                raise PlanError("STORED_PROJECT_TAMPERED", "History metadata page is inconsistent")
            if page.get("role") not in {"owner", "editor"}:
                raise PlanError("PROJECT_ACCESS_DENIED", "Writable recovery requires editor membership")
            pointers = (page.get("head_revision_id"), page.get("baseline_revision_id"))
            if after == 0:
                head, baseline = pointers
            elif pointers != (head, baseline):
                raise PlanError("STALE_REVISION", "Project changed during recovery; reload explicitly")
            for item in page["revisions"]:
                if (not isinstance(item, dict) or type(item.get("number")) is not int
                        or item["number"] != len(metadata) + 1
                        or not isinstance(item.get("revision_id"), str)):
                    raise PlanError("INVALID_REVISION_CHAIN", "History metadata chain is malformed")
                metadata.append(item)
            if len(metadata) > MAX_REVISIONS:
                raise PlanError("HISTORY_LIMIT", "Persisted history exceeds its admitted revision limit")
            next_after = page.get("next_after")
            if next_after is None:
                break
            if (type(next_after) is not int or next_after <= after
                    or next_after != len(metadata) or not page["revisions"]):
                raise PlanError("STORED_PROJECT_TAMPERED", "History cursor failed to advance")
            after = next_after
        revisions, approvals = [], []
        for item in metadata:
            result = self._rpc("acs_plan_revision_document", {
                "p_project": project_id, "p_revision": item["revision_id"], "p_head": head,
            })
            if (result.get("schema") != "acs.plan-revision-document/1.0"
                    or result.get("project_id") != project_id):
                raise PlanError("STORED_PROJECT_TAMPERED", "Revision response identity changed")
            doc = result.get("revision")
            _validate_revision_document(doc)
            if any(doc.get(key) != item.get(key) for key in
                   ("revision_id", "number", "parent_id", "content_hash", "bound_content_hash")):
                raise PlanError("STORED_REVISION_TAMPERED", "Revision no longer matches its metadata")
            revisions.append(doc)
            approval = result.get("approval")
            if approval is not None:
                _validate_approval_shape(approval)
                if approval["revision_id"] != doc["revision_id"]:
                    raise PlanError("STORED_APPROVAL_TAMPERED", "Approval response identity changed")
                approvals.append(approval)
        # An append/approval during paged recovery must never produce a hybrid
        # workspace. A retry is explicit and no provider work has been performed.
        final = self.project_state(project_id, actor_id=actor_id)
        if (final.get("head_revision_id"), final.get("baseline_revision_id")) != (head, baseline):
            raise PlanError("STALE_REVISION", "Project changed during recovery; reload explicitly")
        return {"schema": SNAPSHOT_SCHEMA, "project_id": project_id,
                "head_revision_id": head, "baseline_revision_id": baseline,
                "revisions": revisions, "approvals": approvals}

    def save_revision(self, project_id: str, *, actor_id: str,
                      revision: Any, expected_head: str | None) -> dict:
        self._assert_actor(actor_id)
        project_id = _uuid(project_id, "project_id")
        doc = revision_document(revision)
        if expected_head is not None:
            _bounded_text(expected_head, "expected_head", limit=160)
        _structure(doc["model"])
        _validate_provenance_links(doc["model"], doc["requirements"])
        if doc["number"] > MAX_REVISIONS:
            raise PlanError("HISTORY_LIMIT", "Workspace has reached its admitted revision limit")
        result = self._signed_rpc("acs_write_plan_receipt", "revision", project_id, expected_head, doc)
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
        result = self._signed_rpc("acs_write_plan_receipt", "approval", project_id, expected_head, doc)
        _validate_approval_shape(result)
        if result != doc:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Supabase write receipt changed the approval")
        return result
