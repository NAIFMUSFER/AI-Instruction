# Phase 9 — Deployment Manifest

**Repository state:** end of Phase 9 — Construction Documentation & Professional
Drawing Output Engine.
**Generated from:** the tested source, after `sh tests/phase9/run_all.sh --browser`
(8,006 assertions, 0 failed) and `sh tests/deploy/verify_deploy.sh` (215 checks, 0 failed).

This manifest describes the deployment architecture **already present in the repository**.
No second architecture is introduced.

---

## 1. Deploy targets

| Layer | Platform | Config file | Live URL |
| --- | --- | --- | --- |
| Frontend | Netlify (static publish) | `netlify.toml` | `https://sprightly-selkie-d906c3.netlify.app` |
| Backend | Render.com (Docker web service `acs-engine`) | `render.yaml` + `Dockerfile` | `https://acs-engine.onrender.com` |

## 2. Frontend

| Item | Value |
| --- | --- |
| Entry | `public/index.html` — one self-contained file |
| Build command | `bash tools/netlify-build.sh` |
| Publish directory | `public` |
| Runtime libraries | fetched **at build time** into `public/vendor/` — three 0.160.0, es-module-shims 1.8.2, pdfjs-dist 4.0.379 (13 files) |
| Runtime network dependency | none — no CDN is contacted after the build |

Phase 9 adds **no new frontend build step and no new runtime dependency**. The
documentation layer is injected into `public/index.html` in the repository by
`tools/build_docs_browser.py` and committed; the deploy publishes the file as it stands.

## 3. Backend

| Item | Value |
| --- | --- |
| Entry | `acs_understand_api:app` (FastAPI) |
| Start command | `uvicorn acs_understand_api:app --host 0.0.0.0 --port ${PORT:-8000}` |
| Base image | `python:3.11-slim` |
| Dependency file | `requirements.txt` — unchanged by Phase 9 |
| Health check | `GET /health` |

**Phase 9 adds no backend endpoint and no backend dependency.** The documentation
compiler runs in the browser from the injected mirror and in Python as the reference
implementation and test authority. Verified by the AST closure check, not by assertion.

### Backend runtime import closure (computed from the AST, not a hand list)

```
acs_understand_api.py → acs_understand.py → acs_layout.py → acs_validate.py
                                          → acs_programs.py (+ acs_programs.json)
```

Five modules. The Dockerfile copies every one.

## 4. Phase 9 runtime files — and where each belongs

| File | Classification | Deployed by |
| --- | --- | --- |
| `acs_docs.json` | browser mirror + Python reference | injected into `public/index.html`; **not** in the container |
| `acs_docs.py` | Python reference implementation and test authority | **not** in the container — the API never imports it |
| `tools/build_docs_browser.py` | build-time injector | run in the repository; not deployed |
| `public/index.html` | frontend entry, now carrying the documentation block | Netlify publish |

The deployment closure check enforces this classification: every `acs_*.py` and
`acs_*.json` must fall into exactly one of **container runtime**, **browser mirror**, or
**offline command-line tool** (`acs_compiler.py`). Nothing may be orphaned. If a future
phase makes the API import `acs_docs`, the closure check fails until the Dockerfile is
updated.

## 5. Environment variables — names only, no values

Set `ANTHROPIC_API_KEY` **in the Render dashboard only** (`sync: false` in `render.yaml`).
`.env.example` lists every name with empty or non-secret placeholders.
**Phase 9 introduces no new environment variable.**

**Secret (must be set manually):** `ANTHROPIC_API_KEY`

**Declared in `render.yaml`:** `ACS_LLM_MODEL` (`claude-sonnet-5` — unchanged),
`ACS_ALLOWED_ORIGINS`, `ACS_RL_GEN_HOUR`, `ACS_RL_GEN_DAY`, `ACS_RL_EDIT_HOUR`,
`ACS_RL_GLOBAL_DAY`, `ACS_MAX_TEXT`, `ACS_DEEP`, `ACS_GROUP_SIZE`, `ACS_WORKERS`

**Read with a built-in default (optional):** `ACS_MAX_DESC`, `ACS_MAX_TOKENS`,
`ACS_MAX_TOKENS_REPAIR`, `ACS_MAX_TOKENS_PLAN`, `ACS_MAX_TOKENS_DETAIL`,
`ACS_MAX_GROUPS`, `ACS_REPAIR_ROUNDS`, `ACS_MAX_BUILDING`, `ACS_MAX_UPLOAD_MB`,
`ACS_TRUSTED_PROXIES`

