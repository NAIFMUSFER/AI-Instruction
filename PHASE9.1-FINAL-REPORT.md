# Phase 9.1 — Final Report

**Professional Visual Quality & Real-Time PBR Presentation Layer**
Executed in the build sandbox. Every number below came from a command that was actually
run. Nothing here is projected.

---

## 1. Architecture

```
CANONICAL MODEL → READ-ONLY PRESENTATION COMPILER → REAL-TIME PBR SCENE
   → OPTIONAL POST-PROCESSING → SCREEN / IMAGE OUTPUT
```

No return arrow. `presentation_only: true`, `writes_to_model: false`,
`reverse_write_allowed: false`, `reverse_arrow_exists: false`. Model hash inputs stay
`["model"]`; the presentation configuration is hashed separately from config bytes only.
The existing renderer was inspected first and extended — no duplicate engine, no
Three.js upgrade (pinned 0.160.0). **Result: PASS.**

## 2. Files created or changed

| File | Lines | Status |
| --- | --- | --- |
| `acs_pbr.json` | 293 | new — 71 top-level keys, 20 materials, 8 lighting presets, 8 camera presets |
| `acs_pbr.py` | 416 | new — deterministic presentation compiler |
| `tools/build_pbr_browser.py` | 588 | new — injects ≈41 KB JS mirror + panel DOM/CSS, idempotent |
| `tools/_pbr_bridge_block.js` | 264 | new — the only THREE-touching code (≈12.6 KB injected) |
| `tools/netlify-build.sh` | +8 entries | extended — verification of the 8 postprocessing/shader modules |
| `public/assets/materials/README.txt`, `public/assets/env/README.txt` | — | new — local asset roots, empty-set default policy |
| `tests/phase9_1/test_pbr.py` | 323 | new — contract + §21 immutability |
| `tests/phase9_1/test_parity.js` + `parity/` | 190 | new — Python↔JS byte parity |
| `tests/phase9_1/test_pbr_browser.js` | 174 | new — panel, graceful path, shipped page |
| `tests/phase9_1/benchmark_pbr.py` | 134 | new — CPU-only, no FPS |
| `tests/phase9_1/capture_reference.js` | 149 | new — §25 harness for a networked machine |
| `tests/phase9_1/run_all.sh` | 101 | new — full gate incl. Phase 1–9 regression |
| `tests/security/test_security.py` | +S-Q1…S-Q17 | extended — 348 total |
| `tests/deploy/verify_deploy.py` | +section 11c | extended — 265 total |
| `tests/phase3/lib/build_browser_page.js` | +10 | extended — PBR DOM/styles into the harness |
| `PHASE9.1-VISUAL-QUALITY.md`, `PHASE9.1-FINAL-REPORT.md`, `PHASE9.1-DEPLOYMENT-MANIFEST.md`, `PHASE9.1-PRODUCTION-VERIFICATION.md` | — | new |

`public/index.html` grew by the four marker-fenced generated blocks plus the render-loop
dispatcher (original `renderer.render(scene,camera)` preserved as the else-branch).
Canonical geometry, semantics, navigation, authoring, BIM and documentation logic:
**untouched**.

## 3. TESTS RUN — full chain, this sandbox

`sh tests/phase9_1/run_all.sh --browser` — steps 0–11, all executed:

| Suite | Result |
| --- | --- |
| Phase 9.1 contract `test_pbr.py` | **156 passed, 0 failed** |
| Phase 9.1 parity (byte-identical Python↔JS) | **7 passed, 0 failed** |
| Phase 9.1 panel — Node scope | **4 passed, 0 failed** |
| Phase 9.1 panel — **real Chromium** | **41 passed, 0 failed**, page errors: none |
| Security (incl. S-Q1…S-Q17) | **348 passed, 0 failed** |
| Deploy verification (incl. 11c) | **265 passed, 0 failed** |
| Phase 9 regression (docs 421, parity 72, Chromium 85, …) | all passed |
| Phase 8 regression (BIM 526, parity 53, Chromium 58, …) | all passed |
| Phases 3–7 regression (runtime, authoring, workspace, render, security Chromium 242, …) | all passed |
| Idempotence of the 8 generated markers + single dispatcher + fallback branch | passed |
| Benchmark (CPU only) | ran; artifact written |
| §25 reference captures | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (exit 2, honest refusal) |

