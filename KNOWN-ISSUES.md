# Known Issues — preserved for later remediation

## KI-1 · Automatic engineering changes reported by generation (SEMANTIC — OPEN)

**Status:** intentionally NOT fixed in the Phase 9.2 production remediation (that
remediation was packaging/deployment integrity only, per its §10/§11 scope).

**Observed:** during model generation the application reports automatic engineering
adjustments such as: extending site dimensions, changing aisle widths, adding exits,
adding sprinklers/smoke detectors, changing camera counts, resizing zones.

**Why it matters:** these originate in the generation/normalization path (Phase 2–3
resolution rules), not in the presentation layers. Phases 9.1/9.2 are provably
read-only downstream (byte-immutability suites), so this is a separate authority
question: which automatic adjustments are legitimate deterministic normalizations
with declared provenance, and which should instead surface as
`REQUIRES_ENGINEERING_CHANGE` / unresolved diagnostics awaiting explicit user
consent.

**Planned remediation shape (not started):** audit every automatic adjustment site in
the generation path; classify each as (a) declared deterministic normalization with
provenance + issue code, or (b) silent invention to be removed and replaced by an
explicit unresolved report; extend the adversarial suites to pin the chosen contract.
No canonical semantics were modified by the Phase 9.2 remediation.


## KI-2 · Live raster verification requires the deployed environment (OPEN, environmental)

The black-viewport remediation is verified by explicit geometry calculation, by a
real-browser decoded-pixel analyser with positive and negative fixtures, and by a
fixture-loading boot harness. The final confirmation — the actual deployed page
rendering an actual model in actual pixels — cannot run in this sandbox: there is no
vendored Three.js (npm registry blocked) and no network egress to the deployment
(`ERR_TUNNEL_CONNECTION_FAILED`). Run on any networked machine:

    node tests/deploy/verify_page_boot.js https://sprightly-selkie-d906c3.netlify.app/

It prints BOOT and VISUAL MODEL as two separate verdicts and, on failure, names the
responsible layer through the mode matrix and `window.ACS.renderDiagnostics()`.

## KI-3 · The Phase-1 site-wide floor plate overhangs smaller buildings (OPEN, needs approval)

**Status:** identified, measured and reported — deliberately NOT changed.

Since Phase 1 the rendered floor plate of every level spans the whole **site**
rectangle, not the level's own rooms. Above a building smaller than its plot the
upper plates project past the walls with nothing beneath their edges, which is what
reads as a *floating roof/slab*. For a villa on a 30×24 m plot with a 14×13 m
footprint the plate is ≈4.7× the building area.

This is a **declared display convention**, not a transform bug, and it is pinned by
the Phase-4 golden baseline (`MODEL REGRESSION`, exact mesh positions and sizes for
23 fixtures). Changing it alters rendered geometry for every model and every stored
baseline, so it is escalated rather than slipped in.

**Already in place:** the correct extent is computed by the shared contract
(`plate_rect` / `pqPlateRect`), and `window.ACS.alignmentDiagnostics().plate_overhang`
reports, per level, the site plate, the room-union plate, the overhang in metres, the
area ratio, `convention: PHASE1_SITE_WIDE_PLATE` and `change_requires_approval: true`.
Levels above ground that overhang by more than 1 m raise `ALIGN_ROOF_DETACHED`.

**To apply, with approval:** in `public/index.html` replace

    slabStrips(0,0,site.w,site.d,holes)

with

    (function(){const _p=pqPlateRect((fdef.rooms||[]).map(r=>r.rect),
      [0,0,site.w,site.d]).rect;
      return slabStrips(_p[0],_p[1],_p[2],_p[3],holes);})()

then regenerate the Phase-4 baseline and re-run the full chain. Restricting the change
to levels above 0 (keeping the ground plot slab) is the narrower option.

## KI-4 · The live POST contract cannot be exercised from this sandbox (OPEN, environmental)

