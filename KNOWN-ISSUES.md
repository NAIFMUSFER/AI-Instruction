# Known Issues — preserved for later remediation

> **Independent audit pass (F-19 … F-29).** A third-party review of the
> `AI3_clean` tree ran every offline suite (≈5,200 assertions, 0 failures) and
> then went looking for what those suites do not cover. It found defects that no
> test asserted, each reproduced by measurement inside this repository, and fixed
> them. Two items are recorded as **still open** because closing them is a
> behavioural change that needs an explicit decision.
>
> | | closed by this pass | opened by this pass |
> |---|---|---|
> | | **KI-15 … KI-21** | **KI-13, KI-14** |
>
> Full text of KI-13 … KI-21 is at the bottom of this file; each carries the
> measurement that proves it, not an inspection note.

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

---

# Independent audit pass — KI-13 … KI-21

Every item below was reproduced by running code in this repository. Numbers are
measurements from those runs, not estimates. The environment had no network and
no `fastapi`, so nothing here depends on either.

## KI-13 · `style-src 'self'` silently drops the `style="…"` attributes the panels inject (OPEN — behavioural fix needed)

**Measured:** `tests/remediation/test_panel_entry.js` opens all six panels in
real Chromium under the production policy served as a genuine response header,
and records `style-src-attr … BLOCKED` violations. The repository's own
`tests/remediation/outputs/csp_probe.json` already recorded the same directive,
and `tests/remediation/test_csp.js` already asserts that `setAttribute("style",
…)` is blocked — but `netlify.toml` §32-34 reasoned only about
`element.style.x = …` (CSSOM, which **is** allowed), and concluded the page was
clean. That conclusion is true of the static shell and false of the panels.

**Why it was invisible until now:** the panels could not be opened at all
(KI-19), so the code paths that inject those attributes never ran in any
browser measurement.

**Where:** `generated/docs.js` (`.dc-vp` / `.dc-sheet` take *all* their geometry
— `left/top/width/height/aspect-ratio` — from the blocked attribute, so every
sheet viewport collapses to 0×0 at the corner), `generated/workspace-ui.js`,
`generated/render-engine.js`, `ui/workspace-ui-wiring.js` (including
`acsErrorPanel`, the backend-failure UI, which loses the `display:flex` row
holding its Retry and local-generate buttons).

**Why it is not fixed here:** the correct fix is to move dynamic geometry to
CSSOM assignment (`el.style.left = …` after insertion, which the policy
permits) or to generated classes. Most of the call sites live in
`public/app/generated/*`, which is emitted by `tools/build_*_browser.py` from
the Python layers — editing the JavaScript directly would be overwritten by the
next regeneration. The change therefore belongs in the builders, is behavioural,
and must be proven not to alter the `window.ACS` surface. That is a separate
pass, deliberately not mixed with the mechanical fixes in this one.

## KI-14 · Upload validation and layout run on the asyncio event loop (OPEN — architectural)

**Where:** `acs_understand_api.py` — `UPLOAD.validate_images`,
`UPLOAD.validate_pdf`, the two `json.dumps` + `validate_json_bytes` calls on
`/v1/edit`, and `EA.plan()` → `acs_layout._autofix_apply` (O(n²), 60 iterations)
are synchronous CPU-bound calls inside `async def` handlers, with no
`run_in_executor`. The LLM path is correctly off-loaded through `run_job`; the
validation path is not.

**Consequence:** uvicorn runs one event loop thread, so while any of these burn
CPU, every other connection stalls — including `healthCheckPath: /health`
(`render.yaml`), which makes Render mark the instance unhealthy and restart it.
The declared `ACS_REQUEST_TIMEOUT_S` (840 s) wraps `run_job` only; nothing
bounds the validation phase.

**Mitigated, not closed, by this pass:** F-21/F-22/F-23 cap the *worst case* of
that CPU work (see KI-18 and KI-19 below) — a PDF that used to run unbounded now
finishes in ≈3 s at the very worst, and the image path is rejected from the
header without decoding. The architectural point stands: those seconds still
block the loop. Closing it means routing validation through `_POOL` the same way
generation is, and proving the error contract is unchanged.

