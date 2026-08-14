# F-11 — Content Security Policy: audit, measured impact, and migration plan

**Status: CSP HARDENING IS NOT COMPLETE.**
The two weakest sources — `script-src 'unsafe-inline'` and `script-src
'unsafe-eval'` — are still present and are still exploitable. They are recorded
below as tracked `KNOWN-WEAKNESS` items with measured evidence, not as passes.
**F-09 (splitting `public/index.html` into `public/app/*.js`) is a hard
prerequisite** for removing `'unsafe-inline'`; no amount of CSP editing can
remove it while the entire application is one inline `<script type="module">`.

Everything numeric in this file was measured in this checkout:

* static measurements — `tools/bundle_report.py` → `tests/performance/bundle_report.json`
* browser measurements — `node tests/remediation/csp_browser_probe.js` →
  `tests/remediation/outputs/csp_probe.json` (real Chromium, real
  `Content-Security-Policy` *response header* served from `127.0.0.1` by
  `tools/csp_static_server.py`)
* the machine-checkable claims — `node tests/lib/run.js tests/remediation/test_csp.js`

> **On the exact figures below.** `public/index.html` is being modified by
> another change in flight (it grew from 1 752 083 to 1 863 853 bytes, and from
> 7 inline script elements to 8, while this audit was being written). Every
> concrete byte count and line number in this document is therefore a
> **snapshot**, labelled as one. The authoritative, always-current numbers live
> in two regenerable artifacts — `tests/performance/bundle_report.json` and
> `tests/remediation/outputs/csp_probe.json` — and the tests assert the
> *structure* of the argument, not the snapshot digits, so an edit to the page
> cannot silently invalidate the audit or silently make it pass.

---

## 1. The policy

### 1.1 Before (as deployed at HEAD 130a32d)

```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none';
img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:;
worker-src 'self' blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;
connect-src 'self' https://acs-engine.onrender.com
```

### 1.2 After (this change — purely additive tightening)

```
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none';
img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:;
worker-src 'self' blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;
connect-src 'self' https://acs-engine.onrender.com;
form-action 'self'; frame-src 'none'; manifest-src 'self'; media-src 'self';
upgrade-insecure-requests
```

Every pre-existing directive is byte-identical. Nothing was removed and nothing
was widened. The five added directives cost nothing because the shipped page
uses none of the capabilities they close:

| Added directive | Why it is free today | Evidence |
|---|---|---|
| `form-action 'self'` | the page contains **0** `<form>` elements | `grep -c '<form' public/index.html` → 0 |
| `frame-src 'none'` | the page contains **0** real `<iframe>` elements (the 4 textual hits are strings inside forbidden-tag lists in the embedded JSON specs) | inspected at lines 15780 / 17240 / 18637 / 19362 |
| `manifest-src 'self'` | no `rel="manifest"` is declared | `grep 'rel="manifest"'` → none |
| `media-src 'self'` | no `<video>` / `<audio>` element exists | `grep '<video\|<audio'` → none |
| `upgrade-insecure-requests` | every runtime reference is same-origin or the single pinned `https://` backend | `tools/check_api_base.py` passes |

`netlify.toml` still parses (`python3 -c "import tomllib; tomllib.load(open('netlify.toml','rb'))"` → `toml ok`) and the deploy verifier's baked-absolute-path hunt (`= "/…`) is not tripped, because the CSP value starts with `default-src`, and the URL-scoped header blocks keep the existing TOML *literal string* convention (`for = '/'`).

---

## 2. Directive-by-directive audit

Column 4 ("what it takes to remove") is the work item. Column 5 is the
**measured** compatibility/behaviour impact, not an estimate.

