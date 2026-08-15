# Known Issues — preserved for later remediation

> **Updated by the Production Trust Remediation** (branch `remediation/production-trust`,
> base `865cca1` → `497a681`). Closures below cite the test that proves them; every
> item still open says why. Nothing was closed on inspection alone.
>
> | | closed | still open |
> |---|---|---|
> | | KI-1, KI-3, KI-5, KI-7, **KI-10**, **KI-11** | KI-2, KI-4, KI-6, KI-8, KI-9, KI-12 |
>
> KI-10 (F-09 frontend modularisation) and KI-11 (F-11 strict CSP) were opened by the
> first remediation pass and closed by the second. The five still-open legacy items are
> all environmental — they need network egress or a vendored Three.js. **KI-12** is new
> and is a performance item only: the optional feature panels are still eager.

## KI-1 · Automatic engineering changes reported by generation (SEMANTIC — **CLOSED**)

**Closed by:** the Production Trust Remediation, F-01.
**Proof:** `tests/remediation/test_engineering_authority.py` — **135 passed, 0 failed**,
covering the eight required cases (site expansion, aisle resize, exit addition, smoke
detector, sprinkler, zone resize, camera count, room overlap). For each: a proposal
exists, the canonical model is byte-identical before approval, rejecting changes
nothing, approving creates exactly one normal authoring revision with an audit entry,
provenance is recorded, and no auto-commit path exists.
**What changed:** `acs_layout.autofix` now defaults to `AUTHORITY_PROPOSE` and writes
nothing; all four call sites in `acs_understand.py` were removed; every change the
engine can make is declared in `acs_engineering_changes.json` (4 SAFE_NORMALIZATION,
23 ENGINEERING_PROPOSAL) and an unregistered change id raises rather than passing.

<details><summary>original text (kept for the record)</summary>


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


</details>

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

## KI-3 · The Phase-1 site-wide floor plate overhangs smaller buildings (CLOSED)

**Status:** APPLIED in Phase 10 (F-07). The convention changed from
`PHASE1_SITE_WIDE_PLATE` to `PHASE10_FOOTPRINT_PLATE`.

Since Phase 1 the rendered floor plate of every level spanned the whole **site**
rectangle, not the level's own rooms. Above a building smaller than its plot the
upper plates projected past the walls with nothing beneath their edges, which is
what read as a *floating roof/slab*. For a villa on a 30×24 m plot with a 14×13 m
footprint the plate was ≈4.7× the building area.

**What changed.** Every level plate is now derived from the union of that level's
own room footprints through the single shared extent contract
(`acs_pbr.plate_rect` / `pqPlateRect`) — there is no second extent calculator.
Core voids are still subtracted (`acs_pbr.slab_strips` / `slabStrips`). The
site rectangle is used only as the declared `SITE_FALLBACK` when a level declares
no rooms, and a footprint that genuinely equals the plot is left alone. The
site/ground presentation plane is separate and still site-sized
(`GROUND_PLANE` in the browser scene, `SITE|GROUND|plane|0` in the offline
compiler); it lives outside the `BUILDING` group, so it is excluded from bounds,
export, BIM and quantities by construction.

**Provenance, not silence.** `acs_pbr.PLATE_POLICY` (mirrored to the browser as
`PQ_PLATE_POLICY`, injected at build time from the Python source) records the new
policy name, the previous policy name, what pinned it
(`PHASE4_GOLDEN_BASELINE`), the reason, and the explicit declaration that
nothing canonical moved. `alignmentDiagnostics().plate_overhang` now reports the
site plate, the room-union plate, the **rendered** plate measured from the scene,
the residual overhang, and `avoided_site_overhang_m` — the overhang the old
convention would have produced. `ALIGN_ROOF_DETACHED` is now raised for **any**
level whose rendered plate exceeds its own footprint by more than 1 m, not only
for levels above ground: a stricter rule than before.

**Impact, measured.** The Phase-4 golden baseline
(`tests/phase3/fixtures/mesh_baseline.json`) was regenerated. 39 `FLOOR|*|slab|*`
meshes changed across 7 of the 8 baseline models (the warehouse footprint equals
its site, so it did not move) and **not one non-slab mesh changed** name,
visibility, position, size or rotation. Every engineering model hash is
unchanged. The pre-change baseline is archived at
`tests/remediation/fixtures/plate/mesh_baseline_phase1_site_wide.json` and the
confinement is re-proved on every run by
`tests/remediation/test_webgl_diagnostics.js` §11.

