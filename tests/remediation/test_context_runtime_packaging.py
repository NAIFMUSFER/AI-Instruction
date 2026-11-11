"""Execute the late-imported object policy from only the Docker COPY set."""
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
from pathlib import Path
import acs_context_details
assert Path(acs_context_details.__file__).resolve().parent == Path.cwd()
model = {'site': {'w': 10, 'd': 8}, 'wall_h': 3, 'wall_t': .2, 'floor_height': 3.2,
         'levels': [{'index': 0, 'template': 'ground', 'elevation': 0}],
         'floors': {'ground': {'rooms': [{'id': 'porch', 'rect': [0, 0, 10, 8],
                      'role': 'porch', 'covered': True, 'walls': 'none'}]}}}
before = repr(model)
candidate, report, reason = acs_context_details.with_context_details(model)
assert reason is None, reason
assert repr(model) == before
objects = candidate['floors']['ground']['rooms'][0]['objects']
assert objects and all(o['kind'] == 'column' for o in objects)
assert all(o['context_detail_provenance']['conceptual_only'] is True for o in objects)
assert candidate['meta']['acs_context_details']['source'] == 'system_default'
assert len(acs_context_details.list_context_details(candidate)) == len(objects)
assert not any(name in sys.modules for name in
               ('acs_provider', 'acs_understand', 'acs_compiler', 'acs_bim', 'requests', 'httpx'))
print('CONTEXT RUNTIME PACKAGING: canonical defaults and disclosure execute without a provider')
'''


def run_isolated(omit_helper=False):
    with tempfile.TemporaryDirectory(prefix='acs-context-image-') as tmp:
        for source, destination in copied_python_sources():
            if omit_helper and source.name == 'acs_context_details.py':
                continue
            dest = Path(tmp) / destination
            if destination.suffix != '.py':
                dest /= source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, dest)
        script = 'import sys; sys.path.insert(0,' + json.dumps(tmp) + ')\n' + PROBE
        return subprocess.run([sys.executable, '-I', '-c', script], cwd=tmp,
                              capture_output=True, text=True, timeout=15)


class ContextRuntimePackaging(unittest.TestCase):
    def test_release_copy_set_executes_authoring_and_disclosure(self):
        result = run_isolated()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CONTEXT RUNTIME PACKAGING:', result.stdout)

    def test_checkout_cannot_hide_an_omitted_helper(self):
        result = run_isolated(omit_helper=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No module named 'acs_context_details'", result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
