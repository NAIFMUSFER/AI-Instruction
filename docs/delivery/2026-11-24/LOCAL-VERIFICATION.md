# ACS continuation — local verification, 24 November 2026

## Scope and provenance

This continuation concerns `NAIFMUSFER/AI-Instruction` and PR #201 only.
Production started at `c26bc5fb292082cec266844f6da35ca4d2553b58`.
The original PR head was `143312a346713a10ea89937dc0cfe79dab2c17fe`.
Pending local native-viewer, export-preservation and idle-render fixes were
reconciled with upstream `21c49e1`, `6ce6cf2` and `b09d334`. Concurrent work
on separate guest projects, revision controls, software rendering and tests
was retained. This document records local evidence, not deployment success.

## Four requested descriptions

| Input | Building | Occupied floors | Apartments | Entrance |
|---|---|---:|---:|---|
| Full Riyadh description | 20 × 25 m | 3 | 6 | North |
| Larger residential description | 24 × 28 m | 4 | 8 | North |
| Central open courtyard | 20 × 25 m | 3 | 6 | North |
| New Saudi description | 24 × 28 m | 3 | 6 | West |

Independent model inspection passed all four fixtures and the five-step
generation/revision sequence. Checks cover actual room dimensions, three
daylit bedrooms per unit, shared and private circulation, reciprocal doors,
upper-floor support, stairs and unchanged source data.

The court is a real open shaft with a default clear opening of 4 × 5 m and
shared circulation around it. This size is an explicit design assumption,
not a requirement supplied by the user. Independent Python compiler probes
checked actual vertices in four 24 × 28 m cardinal court variants: no mesh
obstructs the clear court or the checked stair slab/ceiling openings. The
browser slab tessellator independently preserves the court and roof opening.

## Resolved defects and focused evidence

* Roof descendants and extra engineering fields are checked before revision.
  A manual roof object, MEP, structural, fire, or slab data cannot silently
  disappear. Fourteen independent preservation/rejection probes passed.
* Unsupported mixed requests and incompatible preservation instructions are
  rejected in Arabic before replacing the project.
* Shared-door projection was extracted into a pure leaf, avoiding an import
  cycle. The module graph passed its initial 45 assertions and all 50 after
  adding recovery-branch and required-module negative checks.
* JSON and every-floor SVG projection preserve the selected source and its
  authored identifiers. A false courtyard overlapping an occupied room is
  not drawn. Default SVG sheets and the native USDZ asset remain reproducible.
* The software renderer changes the measured central roof pixels when the
  actual court is added. This pure renderer check does not prove browser UI.
* The canceled SVG-download fixture now serves original files over actual
  HTTP and compares bytes, with all other origins blocked. It does not alter
  production authentication behavior.

## Browser and publication gates

The workflow defines four descriptions at 393 and 1440 pixels, with real
every-floor selection, SVG/JSON downloads, desktop GLB inspection, actual
entrance meshes, courtyard rays, and source preservation. Baseline jobs also
run the independent revision journey and the WebGL-disabled recovery journey
once per viewport. Evidence filenames include the source SHA and case.

Local Chromium was unavailable, so no local browser screenshots, downloaded
browser GLB, or browser-raycast pass is claimed here. GitHub Actions must
complete on the final source before merge. Published runs must confirm both
Netlify and Render revision stamps before exercising the public URLs.

The first integrated candidate, `0d865535ea2260ca6e96cb96cb86811beec631de`,
completed six of eight public matrix jobs: both sizes for the larger scheme,
central court and west entrance. Both baseline jobs passed the interactive
revision and software recovery journeys, then failed the initial orbit
assertion. The locked browser harness treated an asynchronous polling
predicate as immediately truthy; the correction uses synchronous polling of
real counters and retains both frame-growth assertions. Initial core gates
also exposed the viewer-only Node extractor's old generator dependency and
a deployment guard interpreting a double-quoted header URL as an absolute
build path. The boot contract also expected recovery-only modules to load on
successful WebGL; it now distinguishes the actual recovery branch while
rejecting omission of any required normal-route module. These initial failures do not
count as successful final acceptance. [Candidate matrix](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/45314948451)

The same candidate's Google/auth browser job passed the shipped UI at both
sizes, including the original failing real-response fallback downloads.
This is synthetic authentication evidence; the production upstream status
below remains a separate finding. [Candidate auth](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/45314948359/job/138179532803)

## External services

At 05:23 Riyadh time, the public version and health probes succeeded, Google
start returned HTTP 503 `AUTH_UPSTREAM_UNAVAILABLE`, and unauthenticated
generation returned HTTP 401 `ACS_AUTH_REQUIRED`. The configured ACS Supabase
auth host was unreachable and administrative project access was denied.
147 local synthetic authentication, recovery and job-delivery contract tests
passed; they do not establish real Google login or paid generation.

PR #197 production database activation still requires access to the existing
ACS database, migration/backup verification and server signer provisioning.
No other project's database was substituted. Reading classic branch
protection returned 403; the connected tools could not establish or change
that protection. Physical iPhone behavior has not been tested.
