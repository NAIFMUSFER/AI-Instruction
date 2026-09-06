"""Offline exit-code regression for the live verifier; no provider is called."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'live_generation_verdict_target', ROOT / 'tests/deploy/verify_backend_live.py')
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)


def envelope(code):
    return {'ok': False, 'error': {'code': code, 'message': 'synthetic failure',
            'request_id': 'req_offline_test', 'retryable': False, 'upstream': None}}


SUCCESS = {'ok': True, 'building': {'site': {'w': 20, 'd': 15},
           'levels': [{'index': 0, 'template': 'ground'}],
           'floors': {'ground': {'rooms': [
               {'id': 'storage', 'rect': [0, 0, 15, 15]},
               {'id': 'receiving', 'rect': [15, 0, 5, 15]}]}}},
           'generation': {'strategy': 'single', 'stop_reasons': ['end_turn']},
           'report': {}, 'model_validation': {'status': 'COMPLETED', 'issue_count': 0,
              'scopes': {'semantic': {'status': 'COMPLETED', 'findings': []},
                         'architecture': {'status': 'COMPLETED', 'findings': []}}}}


class LiveGenerationVerdict(unittest.TestCase):
    def run_verifier(self, status=200, payload=None, text=None, error=None,
                     generation=True):
        calls = []
        response_text = json.dumps(SUCCESS if payload is None else payload) \
            if text is None else text
        origin = 'https://frontend.example'
        health = {'ok': True, 'service': 'test', 'version': 'test',
                  'model_configured': 'test-model', 'api_key_configured': True,
                  'llm': {'llm_provider': 'test-provider', 'llm_model': 'test-model',
                          'llm_state': 'resolved', 'llm_base_host': 'model.example'}}

        def transport(base, path, method='GET', body=None, headers=None, timeout=60):
            headers = headers or {}
            out_headers = {'X-Request-ID': headers.get('X-Request-ID', 'req_offline_test')}
            if headers.get('Origin') == origin:
                out_headers['Access-Control-Allow-Origin'] = origin
                if method != 'OPTIONS':
                    out_headers['Access-Control-Expose-Headers'] = 'X-Request-ID, Retry-After'
            if method == 'OPTIONS':
                return 200, out_headers, '{}', None
            if path == '/v1/understand' and body and body.get('text', '').strip():
                calls.append(copy.deepcopy(body))
                return status, out_headers, response_text, error
            if path == '/health' and method == 'GET':
                result, code = health, 200
            elif path == '/ready':
                result, code = {'ok': True, 'ready': True}, 200
            elif path == '/':
                result, code = {'service': 'test'}, 200
            elif path == '/definitely-not-a-route':
                result, code = envelope('ACS_NOT_FOUND'), 404
            elif path == '/health':
                result, code = envelope('ACS_METHOD_NOT_ALLOWED'), 405
            elif path == '/v1/understand' and body == {}:
                result, code = envelope('ACS_VALIDATION_FAILED'), 422
            else:
                result, code = envelope('ACS_BAD_REQUEST'), 400
            return code, out_headers, json.dumps(result), None

        tls = MagicMock()
        tls.getpeercert.return_value = {'subject': 'synthetic certificate'}
        tls.version.return_value = 'TLSv1.3'
        ssl_context = MagicMock()
        ssl_context.wrap_socket.return_value.__enter__.return_value = tls
        argv = ['verify_backend_live.py', 'https://backend.example']
        if generation:
            argv.append('--generation')
        output = io.StringIO()
        LIVE.p[:] = [0]
        LIVE.f[:] = [0]
        LIVE.skipped[:] = []
        with patch.object(LIVE, 'request', side_effect=transport), \
             patch.object(LIVE.socket, 'getaddrinfo', return_value=[
                 (2, 1, 6, '', ('192.0.2.1', 443))]), \
             patch.object(LIVE.socket, 'create_connection', return_value=MagicMock()), \
             patch.object(LIVE.ssl, 'create_default_context', return_value=ssl_context), \
             patch.object(sys, 'argv', argv), \
             patch.dict(LIVE.os.environ, {'ACS_FRONTEND_ORIGIN': origin}), \
             contextlib.redirect_stdout(output):
            rc = LIVE.main()
        self.assertEqual(len(calls), 1 if generation else 0, 'no automatic resubmission')
        return rc, output.getvalue(), LIVE.f[0], list(LIVE.skipped)

    def test_free_mode_still_skips_generation(self):
        rc, output, failures, skipped = self.run_verifier(generation=False)
        self.assertEqual((rc, failures), (0, 0), output)
        self.assertEqual(skipped, ['end-to-end generation'])

    def test_successful_generation_passes(self):
        rc, output, failures, skipped = self.run_verifier()
        self.assertEqual((rc, failures, skipped), (0, 0, []), output)

    def assert_generation_fails(self, **kwargs):
        rc, output, failures, _ = self.run_verifier(**kwargs)
        self.assertEqual(rc, 1, output)
        self.assertGreater(failures, 0, output)

    def test_unavailable_backend_is_not_success(self):
        self.assert_generation_fails(status=503, payload=envelope('ACS_NOT_CONFIGURED'))

    def test_provider_failure_is_not_success(self):
        self.assert_generation_fails(status=502, payload=envelope('ACS_UPSTREAM_AUTH'))

    def test_rate_limited_generation_is_not_success(self):
        self.assert_generation_fails(status=429, payload=envelope('ACS_RATE_LIMITED'))

    def test_http_200_with_false_ok_is_not_success(self):
        payload = dict(SUCCESS, ok=False)
        self.assert_generation_fails(payload=payload)

    def test_http_200_without_ok_is_not_success(self):
        payload = dict(SUCCESS)
        payload.pop('ok')
        self.assert_generation_fails(payload=payload)

    def test_invalid_json_is_not_success(self):
        self.assert_generation_fails(text='<html>upstream unavailable</html>')

    def test_network_failure_is_not_success(self):
        self.assert_generation_fails(status=0, text='', error='TimeoutError: test')

    def test_empty_building_is_not_success(self):
        self.assert_generation_fails(payload=dict(SUCCESS, building={}))

    def test_missing_diagnostics_is_not_acceptance(self):
        payload = copy.deepcopy(SUCCESS)
        payload.pop('model_validation')
        self.assert_generation_fails(payload=payload)

    def test_failed_diagnostic_scope_is_not_acceptance(self):
        payload = copy.deepcopy(SUCCESS)
        payload['model_validation']['scopes']['architecture']['status'] = 'NOT_EVALUATED'
        self.assert_generation_fails(payload=payload)

    def test_reported_geometry_findings_fail_acceptance(self):
        payload = copy.deepcopy(SUCCESS)
        payload['model_validation']['issue_count'] = 7
        payload['model_validation']['scopes']['architecture']['findings'] = [
            {'code': 'WALL_NEGATIVE_THICKNESS', 'subject': 'L0.wall_%d' % i}
            for i in range(7)]
        self.assert_generation_fails(payload=payload)

    def test_zero_counter_cannot_hide_nonempty_findings(self):
        payload = copy.deepcopy(SUCCESS)
        payload['model_validation']['scopes']['architecture']['findings'] = [
            {'code': 'WALL_NEGATIVE_THICKNESS', 'subject': 'L0.wall_0'}]
        self.assert_generation_fails(payload=payload)

    def test_boolean_counter_is_not_zero_findings(self):
        payload = copy.deepcopy(SUCCESS)
        payload['model_validation']['issue_count'] = False
        self.assert_generation_fails(payload=payload)

    def test_malformed_diagnostics_fail_with_a_verdict(self):
        for diag in ('invalid', {'scopes': ['invalid']}, {'status': 'COMPLETED'}):
            with self.subTest(diag=diag):
                self.assert_generation_fails(payload=dict(SUCCESS, model_validation=diag))


if __name__ == '__main__':
    unittest.main(verbosity=2)
