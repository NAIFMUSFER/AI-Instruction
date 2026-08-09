# Production Verification Checklist

**For the repository as it stands at the end of Phase 8.**
Run this manually after deploying. Record every row as **PASS**, **FAIL**, or
**NV** (not verified). Do not mark PASS from inspection — perform the action.

Frontend: `https://sprightly-selkie-d906c3.netlify.app`
Backend: `https://acs-engine.onrender.com`

> Phase 9 has not been implemented. Rows for a Documentation workspace, floor-plan/section/
> elevation sheet generation, schedules, quantity reports and a sheet/export panel are **not**
> in this checklist, because those features do not exist in this build. They will be added to
> `PHASE9-PRODUCTION-VERIFICATION.md` when Phase 9 is specified and built.

---

## A. Deploy landed

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| A1 | Open the Netlify deploy log for the newest deploy | `bash tools/netlify-build.sh` ran and printed `✓ vendoring complete` | ☐ |
| A2 | Confirm the publish directory in the log | `public` | ☐ |
| A3 | Open the site root | The application loads; no blank page | ☐ |
| A4 | Hard reload (Ctrl/Cmd + Shift + R) | Same result; no stale cached bundle | ☐ |
| A5 | `curl -s https://acs-engine.onrender.com/health` | HTTP 200 with a JSON body including `"key": true` (the boolean only — never the key itself) | ☐ |
| A6 | Open the Render deploy log | Docker build succeeded; `uvicorn acs_understand_api:app` is running | ☐ |

## B. Runtime libraries actually served (this is what the sandbox could not verify)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| B1 | Open DevTools ▸ Network, reload | `vendor/three@0.160.0/build/three.module.js` returns 200 from the site's own origin | ☐ |
| B2 | Same panel | No request goes to any CDN or third-party host | ☐ |
| B3 | Console | No CSP violation is reported | ☐ |
| B4 | Console: `THREE.REVISION` | `"160"` | ☐ |
| B5 | Block all third-party hosts in DevTools and reload | Application still loads fully | ☐ |

## C. Backend API

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| C1 | `POST /v1/understand` with a villa description | 200 with a model; not a 500 | ☐ |
| C2 | Repeat for a hotel and a clinic description | Different, plausible models — the platform is general-purpose, not warehouse-specific | ☐ |
| C3 | CORS preflight from the Netlify origin | Allowed | ☐ |
| C4 | CORS preflight from an unrelated origin | Refused | ☐ |
| C5 | Exceed `ACS_RL_GEN_HOUR` from one client | Rate-limited, not served | ☐ |
| C6 | Inspect any response body and the Render logs | The API key appears nowhere | ☐ |
| C7 | `POST /v1/edit` | 200 | ☐ |

## D. Existing workspace (Phases 4–6)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| D1 | Generate or open a project | The 3D workspace opens | ☐ |
| D2 | Walk through the model | Navigation, collision and portals behave | ☐ |
| D3 | Open the authoring panel and rename a space | The change commits and a new revision appears in history | ☐ |
| D4 | Undo it | The previous revision is restored | ☐ |
| D5 | Attempt an out-of-bounds edit | Refused with a typed message, not silently clamped | ☐ |

## E. Visualization (Phase 7)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| E1 | Open the VISUALIZE panel | It opens inside the workspace | ☐ |
| E2 | Render a floor plan | A real SVG appears in the viewer | ☐ |
| E3 | Render an elevation and a section | Both draw; openings shown exist in the model | ☐ |
| E4 | Note the model hash before and after | Unchanged — rendering never mutates the model | ☐ |
| E5 | Produce a base 3D render | **The sandbox could not verify this** — confirm here that WebGL draws the model | ☐ |
| E6 | If an AI provider key is configured, run an enhancement | The drift detector classifies the result; a rejected image is never presented as model-faithful | ☐ / NV |

## F. BIM exchange (Phase 8)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| F1 | Open the BIM / Exchange panel | It opens; six controls present (Import, Export, Validate, Compare, Proposals, Round-trip) | ☐ |
| F2 | Export BIM | An export summary renders with real object, level and space counts | ☐ |
| F3 | Load `tests/phase8/outputs/villa_glazed_edited.ifc` as an import | The import summary renders under a **STAGED EXTERNAL BIM** label with real entity counts | ☐ |
| F4 | Note the model hash | Unchanged by loading, validating and comparing | ☐ |
| F5 | Click Compare | Difference entries render | ☐ |
| F6 | Click Proposals | Proposals render, each with Accept and Reject | ☐ |
| F7 | Accept one, then check the model hash | Still unchanged — acceptance alone writes nothing | ☐ |
| F8 | Click "Commit accepted through authoring" | A new revision appears in ordinary revision history and the hash changes | ☐ |
| F9 | Open `tests/phase8/outputs/villa_glazed.ifc` in Revit, ArchiCAD or Solibri | It opens; record level, space, wall, door and window counts | ☐ |
| F10 | Run the buildingSMART IFC4 validator (or `ifcopenshell`) on the same file | Record every reported issue verbatim | ☐ |
| F11 | Export a real IFC4 file from Revit and import it here | Staged with its schema, units, counts and unsupported entities reported; the whole file is not refused | ☐ |

> **F9–F11 are the only route to any `INTEROP_VERIFIED` claim.** The build sandbox has no
> network and no independent IFC implementation, so the current report states
> `INTEROP_VERIFIED: none`. Do not upgrade that claim without recording F9–F11.

## G. Cross-cutting

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| G1 | Console, whole session | No new uncaught error | ☐ |
| G2 | Perform every read-only operation above, then compare the model hash to the start | Identical — only an explicit authoring or import commit changes it | ☐ |
| G3 | Resize to 360, 390 and 430 px | Every panel is usable; controls meet the touch target | ☐ |
| G4 | Switch to Arabic | `dir="rtl"`; layout mirrors; panel state survives | ☐ |
| G5 | Switch back to English | `dir="ltr"`; the full configuration is intact | ☐ |
| G6 | Export a JSON model and a GLB | Both download and open | ☐ |
| G7 | Export an IFC file and reopen it in the panel | Round-trip summary reports PASS or a stated WARNING with the reason | ☐ |

## H. Recording template

```
Deployed commit:
Netlify deploy id:            Render deploy id:
Date:                         Tester:

A1 __  A2 __  A3 __  A4 __  A5 __  A6 __
B1 __  B2 __  B3 __  B4 __  B5 __
C1 __  C2 __  C3 __  C4 __  C5 __  C6 __  C7 __
D1 __  D2 __  D3 __  D4 __  D5 __
E1 __  E2 __  E3 __  E4 __  E5 __  E6 __
F1 __  F2 __  F3 __  F4 __  F5 __  F6 __  F7 __  F8 __  F9 __  F10 __  F11 __
G1 __  G2 __  G3 __  G4 __  G5 __  G6 __  G7 __
```

Declare **PRODUCTION VERIFIED** only when every row is PASS or an explicit
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`, with no known defect.
Keep `claude-sonnet-5` unchanged unless verified against official Anthropic documentation or
the live API.
