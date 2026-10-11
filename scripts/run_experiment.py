"""Reproduce the frozen experiment from archived data, without network calls."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment import aggregate,signals,run_group
from scripts.collect_experiment_data import validate_candles


def epoch(value):return int(datetime.fromisoformat(value).timestamp())


def csv_write(path,rows):
    if not rows:
        path.write_text('');return
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    root=args.root;cfg=json.loads((root/'config.json').read_text());args.output.mkdir(parents=True,exist_ok=False)
    # Verify immutable inputs and the instrument-linked public fee schedule.
    instruments=json.loads((root/'probe-1.json').read_text())['payload']['instruments']
    schedules=json.loads((root/'probe-0.json').read_text())['payload']['feeSchedules']
    start,end=epoch(cfg['research_start']),epoch(cfg['research_end_exclusive'])
    partitions=[('development',start,epoch(cfg['development_end'])),('validation',epoch(cfg['development_end']),epoch(cfg['validation_end'])),('chronological_test',epoch(cfg['validation_end']),end)]
    week=7*86400
    walk=[(f'walk_forward_{n}',start+n*week,start+(n+1)*week) for n in (1,2,3)]
    ledgers={'main':[],'walk_forward':[]};summaries=[];skip_rows=[];equity_rows=[]
    for asset,symbol in cfg['instruments'].items():
        directory=root/'data'/symbol
        manifest=json.loads((directory/'manifest.json').read_text())
        if not manifest['complete']:raise ValueError('Incomplete dataset')
        raw_rows=[]
        for request in manifest['attempts']:
            path=directory/request['file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=request['sha256']:raise ValueError('Raw archive hash mismatch')
            if request['file'].startswith('candles-raw-'):
                lower,upper=request['params']['from']*1000,request['params']['to']*1000
                raw_rows.extend(r for r in json.loads(path.read_text())['candles'] if lower<=r['time']<upper)
        minutes=validate_candles(raw_rows,manifest['start'],manifest['end'])
        if minutes!=json.loads((directory/'candles.json').read_text()):raise ValueError('Normalized candles diverge from raw archive')
        funding_rows=json.loads((directory/'funding.json').read_text());funding={r['time']:r['fundingRate'] for r in funding_rows}
        raw_funding=json.loads((directory/'funding-raw.json').read_text())
        expected={epoch(r['timestamp']):float(r['fundingRate']) for r in raw_funding['rates'] if manifest['start']<=epoch(r['timestamp'])<manifest['end']}
        if funding!=expected:raise ValueError('Normalized funding diverges from raw archive')
        instrument=next(i for i in instruments if i['symbol']==symbol)
        schedule=next(s for s in schedules if s['uid']==instrument['feeScheduleUid'])
        tier=next(t for t in schedule['tiers'] if t['usdVolume']==0)
        # API fee fields are percent: 0.05 percent = 5 bps.
        if abs(tier['takerFee']*100-cfg['cost_scenarios'][0]['fee_bps'])>1e-9:raise ValueError('Fee assumption disagrees with linked base tier')
        for horizon,seconds in cfg['signal_seconds'].items():
            candidates=signals(aggregate(minutes,seconds),cfg['signal']['lookback_bars'],cfg['signal']['volume_multiplier'])
            for scenario in cfg['cost_scenarios']:
                for family,folds in [('main',partitions),('walk_forward',walk)]:
                    for name,left,right in folds:
                        for side in ('LONG','SHORT'):
                            trades,skips,equity,info=run_group(minutes,funding,candidates,side,horizon,scenario,cfg,instrument,left,right,name,asset)
                            for n,t in enumerate(trades):t['trade_id']=f'{asset}-{side}-{horizon}-{scenario["name"]}-{name}-{n+1}'
                            ledgers[family].extend(trades);summaries.append(dict(family=family,**info))
                            skip_rows.extend(dict(asset=asset,direction=side,horizon=horizon,scenario=scenario['name'],partition=name,**s) for s in skips)
                            equity_rows.extend(dict(asset=asset,direction=side,horizon=horizon,scenario=scenario['name'],partition=name,timestamp=t,equity_usd=v) for t,v in equity)
    for family,rows in ledgers.items():
        (args.output/(family+'-ledger.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
        csv_write(args.output/(family+'-ledger.csv'),rows)
    (args.output/'metrics.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
    csv_write(args.output/'metrics.csv',summaries);csv_write(args.output/'skipped-signals.csv',skip_rows);csv_write(args.output/'equity.csv',equity_rows)
    hashes={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [root/'config.json',*sorted((root/'data').rglob('*.json')),root/'probe-0.json',root/'probe-1.json']}
    (args.output/'inputs.json').write_text(json.dumps(dict(configuration=cfg,sha256=hashes,deterministic=True,source_sha256={name:hashlib.sha256((Path(__file__).resolve().parents[1]/name).read_bytes()).hexdigest() for name in ('experiment.py','scripts/run_experiment.py','scripts/collect_experiment_data.py')}),indent=2)+'\n')
    for info in summaries:
        if info['partition']=='chronological_test' and info['scenario']=='published_base':print(info['asset'],info['direction'],info['horizon'],info['trade_count'],round(info['net_pnl_usd'],2),info['profit_factor'])
if __name__=='__main__':main()