**Regression:** `tests/remediation/test_plate_extent.py` (158 assertions) over
six fixtures in `tests/remediation/fixtures/plate/`.

</details>

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

## KI-5 · A generation abandoned by the 504 deadline keeps running to completion (**CLOSED**)

**Closed by:** F-06. **Proof:** `tests/remediation/test_generation_cancel.py` —
**159 passed, 0 failed**. The hanging synthetic provider is terminated at the deadline:
the child PID recorded via `ACS_JOB_TEST_MARKER` becomes `ProcessLookupError`, elapsed
time tracks the timeout rather than the sleep, the worker slot returns immediately, and
a timed-out generation produces no model revision (proved against a real
`acs_authoring` project).
**Honest boundary, still true:** terminating the worker does not recall a request the
model provider has already accepted — no provider cancellation API is claimed. This is
stated in `acs_generation_job.health_status()["boundary_note"]`.
**Defect found while closing this:** `TimeoutError` is a subclass of `OSError`, so the
original `raise` was swallowed by its own `except (EOFError, OSError)` handler and the
API's timeout branch was dead. Proved by a negative control that reverts the fix.

<details><summary>original text (kept for the record)</summary>


`run_bounded` answers the client with `504 ACS_TIMEOUT` and a valid JSON body once
`ACS_REQUEST_TIMEOUT_S` elapses, but the worker thread underneath it cannot be killed —
Python has no thread cancellation. The thread finishes its upstream call and its result is
discarded. Consequences, stated rather than hidden: the model call is still billed, and a
worker slot stays occupied until it returns. Bounded by `ACS_UPSTREAM_TIMEOUT_S` (600s,
shorter than the 840s request deadline) so the thread almost always ends first, and by the
existing per-IP and global rate limits. Moving generation to a separate process pool would
make cancellation real; that is a larger change than this remediation's scope.

</details>

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

## KI-7 · Stage-1 geometry is authoritative, but the arithmetic autofix still moves rooms afterwards (**CLOSED**)

**Closed by:** F-01, same evidence as KI-1. The arithmetic autofixer no longer runs in
any generation path. `test_engineering_authority.py` asserts statically that
`acs_understand.py` contains no `autofix(` call and does not import `acs_layout` at all,
and asserts at runtime that a default `autofix()` call leaves the model byte-identical.

<details><summary>original text (kept for the record)</summary>


`understand_deep` rejects any `rect` a detail stage tries to rewrite and records
`STAGE_RECT_OVERRIDE_REJECTED`. After the merge, however, `acs_layout.autofix` — which
predates this work — still shifts rooms to resolve overlaps, so the final rect can differ
from stage 1. That is a declared engineering step, not a staged-generation leak, and it sits
squarely inside KI-1's scope (automatic engineering adjustments). It is named here so the
distinction is not mistaken for a stage-authority failure: the test suite asserts the detail
stage's geometry loses, not that the final rect equals stage 1 byte for byte.

</details>

## KI-8 · The failing live Building JSON was never captured (OPEN, environmental)

The black-viewport mechanism is proven by arithmetic and reproduced by a fixture, but the
actual JSON behind the reported screenshot was never obtained — this sandbox cannot reach
the deployment over HTTP and no capture was supplied. So
`tests/phase9_2/fixtures/live_large_generated.json` is **reconstructed** to the reported
element census (walls 564, floors 6, doors 82, windows 35, electrical 243, lighting 108,
cameras 26, HVAC 44, safety 78, furniture 172, objects 188), and the `_outlier` variant adds
exactly one stray coordinate to reproduce the proven mechanism. The fixture says so in its
own `_provenance` block and the test asserts it says so.

What this means precisely: the *mechanism* is proven (one invalid coordinate, or any radius
above ~1902 m, empties the frustum while the UI stays populated), and the fix is proven to
remove it. What is **not** proven is that the specific model in the screenshot failed for
that reason rather than some third cause. To close this, capture the Building JSON from a
failing session (`ACS.exportModel?.()` or the network tab) and drop it in as
`live_large_generated_captured.json`; the boot harness picks up any fixture in that folder.

