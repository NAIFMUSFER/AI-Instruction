# Generation geometry failure diagnostics

The owner's first observed generation failed at 2026-09-14 04:01 UTC with
`INVALID_GEOMETRY` and no saved revision. Its rejected candidate and detailed
geometry report were not retained, so the exact defect cannot be reconstructed.
Do not claim the historical candidate was repaired or infer a specific defect.

Follow-up production planner logs establish 91 outlined zones, chunk output
ceiling splits, then repeated ACS_RATE_LIMITED chunk fallbacks at 04:01:24 UTC.
The local consented request budget formerly raised generic ACS_RATE_LIMITED;
the planner swallowed it as a recoverable chunk failure and produced unresolved
rectangles. Those then reached the projection gate as invalid geometry.

The budget now has a dedicated non-retryable ACS_PROVIDER_BUDGET_EXHAUSTED code,
preserved across the isolated worker error envelope. Chunk planning propagates
it immediately rather than creating unresolved fallback geometry or iterating
over the remaining chunks. The configured 1–12 call ceiling is unchanged.

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

Validation: 13 connected-workspace tests passed locally, including overlap,
out-of-site and unresolved-space candidates, no save or retry on rejection,
existing-head preservation, durable receipt reload and private-text exclusion.
JavaScript syntax and measured bundle/document consistency were checked.
Budget coverage verifies terminal propagation, no fallback, unchanged consumed
count, non-retryability, and preservation through the worker classification boundary.
