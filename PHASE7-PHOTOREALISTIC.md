# Phase 7 — Photorealistic Visualization & AI Presentation Engine

**Production visual output. Geometry-preserving. Model-conditioned AI.
No engineering mutation. No AI redesign.**

---

## 0. The pipeline, and the arrow that does not exist

```
CANONICAL ENGINEERING MODEL
        ↓
DETERMINISTIC VISUAL SCENE          (Phase 3, unchanged)
        ↓
CAMERA · MATERIAL · LIGHTING        (Phase 7)
        ↓
BASE RENDER                         ← the geometry authority
        ↓
CONTROL BUFFERS                     (deterministic, CPU, GPU-independent)
        ↓
OPTIONAL AI ENHANCEMENT             (adapter boundary; may be absent)
        ↓
PRESENTATION IMAGE
```

There is no return arrow. `reverse_write_allowed` is `false`, `writes_to_model` is `false`
on every object this layer produces, and `model_hash_inputs` is `["model"]` and nothing
else. An AI image can never become model truth.

The deterministic path is complete on its own. With no provider, no network and no API
key, the workspace still produces plans, sections, elevations, cameras, materials,
lighting and control buffers. AI enhancement is strictly downstream and strictly
optional.

---

## 1. Files

| File | Role |
| --- | --- |
| `acs_render.json` | the canonical render specification — view types, material library, lighting, cameras, buffers, drift types, fidelity statuses, metadata, security allow-lists |
| `acs_render.py` | the Python implementation of the whole render layer |
| `tools/build_render_browser.py` | injects the byte-identical JavaScript mirror, the VISUALIZE panel DOM and its styles into `public/index.html`; idempotent |
| `tests/phase7/` | contract, targets, security, parity, benchmark, output generator |
| `tests/phase7/outputs/` | 47 real presentation files generated from the models |

Phase 3's `acs_visual.json` declared this boundary and said *"this phase rasterises none
of them"* about the control buffers. Phase 7 implements it. Phase 3 was not modified.

## 2. The render request

A `VisualRenderRequest` is typed, validated and pinned to a `model_hash` and a
`revision_id` before anything is drawn. An unknown view type, quality, theme, lighting
preset or resolution is refused rather than defaulted, and a reference identifier that is
not a plausible identifier is refused outright. The request declares
`is_presentation_state: true` and `writes_to_model: false`. The same inputs always produce
the same `request_id`.

Eleven output types are supported: EXTERIOR, INTERIOR, DOLLHOUSE, CUTAWAY, ISOMETRIC, TOP,
FLOOR_PLAN, SECTION, ELEVATION, PANORAMA and VR_PREVIEW.

## 3. Materials

Twenty-one materials across sixteen visual classes, each carrying base colour, roughness,
metalness, opacity, world-scale texture size, source, licence and `visual_only: true`.
Every bundled material is procedural, so nothing copyrighted ships and no render depends
on a remote host. No material carries a fire rating, a structural grade or a U-value, and
the specification says so in the material note that the tests assert.

Six themes each cover nine slots. A finish absent from the model renders as a neutral
default while the semantic model still reports it as unknown; the render metadata records
`visual_default_applied`. A user may override a material visually — and if the intent is
to change the actual project specification, the override is **refused here** and routed to
the Phase 5 authoring path. The two operations are never merged.

## 4. Lighting, environment, shadows and quality

Eight lighting presets (DAY, OVERCAST, GOLDEN_HOUR, SUNSET, NIGHT, INTERIOR_DAY,
INTERIOR_NIGHT, STUDIO). A sun direction taken from a preset is labelled `VISUAL_PRESET`
and `is_solar_analysis: false`; only a declared project orientation produces
`PROJECT_ORIENTATION`. No solar analysis is claimed anywhere.

An environment map is used only when a local licensed asset exists; otherwise the
procedural sky is used and the fallback is reported. Four shadow modes, SSAO by quality
profile, and five post-processing effects that change tone and colour only. On a
constrained device the quality profile degrades cost — never semantic geometry.

