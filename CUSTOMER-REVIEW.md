# CUSTOMER-REVIEW — live customer observation

Status: partial live review with dated unauthenticated and authenticated observations. The initial authentication block below was subsequently cleared when the user logged in; it is not the current audit blocker. No repository source, application internals, network payloads, or backend endpoints were read by this stream. No code remedies are proposed.

Observation date: 2026-09-26 UTC. The source was the live product only: https://sprightly-selkie-d906c3.netlify.app/ and the privacy page opened through its visible link. The live deployment's commit was not identified from the public UI, so these observations must not be attributed to the requested base commit.

## Historical observations — 26 September 2026 UTC

The following findings and coverage describe only the initial unauthenticated visit. The authenticated appendix below supersedes those test-access limitations where a later result is recorded.

### Ranked friction observations

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

## Historical coverage and limits — initial unauthenticated visit

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

The user's instruction to proceed without returning for input was respected: no credential request, signup, or login-method selection was initiated. At that time, an authenticated session was the concrete dependency for the unexecuted customer tests. The user subsequently logged in; later outcomes are recorded below. The historical block does not imply those tests passed, failed, or were repaired.

## Reproduction environment and evidence

Browser control used the documented `control-browser` runtime, via `mcp__node_repl__js`. No standalone automation or hidden application-state inspection was used. The commands in the observations are browser commands after documented runtime setup. `customerTab` is a fresh tab from `await browser.tabs.new()`; `customerPrivacyTab` is the tab opened by the observed privacy link.


Screenshot evidence is retained outside the repository as requested: `/workspace/scratch/acs-customer-login-20260926.jpg` and `/workspace/scratch/acs-customer-privacy-20260926.jpg`. No generated artifacts were committed by this stream.


## Authenticated appendix — 27 September 2026, Asia/Riyadh

Provenance: this appendix uses only the coordinator's supplied live-UI observations after the user logged in. The customer stream did not read source or reproduce these authenticated interactions independently. UI validation labels are reported as displayed; they are not an independent engineering certification. No authenticated observation is assigned to the requested base commit without evidence of the live deployment revision.

The coordinator supplied live observations for five generation cases: the villa, warehouse, impossible brief, single-storey apartments, and multistorey apartments. Two cases saved revisions with disclosed fallback and three were explicitly rejected. These are attempted customer journeys, not five successfully generated models; the villa recovery belongs to its original journey. This case accounting comes from the fill → read → confirm → generate → DOM-observation sequences below. Timing, conversion, provider cost, and unobserved measurements are not inferred.

The supplied browser commands were `await acsTab.playwright.getByRole('textbox', {name:'صف المشروع والاستخدامات والعلاقات المطلوبة', exact:true}).fill(prompt)`, followed by `await acsTab.playwright.getByRole('button', {name:'قراءة المتطلبات من الوصف', exact:true}).click()`. Action outcomes and the input-derived dimensions/counts below were read with `await acsTab.playwright.domSnapshot()`. Generation used the observed `توليد البديل A` or `اختيار صالة أوسع والتوليد` button as appropriate; the handoff did not supply every manual confirmation selector. Export commands were `await acsTab.playwright.getByRole('button', {name:format, exact:true}).click()` with the observed labels `IFC4`, `SVG`, `DXF`, and `تنزيل 3D`. Download-event waits timed out, but the coordinator subsequently observed actual downloaded files on disk; the wait timeout is not counted as a failed download. Export screenshot evidence outside Git: `/workspace/scratch/acs-live-export-result-20260927.jpg`.

### Ranked authenticated friction observations

Order reflects likely interruption of this reviewer's purchase evaluation, not a measured abandonment rate. Each record contains only expectation, observation, and customer cost.

### Highest: ordinary villa and warehouse requests stopped without a revision

- **Expected:** After confirming the site and floor requirements, I could obtain a reviewable draft for an ordinary villa or warehouse, or a useful completed result after taking the advertised recovery action.
- **Happened:** The coordinator submitted the requested villa brief «فيلا دورين على أرض ٢٠×٢٥، مجلس ومقلط ومطبخ وأربع غرف نوم ودرج داخلي», manually entered the site dimensions and confirmed the floors, then generated alternative A. The UI explicitly reported «لم يكتمل توزيع الغرف…» and saved no revision; using the advertised resume action returned the same outcome. In the warehouse case, the site was entered as 40×60 متر with storage, receiving, shipping, office, and toilet requirements; after manually confirming a single floor and generating A, the UI explicitly reported that total generated area exceeded the site and saved no revision. These were explained failures, not silently accepted wrong buildings. Evidence: coordinator's supplied villa submit → confirm → generate A → resume sequence and warehouse submit → confirm → generate A sequence.
- **Cost:** I completed the brief and confirmation work but had no villa or warehouse draft to review, export, or use to judge the service's quality. The visible recovery action did not unblock the villa case.