## KI-15 · Empty environment variables prevented the server from importing at all (**CLOSED** — F-19)

**Reproduced:** `int(os.environ.get("ACS_MAX_UPLOAD_MB", "12"))` with the
variable set to `""` raises `ValueError: invalid literal for int() with base 10:
''` — at module import, so `acs_understand_api` never loads and the service does
not boot. `.env.example` shipped `ACS_MAX_BUILDING=`, `ACS_MAX_UPLOAD_MB=` and
`ACS_REPAIR_ROUNDS=` **as empty strings**, and its own header instructs
`cp .env.example .env`. The `ACS_REPAIR_ROUNDS` case is worse than a boot
failure: it raises inside the generation subprocess, is classified by
`classify_upstream`, and reaches the user as **502 `ACS_UPSTREAM_UNKNOWN` — an
unclassified fault from the model provider**, for a purely local config error.

**Fixed:** `acs_understand_api.env_int()` (same shape as the `env_int` that
already existed in `acs_rate_limit`) now backs every integer read in that module;
`acs_understand.py` uses its own existing `_env_int` for `ACS_REPAIR_ROUNDS`;
`.env.example` ships real values with a comment saying why.

## KI-16 · `MAX_UPLOAD` was declared, advertised in `/health`, and never compared to anything (**CLOSED** — F-21)

**Reproduced:** `grep` for `MAX_UPLOAD` across the whole repository returned
exactly two occurrences in code — its definition (`acs_understand_api.py:177`)
and its publication in `/health` (`:373`) — plus documentation claiming it is
enforced. Both upload handlers did `await file.read()` (or `await f.read()` per
part) **before** any size check, so the entire body became resident first; the
12 MiB check inside `validate_pdf` could only fire afterwards.

**Fixed:** `_read_capped()` reads in 256 KiB chunks and raises
`ACS_PAYLOAD_TOO_LARGE` the moment the running total crosses `MAX_UPLOAD`,
across all parts of a multi-image request. `/health` now advertises a limit that
exists.

## KI-17 · `/v1/edit` `notes` had a count limit and no size limit (**CLOSED** — F-20)

**Where:** the handler checked `len(req.notes) > 40` and nothing else;
`validate_json_bytes` and `MAX_BUILDING` are applied to `req.building` only.
`acs_understand.apply_notes` interpolates each note's `text`/`layer`/`floor`/
`room` into the prompt and calls `call_llm(..., truncate=False)`, explicitly
disabling the `MAX_DESC_CHARS` clamp. Forty notes of ten million characters each
was a 400 MB body, accepted, parsed, and pickled across the `spawn` boundary.

**Fixed:** `_cap_notes()` bounds the total to `ACS_MAX_NOTES_CHARS` (20,000 by
default) on `/v1/edit` and on the `notes` form field of `/v1/understand/image`.

## KI-18 · A 120 KB PNG allocated 601 MB and was accepted (**CLOSED** — F-22)

**Reproduced in this repository:**

```
PNG 11000×3600, solid colour  →     122,723 bytes on the wire   (limit 5,242,880)
                                 39,600,000 pixels              (limit 40,000,000)
                                      11,000 px longest side    (limit 12,000)
validate_image(...)           →  1.23 s, peak RSS 601 MB, ACCEPTED
```

Every declared limit measures the wire or the pixel count; none measured the
decoded raster. The `Image.MAX_IMAGE_PIXELS` bomb guard is set *equal to* the
pixel budget, so it can never fire below it. The Render `starter` instance has
512 MB: one unauthenticated request killed the process, and the in-memory
rate-limit state died with it. `validate_images` allows six.

**Fixed:** `ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES` (32 MiB default) is checked from
the *header*, before `im.load()`, using bytes-per-pixel derived from the declared
mode; a shared batch budget follows the same rule. New codes
`IMAGE_DECODED_TOO_LARGE` and `IMAGE_DECODED_BUDGET_EXCEEDED`.
**After:** the same PNG is rejected in 0.00 s with no decode; a realistic
4000×2800 plan still passes. Regression: `tests/remediation/test_upload_security.py`
§N, including the non-vacuousness check that the payload really does clear all
three old limits.

