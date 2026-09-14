# Generation geometry failure diagnostics

The owner's first observed generation failed at 2026-09-14 04:01 UTC with
`INVALID_GEOMETRY` and no saved revision. Its rejected candidate and detailed
geometry report were not retained, so the exact defect cannot be reconstructed.
Do not claim the historical candidate was repaired or infer a specific defect.

Generation now runs the same canonical geometry validator before projection
admission. If it fails, the first deterministic validator category becomes a
bounded `PLAN_GEOMETRY_*` delivery error code. The durable job receipt retains
that code; the authenticated response derives an Arabic message from a fixed
server-owned allowlist. It does not expose arbitrary provider/exception content.
Legacy `INVALID_GEOMETRY` receipts explicitly say their details are unavailable.

This change preserves all admission, approval, export, budget and revision gates.
It does not move rooms, guess dimensions, drop unresolved spaces, retry a paid
request, retain rejected geometry, or claim automatic repair. Multiple defects
may exist: the message identifies the first canonical category only.

Validation: 12 connected-workspace tests passed locally, including overlap,
out-of-site and unresolved-space candidates, no save or retry on rejection,
existing-head preservation, durable receipt reload and private-text exclusion.
JavaScript syntax and measured bundle/document consistency were checked.