| Directive | Current value | Why it is required today (established by reading the code) | What it takes to remove | Measured impact of removing it |
|---|---|---|---|---|
| `default-src` | `'self'` | baseline; nothing external is fetched at runtime | — (already minimal) | n/a |
| `base-uri` | `'self'` | no `<base>` element exists; pinned so an injected `<base>` cannot re-root every relative URL | — (already minimal) | n/a |
| `object-src` | `'none'` | no `<object>`/`<embed>`/applet is used | — (already minimal) | n/a |
| `frame-ancestors` | `'none'` | the studio must never be framed (clickjacking over project data); paired with `X-Frame-Options: DENY` | — (already minimal) | n/a |
| `img-src` | `'self' data: blob:` | `data:` — `renderer.domElement.toDataURL('image/png'\|'image/jpeg')` at lines 26198, 27870, 29004, 29178 feeds screenshots and the PDF/report pipeline back into `Image.src`; also `THREE.CanvasTexture(noiseCanvas(...))` (line 1260) for procedural WebGL textures. `blob:` — `URL.createObjectURL(file)` for user-supplied door/facade images (lines 27283, 29167) and for generated download previews (29893). | replace every `toDataURL` round-trip with an OffscreenCanvas/`ImageBitmap` handoff that never becomes a URL, and keep user file previews on `createImageBitmap(file)` instead of object URLs | **Not free.** 6 `createObjectURL` and 4 `toDataURL` call sites. Removing `data:`/`blob:` from `img-src` today breaks screenshot preview, the door-image feature, and procedural textures. Low security value: `img-src` cannot execute script. **Recommendation: keep.** |
| `style-src` | `'self' 'unsafe-inline'` | exactly **one** inline `<style>` block holding the entire application stylesheet (tens of KB), plus several dozen `style="…"` attributes in the hand-written markup and in the generated DOM blocks. Live counts: `tests/performance/bundle_report.json` (`elements.styles`) and `tests/remediation/outputs/csp_probe.json` (`distinct_source_lines_by_directive['style-src-attr']`). | F-09: move the `<style>` block to `public/app/app.css` (a `<link rel=stylesheet>` needs no `'unsafe-inline'`), then eliminate **every** inline `style` attribute (a nonce does **not** cover style attributes — only `'unsafe-hashes'` plus per-value hashes does, which is unmaintainable) | **Measured:** with `'unsafe-inline'` dropped from `style-src`, Chromium raises **1** `style-src-elem` violation (the stylesheet) and **one `style-src-attr` violation per inline style attribute** — 43 and then 50 on two consecutive snapshots of a page that is being edited, i.e. the number tracks the markup, not the policy. The page renders unstyled. |
| `font-src` | `'self' data:` | no webfont file is shipped; `data:` is kept for inlined glyph fallbacks | audit that no `data:` font is actually used, then narrow to `'self'` | Untested today; likely free, but unverified — listed as a follow-up, not claimed. |
| `worker-src` | `'self' blob:` | the local pdf.js worker: `pdfjs.GlobalWorkerOptions.workerSrc = '/vendor/pdfjs@4.0.379/pdf.worker.min.mjs'` (line 29170). pdf.js falls back to constructing the worker through a `blob:` URL when the module worker cannot be instantiated directly. | pin pdf.js to same-origin module-worker instantiation only and prove the blob fallback never fires | `'self'` alone is very likely sufficient on modern browsers, but pdf.js's fallback path is not exercisable here (`public/vendor` is empty) — **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED**. |
| `script-src` | `'self' 'unsafe-inline' 'unsafe-eval' blob:` | see §3 — the core weakness | see §5 | see §3 |
| `connect-src` | `'self' https://acs-engine.onrender.com` | the single understanding-engine origin. It is declared once in `public/index.html` (`CONFIGURED_BASE`, line 20) and corresponds to the Render service `name: acs-engine` in `render.yaml`. `tools/check_api_base.py` enforces the one-origin rule. | — (already exactly pinned; widening it is the regression to guard against) | n/a — `test_csp.js` asserts it pins exactly this origin and nothing else. |
| `form-action` | `'self'` (**new**) | no forms exist | — | free |
| `frame-src` | `'none'` (**new**) | no iframes exist | — | free |
| `manifest-src` | `'self'` (**new**) | no manifest | — | free |
| `media-src` | `'self'` (**new**) | no media elements | — | free |
| `upgrade-insecure-requests` | (**new**) | no `http://` runtime reference exists; this makes a future one fail closed | — | free |

---

## 3. `script-src` — the three exceptions, measured

### 3.1 `'unsafe-inline'` — required because the whole application is inline

`public/index.html` is a single document containing **every** script the
application runs. There is not one external application script: no
`<script src="/app/…">` exists, and `public/app/` does not exist.

Snapshot (page sha256 `41ec1c16…`, 1 863 853 bytes — regenerate with
`python3 tools/bundle_report.py`):

