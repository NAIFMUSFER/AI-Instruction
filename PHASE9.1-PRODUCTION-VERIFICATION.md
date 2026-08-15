# Phase 9.1 — Production Verification Checklist (§28)

Run this manually after deploying. Record every row as **PASS**, **FAIL** or **NV**
(not verified). Do not mark PASS from inspection — perform the action.

Frontend: `https://sprightly-selkie-d906c3.netlify.app`
Backend: `https://acs-engine.onrender.com`

---

## A. Deploy landed

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| A1 | Open the newest Netlify deploy log | `bash tools/netlify-build.sh` ran; vendoring complete; the 8 postprocessing/shader modules verified | ☐ |
| A2 | Open the site root and hard-reload | Application loads; no blank page; no stale bundle | ☐ |
| A3 | DevTools ▸ Network | Every request is same-origin; **no CDN or third-party host**; no CSP violation in Console | ☐ |

## B. Visual quality layer

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| B1 | Open the quality panel (الجودة البصرية) | Controls: Quality, Lighting, Materials, Environment, Shadows, AO, Exposure — nothing else | ☐ |
| B2 | Switch Materials to **Realistic**, Lighting **CLEAR_NOON**, Apply | Materials change visibly; status `APPLIED`; console clean | ☐ |
| B3 | Look at a glazed façade in Realistic mode | Glass is transmissive (see-through with refraction), not flat grey | ☐ |
| B4 | Lighting **GOLDEN_HOUR** then **INTERIOR_NIGHT** | Sun warms/lowers; at night the sun contribution is zero and interiors read from fill lighting | ☐ |
| B5 | Quality **HIGH** on a desktop GPU | Sharper shadows (4096 map); AO on; no visible slowdown on a mid-range GPU | ☐ |
| B6 | Quality **ULTRA** manually | Applies only by explicit choice — never auto-selected | ☐ |
| B7 | Each of the 8 camera presets | Deterministic framing; building fully in frame; eye-level at human height | ☐ |
| B8 | Warehouse test model, Realistic + WAREHOUSE lighting | Racks/goods/safety paint read correctly; counts unchanged | ☐ |
| B9 | Multi-storey model, DOLLHOUSE preset | Cutaway presentation works; no geometry missing | ☐ |

## C. Immutability & capture

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| C1 | Note the model hash, apply every profile × several lighting presets, re-read hash | **Identical** — the visual layer never moves the model | ☐ |
| C2 | Screenshot button | PNG downloads; metadata shows camera preset, quality profile, model hash, `PRESENTATION_OUTPUT`, `is_engineering_evidence: false` | ☐ |
| C3 | Switch back to Engineering materials | Original appearance returns exactly (reversible) | ☐ |

## D. Degradation

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| D1 | Mid-range phone | HIGH request degrades BALANCED→PERFORMANCE with reported fallback issues; **never a blank viewport** | ☐ |
| D2 | Console on mobile | No errors; page interactive | ☐ |

## E. Reference captures (§25)

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| E1 | On a networked machine: `sh tools/vendor.sh && node tests/phase9_1/capture_reference.js` | 8 before/after pairs + `reference_metadata.json` in `tests/phase9_1/outputs/reference/`; every scene reports canonical bounds unchanged | ☐ |

## F. Backend untouched

| # | Action | Expected result | Result |
| --- | --- | --- | --- |
| F1 | `curl -s https://acs-engine.onrender.com/health` | HTTP 200 — Phase 9.1 changed nothing behind it | ☐ |

Sandbox status: every row above is **NV — EXTERNAL ENVIRONMENT REQUIRED** until executed
on the deployed site.
