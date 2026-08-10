# Phase 9.1 — Professional Visual Quality & Real-Time PBR Presentation Layer

**AI Construction Studio** — general-purpose AI construction platform.
This phase upgrades the **existing** Three.js presentation renderer. It adds no second
engine, no second model, and writes nothing into the canonical engineering model.

```
CANONICAL ENGINEERING MODEL  →  READ-ONLY PRESENTATION COMPILER  →  REAL-TIME PBR SCENE
        →  OPTIONAL POST-PROCESSING  →  SCREEN / IMAGE OUTPUT
```

The arrow never reverses (`reverse_arrow_exists: false`, asserted). A presentation
configuration is hashed **separately** (`presentation_config_hash`, config bytes only);
the model hash inputs remain `["model"]` and are proven byte-identical around every
visual operation.

---

## 1. What already existed (inspected first, §1)

The shipped renderer already had: `ACESFilmicToneMapping`, `SRGBColorSpace`,
`PCFSoftShadowMap`, `PMREMGenerator` + `RoomEnvironment`, a `Sky` dome with a sun
`DirectionalLight` (2048 shadow map), a `HemisphereLight`, a `MeshStandardMaterial`
factory `getMat(name, tint)` with seeded procedural `CanvasTexture`s (plaster, concrete,
tile, wood, marble, asphalt, metal, fabric) and world-scale UVs via `scaleBoxUV`.
Phase 9.1 **extends** these objects — it does not duplicate them.

## 2. New canonical pieces

| File | Role |
| --- | --- |
| `acs_pbr.json` | 71-key canonical specification — the only source of truth |
| `acs_pbr.py` | deterministic presentation compiler (backend twin) |
| `tools/build_pbr_browser.py` | injects the byte-parity JavaScript mirror, panel DOM/CSS, module-scope bridge and render-loop dispatcher into `public/index.html` (idempotent, marker-fenced) |
| `tools/_pbr_bridge_block.js` | the only code that touches THREE — `window.ACS.pbrApply / pbrCameraPreset / pbrCapture / pbrRestore / pbrBounds / pbrCaps` |

Injected weight: JS block ≈ 41 KB, bridge ≈ 12.6 KB, DOM ≈ 0.6 KB, CSS ≈ 1.7 KB.

## 3. Material system (§3–§5)

Exactly **20 PBR materials**: plaster, painted_wall, concrete_exposed, concrete_polished,
ceramic_tile, stone, wood, steel_structural, steel_painted, aluminum, glass_clear,
glass_tinted, roof_membrane, asphalt, soil, fabric, plastic, rack_steel, carton,
safety_paint. Each declares baseColor, roughness, metalness, opacity, transmission, ior,
thickness, emissive, emissiveIntensity, normalScale, textureScale — with per-field
provenance `ENGINEERING_VALUE | USER_VISUAL_OVERRIDE | PRESENTATION_DEFAULT`.
A visual material **never** carries fire rating, structural grade or U-value, and
`ENGINEERING_VALUE` can never originate in this layer.

Glass uses `MeshPhysicalMaterial` (transmission 0.85, IOR 1.52, thickness 0.01 m).
Unmapped engineering materials keep their engineering appearance
(`unmapped_material_policy: KEEP_ENGINEERING_APPEARANCE`).

## 4. Textures (§4, §22)

Local-only: `allowed_asset_root: assets/materials/`, safe-pattern validated IDs,
`allowed_schemes: []`, `remote_texture_allowed: false`. The shipped
`local_texture_sets` is **empty**, so the runtime performs **zero texture fetches** and
falls back to the deterministic procedural PBR set — no CDN, no broken-texture icon.
Hostile paths (`https://…`, `//host`, `../`, `javascript:`, `data:` …) are refused with
typed issues; verified in Python, in parity, and in Chromium.

## 5. Lighting, environment, shadows (§6–§8)

