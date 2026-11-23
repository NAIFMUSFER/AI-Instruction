# CI12: preserve canonical space coordinates in IFC — 11 November 2026

PR192 head `76a90b920d84c9cef8785f3de63f82eaa508154a` is not accepted. The [required independent-reader job](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43071202758/job/130699478337) installed IfcOpenShell0.9.0.post1, opened the approved/reopened residential IFC and passed schema, identity, entity-scope and containment checks. At17:47:01 UTC its first affected world-bound assertion failed: `6.8372085` versus canonical `6.837209302325586` metres, a difference of `8.023255864131329e-7` metres. The six-decimal assertion remains unchanged.

## Reproduced cause and correction

The exporter rounded the room origin and depth to six decimals, then independently rounded the profile's half-depth. That moved the profile centre relative to its own width. An offline reconstruction of the serialized STEP numbers reproduces the discrepancy. The same isolated exporter-module comparison reproduces it with `acs_bim.py` from main `c37b5250dc4ff18ba0606add993b5afe52beebaa` and the pre-stairs parent `064f4a96fdc1941f010b0f6ab814c765acd260c5`. Those comparisons use current shared dependencies and are explicitly **not** complete historical checkouts or deployed reproductions. This is an older serializer defect exposed by the new reader, separate from the earlier stair-admission regression.

For `SPACES_ONLY`, the exchange now preserves finite canonical coordinates, heights and elevations. Its STEP writer uses round-trip decimal numbers and the unrounded half-width/depth. It does not edit the model, model hash, identity contract, approval, locks or history. `tools/build_bim_browser.py` and its generated output preserve the same space values in JavaScript. Legacy full architectural export keeps its previous numeric policy; nine representative `ALL` export results, including files and manifests, are byte-identical before and after the correction.

## Actual local evidence

- New numeric regression: two failing methods before the production change, both passing afterwards. This includes exact Python/shipped-JavaScript exchange parity, a negative level and fractional height, depth and origin.
- Existing IFC stair boundary:8 methods; connected IFC:7; computed residential fallback journey:7; legacy BIM:526 assertions passed.
- Bundle measurement:94 assertions; documentation contract:13 methods; CI gate:78 assertions passed. The measured documentation block was regenerated and checked against the changed JavaScript bytes.
- The new numeric test is included in the mandatory critical CI job. Its internal STEP reconstruction supplements the independent reader; it does not replace it.

The [local evidence manifest](evidence/ci12-precision/manifest.json) records source hashes, full local logs and any whitespace normalization. The complete IfcOpenShell case remains **not run locally**, because its package is unavailable here. Full browser/doc-claim execution also requires CI; the local documentation contract and measured-state check are narrower. Acceptance requires every job on the next head, including the unchanged independent-reader and browser tests. No retry, tolerance relaxation, skip or timeout change is part of this correction.

This fix concerns space-boundary IFC only. Physical stair entities remain unsupported in that export; legacy full architectural IFC still rejects explicit stair forms. Traversal, structural safety, code compliance, physical-phone performance and production deployment remain unverified.
