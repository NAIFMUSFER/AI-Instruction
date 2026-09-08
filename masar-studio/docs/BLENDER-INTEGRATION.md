# MASAR Blender bridge — first integration candidate

Base: MASAR 4.1.0, production-v4 commit `580e0e11434adf9ff9e08cc5d9bf867dd0f4443b`.
The existing public preview is not changed by this feature branch.

## Implemented architecture

The new visualization panel exports an immutable, validated `masar-render-scene-1`
snapshot. Node derives polygon floor cells, full-height wall segments and the union
of hosted aperture cuts. The contract explicitly uses metres and Z up. Blender
converts those same boxes to real meshes and exports GLB (+Y up), an editable
`.blend`, two Cycles CPU PNG images, and a source-hash/geometry manifest. Each uploaded GLB is independently decoded by
the API: actual transformed vertex corners and bounds must match the source; a self-
reported geometry manifest alone is insufficient. A separate
Three.js viewer provides PBR orbit/picking and loads self-contained GLB. The original
2D/WebGL/Canvas renderer remains available. The optional viewer is compiled locally,
not loaded from a CDN at runtime.

Floor/roof plate thickness, the separate 10 mm floor-finish layer, the simple furniture set, materials, window frames and lighting
are PRESENTATION assumptions, not structural or MEP facts. No external asset catalog,
architectural redesign, SBC approval, IFC round-trip expansion, arbitrary .blend
uploads or Blender-to-MASAR edit synchronization is claimed in this candidate.

The render queue reads the owner's saved project from SQLite; it does not accept a
client-supplied model. It checks both project version and revision ID, strips comments,
raw prompt, references and account data, and hashes canonical snapshot bytes. Repeated
identical requests reuse an active/successful job. Render settings do not modify a
project revision. Old results remain explicitly linked to their original revision.

## Local build and use

Core: Node 22.16+ (existing lockfile has no runtime dependencies).

```
npm ci --ignore-scripts
npm run check
npm run build
npm test
cd render-viewer
npm ci
npm run build
cd ..
npm start
```

Open the studio and choose **إخراج Blender**. **معاينة بالخامات** uses the optional
Three.js viewer. **تنزيل مشهد Blender** writes `MASAR-Blender-Scene.json`; this is an
input for the trusted script below, not a file to open directly in Blender's File menu.

Pin Blender 4.5.13 LTS. For one local scene:

```
blender --background --factory-startup --disable-autoexec --offline-mode --threads 2 \
  --python-exit-code 1 --python render-worker/build_scene.py -- \
  --input MASAR-Blender-Scene.json --output ./render-output
```

The script refuses overwrites and produces `model.blend`, `model.glb`, `exterior.png`,
`interior.png`, `manifest.json`. Filenames/commands/URLs are not customizable by users.
Source units and authored opening dimensions are preserved. Plain PBR materials are
used; Cycles tone mapping/light transport and browser shading are not pixel-identical.

## Optional account-to-worker path

On the API host, explicitly set:

```
BLENDER_RENDER_ENABLED=true
RENDER_WORKER_TOKEN=<generate a unique random secret with at least 32 characters>
RENDER_OUTPUT_DIR=/a/private/durable/path/renders
PERSISTENCE_CLASS=persistent
```

Do NOT mark storage persistent unless both SQLite and render artifacts actually reside
on provisioned durable volumes. The free Render preview remains rendering-disabled.
Never commit the worker secret or share it with a browser. API job actions use the
existing owner session + CSRF checks. The worker uses a separate bearer secret and
per-job expiring lease. Only one job runs at a time. Two pending jobs per user, four
new jobs per user/day, 100 retained jobs overall, two attempts per job, 24 MB per
artifact and seven days' retention are hard candidate limits. Missing worker heartbeat
returns 503. Expired running leases fail explicitly; they are not silently rerun.

Build the isolated processor image on an operator-controlled host:

```
docker build -f render-worker/Dockerfile -t masar-blender:4.5.13 .
MASAR_API_URL=https://your-api.example \
  RENDER_WORKER_TOKEN=<the same secret> node render-worker/worker.mjs
```

The pull worker starts per-job Docker containers with no network, read-only root,
no capabilities, no-new-privileges, PID, CPU, RAM and time limits. Only that job's
temporary directory is writable. The API secret is not passed to Blender. Native
mode (`RENDER_UNSANDBOXED_LOCAL=true node render-worker/worker.mjs --native`) is only
for a trusted local/ephemeral CI machine. Blender's `--offline-mode` preference and
`--disable-autoexec` are not OS sandboxes on their own.

Storage is local-to-API in this first integration (not S3). A persistent deployment
requires one API instance with a durable filesystem and worker reachability. Multiple
API instances require a shared queue/database and object-store adapter not supplied
in this candidate. Automated worker hosting, paid GPU provisioning and durable storage
have NOT been enabled on the user's accounts.

## Test and acceptance boundaries

`tests/render-scene.test.mjs`: determinism, source privacy, input rejection, floor
areas, full-height walls, aperture cuts and unchanged geometry on finish change.
`tests/render-service.test.mjs`: owner isolation, CSRF, missing/expired workers,
idempotency, stale versions, leases, cancellation, retry and quota enforcement.
`tests/render-glb.test.mjs`: real binary vertex readback, coordinate transforms,
missing IDs, external references, changed geometry and hostile hierarchies.
`tests/blender-e2e.mjs`: actual HTTP queue -> actual Blender -> private artifacts;
no mock image generation. `tests/verify_blender_outputs.py` independently decodes GLB
vertices and checks bounds against the input in Y-up coordinates, then checks PNG
size/pixel variance. `tests/verify_blend_file.py` reopens the generated .blend and
checks actual vertex bounds and IDs. Tolerance is 0.05 mm for serialization only,
not an architectural fabrication tolerance.

`tests/browser_render.py`: optional live isolated owner journey, actual PBR/GLB,
picking, image/.blend downloads and responsive dialog. The local system browser
blocks HTTP navigation by administrator policy, so live URL UI verification runs
on the authorized GitHub Actions runner rather than weakening that policy.

No proof of permanent cloud availability or performance at customer scale is claimed.
The original release test reports describe the original release, not this new bridge.
Use the new CI run and its archived reports to determine candidate acceptance.

## Primary implementation references

- https://docs.blender.org/manual/en/4.5/advanced/command_line/arguments.html
- https://docs.blender.org/api/4.5/bpy.ops.export_scene.html
- https://www.blender.org/releases/4-5/
- https://threejs.org/docs/pages/GLTFLoader.html
- https://github.com/mrdoob/three.js/blob/r180/LICENSE

## Repeatable integration checks

```sh
# On an isolated development/CI host with Blender 4.5.13 and a browser installed:
BLENDER_BIN=/path/to/blender MASAR_RENDER_BROWSER=true node tests/blender-e2e.mjs
python tests/verify_blender_outputs.py
blender --background --disable-autoexec test-output/blender/model.blend \
  --python-exit-code 1 --python tests/verify_blend_file.py -- test-output/blender
# For the production-shaped sandbox test (no native processing):
MASAR_RENDER_DOCKER=true MASAR_RENDER_BROWSER=true node tests/blender-e2e.mjs
```

The Blender executable/container is checked before a worker announces availability.
No worker access token is transmitted into the render process. CPU timings describe
only the recorded fixture, not a latency SLA. The generated preview images use plain
PBR materials and schematic furniture; no stock architectural photo or AI image is
used as evidence. Upstream 4.1.0 source version remains unchanged on this feature
branch; the bridge has its own pipeline identifier.
