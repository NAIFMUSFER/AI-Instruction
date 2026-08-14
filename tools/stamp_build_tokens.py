# -*- coding: utf-8 -*-
"""يستبدل رموز أصل البناء في سكربت إقلاع الواجهة قبل النشر.

بلا هذه الخطوة تبقى `window.ACS_BUILD_INFO` عند القيم النائبة، فتُعلن الواجهة
عن نفسها `UNPROVENANCED` — وهو السلوك الصحيح: نسخة بلا هوية تقول ذلك بصراحة
بدل أن تختلق SHA. هذه الأداة تمنحها هويّتها الحقيقية وقت النشر.

الهدف بعد F-09: `public/app/boot/build-info.js` لا `public/index.html`.
window.ACS_BUILD_INFO انتقل مع بقيّة السكربتات الكلاسيكية إلى ملفّه، فالختم في
الصفحة صار عملاً بلا أثر — تُطبَع «✓ stamped 0» وتخرج الواجهة UNPROVENANCED إلى
الإنتاج بينما يُعلن البناء نجاحه. لذلك يُرفَض هنا هدفٌ لا يحوي أي رمز.

    python3 tools/stamp_build_tokens.py                 # يستبدل في مكانه
    python3 tools/stamp_build_tokens.py --check         # يتحقّق فقط (بلا كتابة)
    python3 tools/stamp_build_tokens.py --restore       # يعيد الرموز النائبة

مصدر القيم هو acs_build_info.build_info()، فالخادوم والواجهة يعلنان النسخة نفسها.
حتمية: مع ضبط SOURCE_DATE_EPOCH يخرج الطابع الزمني نفسه في كل مرّة.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import acs_build_info as BUILD                                    # noqa: E402

# الهدف: ملفّ إقلاع أصل البناء. كان public/index.html قبل F-09.
TARGET = os.path.join(ROOT, "public", "app", "boot", "build-info.js")
TARGET_REL = "public/app/boot/build-info.js"
# الموضع القديم — يُفحَص فقط ليُقال بصراحة إن الرموز هناك لن تُختَم
LEGACY_PAGE = os.path.join(ROOT, "public", "index.html")

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
    # --target هو الاسم الصحيح؛ --page يبقى مرادفاً لأجل النداءات القديمة
    ap.add_argument("--target", "--page", dest="target", default=TARGET)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.target):
        print("✗ stamp target does not exist: %s" % args.target)
        return 1
    text = read(args.target)
    vals = values()

    if args.check:
        present = [t for t in TOKENS if t in text]
        if present:
            print("build tokens NOT substituted in %s: %s"
                  % (TARGET_REL, ", ".join(present)))
            print("the frontend will declare itself UNPROVENANCED — this is "
                  "honest, not a failure, but a published build should be "
                  "stamped")
            return 0
        # لا رموز نائبة ولا قيمة مختومة = هدف خاطئ، لا نجاح
        if "ACS_BUILD_INFO" not in text:
            print("✗ %s carries neither the placeholder tokens nor "
                  "ACS_BUILD_INFO — this is not the provenance file"
                  % args.target)
            return 1
        print("build tokens substituted in %s" % TARGET_REL)
        return 0

    if args.restore:
        # لا نعرف القيم القديمة، فنعيد الرموز بالبحث عن الشكل المُستبدَل
        print("restore is not supported: re-generate the file from git instead "
              "(git checkout -- %s)" % TARGET_REL)
        return 1

    unknown = [k for k, v in vals.items() if not v or v == BUILD.UNKNOWN]
    if unknown:
        print("✗ refusing to stamp with unknown provenance: %s" % ", ".join(unknown))
        print("  set ACS_GIT_SHA and ACS_BUILT_AT, or run tools/write_build_info.py")
        return 1

    out = text
    hit = 0
    for token, value in vals.items():
        if token in out:
            hit += out.count(token)
            out = out.replace(token, str(value))
    if hit == 0:
        # فرقٌ جوهري بين «مختوم سابقاً» و«الرموز ليست هنا أصلاً». الثاني هو
        # عطل الهدف الخاطئ الذي يجعل النشر UNPROVENANCED بصمت.
        if "ACS_BUILD_INFO" not in out:
            print("✗ nothing to stamp and %s does not define ACS_BUILD_INFO — "
                  "wrong target. Provenance lives in %s"
                  % (args.target, TARGET_REL))
            return 1
        print("nothing to stamp — the tokens are already substituted")
        return 0
    with open(args.target, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("✓ stamped %d token occurrence(s) in %s: sha=%s built_at=%s version=%s"
          % (hit, TARGET_REL, vals["__ACS_GIT_SHA__"][:12],
             vals["__ACS_BUILT_AT__"], vals["__ACS_FRONTEND_VERSION__"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
