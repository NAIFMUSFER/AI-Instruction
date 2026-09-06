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

> **Final hardening pass (F-46…F-49).** **KI-14 is now CLOSED by
> measurement**: heavy upload validation — and the engineering planner that
> ran on *every successful response* — moved to a bounded persistent process
> pool. Worst measured event-loop stall fell from **1591 ms to 17.9 ms**, and
> from **1482 ms to 2.9 ms** for a payload the gate *rejects*. Rate limiting
> stopped being a warning and became an enforced startup invariant. Scene
> complexity is a declared contract, `slabStrips` is 115× faster with
> byte-identical output, every user-controlled loop is bounded, thirteen
> silent `catch` blocks now report, and floors scale past F9. Pinned by
> `test_event_loop.py` (66), `test_scene_limits.js` (171) and
> `test_scene_benchmark.js` (80). **KI-2, KI-4 and KI-6 remain OPEN —
> environmental, no egress and no three.js in this sandbox.**

> **Post-200 apply pass (F-41…F-45).** `POST /v1/understand` was returning
> **200 OK with a valid LARGE building** and the viewport stayed empty — no
> exception, no error panel, and a status line reading «تم التوليد ✓ 2001
> عنصر». KI-24's narrowed outline prompt had dropped `index` from `levels`,
> and the viewer derives every storey's elevation and layer key from it, so
> 1947 of 2001 meshes were built at `NaN`. The level contract is now enforced
> in `validate()` rather than requested in a prompt, the compiler refuses
> geometry it cannot place, the new scene is built before the old one is
> demolished, and **success is not declared until a real frame is measured**.
> See **KI-25**, pinned by `tests/remediation/test_model_apply.js` (85
> assertions) and `tests/remediation/test_apply_render_browser.js` (30
> assertions in real Chromium with real WebGL2). `LIVE FRONTEND APPLY
> (three.js): NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`.
> **KI-14 remains OPEN and untouched.**

> **Bounded-plan pass (F-35…F-40).** `POST /v1/understand` was returning
> **502 `ACS_UPSTREAM_TRUNCATED`** on any LARGE building: staged generation
> split the *detail* stage but never the *plan*, so the plan's own output could
> not fit the plan's own ceiling. The plan is now `outline → plan_chunk[0..n]`
> with chunk size derived from the budget and **re-derived from measured
> output**; a chunk that reaches its ceiling is halved rather than re-sent or
> given a bigger ceiling, and no stage ceiling was raised. See **KI-24**, pinned
> by `tests/remediation/test_plan_chunking.py` (59 assertions against a provider
> double that enforces `max_tokens`). `LIVE LARGE GENERATION: NOT VERIFIED —
> EXTERNAL ENVIRONMENT REQUIRED`. **KI-14 remains OPEN and untouched.**

> **Provider-integration pass (F-31…F-34).** `POST /v1/understand` was
> returning **502 `ACS_UPSTREAM_UNKNOWN`** for a `TypeError` raised **inside
> this server**, before a single byte reached Anthropic. Reproduced against the
> pinned SDK's real signature, fixed at the root, and pinned by
> `tests/remediation/test_provider_integration.py` (56 assertions). See
> **KI-23**. `LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`
> (no credentials in this sandbox). **KI-14 remains OPEN and untouched.**

> **CSP remediation pass (F-30).** **KI-13 is now CLOSED** and **KI-22** was
> found and closed with it. Both are proved by
> `tests/remediation/test_csp_style_architecture.js` — 61 assertions in real
> Chromium under the production policy read from `netlify.toml` and served as a
> genuine response header: zero style violations across boot, login, model load,
> the workspace, all five panels and a composed A3 documentation sheet, with the
> sheet geometry measured from `getBoundingClientRect` rather than asserted from
> the model. `style-src 'self'` is unchanged and no `'unsafe-inline'`,
> `'unsafe-eval'` or `'unsafe-hashes'` was introduced.
> **KI-14 remains OPEN** — it was deliberately not touched by this pass.

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

## KI-13 · `style-src 'self'` silently dropped every `style="…"` the panels injected (**CLOSED** — F-30)

**Closed by:** F-30. **Proof:** `tests/remediation/test_csp_style_architecture.js`
— **61 passed, 0 failed** in real Chromium, with the production policy read out
of `netlify.toml` itself and served as a genuine response header.

### The live failure, reproduced before the fix

Production reported, and this repository reproduced byte-for-byte:

```
style-src-attr | public/app/ui/workspace-ui-wiring.js:1300 | blocked: inline
Refused to apply inline style because it violates the following
Content Security Policy directive: "style-src 'self'".
```

That line is `srvPill()`, which writes the server-status badge with
`p.innerHTML = txt` where `txt` carries `<span style="opacity:.75">`. It runs on
every boot, so every visitor hit it.

### Root cause

`style-src` governs the style **attribute**, not the CSSOM interface — and it
governs it *however the attribute arrives*: written in markup, set through
`setAttribute('style', …)`, or parsed out of a string assigned to `innerHTML`.
The layers used the third route, so the attribute reached the DOM and the
browser refused to apply it. The element looked perfect in devtools and had none
of its geometry.

`netlify.toml` had reasoned only about `element.style.x = …` (CSSOM, which **is**
allowed) and concluded the page was clean. True of the static shell; false of
every panel.

### Every affected file, and where each was fixed

| shipped artefact | sites | canonical source fixed |
|---|---|---|
| `public/app/generated/docs.js` | 2 | `tools/build_docs_browser.py` |
| `public/app/generated/workspace-ui.js` | 6 | `tools/build_workspace_ui.py` |
| `public/app/generated/render-engine.js` | 1 | `tools/build_render_browser.py` |
| `public/app/ui/workspace-ui-wiring.js` | 20 + 1 `cssText` | itself — it is canonical, see below |

**`ui/workspace-ui-wiring.js` is not a generated artefact.** The only tool that
ever produced it is `tools/frontend_split.js`, whose input is the inline code in
`public/index.html`. After F-09 that page is a shell with **zero** executable
inline scripts, so the tool has no input left and cannot regenerate the file.
This is asserted, not assumed: `test_csp_style_architecture.js` §4 measures the
inline-script count (0), runs `frontend_analyze.segments()` on the current page
(returns 1 degenerate segment, not the application), and greps every tool in
`tools/` for one that *writes* that path (none — two merely mention it in a
comment).

### The remediation architecture

Two mechanisms, chosen by whether the value space is finite:

**Finite values → predefined CSS classes.** All 20 hand-written sites and 4 of
the generated ones were constant (`opacity:.65`, `color:#f59e0b`,
`width:100%;margin:3px 0`, the whole error-panel block). They became declared
classes: `.acs-dim-65`, `.acs-warn`, `.ws-btn-block`, `.acs-errbox` and friends,
in `app.css` for the hand layer and inside each builder's own generated CSS
block for the generated layers.

**Genuinely dynamic geometry → CSS custom properties applied through CSSOM.**
Sheet aspect ratio, viewport `left/top/width/height`, and tree indent depth have
unbounded value spaces that no finite class set can express. The markup now
carries `data-acs-style="--dc-vp-x:12.5%;…"`, and the new boot script
`public/app/boot/style-bridge.js` applies it with `element.style.setProperty()`
after insertion. The stylesheet consumes the variables with real fallbacks
(`left: var(--dc-vp-x, 0%)`, `aspect-ratio: var(--dc-sheet-ar, 297/210)`), so a
value that never arrives yields a visible element rather than a collapsed one.

