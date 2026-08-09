# -*- coding: utf-8 -*-
"""يحقن طبقة العرض البصري ونسختها من المواصفة وواجهة المطوّر وممرّ التقديم في
public/index.html. حقنٌ عديم الأثر عند التكرار: يتخطّى ما هو محقون بالفعل."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IDX = os.path.join(ROOT, 'public', 'index.html')

LAYER_ANCHOR = ('/* ==================================================================\n'
                '   المرحلة 2 — أساس التنسيق بين التخصّصات وكشف التعارضات')
API_ANCHOR = '  /* ---- تنسيق بين التخصّصات: كشف وتتبّع فقط. لا إصلاح ولا إعادة توجيه ---- */'
RENDER_ANCHOR = 'function setSun(elev,azi){const phi=THREE.MathUtils.degToRad(90-elev)'


def _read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def main():
    src = _read(IDX)
    done = []
    if 'ACS_VISUAL_SPEC' not in src:
        sys.path.insert(0, '/tmp')
        raise SystemExit('the visual layer block is missing from index.html; it is part of '
                         'the committed artefact and is not regenerated here')
    if 'window.ACS.visualScene' not in src:
        block = _read(os.path.join(HERE, '_visual_api_block.js'))
        assert src.count(API_ANCHOR) == 1, 'api anchor not unique'
        src = src.replace(API_ANCHOR, block + API_ANCHOR)
        done.append('developer API')
    if 'let VIS_GROUP=null' not in src:
        block = _read(os.path.join(HERE, '_visual_renderer_block.js'))
        assert src.count(RENDER_ANCHOR) == 1, 'renderer anchor not unique'
        src = src.replace(RENDER_ANCHOR, block + RENDER_ANCHOR)
        done.append('presentation renderer pass')
    with open(IDX, 'w', encoding='utf-8') as f:
        f.write(src)
    print('injected:', ', '.join(done) if done else 'nothing (already present)')


if __name__ == '__main__':
    main()
