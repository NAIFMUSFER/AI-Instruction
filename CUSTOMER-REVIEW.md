# CUSTOMER-REVIEW — live customer observation

Status: partial live review; authenticated product journey blocked. No repository source, application internals, network payloads, or backend endpoints were read by this stream. No code remedies are proposed.

Observation date: 2026-09-26 UTC. The source was the live product only: https://sprightly-selkie-d906c3.netlify.app/ and the privacy page opened through its visible link. The live deployment's commit was not identified from the public UI, so these observations must not be attributed to the requested base commit.

## Ranked friction observations

Order reflects this reviewer's likelihood of abandoning a purchase evaluation, not measured conversion rates. Each record contains only expectation, observation, and customer cost.

### Highest: no product experience before authentication

- **Expected:** As an engineering-office owner arriving for the first time, I could understand the offered result and start evaluating the requested villa workflow.
- **Happened:** The initial page and subsequent reload showed only a login card: Google, email/password, account creation, password recovery, email confirmation, and privacy. There was no visible building brief field, example result, guest entry, workspace, panel, or export control. Evidence: `await customerTab.goto('https://sprightly-selkie-d906c3.netlify.app'); await customerTab.playwright.domSnapshot();` and `await customerTab.reload(); await customerTab.playwright.domSnapshot();`. Screenshot: `acs-customer-login-20260926.jpg` (evidence outside Git).
- **Cost:** I cannot evaluate the building result without first committing to authentication. This also prevented this review from establishing whether the product satisfies the requested villa task. Authentication being required is an observed product choice, not a claim of broken sign-in.

### Next: confidential-client procurement questions end at an unnamed operator

- **Expected:** Before submitting an office's client drawing, I could identify the receiving AI provider, its applicable retention terms, and someone responsible for answering questions.
- **Happened:** The public privacy page says the deployed AI provider and retention depend on the operator's configuration and contract, then directs the reader to ask the operator. The rendered page did not identify that operator or provide a contact action. Evidence: `await customerTab.playwright.getByRole('link', {name:'الخصوصية وحفظ البيانات'}).click();` followed by `await customerPrivacyTab.playwright.domSnapshot();` on the opened `/privacy` page. This is a review of the disclosure, not independent verification of data processing.
- **Cost:** I cannot settle my client-data-sharing decision from the published information. Establishing provider terms and the accountable operator is an operational/commercial matter; it is not established as a code defect here.

### Next: uploaded-original removal is disclosed as unavailable

- **Expected:** I could understand how to withdraw an original client drawing retained by the project before choosing to store it.
- **Happened:** The public privacy page says originals and selected-page previews may be stored privately, and explicitly says the interface currently provides no deletion control for the original. Evidence: `await customerPrivacyTab.playwright.domSnapshot();`, under the Arabic project-data-storage section and the English corresponding section. The authenticated UI and actual deletion behavior were not available to this review.
- **Cost:** I cannot plan a self-service removal workflow from what the product discloses. No client drawing was uploaded to test this.

## Coverage and limits

| Requested observation | Result and evidence |
|---|---|
| First visit and warm reload | Both displayed the login UI; commands above. These are visible-state observations, not a cold-cache performance benchmark. |
| Throttled 3G, disabled cache, first paint, time to type the building brief, request count and total bytes | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** The supported cloud-browser API advertised no throttling, cache-control, network-capture, or mobile-emulation capability. No FCP, request, or transfer-size figure is inferred from tool elapsed time. The building brief was behind authentication. |
| Phone repetition | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No physical phone or supported phone-emulation control was available to this stream. |
| Arabic villa: «فيلا دورين على أرض ٢٠×٢٥، مجلس ومقلط ومطبخ وأربع غرف نوم ودرج داخلي» | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No authenticated ACS session or visible brief input; prompt was not submitted. |
| Contradictory/impossible building and smaller-than-building plot | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** Authentication blocked generation; no output was produced, so neither correctness nor silent wrongness was established. |
| Workspace, render, BIM exchange, docs, quality, architectural detail; panel wait messaging | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** Panels were not available on the unauthenticated page. |
| IFC4, glTF, DXF, SVG export and opening in an external viewer | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No generated model or export controls; no Revit or equivalent native viewer was available. |
| Empty input, 5000-word input, mixed Arabic/English, words-as-numbers, contradictory dimensions | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** These attacks were not submitted because the product input is behind authentication. A blocked test is not a pass. |
| VR/WebXR | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No headset and no authenticated walkthrough. |
| Public privacy link | Observed opening a separate page with Arabic and English data-use disclosure; `await browser.tabs.list()` identified the new tab, then `await customerPrivacyTab.playwright.domSnapshot()` read the visible page. |
| Public regulatory disclaimer | The privacy page explicitly preserves `NOT_EVALUATED` and says outputs need responsible engineer review. This verifies that displayed disclaimer only, not all generated issue text. |

The user's instruction to proceed without returning for input was respected: no credential request, signup, or login-method selection was initiated. An authenticated session remains the concrete dependency for the unexecuted customer tests. Nothing in this report implies those tests passed, failed, or were repaired.

## Reproduction environment and evidence

Browser control used the documented `control-browser` runtime, via `mcp__node_repl__js`. No standalone automation or hidden application-state inspection was used. The commands in the observations are browser commands after documented runtime setup. `customerTab` is a fresh tab from `await browser.tabs.new()`; `customerPrivacyTab` is the tab opened by the observed privacy link.


Screenshot evidence is retained outside the repository as requested: `/workspace/scratch/acs-customer-login-20260926.jpg` and `/workspace/scratch/acs-customer-privacy-20260926.jpg`. No generated artifacts were committed by this stream.
