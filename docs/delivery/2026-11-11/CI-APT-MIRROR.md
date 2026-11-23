# Verified CI package mirror — 11 November 2026

The guest-roof browser increment remains gated. CI6 and CI7 repeatedly failed before browser/PDF tests while resolving the runner's Azure/archive/security Ubuntu mirrors. The Poppler step failed with exit100 on head `6a0dfd85e31b0c89df3eac0076d0e7a424084d75`, repeated on its retry, and failed again on `f95110cb15f68e02591f7cf5a949ada368e6e856` in [CI7 critical job130603827758](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43044238128/job/130603827758). Other network-dependent pip/npm/advisory and Docker jobs completed. This is observed domain-specific resolution failure; it does not establish a general GitHub outage or distinguish upstream DNS from runner egress policy.

## Bounded setup change

`tools/ci_prepare_apt.py` runs only as the ordinary user on a GitHub Ubuntu runner with the known mirror-list layout. It first probes the primary archive over HTTPS. Only mirror DNS/connect/timeout failures (curl6/7/28) permit the single configured kernel.org alternative. It does not change DNS, proxy settings, TLS validation, APT keys/preferences, package pins, source components or suites.

For the runner's actual codename and architecture, all four release pockets must download within bounded time/size limits, pass `gpgv` with the system Ubuntu archive keyring in an isolated home, and match the expected Ubuntu origin, suite, codename and architecture. Signed Date and optional Valid-Until are checked; no invented expiry is imposed on an immutable base release. TLS/HTTP/policy/signature/metadata/freshness errors fail closed. An unknown source layout or no verified mirror also fails.

Only after validation is the known mirror list backed up and atomically replaced with the verified HTTPS candidate at priority0; the original fallback entries remain. Explicit priority matters because equal-priority entries are randomized. APT subsequently performs its normal signature, validity and package-hash checks during the unchanged installs. No network command runs under sudo.

The existing five affected jobs call the helper before dependency installation: main Chromium, delivery-critical, Google auth, Async delivery and2D review. Every prior install/test command and individual test timeout remains unchanged. The separate overall Google-job budget correction is described below. The14-case offline regression runs in the existing Python contract job, which needs no apt/browser setup.

## Evidence and limits

The helper's offline tests passed, including signature/TLS/wrong-suite/expired-metadata rejection, no-candidate refusal, unchanged files on failure, and backup-before-replacement. These tests mock subprocess results and do not establish real Ubuntu signature verification or runner connectivity. A standalone import-path failure with PYTHONPATH unset was reproduced and corrected in the test; the exact existing ci_run wrapper now passes without changing its environment.

Primary sources establish the alternative's intended role and current metadata availability:

- [Ubuntu Noble package download page](https://packages.ubuntu.com/en/noble/amd64/base-files/download) lists mirrors.kernel.org/ubuntu.
- [Ubuntu mirror guidance](https://discourse.ubuntu.com/t/redirecting-apt-sources-to-address-increased-load-a-guide-to-using-community-mirrors/80500) documents using one mirror for release/update/security pockets while retaining the Ubuntu archive Signed-By keyring.
- [APT mirror transport manual](https://manpages.ubuntu.com/manpages/resolute/man1/apt-transport-mirror.1.html) defines metadata and priority ordering.
- [Mirror distribution index](https://mirrors.edge.kernel.org/ubuntu/dists/) exposes Noble and Resolute pockets. Live retrievals of all four Resolute InRelease files returned HTTP200 and matching metadata; their PGP envelopes alone are not signature validation.
- The observed GitHub images were Ubuntu26.04.1 (`20261101.186.1`) for Chromium and24.04.5 (`20261101.360.1`) for delivery-critical. Both image-tag versions of [the runner source configuration](https://github.com/actions/runner-images/blob/ubuntu26/20261101.186/images/ubuntu/scripts/build/configure-apt-sources.sh) use the same three mirrors with priorities1/2/3. The helper retains each actual codename; it does not replace Resolute with Noble.

Launchpad's live mirror registry was inaccessible and its current approval/status is not claimed. The initial local evidence did not establish real mirror admission or browser execution. The subsequent CI8 observations below establish those parts; final-head CI acceptance remains required. No deployment, migration, provider call or Step4b geometry work is included.

## Observed CI8 setup success and overall job budget

On head `6e44ae478e351346124865fcae14d00ee7e99fdc`, the helper selected the verified kernel.org mirror and the actual browser/PDF package installation succeeded. The2D Chromium/WebKit job passed138 assertions; delivery-critical completed27 Python targets,14 Node targets and3 real Chromium targets, including the full guest/private/approved-artifact suites. Async independently passed the full auth/guest lifecycle and subsequent mobile/connected/panel tests. These are observed runs, not mocked mirror results.

[Google job130625321145](https://github.com/NAIFMUSFER/AI-Instruction/actions/runs/43050323808/job/130625321145) started15:38:11 UTC, began its actual browser suite15:39:06.950, and printed all3 guest journeys passed15:48:19.454. The overall10-minute job limit canceled it91ms later while the test finally awaited browser closure. There was no assertion failure; the canceled job remains canceled and is not counted as green.

The overall Google job budget is therefore15 minutes, allowing the measured full suite, setup and cleanup. This does not alter any browser assertion, action/wait timeout, storage-recovery delay, or the hard2-second approved-viewer transition budget on hosts with4+logical cores. The final changed head still requires its own complete CI outcome.

[Complete CI8 job evidence](CI8-JOBS.md) records16 successful jobs and the canceled Google job, including full boot33/33, visual326/326 and real browser accessibility136/0. Every job log was read. The final changed head must still pass all its triggered jobs.
