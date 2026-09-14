# Bounded draft overlap correction

Owner screenshots show PLAN_GEOMETRY_ROOM_OVERLAP after the diagnostic release.
They do not contain the rejected candidate, so its exact coordinates are unknown.

Before returning a new plan from the isolated worker, inspect its canonical
structure and geometry. Only a detail-free draft whose sole geometry defect is
room overlap is eligible for one correction proposal. It runs inside the same
approved provider-call budget and is skipped when that budget is exhausted.
Provider fallback, if configured, still consumes that same budget.

The correction response can specify only x/z positions keyed by template and
room ID. All rooms must occur exactly once. Sizes, roles, names, site, levels,
authority and other model data are retained by the host, not rewritten from the
provider response. Rooms with placed doors/windows/points or unsupported extra
fields are excluded from this narrow operation. No historical saved revision is
edited. If the candidate still has any geometry defect the original rejection
remains; there is no correction loop or budget increase.

The parent still applies current-head, inherited locks, geometry, projection,
revision admission and authenticated persistence checks. Passing geometry alone
is not architectural quality, approval or regulatory compliance.

Local verification: 14 connected-workspace tests pass, including bounded
correction, exhausted budget, room omission/duplication/identity tampering,
forbidden response fields, residual overlap, outside-site placement and
preservation of original model data. No live paid provider generation was run.
CI and deployment remain pending for the submitted change.
