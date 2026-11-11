# ACS current capability and delivery status

Updated 11 November 2026 for the review-only presentation/roof branch. This is the current status document; historical phase/audit reports retain their original dates and do not establish current production readiness.

The 11 November package is rebased onto PR188 `9556ca4d9d405ba7b733e650d95559e83c60177a` in [PR190](https://github.com/NAIFMUSFER/AI-Instruction/pull/190). Its exact submitted head `3bc06725203533f59a7e4ec9358b0df4b5c9dff6` passed all31 triggered workflows and all42 GitHub Actions jobs; every full job log was reviewed. [CI4 results](delivery/2026-11-11/CI4-JOBS.md) include guest/auth, connected desktop/mobile roof actions and approval, full boot/visual, DOM/ARIA accessibility, approved-artifact views, actual advisory scanning and Docker. The PR remains open and is not merged or deployed. Intentional Netlify preview cancellation enforces the no-deploy instruction and is not called a passing test.

The next separate increment adds the same canonical default roof to local generation and samples, with Python/JavaScript parity and guest-browser verification before and after. It is reconstructed, locally tested and published separately in [PR191](https://github.com/NAIFMUSFER/AI-Instruction/pull/191), targeting PR190. The first submitted head was `3538d3014eddd308b24627d125fa49a34136afa3`; a subsequent boundary regression rejects a default local edit if roof regeneration lacks a required height, preserving the prior model and selection. Changed guest-browser acceptance remains pending its final-head CI. [CI6 infrastructure evidence](delivery/2026-11-11/CI6-INFRASTRUCTURE.md) records repeated Ubuntu mirror DNS failures before Poppler/browser tests could run; the independent import-wait race is corrected with a failing/passing local witness. A [bounded verified-mirror setup helper](delivery/2026-11-11/CI-APT-MIRROR.md) now addresses repeated dependency DNS failures while retaining every install/test command and timeout; actual mirror acceptance and browser success await CI. No later CI success is claimed here. Physical stairs and generator/material defaults have not started. Naif explicitly requires separate review PRs, no main merge, no deployment and no production migration in this task. Application/rebase evidence and retained earlier failures remain in [integration status](delivery/2026-11-11/INTEGRATION-AND-CI.md).

## Release boundaries

The prior10 November review recorded production frontend/backend commit `c37b5250dc4ff18ba0606add993b5afe52beebaa`; this is dated evidence, not a new production verification. The delivery is split deliberately:

1. **Independent application release:** guest preservation, exact approved viewer and Arabic UX, geometry/export fixes, shared paid-command admission, bounded identity/body handling, honest provider identity and release verification. Candidate validation is underway; this paragraph is not a claim of deployment.
2. **Database activation increment:** fail-closed membership, backend-validated canonical write capabilities, paged revision transport and atomic durable job leases. Implemented and tested with real local PostgreSQL; **not production deployed**. Activation requires access to the actual ACS database and secure backend signer provisioning. See [database rollout](delivery/2026-11-10/database/STATUS.md). Do not deploy its adapter/jobs against an unmigrated database or re-enable unsafe RPCs as a fallback.

The current connected Supabase account exposes no ACS schema. The live Google-start gateway returned `503 AUTH_UPSTREAM_UNAVAILABLE`. Two real private users, live cloud save/generation, production SQL grants/migrations and live provider results are therefore **not verified** in this delivery. No real-user project was read or changed, and no paid generation was made.

## What each output actually contains

| Output or feature | Supported evidence | Explicit limits |
|---|---|---|
| Guest local workspace | Residential/warehouse examples, local draft, supported local import/download, separated account namespace | Examples and deterministic local approximations are not fresh AI output; browser storage can fail |
| Connected canonical model | Versioned model, requirements, provenance, locks, conceptual approval and derived artifact hashes | Conceptual planning; no structural design or permit certification |
| Interactive approved 3D | Exact glTF source, six camera presets, level isolation, selection, source/revision labels, materials/shadows, keyboard/touch controls | Camera movement does not prove collision-free travel; unsupported stairs/lifts remain disclosed; decorative context does not change counts/hashes |
| glTF/GLB presentation | Compiler meshes, metres, floor/room identity, explicit elevations and supported object rotations | No arbitrary IFC/Revit import fidelity claim; no replacement generated image |
| Connected SVG/DXF | Canonical projected space boundaries, metres and source identity | Not full construction drawings; DXF is not native DWG |
| Connected PDF | Space drawings with embedded licensed font, shaped/searchable Arabic, mixed labels and source metadata | Conceptual space drawing, not a construction set |
| Connected IFC4 | Space entities/boundaries, storeys, IDs, metres and source metadata; independent reader validates bounds | Spaces-only connected export, not complete architectural BIM or native Revit |
| Legacy architectural IFC | Supported mapped elements; explicit open-wall semantics and distinct stair identities | Separate capability from connected IFC; no physical stair traversal/structural adequacy proof |
| Runtime navigation | Consistent transformed footprints/portals and capsule clearance for supported door geometry | Vertical alignment is not walkability; no full physical circulation certification |
| Canonical flat roof | Explicit unoccupied roof level, disclosed default0.9m parapet, separate area/storey treatment, revision-bound removal/restoration | Review branch only; missing vertical facts stay unknown, partially shared parapet gaps are disclosed; no drainage/structural/roof-access certification; guest roof integration is a subsequent gated increment |
| Large history | Pending DB increment retrieves metadata pages and bounded individual revisions | 100-revision aggregate admission limit remains; not unlimited constant-memory history |

## Verification scope

Deterministic approved villa and warehouse fixtures use the real geometry verifier. See [fixture manifest](delivery/2026-11-10/fixtures/manifest.json) for canonical hashes and serialized output relationships. Independent IfcOpenShell and ezdxf checks are separate from exporter-authored readers. A separately authored synthetic apartment floor also passes canonical approval and independent IFC/DXF bounds checks; its source, explicit dimensions and limitations are recorded in the geometry status. The original incomplete apartment fixture still fails admission. Arabic PDF is parsed by pypdf and visually inspected with Poppler.

Real PostgreSQL witnesses execute SQL, roles and grants against synthetic users/projects. They reproduce baseline missing-membership and direct-write defects before fixing them. This is not a substitute for deployed Supabase/PostgREST/JWT verification.

The local executor cannot launch Chromium because socket creation is denied. The prior cloud browser review verified the explicitly labeled no-WebGL guest fallback only. The first PR190 CI run produced24 approved-viewer captures at1440×900 and393×852, all visually inspected. HeadlessChrome151/SwiftShader on4 logical cores passed the3-second first-view and2-second transition gates. Adaptive immediate transitions yielded insufficient active-frame samples: smooth-frame p95 remains **NOT VERIFIED**. The complete guest/private browser aggregate passed on PR190 head `3bc06725203533f59a7e4ec9358b0df4b5c9dff6`; subsequent changes need their own CI evidence. Those captures are desktop browser emulation, not physical iPhone acceptance. Initial performance targets are ≤3 seconds from available artifact bytes to first view, and transition-frame p95 ≤20ms desktop / ≤33ms mobile viewport. Missing results or missed targets are not PASS.

The production verification runner now treats crashes, missing/malformed evidence and NOT VERIFIED as non-success. The aggregate CI is configured to include the new delivery checks, but branch protection was observed disabled. Requiring the aggregate status remains an administration proposal until the repository's actual protection settings are changed and verified.

## Traceability

- [Starting state and runtime journey](delivery/2026-11-10/STARTING-STATE.md)
- [Actual pending-PR reconciliation](delivery/2026-11-10/PR-RECONCILIATION.md)
- [File-level coverage](delivery/2026-11-10/file-coverage.csv): current review depth, owner, classification, risk, findings, tests and generator relationships. Static parsing is never counted as deep semantic review.
- Specialist scoped status and before/after evidence live under `docs/delivery/2026-11-10/`.

Remaining delivery blockers: actual production database access and signer setup; real authenticated end-to-end cloud generation and reopen; physical iPhone/Safari testing; target-tool interoperability beyond the independent readers stated above.
