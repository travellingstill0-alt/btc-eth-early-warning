import copy
from datetime import datetime, timezone
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import requests
from market import fetch, timestamp
from analysis import Rules, assess, plan, REQUIRED_CONTEXT
from oi_history import SnapshotStore, point

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
MS = int(NOW.timestamp() * 1000)


class Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')
    def json(self):
        return copy.deepcopy(self.body)


def response(url, params, timeout):
    if url.endswith('/ticker') and 'coinbase' in url:
        return Response(dict(price='100', volume='10', time=NOW.isoformat()))
    if url.endswith('/stats'):
        return Response(dict(open='99'))
    if url.endswith('/Ticker'):
        return Response({'error': [], 'result': {'PAIR': {'c': ['100'], 'v': ['5', '10'], 'o': '50'}}})
    if url.endswith('/Trades'):
        return Response({'error': [], 'result': {'PAIR': [['100', '2', MS / 1000, 'b'], ['100', '1', MS / 1000, 's']], 'last': 'cursor'}})
    if url.endswith('/trades'):
        return Response([dict(time=NOW.isoformat(), size='2', side='sell'), dict(time=NOW.isoformat(), size='1', side='buy')])
    if url.endswith('/OHLC') or url.endswith('/candles'):
        step = params.get('granularity', params.get('interval', 0) * 60)
        rows = [[MS // 1000 - (50-i)*step, '100', '110', '90', '100', '100', '10', 2] for i in range(50)]
        if url.endswith('/OHLC'):
            return Response({'error': [], 'result': {'PAIR': rows, 'last': 0}})
        return Response([[r[0], r[3], r[2], r[1], r[4], r[6]] for r in reversed(rows)])
    if url.endswith('/tickers'):
        return Response({'result': 'success', 'serverTime': NOW.isoformat(), 'tickers': [
            dict(symbol=s, openInterest=123, relativeFundingRate=0.00001) for s in ('PF_XBTUSD', 'PF_ETHUSD')]})
    if url.endswith('/open-interest'):
        return Response({'result': {'timestamp': [MS // 1000 - (1445-i)*60 for i in range(1445)],
                                     'data': [['123']*4 for _ in range(1445)]}, 'errors': []})
    if 'deribit' in url:
        return Response({'result': dict(state='open', timestamp=MS, open_interest=12300, funding_8h=0.00008)})
    raise AssertionError(url)


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.history_path = Path(self.temp.name) / 'oi.sqlite3'

    def fetch(self, handler=response, symbol='BTCUSD'):
        with patch('market.requests.get', side_effect=handler):
            return fetch(symbol, now=NOW, history_path=self.history_path)

    def test_valid_iso_timestamp_accepts_microseconds(self):
        self.assertEqual(timestamp('2026-10-10T00:00:00.123456Z'), MS + 123)

    def test_fractional_trade_seconds_remain_valid(self):
        def fractional(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/Trades'):
                for trade in r.body['result']['PAIR']:
                    trade[2] -= 0.0005
            return r
        d = self.fetch(fractional)
        self.assertEqual(d['sources']['trades']['provider'], 'Kraken')

    def test_invalid_primary_timestamps_use_safe_fallback(self):
        for invalid in (123, None, [], {}, '', 'invalid', '2026-10-10T00:00:00',
                        '9999-99-99T00:00:00Z'):
            with self.subTest(timestamp=invalid):
                def bad(url, **kwargs):
                    r = response(url, **kwargs)
                    if url.endswith('/tickers'):
                        r.body['serverTime'] = invalid
                    if 'coinbase' in url and url.endswith('/ticker'):
                        r.body['time'] = invalid
                    return r
                d = self.fetch(bad)
                self.assertEqual(d['sources']['ticker']['provider'], 'Kraken')
                self.assertEqual(d['sources']['interest']['provider'], 'Deribit')
                self.assertEqual(plan(d, assess(d, Rules(), NOW), 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_invalid_primary_and_secondary_timestamps_fail_closed(self):
        for invalid in (None, True, float('nan'), float('inf'), 1e300, -1, MS + 0.5):
            with self.subTest(timestamp=invalid):
                def bad(url, **kwargs):
                    r = response(url, **kwargs)
                    if url.endswith('/tickers'):
                        r.body['serverTime'] = 123
                    if 'deribit' in url:
                        r.body['result']['timestamp'] = invalid
                    return r
                d = self.fetch(bad)
                self.assertNotIn('interest', d)
                self.assertNotIn('funding', d)
                self.assertEqual(plan(d, assess(d, Rules(), NOW), 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_primary_providers_and_verified_history(self):
        for symbol in ('BTCUSD', 'ETHUSD'):
            with self.subTest(symbol=symbol):
                d = self.fetch(symbol=symbol)
                self.assertEqual(d['sources']['ticker']['provider'], 'Coinbase')
                self.assertEqual(d['ticker']['baseVolume'], 10)
                self.assertEqual(d['sources']['candles']['provider'], 'Kraken')
                self.assertEqual(d['sources']['funding']['provider'], 'Kraken Futures')
                self.assertEqual(d['interest']['unit'], symbol[:3])
                self.assertEqual(d['funding']['period_hours'], 1)
                self.assertIn('interest_history', d)
                self.assertEqual(d['sources']['interest_history']['provider'], 'Kraken Futures')
                self.assertEqual(d['oi_changes']['24h']['change_pct'], 0)
                self.assertEqual(sum(t['q'] * (-1 if t['m'] else 1) for t in d['trades']), 1)
                risk = assess(d, Rules(), NOW)
                self.assertEqual(risk['missing'], sorted(REQUIRED_CONTEXT))
                for horizon in ('SCALP', 'DAY TRADE'):
                    self.assertEqual(plan(d, risk, horizon, True, NOW)['status'], 'NO TRADE')

    def test_http_failure_uses_fallbacks_with_native_units(self):
        def fail(url, **kwargs):
            if 'coinbase' in url and url.endswith(('/ticker', '/stats')) or url.endswith('/tickers'):
                return Response({}, 503)
            return response(url, **kwargs)
        d = self.fetch(fail)
        self.assertEqual(d['sources']['ticker']['provider'], 'Kraken')
        self.assertIsNone(d['ticker']['priceChangePercent'])
        self.assertEqual(d['sources']['interest']['provider'], 'Deribit')
        self.assertEqual(d['interest']['unit'], 'USD')
        self.assertEqual(d['funding']['period_hours'], 8)
        self.assertIn('24h price change', assess(d, Rules(), NOW)['missing'])
        self.assertTrue(any(a['http_status'] == 503 for a in d['attempts']))
        self.assertEqual(len(d['interest_history']), 1)
        self.assertIsNone(d['oi_changes']['15m']['change_pct'])
        self.assertFalse(any('open-interest' in a['url'] for a in d['attempts']))

    def test_one_malformed_derivative_field_does_not_discard_other(self):
        def malformed(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/tickers'):
                for t in r.body['tickers']:
                    t['openInterest'] = 'NaN'
            return r
        d = self.fetch(malformed)
        self.assertEqual(d['sources']['interest']['provider'], 'Deribit')
        self.assertEqual(d['sources']['funding']['provider'], 'Kraken Futures')

    def test_stale_or_future_primary_falls_back(self):
        for offset in (-600_000, 60_000):
            def aged(url, **kwargs):
                r = response(url, **kwargs)
                if 'coinbase' in url and url.endswith('/ticker'):
                    r.body['time'] = datetime.fromtimestamp((MS + offset)/1000, timezone.utc).isoformat()
                if url.endswith('/tickers'):
                    r.body['serverTime'] = datetime.fromtimestamp((MS + offset)/1000, timezone.utc).isoformat()
                return r
            d = self.fetch(aged)
            self.assertEqual(d['sources']['ticker']['provider'], 'Kraken')
            self.assertEqual(d['sources']['funding']['provider'], 'Deribit')

    def test_candle_and_trade_fallback_normalizes_order_and_sides(self):
        def fail(url, **kwargs):
            if url.endswith(('/OHLC', '/Trades')):
                raise requests.Timeout('source timed out')
            return response(url, **kwargs)
        d = self.fetch(fail)
        self.assertEqual(d['sources']['candles']['provider'], 'Coinbase')
        self.assertEqual(d['sources']['trades']['provider'], 'Coinbase')
        self.assertEqual(d['candles'][-1][2:6], [110, 90, 100, 10])
        self.assertEqual(sum(t['q'] * (-1 if t['m'] else 1) for t in d['trades']), 1)

    def test_history_endpoint_failure_uses_persistent_snapshots_and_blocks_warmup(self):
        def unavailable(url, **kwargs):
            if url.endswith('/open-interest'):
                return Response({}, 503)
            return response(url, **kwargs)
        d = self.fetch(unavailable)
        self.assertEqual(d['sources']['interest_history']['method'], 'persistent OI snapshots')
        self.assertEqual(len(d['interest_history']), 1)
        risk = assess(d, Rules(), NOW)
        self.assertTrue(risk['missing'])
        self.assertEqual(plan(d, risk, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_malformed_history_does_not_turn_current_oi_into_history(self):
        def malformed(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/open-interest'):
                r.body['result']['data'].pop()
            return r
        d = self.fetch(malformed)
        self.assertEqual(d['sources']['interest_history']['method'], 'persistent OI snapshots')
        self.assertIsNone(d['oi_changes']['4h']['change_pct'])

    def test_storage_failure_has_warning_and_remote_history_still_works(self):
        self.history_path.mkdir()
        d = self.fetch()
        self.assertIn('oi_storage', d['errors'])
        self.assertEqual(d['oi_changes']['24h']['change_pct'], 0)

    def test_verified_stored_coverage_supports_outage_but_not_different_provider(self):
        for i in range(1441):
            ts = MS - (1440-i)*60000
            SnapshotStore(self.history_path).record_and_read(point(
                ('Kraken Futures', 'PF_XBTUSD', 'BTC'), ts, 123, ts, 'server snapshot'))
        def unavailable(url, **kwargs):
            if url.endswith('/open-interest'):
                return Response({}, 503)
            return response(url, **kwargs)
        d = self.fetch(unavailable)
        self.assertEqual(d['sources']['interest_history']['method'], 'persistent OI snapshots')
        self.assertEqual(assess(d, Rules(), NOW)['missing'], sorted(REQUIRED_CONTEXT))
        def failover(url, **kwargs):
            if url.endswith('/tickers'):
                return Response({}, 503)
            return response(url, **kwargs)
        d = self.fetch(failover)
        self.assertEqual(d['sources']['interest_history']['provider'], 'Deribit')
        self.assertEqual(len(d['interest_history']), 1)
        self.assertIsNone(d['oi_changes']['24h']['change_pct'])

    def test_gapped_candles_trigger_fallback(self):
        def gap(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/OHLC'):
                del r.body['result']['PAIR'][-5]
            return r
        self.assertEqual(self.fetch(gap)['sources']['scalp_candles']['provider'], 'Coinbase')

    def test_all_providers_unavailable_remain_missing(self):
        d = self.fetch(lambda *args, **kwargs: Response({}, 429))
        for key in ('ticker', 'candles', 'scalp_candles', 'interest', 'funding', 'trades'):
            self.assertNotIn(key, d)
        risk = assess(d, Rules(), NOW)
        self.assertEqual(plan(d, risk, 'SCALP', True, NOW)['status'], 'NO TRADE')
        self.assertTrue(d['warnings'])

    def test_stale_backups_are_not_accepted(self):
        def stale(url, **kwargs):
            r = response(url, **kwargs)
            if 'coinbase' in url and url.endswith('/ticker'):
                r.body['time'] = '2026-10-09T00:00:00Z'
            if url.endswith('/Trades'):
                for t in r.body['result']['PAIR']:
                    t[2] -= 600
            if url.endswith('/tickers'):
                r.body['serverTime'] = '2026-10-09T00:00:00Z'
            if 'deribit' in url:
                r.body['result']['timestamp'] -= 600_000
            return r
        d = self.fetch(stale)
        self.assertNotIn('ticker', d)
        self.assertNotIn('funding', d)
        self.assertNotIn('interest', d)

    def test_api_error_payload_is_failure_even_with_http_200(self):
        def fail(url, **kwargs):
            if url.endswith('/OHLC'):
                return Response({'error': ['EGeneral:Unavailable']})
            return response(url, **kwargs)
        self.assertEqual(self.fetch(fail)['sources']['candles']['provider'], 'Coinbase')

    def test_unknown_trade_side_is_not_guessed(self):
        def bad(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/Trades'):
                r.body['result']['PAIR'][0][3] = 'unknown'
            return r
        self.assertEqual(self.fetch(bad)['sources']['trades']['provider'], 'Coinbase')

    def test_negative_oi_and_impossible_candles_are_rejected(self):
        def bad(url, **kwargs):
            r = response(url, **kwargs)
            if url.endswith('/tickers'):
                for t in r.body['tickers']:
                    t['openInterest'] = -1
            if url.endswith('/OHLC'):
                r.body['result']['PAIR'][-1][2] = '1'
            return r
        d = self.fetch(bad)
        self.assertEqual(d['sources']['interest']['provider'], 'Deribit')
        self.assertEqual(d['sources']['candles']['provider'], 'Coinbase')
