"""Archive genuine Coinbase candles and original breakout candidates, not trades.

No execution/exit policy is invented. USD spot is not original Binance USDT.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import requests


def validate(rows, start, end, step):
    selected = {}
    for row in rows:
        if not isinstance(row, list) or len(row) != 6:
            raise ValueError('Unexpected candle schema')
        time, low, high, opened, close, volume = row
        if not isinstance(time, int) or time % step or any(not math.isfinite(v) for v in (low, high, opened, close, volume)):
            raise ValueError('Invalid candle timestamp or values')
        if not 0 < low <= min(opened, close) <= max(opened, close) <= high or volume < 0:
            raise ValueError('Invalid OHLCV')
        if start <= time < end:
            if time in selected and selected[time] != row:
                raise ValueError('Conflicting duplicate candle')
            selected[time] = row
    expected = range(start, end, step)
    missing = [t for t in expected if t not in selected]
    return [selected[t] for t in sorted(selected)], missing


def series(asset, step, start, end, output):
    product = asset + '-USD'
    begin = start-20*step
    directory = output/(product+'-'+str(step))
    directory.mkdir(parents=True, exist_ok=False)
    collected, attempts = [], []
    for number, lower in enumerate(range(begin, end, 250*step)):
        upper = min(lower+250*step, end)
        params = dict(granularity=step, start=datetime.fromtimestamp(lower, timezone.utc).isoformat(),
                      end=datetime.fromtimestamp(upper, timezone.utc).isoformat())
        attempt = dict(url=f'https://api.exchange.coinbase.com/products/{product}/candles', params=params,
                       retrieved_at=datetime.now(timezone.utc).isoformat())
        try:
            response = requests.get(attempt['url'], params=params, timeout=15)
            attempt['status'] = response.status_code
            raw = response.content
            name = f'raw-{number:03d}.json'
            (directory/name).write_bytes(raw)
            attempt.update(file=name, sha256=hashlib.sha256(raw).hexdigest())
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError('Expected candle list')
            collected.extend(payload)
        except (requests.RequestException, ValueError) as exc:
            attempt['error'] = str(exc)
        attempts.append(attempt)
    result = dict(asset=asset, product=product, provider='Coinbase Exchange', granularity=step,
                  research_start=start, research_end=end, warmup_start=begin, attempts=attempts,
                  original_instrument=False, note='USD spot; not Binance USDT or perpetual execution history')
    try:
        rows, missing = validate(collected, begin, end, step)
        result.update(rows=len(rows), missing_timestamps=missing, complete=not missing and not any('error' in a for a in attempts))
        (directory/'candles.json').write_text(json.dumps(rows)+'\n')
        candidates = []
        # Require contiguous exact coverage; no signals across gaps.
        if result['complete']:
            for i in range(20, len(rows)):
                last, reference = rows[i], rows[i-20:i]
                high, low = max(r[2] for r in reference), min(r[1] for r in reference)
                side = 'LONG' if last[4]>high else 'SHORT' if last[4]<low else None
                if side and last[5] > sum(r[5] for r in reference)/20*1.2:
                    distance = abs(last[4]-(low if side=='LONG' else high))
                    sign = 1 if side=='LONG' else -1
                    candidates.append(dict(asset=asset, direction=side, horizon='SCALP' if step==300 else 'DAY TRADE',
                                           signal_close_ms=(last[0]+step)*1000, reference_entry=last[4],
                                           stop=low if side=='LONG' else high,
                                           target_1=last[4]+sign*distance, target_2=last[4]+sign*distance*2,
                                           status='UNEXECUTED_CANDIDATE', risk_gate_evaluated=False))
        (directory/'signal-candidates.json').write_text(json.dumps(candidates,indent=2)+'\n')
        result['candidate_count'] = len(candidates)
        result['counts'] = {side:sum(c['direction']==side for c in candidates) for side in ('LONG','SHORT')}
    except (TypeError, ValueError) as exc:
        result.update(complete=False,error=str(exc))
    (directory/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    end=int(datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp())
    start=end-7*86400
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(series,asset,step,start,end,args.output) for asset in ('BTC','ETH') for step in (300,3600)]
        results=[f.result() for f in futures]
    (args.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    for r in results: print(r['asset'],r['granularity'],'complete',r['complete'],'rows',r.get('rows'),'candidates',r.get('counts'))
    return int(any(not r['complete'] for r in results))

if __name__=='__main__': raise SystemExit(main())
