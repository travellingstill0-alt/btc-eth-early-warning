import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from context import flows
from exchange_flows import collect
from analysis import assess, plan, Rules
from test_analysis import fixture, NOW
from test_feed_context import payload, NOW as FEED_NOW
from test_exchange_flows import raw

spec = importlib.util.spec_from_file_location('flow_probe', Path(__file__).resolve().parents[1] / 'scripts/investigate_free_exchange_flows.py')
probe_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_module)

class FreeFlowResearchTests(unittest.TestCase):
    def test_daily_context_has_explicit_asset_units_and_never_certifies_coverage(self):
        for asset in ('btc', 'eth'):
            result = flows(payload(asset), asset, FEED_NOW, FEED_NOW)
            self.assertEqual(result['unit'], asset.upper())
            self.assertEqual(result['frequency'], '1d')
            self.assertFalse(result['coverage_verified'])
            self.assertFalse(result['safety_eligible'])
            self.assertEqual(result['safety_status'], 'UNAVAILABLE')
            self.assertEqual(result['rows'][-1]['net_inflow'], 0)

    def test_reserves_volume_other_assets_and_boolean_amounts_are_rejected(self):
        for asset in ('btc', 'eth'):
            for mutation in ('reserves', 'volume', 'wrong_asset', 'boolean'):
                body = payload(asset)
                row = body['data'][-1]
                if mutation in ('reserves', 'volume'):
                    row['reserve' if mutation == 'reserves' else 'volume'] = row.pop('FlowInExNtv')
                if mutation == 'wrong_asset': row['asset'] = 'btc' if asset == 'eth' else 'eth'
                if mutation == 'boolean': row['FlowInExNtv'] = True
                with self.subTest(asset=asset, mutation=mutation), self.assertRaises((ValueError, KeyError)):
                    flows(body, asset, FEED_NOW, FEED_NOW)

    def test_diagnostic_netflow_and_pagination_cannot_approve_source(self):
        body = raw()
        result = collect(lambda *a, **k: body, 'BTC', lambda: int(NOW.timestamp()*1000))
        self.assertEqual(result['observations'][-1]['net_inflow'], '6')
        self.assertEqual(result['safety_status'], 'UNAVAILABLE')
        body['next_page_token'] = 'more'
        self.assertEqual(collect(lambda *a, **k: body, 'BTC', lambda: int(NOW.timestamp()*1000))['status'], 'unavailable')

    def test_unavailable_flows_keep_unknown_and_observed_extreme_for_both_assets(self):
        for asset in ('BTC', 'ETH'):
            d = fixture(); d['symbol'] = asset+'USD'
            d['ticker']['priceChangePercent'] = '-8'
            d['funding']['lastFundingRate'] = '.001'
            d['interest']['openInterest'] = 120
            d['interest_history'][-1]['sumOpenInterest'] = 120
            d['exchange_flows'] = {'verified': True, 'safety_eligible': True, 'netflow': 0}
            result = assess(d, Rules(), NOW)
            self.assertEqual(result['observed_level'], 'EXTREME')
            self.assertEqual(result['overall_level'], 'UNKNOWN')
            self.assertIn('exchange flows', result['overall_missing'])
            self.assertEqual(plan(d, result, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_probe_records_429_and_rate_headers_without_retry_or_approval(self):
        response = Mock(status_code=429, url='https://api.llama.fi/example')
        response.headers = {'Content-Type': 'application/json', 'Retry-After': '60', 'X-RateLimit-Remaining': '0'}
        response.json.return_value = {'error': 'rate limit'}
        with patch.object(probe_module.requests, 'get', return_value=response) as get:
            report = probe_module.probe(('candidate', response.url, {}))
        get.assert_called_once()
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        self.assertEqual(report['headers']['Retry-After'], '60')
        self.assertEqual(report['http_status'], 429)
        self.assertFalse(report['safety_eligible'])

    def test_proxy_block_does_not_claim_publisher_failure_or_coverage(self):
        import requests
        with patch.object(probe_module.requests, 'get', side_effect=requests.exceptions.ProxyError('CONNECT 403')):
            result = probe_module.probe(('DefiLlama', 'https://api.llama.fi/protocol/binance-cex', {}))
        self.assertIn('CONNECT 403', result['error'])
        self.assertNotIn('http_status', result)
        self.assertFalse(result['coverage_verified'])
