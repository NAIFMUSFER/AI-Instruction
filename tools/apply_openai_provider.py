"""One-shot final response validation; verified by the existing focused workflow."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path.cwd()))
import acs_openai as O

# Reproduce the malformed-body defects before changing their handling.
base = {"status": "completed", "output": []}
for payload, error in ((dict(base, incomplete_details=["bad"]), AttributeError),
                       (dict(base, output=[{"type": "message", "content": None}]), TypeError)):
    try:
        O.normalise(payload)
    except error:
        print("REPRODUCED malformed response escaped as", error.__name__)
    else:
        raise SystemExit("expected malformed response witness changed")


def replace(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit("anchor drift: " + path)
    p.write_text(text.replace(old, new), encoding="utf-8")


replace("acs_openai.py", '    code = raw.get("code") or raw.get("type")\n',
        '    code = raw.get("code") or raw.get("type")\n'
        '    code = code if isinstance(code, str) else None\n')
replace("acs_openai.py", '    blocks, refused = [], False\n',
        '    details = response.get("incomplete_details")\n'
        '    if details is not None and not isinstance(details, dict):\n'
        '        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_incomplete_details")\n'
        '    reason = (details or {}).get("reason")\n'
        '    blocks, refused, unfinished = [], False, False\n')
replace("acs_openai.py", '''        elif item.get("type") == "message":
            if item.get("status", "completed") not in ("completed", "incomplete"):
                raise _error(E.ACS_UPSTREAM_TRUNCATED, "unfinished_message")
            for part in item.get("content", []):
''', '''        elif item.get("type") == "message":
            if item.get("role", "assistant") != "assistant":
                raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_output_role")
            if item.get("status", "completed") != "completed":
                unfinished = True
            parts = item.get("content", [])
            if not isinstance(parts, list):
                raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_output_content")
            for part in parts:
''')
replace("acs_openai.py", '    reason = (response.get("incomplete_details") or {}).get("reason")\n', '')
replace("acs_openai.py", '''        if not blocks:
            blocks.append(SimpleNamespace(type="output_limit"))
    usage = response.get("usage") or {}
''', '''        if not blocks:
            blocks.append(SimpleNamespace(type="output_limit"))
    elif unfinished:
        raise _error(E.ACS_UPSTREAM_TRUNCATED, "unfinished_message")
    usage = response.get("usage") or {}
''')
replace("acs_openai.py", '''            with self._factory(timeout=httpx.Timeout(min(self.timeout, 30.0)),
''', '''            # Keep the configured read budget: a reasoning model may pause
            # before visible output. Connection/pool waits remain short, and
            # the ACS worker is the hard wall-clock request boundary.
            with self._factory(timeout=httpx.Timeout(self.timeout,
                                                     connect=min(self.timeout, 30.0),
                                                     pool=min(self.timeout, 30.0)),
''')
replace("acs_openai.py", '''                        kind = event.get("type")
                        if kind == "error":
''', '''                        kind = event.get("type")
                        if not isinstance(kind, str):
                            raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_event_type")
                        if kind == "error":
''')
replace("acs_provider.py", '    ACS_LLM_PROVIDER            deepseek | anthropic          (افتراضي anthropic)',
        '    ACS_LLM_PROVIDER            deepseek | anthropic | openai (افتراضي anthropic)')
replace("acs_provider.py", '    ACS_LLM_TRANSPORT           stream | create               (افتراضي stream)\n',
        '    ACS_LLM_TRANSPORT           stream | create               (افتراضي stream)\n'
        '    OPENAI_API_KEY              مفتاح OpenAI فقط؛ لا يُستعار المفتاح العام له\n'
        '    ACS_LLM_API_KEY_ENV         اسم متغير المفتاح من قائمة محددة، لا قيمته\n'
        '    ACS_LLM_FALLBACK_API_KEY_ENV اسم متغير مفتاح البديل، لا قيمته\n')

extra = '''

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
        with patch.dict(os.environ, env, clear=True), patch.object(O.httpx, "Client", side_effect=factory(handle)), \\
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

'''
replace("tests/remediation/test_openai_provider.py", '\n\nclass PipelineTests(unittest.TestCase):\n',
        extra + '\nclass PipelineTests(unittest.TestCase):\n')
# The existing workflow stages the product files; include this exact test path.
subprocess.run(["git", "add", "tests/remediation/test_openai_provider.py"], check=True)
print("Malformed terminal responses now fail closed; focused suites follow")
