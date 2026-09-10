"""Verify thinking control in HTTP bodies made by the pinned Anthropic SDK.

The HTTP transport is intercepted locally: no provider call, key, or bill.
Regression: SDK 0.40 does not accept a named thinking argument, but its
extra_body extension must still send DeepSeek's explicit disabled setting.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import anthropic
import httpx
import acs_api_errors as E
import acs_understand as U


def response_message(text='{"ok":1}', stop="end_turn"):
    return dict(id="msg_local", type="message", role="assistant",
                model="deepseek-v4-pro", content=[dict(type="text", text=text)],
                stop_reason=stop, stop_sequence=None,
                usage=dict(input_tokens=3, output_tokens=6))


def response_stream(message):
    start = dict(message, content=[], stop_reason=None)
    events = [dict(type="message_start", message=start),
              dict(type="content_block_start", index=0,
                   content_block=dict(type="text", text="")),
              dict(type="content_block_delta", index=0,
                   delta=dict(type="text_delta", text=message["content"][0]["text"])),
              dict(type="content_block_stop", index=0),
              dict(type="message_delta", delta=dict(
                   stop_reason=message["stop_reason"], stop_sequence=None),
                   usage=dict(output_tokens=6)),
              dict(type="message_stop")]
    return "".join("event: %s\ndata: %s\n\n" % (e["type"], json.dumps(e))
                   for e in events)


class ThinkingWire(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ACS_LLM_PROVIDER": "deepseek",
            "ACS_LLM_API_KEY": "local-transport-test-key",
            "ACS_LLM_MODEL": "deepseek-v4-pro",
            "ACS_LLM_BASE_URL": "https://api.deepseek.com/anthropic",
            "ACS_UPSTREAM_BACKOFF_S": "0",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sent = []
        self.responses = []

        def handle(request):
            body = json.loads(request.content)
            self.sent.append((request.url, body))
            message = self.responses.pop(0) if self.responses else response_message()
            if body.get("stream"):
                return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                      text=response_stream(message))
            return httpx.Response(200, json=message)

        self.client = anthropic.Anthropic(
            api_key="local-transport-test-key", max_retries=0,
            base_url="https://api.deepseek.com/anthropic",
            http_client=httpx.Client(transport=httpx.MockTransport(handle)))
        self.addCleanup(self.client.close)

    def call(self, client=None, **kwargs):
        telemetry = {}
        with patch.object(U, "_build_client", return_value=client or self.client), \
                contextlib.redirect_stdout(io.StringIO()):
            output = U._call_llm_impl("one room", max_tokens=64,
                                      telemetry=telemetry, **kwargs)
        return output, telemetry

    def test_pinned_sdk_rejects_named_thinking(self):
        self.assertEqual(anthropic.__version__, "0.40.0")
        with self.assertRaises(TypeError):
            self.client.messages.stream(model="deepseek-v4-pro", max_tokens=64,
                                        messages=[], thinking={"type": "disabled"})
        self.assertEqual(self.sent, [])

    def test_text_stream_sends_disabled_in_actual_http_body(self):
        output, telemetry = self.call(stage="plan")
        self.assertEqual(output, '{"ok":1}')
        self.assertEqual(len(self.sent), 1)
        url, body = self.sent[0]
        self.assertEqual(url.host, "api.deepseek.com")
        self.assertEqual(url.path, "/anthropic/v1/messages")
        self.assertEqual(body.get("thinking"), {"type": "disabled"})
        self.assertNotIn("extra_body", body)
        self.assertTrue(telemetry["thinking_sent"])

    def test_image_stream_uses_the_same_control(self):
        content = [{"type": "image", "source": {
            "type": "base64", "media_type": "image/png", "data": "dGVzdA=="}}]
        _, telemetry = self.call(stage="vision", content=content)
        self.assertEqual(self.sent[0][1]["messages"][0]["content"], content)
        self.assertEqual(self.sent[0][1].get("thinking"), {"type": "disabled"})
        self.assertTrue(telemetry["thinking_sent"])

    def test_create_fallback_preserves_the_http_control(self):
        class MessagesWithoutStream:
            create = self.client.messages.create

        class ClientWithoutStream:
            messages = MessagesWithoutStream()

        _, telemetry = self.call(client=ClientWithoutStream())
        self.assertEqual(self.sent[0][1].get("thinking"), {"type": "disabled"})
        self.assertEqual(telemetry["transport"], "create")
        self.assertTrue(telemetry["thinking_sent"])

    def test_unsupported_control_fails_before_http(self):
        class MessagesWithoutControl:
            def stream(self, *, model, messages, system, max_tokens):
                raise AssertionError("unsupported control must fail before sending")

            create = stream

        class ClientWithoutControl:
            messages = MessagesWithoutControl()

        with self.assertRaises(E.AcsApiError) as caught:
            self.call(client=ClientWithoutControl())
        self.assertEqual(caught.exception.code, E.ACS_INTEGRATION_ERROR)
        self.assertEqual(self.sent, [])

    def test_default_retry_is_sent_only_as_a_distinct_request(self):
        self.responses = [response_message("", "max_tokens"), response_message()]
        output, telemetry = self.call()
        self.assertEqual(output, '{"ok":1}')
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.sent[0][1].get("thinking"), {"type": "disabled"})
        self.assertNotIn("thinking", self.sent[1][1])
        self.assertFalse(telemetry["thinking_sent"])

    def test_old_anthropic_path_keeps_its_existing_arguments(self):
        os.environ["ACS_LLM_PROVIDER"] = "anthropic"
        _, telemetry = self.call()
        self.assertNotIn("thinking", self.sent[0][1])
        self.assertFalse(telemetry["thinking_sent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
