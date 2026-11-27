# Wiring the healthcare pack into ACS: integration plan

Status: **not wired**. `acs_healthcare_program.py` is a standalone pack (room
table, flow rules, instruction texts, deterministic checks) with its own tests
(`tests/remediation/test_healthcare_program.py`). No production module imports
it, and the UI still offers only «سكني» and «مستودع». Wiring it is a product and
architecture step for the owner to approve. This plan lists the exact steps and
files, in the order they can land, each as its own reviewed change.

Research and numbers: `docs/research/healthcare_planning.md`.

## 0. Decisions for the owner first

1. **Which typologies to offer** at launch: clinic, polyclinic (مجمع طبي), small
   hospital. Recommended: clinic and polyclinic first (one storey or a few, no
   beds, no fire compartments), small hospital second.
2. **Limits** for the step-01 form (`PROGRAM_LIMITS`), recommended:
   `clinic: {side_m: 120, levels: 6}`, `hospital: {side_m: 200, levels: 8,
   beds: 100}` (100 beds is the `MOMRA-1441` external-pharmacy threshold and
   keeps a hospital within `MAX_BUILDING_ZONES = 400` zones per job).
3. **Provider budget**: a hospital needs more calls than an apartment building
   (outline, plan chunks, repair, openings by groups of 24 rooms per template).
   `generation_command` caps `max_provider_calls` at 12; a two-ward small
   hospital needs about 10. Decide whether hospitals get a higher cap.
4. **Wording in the UI**: every healthcare plan is a concept, never a licensing
   drawing; the review shows MOH, CBAHI, SBC and Civil Defense as NOT_VERIFIED.

## 1. Registry and type detection (no behaviour change for existing types)

* `acs_programs.json`: add a `polyclinic` program (category `healthcare`, strong
  keywords «مجمع طبي», «مجمع عيادات», «مركز طبي», «polyclinic») and move those
  keywords out of `clinic`. Mirror the change in the embedded copy that
  `public/index.html` carries (the drift test enforces equality).
* `acs_programs.py`: no code change; `detect_type` returns `clinic`,
  `polyclinic` or `hospital` from the brief.
* `acs_healthcare_program.typology_of` already accepts an explicit `meta.type`.

## 2. Step-01 form and requirements (UI)

* `public/app/core/brief-program.mjs`
  * `PROGRAM_LIMITS`: add `clinic`, `polyclinic` and `hospital` entries
    (decision 2).
  * `buildBriefProgram`: accept the new `input.type` values; the limits message
    names «للمنشآت الصحية».
  * `typeLine`: «نوع المشروع: منشأة صحية / عيادة / مجمع طبي» and «نوع المشروع:
    مستشفى». The server detects the type from this line (step 1), as it does
    for warehouses today.
  * `roles` / `floorRoles`: Arabic labels for the counted roles
    (`exam_room` «غرف الكشف», `patient_room` «غرف التنويم», `operating_room`
    «غرف العمليات», `icu_room` «غرف العناية المركزة», `isolation_room` «غرف
    العزل»), taken from `ROOMS[*].ar`.
* `public/app/ui/connected-workspace.mjs`: add the options to `#cwType`; hide
  the residential-only fields for healthcare as for warehouses.
* `public/app/ui/brief-review.mjs`: add `briefStarters.clinic` and
  `briefStarters.hospital` (one polyclinic, one 40-bed hospital).
* `public/index.html` (guest page select): same options, or leave healthcare
  to signed-in users only.
* Requirements reuse existing metrics: `room_count` with role `exam_room`,
  `patient_room`, `operating_room`, `icu_room` (measured by
  `acs_plan_review._program`); no new metric is needed.
* Tests: `tests/remediation/test_brief_program.mjs` and the UI suites for the
  new options and limits.

## 3. Plan chunk contract: keep `compartment`

* `acs_plan_chunks.validate_chunk` keeps only `name`, `unit_id` and `core_id`
  besides geometry (the loop `for key in ("name", "unit_id", "core_id")`). Add
  `"compartment"` to that tuple so the hospital's fire compartments survive the
  plan_chunk stage. The repair stage already returns whole room objects.
* Test: a chunk with `compartment` keeps it; an over-long value is dropped like
  the other keys (160 characters).

## 4. Generation path (server)

New module `acs_healthcare_generation.py`, built like
`acs_residential_generation.py` but calling the pack, so the residential and
warehouse modules stay untouched:

* `prepare_layout(building, brief, requirements, budget, typology)`: same
  bounded loop as the residential one (structure, `_geometry`, one repair call,
  a second only on real progress and within budget), with
  `H.layout_findings(...)` as the findings: severity `error` are hard,
  `advisory` ride along. System text `H.repair_policy(typology, findings)`;
  context `{building, requirements, findings, brief}`.
* `detail(building, brief, budget, typology)`: openings by groups of 24 rooms
  with `H.openings_policy(typology)`; the same response validation as the
  residential `detail`; one corrective pass with `findings_to_correct =
  H.opening_findings(...)` plus `acs_residential_access.opening_collisions`.