The backend error contract is verified three ways here: by unit assertions over
`acs_api_errors`, by deterministic parser cases that reproduce the exact production
`Extra data` failure, and by structural analysis of every failure path in
`acs_understand_api.py`. The fourth way — a real HTTP conversation — cannot run in this
sandbox. `pip install fastapi` is blocked (the package index is unreachable), so the
`TestClient` section (د) of `tests/phase9_2/test_backend_contract.py` reports
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED` instead of passing. Outbound HTTP to the
deployment is also blocked (`Tunnel connection failed: 403`), so
`tests/deploy/verify_backend_live.py` exits 2 rather than failing.

DNS and TLS to `acs-engine.onrender.com` **were** verified from here directly (the host
resolves to two addresses and presents a valid certificate), and `GET /` and
`GET /health` were read successfully through the one permitted web-fetch path.

On any networked machine, both gaps close with:

    pip install -r requirements.txt
    python3 tests/phase9_2/test_backend_contract.py     # section د executes
    python3 tests/deploy/verify_backend_live.py         # free, no model call
    python3 tests/deploy/verify_backend_live.py --generation   # spends one call

## KI-5 · A generation abandoned by the 504 deadline keeps running to completion (OPEN, accepted)

`run_bounded` answers the client with `504 ACS_TIMEOUT` and a valid JSON body once
`ACS_REQUEST_TIMEOUT_S` elapses, but the worker thread underneath it cannot be killed —
Python has no thread cancellation. The thread finishes its upstream call and its result is
discarded. Consequences, stated rather than hidden: the model call is still billed, and a
worker slot stays occupied until it returns. Bounded by `ACS_UPSTREAM_TIMEOUT_S` (600s,
shorter than the 840s request deadline) so the thread almost always ends first, and by the
existing per-IP and global rate limits. Moving generation to a separate process pool would
make cancellation real; that is a larger change than this remediation's scope.

## KI-6 · The exact live token numbers behind the truncation were never captured (OPEN, environmental)

The truncation hotfix was built from what is provable offline: the routing rule
(`_should_go_deep`) judged **input** length, so a 55-character warehouse prompt always took
the single-stage path; no output-size estimate existed anywhere; the budget lived in five
unrelated constants; `_balance_json` brace-repaired a `max_tokens` reply instead of
discarding it; and the attempt ladder "recovered" from truncation by retrying the same
request at 16000 then 8000 tokens — a smaller ceiling, which truncates sooner.

What is **not** captured here is the live pair of numbers from the failing run: how many
output tokens the model actually produced before `max_tokens`, and how much of that budget
extended thinking consumed. This sandbox has no API key and no egress to the provider, so
no real generation could be run. That is now instrumented rather than guessed:
`/v1/understand` returns a `generation` block (strategy, size class, per-stage stop reason,
input/output tokens, per-stage ceiling), and `verify_backend_live.py --generation` prints
the full §2 capture. Run it once after deploying and the numbers become evidence.

If that capture shows the *plan* stage itself stopping at `max_tokens` for a small prompt,
the cause is extended thinking eating the budget rather than model size, and the fix is a
`thinking` budget cap rather than more staging — the telemetry now distinguishes the two.

## KI-7 · Stage-1 geometry is authoritative, but the arithmetic autofix still moves rooms afterwards (OPEN, by design, worth naming)

`understand_deep` rejects any `rect` a detail stage tries to rewrite and records
`STAGE_RECT_OVERRIDE_REJECTED`. After the merge, however, `acs_layout.autofix` — which
predates this work — still shifts rooms to resolve overlaps, so the final rect can differ
from stage 1. That is a declared engineering step, not a staged-generation leak, and it sits
squarely inside KI-1's scope (automatic engineering adjustments). It is named here so the
distinction is not mistaken for a stage-authority failure: the test suite asserts the detail
stage's geometry loses, not that the final rect equals stage 1 byte for byte.
