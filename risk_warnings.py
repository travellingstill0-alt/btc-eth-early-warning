"""Independent observed warnings. No strategy results or order actions as inputs."""
from context_data import parse
from funding_history import observation as funding_observation
from oi_history import calculate_changes


def warnings(data, now_ms, max_age=180, funding_threshold_pct=0.03, oi_threshold_pct=10.0, oi_window="24h"):
    output = {}
    for kind, label in [('liquidations', 'Liquidation pressure'), ('cvd', 'CVD divergence')]:
        try:
            payload = data[kind]
            if payload['asset'] != data['symbol'][:3]:
                raise ValueError('Wrong asset')
            value = parse(payload, now_ms, max_age)['value']
            if kind == 'liquidations':
                output[label] = f'Observed executed liquidation volume: {value:g} {payload["unit"]}; future pressure and direction unverified.'
            else:
                output[label] = f'Verified window delta: {value:+g} {payload["unit"]}; divergence requires aligned same-contract price history.'
        except (ValueError, KeyError, TypeError):
            output[label] = 'UNAVAILABLE: fresh verified coverage required.'
    output['Long squeeze'] = 'UNVERIFIED: aligned contract price, OI, funding and directional liquidation history required.'
    output['Short squeeze'] = 'UNVERIFIED: aligned contract price, OI, funding and directional liquidation history required.'
    change=calculate_changes(data,now_ms,max_age).get(oi_window,{})
    value=change.get('change_pct')
    output['Abnormal open interest'] = ('UNAVAILABLE: '+str(change.get('reason','Unverified required window'))) if value is None else (
        f'{oi_window} verified OI change {value:+.3f}% — ' + ('GROWTH WARNING' if value>=oi_threshold_pct else 'configured growth threshold not triggered') + '; no statistical anomaly or squeeze claim.')
    try:
        item=funding_observation(data,int(now_ms),max_age)
        threshold=funding_threshold_pct*item['period_hours']/8
        elevated=abs(item['rate_fraction']*100)>=threshold
        output['Funding extremes'] = f"{item['rate_fraction']*100:+.5f}% per {item['period_hours']}h — " + ('EXTREME FUNDING WARNING' if elevated else 'configured threshold not triggered') + '; native-period comparison, not a squeeze prediction.'
    except (ValueError,KeyError,TypeError,OverflowError):
        output['Funding extremes'] = 'UNAVAILABLE: verified fresh funding and native period required.'
    output['Macro announcements'] = 'Independent calendar gate remains active; missing global coverage cannot produce an all-clear.'
    return output
