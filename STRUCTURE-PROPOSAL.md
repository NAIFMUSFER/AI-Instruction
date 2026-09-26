# ACS feature architecture — proposal and migration plan

Recommendation: retain the current deployed layout for this audit. No production source, generated output, deployment setting, or import order is changed by this stream. The requested feature map is provided below as a conditional design, not as evidence that a migration has happened or that it would make the product faster.

The measured source has already evolved beyond the requested base into an authenticated plan-first workspace with durable revisions and residential/warehouse admission paths. A folder-only migration would not remove that complexity. The source contains deliberate deferred imports, late-bound rendering state, module-relative schema loads, and path-sensitive deployment gates. Those contracts must survive before a customer-visible benefit can be claimed.

<!-- ACS:CURRENT-STATE:BEGIN -->

## Measured audit snapshot

All numerical source-state observations in this document are confined to this block. Commands are run from the repository root. This is a dated audit snapshot, not a replacement for the generated state block in `KNOWN-ISSUES.md`.

| Measurement | Observed | Reproduction command |
|---|---|---|
| Examined source | `adec616aa5191315991fb9439cee83efbb719b8f` | `git rev-parse HEAD` before the audit documentation commit |
| Requested base | `9e3e472d6de893c8cad8b72eb870bf5768f20147` | `git rev-parse 9e3e472` |
| Main evolution after requested base | 766 commits; requested base is an ancestor | `git rev-list --count 9e3e472..adec616; git merge-base --is-ancestor 9e3e472 adec616` |
| Root Python scope | 77 files: 74 `acs_*.py` plus 3 `warehouse_*.py` | `python3 docs/audit/2026-09-26/measure_structure.py` → `root_py`, `acs_root_py` |
| Canonical schema/resource scope | 21 `acs_*.json` files | `python3 docs/audit/2026-09-26/measure_structure.py` → `canonical_json` |
| Browser scope | 44 files, including 41 JavaScript modules/scripts | `python3 docs/audit/2026-09-26/measure_structure.py` → `frontend_files`, `frontend_javascript` |
| Backend static dependency cycles | 3 strongly connected components: authority/layout, plan-review/warehouse vertical gate, workspace HTTP/service | `python3 docs/audit/2026-09-26/measure_structure.py` → `backend_module_sccs` |
| Browser static import cycles | 0 in the measured declared import graph | `python3 docs/audit/2026-09-26/measure_structure.py` → `frontend_static_sccs` |
| Browser late-binding component | 7 modules join one component when `__ACS_LATE` ownership is included | `python3 docs/audit/2026-09-26/measure_structure.py` → `frontend_with_late_sccs` |
| Proposed grouping of the measured edges | 0 cross-feature cycles in either half; no omitted scoped source files | `python3 docs/audit/2026-09-26/measure_structure.py` → `proposed_backend_sccs`, `proposed_frontend_sccs`, inventory fields |
| Historical splitter check on the externalized page | Exit 2: `no module script in page — already split?` | `node tools/frontend_split.js --check` (run against the unchanged source with installed dependencies) |
| Historical co-change sample | Of the last 80 non-merge commits at `adec616`, 23 touched the scoped source. Workspace service changed in 8; connected workspace in 6. Workspace service and residential manifest changed together in 3; service and browser connected workspace together in 2. | `python3 docs/audit/2026-09-26/measure_structure.py` → `history`; underlying command `git log adec616 -80 --format=COMMIT:%H --name-only --no-merges` |
| Branch Phase-0 install/gates | `npm install`, integration, index, API-base, CSP, deploy and bundle commands all exit 0 | Exact requested commands rerun in `audit/acs-architecture-20260926`; logs captured outside the repository in `architecture-verification/` |
| Bare CI entry command | Exit 64, verbatim: `ci_run: --runner is required` — same baseline invocation limitation | `ACS_ENV=test bash tools/ci_run.sh` |
| Documentation claim gate | Exit 1; current-state block matches; browser CSP claim cannot be measured without Chromium — same baseline environmental failure | `python3 tools/check_doc_claims.py` |
| Documentation map/graph controls | PASS: full source coverage, unique targets, Markdown agreement; sound DAG accepted and deliberately added backend/browser reverse edges detected | `python3 docs/audit/2026-09-26/measure_structure.py --verify`; negative controls change in-memory copies only |

The co-change sample supports a boundary around connected workspace orchestration. It does **not** measure developer search time, merge-conflict cost, incident recovery time, customer conversion, or a migration return on investment. No savings estimate is invented.

<!-- ACS:CURRENT-STATE:END -->

## Measurement boundary and design decision

`measure_structure.py` reads Python imports with `ast`, including imports nested inside functions. Its browser scan recognizes the repository's explicit static import statements, literal dynamic import calls, and declared `__ACS_LATE` owners/readers. It also names the inspected residential-quality dispatch calls explicitly. It is a transparent inventory aid, not a replacement for `test_module_graph.js` or a complete JavaScript program analysis.

Dynamic `window.ACS`, `ACS_AUTH`, event callbacks, boot-to-application calls, reflection, and subprocess imports need runtime ownership tests before any migration. Full dynamic feature isolation is **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** for live integration; local dispatch coverage is also not established by this inventory. The proposed DAG is a constrained future import policy, not a claim that all present runtime coupling has vanished.

Required documents were inspected for architectural contracts: `KNOWN-ISSUES.md`, `VERIFICATION-RUNBOOK.md`, the `PHASE*.md` set, and `tools/frontend_lazy.txt`. Historical verification counts and packaging directions in those documents are not substituted for this run's `BASELINE.md`. In particular, old instructions to alter import maps or restore removed shims must not override the current source gates.

The candidate feature list changes for these reasons:

