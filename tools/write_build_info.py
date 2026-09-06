#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# tools/write_build_info.py — يختم أصل البناء في build_info.json.
#
# بلا هذا الملفّ لا يعرف الخادم المنشور أيّ التزام يعمل عليه: بيئات البناء
# (Netlify / Render / GitHub Actions) تعرف الـSHA وقت البناء ولا تعرفه بعده،
# فيُكتب هنا مرّة ليقرأه acs_build_info._from_file لاحقاً.
#
# المصادر — بلا اختراع:
#   git_sha    : git rev-parse HEAD
#   git_branch : git rev-parse --abbrev-ref HEAD  (ثمّ متغيّرات البيئة المعلنة)
#   built_at   : --built-at  ثمّ  SOURCE_DATE_EPOCH  ثمّ  الآن (UTC)
#
# الحتميّة: مع SOURCE_DATE_EPOCH مضبوطاً يكون المخرج متطابقاً بايتاً بايتاً بين
# التشغيلات — لا شيء آخر في هذا الملفّ يتغيّر بمرور الزمن.
#
#   python3 tools/write_build_info.py
#   SOURCE_DATE_EPOCH=1700000000 python3 tools/write_build_info.py
#   python3 tools/write_build_info.py --built-at 2026-01-01T00:00:00Z
# =============================================================================
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

DEFAULT_OUT = os.path.join(ROOT, "build_info.json")
UNKNOWN = "unknown"

# أسماء الفرع التي تحقنها منصّات البناء — نفس ترتيب acs_build_info
_ENV_BRANCH = ("ACS_GIT_BRANCH", "RENDER_GIT_BRANCH", "BRANCH", "HEAD")
_ENV_SHA = ("ACS_GIT_SHA", "RENDER_GIT_COMMIT", "COMMIT_REF",
            "GITHUB_SHA", "SOURCE_VERSION")


def _git(*args):
    try:
        out = subprocess.check_output(("git", "-C", ROOT) + args,
                                      stderr=subprocess.DEVNULL, timeout=10)
        return out.decode("utf-8", "replace").strip() or None
    except Exception:
        return None


def _env_first(names):
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return None


def iso_utc(epoch=None):
    """ISO-8601 بتوقيت UTC وبثانية كاملة — Z لا +00:00."""
    if epoch is None:
        dt = datetime.now(timezone.utc)
    else:
        dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_built_at(cli_value=None):
    """--built-at ثمّ SOURCE_DATE_EPOCH ثمّ الآن. لا قيمة مخترعة."""
    if cli_value:
        return cli_value.strip()
    sde = (os.environ.get("SOURCE_DATE_EPOCH") or "").strip()
    if sde:
        try:
            return iso_utc(int(sde, 10))
        except (TypeError, ValueError):
            sys.stderr.write(
                "SOURCE_DATE_EPOCH=%r is not an integer; using the current "
                "time instead\n" % sde)
    return iso_utc()


def build_payload(built_at=None):
    sha = _env_first(_ENV_SHA) or _git("rev-parse", "HEAD") or UNKNOWN
    branch = _env_first(_ENV_BRANCH) or _git("rev-parse", "--abbrev-ref",
                                             "HEAD") or UNKNOWN
    try:
        import acs_build_info as B
        service, version = B.SERVICE_NAME, B.SERVICE_VERSION
        schema_versions = dict(B.SCHEMA_VERSIONS)
    except Exception:                                             # pragma: no cover
        service, version, schema_versions = UNKNOWN, UNKNOWN, {}
    version = (os.environ.get("ACS_VERSION") or "").strip() or version
    return {
        "schema": "acs-build-info/1.0.0",
        "service": service,
        "version": version,
        "git_sha": sha,
        "git_sha_short": sha[:12] if sha != UNKNOWN else UNKNOWN,
        "git_branch": branch,
        "built_at": resolve_built_at(built_at),
        "schema_versions": schema_versions,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Stamp build provenance into build_info.json.")
    ap.add_argument("--built-at", default=None,
                    help="ISO-8601 UTC timestamp; overrides SOURCE_DATE_EPOCH")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="output path (default: <repo>/build_info.json)")
    ap.add_argument("--print-only", action="store_true",
                    help="print the JSON without writing the file")
    ap.add_argument("--require-provenance", action="store_true",
                    help="reject missing/invalid commit or timestamp before writing")
    args = ap.parse_args(argv)

    payload = build_payload(args.built_at)
    if args.require_provenance:
        try:
            timestamp = datetime.fromisoformat(payload["built_at"].replace("Z", "+00:00"))
            valid_time = timestamp.tzinfo is not None
        except (ValueError, TypeError):
            valid_time = False
        if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", payload["git_sha"]) \
                or not valid_time:
            sys.stderr.write("Build provenance requires a full commit SHA and a "
                             "timezone-aware timestamp; no file was written.\n")
            return 1
    text = json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"
    if not args.print_only:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stderr.write("wrote %s\n" % args.out)
    sys.stdout.write(text)
    return 0 if payload["git_sha"] != UNKNOWN else 1


if __name__ == "__main__":
    raise SystemExit(main())
