"""Deterministic, non-regulatory scorecard for ACS plan-first canonical models.

This module only measures geometry and explicit operational data already present in
canonical Building JSON. It does not infer code compliance, required clearances,
usable/load-rated storage capacity, throughput, safety, or daylight. Missing inputs
remain unknown. No provider, network, CAD, compiler, or production route is imported
here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

SCHEMA = "acs.plan-scorecard/1.0"
EPS = 1e-9
_INDUSTRIAL = {"warehouse", "industrial", "factory", "logistics", "مستودع"}


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _positive(value: Any) -> bool:
    return _finite(value) and value > 0


def _count(value: Any, *, default: int = 1) -> int | None:
    if value is None:
        return default
    if type(value) is int and value >= 0:
        return value
    return None


def _typology(model: dict) -> str:
    meta = model.get("meta") if isinstance(model.get("meta"), dict) else {}
    raw = str(meta.get("type") or meta.get("building_type") or "").strip().lower()
    if raw in _INDUSTRIAL:
        return "warehouse"
    # Do not classify a non-industrial model from a single generic room role.
    if raw:
        return raw
    return "unknown"


def _level_templates(model: dict) -> tuple[list[str], list[str]]:
    """Return valid template instances and disclosure warnings.

    Repeated templates are repeated intentionally because measured areas/counts are
    building-instance metrics, not template-library metrics.
    """
    floors = model.get("floors") if isinstance(model.get("floors"), dict) else {}
    levels = model.get("levels")
    warnings: list[str] = []
    if not isinstance(levels, list) or not levels:
        return [], ["LEVELS_NOT_MEASURABLE"]
    templates: list[str] = []
    seen_indices: set[int] = set()
    for level in levels:
        if not isinstance(level, dict) or type(level.get("index")) is not int:
            warnings.append("INVALID_LEVEL_IDENTITY")
            continue
        if level["index"] in seen_indices:
            warnings.append("DUPLICATE_LEVEL_INDEX")
            continue
        seen_indices.add(level["index"])
        template = level.get("template")
        if not isinstance(template, str) or template not in floors:
            warnings.append("LEVEL_TEMPLATE_NOT_MEASURABLE")
            continue
        templates.append(template)
    return templates, warnings


def _rect_tuple(rect: Any) -> tuple[float, float, float, float] | None:
    if (not isinstance(rect, list) or len(rect) != 4
            or not all(_finite(v) for v in rect)
            or rect[2] <= 0 or rect[3] <= 0):
        return None
    return float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])


def _rect_area(rect: Any) -> float | None:
    normalized = _rect_tuple(rect)
    if normalized is None:
        return None
    area = normalized[2] * normalized[3]
    return area if math.isfinite(area) else None


def _lane_rect(lane: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(lane, dict):
        return None
    x, z, w, d = lane.get("x"), lane.get("z"), lane.get("w"), lane.get("d")
    if not (_finite(x) and _finite(z) and _positive(w) and _positive(d)):
        return None
    return float(x), float(z), float(w), float(d)


def _lane_area(lane: Any) -> float | None:
    rect = _lane_rect(lane)
    if rect is None:
        return None
    area = rect[2] * rect[3]
    return area if math.isfinite(area) else None


def _lane_centerline_length(lane: Any) -> float | None:
    """Measure only an explicitly oriented lane rectangle's longitudinal axis.

    This is declared lane geometry, not an origin/destination route, travel path,
    egress distance, throughput model, or safety-compliance result.
    """
    rect = _lane_rect(lane)
    if rect is None or not isinstance(lane, dict):
        return None
    direction = str(lane.get("dir") or "").strip().lower()
    if direction == "x":
        return rect[2]
    if direction == "z":
        return rect[3]
    return None


def _rack_footprint_area(rack: Any) -> float | None:
    """Return the explicit rack-group rectangle area when both dimensions exist."""
    if not isinstance(rack, dict):
        return None
    w, d = rack.get("w"), rack.get("d")
    if not (_positive(w) and _positive(d)):
        return None
    area = w * d
    return area if math.isfinite(area) else None


def _rack_rect(rack: Any) -> tuple[float, float, float, float] | None:
    """Return explicit room-relative rack geometry only when position and size exist."""
    if not isinstance(rack, dict):
        return None
    x, z, w, d = rack.get("x"), rack.get("z"), rack.get("w"), rack.get("d")
    if not (_finite(x) and _finite(z) and _positive(w) and _positive(d)):
        return None
    return float(x), float(z), float(w), float(d)


def _rack_geometric_counts(rack: Any) -> tuple[int, int] | None:
    """Return modeled bay and bay-level counts from explicit rack geometry only.

    A bay is one declared ``bay`` pitch along the rack run for each explicit row.
    A bay-level position is that geometric bay count multiplied by explicit rack
    levels. These are geometric layout counts, not pallet positions, usable/load-
    rated storage capacity, clearance proof or throughput. Missing/invalid inputs
    fail closed instead of borrowing the 3D compiler's presentation defaults.
    """
    if not isinstance(rack, dict):
        return None
    direction = rack.get("dir")
    w, d = rack.get("w"), rack.get("d")
    bay, rows, levels = rack.get("bay"), rack.get("rows"), rack.get("levels")
    if (direction not in {"x", "z"}
            or not _positive(w) or not _positive(d) or not _positive(bay)
            or type(rows) is not int or rows <= 0
            or type(levels) is not int or levels <= 0):
        return None
    run = w if direction == "x" else d
    bays_per_row = math.floor(run / bay)
    if bays_per_row < 1:
        return None
    bays = bays_per_row * rows
    return bays, bays * levels


def _rect_overlap_area(a: tuple[float, float, float, float],
                       b: tuple[float, float, float, float]) -> float:
    ax, az, aw, ad = a
    bx, bz, bw, bd = b
    w = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    d = max(0.0, min(az + ad, bz + bd) - max(az, bz))
    return w * d


def _element_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    value = item.get("id")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _measure_configured_routes(model: dict) -> tuple[dict[str, float] | None,
                                                       dict[str, float] | None,
                                                       list[dict], str | None]:
    """Measure explicit warehouse route polylines, failing the set closed.

    Nothing is routed or optimized here: each route length is the Euclidean sum of
    its supplied site-coordinate polyline segments. One malformed route invalidates
    the whole configured-route measurement so a partial aggregate cannot look
    authoritative.
    """
    raw = model.get("routes")
    if raw is None:
        return None, None, [], "No explicit configured warehouse route polylines are present."
    if not isinstance(raw, list) or not raw:
        return None, None, [], "Configured routes must be a non-empty list of explicit route definitions."

    by_id: dict[str, float] = {}
    by_flow: defaultdict[str, float] = defaultdict(float)
    definitions: list[dict] = []
    seen_ids: set[str] = set()

    for route in raw:
        if not isinstance(route, dict):
            return None, None, [], "Every configured route must be an explicit route object."
        route_id = route.get("id")
        kind = route.get("kind")
        from_role = route.get("from_role")
        to_role = route.get("to_role")
        if (not isinstance(route_id, str) or not route_id.strip() or len(route_id) > 80
                or not isinstance(kind, str) or not kind.strip() or len(kind) > 80
                or not isinstance(from_role, str) or not from_role.strip() or len(from_role) > 80
                or not isinstance(to_role, str) or not to_role.strip() or len(to_role) > 80):
            return None, None, [], "Configured routes need bounded id, kind, from_role and to_role strings."
        route_id = route_id.strip()
        if route_id in seen_ids:
            return None, None, [], "Configured route ids must be unique."
        seen_ids.add(route_id)
        kind = kind.strip().lower()
        from_role = from_role.strip().lower()
        to_role = to_role.strip().lower()

        points = route.get("points")
        if not isinstance(points, list) or len(points) < 2:
            return None, None, [], "Each configured route needs at least two explicit polyline points."
        normalized: list[tuple[float, float]] = []
        for point in points:
            if (not isinstance(point, (list, tuple)) or len(point) != 2
                    or not _finite(point[0]) or not _finite(point[1])):
                return None, None, [], "Configured route points must be finite [x, z] coordinate pairs."
            normalized.append((float(point[0]), float(point[1])))

        length = 0.0
        for index in range(1, len(normalized)):
            ax, az = normalized[index - 1]
            bx, bz = normalized[index]
            length += math.hypot(bx - ax, bz - az)
        if not math.isfinite(length):
            return None, None, [], "Configured route polyline length is not finite."
        length = round(length, 6)
        by_id[route_id] = length
        by_flow[f"{from_role}->{to_role}"] += length
        definitions.append({
            "id": route_id,
            "kind": kind,
            "from_role": from_role,
            "to_role": to_role,
            "point_count": len(normalized),
            "measurement_basis": "explicit_polyline",
        })

    return (dict(sorted(by_id.items())),
            {key: round(value, 6) for key, value in sorted(by_flow.items())},
            definitions, None)


def measure_plan(model: dict) -> dict:
    """Measure a canonical plan without inventing missing engineering facts.

    Returned values are descriptive measurements only. In particular:
    - `space_rect_area_m2` is not GFA/NFA.
    - `space_area_by_role_m2` is the sum of explicit room rectangles grouped by
      their declared canonical role. It is descriptive area allocation, not a
      minimum-area, code-compliance, usability, daylight, or adjacency score.
    - `zone_area_ratio_by_role` is each declared warehouse role area divided by
      complete measured canonical room-rectangle area. Unclassified area remains
      in the denominator. It is not utilization, efficiency or an AI quality score.
    - `dock_count_by_zone_role` groups explicit dock counts by the canonical role
      of their owning warehouse zone. It is allocation only, not capacity or throughput.
    - `lane_area_by_kind_m2` is painted/declared lane rectangle area, not a
      clearance or safety-compliance result.
    - `lane_centerline_length_by_kind_m` measures only the longitudinal dimension
      of explicit lane rectangles whose `dir` is known. It is not routed travel.
    - `lane_overlap_area_by_kind_pair_m2` is the sum of pairwise rectangle
      intersections between distinct explicit lane kinds inside the same room.
      It is a geometric conflict indicator only, not a safety/compliance result.
    - `rack_declared_footprint_area_m2` sums explicit rack-group rectangles; it is
      not storage capacity, pallet positions, or proof of usable clearances.
    - `rack_geometric_bay_count` and `rack_geometric_bay_level_positions` count
      only explicit run/bay/row/level geometry; they are not usable/load-rated
      storage capacity or proof of clearances/load units.
    - `configured_route_length_by_id_m` and `configured_route_length_by_flow_m`
      measure only explicit configured polylines and their named role endpoints;
      they do not choose, infer, optimize or weight a movement route.
    - `rack_overlap_area_m2` and `rack_lane_overlap_area_by_lane_kind_m2` measure
      only explicit room-relative rectangle intersections. They are geometric
      conflict indicators, not clearance, traffic-safety or code-compliance proof.
    - `expansion_reserve_*` metrics use only rooms explicitly assigned canonical
      role `expansion` and explicit zone/rack/lane rectangles. They do not predict
      future demand, certify a reserve as sufficient, or infer clearance/safety.
    - `rack_group_count` counts declared rack groups, not pallet positions.
    - usable storage capacity and throughput stay unavailable unless a future
      canonical contract defines sufficient source data and calculation semantics.
    """
    if not isinstance(model, dict):
        raise TypeError("model must be a dict")

    typology = _typology(model)
    floors = model.get("floors") if isinstance(model.get("floors"), dict) else {}
    templates, warnings = _level_templates(model)

    site = model.get("site") if isinstance(model.get("site"), dict) else {}
    sw, sd = site.get("w"), site.get("d")
    site_area = sw * sd if _positive(sw) and _positive(sd) else None
    if site_area is not None and not math.isfinite(site_area):
        site_area = None
    if site_area is None:
        warnings.append("SITE_AREA_NOT_MEASURABLE")

    space_area = 0.0
    space_area_known = bool(templates)
    space_count_known = bool(templates)
    zone_area: defaultdict[str, float] = defaultdict(float)
    unclassified_zone_area = 0.0
    space_count_by_role: defaultdict[str, int] = defaultdict(int)
    unclassified_space_count = 0

    dock_count = 0
    dock_count_known = bool(templates)
    dock_by_edge: defaultdict[str, int] = defaultdict(int)
    dock_by_zone_role: defaultdict[str, int] = defaultdict(int)
    dock_zone_role_complete = bool(templates)
    rack_groups = 0
    rack_groups_known = bool(templates)
    rack_declared_levels = 0
    rack_levels_complete = bool(templates)
    rack_geometric_bays = 0
    rack_geometric_bay_levels = 0
    rack_geometric_complete = bool(templates)
    rack_footprint_area = 0.0
    rack_footprint_complete = bool(templates)
    rack_overlap_area = 0.0
    rack_overlap_complete = bool(templates)
    rack_lane_overlap: defaultdict[str, float] = defaultdict(float)
    rack_lane_overlap_complete = bool(templates)
    station_count = 0
    station_count_known = bool(templates)
    lane_area: defaultdict[str, float] = defaultdict(float)
    lane_area_complete = bool(templates)
    lane_centerline: defaultdict[str, float] = defaultdict(float)
    lane_centerline_complete = bool(templates)
    lane_overlap: defaultdict[str, float] = defaultdict(float)
    lane_overlap_complete = bool(templates)

    expansion_reserve_declared = False
    expansion_reserve_geometry_complete = bool(templates)
    expansion_zone_overlap_complete = bool(templates)
    expansion_rack_overlap_complete = bool(templates)
    expansion_lane_overlap_complete = bool(templates)
    expansion_reserve_area = 0.0
    expansion_zone_overlap = 0.0
    expansion_rack_overlap = 0.0
    expansion_lane_overlap: defaultdict[str, float] = defaultdict(float)
    expansion_intrusions: list[dict] = []

    for template in templates:
        floor = floors.get(template)
        rooms = floor.get("rooms") if isinstance(floor, dict) else None
        if not isinstance(rooms, list):
            warnings.append("ROOMS_NOT_MEASURABLE")
            space_area_known = False
            space_count_known = False
            dock_count_known = rack_groups_known = station_count_known = False
            dock_zone_role_complete = False
            rack_levels_complete = rack_geometric_complete = rack_footprint_complete = False
            rack_overlap_complete = rack_lane_overlap_complete = False
            lane_area_complete = lane_centerline_complete = lane_overlap_complete = False
            expansion_reserve_geometry_complete = False
            expansion_zone_overlap_complete = False
            expansion_rack_overlap_complete = False
            expansion_lane_overlap_complete = False
            continue

        reserve_rects: list[tuple[str | None, tuple[float, float, float, float]]] = []
        for reserve_room in rooms:
            if not isinstance(reserve_room, dict):
                expansion_reserve_geometry_complete = False
                expansion_zone_overlap_complete = False
                continue
            role = reserve_room.get("role")
            normalized_role = role.strip().lower() if isinstance(role, str) and role.strip() else None
            if normalized_role != "expansion":
                continue
            expansion_reserve_declared = True
            reserve_rect = _rect_tuple(reserve_room.get("rect"))
            if reserve_rect is None:
                expansion_reserve_geometry_complete = False
                expansion_zone_overlap_complete = False
                continue
            reserve_rects.append((_element_id(reserve_room), reserve_rect))
            expansion_reserve_area += reserve_rect[2] * reserve_rect[3]

        if reserve_rects:
            for reserve_id, reserve_rect in reserve_rects:
                for other_room in rooms:
                    if not isinstance(other_room, dict):
                        expansion_zone_overlap_complete = False
                        continue
                    role = other_room.get("role")
                    normalized_role = role.strip().lower() if isinstance(role, str) and role.strip() else None
                    if normalized_role == "expansion":
                        continue
                    other_rect = _rect_tuple(other_room.get("rect"))
                    if other_rect is None:
                        expansion_zone_overlap_complete = False
                        continue
                    overlap = _rect_overlap_area(reserve_rect, other_rect)
                    if overlap > EPS:
                        expansion_zone_overlap += overlap
                        expansion_intrusions.append({
                            "reserve_room_id": reserve_id,
                            "element_kind": "zone",
                            "element_id": _element_id(other_room),
                            "overlap_area_m2": round(overlap, 6),
                        })

        for room in rooms:
            if not isinstance(room, dict):
                warnings.append("ROOM_NOT_MEASURABLE")
                space_area_known = False
                space_count_known = False
                dock_zone_role_complete = False
                rack_geometric_complete = rack_footprint_complete = False
                rack_overlap_complete = rack_lane_overlap_complete = False
                lane_centerline_complete = lane_overlap_complete = False
                if reserve_rects:
                    expansion_rack_overlap_complete = False
                    expansion_lane_overlap_complete = False
                continue
            role = room.get("role")
            normalized_role = role.strip().lower() if isinstance(role, str) and role.strip() else None
            if normalized_role:
                space_count_by_role[normalized_role] += 1
            else:
                unclassified_space_count += 1
            area = _rect_area(room.get("rect"))
            if area is None:
                warnings.append("SPACE_AREA_NOT_MEASURABLE")
                space_area_known = False
            else:
                space_area += area
                if normalized_role:
                    zone_area[normalized_role] += area
                else:
                    unclassified_zone_area += area

            raw_docks = room.get("docks")
            docks = [] if raw_docks is None else raw_docks
            if not isinstance(docks, list):
                dock_count_known = False
                dock_zone_role_complete = False
            else:
                for dock in docks:
                    if not isinstance(dock, dict):
                        dock_count_known = False
                        dock_zone_role_complete = False
                        continue
                    count = _count(dock.get("count"))
                    edge = str(dock.get("edge") or "").upper()
                    if count is None:
                        dock_count_known = False
                        dock_zone_role_complete = False
                        continue
                    dock_count += count
                    if normalized_role:
                        dock_by_zone_role[normalized_role] += count
                    elif count:
                        dock_zone_role_complete = False
                        warnings.append("DOCK_ZONE_ROLE_NOT_CLASSIFIED")
                    if edge in {"N", "S", "E", "W"}:
                        dock_by_edge[edge] += count
                    elif count:
                        warnings.append("DOCK_EDGE_NOT_CLASSIFIED")

            racks = room.get("racks") or []
            normalized_racks: list[tuple[float, float, float, float]] = []
            room_racks_complete = True
            if not isinstance(racks, list):
                rack_groups_known = False
                rack_levels_complete = False
                rack_geometric_complete = False
                rack_footprint_complete = False
                rack_overlap_complete = rack_lane_overlap_complete = False
                room_racks_complete = False
                if reserve_rects:
                    expansion_rack_overlap_complete = False
            else:
                for rack in racks:
                    if not isinstance(rack, dict):
                        rack_groups_known = False
                        rack_levels_complete = False
                        rack_geometric_complete = False
                        rack_footprint_complete = False
                        rack_overlap_complete = rack_lane_overlap_complete = False
                        room_racks_complete = False
                        if reserve_rects:
                            expansion_rack_overlap_complete = False
                        continue
                    rack_groups += 1
                    levels = rack.get("levels")
                    if type(levels) is int and levels > 0:
                        rack_declared_levels += levels
                    else:
                        rack_levels_complete = False
                    geometric_counts = _rack_geometric_counts(rack)
                    if geometric_counts is None:
                        rack_geometric_complete = False
                    else:
                        bays, bay_levels = geometric_counts
                        rack_geometric_bays += bays
                        rack_geometric_bay_levels += bay_levels
                    rack_area = _rack_footprint_area(rack)
                    if rack_area is None:
                        rack_footprint_complete = False
                    else:
                        rack_footprint_area += rack_area
                    rack_rect = _rack_rect(rack)
                    if rack_rect is None:
                        rack_overlap_complete = rack_lane_overlap_complete = False
                        room_racks_complete = False
                        if reserve_rects:
                            expansion_rack_overlap_complete = False
                    else:
                        normalized_racks.append(rack_rect)
                        for reserve_id, reserve_rect in reserve_rects:
                            overlap = _rect_overlap_area(rack_rect, reserve_rect)
                            if overlap > EPS:
                                expansion_rack_overlap += overlap
                                expansion_intrusions.append({
                                    "reserve_room_id": reserve_id,
                                    "element_kind": "rack",
                                    "element_id": _element_id(rack),
                                    "overlap_area_m2": round(overlap, 6),
                                })
                if room_racks_complete:
                    for i in range(len(normalized_racks)):
                        for j in range(i + 1, len(normalized_racks)):
                            rack_overlap_area += _rect_overlap_area(
                                normalized_racks[i], normalized_racks[j])

            stations = room.get("stations") or []
            if not isinstance(stations, list):
                station_count_known = False
            else:
                for station in stations:
                    if not isinstance(station, dict):
                        station_count_known = False
                        continue
                    count = _count(station.get("count"))
                    if count is None:
                        station_count_known = False
                    else:
                        station_count += count

            lanes = room.get("lanes") or []
            normalized_lanes: list[tuple[str, tuple[float, float, float, float]]] = []
            room_lanes_complete = True
            if not isinstance(lanes, list):
                lane_area_complete = False
                lane_centerline_complete = False
                lane_overlap_complete = False
                rack_lane_overlap_complete = False
                room_lanes_complete = False
                if reserve_rects:
                    expansion_lane_overlap_complete = False
            else:
                for lane in lanes:
                    area = _lane_area(lane)
                    length = _lane_centerline_length(lane)
                    kind = (str(lane.get("kind") or "").strip().lower()
                            if isinstance(lane, dict) else "")
                    rect = _lane_rect(lane)
                    if area is None:
                        lane_area_complete = False
                    else:
                        lane_area[kind or "unknown"] += area
                    if length is None or not kind:
                        lane_centerline_complete = False
                    else:
                        lane_centerline[kind] += length
                    if not kind or rect is None:
                        lane_overlap_complete = False
                        rack_lane_overlap_complete = False
                        room_lanes_complete = False
                        if reserve_rects:
                            expansion_lane_overlap_complete = False
                    else:
                        normalized_lanes.append((kind, rect))
                        for reserve_id, reserve_rect in reserve_rects:
                            overlap = _rect_overlap_area(rect, reserve_rect)
                            if overlap > EPS:
                                expansion_lane_overlap[kind] += overlap
                                expansion_intrusions.append({
                                    "reserve_room_id": reserve_id,
                                    "element_kind": f"lane:{kind}",
                                    "element_id": _element_id(lane),
                                    "overlap_area_m2": round(overlap, 6),
                                })
                if room_lanes_complete:
                    for i in range(len(normalized_lanes)):
                        kind_a, rect_a = normalized_lanes[i]
                        for j in range(i + 1, len(normalized_lanes)):
                            kind_b, rect_b = normalized_lanes[j]
                            if kind_a == kind_b:
                                continue
                            overlap = _rect_overlap_area(rect_a, rect_b)
                            if overlap > EPS:
                                key = "|".join(sorted((kind_a, kind_b)))
                                lane_overlap[key] += overlap
                if room_lanes_complete and room_racks_complete:
                    for rack_rect in normalized_racks:
                        for lane_kind, lane_rect in normalized_lanes:
                            overlap = _rect_overlap_area(rack_rect, lane_rect)
                            if overlap > EPS:
                                rack_lane_overlap[lane_kind] += overlap

    metrics: dict[str, Any] = {
        "site_area_m2": round(site_area, 6) if site_area is not None else None,
        "level_count": len(templates) if templates else None,
        "space_rect_area_m2": round(space_area, 6) if space_area_known else None,
        "space_area_by_role_m2": (
            {k: round(v, 6) for k, v in sorted(zone_area.items())}
            if space_area_known else None),
        "unclassified_space_area_m2": (
            round(unclassified_zone_area, 6) if space_area_known else None),
        "space_count_by_role": (
            dict(sorted(space_count_by_role.items())) if space_count_known else None),
        "unclassified_space_count": unclassified_space_count if space_count_known else None,
        "gross_floor_area_m2": None,
        "net_floor_area_m2": None,
        "efficiency": None,
    }

    unavailable = {
        "gross_floor_area_m2": "No canonical gross-envelope calculation is defined here.",
        "net_floor_area_m2": "No canonical net-area classification is defined here.",
        "efficiency": "GFA/NFA are not established, so efficiency is not computed.",
    }
    configured_route_definitions: list[dict] = []
    checks: dict[str, dict] = {}

    if typology == "warehouse":
        zone_ratios = (
            {k: round(v / space_area, 6) for k, v in sorted(zone_area.items())}
            if space_area_known and space_area > EPS else None
        )
        route_by_id, route_by_flow, configured_route_definitions, route_error = (
            _measure_configured_routes(model))

        if not expansion_reserve_declared:
            expansion_area_metric: float | None = 0.0
            expansion_zone_metric: float | None = 0.0
            expansion_rack_metric: float | None = 0.0
            expansion_lane_metric: dict[str, float] | None = {}
            expansion_status = "NOT_APPLICABLE"
        else:
            expansion_area_metric = (round(expansion_reserve_area, 6)
                                     if expansion_reserve_geometry_complete else None)
            expansion_zone_metric = (round(expansion_zone_overlap, 6)
                                     if expansion_zone_overlap_complete else None)
            expansion_rack_metric = (round(expansion_rack_overlap, 6)
                                     if expansion_rack_overlap_complete else None)
            expansion_lane_metric = (
                {k: round(v, 6) for k, v in sorted(expansion_lane_overlap.items())}
                if expansion_lane_overlap_complete else None)
            if not (expansion_reserve_geometry_complete and expansion_zone_overlap_complete
                    and expansion_rack_overlap_complete and expansion_lane_overlap_complete):
                expansion_status = "NOT_VERIFIED"
            elif (expansion_zone_overlap > EPS or expansion_rack_overlap > EPS
                  or any(v > EPS for v in expansion_lane_overlap.values())):
                expansion_status = "FAIL"
            else:
                expansion_status = "PASS"

        metrics.update({
            "zone_area_by_role_m2": metrics["space_area_by_role_m2"],
            "zone_area_ratio_by_role": zone_ratios,
            "unclassified_zone_area_m2": metrics["unclassified_space_area_m2"],
            "dock_count": dock_count if dock_count_known else None,
            "dock_count_by_edge": dict(sorted(dock_by_edge.items())) if dock_count_known else None,
            "dock_count_by_zone_role": (
                dict(sorted(dock_by_zone_role.items()))
                if dock_count_known and dock_zone_role_complete else None),
            "rack_group_count": rack_groups if rack_groups_known else None,
            "rack_declared_level_sum": rack_declared_levels if rack_levels_complete else None,
            "rack_geometric_bay_count": (
                rack_geometric_bays if rack_geometric_complete else None),
            "rack_geometric_bay_level_positions": (
                rack_geometric_bay_levels if rack_geometric_complete else None),
            "rack_declared_footprint_area_m2": (
                round(rack_footprint_area, 6) if rack_footprint_complete else None),
            "rack_overlap_area_m2": (
                round(rack_overlap_area, 6) if rack_overlap_complete else None),
            "rack_lane_overlap_area_by_lane_kind_m2": (
                {k: round(v, 6) for k, v in sorted(rack_lane_overlap.items())}
                if rack_lane_overlap_complete else None),
            "station_count": station_count if station_count_known else None,
            "lane_area_by_kind_m2": ({k: round(v, 6) for k, v in sorted(lane_area.items())}
                                     if lane_area_complete else None),
            "lane_centerline_length_by_kind_m": (
                {k: round(v, 6) for k, v in sorted(lane_centerline.items())}
                if lane_centerline_complete else None),
            "lane_overlap_area_by_kind_pair_m2": (
                {k: round(v, 6) for k, v in sorted(lane_overlap.items())}
                if lane_overlap_complete else None),
            "configured_route_length_by_id_m": route_by_id,
            "configured_route_length_by_flow_m": route_by_flow,
            "expansion_reserve_area_m2": expansion_area_metric,
            "expansion_reserve_zone_overlap_area_m2": expansion_zone_metric,
            "expansion_reserve_rack_overlap_area_m2": expansion_rack_metric,
            "expansion_reserve_lane_overlap_area_by_kind_m2": expansion_lane_metric,
            "storage_capacity_positions": None,
            "throughput_per_hour": None,
            "travel_distance_m": None,
            "pedestrian_vehicle_separation_compliance": None,
            "fire_life_safety_compliance": None,
        })
        checks["expansion_reserve_preservation"] = {
            "status": expansion_status,
            "measurement_basis": "explicit_rectangles",
            "canonical_role": "expansion",
            "intrusions": sorted(
                expansion_intrusions,
                key=lambda row: (str(row.get("reserve_room_id")),
                                 str(row.get("element_kind")),
                                 str(row.get("element_id")),
                                 row.get("overlap_area_m2", 0.0))),
            "claims_reserve_sufficiency": False,
            "claims_regulatory_compliance": False,
            "claims_safety_compliance": False,
        }
        unavailable.update({
            "storage_capacity_positions": (
                "Geometric rack bay/level counts are not usable or load-rated storage capacity; "
                "no canonical load-unit, clearance, occupancy or load-rating contract is present."),
            "throughput_per_hour": "No measured flow/time model is present in canonical Building JSON.",
            "travel_distance_m": (
                "No single selected/weighted movement model is defined; explicit configured route "
                "polylines are reported separately and are not collapsed into one travel distance."),
            "pedestrian_vehicle_separation_compliance": "Lane overlap measurements alone cannot prove safety compliance.",
            "fire_life_safety_compliance": "No authoritative jurisdiction/rule evaluation is performed here.",
        })
        if expansion_reserve_declared and not expansion_reserve_geometry_complete:
            unavailable["expansion_reserve_area_m2"] = (
                "Expansion reserve area needs finite positive rectangles for every canonical room "
                "whose role is exactly 'expansion'.")
        if expansion_reserve_declared and not expansion_zone_overlap_complete:
            unavailable["expansion_reserve_zone_overlap_area_m2"] = (
                "Expansion reserve zone-overlap measurement needs explicit finite room rectangles.")
        if expansion_reserve_declared and not expansion_rack_overlap_complete:
            unavailable["expansion_reserve_rack_overlap_area_m2"] = (
                "Expansion reserve rack-overlap measurement needs explicit rack x/z/w/d geometry.")
        if expansion_reserve_declared and not expansion_lane_overlap_complete:
            unavailable["expansion_reserve_lane_overlap_area_by_kind_m2"] = (
                "Expansion reserve lane-overlap measurement needs explicit lane kind/x/z/w/d geometry.")
        if route_error is not None:
            unavailable["configured_route_length_by_id_m"] = route_error
            unavailable["configured_route_length_by_flow_m"] = route_error
        if not dock_count_known or not dock_zone_role_complete:
            unavailable["dock_count_by_zone_role"] = (
                "Dock allocation by owning zone role needs valid explicit counts and a canonical "
                "owning zone role for every non-zero dock count.")
        if zone_ratios is None:
            unavailable["zone_area_ratio_by_role"] = (
                "Zone allocation ratios need complete positive measured canonical room-rectangle area.")
        if not rack_geometric_complete:
            message = (
                "Geometric rack bay counts need explicit positive w/d/bay geometry, x/z run "
                "direction, integer rows and integer levels for every declared rack group.")
            unavailable["rack_geometric_bay_count"] = message
            unavailable["rack_geometric_bay_level_positions"] = message
        if not rack_overlap_complete:
            unavailable["rack_overlap_area_m2"] = (
                "Rack overlap needs explicit room-relative x/z/w/d geometry for every rack group.")
        if not rack_lane_overlap_complete:
            unavailable["rack_lane_overlap_area_by_lane_kind_m2"] = (
                "Rack/lane overlap needs explicit room-relative rack geometry and lane kind/x/z/w/d geometry.")

    # Deduplicate disclosure codes while keeping deterministic order.
    warnings = sorted(set(warnings))
    return {
        "schema": SCHEMA,
        "typology": typology,
        "metrics": metrics,
        "checks": checks,
        "configured_route_definitions": configured_route_definitions,
        "unavailable": unavailable,
        "warnings": warnings,
        "claims_regulatory_compliance": False,
        "claims_structural_safety": False,
    }
