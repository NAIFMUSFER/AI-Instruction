"""Deterministic semantic diff for ACS Plan-first canonical revisions.

The diff is intentionally geometry/data driven. It does not ask a model to explain
or rank a design, does not infer regulatory compliance, and never uses array
position as engineering identity. Rooms require stable explicit IDs. Nested plan
elements use their explicit IDs when available; if a changed collection contains
unidentified items, the collection is reported as identity-unresolved rather than
matched heuristically.
"""
from __future__ import annotations

import json
from typing import Any

from acs_plan_review import PlanError, canonical, digest
from acs_plan_semantic_locks import _ELEMENT_COLLECTIONS

SCHEMA = "acs.plan-semantic-diff/1.0"
MAX_CHANGES = 512
MAX_VISIBLE_VALUE_CHARS = 2048
_VISIBLE_FIELDS = frozenset({
    "rect", "x", "z", "w", "d", "h", "levels", "edge", "dir", "kind",
    "role", "name", "type", "template", "floor_height", "wall_h", "wall_t",
})


def _stable_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 120


def _detached(value: Any) -> Any:
    return json.loads(canonical(value))


def _changed_fields(before: dict, after: dict, *, exclude=()) -> list[str]:
    excluded = set(exclude)
    keys = (set(before) | set(after)) - excluded
    return sorted(key for key in keys if before.get(key) != after.get(key))


def _visible_values(source: dict, fields: list[str]) -> dict:
    out = {}
    for key in fields:
        if key not in _VISIBLE_FIELDS or key not in source:
            continue
        value = source[key]
        try:
            text = canonical(value)
        except PlanError:
            continue
        if len(text) <= MAX_VISIBLE_VALUE_CHARS:
            out[key] = _detached(value)
    return out


def _record(*, kind: str, change: str, before: dict | None = None,
            after: dict | None = None, changed_fields: list[str] | None = None,
            **identity) -> dict:
    row = {"kind": kind, "change": change, **identity}
    if changed_fields is not None:
        row["changed_fields"] = changed_fields
    if before is not None:
        row["before_hash"] = digest(before)
    if after is not None:
        row["after_hash"] = digest(after)
    if changed_fields:
        before_values = _visible_values(before or {}, changed_fields)
        after_values = _visible_values(after or {}, changed_fields)
        if before_values:
            row["before_values"] = before_values
        if after_values:
            row["after_values"] = after_values
    return row


def _room_index(floor: dict, *, template: str) -> dict[str, dict]:
    rooms = floor.get("rooms")
    if rooms is None:
        rooms = []
    if not isinstance(rooms, list):
        raise PlanError("INVALID_DIFF_IDENTITY", "Plan diff requires a room array")
    out: dict[str, dict] = {}
    for room in rooms:
        if not isinstance(room, dict) or not _stable_id(room.get("id")):
            raise PlanError(
                "INVALID_DIFF_IDENTITY",
                "Plan diff requires stable explicit room ids",
            )
        room_id = room["id"].strip()
        if room_id in out:
            raise PlanError("INVALID_DIFF_IDENTITY", "Duplicate room id in semantic diff")
        out[room_id] = room
    return out


def _element_state(room: dict, collection: str) -> tuple[dict[str, dict] | None, Any]:
    items = room.get(collection)
    if items is None:
        items = []
    if not isinstance(items, list):
        raise PlanError("INVALID_DIFF_IDENTITY", "Nested plan collection must be an array")
    indexed: dict[str, dict] = {}
    complete = True
    for item in items:
        if not isinstance(item, dict):
            complete = False
            continue
        item_id = item.get("id")
        if not _stable_id(item_id):
            complete = False
            continue
        item_id = item_id.strip()
        if item_id in indexed:
            raise PlanError("INVALID_DIFF_IDENTITY", "Duplicate nested element id in semantic diff")
        indexed[item_id] = item
    return (indexed if complete else None), items


def _append(changes: list[dict], row: dict) -> None:
    if len(changes) >= MAX_CHANGES:
        raise PlanError("DIFF_TOO_LARGE", "Semantic diff exceeds the bounded change count")
    changes.append(row)


