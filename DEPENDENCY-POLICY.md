# Dependency Policy — how versions are decided, pinned and changed

**Scope:** every dependency this repository installs — the Python backend
(`requirements.in` → `requirements.lock` → `requirements.txt`), the Node test
tooling (`package.json` → `package-lock.json`), and the three frontend libraries
vendored at Netlify build time (`three`, `es-module-shims`, `pdfjs-dist`).

**Enforced by:** `tests/remediation/test_dependency_lock.py` (contract) and
`tools/dependency_audit.py` (audit command). Both run offline and both fail
non-zero on drift. Neither can check a hash or a CVE — see §7.

---

## 0. The state this policy starts from (read this first)

`requirements.lock` was generated **offline**, in a sandbox where `pip install`,
`pip download` and `npm install` all return HTTP 403. Three consequences, none
of them hidden:

| Fact | Consequence |
| --- | --- |
| No artefact could be fetched | **No hashes exist in `requirements.lock`.** None were invented. Pinning without hashes gives version reproducibility, not artefact integrity. |
| No index could be queried | The Python pins are **FLOOR-DERIVED**: each is the exact lower bound the repository already declared (`fastapi>=0.110`, `uvicorn[standard]>=0.27`, `anthropic>=0.40`, `pypdf>=4.0`, `python-multipart>=0.0.9`). That is the only version evidence anywhere in this repository. |
| No metadata could be read | The **transitive closure is unresolved**. Every transitive line in `requirements.lock` is commented out and marked `# UNRESOLVED-OFFLINE`; pip never reads it. Both the versions *and* the membership of that list are unverified. |

**What the live deployment is actually running is unknown and unknowable from
here.** Before this change the ranges were open, so every `docker build` on
Render resolved to whatever was newest that day and recorded nothing. Pinning
to the declared floors makes builds reproducible for the first time; it does
**not** reproduce the current production image, and it may well pin *older*
libraries than production has been running. The first job on a networked
machine is §2.

---

## 1. Adding, removing or changing a Python dependency

1. Edit **`requirements.in`** — and only `requirements.in`. One line per direct
   dependency, no version specifier, with a comment saying which module needs
   it. Never add a transitive dependency here: if you find yourself typing
   `starlette`, what you actually need is `fastapi`.
2. Regenerate the lock (§2). This requires a network. There is no offline path
   that produces a truthful lock.
3. Mirror the resolved direct pins into **`requirements.txt`**.
   *Why the duplication:* `Dockerfile` line 4 is `COPY requirements.txt .` — the
   image copies that file **alone**, so `-r requirements.lock` inside it would
   reference a file that does not exist in the build context and `pip install`
   would fail. `requirements.txt` must therefore stay self-contained.
   The duplication cannot drift silently: `tests/remediation/test_dependency_lock.py`
   asserts the two files agree name-for-name, version-for-version and
   extra-for-extra.
4. Run both gates:

   ```sh
   python3 tests/remediation/test_dependency_lock.py
   python3 tools/dependency_audit.py
   ```

5. If the new dependency is imported by the deployed backend, add it to the
   `COPY` list in `Dockerfile` only if it is a *repository module*; installed
   packages need nothing there. `tests/deploy/verify_deploy.sh` recomputes the
   import closure and will fail if a module the server imports is not copied.

## 2. Regenerating the lock **with hashes** on a networked machine

```sh
python3 -m pip install pip-tools

# resolve the full closure and record a hash per artefact
pip-compile --generate-hashes --output-file requirements.lock requirements.in

# mirror the resolved direct pins into the file Docker installs
$EDITOR requirements.txt          # keep only == pins, no -r, no ranges

# prove nothing drifted
python3 tests/remediation/test_dependency_lock.py
python3 tools/dependency_audit.py

# prove the pins actually install and the server still boots
python3 -m venv /tmp/acsvenv && /tmp/acsvenv/bin/pip install -r requirements.txt
/tmp/acsvenv/bin/python tests/phase9_2/test_backend_contract.py   # section د executes
docker build -t acs-engine .
```

After regeneration, delete the FLOOR-DERIVED / `UNRESOLVED-OFFLINE` header
blocks from `requirements.lock` — they describe the offline state and become a
lie the moment a real resolution replaces it.

Once hashes exist, harden the install line by hand-editing `Dockerfile` in a
separate, reviewed change:

```dockerfile
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
```

`--require-hashes` is what turns the lock from a convention into a guarantee.
It is deliberately **not** enabled today, because the current lock has no
hashes and enabling it would break the deploy.

## 3. The upgrade rule

> **Test the current exact versions first. Upgrade only packages with a proven
> vulnerability, and only with compatibility proof.**

Concretely:

1. **Never** bulk-upgrade ("`pip-compile --upgrade`") because a run is red.
   Reproduce the failure against the pinned versions first; a failure that only
   appears after an upgrade is an upgrade bug, and one that appears on the pins
   is our bug.
2. A version moves for exactly one of three reasons, and the commit message
   says which:
   - **security** — a CVE affects the pinned version. Cite the advisory ID.
   - **capability** — a feature the code now needs. Cite the calling code.
   - **compatibility** — a floor forced by another dependency. Cite the resolver
     output.