**The bridge validates; the old attribute never did.** Values reach these
properties from the model, and the model comes from user text or an uploaded
file. `ACS_STYLE` applies a declaration only if the property is on an explicit
allow-list (or is an `--acs-/--ws-/--dc-` custom property) *and* the value
matches a narrow grammar — number-with-unit, `a/b` ratio, hex colour,
`var(--name)`, or a bare keyword. `url(…)`, `expression(…)`, `@import`,
`;{}<>\` and anything over 64 characters are refused and counted in
`ACS_STYLE.stats()`. Measured in §6: `url(javascript:1)`, an off-list property,
and `expression(alert(1))` are all dropped while the legitimate declarations
around them apply. The fix therefore closes an injection surface that the
original inline attribute left wide open.

### Real-browser evidence

Production policy as a real response header, full user path — boot → login →
model → workspace → all five panels → a composed A3 sheet:

```
boot            0 violations
login + tab     0 violations
model load      0 violations
workspace open  0 violations
five panels     0 violations
documentation   0 violations
TOTAL           0 violations
```

The only two violations recorded in the whole run come from §1's **deliberate
negative controls**, which inject a style attribute on purpose to prove the
policy is still enforcing. The test asserts they fire (`probeViolations >= 2`);
without them the zero above would prove nothing.

**Documentation layout, measured from the page — not from the model:**

```
sheet          495 × 350.03 px   aspect-ratio: 420 / 297   (A3 landscape, from the model)
viewport #1    4.76% / 6.73%  ·  42.86% × 40.40%  ⇒  211.28 × 140.61 px  @ +24.47, +24.42
viewport #2   52.38% / 50.51%  ·  40.48% × 37.04%  ⇒  199.55 × 128.89 px  @ +259.23, +176.77
```

Nothing is 0×0, nothing sits at the corner, and every measured pixel matches the
requested percentage within 2 px. `aspect-ratio` reads `420 / 297` — the value
from the sheet's paper size, not the stylesheet fallback.

**A defect this test caught in the fix itself:** the first version of the bridge
validated ratio values only for the literal `aspect-ratio` property, so
`--dc-sheet-ar: 420/297` was silently dropped and the sheet fell back to
`297/210`. Both are 1.414, so the ratio assertion passed by coincidence — the
`aspect-ratio` **string** comparison is what exposed it.

### The policy is unchanged

`test_csp_style_architecture.js` §5 asserts against `netlify.toml` directly:
`style-src 'self'` present verbatim; no `'unsafe-inline'`, no `'unsafe-eval'`,
no `'unsafe-hashes'`, no `style-src-attr` or `style-src-elem` directive added.
The CSP header is byte-identical to the one deployed before this pass.

### Regression protection

`test_csp_style_architecture.js` §2 walks the **shipped** `public/` tree — the
generated artefacts, not the generators — and fails on `style="`, `style='`,
`.setAttribute("style"` or `.style.cssText =` in any of them. It carries its own
canary so a scanner that stopped seeing anything would fail rather than pass
silently. §3 re-runs all eight browser injectors and fails on any byte of drift,
so a hand-edit to a generated file cannot survive.

<details><summary>original text (kept for the record)</summary>

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

</details>

## KI-22 · The workspace had no way back once opened (**CLOSED** — F-30)

Found while exercising F-27's entry points for this pass: `#acsWorkspace` is a
full-screen surface that covers the launcher bar, and its toolbar carries no
close button — so a user who opened it was stranded. Measured directly: the
Chromium run could not click any panel button after opening the workspace,
because the workspace intercepted every pointer event.

**Fixed:** `Escape` now closes the workspace as well as the five dialog panels,
in `public/app/ui/panels-entry.js`. **Proof:**
`test_csp_style_architecture.js` §7 asserts the workspace opens, then that
`Escape` closes it, and only then opens the remaining five panels — the same
sequence a user performs.

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

## KI-23 · A local `TypeError` was reported as a provider fault, and `/v1/understand` returned 502 (**CLOSED** — F-31…F-34)

**Closed by:** F-31 (root cause), F-32 (fallback discipline), F-33
(classification), F-34 (process boundary).
**Proof:** `tests/remediation/test_provider_integration.py` — **56 passed,
0 failed**, including a red-team run that re-introduces all three defects and
watches the suite fail with the exact production signature.

### The production failure

```
[ACS-PLAN] class=LARGE est_out=34437 zones=51 budget=32000 -> staged
[ACS-DEEP] نوع المبنى: warehouse
[ACS-LLM] call failed (max_tokens=16000, thinking=off) -> ACS_UPSTREAM_UNKNOWN
{"event":"llm_generation","success":false,"upstream_class":"TypeError","duration_ms":389}
{"event":"generation_job","state":"FAILED","error_class":"AcsApiError"}
{"error_code":"ACS_UPSTREAM_UNKNOWN","upstream_class":"JobError","status":502}
```

The 389 ms is the tell: there was no network round trip at all.

### Exact error and location

```
TypeError: Messages.stream() got an unexpected keyword argument 'thinking'
    acs_understand.py:595   →  with client.messages.stream(**kw)
TypeError: Messages.create() got an unexpected keyword argument 'thinking'
    acs_understand.py:598   →  except (AttributeError, TypeError): create(**kw)
    (escapes at :617 / :624 into E.classify_upstream)
```

### Root cause — three defects in series

**F-31 · the argument does not exist in the pinned SDK.** `requirements.txt`
pins `anthropic==0.40`. That version's `Messages.create()` and
`Messages.stream()` are keyword-only, fully explicit, and carry **no**
`thinking` parameter and **no** `**kwargs` (primary source: anthropic-sdk-python
`v0.40.0`, `src/anthropic/resources/messages.py`; the parameter is present by
`v0.47.0`). The first rung of the attempt ladder always sent
`thinking={"type":"disabled"}`, so Python's own argument binding raised
`TypeError` before any HTTP call.

**F-32 · the fallback guaranteed the same failure.** `except (AttributeError,
TypeError)` was written for "an old library with no `stream()`", but it also
swallowed the argument-binding error and re-sent the **identical** kwargs to
`create()` — a retry that could only fail the same way, while erasing the trail.

**F-33/F-34 · the classification was destroyed twice.** `TypeError` matches no
entry in `_BY_CLASS`, carries no HTTP status, and is not a `ConnectionError`, so
`classify_upstream` fell through to `ACS_UPSTREAM_UNKNOWN` — 502, *"unclassified
fault from the model provider"* — for a purely local bug, poisoning the
operator's upstream-error telemetry. Then the process boundary destroyed what was
left: `_child` shipped only `(class name, message)`, so every classified error
arrived at the parent as `JobError(error_class="AcsApiError")` and was
re-classified from scratch under a class name no table knows.

### Why no existing test caught it

The `anthropic` doubles in `test_generation_budget.py` and `test_logging.py`
declare `create(self, **kw)` and `stream(self, **kw)`. **A double that accepts
any keyword argument cannot detect a signature mismatch.** The new suite's
double copies the `v0.40.0` signature verbatim, so the error is raised by
Python's argument binding, not by test logic — and it disappears on its own if
the pin is raised.

### The fix

* **F-31:** `_sdk_supports(client, "thinking")` inspects the installed client's
  real signature once, before the loop, and the parameter is sent only if it is
  accepted (a `**kwargs` signature counts as accepting). On a version that has no
  extended thinking, omitting the parameter *is* `{"type": "disabled"}` — no
  behaviour is lost. Introspection rather than a version string: forks, vendored
  copies and compatible proxies all lie about versions; the signature is what
  Python will actually bind against.
* **F-32:** the fallback to `create()` now triggers on `AttributeError` only.
* **F-33:** new code **`ACS_INTEGRATION_ERROR`** (HTTP **500**, not retryable,
  not in `UPSTREAM_CODES`). Client message: *"a fault in this server's
  integration with the model provider's library — not a fault in your request
  and not at the provider"*. Server telemetry adds `fault=local_integration`,
  the offending `parameter` name, and the installed `sdk_version`. Scope is
  deliberately narrow: only a `TypeError` whose text is an argument-binding
  failure. A `TypeError` from inside the network or parsing layer keeps its old
  classification, so a real provider fault is never mislabelled local.
* **F-34:** `_child` now also ships `{acs_code, message, retryable, upstream}`
  — envelope fields only, already passed through `E.redact`, no traceback, no
  prompt, no raw provider response. The parent re-raises the same `AcsApiError`;
  a code that is not in the declared table is ignored rather than trusted. Both
  executors (process and thread) do this, the older 2-tuple payload is still
  accepted for rolling deploys, and `generation_job` logs now carry
  `error_code`.

### Model identifier — checked, not changed

`claude-sonnet-5` is passed **verbatim** to `messages.create(model=…)`; there is
no alias table anywhere in the repository. It is **not** implicated in this
failure: a bad identifier produces `NotFoundError`/404 →
`ACS_UPSTREAM_MODEL_REJECTED` after a network round trip, whereas this failure
was a local `TypeError` at 389 ms with no request sent. Per instruction it was
left alone. Whether the identifier is correct for the account is a separate
question this evidence cannot answer, and closing it needs the live call below.

### Not verified here

`LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.`
`api.anthropic.com:443` is reachable from this sandbox (TLS handshake succeeds,
`GET /v1/messages` → 405), but there is no `ANTHROPIC_API_KEY` and PyPI is
blocked (403) so `anthropic==0.40` cannot be installed. On a networked machine
with the production key:

    pip install -r requirements.txt
    python3 tests/deploy/verify_backend_live.py --generation

That single command exercises the real SDK, the real model identifier and the
staged path, and prints the token capture that also closes KI-6.

---

## KI-24 · A LARGE building's **plan** could not fit its own stage ceiling, and `/v1/understand` returned 502 (**CLOSED** — F-35…F-40)

