"""Deterministic 2D drafting layer for ACS plan drawings (SVG, PDF, DXF).

The approved Canonical ACS Model stays the Source of Truth. This module only
draws facts that the canonical model already states and that the 3D compiler
already builds from: room rectangles (wall centre lines), the model wall
thickness, declared wall edges and heights, doors, windows, docks and explicit
stair objects. On top of those facts it applies drafting conventions from
:mod:`acs_drafting_standards`: wall poche cut at the plan plane, door leaves
and swings, window symbols, stair treads with travel arrows, dimension chains,
room tags with net area, a north arrow, a scale bar and a title block.

Two conventions are not stated by the canonical model and are therefore
disclosed as drafting defaults: the side a door swings to and its hinge side.
Nothing here writes to the model, calls a provider or claims construction,
regulatory or structural approval. Stdlib only so ``python -S`` export gates
keep working.

Coordinates: canonical plan metres, X east and Z south (north is -Z), exactly
as the compiler and :func:`acs_plan_projection.project` use them. Renderers
map (x, z) to paper millimetres (SVG/PDF) or to CAD (x, -z) metres (DXF).
"""
from __future__ import annotations

import hashlib
import json
import math

import acs_drafting_standards as STD
from acs_geometry_contract import parapet_spans, wall_edges
from acs_plan_review import PlanError

SCHEMA = "acs.plan-drafting/1.0"
SCOPE = "CANONICAL_WALLS_OPENINGS_STAIRS_ANNOTATION"
EDGES = ("N", "S", "E", "W")
TOL = 0.0025  # the local author rounds coincident offsets to a millimetre
INDUSTRIAL_TYPES = ("warehouse", "industrial", "factory", "logistics")
CIRCULATION_ROLES = frozenset({
    "corridor", "hall", "hallway", "lobby", "entrance", "entry", "foyer", "stairs", "stair",
    "elevator", "lift", "porch", "circulation", "passage", "landing", "vestibule",
})
PRIVATE_ROLES = frozenset({
    "bedroom", "bathroom", "wc", "toilet", "closet", "wardrobe", "dressing", "laundry",
    "storage", "store", "pantry", "maid", "driver", "ensuite",
})
ELEVATOR_ROLES = frozenset({"elevator", "lift"})
DRAFTING_DEFAULTS = ("door_swing_side", "door_hinge_side", "double_leaf_at_or_above_1.4m")
NOT_DRAWN = ("structural_grid", "columns", "MEP", "furniture", "warehouse_racks_lanes_stations")
AR_ORDINALS = ("الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر")


def _q(value: float) -> float:
    out = round(float(value), 6)
    return 0.0 if out == 0 else out


def _num(value) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def fmt_length(metres: float) -> str:
    return "%.*f" % (STD.DIMENSION["decimals"], metres + 0.0)


def fmt_area(square_metres: float) -> str:
    return "%.2f m2" % (square_metres + 0.0)


def _hash(value) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_width_mm(text: str, size_mm: float) -> float:
    """Advance estimate for DejaVu-like sans fonts; ``size_mm`` is the lettering (cap) height."""
    total = 0.0
    for ch in str(text):
        code = ord(ch)
        if ch.isdigit():
            total += 0.64
        elif ch in ".,:;|'":
            total += 0.32
        elif ch.isspace():
            total += 0.32
        elif 0x064B <= code <= 0x065F or code == 0x0670:
            continue  # Arabic combining marks take no advance
        elif 0x0600 <= code <= 0x06FF or 0xFB50 <= code <= 0xFEFF:
            total += 0.55
        elif ch.isupper():
            total += 0.68
        else:
            total += 0.58
    return total * STD.font_size_mm(size_mm)


# ---------------------------------------------------------------------------
# Canonical facts
# ---------------------------------------------------------------------------
def _edge_line(edge: str, rect) -> tuple[str, float, float, float]:
    """(axis, fixed, u0, u1): axis 'x' runs along X at Z=fixed; 'z' along Z at X=fixed."""
    x, z, w, d = rect
    return {"N": ("x", z, x, x + w), "S": ("x", z + d, x, x + w),
            "W": ("z", x, z, z + d), "E": ("z", x + w, z, z + d)}[edge]


def _opening_u(edge: str, rect, offset: float) -> float:
    """Same rule as the compiler: offset is measured from the room corner."""
    return (rect[0] if edge in ("N", "S") else rect[1]) + offset


class _Snap:
    """Snap coincident coordinates (author rounding) onto one value per axis."""

    def __init__(self):
        self.values = {"x": [], "z": []}

    def __call__(self, dim: str, value: float) -> float:
        value = _q(value)
        for known in self.values[dim]:
            if abs(known - value) <= TOL:
                return known
        self.values[dim].append(value)
        return value


def _fixed_dim(axis: str) -> str:
    return "z" if axis == "x" else "x"


def level_title_ar(level: dict, index: int) -> str:
    if level.get("kind") == "roof":
        return "مخطط السطح (غير مشغول)"
    if index == 0:
        return "مخطط الدور الأرضي"
    if 1 <= index <= len(AR_ORDINALS):
        return "مخطط الدور " + AR_ORDINALS[index - 1]
    if index < 0:
        return "مخطط القبو %d" % abs(index)
    return "مخطط الدور %d" % index


# ---------------------------------------------------------------------------
# Walls: merged runs, cell coverage and outline loops
# ---------------------------------------------------------------------------
def _wall_runs(model: dict, rooms: list, snap: _Snap) -> list[tuple]:
    industrial = str((model.get("meta") or {}).get("type", "residential")).lower() in INDUSTRIAL_TYPES
    default_h = model.get("wall_h") if _num(model.get("wall_h")) else 3.0
    runs = []
    for room in rooms:
        rect = room["rect"]
        try:
            edges = wall_edges(room, industrial)
            spans = parapet_spans(room)
        except ValueError as exc:
            raise PlanError("INVALID_GEOMETRY", "Declared room walls are malformed") from exc
        mode = room.get("walls")
        height = room.get("wall_h", default_h)
        height = height if _num(height) else default_h
        if mode == "glass":
            category = "glazed"
        elif mode in ("low", "rail"):
            category = "low"
        elif mode == "half":
            category = "cut" if 1.8 >= STD.CUT_PLANE_HEIGHT_M else "low"
        else:
            category = "cut" if height >= STD.CUT_PLANE_HEIGHT_M else "low"
        pieces = [(e,) + _edge_line(e, rect)[1:] for e in edges]
        for edge, s0, s1 in spans:
            _, fixed, u0, _ = _edge_line(edge, rect)
            pieces.append((edge, fixed, u0 + s0, u0 + s1))
        for edge, fixed, u0, u1 in pieces:
            axis = _edge_line(edge, rect)[0]
            runs.append((category, axis, snap(_fixed_dim(axis), fixed), snap(axis, u0), snap(axis, u1)))
    merged = []
    for key in sorted({(c, a, f) for c, a, f, _, _ in runs}):
        spans = sorted((u0, u1) for c, a, f, u0, u1 in runs if (c, a, f) == key and u1 - u0 > TOL)
        current = None
        for u0, u1 in spans:
            if current and u0 <= current[1] + TOL:
                current[1] = max(current[1], u1)
            else:
                if current:
                    merged.append(key + tuple(current))
                current = [u0, u1]
        if current:
            merged.append(key + tuple(current))
    return merged