3. **Compatibility proof** for any Python upgrade is the full chain, not a smoke
   test:

   ```sh
   sh tests/phase9_2/run_all.sh            # every phase suite, Python + Node
   python3 tests/security/test_security.py
   sh tests/deploy/verify_deploy.sh
   python3 tests/phase9_2/test_backend_contract.py   # needs FastAPI installed
   docker build -t acs-engine .
   ```

4. Upgrade **one package per commit**. A lock diff that moves twelve transitive
   versions at once cannot be bisected when production breaks.
5. Known compatibility constraints in the current code, to check before moving
   the `anthropic` pin: `acs_understand.call_llm` calls
   `client.messages.stream(...)` and falls back to `client.messages.create(...)`
   on `AttributeError`/`TypeError`, and passes `thinking={"type": "disabled"}`
   on its first attempt only. Older SDKs reject `thinking` client-side (no API
   call is spent) and the second attempt succeeds; newer SDKs use it. Both ends
   of that range work — but only the pinned end is tested.

## 4. Node / Playwright

`package-lock.json` is committed with `lockfileVersion: 3` and an sha512
`integrity` field for every package. `playwright` and `playwright-core` must
always be the **same** exact version (1.62.1 today); a mismatch means one of
them was installed outside the lock.

- Install in CI and locally with **`npm ci`**, never `npm install` — `ci`
  installs the lock exactly and fails if `package.json` and the lock disagree.
- `node_modules/` is **committed** in this repository (playwright only), so
  browser tests can run in a sandbox with no registry. That is a deliberate
  contract, recorded in `.gitignore`. If it is ever removed from tracking,
  every CI job that runs a browser test must gain an `npm ci` step first.
- Browser binaries are **not** committed: `npx playwright install --with-deps
  chromium` needs a network and runs only in the `chromium-browser` CI job.

## 5. The frontend vendored versions are pinned in more than one place

`three`, `es-module-shims` and `pdfjs-dist` are not installed by npm. They are
downloaded by `tools/netlify-build.sh` during the Netlify build (`npm pack`) into
`public/vendor/`, which is git-ignored. The version therefore appears in
several files at once, and every one of them must agree:

| Place | What it holds | Effect if it drifts |
| --- | --- | --- |
| `tools/netlify-build.sh` — `THREE=` / `SHIMS=` / `PDFJS=` | the version actually fetched | the authority |
| `tools/netlify-build.sh` — header comment | the documented version | a reader upgrades against a stale note |
| `tools/check_index_guard.py` — `IMPORTMAP_THREE` / `IMPORTMAP_ADDONS` | the version the guard demands | the build fails **after** vendoring |
| `public/index.html` — importmap, shim `src`, pdf.js dynamic `import()` | the version the browser requests | a 404 at runtime — a blank viewport in production |
| `netlify.toml` — build comment | documentation | stale note |
| `tests/deploy/verify_page_boot.js`, `tests/phase9_1/capture_reference.js`, `tests/phase9_2/capture_reference_92.js` | absolute `vendor/three@…` paths | the boot and reference captures silently stop finding Three.js |

**To bump one of them:** change every row in that table in a single commit, then
run `python3 tools/dependency_audit.py` (which compares all of them) and
`python3 tests/remediation/test_dependency_lock.py` (which fails if any place
disagrees, and separately if the version stops matching what the build script
vendors). Also re-check the pinned `REVISION` assertion in
`tools/netlify-build.sh` — for `three` it checks the revision integer (`160`),
not the full `0.160.0`.

`public/index.html` is generated in part by the `tools/build_*_browser.py`
injectors; the importmap is in the hand-written region, but always re-run
`python3 tools/check_index_guard.py public/index.html` after editing it.

## 6. Who runs what, and when

| Gate | Command | Runs |
| --- | --- | --- |
| Lock contract | `python3 tests/remediation/test_dependency_lock.py` | every PR (`dependency-audit` job) |
| Offline audit | `python3 tools/dependency_audit.py` | every PR (`dependency-audit` job) |
| Deploy closure | `sh tests/deploy/verify_deploy.sh` | every PR (`deploy-verification` job) |
| CVE scan | `pip-audit -r requirements.txt`, `npm audit --package-lock-only` | **manual, networked machine** — see §7 |
| Live production check | `.github/workflows/production-verify.yml` | `workflow_dispatch` / `schedule` only, never on a PR |

## 7. What no gate in this repository verifies

Printed verbatim by `tools/dependency_audit.py` as
`NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED`, never as a pass:

- **CVE / advisory status of any pin.** Needs a live advisory database.
  `python-multipart==0.0.9` and the unresolved `starlette` floor beneath
  `fastapi==0.110` are old enough that this review is **mandatory before the
  next production deploy**.
- **Artefact hashes.** `requirements.lock` has none, so nothing proves the wheel
  installed on Render is the wheel the author intended.
- **Whether a pinned version exists on PyPI at all.** The floors were read from
  this repository, not from the index.
- **The transitive closure.** 21 names are listed as `UNRESOLVED-OFFLINE`
  TODOs, not as facts.
- **npm integrity hashes are read, not recomputed.** Proving them needs the
  tarballs (`npm ci`).
