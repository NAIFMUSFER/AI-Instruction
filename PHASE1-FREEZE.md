# PHASE 1 — CODE FREEZE

**Status:** `CODE-COMPLETE / LOCALLY VERIFIED` · **`PHASE 1 VERIFIED = PENDING EXTERNAL RUNTIME VERIFICATION`**

**No Phase 2 work has been started.**

**No known code defect remains in the locally executable Phase 1 scope.**

The working tree is frozen at this point. This document records what is verified, what
remains, exactly why, and exactly how to close each remaining item on a networked machine.
No code, configuration, dependency, model ID, or architecture was changed to produce this file.

---

## 1. Current project status
- Frontend: single-file static app `public/index.html` (deployed on Netlify).
- Backend: FastAPI engine (`acs_understand_api.py` + `acs_understand.py`, with pure helpers
  `acs_validate.py`, `acs_layout.py`) and offline glTF CLI `acs_compiler.py` (deployed on Render).
- Phase 1 outcome: all locally executable data/security/logic tests PASS; all remaining items
  are runtime tests blocked solely by this sandbox's lack of outbound network, a Three.js-capable
  browser, production reachability, and WebXR hardware. None is a code defect.

### Files changed during Phase 1 (frozen as-is)
| File | Nature of change |
|---|---|
| `public/index.html` | Local object extractor + coverage; XSS escaping of 2 sinks; multi-CDN shim fallback + local-importmap stub + load watchdog; dev-only stat gated to debug; feminine-dual extraction fix |
| `acs_compiler.py` | D-1: ported generic `room.objects` rendering (people/vehicles/furniture/unknown→box) + object coverage report; additive materials; **industrial gating unchanged** |
| `netlify.toml` | Added CSP, `X-Frame-Options`, `Permissions-Policy` (kept COOP/Referrer/nosniff) |
| `render.yaml` | `ACS_ALLOWED_ORIGINS` set to the Netlify origin (not `*`) |
| `acs_understand_api.py` | CORS default hardened to the Netlify origin when env unset |
| `tools/vendor.sh`, `tools/verify-offline.mjs` | New helpers for local vendoring + offline verification |
| `VERIFICATION-RUNBOOK.md`, `ARCHITECTURE-AUDIT.md` | Documentation |

Unchanged from original: `acs_understand.py`, `acs_validate.py`, `acs_layout.py`, `Dockerfile`,
`requirements.txt`. Model ID `claude-sonnet-5` unchanged everywhere.

---

## 2. Locally verified areas (all EXECUTED this session)
| Area | Status | Evidence |
|---|---|---|
| **3. D-1 offline compiler parity** | **PASS** | `acs_compiler.py` renders `room.objects`; villa 5/5, warehouse 9/9, hotel 6/6, clinic 5/5; frontend↔offline placement counts identical; glTF object nodes present; unknown → labeled box + reported |
| **4. Generic building architecture** | **PASS** | Core is generic; `SCHEMA_BRIEF` always sent; villa→compile emits WALL/DOOR/FURN with **no** rack/dock/lane geometry |
| **5. Industrial isolation** | **PASS** | Single gate `industrial = btype in (warehouse,industrial,factory,logistics)` in all 4 modules; villa/hotel/clinic/office inject **zero** industrial fields (33/33) |
| **6. Object preservation (structured objects)** | **PASS** | `room.objects[]` preserved through local extractor, `attachObjects`, offline compiler; dropped=0 |
| **7. Coverage semantics** | **PASS** | REQUESTED / GENERATED / UNSUPPORTED(generic_box) / EXCLUDED / AUTO-ADDED kept as distinct arrays, never merged |
| **8. Negation** | **PASS** | "بدون رافعات شوكية" → forklift EXCLUDED, not generated, survives to `meta.excluded` and JSON |
| **9. XSS** | **PASS** | `<script>` neutralized in room name / description / note / object-name (tooltip) / report; Arabic intact |
| **10. Claude Sonnet 5 model ID** | **PASS (documentation-verified)** | Official Anthropic Model IDs page lists `claude-sonnet-5` as a valid dateless API model ID; left unchanged |
| **11. Regression suite** | **PASS** | Node: P0 17/17, Gate 21/21, XSS 6/6, Types 33/33, Battery 25/25; Python: D-1 objects, backend helpers 7/7, `py_compile` 5/5, config parse |
| JSON serialization content | **PASS** | Exact bytes `bJson` writes contain rooms, `objects`, `meta.requirements/excluded/added` |
| Backend security helpers | **PASS** | `_safe_model` allowlist rejects arbitrary models; `_client_ip` reads rightmost XFF (anti-spoof) |
| Industrial extension activates only when fields present | **PASS** | Warehouse JSON with racks/docks builds them; absent → none |

