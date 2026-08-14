/* ============================================================
   public/app/render/scene.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { _mnid, _snum, compileArchitecture, compileFls, compileMep, compileStructure, flsElementById, flsRenderItems, mepElementById, mepRenderItems, structElementById, structRenderItems } from '../core/disciplines.js';
import { _scmp, modelHash, sha256Hex } from '../core/standards.js';
import { FLOOR_NAMES, RoomEnvironment, Sky, THREE, _pyRound, getMat } from '../core/viewer.js';
import { lastBuilding, model, setSun } from '../ui/workspace-ui-wiring.js';



const ACS_VISUAL_SPEC = {
 "schema": "acs.visual/1",
 "compiler_version": "acs-visual-compiler/1.0.0",
 "note": "VISUAL RENDERING AND PRESENTATION — GEOMETRY-PRESERVING VISUALISATION ONLY. This layer reads the compiled architectural, structural, MEP, fire/life-safety and coordination models and produces a derived visual scene: objects, materials, lights, cameras, environment and presentation state. It never moves a wall, a door, a window, a stair, a structural member, an MEP route or a fire device; it never adds or removes a room, changes the floor count, or alters the building footprint. Appearance is not engineering truth.",
 "derivation_note": "the visual scene is DERIVED. It is never written back into any discipline model, and compiling it leaves the architectural, structural, MEP, fire/life-safety and coordination models byte-identical.",
 "authority_note": "a visual material, a decoration object, an entourage figure, a landscape placeholder, a ground plane and a sky are APPEARANCE. None of them is a structural material, a fire rating, a thermal property, an occupant, an engineering object, a coverage input or a code input, and none of them is ever counted as one.",
 "visual_modes": [
  "ENGINEERING",
  "ARCHITECTURAL",
  "PRESENTATION",
  "DOLLHOUSE",
  "CUTAWAY",
  "FLOOR_PLAN_2D",
  "SECTION",
  "ELEVATION",
  "VR"
 ],
 "mode_note": "every mode is a different presentation of the SAME compiled model. A mode changes what is shown, how it is shaded and where the camera stands. No mode regenerates, simplifies or re-authors geometry, and switching modes can never change what exists in the building.",
 "mode_intent": {
  "ENGINEERING": "technical clarity over realism; discipline layers and the coordination overlay are available and nothing technical is hidden",
  "ARCHITECTURAL": "architectural finishes, glazing, ceilings and roofs; still literal geometry",
  "PRESENTATION": "realistic lighting, shadows, environment and composed cameras",
  "DOLLHOUSE": "roof hidden and upper enclosure clipped so interiors read from above",
  "CUTAWAY": "reversible clipping planes through the same geometry",
  "FLOOR_PLAN_2D": "orthographic plan derived from architectural geometry",
  "SECTION": "orthographic cut on a stated plane",
  "ELEVATION": "orthographic facade projection of the real envelope",
  "VR": "presentation shading at true physical scale for WebXR"
 },
 "engineering_modes": [
  "ENGINEERING"
 ],
 "presentation_modes": [
  "ARCHITECTURAL",
  "PRESENTATION",
  "DOLLHOUSE",
  "CUTAWAY",
  "VR"
 ],
 "orthographic_modes": [
  "FLOOR_PLAN_2D",
  "SECTION",
  "ELEVATION"
 ],
 "visual_layers": [
  "ARCHITECTURE",
  "STRUCTURE",
  "MEP",
  "FLS",
  "COORDINATION",
  "FURNITURE",
  "SITE",
  "LANDSCAPE",
  "ENTOURAGE"
 ],
 "layer_note": "layers toggle independently. PRESENTATION-family modes may hide technical layers; ENGINEERING mode may not — hiding a discipline in the engineering view would misrepresent the model rather than present it.",
 "mode_default_layers": {
  "ENGINEERING": [
   "ARCHITECTURE",
   "STRUCTURE",
   "MEP",
   "FLS"
  ],
  "ARCHITECTURAL": [
   "ARCHITECTURE",
   "SITE"
  ],
  "PRESENTATION": [
   "ARCHITECTURE",
   "SITE",
   "LANDSCAPE"
  ],
  "DOLLHOUSE": [
   "ARCHITECTURE",
   "FURNITURE",
   "SITE"
  ],
  "CUTAWAY": [
   "ARCHITECTURE",
   "STRUCTURE",
   "SITE"
  ],
  "FLOOR_PLAN_2D": [
   "ARCHITECTURE"
  ],
  "SECTION": [
   "ARCHITECTURE"
  ],
  "ELEVATION": [
   "ARCHITECTURE"
  ],
  "VR": [
   "ARCHITECTURE",
   "SITE",
   "LANDSCAPE"
  ]
 },
 "clash_overlay_modes": [
  "ENGINEERING"
 ],
 "clash_overlay_note": "coordination clashes are an ENGINEERING overlay and are off by default everywhere else. They are never removed from the model to make an image attractive — they are simply not drawn in an architectural presentation, and the engineering view always shows them on request.",
 "material_class": "VISUAL_MATERIAL",
 "material_class_note": "every entry in this library is appearance only. It carries no structural strength, no fire rating, no reaction-to-fire class, no thermal conductivity, no U-value and no acoustic rating, and none may be inferred from its name. A wall that looks like concrete is not a concrete wall.",
 "materials": {
  "paint_white": {
   "base_color": "#f2f1ee",
   "roughness": 0.92,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "paint"
  },
  "paint_warm": {
   "base_color": "#e9e2d6",
   "roughness": 0.92,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "paint"
  },
  "paint_grey": {
   "base_color": "#c9cbcc",
   "roughness": 0.9,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "paint"
  },
  "plaster": {
   "base_color": "#e6e2da",
   "roughness": 0.95,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "plaster"
  },
  "concrete": {
   "base_color": "#b8b8b4",
   "roughness": 0.88,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "concrete"
  },
  "concrete_dark": {
   "base_color": "#8d8f8e",
   "roughness": 0.86,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "concrete"
  },
  "stone": {
   "base_color": "#cdc4b4",
   "roughness": 0.8,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "stone"
  },
  "marble": {
   "base_color": "#efeeea",
   "roughness": 0.25,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "stone"
  },
  "wood_light": {
   "base_color": "#c79f6d",
   "roughness": 0.62,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "wood"
  },
  "wood_dark": {
   "base_color": "#7a5433",
   "roughness": 0.58,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "wood"
  },
  "glass_clear": {
   "base_color": "#cfe3ec",
   "roughness": 0.06,
   "metalness": 0.0,
   "opacity": 0.28,
   "family": "glass"
  },
  "glass_tinted": {
   "base_color": "#8fa9b6",
   "roughness": 0.08,
   "metalness": 0.0,
   "opacity": 0.42,
   "family": "glass"
  },
  "metal_steel": {
   "base_color": "#9aa0a6",
   "roughness": 0.35,
   "metalness": 0.9,
   "opacity": 1.0,
   "family": "metal"
  },
  "metal_dark": {
   "base_color": "#4d5257",
   "roughness": 0.4,
   "metalness": 0.85,
   "opacity": 1.0,
   "family": "metal"
  },
  "metal_brass": {
   "base_color": "#b08d4f",
   "roughness": 0.3,
   "metalness": 0.95,
   "opacity": 1.0,
   "family": "metal"
  },
  "tile": {
   "base_color": "#dcdcd6",
   "roughness": 0.3,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "tile"
  },
  "carpet": {
   "base_color": "#8a8378",
   "roughness": 0.98,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "carpet"
  },
  "fabric": {
   "base_color": "#b7ada0",
   "roughness": 0.95,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "fabric"
  },
  "asphalt": {
   "base_color": "#4a4a4c",
   "roughness": 0.95,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "asphalt"
  },
  "grass": {
   "base_color": "#6f8f4a",
   "roughness": 1.0,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "grass"
  },
  "water": {
   "base_color": "#3f7f9c",
   "roughness": 0.05,
   "metalness": 0.0,
   "opacity": 0.75,
   "family": "water"
  },
  "roof_tile": {
   "base_color": "#8d5b46",
   "roughness": 0.75,
   "metalness": 0.0,
   "opacity": 1.0,
   "family": "tile"
  },
  "technical": {
   "base_color": "#8fa3b8",
   "roughness": 0.7,
   "metalness": 0.1,
   "opacity": 1.0,
   "family": "technical"
  }
 },
 "material_families": [
  "paint",
  "plaster",
  "concrete",
  "stone",
  "wood",
  "glass",
  "metal",
  "tile",
  "carpet",
  "fabric",
  "asphalt",
  "grass",
  "water",
  "technical"
 ],
 "material_provenance": [
  "USER",
  "IMPORTED",
  "AI_SUGGESTED",
  "SYSTEM_DEFAULT",
  "VISUAL_THEME"
 ],
 "provenance_note": "a material chosen by the system is SYSTEM_DEFAULT and a material chosen by a theme is VISUAL_THEME. Neither is ever recorded as a user requirement, and an AI-suggested finish stays AI_SUGGESTED until a human states otherwise.",
 "themes": [
  "Modern",
  "Contemporary",
  "Classic",
  "Industrial",
  "Minimal",
  "Luxury",
  "Neutral"
 ],
 "theme_note": "a theme selects finishes and light colour only. It cannot change a room dimension, a layout, an opening, a level count, a building type or any engineering system, and the test suite asserts that the compiled architectural model is byte-identical across every theme.",
 "theme_palette": {
  "Modern": {
   "wall": "paint_white",
   "floor": "wood_light",
   "ceiling": "paint_white",
   "roof": "concrete",
   "frame": "metal_dark",
   "glass": "glass_clear",
   "accent": "wood_dark"
  },
  "Contemporary": {
   "wall": "paint_warm",
   "floor": "tile",
   "ceiling": "paint_white",
   "roof": "concrete",
   "frame": "metal_steel",
   "glass": "glass_clear",
   "accent": "stone"
  },
  "Classic": {
   "wall": "plaster",
   "floor": "marble",
   "ceiling": "plaster",
   "roof": "roof_tile",
   "frame": "wood_dark",
   "glass": "glass_clear",
   "accent": "wood_dark"
  },
  "Industrial": {
   "wall": "concrete",
   "floor": "concrete_dark",
   "ceiling": "concrete",
   "roof": "metal_dark",
   "frame": "metal_dark",
   "glass": "glass_tinted",
   "accent": "metal_steel"
  },
  "Minimal": {
   "wall": "paint_white",
   "floor": "concrete",
   "ceiling": "paint_white",
   "roof": "concrete",
   "frame": "metal_steel",
   "glass": "glass_clear",
   "accent": "paint_grey"
  },
  "Luxury": {
   "wall": "marble",
   "floor": "marble",
   "ceiling": "plaster",
   "roof": "stone",
   "frame": "metal_brass",
   "glass": "glass_clear",
   "accent": "wood_dark"
  },
  "Neutral": {
   "wall": "paint_white",
   "floor": "tile",
   "ceiling": "paint_white",
   "roof": "concrete",
   "frame": "metal_steel",
   "glass": "glass_clear",
   "accent": "paint_grey"
  }
 },
 "default_theme": "Neutral",
 "engineering_palette": {
  "ARCH_WALL": "#cfd4d9",
  "ARCH_SLAB": "#b9c0c7",
  "ARCH_OPENING": "#8fb7d6",
  "STRUCTURE": "#e0a458",
  "MEP": "#5aa9e6",
  "FLS": "#e05a5a",
  "COORDINATION": "#ff2d55"
 },
 "decoration_class": "VISUAL_DECORATION",
 "decoration_kinds": [
  "sofa",
  "table",
  "chair",
  "bed",
  "cabinet",
  "tv",
  "rug",
  "plant",
  "curtain",
  "lamp",
  "decor"
 ],
 "decoration_note": "decoration is VISUAL_ONLY and is generated by the renderer, never by the user's brief. It is excluded from object preservation, coverage requirements, engineering exports, code evaluation, MEP loads and occupant counts. An object the user actually asked for lives in the engineering model and stays there — it is never re-labelled as decoration, and decoration is never promoted into the model without an explicit user action that this phase does not implement.",
 "entourage_class": "VISUAL_ONLY_ENTOURAGE",
 "entourage_kinds": [
  "person",
  "car",
  "bicycle"
 ],
 "landscape_class": "VISUAL_ONLY_LANDSCAPE",
 "landscape_kinds": [
  "tree",
  "shrub",
  "grass_patch"
 ],
 "site_note": "site geometry is never invented. A visual ground plane, a sky and landscape placeholders are allowed and are tagged visual_only; a road, a parking bay, a fence or a pool appears only where the model states one.",
 "water_kinds": [
  "pool",
  "fountain",
  "water_feature"
 ],
 "water_note": "visual water is emitted only for an explicitly represented pool, fountain or water feature. No pool is ever invented.",
 "camera_presets": [
  "EXTERIOR_FRONT",
  "EXTERIOR_REAR",
  "EXTERIOR_CORNER",
  "TOP",
  "DOLLHOUSE",
  "INTERIOR_ROOM",
  "WALKTHROUGH",
  "SECTION",
  "ELEVATION",
  "PANORAMA_360"
 ],
 "camera_note": "camera state is presentation state, never model truth. Framing is computed from the model's own bounding volume with a stated margin; a camera change never regenerates geometry, and a door visible in one view exists at the same coordinates in every other view.",
 "camera_defaults": {
  "fov_deg": 45.0,
  "margin": 1.25,
  "near_m": 0.05,
  "far_m": 4000.0,
  "eye_height_m": 1.6,
  "min_distance_m": 2.0
 },
 "lighting_presets": [
  "DAY",
  "GOLDEN_HOUR",
  "NIGHT"
 ],
 "lighting_preset_params": {
  "DAY": {
   "sun_elevation_deg": 58.0,
   "sun_azimuth_deg": 140.0,
   "sun_intensity": 3.0,
   "sun_color": "#fff6e6",
   "sky_intensity": 1.0,
   "ambient_intensity": 0.45,
   "ambient_color": "#dfeaff",
   "background": "sky",
   "exposure": 1.0
  },
  "GOLDEN_HOUR": {
   "sun_elevation_deg": 12.0,
   "sun_azimuth_deg": 258.0,
   "sun_intensity": 2.4,
   "sun_color": "#ffca7a",
   "sky_intensity": 0.8,
   "ambient_intensity": 0.35,
   "ambient_color": "#ffd9b0",
   "background": "sky",
   "exposure": 1.15
  },
  "NIGHT": {
   "sun_elevation_deg": -14.0,
   "sun_azimuth_deg": 300.0,
   "sun_intensity": 0.05,
   "sun_color": "#334a6b",
   "sky_intensity": 0.12,
   "ambient_intensity": 0.12,
   "ambient_color": "#26334d",
   "background": "night_sky",
   "exposure": 1.3
  }
 },
 "default_lighting": "DAY",
 "lighting_note": "presentation lighting is a visual light rig. It is a different layer from MEP lighting fixtures: a visual light is never counted as a luminaire, an MEP fixture is never treated as a presentation light source, and no illuminance, lux level or lighting adequacy is claimed anywhere.",
 "night_fixture_note": "NIGHT may place a small visual emitter at a represented MEP lighting terminal so interiors read at night. That emitter is appearance only and asserts nothing about the fixture's output or adequacy.",
 "quality_profiles": [
  "LOW",
  "MEDIUM",
  "HIGH",
  "ULTRA"
 ],
 "quality_params": {
  "LOW": {
   "pixel_ratio": 1.0,
   "shadows": false,
   "shadow_map": 0,
   "texture_px": 256,
   "antialias": false,
   "tone_mapping": "none",
   "environment": "flat",
   "max_visual_objects": 4000
  },
  "MEDIUM": {
   "pixel_ratio": 1.5,
   "shadows": true,
   "shadow_map": 1024,
   "texture_px": 512,
   "antialias": true,
   "tone_mapping": "aces",
   "environment": "room",
   "max_visual_objects": 12000
  },
  "HIGH": {
   "pixel_ratio": 2.0,
   "shadows": true,
   "shadow_map": 2048,
   "texture_px": 1024,
   "antialias": true,
   "tone_mapping": "aces",
   "environment": "room",
   "max_visual_objects": 30000
  },
  "ULTRA": {
   "pixel_ratio": 2.0,
   "shadows": true,
   "shadow_map": 4096,
   "texture_px": 2048,
   "antialias": true,
   "tone_mapping": "aces",
   "environment": "room",
   "max_visual_objects": 60000
  }
 },
 "default_quality": "MEDIUM",
 "quality_note": "a quality profile controls pixel ratio, shadow maps, texture size, post-processing and environment quality. It never changes geometry, and a lower profile drops visual-only detail before it ever drops a modelled element.",
 "lod_levels": [
  "FULL",
  "SIMPLIFIED",
  "MASSING"
 ],
 "lod_note": "level of detail applies to visual-only assets and to distant repeated objects. A modelled architectural, structural, MEP or fire element is never removed by LOD in ENGINEERING mode, and the scene records which LOD each object was emitted at.",
 "instancing_note": "repeated visual-only objects sharing an asset and a material are grouped into instancing candidates. A modelled element is never merged into an instance group, because merging would destroy per-element selection and traceability.",
 "floor_plan_styles": [
  "TECHNICAL",
  "CLEAN",
  "MONOCHROME",
  "ZONING"
 ],
 "floor_plan_note": "the plan is projected from the same architectural geometry as the 3D view. It is a derived drawing, not a CAD deliverable, and it makes no CAD-grade claim about tolerance, line weight standards or drafting conventions.",
 "dimension_sources": [
  "model",
  "unknown"
 ],
 "dimension_note": "a dimension is emitted only where the model states the geometry it measures. An unknown value is emitted as null with source 'unknown' and is never replaced by a plausible number.",
 "section_axes": [
  "x",
  "z"
 ],
 "elevation_faces": [
  "NORTH",
  "SOUTH",
  "EAST",
  "WEST"
 ],
 "elevation_note": "an elevation projects the real envelope and its real openings. No opening is ever added to balance a facade.",
 "dollhouse_note": "dollhouse hides the roof and clips enclosure above a stated cut height. It is expressed as visibility and clipping directives over the SAME objects — no second model is generated, no wall is shortened in the model, and every room keeps its exact position and size.",
 "cutaway_methods": [
  "CLIP_PLANE",
  "LEVEL_ISOLATION",
  "WALL_CLIP"
 ],
 "cutaway_note": "cutaway is reversible rendering state. Clipping planes and visibility flags are recorded on the scene; the model geometry is untouched and restoring the scene restores the full view exactly.",
 "snapshot_formats": [
  "PNG",
  "JPEG"
 ],
 "snapshot_defaults": {
  "width": 1920,
  "height": 1080,
  "format": "PNG",
  "quality": 0.92,
  "transparent": false
 },
 "snapshot_max_px": 33177600,
 "render_kinds": [
  "DETERMINISTIC_RENDER",
  "AI_ENHANCED_VISUALISATION"
 ],
 "render_authority": {
  "DETERMINISTIC_RENDER": "ENGINEERING_VIEW_OF_MODEL",
  "AI_ENHANCED_VISUALISATION": "VISUALISATION"
 },
 "render_authority_note": "only a deterministic render of the compiled geometry may be labelled an engineering view. Any AI-enhanced image is labelled VISUALISATION and can never be presented as the model.",
 "control_buffers": [
  "depth",
  "normal",
  "object_id",
  "semantic_mask",
  "edge",
  "room_id"
 ],
 "control_buffer_note": "control buffers are deterministic descriptors of the real geometry, computed from the compiled model. They exist to constrain a future AI enhancement pass and to make drift detectable; they are not themselves an enhancement, and this phase rasterises none of them. An AI request carries requested_control_buffers (the ordered names asked for) AND control_buffers (a map from each requested name to its deterministic descriptor: the ids, classes or counts a future generator would consume). No pixel buffer is generated, claimed or implied.",
 "ai_enhancement_stages": [
  "CANONICAL_MODEL",
  "DETERMINISTIC_BASE_RENDER",
  "CONTROL_BUFFERS",
  "AI_ENHANCEMENT",
  "PRESENTATION_IMAGE"
 ],
 "ai_may_change": [
  "materials",
  "lighting",
  "vegetation",
  "weather",
  "furniture_style",
  "surface_detail",
  "sky",
  "post_processing"
 ],
 "ai_may_not_change": [
  "wall_positions",
  "door_count",
  "window_count",
  "floor_count",
  "stair_location",
  "building_footprint",
  "room_count",
  "level_elevations"
 ],
 "ai_note": "AI enhancement is strictly downstream of the model. This phase ships the interface, the constraints and the drift check — it ships NO image generator, makes no network call, and provides no path by which an enhanced image can be written back into any model.",
 "drift_codes": [
  "VISUAL_GEOMETRY_DRIFT",
  "VISUAL_FEATURE_COUNT_MISMATCH",
  "VISUAL_FOOTPRINT_MISMATCH",
  "VISUAL_LEVEL_COUNT_MISMATCH",
  "VISUAL_CONTROL_BUFFER_MISSING",
  "VISUAL_SOURCE_HASH_MISMATCH",
  "VISUAL_SIGNATURE_MISSING"
 ],
 "drift_severities": [
  "INFO",
  "WARNING",
  "ERROR"
 ],
 "drift_code_severity": {
  "VISUAL_GEOMETRY_DRIFT": "ERROR",
  "VISUAL_FEATURE_COUNT_MISMATCH": "ERROR",
  "VISUAL_FOOTPRINT_MISMATCH": "ERROR",
  "VISUAL_LEVEL_COUNT_MISMATCH": "ERROR",
  "VISUAL_CONTROL_BUFFER_MISSING": "WARNING",
  "VISUAL_SOURCE_HASH_MISMATCH": "WARNING",
  "VISUAL_SIGNATURE_MISSING": "ERROR"
 },
 "drift_note": "a drift finding says an image disagrees with the model it claims to depict. It never rewrites the model, never silently discards the image, and never asserts which of the two is aesthetically better — it marks the image as untrustworthy as geometry.",
 "asset_classes": [
  "VISUAL_ONLY",
  "SEMANTIC"
 ],
 "asset_required_fields": [
  "id",
  "type",
  "asset_class",
  "dimensions_m",
  "license",
  "source"
 ],
 "asset_licenses": [
  "PROCEDURAL",
  "CC0",
  "CC-BY",
  "PROPRIETARY_LICENSED",
  "UNKNOWN"
 ],
 "asset_note": "the asset library is local and controlled. Nothing is downloaded automatically, an asset with UNKNOWN license is never emitted into a scene, asset metadata is data and is never executed, and an asset that is missing degrades to simple procedural geometry rather than breaking the render.",
 "procedural_fallback_note": "when no library asset is available the scene emits a labelled procedural box of the stated dimensions. It is tagged as a fallback and, like every render fallback in this platform, it is never promoted into engineering data.",
 "texture_note": "no remote CDN texture is required or requested. Materials are parametric (base colour, roughness, metalness, opacity) and any texture must be locally vendored; this phase introduces no new production network dependency.",
 "vr_scale_note": "one model metre is one physical metre in VR. Any visualisation scaling is explicit, is recorded on the scene, and never happens silently.",
 "walkthrough_note": "walkthrough is a visual camera path. It is not accessibility-compliant navigation, it makes no clearance, width or route-adequacy claim, and it does not alter the navigation, egress or walking-distance layers.",
 "export_note": "the engineering GLB keeps its current semantics. A presentation GLB is a separate, explicitly requested export that may carry visual materials, decoration and landscape; the two are never interchanged, and visual scene state is never merged into the engineering JSON — it is written, if at all, into a separate additive block.",
 "presentation_block_key": "presentation",
 "revision_note": "a render records the model hash it was produced from. If the building changes afterwards the render remains historical and is reported STALE rather than relabelled current, and no visual state ever enters a revision hash.",
 "forbidden_claims": [
  "photoreal_is_measured",
  "render_is_as_built",
  "ai_generated_geometry",
  "visually_verified_compliance",
  "lighting_adequate",
  "material_fire_rated",
  "material_structural_grade",
  "thermally_compliant",
  "accessibility_verified",
  "decoration_is_engineering_object",
  "entourage_is_occupant"
 ],
 "id_patterns": {
  "scene": "vscene_<model_hash_16>_<mode>",
  "object": "<bid>.vis.<n>",
  "decoration": "<bid>.vis.deco_<n>",
  "landscape": "<bid>.vis.land_<n>",
  "entourage": "<bid>.vis.ent_<n>",
  "light": "<bid>.vis.light_<n>",
  "camera": "<bid>.vis.cam_<preset>",
  "render": "vrender_<sha256_16>"
 },
 "rule_inputs": [
  "visual.scene.object_count",
  "visual.scene.visual_only_count",
  "visual.scene.mode",
  "visual.render.exists"
 ],
 "rule_note": "factual inputs only. Nothing here is a regulatory input, appearance is never compared to a threshold, and no visual value ever feeds a code evaluation.",
 "no_generator_note": "this phase ships NO geometry generator, NO design operation, NO image generator and NO network call. It answers how the model should be shown, never what the model should be.",
 "validation_codes": [
  "MATERIAL_NOT_VISUAL_CLASS",
  "MATERIAL_CARRIES_ENGINEERING_PROPERTY",
  "MATERIAL_NOT_IN_LIBRARY",
  "MATERIAL_PROVENANCE_INVALID",
  "VISUAL_OBJECT_MARKED_SEMANTIC",
  "VISUAL_ONLY_OBJECT_WITH_SOURCE",
  "DECORATION_LINKED_TO_MODEL_ELEMENT",
  "MODELLED_OBJECT_WITHOUT_SOURCE"
 ],
 "source_reference_invariant": "the source-reference rule is universal and symmetric, and holds for every object regardless of visual_class, material, theme, asset, LOD, geometry source, render mode, discipline or decoration category. If visual_only is false the object MUST carry a source_element_id identifying its canonical source element; failing that is MODELLED_OBJECT_WITHOUT_SOURCE. If visual_only is true the object MUST NOT carry a source_element_id at all; failing that is VISUAL_ONLY_OBJECT_WITH_SOURCE. DECORATION_LINKED_TO_MODEL_ELEMENT is a specialisation that is reported in addition for a VISUAL_DECORATION object, never instead of the universal code.",
 "ai_request_fields": [
  "stage_pipeline",
  "scene_id",
  "model_hash",
  "building_id",
  "base_render_required",
  "requested_control_buffers",
  "control_buffers",
  "geometry_signature",
  "prompt",
  "strength",
  "may_change",
  "may_not_change",
  "writes_to_model",
  "generator_shipped",
  "network_call",
  "authority"
 ],
 "ai_request_note": "every AI request carries a deterministic descriptor for each requested control buffer and the geometry signature the enhancement may not change. A request with no geometry signature is not a valid constrained request: the consistency check reports VISUAL_SIGNATURE_MISSING rather than silently passing an unconstrained image."
};
const VIS_SCHEMA = ACS_VISUAL_SPEC.schema;
const VIS_COMPILER_VERSION = ACS_VISUAL_SPEC.compiler_version;
const VIS_MODES = ACS_VISUAL_SPEC.visual_modes;
const VIS_ENGINEERING_MODES = ACS_VISUAL_SPEC.engineering_modes;
const VIS_PRESENTATION_MODES = ACS_VISUAL_SPEC.presentation_modes;
const VIS_ORTHO_MODES = ACS_VISUAL_SPEC.orthographic_modes;
const VIS_LAYERS = ACS_VISUAL_SPEC.visual_layers;
const VIS_MODE_LAYERS = ACS_VISUAL_SPEC.mode_default_layers;
const VIS_MATERIALS = ACS_VISUAL_SPEC.materials;
const VIS_MATERIAL_CLASS = ACS_VISUAL_SPEC.material_class;
const VIS_PROVENANCE = ACS_VISUAL_SPEC.material_provenance;
const VIS_THEMES = ACS_VISUAL_SPEC.themes;
const VIS_THEME_PALETTE = ACS_VISUAL_SPEC.theme_palette;
const VIS_DEFAULT_THEME = ACS_VISUAL_SPEC.default_theme;
const VIS_ENG_PALETTE = ACS_VISUAL_SPEC.engineering_palette;
const VIS_DECORATION_CLASS = ACS_VISUAL_SPEC.decoration_class;
const VIS_DECORATION_KINDS = ACS_VISUAL_SPEC.decoration_kinds;
const VIS_ENTOURAGE_CLASS = ACS_VISUAL_SPEC.entourage_class;
const VIS_LANDSCAPE_CLASS = ACS_VISUAL_SPEC.landscape_class;
const VIS_WATER_KINDS = ACS_VISUAL_SPEC.water_kinds;
const VIS_CAMERA_PRESETS = ACS_VISUAL_SPEC.camera_presets;
const VIS_CAMERA_DEFAULTS = ACS_VISUAL_SPEC.camera_defaults;
const VIS_LIGHTING_PRESETS = ACS_VISUAL_SPEC.lighting_presets;
const VIS_LIGHTING_PARAMS = ACS_VISUAL_SPEC.lighting_preset_params;
const VIS_DEFAULT_LIGHTING = ACS_VISUAL_SPEC.default_lighting;
const VIS_QUALITY_PROFILES = ACS_VISUAL_SPEC.quality_profiles;
const VIS_QUALITY_PARAMS = ACS_VISUAL_SPEC.quality_params;
const VIS_DEFAULT_QUALITY = ACS_VISUAL_SPEC.default_quality;
const VIS_LOD_LEVELS = ACS_VISUAL_SPEC.lod_levels;
const VIS_PLAN_STYLES = ACS_VISUAL_SPEC.floor_plan_styles;
const VIS_SECTION_AXES = ACS_VISUAL_SPEC.section_axes;
const VIS_ELEVATION_FACES = ACS_VISUAL_SPEC.elevation_faces;
const VIS_CUTAWAY_METHODS = ACS_VISUAL_SPEC.cutaway_methods;
const VIS_SNAPSHOT_FORMATS = ACS_VISUAL_SPEC.snapshot_formats;
const VIS_SNAPSHOT_DEFAULTS = ACS_VISUAL_SPEC.snapshot_defaults;
const VIS_SNAPSHOT_MAX_PX = ACS_VISUAL_SPEC.snapshot_max_px;
const VIS_RENDER_KINDS = ACS_VISUAL_SPEC.render_kinds;
const VIS_RENDER_AUTHORITY = ACS_VISUAL_SPEC.render_authority;
const VIS_CONTROL_BUFFERS = ACS_VISUAL_SPEC.control_buffers;
const VIS_AI_STAGES = ACS_VISUAL_SPEC.ai_enhancement_stages;
const VIS_AI_MAY_CHANGE = ACS_VISUAL_SPEC.ai_may_change;
const VIS_AI_MAY_NOT_CHANGE = ACS_VISUAL_SPEC.ai_may_not_change;
const VIS_DRIFT_CODES = ACS_VISUAL_SPEC.drift_codes;
const VIS_VALIDATION_CODES = ACS_VISUAL_SPEC.validation_codes;
const VIS_DRIFT_SEVERITIES = ACS_VISUAL_SPEC.drift_severities;
const VIS_DRIFT_SEVERITY = ACS_VISUAL_SPEC.drift_code_severity;
const VIS_ASSET_CLASSES = ACS_VISUAL_SPEC.asset_classes;
const VIS_ASSET_LICENSES = ACS_VISUAL_SPEC.asset_licenses;
const VIS_PRESENTATION_KEY = ACS_VISUAL_SPEC.presentation_block_key;
const _VIS_EPS = 1e-9;

function _vQ(v){ const r=_pyRound(Number(v),6); return r===0?0:r; }
function _vNum(v){ return _snum(v); }
function _vCanon(o){ return JSON.stringify(_vSort(o)); }
function _vSort(v){ if(Array.isArray(v)) return v.map(_vSort);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).sort(_scmp).forEach(k=>{o[k]=_vSort(v[k]);}); return o; }
  return v; }
function _vSha16(o){ return sha256Hex(_vCanon(o)).slice(0,16); }
/* قيمة مذكورة إن وُجدت، وإلّا احتياط عرض — مع الإفصاح عن أيّهما استُعمل */
function _vVal(field,fallbackOk){
  if(!field||typeof field!=='object') return [null,'unknown'];
  if(field.value!==null&&field.value!==undefined) return [Number(field.value),'model'];
  if(fallbackOk!==false&&field.render_fallback!==null&&field.render_fallback!==undefined)
    return [Number(field.render_fallback),'display_fallback'];
  return [null,'unknown']; }
