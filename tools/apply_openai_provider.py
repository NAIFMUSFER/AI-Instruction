"""One-shot guarded integration. Removed after verified product files are committed."""
from pathlib import Path


def replace(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit("anchor drift: " + path + " occurrences=" + str(text.count(old)))
    p.write_text(text.replace(old, new), encoding="utf-8")
    print("updated", path)


replace("acs_provider.py", 'PROVIDERS = ("anthropic", "deepseek")',
        'PROVIDERS = ("anthropic", "deepseek", "openai")')
replace("acs_provider.py", 'PROVIDER_SPEC = {\n', '''PROVIDER_SPEC = {
    # Native Responses API. Known model ceilings, checked 2026-09-11:
    # https://developers.openai.com/api/docs/models/gpt-5.4
    # https://developers.openai.com/api/docs/models/gpt-5.4-mini
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "requires_base_url": True,
        "models": ("gpt-5.4", "gpt-5.4-mini"),
        "documented_max_output": 128000,
        "legacy_key_env": "OPENAI_API_KEY",
        "key_prefix": None,
        "capabilities": {
            "output_tokens_are_content_proxy": False,
            # Conservative scheduling allowance, NOT a measured efficiency ratio.
            # Never increases the request budget or the declared model ceiling.
            "content_token_multiplier": 2.0,
        },
    },
''')
replace("acs_provider.py", '    key = clean_key(_env(prefix + "API_KEY"), name)\n', '''    # An existing ACS_LLM_API_KEY may belong to DeepSeek. OpenAI never
    # consumes it implicitly. Selectors contain NAMES only, never secret values.
    key_env = _env(prefix + "API_KEY_ENV")
    if name == "openai":
        if key_env and key_env != "OPENAI_API_KEY":
            return ProviderConfig(role, name, state=MISSING_KEY,
                                  missing=(prefix + "API_KEY_ENV",))
        key = clean_key(_env("OPENAI_API_KEY"), name)
    elif key_env:
        permitted = {"ACS_LLM_API_KEY", "ACS_LLM_FALLBACK_API_KEY"}
        permitted.add("DEEPSEEK_API_KEY" if name == "deepseek" else "ANTHROPIC_API_KEY")
        if key_env not in permitted:
            return ProviderConfig(role, name, state=MISSING_KEY,
                                  missing=(prefix + "API_KEY_ENV",))
        key = clean_key(_env(key_env), name)
    else:
        key = clean_key(_env(prefix + "API_KEY"), name)
''')
replace("acs_provider.py", '                          documented_max_output=spec["documented_max_output"],\n',
        '                          documented_max_output=(None if name == "openai" and model not in spec["models"]\n'
        '                                                 else spec["documented_max_output"]),\n')
replace("acs_provider.py", '    return (PROVIDER_SPEC.get(cfg.provider or "") or {}).get(\n        "documented_max_output")',
        '    if cfg.provider == "openai":\n        return cfg.documented_max_output\n'
        '    return (PROVIDER_SPEC.get(cfg.provider or "") or {}).get(\n        "documented_max_output")')
replace("acs_provider.py", '            "api_key_configured": bool(p.api_key),\n',
        '            "api_key_configured": bool(p.api_key),\n'
        '            "openai_key_configured": bool(clean_key(_env("OPENAI_API_KEY"), "openai")),\n')
replace("acs_understand.py", '''def _build_client(cfg, timeout_s):
    """عميلٌ مضبوطٌ على نقطة نهاية المزوّد المحلول. لا يخمّن ولا يتساهل."""
    import anthropic
''', '''def _build_client(cfg, timeout_s):
    """عميلٌ مضبوطٌ على نقطة نهاية المزوّد المحلول. لا يخمّن ولا يتساهل."""
    if cfg.provider == "openai":
        from acs_openai import ResponsesClient
        return ResponsesClient(cfg, timeout_s)
    import anthropic
''')
replace("acs_understand.py", '''        model = model_override or cfg.model
        client = _build_client(cfg, timeout_s)
''', '''        # A caller's primary-model override must not be sent to another provider.
        model = (model_override if cfg.role == "primary" else None) or cfg.model
        client = _build_client(cfg, timeout_s)
        sdk_ver = getattr(client, "acs_sdk_version", None) or _sdk_version()
        tel["sdk_version"] = sdk_ver
''')
replace("Dockerfile", 'COPY acs_api_errors.py acs_generation.py acs_plan_chunks.py acs_provider.py ./',
        'COPY acs_api_errors.py acs_generation.py acs_plan_chunks.py acs_provider.py acs_openai.py ./')
replace("tests/remediation/test_generation_spatial_context.py", '''    def test_residential_presentation_contract_remains_green(self):
        self._run(["node", "tests/remediation/test_residential_presentation.js"])
''', '''    def test_residential_presentation_contract_remains_green(self):
        self._run(["node", "tests/remediation/test_residential_presentation.js"])

    def test_native_openai_provider_contract_remains_green(self):
        self._run([sys.executable, "tests/remediation/test_openai_provider.py"])
''')
replace("acs_openai.py", '                    if not streaming:\n',
        '                    received = True  # HTTP 200 is evidence the provider accepted the request.\n'
        '                    if not streaming:\n')
replace("acs_openai.py", '    code = raw.get("code") or raw.get("type")\n', '''    code = raw.get("code") or raw.get("type")
    # Terminal SSE failures have no independent HTTP status. Classify only
    # known codes; an unknown terminal failure must not spend on a fallback.
    if status == 0:
        status = {"invalid_api_key": 401, "permission_denied": 403,
                  "model_not_found": 404, "rate_limit_exceeded": 429,
                  "insufficient_quota": 429, "server_error": 503}.get(code, 400)
''')
replace("acs_openai.py", '        raise _provider_error(502, response)',
        '        raise _provider_error(0, response)')
replace("acs_openai.py", '                            raise _provider_error(400, event)',
        '                            raise _provider_error(0, event)')
print("OpenAI native provider wired; no production settings changed")
