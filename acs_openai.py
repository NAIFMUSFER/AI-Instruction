# -*- coding: utf-8 -*-
"""Native OpenAI Responses transport; preserves the ACS message/result contract.

Uses the already locked httpx dependency, not the Anthropic protocol. No SDK
retries, tools, remote image URLs, response storage, or raw-response logging.
JSON mode is NOT strict schema validation: ACS still validates the Building.
Sources (checked 2026-09-11):
https://developers.openai.com/api/docs/guides/streaming-responses
https://developers.openai.com/api/docs/guides/structured-outputs
https://developers.openai.com/api/reference/python/resources/responses/methods/create
"""
import base64
import binascii
import json
import math
import os
import time
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import acs_api_errors as E

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_STREAM_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 262144
MAX_IMAGE_BYTES = 8 * 1024 * 1024
TERMINAL = {"response.completed": "completed", "response.incomplete": "incomplete",
            "response.failed": "failed"}


def _error(code, kind, status=None):
    # Only controlled identifiers, never provider messages or response bodies.
    up = {"provider": "openai", "kind": kind}
    if status is not None:
        up["status_code"] = status
    return E.AcsApiError(code, upstream=up)


def endpoint(base_url):
    """Refuse an old DeepSeek URL before attaching an OpenAI credential."""
    try:
        p = urlsplit(base_url or "https://api.openai.com/v1")
        valid = (p.scheme == "https" and p.hostname == "api.openai.com"
                 and p.port in (None, 443) and not p.username and not p.password
                 and p.path.rstrip("/") == "/v1" and not p.query and not p.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise _error(E.ACS_INTEGRATION_ERROR, "openai_endpoint_not_allowed")
    return "https://api.openai.com/v1/responses"


def _number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _provider_error(status, data):
    raw = data.get("error", data) if isinstance(data, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    code = raw.get("code") or raw.get("type")
    # Terminal SSE failures have no independent HTTP status. Classify only
    # known codes; an unknown terminal failure must not spend on a fallback.
    if status == 0:
        status = {"invalid_api_key": 401, "permission_denied": 403,
                  "model_not_found": 404, "rate_limit_exceeded": 429,
                  "insufficient_quota": 429, "server_error": 503}.get(code, 400)
    if code in ("insufficient_quota", "billing_hard_limit_reached", "billing_not_active") or status == 402:
        return _error(E.ACS_UPSTREAM_BILLING, "billing", status)
    if code in ("content_filter", "safety_violation"):
        return _error(E.ACS_UPSTREAM_REFUSED, "refusal", status)
    if status == 401:
        return _error(E.ACS_UPSTREAM_AUTH, "authentication", status)
    if status == 403:
        return _error(E.ACS_UPSTREAM_PERMISSION, "permission", status)
    if status == 404 or code == "model_not_found":
        return _error(E.ACS_UPSTREAM_MODEL_REJECTED, "model_rejected", status)
    if status == 429 or code == "rate_limit_exceeded":
        return _error(E.ACS_UPSTREAM_RATE_LIMIT, "rate_limit", status)
    if status in (408, 504):
        return _error(E.ACS_UPSTREAM_TIMEOUT, "timeout", status)
    if 300 <= status < 400:
        return _error(E.ACS_INTEGRATION_ERROR, "redirect_refused", status)
    if status >= 500 or code == "server_error":
        return _error(E.ACS_UPSTREAM_UNAVAILABLE, "unavailable", status)
    return _error(E.ACS_UPSTREAM_BAD_REQUEST, "request_rejected", status)


def _json(raw):
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError):
        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_response_json") from None
    if not isinstance(obj, dict):
        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_response_object")
    return obj


def _input(messages):
    result = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_input_role")
        content = message.get("content")
        if isinstance(content, str):
            result.append({"role": "user", "content": content})
            continue
        if not isinstance(content, list):
            raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_input_content")
        parts = []
        for part in content:
            if not isinstance(part, dict):
                raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_input_block")
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                parts.append({"type": "input_text", "text": part["text"]})
            elif part.get("type") == "image":
                src = part.get("source")
                if not isinstance(src, dict) or src.get("type") != "base64":
                    raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_image_source")
                media, data = src.get("media_type"), src.get("data")
                if (media not in ("image/png", "image/jpeg", "image/webp")
                        or not isinstance(data, str) or len(data) > MAX_IMAGE_BYTES):
                    raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_image_content")
                try:
                    base64.b64decode(data, validate=True)
                except (ValueError, binascii.Error):
                    raise _error(E.ACS_INTEGRATION_ERROR, "invalid_image_base64") from None
                parts.append({"type": "input_image", "image_url": "data:" + media + ";base64," + data})
            else:
                raise _error(E.ACS_INTEGRATION_ERROR, "unsupported_input_block")
        result.append({"role": "user", "content": parts})
    return result


def normalise(response):
    """Map terminal Responses data to the existing ACS accounting envelope."""
    if not isinstance(response, dict):
        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_response_object")
    status = response.get("status")
    if status == "failed":
        raise _provider_error(0, response)
    if status not in ("completed", "incomplete"):
        raise _error(E.ACS_UPSTREAM_TRUNCATED, "missing_terminal_status")
    output = response.get("output", [])
    if not isinstance(output, list):
        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_output_list")
    blocks, refused = [], False
    for item in output:
        if not isinstance(item, dict):
            raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_output_item")
        if item.get("type") == "reasoning":
            # Never retain or expose reasoning content; count its presence only.
            blocks.append(SimpleNamespace(type="reasoning"))
        elif item.get("type") == "message":
            if item.get("status", "completed") not in ("completed", "incomplete"):
                raise _error(E.ACS_UPSTREAM_TRUNCATED, "unfinished_message")
            for part in item.get("content", []):
                if not isinstance(part, dict):
                    raise _error(E.ACS_UPSTREAM_INVALID_JSON, "invalid_output_block")
                if part.get("type") == "refusal":
                    refused = True
                elif part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    blocks.append(SimpleNamespace(type="text", text=part["text"]))
                else:
                    raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "unexpected_output_block")
        else:
            # ACS does not request tools. Never silently accept an unexpected call.
            raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "unexpected_output_item")
    reason = (response.get("incomplete_details") or {}).get("reason")
    stop = "end_turn"
    if refused or reason == "content_filter":
        stop = "refusal"
    elif status == "incomplete":
        if reason != "max_output_tokens":
            raise _error(E.ACS_UPSTREAM_TRUNCATED, "incomplete_response")
        stop = "max_tokens"
        if not blocks:
            blocks.append(SimpleNamespace(type="output_limit"))
    usage = response.get("usage") or {}
    usage = usage if isinstance(usage, dict) else {}
    ins, outs = usage.get("input_tokens_details") or {}, usage.get("output_tokens_details") or {}
    mapped = {"input_tokens": _number(usage.get("input_tokens")),
              "output_tokens": _number(usage.get("output_tokens"))}
    if isinstance(ins, dict) and _number(ins.get("cached_tokens")) is not None:
        mapped["cache_read_input_tokens"] = ins["cached_tokens"]
    if isinstance(outs, dict) and _number(outs.get("reasoning_tokens")) is not None:
        mapped["reasoning_tokens"] = outs["reasoning_tokens"]
    return SimpleNamespace(content=blocks, stop_reason=stop, usage=SimpleNamespace(**mapped))


