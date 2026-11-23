"""Endpoint identity is distinct from API protocol; no provider calls are made."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_provider as P


class ProviderIdentity(unittest.TestCase):
    def config(self, **env):
        return patch.dict(os.environ, {'ACS_LLM_API_KEY': 'synthetic-only', **env}, clear=True)

    def test_compatibility_alias_does_not_claim_anthropic_model(self):
        with self.config(ACS_LLM_PROVIDER='anthropic', ACS_LLM_BASE_URL='https://api.deepseek.com/anthropic', ACS_LLM_MODEL='claude-sonnet-5'):
            h = P.health_status()
            self.assertEqual(h['llm_api_protocol'], 'anthropic-messages')
            self.assertEqual(h['llm_actual_provider'], 'deepseek')
            self.assertEqual(h['llm_requested_model'], 'claude-sonnet-5')
            self.assertEqual(h['llm_resolved_model'], 'deepseek-flash')
            self.assertEqual(h['llm_endpoint_path'], '/anthropic')
            self.assertEqual(h['llm_model_identity_basis'], 'DOCUMENTED_ALIAS_MAPPING')
            self.assertFalse(h['provider_call_verified'])
            self.assertFalse(h['capabilities']['output_tokens_are_content_proxy'])
            self.assertGreaterEqual(h['capabilities']['content_token_multiplier'], 2)

    def test_sdk_legacy_endpoint_is_resolved_before_routing(self):
        with self.config(ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic', ACS_LLM_MODEL='claude-opus-5'):
            cfg = P.primary()
            self.assertEqual(cfg.base_url, 'https://api.deepseek.com/anthropic')
            self.assertEqual(P.health_status()['llm_resolved_model'], 'deepseek-v4-pro')
            self.assertFalse(P.capabilities(cfg)['output_tokens_are_content_proxy'])

    def test_arbitrary_host_or_model_is_not_given_measured_capabilities(self):
        for host, model in [('https://gateway.example.test/proxy', 'claude-sonnet-5'), ('https://api.anthropic.com', 'unmeasured-future-model')]:
            with self.subTest(host=host), self.config(ACS_LLM_BASE_URL=host, ACS_LLM_MODEL=model):
                h = P.health_status()
                self.assertEqual(h['llm_capability_profile'], 'unknown-conservative')
                self.assertFalse(h['capabilities']['output_tokens_are_content_proxy'])
                self.assertGreaterEqual(h['capabilities']['content_token_multiplier'], 2)

    def test_limits_follow_the_verified_endpoint_and_model(self):
        with self.config(ACS_LLM_PROVIDER='anthropic', ACS_LLM_BASE_URL='https://api.deepseek.com/anthropic', ACS_LLM_MODEL='claude-sonnet-5'):
            self.assertEqual(P.documented_max_output(), 384000)
        with self.config(ACS_LLM_PROVIDER='deepseek', ACS_LLM_BASE_URL='https://proxy.example.test/anthropic'):
            self.assertIsNone(P.documented_max_output())

    def test_route_profile_needs_exact_tls_origin_and_safe_path(self):
        for url in ('http://api.deepseek.com/anthropic', 'https://api.deepseek.com:4242/anthropic',
                    'https://api.deepseek.com/anthropic?mode=synthetic', 'https://api.deepseek.com/custom'):
            with self.subTest(url=url), self.config(ACS_LLM_BASE_URL=url, ACS_LLM_MODEL='claude-sonnet-5'):
                h = P.health_status()
                self.assertEqual(h['llm_capability_profile'], 'unknown-conservative')
                self.assertNotEqual(h['llm_model_identity_basis'], 'DOCUMENTED_ALIAS_MAPPING')

    def test_legacy_flash_model_is_disclosed_as_an_alias(self):
        with self.config(ACS_LLM_PROVIDER='deepseek', ACS_LLM_MODEL='deepseek-v4-flash'):
            h = P.health_status()
            self.assertEqual(h['llm_requested_model'], 'deepseek-v4-flash')
            self.assertEqual(h['llm_resolved_model'], 'deepseek-flash')
            self.assertEqual(h['llm_model_identity_basis'], 'DOCUMENTED_ALIAS_MAPPING')

    def test_endpoint_diagnostics_never_echo_query_or_userinfo(self):
        with self.config(ACS_LLM_BASE_URL='https://secret-user:secret-pass@api.deepseek.com/anthropic?token=secret-query#secret-fragment'):
            text = str(P.health_status()) + repr(P.primary())
            self.assertNotIn('secret-', text)
            self.assertNotIn('synthetic-only', text)


if __name__ == '__main__':
    unittest.main()
