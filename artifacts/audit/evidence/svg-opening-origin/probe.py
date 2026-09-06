"""Run at the checkout root with the audit Python environment."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
import acs_arch as A
import acs_docs as D

fixture=json.loads(Path(__file__).with_name('result.json').read_text())
arch=A.compile_architecture(fixture['model'])
opening=arch['openings'][0]
print(json.dumps({'canonical_anchor':A.opening_anchor(arch,opening['id']),
                  'svg_segment':D._opening_plan(opening,arch)},indent=2))
