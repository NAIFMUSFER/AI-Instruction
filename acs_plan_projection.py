"""Traceable SPACE-BOUNDARY projections of a canonical ACS plan revision.

SVG/DXF share the same primitive list. These are not complete working drawings:
no wall thickness offset, opening geometry, structural grids, or MEP is invented.
DXF requires optional ezdxf; native AutoCAD/DWG compatibility is not certified.

The provenance map is deliberately requirement-aware but never guesses links.
An entity is connected to a Program-of-Requirements item only through an explicit
``requirement_ids`` array stored on that canonical entity.  Missing links remain
empty; unknown/malformed links fail closed at projection/handoff time.
"""
from __future__ import annotations
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from acs_plan_review import Revision, PlanError, _geometry, canonical, digest

SCOPE = 'SPACE_BOUNDARIES_ONLY'
PROVENANCE_SCHEMA = 'acs.plan-provenance/1.0'
_LINKED_ELEMENT_COLLECTIONS = (
    'racks', 'docks', 'lanes', 'stations', 'doors', 'windows',
    'objects', 'points', 'furniture',
)


def _text(value):
    # XML 1.0 printable scalar values; never render model text as markup.
    return ''.join(ch for ch in str(value) if ord(ch) in (9, 10, 13)
                   or 0x20 <= ord(ch) <= 0xD7FF or 0xE000 <= ord(ch) <= 0xFFFD
                   or 0x10000 <= ord(ch) <= 0x10FFFF)


