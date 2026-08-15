# Deployment Manifest

**Repository state:** end of Phase 8 — BIM Interoperability & Exchange Foundation.
**Generated from:** the tested source, after `sh tests/phase8/run_all.sh --browser`
(6,446 assertions, 0 failed) and `sh tests/deploy/verify_deploy.sh` (191 checks, 0 failed).

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
| Entry | `public/index.html` — one self-contained file, 1,380,704 bytes |
| Build command | `bash tools/netlify-build.sh` |
| Publish directory | `public` |
| Runtime libraries | fetched **at build time** into `public/vendor/` — three 0.160.0, es-module-shims 1.8.2, pdfjs-dist 4.0.379 |
| Runtime network dependency | none — no CDN is contacted after the build |

`public/index.html` is not compiled from sources at deploy time. Every browser layer is
**injected into it in the repository** by the `tools/build_*.py` injectors and committed. The
deploy publishes the file as it stands. The verification script re-runs all six injectors and
then asserts each generated block appears exactly once, so a stale page cannot ship silently.

## 3. Backend

| Item | Value |
| --- | --- |
| Entry | `acs_understand_api:app` (FastAPI) |
| Start command | `uvicorn acs_understand_api:app --host 0.0.0.0 --port ${PORT:-8000}` |
| Base image | `python:3.11-slim` |
| Dependency file | `requirements.txt` — fastapi, uvicorn[standard], anthropic, pypdf, python-multipart |
| Health check | `GET /health` (declared in `render.yaml`, served by the API) |
| API surface | `GET /` · `GET /health` · `POST /v1/understand` · `POST /v1/edit` · `POST /v1/understand/image` · `POST /v1/understand/pdf` |

### Backend runtime import closure (computed, not assumed)

The deployed entrypoint transitively imports **5 modules**, and the Dockerfile copies every
one of them:

```
acs_understand_api.py → acs_understand.py → acs_layout.py → acs_validate.py
                                          → acs_programs.py (+ acs_programs.json)
```

## 4. Environment variables — names only, no values

Set `ANTHROPIC_API_KEY` **in the Render dashboard only**. It is declared in `render.yaml`
with `sync: false`, so no value ever lives in the repository. `.env.example` lists every name
with empty or non-secret placeholders.

**Secret (must be set manually):**

- `ANTHROPIC_API_KEY`

**Declared in `render.yaml`:**

- `ACS_LLM_MODEL` — `claude-sonnet-5` (do not change without verifying against official
  Anthropic documentation or the live API)
- `ACS_ALLOWED_ORIGINS` — pinned to the Netlify origin; never `*` in production
- `ACS_RL_GEN_HOUR`, `ACS_RL_GEN_DAY`, `ACS_RL_EDIT_HOUR`, `ACS_RL_GLOBAL_DAY` — rate limits
- `ACS_MAX_TEXT`
- `ACS_DEEP`, `ACS_GROUP_SIZE`, `ACS_WORKERS`

**Read by the backend with a built-in default (optional to set):**

- `ACS_MAX_DESC`, `ACS_MAX_TOKENS`, `ACS_MAX_TOKENS_REPAIR`, `ACS_MAX_TOKENS_PLAN`,
  `ACS_MAX_TOKENS_DETAIL`, `ACS_MAX_GROUPS`, `ACS_REPAIR_ROUNDS`, `ACS_MAX_BUILDING`,
  `ACS_MAX_UPLOAD_MB`, `ACS_TRUSTED_PROXIES`

Twenty-two variables are read in total; the verification script asserts none is both
undeclared and undefaulted.

## 5. Files expected in the deployed **site** (Netlify)

| Path | Source | Note |
| --- | --- | --- |
| `index.html` | committed | carries every injected phase block |
| `vendor/three@0.160.0/build/three.module.js` | build-time fetch | plus 6 `examples/jsm` addons |
| `vendor/es-module-shims@1.8.2/es-module-shims.js` | build-time fetch | iOS Safari < 16.4 only |
| `vendor/pdfjs@4.0.379/pdf.min.mjs` + `pdf.worker.min.mjs` | build-time fetch | PDF import |