- **Plan revisions** are distinct from **connected workspace orchestration**. `acs_plan_review` and semantic locks are durable domain authority; HTTP, provider jobs, file inputs, and artifact delivery change for different reasons. Folding both into “understanding” would create a dependency cycle because generation also consumes revision contracts.
- **Engineering changes** owns layout repair together with authority and approval. The measured authority/layout mutual import stays inside this feature. Validation remains a lower read-only dependency, and the regulatory refusal remains intact.
- **Presentation** keeps backend visual compilation, material quality, and architectural detail in the same feature with internal submodules. Their public use case is derived presentation; none becomes an authority to edit engineering geometry.
- The browser **model workbench** stays broader than “viewer” or “materials.” Its late-bound floor plates, disciplines, camera, live model, renderer and authoring state are a shared execution contract. Drawing feature boxes around those current modules would conceal a cycle. Optional BIM, documentation, walkthrough and inspection remain consumers.
- Browser **application composition** owns lazy panel loading, viewport-to-workspace wiring, residential presentation orchestration and async generation delivery. Those adapters connect multiple features; they are not reusable domain services. Composition may depend on features; features must eventually receive narrow callbacks or dispatch events instead of calling composition implementations.
- **Trust/provenance** is not made into an independent browser feature merely because it has a directory. Pure review/status vocabulary belongs in the shared kernel; render-linked trust wiring belongs with the workbench that owns its state. A future independent trust inspector requires an injected snapshot contract first.

A cycle in the measured graph is not itself a reported product defect: imports inside call paths may be intentional. It is evidence against pretending that a proposed feature boundary already exists.

## Target layout and public contracts

The target uses `acs/features/<feature>/` for backend features and `public/app/features/<feature>/` for browser features. Each feature owns its **models**, **services**, and **controllers** responsibilities. “Controller” means the use-case boundary callable from another feature or the application, not an unnecessary HTTP endpoint. Existing mixed modules remain intact until a separately tested extraction justifies splitting them. No empty folders, replacement domain model, generic repository framework, or duplicate service layer is created to satisfy a naming pattern.

The eventual concrete shape is:

- Backend feature: `models/` holds its schemas and domain contracts; `services/` holds the existing implementation modules; `controllers/` holds its existing route/command boundary or a justified extraction of the public entry functions.
- Browser feature: `models/` holds feature data contracts; `services/` holds pure behavior and generated mirrors; `controllers/` holds its UI/renderer adapters. Generated ownership is still recorded in the generator, regardless of the folder containing its output.
- `acs/shared_kernel/` and `public/app/shared/` contain only truly shared contracts and state registries. Application composition stays outside feature ownership. The shell, boot scripts, stylesheet contracts, and import-map sidecar retain their existing published paths in the first migration stages.

The move map later in this document gives every existing file a concrete target. It does not pretend a mixed generated file can be mechanically divided into new models/services/controllers without regenerating it. The responsibilities below identify the extraction boundary if that later becomes worthwhile.

### Backend feature responsibilities

Names in the public-surface column are existing functions/classes, not invented service contracts. “Models / services / controllers” describe owned responsibilities; the file map preserves an existing mixed implementation as a unit until an extraction is separately proven.

| Feature / owned use case | Models | Services | Controllers / public surface |
|---|---|---|---|
| `platform` — admit, constrain and observe requests | Authentication/error/job/upload result contracts | Authentication, upload parsing, limits, CPU isolation, logging, build identity | `authorize_asgi`, `maybe_handle`, `AsyncGenerationMiddleware`, upload validators, `health_status` |
| `source_evidence` — carry authenticated evidence and disclose unavailable rule authority | Rule, source, ingestion and occupancy schemas | Evidence hashing, rule-pack state transitions, catalogue research | Existing ingestion/occupancy validation APIs and `research`; no fabricated regulatory thresholds |
| `revision_identity` — make derived results traceable and reject stale snapshots | Revision schema and snapshot records | Canonicalisation and stable hashes | `revision`, `snapshot_result`, `check_result_integrity`, `apply_integrity` |
| `geometry` — derive represented architecture and discipline topology | Architecture/structure/MEP/FLS schemas; relationship, route and distance records | Geometry compilers and factual navigation/egress queries | `compile_architecture`, `compile_structure`, `compile_mep`, `compile_fls`, `find_path`, `measure_path` |
| `coordination` — reconcile multidisciplinary conflicts | Clash/snapshot schema | Broad phase, conflict calculation and reconciliation | `compile_coordination`, `reconcile`, `set_status`, `check_snapshot` |
| `validation` — report geometric/topological defects without changing the model | Issue shape and declared residential access facts | `validate_building`, residential reachability and opening-collision checks | `format_issues`, `issues`, `detail_issues`; public checker stays deterministic/read-only |
| `authoring` — preview and commit controlled legacy edits | Authoring and workspace schemas; transaction/UI state | Target resolution, preview, validation, revisions and inspector model | `create_project`, `preview_command`, `commit_transaction`, `undo`, `redo` |
| `engineering_changes` — classify and approve proposed geometric changes | Engineering-change registry and proposal records | Authority planner and overlap/layout repair | `plan`, `plan_with_model`, `autofix`, `approve`, `reject`; layout/authority mutual calls stay internal |
| `plan_revision` — maintain approved, locked and persisted plan identity | `Revision`, `Approval`, `PlanWorkspace`, bound locks and `PlanStorePort` | Scorecard, semantic diff, store/reload adapters and warehouse vertical-stage admission | Domain methods on `PlanWorkspace`/`PlanLockWorkspace`, `load_workspace`, store port; provider orchestration stays outside |
| `understanding` — turn a brief into a bounded candidate model | Program registry, provider configuration, chunk/residential manifest and generation job records | Provider calls, budgets, chunking, residential candidate planning | `understand`, `understand_deep`, `understand_images`, `GenerationJob`/`JobRunner`; acceptance stays with plan revision/validation |
| `connected_workspace` — deliver authenticated project workflows | Request/command, source-reference and projection contracts | Candidate bridge, persisted commands, chat, source inputs, approved artifacts and workspace job orchestration | `PlanCommandMiddleware`, `WorkspaceMiddleware`, `execute_plan_command`, `generate_and_save`, `artifact`; the measured HTTP/service component stays internal |
| `bim_exchange` — stage or serialize semantic exchange | BIM exchange schema and STEP records | IFC serialization/parsing, opening identity and exchange validation | `build_exchange`, `export_ifc`, `stage_import`, `validate_exchange` |
| `documentation` — derive drawings and quantities from represented facts | Documentation views, sheets, schedules and artifact schema | Plan/elevation/section geometry, dimensions, annotations and quantities | Existing view/sheet export APIs; unknown facts stay disclosed |
| `presentation` — derive visual outputs without changing canonical engineering | Visual/render/PBR/detail schemas | Visual compiler, materials, scene descriptors, camera and architectural detail | `compile_visual_scene`, compiler export API, `render_request`, PBR/detail config and capture APIs |
| `walkthrough` — query navigation and interaction on a read-only runtime scene | Runtime scene/state schema | Collision, selection, portal and simulation queries | `compile_runtime_scene`, `create_runtime_state`, `move_query`, `set_portal_state` |

