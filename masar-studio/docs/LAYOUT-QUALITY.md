# Optional measured layout improvement

## Scope and entry points
`جودة التوزيع` opens a read-only review from the toolbar or the material-preview dialog. On an unedited, unlocked `compact-three-bedroom-v1` plan, it also offers a separate optional preview. Nothing changes on load, on review, or on cancellation. Accepting uses the existing revision/undo pipeline and preserves the original revision.

The option is intentionally not a general architectural optimizer. Other programmes, manually edited geometry and locked rooms/openings receive an explanation instead of being replaced. Original text, requirement objects, comment targets, all 17 room IDs/kinds/names/notes, authoring settings, plot and all outdoor features remain unchanged. The template changes interior geometry and openings and moves the family entrance to the side; the comparison explicitly shows smaller secondary bedrooms and dining space. This is a tradeoff for the client to review, not a hidden automatic migration.

## Reproduced baseline and measured candidate
For the exact 2,191-character customer brief on 20x25, the shipped template has a 10.419 m straight hall extent and a 14.522 m² hall allocation (19.288 m² including reception). Its principal bedroom polygon has 13.032 m²; the largest contained rectangle is only 2.412 by 4.245 m, despite the much larger bounding box.

The candidate retains three bedrooms and an approximately 150.74 m² conservative ground envelope. It has a broken-up 5.402 m maximum straight hall extent, 10.946 m² halls, and 14.297 m² including reception. The principal bedroom is a 4.052 by 3.666 m rectangle, about 14.855 m². Its geometric bed-zone check succeeds. The kitchen has a hosted exit on the garden side. Guest reception, guest WC and majlis have a separate interior connection graph from the family spaces; this does not certify visual/acoustic privacy or the outdoor route.

Measured values are not magic acceptance constants: tests also run a budget/orientation matrix, independently check the graph, compare full retained metadata, validate host walls and produce a real IFC and render contract. Small millimetre rounding differences between partitioned polygons are not represented as meaningful area savings.

## Definitions and limitations
The envelope is the existing conservative ground-floor envelope with maximum wall allowance, not licensed construction area. The sum of room polygons is not finished clear floor area. Outside-envelope space includes paving, pool, parking and circulation, not just planting.

The hall extent is the longest axis-aligned cross section through the union of hall polygons, with the model's 2 mm geometric tolerance. Splitting a corridor into differently named hall rooms does not lower the number. It is NOT shortest walking distance, escape distance, clear corridor width or code compliance.

A bedroom check looks for a rectangle inside the actual room polygon that can contain a disclosed illustrative 3x2.8 m bed zone after subtracting a conservative wall allowance. It does not verify doors, wardrobes, turning space, accessibility, fire, structural, MEP, ventilation, daylight, pool safety or acoustic/visual privacy. Passing does not approve the plan for construction. The family approach, dining furniture, kitchen island and bathroom layouts still need professional review.

The alternative gallery no longer enables a card that has no actual model changes or has blocking geometry errors. Optional proposals are shown as alternatives, not silently substituted for saved projects.

## Regression entry points
- `npm test`: existing tests plus `tests/layout-quality.test.mjs`.
- `MASAR_BROWSER=chromium python tests/layout_quality_browser.py` (WebKit also).
- Set `MASAR_ACCEPTANCE_URL` only for the non-account live client journey.
- The new public module is included in the standalone build order and the versioned service-worker shell; the independent cache inventory is updated correspondingly.

No cloud Blender worker, AI provider, paid compute, storage plan or unrelated service is enabled or changed by this feature.
