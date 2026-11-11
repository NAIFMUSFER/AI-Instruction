"""The deferred stair policy must be executable from the release COPY set."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_roof_runtime_packaging import ROOT, copied_python_sources


PROBE = '''
import sys
import acs_stairs
from pathlib import Path
assert Path(acs_stairs.__file__).resolve().parent == Path.cwd()
assert callable(acs_stairs.with_default_stairs)
assert not any(name in sys.modules for name in
               ('acs_provider', 'acs_compiler', 'acs_bim', 'requests', 'httpx'))
model = {"site":{"w":8,"d":8}, "wall_h":3, "floor_height":3.2,
         "levels":[{"index":0,"template":"ground","elevation":0}],
         "floors":{"ground":{"rooms":[{"id":"hall","rect":[0,0,8,8]}]}}}
before = repr(model)
candidate, report, reason = acs_stairs.with_default_stairs(model)
assert repr(model) == before
assert reason == "STAIR_NOT_APPLICABLE"
assert report["physical_traversal"] == "NOT_VERIFIED"
assert not any(room.get("objects") for floor in candidate["floors"].values()
               for room in floor["rooms"])
print("STAIRS RUNTIME PACKAGING: isolated policy executes without a provider")
'''


def run_isolated(omit_stairs=False):
    with tempfile.TemporaryDirectory(prefix="acs-stairs-image-") as tmp:
        target = Path(tmp)
        for source, destination in copied_python_sources():
            if omit_stairs and source.name == "acs_stairs.py":
                continue
            dest = target / destination
            if destination.suffix != ".py":
                dest /= source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, dest)
        script = "import sys; sys.path.insert(0," + json.dumps(tmp) + ")\n" + PROBE
        return subprocess.run([sys.executable, "-I", "-c", script], cwd=tmp,
                              capture_output=True, text=True, timeout=15)


class StairRuntimePackagingTests(unittest.TestCase):
    def test_release_copy_set_executes_policy(self):
        result = run_isolated()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("STAIRS RUNTIME PACKAGING:", result.stdout)

    def test_checkout_cannot_hide_an_omitted_helper(self):
        result = run_isolated(omit_stairs=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No module named 'acs_stairs'", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