`acs/shared_kernel/` owns existing shared error envelopes, project/opening identities and worker-progress contracts. It is a restricted contract package, not an invitation to move unrelated helpers into `utils`. `acs/application/controllers/acs_understand_api.py` remains the composition root; its middleware and route registration order must be preserved.

### Browser feature responsibilities

| Feature / owned use case | Models | Services | Controllers / public surface |
|---|---|---|---|
| `connected_workspace` — review, approve and persist a plan before viewing/exporting it | Brief/residential program and review-packet modules | Existing review/upload and approved-artifact behaviors | Connected workspace, semantic locks, brief review, residential choices and approved viewer; preserve their existing exported functions |
| `model_workbench` — apply, inspect and render a live building | Current canonical-model, material, discipline, authoring and trust state contracts | Viewer/standards/discipline implementations and generated authoring/PBR mirrors | Scene, PBR bridge, model application, trust wiring and viewport selection; preserve `ACS.setModel`, `ACS.exportModel`, render diagnostics and authoring APIs |
| `walkthrough` — deterministic scene interaction | Runtime spec/state in the generated mirror | Generated runtime queries | Existing published runtime entry points; preserve the single generated module until a generator-level split is justified |
| `workspace_inspector` — inspect/edit a represented project | Workspace tree, property and UI state models | Generated workspace view-model logic | Generated workspace panel; public `ACS.workspace` |
| `bim_exchange` — exchange the active model | Exchange spec/result and import staging | Generated exchange implementation | Public `ACS.bim` panel/API |
| `documentation` — request model-derived documents | Document/view/schedule spec and results | Generated document implementation | Public `ACS.docs` panel/API |
| `presentation` — optional render/detail configuration | Render/detail specs and presentation-only settings | Generated render/detail services | Generated detail bridge and `ACS.render`/`ACS.archdetail` panels |

The shell boot files and API-base configuration remain platform infrastructure at their existing URLs. `public/app/main.js` remains the only module entry. `public/app/application/controllers/` owns cross-feature dispatch: the lazy panel entry, viewport-selection runtime adapter, async generation delivery and residential-quality orchestration. The last of these calls `ensureLayer('archdetail')`; assigning it to a lower feature would hide a reverse dependency on the loader. The same concern applies to callbacks that still cross through `window.ACS`: introduce/inject the lower-owned port before claiming feature isolation.

### Dependency direction

Each arrow means **consumer → provider**. The following tables are generated from the measured import/late-binding graph after applying the proposed feature assignment. They also define the permitted direction for future package imports. All inbound consumers are listed explicitly. A feature not listed as an inbound consumer must not import that feature's internals. Application composition may call public feature controllers and pass adapters, while a feature must not import application composition.

The backend graph excludes nonliteral dynamic imports and runtime subprocess resolution; the browser graph excludes unresolved global dispatch. Required runtime-seam work is stated in the migration stages. This limitation must not be removed by changing the diagram or suppressing a test.

Backend:

| Feature | May depend on | May be consumed by |
|---|---|---|
| `shared_kernel` | No measured feature dependency | `platform`, `revision_identity`, `authoring`, `understanding`, `connected_workspace`, `bim_exchange`, `composition` |
| `platform` | `shared_kernel` | `understanding`, `connected_workspace`, `composition` |
| `source_evidence` | No measured feature dependency | `revision_identity`, `authoring`, `engineering_changes`, `connected_workspace`, `bim_exchange`, `documentation`, `presentation`, `walkthrough` |
| `revision_identity` | `shared_kernel`, `source_evidence` | `coordination`, `presentation` |
| `geometry` | No measured feature dependency | `coordination`, `authoring`, `engineering_changes`, `documentation`, `presentation` |
| `coordination` | `geometry`, `revision_identity` | `presentation` |
| `validation` | No measured feature dependency | `engineering_changes`, `understanding`, `connected_workspace` |
| `authoring` | `geometry`, `shared_kernel`, `source_evidence` | `engineering_changes` |
| `engineering_changes` | `authoring`, `geometry`, `source_evidence`, `validation` | `composition` |
| `plan_revision` | No measured feature dependency | `understanding`, `connected_workspace` |
| `understanding` | `plan_revision`, `platform`, `shared_kernel`, `validation` | `connected_workspace`, `composition` |
| `connected_workspace` | `plan_revision`, `platform`, `shared_kernel`, `source_evidence`, `understanding`, `validation` | `composition` |
| `bim_exchange` | `shared_kernel`, `source_evidence` | No measured feature dependency |
| `documentation` | `geometry`, `source_evidence` | No measured feature dependency |
| `presentation` | `coordination`, `geometry`, `revision_identity`, `source_evidence` | No measured feature dependency |
| `walkthrough` | `source_evidence` | No measured feature dependency |
| `composition` | `connected_workspace`, `engineering_changes`, `platform`, `shared_kernel`, `understanding` | No measured feature dependency |

Browser:

| Feature | May depend on | May be consumed by |
|---|---|---|
| `platform` | No measured feature dependency | No measured feature dependency |
| `shared_kernel` | No measured feature dependency | `composition`, `model_workbench`, `workspace_inspector` |
| `composition` | `bim_exchange`, `connected_workspace`, `documentation`, `model_workbench`, `presentation`, `shared_kernel`, `walkthrough`, `workspace_inspector` | No measured feature dependency |
| `connected_workspace` | No measured feature dependency | `composition` |
| `model_workbench` | `shared_kernel` | `composition`, `walkthrough`, `workspace_inspector`, `bim_exchange`, `documentation`, `presentation` |
| `walkthrough` | `model_workbench` | `composition`, `workspace_inspector` |
| `workspace_inspector` | `model_workbench`, `shared_kernel`, `walkthrough` | `composition` |
| `bim_exchange` | `model_workbench` | `composition` |
| `documentation` | `model_workbench` | `composition` |
| `presentation` | `model_workbench` | `composition` |

## Generator ownership is part of the migration