| # | line | type | body bytes | what it is |
|---|---|---|---|---|
| 1 | 17 | classic | 1 556 | early boot / language + error guards |
| 2 | 52 | classic | 5 009 | error panel, diagnostics download (`URL.createObjectURL`) |
| 3 | 1039 | classic | 204 | debug-flag reveal |
| 4 | 1271 | classic | 1 101 | the guarded `es-module-shims` loader (§3.2) |
| 5 | 1291 | `importmap` | 131 | `three` → `/vendor/three@0.160.0/…` (local only) |
| 6 | 1300 | classic | 1 330 | login card + `window.ACS` bootstrap (works even if 3D fails) |
| 7 | 1333 | **module** | **1 759 459** | the entire application |
| 8 | 31989 | classic | 4 575 | late page-level script (added by the in-flight change) |

Script #7 alone is ~94 % of the page. **A nonce or hash cannot help here in any
useful way**: hashing a 1.7 MB inline module would force a full-page cache bust
on every code change, and a nonce on an inline module still leaves the whole
application inside the HTML document, which is what makes any XSS sink
immediately script-executing. The only real fix is F-09.

**Measured, in real Chromium, under the *deployed* policy:**

```
KNOWN-WEAKNESS · CSP-INLINE-EXEC
  a hostile <script> injected into the live page EXECUTED  →  true
```

This is not a hypothetical. `tests/remediation/csp_browser_probe.js` appends
`<script>window.__HOSTILE_INLINE__ = true</script>` to the loaded page and reads
the flag back: it is `true`. Any injection sink in the application is therefore
directly script-executing.

### 3.2 `'unsafe-eval'` and `blob:` — es-module-shims 1.8.2

The shim is loaded by the guarded loader at lines 1024–1040:

```js
var nativeImportMap = typeof HTMLScriptElement !== 'undefined'
  && typeof HTMLScriptElement.supports === 'function'
  && HTMLScriptElement.supports('importmap');
if (nativeImportMap) return;                 // modern path: no shim, no blob:
var s = document.createElement('script');
s.src = '/vendor/es-module-shims@1.8.2/es-module-shims.js';   // local, no CDN
```

Confirmed by reading the code:

* the shim is **local** (`/vendor/…`), never a CDN — so `'unsafe-eval'`/`blob:`
  buy an attacker no external origin;
* on a browser with native import maps the shim is **never fetched**, so no
  `blob:` module is ever created there;
* **the application itself contains zero `eval(` and zero `new Function(` call
  sites.** All 7 textual `eval(` hits (lines 7189, 14116, 15780, 17240, 18637,
  19362, 21140) are entries in *forbidden-token deny-lists* inside the embedded
  JSON specifications, not call sites. So `'unsafe-eval'` is attributable
  **entirely** to the shim.

**Partly refuted / sharpened, two ways:**

1. **The guard is stricter than it needs to be.** `HTMLScriptElement.supports`
   shipped later than import-map support in Chromium: import maps landed in
   Chrome/Edge **89**, but `HTMLScriptElement.supports` only in Chrome **106**.
   So Chrome/Edge **89–105** take the legacy branch and download the shim even
   though they support import maps natively. Fixing the feature test (probe an
   actual `<script type="importmap">` acceptance instead) shrinks the shim's
   real audience to genuinely-legacy browsers — a cheap, F-09-independent
   improvement.
2. **Whether the shim strictly needs `'unsafe-eval'` is NOT VERIFIED here.**
   `public/vendor` is empty in this sandbox and there is no network, so
   `es-module-shims@1.8.2` cannot be read or executed. Its documented CSP
   requirement is `blob:` for rewritten modules; `'unsafe-eval'` may be
   removable independently. **This must be measured on a networked machine
   before `'unsafe-eval'` is dropped** — see step 0 of §5.

**Measured, under the deployed policy:**

```
KNOWN-WEAKNESS · CSP-EVAL-EXEC        hostile eval() from page code EXECUTED  →  true
KNOWN-WEAKNESS · CSP-FUNCTION-CTOR    hostile new Function()        EXECUTED  →  true
```

### 3.3 Browser-compatibility cost of dropping the shim — stated explicitly

Dropping `es-module-shims` is the only way to remove `blob:` (and possibly
`'unsafe-eval'`) from `script-src`. **The application does not degrade on the
affected browsers; it does not run at all** — every bare specifier (`three`,
`three/addons/…`) becomes unresolvable, the module script never executes, and
the user sees the login card and then the "engine did not load" warning at 12 s
(line ~1075) forever.

