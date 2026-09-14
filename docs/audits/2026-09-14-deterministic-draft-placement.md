# Bounded numerical placement before provider correction

The owner job ddaa1081-e5ee-4e97-a20d-e49b82248b2b failed after the PR111
release. Render logs confirm its correction provider call completed, followed
by a ROOM_OVERLAP receipt. Its candidate coordinates were not retained, so the
exact remaining geometry and feasibility cannot be inferred.

Eligible detail-free, single-level/single-template overlap drafts now first try
numerical position placement. The search prefers positions close to the original,
tries three fixed room orders, and uses room/site edges as candidate positions.
It preserves every room's dimensions, orientation, identity and other fields.
There are at most 64 rooms and 100000 intersection comparisons. Failed greedy
search is not reported as mathematical infeasibility; existing bounded provider
correction remains available. A sum of room areas larger than the site is a
separate provable capacity conflict and stops before another provider call.

The existing canonical validator caps issue output at 256 plus an omission marker.
That marker does not block a local attempt when the visible defects are overlap;
full geometry validation of the proposed result is still required. Detailed
rooms and unsupported fields remain excluded. Multi-level placement stays out
of scope because vertical relationships require a separate contract.

The parent still enforces authority, inherited locks, current-head checks,
geometry/projection admission and revision persistence. Layout feasibility does
not prove requested adjacency, access, operational quality, approval or regulatory
compliance. No saved baseline or historical failed job is modified.

Local verification: 17 connected-workspace tests pass. Added coverage checks
24 synthetic overlapping rooms on a 100x150 site (not the historical model),
repeatable placement, no provider usage even with an exhausted budget, immutable
input/dimensions/fields, area over-capacity, detailed-room exclusion and multi-level
exclusion. Existing provider-correction contract tests explicitly isolate the
fallback from local placement. No live paid generation was run.