def _diff_collection(changes: list[dict], before_room: dict, after_room: dict,
                     *, template: str, room_id: str, collection: str) -> None:
    before_index, before_items = _element_state(before_room, collection)
    after_index, after_items = _element_state(after_room, collection)
    if before_items == after_items:
        return
    if before_index is None or after_index is None:
        _append(changes, {
            "kind": "collection",
            "change": "modified",
            "template": template,
            "room_id": room_id,
            "collection": collection,
            "identity": "UNRESOLVED",
            "before_hash": digest(before_items),
            "after_hash": digest(after_items),
        })
        return
    for element_id in sorted(set(before_index) | set(after_index)):
        before = before_index.get(element_id)
        after = after_index.get(element_id)
        identity = {
            "template": template,
            "room_id": room_id,
            "collection": collection,
            "element_id": element_id,
        }
        if before is None:
            _append(changes, _record(kind="element", change="added", after=after, **identity))
            continue
        if after is None:
            _append(changes, _record(kind="element", change="removed", before=before, **identity))
            continue
        fields = _changed_fields(before, after, exclude={"id"})
        if fields:
            _append(changes, _record(
                kind="element", change="modified", before=before, after=after,
                changed_fields=fields, **identity,
            ))


def diff_models(before_model: dict, after_model: dict) -> dict:
    """Return a stable-identity diff between two canonical ACS plan models."""
    if not isinstance(before_model, dict) or not isinstance(after_model, dict):
        raise PlanError("INVALID_PLAN", "Semantic diff requires two canonical plan objects")
    before = _detached(before_model)
    after = _detached(after_model)
    changes: list[dict] = []

    global_fields = _changed_fields(before, after, exclude={"floors"})
    if global_fields:
        _append(changes, _record(
            kind="global", change="modified", before=before, after=after,
            changed_fields=global_fields,
        ))

    before_floors = before.get("floors") or {}
    after_floors = after.get("floors") or {}
    if not isinstance(before_floors, dict) or not isinstance(after_floors, dict):
        raise PlanError("INVALID_DIFF_IDENTITY", "Plan diff requires a floors object")

    for template in sorted(set(before_floors) | set(after_floors)):
        before_floor = before_floors.get(template)
        after_floor = after_floors.get(template)
        if before_floor is None:
            if not isinstance(after_floor, dict):
                raise PlanError("INVALID_DIFF_IDENTITY", "Floor template must be an object")
            _append(changes, _record(
                kind="template", change="added", after=after_floor, template=template,
            ))
            continue
        if after_floor is None:
            if not isinstance(before_floor, dict):
                raise PlanError("INVALID_DIFF_IDENTITY", "Floor template must be an object")
            _append(changes, _record(
                kind="template", change="removed", before=before_floor, template=template,
            ))
            continue
        if not isinstance(before_floor, dict) or not isinstance(after_floor, dict):
            raise PlanError("INVALID_DIFF_IDENTITY", "Floor template must be an object")

        floor_fields = _changed_fields(before_floor, after_floor, exclude={"rooms"})
        if floor_fields:
            _append(changes, _record(
                kind="template", change="modified", before=before_floor, after=after_floor,
                changed_fields=floor_fields, template=template,
            ))

        before_rooms = _room_index(before_floor, template=template)
        after_rooms = _room_index(after_floor, template=template)
        for room_id in sorted(set(before_rooms) | set(after_rooms)):
            before_room = before_rooms.get(room_id)
            after_room = after_rooms.get(room_id)
            identity = {"template": template, "room_id": room_id}
            if before_room is None:
                _append(changes, _record(kind="room", change="added", after=after_room, **identity))
                continue
            if after_room is None:
                _append(changes, _record(kind="room", change="removed", before=before_room, **identity))
                continue

            room_fields = _changed_fields(
                before_room, after_room, exclude={"id", *_ELEMENT_COLLECTIONS},
            )
            if room_fields:
                _append(changes, _record(
                    kind="room", change="modified", before=before_room, after=after_room,
                    changed_fields=room_fields, **identity,
                ))
            for collection in sorted(_ELEMENT_COLLECTIONS):
                _diff_collection(
                    changes, before_room, after_room,
                    template=template, room_id=room_id, collection=collection,
                )

    return {
        "schema": SCHEMA,
        "before_model_hash": digest(before),
        "after_model_hash": digest(after),
        "change_count": len(changes),
        "changes": changes,
        "claims_best_option": False,
        "claims_regulatory_compliance": False,
        "claims_structural_safety": False,
    }
