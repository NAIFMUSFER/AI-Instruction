# Frontend and delivery audit — 2026-09-26

Scope: Stream 4, source descended from `adec616`, with the untouched measurements
committed in `BASELINE.md`. The requested `9e3e472` is an ancestor of the observed
main head; this stream did not verify a live deployment commit. All results below are this audit's recorded runs;
they are not a claim that the live deployment has received these branch changes.
The live customer journey belongs to `CUSTOMER-REVIEW.md`.

## Findings ordered by customer impact

### FE-01 — Opening an advanced panel stranded keyboard focus — FIXED

Expected: opening a panel transfers focus into its controls; closing it returns
focus to the opener. Observed before the fix: focus remained on the opener for
workspace, render, BIM, documentation, quality and architectural detail. Using a
close control then left focus on a hidden close button or the document body.
Cost: a keyboard user must search through unrelated controls to operate the panel
and can lose their position when closing it.

Evidence command:

```sh
node tests/remediation/test_audit_frontend_panels.js
```

With Chromium available, the initial regression run reported **17 failed
assertions**, while the no-model refusal, eager/lazy timing, no-page-error and CSP
controls passed. The old accessibility suite had passed because its named-control
scan explicitly excludes generated panels. That passing suite did not establish
their focus behavior.

The fix lives in `public/app/ui/panels-entry.js`. It moves focus synchronously
after an already-loaded panel opens, and observes the panel's actual close state
to restore focus. It preserves focus if the user has deliberately moved to another
control. These are nonmodal panels: no new focus trap was introduced. The
generated panel implementations and model contents are unchanged.

### FE-02 — Architectural controls lacked accessible associations — FIXED

Expected: a screen reader can name the architectural panel, its choices and its
icon actions. The added browser checks failed on the dialog title, label
associations for `adDetail`, `adFacade`, `adContext`, `adStaging`, `adCamera`, and
meaningful names for `adClose`, `adApplyBtn`, `adCompareE/P/A`.
Cost: controls visibly labelled on screen had no programmatic relationship to
their labels, and the action names were just symbols or letters.

The same command produced **3 failed assertions** after FE-01 was fixed and before
the generator changed. `tools/build_archdetail_browser.py` now emits the dialog
semantics, `for` associations and bilingual action names. A no-op regeneration
was byte-identical for every declared target before editing. Regeneration after
the fix changed only the generated DOM block in `public/index.html`; generated
JavaScript, the bridge and CSS remained byte-identical. No generated file was
hand-edited.

### FE-03 — Security suites falsely rejected declared lazy layers — FIXED

The untouched baseline's workspace and render security suites each failed their
assertion that the module must be imported directly by `main.js`. Both modules
already had valid lazy declarations and loaders. This is a delivery-gate defect,
not evidence of a broken customer panel.

Evidence commands:

```sh
node tests/lib/run.js tests/phase6/test_security.js
node tests/lib/run.js tests/phase7/test_security.js
node tests/remediation/test_audit_frontend_guards.js
```

The replacement assertions require exactly one eager-or-lazy declaration and,
for a lazy declaration, exactly one loader in the declared panel entry. Every
existing malicious-input, escaping and dynamic-execution check remains. The new
regression was run red before changing the assertions. Afterward the original
suites reported **168/0** and **164/0** in Node scope, and the mutation suite
reported **12/0**: valid eager and lazy paths pass; missing ownership, duplicate
ownership, missing loading and duplicate loading fail in each real security suite.

### FE-04 — Real-device rendering capacity remains unverified — OPEN

Whether the owner's Intel integrated GPU can sustain the required interaction is
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. No available device was that
machine, no headset was connected, and no synthetic frame time is substituted
for an Intel measurement. This is an evidence/access gap, not a measured code
defect.

## Weight and further deferral

Reproduce source-byte accounting with:

```sh
python3 tools/bundle_report.py
node tests/remediation/test_module_graph.js
python3 tests/remediation/test_bundle_report.py
```

