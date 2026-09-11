"""SVG XML + DXF round-trip evidence. Does not claim native AutoCAD testing."""
import io
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_review import PlanError, PlanWorkspace
import acs_plan_projection as C
from test_plan_review import model, BRIEF, program
import ezdxf  # mandatory for this dedicated suite; do not silently skip it


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.ws = PlanWorkspace()
        self.rev = self.ws.propose(model(), brief=BRIEF, requirements=program(),
                                   expected_head=None, note='projection fixture')

    def test_draft_projection_is_not_approval(self):
        p = C.project(self.rev, 0)
        self.assertEqual(p['scope'], 'SPACE_BOUNDARIES_ONLY')
        self.assertFalse(p['construction_approved'])
        self.assertIn('doors', p['not_projected'])
        self.assertIsNone(self.ws.baseline)

    def test_projection_preserves_source_coordinates(self):
        p = C.project(self.rev, 0)['primitives'][0]
        self.assertEqual(p['rect_xz_m'], [0, 0, 4, 4])
        self.assertEqual(p['cad_polygon_xy_m'], [[0, 0], [4, 0], [4, -4], [0, -4]])
        self.assertEqual(p['space_rect_area_m2'], 16)

    def test_floor_instance_ids_are_distinct_and_stable(self):
        first = C.project(self.rev, 0)['primitives']
        second = C.project(self.rev, 1)['primitives']
        self.assertNotEqual(first[0]['source_id'], second[0]['source_id'])
        self.assertEqual(first, C.project(self.rev, 0)['primitives'])

    def test_svg_contains_actual_dimensions_and_scope(self):
        text = C.to_svg(self.rev, 0)
        svg = ET.fromstring(text)
        self.assertEqual(svg.attrib['role'], 'img')
        self.assertIn('4 × 4 m', text)
        self.assertIn('Not construction documents', text)
        self.assertEqual(len(svg.findall('{*}g')), 2)

    def test_svg_model_text_is_escaped_and_xml_controls_removed(self):
        m = model(); m['floors']['g']['rooms'][0]['name'] = '<script>alert(1)</script>\x00مجلس'
        rev = self.ws.propose(m, brief=BRIEF, requirements=program(), expected_head=self.ws.head, note='label')
        text = C.to_svg(rev, 0)
        root = ET.fromstring(text)
        self.assertFalse(root.findall('.//{*}script'))
        self.assertIn('&lt;script&gt;', text)
        self.assertIn('مجلس', text)
        self.assertNotIn('\x00', text)

    def test_dxf_roundtrip_declares_meters_and_version(self):
        result = C.to_dxf(self.rev, 0)
        doc = ezdxf.read(io.StringIO(result['dxf_text']))
        self.assertEqual(doc.units, 6)
        self.assertEqual(doc.dxfversion, 'AC1024')
        self.assertFalse(doc.audit().has_errors)
        self.assertFalse(result['native_dwg'])
        self.assertFalse(result['autocad_verified'])

    def test_dxf_polygons_match_projection_and_roundtrip_provenance(self):
        result = C.to_dxf(self.rev, 0)
        doc = ezdxf.read(io.StringIO(result['dxf_text']))
        entities = list(doc.modelspace().query('LWPOLYLINE'))
        self.assertEqual(len(entities), 2)
        for entity, primitive in zip(entities, result['manifest']['primitives']):
            self.assertTrue(entity.closed)
            self.assertEqual([list(v) for v in entity.get_points('xy')], primitive['cad_polygon_xy_m'])
            self.assertEqual(entity.get_xdata('ACS_PLAN')[0].value, primitive['source_id'])
            self.assertEqual(entity.get_xdata('ACS_PLAN')[2].value, self.rev.model_hash)

    def test_dxf_labels_preserve_arabic(self):
        m = model(); m['floors']['g']['rooms'][0]['name'] = 'غرفة النوم'
        rev = self.ws.propose(m, brief=BRIEF, requirements=program(), expected_head=self.ws.head, note='label')
        doc = ezdxf.read(io.StringIO(C.to_dxf(rev, 0)['dxf_text']))
        self.assertIn('غرفة النوم', [e.dxf.text for e in doc.modelspace().query('TEXT')])

    def test_unknown_floor_never_falls_back_to_first_floor(self):
        for index in (10, None, '0', True):
            with self.assertRaises(PlanError): C.project(self.rev, index)

    def test_no_export_on_invalid_geometry(self):
        m = model(); m['floors']['g']['rooms'][0]['rect'][0] = 20
        rev = self.ws.propose(m, brief=BRIEF, requirements=program(), expected_head=self.ws.head, note='invalid fixture')
        with self.assertRaises(PlanError): C.to_dxf(rev, 0)
        with self.assertRaises(PlanError): C.to_svg(rev, 0)

    def test_missing_dxf_library_is_reported_not_silent_conversion(self):
        with patch.dict(sys.modules, {'ezdxf': None}):
            with self.assertRaises(PlanError) as got: C.to_dxf(self.rev, 0)
        self.assertEqual(got.exception.code, 'CAD_DEPENDENCY_UNAVAILABLE')

    def test_projection_does_not_modify_source(self):
        before = self.rev.model_json
        C.to_svg(self.rev, 0); C.to_dxf(self.rev, 0)
        self.assertEqual(self.rev.model_json, before)
        self.assertEqual(self.rev.model, model())


if __name__ == '__main__':
    unittest.main(verbosity=2)