Browsers that lose the application entirely if the shim is dropped:

| Engine | Import maps supported from | Lost if the shim is dropped |
|---|---|---|
| Safari (macOS **and** iOS/iPadOS — all iOS browsers use WebKit) | **16.4** (March 2023) | **iOS/iPadOS ≤ 16.3, macOS Safari ≤ 16.3.** This is the population the shim exists for. iOS 15.x devices are still in the field, and every iPhone that cannot take iOS 16.4 (iPhone 7 / 6s / SE-1 class) is permanently in this bucket. |
| Firefox | 108 (December 2022) | Firefox ≤ 107, and **Firefox ESR 102** (still deployed in managed/enterprise fleets) |
| Chrome / Edge | 89 (March 2021) | Chrome/Edge ≤ 88 |
| Samsung Internet | 15.0 | ≤ 14.x |
| Opera | 75 | ≤ 74 |

**Recommendation: do NOT drop the shim as part of CSP hardening.** The security
gain (removing a *same-origin* `blob:` source, on a code path that only runs on
browsers that already lack modern mitigations) is small; the cost is a total
outage for a real, identifiable user population. If the product later declares
a minimum-browser baseline of "native import maps", then and only then delete
the loader block from `index.html` **first** and the `blob:` (and, after step 0
of §5 proves it, `'unsafe-eval'`) source **second**.

---

## 4. Measured evidence: current policy vs. hardened trial policy

Both rows are one real Chromium load of the real shipped page, served over
`http://127.0.0.1` with the policy applied as a genuine response header. The
hardened trial policy is the deployed policy with **only** `'unsafe-inline'`
and `'unsafe-eval'` removed — nothing else changed, so the whole delta is
attributable to those two tokens.

| Measurement | CURRENT (deployed) | HARDENED TRIAL |
|---|---|---|
| page loaded | true | true |
| **CSP violations (total)** | **0** | **54**, then **61** on the next snapshot — the count tracks the page, and it is never 0 |
| … `script-src-elem` | 0 | **one per inline script element in the page, plus the injected hostile one** — every application script is blocked, the import map included |
| … `script-src` (eval family) | 0 | **2** — `eval()` and `new Function()` |
| … `style-src-elem` | 0 | **1** — the single inline application stylesheet |
| … `style-src-attr` | 0 | **one per inline `style="…"` attribute** (43 and then 50 across two snapshots of the page as it was edited) |
| console errors | 7 (all `404` for the absent `public/vendor`) | 52 (all `Refused to execute/apply …`) |
| failed requests | 7 (absent vendor files) | 0 — *because the module script never ran, so it never asked for them* |
| **application inline scripts executed** | **true** | **false** — the application does not start at all |
| **hostile inline `<script>` executed** | **true** ← weakness | **false** |
| hostile external same-origin script loaded | true | true (`'self'` is intact in both) |
| **hostile `eval()` executed** | **true** ← weakness | **false** |
| **hostile `new Function()` executed** | **true** ← weakness | **false** |

Read plainly: **the hardened policy is exactly the policy we want, and it
breaks 100 % of the application today.** That is the whole argument for F-09.

### Frame rendering: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED

`public/vendor` is empty in this checkout and there is no network, so Three.js
cannot load and **no frame was rendered**. Nothing above depends on a rendered
frame: CSP decisions are taken by the browser at parse/execute time. Any claim
about rendering under either policy stays NOT VERIFIED here.

---

## 5. Migration plan to a nonce/hash-based CSP

Ordered. Steps 1–3 are **F-09 work**, not CSP work. The CSP change is the last,
smallest step; that is the honest shape of this problem.

**Step 0 — measurable, independent of F-09 (do this first, it is cheap).**
On a networked machine, run `sh tools/vendor.sh`, then re-run
`node tests/remediation/csp_browser_probe.js` with a trial policy that removes
**only** `'unsafe-eval'` (keeping `'unsafe-inline'` and `blob:`), on a browser
forced down the shim path. If the shim runs, drop `'unsafe-eval'` immediately —
it is then unattributed. Also fix the `HTMLScriptElement.supports` feature test
(§3.2) so Chrome 89–105 stops loading the shim. Neither change needs F-09.

