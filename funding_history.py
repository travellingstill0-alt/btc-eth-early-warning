"""Verified native-period funding snapshots, persisted independently of strategies."""
import math
import os
from pathlib import Path
import sqlite3

PERIODS={('Kraken Futures','PF_XBTUSD'):1,('Kraken Futures','PF_ETHUSD'):1,
         ('Deribit','BTC-PERPETUAL'):8,('Deribit','ETH-PERPETUAL'):8}


def observation(data,now_ms,max_age=180):
    value,source=data['funding'],data['sources']['funding']
    key=source['provider'],source['instrument']
    time=source['source_time_ms'];rate=float(value['lastFundingRate']);period=value['period_hours']
    if key not in PERIODS or PERIODS[key]!=period or source['timestamp_kind']!='server snapshot':
        raise ValueError('Unverified funding provider, contract, period or timestamp type')
    allowed={'BTC':('PF_XBTUSD','BTC-PERPETUAL'),'ETH':('PF_ETHUSD','ETH-PERPETUAL')}
    if key[1] not in allowed.get(data['symbol'][:3],()):
        raise ValueError('Wrong funding asset')
    if not isinstance(time,int) or time<=0 or value['time']!=time or not -5000<=now_ms-time<=max_age*1000 or not math.isfinite(rate):
        raise ValueError('Missing, stale, future or inconsistent funding observation')
    return dict(provider=key[0],instrument=key[1],period_hours=period,timestamp=time,
                rate_fraction=rate,received_at_ms=now_ms,timestamp_kind=source['timestamp_kind'],
                note='Server snapshot; field-specific update time unavailable')


def preserve(data,now_ms,max_age=180,path=None):
    item=observation(data,now_ms,max_age)
    path=Path(path or os.environ.get('FUNDING_HISTORY_DB_PATH','data/funding_snapshots.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    key=(item['provider'],item['instrument'],item['period_hours'],item['timestamp'])
    with sqlite3.connect(path,timeout=10) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS funding_snapshots (provider TEXT,instrument TEXT,period_hours INTEGER,timestamp INTEGER,rate_fraction REAL,received_at_ms INTEGER,timestamp_kind TEXT,PRIMARY KEY(provider,instrument,period_hours,timestamp))')
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT rate_fraction FROM funding_snapshots WHERE provider=? AND instrument=? AND period_hours=? AND timestamp=?',key).fetchone()
        if old and old[0]!=item['rate_fraction']:raise ValueError('Conflicting funding value for source timestamp')
        db.execute('INSERT OR IGNORE INTO funding_snapshots VALUES (?,?,?,?,?,?,?)',(*key,item['rate_fraction'],item['received_at_ms'],item['timestamp_kind']))
    return item
