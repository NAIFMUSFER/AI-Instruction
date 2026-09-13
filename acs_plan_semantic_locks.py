"""Stable semantic lock manifests for ACS plan-first editing.

Room locks already live in :mod:`acs_plan_review`. This companion covers site and
explicitly identified nested plan elements such as warehouse racks, docks, lanes
and stations. It deliberately refuses positional/index identities: an engineer
lock must survive array reordering and therefore needs an explicit stable `id`.

The manifest is deterministic and provider-free. It is not authentication or
persistence; a trusted host must associate the manifest with the engineer/project
and an approved revision before exposing it across devices.
"""
from __future__ import annotations

import json
from typing import Any

from acs_plan_review import PlanError, canonical, digest

SCHEMA = "acs.plan-semantic-locks/1.0"
MAX_LOCKS = 256
_ELEMENT_COLLECTIONS = frozenset({
    "racks", "docks", "lanes", "stations", "doors", "windows",
    "objects", "points", "furniture",
})


def _stable_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 120


def _floor(model: dict, template: str) -> dict:
    floors = model.get("floors")
    if not isinstance(floors, dict) or template not in floors or not isinstance(floors[template], dict):
        raise PlanError("LOCK_TARGET_NOT_FOUND", "Lock template does not exist")
    return floors[template]


def _room(model: dict, template: str, room_id: str) -> dict:
    floor = _floor(model, template)
    matches = [r for r in (floor.get("rooms") or [])
               if isinstance(r, dict) and r.get("id") == room_id]
    if len(matches) != 1:
        raise PlanError("LOCK_TARGET_NOT_FOUND", "Lock room needs one stable explicit id")
    return matches[0]


def _element(model: dict, template: str, room_id: str,
             collection: str, element_id: str) -> dict:
    if collection not in _ELEMENT_COLLECTIONS:
        raise PlanError("LOCK_COLLECTION_UNSUPPORTED", "Unsupported semantic lock collection")
    room = _room(model, template, room_id)
    items = room.get(collection)
    if not isinstance(items, list):
        raise PlanError("LOCK_TARGET_NOT_FOUND", "Lock collection is not present")
    matches = [item for item in items if isinstance(item, dict) and item.get("id") == element_id]
    if len(matches) != 1:
        raise PlanError("LOCK_TARGET_NOT_FOUND", "Nested lock needs one stable explicit element id")
    return matches[0]


def _global_context(model: dict) -> dict:
    """Fields that can move/scale locked local geometry without editing it."""
    return {key: model.get(key) for key in (
        "site", "floor_height", "wall_h", "wall_t", "levels")}


def _template_context(model: dict, template: str) -> dict:
    floor = _floor(model, template)
    return {k: v for k, v in floor.items() if k != "rooms"}


def _room_context(room: dict) -> dict:
    # Nested collections may change independently. The room's own geometry/role/
    # walls remain context because changing them moves or reinterprets a rack/dock.
    return {k: v for k, v in room.items() if k not in _ELEMENT_COLLECTIONS}


