# Approved-viewer presentation and CI repair — 11 November 2026

Base: `a6da9d6d278b71082781ce8ef075bbb741ee77ff` (PR #188). Author: Claude, for Naif, after Codex was stopped.
Not merged, not deployed. Every figure below was measured in one sandbox: 1 logical core, Chromium 1243 (Playwright 1.63.0, the lock pins 1.62.1), SwiftShader software WebGL, PostgreSQL 16. It is not GitHub CI, not a GPU, and not a phone.

ملخص: صار العارض المعتمد يعرض المبنى بإضاءة وظلال وحواف وأسماء فراغات وشبكة قياس وكاميرات تواجه المدخل، دون أي تغيير في الهندسة. وأُصلحت ستة اختبارات مطلوبة في CI كانت تنجح على `main` وتفشل على فرع #188 نفسه.

## 1. Presentation layer on the exact approved artifact

File: `public/app/ui/approved-viewer.mjs` (+ three label rules in `connected-workspace.css`).

- Balanced exposure and light, gradient backdrop, fogged context ground. Before this change the scene was over-exposed and shadows were barely visible.
- Edge lines derived from the approved meshes, merged into one draw call per level.
- Metric reference grid (1 m cell, 5 m for buildings wider than 60 m), stated in the help line.
- Room names from the review packet when supplied, otherwise the artifact's own room identifiers; shown in exterior, aerial and cutaway views, with a toggle.
- Hero and street cameras face the facade that carries an exterior door on the wall envelope. The interior camera stands in the clearest corner instead of inside furniture or racks. The detail view faces a door or window square-on.
- Cut parts no longer cast shadows (local clipping plane with shadow clipping).
- The evidence panel now says that the artifact has no roof and that the viewer does not add one. The compiler emits no roof element today; this is a geometry capability gap, not a rendering one.

Nothing here adds, moves or resizes approved geometry. `test_approved_viewer_browser.cjs` asserts identical mesh count, triangle count and model hash in every view, and that sky, ground, grid, edges and labels are flagged presentation-only.

### Performance changes
- The shadow map is rendered when visibility or the cut changes, not on every camera frame.
- One clipping plane always exists, so entering the cutaway does not recompile materials.
- The selection outline reuses an already compiled line program. First selection dropped from roughly 0.9–3.0 s to about 30 ms in three of four fixture runs here.
- A frame gap above 120 ms stops animated camera moves for the rest of the session and snaps to the target.

### Measured here (not a device claim)
Two fixtures, two viewports, six views: 24 transitions. Before: cutaway about 2.8–3.3 s and detail up to 5.1 s at 1440×900. After: 22 or 23 of 24 under 2 s depending on the run; the slowest remaining transition was about 3.0 s at 1440×900. First view 1.0–1.3 s in every run. The frame p95 target (20 ms desktop / 33 ms mobile) is **not met** under software rendering and is recorded as missed.

### Test policy change that needs the owner's agreement
`transition_timeout_ms` (2 s) stays a hard failure on hosts with 4 or more logical cores, the GitHub runner class. On weaker hosts the test fails only on a stall above 10 s and records the 2 s target as missed in `visual-evidence.json`. Without this the suite could not produce evidence in a 1-core sandbox. Whether the 2 s gate passes on the real CI runner is **not verified**.

## 2. CI suites that were red on PR #188 itself

Each passed on `main` (`c37b525`) and failed on the untouched PR #188 head in the same sandbox.

| Suite | On #188 | Cause | Now |
|---|---|---|---|
| `tests/remediation/test_panel_entry.js` | 26/37 | Fixture still built its graph from `main.js` only; the local studio moved to a dynamic route, so the real renderer met the three.js stub | 37/37 |
| `tests/remediation/test_plate_extent.py` | crash | Stub builder lacked the new `rotation` argument; three checks still asserted the single bounding plate | 159/159 |
| `tests/remediation/test_scene_limits.js` | 165/171 | Golden mesh totals moved because a level now has several slab pieces | 175/175 |
| `tests/remediation/test_ci_dependencies.py` | 19/20 | Five new third-party imports were not declared in the dependency contract | 20/20 |
| `tests/remediation/test_thinking_wire.py` | 11/12 | Still asserted that the ambient endpoint is absent from the provider config | 12/12 |
| `tests/phase3/test_dev_api.js` | 31/33 | Expected `main.js` to import the studio wiring statically | 33/33 |
| `tests/deploy/verify_page_boot.js` | BOOT 12/21 | String predicate is polled with `eval`, which the production CSP forbids; readiness was never observed once loading became dynamic | Readiness and eager-module checks pass; the full run reached 243 passing checks and 0 failures and was stopped before it finished, so it is **not** a completed pass |

In every case the product behaviour introduced by #188 was the intended one and was confirmed directly (for example the local studio reaches `ACS.ready` in about 0.6 s under the production CSP). The repairs are in the tests. Guards were kept at strength rather than loosened:
- scene limits now pins non-slab meshes to the old figures (13, 888, 1998, 3801) and pins slab pieces separately (2, 24, 54, 22); the whole delta was confirmed to be slab pieces;
- plate extent recomputes the room-union area independently and requires disjoint pieces covering it exactly;
- the dependency contract accepts a directly installed test-only package only with an exact version.

## 3. Not resolved

- `test_guest_workspace.cjs` and `test_connected_workspace_browser.cjs`: no result in this sandbox (time-outs under software rendering). Neither a pass nor a product defect is claimed.
- `test_accessibility.js`: timed out at 150 s here; not compared against `main`.
- `test_asgi_client_contract.py` (30/31) and `test_webgl_diagnostics.js` (141/142) also fail on `main` here. The first is a sandbox package conflict reported by `pip check`; the second was not investigated.
- `tools/check_doc_claims.py` reports the status block as stale (module graph documented 43, actual 45).
- GitHub CI results for PR #188/#189, the live Netlify/Render commit, the production database identity, and the Google sign-in 503 reported on 10 November were not checked in this increment.
- Visual quality is still limited by what the compiler emits: no roof, no parapets, no window frames or sills, no stair geometry. Those need canonical/compiler work with parity tests, not viewer changes.

## 4. Second increment, same day: dressing of approved openings, assumed roof, sun, tour

Prompted by the owner's reference video (an interactive courtyard scene with detailed umbrellas, columns, paving, visitors, view modes and an automatic tour). That scene is a single hand-authored showcase; ACS renders whatever the canonical model contains. This increment closes part of the gap inside the viewer and states what it cannot close.

Added to `approved-viewer.mjs`, all presentation-only, instanced, never selectable, counted or exported:
- frames, mullions, transoms and sills around approved windows; frames, a rail and a handle on approved doors; frames and sectional ribs on large (dock) doors. Only flat, axis-aligned openings that exist in the artifact are dressed;
- an **assumed** flat roof over the top floor plate, on by default, hidden in aerial and cutaway views, removable with one toggle, and described in the evidence panel as not part of the approved revision;
- two translucent human scale figures beside the detected entrance; one room lamp used only by the interior view;
- a sun control (06:00–18:00). The artifact declares no north, so the panel states that shadows are not a solar study;
- an automatic tour through the six views that stops on any pointer, key or view choice;
- secondary controls moved into a collapsed "خيارات العرض" group so the toolbar stays short on a phone.

The browser test additionally asserts: dressing exists, the assumed roof is disclosed and never covers plan-like views, the roof toggle works, the sun control re-renders once, the tour ends on a view choice, and no toggle changes the approved mesh count.

Measured in the same 1-core software-rendering sandbox: 21 to 23 of 24 transitions under 2 s across three runs; slowest 3.3 s.

### Gap to the reference video that the viewer cannot close
The reference shows authored components: parametric umbrellas, columns with capitals, patterned paving, railings, lamps, animated visitors, minarets and arcades. ACS has no equivalent elements in its canonical model or compiler. Reaching or exceeding that level for generated buildings requires new canonical element types with compiler geometry and Python/browser parity tests (roof and parapet, stairs with treads and landings, columns, railings, shading devices, site paving and landscape), plus a material library with world-scale texture coordinates. None of that is delivered here.