Twenty-two variables are read in total; none is both undeclared and undefaulted.

## 6. Files expected in the deployed **site** (Netlify)

| Path | Source |
| --- | --- |
| `index.html` | committed — carries every injected phase block |
| `vendor/three@0.160.0/**` | build-time fetch (7 files) |
| `vendor/es-module-shims@1.8.2/es-module-shims.js` | build-time fetch |
| `vendor/pdfjs@4.0.379/pdf.min.mjs` + `pdf.worker.min.mjs` | build-time fetch |

### Generated blocks that must be present in `index.html`

Each appears **exactly once**, verified:

```
ACS RUNTIME LAYER · ACS AUTHORING LAYER
ACS WORKSPACE UI / STYLES / DOM
ACS RENDER ENGINE / STYLES / DOM
ACS BIM EXCHANGE / STYLES / DOM
ACS DOCUMENTATION / DOCS STYLES / DOCS DOM      ← new in Phase 9
```

Seven mirrored specifications (`ACS_VISUAL_SPEC`, `ACS_RUNTIME_SPEC`,
`ACS_AUTHORING_SPEC`, `ACS_WORKSPACE_SPEC`, `ACS_RENDER_SPEC`, `ACS_BIM_SPEC`,
`ACS_DOCS_SPEC`) are asserted byte-equal to their `acs_*.json` files on disk.

## 7. Files expected in the deployed **container** (Render)

`requirements.txt` and 33 `acs_*` sources. Five are load-bearing:

```
acs_understand_api.py  acs_understand.py  acs_layout.py  acs_validate.py
acs_programs.py  acs_programs.json
```

Fifteen further modules ship without being reachable from the API entrypoint
(`acs_arch`, `acs_coord`, `acs_distance`, `acs_egress`, `acs_fls`, `acs_ingest`,
`acs_mep`, `acs_navigation`, `acs_occupancy`, `acs_project`, `acs_relations`,
`acs_revision`, `acs_rules`, `acs_struct`, `acs_visual`) — the server-side reference
implementation. Reported, not implicit.

## 8. Deliberately **not** in the container

`acs_runtime`, `acs_authoring`, `acs_workspace`, `acs_render`, `acs_bim`, **`acs_docs`**,
`acs_compiler`.

These layers execute in the browser from the mirrors injected into `public/index.html`
(or, for `acs_compiler`, as an offline CLI). Shipping them would enlarge the attack
surface without enabling any endpoint.

## 9. Optional files

- `public/vendor/**` — absent from the repository by design; created by the Netlify build.
  `tools/vendor.sh` does the same on a developer machine.
- `.env` — never committed. Copy `.env.example` locally.

## 10. Test-only, **not required in production**

```
tests/**                          all suites, fixtures and outputs
tests/phase9/outputs/**           55 real documentation artifacts + ARTIFACT-MANIFEST.json
tests/phase8/outputs/**           41 real BIM artifacts
tests/phase7/outputs/**           47 real presentation files
tests/deploy/verify_deploy.*      deployment validation
tools/verify-offline.mjs, tools/verify-provenance-browser.js
PHASE*.md, DEPLOYMENT-MANIFEST.md, PRODUCTION-VERIFICATION.md,
ARCHITECTURE-AUDIT.md, REVIEW-BOARD.md, VERIFICATION-RUNBOOK.md, README.md
```

Neither the Dockerfile nor the Netlify publish directory references anything under
`tests/`; both are asserted.

## 11. Verification

```
sh tests/deploy/verify_deploy.sh   →  215 checks passed, 0 failed
```

Covers: required files exist · backend closure computed from the AST and matched against
the Dockerfile · every generated block present exactly once · every mirrored spec
byte-equal to its file · **every canonical file classified with none orphaned** · Netlify
config valid with no wildcard script source · Render config valid, health path actually
served, secret declared without a value, origin pinned, rate limits intact · no env var
undeclared and undefaulted · no `/home/` or sandbox path in anything deployed · no
credential-shaped value · no real `.env` · the page loads no remote script · vendored
references accounted for · nothing from `tests/` required.
