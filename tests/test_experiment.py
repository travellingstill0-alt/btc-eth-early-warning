import unittest
from experiment import aggregate, signals, simulate, metrics, run_group
from scripts.collect_experiment_data import validate_candles


def minutes(n=60):
    return [dict(time=i*60,open=100.,high=101.,low=99.,close=100.,volume=10.) for i in range(n)]

SCENARIO=dict(name='test',fee_bps=5,slippage_bps_per_fill=2)
POSITION=dict(initial_equity_usd=10000,notional_cap_usd=1000)
SIGNAL=dict(signal_time=60,side='LONG',reference_entry=100.,stop=90.)

class ExperimentTests(unittest.TestCase):
    def test_next_open_fees_rounding_funding(self):
        rows=minutes();rows[1]['open']=100.1
        trade,skip,path=simulate(rows,{0:.01},SIGNAL,120,SCENARIO,POSITION,.01,4)
        self.assertIsNone(skip);self.assertGreaterEqual(trade['entry_price'],100.1*1.0002)
        self.assertAlmostEqual(trade['fees_usd'],trade['quantity']*(trade['entry_price']+trade['exit_price'])*.0005)
        self.assertAlmostEqual(trade['funding_cost_usd'],trade['quantity']*.01*120/3600)
        self.assertAlmostEqual(trade['net_pnl_usd'],trade['gross_pnl_usd']-trade['fees_usd']-trade['funding_cost_usd'])
        self.assertEqual(trade['exit_reason'],'TIMEOUT')
    def test_short_positive_funding_credit(self):
        trade,_,_=simulate(minutes(),{0:.01},dict(SIGNAL,side='SHORT',stop=110),120,SCENARIO,POSITION,.01,4)
        self.assertLess(trade['funding_cost_usd'],0)
    def test_collision_stop_first_bounds(self):
        rows=minutes();rows[1].update(high=120.,low=80.)
        trade,_,_=simulate(rows,{0:0},SIGNAL,120,dict(SCENARIO,fee_bps=0,slippage_bps_per_fill=0),POSITION,.01,4)
        self.assertEqual(trade['exit_reason'],'STOP');self.assertTrue(trade['ambiguous_stop_target'])
        self.assertEqual(trade['mfe_lower_pct'],0);self.assertEqual(trade['mfe_upper_pct'],20)
        self.assertEqual(trade['mae_lower_pct'],-20);self.assertEqual(trade['mae_upper_pct'],-10)
        self.assertFalse(trade['exit_timestamp_exact'])
    def test_gap_stop_before_later_high(self):
        rows=minutes();rows[2].update(open=85.,high=120.,low=80.,close=100.)
        trade,_,_=simulate(rows,{0:0},SIGNAL,180,dict(SCENARIO,slippage_bps_per_fill=0),POSITION,.01,4)
        self.assertEqual(trade['exit_reason'],'STOP_GAP');self.assertEqual(trade['raw_exit_price'],85)
        self.assertEqual(trade['mfe_upper_pct'],1);self.assertTrue(trade['exit_timestamp_exact'])
    def test_no_future_signal_dependency(self):
        bars=aggregate(minutes(150),300)
        bars[20].update(high=115.,close=115.,volume=100.)
        before=signals(bars[:21])
        bars[-1].update(high=99999.,close=99999.,volume=99999.)
        self.assertEqual(before,[s for s in signals(bars) if s['signal_time']<=bars[20]['end']])
    def test_aggregation_gap_rejected(self):
        rows=minutes(5);rows[2]['time']+=60
        with self.assertRaises(ValueError):aggregate(rows,300)
    def test_coverage_missing_rejected(self):
        with self.assertRaises(ValueError):validate_candles([dict(time=0,open=100,close=100,high=101,low=99,volume=1)],0,120)
    def test_funding_missing_rejected(self):
        with self.assertRaises(ValueError):simulate(minutes(),{},SIGNAL,120,SCENARIO,POSITION,.01,4)
    def test_boundary_purge_and_no_overlap(self):
        cfg=dict(position=POSITION,timeout_seconds={'SCALP':180},take_profit={'risk_multiple':1})
        signals_=[SIGNAL,dict(SIGNAL,signal_time=120),dict(SIGNAL,signal_time=540)]
        rows=minutes(10)
        trades,skips,_,_=run_group(rows,{0:0},signals_,'LONG','SCALP',SCENARIO,cfg,dict(symbol='test',tickSize=.01,contractValueTradePrecision=4),0,600,'test','BTC')
        self.assertEqual(len(trades),1)
        self.assertEqual({s['reason'] for s in skips},{'POSITION_ALREADY_OPEN','PURGED_MAX_HOLD_CROSSES_BOUNDARY'})
    def test_drawdown_includes_unrealized_loss(self):
        result=metrics([],[(0,10000),(60,9500),(120,10000)],10000)
        self.assertEqual(result['maximum_drawdown_pct'],5)
        self.assertIsNone(result['win_rate_pct'])
    def test_entry_gap_invalidates_levels(self):
        rows=minutes();rows[1].update(open=120.,high=121.,low=119.,close=120.)
        trade,skip,_=simulate(rows,{0:0},SIGNAL,120,SCENARIO,POSITION,.01,4)
        self.assertIsNone(trade);self.assertEqual(skip,'ENTRY_GAP_INVALIDATES_LEVELS')
