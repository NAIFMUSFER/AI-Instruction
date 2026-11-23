#!/usr/bin/env python3
"""Inventory every tracked path without overstating semantic review coverage."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/delivery/2026-11-10'
GENERATORS = {
    'bim.js': ['tools/build_bim_browser.py', 'acs_bim.py'],
    'docs.js': ['tools/build_docs_browser.py', 'acs_docs.py'],
    'runtime.js': ['tools/build_runtime_browser.py', 'acs_runtime.py'],
    'pbr.js': ['tools/build_pbr_browser.py', 'acs_pbr.py'],
    'pbr-bridge.js': ['tools/build_pbr_browser.py', 'tools/_pbr_bridge_block.js'],
    'arch-detail.js': ['tools/build_archdetail_browser.py', 'acs_archdetail.py'],
    'arch-detail-bridge.js': ['tools/build_archdetail_browser.py', 'tools/_archdetail_bridge_block.js'],
    'render-engine.js': ['tools/build_render_browser.py', 'acs_render.py'],
    'authoring.js': ['tools/build_authoring_browser.py', 'acs_authoring.py'],
    'requirement-metrics.mjs': ['tools/build_requirement_metrics.py', 'acs_requirement_metrics.json'],
}


def classify(path):
    if '/vendor/' in path or path.startswith('assets/fonts/'):
        return 'vendor'
    if path.startswith('tests/'):
        return 'test-artifact' if '/outputs/' in path else 'test'
    if '/generated/' in path:
        return 'generated'
    if path.endswith(('.md', '.csv', '.log')) or path.startswith('docs/'):
        return 'document'
    if path.startswith('.github/') or path.endswith(('.yml', '.yaml', '.toml', '.lock')):
        return 'configuration'
    if path.endswith(('.py', '.js', '.mjs', '.cjs', '.sh', '.css', '.html', '.sql')):
        return 'source'
    return 'data'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    reviews = {}
    for report in sorted(OUT.glob('coverage-*.json')):
        if report.name == 'coverage-summary.json':
            continue
        data = json.loads(report.read_text())
        if isinstance(data, dict):
            data = data.get('files', data.get('coverage', []))
        for row in data:
            if isinstance(row, dict) and 'path' in row:
                reviews[row['path']] = dict(row, owner=report.stem.removeprefix('coverage-'))
    rows = []
    for path in sorted(filter(None, files)):
        file = ROOT / path
        if not file.is_file():
            continue
        raw = file.read_bytes()
        semantic = reviews.get(path, {})
        depth = semantic.get('depth', 'unreviewed')
        static = []
        if path.endswith('.py'):
            try:
                tree = ast.parse(raw.decode('utf-8-sig'))
                static.append('Python AST parse: pass')
                purpose = (ast.get_docstring(tree) or '').split('\n')[0]
            except (SyntaxError, UnicodeError):
                static.append('Python AST parse: fail')
                purpose = ''
        else:
            purpose = ''
        if path.endswith('.json'):
            try:
                json.loads(raw)
                static.append('JSON parse: pass')
            except (ValueError, UnicodeError):
                static.append('JSON parse: fail')
        if depth == 'unreviewed' and static:
            depth = 'static'
        kind = classify(path)
        rows.append({
            'path': path,
            'purpose': semantic.get('purpose') or purpose or f'{kind} inventory only; purpose not semantically established',
            'owner': semantic.get('owner', 'integration-inventory'),
            'classification': kind,
            'inspection_depth': depth,
            'risk': semantic.get('risk', 'not assessed'),
            'finding_ids': ';'.join(semantic.get('findings', [])),
            'relevant_tests': ';'.join(semantic.get('tests', [])),
            'generated_from': ';'.join(semantic.get('generated_from', []) or (GENERATORS.get(file.name, []) if '/generated/' in path else [])),
            'static_checks': ';'.join(static),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw),
        })
    target = OUT / 'file-coverage.csv'
    # Self and aggregate metadata are included with no circular content hash.
    for row in rows:
        if row['path'] in {str(target.relative_to(ROOT)), str((OUT/'coverage-summary.json').relative_to(ROOT))}:
            row['sha256'] = 'self-referential inventory; not content-hashed'
            row['bytes'] = ''
    with target.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        'schema': 'acs.delivery.coverage/1',
        'base_commit': 'c37b5250dc4ff18ba0606add993b5afe52beebaa',
        'tracked_files': len(rows),
        'depth': dict(Counter(row['inspection_depth'] for row in rows)),
        'classification': dict(Counter(row['classification'] for row in rows)),
        'scope': 'Current delivery review only. Previous dated audit coverage is not silently promoted to current deep review.',
        'warning': 'Inventory and parsing do not establish semantic correctness. Unreviewed and static paths remain explicitly identified.',
    }
    (OUT/'coverage-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
