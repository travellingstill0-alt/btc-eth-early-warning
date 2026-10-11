import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from price_context import parse,preserve,collect
from risk_warnings import warnings
from test_context_data import item,START,END,MS


def price():
    return dict(provider='Kraken Futures',instrument='PF_XBTUSD',asset='BTC',price_unit='USD',method='one-minute trade candles',
                start_ms=START,end_ms=END,received_at_ms=MS,
                raw={'candles':[dict(time=t,open='100',high='101',low='98',close='99',volume='10') for t in range(START,END+1,60000)]})

class PriceContextTests(unittest.TestCase):
    def test_aligned_verified_price_and_bullish_sign_divergence(self):
        p=price();self.assertEqual(parse(p,MS)['count'],15)
        self.assertAlmostEqual(parse(p,MS)['change_pct'],-1)
        data=dict(symbol='BTCUSD',cvd=item(),perpetual_price=p)
        self.assertIn('BULLISH PRICE-FLOW SIGN DIVERGENCE',warnings(data,MS)['CVD divergence'])
    def test_bearish_sign_divergence_without_performance_input(self):
        cvd=item();cvd['raw']['result']['data']=dict(buy_volume=['0']*15,sell_volume=['1']*15,cvd=[str(-i-1) for i in range(15)])
        p=price()
        for bar in p['raw']['candles']:bar.update(high='102',low='99',close='101')
        data=dict(symbol='BTCUSD',cvd=cvd,perpetual_price=p)
        before=warnings(data,MS)
        self.assertIn('BEARISH PRICE-FLOW SIGN DIVERGENCE',before['CVD divergence'])
        data['strategy_profit']=999999
        self.assertEqual(before,warnings(data,MS))
    def test_no_spot_or_cross_contract_substitution(self):
        data=dict(symbol='BTCUSD',cvd=item(),perpetual_price=price())
        data['perpetual_price']['instrument']='PF_ETHUSD'
        self.assertIn('UNAVAILABLE',warnings(data,MS)['CVD divergence'])
        data.pop('perpetual_price');data['ticker']={'priceChangePercent':'-1'}
        self.assertIn('UNAVAILABLE',warnings(data,MS)['CVD divergence'])
    def test_missing_stale_future_malformed_windows_rejected(self):
        for mutation in ('gap','stale','future','bad_price','bad_unit'):
            p=price()
            if mutation=='gap':p['raw']['candles'].pop(5)
            elif mutation=='stale':p['received_at_ms']=MS-181000
            elif mutation=='future':p['received_at_ms']=MS+6000
            elif mutation=='bad_price':p['raw']['candles'][0]['close']='nan'
            else:p['price_unit']='BTC'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):parse(p,MS)
    def test_transactional_dedup_invalid_never_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'prices.sqlite3';p=price()
            self.assertEqual(preserve(p,MS,path=path),preserve(p,MS,path=path))
            with sqlite3.connect(path) as db:self.assertEqual(db.execute('SELECT count(*) FROM price_windows').fetchone()[0],1)
            p['instrument']='spot'
            with self.assertRaises(ValueError):preserve(p,MS,path=path)
    def test_same_window_collection_and_unknown_provider_rejected(self):
        requests=[]
        def request(base,path,**params):requests.append((path,params));return price()['raw']
        p=collect(request,item(),lambda:MS)
        self.assertEqual(p['start_ms'],START);self.assertEqual(p['end_ms'],END)
        self.assertEqual(requests[0][1]['from'],START//1000)
        cvd=copy.deepcopy(item());cvd['provider']='Deribit'
        with self.assertRaises(ValueError):collect(request,cvd,lambda:MS)
