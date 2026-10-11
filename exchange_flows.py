"""Read-only exchange-wallet feed diagnostics. No provider is safety-approved yet.

Coin Metrics exchange metrics use provider-labelled addresses. Labels alone do
not prove complete wallet coverage; these daily diagnostics never unlock ENTER.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

BASE = 'https://community-api.coinmetrics.io'
PATH = '/v4/timeseries/asset-metrics'
METRICS = ('FlowInKRKNtv', 'FlowOutKRKNtv')


def inspect(raw, asset, now_ms, max_age=180):
    if asset not in ('BTC', 'ETH'):
        raise ValueError('Unsupported exchange-flow asset')
    if not isinstance(raw, dict) or raw.get('error') or raw.get('next_page_url'):
        raise ValueError('Provider error or incomplete/paginated exchange flows')
    rows = raw.get('data')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Missing exchange inflow/outflow observations')
    observations, seen = [], set()
    for row in rows:
        if row['asset'] != asset.lower():
            raise ValueError('Wrong exchange-flow asset')
        stamp = row['time']
        if not isinstance(stamp, str):
            raise ValueError('Invalid exchange-flow timestamp')
        dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError('Exchange-flow timestamp needs timezone')
        dt = dt.astimezone(timezone.utc)
        ms = int(dt.timestamp()*1000)
        if ms <= 0 or ms > now_ms or ms in seen or any((dt.hour, dt.minute, dt.second, dt.microsecond)):
            raise ValueError('Future, duplicate or unaligned daily exchange-flow timestamp')
        seen.add(ms)
        values = []
        for metric in METRICS:
            value = row[metric]
            if isinstance(value, bool) or value is None:
                raise ValueError('Invalid exchange-flow amount')
            try:
                amount = Decimal(str(value))
            except InvalidOperation as exc:
                raise ValueError('Invalid exchange-flow amount') from exc
            if not amount.is_finite() or amount < 0:
                raise ValueError('Invalid exchange-flow amount')
            values.append(str(amount))
        observations.append(dict(provider_time_ms=ms, inflow=values[0], outflow=values[1]))
    observations.sort(key=lambda x: x['provider_time_ms'])
    if any(b['provider_time_ms']-a['provider_time_ms'] != 86400000 for a,b in zip(observations, observations[1:])):
        raise ValueError('Gaps in exchange-flow daily observations')
    return dict(observations=observations,
                provider_timestamp_age_seconds=(now_ms-observations[-1]['provider_time_ms'])/1000,
                timestamp_within_freshness=(now_ms-observations[-1]['provider_time_ms']) <= max_age*1000)


def collect(request, asset, now_ms, max_age=180):
    report = dict(provider='Coin Metrics Community', asset=asset, exchange='Kraken',
                  unit=asset, frequency='1d', classification='provider-labelled wallet aggregate; unverified coverage',
                  verified=False, safety_eligible=False, status='unavailable',
                  reason='No validated fresh and complete exchange-wallet provider; NO TRADE.',
                  received_at_ms=None)
    try:
        raw = request(BASE, PATH, assets=asset.lower(), metrics=','.join(METRICS),
                      frequency='1d', limit_per_asset=2, page_size=2, sort='desc')
        report['received_at_ms'] = now_ms()
        report.update(inspect(raw, asset, report['received_at_ms'], max_age))
        report.update(status='diagnostic only', reason=(
            'Daily provider-labelled Kraken wallet aggregates are not verified safety inputs: '
            'interval completion, wallet attribution, indexing completeness and finality are unvalidated. '
            'Daily resolution cannot certify the required fresh observation window; NO TRADE.'))
    except (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError, AttributeError) as exc:
        report['error'] = str(exc)
    return report
