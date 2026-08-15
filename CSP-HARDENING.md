# F-11 — Content Security Policy: before, after, evidence, compatibility

**Status: CLOSED.**
The deployed policy carries no `'unsafe-inline'`, no `'unsafe-eval'`, no
`'unsafe-hashes'`, no wildcard, no `blob:`/`data:` script source and no CDN
host. All **eight** attack classes named in the F-11 brief were attempted as
real code execution in a real Chromium against the real policy served as a real
response header, and all eight were **BLOCKED**. A normal boot of the shipped
page produces **0** CSP violations.

The close was made possible by F-09: `public/index.html` is now a 44 253-byte
shell with zero executable inline JavaScript, zero `<style>` blocks and zero
`style="…"` attributes; the whole application lives in ES modules under
`public/app/`. The only inline element left in the page is the import map, and
it is pinned by a sha256 hash.

Everything numeric in this file was measured in this checkout:

* browser measurements — `node tests/remediation/csp_browser_probe.js` →
  `tests/remediation/outputs/csp_probe.json` (real Chromium, real
  `Content-Security-Policy` **response header** served from `127.0.0.1` by
  `tools/csp_static_server.py` — never `<meta http-equiv>`, which cannot express
  `frame-ancestors` and would therefore measure a different policy than the one
  deployed)
* the machine-checkable claims — `node tests/lib/run.js tests/remediation/test_csp.js`
* the "before" numbers come from the probe output recorded at commit `c5dcfb2`

Two adjacent defects that this work uncovered but did **not** cause and does
**not** fix are recorded in §6. Neither is a hole in the policy; both are
application bugs that the policy makes visible.

---

## 1. Before

### 1.1 The old policy, verbatim (as deployed at `c5dcfb2`)

```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; worker-src 'self' blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; connect-src 'self' https://acs-engine.onrender.com; form-action 'self'; frame-src 'none'; manifest-src 'self'; media-src 'self'; upgrade-insecure-requests
```

The load-bearing weakness was `script-src 'self' 'unsafe-inline' 'unsafe-eval'
blob:`. `'unsafe-inline'` existed because the entire application was one
1.76 MB inline `<script type="module">` — about 94 % of a 1 863 894-byte page.
`'unsafe-eval'` and `blob:` existed for exactly one reason: `es-module-shims`,
loaded to give import-map support to browsers that lack it natively.

### 1.2 The old measured numbers

Two Chromium loads of the same shipped page: once with the deployed policy
above, once with a **hardened trial** policy that differed only by the removal
of `'unsafe-inline'` and `'unsafe-eval'`.

| Measurement | CURRENT (as deployed) | HARDENED TRIAL |
|---|---|---|
| page loaded | true | true |
| **CSP violations, total** | **0** | **62** |
| … `script-src-elem` | 0 | 9 — every inline application script, the import map included |
| … `script-src` (eval family) | 0 | 2 — `eval()` and `new Function()` |
| … `style-src-elem` | 0 | 1 — the inline application stylesheet |
| … `style-src-attr` | 0 | 50 — one per inline `style="…"` attribute |
| console errors | 7 (all 404 for the absent `public/vendor`) | 60 (all `Refused to execute/apply …`) |
| failed requests | 7 | 0 — the module script never ran, so it never asked |
| **application inline scripts executed** | **true** | **false** — the app did not start at all |
| **hostile inline `<script>`** | **EXECUTED** ← weakness | BLOCKED |
| **hostile `eval()`** | **EXECUTED** ← weakness | BLOCKED |
| **hostile `new Function()`** | **EXECUTED** ← weakness | BLOCKED |

Read plainly: the policy we wanted was already known to work, and it broke
100 % of the application. That was the whole argument for F-09.

---

## 2. After

### 2.1 The new policy, verbatim (`netlify.toml`, header block `for = "/*"`)

```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; frame-src 'none'; form-action 'self'; script-src 'self' 'sha256-kmeUkbmn7TSoFc+bR+iKEW0CLiuQIqi5X7Op3y+XBkA='; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; worker-src 'self'; connect-src 'self' https://acs-engine.onrender.com; media-src 'self'; manifest-src 'self'; upgrade-insecure-requests
```

What changed, directive by directive:

