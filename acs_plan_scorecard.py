"""Deterministic, non-regulatory scorecard for ACS plan-first canonical models.

This module only measures geometry and explicit operational data already present in
canonical Building JSON. It does not infer code compliance, required clearances,
storage capacity, throughput, safety, or daylight. Missing inputs remain unknown.
No provider, network, CAD, compiler, or production route is imported here.
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


def _rect_area(rect: Any) -> float | None:
    if (not isinstance(rect, list) or len(rect) != 4
            or not all(_finite(v) for v in rect)
            or rect[2] <= 0 or rect[3] <= 0):
        return None
    area = rect[2] * rect[3]
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


def _rect_overlap_area(a: tuple[float, float, float, float],
                       b: tuple[float, float, float, float]) -> float:
    ax, az, aw, ad = a
    bx, bz, bw, bd = b
    w = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    d = max(0.0, min(az + ad, bz + bd) - max(az, bz))
    return w * d


def measure_plan(model: dict) -> dict:
    """Measure a canonical plan without inventing missing engineering facts.

    Returned values are descriptive measurements only. In particular:
    - `space_rect_area_m2` is not GFA/NFA.
    - `space_area_by_role_m2` is the sum of explicit room rectangles grouped by
      their declared canonical role. It is descriptive area allocation, not a
      minimum-area, code-compliance, usability, daylight, or adjacency score.
    - `lane_area_by_kind_m2` is painted/declared lane rectangle area, not a
      clearance or safety-compliance result.
    - `lane_centerline_length_by_kind_m` measures only the longitudinal dimension
      of explicit lane rectangles whose `dir` is known. It is not routed travel.
    - `lane_overlap_area_by_kind_pair_m2` is the sum of pairwise rectangle
      intersections between distinct explicit lane kinds inside the same room.
      It is a geometric conflict indicator only, not a safety/compliance result.
    - `rack_declared_footprint_area_m2` sums explicit rack-group rectangles; it is
      not storage capacity, pallet positions, or proof of usable clearances.
    - `rack_group_count` counts declared rack groups, not pallet positions.
    - storage capacity and throughput stay unavailable unless a future canonical
      contract defines sufficient source data and its calculation semantics.
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
    rack_groups = 0
    rack_groups_known = bool(templates)
    rack_declared_levels = 0
    rack_levels_complete = bool(templates)
    rack_footprint_area = 0.0
    rack_footprint_complete = bool(templates)
    station_count = 0
    station_count_known = bool(templates)
    lane_area: defaultdict[str, float] = defaultdict(float)
    lane_area_complete = bool(templates)
    lane_centerline: defaultdict[str, float] = defaultdict(float)
    lane_centerline_complete = bool(templates)
    lane_overlap: defaultdict[str, float] = defaultdict(float)
    lane_overlap_complete = bool(templates)

    for template in templates:
        floor = floors.get(template)
        rooms = floor.get("rooms") if isinstance(floor, dict) else None
        if not isinstance(rooms, list):
            warnings.append("ROOMS_NOT_MEASURABLE")
            space_area_known = False
            space_count_known = False
            dock_count_known = rack_groups_known = station_count_known = False
            rack_levels_complete = rack_footprint_complete = False
            lane_area_complete = lane_centerline_complete = lane_overlap_complete = False
            continue
        for room in rooms:
            if not isinstance(room, dict):
                warnings.append("ROOM_NOT_MEASURABLE")
                space_area_known = False
                space_count_known = False
                rack_footprint_complete = False
                lane_centerline_complete = lane_overlap_complete = False
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

            docks = room.get("docks") or []
            if not isinstance(docks, list):
                dock_count_known = False
            else:
                for dock in docks:
                    if not isinstance(dock, dict):
                        dock_count_known = False
                        continue
                    count = _count(dock.get("count"))
                    edge = str(dock.get("edge") or "").upper()
                    if count is None:
                        dock_count_known = False
                        continue
                    dock_count += count
                    if edge in {"N", "S", "E", "W"}:
                        dock_by_edge[edge] += count
                    elif count:
                        warnings.append("DOCK_EDGE_NOT_CLASSIFIED")

            racks = room.get("racks") or []
            if not isinstance(racks, list):
                rack_groups_known = False
                rack_levels_complete = False
                rack_footprint_complete = False
            else:
                for rack in racks:
                    if not isinstance(rack, dict):
                        rack_groups_known = False
                        rack_levels_complete = False
                        rack_footprint_complete = False
                        continue
                    rack_groups += 1
                    levels = rack.get("levels")
                    if type(levels) is int and levels > 0:
                        rack_declared_levels += levels
                    else:
                        rack_levels_complete = False
                    rack_area = _rack_footprint_area(rack)
                    if rack_area is None:
                        rack_footprint_complete = False
                    else:
                        rack_footprint_area += rack_area

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
            if not isinstance(lanes, list):
                lane_area_complete = False
                lane_centerline_complete = False
                lane_overlap_complete = False
            else:
                normalized_lanes: list[tuple[str, tuple[float, float, float, float]]] = []
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
                    else:
                        normalized_lanes.append((kind, rect))
                if lane_overlap_complete:
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

    if typology == "warehouse":
        metrics.update({
            "zone_area_by_role_m2": metrics["space_area_by_role_m2"],
            "unclassified_zone_area_m2": metrics["unclassified_space_area_m2"],
            "dock_count": dock_count if dock_count_known else None,
            "dock_count_by_edge": dict(sorted(dock_by_edge.items())) if dock_count_known else None,
            "rack_group_count": rack_groups if rack_groups_known else None,
            "rack_declared_level_sum": rack_declared_levels if rack_levels_complete else None,
            "rack_declared_footprint_area_m2": (
                round(rack_footprint_area, 6) if rack_footprint_complete else None),
            "station_count": station_count if station_count_known else None,
            "lane_area_by_kind_m2": ({k: round(v, 6) for k, v in sorted(lane_area.items())}
                                     if lane_area_complete else None),
            "lane_centerline_length_by_kind_m": (
                {k: round(v, 6) for k, v in sorted(lane_centerline.items())}
                if lane_centerline_complete else None),
            "lane_overlap_area_by_kind_pair_m2": (
                {k: round(v, 6) for k, v in sorted(lane_overlap.items())}
                if lane_overlap_complete else None),
            "storage_capacity_positions": None,
            "throughput_per_hour": None,
            "travel_distance_m": None,
            "pedestrian_vehicle_separation_compliance": None,
            "fire_life_safety_compliance": None,
        })
        unavailable.update({
            "storage_capacity_positions": "Rack group geometry does not define a canonical slot/capacity contract.",
            "throughput_per_hour": "No measured flow/time model is present in canonical Building JSON.",
            "travel_distance_m": "Declared lane centerlines are not routed origin/destination travel paths.",
            "pedestrian_vehicle_separation_compliance": "Lane overlap measurements alone cannot prove safety compliance.",
            "fire_life_safety_compliance": "No authoritative jurisdiction/rule evaluation is performed here.",
        })

    # Deduplicate disclosure codes while keeping deterministic order.
    warnings = sorted(set(warnings))
    return {
        "schema": SCHEMA,
        "typology": typology,
        "metrics": metrics,
        "unavailable": unavailable,
        "warnings": warnings,
        "claims_regulatory_compliance": False,
        "claims_structural_safety": False,
    }
