# PHASE 7 — PHOTOREALISTIC VISUALIZATION & AI PRESENTATION ENGINE
## FINAL REPORT

**Production visual output · Geometry-preserving · Model-conditioned AI
No engineering mutation · No AI redesign**

Executed offline in the build sandbox. Chromium **is** available and reports WebGL 2.0
through SwiftShader; Three.js is **not** vendored because there is no network, so no GPU
base render was produced. Every figure below came from a command that ran.

---

### 1. Rendering architecture

```
CANONICAL ENGINEERING MODEL → DETERMINISTIC VISUAL SCENE → CAMERA·MATERIAL·LIGHTING
   → BASE RENDER → CONTROL BUFFERS → OPTIONAL AI ENHANCEMENT → PRESENTATION IMAGE
```

`reverse_write_allowed: false`, `writes_to_model: false` on every produced object, and
`model_hash_inputs: ["model"]`. There is no return arrow and no code path that could
create one. Phase 3 declared this boundary and said it rasterised no buffers; Phase 7
implements it without modifying Phase 3.

### 2. Files created or changed

`acs_render.json` (canonical spec, 137 keys), `acs_render.py`,
`tools/build_render_browser.py` (JS mirror + VISUALIZE panel DOM and styles),
`tests/phase7/` (7 suites, benchmark, output generator, parity triple, fixtures),
`tests/phase7/outputs/` (47 generated files), `tests/security/test_security.py` (+23
Phase 7 checks), `tests/phase3/lib/build_browser_page.js` and `run_browser.js` (harness
now carries the render panel and a larger page), `acs_workspace.json`/`.py` and
`tools/build_workspace_ui.py` (reference guard hardened — see §36),
`PHASE7-PHOTOREALISTIC.md`, `VERIFICATION-RUNBOOK.md` (new **B-RENDER** section).

### 3. RenderRequest schema

Typed, validated and pinned to `model_hash` + `revision_id` before anything is drawn. All
thirteen declared fields plus resolution and context flags. Unknown view type, quality,
theme, lighting or resolution is **refused, not defaulted**. Identical inputs produce an
identical `request_id`; a different theme produces a different one. `writes_to_model:
false`, `is_presentation_state: true`.

### 4. Base deterministic renderer

The deterministic path is complete without AI: cameras solve, materials assign, lighting
configures, drawings serialise and control buffers rasterise with no provider, no network
and no key. With no provider, `ai_enhance` returns `used_ai: false`,
`fallback: DETERMINISTIC_BASE_RENDER` and a real `PROVIDER_UNAVAILABLE` issue — never a
blank output. **The GPU base render itself is NOT VERIFIED here** (§40).

### 5. Material system

21 materials across 16 visual classes, each with base colour, roughness, metalness,
opacity, world-scale texture size, source, licence and `visual_only: true`. No material
carries a fire rating, structural grade or U-value — asserted. Six themes × nine slots,
all populated. Glass has transparency and low roughness with no engineering claim
attached.

### 6. Texture system

`uv_mode: WORLD_SCALE`, so a large wall does not stretch a texture, and UV mapping never
touches geometry. Four texture sources: local vendor, bundled, approved upload,
procedural. Every bundled material is procedural, so nothing copyrighted ships and no
render depends on an uncontrolled host — asserted.

### 7. Lighting

Eight presets. A preset sun is labelled `VISUAL_PRESET` with `is_solar_analysis: false`; a
declared project orientation switches the label to `PROJECT_ORIENTATION`.
`solar_analysis_claimed: false`. Night presets turn on interior fixtures rather than
faking daylight.

### 8. Environment

Procedural sky, environment map, flat background. An environment map is used only when a
local licensed asset exists; otherwise the procedural sky is used and `fell_back: true` is
reported. `remote_dependency: false` on every path.

### 9. Shadows and post-processing

Four shadow modes with rising map resolution and cascades; SSAO enabled by quality
profile; five post effects. Post processing changes tone and colour only — *"No effect
moves, scales or deforms geometry."* On a constrained device the profile degrades cost and
`removes_semantic_geometry` stays `false`.

### 10. Exterior rendering

Cameras solve from real scene bounds. Presentation site context (sky, ground, vegetation,
entourage) is opt-in per render and tagged visual-only; it never becomes site engineering
data.

### 11. Interior rendering

An automatic interior camera is placed inside the real space rectangle, at the declared
0.45 m clearance from the wall, at eye level above that space's floor elevation. A space
too small for a safe camera is **refused** with `SPACE_TOO_SMALL` rather than guessed. A
non-existent space is refused.

### 12. Dollhouse