| Directive | Before | After | Why the change is safe |
|---|---|---|---|
| `script-src` | `'self' 'unsafe-inline' 'unsafe-eval' blob:` | `'self' 'sha256-…'` | the page has zero executable inline scripts; the one inline element left (the import map) is pinned by content hash; `es-module-shims` is deleted, which removes the only consumer of `'unsafe-eval'` and `blob:` |
| `style-src` | `'self' 'unsafe-inline'` | `'self'` | zero `<style>` blocks and zero `style="…"` attributes remain in the page; all CSS is `/app/styles/app.css` |
| `font-src` | `'self' data:` | `'self'` | `public/app/styles/app.css` contains zero `@font-face` rules and zero `data:` fonts |
| `worker-src` | `'self' blob:` | `'self'` | the pdf.js worker is loaded from a real same-origin path (`/vendor/pdfjs@4.0.379/pdf.worker.min.mjs`) — see §5 |
| everything else | unchanged | unchanged | already minimal |

The `'sha256-…'` source is the sha256 of the exact text content of the page's
`<script type="importmap">` element. It is not copied by hand: it is written to
`public/app/importmap.sha256`, and `tests/remediation/test_csp.js` **recomputes
it from `public/index.html`** and refuses the policy if the two differ. A single
hash over a single known, tiny, non-executable JSON document is not a hole —
changing one byte of the map invalidates it and the map stops loading.

An import map cannot be an external file with adequate cross-browser support,
which is why it is the one inline element that remains.

### 2.2 The new measured numbers

`tests/remediation/outputs/csp_probe.json`, three consecutive runs, identical
results:

| Attack class | Attempted as | Result |
|---|---|---|
| injected inline `<script>` | `script.textContent = …; head.appendChild(script)` | **BLOCKED** (`script-src-elem`) |
| `eval("…")` | called from a same-origin external script | **BLOCKED** (`script-src`) |
| `new Function("…")()` | called from a same-origin external script | **BLOCKED** (`script-src`) |
| `javascript:` URL | `<a href="javascript:…">` appended and `.click()`ed | **BLOCKED** (`script-src-elem`) |
| external script, unrelated origin | `<script src="http://127.0.0.1:<other-port>/…">` | **BLOCKED** (`script-src-elem`); Chromium reported the request failure reason as **`csp`** |
| inline event handler | `btn.setAttribute('onclick', …); btn.click()` | **BLOCKED** (`script-src-attr`) |
| `data:text/javascript` script | `<script src="data:text/javascript,…">` | **BLOCKED** (`script-src-elem`) |
| `blob:` script | `URL.createObjectURL(new Blob([…],{type:'text/javascript'}))` as `<script src>` | **BLOCKED** (`script-src-elem`) — the boundary is exercised explicitly because `script-src` deliberately does **not** list `blob:` |

| Boot / style measurement | Result |
|---|---|
| CSP violations during a normal boot | **0** |
| `window.ACS_API` present | true |
| `window.ACS` present | true |
| import map accepted by its hash (the bare specifier `three` really resolved through it) | true |
| executable inline `<script>` blocks in the DOM | 0 |
| `<style>` blocks in the DOM | 0 |
| `element.style.<prop> = …` (CSSOM write) | **ALLOWED** — CSSOM is *not* governed by `style-src`; measured, not assumed |
| `setAttribute('style', …)` | **BLOCKED** (`style-src-attr`) |
| total violations recorded across boot + all attacks | 9 — `script-src-elem` 5, `script-src` 2, `script-src-attr` 1, `style-src-attr` 1 |

Every violation is recorded with its `violatedDirective`, `effectiveDirective`,
`blockedURI`, `sourceFile` and `lineNumber` in the JSON — not as a bare count.

---

## 3. Evidence

**Probe:** `tests/remediation/csp_browser_probe.js`
**Output:** `tests/remediation/outputs/csp_probe.json`
**Server:** `tools/csp_static_server.py` (applies the policy as a genuine
response header; serves the attack driver at the virtual path
`/__csp_probe__/hostile.js`, which is never written into `public/`)
**Contract test:** `tests/remediation/test_csp.js`

### 3.1 The methodology trap: `page.evaluate()` bypasses CSP

**`page.evaluate()` injects code through the CDP debugger
(`Runtime.evaluate`), and that path is exempt from Content Security Policy.**
`eval()` or `new Function()` called from inside `page.evaluate()` runs *even
under a policy that forbids them*, and would be recorded as `EXECUTED` — a false
negative that makes a correct, strict policy look broken.

Every attack in this probe is therefore compiled by the page itself: the driver
is served as a same-origin `<script src="/__csp_probe__/hostile.js">` and the
page's ordinary script machinery — the machinery the policy governs — fetches
and compiles it. `page.evaluate()` is used for exactly two things: appending
that one `<script>` element (a plain DOM insertion, itself subject to CSP) and
reading result *data* back out. The warning is repeated in the header of both
`tools/csp_static_server.py` and `tests/remediation/csp_browser_probe.js` so it
cannot be re-introduced by accident.

### 3.2 The cross-origin script really is cross-origin

