# ACS Design Pipeline v2 — shared workflow, building-specific rules

Status: OWNER-REQUESTED SCOPE / IMPLEMENTATION SPECIFICATION. This document does not establish that the workflow, CAD exports, cloud revision storage or the acceptance tests below are implemented or deployed.

Decision recorded: 2026-09-11. The owner explicitly extended the entire plan-first workflow to warehouses, not just residential buildings. Earlier instructions to preserve warehouse quality are a regression constraint, NOT an exemption from plan review, editing, locks or approval.

## 1. Scope and invariant

Residential, villa, apartment, warehouse and industrial projects use the same lifecycle:

Brief → Program → Constraints → Design Options → intelligent 2D/CAD plan → chat editing + Lock → Validation & Metrics → engineer approval → Frozen Baseline → derived BIM/3D → DXF/IFC/SVG/PDF.

One canonical, versioned ACS model is the source of truth. CAD files, plan views, sections, schedules, BIM and 3D are projections/exports, not independent AI-generated geometry. Building-specific policy adapters supply planning constraints and metrics; they do not skip approval.

For a warehouse, the approved baseline must include the operational layout (zones, racks, aisles, loading and movement interfaces), not only the building shell. A final 3D conversion must not independently rearrange racks, narrow aisles, move docks or invent capacity.

## 2. Requirements and information provenance

Each requirement retains an ID, the source message/import, units, scope and status: explicit, proposed/inferred, confirmed or not specified. Proposed values must be visible and require confirmation where material to the design. Unknown quantities stay null / غير محدد; zero is a measured or explicit zero only.

Before proposing a warehouse layout, capture applicable inputs:

- Site boundary versus built footprint, street/access side, entrances, usable height, roof profile and explicit column/structural obstructions.
- Stored goods, load units and their dimensions/weights, requested storage system, target storage positions and stated operating volumes. A quantity target is not proof of achievable capacity.
- Receiving, inspection, quarantine, reserve storage, forward picking, packing, dispatch staging and returns as requested. Mark unrequested recommended zones as proposals, not customer requirements.
- Dock/door count and positions, truck/yard access, equipment models, operating envelopes, turning/clearance inputs and pedestrian routes.
- Requested offices, staff spaces, maintenance, charging, cold storage or specialist storage. Do not add physical rooms/walls to every logical operating zone.
- Structural, fire, emergency-egress, chemical compatibility, ventilation and environmental requirements, with sources and verification status. Missing safety-critical information is a review blocker for the applicable check, not permission to guess a compliant solution.

Do not hardcode universal aisle widths, fire distances, permissible rack/slab loads, storage heights, chemical-separation rules or setback values. Applicable equipment specifications and engineer-confirmed requirements must be supplied and traced. This product specification is not an engineering standard or regulatory approval.

## 3. Design alternatives

Offer distinct, labelled proposals for the confirmed program; do not silently triple paid generation calls. Show scope, expected provider calls and budget, and respect project limits.

Warehouse objectives may be:

A — capacity-oriented within confirmed constraints.
B — shorter handling routes under explicit operating assumptions.
C — clearer separation of pedestrian/equipment flows and future expansion reserve.

These labels are objectives, not claims that a proposal is optimal, safe, fastest or regulation-compliant. Compute the comparison metrics. When geometry or operating data are insufficient, show NOT EVALUATED. Do not rank throughput without a stated simulation/measurement model and assumptions.

## 4. Intelligent 2D and targeted editing

Represent site, building envelope, spaces/zones, walls, openings, columns, racks, bays, aisles, routes, docks and vertical circulation as typed elements with stable IDs. Use explicit units, coordinates and tolerances. A warehouse plan includes rack elevation/section information when vertical storage or clear height is relevant; a floor plan alone does not confirm vertical capacity or clearances.

Display dimensions, labels, element properties and a selected-floor/level view. Plan editing must modify canonical geometry, not only SVG strokes or screenshot pixels. Imported CAD entities must be mapped/validated with stated import limitations before becoming authoritative objects.

Support chat requests such as:

«انقل منطقة التجهيز إلى جوار الشحن، ولا تغيّر الأرصفة أو الأعمدة أو الممر الرئيسي».
«زد مواقع التخزين ضمن المساحة المتاحة، مع تثبيت مخارج الطوارئ وأبعاد الممرات المعتمدة».

Locks can protect an entire element or selected properties (position, dimensions, orientation, type). The backend must reject any candidate patch that changes a locked property, including indirect changes through parent/group transforms. Client-side labels alone are not enforcement.

Compute a before/after change set; identify impacted requirements and measurements. Reject infeasible requests with a conflict explanation. Never silently unlock objects, reduce required capacity, delete program items or change unselected zones merely to produce a response. No broad replacement of the current industrial renderer is authorized by this scope change.

## 5. Validation and warehouse scorecard

Shared checks include valid dimensions, containment, unintended overlaps, supported adjacency, access connectivity, matching the confirmed program, lock preservation and consistency across levels.

Warehouse-specific checks and measurements must be explicit:

- Count modeled rack bays and storage positions by level; report geometric positions separately from usable/load-rated capacity. Missing load-unit, rack or clearance information prevents a verified usable-capacity claim.
- Measure zone areas and allocation ratios from geometry under named definitions. Keep net storage area, staging, circulation and building/site area distinct; do not double-count nested zones.
- Detect geometric intersections involving racks, columns, door openings, reserved routes and staging zones. Associate each check with the actual model version.
- Evaluate minimum aisle clearances and equipment movement envelopes only against supplied equipment/operating data; report unavailable checks as NOT VERIFIED.
- Measure configured route lengths between receiving, storage, picking and dispatch. Report assumed movements and route definitions; do not infer throughput from distance alone.
- Check clearance to roof/obstructions when those objects and heights are modeled. Structural and fire/egress compliance remain separate specialist validations.
- Preserve explicit expansion reserves and check that a proposal has not occupied them.

Use PASS / FAIL / NOT VERIFIED / NOT APPLICABLE per check, with evidence and scope. A geometric check cannot certify rack design, structural support, fire protection, chemical storage or Saudi-code compliance. No unexplained composite AI quality percentage.

## 6. Approval, revision and deterministic derivation

Draft → Review Ready → Engineer Approved → Frozen Baseline → Derived Artifacts.

Approval records the reviewer, timestamp, revision, canonical snapshot hash, confirmed requirements, locks, validation report and unresolved items. The interface must distinguish schematic approval from statutory/structural approval. Known hard violations block schematic approval; unresolved safety-critical criteria must not be labelled passed or silently waived. Construction-release claims are out of scope until the required professional/regulatory approvals exist.

The hash detects snapshot mismatch; it is not authorization. Server-side project access control and approval identity are required for shared/cloud projects.

BIM/3D generation consumes the exact frozen snapshot without another LLM layout decision. Each derived object retains its source element ID and revision. Mapping may be one-to-many (for example a wall with opening segments); identity, geometry and tolerances must remain auditable. Missing dimensions must be resolved before approval or explicitly block the affected derivation, not invented downstream.

Post-approval edits create a new draft revision. The prior approved plan and its artifacts stay unchanged. All affected checks rerun and the new revision requires approval before replacing the current baseline. Cosmetic-only rendering changes must not mutate canonical geometry.

## 7. Persistence, recovery and exports

Provide explicit save, version labels, reopen, comparison and an approved-version marker for BOTH residential and warehouse projects. Preserve the original brief, confirmed constraints, option selection, locks and approval metadata. Generating another proposal must not overwrite an approved version.

Local recovery is a device-local backup, not cloud storage. Shared commercial project storage requires authenticated access, atomic revisions, project isolation and durable model/artifact storage. Temporary async generation results are not a permanent project archive. Reconnection must resume the same job and avoid automatic duplicate paid submissions.

Export DXF, IFC, SVG and PDF from the selected approved baseline, with units, layers/entity mapping and a provenance manifest. Verify that each format represents the same geometry/revision within explicit tolerances. Declare omitted/unsupported objects. Native DWG or Revit delivery is a separate, verified integration; do not rename DXF or claim native compatibility without testing. Supported IFC schema/version must be selected and tested rather than assumed from this specification.

## 8. Acceptance cases required before claiming delivery

- The same approval-first lifecycle is exercised for a residential fixture and a warehouse fixture; neither bypasses the plan stage.
- A warehouse operating zone remains open unless walls are explicitly specified.
- Locked dock/column/aisle coordinates and dimensions survive targeted chat edits exactly within the declared numeric representation.
- An impossible capacity increase reports a constraint conflict instead of narrowing locked aisles or moving fixed equipment.
- Capacity is unknown when rack/load dimensions are missing; target capacity is never reported as measured capacity.
- Position counts agree with explicitly modeled bays and levels, and geometric versus operational capacity is distinguished.
- Containment, overlap, configured-clearance and route tests fail on deliberately invalid local fixtures; no production customer data are used.
- Frozen-baseline mismatch blocks derivation; no paid LLM call is made during deterministic plan-to-3D conversion.
- Saved approved version V1 survives a new V2 proposal, reload, comparison and restore; cloud/device-local behavior is identified correctly.
- Cross-user and cross-project access tests cover shared saves, approvals and artifact retrieval.
- Mobile offline/reconnect/reload resumes the original task without duplicate generation and keeps version selection stable.
- DXF/IFC/2D/3D outputs retain source IDs and revision mapping; round-trip/inspection checks cover geometry, units and unsupported objects.
- Existing warehouse visual/regression fixtures remain valid; residential-only massing rules are not applied to industrial layouts.

## 9. Incremental implementation order

1. Shared canonical plan/revision state, requirements provenance and approval contract.
2. Residential AND warehouse 2D views, selection, dimensions and lock-aware patch validation.
3. Building-specific proposal generation and measured scorecards.
4. Frozen-baseline derivation and export adapters; reuse the existing warehouse renderer where consistent with the approved model.
5. Durable shared project storage, full version comparison and production acceptance evidence.

Each increment needs focused tests plus the repository's required CI, review and deployment verification. Completing documentation or obtaining a green CI run does not establish implemented features, professional design quality or a live production release. Existing PRs must be inspected at their current heads; this document does not change their runtime scope or waive their release gates.