def _rect_of_run(axis: str, fixed: float, u0: float, u1: float, half: float) -> tuple:
    if axis == "x":
        return (u0, fixed - half, u1, fixed + half)
    return (fixed - half, u0, fixed + half, u1)


def _extended_rects(runs: list, half: float, category: str) -> list:
    """Wall rectangles, extended by half a thickness where they meet a perpendicular wall."""
    rects = []
    for cat, axis, fixed, u0, u1 in runs:
        if cat != category:
            continue
        ends = []
        for end in (u0, u1):
            meets = any(other_axis != axis and abs(other_fixed - end) <= TOL
                        and o0 - TOL <= fixed <= o1 + TOL
                        for _, other_axis, other_fixed, o0, o1 in runs)
            ends.append(half if meets else 0.0)
        rects.append(_rect_of_run(axis, fixed, u0 - ends[0], u1 + ends[1], half))
    return rects


def _grid(add: list, sub: list):
    xs = sorted({_q(v) for r in add + sub for v in (r[0], r[2])})
    zs = sorted({_q(v) for r in add + sub for v in (r[1], r[3])})
    xi = {v: i for i, v in enumerate(xs)}
    zi = {v: i for i, v in enumerate(zs)}
    cells = set()
    for rects, keep in ((add, True), (sub, False)):
        for r in rects:
            i0, i1 = xi[_q(r[0])], xi[_q(r[2])]
            j0, j1 = zi[_q(r[1])], zi[_q(r[3])]
            for i in range(i0, i1):
                for j in range(j0, j1):
                    if keep:
                        cells.add((i, j))
                    else:
                        cells.discard((i, j))
    return xs, zs, cells


def _loops(xs, zs, cells) -> list[list[list[float]]]:
    """Closed outlines of a cell set; outer loops clockwise on paper, holes opposite."""
    out: dict = {}

    def add(a, b):
        out.setdefault(a, []).append(b)

    for i, j in sorted(cells):
        if (i, j - 1) not in cells:
            add((i, j), (i + 1, j))
        if (i + 1, j) not in cells:
            add((i + 1, j), (i + 1, j + 1))
        if (i, j + 1) not in cells:
            add((i + 1, j + 1), (i, j + 1))
        if (i - 1, j) not in cells:
            add((i, j + 1), (i, j))
    loops = []
    while out:
        start = min(out)
        loop, current, heading = [start], start, None
        while True:
            options = out[current]
            choice = options[0]
            if heading is not None and len(options) > 1:
                preference = ((-heading[1], heading[0]), heading, (heading[1], -heading[0]))
                for want in preference:
                    hit = [o for o in options if (o[0] - current[0], o[1] - current[1]) == want]
                    if hit:
                        choice = hit[0]
                        break
            options.remove(choice)
            if not options:
                del out[current]
            heading = (choice[0] - current[0], choice[1] - current[1])
            current = choice
            if current == start:
                break
            loop.append(current)
        simple = []
        count = len(loop)
        for k, point in enumerate(loop):
            before, after = loop[k - 1], loop[(k + 1) % count]
            if (point[0] - before[0], point[1] - before[1]) != (after[0] - point[0], after[1] - point[1]):
                simple.append(point)
        loops.append([[xs[i], zs[j]] for i, j in (simple or loop)])
    return loops


def _cells_area(xs, zs, cells) -> float:
    return sum((xs[i + 1] - xs[i]) * (zs[j + 1] - zs[j]) for i, j in cells)


def _cells_bounds(xs, zs, cells):
    if not cells:
        return None
    i0 = min(i for i, _ in cells)
    i1 = max(i for i, _ in cells) + 1
    j0 = min(j for _, j in cells)
    j1 = max(j for _, j in cells) + 1
    return (xs[i0], zs[j0], xs[i1], zs[j1])


def _covered(runs: list, axis: str, fixed: float, u: float) -> bool:
    return any(a == axis and abs(f - fixed) <= TOL and u0 - TOL <= u <= u1 + TOL for _, a, f, u0, u1 in runs)


def _coverage_fraction(runs: list, axis: str, fixed: float, u0: float, u1: float) -> float:
    length = u1 - u0
    if length <= TOL:
        return 0.0
    spans = sorted((max(a0, u0), min(a1, u1)) for _, a, f, a0, a1 in runs
                   if a == axis and abs(f - fixed) <= TOL and a1 > u0 and a0 < u1)
    covered, cursor = 0.0, u0
    for s0, s1 in spans:
        s0 = max(s0, cursor)
        if s1 > s0:
            covered += s1 - s0
            cursor = s1
    return covered / length


def _uncovered_spans(runs: list, openings: list, axis: str, fixed: float, u0: float, u1: float) -> list:
    """Parts of a room edge with neither a wall nor an opening on it."""
    blocks = [(a0, a1) for _, a, f, a0, a1 in runs if a == axis and abs(f - fixed) <= TOL]
    blocks += [(o["a"], o["b"]) for o in openings if o["axis"] == axis and abs(o["fixed"] - fixed) <= TOL]
    out, cursor = [], u0
    for b0, b1 in sorted(blocks):
        if b1 <= cursor:
            continue
        if b0 > cursor + TOL and b0 < u1:
            out.append((cursor, min(b0, u1)))
        cursor = max(cursor, b1)
        if cursor >= u1:
            break
    if cursor < u1 - TOL:
        out.append((cursor, u1))
    return [(a, b) for a, b in out if b - a > TOL]


# ---------------------------------------------------------------------------
# Openings
# ---------------------------------------------------------------------------
def _room_rank(room: dict, industrial: bool) -> int:
    try:
        enclosed = bool(wall_edges(room, industrial))
    except ValueError:
        enclosed = True
    if not enclosed:
        return -1  # a wall-less space (porch) is exterior for swing purposes
    role = str(room.get("role") or "").lower()
    if role in CIRCULATION_ROLES:
        return 0
    if role in PRIVATE_ROLES or "bath" in role or "wc" in role:
        return 2
    return 1


def _adjacent(rooms: list, axis: str, fixed: float, a: float, b: float) -> dict:
    """Rooms on the + side (larger z or x) and - side of a wall line around [a, b]."""
    sides = {}
    mid = (a + b) / 2
    for room in rooms:
        x, z, w, d = room["rect"]
        lo_fixed, hi_fixed, s0, s1 = (z, z + d, x, x + w) if axis == "x" else (x, x + w, z, z + d)
        if not s0 - TOL <= mid <= s1 + TOL:
            continue
        if abs(lo_fixed - fixed) <= TOL and 1 not in sides:
            sides[1] = room
        elif abs(hi_fixed - fixed) <= TOL and -1 not in sides:
            sides[-1] = room
    return sides


def _point(axis: str, u: float, v: float) -> list:
    return [_q(u), _q(v)] if axis == "x" else [_q(v), _q(u)]