Eight presets — STUDIO_DAY, CLEAR_NOON, GOLDEN_HOUR, OVERCAST, INTERIOR_DAY,
INTERIOR_NIGHT, WAREHOUSE, PRESENTATION_SOFT — all `visual_only`, and **no MEP fixture
is ever reused as a presentation light** (`mep_fixture_reused: false`, asserted).
Environment modes NEUTRAL / SKY / STUDIO run through the existing local PMREM path —
no remote HDRI exists anywhere. Shadow tiers LOW/MEDIUM/HIGH/ULTRA (1024→8192 maps)
frame the shadow camera from **live model bounds** × 1.15 margin — no hardcoded
building size (asserted with scaled fixtures).

## 6. Quality, degradation, cameras (§13, §17, §18)

Profiles PERFORMANCE / BALANCED / HIGH / ULTRA with declared minimum capabilities and
the fallback chain ULTRA→HIGH→BALANCED→PERFORMANCE. Every fallback step is reported as
a typed `PQ_FALLBACK_APPLIED` issue. **ULTRA is never auto-selected**
(`auto_max_profile: HIGH`, `ultra_auto_selected` always false).
`blank_viewport_allowed: false` — with no 3D runtime at all, apply returns a typed
`PQ_THREE_UNAVAILABLE` refusal and the page stays alive (proven in Chromium).

Eight deterministic camera presets (EXTERIOR_HERO, EXTERIOR_CORNER, EYE_LEVEL, AERIAL,
INTERIOR_WIDE, INTERIOR_EYE_LEVEL, WAREHOUSE_OVERVIEW, DOLLHOUSE) framed spherically
from model bounds; FOV clamped 20–75°; eye-level targets sit at 1.6 m above the real
minimum Y.

## 7. Post-processing and color (§9–§12)

Optional `EffectComposer` chain (SSAO, FXAA, subtle bloom-free output pass) loaded via
same-origin `three/addons/…` dynamic imports with a catch → `POST_UNAVAILABLE` clean
fallback; the render loop keeps `renderer.render(scene, camera)` as the else-branch.
ACES filmic + sRGB output, exposure clamped 0.5–1.8.

## 8. Ground context (§14)

`PQ_CONTEXT` group (ground plane) is added to the **scene**, never the building group,
and is excluded from BIM, documentation, quantities, engineering GLB and the model hash.
Roads/parking/landscaping/neighbor massing are declared off.

## 9. Settings panel and capture (§19–§20)

Arabic/English panel: Quality, Lighting, Materials (Engineering ↔ Realistic),
Environment, Shadows, AO, Exposure — and nothing else (forbidden raw developer controls
asserted absent). Screenshot capture is typed `PRESENTATION_OUTPUT` with camera preset,
quality profile, model hash and `is_engineering_evidence: false` — it can never be
promoted to engineering evidence.

## 10. Immutability (§21) and security (§22)

For four models × four profiles × four lighting presets plus every camera preset and
captures, the canonical model bytes are re-canonicalized and compared **identical**;
hash and revision unchanged; warehouse arch/struct/MEP/FLS counts untouched. Repeated in
Chromium through the real panel UI. Security suite S-Q1…S-Q17 covers no-exec of the
generated block, separate hashes, no promotion path, no CDN string in the quality layer,
hostile texture paths, prototype-pollution keys, panel forbidden controls and context
exclusions.

## 11. Build and deploy (§23)

`tools/netlify-build.sh` already vendors the full `examples/jsm` tree for pinned
`three@0.160.0`; Phase 9.1 adds **verification entries** for the 8 postprocessing/shader
modules actually imported. Three.js is **not** upgraded. Deploy verification gained
section 11c (bridge sentinels, dispatcher + fallback, same-origin imports, module
verification in the build script, texture policy) — 265 checks total.

## 12. What this phase does NOT claim (§26, §30)

No photorealism claim (`photorealism_claimed: false`), no path tracing, no offline
render, no FPS numbers — this sandbox has no GPU/WebGL+Three runtime, so raster output
is **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. `tests/phase9_1/capture_reference.js`
produces the 8 deterministic before/after pairs on a networked machine and refuses
honestly (exit 2) where the environment is missing.
