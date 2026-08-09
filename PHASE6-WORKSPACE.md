# Phase 6 — Product Workspace & Professional Authoring UI

**Real user workflow. Project tree · Inspector · Viewport · Edit mode · History.
No new engineering engines. No direct model mutation. No AI auto-commit.**

---

## 0. What this phase is, and what it is not

Phases 1–5 built the engines. Phase 6 builds the **product surface** over them, so a
person can do real work without touching a console API:

```
CREATE PROJECT → ENTER REQUIREMENTS → GENERATE MODEL → EXPLORE 3D → SELECT ELEMENT
     → INSPECT PROPERTIES → ENTER EDIT MODE → PREVIEW → COMMIT or CANCEL
     → VIEW WARNINGS → VIEW REVISION HISTORY → EXPORT
```

This phase added **no engineering calculation whatsoever**. Every number the workspace
shows is read from an existing compiler output or from the canonical model. Every change
the workspace makes goes through the Phase 5 authoring command path — the interface has
no second implementation of anything.

The platform remains **general purpose**. Warehouse fixtures are test data only; the
workspace is driven from villa, hotel, clinic, office and warehouse models identically,
and the parity suite runs all of them.

---

## 1. The state boundary this phase depends on

Six state classes are declared in `acs_workspace.json` and enforced in code:

| Class | Owner | May enter the model hash |
| --- | --- | --- |
| `UI_STATE` | the workspace | no |
| `RUNTIME_STATE` | Phase 4 runtime | no |
| `AUTHORING_STATE` | Phase 5 authoring | no |
| `ENGINEERING_MODEL` | the canonical model | **yes — and only this** |
| `DERIVED_ANALYSIS` | compilers | no |
| `PRESENTATION_OUTPUT` | exports, references | no |

`model_hash_inputs` is `["model"]` and nothing else. `assert_ui_state_excluded()` proves
at runtime that selection, mode, filters, expansion, language and camera never reach the
hash, and the parity suite checks both implementations agree on that proof.

---

## 2. Files

| File | Role |
| --- | --- |
| `acs_workspace.json` | the canonical workspace specification — state classes, breakpoints, tree kinds, issue categories, editability classes, provenance labels, forbidden words, export kinds, reference kinds, unsafe-reference patterns, interface labels |
| `acs_workspace.py` | the Python implementation of every workspace view model |
| `tools/build_workspace_ui.py` | injects the mirrored JavaScript, the DOM and the styles into `public/index.html` between explicit markers; idempotent |
| `public/index.html` | carries the generated workspace block, DOM and styles |
| `tests/phase6/*` | the verification suites described in §6 |

The specification is the single source of truth. The browser copy is compared to
`acs_workspace.json` byte for byte by a drift test; the two implementations are compared
to each other by the parity suite.

---

## 3. The editing path — there is only one

A change made in the interface travels exactly this route:

```
element selected in the tree or the viewport   (UI_STATE only)
        ↓
operation chosen in the inspector              (offered per element kind)
        ↓
WS.beginPreview(command)   →   auPreviewCommand   →  candidate model + issues
        ↓                       committed model unchanged, byte for byte
preview panel: affected elements, new and resolved warnings, integrity, diff
        ↓  the user presses Commit
auCommitTransaction   →   confirmation digest, warning acknowledgement,
                          revision guard, new revision id
        ↓
derived data rebuilt: architecture, coordination, visual scene, runtime scene
```

There is no other write path. The interface never assigns into the model, never patches
JSON, never skips the preview and never commits on behalf of the assistant.

## 4. Honesty rules the interface holds

- **Unknown stays unknown.** A value absent from the model renders as *Not specified* /
  *غير محدد*, never as `0` and never as a default. The inspector counts them.
- **Derived stays read only.** A derived value carries its class and cannot be edited;
  it changes only when its source changes.
- **Display fallbacks are presentation only** and are labelled as such.
- **No compliance verdict anywhere.** `compliance` is `NOT_EVALUATED` in the inspector,
  in the preview panel and in every export descriptor. `forbidden_status_words` is
  scanned in issue text by an executed test, not by convention.
