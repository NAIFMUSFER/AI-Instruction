# -*- coding: utf-8 -*-
"""أدوات مشتركة لاختبارات المرحلة 4 في بايثون — نظير lib_runtime_fixtures.js."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def load():
    with open(os.path.join(HERE, 'fixtures', 'runtime_scenarios.json'), encoding='utf-8') as f:
        return json.load(f)


def hydrate(v):
    if isinstance(v, list):
        return [hydrate(x) for x in v]
    if isinstance(v, dict):
        return {k: hydrate(x) for k, x in v.items()}
    if v == 'NaN_MARKER':
        return float('nan')
    if v == 'INF_MARKER':
        return float('inf')
    if v == 'NEG_INF_MARKER':
        return float('-inf')
    return v
