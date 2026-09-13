# Plan-first 2D review UI — read-only slice

The existing `acs_plan_projection.project` function produced exact, provenance-aware
space-boundary primitives but there was no browser review consumer under
`public/plan-review/` at base `7773397d471d4f28630698087834b3c15e2b3a80`.
This slice connects that existing foundation to an Arabic responsive reader rather
than inventing a second planning/geometry engine.

## Current use

`build_review_packet(workspace, revision_id)` in `tools/acs_plan_review_packet.py`
uses that exact immutable revision, its existing review, scorecard, room/semantic
lock selectors, requirements and per-level projections. It never approves or
calls the provider/compiler. Raw brief, evidence, notes and actor names are omitted.

For a supplied canonical input `{building, brief, requirements}`:

```sh
python tools/acs_plan_review_packet.py input.json output.acs-review.json
```

The CLI uses `existing_geometry_verifier` and creates an explicit draft, not a
claimed pre-existing approved revision. Existing workspaces should call the
export function to retain their exact revision identity and recorded locks.
Output paths are exclusive-create; invalid geometry/provenance fails closed.

Serve `public/` and open `/plan-review/` over HTTPS or localhost. Import one to
eight generated review files, switch revision/floor, select rooms with pointer or
keyboard, inspect metre geometry, requirements/source spans, metrics and recorded
locks. Clear removes the views; a late file read cannot restore cleared data.
No sample files ship under public, and no project file is uploaded or persisted.

## Trust and scope

SHA-256 covers exact UTF-8 payload bytes (avoids Python/JavaScript float
serialization differences). The reader also checks revision/source identity,
geometry bounds and displayed area consistency. A hash is not a signature or
issuer authentication. Imported review results are explicitly unverified in the
browser session. No approval, edit, unlock, 3D generation or cloud-save authority
can be granted by importing a file; those controls are not exposed.

The drawing is `SPACE_BOUNDARIES_ONLY`. It is not complete working CAD: no wall
thickness, openings, rack footprints, docks, MEP or safety paths are invented.
Warehouse operational metrics and explicit linked rack/dock provenance remain
inspectable, but the existing warehouse renderer is untouched, not replaced.
The original Canonical ACS Model remains source of truth.

Authentication, authoritative server-backed edits/locks/approval, persistent
project loading, warehouse operational drawing layers and approved-baseline 3D
integration remain separate required slices. This reader is not the completed
Design Pipeline v2 website, regulatory certification, or a production deployment.

## Gates

The new `Plan-first 2D review UI` workflow is mandatory for this slice in addition
to full CI, Plan-first foundation contracts and Async generation delivery. It
uses synthetic temporary fixtures, actual canonical projection code and real
Chromium/WebKit. The topology test double is explicit; the CLI test additionally
uses the repository validator. Browser tests cover 320/393/800/1280 px, Arabic
selection, corruption, source identity, plain-text labels, import races and CSP.
Read the run/artifacts for results; this document does not claim a test outcome.
