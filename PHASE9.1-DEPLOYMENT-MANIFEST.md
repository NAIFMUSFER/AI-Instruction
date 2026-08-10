# Phase 9.1 — Deployment Manifest

**Repository state:** end of Phase 9.1 — Professional Visual Quality & Real-Time PBR
Presentation Layer.
**Generated from:** the tested source, after `sh tests/phase9_1/run_all.sh --browser`
(8,996 assertions, 0 failed across the full Phase 1–9.1 chain) and
`sh tests/deploy/verify_deploy.sh` (265 checks, 0 failed).

This manifest describes the deployment architecture **already present in the repository**.
Phase 9.1 introduces no new deploy target, no new service and no new runtime network
dependency.

---

## 1. Deploy targets (unchanged)

| Layer | Platform | Config file | Live URL |
| --- | --- | --- | --- |
| Frontend | Netlify (static publish) | `netlify.toml` — base **NOT SET**, publish `public`, build `bash tools/netlify-build.sh` | `https://sprightly-selkie-d906c3.netlify.app` |
| Backend | Render.com (Docker web service `acs-engine`) | `render.yaml` + `Dockerfile` (`acs_understand_api:app`) | `https://acs-engine.onrender.com` |

## 2. What Phase 9.1 adds to the shipped frontend

| Item | Value |
| --- | --- |
| Generated quality blocks in `public/index.html` | JS ≈ 41 KB, bridge ≈ 12.6 KB, DOM ≈ 0.6 KB, CSS ≈ 1.7 KB — marker-fenced, regenerable by `python3 tools/build_pbr_browser.py` (idempotent) |
| Render loop | single dispatcher; `renderer.render(scene,camera)` preserved as the else-branch |
| New asset roots | `public/assets/materials/`, `public/assets/env/` — README policy files only; `local_texture_sets` ships **empty** → zero runtime texture fetches |
| Post-processing modules | 8 files under `vendor/three@0.160.0/examples/jsm/{postprocessing,shaders}/` — already copied by the existing `cp -R examples/jsm` in `tools/netlify-build.sh`; now individually **verified non-empty** by the build script's must-list |
| Runtime network dependency | **none** — same-origin `three/addons/…` imports only; no CDN, no remote HDRI, no remote texture; CSP unchanged |
| Three.js | pinned `0.160.0` — **not upgraded** |

## 3. Backend

Unchanged. `acs_pbr.py` is a pure deterministic module with no route, no I/O, no
environment variable and no secret; it joins the same container image via the existing
`COPY acs_*.py` pattern. Rate limits, CSP and `claude-sonnet-5` untouched.

## 4. Canonical file closure

`tests/deploy/verify_deploy.py` (265 checks) proves every `acs_*` file classifies as
container / browser-mirror / offline-tool with no orphan, including the new pair
`acs_pbr.json` ↔ `acs_pbr.py` ↔ generated browser mirror, and section 11c: bridge
sentinels exactly once, dispatcher + fallback, same-origin addon imports only, the 8
modules present in the build script, texture policy local-only with empty default set.

## 5. Deploy steps (unchanged from Phase 9 hotfix)

1. Netlify UI ▸ Build settings: **Base directory EMPTY**, build command
   `bash tools/netlify-build.sh`, publish directory `public`.
2. Push / redeploy; the build vendors three@0.160.0 (incl. `examples/jsm` tree),
   es-module-shims 1.8.2, pdfjs 4.0.379 and verifies 21+ files plus the 8 quality-layer
   modules.
3. Render: Docker web service auto-deploys from the same repo; no change required.
4. After deploy, run `PHASE9.1-PRODUCTION-VERIFICATION.md` and, on any machine with the
   repo + network: `sh tools/vendor.sh && node tests/phase9_1/capture_reference.js`
   for the 8 before/after reference pairs.

Sandbox status of the builds themselves: npm 403 / no Docker daemon here →
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (attempted, logs kept).
