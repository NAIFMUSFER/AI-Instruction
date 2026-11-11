# -*- coding: utf-8 -*-
"""Canonical flat-roof level with parapets.

A roof is model data, not a rendering effect. This module appends one explicit
roof level to a canonical building model so that every derived output (3D, IFC,
plans, quantities) reads the same roof from the same revision:

  * the level carries ``kind: "roof"`` and ``auto: true``; ``acs_arch`` already
    reports such a level as a ROOF, ``occupied_floor: False``, source
    ``system_default`` — it is never counted as a storey or as floor area;
  * its rooms mirror the rectangles of the top occupied level, so an L-shaped
    building gets an L-shaped roof and no roof covers an open recess;
  * every roof room uses the existing per-room ``wall_h`` to raise a parapet on
    its exterior edges only. No new geometry code is involved: both compilers
    (Python and browser) already build per-room wall heights.

Nothing here is a structural, drainage, waterproofing or code-compliance design.
The function is pure and deterministic and refuses to run twice.
"""
import copy

EDGES = ("N", "S", "W", "E")
ROOF_ROOM_PREFIX = "roof_"
DEFAULT_PARAPET_H = 0.9
_EPS = 1e-6


def is_roof_level(level):
    """Same reading as acs_arch: explicit kind, or a template named as a roof."""
    kind = str((level or {}).get("kind") or "").lower()
    if kind:
        return kind == "roof"
    return ("roof" in str((level or {}).get("template") or "").lower()
            or "سطح" in str((level or {}).get("name") or ""))


def has_roof_level(model):
    return any(is_roof_level(l) for l in (model.get("levels") or []))


def _rect(room):
    r = (room or {}).get("rect")
    if not isinstance(r, (list, tuple)) or len(r) != 4:
        return None
    try:
        x, z, w, d = (float(v) for v in r)
    except (TypeError, ValueError):
        return None
    return (x, z, w, d) if (w > 0 and d > 0) else None


def _edge_span(edge, rect):
    """(axis, fixed coordinate, start, end) of one edge, matching the compiler:
    N is the low-z side, S the high-z side, W low-x, E high-x."""
    x, z, w, d = rect
    if edge == "N":
        return ("x", z, x, x + w)
    if edge == "S":
        return ("x", z + d, x, x + w)
    if edge == "W":
        return ("z", x, z, z + d)
    return ("z", x + w, z, z + d)


def _shared_length(edge, rect, others):
    """Length of this edge that lies against another rectangle's opposite edge."""
    axis, fixed, a0, a1 = _edge_span(edge, rect)
    opposite = {"N": "S", "S": "N", "W": "E", "E": "W"}[edge]
    total = 0.0
    for other in others:
        o_axis, o_fixed, b0, b1 = _edge_span(opposite, other)
        if o_axis != axis or abs(o_fixed - fixed) > _EPS:
            continue
        total += max(0.0, min(a1, b1) - max(a0, b0))
    return total


def _elevation(level, floor_height):
    if level.get("elevation") is not None:
        return float(level["elevation"])
    return float(level.get("index", 0)) * float(floor_height)


def add_flat_roof_level(model, parapet_h=DEFAULT_PARAPET_H):
    """Return ``(new_model, report)``; the input model is not modified.

    Raises ValueError with a stable code when a roof cannot be added honestly.
    """
    try:
        parapet_h = float(parapet_h)
    except (TypeError, ValueError):
        raise ValueError("ROOF_PARAPET_HEIGHT_INVALID")
    if not (0.0 <= parapet_h <= 2.0):
        raise ValueError("ROOF_PARAPET_HEIGHT_INVALID")
    if not isinstance(model, dict):
        raise ValueError("ROOF_MODEL_INVALID")
    if has_roof_level(model):
        raise ValueError("ROOF_LEVEL_EXISTS")
    out = copy.deepcopy(model)
    levels = out.get("levels") or []
    floors = out.get("floors") or {}
    occupied = [l for l in levels if isinstance(l, dict) and l.get("template") in floors]
    if not occupied:
        raise ValueError("ROOF_NO_OCCUPIED_LEVEL")
    top = max(occupied, key=lambda l: int(l.get("index", 0)))
    top_rooms = [(r, _rect(r)) for r in (floors[top["template"]].get("rooms") or [])]
    top_rooms = [(r, rc) for r, rc in top_rooms if rc is not None]
    if not top_rooms:
        raise ValueError("ROOF_TOP_LEVEL_HAS_NO_ROOMS")

    wall_h = float(out.get("wall_h", 3.0))
    floor_height = float(out.get("floor_height", wall_h + 0.2))
    top_wall = max(float(r.get("wall_h", wall_h)) for r, _ in top_rooms)
    # The roof slab follows the building's own storey convention when that clears
    # the top walls; otherwise it sits directly on them (slab is 0.15 m thick and
    # hangs below its level elevation, exactly like every floor slab).
    rise = floor_height if floor_height >= top_wall + 0.15 - _EPS else top_wall + 0.15
    roof_elevation = round(_elevation(top, floor_height) + rise, 6)

    template = "roof"
    n = 2
    while template in floors:
        template = "roof_%d" % n
        n += 1
    rects = [rc for _, rc in top_rooms]
    roof_rooms, gaps, parapet_m = [], [], 0.0
    used = set()
    for room, rc in top_rooms:
        others = [o for o in rects if o is not rc]
        walls = []
        for edge in EDGES:
            _, _, a0, a1 = _edge_span(edge, rc)
            length = a1 - a0
            shared = _shared_length(edge, rc, others)
            if shared <= _EPS:
                walls.append(edge)
                parapet_m += length
            elif shared < length - _EPS:
                # A whole-edge parapet would cross the neighbouring roof deck, so a
                # partly shared edge is left open and reported, never guessed.
                gaps.append({"room_id": room.get("id"), "edge": edge,
                             "open_length_m": round(length - shared, 6)})
        base = ROOF_ROOM_PREFIX + str(room.get("id") or "deck")
        rid, k = base, 2
        while rid in used:
            rid = "%s_%d" % (base, k)
            k += 1
        used.add(rid)
        roof_rooms.append({
            "id": rid, "name": "سطح", "role": "roof_deck", "auto": True,
            "rect": [rc[0], rc[1], rc[2], rc[3]],
            "walls": walls if parapet_h > 0 else "none",
            "wall_h": parapet_h if parapet_h > 0 else None,
            "doors": [], "windows": [], "points": [],
        })
        if parapet_h <= 0:
            roof_rooms[-1].pop("wall_h")
    floors[template] = {"rooms": roof_rooms}
    levels.append({"index": int(top.get("index", 0)) + 1, "template": template,
                   "kind": "roof", "auto": True, "name": "السطح",
                   "elevation": roof_elevation})
    out["levels"], out["floors"] = levels, floors
    report = {
        "schema": "acs.roof/1", "form": "flat", "source": "system_default",
        "level_index": int(top.get("index", 0)) + 1, "template": template,
        "elevation_m": roof_elevation, "parapet_height_m": parapet_h,
        "parapet_length_m": round(parapet_m if parapet_h > 0 else 0.0, 6),
        "deck_area_m2": round(sum(rc[2] * rc[3] for rc in rects), 6),
        "parapet_gaps": gaps, "occupied_floor": False,
        "not_verified": ["structure", "drainage", "waterproofing", "roof access", "code compliance"],
    }
    return out, report