function _vMode(m){ m=String(m||'PRESENTATION').toUpperCase();
  return VIS_MODES.indexOf(m)>=0?m:'PRESENTATION'; }
function _vTheme(t){ t=String(t===null||t===undefined?VIS_DEFAULT_THEME:t);
  return VIS_THEMES.indexOf(t)>=0?t:VIS_DEFAULT_THEME; }
function _vLight(p){ p=String(p||VIS_DEFAULT_LIGHTING).toUpperCase();
  return VIS_LIGHTING_PRESETS.indexOf(p)>=0?p:VIS_DEFAULT_LIGHTING; }
function _vQuality(p){ p=String(p||VIS_DEFAULT_QUALITY).toUpperCase();
  return VIS_QUALITY_PROFILES.indexOf(p)>=0?p:VIS_DEFAULT_QUALITY; }
function _vStyle(s){ s=String(s||'TECHNICAL').toUpperCase();
  return VIS_PLAN_STYLES.indexOf(s)>=0?s:'TECHNICAL'; }

/* ------------------------------------------------- مكتبة الأصول -------- */
const _VIS_ASSETS=[
 {id:'asset.proc.box',type:'generic',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.0,d:1.0,h:1.0},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.sofa',type:'sofa',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:2.0,d:0.9,h:0.8},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.table',type:'table',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.4,d:0.8,h:0.75},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.chair',type:'chair',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:0.5,d:0.5,h:0.9},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.bed',type:'bed',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.6,d:2.0,h:0.5},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.cabinet',type:'cabinet',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.2,d:0.5,h:1.8},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.tv',type:'tv',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.2,d:0.08,h:0.7},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.rug',type:'rug',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:2.4,d:1.6,h:0.02},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.plant',type:'plant',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:0.6,d:0.6,h:1.2},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.lamp',type:'lamp',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:0.35,d:0.35,h:1.5},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.tree',type:'tree',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:3.0,d:3.0,h:5.0},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.shrub',type:'shrub',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.0,d:1.0,h:0.8},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.person',type:'person',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:0.5,d:0.35,h:1.7},license:'PROCEDURAL',source:'acs_visual',author:null},
 {id:'asset.proc.car',type:'car',asset_class:'VISUAL_ONLY',
  dimensions_m:{w:1.8,d:4.4,h:1.5},license:'PROCEDURAL',source:'acs_visual',author:null}];
const _VIS_ASSET_INDEX={}; _VIS_ASSETS.forEach(a=>{_VIS_ASSET_INDEX[a.id]=a;});
const _VIS_ASSET_BY_TYPE={};
_VIS_ASSETS.forEach(a=>{ if(!Object.prototype.hasOwnProperty.call(_VIS_ASSET_BY_TYPE,a.type))
  _VIS_ASSET_BY_TYPE[a.type]=a.id; });
function visAssetLibrary(){ return _VIS_ASSETS.map(a=>JSON.parse(JSON.stringify(a))); }
function visAssetById(aid){ const a=_VIS_ASSET_INDEX[aid];
  return a?JSON.parse(JSON.stringify(a)):null; }
/* أصل من المكتبة إن وُجد، وإلّا صندوق إجرائي مُعلَن كاحتياط */
function _vAssetFor(kind){
  if(Object.prototype.hasOwnProperty.call(_VIS_ASSET_BY_TYPE,kind))
    return [_VIS_ASSET_BY_TYPE[kind],false];
  return ['asset.proc.box',true]; }
/* يرفض الأصل الناقص أو مجهول الرخصة أو الذي يحاول حمل شيفرة */
function visValidateAsset(asset){
  const issues=[];
  if(!asset||typeof asset!=='object'||Array.isArray(asset)) return ['ASSET_NOT_AN_OBJECT'];
  ACS_VISUAL_SPEC.asset_required_fields.forEach(f=>{
    if(asset[f]===null||asset[f]===undefined||asset[f]==='') issues.push('ASSET_FIELD_MISSING:'+f); });
  if(VIS_ASSET_CLASSES.indexOf(asset.asset_class)<0) issues.push('ASSET_CLASS_INVALID');
  if(VIS_ASSET_LICENSES.indexOf(asset.license)<0) issues.push('ASSET_LICENSE_INVALID');
  if(asset.license==='UNKNOWN') issues.push('ASSET_LICENSE_UNKNOWN_NOT_EMITTED');
  const d=asset.dimensions_m;
  if(!d||typeof d!=='object'||['w','d','h'].some(k=>_vNum(d[k])===null||_vNum(d[k])<=0))
    issues.push('ASSET_DIMENSIONS_INVALID');
  ['script','code','eval','onload','src','url','href','exec'].forEach(k=>{
    if(Object.prototype.hasOwnProperty.call(asset,k))
      issues.push('ASSET_METADATA_MUST_NOT_CARRY_CODE:'+k); });
  return issues.sort(_scmp); }

/* ----------------------------------------------------------- المواد ---- */
function visMaterial(mid){
  const m=VIS_MATERIALS[mid]; if(m===null||m===undefined) return null;
  const out=JSON.parse(JSON.stringify(m));
  out.id=mid; out.material_class=VIS_MATERIAL_CLASS;
  out.structural_material=false; out.fire_rating=null; out.thermal_property=null;
  out.note='visual material only — no structural, fire or thermal property is implied by '+
           'its appearance or its name';
  return out; }
/* اختيار مادة مع إسناد صريح: المستخدم أوّلاً، ثم السمة، ثم افتراض النظام */
function _vAssign(theme,slot,overrides,subject){
  const ov=(overrides||{})[subject];
  if(ov&&typeof ov==='object'&&Object.prototype.hasOwnProperty.call(VIS_MATERIALS,ov.material)){
    const pr=String(ov.provenance||'USER').toUpperCase();
    return [ov.material,VIS_PROVENANCE.indexOf(pr)>=0?pr:'USER']; }
  if(typeof ov==='string'&&Object.prototype.hasOwnProperty.call(VIS_MATERIALS,ov))
    return [ov,'USER'];
  const pal=VIS_THEME_PALETTE[theme]||{};
  const mid=pal[slot];
  if(Object.prototype.hasOwnProperty.call(VIS_MATERIALS,mid))
    return [mid,theme!==VIS_DEFAULT_THEME?'VISUAL_THEME':'SYSTEM_DEFAULT'];
  return ['paint_white','SYSTEM_DEFAULT']; }

/* -------------------------------------------------- هندسة عالمية ------- */
function _vRot(px,pz,rotDeg,ox,oz){
  const r=(Number(rotDeg)||0)*Math.PI/180, ca=Math.cos(r), sa=Math.sin(r);
  return [(ox||0)+px*ca-pz*sa,(oz||0)+px*sa+pz*ca]; }
function _vWorld(cx,cy,cz,ex,ey,ez,rotY,transform){
  const t=transform||{}, brot=Number(t.rotation_deg)||0;
  const p=t.position||{}, px=Number(p.x)||0, pz=Number(p.z)||0;
  const w=_vRot(cx,cz,brot,px,pz);
  return {type:'box',cx:_vQ(w[0]),cy:_vQ(cy),cz:_vQ(w[1]),
    ex:_vQ(Math.abs(ex)),ey:_vQ(Math.abs(ey)),ez:_vQ(Math.abs(ez)),
    rot_y:_vQ((Number(rotY)||0)+brot*Math.PI/180)}; }
