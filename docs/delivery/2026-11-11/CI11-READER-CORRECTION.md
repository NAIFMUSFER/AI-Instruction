# CI11 independent-reader correction — 11 November 2026

Head `14a2adf25983167f18bda0bba79eda2ce0475c6c` is not accepted. The [critical job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43070364353/job/130696285621) failed at17:41:16 UTC in `test_stair_ifc_reader.py`: IfcOpenShell returned an empty tuple for `by_type('IfcStair')`, while the new test compared it to an empty list. `() != []` is a sequence-representation mismatch; it is not evidence of an exported stair entity.

The correction requires `len(parsed.by_type(entity)) == 0` for every forbidden entity type. It preserves the same zero-entity requirement. Schema, physical identity and product-count checks precede the assertion; geometric world-bound checks follow it and had not executed at failure. The entire corrected case must pass on the next CI head before independent parsing is claimed. No production code, parser substitution, assertion removal, timeout or skip changed.

The original generic-object test passed unchanged in CI11. Async passed the previously failing computed residential save/approve/reopen/IFC case. The measured-documentation gate also passed and reached the full main browser tests. Those observations do not establish completion of the full CI11 run; the follow-up head triggers a new run and may cancel unfinished jobs under the existing workflow concurrency policy. Any cancellation remains non-success in the final evidence inventory.

Local IfcOpenShell remains unavailable. No local complete reader execution is claimed.
