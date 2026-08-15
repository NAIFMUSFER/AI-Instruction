# AI Construction Studio — External Verification Runbook (Phase 1 Gate)

**Purpose:** execute the runtime tests that the build sandbox could not (blocked network,
no browser 3D, no backend). Run these on (A) a networked developer machine and (B) against
production. Record every result as **PASS / FAIL / NOT VERIFIED** — no assumed PASS.

**Scope reminder:** this is a **general-purpose** construction / digital-twin platform.
Warehouse prompts here are **test fixtures only**. Objects (workers, AMR, forklift, racks,
cars, furniture, people…) are generic object *types*, not warehouse-specific architecture.
Test with several building types (villa, hotel, clinic, office, warehouse) — not warehouse alone.

**Model ID:** `claude-sonnet-5` must **not** be changed unless verified against official
Anthropic docs or the live API. If unverifiable → keep it and record
`NOT VERIFIED — MODEL ID REQUIRES PRODUCTION VERIFICATION`.

Legend used below: **CODE VERIFIED** (already proven in sandbox) · **RUNTIME VERIFIED**
(you confirm here) · **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

---

## A. LOCAL VENDORING PROCEDURE (networked machine)

Goal: eliminate the Three.js (and optionally pdf.js) CDN dependency and prove the app loads
with all external CDNs blocked.

### A.1 Run the vendoring script
```bash
cd <repo-root>
bash tools/vendor.sh
```
**Expected files** under `public/vendor/` (the script self-checks and prints ✓ per file):
```
public/vendor/three@0.160.0/build/three.module.js
public/vendor/three@0.160.0/examples/jsm/controls/OrbitControls.js
public/vendor/three@0.160.0/examples/jsm/webxr/VRButton.js
public/vendor/three@0.160.0/examples/jsm/webxr/ARButton.js
public/vendor/three@0.160.0/examples/jsm/exporters/GLTFExporter.js
public/vendor/three@0.160.0/examples/jsm/objects/Sky.js
public/vendor/three@0.160.0/examples/jsm/environments/RoomEnvironment.js
public/vendor/es-module-shims@1.8.2/es-module-shims.js
public/vendor/pdfjs@4.0.379/pdf.min.mjs          (optional)
public/vendor/pdfjs@4.0.379/pdf.worker.min.mjs   (optional)
```

### A.2 Verify versions & addon completeness
```bash
# Three.js version MUST be 0.160.0
grep -n "REVISION" public/vendor/three@0.160.0/build/three.module.js | head -1
# expect: ... const REVISION = '0.160.0';

# All six imported addons present (must print 6)
ls public/vendor/three@0.160.0/examples/jsm/{controls/OrbitControls,webxr/VRButton,webxr/ARButton,exporters/GLTFExporter,objects/Sky,environments/RoomEnvironment}.js | wc -l

# es-module-shims present
test -s public/vendor/es-module-shims@1.8.2/es-module-shims.js && echo "shims OK"
```
- **PASS:** REVISION is exactly `0.160.0`, the addon count is `6`, shims file non-empty.
- **FAIL:** any file missing or wrong version → do **not** proceed; re-run `vendor.sh`, or copy
  the full `examples/jsm/` tree (see comment in `vendor.sh`) if an addon has internal imports.

### A.3 Activate the LOCAL importmap, disable the CDN one
Edit `public/index.html`:
1. **Disable** the active CDN importmap (currently around line 513):
   ```html
   <!-- <script type="importmap">
   { "imports":{
     "three":"https://unpkg.com/three@0.160.0/build/three.module.js",
     "three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"
   }}
   </script> -->
   ```
2. **Enable** the local importmap (remove the surrounding `<!-- … -->` so this is live):
   ```html
   <script type="importmap">
   { "imports":{
     "three":"/vendor/three@0.160.0/build/three.module.js",
     "three/addons/":"/vendor/three@0.160.0/examples/jsm/"
   }}
   </script>
   ```
3. **(Optional, full offline)** localize es-module-shims: in the `var SHIMS=[…]` array
   (around line 496) make the **first** entry `'/vendor/es-module-shims@1.8.2/es-module-shims.js'`.
4. **(Optional)** localize pdf.js — see Procedure B, test 10.

**Verify the swap is correct (exactly one active importmap, pointing local):**
```bash
grep -nE '^\s*<script type="importmap">' public/index.html         # expect ONE uncommented line
grep -n '/vendor/three@0.160.0/build/three.module.js' public/index.html   # expect it present & uncommented
grep -n 'unpkg.com/three@0.160.0' public/index.html                # expect only inside a comment
```
- **PASS:** exactly one live `<script type="importmap">`, and it references `/vendor/…`.
- **FAIL:** two live importmaps, or the live one still references unpkg.

### A.4 Serve + block CDNs + verify load — automated
```bash
npm i -D playwright && npx playwright install chromium   # one-time
node tools/verify-offline.mjs
```
This serves `public/`, aborts every request to `unpkg.com`, `cdn.jsdelivr.net`,
`cdnjs.cloudflare.com`, loads the app, and checks `window.ACS.ready === true`.
- **PASS condition:** script prints `RESULT: PASS` (ready=true, engineWarn hidden, 0 page errors)
  → **RUNTIME VERIFIED: Three.js + OrbitControls + all addons load with no CDN.**
- **FAIL condition:** `RESULT: FAIL` (usually a missing vendored addon path in console) → fix A.1/A.2.

### A.4-alt Manual browser check (if you prefer DevTools)
1. Serve locally: `python3 -m http.server 8000 --directory public`
2. DevTools → Network → check **"Disable cache"**; DevTools → **Network request blocking** →
   add patterns `*unpkg.com*`, `*cdn.jsdelivr.net*`, `*cdnjs.cloudflare.com*`, enable blocking.
3. Load `http://localhost:8000/`, log in, wait ~3s.
- **PASS:** model canvas renders, no red `#engineWarn` banner, Console has **no** failed
  `three.module.js` / addon requests, and `window.ACS.ready === true` in the Console.
- **FAIL:** banner appears or any addon 404s.

