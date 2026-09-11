"""Traceable SPACE-BOUNDARY projections of a canonical ACS plan revision.

SVG/DXF share the same primitive list. These are not complete working drawings:
no wall thickness offset, opening geometry, structural grids, or MEP is invented.
DXF requires optional ezdxf; native AutoCAD/DWG compatibility is not certified.
"""
from __future__ import annotations
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from acs_plan_review import Revision, PlanError, _geometry, canonical

SCOPE = 'SPACE_BOUNDARIES_ONLY'


def _text(value):
    # XML 1.0 printable scalar values; never render model text as markup.
    return ''.join(ch for ch in str(value) if ord(ch) in (9, 10, 13)
                   or 0x20 <= ord(ch) <= 0xD7FF or 0xE000 <= ord(ch) <= 0xFFFD
                   or 0x10000 <= ord(ch) <= 0x10FFFF)


def project(revision: Revision, level_index: int) -> dict:
    if type(level_index) is not int:
        raise PlanError('INVALID_LEVEL', 'An explicit integer level index is required')
    model = revision.model
    issues, _ = _geometry(model)
    if issues:
        raise PlanError('INVALID_GEOMETRY', 'Resolve geometry issues before CAD export')
    level = next((v for v in model['levels'] if v['index'] == level_index), None)
    if level is None:
        raise PlanError('LEVEL_NOT_FOUND', 'Requested level is absent')
    primitives = []
    for room in model['floors'][level['template']]['rooms']:
        source = {'level_index': level_index, 'template': level['template'], 'room_id': room['id']}
        sid = 'space_' + hashlib.sha256(canonical(source).encode('utf-8')).hexdigest()
        x, z, w, d = room['rect']
        primitives.append({'source_id': sid, 'source': source,
            'rect_xz_m': list(room['rect']),
            # CAD Y points north; ACS Z increases south. Inverse is z=-y.
            'cad_polygon_xy_m': [[x, -z], [x + w, -z], [x + w, -(z + d)], [x, -(z + d)]],
            'label': _text(room.get('name') or room['id']),
            'space_rect_area_m2': w * d})
    return {'scope': SCOPE, 'units': 'm', 'revision_id': revision.id,
            'model_hash': revision.model_hash, 'level_index': level_index,
            'site': model['site'], 'primitives': primitives,
            'not_projected': ['wall_thickness', 'doors', 'windows', 'structural_grid', 'MEP'],
            'construction_approved': False}


def to_svg(revision: Revision, level_index: int) -> str:
    p = project(revision, level_index)
    width, depth = p['site']['w'], p['site']['d']
    margin = max(width, depth) * .06
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg',
        'viewBox': f'{-margin} {-margin * 2} {width + 2 * margin} {depth + 3 * margin}',
        'role': 'img', 'aria-labelledby': 'plan-title plan-description'})
    ET.SubElement(root, 'title', {'id': 'plan-title'}).text = f'ACS plan V{revision.number} — level {level_index}'
    ET.SubElement(root, 'desc', {'id': 'plan-description'}).text = (
        'Schematic space boundaries in metres. Not construction documents. '
        'Doors, windows, wall thickness and structural information are not drawn.')
    ET.SubElement(root, 'metadata').text = json.dumps({k: v for k, v in p.items() if k != 'primitives'}, ensure_ascii=False)
    ET.SubElement(root, 'rect', {'x': '0', 'y': '0', 'width': str(width), 'height': str(depth),
                  'fill': 'white', 'stroke': '#697586', 'stroke-width': str(margin * .025)})
    for item in p['primitives']:
        x, z, w, d = item['rect_xz_m']
        g = ET.SubElement(root, 'g', {'data-source-id': item['source_id']})
        ET.SubElement(g, 'title').text = item['label']
        ET.SubElement(g, 'rect', {'x': str(x), 'y': str(z), 'width': str(w), 'height': str(d),
            'fill': 'none', 'stroke': '#14263b', 'stroke-width': str(margin * .04)})
        label = ET.SubElement(g, 'text', {'x': str(x + w / 2), 'y': str(z + d / 2),
            'text-anchor': 'middle', 'font-size': str(min(w, d) * .1)})
        label.text = item['label']
        ET.SubElement(g, 'text', {'x': str(x + w / 2), 'y': str(z + d / 2 + min(w, d) * .16),
            'text-anchor': 'middle', 'font-size': str(min(w, d) * .075)}).text = f'{w:g} × {d:g} m'
    return ET.tostring(root, encoding='unicode')


def to_dxf(revision: Revision, level_index: int) -> dict:
    p = project(revision, level_index)
    try:
        import ezdxf
    except ImportError as exc:
        raise PlanError('CAD_DEPENDENCY_UNAVAILABLE', 'DXF export needs optional ezdxf') from exc
    doc = ezdxf.new('R2010', units=6)
    doc.layers.new('ACS_SPACE_BOUNDARIES')
    doc.layers.new('ACS_SPACE_LABELS')
    doc.layers.new('ACS_REVIEW_NOTES')
    doc.appids.new('ACS_PLAN')
    space = doc.modelspace()
    for item in p['primitives']:
        entity = space.add_lwpolyline(item['cad_polygon_xy_m'], close=True,
                                     dxfattribs={'layer': 'ACS_SPACE_BOUNDARIES'})
        entity.set_xdata('ACS_PLAN', [(1000, item['source_id']), (1000, p['revision_id']),
                                     (1000, p['model_hash'])])
        x, z, w, d = item['rect_xz_m']
        space.add_text(item['label'].replace('\n', ' ').replace('\r', ' '),
            dxfattribs={'insert': (x + .1 * w, -(z + .5 * d)), 'height': min(w, d) * .1,
                        'layer': 'ACS_SPACE_LABELS'})
    space.add_text('SCHEMATIC SPACE BOUNDARIES - NOT FOR CONSTRUCTION - UNITS: METRES',
                   dxfattribs={'insert': (0, 1), 'height': .2, 'layer': 'ACS_REVIEW_NOTES'})
    if doc.audit().has_errors:
        raise PlanError('CAD_EXPORT_INVALID', 'DXF audit failed; no file returned')
    output = io.StringIO()
    doc.write(output)
    return {'dxf_text': output.getvalue(), 'manifest': p,
            'native_dwg': False, 'autocad_verified': False}
