"""Offline causal entry/exit comparisons; no search, fitting, orders or alerts."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment import aggregate,signals,run_group,simulate
from confirmation_research import retest_signals,regime_map,diagnostics,regime_metrics,seconds
from historical_context import features,confirms,normalize
from scripts.run_experiment import csv_write


def verify_manifest(root):
    manifest=json.loads((root/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Archived input changed: '+name)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cfg=json.loads((args.root/'config.json').read_text());base=Path(cfg['baseline_artifact']);verify_manifest(base)
    if hashlib.sha256((base/'config.json').read_bytes()).hexdigest()!=cfg['baseline_config_sha256']:raise ValueError('Baseline config changed')
    baseline=json.loads((base/'config.json').read_text());instruments=json.loads((base/'probe-1.json').read_text())['payload']['instruments']
    args.output.mkdir(parents=True,exist_ok=False)
    start,end=seconds(baseline['research_start']),seconds(baseline['research_end_exclusive'])
    main_folds=[('development',start,seconds(baseline['development_end'])),('validation',seconds(baseline['development_end']),seconds(baseline['validation_end'])),('chronological_test',seconds(baseline['validation_end']),end)]
    walk_folds=[(f'walk_forward_{n}',start+n*7*86400,start+(n+1)*7*86400) for n in (1,2,3)]
    ledger=[];reports=[];regimes=[];diagnostic_rows=[];skips=[];feature_rows=[];blocked=[]
    originals={t['trade_id']:t for family in ('main','walk_forward') for t in json.loads((base/'results'/(family+'-ledger.json')).read_text())}
    matched=set();retest_sets={};asset_data={}
    for asset,symbol in baseline['instruments'].items():
        minutes=json.loads((base/'data'/symbol/'candles.json').read_text());minute_map={r['time']:r for r in minutes}
        funding_rows=json.loads((base/'data'/symbol/'funding.json').read_text());funding={r['time']:r['fundingRate'] for r in funding_rows}
        funding_features={r['time']:dict(r,availability_verified=False,available_at=None) for r in funding_rows}
        contexts={}
        for kind in ('cvd','open-interest'):
            folder=args.root/'context-history'/symbol/kind;manifest=json.loads((folder/'manifest.json').read_text());checked=[]
            for attempt in manifest['attempts']:
                if 'error' in attempt:continue
                raw=folder/attempt['file']
                if hashlib.sha256(raw.read_bytes()).hexdigest()!=attempt['sha256']:raise ValueError('Context raw hash mismatch')
                checked.extend(normalize(kind,json.loads(raw.read_text()),attempt['params']['since'],attempt['params']['to']))
            if checked!=json.loads((folder/'records.json').read_text()):raise ValueError('Context normalization mismatch')
            contexts[kind]={r['time']:r for r in checked}
        instrument=next(i for i in instruments if i['symbol']==symbol)
        asset_data[asset]=(minutes,funding,instrument)
        for horizon,step in baseline['signal_seconds'].items():
            bars=aggregate(minutes,step);original_signals=signals(bars)
            retests=retest_signals(bars,original_signals,cfg['retest']['maximum_wait_signal_bars']);retest_sets[(asset,horizon)]=len(retests)
            regime_lookup=regime_map(bars,horizon,cfg['regimes']);qualified=[]
            for s in retests:
                f=features(minute_map,contexts['cvd'],contexts['open-interest'],funding_features,s['signal_time'],step,cfg['context'])
                eligible=confirms(f,s['side'],cfg['context'])
                feature_rows.append(dict(asset=asset,horizon=horizon,direction=s['side'],signal_timestamp=s['signal_time'],eligible_verified_context=eligible,**f))
                if eligible:qualified.append(s)
            for variant in cfg['variants']:
                selected=original_signals if variant['entry']=='breakout' else retests if variant['entry']=='confirmed_retest' else qualified
                config=copy.deepcopy(baseline)
                config['take_profit']['risk_multiple']=variant['target_r']
                config['timeout_seconds'][horizon]=int(baseline['timeout_seconds'][horizon]*variant['timeout_multiplier'])
                if variant['id']!='baseline_unchanged':config['version']=cfg['version']+'-'+variant['id']
                signal_lookup={(s['side'],s['signal_time']):s for s in selected}
                for scenario in baseline['cost_scenarios']:
                    for family,folds in [('main',main_folds),('walk_forward',walk_folds)]:
                        for name,left,right in folds:
                            for side in ('LONG','SHORT'):
                                identity=dict(strategy=variant['id'],family=family,asset=asset,direction=side,horizon=horizon,scenario=scenario['name'],partition=name)
                                if variant['entry']=='confirmed_retest_with_verified_context' and not qualified:
                                    blocked.append(dict(**identity,status='NOT_EVALUATED',reason='No verified original as-of CVD/OI/funding availability; do not interpret as zero-trade profitability.'))
                                    continue
                                trades,omitted,equity,info=run_group(minutes,funding,selected,side,horizon,scenario,config,instrument,left,right,name,asset)
                                for n,t in enumerate(trades):
                                    original_id=f'{asset}-{side}-{horizon}-{scenario["name"]}-{name}-{n+1}'
                                    t['trade_id']=original_id if variant['id']=='baseline_unchanged' else variant['id']+'-'+original_id
                                    if variant['id']=='baseline_unchanged':
                                        expected=originals[t['trade_id']]
                                        if any(t.get(k)!=v for k,v in expected.items()):raise ValueError('Baseline ledger changed')
                                        matched.add(t['trade_id'])
                                    t.update(strategy=variant['id'],family=family,**regime_lookup[seconds(t['signal_timestamp'])])
                                    s=signal_lookup[(side,seconds(t['signal_timestamp']))]
                                    t['breakout_signal_timestamp']=s.get('breakout_signal_time',s['signal_time'])
                                    t['retest_level']=s.get('retest_level');t['confirmation_delay_bars']=s.get('confirmation_delay_bars',0)
                                    diagnostic_rows.append(diagnostics(minutes,t,step))
                                ledger.extend(trades);reports.append(dict(strategy=variant['id'],family=family,**info))
                                regimes.extend(dict(**identity,**m) for m in regime_metrics(trades,equity,config['position']['initial_equity_usd']))
                                skips.extend(dict(**identity,**s) for s in omitted)
    if matched!=set(originals):raise ValueError('Baseline trade coverage differs')
    # Exit-only counterfactuals keep exactly the baseline entries and suppress re-entry.
    # This distinguishes changed exit economics from changed trading frequency.
    paired=[];pair_skips=[]
    for t in (row for row in ledger if row['strategy']=='baseline_unchanged'):
        minutes,funding,instrument=asset_data[t['asset']]
        scenario=next(v for v in baseline['cost_scenarios'] if v['name']==t['scenario'])
        signal=dict(signal_time=seconds(t['signal_timestamp']),side=t['direction'],reference_entry=t['reference_entry'],stop=t['stop_loss'])
        for variant in (v for v in cfg['variants'] if v['id'] in ('half_r_target_v1','half_timeout_v1')):
            alternate,reason,_=simulate(minutes,funding,signal,int(baseline['timeout_seconds'][t['horizon']]*variant['timeout_multiplier']),scenario,baseline['position'],instrument['tickSize'],instrument['contractValueTradePrecision'],variant['target_r'])
            if reason:
                pair_skips.append(dict(baseline_trade_id=t['trade_id'],strategy=variant['id'],reason=reason));continue
            alternate.update(asset=t['asset'],direction=t['direction'],horizon=t['horizon'],scenario=t['scenario'],partition=t['partition'],family=t['family'],strategy=variant['id'],regime=t['regime'],baseline_trade_id=t['trade_id'],baseline_net_pnl_usd=t['net_pnl_usd'],delta_net_pnl_usd=alternate['net_pnl_usd']-t['net_pnl_usd'],baseline_exit_reason=t['exit_reason'],comparison_mode='forced_baseline_entries_no_reentry',simulation_only=True)
            paired.append(alternate)
    (args.output/'paired-exit-ledger.json').write_text(json.dumps(paired,indent=2,allow_nan=False)+'\n')
    csv_write(args.output/'paired-exit-ledger.csv',paired)
    (args.output/'paired-exit-skips.json').write_text(json.dumps(pair_skips,indent=2)+'\n')
    for name,rows in [('ledger',ledger),('metrics',reports),('regime-metrics',regimes),('trade-diagnostics',diagnostic_rows),('skipped-signals',skips)]:
        (args.output/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n');csv_write(args.output/(name+'.csv'),rows)
    (args.output/'context-feature-audit.json').write_text(json.dumps(feature_rows,indent=2,allow_nan=False)+'\n')
    (args.output/'blocked-comparisons.json').write_text(json.dumps(blocked,indent=2)+'\n')
    verification=dict(baseline_trades_identically_reproduced=len(matched),main_and_walk_forward_ledgers_not_additive=True,retest_candidates={str(k):v for k,v in retest_sets.items()},full_context_qualified=sum(f['eligible_verified_context'] for f in feature_rows))
    (args.output/'baseline-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    sources=['experiment.py','confirmation_research.py','historical_context.py','scripts/run_confirmation_research.py','scripts/collect_historical_context.py']
    inputs=dict(config_sha256=hashlib.sha256((args.root/'config.json').read_bytes()).hexdigest(),source_sha256={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in sources},baseline_manifest_sha256=hashlib.sha256((base/'manifest.json').read_bytes()).hexdigest(),context_sha256={str(p.relative_to(args.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((args.root/'context-history').rglob('*.json'))})
    (args.output/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print(verification,'simulation rows',len(ledger),'blocked groups',len(blocked))
if __name__=='__main__':main()
