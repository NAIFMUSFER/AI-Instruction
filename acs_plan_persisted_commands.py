"""Persist trusted Plan-first commands against the durable project store.

This module composes the already-audited command boundary, lock-bound workspace
reload, and optimistic SQLite persistence.  It is intentionally not an HTTP route
and does not authenticate callers.  A host must resolve ``project_id`` and
``actor_id`` from an authenticated project session and provide the real verifier
and provider configuration.

The Canonical ACS Model remains the source of truth.  This adapter never invokes
3D/BIM/export code and never permits a client command to select project authority.
"""
from __future__ import annotations

from typing import Any

from acs_plan_commands import execute_plan_command
from acs_plan_lock_binding import BoundApproval
from acs_plan_review import PlanError, canonical
from acs_plan_store import SQLitePlanStore
from acs_plan_store_reload import load_workspace


SCHEMA = "acs.plan-persisted-command-result/1.0"
_FORBIDDEN_PROJECT_FIELDS = frozenset({
    "project_id", "project", "workspace_id", "tenant_id",
})


def _trusted_command(value: Any) -> dict:
    if not isinstance(value, dict):
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command must be an object")
    canonical(value)
    if _FORBIDDEN_PROJECT_FIELDS.intersection(value):
        raise PlanError(
            "CLIENT_PROJECT_AUTHORITY",
            "Project/workspace authority must come from the authenticated host session",
        )
    return value


def _approval_from_result(workspace, result: dict, actor_id: str) -> BoundApproval:
    """Reconstruct the exact immutable approval receipt for store admission.

    The public command result deliberately omits actor identity and duplicate model
    hashes.  Those values are recovered only from trusted host identity and the
    lock-bound canonical workspace; the store independently revalidates every hash.
    """
    meta = result.get("approval")
    revision_id = workspace.baseline
    if not isinstance(meta, dict) or not isinstance(revision_id, str):
        raise PlanError("APPROVAL_RECEIPT_CHANGED", "Command did not produce an approval receipt")
    bound = workspace.get(revision_id)
    if (
        meta.get("revision_id") != revision_id
        or meta.get("bound_content_hash") != bound.bound_content_hash
        or meta.get("semantic_lock_manifest_hash") != bound.semantic_lock_manifest_hash
        or meta.get("semantic_lock_count") != bound.semantic_lock_count
    ):
        raise PlanError("APPROVAL_RECEIPT_CHANGED", "Command approval no longer matches the canonical revision")
    approved_at = meta.get("approved_at")
    scope = meta.get("scope")
    if not isinstance(approved_at, str) or not approved_at or scope != "CONCEPTUAL_DESIGN_ONLY":
        raise PlanError("APPROVAL_RECEIPT_CHANGED", "Command approval metadata is malformed")
    return BoundApproval(
        revision_id=revision_id,
        revision_content_hash=bound.content_hash,
        bound_content_hash=bound.bound_content_hash,
        model_hash=bound.model_hash,
        semantic_lock_manifest_hash=bound.semantic_lock_manifest_hash,
        semantic_lock_count=bound.semantic_lock_count,
        actor_label=actor_id.strip(),
        approved_at=approved_at,
        scope=scope,
    )


def execute_persisted_plan_command(
    store: SQLitePlanStore,
    project_id: str,
    command: dict,
    *,
    actor_id: str,
    provider_model=None,
    verifier=None,
) -> dict:
    """Execute one trusted project command and durably persist its exact result.

    Owner/editor authorization is enforced by ``load_workspace`` before a mutable
    aggregate is returned.  No database transaction is held across provider work.
    The subsequent store write uses the captured persisted head as an optimistic
    concurrency token, so a concurrent winner causes ``STALE_REVISION`` rather
    than a silent rebase or lost update.

    This boundary is deliberately writable-only: viewers continue to use the
    store's read-only APIs and are not handed a mutable workspace.
    """
    if not isinstance(store, SQLitePlanStore):
        raise PlanError("INVALID_STORE", "Persisted commands require SQLitePlanStore")
    command = _trusted_command(command)

    before = store.project_state(project_id, actor_id=actor_id)
    expected_head = before["head_revision_id"]
    expected_baseline = before["baseline_revision_id"]

    workspace = load_workspace(
        store, project_id, actor_id=actor_id, verifier=verifier,
    )
    if workspace.head != expected_head or workspace.baseline != expected_baseline:
        raise PlanError("STORED_PROJECT_TAMPERED", "Reloaded project pointers changed before command execution")

    result = execute_plan_command(
        workspace,
        command,
        actor_id=actor_id,
        provider_model=provider_model,
    )

    revision_persisted = False
    approval_persisted = False

    if workspace.head != expected_head:
        if workspace.head is None:
            raise PlanError("INVALID_REVISION_CHAIN", "Command removed the project head")
        store.save_revision(
            project_id,
            actor_id=actor_id,
            revision=workspace.get(workspace.head),
            expected_head=expected_head,
        )
        revision_persisted = True

    if workspace.baseline != expected_baseline:
        approval = _approval_from_result(workspace, result, actor_id)
        store.save_approval(
            project_id,
            actor_id=actor_id,
            approval=approval,
            expected_head=workspace.head,
        )
        approval_persisted = True

    after = store.project_state(project_id, actor_id=actor_id)
    if not revision_persisted and not approval_persisted:
        # Read-only commands must not return a stale snapshot as though it were
        # current when another writer won while this command was executing.
        if (
            after["head_revision_id"] != expected_head
            or after["baseline_revision_id"] != expected_baseline
        ):
            raise PlanError("STALE_REVISION", "Persisted project changed while the command was executing")

    out = dict(result)
    out["persistence"] = {
        "schema": SCHEMA,
        "head_revision_id": after["head_revision_id"],
        "baseline_revision_id": after["baseline_revision_id"],
        "revision_persisted": revision_persisted,
        "approval_persisted": approval_persisted,
    }
    return out