## 4. ASSERTIONS PASSED / FAILED

**8,996 passed, 0 failed** across 56 suite summaries in one chained run
(includes all Phase 1–9 regression; no prior test was weakened, skipped or removed).
Phase 9.1's own new assertions: 156 + 7 + 4 + 41 = **208**, plus the 17 new security
checks and the new deploy section inside the totals above.

## 5. BROWSER VERIFIED

Real Chromium (Playwright, bundled build): 4 suites — security 242, BIM 58, docs 85,
**PBR 41** — 0 failures, 0 page errors. What Chromium proves here: spec reaches the
browser byte-identically; the panel renders, localizes (ar/en) and clamps; apply/capture
without a 3D runtime refuse with typed `PQ_THREE_UNAVAILABLE` and the page stays alive;
canonical model bytes stay identical through 32 UI apply combinations; the shipped page
carries the bridge and dispatcher exactly once with the fallback branch and no remote
scheme, CDN host or remote fetch/import in the quality layer.
**WebGL rendering itself: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (this sandbox
has no vendored Three.js — `public/vendor` is populated at Netlify build time).

## 6. NETLIFY BUILD VERIFIED

`bash tools/netlify-build.sh` was executed: it fails here at `npm pack` with **403**
(registry blocked in the sandbox) → **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
What IS verified: the script's must-list now includes the 8 postprocessing/shader
modules; the existing `cp -R examples/jsm` already ships them; deploy verification
parses the real script and TOML (`base` not set, publish `public`, 265 checks green).

## 7. PRODUCTION VERIFIED

Backend Docker build: no Docker daemon in the sandbox → **NOT VERIFIED — EXTERNAL
ENVIRONMENT REQUIRED**. Live URLs unreachable from here for the same reason. The
step-by-step post-deploy checklist is `PHASE9.1-PRODUCTION-VERIFICATION.md`.

## 8. Benchmarks (no invented FPS)

CPU milliseconds in this sandbox, this run (`tests/phase9_1/outputs/benchmark_pbr.json`):
resolving all 20 materials ≤ 0.1 ms; 4 shadow tiers ≤ 0.03 ms; 8 cameras ≤ 0.3 ms;
32 full configs + hashes ≈ 6.3–7.1 ms per model; immutability re-verification 0.06 ms
(warehouse) → 27.3 ms (1,000-space grid). Canonical bytes re-verified identical after
every row. **No frame rate is measured, estimated or claimed** — FPS does not exist
outside a real browser on real hardware.

## 9. KNOWN LIMITATIONS

1. Raster output (glass transmission, shadows, SSAO, presets **as pixels**) is
   NOT VERIFIED here — run `node tests/phase9_1/capture_reference.js` on a networked
   machine after `sh tools/vendor.sh`; it produces the 8 deterministic before/after
   pairs and refuses honestly (exit 2) otherwise. No screenshot was fabricated.
2. `local_texture_sets` ships empty by design: the realistic mode uses the deterministic
   procedural PBR set; image textures become active only by listing allow-listed local
   files — never a URL.
3. Basic real-time PBR is what is shipped and claimed; `photorealism_claimed: false`
   remains asserted (§30) — no path tracing, no offline rendering.
4. Netlify/Render builds and the live site cannot be exercised from this sandbox
   (npm 403, no Docker daemon, no network) — external environment required.

## 10. HARD STOP

Phase 9.1 ends here per §31. **No Phase 10 work was started.** Awaiting approval.
