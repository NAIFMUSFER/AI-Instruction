# -*- coding: utf-8 -*-
"""فحص فتحات معلومة الهندسة؛ لا أبعاد افتراضية ولا أحكام كود بناء.

Each broken case has a sound counterpart. --mutations deliberately disables
each changed guard in memory; it never edits the working tree. --evidence
reproduces the dated engineering report's fixture, vocabulary and IFC census.
"""
import copy
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_validate as V


def model(two_rooms=False):
    rooms = [{"id": "room", "rect": [0, 0, 8, 8],
              "doors": [{"edge": "N", "offset": 2, "width": 1, "height": 2.1}]}]
    if two_rooms:
        rooms.append({"id": "neighbour", "rect": [8, 0, 3, 3]})
    return {"meta": {"strict": True}, "site": {"w": 20, "d": 20}, "wall_h": 3,
            "levels": [{"index": 0, "template": "g"}], "floors": {"g": {"rooms": rooms}}}


def room(m):
    return m["floors"]["g"]["rooms"][0]


def window(edge="S", offset=2, sill=0.9, height=1):
    return {"edge": edge, "offset": offset, "width": 1, "sill": sill, "height": height}


def issues(m, marker=None):
    found = V.validate_building(m)[0]
    return found if marker is None else [i for i in found if marker in i]


class OpeningGeometry(unittest.TestCase):
    def test_sound_stated_geometry_is_silent(self):
        m = model()
        room(m)["windows"] = [window()]
        self.assertEqual(issues(m), [])

    def test_invalid_edge_is_reported(self):
        m = model()
        room(m)["doors"][0]["edge"] = "Q"
        self.assertTrue(issues(m, "حافّة غير صالحة"))

    def test_invalid_edges_do_not_create_topology_findings(self):
        m = model(True)
        room(m)["doors"] = [{"edge": "Q", "offset": 2, "width": 1, "height": 2} for _ in range(2)]
        self.assertEqual(len(issues(m, "حافّة غير صالحة")), 2)
        self.assertEqual(issues(m, "متراكبتان"), [])

    def test_nonpositive_width_is_reported(self):
        for value in (0, -1):
            with self.subTest(width=value):
                m = model()
                room(m)["doors"][0]["width"] = value
                self.assertTrue(issues(m, "أبعاد فتحة غير صالحة"))

    def test_nonfinite_opening_does_not_crash_or_pass(self):
        for field in ("offset", "width"):
            for value in (None, "bad", float("nan"), float("inf")):
                with self.subTest(field=field, value=value):
                    m = model(True)
                    room(m)["doors"][0][field] = value
                    self.assertTrue(issues(m, "أبعاد فتحة غير صالحة"))

    def test_invalid_stated_vertical_dimension_is_reported(self):
        for field, value in (("height", 0), ("height", -1), ("height", "bad"),
                             ("height", float("nan")), ("sill", -1),
                             ("sill", float("inf"))):
            with self.subTest(field=field, value=value):
                m = model()
                room(m)["windows"] = [window()]
                room(m)["windows"][0][field] = value
                self.assertTrue(issues(m, "البعد الرأسي"))

    def test_opening_above_stated_wall_is_reported(self):
        for kind, opening in (("windows", window(sill=2.5)),
                              ("doors", {"edge": "N", "offset": 2,
                                         "width": 1, "height": 3.5})):
            with self.subTest(kind=kind):
                m = model()
                room(m)[kind] = [opening]
                self.assertTrue(issues(m, "تتجاوز ارتفاع الجدار"))

    def test_room_wall_height_overrides_building_height(self):
        m = model()
        room(m)["wall_h"] = 4
        room(m)["windows"] = [window(sill=2.5)]
        self.assertEqual(issues(m), [])

    def test_unknown_vertical_dimensions_are_not_invented(self):
        m = model()
        del m["wall_h"]
        room(m)["windows"] = [window(sill=10)]
        self.assertEqual(issues(m), [])
        m = model()
        room(m)["windows"] = [{"edge": "N", "offset": 2, "width": 1}]
        self.assertEqual(issues(m), [])