## 5. Cameras

Ten presets, each solved from the real scene bounds, never from an invented number. Field
of view is clamped to an architecturally sane range so a default render never shows
extreme distortion. An interior camera is placed inside the real space boundary with a
declared clearance from the wall, at eye level above that space's floor — and a space too
small for a safe camera is **refused** rather than guessed.

## 6. Dollhouse, exploded and cutaway

Five visual transforms: ROOF_HIDE, WALL_CLIP, LEVEL_ISOLATION, CLIP_PLANE, LEVEL_EXPLODE.
Each returns hidden object identifiers, a clip plane or display offsets. Every one
declares `duplicates_geometry: false`, `changes_level_elevation: false`, `reversible:
true` and `writes_to_model: false`. A dollhouse hides the roof; it does not build a second
model.

## 7. Plans, sections and elevations

These are the outputs this environment can produce end to end, and it does: 47 files in
`tests/phase7/outputs/` for the villa, hotel, clinic and warehouse.

A plan derives its walls and openings from the compiled architecture — every wall and
opening identifier in the drawing exists in `acs_arch` output, which is asserted. Space
names and areas come from the model, dimensions declare `source: MODEL`, and a north
indicator is drawn **only** when the project declares an orientation. The drawing sets
`is_construction_drawing: false` and the SVG says so on its face.

An elevation shows only openings that exist in the model; `invented_features` is `0` and
visual-only objects are excluded. A section separates cut elements from those beyond and
reports the level elevations it found. All three serialise to deterministic SVG.

## 8. Control buffers

Six buffers — DEPTH, EDGE, NORMAL, OBJECT_ID, ROOM_ID, SEMANTIC_MASK — rasterised on the
CPU from the compiled scene at one declared camera and resolution.

**Why CPU and not GPU.** These buffers must be identical in Python and JavaScript to be
comparable at all, and a GPU result cannot be parity-tested. `rasterised_on:
CPU_DETERMINISTIC`, `gpu_dependent: false`. The byte streams are identical across both
implementations, including the PNG encodings — which use stored (uncompressed) deflate
blocks precisely because compression levels differ between libraries.

Alignment is strict: any difference in width, height, camera, projection or model hash
fails `buffers_aligned`, and an enhancement request carrying misaligned buffers is
refused.

One rasterisation rule is worth naming: an opening is a hole cut in its host wall, so
within a declared wall-thickness epsilon the opening wins the depth test in both
directions. Without it every door and window disappears behind its host in every exterior
view, and opening drift becomes undetectable.

## 9. The AI boundary

Every enhancement request carries the control buffers. `text_only` is `false` whenever
geometry control data exists — a text-only prompt is never sent when the buffers are
available. The prompt contract states literally what must be preserved (massing, floor
count, wall positions, openings, doors, windows, stairs, roof outline, camera viewpoint,
footprint) and what may be enhanced (materials, surface detail, lighting, furniture
styling, landscape, atmosphere). No preserved feature appears in the enhanceable list.

The provider is an adapter: `accepts` an image, buffers, a prompt and references;
`returns` a presentation image. No provider name appears anywhere in the specification.
The key lives in the server environment only and never in client source, render metadata
or a log — asserted, including against a provider response that tries to leak one back.

If the provider is unavailable, the deterministic render remains the output, an issue is
raised, and nothing is blank.

Every AI output is typed `AI_ENHANCED_VISUALIZATION` with `engineering_authority: false`,
pinned to the model hash, revision, base render and camera.

## 10. Geometry drift detection

Features are extracted from the control buffers: building silhouette (excluding
visual-only objects, so decoration cannot move the footprint), footprint area, roof line
per column, storey bands, connected-component openings with centres, and wall coverage.

