"""Fail-closed reconstruction of persisted ACS Plan-first workspaces.

This companion closes a deliberate boundary between :mod:`acs_plan_store`, which
persists immutable receipts, and :class:`acs_plan_lock_binding.PlanLockWorkspace`,
which owns live revision/lock/approval behavior.  It reconstructs only receipts
that have already passed the store's row/document integrity checks and then
revalidates the canonical model/provenance/lock binding before exposing a live
workspace.

It performs no provider, compiler, network, authentication, or geometry-repair
work.  SQLite remains filesystem durability; callers still need a durable host
volume or a production datastore port for real cross-device/cloud persistence.
"""
from __future__ import annotations

from typing import Callable

from acs_plan_lock_binding import BoundApproval, PlanLockWorkspace
from acs_plan_review import (
    Approval,
    MAX_REVISIONS,
    PlanError,
    Revision,
    _room_index,
    _structure,
    _validate_provenance_links,
    canonical,
)
from acs_plan_store import (
    ROLES,
    SQLitePlanStore,
    _approval_from_row,
    _id,
    _revision_from_row,
)


def _validate_locked_rooms(doc: dict) -> tuple[tuple[str, str], ...]:
    raw = doc.get("locked_rooms")
    if not isinstance(raw, list):
        raise PlanError("INVALID_STORED_REVISION", "Stored room locks are malformed")
    refs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    rooms = _room_index(doc["model"])
    for item in raw:
        if (not isinstance(item, list) or len(item) != 2
                or any(not isinstance(value, str) or not value for value in item)):
            raise PlanError("INVALID_STORED_REVISION", "Stored room lock identity is malformed")
        ref = (item[0], item[1])
        if ref in seen or ref not in rooms:
            raise PlanError("INVALID_STORED_REVISION", "Stored room lock target is missing or duplicated")
        seen.add(ref)
        refs.append(ref)
    return tuple(sorted(refs))