The maintained present-tense figures belong only to the generated
`ACS:CURRENT-STATE` block in `KNOWN-ISSUES.md`. The source snapshot for this audit
grew by **2,383 JavaScript bytes** for focus management and **498 HTML bytes** for
generated accessibility semantics; these are the differences between the
untouched and patched runs of the command above. No loading-performance
improvement is claimed. The shell and module-size gates passed after the changes.

No additional module met every specified deferral condition. `tools/frontend_lazy.txt`
and `main.js` are unchanged. The measured static-import inventory came from
`tools.bundle_report.A.modules()`, `STATIC_IMPORT`, and `eager_closure()`; an
independent graph run passed **43 assertions**.

| Candidate or group | Why it is not eligible for a behavior-preserving whole-module deferral |
|---|---|
| `generated/pbr.js` | Imported by the PBR bridge and architectural code; publishes the plate/rack helpers read by the eager viewer. Deferring it would violate the stated floor-plate contract. |
| `generated/runtime.js`, authoring, core and shared modules | Have static importers beyond `main.js`; they fail the main-only prerequisite. |
| `trust/wiring.js` | Installs error handling, persistence/recovery, accessibility and authentication listeners at evaluation. |
| `ui/connected-workspace.mjs` | Registers the authenticated-project startup listener at evaluation. |
| `ui/connected-semantic-locks.mjs` | Calls its installer at evaluation and registers authentication/change/click handling. |
| `ui/generation-jobs.js` | Captures/wraps the initial transport and installs recovery behavior during evaluation. |
| `ui/residential-quality.js` | Wraps existing model/generation entry points during evaluation. |
| `ui/workspace-viewport-selection-runtime.js` | Installs viewport selection during evaluation and reads eager renderer/registry state. |

For the last six, moving the entire module behind a later panel click would
change when the product's existing event/transport wiring becomes available.
Splitting initial registration from later work would be a separate behavior
change requiring its own measurement; it is not a safe deletion from `main.js`.

Import order, forward-reference ownership, the lazy set, the pinned importmap and
API origin were preserved. The original panel-entry suite passed **37/0** in the
prepared browser environment, including the same-tick PBR opening and lazy-load
waiting-message assertions.

## Rendering measurements and their limits

```sh
node tests/remediation/test_scene_limits.js
node tests/remediation/test_scene_benchmark.js
python3 tests/phase9_1/test_pbr.py
```

The scene-limit suite passed **171/0**. The prepared compiler/raw-WebGL benchmark
passed **81/0** and explicitly reported `three_js_real: false`. In its desktop
MEDIUM fixture it compiled **1,309 meshes**, with **1,261 draw calls in its test
adapter**. The adversarial fixture reached **47,855 meshes** and disclosed
`SLAB_CORES_CAPPED`. These are compiler/adapter measurements, not actual Three.js
draw calls or a commercial rendering-capacity claim. The fixtures are synthetic;
their geometry-rejection diagnostics do not establish the quality of a live
generated building.

The PBR contract is raster rendering: `acs_pbr.SPEC['path_tracing_claimed']` is
false. Source inspection (`rg 'InstancedMesh' tools/_archdetail_bridge_block.js`)
finds instancing for decorative tree trunks/canopies; it does not prove that the
entire engineering scene is instanced. Running `acs_pbr.quality('HIGH',
{'webgl2': False, 'max_texture_size': 2048, 'device_pixel_ratio': 1})` returns
`PERFORMANCE` with `PQ_FALLBACK_APPLIED`, disabled SSAO and disabled
post-processing. This measures the fallback contract, not automatic detection of
an Intel GPU's performance.

Actual Three.js draw calls, GPU texture memory, sustained frame times on the
owner's Intel machine, physical-phone rendering and headset WebXR are
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. Ray/path tracing was neither
added nor enabled by this work.

## Accessibility, RTL and failure behavior

