# -*- coding: utf-8 -*-
"""يحقن واجهة المطوّر وممرّ التقديم للطبقة البصرية في وحدات public/app/ (F-09).

طبقة العرض البصري نفسها ومواصفتها ACS_VISUAL_SPEC جزء من المُسلَّم المحفوظ ولا
تُولَّد هنا: هذا الحاقن مسؤول عن كتلتين إضافيتين فقط، ويتخطّى ما هو محقون بالفعل.

بعد التفكيك صارت ACS_VISUAL_SPEC في public/app/render/scene.js، فصار هو الهدف
المُعلَن الذي يُتحقَّق منه أوّلاً. أمّا مربطا الكتلتين فهما نصّان داخل الشيفرة لا
علامتان، وقد ينقلهما التفكيك إلى وحدة أخرى؛ لذلك يُبحَث عنهما في وحدات
public/app/ كلّها ويُكتَب في الوحدة التي تحملهما وحدها. إن غاب مربط — أو وُجد في
أكثر من وحدة — يُرفَع خطأ صريح يسمّي المربط والوحدات: لا انهيار غامض ولا تخطٍّ
صامت، فالكتلة الغائبة تعني ميزة غائبة وذلك يُقال بصوت عالٍ.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import app_source as APP  # noqa: E402 — التخطيط بعد التفكيك يُعرَف من مصدر واحد

# الهدف المُعلَن: الوحدة التي تحمل الطبقة البصرية ومواصفتها بعد التفكيك
TARGET = os.path.join(APP.APP, "render", "scene.js")
SPEC_SYMBOL = "ACS_VISUAL_SPEC"

# (اسم الكتلة، ملفّ نصّها، الحارس الذي يدلّ أنها محقونة، المربط الذي تُحقن قبله)
BLOCKS = (
    ("developer API", "_visual_api_block.js", "window.ACS.visualScene",
     "  /* ---- تنسيق بين التخصّصات: كشف وتتبّع فقط. لا إصلاح ولا إعادة توجيه ---- */"),
    ("presentation renderer pass", "_visual_renderer_block.js", "let VIS_GROUP=null",
     "function setSun(elev,azi){const phi=THREE.MathUtils.degToRad(90-elev)"),
)


def _fail(msg):
    raise SystemExit("%s: %s" % (os.path.basename(__file__), msg))


def _read(path):
    if not os.path.exists(path):
        _fail("target file not found: %s\n"
              "  after F-09 the visual layer lives in the modules under "
              "public/app/ (layout: tools/app_source.py).\n"
              "  restore the file (or fix the layout) before regenerating."
              % path)
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _find(needle, mods):
    """الوحدات التي يظهر فيها النصّ — بالمسار النسبيّ تحت public/app/."""
    return sorted(f for f, src in mods.items() if needle in src)


def main():
    src = _read(TARGET)
    if SPEC_SYMBOL not in src:
        _fail("%s is missing from %s.\n"
              "  the visual layer block is part of the committed artefact and "
              "is not regenerated here; this injector only adds the developer "
              "API and the presentation renderer pass on top of it.\n"
              "  restore that block before running this tool."
              % (SPEC_SYMBOL, TARGET))
    print("visual layer: %s present in %s"
          % (SPEC_SYMBOL, os.path.relpath(TARGET, ROOT)))

    mods = APP.modules()
    done = []
    for name, block_file, guard, anchor in BLOCKS:
        where = _find(guard, mods)
        if where:
            print("  present   %-27s in %s"
                  % (name, ", ".join("public/app/" + w for w in where)))
            continue
        hosts = _find(anchor, mods)
        if len(hosts) != 1:
            _fail("cannot inject the %s: its anchor occurs in %d module(s) "
                  "under public/app/, and exactly one is required.\n"
                  "  anchor: %s\n"
                  "  found in: %s\n"
                  "  this anchor is plain code, not a marker, so the split may "
                  "have moved or reshaped it. re-point it at the module that "
                  "now owns that code: until then the block in tools/%s is NOT "
                  "injected and the feature is absent."
                  % (name, len(hosts), anchor,
                     ", ".join("public/app/" + h for h in hosts) or "no module",
                     block_file))
        host = os.path.join(APP.APP, hosts[0])
        block = _read(os.path.join(HERE, block_file))
        out = mods[hosts[0]].replace(anchor, block + anchor, 1)
        with io.open(host, "w", encoding="utf-8") as f:
            f.write(out)
        print("  injected  %-27s → %s  block=%d bytes  file=%d bytes"
              % (name, os.path.relpath(host, ROOT),
                 len(block.encode("utf-8")), len(out.encode("utf-8"))))
        done.append(name)

    print("injected: %s" % (", ".join(done) if done else
                            "nothing (both blocks already present)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