def _openings(model: dict, rooms: list, runs: list, snap: _Snap, t: float, element_ids: dict, level: dict):
    industrial = str((model.get("meta") or {}).get("type", "residential")).lower() in INDUSTRIAL_TYPES
    records = {"doors": [], "windows": []}
    docks = []
    for room in rooms:
        rect = room["rect"]
        for collection in ("doors", "windows"):
            for index, item in enumerate(room.get(collection) or []):
                if (not isinstance(item, dict) or item.get("edge") not in EDGES
                        or not _num(item.get("offset")) or not _num(item.get("width")) or item["width"] <= 0):
                    continue
                axis, fixed, _, _ = _edge_line(item["edge"], rect)
                uc = _q(_opening_u(item["edge"], rect, item["offset"]))
                records[collection].append({
                    "axis": axis, "fixed": snap(_fixed_dim(axis), fixed), "uc": uc, "w": float(item["width"]),
                    "room": room, "index": index, "item": item,
                    "source_id": element_ids.get((room["id"], collection, item.get("id"))),
                })
        for dock in room.get("docks") or []:
            if not isinstance(dock, dict) or dock.get("edge") not in EDGES:
                continue
            if not all(_num(dock.get(k)) for k in ("offset", "width", "pitch")) or type(dock.get("count")) is not int:
                continue
            axis, fixed, _, _ = _edge_line(dock["edge"], rect)
            for i in range(max(1, min(dock["count"], 24))):
                uc = _opening_u(dock["edge"], rect, dock["offset"] + dock["pitch"] * i)
                half = dock["width"] / 2
                docks.append({"kind": "overhead", "axis": axis, "fixed": snap(_fixed_dim(axis), fixed),
                              "a": _q(uc - half), "b": _q(uc + half), "width": _q(dock["width"]),
                              "source_ids": [s for s in [element_ids.get((room["id"], "docks", dock.get("id")))] if s]})

    def grouped(collection):
        rows = sorted(records[collection], key=lambda r: (r["axis"], r["fixed"], r["uc"], r["room"]["id"], r["index"]))
        groups = []
        for row in rows:
            last = groups[-1] if groups else None
            if (last and last["axis"] == row["axis"] and last["fixed"] == row["fixed"]
                    and abs(last["uc"] - row["uc"]) <= TOL and abs(last["w"] - row["w"]) <= TOL):
                last["records"].append(row)
            else:
                groups.append({"axis": row["axis"], "fixed": row["fixed"], "uc": row["uc"],
                               "w": row["w"], "records": [row]})
        return groups

    doors = []
    for group in grouped("doors"):
        axis, fixed, uc, width = group["axis"], group["fixed"], group["uc"], group["w"]
        a, b = _q(uc - width / 2), _q(uc + width / 2)
        thick = t if _covered(runs, axis, fixed, uc) else 0.0
        sides = _adjacent(rooms, axis, fixed, a, b)
        hosts = [r["room"] for r in group["records"]]
        if not sides:
            sides = {1: hosts[0]}
        ranked = sorted(sides.items(), key=lambda kv: (-_room_rank(kv[1], industrial),
                                                       kv[1]["rect"][2] * kv[1]["rect"][3], kv[1]["id"]))
        sign, swing_room = ranked[0]
        sx, sz, sw, sd = swing_room["rect"]
        span0, span1 = (sx, sx + sw) if axis == "x" else (sz, sz + sd)
        hinge_low = (a - span0) <= (span1 - b)
        face = fixed + sign * thick / 2
        leaves = []
        if width >= STD.DOUBLE_LEAF_MIN_WIDTH_M - 1e-9:
            mid = (a + b) / 2
            for hinge, latch in ((a, mid), (b, mid)):
                leaves.append({"hinge": _point(axis, hinge, face), "closed": _point(axis, latch, face),
                               "open": _point(axis, hinge, face + sign * abs(latch - hinge)),
                               "radius": _q(abs(latch - hinge))})
        else:
            hinge, latch = (a, b) if hinge_low else (b, a)
            leaves.append({"hinge": _point(axis, hinge, face), "closed": _point(axis, latch, face),
                           "open": _point(axis, hinge, face + sign * width), "radius": _q(width)})
        doors.append({
            "kind": "double" if len(leaves) == 2 else "single", "axis": axis, "fixed": fixed,
            "a": a, "b": b, "width": _q(width), "wall_thickness": _q(thick), "leaves": leaves,
            "swing_room": swing_room["id"], "swing_basis": "DRAFTING_DEFAULT",
            "glass": any(r["item"].get("material") == "glass" for r in group["records"]),
            "rooms": sorted({r["room"]["id"] for r in group["records"]}),
            "source_ids": sorted({r["source_id"] for r in group["records"] if r["source_id"]}),
        })
    windows = []
    for group in grouped("windows"):
        axis, fixed, uc, width = group["axis"], group["fixed"], group["uc"], group["w"]
        windows.append({
            "axis": axis, "fixed": fixed, "a": _q(uc - width / 2), "b": _q(uc + width / 2),
            "width": _q(width), "wall_thickness": _q(t if _covered(runs, axis, fixed, uc) else 0.0),
            "rooms": sorted({r["room"]["id"] for r in group["records"]}),
            "source_ids": sorted({r["source_id"] for r in group["records"] if r["source_id"]}),
        })
    for dock in docks:
        dock["wall_thickness"] = _q(t if _covered(runs, dock["axis"], dock["fixed"], (dock["a"] + dock["b"]) / 2) else 0.0)
    return doors, windows, docks