The generated headers identify the block generators, but the wrapper `import`/`export` lists and module destinations were produced by `tools/frontend_split.js`. The bridge headers merely say “module scope”; that is not permission to hand-edit them. Inspection of the owning builders resolves the real bridge templates below.

| Current generated output | Body/spec owner | Wrapper/path owner and required change |
|---|---|---|
| `public/app/generated/runtime.js` | `tools/build_runtime_browser.py`, `acs_runtime.py` / `acs_runtime.json` | Remap builder `JS_TARGET` and generated wrapper imports through an idempotent module emitter |
| `public/app/generated/authoring.js` | `tools/build_authoring_browser.py`, authoring schema/implementation | Same; preserve symbol names and authoring identity |
| `public/app/generated/workspace-ui.js` | `tools/build_workspace_ui.py`, workspace schema/implementation | Same; preserve panel DOM/style markers and lazy registration |
| `public/app/generated/render-engine.js` | `tools/build_render_browser.py`, render schema/implementation | Same; keep optional panel deferred |
| `public/app/generated/bim.js` | `tools/build_bim_browser.py`, BIM schema/implementation | Same; preserve authoring imports and import staging authority |
| `public/app/generated/docs.js` | `tools/build_docs_browser.py`, documentation schema/implementation | Same; preserve discipline/standards imports and export parity |
| `public/app/generated/pbr.js` | `tools/build_pbr_browser.py`, PBR schema/implementation | Remap `JS_TARGET` and `LATE_PATH`; keep floor-plate/rack exports eager |
| `public/app/generated/pbr-bridge.js` | `tools/build_pbr_browser.py` + `tools/_pbr_bridge_block.js` | Remap `BRIDGE_TARGET` and wrapper imports; preserve `BRIDGE_LATE` ownership and render-loop hook |
| `public/app/generated/arch-detail.js` | `tools/build_archdetail_browser.py`, detail schema/implementation | Remap `JS_TARGET`, PBR imports and canonical resource path |
| `public/app/generated/arch-detail-bridge.js` | `tools/build_archdetail_browser.py` + `tools/_archdetail_bridge_block.js` | Remap `BRIDGE_TARGET`, PBR/scene imports and deferred dependency order |

`tools/build_visual_browser.py` also writes marker-owned pieces in the scene/workspace wiring modules; it searches module text through `app_source` and must continue finding unique owners after any remap. It cannot be omitted just because its targets are outside `generated/`.

The old splitter reads an inline module from `public/index.html`. On this already-split tree its check refuses with `no module script in page — already split?`. Therefore “update `FILES` and rerun the splitter” is **not an executable migration plan**. Before moving generated output, add an idempotent wrapper/path emitter that accepts the current external module tree, prove unchanged output at the existing layout, and only then give it the target map. Keep the existing builder scripts at their CLI paths, and update their target/resource declarations. Do not reconstruct a monolith or copy hand-maintained import lists into generated files.

## Exact gate and packaging work

These are future required edits, not changes performed in this audit. A row marked “retain” still requires its existing command to pass against the new package layout; it is not a skipped gate.

| Contract owner | Exact migration work | Negative control required before trusting the changed guard |
|---|---|---|
| `tools/check_index_guard.py` | Remap `LAZY_ENTRY`, `ENGINE_FILES` and any declared registry exceptions. Continue scanning `.js` and `.mjs` recursively. Keep the single `/app/main.js` shell entry, module-size ceiling and orphan checks. | Omit a moved eager file; duplicate a main import; statically import a declared lazy module; remove the genuine engine while leaving approved-viewer present. Each must fail; a correctly remapped sound tree must pass. |
| `tools/check_integration.py` | Keep DOM/JS markers and render-diagnostic requirements. Update any literal scene, schema and build-token host references via the shared layout reader. Keep shell and app source distinct. | Duplicate/remove a generated marker or required live-render hook; wrong canonical schema must fail. |
| `tools/check_csp_hash.py` | Retain shell, sidecar and Netlify paths in this proposal. Internal relative-module moves need no import-map change. If the import map actually changes, regenerate its exact body hash in page, sidecar and CSP together. | Change a single import-map byte in a temporary tree; gate must reject stale sidecar/CSP without relaxing policy. |
| `tools/check_api_base.py` | Retain `boot/api-base.js` and the allowed backend origin. Ensure source scanning still includes moved modules and `acsFetchJSON` callers. Do not add an API origin just to make tests pass. | Introduce a second configured base or remove the configured origin from `connect-src`; reject both; same-origin sound case passes. |
| `tools/check_doc_claims.py` | Keep the canonical current-state block in `KNOWN-ISSUES.md`; regenerate bundle measurements before regenerating state. If measured source readers move, update them once. Preserve historical-claim exclusion and partial-verification wording. | Perturb a measured current figure or assertion claim and prove failure; preserve a clearly historical statement unchanged. |
| `tests/remediation/test_module_graph.js` | Update only path identities/boot classifier if needed: `LAZY_ENTRY`, registry destinations and declared map. Retain parser-derived import DAG, load-order, free-identifier and `__ACS_LATE` owner/read constraints. Revalidate the current parser rather than assuming the inventory helper proves it. | Add a back-edge, move a late-binding read to evaluation time, publish the same name from another owner, or leave a free identifier unresolved; each must fail. |
| `tests/deploy/verify_deploy.py` | Replace flat-root `acs_` filename/import matching with package-aware import closure and explicit runtime resources. Include package imports, the warehouse modules and artifact worker subprocess paths. Remap injector/spec catalogue, canonical-file classification, boot/stylesheet/engine host references and source-specific assertions. Preserve the container's no-provider/no-compiler eager-import checks where they apply. | Remove a transitive package module/schema from the Docker context and prove failure; include an orphan runtime resource and prove classification refuses it. |
| `tests/phase3/lib/extract_browser_bundle.js` | Remap `FULL`, `PREFIX`, `PICK` identities and `tests/lib/app_source.js` `PURE`/`REGISTRIES`. Keep load order, pure-prefix measurement, late publications and content-based cache stamp intact. Preserve the bridge suffix convention or replace it with an explicit semantic manifest. | Reorder a dependency, remove a picked declaration, or omit a registry publication; extraction must fail. Byte-identical behavioral fixtures must still pass in the sound case. |
| `public/app/main.js` | Rewrite relative paths in place without reordering evaluation. Keep only side-effect imports; do not introduce eager feature barrels that pull lazy modules into boot. | Reordering the PBR/slab or camera owner relative to a consumer must be caught by the module graph and rendering regression. |
| `tools/frontend_lazy.txt` + panel entry | Rewrite each deferred path and its literal dynamic import as the same change. Preserve sole lazy-loader ownership, warm-panel same-tick opening and first-load failure handling. PBR remains eager. | Cold/warm panel tests, forced import rejection and intentional eager import of a lazy module; same-tick DOM assertion must remain unchanged. |
| `tools/app_source.py` + `tests/lib/app_source.js` | Update `PURE`, registry paths and layout discovery together; retain recursive source discovery and full eager/lazy order. Keep boot/style published paths stable for staged moves. | A source visible to the browser but absent from the reader must be detected; Python and JavaScript readers must agree. |
| `tools/bundle_report.py` | Remap the connected-workspace artifact census and any path labels. Recompute actual eager/deferred reachability and bytes after each stage. No claimed saving from a mere rename. | A deliberately restored eager import must increase measured eager reachability; no fixed target number replaces measurement. |
| Canonical schema loaders and browser builders | Replace `__file__`-sibling assumptions when schemas move to `models/`, preferably using explicit package resources. Preserve payload bytes and schema identities. Update builder `SPEC_PATH` and module target declarations as a unit. | Launch from a working directory outside the checkout and from the built container; a missing schema must fail clearly. |
| `netlify.toml` | Retain publish `public`, build entry, pinned API origin and security headers. Retain the external boot, shell, stylesheet and sidecar URLs in early stages. CSP changes only when its exact import-map body changes. | Run build plus production-header/CSP checks on a preview; no `unsafe-inline`/`unsafe-eval` escape hatch. |
| `Dockerfile` | Copy the runtime Python package and its canonical resources explicitly; preserve nonroot user and source provenance. Keep the root import shim during transition, then change the uvicorn module target and closure gate together in a separate stage. Recheck subprocess importability. | Container startup, `/health`, authenticated command import path and isolated worker smoke checks; deliberately omit one required package file and prove build/closure rejection. |
| `render.yaml` | Retain service, region, instance/limiter contract, environment names and `/health`; no scaling or provider change is part of a folder migration. If an entry path is eventually declared here, update it with the Docker entry change. | Verify health/readiness against a branch preview/container; a renamed entry with old deployment configuration must fail before merging. |
| `requirements.lock` and `requirements.txt` | No dependency changes are required by this proposal. Retain pinned dependencies; do not regenerate locks to hide a packaging failure. | Install the existing locked environment and import from the packaged working directory. A new dependency requires a separate measured justification. |
| Generator wrappers/templates and build stamping | Add the external-tree emitter before using the target map; remap builder targets and `tools/frontend_split.js` ownership metadata together. Keep `stamp_build_tokens.py` target stable unless its host actually moves. | Regenerate twice with no diff; missing marker/duplicate owner must fail; remove a required binding and prove the graph gate reacts. |

