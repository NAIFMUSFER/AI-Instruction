# -*- coding: utf-8 -*-
# =============================================================================
# acs_compiler.py  --  ACS Geometry Compiler  (Building JSON -> glTF 2.0)
# يحوّل وصفاً منظّماً للمبنى (أدوار/غرف/أبواب/نوافذ/أفياش/إنارة/كاميرات/أثاث)
# إلى نموذج ثلاثي الأبعاد هندسي دقيق (glTF) قابل للمشي داخله، بطبقات وألوان.
#
# لا يعتمد على مكتبات خارجية — مُصدّر glTF مدمج (numpy فقط).
# التشغيل:  python3 acs_compiler.py  <building.json>  <out.gltf>
#
# اصطلاح تسمية العقد للطبقات (يفصله العارض على '|'):
#   LAYER|F<level>|<room>|<detail>
#   LAYER ∈ {WALL, FLOOR, DOOR, WINDOW, ELEC, LIGHT, CAMERA, HVAC, SAFETY, FURN}
# =============================================================================

import json
import sys
import struct
import base64
import numpy as np

# ---------------------------------------------------------------------------
# لوحة الألوان (baseColorFactor RGBA) + خصائص المادة
# ---------------------------------------------------------------------------
MAT = {
    "wall":     (0.82, 0.80, 0.76, 1.0, 0.0, 0.9),
    "floor":    (0.58, 0.58, 0.60, 1.0, 0.0, 0.85),
    "ceiling":  (0.90, 0.90, 0.92, 1.0, 0.0, 0.9),
    "door":     (0.45, 0.28, 0.13, 1.0, 0.0, 0.55),   # خشب
    "door_glass":(0.55, 0.72, 0.85, 0.35, 0.0, 0.1),
    "window":   (0.55, 0.72, 0.88, 0.30, 0.0, 0.08),  # زجاج
    "outlet":   (0.88, 0.10, 0.10, 1.0, 0.2, 0.5),    # فيش أحمر
    "switch":   (0.10, 0.72, 0.24, 1.0, 0.2, 0.5),    # مفتاح أخضر
    "network":  (0.10, 0.35, 0.95, 1.0, 0.2, 0.5),    # شبكة أزرق
    "tv":       (0.05, 0.05, 0.06, 1.0, 0.3, 0.35),   # شاشة
    "usb":      (0.60, 0.30, 0.90, 1.0, 0.2, 0.5),
    "ev":       (0.95, 0.75, 0.10, 1.0, 0.3, 0.4),
    "light":    (1.00, 0.86, 0.35, 1.0, 0.0, 0.4),    # إنارة صفراء
    "camera":   (0.03, 0.03, 0.03, 1.0, 0.4, 0.3),    # كاميرا
    "ac":       (0.25, 0.82, 0.92, 1.0, 0.1, 0.4),    # تكييف
    "safety":   (1.00, 0.45, 0.00, 1.0, 0.1, 0.5),    # سلامة برتقالي
    "furn":     (0.55, 0.50, 0.45, 1.0, 0.0, 0.7),    # أثاث
    "furn_soft":(0.35, 0.42, 0.55, 1.0, 0.0, 0.85),   # كنب
    "counter":  (0.20, 0.22, 0.25, 1.0, 0.1, 0.35),
    # ---- صناعي / لوجستي ----
    "steel":    (0.18, 0.44, 0.82, 1.0, 0.55, 0.42),
    "beam":     (0.96, 0.62, 0.04, 1.0, 0.50, 0.45),
    "deck":     (0.56, 0.57, 0.60, 1.0, 0.30, 0.60),
    "goods":    (0.69, 0.54, 0.32, 1.0, 0.00, 0.85),
    "pallet":   (0.61, 0.48, 0.30, 1.0, 0.00, 0.90),
    "belt":     (0.16, 0.18, 0.20, 1.0, 0.20, 0.55),
    "frame":    (0.60, 0.63, 0.66, 1.0, 0.60, 0.35),
    "guard":    (0.98, 0.80, 0.08, 1.0, 0.30, 0.50),
    "paint_lane": (0.96, 0.62, 0.04, 1.0, 0.0, 0.95),
    "paint_ped":  (0.98, 0.80, 0.08, 1.0, 0.0, 0.95),
    "paint_amr":  (0.55, 0.36, 0.96, 1.0, 0.0, 0.95),
    "paint_zone": (0.15, 0.39, 0.92, 1.0, 0.0, 0.95),
    "paint_fire": (0.94, 0.27, 0.27, 1.0, 0.0, 0.95),
    "dockdoor": (0.32, 0.34, 0.37, 1.0, 0.50, 0.45),
    "bumper":   (0.11, 0.11, 0.13, 1.0, 0.10, 0.85),
    "screen":   (0.04, 0.24, 0.18, 1.0, 0.20, 0.30),
    "robot":    (0.07, 0.07, 0.09, 1.0, 0.50, 0.35),
}