---

## 12. Arabic feminine-dual extraction defect (fixed & reverified)
- **Defect:** the local free-text object extractor did not handle the feminine ة→ت
  transformation, so duals/plurals of ة-nouns were silently dropped — e.g. "سيارتان"
  (2 cars), "رافعتان", "طاولتان" yielded **0** of that object. This violated the
  no-silent-drop rule for a user-requested object.
- **Fix (scope-limited):** only `objectsFromText` in `public/index.html` — feminine stem +
  suffix set `(ة|ات|تان|تين|تي)`. No other code touched.
- **Reverified:** "فيلا فيها شخصان وسيارتان وسرير واحد" → person×2, **car×2**, bed×1; full
  regression re-run green (17/21/6/33 + battery 25 + Python suites). Offline compiler unaffected
  (it resolves already-formed `room.objects`, not free text).
- Note (explicitly **not** a defect, per freeze instruction): a free-text **unknown** noun such
  as "جهاز أشعة" is not recognized by the local heuristic. It is **not** a silent loss in the
  structured/AI object pipeline — when present in `room.objects` (AI path or explicit model) the
  offline compiler renders it as a labeled box and reports it under `generic_box`. Left as-is.

---

## 13. Remaining NOT VERIFIED runtime items
All are `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`:
Part A Local vendoring · Part B Offline runtime · Part C Real 3D runtime · Part H GLB export ·
Part I PDF runtime · Part J Production AI · Part K-production (docs already PASS) · Part L Live CORS ·
Part M Live CSP · Part O Real mobile (3D-inclusive; UI-chrome no-overflow already PASS) ·
Part P WebXR · Part Q true CDN-independence (graceful-degradation already PASS).

---

## 14. Exact reason each item cannot be verified in this sandbox
Verified by live probe: outbound to `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`,
`acs-engine.onrender.com`, and `sprightly-selkie-d906c3.netlify.app` all return `403`/`000`
(CONNECT tunnel refused); `npm`/`pip` registries return `403`.
- **A/Q-independence:** `vendor.sh` needs CDN/npm downloads → `curl … 403`; `public/vendor/` stays empty.
- **B:** depends on A (no vendored files) → cannot prove independence.
- **C/H/O:** Three.js loads only from blocked CDNs, so the renderer never initializes
  (`window.ACS.ready === false`) → no 3D scene, no GLB export, no usable 3D canvas.
- **I:** pdf.js is fetched from `cdnjs` (blocked); worker/text-extraction can't load.
- **J/L/M:** Render + Netlify unreachable (`000`) → no `/health`, no `/v1/understand`, no live
  preflight, no live response headers.
- **P:** no WebXR-capable device attached.
- These are environment limits, **not** code defects.

---

## 15. Exact commands to run on a networked machine
```bash
# PART A — vendor Three.js/addons/shims (+ optional pdf.js) locally
bash tools/vendor.sh
grep -n "REVISION" public/vendor/three@0.160.0/build/three.module.js | head -1   # expect '0.160.0'
ls public/vendor/three@0.160.0/examples/jsm/{controls/OrbitControls,webxr/VRButton,webxr/ARButton,exporters/GLTFExporter,objects/Sky,environments/RoomEnvironment}.js | wc -l   # expect 6

# Then edit public/index.html: comment the CDN importmap, uncomment the /vendor importmap.
grep -nE '^\s*<script type="importmap">' public/index.html      # expect exactly ONE live
grep -n '/vendor/three@0.160.0/build/three.module.js' public/index.html   # present & uncommented
grep -n 'unpkg.com/three@0.160.0' public/index.html             # only inside a comment

# PART B / Q — offline load with all CDNs blocked
npm i -D playwright && npx playwright install chromium
node tools/verify-offline.mjs        # PASS => ready=true, engineWarn hidden, 0 errors, CDNs blocked

# PART C / H / O — real browser (see VERIFICATION-RUNBOOK.md Parts C/H/O):
#   generate villa/hotel/clinic/office/warehouse; verify render, orbit, clip, measure,
#   sun/shadow, object rendering; export GLB and open in an independent glTF viewer;
#   test at 360/390/430 px including 3D-canvas usability.
```

