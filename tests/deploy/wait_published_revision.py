"""Bounded, credential-free deployment identity wait; failures retain evidence."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request


SHA = re.compile(r"[a-f0-9]{40}\Z")
MAX_BYTES = 256 * 1024


def revision(kind, text):
    if kind == "frontend":
        # Read the stamped literal, never execute remote JavaScript.
        raw = re.search(r"\bvar\s+RAW\s*=\s*\{([^}]+)\}", text)
        match = re.search(r'\bgit_sha\s*:\s*"([^"]+)"', raw[1]) if raw else None
        value = match[1] if match and "window.ACS_BUILD_INFO = INFO" in text else None
    else:
        data = json.loads(text)
        value = data.get("git_sha") if isinstance(data, dict) and data.get("provenance_verified") is True else None
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("INVALID_BUILD_IDENTITY")
    return value


def observe(kind, url, expected, timeout):
    try:
        request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "ACS-public-release-check/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(body) > MAX_BYTES:
                raise ValueError("INVALID_METADATA_RESPONSE")
        sha = revision(kind, body.decode("utf-8"))
        return {"status": "MATCH" if sha == expected else "MISMATCH", "git_sha": sha}
    except urllib.error.HTTPError as error:
        return {"status": "UNAVAILABLE", "http_status": error.code}
    except (ValueError, UnicodeError):
        return {"status": "INVALID", "error": "INVALID_BUILD_IDENTITY"}
    except Exception as error:
        # No arbitrary response, exception message, token or URL is logged.
        return {"status": "UNAVAILABLE", "error_type": type(error).__name__}


def wait(frontend, backend, expected, seconds, output, *, probe=observe,
         clock=time.monotonic, pause=time.sleep):
    evidence = {"schema": "acs-published-revision-wait/1.0", "expected_sha": expected,
                "frontend": frontend, "backend": backend, "verdict": "FAIL", "attempts": []}
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    def save():
        path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    save()  # Interrupted runs retain non-success evidence.
    if not SHA.fullmatch(expected or "") or not 0 < seconds <= 600:
        evidence["reason"] = "INVALID_EXPECTED_SHA_OR_WAIT_BOUND"
        save()
        return 1
    start = clock()
    deadline = start + seconds
    endpoints = {"frontend": frontend.rstrip("/") + "/app/boot/build-info.js",
                 "backend": backend.rstrip("/") + "/version"}
    while clock() < deadline:
        attempt = {"elapsed_seconds": round(clock() - start, 2), "observed": {}}
        for kind, url in endpoints.items():
            remaining = deadline - clock()
            if remaining <= 0:
                attempt["observed"][kind] = {"status": "UNAVAILABLE", "error": "WAIT_DEADLINE"}
            else:
                attempt["observed"][kind] = probe(kind, url, expected, min(15, remaining))
        evidence["attempts"].append(attempt)
        if all(value["status"] == "MATCH" for value in attempt["observed"].values()):
            evidence["verdict"] = "PASS"
            save()
            print("PUBLISHED REVISION: PASS — both public endpoints match " + expected)
            return 0
        save()
        print("PUBLISHED REVISION: waiting — " + json.dumps(attempt), flush=True)
        remaining = deadline - clock()
        if remaining > 0:
            pause(min(15, remaining))
    evidence["reason"] = "PUBLISHED_REVISION_NOT_MATCHED_WITHIN_BOUND"
    save()
    print("PUBLISHED REVISION: FAIL — missing, invalid or mismatched identity; see " + str(path))
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-sha", default=os.environ.get("ACS_VERIFY_EXPECT_SHA", ""))
    parser.add_argument("--frontend", default=os.environ.get("ACS_VERIFY_FRONTEND", "https://sprightly-selkie-d906c3.netlify.app"))
    parser.add_argument("--backend", default=os.environ.get("ACS_VERIFY_BACKEND", "https://acs-engine.onrender.com"))
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument("--output", default="logs/published/revision-wait.json")
    args = parser.parse_args()
    return wait(args.frontend, args.backend, args.expect_sha, args.seconds, args.output)


if __name__ == "__main__":
    sys.exit(main())