`ROOF_HIDE` returns real object identifiers to hide. `duplicates_geometry: false`,
`reversible: true`, and the scene object list is byte-identical afterwards. Level
isolation and exploded levels are display offsets only, with
`changes_level_elevation: false`.

### 13. Cutaway

`CLIP_PLANE` on x, y or z with a declared offset and keep side; `WALL_CLIP` for the
dollhouse cut. Unknown axes refused. Reversible runtime operations only.

### 14. Floor plans

Derived from the compiled architecture. Every wall and opening identifier in the drawing
exists in the `acs_arch` output — asserted. Space names and areas from the model,
dimensions marked `source: MODEL`, stairs from real objects, furniture only when
requested. A north indicator appears **only** when orientation is declared.
`is_construction_drawing: false` and the SVG says so on its face. Four plan styles.

### 15. Sections

Real cuts through the compiled scene, separating cut elements from those beyond, reporting
the level elevations found. Both declared axes work; an unknown axis is refused. Every
shape is a real scene object.

### 16. Elevations

Four faces from the real envelope. `invented_features: 0`, visual-only objects excluded,
and the SVG states how many openings are modelled and that none were invented.

### 17. Cameras

Ten presets. Field of view clamped to 18–90° so a default render never distorts. The top
view is orthographic. Framing keeps the whole building in frame at a declared margin.
Every camera declares `is_presentation_state: true`.

### 18. Reference-image integration

Phase 6 references feed the prompt as context with four scopes. A reference **cannot**
override geometry: `wall_positions` is in `preserve` and absent from `may_enhance`.
Attaching a reference leaves the model hash unchanged, and the geometry the AI is
constrained by is byte-identical before and after.

### 19. Visual intent

Style, mood, material, lighting and landscape preferences flow into the prompt after
passing a declared allow-list pattern (§36).

### 20. AI provider boundary

`accepts: [base_image, control_buffers, prompt, reference_images]`,
`returns: [presentation_image, provider_model, generated_at]`. No provider name appears
anywhere in the specification — asserted against openai, stability, midjourney, replicate
and anthropic. Timeout and availability declared. A provider failure keeps the
deterministic render.

### 21. Control buffers

Six buffers rasterised **on the CPU** from the compiled scene at one camera and
resolution: `rasterised_on: CPU_DETERMINISTIC`, `gpu_dependent: false`. This is a design
decision, not a workaround — a GPU result cannot be parity-tested, and these buffers must
be identical in both implementations to be comparable at all. Alignment is strict on
width, height, camera, projection and model hash; misaligned buffers fail and an
enhancement request carrying them is refused.

### 22. AI prompt constraints

The contract names ten preserved features and six enhanceable ones, with **no overlap**.
The prompt text states the constraint literally. `text_only` is `false` whenever buffers
exist — a text-only prompt is never sent when geometry control data is available. A
request without buffers, without a base render, or with a base render and buffers from
different cameras is refused.

### 23. Geometry drift detector

Features from the control buffers: building silhouette excluding visual-only objects
(so decoration cannot move the footprint), footprint area, per-column roof line, storey
bands, connected-component openings with centres, and wall coverage. Compared against
declared thresholds.

### 24. Fidelity statuses

PASS, WARNING, REJECTED. One major drift rejects; a minor drift warns. A rejected image
sets `presented_as_model_faithful: false`, carries `VISUAL_GEOMETRY_DRIFT` and
`may_regenerate: true`. No drift result edits the model.

### 25. Visual variants

Six themes over one model hash. Two variants share the model hash and differ in
configuration; `creates_revision: false` on both.

### 26. Furniture and decoration separation

`separate_visual` splits semantic from visual-only objects with
`counts_are_separate: true`, `visual_enters_semantic_count: false` and
`visual_becomes_site_data: false`. Every visual-only object carries a
`VISUAL_ONLY_DECORATION`, `_LANDSCAPE` or `_ENTOURAGE` tag.

### 27. Landscape and entourage

Presentation context flags are opt-in per render and never derived from building type.
`industrial_equipment` is off by default for the villa, hotel, clinic **and** warehouse,
and turns on only when explicitly requested — asserted for all four.

### 28. Villa results

Front exterior, corner exterior, dollhouse, ground floor plan, first floor plan, living
room interior, majlis interior, night lighting, and an AI variant prepared with full
geometry control — **nine of nine produced**, all carrying the same model hash and
revision, with the model unchanged afterwards. The AI variant was prepared but not
produced, because no provider is reachable; that is reported, not claimed.

### 29. Hotel results