ROLE_COLOR = {
    "receiving": "#14b8a6", "inbound": "#14b8a6", "crossdock": "#0ea5e9", "qc": "#f97316",
    "storage": "#2563eb", "bulk": "#1d4ed8", "bin": "#3b82f6", "shelf": "#3b82f6",
    "picking": "#22c55e", "wave": "#16a34a", "zone_pick": "#4ade80", "robot": "#8b5cf6",
    "packing": "#f59e0b", "labeling": "#fbbf24", "consolidation": "#eab308",
    "sorting": "#a855f7", "outbound": "#8b5cf6", "shipping": "#8b5cf6", "dispatch": "#a78bfa",
    "safety": "#ef4444", "office": "#94a3b8", "admin": "#94a3b8", "it": "#64748b",
    "maintenance": "#78716c", "staff": "#a8a29e", "circulation": "#facc15", "aisle": "#facc15",
}

# أبعاد أنظمة التخزين القياسية (عمق, طول الخانة, ارتفاع, مستويات, ممر)
RACK_DEF = {
    "pallet": (1.10, 2.70, 8.0, 4, 3.40),
    "shelf":  (0.60, 1.20, 2.40, 5, 1.40),
    "bin":    (0.45, 0.90, 2.10, 6, 1.10),
    "mezz":   (1.20, 3.00, 5.00, 2, 2.50),
    "flow":   (1.20, 1.50, 2.20, 4, 1.60),
    "cage":   (1.00, 1.20, 1.80, 1, 1.20),
}
STA_DEF = {
    "pack":    (1.8, 0.9, 0.9, 2.6, True, True),
    "inspect": (1.6, 0.9, 0.9, 2.4, True, False),
    "label":   (1.2, 0.8, 0.9, 1.8, True, True),
    "qa":      (1.4, 0.9, 0.9, 2.2, True, False),
    "sort":    (2.2, 1.0, 0.85, 3.0, False, False),
    "void":    (1.2, 1.0, 1.3, 2.0, False, False),
    "desk":    (1.5, 0.75, 0.75, 2.0, True, False),
    "charger": (0.7, 0.5, 0.5, 1.2, False, False),
    "locker":  (0.9, 0.5, 1.9, 0.95, False, False),
    "wrap":    (1.6, 1.6, 2.0, 3.0, False, False),
}
LANE_MAT = {"forklift": "paint_lane", "pedestrian": "paint_ped", "amr": "paint_amr",
            "robot": "paint_amr", "one_way": "paint_lane", "zone": "paint_zone",
            "fire": "paint_fire", "safety": "paint_fire"}

def hex_rgb(h):
    """'#22c55e' -> (0.13, 0.77, 0.37) خطّي تقريبي (sRGB مباشرة كـ baseColorFactor)."""
    if not h:
        return None
    h = str(h).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None


def tinted(mat, color):
    """اسم مادة مصبوغة: 'wall@#22c55e' — يُنتج مادة glTF مستقلة لهذه الغرفة وحدها."""
    rgb = hex_rgb(color)
    return "%s@%s" % (mat, str(color).strip().lower()) if rgb else mat


def resolve_mat(name):
    """يفكّ 'base@#hex' إلى قيم المادة الأساسية مع استبدال اللون."""
    base, _, tint = str(name).partition("@")
    r, g, b, a, metal, rough = MAT.get(base, (0.7, 0.7, 0.7, 1.0, 0.0, 0.7))
    rgb = hex_rgb(tint)
    if rgb:
        r, g, b = rgb
    return r, g, b, a, metal, rough


# نوع النقطة -> (طبقة, مادة, ارتفاع افتراضي متر, حجم العلامة)
POINT_KINDS = {
    "outlet":  ("ELEC",   "outlet",  0.40, (0.09, 0.09, 0.03)),
    "switch":  ("ELEC",   "switch",  1.20, (0.09, 0.12, 0.03)),
    "network": ("ELEC",   "network", 0.40, (0.08, 0.08, 0.03)),
    "usb":     ("ELEC",   "usb",     0.55, (0.06, 0.06, 0.03)),
    "tv":      ("ELEC",   "tv",      1.40, (0.9,  0.55, 0.05)),
    "ev":      ("ELEC",   "ev",      0.90, (0.15, 0.25, 0.10)),
    "light":   ("LIGHT",  "light",   None, (0.30, 0.30, 0.06)),  # سقف
    "spot":    ("LIGHT",  "light",   None, (0.12, 0.12, 0.05)),
    "camera":  ("CAMERA", "camera",  None, (0.12, 0.12, 0.12)),  # قرب السقف
    "ac":      ("HVAC",   "ac",      None, (0.8,  0.20, 0.20)),  # فوق النافذة/سقف
    "vent":    ("HVAC",   "ac",      None, (0.30, 0.30, 0.06)),
    "smoke":   ("SAFETY", "safety",  None, (0.14, 0.14, 0.05)),  # سقف
    "sprinkler":("SAFETY","safety",  None, (0.10, 0.10, 0.08)),
    "exit":    ("SAFETY", "safety",  2.10, (0.30, 0.14, 0.05)),
}

