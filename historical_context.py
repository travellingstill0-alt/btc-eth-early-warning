"""Historical CVD/OI value validation; never invent original publication times."""
from decimal import Decimal, InvalidOperation
from math import isfinite


def finite(value,nonnegative=False):
    if isinstance(value,bool):raise ValueError('Boolean context value')
    try:d=Decimal(str(value))
    except InvalidOperation as exc:raise ValueError('Invalid context number') from exc
    if not d.is_finite() or not isfinite(float(d)) or nonnegative and d<0:raise ValueError('Invalid context value')
    return d


def normalize(kind,payload,start,end):
    if payload.get('errors') or not isinstance(payload.get('result'),dict):raise ValueError('Context API error/schema')
    result=payload['result'];times=result['timestamp'];data=result['data']
    if result.get('more') is not False:raise ValueError('Unconsumed context pagination')
    if any(isinstance(t,bool) or not isinstance(t,int) or t%60 for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Invalid context times')
    if kind=='cvd':
        arrays=[]
        for snake,camel in [('buy_volume','buyVolume'),('sell_volume','sellVolume'),('cvd','cvd')]:
            keys=set(k for k in (snake,camel) if k in data)
            if len(keys)!=1:raise ValueError('Missing/ambiguous CVD field')
            arrays.append(data[next(iter(keys))])
        if any(len(a)!=len(times) for a in arrays):raise ValueError('CVD array mismatch')
        buy,sell,cumulative=[[finite(v,n<2) for v in a] for n,a in enumerate(arrays)]
        for i in range(1,len(times)):
            if times[i]==times[i-1]+60 and abs(cumulative[i]-cumulative[i-1]-(buy[i]-sell[i]))>Decimal('0.00000001'):
                raise ValueError('CVD increment contradicts taker volumes')
        records=[dict(time=t,buy_volume=float(buy[i]),sell_volume=float(sell[i]),delta=float(buy[i]-sell[i])) for i,t in enumerate(times)]
    elif kind=='open-interest':
        if len(data)!=len(times):raise ValueError('OI array mismatch')
        records=[]
        for t,row in zip(times,data):
            if len(row)!=4:raise ValueError('OI OHLC schema')
            o,h,l,c=[finite(v,True) for v in row]
            if not l<=min(o,c)<=max(o,c)<=h:raise ValueError('OI OHLC inconsistency')
            records.append(dict(time=t,open_interest=float(c)))
    else:raise ValueError('Unsupported historical context')
    selected=[r for r in records if start<=r['time']<end]
    if [r['time'] for r in selected]!=list(range(start,end,60)):raise ValueError('Missing historical context buckets')
    for row in selected:
        row.update(values_verified=True,interval_end=row['time']+60,available_at=None,availability_verified=False)
    return selected


def features(minutes,cvd,oi,funding,signal_time,signal_seconds,config):
    """Aligned completed windows; expose value checks separately from availability."""
    end=signal_time-config['minimum_completed_bar_lag_seconds'];start=end-config['window_signal_bars']*signal_seconds
    rows=[]
    try:
        for t in range(start,end,60):rows.append((minutes[t],cvd[t],oi[t]))
        baseline=oi[start-60]
        if any(c.get('values_verified') is not True or o.get('values_verified') is not True or c['interval_end']!=t+60 or o['interval_end']!=t+60 for t,(_,c,o) in zip(range(start,end,60),rows)):
            raise ValueError('Unverified historical value/boundary')
        rate_candidates=[r for t,r in funding.items() if t+3600<=end]
        if not rate_candidates:raise ValueError('Missing completed funding observation')
        rate=max(rate_candidates,key=lambda r:r['time'])
        if end-(rate['time']+3600)>=3600 or not all(isfinite(rate[k]) for k in ('fundingRate','relativeFundingRate')):
            raise ValueError('Stale or invalid historical funding')
        if baseline.get('values_verified') is not True or baseline['open_interest']<=0:raise ValueError('Invalid OI baseline')
        delta=sum(c['delta'] for _,c,_ in rows)
        price=(rows[-1][0]['close']/rows[0][0]['open']-1)*100
        oi_change=(rows[-1][2]['open_interest']/baseline['open_interest']-1)*100
        if not all(isfinite(v) for v in (delta,price,oi_change)):raise ValueError('Historical feature overflow')
        availability=[baseline,rate,*[v for _,c,o in rows for v in (c,o)]]
        asof=all(v.get('availability_verified') is True and isinstance(v.get('available_at'),(int,float)) and isfinite(v['available_at']) and v['available_at']<=signal_time for v in availability)
        return dict(values_available=True,asof_verified=asof,window_start=start,window_end=end,cvd_delta=delta,price_change_pct=price,oi_change_pct=oi_change,
                    funding_fraction_per_hour=rate['relativeFundingRate'],funding_time=rate['time'],
                    reason=None if asof else 'ORIGINAL_ASOF_AVAILABILITY_UNVERIFIED')
    except (KeyError,ValueError,TypeError,ZeroDivisionError) as exc:
        return dict(values_available=False,asof_verified=False,reason=str(exc))


def confirms(feature,side,config):
    if not feature.get('values_available') or not feature.get('asof_verified'):return False
    divergence=feature['price_change_pct']<=0 and feature['cvd_delta']>0 if side=='LONG' else feature['price_change_pct']>=0 and feature['cvd_delta']<0
    funding_cap=config['funding_threshold_pct_per_8h']/100/8
    return divergence and feature['oi_change_pct']>0 and abs(feature['funding_fraction_per_hour'])<=funding_cap
