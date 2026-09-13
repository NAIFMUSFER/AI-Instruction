"""Isolated provider proposal boundary for ACS Plan-first chat edits.

This module has no HTTP route and no persistence authority. The trusted parent
process may pass canonical model geometry, explicit engineer notes, and an
optional provider model identifier through the existing cancellable generation
runner. The worker may propose geometry only. Authentication, Supabase access,
locks, revision admission, approval, Frozen Baseline authority, CAD/BIM/3D and
exports remain in the parent/canonical process.
"""
from __future__ import annotations

import json
from typing import Any

from acs_plan_review import PlanError, canonical


TARGET = "acs_plan_chat_job:generate_chat_candidate"


def _validated_inputs(building: Any, notes: Any, model: Any = None) -> tuple[dict, list[dict], str | None]:
    """Return detached bounded JSON inputs before any provider module is imported."""
    if not isinstance(building, dict):
        raise PlanError("INVALID_EDIT", "Plan chat worker requires one canonical building object")
    if (
        not isinstance(notes, list)
        or not notes
        or any(
            not isinstance(note, dict)
            or not isinstance(note.get("text"), str)
            or not note["text"].strip()
            for note in notes
        )
    ):
        raise PlanError("INVALID_EDIT", "Explicit engineer notes are required")
    if model is not None:
        if not isinstance(model, str) or not model.strip():
            raise PlanError("INVALID_EDIT", "Provider model identifier must be a non-empty string")
        model = model.strip()

    # canonical() rejects unsupported / non-finite structures and the JSON
    # round-trip detaches worker-owned values from parent-owned mutable objects.
    detached_building = json.loads(canonical(building))
    detached_notes = json.loads(canonical(notes))
    return detached_building, detached_notes, model


def generate_chat_candidate(building: dict, notes: list[dict], model: str | None = None) -> dict:
    """Worker target: call the provider edit function and return candidate geometry.

    This function is intentionally import-safe: ``acs_understand`` is imported
    only after input validation and only inside the worker target. No request
    scope, bearer token, actor id, project id, PlanStore or approval receipt is
    accepted by this function.
    """
    detached_building, detached_notes, provider_model = _validated_inputs(
        building, notes, model)

    import acs_understand as U

    candidate = U.apply_notes(
        detached_building,
        detached_notes,
        model=provider_model,
    )
    if not isinstance(candidate, dict):
        raise PlanError("INVALID_EDIT", "Provider returned no canonical building candidate")
    return json.loads(canonical(candidate))


def run_isolated_chat_candidate(
    building: dict,
    notes: list[dict],
    *,
    model: str | None = None,
    request_id: str | None = None,
    timeout_s: float | None = None,
    runner=None,
) -> dict:
    """Submit provider proposal work through the existing process job boundary.

    The serialized worker kwargs are deliberately closed: building + notes +
    provider model only. ``request_id`` and timeout remain JobRunner control
    metadata in the parent and are not part of the worker kwargs. A caller must
    still pass the returned candidate through ``admit_bound_chat_edit_candidate``
    against a freshly reloaded canonical workspace before any revision is saved.
    """
    detached_building, detached_notes, provider_model = _validated_inputs(
        building, notes, model)

    if runner is None:
        # Lazy import keeps this module provider/job-runner free when imported by
        # deployment-closure checks and other canonical Plan-first companions.
        import acs_generation_job as JOBS
        runner = JOBS.default_runner()

    candidate = runner.run(
        TARGET,
        {
            "building": detached_building,
            "notes": detached_notes,
            "model": provider_model,
        },
        timeout_s=timeout_s,
        request_id=request_id,
    )
    if not isinstance(candidate, dict):
        raise PlanError("INVALID_EDIT", "Isolated provider worker returned no building candidate")
    return json.loads(canonical(candidate))
