import unittest
from datetime import datetime, timezone, timedelta
from analysis import Rules, assess, plan

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
MS = int(NOW.timestamp() * 1000)

def bars(step):
    return [[MS - (50-i)*step, '100', '110', '90', '100', '10', MS-(49-i)*step-1] for i in range(50)]

def fixture():
    return {'retrieved_at': NOW, 'ticker': {'priceChangePercent': '1', 'closeTime': MS},
            'funding': {'lastFundingRate': '0.0001', 'time': MS}, 'interest': {'time': MS},
            'interest_history': [{'sumOpenInterest': '100', 'timestamp': MS-86400000}, {'sumOpenInterest': '101', 'timestamp': MS}],
            'trades': [{'T': MS}], 'candles': bars(3600000), 'scalp_candles': bars(300000)}

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

if __name__ == '__main__':
    unittest.main()