Existing guard mutation results belong to `BASELINE.md` and the other audit streams; this document does not claim to have modified or mutation-tested those guards. No new production guard is added here. The negative controls above are explicit acceptance work for a future migration.

## File-by-file conditional move map

This map exhausts the scoped root Python modules, their canonical JSON resources, and every tracked file under `public/app/`. A repeated path in the destination column means **retain at that path**, not an omitted decision. Backend and frontend shared contracts/application composition are intentionally outside feature folders. Generator scripts, templates, tests, CLI tools and deployment files stay at their existing paths; their required internal edits are listed above. This is a target map only: none of these moves has been performed.

The backend map preserves source module basenames to avoid coupling a folder change with an API rename. Temporary root compatibility modules would remain until all consumers and subprocess import paths are migrated; they are not duplicate implementations. A plain `from ... import *` shim is not assumed safe: private helper imports, monkeypatches, mutable module state, class identity and worker pickling must be tested before choosing a compatibility mechanism.

Generated JS remains whole under `services/generated/` or `controllers/generated/`; splitting its embedded spec/model, service and panel concerns would be a generator-level extraction in a later stage. The ownership table above, not a hand edit to the destination file, controls that work.

### Backend Python

| Old path | Conditional target path |
|---|---|
| `acs_api_errors.py` | `acs/shared_kernel/acs_api_errors.py` |
| `acs_arch.py` | `acs/features/geometry/services/acs_arch.py` |
| `acs_archdetail.py` | `acs/features/presentation/services/acs_archdetail.py` |
| `acs_async_jobs.py` | `acs/features/platform/services/acs_async_jobs.py` |
| `acs_auth.py` | `acs/features/platform/services/acs_auth.py` |
| `acs_auth_gateway.py` | `acs/features/platform/controllers/acs_auth_gateway.py` |
| `acs_authoring.py` | `acs/features/authoring/services/acs_authoring.py` |
| `acs_bim.py` | `acs/features/bim_exchange/services/acs_bim.py` |
| `acs_build_info.py` | `acs/features/platform/services/acs_build_info.py` |
| `acs_compiler.py` | `acs/features/presentation/services/acs_compiler.py` |
| `acs_coord.py` | `acs/features/coordination/services/acs_coord.py` |
| `acs_cpu_pool.py` | `acs/features/platform/services/acs_cpu_pool.py` |
| `acs_design_research.py` | `acs/features/source_evidence/services/acs_design_research.py` |
| `acs_distance.py` | `acs/features/geometry/services/acs_distance.py` |
| `acs_docs.py` | `acs/features/documentation/services/acs_docs.py` |
| `acs_egress.py` | `acs/features/geometry/services/acs_egress.py` |
| `acs_engineering_approval.py` | `acs/features/engineering_changes/controllers/acs_engineering_approval.py` |
| `acs_engineering_authority.py` | `acs/features/engineering_changes/services/acs_engineering_authority.py` |
| `acs_fls.py` | `acs/features/geometry/services/acs_fls.py` |
| `acs_generation.py` | `acs/features/understanding/services/acs_generation.py` |
| `acs_generation_job.py` | `acs/features/understanding/services/acs_generation_job.py` |
| `acs_ingest.py` | `acs/features/source_evidence/services/acs_ingest.py` |
| `acs_layout.py` | `acs/features/engineering_changes/services/acs_layout.py` |
| `acs_logging.py` | `acs/features/platform/services/acs_logging.py` |
| `acs_mep.py` | `acs/features/geometry/services/acs_mep.py` |
| `acs_navigation.py` | `acs/features/geometry/services/acs_navigation.py` |
| `acs_occupancy.py` | `acs/features/source_evidence/services/acs_occupancy.py` |
| `acs_opening_identity.py` | `acs/shared_kernel/acs_opening_identity.py` |
| `acs_pbr.py` | `acs/features/presentation/services/acs_pbr.py` |
| `acs_plan_bridge.py` | `acs/features/connected_workspace/services/acs_plan_bridge.py` |
| `acs_plan_chat_job.py` | `acs/features/connected_workspace/services/acs_plan_chat_job.py` |
| `acs_plan_chat_orchestration.py` | `acs/features/connected_workspace/services/acs_plan_chat_orchestration.py` |
| `acs_plan_chunks.py` | `acs/features/understanding/services/acs_plan_chunks.py` |
| `acs_plan_commands.py` | `acs/features/connected_workspace/controllers/acs_plan_commands.py` |
| `acs_plan_http.py` | `acs/features/connected_workspace/controllers/acs_plan_http.py` |
| `acs_plan_lock_binding.py` | `acs/features/plan_revision/models/acs_plan_lock_binding.py` |
| `acs_plan_options.py` | `acs/features/plan_revision/services/acs_plan_options.py` |
| `acs_plan_overlap_repair.py` | `acs/features/connected_workspace/services/acs_plan_overlap_repair.py` |
| `acs_plan_persisted_commands.py` | `acs/features/connected_workspace/controllers/acs_plan_persisted_commands.py` |
| `acs_plan_projection.py` | `acs/features/connected_workspace/services/acs_plan_projection.py` |
| `acs_plan_review.py` | `acs/features/plan_revision/models/acs_plan_review.py` |
| `acs_plan_scorecard.py` | `acs/features/plan_revision/services/acs_plan_scorecard.py` |
| `acs_plan_semantic_diff.py` | `acs/features/plan_revision/services/acs_plan_semantic_diff.py` |
| `acs_plan_semantic_locks.py` | `acs/features/plan_revision/services/acs_plan_semantic_locks.py` |
| `acs_plan_session.py` | `acs/features/connected_workspace/services/acs_plan_session.py` |
| `acs_plan_sources.py` | `acs/features/connected_workspace/services/acs_plan_sources.py` |
| `acs_plan_store.py` | `acs/features/plan_revision/services/acs_plan_store.py` |
| `acs_plan_store_port.py` | `acs/features/plan_revision/models/acs_plan_store_port.py` |
| `acs_plan_store_reload.py` | `acs/features/plan_revision/services/acs_plan_store_reload.py` |
| `acs_programs.py` | `acs/features/understanding/services/acs_programs.py` |
| `acs_project.py` | `acs/shared_kernel/acs_project.py` |
| `acs_provider.py` | `acs/features/understanding/services/acs_provider.py` |
| `acs_provider_budget.py` | `acs/features/understanding/services/acs_provider_budget.py` |
| `acs_rate_limit.py` | `acs/features/platform/services/acs_rate_limit.py` |
| `acs_relations.py` | `acs/features/geometry/services/acs_relations.py` |
| `acs_render.py` | `acs/features/presentation/services/acs_render.py` |
| `acs_residential_access.py` | `acs/features/validation/services/acs_residential_access.py` |
| `acs_residential_generation.py` | `acs/features/understanding/services/acs_residential_generation.py` |
| `acs_residential_layout.py` | `acs/features/understanding/services/acs_residential_layout.py` |
| `acs_residential_manifest.py` | `acs/features/understanding/services/acs_residential_manifest.py` |
| `acs_revision.py` | `acs/features/revision_identity/services/acs_revision.py` |
| `acs_rules.py` | `acs/features/source_evidence/services/acs_rules.py` |
| `acs_runtime.py` | `acs/features/walkthrough/services/acs_runtime.py` |
| `acs_struct.py` | `acs/features/geometry/services/acs_struct.py` |
| `acs_supabase_plan_store.py` | `acs/features/plan_revision/services/acs_supabase_plan_store.py` |
| `acs_understand.py` | `acs/features/understanding/services/acs_understand.py` |
| `acs_understand_api.py` | `acs/application/controllers/acs_understand_api.py` |
| `acs_upload_security.py` | `acs/features/platform/services/acs_upload_security.py` |
| `acs_validate.py` | `acs/features/validation/services/acs_validate.py` |
| `acs_visual.py` | `acs/features/presentation/services/acs_visual.py` |
| `acs_workspace.py` | `acs/features/authoring/services/acs_workspace.py` |
| `acs_workspace_http.py` | `acs/features/connected_workspace/controllers/acs_workspace_http.py` |
| `acs_workspace_progress.py` | `acs/shared_kernel/acs_workspace_progress.py` |
| `acs_workspace_service.py` | `acs/features/connected_workspace/services/acs_workspace_service.py` |
| `warehouse_program_feasibility.py` | `acs/features/connected_workspace/services/warehouse_program_feasibility.py` |
| `warehouse_soft_area_fit.py` | `acs/features/connected_workspace/services/warehouse_soft_area_fit.py` |
| `warehouse_vertical_stage_gate.py` | `acs/features/plan_revision/services/warehouse_vertical_stage_gate.py` |