Thirteen vendored files in total. The build script verifies each is present and non-empty and
checks the Three.js `REVISION` constant; any miss fails the build, so the previous successful
deploy stays live.

### Generated blocks that must be present in `index.html`

Each of these appears **exactly once**, verified:

```
ACS RUNTIME LAYER · ACS AUTHORING LAYER
ACS WORKSPACE UI / STYLES / DOM
ACS RENDER ENGINE / STYLES / DOM
ACS BIM EXCHANGE / STYLES / DOM
```

Their canonical specifications (`ACS_VISUAL_SPEC`, `ACS_RUNTIME_SPEC`, `ACS_AUTHORING_SPEC`,
`ACS_WORKSPACE_SPEC`, `ACS_RENDER_SPEC`, `ACS_BIM_SPEC`) are asserted byte-equal to the
`acs_*.json` files on disk.

## 6. Files expected in the deployed **container** (Render)

`requirements.txt` and 33 `acs_*` sources. The five in the runtime closure are load-bearing:

```
acs_understand_api.py  acs_understand.py  acs_layout.py  acs_validate.py
acs_programs.py  acs_programs.json
```

The other 15 modules the Dockerfile copies — `acs_arch`, `acs_coord`, `acs_distance`,
`acs_egress`, `acs_fls`, `acs_ingest`, `acs_mep`, `acs_navigation`, `acs_occupancy`,
`acs_project`, `acs_relations`, `acs_revision`, `acs_rules`, `acs_struct`, `acs_visual`
(and their `.json` specs) — are **present but not reachable from the API entrypoint** today.
They ship as the server-side reference implementation. This is reported by the verification
script rather than left implicit.

## 7. Deliberately **not** in the container

`acs_runtime`, `acs_authoring`, `acs_workspace`, `acs_render`, `acs_bim`, `acs_compiler`.

These layers execute **in the browser**, from the JavaScript mirrors injected into
`public/index.html`. Their Python modules are the canonical reference implementation and the
parity/test authority; the deployed API neither imports nor needs them. Adding them to the
image would enlarge the attack surface without enabling any endpoint. If a future phase gives
the API an endpoint that imports one of them, the closure check in
`tests/deploy/verify_deploy.py` will fail until the Dockerfile is updated — that is the whole
point of computing the closure instead of maintaining a list by hand.

## 8. Optional files

- `public/vendor/**` — absent from the repository by design; created by the Netlify build.
  `tools/vendor.sh` does the same job on a developer machine.
- `.env` — never committed. Copy `.env.example` locally.

## 9. Test-only, **not required in production**

```
tests/**                         all suites, fixtures and outputs
tests/phase8/outputs/**          41 real BIM artifacts (7.7 MB) — evidence, not runtime
tests/deploy/verify_deploy.*     deployment validation
tools/verify-offline.mjs         offline-load check
tools/verify-provenance-browser.js
PHASE*.md, ARCHITECTURE-AUDIT.md, REVIEW-BOARD.md, VERIFICATION-RUNBOOK.md, README.md
```

Neither the Dockerfile nor the Netlify publish directory references anything under `tests/`;
both are asserted.

## 10. Verification

```
sh tests/deploy/verify_deploy.sh   →  191 checks passed, 0 failed
```

Covers: required files exist · backend closure computed and matched against the Dockerfile ·
every generated block present exactly once · every mirrored spec byte-equal to its file ·
Netlify config valid, CSP without a wildcard script source · Render config valid, health path
actually served, secret declared without a value, origin pinned, rate limits intact · no env
var undeclared and undefaulted · no `/home/` or sandbox path in anything deployed · no
credential-shaped value anywhere · no real `.env` · the page loads no remote script · vendored
references accounted for · nothing from `tests/` required.
