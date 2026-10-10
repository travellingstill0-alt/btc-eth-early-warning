import unittest
from exchange_flows import collect, inspect
from analysis import assess, plan, Rules
from test_analysis import fixture, NOW, MS


def raw():
    return {'data': [{'asset': 'btc', 'time': '2026-10-09T00:00:00Z',
                     'FlowInKRKNtv': '10', 'FlowOutKRKNtv': '4'},
                    {'asset': 'btc', 'time': '2026-10-08T00:00:00Z',
                     'FlowInKRKNtv': '0', 'FlowOutKRKNtv': '0'}]}


class ExchangeFlowsTests(unittest.TestCase):
    def test_labelled_daily_data_and_true_zero_are_diagnostics_only(self):
        result = collect(lambda *a, **k: raw(), 'BTC', lambda: MS)
        self.assertEqual(result['status'], 'diagnostic only')
        self.assertEqual(result['observations'][0]['inflow'], '0')
        self.assertFalse(result['verified'])
        self.assertFalse(result['safety_eligible'])
        self.assertFalse(result['timestamp_within_freshness'])

    def test_invalid_times_never_crash_collection(self):
        for stamp in (None, True, 0, 'bad', '2026-10-09',
                      '99999-10-09T00:00:00Z', '2026-10-11T00:00:00Z',
                      '2026-10-09T00:00:00.000001Z', '2026-10-09T01:00:00Z'):
            with self.subTest(stamp=stamp):
                body = raw(); body['data'][0]['time'] = stamp
                result = collect(lambda *a, **k: body, 'BTC', lambda: MS)
                self.assertEqual(result['status'], 'unavailable')
                self.assertFalse(result['safety_eligible'])

    def test_missing_negative_nonfinite_and_wrong_asset_rejected(self):
        for value in (None, True, '-1', 'NaN', 'Infinity', 'bad'):
            body = raw(); body['data'][0]['FlowInKRKNtv'] = value
            self.assertEqual(collect(lambda *a, **k: body, 'BTC', lambda: MS)['status'], 'unavailable')
        for mutation in ('missing', 'asset', 'empty', 'page', 'duplicate', 'gap', 'error'):
            body = raw()
            if mutation == 'missing': del body['data'][0]['FlowOutKRKNtv']
            if mutation == 'asset': body['data'][0]['asset'] = 'eth'
            if mutation == 'empty': body['data'] = []
            if mutation == 'page': body['next_page_url'] = 'https://untrusted.example'
            if mutation == 'duplicate': body['data'][1]['time'] = body['data'][0]['time']
            if mutation == 'gap': body['data'][1]['time'] = '2026-10-07T00:00:00Z'
            if mutation == 'error': body['error'] = 'access denied'
            self.assertEqual(collect(lambda *a, **k: body, 'BTC', lambda: MS)['status'], 'unavailable', mutation)

    def test_transport_failure_is_not_zero(self):
        def failure(*a, **k): raise ValueError('429 quota exceeded')
        result = collect(failure, 'ETH', lambda: MS)
        self.assertNotIn('observations', result)
        self.assertIn('429', result['error'])

    def test_fresh_timestamp_and_claimed_verification_cannot_unlock_enter(self):
        body = raw(); body['data'] = [dict(body['data'][0], time=NOW.isoformat())]
        result = collect(lambda *a, **k: body, 'BTC', lambda: MS)
        self.assertTrue(result['timestamp_within_freshness'])
        self.assertFalse(result['safety_eligible'])
        from test_context_data import item
        for payload in (result, dict(result, verified=True, safety_eligible=True),
                        {'provider': 'unknown', 'classification': 'proxy', 'value': 0}):
            d = fixture(); d.update(symbol='BTCUSD', cvd=item(), liquidations=item('liquidations'),
                                    exchange_flows=payload, exchange_flow_diagnostics=payload)
            risk = assess(d, Rules(), NOW)
            self.assertIn('exchange flows', risk['missing'])
            for horizon in ('SCALP', 'DAY TRADE'):
                self.assertEqual(plan(d, risk, horizon, True, NOW)['status'], 'NO TRADE')

    def test_eth_identity_and_timezone_normalization(self):
        body = raw()
        for row in body['data']:
            row['asset'] = 'eth'
            row['time'] = row['time'].replace('T00:00:00Z', 'T01:00:00+01:00')
        self.assertEqual(len(inspect(body, 'ETH', MS)['observations']), 2)
