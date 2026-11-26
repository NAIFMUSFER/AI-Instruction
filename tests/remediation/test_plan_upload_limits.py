"""A normal phone photo of a plan is accepted, and browser and server agree (U2).

Before: a 12 MP phone JPEG (3024x4032, 36.6 MB decoded RGB) was rejected on
save by the 32 MB decoded budget with an English detail. The browser now
downscales to the vision read's 2576 px long side before upload, and the
server decodes an oversized JPEG at 1/2, 1/4 or 1/8 scale (JPEG draft mode)
instead of rejecting it. No provider is called.
"""
import base64
import io
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw

import acs_plan_sources as S
import acs_upload_security as U

SOURCE = '44444444-4444-4444-8444-444444444444'


def phone_photo(size=(3024, 4032)):
    image = Image.new('RGB', size, (236, 232, 222))
    draw = ImageDraw.Draw(image)
    for i in range(0, size[0], 180):
        draw.line([(i, 0), (i + 40, size[1])], fill=(40, 40, 52), width=6)
    for j in range(0, size[1], 220):
        draw.line([(0, j), (size[0], j + 30)], fill=(40, 40, 52), width=6)
    out = io.BytesIO()
    exif = Image.Exif()
    exif[0x010F] = 'ExamplePhone'
    image.save(out, 'JPEG', quality=85, exif=exif)
    return out.getvalue()


def upload(raw, media='image/jpeg', name='photo.jpg'):
    return {'action': 'upload', 'source_id': SOURCE, 'name': name, 'media_type': media,
            'data_base64': base64.b64encode(raw).decode(), 'page': 1}


class PhonePhotos(unittest.TestCase):
    def test_a_12_megapixel_phone_jpeg_is_saved_with_a_read_sized_preview(self):
        raw = phone_photo()
        self.assertLessEqual(len(raw), S.MAX_FILE)
        self.assertGreater(U._decoded_bytes('RGB', 3024, 4032), U.ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES,
                           'the fixture exceeds the decoded budget, so the test is not vacuous')
        checked = S.validate_upload(upload(raw))
        self.assertNotIn('error', checked, checked.get('error'))
        preview = Image.open(io.BytesIO(checked['preview']))
        self.assertLessEqual(max(preview.size), U.VISION_MAX_SIDE)
        self.assertEqual(preview.size[0] * 4, preview.size[1] * 3, 'aspect ratio kept')

    def test_an_oversized_lossless_image_is_still_refused_with_the_shared_hint(self):
        out = io.BytesIO()
        Image.new('RGB', (11000, 3600), (3, 7, 11)).save(out, 'PNG', optimize=True)
        with self.assertRaises(U.UploadRejected) as caught:
            U.validate_image(out.getvalue(), 'image/png', max_side=U.VISION_MAX_SIDE)
        self.assertEqual(caught.exception.code, 'IMAGE_DECODED_TOO_LARGE')
        self.assertIn(str(U.VISION_MAX_SIDE), caught.exception.message_ar)

    def test_a_small_drawing_is_not_resampled(self):
        out = io.BytesIO()
        Image.new('RGB', (1400, 2240), 'white').save(out, 'PNG')
        checked = S.validate_upload(upload(out.getvalue(), 'image/png', 'plan.png'))
        self.assertEqual(Image.open(io.BytesIO(checked['preview'])).size, (1400, 2240))


class BrowserAndServerAgree(unittest.TestCase):
    def test_upload_limits_in_the_page_match_the_engine(self):
        source = (ROOT / 'public/app/ui/plan-upload.mjs').read_text(encoding='utf-8')
        found = re.search(r'export const LIMITS=(\{[^}]*\})', source)
        self.assertTrue(found, 'plan-upload.mjs exports its limits')
        limits = json.loads(re.sub(r'(\w+):', r'"\1":', found.group(1)).replace('*', '__MUL__')
                            .replace('5__MUL__1024__MUL__1024', str(5 * 1024 * 1024))
                            .replace('25__MUL__1024__MUL__1024', str(25 * 1024 * 1024))
                            .replace('2__MUL__1024__MUL__1024', str(2 * 1024 * 1024)))
        self.assertEqual(limits['file'], S.MAX_FILE)
        self.assertEqual(limits['preview'], S.MAX_PREVIEW)
        self.assertEqual(limits['pixels'], U.ACS_UPLOAD_MAX_IMAGE_PIXELS)
        self.assertEqual(limits['side'], U.ACS_UPLOAD_MAX_IMAGE_SIDE)
        self.assertEqual(limits['read'], U.VISION_MAX_SIDE)
        self.assertEqual(limits['file'], U.ACS_UPLOAD_MAX_IMAGE_BYTES)


if __name__ == '__main__':
    unittest.main()