The "unrelated origin" is a second real HTTP server bound to a **second port on
127.0.0.1**. A different port is a different origin by definition
(scheme + host + port), the server resolves and responds, and it serves the
payload with **no CSP header of its own**. So the block is attributable to the
page's policy and nothing else. Chromium reported the failure reason on the
`requestfailed` event as **`csp`** — observed, not assumed, and not a DNS
failure.

### 3.3 The probe is not vacuous

Run against a deliberately permissive policy
(`script-src * 'unsafe-inline' 'unsafe-eval' data: blob:`) the same probe
reports all eight attack classes as `EXECUTED`, prints a `KNOWN-WEAKNESS` line
for each and exits non-zero. Against the deployed policy it reports eight
`BLOCKED` and exits zero. It fails the build if any attack executes or if a
normal boot produces any CSP violation.

`tests/remediation/test_csp.js` is validated the same way: **30 hostile mutants
of the real policy — each a single hostile edit — are fed through the same
auditor used for the real policy, and all 30 are rejected (30/30).** Three
benign rewrites (source order swapped, directive order rotated, extra
whitespace) still pass, proving the gate checks meaning rather than doing string
comparison.

### 3.4 Exact environment

| | |
|---|---|
| Chromium | **141.0.7390.37** (`/opt/pw-browsers/chromium`) |
| Playwright | 1.62.1 |
| Node | v22 |
| Platform | linux x64 |
| `public/vendor` | **absent** in this checkout, and there is no network |

Because `public/vendor` is empty, the bare specifier `three` could not otherwise
resolve and the ES module graph would never start. The probe therefore generates
a **TEST-ONLY Three.js stub** at runtime into a temporary directory
(`/tmp/acs-csp-probe-vendor-*`) and serves it as an overlay above `public/`.
**Not one byte is written inside `public/`.** The stub is labelled TEST-ONLY in
its own file header and in the `environment` block of the JSON output.

**The stub renders nothing. Rendering behaviour is NOT VERIFIED here.** This
probe measures *policy* — what the browser permits — not rendering. CSP
decisions are taken by the browser at parse/compile time and do not require a
rendered frame, so nothing in §2.2 depends on one.

---

## 4. Compatibility — the `es-module-shims` removal

`es-module-shims` was deleted from the page. It was the sole reason
`script-src` ever carried `'unsafe-eval'` and `blob:`.

### 4.1 What is lost, stated in versions

Import maps are natively supported from:

| Engine | Native import maps from | Lost by dropping the shim |
|---|---|---|
| Chrome / Edge | **89** (March 2021) | Chrome/Edge **≤ 88** |
| Firefox | **108** (December 2022) | Firefox **≤ 107**, including **ESR 102** in managed fleets |
| Safari (macOS) | **16.4** (March 2023) | macOS Safari **≤ 16.3** |
| Safari / WebKit on iOS & iPadOS (every iOS browser is WebKit) | **16.4** | iOS/iPadOS **≤ 16.3** — including every device that cannot take 16.4 (iPhone 7 / 6s / SE-1 class), permanently |

On those versions the application does not degrade — **it does not run at all**.
Every bare specifier (`three`, `three/addons/…`) becomes unresolvable, the
module script never executes, and the user sees the login card followed by the
"engine did not load" warning.

**How large is that population as a share of real users? NOT VERIFIED.**
Market share cannot be measured from this sandbox: there is no network, no
analytics access and no usage data in the repository. Any percentage stated here
would be invented. The loss is stated in **versions**, which is a fact, and not
in **market share**, which is not knowable offline.

### 4.2 What was bought with it

`'unsafe-eval'` is not a per-browser concession — it is a **policy-wide**
property of the response header. It was served to, and borne by, **100 % of
users**, including every modern browser that never fetched the shim, in order to
keep serving browsers that could not run the application securely anyway. It
made the eval family available to any injection sink in the application: under
the old policy `eval()` and `new Function()` were **measured executing**
(§1.2). Removing it removes that primitive for everyone, permanently.

The same trade applies to `blob:` in `script-src`: a `blob:` script source is a
general-purpose XSS primitive for all users, and it existed only for the shim's
module-rewriting path.

### 4.3 The alternative that keeps those browsers *without* `'unsafe-eval'`

There is one, and it is worth recording precisely because it was
**NOT IMPLEMENTED** and **NOT TESTED** here.

The shim exists only to resolve **bare specifiers**. If the vendored Three.js
tree is post-processed at build time so that every bare specifier is rewritten
to a relative path — `import … from 'three'` →
`import … from '/vendor/three@0.160.0/build/three.module.js'`, and likewise for
the `three/addons/` prefix inside `examples/jsm/**` (the addon files import
`three` internally, which is why the whole `jsm` tree must be rewritten, not
just the application) — then **the import map itself becomes unnecessary**.
Without an import map there are no bare specifiers to shim, plain ES modules
work back to Chrome 61 / Firefox 60 / Safari 10.1, and `script-src` could drop
even the one remaining sha256 hash.