* `acs_workspace_service.generate_plan_candidate`: after
  `detected = U.detect_type(brief)` add
  `healthcare = detected in ('clinic', 'polyclinic', 'hospital')`; then
  * `policy = H.planning_policy(typology)` (instead of `None`, which today sends
    a healthcare brief to the generic legacy prompt);
  * `prompt += H.room_program_text(typology, requirements)`;
  * after `generate_candidate`, call the new `prepare_layout` and `detail`;
  * stamp `meta.type = typology` server-side (never from the provider).
* `acs_understand`: no change; `planning_system(stage)` already routes the
  policy to the outline and plan_chunk stages.
* Tests (stub provider, **no paid calls**): a polyclinic and a hospital brief
  run end to end against recorded provider replies; a reply with a seeded
  violation buys exactly one repair; budgets are respected.

## 5. Review and approval

* `acs_plan_review.PlanWorkspace.review`: next to the villa block
  (`scopes["dwelling_program"]`), when `meta.type` is a healthcare typology run
  `blocking, advice = H.check(model, typology, requirements)`, extend `issues`
  and `advisories`, and set `scopes["healthcare_program"]` to PASS or FAIL
  (NOT_VERIFIED when geometry already fails). Older revisions review as before.
* Keep `regulatory_compliance` NOT_VERIFIED; add the healthcare authorities
  (MOH, CBAHI, SBC 801 / Civil Defense) to the disclosed NOT_EVALUATED list in
  `acs_engineering_authority` / `acs_occupancy` (Group I-2 for hospitals,
  Group B or ambulatory care for clinics). No module may print a compliance
  claim.

## 6. Generic validator adjustments

* `acs_validate.review_building`: the «حيّز عام» split warning fires for any id
  containing `unit` and larger than 30 m2. Healthcare ids such as
  `recovery_unit` would trip it; add the healthcare roles from
  `acs_healthcare_program.ROOMS` to the role exemption list (or require the
  provider to avoid `unit` in ids). Re-run
  `tests/remediation/test_validate_against_real_models.py` (its noise ceiling
  must stay at 6 models / 6 findings).
* `acs_plan_bridge.existing_geometry_verifier` already passes the two compliant
  fixtures (topology and vertical circulation PASS); no change expected.

## 7. Compiler, 2D and 3D

* `acs_compiler`: roles are free strings; healthcare rooms compile as enclosed
  rooms (full walls) with the default material. Optional: tints for healthcare
  groups in `ROLE_COLOR`, owned by the CAD/compiler stream.
* Hospital storeys should use `floor_height` of at least 4.2 m (3.0 m clear in
  ICU and OR plus services, `DHA-C2` 2.2).

## 8. Instruction budget (stated sizes)

Characters of the composed texts; the pack's tests require these exact measured
sizes (`MEASURED_INSTRUCTION_CHARS`) and the bounds below
(`INSTRUCTION_MAX_CHARS`).

| text | bound | clinic / polyclinic | hospital |
|---|---|---|---|
| planning | 4,400 | 3,074 | 4,226 |
| openings | 3,300 | 3,013 | 3,074 |
| repair | 7,000 | 5,580 | 6,732 |
| room_program | 1,000 | 587 | 868 |

Repair is measured with every repair hint present (the worst case); a real
repair carries only the codes it found. In tokens (about 4 characters a token
for English, 2.5 for Arabic) the hospital planning text is about 1,050 tokens
and the worst repair about 1,700, against about 360 and 590 for the residential
apartment planning and repair texts on the base commit (1,446 and 2,340
characters). The difference is the role table: it carries every minimum the
checks enforce, so the model is told exactly what is checked.

## 9. Rollout and removal of the guard

1. Land steps 1 and 3 (no visible change).
2. Land step 4 behind a server flag (`ACS_HEALTHCARE=1`), run the stub-provider
   tests, then a small number of paid jobs approved by the owner.
3. Land step 5 and step 2 together so the UI never offers a typology the
   review cannot check.
4. In the change that first imports the pack from the API:
   * `Dockerfile`: `COPY acs_healthcare_program.py acs_healthcare_generation.py ./`
     next to `acs_villa_program.py`;
   * `tests/deploy/verify_deploy.py`: remove `acs_healthcare_program.py` from
     `STAGED_PACKS` (that list proves today that the pack is neither reachable
     from the API nor shipped);
   * `tests/remediation/test_healthcare_program.py`: delete `NotWiredYet`.

The pack's suite already runs in CI (`.github/workflows/ci.yml`, python contract
suites).

## Open risks

* Several figures come from secondary summaries of FGI, IBC and NFPA (paywalled
  or blocked here) and SBC 201 was not read directly; confirm against the
  adopted Saudi editions before a client sees them as code values.
* The fire checks approximate travel distance by a straight line (a lower
  bound) and know nothing of fire ratings, sprinklers or exits.
* Room shapes are rectangles; real ORs, ICUs and isolation suites need equipment
  zones, pendants and pressure regimes that ACS does not model.
* A larger hospital (multiple wards per storey, CSSD, kitchens, morgue) needs
  more provider calls than the current 12-call cap allows.