### Canonical model/schema resources

| Old path | Conditional target path |
|---|---|
| `acs_arch.json` | `acs/features/geometry/models/acs_arch.json` |
| `acs_archdetail.json` | `acs/features/presentation/models/acs_archdetail.json` |
| `acs_authoring.json` | `acs/features/authoring/models/acs_authoring.json` |
| `acs_bim.json` | `acs/features/bim_exchange/models/acs_bim.json` |
| `acs_coord.json` | `acs/features/coordination/models/acs_coord.json` |
| `acs_docs.json` | `acs/features/documentation/models/acs_docs.json` |
| `acs_engineering_changes.json` | `acs/features/engineering_changes/models/acs_engineering_changes.json` |
| `acs_fls.json` | `acs/features/geometry/models/acs_fls.json` |
| `acs_ingest.json` | `acs/features/source_evidence/models/acs_ingest.json` |
| `acs_mep.json` | `acs/features/geometry/models/acs_mep.json` |
| `acs_occupancy.json` | `acs/features/source_evidence/models/acs_occupancy.json` |
| `acs_pbr.json` | `acs/features/presentation/models/acs_pbr.json` |
| `acs_programs.json` | `acs/features/understanding/models/acs_programs.json` |
| `acs_render.json` | `acs/features/presentation/models/acs_render.json` |
| `acs_revision.json` | `acs/features/revision_identity/models/acs_revision.json` |
| `acs_rules.json` | `acs/features/source_evidence/models/acs_rules.json` |
| `acs_runtime.json` | `acs/features/walkthrough/models/acs_runtime.json` |
| `acs_sources.json` | `acs/features/source_evidence/models/acs_sources.json` |
| `acs_struct.json` | `acs/features/geometry/models/acs_struct.json` |
| `acs_visual.json` | `acs/features/presentation/models/acs_visual.json` |
| `acs_workspace.json` | `acs/features/authoring/models/acs_workspace.json` |

