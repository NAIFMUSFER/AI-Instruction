# Live warehouse vertical-stage gap — 2026-09-15

Production owner replay on `main` `1256cf17875b481b63625ca42b4038239c586c81` produced `PLAN_GEOMETRY_DIMENSION_NOT_SPECIFIED` while generating a warehouse Design Option. The brief deliberately leaves final clear height / structural system / wall build-up to later engineering.

This is a stage-boundary defect, not permission to invent defaults. The current shared `_geometry()` reports missing `floor_height`, `wall_h`, and `wall_t`; `acs_workspace_service.generate_and_save()` converts the first geometry finding into a fatal durable generation error before the draft can be reviewed. That is appropriate for an approved downstream 3D handoff, but too strict for a pre-approval warehouse 2D/Design Option when vertical engineering values are explicitly unknown.

Required behavior:

1. Preserve `floor_height`, `wall_h`, `wall_t` as unknown when not supplied/verified. Do not normalize them to arbitrary values.
2. Warehouse Brief/Program/Constraints/Design Options/2D review may proceed using known horizontal/operational geometry when those vertical values are unknown.
3. The review UI must surface the unknown vertical values as unresolved constraints, not hide them.
4. Engineer approval for a baseline that is intended to feed BIM/3D must fail closed until downstream-required vertical geometry is explicit and validated.
5. `tools/acs_plan_handoff.py` remains strict: no 3D compiler default may invent approved geometry.
6. Keep real horizontal failures (`OUTSIDE_SITE`, `ROOM_OVERLAP`, invalid rects, unresolved spaces) fatal for the candidate; do not weaken them.
7. Regression must replay a warehouse candidate with valid site/rooms and missing vertical engineering values: draft review succeeds with unresolved vertical constraints; approval/3D remains blocked. A second regression with explicit valid vertical values must preserve them byte-for-byte into approved handoff.

This document records live evidence only. It does not claim the implementation is fixed.
