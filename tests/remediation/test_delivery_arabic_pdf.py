"""Independent PDF parser + Poppler extraction checks on synthetic labels."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(os.environ.get('ACS_AUDIT_ROOT', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests/remediation'))
from test_plan_pdf_export import approved_workspace, residential_model
from tools.acs_plan_pdf_export import export_approved_pdf, verify_pdf_export
from pypdf import PdfReader


class ArabicPdf(unittest.TestCase):
    def test_legacy_sheet_embeds_arabic_without_question_marks(self):
        import acs_docs
        sheets = [{'sheet_id': 'synthetic-sheet', 'paper_mm': [210, 297],
                   'viewports': [{'view_id': 'v', 'x': 10, 'y': 10, 'width': 100, 'height': 100}],
                   'title_block': {'sheet_title': 'مخطط عربي'}}]
        drawings = {'v': {'paper_mm': [100, 100], 'ops': [
            {'op': 'rect', 'x': 5, 'y': 5, 'w': 50, 'h': 30},
            {'op': 'text', 'text': 'مجلس الضيوف A-12', 'x': 10, 'y': 20, 'size': 3}]}}
        raw = acs_docs.sheet_pdf(sheets, drawings)['pdf']
        reader = PdfReader(io.BytesIO(raw))
        text = reader.pages[0].extract_text()
        self.assertIn('مجلس الضيوف', text)
        self.assertIn('مخطط عربي', text)
        self.assertIn('/F2', reader.pages[0]['/Resources']['/Font'])
        from pypdf.generic import ContentStream
        fill = [0, 0, 0]
        for args, operator in ContentStream(reader.pages[0].get_contents(), reader).operations:
            if operator == b'rg':
                fill = [float(v) for v in args]
            if operator in (b'Tj', b'TJ'):
                self.assertNotEqual(fill, [1, 1, 1], 'text must be visible on the white sheet')

    def test_unsupported_glyph_is_explicit_and_writes_no_artifact(self):
        from acs_plan_review import PlanError
        model = residential_model()
        model['floors']['ground']['rooms'][0]['name'] = 'غرفة 🦄'
        ws, rev = approved_workspace(model)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'unsupported.pdf'
            with self.assertRaises(PlanError) as got:
                export_approved_pdf(ws, rev.id, path)
            self.assertEqual(got.exception.code, 'PDF_TEXT_UNSUPPORTED')
            self.assertFalse(path.exists())

    def test_embedded_arabic_logical_text_and_unchanged_model(self):
        model = residential_model()
        model['floors']['ground']['rooms'][0]['name'] = 'مجلس الضيوف A-12'
        model['floors']['upper']['rooms'][0]['name'] = 'غرفة نوم ٢'
        ws, rev = approved_workspace(model)
        before = copy.deepcopy(ws.get(rev.id).revision.model)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'arabic.pdf'
            receipt = export_approved_pdf(ws, rev.id, path)
            reader = PdfReader(path)
            self.assertEqual(len(reader.pages), 2)
            font = reader.pages[0]['/Resources']['/Font']['/F2'].get_object()
            self.assertEqual(font['/Subtype'], '/Type0')
            self.assertTrue(font['/ToUnicode'].get_data())
            desc = font['/DescendantFonts'][0].get_object()['/FontDescriptor']
            self.assertGreater(len(desc['/FontFile2'].get_data()), 1000)
            content = reader.pages[0].get_contents().get_data()
            self.assertIn(('\ufeffمجلس الضيوف A-12').encode('utf-16-be').hex().upper().encode(), content)
            self.assertNotIn(b'(????', content)
            parsed_text = '\n'.join(page.extract_text() for page in reader.pages)
            for text in ('مجلس الضيوف', 'A-12', 'غرفة نوم', '٢'):
                self.assertIn(text, parsed_text)
            self.assertEqual(ws.get(rev.id).revision.model, before)
            self.assertEqual(receipt['model_hash'], rev.model_hash)
            self.assertTrue(verify_pdf_export(path)['ok'])
            if not shutil.which('pdftotext'):
                self.skipTest('Poppler unavailable; embedded-font/parser assertions passed')
            extracted = subprocess.check_output(['pdftotext','-enc','UTF-8',str(path),'-']).decode()
            # Poppler emits visual-order Arabic inside directional embeddings.
            # Apply the Unicode bidi algorithm to obtain its logical reading.
            from bidi.algorithm import get_display
            logical = '\n'.join(get_display(line) for line in extracted.splitlines())
            self.assertIn('مجلس الضيوف A-12', logical)
            self.assertIn('غرفة نوم ٢', logical)
            self.assertIn('35.00 m2', extracted)

    def test_same_approved_revision_produces_identical_pdf(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / 'a.pdf', Path(temp) / 'b.pdf'
            export_approved_pdf(ws, rev.id, a)
            export_approved_pdf(ws, rev.id, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == '__main__':
    unittest.main()