## 16. Exact production endpoints to test
```bash
# PART J — health + generation (villa/hotel/clinic prompts from the runbook)
curl -s https://acs-engine.onrender.com/health | jq .        # expect {ok:true, model:"claude-sonnet-5", key:true, ...}
curl -s https://acs-engine.onrender.com/v1/understand -H 'Content-Type: application/json' \
  -d '{"text":"فيلا دورين ...","btype":"auto"}' | jq '{levels,rooms,type,report}'

# PART L — CORS preflight (allowed vs disallowed origin)
curl -s -i -X OPTIONS https://acs-engine.onrender.com/v1/understand \
  -H 'Origin: https://sprightly-selkie-d906c3.netlify.app' -H 'Access-Control-Request-Method: POST' \
  | grep -i 'access-control-allow-origin'        # expect the Netlify origin
curl -s -i -X OPTIONS https://acs-engine.onrender.com/v1/understand \
  -H 'Origin: https://evil.example' -H 'Access-Control-Request-Method: POST' \
  | grep -i 'access-control-allow-origin'         # expect NO allow-origin

# PART M — live security headers
curl -s -I https://sprightly-selkie-d906c3.netlify.app \
  | grep -iE 'content-security-policy|x-frame-options|permissions-policy|x-content-type|referrer|cross-origin-opener'
```
Frontend: `https://sprightly-selkie-d906c3.netlify.app` · Backend: `https://acs-engine.onrender.com`.

---

## 17. Exact acceptance criteria to close each remaining row
| Part | PASS when |
|---|---|
| **A Vendoring** | `vendor.sh` self-check ✓ all files; `REVISION='0.160.0'`; addon count = 6; shims present; local importmap live and the only one |
| **B Offline runtime** | `node tools/verify-offline.mjs` prints `RESULT: PASS` (ready=true, engineWarn hidden, 0 page errors) with CDNs blocked |
| **C Real 3D** | villa/hotel/clinic/office/warehouse each render; orbit, clip/section, measurements, sun/shadow, object rendering all work; no critical console errors |
| **H GLB export** | GLB downloads, non-empty, valid, opens in an independent glTF viewer; object nodes present; no requested object missing (record filename, size, viewer result) |
| **I PDF runtime** | PDF upload → pdf.js + worker load → text extraction + first-page render; if vendored, still works with cdnjs blocked; else explicitly documented as accepted online-only dependency (then no CDN-independence claim for PDF) |
| **J Production AI** | `/health` HTTP 200 `ok:true key:true`; `/v1/understand` HTTP 200 coherent building JSON matching prompt; type not forced to warehouse; error handling sane; no secret exposed |
| **L Live CORS** | allowed origin echoed in `Access-Control-Allow-Origin`; disallowed origin gets none; never `*` |
| **M Live CSP** | CSP + `X-Frame-Options: DENY` + `Permissions-Policy` present; app scripts/Three.js/workers/backend fetch all function; zero violations from our own app |
| **O Real mobile** | at 360/390/430: no horizontal overflow AND controls + coverage + 3D canvas + export all usable |
| **P WebXR** | on a WebXR device: ENTER VR, camera, movement, 1:1 scale, exit all work; else remains `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED` |
| **Q CDN failure** | post-vendoring, app loads and renders 3D with unpkg/jsdelivr/cdnjs all blocked (graceful-degradation pre-vendoring already PASS) |

---

## Declarations
- **No Phase 2 work has been started.**
- **No known code defect remains in the locally executable Phase 1 scope.**
- No code, dependencies, configuration, model IDs, or architecture were modified to produce this freeze.
- `PHASE 1 VERIFIED` may be declared only after the rows in §17 are actually executed and pass,
  or are explicitly recorded as `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`.