# ---------------------------------------------------------------------------
# Stairs and lifts
# ---------------------------------------------------------------------------
def _stairs(model: dict, level: dict, rooms: list) -> tuple[list, list]:
    import acs_stairs
    index = level["index"]
    found, skipped, seen = [], [], set()
    sources = [(level["template"], rooms, True)]
    for other in model.get("levels") or []:
        template = other.get("template") if isinstance(other, dict) else None
        if template != level["template"] and isinstance(model["floors"].get(template), dict):
            sources.append((template, model["floors"][template].get("rooms") or [], False))
    for template, source_rooms, own in sources:
        for room in source_rooms:
            for obj in room.get("objects") or []:
                if not isinstance(obj, dict) or obj.get("kind") != "stairs":
                    continue
                key = (template, room.get("id"), obj.get("id"))
                if key in seen:
                    continue
                stair = obj.get("stair") if isinstance(obj.get("stair"), dict) else {}
                source_level, target_level = stair.get("source_level_index"), stair.get("target_level_index")
                role = "up" if own and source_level == index else ("down" if target_level == index else None)
                if role is None and not own:
                    continue
                seen.add(key)
                try:
                    acs_stairs.resolve_stair_geometry(obj)
                except ValueError:
                    skipped.append({"room_id": room.get("id"), "object_id": obj.get("id"), "reason": "STAIR_GEOMETRY_NOT_DRAWABLE"})
                    continue
                found.append((room, obj, role or "none", own))
    stairs = []
    footprints = {}
    for room, obj, role, own in found:
        s = obj["stair"]
        fw, gap, tread, entry, mid = (float(s[k]) for k in ("flight_width_m", "gap_m", "tread_m", "entry_landing_m", "mid_landing_m"))
        n = s["risers_per_flight"]
        width, depth = 2 * fw + gap, entry + (n - 1) * tread + mid
        start, run = -depth / 2 + entry, (n - 1) * tread
        rise = (s["target_elevation_m"] - s["source_elevation_m"]) / (2 * n)
        turns = int(obj["rot"] / 90) % 4
        ox, oz = room["rect"][0] + obj["x"], room["rect"][1] + obj["z"]

        def world(a, b, turns=turns, ox=ox, oz=oz):
            ta, tb = ((a, b), (-b, a), (-a, -b), (b, -a))[turns]
            return [_q(ox + ta), _q(oz + tb)]

        x1, x2 = -(fw + gap) / 2, (fw + gap) / 2
        cut = min(n - 1, max(1, int(math.ceil(STD.CUT_PLANE_HEIGHT_M / rise)))) if rise > 0 else n - 1
        solid, overhead = [], []
        for k in range(n):
            zline = start + k * tread
            for side_x0, side_x1, flight in ((-width / 2, -gap / 2, 1), (gap / 2, width / 2, 2)):
                above = flight == 2 or k > cut
                (overhead if (role == "up" and above) else solid).append([world(side_x0, zline), world(side_x1, zline)])
        for xa in (-width / 2, -gap / 2, gap / 2, width / 2):
            lower = [world(xa, start), world(xa, start + min(run, (cut + 0.5) * tread))]
            upper = [world(xa, start + min(run, (cut + 0.5) * tread)), world(xa, start + run)]
            if xa < 0 and role == "up":
                solid.append(lower)
                overhead.append(upper)
            elif role == "up":
                overhead.append([world(xa, start), world(xa, start + run)])
            else:
                solid.append([world(xa, start), world(xa, start + run)])
        landing = [[world(-width / 2, start + run), world(width / 2, start + run)],
                   [world(-width / 2, depth / 2), world(width / 2, depth / 2)],
                   [world(-width / 2, start + run), world(-width / 2, depth / 2)],
                   [world(width / 2, start + run), world(width / 2, depth / 2)]]
        (overhead if role == "up" else solid).extend(landing)
        mid_z = start + run + mid * 0.2
        item = {"object_id": obj.get("id"), "room_id": room.get("id"), "role": role, "own": own,
                # The tag sits in the lower part of the mid-landing; arrows turn in its upper part.
                "landing_center": world(0.0, start + run + mid * 0.62),
                "landing_size": [_q(width), _q(mid * 0.7)] if turns % 2 == 0 else [_q(mid * 0.7), _q(width)],
                "risers_per_flight": n, "tread_m": _q(tread), "riser_m": _q(rise),
                "solid": solid, "overhead": overhead, "break": None, "arrows": []}
        if role == "up":
            zc = start + (cut + 0.5) * tread
            item["break"] = [world(-width / 2 - 0.05, zc + 0.6 * tread), world(-gap / 2 + 0.05, zc - 0.6 * tread)]
        footprints.setdefault(tuple(world(0, 0)), []).append(item)
        item["_path"] = {
            "up_full": [world(x1, start), world(x1, mid_z), world(x2, mid_z), world(x2, start)],
            "up_flight": [world(x1, start), world(x1, start + (cut + 0.5) * tread)],
            "down_full": [world(x2, start), world(x2, mid_z), world(x1, mid_z), world(x1, start)],
            "down_flight": [world(x2, start), world(x2, start + run - 0.1 * tread)],
            "label_up": world(x1, start - entry / 2),
            "label_down": world(x2, start - entry / 2),
        }
        stairs.append(item)
    for items in footprints.values():
        roles = {i["role"] for i in items}
        for item in items:
            path = item.pop("_path")
            if item["role"] == "up":
                if "down" in roles:  # stacked core: the flight below the cut is seen solid
                    item["solid"].extend(item["overhead"])
                    item["overhead"] = []
                item["arrows"].append({"kind": "up", "points": path["up_flight" if "down" in roles else "up_full"],
                                       "label": "صعود", "label_at": path["label_up"]})
            elif item["role"] == "down":
                item["arrows"].append({"kind": "down", "points": path["down_flight" if "up" in roles else "down_full"],
                                       "label": "نزول", "label_at": path["label_down"]})
    return stairs, skipped


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
def _dedupe(points: list) -> list:
    out = []
    for p in sorted(points):
        if not out or p - out[-1] > 0.005:
            out.append(_q(p))
    return out


def _chains(bounds, runs: list, openings: list, t: float) -> list:
    x0, z0, x1, z1 = bounds
    chains = []
    for side in ("N", "S", "W", "E"):
        along = "x" if side in ("N", "S") else "z"
        lines = [f for _, a, f, _, _ in runs if a == along]
        if not lines:
            continue
        facade = min(lines) if side in ("N", "W") else max(lines)
        lo, hi = (x0, x1) if along == "x" else (z0, z1)
        face = {"N": z0, "S": z1, "W": x0, "E": x1}[side]
        reach = t + TOL
        touching = [f for _, a, f, u0, u1 in runs if a != along
                    and ((u0 <= facade + reach) if side in ("N", "W") else (u1 >= facade - reach))]
        inner = [p for p in touching if lo + 0.75 * t + TOL < p < hi - 0.75 * t - TOL]
        walls = _dedupe([lo, hi] + inner)
        jambs = []
        for o in openings:
            if o["axis"] == along and abs(o["fixed"] - facade) <= TOL:
                jambs += [min(max(o["a"], lo), hi), min(max(o["b"], lo), hi)]
        opening_chain = _dedupe([lo, hi] + jambs)
        result = []
        if len(opening_chain) > 2 and opening_chain != walls:
            result.append(("openings", opening_chain))
        if len(walls) > 2:
            result.append(("walls", walls))
        result.append(("overall", _dedupe([lo, hi])))
        for rank, (kind, points) in enumerate(result):
            chains.append({"side": side, "kind": kind, "rank": rank, "face": _q(face), "points": points})
    return chains


