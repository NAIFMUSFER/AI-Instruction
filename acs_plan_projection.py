"""Traceable projections and 2D drawings of a canonical ACS plan revision.

``project`` returns the provenance-bound SPACE_BOUNDARIES_ONLY primitive list
(room rectangles at wall centre lines). ``to_svg``/``to_dxf`` draw a plan sheet
from it plus the drafting layer in :mod:`acs_plan_drafting`: walls at the
canonical thickness, doors, windows, stairs, dimension chains, room tags, north
arrow, scale bar and title block. Every drawn fact comes from the canonical
model; door swing side/hand are disclosed drafting defaults. Structural grids,
columns and MEP are not drawn and nothing is invented. These are not working
drawings. DXF requires optional ezdxf; native AutoCAD/DWG opening and Arabic
display inside AutoCAD are not certified.

The provenance map is deliberately requirement-aware but never guesses links.
An entity is connected to a Program-of-Requirements item only through an explicit
``requirement_ids`` array stored on that canonical entity. Missing links remain
empty; unknown/malformed links fail closed at projection/handoff time. Canonical
nested elements with a stable explicit ``id`` still receive a plan provenance
identity even when no requirement link exists, so downstream 3D/export receipts
can preserve plan identity without fabricating requirement evidence.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
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
    brief = getattr(revision, 'brief', None)
    if not isinstance(brief, str):
        raise PlanError('INVALID_PROVENANCE', 'Revision brief is unavailable')
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
        if 'source_span' in row:
            span = row['source_span']
            valid_span = (
                isinstance(span, dict)
                and set(span) == {'start', 'end'}
                and type(span.get('start')) is int
                and type(span.get('end')) is int
                and 0 <= span['start'] < span['end'] <= len(brief)
            )
            if not valid_span:
                raise PlanError('INVALID_PROVENANCE', 'Requirement source_span is malformed')
            evidence = row.get('evidence')
            if not isinstance(evidence, str) or brief[span['start']:span['end']] != evidence:
                raise PlanError('INVALID_PROVENANCE', 'Requirement source_span no longer matches its brief evidence')
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
        ref = {
            'requirement_id': rid,
            'source': req['source'],
            # External source/document identity is preserved when supplied. It
            # is never fabricated from free text or from a standard registry.
            'source_id': req.get('source_id'),
        }
        if 'source_span' in req:
            ref['source_span'] = dict(req['source_span'])
        out.append(ref)
    return out


def _source_id(identity: dict) -> str:
    return 'plan_' + hashlib.sha256(canonical(identity).encode('utf-8')).hexdigest()


def provenance_map(revision: Revision) -> dict:
    """Return deterministic plan→requirement provenance without inference.

    Space instances are always listed so CAD/3D can retain a stable identity.
    Nested elements are listed whenever they carry a stable explicit canonical
    ``id``. Their requirement refs remain empty unless explicit ``requirement_ids``
    prove a link. Unidentified presentation-only nested elements are not promoted
    into engineering identities; a linked nested element without a stable id fails
    closed rather than receiving an invented identity. Duplicate explicit nested
    identities also fail closed; array position is never used to disambiguate them.
    """
    model = revision.model
    requirements, requirement_index = _requirements(revision)
    entries = []
    seen_element_identities = set()
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
                    refs = _requirement_refs(item, requirement_index)
                    item_id = item.get('id')
                    if not _stable_id(item_id):
                        if refs:
                            raise PlanError('AMBIGUOUS_PROVENANCE_TARGET',
                                            'Linked nested element requires a stable explicit id')
                        continue
                    identity = {'kind': 'element', 'level_index': level['index'],
                                'template': template, 'room_id': room['id'],
                                'collection': collection, 'element_id': item_id}
                    identity_key = canonical(identity)
                    if identity_key in seen_element_identities:
                        raise PlanError('AMBIGUOUS_PROVENANCE_TARGET',
                                        'Duplicate nested canonical element identity')
                    seen_element_identities.add(identity_key)
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
    # This projector is also the read-only 2D review surface. Warehouse drafts
    # may defer only unresolved floor/wall vertical values; horizontal geometry
    # still fails closed. Approved CAD remains protected by workspace.handoff().
    from warehouse_vertical_stage_gate import draft_geometry_admission
    admission = draft_geometry_admission(model, issues)
    if admission['blocking']:
        raise PlanError('INVALID_GEOMETRY', 'Resolve blocking geometry issues before 2D projection')
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
    from acs_roof import roof_disclosure
    return {'scope': SCOPE, 'units': 'm', 'revision_id': revision.id,
            'model_hash': revision.model_hash, 'level_index': level_index,
            'level_kind': level.get('kind'), 'level_auto': level.get('auto') is True,
            'roof_disclosure': roof_disclosure(model, level),
            'site': model['site'], 'primitives': primitives,
            'provenance_schema': provenance['schema'],
            'requirements_hash': provenance['requirements_hash'],
            'provenance_hash': provenance['provenance_hash'],
            'source_map': provenance['entries'],
            'not_projected': ['wall_thickness', 'doors', 'windows', 'structural_grid', 'MEP'],
            'construction_approved': False}


SVG_FONT = "'Noto Naskh Arabic','Noto Sans Arabic','DejaVu Sans','Segoe UI',Tahoma,Arial,sans-serif"


def _drafting(revision: Revision, level_index: int, p: dict):
    import acs_plan_drafting as D
    model = revision.model
    sheet = D.sheet_for(model)
    paper = D.Paper(sheet)
    draft = D.level_drafting(model, level_index, p['primitives'], p['source_map'])
    level = next(v for v in model['levels'] if v['index'] == level_index)
    title_en = ('Roof deck, unoccupied - Level %d' % level_index if level.get('kind') == 'roof'
                else 'Level %d floor plan' % level_index)
    # Same sheet number as this level's page in the PDF set (A-101, A-102, ...).
    page = ([v['index'] for v in model['levels']].index(level_index) + 1, len(model['levels']))
    return D, sheet, paper, draft, title_en, page


def _is_rtl(text: str) -> bool:
    return any(0x0590 <= ord(ch) <= 0x08FF or 0xFB1D <= ord(ch) <= 0xFEFC for ch in text)


def _mm(value: float) -> str:
    out = ('%.3f' % value).rstrip('0').rstrip('.')
    return '0' if out in ('-0', '') else out


class _SvgPen:
    """Batches line work per layer into one path per layer (compact, CAD-like SVG)."""

    def __init__(self, parent, place):
        self.parent, self.place, self.paths = parent, place, {}

    def _d(self, layer):
        return self.paths.setdefault(layer, [])

    def line(self, layer, a, b):
        (x1, y1), (x2, y2) = self.place(a), self.place(b)
        self._d(layer).append('M%s %sL%s %s' % (_mm(x1), _mm(y1), _mm(x2), _mm(y2)))

    def loops(self, layer, loops):
        for loop in loops:
            pts = [self.place(pt) for pt in loop]
            self._d(layer).append('M' + 'L'.join('%s %s' % (_mm(x), _mm(y)) for x, y in pts) + 'Z')

    def arc(self, layer, c, r, start, end, k):
        (cx, cy), (x1, y1), (x2, y2) = self.place(c), self.place(start), self.place(end)
        sweep = 1 if (x1 - cx) * (y2 - cy) - (y1 - cy) * (x2 - cx) > 0 else 0
        self._d(layer).append('M%s %sA%s %s 0 0 %d %s %s' % (_mm(x1), _mm(y1), _mm(r * k), _mm(r * k), sweep, _mm(x2), _mm(y2)))

    def flush(self):
        for layer, parts in self.paths.items():
            ET.SubElement(self.parent, 'path', {'class': layer, 'd': ''.join(parts)})
        self.paths = {}


def _svg_text(parent, op, place):
    x, y = place(op['at'])
    anchor = op['anchor']
    import acs_drafting_standards as STD
    attrs = {'x': _mm(x), 'y': _mm(y), 'font-size': _mm(STD.font_size_mm(op['size'])),
             'class': 'txt halo' if op.get('halo') else 'txt',
             'data-layer': op['layer']}
    if _is_rtl(op['text']):
        attrs['direction'] = 'rtl'
        anchor = {'start': 'end', 'end': 'start'}.get(anchor, anchor)
    attrs['text-anchor'] = anchor
    if op.get('rotate'):
        attrs['transform'] = 'rotate(%s %s %s)' % (_mm(-op['rotate']), _mm(x), _mm(y))
    ET.SubElement(parent, 'text', attrs).text = _text(op['text'])


def _svg_style() -> str:
    import acs_drafting_standards as STD
    rules = ['text{font-family:%s;fill:#111;stroke:none}' % SVG_FONT,
             '.halo{paint-order:stroke;stroke:#fff;stroke-width:0.6px;stroke-linejoin:round}',
             '.sheet{fill:#fff;stroke:none}', '.room-hit{fill:#fff;fill-opacity:0;stroke:none}']
    for name, spec in STD.LAYERS.items():
        css = 'fill:none;stroke:%s;stroke-width:%s;stroke-linecap:round;stroke-linejoin:round' % (spec['svg'], spec['lw'])
        dash = STD.LINETYPE_MM[spec['lt']]
        if dash:
            css += ';stroke-dasharray:%s' % ' '.join(_mm(v if v else 0.2) for v in dash)
        rules.append('.%s{%s}' % (name, css))
    rules.append('.A-WALL-PATT{fill:%s;stroke:none}' % STD.LAYERS['A-WALL-PATT']['svg'])
    rules.append('.A-ANNO-TTLB.frame{stroke-width:0.7}')
    return '\n'.join(rules)


def render_svg(revision: Revision, level_index: int) -> dict:
    """Plan sheet SVG (1 user unit = 1 mm on paper) plus its drafting summary."""
    p = project(revision, level_index)
    D, sheet, paper, draft, title_en, page = _drafting(revision, level_index, p)
    pw, ph = sheet['paper_mm']
    k = paper.k
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg',
        'width': '%smm' % _mm(pw), 'height': '%smm' % _mm(ph), 'viewBox': '0 0 %s %s' % (_mm(pw), _mm(ph)),
        'role': 'img', 'aria-labelledby': 'plan-title plan-description',
        'data-acs-drafting': D.SCHEMA, 'data-acs-drafting-hash': draft['drafting_hash'],
        'data-acs-scale': '1:%d' % sheet['scale'], 'data-acs-paper': sheet['paper']})
    ET.SubElement(root, 'title', {'id': 'plan-title'}).text = f'ACS plan V{revision.number} — level {level_index}'
    ET.SubElement(root, 'desc', {'id': 'plan-description'}).text = (
        'Concept floor plan at 1:%d on %s (1 SVG unit = 1 mm on paper). Walls at the canonical thickness, '
        'doors, windows, stairs, dimension chains in metres and room areas in m2 are drawn from the '
        'canonical model; door swing side and hinge side are drafting defaults. Not construction documents. '
        'Structural grid, columns and MEP are not drawn.' % (sheet['scale'], sheet['paper']))
    ET.SubElement(root, 'metadata').text = json.dumps({k2: v for k2, v in p.items() if k2 != 'primitives'}, ensure_ascii=False)
    ET.SubElement(root, 'style').text = _svg_style()
    ET.SubElement(root, 'rect', {'class': 'sheet', 'x': '0', 'y': '0', 'width': _mm(pw), 'height': _mm(ph)})
    place_model = paper.to_paper

    def place_paper(pt):
        return pt[0], pt[1]

    x0, y0 = place_model((0.0, 0.0))
    ET.SubElement(root, 'rect', {'class': 'C-PROP', 'x': _mm(x0), 'y': _mm(y0),
                                 'width': _mm(p['site']['w'] * k), 'height': _mm(p['site']['d'] * k)})
    ops = D.plan_ops(draft, paper)
    pen = _SvgPen(root, place_model)
    for op in ops['areas']:
        pen.line(op['layer'], op['a'], op['b'])
    pen.flush()
    for op in ops['fills']:
        path = ''.join('M' + 'L'.join('%s %s' % tuple(_mm(v) for v in place_model(pt)) for pt in loop) + 'Z'
                       for loop in op['loops'])
        ET.SubElement(root, 'path', {'class': op['layer'], 'd': path, 'fill-rule': 'evenodd'})
    for op in ops['lines']:
        if op['op'] == 'line':
            pen.line(op['layer'], op['a'], op['b'])
        elif op['op'] == 'loops':
            pen.loops(op['layer'], op['loops'])
        elif op['op'] == 'arc':
            pen.arc(op['layer'], op['c'], op['r'], op['from'], op['to'], k)
    pen.flush()
    dim_texts = []
    for op in ops['dims']:
        for part in D.expand_dim(op, paper):
            if part['op'] == 'line':
                pen.line(part['layer'], part['a'], part['b'])
            else:
                dim_texts.append(part)
    pen.flush()
    _svg_shapes(root, ops['symbols'], place_model, k)
    for op in dim_texts + ops['texts']:
        _svg_text(root, op, place_model)
    for op in ops['rooms']:
        x, z, w, d = op['rect']
        rx, ry = place_model((x, z))
        g = ET.SubElement(root, 'g', {'data-source-id': op['source_id'], 'data-room-number': op['number']})
        ET.SubElement(g, 'title').text = op['label']
        ET.SubElement(g, 'desc').text = _text(op['desc'])
        ET.SubElement(g, 'rect', {'class': 'room-hit', 'x': _mm(rx), 'y': _mm(ry), 'width': _mm(w * k), 'height': _mm(d * k)})
        for text in op['texts']:
            _svg_text(g, text, place_model)
    sheet_ops = D.sheet_ops(draft, sheet, paper, model=revision.model, page_number=page[0], page_count=page[1],
                            title_en=title_en, revision_id=revision.id, model_hash=revision.model_hash,
                            provenance_hash=p['provenance_hash'], schedule=True)
    pen = _SvgPen(root, place_paper)
    for op in sheet_ops:
        if op['op'] == 'line':
            pen.line(op['layer'], op['a'], op['b'])
    pen.flush()
    _svg_shapes(root, [op for op in sheet_ops if op['op'] in ('poly', 'circle')], place_paper, 1.0)
    for op in sheet_ops:
        if op['op'] == 'text':
            _svg_text(root, op, place_paper)
    return {'svg_text': ET.tostring(root, encoding='unicode'), 'drafting': D.summary(draft, sheet)}


def _svg_shapes(root, ops, place, k):
    for op in ops:
        if op['op'] == 'circle':
            cx, cy = place(op['c'])
            ET.SubElement(root, 'circle', {'class': op['layer'], 'cx': _mm(cx), 'cy': _mm(cy), 'r': _mm(op['r'] * k),
                                           'style': 'fill:#111' if op.get('fill') else 'fill:none'})
        elif op['op'] == 'poly':
            pts = ' '.join('%s,%s' % tuple(_mm(v) for v in place(pt)) for pt in op['pts'])
            cls = op['layer'] + (' frame' if op.get('weight') else '')
            ET.SubElement(root, 'polygon', {'class': cls, 'points': pts,
                                            'style': 'fill:#111' if op.get('fill') else 'fill:#fff' if op['layer'] == 'A-ANNO-SYMB' else 'fill:none'})


def to_svg(revision: Revision, level_index: int) -> str:
    return render_svg(revision, level_index)['svg_text']


def _dxf_setup(doc, sheet):
    import acs_drafting_standards as STD
    scale = sheet['scale']
    factor = scale / 1000.0
    for name, pattern in STD.LINETYPE_MM.items():
        if pattern and name not in doc.linetypes:
            elements = [(v if i % 2 == 0 else -v) * factor for i, v in enumerate(pattern)]
            doc.linetypes.add(name, [sum(abs(v) for v in elements)] + elements,
                              description='ACS %s at 1:%d' % (name.lower(), scale))
    for name, spec in STD.LAYERS.items():
        layer = doc.layers.add(name, color=spec['aci'], linetype=spec['lt'] if spec['lt'] != 'CONTINUOUS' else 'Continuous',
                               lineweight=int(round(spec['lw'] * 100)))
        layer.description = spec['desc']
        if spec.get('plot') is False:
            layer.dxf.plot = 0
    doc.styles.add('ACS-ARABIC', font='arial.ttf')
    doc.dimstyles.add('ACS-ARCH', dxfattribs={
        'dimscale': float(scale), 'dimtxt': 0.0025, 'dimtsz': 0.0012, 'dimexe': 0.002, 'dimexo': 0.002,
        'dimdle': 0.0015, 'dimgap': 0.001, 'dimdec': 2, 'dimzin': 0, 'dimtad': 1, 'dimtih': 0, 'dimtoh': 0,
        'dimlunit': 2, 'dimdsep': ord('.'), 'dimtxsty': 'ACS-ARABIC', 'dimclrd': 0, 'dimclre': 0, 'dimclrt': 0})
    header = doc.header
    header['$INSUNITS'] = 6
    header['$MEASUREMENT'] = 1
    header['$LUNITS'] = 2
    header['$LUPREC'] = 3
    header['$LWDISPLAY'] = 1
    header['$LTSCALE'] = 1.0
    header['$DIMSCALE'] = float(scale)
    header['$TEXTSTYLE'] = 'ACS-ARABIC'
    header['$DIMSTYLE'] = 'ACS-ARCH'


def _dxf_entities(space, ops, to_cad, scale):
    from ezdxf.enums import TextEntityAlignment
    align = {'start': TextEntityAlignment.LEFT, 'middle': TextEntityAlignment.CENTER, 'end': TextEntityAlignment.RIGHT}
    for op in ops:
        attribs = {'layer': op['layer']}
        kind = op['op']
        made = []
        if kind == 'line':
            made.append(space.add_line(to_cad(op['a']), to_cad(op['b']), dxfattribs=attribs))
        elif kind == 'loops':
            for loop in op['loops']:
                pts = [to_cad(pt) for pt in loop]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    space.add_line(a, b, dxfattribs=attribs)
        elif kind == 'fill':
            hatch = space.add_hatch(dxfattribs=attribs)
            hatch.set_solid_fill(color=256)
            for loop in op['loops']:
                hatch.paths.add_polyline_path([to_cad(pt) for pt in loop], is_closed=True)
        elif kind == 'arc':
            c, a, b = to_cad(op['c']), to_cad(op['from']), to_cad(op['to'])
            start = math.degrees(math.atan2(a[1] - c[1], a[0] - c[0]))
            end = math.degrees(math.atan2(b[1] - c[1], b[0] - c[0]))
            if ((end - start + 540.0) % 360.0) - 180.0 < 0:
                start, end = end, start
            radius = math.hypot(a[0] - c[0], a[1] - c[1])
            made.append(space.add_arc(c, radius, start % 360.0, end % 360.0, dxfattribs=attribs))
        elif kind == 'circle':
            c = to_cad(op['c'])
            r = op['r'] * op.get('_k', 1.0)
            space.add_circle(c, r, dxfattribs=attribs)
            if op.get('fill'):
                hatch = space.add_hatch(dxfattribs=attribs)
                hatch.set_solid_fill(color=256)
                hatch.paths.add_edge_path().add_arc(c, r, 0, 360)
        elif kind == 'poly':
            pts = [to_cad(pt) for pt in op['pts']]
            if op.get('fill'):
                hatch = space.add_hatch(dxfattribs=attribs)
                hatch.set_solid_fill(color=256)
                hatch.paths.add_polyline_path(pts, is_closed=True)
            for a, b in zip(pts, pts[1:] + pts[:1]):
                space.add_line(a, b, dxfattribs=attribs)
        elif kind == 'text':
            text = space.add_text(op['text'].replace('\n', ' ').replace('\r', ' '), height=op['size'] * scale / 1000.0,
                                  rotation=op.get('rotate') or 0.0, dxfattribs=dict(attribs, style='ACS-ARABIC'))
            text.set_placement(to_cad(op['at']), align=align[op['anchor']])
        for entity in made:
            ids = op.get('source_ids') or []
            if ids:
                entity.set_xdata('ACS_PLAN', [(1000, source_id) for source_id in ids[:8]])


def to_dxf(revision: Revision, level_index: int) -> dict:
    p = project(revision, level_index)
    try:
        import ezdxf
    except ImportError as exc:
        raise PlanError('CAD_DEPENDENCY_UNAVAILABLE', 'DXF export needs optional ezdxf') from exc
    D, sheet, paper, draft, title_en, page = _drafting(revision, level_index, p)
    scale = sheet['scale']
    doc = ezdxf.new('R2010', units=6)
    _dxf_setup(doc, sheet)
    doc.appids.new('ACS_PLAN')
    space = doc.modelspace()

    def model_to_cad(pt):
        return (pt[0], -pt[1])

    def paper_to_cad(pt):
        return model_to_cad(paper.to_model(pt))

    # Canonical space boundaries first, in projection order, with provenance XDATA.
    for item in p['primitives']:
        entity = space.add_lwpolyline(item['cad_polygon_xy_m'], close=True, dxfattribs={'layer': 'A-AREA'})
        entity.set_xdata('ACS_PLAN', [(1000, item['source_id']), (1000, p['revision_id']),
                                     (1000, p['model_hash']), (1000, p['requirements_hash'])])
    site = p['site']
    corners = [(0.0, 0.0), (site['w'], 0.0), (site['w'], site['d']), (0.0, site['d'])]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        space.add_line(model_to_cad(a), model_to_cad(b), dxfattribs={'layer': 'C-PROP'})
    ops = D.plan_ops(draft, paper)
    for phase in ('areas', 'fills', 'lines'):
        _dxf_entities(space, ops[phase], model_to_cad, scale)
    for op in ops['symbols']:
        _dxf_entities(space, [op], model_to_cad, scale)
    _dxf_entities(space, ops['texts'], model_to_cad, scale)
    for op in ops['rooms']:
        _dxf_entities(space, op['texts'], model_to_cad, scale)
    for op in ops['dims']:
        a, b = op['a'], op['b']
        if op['axis'] == 'x':
            p1, p2, base, angle = (a, -op['face']), (b, -op['face']), (a, -op['line']), 0
        else:
            p1, p2, base, angle = (op['face'], -a), (op['face'], -b), (op['line'], -a), 90
        space.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle='ACS-ARCH',
                             dxfattribs={'layer': 'A-ANNO-DIMS'}).render()
    sheet_ops = D.sheet_ops(draft, sheet, paper, model=revision.model, page_number=page[0], page_count=page[1],
                            title_en=title_en, revision_id=revision.id, model_hash=revision.model_hash,
                            provenance_hash=p['provenance_hash'], schedule=False)
    for op in sheet_ops:
        if op['op'] == 'circle':
            op = dict(op, _k=1.0 / paper.k)
        _dxf_entities(space, [op], paper_to_cad, scale)
    from ezdxf import zoom
    # Open on the whole sheet (CAD viewers start from the active viewport).
    zoom.window(space, paper_to_cad((0.0, sheet['paper_mm'][1])), paper_to_cad((sheet['paper_mm'][0], 0.0)))
    if doc.audit().has_errors:
        raise PlanError('CAD_EXPORT_INVALID', 'DXF audit failed; no file returned')
    output = io.StringIO()
    doc.write(output)
    return {'dxf_text': output.getvalue(), 'manifest': p, 'drafting': D.summary(draft, sheet),
            'native_dwg': False, 'autocad_verified': False}