### Browser source and resources

| Old path | Conditional target path |
|---|---|
| `public/app/boot/a11y-baseline.js` | `public/app/boot/a11y-baseline.js` |
| `public/app/boot/api-base.js` | `public/app/boot/api-base.js` |
| `public/app/boot/build-info.js` | `public/app/boot/build-info.js` |
| `public/app/boot/debug-toggle.js` | `public/app/boot/debug-toggle.js` |
| `public/app/boot/engine-guard.js` | `public/app/boot/engine-guard.js` |
| `public/app/boot/style-bridge.js` | `public/app/boot/style-bridge.js` |
| `public/app/core/brief-program.mjs` | `public/app/features/connected_workspace/models/brief-program.mjs` |
| `public/app/core/disciplines.js` | `public/app/features/model_workbench/services/disciplines.js` |
| `public/app/core/plan-review-packet.mjs` | `public/app/features/connected_workspace/models/plan-review-packet.mjs` |
| `public/app/core/residential-program.mjs` | `public/app/features/connected_workspace/models/residential-program.mjs` |
| `public/app/core/standards.js` | `public/app/features/model_workbench/services/standards.js` |
| `public/app/core/viewer.js` | `public/app/features/model_workbench/services/viewer.js` |
| `public/app/generated/arch-detail-bridge.js` | `public/app/features/presentation/controllers/generated/arch-detail-bridge.js` |
| `public/app/generated/arch-detail.js` | `public/app/features/presentation/services/generated/arch-detail.js` |
| `public/app/generated/authoring.js` | `public/app/features/model_workbench/services/generated/authoring.js` |
| `public/app/generated/bim.js` | `public/app/features/bim_exchange/services/generated/bim.js` |
| `public/app/generated/docs.js` | `public/app/features/documentation/services/generated/docs.js` |
| `public/app/generated/pbr-bridge.js` | `public/app/features/model_workbench/controllers/generated/pbr-bridge.js` |
| `public/app/generated/pbr.js` | `public/app/features/model_workbench/services/generated/pbr.js` |
| `public/app/generated/render-engine.js` | `public/app/features/presentation/services/generated/render-engine.js` |
| `public/app/generated/runtime.js` | `public/app/features/walkthrough/services/generated/runtime.js` |
| `public/app/generated/workspace-ui.js` | `public/app/features/workspace_inspector/controllers/generated/workspace-ui.js` |
| `public/app/importmap.sha256` | `public/app/importmap.sha256` |
| `public/app/late-bindings.js` | `public/app/shared/late-bindings.js` |
| `public/app/main.js` | `public/app/main.js` |
| `public/app/render/scene.js` | `public/app/features/model_workbench/controllers/scene.js` |
| `public/app/render/warehouse-canonical-identity.js` | `public/app/features/model_workbench/controllers/warehouse-canonical-identity.js` |
| `public/app/shared-state.js` | `public/app/shared/shared-state.js` |
| `public/app/styles/app.css` | `public/app/styles/app.css` |
| `public/app/styles/connected-workspace.css` | `public/app/features/connected_workspace/styles/connected-workspace.css` |
| `public/app/trust/core.js` | `public/app/shared/trust-core.js` |
| `public/app/trust/wiring.js` | `public/app/features/model_workbench/controllers/trust-wiring.js` |
| `public/app/ui/approved-viewer.mjs` | `public/app/features/connected_workspace/controllers/approved-viewer.mjs` |
| `public/app/ui/brief-review.mjs` | `public/app/features/connected_workspace/controllers/brief-review.mjs` |
| `public/app/ui/connected-semantic-locks.mjs` | `public/app/features/connected_workspace/controllers/connected-semantic-locks.mjs` |
| `public/app/ui/connected-workspace.mjs` | `public/app/features/connected_workspace/controllers/connected-workspace.mjs` |
| `public/app/ui/generation-jobs.js` | `public/app/application/controllers/generation-jobs.js` |
| `public/app/ui/panels-entry.js` | `public/app/application/controllers/panels-entry.js` |
| `public/app/ui/plan-upload.mjs` | `public/app/features/connected_workspace/controllers/plan-upload.mjs` |
| `public/app/ui/residential-options.mjs` | `public/app/features/connected_workspace/controllers/residential-options.mjs` |
| `public/app/ui/residential-quality.js` | `public/app/application/controllers/residential-quality.js` |
| `public/app/ui/workspace-ui-wiring.js` | `public/app/features/model_workbench/controllers/workspace-ui-wiring.js` |
| `public/app/ui/workspace-viewport-selection-runtime.js` | `public/app/application/controllers/workspace-viewport-selection-runtime.js` |
| `public/app/ui/workspace-viewport-selection.js` | `public/app/features/model_workbench/controllers/workspace-viewport-selection.js` |

## Staged, independently revertible sequence

Each stage is a separate branch/PR. No stage pushes or merges to `main`; the user identified coupled frontend/backend automatic deployments. Each stage records its own pre-change Phase-0 outputs, adds the relevant failing contract/negative control before implementation, and reruns the same command set after it. The complete baseline failure set must be diffed before the PR. A new failure blocks the stage; a pre-existing environmental failure stays explicitly unverified, never relabeled “green.” A stage that requires live renderer, container or external-tool evidence waits for that evidence before it is accepted as green.

