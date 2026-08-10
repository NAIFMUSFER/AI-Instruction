# Phase 9.2 — Final Report

**Architectural Visual Fidelity, Façade Detailing & Presentation Context**
Executed in the build sandbox. Every number below came from a command that was actually
run. Nothing here is projected.

## 1. Architecture

```
CANONICAL MODEL → EXISTING VISUAL COMPILER → EXISTING PBR LAYER
  → ARCHITECTURAL PRESENTATION DETAIL LAYER
  → LIGHTING / ENVIRONMENT / POST PROCESS → VIEWPORT / IMAGE
```

Phase 9.1 was extended, not replaced: one PBR engine, one lighting system, one material
registry per layer, one camera resolver (9.2 presets resolve through it), one quality
pipeline, one screenshot metadata chain, the same immutability machinery. No reverse
arrow. **Result: PASS.**

## 2. Files created or changed

| File | Lines | Status |
| --- | --- | --- |
| `acs_archdetail.json` | ~400 | new — canonical Phase 9.2 spec: 5 detail classes, 4 authority classes, 3 detail profiles, 27 presentation materials, 60+ object kinds, 11 cameras, 4 environments, interpreter keyword map, diagnostic statuses, 18 issue codes, 16 hard-stop boundaries |
| `acs_archdetail.py` | ~700 | new — deterministic layer (zoning, assemblies, LED, staging, recipes, placement, variation, interpreter, diagnostic, coverage, config, capture) |
| `tools/build_archdetail_browser.py` | ~900 | new — idempotent injector: byte-parity JS mirror + panel + bridge |
| `tools/_archdetail_bridge_block.js` | ~330 | new — the only THREE-touching 9.2 code: frames, zoning, LED strips, context/landscape (InstancedMesh), object builders, compare modes, all reversible |
| `tests/phase9_2/lib_ad_fixtures.py` | 120 | new — fixtures A–L incl. apartment-with-balconies model |
| `tests/phase9_2/test_archdetail.py` | ~530 | new — contract + §43/§44 immutability |
| `tests/phase9_2/test_parity.js` + `parity/` | ~330 | new — 26 groups byte-identical |
| `tests/phase9_2/test_archdetail_browser.js` | ~180 | new — panel, graceful path, UI immutability, shipped page |
| `tests/phase9_2/capture_reference_92.js` | ~170 | new — §48 harness, honest exit-2 refusal in-sandbox |
| `tests/phase9_2/run_all.sh` | 100 | new — full gate chaining Phase 9.1 (and thus 1–9) |
| `tests/security/test_security.py` | +S-R1…S-R17 | extended — 365 total |
| `tests/deploy/verify_deploy.py` | +section 11d | extended — 287 total |
| `tests/phase3/lib/build_browser_page.js` | +10 | extended — AD DOM/styles into the harness |
| `PHASE9.2-*.md` ×4 | — | new |

`public/index.html` grew by four marker-fenced generated blocks (JS mirror ≈47 KB,
bridge ≈13 KB, DOM, CSS). The 9.1 render-loop dispatcher stays **single** (asserted);
no engineering block was touched. `tools/netlify-build.sh` unchanged — the layer needs
no new vendored module. Three.js stays pinned at 0.160.0.

## 3. ARCHITECTURAL DETAIL SYSTEM

Profiles DETAIL_OFF (exact 9.1 appearance) / DETAIL_STANDARD (frames + reveals +
zoning + moderate furniture) / DETAIL_HIGH (+ context, stronger AO tie-in); mobile
degrades HIGH→STANDARD with a typed issue; canonical objects never removed; blank
viewport never allowed. Five presentation-detail classes with promotion forbidden.

## 4. FAÇADE SYSTEM

Material zoning on represented exterior walls only (beige stone, plasters, exposed
concrete, gray panel, wood, metal cladding, glass zones); unresolvable accents return
`AD_VISUAL_DETAIL_UNRESOLVED`; visual offsets bounded at 0.06 m; deterministic seeded
variation (model_hash+element_id+material_id — no runtime randomness).

## 5. WINDOW / GLASS SYSTEM

Opening → aluminum frame (proportional 0.045·min(w,h), clamp 0.03–0.09 m, three
finishes) + 9.1 physical glass + sill; opening size/position/count provably unchanged;
assemblies are DERIVED_PRESENTATION_DETAIL with source ids.

## 6. INTERIOR DETAIL

Staging default REQUESTED_ONLY; PRESENTATION_DEFAULT additions explicitly opt-in and
excluded from BIM/quantities/exports/schedules; furniture recipes read as their
categories; kitchens never invent a layout from «L أو U حسب الدور»; bathrooms never gain
fixtures or plumbing.

## 7. CONTEXT / PARKING / LANDSCAPE

