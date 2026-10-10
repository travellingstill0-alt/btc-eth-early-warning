import unittest
from unittest.mock import Mock, patch
import requests
from diagnostics import failure_details
from scripts.check_public_providers import probe, candidates


class DiagnosticsTests(unittest.TestCase):
    def test_policy_block_is_not_a_provider_restriction(self):
        exc = requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden')
        result = failure_details(exc)
        self.assertEqual(result['category'], 'network_policy_blocked')
        self.assertIsNone(result['http_status'])
        self.assertEqual(failure_details(requests.exceptions.ProxyError('connection refused'))['category'], 'proxy_unavailable')

    def test_http_failures_preserve_status(self):
        for status, expected in [(451, 'provider_restricted'), (403, 'http_access_denied'), (429, 'rate_limited')]:
            response = Mock(status_code=status)
            self.assertEqual(failure_details(requests.HTTPError(response=response))['category'], expected)
            self.assertEqual(failure_details(requests.HTTPError(response=response))['http_status'], status)

    def test_probe_failure_is_timestamped_and_unusable(self):
        with patch('scripts.check_public_providers.requests.get', side_effect=requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden')):
            result = probe(candidates()[0])
        self.assertEqual(result['category'], 'network_policy_blocked')
        self.assertFalse(result['usable_for_dashboard'])
        self.assertIn('completed_at_utc', result)

    def test_success_is_observation_not_automatic_provider_selection(self):
        response = Mock(status_code=200)
        response.json.return_value = {'result': {'last': '100'}}
        with patch('scripts.check_public_providers.requests.get', return_value=response) as request:
            result = probe(candidates()[0])
        self.assertEqual(result['status'], 'http_json_received_not_integrated')
        self.assertFalse(result['usable_for_dashboard'])
        self.assertFalse(request.call_args.kwargs['allow_redirects'])

    def test_invalid_success_payload_preserves_http_200(self):
        response = Mock(status_code=200)
        response.json.return_value = {'error': ['invalid market']}
        with patch('scripts.check_public_providers.requests.get', return_value=response):
            result = probe(candidates()[0])
        self.assertEqual(result['http_status'], 200)
        self.assertEqual(result['category'], 'invalid_payload')
        self.assertFalse(result['usable_for_dashboard'])

    def test_redirect_is_not_followed(self):
        response = Mock(status_code=302)
        with patch('scripts.check_public_providers.requests.get', return_value=response):
            result = probe(candidates()[0])
        self.assertEqual(result['status'], 'unexpected_http_status')
        response.json.assert_not_called()