**Closed by:** F-35 (outline stage), F-36 (bounded plan chunks), F-37 (recovery
for the legacy single-call plan), F-38 (chunk-level telemetry), F-39 (split a
chunk that reached its ceiling), F-40 (size chunks from measured output, not
from an estimate the provider is free to ignore).
**Proof:** `tests/remediation/test_plan_chunking.py` — **59 passed, 0 failed**,
against a provider double that **enforces `max_tokens`** and truncates past it.
Red-team verified: disabling F-39 alone fails 2 assertions, disabling F-40 alone
fails 3, disabling both fails 5, and reverting the outline ceiling to its old
25 % share fails 3.
**KI-14 remains OPEN and untouched.**

### The production failure

```
[ACS-PLAN] class=LARGE est_out=34437 zones=51 budget=32000 -> staged (estimate_exceeds_budget)
POST /v1/understand -> 502  ACS_UPSTREAM_TRUNCATED
«رد مزود النموذج توقف عند حد المخرجات (16000 رمزًا) في المرحلة plan»
```

### Root cause

Staged generation split the **detail** stage and never split the **plan**. The
plan was one call that had to emit the whole building — every zone with its id,
rect, role and an **open-length `brief`** — under a ceiling of 50 % of the
budget. Nothing in the system estimated the *plan's* output (the estimator sized
the final model only), nothing compared that estimate to the stage ceiling, and
nothing recovered if the plan truncated: the single→staged escalation covers the
one-shot call and `_detail_group_split` covers detail, but the plan sat between
them with no guard. So a large enough request killed the whole generation — not
because the model could not fit the budget, but because its *description* could
not fit its stage.

### The fix — three bounded stages instead of two

`outline → plan_chunk[0..n] → detail_chunk[0..m]`, in the new pure module
`acs_plan_chunks.py` (no provider call, no network, no randomness, no clock).

* **F-35 · outline.** A small call that returns only the envelope and a flat
  `(id, role, template)` list — no rects, no prose. ≈24 tokens/zone measured.
  It is the **determinism anchor**: after it the server knows how many zones
  there are, what they are called and in what order, so chunking is computed
  rather than guessed. It is also the one stage that *cannot* be split (before
  it there is nothing to split on), so its ceiling is derived from the declared
  capacity `ACS_MAX_BUILDING_ZONES` — not from a comfortable fraction. The old
  25 % share held 299 zones and then truncated silently.
* **F-36 · bounded chunks.** `chunk_size = floor(budget × safety / cost-per-zone)`,
  derived, never a buried constant. Chunk boundaries are **semantic** — a chunk
  never mixes two templates (levels), so a failure is attributable and the model
  keeps coherent context. No JSON byte range is ever split. `brief` is capped by
  contract at `ACS_PLAN_BRIEF_MAX_CHARS`; unbounded prose in the plan was what
  made the plan's output unbounded.
* **F-37 · legacy recovery.** If the workload still starts on the single-call
  plan and that call truncates, it escalates **once** to the bounded path
  instead of returning 502. This is a genuinely different request, not a retry
  of the same one.
* **F-38 · telemetry.** Every generation event now carries
  `chunk_index` / `chunk_count` alongside `stage`, `strategy`, `input_tokens`,
  `output_tokens`, `max_output_tokens`, `stop_reason`, `duration_ms` and
  `success`. `acs_logging.generation()` drops undeclared fields silently, so
  both names had to be added to its allow-list — they are. The merged model
  carries `meta.acs_plan_report`: counts, codes, planned vs executed chunks,
  estimated vs measured per-zone cost. Numbers and codes only — no prompt, no
  building content, no key, no raw provider text (asserted).
* **F-39 · split, never raise.** A chunk that reaches its ceiling is **halved
  and re-sent**, bounded by `ACS_MAX_PLAN_CHUNK_SPLITS` and `MIN_CHUNK_ZONES`.
  Not re-sent unchanged (same request ⇒ same truncation, one call burned) and
  not given a bigger ceiling (that just moves the failure to a bigger building).
  The split is gated on `stop_reason == "max_tokens"`, so a response malformed
  for some other reason is attributed rather than pointlessly halved.
* **F-40 · measure, do not assume.** Chunk size derived from the estimate
  assumes the model honours the declared `brief` cap. That assumption is
  reasonable but **not guaranteed**, and relying on an unguaranteed output is
  the original bug in a new place. So: the per-zone cost of every completed
  chunk is measured and drives the size of the next one (downward only, so the
  adaptation is monotone and deterministic); and a workload large enough that
  `VERBOSITY_TOLERANCE`× overrun would reach the ceiling is preceded by a small
  **pilot** chunk that measures before the run commits. F-39 stays as the last
  guard for verbosity that changes mid-generation.

### Measured — provider double that ignores the `brief` contract 4.4×

Ceiling 16000 tokens/chunk. `worst` is the largest single-call output.

| class | zones | calls | worst | ceiling | calls at ceiling |
|---|---|---|---|---|---|
| SMALL | 6 | 2 | 2184 | 16000 | 0 |
| MEDIUM | 20 | 2 | 7275 | 16000 | 0 |
| LARGE | 51 | 4 | 9457 | 16000 | 0 |
| VERY_LARGE | 220 | 11 | 9469 | 16000 | 0 |

The LARGE run in detail — the exact shape of the production failure:

```
outline      51 zones   ->  1367 / 17701
plan_chunk    4 zones   ->  1457 / 16000   (pilot: measures 365 tok/zone vs 156 estimated)
plan_chunk   26 zones   ->  9457 / 16000
plan_chunk   21 zones   ->  7648 / 16000
report: planned 1 chunk, executed 3, estimated 156 tok/zone, measured 365
```

Without F-40 the same workload sends all 51 zones in one chunk, hits 16000,
and (with F-39) recovers by splitting — correct, but one full call wasted.
Without both, it is the production 502.

### Guarantees held

Chunking does not change ids, references, geometry semantics, source
traceability, validation contracts or revision semantics. The merge is ordered
by the **outline**, not by response arrival, so chunk order and retries are
byte-identical (asserted). A failed or capped chunk never deletes a zone the
client asked for: its zones get a deterministic fallback rect and a
`PLAN_ZONE_UNRESOLVED` diagnostic. Truncated JSON is still never repaired or
accepted — `stop_reason=max_tokens` still classifies as `ACS_UPSTREAM_TRUNCATED`
(asserted). Upload limits, CSP, the API error contract, generation process
isolation and the KI-23 SDK-compatibility fix are unchanged (asserted).
No stage ceiling was raised to make this pass: `stage_budget('plan')` is still
0.50 × budget and `stage_budget('single')` is still the full budget (asserted).

### Not verified here

`LIVE LARGE GENERATION: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.`
Same sandbox limits as KI-23: no `ANTHROPIC_API_KEY`, and PyPI returns 403 so
`anthropic==0.40` cannot be installed. Everything above is measured against a
double that enforces `max_tokens` exactly as the provider does, which is what
makes it capable of reproducing this class of failure at all — but it is not a
live call. On a networked machine with the production key:

    pip install -r requirements.txt
    python3 tests/deploy/verify_backend_live.py --generation

with a 50+ zone warehouse prompt reproduces the original 502 on the base commit
and must complete on this one.

---

## KI-25 · `/v1/understand` returned **200 with a valid building** and the viewport stayed empty (**CLOSED** — F-41…F-45)

**Closed by:** F-41 (the level contract, enforced not requested), F-42 (the
compiler never emits geometry it cannot place), F-43 (build before demolish,
with a defined rollback), F-44 (a post-200 apply boundary), F-45 (a request
generation so a stale response cannot overwrite a newer model).
**Proof:** `tests/remediation/test_model_apply.js` — **85 passed, 0 failed**
(node scope, the shipped `compile()` on a declared geometry double) and
`tests/remediation/test_apply_render_browser.js` — **30 passed, 0 failed**
(real Chromium, real WebGL2, real `gl.readPixels`).
Red-team verified: reverting F-41's viewer-side derivation fails 7 node
assertions and **5 browser assertions**, and drops the production-shaped
payload from **44.53 % non-background pixels to 0 %**; reverting F-42's
`addBox` guard fails 3; reverting F-42's `rect` guard fails 12; undeclaring the
sealed shared-state key fails 2.
**KI-13, KI-23 and KI-24 are untouched and still green. KI-14 remains OPEN.**

### The production failure

```
POST https://acs-engine.onrender.com/v1/understand → 200 OK
request_id req_8914f73983354f22 · submitted=1 succeeded=1 failed=0 in_flight=0
ok:true · building present · site 22×16 · levels L0/L1/L2 · rooms, racks,
lanes, points, furniture · acs_plan_report: staged · LARGE · chunks_executed=10
· capped=false · failed_chunks=[]
```

The backend did everything right — which is why KI-24 is live-verified by this
same evidence. Nothing was displayed.

### Exact exception and location

**There is none, and that is the finding.** Nothing threw. The failure was
arithmetic and silent:

```
public/app/core/viewer.js:824   const baseY = lvl.index*fh;  const fkey = 'F'+lvl.index;
                                → undefined * 4 = NaN        → 'Fundefined'
```

Measured on a production-shaped payload (22×16, L0/L1/L2, 54 zones):

| | levels **with** `index` | levels **without** `index` |
|---|---|---|
| meshes built | 2001 | 2001 |
| reached the camera bounds | 2001 | **54** |
| excluded `NON_FINITE` | 0 | **1947** |
| floor keys | `F0 F1 F2` | **`Fundefined`** |
| scene radius | 10.34 | 8.83 |
| `bounds_valid` / `camera_in_frustum` | true / true | **true / true** |
| exception | none | none |
| status line shown to the user | `تم التوليد ✓ 2001 عنصر` | `تم التوليد ✓ 2001 عنصر` |

Every guard in the system reported success. The KI-3 robust-bounds contract
excluded the corrupt meshes — correctly, that is its job for a stray outlier —
and the counter counted them, so the UI wrote a truthful-looking sentence over
an empty window. **A success declared on nothing is worse than an exception.**

### Root cause

The canonical model contract (`acs_understand.py:55`) has always been
`"levels": [ {"index": int, "name": str, "template": str} ]`, and the viewer
derives both the storey elevation and the storey layer key from `index`. When
KI-24 narrowed the outline prompt to the smallest possible schema it asked for
`{"id","template","elevation"}` and dropped `index`; `merge_plan` passes the
outline envelope through verbatim. So **every LARGE building** — every request
that takes the bounded plan path — came back with index-less levels. Small and
medium buildings, which still take the single-call path where the model sees
the full schema in the system prompt, were unaffected. That is why this
survived a green suite and reached production.

### The fix — four independent layers, each red-team verified

* **F-41 · the contract is enforced, not requested.** `PC.normalise_levels()`
  is a pure deterministic normaliser: a declared integer `index` is honoured, a
  missing one is derived from `elevation` order (or array order), duplicates are
  resolved without dropping a level, and every derivation is reported
  (`PLAN_LEVEL_INDEX_DERIVED`, `PLAN_LEVEL_INDEX_DUPLICATE`). It also reports a
  level naming a template that does not exist and a `floors` key no level
  references — two silent drops that predate this bug. It is called from
  `acs_understand.validate()`, the one funnel every generation path passes
  through, so the contract no longer depends on the model obeying a prompt. The
  prompt asks for `index` too — but that is now the hint, not the guarantee.
* **F-42 · the compiler never emits geometry it cannot place.** `addBox`'s old
  guard was `if(ex<=0||ey<=0||ez<=0) return;` — and `NaN<=0` and `undefined<=0`
  are both `false`, so corrupt boxes sailed straight through. Now a non-finite
  position or extent is refused and counted. The viewer also derives a level
  index of its own when one is missing (models arrive from JSON import, DXF and
  older saves, not only from this server), rejects a room whose `rect` is not
  four finite numbers instead of throwing `rect is not iterable`, and tolerates
  a list-shaped field that arrives as a scalar. Every refusal lands in a build-
  defect ledger — counts, reason codes and layer tags, no building content.
* **F-43 · build before demolish.** `setModel` used to dispose the old scene and
  every material *before* calling `compile`. One exception left the user with an
  empty window, no old model to fall back to, and `lastBuilding` already
  replaced by the poison model — so even a later detail-level change re-threw
  and the page stayed dead until reload. Now the new group is compiled first on
  a fresh material cache; on failure the old materials are restored and the
  scene is untouched, and `lastBuilding` is only advanced after a successful
  compile.
* **F-44 · the boundary.** Between "200 with a building" and "the user sees a
  model" there was no `try`, and no question asked. Now success is not declared
  until four things are measured: `setModel` returned; what was built is what
  was given (no rejected rooms, no non-finite geometry, ≥90 % of built meshes
  reached the camera bounds); the camera is finite, its bounds valid and the
  model inside the frustum; and **one real frame was drawn whose pixels are not
  a uniform background**. Failure classifies as `MODEL_LOAD_ERROR`,
  `RENDER_CAMERA_ERROR` or `RENDER_BLACK_VIEWPORT` and opens a panel with a
  retry — never as a network or API fault, because the server succeeded. The
  panel is deliberately a different panel with different words; telling the user
  "the server did not generate" when it did is what sends them to retry forever.
* **F-45 · request generation.** The error panel's retry button bypassed the
  double-click lock on the main button, so three clicks meant three concurrent
  900-second requests and the *last to land* won `setModel`. Each request now
  draws a ticket; a response whose ticket has been superseded is discarded, and
  discarding it is not reported as a failure.

### Measured in real Chromium (real WebGL2, real `readPixels`)

| | meshes | radius | draw calls | non-background pixels | distinct colours |
|---|---|---|---|---|---|
| production-shaped LARGE | 1263 | 10.275 | 1263 | **44.53 %** | 25 |
| same payload, levels without `index` | 1263 | 10.275 | 1263 | **44.53 %** | 25 |
| negative control — geometry at NaN | 1263 | — | 0 | **0.00 %** | **1** |
| same, with F-41 reverted | — | — | — | **0.00 %** | 0 |

A new model replaces the old one: after a small model follows the large one the
frame hash changes, the mesh count changes and the scene radius changes.
Zero unhandled application exceptions, zero failed requests, zero CSP
violations under the production policy read from `netlify.toml`.

### Not verified here

`LIVE FRONTEND APPLY (three.js): NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.`
`public/vendor` is empty in this checkout (`tools/netlify-build.sh` fills it at
build time) and the npm registry returns 403, so `three@0.160.0` cannot be
obtained. The browser suite therefore rasterises the shipped `compile()` output
through a real WebGL2 context with real shaders written for the test, driven by
the shipped `pqCameraFit` — which proves the geometry and the camera are
drawable, and proves the defect makes them undrawable, but does **not** prove
three.js's own scene graph draws them. Closing that needs one run on a built
tree:

    bash tools/vendor.sh
    node tests/remediation/test_apply_render_browser.js

The CI `chromium-browser` job already vendors the runtime, so this closes on the
first pipeline run.

### Still open after this pass

**KI-14** (upload validation and layout run on the asyncio event loop) is
unchanged and still OPEN — it was deliberately not touched.
Found while auditing this chain and **not fixed here**, recorded so they are not
lost: `slabStrips` is O(V³) in core count with no cap (a level pierced by ~150
stair/lift cores costs millions of comparisons on the main thread); there is no
global scene object-count limit, and the "lower the detail level" advice the UI
offers reaches only two expressions in `buildRacks`; the conveyor e-stop loop at
`viewer.js:644` is the one uncapped count loop among the industrial builders;
`compile`'s four `catch(e){}` blocks can drop a whole discipline layer with no
console line; and floor buttons sort lexicographically (`F0,F1,F10,F2`) while
`FLOOR_NAMES` only covers `F0`–`F6`.

---

# Final production-hardening pass — F-46…F-49 (over commit `02cf7e3`)

## KI-14 · Upload validation and the engineering planner ran on the asyncio event loop (**CLOSED** — F-46)

**Closed by:** F-46 (`acs_cpu_pool` — a bounded, persistent process pool; every
CPU-heavy path moved off the loop).
**Proof:** `tests/remediation/test_event_loop.py` — **66 passed, 0 failed**, on
a real asyncio loop, a real HTTP server, the shipped validators, a light client
on a separate thread, and a real `redis-server`.

### Reproduced first, on the heaviest **accepted** input

| path | event-loop stall BEFORE | longest light request BEFORE | stall AFTER | longest AFTER |
|---|---|---|---|---|
| `validate_json_bytes` (3 000 rooms) | 4.5 ms | 6.7 ms | 1.2 ms | 1.5 ms |
| `validate_pdf` (200 pages — the page cap) | 230.3 ms | 228.3 ms | **1.2 ms** | 4.2 ms |
| `validate_images` (3340² px — the decode cap) | 425.9 ms | 427.4 ms | **1.3 ms** | 1.0 ms |
| `validate_images` ×6 — **rejected** by the pixel budget | **1482.4 ms** | 1488.5 ms | **2.9 ms** | 2.5 ms |
| `EA.plan` (4 000 rooms, 528 KB — under `ACS_MAX_BUILDING`) | **1591.4 ms** | 1588.2 ms | **17.9 ms** | 24.9 ms |

Thresholds (declared in `lib_loop_probe`, not lowered): stall ≤ 250 ms,
p95 ≤ 500 ms. p95 after is 0.6–1.3 ms on every path.

Two findings the original KI-14 text did not have:

* The **rejected** six-image batch was the worst case, not the accepted one:
  1.5 s of total server paralysis for a payload the gate throws away. That is a
  denial-of-service primitive built out of a rejection.
* `_engineering_authority` → `EA.plan()` ran on the loop for **every successful
  `/v1/understand` response**, not only on `/v1/edit`. Its cost is
  super-linear — 2.8 ms at 20 rooms, 398 ms at 1 600, **1.6 s at 4 000, 5.7 s at
  8 400** — and all of those are models under the accepted size ceiling. That is
  the "multi-second synchronous CPU work on the event loop" the acceptance
  criteria forbid, on the success path.

### The fix

`acs_cpu_pool.CpuPool`: persistent `ProcessPoolExecutor` (spawn), **2 workers +
8 queue slots**, `max_tasks_per_child=50`, 45 s per-operation timeout.
Processes, not threads, because pypdf is pure Python and holds the GIL. A
persistent pool, not the generation `JobRunner`, because that spawns one process
per job (correct for a minutes-long cancellable generation, wrong for a 400 ms
validation) and because validation must not consume a generation slot.

* **Bounded concurrency and deterministic rejection.** Saturation is an
  immediate `PoolSaturated` → HTTP 429 with `Retry-After`, never an unbounded
  queue that later dies on the gateway timeout.
* **Timeout and disconnect.** Both free the admission slot immediately and
  classify (504 / cancelled). The worker finishes what it started — Python
  cannot kill a task inside a `ProcessPoolExecutor` and we do not claim to, the
  same boundary the generation runner declares for the provider. The difference
  that matters here: the work is **bounded by the upload contract itself**
  (bytes, pixels, pages, decompression), so abandoned work terminates in
  measured time rather than opening an unbounded-consumption path.
* **No unsafe state crosses the boundary.** `UploadRejected(code, message_ar,
  detail)` was **not picklable** — Python rebuilds exceptions from `self.args`,
  which is one string, while `__init__` needs two. The worker therefore returns
  a declared envelope, never an exception, and the parent rebuilds the rejection
  from an allow-listed code. `__reduce__` was also added at the source, because
  a class that cannot be pickled is a trap for the next caller.
* **Only declared targets run.** `TARGETS` maps five short names to two modules;
  a name arriving from the network can never select a callable.
* **Degradation is reported, never silent.** If the platform forbids `spawn`,
  the pool falls back to threads and `/health` says `executor=thread`,
  `isolated=false`, `degraded=true`.

Zero synchronous `UPLOAD.validate_*`, `EA.plan(` or `EA.flat_diff(` calls remain
in `acs_understand_api.py` (asserted). `/health` carries `cpu_pool`.

## Rate limiting — an operational decision, not a warning (F-47)

`/health` used to report `PROCESS_LOCAL_RATE_LIMIT` and
`PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND` and then start normally. A warning that
prevents nothing: two instances mean two quotas, a rolling deploy briefly means
three, and `ACS_RL_GLOBAL_DAY` — the one real safety valve on spend — becomes
silently multiplicable.

The production architecture was read from the deployment, not assumed:
`render.yaml` declares one Docker web service on `plan: starter` with no
autoscaling, and the `Dockerfile` runs `uvicorn` **without `--workers`**. One
process, one instance. That is now an **enforced invariant**:

| state | meaning | startup |
|---|---|---|
| `distributed_backend` | Redis (or equivalent) shared atomic store | starts |
| `development` | not production | starts |
| `single_instance_declared` | production + `ACS_SINGLE_INSTANCE=1` + platform concurrency 1 | starts |
| `UNDECLARED_SINGLE_INSTANCE` | production, process-local limiter, no acknowledgement | **refuses to start** |
| `SINGLE_INSTANCE_INVARIANT_VIOLATED` | acknowledged, but `WEB_CONCURRENCY`/`UVICORN_WORKERS`/… > 1 | **refuses to start** |

`render.yaml` now carries `ACS_SINGLE_INSTANCE=1` with the reason and the exact
escape hatch (`ACS_RATE_LIMIT_BACKEND=redis` + `ACS_REDIS_URL`).

The distributed path was **exercised against a real `redis-server`**, through a
dependency-free RESP client (`tests/remediation/lib_resp_client.py`) written
because PyPI returns 403 here while `redis-server` is installed — the atomicity
measured is Redis's own:

* four workers sharing one quota of 5 → **exactly 5 of 20** accepted (per-process
  limiting would have allowed 20)
* eight threads × ten attempts against a quota of 10 → **exactly 10** accepted
* Redis down + `fail_policy=closed` → requests refused, not silently opened
* Redis down + `fail_policy=open` → opened **and** the failure is reported;
  `health_status().healthy` is false

## Scene complexity, compiler visibility and floor scalability (F-48)

* **`SCENE_LIMITS`** — one frozen, exported, tested contract
  (`acs.scene-limits/1.0.0`) with 23 named limits. Every previously buried
  `Math.min(…, 40)` / `(…, 60)` / `(…, 200)` now reads from it. New global caps:
  total meshes, levels, rooms per level, cores per level, slab strips, object
  parts, points per room, generator span, text-derived repeats.
* **`slabStrips` was O(V³)** in core count — 2.5 ms at 64 holes, 141 ms at 256,
  **919 ms at 512**. Replaced with a per-z-band sweep using binary search and a
  difference array: O(V² log V). Measured after: 0.18 ms at 64, 2.3 ms at 256,
  **8.1 ms at 512 — 115× faster**. Output is byte-identical to the previous
  algorithm, proved against an inline copy of it over 36 seeded hole sets.
  A 64-core cap now also applies, with a `SLAB_CORES_CAPPED` diagnostic.
* **Unbounded loops closed.** The conveyor emergency-stop loop
  (`es = Math.max(1, Math.floor(len/12))`) had no ceiling — reverting the fix
  **hangs the test runner**, which is what an unbounded user-controlled loop
  means in practice. Same for stair treads and railing posts (no cap), and the
  generator site span (`Infinity` flowed into a division-derived loop). Two
  helpers, `acsCount` and `acsFit`, now clamp every model-supplied repetition and
  record `COUNT_NOT_FINITE` / `COUNT_BELOW_ONE` / `COUNT_ABOVE_LIMIT`.
  Effect on real models: exactly one count moved anywhere — a 1200×800 warehouse
  went 18 661 → 18 637 meshes, the 24 previously-uncapped e-stops.
* **Silent catches.** Thirteen `catch(e){}` blocks in the shipped compiler path
  now record a subsystem, a reason code and a count —
  `ARCH_COMPILE_FAILED`, `SLAB_VOIDS_LOST` (the `ARCH=null` case, which silently
  deleted every core void from every slab), `STRUCT_/MEP_/FLS_COMPILE_FAILED`
  and eight more. Aggregated, never one line per primitive, and carrying no
  building content or prompt text. This immediately paid for itself: the first
  benchmark run reported `ARCH_COMPILE_FAILED` five times and exposed a missing
  module import in the new harness that would otherwise have been measured as a
  valid result.
* **`acsCompileSummary()`** exposes accepted / rejected / non-finite / capped /
  specialization failures / degradation decisions, and the post-200 apply
  boundary now refuses to claim a *complete* render when a subsystem was
  dropped — a new `MODEL_DEGRADED_RENDER` class, distinct from
  `MODEL_LOAD_ERROR` because the model did load.
* **Floors.** Sorting is natural, not lexicographic (`F0,F1,…,F9,F10,F11`,
  verified at 1, 7, 12 and 50 floors). The `F0–F6` naming ceiling is gone, and
  with it a real bug: `F6` was hard-mapped to "السطح" (roof), which is wrong on
  any building taller than seven storeys. Roof-ness is now derived from the
  actual top index, with a deterministic ordinal fallback for any index.

## Performance budgets (F-49) — real Chromium, real WebGL2

Declared before measuring, in `tests/remediation/test_scene_benchmark.js`, and
not lowered afterwards: first visible frame after the HTTP response ≤ 2 s SMALL,
≤ 4 s MEDIUM, ≤ 8 s LARGE/VERY_LARGE/ADVERSARIAL; no main-thread stall > 1 s.

| fixture | meshes | desktop 1440×900 | mobile 390×844 | tablet 820×1180 | budget |
|---|---|---|---|---|---|
| SMALL | 95 | 208 ms | 32 ms | 87 ms | 2 000 |
| MEDIUM | 1 309 | 195 ms | 66 ms | 132 ms | 4 000 |
| LARGE | 2 917 | 243 ms | 116 ms | 182 ms | 8 000 |
| VERY_LARGE | 16 316 | 757 ms | 480 ms | 650 ms | 8 000 |
| ADVERSARIAL (8 levels × 64 cores) | 47 855 | 1 653 ms | 1 253 ms | 1 536 ms | 8 000 |

