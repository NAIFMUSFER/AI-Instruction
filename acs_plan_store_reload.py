"""Fail-closed reconstruction of persisted ACS Plan-first workspaces.

This companion reconstructs only integrity-checked persistence snapshots and then
revalidates canonical model/provenance/lock binding before exposing a live
workspace.  It does not depend on SQLite rows or connections; local SQLite callers
are adapted behind :mod:`acs_plan_store_port`, while production backends can
implement the same narrow snapshot contract directly.

It performs no provider, compiler, network, authentication, or geometry-repair
work.  The Canonical ACS Model and immutable revision/approval receipts remain the
authority regardless of the backing datastore.
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
from acs_plan_store import _id, _validate_approval_shape, _validate_revision_document
from acs_plan_store_port import PlanStorePort, SNAPSHOT_SCHEMA, as_plan_store_port


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


def load_workspace(store: PlanStorePort, project_id: str, *, actor_id: str,
                   verifier: Callable[[dict], dict] | None = None) -> PlanLockWorkspace:
    """Reconstruct one *writable* persisted project without minting new identities.

    Exact persisted revision IDs, timestamps, parent links, model/program content,
    room/semantic locks, approval receipts and Frozen Baseline identity are kept.
    Any broken chain, stale project head, orphan/duplicate approval, altered lock
    receipt or snapshot mismatch fails before the workspace is returned.  Viewers
    deliberately use read-only store APIs instead of receiving a mutable aggregate.
    """
    backend = as_plan_store_port(store)
    project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
    snapshot = backend.workspace_snapshot(project_id, actor_id=actor_id)
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise PlanError("INVALID_STORE_SNAPSHOT", "Persistence backend returned an unknown workspace snapshot")
    if snapshot.get("project_id") != project_id:
        raise PlanError("STORED_PROJECT_TAMPERED", "Persistence snapshot project identity changed")

    revision_docs = snapshot.get("revisions")
    approval_rows = snapshot.get("approvals")
    if not isinstance(revision_docs, list) or not isinstance(approval_rows, list):
        raise PlanError("INVALID_STORE_SNAPSHOT", "Persistence snapshot history is malformed")
    if len(revision_docs) > MAX_REVISIONS:
        raise PlanError("HISTORY_LIMIT", "Persisted workspace exceeds the revision boundary")

    by_id: dict[str, dict] = {}
    previous_id: str | None = None
    for expected_number, doc in enumerate(revision_docs, start=1):
        if not isinstance(doc, dict):
            raise PlanError("INVALID_STORED_REVISION", "Stored revision receipt is malformed")
        _validate_revision_document(doc)
        rid = _id(doc.get("revision_id"), "revision_id")
        if rid in by_id:
            raise PlanError("INVALID_REVISION_CHAIN", "Persisted revision identity is duplicated")
        if doc["number"] != expected_number or doc["parent_id"] != previous_id:
            raise PlanError("INVALID_REVISION_CHAIN", "Persisted revision history is not a single monotonic chain")
        # Persisted hashes prove content identity; these checks additionally prove
        # the content still satisfies the canonical admission/provenance contract.
        _structure(doc["model"])
        _validate_provenance_links(doc["model"], doc["requirements"])
        canonical({"brief": doc["brief"], "note": doc["note"]})
        _validate_locked_rooms(doc)
        by_id[rid] = doc
        previous_id = rid

    persisted_head = snapshot.get("head_revision_id")
    if persisted_head is not None:
        persisted_head = _id(persisted_head, "head_revision_id")
    if persisted_head != previous_id:
        raise PlanError("STORED_PROJECT_TAMPERED", "Persisted project head does not match revision history")

    approval_docs: dict[str, dict] = {}
    for doc in approval_rows:
        if not isinstance(doc, dict):
            raise PlanError("INVALID_STORED_APPROVAL", "Stored approval receipt is malformed")
        _validate_approval_shape(doc)
        rid = _id(doc.get("revision_id"), "revision_id")
        if rid in approval_docs:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Persisted approval identity is duplicated")
        if rid not in by_id:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Persisted approval references no revision")
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

    baseline = snapshot.get("baseline_revision_id")
    if baseline is not None:
        baseline = _id(baseline, "baseline_revision_id")
        if baseline not in approval_docs:
            raise PlanError("STORED_PROJECT_TAMPERED", "Frozen Baseline has no matching persisted approval")

    workspace = PlanLockWorkspace(verifier=verifier)

    # This restores already validated immutable receipts, not an admission bypass
    # for new content.  New changes still go through propose().
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