## KI-19 · A 72 KB PDF pinned the CPU for 62 seconds and was accepted (**CLOSED** — F-23)

**Reproduced in this repository** (one page, Flate content stream, ~260:1):

| file | expands to | before | after |
|---|---|---|---|
| 4 KB | 0.9 MB | 0.37 s | 0.23 s |
| 18 KB | 4.6 MB | 5.04 s | 0.80 s |
| 72 KB | 18.4 MB | **62.07 s** | **3.12 s** |
| 268 KB | 74 MB | (super-linear) | **0.03 s — rejected** |
| 1.0 MB | 294 MB | (super-linear) | **0.04 s — rejected** |

The 400,000-character budget was checked *between* pages and applied *after*
each one, but `page.extract_text()` itself was unbounded — and pypdf decompresses
and parses the whole content stream into an operation list *before* extraction
begins, so a character budget cannot reach that phase at all. The allowed
maximum, 12 MiB, is 166× the 72 KB case.

**Fixed, two layers:** `_extract_page_text()` passes a `visitor_text` callback
that aborts the moment the remaining character budget is reached; and
`_flate_expansion()` measures total Flate expansion **before** any extraction,
decompressing each stream with an explicit `max_length` so the measurement
itself can never build more than the budget in memory. Budget
`ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES`, 24 MiB by default; new code
`PDF_DECOMPRESSION_BOMB`. Worst case is now bounded at ≈3 s. Regression:
`tests/remediation/test_upload_security.py` §O.

## KI-20 · `site_w: 1e400` surfaced as "unclassified fault from the model provider" (**CLOSED** — F-24)

**Reproduced:** pydantic v2 defaults to `allow_inf_nan=True`, so
`{"text":"x","site_w":1e400,"site_d":1e400}` yields `inf`. In
`acs_generation.plan_strategy`, `int(area / AREA_PER_ZONE[kind])` then raises
`OverflowError` — which is **not** a subclass of `ValueError`, so the
`except (TypeError, ValueError)` immediately around it does not catch it. The
exception escapes `understand()`, is caught only by the generic handler in the
child process, and is classified as an upstream failure: the user sees **502
`ACS_UPSTREAM_UNKNOWN`** for a local arithmetic bug, at zero token cost to the
caller and with the operator's upstream-error telemetry poisoned.

**Fixed, two layers:** `UnderstandReq` sets `allow_inf_nan=False` and bounds
`site_w`/`site_d` (`gt=0, le=100000`) and `floors` (`ge=1, le=400`), so the
request is rejected as a 422 validation error with the field named; and
`plan_strategy` additionally ignores non-finite areas and catches
`OverflowError`, so the `/v1/understand/image` form path — which does not go
through that model — is covered too.

## KI-21 · Production shipped as `ACS_ENV=development`, as root, with six unreachable feature panels (**CLOSED** — F-25 … F-29)

Five separate defects, grouped because each is a small, verified fix.

**F-25 · `ACS_ENV` was never set anywhere.** Neither `render.yaml` nor the
`Dockerfile` set it, so `acs_logging.ENV` stayed `"development"`,
`IS_PRODUCTION` stayed `False`, and `STACK_TRACES = not IS_PRODUCTION` was
therefore **`True` in production** — the full formatted traceback printed on
every unhandled error, which is precisely what F-18 claimed to have closed.
`E.redact` strips key-shaped substrings only; it does not strip request bodies,
prompt text or internal paths carried in frame context. Second consequence:
`acs_rate_limit.health_status()` only raises
`PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND` when `ACS_ENV=production`, so `/health`
reported the limiter as fine while it was a per-process `MemoryBackend` — making
the `ACS_RL_GLOBAL_DAY=400` spend cap, described in `render.yaml` as "the most
important safety valve", reset on every deploy, restart and OOM kill.
*Fixed:* set in both `render.yaml` and the `Dockerfile`.

**F-26 · the container ran as uid 0.** `python:3.11-slim` sets no `USER` and the
`Dockerfile` added none. *Fixed:* a non-root `acs` user (uid 10001) owns `/app`
and runs the server; nothing needs root after `pip install`.