**Do not mark A PASS from file existence alone — only after A.4 (or A.4-alt) actually loads with CDNs blocked.**

---

## B. PRODUCTION VERIFICATION PROCEDURE

URLs (from repo): Frontend `https://sprightly-selkie-d906c3.netlify.app` ·
Backend `https://acs-engine.onrender.com`.

> For each test: **ACTION → EXPECTED → PASS → FAIL.**

### B.1 Netlify production URL loads
- **ACTION:** open `https://sprightly-selkie-d906c3.netlify.app` in Chrome; log in.
- **EXPECTED:** login screen, then the studio UI + 3D canvas; no red engine banner.
- **PASS:** UI renders, `window.ACS.ready===true` in Console, no console errors.
- **FAIL:** engine banner shows, or console shows failed module/addon loads.

### B.2 Render `/health`
- **ACTION:**
  ```bash
  curl -s https://acs-engine.onrender.com/health | jq .
  ```
- **EXPECTED:** `{"ok":true,"model":"claude-sonnet-5","key":true,"limits":{...}}`
  (first call may take ~50s if the instance cold-starts).
- **PASS:** HTTP 200, `ok:true`, `key:true` (secret present but **not** exposed — only a boolean).
- **FAIL:** non-200, `key:false` (API key not set on Render), or timeout after a retry.

### B.3 Render `/v1/understand` — AI generation (multiple building types)
- **ACTION (run each; general-purpose, not warehouse-only):**
  ```bash
  BASE=https://acs-engine.onrender.com
  # Villa
  curl -s $BASE/v1/understand -H 'Content-Type: application/json' \
    -d '{"text":"فيلا دورين: 5 غرف نوم، مجلس، صالة، مطبخ، 4 حمامات، مصعد، درج، وموقفا سيارة","btype":"auto"}' | jq '{levels,rooms,type,report:(.report.requirements|length)}'
  # Hotel
  curl -s $BASE/v1/understand -H 'Content-Type: application/json' \
    -d '{"text":"فندق 8 أدوار: لوبي، استقبال، مطعم، 40 غرفة نزلاء، مصعدان، درج طوارئ","btype":"auto"}' | jq '{levels,rooms,type}'
  # Clinic
  curl -s $BASE/v1/understand -H 'Content-Type: application/json' \
    -d '{"text":"عيادة: استقبال، صالة انتظار، 4 غرف كشف، مختبر، صيدلية","btype":"auto"}' | jq '{levels,rooms,type}'
  ```
- **EXPECTED:** each returns `{building, levels, rooms, type, report}`; `rooms`>0; `report.requirements`
  lists the requested spaces; `type` reflects the description (residential/…); **not** forced to warehouse.
- **PASS:** HTTP 200, coherent building JSON, requirements reflect the prompt, no requested space dropped.
- **FAIL:** HTTP 500 (inspect Render logs — often invalid `ACS_LLM_MODEL`), empty rooms, or type wrongly warehouse.
  - If 500 traces to the model ID → record `NOT VERIFIED — MODEL ID REQUIRES PRODUCTION VERIFICATION`; do **not** change it here.

### B.4 CORS preflight (only the Netlify origin allowed)
- **ACTION:**
  ```bash
  # Allowed origin
  curl -s -i -X OPTIONS https://acs-engine.onrender.com/v1/understand \
    -H 'Origin: https://sprightly-selkie-d906c3.netlify.app' \
    -H 'Access-Control-Request-Method: POST' | grep -i 'access-control-allow-origin'
  # Disallowed origin
  curl -s -i -X OPTIONS https://acs-engine.onrender.com/v1/understand \
    -H 'Origin: https://evil.example.com' \
    -H 'Access-Control-Request-Method: POST' | grep -i 'access-control-allow-origin'
  ```
- **EXPECTED:** first prints `access-control-allow-origin: https://sprightly-selkie-d906c3.netlify.app`;
  second prints **nothing** (no allow-origin for evil).
- **PASS:** allowed origin echoed; disallowed origin gets no ACAO header.
- **FAIL:** `access-control-allow-origin: *`, or the evil origin is echoed → `ACS_ALLOWED_ORIGINS` misconfigured on Render.

### B.5 CSP (headers on the live site)
- **ACTION:**
  ```bash
  curl -s -I https://sprightly-selkie-d906c3.netlify.app | grep -iE 'content-security-policy|x-frame-options|permissions-policy|x-content-type|referrer|cross-origin-opener'
  ```
  Then in Chrome DevTools → Console, load the site and watch for CSP violation errors.
- **EXPECTED:** CSP present with `frame-ancestors 'none'`, `object-src 'none'`,
  `connect-src 'self' https://acs-engine.onrender.com`, `script-src … unpkg/jsdelivr/cdnjs`
  (until vendored); `X-Frame-Options: DENY`; `Permissions-Policy` present.
- **PASS:** headers present **and** no CSP violation blocks app scripts, WebGL, workers, or the backend fetch.
- **FAIL:** any needed resource blocked (adjust CSP), or headers missing (Netlify not applying `netlify.toml`).
- **After Procedure A vendoring is live:** remove the three CDN hosts from `script-src` and re-run B.5.

### B.6 AI generation in the browser (end-to-end)
- **ACTION:** on the live site, paste the villa prompt (B.3) → click **توليد المبنى (genLLM)**.
- **EXPECTED:** status shows engine connected; 3D model builds; **تقرير التغطية** lists the requested spaces.
- **PASS:** model renders and coverage matches the prompt.
- **FAIL:** falls back to local with an error (then B.2/B.3 diagnose the backend).

### B.7 Object preservation — BOTH paths (fixture)
- **ACTION (Local):** Advanced → temporarily clear the engine URL (or block the backend) →
  generate `مستودع 100×60 فيه ستة عمال واثنين AMR ورافعة شوكية`.
- **ACTION (AI):** restore backend → generate the same text via **genLLM**.
- **EXPECTED:**
  ```
  Requested:  worker×6 · AMR×2 · forklift×1
  Generated:  worker×6 · AMR×2 · forklift×1   (visible in the 3D scene)
  Unsupported: 0     Dropped: 0
  ```
