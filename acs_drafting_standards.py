"""Machine-readable drafting and dimensional standards for ACS plans.

One small table that the drawing exporters use today and that planners and
checks can import later. Every number is in SI units (metres, square metres,
millimetres on paper where named ``*_mm``) and carries its basis:

* ``CODE_REFERENCE`` values come from the model codes that the Saudi Building
  Code adapts (SBC 201 is based on the 2015 IBC; SBC 1101 is the residential
  code). They are cited, not certified: confirm against the adopted SBC text
  before a value is used as a pass/fail rule.
* ``PRACTICE`` values are common Saudi/Gulf construction practice (block sizes,
  nominal door leaves). They are planning defaults, not legal minimums.
* ``DRAFTING_CONVENTION`` values decide how a drawing looks (layers, pen
  widths, text heights, scales). They never change canonical geometry.

Research notes and source links: ``docs/research/cad_drafting_standards.md``.
Stdlib only, no I/O: safe to import from ``python -S`` export gates.
"""
from __future__ import annotations

import math

SCHEMA = "acs.drafting-standards/1.0"

SOURCES = {
    "IBC2015": "International Building Code 2015 (basis of SBC 201-2018)",
    "IRC": "International Residential Code R304/R311 (residential model code)",
    "A117": "ICC A117.1 / 2010 ADA Standards 404.2.3 and 403.5.1",
    "SA_BLOCK": "Saudi block suppliers and BOQs: 200 mm external, 100/150 mm partitions",
    "NCS": "US National CAD Standard / AIA CAD Layer Guidelines (referenced by EXPRO)",
    "EXPRO": "EXPRO CAD Standards Procedure EPM-KE0-PR-000008 (ByLayer properties)",
    "ISO128": "ISO 128 line widths in the 1:sqrt(2) series",
    "ISO3098": "ISO 3098-0 lettering heights 1.8/2.5/3.5/5/7/10 mm",
    "ISO5455": "ISO 5455 recommended scales 1:2/1:5/1:10 x 10^n",
    "ISO5457": "ISO 5457 sheet sizes and frame (20 mm filing margin)",
    "PRACTICE": "ACS drafting default; adjustable per office standard",
}


def _rule(value, basis, source, **extra):
    row = {"value": value, "basis": basis, "source": source}
    row.update(extra)
    return row


# ---------------------------------------------------------------------------
# Dimensional standards for planners and checks
# ---------------------------------------------------------------------------
# Minimum *clear* opening widths (door open 90 degrees, face of leaf to stop).
# A nominal leaf is roughly 80-90 mm wider than its clear opening.
DOOR_CLEAR_WIDTH_MIN_M = {
    "egress": _rule(0.813, "CODE_REFERENCE", "IBC2015", note="IBC 1010.1.1: 32 in clear"),
    "dwelling_egress": _rule(0.813, "CODE_REFERENCE", "IRC", note="IRC R311.2: 32 in clear, 78 in high",
                             clear_height_min_m=1.981),
    "accessible": _rule(0.815, "CODE_REFERENCE", "A117", note="32 in clear; 915 mm for openings deeper than 610 mm"),
}

# Nominal leaf widths used when a planner must choose a door size by room use.
DOOR_NOMINAL_LEAF_M = {
    "main_entrance": _rule(1.0, "PRACTICE", "PRACTICE", range_m=[1.0, 1.2]),
    "apartment_entrance": _rule(1.0, "PRACTICE", "PRACTICE"),
    "habitable_room": _rule(0.9, "PRACTICE", "PRACTICE"),
    "bedroom": _rule(0.9, "PRACTICE", "PRACTICE"),
    "kitchen": _rule(0.9, "PRACTICE", "PRACTICE"),
    "bathroom": _rule(0.8, "PRACTICE", "PRACTICE"),
    "closet": _rule(0.7, "PRACTICE", "PRACTICE"),
    "accessible_room": _rule(0.9, "PRACTICE", "A117", note="0.9 m leaf gives about 0.815 m clear"),
}

