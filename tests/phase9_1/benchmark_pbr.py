# -*- coding: utf-8 -*-
"""قياس أداء طبقة الجودة البصرية — مُجمِّع الإعداد العرضي وحده.

كل رقم هنا هو مللي ثانية عمل معالج في هذا الصندوق على هذا التشغيل بالذات.
لا إطار في الثانية، ولا بطاقة رسوميات، ولا WebGL، ولا رسم فعلي يُقاس أو
يُدَّعى هنا: زمن الرسم الحقيقي لا يوجد إلا في متصفح على النشر الحقيقي،
وهو NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED في هذا الصندوق (§26).
"""
import copy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'phase9'))

import acs_pbr as P                                               # noqa: E402
import acs_docs as D                                              # noqa: E402
import acs_authoring as AU                                        # noqa: E402
import lib_docs_fixtures as LIB                                   # noqa: E402

OUT = os.path.join(HERE, 'outputs')
os.makedirs(OUT, exist_ok=True)

CAPS = {'webgl2': True, 'max_texture_size': 16384, 'device_pixel_ratio': 2}
OVR = {'plaster': {'roughness': 0.4},
       'glass_clear': {'transmission': 0.9}}


def _t(fn):
    t0 = time.perf_counter()
    r = fn()
    return r, (time.perf_counter() - t0) * 1000.0


def _bounds(src):
    """حدود تقريبية من فراغات النموذج الحقيقية — لقياس الأداء فقط."""
    xs, ys = [], []
    for s in src['arch']['spaces']:
        r = s.get('rect') or [0, 0, 5, 4]
        xs += [r[0], r[0] + r[2]]
        ys += [r[1], r[1] + r[3]]
    if not xs:
        return {'cx': 0, 'cy': 3, 'cz': 0, 'radius': 20, 'min_y': 0}
    w, d = max(xs) - min(xs), max(ys) - min(ys)
    return {'cx': (min(xs) + max(xs)) / 2.0, 'cy': 3.0,
            'cz': (min(ys) + max(ys)) / 2.0,
            'radius': max(10.0, ((w * w + d * d) ** 0.5) / 2.0), 'min_y': 0}


def measure(name, model):
    prj = AU.create_project(copy.deepcopy(model), 'bld_0', 'IMPORT', None)
    before = D._canon(prj['model'])
    h0 = prj['model_hash']
    src = D.sources(prj)
    b = _bounds(src)

    _, ms_mat = _t(lambda: [P.material(m) for m in P.MATERIALS])
    _, ms_ovr = _t(lambda: [P.material(m, OVR.get(m)) for m in P.MATERIALS])
    _, ms_lgt = _t(lambda: [P.lighting(k) for k in P.LIGHTING])
    _, ms_shd = _t(lambda: [P.shadow_config(t, b) for t in P.SHADOWS])
    _, ms_qlt = _t(lambda: [P.quality(q, CAPS) for q in P.QUALITY])
    _, ms_cam = _t(lambda: [P.camera(c, b) for c in P.CAMERAS])
    cfgs, ms_cfg = _t(lambda: [
        P.config(q, lp, 'REALISTIC', 'SKY', 1.1, OVR, CAPS, b)
        for q in P.QUALITY for lp in P.LIGHTING])
    cfg = cfgs[0]['config']
    _, ms_cap = _t(lambda: [P.capture_metadata(cfg, h0, 1920, 1080, None)
                            for _ in range(32)])
    _, ms_tex = _t(lambda: [P.texture_path_ok(pth) for pth in
                            (['assets/materials/a.png'] * 50
                             + ['https://cdn.example/x.png'] * 50)])
    _, ms_ver = _t(lambda: D.verify_no_mutation(before, prj))
    ok = D.verify_no_mutation(before, prj)
    assert ok['unchanged'] is True and prj['model_hash'] == h0
    return {'model': name,
            'spaces': len(src['arch']['spaces']),
            'walls': len(src['arch']['walls']),
            'configs_built': len(cfgs),
            'bounds_radius_m': round(b['radius'], 2),
            'model_unchanged': True,
            'ms': {'materials_20': round(ms_mat, 2),
                   'materials_20_with_overrides': round(ms_ovr, 2),
                   'lighting_8': round(ms_lgt, 2),
                   'shadow_4_tiers': round(ms_shd, 2),
                   'quality_4_profiles': round(ms_qlt, 2),
                   'cameras_8': round(ms_cam, 2),
                   'full_config_32': round(ms_cfg, 2),
                   'capture_metadata_32': round(ms_cap, 2),
                   'texture_path_checks_100': round(ms_tex, 2),
                   'immutability_verify': round(ms_ver, 2)}}


def main():
    models = LIB.all_models()
    rows = []
    for k in ('villa', 'villa_glazed', 'hotel', 'clinic', 'warehouse',
              'office', 'clash_mep'):
        rows.append(measure(k, models[k]))
    for n in (100, 500, 1000):
        rows.append(measure('grid_%d' % n, LIB.grid_model(n)))
    hdr = ('%-16s %7s %7s %8s %8s %8s %8s %8s %8s'
           % ('model', 'spaces', 'cfgs', 'mats', 'shadow', 'quality',
              'cams', 'cfg32', 'verify'))
    print('\n== VISUAL QUALITY LAYER BENCHMARK '
          '(CPU, deterministic; no FPS, no GPU, no WebGL) ==')
    print(hdr)
    print('-' * len(hdr))
    for r in rows:
        m = r['ms']
        print('%-16s %7d %7d %7.2fm %7.2fm %7.2fm %7.2fm %7.2fm %7.2fm'
              % (r['model'], r['spaces'], r['configs_built'],
                 m['materials_20'], m['shadow_4_tiers'],
                 m['quality_4_profiles'], m['cameras_8'],
                 m['full_config_32'], m['immutability_verify']))
    print('\nevery timing is milliseconds of CPU work in this sandbox on this '
          'run. The presentation compiler touches configuration only; the '
          'canonical model bytes were re-verified identical after every row. '
          'Frame rate on real hardware is NOT VERIFIED — EXTERNAL ENVIRONMENT '
          'REQUIRED: it is not measured, estimated or claimed here.')
    with open(os.path.join(OUT, 'benchmark_pbr.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'note': 'CPU ms in sandbox; no FPS or GPU measurement '
                           'exists in this environment',
                   'fps_claimed': False, 'rows': rows}, fh,
                  ensure_ascii=False, indent=1)
    print('\nwritten: tests/phase9_1/outputs/benchmark_pbr.json')


if __name__ == '__main__':
    main()