# ---------------------------------------------------------------------------
# هندسة صندوق (24 رأس / 6 أوجه) مع نورمال مسطّح
# ---------------------------------------------------------------------------
_UV = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

def box(cx, cy, cz, ex, ey, ez):
    hx, hy, hz = ex/2.0, ey/2.0, ez/2.0
    # 6 أوجه: +X,-X,+Y,-Y,+Z,-Z
    faces = [
        ((hx,-hy,-hz),(hx,hy,-hz),(hx,hy,hz),(hx,-hy,hz),(1,0,0)),
        ((-hx,-hy,hz),(-hx,hy,hz),(-hx,hy,-hz),(-hx,-hy,-hz),(-1,0,0)),
        ((-hx,hy,-hz),(-hx,hy,hz),(hx,hy,hz),(hx,hy,-hz),(0,1,0)),
        ((-hx,-hy,hz),(-hx,-hy,-hz),(hx,-hy,-hz),(hx,-hy,hz),(0,-1,0)),
        ((-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz),(0,0,1)),
        ((hx,-hy,-hz),(-hx,-hy,-hz),(-hx,hy,-hz),(hx,hy,-hz),(0,0,-1)),
    ]
    pos = []; nrm = []; uv = []; idx = []
    for f in faces:
        base = len(pos)
        n = f[4]
        for k, v in enumerate(f[:4]):
            pos.append((v[0]+cx, v[1]+cy, v[2]+cz)); nrm.append(n); uv.append(_UV[k])
        idx += [base, base+1, base+2, base, base+2, base+3]
    return (np.array(pos, np.float32), np.array(nrm, np.float32),
            np.array(uv, np.float32), np.array(idx, np.uint32))