# ---------------------------------------------------------------------------
# Generation and editing journey
# ---------------------------------------------------------------------------
def _auto_roof_levels(model):
    return [l for l in ((model or {}).get("levels") or [])
            if isinstance(l, dict) and l.get("kind") == "roof" and l.get("auto") is True]


def _parapet_of(model):
    for level in _auto_roof_levels(model):
        for r in (((model.get("floors") or {}).get(level.get("template")) or {}).get("rooms") or []):
            if isinstance(r, dict) and r.get("wall_h") is not None:
                try:
                    return float(r["wall_h"])
                except (TypeError, ValueError):
                    break
            if isinstance(r, dict) and r.get("walls") == "none":
                return 0.0
    return DEFAULT_PARAPET_H


def _disclosure(parapet_h):
    # Deliberately constant across edits: room locks freeze everything outside
    # ``floors`` (levels and meta included), so this record must not carry figures
    # that move when an unlocked room on the top storey is edited.
    return {"schema": "acs.roof/1", "source": "system_default", "form": "flat",
            "parapet_height_m": float(parapet_h), "occupied_floor": False}


def with_default_roof(model, parapet_h=DEFAULT_PARAPET_H):
    """Every generated building gets the same disclosed default: a flat roof with
    a parapet. Returns ``(model, report, reason)``.

    The roof is recorded in ``meta.acs_roof`` as a system default, so the review
    can show it as an assumption. A model that already declares a roof, or one a
    roof cannot honestly be added to, is returned unchanged with the reason.
    """
    if not isinstance(model, dict):
        return model, None, "ROOF_MODEL_INVALID"
    if has_roof_level(model):
        return model, None, "ROOF_LEVEL_EXISTS"
    try:
        out, report = add_flat_roof_level(model, parapet_h)
    except ValueError as exc:
        return model, None, str(exc)
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    meta = dict(meta)
    meta["acs_roof"] = _disclosure(report["parapet_height_m"])
    out["meta"] = meta
    return out, report, None


def carry_auto_roof(before_model, candidate):
    """After an edit, keep the automatic roof in step with the top storey.

    Only a roof that the previous revision held as ``auto`` is rebuilt. If the
    previous revision had no automatic roof (never added, or removed by the
    user), the candidate is returned untouched: an edit never re-adds a roof the
    user took away, and never touches a roof the user authored.
    """
    previous = _auto_roof_levels(before_model)
    if not previous or not isinstance(candidate, dict):
        return candidate
    height = _parapet_of(before_model)
    templates = {l.get("template") for l in previous}
    out = copy.deepcopy(candidate)
    out["levels"] = [l for l in (out.get("levels") or [])
                     if not (isinstance(l, dict) and (l.get("template") in templates
                             or (l.get("kind") == "roof" and l.get("auto") is True)))]
    floors = out.get("floors") if isinstance(out.get("floors"), dict) else {}
    still_used = {l.get("template") for l in out["levels"] if isinstance(l, dict)}
    for template in templates - still_used:
        floors.pop(template, None)
    out["floors"] = floors
    meta = dict(out.get("meta")) if isinstance(out.get("meta"), dict) else {}
    meta.pop("acs_roof", None)
    if not has_roof_level(out):
        try:
            out, report = add_flat_roof_level(out, height)
            meta["acs_roof"] = _disclosure(height)
        except ValueError as exc:
            meta["acs_roof"] = {"schema": "acs.roof/1", "source": "system_default",
                                "omitted": str(exc)}
    if meta or isinstance(candidate.get("meta"), dict):
        out["meta"] = meta
    return out


def is_auto_roof_template(model, template):
    return any(l.get("template") == template for l in _auto_roof_levels(model))
