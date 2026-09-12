"""Approved-plan-only 3D compilation boundary for ACS Plan-first v2.

This module never calls an LLM and never repairs/replans geometry. It accepts only
an already-approved :class:`acs_plan_review.PlanWorkspace` revision, compiles the
exact canonical Building JSON returned by ``workspace.handoff()``, embeds a
non-geometric baseline receipt into the glTF root ``extras``, and writes a
hash-bound provenance sidecar next to the artifact.

The sidecar is traceability evidence, not regulatory/structural certification.
This module intentionally lives under ``tools/`` while the 3D handoff is an
offline/CI foundation rather than a public production route. Import is inert:
``acs_compiler`` is imported only inside the compile function.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Callable

from acs_plan_review import PlanError, PlanWorkspace, canonical, digest
from acs_plan_projection import PROVENANCE_SCHEMA, provenance_map

SCHEMA = "acs.plan-3d-handoff/1.0"


def _artifact_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_paths(out_path: str | os.PathLike[str]) -> tuple[Path, Path]:
    out = Path(out_path)
    if not out.name or out.suffix.lower() != ".gltf":
        raise PlanError("INVALID_OUTPUT_PATH", "Approved 3D handoff currently emits .gltf only")
    parent = out.parent if str(out.parent) else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise PlanError("OUTPUT_DIR_MISSING", "3D output directory must already exist")
    if out.exists() and out.is_symlink():
        raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing to replace a symlinked 3D artifact")
    sidecar = Path(str(out) + ".baseline.json")
    if sidecar.exists() and sidecar.is_symlink():
        raise PlanError("UNSAFE_OUTPUT_PATH", "Refusing to replace a symlinked baseline receipt")
    return out, sidecar


def _embed_baseline_marker(gltf_path: Path, marker: dict) -> None:
    try:
        raw = json.loads(gltf_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "Compiler did not produce readable glTF JSON") from exc
    if not isinstance(raw, dict):
        raise PlanError("INVALID_3D_ARTIFACT", "Compiler glTF root must be an object")
    extras = raw.get("extras")
    if extras is None:
        extras = {}
        raw["extras"] = extras
    if not isinstance(extras, dict) or "acs_plan_baseline" in extras:
        raise PlanError("INVALID_3D_ARTIFACT", "glTF extras cannot safely carry ACS baseline provenance")
    extras["acs_plan_baseline"] = marker
    # The canonical plan/receipt envelope is deliberately bounded to 900 kB,
    # but a real glTF can be much larger. Do not route artifact JSON through
    # ``canonical`` merely to serialize it: that would reject valid large
    # geometry after a successful compile. We still reject NaN/Infinity and
    # hash the final bytes below; baseline metadata itself remains canonical.
    try:
        encoded = json.dumps(raw, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "glTF JSON contains unsupported values") from exc
    gltf_path.write_text(encoded, encoding="utf-8")


def _verify_space_map_matches_handoff(handoff_map: object, provenance: dict) -> None:
    """Prove provenance enrichment did not add/drop/relabel canonical spaces."""
    if not isinstance(handoff_map, list):
        raise PlanError("PROVENANCE_MISMATCH", "Approved handoff source map is malformed")
    legacy = []
    for row in handoff_map:
        if not isinstance(row, dict):
            raise PlanError("PROVENANCE_MISMATCH", "Approved handoff source identity is malformed")
        legacy.append((row.get("level_index"), row.get("template"), row.get("room_id")))
    enriched = [
        (entry["source"].get("level_index"), entry["source"].get("template"),
         entry["source"].get("room_id"))
        for entry in provenance.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("source"), dict)
        and entry["source"].get("kind") == "space"
    ]
    if legacy != enriched:
        raise PlanError("PROVENANCE_MISMATCH",
                        "Requirement provenance does not match approved canonical space identities")


def _is_finite_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


_APPROVED_NESTED_COLLECTIONS = (
    "racks", "docks", "lanes", "stations", "doors", "windows",
    "objects", "points", "furniture",
)


def _stable_nested_identity(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 160


def _require_traceable_approved_nested_elements(building: dict) -> None:
    """Require stable canonical identity for geometry that can reach approved 3D.

    ``provenance_map`` derives nested-element ``source_id`` only from a stable
    explicit canonical ``id``.  Final approved 3D therefore refuses anonymous
    nested geometry instead of promoting renderer array position to engineering
    identity.  Requirement links/source ids are never invented here.
    """
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace owns the top-level model contract.
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict):
                continue
            room_id = room.get("id")
            for collection in _APPROVED_NESTED_COLLECTIONS:
                items = room.get(collection)
                if items is None:
                    continue
                if not isinstance(items, list):
                    continue  # Existing provenance admission owns malformed shapes.
                for index, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue  # Existing provenance admission owns malformed entries.
                    if not _stable_nested_identity(item.get("id")):
                        where = f"{template}/{room_id}/{collection}/{index}"
                        raise PlanError(
                            "DOWNSTREAM_PROVENANCE_NOT_SPECIFIED",
                            f"Approved nested geometry requires a stable explicit id at {where}",
                        )


def _require_explicit_object_geometry(building: dict) -> None:
    """Prevent approved 3D from inventing shared room.objects geometry."""
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace owns the top-level model contract.
    panel_kinds = {
        "tv", "rug", "curtain", "sign",
        "شاشة", "تلفزيون", "سجادة", "ستارة", "لوحة",
    }
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict) or "objects" not in room:
                continue
            objects = room.get("objects")
            if not isinstance(objects, list):
                continue  # Existing provenance admission owns malformed collection shapes.
            for index, obj in enumerate(objects):
                where = f"{template}/{room.get('id')}/objects/{index}"
                if not isinstance(obj, dict):
                    continue  # Existing provenance admission owns malformed entries.
                required = ("kind", "x", "z", "y", "w", "d", "h", "count", "pitch", "dir")
                missing = [key for key in required if key not in obj]
                if missing:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        f"Approved object geometry is missing {','.join(missing)} at {where}",
                    )
                kind = obj["kind"]
                if not isinstance(kind, str) or not kind.strip():
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Object kind is invalid at {where}")
                if obj["dir"] not in {"x", "z"}:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Object direction is invalid at {where}")
                for key in ("x", "z", "y"):
                    if not _is_finite_number(obj[key]):
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Object {key} must be an explicit finite number at {where}",
                        )
                for key in ("w", "d", "h", "pitch"):
                    value = obj[key]
                    if not _is_finite_number(value) or value <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Object {key} must be an explicit positive finite number at {where}",
                        )
                count = obj["count"]
                if type(count) is not int or not 1 <= count <= 200:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved object count would be changed by the 3D compiler at {where}",
                    )
                if kind.strip().lower() in panel_kinds:
                    if "height" not in obj:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                            f"Approved panel object vertical position is missing height at {where}",
                        )
                    height = obj["height"]
                    if not _is_finite_number(height) or height < 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Panel object height must be an explicit non-negative finite number at {where}",
                        )


def _require_explicit_warehouse_rack_geometry(building: dict) -> None:
    """Prevent approved warehouse 3D from defaulting or clamping rack geometry."""
    meta = building.get("meta")
    if not isinstance(meta, dict) or str(meta.get("type", "")).strip().lower() != "warehouse":
        return
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace structure validation owns the top-level model contract.
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict) or "racks" not in room:
                continue
            racks = room.get("racks")
            if not isinstance(racks, list):
                raise PlanError(
                    "DOWNSTREAM_GEOMETRY_INVALID",
                    f"Approved warehouse racks must be a list at {template}/{room.get('id')}",
                )
            rect = room.get("rect")
            room_w = room_d = None
            if isinstance(rect, list) and len(rect) == 4:
                room_w, room_d = rect[2], rect[3]
            for index, rack in enumerate(racks):
                where = f"{template}/{room.get('id')}/racks/{index}"
                if not isinstance(rack, dict):
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Rack geometry is invalid at {where}")
                required = (
                    "x", "z", "w", "d", "dir", "rows",
                    "depth", "bay", "aisle", "levels", "h",
                )
                missing = [key for key in required if key not in rack]
                if missing:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        f"Approved rack geometry is missing {','.join(missing)} at {where}",
                    )
                if rack["dir"] not in {"x", "z"}:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Rack direction is invalid at {where}")
                for key in ("x", "z"):
                    value = rack[key]
                    if not _is_finite_number(value):
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Rack {key} must be an explicit finite number at {where}",
                        )
                for key in ("w", "d", "depth", "bay", "aisle", "h"):
                    value = rack[key]
                    if not _is_finite_number(value) or value <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Rack {key} must be an explicit positive finite number at {where}",
                        )
                rows = rack["rows"]
                levels = rack["levels"]
                if type(rows) is not int or not 1 <= rows <= 40:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved rack rows would be changed by the 3D compiler at {where}",
                    )
                if type(levels) is not int or not 1 <= levels <= 10:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved rack levels would be changed by the 3D compiler at {where}",
                    )
                if (not _is_finite_number(room_w) or not _is_finite_number(room_d)
                        or room_w <= 0 or room_d <= 0):
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Rack owning-room extent is invalid at {where}",
                    )
                if rack["w"] > room_w or rack["d"] > room_d:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved rack extent would be clamped by the 3D compiler at {where}",
                    )


def _require_explicit_warehouse_lane_geometry(building: dict) -> None:
    """Prevent approved warehouse 3D from filling lane geometry with compiler defaults."""
    meta = building.get("meta")
    if not isinstance(meta, dict) or str(meta.get("type", "")).strip().lower() != "warehouse":
        return
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace structure validation owns the top-level model contract.
    lane_kinds = {
        "forklift", "pedestrian", "amr", "robot", "one_way",
        "zone", "fire", "safety", "conveyor",
    }
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict) or "lanes" not in room:
                continue
            lanes = room.get("lanes")
            if not isinstance(lanes, list):
                continue  # Existing provenance admission owns malformed collection shapes.
            for index, lane in enumerate(lanes):
                where = f"{template}/{room.get('id')}/lanes/{index}"
                if not isinstance(lane, dict):
                    continue  # Existing provenance admission owns malformed entries.
                required = ("kind", "x", "z", "w", "d", "dir")
                missing = [key for key in required if key not in lane]
                if missing:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        f"Approved lane geometry is missing {','.join(missing)} at {where}",
                    )
                if lane["kind"] not in lane_kinds:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Lane kind is invalid at {where}")
                if lane["dir"] not in {"x", "z"}:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Lane direction is invalid at {where}")
                for key in ("x", "z"):
                    value = lane[key]
                    if not _is_finite_number(value):
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Lane {key} must be an explicit finite number at {where}",
                        )
                for key in ("w", "d"):
                    value = lane[key]
                    if not _is_finite_number(value) or value <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Lane {key} must be an explicit positive finite number at {where}",
                        )
                if lane["kind"] == "conveyor":
                    if "h" not in lane:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                            f"Approved conveyor lane geometry is missing h at {where}",
                        )
                    height = lane["h"]
                    if not _is_finite_number(height) or height <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Conveyor lane h must be an explicit positive finite number at {where}",
                        )

def _require_explicit_warehouse_station_geometry(building: dict) -> None:
    """Prevent approved warehouse 3D from filling station geometry with compiler defaults."""
    meta = building.get("meta")
    if not isinstance(meta, dict) or str(meta.get("type", "")).strip().lower() != "warehouse":
        return
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace structure validation owns the top-level model contract.
    station_kinds = {
        "pack", "inspect", "label", "qa", "sort",
        "void", "desk", "charger", "locker", "wrap",
    }
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict) or "stations" not in room:
                continue
            stations = room.get("stations")
            if not isinstance(stations, list):
                continue  # Existing provenance admission owns malformed collection shapes.
            for index, station in enumerate(stations):
                where = f"{template}/{room.get('id')}/stations/{index}"
                if not isinstance(station, dict):
                    continue  # Existing provenance admission owns malformed entries.
                required = ("kind", "x", "z", "w", "d", "h", "pitch", "dir", "count")
                missing = [key for key in required if key not in station]
                if missing:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        f"Approved station geometry is missing {','.join(missing)} at {where}",
                    )
                if station["kind"] not in station_kinds:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Station kind is invalid at {where}")
                if station["dir"] not in {"x", "z"}:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Station direction is invalid at {where}")
                for key in ("x", "z"):
                    value = station[key]
                    if not _is_finite_number(value):
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Station {key} must be an explicit finite number at {where}",
                        )
                for key in ("w", "d", "h", "pitch"):
                    value = station[key]
                    if not _is_finite_number(value) or value <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Station {key} must be an explicit positive finite number at {where}",
                        )
                count = station["count"]
                if type(count) is not int or not 1 <= count <= 60:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved station count would be changed by the 3D compiler at {where}",
                    )


def _require_explicit_warehouse_dock_geometry(building: dict) -> None:
    """Prevent approved warehouse 3D from filling dock geometry with compiler defaults."""
    meta = building.get("meta")
    if not isinstance(meta, dict) or str(meta.get("type", "")).strip().lower() != "warehouse":
        return
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return  # PlanWorkspace structure validation owns the top-level model contract.
    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict) or "docks" not in room:
                continue
            docks = room.get("docks")
            if not isinstance(docks, list):
                raise PlanError(
                    "DOWNSTREAM_GEOMETRY_INVALID",
                    f"Approved warehouse docks must be a list at {template}/{room.get('id')}",
                )
            for index, dock in enumerate(docks):
                where = f"{template}/{room.get('id')}/docks/{index}"
                if not isinstance(dock, dict):
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Dock geometry is invalid at {where}")
                required = ("edge", "offset", "width", "height", "count", "pitch")
                missing = [key for key in required if key not in dock]
                if missing:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                        f"Approved dock geometry is missing {','.join(missing)} at {where}",
                    )
                if dock["edge"] not in {"N", "S", "E", "W"}:
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID", f"Dock edge is invalid at {where}")
                count = dock["count"]
                if type(count) is not int or not 1 <= count <= 24:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Approved dock count would be changed by the 3D compiler at {where}",
                    )
                for key in ("width", "height", "pitch"):
                    value = dock[key]
                    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                        raise PlanError(
                            "DOWNSTREAM_GEOMETRY_INVALID",
                            f"Dock {key} must be an explicit positive finite number at {where}",
                        )
                offset = dock["offset"]
                if type(offset) not in (int, float) or not math.isfinite(offset) or offset < 0:
                    raise PlanError(
                        "DOWNSTREAM_GEOMETRY_INVALID",
                        f"Dock offset must be an explicit non-negative finite number at {where}",
                    )



def _require_explicit_approved_room_presentation_geometry(building: dict) -> None:
    """Prevent derived 3D from inventing room presentation geometry after approval.

    This guard is typology-agnostic and validates only fields that the current
    compiler otherwise defaults or reclassifies. It does not infer dimensions,
    repair geometry, or establish regulatory/MEP/accessibility compliance.
    """
    floors = building.get("floors")
    if not isinstance(floors, dict):
        return

    point_kinds = {
        "outlet", "switch", "network", "usb", "tv", "ev",
        "light", "spot", "camera", "ac", "vent", "smoke",
        "sprinkler", "exit",
    }
    point_height_kinds = {"outlet", "switch", "network", "usb", "tv", "ev", "exit"}

    def required(item: dict, keys: tuple[str, ...], label: str, where: str) -> None:
        missing = [key for key in keys if key not in item]
        if missing:
            raise PlanError(
                "DOWNSTREAM_GEOMETRY_NOT_SPECIFIED",
                f"Approved {label} geometry is missing {','.join(missing)} at {where}",
            )

    def finite(item: dict, keys: tuple[str, ...], label: str, where: str,
               *, positive: bool = False, non_negative: bool = False) -> None:
        for key in keys:
            value = item[key]
            if not _is_finite_number(value):
                raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                f"Approved {label} {key} must be finite at {where}")
            if positive and value <= 0:
                raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                f"Approved {label} {key} must be positive at {where}")
            if non_negative and value < 0:
                raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                f"Approved {label} {key} must be non-negative at {where}")

    for template, floor in floors.items():
        if not isinstance(floor, dict) or not isinstance(floor.get("rooms"), list):
            continue
        for room in floor["rooms"]:
            if not isinstance(room, dict):
                continue
            room_id = room.get("id")

            for collection, label in (("doors", "door"), ("windows", "window")):
                items = room.get(collection)
                if items is None:
                    continue
                if not isinstance(items, list):
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                    f"Approved {collection} must be a list at {template}/{room_id}")
                for index, item in enumerate(items):
                    where = f"{template}/{room_id}/{collection}/{index}"
                    if not isinstance(item, dict):
                        raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                        f"Approved {label} geometry is invalid at {where}")
                    if collection == "doors":
                        required(item, ("edge", "offset", "width", "height", "material"), label, where)
                    else:
                        required(item, ("edge", "offset", "width", "sill", "height"), label, where)
                    if item["edge"] not in {"N", "S", "E", "W"}:
                        raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                        f"Approved {label} edge is invalid at {where}")
                    finite(item, ("offset",), label, where, non_negative=True)
                    finite(item, ("width", "height"), label, where, positive=True)
                    if collection == "windows":
                        finite(item, ("sill",), label, where, non_negative=True)
                    else:
                        material = item["material"]
                        if not isinstance(material, str) or not material.strip():
                            raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                            f"Approved door material is invalid at {where}")

            points = room.get("points")
            if points is not None:
                if not isinstance(points, list):
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                    f"Approved points must be a list at {template}/{room_id}")
                for index, point in enumerate(points):
                    where = f"{template}/{room_id}/points/{index}"
                    if not isinstance(point, dict):
                        raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                        f"Approved point geometry is invalid at {where}")
                    required(point, ("type", "x", "z"), "point", where)
                    kind = point["type"]
                    if kind not in point_kinds:
                        raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                        f"Approved point type is not implemented at {where}")
                    finite(point, ("x", "z"), "point", where)
                    if kind in point_height_kinds:
                        required(point, ("height",), "point", where)
                        finite(point, ("height",), "point", where, non_negative=True)

            furniture = room.get("furniture")
            if furniture is not None:
                if not isinstance(furniture, list):
                    raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                    f"Approved furniture must be a list at {template}/{room_id}")
                for index, item in enumerate(furniture):
                    where = f"{template}/{room_id}/furniture/{index}"
                    if not isinstance(item, dict):
                        raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                        f"Approved furniture geometry is invalid at {where}")
                    required(item, ("name", "x", "z", "w", "d", "h", "mat"), "furniture", where)
                    finite(item, ("x", "z"), "furniture", where)
                    finite(item, ("w", "d", "h"), "furniture", where, positive=True)
                    for key in ("name", "mat"):
                        value = item[key]
                        if not isinstance(value, str) or not value.strip():
                            raise PlanError("DOWNSTREAM_GEOMETRY_INVALID",
                                            f"Approved furniture {key} is invalid at {where}")

def compile_approved_baseline(
    workspace: PlanWorkspace,
    revision_id: str,
    out_path: str | os.PathLike[str],
    *,
    compiler: Callable[[dict, str], tuple[int, int]] | None = None,
    overwrite: bool = False,
) -> dict:
    """Compile exactly one approved baseline and return its provenance receipt.

    ``workspace.handoff`` is the authority boundary: drafts fail before the
    compiler is imported/called. The Building object is canonicalized and hashed
    before compilation; mutation by the compiler fails closed. The final file is
    written atomically only after those checks pass.
    """
    if not isinstance(workspace, PlanWorkspace):
        raise PlanError("INVALID_WORKSPACE", "Approved 3D handoff requires a PlanWorkspace")
    out, sidecar = _output_paths(out_path)
    if not overwrite and (out.exists() or sidecar.exists()):
        raise PlanError("OUTPUT_EXISTS", "Refusing to overwrite an existing 3D artifact or receipt")

    handoff = workspace.handoff(revision_id)
    revision = workspace.get(revision_id)
    building = json.loads(canonical(handoff.get("building")))
    _require_traceable_approved_nested_elements(building)
    _require_explicit_object_geometry(building)
    _require_explicit_warehouse_rack_geometry(building)
    _require_explicit_warehouse_lane_geometry(building)
    _require_explicit_warehouse_station_geometry(building)
    _require_explicit_warehouse_dock_geometry(building)
    _require_explicit_approved_room_presentation_geometry(building)
    baseline = json.loads(canonical(handoff.get("baseline")))
    provenance = provenance_map(revision)
    _verify_space_map_matches_handoff(handoff.get("source_map"), provenance)
    source_map = json.loads(canonical(provenance["entries"]))
    before_json = canonical(building)
    before_hash = digest(building)
    if baseline.get("model_hash") != before_hash or revision.model_hash != before_hash:
        raise PlanError("BASELINE_CHANGED", "Approved handoff model hash does not match its receipt")
    source_map_hash = digest(source_map)

    if compiler is None:
        import acs_compiler as _compiler
        compiler = _compiler.compile_building
        compiler_id = "acs_compiler.compile_building"
    else:
        compiler_id = getattr(compiler, "__qualname__", None) or getattr(compiler, "__name__", None) or "callable"

    temp_artifact = None
    temp_receipt = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".acs-plan-", suffix=".gltf", dir=str(out.parent))
        os.close(fd)
        os.unlink(temp_name)  # compiler owns creation; existence is verified below
        temp_artifact = Path(temp_name)

        result = compiler(building, str(temp_artifact))
        if (not isinstance(result, tuple) or len(result) != 2
                or type(result[0]) is not int or type(result[1]) is not int
                or result[0] < 0 or result[1] < 0):
            raise PlanError("INVALID_COMPILER_RESULT", "3D compiler returned invalid node/buffer measurements")
        if canonical(building) != before_json or digest(building) != before_hash:
            raise PlanError("COMPILER_MUTATED_BASELINE", "3D compiler modified the approved canonical plan")
        if not temp_artifact.exists() or not temp_artifact.is_file() or temp_artifact.stat().st_size <= 0:
            raise PlanError("MISSING_3D_ARTIFACT", "3D compiler did not produce a non-empty glTF artifact")

        marker = {
            "schema": SCHEMA,
            "revision_id": baseline.get("revision_id"),
            "model_hash": before_hash,
            "content_hash": baseline.get("content_hash"),
            "approval_scope": baseline.get("approval_scope"),
            "provenance_schema": provenance["schema"],
            "requirements_hash": provenance["requirements_hash"],
            "provenance_hash": provenance["provenance_hash"],
            "source_map_hash": source_map_hash,
        }
        _embed_baseline_marker(temp_artifact, marker)
        artifact_sha = _artifact_sha(temp_artifact)
        receipt = {
            "schema": SCHEMA,
            "mode": "DETERMINISTIC_APPROVED_BASELINE_ONLY",
            "revision_id": marker["revision_id"],
            "model_hash": before_hash,
            "content_hash": marker["content_hash"],
            "approval_scope": marker["approval_scope"],
            "provenance_schema": provenance["schema"],
            "requirements_hash": provenance["requirements_hash"],
            "provenance_hash": provenance["provenance_hash"],
            "source_map_hash": source_map_hash,
            "source_map": source_map,
            "compiler": compiler_id,
            "compiler_node_count": result[0],
            "compiler_buffer_bytes": result[1],
            "artifact_sha256": artifact_sha,
            "artifact_bytes": temp_artifact.stat().st_size,
            "provider_calls": 0,
            "regulatory_compliance": "NOT_VERIFIED",
            "structural_safety": "NOT_VERIFIED",
        }
        canonical(receipt)

        fd, receipt_name = tempfile.mkstemp(prefix=".acs-plan-", suffix=".baseline.json", dir=str(out.parent))
        os.close(fd)
        temp_receipt = Path(receipt_name)
        temp_receipt.write_text(canonical(receipt), encoding="utf-8")

        os.replace(temp_artifact, out)
        temp_artifact = None
        os.replace(temp_receipt, sidecar)
        temp_receipt = None
        return json.loads(canonical(receipt))
    finally:
        for path in (temp_artifact, temp_receipt):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def verify_compiled_artifact(out_path: str | os.PathLike[str], receipt: dict | None = None) -> dict:
    """Verify artifact bytes and embedded baseline marker against the sidecar/receipt."""
    out, sidecar = _output_paths(out_path)
    if not out.exists() or not out.is_file():
        raise PlanError("MISSING_3D_ARTIFACT", "3D artifact is missing")
    if receipt is None:
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("MISSING_BASELINE_RECEIPT", "3D baseline sidecar is missing or invalid") from exc
    receipt = json.loads(canonical(receipt))
    if receipt.get("schema") != SCHEMA or receipt.get("mode") != "DETERMINISTIC_APPROVED_BASELINE_ONLY":
        raise PlanError("INVALID_BASELINE_RECEIPT", "Unknown 3D baseline receipt")
    actual_sha = _artifact_sha(out)
    if receipt.get("artifact_sha256") != actual_sha or receipt.get("artifact_bytes") != out.stat().st_size:
        raise PlanError("ARTIFACT_CHANGED", "3D artifact bytes no longer match the approved receipt")
    try:
        gltf = json.loads(out.read_text(encoding="utf-8"))
        marker = (gltf.get("extras") or {}).get("acs_plan_baseline") if isinstance(gltf, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanError("INVALID_3D_ARTIFACT", "3D artifact is not readable glTF JSON") from exc
    expected = {k: receipt.get(k) for k in (
        "schema", "revision_id", "model_hash", "content_hash", "approval_scope",
        "provenance_schema", "requirements_hash", "provenance_hash", "source_map_hash")}
    if not isinstance(marker, dict) or canonical(marker) != canonical(expected):
        raise PlanError("PROVENANCE_MISMATCH", "Embedded 3D baseline provenance does not match the receipt")
    if digest(receipt.get("source_map")) != receipt.get("source_map_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "Source map hash does not match the receipt")
    if receipt.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise PlanError("PROVENANCE_MISMATCH", "Unknown plan provenance schema")
    reconstructed = {
        "schema": receipt["provenance_schema"],
        "revision_id": receipt.get("revision_id"),
        "model_hash": receipt.get("model_hash"),
        "requirements_hash": receipt.get("requirements_hash"),
        "entries": receipt.get("source_map"),
    }
    if digest(reconstructed) != receipt.get("provenance_hash"):
        raise PlanError("PROVENANCE_MISMATCH", "Plan provenance hash does not match its source map")
    return {"ok": True, "artifact_sha256": actual_sha,
            "revision_id": receipt.get("revision_id"), "model_hash": receipt.get("model_hash"),
            "requirements_hash": receipt.get("requirements_hash")}
