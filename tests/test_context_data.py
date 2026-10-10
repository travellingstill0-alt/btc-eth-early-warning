from copy import deepcopy
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from context_data import collect, parse, window, WINDOW_MS
from analysis import assess, plan, Rules
from test_analysis import fixture, MS, NOW
from test_market import response, Response
from market import fetch

START, END = window(MS)


def analytics(kind):
    times = list(range(START//1000, (END+1)//1000, 60))
    data = {'buy_volume': ['2']*15, 'sell_volume': ['1']*15, 'cvd': [str(i+1) for i in range(15)]} if kind == 'cvd' else ['0']*15
    return {'result': {'timestamp': times, 'data': data, 'more': False}, 'errors': []}


def item(kind='cvd'):
    return dict(kind=kind, provider='Kraken Futures', instrument='PF_XBTUSD', asset='BTC', unit='BTC',
                start_ms=START, end_ms=END, received_at_ms=MS, method='minute analytics', raw=analytics(kind))


def trades():
    return [dict(trade_seq=10+i, trade_id=str(i), timestamp=START+i*60000, instrument_name='BTC-PERPETUAL',
                 direction='buy' if i == 0 else 'sell', amount=10) for i in range(2)]


def history():
    return dict(result='success', serverTime=NOW.isoformat(), history=[
        dict(time=datetime.fromtimestamp(t/1000, timezone.utc).isoformat(), sequence_id=10+i, uid=str(i),
             size=1, type=kind) for i, (t, kind) in enumerate(
                 ((START-1, 'fill'), (START+1000, 'liquidation'), (END, 'partial liquidation')))])


class ContextTests(unittest.TestCase):
    def test_exact_cvd_and_reported_zero_liquidations_with_complete_buckets(self):
        self.assertEqual(parse(item(), MS)['value'], 15)
        self.assertEqual(parse(item('liquidations'), MS)['value'], 0)
        d = fixture(); d.update(symbol='BTCUSD', cvd=item(), liquidations=item('liquidations'))
        d['scalp_candles'][-1][4:6] = ['115', '20']
        r = assess(d, Rules(), NOW)
        self.assertEqual(r['missing'], ['exchange flows'])
        self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_gaps_duplicates_partial_future_and_malformed_bars_are_rejected(self):
        for mutation in ('gap', 'duplicate', 'future', 'fractional', 'partial', 'more', 'nan', 'negative', 'mismatch'):
            d = item(); raw = d['raw']['result']
            if mutation == 'gap': del raw['timestamp'][5]
            elif mutation == 'duplicate': raw['timestamp'][5] = raw['timestamp'][4]
            elif mutation == 'future': raw['timestamp'][-1] = MS//1000+60
            elif mutation == 'fractional': raw['timestamp'][0] += 0.5
            elif mutation == 'partial': d['end_ms'] = MS+59999
            elif mutation == 'more': raw['more'] = True
            elif mutation == 'nan': raw['data']['cvd'][0] = 'NaN'
            elif mutation == 'negative': raw['data']['buy_volume'][0] = '-1'
            elif mutation == 'mismatch': raw['data']['cvd'][-1] = '10000'
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, KeyError)):
                parse(d, MS)

    def test_active_bucket_is_excluded(self):
        d = item(); r = d['raw']['result'];r['timestamp'].append(MS//1000)
        r['data']['buy_volume'].append('100');r['data']['sell_volume'].append('0');r['data']['cvd'].append('115')
        self.assertEqual(parse(d, MS)['value'], 15)

    def test_liquidation_missing_negative_nonfinite_is_not_zero(self):
        for value in (None, '-1', 'NaN', 'Infinity'):
            d = item('liquidations'); d['raw']['result']['data'][3] = value
            with self.subTest(value=value), self.assertRaises(ValueError):parse(d, MS)

    def test_stale_cache_or_altered_identity_never_satisfies_context(self):
        for key, value in (('provider', 'Unknown'), ('unit', 'USD'), ('asset', 'ETH'), ('received_at_ms', MS+60000), ('method', 'estimate')):
            d = fixture(); d.update(symbol='BTCUSD', cvd=item());d['cvd'][key]=value
            self.assertIn('CVD', assess(d, Rules(), NOW)['missing'])
        d=fixture();d.update(symbol='BTCUSD',cvd=item(),liquidations=item('liquidations'))
        later=datetime.fromtimestamp((MS+181000)/1000, timezone.utc)
        self.assertIn('CVD',assess(d,Rules(),later)['missing'])
        self.assertIn('liquidation data',assess(d,Rules(),later)['missing'])
        d['cvd']['value']=0;d['cvd']['raw']['result']['data']['cvd'][-1]='999'
        self.assertIn('CVD',assess(d,Rules(),NOW)['missing'])

    def test_deribit_complete_tape_uses_native_usd_and_rejects_bad_coverage(self):
        d=item();d.update(provider='Deribit',instrument='BTC-PERPETUAL',unit='USD',method='complete trade history',
            raw=dict(result=dict(trades=trades(),has_more=False),response_times_ms=[MS]))
        self.assertEqual(parse(d,MS)['value'],0)
        for mutation in ('more','gap','duplicate','wrong_contract','outside','unknown_side','block','empty','stale_response'):
            bad=deepcopy(d);r=bad['raw']['result'];t=r['trades']
            if mutation=='more':r['has_more']=True
            elif mutation=='gap':t[1]['trade_seq']+=1
            elif mutation=='duplicate':t[1]['trade_id']=t[0]['trade_id']
            elif mutation=='wrong_contract':t[0]['instrument_name']='ETH-PERPETUAL'
            elif mutation=='outside':t[0]['timestamp']=START-1
            elif mutation=='unknown_side':t[0]['direction']='unknown'
            elif mutation=='block':t[0]['block_trade_id']='block'
            elif mutation=='empty':r['trades']=[]
            elif mutation=='stale_response':bad['raw']['response_times_ms']=[MS-181000]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):parse(bad,MS)

    def test_cvd_fallback_and_liquidation_secondary_require_full_coverage(self):
        def request(base,path,**params):
            if path.endswith('/cvd'):raise ValueError('503')
            if path.endswith('/liquidation-volume'):return analytics('liquidations')
            return dict(result=dict(trades=trades(),has_more=False),usOut=MS*1000)
        available, errors, warnings=collect(request,'BTC',lambda:MS)
        self.assertEqual(available['cvd']['provider'],'Deribit')
        self.assertEqual(available['cvd']['unit'],'USD')
        self.assertIn('cvd:primary',errors);self.assertTrue(warnings)
        def request_history(base,path,**params):
            if path.endswith('/liquidation-volume'):raise ValueError('503')
            if path.endswith('/history'):return history()
            return analytics('cvd')
        available,_,_=collect(request_history,'BTC',lambda:MS)
        self.assertEqual(parse(available['liquidations'],MS)['value'],2)

    def test_liquidation_history_gaps_unknown_types_and_absent_boundary_fail_closed(self):
        d=item('liquidations');d.update(method='complete execution history',raw=history())
        for mutation in ('gap','type','boundary','future_server'):
            bad=deepcopy(d);r=bad['raw'];t=r['history']
            if mutation=='gap':t[1]['sequence_id']+=3
            elif mutation=='type':t[1]['type']='unknown'
            elif mutation=='boundary':t[0]['time']=datetime.fromtimestamp(START/1000,timezone.utc).isoformat()
            elif mutation=='future_server':r['serverTime']='2027-01-01T00:00:00Z'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):parse(bad,MS)

    def test_deribit_saturated_range_is_split_without_skipping_boundary_trades(self):
        tape=trades();calls=[]
        def request(base,path,**params):
            if path.endswith('/cvd'):raise ValueError('503')
            if path.endswith('/liquidation-volume'):return analytics('liquidations')
            lo,hi=params['start_timestamp'],params['end_timestamp'];calls.append((lo,hi))
            rows=[t for t in tape if lo<=t['timestamp']<=hi]
            more=lo==START and hi==END
            return dict(result=dict(trades=rows,has_more=more),usOut=MS*1000)
        available,_,_=collect(request,'BTC',lambda:MS)
        self.assertEqual(parse(available['cvd'],MS)['count'],2)
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[1][1]+1,calls[2][0])

    def test_rate_limit_and_budget_exhaustion_do_not_assume_zero(self):
        def saturated(base,path,**params):
            if 'analytics' in path:raise ValueError('429')
            if path.endswith('/history'):raise ValueError('429')
            return dict(result=dict(trades=[],has_more=True),usOut=MS*1000)
        data,errors,warnings=collect(saturated,'BTC',lambda:MS)
        self.assertEqual(data,{})
        self.assertIn('budget',errors['cvd:fallback'])
        self.assertTrue(all('UNAVAILABLE' in w for w in warnings))

    def test_market_fetch_connects_verified_context_and_diagnostics(self):
        import tempfile
        def handler(url,**params):
            if url.endswith('/cvd'):return Response(analytics('cvd'))
            if url.endswith('/liquidation-volume'):return Response(analytics('liquidations'))
            return response(url,**params)
        with tempfile.TemporaryDirectory() as folder,patch('market.requests.get',side_effect=handler):
            data=fetch('BTCUSD',now=NOW,history_path=folder+'/oi.db')
        self.assertEqual(assess(data,Rules(),NOW)['missing'],['exchange flows'])
        self.assertEqual(data['sources']['cvd']['instrument'],'PF_XBTUSD')
        self.assertTrue(any(a['url'].endswith('/cvd') for a in data['attempts']))

    def test_overlapping_history_pages_are_deduplicated_without_conflict(self):
        tape=history()['history'];calls=[]
        def request(base,path,**params):
            if path.endswith('/cvd'):return analytics('cvd')
            if path.endswith('/liquidation-volume'):raise ValueError('503')
            calls.append(params['lastTime'])
            return dict(result='success',serverTime=NOW.isoformat(),history=tape[1:] if len(calls)==1 else tape[:2])
        available,_,_=collect(request,'BTC',lambda:MS)
        self.assertEqual(parse(available['liquidations'],MS)['value'],2)
        self.assertEqual(len(calls),2)

    def test_conflicting_history_pages_do_not_become_verified(self):
        tape=history()['history'];calls=[]
        def request(base,path,**params):
            if path.endswith('/cvd'):return analytics('cvd')
            if path.endswith('/liquidation-volume'):raise ValueError('503')
            calls.append(params['lastTime'])
            page=deepcopy(tape[1:] if len(calls)==1 else tape[:2])
            if len(calls)>1:page[-1]['size']=999
            return dict(result='success',serverTime=NOW.isoformat(),history=page)
        available,errors,_=collect(request,'BTC',lambda:MS)
        self.assertNotIn('liquidations',available)
        self.assertIn('Conflicting',errors['liquidations:fallback'])

    def test_malformed_provider_body_is_unavailable_without_crashing(self):
        available,_,warnings=collect(lambda *a,**k:[], 'BTC',lambda:MS)
        self.assertEqual(available,{})
        self.assertEqual(len(warnings),2)

    def test_camel_case_schema_and_aggregate_overflow(self):
        d=item();r=d['raw']['result']['data']
        r['buyVolume']=r.pop('buy_volume');r['sellVolume']=r.pop('sell_volume')
        self.assertEqual(parse(d,MS)['value'],15)
        d=item('liquidations');d['raw']['result']['data']=['1e308']*15
        with self.assertRaisesRegex(ValueError,'overflow'):parse(d,MS)
