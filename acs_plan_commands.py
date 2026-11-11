"""Closed server-side command boundary for the ACS Plan-first workspace.

This module is intentionally NOT a public HTTP route and does not authenticate a
caller. A trusted host must resolve ``actor_id`` from its authenticated project
session before calling :func:`execute_plan_command`. Client payloads never get to
supply actor authority, detached lock manifests, or replacement canonical models.

The Canonical ACS Model remains the source of truth. Commands only compose the
existing revision/lock/review contracts; no 3D/BIM/compiler path is exposed here.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError, canonical
from acs_plan_semantic_diff import diff_models
from tools.acs_plan_review_packet import build_review_packet

SCHEMA = "acs.plan-command-result/1.0"
MAX_ACTOR_ID_CHARS = 256
MAX_OBJECT_ACTIONS = 256
_REMOVABLE_OBJECT_KINDS = frozenset({"column", "railing", "plant", "planter"})
_OPTIONAL_TYPOLOGY_COMPARISON_ACTIONS = frozenset({
    "remove_object", "set_room_lock", "replace_semantic_locks", "restore",
    "chat_edit", "edit_geometry", "set_roof",
})


def _stable_object_id(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 160


def _object_removal_capability(obj, *, physical_instances, identity_matches):
    """Shape/scope capability only. Authorization and locks remain separate."""
    kind = obj.get("kind")
    kind = kind.strip().lower() if isinstance(kind, str) and len(kind) <= 80 else None
    count = obj.get("count", 1)
    if not _stable_object_id(obj.get("id")):
        reason = "OBJECT_NOT_FOUND"
    elif identity_matches != 1:
        reason = "OBJECT_ID_AMBIGUOUS"
    elif physical_instances != 1:
        reason = "OBJECT_TEMPLATE_SHARED"
    elif kind not in _REMOVABLE_OBJECT_KINDS or "stair" in obj or "stair_provenance" in obj or obj.get("form") == "u_return":
        reason = "OBJECT_REMOVAL_UNSUPPORTED"
    elif type(count) is not int or count != 1:
        reason = "OBJECT_REPETITION_UNSUPPORTED"
    else:
        reason = None
    return kind, count, reason


def _object_actions(workspace, revision_id):
    from acs_context_details import list_context_details
    revision = workspace.get(revision_id)
    model = revision.model
    levels = model.get("levels") if isinstance(model.get("levels"), list) else []
    usages = Counter(level.get("template") for level in levels if isinstance(level, dict) and isinstance(level.get("template"), str))
    result = {"revision_id":revision_id, "model_hash":revision.model_hash,
              "requires_new_draft":any(row["revision_id"] == revision_id and row["state"] == "APPROVED" for row in workspace.history()),
              "items":[], "truncated":False}
    # Declared, bounded conceptual provenance only; never infer authority from
    # model-level counters or forward arbitrary imported metadata to the UI.
    details = list_context_details(model)
    detail_keys = Counter((row["template"], row["level_index"], row["room_id"], row["element_id"]) for row in details)
    provenance = {(row["template"], row["level_index"], row["room_id"], row["element_id"]):row["context_detail_provenance"]
                  for row in details if detail_keys[(row["template"], row["level_index"], row["room_id"], row["element_id"])] == 1}
    for level in levels:
        if not isinstance(level, dict):
            continue
        template = level.get("template")
        floor = model.get("floors", {}).get(template, {})
        for room in floor.get("rooms", []) if isinstance(floor, dict) else []:
            if not isinstance(room, dict) or not isinstance(room.get("objects"), list):
                continue
            ids = Counter(obj.get("id") for obj in room["objects"] if isinstance(obj, dict) and isinstance(obj.get("id"), str))
            for obj in room["objects"]:
                if not isinstance(obj, dict):
                    continue
                if len(result["items"]) >= MAX_OBJECT_ACTIONS:
                    result["truncated"] = True
                    return result
                oid = obj.get("id")
                kind, count, reason = _object_removal_capability(obj, physical_instances=usages[template], identity_matches=ids.get(oid, 0) if isinstance(oid, str) else 0)
                entry = {"template":template, "room_id":room.get("id"),
                    "object_id":oid if _stable_object_id(oid) else None, "level_index":level.get("index"),
                    "kind":kind, "count":count if type(count) is int and 0 <= count <= 200 else None,
                    "supported":reason is None, "reason":reason}
                key = (template, level.get("index"), room.get("id"), entry["object_id"])
                if key in provenance and ids.get(oid, 0) == 1:
                    entry["context_detail_provenance"] = provenance[key]
                result["items"].append(entry)
    return result


def _remove_object(workspace, command):
    allowed = {"action", "expected_head", "room_ref", "object_id", "confirm_new_draft"}
    if set(command) - allowed or type(command.get("confirm_new_draft")) is not bool:
        raise PlanError("INVALID_PLAN_COMMAND", "أرسل هوية العنصر وتأكيد إنشاء المسودة فقط.")
    expected = _head(command.get("expected_head"))
    if expected != workspace.head:
        raise PlanError("STALE_REVISION", "اختر آخر نسخة محفوظة قبل إزالة العنصر.")
    ref, oid = command.get("room_ref"), command.get("object_id")
    if not isinstance(ref, list) or len(ref) != 2 or not all(_stable_object_id(value) for value in ref) or not _stable_object_id(oid):
        raise PlanError("OBJECT_NOT_FOUND", "اختر عنصرًا له هوية ثابتة داخل فراغ معروف.")
    before = workspace.get(expected)
    candidate = before.model
    floor = candidate.get("floors", {}).get(ref[0], {})
    rooms = [room for room in floor.get("rooms", []) if isinstance(room, dict) and room.get("id") == ref[1]] if isinstance(floor, dict) else []
    objects = rooms[0].get("objects") if len(rooms) == 1 else None
    matches = [obj for obj in objects if isinstance(obj, dict) and obj.get("id") == oid] if isinstance(objects, list) else []
    if not matches:
        raise PlanError("OBJECT_NOT_FOUND", "العنصر غير موجود في النسخة المختارة؛ حدّث الاختيار.")
    instances = sum(1 for level in candidate.get("levels", []) if isinstance(level, dict) and level.get("template") == ref[0])
    _, _, reason = _object_removal_capability(matches[0], physical_instances=instances, identity_matches=len(matches))
    messages = {
        "OBJECT_ID_AMBIGUOUS":"هوية العنصر مكررة؛ لا يمكن تحديد عنصر واحد للحذف بأمان.",
        "OBJECT_TEMPLATE_SHARED":"هذا العنصر ضمن قالب يتكرر في أكثر من مستوى؛ إزالة نسخة واحدة غير مدعومة حاليًا.",
        "OBJECT_REMOVAL_UNSUPPORTED":"الإزالة المباشرة تدعم الأعمدة والدرابزين والنباتات والأصص فقط؛ الدرج والعناصر الأخرى غير مدعومة بهذه الأداة.",
        "OBJECT_REPETITION_UNSUPPORTED":"هذا السجل يمثل نسخًا متكررة؛ إزالة نسخة واحدة غير مدعومة حاليًا.",
    }
    if reason:
        raise PlanError(reason, messages.get(reason, "تعذّر تحديد عنصر واحد صالح للإزالة."))
    approved = any(row["revision_id"] == expected and row["state"] == "APPROVED" for row in workspace.history())
    if approved and command["confirm_new_draft"] is not True:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد إنشاء مسودة جديدة قبل إزالة عنصر من النسخة المعتمدة؛ يبقى الاعتماد السابق محفوظًا.")
    # The detached model keeps every surviving object, source field and program
    # byte-for-byte. Existing immutable history retains the removed attribution.
    rooms[0]["objects"] = [obj for obj in objects if obj is not matches[0]]
    revision = workspace.propose(candidate, brief=before.brief,
        requirements=json.loads(before.requirements_json), expected_head=expected,
        note="إزالة العنصر " + oid + " من " + ref[0] + "/" + ref[1])
    return _view_result(workspace, "remove_object", revision.id, reference_revision_id=expected)

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
        "object_actions": _object_actions(workspace, revision_id),
    }
    if reference_revision_id is not None:
        result["semantic_diff"] = _semantic_diff(
            workspace, reference_revision_id, revision_id,
        )
        # Reuse the existing deterministic scorecard/options comparison so a
        # mutation response exposes measured impact without another provider call
        # or any new ranking/compliance authority.
        try:
            result["revision_comparison"] = workspace.compare_revisions(
                reference_revision_id, revision_id,
            )
        except PlanError as error:
            # An admitted/approved model may have no declared typology. These
            # mutations do not need one; semantic_diff above still gives the full
            # canonical change. Keep the optional scorecard limitation
            # explicit, while preserving every other comparison failure and the
            # strict standalone comparison contract.
            if action not in _OPTIONAL_TYPOLOGY_COMPARISON_ACTIONS or error.code != "OPTION_TYPOLOGY_UNKNOWN":
                raise
            result["revision_comparison_unavailable"] = {
                "reason": error.code,
                "reference_revision_id": reference_revision_id,
                "target_revision_id": revision_id,
                "message": "نوع المبنى غير محدد؛ فرق العناصر متاح، ومقارنة مؤشرات التصميم غير متاحة لهذه النسخة.",
            }
    return result


def validate_plan_chat_command(command: dict, *, actor_id: str) -> tuple[dict, str]:
    """Preflight a chat command before any provider runner is allowed to start."""
    _authenticated_actor(actor_id)
    command = _command(command)
    if command["action"].strip() != "chat_edit":
        raise PlanError(
            "PLAN_COMMAND_NOT_SUPPORTED",
            "Plan chat candidate flow accepts chat_edit only",
        )
    return command, _head(command.get("expected_head"))


def admit_plan_chat_candidate(workspace: PlanLockWorkspace, command: dict, *,
                              actor_id: str, candidate: dict) -> dict:
    """Admit one precomputed provider candidate through canonical Plan authority.

    This seam performs no provider work. It validates the same host-resolved actor
    and client-command authority contract as ``execute_plan_command``, then asks the
    provider-free bridge to re-check the current expected head plus inherited
    room/semantic locks. A successful candidate is a new draft only; an existing
    engineer-approved Frozen Baseline is never moved here.
    """
    workspace = _workspace(workspace)
    command, expected = validate_plan_chat_command(command, actor_id=actor_id)
    from acs_plan_bridge import admit_bound_chat_edit_candidate
    revision = admit_bound_chat_edit_candidate(
        workspace,
        command.get("notes"),
        expected_head=expected,
        candidate=candidate,
    )
    return _view_result(
        workspace,
        "chat_edit",
        revision.id,
        reference_revision_id=expected,
    )


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

    if action == "remove_object":
        return _remove_object(workspace, command)

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