- **PASS (Local):** already **CODE VERIFIED** in sandbox (data layer) — confirm the meshes render in-browser here.
- **PASS (AI):** backend returns the objects and they render.
- **FAIL:** any requested object missing from scene **and** absent from the coverage report.
- If the backend can't run: record AI path `NOT VERIFIED`.

### B.8 JSON export
- **ACTION:** generate a building that includes spaces + objects (e.g., B.7) → click **بيانات JSON (bJson)** →
  open the downloaded `.json`.
- **EXPECTED / PASS:** file is non-empty and contains `floors…rooms[].objects` (the workers/AMR/forklift),
  plus `meta.requirements` and `meta.excluded`. Modify the model (engineer note) → re-export → change is present.
- **FAIL:** objects, coverage, or exclusions missing, or edits not reflected. *(Data layer is CODE VERIFIED; this confirms the browser download.)*

### B.9 GLB export
- **ACTION:** generate a building → click **GLB (bGlb)** → note file size → open the `.glb` in
  a glTF viewer (e.g. `https://gltf-viewer.donmccurdy.com/` or Blender import).
- **EXPECTED:** download completes; file is **non-empty** (well over a few KB); opens without error;
  geometry matches the on-screen model; requested objects present.
- **PASS:** valid, non-empty GLB whose contents match the model (incl. objects).
- **FAIL:** 0-byte/tiny file, viewer parse error, or missing geometry.

### B.10 PDF import
- **ACTION:** import a real architectural PDF via the file control.
  - If **pdf.js vendored** (Procedure A optional): repeat with CDNs blocked (A.4 network-block).
- **EXPECTED:** text-based PDF → parsed and a model is built or the vision path runs; first-page preview renders;
  a scanned/no-text PDF → an accurate "no text" message (not fake progress).
- **PASS:** extraction/preview works; worker path loads (if vendored, works with cdnjs blocked).
- **FAIL:** silent failure, fake progress, or (if vendored) still requires cdnjs.
  If left CDN-only by choice: record **PDF import = optional online-only feature** (acceptable per gate).

### B.11 WebXR / VR
- **ACTION:** on a WebXR device (Quest browser, or Chrome + WebXR emulator) open the site → **ENTER VR**.
- **EXPECTED:** VR session starts; 1:1 scale; look/move works; exit returns cleanly. On a non-XR browser,
  an accurate "WebXR not supported / needs https" message appears (no fake VR).
- **PASS:** VR works on device **or** an accurate unsupported message on non-XR.
- **FAIL:** claims VR without a session, or crashes.
- No device? → `NOT VERIFIED — WEBXR DEVICE REQUIRED`.

### B.12 Mobile
- **ACTION:** load the live site at widths **360 / 390 / 430** (DevTools device toolbar or real phones).
- **EXPECTED:** no horizontal overflow; tabs, generate button, coverage report, and 3D canvas all usable
  (pan/orbit by touch).
- **PASS:** no overflow **and** controls + canvas usable at all three widths.
- **FAIL:** horizontal scroll, unreachable controls, or dead canvas. *(No-overflow of the UI chrome is CODE VERIFIED; confirm canvas usability live.)*

### B.13 CDN failure resilience (live)
- **ACTION:** in DevTools → Network request blocking, block `*unpkg.com*`, `*cdn.jsdelivr.net*`,
  `*cdnjs.cloudflare.com*`; hard-reload.
  - **Before** Procedure A: expect the red `#engineWarn` banner + working login (graceful, no crash).
  - **After** Procedure A (local importmap live): expect the **app to still load and render** (no banner).
- **PASS (before vendoring):** accurate banner + reload button, base UI still works (**CODE VERIFIED** in sandbox — reconfirm live).
- **PASS (after vendoring):** 3D loads with all CDNs blocked (this is the real Finding-2 closure; ties to A.4).
- **FAIL:** blank page with no message, or (post-vendor) still fails with CDNs blocked.

---

## B-COORD. Multidisciplinary coordination & clash foundation (executed offline)

Detection and traceability only. Every command references a repository file.

```
node tests/lib/run.js tests/phase2/test_coord.js            # 131 checks
python3 tests/phase2/parity/py_coord.py
node tests/lib/run.js tests/phase2/parity/js_coord_body.js
node tests/phase2/parity/compare.js coord                   # 20/20 byte-identical
node tests/phase3/lib/run_browser.js "$PWD/tests/phase2/test_coord.js"   # real Chromium
```

| # | Test | Result | Evidence |
|---|------|--------|----------|
| CO.1 | Detector compiles and imports | PASS | `py_compile` clean |
| CO.2 | Browser spec byte-identical to `acs_coord.json` | PASS | drift test §1 |
| CO.3 | TEST A duct through beam → `HARD_CLASH`, MEP↔STRUCTURE, `stated` | PASS | §2 |
| CO.4 | TEST B pipe through wall, no penetration → `OPENING_REQUIRED` | PASS | §3 |
| CO.5 | TEST C covering penetration suppresses and logs | PASS | §3 |
| CO.6 | TEST C2 misplaced penetration → `PENETRATION_UNRESOLVED` | PASS | §3 |
| CO.7 | TEST D column in a declared door opening reported | PASS | §4 |
| CO.8 | TEST E duplicate FLS device → `DUPLICATE_OCCUPANCY` (INFO) | PASS | §4 |
| CO.9 | TEST F 0°/45°/90° find the same conflicts, different coordinates | PASS | §5 |
| CO.10 | TEST G multi-building: 30 m apart clean, 1 m apart clashes | PASS | §6 |
| CO.11 | TEST H stale snapshot + reconciliation states | PASS | §7 |
| CO.12 | TEST I dangling cross-discipline refs → ERROR findings | PASS | §8 |
| CO.13 | Every exemption semantic and recorded | PASS | §9 |
| CO.14 | Clearance only where stated | PASS | §10 |
| CO.15 | No auto-fix / no mutation of any model | PASS | §11 |
| CO.16 | Navigation and egress unchanged | PASS | §12 |
| CO.17 | Emitted 3D geometry identical before/after the layer | PASS | `mesh_invariance_dump.js` |
| CO.18 | Debug marker excluded from GLB | PASS | marker added to scene, exporter parses `model` |
| CO.19 | JS↔Python parity | PASS | 20/20 byte-identical |
| CO.20 | Developer API behaves as documented | PASS | 17/17 probe (Phase 2 session) |
| CO.21 | Full WebGL pixel output of the debug overlay | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | `public/vendor/` empty |
| CO.22 | Live Render backend with the new module | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | `fastapi` absent in this sandbox |