### Next: an impossible brief was rejected without identifying the impossible requirement

- **Expected:** If I gave contradictory site dimensions and rooms that could not fit, the product would identify the conflicting requirement so I could correct the brief.
- **Happened:** The coordinator submitted «أرض ٥×٥ متر، أريد مبنى دور واحد بأبعاد ٢٠×٢٠ متر داخل حدود الأرض دون بروز. عشر غرف نوم مساحة كل غرفة ٢٠ متر مربع ومجلس ومطبخ ودرج. عرض الأرض ٥ متر وعرضها ٢٠ متر في الوقت نفسه.» Requirement reading extracted the small site dimensions without explicitly identifying the contradiction; after manual floor confirmation, generation rejected the layout with the same generic layout-failure outcome as the villa, and produced no files. Evidence: the supplied fill → read requirements → manual confirmation → generate sequence, with `await acsTab.playwright.domSnapshot()` after the actions. This was a visible rejection, not a silently accepted wrong model.
- **Cost:** I know that generation failed, but the response does not tell me which conflicting requirement to resolve before spending time trying again.

### Next: the brief confirmation lost ordinary Arabic requirements

- **Expected:** Site dimensions and bedroom/floor requirements stated naturally in Arabic would survive into confirmation, so I would check them rather than reconstruct them.
- **Happened:** For the exact villa prompt above, the coordinator observed extraction of the two floors but no site dimensions from unitless «٢٠×٢٥» and no bedroom count from «أربع غرف نوم». The missing values required manual entry. The warehouse brief's explicit metre dimensions were extracted as 40 and 60, while «دور واحد» did not populate the floor count and needed manual correction. Evidence: coordinator's supplied extraction-state observations before manual confirmation for each named brief. The counts and dimensions here identify those inputs and displayed fields; they are not accuracy statistics.
- **Cost:** I must compare every extracted requirement against my original brief and re-enter missed details. I cannot safely assume the confirmation form preserved what I wrote.

### Next: successful downloads did not establish the engineering handoff I expected

- **Expected:** I could establish whether the exported building would carry usable building elements into my downstream engineering workflow.
- **Happened:** The successful apartment revision allowed planning-only approval and actual SVG, DXF, glTF, and IFC downloads. The coordinator reported that the downloaded files were present. The IFC interface clearly described its scope as spaces only, and the CAD interface described boundaries only. The UI also kept regulatory and structural matters unverified. No Revit import or verification of walls, doors, windows, scale, or storey elevations in a native authoring tool was supplied. Evidence: coordinator's apartment revision → planning-only approval → export observations; external import remains **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.
- **Cost:** I have planning files, but cannot treat their availability as proof of an engineered, construction-ready handoff. The disclosed output scope and the remaining professional review are material to whether this product fits my office's intended purchase.

### Next: a successful planning revision still could not be explored in 3D in this browser

- **Expected:** Once the apartment revision existed, I could inspect it through the advertised three-dimensional view.
- **Happened:** Clicking the 3D control displayed «العرض ثلاثي الأبعاد غير متاح في هذا المتصفح. يمكنك متابعة المخطط ثنائي الأبعاد والحفظ والتصدير.» The limitation was explained, and planning/export remained available. Evidence: coordinator's click and resulting live-UI message. The cloud browser's GPU limitation is unresolved; this observation does not establish a product rendering defect or failure on the owner's machine.
- **Cost:** I could not judge the walkable experience in this session. Its practical availability on the intended customer device remains **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**.

### Next: an alternative's promise conflicted with the confirmed bedroom count

- **Expected:** Alternative descriptions would explain meaningful differences while honoring the requirements I had fixed.
- **Happened:** In the apartment case, alternative B promised more bedrooms even though the displayed alternative cards all retained the fixed bedroom count. Evidence: coordinator's comparison of the visible alternative descriptions after confirming the apartment requirements. No increase in the generated bedroom count is claimed from this wording observation.
- **Cost:** I cannot tell whether choosing that alternative changes my agreed brief or merely changes the sales description, making the choice less useful.

### Next: room-dimension labels were difficult to review quickly

- **Expected:** Room dimensions would be displayed in a form suitable for a quick architectural review.
- **Happened:** The apartment review displayed raw-looking lengths including a kitchen at `4.032×15.241379310344822 m` and a bathroom at `4.032×6.275862068965523 m`. Evidence: coordinator's supplied room-dimension labels from the visible apartment review. These are reported labels, not independently measured physical geometry; no regulatory judgement is inferred.
- **Cost:** The labels require interpretation before I can discuss the plan with a client, and the excess decimal places obscure the practical room proportions.