Exterior, lobby interior, guest-room camera, selected-floor dollhouse and floor plan. The
model genuinely repeats a floor template, and repeated floors keep identical wall geometry
— asserted.

### 30. Warehouse results

Exterior, interior, engineering overlay scene and presentation render. Every semantic
object is preserved through material assignment, lighting and buffer generation, and
semantic equipment is never tagged visual-only.

### 31. Clinic results

Exterior and floor plan. **No healthcare equipment is invented** — asserted against
scanner, x-ray, MRI, bed, monitor, ventilator and stretcher. The elevation invents no
façade feature.

### 32. Render gallery

Cards carry all eight declared fields including fidelity and staleness, count stale
renders, and declare `cloud: false` with local-session persistence.

### 33. Workspace integration

A VISUALIZE panel inside the Phase 6 workspace with View, Style, Lighting, Quality,
Materials and AI-enhancement sections, and **no engineering mutation control** — asserted
against a declared forbidden list. Verified in real Chromium: the panel opens, renders a
plan to real SVG, displays it in the viewer, and toggles base/AI.

### 34. Metadata and traceability

All twenty declared metadata fields recorded. Every render names its model hash, revision,
camera and view type, sets `certifies_nothing: true` and `engineering_authority: false`,
and claims a resolution as rendered **only** when one was actually produced.

### 35. Revision staleness

A fresh render is CURRENT. After the model moves on it is `STALE_SOURCE_MODEL`, still
naming its own revision, with `auto_deleted: false` and `auto_repointed: false`. Proven
end to end in Test C with a **real committed authoring revision**: a window was moved
through the Phase 5 path, the old render went stale, and a new render used the moved
window position.

### 36. Security

**163 checks in Node, 242 in real Chromium with zero page errors, 189 backend checks.**

Untrusted input is refused by **allow-list**, not by guessing the attack: a declared
safe-identifier pattern, an allowed-scheme list for reference sources (an `image/*` base64
data URL qualifies, `image/svg+xml` does not), and a short Arabic-or-English pattern for
visual intent. Ten real payloads — script tags, event handlers, `javascript:`,
`vbscript:`, `data:text/html`, an XXE doctype, template injection and JavaScript injection
— are all refused, and none executed when rendered in Chromium. Generated SVG opens no
element from an untrusted value (the test counts tags rather than searching strings). Size,
pixel and MIME limits are declared and finite. The generated block has no `eval`, no
`new Function`, no `document.write` and no network call. A provider response attempting to
leak an API key back does not carry it into the output.

**A gap in Phase 6 found and closed by this phase's adversarial tests.** Phase 6's
reference guard used a deny-list and therefore accepted an XXE doctype and two injection
payloads. Phase 6 now uses the same scheme allow-list, and its own suites still pass.

### 37. Performance

Measured on this machine; no FPS, GPU or shader claim anywhere.

| Case | Objects | Scene build | Buffers 96×64 | Buffers 320×200 | Features | Plan ×10 | AI prep ×10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| villa_glazed | 88 | 8 ms | 26 ms | 245 ms | 6 ms | 8 ms | 2 ms |
| hotel_glazed | 63 | 5 ms | 21 ms | 190 ms | 5 ms | 5 ms | 1 ms |
| warehouse_glazed | 39 | 3 ms | 15 ms | 135 ms | 4 ms | 3 ms | 1 ms |
| clinic_glazed | 48 | 4 ms | 18 ms | 158 ms | 4 ms | 4 ms | 1 ms |

Every benchmarked case left the model hash unchanged.

### 38. Mobile

The VISUALIZE panel takes the full viewport below 768 px, keeps 44 px touch targets, and
hides no control off-screen — it scrolls. Phase 6's responsive suite re-ran green at all
seven widths (**87 passed**).

### 39. VR compatibility

Presentation materials are ordinary PBR values on the existing scene; no separate VR
geometry is created and `VR_PREVIEW` is a view type over the same model. Phase 3's 1:1 VR
scale note is unchanged. **Runtime VR behaviour is NOT VERIFIED here.**

### 40. Runtime verification

| Item | Class |
| --- | --- |
| Render layer, drawings, buffers, drift, AI boundary, security | **CODE_VERIFIED** |
| SVG plans, sections, elevations rendered as real pixels in Chromium | **RUNTIME_VERIFIED** |
| The VISUALIZE panel operating in real Chromium | **RUNTIME_VERIFIED** |
| WebGL base render, materials, shadows, SSAO, post-processing | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** |
| Panorama and VR_PREVIEW raster output | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** |
| Frames per second, GPU behaviour, shader compilation | **NOT MEASURED — no claim made** |