Eight drift types are classified — WINDOW_ADDED, WINDOW_REMOVED, DOOR_MOVED,
FLOOR_COUNT_DRIFT, WALL_LAYOUT_DRIFT, FOOTPRINT_DRIFT, ROOF_GEOMETRY_DRIFT and
SEMANTIC_OBJECT_MISSING — against declared thresholds. One major drift rejects; a minor
drift warns. A rejected image sets `presented_as_model_faithful: false` and the declared
`VISUAL_GEOMETRY_DRIFT` code, and may be regenerated. **Material and detail differences
are expected and are not drift** — a plaster-to-stone change passes with every geometric
feature identical.

No drift result edits the model.

## 11. Traceability and staleness

Every render descriptor records all twenty declared metadata fields, certifies nothing,
and claims a resolution as rendered only when one was actually produced. When the model
moves on, the render is marked `STALE_SOURCE_MODEL`; it is never deleted automatically and
never silently re-pointed. The gallery counts stale cards. Persistence is local session;
`gallery_cloud` is `false`.

## 12. Security

Untrusted input is refused by **allow-list**, not by guessing the attack. A reference
identifier must match a declared safe-identifier pattern; a reference source must be on an
allowed scheme (an `image/*` base64 data URL qualifies, `image/svg+xml` does not); a
visual intent value must match a short Arabic-or-English style pattern. Ten real payloads
— script tags, event handlers, `javascript:`, `vbscript:`, `data:text/html`, an XXE
doctype, template injection and JavaScript injection — are all refused, and none executes
when rendered in real Chromium.

Generated SVG opens no element from an untrusted value: the test counts tags rather than
searching for strings. Size, pixel and MIME limits are declared and finite. The generated
browser block contains no `eval`, no `new Function`, no `document.write` and no network
call.

**A gap found and closed.** Phase 7's adversarial tests showed that Phase 6's reference
guard, which used a deny-list, accepted an XXE doctype and two injection payloads. Phase 6
now uses the same scheme allow-list. That is the point of running the adversarial suite
against the earlier layer.

## 13. Workspace integration

A VISUALIZE panel inside the Phase 6 workspace: View, Camera, Style, Materials, Lighting,
Landscape, Decor, Quality, AI enhancement — and **no engineering mutation control**, which
is asserted against a declared forbidden list. Preview, Render, Compare and Export.
Renders land in a gallery whose cards show view type, revision, style, base-or-AI,
fidelity and staleness. A base/AI toggle exists so the deterministic geometry can always
be inspected beside any AI result.

Verified in real Chromium: the panel opens, renders a plan to real SVG, shows it in the
viewer, and survives an Arabic ↔ English switch with its whole configuration intact.

## 14. Verification classes

This phase distinguishes four, and does not blur them:

| Class | Meaning | Applied to |
| --- | --- | --- |
| CODE_VERIFIED | proven by an executed test | the whole render layer, drawings, buffers, drift, AI boundary, security |
| RUNTIME_VERIFIED | real pixels from a real engine | the SVG drawings rendered in Chromium; the panel in Chromium |
| AI_VERIFIED | a real provider returned an image | **nothing** — no provider is reachable here |
| NOT_VERIFIED | requires an environment this sandbox lacks | WebGL base render, shadows, SSAO, post-processing, VR |

## 15. Known limitations

- **No WebGL base render was produced.** `public/vendor/` is empty because the sandbox has
  no network, so Three.js never loads. Chromium here *does* report WebGL 2.0 via
  SwiftShader, so the limitation is the missing library, not the browser. Every raster
  3D claim is `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`.
- **No AI image was generated.** No provider is reachable. The adapter, the prompt
  contract, the request assembly, the failure path and the drift detector are all
  exercised; the network call is not.
- **Drift detection is validated on synthetic candidates.** Reference features come from
  real geometry; candidates are perturbations of those same buffers run through the same
  extractor. Extracting features from a photographic image returned by a provider is a
  separate step that this environment cannot exercise.
- **Panorama and VR_PREVIEW are declared and requestable but have no deterministic
  raster output here**, for the same reason as the other 3D views.
- **A section is taken on x or z only.** An arbitrary plane is declared future work.

## 16. Hard stop

Phase 7 ends here. BIM interoperability, cloud collaboration, automatic structural or MEP
design and autonomous design are **not** started and require explicit approval.
