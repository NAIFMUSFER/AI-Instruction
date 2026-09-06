# Building polygon boundary

This optional contract extends rectangular rooms without changing their meaning.

- `room.polygon` is a simple closed boundary represented by at least three
  straight-edge `[x,z]` vertices. Coordinates are metres relative to the same site
  origin as `room.rect`. Either winding is accepted. A repeated final vertex is
  optional. Self-intersections, overlapping edges and zero-length edges are invalid.
- `rect=[minX,minZ,maxX-minX,maxZ-minZ]` remains required for room-local objects.
  It is a bounding box, never a substitute for a declared polygon boundary.
- Objects, points and furniture retain their existing coordinates relative to
  `[rect[0],rect[1]]`. Y and level elevations retain the existing metre contract.
- Polygon doors and windows use zero-based `edge_index` and `offset` in metres
  from vertex `i` toward vertex `(i+1) % vertex_count`. Width is centred at that
  offset. Rectangle doors and windows keep the existing N/S/E/W contract.
- A level containing polygons uses the union of its actual room boundaries for
  its floor plate. Architectural core voids are subtracted. The site plane remains
  separate. No change to legacy rectangle-only plate policy is implied.
- No scaling to fit the site and no origin shift is implicit. Curves, holes in
  an individual room boundary and non-planar boundaries need their own explicit
  representation; this contract does not turn them into rectangles.

Implementation status is tracked by C09 in AUDIT-REPORT.md. This document alone
does not claim that every consumer has been migrated.