def load_workspace(store: SQLitePlanStore, project_id: str, *, actor_id: str,
                   verifier: Callable[[dict], dict] | None = None) -> PlanLockWorkspace:
    """Reconstruct one persisted project without minting replacement identities.

    Exact persisted revision IDs, timestamps, parent links, model/program content,
    room/semantic locks, approval receipts and Frozen Baseline identity are kept.
    Any broken chain, stale project head, orphan approval, altered lock receipt or
    receipt mismatch fails before the workspace is returned.
    """
    if not isinstance(store, SQLitePlanStore):
        raise PlanError("INVALID_STORE", "Workspace reload requires SQLitePlanStore")
    project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")

    with store._connect() as con:
        project = store._project(con, project_id)
        store._role(con, project_id, actor_id, ROLES)
        revision_rows = con.execute(
            "SELECT * FROM plan_revisions WHERE project_id=? ORDER BY number",
            (project_id,),
        ).fetchall()
        approval_rows = con.execute(
            "SELECT * FROM plan_approvals WHERE project_id=? ORDER BY approved_at,revision_id",
            (project_id,),
        ).fetchall()

    if len(revision_rows) > MAX_REVISIONS:
        raise PlanError("HISTORY_LIMIT", "Persisted workspace exceeds the revision boundary")

    revision_docs: list[dict] = []
    by_id: dict[str, dict] = {}
    previous_id: str | None = None
    for expected_number, row in enumerate(revision_rows, start=1):
        rid = row["revision_id"]
        doc = _revision_from_row(row, project_id=project_id, revision_id=rid)
        if doc["number"] != expected_number or doc["parent_id"] != previous_id:
            raise PlanError("INVALID_REVISION_CHAIN", "Persisted revision history is not a single monotonic chain")
        # Persisted hashes prove byte/content identity; these checks additionally
        # prove the content still satisfies the canonical admission contract.
        _structure(doc["model"])
        _validate_provenance_links(doc["model"], doc["requirements"])
        canonical({"brief": doc["brief"], "note": doc["note"]})
        _validate_locked_rooms(doc)
        revision_docs.append(doc)
        by_id[rid] = doc
        previous_id = rid

    persisted_head = project["head_revision_id"]
    if persisted_head != previous_id:
        raise PlanError("STORED_PROJECT_TAMPERED", "Persisted project head does not match revision history")

    approval_docs: dict[str, dict] = {}
    for row in approval_rows:
        rid = row["revision_id"]
        if rid not in by_id:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Persisted approval references no revision")
        doc = _approval_from_row(row, project_id=project_id, revision_id=rid)
        rev = by_id[rid]
        expected = (
            rev["content_hash"], rev["bound_content_hash"], rev["model_hash"],
            rev["semantic_lock_manifest_hash"], rev["semantic_lock_count"],
        )
        actual = (
            doc["revision_content_hash"], doc["bound_content_hash"], doc["model_hash"],
            doc["semantic_lock_manifest_hash"], doc["semantic_lock_count"],
        )
        if actual != expected:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Persisted approval does not match its revision")
        approval_docs[rid] = doc

    baseline = project["baseline_revision_id"]
    if baseline is not None:
        baseline = _id(baseline, "baseline_revision_id")
        if baseline not in approval_docs:
            raise PlanError("STORED_PROJECT_TAMPERED", "Frozen Baseline has no matching persisted approval")

    workspace = PlanLockWorkspace(verifier=verifier)

    # This is restoration of already validated immutable receipts, not an
    # admission bypass for new content.  New changes still go through propose().
    for doc in revision_docs:
        locks = _validate_locked_rooms(doc)
        revision = Revision(
            id=doc["revision_id"],
            number=doc["number"],
            parent_id=doc["parent_id"],
            model_json=canonical(doc["model"]),
            requirements_json=canonical(doc["requirements"]),
            brief=doc["brief"],
            note=doc["note"],
            locked_rooms=locks,
            created_at=doc["created_at"],
        )
        if revision.model_hash != doc["model_hash"] or revision.content_hash != doc["content_hash"]:
            raise PlanError("STORED_REVISION_TAMPERED", "Reconstructed revision hash changed")
        workspace._workspace._revisions[revision.id] = revision
        workspace._workspace._head = revision.id
        manifest = doc["semantic_lock_manifest"]
        workspace._manifests[revision.id] = canonical(manifest) if manifest is not None else None
        bound = workspace.get(revision.id)
        if (bound.bound_content_hash != doc["bound_content_hash"]
                or bound.semantic_lock_manifest_hash != doc["semantic_lock_manifest_hash"]
                or bound.semantic_lock_count != doc["semantic_lock_count"]):
            raise PlanError("STORED_LOCK_RECEIPT_TAMPERED", "Reconstructed lock binding changed")

    for rid, doc in approval_docs.items():
        base = Approval(
            revision_id=rid,
            content_hash=doc["revision_content_hash"],
            model_hash=doc["model_hash"],
            actor_label=doc["actor_label"],
            approved_at=doc["approved_at"],
            scope=doc["scope"],
        )
        bound = BoundApproval(
            revision_id=rid,
            revision_content_hash=doc["revision_content_hash"],
            bound_content_hash=doc["bound_content_hash"],
            model_hash=doc["model_hash"],
            semantic_lock_manifest_hash=doc["semantic_lock_manifest_hash"],
            semantic_lock_count=doc["semantic_lock_count"],
            actor_label=doc["actor_label"],
            approved_at=doc["approved_at"],
            scope=doc["scope"],
        )
        workspace._workspace._approvals[rid] = base
        workspace._approval_receipts[rid] = bound

    workspace._workspace._baseline = baseline
    if workspace.head != persisted_head or workspace.baseline != baseline:
        raise PlanError("STORED_PROJECT_TAMPERED", "Reconstructed project pointers changed")
    if baseline is not None:
        # Re-run the exact lock-bound handoff receipt check before returning.
        workspace.handoff(baseline)
    return workspace
