# Local canonical roof increment — 11 November 2026

This separate review increment starts at PR190 head `3bc06725203533f59a7e4ec9358b0df4b5c9dff6`. Its prerequisite passed: all31 triggered workflows and all42 jobs, including the complete guest browser suite. See [the individual CI4 jobs](CI4-JOBS.md). Nothing is merged into main, deployed or migrated by this increment.

## Behavior and ownership

New residential/warehouse samples and locally generated buildings receive the same flat, explicit `kind: "roof"` level and disclosed0.9m parapet as `acs_roof.py`. The synchronous JavaScript twin is `public/app/core/roof.mjs`. It changes model data at the local creation/edit boundary; rendering, storage and exports subsequently consume that same model. It does not generate an alternative presentation-only roof.

Only the old hard-coded synthetic roof scaffolding in `EXAMPLE` and `parseDescription` is removed. Its rooftop utilities were illustrative defaults, not user-authored content. Requested local objects remain attached. JSON/DXF import, saved-draft recovery, server results and generic `setModel` do not automatically add or reinterpret a roof. An imported level merely named `roof` is not classified as an unoccupied roof without its explicit kind.

The existing floor panel exposes a contextual remove/restore button for automatic roofs or an explicit removal preference, with an Arabic disclosure, keyboard operation, focus retention and a44px target. Authored imported roofs are not offered for automatic removal. Same-project local regeneration preserves removal; choosing a sample explicitly starts a new sample with its default roof. No HTML/CSS layout, guest entry banner, authentication, storage namespace or paid route is changed.

Local counts distinguish occupied storeys/room instances from roof decks. The roof does not add occupied area or require a stair core. Partial parapet gaps stay explicitly disclosed; structural design, drainage, waterproofing, roof access and code compliance remain unverified.

All physical levels must fit the existing64-level scene limit. Creation/restoration rejects an excess before replacing the visible model; it does not silently drop the roof. A missing height/elevation is an error rather than a fabricated engineering value. A local model with authoring locks fails closed for these operations. A successful new model resets a stale floor selection, preventing a removed roof selection from leaving the viewport blank. Presentation-only rebuilds and failed compilation preserve the existing selection/model. New UI readers also retain the renderer’s existing handling of legacy malformed levels and derived indices without mutating the imported model. A new regression first reproduced a non-array-level TypeError, then passed after reusing the compiler’s level resolver and scene cap.

The increment is [PR191](https://github.com/NAIFMUSFER/AI-Instruction/pull/191), targeting PR190. Independent security review reproduced a default local-edit path committing a roofless candidate after a missing-height failure. The same omission guard already present in generation now rejects that edit before compilation; the regression preserves the prior model and floor selection while allowing an explicit user-removed roof to remain absent.

## Verification boundaries

The Python/JavaScript parity suite compares exact numeric values, Boolean types, identities, reports and input immutability. It covers explicit elevations, negative indices, nonuniform heights, shared authored templates, Unicode160-character identities and collision suffixes, partial gaps, invalid heights, removal/carry/restore, and actual residential/warehouse sample counts. It evaluates real shipped declarations with the repository source loader and real hashing/numeric helpers; native module loading and browser rendering are separate checks.

Raw helper numeric-string conversion is tested independently. Arabic/underscore string dimensions remain invalid at canonical geometry admission and the local renderer; matching helper conversion does not promote them to confirmed canonical dimensions. The suite is not a universal malformed-JSON validator and does not claim cross-runtime wire-format/private-revision hash equivalence.

The guest browser extension exercises visible roof isolation/removal/restoration, actual saved payload/hash changes, local regeneration, exact reload, imports with automatic/authored/no roof, unsupported/malformed imports, two tabs, denied storage and delayed recovery of an older roofless draft. Every existing timeout and zero-auth/private-project/provider assertion remains. New tests require actual canonical geometry and visible floor/room counts, not merely a success label.

Local parity and focused source integration have before/after witnesses. The restored local executor still aborts Chromium at `socket() EPERM` before opening a page. Therefore the changed guest browser journey and final acceptance require CI on the published increment; no after-change browser pass is claimed in this document yet. No physical phone, live AI output or physical stair traversal is established. The existing separate authoring panel is not represented as a newly integrated main-scene editor.

## Import-wait regression

The recovery-seed import followed another24m-wide fixture. Its old width-only wait could finish before the asynchronous file read committed the new model. The browser wait now requires the unique recovery-model identity as well as the same width, with its timeout and every existing assertion retained. `test_guest_import_wait.cjs` executes the actual import handler with a deliberately pending `file.text()` and the actual browser predicate: it fails for the old predicate and passes after the identity guard. This is source/async-boundary evidence, not a native-browser pass.

## Recovery note

The first uncommitted attempt was lost when the executor returned an older filesystem snapshot. PR190 and its acceptance evidence remained intact on GitHub. This increment was reconstructed above that exact remote head and re-tested; earlier local results were not silently carried forward as verification of reconstructed files.
