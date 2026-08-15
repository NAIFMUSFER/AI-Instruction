# -*- coding: utf-8 -*-
"""نموذج اصطناعي كبير للمرحلة 8.

ليس مستودعاً ولا نمطاً معمارياً بعينه: شبكة فراغات منتظمة على عدّة أدوار،
غايتها قياس الأداء على ملفّ IFC حقيقي كبير داخل الحدود المعلَنة. لا يُدّعى أنه
تصميم، ولا تُشتقّ منه أي نتيجة هندسية.
"""


def large_model(levels=8, cols=8, rows=8, room_w=6.0, room_d=5.0,
                floor_height=3.4, wall_h=3.2):
    """شبكة cols×rows فراغاً في كل دور، لكل فراغ باب ونافذتان."""
    floors = {}
    level_list = []
    for li in range(levels):
        tmpl = 'lv%d' % li
        level_list.append({"index": li, "name": "level %d" % li,
                           "template": tmpl})
        rooms = []
        for c in range(cols):
            for r in range(rows):
                x = c * room_w
                z = r * room_d
                room = {
                    "id": "r%02d_%02d" % (c, r),
                    "name": "Room %d-%d-%d" % (li, c, r),
                    "rect": [x, z, room_w, room_d],
                    "doors": [{"edge": "N" if r == 0 else "S",
                               "offset": room_w / 2.0, "width": 0.9}],
                    "windows": [
                        {"edge": "E", "offset": room_d / 2.0, "width": 1.4,
                         "height": 1.4, "sill": 0.9},
                        {"edge": "W", "offset": room_d / 2.0, "width": 1.4,
                         "height": 1.4, "sill": 0.9}],
                }
                if c == 0 and r == 0:
                    room["objects"] = [{"count": 1, "kind": "stairs",
                                        "x": 1.0, "z": 1.0}]
                rooms.append(room)
        floors[tmpl] = {"rooms": rooms}
    return {
        "meta": {"name": "synthetic_grid", "type": "generic"},
        "site": {"w": cols * room_w + 20.0, "d": rows * room_d + 20.0},
        "floor_height": floor_height,
        "wall_h": wall_h,
        "levels": level_list,
        "floors": floors,
    }
