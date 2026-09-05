# -*- coding: utf-8 -*-
# =============================================================================
# acs_build_info.py — أصل البناء (build provenance).
#
# كان النشر بلا هويّة: لا طريقة لمعرفة أيّ التزام يعمل على الخادم أو في الصفحة،
# فأي تحقّق إنتاجي كان يقيس "شيئاً ما" لا نسخةً بعينها.
#
# ترتيب المصادر — أوّل مصدر يجيب هو المعتمد، ولا يُخترَع شيء:
#   1) متغيّرات البيئة التي يحقنها النشر: ACS_GIT_SHA / ACS_BUILT_AT.
#   2) متغيّرات المنصّات المعروفة (Render / Netlify / GitHub Actions).
#   3) ملفّ build_info.json يكتبه سكربت البناء.
#   4) مستودع git محلّي (تطوير فقط).
#   5) "unknown" — تُعلَن كما هي ولا تُستبدَل بقيمة مخترعة.
#
# لا يُعرَض أي سرّ: SHA وطابع زمني ورقم إصدار فقط.
# =============================================================================
import json
import os
import re
import subprocess
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
UNKNOWN = "unknown"

SERVICE_NAME = "ACS Understanding Engine"
SERVICE_VERSION = "1.3"

SCHEMA_VERSIONS = {
    "error_contract": "acs-error-envelope/1.0.0",
    "engineering_changes": "acs-engineering-changes/1.0.0",
    "api_base": "acs-api-base/1.0.0",
}

_ENV_SHA = ("ACS_GIT_SHA", "RENDER_GIT_COMMIT", "COMMIT_REF",
            "GITHUB_SHA", "SOURCE_VERSION")
_ENV_BUILT = ("ACS_BUILT_AT", "BUILD_TIMESTAMP")
_ENV_BRANCH = ("ACS_GIT_BRANCH", "RENDER_GIT_BRANCH", "BRANCH", "HEAD")


def _env_first(names):
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return None


def _from_file():
    path = os.environ.get("ACS_BUILD_INFO_FILE", "") or os.path.join(_HERE, "build_info.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _from_git():
    try:
        sha = subprocess.check_output(
            ["git", "-C", _HERE, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5).decode("ascii").strip()
        return sha or None
    except Exception:
        return None


def _short(sha):
    return sha[:12] if sha and sha != UNKNOWN else UNKNOWN


def build_info():
    """أصل البناء كما هو — بلا اختراع ولا سرّ."""
    fileinfo = _from_file()
    sha = _env_first(_ENV_SHA) or fileinfo.get("git_sha") or _from_git() or UNKNOWN
    # Metadata from a different commit cannot establish this deployment's age.
    matching_file = fileinfo if fileinfo.get("git_sha") == sha else {}
    built = _env_first(_ENV_BUILT) or matching_file.get("built_at") or UNKNOWN
    branch = _env_first(_ENV_BRANCH) or matching_file.get("git_branch") or UNKNOWN
    version = (os.environ.get("ACS_VERSION", "") or "").strip() \
        or matching_file.get("version") or SERVICE_VERSION
    try:
        timestamp = datetime.fromisoformat(str(built).replace("Z", "+00:00"))
        valid_time = timestamp.tzinfo is not None
    except (ValueError, TypeError):
        valid_time = False
    return {
        "service": SERVICE_NAME,
        "version": version,
        "git_sha": sha,
        "git_sha_short": _short(sha),
        "git_branch": branch,
        "built_at": built,
        "schema_versions": dict(SCHEMA_VERSIONS),
        "provenance_verified": bool(re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?",
                                                 str(sha))) and valid_time,
    }


def build_identifier():
    """معرّف قصير يُعرَض في واجهة "عن النظام"."""
    info = build_info()
    return "%s · %s" % (info["version"], info["git_sha_short"])


if __name__ == "__main__":                                      # pragma: no cover
    print(json.dumps(build_info(), ensure_ascii=False, indent=2))
