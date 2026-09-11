"""Revision-bound semantic locks for the ACS plan-first foundation.

This module composes :class:`acs_plan_review.PlanWorkspace` with the stable
semantic lock contract from :mod:`acs_plan_semantic_locks`.  Lock changes are
versioned operations: a manifest is rebound to every admitted revision, approval
captures its hash, and approved handoff carries the same receipt.  A provider or
compiler cannot silently drop, replace, or reinterpret an engineer lock.

This is still process-local foundation code.  It is not authentication, durable
cloud persistence, regulatory approval, or a public production route.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Callable

from acs_plan_options import compare_options
from acs_plan_review import Approval, PlanError, PlanWorkspace, Revision, canonical, digest
from acs_plan_semantic_locks import build_lock_manifest, verify_lock_manifest

SCHEMA = "acs.plan-lock-binding/1.0"
REVISION_COMPARE_SCHEMA = "acs.plan-revision-comparison/1.0"


def _selectors(manifest: dict | None) -> list[dict]:
    if manifest is None:
        return []
    locks = manifest.get("locks") if isinstance(manifest, dict) else None
    if not isinstance(locks, list):
        raise PlanError("INVALID_LOCK_MANIFEST", "Bound semantic lock manifest is malformed")
    out = []
    for record in locks:
        selector = record.get("selector") if isinstance(record, dict) else None
        if not isinstance(selector, dict):
            raise PlanError("INVALID_LOCK_MANIFEST", "Bound semantic lock selector is malformed")
        out.append(json.loads(canonical(selector)))
    return out


def _manifest_hash(manifest: dict | None) -> str | None:
    if manifest is None:
        return None
    value = manifest.get("manifest_hash") if isinstance(manifest, dict) else None
    if not isinstance(value, str) or not value:
        raise PlanError("INVALID_LOCK_MANIFEST", "Bound semantic lock manifest has no hash")
    return value


def _bound_hash(revision: Revision, manifest: dict | None) -> str:
    return digest({
        "schema": SCHEMA,
        "revision_id": revision.id,
        "revision_content_hash": revision.content_hash,
        "model_hash": revision.model_hash,
        "semantic_lock_manifest_hash": _manifest_hash(manifest),
    })


@dataclass(frozen=True)
class BoundRevision:
    """Detached revision receipt with the semantic-lock binding made explicit."""

    revision: Revision
    semantic_lock_manifest_json: str | None
    semantic_lock_manifest_hash: str | None
    semantic_lock_count: int
    bound_content_hash: str

    @property
    def id(self) -> str:
        return self.revision.id

    @property
    def number(self) -> int:
        return self.revision.number

    @property
    def parent_id(self) -> str | None:
        return self.revision.parent_id

    @property
    def model(self) -> dict:
        return self.revision.model

    @property
    def model_hash(self) -> str:
        return self.revision.model_hash

    @property
    def content_hash(self) -> str:
        return self.revision.content_hash

    @property
    def requirements_json(self) -> str:
        return self.revision.requirements_json

    @property
    def brief(self) -> str:
        return self.revision.brief

    @property
    def note(self) -> str:
        return self.revision.note

    @property
    def locked_rooms(self):
        return self.revision.locked_rooms

    @property
    def created_at(self) -> str:
        return self.revision.created_at

    @property
    def semantic_lock_manifest(self) -> dict | None:
        return (json.loads(self.semantic_lock_manifest_json)
                if self.semantic_lock_manifest_json is not None else None)


@dataclass(frozen=True)
class BoundApproval:
    """Approval receipt that cannot be detached from the active lock manifest."""

    revision_id: str
    revision_content_hash: str
    bound_content_hash: str
    model_hash: str
    semantic_lock_manifest_hash: str | None
    semantic_lock_count: int
    actor_label: str
    approved_at: str
    scope: str


class PlanLockWorkspace:
    """PlanWorkspace-compatible facade with revision-bound semantic locks.

    The wrapped workspace remains the authority for immutable plan revisions,
    room locks, review, approval and exact approved-model handoff.  This facade
    adds stable nested locks (racks/docks/lanes/etc.) and versions every lock-set
    change as a new revision.  Inherited locks are verified *before* admission,
    then rebound to the admitted revision so their source hash follows history.
    """

    def __init__(self, verifier: Callable[[dict], dict] | None = None,
                 workspace: PlanWorkspace | None = None):
        if workspace is not None and verifier is not None:
            raise PlanError("INVALID_WORKSPACE", "Provide a workspace or verifier, not both")
        self._workspace = workspace or PlanWorkspace(verifier=verifier)
        self._manifests: dict[str, str | None] = {}
        self._approval_receipts: dict[str, BoundApproval] = {}
        self._mutex = threading.RLock()

    @property
    def head(self) -> str | None:
        return self._workspace.head

    @property
    def baseline(self) -> str | None:
        return self._workspace.baseline

    def _stored_manifest(self, revision_id: str) -> dict | None:
        raw = self._manifests.get(revision_id)
        if raw is None:
            return None
        manifest = json.loads(raw)
        revision = self._workspace.get(revision_id)
        # This proves both the manifest's internal hash and its source revision.
        verify_lock_manifest(revision.model, revision.model, manifest)
        return manifest

    def _store_manifest(self, revision: Revision, manifest: dict | None) -> None:
        if manifest is None:
            self._manifests[revision.id] = None
            return
        verify_lock_manifest(revision.model, revision.model, manifest)
        self._manifests[revision.id] = canonical(manifest)

    def _rebind(self, source_revision: Revision, candidate_model: dict,
                manifest: dict | None) -> dict | None:
        if manifest is None:
            return None
        verify_lock_manifest(source_revision.model, candidate_model, manifest)
        selectors = _selectors(manifest)
        return build_lock_manifest(candidate_model, selectors)

    def _bound(self, revision: Revision) -> BoundRevision:
        manifest = self._stored_manifest(revision.id)
        raw = canonical(manifest) if manifest is not None else None
        return BoundRevision(
            revision=revision,
            semantic_lock_manifest_json=raw,
            semantic_lock_manifest_hash=_manifest_hash(manifest),
            semantic_lock_count=len(_selectors(manifest)),
            bound_content_hash=_bound_hash(revision, manifest),
        )

    def get(self, revision_id: str) -> BoundRevision:
        with self._mutex:
            return self._bound(self._workspace.get(revision_id))

    def propose(self, model: dict, *, brief: str, requirements: list[dict],
                expected_head: str | None, note: str) -> BoundRevision:
        with self._mutex:
            inherited = None
            source = None
            if self.head is not None:
                if expected_head != self.head:
                    raise PlanError("STALE_REVISION", "The plan changed; rebase the proposal explicitly")
                source = self._workspace.get(self.head)
                inherited = self._stored_manifest(source.id)
                # Fail before the immutable history is extended.
                if inherited is not None:
                    verify_lock_manifest(source.model, model, inherited)
            revision = self._workspace.propose(
                model, brief=brief, requirements=requirements,
                expected_head=expected_head, note=note)
            rebound = (self._rebind(source, revision.model, inherited)
                       if source is not None else None)
            self._store_manifest(revision, rebound)
            return self._bound(revision)

    def compare_revisions(self, reference_revision_id: str,
                          target_revision_id: str) -> dict:
        """Compare two immutable revisions using only existing measured facts.

        This does not rank revisions or authenticate program equivalence.  If the
        exact stored brief and requirements are byte-equivalent after canonical
        storage, an opaque content receipt labels that fact; it is still reported
        as unauthenticated by the underlying comparison contract.
        """
        with self._mutex:
            reference = self.get(reference_revision_id)
            target = self.get(target_revision_id)
            same_program = (reference.brief == target.brief
                            and reference.requirements_json == target.requirements_json)
            program_receipt = (digest({
                "brief": reference.brief,
                "requirements": json.loads(reference.requirements_json),
            }) if same_program else None)
            measured = compare_options([
                {"id": "reference", "revision_id": reference.id,
                 "model": reference.model},
                {"id": "target", "revision_id": target.id,
                 "model": target.model},
            ], declared_program_receipt=program_receipt)
            return {
                "schema": REVISION_COMPARE_SCHEMA,
                "reference_revision_id": reference.id,
                "target_revision_id": target.id,
                "same_program_content": same_program,
                "reference_bound_content_hash": reference.bound_content_hash,
                "target_bound_content_hash": target.bound_content_hash,
                "reference_semantic_lock_manifest_hash": reference.semantic_lock_manifest_hash,
                "target_semantic_lock_manifest_hash": target.semantic_lock_manifest_hash,
                "reference_semantic_lock_count": reference.semantic_lock_count,
                "target_semantic_lock_count": target.semantic_lock_count,
                "reference_is_frozen_baseline": reference.id == self.baseline,
                "target_is_frozen_baseline": target.id == self.baseline,
                "measured": measured,
                "claims_best_option": False,
                "claims_regulatory_compliance": False,
                "claims_structural_safety": False,
            }

    def restore_revision(self, source_revision_id: str, *, expected_head: str,
                         note: str) -> BoundRevision:
        """Restore historical content as a new draft child of the current head.

        Restore never moves the head pointer backwards and never copies approval
        authority from the historical revision.  The *current* head's room and
        semantic locks remain authoritative because admission is delegated to
        :meth:`propose`, which verifies those locks before extending history.
        """
        with self._mutex:
            if expected_head != self.head:
                raise PlanError("STALE_REVISION", "The plan changed before restore")
            if not isinstance(note, str) or not note.strip():
                raise PlanError("DESCRIPTION_REQUIRED", "Revision restore needs an explicit note")
            source = self.get(source_revision_id)
            if source.id == self.head:
                raise PlanError("RESTORE_NOT_NEEDED", "The selected revision is already current")
            return self.propose(
                source.model,
                brief=source.brief,
                requirements=json.loads(source.requirements_json),
                expected_head=expected_head,
                note=note,
            )

    def replace_semantic_locks(self, selectors: list[dict], *, expected_head: str,
                               note: str) -> BoundRevision:
        """Version an explicit semantic lock-set change without mutating a revision."""
        with self._mutex:
            if expected_head != self.head:
                raise PlanError("STALE_REVISION", "The plan changed before the lock operation")
            if not isinstance(selectors, list):
                raise PlanError("INVALID_LOCK_SELECTOR", "Lock selectors must be an array")
            if not isinstance(note, str) or not note.strip():
                raise PlanError("DESCRIPTION_REQUIRED", "Semantic lock changes need an explicit note")
            before = self._workspace.get(expected_head)
            manifest = build_lock_manifest(before.model, selectors) if selectors else None
            revision = self._workspace.propose(
                before.model, brief=before.brief,
                requirements=json.loads(before.requirements_json),
                expected_head=expected_head, note=note)
            rebound = (build_lock_manifest(revision.model, _selectors(manifest))
                       if manifest is not None else None)
            self._store_manifest(revision, rebound)
            return self._bound(revision)

    def set_room_lock(self, room_ref: tuple[str, str], *, locked: bool,
                      expected_head: str) -> BoundRevision:
        """Preserve semantic locks while the underlying room-lock set is versioned."""
        with self._mutex:
            if expected_head != self.head:
                raise PlanError("STALE_REVISION", "The plan changed before the room lock operation")
            source = self._workspace.get(expected_head)
            inherited = self._stored_manifest(source.id)
            revision = self._workspace.set_room_lock(
                room_ref, locked=locked, expected_head=expected_head)
            rebound = self._rebind(source, revision.model, inherited)
            self._store_manifest(revision, rebound)
            return self._bound(revision)

    def review(self, revision_id: str) -> dict:
        with self._mutex:
            result = dict(self._workspace.review(revision_id))
            bound = self.get(revision_id)
            result["semantic_lock_manifest_hash"] = bound.semantic_lock_manifest_hash
            result["semantic_lock_count"] = bound.semantic_lock_count
            result["bound_content_hash"] = bound.bound_content_hash
            return result

    def approve(self, revision_id: str, *, expected_head: str, actor_label: str,
                confirmed: bool, acknowledge_concept_only: bool) -> BoundApproval:
        with self._mutex:
            base: Approval = self._workspace.approve(
                revision_id, expected_head=expected_head, actor_label=actor_label,
                confirmed=confirmed, acknowledge_concept_only=acknowledge_concept_only)
            bound = self.get(revision_id)
            receipt = BoundApproval(
                revision_id=revision_id,
                revision_content_hash=base.content_hash,
                bound_content_hash=bound.bound_content_hash,
                model_hash=base.model_hash,
                semantic_lock_manifest_hash=bound.semantic_lock_manifest_hash,
                semantic_lock_count=bound.semantic_lock_count,
                actor_label=base.actor_label,
                approved_at=base.approved_at,
                scope=base.scope,
            )
            self._approval_receipts[revision_id] = receipt
            return receipt

    def handoff(self, revision_id: str) -> dict:
        with self._mutex:
            receipt = self._approval_receipts.get(revision_id)
            if receipt is None:
                raise PlanError("APPROVAL_REQUIRED", "Lock-bound approval is required before 3D handoff")
            bound = self.get(revision_id)
            if (receipt.bound_content_hash != bound.bound_content_hash
                    or receipt.semantic_lock_manifest_hash != bound.semantic_lock_manifest_hash
                    or receipt.semantic_lock_count != bound.semantic_lock_count):
                raise PlanError("LOCK_RECEIPT_CHANGED", "Approved semantic lock receipt no longer matches")
            result = self._workspace.handoff(revision_id)
            baseline = dict(result["baseline"])
            baseline.update({
                "lock_binding_schema": SCHEMA,
                "bound_content_hash": bound.bound_content_hash,
                "semantic_lock_manifest_hash": bound.semantic_lock_manifest_hash,
                "semantic_lock_count": bound.semantic_lock_count,
            })
            result = dict(result)
            result["baseline"] = baseline
            result["semantic_lock_selectors"] = _selectors(bound.semantic_lock_manifest)
            return result

    def history(self) -> list[dict]:
        with self._mutex:
            rows = []
            for row in self._workspace.history():
                bound = self.get(row["revision_id"])
                enriched = dict(row)
                enriched.update({
                    "semantic_lock_manifest_hash": bound.semantic_lock_manifest_hash,
                    "semantic_lock_count": bound.semantic_lock_count,
                    "bound_content_hash": bound.bound_content_hash,
                })
                rows.append(enriched)
            return rows
