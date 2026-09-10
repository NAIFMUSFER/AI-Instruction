"""OpenAI integration contracts. Synthetic httpx transport only; no live keys."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import acs_api_errors as E
import acs_openai as O
import acs_provider as P
import acs_understand as U

REAL_CLIENT = httpx.Client
ENV = {"ACS_LLM_PROVIDER": "openai", "OPENAI_API_KEY": "unit-openai-credential",
       "ACS_LLM_MODEL": "gpt-5.4", "ACS_UPSTREAM_BACKOFF_S": "0"}


def reply(text='{"ok":true}', status="completed", reason=None, refusal=False):
    parts = ([{"type": "refusal", "refusal": "not logged"}] if refusal else
             [{"type": "output_text", "text": text}])
    return {"status": status, "output": [{"type": "message", "status": "completed",
                                           "role": "assistant", "content": parts}],
            "incomplete_details": {"reason": reason} if reason else None,
            "usage": {"input_tokens": 18, "output_tokens": 9,
                      "input_tokens_details": {"cached_tokens": 4},
                      "output_tokens_details": {"reasoning_tokens": 3}}}


def event(data, kind="response.completed"):
    return ("event: " + kind + "\ndata: " +
            json.dumps({"type": kind, "response": data}) + "\n\n").encode()


def factory(handler):
    return lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw)


class ProviderConfigTests(unittest.TestCase):
    def test_registry_and_default_are_backwards_compatible(self):
        self.assertIn("openai", P.PROVIDERS)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "unit-anthropic"}, clear=True):
            self.assertEqual(P.primary().provider, "anthropic")
            self.assertTrue(P.primary().ok)

    def test_native_key_is_used_not_old_deepseek_key(self):
        with patch.dict(os.environ, dict(ENV, ACS_LLM_API_KEY="unit-old-deepseek"), clear=True):
            cfg = P.primary()
            self.assertTrue(cfg.ok)
            self.assertEqual(cfg.api_key, ENV["OPENAI_API_KEY"])
            self.assertEqual(cfg.base_url, "https://api.openai.com/v1")

    def test_missing_openai_key_never_borrows_generic_or_anthropic(self):
        with patch.dict(os.environ, {"ACS_LLM_PROVIDER": "openai", "ACS_LLM_API_KEY": "unit-old-deepseek",
                                    "ANTHROPIC_API_KEY": "unit-anthropic"}, clear=True):
            self.assertFalse(P.primary().ok)
            self.assertIsNone(P.primary().api_key)

    def test_deepseek_fallback_can_reference_existing_secret_without_copying_it(self):
        env = dict(ENV, ACS_LLM_API_KEY="unit-old-deepseek", ACS_LLM_FALLBACK_PROVIDER="deepseek",
                   ACS_LLM_FALLBACK_API_KEY_ENV="ACS_LLM_API_KEY", ACS_LLM_FALLBACK_MODEL="deepseek-v4-pro")
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(P.primary().api_key, ENV["OPENAI_API_KEY"])
            self.assertEqual(P.fallback().api_key, "unit-old-deepseek")
            self.assertTrue(P.fallback().ok)

    def test_cross_provider_key_reference_is_rejected(self):
        env = dict(ENV, ACS_LLM_FALLBACK_PROVIDER="deepseek", ACS_LLM_FALLBACK_API_KEY_ENV="OPENAI_API_KEY")
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(P.fallback().ok)
            self.assertIsNone(P.fallback().api_key)

    def test_arbitrary_secret_name_is_rejected(self):
        with patch.dict(os.environ, dict(ENV, ACS_LLM_API_KEY_ENV="DATABASE_PASSWORD", DATABASE_PASSWORD="unit-private"), clear=True):
            self.assertFalse(P.primary().ok)
            self.assertIsNone(P.primary().api_key)

    def test_public_metadata_and_repr_do_not_expose_keys(self):
        with patch.dict(os.environ, ENV, clear=True):
            cfg = P.primary()
            blob = repr(cfg) + json.dumps(cfg.public()) + json.dumps(P.health_status()) + repr(O.ResponsesClient(cfg, 10))
            self.assertNotIn(ENV["OPENAI_API_KEY"], blob)
            self.assertTrue(P.health_status()["openai_key_configured"])

    def test_accounting_and_known_model_ceiling(self):
        with patch.dict(os.environ, ENV, clear=True):
            self.assertFalse(P.capabilities()["output_tokens_are_content_proxy"])
            self.assertEqual(P.documented_max_output(), 128000)
        with patch.dict(os.environ, dict(ENV, ACS_LLM_MODEL="unverified-custom-model"), clear=True):
            self.assertIsNone(P.documented_max_output())

    def test_openai_fallback_uses_its_own_key(self):
        with patch.dict(os.environ, {"ACS_LLM_PROVIDER": "deepseek", "ACS_LLM_API_KEY": "unit-ds",
                                    "ACS_LLM_FALLBACK_PROVIDER": "openai", "OPENAI_API_KEY": "unit-oa"}, clear=True):
            self.assertEqual(P.primary().api_key, "unit-ds")
            self.assertEqual(P.fallback().api_key, "unit-oa")


class WireTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = []

    def call(self, response, transport="stream", **kwargs):
        def handler(request):
            self.calls.append(request)
            return response(request) if callable(response) else response
        cfg = P.primary()
        cfg.transport = transport
        client = O.ResponsesClient(cfg, 10, factory(handler))
        with client.messages.stream(model=cfg.model, max_tokens=256, system="Produce JSON only.",
                                    messages=kwargs.get("messages", [{"role": "user", "content": "test"}])) as stream:
            return stream.get_final_message()

    def test_stream_uses_native_responses_and_terminal_result_only(self):
        delta = b'data: {"type":"response.output_text.delta","delta":"discard this delta"}\n\n'
        msg = self.call(httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                                      content=delta + event(reply())))
        req = self.calls[0]
        self.assertEqual(str(req.url), "https://api.openai.com/v1/responses")
        body = json.loads(req.content)
        self.assertEqual(body["max_output_tokens"], 256)
        self.assertNotIn("max_tokens", body)
        self.assertNotIn("thinking", body)
        self.assertFalse(body["store"])
        self.assertTrue(body["stream"])
        self.assertEqual(body["text"]["format"], {"type": "json_object"})
        self.assertEqual(msg.content[0].text, '{"ok":true}')
        self.assertEqual(msg.stop_reason, "end_turn")
        self.assertEqual(req.headers["Authorization"], "Bearer " + ENV["OPENAI_API_KEY"])

    def test_create_transport(self):
        msg = self.call(httpx.Response(200, json=reply()), transport="create")
        self.assertFalse(json.loads(self.calls[0].content)["stream"])
        self.assertEqual(msg.stop_reason, "end_turn")

    def test_usage_preserves_total_reasoning_and_cache(self):
        msg = O.normalise(reply())
        self.assertEqual((msg.usage.input_tokens, msg.usage.output_tokens), (18, 9))
        self.assertEqual(msg.usage.reasoning_tokens, 3)
        self.assertEqual(msg.usage.cache_read_input_tokens, 4)

    def test_unknown_usage_stays_none(self):
        data = reply(); data.pop("usage")
        msg = O.normalise(data)
        self.assertIsNone(msg.usage.output_tokens)
        self.assertIsNone(msg.usage.input_tokens)

    def test_images_are_translated_without_dropping_text(self):
        image = base64.b64encode(b"synthetic-image").decode()
        self.call(httpx.Response(200, json=reply()), transport="create", messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image}},
            {"type": "text", "text": "inspect"}]}])
        parts = json.loads(self.calls[0].content)["input"][0]["content"]
        self.assertEqual(parts[0]["type"], "input_image")
        self.assertEqual(parts[0]["image_url"], "data:image/png;base64," + image)
        self.assertEqual(parts[1], {"type": "input_text", "text": "inspect"})

    def test_remote_images_fail_before_network(self):
        with self.assertRaises(E.AcsApiError):
            self.call(httpx.Response(200, json=reply()), messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "url", "url": "https://example.test/private"}}]}])
        self.assertEqual(self.calls, [])

    def test_old_or_untrusted_endpoint_fails_before_network(self):
        for url in ("https://api.deepseek.com/anthropic", "http://api.openai.com/v1",
                    "https://api.openai.com.evil.test/v1", "https://name:password@api.openai.com/v1",
                    "https://api.openai.com/v1?key=private", "https://api.openai.com:444/v1"):
            with self.subTest(url=url), self.assertRaises(E.AcsApiError):
                O.endpoint(url)
        self.assertEqual(O.endpoint("https://api.openai.com/v1/"), "https://api.openai.com/v1/responses")

    def test_redirect_is_not_followed(self):
        with self.assertRaises(E.AcsApiError) as caught:
            self.call(httpx.Response(307, headers={"Location": "https://example.test/receive"}))
        self.assertEqual(caught.exception.code, E.ACS_INTEGRATION_ERROR)
        self.assertEqual(len(self.calls), 1)

    def test_incomplete_response_never_becomes_success(self):
        msg = O.normalise(reply(status="incomplete", reason="max_output_tokens"))
        self.assertEqual(E.classify_response(msg.stop_reason, len(msg.content[0].text))[1], E.ACS_UPSTREAM_TRUNCATED)

    def test_empty_token_limited_response_remains_ceiling_evidence(self):
        data = reply(status="incomplete", reason="max_output_tokens"); data["output"] = []
        msg = O.normalise(data)
        self.assertEqual(msg.stop_reason, "max_tokens")
        self.assertTrue(msg.content)
        self.assertEqual(E.classify_response(msg.stop_reason, 0, 0, len(msg.content))[1], E.ACS_UPSTREAM_NO_VISIBLE_OUTPUT)

    def test_refusal_wins_even_with_other_text(self):
        data = reply(refusal=True)
        data["output"][0]["content"].append({"type": "output_text", "text": '{"ok":true}'})
        self.assertEqual(O.normalise(data).stop_reason, "refusal")

    def test_no_terminal_event_rejects_complete_looking_delta(self):
        body = b'data: {"type":"response.output_text.delta","delta":"{}"}\n\ndata: [DONE]\n\n'
        with self.assertRaises(E.AcsApiError) as caught:
            self.call(httpx.Response(200, headers={"Content-Type": "text/event-stream"}, content=body))
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_TRUNCATED)

    def test_terminal_event_status_mismatch_is_rejected(self):
        with self.assertRaises(E.AcsApiError) as caught:
            self.call(httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                                     content=event(reply(status="incomplete"))))
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_TRUNCATED)

    def test_unknown_incomplete_reason_is_rejected(self):
        with self.assertRaises(E.AcsApiError):
            O.normalise(reply(status="incomplete", reason="unknown"))

    def test_unauthorized_tools_are_not_accepted_as_output(self):
        data = reply(); data["output"] = [{"type": "function_call", "name": "unexpected"}]
        with self.assertRaises(E.AcsApiError):
            O.normalise(data)

    def test_error_classification_and_no_raw_message_leak(self):
        for status, code, expected in (
            (401, "invalid_api_key", E.ACS_UPSTREAM_AUTH),
            (403, "permission_denied", E.ACS_UPSTREAM_PERMISSION),
            (404, "model_not_found", E.ACS_UPSTREAM_MODEL_REJECTED),
            (429, "insufficient_quota", E.ACS_UPSTREAM_BILLING),
            (429, "rate_limit_exceeded", E.ACS_UPSTREAM_RATE_LIMIT),
            (503, "server_error", E.ACS_UPSTREAM_UNAVAILABLE)):
            with self.subTest(status=status, code=code), self.assertRaises(E.AcsApiError) as caught:
                self.call(httpx.Response(status, json={"error": {"code": code, "message": "unit-private-provider-body"}}))
            self.assertEqual(caught.exception.code, expected)
            self.assertNotIn("unit-private-provider-body", str(caught.exception) + str(caught.exception.upstream))

    def test_response_size_is_bounded(self):
        with patch.object(O, "MAX_RESPONSE_BYTES", 30), self.assertRaises(E.AcsApiError):
            self.call(httpx.Response(200, content=b"x" * 100), transport="create")

    def test_sse_handles_crlf_comments_and_chunked_utf8(self):
        raw = b": keepalive\r\n\r\n" + event(reply('{"name":"بيت"}')).replace(b"\n", b"\r\n")
        class Stream(httpx.SyncByteStream):
            def __iter__(self):
                for i in range(0, len(raw), 3):
                    yield raw[i:i+3]
        msg = self.call(httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=Stream()))
        self.assertEqual(json.loads(msg.content[0].text)["name"], "بيت")

    def test_post_header_read_failure_is_not_fallback_eligible(self):
        class Broken(httpx.SyncByteStream):
            def __iter__(self):
                yield b"data: {"
                raise httpx.ReadError("unit-private")
        with self.assertRaises(E.AcsApiError) as caught:
            self.call(httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=Broken()))
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_TRUNCATED)

    def test_client_is_closed_on_failure(self):
        clients = []
        def make(**kw):
            c = factory(lambda req: httpx.Response(401, json={}))( **kw)
            clients.append(c); return c
        with self.assertRaises(E.AcsApiError):
            O.ResponsesClient(P.primary(), 10, make).create(model="gpt-5.4", max_tokens=256,
                system="JSON", messages=[{"role": "user", "content": "test"}])
        self.assertTrue(clients[0].is_closed)


class ResponseShapeTests(unittest.TestCase):
    def test_bad_nested_fields_are_classified(self):
        for details in (["bad"], "bad", 1):
            data = reply(); data["incomplete_details"] = details
            with self.subTest(details=details), self.assertRaises(E.AcsApiError) as caught:
                O.normalise(data)
            self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_INVALID_JSON)
        for content in (None, "bad", 1, {}):
            data = reply(); data["output"][0]["content"] = content
            with self.subTest(content=content), self.assertRaises(E.AcsApiError) as caught:
                O.normalise(data)
            self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_INVALID_JSON)

    def test_completed_response_cannot_hide_unfinished_message(self):
        for status in ("incomplete", "in_progress", "unknown"):
            data = reply(); data["output"][0]["status"] = status
            with self.subTest(status=status), self.assertRaises(E.AcsApiError) as caught:
                O.normalise(data)
            self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_TRUNCATED)

    def test_malformed_terminal_never_retries_or_uses_fallback(self):
        calls, tel = [], {}
        data = reply(); data["incomplete_details"] = ["bad"]
        def handle(request):
            calls.append(request)
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=event(data))
        env = dict(ENV, ACS_LLM_FALLBACK_PROVIDER="deepseek", ACS_LLM_FALLBACK_API_KEY="unit-ds")
        with patch.dict(os.environ, env, clear=True), patch.object(O.httpx, "Client", side_effect=factory(handle)), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaises(E.AcsApiError) as caught:
            U.call_llm("test", max_tokens=256, telemetry=tel)
        self.assertEqual(caught.exception.code, E.ACS_UPSTREAM_INVALID_JSON)
        self.assertEqual(len(calls), 1)
        self.assertFalse(tel["fallback_attempted"])

    def test_malformed_error_code_does_not_raise_python_exception(self):
        err = O._provider_error(0, {"error": {"code": ["bad"]}})
        self.assertEqual(err.code, E.ACS_UPSTREAM_BAD_REQUEST)

    def test_reasoning_read_timeout_uses_configured_budget(self):
        captured = []
        def make(**kw):
            captured.append(kw["timeout"])
            return factory(lambda req: httpx.Response(200, json=reply()))(**kw)
        with patch.dict(os.environ, ENV, clear=True):
            O.ResponsesClient(P.primary(), 120, make).create(model="gpt-5.4", max_tokens=256,
                system="JSON", messages=[{"role": "user", "content": "test"}])
        self.assertEqual(captured[0].read, 120)
        self.assertEqual(captured[0].connect, 30)


class PipelineTests(unittest.TestCase):
    def test_actual_call_path_native_transport_and_safe_telemetry(self):
        calls, tel, logs = [], {}, io.StringIO()
        def handle(request):
            calls.append(request)
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=event(reply()))
        with patch.dict(os.environ, ENV, clear=True), patch.object(O.httpx, "Client", side_effect=factory(handle)), contextlib.redirect_stdout(logs):
            text = U.call_llm("unit-private-description", btype="villa", max_tokens=256, telemetry=tel)
        self.assertEqual(json.loads(text), {"ok": True})
        self.assertEqual(len(calls), 1)
        self.assertEqual(tel["provider"], "openai")
        self.assertTrue(tel["complete"])
        self.assertIn("responses", tel["sdk_version"])
        self.assertFalse(tel["thinking_sent"])
        self.assertEqual(tel["reasoning_tokens"], 3)
        self.assertNotIn("unit-private-description", logs.getvalue())
        self.assertNotIn(ENV["OPENAI_API_KEY"], logs.getvalue())

    def test_fallback_preserves_deepseek_key_and_model_with_primary_override(self):
        env = dict(ENV, ACS_LLM_API_KEY="unit-deepseek-credential", ACS_LLM_FALLBACK_PROVIDER="deepseek",
                   ACS_LLM_FALLBACK_API_KEY_ENV="ACS_LLM_API_KEY", ACS_LLM_FALLBACK_MODEL="deepseek-v4-pro")
        builds, sent, tel = [], [], {}
        original = U._build_client
        class DS:
            @contextlib.contextmanager
            def stream(self, **kw):
                sent.append(kw)
                yield SimpleNamespace(get_final_message=lambda: O.normalise(reply()))
        def build(cfg, timeout):
            builds.append(cfg)
            return original(cfg, timeout) if cfg.provider == "openai" else SimpleNamespace(messages=DS())
        with patch.dict(os.environ, env, clear=True), patch.object(U, "_build_client", side_effect=build), \
             patch.object(O.httpx, "Client", side_effect=factory(lambda r: httpx.Response(503, json={"error": {"code": "server_error"}}))), \
             contextlib.redirect_stdout(io.StringIO()):
            U.call_llm("test", model="gpt-5.4", max_tokens=256, telemetry=tel)
        self.assertEqual([x.provider for x in builds], ["openai", "deepseek"])
        self.assertEqual(builds[1].api_key, "unit-deepseek-credential")
        self.assertEqual(sent[0]["model"], "deepseek-v4-pro")
        self.assertTrue(tel["fallback_success"])
        self.assertEqual(tel["provider"], "deepseek")

    def test_auth_billing_and_truncation_never_trigger_fallback(self):
        env = dict(ENV, ACS_LLM_FALLBACK_PROVIDER="deepseek", ACS_LLM_FALLBACK_API_KEY="unit-ds")
        cases = [(httpx.Response(401, json={}), E.ACS_UPSTREAM_AUTH),
                 (httpx.Response(429, json={"error": {"code": "insufficient_quota"}}), E.ACS_UPSTREAM_BILLING),
                 (httpx.Response(200, headers={"content-type": "text/event-stream"}, content=b""), E.ACS_UPSTREAM_TRUNCATED)]
        for response, code in cases:
            tel = {}
            with self.subTest(code=code), patch.dict(os.environ, env, clear=True), \
                 patch.object(O.httpx, "Client", side_effect=factory(lambda r: response)), \
                 contextlib.redirect_stdout(io.StringIO()), self.assertRaises(E.AcsApiError) as caught:
                U.call_llm("test", max_tokens=256, telemetry=tel)
            self.assertEqual(caught.exception.code, code)
            self.assertFalse(tel["fallback_attempted"])

    def test_docker_and_mandatory_ci_include_transport_and_tests(self):
        root = Path(__file__).resolve().parents[2]
        self.assertIn("acs_openai.py", (root / "Dockerfile").read_text())
        self.assertIn("test_openai_provider.py", (root / "tests/remediation/test_generation_spatial_context.py").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
