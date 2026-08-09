# Phase 9 — Production Verification Checklist

Run this manually after deploying. Record every row as **PASS**, **FAIL** or **NV**
(not verified). Do not mark PASS from inspection — perform the action.

Frontend: `https://sprightly-selkie-d906c3.netlify.app`
Backend: `https://acs-engine.onrender.com`

---

## A. Deploy landed

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| A1 | Open the newest Netlify deploy log | `bash tools/netlify-build.sh` ran and printed `✓ vendoring complete` | ☐ |
| A2 | Confirm the publish directory in the log | `public` | ☐ |
| A3 | Open the site root | The application loads; no blank page | ☐ |
| A4 | Hard reload (Ctrl/Cmd + Shift + R) | Same result; no stale cached bundle | ☐ |
| A5 | `curl -s https://acs-engine.onrender.com/health` | HTTP 200, JSON including `"key": true` (the boolean only — never the key) | ☐ |
| A6 | Open the Render deploy log | Docker build succeeded; `uvicorn acs_understand_api:app` running | ☐ |

## B. Runtime libraries actually served

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| B1 | DevTools ▸ Network, reload | `vendor/three@0.160.0/build/three.module.js` returns 200 from the site's own origin | ☐ |
| B2 | Same panel | No request goes to any CDN or third-party host | ☐ |
| B3 | Console | No CSP violation | ☐ |
| B4 | Console: `THREE.REVISION` | `"160"` | ☐ |
| B5 | Block all third-party hosts and reload | Application still loads fully | ☐ |

## C. Backend API

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| C1 | `POST /v1/understand` with a villa description | 200 with a model; not a 500 | ☐ |
| C2 | Repeat for a hotel and a clinic | Different, plausible models — the platform is general-purpose | ☐ |
| C3 | CORS preflight from the Netlify origin | Allowed | ☐ |
| C4 | CORS preflight from an unrelated origin | Refused | ☐ |
| C5 | Exceed `ACS_RL_GEN_HOUR` from one client | Rate-limited | ☐ |
| C6 | Inspect responses and Render logs | The API key appears nowhere | ☐ |
| C7 | `POST /v1/edit` | 200 | ☐ |

## D. Existing workspace and authoring (Phases 4–6)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| D1 | Generate or open a project | The 3D workspace opens | ☐ |
| D2 | Walk through the model | Navigation, collision and portals behave | ☐ |
| D3 | Open the authoring panel and rename a space | Commits; a new revision appears in history | ☐ |
| D4 | Undo it | The previous revision is restored | ☐ |
| D5 | Attempt an out-of-bounds edit | Refused with a typed message, not silently clamped | ☐ |

## E. Visualization (Phase 7)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| E1 | Open the VISUALIZE panel | Opens inside the workspace | ☐ |
| E2 | Render a floor plan | A real SVG appears in the viewer | ☐ |
| E3 | Note the model hash before and after | Unchanged — rendering never mutates the model | ☐ |
| E4 | Produce a base 3D render | **The sandbox could not verify this** — confirm WebGL draws the model | ☐ |

## F. BIM exchange (Phase 8)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| F1 | Open the BIM / Exchange panel | Opens with its six controls | ☐ |
| F2 | Export BIM | An export summary with real counts | ☐ |
| F3 | Load `tests/phase8/outputs/villa_glazed_edited.ifc` | Import summary under a **STAGED EXTERNAL BIM** label | ☐ |
| F4 | Compare, accept a proposal, check the hash | Unchanged until an explicit commit | ☐ |
| F5 | Commit through authoring | A new revision in ordinary history | ☐ |
| F6 | Open `tests/phase8/outputs/villa_glazed.ifc` in Revit / ArchiCAD / Solibri | Record what each reads | ☐ |

## G. Documentation workspace (Phase 9)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| G1 | Open the DOCUMENTATION panel | Opens inside the workspace; tree shows Views, Schedules, Quantities, Sheets | ☐ |
| G2 | Inspect the panel for engineering controls | None present — no move wall, resize space, delete, auto-fix or approve | ☐ |
| G3 | Note the model hash shown in the panel | Matches the current project revision | ☐ |

## H. Floor plans, elevations, sections

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| H1 | Create a floor plan for the ground level at 1:100 | A real vector SVG renders in the viewer | ☐ |
| H2 | Inspect the SVG in DevTools | Real `<line>`/`<rect>` elements; no `<image>`; `data-construction-drawing="false"` | ☐ |
| H3 | Compare the plan against the 3D model | Every room, wall, door and window in the drawing exists in the model | ☐ |
| H4 | Create the four elevations | Each shows only represented external openings; the four differ | ☐ |
| H5 | Create a section on x and one on z | Cut elements differ from projected; elements beyond the depth are reported | ☐ |
| H6 | Cut a section through the stair void | The slab is shown open at the void, not continuous | ☐ |
| H7 | Create a detail view | A magnified crop only — no invented layers, fasteners or assemblies | ☐ |
| H8 | Note the model hash after every view | Unchanged throughout | ☐ |

