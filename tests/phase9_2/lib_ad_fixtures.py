# -*- coding: utf-8 -*-
"""تجهيزات المرحلة 9.2 — النماذج والطلبات البصرية (§46 A–L).

النماذج القانونية تأتي من تجهيزات المراحل السابقة نفسها؛ هنا تُضاف حالات
الطلب البصري: حجر وزجاج، بلكونات ممثَّلة وغير ممثَّلة، مواقف غير محسومة،
LED عرضي، مطبخ غامض، طلب واجهة مختلط، ومدخلات عدائية.
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'phase9'))

import lib_docs_fixtures as LIB9                                  # noqa: E402

HOSTILE_TEXT = list(LIB9.HOSTILE_TEXT)


def apartment_model():
    """عمارة سكنية من طابقين ببلكونات ممثَّلة (فراغ بدور balcony + درابزين)."""
    rooms = []
    for i in range(2):
        rooms.append({
            "id": "apt%d" % i, "name": "Apartment %d" % i,
            "rect": [i * 7.0, 0.0, 7.0, 9.0],
            "doors": [{"edge": "S", "offset": 3.5, "width": 1.0}],
            "windows": [{"edge": "N", "offset": 3.0, "width": 1.6,
                         "height": 1.5, "sill": 0.9}],
        })
        rooms.append({
            "id": "bal%d" % i, "name": "Balcony %d" % i,
            "role": "balcony",
            "rect": [i * 7.0 + 1.5, 9.0, 4.0, 1.6],
            "doors": [{"edge": "N", "offset": 2.0, "width": 1.0}],
            "objects": [{"kind": "railing", "x": 2.0, "z": 1.5,
                         "w": 4.0, "d": 0.06, "h": 1.1}],
        })
    tmpl = {"rooms": rooms}
    return {"meta": {"name": "apartment_balconies", "type": "generic"},
            "site": {"w": 34.0, "d": 26.0},
            "floor_height": 3.2, "wall_h": 3.0,
            "levels": [{"index": 0, "name": "ground", "template": "t"},
                       {"index": 1, "name": "first", "template": "t"}],
            "floors": {"t": tmpl}}


def fixtures():
    """الحالات A–L: (النموذج، نص الطلب البصري، ملخّص النموذج للعرض)."""
    m = LIB9.all_models()
    apt = apartment_model()
    return {
        'A_villa_stone': {
            'model': m['villa_glazed'],
            'request': 'واجهة حجر طبيعي بيج مع لمسات رمادية وزجاج عاكس',
            'summary': {'exterior_walls': 4, 'windows': 6, 'accent_band': 0,
                        'balcony': False, 'parking_bays': 0}},
        'B_apartment_balconies': {
            'model': apt,
            'request': 'بلكونات مع إنارة LED مخفية',
            'summary': {'exterior_walls': 6, 'windows': 4, 'accent_band': 0,
                        'balcony': True, 'parking_bays': 0}},
        'C_warehouse': {
            'model': m['warehouse'],
            'request': 'ضع فوركلفت في منطقة الاستلام',
            'summary': {'exterior_walls': 4, 'windows': 0, 'accent_band': 0,
                        'balcony': False, 'parking_bays': 0,
                        'objects': [{'kind': 'forklift', 'requested': True}],
                        'context_enabled': True}},
        'D_clinic': {'model': m['clinic'], 'request': '',
                     'summary': {'exterior_walls': 4, 'windows': 3}},
        'E_hotel': {'model': m['hotel'], 'request': '',
                    'summary': {'exterior_walls': 4, 'windows': 8}},
        'F_office': {'model': m['office'], 'request': '',
                     'summary': {'exterior_walls': 4, 'windows': 5}},
        'G_unresolved_balcony': {
            'model': m['villa'],
            'request': 'أريد بلكونات واسعة',
            'summary': {'exterior_walls': 4, 'windows': 4, 'balcony': False}},
        'H_unresolved_parking': {
            'model': m['office'],
            'request': 'مواقف أمامية وخلفية',
            'summary': {'exterior_walls': 4, 'windows': 5,
                        'parking_bays': 0}},
        'I_led_request': {
            'model': m['villa_glazed'],
            'request': 'إنارة خارجية مخفية LED',
            'summary': {'exterior_walls': 4, 'windows': 6}},
        'J_ambiguous_kitchen': {
            'model': m['villa'],
            'request': 'مطبخ L أو U حسب الدور',
            'summary': {'exterior_walls': 4, 'windows': 4,
                        'kitchen_layout': None}},
        'K_mixed_facade': {
            'model': m['hotel'],
            'request': 'واجهة حجر طبيعي بيج مع كسوة خشب ولمسات رمادية',
            'summary': {'exterior_walls': 4, 'windows': 8,
                        'accent_band': 1}},
        'L_malicious': {
            'model': m['villa'],
            'request': HOSTILE_TEXT[0] if HOSTILE_TEXT else '<script>x</script>',
            'summary': {'exterior_walls': 4, 'windows': 4,
                        'objects': [{'kind': '../../etc/passwd'},
                                    {'kind': '<img src=x onerror=1>'}]}},
    }


def all_models():
    m = LIB9.all_models()
    m['apartment_balconies'] = apartment_model()
    return m


def grid_model(*a, **kw):
    return LIB9.grid_model(*a, **kw)