# ---------------------------------------------------------------------------
# Level drafting
# ---------------------------------------------------------------------------
def level_drafting(model: dict, level_index: int, primitives: list, source_map: list) -> dict:
    """Derive the drawing content of one level from the canonical model only."""
    level = next((v for v in model["levels"] if v.get("index") == level_index), None)
    if level is None:
        raise PlanError("LEVEL_NOT_FOUND", "Requested level is absent")
    rooms = [r for r in model["floors"][level["template"]]["rooms"] if isinstance(r, dict)]
    t = float(model["wall_t"]) if _num(model.get("wall_t")) and model["wall_t"] > 0 else 0.15
    half = t / 2
    snap = _Snap()
    runs = _wall_runs(model, rooms, snap)
    element_ids = {}
    for entry in source_map:
        source = entry.get("source") if isinstance(entry, dict) else None
        if (isinstance(source, dict) and source.get("kind") == "element"
                and source.get("level_index") == level_index and source.get("template") == level["template"]):
            element_ids[(source.get("room_id"), source.get("collection"), source.get("element_id"))] = entry["source_id"]
    doors, windows, docks = _openings(model, rooms, runs, snap, t, element_ids, level)
    opening_rects = []
    for o in doors + windows + docks:
        opening_rects.append(_rect_of_run(o["axis"], o["fixed"], o["a"], o["b"], half))
    cut_rects = _extended_rects(runs, half, "cut")
    low_rects = _extended_rects(runs, half, "low")
    glazed_rects = _extended_rects(runs, half, "glazed")
    xs, zs, cut_cells = _grid(cut_rects, opening_rects)
    walls = {"cut": _loops(xs, zs, cut_cells)}
    lx, lz, low_cells = _grid(low_rects, opening_rects + cut_rects)
    walls["low"] = _loops(lx, lz, low_cells)
    gx, gz, glazed_cells = _grid(glazed_rects, opening_rects + cut_rects + low_rects)
    walls["glazed"] = _loops(gx, gz, glazed_cells)
    walls["glazed_centrelines"] = [
        [_point(a, u0, f), _point(a, u1, f)] for c, a, f, u0, u1 in runs if c == "glazed"]

    # Building bounds: wall faces and every room rectangle on this level.
    boxes = [b for b in (_cells_bounds(xs, zs, cut_cells), _cells_bounds(lx, lz, low_cells),
                         _cells_bounds(gx, gz, glazed_cells)) if b]
    boxes += [(r["rect"][0], r["rect"][1], r["rect"][0] + r["rect"][2], r["rect"][1] + r["rect"][3]) for r in rooms]
    bounds = [_q(min(b[0] for b in boxes)), _q(min(b[1] for b in boxes)),
              _q(max(b[2] for b in boxes)), _q(max(b[3] for b in boxes))]

    def present_edges(rect):
        out = {}
        for edge in EDGES:
            axis, fixed, u0, u1 = _edge_line(edge, rect)
            out[edge] = _coverage_fraction(runs, axis, snap(_fixed_dim(axis), fixed), u0, u1) >= 0.5
        return out

    stairs, skipped = _stairs(model, level, rooms)

    def landing_in(rect):
        x, z, w, d = rect
        for stair in stairs:  # own stairs first, then stairs arriving from below
            cx, cz = stair["landing_center"]
            if x < cx < x + w and z < cz < z + d:
                return stair
        return None

    # Room tags, open-edge separation lines and lifts.
    tags, lifts, separations = [], [], {}
    by_id = {}
    for room in rooms:
        by_id.setdefault(room.get("id"), room)
    all_openings = doors + windows + docks
    for ordinal, primitive in enumerate(primitives, 1):
        room = by_id.get(primitive["source"].get("room_id"))
        x, z, w, d = primitive["rect_xz_m"]
        present = present_edges((x, z, w, d))
        for edge in EDGES:
            axis, fixed, u0, u1 = _edge_line(edge, (x, z, w, d))
            fixed = snap(_fixed_dim(axis), fixed)
            for s0, s1 in _uncovered_spans(runs, all_openings, axis, fixed, u0, u1):
                a, b = _point(axis, s0, fixed), _point(axis, s1, fixed)
                separations[tuple(a + b)] = [a, b]
        clear_w = max(0.0, w - half * (present["W"] + present["E"]))
        clear_d = max(0.0, d - half * (present["N"] + present["S"]))
        tags.append({
            "ordinal": ordinal, "number": "S%d" % ordinal, "source_id": primitive["source_id"],
            "label": primitive["label"], "rect": [_q(v) for v in (x, z, w, d)],
            "center": [_q(x + w / 2), _q(z + d / 2)],
            "clear_w_m": _q(clear_w), "clear_d_m": _q(clear_d), "net_area_m2": _q(clear_w * clear_d),
            "axis_area_m2": _q(w * d), "walls_present": [e for e in EDGES if present[e]],
            "role": str((room or {}).get("role") or ""),
        })
        landing = landing_in((x, z, w, d))
        if landing is not None:
            tags[-1]["center"] = landing["landing_center"]
            tags[-1]["fit_m"] = landing["landing_size"]
        if room is not None and str(room.get("role") or "").lower() in ELEVATOR_ROLES:
            cx0, cz0 = x + half * present["W"], z + half * present["N"]
            cx1, cz1 = x + w - half * present["E"], z + d - half * present["S"]
            lifts.append([[_q(cx0), _q(cz0)], [_q(cx1), _q(cz1)]])
            lifts.append([[_q(cx0), _q(cz1)], [_q(cx1), _q(cz0)]])

    if runs:
        chain_runs, chain_t = runs, t
    else:  # wall-less zones (open warehouse floors): dimension the zone lines
        chain_runs, chain_t = [], 0.0
        for room in rooms:
            for edge in EDGES:
                axis, fixed, u0, u1 = _edge_line(edge, room["rect"])
                chain_runs.append(("zone", axis, snap(_fixed_dim(axis), fixed), u0, u1))
    chains = _chains(bounds, chain_runs, all_openings, chain_t)

    enclosed = [r for r in rooms if any(present_edges(r["rect"]).values())]
    area_rects = [(r["rect"][0], r["rect"][1], r["rect"][0] + r["rect"][2], r["rect"][1] + r["rect"][3]) for r in enclosed]
    ax, az, area_cells = _grid(area_rects + cut_rects + low_rects + glazed_rects, [])
    gross = _cells_area(ax, az, area_cells) if area_cells and level.get("kind") != "roof" else None
    geometry = {
        "schema": SCHEMA, "scope": SCOPE, "level_index": level_index, "level_kind": level.get("kind"),
        "template": level["template"], "wall_thickness_m": _q(t), "cut_plane_m": STD.CUT_PLANE_HEIGHT_M,
        "bounds": bounds, "walls": walls, "doors": doors, "windows": windows, "docks": docks,
        "stairs": stairs, "lifts": lifts, "separations": [separations[k] for k in sorted(separations)],
        "tags": tags, "chains": chains,
        "net_area_total_m2": _q(sum(tag["net_area_m2"] for tag in tags)),
        "gross_area_outer_faces_m2": None if gross is None else _q(gross),
        "drafting_defaults": list(DRAFTING_DEFAULTS), "not_drawn": list(NOT_DRAWN),
        "skipped": skipped,
    }
    geometry["drafting_hash"] = _hash(geometry)
    return geometry


def model_extents(model: dict) -> list:
    """Union of the site and every room (+ half a wall) over all levels: one sheet frame per set."""
    t = float(model["wall_t"]) if _num(model.get("wall_t")) and model["wall_t"] > 0 else 0.15
    boxes = []
    site = model.get("site") if isinstance(model.get("site"), dict) else {}
    if _num(site.get("w")) and _num(site.get("d")) and site["w"] > 0 and site["d"] > 0:
        boxes.append((0.0, 0.0, float(site["w"]), float(site["d"])))
    for level in model.get("levels") or []:
        floor = model.get("floors", {}).get(level.get("template")) if isinstance(level, dict) else None
        for room in (floor or {}).get("rooms") or []:
            rect = room.get("rect") if isinstance(room, dict) else None
            if isinstance(rect, list) and len(rect) == 4 and all(_num(v) for v in rect):
                x, z, w, d = rect
                boxes.append((x - t / 2, z - t / 2, x + w + t / 2, z + d + t / 2))
    if not boxes:
        raise PlanError("INVALID_GEOMETRY", "Plan has no measurable extent")
    return [_q(min(b[0] for b in boxes)), _q(min(b[1] for b in boxes)),
            _q(max(b[2] for b in boxes)), _q(max(b[3] for b in boxes))]


def sheet_for(model: dict) -> dict:
    extents = model_extents(model)
    chosen = STD.choose_sheet(extents[2] - extents[0], extents[3] - extents[1])
    pw, ph = chosen["paper_mm"]
    frame = STD.SHEET_FRAME_MM
    margin = STD.DIMENSION["margin_mm"]
    k = 1000.0 / chosen["scale"]
    ax0, ax1 = frame["left"] + 4.0, pw - frame["right"] - STD.TITLE_BLOCK_WIDTH_MM - 4.0
    ay0, ay1 = frame["top"] + 4.0, ph - frame["bottom"] - 4.0
    bw = (extents[2] - extents[0]) * k + 2 * margin
    bh = (extents[3] - extents[1]) * k + 2 * margin + 18.0
    ox = ax0 + max(0.0, (ax1 - ax0 - bw) / 2) + margin
    oy = ay0 + max(0.0, (ay1 - ay0 - bh) / 2) + margin
    chosen.update({"extents_m": extents, "mm_per_m": k, "origin_mm": [round(ox, 4), round(oy, 4)],
                   "drawing_area_mm": [ax0, ay0, ax1, ay1]})
    return chosen


