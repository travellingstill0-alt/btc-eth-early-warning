"""Public, read-only USD market data. Never substitutes synthetic observations."""
from datetime import datetime, timezone
import math
import requests

KRAKEN = 'https://api.kraken.com'
COINBASE = 'https://api.exchange.coinbase.com'
FUTURES = 'https://futures.kraken.com'
DERIBIT = 'https://www.deribit.com'


def number(value, positive=False, nonnegative=False):
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError('Invalid numeric observation')
    return value


def timestamp(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


def metadata(provider, instrument, time_ms, kind, **details):
    return dict(provider=provider, instrument=instrument, source_time_ms=time_ms,
                timestamp_kind=kind, **details)


def fetch(symbol, max_age=180, now=None):
    asset = symbol.removesuffix('USDT').removesuffix('USD')
    if asset not in ('BTC', 'ETH'):
        raise ValueError('Only BTC and ETH are supported')
    clock = (lambda: now) if now else (lambda: datetime.now(timezone.utc))
    data = dict(symbol=asset + 'USD', retrieved_at=clock(), errors={}, sources={},
                attempts=[], warnings=[])
    pair = 'XBTUSD' if asset == 'BTC' else 'ETHUSD'
    instrument = 'PF_' + pair
    cache = {}

    def request(base, path, **params):
        attempt = dict(url=base + path, params=params, received_at=None, http_status=None)
        data['attempts'].append(attempt)
        try:
            response = requests.get(base + path, params=params, timeout=12)
            attempt.update(http_status=response.status_code, received_at=clock().isoformat())
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict) and (body.get('error') or body.get('result') == 'error'):
                raise ValueError(str(body.get('error') or body.get('errors')))
            return body
        except (requests.RequestException, ValueError) as exc:
            attempt['error'] = str(exc)
            raise

    def memo(name, loader):
        if name not in cache:
            try:
                cache[name] = loader()
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
                cache[name] = exc
        if isinstance(cache[name], Exception):
            raise cache[name]
        return cache[name]

    def choose(key, candidates, freshness=max_age):
        for provider, loader in candidates:
            try:
                payload, source = loader()
                age = (clock().timestamp() * 1000 - source['source_time_ms']) / 1000
                if age < -5 or age > freshness:
                    raise ValueError(f'Stale or future source timestamp (age {age:.1f}s)')
                source['received_at'] = clock().isoformat()
                data[key], data['sources'][key] = payload, source
                if provider != candidates[0][0]:
                    data['warnings'].append(f'{key}: using {provider} fallback')
                return
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
                data['errors'][key + ':' + provider] = f'{type(exc).__name__}: {exc}'
        data['warnings'].append(f'{key}: unavailable; all providers failed validation')

    def coinbase_spot():
        ticker = request(COINBASE, f'/products/{asset}-USD/ticker')
        stats = request(COINBASE, f'/products/{asset}-USD/stats')
        price, opening = number(ticker['price'], True), number(stats['open'], True)
        time_ms = timestamp(ticker['time'])
        return dict(lastPrice=price, baseVolume=number(ticker['volume'], nonnegative=True),
                    priceChangePercent=(price / opening - 1) * 100, closeTime=time_ms), metadata(
            'Coinbase', asset + '-USD', time_ms, 'latest trade',
            note='Volume and rolling 24h open have no separate observation timestamp.')

    def kraken_trades():
        body = request(KRAKEN, '/0/public/Trades', pair=pair, count=1000)['result']
        rows = next(v for k, v in body.items() if k != 'last')
        if not rows:
            raise ValueError('No public trades')
        if any(r[3] not in ('b', 's') for r in rows):
            raise ValueError('Unknown trade side')
        return sorted([dict(T=int(number(r[2]) * 1000), q=number(r[1], nonnegative=True),
                            m=r[3] == 's') for r in rows], key=lambda r: r['T'])

    def kraken_spot():
        body = request(KRAKEN, '/0/public/Ticker', pair=pair)['result']
        ticker = next(iter(body.values()))
        trades = memo('kraken_trades', kraken_trades)
        time_ms = trades[-1]['T']
        # Kraken's ticker open is UTC-day open, not a rolling 24h open.
        return dict(lastPrice=number(ticker['c'][0], True), baseVolume=number(ticker['v'][1], nonnegative=True),
                    priceChangePercent=None, closeTime=time_ms), metadata(
            'Kraken', pair, time_ms, 'latest trade',
            note='Volume has no separate timestamp. Rolling 24h change unavailable; UTC-day open is not substituted.')

    def candles(provider, interval):
        if provider == 'Kraken':
            body = request(KRAKEN, '/0/public/OHLC', pair=pair, interval=interval // 60)['result']
            rows = next(v for k, v in body.items() if k != 'last')
            bars = [[int(number(r[0]) * 1000), *[number(r[i], True) for i in (1, 2, 3, 4)],
                     number(r[6], nonnegative=True), int(number(r[0]) * 1000) + interval * 1000 - 1] for r in rows]
        else:
            rows = request(COINBASE, f'/products/{asset}-USD/candles', granularity=interval)
            bars = [[int(number(r[0]) * 1000), number(r[3], True), number(r[2], True), number(r[1], True),
                     number(r[4], True), number(r[5], nonnegative=True), int(number(r[0]) * 1000) + interval * 1000 - 1] for r in rows]
        if any(r[2] < max(r[1], r[3], r[4]) or r[3] > min(r[1], r[2], r[4]) for r in bars):
            raise ValueError('Invalid OHLC range')
        bars.sort(key=lambda r: r[0])
        finished = [r for r in bars if r[6] < clock().timestamp() * 1000]
        required = 40 if interval == 3600 else 21
        if len(finished) < required:
            raise ValueError('Insufficient completed candles')
        recent = finished[-required:]
        if any(b[0] - a[0] != interval * 1000 for a, b in zip(recent, recent[1:])):
            raise ValueError('Gaps in recent candles')
        return bars, metadata(provider, pair if provider == 'Kraken' else asset + '-USD',
                              finished[-1][6], 'completed candle end', interval_seconds=interval)

    def kraken_derivatives():
        body = request(FUTURES, '/derivatives/api/v3/tickers')
        ticker = next(t for t in body['tickers'] if t['symbol'] == instrument)
        if ticker.get('suspended') or ticker.get('postOnly'):
            raise ValueError('Perpetual market suspended or post-only')
        return ticker, timestamp(body['serverTime'])

    def deribit_derivatives():
        body = request(DERIBIT, '/api/v2/public/ticker', instrument_name=asset + '-PERPETUAL')['result']
        if body['state'] != 'open':
            raise ValueError('Perpetual market not open')
        return body, int(body['timestamp'])

    def derivatives(provider, key):
        ticker, time_ms = memo(provider, kraken_derivatives if provider == 'Kraken Futures' else deribit_derivatives)
        source = metadata(provider, instrument if provider == 'Kraken Futures' else asset + '-PERPETUAL',
                          time_ms, 'server snapshot',
                          note='No separate observation timestamp for OI or funding.')
        if key == 'interest':
            value = dict(openInterest=number(ticker['openInterest'] if provider == 'Kraken Futures' else ticker['open_interest'], nonnegative=True),
                         unit=asset if provider == 'Kraken Futures' else 'USD', time=time_ms)
        else:
            value = dict(lastFundingRate=number(ticker['relativeFundingRate'] if provider == 'Kraken Futures' else ticker['funding_8h']),
                         period_hours=1 if provider == 'Kraken Futures' else 8, time=time_ms)
        return value, source

    def flow(provider):
        if provider == 'Kraken':
            trades = memo('kraken_trades', kraken_trades)
        else:
            rows = request(COINBASE, f'/products/{asset}-USD/trades', limit=1000)
            if any(r['side'] not in ('buy', 'sell') for r in rows):
                raise ValueError('Unknown trade side')
            # Coinbase side is the maker's side; invert it for taker flow.
            trades = sorted([dict(T=timestamp(r['time']), q=number(r['size'], nonnegative=True),
                                  m=r['side'] == 'buy') for r in rows], key=lambda r: r['T'])
        if not trades:
            raise ValueError('No public trades')
        return trades, metadata(provider, pair if provider == 'Kraken' else asset + '-USD',
                                trades[-1]['T'], 'latest sampled trade',
                                note='Limited taker flow sample, not CVD or complete market coverage.')

    choose('ticker', [('Coinbase', coinbase_spot), ('Kraken', kraken_spot)])
    for key, interval in [('candles', 3600), ('scalp_candles', 300)]:
        choose(key, [(p, lambda p=p: candles(p, interval)) for p in ('Kraken', 'Coinbase')], interval * 2)
    for key in ('interest', 'funding'):
        choose(key, [(p, lambda p=p: derivatives(p, key)) for p in ('Kraken Futures', 'Deribit')])
    choose('trades', [(p, lambda p=p: flow(p)) for p in ('Kraken', 'Coinbase')])
    data['errors']['interest_history'] = 'Unavailable: verified providers supply current OI, not comparable hourly OI history.'
    data['warnings'].append('OI growth unavailable; required historical OI is missing, so ENTER is blocked.')
    if data.get('ticker', {}).get('priceChangePercent') is None:
        data['warnings'].append('Rolling 24h spot price change unavailable; ENTER is blocked.')
    data['retrieved_at'] = clock()
    return data