- **No false coverage.** Requirement coverage reports per class, counts unresolved and
  excluded items separately, and sets `claims_full_coverage: false`.
- **The assistant proposes only.** Every assistant result carries `committed: false` and
  `requires_explicit_confirmation: true`; an unresolvable phrase is refused with
  candidates rather than guessed.
- **Exports certify nothing.** Every descriptor names its revision id and model hash,
  states `certifies_nothing: true`, and marks preview exports as previews.

## 5. Bilingual and responsive behaviour

Interface text lives in `acs_workspace.json` under `ui_labels`, in Arabic and English.
The controller builds its lookup table from that map — there is no second table — and
`renderChrome()` localises the static shell too, so an Arabic session contains no
untranslated English prose and an English session contains no stray Arabic. Two
categories are deliberately **not** translated, and both are asserted explicitly:

- **canonical enum codes** (`VIEW`, `ORBIT`, `NOT_EVALUATED`, `HOSTS_DOOR`, discipline
  and issue-category codes) and **canonical field keys** (`space.area_m2`,
  `lock_reason`), because an engineer needs the specification value verbatim;
- **contract disclosure notes**, which are marked `data-ws-note="canonical" lang="en"`.
  Translating a legal-shaped disclosure risks shifting its meaning, so it is presented in
  one language and flagged in the DOM. This is a **known limitation**, not an oversight.

The layout is verified at 360, 390, 430, 768, 1024, 1440 and 1920 px in real Chromium:
no horizontal page overflow at any width, a usable viewport at every width, touch targets
at or above the declared 44 px minimum below 430 px, and all three panels docked from
1024 px up. Below 768 px the eleven toolbar controls cannot fit at a 44 px touch size, so
the toolbar scrolls horizontally; a test asserts it is genuinely scrollable rather than
clipped, so no control can become unreachable silently.

## 6. Verification

```bash
sh tests/phase6/run_all.sh              # everything except real Chromium
sh tests/phase6/run_all.sh --browser    # adds Chromium, responsive and walkthrough
```

| Suite | What it proves | Result |
| --- | --- | --- |
| `test_workspace.js` | spec integrity, state boundaries, view models | 113 passed |
| `test_workflow.js` | the whole product workflow through the public API | 153 passed |
| `test_dom.js` | the real interface in a real DOM | 197 passed (Chromium) |
| `test_security.js` | malicious names, labels, imports, references, assistant text | 238 passed (Chromium) |
| `test_parity.js` | Python ↔ JavaScript workspace parity | 47 passed |
| `test_responsive.js` | seven widths, RTL, language purity, screenshots | 87 passed |
| `walkthrough.js` | the seventeen-step product walkthrough | 16 PASS, 1 NOT_VERIFIED |
| `tests/security/test_security.py` | backend and configuration security | 166 passed |
| `benchmark_workspace.{js,py}` | measured timings, no FPS or GPU claim | 3 cases each |

Phases 1–5 are re-run unchanged as a regression gate and all pass.

## 7. What is not verified here

- **3D rendering.** This sandbox has no outbound network, so `public/vendor/` is empty
  and Three.js is not loaded. The viewport host is present and correctly sized, and the
  workspace stays fully usable without it, but any claim about rendered pixels, camera
  behaviour or frame rate is reported as
  `NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`.
- **The live backend.** No network; the Render service was not contacted.
- **Screenshot pixel identity.** Screenshots are captured as evidence of layout and
  state, not compared pixel by pixel; `screenshot_note` says so, and a test asserts it.
- **Photorealistic rendering.** The pipeline stages are declared and
  `photorealistic_implemented` is `false`. Nothing pretends otherwise.

## 8. Hard stop

Phase 6 ends here. Cloud collaboration, photorealistic AI rendering, automatic
engineering design, BIM interoperability and autonomous design are **not** started and
require explicit approval.
