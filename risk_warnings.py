"""Independent observed warnings. No strategy results or order actions as inputs."""
from context_data import parse


def warnings(data, now_ms, max_age=180):
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
    output['Abnormal open interest'] = 'Existing validated OI growth assessment displayed above; abnormality baseline research pending.'
    output['Funding extremes'] = 'Existing period-normalized threshold assessment displayed above; no squeeze prediction.'
    output['Macro announcements'] = 'Independent calendar gate remains active; missing global coverage cannot produce an all-clear.'
    return output