WALL_THICKNESS_M = {
    "exterior": _rule(0.20, "PRACTICE", "SA_BLOCK", range_m=[0.20, 0.30],
                      note="200 mm insulated block typical; 250-300 mm with cladding or cavity"),
    "interior_partition": _rule(0.15, "PRACTICE", "SA_BLOCK", range_m=[0.10, 0.15]),
    "wet_or_shaft": _rule(0.15, "PRACTICE", "SA_BLOCK", range_m=[0.15, 0.20],
                          note="wet walls carry pipes; shafts and stair cores use 150-200 mm"),
}

STAIR = {
    "general": {
        "riser_max_m": _rule(0.178, "CODE_REFERENCE", "IBC2015", note="IBC 1011.5.2: 7 in maximum"),
        "riser_min_m": _rule(0.102, "CODE_REFERENCE", "IBC2015", note="4 in minimum"),
        "tread_min_m": _rule(0.279, "CODE_REFERENCE", "IBC2015", note="11 in minimum"),
        "width_min_m": _rule(1.118, "CODE_REFERENCE", "IBC2015", note="IBC 1011.2: 44 in; 36 in under 50 occupants"),
        "width_min_small_m": _rule(0.914, "CODE_REFERENCE", "IBC2015"),
        "headroom_min_m": _rule(2.032, "CODE_REFERENCE", "IBC2015", note="80 in"),
    },
    "dwelling": {
        "riser_max_m": _rule(0.196, "CODE_REFERENCE", "IRC", note="IRC R311.7.5.1: 7 3/4 in"),
        "tread_min_m": _rule(0.254, "CODE_REFERENCE", "IRC", note="IRC R311.7.5.2: 10 in"),
        "width_min_m": _rule(0.914, "CODE_REFERENCE", "IRC", note="IRC R311.7.1: 36 in"),
        "headroom_min_m": _rule(2.032, "CODE_REFERENCE", "IRC", note="IRC R311.7.2: 6 ft 8 in"),
    },
    # Blondel comfort rule 2R + T, used as a soft planning check only.
    "comfort_2r_plus_t_m": _rule([0.60, 0.65], "PRACTICE", "PRACTICE"),
}

CORRIDOR_WIDTH_MIN_M = {
    "general": _rule(1.118, "CODE_REFERENCE", "IBC2015", note="IBC Table 1020.2: 44 in"),
    "occupant_load_under_50": _rule(0.914, "CODE_REFERENCE", "IBC2015", note="36 in"),
    "within_dwelling": _rule(0.914, "CODE_REFERENCE", "IRC", note="IRC R311.6: 3 ft hallway"),
    "accessible_route": _rule(0.915, "CODE_REFERENCE", "A117", note="interior accessible route"),
    "bed_movement_healthcare": _rule(2.438, "CODE_REFERENCE", "IBC2015",
                                     note="Group I-2 areas for bed movement: 96 in; verify in SBC 201"),
}

HABITABLE_ROOM_MIN = {
    "area_m2": _rule(6.5, "CODE_REFERENCE", "IRC", note="IRC R304.1: 70 sq ft, kitchens excepted"),
    "dimension_m": _rule(2.134, "CODE_REFERENCE", "IRC", note="IRC R304.2: 7 ft in any horizontal direction"),
}