---

## B-VISUAL. Visual rendering & presentation foundation (executed offline)

Geometry-preserving visualisation only. Every command below references a file that lives in the
repository: a clean checkout reproduces these numbers without reconstructing anything.

**Dependencies.** Python 3 (standard library only) and Node.js are required. `playwright` and a
Chromium build are required only for the real-browser pass.

```
git clone <repo> && cd <repo>

# everything except the real browser
sh tests/phase3/run_all.sh

# add the real-browser pass
sh tests/phase3/run_all.sh --browser
```

Individual steps, if you prefer to run them one at a time:

```
python3 -m py_compile acs_*.py                              # syntax
node tests/phase3/gen_visual_fixtures.js                    # regenerate scenarios
node tests/phase3/lib/run.js test_visual.js                 # 211 checks
node tests/phase3/lib/run.js test_visual_adversarial.js     # 115 checks
node tests/phase3/lib/run.js test_dev_api.js                # 31 checks
python3 tests/phase3/parity/py_visual.py                    # Python parity side
node tests/phase3/lib/run.js parity/js_visual_body.js       # JavaScript parity side
node tests/phase3/parity/compare.js                         # 116/116 + 16/16 adversarial
python3 tests/security/test_security.py                     # 141 checks
node tests/phase3/lib/run.js perf_visual.js                 # deterministic benchmarks
python3 tests/phase3/perf_visual.py
node tests/phase3/lib/run_browser.js "$PWD/tests/phase3/test_visual.js"   # real Chromium
```

Phase 1 and Phase 2 regression, also from repository files:

```
for f in tests/phase1/*.js tests/phase2/test_*.js; do node tests/lib/run.js "$f"; done
for n in arch struct mep fls ing occ rev rules dist coord; do
  python3 tests/phase2/parity/py_$n.py
  node tests/lib/run.js tests/phase2/parity/js_${n}_body.js
  node tests/phase2/parity/compare.js $n
done
```

`tests/phase1/test_gate.js` and `tests/phase1/test_prov.js` require a DOM and pass only through
`tests/phase3/lib/run_browser.js`; under plain Node they exit with a `document is not defined`
error, which is expected and is not a failure of the code under test.

| # | Test | Result | Evidence |
|---|------|--------|----------|
| VI.1 | Compiler compiles and imports (20 modules) | PASS | `run_all.sh` step 0 |
| VI.2 | Browser spec byte-identical to `acs_visual.json` | PASS | `test_visual.js` §1 |
| VI.3 | No engineering geometry mutation, any mode/theme/quality | PASS | §2 |
| VI.4 | Emitted mesh trees identical before/after remediation | PASS | `mesh_invariance_dump.js`, 8 models |
| VI.5 | Universal visual-only source invariant (both directions) | PASS | `test_visual_adversarial.js` A/B |
| VI.6 | Nine visual modes over one model, one model hash | PASS | §4, §25 |
| VI.7 | Materials are VISUAL_MATERIAL with no engineering property | PASS | §5, adversarial E |
| VI.8 | Material provenance separates USER / THEME / SYSTEM / AI | PASS | §5 |
| VI.9 | Themes change appearance only; hash unchanged | PASS | adversarial G |
| VI.10 | Decoration off by default, visual-only, excluded everywhere | PASS | §7, adversarial |
| VI.11 | Site, landscape and water are never invented | PASS | §8, adversarial |
| VI.12 | Dollhouse and cutaway are reversible view state | PASS | §9 |
| VI.13 | 2D plans project the real geometry | PASS | §10 |
| VI.14 | Dimensions come from the model or stay null | PASS | §11 |
| VI.15 | Sections and elevations project real geometry only | PASS | §12, §13 |
| VI.16 | Camera framing from model bounds; no geometry regenerated | PASS | §14 |
| VI.17 | Presentation lights are not MEP luminaires | PASS | §15 |
| VI.18 | Quality/LOD/instancing never touch modelled elements | PASS | §16 |
| VI.19 | Snapshot clamps, refuses bad formats, records metadata | PASS | §17, adversarial |
| VI.20 | A render of a changed model is STALE, never current | PASS | §18 |
| VI.21 | AI interface cannot write to the model; no generator ships | PASS | §19, adversarial |
| VI.22 | Each requested control buffer travels with a descriptor | PASS | adversarial, contract block |
| VI.23 | A signature-less AI request is rejected | PASS | adversarial D |
| VI.24 | Drift detection flags layout change; `model_modified:false` | PASS | adversarial C |
| VI.25 | Engineering view cannot hide a discipline | PASS | adversarial H |
| VI.26 | Asset metadata never executed; no unknown license emitted | PASS | adversarial F |
| VI.27 | VR is 1:1 unless scaling is explicit | PASS | adversarial |
| VI.28 | Python↔JS parity, including adversarial agreement | PASS | 116/116 · 16/16 |
| VI.29 | Developer API behaves as documented | PASS | 31/31 |
| VI.30 | Real WebGL pixels, materials, shadows, textures | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | `public/vendor/` empty, no outbound network |
| VI.31 | FPS and texture memory on target devices | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | no WebGL context in this sandbox |

---

## B-RUNTIME. Interactive walkthrough & deterministic simulation runtime foundation (executed offline)

Deterministic, read-only interaction only. The flow is one-way and never reverses:

