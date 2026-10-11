"""Small frozen comparison set and causal diagnostics; baseline engine unchanged."""
from bisect import bisect_right
from datetime import datetime
from statistics import mean
from experiment import metrics


def seconds(value):return int(datetime.fromisoformat(value).timestamp())


def retest_signals(bars,candidates,maximum_wait=3):
    by_end={b['end']:i for i,b in enumerate(bars)};out=[];used=set()
    for original in candidates:
        i=by_end[original['signal_time']];long=original['side']=='LONG'
        reference=bars[i-20:i]
        level=max(b['high'] for b in reference) if long else min(b['low'] for b in reference)
        prior_low=min(b['low'] for b in bars[i-3:i]);prior_high=max(b['high'] for b in bars[i-3:i])
        for j in range(i+1,min(i+maximum_wait+1,len(bars))):
            b=bars[j]
            failed_hold=b['close']<level if long else b['close']>level
            if failed_hold:break
            condition=(b['low']<=level<b['close'] and b['close']>b['open'] and b['low']>prior_low) if long else (
                b['high']>=level>b['close'] and b['close']<b['open'] and b['high']<prior_high)
            if condition:
                key=(original['side'],b['end'])
                if key not in used:
                    used.add(key);out.append(dict(signal_time=b['end'],side=original['side'],reference_entry=b['close'],stop=original['stop'],
                                                 breakout_signal_time=original['signal_time'],retest_level=level,confirmation_delay_bars=j-i))
                break
    return sorted(out,key=lambda s:(s['signal_time'],s['side']))


def regime_map(bars,horizon,config):
    out={};n=config['lookback_completed_signal_bars']
    for i in range(n-1,len(bars)):
        rows=bars[i-n+1:i+1];closes=[b['close'] for b in rows]
        direction=closes[-1]-closes[0];path=sum(abs(b-a) for a,b in zip(closes,closes[1:]))
        efficiency=abs(direction)/path if path else 0
        trend=('UPTREND' if direction>0 else 'DOWNTREND') if efficiency>=config['trend_efficiency_threshold'] else 'RANGE'
        previous=bars[i-n]['close'] if i>=n else rows[0]['open']
        ranges=[]
        for b in rows:
            ranges.append(max(b['high']-b['low'],abs(b['high']-previous),abs(b['low']-previous)));previous=b['close']
        atr_fraction=mean(ranges)/closes[-1]
        vol='HIGH_VOL' if atr_fraction>=config['high_volatility_atr_fraction'][horizon] else 'NORMAL_VOL'
        out[rows[-1]['end']]=dict(regime=trend+'_'+vol,trend_efficiency=efficiency,atr_fraction=atr_fraction,regime_available_at=rows[-1]['end'])
    return out


def diagnostics(minutes,trade,signal_seconds):
    entry=seconds(trade['entry_timestamp']);exit_=seconds(trade['exit_timestamp']);origin=minutes[0]['time']
    first=(entry-origin)//60;last=(exit_-origin)//60;sign=1 if trade['direction']=='LONG' else -1
    gap=trade['exit_reason'].endswith('_GAP')
    observed=minutes[first:last]
    upper=0.;interval=(0,0);candidate_partial=False
    for b in observed:
        price=b['high'] if sign==1 else b['low'];value=sign*(price-trade['entry_price'])/trade['entry_price']*100
        if value>upper:
            upper=value;interval=(b['time']-entry,b['time']+60-entry)
            candidate_partial=not trade['exit_timestamp_exact'] and b['time']+60==exit_
    if gap:
        gap_value=sign*(trade['raw_exit_price']-trade['entry_price'])/trade['entry_price']*100
        if gap_value>upper:upper=gap_value;interval=(exit_-entry,exit_-entry);candidate_partial=False
    exact_interval=not candidate_partial and abs(trade['mfe_upper_pct']-trade['mfe_lower_pct'])<1e-10
    target_distance=sign*(trade['take_profit']-trade['entry_price'])/trade['entry_price']*100
    stop_distance=abs(trade['entry_price']-trade['stop_loss'])/trade['entry_price']*100
    record=dict(trade_id=trade['trade_id'],asset=trade['asset'],direction=trade['direction'],horizon=trade['horizon'],scenario=trade['scenario'],partition=trade['partition'],strategy=trade['strategy'],regime=trade['regime'],
                exit_reason=trade['exit_reason'],holding_seconds=trade['holding_seconds'],net_pnl_usd=trade['net_pnl_usd'],
                mfe_lower_pct=trade['mfe_lower_pct'],mfe_upper_pct=trade['mfe_upper_pct'],mae_lower_pct=trade['mae_lower_pct'],mae_upper_pct=trade['mae_upper_pct'],
                target_distance_pct=target_distance,stop_distance_pct=stop_distance,
                mfe_to_target_lower=trade['mfe_lower_pct']/target_distance,mfe_to_target_upper=trade['mfe_upper_pct']/target_distance,
                time_to_mfe_candidate_interval_start_seconds=interval[0],time_to_mfe_candidate_interval_end_seconds=interval[1],
                time_to_mfe_interval_verified=exact_interval,
                time_to_mfe_note='First minute attaining price MFE upper bound; partial exit-bar candidate is not verified actual peak time',
                realized_cost_hurdle_pct=(trade['fees_usd']+trade['slippage_and_rounding_usd']+trade['funding_cost_usd'])/trade['entry_notional_usd']*100)
    horizons=[300,900,1800,3600] if signal_seconds==300 else [3600,10800,21600,43200]
    for elapsed in (300,900,1800,3600,10800,21600,43200):
        # Do not inspect post-exit candles; an intraminute exit censors its own final-minute close.
        known=elapsed in horizons and entry+elapsed<=exit_ and (entry+elapsed<exit_ or trade['exit_timestamp_exact'] and not gap)
        record[f'directional_return_at_{elapsed}s_pct']=sign*(minutes[first+elapsed//60-1]['close']/trade['entry_price']-1)*100 if known else None
    return record


def regime_metrics(trades,equity,capital):
    output=[]
    for label in sorted({t['regime'] for t in trades}):
        selected=[t for t in trades if t['regime']==label];path=[equity[0]];all_realized=0.;selected_realized=0.;cursor=1
        for trade in trades:
            exit_=seconds(trade['exit_timestamp'])
            while cursor<len(equity) and equity[cursor][0]<=exit_:
                time,value=equity[cursor]
                if trade['regime']==label:path.append((time,capital+selected_realized+(value-capital-all_realized)))
                cursor+=1
            if trade['regime']==label:selected_realized+=trade['net_pnl_usd']
            all_realized+=trade['net_pnl_usd']
        output.append(dict(regime=label,**metrics(selected,path,capital)))
    return output
