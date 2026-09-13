# Connected requirements and source evidence

This change extends the authenticated ACS requirements form. It does not close
the complete Design Pipeline v2 acceptance checklist.

## Behavior

- The owner can explicitly read quantities from the original Arabic/English
  description, inspect each quoted source, and use individual values in the form.
  Reading and selecting values makes no HTTP request or provider call.
- Supported explicit forms include site width/depth with meter, centimeter or
  millimeter units; numeric floor counts; bedroom, office and kitchen totals;
  dock counts; and explicitly minimum rack-group counts. Arabic-Indic and Persian
  digits retain their original quoted text. An unlabelled site dimension pair is
  labelled as a proposed width/depth interpretation, requiring confirmation.
- Conditional, negative, approximate, range, per-floor and other scoped counts
  are not silently promoted to global requirements. Clarification appears beside
  the form. Unsupported prose remains in full in the description, with a visible
  reminder to review it; this is bounded quantity reading, not a complete Arabic
  semantic parser or regulatory requirements extraction.
- Missing dimensions stay unspecified. Disagreement between recognized text
  quantities and form entries blocks generation until corrected. Duplicate
  selectors and fractional counts are rejected. Explicit zero remains available
  for applicable counts; absence is never converted to zero.
- Every submitted requirement carries exact source evidence and a source span.
  Manually entered answers get separate labelled lines in the canonical brief.
  Span offsets use Unicode code points to match the existing Python consumer,
  including text containing emoji. Existing server provenance validation remains
  authoritative before provider execution and persists through cloud revisions.
- Changing the description or a field, adopting a proposed value, or reopening a
  draft clears confirmation. Provider submission still requires the existing
  explicit confirmation, selected option and bounded budget.

## Verification

Local checks cover the shipped pure producer, real Python admission/store/review,
source-span rejection before a provider is called, and the existing module graph
and single-entry guard. The Unicode integration test invokes the actual shipped
JavaScript producer and reloads the resulting revision from the actual temporary
SQLite store, without any production identity or provider.

The required Async delivery workflow additionally runs the full shipped page at
393 and 1280 pixels, plus 393 without WebGL: read/adopt values, reject a conflicting
width, clear confirmation after changes/reload, preserve the unsent draft, generate
once, persist quoted requirements, lock, approve, export, show exact approved 3D
where available, create a chat revision, compare and log out. These controlled
fixtures do not establish that the owner completed a live Supabase recovery or
accepted a real residential/warehouse design.

The local runtime has no Chromium binary. Browser/CSP and full documentation
measurement gates must pass in CI on the final branch head before merging.
Record final CI, preview and production deployment identities in the PR.

Full architectural walls/openings/shared-wall CAD, professional CAD/IFC tool
acceptance, office Design DNA, full semantic brief extraction and real owner
residential/warehouse acceptance remain open. No compliance or construction-ready
claim is introduced.
