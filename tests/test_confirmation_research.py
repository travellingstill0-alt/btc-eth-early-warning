import unittest
from confirmation_research import retest_signals,regime_map,diagnostics
from historical_context import normalize,features,confirms
from experiment import signals,simulate


def bars():
    rows=[dict(time=i*300,end=(i+1)*300,open=100.,high=101.,low=99.,close=100.,volume=10.) for i in range(27)]
    rows[20].update(open=100.,high=104.,low=100.,close=103.,volume=30.)
    rows[21].update(open=102.,high=103.,low=101.,close=102.5)
    return rows

CTX=dict(minimum_completed_bar_lag_seconds=60,window_signal_bars=3,funding_threshold_pct_per_8h=.03)

class ConfirmationTests(unittest.TestCase):
    def test_long_support_higher_low_bullish_retest(self):
        rows=bars();original=signals(rows[:21]);out=retest_signals(rows,original)
        self.assertEqual(len(out),1);self.assertEqual(out[0]['signal_time'],rows[21]['end'])
        self.assertEqual(out[0]['stop'],original[0]['stop']);self.assertEqual(out[0]['confirmation_delay_bars'],1)
    def test_short_resistance_lower_high_bearish_retest(self):
        rows=bars()
        for b in rows:
            b.update(open=200-b['open'],close=200-b['close'],high=200-b['low'],low=200-b['high'])
        out=retest_signals(rows,signals(rows[:21]));self.assertEqual(out[0]['side'],'SHORT')
    def test_failed_hold_blocks_later_retest(self):
        rows=bars();rows[21]['close']=100
        rows[22].update(open=102,close=102.5,low=101,high=103)
        self.assertEqual(retest_signals(rows,signals(rows[:21])),[])
    def test_future_retest_not_used_early(self):
        rows=bars();original=signals(rows[:21]);earlier=retest_signals(rows[:22],original)
        rows[-1].update(close=200.,high=210.,volume=1000.)
        self.assertEqual(earlier,[s for s in retest_signals(rows,original) if s['signal_time']<=rows[21]['end']])
    def context(self):
        minutes={t:dict(time=t,open=100.,close=100.) for t in range(0,7260,60)}
        cvd={t:dict(time=t,interval_end=t+60,delta=1.,values_verified=True,availability_verified=True,available_at=t+60) for t in minutes}
        oi={t:dict(time=t,interval_end=t+60,open_interest=100+t/60,values_verified=True,availability_verified=True,available_at=t+60) for t in minutes}
        funding={0:dict(time=0,fundingRate=0.,relativeFundingRate=0.,availability_verified=True,available_at=3600)}
        return minutes,cvd,oi,funding
    def test_full_context_requires_verified_asof(self):
        data=self.context();f=features(*data,7200,300,CTX);self.assertTrue(confirms(f,'LONG',CTX))
        data[1][6300]['availability_verified']=False
        self.assertFalse(confirms(features(*data,7200,300,CTX),'LONG',CTX))
    def test_late_context_and_missing_bucket_block(self):
        data=self.context();data[2][6300]['available_at']=7201
        self.assertFalse(features(*data,7200,300,CTX)['asof_verified'])
        del data[1][6360];self.assertFalse(features(*data,7200,300,CTX)['values_available'])
    def test_future_funding_not_substituted(self):
        data=list(self.context());data[3]={7200:dict(time=7200,fundingRate=1.,relativeFundingRate=.01,available_at=7200,availability_verified=True)}
        self.assertFalse(features(*data,7200,300,CTX)['values_available'])
    def test_cvd_normalization_never_backdates_availability(self):
        payload=dict(errors=[],result=dict(more=False,timestamp=[0,60],data=dict(buy_volume=['2','3'],sell_volume=['1','1'],cvd=['1','3'])))
        out=normalize('cvd',payload,0,120)
        self.assertEqual(out[1]['delta'],2);self.assertIsNone(out[1]['available_at']);self.assertFalse(out[1]['availability_verified'])
        payload['result']['data']['cvd'][1]='999'
        with self.assertRaises(ValueError):normalize('cvd',payload,0,120)
    def test_regime_does_not_see_future(self):
        cfg=dict(lookback_completed_signal_bars=20,trend_efficiency_threshold=.3,high_volatility_atr_fraction={'SCALP':.0025})
        rows=bars();before=regime_map(rows[:22],'SCALP',cfg)
        rows[-1].update(close=999.,high=1000.)
        after=regime_map(rows,'SCALP',cfg)
        self.assertEqual(before,{k:v for k,v in after.items() if k<=rows[21]['end']})
    def test_time_to_mfe_gap_exit_point(self):
        minutes=[dict(time=i*60,open=100.,high=101.,low=99.,close=100.) for i in range(5)]
        minutes[2].update(open=115.,high=116.,low=114.,close=115.)
        t,_,_=simulate(minutes,{0:0},dict(signal_time=60,side='LONG',reference_entry=100.,stop=90.),180,dict(name='test',fee_bps=0,slippage_bps_per_fill=0),dict(notional_cap_usd=1000),.01,4)
        t.update(trade_id='test',asset='BTC',direction='LONG',horizon='SCALP',scenario='test',partition='test',strategy='test',regime='test')
        d=diagnostics(minutes,t,300)
        self.assertEqual(d['time_to_mfe_candidate_interval_start_seconds'],60)
        self.assertEqual(d['time_to_mfe_candidate_interval_end_seconds'],60)
        self.assertTrue(d['time_to_mfe_interval_verified'])
        self.assertIsNone(d['directional_return_at_300s_pct'])
