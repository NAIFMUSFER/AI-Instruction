# Phase 9.2 — Architectural Visual Fidelity, Façade Detailing & Presentation Context

**AI Construction Studio** — general-purpose AI construction platform.
Phase 9.2 extends the Phase 9.1 read-only presentation architecture. It adds no second
PBR engine, no second camera/lighting/quality registry, and writes nothing into the
canonical engineering model.

```
CANONICAL MODEL → EXISTING VISUAL COMPILER → EXISTING PBR LAYER
  → ARCHITECTURAL PRESENTATION DETAIL LAYER
  → LIGHTING / ENVIRONMENT / POST PROCESS → VIEWPORT / IMAGE
```

There is never a reverse arrow (`reverse_arrow_exists: false`, asserted).

## 1. Authority boundary (§1)

The canonical model is the only engineering source of truth. Every presentation-only
object carries `visual_only: true`, `source_element_id`, `provenance`, `confidence`,
`reason` — and `presentation_context: true` where applicable. Nothing from this layer
enters architectural geometry, structure, MEP, FLS, BIM, documentation, quantities,
navigation, compliance or authoring history — proven by the §43 immutability battery
(byte-identical canonical model across five building types after the full visual
workload).

## 2. Presentation-detail classes (§4)

`CANONICAL_GEOMETRY` · `DERIVED_PRESENTATION_DETAIL` (e.g. a window frame derived from a
represented opening) · `REQUESTED_PRESENTATION_DETAIL` (e.g. a beige-stone façade
appearance) · `DEFAULT_PRESENTATION_CONTEXT` (e.g. a neutral ground plane) ·
`UNRESOLVED`. Promotion between classes is forbidden and asserted. Objects carry the
parallel authority classes of 14B: `CANONICAL_OBJECT`, `USER_REQUESTED_OBJECT`,
`PRESENTATION_CONTEXT_OBJECT`, `UNRESOLVED_OBJECT` — ambiguity always resolves to
UNRESOLVED, never to invention.

## 3. Façade system (§5, §6, §23–§26)

Zoning assigns presentation materials (beige stone, painted/architectural plaster,
exposed concrete, gray panels, wood accent, metal cladding, glass zones) **only to
represented exterior surfaces**; a requested accent with no safely derivable band
returns `AD_VISUAL_DETAIL_UNRESOLVED` instead of a fabricated zone. No wall is invented
and no thickness changes. Visual depth elements (cladding skin, reveals, trims, sills,
lintel caps, parapet coping) are bounded by `presentation_offset_max_m: 0.06`, attached
to a canonical source element, and removable without any model change. Deterministic
material variation (roughness/albedo/normal jitter within declared maxima) is seeded
from `model_hash + element_id + material_id` — the same model always renders the same
variation; `Math.random` is absent from the layer (asserted).

## 4. Windows, doors, balconies, roofline (§7–§10)

Every represented window pane derives a presentation assembly: aluminum frame
(dark/gray/light, thickness proportional to the opening, clamped 0.03–0.09 m), the 9.1
physical glass, and a sill — with `opening_size_changed / opening_position_changed /
window_count_changed` all false. Doors map from represented evidence to visual classes
(wood, painted metal, alu-glass, service, entrance, dock) with a generic fallback; fire
and security ratings are **never inferred**. Represented balconies are enhanced;
requested-but-unrepresented balconies surface as `REQUESTED_BUT_NOT_REPRESENTED` with a
bilingual UI note and are never created. Roofline enhancement touches represented
elements only; no rooftop equipment or height is invented.

## 5. LED / architectural lighting (§11)

Six visual-only types (façade strip, balcony strip, entrance wash, cove, wall washer,
bollard). A light attaches only to a represented host; it never creates an electrical
circuit, load, panel assignment, cable route, or MEP schedule entry, and no MEP fixture
is ever reused as a presentation light — all asserted per light.

## 6. Interior, staging, kitchens, bathrooms (§12–§16)

Default staging is `STAGING_REQUESTED_ONLY`: canonical and user-requested objects are
improved; nothing is silently added. `STAGING_PRESENTATION_DEFAULT` must be explicitly
selected; its additions are `PRESENTATION_CONTEXT_OBJECT`s excluded from BIM,
quantities, engineering exports and documentation schedules. The furniture library
reads as its categories (bed = base+mattress+headboard, sofa = seat+back+arms,
wardrobe = carcass+doors, rack = uprights+beams+decks). An ambiguous kitchen phrase
(«L أو U حسب الدور») returns `AD_KITCHEN_LAYOUT_UNRESOLVED` — never an invented layout.
Bathroom fixtures are never placed when absent and plumbing is never inferred.

## 7. The general presentation object library (14A–14J)