class Paper:
    """Model (x, z) metres to sheet millimetres (y down) and back."""

    def __init__(self, sheet: dict):
        self.k = sheet["mm_per_m"]
        self.ex, self.ez = sheet["extents_m"][0], sheet["extents_m"][1]
        self.ox, self.oy = sheet["origin_mm"]
        self.scale = sheet["scale"]

    def to_paper(self, point) -> tuple[float, float]:
        return (self.ox + (point[0] - self.ex) * self.k, self.oy + (point[1] - self.ez) * self.k)

    def to_model(self, point) -> tuple[float, float]:
        return (self.ex + (point[0] - self.ox) / self.k, self.ez + (point[1] - self.oy) / self.k)

    def m(self, paper_mm: float) -> float:
        return paper_mm / self.k


# ---------------------------------------------------------------------------
# Draw operations
# ---------------------------------------------------------------------------
# Every op has "space": "model" (x, z metres) or "paper" (mm, y down), a layer
# and op-specific fields. Text sizes are always paper millimetres.
def _line(layer, a, b, space="model"):
    return {"op": "line", "layer": layer, "a": list(a), "b": list(b), "space": space}


def _text(layer, text, at, size, anchor="middle", rotate=0.0, space="model", halo=False, role=None):
    op = {"op": "text", "layer": layer, "text": str(text), "at": list(at), "size": size,
          "anchor": anchor, "rotate": rotate, "space": space, "halo": halo}
    if role:
        op["role"] = role
    return op


def _tag_ops(tag: dict, paper: Paper) -> list:
    """Room name, number/net area and clear size, fitted inside the room on paper."""
    sizes = STD.TEXT_HEIGHT_MM
    fit_w, fit_h = tag.get("fit_m") or (tag["clear_w_m"], tag["clear_d_m"])
    room_w = fit_w * paper.k - 2.0
    room_h = fit_h * paper.k - 1.0
    name = tag["label"]
    name_size = sizes["room_name"]
    width = text_width_mm(name, name_size)
    if width > room_w > 0:
        name_size = max(sizes["minimum"], name_size * room_w / width)
    lines = [(name, name_size, "A-FLOR-IDEN", "name"),
             ("%s · %s" % (tag["number"], fmt_area(tag["net_area_m2"])), sizes["room_area"], "A-AREA-IDEN", "area"),
             ("%s × %s" % (fmt_length(tag["clear_w_m"]), fmt_length(tag["clear_d_m"])), sizes["note"], "A-AREA-IDEN", "size")]
    gap = 0.75
    while len(lines) > 1 and sum(1.45 * s for _, s, _, _ in lines) + gap * (len(lines) - 1) > room_h:
        lines.pop()
    for k, (text, size, layer, role) in enumerate(lines[1:], 1):
        avail = room_w
        if text_width_mm(text, size) > avail > 0:
            lines[k] = (text, max(sizes["minimum"], size * avail / text_width_mm(text, size)), layer, role)
    total = sum(1.45 * s for _, s, _, _ in lines) + gap * (len(lines) - 1)
    cx, cy = paper.to_paper(tag["center"])
    y = cy - total / 2
    ops = []
    for text, size, layer, role in lines:
        y += 1.15 * size  # room for Arabic ascenders above the cap height
        ops.append(_text(layer, text, paper.to_model((cx, y)), round(size, 3), halo=True, role=role))
        y += 0.3 * size + gap
    return ops


def dim_ops(chain: dict, paper: Paper) -> list:
    """Expand one dimension chain into dimension segment ops (model space)."""
    dim = STD.DIMENSION
    side = chain["side"]
    outward = -1 if side in ("N", "W") else 1
    offset = paper.m(dim["first_offset_mm"] + chain["rank"] * dim["chain_spacing_mm"])
    line = chain["face"] + outward * offset
    ops = []
    points = chain["points"]
    flip = False
    for a, b in zip(points, points[1:]):
        text = fmt_length(b - a)
        short = text_width_mm(text, dim_text_size()) + 1.0 > (b - a) * paper.k
        flip = (not flip) if short else False
        ops.append({"op": "dim", "layer": "A-ANNO-DIMS", "space": "model", "axis": "x" if side in ("N", "S") else "z",
                    "a": _q(a), "b": _q(b), "face": chain["face"], "line": _q(line), "outward": outward,
                    "text": text, "flip": flip, "chain": chain["kind"], "side": side})
    return ops


def dim_text_size() -> float:
    return STD.TEXT_HEIGHT_MM["dimension"]


def expand_dim(op: dict, paper: Paper) -> list:
    """Extension lines, dimension line, ticks and text of one segment (model space)."""
    dim = STD.DIMENSION
    m = paper.m
    axis, a, b, face, line, out = op["axis"], op["a"], op["b"], op["face"], op["line"], op["outward"]

    def pt(u, v):
        return [u, v] if axis == "x" else [v, u]

    ops = []
    for u in (a, b):
        ops.append(_line("A-ANNO-DIMS", pt(u, face + out * m(dim["extension_gap_mm"])),
                         pt(u, line + out * m(dim["extension_beyond_mm"]))))
        h = m(dim["tick_mm"]) / 2 / math.sqrt(2)
        # A tick reads lower-left to upper-right on paper (z grows downward).
        ops.append(_line("A-ANNO-DIMS", pt(u - h, line + h) if axis == "x" else [line - h, u + h],
                         pt(u + h, line - h) if axis == "x" else [line + h, u - h]))
    over = m(dim["line_overrun_mm"])
    ops.append(_line("A-ANNO-DIMS", pt(a - over, line), pt(b + over, line)))
    size = dim_text_size()
    gap = m(dim["text_gap_mm"])
    mid = (a + b) / 2
    if axis == "x":
        at = [mid, line + gap + m(size)] if op["flip"] else [mid, line - gap]
        ops.append(_text("A-ANNO-DIMS", op["text"], at, size, halo=True))
    else:
        at = [line + gap + m(size), mid] if op["flip"] else [line - gap, mid]
        ops.append(_text("A-ANNO-DIMS", op["text"], at, size, rotate=90.0, halo=True))
    return ops


