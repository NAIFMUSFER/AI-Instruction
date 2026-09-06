"""Bounded ASGI regressions for C08; no provider calls or public requests."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import acs_understand_api as A
import acs_api_errors as E


class RequestBodyLimits(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=A.app), base_url="http://audit.local")
        self.origin = "https://sprightly-selkie-d906c3.netlify.app"
        self.budget = A.MAX_UPLOAD + 4 * A.MAX_NOTES + 64 * 1024

    async def asyncTearDown(self):
        await self.client.aclose()

    def check_error(self, response, status):
        self.assertEqual(response.status_code, status, response.text[:300])
        self.assertFalse(response.json()["ok"])
        self.assertTrue(response.json()["error"]["request_id"])
        self.assertEqual(response.headers["access-control-allow-origin"], self.origin)

    async def test_declared_oversize_rejected_before_body_read(self):
        reads = []
        async def body():
            reads.append(1)
            yield b"--a--\r\n"
        res = await self.client.post("/v1/understand/pdf", content=body(), headers={
            "Content-Type": "multipart/form-data; boundary=a",
            "Content-Length": str(self.budget + 1), "Origin": self.origin})
        self.check_error(res, 413)
        self.assertEqual(reads, [], "oversize header must be rejected before parsing")

    async def test_chunked_file_stops_before_consuming_tail(self):
        reads = []
        chunks = self.budget // 65536 + 8
        async def body():
            yield (b'--a\r\nContent-Disposition: form-data; name="file"; filename="x.pdf"'
                   b'\r\nContent-Type: application/pdf\r\n\r\n')
            for i in range(chunks):
                reads.append(i)
                yield b"X" * 65536
            yield b"\r\n--a--\r\n"
        res = await self.client.post("/v1/understand/pdf", content=body(), headers={
            "Content-Type": "multipart/form-data; boundary=a", "Origin": self.origin})
        self.check_error(res, 413)
        self.assertLess(len(reads), chunks, "the parser must not spool the complete upload")

    async def test_nonfile_part_limit_runs_before_endpoint_validation(self):
        validator = AsyncMock(side_effect=E.AcsApiError(E.ACS_UNPROCESSABLE))
        with patch.object(A, "_validate", validator):
            res = await self.client.post("/v1/understand/pdf",
                data={"unused": "X" * (2 * 1024 * 1024)},
                files={"file": ("audit.pdf", b"%PDF-1.7\n", "application/pdf")},
                headers={"Origin": self.origin})
        self.check_error(res, 400)
        validator.assert_not_awaited()

    async def test_urlencoded_field_limit_runs_before_endpoint(self):
        data = "&".join("f%d=x" % i for i in range(1001))
        res = await self.client.post("/v1/understand/pdf", content=data, headers={
            "Content-Type": "application/x-www-form-urlencoded", "Origin": self.origin})
        self.check_error(res, 400)

    async def test_small_file_keeps_existing_validation_and_error_contract(self):
        validator = AsyncMock(side_effect=E.AcsApiError(E.ACS_UNPROCESSABLE))
        with patch.object(A, "_validate", validator):
            res = await self.client.post("/v1/understand/pdf",
                files={"file": ("audit.pdf", b"%PDF-1.7\n", "application/pdf")},
                headers={"Origin": self.origin})
        self.check_error(res, 422)
        validator.assert_awaited_once()
        self.assertEqual(validator.call_args.args[0], "validate_pdf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
