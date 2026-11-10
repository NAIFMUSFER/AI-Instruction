# Provider and Arabic PDF delivery evidence — 2026-11-10

This increment selectively adopts reviewed PR #183 source/test changes on the
released guest baseline `c37b5250dc4ff18ba0606add993b5afe52beebaa`; it does not merge
the historical PR or claim a real provider call. PR #182–#186 reconciliation is
recorded separately by the integration owner. All provider tests here use
synthetic SDKs/fixtures.

## Provider identity and paid attempts

- A missing stream method may choose `create` before a request; failure after
  stream entry never purchases a hidden second call. Exactly one budget unit is
  consumed for the actual attempt. Repair accounting includes malformed replies.
- A timeout or connection failure after admission has uncertain provider outcome;
  it cannot retry or switch provider automatically. This does not prove that an
  upstream provider cancelled an accepted request.
- `acs_provider.py` now resolves the legacy SDK endpoint before capability
  routing and distinguishes API protocol, configured provider, endpoint provider,
  requested model, documented alias mapping and accounting profile. Known safe
  endpoint paths are reported without URL query, fragment, userinfo or key.
- The current official DeepSeek compatibility guide (read 2026-11-10) maps Claude
  Sonnet/Haiku aliases to `deepseek-flash` and Opus aliases to `deepseek-v4-pro`:
  https://api-docs.deepseek.com/guides/anthropic_api/ . These are documented
  mappings, not response-model verification. `provider_call_verified` is false
  in configuration health. Unknown endpoint/model profiles use conservative
  accounting rather than inheriting Anthropic's content-token proxy assumption.
- Warehouse planning now forbids an enclosing room double-counting functional
  zones. Explicit Arabic residential roles normalize through a narrow allowlist;
  role-only resumed work retains completed details. The integration owner's
  workspace service carries the corresponding policy/reuse wiring.

The exact current-main archive fails the newly supplied PR regressions; the
respective PR heads pass them. New identity tests failed before the identity fix.
These failures are reproducible evidence, not a count of independent incidents.
Missing new helper/coverage/mutation-anchor failures are not separate bugs.

## Arabic PDF

Connected approved PDF now renders actual Arabic room names alongside stable
numbered callouts using a bundled, embedded subset font, Arabic shaping, bidi
ordering, ToUnicode mapping and original logical ActualText. The original model,
approval and source-map hashes remain unchanged. Unsupported font characters
produce `PDF_TEXT_UNSUPPORTED` before writing an artifact. Space-boundary scope
remains unchanged; this adds no construction or BIM geometry.

The legacy Python documentation serializer also supports Unicode. Visual QA
found and reproduced an additional existing defect: its white background fill
remained the text color. The Python and browser generators now explicitly restore
black text. An independent parsed-content color regression fails before and
passes after this change.

The legacy browser-only documentation stream generator has no embedded Unicode
font. It now refuses Unicode PDF with an explicit Arabic message directing the
user to approved workspace PDF or local SVG/JSON. It no longer silently replaces
Arabic with question marks. The shared Python/JavaScript parity fixture compares
the common ASCII PDF stream surface while continuing to compare full Unicode
draw operations, geometry and SVG. Independent PDF reader tests cover the new
server Unicode surface.

Runtime dependencies: existing fonttools `4.65.0` promoted to direct dependency,
arabic-reshaper `3.1.0`, python-bidi `0.6.12`. Root regenerated universal hashed
requirements files without changing unrelated versions. Font: unchanged DejaVu
Sans `2.37`, `assets/fonts/DejaVuSans.ttf`; origin/license/checksum are in the
adjacent README and LICENSE-DejaVu.txt. No remote font request is made.

## Validation and limits

`evidence/provider-pdf-checks.json` lists exact fresh commands, exit codes and
summaries. All listed commands exited zero. Relevant results: identity 4,
provider attempts/accounting 11, warehouse policy 6, Arabic roles 14,
capability 92, multi-provider 111, accounting 51, integration 56, rejection 57,
Arabic PDF 4, existing approved PDF 7, legacy documentation 421. Fixture corpus contracts passed 5 tests. Shared PDF/docs
parity passed 72 checks using the pinned `.venv` interpreter.

`evidence/arabic-pdf-red.log` records the old missing embedded font; the separate
visibility red log records white-on-white text. `provider-identity-red.log`
records missing endpoint identity and wrong capability routing. These red logs
contain synthetic tests only.

Actual generated synthetic artifacts and final visually inspected PNGs are under
`evidence/approved-arabic*` (two canonical levels) and `evidence/legacy-arabic*`.
Pypdf independently verifies embedded font data, readable Arabic words, page
count, unchanged model hash and valid receipts; Poppler verifies extraction and
renders reviewed pages. Poppler emits visual Arabic in bidi embeddings; the test
applies the Unicode bidi algorithm to that output, while ActualText retains the
original exact mixed label. These fixtures prove text rendering, not live AI
building quality. Deployment verification belongs to the integration owner.
