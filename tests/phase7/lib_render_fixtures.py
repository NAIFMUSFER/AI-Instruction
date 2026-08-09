# -*- coding: utf-8 -*-
"""أدوات مشتركة لاختبارات المرحلة 7 في بايثون."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def base():
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'base_fixtures.json'), encoding='utf-8') as f:
        return json.load(f)


def render():
    with open(os.path.join(HERE, 'fixtures', 'render_fixtures.json'),
              encoding='utf-8') as f:
        return json.load(f)


def all_models():
    o = {}
    o.update(base())
    o.update(render())
    return o
