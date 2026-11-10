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