def plan_ops(draft: dict, paper: Paper) -> dict:
    """Ordered draw ops for one level. Phases keep fills under lines and text on top."""
    ops = {"areas": [], "fills": [], "lines": [], "symbols": [], "texts": [], "rooms": [], "dims": []}
    for a, b in draft["separations"]:
        ops["areas"].append(_line("A-AREA-BNDY", a, b))
    if draft["walls"]["cut"]:
        ops["fills"].append({"op": "fill", "layer": "A-WALL-PATT", "loops": draft["walls"]["cut"], "space": "model"})
        ops["lines"].append({"op": "loops", "layer": "A-WALL", "loops": draft["walls"]["cut"], "space": "model"})
    if draft["walls"]["low"]:
        ops["lines"].append({"op": "loops", "layer": "A-WALL-PRHT", "loops": draft["walls"]["low"], "space": "model"})
    if draft["walls"]["glazed"]:
        ops["lines"].append({"op": "loops", "layer": "A-GLAZ", "loops": draft["walls"]["glazed"], "space": "model"})
    for a, b in draft["walls"]["glazed_centrelines"]:
        ops["lines"].append(_line("A-GLAZ", a, b))
    for window in draft["windows"]:
        axis, f, a, b, t = window["axis"], window["fixed"], window["a"], window["b"], window["wall_thickness"]
        # Sill lines on both wall faces and a double glazing line on the wall axis.
        offsets = (-t / 2, t / 2, -paper.m(0.35), paper.m(0.35)) if t else (-paper.m(0.35), paper.m(0.35))
        for v in offsets:
            ops["lines"].append(dict(_line("A-GLAZ", _point(axis, a, f + v), _point(axis, b, f + v)),
                                     source_ids=window["source_ids"]))
    for door in draft["doors"]:
        for leaf in door["leaves"]:
            ops["lines"].append(dict(_line("A-DOOR", leaf["hinge"], leaf["open"]), source_ids=door["source_ids"]))
            ops["lines"].append({"op": "arc", "layer": "A-DOOR-SWNG", "c": leaf["hinge"], "r": leaf["radius"],
                                 "from": leaf["open"], "to": leaf["closed"], "space": "model",
                                 "source_ids": door["source_ids"]})
    for dock in draft["docks"]:
        axis, f, a, b, t = dock["axis"], dock["fixed"], dock["a"], dock["b"], dock["wall_thickness"]
        for v in ((-t / 2, t / 2) if t else (0.0,)):
            ops["lines"].append(dict(_line("A-FLOR-OVHD", _point(axis, a, f + v), _point(axis, b, f + v)),
                                     source_ids=dock["source_ids"]))
    for stair in draft["stairs"]:
        for a, b in stair["solid"]:
            ops["lines"].append(_line("A-FLOR-STRS", a, b))
        for a, b in stair["overhead"]:
            ops["lines"].append(_line("A-FLOR-OVHD", a, b))
        if stair["break"]:
            ops["lines"].append(_line("A-FLOR-STRS", *stair["break"]))
        for arrow in stair["arrows"]:
            pts = arrow["points"]
            for a, b in zip(pts, pts[1:]):
                ops["lines"].append(_line("A-FLOR-STRS", a, b))
            # Start dot and arrow head (paper-sized, model space).
            ops["symbols"].append({"op": "circle", "layer": "A-FLOR-STRS", "c": pts[0], "r": paper.m(0.6),
                                   "fill": True, "space": "model"})
            (ax, az), (bx, bz) = pts[-2], pts[-1]
            length = math.hypot(bx - ax, bz - az) or 1.0
            ux, uz = (bx - ax) / length, (bz - az) / length
            head, wing = paper.m(2.5), paper.m(0.9)
            ops["symbols"].append({"op": "poly", "layer": "A-FLOR-STRS", "fill": True, "space": "model", "pts": [
                [bx, bz], [bx - ux * head - uz * wing, bz - uz * head + ux * wing],
                [bx - ux * head + uz * wing, bz - uz * head - ux * wing]]})
            ops["texts"].append(_text("A-FLOR-STRS", arrow["label"], arrow["label_at"], STD.TEXT_HEIGHT_MM["dimension"], halo=True))
    for a, b in draft["lifts"]:
        ops["lines"].append(_line("A-FLOR-EVTR", a, b))
    for chain in draft["chains"]:
        ops["dims"].extend(dim_ops(chain, paper))
    for tag in draft["tags"]:
        ops["rooms"].append({"op": "room", "layer": "A-AREA", "space": "model", "source_id": tag["source_id"],
                             "label": tag["label"], "rect": tag["rect"], "number": tag["number"],
                             "desc": "%s · axis rectangle %s × %s m (%s) · clear %s × %s m · net area %s" % (
                                 tag["number"], "%g" % tag["rect"][2], "%g" % tag["rect"][3],
                                 fmt_area(tag["axis_area_m2"]), fmt_length(tag["clear_w_m"]),
                                 fmt_length(tag["clear_d_m"]), fmt_area(tag["net_area_m2"])),
                             "texts": _tag_ops(tag, paper)})
    return ops


def _north_arrow(cx: float, cy: float) -> list:
    r = 6.0
    return [
        {"op": "circle", "layer": "A-ANNO-SYMB", "c": [cx, cy], "r": r, "fill": False, "space": "paper"},
        {"op": "poly", "layer": "A-ANNO-SYMB", "fill": True, "space": "paper",
         "pts": [[cx, cy - r - 1.5], [cx - 3.2, cy + 4.0], [cx, cy + 1.8]]},
        {"op": "poly", "layer": "A-ANNO-SYMB", "fill": False, "space": "paper",
         "pts": [[cx, cy - r - 1.5], [cx + 3.2, cy + 4.0], [cx, cy + 1.8]]},
        _text("A-ANNO-SYMB", "N", (cx, cy - r - 3.0), 3.5, space="paper"),
    ]


def _scale_bar(x: float, y: float, scale: int) -> list:
    length_m, parts = STD.scale_bar_length_m(scale)
    total = length_m * 1000.0 / scale
    step = total / parts
    ops = []
    for i in range(parts):
        ops.append({"op": "poly", "layer": "A-ANNO-SYMB", "fill": i % 2 == 0, "space": "paper",
                    "pts": [[x + i * step, y], [x + (i + 1) * step, y], [x + (i + 1) * step, y + 1.6], [x + i * step, y + 1.6]]})
    for i in range(parts + 1):
        value = length_m * i / parts
        label = ("%g" % value) + (" m" if i == parts else "")
        ops.append(_text("A-ANNO-SYMB", label, (x + i * step, y + 4.6), 2.0, space="paper"))
    return ops


