"""A refused plan file is explained in Arabic and is not offered for retry (U1, U9).

Before: the engine returned the English diagnostic (``str(exc)``, e.g.
"PDF_ENCRYPTED: encrypted pdf: empty-password decrypt refused") and the page
said «أعد المحاولة» for a file that can never be accepted; a password PDF
showed pdf.js's "No password given". No provider is called.
"""
import base64
import io
from pathlib import Path
import re
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image
import pypdf

import acs_plan_sources as S

SOURCE = '44444444-4444-4444-8444-444444444444'


def preview():
    out = io.BytesIO()
    Image.new('RGB', (60, 90), 'white').save(out, 'JPEG')
    return base64.b64encode(out.getvalue()).decode()


def upload(raw, media, name, **extra):
    return dict({'action': 'upload', 'source_id': SOURCE, 'name': name, 'media_type': media,
                 'data_base64': base64.b64encode(raw).decode(), 'page': 1}, **extra)


def password_pdf():
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.encrypt(user_password='secret-pdf', owner_password='owner-pdf')
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def flate_bomb():
    raw = b' ' * (40 * 1024 * 1024) + b'\nBT /F1 24 Tf 72 720 Td (bomb) Tj ET\n'
    comp = zlib.compress(raw, 9)
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>',
            b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp) + comp + b'\nendstream']
    out = io.BytesIO()
    out.write(b'%PDF-1.4\n')
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b'%d 0 obj\n' % i + obj + b'\nendobj\n')
    xref = out.tell()
    out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for offset in offsets:
        out.write(b'%010d 00000 n \n' % offset)
    out.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref))
    return out.getvalue()


def huge_png():
    out = io.BytesIO()
    Image.new('RGB', (11000, 3600), (255, 255, 255)).save(out, 'PNG', optimize=True)
    return out.getvalue()


class RefusedFiles(unittest.TestCase):
    def test_every_refusal_reaches_the_owner_in_arabic_as_unusable(self):
        cases = {
            'password PDF': upload(password_pdf(), 'application/pdf', 'p.pdf', preview_base64=preview()),
            'flate bomb': upload(flate_bomb(), 'application/pdf', 'b.pdf', preview_base64=preview()),
            'decoded 119 MB PNG': upload(huge_png(), 'image/png', 'h.png'),
            'SVG renamed .png': upload(b'<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>',
                                       'image/png', 's.png'),
            'GIF declared PNG': upload(b'GIF89a' + b'\0' * 64, 'image/png', 'g.png'),
        }
        for label, command in cases.items():
            with self.subTest(label):
                error = S.validate_upload(command)['error']
                self.assertEqual(error['code'], 'INVALID_PLAN_SOURCE')
                self.assertTrue(error['message'].startswith('لا يمكن استخدام هذا الملف كما هو: '), error)
                self.assertNotRegex(error['message'], r'[A-Z]{3,}_[A-Z]', 'no engine code reaches the owner')
                self.assertNotIn('decrypt', error['message'])
        self.assertIn('كلمة مرور', S.validate_upload(cases['password PDF'])['error']['message'])
        self.assertIn('2576', S.validate_upload(cases['decoded 119 MB PNG'])['error']['message'])


class PageWording(unittest.TestCase):
    def test_the_page_never_offers_a_retry_for_a_refused_file(self):
        source = (ROOT / 'public/app/ui/plan-upload.mjs').read_text(encoding='utf-8')
        self.assertIn("PasswordException", source)
        self.assertIn('ملف PDF محمي بكلمة مرور. أزل الحماية', source)
        # The retry line is kept only for a lost response, never for a refusal.
        save = source[source.index("$('cwSaveSource').addEventListener"):]
        save = save[:save.index("$('cwDownloadSource')")]
        self.assertIn("['INVALID_PLAN_SOURCE','INPUT_LIMIT'].includes(e?.code)", save)
        self.assertRegex(save, r"refused\?.*UNUSABLE")


if __name__ == '__main__':
    unittest.main()
