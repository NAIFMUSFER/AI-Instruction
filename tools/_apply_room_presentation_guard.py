from pathlib import Path

p = Path('tools/acs_plan_handoff.py')
s = p.read_text()
marker = '\ndef compile_approved_baseline(\n'
assert marker in s

guard = '''

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
'''

s = s.replace(marker, guard + marker, 1)
call_anchor = '    _require_explicit_warehouse_dock_geometry(building)\n    baseline = '
assert call_anchor in s
s = s.replace(
    call_anchor,
    '    _require_explicit_warehouse_dock_geometry(building)\n'
    '    _require_explicit_approved_room_presentation_geometry(building)\n'
    '    baseline = ',
    1,
)
p.write_text(s)
