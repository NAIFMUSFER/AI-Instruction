# -*- coding: utf-8 -*-
"""تجهيزات المرحلة 9: نماذج المستودع بكل تخصّصاتها، ونماذج شبكية للقياس.

المستودع ليس نمطاً معمارياً هنا؛ إنه أحد نماذج الفحص إلى جانب الفيلا والفندق
والعيادة والمكتب. نماذج التخصّصات تأتي من تجهيزات المرحلة الثالثة نفسها.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def models():
    """كل النماذج المعمارية المشحونة في المستودع."""
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'base_fixtures.json'), encoding='utf-8') as f:
        base = json.load(f)
    with open(os.path.join(ROOT, 'tests', 'phase7', 'fixtures',
                           'render_fixtures.json'), encoding='utf-8') as f:
        base.update(json.load(f))
    return base


def discipline_models():
    """نماذج تحمل بيانات إنشائية أو كهروميكانيكية أو حريق ممثَّلة فعلاً."""
    out = {}
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'mep_fixtures.json'), encoding='utf-8') as f:
        out.update(json.load(f)['models'])
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'fls_fixtures.json'), encoding='utf-8') as f:
        out.update(json.load(f)['models'])
    return out


def all_models():
    m = models()
    m.update(discipline_models())
    return m


def grid_model(spaces=100, cols=10, room_w=5.0, room_d=4.0,
               floor_height=3.2, wall_h=3.0):
    """نموذج شبكي بعدد فراغات مطلوب — لقياس الأداء لا لادّعاء تصميم."""
    rows = max(1, (spaces + cols - 1) // cols)
    per_level = cols * rows
    levels = max(1, (spaces + per_level - 1) // per_level)
    made = 0
    floors, level_list = {}, []
    for li in range(levels):
        tmpl = 'g%d' % li
        level_list.append({"index": li, "name": "level %d" % li, "template": tmpl})
        rlist = []
        for c in range(cols):
            for r in range(rows):
                if made >= spaces:
                    break
                made += 1
                rlist.append({
                    "id": "r%02d_%02d" % (c, r),
                    "name": "Room %d-%d-%d" % (li, c, r),
                    "rect": [c * room_w, r * room_d, room_w, room_d],
                    "doors": [{"edge": "N" if r == 0 else "S",
                               "offset": room_w / 2.0, "width": 0.9}],
                    "windows": [{"edge": "E", "offset": room_d / 2.0,
                                 "width": 1.4, "height": 1.4, "sill": 0.9}],
                })
        floors[tmpl] = {"rooms": rlist}
    return {"meta": {"name": "grid_%d" % spaces, "type": "generic"},
            "site": {"w": cols * room_w + 20.0, "d": rows * room_d + 20.0},
            "floor_height": floor_height, "wall_h": wall_h,
            "levels": level_list, "floors": floors}


HOSTILE_TEXT = [
    "<scr" + "ipt>window.__PWNED__=1</scr" + "ipt>",
    '<img src=x onerror="window.__PWNED__=1">',
    "javascript:window.__PWNED__=1",
    "../../etc/passwd",
    "<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]>",
    "vbscript:msgbox(1)",
    "data:text/html;base64,PHNjcmlwdD54PC9zY3JpcHQ+",
]
INERT_TEXT = ["__proto__", "constructor", "prototype", "{{7*7}}",
              "<b>bold</b>", 'a "quoted" & <tag>', "مجلس", "O'Brien Room",
              "Café – 100%", "🏗️ site"]
HOSTILE_FILENAMES = ["../escape.svg", "/etc/passwd", "..\\win.svg",
                     "a/b.svg", "CON", "NUL.svg", "with space.svg",
                     "x" * 200 + ".svg", "", "\x00.svg", ".hidden"]
