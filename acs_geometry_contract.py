"""Small canonical geometry rules shared by derived consumers (metres, X/Z plan)."""
import math

EDGES = ('N', 'S', 'E', 'W')
ADMIN_ROLES = ('office', 'admin', 'it', 'staff', 'maintenance', 'meeting')

def wall_edges(room, industrial=False):
    value = room.get('walls')
    if isinstance(value, list):
        if any(e not in EDGES for e in value) or len(set(value)) != len(value):
            raise ValueError('Invalid explicit room wall edges')
        return tuple(value)
    if value in ('none', 'line'):
        return ()
    if not value and industrial and room.get('role') and room['role'] not in ADMIN_ROLES:
        return ()
    return EDGES

def parapet_spans(room):
    """Wall spans along part of an edge (a roof parapet over an open stretch).

    Each span is (edge, start, end), offsets in metres from the edge's low end.
    Only a room with explicit wall edges may carry spans; invalid data fails closed.
    Twin of ``_aParapetSpans`` in public/app/core/standards.js.
    """
    value = room.get('parapet_spans')
    if value is None:
        return ()
    if not isinstance(room.get('walls'), list) or not isinstance(value, list):
        raise ValueError('Invalid parapet spans')
    rect = room.get('rect')
    out = []
    for span in value:
        if not isinstance(span, dict) or span.get('edge') not in EDGES or span['edge'] in room['walls']:
            raise ValueError('Invalid parapet spans')
        start, end = span.get('start_m'), span.get('end_m')
        if (type(start) not in (int, float) or type(end) not in (int, float) or
                not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end):
            raise ValueError('Invalid parapet spans')
        length = rect[2] if span['edge'] in ('N', 'S') else rect[3]
        if end > float(length) + 1e-6:
            raise ValueError('Invalid parapet spans')
        out.append((span['edge'], float(start), float(end)))
    return tuple(out)


def level_elevation(level, floor_height):
    value = level.get('elevation')
    if value is None:
        value = level['index'] * floor_height
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('Level elevation must be a finite metric value')
    return float(value)

def rectangle_union(rects):
    """Exact disjoint strips of axis-aligned rectangles; recesses/holes stay empty.

    This describes room coverage, not GFA/NFA or a structural slab specification.
    Coordinate cut count is bounded by the caller's canonical room limit.
    """
    if not rects:
        return []
    xs=sorted({float(v) for r in rects for v in (r[0],r[0]+r[2])})
    strips=[]
    for x0,x1 in zip(xs,xs[1:]):
        intervals=sorted((r[1],r[1]+r[3]) for r in rects if r[0] < x1 and r[0]+r[2] > x0)
        merged=[]
        for lo,hi in intervals:
            if merged and lo <= merged[-1][1]: merged[-1][1]=max(hi,merged[-1][1])
            else: merged.append([lo,hi])
        strips.extend([[x0,z0,x1-x0,z1-z0] for z0,z1 in merged])
    return strips


def occupied_template_instances(model: dict) -> tuple[list[str], list[str]]:
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
        if level.get("kind") == "roof":
            # An explicitly declared roof level is a deck, not an occupied storey:
            # it is excluded from every programme measurement (see acs_plan_review).
            continue
        template = level.get("template")
        if not isinstance(template, str) or template not in floors:
            warnings.append("LEVEL_TEMPLATE_NOT_MEASURABLE")
            continue
        templates.append(template)
    return templates, warnings
