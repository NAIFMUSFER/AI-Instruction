# Phase 9.2 — Production Verification Checklist (§52)

Run this manually after deploying. Record every row as **PASS**, **FAIL** or
**NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. Do not mark PASS from inspection —
perform the action.

Frontend: `https://sprightly-selkie-d906c3.netlify.app`
Backend: `https://acs-engine.onrender.com`

## A. Deploy landed

| # | Action | Expected | Result |
| --- | --- | --- | --- |
| A1 | Newest Netlify deploy log | `bash tools/netlify-build.sh` ran; publish `public`; base empty | ☐ |
| A2 | DevTools ▸ Network on load | every asset same-origin; **no CDN**; no CSP violation; no console errors | ☐ |

## B. Architectural mode

| # | Action | Expected | Result |
| --- | --- | --- | --- |
| B1 | Open the architectural panel (العرض المعماري) | Detail/Façade/Context/Staging/Camera/diagnostic — nothing else | ☐ |
| B2 | Detail **Standard**, Façade **Requested appearance**, request «واجهة حجر بيج», Apply | exterior walls read as beige stone; the SAME building, same dimensions | ☐ |
| B3 | Look at any window | dark aluminum frame + sill around the same opening; reflective/transmissive glazing | ☐ |
| B4 | Request «إنارة LED مخفية», Apply | warm strips on represented façade edges only; no MEP schedule entry anywhere | ☐ |
| B5 | Context **Site** then **Landscape** | paving/path planes appear, then instanced trees around the site; toggling back removes them completely | ☐ |
| B6 | Compare **E / P / A** buttons (§37) | Engineering ↔ PBR ↔ Architectural over the identical model and camera | ☐ |
| B7 | Engineering mode after everything | the original engineering appearance returns exactly | ☐ |

## C. PBR + models

| # | Action | Expected | Result |
| --- | --- | --- | --- |
| C1 | 9.1 quality panel still works | profiles/lighting/materials/exposure as before — no regression | ☐ |
| C2 | Warehouse model, Detail Standard | racks/cartons/forklifts read as their categories; WAREHOUSE_OVERVIEW camera frames all | ☐ |
| C3 | Apartment building | balconies enhanced; stone + gray differentiation where safely resolvable; roofline readable | ☐ |
| C4 | Hotel and clinic | auto presentation picks hero/golden-hour and front/studio-day respectively | ☐ |
| C5 | Staging **Presentation** on an empty room | additions appear, flagged presentation; **quantities and schedules unchanged** | ☐ |

## D. Integrity

| # | Action | Expected | Result |
| --- | --- | --- | --- |
| D1 | Note model hash → apply every detail/context/staging combo → re-read | **identical** | ☐ |
| D2 | Visual diagnostic toggle | every request listed with its status; unresolved items named, none dropped | ☐ |
| D3 | Screenshot | PNG with camera preset, quality, detail level, context, staging, coverage, model hash, `is_engineering_evidence: false` | ☐ |
| D4 | Mobile mid-range phone | HIGH→STANDARD degradation reported; never a blank viewport; console clean | ☐ |

## E. Reference captures (§48)

| # | Action | Expected | Result |
| --- | --- | --- | --- |
| E1 | Networked machine: `sh tools/vendor.sh && node tests/phase9_2/capture_reference_92.js` | villa/apartment/warehouse/hotel/clinic/interior/dollhouse before/after pairs + metadata; canonical bounds unchanged per scene | ☐ |

Sandbox status: every row is **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** until
executed on the deployed site.
