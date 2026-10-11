"""Fixed-parameter historical research only. No orders or live safety overrides."""
from datetime import datetime, timezone
from math import ceil, floor, isfinite
from statistics import mean


def stamp(t):
    return datetime.fromtimestamp(t,timezone.utc).isoformat()


def aggregate(minutes,seconds):
    if seconds%60 or seconds<60:raise ValueError('Invalid signal interval')
    output=[];size=seconds//60
    for i in range(0,len(minutes),size):
        chunk=minutes[i:i+size]
        if len(chunk)!=size or chunk[0]['time']%seconds or any(b['time']!=chunk[0]['time']+j*60 for j,b in enumerate(chunk)):
            raise ValueError('Incomplete aggregation bucket')
        output.append(dict(time=chunk[0]['time'],end=chunk[-1]['time']+60,open=chunk[0]['open'],
                           high=max(b['high'] for b in chunk),low=min(b['low'] for b in chunk),
                           close=chunk[-1]['close'],volume=sum(b['volume'] for b in chunk)))
    return output


def signals(bars,lookback=20,volume_multiple=1.2):
    output=[]
    for i in range(lookback,len(bars)):
        reference,last=bars[i-lookback:i],bars[i]
        high,low=max(b['high'] for b in reference),min(b['low'] for b in reference)
        side='LONG' if last['close']>high else 'SHORT' if last['close']<low else None
        if side and last['volume']>mean(b['volume'] for b in reference)*volume_multiple:
            stop=low if side=='LONG' else high
            output.append(dict(signal_time=last['end'],side=side,reference_entry=last['close'],stop=stop))
    return output


def tick_fill(price,tick,order_sign):
    if not isfinite(price) or price<=0 or tick<=0:raise ValueError('Invalid fill')
    return (ceil(price/tick-1e-10) if order_sign==1 else floor(price/tick+1e-10))*tick


def simulate(minutes,funding,signal,timeout,scenario,position,tick,precision,target_r=1):
    sign=1 if signal['side']=='LONG' else -1
    start=(signal['signal_time']-minutes[0]['time'])//60
    count=timeout//60
    if timeout%60 or start<0 or start+count>len(minutes):raise ValueError('Insufficient execution window')
    first=minutes[start]
    if first['time']!=signal['signal_time']:raise ValueError('Execution timestamp mismatch')
    slip=scenario['slippage_bps_per_fill']/10000;fee_rate=scenario['fee_bps']/10000
    raw_entry=first['open'];entry=tick_fill(raw_entry*(1+sign*slip),tick,sign)
    stop=signal['stop'];target=signal['reference_entry']+sign*abs(signal['reference_entry']-stop)*target_r
    if target<=0 or sign*(entry-stop)<=0 or sign*(target-entry)<=0:
        return None,'ENTRY_GAP_INVALIDATES_LEVELS',[]
    quantity=floor(position['notional_cap_usd']/entry*10**precision+1e-10)/10**precision
    if quantity<=0:return None,'QUANTITY_ROUNDS_TO_ZERO',[]
    entry_fee=entry*quantity*fee_rate
    funding_total=0.;mfe_lower=0.;mfe_upper=0.;mae_lower=0.;mae_upper=0.;equity_path=[]
    for offset in range(count):
        b=minutes[start+offset];time=b['time'];hour=time//3600*3600
        if hour not in funding:raise ValueError('Missing funding during position')
        gap_stop=sign*(b['open']-stop)<=0;gap_target=sign*(b['open']-target)>=0
        stop_hit=b['low']<=stop if sign==1 else b['high']>=stop
        target_hit=b['high']>=target if sign==1 else b['low']<=target
        ambiguous=bool(stop_hit and target_hit and not(gap_stop or gap_target))
        reason='STOP_GAP' if gap_stop else 'TARGET_GAP' if gap_target else 'STOP' if stop_hit else 'TARGET' if target_hit else 'TIMEOUT' if offset==count-1 else None
        if reason:
            raw_exit=b['open'] if gap_stop or gap_target else stop if stop_hit else target if target_hit else b['close']
            exact=bool(gap_stop or gap_target or reason=='TIMEOUT')
            exit_time=time if gap_stop or gap_target else time+60
            seconds_held_in_bar=0 if gap_stop or gap_target else 60
        else:
            raw_exit=b['close'];exact=True;exit_time=time+60;seconds_held_in_bar=60
        funding_total+=sign*quantity*funding[hour]*seconds_held_in_bar/3600
        # Exit candle path is unknown. Keep rigorous pre-exit price-excursion bounds.
        known=[b['open'],raw_exit] if reason else [b['open'],b['high'],b['low'],b['close']]
        possible=known if gap_stop or gap_target else [*known,b['high'],b['low']]
        if reason=='TIMEOUT':known=possible
        values=[sign*(p-entry)/entry*100 for p in known]
        bounds=[sign*(p-entry)/entry*100 for p in possible]
        mfe_lower=max(mfe_lower,max(values));mfe_upper=max(mfe_upper,max(bounds))
        mae_upper=min(mae_upper,min(values));mae_lower=min(mae_lower,min(bounds))
        if reason:
            exit_price=tick_fill(raw_exit*(1-sign*slip),tick,-sign)
            exit_fee=exit_price*quantity*fee_rate
            gross=sign*quantity*(exit_price-entry)
            net=gross-entry_fee-exit_fee-funding_total
            equity_path.append((exit_time,net))
            risk=quantity*abs(entry-stop)
            trade=dict(signal_timestamp=stamp(signal['signal_time']),entry_timestamp=stamp(first['time']),
                       exit_timestamp=stamp(exit_time),exit_timestamp_exact=exact,
                       exit_interval_start=stamp(time),exit_interval_end=stamp(time if gap_stop or gap_target else time+60),
                       entry_price=entry,exit_price=exit_price,raw_entry_price=raw_entry,raw_exit_price=raw_exit,
                       reference_entry=signal['reference_entry'],stop_loss=stop,take_profit=target,quantity=quantity,
                       entry_notional_usd=entry*quantity,initial_risk_usd=risk,
                       entry_fee_usd=entry_fee,exit_fee_usd=exit_fee,fees_usd=entry_fee+exit_fee,
                       slippage_and_rounding_usd=quantity*(abs(entry-raw_entry)+abs(exit_price-raw_exit)),
                       funding_cost_usd=funding_total,funding_convention='hour-forward prorated; intraminute exits charged through minute end',
                       gross_before_execution_costs_usd=sign*quantity*(raw_exit-raw_entry),gross_pnl_usd=gross,net_pnl_usd=net,net_return_pct=net/(entry*quantity)*100,net_r_multiple=net/risk,
                       maximum_favorable_excursion_pct=mfe_upper,maximum_adverse_excursion_pct=mae_lower,
                       mfe_lower_pct=mfe_lower,mfe_upper_pct=mfe_upper,mae_lower_pct=mae_lower,mae_upper_pct=mae_upper,
                       excursion_exact=abs(mfe_upper-mfe_lower)<1e-12 and abs(mae_upper-mae_lower)<1e-12,
                       excursion_basis='price relative to actual entry; excludes costs; intraminute exit bounds',
                       exit_reason=reason,ambiguous_stop_target=ambiguous,holding_seconds=exit_time-first['time'],
                       outcome='WIN' if net>0 else 'LOSS' if net<0 else 'BREAKEVEN')
            return trade,None,equity_path
        # Intratrade mark-to-market uses minute close, actual entry fee and accrued funding.
        equity_path.append((time+60,sign*quantity*(b['close']-entry)-entry_fee-funding_total))
    raise AssertionError('Timeout must close position')