class OpeningCollisions(unittest.TestCase):
    def test_single_room_collision_is_reported(self):
        m = model()
        room(m)["doors"].append({"edge": "N", "offset": 2.2, "width": 1, "height": 2.1})
        self.assertTrue(issues(m, "متراكبتان"))

    def test_door_window_collision_is_reported(self):
        m = model(True)
        room(m)["windows"] = [window("N")]
        self.assertTrue(issues(m, "متراكبتان"))

    def test_transom_above_door_is_silent(self):
        m = model(True)
        room(m)["windows"] = [window("N", sill=2.2, height=0.6)]
        self.assertEqual(issues(m), [])

    def test_stacked_windows_are_silent(self):
        m = model(True)
        room(m)["windows"] = [window(sill=0.5, height=0.7), window(sill=1.4, height=0.7)]
        self.assertEqual(issues(m), [])

    def test_horizontal_separation_is_silent(self):
        m = model(True)
        room(m)["windows"] = [window("N", offset=4)]
        self.assertEqual(issues(m), [])

    def test_touching_openings_are_silent(self):
        m = model(True)
        room(m)["windows"] = [window("N", offset=3)]
        self.assertEqual(issues(m), [])

    def test_unknown_door_height_cannot_prove_cross_kind_collision(self):
        m = model(True)
        del room(m)["doors"][0]["height"]
        room(m)["windows"] = [window("N")]
        self.assertEqual(issues(m), [])


class WindowExposure(unittest.TestCase):
    def test_partial_edge_neighbour_clear_of_aperture_is_silent(self):
        m = model(True)
        room(m)["windows"] = [window("E", offset=6)]
        self.assertEqual(issues(m), [])

    def test_aperture_overlapping_neighbour_is_reported(self):
        m = model(True)
        room(m)["windows"] = [window("E", offset=2)]
        self.assertTrue(issues(m, "جدار داخلي"))

    def test_north_aperture_clear_of_partial_neighbour_is_silent(self):
        m = model(True)
        room(m)["rect"] = [0, 3, 8, 8]
        m["floors"]["g"]["rooms"][1]["rect"] = [0, 0, 3, 3]
        room(m)["windows"] = [window("N", offset=6)]
        self.assertEqual(issues(m), [])


class Boundary(unittest.TestCase):
    def test_deterministic_nonmutating_arabic_geometry_issues(self):
        m = model(True)
        room(m)["windows"] = [window("N")]
        before = copy.deepcopy(m)
        first = issues(m)
        self.assertTrue(first)
        self.assertEqual(first, issues(m))
        self.assertEqual(m, before)
        for forbidden in ("SBC", "IBC", "NFPA", "الكود", "compliant", "معتمد"):
            self.assertNotIn(forbidden, " ".join(first))


def evidence():
    import acs_authoring as A
    import acs_bim as B
    import acs_generation as G
    import acs_programs as P
    from test_validate_against_real_models import scan
    models = json.loads((ROOT / "tests/phase3/fixtures/base_fixtures.json").read_text())
    models.update(json.loads((ROOT / "tests/phase7/fixtures/render_fixtures.json").read_text()))
    print("CORPUS", scan())
    for name in ("villa_glazed", "hotel_glazed", "office", "clinic_glazed", "warehouse_glazed"):
        m = models[name]
        result = B.export_ifc(A.create_project(m, "bld_0", source="TEST", actor_id="audit"),
                              generated_at="2026-09-26T00:00:00Z")
        text = result["file"]
        row = {"model": name, "validator_issues": V.validate_building(m)[0],
               "template_rooms": sum(len(f["rooms"]) for f in m["floors"].values()),
               "ifc_valid": result["valid"], "schema_ifc4": "FILE_SCHEMA(('IFC4'))" in text,
               "metres": bool(re.search(r"IFCSIUNIT\(\*,\.LENGTHUNIT\.,\$,\.METRE\.\)", text)),
               "elevations": [l["elevation"] for l in result["exchange"]["levels"]],
               "space_names": [s["name"] for s in result["exchange"]["spaces"]],
               "entities": {k: len(re.findall("=" + k + r"\(", text)) for k in
                            ("IFCSPACE", "IFCWALLSTANDARDCASE", "IFCDOOR", "IFCWINDOW")},
               "unsupported": result["manifest"]["unsupported_count"],
               "losses": result["manifest"]["losses"],
               "manual_geometry": {t: [{k: r[k] for k in ("id", "rect", "role", "doors", "windows", "objects")
                                        if k in r} for r in f["rooms"]] for t, f in m["floors"].items()}}
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    for word in ("مجلس", "مقلط", "ملحق", "فناء", "منور", "سطح", "قبو", "مستودع", "بدروم"):
        print("VOCAB", word, sorted(G._synonym_hits(word)), P.detect_type(word))