function _vSeg(a,b,w,h,transform){
  const dx=b[0]-a[0], dz=b[2]-a[2], ln=Math.sqrt(dx*dx+dz*dz);
  if(ln<=1e-9) return _vWorld((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2,
    Math.max(w,1e-3),Math.max(h,1e-3),Math.max(w,1e-3),0,transform);
  return _vWorld((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2,
    ln,Math.max(h,1e-3),Math.max(w,1e-3),Math.atan2(-dz,dx),transform); }
function _vObj(oid,kind,layer,geom,materialId,provenance,meta){
  const o={id:oid,kind:kind,layer:layer,geometry:geom,material:materialId,
    material_provenance:provenance,semantic:true,visual_only:false,lod:'FULL',
    asset_id:null,asset_fallback:false,instance_key:null,geometry_source:'model',
    visible:true,source_layer:null,source_element_id:null};
  Object.keys(meta||{}).forEach(k=>{o[k]=(meta[k]===undefined)?null:meta[k];});
  return o; }

/* ------------------------------------------------ أجسام المعماري ------ */
function _vArchObjects(arch,transform,bid,theme,overrides,mode){
  const out=[]; if(!arch) return out;
  const lv={}; (arch.levels||[]).forEach(l=>{lv[l.index]=l;});
  const wall=_vAssign(theme,'wall',overrides,'wall');
  const floor=_vAssign(theme,'floor',overrides,'floor');
  const ceil=_vAssign(theme,'ceiling',overrides,'ceiling');
  const glass=_vAssign(theme,'glass',overrides,'glass');
  const frame=_vAssign(theme,'frame',overrides,'frame');
  const roof=_vAssign(theme,'roof',overrides,'roof');
  const eng=VIS_ENGINEERING_MODES.indexOf(mode)>=0;
  (arch.walls||[]).forEach(w=>{
    const hv=_vVal(w.height_m), tv=_vVal(w.thickness_m);
    const base=(lv[w.level_index]||{}).elevation_m;
    if(hv[0]===null||tv[0]===null||base===null||base===undefined) return;
    const a=w.start,b=w.end;
    const g=_vSeg([a.x,base+hv[0]/2,a.z],[b.x,base+hv[0]/2,b.z],tv[0],hv[0],transform);
    out.push(_vObj(w.id,'WALL','ARCHITECTURE',g,eng?'technical':wall[0],
      eng?'SYSTEM_DEFAULT':wall[1],
      {source_layer:'ARCHITECTURE',source_element_id:w.id,level_index:w.level_index,
       exposure:w.exposure,
       geometry_source:(hv[1]==='model'&&tv[1]==='model')?'model':'display_fallback',
       engineering_color:VIS_ENG_PALETTE.ARCH_WALL})); });
  (arch.openings||[]).forEach(o=>{
    const wv=_vVal(o.width_m), hv=_vVal(o.height_m);
    const base=(lv[o.level_index]||{}).elevation_m;
    if(wv[0]===null||hv[0]===null||base===null||base===undefined) return;
    let sill=0;
    if(o.type==='WINDOW'){ const sv=_vVal(o.sill_m); sill=sv[0]===null?0:sv[0]; }
    const cy=base+sill+hv[0]/2;
    const g=(o.axis==='x')?_vWorld(o.u_center,cy,o.fixed,wv[0],hv[0],0.12,0,transform)
                          :_vWorld(o.fixed,cy,o.u_center,0.12,hv[0],wv[0],0,transform);
    const isWin=o.type==='WINDOW';
    out.push(_vObj(o.id,o.type,'ARCHITECTURE',g,
      eng?'technical':(isWin?glass[0]:frame[0]),
      eng?'SYSTEM_DEFAULT':(isWin?glass[1]:frame[1]),
      {source_layer:'ARCHITECTURE',source_element_id:o.id,level_index:o.level_index,
       host_wall_id:o.host_wall_id,space_id:o.space_id,
       geometry_source:(wv[1]==='model'&&hv[1]==='model')?'model':'display_fallback',
       engineering_color:VIS_ENG_PALETTE.ARCH_OPENING})); });
  (arch.slabs||[]).forEach(s=>{
    const o=s.outline, tv=_vVal(s.thickness_m);
    if(o===null||o===undefined||s.elevation_m===null||s.elevation_m===undefined
       ||tv[0]===null) return;
    const g=_vWorld(o[0]+o[2]/2,s.elevation_m-tv[0]/2,o[1]+o[3]/2,o[2],tv[0],o[3],0,transform);
    out.push(_vObj(s.id,'SLAB','ARCHITECTURE',g,eng?'technical':floor[0],
      eng?'SYSTEM_DEFAULT':floor[1],
      {source_layer:'ARCHITECTURE',source_element_id:s.id,level_index:s.level_index,
       geometry_source:tv[1]==='model'?'model':'display_fallback',
       engineering_color:VIS_ENG_PALETTE.ARCH_SLAB})); });
  if(mode!=='ENGINEERING'){
    (arch.ceilings||[]).forEach(c=>{
      const o=c.outline, tv=_vVal(c.thickness_m);
      if(o===null||o===undefined||c.elevation_m===null||c.elevation_m===undefined
         ||tv[0]===null) return;
      const g=_vWorld(o[0]+o[2]/2,c.elevation_m+tv[0]/2,o[1]+o[3]/2,o[2],tv[0],o[3],0,transform);
      out.push(_vObj(c.id,'CEILING','ARCHITECTURE',g,ceil[0],ceil[1],
        {source_layer:'ARCHITECTURE',source_element_id:c.id,space_id:c.space_id,
         geometry_source:tv[1]==='model'?'model':'display_fallback'})); }); }
  (arch.roofs||[]).forEach(r=>{
    const o=r.outline, tv=_vVal(r.thickness_m);
    if(o===null||o===undefined||r.elevation_m===null||r.elevation_m===undefined
       ||tv[0]===null) return;
    const g=_vWorld(o[0]+o[2]/2,r.elevation_m+tv[0]/2,o[1]+o[3]/2,o[2],tv[0],o[3],0,transform);
    out.push(_vObj(r.id,'ROOF','ARCHITECTURE',g,roof[0],roof[1],
      {source_layer:'ARCHITECTURE',source_element_id:r.id,
       geometry_source:tv[1]==='model'?'model':'display_fallback'})); });
  /* درج مرئي عند نواة معلنة — موضعه وأبعاده من النموذج، لا من تقدير */
  (arch.cores||[]).forEach(c=>{
    if(c.type!=='STAIR') return;
    const fw=_vVal(c.footprint_w_m), fd=_vVal(c.footprint_d_m);
    const served=c.served_levels||[];
    if(fw[0]===null||fd[0]===null||!served.length) return;
    const base=(lv[Math.min.apply(null,served)]||{}).elevation_m;
    const top=(lv[Math.max.apply(null,served)]||{}).elevation_m;
    if(base===null||base===undefined||top===null||top===undefined||top-base<=0) return;
    const g=_vWorld(c.x,base+(top-base)/2,c.z,fw[0],top-base,fd[0],0,transform);
    out.push(_vObj(c.id,'STAIR','ARCHITECTURE',g,eng?'technical':floor[0],
      eng?'SYSTEM_DEFAULT':floor[1],
      {source_layer:'ARCHITECTURE',source_element_id:c.id,core_type:c.type,
       geometry_source:(fw[1]==='model'&&fd[1]==='model')?'model':'display_fallback'})); });
  return out; }

/* غطاء سقف بصريّ حين لا يذكر النموذج سقفاً — VISUAL_ONLY ولا يصير سقفاً هندسياً */
function _vRoofCap(arch,transform,bid,theme,overrides){
  if(!arch||(arch.roofs||[]).length) return [];
  const lv=(arch.levels||[]).filter(l=>l.elevation_m!==null&&l.elevation_m!==undefined)
    .slice().sort((a,b)=>a.index-b.index);
  const slabs=(arch.slabs||[]).filter(s=>s.outline);
  if(!lv.length||!slabs.length) return [];
  const top=lv[lv.length-1];
  let tops=slabs.filter(s=>s.level_index===top.index);
  if(!tops.length) tops=[slabs[slabs.length-1]];
  const o=tops[0].outline;
  const hs=(arch.walls||[]).filter(w=>w.level_index===top.index)
    .map(w=>_vVal(w.height_m)[0]).filter(v=>v!==null);
  const h=hs.length?Math.max.apply(null,hs):3.0;
  const y=top.elevation_m+h;
  const roof=_vAssign(theme,'roof',overrides,'roof');
  const g=_vWorld(o[0]+o[2]/2,y+0.1,o[1]+o[3]/2,o[2],0.2,o[3],0,transform);
  return [_vObj(bid+'.vis.roof_cap','ROOF_CAP','ARCHITECTURE',g,roof[0],roof[1],
    {semantic:false,visual_only:true,geometry_source:'display_fallback',
     source_layer:null,source_element_id:null,
     note:'visual roof cap — the model states no roof; this is appearance only and is '+
          'never engineering geometry'})]; }

/* ------------------------------- أجسام التخصّصات الأخرى (كما هي) ------ */
function _vDisciplineObjects(items,layer,transform,colour){
  const out=[];
  items.forEach(it=>{
    if(!(it.ex&&it.ey&&it.ez)) return;
    const g=_vWorld(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,it.rot_y||0,transform);
    out.push(_vObj(it.name||it.id,it.kind,layer,g,'technical','SYSTEM_DEFAULT',
      {source_layer:layer,source_element_id:it.id,
       geometry_source:it.geometry_source||'model',engineering_color:colour})); });
  return out; }
function _vFlsObjects(fls,transform){
  const out=[]; if(!fls) return out;
  flsRenderItems(fls).forEach(it=>{
    if(it.render_mode!=='emitted') return;
    const g=_vWorld(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,0,transform);
    out.push(_vObj(it.id,it.kind,'FLS',g,'technical','SYSTEM_DEFAULT',
      {source_layer:'FLS',source_element_id:it.id,
       geometry_source:it.geometry_source||'model',
       engineering_color:VIS_ENG_PALETTE.FLS})); });
  return out; }

/* ------------------------------------------- الموقع والمناظر ---------- */
function _vSiteObjects(building,arch,transform,bid,theme,overrides,bbox){
  const out=[];
  const site=(building.site&&typeof building.site==='object')?building.site:null;
  let w=_vNum((site||{}).w), d=_vNum((site||{}).d);
  const stated=(w!==null&&d!==null&&w>0&&d>0);
  if(!stated&&bbox){ w=Math.max(bbox[3]-bbox[0],1.0)*3.0; d=Math.max(bbox[5]-bbox[2],1.0)*3.0; }
  if(w===null||d===null||w===undefined||d===undefined) return out;
  const cx=stated?(w/2):(bbox?((bbox[0]+bbox[3])/2):0);
  const cz=stated?(d/2):(bbox?((bbox[2]+bbox[5])/2):0);
  const g=_vWorld(cx,-0.05,cz,w,0.1,d,0,transform);
  out.push(_vObj(bid+'.vis.ground','GROUND','SITE',g,'grass','SYSTEM_DEFAULT',
    {semantic:false,visual_only:true,geometry_source:'display_fallback',
     site_dimensions_stated:!!stated,
     note:stated?'visual ground plane drawn to the stated site dimensions'
                :'visual ground plane — appearance only; no site geometry is invented and '+
                 'its extent is not a stated site boundary'}));
  return out; }
/* ماء مرئي للعناصر المائية المذكورة صراحةً فقط. لا مسبح يُختلق */
function _vWaterObjects(building,transform,bid){
  const out=[]; let n=0;
  const feats=Array.isArray(building.site_features)?building.site_features:[];
  feats.forEach(f=>{
    const k=String(f.kind||'').toLowerCase();
    if(VIS_WATER_KINDS.indexOf(k)<0) return;
    const x=_vNum(f.x), z=_vNum(f.z), fw=_vNum(f.w), fd=_vNum(f.d);
    if(x===null||z===null||fw===null||fd===null) return;
    const g=_vWorld(x+fw/2,0.02,z+fd/2,fw,0.04,fd,0,transform);
    out.push(_vObj(bid+'.vis.water_'+n,'WATER','SITE',g,'water','SYSTEM_DEFAULT',
      {source_layer:'SITE',source_element_id:f.id,water_kind:k,geometry_source:'model',
       note:'visual water for a represented water feature'}));
    n++; });
  return out; }
/* نباتات بصرية فقط حول المسطح — VISUAL_ONLY وموضعها حتمي لا عشوائي */
function _vLandscapeObjects(bbox,transform,bid,count){
  const out=[]; if(!bbox||count<=0) return out;
  const x0=bbox[0], z0=bbox[2], x1=bbox[3], z1=bbox[5];
  const per=Math.max(1,Math.floor(count/4));
  let n=0;
  for(let side=0;side<4;side++) for(let i=0;i<per;i++){
    const f=(i+1.0)/(per+1.0);
    let x,z;
    if(side===0){ x=x0+(x1-x0)*f; z=z0-4.0; }
    else if(side===1){ x=x0+(x1-x0)*f; z=z1+4.0; }
    else if(side===2){ x=x0-4.0; z=z0+(z1-z0)*f; }
    else { x=x1+4.0; z=z0+(z1-z0)*f; }
    const a=_vAssetFor((n%3)?'tree':'shrub'), aid=a[0], fb=a[1];
    const dm=_VIS_ASSET_INDEX[aid].dimensions_m;
    const g=_vWorld(x,dm.h/2,z,dm.w,dm.h,dm.d,0,transform);
    out.push(_vObj(bid+'.vis.land_'+n,(n%3)?'TREE':'SHRUB','LANDSCAPE',g,'grass',
      'SYSTEM_DEFAULT',
      {semantic:false,visual_only:true,asset_id:aid,asset_fallback:fb,
       geometry_source:'display_fallback',instance_key:'LANDSCAPE|'+aid+'|grass',
       visual_class:VIS_LANDSCAPE_CLASS,
       note:'visual-only landscape placeholder; not project site geometry'}));
    n++; }
  return out; }

/* ------------------------------------------------------------ الديكور - */
const _VIS_DECOR_BY_NAME=[
 ['majlis',['sofa','table','rug','plant']],
 ['living',['sofa','table','tv','rug']],
 ['family',['sofa','table','tv']],
 ['bed',['bed','cabinet','lamp']],
 ['lobby',['sofa','table','plant']],
 ['kitchen',['cabinet','table']],
 ['office',['table','chair','cabinet']],
 ['room',['bed','cabinet']],
 ['reception',['table','chair','plant']],
 ['waiting',['chair','plant']]];
function _vDecorKinds(name){
  const n=String(name===null||name===undefined?'':name).toLowerCase();
  for(let i=0;i<_VIS_DECOR_BY_NAME.length;i++)
    if(n.indexOf(_VIS_DECOR_BY_NAME[i][0])>=0) return _VIS_DECOR_BY_NAME[i][1];
  return []; }
/* ديكور بصريّ حتميّ داخل الفراغات المذكورة — VISUAL_ONLY دائماً */
function _vDecorationObjects(arch,transform,bid,theme,overrides){
  const out=[]; if(!arch) return out;
  const lv={}; (arch.levels||[]).forEach(l=>{lv[l.index]=l;});
  const accent=_vAssign(theme,'accent',overrides,'decoration');
  let n=0;
  (arch.spaces||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(sp=>{
    const kinds=_vDecorKinds(sp.name);
    if(!kinds.length) return;
    const r=sp.rect, base=(lv[sp.level_index]||{}).elevation_m;
    if(base===null||base===undefined||r[2]<=0.6||r[3]<=0.6) return;
    kinds.forEach((kind,k)=>{
      const a=_vAssetFor(kind), aid=a[0], fb=a[1];
      const dm=_VIS_ASSET_INDEX[aid].dimensions_m;
      if(dm.w+0.4>r[2]||dm.d+0.4>r[3]) return;
      const fx=(k+1.0)/(kinds.length+1.0);
      const x=r[0]+r[2]*fx, z=r[1]+r[3]*((k%2===0)?0.3:0.7);
      const g=_vWorld(x,base+dm.h/2,z,dm.w,dm.h,dm.d,0,transform);
      out.push(_vObj(bid+'.vis.deco_'+n,kind.toUpperCase(),'FURNITURE',g,accent[0],accent[1],
        {semantic:false,visual_only:true,asset_id:aid,asset_fallback:fb,
         geometry_source:'display_fallback',instance_key:'FURNITURE|'+aid+'|'+accent[0],
         visual_class:VIS_DECORATION_CLASS,space_id:sp.id,level_index:sp.level_index,
         note:'visual decoration only — never an engineering object, never an occupant, '+
              'never a coverage or load input'}));
      n++; }); });
  return out; }
function _vEntourageObjects(bbox,transform,bid,count){
  const out=[]; if(!bbox||count<=0) return out;
  for(let i=0;i<count;i++){
    const kind=(i%2===0)?'person':'car';
    const a=_vAssetFor(kind), aid=a[0], fb=a[1];
    const dm=_VIS_ASSET_INDEX[aid].dimensions_m;
    const f=(i+1.0)/(count+1.0);
    const x=bbox[0]+(bbox[3]-bbox[0])*f;
    const z=bbox[2]-6.0-((kind==='car')?2.0:0.0);
    const g=_vWorld(x,dm.h/2,z,dm.w,dm.h,dm.d,0,transform);
    out.push(_vObj(bid+'.vis.ent_'+i,kind.toUpperCase(),'ENTOURAGE',g,
      (kind==='person')?'fabric':'metal_steel','SYSTEM_DEFAULT',
      {semantic:false,visual_only:true,asset_id:aid,asset_fallback:fb,
       geometry_source:'display_fallback',instance_key:'ENTOURAGE|'+aid,
       visual_class:VIS_ENTOURAGE_CLASS,
       note:'visual-only entourage; never an occupant and never counted'})); }
  return out; }

/* ------------------------------------------------------------ الإضاءة - */
function _vLights(preset,bbox,mep,transform,bid){
  const p=VIS_LIGHTING_PARAMS[preset];
  const rigNote='presentation light rig — not an MEP luminaire and no illuminance implied';
  const out=[
    {id:bid+'.vis.light_sun',kind:'SUN',visual_only:true,
     elevation_deg:p.sun_elevation_deg,azimuth_deg:p.sun_azimuth_deg,
     intensity:p.sun_intensity,color:p.sun_color,casts_shadow:true,note:rigNote},
    {id:bid+'.vis.light_sky',kind:'SKY',visual_only:true,
     intensity:p.sky_intensity,color:p.ambient_color,casts_shadow:false,note:rigNote},
    {id:bid+'.vis.light_ambient',kind:'AMBIENT',visual_only:true,
     intensity:p.ambient_intensity,color:p.ambient_color,casts_shadow:false,note:rigNote}];
  if(preset==='NIGHT'&&mep){
    let n=0;
    (mep.terminals||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(t=>{
      const tt=String(t.terminal_type||'').toLowerCase();
      if(tt!=='light_fixture'&&tt!=='luminaire') return;
      if(t.x===null||t.x===undefined||t.z===null||t.z===undefined) return;
      const y=_vNum(t.y);
      const w=_vRot(Number(t.x),Number(t.z),Number((transform||{}).rotation_deg)||0,
        Number(((transform||{}).position||{}).x)||0,Number(((transform||{}).position||{}).z)||0);
      out.push({id:bid+'.vis.light_'+n,kind:'INTERIOR_VISUAL',visual_only:true,
        intensity:0.6,color:'#ffe9c4',casts_shadow:false,
        x:_vQ(w[0]),y:_vQ(y===null?2.7:y),z:_vQ(w[1]),at_mep_element:t.id,
        note:"a visual emitter placed at a represented fixture; it asserts nothing about "+
             "that fixture's output or adequacy"});
      n++; }); }
  return out; }

/* --------------------------------------------------------- الكاميرات -- */
function _vBboxOf(objects){
  let lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity], found=false;
  objects.forEach(o=>{
    if(o.visual_only) return;
    const g=o.geometry, c=Math.cos(g.rot_y), s=Math.sin(g.rot_y);
    const rx=Math.abs(g.ex/2*c)+Math.abs(g.ez/2*s);
    const rz=Math.abs(g.ex/2*s)+Math.abs(g.ez/2*c);
    const arr=[[g.cx,rx],[g.cy,g.ey/2],[g.cz,rz]];
    for(let i=0;i<3;i++){ lo[i]=Math.min(lo[i],arr[i][0]-arr[i][1]);
      hi[i]=Math.max(hi[i],arr[i][0]+arr[i][1]); }
    found=true; });
  if(!found) return null;
  return [_vQ(lo[0]),_vQ(lo[1]),_vQ(lo[2]),_vQ(hi[0]),_vQ(hi[1]),_vQ(hi[2])]; }
/* مسافة تُظهر المبنى كاملاً بهامش معلن — محسوبة من حجم النموذج نفسه */
function _vFitDistance(bbox,fovDeg,margin){
  const w=Math.max(bbox[3]-bbox[0],1e-3), h=Math.max(bbox[4]-bbox[1],1e-3),
        d=Math.max(bbox[5]-bbox[2],1e-3);
  const radius=Math.sqrt(w*w+h*h+d*d)/2;
  const half=(Number(fovDeg)*Math.PI/180)/2;
  const dist=radius/Math.max(Math.tan(half),1e-6);
  return Math.max(dist*Number(margin),Number(VIS_CAMERA_DEFAULTS.min_distance_m)); }
function _vCamera(preset,bbox,bid,spaces,transform,roomId){
  const fov=Number(VIS_CAMERA_DEFAULTS.fov_deg), margin=Number(VIS_CAMERA_DEFAULTS.margin);
  const cx=(bbox[0]+bbox[3])/2, cy=(bbox[1]+bbox[4])/2, cz=(bbox[2]+bbox[5])/2;
  const dist=_vFitDistance(bbox,fov,margin);
  let target=[_vQ(cx),_vQ(cy),_vQ(cz)], pos;
  const proj=(preset==='SECTION'||preset==='ELEVATION')?'orthographic':'perspective';
  if(preset==='EXTERIOR_FRONT') pos=[cx,cy+dist*0.25,cz-dist];
  else if(preset==='EXTERIOR_REAR') pos=[cx,cy+dist*0.25,cz+dist];
  else if(preset==='EXTERIOR_CORNER') pos=[cx-dist*0.72,cy+dist*0.45,cz-dist*0.72];
  else if(preset==='TOP') pos=[cx,cy+dist*1.4,cz+0.001];
  else if(preset==='DOLLHOUSE') pos=[cx-dist*0.55,cy+dist*0.9,cz-dist*0.55];
  else if(preset==='PANORAMA_360')
    pos=[cx,bbox[1]+Number(VIS_CAMERA_DEFAULTS.eye_height_m),cz];
  else if(preset==='INTERIOR_ROOM'||preset==='WALKTHROUGH'){
    let sp=null;
    const list=spaces||[];
    for(let i=0;i<list.length;i++){ const s=list[i];
      if(roomId===null||roomId===undefined||s.id===roomId||s.space_id===roomId
         ||s.name===roomId){ sp=s; break; } }
    if(sp===null) pos=[cx,bbox[1]+Number(VIS_CAMERA_DEFAULTS.eye_height_m),cz];
    else {
      const r=sp.rect;
      const rot=Number((transform||{}).rotation_deg)||0;
      const ox=Number(((transform||{}).position||{}).x)||0;
      const oz=Number(((transform||{}).position||{}).z)||0;
      const w=_vRot(r[0]+r[2]*0.5,r[1]+r[3]*0.5,rot,ox,oz);
      const t2=_vRot(r[0]+r[2]*0.5,r[1]+r[3]*0.9,rot,ox,oz);
      const base=sp._elev||0;
      pos=[w[0],base+Number(VIS_CAMERA_DEFAULTS.eye_height_m),w[1]];
      target=[_vQ(t2[0]),_vQ(base+1.5),_vQ(t2[1])]; } }
  else pos=[cx,cy,cz-dist];
  return {id:bid+'.vis.cam_'+preset,preset:preset,projection:proj,
    fov_deg:(proj==='perspective')?_vQ(fov):null,
    position:[_vQ(pos[0]),_vQ(pos[1]),_vQ(pos[2])],target:target,up:[0,1,0],
    near_m:VIS_CAMERA_DEFAULTS.near_m,far_m:VIS_CAMERA_DEFAULTS.far_m,
    margin:_vQ(margin),fit_bbox:bbox.slice(),presentation_state:true,
    note:'camera state is presentation state, never model truth'}; }
/* إعادة تأطير كاميرا على المشهد نفسه — بلا أي إعادة توليد للهندسة */
function visFrameCamera(scene,preset,roomId){
  preset=String(preset||'EXTERIOR_CORNER').toUpperCase();
  if(VIS_CAMERA_PRESETS.indexOf(preset)<0) return null;
  const bbox=scene.bounds; if(!bbox) return null;
  return _vCamera(preset,bbox,scene.building_id,scene.spaces_index||[],scene.transform,
    (roomId===undefined)?null:roomId); }

/* ----------------------------------------------------- القص والدمى --- */
function _vDollhouse(arch,mode,cutLevel){
  if(mode!=='DOLLHOUSE') return null;
  const lv=((arch||{}).levels||[]).filter(l=>l.elevation_m!==null&&l.elevation_m!==undefined)
    .slice().sort((a,b)=>a.index-b.index);
  if(!lv.length) return null;
  const idx=(cutLevel===null||cutLevel===undefined)?lv[lv.length-1].index:cutLevel;
  let top=null;
  lv.forEach(l=>{ if(l.index===idx) top=l; });
  if(top===null) top=lv[lv.length-1];
  return {hide_roof:true,hide_ceilings:true,clip_above_m:_vQ(top.elevation_m+1.2),
    cut_level_index:top.index,reversible:true,
    note:'dollhouse hides the roof and clips enclosure above a stated height; the model '+
         'geometry is untouched and every room keeps its exact position and size'}; }
function _vCutaway(mode,method,plane){
  if(mode!=='CUTAWAY') return null;
  method=String(method||'CLIP_PLANE').toUpperCase();
  if(VIS_CUTAWAY_METHODS.indexOf(method)<0) method='CLIP_PLANE';
  const p=(plane&&typeof plane==='object')?plane:{};
  const nz=_vNum(p.nz);
  return {method:method,
    normal:[_vQ(_vNum(p.nx)||0),_vQ(_vNum(p.ny)||0),_vQ(nz===null?1.0:nz)],
    constant_m:_vQ(_vNum(p.constant)||0),
    level_index:(p.level_index===undefined)?null:p.level_index,reversible:true,
    note:'reversible rendering state only; no model geometry is modified and restoring '+
         'the scene restores the full view exactly'}; }

/* ------------------------------------------------------ المشهد البصري - */
function compileVisualScene(building,buildingId,position,rotationDeg,opts){
  opts=opts||{};
  const bid=buildingId||'bld_0';
  const b=building||{};
  const mode=_vMode(opts.mode), theme=_vTheme(opts.theme);
  const lighting=_vLight(opts.lighting), quality=_vQuality(opts.quality);
  const transform={position:position||{x:0,z:0},rotation_deg:Number(rotationDeg)||0};
  let arch=opts.arch, struct=opts.struct, mep=opts.mep, fls=opts.fls, coord=opts.coord;
  if(arch===null||arch===undefined){
    try{ arch=compileArchitecture(b,bid,position,rotationDeg); }catch(e){ arch=null; } }
  if(struct===null||struct===undefined){
    try{ struct=compileStructure(b,bid,position,rotationDeg,arch); }catch(e){ struct=null; } }
  if(mep===null||mep===undefined){
    try{ mep=compileMep(b,bid,position,rotationDeg,arch,struct); }catch(e){ mep=null; } }
  if(fls===null||fls===undefined){
    try{ fls=compileFls(b,bid,position,rotationDeg,arch,mep); }catch(e){ fls=null; } }

  let active=((opts.layers===null||opts.layers===undefined)
    ?(VIS_MODE_LAYERS[mode]||['ARCHITECTURE']):opts.layers)
    .filter(l=>VIS_LAYERS.indexOf(l)>=0);
  if(VIS_ENGINEERING_MODES.indexOf(mode)>=0)
    ['ARCHITECTURE','STRUCTURE','MEP','FLS'].forEach(l=>{ if(active.indexOf(l)<0) active.push(l); });
  active=Array.from(new Set(active)).sort(_scmp);

  const materials=opts.materials||null;
  let objects=[];
  if(active.indexOf('ARCHITECTURE')>=0){
    objects=objects.concat(_vArchObjects(arch,transform,bid,theme,materials,mode));
    if(mode!=='ENGINEERING')
      objects=objects.concat(_vRoofCap(arch,transform,bid,theme,materials)); }
  if(active.indexOf('STRUCTURE')>=0&&struct)
    objects=objects.concat(_vDisciplineObjects(
      structRenderItems(struct).filter(it=>it.kind!=='GRID_LINE'),
      'STRUCTURE',transform,VIS_ENG_PALETTE.STRUCTURE));
  if(active.indexOf('MEP')>=0&&mep)
    objects=objects.concat(_vDisciplineObjects(mepRenderItems(mep),'MEP',transform,
      VIS_ENG_PALETTE.MEP));
  if(active.indexOf('FLS')>=0&&fls)
    objects=objects.concat(_vFlsObjects(fls,transform));

  const bboxModel=_vBboxOf(objects);
  if(active.indexOf('SITE')>=0){
    objects=objects.concat(_vSiteObjects(b,arch,transform,bid,theme,materials,bboxModel));
    objects=objects.concat(_vWaterObjects(b,transform,bid)); }
  const wantLand=(opts.include_landscape===null||opts.include_landscape===undefined)
    ?(active.indexOf('LANDSCAPE')>=0):opts.include_landscape;
  if(wantLand&&active.indexOf('LANDSCAPE')>=0)
    objects=objects.concat(_vLandscapeObjects(bboxModel,transform,bid,
      Math.trunc(Number(opts.landscape_count===undefined?12:opts.landscape_count)||0)));
  if(opts.include_decoration&&active.indexOf('FURNITURE')>=0)
    objects=objects.concat(_vDecorationObjects(arch,transform,bid,theme,materials));
  if(opts.include_entourage&&active.indexOf('ENTOURAGE')>=0)
    objects=objects.concat(_vEntourageObjects(bboxModel,transform,bid,
      Math.trunc(Number(opts.entourage_count)||0)));

  objects.sort((a,b2)=>_scmp(String(a.layer),String(b2.layer))
    ||_scmp(String(a.kind),String(b2.kind))||_scmp(String(a.id),String(b2.id)));

  const used=Array.from(new Set(objects.map(o=>o.material))).sort(_scmp);
  const mats=[];
  used.forEach(mid=>{ const m=visMaterial(mid); if(!m) return;
    m.provenance=Array.from(new Set(objects.filter(o=>o.material===mid)
      .map(o=>o.material_provenance))).sort(_scmp);
    mats.push(m); });

  const bbox=bboxModel||_vBboxOf(objects)||[0,0,0,1,1,1];
  const lvmap={}; ((arch||{}).levels||[]).forEach(l=>{lvmap[l.index]=l;});
  const spaces=((arch||{}).spaces||[]).slice()
    .sort((a,b2)=>_scmp(String(a.id),String(b2.id))).map(s=>({
      id:s.id,space_id:s.space_id,name:s.name,rect:s.rect.map(_vQ),
      level_index:s.level_index,area_m2:_vQ(s.area_m2),
      _elev:_vQ((lvmap[s.level_index]||{}).elevation_m||0)}));

  const roomId=(opts.room_id===undefined)?null:opts.room_id;
  const cams=VIS_CAMERA_PRESETS.map(p=>_vCamera(p,bbox,bid,spaces,transform,
    (p==='INTERIOR_ROOM'||p==='WALKTHROUGH')?roomId:null));
  const lights=_vLights(lighting,bbox,mep,transform,bid);
  const lp=VIS_LIGHTING_PARAMS[lighting], qp=VIS_QUALITY_PARAMS[quality];
  let mh=null;
  try{ mh=modelHash(b,'building',bid); }catch(e){ mh=null; }
  let sc=_vNum(opts.scale===undefined?1.0:opts.scale);
  sc=(sc===null||sc<=0)?1.0:sc;
  const camIn=String(opts.camera||'').toUpperCase();
  const cutaway=opts.cutaway;
  const cutLevel=(opts.cut_level===undefined)?null:opts.cut_level;

  const scene={
    schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,
    building_id:bid,model_hash:mh,
    scene_id:mh?('vscene_'+mh.slice(0,16)+'_'+mode):null,
    created_at:(opts.at===undefined)?null:opts.at,mode:mode,transform:transform,
    bounds:bbox,objects:objects,materials:mats,lights:lights,cameras:cams,
    active_camera:(VIS_CAMERA_PRESETS.indexOf(camIn)>=0)?camIn
      :((mode==='DOLLHOUSE')?'DOLLHOUSE':'EXTERIOR_CORNER'),
    environment:{background:lp.background,exposure:lp.exposure,
      tone_mapping:qp.tone_mapping,environment_quality:qp.environment,
      ground_plane:objects.some(o=>o.kind==='GROUND'),
      note:'sky, background and ground plane are appearance only'},
    presentation:{theme:theme,lighting_preset:lighting,quality:quality,
      quality_params:JSON.parse(JSON.stringify(qp)),layers:active,
      layer_visibility:(function(){const v={};
        VIS_LAYERS.forEach(l=>{v[l]=active.indexOf(l)>=0;}); return v;})(),
      clash_overlay:!!opts.clash_overlay
        &&ACS_VISUAL_SPEC.clash_overlay_modes.indexOf(mode)>=0,
      dollhouse:_vDollhouse(arch,mode,cutLevel),
      cutaway:_vCutaway(mode,(cutaway&&typeof cutaway==='object')?cutaway.method:cutaway,
        (cutaway&&typeof cutaway==='object')?cutaway:null),
      scale:_vQ(sc),scale_is_explicit:sc!==1.0,
      decoration_included:!!opts.include_decoration,
      entourage_included:!!opts.include_entourage,
      note:'presentation state only; none of it is model truth and none of it enters a '+
           'revision hash'},
    counts:{},
    meta:{note:ACS_VISUAL_SPEC.note,derivation:ACS_VISUAL_SPEC.derivation_note,
      authority:ACS_VISUAL_SPEC.authority_note,material_class:VIS_MATERIAL_CLASS,
      compliance:'NOT_EVALUATED'},
    spaces_index:spaces};
  if(scene.presentation.clash_overlay&&(coord===null||coord===undefined)){
    try{ coord=compileCoordination(b,bid,position,rotationDeg,arch,struct,mep,fls,null); }
    catch(e){ coord=null; } }
  if(scene.presentation.clash_overlay&&coord)
    scene.clash_overlay=(coord.clashes||[]).filter(c=>c.geometry).map(c=>({
      clash_id:c.id,type:c.type,severity:c.severity,
      elements:[c.element_a,c.element_b],
      intersection:(c.geometry||{}).intersection,visual_only:true,
      note:'coordination overlay drawn on the engineering view; it is never hidden to '+
           'make an image attractive and never baked into geometry'}));
  /* الأوضاع المسقطة تحمل الرسم المشتقّ من الهندسة نفسها — لا نموذج ثانٍ */
  if(mode==='FLOOR_PLAN_2D'){
    let li=cutLevel;
    if(li===null||li===undefined){
      const idxs=((arch||{}).levels||[]).map(l=>l.index);
      li=idxs.length?Math.min.apply(null,idxs):0; }
    scene.drawing=visFloorPlan(arch,li,
      (cutaway&&typeof cutaway==='object')?cutaway.style:null,bid);
  } else if(mode==='SECTION'){
    const ax=(cutaway&&typeof cutaway==='object')?cutaway.axis:null;
    const po=(cutaway&&typeof cutaway==='object')?cutaway.position_m:null;
    scene.drawing=visSection(arch,ax||'x',(po===undefined)?null:po,bid);
  } else if(mode==='ELEVATION'){
    const fc=(cutaway&&typeof cutaway==='object')?cutaway.face:null;
    scene.drawing=visElevation(arch,fc||'NORTH',bid);
  } else scene.drawing=null;
  if(VIS_ORTHO_MODES.indexOf(mode)>=0)
    scene.active_camera=(mode==='SECTION')?'SECTION'
      :((mode==='ELEVATION')?'ELEVATION':'TOP');
  scene.counts=_vCounts(scene);
  scene.summary=visSummary(scene);
  return scene; }

function _vCounts(scene){
  const objs=scene.objects||[];
  const byLayer={}, byKind={};
  objs.forEach(o=>{ byLayer[o.layer]=(byLayer[o.layer]||0)+1;
    byKind[o.kind]=(byKind[o.kind]||0)+1; });
  return {objects:objs.length,
    semantic_objects:objs.filter(o=>o.semantic).length,
    visual_only_objects:objs.filter(o=>o.visual_only).length,
    decoration_objects:objs.filter(o=>o.visual_class===VIS_DECORATION_CLASS).length,
    entourage_objects:objs.filter(o=>o.visual_class===VIS_ENTOURAGE_CLASS).length,
    landscape_objects:objs.filter(o=>o.visual_class===VIS_LANDSCAPE_CLASS).length,
    by_layer:byLayer,by_kind:byKind,
    materials:(scene.materials||[]).length,lights:(scene.lights||[]).length,
    cameras:(scene.cameras||[]).length,
    display_fallback_objects:objs.filter(o=>o.geometry_source==='display_fallback').length}; }

/* ------------------------------------------- المسقط ثنائي الأبعاد ----- */
function visFloorPlan(arch,levelIndex,style,buildingId){
  style=_vStyle(style);
  levelIndex=(levelIndex===null||levelIndex===undefined)?0:levelIndex;
  const out={schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,kind:'FLOOR_PLAN_2D',
    building_id:buildingId||'bld_0',level_index:levelIndex,style:style,
    walls:[],openings:[],spaces:[],stairs:[],fixtures:[],dimensions:[],extent:null,
    note:'a derived drawing projected from the same architectural geometry as the 3D view; '+
         'it makes no CAD-grade claim'};
  if(!arch) return out;
  let lv=null;
  (arch.levels||[]).forEach(l=>{ if(l.index===levelIndex) lv=l; });
  if(lv===null){ out.level_exists=false; return out; }
  out.level_exists=true; out.level_id=lv.id; out.level_name=lv.name;
  (arch.walls||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(w=>{
    if(w.level_index!==levelIndex) return;
    const tv=_vVal(w.thickness_m);
    out.walls.push({id:w.id,x1:_vQ(w.start.x),z1:_vQ(w.start.z),x2:_vQ(w.end.x),
      z2:_vQ(w.end.z),thickness_m:tv[0]===null?null:_vQ(tv[0]),thickness_source:tv[1],
      length_m:_vQ(w.length_m),exposure:w.exposure}); });
  (arch.openings||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(o=>{
    if(o.level_index!==levelIndex) return;
    const wv=_vVal(o.width_m), wdt=wv[0]===null?0:wv[0];
    let x1,z1,x2,z2;
    if(o.axis==='x'){ x1=o.u_center-wdt/2; z1=o.fixed; x2=o.u_center+wdt/2; z2=o.fixed; }
    else { x1=o.fixed; z1=o.u_center-wdt/2; x2=o.fixed; z2=o.u_center+wdt/2; }
    out.openings.push({id:o.id,type:o.type,x1:_vQ(x1),z1:_vQ(z1),x2:_vQ(x2),z2:_vQ(z2),
      width_m:wv[0]===null?null:_vQ(wv[0]),width_source:wv[1],
      host_wall_id:(o.host_wall_id===undefined)?null:o.host_wall_id,
      swing_direction:(o.swing_direction===undefined)?null:o.swing_direction,
      swing_status:(o.swing_status===undefined)?null:o.swing_status}); });
  (arch.spaces||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(s=>{
    if(s.level_index!==levelIndex) return;
    const r=s.rect;
    out.spaces.push({id:s.id,space_id:s.space_id,name:s.name,
      x:_vQ(r[0]),z:_vQ(r[1]),w:_vQ(r[2]),d:_vQ(r[3]),area_m2:_vQ(s.area_m2),
      boundary_basis:s.boundary_basis,label_x:_vQ(r[0]+r[2]/2),label_z:_vQ(r[1]+r[3]/2)});
    out.dimensions.push({subject:s.id,kind:'space_width',value_m:_vQ(r[2]),source:'model'});
    out.dimensions.push({subject:s.id,kind:'space_depth',value_m:_vQ(r[3]),source:'model'}); });
  (arch.cores||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(c=>{
    if((c.served_levels||[]).indexOf(levelIndex)<0) return;
    const fw=_vVal(c.footprint_w_m), fd=_vVal(c.footprint_d_m);
    out.stairs.push({id:c.id,type:c.type,x:_vQ(c.x),z:_vQ(c.z),
      w:fw[0]===null?null:_vQ(fw[0]),d:fd[0]===null?null:_vQ(fd[0]),
      w_source:fw[1],d_source:fd[1]}); });
  out.walls.forEach(w=>{ out.dimensions.push({subject:w.id,kind:'wall_length',
    value_m:w.length_m,source:'model'}); });
  out.openings.forEach(o=>{ out.dimensions.push({subject:o.id,kind:'opening_width',
    value_m:o.width_m,source:(o.width_source==='model')?'model':'unknown'}); });
  const xs=[], zs=[];
  out.walls.forEach(w=>{ xs.push(w.x1,w.x2); zs.push(w.z1,w.z2); });
  if(xs.length&&zs.length) out.extent=[_vQ(Math.min.apply(null,xs)),
    _vQ(Math.min.apply(null,zs)),_vQ(Math.max.apply(null,xs)),_vQ(Math.max.apply(null,zs))];
  out.dimensions.sort((a,b)=>_scmp(String(a.kind),String(b.kind))
    ||_scmp(String(a.subject),String(b.subject)));
  out.counts={walls:out.walls.length,openings:out.openings.length,spaces:out.spaces.length,
    stairs:out.stairs.length,dimensions:out.dimensions.length,
    unknown_dimensions:out.dimensions.filter(d=>d.source!=='model').length};
  return out; }

/* ------------------------------------------------------------ القطاع -- */
function visSection(arch,axis,positionM,buildingId){
  axis=String(axis||'x').toLowerCase();
  if(VIS_SECTION_AXES.indexOf(axis)<0) axis='x';
  const out={schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,kind:'SECTION',
    building_id:buildingId||'bld_0',axis:axis,position_m:null,
    levels:[],slabs:[],walls:[],openings:[],stairs:[],
    note:'an orthographic cut of the same architectural geometry; no structural or code '+
         'interpretation is made'};
  if(!arch) return out;
  const walls=arch.walls||[];
  if(positionM===null||positionM===undefined){
    const outs=(arch.slabs||[]).filter(s=>s.outline).map(s=>s.outline);
    if(outs.length){
      const lo=Math.min.apply(null,outs.map(o=>(axis==='x')?o[1]:o[0]));
      const hi=Math.max.apply(null,outs.map(o=>(axis==='x')?(o[1]+o[3]):(o[0]+o[2])));
      positionM=(lo+hi)/2; }
    else positionM=0; }
  const pos=Number(positionM);
  out.position_m=_vQ(pos);
  (arch.levels||[]).slice().sort((a,b)=>a.index-b.index).forEach(l=>{
    out.levels.push({id:l.id,index:l.index,name:l.name,
      elevation_m:(l.elevation_m===null||l.elevation_m===undefined)?null:_vQ(l.elevation_m),
      elevation_source:l.elevation_source}); });
  const lv={}; (arch.levels||[]).forEach(l=>{lv[l.index]=l;});
  (arch.slabs||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(s=>{
    const o=s.outline;
    if(!o||s.elevation_m===null||s.elevation_m===undefined) return;
    const lo=(axis==='x')?o[0]:o[1];
    const hi=lo+((axis==='x')?o[2]:o[3]);
    const cutLo=(axis==='x')?o[1]:o[0];
    const cutHi=cutLo+((axis==='x')?o[3]:o[2]);
    if(!(cutLo-_VIS_EPS<=pos&&pos<=cutHi+_VIS_EPS)) return;
    const tv=_vVal(s.thickness_m);
    out.slabs.push({id:s.id,level_index:s.level_index,u0:_vQ(lo),u1:_vQ(hi),
      y0:_vQ(s.elevation_m-(tv[0]||0)),y1:_vQ(s.elevation_m),
      thickness_m:tv[0]===null?null:_vQ(tv[0]),thickness_source:tv[1]}); });
  walls.slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(w=>{
    const hv=_vVal(w.height_m), t=_vVal(w.thickness_m)[0]||0.2;
    const base=(lv[w.level_index]||{}).elevation_m;
    if(hv[0]===null||base===null||base===undefined) return;
    let u0,u1;
    if(w.axis===axis){
      if(Math.abs(w.fixed-pos)>t/2+_VIS_EPS) return;
      u0=w.u0; u1=w.u1; }
    else {
      if(!(Math.min(w.u0,w.u1)-_VIS_EPS<=pos&&pos<=Math.max(w.u0,w.u1)+_VIS_EPS)) return;
      u0=w.fixed-t/2; u1=w.fixed+t/2; }
    out.walls.push({id:w.id,level_index:w.level_index,u0:_vQ(u0),u1:_vQ(u1),
      y0:_vQ(base),y1:_vQ(base+hv[0]),cut:true,height_source:hv[1]}); });
  (arch.openings||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(o=>{
    const wv=_vVal(o.width_m), hv=_vVal(o.height_m);
    const base=(lv[o.level_index]||{}).elevation_m;
    if(wv[0]===null||hv[0]===null||base===null||base===undefined) return;
    let u0,u1;
    if(o.axis===axis){
      if(Math.abs(o.fixed-pos)>0.35) return;
      u0=o.u_center-wv[0]/2; u1=o.u_center+wv[0]/2; }
    else {
      if(!(o.u_center-wv[0]/2-_VIS_EPS<=pos&&pos<=o.u_center+wv[0]/2+_VIS_EPS)) return;
      u0=o.fixed-0.1; u1=o.fixed+0.1; }
    let sill=(o.type==='WINDOW')?_vVal(o.sill_m)[0]:0;
    sill=(sill===null||sill===undefined)?0:sill;
    out.openings.push({id:o.id,type:o.type,u0:_vQ(u0),u1:_vQ(u1),
      y0:_vQ(base+sill),y1:_vQ(base+sill+hv[0]),
      width_source:wv[1],height_source:hv[1]}); });
  (arch.cores||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(c=>{
    const fw=_vVal(c.footprint_w_m), fd=_vVal(c.footprint_d_m);
    const served=c.served_levels||[];
    if(fw[0]===null||fd[0]===null||!served.length) return;
    const half=((axis==='x')?fd[0]:fw[0])/2;
    const centre=(axis==='x')?c.z:c.x;
    if(Math.abs(centre-pos)>half+_VIS_EPS) return;
    const base=(lv[Math.min.apply(null,served)]||{}).elevation_m;
    const top=(lv[Math.max.apply(null,served)]||{}).elevation_m;
    if(base===null||base===undefined||top===null||top===undefined) return;
    const u=(axis==='x')?c.x:c.z;
    const halfU=((axis==='x')?fw[0]:fd[0])/2;
    out.stairs.push({id:c.id,type:c.type,u0:_vQ(u-halfU),u1:_vQ(u+halfU),
      y0:_vQ(base),y1:_vQ(top)}); });
  out.counts={levels:out.levels.length,slabs:out.slabs.length,walls:out.walls.length,
    openings:out.openings.length,stairs:out.stairs.length};
  return out; }

/* ---------------------------------------------------------- الواجهة -- */
const _VIS_FACE_AXIS={NORTH:['z','min','x'],SOUTH:['z','max','x'],
  WEST:['x','min','z'],EAST:['x','max','z']};
function visElevation(arch,face,buildingId){
  face=String(face||'NORTH').toUpperCase();
  if(VIS_ELEVATION_FACES.indexOf(face)<0) face='NORTH';
  const out={schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,kind:'ELEVATION',
    building_id:buildingId||'bld_0',face:face,walls:[],openings:[],levels:[],outline:null,
    note:'the real envelope and its real openings are projected; no opening is ever added '+
         'to balance a facade'};
  if(!arch) return out;
  const env=arch.envelope||{};
  const ext={}; (env.exterior_walls||[]).forEach(id=>{ext[id]=true;});
  const lv={}; (arch.levels||[]).forEach(l=>{lv[l.index]=l;});
  const axis=_VIS_FACE_AXIS[face][0], side=_VIS_FACE_AXIS[face][1];
  let cand=(arch.walls||[]).filter(w=>ext[w.id]&&w.axis!==axis);
  if(!cand.length) cand=(arch.walls||[]).filter(w=>w.axis!==axis);
  if(!cand.length) return out;
  const fixedVals=cand.map(w=>w.fixed);
  const target=(side==='min')?Math.min.apply(null,fixedVals):Math.max.apply(null,fixedVals);
  const picked=cand.filter(w=>Math.abs(w.fixed-target)<=0.6);
  const ids={}; picked.forEach(w=>{ids[w.id]=true;});
  (arch.levels||[]).slice().sort((a,b)=>a.index-b.index).forEach(l=>{
    out.levels.push({id:l.id,index:l.index,
      elevation_m:(l.elevation_m===null||l.elevation_m===undefined)?null
        :_vQ(l.elevation_m)}); });
  const ys=[];
  picked.slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(w=>{
    const hv=_vVal(w.height_m);
    const base=(lv[w.level_index]||{}).elevation_m;
    if(hv[0]===null||base===null||base===undefined) return;
    out.walls.push({id:w.id,level_index:w.level_index,u0:_vQ(w.u0),u1:_vQ(w.u1),
      y0:_vQ(base),y1:_vQ(base+hv[0]),height_source:hv[1]});
    ys.push(base,base+hv[0]); });
  (arch.openings||[]).slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).forEach(o=>{
    if(!ids[o.host_wall_id]) return;
    const wv=_vVal(o.width_m), hv=_vVal(o.height_m);
    const base=(lv[o.level_index]||{}).elevation_m;
    if(wv[0]===null||hv[0]===null||base===null||base===undefined) return;
    let sill=(o.type==='WINDOW')?_vVal(o.sill_m)[0]:0;
    sill=(sill===null||sill===undefined)?0:sill;
    out.openings.push({id:o.id,type:o.type,u0:_vQ(o.u_center-wv[0]/2),
      u1:_vQ(o.u_center+wv[0]/2),y0:_vQ(base+sill),y1:_vQ(base+sill+hv[0]),
      host_wall_id:o.host_wall_id,width_source:wv[1],height_source:hv[1]}); });
  const us=[]; out.walls.forEach(w=>{us.push(w.u0,w.u1);});
  if(us.length&&ys.length) out.outline=[_vQ(Math.min.apply(null,us)),
    _vQ(Math.min.apply(null,ys)),_vQ(Math.max.apply(null,us)),_vQ(Math.max.apply(null,ys))];
  out.counts={walls:out.walls.length,openings:out.openings.length,levels:out.levels.length};
  return out; }

/* ------------------------------- الأداء: التكرار والتفاصيل ------------ */
function visInstancingPlan(scene){
  const groups={};
  (scene.objects||[]).forEach(o=>{
    if(!o.visual_only||!o.instance_key) return;
    if(!groups[o.instance_key]) groups[o.instance_key]={instance_key:o.instance_key,
      asset_id:o.asset_id,material:o.material,count:0,object_ids:[]};
    groups[o.instance_key].count++; groups[o.instance_key].object_ids.push(o.id); });
  const out=Object.keys(groups).map(k=>groups[k]).filter(g=>g.count>1)
    .map(g=>({instance_key:g.instance_key,asset_id:g.asset_id,material:g.material,
      count:g.count,object_ids:g.object_ids.slice().sort(_scmp)}));
  out.sort((a,b)=>_scmp(String(a.instance_key),String(b.instance_key)));
  return {groups:out,instanced_objects:out.reduce((n,g)=>n+g.count,0),
    modelled_objects_merged:0,
    note:'only visual-only objects are instanced; merging a modelled element would '+
         'destroy per-element selection and traceability'}; }
function visLodPlan(scene,budget){
  const objs=scene.objects||[];
  const q=(scene.presentation||{}).quality_params||{};
  const cap=Math.trunc((budget===null||budget===undefined)
    ?(q.max_visual_objects||12000):budget);
  const eng=VIS_ENGINEERING_MODES.indexOf(scene.mode)>=0;
  const visual=objs.filter(o=>o.visual_only), modelled=objs.filter(o=>!o.visual_only);
  const over=Math.max(0,objs.length-cap);
  const drop={};
  if(over>0) visual.slice().sort((a,b)=>_scmp(String(a.id),String(b.id))).reverse()
    .slice(0,over).forEach(o=>{drop[o.id]=true;});
  let dropped=0, simplified=0;
  const plan=[];
  objs.forEach(o=>{
    if(drop[o.id]){ plan.push({id:o.id,lod:'MASSING',emitted:false,
      reason:'visual-only object beyond the quality budget'}); dropped++; }
    else if(o.visual_only&&objs.length>cap*0.8){ plan.push({id:o.id,lod:'SIMPLIFIED',
      emitted:true,reason:'visual-only object simplified near the budget'}); simplified++; }
    else plan.push({id:o.id,lod:'FULL',emitted:true,reason:null}); });
  plan.sort((a,b)=>_scmp(String(a.id),String(b.id)));
  return {budget:cap,objects:objs.length,modelled_objects:modelled.length,
    visual_only_objects:visual.length,dropped_visual_only:dropped,
    simplified_visual_only:simplified,dropped_modelled:0,engineering_mode:!!eng,plan:plan,
    note:'a modelled architectural, structural, MEP or fire element is never removed by '+
         'LOD; only visual-only detail degrades'}; }

/* ----------------------------------------------- اللقطة وبياناتها ---- */
function visSnapshotRequest(scene,opts){
  opts=opts||{};
  let w=Math.trunc(_vNum(opts.width)||VIS_SNAPSHOT_DEFAULTS.width);
  let h=Math.trunc(_vNum(opts.height)||VIS_SNAPSHOT_DEFAULTS.height);
  const issues=[];
  if(w<=0||h<=0){ issues.push('SNAPSHOT_DIMENSIONS_INVALID');
    w=VIS_SNAPSHOT_DEFAULTS.width; h=VIS_SNAPSHOT_DEFAULTS.height; }
  if(w*h>VIS_SNAPSHOT_MAX_PX){ issues.push('SNAPSHOT_EXCEEDS_MAX_PIXELS');
    const sc=Math.sqrt(VIS_SNAPSHOT_MAX_PX/(w*h));
    w=Math.max(1,Math.trunc(w*sc)); h=Math.max(1,Math.trunc(h*sc)); }
  let f=String(opts.format||VIS_SNAPSHOT_DEFAULTS.format).toUpperCase();
  if(VIS_SNAPSHOT_FORMATS.indexOf(f)<0){ issues.push('SNAPSHOT_FORMAT_UNSUPPORTED');
    f=VIS_SNAPSHOT_DEFAULTS.format; }
  let cam=String(opts.camera||scene.active_camera||'EXTERIOR_CORNER').toUpperCase();
  if(VIS_CAMERA_PRESETS.indexOf(cam)<0){ issues.push('SNAPSHOT_CAMERA_UNKNOWN');
    cam='EXTERIOR_CORNER'; }
  let q=_vNum(opts.quality);
  q=(q===null)?VIS_SNAPSHOT_DEFAULTS.quality:Math.min(Math.max(q,0.1),1.0);
  return {width:w,height:h,format:f,quality:_vQ(q),
    transparent:!!((opts.transparent===null||opts.transparent===undefined)
      ?VIS_SNAPSHOT_DEFAULTS.transparent:opts.transparent),
    camera:cam,mode:scene.mode,issues:issues.sort(_scmp),
    note:'a snapshot is an image of the deterministic scene; it carries the model hash it '+
         'was produced from'}; }
function visRenderMetadata(scene,request,kind,at,ai){
  kind=String(kind||'DETERMINISTIC_RENDER').toUpperCase();
  if(VIS_RENDER_KINDS.indexOf(kind)<0) kind='DETERMINISTIC_RENDER';
  const req=request||visSnapshotRequest(scene);
  const pres=scene.presentation||{};
  const body={model_hash:scene.model_hash,building_id:scene.building_id,
    scene_id:scene.scene_id,visual_mode:scene.mode,camera:req.camera,
    theme:pres.theme,material_preset:pres.theme,lighting_preset:pres.lighting_preset,
    quality:pres.quality,width:req.width,height:req.height,format:req.format,kind:kind,
    compiler_version:VIS_COMPILER_VERSION};
  const meta=JSON.parse(JSON.stringify(body));
  meta.render_id='vrender_'+_vSha16(body);
  meta.created_at=(at===undefined)?null:at;
  meta.authority=VIS_RENDER_AUTHORITY[kind];
  meta.is_engineering_model=(kind==='DETERMINISTIC_RENDER');
  meta.ai_enhanced=(kind==='AI_ENHANCED_VISUALISATION');
  if(meta.ai_enhanced){ meta.ai=ai||{};
    meta.note='AI-enhanced VISUALISATION — appearance only. It is not the engineering '+
              'model, it is not as-built, and no geometry in it is authoritative'; }
  else meta.note='deterministic render of the compiled geometry; it depicts the model at '+
                 'the stated model hash and nothing else';
  return meta; }
function visCheckRenderCurrency(renderMeta,building,buildingId){
  let now;
  try{ now=modelHash(building||{},'building',buildingId||'bld_0'); }
  catch(e){ return {status:'UNVERIFIABLE',presented_as_current:false,
    reason:'the model hash could not be computed'}; }
  const stored=(renderMeta||{}).model_hash;
  if(stored===null||stored===undefined)
    return {status:'UNVERIFIABLE',presented_as_current:false,
      reason:'the render carries no model hash'};
  if(stored!==now)
    return {status:'STALE_MODEL_CHANGED',stored_hash:stored,current_hash:now,
      presented_as_current:false,
      reason:'the building changed after this render; the image remains historical and is '+
             'not relabelled current'};
  return {status:'CURRENT',stored_hash:stored,current_hash:now,presented_as_current:true}; }

/* ------------------------------------- ممرات التحكّم والذكاء ---------- */
function visControlBuffers(scene,kinds){
  const want=(kinds||VIS_CONTROL_BUFFERS).filter(k=>VIS_CONTROL_BUFFERS.indexOf(k)>=0);
  const objs=scene.objects||[];
  const ids=objs.filter(o=>!o.visual_only).map(o=>o.id);
  const rooms=Array.from(new Set(objs.filter(o=>o.space_id).map(o=>o.space_id))).sort(_scmp);
  const out=[];
  want.slice().sort(_scmp).forEach(k=>{
    const entry={kind:k,deterministic:true,from_model:true,source_scene:scene.scene_id,
      note:'a deterministic pass over the compiled geometry'};
    if(k==='object_id'){ entry.ids=ids.slice().sort(_scmp); entry.count=ids.length; }
    else if(k==='room_id'){ entry.ids=rooms; entry.count=rooms.length; }
    else if(k==='semantic_mask'){
      entry.classes=Array.from(new Set(objs.filter(o=>!o.visual_only).map(o=>o.kind)))
        .sort(_scmp);
      entry.count=entry.classes.length; }
    else entry.count=objs.length;
    out.push(entry); });
  return {scene_id:scene.scene_id,model_hash:scene.model_hash,buffers:out,
    available:want.slice().sort(_scmp),note:ACS_VISUAL_SPEC.control_buffer_note}; }
/* بصمة السمات التي يُمنع على الذكاء الاصطناعي تغييرها — أساس كشف الانحراف */
function visGeometrySignature(scene,arch){
  const objs=scene.objects||[];
  const b=scene.bounds||[0,0,0,0,0,0];
  let lvl=new Set();
  objs.forEach(o=>{ if(o.level_index!==null&&o.level_index!==undefined) lvl.add(o.level_index); });
  if(arch) lvl=new Set((arch.levels||[]).map(l=>l.index));
  let rooms=new Set(objs.filter(o=>o.space_id).map(o=>o.space_id)).size;
  if(arch) rooms=(arch.spaces||[]).length;
  return {door_count:objs.filter(o=>o.kind==='DOOR').length,
    window_count:objs.filter(o=>o.kind==='WINDOW').length,
    wall_count:objs.filter(o=>o.kind==='WALL').length,
    stair_count:objs.filter(o=>o.kind==='STAIR').length,
    floor_count:lvl.size,room_count:rooms,
    footprint:[_vQ(b[0]),_vQ(b[2]),_vQ(b[3]),_vQ(b[5])],
    model_hash:scene.model_hash}; }
/* واجهة تحسين بصريّ. لا تولّد صورة ولا تتّصل بشبكة ولا تملك أي مسار كتابة */
function visAiEnhancementRequest(scene,prompt,buffers,strength,arch){
  let st=_vNum(strength===undefined?0.35:strength);
  st=(st===null)?0.35:Math.min(Math.max(st,0),1);
  const cb=visControlBuffers(scene,buffers);
  /* كل ممرّ مطلوب يسافر مع واصفه الحتميّ، لا باسمه وحده. لا بكسل يُولَّد هنا */
  const descriptors={};
  cb.buffers.forEach(b=>{ descriptors[b.kind]=JSON.parse(JSON.stringify(b)); });
  return {stage_pipeline:VIS_AI_STAGES.slice(),scene_id:scene.scene_id,
    model_hash:scene.model_hash,building_id:scene.building_id,
    base_render_required:true,
    requested_control_buffers:cb.available.slice(),
    control_buffers:descriptors,
    geometry_signature:visGeometrySignature(scene,arch),
    prompt:(prompt===null||prompt===undefined)?null:String(prompt),
    strength:_vQ(st),may_change:VIS_AI_MAY_CHANGE.slice(),
    may_not_change:VIS_AI_MAY_NOT_CHANGE.slice(),
    writes_to_model:false,generator_shipped:false,network_call:false,
    authority:VIS_RENDER_AUTHORITY.AI_ENHANCED_VISUALISATION,
    note:ACS_VISUAL_SPEC.ai_note}; }
/* أسماء الممرّات المطلوبة سواء وردت كخريطة واصفات أو كقائمة أسماء */
function _vRequestedBuffers(request){
  const r=request||{};
  if(Array.isArray(r.requested_control_buffers)) return r.requested_control_buffers.slice();
  const cb=r.control_buffers;
  if(Array.isArray(cb)) return cb.slice();
  if(cb&&typeof cb==='object') return Object.keys(cb).sort(_scmp);
  return []; }
/* يقارن ما تدّعيه صورة محسّنة بما ينصّ عليه النموذج. لا يكتب في النموذج أبداً */
function visCheckConsistency(request,reported,toleranceM){
  const sig=(request||{}).geometry_signature||{};
  const rep=reported||{};
  const tol=(toleranceM===null||toleranceM===undefined)?0.5:Number(toleranceM);
  const findings=[];
  const add=(code,subject,expected,observed)=>findings.push({code:code,
    severity:VIS_DRIFT_SEVERITY[code],subject:subject,expected:expected,observed:observed,
    writes_to_model:false,
    note:'the image disagrees with the model it claims to depict; the model is never '+
         'rewritten and the image is never accepted as geometry'});
  [['door_count','doors'],['window_count','windows'],['floor_count','levels'],
   ['room_count','rooms'],['stair_count','stairs'],['wall_count','walls']].forEach(pair=>{
    const key=pair[0], subject=pair[1];
    if(!Object.prototype.hasOwnProperty.call(rep,key)) return;
    const exp=sig[key], obs=rep[key];
    if(exp===null||exp===undefined||obs===null||obs===undefined||exp===obs) return;
    add((key==='floor_count')?'VISUAL_LEVEL_COUNT_MISMATCH'
      :'VISUAL_FEATURE_COUNT_MISMATCH',subject,exp,obs); });
  if(Object.prototype.hasOwnProperty.call(rep,'footprint')&&sig.footprint){
    const exp=sig.footprint, obs=rep.footprint;
    let bad=false;
    if(!Array.isArray(obs)||obs.length!==4) bad=true;
    else for(let i=0;i<4;i++){ const o=Number(obs[i]);
      if(!isFinite(o)||Math.abs(o-Number(exp[i]))>tol){ bad=true; break; } }
    if(bad) add('VISUAL_FOOTPRINT_MISMATCH','footprint',exp,obs); }
  if(Object.prototype.hasOwnProperty.call(rep,'model_hash')&&sig.model_hash
     &&rep.model_hash!==sig.model_hash)
    add('VISUAL_SOURCE_HASH_MISMATCH','model_hash',sig.model_hash,rep.model_hash);
  if(!_vRequestedBuffers(request).length)
    add('VISUAL_CONTROL_BUFFER_MISSING','control_buffers','>=1',0);
  /* طلب بلا بصمة هندسية ليس طلباً مقيَّداً: يُرفض ولا يُمرَّر بصمت */
  if(!Object.keys(sig).length)
    add('VISUAL_SIGNATURE_MISSING','geometry_signature',
      'a geometry signature is required to constrain an AI enhancement',null);
  findings.sort((a,b)=>(VIS_DRIFT_SEVERITIES.indexOf(a.severity)
    -VIS_DRIFT_SEVERITIES.indexOf(b.severity))||_scmp(String(a.code),String(b.code))
    ||_scmp(String(a.subject),String(b.subject)));
  if(findings.length) findings.unshift({code:'VISUAL_GEOMETRY_DRIFT',
    severity:VIS_DRIFT_SEVERITY.VISUAL_GEOMETRY_DRIFT,subject:'scene',
    expected:'image matches the model',
    observed:findings.length+' inconsistency(ies)',writes_to_model:false,
    note:'major layout features in the image are inconsistent with the model; the image '+
         'is not authoritative geometry'});
  return {drift:findings.length>0,findings:findings,model_modified:false,
    image_accepted_as_geometry:false,
    authority:VIS_RENDER_AUTHORITY.AI_ENHANCED_VISUALISATION,
    note:ACS_VISUAL_SPEC.drift_note}; }

/* ------------------------------------------------------ تصدير وخدمات - */
function visPresentationBlock(scene){
  const pres=scene.presentation||{};
  const out={};
  out[VIS_PRESENTATION_KEY]={schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,
    building_id:scene.building_id,model_hash:scene.model_hash,mode:scene.mode,
    theme:pres.theme,lighting_preset:pres.lighting_preset,quality:pres.quality,
    layers:pres.layers,active_camera:scene.active_camera,scale:pres.scale,
    derived:true,affects_revision_hash:false,
    note:'an additive presentation block; engineering JSON is never polluted with visual '+
         'scene state and no visual value enters a revision hash'};
  return out; }
function visExportScene(scene,presentationGlb){
  const objs=scene.objects||[];
  const keep=presentationGlb?objs:objs.filter(o=>!o.visual_only);
  return {schema:VIS_SCHEMA,compiler_version:VIS_COMPILER_VERSION,
    kind:presentationGlb?'PRESENTATION_GLB':'ENGINEERING_GLB',
    building_id:scene.building_id,model_hash:scene.model_hash,scene_id:scene.scene_id,
    mode:scene.mode,
    objects:keep.map(o=>({id:o.id,kind:o.kind,layer:o.layer,semantic:o.semantic,
      visual_only:o.visual_only,source_element_id:o.source_element_id,material:o.material,
      material_provenance:o.material_provenance,geometry:o.geometry})),
    includes_visual_only:!!presentationGlb,derived:true,
    note:'the engineering export keeps its semantics; a presentation export is separate, '+
         'explicitly requested, and never replaces it'}; }
function visObjectById(scene,oid){
  const objs=scene.objects||[];
  for(let i=0;i<objs.length;i++) if(objs[i].id===oid) return objs[i];
  return null; }
function visObjectsByLayer(scene,layer){
  return (scene.objects||[]).filter(o=>o.layer===layer); }
/* تبديل رؤية طبقة — حالة عرض بحتة. العرض الهندسي لا يخفي تخصّصاً */
function visSetLayerVisible(scene,layer,on){
  layer=String(layer||'').toUpperCase();
  if(VIS_LAYERS.indexOf(layer)<0) return [false,'LAYER_UNKNOWN',null];
  if(VIS_ENGINEERING_MODES.indexOf(scene.mode)>=0&&!on
     &&['ARCHITECTURE','STRUCTURE','MEP','FLS'].indexOf(layer)>=0)
    return [false,'ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE',null];
  scene.presentation.layer_visibility[layer]=!!on;
  (scene.objects||[]).forEach(o=>{ if(o.layer===layer) o.visible=!!on; });
  return [true,null,scene.presentation.layer_visibility]; }
function visValidateScene(scene){
  const issues=[];
  (scene.materials||[]).forEach(m=>{
    if(m.material_class!==VIS_MATERIAL_CLASS)
      issues.push({code:'MATERIAL_NOT_VISUAL_CLASS',subject:m.id});
    if(m.fire_rating!==null||m.thermal_property!==null||m.structural_material)
      issues.push({code:'MATERIAL_CARRIES_ENGINEERING_PROPERTY',subject:m.id}); });
  (scene.objects||[]).forEach(o=>{
    if(o.visual_only&&o.semantic)
      issues.push({code:'VISUAL_OBJECT_MARKED_SEMANTIC',subject:o.id});
    /* قاعدة المصدر متناظرة وشاملة: لا تعتمد على التصنيف ولا المادة ولا السمة
       ولا الأصل ولا مستوى التفاصيل ولا التخصّص ولا فئة الديكور. */
    if(o.visual_only){
      if(o.source_element_id!==null&&o.source_element_id!==undefined){
        issues.push({code:'VISUAL_ONLY_OBJECT_WITH_SOURCE',subject:o.id});
        /* تخصيص إضافي للديكور — يُبلَّغ فوق القاعدة العامة لا بدلاً منها */
        if(o.visual_class===VIS_DECORATION_CLASS)
          issues.push({code:'DECORATION_LINKED_TO_MODEL_ELEMENT',subject:o.id}); } }
    else if(!o.source_element_id)
      issues.push({code:'MODELLED_OBJECT_WITHOUT_SOURCE',subject:o.id});
    if(!Object.prototype.hasOwnProperty.call(VIS_MATERIALS,o.material))
      issues.push({code:'MATERIAL_NOT_IN_LIBRARY',subject:o.id});
    if(VIS_PROVENANCE.indexOf(o.material_provenance)<0)
      issues.push({code:'MATERIAL_PROVENANCE_INVALID',subject:o.id}); });
  issues.sort((a,b)=>_scmp(String(a.code),String(b.code))
    ||_scmp(String(a.subject),String(b.subject)));
  return issues; }
function visRuleInputs(scene){
  const c=scene.counts||_vCounts(scene);
  return {building:{'visual.scene.object_count':c.objects,
    'visual.scene.visual_only_count':c.visual_only_objects,
    'visual.scene.mode':scene.mode,
    'visual.render.exists':!!scene.scene_id}}; }
function visSummary(scene){
  const c=scene.counts||_vCounts(scene);
  const pres=scene.presentation||{};
  return {compiler_version:VIS_COMPILER_VERSION,building_id:scene.building_id,
    model_hash:scene.model_hash,scene_id:scene.scene_id,mode:scene.mode,theme:pres.theme,
    lighting_preset:pres.lighting_preset,quality:pres.quality,layers:pres.layers,
    objects:c.objects,semantic_objects:c.semantic_objects,
    visual_only_objects:c.visual_only_objects,decoration_objects:c.decoration_objects,
    entourage_objects:c.entourage_objects,landscape_objects:c.landscape_objects,
    materials:c.materials,lights:c.lights,cameras:c.cameras,
    display_fallback_objects:c.display_fallback_objects,
    engineering_geometry_modified:false,compliance:'NOT_EVALUATED',
    note:'geometry-preserving visualisation only — no engineering mutation, no AI '+
         'geometry, and visual decoration is never engineering data'}; }
/* ==================================================================
   المرحلة 2 — أساس التنسيق بين التخصّصات وكشف التعارضات (مطابق لـ acs_coord.py).
   كشف وتتبّع فقط: لا إصلاح تلقائي ولا إعادة توجيه ولا تحجيم ولا إنشاء فتحات
   ولا تحسين ولا إعادة تصميم إنشائي أو MEP أو حريق • التعارض ليس مخالفة كود
   ولا حكم سلامة • الطبقة مشتقّة ولا تُكتب في أي نموذج.
   ================================================================== */
const ACS_COORD_SPEC = {
 "schema": "acs.coord/1",
 "detector_version": "acs-coord-detector/1.0.0",
 "note": "MULTIDISCIPLINARY COORDINATION — DETECTION AND TRACEABILITY ONLY. This layer reads the compiled architectural, structural, MEP and fire/life-safety models and reports where they conflict. It performs NO auto-fix and NO design: it never moves an MEP route, resizes a beam, moves a door, creates a penetration or an opening, sizes a sleeve, reroutes a pipe or duct, or repositions equipment. It draws NO code, safety or adequacy conclusion. A clash is a coordination finding about modelled geometry and references — nothing more.",
 "derivation_note": "the coordination model is DERIVED. It is never written back into the architectural, structural, MEP or FLS models, and compiling it leaves every one of them byte-identical.",
 "disciplines": [
  "ARCHITECTURE",
  "STRUCTURE",
  "MEP",
  "FLS"
 ],
 "clash_types": [
  "HARD_CLASH",
  "CLEARANCE_CLASH",
  "OPENING_REQUIRED",
  "PENETRATION_UNRESOLVED",
  "SEMANTIC_CONFLICT",
  "OUTSIDE_HOST",
  "DUPLICATE_OCCUPANCY",
  "INVALID_REFERENCE"
 ],
 "clash_type_note": "a deliberately small vocabulary. HARD_CLASH is a real volume intersection in resolved world coordinates. CLEARANCE_CLASH exists only where the model states a clearance. OPENING_REQUIRED is a coordination finding, never an instruction and never an opening. PENETRATION_UNRESOLVED means a declared penetration does not resolve or does not actually cover the crossing it claims.",
 "clash_statuses": [
  "OPEN",
  "ACKNOWLEDGED",
  "RESOLVED_EXTERNALLY",
  "FALSE_POSITIVE",
  "OBSOLETE"
 ],
 "status_note": "RESOLVED is deliberately absent as an automatic outcome. A clash that no longer appears in a newer snapshot is classified RESOLVED_BY_MODEL_CHANGE or OBSOLETE — never 'engineered correctly'. Only a human decision produces ACKNOWLEDGED, RESOLVED_EXTERNALLY or FALSE_POSITIVE.",
 "reconciliation_states": [
  "NEW",
  "PERSISTING",
  "RESOLVED_BY_MODEL_CHANGE",
  "OBSOLETE"
 ],
 "reconciliation_note": "RESOLVED_BY_MODEL_CHANGE states only that the geometry that produced the finding is no longer present. It asserts nothing about whether the change was correct, adequate or engineered.",
 "severities": [
  "INFO",
  "WARNING",
  "ERROR"
 ],
 "severity_note": "coordination severities reflect data and model integrity only. UNSAFE / FATAL / CODE VIOLATION are deliberately absent and are never justified by this layer.",
 "clash_severity": {
  "HARD_CLASH": "WARNING",
  "CLEARANCE_CLASH": "INFO",
  "OPENING_REQUIRED": "WARNING",
  "PENETRATION_UNRESOLVED": "WARNING",
  "SEMANTIC_CONFLICT": "ERROR",
  "OUTSIDE_HOST": "WARNING",
  "DUPLICATE_OCCUPANCY": "INFO",
  "INVALID_REFERENCE": "ERROR"
 },
 "snapshot_statuses": [
  "CURRENT",
  "STALE_MODEL_CHANGED",
  "UNVERIFIABLE"
 ],
 "discipline_pairs": [
  [
   "ARCHITECTURE",
   "STRUCTURE"
  ],
  [
   "ARCHITECTURE",
   "MEP"
  ],
  [
   "ARCHITECTURE",
   "FLS"
  ],
  [
   "STRUCTURE",
   "MEP"
  ],
  [
   "STRUCTURE",
   "FLS"
  ],
  [
   "MEP",
   "FLS"
  ]
 ],
 "pair_note": "only cross-discipline pairs are tested. Two elements of the same discipline meeting each other is that discipline's own business and is already validated inside its own layer; testing it here would manufacture noise rather than coordination findings.",
 "element_kinds": [
  "ARCH_WALL",
  "ARCH_OPENING",
  "ARCH_SLAB",
  "ARCH_VOID",
  "ARCH_CORE",
  "STRUCT_COLUMN",
  "STRUCT_BEAM",
  "STRUCT_SLAB",
  "STRUCT_WALL",
  "STRUCT_FOUNDATION",
  "STRUCT_CORE",
  "MEP_SEGMENT",
  "MEP_EQUIPMENT",
  "MEP_TERMINAL",
  "MEP_RISER",
  "FLS_DEVICE",
  "FLS_SIGN",
  "FLS_ASSEMBLY_POINT"
 ],
 "geometry_note": "every element is resolved into one world-space axis-aligned bounding box plus, where the element is a rotated box, its centre, half-extents and rotation about Y. The building position and rotation, the grid or element rotation and the level elevation are all applied before any test. There is no world-axis shortcut anywhere. Elements that represent negative space carry solid=false and are indexed but never act as clash bodies.",
 "broad_phase": "uniform spatial hash. Every element's world AABB is inserted into every grid cell it overlaps; candidate pairs are the cross-discipline pairs sharing at least one cell, deduplicated. Cell size is fixed at 2 m. Complexity is O(n·k) to build, where k is the number of cells an element spans, and O(sum over cells of m^2) to enumerate, which is near-linear for the sparse, mostly-small elements this platform produces. It degenerates toward O(n^2) only if many large elements overlap the same cells; the benchmark records the actual candidate-pair count so the behaviour is visible rather than assumed.",
 "narrow_phase": "world AABB overlap with a strictly positive overlap volume, then, when both elements carry an oriented box, a separating-axis test on the two Y-rotated boxes. No mesh boolean operation is performed and none is needed for the box and swept-segment geometry this platform emits. Proximity alone never produces a HARD_CLASH.",
 "exemption_kinds": [
  "OPENING_IN_ITS_HOST_WALL",
  "SEGMENT_THROUGH_EXISTING_OPENING",
  "SEGMENT_IN_DECLARED_PENETRATION",
  "COLUMN_THROUGH_ITS_OWN_LEVEL_SLAB",
  "BEAM_MEETS_COLUMN_AT_NODE",
  "SAME_SOURCE_ELEMENT",
  "FLS_REFERENCES_MEP_ELEMENT",
  "ELEMENT_INSIDE_DECLARED_VOID_OR_CORE"
 ],
 "exemption_note": "exemptions are semantic, never type-blind. Each one is justified by an explicit relationship or an explicit declaration in the models — an opening declares its host wall, a penetration declares its host and service, a beam endpoint coincides with a column axis, an FLS device references the MEP element it was adapted from, and a core or floor void is declared negative space rather than matter. No clash is dropped merely because of the kinds of the two elements involved, and every applied exemption is recorded on the pair it suppressed, with both element ids, so nothing is silently hidden.",
 "penetration_note": "a represented penetration is not a structurally approved opening, is not firestopped and is not code compliant. It only records that the model states an opening exists where a service crosses a host, and this layer additionally checks that the stated penetration geometrically covers the crossing it claims.",
 "clearance_note": "a clearance clash is reported only where an element explicitly states clearance_m. No service, maintenance or code clearance is ever invented, and with no stated clearance there is no clearance clash.",
 "identity_note": "a clash id is deterministic: sha256 over the canonical tuple (type, discipline_a, element_a, discipline_b, element_b), truncated to 16 hex characters and prefixed clash_. The same conflict in the same two elements always produces the same id, in both languages, which is what makes reconciliation between revisions possible.",
 "evidence_note": "every clash carries its geometric evidence — the two world AABBs, the intersection box and its volume — plus the source element ids, the two discipline models, the model revision hash and the detector version. No clash is ever produced without geometric or reference evidence, and nothing here is AI-generated.",
 "navigation_note": "coordination findings do NOT affect navigation, egress, pathfinding or walking distance in this phase. A column that geometrically blocks a route is reported as a clash and nothing is silently rerouted. Obstacle-aware navigation is a future explicit phase.",
 "forbidden_claims": [
  "unsafe",
  "fatal",
  "code_violation",
  "non_compliant",
  "compliant",
  "auto_fixed",
  "rerouted",
  "resized",
  "resolved_automatically",
  "firestopped",
  "structurally_adequate",
  "opening_created",
  "sleeve_size",
  "optimised",
  "optimized"
 ],
 "grid_cell_m": 2.0,
 "id_patterns": {
  "clash": "clash_<sha256_16>",
  "penetration": "<bid>.coord.pen_<n>",
  "snapshot": "coord_<model_hash_16>"
 },
 "rule_inputs": [
  "coordination.clash.count",
  "coordination.clash.count_by_type",
  "coordination.issue.exists",
  "coordination.penetration.exists",
  "coordination.penetration.count"
 ],
 "rule_note": "factual inputs only. No regulatory rule exists here, a clash count is never compared to a threshold, and missing data stays missing.",
 "no_generator_note": "this phase ships NO clash resolution, NO routing, NO optimisation, NO opening or sleeve creation and NO auto-fix of any kind. It answers what conflicts exist, never how they should be redesigned.",
 "void_note": "ARCH_VOID and ARCH_CORE are declared negative space, not matter: the architectural layer itself punches a floor void through every slab a core passes. An element lying inside one of them therefore has nothing to intersect, and the pair is recorded as ELEMENT_INSIDE_DECLARED_VOID_OR_CORE in the suppressed list instead of being reported as a hard clash or being dropped in silence. This layer draws no conclusion about whether that element belongs there.",
 "geometry_confidence": [
  "stated",
  "display_fallback"
 ],
 "geometry_confidence_note": "every clash declares whether both sides were sized from stated model dimensions or whether at least one side fell back to a render dimension. A display fallback is never promoted to an engineering dimension, and a clash resting on one is reported as found and labelled, never silently dropped and never presented as a measured conflict."
};
const COORD_SCHEMA = ACS_COORD_SPEC.schema;
const COORD_DETECTOR_VERSION = ACS_COORD_SPEC.detector_version;
const COORD_DISCIPLINES = ACS_COORD_SPEC.disciplines;
const COORD_CLASH_TYPES = ACS_COORD_SPEC.clash_types;
const COORD_CLASH_STATUSES = ACS_COORD_SPEC.clash_statuses;
const COORD_RECONCILIATION_STATES = ACS_COORD_SPEC.reconciliation_states;
const COORD_SEVERITIES = ACS_COORD_SPEC.severities;
const COORD_CLASH_SEVERITY = ACS_COORD_SPEC.clash_severity;
const COORD_SNAPSHOT_STATUSES = ACS_COORD_SPEC.snapshot_statuses;
const COORD_DISCIPLINE_PAIRS = ACS_COORD_SPEC.discipline_pairs;
const COORD_ELEMENT_KINDS = ACS_COORD_SPEC.element_kinds;
const COORD_EXEMPTION_KINDS = ACS_COORD_SPEC.exemption_kinds;
const COORD_GEOMETRY_CONFIDENCE = ACS_COORD_SPEC.geometry_confidence;
const COORD_CELL = Number(ACS_COORD_SPEC.grid_cell_m);
const _CO_EPS = 1e-9;
const _CO_MAX_CELLS = 4096;
const _CO_NON_SOLID = ['ARCH_VOID', 'ARCH_CORE'];

function coordSeverityOf(t){
  return Object.prototype.hasOwnProperty.call(COORD_CLASH_SEVERITY,t)
    ?COORD_CLASH_SEVERITY[t]:'WARNING'; }
function _coNum(v){ return _snum(v); }
/* تقريب قانوني للإحداثيات المنشورة — يمنع انحراف الفاصلة بين اللغتين */
function _coQ(v){ const r=_pyRound(Number(v),6); return r===0?0:r; }
function _coFmt6(v){ return _coFixed(Number(v)+0,6); }
/* تنسيق ثابت مطابق لـ "%.6f" في بايثون (تقريب مصرفي إلى أقرب زوجي) */
function _coFixed(v,nd){
  const r=_pyRound(v,nd); const neg=(r<0)||(r===0&&1/r<0);
  const a=Math.abs(r); let s=a.toFixed(nd);
  if(s.indexOf('e')>=0||s.indexOf('E')>=0) s=a.toFixed(nd);
  return (neg?'-':'')+s; }
function _coCanon(o){ return JSON.stringify(o); }
function _coProjectKey(hashes){
  return hashes.map(h=>[String(h.building_id),String(h.model_hash),
    _coFmt6(h.position.x),_coFmt6(h.position.z),_coFmt6(h.rotation_deg)]); }
function _coClashId(ctype,da,ea,db,eb){
  return 'clash_'+sha256Hex(_coCanon([ctype,da===undefined?null:da,ea===undefined?null:ea,
    db===undefined?null:db,eb===undefined?null:eb])).slice(0,16); }

/* ------------------------------------------- هندسة عالمية موحّدة ------- */
function _coRot(px,pz,rotDeg,ox,oz){
  const r=(Number(rotDeg)||0)*Math.PI/180, ca=Math.cos(r), sa=Math.sin(r);
  return [(ox||0)+px*ca-pz*sa,(oz||0)+px*sa+pz*ca]; }
function _coObb(cx,cy,cz,ex,ey,ez,rotYRad,transform){
  const t=transform||{}, brot=Number(t.rotation_deg)||0;
  const p=t.position||{}, px=Number(p.x)||0, pz=Number(p.z)||0;
  const w=_coRot(cx,cz,brot,px,pz);
  const yaw=(Number(rotYRad)||0)+brot*Math.PI/180;
  return {cx:_coQ(w[0]),cy:_coQ(cy),cz:_coQ(w[1]),
    hx:_coQ(Math.abs(ex)/2),hy:_coQ(Math.abs(ey)/2),hz:_coQ(Math.abs(ez)/2),yaw:_coQ(yaw)}; }
function _coAabbOf(o){
  const ca=Math.abs(Math.cos(o.yaw)), sa=Math.abs(Math.sin(o.yaw));
  const rx=o.hx*ca+o.hz*sa, rz=o.hx*sa+o.hz*ca;
  return [_coQ(o.cx-rx),_coQ(o.cy-o.hy),_coQ(o.cz-rz),
          _coQ(o.cx+rx),_coQ(o.cy+o.hy),_coQ(o.cz+rz)]; }
function _coAabbOverlap(a,b){
  const lo=[Math.max(a[0],b[0]),Math.max(a[1],b[1]),Math.max(a[2],b[2])];
  const hi=[Math.min(a[3],b[3]),Math.min(a[4],b[4]),Math.min(a[5],b[5])];
  if(hi[0]-lo[0]<=_CO_EPS||hi[1]-lo[1]<=_CO_EPS||hi[2]-lo[2]<=_CO_EPS) return null;
  return {min:[_coQ(lo[0]),_coQ(lo[1]),_coQ(lo[2])],
          max:[_coQ(hi[0]),_coQ(hi[1]),_coQ(hi[2])],
          volume_m3:_coQ((hi[0]-lo[0])*(hi[1]-lo[1])*(hi[2]-lo[2]))}; }
function _coProj(o,ax,az){
  const c=Math.cos(o.yaw), s=Math.sin(o.yaw);
  return Math.abs(c*ax+s*az)*o.hx+Math.abs(-s*ax+c*az)*o.hz; }
function _coObbOverlap(a,b){
  if(a.cy+a.hy<=b.cy-b.hy+_CO_EPS||b.cy+b.hy<=a.cy-a.hy+_CO_EPS) return false;
  const axes=[];
  [a,b].forEach(o=>{ const c=Math.cos(o.yaw), s=Math.sin(o.yaw);
    axes.push([c,s]); axes.push([-s,c]); });
  const dx=b.cx-a.cx, dz=b.cz-a.cz;
  for(let i=0;i<axes.length;i++){
    const ax=axes[i][0], az=axes[i][1];
    if(Math.abs(dx*ax+dz*az)>=_coProj(a,ax,az)+_coProj(b,ax,az)-1e-9) return false; }
  return true; }
/* هل أبعاد العنصر مذكورة في النموذج أم احتياط عرض؟ لا يُرقّى الاحتياط أبداً */
function _coGsrc(fields){
  for(let i=0;i<fields.length;i++){ const f=fields[i];
    if(!f||typeof f!=='object'||f.value===null||f.value===undefined) return 'display_fallback'; }
  return 'model'; }
function _coVol(discipline,kind,eid,obb,meta){
  const e={discipline:discipline,kind:kind,element_id:eid,obb:obb,aabb:_coAabbOf(obb),
    solid:_CO_NON_SOLID.indexOf(kind)<0};
  Object.keys(meta||{}).forEach(k=>{e[k]=(meta[k]===undefined)?null:meta[k];});
  return e; }
function _coSegBox(a,b,w,h,transform){
  const dx=b[0]-a[0], dz=b[2]-a[2];
  const ay=(a[1]===null||a[1]===undefined)?0:a[1], by=(b[1]===null||b[1]===undefined)?0:b[1];
  const ln=Math.sqrt(dx*dx+dz*dz), dy=by-ay;
  if(ln<=1e-9) return _coObb((a[0]+b[0])/2,(ay+by)/2,(a[2]+b[2])/2,
    Math.max(w,1e-3),Math.max(Math.abs(dy),1e-3),Math.max(h,1e-3),0,transform);
  return _coObb((a[0]+b[0])/2,(ay+by)/2,(a[2]+b[2])/2,
    Math.sqrt(ln*ln+dy*dy),Math.max(h,1e-3),Math.max(w,1e-3),Math.atan2(-dz,dx),transform); }

/* ------------------------------------------- استخراج أحجام النماذج ----- */
function _coArchVolumes(arch,transform,bid){
  const out=[]; if(!arch) return out;
  const lv={}; (arch.levels||[]).forEach(l=>{lv[l.index]=l;});
  (arch.walls||[]).forEach(w=>{
    const h=w.height_m.value||w.height_m.render_fallback;
    const t=w.thickness_m.value||w.thickness_m.render_fallback;
    const base=(lv[w.level_index]||{}).elevation_m;
    if(base===null||base===undefined) return;
    const a=w.start, b=w.end;
    const obb=_coSegBox([a.x,base+h/2,a.z],[b.x,base+h/2,b.z],t,h,transform);
    out.push(_coVol('ARCHITECTURE','ARCH_WALL',w.id,obb,
      {level_index:w.level_index,spaces:(w.spaces||[]).slice(),source_ref:w.id,
       host_of:(w.openings||[]).slice(),
       geometry_source:_coGsrc([w.height_m,w.thickness_m])})); });
  (arch.openings||[]).forEach(o=>{
    const wdt=o.width_m.value||o.width_m.render_fallback;
    const hgt=o.height_m.value||o.height_m.render_fallback;
    const base=(lv[o.level_index]||{}).elevation_m;
    if(base===null||base===undefined) return;
    let sill=0;
    if(o.type==='WINDOW') sill=(o.sill_m.value===null||o.sill_m.value===undefined)
      ?o.sill_m.render_fallback:o.sill_m.value;
    const cy=base+sill+hgt/2;
    const obb=(o.axis==='x')?_coObb(o.u_center,cy,o.fixed,wdt,hgt,0.2,0,transform)
                            :_coObb(o.fixed,cy,o.u_center,0.2,hgt,wdt,0,transform);
    out.push(_coVol('ARCHITECTURE','ARCH_OPENING',o.id,obb,
      {level_index:o.level_index,space_id:o.space_id,host_wall_id:o.host_wall_id,
       source_ref:o.id,geometry_source:_coGsrc([o.width_m,o.height_m])})); });
  (arch.slabs||[]).forEach(s=>{
    const o=s.outline, t=s.thickness_m.value||s.thickness_m.render_fallback;
    if(o===null||o===undefined||s.elevation_m===null||s.elevation_m===undefined) return;
    out.push(_coVol('ARCHITECTURE','ARCH_SLAB',s.id,
      _coObb(o[0]+o[2]/2,s.elevation_m-t/2,o[1]+o[3]/2,o[2],t,o[3],0,transform),
      {level_index:s.level_index,source_ref:s.id,geometry_source:_coGsrc([s.thickness_m])})); });
  (arch.voids||[]).forEach(v=>{
    const r=v.rect, base=(lv[v.level_index]||{}).elevation_m;
    if(base===null||base===undefined) return;
    out.push(_coVol('ARCHITECTURE','ARCH_VOID',v.id,
      _coObb(r[0]+r[2]/2,base,r[1]+r[3]/2,r[2],0.4,r[3],0,transform),
      {level_index:v.level_index,core_id:v.core_id,source_ref:v.id})); });
  (arch.cores||[]).forEach(c=>{
    const fw=c.footprint_w_m.value||c.footprint_w_m.render_fallback;
    const fd=c.footprint_d_m.value||c.footprint_d_m.render_fallback;
    const served=c.served_levels||[];
    if(!served.length) return;
    const base=(lv[Math.min.apply(null,served)]||{}).elevation_m;
    const top=(lv[Math.max.apply(null,served)]||{}).elevation_m;
    if(base===null||base===undefined||top===null||top===undefined||top-base<=0) return;
    out.push(_coVol('ARCHITECTURE','ARCH_CORE',c.id,
      _coObb(c.x,base+(top-base)/2,c.z,fw,top-base,fd,0,transform),
      {core_type:c.type,source_ref:c.id,
       geometry_source:_coGsrc([c.footprint_w_m,c.footprint_d_m])})); });
  return out; }

function _coStructVolumes(struct,transform){
  const out=[]; if(!struct) return out;
  const kinds={COLUMN:'STRUCT_COLUMN',BEAM:'STRUCT_BEAM',STRUCTURAL_SLAB:'STRUCT_SLAB',
    STRUCTURAL_WALL:'STRUCT_WALL',FOUNDATION:'STRUCT_FOUNDATION',STRUCTURAL_CORE:'STRUCT_CORE'};
  const supports={};
  (struct.relationships||[]).forEach(r=>{ if(r.type!=='COLUMN_SUPPORTS') return;
    if(!supports[r.to]) supports[r.to]={}; supports[r.to][r.from]=true;
    if(!supports[r.from]) supports[r.from]={}; supports[r.from][r.to]=true; });
  structRenderItems(struct).forEach(it=>{
    if(it.kind==='GRID_LINE') return;
    const kind=Object.prototype.hasOwnProperty.call(kinds,it.kind)?kinds[it.kind]:'STRUCT_COLUMN';
    const el=structElementById(struct,it.id);
    const meta={source_ref:it.id,
      connected:Object.keys(supports[it.id]||{}).sort(_scmp),
      geometry_source:it.geometry_source};
    if(el!==null&&el!==undefined){
      meta.level_index=el.level_index; meta.base_level_index=el.base_level_index;
      meta.top_level_index=el.top_level_index; meta.level_indexes=el.level_indexes;
      const props=el.properties;
      if(props&&typeof props==='object'){
        const cl=_coNum(props.clearance_m);
        if(cl!==null) meta.clearance_m=cl; } }
    out.push(_coVol('STRUCTURE',kind,it.id,
      _coObb(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,it.rot_y||0,transform),meta)); });
  return out; }

function _coMepVolumes(mep,transform,bid){
  const out=[]; if(!mep) return out;
  const segById={}; (mep.segments||[]).forEach(s=>{segById[s.id]=s;});
  mepRenderItems(mep).forEach(it=>{
    if(it.kind==='SEGMENT'){
      const s=segById[it.id]||{};
      out.push(_coVol('MEP','MEP_SEGMENT',it.name,
        _coObb(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,it.rot_y||0,transform),
        {segment_id:it.id,source_ref:it.id,level_index:s.level_index,system_id:s.system_id,
         geometry_source:it.geometry_source}));
      return; }
    const kmap={EQUIPMENT:'MEP_EQUIPMENT',TERMINAL:'MEP_TERMINAL',RISER:'MEP_RISER'};
    const kind=Object.prototype.hasOwnProperty.call(kmap,it.kind)?kmap[it.kind]:'MEP_EQUIPMENT';
    const el=mepElementById(mep,it.id);
    const meta={source_ref:it.id,geometry_source:it.geometry_source};
    if(el!==null&&el!==undefined){
      meta.level_index=el.level_index; meta.space_id=el.space_id; meta.system_id=el.system_id;
      const props=el.properties||{};
      const pc=props.clearance_m;
      if(pc&&typeof pc==='object'){ const cl=_coNum(pc.value); if(cl!==null) meta.clearance_m=cl; } }
    out.push(_coVol('MEP',kind,it.id,
      _coObb(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,it.rot_y||0,transform),meta)); });
  return out; }

/* العناصر المُشار إليها لا تُدرَج: هندستها مملوكة لطبقة MEP */
function _coFlsVolumes(fls,transform){
  const out=[]; if(!fls) return out;
  flsRenderItems(fls).forEach(it=>{
    if(it.render_mode!=='emitted') return;
    const el=flsElementById(fls,it.id);
    const kmap={DEVICE:'FLS_DEVICE',SIGN:'FLS_SIGN',ASSEMBLY_POINT:'FLS_ASSEMBLY_POINT'};
    const kind=Object.prototype.hasOwnProperty.call(kmap,it.kind)?kmap[it.kind]:'FLS_DEVICE';
    const meta={source_ref:((el||{}).mep_element_id)||it.id,device_type:it.device_type};
    if(el!==null&&el!==undefined){ meta.level_index=el.level_index; meta.space_id=el.space_id; }
    out.push(_coVol('FLS',kind,it.id,
      _coObb(it.cx,it.cy,it.cz,it.ex,it.ey,it.ez,0,transform),meta)); });
  return out; }

/* ------------------------------------------------------- الاختراقات ---- */
function _coPenetrations(mep,arch,struct,bid,transform){
  const out=[];
  const raw=((mep||{}).penetrations||[]).slice()
    .sort((a,b)=>_scmp(String(a.id),String(b.id)));
  raw.forEach((p,n)=>{
    let host=null;
    const srcs=[['walls',arch],['slabs',arch],['beams',struct],['columns',struct],
                ['slabs',struct],['walls',struct]];
    for(let i=0;i<srcs.length&&host===null;i++){
      const list=((srcs[i][1]||{})[srcs[i][0]])||[];
      for(let j=0;j<list.length;j++){ if(list[j].id===p.host_id){ host=list[j]; break; } } }
    let seg=null;
    const segs=(mep||{}).segments||[];
    for(let i=0;i<segs.length;i++){
      if(segs[i].id===p.segment_id||segs[i].id===_mnid(bid,p.segment_id,'seg',0)){ seg=segs[i]; break; } }
    out.push({id:bid+'.coord.pen_'+n,penetration_id:p.id,host_element:p.host_id,
      host_type:p.host_type,host_resolved:host!==null,
      service_element:seg?seg.id:p.segment_id,service_resolved:seg!==null,
      x:p.x,z:p.z,level_index:p.level_index,size:p.size,source:p.source,
      status:'REPRESENTED',
      note:'a represented penetration is not a structurally approved opening, '+
           'is not firestopped and is not code compliant'}); });
  return out; }
/* هل يغطّي الاختراق المعلن موضع العبور فعلاً؟ بلا موضع معلن لا نجزم */
function _coPenCovers(pen,inter){
  if(pen.x===null||pen.x===undefined||pen.z===null||pen.z===undefined) return null;
  const sz=pen.size||{};
  const r=_coNum(sz.diameter_m)||_coNum(sz.width_m)||0.6;
  const cx=(inter.min[0]+inter.max[0])/2, cz=(inter.min[2]+inter.max[2])/2;
  return Math.abs(cx-Number(pen.x))<=r+0.5&&Math.abs(cz-Number(pen.z))<=r+0.5; }

/* --------------------------------------------------------- الاستثناء --- */
function _coExempt(a,b,pens,openings){
  if(a.source_ref&&a.source_ref===b.source_ref) return 'SAME_SOURCE_ELEMENT';
  if(a.discipline==='FLS'&&b.discipline==='MEP'&&a.source_ref===b.element_id)
    return 'FLS_REFERENCES_MEP_ELEMENT';
  if(b.discipline==='FLS'&&a.discipline==='MEP'&&b.source_ref===a.element_id)
    return 'FLS_REFERENCES_MEP_ELEMENT';
  const ord=[[a,b],[b,a]];
  for(let i=0;i<ord.length;i++){
    const x=ord[i][0], y=ord[i][1];
    if(x.kind==='ARCH_OPENING'&&y.kind==='ARCH_WALL'&&x.host_wall_id===y.element_id)
      return 'OPENING_IN_ITS_HOST_WALL';
    if(x.kind==='STRUCT_COLUMN'&&(y.kind==='ARCH_SLAB'||y.kind==='STRUCT_SLAB')){
      const lo=x.base_level_index, hi=x.top_level_index, li=y.level_index;
      if(lo!==null&&lo!==undefined&&hi!==null&&hi!==undefined&&li!==null&&li!==undefined
         &&lo<=li&&li<=hi) return 'COLUMN_THROUGH_ITS_OWN_LEVEL_SLAB'; }
    if(x.kind==='STRUCT_BEAM'&&y.kind==='STRUCT_COLUMN'&&
       (x.connected||[]).indexOf(y.element_id)>=0) return 'BEAM_MEETS_COLUMN_AT_NODE';
    /* فراغ معلن لا مادّة فيه: لا شيء يصطدم به، والزوج يُسجَّل بدل أن يُخفى */
    if(!y.solid&&x.solid) return 'ELEMENT_INSIDE_DECLARED_VOID_OR_CORE';
    /* مقطع يعبر الجدار داخل فتحة معلنة في الجدار نفسه — لا فتحة جديدة مطلوبة */
    if(x.kind==='MEP_SEGMENT'&&y.kind==='ARCH_WALL'&&openings){
      const hs=y.host_of||[];
      for(let k=0;k<hs.length;k++){ const ov=openings[hs[k]];
        if(ov!==null&&ov!==undefined&&_coAabbOverlap(x.aabb,ov.aabb))
          return 'SEGMENT_THROUGH_EXISTING_OPENING'; } } }
  if(!a.solid&&!b.solid) return 'ELEMENT_INSIDE_DECLARED_VOID_OR_CORE';
  return null; }
/* مقطع MEP داخل اختراق معلن يغطّي موضع العبور فعلاً */
function _coPenExempt(a,b,pens,inter){
  const ord=[[a,b],[b,a]];
  for(let i=0;i<ord.length;i++){
    const x=ord[i][0], y=ord[i][1];
    if(x.kind!=='MEP_SEGMENT') continue;
    for(let j=0;j<pens.length;j++){ const p=pens[j];
      if(p.service_element!==x.segment_id) continue;
      if(p.host_element!==y.element_id) continue;
      const cov=_coPenCovers(p,inter);
      if(cov===null||cov===true) return ['SEGMENT_IN_DECLARED_PENETRATION',p,cov];
      return [null,p,false]; } }
  return [null,null,null]; }

/* ------------------------------------------- الفهرسة والمرحلة العريضة -- */
/* عدد الخلايا يُحسب قبل توليدها كي لا يُبنى ملايين المفاتيح لعنصر ضخم واحد */
function _coCellSpan(aabb){
  const nx=Math.floor(aabb[3]/COORD_CELL)-Math.floor(aabb[0]/COORD_CELL)+1;
  const ny=Math.floor(aabb[4]/COORD_CELL)-Math.floor(aabb[1]/COORD_CELL)+1;
  const nz=Math.floor(aabb[5]/COORD_CELL)-Math.floor(aabb[2]/COORD_CELL)+1;
  return nx*ny*nz; }
function _coCells(aabb){
  const out=[];
  for(let ix=Math.floor(aabb[0]/COORD_CELL);ix<=Math.floor(aabb[3]/COORD_CELL);ix++)
    for(let iy=Math.floor(aabb[1]/COORD_CELL);iy<=Math.floor(aabb[4]/COORD_CELL);iy++)
      for(let iz=Math.floor(aabb[2]/COORD_CELL);iz<=Math.floor(aabb[5]/COORD_CELL);iz++)
        out.push(ix+'|'+iy+'|'+iz);
  return out; }
const _CO_PAIR_SET={};
COORD_DISCIPLINE_PAIRS.forEach(p=>{ _CO_PAIR_SET[p.slice().sort(_scmp).join('|')]=true; });
/* صندوق الفهرسة يتّسع بالخلوص المذكور فقط — لا خلوص مُخترع */
function _coIndexAabb(v){
  const cl=v.clearance_m;
  if(cl===null||cl===undefined||cl<=0) return v.aabb;
  const a=v.aabb;
  return [a[0]-cl,a[1]-cl,a[2]-cl,a[3]+cl,a[4]+cl,a[5]+cl]; }
function coordBroadPhase(volumes){
  const grid={}, oversized=[], pairs={};
  volumes.forEach((v,i)=>{
    const box=_coIndexAabb(v);
    if(_coCellSpan(box)>_CO_MAX_CELLS){ oversized.push(i); return; }
    _coCells(box).forEach(c=>{ if(!grid[c]) grid[c]=[]; grid[c].push(i); }); });
  function consider(a,b){
    const da=volumes[a].discipline, db=volumes[b].discipline;
    if(da===db) return;
    if(!_CO_PAIR_SET[[da,db].sort(_scmp).join('|')]) return;
    const k=(a<b)?(a+'|'+b):(b+'|'+a);
    pairs[k]=(a<b)?[a,b]:[b,a]; }
  let busiest=0;
  Object.keys(grid).sort(_scmp).forEach(c=>{
    const idxs=grid[c];
    if(idxs.length>busiest) busiest=idxs.length;
    for(let i=0;i<idxs.length;i++) for(let j=i+1;j<idxs.length;j++) consider(idxs[i],idxs[j]); });
  oversized.forEach(a=>{ for(let b=0;b<volumes.length;b++) if(a!==b) consider(a,b); });
  const out=Object.keys(pairs).map(k=>pairs[k]);
  out.sort((p,q)=>(p[0]-q[0])||(p[1]-q[1]));
  return [out,{cells:Object.keys(grid).length,oversized_elements:oversized.length,
               busiest_cell:busiest}]; }

/* ----------------------------------------------------------- التصريف --- */
const _CO_SEMANTIC_SOURCE={
  ARCHITECTURE:[],
  STRUCTURE:['INVALID_LEVEL_REF','INVALID_NODE_REF','INVALID_MATERIAL_REF',
             'INVALID_GRID_REF','CROSS_BUILDING_REF','FOUNDATION_TARGET_UNRESOLVED'],
  MEP:['INVALID_SYSTEM_REF','INVALID_NODE_REF','INVALID_EQUIPMENT_REF','INVALID_LEVEL_REF',
       'INVALID_SPACE_REF','CROSS_BUILDING_REF','PENETRATION_HOST_UNRESOLVED',
       'PENETRATION_SEGMENT_UNRESOLVED'],
  FLS:['INVALID_SYSTEM_REF','INVALID_MEP_ELEMENT_REF','INVALID_LEVEL_REF','INVALID_SPACE_REF',
       'INVALID_EXIT_REF','INVALID_HOST_WALL_REF','INVALID_HOST_OPENING_REF','INVALID_CORE_REF',
       'INVALID_ZONE_SPACE_REF','INVALID_BARRIER_REF','CROSS_BUILDING_REF','SIGN_TARGET_MISSING',
       'FIRE_DOOR_NOT_HOSTED','BARRIER_WITHOUT_HOST']};
const _CO_SEMANTIC_PARTNER={FLS:'ARCHITECTURE',MEP:'ARCHITECTURE',STRUCTURE:'ARCHITECTURE'};
const _CO_SEMANTIC_MEP=['INVALID_MEP_ELEMENT_REF','INVALID_SYSTEM_REF'];
/* تعارضات مرجعية بين التخصّصات — مأخوذة من فحوص كل طبقة، لا مُختلقة */
function _coSemanticConflicts(bid,arch,struct,mep,fls){
  const out=[];
  [['STRUCTURE',struct],['MEP',mep],['FLS',fls]].forEach(pair=>{
    const disc=pair[0], model=pair[1];
    ((model||{}).issues||[]).forEach(i=>{
      if(_CO_SEMANTIC_SOURCE[disc].indexOf(i.code)<0) return;
      const partner=(disc==='FLS'&&_CO_SEMANTIC_MEP.indexOf(i.code)>=0)
        ?'MEP':_CO_SEMANTIC_PARTNER[disc];
      const ctype=(String(i.code).indexOf('INVALID')===0)?'INVALID_REFERENCE':'SEMANTIC_CONFLICT';
      const ref=(i.ref!==null&&i.ref!==undefined)?i.ref:i.refs;
      out.push({type:ctype,discipline_a:disc,
        element_a:(i.subject===undefined)?null:i.subject,
        discipline_b:partner,
        element_b:(ref!==null&&ref!==undefined)?_coRefStr(ref):null,
        code:i.code,detail:(i.detail===undefined)?null:i.detail,
        evidence:{kind:'reference',reported_by:disc,source_code:i.code}}); }); });
  out.sort((x,y)=>_scmp(String(x.type),String(y.type))
    ||_scmp(String(x.discipline_a),String(y.discipline_a))
    ||_scmp(String(x.element_a),String(y.element_a))
    ||_scmp(String(x.code),String(y.code))
    ||_scmp(String(x.element_b),String(y.element_b)));
  return out; }
/* تمثيل نصّي مطابق لـ str() في بايثون للمراجع البسيطة والقوائم */
function _coRefStr(v){
  if(Array.isArray(v)) return '['+v.map(x=>_coRefStr1(x)).join(', ')+']';
  if(typeof v==='string') return v;
  return _coRefStr1(v); }
function _coRefStr1(v){
  if(v===null) return 'None';
  if(v===true) return 'True';
  if(v===false) return 'False';
  if(typeof v==='number') return String(v);
  if(typeof v==='string') return "'"+v.replace(/\\/g,'\\\\').replace(/'/g,"\\'")+"'";
  return String(v); }

function compileCoordination(building,buildingId,position,rotationDeg,arch,struct,mep,fls,at){
  return compileProjectCoordination([{id:buildingId||'bld_0',building:building,
    position:position,rotation_deg:rotationDeg||0,arch:arch,struct:struct,mep:mep,fls:fls}],at); }

/* تنسيق على مستوى المشروع: كل مبنى يُحلّ إلى الإحداثيات العالمية أولاً */
function compileProjectCoordination(entries,at){
  const volumes=[], pens=[], disciplines=[], hashes=[], semantic=[];
  (entries||[]).forEach(ent=>{
    const bid=ent.id||'bld_0';
    const b=ent.building||{};
    const pos=ent.position, rot=Number(ent.rotation_deg)||0;
    const transform={position:pos||{x:0,z:0},rotation_deg:rot};
    let arch=ent.arch, struct=ent.struct, mep=ent.mep, fls=ent.fls;
    if(arch===null||arch===undefined){
      try{ arch=compileArchitecture(b,bid,pos,rot); }catch(e){ arch=null; } }
    if(struct===null||struct===undefined){
      try{ struct=compileStructure(b,bid,pos,rot,arch); }catch(e){ struct=null; } }
    if(mep===null||mep===undefined){
      try{ mep=compileMep(b,bid,pos,rot,arch,struct); }catch(e){ mep=null; } }
    if(fls===null||fls===undefined){
      try{ fls=compileFls(b,bid,pos,rot,arch,mep); }catch(e){ fls=null; } }
    let mh=null;
    try{ mh=modelHash(b,'building',bid); }catch(e){ mh=null; }
    /* الوضع والدوران جزء من الهوية: مبنى تحرّك يُبطل اللقطة ولو لم يتغيّر نموذجه */
    hashes.push({building_id:bid,model_hash:mh,
      position:{x:_coQ(transform.position.x||0),z:_coQ(transform.position.z||0)},
      rotation_deg:_coQ(transform.rotation_deg)});
    disciplines.push({building_id:bid,ARCHITECTURE:!!arch,STRUCTURE:!!struct,
      MEP:!!mep,FLS:!!fls,transform:transform});
    const mine=[];
    _coArchVolumes(arch,transform,bid).forEach(v=>mine.push(v));
    _coStructVolumes(struct,transform).forEach(v=>mine.push(v));
    _coMepVolumes(mep,transform,bid).forEach(v=>mine.push(v));
    _coFlsVolumes(fls,transform).forEach(v=>mine.push(v));
    mine.forEach(v=>{ v.building_id=bid; volumes.push(v); });
    _coPenetrations(mep,arch,struct,bid,transform).forEach(p=>pens.push(p));
    _coSemanticConflicts(bid,arch,struct,mep,fls).forEach(s=>semantic.push(s)); });
  volumes.sort((a,b)=>_scmp(String(a.building_id),String(b.building_id))
    ||_scmp(String(a.discipline),String(b.discipline))
    ||_scmp(String(a.kind),String(b.kind))
    ||_scmp(String(a.element_id),String(b.element_id)));

  const openings={};
  volumes.forEach(v=>{ if(v.kind==='ARCH_OPENING') openings[v.element_id]=v; });
  const bp=coordBroadPhase(volumes), pairs=bp[0], gstats=bp[1];
  const clashes=[], clearance=[], suppressed=[], seenSource={};
  pairs.forEach(pr=>{
    const a=volumes[pr[0]], b=volumes[pr[1]];
    const ex=_coExempt(a,b,pens,openings);
    const inter=_coAabbOverlap(a.aabb,b.aabb);
    if(ex){
      if(inter) suppressed.push({exemption:ex,element_a:a.element_id,element_b:b.element_id});
      if(ex==='SAME_SOURCE_ELEMENT'&&a.element_id!==b.element_id){
        const key=String(a.source_ref);
        if(!Object.prototype.hasOwnProperty.call(seenSource,key)){
          seenSource[key]=true;
          clashes.push(_coMk('DUPLICATE_OCCUPANCY',a,b,
            {kind:'shared_source_element',source_ref:a.source_ref},
            'the same underlying element is represented twice; no clash is reported for it')); } }
      return; }
    if(inter===null){
      const cl=_coClearance(a,b);
      if(cl!==null) clearance.push(cl);
      return; }
    if(!_coObbOverlap(a.obb,b.obb)) return;
    const pe=_coPenExempt(a,b,pens,inter), penEx=pe[0], pen=pe[1], cov=pe[2];
    if(penEx){ suppressed.push({exemption:penEx,element_a:a.element_id,element_b:b.element_id,
        penetration:pen.penetration_id}); return; }
    if(pen!==null&&pen!==undefined&&cov===false){
      clashes.push(_coMk('PENETRATION_UNRESOLVED',a,b,inter,
        'a penetration is declared for this crossing but does not cover it; nothing is '+
        'created or moved',pen.penetration_id));
      return; }
    if(_coHostKind(a,b)==='arch')
      clashes.push(_coMk('OPENING_REQUIRED',a,b,inter,
        'a route crosses this host with no represented penetration; this is a coordination '+
        'finding, not an instruction, and no opening is created'));
    else
      clashes.push(_coMk('HARD_CLASH',a,b,inter,
        'a real volume intersection in resolved world coordinates; nothing is moved, '+
        'resized or rerouted')); });

  const outClashes=clashes.concat(clearance).concat(semantic.map(s=>_coMkSemantic(s)));
  outClashes.forEach(c=>{ c.severity=coordSeverityOf(c.type); });
  outClashes.sort((a,b)=>(COORD_SEVERITIES.indexOf(a.severity)-COORD_SEVERITIES.indexOf(b.severity))
    ||_scmp(String(a.type),String(b.type))
    ||_scmp(String(a.element_a),String(b.element_a))
    ||_scmp(String(a.element_b),String(b.element_b)));
  const mh=(hashes.length===1)?hashes[0].model_hash:null;
  const ph=sha256Hex(_coCanon(_coProjectKey(hashes)));
  const snap={schema:COORD_SCHEMA,detector_version:COORD_DETECTOR_VERSION,
    created_at:(at===undefined)?null:at,model_hashes:hashes,revision_hash:mh,
    project_hash:ph,snapshot_id:'coord_'+(mh?mh.slice(0,16):ph.slice(0,16)),
    disciplines:disciplines,clashes:outClashes,penetrations:pens,
    clearance_issues:outClashes.filter(c=>c.type==='CLEARANCE_CLASH'),
    semantic_conflicts:outClashes.filter(c=>c.type==='SEMANTIC_CONFLICT'
      ||c.type==='INVALID_REFERENCE'),
    suppressed:suppressed.slice().sort((a,b)=>_scmp(String(a.exemption),String(b.exemption))
      ||_scmp(String(a.element_a),String(b.element_a))
      ||_scmp(String(a.element_b),String(b.element_b))),
    statistics:{elements:volumes.length,candidate_pairs:pairs.length,
      grid_cells:gstats.cells,grid_cell_m:COORD_CELL,
      oversized_elements:gstats.oversized_elements,busiest_cell:gstats.busiest_cell,
      suppressed_by_exemption:suppressed.length},
    meta:{note:ACS_COORD_SPEC.note,derivation:ACS_COORD_SPEC.derivation_note,
      navigation_impact:ACS_COORD_SPEC.navigation_note,
      broad_phase:ACS_COORD_SPEC.broad_phase,narrow_phase:ACS_COORD_SPEC.narrow_phase,
      compliance:'NOT_EVALUATED'}};
  snap.summary=coordSummary(snap);
  return snap; }

function _coMk(ctype,a,b,evidence,note,penetration){
  let da=a.discipline, db=b.discipline, ea=a.element_id, eb=b.element_id;
  if(_scmp(da,db)>0||(da===db&&_scmp(String(ea),String(eb))>0)){
    const t=a; a=b; b=t; const td=da; da=db; db=td; const te=ea; ea=eb; eb=te; }
  const c={id:_coClashId(ctype,da,ea,db,eb),type:ctype,
    discipline_a:da,element_a:ea,kind_a:a.kind,
    discipline_b:db,element_b:eb,kind_b:b.kind,
    building_a:(a.building_id===undefined)?null:a.building_id,
    building_b:(b.building_id===undefined)?null:b.building_id,
    cross_building:a.building_id!==b.building_id,
    geometry:{aabb_a:a.aabb,aabb_b:b.aabb,intersection:evidence},
    level_index:(a.level_index!==null&&a.level_index!==undefined)?a.level_index
      :((b.level_index===undefined)?null:b.level_index),
    status:'OPEN',note:note,
    evidence:{kind:'geometry',detector_version:COORD_DETECTOR_VERSION}};
  const fb=[a,b].filter(e=>['model','imported','stated'].indexOf(e.geometry_source)<0
    &&e.geometry_source!==null&&e.geometry_source!==undefined).map(e=>e.element_id);
  c.geometry_confidence=fb.length?'display_fallback':'stated';
  c.evidence.geometry_source_a=(a.geometry_source===undefined)?null:a.geometry_source;
  c.evidence.geometry_source_b=(b.geometry_source===undefined)?null:b.geometry_source;
  if(fb.length){
    c.evidence.fallback_geometry=fb.slice().sort(_scmp);
    c.evidence.confidence_note='at least one side is sized from a display fallback, not from '+
      'stated model dimensions; the intersection is reported as found and the fallback is '+
      'never promoted to an engineering dimension'; }
  if(penetration) c.penetration=penetration;
  return c; }

function _coMkSemantic(s){
  return {id:_coClashId(s.type,s.discipline_a,s.element_a,s.discipline_b,s.element_b),
    type:s.type,discipline_a:s.discipline_a,element_a:s.element_a,kind_a:null,
    discipline_b:s.discipline_b,element_b:s.element_b,kind_b:null,
    geometry:null,level_index:null,status:'OPEN',code:s.code,
    detail:(s.detail===undefined)?null:s.detail,
    note:'a reference in one discipline does not resolve in another; this is a coordination '+
         'integrity finding, not a code or safety judgement',
    evidence:s.evidence}; }

/* تعارض خلوص فقط حيث ذُكر خلوص صراحةً — لا خلوص مُخترع إطلاقاً */
function _coClearance(a,b){
  const ord=[[a,b],[b,a]];
  for(let i=0;i<ord.length;i++){
    const x=ord[i][0], y=ord[i][1], cl=x.clearance_m;
    if(cl===null||cl===undefined||cl<=0) continue;
    const grown=[x.aabb[0]-cl,x.aabb[1]-cl,x.aabb[2]-cl,x.aabb[3]+cl,x.aabb[4]+cl,x.aabb[5]+cl];
    const inter=_coAabbOverlap(grown,y.aabb);
    if(inter){
      const c=_coMk('CLEARANCE_CLASH',x,y,inter,
        'an element states a clearance and another element lies inside it; no clearance is '+
        'ever invented and none is applied here');
      c.clearance_m=cl;
      return c; } }
  return null; }
function _coHostKind(a,b){
  const ord=[[a,b],[b,a]];
  for(let i=0;i<ord.length;i++){
    const x=ord[i][0], y=ord[i][1];
    if((x.kind==='ARCH_WALL'||x.kind==='ARCH_SLAB')&&y.kind==='MEP_SEGMENT') return 'arch'; }
  return null; }

/* --------------------------------------- نزاهة اللقطة والمصالحة ------- */
function checkProjectSnapshot(snapshot,entries){
  let now;
  try{
    const cur=(entries||[]).map(ent=>{
      const bid=ent.id||'bld_0', pos=ent.position||{x:0,z:0};
      return {building_id:bid,model_hash:modelHash(ent.building||{},'building',bid),
        position:{x:_coQ(pos.x||0),z:_coQ(pos.z||0)},
        rotation_deg:_coQ(ent.rotation_deg||0)}; });
    now=sha256Hex(_coCanon(_coProjectKey(cur)));
  }catch(e){ return {status:'UNVERIFIABLE',reason:'the project hash could not be computed',
      presented_as_current:false}; }
  const stored=snapshot.project_hash;
  if(stored===null||stored===undefined)
    return {status:'UNVERIFIABLE',reason:'the snapshot carries no project hash',
      presented_as_current:false};
  if(stored!==now)
    return {status:'STALE_MODEL_CHANGED',stored_hash:stored,current_hash:now,
      presented_as_current:false,
      reason:'a model or a building placement changed after this coordination run; its clash '+
             'count is not the current clash count'};
  return {status:'CURRENT',stored_hash:stored,current_hash:now,presented_as_current:true}; }

function checkCoordSnapshot(snapshot,building,buildingId){
  let now;
  try{ now=modelHash(building,'building',buildingId||'bld_0'); }
  catch(e){ return {status:'UNVERIFIABLE',reason:'model hash could not be computed',
      presented_as_current:false}; }
  const stored=snapshot.revision_hash;
  if(stored===null||stored===undefined)
    return {status:'UNVERIFIABLE',reason:'the snapshot carries no model hash',
      presented_as_current:false};
  if(stored!==now)
    return {status:'STALE_MODEL_CHANGED',stored_hash:stored,current_hash:now,
      presented_as_current:false,
      reason:'the model changed after this coordination run; its clash count is not the '+
             'current clash count'};
  return {status:'CURRENT',stored_hash:stored,current_hash:now,presented_as_current:true}; }

/* يصنّف تعارضات لقطتين. RESOLVED_BY_MODEL_CHANGE يعني أنّ الهندسة اختفت */
function coordReconcile(snapA,snapB){
  const a={}, b={};
  ((snapA||{}).clashes||[]).forEach(c=>{a[c.id]=c;});
  ((snapB||{}).clashes||[]).forEach(c=>{b[c.id]=c;});
  const ids={}; Object.keys(a).forEach(k=>{ids[k]=true;}); Object.keys(b).forEach(k=>{ids[k]=true;});
  const out=[];
  Object.keys(ids).sort(_scmp).forEach(cid=>{
    let state;
    const inA=Object.prototype.hasOwnProperty.call(a,cid);
    const inB=Object.prototype.hasOwnProperty.call(b,cid);
    if(inA&&inB) state='PERSISTING';
    else if(inB) state='NEW';
    else state=(['ACKNOWLEDGED','FALSE_POSITIVE','RESOLVED_EXTERNALLY'].indexOf(a[cid].status)>=0)
      ?'OBSOLETE':'RESOLVED_BY_MODEL_CHANGE';
    const src=inB?b[cid]:a[cid];
    out.push({id:cid,state:state,type:src.type,
      discipline_a:src.discipline_a,element_a:src.element_a,
      discipline_b:src.discipline_b,element_b:src.element_b,
      previous_status:inA?a[cid].status:null,
      note:'RESOLVED_BY_MODEL_CHANGE states only that the geometry that produced this '+
           'finding is no longer present'}); });
  const counts={};
  out.forEach(r=>{ counts[r.state]=(counts[r.state]||0)+1; });
  return {detector_version:COORD_DETECTOR_VERSION,
    hash_a:(snapA||{}).revision_hash,hash_b:(snapB||{}).revision_hash,
    results:out,counts:counts,
    note:'no reconciliation state asserts that a change was correct, adequate or engineered'}; }

/* قرار بشري صريح فقط. لا حالة تُغيَّر تلقائياً بناءً على الهندسة */
function coordSetStatus(snapshot,clashId,status,by,at,note){
  if(COORD_CLASH_STATUSES.indexOf(status)<0||status==='OPEN')
    return [false,'STATUS_NOT_ALLOWED',null];
  if(status==='OBSOLETE') return [false,'OBSOLETE_IS_DERIVED_NOT_SET',null];
  const cl=snapshot.clashes||[];
  for(let i=0;i<cl.length;i++){
    if(cl[i].id===clashId){
      cl[i].status=status;
      cl[i].decision={by:(by===undefined)?null:by,at:(at===undefined)?null:at,
        note:(note===undefined)?null:note,
        basis:'explicit human decision; never derived from geometry'};
      return [true,null,cl[i]]; } }
  return [false,'CLASH_NOT_FOUND',null]; }

function coordClashById(snapshot,cid){
  const cl=snapshot.clashes||[];
  for(let i=0;i<cl.length;i++) if(cl[i].id===cid) return cl[i];
  return null; }

function coordFilterClashes(snapshot,opts){
  opts=opts||{};
  return (snapshot.clashes||[]).filter(c=>{
    const pair=[c.discipline_a,c.discipline_b];
    if(opts.discipline_a&&pair.indexOf(opts.discipline_a)<0) return false;
    if(opts.discipline_b&&pair.indexOf(opts.discipline_b)<0) return false;
    if(opts.level_index!==null&&opts.level_index!==undefined&&c.level_index!==opts.level_index)
      return false;
    if(opts.building_id&&[c.building_a,c.building_b].indexOf(opts.building_id)<0) return false;
    if(opts.type&&c.type!==opts.type) return false;
    if(opts.status&&c.status!==opts.status) return false;
    if(opts.severity&&c.severity!==opts.severity) return false;
    return true; }); }

/* بيانات إبراز للتصحيح — لا تغيّر مظهر النموذج الطبيعي إطلاقاً */
function coordDebugView(snapshot,clashId){
  const c=coordClashById(snapshot,clashId);
  if(c===null) return null;
  const g=c.geometry||{}, it=g.intersection;
  return {clash_id:c.id,highlight:[c.element_a,c.element_b],
    isolate:[c.element_a,c.element_b],
    aabb_a:(g.aabb_a===undefined)?null:g.aabb_a,
    aabb_b:(g.aabb_b===undefined)?null:g.aabb_b,
    intersection:(it===undefined)?null:it,
    marker:(!it||!it.min)?null:{cx:_coQ((it.min[0]+it.max[0])/2),cy:_coQ((it.min[1]+it.max[1])/2),
      cz:_coQ((it.min[2]+it.max[2])/2),ex:_coQ(it.max[0]-it.min[0]),
      ey:_coQ(it.max[1]-it.min[1]),ez:_coQ(it.max[2]-it.min[2])},
    note:'debug overlay only — the normal model appearance is never changed and no clash '+
         'geometry is baked into the standard export'}; }

/* تصدير صريح للقطة تنسيق. مشتقّة لا حقيقة نموذج */
function coordExportSnapshot(snapshot){
  return {schema:snapshot.schema,detector_version:snapshot.detector_version,
    revision_hash:snapshot.revision_hash,project_hash:snapshot.project_hash,
    model_hashes:snapshot.model_hashes,snapshot_id:snapshot.snapshot_id,
    created_at:snapshot.created_at,
    clashes:(snapshot.clashes||[]).map(c=>({id:c.id,type:c.type,severity:c.severity,
      status:c.status,discipline_a:c.discipline_a,element_a:c.element_a,
      discipline_b:c.discipline_b,element_b:c.element_b,
      building_a:(c.building_a===undefined)?null:c.building_a,
      building_b:(c.building_b===undefined)?null:c.building_b,
      cross_building:(c.cross_building===undefined)?null:c.cross_building,
      geometry_confidence:(c.geometry_confidence===undefined)?null:c.geometry_confidence,
      geometry:(c.geometry===undefined)?null:c.geometry,
      evidence:(c.evidence===undefined)?null:c.evidence})),
    penetrations:snapshot.penetrations,summary:snapshot.summary,derived:true,
    note:'a derived coordination snapshot; it is never persisted as core model truth and '+
         'never modifies any discipline model'}; }

function coordRuleInputs(snapshot){
  const s=snapshot.summary||coordSummary(snapshot);
  const out={building:{'coordination.clash.count':s.clashes,
    'coordination.issue.exists':s.clashes>0,
    'coordination.penetration.count':s.penetrations,
    'coordination.penetration.exists':s.penetrations>0}};
  COORD_CLASH_TYPES.forEach(t=>{
    out.building['coordination.clash.count_by_type.'+t]=
      Object.prototype.hasOwnProperty.call(s.by_type,t)?s.by_type[t]:0; });
  return out; }

function coordSummary(snapshot){
  const cl=snapshot.clashes||[];
  const byType={}, byPair={}, byStatus={}, byConf={}, byExempt={};
  cl.forEach(c=>{
    byType[c.type]=(byType[c.type]||0)+1;
    const k=[c.discipline_a,c.discipline_b].slice().sort(_scmp).join(' ↔ ');
    byPair[k]=(byPair[k]||0)+1;
    byStatus[c.status]=(byStatus[c.status]||0)+1;
    const gc=c.geometry_confidence||'not_applicable';
    byConf[gc]=(byConf[gc]||0)+1; });
  (snapshot.suppressed||[]).forEach(x=>{ byExempt[x.exemption]=(byExempt[x.exemption]||0)+1; });
  const st=snapshot.statistics||{};
  return {detector_version:snapshot.detector_version,revision_hash:snapshot.revision_hash,
    clashes:cl.length,by_type:byType,by_discipline_pair:byPair,by_status:byStatus,
    by_geometry_confidence:byConf,by_exemption:byExempt,
    errors:cl.filter(c=>c.severity==='ERROR').length,
    warnings:cl.filter(c=>c.severity==='WARNING').length,
    infos:cl.filter(c=>c.severity==='INFO').length,
    penetrations:(snapshot.penetrations||[]).length,
    suppressed_by_exemption:st.suppressed_by_exemption||0,
    elements:st.elements||0,candidate_pairs:st.candidate_pairs||0,
    compliance:'NOT_EVALUATED',
    geometry_confidence_note:'display_fallback means at least one side of the intersection '+
      'is sized from a render fallback rather than a stated model dimension',
    note:'coordination detection and traceability only — no auto-fix, no rerouting, '+
         'no redesign, no code compliance and no safety claim'}; }
/* ==================================================================
   المرحلة 2 — أساس: سجل برامج أنواع المباني (نسخة مطابقة لـ acs_programs.json).
   يفرض التطابقَ اختبارُ الانحراف في مجموعة الاختبارات، فالمصدر يبقى واحداً.
   البرنامج إرشادي: مفردات + تصنيفات فراغات. ليس محرّكاً ولا يفرض متطلّبات
   ولا يدّعي مطابقة أي كود. النواة (هندسة/أدوار/فراغات/عناصر) تبقى عامّة.
   ================================================================== */
const ACS_INDUSTRIAL = ['warehouse','industrial','factory','logistics'];
const ACS_PROGRAMS = [
 {id:'residential',domain:'generic',categories:'residential',
  strong:['سكني','residential'],
  weak:['مجلس','غرفة نوم','غرف نوم','مطبخ','حمام','صالة','دورة مياه','بلكونة','خادمة','bedroom','kitchen','living room']},
 {id:'villa',domain:'generic',categories:'residential',
  strong:['فيلا','villa','قصر'], weak:['دورين','ملحق','مسبح','حوش','مجلس رجال','مجلس نساء']},
 {id:'apartment',domain:'generic',categories:'residential',
  strong:['عمارة','عمارة سكنية','شقق','apartment','شقة','مبنى سكني'],
  weak:['دور متكرر','أدوار متكررة','وحدات سكنية','unit']},
 {id:'hotel',domain:'generic',categories:'hospitality',
  strong:['فندق','hotel','نزل','شقق فندقية'],
  weak:['لوبي','غرفة نزلاء','غرف نزلاء','أجنحة','جناح','استقبال','housekeeping','guest room','suite']},
 {id:'resort',domain:'generic',categories:'hospitality',
  strong:['منتجع','resort','قرية سياحية'], weak:['شاليه','شاليهات','نادي','مسبح','spa','سبا']},
 {id:'office',domain:'generic',categories:'workplace',
  strong:['مبنى مكاتب','office building','برج مكاتب','coworking','مقر إداري'],
  weak:['مكاتب مفتوحة','open plan','غرف اجتماعات','قاعة اجتماعات','مكتب إداري']},
 {id:'commercial',domain:'generic',categories:'retail',
  strong:['مبنى تجاري','commercial building'], weak:['محلات','معارض','تجاري']},
 {id:'retail',domain:'generic',categories:'retail',
  strong:['مركز تجاري','mall','متجر','retail','showroom','معرض','سوبرماركت','supermarket'],
  weak:['كاشير','رفوف عرض','واجهة عرض']},
 {id:'restaurant',domain:'generic',categories:'hospitality',
  strong:['مطعم','restaurant','كافيه','مقهى','cafe'], weak:['صالة طعام','مطبخ','بار','dining']},
 {id:'clinic',domain:'generic',categories:'healthcare',
  strong:['عيادة','عيادات','clinic','مركز طبي','مجمع طبي'],
  weak:['غرفة كشف','غرف كشف','مختبر','صيدلية','صالة انتظار','أشعة']},
 {id:'hospital',domain:'generic',categories:'healthcare',
  strong:['مستشفى','hospital','مركز تخصصي'],
  weak:['طوارئ','غرف مرضى','عمليات','عناية مركزة','icu','جناح تنويم']},
 {id:'school',domain:'generic',categories:'education',
  strong:['مدرسة','school','روضة','معهد'],
  weak:['فصل','فصول','صف','مختبر','مكتبة','صالة رياضية','classroom']},
 {id:'university',domain:'generic',categories:'education',
  strong:['جامعة','university','كلية','campus','حرم جامعي'],
  weak:['قاعة محاضرات','مدرج','مختبرات','lecture hall']},
 {id:'government',domain:'generic',categories:'workplace',
  strong:['مبنى حكومي','government building','بلدية','وزارة','إمارة','محكمة'],
  weak:['قاعة جمهور','شباك خدمة','أرشيف']},
 {id:'parking',domain:'generic',categories:'parking',
  strong:['مبنى مواقف','موقف متعدد الأدوار','parking structure','parking garage','كراج'],
  weak:['مواقف','موقف سيارات','رامب','ramp']},
 {id:'mixed_use',domain:'generic',categories:'mixed',
  strong:['متعدد الاستخدامات','mixed use','mixed-use','استخدام مختلط','متعدد الاستعمالات'],
  weak:['تجاري وسكني','محلات وشقق','retail and office']},
 {id:'warehouse',domain:'industrial',categories:'industrial',
  strong:['warehouse','مستودع','مخزن ','لوجست','logistic','fulfil','distribution cent','مركز توزيع',
          'رصيف تحميل','أرصفة تحميل','ارصفة تحميل','dock leveler','loading dock','cross-dock','crossdock',
          'كروس دوك','conveyor','سير ناقل','سيور','wms','amr','agv','pallet rack','رفوف بالتات',
          'بالتات','pallet','forklift','رافعة شوكية','sku','picking zone','منطقة التقاط'],
  weak:['رفوف','تخزين','picking','التقاط','packing','تغليف','dock','أرصفة','فرز','sorting','racking','شحن']},
 {id:'factory',domain:'industrial',categories:'industrial',
  strong:['مصنع','factory','خط إنتاج','production line','ورشة','workshop','معمل'],
  weak:['إنتاج','تجميع','assembly','صيانة']},
 {id:'industrial',domain:'industrial',categories:'industrial',
  strong:['منشأة صناعية','industrial facility'], weak:['صناعي']},
 {id:'logistics',domain:'industrial',categories:'industrial',
  strong:['منشأة لوجستية','logistics facility'], weak:['لوجستي']}
];
const ACS_SPACE_CATEGORIES = {
  residential:['living','sleeping','service','circulation','outdoor'],
  hospitality:['guest','public','back_of_house','service','circulation'],
  healthcare:['clinical','diagnostic','patient','support','administration','circulation'],
  workplace:['work','meeting','public','support','circulation'],
  retail:['sales','storage','public','support','circulation'],
  education:['teaching','labs','public','administration','support','circulation'],
  industrial:['receiving','storage','process','shipping','support','circulation'],
  parking:['parking','circulation','support'],
  mixed:['mixed','circulation','support']
};
function isIndustrialProgram(id){ return ACS_INDUSTRIAL.indexOf(String(id||'').toLowerCase())>=0; }
function programOf(id){ return ACS_PROGRAMS.find(p=>p.id===String(id||'').toLowerCase())||null; }
function spaceCategories(id){ const p=programOf(id); return p?(ACS_SPACE_CATEGORIES[p.categories]||[]).slice():[]; }
/* كشف نوع المبنى من نص المستخدم (نفس منطق الخادم acs_programs.detect_type) */
function detectTypeJS(t){
  t=(t||'').toLowerCase();
  const SW=3, WW=1, IND_MIN=3;
  const sc={};
  for(const p of ACS_PROGRAMS){
    let s=0, first=null;
    for(const k of p.strong){ const i=t.indexOf(k); if(i>=0){ s+=SW; first=(first===null)?i:Math.min(first,i); } }
    for(const k of p.weak){ if(t.indexOf(k)>=0) s+=WW; }
    sc[p.id]={s:s, pos:(first===null?1e6:first)};
  }
  const resScore=Math.max(sc.residential.s, sc.villa.s, sc.apartment.s);
  const pick=list=>{ let b=null;
    for(const id of list){ const c=sc[id]; if(!c.s) continue;
      if(!b||c.s>b.s||(c.s===b.s&&c.pos<b.pos)) b={id:id,s:c.s,pos:c.pos}; }
    return b; };
  const bi=pick(ACS_PROGRAMS.filter(p=>p.domain==='industrial').map(p=>p.id));
  if(bi && bi.s>=IND_MIN && bi.s>resScore) return bi.id;   // حارس: "رفوف تخزين" في بيت ليست مستودعاً
  const bg=pick(ACS_PROGRAMS.filter(p=>p.domain!=='industrial').map(p=>p.id));
  if(bg && bg.s>=SW) return bg.id;
  return 'residential';
}
function quickModel(W,D,nF,nRooms){
  const rooms=[]; const cols=Math.ceil(Math.sqrt(nRooms)); const rw=(W-2)/cols-0.4;
  for(let i=0;i<nRooms;i++){const cxi=i%cols, rzi=Math.floor(i/cols);
    const x=1+cxi*(rw+0.4), z=1+rzi*(rw+0.4);
    rooms.push({id:'room'+(i+1),rect:[x,z,rw,rw],
      doors:[{edge:'N',offset:rw/2,width:0.9,height:2.1}],
      windows:[{edge:'S',offset:rw/2,width:Math.min(rw-1,2),sill:0.9,height:1.5}],
      points:[{type:'light',x:rw/2,z:rw/2},{type:'outlet',x:1,z:0.3},{type:'outlet',x:rw-1,z:0.3},
              {type:'ac',x:rw/2,z:0.2},{type:'smoke',x:rw/2,z:rw/2}]});}
  const levels=[]; for(let i=0;i<nF;i++)levels.push(
    {index:i,name:FLOOR_NAMES['F'+i]||('الدور '+i),template:'typical'});
  return {site:{w:W,d:D},floor_height:3.2,wall_h:3.0,wall_t:0.15,levels,floors:{typical:{rooms}}};
}

/* ========================= المشهد والعرض ========================= */
const app=document.getElementById('app'), statusEl=document.getElementById('status');
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.05;
renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.xr.enabled=true;                       // دعم نظارات VR (Meta Quest عبر WebXR)
app.appendChild(renderer.domElement);

const scene=new THREE.Scene();
/* علامة تصحيح لتقاطع تعارض — كائن مؤقّت في المشهد فقط. لا تدخل النموذج،
   ولا تُخبز في أي تصدير GLB، ولا تُحتسب في أي بصمة مراجعة. */
window.__ACS_ADD_MARKER__=(m)=>{
  try{
    const g=new THREE.Mesh(new THREE.BoxGeometry(Math.max(m.ex,0.02),Math.max(m.ey,0.02),
      Math.max(m.ez,0.02)),
      new THREE.MeshBasicMaterial({color:0xff2d55,transparent:true,opacity:0.55,
        depthTest:false}));
    g.position.set(m.cx,m.cy,m.cz);
    g.name='COORD_DEBUG_MARKER';
    g.userData.acs_debug_only=true;
    g.renderOrder=999;
    scene.add(g);
    return g;
  }catch(e){ return null; } };
window.__ACS_DEL_MARKER__=(g)=>{ try{ if(g&&g.parent) g.parent.remove(g);
  if(g&&g.geometry) g.geometry.dispose(); if(g&&g.material) g.material.dispose(); }catch(e){} };
const pmrem=new THREE.PMREMGenerator(renderer);
scene.environment=pmrem.fromScene(new RoomEnvironment(),0.04).texture;

// سماء واقعية + شمس
const sky=new Sky(); sky.scale.setScalar(45000); sky.name='SKY_DOME';
/* قبّة السماء ليست هندسة قانونية: تسميتها تستبعدها صراحةً من حدود العرض */
scene.add(sky);
const su=sky.material.uniforms; su.turbidity.value=6; su.rayleigh.value=2.2;
su.mieCoefficient.value=0.005; su.mieDirectionalG.value=0.8;
const sun=new THREE.DirectionalLight(0xffffff,2.6); sun.castShadow=true;
sun.shadow.mapSize.set(2048,2048); sun.shadow.bias=-0.0004;
scene.add(sun); scene.add(new THREE.HemisphereLight(0xdfeaff,0x30343d,0.6));
/* ============ تطبيق وضع العرض البصري على المشهد نفسه ============
   لا يغيّر هندسة النموذج ولا يعيد بناءها: يبدّل المواد والرؤية والقصّ فقط،
   ويضيف الأجسام البصرية إلى المشهد لا إلى مجموعة المبنى، فتبقى خارج تصدير
   GLB الهندسي بالبناء نفسه لا بالوعد. */
let VIS_GROUP=null, VIS_ORIGINAL=null, VIS_STATE=null;
function _visColorOf(o){
  if(o.engineering_color) return o.engineering_color;
  const m=VIS_MATERIALS[o.material];
  return m?m.base_color:'#cccccc'; }
function _visRestore(){
  if(VIS_ORIGINAL){ VIS_ORIGINAL.forEach(e=>{
    try{ e.mesh.material=e.material; e.mesh.visible=e.visible; }catch(err){} });
    VIS_ORIGINAL=null; }
  if(VIS_GROUP){ try{ scene.remove(VIS_GROUP);
    VIS_GROUP.traverse(o=>{ if(o.geometry)o.geometry.dispose();
      if(o.material&&o.material.dispose)o.material.dispose(); }); }catch(err){}
    VIS_GROUP=null; }
  try{ renderer.clippingPlanes=[]; }catch(err){}
  VIS_STATE=null; }
function applyVisualMode(mode,opts){
  if(!lastBuilding||!model) return null;
  _visRestore();
  opts=Object.assign({},opts||{},{mode:mode});
  let sc;
  try{ sc=compileVisualScene(lastBuilding,opts.building_id||'bld_0',null,0,opts); }
  catch(e){ return null; }
  /* فهرسة أجسام المشهد بمعرّف العنصر المصدر كي نلوّن الشبكات القائمة كما هي */
  const byId={};
  sc.objects.forEach(o=>{ if(o.source_element_id) byId[o.source_element_id]=o; });
  VIS_ORIGINAL=[];
  const eng=VIS_ENGINEERING_MODES.indexOf(sc.mode)>=0;
  model.traverse(m=>{
    if(!m.isMesh) return;
    VIS_ORIGINAL.push({mesh:m,material:m.material,visible:m.visible});
    const u=m.userData||{};
    const eid=(u.struct&&u.struct.id)||(u.mep&&u.mep.id)||(u.fls&&u.fls.id)||null;
    const o=eid?byId[eid]:null;
    if(o){ try{ m.material=getMat('frame',_visColorOf(o)); }catch(e){} }
    else if(!eng&&/^(WALL|FLOOR|ROOF|DOOR|WINDOW)\|/.test(m.name||'')){
      const slot=/^WALL/.test(m.name)?'wall':(/^FLOOR/.test(m.name)?'floor':'roof');
      const pal=VIS_THEME_PALETTE[sc.presentation.theme]||{};
      const mid=pal[slot];
      const col=(VIS_MATERIALS[mid]||{}).base_color;
      if(col){ try{ m.material=getMat('frame',col); }catch(e){} } }
    /* الدمى: إخفاء السقف وقصّ ما فوق ارتفاع معلن — رؤية فقط، لا هندسة */
    const dh=sc.presentation.dollhouse;
    if(dh&&m.position&&m.position.y>dh.clip_above_m) m.visible=false;
  });
  /* الأجسام البصرية تُضاف إلى المشهد لا إلى المبنى */
  VIS_GROUP=new THREE.Group(); VIS_GROUP.name='VISUAL_ONLY';
  VIS_GROUP.userData.acs_visual_only=true;
  sc.objects.filter(o=>o.visual_only).forEach(o=>{
    const g=o.geometry;
    if(!(g.ex>0&&g.ey>0&&g.ez>0)) return;
    try{
      const mesh=new THREE.Mesh(new THREE.BoxGeometry(g.ex,g.ey,g.ez),
        getMat('frame',_visColorOf(o)));
      mesh.position.set(g.cx,g.cy,g.cz); mesh.rotation.y=g.rot_y;
      mesh.name='VISUAL|'+o.layer+'|'+o.id;
      mesh.userData.acs_visual_only=true;
      mesh.userData.visual={id:o.id,kind:o.kind,layer:o.layer,
        visual_class:o.visual_class||null,material:o.material,
        material_provenance:o.material_provenance};
      VIS_GROUP.add(mesh);
    }catch(e){}
  });
  scene.add(VIS_GROUP);
  /* إضاءة التقديم — طبقة بصرية مستقلّة عن وحدات إنارة MEP */
  const p=VIS_LIGHTING_PARAMS[sc.presentation.lighting_preset];
  try{
    setSun(p.sun_elevation_deg,p.sun_azimuth_deg);
    sun.intensity=p.sun_intensity;
    sun.color.set(p.sun_color);
    sun.castShadow=!!sc.presentation.quality_params.shadows;
    if(sc.presentation.quality_params.shadow_map)
      sun.shadow.mapSize.set(sc.presentation.quality_params.shadow_map,
        sc.presentation.quality_params.shadow_map);
    renderer.toneMapping=(sc.presentation.quality_params.tone_mapping==='aces')
      ?THREE.ACESFilmicToneMapping:THREE.NoToneMapping;
    renderer.toneMappingExposure=sc.environment.exposure;
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,
      sc.presentation.quality_params.pixel_ratio));
  }catch(e){}
  /* القصّ: مستويات قصّ قابلة للعكس، ولا تمسّ الهندسة */
  try{
    const cu=sc.presentation.cutaway;
    if(cu){ renderer.localClippingEnabled=true;
      renderer.clippingPlanes=[new THREE.Plane(
        new THREE.Vector3(cu.normal[0],cu.normal[1],cu.normal[2]),cu.constant_m)]; }
  }catch(e){}
  VIS_STATE={mode:sc.mode,scene_id:sc.scene_id,model_hash:sc.model_hash,
    objects:sc.counts.objects,visual_only:sc.counts.visual_only_objects};
  return {mode:sc.mode,scene_id:sc.scene_id,model_hash:sc.model_hash,
    summary:sc.summary,
    note:'presentation state applied to the existing scene; the model geometry is '+
         'unchanged and no visual object is part of the building group'}; }
function clearVisualMode(){ _visRestore(); return true; }


export { ACS_COORD_SPEC, ACS_INDUSTRIAL, ACS_PROGRAMS, ACS_SPACE_CATEGORIES, ACS_VISUAL_SPEC, COORD_CELL, COORD_CLASH_SEVERITY, COORD_CLASH_STATUSES, COORD_CLASH_TYPES, COORD_DETECTOR_VERSION, COORD_DISCIPLINES, COORD_DISCIPLINE_PAIRS, COORD_ELEMENT_KINDS, COORD_EXEMPTION_KINDS, COORD_GEOMETRY_CONFIDENCE, COORD_RECONCILIATION_STATES, COORD_SCHEMA, COORD_SEVERITIES, COORD_SNAPSHOT_STATUSES, VIS_AI_MAY_CHANGE, VIS_AI_MAY_NOT_CHANGE, VIS_AI_STAGES, VIS_ASSET_CLASSES, VIS_ASSET_LICENSES, VIS_CAMERA_DEFAULTS, VIS_CAMERA_PRESETS, VIS_COMPILER_VERSION, VIS_CONTROL_BUFFERS, VIS_CUTAWAY_METHODS, VIS_DECORATION_CLASS, VIS_DECORATION_KINDS, VIS_DEFAULT_LIGHTING, VIS_DEFAULT_QUALITY, VIS_DEFAULT_THEME, VIS_DRIFT_CODES, VIS_DRIFT_SEVERITIES, VIS_DRIFT_SEVERITY, VIS_ELEVATION_FACES, VIS_ENGINEERING_MODES, VIS_ENG_PALETTE, VIS_ENTOURAGE_CLASS, VIS_GROUP, VIS_LANDSCAPE_CLASS, VIS_LAYERS, VIS_LIGHTING_PARAMS, VIS_LIGHTING_PRESETS, VIS_LOD_LEVELS, VIS_MATERIALS, VIS_MATERIAL_CLASS, VIS_MODES, VIS_MODE_LAYERS, VIS_ORIGINAL, VIS_ORTHO_MODES, VIS_PLAN_STYLES, VIS_PRESENTATION_KEY, VIS_PRESENTATION_MODES, VIS_PROVENANCE, VIS_QUALITY_PARAMS, VIS_QUALITY_PROFILES, VIS_RENDER_AUTHORITY, VIS_RENDER_KINDS, VIS_SCHEMA, VIS_SECTION_AXES, VIS_SNAPSHOT_DEFAULTS, VIS_SNAPSHOT_FORMATS, VIS_SNAPSHOT_MAX_PX, VIS_STATE, VIS_THEMES, VIS_THEME_PALETTE, VIS_VALIDATION_CODES, VIS_WATER_KINDS, _CO_EPS, _CO_MAX_CELLS, _CO_NON_SOLID, _CO_PAIR_SET, _CO_SEMANTIC_MEP, _CO_SEMANTIC_PARTNER, _CO_SEMANTIC_SOURCE, _VIS_ASSETS, _VIS_ASSET_BY_TYPE, _VIS_ASSET_INDEX, _VIS_DECOR_BY_NAME, _VIS_EPS, _VIS_FACE_AXIS, _coAabbOf, _coAabbOverlap, _coArchVolumes, _coCanon, _coCellSpan, _coCells, _coClashId, _coClearance, _coExempt, _coFixed, _coFlsVolumes, _coFmt6, _coGsrc, _coHostKind, _coIndexAabb, _coMepVolumes, _coMk, _coMkSemantic, _coNum, _coObb, _coObbOverlap, _coPenCovers, _coPenExempt, _coPenetrations, _coProj, _coProjectKey, _coQ, _coRefStr, _coRefStr1, _coRot, _coSegBox, _coSemanticConflicts, _coStructVolumes, _coVol, _vArchObjects, _vAssetFor, _vAssign, _vBboxOf, _vCamera, _vCanon, _vCounts, _vCutaway, _vDecorKinds, _vDecorationObjects, _vDisciplineObjects, _vDollhouse, _vEntourageObjects, _vFitDistance, _vFlsObjects, _vLandscapeObjects, _vLight, _vLights, _vMode, _vNum, _vObj, _vQ, _vQuality, _vRequestedBuffers, _vRoofCap, _vRot, _vSeg, _vSha16, _vSiteObjects, _vSort, _vStyle, _vTheme, _vVal, _vWaterObjects, _vWorld, _visColorOf, _visRestore, app, applyVisualMode, checkCoordSnapshot, checkProjectSnapshot, clearVisualMode, compileCoordination, compileProjectCoordination, compileVisualScene, coordBroadPhase, coordClashById, coordDebugView, coordExportSnapshot, coordFilterClashes, coordReconcile, coordRuleInputs, coordSetStatus, coordSeverityOf, coordSummary, detectTypeJS, isIndustrialProgram, pmrem, programOf, quickModel, renderer, scene, sky, spaceCategories, statusEl, su, sun, visAiEnhancementRequest, visAssetById, visAssetLibrary, visCheckConsistency, visCheckRenderCurrency, visControlBuffers, visElevation, visExportScene, visFloorPlan, visFrameCamera, visGeometrySignature, visInstancingPlan, visLodPlan, visMaterial, visObjectById, visObjectsByLayer, visPresentationBlock, visRenderMetadata, visRuleInputs, visSection, visSetLayerVisible, visSnapshotRequest, visSummary, visValidateAsset, visValidateScene };
