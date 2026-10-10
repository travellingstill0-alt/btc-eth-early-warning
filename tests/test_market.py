import unittest
from unittest.mock import patch
import requests
from market import fetch, validate

class MarketTests(unittest.TestCase):
    def test_malformed_and_nonfinite_responses_rejected(self):
        for value in ({}, {'symbol': 'BTCUSDT', 'lastPrice': 'NaN'},
                      {'symbol': 'ETHUSDT', 'lastPrice': '100'}):
            with self.assertRaises(ValueError):
                validate('ticker', value, 'BTCUSDT')
        with self.assertRaises(ValueError):
            validate('candles', [[0]], 'BTCUSDT')
        with self.assertRaises(ValueError):
            validate('trades', [{'T': 1, 'q': '1', 'm': 'false'}], 'BTCUSDT')

    def test_failures_isolated_and_recovery_uses_new_values(self):
        def response(base, path, **params):
            if path.endswith('openInterest'):
                return {'symbol': params['symbol'], 'openInterest': '42', 'time': 100}
            raise requests.Timeout('test timeout')
        with patch('market.get', side_effect=response):
            data = fetch('BTCUSDT')
        self.assertEqual(data['interest']['openInterest'], '42')
        self.assertEqual(len(data['errors']), 6)
        self.assertEqual(len(data['source_retrieved_at']), 7)
        with patch('market.get', side_effect=requests.Timeout('test timeout')):
            failed = fetch('BTCUSDT')
        self.assertNotIn('interest', failed)
        self.assertEqual(len(failed['errors']), 7)
        self.assertGreaterEqual(failed['retrieved_at'], data['retrieved_at'])

    def test_invalid_payload_is_unavailable(self):
        with patch('market.get', return_value={'code': -1, 'msg': 'error'}):
            data = fetch('ETHUSDT')
        self.assertEqual(len(data['errors']), 7)
        self.assertNotIn('ticker', data)
