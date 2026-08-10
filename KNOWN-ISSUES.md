# Known Issues — preserved for later remediation

## KI-1 · Automatic engineering changes reported by generation (SEMANTIC — OPEN)

**Status:** intentionally NOT fixed in the Phase 9.2 production remediation (that
remediation was packaging/deployment integrity only, per its §10/§11 scope).

**Observed:** during model generation the application reports automatic engineering
adjustments such as: extending site dimensions, changing aisle widths, adding exits,
adding sprinklers/smoke detectors, changing camera counts, resizing zones.

**Why it matters:** these originate in the generation/normalization path (Phase 2–3
resolution rules), not in the presentation layers. Phases 9.1/9.2 are provably
read-only downstream (byte-immutability suites), so this is a separate authority
question: which automatic adjustments are legitimate deterministic normalizations
with declared provenance, and which should instead surface as
`REQUIRES_ENGINEERING_CHANGE` / unresolved diagnostics awaiting explicit user
consent.

**Planned remediation shape (not started):** audit every automatic adjustment site in
the generation path; classify each as (a) declared deterministic normalization with
provenance + issue code, or (b) silent invention to be removed and replaced by an
explicit unresolved report; extend the adversarial suites to pin the chosen contract.
No canonical semantics were modified by the Phase 9.2 remediation.