```
CANONICAL ENGINEERING MODEL -> COORDINATION -> VISUAL SCENE -> RUNTIME SCENE -> RUNTIME STATE -> USER INTERACTION
```

**RUNTIME IS EPHEMERAL. ENGINEERING MODEL IS IMMUTABLE.**

Every command below references a file that lives in the repository. A clean checkout reproduces
these numbers without reconstructing anything, and `run_all.sh` works from any working directory.

**Dependencies.** Python 3 (standard library only) and Node.js are required. `playwright` and a
Chromium build are required only for the real-browser pass.

```
git clone <repo> && cd <repo>

# everything except the real browser
sh tests/phase4/run_all.sh

# add the real-browser pass (Chromium via Playwright)
sh tests/phase4/run_all.sh --browser
```

Individual steps, if you prefer to run them one at a time:

```
python3 -m py_compile acs_*.py                                   # syntax
python3 tools/build_runtime_browser.py                           # regenerate the browser layer
node tests/phase3/gen_visual_fixtures.js                         # Phase 3 scenarios
node tests/phase4/fixture_generator.js                           # Phase 4 scenarios

node tests/lib/run.js tests/phase4/test_runtime.js               # 49 checks
node tests/lib/run.js tests/phase4/test_navigation.js            # 39 checks
node tests/lib/run.js tests/phase4/test_collision.js             # 73 checks
node tests/lib/run.js tests/phase4/test_portals.js               # 45 checks
node tests/lib/run.js tests/phase4/test_selection.js             # 113 checks
node tests/lib/run.js tests/phase4/test_visibility.js            # 145 checks
node tests/lib/run.js tests/phase4/test_measurement.js           # 131 checks
node tests/lib/run.js tests/phase4/test_immutability.js          # 135 checks
node tests/lib/run.js tests/phase4/test_adversarial.js           # 457 checks

node tests/phase4/test_model_regression.js                       # 22 checks
node tests/phase4/test_parity.js                                 # 17 checks (runs both sides)
python3 tests/phase4/parity/py_runtime.py                        # Python parity side
node tests/lib/run.js tests/phase4/parity/js_runtime_body.js     # JavaScript parity side
node tests/phase4/parity/compare.js                              # 19/19 + 16/16 + 357/357

python3 tests/security/test_security.py                          # 141 checks
sh tests/phase3/run_all.sh                                       # Phase 1/2/3 regression

node tests/lib/run.js tests/phase4/benchmark_runtime.js          # timings, no FPS claim
python3 tests/phase4/benchmark_runtime.py                        # timings, no FPS claim

node tests/phase4/test_browser_parity.js                         # 44 checks, real Chromium
```

### What this phase does NOT verify

| # | Item | Status | Why |
|---|------|--------|-----|
| RT.1 | Real WebGL pixels, materials, shadows, textures | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | `public/vendor/` is empty; no outbound network in the offline environment |
| RT.2 | Frames per second, GPU behaviour, texture memory | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | no WebGL context; no such claim is made anywhere in this phase |
| RT.3 | Pointer, touch, gamepad and headset input devices | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | no input hardware; the runtime contract is device-independent |
| RT.4 | The live Render backend | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED | no outbound network |

### Out of scope by contract, not by omission

No agent, no LLM control of the runtime, no generative geometry, no geometry editing, no BIM
authoring, no crowd or evacuation simulation, no fire or smoke propagation, no CFD, no thermal or
structural simulation, no vehicle or robot physics, no live digital twin, no IoT, no multiplayer,
no network sync, no VR controllers, no AR, no native mobile app, no pathfinding agents, no NPCs,
no gameplay, no physics engine, no design optimisation and no automatic engineering decision.
The runtime exposes no model-write path of any kind; an attempt to request one is refused with
`RUNTIME_MODEL_WRITE_ATTEMPT`.

---

## B-AUTHORING. Project authoring & controlled editing foundation (executed offline)

Controlled model mutation only. The runtime still has no write path; authoring is a separate
subsystem reached through an explicit transaction:

```
USER ACTION -> AUTHORING COMMAND -> VALIDATION/PREVIEW -> TRANSACTION
            -> explicit commit -> NEW REVISION -> rebuild Coordination/Visual/Runtime
```

**RUNTIME IS EPHEMERAL. ENGINEERING MODEL IS IMMUTABLE. NO SILENT EDITS.**

```
git clone <repo> && cd <repo>

# everything except the real browser
sh tests/phase5/run_all.sh

# add the real-browser pass (Chromium via Playwright)
sh tests/phase5/run_all.sh --browser
```

Individual steps:

```
python3 -m py_compile acs_*.py                                    # syntax
python3 tools/build_runtime_browser.py                            # runtime layer
python3 tools/build_authoring_browser.py                          # authoring layer
node tests/phase5/fixture_generator.js                            # Phase 5 scenarios

node tests/lib/run.js tests/phase5/test_authoring.js              # 127 checks
node tests/lib/run.js tests/phase5/test_commands.js               # 180 checks
node tests/lib/run.js tests/phase5/test_transaction.js            # 120 checks
node tests/lib/run.js tests/phase5/test_revision.js               #  89 checks
node tests/lib/run.js tests/phase5/test_ai_boundary.js            #  67 checks
node tests/lib/run.js tests/phase5/test_integration.js            #  70 checks
node tests/lib/run.js tests/phase5/test_immutability.js           # 105 checks
node tests/lib/run.js tests/phase5/test_adversarial.js            # 519 checks
node tests/lib/run.js tests/phase5/test_browser.js                #  55 checks

node tests/phase5/test_parity.js                                  #  35 checks
python3 tests/phase5/parity/py_authoring.py                       # Python parity side
node tests/lib/run.js tests/phase5/parity/js_authoring_body.js    # JavaScript parity side
node tests/phase5/parity/compare.js                               # 63/63 + 40/40 adversarial

python3 tests/security/test_security.py                           # 151 checks
sh tests/phase4/run_all.sh                                        # Phase 1/2/3/4 regression

node tests/lib/run.js tests/phase5/benchmark_authoring.js         # timings, no FPS claim
python3 tests/phase5/benchmark_authoring.py                       # timings, no FPS claim

node tests/phase5/test_browser_parity.js                          #  43 checks, real Chromium
```