Site classes CANONICAL/REQUESTED/DEFAULT; no invented boundaries or roads. Parking:
represented bays render professionally, absent bays →
`PARKING_REQUESTED_NOT_GEOMETRICALLY_RESOLVED`, 10-cars-into-6-bays places 6 and
reports 4. Landscape OFF by default, LOD LOW/STANDARD/HIGH, instanced, never enters the
engineering model. Object library: 63 kinds across 6 categories; vehicles and forklifts
with recognizable silhouettes and zero invented attributes (asserted per recipe).

## 8. VISUAL REQUEST DIAGNOSTIC

Interpreter classes SAFE_VISUAL_OVERRIDE / REQUIRES_ENGINEERING_CHANGE / AMBIGUOUS /
UNSUPPORTED over an Arabic/English keyword map («حجر بيج» safe; «بلكونات أكبر»
engineering; hostile text → zero intents). Diagnostic accounts for every request with
`silently_dropped == []` across all 12 fixtures; object ledger per 14J;
`VISUAL_REQUEST_COVERAGE` with no compliance meaning. Visible in the panel via the
diagnostic toggle.

## 9. IMMUTABILITY RESULT

For villa_glazed, hotel, clinic, warehouse and the apartment-balconies model: canonical
bytes re-canonicalized **identical** after 12 config combinations × captures + zoning +
assemblies + LED + staging + recipes + all cameras; hash, revision, arch/struct/MEP/FLS
counts, documentation quantities and floor-object identity unchanged (15 assertions,
all green). Repeated in Chromium through the real panel (36 combos + 3 compare modes).
**PASS.**

## 10. SECURITY RESULT

S-R1…S-R17: no dynamic execution, single blocks, no CDN/scheme in the layer, no remote
texture/filesystem/GLTF/executable assets, prototype-pollution refused, hostile text
and hostile object kinds refused, LED creates no electrical artifact, panel has no
engineering edit control, no false claims, bridge refuses non-read-only configs,
deterministic variation. **365 passed, 0 failed.** Deploy closure 11d: **287 passed, 0
failed.**

## 11. TESTS RUN · ASSERTIONS PASSED / FAILED

`sh tests/phase9_2/run_all.sh --browser` — one chained run, steps 0–10, then repeated
from the fresh-extracted ZIP:

**10,045 passed · 0 failed** across 62 suite summaries — Phase 9.2 contract 168,
parity 7 (26 groups byte-identical), panel Node 4, **Chromium 38 (0 page errors)**,
security 365, deploy 287, plus the full Phase 1–9.1 regression (docs 421/72/85, BIM
526/53/58, PBR 156/7/41, security Chromium 242, and every earlier suite). No test was
weakened, skipped or removed.

## 12. BROWSER VERIFIED

Real Chromium, 5 suites: security 242, BIM 58, docs 85, PBR 41, **arch detail 38** — 0
failures, 0 page errors. Chromium proves: spec byte-identical in the page; the panel
renders, localizes and exposes exactly the declared controls; apply/compare without a
3D runtime refuse with typed `AD_THREE_UNAVAILABLE` while the page stays alive;
canonical bytes identical through 36 UI combinations; single bridges, single
dispatcher, zero network schemes in the extracted layer.

## 13. WEBGL RASTER VERIFIED

**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No vendored Three.js exists in this
sandbox (npm 403), so no pixel was rendered and none is claimed.
`tests/phase9_2/capture_reference_92.js` refused honestly (exit 2) and will produce the
§48 villa/apartment/warehouse/hotel/clinic/interior/dollhouse before/after pairs on a
networked machine.

## 14. NETLIFY BUILD VERIFIED / LIVE PRODUCTION VERIFIED

`bash tools/netlify-build.sh` executed → npm **E403** in-sandbox; `docker info` → no
daemon; live URLs unreachable. All three: **NOT VERIFIED — EXTERNAL ENVIRONMENT
REQUIRED** (attempt logs kept). Deploy verification (287 checks) proves the repo-side
apparatus: Netlify root, build `bash tools/netlify-build.sh`, publish `public`, **no
base directory**, no runtime CDN, Three.js pinned.

## 15. KNOWN LIMITATIONS

1. Raster quality (stone as pixels, frames, LED glow, reflections) requires the real
   deployment — checklist in `PHASE9.2-PRODUCTION-VERIFICATION.md`.
2. Two-point perspective: NOT IMPLEMENTED (honest §31 decision, documented in-spec).
3. Bridge-level geometric staging places objects only through resolved placements
   (canonical/user/zone); bulk auto-furnishing of rooms is intentionally absent.
4. Façade accent zoning resolves only on represented bands (parapet/base/accent
   groups); models without such surfaces report UNRESOLVED by design.
5. Landscape/context objects are lightweight parametric proxies — presentation only,
   never a landscape design.

## 16. HARD STOP

Phase 9.2 ends here per §56. No Phase 10, no cloud accounts, no persistence, no
collaboration, no regulatory extensions were started. Awaiting approval.
