# Phase 9.2 — Deployment Manifest

**Repository state:** end of Phase 9.2 — Architectural Visual Fidelity, Façade
Detailing & Presentation Context.
**Generated from:** the tested source, after `sh tests/phase9_2/run_all.sh --browser`
(10,045 assertions, 0 failed across the full Phase 1–9.2 chain) and
`sh tests/deploy/verify_deploy.sh` (287 checks, 0 failed).

Phase 9.2 introduces **no new deploy target, no new service, no new vendored module and
no new runtime network dependency**.

## 1. Deploy targets (unchanged)

| Layer | Platform | Config | Live URL |
| --- | --- | --- | --- |
| Frontend | Netlify (static) | `netlify.toml` — base **NOT SET**, build `bash tools/netlify-build.sh`, publish `public` | `https://sprightly-selkie-d906c3.netlify.app` |
| Backend | Render.com Docker (`acs-engine`, `acs_understand_api:app`) | `render.yaml` + `Dockerfile` | `https://acs-engine.onrender.com` |

## 2. What Phase 9.2 adds to the shipped frontend

| Item | Value |
| --- | --- |
| Generated blocks in `public/index.html` | ARCH DETAIL JS mirror ≈47 KB + bridge ≈13 KB + panel DOM/CSS — marker-fenced, regenerable by `python3 tools/build_archdetail_browser.py` (idempotent, proven twice-run) |
| Render loop | untouched — the single 9.1 dispatcher remains the only one (asserted in deploy 11d) |
| Vendored modules | **none added** — the layer is pure JS over the existing pinned three@0.160.0 |
| Runtime network dependency | none — no CDN, no remote texture, no URL GLTF, no executable asset (S-R7/S-R8, 11d, Chromium layer scan) |
| New canonical pair | `acs_archdetail.json` ↔ `acs_archdetail.py` ↔ generated browser mirror — classified in the deploy closure like every other pair |

## 3. Backend

Unchanged. `acs_archdetail.py` is a pure deterministic module (no route, no I/O, no
env var, no secret) that ships in the same container via the existing `COPY acs_*.py`.
Rate limits, CSP and `claude-sonnet-5` untouched.

## 4. Deploy steps

1. Netlify UI ▸ Build settings: Base directory **EMPTY**, build
   `bash tools/netlify-build.sh`, publish `public` (unchanged since the 9.x hotfix).
2. Push / redeploy. 3. Render auto-deploys the same repo.
4. Post-deploy: run `PHASE9.2-PRODUCTION-VERIFICATION.md`, and on any networked
   machine `sh tools/vendor.sh && node tests/phase9_2/capture_reference_92.js` for the
   §48 before/after pairs.

Sandbox build attempts: npm E403, no Docker daemon → **NOT VERIFIED — EXTERNAL
ENVIRONMENT REQUIRED** (logs kept).
