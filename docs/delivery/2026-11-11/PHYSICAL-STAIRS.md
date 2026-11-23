# Bounded physical stairs — 11 November 2026

This is Step4b, above PR191 head `064f4a96fdc1941f010b0f6ab814c765acd260c5`. The prerequisite [CI9](CI9-JOBS.md) passed all six triggered workflows and17 jobs. This stair increment is [PR192](https://github.com/NAIFMUSFER/AI-Instruction/pull/192); its own browser/CI acceptance is pending. [CI10](CI10-JOBS.md) initially found a non-stair validation-boundary regression, a connected spaces-only IFC scope leak and stale measured documentation. These are retained as failures, not relabeled as passing results. No merge, deployment, migration or paid provider request is included.

## Canonical geometry and supported boundary

An explicit `kind: "stairs", form: "u_return"` object owns its dimensions, source/destination levels and elevations, repetition limits and component identities. The pure Python and JavaScript resolvers derive the same two flights and middle landing. The conceptual default uses nine risers per flight, eight treads per flight,0.25m tread depth,0.9m flight width,0.1m gap, and0.9m entry/middle landing depths. Its footprint is1.9×3.8m; height is the declared elevation difference within the supported2.4–3.6m default range. These are disclosed design defaults, not code-derived or structurally verified dimensions.

Generation requires explicitly identified, aligned stair-core rooms and supported entrance/arrival doors. It does not resize a narrow core or infer a stair from a room name. Unsupported cases are recorded and disclosed. Physical order follows actual elevation, including negative elevations and indices that do not follow height order. Only explicit `kind: "roof"` is excluded from occupied-storey connectivity; a declared flight to/from an unsupported roof is rejected.

Fresh automatic placement is bounded before per-core searches or template cloning: at most128 prospective connections,512 physical room instances,600KB estimated output and30000 estimated nodes. These conservative authoring limits are below the canonical900KB/50000-node envelope and do not redefine existing imported-model limits. Exceeding them produces `STAIR_RESOURCE_LIMIT` with an Arabic request to reduce levels/cores, preserving the existing head/history without a provider retry. The estimator charges32 bytes per finite numeric scalar within the JavaScript safe numeric range, plus UTF-8 string/key bytes and container punctuation. Larger numeric magnitudes are outside this fresh automatic-placement profile. This keeps Python/JavaScript threshold decisions identical without changing canonical/imported geometry limits. The estimator is admission planning, not an exact transport-byte measurement.

The upper occupied storey receives the incoming connection and retains its arrival strip; it has no default outgoing flight. Destination slabs, room floor finishes and source ceiling finishes use the same opening. Cardinal rotations are supported; unsupported declared forms/rotations fail instead of silently rendering the former straight stair. A changed elevation, core or entrance invalidates the connection rather than repairing approved geometry during rendering.

Repeated templates are materialized only at fresh authoring. Stable room identities and validated template-scope records preserve confirmed room-count and minimum-room-area requirements. Element collisions receive deterministic distinct IDs. Scope metadata is a canonical relationship, not proof of authorship. Provider-supplied system reports/provenance/lineage are rejected at the fresh server boundary; imported reports never establish a verified traversal claim.

## Authoring, presentation and export

The server adds defaults only to a new described project, after the second stale-head check and before roof/proposal/approval. Imports, source revisions, existing-project regeneration and resumed jobs retain their objects and lock context. Local authoring is similarly restricted to a fresh sample/first creation. Existing local regeneration is not silently fitted with stairs. No dimensions in the old guest sample were changed to force it to fit this capability.

The connected viewer consumes the exact approved glTF; no second stair generator was added to it. The local compiler consumes the same canonical object through the JavaScript twin. Presentation cannot change the selected revision/hash or manufacture a connection.

| Output | Actual stair content | Limit |
|---|---|---|
| Python glTF / connected3D | Sixteen tread solids and one middle-landing solid per supported default connection, stable source IDs and actual elevations | Connected handoff is glTF; no new GLB compatibility claim |
| Local3D | Same canonical components/openings through the tested JS twin | Existing/imported geometry is not automatically repaired |
| Connected IFC/SVG/DXF/PDF | Existing space-boundary/space content | These connected exports do not become complete architectural stair drawings/BIM |
| Legacy architectural IFC | Explicit stair forms block full export with physical IDs and no file/manifest; spaces-only scope remains supported | The previous bounding-prism mapping cannot represent the new flights/openings honestly |

The IFC panel clears old export success when a new export fails and shows escaped, actionable Arabic errors. A successful prior manifest cannot be presented as the result of an unsupported stair export.

## Verification and limitations

The [evidence manifest](evidence/stairs/manifest.json) records 24 reviewed local logs, their original/copy SHA-256 hashes, source paths, observed file timestamps, and exact limitations. These are point-in-time results from the integration worktree above `064f4a96fdc1941f010b0f6ab814c765acd260c5`; complete per-run tree hashes were not captured. The manifest binds the latest frontend logs to the three production-file hashes reported by their owner. Filesystem timestamps are metadata, not independently authenticated execution times. Focused cases recur in larger suites, so the counts below must not be added into a release score.

| Check | Failing-before evidence | Passing local evidence |
|---|---|---|
| Fresh server authoring | [One missing-stair failure](evidence/stairs/server-before.log) | [Five lifecycle methods](evidence/stairs/server-focused-after.log); included in the later [34-method connected suite](evidence/stairs/server-full-after.log) |
| Malformed-room admission | [AttributeError before canonical rejection](evidence/stairs/malformed-server-before.log) | [One method passes](evidence/stairs/malformed-server-after.log) |
| Provider authority fields | [One method: five failing subcases and one error](evidence/stairs/provider-authority-before.log) | [Two methods pass](evidence/stairs/provider-authority-after.log), including preservation of authored geometry without system claims |
| Server resource admission | [Late `REVIEW_VIEW_LIMIT` rejection](evidence/stairs/resource-server-before.log) | [Early `STAIR_RESOURCE_LIMIT` without retry/write](evidence/stairs/resource-server-after.log) |
| Runtime packaging | [Missing `acs_stairs` in isolated COPY set](evidence/stairs/packaging-before.log) | [Two methods pass](evidence/stairs/packaging-after.log); this is an isolated COPY-set import, not a local Docker-container run |
| Serialized glTF geometry | [Base compiler substituted into the new suite: four cardinal subcases fail](evidence/stairs/independent-reader-before.log) | [Four methods pass](evidence/stairs/independent-reader-after.log), including obstruction and missing-arrival mutation witnesses |
| Python geometry and IFC boundary | No separate original failing log is reconstructed here | [16 geometry methods](evidence/stairs/geometry-after.log) and [seven IFC boundary methods](evidence/stairs/ifc-boundary-after.log) pass |
| JS/Python resource and Unicode parity | [Overlength Unicode core mismatch](evidence/stairs/resource-parity-before.log) | [81 independent scenarios pass](evidence/stairs/resource-parity-after.log) |
| Fresh local resource boundary | [132 prospective connections were not rejected](evidence/stairs/resource-local-before.log) | [Actual local-handler integration passes](evidence/stairs/resource-local-after.log) |
| Shipped local compiler | No saved original failing log claimed | [Geometry/holes/arrival/identity checks pass in Node](evidence/stairs/browser-geometry-after.log); this is not a real-browser result |
| Existing contracts | No new failure claimed | [Module graph: 45 assertions](evidence/stairs/module-graph-after.log), [guest-roof integration](evidence/stairs/roof-integration-after.log), and [CI contract gate: 78 assertions](evidence/stairs/ci-gate-after.log) pass |

The independent reader uses the pinned Three.js GLTFLoader to parse Python-produced files. Expected dimensions, triangle surfaces, opening emptiness and arrival area are checked independently of the stair resolver. Injecting a translated slab over the opening or deleting an arrival strip makes the check fail. This is an independent serialized-file reader, not another display engine or BIM target-tool validation. The baseline comparison substitutes the base compiler into the new fixture/architecture path; it does not claim that the entire old baseline was executed.

The new real-browser suite is prepared for six presets at 1440×900 and 393×852 plus two upper-arrival views. [Actual local Chromium launch failed before page load](evidence/stairs/browser-local-launch-failure.log) with `socket() EPERM`; no screenshot, browser assertion or performance measurement was obtained. Browser acceptance remains **PENDING CI**. The suite uses the real approved artifact, selects an actual tread, checks revision/hash/mesh identity, and retains the hard 2-second preset limit on 4+ logical cores. The current cutaway isolates one level and cannot display both full flights and the upper slab simultaneously. Detail frames a selected component, not a grouped stair assembly.

Physical traversal, guards, support, headroom, accessibility, escape capacity and code compliance remain **NOT_VERIFIED**. A shaped stair and opening do not establish any of these. No physical iPhone, paid/live AI generation or deployment is claimed.

## CI10 corrections awaiting a new CI head

Unmarked non-stair collections retain the existing provenance boundary; explicit stair forms/reports/scopes remain strict. The unchanged generic-object test passes on main, the parent and the corrected worktree; five new boundary tests protect the distinction. Spaces-only IFC excludes legacy opening validation because it emits no openings; full architectural IFC retains that validation and its explicit-stair refusal. The original fallback journey passes locally again. Browser output sources were regenerated, and the measured source-state documentation now agrees with the actual bundle. No test assertion or timeout was relaxed.

A new mandatory IfcOpenShell case will independently parse the serialized spaces-only IFC from a generated/approved/reopened synthetic residential stair project, including identities, bounds, units and entity scope. This test is wired only into the existing CI job that installs the pinned reader. It has not run locally because IfcOpenShell is absent; syntax checking is not execution.
