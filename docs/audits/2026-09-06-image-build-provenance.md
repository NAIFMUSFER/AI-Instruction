# Image build provenance — 2026-09-06

## Executive summary / current state

The user-supplied archive identifies `ACS_BUILT_AT=2026-08-15T04:59:00+03:00`
and the user reports that `BUILD_TIMESTAMP` is absent. At 03:26:31 UTC, the live
backend's `/health`, `/ready` and `/version` all returned HTTP 200. `/version`
reported commit `0ae73fdc8e953e769402bdced0ce0487a483e901` and the old timestamp.
The response's `provenance_verified` flag validates formatting, not authenticity.

Base: `0ae73fdc8e953e769402bdced0ce0487a483e901`. The initial working tree was
clean. The existing Dockerfile copied the reader but neither generated nor
copied its build artifact. Runtime environment metadata took priority. Deleting
the old timestamp alone would therefore replace it with `unknown`.

## Gap analysis and target architecture

Docker now stamps `build_info.json` while building and explicitly selects
`ACS_BUILD_INFO_SOURCE=file`. All four identity fields come from the same
artifact. Old runtime timestamps cannot replace its date. Missing, corrupt or
wrong-schema artifacts and unrecognized source modes fail closed; they do not
invent startup dates or borrow another source's identity.

The default outside Docker remains the previous `environment` mode. The public
response has the same eight fields. This is an explicit Docker migration, not a
silent global change of precedence.

Only public revision/branch build arguments are declared. Render supplies its
documented `RENDER_GIT_COMMIT`/`RENDER_GIT_BRANCH`; other Docker builders must pass
`ACS_GIT_SHA`. The strict stamper rejects missing/invalid SHAs or timestamps
before writing. A revision change invalidates the stamp layer. A cached layer
for the same revision truthfully retains its original date.

## Files changed

- `acs_build_info.py`: explicit file mode, schema check, typed file values and
  unchanged compatibility mode.
- `tools/write_build_info.py`: opt-in `--require-provenance` validation.
- `Dockerfile`: build-time stamping, public build arguments and file mode.
- `.dockerignore`: exclude local stamps, Git data, env files, dependencies and logs.
- `.github/workflows/ci.yml`: include the new suite; pass the checkout identity;
  compare the real container's artifact, `/version` and `/health` with the build
  interval while deliberately injecting stale runtime timestamps.
- `tests/remediation/test_image_build_metadata.py`: real writer/reader subprocess
  tests in a temporary directory without a Git checkout.
- `tests/remediation/test_build_metadata.py`: isolate the new source selector in
  test environments while retaining all prior assertions.
- `README.md`, `.gitignore`: document precedence, migration and build commands.
- This audit record.

## Architectural and security changes

The image owns its recorded identity. Metadata generation runs during build,
not startup or request handling. No dependency pin, canonical geometry, frontend
renderer, CSP, CORS, rate-limit invariant or secret setting is changed. No API
keys are passed as Docker arguments. `provenance_verified` remains metadata
validation; this is not a cryptographic image attestation.

## Tests executed and evidence

The targeted commands executed from the repository root were:

```bash
python3 tests/remediation/test_build_metadata.py
python3 tests/remediation/test_image_build_metadata.py
python3 tests/remediation/test_container_topology.py
/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/security/test_security.py
/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/remediation/test_asgi_client_contract.py
uv pip check --python /workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python
git diff --check
```

| Target | Passed | Failed |
| --- | ---: | ---: |
| Existing build metadata contract | 99 | 0 |
| Image writer/reader subprocess contract | 41 | 0 |
| Container topology contract | 26 | 0 |
| Backend/configuration security | 377 | 0 |
| ASGI client contract, final targeted run | 31 | 0 |
| CI gate contract, within regression run | 78 | 0 |
| Browser acquisition contract, within regression run | 51 | 0 |

The workflow YAML parsed; all **22 shell blocks** passed `bash -n`. Its embedded
container verifier and all four changed/new Python source files parsed. These
are syntax checks, not container execution. A direct source comparison against
the base revision reproduced the stale timestamp and showed the new reader
preserving the artifact date: **2 passed / 0 failed**, using synthetic metadata.

The full 27-target dependency/provider/remediation group was also executed
through `tools/ci_run.sh` using the target list now present in `ci.yml`. The
first run used a stale local venv path and fell back to the current runtime:
**25 targets passed / 2 failed**, due to missing psutil and FastAPI metadata.
A new Python **3.11.15** environment was installed with the existing hash-locked
`requirements.txt` and `requirements-dev.txt`. `uv pip check` validated all
31 installed packages. This required no manifest changes.

