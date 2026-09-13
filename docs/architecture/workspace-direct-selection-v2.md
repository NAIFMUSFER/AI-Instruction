# Workspace direct selection — Design Pipeline v2

This slice connects the existing ACS 3D viewport to the existing Phase 6 Project Tree and Inspector. It does not introduce a second renderer, inspector, geometry model, or editing authority.

## Identity rule

Viewport hits are translated only when the rendered tag can be bound to a canonical identity through the current Building model.

- Explicit doors/windows resolve to their canonical opening identity, preserving an explicit model id when present.
- A rendered wall/floor/roof segment is currently a derived visualization of a canonical SPACE. It therefore selects the owning SPACE and is labelled `OWNER_SPACE`; ACS does not invent an independent wall identity.
- Presentation-only and visual-only meshes are never promoted to engineering selections.
- Unknown level, template, room, or opening identity fails closed.
- Warehouse rack/dock/lane/station submesh selection must not be advertised as exact until renderer tags carry stable canonical element/source identities. Heuristic identity reconstruction is not permitted.

## Interaction rule

A short primary-pointer click may select. Orbit-like pointer movement is not treated as an engineering selection. Before direct selection is handed to the workspace, the existing workspace entry point is reused so the latest exported canonical project is attached. The existing workspace remains responsible for Inspector state, AuthoringCommand preview/commit, revisions, undo/redo, validation, provenance, and later locks/approval integration.

Tree/Inspector selection and viewport selection use the same workspace selection authority. Viewport highlighting is presentation-only and lives outside the canonical Building group; it cannot enter model hashes, BIM, quantities, approval receipts, or exports.

## Presentation controls

ACS already owns reversible DOLLHOUSE/CUTAWAY/FLOOR_PLAN/SECTION presentation modes. This slice intentionally does not duplicate floor isolation, roof hiding, clipping, or section logic. Those controls will be exposed/refined through the professional workspace in separate auditable slices.

## Product boundary

Direct selection is not direct model mutation. A future drag/property edit must become an ordinary canonical authoring proposal/revision and pass locks, validation and measured scorecards before approval. Frozen Baseline semantics remain unchanged: downstream BIM/3D/export derives from the exact approved canonical revision only.

## CI synchronization evidence

The first full-CI attempt after the selection bridge reached the real Chromium mobile/documentation gate with all 65 mobile-layout assertions passing, then failed because the generated repository measurement block had drifted after the new frontend modules were added. The repair regenerated `tests/performance/bundle_report.json` and the matching `KNOWN-ISSUES.md` state using the repository's own measurement tools; no assertion or browser gate was removed. A fresh workflow run on the final human-authored head is still required before this slice can be considered green or mergeable into the RC.
