"""Plan-first approval boundary for ACS canonical Building JSON.

Headless foundation, not an HTTP authentication or CAD/BIM certification service.
No provider, network, geometry repair, or compiler call occurs in this module.
A trusted in-process verifier must establish topology and vertical circulation
before conceptual approval. Missing verification is never interpreted as PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

SCHEMA = "acs.plan-review/1.0"
MAX_BYTES = 900_000
MAX_NODES = 50_000
MAX_DEPTH = 32
MAX_ROOMS = 2048
MAX_LEVELS = 256
MAX_REQUIREMENTS = 512
MAX_REVISIONS = 100
EPS = 1e-7  # numerical tolerance, not a construction/regulatory allowance
_MISSING = object()
_PROVENANCE_ELEMENT_COLLECTIONS = (
    "racks", "docks", "lanes", "stations", "doors", "windows",
    "objects", "points", "furniture",
)


class PlanError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def canonical(value: Any) -> str:
    """Bounded JSON only; do not coerce missing/invalid values or use defaults."""
    count = 0

    def walk(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            raise PlanError("INPUT_LIMIT", "JSON nesting/node limit exceeded")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or key in {"__proto__", "prototype", "constructor"}:
                    raise PlanError("INVALID_JSON_KEY", "Unsupported JSON key")
                walk(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                walk(child, depth + 1)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise PlanError("INVALID_JSON_VALUE", "Only JSON values are accepted")
        elif type(item) is float and not math.isfinite(item):
            raise PlanError("NON_FINITE", "A geometry value is not finite")
    try:
        walk(value, 0)
        text = json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise PlanError("INPUT_LIMIT", "JSON byte limit exceeded")
        return text
    except (RecursionError, UnicodeError, OverflowError, ValueError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("INVALID_JSON_VALUE", "Unsupported JSON representation") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 160


def _room_index(model: dict) -> dict[tuple[str, str], dict]:
    out = {}
    for template, floor in (model.get("floors") or {}).items():
        for room in floor.get("rooms", []):
            out[(template, room["id"])] = room
    return out


def _structure(model: Any) -> None:
    """Reject ambiguous identities before revisions, locks, or checks are recorded."""
    if not isinstance(model, dict) or not isinstance(model.get("floors"), dict):
        raise PlanError("INVALID_MODEL", "Building.floors must be an object")
    levels = model.get("levels")
    if isinstance(levels, list) and len(levels) > MAX_LEVELS:
        raise PlanError("INPUT_LIMIT", "Too many levels for this review boundary")
    total = 0
    for template, floor in model["floors"].items():
        if not _id(template) or not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            raise PlanError("INVALID_MODEL", "Each template needs an explicit rooms array")
        seen = set()
        for room in floor["rooms"]:
            total += 1
            if not isinstance(room, dict) or not _id(room.get("id")) or room["id"] in seen:
                raise PlanError("AMBIGUOUS_ROOM_ID", "Missing or duplicate room identity")
            seen.add(room["id"])
    if total > MAX_ROOMS:
        raise PlanError("INPUT_LIMIT", "Too many rooms for this review boundary")


def _provenance_requirement_ids(requirements: list[dict]) -> set[str]:
    """Return only unambiguous requirement ids and validate optional external ids.

    General Program defects remain review findings.  This admission helper is
    deliberately narrower: it rejects only provenance metadata that would make
    an explicit canonical entity→requirement link ambiguous or untraceable.
    """
    counts = Counter(
        row.get("id") for row in requirements
        if isinstance(row, dict) and _id(row.get("id"))
    )
    valid = set()
    for row in requirements:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not _id(rid) or counts[rid] != 1:
            continue
        source_id = row.get("source_id", _MISSING)
        if source_id is not _MISSING and not _id(source_id):
            raise PlanError("INVALID_PROVENANCE_SOURCE_ID",
                            "Requirement source_id must be a non-empty bounded identity")
        valid.add(rid)
    return valid


def _validate_requirement_links(entity: dict, requirement_ids: set[str], *, nested: bool) -> None:
    raw = entity.get("requirement_ids", _MISSING)
    if raw is _MISSING:
        return
    if (not isinstance(raw, list) or any(not _id(rid) for rid in raw)
            or len(raw) != len(set(raw)) or any(rid not in requirement_ids for rid in raw)):
        raise PlanError("INVALID_PROVENANCE_LINK",
                        "requirement_ids must be unique stable ids of unambiguous requirements")
    if nested and raw and not _id(entity.get("id")):
        raise PlanError("AMBIGUOUS_PROVENANCE_TARGET",
                        "Linked nested canonical elements require a stable explicit id")


def _validate_provenance_links(model: dict, requirements: list[dict]) -> None:
    """Fail closed before history records malformed explicit provenance links."""
    requirement_ids = _provenance_requirement_ids(requirements)
    for floor in model["floors"].values():
        for room in floor["rooms"]:
            _validate_requirement_links(room, requirement_ids, nested=False)
            for collection in _PROVENANCE_ELEMENT_COLLECTIONS:
                items = room.get(collection)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict):
                        _validate_requirement_links(item, requirement_ids, nested=True)


def _geometry(model: dict) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    def issue(code, path):
        if len(issues) < 256:
            issues.append({"code": code, "path": path, "severity": "error"})
        elif len(issues) == 256:
            issues.append({"code": "ADDITIONAL_ISSUES_OMITTED", "severity": "error"})
    site = model.get("site")
    w, d = (site.get("w"), site.get("d")) if isinstance(site, dict) else (None, None)
    good_site = all(_number(v) and v > 0 for v in (w, d))
    if not good_site:
        issue("SITE_NOT_SPECIFIED", "/site")
    for key in ("floor_height", "wall_h", "wall_t"):
        v = model.get(key)
        if not _number(v) or v <= 0:
            issue("DIMENSION_NOT_SPECIFIED", "/" + key)
    levels = model.get("levels")
    levels_valid = isinstance(levels, list) and bool(levels)
    if not levels_valid:
        issue("LEVELS_NOT_SPECIFIED", "/levels")
        levels = []
    seen, used = set(), set()
    for level in levels:
        if (not isinstance(level, dict) or type(level.get("index")) is not int
                or level["index"] in seen or not _id(level.get("template"))
                or level["template"] not in model["floors"]):
            issue("INVALID_LEVEL", "/levels")
            levels_valid = False
            continue
        seen.add(level["index"])
        used.add(level["template"])
    areas, room_counts = {}, {}
    for template, floor in model["floors"].items():
        path = "/floors/" + template
        if template not in used:
            issue("UNREFERENCED_TEMPLATE", path)
        rooms = floor["rooms"]
        if not rooms:
            issue("EMPTY_TEMPLATE", path)
        valid = []
        for room in rooms:
            ref = path + "/rooms/" + room["id"]
            rect = room.get("rect")
            if (not isinstance(rect, list) or len(rect) != 4
                    or not all(_number(x) for x in rect) or rect[2] <= 0 or rect[3] <= 0):
                issue("INVALID_RECT", ref)
                continue
            x, z, rw, rd = rect
            if good_site and (x < -EPS or z < -EPS or x + rw > w + EPS or z + rd > d + EPS):
                issue("OUTSIDE_SITE", ref)
            if room.get("acs_unresolved"):
                issue("UNRESOLVED_SPACE", ref)
            if room.get("polygon") is not None:
                issue("UNSUPPORTED_NON_RECTANGULAR_SPACE", ref)
            valid.append(room)
        for i, room in enumerate(valid):
            x, z, rw, rd = room["rect"]
            for other in valid[i + 1:]:
                ox, oz, ow, od = other["rect"]
                if (min(x + rw, ox + ow) - max(x, ox) > EPS
                        and min(z + rd, oz + od) - max(z, oz) > EPS):
                    issue("ROOM_OVERLAP", [template, room["id"], other["id"]])
        areas[template] = sum(r["rect"][2] * r["rect"][3] for r in valid)
        if not _number(areas[template]):
            issue("NON_FINITE_MEASUREMENT", path)
        room_counts[template] = len(rooms)
    if not model["floors"]:
        issue("EMPTY_MODEL", "/floors")
    total_area = sum(areas[l["template"]] for l in levels) if levels_valid and not issues else None
    if total_area is not None and not _number(total_area):
        issue("NON_FINITE_MEASUREMENT", "/levels")
        total_area = None
    metrics = {
        "level_count": len(levels) if levels_valid else None,
        "space_instance_count": sum(room_counts[l["template"]] for l in levels) if levels_valid else None,
        # This is NOT GFA/NFA: it is the sum of non-overlapping canonical rect areas.
        "space_rect_area_m2": total_area,
        "gross_floor_area_m2": None, "net_floor_area_m2": None, "efficiency": None,
    }
    return issues, metrics


def _program(model: dict, text: str, requirements: list[dict]) -> list[dict]:
    issues = []
    def issue(code, rid):
        issues.append({"code": code, "requirement_id": rid, "severity": "error"})
    if not requirements:
        issue("PROGRAM_NOT_CONFIRMED", None)
        return issues
    seen = set()
    rooms = _room_index(model)
    levels = model.get("levels") if isinstance(model.get("levels"), list) else []
    instances = Counter(lv.get("template") for lv in levels
                        if isinstance(lv, dict) and isinstance(lv.get("template"), str))
    # One pass per template/role, not requirements × levels × all room objects.
    counts = Counter()
    for (template, _), room in rooms.items():
        n = instances[template]
        counts[(None, None)] += n
        counts[(template, None)] += n
        if _id(room.get("role")):
            counts[(None, room["role"])] += n
            counts[(template, room["role"])] += n
    for r in requirements:
        rid = r.get("id") if isinstance(r, dict) else None
        if not isinstance(r, dict) or not _id(rid) or rid in seen:
            issue("INVALID_REQUIREMENT", rid)
            continue
        seen.add(rid)
        source, expected = r.get("source"), r.get("expected")
        evidence = r.get("evidence")
        source_span = r.get("source_span", _MISSING)
        if source_span is not _MISSING:
            span_valid = (
                isinstance(source_span, dict)
                and set(source_span) == {"start", "end"}
                and type(source_span.get("start")) is int
                and type(source_span.get("end")) is int
                and 0 <= source_span["start"] < source_span["end"] <= len(text)
            )
            if not span_valid:
                issue("INVALID_SOURCE_SPAN", rid)
            elif (not isinstance(evidence, str)
                  or text[source_span["start"]:source_span["end"]] != evidence):
                issue("SOURCE_SPAN_MISMATCH", rid)
        if source not in ("requested", "inferred", "unknown"):
            issue("INVALID_PROVENANCE", rid)
        elif source == "requested" and (not isinstance(evidence, str) or not evidence.strip() or evidence not in text):
            issue("MISSING_SOURCE_EVIDENCE", rid)
        elif source == "inferred" and r.get("confirmed") is not True:
            issue("INFERENCE_NOT_CONFIRMED", rid)
        if source == "unknown" or expected is None:
            issue("REQUIREMENT_NOT_SPECIFIED", rid)
            continue
        kind = r.get("metric")
        actual = _MISSING
        if kind in ("site_width_m", "site_depth_m"):
            site = model.get("site") or {}
            actual = site.get("w" if kind == "site_width_m" else "d") if isinstance(site, dict) else None
            valid_expected = _number(expected) and expected > 0
        elif kind == "level_count":
            actual = len(levels)
            valid_expected = type(expected) is int and expected > 0
        elif kind == "room_count":
            template, role = r.get("template"), r.get("role")
            valid_selector = ((template is None or (_id(template) and template in model["floors"]))
                              and (role is None or _id(role)))
            actual = counts[(template, role)] if valid_selector else None
            valid_expected = type(expected) is int and expected >= 0 and valid_selector
        elif kind == "min_room_area_m2":
            target = r.get("room")
            room = rooms.get(tuple(target)) if isinstance(target, list) and len(target) == 2 and all(isinstance(x, str) for x in target) else None
            rect = room.get("rect") if room else None
            if isinstance(rect, list) and len(rect) == 4 and all(_number(v) for v in rect):
                actual = rect[2] * rect[3]
            valid_expected = _number(expected) and expected > 0 and room is not None
        else:
            issue("REQUIREMENT_METRIC_NOT_SUPPORTED", rid)
            continue
        if not valid_expected:
            issue("INVALID_EXPECTATION", rid)
        elif actual is _MISSING or actual is None or not _number(actual):
            issue("REQUIREMENT_NOT_MEASURABLE", rid)
        elif (actual + EPS < expected if kind == "min_room_area_m2" else abs(actual - expected) > EPS):
            issue("REQUIREMENT_MISMATCH", rid)
    return issues


@dataclass(frozen=True)
class Revision:
    id: str
    number: int
    parent_id: str | None
    model_json: str
    requirements_json: str
    brief: str
    note: str
    locked_rooms: tuple[tuple[str, str], ...]
    created_at: str

    @property
    def model(self) -> dict:
        return json.loads(self.model_json)  # every caller receives a detached copy

    @property
    def model_hash(self) -> str:
        return hashlib.sha256(self.model_json.encode("utf-8")).hexdigest()

    @property
    def content_hash(self) -> str:
        return digest({"model": self.model, "requirements": json.loads(self.requirements_json),
                       "brief": self.brief, "locks": [list(x) for x in self.locked_rooms]})


@dataclass(frozen=True)
class Approval:
    revision_id: str
    content_hash: str
    model_hash: str
    actor_label: str  # host MUST resolve/authenticate identity; not a verified licence
    approved_at: str
    scope: str = "CONCEPTUAL_DESIGN_ONLY"


class PlanWorkspace:
    """Process-local revision aggregate. Persist externally; no cloud-save claim.

    The verifier is a trusted server-side integration, never client-supplied JSON.
    It returns {scopes:{topology:PASS,vertical_circulation:PASS},issues:[]}.
    No missing verifier or failed check can approve a draft.
    """
    def __init__(self, verifier: Callable[[dict], dict] | None = None):
        self._verifier = verifier
        self._revisions: dict[str, Revision] = {}
        self._approvals: dict[str, Approval] = {}
        self._head: str | None = None
        self._baseline: str | None = None
        self._mutex = threading.RLock()

    @property
    def head(self) -> str | None:
        return self._head

    @property
    def baseline(self) -> str | None:
        return self._baseline

    def get(self, revision_id: str) -> Revision:
        try:
            return self._revisions[revision_id]
        except KeyError as exc:
            raise PlanError("REVISION_NOT_FOUND", "Unknown plan revision") from exc

    def propose(self, model: dict, *, brief: str, requirements: list[dict],
                expected_head: str | None, note: str) -> Revision:
        with self._mutex:
            if expected_head != self._head:
                raise PlanError("STALE_REVISION", "The plan changed; rebase the proposal explicitly")
            if len(self._revisions) >= MAX_REVISIONS:
                raise PlanError("HISTORY_LIMIT", "Archive this workspace before adding revisions")
            if not isinstance(brief, str) or not brief.strip() or not isinstance(note, str) or not note.strip():
                raise PlanError("DESCRIPTION_REQUIRED", "Brief and explicit change note are required")
            if not isinstance(requirements, list):
                raise PlanError("INVALID_PROGRAM", "Requirements must be an array")
            if len(requirements) > MAX_REQUIREMENTS:
                raise PlanError("INPUT_LIMIT", "Too many requirements for this review boundary")
            model_json = canonical(model)
            requirements_json = canonical(requirements)
            canonical({"brief": brief, "note": note})
            model = json.loads(model_json)
            requirements = json.loads(requirements_json)
            _structure(model)
            _validate_provenance_links(model, requirements)
            canonical({"model": model, "requirements": requirements, "brief": brief, "note": note})
            locked = ()
            if self._head:
                previous = self.get(self._head)
                locked = previous.locked_rooms
                self._check_locks(previous, model)
            rev = Revision("plan_" + uuid.uuid4().hex, len(self._revisions) + 1,
                           self._head, model_json, requirements_json, brief, note,
                           locked, datetime.now(timezone.utc).isoformat())
            self._revisions[rev.id] = rev
            self._head = rev.id
            return rev

    def _check_locks(self, previous: Revision, model: dict) -> None:
        old = previous.model
        index = _room_index(model)
        original = _room_index(old)
        for ref in previous.locked_rooms:
            if ref not in index or canonical(index[ref]) != canonical(original[ref]):
                raise PlanError("LOCK_VIOLATION", "A locked room was removed or changed")
        if previous.locked_rooms:
            # Freeze all enclosing data rather than guessing which fields the
            # compiler uses for placement/defaults. Unlocked room edits remain free.
            before = {k: v for k, v in old.items() if k != "floors"}
            after = {k: v for k, v in model.items() if k != "floors"}
            if canonical(before) != canonical(after):
                raise PlanError("LOCK_CONTEXT_CHANGED", "The enclosing model context changed")
            for template, _ in previous.locked_rooms:
                a = {k: v for k, v in old["floors"][template].items() if k != "rooms"}
                b = {k: v for k, v in model["floors"][template].items() if k != "rooms"}
                if canonical(a) != canonical(b):
                    raise PlanError("LOCK_CONTEXT_CHANGED", "The enclosing template context changed")

    def set_room_lock(self, room_ref: tuple[str, str], *, locked: bool,
                      expected_head: str) -> Revision:
        with self._mutex:
            if type(locked) is not bool or expected_head != self._head:
                raise PlanError("STALE_REVISION", "Invalid or stale lock operation")
            old = self.get(expected_head)
            if not isinstance(room_ref, tuple) or len(room_ref) != 2 or not all(isinstance(x, str) for x in room_ref) or room_ref not in _room_index(old.model):
                raise PlanError("ROOM_NOT_FOUND", "Lock needs a stable (template, room ID)")
            locks = set(old.locked_rooms)
            if locked:
                locks.add(room_ref)
            else:
                locks.discard(room_ref)
            canonical({"model": old.model, "requirements": json.loads(old.requirements_json),
                       "brief": old.brief, "locks": [list(x) for x in sorted(locks)]})
            rev = self.propose(old.model, brief=old.brief,
                               requirements=json.loads(old.requirements_json), expected_head=expected_head,
                               note=("LOCK " if locked else "UNLOCK ") + repr(room_ref))
            # No published revision is mutated; replace this just-created value.
            from dataclasses import replace
            rev = replace(rev, locked_rooms=tuple(sorted(locks)))
            self._revisions[rev.id] = rev
            return rev

    def review(self, revision_id: str) -> dict:
        rev = self.get(revision_id)
        model = rev.model
        geometry_issues, metrics = _geometry(model)
        program_issues = _program(model, rev.brief, json.loads(rev.requirements_json))
        issues = geometry_issues + program_issues
        scopes = {"rectangular_geometry": "FAIL" if geometry_issues else "PASS",
                  "program": "FAIL" if program_issues else "PASS",
                  "topology": "NOT_VERIFIED", "vertical_circulation": "NOT_VERIFIED",
                  "regulatory_compliance": "NOT_VERIFIED", "structural_safety": "NOT_VERIFIED"}
        if self._verifier is not None and not geometry_issues:
            try:
                evidence = self._verifier(model)
                if digest(model) != rev.model_hash:
                    raise PlanError("MUTATING_VERIFIER", "Verifier must not rewrite the plan")
                if not isinstance(evidence, dict) or not isinstance(evidence.get("issues"), list):
                    raise PlanError("INVALID_VERIFICATION", "Missing verification evidence")
                for key in ("topology", "vertical_circulation"):
                    state = (evidence.get("scopes") or {}).get(key)
                    if state not in ("PASS", "FAIL", "NOT_VERIFIED"):
                        raise PlanError("INVALID_VERIFICATION", "Unknown scope result")
                    scopes[key] = state
                for item in evidence["issues"]:
                    if not isinstance(item, dict) or not _id(item.get("code")):
                        raise PlanError("INVALID_VERIFICATION", "Malformed issue")
                issues.extend(evidence["issues"])
            except Exception:
                scopes["topology"] = scopes["vertical_circulation"] = "NOT_VERIFIED"
                issues.append({"code": "VERIFICATION_UNAVAILABLE", "severity": "error"})
        ready = not issues and all(scopes[k] == "PASS" for k in
                                    ("rectangular_geometry", "program", "topology", "vertical_circulation"))
        return {"schema": SCHEMA, "revision_id": rev.id, "content_hash": rev.content_hash,
                "model_hash": rev.model_hash, "can_approve": ready, "scopes": scopes,
                "metrics": metrics, "issues": issues, "construction_approved": False}

    def approve(self, revision_id: str, *, expected_head: str, actor_label: str,
                confirmed: bool, acknowledge_concept_only: bool) -> Approval:
        with self._mutex:
            if expected_head != self._head or revision_id != self._head:
                raise PlanError("STALE_REVISION", "Approval must refer to the currently reviewed revision")
            if confirmed is not True or acknowledge_concept_only is not True or not _id(actor_label):
                raise PlanError("EXPLICIT_APPROVAL_REQUIRED", "Explicit conceptual-design approval is required")
            if not self.review(revision_id)["can_approve"]:
                raise PlanError("PLAN_NOT_READY", "Resolve failed or unverified plan checks first")
            if expected_head != self._head:
                raise PlanError("STALE_REVISION", "The plan changed during verification")
            rev = self.get(revision_id)
            approval = self._approvals.get(revision_id) or Approval(
                revision_id, rev.content_hash, rev.model_hash, actor_label,
                datetime.now(timezone.utc).isoformat())
            self._approvals[revision_id] = approval
            self._baseline = revision_id
            return approval

    def handoff(self, revision_id: str) -> dict:
        """Exact approved Building, without another LLM or silent plan repair."""
        with self._mutex:
            rev = self.get(revision_id)
            approval = self._approvals.get(revision_id)
            if approval is None:
                raise PlanError("APPROVAL_REQUIRED", "Drafts cannot enter the approved 3D path")
            if approval.content_hash != rev.content_hash or approval.model_hash != rev.model_hash:
                raise PlanError("BASELINE_CHANGED", "Approved content does not match its receipt")
            model = rev.model
            return {"building": model, "baseline": {
                "schema": SCHEMA, "revision_id": rev.id, "model_hash": rev.model_hash,
                "content_hash": rev.content_hash, "approval_scope": approval.scope},
                "source_map": [{"level_index": lv["index"], "template": lv["template"],
                                "room_id": room["id"]}
                               for lv in model["levels"]
                               for room in model["floors"][lv["template"]]["rooms"]]}

    def history(self) -> list[dict]:
        with self._mutex:
            return [{"revision_id": r.id, "version": r.number, "parent_id": r.parent_id,
                     "state": "APPROVED" if r.id in self._approvals else "DRAFT",
                     "baseline": r.id == self._baseline, "note": r.note}
                    for r in self._revisions.values()]
