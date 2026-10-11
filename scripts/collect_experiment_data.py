"""Read-only genuine Kraken Futures data archive; never fill historical gaps."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import requests


def epoch(value):
    return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp())


def request(url, path, params=None):
    if path.exists():
        raw=path.read_bytes()
        return json.loads(raw),dict(url=url,params=params,status=None,received_at=None,file=path.name,sha256=hashlib.sha256(raw).hexdigest(),reused_existing_raw=True,receipt_limit='First attempt receipt metadata unavailable; raw response preserved')
    response=requests.get(url,params=params,timeout=20)
    path.write_bytes(response.content)
    response.raise_for_status()
    return response.json(),dict(url=url,params=params,status=response.status_code,
        received_at=datetime.now(timezone.utc).isoformat(),file=path.name,sha256=hashlib.sha256(response.content).hexdigest())


def validate_candles(rows,start,end):
    selected={}
    for raw in rows:
        t=raw['time']
        if not isinstance(t,int) or t%60000:raise ValueError('Invalid candle boundary')
        values={k:float(raw[k]) for k in ('open','high','low','close','volume')}
        if any(not math.isfinite(v) for v in values.values()) or not 0<values['low']<=min(values['open'],values['close'])<=max(values['open'],values['close'])<=values['high'] or values['volume']<0:
            raise ValueError('Invalid OHLCV')
        if start*1000<=t<end*1000:
            row=dict(time=t//1000,**values)
            if t in selected and selected[t]!=row:raise ValueError('Conflicting candles')
            selected[t]=row
    missing=[t for t in range(start*1000,end*1000,60000) if t not in selected]
    if missing:raise ValueError(f'Missing {len(missing)} minutes, first {missing[:5]}')
    return [selected[t] for t in sorted(selected)]


def collect(asset,symbol,start,end,out):
    directory=out/symbol;directory.mkdir(exist_ok=True)
    if (directory/'manifest.json').exists():raise FileExistsError('Completed dataset is immutable; choose a new version')
    attempts=[];rows=[]
    for n,left in enumerate(range(start,end,86400)):
        payload,meta=request(f'https://futures.kraken.com/api/charts/v1/trade/{symbol}/1m',directory/f'candles-raw-{n:03d}.json',dict(**{'from':left},to=min(end,left+86400)))
        if not isinstance(payload.get('candles'),list):raise ValueError('Invalid chart schema')
        # The endpoint includes the upper boundary; each request owns [from,to).
        rows.extend(r for r in payload['candles'] if left*1000<=r['time']<min(end,left+86400)*1000);attempts.append(meta)
    candles=validate_candles(rows,start,end)
    (directory/'candles.json').write_text(json.dumps(candles,separators=(',',':'))+'\n')
    funding,meta=request('https://futures.kraken.com/derivatives/api/v4/historicalfundingrates',directory/'funding-raw.json',dict(symbol=symbol))
    attempts.append(meta)
    if funding.get('result')!='success' or not isinstance(funding.get('rates'),list):raise ValueError('Invalid funding schema')
    rates={}
    for r in funding['rates']:
        t=epoch(r['timestamp'])
        if t%3600:raise ValueError('Non-hourly funding timestamp')
        v=float(r['fundingRate'])
        relative=float(r['relativeFundingRate'])
        if not math.isfinite(v) or not math.isfinite(relative):raise ValueError('Invalid funding')
        if start<=t<end:
            item=dict(time=t,fundingRate=v,relativeFundingRate=relative)
            if t in rates and rates[t]!=item:raise ValueError('Conflicting funding')
            rates[t]=item
    expected=list(range(start//3600*3600,end,3600))
    if any(t not in rates for t in expected):raise ValueError('Missing historical funding hours')
    (directory/'funding.json').write_text(json.dumps([rates[t] for t in expected],separators=(',',':'))+'\n')
    manifest=dict(asset=asset,instrument=symbol,start=start,end=end,candle_count=len(candles),funding_count=len(rates),complete=True,attempts=attempts,
                  revision_limit='No original publication/as-of revision history; current historical exchange responses')
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(symbol,len(candles),'candles',len(rates),'funding hours')
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cfg=json.loads(args.config.read_text());start=epoch(cfg['research_start'])-cfg['warmup_hours']*3600;end=epoch(cfg['research_end_exclusive'])
    if end>datetime.now(timezone.utc).timestamp():raise ValueError('Research includes future data')
    args.output.mkdir(exist_ok=True,parents=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(collect,a,s,start,end,args.output) for a,s in cfg['instruments'].items()]
        manifests=[f.result() for f in futures]
    (args.output/'manifest.json').write_text(json.dumps(manifests,indent=2)+'\n')
if __name__=='__main__':main()
