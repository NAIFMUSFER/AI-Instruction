# ACS Design Pipeline v2 — implementation and remaining release gates

## Product decision

Replace the direct residential brief-to-final-model experience with:

Brief → confirmed program and constraints → alternative schematic plans →
chat edits and explicit locks → measured review → engineer conceptual approval →
exact baseline handoff → deterministic BIM/3D and exports.

The ACS canonical Building remains the source of truth. DXF/DWG are exchange
formats, not a second editable authority. No new provider, infrastructure,
production route, warehouse policy, or deployment setting is enabled by this PR.

## Implemented foundation in this branch

* `acs_plan_review.py`: immutable JSON revisions, stable template/room references,
  optimistic revision checks, retained approvals, explicit lock/unlock revisions,
  and exact baseline handoff. Edits never overwrite an approved version.
* The draft admission path permits reviewable geometric defects but refuses
  ambiguous room IDs, malformed/bounded JSON and resource-limit violations.
* Geometry checks cover positive explicit dimensions, site bounds, rectangular
  overlaps, level/template references, unresolved spaces, and empty templates.
* Program checks distinguish requested, inferred and unknown facts. A requested
  fact needs an actual source excerpt; an inference needs explicit confirmation;
  missing information is not replaced by zero. Counts expand repeated templates
  into actual level instances. Only the supplied typed requirements are checked:
  this does not prove that all natural-language requirements were extracted.
* Approval requires the current revision, an explicit conceptual-only action,
  and successful in-process topology and vertical-circulation verification.
  Missing/malformed/throwing or mutating verifiers fail closed. Regulatory
  compliance and structural safety are always NOT_VERIFIED here.
* `acs_plan_bridge.py`: opt-in adapter to the existing bounded planning stage.
  It stops before detail generation and compilation. A separate chat-edit adapter
  proposes one new revision; it cannot silently alter locked spaces or approve it.
  Existing validator findings are retained, not filtered out by message keywords.
* `acs_plan_projection.py`: SVG and DXF derive from the same space-boundary
  primitives and carry revision/model provenance. DXF has metre units and a
  reversible ACS (x,z) → CAD (x,-z) mapping. `ezdxf` is an optional exporter
  dependency, not added to the production runtime in this PR.

## Deliberate limits — not a finished user-facing feature

The workspace is process-local. A restart loses it unless a host persists it;
this is NOT the durable/cloud project store and is NOT a replacement for PR19's
saved versions. No public API accepts an approval label as authenticated identity.
The host must resolve the engineer/account and enforce project membership.

The adapter is not registered on production routes. Before exposure it must run
behind the existing body caps, quotas, isolated/cancellable job runner, and
recoverable asynchronous delivery. It must not execute on an HTTP event loop.

The CAD projection is **SPACE_BOUNDARIES_ONLY**. It does not draw complete walls,
doors/windows, structural grids, MEP or permit sheets. Space rectangle totals
are NOT gross floor area, net floor area, or an efficiency score; those metrics
remain null. DXF files are parsed/audited with ezdxf; native AutoCAD/DWG opening
has not been verified. Arabic label content round-trips; visual font shaping
inside AutoCAD has not been checked. No DWG, IFC, PDF or Revit export is claimed.

The old planner can return incomplete/disclosed assumptions. These stay drafts;
this adapter does not turn planning output into automatically approved geometry.
No live paid generation or OpenAI-versus-DeepSeek comparison was run by this PR.

## Remaining implementation sequence (all agreed features retained)

1. Authenticated, project-scoped persistent brief/program/constraint/revision store;
   server-side atomic approval receipts and durable job/result storage.
2. Four-stage Arabic/mobile workspace: requirements, intelligent 2D plan, 3D/BIM,
   presentation/export. A new residential generation must open the plan for review
   rather than applying it to the 3D viewport automatically.
3. Structured brief extraction with source spans, clarification questions, units,
   and engineer confirmation. Add program metrics only when measurable.
4. Three explicitly requested design alternatives with shared hard constraints;
   comparison of area use, movement/privacy and externally evaluated daylight.
   Do not label an unmeasured option "best lighting" or generate three paid jobs
   merely because a panel opened.
5. Chat changes expressed as scoped proposals plus a visible semantic diff.
   Room/core/site locks persist. Repeated-template and single-floor edits require
   explicit instance scope. Approved geometries require a fresh revision/approval.
6. Full architectural 2D geometry: shared walls, explicit openings, core IDs,
   stairs/elevators/shafts, grids, dimensions and a real preflight scorecard.
   No automatic rect repair or deleted requirements to make tests green.
7. Deterministic compiler integration with baseline/hash verification and exact
   element lineage. 3D presentation may change materials/camera, not floor plans.
8. Full DXF round-trip acceptance in a supported CAD app; IFC/IDS checks and
   SVG/PDF sheets with identical revision references. Native DWG/Revit/Autodesk
   services are optional later connectors, not a mandatory paid dependency.
9. Office standards library (Design DNA), saved/accepted alternatives, restore,
   rename, compare and explicit deletion with backups and cross-device access.
10. Real mobile recovery + plan edit + approval + 3D + save/reopen acceptance;
    warehouse regressions unchanged; measured residential output review, then
    controlled production activation. No merge on foundation tests alone.

## Verification commands

```
python tests/remediation/test_plan_review.py
python tests/remediation/test_plan_bridge.py
python tests/remediation/test_plan_projection.py  # optional ezdxf==1.4.4 required
python tests/remediation/test_plan_bridge_integration.py  # full repository
```

The dedicated workflow installs the existing runtime locks and the optional CAD
library in its test environment. It runs actual assertions and preserves logs;
no writer workflow, bypassed check, provider secret, or automatic merge is used.
The existing full CI remains a separate gate.

## References for the CAD adapter

* ezdxf document management / encoding / supported versions:
  https://ezdxf.readthedocs.io/en/stable/drawing/management.html
* Document units and explicit block scaling:
  https://ezdxf.readthedocs.io/en/stable/concepts/units.html

These describe exchange mechanics, not architectural quality or certification.