def metrics(trades,equity,start_equity):
    pnl=[t['net_pnl_usd'] for t in trades];wins=[p for p in pnl if p>0];losses=[p for p in pnl if p<0]
    peak=start_equity;max_dd=0.
    for _,value in equity:
        peak=max(peak,value);max_dd=max(max_dd,(peak-value)/peak*100)
    return dict(trade_count=len(trades),win_rate_pct=len(wins)/len(pnl)*100 if pnl else None,
                profit_factor=sum(wins)/abs(sum(losses)) if losses else 'NO_LOSSES' if wins else None,
                maximum_drawdown_pct=max_dd,drawdown_basis='minute-close/open-gap mark-to-market, not intraminute extrema',
                average_net_return_pct=mean(t['net_return_pct'] for t in trades) if trades else None,
                expectancy_usd=mean(pnl) if pnl else None,expectancy_r=mean(t['net_r_multiple'] for t in trades) if trades else None,
                net_pnl_usd=sum(pnl),account_return_pct=sum(pnl)/start_equity*100,
                fees_usd=sum(t['fees_usd'] for t in trades),funding_cost_usd=sum(t['funding_cost_usd'] for t in trades),
                slippage_and_rounding_usd=sum(t['slippage_and_rounding_usd'] for t in trades),
                exit_reasons={r:sum(t['exit_reason']==r for t in trades) for r in sorted({t['exit_reason'] for t in trades})},
                ambiguous_exits=sum(t['ambiguous_stop_target'] for t in trades),
                timeout_fraction_pct=sum(t['exit_reason']=='TIMEOUT' for t in trades)/len(trades)*100 if trades else None)


def run_group(minutes,funding,candidates,side,horizon,scenario,config,instrument,start,end,partition,asset):
    trades=[];skips=[];equity=[(start,config['position']['initial_equity_usd'])]
    realized=0.;next_available=start;timeout=config['timeout_seconds'][horizon]
    for signal in candidates:
        time=signal['signal_time']
        if signal['side']!=side or not start<=time<end:continue
        reason='PURGED_MAX_HOLD_CROSSES_BOUNDARY' if time+timeout>end else 'POSITION_ALREADY_OPEN' if time<next_available else None
        if reason:skips.append(dict(signal_timestamp=stamp(time),reason=reason));continue
        trade,reason,path=simulate(minutes,funding,signal,timeout,scenario,config['position'],instrument['tickSize'],instrument['contractValueTradePrecision'],config['take_profit']['risk_multiple'])
        if reason:skips.append(dict(signal_timestamp=stamp(time),reason=reason));continue
        trade.update(asset=asset,instrument=instrument['symbol'],direction=side,horizon=horizon,scenario=scenario['name'],partition=partition,simulation_only=True,fee_bps_per_fill=scenario['fee_bps'],slippage_bps_per_fill=scenario['slippage_bps_per_fill'],fees_currency='USD',configuration_version=config.get('version','test-only'))
        equity.extend((t,config['position']['initial_equity_usd']+realized+p) for t,p in path)
        realized+=trade['net_pnl_usd'];next_available=int(datetime.fromisoformat(trade['exit_timestamp']).timestamp())
        trades.append(trade)
    info=dict(asset=asset,direction=side,horizon=horizon,scenario=scenario['name'],partition=partition,
              start=stamp(start),end_exclusive=stamp(end),skipped_count=len(skips),**metrics(trades,equity,config['position']['initial_equity_usd']))
    return trades,skips,equity,info
