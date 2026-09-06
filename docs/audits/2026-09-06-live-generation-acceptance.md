# Live generation acceptance — 2026-09-06

## Executive summary

One synthetic production generation was explicitly authorized and submitted to
`/v1/understand`. The request returned HTTP 200 with `ok=true` after 95.087 seconds.
The returned model preserved the requested site, level, space rectangles and door
dimensions. **Full engineering acceptance did not pass.** The returned data has
unknown-data and provenance defects recorded below.

During preparation, the live verifier was found to return exit 0 for a correctly
classified failed generation. This change fixes that verification defect without
changing the deployed generation engine or weakening any release gate.

## Deployment and request evidence

- Tested deployment: `ca2f98a450a36468431c5f87f2788420d9903f8b`.
- Backend: `https://acs-engine.onrender.com`.
- Request ID: `req_acs_acceptance_20260906_warehouse_01`.
- Submitted: `2026-09-06T05:15:40.090647+00:00`.
- Response completed: `2026-09-06T05:17:15.177564+00:00`.
- One client submission, no client retry, `deep=false`, `strict=true`.
- Synthetic warehouse: 20 × 15 m, one level, 4 m floor height; storage rectangle
  `[0, 0, 15, 15]`, reception rectangle `[15, 0, 5, 15]`; two doors with nominal
  dimensions 2 × 2.4 m and 1.2 × 2.1 m. Wall/slab thickness, materials and window
  positions were explicitly left unspecified.
- Reported strategy: `single`; stages 1; escalations 0; stop reason `end_turn`;
  input tokens 4,766; output tokens 5,855. These are response telemetry, not a
  provider invoice or independently verified count of every upstream attempt.
- Actual response echoed the request ID and allowed the configured frontend origin.

## Acceptance findings

The captured response was checked against the input and exercised with the local
Python authoring/documentation engines at the same source tree. The combined
acceptance matrix recorded **34 passing and 6 failing checks**. This does not mean
34 browser checks: local engine behavior is separate from live HTTP evidence.

| Finding | Observed evidence | Status |
| --- | --- | --- |
| Requested geometry | Site 20 × 15 m; one level; two exact room rectangles; both nominal door dimensions preserved | PASS |
| Unknown wall thickness | `wall_t: 0.0` despite an explicitly unspecified thickness; no field status or source in the raw model | FAIL |
| Door offset provenance | Offsets 2.5 and 7.5 were not specified in the input; no inference provenance on the raw door records; the compiler labels the offsets stated | FAIL |
| Stable opening IDs | Raw door records have no IDs; later derived IDs use array positions | FAIL |
| Architectural geometry | Seven `WALL_NEGATIVE_THICKNESS` issues emitted by the architecture compiler for the zero thickness | FAIL |
| Issue propagation | Live response reports `issues: 0`; the legacy validator and authoring integrity validator also report no issue | FAIL |
| Numerical life-safety proposals | Proposed four exits, two extinguishers and an assembly point without a cited authoritative rule/version; proposals remained uncommitted | FAIL |
| Authority boundary | Compliance is `NOT_EVALUATED`; all five engineering proposals remain unapplied and require confirmation | PASS |
| Local authoring | Rename preview, cancel, commit, undo and redo work on a copy of the captured model; commit records actor and timestamp | PASS, local engine scope |
| Local persistence | Serialized project, full revision models and history survive a disk round trip; undo still works | PASS, local disk scope |
| Local documentation | Seven deterministic, model-hash-bound SVG views and room/door/window schedule counts; model remains unchanged | PASS, diagnostic output only |

These drawings preserve the captured model's defects. They are explicitly marked
as model-derived documentation, not construction drawings, and are not an
engineering approval.

## Browser verification

The connected cloud browser could not create a WebGL context. Its console reports
`GL_VENDOR = Disabled`, `GL_RENDERER = Disabled`, and `Error creating WebGL context`.
One reload produced the same limitation. The visible boot banner suggests a CDN
failure even though the console identifies graphics initialization failure.

**BROWSER NOT VERIFIED for this generated model.** No generation was submitted
through the blocked UI. Editing controls, browser persistence, authenticated
server-side project storage and exports through the UI were not exercised.
Earlier successful Chromium tests used declared fixtures and do not establish
that this new generated model renders correctly.

## Verifier remediation

Previously, `--generation` treated a valid error envelope as a passing assertion
without counting the underlying generation as failed. A 429, 502 or 503 response
could therefore leave the script's failure count at zero. HTTP 200 bodies with a
missing or false `ok` field could also pass all existing structural checks.

The verifier now requires HTTP 200 and boolean `ok=true` before entering the
model-success branch. A well-formed error can still pass its error-contract check,
but the generation itself fails and the script exits 1. Free checks continue to
skip generation explicitly. No paid request is retried by this change.

`test_live_generation_verdict.py` runs the actual verifier entry point with
controlled DNS/TLS/HTTP test doubles. It makes no network or provider call. Ten
tests cover free mode, successful generation, rate limits, provider/backend
failures, false/missing `ok`, invalid JSON, timeout and an empty model. CI now runs
this regression through the existing required suite runner.

## Tests executed during implementation

```bash
python3 tests/remediation/test_live_generation_verdict.py
python3 tests/remediation/test_ci_gate.py
python3 tests/phase9_2/test_generation_budget.py
git diff --check
```

- New regression against the original verifier: **10 tests, 5 passed, 5 failed**.
- Same regression after the fix: **10 tests, 10 passed, 0 failed**.
- Existing CI gate regression: **78 passed, 0 failed**.
- Existing generation budget regression: **74 passed, 0 failed**.
- Whitespace/diff check: exit 0.
- Remote CI for this new commit: **NOT VERIFIED at document creation**.
- Deployment of this verifier fix: **PENDING**; production remains on the tested
  merge SHA until a separately approved merge/deployment.

## Security, limits and next actions

No secrets, provider settings, CSP, CORS, application geometry, budgets or
production data were changed. The input contains synthetic data only. No server
project-storage success or monetary billing amount is claimed.

The next product change needs a compatible uncertainty/provenance contract across
generation, canonical validation, architecture compilation and documentation.
It should retain unknown thickness as unknown, identify inferred offsets, assign
stable opening IDs, propagate compiler issues, and replace uncited numeric safety
recommendations with unresolved requirements. None of those six acceptance
failures is closed by this verifier-only fix.

Definition of done for this fix: failed generations cannot yield a green live
verification, free checks remain free, the new regression and existing required
CI pass, and the known product-level failures remain explicitly documented.
