"""Authoritative supported requirement vocabulary. Source: acs_requirement_metrics.json."""
import json
from pathlib import Path
SPEC=json.loads(Path(__file__).with_name('acs_requirement_metrics.json').read_text(encoding='utf-8'))
METRICS=SPEC['metrics']
def unsupported_metrics(requirements):
    return sorted({str(r.get('metric')) for r in requirements if isinstance(r,dict) and r.get('metric') not in METRICS})