The locked-runtime aggregate again reported **25 targets passed / 2 failed**:
the ASGI target required pip (not initially seeded by uv), and cancellation
encountered `psutil.NoSuchProcess` for the running parent's PID in this local
environment. After `python -m ensurepip --upgrade`, the ASGI target passed
**31/31**. Cancellation remains **NOT VERIFIED locally** and was not skipped,
patched or removed from CI. The local full aggregate is not claimed green.

Logs: `evidence/build-provenance-regression.log`,
`evidence/build-provenance-regression-locked.log`,
`evidence/build-provenance-security-locked.log`, and
`evidence/build-provenance-asgi-final.log` in the audit workspace.

## Browser verification and CI status

No frontend files are changed. This phase has not executed a new real-browser
run locally: **BROWSER NOT VERIFIED locally for this change**. The previous main
revision's CI #35 and live verification #23 remain separate historical evidence.

Draft [PR #5](https://github.com/NAIFMUSFER/AI-Instruction/pull/5) was published
at `3594581e48329c9112832dc6e491ed02d63a0d50`.
[CI #36](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/34010050384)
provided the following evidence at preparation of this corrective commit:

- The real Docker build/boot job succeeded. Its image provenance verifier
  passed **14/14**, including the artifact, HTTP endpoints, expected checkout
  revision, build interval and resistance to injected stale runtime timestamps.
- The dependency/provider/remediation group passed **27 targets / 0 failed**.
  Cancellation passed **159/159** in GitHub's runner; the local process-inspection
  limitation remains recorded above. Both Python and npm advisory scans reported
  no known vulnerabilities.
- Deployment closure failed **599 passed / 1 failed**: `ACS_BUILD_INFO_SOURCE`
  was not recognized as defaulted. The checker inspects the explicit default
  argument of `os.environ.get`; it does not infer chained `or` expressions.
  The corrective change declares `environment` as that explicit default while
  preserving empty-string handling. No checker, exemption or gate was changed.
- Real Chromium was still running at this point. CI #36 is not claimed green.

After the correction, these commands were executed from the repository root:

```bash
PATH=/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin:$PATH sh tests/deploy/verify_deploy.sh
/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/remediation/test_image_build_metadata.py
/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/remediation/test_build_metadata.py
```

Results: deployment closure **600 passed / 0 failed**, all **5** browser block
regenerators succeeded without changing tracked generated files, image metadata
**41 passed / 0 failed**, and existing metadata **99 passed / 0 failed**. Logs are
`evidence/build-provenance-deploy-closure-fixed.log`,
`evidence/build-provenance-image-final.log` and
`evidence/build-provenance-metadata-final.log` in the audit workspace.

Docker is not installed locally; its execution evidence above comes from the
named GitHub job. **CI VERIFICATION PENDING for the corrective revision**. All
existing required jobs, including real Chromium and cancellation, remain mandatory.

## Deployment status and prioritized release plan

**PRODUCTION VERIFICATION PENDING for this change.** No production deployment,
main merge, environment mutation or paid AI call was performed in this phase.

1. Run the draft PR's complete CI, especially Docker provenance and cancellation.
2. Review the migration and merge only after every required job succeeds.
3. Deploy the approved revision; check the actual image build log, expected
   frontend/backend commits, `/health`, `/ready`, `/version`, CSP and CORS.
4. Confirm the backend date is from the built artifact, not the old August
   environment value. Existing timestamp variables are ignored in Docker file
   mode; removing them is optional cleanup after review, not a required fix.
5. Repeat live production verification. Keep paid generation disabled unless
   explicitly authorized. Roll back to the prior image on failed release checks.

Render's plugin directory reports it installed/enabled, but its service-management
tools were not exposed in this active session. Authenticated Render settings and
deploy history have therefore **NOT BEEN READ**. This is an access/tool-loading
limitation, not evidence that a deployment was inspected or changed.

## Definition of done

The fix closes only when the same revision passes existing CI, the real image
checks demonstrate resistance to stale runtime timestamps, and an authorized
deployment exposes matching, artifact-derived identity. Metadata checks do not
establish structural safety, regulatory compliance or completion of unrelated
production architecture gaps. Regulatory validation: **NOT EVALUATED**.

Primary platform references: [Render Docker arguments](https://render.com/docs/docker#environment-variable-translation),
[Render revision variables](https://render.com/docs/environment-variables).