**Why it is not implemented or tested in this change:** `public/vendor` does not
exist in this checkout — there is **no vendored tree** to rewrite — and there is
**no network** to fetch one. `tools/netlify-build.sh` populates `public/vendor`
only inside Netlify's build environment. A rewrite pass written here could not
be run against a single real file, so it would be untested code claiming an
untested compatibility improvement. That is worse than an honest gap. It belongs
in the build script, next to `tools/vendor.sh`, and must be validated on a
networked machine.

---

## 5. Remaining exceptions

These three, and nothing else.

| Exception | Why it is there | What would remove it |
|---|---|---|
| **`img-src 'self' data: blob:`** | `data:` — the inline favicon (`href="data:,"`) and canvas snapshots taken with `toDataURL()`. `blob:` — WebGL textures and user-imported images handed to the page through `URL.createObjectURL()` (7 call sites in `public/app/`), plus screenshot export. An image source is not a script source: neither token can execute code. | moving snapshot/import flows to same-origin object URLs served by a worker; low value, real cost |
| **The single `'sha256-…'` in `script-src`** | The import map. An import map **cannot** be an external file with adequate cross-browser support, so it is the one inline element left in the page; it is pinned by content, so any edit invalidates it. It is JSON, not code. | rewriting the bare specifiers at build time so no import map is needed at all — see §4.3 (NOT IMPLEMENTED) |
| **`worker-src 'self'`** | Not an exception so much as a note: pdf.js is loaded from a real same-origin path and sets `GlobalWorkerOptions.workerSrc = '/vendor/pdfjs@4.0.379/pdf.worker.min.mjs'`, so `'self'` is sufficient. pdf.js does, however, have a documented fallback that constructs its worker through a `blob:` URL when the module worker cannot be instantiated directly. That fallback is **NOT VERIFIED** here — `public/vendor` is empty and there is no network. | nothing. But if the fallback is ever observed in production, **the single directive to add is `worker-src 'self' blob:`** — and nothing else. Do not widen `script-src`. |

---

## 6. Adjacent defects found while measuring (not policy holes)

Both were surfaced by this work, neither is caused by the policy, and neither is
fixed here — they live in files outside F-11's scope.

### 6.1 A dead inline event handler in the shipped page — OPEN

`public/index.html` line 33 still carries
`onclick="location.reload()"` on the reload button inside the `#engineWarn`
alert. Under `script-src 'self' 'sha256-…'` an inline event handler **never
runs** — this is attack class 6 in §2.2, measured `BLOCKED`. The policy is
correct; the button is silently dead. It must be rewired to an
`addEventListener` in a module under `public/app/`.
`tests/remediation/test_csp.js` fails on it by name until it is.

### 6.2 The ES module graph does not evaluate to completion — OPEN

Boot produces **0 CSP violations**, but a plain JavaScript error:

```
Failed to read the 'MathUtils' property from 'Module':
Cannot access 'MathUtils' before initialization
```

`public/app/core/viewer.js` lists `import '../render/scene.js'` (source line 10)
**before** `import * as THREE from 'three'` (line 12). ES modules evaluate
dependencies in source order, and `scene.js` → `ui/workspace-ui-wiring.js` calls
`setSun(52,135)` at top level, which reads `THREE.MathUtils`. At that moment the
body of the `three` module has not run — the probe records
`boot.three_module_body_evaluated: false` — so the binding is still in its
temporal dead zone and the graph throws.

This is **not** an artefact of the TEST-ONLY stub and **not** a consequence of
the CSP: real `three.module.js` exports `MathUtils` as a `const` exactly as the
stub does, so a real vendored Three.js fails identically. It is an import-order
defect in the F-09 split. Diagnosis is recorded in
`csp_probe.json` under `boot.module_graph_diagnosis`.

---

## 7. How to re-measure

```
node tests/lib/run.js tests/remediation/test_csp.js     # the contract
node tests/remediation/csp_browser_probe.js             # the real browser
cat tests/remediation/outputs/csp_probe.json            # the evidence
```

The probe exits non-zero if any of the eight attack classes reports `EXECUTED`
or if a normal boot produces any CSP violation. The contract test exits non-zero
if the policy drifts, if the import-map hash stops matching the page, if a CDN
host or a second remote origin appears, if a real `eval(`/`new Function(` call
site appears under `public/app/`, or if this document stops matching the policy
it describes.