Chromium here reports WebGL 2.0 via SwiftShader; the blocker is the missing Three.js
vendor bundle, not the browser. 47 real presentation files were produced and are listed in
`tests/phase7/outputs/MANIFEST.json`, each naming its revision and model hash.

### 41. AI verification

**AI_VERIFIED: nothing.** No provider is reachable from this sandbox. The adapter, prompt
contract, request assembly, alignment checks, failure path and drift detector are all
executed; the network call is not. No AI image was generated, and none is claimed.

### 42. Phase 1–6 regression

`sh tests/phase7/run_all.sh --browser` → **4,954 assertions passed, 0 failed, exit 0.**

| Phase | Result |
| --- | --- |
| Phase 3 | 357 checks; visual parity 116/116; adversarial agreement 16/16 |
| Phase 4 | 1,227 checks across 11 suites |
| Phase 5 | 1,367 checks; authoring parity 35 |
| Phase 6 | 113 + 153 + 167 + 47; responsive 87; walkthrough 16 PASS / 1 NOT_VERIFIED |
| Security | 189 checks (166 prior + 23 new) |
| **Phase 7** | **272 + 93 + 163 + 49 = 577, plus 242 in Chromium** |

Render parity is **18/18 byte-identical**: cameras 10/10, materials 10/10, drawings 10/10,
control buffers 10/10, geometry features 10/10, SVG output 10/10, **PNG byte streams
10/10**, model hashes 10/10, drift cases 12/12, AI boundary 8/8.

### 43. Known limitations

No WebGL base render was produced (no vendored Three.js). No AI image was generated (no
provider). Drift detection is validated on synthetic candidates derived from real geometry
and run through the same extractor — extracting features from a photographic provider
image is a declared, unimplemented boundary. Panorama and VR_PREVIEW have no deterministic
raster output here. Sections are taken on x or z only; an arbitrary plane is future work.
Two defects of my own were found and fixed during the phase: three materials had a
positional-argument shift that made `texture_scale_m` a string and the licence lowercase,
and an explicit zero buffer dimension was silently replaced by the default in both
implementations (`0 || default`).

---

## EXPLICIT CONFIRMATIONS

- **NO ENGINEERING MODEL MUTATION FROM VISUALIZATION** — six models × the entire pipeline,
  model hash, revision and canonical JSON byte-identical afterwards.
- **NO AI IMAGE CAN BECOME ENGINEERING MODEL TRUTH** — `reverse_write_allowed: false`; an
  AI response carrying a model, structural, MEP, FLS or coordination payload changes
  nothing and those keys never appear in the output.
- **NO AI AUTO-EDIT** — every AI output is `engineering_authority: false`,
  `writes_to_model: false`.
- **NO WALL / DOOR / WINDOW / FLOOR / STAIR GEOMETRY CHANGE FROM RENDERING** — all seven
  drift types classified and rejected; the model is untouched in every case.
- **VISUAL MATERIAL ≠ ENGINEERING MATERIAL** — no material carries a fire rating,
  structural grade or thermal value; `semantic_finish_unchanged: true` on every
  assignment.
- **VISUAL FURNITURE ≠ SEMANTIC OBJECT** — separate counts,
  `visual_enters_semantic_count: false`.
- **VISUAL LANDSCAPE ≠ SITE ENGINEERING DATA** — `visual_becomes_site_data: false`.
- **ALL RENDERS ARE PINNED TO MODEL HASH + REVISION** — and marked stale, never deleted or
  re-pointed, when the model moves on.
- **BASE DETERMINISTIC RENDER ALWAYS EXISTS AS AUTHORITY** — the whole path runs with no
  provider, no network and no key.
- **AI ENHANCEMENT IS OPTIONAL AND DOWNSTREAM** — and absent here, reported as absent.
- **NO FAKE PHOTOREALISTIC PASS** — `photorealistic_engine_shipped: false`, AI_VERIFIED is
  empty, and stub output is explicitly not reported as a rendering pass.
- **NO PHASE 1–6 REGRESSION** — every earlier suite re-executed and passed.
- No code system (SBC, IBC, NFPA, ADA, ACI, ASCE, AISC, Eurocode, NEC, ASHRAE) appears in
  the render specification. No secret was exposed or printed. The `claude-sonnet-5` model
  id is unchanged. CSP, rate limits and secret handling are unchanged.
- No PASS in this report is fabricated.

## HARD STOP

Stopping here as instructed. **BIM interoperability, cloud collaboration, automatic
structural or MEP design, and autonomous design are NOT started and will not be started
without explicit approval.**
