# Start a connected project from an existing drawing

The connected workspace previously offered only a textual brief. The first requirements step now offers an existing PNG, JPEG, WebP or PDF (maximum 5 MiB). PDF users explicitly choose one page; the complete original and its selected-page preview are stored privately in the project. Saved inputs remain selectable after refresh, and the original can be downloaded byte for byte.

Uploading does not call a model. After reviewing and confirming the requirements, the user explicitly starts either a reading of the existing layout or a proposed revision according to the brief. The selected preview is sent to the existing isolated vision provider with the chosen call ceiling. There is no automatic follow-up generation or hidden budget increase. Uploaded layouts are not passed through the deterministic overlap relocation helper.

The parent process attaches the source ID, original and preview hashes, selected page, mode and `needs_review` measurement status to the model receipt. Provider output cannot create or change this receipt. Normal geometry validation, project membership, stale-head checks, locks, revision history, concept approval and artifact gates still apply.

## Storage and processing

- `20260914105346_acs_plan_sources.sql` creates a private bucket and project-member RLS policies. Viewers can read; owners/editors can insert. Original objects and metadata have no client update/delete grant or policy.
- Requests use the existing user-scoped Supabase JWT, never a service-role key or public URL. Fixed project/source paths and persisted SHA-256 checks bind reads to the selected input.
- The dedicated authenticated upload route has a 10 MiB JSON body limit for bounded base64 fields. The surrounding command document and all ordinary routes retain their existing limits. File signature, PDF page/decompression limits, image dimensions, and image metadata normalization are checked in the bounded CPU worker.
- A retry reuses the same source ID. Existing objects are accepted only when their bytes match. An interrupted upload can leave private unreferenced objects; automated cleanup and deletion UI are not part of this change.

## Evidence and limits

- Eight synthetic upload/vision/provenance tests pass, along with the existing 17 connected-workspace and seven HTTP command-boundary tests. Deployment content closure passes (711 checks).
- The private-storage migration was applied on 2026-09-14. A transactional probe using only generated synthetic users/projects passed owner insert/read, viewer read-only, outsider denial, and immutable-original checks, then rolled back all fixture rows. The project advisor reported no storage/table warning; its existing leaked-password-protection setting is outside this change.
- The real browser fixture now exercises image and selected PDF-page uploads, no-provider upload, original download, refresh recovery, saved source generation and the existing review/export lifecycle. Generation and storage are controlled fixtures; the browser and HTTP application are real.
- Local Chromium cannot start because the workspace blocks its process-singleton socket. GitHub Actions must pass the browser fixture before release; this is not a successful local browser result.
- The PDF page preview is rendered by the client and its bytes are validated and stored. This does not attest pixel equivalence to the original PDF, dimensional accuracy, architectural compliance or completeness. Only the chosen page is interpreted. DWG/DXF and multi-page merging are not supported here.
- No paid generation was run on the user's account. Actual provider extraction quality is not established by the fixture.

## Separate unresolved live generation failure

Job `d8718b95-1596-4282-908e-ceda0df95d95` on 2026-09-14 finished with `ACS_PROVIDER_BUDGET_EXHAUSTED`. Provider logs show a 43-zone proposal split recursively after output ceilings were reached. This upload change does not fix that text-generation budget failure and does not increase the user's selected limit.