Six categories, 60+ kinds: vehicles (car, SUV, pickup, van, truck, delivery truck, bus,
emergency vehicle — explicit request only), material handling (counterbalance forklift,
reach truck, pallet jack, order picker, stacker, …), logistics (pallet, carton, crate,
drum, IBC, rack, bollard, wheel stop, cone, …), landscape (tree, palm, shrub, hedge,
planter with LOW/STANDARD/HIGH LODs), site (parking bay, markings, fence, gate, barrier
arm, light pole, …), and construction proxies (requested/represented only). Vehicles
read as vehicles (body, cabin, four wheels, glazing, light surfaces) with no make,
model, plate, engine or VIN invented; forklifts read as forklifts (chassis, operator
compartment, overhead guard, mast, forks, counterweight) with no capacity, mast rating,
battery, fuel type or manufacturer inferred — unknown variants fall to
`GENERIC_FORKLIFT_PRESENTATION`. 27 presentation material classes (automotive paint,
vehicle glass, tire rubber, chrome, forklift body/mast, road asphalt, parking paint,
curb, paving, grass, foliage, bark, gravel, bollard, fence …) — none is engineering
truth. Scale priority: canonical → user → PRESENTATION_DEFAULT (reported as fallback).
Placement priority: canonical → user → deterministic in a requested zone → UNRESOLVED;
nothing is auto-placed just because a space exists. «ضع 10 سيارات في المواقف» fills
exactly the represented valid bays and reports the shortfall. Repeated context objects
(cars, trees, bollards, cartons …) are marked for `InstancedMesh` with traceable
per-instance metadata; canonical selectable objects are never merged.

## 8. Context, parking, landscape, entrance, cores, FLS (§17–§22)

Site presentation distinguishes CANONICAL_SITE / REQUESTED_SITE_PRESENTATION /
DEFAULT_CONTEXT; no site boundary or road is invented. Represented parking renders with
asphalt/paving and painted markings; a parking request with no bays returns
`PARKING_REQUESTED_NOT_GEOMETRICALLY_RESOLVED` with no invented count. Landscape
defaults OFF and never enters the engineering model — no fake species, tree counts or
irrigation. Entrance emphasis and vertical-core presentation touch represented geometry
only (canopy only if represented; elevator capacity remains request provenance).
FLS devices get better lightweight presentation geometry but missing devices are never
added and no coverage or compliance is implied.

## 9. Environments, cameras, auto mode (§27–§32)

Four glass-reflection environments (NEUTRAL_STUDIO, CLEAR_SKY, OVERCAST_SKY,
SUNSET_SKY) run through the existing local PMREM path — no runtime CDN, no remote HDRI.
Eleven new camera presets (hero front/corner, street level, aerial, living, kitchen,
bedroom, corridor, warehouse aisle/overview, dollhouse hero) resolve through the same
bounds-framed, FOV-clamped (20–75°), deterministic resolver as Phase 9.1 — one registry,
no fisheye, hero favouring the three-quarter view. `AUTO_PRESENTATION` picks
presentation settings only (camera, lighting, quality ≤ HIGH — never ULTRA,
environment, materials, detail) per building type; it can never change engineering
geometry. Two-point perspective is **NOT IMPLEMENTED** — documented honestly per §31.

## 10. Request interpretation and diagnostics (§33–§35)

The interpreter classifies each extracted intent: «حجر بيج» → SAFE_VISUAL_OVERRIDE;
«بلكونات أكبر» / «دور إضافي» → REQUIRES_ENGINEERING_CHANGE; «مواقف» → AMBIGUOUS until
geometry decides; unknown → UNSUPPORTED. Descriptive language never grants engineering
permission (asserted). The visual fidelity diagnostic accounts for every request —
requested / represented / unresolved / engineering-change-required /
presentation-defaults, plus the object ledger of 14J — with `silently_dropped` provably
empty. `VISUAL_REQUEST_COVERAGE` counts only user-requested visual features and carries
`is_engineering_completeness: false`, `has_compliance_meaning: false`.

## 11. UI, comparison, capture (§36–§38)

The architectural panel (Arabic/English) adds exactly: Detail (Off/Standard/High),
Façade (Engineering/Requested appearance/Realistic), Context
(None/Neutral/Site/Landscape), Staging (Off/Requested only/Presentation), Camera
(Auto/Hero/Street/Aerial/Interior), a visual-diagnostic toggle, and the three-way
in-app comparison ENGINEERING / PBR / ARCHITECTURAL over the same model and geometry.
Capture metadata extends the 9.1 record with presentation_layer_version, revision,
architectural_detail_level, context_mode, staging_mode and visual_request_coverage —
and remains non-engineering evidence.

## 12. Performance, mobile, security (§39–§42)

Shared owned materials, InstancedMesh for repeated context, LOD for landscape, no
ultra-high mesh density, and no merging of canonical selectable meshes. On constrained
devices DETAIL_HIGH degrades to DETAIL_STANDARD (typed `AD_MOBILE_FALLBACK_APPLIED`);
canonical objects are never removed and a blank viewport is never allowed. Security:
no arbitrary texture URLs, no user filesystem paths, no URL-based GLTF injection, no
executable assets, no runtime CDN (S-R1…S-R17 in the security suite; section 11d in
deploy verification; layer-extraction scheme scan in Chromium).

## 13. Limitations

Raster output (façade stone as pixels, frame meshes, LED glow) is
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** in this sandbox (no vendored
Three.js). `tests/phase9_2/capture_reference_92.js` produces the §48 before/after pairs
on a networked machine and refuses honestly (exit 2) otherwise. Basic real-time PBR +
parametric presentation detail is what is shipped and claimed — no photorealism, no
path/ray tracing, no GI, no BIM-grade façade detailing, no code compliance, no parking
engineering, no landscape or lighting design (§45, all flags asserted false).
