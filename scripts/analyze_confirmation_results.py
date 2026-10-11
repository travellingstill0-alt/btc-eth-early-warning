"""Offline entry/exit audit, including equal-entry exit-rule counterfactuals."""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import mean,median
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment import aggregate
from scripts.run_experiment import csv_write


def seconds(value):return int(datetime.fromisoformat(value).timestamp())


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((args.root/'config.json').read_text());base=Path(cfg['baseline_artifact']);basecfg=json.loads((base/'config.json').read_text())
    ledger=json.loads((args.root/'results/ledger.json').read_text());diags=json.loads((args.root/'results/trade-diagnostics.json').read_text());diagmap={r['trade_id']:r for r in diags}
    bars={};indices={}
    for asset,symbol in basecfg['instruments'].items():
        minutes=json.loads((base/'data'/symbol/'candles.json').read_text())
        for horizon,step in basecfg['signal_seconds'].items():
            rows=aggregate(minutes,step);bars[(asset,horizon)]=rows;indices[(asset,horizon)]={r['end']:i for i,r in enumerate(rows)}
    entries=[];groups=defaultdict(list)
    for t in ledger:
        key=(t['asset'],t['horizon']);rows=bars[key];i=indices[key][t['breakout_signal_timestamp']]
        prior,breakout=rows[i-20:i],rows[i]
        sign=1 if t['direction']=='LONG' else -1
        edge=max(r['high'] for r in prior) if sign==1 else min(r['low'] for r in prior)
        atr=t['atr_fraction']*rows[indices[key][seconds(t['signal_timestamp'])]]['close']
        d=diagmap[t['trade_id']]
        rec=dict(trade_id=t['trade_id'],asset=t['asset'],direction=t['direction'],horizon=t['horizon'],scenario=t['scenario'],partition=t['partition'],family=t['family'],strategy=t['strategy'],regime=t['regime'],
                 original_breakout_protrusion_pct=sign*(breakout['close']-edge)/breakout['close']*100,
                 original_breakout_volume_multiple=breakout['volume']/mean(r['volume'] for r in prior) if any(r['volume'] for r in prior) else None,
                 target_in_signal_atr=abs(t['take_profit']-t['entry_price'])/atr if atr else None,
                 stop_in_signal_atr=abs(t['entry_price']-t['stop_loss'])/atr if atr else None,
                 raw_next_open_gap_bps=sign*(t['raw_entry_price']/t['reference_entry']-1)*10000,
                 confirmation_delay_bars=t['confirmation_delay_bars'],entry_features_signal_close=seconds(t['signal_timestamp']),
                 **{k:d[k] for k in ('mfe_lower_pct','mfe_upper_pct','mae_lower_pct','target_distance_pct','stop_distance_pct','mfe_to_target_lower','mfe_to_target_upper','holding_seconds','exit_reason','time_to_mfe_candidate_interval_start_seconds','time_to_mfe_candidate_interval_end_seconds','time_to_mfe_interval_verified','realized_cost_hurdle_pct')})
        entries.append(rec);groups[tuple(rec[k] for k in ('strategy','family','asset','direction','horizon','scenario','partition'))].append(rec)
    summary=[]
    for key,items in groups.items():
        times=[(r['time_to_mfe_candidate_interval_start_seconds']+r['time_to_mfe_candidate_interval_end_seconds'])/2 for r in items if r['time_to_mfe_interval_verified']]
        def med(field):
            vals=[r[field] for r in items if r[field] is not None]
            return median(vals) if vals else None
        summary.append(dict(zip(('strategy','family','asset','direction','horizon','scenario','partition'),key),trade_count=len(items),
                            median_target_pct=med('target_distance_pct'),median_stop_pct=med('stop_distance_pct'),median_target_atr=med('target_in_signal_atr'),
                            median_mfe_lower_pct=med('mfe_lower_pct'),median_mfe_upper_pct=med('mfe_upper_pct'),median_mae_lower_pct=med('mae_lower_pct'),
                            median_mfe_to_target_lower=med('mfe_to_target_lower'),median_mfe_to_target_upper=med('mfe_to_target_upper'),
                            median_time_to_mfe_interval_midpoint_seconds=median(times) if times else None,verified_peak_interval_count=len(times),
                            median_cost_hurdle_pct=med('realized_cost_hurdle_pct'),median_breakout_protrusion_pct=med('original_breakout_protrusion_pct'),
                            median_breakout_volume_multiple=med('original_breakout_volume_multiple'),
                            definitely_failed_to_cover_realized_cost_hurdle=sum(r['mfe_upper_pct']<r['realized_cost_hurdle_pct'] for r in items)))
    pairs=json.loads((args.root/'results/paired-exit-ledger.json').read_text());paired_groups=defaultdict(list)
    for r in pairs:paired_groups[tuple(r[k] for k in ('strategy','family','asset','direction','horizon','scenario','partition'))].append(r)
    paired_summary=[]
    for key,items in paired_groups.items():
        paired_summary.append(dict(zip(('strategy','family','asset','direction','horizon','scenario','partition'),key),paired_trades=len(items),
                                   mean_baseline_net_usd=mean(r['baseline_net_pnl_usd'] for r in items),mean_alternative_net_usd=mean(r['net_pnl_usd'] for r in items),
                                   mean_delta_net_usd=mean(r['delta_net_pnl_usd'] for r in items),baseline_timeout_pct=sum(r['baseline_exit_reason']=='TIMEOUT' for r in items)/len(items)*100,
                                   alternative_timeout_pct=sum(r['exit_reason']=='TIMEOUT' for r in items)/len(items)*100))
    for name,records in [('entry-exit-details',entries),('diagnostic-summary',summary),('paired-exit-summary',paired_summary)]:
        (args.output/(name+'.json')).write_text(json.dumps(records,indent=2,allow_nan=False)+'\n');csv_write(args.output/(name+'.csv'),records)
    inputs=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs_sha256={name:hashlib.sha256((args.root/name).read_bytes()).hexdigest() for name in ('config.json','results/ledger.json','results/trade-diagnostics.json','results/paired-exit-ledger.json')},
                note='Peak-time medians use midpoint of verified minute intervals only, not exact extrema timestamps. Cost hurdle is realized cost accounting, not an entry filter.')
    (args.output/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
if __name__=='__main__':main()
