"""Archive genuine historical analytics, keeping as-of availability unknown."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from historical_context import normalize


def collect(symbol,kind,start,end,out):
    folder=out/symbol/kind;folder.mkdir(parents=True,exist_ok=False)
    records=[];attempts=[]
    for n,left in enumerate(range(start,end,86400)):
        right=min(left+86400,end);url=f'https://futures.kraken.com/api/charts/v1/analytics/{symbol}/{kind}'
        params=dict(interval=60,since=left,to=right)
        attempt=dict(url=url,params=params,received_at=datetime.now(timezone.utc).isoformat())
        try:
            response=requests.get(url,params=params,timeout=20);attempt['http_status']=response.status_code
            name=f'raw-{n:03d}.json';(folder/name).write_bytes(response.content)
            attempt.update(file=name,sha256=hashlib.sha256(response.content).hexdigest());response.raise_for_status()
            chunk=normalize(kind,response.json(),left,right);records.extend(chunk)
        except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
            attempt['error']=str(exc)
        attempts.append(attempt)
    missing=sorted(set(range(start,end,60))-{r['time'] for r in records})
    (folder/'records.json').write_text(json.dumps(records,separators=(',',':'),allow_nan=False)+'\n')
    manifest=dict(provider='Kraken Futures',instrument=symbol,kind=kind,start=start,end=end,records=len(records),complete=not missing,
                  missing_timestamps=missing,original_asof_availability_verified=False,attempts=attempts)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(symbol,kind,len(records),'missing',len(missing),'errors',sum('error' in a for a in attempts))
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cfg=json.loads((args.baseline/'config.json').read_text())
    start=int(datetime.fromisoformat(cfg['research_start']).timestamp())-cfg['warmup_hours']*3600
    end=int(datetime.fromisoformat(cfg['research_end_exclusive']).timestamp())
    args.output.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(collect,s,k,start,end,args.output) for s in cfg['instruments'].values() for k in ('cvd','open-interest')]
        manifests=[j.result() for j in jobs]
    (args.output/'coverage.json').write_text(json.dumps(manifests,indent=2)+'\n')
if __name__=='__main__':main()
