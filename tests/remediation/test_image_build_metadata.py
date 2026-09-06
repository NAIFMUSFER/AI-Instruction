#!/usr/bin/env python3
"""Exercise the real stamper and reader in a directory with no Git checkout.

This is a subprocess contract test, not a Docker execution. CI separately boots
the actual image and checks its HTTP endpoints against the embedded artifact.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40
OLD = "2000-01-01T00:00:00Z"
passed = failed = 0


def check(name, ok):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(("  ✓ " if ok else "  ✗ ") + name)


def base_env():
    env = os.environ.copy()
    for key in ("ACS_GIT_SHA", "ACS_GIT_BRANCH", "RENDER_GIT_COMMIT",
                "RENDER_GIT_BRANCH", "COMMIT_REF", "GITHUB_SHA", "SOURCE_VERSION",
                "ACS_BUILT_AT", "BUILD_TIMESTAMP", "BRANCH", "HEAD", "ACS_VERSION",
                "ACS_BUILD_INFO_SOURCE", "ACS_BUILD_INFO_FILE", "SOURCE_DATE_EPOCH"):
        env.pop(key, None)
    return env


with tempfile.TemporaryDirectory(prefix="acs_image_metadata_") as tmp:
    root = Path(tmp)
    (root / "tools").mkdir()
    for rel in ("acs_build_info.py", "tools/write_build_info.py"):
        shutil.copyfile(ROOT / rel, root / rel)
    file = root / "build_info.json"
    env = base_env()
    env.update(RENDER_GIT_COMMIT=SHA, RENDER_GIT_BRANCH="main",
               ACS_BUILT_AT=OLD, BUILD_TIMESTAMP=OLD)
    command = [sys.executable, str(root / "tools/write_build_info.py"),
               "--require-provenance"]

    def run(args, runtime_env):
        return subprocess.run(args, cwd=root, env=runtime_env, capture_output=True,
                              text=True, timeout=20)

    def read(source="file"):
        runtime = base_env()
        runtime.update(ACS_BUILD_INFO_SOURCE=source, ACS_BUILT_AT=OLD,
                       BUILD_TIMESTAMP=OLD, ACS_GIT_SHA="b" * 40,
                       ACS_GIT_BRANCH="stale-branch", ACS_VERSION="stale-version")
        result = run([sys.executable, "-c", "import json, acs_build_info; "
                      "print(json.dumps(acs_build_info.build_info()))"], runtime)
        check("reader subprocess exits successfully", result.returncode == 0)
        return json.loads(result.stdout)

    before = datetime.now(timezone.utc).replace(microsecond=0)
    result = run(command, env)
    after = datetime.now(timezone.utc)
    check("stamper runs without a Git checkout", result.returncode == 0)
    check("stamper creates the artifact", file.is_file())
    payload = json.loads(file.read_text(encoding="utf-8"))
    stamp = datetime.fromisoformat(payload["built_at"].replace("Z", "+00:00"))
    check("artifact uses Render's build-time commit", payload["git_sha"] == SHA)
    check("artifact records the build-time branch", payload["git_branch"] == "main")
    check("timestamp was captured during this actual build", before <= stamp <= after)
    check("old runtime timestamp variables do not taint the build", payload["built_at"] != OLD)
    check("stdout describes exactly the artifact written", json.loads(result.stdout) == payload)

    info = read()
    check("file mode keeps the image commit despite a runtime override", info["git_sha"] == SHA)
    check("file mode keeps the image timestamp despite BOTH stale variables",
          info["built_at"] == payload["built_at"])
    check("file mode keeps branch and version from the same artifact",
          info["git_branch"] == payload["git_branch"] and info["version"] == payload["version"])
    check("valid image metadata passes validation", info["provenance_verified"] is True)
    check("the public eight-field response contract is unchanged", set(info) == {
        "service", "version", "git_sha", "git_sha_short", "git_branch", "built_at",
        "schema_versions", "provenance_verified"})
    check("reading in a new process does not restamp the image", read() == info)
    check("the artifact path is not exposed", str(root) not in json.dumps(info))
    legacy = read("environment")
    check("explicit compatibility mode preserves native deployment precedence",
          legacy["git_sha"] == "b" * 40 and legacy["built_at"] == OLD)

    for name, text in [
        ("missing", None), ("corrupt", "{"), ("non-object", "[]"),
        ("wrong schema", json.dumps(dict(payload, schema="unknown"))),
        ("untyped identity", json.dumps(dict(payload, git_sha=[], built_at={}))),
        ("missing timestamp", json.dumps({k: v for k, v in payload.items() if k != "built_at"})),
    ]:
        if text is None:
            file.unlink()
        else:
            file.write_text(text, encoding="utf-8")
        broken = read()
        check(name + " artifact cannot be verified from runtime fallbacks",
              broken["provenance_verified"] is False and broken["built_at"] == "unknown")

    file.write_text(json.dumps(payload), encoding="utf-8")
    check("an invalid source mode cannot silently select legacy metadata",
          read("misspelled")["provenance_verified"] is False)

    rejected = root / "rejected.json"
    for name, overrides, extra in [
        ("missing commit", {"RENDER_GIT_COMMIT": ""}, []),
        ("invalid commit", {"RENDER_GIT_COMMIT": "invalid"}, []),
        ("invalid time", {}, ["--built-at", "invalid"]),
        ("naive time", {}, ["--built-at", "2026-01-01T00:00:00"]),
    ]:
        attempt = run(command + ["--out", str(rejected)] + extra, dict(env, **overrides))
        check(name + " fails the build before producing an artifact",
              attempt.returncode != 0 and not rejected.exists() and not attempt.stdout)

    deterministic = dict(env, SOURCE_DATE_EPOCH="1700000000")
    first = run(command, deterministic)
    second = run(command, deterministic)
    check("explicit reproducible builds remain byte-identical",
          first.returncode == second.returncode == 0 and first.stdout == second.stdout)

docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
check("Docker executes the strict stamper during image build",
      "RUN python tools/write_build_info.py --require-provenance" in docker)
check("Docker explicitly opts into file provenance", "ENV ACS_BUILD_INFO_SOURCE=file" in docker)
check("CI includes this subprocess suite", "tests/remediation/test_image_build_metadata.py" in workflow)
check("CI verifies the actual container's provenance endpoints", "IMAGE PROVENANCE:" in workflow)

print("\nIMAGE BUILD METADATA: %d passed, %d failed (subprocesses; Docker checked separately in CI)"
      % (passed, failed))
sys.exit(1 if failed else 0)