class Builder:
    """يجمّع أجزاء (صناديق) بمواد وأسماء، ثم يصدّرها glTF."""
    def __init__(self):
        self.parts = []   # (pos, nrm, idx, mat_name, node_name)

    def add_box(self, cx, cy, cz, ex, ey, ez, mat, name):
        if ex <= 0 or ey <= 0 or ez <= 0:
            return
        p, n, u, i = box(cx, cy, cz, ex, ey, ez)
        self.parts.append((p, n, u, i, mat, name))

    # ---- تصدير glTF 2.0 (buffer مضمّن base64) ----
    def export_gltf(self, path):
        # مواد فريدة
        mat_names = []
        for part in self.parts:
            m = part[4]
            if m not in mat_names:
                mat_names.append(m)
        materials = []
        for m in mat_names:
            r, g, b, a, metal, rough = resolve_mat(m)
            mat = {
                "name": m,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [r, g, b, a],
                    "metallicFactor": metal, "roughnessFactor": rough,
                },
                "doubleSided": True,
            }
            if a < 1.0:
                mat["alphaMode"] = "BLEND"
            materials.append(mat)
        mat_index = {m: k for k, m in enumerate(mat_names)}

        buf = bytearray()
        bufferViews = []; accessors = []; meshes = []; nodes = []

        def align():
            while len(buf) % 4 != 0:
                buf.append(0)

        for (pos, nrm, uv, idx, mat, name) in self.parts:
            # POSITION
            align(); off = len(buf); data = pos.tobytes(); buf += data
            bufferViews.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": 34962})
            acc_pos = len(accessors)
            accessors.append({"bufferView": len(bufferViews)-1, "componentType": 5126,
                              "count": int(len(pos)), "type": "VEC3",
                              "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
            # NORMAL
            align(); off = len(buf); data = nrm.tobytes(); buf += data
            bufferViews.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": 34962})
            acc_nrm = len(accessors)
            accessors.append({"bufferView": len(bufferViews)-1, "componentType": 5126,
                              "count": int(len(nrm)), "type": "VEC3"})
            # TEXCOORD_0
            align(); off = len(buf); data = uv.tobytes(); buf += data
            bufferViews.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": 34962})
            acc_uv = len(accessors)
            accessors.append({"bufferView": len(bufferViews)-1, "componentType": 5126,
                              "count": int(len(uv)), "type": "VEC2"})
            # INDICES
            align(); off = len(buf); data = idx.tobytes(); buf += data
            bufferViews.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": 34963})
            acc_idx = len(accessors)
            accessors.append({"bufferView": len(bufferViews)-1, "componentType": 5125,
                              "count": int(len(idx)), "type": "SCALAR"})
            meshes.append({"primitives": [{"attributes": {"POSITION": acc_pos, "NORMAL": acc_nrm,
                                                          "TEXCOORD_0": acc_uv},
                                           "indices": acc_idx, "material": mat_index[mat]}]})
            nodes.append({"mesh": len(meshes)-1, "name": name})

        b64 = base64.b64encode(bytes(buf)).decode("ascii")
        gltf = {
            "asset": {"version": "2.0", "generator": "ACS Geometry Compiler 1.0"},
            "scene": 0,
            "scenes": [{"nodes": list(range(len(nodes)))}],
            "nodes": nodes,
            "meshes": meshes,
            "materials": materials,
            "accessors": accessors,
            "bufferViews": bufferViews,
            "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + b64}],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gltf, f)
        return len(nodes), len(buf)


# ---------------------------------------------------------------------------
# بناء الجدران مع فتحات الأبواب/النوافذ
# ---------------------------------------------------------------------------
def wall_with_openings(bld, axis, fixed, u0, u1, y0, H, t, openings, layer, fkey, room, tag,
                       wall_mat="wall"):
    """
    axis='x' جدار يمتد على X عند z=fixed ؛ axis='z' عند x=fixed.
    openings: قائمة (u_center, width, bottom, top)  (u على طول الجدار)
    """
    L = u1 - u0
    segs = sorted([o for o in openings if o[1] > 0], key=lambda o: o[0])
    cursor = u0
    solids = []  # (a, b) فراغات ممتلئة بكامل الارتفاع
    for (uc, w, bottom, top) in segs:
        a = max(u0, uc - w/2.0); b = min(u1, uc + w/2.0)
        if a > cursor:
            solids.append((cursor, a, y0, y0+H))
        # أسفل الفتحة (جلسة نافذة)
        if bottom > 0:
            solids.append((a, b, y0, y0+bottom))
        # أعلى الفتحة (عتب)
        if (y0+top) < (y0+H):
            solids.append((a, b, y0+top, y0+H))
        cursor = max(cursor, b)
    if cursor < u1:
        solids.append((cursor, u1, y0, y0+H))

    for k, (a, b, yb, yt) in enumerate(solids):
        w = b - a; h = yt - yb
        if w <= 0.001 or h <= 0.001:
            continue
        cu = (a+b)/2.0; cy = (yb+yt)/2.0
        if axis == 'x':
            bld.add_box(cu, cy, fixed, w, h, t, wall_mat, "%s|%s|%s|%s_seg%d" % (layer, fkey, room, tag, k))
        else:
            bld.add_box(fixed, cy, cu, t, h, w, wall_mat, "%s|%s|%s|%s_seg%d" % (layer, fkey, room, tag, k))


def edge_geom(edge, rect):
    """يعيد (axis, fixed, u0, u1) لحافة غرفة. rect=[x,z,w,d]."""
    x, z, w, d = rect
    if edge == 'N':  return ('x', z,     x, x+w)
    if edge == 'S':  return ('x', z+d,   x, x+w)
    if edge == 'W':  return ('z', x,     z, z+d)
    if edge == 'E':  return ('z', x+w,   z, z+d)
    return None


def opening_u(edge, rect, offset):
    """يحوّل offset (من الركن) إلى إحداثي u على الحافة."""
    x, z, w, d = rect
    if edge in ('N', 'S'):  return x + offset
    return z + offset


# ---------------------------------------------------------------------------
# عناصر صناعية مضغوطة: سطر JSON واحد -> مئات القطع (مطابق لعارض الويب)
# ---------------------------------------------------------------------------
def build_racks(bld, room, fkey, base_y):
    rx, rz, rw, rd = [float(v) for v in room["rect"]]
    nm = room.get("id", "room")
    for ri, R in enumerate(room.get("racks") or []):
        depth, bay, H, lv, aisle = RACK_DEF.get(R.get("kind"), RACK_DEF["pallet"])
        depth = float(R.get("depth", depth)); bay = float(R.get("bay", bay))
        H = float(R.get("h", H)); lv = max(1, min(int(R.get("levels", lv)), 10))
        aisle = float(R.get("aisle", aisle))
        d_ = "z" if R.get("dir") == "z" else "x"
        bx, bz = rx + float(R.get("x", 0)), rz + float(R.get("z", 0))
        bw = min(float(R.get("w", rw)), rw); bd = min(float(R.get("d", rd)), rd)
        run = bw if d_ == "x" else bd
        across = bd if d_ == "x" else bw
        pitch = depth + aisle
        rows = int(R.get("rows") or max(1, int((across + aisle) / pitch)))
        rows = max(1, min(rows, 40))
        bays = max(1, min(int(run / bay), 60))
        segs = max(1, min(bays, 8)); posts = max(2, min(bays + 1, 6))
        for r in range(rows):
            off = r * pitch + depth / 2.0
            if off - depth / 2.0 > across - 0.05:
                break
            cA = (bz + off) if d_ == "x" else (bx + off)
            c0 = bx if d_ == "x" else bz
            for L in range(lv):
                y = base_y + 0.12 + (H - 0.2) * (L / float(lv))
                if d_ == "x":
                    bld.add_box(c0 + run / 2, y, cA, run, 0.07, depth, "deck",
                                "FURN|%s|%s|rack%dr%dL%d" % (fkey, nm, ri, r, L))
                else:
                    bld.add_box(cA, y, c0 + run / 2, depth, 0.07, run, "deck",
                                "FURN|%s|%s|rack%dr%dL%d" % (fkey, nm, ri, r, L))
                segL = run / segs
                gh = min((H - 0.2) / lv - 0.25, 1.15)
                if gh < 0.2:
                    continue
                for s in range(segs):
                    if (s + r + L) % 4 == 3:
                        continue
                    cu = c0 + segL * (s + 0.5)
                    if d_ == "x":
                        bld.add_box(cu, y + 0.05 + gh / 2, cA, segL * 0.86, gh, depth * 0.86,
                                    "goods", "FURN|%s|%s|goods%dr%dL%ds%d" % (fkey, nm, ri, r, L, s))
                    else:
                        bld.add_box(cA, y + 0.05 + gh / 2, cu, depth * 0.86, gh, segL * 0.86,
                                    "goods", "FURN|%s|%s|goods%dr%dL%ds%d" % (fkey, nm, ri, r, L, s))
            for p in range(posts):
                cu = c0 + run * (p / float(posts - 1 or 1))
                for sgn in (-1, 1):
                    ca = cA + sgn * (depth / 2 - 0.05)
                    if d_ == "x":
                        bld.add_box(cu, base_y + H / 2, ca, 0.10, H, 0.10, "steel",
                                    "FURN|%s|%s|post%dr%dp%d" % (fkey, nm, ri, r, p))
                    else:
                        bld.add_box(ca, base_y + H / 2, cu, 0.10, H, 0.10, "steel",
                                    "FURN|%s|%s|post%dr%dp%d" % (fkey, nm, ri, r, p))
            if d_ == "x":
                bld.add_box(c0 + run / 2, base_y + 0.32, cA, run, 0.10, depth * 1.02, "beam",
                            "FURN|%s|%s|beam%dr%d" % (fkey, nm, ri, r))
            else:
                bld.add_box(cA, base_y + 0.32, c0 + run / 2, depth * 1.02, 0.10, run, "beam",
                            "FURN|%s|%s|beam%dr%d" % (fkey, nm, ri, r))


def build_lanes(bld, room, fkey, base_y):
    rx, rz = float(room["rect"][0]), float(room["rect"][1])
    nm = room.get("id", "room")
    for li, L in enumerate(room.get("lanes") or []):
        kind = L.get("kind", "forklift")
        x = rx + float(L.get("x", 0)); z = rz + float(L.get("z", 0))
        w = float(L.get("w", 2.5)); d = float(L.get("d", 2.5))
        d_ = "z" if L.get("dir") == "z" else "x"
        if kind == "conveyor":
            h = float(L.get("h", 0.85)); run = w if d_ == "x" else d
            bld.add_box(x + w / 2, base_y + h, z + d / 2, w, 0.10, d, "belt",
                        "FURN|%s|%s|conv%d" % (fkey, nm, li))
            for sgn in (-1, 1):
                if d_ == "x":
                    bld.add_box(x + w / 2, base_y + h + 0.16, z + d / 2 + sgn * (d / 2 - 0.03),
                                w, 0.22, 0.06, "guard", "SAFETY|%s|%s|convrail%d" % (fkey, nm, li))
                else:
                    bld.add_box(x + w / 2 + sgn * (w / 2 - 0.03), base_y + h + 0.16, z + d / 2,
                                0.06, 0.22, d, "guard", "SAFETY|%s|%s|convrail%d" % (fkey, nm, li))
            legs = max(2, min(int(run / 2.5), 24))
            for i in range(legs):
                u = run * (i / float(legs - 1 or 1))
                lx = (x + u) if d_ == "x" else (x + w / 2)
                lz = (z + d / 2) if d_ == "x" else (z + u)
                bld.add_box(lx, base_y + h / 2, lz, 0.09, h, 0.09, "frame",
                            "FURN|%s|%s|convleg%d_%d" % (fkey, nm, li, i))
            continue
        bld.add_box(x + w / 2, base_y + 0.008, z + d / 2, w, 0.016, d,
                    tinted(LANE_MAT.get(kind, "paint_lane"), L.get("color")),
                    "SAFETY|%s|%s|lane%d" % (fkey, nm, li))
        if kind in ("pedestrian", "forklift", "one_way"):
            for sgn in (-1, 1):
                if d_ == "x":
                    bld.add_box(x + w / 2, base_y + 0.018, z + d / 2 + sgn * (d / 2 - 0.06),
                                w, 0.012, 0.12, "paint_ped", "SAFETY|%s|%s|lane%dedge" % (fkey, nm, li))
                else:
                    bld.add_box(x + w / 2 + sgn * (w / 2 - 0.06), base_y + 0.018, z + d / 2,
                                0.12, 0.012, d, "paint_ped", "SAFETY|%s|%s|lane%dedge" % (fkey, nm, li))


def build_stations(bld, room, fkey, base_y):
    rx, rz, rw, rd = [float(v) for v in room["rect"]]
    nm = room.get("id", "room")
    for si, S in enumerate(room.get("stations") or []):
        w, d, h, pitch, screen, printer = STA_DEF.get(S.get("kind"), STA_DEF["pack"])
        w = float(S.get("w", w)); d = float(S.get("d", d)); h = float(S.get("h", h))
        pitch = float(S.get("pitch", pitch))
        d_ = "z" if S.get("dir") == "z" else "x"
        n = max(1, min(int(S.get("count", 1)), 60))
        x0 = rx + float(S.get("x", 0.6)); z0 = rz + float(S.get("z", 0.6))
        for i in range(n):
            cx = (x0 + pitch * i + w / 2) if d_ == "x" else (x0 + w / 2)
            cz = (z0 + d / 2) if d_ == "x" else (z0 + pitch * i + d / 2)
            if cx > rx + rw + 0.2 or cz > rz + rd + 0.2:
                break
            bld.add_box(cx, base_y + h - 0.04, cz, w, 0.08, d, "counter",
                        "FURN|%s|%s|st%d_%d" % (fkey, nm, si, i))
            for sx in (-1, 1):
                for sz in (-1, 1):
                    bld.add_box(cx + sx * (w / 2 - 0.08), base_y + h / 2, cz + sz * (d / 2 - 0.08),
                                0.07, h, 0.07, "frame", "FURN|%s|%s|stleg%d_%d" % (fkey, nm, si, i))
            if screen:
                bld.add_box(cx, base_y + h + 0.28, cz - d / 2 + 0.1, 0.52, 0.34, 0.04, "screen",
                            "ELEC|%s|%s|stscr%d_%d" % (fkey, nm, si, i))
            if printer:
                bld.add_box(cx + w / 2 - 0.22, base_y + h + 0.11, cz, 0.3, 0.18, 0.28, "frame",
                            "ELEC|%s|%s|stprn%d_%d" % (fkey, nm, si, i))
            if S.get("kind") == "charger":
                bld.add_box(cx, base_y + 0.1, cz + d / 2 + 0.35, 0.55, 0.2, 0.55, "robot",
                            "FURN|%s|%s|strobot%d_%d" % (fkey, nm, si, i))


def dock_openings(room):
    out = {"N": [], "S": [], "E": [], "W": []}
    for D in (room.get("docks") or []):
        n = max(1, min(int(D.get("count", 1)), 24))
        wd = float(D.get("width", 3.0)); dh = float(D.get("height", 4.0))
        pitch = float(D.get("pitch", wd + 1.8)); e = D.get("edge", "N")
        for i in range(n):
            out[e].append((opening_u(e, room["rect"], float(D.get("offset", 3)) + pitch * i),
                           wd, 0.0, dh))
    return out


def build_docks(bld, room, fkey, base_y):
    rect = room["rect"]; nm = room.get("id", "room")
    for di, D in enumerate(room.get("docks") or []):
        n = max(1, min(int(D.get("count", 1)), 24))
        wd = float(D.get("width", 3.0)); dh = float(D.get("height", 4.0))
        pitch = float(D.get("pitch", wd + 1.8)); e = D.get("edge", "N")
        axis, fixed, _, _ = edge_geom(e, rect)
        outw = -1 if e in ("N", "W") else 1
        for i in range(n):
            uc = opening_u(e, rect, float(D.get("offset", 3)) + pitch * i)
            if axis == "x":
                bld.add_box(uc, base_y + dh / 2, fixed, wd, dh, 0.10, "dockdoor",
                            "DOOR|%s|%s|dock%d_%d" % (fkey, nm, di, i))
                bld.add_box(uc, base_y + 0.06, fixed + outw * 0.9, wd, 0.12, 1.7, "frame",
                            "FLOOR|%s|%s|leveler%d_%d" % (fkey, nm, di, i))
                for s in (-1, 1):
                    bld.add_box(uc + s * (wd / 2 + 0.12), base_y + 0.55, fixed + outw * 0.12,
                                0.22, 0.5, 0.3, "bumper", "SAFETY|%s|%s|bump%d_%d" % (fkey, nm, di, i))
            else:
                bld.add_box(fixed, base_y + dh / 2, uc, 0.10, dh, wd, "dockdoor",
                            "DOOR|%s|%s|dock%d_%d" % (fkey, nm, di, i))
                bld.add_box(fixed + outw * 0.9, base_y + 0.06, uc, 1.7, 0.12, wd, "frame",
                            "FLOOR|%s|%s|leveler%d_%d" % (fkey, nm, di, i))
                for s in (-1, 1):
                    bld.add_box(fixed + outw * 0.12, base_y + 0.55, uc + s * (wd / 2 + 0.12),
                                0.3, 0.5, 0.22, "bumper", "SAFETY|%s|%s|bump%d_%d" % (fkey, nm, di, i))


# ---------------------------------------------------------------------------
# بناء غرفة
# ---------------------------------------------------------------------------
def build_room(bld, room, fkey, base_y, defaults):
    rect = room["rect"]; x, z, w, d = rect
    H = room.get("wall_h", defaults["wall_h"])
    t = defaults["wall_t"]
    name = room.get("id", "room")

    # تجميع الفتحات لكل حافة
    per_edge = {'N': [], 'S': [], 'E': [], 'W': []}
    doors = room.get("doors", [])
    windows = room.get("windows", [])
    for dr in doors:
        e = dr["edge"]; uc = opening_u(e, rect, dr["offset"])
        per_edge[e].append((uc, dr.get("width", 0.9), 0.0, dr.get("height", 2.1)))
    for wn in windows:
        e = wn["edge"]; uc = opening_u(e, rect, wn["offset"])
        sill = wn.get("sill", 0.9); wh = wn.get("height", 1.6)
        per_edge[e].append((uc, wn.get("width", 1.2), sill, sill+wh))

    # فتحات أرصفة التحميل تُحسب ضمن فتحات الجدار
    for e, lst in dock_openings(room).items():
        per_edge[e].extend(lst)

    # تشطيبات خاصة بالغرفة (لون جدار/أرضية/سقف مطلوب من المستخدم)
    zone_col = room.get("wall_color") or ROLE_COLOR.get(str(room.get("role", "")).lower())
    wall_mat = tinted("wall", zone_col)

    # نمط الجدار: مناطق المستودع مفتوحة (دهان أرضي) لا جدران كاملة
    ADMIN_ROLES = ("office", "admin", "it", "staff", "maintenance", "meeting")
    _ind = bool(defaults.get("industrial"))
    walls_mode = room.get("walls") or (
        "none" if (_ind and room.get("role") and room["role"] not in ADMIN_ROLES) else "full")
    WH = {"none": 0.0, "line": 0.0, "low": 1.10, "rail": 1.10, "half": 1.80,
          "glass": H, "full": H}
    hW = WH.get(walls_mode, H)

    if walls_mode in ("none", "line"):
        zc = zone_col or "#2563eb"
        for e in ('N', 'S', 'E', 'W'):
            axis, fixed, u0, u1 = edge_geom(e, rect)
            if axis == 'x':
                bld.add_box((u0 + u1) / 2, base_y + 0.006, fixed, u1 - u0, 0.012, 0.15,
                            tinted("paint_zone", zc), "FLOOR|%s|%s|zone%s" % (fkey, name, e))
            else:
                bld.add_box(fixed, base_y + 0.006, (u0 + u1) / 2, 0.15, 0.012, u1 - u0,
                            tinted("paint_zone", zc), "FLOOR|%s|%s|zone%s" % (fkey, name, e))
        bld.add_box(x + w / 2, base_y + 0.01, z + d / 2, min(w * 0.5, 6), 0.014, min(d * 0.22, 2.2),
                    tinted("paint_zone", zc), "FLOOR|%s|%s|label" % (fkey, name))
    else:
        for e in ('N', 'S', 'E', 'W'):
            axis, fixed, u0, u1 = edge_geom(e, rect)
            wall_with_openings(bld, axis, fixed, u0, u1, base_y, hW, t,
                               per_edge[e], "WALL", fkey, name, "w"+e, wall_mat)

    # لوح أرضية/سقف ملوّن للغرفة (يُبنى فقط عند طلب لون)
    if hex_rgb(room.get("floor_color")):
        bld.add_box(x + w/2.0, base_y + 0.012, z + d/2.0, max(w - t, 0.1), 0.024, max(d - t, 0.1),
                    tinted("floor", room["floor_color"]), "FLOOR|%s|%s|plate" % (fkey, name))
    if hex_rgb(room.get("ceiling_color")):
        bld.add_box(x + w/2.0, base_y + H - 0.03, z + d/2.0, max(w - t, 0.1), 0.05, max(d - t, 0.1),
                    tinted("ceiling", room["ceiling_color"]), "FLOOR|%s|%s|ceil" % (fkey, name))

    # لوح باب/زجاج في كل فتحة باب
    for i, dr in enumerate(doors):
        e = dr["edge"]; uc = opening_u(e, rect, dr["offset"])
        wdt = dr.get("width", 0.9); dh = dr.get("height", 2.1)
        mat = "door_glass" if dr.get("material") == "glass" else "door"
        mat = tinted(mat, dr.get("color"))
        axis, fixed, _, _ = edge_geom(e, rect)
        cy = base_y + dh/2.0
        if axis == 'x':
            bld.add_box(uc, cy, fixed, wdt, dh, 0.05, mat, "DOOR|%s|%s|%d" % (fkey, name, i))
        else:
            bld.add_box(fixed, cy, uc, 0.05, dh, wdt, mat, "DOOR|%s|%s|%d" % (fkey, name, i))

    # زجاج النوافذ
    for i, wn in enumerate(windows):
        e = wn["edge"]; uc = opening_u(e, rect, wn["offset"])
        wdt = wn.get("width", 1.2); sill = wn.get("sill", 0.9); wh = wn.get("height", 1.6)
        axis, fixed, _, _ = edge_geom(e, rect)
        cy = base_y + sill + wh/2.0
        if axis == 'x':
            bld.add_box(uc, cy, fixed, wdt, wh, 0.04, "window", "WINDOW|%s|%s|%d" % (fkey, name, i))
        else:
            bld.add_box(fixed, cy, uc, 0.04, wh, wdt, "window", "WINDOW|%s|%s|%d" % (fkey, name, i))

    # نقاط MEP (أفياش/مفاتيح/إنارة/كاميرات/تكييف/سلامة)
    for j, pt in enumerate(room.get("points", [])):
        kind = pt.get("type", "outlet")
        layer, mat, def_h, size = POINT_KINDS.get(kind, POINT_KINDS["outlet"])
        px = x + pt.get("x", w/2.0); pz = z + pt.get("z", d/2.0)
        if def_h is None:  # سقف/قرب السقف
            if layer in ("LIGHT", "SAFETY", "HVAC") and kind not in ("ac", "exit"):
                py = base_y + H - size[1]/2.0 - 0.02
            elif kind == "camera":
                py = base_y + H - 0.15
            elif kind == "ac":
                py = base_y + H - 0.35
            else:
                py = base_y + H - 0.1
        else:
            py = base_y + pt.get("height", def_h)
        bld.add_box(px, py, pz, size[0], size[1], size[2], mat,
                    "%s|%s|%s|%s%d" % (layer, fkey, name, kind, j))

    # أثاث
    for k, fu in enumerate(room.get("furniture", [])):
        fx = x + fu["x"]; fz = z + fu["z"]
        fw = fu.get("w", 0.8); fd = fu.get("d", 0.8); fh = fu.get("h", 0.8)
        mat = fu.get("mat", "furn")
        bld.add_box(fx, base_y + fh/2.0, fz, fw, fh, fd, mat,
                    "FURN|%s|%s|%s%d" % (fkey, name, fu.get("name", "obj"), k))

    # العناصر الصناعية المضغوطة (رفوف · ممرات وسيور · محطات · أرصفة)
    if room.get("racks"):
        build_racks(bld, room, fkey, base_y)
    if room.get("lanes"):
        build_lanes(bld, room, fkey, base_y)
    if room.get("stations"):
        build_stations(bld, room, fkey, base_y)
    if room.get("docks"):
        build_docks(bld, room, fkey, base_y)


# ---------------------------------------------------------------------------
# بناء دور كامل (لوح أرضية + غرف)
# ---------------------------------------------------------------------------
def build_level(bld, level, floor_def, base_y, defaults, fkey):
    site = defaults["site"]
    # لوح أرضية للدور
    bld.add_box(site["w"]/2.0, base_y - 0.075, site["d"]/2.0,
                site["w"], 0.15, site["d"], "floor", "FLOOR|%s|slab|0" % fkey)
    for room in floor_def.get("rooms", []):
        build_room(bld, room, fkey, base_y, defaults)


def compile_building(data, out_path):
    bld = Builder()
    _bt = str((data.get("meta") or {}).get("type", "residential")).lower()
    defaults = {
        "site": data.get("site", {"w": 30.0, "d": 25.0}),
        "wall_h": data.get("wall_h", 3.0),
        "wall_t": data.get("wall_t", 0.15),
        "industrial": _bt in ("warehouse", "industrial", "factory", "logistics"),
    }
    floors = data.get("floors", {})
    fh = data.get("floor_height", defaults["wall_h"] + 0.2)
    for lvl in data.get("levels", []):
        idx = lvl["index"]
        tmpl = lvl["template"]
        fdef = floors.get(tmpl, {})
        base_y = idx * fh
        fkey = "F%d" % idx
        build_level(bld, lvl, fdef, base_y, defaults, fkey)
    n, size = bld.export_gltf(out_path)
    return n, size


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "acs_building_example.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "ACS-building.gltf"
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    n, size = compile_building(data, out)
    print("[ACS] compiled %d nodes, buffer %.1f KB -> %s" % (n, size/1024.0, out))


if __name__ == "__main__":
    main()
