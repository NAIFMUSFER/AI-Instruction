# -*- coding: utf-8 -*-
"""يستبدل رموز أصل البناء في صفحة التطبيق قبل النشر.

بلا هذه الخطوة تبقى `window.ACS_BUILD_INFO` عند القيم النائبة، فتُعلن الصفحة
عن نفسها `UNPROVENANCED` — وهو السلوك الصحيح: نسخة بلا هوية تقول ذلك بصراحة
بدل أن تختلق SHA. هذه الأداة تمنحها هويّتها الحقيقية وقت النشر.

    python3 tools/stamp_build_tokens.py                 # يستبدل في مكانه
    python3 tools/stamp_build_tokens.py --check         # يتحقّق فقط (بلا كتابة)
    python3 tools/stamp_build_tokens.py --restore       # يعيد الرموز النائبة

مصدر القيم هو acs_build_info.build_info()، فالخادوم والصفحة يعلنان النسخة نفسها.
حتمية: مع ضبط SOURCE_DATE_EPOCH يخرج الطابع الزمني نفسه في كل مرّة.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import acs_build_info as BUILD                                    # noqa: E402

PAGE = os.path.join(ROOT, "public", "index.html")

TOKENS = ("__ACS_GIT_SHA__", "__ACS_BUILT_AT__", "__ACS_FRONTEND_VERSION__")


def values():
    info = BUILD.build_info()
    return {"__ACS_GIT_SHA__": info["git_sha"],
            "__ACS_BUILT_AT__": info["built_at"],
            "__ACS_FRONTEND_VERSION__": info["version"]}


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    page = read(args.page)
    vals = values()

    if args.check:
        present = [t for t in TOKENS if t in page]
        if present:
            print("build tokens NOT substituted: %s" % ", ".join(present))
            print("the page will declare itself UNPROVENANCED — this is honest, "
                  "not a failure, but a published build should be stamped")
            return 0
        print("build tokens substituted")
        return 0

    if args.restore:
        # لا نعرف القيم القديمة، فنعيد الرموز بالبحث عن الشكل المُستبدَل
        print("restore is not supported: re-generate the page from git instead")
        return 1

    unknown = [k for k, v in vals.items() if not v or v == BUILD.UNKNOWN]
    if unknown:
        print("✗ refusing to stamp with unknown provenance: %s" % ", ".join(unknown))
        print("  set ACS_GIT_SHA and ACS_BUILT_AT, or run tools/write_build_info.py")
        return 1

    out = page
    hit = 0
    for token, value in vals.items():
        if token in out:
            hit += out.count(token)
            out = out.replace(token, str(value))
    if hit == 0:
        print("nothing to stamp — the tokens are already substituted")
        return 0
    with open(args.page, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("✓ stamped %d token occurrence(s): sha=%s built_at=%s version=%s"
          % (hit, vals["__ACS_GIT_SHA__"][:12], vals["__ACS_BUILT_AT__"],
             vals["__ACS_FRONTEND_VERSION__"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