## I. Dimensions and annotations

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| I1 | Create a plan with the full dimension chain | Overall, space and opening dimensions appear | ☐ |
| I2 | Find an element whose value the model does not state | Its dimension reads UNKNOWN — never the render fallback | ☐ |
| I3 | Compare a displayed dimension to the model value | Display rounding only; the exact value is unchanged | ☐ |
| I4 | Look for FFL / SSL / TOS / TOC datum tags | None — only the real level elevation | ☐ |
| I5 | Open a model with no structural grid | No grid lines or bubbles are drawn | ☐ |
| I6 | Add a user note | It is marked user-authored, never model-derived | ☐ |

## J. Schedules

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| J1 | Generate the room schedule | One row per canonical space; zero phantom rooms | ☐ |
| J2 | Generate the door schedule | Nominal width populated; **clear width reads NOT_SPECIFIED** unless the model states it | ☐ |
| J3 | Check fire rating and material columns | NOT_SPECIFIED unless represented — never inferred | ☐ |
| J4 | Generate the window schedule | Every row maps to a represented opening | ☐ |
| J5 | On a model with structure, generate the column schedule | Unknown sections and materials stay unknown | ☐ |
| J6 | On a model with MEP, generate the equipment schedule | No CFM, flow, pressure or capacity is generated | ☐ |
| J7 | On a model with FLS, generate the device schedule | No coverage, compliance or adequacy wording anywhere | ☐ |

## K. Quantity report

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| K1 | Generate quantities | Room, door, window and level counts match the model | ☐ |
| K2 | Check a discipline with no data | Coverage reads NOT_AVAILABLE — not zero | ☐ |
| K3 | Check a model with unrouted MEP | Segment length reads PARTIAL — unrouted excluded, not estimated | ☐ |
| K4 | Look for cost, rate, price or currency | None anywhere | ☐ |
| K5 | Read the report's own wording | States it is not a bill of quantities and not a cost estimate | ☐ |

## L. Sheets and export

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| L1 | Compose an A3 sheet with two viewports | Both place at their declared coordinates | ☐ |
| L2 | Deliberately overlap two viewports | The collision is reported; **nothing is silently moved** | ☐ |
| L3 | Try to set the status to APPROVED_FOR_CONSTRUCTION | Refused | ☐ |
| L4 | Inspect the title block | Unknown fields blank; no company, engineer, stamp or signature | ☐ |
| L5 | Export SVG | Downloads and opens in a browser and a vector editor | ☐ |
| L6 | Export PDF | Opens in a PDF reader; correct page count; A3 page size; drawing visible | ☐ |
| L7 | Export the JSON documentation package | Contains views, sheets, schedules, quantities and the model hash | ☐ |
| L8 | Try an export filename `../escape.svg` | Refused | ☐ |

## M. Staleness and regeneration

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| M1 | With documentation open, edit the model through authoring | Every existing artifact turns **out of date** | ☐ |
| M2 | Observe whether anything regenerates itself | Nothing does — regeneration is explicit | ☐ |
| M3 | Press Regenerate | A new documentation revision; the previous one is preserved | ☐ |
| M4 | Compare the regenerated drawing | Reflects the geometric change | ☐ |

## N. Cross-cutting

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| N1 | Console, whole session | No new uncaught error | ☐ |
| N2 | Perform every documentation action above, then compare the model hash to the start | **Identical** — only an explicit authoring commit changes it | ☐ |
| N3 | Resize to 360, 390 and 430 px | Every panel usable; controls meet the touch target | ☐ |
| N4 | Switch to Arabic | `dir="rtl"`; the panel is Arabic; **the drawing is not mirrored** | ☐ |
| N5 | Compare a drawing before and after the language switch | Byte-identical geometry | ☐ |
| N6 | Switch back to English | `dir="ltr"`; full documentation state intact | ☐ |
| N7 | Enter a room name containing `<b>bold</b>` or `__proto__` | Rendered as escaped text; nothing executes | ☐ |
| N8 | Open the exported SVG and PDF in an external viewer | Both open correctly and show the drawing | ☐ |

## O. Recording template

```
Deployed commit:
Netlify deploy id:            Render deploy id:
Date:                         Tester:

A1 __  A2 __  A3 __  A4 __  A5 __  A6 __
B1 __  B2 __  B3 __  B4 __  B5 __
C1 __  C2 __  C3 __  C4 __  C5 __  C6 __  C7 __
D1 __  D2 __  D3 __  D4 __  D5 __
E1 __  E2 __  E3 __  E4 __
F1 __  F2 __  F3 __  F4 __  F5 __  F6 __
G1 __  G2 __  G3 __
H1 __  H2 __  H3 __  H4 __  H5 __  H6 __  H7 __  H8 __
I1 __  I2 __  I3 __  I4 __  I5 __  I6 __
J1 __  J2 __  J3 __  J4 __  J5 __  J6 __  J7 __
K1 __  K2 __  K3 __  K4 __  K5 __
L1 __  L2 __  L3 __  L4 __  L5 __  L6 __  L7 __  L8 __
M1 __  M2 __  M3 __  M4 __
N1 __  N2 __  N3 __  N4 __  N5 __  N6 __  N7 __  N8 __
```

Declare **PRODUCTION VERIFIED** only when every row is PASS or an explicit
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`, with no known defect.
Keep `claude-sonnet-5` unchanged unless verified against official Anthropic
documentation or the live API.
