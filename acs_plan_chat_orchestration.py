"""Trusted stale-safe orchestration for isolated ACS Plan-first chat edits.

Provider work is deliberately separated from canonical admission. The trusted
parent process captures the persisted head, sends only detached canonical geometry
plus explicit engineer notes/provider model through the isolated generation runner,
then reloads the durable workspace before admitting or persisting the candidate.

Authentication/session authority and the PlanStore stay in the parent. The worker
receives no bearer token, actor/project authority, approval receipt, CAD/BIM/3D or
export authority. A concurrent head change fails closed as ``STALE_REVISION``;
there is no silent rebase. Existing engineer-approved Frozen Baselines are never
moved by this command.
"""
from __future__ import annotations

from typing import Any

from acs_plan_chat_job import run_isolated_chat_candidate
from acs_plan_commands import admit_plan_chat_candidate, validate_plan_chat_command
from acs_plan_review import PlanError
from acs_plan_store_port import PlanStorePort, as_plan_store_port
from acs_plan_store_reload import load_workspace


SCHEMA = "acs.plan-persisted-command-result/1.0"
_FORBIDDEN_PROJECT_FIELDS = frozenset({
    "project_id", "project", "workspace_id", "tenant_id",
})


def _chat_command(value: Any, *, actor_id: str) -> tuple[dict, str]:
    if not isinstance(value, dict):
        raise PlanError("INVALID_PLAN_COMMAND", "Plan-first command must be an object")
    if _FORBIDDEN_PROJECT_FIELDS.intersection(value):
        raise PlanError(
            "CLIENT_PROJECT_AUTHORITY",
            "Project/workspace authority must come from the authenticated host session",
        )
    # Reuse the canonical command boundary before any provider runner starts so
    # actor/model/lock/approval authority fields fail closed without paid work.
    return validate_plan_chat_command(value, actor_id=actor_id)


def _assert_loaded_state(workspace, state: dict, *, expected_head: str | None = None) -> None:
    head = state.get("head_revision_id")
    baseline = state.get("baseline_revision_id")
    if workspace.head != head or workspace.baseline != baseline:
        raise PlanError(
            "STORED_PROJECT_TAMPERED",
            "Reloaded project pointers changed while reconstructing the canonical workspace",
        )
    if expected_head is not None and head != expected_head:
        raise PlanError(
            "STALE_REVISION",
            "Persisted project head changed while provider work was in progress",
        )


def execute_isolated_persisted_chat_edit(
    store: PlanStorePort,
    project_id: str,
    command: dict,
    *,
    actor_id: str,
    provider_model=None,
    verifier=None,
    runner=None,
    request_id: str | None = None,
    timeout_s: float | None = None,
) -> dict:
    """Run one provider-backed chat edit without giving the worker mutation authority.

    The initial reload proves the provider proposal starts from the exact persisted
    canonical head and validates its revision-bound lock manifest. After provider
    work returns, a second durable state read + full workspace reload occurs before
    candidate admission. ``admit_plan_chat_candidate`` then re-checks the expected
    head and inherited locks on that fresh aggregate. The final store append still
    uses optimistic ``expected_head`` protection, covering a second race between
    reload/admission and persistence.
    """
    backend = as_plan_store_port(store)
    command, expected_head = _chat_command(command, actor_id=actor_id)

    before_state = backend.project_state(project_id, actor_id=actor_id)
    if before_state.get("head_revision_id") != expected_head:
        raise PlanError(
            "STALE_REVISION",
            "Expected revision is not the current persisted project head",
        )

    before_workspace = load_workspace(
        backend,
        project_id,
        actor_id=actor_id,
        verifier=verifier,
    )
    _assert_loaded_state(before_workspace, before_state, expected_head=expected_head)
    before_revision = before_workspace.get(expected_head)

    candidate = run_isolated_chat_candidate(
        before_revision.model,
        command.get("notes"),
        model=provider_model,
        request_id=request_id,
        timeout_s=timeout_s,
        runner=runner,
    )

    # Critical race boundary: provider work may be slow. Never admit its result
    # against the pre-provider in-memory aggregate. Re-read durable pointers and
    # reconstruct all revisions/approvals/locks from the store first.
    current_state = backend.project_state(project_id, actor_id=actor_id)
    if current_state.get("head_revision_id") != expected_head:
        raise PlanError(
            "STALE_REVISION",
            "Persisted project head changed while provider work was in progress",
        )
    current_workspace = load_workspace(
        backend,
        project_id,
        actor_id=actor_id,
        verifier=verifier,
    )
    _assert_loaded_state(current_workspace, current_state, expected_head=expected_head)

    result = admit_plan_chat_candidate(
        current_workspace,
        command,
        actor_id=actor_id,
        candidate=candidate,
    )
    new_head = current_workspace.head
    if not isinstance(new_head, str) or new_head == expected_head:
        raise PlanError(
            "INVALID_REVISION_CHAIN",
            "Admitted chat candidate did not create a new immutable draft revision",
        )

    backend.save_revision(
        project_id,
        actor_id=actor_id,
        revision=current_workspace.get(new_head),
        expected_head=expected_head,
    )

    after = backend.project_state(project_id, actor_id=actor_id)
    if after.get("head_revision_id") != new_head:
        raise PlanError(
            "STALE_REVISION",
            "Persisted project changed before the admitted chat revision was confirmed",
        )

    out = dict(result)
    out["persistence"] = {
        "schema": SCHEMA,
        "head_revision_id": after["head_revision_id"],
        "baseline_revision_id": after["baseline_revision_id"],
        "revision_persisted": True,
        "approval_persisted": False,
    }
    return out
