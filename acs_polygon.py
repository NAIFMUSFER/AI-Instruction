"""Straight, simple Building boundaries in site-local X/Z metres.

`polygon` is authoritative; `rect` is its bounding box, never replacement geometry.
The sweep returns convex, disjoint cells of a union minus holes. Splitting at
edge intersections makes it valid for concave, diagonal and overlapping rings.
No rasterization, resizing, origin shift or input mutation is performed.
"""
import math

EPS = 1e-7  # metres; geometric coincidence tolerance, not a design allowance


def edges(ring):
    return list(zip(ring, ring[1:] + ring[:1]))


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def signed_area(ring):
    return sum(a[0]*b[1]-b[0]*a[1] for a, b in edges(ring))/2


def on_segment(p, a, b):
    length = math.hypot(b[0]-a[0], b[1]-a[1])
    return (abs(cross(a, b, p)) <= EPS * max(length, EPS)
            and min(a[0], b[0])-EPS <= p[0] <= max(a[0], b[0])+EPS
            and min(a[1], b[1])-EPS <= p[1] <= max(a[1], b[1])+EPS)


def intersection(a, b, c, d):
    dx, dz, ex, ez = b[0]-a[0], b[1]-a[1], d[0]-c[0], d[1]-c[1]
    det = dx*ez-dz*ex
    if abs(det) <= EPS * max(math.hypot(dx, dz), math.hypot(ex, ez), EPS):
        return None
    t = ((c[0]-a[0])*ez-(c[1]-a[1])*ex)/det
    u = ((c[0]-a[0])*dz-(c[1]-a[1])*dx)/det
    if -EPS <= t <= 1+EPS and -EPS <= u <= 1+EPS:
        return [a[0]+t*dx, a[1]+t*dz]
    return None


def ring_validated(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        raise ValueError("POLYGON_INVALID: at least three X/Z vertices are required")
    ring = []
    for p in raw:
        if (not isinstance(p, (list, tuple)) or len(p) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in p)):
            raise ValueError("POLYGON_INVALID: vertices must be finite numeric X/Z pairs")
        ring.append([float(p[0]), float(p[1])])
    if ring[0] == ring[-1]:
        ring.pop()  # explicit closing vertex has the same meaning; caller is unchanged
    if len(ring) < 3:
        raise ValueError("POLYGON_INVALID: fewer than three distinct vertices")
    segments = edges(ring)
    for i, (a, b) in enumerate(segments):
        if math.dist(a, b) <= EPS:
            raise ValueError("POLYGON_INVALID: zero-length edge")
        prev = ring[i-1]
        if on_segment(b, prev, a) or on_segment(prev, a, b):
            raise ValueError("POLYGON_INVALID: adjacent edges overlap")
        for j in range(i+1, len(segments)):
            if j == i+1 or (i == 0 and j == len(segments)-1):
                continue
            c, d = segments[j]
            if (intersection(a, b, c, d) is not None or on_segment(a, c, d)
                    or on_segment(b, c, d) or on_segment(c, a, b) or on_segment(d, a, b)):
                raise ValueError("POLYGON_INVALID: boundary intersects itself")
    if abs(signed_area(ring)) <= EPS*EPS:
        raise ValueError("POLYGON_INVALID: boundary has no area")
    return ring


def rect_ring(rect):
    x, z, w, d = rect
    return [[x, z], [x+w, z], [x+w, z+d], [x, z+d]]


def room_ring(room):
    if "polygon" not in room:
        return rect_ring(room["rect"])
    ring = ring_validated(room["polygon"])
    xs, zs = zip(*ring)
    bbox = [min(xs), min(zs), max(xs)-min(xs), max(zs)-min(zs)]
    rc = room.get("rect")
    if (not isinstance(rc, (list, tuple)) or len(rc) != 4
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in rc)
            or any(abs(a-b) > EPS for a, b in zip(rc, bbox))):
        raise ValueError("POLYGON_RECT_MISMATCH: rect must equal the polygon bounding box")
    return ring


def contains_point(ring, p):
    inside = False
    for a, b in edges(ring):
        if on_segment(p, a, b):
            return True
        if (a[1] > p[1]) != (b[1] > p[1]):
            if p[0] < a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]):
                inside = not inside
    return inside


def edge_index(room, opening):
    ring = room_ring(room)
    index = opening.get("edge_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(ring):
        raise ValueError("POLYGON_OPENING_EDGE_INVALID: edge_index must identify a boundary edge")
    return index


def _z_at(edge, x):
    a, b = edge
    return a[1]+(x-a[0])*(b[1]-a[1])/(b[0]-a[0])


def _intervals(rings, x):
    intervals = []
    for ring in rings:
        crossings = sorted([( _z_at(e, x), e) for e in edges(ring)
                            if min(e[0][0], e[1][0]) < x < max(e[0][0], e[1][0])],
                           key=lambda item: item[0])
        for i in range(0, len(crossings)-1, 2):
            intervals.append([crossings[i][1], crossings[i+1][1]])
    intervals.sort(key=lambda pair: _z_at(pair[0], x))
    merged = []
    for lo, hi in intervals:
        if merged and _z_at(lo, x) <= _z_at(merged[-1][1], x)+EPS:
            if _z_at(hi, x) > _z_at(merged[-1][1], x):
                merged[-1][1] = hi
        else:
            merged.append([lo, hi])
    return merged


def cells(rings, holes=()):
    """Disjoint convex cells covering union(rings) minus union(holes)."""
    segments = [e for ring in list(rings)+list(holes) for e in edges(ring)]
    cuts = [p[0] for ring in list(rings)+list(holes) for p in ring]
    for i, (a, b) in enumerate(segments):
        for c, d in segments[i+1:]:
            hit = intersection(a, b, c, d)
            if hit is not None:
                cuts.append(hit[0])
    xs = []
    for x in sorted(cuts):
        if not xs or x-xs[-1] > EPS:
            xs.append(x)
    out = []
    for left, right in zip(xs, xs[1:]):
        mid = (left+right)/2
        spans = _intervals(rings, mid)
        for hlo, hhi in _intervals(holes, mid):
            remaining = []
            for lo, hi in spans:
                if _z_at(hhi, mid) <= _z_at(lo, mid)+EPS or _z_at(hlo, mid) >= _z_at(hi, mid)-EPS:
                    remaining.append([lo, hi])
                    continue
                if _z_at(hlo, mid) > _z_at(lo, mid)+EPS:
                    remaining.append([lo, hlo])
                if _z_at(hhi, mid) < _z_at(hi, mid)-EPS:
                    remaining.append([hhi, hi])
            spans = remaining
        for lo, hi in spans:
            points = [[left, _z_at(lo, left)], [right, _z_at(lo, right)],
                      [right, _z_at(hi, right)], [left, _z_at(hi, left)]]
            clean = []
            for p in points:
                if not clean or math.dist(p, clean[-1]) > EPS:
                    clean.append(p)
            if len(clean) > 1 and math.dist(clean[0], clean[-1]) <= EPS:
                clean.pop()
            if len(clean) >= 3 and signed_area(clean) > EPS*EPS:
                out.append(clean)
    return out