### Authenticated coverage and limits

| Case or requested observation | Result from the supplied live-UI observation |
|---|---|
| Exact Arabic villa brief | Submitted. Some requirements needed manual correction. Generation A and the advertised recovery failed explicitly without a saved revision. |
| Warehouse brief | Explicit metre dimensions were extracted; the floor count needed manual entry. Generation failed explicitly for total generated area exceeding the site; no saved revision. |
| Apartment brief | Submitted: «مبنى سكني من دور واحد على أرض ٢٤×٣٠ متر، شقتان مستقلتان. كل شقة غرفتا نوم وصالة ومطبخ وحمام ومجلس، ومدخل مستقل.» Requirements were manually confirmed as one floor, two flats, two bedrooms, one bathroom, and independent majlis. Alternative A produced V1 with a disclosed fallback after provider failure. |
| Apartment validation display | The UI showed the scoped geometry/topology checks as passing and kept regulatory/structural evaluation unverified. This reports the UI outcome only; it does not substitute for the engineer stream's independent output audit. |
| Multistorey apartment brief | Submitted: «عمارة سكنية ٣ أدوار على أرض ٣٠×٣٠ متر. شقتان في كل دور، لكل شقة غرفتا نوم وصالة ومطبخ وحمام ومجلس. درج داخلي ومصعد ومحاذاة النواة بين الأدوار، المدخل من الشمال.» The coordinator manually confirmed the site, floors, flats per floor, bedrooms, bathroom, majlis, and north entrance. Alternative C produced V1 with a disclosed fallback. `await acsTab.playwright.domSnapshot()` showed selectable floors and stair/lift labels of `4×4 m` and `3×4 m` on the ground and first floors. This is not proof of a continuous physical walkthrough or independent core-alignment verification. |
| Multistorey validation display | The UI showed the scoped checks, including interlevel checks, passing while leaving safety/regulatory evaluation unverified. The engineer stream's independent review remained separate. |
| Empty input | Continue displayed «اكتب وصف المشروع أولًا.» This tested the visible empty-brief response. |
| SVG, DXF, glTF, IFC download | Planning-only approval allowed downloads, and the coordinator reported actual files present. Content correctness and application interoperability are separate, unverified questions here. |
| IFC import in Revit; actual IFC entities, scale, elevations | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** Download success and the spaces-only UI disclosure do not verify these properties. |
| 3D viewer | Attempted on the successful apartment revision; a clear unsupported-browser message appeared. The cloud GPU limitation is unresolved. |
| Every requested panel and panel opening delays | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** The supplied observations do not establish a complete workspace/render/BIM/docs/quality/architectural-detail panel inventory or timing measurements. |
| Deliberately contradictory brief and requested building larger than plot | Submitted the impossible small-site brief quoted above. Extraction did not explicitly flag the conflicting dimensions. Generation rejected the layout generically and produced no files; no silently wrong accepted result was observed. |
| Mixed Arabic/English input | Submitted to requirement reading only: `فيلا 20×25 متر، 2 floors، 4 bedrooms ومجلس ومقلط ومطبخ.` The returned candidates included two floors and four bedrooms, without a site-dimension candidate. The unlabelled villa footprint/site ambiguity is preserved; this is not counted as a new defect. No model was generated from this case. |
| 5000-word input | Client-side requirement reading only. The coordinator constructed `text = ['أرض','20×25','متر،','دورين،','4','غرف','نوم',...Array(4993).fill('مراجعة')].join(' ')` and measured `text.split(/\s+/).length` as 5000 and `text.length` as 34982. After filling the brief and invoking requirement reading, `await acsTab.playwright.getByRole('article').allTextContents()` showed bedroom, floor, width, and depth candidates of 4, 2, 20, and 25; `await acsTab.playwright.getByRole('alert').allTextContents()` returned no alerts. This verifies that parsing observation only: long-input generation, provider handling, latency, and adversarial resilience remain **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. |
| Numbers written as words | Partial observation only: the villa bedroom phrase and warehouse floor phrase were missed as described. A complete number-vocabulary attack sweep was not supplied. |
| Throttled 3G, cold cache, first paint, time to type, request count/bytes, phone repetition | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No supported measurements or physical phone run were supplied. |
| Headset/WebXR walkthrough | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.** No headset run was supplied. |

The earlier public privacy/retention observations remain dated disclosure findings. Authentication cleared the access blocker; it did not independently settle provider contract terms, original-drawing deletion, export interoperability, or engineering defensibility.
