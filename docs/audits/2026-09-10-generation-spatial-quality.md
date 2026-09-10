# Staged generation: spatial context and wall preservation

User report: generation quality needs improvement after the model became visible
on an iPhone. The screenshots establish appearance, not the exact model JSON or
the cause of every visible gap. This change addresses independently reproduced
defects in the production generation path at main `23c64c9`.

## Reproduced defects

| Production path | Evidence before the change | Result after the change |
| --- | --- | --- |
| `acs_plan_chunks.py:545–549`, `validate_chunk` | A room omitting `walls` was assigned `walls=none`. The actual `acs_compiler.build_room` produced **0 wall meshes** for a residential bedroom and an industrial office. | Preserve omission; the compiler's existing building-type defaults produce **4 wall meshes** for both. Explicitly open zones and industrial storage remain open. |
| `acs_plan_chunks.py:547–553`, `validate_chunk` | A supplied `wall_h=1.1` was discarded; actual compiled vertices reached **3.0 m**. | Retain valid explicit heights; the same wall vertices reach **1.1 m**. Invalid heights are reported and excluded from the accepted field. |
| `acs_understand.py:1477–1492`, `_plan_chunk` | Calls received only the requested IDs/roles and the original text, without the outline envelope, template identity, full zone manifest, or prior accepted rectangles. A controlled cooperative planner therefore overlapped chunks. | Supply compact shared context before each call, including recursive split halves. The controlled two-floor case retains all 16 rooms with no within-floor overlaps; rooms on different floors can share XY coordinates. |
| `acs_understand.py:1804–1808`, detail context | Room IDs/rectangles were flattened across all templates without template identity. Reused room IDs could not be disambiguated. | Include each room's template, level/envelope data, and the current group's `target_template`. |
| `acs_understand.py:1852–1867`, detail merge | Replacing the planned room with a partial detail response dropped role, wall mode, explicit height, finish/source metadata. A conflicting response could remove planned walls or change their height. | Merge details onto the plan; retain explicit planned rect/role/walls/height and disclose rejected changes. Previously unspecified properties can still be supplied by detailing. |

Line references above are to the production source before this change.

## Verification

`tests/remediation/test_generation_spatial_context.py` calls the actual staged
pipeline with controlled provider replies and measures wall vertices generated
by the real Python geometry compiler. It makes no network request.

- The first 10 regression cases on the original implementation: **1 passed,
  6 assertion failures, 3 errors** from absent context fields.
- Final regression suite after implementation: **12/12 passed**. Additional
  cases verify invalid-height reporting and adding properties absent in a plan.
- Existing plan chunking: **72/72 passed**. Its provider double now reads only
  the requested detail-room array; its previous scan of every `id` in the prompt
  incorrectly manufactured a room from a level ID once levels entered context.
- Generation budget: **74/74**; provider capability: **92/92**; engineering
  authority: **115/115**; CI runner regression: **78/78**.
- Python compilation, workflow YAML parsing, and `git diff --check` passed.
- The new regression is mandatory in the existing dependency/provider CI job.
  Remote CI status is tracked in the pull request.

No additional provider requests, retry rounds, or output-token ceilings are
introduced. Prompts include more input context, so input-token usage can increase.
Failed chunks remain explicitly unresolved; their placeholder geometry is never
advertised to later calls as accepted planning. Existing generated models are not
rewritten by this change.

## Acceptance still needed

The fixture planner demonstrates that the necessary information now crosses the
stage boundary. It does **not** measure how reliably DeepSeek follows it.
Live architectural quality, room-count fidelity, connected door routes, vertical
core alignment, and the appearance of a newly generated model still require
evaluation against the original description and returned JSON after deployment.
No live generation, iPhone rendering, or engineering/regulatory acceptance is
claimed for this new code at document creation.
