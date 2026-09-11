"""Durable owner-scoped storage contract for ACS Plan-first v2.

SQLite is used as a deterministic local persistence boundary.  This module does
NOT authenticate users: the host must supply an already-authenticated ``actor_id``.
It enforces project membership/RBAC, optimistic head updates, immutable revision
and approval receipts, semantic-lock receipt integrity, and exact approved-plan
reload after process restart.

A SQLite file on an ephemeral filesystem is still ephemeral.  Cross-device/cloud
durability requires the host to place this database on durable storage or port
this contract to the production datastore.  No regulatory/structural approval is
implied by any persisted conceptual-design receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from acs_plan_review import PlanError, canonical, digest
from acs_plan_semantic_locks import verify_lock_manifest

SCHEMA = "acs.plan-store/1.0"
REVISION_SCHEMA = "acs.plan-store-revision/1.0"
APPROVAL_SCHEMA = "acs.plan-store-approval/1.0"
HANDOFF_SCHEMA = "acs.plan-store-handoff/1.0"
LOCK_BINDING_SCHEMA = "acs.plan-lock-binding/1.0"
ROLES = {"owner", "editor", "viewer"}
MAX_STORE_BYTES = 2_500_000


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise PlanError("INVALID_IDENTITY", "%s must be a non-empty bounded string" % label)
    return value.strip()


def _json(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise PlanError("INVALID_STORED_VALUE", "Persistence payload is not valid JSON") from exc
    if len(raw.encode("utf-8")) > MAX_STORE_BYTES:
        raise PlanError("STORE_INPUT_LIMIT", "Persistence payload exceeds the bounded store contract")
    return raw


def _model_hash(model: dict) -> str:
    return hashlib.sha256(canonical(model).encode("utf-8")).hexdigest()


def _source_map(model: dict) -> list[dict]:
    out = []
    floors = model.get("floors") or {}
    levels = model.get("levels") or []
    for lv in levels:
        if not isinstance(lv, dict) or type(lv.get("index")) is not int:
            raise PlanError("INVALID_STORED_REVISION", "Stored level identity is malformed")
        template = lv.get("template")
        floor = floors.get(template) if isinstance(template, str) else None
        rooms = floor.get("rooms") if isinstance(floor, dict) else None
        if not isinstance(rooms, list):
            raise PlanError("INVALID_STORED_REVISION", "Stored template/level relation is malformed")
        for room in rooms:
            rid = room.get("id") if isinstance(room, dict) else None
            if not isinstance(rid, str) or not rid:
                raise PlanError("INVALID_STORED_REVISION", "Stored room identity is malformed")
            out.append({"level_index": lv["index"], "template": template, "room_id": rid})
    return out


def revision_document(revision: Any) -> dict:
    """Detach a BoundRevision-like object into an integrity-checked JSON document."""
    try:
        model = revision.model
        requirements = json.loads(revision.requirements_json)
        locked_rooms = [list(x) for x in revision.locked_rooms]
        manifest = revision.semantic_lock_manifest
        doc = {
            "schema": REVISION_SCHEMA,
            "revision_id": revision.id,
            "number": revision.number,
            "parent_id": revision.parent_id,
            "model": model,
            "requirements": requirements,
            "brief": revision.brief,
            "note": revision.note,
            "locked_rooms": locked_rooms,
            "created_at": revision.created_at,
            "model_hash": revision.model_hash,
            "content_hash": revision.content_hash,
            "semantic_lock_manifest": manifest,
            "semantic_lock_manifest_hash": revision.semantic_lock_manifest_hash,
            "semantic_lock_count": revision.semantic_lock_count,
            "bound_content_hash": revision.bound_content_hash,
        }
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PlanError("INVALID_REVISION_RECEIPT", "Expected a bound plan revision receipt") from exc
    _validate_revision_document(doc)
    return json.loads(_json(doc))


def approval_document(approval: Any) -> dict:
    """Detach a BoundApproval-like object. actor_label is display metadata only."""
    try:
        doc = {
            "schema": APPROVAL_SCHEMA,
            "revision_id": approval.revision_id,
            "revision_content_hash": approval.revision_content_hash,
            "bound_content_hash": approval.bound_content_hash,
            "model_hash": approval.model_hash,
            "semantic_lock_manifest_hash": approval.semantic_lock_manifest_hash,
            "semantic_lock_count": approval.semantic_lock_count,
            "actor_label": approval.actor_label,
            "approved_at": approval.approved_at,
            "scope": approval.scope,
        }
    except AttributeError as exc:
        raise PlanError("INVALID_APPROVAL_RECEIPT", "Expected a bound plan approval receipt") from exc
    _validate_approval_shape(doc)
    return json.loads(_json(doc))


def _validate_revision_document(doc: dict) -> None:
    if not isinstance(doc, dict) or doc.get("schema") != REVISION_SCHEMA:
        raise PlanError("INVALID_STORED_REVISION", "Unknown stored revision schema")
    rid = _id(doc.get("revision_id"), "revision_id")
    number = doc.get("number")
    if type(number) is not int or number < 1:
        raise PlanError("INVALID_STORED_REVISION", "Revision number is invalid")
    parent = doc.get("parent_id")
    if parent is not None:
        _id(parent, "parent_id")
    model = doc.get("model")
    requirements = doc.get("requirements")
    locks = doc.get("locked_rooms")
    if not isinstance(model, dict) or not isinstance(requirements, list) or not isinstance(locks, list):
        raise PlanError("INVALID_STORED_REVISION", "Stored canonical plan/program/room locks are malformed")
    canonical(model)
    canonical(requirements)
    canonical({"brief": doc.get("brief"), "note": doc.get("note"), "locks": locks})
    mh = _model_hash(model)
    if doc.get("model_hash") != mh:
        raise PlanError("STORED_MODEL_TAMPERED", "Stored model hash does not match canonical plan")
    expected_content = digest({"model": model, "requirements": requirements,
                               "brief": doc.get("brief"), "locks": locks})
    if doc.get("content_hash") != expected_content:
        raise PlanError("STORED_REVISION_TAMPERED", "Stored revision content hash does not match")

    manifest = doc.get("semantic_lock_manifest")
    lock_hash = doc.get("semantic_lock_manifest_hash")
    count = doc.get("semantic_lock_count")
    if manifest is None:
        if lock_hash is not None or count != 0:
            raise PlanError("STORED_LOCK_RECEIPT_TAMPERED", "Empty semantic locks have inconsistent receipt data")
    else:
        if not isinstance(manifest, dict):
            raise PlanError("STORED_LOCK_RECEIPT_TAMPERED", "Semantic lock manifest is malformed")
        verify_lock_manifest(model, model, manifest)
        rows = manifest.get("locks")
        if not isinstance(rows, list) or count != len(rows) or lock_hash != manifest.get("manifest_hash"):
            raise PlanError("STORED_LOCK_RECEIPT_TAMPERED", "Semantic lock hash/count does not match manifest")
    expected_bound = digest({"schema": LOCK_BINDING_SCHEMA,
                             "revision_id": rid,
                             "revision_content_hash": expected_content,
                             "model_hash": mh,
                             "semantic_lock_manifest_hash": lock_hash})
    if doc.get("bound_content_hash") != expected_bound:
        raise PlanError("STORED_LOCK_RECEIPT_TAMPERED", "Bound revision receipt does not match")
    _json(doc)


def _validate_approval_shape(doc: dict) -> None:
    if not isinstance(doc, dict) or doc.get("schema") != APPROVAL_SCHEMA:
        raise PlanError("INVALID_STORED_APPROVAL", "Unknown stored approval schema")
    _id(doc.get("revision_id"), "revision_id")
    if not isinstance(doc.get("actor_label"), str) or not doc["actor_label"].strip():
        raise PlanError("INVALID_STORED_APPROVAL", "Approval actor label is missing")
    if not isinstance(doc.get("approved_at"), str) or not doc["approved_at"].strip():
        raise PlanError("INVALID_STORED_APPROVAL", "Approval timestamp is missing")
    if doc.get("scope") != "CONCEPTUAL_DESIGN_ONLY":
        raise PlanError("INVALID_STORED_APPROVAL", "Only conceptual-design approval is supported")
    if type(doc.get("semantic_lock_count")) is not int or doc["semantic_lock_count"] < 0:
        raise PlanError("INVALID_STORED_APPROVAL", "Approval semantic-lock count is invalid")
    for key in ("revision_content_hash", "bound_content_hash", "model_hash"):
        if not isinstance(doc.get(key), str) or len(doc[key]) != 64:
            raise PlanError("INVALID_STORED_APPROVAL", "Approval hash receipt is malformed")
    lh = doc.get("semantic_lock_manifest_hash")
    if lh is not None and (not isinstance(lh, str) or len(lh) != 64):
        raise PlanError("INVALID_STORED_APPROVAL", "Approval semantic-lock hash is malformed")
    _json(doc)


class SQLitePlanStore:
    """Durable SQLite aggregate with host-supplied authenticated actor identity."""

    def __init__(self, path: str | os.PathLike[str]):
        if path is None or not str(path).strip() or str(path) == ":memory:":
            raise PlanError("DURABLE_STORE_REQUIRED", "Plan store requires a filesystem database path")
        self.path = str(Path(path))
        parent = Path(self.path).parent
        if not parent.exists() or not parent.is_dir():
            raise PlanError("STORE_DIR_MISSING", "Plan store directory must already exist")
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=15.0, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=15000")
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS projects(
              project_id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              head_revision_id TEXT,
              baseline_revision_id TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS project_members(
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
              actor_id TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')),
              PRIMARY KEY(project_id, actor_id)
            );
            CREATE TABLE IF NOT EXISTS plan_revisions(
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
              revision_id TEXT NOT NULL,
              number INTEGER NOT NULL,
              parent_id TEXT,
              revision_json TEXT NOT NULL,
              model_hash TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              bound_content_hash TEXT NOT NULL,
              semantic_lock_manifest_hash TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(project_id, revision_id),
              UNIQUE(project_id, number)
            );
            CREATE TABLE IF NOT EXISTS plan_approvals(
              project_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              approval_json TEXT NOT NULL,
              approved_by TEXT NOT NULL,
              approved_at TEXT NOT NULL,
              PRIMARY KEY(project_id, revision_id),
              FOREIGN KEY(project_id, revision_id)
                REFERENCES plan_revisions(project_id, revision_id) ON DELETE RESTRICT
            );
            """)

    @staticmethod
    def _project(con: sqlite3.Connection, project_id: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if row is None:
            raise PlanError("PROJECT_NOT_FOUND", "Project does not exist or is not accessible")
        return row

    @staticmethod
    def _role(con: sqlite3.Connection, project_id: str, actor_id: str,
              allowed: set[str]) -> str:
        row = con.execute("SELECT role FROM project_members WHERE project_id=? AND actor_id=?",
                          (project_id, actor_id)).fetchone()
        if row is None or row["role"] not in allowed:
            raise PlanError("PROJECT_ACCESS_DENIED", "Authenticated actor lacks the required project role")
        return row["role"]

    def create_project(self, project_id: str, *, owner_id: str) -> dict:
        project_id, owner_id = _id(project_id, "project_id"), _id(owner_id, "owner_id")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute("INSERT INTO projects(project_id,owner_id) VALUES(?,?)",
                            (project_id, owner_id))
                con.execute("INSERT INTO project_members(project_id,actor_id,role) VALUES(?,?, 'owner')",
                            (project_id, owner_id))
                con.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                con.execute("ROLLBACK")
                raise PlanError("PROJECT_EXISTS", "Project identity already exists") from exc
        return {"schema": SCHEMA, "project_id": project_id, "owner_id": owner_id,
                "head_revision_id": None, "baseline_revision_id": None}

    def grant_role(self, project_id: str, *, by_actor_id: str,
                   actor_id: str, role: str) -> dict:
        project_id = _id(project_id, "project_id")
        by_actor_id, actor_id = _id(by_actor_id, "actor_id"), _id(actor_id, "actor_id")
        if role not in ROLES or role == "owner":
            raise PlanError("INVALID_PROJECT_ROLE", "Only editor/viewer delegation is supported")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                project = self._project(con, project_id)
                self._role(con, project_id, by_actor_id, {"owner"})
                if actor_id == project["owner_id"]:
                    raise PlanError("INVALID_PROJECT_ROLE", "Project owner role cannot be replaced")
                con.execute("INSERT INTO project_members(project_id,actor_id,role) VALUES(?,?,?) "
                            "ON CONFLICT(project_id,actor_id) DO UPDATE SET role=excluded.role",
                            (project_id, actor_id, role))
                con.execute("COMMIT")
            except Exception:
                if con.in_transaction:
                    con.execute("ROLLBACK")
                raise
        return {"project_id": project_id, "actor_id": actor_id, "role": role}

    def save_revision(self, project_id: str, *, actor_id: str,
                      revision: Any, expected_head: str | None) -> dict:
        project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
        if expected_head is not None:
            expected_head = _id(expected_head, "expected_head")
        doc = revision_document(revision)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                project = self._project(con, project_id)
                self._role(con, project_id, actor_id, {"owner", "editor"})
                if project["head_revision_id"] != expected_head:
                    raise PlanError("STALE_REVISION", "Persisted project head changed; rebase explicitly")
                if doc["parent_id"] != expected_head:
                    raise PlanError("INVALID_REVISION_CHAIN", "Revision parent does not match persisted head")
                previous_number = 0
                if expected_head is not None:
                    parent = con.execute("SELECT number FROM plan_revisions WHERE project_id=? AND revision_id=?",
                                         (project_id, expected_head)).fetchone()
                    if parent is None:
                        raise PlanError("INVALID_REVISION_CHAIN", "Persisted parent revision is missing")
                    previous_number = parent["number"]
                if doc["number"] != previous_number + 1:
                    raise PlanError("INVALID_REVISION_CHAIN", "Revision number is not monotonic")
                try:
                    con.execute("""INSERT INTO plan_revisions(
                        project_id,revision_id,number,parent_id,revision_json,model_hash,
                        content_hash,bound_content_hash,semantic_lock_manifest_hash,
                        created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (project_id, doc["revision_id"], doc["number"], doc["parent_id"],
                         _json(doc), doc["model_hash"], doc["content_hash"],
                         doc["bound_content_hash"], doc["semantic_lock_manifest_hash"],
                         actor_id, doc["created_at"]))
                except sqlite3.IntegrityError as exc:
                    raise PlanError("REVISION_EXISTS", "Revision/version already exists in this project") from exc
                con.execute("UPDATE projects SET head_revision_id=?,updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                            (doc["revision_id"], project_id))
                con.execute("COMMIT")
            except Exception:
                if con.in_transaction:
                    con.execute("ROLLBACK")
                raise
        return json.loads(_json(doc))

    def save_approval(self, project_id: str, *, actor_id: str,
                      approval: Any, expected_head: str) -> dict:
        project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
        expected_head = _id(expected_head, "expected_head")
        doc = approval_document(approval)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                project = self._project(con, project_id)
                self._role(con, project_id, actor_id, {"owner", "editor"})
                if project["head_revision_id"] != expected_head or doc["revision_id"] != expected_head:
                    raise PlanError("STALE_REVISION", "Approval must bind the persisted current head")
                row = con.execute("SELECT revision_json FROM plan_revisions WHERE project_id=? AND revision_id=?",
                                  (project_id, expected_head)).fetchone()
                if row is None:
                    raise PlanError("REVISION_NOT_FOUND", "Approval revision is not persisted")
                rev = json.loads(row["revision_json"])
                _validate_revision_document(rev)
                expected = (rev["content_hash"], rev["bound_content_hash"], rev["model_hash"],
                            rev["semantic_lock_manifest_hash"], rev["semantic_lock_count"])
                actual = (doc["revision_content_hash"], doc["bound_content_hash"], doc["model_hash"],
                          doc["semantic_lock_manifest_hash"], doc["semantic_lock_count"])
                if actual != expected:
                    raise PlanError("APPROVAL_RECEIPT_CHANGED", "Approval does not match persisted revision/lock receipt")
                try:
                    con.execute("INSERT INTO plan_approvals(project_id,revision_id,approval_json,approved_by,approved_at) "
                                "VALUES(?,?,?,?,?)",
                                (project_id, expected_head, _json(doc), actor_id, doc["approved_at"]))
                except sqlite3.IntegrityError as exc:
                    raise PlanError("APPROVAL_EXISTS", "Approval receipt is immutable once persisted") from exc
                con.execute("UPDATE projects SET baseline_revision_id=?,updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                            (expected_head, project_id))
                con.execute("COMMIT")
            except Exception:
                if con.in_transaction:
                    con.execute("ROLLBACK")
                raise
        return json.loads(_json(doc))

    def load_revision(self, project_id: str, *, actor_id: str, revision_id: str) -> dict:
        project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
        revision_id = _id(revision_id, "revision_id")
        with self._connect() as con:
            self._project(con, project_id)
            self._role(con, project_id, actor_id, ROLES)
            row = con.execute("SELECT revision_json FROM plan_revisions WHERE project_id=? AND revision_id=?",
                              (project_id, revision_id)).fetchone()
        if row is None:
            raise PlanError("REVISION_NOT_FOUND", "Revision does not exist in this project")
        try:
            doc = json.loads(row["revision_json"])
        except json.JSONDecodeError as exc:
            raise PlanError("STORED_REVISION_TAMPERED", "Stored revision JSON is invalid") from exc
        _validate_revision_document(doc)
        return json.loads(_json(doc))

    def approved_handoff(self, project_id: str, *, actor_id: str,
                         revision_id: str | None = None) -> dict:
        project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
        with self._connect() as con:
            project = self._project(con, project_id)
            self._role(con, project_id, actor_id, ROLES)
            rid = revision_id or project["baseline_revision_id"]
            if rid is None:
                raise PlanError("APPROVAL_REQUIRED", "Project has no persisted approved baseline")
            rid = _id(rid, "revision_id")
            rev_row = con.execute("SELECT revision_json FROM plan_revisions WHERE project_id=? AND revision_id=?",
                                  (project_id, rid)).fetchone()
            app_row = con.execute("SELECT approval_json,approved_by FROM plan_approvals "
                                  "WHERE project_id=? AND revision_id=?", (project_id, rid)).fetchone()
        if rev_row is None or app_row is None:
            raise PlanError("APPROVAL_REQUIRED", "Persisted approval/revision pair is incomplete")
        try:
            rev = json.loads(rev_row["revision_json"])
            app = json.loads(app_row["approval_json"])
        except json.JSONDecodeError as exc:
            raise PlanError("STORED_RECEIPT_TAMPERED", "Persisted baseline JSON is invalid") from exc
        _validate_revision_document(rev)
        _validate_approval_shape(app)
        expected = (rev["content_hash"], rev["bound_content_hash"], rev["model_hash"],
                    rev["semantic_lock_manifest_hash"], rev["semantic_lock_count"])
        actual = (app["revision_content_hash"], app["bound_content_hash"], app["model_hash"],
                  app["semantic_lock_manifest_hash"], app["semantic_lock_count"])
        if actual != expected:
            raise PlanError("STORED_APPROVAL_TAMPERED", "Persisted approval no longer matches its baseline")
        manifest = rev["semantic_lock_manifest"]
        selectors = [] if manifest is None else [row["selector"] for row in manifest["locks"]]
        handoff = {
            "schema": HANDOFF_SCHEMA,
            "building": rev["model"],
            "baseline": {
                "schema": "acs.plan-review/1.0",
                "revision_id": rid,
                "model_hash": rev["model_hash"],
                "content_hash": rev["content_hash"],
                "approval_scope": app["scope"],
                "lock_binding_schema": LOCK_BINDING_SCHEMA,
                "bound_content_hash": rev["bound_content_hash"],
                "semantic_lock_manifest_hash": rev["semantic_lock_manifest_hash"],
                "semantic_lock_count": rev["semantic_lock_count"],
                "persisted_approved_by": app_row["approved_by"],
            },
            "source_map": _source_map(rev["model"]),
            "semantic_lock_selectors": selectors,
        }
        _json(handoff)
        return json.loads(_json(handoff))

    def project_state(self, project_id: str, *, actor_id: str) -> dict:
        project_id, actor_id = _id(project_id, "project_id"), _id(actor_id, "actor_id")
        with self._connect() as con:
            project = self._project(con, project_id)
            role = self._role(con, project_id, actor_id, ROLES)
            rows = con.execute("SELECT revision_id,number,parent_id,created_by,created_at FROM plan_revisions "
                               "WHERE project_id=? ORDER BY number", (project_id,)).fetchall()
        return {"schema": SCHEMA, "project_id": project_id, "role": role,
                "head_revision_id": project["head_revision_id"],
                "baseline_revision_id": project["baseline_revision_id"],
                "revisions": [dict(r) for r in rows]}
