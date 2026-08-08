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