**F-27 · six shipped feature panels had no entry point.** `#acsWorkspace`,
`#rvPanel`, `#bxPanel`, `#dcPanel`, `#pqPanel` and `#adPanel` ship their full
markup in `public/index.html` and their full logic in `public/app/generated/*`,
and **no line of shipped code called `init()`, `bind()` or `open()` on any of
them** — a repository-wide grep found the calls only inside `tests/`. Every
panel is `display:none` until a `.on` class that nothing added. So the project
tree, inspector, issue centre, revision history, undo/redo, language toggle, and
the BIM / documentation / render / visual-quality / architectural-detail panels
were unreachable from the browser; and because `bind()` never ran, the B/E/I/F
and Ctrl+Z shortcuts and the `beforeunload` unsaved-work guard were never
installed either — closing the tab discarded edits with no prompt.
*Why no suite caught it:* every existing suite calls `init()` itself before
asserting, which proves the panel works **if invoked**, not that anything
invokes it. The one file that would have caught it,
`tests/production/verify_live_browser.js`, looks for `#wsBtnTree` on the live
page and has never run (`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`).
*Fixed:* `public/app/ui/panels-entry.js` (imported last by `main.js`), a
six-button launcher group in the shell wired with `addEventListener` only, and
`window.ACS.exportModel()` exposed from `ui/workspace-ui-wiring.js` so the
panels can be handed the active model. *Proof:*
`tests/remediation/test_panel_entry.js` — 29 assertions in real Chromium under
the production CSP: all six panels actually acquire `.on`, `init()` really wires
the ten workspace-toolbar buttons, clicking with no model explains what is
missing instead of opening an empty panel, and a negative control asserts no
second entry point exists.

**F-28 · `?debug=1` was a no-op.** `boot/debug-toggle.js` did
`e.style.display=''`, but after the F-09 migration `#statCount` is hidden by a
*class* (`.acs-u-13{display:none}`), and clearing an inline property cannot beat
a class rule. The element counter was updated on every frame and never shown.
*Fixed:* an explicit `.acs-debug-on` class, the same technique
`boot/engine-guard.js` already used correctly.

**F-29 · `tools/vendor.sh` produced a tree the production build rejects.** It
still downloaded `es-module-shims` **and listed it as mandatory**, while
`tools/netlify-build.sh` fails the build if any trace of it exists in
`public/vendor` (F-11 removed it). It also fetched six addons while the
application imports twelve — the six postprocessing/shader modules used by
`generated/pbr-bridge.js` were missing, so SSAO and FXAA would silently degrade
to `POST_UNAVAILABLE` while `tools/verify-offline.mjs` still printed PASS
(it only checks `ACS.ready`). Its closing instructions referred to an external
import map and a `SHIMS` array that no longer exist in the page.
*Fixed:* rewritten to produce byte-for-byte what `netlify-build.sh` produces,
with the same 17-file checklist and the same anti-shrink guard.

---

## Packaging note — not a code defect

The `AI3CLEAN.zip` archive as received had **CRLF line endings on 366 of its
files** (the repository itself is LF). Consequences measured here:

* `sh tests/deploy/verify_deploy.sh` failed immediately with
  `cd: can't cd to <root>` — the trailing `\r` became part of the path. The
  same applies to `tools/netlify-build.sh` and `tools/vendor.sh` on a Linux
  build agent, and to `RUN` lines in the `Dockerfile`.
* `tests/remediation/test_bundle_report.py` reported **20 failures**: every
  byte count in `tests/performance/bundle_report.json` disagreed with the files
  on disk (`index.html` 44,882 on disk vs 44,255 declared, and so on). After
  normalising to LF, every size matched exactly and the suite returned
  91 passed / 0 failed.

Not affected, verified rather than assumed: **the CSP import-map hash still
matches.** The HTML tokenizer normalises `\r\n` to `\n` while preprocessing the
input stream, so the browser hashes the LF form; measured in real Chromium with
the production policy as a genuine response header — zero violations, import map
accepted, `textContent.length` 131 not 136.

`.gitattributes` was added (`* text=auto eol=lf`, with binary fixtures marked)
so a checkout on Windows cannot reintroduce this.