The supplementary environment used a scratch-installed Chromium executable via
the existing `ACS_CHROMIUM` override. It was provisioned only after the untouched
baseline was complete. The original baseline remains a separate no-browser,
no-vendor record.

```sh
node tests/remediation/test_audit_frontend_panels.js --mutations
node tests/remediation/test_accessibility.js
node tests/remediation/test_transport_browser.js
node tests/remediation/test_transport_errors.js
```

The new panel suite's final recorded run passed **39/0**. Disabling the entry-focus
call or the return-focus call in an in-memory served copy was rejected. Removing
the label association, action name or dialog role was also rejected. Sound
controls passed: no-model refusal keeps focus, another chosen control retains
focus after panel closure, eager/cached opening remains synchronous, delayed
loading is explained, and no CSP violation or page exception occurred.

The existing accessibility suite passed **136/0** both before and after changes.
That is its documented DOM/ARIA, keyboard, contrast and responsive-touch scope,
not full WCAG certification or complete generated-panel coverage. It uses the
actual external CSS under the production CSP. The new focused tests extend
coverage to advanced-panel focus and architectural semantics; they do not claim
that every generated subdialog is audited. Arabic text and RTL styling were
retained. Real VoiceOver/NVDA/JAWS behavior and a complete independent accessibility
audit are **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

The transport browser suite passed **7/0**, including offline preflight, timeout,
CORS rejection and CSP rejection. The transport unit suite passed **22/0**. These
tests exercise shipped transport error handling locally and distinguish an
unreachable service from DNS assertions the browser cannot establish. The
declared API origin and strict `connect-src` policy were not broadened. A live
backend outage, authenticated paid-generation recovery and Safari-specific
behavior are **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** in this stream.

## Delivery and regression comparison

All four requested source gates passed after the changes. The exact bare
`ACS_ENV=test bash tools/ci_run.sh` still refuses the missing `--runner` with exit
64, as in `BASELINE.md`; it is not described as a passing full test run.
The expanded comparison replayed the original target/runner invocations from
`BASELINE.md`, using the coordinator's discovery harness:

```sh
TMPDIR=/workspace/scratch/cc68e7a7ea83/audit-evidence/frontend/tmp \
  python3 /workspace/scratch/cc68e7a7ea83/run_baseline.py \
  /workspace/scratch/cc68e7a7ea83/acs-frontend \
  /workspace/scratch/cc68e7a7ea83/audit-evidence/frontend/full
```

This recorded **244 invocations / 29 nonzero exits**, compared with the original
discovery run's **242 / 30**. The two added invocations are the new tests. The
complete differences are:

| Target | Untouched | Patched, same no-browser environment |
|---|---:|---:|
| `tests/phase6/test_security.js` | 1 | 0 |
| `tests/phase7/test_security.js` | 1 | 0 |
| `test_audit_frontend_guards.js` | did not exist | 0 |
| `test_audit_frontend_panels.js` | did not exist | explicit environment refusal: direct exit 2, runner exit 1 |

No previously passing target failed. Every other original nonzero exit was
unchanged; neither the six incorrect initial phase-1 invocations nor absent
browser/vendor capabilities were repaired by changing product behavior. The new
browser test's refusal is an environmental outcome, not an untested success: its
prepared-environment counterpart passed **39/0** with deliberate mutations
rejected. Deployment verification passed **733/0**. Test outputs,
`package-lock.json` and the generated bundle-report artifact were restored before
commit; the generated source-state documentation is retained.

`tools/check_doc_claims.py --fix` refreshed the measured source block rather than
hand-editing it. In the prepared browser/virtualenv environment its declared
claims passed **10/10**. `.github/workflows/acs-audit-frontend.yml` runs the new
contracts and mutations, original panel/accessibility/graph tests, and a no-drift
generator check on pull requests using the repository's pinned action revisions.

No main push, merge, deployment, provider call or external message was performed
by this stream. Production adoption remains reviewable through its branch/PR.