## KI-9 · The A–J render state matrix is executed, but not in this sandbox (OPEN, environmental)

`tests/deploy/verify_page_boot.js` now walks BASE → PBR off/on → post-processing → arch
detail → context for every fixture including the two large ones, calling
`ACS.renderDiagnostics()`, `ACS.verifyVisibleModel()` and the decoded-RGBA analyser after
each transition, and it fails if any state turns the viewport black. It cannot run here:
`public/vendor` is empty because the npm registry is blocked, so the harness exits 2 with
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`. Run it on any networked machine, or against
the deployed URL:

    sh tools/vendor.sh && node tests/deploy/verify_page_boot.js
    node tests/deploy/verify_page_boot.js https://sprightly-selkie-d906c3.netlify.app/

That single command produces the STATE | MESHES | CALLS | TRIANGLES | FRUSTUM | NEAR/FAR |
PIXEL | RESULT table §4 asks for, with real numbers.


## KI-10 · The frontend was a single 1.86 MB `public/index.html` (**CLOSED**)

**Closed by:** F-09. **Evidence:** `tests/remediation/test_bundle_report.py` (91/0),
`tests/remediation/test_module_graph.js` (32/0), `tools/check_index_guard.py`, and
`tests/deploy/verify_deploy.sh` (584/0).

| | before | after |
|---|---|---|
| `public/index.html` | **1,863,894 B** (gzip 513,557) | **44,255 B** (gzip 12,410) — 2.4 % of the old page |
| executable inline JS | 7 classic scripts + one 1,758,943 B module | **0** — the only inline `<script>` is `type="importmap"` |
| `<style>` blocks | 1 (46,752 B) | **0** — `public/app/styles/app.css` |
| `style="…"` attributes | 50 | **0** — 28 generated `.acs-u-NN` classes + `.acs-hidden` |
| first-party modules | 1 | **25** files under `public/app/`, largest 228,695 B (12.6 % of the total, cap 307,200) |

**Module layout** — `main.js` (entry, imports in the original evaluation order),
`shared-state.js` and `late-bindings.js` (the two leaf registries), `boot/` (5 classic
scripts), `styles/app.css`, `core/{viewer,standards,disciplines}.js`,
`generated/{runtime,authoring,workspace-ui,render-engine,bim,docs,pbr,arch-detail,
pbr-bridge,arch-detail-bridge}.js`, `render/scene.js`, `ui/workspace-ui-wiring.js`,
`trust/{core,wiring}.js`.

**Why it is safe.** The split was mechanical, not hand-cut: `tools/frontend_split.js`
parses the module with a real JS parser, computes each segment's top-level declarations
and free identifiers, and generates every `import`/`export` from that computation. Two
properties made it possible and are now locked by `test_module_graph.js`:

* **No application identifier is read at module-evaluation time** — every cross-segment
  reference is inside a function. Measured, not assumed.
* **The graph is acyclic and every edge points backwards** in `main.js`'s order, so the
  evaluation order is byte-for-byte the pre-split page order. The 20 forward references
  go through `late-bindings.js`; the 8 bindings written across module boundaries go
  through `shared-state.js`, because an ES import binding is read-only.

The old guard asserted `MIN_BYTES = 1_000_000` — *the page must be at least a megabyte
or it is truncated*. That constant is now `MAX_BYTES = 204_800` and the build fails
above it. The inversion of that one constant is the whole finding.

**Anti-gaming:** `test_bundle_report.py` fails if the module count drops below 15 or if
any single module holds more than 20 % of first-party JS — so "F-09 done" cannot be
claimed by moving 1.7 MB from HTML into one `app.js`.

**Still true and unchanged:** the split moved bytes, it did not shrink them. Total
first-party JavaScript is 1,819,588 B across 25 now-cacheable files. Lazy-loading of the
optional panels is **not** implemented (`lazy_bytes: 0`, reported honestly); the four
heavy feature layers are still in the eager graph. That is a performance item, not a
security or architecture one, and it is recorded here as **KI-12**.


## KI-11 · The deployed CSP carried `'unsafe-inline'` and `'unsafe-eval'` (**CLOSED**)

**Closed by:** F-11, which F-09 unblocked. **Evidence:** `tests/remediation/csp_browser_probe.js`
→ `tests/remediation/outputs/csp_probe.json`, measured in real Chromium with the
production policy served as a genuine response header; `tests/remediation/test_csp.js`
(141 assertions, 30/30 hostile policy mutants caught); `tests/security/test_security.py`
(377/0); `tools/check_csp_hash.py`.

**Final policy:**
```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none';
frame-src 'none'; form-action 'self';
script-src 'self' 'sha256-kmeUkbmn7TSoFc+bR+iKEW0CLiuQIqi5X7Op3y+XBkA=';
style-src 'self'; img-src 'self' data: blob:; font-src 'self'; worker-src 'self';
connect-src 'self' https://acs-engine.onrender.com; media-src 'self';
manifest-src 'self'; upgrade-insecure-requests
```

| attack | before | after |
|---|---|---|
| hostile inline `<script>` | **EXECUTED** | **BLOCKED** |
| `eval("…")` | **EXECUTED** | **BLOCKED** |
| `new Function("…")()` | **EXECUTED** | **BLOCKED** |
| `javascript:` URL | not measured | **BLOCKED** |
| external cross-origin script | not measured | **BLOCKED** |
| inline event handler | not measured | **BLOCKED** |
| `data:text/javascript` | not measured | **BLOCKED** |
| `blob:` script | not measured | **BLOCKED** |
| `setAttribute('style', …)` | allowed | **BLOCKED** |
| `element.style.prop = …` | allowed | **still ALLOWED** (CSSOM is not governed by `style-src` — measured) |
| normal-boot CSP violations | 0 | **0** |

**Methodology note that matters:** `page.evaluate()` injects through the CDP debugger,
which bypasses CSP. Measuring `eval` from inside it reports EXECUTED even under a strict
policy. Both the probe and `tools/csp_static_server.py` measure `eval`/`new Function`
from a same-origin **external** script and carry a comment saying why.

**The single remaining hash.** An import map cannot be an external file with adequate
cross-browser support, so it is the one inline element left. It is pinned by content
sha256; `tools/check_csp_hash.py` fails the build if the page, `public/app/importmap.sha256`
and `netlify.toml` ever disagree — a one-character edit to the map cannot ship silently.

**es-module-shims was removed.** It was the sole reason for `'unsafe-eval'` and `blob:`
(the application contains zero real `eval(`/`new Function(` call sites). Browsers older
than Chrome/Edge 89, Firefox 108 and Safari/iOS 16.4 lose the application entirely. That
population is stated in versions; its **market share is NOT VERIFIED** — no network, no
analytics. `CSP-HARDENING.md` §4.3 documents the alternative that would restore those
browsers without `unsafe-eval` (rewrite the bare `'three'` specifiers in the vendored
addons at build time, making the import map unnecessary); it is NOT implemented and NOT
tested, because there is no vendored tree here.

**Three defects this hardening exposed, all fixed and measured:**
1. `onclick="location.reload()"` on the engine-failure button — dead under the new
   policy, i.e. the only recovery affordance shown when the 3D engine fails did nothing.
   Rewired with `addEventListener` in `boot/engine-guard.js`; the page now really reloads.
2. `.acs-u-03{display:none}` replacing `style="display:none"` broke the tab switcher —
   `p.style.display=''` cannot clear a class rule. Fixed with a semantic `.acs-hidden`
   that the shipped `showTab` removes; proven in Chromium with the shipped function,
   the real markup and the real stylesheet: exactly one panel visible per tab.
3. The same conversion left `#left` visible before login (`#left{display:flex}` outranks
   a class). Fixed; measured `none` before login and `flex` after.


## KI-12 · Optional feature panels are not lazy-loaded (OPEN — performance only)

`tests/performance/bundle_report.json` records `lazy_bytes: 0`. The BIM, Documentation,
PBR and Architectural-Detail layers (≈ 361 KB together) are imported eagerly by
`public/app/main.js`, because the split preserved the original evaluation order exactly
and those layers register `window.ACS` methods that other modules bind at load.

Making them lazy means giving each an explicit `init()` and deferring the `window.ACS`
registration behind it — a behavioural change that must be proven not to alter the
`window.ACS` surface, the render loop, or listener counts. It is a performance item with
no security or correctness consequence, and it was deliberately not attempted in the same
pass as the split: mixing a mechanical, parser-verified refactor with a behavioural one
would have made both unreviewable.
