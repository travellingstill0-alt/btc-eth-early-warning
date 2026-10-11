import unittest
from research import Costs, STRATEGIES, replay, entry_hypothesis


def bars():
    return [dict(time=i*60, end=(i+1)*60, open=100., high=102., low=98., close=100.) for i in range(5)]

class ReplayTests(unittest.TestCase):
    def test_next_open_and_two_sided_costs(self):
        b=bars(); b[0].update(high=150., close=140.); b[1].update(open=101., high=104.)
        r=replay(b,0,'LONG',95,110,1,Costs(10,5,'assumed stress case'))
        self.assertAlmostEqual(r['entry'],101*1.0005)
        self.assertAlmostEqual(r['fees'],(r['entry']+r['exit'])*.001)
        self.assertEqual(r['reason'],'TIMEOUT')
        self.assertEqual(r['bars_held'],1)
    def test_stop_first_collision(self):
        b=bars(); b[1].update(high=115.,low=85.)
        r=replay(b,0,'LONG',90,110,3,Costs(0,0,'frictionless diagnostic'))
        self.assertTrue(r['ambiguous']); self.assertEqual(r['exit'],90)
    def test_short_pnl(self):
        b=bars(); b[1].update(low=85.)
        r=replay(b,0,'SHORT',110,90,3,Costs(0,0,'diagnostic'))
        self.assertEqual(r['net_pnl'],10)
    def test_gap_stop(self):
        b=bars(); b[2].update(open=85.,low=80.,high=88.,close=84.)
        r=replay(b,0,'LONG',90,120,3,Costs(0,0,'diagnostic'))
        self.assertEqual(r['exit'],85)
    def test_censored_not_timeout(self):
        self.assertEqual(replay(bars(),0,'LONG',90,110,10,Costs(0,0,'diagnostic'))['reason'],'CENSORED')
    def test_gap_rejected(self):
        b=bars(); b[2]['time']+=1
        with self.assertRaises(ValueError): replay(b,0,'LONG',90,110,1,Costs(0,0,'diagnostic'))
    def test_eight_groups_and_missing_context(self):
        self.assertEqual(len(STRATEGIES),8)
        b=[dict(time=i*60,end=(i+1)*60,open=100.,high=110.,low=90.,close=100.) for i in range(27)]
        self.assertFalse(entry_hypothesis(b,'LONG',{})['eligible'])
    def test_future_context_rejected(self):
        b=[dict(time=i*60,end=(i+1)*60,open=100.,high=110.,low=90.,close=100.) for i in range(27)]
        context={'traded_contract':'PF_XBTUSD'}
        for k in ('cvd','oi','funding'):
            context[k]=dict(verified=True,available_at=99999,end=100,contract='PF_XBTUSD',value=1.)
        self.assertFalse(entry_hypothesis(b,'LONG',context)['conditions']['oi_funding_assessed'])