Longest single synchronous span: 296 ms (`compile`, ADVERSARIAL desktop).
Non-background pixels 4.4 %–33.9 % on every fixture and viewport; zero
application exceptions across fifteen runs. ADVERSARIAL is the only fixture that
degrades, and it says so: `["SLAB_CORES_CAPPED"]`.

## Reconciliation of the environmental NOT VERIFIED items

The rule applied: an item is closed only where **evidence produced in this pass**
satisfies its original acceptance criteria. Evidence reported by the operator is
recorded as an operator attestation and labelled as such — it is not converted
into a measurement this pass did not make.

* **KI-2 · live raster verification** — **STILL OPEN (environmental).** This pass
  measured real WebGL2 rasterisation of the shipped `compile()` output in real
  Chromium at three viewports, but `public/vendor` is empty here (npm 403), so
  three.js itself was not exercised. KI-2's criterion is the deployed renderer.
* **KI-4 · live HTTP contract** — **STILL OPEN (environmental).** All egress from
  this sandbox returns `403 CONNECT tunnel failed`; `acs-engine.onrender.com` and
  the Netlify origin are both unreachable. No live request was made this pass.
* **KI-6 · live token capture** — **STILL OPEN (environmental).** No
  `ANTHROPIC_API_KEY` and no network; no provider call was made this pass.
* **KI-13 / KI-23 / KI-24 / KI-25** — recorded as **LIVE VERIFIED (operator
  attestation, 2026-08-15)** against commit `02cf7e3`: a real LARGE warehouse
  request returned 200 with a visible 3D model, `/health` reports the deployed
  SHA, CORS is correct for the Netlify origin, and the production CSP is strict.
  Their in-repository regression suites remain green in this pass (61 / 56 / 72 /
  85 + 30 assertions). This pass did not independently re-observe production.

## Still open after this pass

* **KI-2, KI-4, KI-6** — environmental, above. Each closes with one run from a
  networked machine; the exact commands are in their original entries.
* Floor-index assumptions found and **not** fixed (outside the scope of the
  files touched): `pbr-bridge.js:621` derives roof-ness from `max(level.index)`
  and picks the wrong slab on a sparse index set; `pbr-bridge.js:487,490,496`
  build host keys as `'F'+lv.index` with no validation, which reproduces the
  KI-25 `Fundefined` shape on the PBR side; and `viewer.js`'s
  `_navLevelsForTemplate`, `_levelElevation` and `ARCH.voids.filter(v =>
  v.level_index === li)` match on the raw `level.index` rather than the index
  `compile()` derives, so a level whose index had to be derived gets no voids and
  no navigation edges. None can crash or silently report success — they degrade
  visibly — but they are a genuine inconsistency between two index sources.
* ~20 empty `catch` blocks in `workspace-ui-wiring.js` outside the compiler path
  (GPU disposal, `localStorage`, XR, PDF import, render diagnostics). Each already
  assigns an explicit fallback; they were left alone deliberately.

---

## Provider 400 · `ACS_UPSTREAM_BAD_REQUEST` was undiagnosable (**diagnostics CLOSED** — F-50; underlying 400 **NOT DIAGNOSED**)

**Live evidence** (`0912415`): `POST /v1/understand` → 502
`ACS_UPSTREAM_BAD_REQUEST`, `request_id=req_1e1db28104a9462e`,
`duration_ms=884`, `upstream_class=BadRequestError`.

**Proof of the fix:** `tests/remediation/test_provider_reject.py` — **57 passed,
0 failed**.
**LIVE PROVIDER CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (no key, no
egress: every outbound connection from this sandbox returns `403 CONNECT tunnel
failed`).

### What the evidence establishes

`884 ms` means the request **reached Anthropic and was rejected by validation** —
this is not KI-23's shape (that was 389 ms with no network round trip at all).

And the provider-call path is **byte-identical** between `02cf7e3` — the commit
whose live LARGE request returned 200 with a visible model — and `0912415`:

```
git diff --stat 02cf7e3 0912415 -- acs_understand.py acs_generation.py \
                                   acs_plan_chunks.py acs_api_errors.py
(empty)
```

The only deployment change was `ACS_SINGLE_INSTANCE=1`, which never reaches the
provider. So the 400 was **not** introduced by a change to how this server builds
its request. It follows that the cause is one of: a different request shape
driven by a different prompt (a different stage and `max_tokens`), a change on
the provider side (model capability, API version, account entitlement), or an
SDK version resolved at image-build time that differs from the pin.

**Which of those it is cannot be determined from the deployed system, because
the deployed system discards every field that would say.** Three independent
gaps, each verified by reading the shipped code:

1. `acs_api_errors.classify_upstream` kept `{provider, kind, status, attempts}`
   and **dropped the provider's structured body** — the `invalid_request_error`
   message that names the offending parameter and its limit.
2. `sdk_version` was measured in `acs_understand` and then **silently dropped by
   the `acs_logging.generation` allow-list** — the same class of defect as
   KI-24/F-38, in a second place.
3. `max_output_tokens` was only written to telemetry **after a successful
   response**, so every failed call logged `max_output_tokens=null` — the single
   most useful number for diagnosing a 400, absent from exactly the case that
   needs it.

A fourth, structural: **there is no model-capability constant anywhere in the
repository.** Every ceiling derives from `ACS_LLM_MAX_OUTPUT_TOKENS`, which is an
operator's number, not the model's. Today that yields
single/repair 32000, detail 24000, **outline 17701**, plan/plan_chunk 16000, and
nothing compares any of them against what the model actually accepts.

### The fix (F-50) — diagnostics, not a guess