**Step 1 — F-09.a: extract the stylesheet.**
Move the single inline `<style>` block (line 152; tens of KB — exact size in
`bundle_report.json`) to `public/app/app.css`, referenced by
`<link rel="stylesheet" href="/app/app.css">`. Then delete every `style="…"`
attribute (§2) by moving it to a class. Only when *both* are done can
`'unsafe-inline'` leave `style-src`. Verify with the probe: `style-src-elem`
must go 1 → 0 and `style-src-attr` must go to 0.

**Step 2 — F-09.b: extract the application module.**
Split the multi-megabyte inline `<script type="module">` into
`public/app/*.js`, loaded as `<script type="module" src="/app/main.js">`. The
generated blocks already have unambiguous begin/end markers (10 JS pairs, 6 CSS
pairs, 6 DOM pairs — enumerated in `tests/performance/bundle_report.json`), so
the split can follow the existing generator boundaries one-for-one, and the
generators keep writing to their own files instead of into the HTML.

**Step 3 — F-09.c: the remaining inline scripts.**
Scripts #1, #2, #3, #6, #8 become `public/app/boot/*.js`. Script #5 (the import map)
**must stay inline** — an import map cannot be external — so it needs a
**nonce**, not extraction. Script #4 (the shim loader) becomes external, or
disappears if the browser baseline changes (§3.3). Delete every inline event-handler attribute — at the time of writing there is
one, `onclick="location.reload()"` on the engine-warning reload button (a nonce
does not cover event-handler attributes).

**Step 4 — issue a per-response nonce.**
Netlify static headers cannot vary per response, so a per-request nonce needs a
Netlify **Edge Function** that injects `nonce-<random>` into both the header and
the import-map tag. Alternative with no edge function: a build-time **hash**
(`'sha256-…'`) of the import map, computed by `tools/netlify-build.sh` and
written into `netlify.toml`. The import map is 131 bytes and changes only when
vendored versions change, so the hash route is the pragmatic one and is
recommended.

**Step 5 — tighten the policy.**
Target:

```
script-src 'self' 'sha256-<importmap hash>';
style-src  'self';
```

i.e. `'unsafe-inline'`, `'unsafe-eval'` and `blob:` all gone from `script-src`
(the last only if §3.3's browser-baseline decision has been taken and written
down). Re-run `csp_browser_probe.js` and require **0 violations** with the
application fully booting — the exact opposite of the row measured in §4 today.

**Step 6 — lock it.**
Extend `tests/remediation/test_csp.js` to *fail* on the presence of
`'unsafe-inline'` once step 5 lands, converting today's tracked weakness into a
regression guard.

---

## 6. Tracked weaknesses (open)

| ID | Weakness | Blocked on | Evidence |
|---|---|---|---|
| `CSP-INLINE-EXEC` | `script-src 'unsafe-inline'`: a hostile inline `<script>` **executes** on the deployed policy | **F-09** (steps 1–3) | measured `true`, `tests/remediation/outputs/csp_probe.json` |
| `CSP-EVAL-EXEC` | `script-src 'unsafe-eval'`: a hostile `eval()` **executes** on the deployed policy | step 0, then the es-module-shims decision (§3.3) | measured `true`, same file |
| `CSP-FUNCTION-CTOR` | `new Function()` **executes** (same root cause) | as above | measured `true`, same file |
| `CSP-STYLE-INLINE` | `style-src 'unsafe-inline'`: 1 inline stylesheet + several dozen inline style attributes | F-09 step 1 | 44 and then 51 style violations measured under the trial policy |
| `CSP-BLOB-SCRIPT` | `script-src blob:` for es-module-shims | a written browser-baseline decision (§3.3) | shim is local-only and guarded; not exercisable here |
| `CSP-SHIM-OVERFETCH` | Chrome/Edge 89–105 load the shim unnecessarily (feature test uses `HTMLScriptElement.supports`, Chrome 106+) | nothing — fixable today | read from `public/index.html` lines 1026–1038 |
| `CSP-WORKER-BLOB` | `worker-src blob:` for the pdf.js fallback | proving the fallback never fires | **NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED** (`public/vendor` empty) |

**F-09: NOT IMPLEMENTED.**
**Full CSP hardening: NOT COMPLETE — and it cannot be completed before F-09.**