def sheet_ops(draft: dict, sheet: dict, paper: Paper, *, model: dict, page_number: int, page_count: int,
              title_en: str, revision_id: str, model_hash: str, provenance_hash: str, schedule: bool) -> list:
    """Border, drawing title, north arrow, scale bar and the right-hand title block (paper mm)."""
    pw, ph = sheet["paper_mm"]
    frame = STD.SHEET_FRAME_MM
    fx0, fy0, fx1, fy1 = frame["left"], frame["top"], pw - frame["right"], ph - frame["bottom"]
    tb0 = fx1 - STD.TITLE_BLOCK_WIDTH_MM
    T = STD.TEXT_HEIGHT_MM
    ops = [{"op": "poly", "layer": "A-ANNO-TTLB", "fill": False, "space": "paper",
            "pts": [[fx0, fy0], [fx1, fy0], [fx1, fy1], [fx0, fy1]], "weight": 0.7},
           _line("A-ANNO-TTLB", (tb0, fy0), (tb0, fy1), space="paper")]
    level = next(v for v in model["levels"] if v.get("index") == draft["level_index"])
    title_ar = level_title_ar(level, draft["level_index"])
    scale_text = "1:%d" % sheet["scale"] if sheet["standard_scale"] else "1:%d (غير قياسي)" % sheet["scale"]
    # Drawing title and scale bar under the plan block.
    ext = sheet["extents_m"]
    left, _ = paper.to_paper((ext[0], ext[1]))
    right, bottom = paper.to_paper((ext[2], ext[3]))
    cx = (left + right) / 2
    ty = bottom + STD.DIMENSION["margin_mm"] + 2.0
    ops.append(_text("A-ANNO-TEXT", title_ar, (cx, ty), T["title"], space="paper"))
    ops.append(_line("A-ANNO-TEXT", (cx - 40.0, ty + 1.6), (cx + 40.0, ty + 1.6), space="paper"))
    ops.append(_text("A-ANNO-TEXT", "%s · %s" % (title_en, scale_text), (cx, ty + 6.0), T["dimension"], space="paper"))
    length_m, _ = STD.scale_bar_length_m(sheet["scale"])
    ops += _scale_bar(cx - length_m * 500.0 / sheet["scale"], ty + 9.0, sheet["scale"])

    # Title block, right-aligned for Arabic.
    rx = fx1 - 4.0
    lx = tb0 + 4.0
    y = fy0 + 4.0

    def row(text, size, layer="A-ANNO-TEXT", anchor="end", x=None, room=None):
        nonlocal y
        width = text_width_mm(text, size)
        room = rx - lx if room is None else room
        if width > room:
            size = max(1.4, size * room / width)
        y += size * 1.15
        ops.append(_text(layer, text, (rx if x is None else x, y), round(size, 3), anchor=anchor, space="paper"))
        y += size * 0.6

    def rule():
        nonlocal y
        y += 1.2
        ops.append(_line("A-ANNO-TTLB", (tb0, y), (fx1, y), space="paper"))
        y += 1.6

    row("ACS · استوديو البناء", T["title"])
    row("مخطط معماري مفاهيمي من النموذج المعتمد", T["note"])
    rule()
    project_name = str((model.get("meta") or {}).get("name") or "").strip()
    if project_name:
        row("المشروع", T["note"])
        row(project_name[:60], T["subtitle"])
        ops[-1]["optional"] = True  # cosmetic: a renderer may drop it if its font cannot draw it
        rule()
    section_top = y
    row("اللوحة", T["note"])
    ops += _north_arrow(lx + 9.0, section_top + 13.0)  # plan north is up (canonical -Z)
    beside_arrow = rx - lx - 20.0  # keep the drawing title clear of the north arrow
    row(title_ar, T["title"], room=beside_arrow)
    row(title_en, T["dimension"], room=beside_arrow)
    row("A-%d · %d / %d" % (100 + page_number, page_number, page_count), T["dimension"], room=beside_arrow)
    rule()
    row("المقياس %s على ورق %s" % (scale_text, sheet["paper"]), T["subtitle"])
    row("Scale %s at %s · 1 unit = 1 m" % (scale_text, sheet["paper"]), T["note"])
    row("الأبعاد بالمتر، والمساحات بالمتر المربع (m2)", T["note"])
    row("Dimensions in metres; areas in m2", T["note"])
    rule()
    if schedule:
        row("جدول المساحات", T["subtitle"])
        cols = (rx, rx - 9.0, lx + 34.0, lx + 15.0)
        header_y = y + T["note"]
        for text, x in (("رقم", cols[0]), ("الفراغ", cols[1]), ("صافي", cols[2]), ("محاور", cols[3])):
            ops.append(_text("A-ANNO-TEXT", text, (x, header_y), T["note"], anchor="end", space="paper"))
        y = header_y + 1.5
        ops.append(_line("A-ANNO-TTLB", (lx, y), (rx, y), space="paper"))
        rows = draft["tags"]
        reserve = 78.0
        available = max(0.0, fy1 - reserve - y)
        pitch = max(2.8, min(4.2, available / max(1, len(rows) + 2)))
        size = round(min(T["note"], pitch * 0.5), 3)
        shown = rows if len(rows) * pitch <= available else rows[:max(0, int(available // pitch) - 1)]
        for tag in shown:
            y += pitch
            name = tag["label"]
            name_size = size
            room_w = (cols[1] - cols[2]) - 12.0  # keep clear of the right-aligned area figure
            if text_width_mm(name, name_size) > room_w:
                name_size = max(1.5, name_size * room_w / text_width_mm(name, name_size))
            ops.append(_text("A-ANNO-TEXT", tag["number"], (cols[0], y), size, anchor="end", space="paper"))
            ops.append(_text("A-ANNO-TEXT", name, (cols[1], y), name_size, anchor="end", space="paper", role="schedule_name"))
            ops.append(_text("A-ANNO-TEXT", fmt_area(tag["net_area_m2"]), (cols[2], y), size, anchor="end", space="paper"))
            ops.append(_text("A-ANNO-TEXT", fmt_area(tag["axis_area_m2"]), (cols[3], y), size, anchor="end", space="paper"))
        if len(shown) < len(rows):
            y += pitch
            ops.append(_text("A-ANNO-TEXT", "+%d فراغات أخرى في ملف الإيصال" % (len(rows) - len(shown)),
                             (rx, y), size, anchor="end", space="paper"))
        y += 1.5
        ops.append(_line("A-ANNO-TTLB", (lx, y), (rx, y), space="paper"))
        # Arabic label right, figure left: two runs so bidi never reorders "446.31 m2".
        totals = [("مجموع المساحات الصافية", draft["net_area_total_m2"])]
        if draft["gross_area_outer_faces_m2"] is not None:
            totals.append(("مساحة المسقط حتى الوجه الخارجي للجدران", draft["gross_area_outer_faces_m2"]))
        for label, value in totals:
            row(label, T["note"])
            ops.append(_text("A-ANNO-TEXT", fmt_area(value), (lx, ops[-1]["at"][1]), T["note"], anchor="start", space="paper"))
        rule()
    y = max(y, fy1 - 52.0)
    for note in ("صافي: بين أوجه الجدران · محاور: مستطيل الفراغ في النموذج",
                 "الجدران الداخلية إلى المحور، والخارجية إلى الوجه الخارجي",
                 "اتجاه فتح الأبواب وجهة المفصلات افتراض رسم",
                 "بلا شبكة محاور إنشائية أو أعمدة أو تمديدات"):
        row(note, T["minimum"], layer="A-ANNO-NOTE")
    rule()
    row("Revision %s" % revision_id, 1.5, layer="A-ANNO-NOTE", anchor="start", x=lx)
    row("Model %s…  Provenance %s…" % (model_hash[:16], provenance_hash[:16]), 1.5, layer="A-ANNO-NOTE", anchor="start", x=lx)
    row("Drafting %s…" % draft["drafting_hash"][:16], 1.5, layer="A-ANNO-NOTE", anchor="start", x=lx)
    rule()
    row("ليست للتنفيذ · الامتثال النظامي والإنشائي غير متحقق", T["note"], layer="A-ANNO-NOTE")
    row("CONCEPT PLAN - NOT FOR CONSTRUCTION - COMPLIANCE NOT VERIFIED", T["minimum"], layer="A-ANNO-NOTE")
    return ops


def summary(draft: dict, sheet: dict) -> dict:
    """Small, receipt-friendly description of a drawn level."""
    return {
        "schema": SCHEMA, "scope": SCOPE, "drafting_hash": draft["drafting_hash"],
        "paper": sheet["paper"], "scale": sheet["scale"], "standard_scale": sheet["standard_scale"],
        "units": "m", "wall_thickness_m": draft["wall_thickness_m"], "cut_plane_m": draft["cut_plane_m"],
        "counts": {
            "wall_outlines": len(draft["walls"]["cut"]) + len(draft["walls"]["low"]) + len(draft["walls"]["glazed"]),
            "doors": len(draft["doors"]), "windows": len(draft["windows"]), "docks": len(draft["docks"]),
            "stairs": len(draft["stairs"]), "dimension_chains": len(draft["chains"]), "room_tags": len(draft["tags"]),
        },
        "net_area_total_m2": draft["net_area_total_m2"],
        "gross_area_outer_faces_m2": draft["gross_area_outer_faces_m2"],
        "area_basis": "net = clear area between wall faces; gross = footprint to outer wall faces (drafting measure, not a permit calculation)",
        "drafting_defaults": draft["drafting_defaults"], "not_drawn": draft["not_drawn"],
        "skipped": draft["skipped"],
    }
