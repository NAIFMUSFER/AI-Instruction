"""Import deferred roof helpers from only the image's explicit COPY sources."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROBE = '''
import acs_roof
from pathlib import Path
assert Path(acs_roof.__file__).resolve().parent == Path.cwd()
model = {"site":{"w":10,"d":8}, "wall_h":3, "floor_height":3.2,
         "levels":[{"index":0,"template":"ground"}],
         "floors":{"ground":{"rooms":[{"id":"hall","rect":[0,0,10,8]}]}}}
before = repr(model)
roofed, report, reason = acs_roof.with_default_roof(model)
assert reason is None and repr(model) == before
assert len(roofed["levels"]) == 2 and roofed["meta"]["acs_roof"]["source"] == "system_default"
assert report["occupied_floor"] is False and report["deck_area_m2"] == 80
removed = acs_roof.remove_auto_roof(roofed)
assert len(removed["levels"]) == 1 and acs_roof.roof_removed_by_user(removed)
restored = acs_roof.restore_default_roof(removed)
assert len(restored["levels"]) == 2 and not acs_roof.roof_removed_by_user(restored)
print("ROOF RUNTIME PACKAGING: pure synthetic add/remove/restore PASS; no provider call")
'''


def copied_python_sources():
    for line in (ROOT / "Dockerfile").read_text().splitlines():
        words = shlex.split(line, comments=True)
        if not words or words[0] != "COPY":
            continue
        for source in words[1:-1]:
            if source.endswith(".py"):
                yield Path(source), Path(words[-1])


def run_isolated(omit_roof=False):
    with tempfile.TemporaryDirectory(prefix="acs-image-copy-") as tmp:
        target = Path(tmp)
        for source, destination in copied_python_sources():
            if omit_roof and source.name == "acs_roof.py":
                continue
            # Current manifest uses explicit files; emulate each COPY target.
            dest = target / destination
            if destination.suffix != ".py":
                dest /= source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, dest)
        script = "import sys; sys.path.insert(0," + json.dumps(tmp) + ")\n" + PROBE
        return subprocess.run([sys.executable, "-I", "-c", script], cwd=tmp,
                              capture_output=True, text=True, timeout=15)


class RoofRuntimePackagingTests(unittest.TestCase):
    def test_copy_manifest_can_execute_deferred_roof_operations(self):
        result = run_isolated()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ROOF RUNTIME PACKAGING:", result.stdout)

    def test_missing_helper_cannot_be_hidden_by_checkout_imports(self):
        result = run_isolated(omit_roof=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No module named 'acs_roof'", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
