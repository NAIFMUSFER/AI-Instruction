#!/usr/bin/env python3
"""One-time bounded source transformation for PR #63.

Applies only the proven dock-allocation measurement gap. Every replacement is
asserted exactly once so drift fails closed instead of editing an unintended block.
"""
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


score_path = Path("acs_plan_scorecard.py")
score = score_path.read_text()

score = replace_once(
    score,
    '    - `zone_area_ratio_by_role` is each declared warehouse role area divided by\n'
    '      complete measured canonical room-rectangle area. Unclassified area remains\n'
    '      in the denominator. It is not utilization, efficiency or an AI quality score.\n',
    '    - `zone_area_ratio_by_role` is each declared warehouse role area divided by\n'
    '      complete measured canonical room-rectangle area. Unclassified area remains\n'
    '      in the denominator. It is not utilization, efficiency or an AI quality score.\n'
    '    - `dock_count_by_zone_role` groups explicit dock counts by the canonical role\n'
    '      of their owning warehouse zone. It is allocation only, not capacity or throughput.\n',
    "scorecard disclosure",
)

score = replace_once(
    score,
    '    dock_count = 0\n'
    '    dock_count_known = bool(templates)\n'
    '    dock_by_edge: defaultdict[str, int] = defaultdict(int)\n',
    '    dock_count = 0\n'
    '    dock_count_known = bool(templates)\n'
    '    dock_by_edge: defaultdict[str, int] = defaultdict(int)\n'
    '    dock_by_zone_role: defaultdict[str, int] = defaultdict(int)\n'
    '    dock_zone_role_complete = bool(templates)\n',
    "dock accumulator",
)

score = replace_once(
    score,
    '            dock_count_known = rack_groups_known = station_count_known = False\n'
    '            rack_levels_complete = rack_footprint_complete = False\n',
    '            dock_count_known = rack_groups_known = station_count_known = False\n'
    '            dock_zone_role_complete = False\n'
    '            rack_levels_complete = rack_footprint_complete = False\n',
    "invalid rooms completeness",
)

score = replace_once(
    score,
    '                space_area_known = False\n'
    '                space_count_known = False\n'
    '                rack_footprint_complete = False\n',
    '                space_area_known = False\n'
    '                space_count_known = False\n'
    '                dock_zone_role_complete = False\n'
    '                rack_footprint_complete = False\n',
    "invalid room completeness",
)

score = replace_once(
    score,
    '            docks = room.get("docks") or []\n'
    '            if not isinstance(docks, list):\n'
    '                dock_count_known = False\n'
    '            else:\n'
    '                for dock in docks:\n'
    '                    if not isinstance(dock, dict):\n'
    '                        dock_count_known = False\n'
    '                        continue\n'
    '                    count = _count(dock.get("count"))\n'
    '                    edge = str(dock.get("edge") or "").upper()\n'
    '                    if count is None:\n'
    '                        dock_count_known = False\n'
    '                        continue\n'
    '                    dock_count += count\n'
    '                    if edge in {"N", "S", "E", "W"}:\n'
    '                        dock_by_edge[edge] += count\n'
    '                    elif count:\n'
    '                        warnings.append("DOCK_EDGE_NOT_CLASSIFIED")\n',
    '            docks = room.get("docks") or []\n'
    '            if not isinstance(docks, list):\n'
    '                dock_count_known = False\n'
    '                dock_zone_role_complete = False\n'
    '            else:\n'
    '                for dock in docks:\n'
    '                    if not isinstance(dock, dict):\n'
    '                        dock_count_known = False\n'
    '                        dock_zone_role_complete = False\n'
    '                        continue\n'
    '                    count = _count(dock.get("count"))\n'
    '                    edge = str(dock.get("edge") or "").upper()\n'
    '                    if count is None:\n'
    '                        dock_count_known = False\n'
    '                        dock_zone_role_complete = False\n'
    '                        continue\n'
    '                    dock_count += count\n'
    '                    if normalized_role:\n'
    '                        dock_by_zone_role[normalized_role] += count\n'
    '                    elif count:\n'
    '                        dock_zone_role_complete = False\n'
    '                        warnings.append("DOCK_ZONE_ROLE_NOT_CLASSIFIED")\n'
    '                    if edge in {"N", "S", "E", "W"}:\n'
    '                        dock_by_edge[edge] += count\n'
    '                    elif count:\n'
    '                        warnings.append("DOCK_EDGE_NOT_CLASSIFIED")\n',
    "dock measurement",
)

score = replace_once(
    score,
    '            "dock_count": dock_count if dock_count_known else None,\n'
    '            "dock_count_by_edge": dict(sorted(dock_by_edge.items())) if dock_count_known else None,\n',
    '            "dock_count": dock_count if dock_count_known else None,\n'
    '            "dock_count_by_edge": dict(sorted(dock_by_edge.items())) if dock_count_known else None,\n'
    '            "dock_count_by_zone_role": (\n'
    '                dict(sorted(dock_by_zone_role.items()))\n'
    '                if dock_count_known and dock_zone_role_complete else None),\n',
    "dock metrics publication",
)

score = replace_once(
    score,
    '        if zone_ratios is None:\n'
    '            unavailable["zone_area_ratio_by_role"] = (\n'
    '                "Zone allocation ratios need complete positive measured canonical room-rectangle area.")\n',
    '        if not dock_count_known or not dock_zone_role_complete:\n'
    '            unavailable["dock_count_by_zone_role"] = (\n'
    '                "Dock allocation by owning zone role needs valid explicit counts and a canonical "\n'
    '                "owning zone role for every non-zero dock count.")\n'
    '        if zone_ratios is None:\n'
    '            unavailable["zone_area_ratio_by_role"] = (\n'
    '                "Zone allocation ratios need complete positive measured canonical room-rectangle area.")\n',
    "dock unavailable disclosure",
)

score_path.write_text(score)

options_path = Path("acs_plan_options.py")
options = options_path.read_text()
options = replace_once(
    options,
    '    "dock_count_by_edge",\n'
    '    "lane_area_by_kind_m2",\n',
    '    "dock_count_by_edge",\n'
    '    "dock_count_by_zone_role",\n'
    '    "lane_area_by_kind_m2",\n',
    "option dock allocation mapping",
)
options_path.write_text(options)