def _normalize_selector(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise PlanError("INVALID_LOCK_SELECTOR", "Semantic lock selector must be an object")
    kind = raw.get("kind")
    if kind == "site":
        return {"kind": "site"}
    if kind == "room":
        template, room_id = raw.get("template"), raw.get("room_id")
        if not (_stable_id(template) and _stable_id(room_id)):
            raise PlanError("INVALID_LOCK_SELECTOR", "Room lock requires template and room_id")
        return {"kind": "room", "template": template.strip(), "room_id": room_id.strip()}
    if kind == "element":
        template, room_id = raw.get("template"), raw.get("room_id")
        collection, element_id = raw.get("collection"), raw.get("element_id")
        if not (_stable_id(template) and _stable_id(room_id)
                and isinstance(collection, str) and collection in _ELEMENT_COLLECTIONS
                and _stable_id(element_id)):
            raise PlanError("INVALID_LOCK_SELECTOR", "Element lock requires stable template/room/collection/id")
        return {"kind": "element", "template": template.strip(), "room_id": room_id.strip(),
                "collection": collection, "element_id": element_id.strip()}
    raise PlanError("INVALID_LOCK_SELECTOR", "Lock kind must be site, room or element")


def _resolve(model: dict, selector: dict) -> tuple[Any, Any]:
    kind = selector["kind"]
    if kind == "site":
        site = model.get("site")
        if not isinstance(site, dict):
            raise PlanError("LOCK_TARGET_NOT_FOUND", "Site geometry is unavailable")
        return site, {"site": site}
    if kind == "room":
        room = _room(model, selector["template"], selector["room_id"])
        context = {"global": _global_context(model),
                   "template": _template_context(model, selector["template"])}
        return room, context
    room = _room(model, selector["template"], selector["room_id"])
    item = _element(model, selector["template"], selector["room_id"],
                    selector["collection"], selector["element_id"])
    context = {"global": _global_context(model),
               "template": _template_context(model, selector["template"]),
               "room": _room_context(room)}
    return item, context


def build_lock_manifest(model: dict, selectors: list[dict]) -> dict:
    """Capture exact lock snapshots from canonical plan geometry."""
    if not isinstance(model, dict):
        raise PlanError("INVALID_PLAN", "Lock source must be canonical Building JSON")
    if not isinstance(selectors, list) or not selectors or len(selectors) > MAX_LOCKS:
        raise PlanError("INVALID_LOCK_SELECTOR", "Provide 1..256 semantic lock selectors")
    # Bound and detach source input using the same review ceiling.
    model = json.loads(canonical(model))
    normalized = [_normalize_selector(s) for s in selectors]
    identities = [canonical(s) for s in normalized]
    if len(set(identities)) != len(identities):
        raise PlanError("DUPLICATE_LOCK", "Semantic lock selectors must be unique")
    locks = []
    for selector in sorted(normalized, key=canonical):
        value, context = _resolve(model, selector)
        locks.append({"selector": selector,
                      "value_hash": digest(value),
                      "context_hash": digest(context)})
    payload = {"schema": SCHEMA, "source_model_hash": digest(model), "locks": locks}
    payload["manifest_hash"] = digest(payload)
    return payload


def verify_lock_manifest(source_model: dict, candidate_model: dict, manifest: dict) -> dict:
    """Fail closed if any locked target or its placement context changed."""
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise PlanError("INVALID_LOCK_MANIFEST", "Unknown semantic lock manifest")
    if not isinstance(source_model, dict) or not isinstance(candidate_model, dict):
        raise PlanError("INVALID_PLAN", "Semantic locks require canonical Building JSON")
    source = json.loads(canonical(source_model))
    candidate = json.loads(canonical(candidate_model))
    locks = manifest.get("locks")
    if not isinstance(locks, list) or not locks or len(locks) > MAX_LOCKS:
        raise PlanError("INVALID_LOCK_MANIFEST", "Semantic lock manifest is empty or oversized")
    check = {"schema": SCHEMA, "source_model_hash": manifest.get("source_model_hash"), "locks": locks}
    if manifest.get("manifest_hash") != digest(check):
        raise PlanError("LOCK_MANIFEST_TAMPERED", "Semantic lock manifest hash does not match")
    if manifest.get("source_model_hash") != digest(source):
        raise PlanError("LOCK_SOURCE_CHANGED", "Semantic locks were captured from another plan revision")

    seen: set[str] = set()
    for record in locks:
        if not isinstance(record, dict):
            raise PlanError("INVALID_LOCK_MANIFEST", "Malformed semantic lock record")
        selector = _normalize_selector(record.get("selector"))
        identity = canonical(selector)
        if identity in seen:
            raise PlanError("INVALID_LOCK_MANIFEST", "Duplicate semantic lock record")
        seen.add(identity)
        source_value, source_context = _resolve(source, selector)
        try:
            candidate_value, candidate_context = _resolve(candidate, selector)
        except PlanError as exc:
            raise PlanError("LOCK_VIOLATION", "A locked plan element was removed") from exc
        if record.get("value_hash") != digest(source_value) or record.get("context_hash") != digest(source_context):
            raise PlanError("LOCK_MANIFEST_TAMPERED", "Semantic lock snapshot does not match its source")
        if digest(candidate_value) != record["value_hash"]:
            raise PlanError("LOCK_VIOLATION", "A locked plan element changed")
        if digest(candidate_context) != record["context_hash"]:
            raise PlanError("LOCK_CONTEXT_CHANGED", "Placement context of a locked plan element changed")
    return {"ok": True, "manifest_hash": manifest["manifest_hash"], "lock_count": len(locks)}