def compare_baseline(ref):
    from test_validate_against_real_models import _walk
    baseline = types.ModuleType("acs_validate_baseline")
    source = subprocess.check_output(["git", "show", ref + ":acs_validate.py"],
                                     cwd=ROOT, text=True)
    exec(compile(source, "baseline/acs_validate.py", "exec"), baseline.__dict__)
    count, changed, mutated, unstable = 0, [], [], []
    for path in sorted((ROOT / "tests").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, ValueError):
            continue
        for location, m in _walk(data):
            count += 1
            before = copy.deepcopy(m)
            old, now = baseline.validate_building(m), V.validate_building(m)
            label = str(path.relative_to(ROOT)) + " :: " + location
            if old != now:
                changed.append(label)
            if m != before:
                mutated.append(label)
            if now != V.validate_building(m):
                unstable.append(label)
    print(json.dumps({"models": count, "changed_results": changed, "mutated": mutated,
                      "nondeterministic": unstable}, ensure_ascii=False))
    if count == 0 or changed or mutated or unstable:
        raise AssertionError("baseline corpus contract changed")


def mutations():
    """كل تغيير حارس يُكسَر منفرداً ويجب أن تُسقِطه حالة المعطوب أو السليم."""
    global V
    source = (ROOT / "acs_validate.py").read_text(encoding="utf-8")
    cases = [
        ("invalid edge", 'if e not in ("N", "S", "E", "W"):', 'if False:'),
        ("invalid edge excluded from topology", 'if edge not in ("N", "S", "E", "W"):', 'if False:'),
        ("positive width", 'or float(width) <= 0:', 'or False:'),
        ("finite plan dimensions", 'if not _finite(offset) or not _finite(width) or float(width) <= 0:',
         'if False:'),
        ("stated vertical dimensions", 'if field in o and (', 'if False and ('),
        ("unknown or invalid vertical interval", 'if not _finite(h) or not _finite(sill) or float(h) <= 0 or float(sill) < 0:',
         'if False:'),
        ("stated wall height", 'if vertical is not None and _finite(wall_h) and vertical[1] > float(wall_h) + GEOM_TOL:',
         'if False:'),
        ("room wall override", 'wall_h = r.get("wall_h") if r.get("wall_h") is not None else b.get("wall_h")',
         'wall_h = b.get("wall_h")'),
        ("single room", 'if not entries:', 'if len(entries) < 2:'),
        ("door and window shared span ledger", '            spans = {}\n            for kind in ("doors", "windows"):',
         '            for kind in ("doors", "windows"):\n                spans = {}'),
        ("vertical separation", 'return a[0] < b[1] - GEOM_TOL and b[0] < a[1] - GEOM_TOL',
         'return True'),
        ("unknown cross-kind elevation", 'return same_kind', 'return True'),
        ("aperture-specific neighbour", 'if opening_span is not None:', 'if False:'),
        ("horizontal separation", 'if (lo < phi - GEOM_TOL and plo < hi - GEOM_TOL', 'if (True'),
    ]
    original = V
    survived = []
    for name, old, new in cases:
        if source.count(old) != 1:
            raise AssertionError("mutation anchor must be unique: " + name)
        mutant = types.ModuleType("acs_validate_mutant")
        exec(compile(source.replace(old, new, 1), str(ROOT / "acs_validate.py"), "exec"), mutant.__dict__)
        V = mutant
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)
                                   for c in (OpeningGeometry, OpeningCollisions, WindowExposure, Boundary))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        killed = not result.wasSuccessful()
        print(("KILLED" if killed else "SURVIVED") + " " + name)
        if not killed:
            survived.append(name)
    V = original
    if survived:
        raise AssertionError("unguarded mutations: " + ", ".join(survived))
    print("MUTATIONS", len(cases), "killed", len(cases) - len(survived), "survived", len(survived))


if __name__ == "__main__":
    if "--evidence" in sys.argv:
        evidence()
    elif "--mutations" in sys.argv:
        mutations()
    elif "--compare-baseline" in sys.argv:
        compare_baseline(sys.argv[sys.argv.index("--compare-baseline") + 1])
    else:
        unittest.main(verbosity=2)
