# -*- coding: utf-8 -*-
"""أدوات مشتركة لاختبارات المرحلة 6 في بايثون."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def models():
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'base_fixtures.json'), encoding='utf-8') as f:
        return json.load(f)


def mep():
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'mep_fixtures.json'), encoding='utf-8') as f:
        return json.load(f)['models']
