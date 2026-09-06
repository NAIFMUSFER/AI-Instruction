"""C11: image forms must obey the numeric contract of text generation."""
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import acs_understand_api as A


class ImageDimensions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=A.app), base_url="http://audit.local")
        # The decoder/provider are doubles; multipart parsing and numeric
        # validation run through the real ASGI app before those boundaries.
        self.checked = [{"media_type": "image/png", "normalized": b"png",
                         "width": 1, "height": 1}]

    async def asyncTearDown(self):
        await self.client.aclose()

    async def post(self, data):
        return await self.client.post("/v1/understand/image", data=data,
            files={"files": ("plan.png", b"png", "image/png")})

    async def test_invalid_dimensions_stop_before_decode_or_generation(self):
        invalid = [(field, value) for field in ("site_w", "site_d")
                   for value in ("nan", "inf", "-inf", "-1", "0", "100001")]
        invalid += [("floors", value) for value in ("-1", "0", "401", "1.5")]
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                with patch.object(A, "guard") as guard, \
                     patch.object(A, "_validate", AsyncMock(return_value=self.checked)) as decode, \
                     patch.object(A, "run_job", AsyncMock(return_value={})) as job, \
                     patch.object(A, "_understand_payload", AsyncMock(return_value={"ok": True})):
                    response = await self.post({field: value})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertFalse(response.json()["ok"])
                self.assertTrue(response.json()["error"]["request_id"])
                guard.assert_not_called()
                decode.assert_not_awaited()
                job.assert_not_awaited()

    async def test_valid_dimensions_and_hints_reach_provider_unchanged(self):
        for width, depth, floors in ((20, 25, 3), (100000, 0.1, 400)):
            with self.subTest(width=width, depth=depth, floors=floors):
                with patch.object(A, "guard"), \
                     patch.object(A, "_validate", AsyncMock(return_value=self.checked)), \
                     patch.object(A, "run_job", AsyncMock(return_value={})) as job, \
                     patch.object(A, "_understand_payload", AsyncMock(return_value={"ok": True})):
                    response = await self.post({"site_w": str(width), "site_d": str(depth),
                        "floors": str(floors), "notes": "بدون فرز", "strict": "true",
                        "btype": "warehouse"})
                self.assertEqual(response.status_code, 200, response.text)
                args = job.call_args.args
                self.assertEqual(args[0], "acs_understand:understand_images")
                self.assertEqual({key: args[1][key] for key in
                    ("site_w", "site_d", "floors", "notes", "strict", "btype")},
                    dict(site_w=width, site_d=depth, floors=floors, notes="بدون فرز",
                         strict=True, btype="warehouse"))

    async def test_optional_dimensions_remain_optional(self):
        with patch.object(A, "guard"), \
             patch.object(A, "_validate", AsyncMock(return_value=self.checked)), \
             patch.object(A, "run_job", AsyncMock(return_value={})) as job, \
             patch.object(A, "_understand_payload", AsyncMock(return_value={"ok": True})):
            response = await self.post({})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([job.call_args.args[1][key] for key in
                          ("site_w", "site_d", "floors")], [None, None, None])


if __name__ == "__main__":
    unittest.main(verbosity=2)