### Restoring or re-taking the geometry baseline

`tests/phase3/mesh_invariance_dump.js` writes its output to `ACS_GEOM_OUT` (a `.json` path). It
refuses to write over a JavaScript source file — under the unified runner `process.argv[2]` is
the test file itself, which previously caused the script to overwrite its own source.

```
ACS_GEOM_OUT=/tmp/geom.json node tests/lib/run.js tests/phase3/mesh_invariance_dump.js
node tests/phase4/test_model_regression.js     # compares against the vendored baseline
```

### What this phase does NOT verify

| # | Item | Status |
|---|------|--------|
| AU.1 | Real WebGL pixels, materials, shadows, textures | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| AU.2 | Frames per second, GPU behaviour, texture memory | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| AU.3 | Pointer, touch and headset input driving the gizmos | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| AU.4 | The live Render backend | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |

### Out of scope by contract

No collaboration, no multiplayer, no real-time co-editing, no WebSocket synchronisation, no
CRDTs, no cloud persistence, no full BIM authoring, no design optimisation and no autonomous AI
editing. No coordination clash is auto-fixed, no MEP is auto-rerouted, no structure is
auto-redesigned, no code-required element is auto-added, and no code-compliance decision mutates
geometry.

---

## B-WORKSPACE. Product workspace & professional authoring UI (executed offline)

The product surface over the Phase 1–5 engines. A person completes real work without a
console API, and every engineering change still travels the Phase 5 command path.

```
CREATE PROJECT -> REQUIREMENTS -> GENERATE -> EXPLORE 3D -> SELECT -> INSPECT
              -> EDIT MODE -> PREVIEW -> COMMIT or CANCEL -> WARNINGS
              -> REVISION HISTORY -> EXPORT
```

**THE INTERFACE NEVER MUTATES ENGINEERING JSON. NO AI AUTO-COMMIT. NO AUTO-FIX.**

```
git clone <repo> && cd <repo>

# everything except the real browser
sh tests/phase6/run_all.sh

# add the real-browser pass (Chromium via Playwright)
sh tests/phase6/run_all.sh --browser
```

Individual steps:

```
python3 -m py_compile acs_*.py                                     # syntax
python3 tools/build_runtime_browser.py                             # runtime layer
python3 tools/build_authoring_browser.py                           # authoring layer
python3 tools/build_workspace_ui.py                                # workspace UI, DOM, styles

node tests/lib/run.js tests/phase6/test_workspace.js               # 113 checks
node tests/lib/run.js tests/phase6/test_workflow.js                # 153 checks
node tests/lib/run.js tests/phase6/test_dom.js                     # declares NOT VERIFIED in Node
node tests/lib/run.js tests/phase6/test_security.js                # 167 checks in Node

node tests/phase6/test_parity.js                                   #  47 checks
python3 tests/phase6/parity/py_workspace.py                        # Python parity side
node tests/lib/run.js tests/phase6/parity/js_workspace_body.js     # JavaScript parity side
node tests/phase6/parity/compare.js                                # 20/20 byte-identical

python3 tests/security/test_security.py                            # 166 checks
sh tests/phase5/run_all.sh                                         # Phase 1/2/3/4/5 regression

node tests/lib/run.js tests/phase6/benchmark_workspace.js          # timings, no FPS claim
python3 tests/phase6/benchmark_workspace.py                        # timings, no FPS claim

node tests/phase3/lib/run_browser.js "$PWD/tests/phase6/test_dom.js"       # 197, Chromium
node tests/phase3/lib/run_browser.js "$PWD/tests/phase6/test_security.js"  # 238, Chromium
node tests/phase6/test_responsive.js                               #  87 checks, 7 widths + RTL
node tests/phase6/walkthrough.js                                   #  17-step product walkthrough
```

Screenshots land in `tests/phase6/screenshots/` (EMPTY, PROJECT_GENERATED, ROOM_SELECTED,
EDIT_PREVIEW, ISSUE_SELECTED, MOBILE, RTL). They are layout and state evidence only — no
claim of pixel identity across GPU environments is made anywhere.

The walkthrough writes `tests/phase6/walkthrough_result.json` with one verdict per step:
PASS / FAIL / NOT_SUPPORTED / NOT_VERIFIED.

### What this phase does NOT verify

| # | Item | Status |
|---|------|--------|
| WS.1 | Real WebGL pixels in the workspace viewport | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| WS.2 | Frames per second, GPU behaviour, render latency | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| WS.3 | Pointer, touch and headset input driving gizmos and camera | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| WS.4 | Screenshot pixel identity across machines | NOT CLAIMED BY CONTRACT |
| WS.5 | Photorealistic rendering | NOT IMPLEMENTED — declared, boundary only |
| WS.6 | The live Render backend | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |

### Known limitation carried forward

Contract disclosure notes shown in the inspector and the references panel are presented in
English in both languages and are marked `data-ws-note="canonical" lang="en"` in the DOM.
Translating a disclosure risks shifting its engineering meaning, so it is flagged rather
than translated. Everything else in the shell is localised from `acs_workspace.json`.

### Production verification checklist for the workspace (real hardware)

1. Vendor Three.js into `public/vendor/`, load the app with the network disabled, and
   confirm the workspace viewport draws the model.
2. Walk the seventeen steps by hand on a desktop browser and on a real phone; record each
   as PASS / FAIL / NOT_SUPPORTED.
3. Confirm the toolbar scrolls (not clips) at 390 px on a real device, and that every
   control is reachable by touch.
4. Confirm Arabic renders right-to-left with no mixed-language shell text, and that
   switching language keeps selection, mode and preview.
5. Export each of the five kinds and confirm each file names the committed revision id and
   model hash, and claims no certification.

### Out of scope by contract

No cloud collaboration, no photorealistic AI rendering, no automatic engineering design, no
BIM interoperability and no autonomous design. The workspace adds no engineering
calculation, resolves no clash automatically and repairs no model.

