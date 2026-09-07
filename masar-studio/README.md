# MASAR Studio 4.1.0 — مسار

An Arabic-first full-stack architectural **concept authoring studio**. A canonical
project drives synchronized plans, a 3D view, hosted openings, quantities, review
snapshots and exports. It is not a building-permit, structural design or certified
BIM authoring system.

## Run

Use Node **22.23.2** (security-patched deployment target). Compatibility tests also
run on 22.16.0, which is not the recommended public deployment version.

```sh
npm ci --ignore-scripts
npm run check
npm run build
npm test
npm start
```

Open `http://localhost:3000`. `start-windows.cmd` starts the same server. There are
no runtime npm dependencies. `dist/index.html` is the standalone, offline-capable
build; it does not provide server accounts/sharing on its own. The native server
serves the source modules and the same model, not an unrelated mock UI.

## Working product

Describe a villa, chalet, office, warehouse or retail project; review the dimensions,
floor count, requirements and assumptions before generation. The generator is
rule-based and bounded to 1–8 floors. It does not pretend to understand every free
architectural sentence. The original brief and unresolved requests are retained.

Select a room in the plan, tree or 3D view. Edit dimensions, position, name or notes;
preview local Arabic editing commands; inspect affected elements before committing.
Locks and geometric/connectivity blockers prevent an invalid commit. Four comparison
alternatives, measurements, comments, named revisions, undo/redo and restoration
are available. History is retained; the 100-revision bound fails explicitly rather
than deleting old revisions silently.

Authoring includes composite conceptual wall types, separate doors and windows,
hosted aperture-fit checks, individual opening lock enforcement, and simple
orthogonal non-rectangular footprints. The UI can create a corner notch and move
an existing polygon; it is not a general polygon drawing/CAD editor. Editing one
door does not delete the other doors. Proposed wall-type changes are project-level
changes and never render fake room bounding boxes.

Exports: MASAR JSON with history; SVG; conceptual DXF; OBJ; IFC4 architectural subset
with wall layer assignments and real hosted void/fill relations; room/element/
requirement CSV; quality JSON; HTML report; PNG. User-provided CSV text is escaped
against spreadsheet formula execution. IFC import is reviewed before creating a
separate project and rejects unsupported/ambiguous geometry instead of flattening
it silently. Read `docs/LIMITATIONS.md` before exchanging BIM files.

## Accounts, data and review

The Node server uses SQLite, scrypt password hashes, hashed session tokens,
HttpOnly/SameSite cookies, exact-origin and CSRF checks, ownership checks and
optimistic save versions. A stale browser save offers conflict choices without
silently replacing either document. Cloud base-version metadata is retained with
the local IndexedDB project. A separate account cannot access another account's
project. Local device copies remain after logout and are clearly distinguished
from account storage.

Sharing requires explicit consent and creates an immutable snapshot. Anyone with
the URL can review it until expiry or revocation. Original prompts and internal
comments are excluded by default. Reviewer comments are stored separately from
geometry; the owner can resolve them without rewriting the project. Invalid or
revoked review links fail closed, never displaying a different private local file.

The service worker controls the root and caches only the public application shell.
It does not cache API responses or review-token URLs. Browser-origin offline
persistence is tested separately from standalone rendering; neither a memory mock
nor `set_content` is counted as proof of real browser storage.

## Deployment and recovery

Public deployment needs an exact HTTPS origin and durable storage. `compose.yaml`
uses a dedicated named volume and a non-root, read-only application container;
place an HTTPS reverse proxy in front of the loopback port. Public registration
is closed by default in production. Configure a bootstrap account through secret
environment variables and remove bootstrap credentials after the first start.

`render.yaml` is specifically a **free, ephemeral staging** blueprint for the
`masar-studio/` directory on the isolated `masar/production-v4` branch. It is not a
durable production deployment. The UI permanently warns when that storage class
is active. No existing ACS or dawaee service needs to be changed.

Consistent online snapshots and fail-safe restoration are available:

```sh
node tools/backup.mjs create /persistent/masar.sqlite /secure-backups/new.sqlite
node tools/backup.mjs restore /secure-backups/new.sqlite /persistent/restored.sqlite
```

Existing targets are never overwritten. Integrity, foreign keys, schema version,
size and SHA-256 are checked. Restoring invalidates sessions. Snapshots contain
private account/project information and must never be served publicly, committed,
or stored in the project source ZIP. Hashes detect corruption, not a malicious
replacement of both a backup and its manifest. See `docs/DEPLOYMENT.md`.

## Verification

```sh
npm run check
npm run build
npm test
python tests/browser_flows.py                 # Exact standalone build
MASAR_BROWSER=chromium python tests/browser_http.py
MASAR_BROWSER=firefox python tests/browser_http.py
MASAR_BROWSER=webkit python tests/browser_http.py
node tests/ifc-fixtures.mjs
python tests/ifc_external.py                   # IfcOpenShell 0.8.5 + pytest 8.4.2
node tests/docker-smoke.mjs                    # Docker required
```

The HTTP suite starts disposable local test servers/databases/browser profiles.
It must be run where localhost browser navigation is allowed; it is not a request
to bypass an environment restriction. The standalone suite works without URL
navigation and explicitly records its narrower scope. Machine-readable reports
and CI output are the evidence; no fixed passing count in this README substitutes
for running the exact source under review.

The independent IFC suite checks 12 fixtures with an external parser, EXPRESS
rules, tessellation, world-space space volumes and wall volumes after actual void
subtraction. It also checks Arabic/supplementary Unicode and ownership relations.
That verification is not Revit certification or engineering/code compliance.

## Explicit exclusions

No structural, MEP, fire, accessibility or SBC approval; no native DWG authoring;
no arbitrary PDF/image-to-BIM conversion; no arbitrary IFC authoring round trip;
no email verification/password-recovery mail provider; no horizontal multi-node
SQLite deployment. Cloud AI is optional and requires a configured provider/model
and per-request consent. A live paid provider call is not implied by the tests.

This release recovers complete files from the previously partial v4 upload,
reconstructs missing frontend/build/test parts from the delivered v3 baseline,
and adds audited corrections. It does **not** claim byte identity with the lost
original v4 archive. The release source manifest identifies the actual new tree.