# ---------------------------------------------------------------------------
# Drafting conventions used by the SVG/PDF/DXF exporters
# ---------------------------------------------------------------------------
CUT_PLANE_HEIGHT_M = 1.2          # walls lower than this are drawn uncut (outline only)
DOUBLE_LEAF_MIN_WIDTH_M = 1.4     # openings this wide are drawn as double doors
ISO_LINE_WIDTHS_MM = (0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0)
ISO_TEXT_HEIGHTS_MM = (1.8, 2.5, 3.5, 5.0, 7.0, 10.0, 14.0, 20.0)
# Lettering height h is the capital-letter height (ISO 3098; AutoCAD TEXT height).
# SVG/PDF font sizes are em sizes, so they draw at h / CAP_HEIGHT_RATIO.
CAP_HEIGHT_RATIO = 0.72
TEXT_HEIGHT_MM = {
    "minimum": 1.8, "dimension": 2.5, "note": 2.0, "room_area": 2.5, "room_name": 3.5,
    "subtitle": 3.5, "title": 5.0, "sheet_title": 7.0,
}
PREFERRED_SCALES = (20, 50, 100, 200, 500, 1000, 2000)
PAPER_MM = {"A3": (420.0, 297.0), "A2": (594.0, 420.0), "A1": (841.0, 594.0), "A0": (1189.0, 841.0)}
SHEET_FRAME_MM = {"left": 20.0, "top": 10.0, "right": 10.0, "bottom": 10.0}
TITLE_BLOCK_WIDTH_MM = 90.0
# Preferred (paper, scale) order: a whole floor at 1:100 first, larger paper
# before a smaller scale, and 1:50 only when a small plan fits A3.
SHEET_CANDIDATES = (
    ("A3", 50), ("A3", 100), ("A2", 100), ("A1", 100), ("A3", 200), ("A2", 200),
    ("A1", 200), ("A1", 500), ("A0", 500), ("A0", 1000), ("A0", 2000),
)
DIMENSION = {
    "first_offset_mm": 10.0,   # building face to first dimension line
    "chain_spacing_mm": 7.0,   # between successive dimension lines
    "extension_gap_mm": 2.0,   # gap between object and extension line
    "extension_beyond_mm": 2.0,
    "tick_mm": 2.5,            # 45-degree architectural tick
    "line_overrun_mm": 1.5,
    "text_gap_mm": 1.0,
    "decimals": 2,             # metres to the centimetre
    "margin_mm": 28.0,         # room reserved around a plan for three chains
}