* **`safe_provider_detail(exc)`** extracts, from the provider's own structured
  body: `error_type` (allow-listed), `param` (allow-listed, read from the
  message's leading `param:` prefix — because `"stream: must be true when
  max_tokens is greater than 21333"` blames `stream`, not `max_tokens`),
  `requested` and `limit` (integers from the canonical wording),
  `provider_request_id`, and a `detail` string that is redacted, stripped of all
  non-ASCII and capped at 240 chars. Arabic is what user descriptions and system
  prompts are written in here, so the ASCII filter provably removes them — that
  is asserted with a deliberately leaky message.
* **`ACS_UPSTREAM_MAX_TOKENS`** — a distinct code when `max_tokens` is the
  offending parameter or the provider states an output limit, because that case
  has exactly one operator action, and "the provider rejected the request
  wording" does not communicate it.
* **The logging allow-list** now carries `sdk_version`, `transport`,
  `thinking_sent`, `requested_max_tokens`, `budget_clamped`,
  `provider_error_type`, `provider_param`, `provider_limit`, `provider_detail`.
* **`requested_max_tokens` is recorded before the call**, not after success.
* **`acs_generation.model_max_output()` / `clamp_to_model()`** — one authoritative
  ceiling from `ACS_LLM_MODEL_MAX_OUTPUT`, applied at the single derivation point
  so no path can build an unclamped ceiling (including the legacy
  `ACS_MAX_TOKENS_PLAN` / `ACS_MAX_TOKENS_OUTLINE` overrides). **It is unset by
  default and no number is invented**: with it unset, behaviour is byte-identical
  to today. When the provider states its real limit in a 400, that number is now
  logged, so the operator sets this from the provider's own words.

Nothing was raised. `STAGE_SHARE` is unchanged, KI-23's `thinking` gating is
unchanged, KI-24's bounded chunking is unchanged — all asserted.

### Verdict on the underlying 400

**NOT DIAGNOSED.** The exact provider validation reason could not be reproduced
or extracted here: no API key, no egress, and the deployed build never recorded
it. What this pass changed is that the **next** occurrence is self-describing.
After deploying this commit, one retry of the same request produces a log line
carrying `provider_param`, `provider_limit`, `requested_max_tokens`,
`sdk_version`, `transport`, `thinking_sent` and the stage — which names the cause
without another round of guessing.

---

## KI-26 · The provider was hard-wired, so a billing outage had no exit (**CLOSED** — multi-provider migration)

**Status:** CLOSED. **Measured, live, on `0912415` and again on `c9bafa0`.**

### What was measured

The F-50 diagnostics pass ended with the provider's own words, on
`req_034b149147eb43a5` at `2026-08-15T17:58:26Z`:

```
provider_error_type = invalid_request_error
provider_detail     = "Your credit balance is too low to access the
                       Anthropic API. Please go to Plans & Billing to
                       upgrade or purchase credits."
```

Diagnosis complete — and the system had **no move to make**. Three separate
defects, each invisible until this exact failure:

1. **No exit.** `_call_llm_impl` built its client inline:
   `anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], …)`. The
   provider name, key and endpoint were three decisions scattered inside the
   generation function — the one function guarded by KI-23, KI-24 and F-50.
   Switching endpoint meant editing the generation path.

2. **Wrong classification.** A 400 whose cause is the operator's account was
   `ACS_UPSTREAM_BAD_REQUEST` → 502 → «رفض المزوّد صياغة الطلب». The request
   was perfectly well-formed. The user was told their input was the problem,
   and the frontend map put it in `HTTP_4XX_VALIDATION`.

3. **Wrong provider name in every log.** `classify_upstream` hard-coded
   `{"provider": "anthropic"}` in the string. On any other endpoint that is
   worse than a missing field: an absence that looks like information.

### What changed

`acs_provider.py` — a pure resolution layer, no SDK import, no connection, no
secret in any output. It resolves provider · key · base URL · model ·
transport · documented ceiling for a primary and one optional fallback. No
generation-stage code knows which provider is active.

**The endpoint-safety rule is the load-bearing one.** DeepSeek is reached
through the *anthropic* SDK with `base_url` swapped. If `base_url` were
dropped for any reason — an older SDK, a signature change — the request would
go to `api.anthropic.com` **carrying a DeepSeek key**. That is credential
disclosure, not graceful degradation. So `_sdk_accepts_base_url()` introspects
`anthropic.Anthropic.__init__` before the call and raises
`ACS_INTEGRATION_ERROR` if the endpoint cannot be applied. Measured: **zero
bytes sent** in that case.

`ACS_UPSTREAM_BILLING` — 503, not retryable, and a user message that names no
balance, no account and no billing. Classified from provider evidence only:
DeepSeek's documented `402 Insufficient Balance`, an `error_type` of
`billing_error`, or an explicit phrase from `BILLING_MARKERS`. A generic 400
stays a generic 400 — asserted.

Fallback is an **allow-list of three codes** (`UNAVAILABLE`, `OVERLOADED`,
`CONNECTION`), one attempt, one alternate provider, no recursion. Timeout is
deliberately *not* eligible: a timeout does not prove the provider declined
the work, and a second copy doubles the spend on generation that may already
be running. Billing is eligible only behind an explicit
`ACS_LLM_FALLBACK_ON_BILLING=1` — an automatic switch would move spending to
another vendor with no human decision.

### What did not change

`STAGE_SHARE`, `STAGE_FLOOR`, stage budgets (32000/16000/24000 on the
production ceiling), single-vs-staged routing, KI-24 chunk constants, prompts,
schema, repair, scene generation, rendering, engineering authority. All
asserted, not claimed. Existing Anthropic deployments keep working on the old
`ANTHROPIC_API_KEY` alone — and that key is **never** lent to DeepSeek.

Pinned by `tests/remediation/test_multi_provider.py` (111 assertions).
Red-team verified: re-introducing the silent `base_url` drop fails 12
assertions, lending the legacy key fails 3, removing the billing branch fails
3, widening the fallback allow-list fails 5, dropping the new telemetry fields
fails 3, and making the fallback recursive fails 14.

**LIVE DEEPSEEK CALL: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** There is
no DeepSeek key here and PyPI is blocked, so the real SDK cannot be installed.
What is proven is resolution, endpoint targeting, classification, the fallback
bound and secret isolation — measured against a double carrying the real
v0.40.0 signature that records what the client was built with.
# Audit 2026-09-06 — حالة فرع audit/fix-2026-09-06

هذا التحديث يخص الأصل remediation/production-trust@962f8da، ولا يصف تلقائياً main أو النشر الحالي.
السجل الجامع: [AUDIT-REPORT.md](AUDIT-REPORT.md). الإغلاقات التاريخية أدناه لا تتجاوز نطاق اختبارها.
رُفع فرع audit/fix-2026-09-06 إلى GitHub بموافقة المستخدم، مع تطابق محتوى كل commit.
عبارات «لم يُنشر» أدناه تخص نشر التطبيق على Render/Netlify. معرّفات commits المحلية
ومقابلاتها المنشورة محفوظة في artifacts/audit/final/published-commit-map.json؛ آخر إصلاح
منتج منشور عند هذا التحديث هو C09g: ed80077cfd0d3db9fd1d58123cd8e46167ec3c3e.
سجل المضلعات في artifacts/audit/final/cad-published-commit-map.json.

| البند | الحالة | الدليل/الحد |
|---|---|---|
| AUDIT-C08: جسم multipart غير محدود قبل تحليل الطلب | أُصلح محلياً، لم يُنشر | test_request_body_limits.py: فشلت 4/5 قبل الإصلاح ونجحت 5/5 بعده؛ حد الجسم يسبق parsing/spooling، مع تحديث FastAPI/Starlette/python-multipart لإغلاق ثغرات المحللات المثبتة |
| AUDIT-C05: تجاهل منسوب الدور الصريح | أُصلح محلياً، لم يُنشر | test_level_elevation.py/js يفحصان رؤوس glTF وmeshes حقيقية؛ منسوب 7.5 م يُرسم/يُصدّر هندسياً عند 7.5، مع حفظ الصفر والسالب وfallback القديم؛ ليس إثبات بكسلات |
| AUDIT-C06: ابتلاع فشل المصرّف المعماري | أُصلح محلياً، لم يُنشر | test_compiler_arch_failure.py: فشل 2/3 قبل الإصلاح، نجحت 3/3 بعده؛ لا يُسلّم ملف فاقد لفراغات البلاطات عند فشل المعمار، ويُحفظ الملف السابق دون استبدال |
| AUDIT-C11: قبول أبعاد غير صالحة في مسار الصور | أُصلح محلياً، لم يُنشر | test_image_dimensions.py: 15 حالة قبول خاطئ قبل الإصلاح وصفر بعدها؛ قيود العدد/المدى تطابق طلب النص، والحقول الصحيحة/الاختيارية محفوظة |
| AUDIT-C03: عداد API قديم وتفاصيل تحقق مفقودة | أُصلح محلياً، لم يُنشر | test_validator_response.py: 5 فشل قبل الإصلاح و5 نجاح بعده؛ فحص للنموذج الخارج بعد التطبيع، عداد وتفاصيل من نتيجة واحدة، وفشل المدقق لا يصبح صفراً؛ نطاق acs_validate فقط |
| AUDIT-C07: فحوص الفتحات غير مكتملة | أُصلح التشخيص محلياً، لم يُنشر | test_validator_openings.py: 15 فشل واستثناء قبل الإصلاح، ثم صفر؛ enum والأعداد والاحتواء الأفقي والرأسي مفحوصة لكل فتحة. لا تعني هذه الخطوة أن CLI يرفض تلقائياً كل نموذج به مخالفة |
| AUDIT-C01: صفر كاذب مع هندسة/هويات غير صالحة | أُصلحت الحالات المثبتة محلياً، لم يُنشر | test_validator_geometry.py: 13 فشل واستثناءان قبل الإصلاح وصفر بعده؛ أعداد وأبعاد وهويات وحدود نقاط/عناصر مفحوصة بلا تعديل للمدخل. أبعاد object الغائبة معلنة كغير معلومة؛ لا ادعاء بشمول الـ22 |
| AUDIT-C04: إصلاح LLM يستبدل الهندسة صامتاً | أُصلح محلياً، لم يُنشر | test_repair_proposal.py يحفظ 6×6 م مع إتاحة اقتراح 5×5 م للمراجعة؛ المقترح خارج Building وبصمته، والواجهة تعرض الفرق وتنزيل JSON دون تطبيق تلقائي. اختبارات Python وDOM ناجحة؛ البكسلات غير متحققة |
| AUDIT-C02a: تطابق النوى الرأسية | أُصلح للنوى ذات الهوية الصريحة محلياً | test_core_alignment.py: مركز وبصمة ثابتان عالمياً للدرج/المصعد؛ الحالات مجهولة الهوية/المقاس معلنة NOT_EVALUATED/PARTIAL. لا يثبت تصميم الدرج أو الإسناد الإنشائي أو قبول الـ22 |
| AUDIT-C12: forklift يصنف مصعداً | أُصلح محلياً، لم يُنشر | test_core_classification.py/js: لم تعد الرافعة تخلق نواة أو فراغاً أو رابطاً رأسياً؛ المصاعد والأدراج الحقيقية محفوظة. التحقق يشمل مصنّفات المعمار والعلاقات والمسافة في Python والواجهة |
| AUDIT-C02b: غرف بلا وصول | أُصلح للمستطيلات، وأضيف المضلع المستقيم في C09h | test_room_access.py: 8 اختبارات ناجحة؛ رسم أبواب مشتركة ومناطق مفتوحة، مع كشف المكونات المعزولة حتى مع strict. الأغلفة المتداخلة ومداخل التحميل والأشكال غير المدعومة معلنة غير مكتملة؛ لا يشمل إخلاء الأدوار أو القبول الـ22. API يعلن PARTIAL عند نقص نطاق الوصول/النوى |
| AUDIT-C09a: glTF يستبدل المضلع بمستطيل | أُصلح في مصدر glTF؛ بقية C09 مفتوحة | test_polygon_gltf.py: 6 اختبارات؛ مساحة L الفعلية 20 م² وطرح فراغ النواة، جدران مائلة وفتحات، حفظ الأصل ورفض الحلقة المتقاطعة. اكتمل العرض والتصدير في C09b–e؛ الاستيراد والمدقق والعلاقات/المسافات باقية |
| AUDIT-C09b: العرض يستبدل المضلع ويغير حافة الباب | أُصلح في هندسة Three؛ البكسلات غير متحققة | test_polygon_meshes.js: 8 اختبارات على مثلثات فعلية، فتحة النواة والتشطيبات والحافة المائلة وعدم تعديل المدخل؛ تكافؤ Python/JS وحارس تعقيد مشترك. نجح بناء Netlify؛ بقية مستهلكي C09 ما زالت مفتوحة |
| AUDIT-C09c: مساحة المضلع ومعماره وطوبولوجيا الجدران | أُصلح في المصرّف المعماري ومرآته | 6 اختبارات Python و4 واجهة/تكافؤ؛ ستة جدران L ومساحة 20 م²، جدار قطري مشترك وباب صحيح، مساحة تقاطع فعلية وفراغ بلاطة؛ لا ترقية تلقائية لتعرض الفناء. اكتمل SVG/PDF وIFC في C09d/e؛ المدقق والعلاقات/المسافات والمستورد ما زالت تحتاج الإكمال |
| AUDIT-C09d: حدود ومساحات المضلع في المستندات | أُصلح في SVG/PDF والقطاع والكمية | 6 اختبارات Python وحالتا تكافؤ؛ L=20 م²، ثلمة القطاع وفراغ النواة محفوظان، لا خطوط تقسيم حسابية داخلية. تصدير IFC أُكمل في C09e؛ الاستيراد والمدقق ما زالا مفتوحين |
| AUDIT-C09e: حدود المضلع في نموذج التبادل وIFC | أُصلح في المصدر والمرآة والتسلسل | 7 اختبارات Python و3 تكافؤ؛4ملفات بصفر أخطاء IFC4/EXPRESS وقراءة هندسة مستقلة صحيحة. القارئ أُكمل للبثق الرأسي المستقيم في C09f؛ المدقق ومستورد CAD ما زالا مفتوحين |
| AUDIT-C09f: قراءة مقاطع IFC المغلقة | أُصلح للبثق الرأسي ذي الحدود المستقيمة | 5اختبارات؛ حدود L وخلايا البلاطة وفراغ الدرج محفوظة، ووحدة الملليمتر والدوران والإزاحة تطبق مرة واحدة. شاهد خارجي بصفر أخطاء IFC4/EXPRESS وحجم مستقل60م³؛ الأشكال الخارجة عن النطاق تعلن فقد الهندسة |
| AUDIT-C09h: المدقق يتجاهل حدود المضلع | أُصلح للحدود والفتحات والنقاط والتداخل والوصول | 7اختبارات بعد8إخفاقات؛ حلقات معيبة ونقطة الثلمة تكشف، والباب الصحيح والمثلثان المتجاوران يمران. بصمات الأثاث/التكرار تبقى C09i |
| AUDIT-C09i: محتويات المضلع تفحص بصندوقه | مفتوح ومثبت | صندوق داخل الثلمة ونسخة وسطى خارج U وأثاث يقطع الثلمة تمر دون مشكلة؛ C09i/*-before.json |
| AUDIT-C13: موضع فتحة SVG يكرر إضافة أصل الجدار | أُصلح في المصدر والمرآة | test_svg_opening_origin.py/js: خمس حالات ناجحة لكل لغة؛ SVG/الواجهة/القطاع تحفظ المركز القانوني. خمسة ملفات SVG للحالتين تصححت؛ JSON/glTF لم تتغير |
| AUDIT-C14: موضع مقطع IFC من النوع الخاطئ | أُصلح، مع حفظ إزاحته وتوافق الاستيراد | 3 اختبارات ناجحة؛ اختفت أخطاء Position التسعة من فحص IfcOpenShell. أغلق C15 خطأي حقول الفتحات لاحقاً |
| AUDIT-C15: حقل أخير مفقود في الباب والنافذة IFC | أُصلح | اختباران ناجحان؛ لا أخطاء أنواع/عدد حقول في العينة وIFC المستودع. أغلقت C16/C17/C18 مخالفات EXPRESS المثبتة لاحقاً |
| AUDIT-C16: سجل تغيير IFC مجهول | أُصلح | NOTDEFINED يحفظ غياب تاريخ التعديل؛ اختبار بحالتين ناجح، واختفت CorrectChangeAction من فحص EXPRESS |
| AUDIT-C17: الربط المكاني لغرف IFC | أُصلح في الكاتب والقارئ | اختباران ناجحان لدورين؛ اختفت WR31 وWR41 من EXPRESS، واحتواء المنتجات محفوظ |
| AUDIT-C18: تصنيف جدران IFC | أُصلح مع حفظ كامل الهندسة | IfcWall عام، مع استمرار استيراد StandardCase؛ عينة IFC والمستودع صفر أخطاء مخطط/EXPRESS. شكل المضلع عولج في C09e/f؛ المدقق وبقية C09 مفتوحة |
| AUDIT-C19: تقرير أمانة IFC يخفي فقد الشكل | أُصلح للغرف والبلاطات المثبتة | 6اختبارات بعد8إخفاقات؛ الحدود الفعلية والمناسيب والأبعاد المعلومة تدخل التقرير. العينة المفقودة FAIL/0.789474/4خسائر حرجة؛ السليمة PASS/1.0/0. لم تُغلق مطابقة كل العلاقات |
| AUDIT-C20: مقترح IFC يستهدف غرفة في الدور الخطأ | أُصلح في المصدر والمرآة | 7اختبارات و3تكافؤ؛ الهوية الفعلية أو الهندسة/منسوب الدور الفريدان يمنعان الخلط؛ اختبار القبول يعدل غرفة الأرضي وحدها. المطابقة الملتبسة والإحداثيات الغائبة لا تتحول إلى أمر اسم |
| AUDIT-C09g: مساحة فرق IFC تعود للصندوق | أُصلح في المصدر والمرآة | 5اختبارات و3تكافؤ؛ مساحة من الحدود الفعلية، وتغير الشكل/فراغ البلاطة يظهر مع حفظ الاتجاه والتقسيم المكافئين بلا إنذار |
| AUDIT-H10: IFC يرفض معرّفات الغرف العربية | مفتوح | غرفة_1 في العينة تعيد7أخطاء BIM_INVALID_IDENTIFIER، والشاليه18خطأ؛ يلزم ربط هوية تبادل آمنة دون تغيير الأصل |
| AUDIT-H07: اختبار المعمار يطبع فشلاً ويخرج بـ0 | مفتوح في بوابة المنتج؛ سجل التدقيق يصنفه فشلاً | C09c/legacy-arch-before-update.log: 143 نجاح و4 فشل مع exit 0. لا حالات نجاح مخفية في ملخصات التشغيلات السابقة المفحوصة |
| تحقق النشر والحالتين بعد C08 | غير متحقق بالكامل | التوليد المحلي بالمزوّد يعيد 503 لغياب الاعتماد؛ نتائج المولد المحلي والتصدير للحالتين تطابق الأصل بايتاً؛ لا يثبت ذلك صحة وصفهما أو رسم البكسلات |

آخر تشغيل كامل بعد C09h: 145 ملف اختبار، 130 نجاح / 7 فشل / 8 غير متحققة.
وافق المستخدم على دعم المضلعات فعلياً واستؤنف الإصلاح، وفق القسم 14
من AUDIT-REPORT.md. C09/C10 والأجزاء الباقية من فحوص المدقق ما زالت مفتوحة.
المقارنة بعد C13 أبقت JSON/glTF للحالتين بايتاً؛ تصححت خمسة ملفات SVG لمواضع الفتحات.
نتائج التحقق تغيرت في الإصلاحات السابقة كما هو مفصل في التقرير،
ولا يعني ذلك صحة الوصف المحلي أو تحقق التوليد عبر المزوّد. 11 عينة عيب منفردة
وشاهد سليم تطابق نتائجها التوقعات؛ ليست عينة الـ22 الأصلية.

أدلة الإصلاح في artifacts/audit/fixes/. بقية مشاكل التدقيق في AUDIT-REPORT.md ما زالت مفتوحة؛
خصوصاً اكتمال هندسة المدقّق والقالب المحلي وعقد CAD. أُبقيت قدرة الإصلاح اللغوي كمقترح للمراجعة.