class ResponsesClient:
    """Narrow facade: the wire is /v1/responses, not /v1/messages.

    Explicit method signatures intentionally reject Anthropic-only parameters.
    Each call owns and closes its httpx client and response, including failures.
    """
    def __init__(self, cfg, timeout_s, http_client_factory=None):
        self.url = endpoint(cfg.base_url)
        if not cfg.ok or not cfg.api_key:
            raise _error(E.ACS_UPSTREAM_NOT_CONFIGURED, "missing_key")
        self._key = cfg.api_key
        self._factory = http_client_factory or httpx.Client
        self.timeout = float(timeout_s)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise _error(E.ACS_INTEGRATION_ERROR, "invalid_timeout")
        self.transport = cfg.transport
        self.messages = self
        self.acs_sdk_version = "httpx/" + httpx.__version__ + ";responses/1"

    def __repr__(self):
        return "<ResponsesClient provider=openai endpoint=api.openai.com>"

    def _payload(self, model, max_tokens, system, messages, stream):
        effort = os.environ.get("ACS_OPENAI_REASONING_EFFORT", "low").strip().lower()
        if effort not in ("none", "low", "medium", "high", "xhigh"):
            raise _error(E.ACS_INTEGRATION_ERROR, "invalid_reasoning_effort")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
            raise _error(E.ACS_INTEGRATION_ERROR, "invalid_output_budget")
        return {"model": model, "instructions": system,
                "input": _input(messages), "max_output_tokens": max_tokens,
                "stream": stream, "store": False,
                "text": {"format": {"type": "json_object"}},
                "reasoning": {"effort": effort}}

    def _bytes(self, response, deadline, limit):
        count = 0
        for chunk in response.iter_bytes(chunk_size=16384):
            if time.monotonic() > deadline:
                raise _error(E.ACS_UPSTREAM_TIMEOUT, "deadline")
            count += len(chunk)
            if count > limit:
                raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "response_size_limit")
            yield chunk

    def _events(self, response, deadline):
        # Parse bytes, not iter_lines(): a hostile line cannot allocate without a bound.
        pending, data, size, events = b"", [], 0, 0
        for chunk in self._bytes(response, deadline, MAX_STREAM_BYTES):
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                line = line.rstrip(b"\r")
                if len(line) > MAX_RESPONSE_BYTES:
                    raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "event_size_limit")
                if not line:
                    if data:
                        events += 1
                        if events > MAX_EVENTS:
                            raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "event_count_limit")
                        raw = b"\n".join(data)
                        if raw != b"[DONE]":
                            yield _json(raw)
                    data, size = [], 0
                elif line.startswith(b"data:"):
                    value = line[5:].lstrip(b" ")
                    size += len(value)
                    if size > MAX_RESPONSE_BYTES:
                        raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "event_size_limit")
                    data.append(value)
            if len(pending) > MAX_RESPONSE_BYTES:
                raise _error(E.ACS_UPSTREAM_BAD_REQUEST, "event_size_limit")
        # SSE must terminate a dispatched event. No partial delta salvage at EOF.

    def _request(self, model, max_tokens, system, messages, streaming):
        payload = self._payload(model, max_tokens, system, messages, streaming)
        deadline, received = time.monotonic() + self.timeout, False
        try:
            with self._factory(timeout=httpx.Timeout(min(self.timeout, 30.0)),
                               follow_redirects=False, trust_env=False) as client:
                with client.stream("POST", self.url,
                                   headers={"Authorization": "Bearer " + self._key,
                                            "Content-Type": "application/json"},
                                   json=payload) as response:
                    if response.status_code != 200:
                        raw = b"".join(self._bytes(response, deadline, MAX_RESPONSE_BYTES))
                        try:
                            body = json.loads(raw)
                        except (ValueError, UnicodeError):
                            body = {}
                        raise _provider_error(response.status_code, body)
                    received = True  # HTTP 200 is evidence the provider accepted the request.
                    if not streaming:
                        return normalise(_json(b"".join(self._bytes(response, deadline, MAX_RESPONSE_BYTES))))
                    if "text/event-stream" not in response.headers.get("content-type", ""):
                        raise _error(E.ACS_UPSTREAM_INVALID_JSON, "expected_event_stream")
                    for event in self._events(response, deadline):
                        received = True
                        kind = event.get("type")
                        if kind == "error":
                            raise _provider_error(0, event)
                        if kind in TERMINAL:
                            data = event.get("response")
                            if not isinstance(data, dict) or data.get("status") != TERMINAL[kind]:
                                raise _error(E.ACS_UPSTREAM_TRUNCATED, "terminal_status_mismatch")
                            return normalise(data)
                    raise _error(E.ACS_UPSTREAM_TRUNCATED, "stream_without_terminal_event")
        except httpx.TimeoutException:
            raise _error(E.ACS_UPSTREAM_TIMEOUT, "timeout") from None
        except httpx.TransportError:
            # A connection lost after a response began is not safe to duplicate.
            code = E.ACS_UPSTREAM_TRUNCATED if received else E.ACS_UPSTREAM_CONNECTION
            raise _error(code, "transport_interrupted") from None

    @contextmanager
    def stream(self, *, model, max_tokens, system, messages):
        result = self._request(model, max_tokens, system, messages, self.transport == "stream")
        yield SimpleNamespace(get_final_message=lambda: result)

    def create(self, *, model, max_tokens, system, messages):
        return self._request(model, max_tokens, system, messages, False)