# NCS/AIA layer names (discipline-major-minor). Colour is the AutoCAD index used
# on screen; plotting relies on lineweight (EXPRO asks for ByLayer properties).
# ``svg`` is the paper colour used by the SVG/PDF renderers.
LAYERS = {
    "A-WALL": {"desc": "Walls cut by the plan plane", "aci": 7, "lw": 0.5, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-WALL-PATT": {"desc": "Wall poche (solid fill)", "aci": 8, "lw": 0.13, "lt": "CONTINUOUS", "svg": "#8a8f98"},
    "A-WALL-PRHT": {"desc": "Partial-height walls and parapets (below cut)", "aci": 7, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-DOOR": {"desc": "Door leaves, swings and overhead doors", "aci": 3, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-DOOR-SWNG": {"desc": "Door swing arcs", "aci": 3, "lw": 0.13, "lt": "CONTINUOUS", "svg": "#333333"},
    "A-GLAZ": {"desc": "Windows and glazed partitions", "aci": 4, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-FLOR-STRS": {"desc": "Stair treads, landings, arrows", "aci": 6, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-FLOR-OVHD": {"desc": "Items above the cut plane", "aci": 8, "lw": 0.18, "lt": "DASHED", "svg": "#555555"},
    "A-FLOR-EVTR": {"desc": "Elevator shafts", "aci": 6, "lw": 0.18, "lt": "CONTINUOUS", "svg": "#333333"},
    "A-AREA": {"desc": "Canonical room rectangles (non-plotting, like room boundaries)", "aci": 8, "lw": 0.13,
               "lt": "CONTINUOUS", "svg": "#7b8794", "plot": False},
    "A-AREA-BNDY": {"desc": "Plotted space separation lines where no wall exists", "aci": 8, "lw": 0.18,
                    "lt": "DASHED", "svg": "#5b6b7a"},
    "A-AREA-IDEN": {"desc": "Room areas and clear dimensions", "aci": 2, "lw": 0.18, "lt": "CONTINUOUS", "svg": "#222222"},
    "A-FLOR-IDEN": {"desc": "Room names and numbers", "aci": 2, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-ANNO-DIMS": {"desc": "Dimensions", "aci": 1, "lw": 0.18, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-ANNO-SYMB": {"desc": "North arrow, scale bar, symbols", "aci": 7, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-ANNO-TEXT": {"desc": "Drawing titles and labels", "aci": 7, "lw": 0.25, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-ANNO-NOTE": {"desc": "General notes and disclaimers", "aci": 7, "lw": 0.18, "lt": "CONTINUOUS", "svg": "#111111"},
    "A-ANNO-TTLB": {"desc": "Sheet border and title block", "aci": 7, "lw": 0.35, "lt": "CONTINUOUS", "svg": "#111111"},
    "C-PROP": {"desc": "Canonical site rectangle", "aci": 1, "lw": 0.35, "lt": "PHANTOM", "svg": "#5b6b7a"},
}
# Dash patterns on paper (mm): dash, gap, ... (dot = 0).
LINETYPE_MM = {
    "CONTINUOUS": (),
    "DASHED": (3.0, 1.5),
    "PHANTOM": (12.0, 1.5, 1.5, 1.5, 1.5, 1.5),
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def font_size_mm(cap_height_mm: float) -> float:
    """Em size (SVG font-size, PDF Tf) that gives the ISO lettering height."""
    return float(cap_height_mm) / CAP_HEIGHT_RATIO


def model_size_m(paper_mm: float, scale: int) -> float:
    """Model-space size (metres) that plots at ``paper_mm`` for 1:``scale``."""
    return float(paper_mm) * float(scale) / 1000.0


def scale_bar_length_m(scale: int) -> tuple[float, int]:
    """A round scale-bar length (metres) near 50 mm on paper, and its divisions."""
    for length in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):
        if length * 1000.0 / scale >= 35.0:
            return float(length), (4 if length in (2, 20, 200) else 5)
    return 1000.0, 5


def choose_sheet(width_m: float, depth_m: float) -> dict:
    """Pick the preferred standard paper and scale that hold a plan of this size.

    ``width_m``/``depth_m`` are the plan extents. Room is reserved for three
    dimension chains on every side and for the drawing title below the plan.
    Falls back to A0 at a computed (non-standard) scale for very large plans.
    """
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (width_m, depth_m)):
        raise ValueError("Plan extents must be positive finite metres")
    margin = DIMENSION["margin_mm"]
    frame = SHEET_FRAME_MM
    for paper, scale in SHEET_CANDIDATES:
        pw, ph = PAPER_MM[paper]
        area_w = pw - frame["left"] - frame["right"] - TITLE_BLOCK_WIDTH_MM - 8.0
        area_h = ph - frame["top"] - frame["bottom"] - 8.0
        need_w = width_m * 1000.0 / scale + 2 * margin
        need_h = depth_m * 1000.0 / scale + 2 * margin + 18.0
        if need_w <= area_w and need_h <= area_h:
            return {"paper": paper, "scale": scale, "standard_scale": True,
                    "paper_mm": [pw, ph]}
    pw, ph = PAPER_MM["A0"]
    area_w = pw - frame["left"] - frame["right"] - TITLE_BLOCK_WIDTH_MM - 8.0 - 2 * margin
    area_h = ph - frame["top"] - frame["bottom"] - 8.0 - 2 * margin - 18.0
    scale = int(math.ceil(max(width_m * 1000.0 / area_w, depth_m * 1000.0 / area_h)))
    return {"paper": "A0", "scale": scale, "standard_scale": False, "paper_mm": [pw, ph]}


def door_clear_width_ok(clear_width_m: float, use: str = "egress") -> bool:
    """True when a clear opening meets the cited minimum for ``use``."""
    return float(clear_width_m) + 1e-9 >= DOOR_CLEAR_WIDTH_MIN_M[use]["value"]


def stair_ok(riser_m: float, tread_m: float, kind: str = "dwelling") -> dict:
    """Return riser/tread findings for a stair against the cited table row."""
    row = STAIR[kind]
    out = {"riser_ok": float(riser_m) <= row["riser_max_m"]["value"] + 1e-9,
           "tread_ok": float(tread_m) + 1e-9 >= row["tread_min_m"]["value"]}
    if "riser_min_m" in row:
        out["riser_ok"] = out["riser_ok"] and float(riser_m) + 1e-9 >= row["riser_min_m"]["value"]
    low, high = STAIR["comfort_2r_plus_t_m"]["value"]
    out["comfort_ok"] = low - 1e-9 <= 2 * float(riser_m) + float(tread_m) <= high + 1e-9
    return out


def corridor_ok(width_m: float, context: str = "within_dwelling") -> bool:
    return float(width_m) + 1e-9 >= CORRIDOR_WIDTH_MIN_M[context]["value"]
