"""Verified aligned perpetual price windows for independent CVD diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from context_data import bounds,integer
from scripts.collect_experiment_data import validate_candles


def parse(payload,now_ms,max_age=180):
    asset=payload['asset'];expected={'BTC':'PF_XBTUSD','ETH':'PF_ETHUSD'}.get(asset)
    if payload['provider']!='Kraken Futures' or payload['instrument']!=expected or payload['price_unit']!='USD' or payload['method']!='one-minute trade candles':
        raise ValueError('Unverified perpetual price identity')
    start,end=payload['start_ms'],payload['end_ms'];bounds(start,end,now_ms,max_age)
    if not -5000<=now_ms-integer(payload['received_at_ms'])<=max_age*1000:raise ValueError('Stale/future price receipt')
    raw=payload['raw']
    if raw.get('errors') or not isinstance(raw.get('candles'),list):raise ValueError('Price chart error/schema')
    rows=validate_candles(raw['candles'],start//1000,(end+1)//1000)
    return dict(change_pct=(rows[-1]['close']/rows[0]['open']-1)*100,first_open=rows[0]['open'],last_close=rows[-1]['close'],count=len(rows))


def collect(request,cvd_payload,clock,max_age=180):
    if cvd_payload['provider']!='Kraken Futures':raise ValueError('No validated same-contract price adapter for selected CVD provider')
    start,end=cvd_payload['start_ms'],cvd_payload['end_ms']
    raw=request('https://futures.kraken.com',f"/api/charts/v1/trade/{cvd_payload['instrument']}/1m",**{'from':start//1000,'to':(end+1)//1000})
    payload=dict(provider='Kraken Futures',instrument=cvd_payload['instrument'],asset=cvd_payload['asset'],price_unit='USD',method='one-minute trade candles',start_ms=start,end_ms=end,received_at_ms=clock(),raw=raw)
    parse(payload,clock(),max_age)
    return payload


def preserve(payload,now_ms,max_age=180,path=None):
    parse(payload,now_ms,max_age)
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False);digest=hashlib.sha256(encoded.encode()).hexdigest()
    path=Path(path or os.environ.get('PRICE_CONTEXT_DB_PATH','data/perpetual_price_windows.sqlite3'));path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path,timeout=10) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS price_windows (digest TEXT PRIMARY KEY,provider TEXT,instrument TEXT,start_ms INTEGER,end_ms INTEGER,received_ms INTEGER,payload TEXT)')
        db.execute('INSERT OR IGNORE INTO price_windows VALUES (?,?,?,?,?,?,?)',(digest,payload['provider'],payload['instrument'],payload['start_ms'],payload['end_ms'],payload['received_at_ms'],encoded))
    return digest