def _stable_id(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 160


def _requirements(revision: Revision) -> tuple[list[dict], dict[str, dict]]:
    try:
        rows = json.loads(revision.requirements_json)
    except (AttributeError, json.JSONDecodeError) as exc:
        raise PlanError('INVALID_PROVENANCE', 'Revision requirements are unavailable') from exc
    if not isinstance(rows, list):
        raise PlanError('INVALID_PROVENANCE', 'Revision requirements must be an array')
    index = {}
    for row in rows:
        rid = row.get('id') if isinstance(row, dict) else None
        if not _stable_id(rid) or rid in index:
            raise PlanError('INVALID_PROVENANCE', 'Requirement identities must be unique and stable')
        source = row.get('source')
        if source not in ('requested', 'inferred', 'unknown'):
            raise PlanError('INVALID_PROVENANCE', 'Requirement provenance source is invalid')
        external_source = row.get('source_id')
        if external_source is not None and not _stable_id(external_source):
            raise PlanError('INVALID_PROVENANCE', 'Requirement source_id must be a bounded stable string')
        index[rid] = row
    return rows, index


def _requirement_refs(entity: dict, requirement_index: dict[str, dict]) -> list[dict]:
    raw = entity.get('requirement_ids')
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PlanError('INVALID_PROVENANCE_LINK', 'requirement_ids must be an explicit array')
    if any(not _stable_id(rid) for rid in raw) or len(set(raw)) != len(raw):
        raise PlanError('INVALID_PROVENANCE_LINK', 'Requirement links must be unique stable ids')
    out = []
    for rid in raw:
        req = requirement_index.get(rid)
        if req is None:
            raise PlanError('INVALID_PROVENANCE_LINK', 'Canonical entity references an unknown requirement')
        out.append({
            'requirement_id': rid,
            'source': req['source'],
            # External source/document identity is preserved when supplied.  It
            # is never fabricated from free text or from a standard registry.
            'source_id': req.get('source_id'),
        })
    return out


def _source_id(identity: dict) -> str:
    return 'plan_' + hashlib.sha256(canonical(identity).encode('utf-8')).hexdigest()


def provenance_map(revision: Revision) -> dict:
    """Return deterministic plan→requirement provenance without inference.

    Space instances are always listed so CAD/3D can retain a stable identity.
    Nested elements are listed only when they carry explicit ``requirement_ids``;
    this avoids pretending that an unlinked rack, dock, door, or other object was
    requested by any particular requirement.
    """
    model = revision.model
    requirements, requirement_index = _requirements(revision)
    entries = []
    levels = model.get('levels')
    floors = model.get('floors')
    if not isinstance(levels, list) or not isinstance(floors, dict):
        raise PlanError('INVALID_PROVENANCE', 'Canonical level/floor identity is unavailable')
    for level in levels:
        if (not isinstance(level, dict) or type(level.get('index')) is not int
                or not _stable_id(level.get('template'))):
            raise PlanError('INVALID_PROVENANCE', 'Canonical level identity is malformed')
        template = level['template']
        floor = floors.get(template)
        rooms = floor.get('rooms') if isinstance(floor, dict) else None
        if not isinstance(rooms, list):
            raise PlanError('INVALID_PROVENANCE', 'Canonical level template has no rooms array')
        for room in rooms:
            if not isinstance(room, dict) or not _stable_id(room.get('id')):
                raise PlanError('INVALID_PROVENANCE', 'Canonical room identity is malformed')
            base = {'kind': 'space', 'level_index': level['index'],
                    'template': template, 'room_id': room['id']}
            entries.append({
                'source_id': _source_id(base),
                'source': base,
                'requirement_refs': _requirement_refs(room, requirement_index),
            })
            for collection in _LINKED_ELEMENT_COLLECTIONS:
                items = room.get(collection)
                if items is None:
                    continue
                if not isinstance(items, list):
                    raise PlanError('INVALID_PROVENANCE', 'Canonical nested element collection is malformed')
                for item in items:
                    if not isinstance(item, dict):
                        raise PlanError('INVALID_PROVENANCE', 'Canonical nested element is malformed')
                    if item.get('requirement_ids') is None:
                        continue
                    refs = _requirement_refs(item, requirement_index)
                    if not refs:
                        continue
                    if not _stable_id(item.get('id')):
                        raise PlanError('AMBIGUOUS_PROVENANCE_TARGET',
                                        'Linked nested element requires a stable explicit id')
                    identity = {'kind': 'element', 'level_index': level['index'],
                                'template': template, 'room_id': room['id'],
                                'collection': collection, 'element_id': item['id']}
                    entries.append({'source_id': _source_id(identity), 'source': identity,
                                    'requirement_refs': refs})
    payload = {
        'schema': PROVENANCE_SCHEMA,
        'revision_id': revision.id,
        'model_hash': revision.model_hash,
        'requirements_hash': digest(requirements),
        'entries': entries,
    }
    payload['provenance_hash'] = digest(payload)
    return json.loads(canonical(payload))


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
    provenance = provenance_map(revision)
    space_sources = {
        (e['source']['level_index'], e['source']['template'], e['source']['room_id']): e
        for e in provenance['entries'] if e['source']['kind'] == 'space'
    }
    primitives = []
    for room in model['floors'][level['template']]['rooms']:
        key = (level_index, level['template'], room['id'])
        source_record = space_sources.get(key)
        if source_record is None:
            raise PlanError('PROVENANCE_MISMATCH', 'Projected space is missing its canonical provenance identity')
        x, z, w, d = room['rect']
        primitives.append({'source_id': source_record['source_id'],
            'source': source_record['source'],
            'requirement_refs': source_record['requirement_refs'],
            'rect_xz_m': list(room['rect']),
            # CAD Y points north; ACS Z increases south. Inverse is z=-y.
            'cad_polygon_xy_m': [[x, -z], [x + w, -z], [x + w, -(z + d)], [x, -(z + d)]],
            'label': _text(room.get('name') or room['id']),
            'space_rect_area_m2': w * d})
    return {'scope': SCOPE, 'units': 'm', 'revision_id': revision.id,
            'model_hash': revision.model_hash, 'level_index': level_index,
            'site': model['site'], 'primitives': primitives,
            'provenance_schema': provenance['schema'],
            'requirements_hash': provenance['requirements_hash'],
            'provenance_hash': provenance['provenance_hash'],
            'source_map': provenance['entries'],
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
                                     (1000, p['model_hash']), (1000, p['requirements_hash'])])
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
