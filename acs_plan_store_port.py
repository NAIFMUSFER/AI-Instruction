"""Backend-neutral persistence port for ACS Plan-first v2.

The canonical plan/revision/lock/approval rules remain owned by the existing ACS
model and workspace layers.  This module only separates those rules from a
concrete storage engine so a cloud adapter can be added without duplicating the
Plan-first command or reload logic.

``SQLitePlanStoreAdapter`` is a compatibility bridge for the audited local store.
New production backends should implement :class:`PlanStorePort` directly and
return the same integrity-checked workspace snapshot contract.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from acs_plan_review import PlanError
from acs_plan_store import (
    ROLES,
    SQLitePlanStore,
    _approval_from_row,
    _id,
    _revision_from_row,
)

WRITABLE_ROLES = {"owner", "editor"}
SNAPSHOT_SCHEMA = "acs.plan-store-workspace-snapshot/1.0"


@runtime_checkable
class PlanStorePort(Protocol):
    """Minimal durable store boundary consumed by Plan-first command/reload code."""

    def project_state(self, project_id: str, *, actor_id: str) -> dict: ...

    def workspace_snapshot(self, project_id: str, *, actor_id: str) -> dict: ...

    def save_revision(self, project_id: str, *, actor_id: str,
                      revision: Any, expected_head: str | None) -> dict: ...

    def save_approval(self, project_id: str, *, actor_id: str,
                      approval: Any, expected_head: str) -> dict: ...


class SQLitePlanStoreAdapter:
    """Expose the existing SQLite aggregate through the neutral store port.

    Raw SQLite access is isolated here.  Generic workspace reconstruction never
    sees rows/connections and receives only documents that passed the existing
    row/document integrity validators.
    """

    def __init__(self, store: SQLitePlanStore):
        if not isinstance(store, SQLitePlanStore):
            raise PlanError("INVALID_STORE", "SQLite adapter requires SQLitePlanStore")
        self._store = store

    def project_state(self, project_id: str, *, actor_id: str) -> dict:
        return self._store.project_state(project_id, actor_id=actor_id)

    def workspace_snapshot(self, project_id: str, *, actor_id: str) -> dict:
        project_id = _id(project_id, "project_id")
        actor_id = _id(actor_id, "actor_id")
        with self._store._connect() as con:
            project = self._store._project(con, project_id)
            # A restored workspace is mutable.  Do not hand it to a viewer and
            # rely on a later write to discover the authorization failure.
            self._store._role(con, project_id, actor_id, WRITABLE_ROLES)
            revision_rows = con.execute(
                "SELECT * FROM plan_revisions WHERE project_id=? ORDER BY number",
                (project_id,),
            ).fetchall()
            approval_rows = con.execute(
                "SELECT * FROM plan_approvals WHERE project_id=? ORDER BY approved_at,revision_id",
                (project_id,),
            ).fetchall()

        revisions = [
            _revision_from_row(row, project_id=project_id, revision_id=row["revision_id"])
            for row in revision_rows
        ]
        approvals = [
            _approval_from_row(row, project_id=project_id, revision_id=row["revision_id"])
            for row in approval_rows
        ]
        return {
            "schema": SNAPSHOT_SCHEMA,
            "project_id": project_id,
            "head_revision_id": project["head_revision_id"],
            "baseline_revision_id": project["baseline_revision_id"],
            "revisions": revisions,
            "approvals": approvals,
        }

    def save_revision(self, project_id: str, *, actor_id: str,
                      revision: Any, expected_head: str | None) -> dict:
        return self._store.save_revision(
            project_id, actor_id=actor_id, revision=revision, expected_head=expected_head,
        )

    def save_approval(self, project_id: str, *, actor_id: str,
                      approval: Any, expected_head: str) -> dict:
        return self._store.save_approval(
            project_id, actor_id=actor_id, approval=approval, expected_head=expected_head,
        )


def as_plan_store_port(store: object) -> PlanStorePort:
    """Return a backend-neutral port while preserving SQLite caller compatibility."""
    if isinstance(store, PlanStorePort):
        return store
    if isinstance(store, SQLitePlanStore):
        return SQLitePlanStoreAdapter(store)
    raise PlanError("INVALID_STORE", "Plan-first persistence requires PlanStorePort")