---

## B-RENDER. Photorealistic visualization & AI presentation engine (executed offline)

Presentation output derived from the canonical model. The deterministic base render is the
geometry authority; AI enhancement is optional and strictly downstream.

```
MODEL -> VISUAL SCENE -> CAMERA/MATERIAL/LIGHTING -> BASE RENDER
      -> CONTROL BUFFERS -> OPTIONAL AI -> PRESENTATION IMAGE
```

**NO REVERSE WRITE. AN AI IMAGE NEVER BECOMES MODEL TRUTH.**

```
sh tests/phase7/run_all.sh              # everything except real Chromium
sh tests/phase7/run_all.sh --browser    # adds Chromium
```

Individual steps:

```
python3 tools/build_render_browser.py                            # render engine + panel
node tests/phase7/fixture_generator.js                           # glazed fixtures

node tests/lib/run.js tests/phase7/test_render.js                # 272 checks
node tests/lib/run.js tests/phase7/test_targets.js               #  93 checks (Tests A-L)
node tests/lib/run.js tests/phase7/test_security.js              # 163 checks in Node
node tests/phase7/test_parity.js                                 #  49 checks
python3 tests/security/test_security.py                          # 189 checks
sh tests/phase6/run_all.sh                                       # Phase 1-6 regression
node tests/lib/run.js tests/phase7/benchmark_render.js           # timings, no FPS claim
node tests/lib/run.js tests/phase7/make_outputs.js               # 47 real output files
node tests/phase3/lib/run_browser.js "$PWD/tests/phase7/test_security.js"   # 242, Chromium
```

Generated presentation output lands in `tests/phase7/outputs/` with a `MANIFEST.json`
naming the revision and model hash behind every file: floor plans, four elevations and two
sections per model as SVG, plus four control buffers per model as PNG.

### Verification classes used in this phase

| Class | Meaning |
|---|---|
| CODE_VERIFIED | proven by an executed test |
| RUNTIME_VERIFIED | real pixels produced by a real engine |
| AI_VERIFIED | a real provider returned an image |
| NOT_VERIFIED | requires an environment this sandbox lacks |

### What this phase does NOT verify

| # | Item | Status |
|---|------|--------|
| RD.1 | WebGL base render, materials, shadows, SSAO, post-processing | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| RD.2 | Frames per second, GPU behaviour, shader compilation | NOT MEASURED — no such claim is made |
| RD.3 | A real AI provider returning an image | NOT VERIFIED — no provider reachable |
| RD.4 | Feature extraction from a photographic AI image | NOT IMPLEMENTED — declared boundary |
| RD.5 | Panorama and VR_PREVIEW raster output | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| RD.6 | Photorealistic generation | NOT SHIPPED — adapter boundary only |

Chromium in this sandbox does report WebGL 2.0 through SwiftShader; the blocker is the
missing Three.js vendor bundle, not the browser.

### Production verification checklist for rendering (real hardware)

1. Vendor Three.js into `public/vendor/`, load with the network disabled, and confirm the
   base render draws the model.
2. Produce each of the eleven view types and confirm each is the same model.
3. Configure a real AI provider key **in the server environment only**; confirm no key
   appears in client source, render metadata or logs.
4. Run an AI enhancement and confirm the drift detector classifies the result; confirm a
   rejected image is never presented as model faithful.
5. Confirm a provider timeout leaves the deterministic render as the output.
6. Confirm exports at 1920×1080, 2560×1440 and 3840×2160 report the resolution actually
   rendered.

### Out of scope by contract

No BIM interoperability, no cloud collaboration, no automatic structural or MEP design, no
autonomous design. No render mutates the model, and no AI image becomes model truth.

---

## B-BIM. BIM interoperability & exchange foundation (executed offline)

Deterministic exchange between the canonical engineering model and real IFC4 STEP files.
The canonical model stays the only engineering authority.

```
IMPORT: IFC FILE -> STEP PARSER -> STAGING MODEL -> VALIDATION -> SEMANTIC MAPPING
        -> DIFF/CONFLICT/LOSS -> PROPOSALS -> EXPLICIT ACCEPTANCE
        -> PHASE 5 AUTHORING PATH -> CANONICAL MODEL
EXPORT: CANONICAL MODEL -> BIM MAPPING -> EXCHANGE MODEL -> VALIDATION
        -> SERIALISATION -> IFC FILE
```

**NO EXTERNAL BIM FILE BECOMES MODEL TRUTH. NO IMPORT WRITES WITHOUT AN EXPLICIT COMMIT.**

```
sh tests/phase8/run_all.sh              # everything except real Chromium
sh tests/phase8/run_all.sh --browser    # adds Chromium, and cascades --browser to phase 7
```

Individual steps:

```
python3 tools/build_bim_browser.py                               # exchange layer + panel
python3 tests/phase8/fixture_generator.py                        # staged fixtures from real IFC

python3 tests/phase8/test_bim.py                                 # 526 checks
node    tests/phase8/test_parity.js                              #  53 checks
node    tests/lib/run.js tests/phase8/test_bim_browser.js        #   4 checks in Node scope
python3 tests/security/test_security.py                          # 259 checks (S-B1..S-B22)
sh      tests/phase7/run_all.sh --browser                        # Phase 1-7 regression
python3 tests/phase8/benchmark_bim.py                            # CPU timings, no FPS claim
python3 tests/phase8/make_outputs.py                             # 41 real artifacts
node    tests/phase3/lib/run_browser.js "$PWD/tests/phase8/test_bim_browser.js"   # 58, Chromium
```

Artifacts land in `tests/phase8/outputs/` with `index.json` naming the model hash, revision,
entity count, file hash and round-trip verdict behind every file: 13 IFC files, 13 export
manifests, 12 round-trip reports and 1 import report.

### Verification classes used in this phase

| Class | Meaning |
|---|---|
| CODE_VERIFIED | proven by an executed test |
| RUNTIME_VERIFIED | real files written, read back and compared; real Chromium |
| INTEROP_VERIFIED | an independent implementation read or wrote the file |
| NOT_VERIFIED | requires an environment this sandbox lacks |

