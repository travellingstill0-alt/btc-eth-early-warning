import unittest
from datetime import datetime, timezone, timedelta
from analysis import Rules, assess, plan
from oi_history import point

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
MS = int(NOW.timestamp() * 1000)

def bars(step):
    return [[MS - (50-i)*step, '100', '110', '90', '100', '10', MS-(49-i)*step-1] for i in range(50)]

def fixture():
    data = {'retrieved_at': NOW,
            'sources': {key: {'source_time_ms': MS, 'provider': 'Test provider', 'instrument': 'Test instrument', 'timestamp_kind': 'test fixture'}
                        for key in ('ticker', 'funding', 'interest', 'trades', 'candles', 'scalp_candles')},
            'ticker': {'priceChangePercent': '1', 'closeTime': MS},
            'funding': {'lastFundingRate': '0.0001', 'time': MS}, 'interest': {'time': MS, 'openInterest': 101, 'unit': 'BTC'},
            'trades': [{'T': MS}], 'candles': bars(3600000), 'scalp_candles': bars(300000)}
    source = dict(provider='Kraken Futures', instrument='PF_XBTUSD', unit='BTC', source_time_ms=MS,
                  timestamp_kind='server snapshot', verified=True, method='test fixture')
    data['sources']['interest'] = source.copy()
    data['sources']['interest_history'] = source.copy()
    key = ('Kraken Futures', 'PF_XBTUSD', 'BTC')
    data['interest_history'] = [point(key, MS - (1440-i)*60000, 100 if i < 1440 else 101,
                                     MS - (1440-i)*60000, 'server snapshot') for i in range(1441)]
    return data

class AnalysisTests(unittest.TestCase):
    def test_complete_low_wait(self):
        d = fixture(); r = assess(d, Rules(), NOW)
        self.assertEqual(r['level'], 'LOW')
        self.assertEqual(r['missing'], [])
        self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'WAIT')
    def test_missing_blocks(self):
        d = fixture(); del d['funding']; r = assess(d, Rules(), NOW)
        self.assertIn('funding', r['missing'])
        self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')
    def test_extreme(self):
        d = fixture(); d['ticker']['priceChangePercent'] = '-8'; d['funding']['lastFundingRate'] = '-0.001'
        d['interest_history'][-1]['sumOpenInterest'] = '120'
        d['interest']['openInterest'] = 120
        self.assertEqual(assess(d, Rules(), NOW)['level'], 'EXTREME')
    def test_stale(self):
        d = fixture(); d['retrieved_at'] -= timedelta(minutes=4)
        self.assertIn('stale retrieval', assess(d, Rules(), NOW)['missing'])
    def test_macro_blocks(self):
        d = fixture(); r = assess(d, Rules(), NOW)
        self.assertEqual(plan(d, r, 'SCALP', False, NOW)['status'], 'NO TRADE')
    def test_confirmed_breakout(self):
        d = fixture(); d['scalp_candles'][-1][4] = '115'; d['scalp_candles'][-1][5] = '20'
        p = plan(d, assess(d, Rules(), NOW), 'SCALP', True, NOW)
        self.assertEqual(p['status'], 'ENTER'); self.assertEqual(p['invalidation'], 90)
        self.assertEqual(p['target_1'], 140)
    def test_unclosed_breakout_ignored(self):
        d = fixture(); d['scalp_candles'].append([MS, '100', '130', '90', '125', '100', MS+300000])
        self.assertEqual(plan(d, assess(d, Rules(), NOW), 'SCALP', True, NOW)['status'], 'WAIT')
    def test_funding_threshold_respects_hourly_and_eight_hour_periods(self):
        for period, rate in [(1, 0.00005), (8, 0.0004)]:
            d = fixture(); d['funding'].update(period_hours=period, lastFundingRate=rate)
            self.assertEqual(assess(d, Rules(), NOW)['score'], 2)
        d['funding']['period_hours'] = 0
        self.assertIn('unknown funding period', assess(d, Rules(), NOW)['missing'])
    def test_source_metadata_stale_missing_and_future_block_enter(self):
        for time in (MS - 200000, MS + 60000, None):
            d = fixture(); d['scalp_candles'][-1][4:6] = ['115', '20']
            d['sources'] = {k: {'source_time_ms': MS} for k in ('ticker', 'interest', 'funding', 'trades', 'candles', 'scalp_candles')}
            d['sources']['funding']['source_time_ms'] = time
            r = assess(d, Rules(), NOW)
            self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')
    def test_high_and_extreme_block_confirmed_breakout(self):
        for oi in (101, 120):
            d = fixture(); d['ticker']['priceChangePercent'] = 8
            d['funding']['lastFundingRate'] = 0.001
            d['interest_history'][-1]['sumOpenInterest'] = oi
            d['interest']['openInterest'] = oi
            d['scalp_candles'][-1][4:6] = ['115', '20']
            r = assess(d, Rules(), NOW)
            self.assertIn(r['level'], ('HIGH', 'EXTREME'))
            self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')

if __name__ == '__main__':
    unittest.main()