| Stage | Concrete deliverable | Exit evidence | Revert boundary |
|---|---|---|---|
| Ownership record — this audit | This proposal and read-only inventory helper; no application modifications | Scoped inventory complete; current source graphs measured; no claims about migrated runtime behavior | Revert documentation commit only |
| Runtime seams, before moves | Characterize all `window.ACS` ownership used by the affected feature; move multi-feature orchestration into application adapters or inject lower-owned callbacks. Establish explicit package/resource import tests without renaming anything. | Fail first on wrong owner/stale callback/missing optional panel; sound fixture silent; exact rendering, same-tick panel and model immutability contracts pass | Revert a single seam extraction; data and paths unchanged |
| Shared layout/resource readers | Introduce a path/resource manifest understood by Python and JavaScript readers, generators, closure checks and packaging; manifest initially describes existing paths | Unchanged source output and behavior; mutation proves missing module/resource is caught; all required gates pass against original layout | Revert manifest/reader commit; original layout remains |
| A low-coupling backend feature | Select the smallest measured self-contained candidate, such as geometry-only validation, only if maintainers have a concrete need. Move implementation with a proven identity-preserving root compatibility contract; adjust package resources and Docker copies in the same PR. | Same public imports and issue/output fixtures; external-cwd import; full Phase-0 diff; worker import check; no regulatory-boundary change | Revert feature/package/compatibility commit; no persisted data rewrite |
| Remaining backend, dependency order | Move leaf contracts/evidence/geometry first, then revision/authoring/coordination/plan authority, then understanding and workspace orchestration. Keep the measured mutual-import components inside the same feature. Treat every feature as a separate stage. | Package-aware closure includes schemas, warehouse gates and workers; unchanged authenticated ownership/approval behavior; all previously green gates still green | Revert the current feature stage; lower migrated features remain usable through their compatibility surface |
| External-tree generator support | Add the idempotent wrapper/path emitter, retaining current paths initially; preserve builder CLI locations and marker ownership | Repeated regeneration produces no tracked diff; generator parity, graph, CSP, integration and Node bundle extraction pass; deliberately broken wrapper fails | Revert emitter work; generated files and production layout remain at old paths |
| A browser feature at a time | Start with a deferred leaf panel after emitter support. Rewrite generator targets, module paths, lazy declaration, loader, reader and gate references together. Keep import order and old public `window.ACS` surface. | Cold/warm/error panel tests, same-tick DOM assertion, real render when relevant, parity and measured bundle report; no eagerness change unless separately authorized and proved | Revert the panel remap commit; no user data migration |
| Workbench/connected-workspace move | Move only after runtime seam checks show the intended acyclic ownership. Preserve `__ACS_LATE` owners and eager PBR until any independent tested replacement exists. Keep main and boot URLs stable. | Apply model, first frame, diagnostics, editing, approval, upload, async job resume and authenticated artifact flows pass in a branch preview; target hardware still needs its own evidence | Revert workbench remap; saved revisions use unchanged schemas |
| Compatibility retirement | Remove old import surfaces only after runtime/test/CLI/generator consumers are measured absent; separately change uvicorn target if needed | Package and subprocess import closure, clean-container startup/readiness, full suite and preview smoke pass; no consumer depends on removed alias | Revert the compatibility-retirement commit; aliases return without model/schema conversion |

Do not combine performance deferral with folder movement. A path rename must not change first-load evaluation, panel timing, provider behavior, rendering defaults, rate limits, approval authority or schema versions. A future change that needs such behavior is a separate feature PR with its own test-first evidence.

## Cost, benefit, and the case for stopping

The possible benefit is clearer ownership for plan-first workflows, easier navigation to related model/service/controller responsibilities, and a narrower place to review future feature changes. Co-change evidence supports investigating those boundaries. It does not establish that wholesale relocation is worth doing now.

The measured liabilities are concrete: backend mutual dependencies require deliberate grouping; schema files are loaded beside modules; the deploy closure assumes root filenames; browser module evaluation and late ownership are enforced; generated wrappers have no current external-tree remapping workflow; and the live application still uses global dispatch across proposed boundaries. Each is acceptance work before a move can be called safe. None is resolved by renaming directories.

A broad restructure has no demonstrated improvement to an engineer's output quality, successful generation rate, time to a usable model, external IFC acceptance, or purchase decision. The opportunity cost is spending the audit fixing layout machinery while those customer outcomes still need measurement/remediation. No person-day estimate, delivery-time promise or monetary return is supported by this stream.

Therefore the current layout is acceptable to retain. Complete customer-facing correctness and verification work first. Keep this ownership map as a review aid; revisit only when measured repeated cross-feature changes, ownership confusion, merge conflicts or packaging incidents justify the specific slice. This audit stops at the proposal. A prettier tree is not an accepted reason to begin the migration.

## Verification and unresolved limits

- **VERIFIED by read-only source measurement:** scoped inventory and target-map coverage; named backend mutual-import components; browser declared import and late-owner component; proposed grouping acyclic for the measured edge classes; actual generator/template ownership; path-sensitive gate and package assumptions. Commands are in the audit snapshot and reproducible helper.
- **VERIFIED by deliberate non-writing probe:** the historical `frontend_split.js --check` refuses the current externalized shell. This is a tooling limitation of the proposed migration, not a newly introduced regression or a reason to restore an inline application.
- **NOT VERIFIED:** whole-program dynamic ownership, feature-package runtime equivalence, regenerated moved modules, container/worker behavior after relocation, or performance benefit. No relocation occurred, so there is no migration success claim.
- **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED:** full live integration under the proposed layout, target-device render behavior, Revit interoperability, and production deployment. These are not inferred from the source graph or baseline test counts.

The exact requested Phase-0 commands were rerun on this documentation branch. The bare CI entry and the documentation claim gate retain the invocation/environment failures already recorded in `BASELINE.md`; no new failing suite was observed in that command set. The helper's source map and document agree, and deliberately reversed dependency edges are detected in memory. Install/bundle artifacts were restored before commit.

The parent's expanded application sweep is shared evidence from a source-equivalent tree, not a separate full application sweep performed by this stream. Documentation-only scope preserves the baseline's code and tests. The final audit integration must still diff branch verification against `BASELINE.md`; this proposal does not certify the other workstreams' changes.