**INTEROP_VERIFIED: none.** Internal export followed by internal import is not
interoperability and is not reported as such.

### What this phase does NOT verify

| # | Item | Status |
|---|------|--------|
| BM.1 | Independent IFC validation of the produced files | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| BM.2 | Opening the files in Revit / ArchiCAD / Solibri | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| BM.3 | Importing a file authored by a third-party tool | NOT VERIFIED — no such file exists here |
| BM.4 | WebGL display of imported geometry | NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED |
| BM.5 | IFC2X3 writing | OUT OF SCOPE — readable only |
| BM.6 | Swept-solid / B-rep / CSG conversion to canonical geometry | NOT IMPLEMENTED — read and preserved, not converted |
| BM.7 | Authoring commands for resize / add / remove proposals | NOT IMPLEMENTED — proposed, then reported unsupported at commit |

### Production verification checklist for exchange (real tools)

1. Open `tests/phase8/outputs/villa_glazed.ifc` in Revit, ArchiCAD and Solibri. Record what
   each reads: level count, space count, wall count, door and window count.
2. Run the buildingSMART IFC4 validator (or `ifcopenshell`) against every file in
   `tests/phase8/outputs/`. Record every reported issue verbatim.
3. Export a real project from Revit as IFC4 and import it here. Confirm the staging summary
   reports its schema, units, counts and unsupported entities without refusing the whole file.
4. Confirm no proposal from that import writes anything until an explicit commit, and that the
   commit lands in ordinary revision history.
5. Re-export after the commit and diff the two files; confirm only the committed change moved.
6. Only after 1-5 are recorded may any `INTEROP_VERIFIED` claim be made, and only for the
   tools actually exercised.

### Out of scope by contract

No cloud collaboration, no automatic structural or MEP design, no code-compliance engine, no
autonomous design, no AI engineering auto-edit, no multi-user cloud authoring, no live Revit
sync. No export mutates the model, and no import writes outside the Phase 5 authoring path.

---

## B-VISUAL-PROD. Production verification checklist (must be run on real hardware)

Because visual rendering is the purpose of this phase, the pixels themselves must be signed off in a
real browser. Everything below is deliberately **not** claimed as verified here.

**Setup**
1. Vendor Three.js and its addons into `public/vendor/` and confirm the page loads with the network
   disabled (`ACS.ready === true`).
2. Open the app, load the villa example, and confirm `ACS.visualScene()` returns a scene whose
   `model_hash` matches `ACS.coordination().revision_hash`.

**Real WebGL**
3. `ACS.applyVisualMode('PRESENTATION')` — confirm finishes, sky, shadows and tone mapping appear
   and that no wall, door or window moved. Compare against `ACS.applyVisualMode('ENGINEERING')`.
4. Confirm `ACS.clearVisualMode()` restores the original materials and visibility exactly.
5. Toggle `ACS.applyVisualMode('DOLLHOUSE')` — roof and ceilings hidden, interiors readable from
   above, rooms in their exact positions. Confirm it is reversible.
6. `ACS.applyVisualMode('CUTAWAY', {cutaway:{nz:1, constant:5}})` — confirm a live clipping plane
   and that clearing restores the full model.
7. Cycle LOW / MEDIUM / HIGH / ULTRA and record real FPS for villa, hotel, warehouse and a
   1 000-space project. Record draw calls and texture memory from the WebGL inspector.
8. Cycle DAY / GOLDEN_HOUR / NIGHT and confirm shadows, exposure and night interior emitters.

**Drawings and images**
9. `ACS.floorPlan2D(0)` and `(1)` for the villa — render and confirm walls, openings, room names,
   stairs and dimensions match the plan on screen.
10. `ACS.sectionView('x', 2.5)` and `ACS.elevationView('NORTH'|'SOUTH'|'EAST'|'WEST')` — confirm
    they match the 3D model.
11. `ACS.snapshot({width:3840,height:2160})` — confirm a real PNG data URL is returned,
    `rendered === true`, and the metadata carries the current model hash. Repeat as JPEG.
12. Change the model, then re-check the earlier render metadata with `ACS.renderCurrency()` —
    it must report `STALE_MODEL_CHANGED`.

**Exports**
13. Export the engineering GLB and confirm no visual-only object, no decoration, no landscape and
    no debug marker is present. Export a presentation GLB separately and confirm they differ.

**Mobile and VR**
14. Verify at 360 / 390 / 430 px widths that presentation mode is usable and that quality drops
    gracefully.
15. Enter WebXR on a headset, confirm 1 model metre reads as 1 physical metre, and confirm the VR
    view shows the same geometry as presentation.

**Declare `PHASE 3 VISUAL VERIFIED` only when every row above is PASS on real hardware.**

---

## C. Result recording template

| # | Test | Result | Evidence / notes |
|---|------|--------|------------------|
| A | Local vendoring + offline load | PASS / FAIL | `verify-offline` output |
| B.1 | Netlify loads | PASS / FAIL | |
| B.2 | /health | PASS / FAIL / NV | |
| B.3 | /v1/understand (villa/hotel/clinic) | PASS / FAIL / NV | model-ID note if 500 |
| B.4 | CORS preflight | PASS / FAIL | |
| B.5 | CSP headers | PASS / FAIL | |
| B.6 | AI gen in browser | PASS / FAIL / NV | |
| B.7 | Object preservation (local+AI) | PASS / FAIL / NV | |
| B.8 | JSON export | PASS / FAIL | |
| B.9 | GLB export | PASS / FAIL | viewer screenshot |
| B.10 | PDF import | PASS / FAIL / online-only | |
| B.11 | WebXR | PASS / FAIL / NV | |
| B.12 | Mobile 360/390/430 | PASS / FAIL | |
| B.13 | CDN failure | PASS / FAIL | before & after vendoring |

**Declare `PHASE 1 VERIFIED` only when every row is PASS or an explicit
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`, with no known code defect.**
Keep `claude-sonnet-5` unchanged unless verified against official Anthropic docs / live API.
