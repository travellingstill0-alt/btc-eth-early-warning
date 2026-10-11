import tempfile
from pathlib import Path
import sqlite3
import unittest
from funding_history import preserve,observation
from risk_warnings import warnings


def fixture():
    return dict(symbol='BTCUSD',funding=dict(time=100000,lastFundingRate=.001,period_hours=1),
                sources={'funding':dict(provider='Kraken Futures',instrument='PF_XBTUSD',source_time_ms=100000,timestamp_kind='server snapshot')})

class FundingTests(unittest.TestCase):
    def test_immutable_deduplicated(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'funding.sqlite3';data=fixture()
            preserve(data,100000,path=path);preserve(data,100000,path=path)
            with sqlite3.connect(path) as db:self.assertEqual(db.execute('SELECT count(*) FROM funding_snapshots').fetchone()[0],1)
            data['funding']['lastFundingRate']=.002
            with self.assertRaises(ValueError):preserve(data,100000,path=path)
    def test_stale_wrong_asset_period_nonfinite(self):
        with self.assertRaises(ValueError):observation(fixture(),1000000)
        for key,value in [('period_hours',8),('lastFundingRate',float('nan'))]:
            data=fixture();data['funding'][key]=value
            with self.assertRaises(ValueError):observation(data,100000)
        data=fixture();data['symbol']='ETHUSD'
        with self.assertRaises(ValueError):observation(data,100000)
    def test_independent_warning_uses_native_period(self):
        result=warnings(fixture(),100000)
        self.assertIn('EXTREME FUNDING WARNING',result['Funding extremes'])
        self.assertIn('UNAVAILABLE',result['Abnormal open interest'])
        self.assertIn('UNAVAILABLE',warnings({},100000)['Funding extremes'])
