"""Closed server-side command boundary for the ACS Plan-first workspace.

This module is intentionally NOT a public HTTP route and does not authenticate a
caller. A trusted host must resolve ``actor_id`` from its authenticated project
session before calling :func:`execute_plan_command`. Client payloads never get to
supply actor authority, detached lock manifests, or replacement canonical models.

The Canonical ACS Model remains the source of truth. Commands only compose the
existing revision/lock/review contracts; no 3D/BIM/compiler path is exposed here.
"""
from __future__ import annotations

from typing import Any

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError, canonical
from acs_plan_semantic_diff import diff_models
from tools.acs_plan_review_packet import build_review_packet

SCHEMA = "acs.plan-command-result/1.0"
MAX_ACTOR_ID_CHARS = 256

# Fields whose authority must come from the trusted host/server-side workspace,
# never from an untrusted browser command payload.
_FORBIDDEN_CLIENT_FIELDS = frozenset({
    "actor_id", "actor_label", "user_id", "owner_id",
    "semantic_lock_manifest", "lock_manifest",
    "building", "model", "canonical_model",
    "approval_receipt", "bound_content_hash",
})


def _authenticated_actor(actor_id: Any) -> str:
    if (not isinstance(actor_id, str) or not actor_id.strip()
            or len(actor_id) > MAX_ACTOR_ID_CHARS):
        raise PlanError(
            "AUTHENTICATED_ACTOR_REQUIRED",
            "The host must resolve an authenticated actor before Plan-first commands",
        )
    return actor_id.strip()


def _command(value: Any) -> dict:
    if not isinstance(value, dict):
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command must be an object")
    # Reuse the canonical bounded-JSON contract before inspecting nested payloads.
    canonical(value)
    action = value.get("action")
    if not isinstance(action, str) or not action.strip():
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command action is required")
    forbidden = _FORBIDDEN_CLIENT_FIELDS.intersection(value)
    if forbidden:
        raise PlanError(
            "CLIENT_AUTHORITY_FIELD",
            "Client command contains server-authoritative fields",
        )
    return value


def _workspace(value: Any) -> PlanLockWorkspace:
    if not isinstance(value, PlanLockWorkspace):
        raise PlanError(
            "INVALID_WORKSPACE",
            "Writable Plan-first commands require the lock-bound canonical workspace",
        )
    return value


def _head(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError("STALE_REVISION", "A current expected revision is required")
    return value


def _semantic_diff(workspace: PlanLockWorkspace, reference_revision_id: str,
                   target_revision_id: str) -> dict:
    reference = workspace.get(reference_revision_id)
    target = workspace.get(target_revision_id)
    result = diff_models(reference.model, target.model)
    result["reference_revision_id"] = reference.id
    result["target_revision_id"] = target.id
    return result


def _view_result(workspace: PlanLockWorkspace, action: str, revision_id: str,
                 *, reference_revision_id: str | None = None) -> dict:
    report = workspace.review(revision_id)
    result = {
        "schema": SCHEMA,
        "action": action,
        "head": workspace.head,
        "baseline": workspace.baseline,
        "revision_id": revision_id,
        "history": workspace.history(),
        "authority": {
            # This is only schematic readiness computed by the trusted workspace.
            # It is not statutory, structural or professional certification.
            "can_approve_concept": report.get("can_approve") is True,
            "construction_approved": False,
        },
        "review_packet": build_review_packet(workspace, revision_id),
    }
    if reference_revision_id is not None:
        result["semantic_diff"] = _semantic_diff(
            workspace, reference_revision_id, revision_id,
        )
    return result


def execute_plan_command(workspace: PlanLockWorkspace, command: dict, *,
                         actor_id: str, provider_model=None) -> dict:
    """Execute one host-authorized Plan-first UI command.

    ``actor_id`` is a host-resolved identity, not a value accepted from ``command``.
    ``provider_model`` is likewise host configuration. The function intentionally
    exposes no 3D/BIM/export command; those remain behind the explicit approved
    Frozen-Baseline handoff/export boundaries.
    """
    actor = _authenticated_actor(actor_id)
    workspace = _workspace(workspace)
    command = _command(command)
    action = command["action"].strip()

    if action == "review":
        revision_id = command.get("revision_id")
        if not isinstance(revision_id, str) or not revision_id:
            raise PlanError("REVISION_NOT_FOUND", "Review requires an explicit revision")
        return _view_result(workspace, action, revision_id)

    if action == "chat_edit":
        expected = _head(command.get("expected_head"))
        from acs_plan_bridge import propose_bound_chat_edit
        revision = propose_bound_chat_edit(
            workspace, command.get("notes"), expected_head=expected,
            model=provider_model,
        )
        return _view_result(
            workspace, action, revision.id, reference_revision_id=expected,
        )

    if action == "replace_semantic_locks":
        expected = _head(command.get("expected_head"))
        revision = workspace.replace_semantic_locks(
            command.get("selectors"), expected_head=expected,
            note=command.get("note"),
        )
        return _view_result(
            workspace, action, revision.id, reference_revision_id=expected,
        )

    if action == "set_room_lock":
        expected = _head(command.get("expected_head"))
        ref = command.get("room_ref")
        if not isinstance(ref, list) or len(ref) != 2 or not all(
                isinstance(v, str) and v for v in ref):
            raise PlanError("ROOM_NOT_FOUND", "Room lock requires [template, room_id]")
        revision = workspace.set_room_lock(
            tuple(ref), locked=command.get("locked"), expected_head=expected,
        )
        return _view_result(
            workspace, action, revision.id, reference_revision_id=expected,
        )

    if action == "compare":
        reference_revision_id = command.get("reference_revision_id")
        target_revision_id = command.get("target_revision_id")
        comparison = workspace.compare_revisions(
            reference_revision_id,
            target_revision_id,
        )
        return {
            "schema": SCHEMA,
            "action": action,
            "head": workspace.head,
            "baseline": workspace.baseline,
            "comparison": comparison,
            "semantic_diff": _semantic_diff(
                workspace, reference_revision_id, target_revision_id,
            ),
        }

    if action == "restore":
        expected = _head(command.get("expected_head"))
        revision = workspace.restore_revision(
            command.get("source_revision_id"), expected_head=expected,
            note=command.get("note"),
        )
        return _view_result(
            workspace, action, revision.id, reference_revision_id=expected,
        )

    if action == "approve":
        expected = _head(command.get("expected_head"))
        receipt = workspace.approve(
            expected, expected_head=expected, actor_label=actor,
            confirmed=command.get("confirmed"),
            acknowledge_concept_only=command.get("acknowledge_concept_only"),
        )
        result = _view_result(workspace, action, expected)
        # Do not echo actor identity. The server-side receipt keeps it for audit.
        result["approval"] = {
            "revision_id": receipt.revision_id,
            "approved_at": receipt.approved_at,
            "scope": receipt.scope,
            "bound_content_hash": receipt.bound_content_hash,
            "semantic_lock_manifest_hash": receipt.semantic_lock_manifest_hash,
            "semantic_lock_count": receipt.semantic_lock_count,
        }
        return result

    raise PlanError(
        "PLAN_COMMAND_NOT_SUPPORTED",
        "This command is not exposed by the writable Plan-first UI boundary",
    )