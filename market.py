"""Public, read-only USD market data. Never substitutes synthetic observations."""
from datetime import datetime, timezone
import math
import sqlite3
import requests
import sqlite3
from context_data import collect as collect_context
from exchange_flows import collect as collect_exchange_flows
from oi_history import SnapshotStore, current_point, parse_kraken_history, calculate_changes, WINDOWS

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
    if not isinstance(value, str):
        raise ValueError('Invalid provider timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Provider timestamp must include a timezone')
        return epoch_ms(int(parsed.timestamp() * 1000))
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError('Invalid provider timestamp') from exc


def epoch_ms(value):
    try:
        if isinstance(value, bool):
            raise ValueError('Boolean timestamp')
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0 or numeric != int(numeric):
            raise ValueError('Invalid epoch timestamp')
        datetime.fromtimestamp(numeric / 1000, timezone.utc)
        return int(numeric)
    except (TypeError, ValueError, OverflowError, OSError) as exc:
        raise ValueError('Invalid provider epoch timestamp') from exc


def epoch_seconds(value):
    try:
        seconds = number(value, positive=True)
        return epoch_ms(int(seconds * 1000))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Invalid provider trade timestamp') from exc


def metadata(provider, instrument, time_ms, kind, **details):
    return dict(provider=provider, instrument=instrument, source_time_ms=time_ms,
                timestamp_kind=kind, **details)


def fetch(symbol, max_age=180, now=None, history_path=None):
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
            if isinstance(body, dict) and (body.get('error') or body.get('errors') or body.get('result') == 'error'):
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
        return sorted([dict(T=epoch_seconds(r[2]), q=number(r[1], nonnegative=True),
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
            bars = [[epoch_ms(number(r[0]) * 1000), *[number(r[i], True) for i in (1, 2, 3, 4)],
                     number(r[6], nonnegative=True), epoch_ms(number(r[0]) * 1000) + interval * 1000 - 1] for r in rows]
        else:
            rows = request(COINBASE, f'/products/{asset}-USD/candles', granularity=interval)
            bars = [[epoch_ms(number(r[0]) * 1000), number(r[3], True), number(r[2], True), number(r[1], True),
                     number(r[4], True), number(r[5], nonnegative=True), epoch_ms(number(r[0]) * 1000) + interval * 1000 - 1] for r in rows]
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
        return body, epoch_ms(body['timestamp'])

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
    try:
        now_ms = int(clock().timestamp() * 1000)
        current = current_point(data, now_ms, max_age)
        candidates = []
        try:
            stored = SnapshotStore(history_path).record_and_read(current, max_age)
            candidates.append((stored, 'persistent OI snapshots'))
        except (sqlite3.Error, OSError, ValueError) as exc:
            data['errors']['oi_storage'] = str(exc)
            data['warnings'].append('OI snapshot storage unavailable; observations were not saved.')
        if current['provider'] == 'Kraken Futures':
            try:
                body = request(FUTURES, f'/api/charts/v1/analytics/{current["instrument"]}/open-interest',
                               interval=60, since=now_ms // 1000 - WINDOWS['24h'] - 240)
                bars = parse_kraken_history(body, current, int(clock().timestamp() * 1000))
                candidates.append((bars + [current], 'Kraken minute OI bar closes + current snapshot'))
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
                data['errors']['interest_history:Kraken Futures'] = str(exc)
                data['warnings'].append('Kraken OI history unavailable; using separate persistent snapshots when sufficient.')
        else:
            data['warnings'].append('Deribit historical OI unavailable; collecting persistent observations for this contract.')
        best = None
        for rows, method in candidates:
            source = metadata(current['provider'], current['instrument'], current['timestamp'],
                              'OI observations', unit=current['unit'], verified=True, method=method,
                              note='Real observations only; completed bar boundaries or server snapshot timestamps.')
            trial = dict(data, interest_history=rows,
                         sources={**data['sources'], 'interest_history': source})
            changes = calculate_changes(trial, int(clock().timestamp() * 1000), max_age)
            coverage = max((WINDOWS[w] for w, result in changes.items() if result['change_pct'] is not None), default=0)
            if best is None or coverage >= best[0]:
                best = coverage, rows, source, changes
        if best is None:
            raise ValueError('No verified OI history or readable persistent store')
        _, data['interest_history'], data['sources']['interest_history'], data['oi_changes'] = best
        if not best[0]:
            data['warnings'].append('OI history warming up or incomplete; required missing windows block ENTER.')
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        data['errors']['interest_history'] = str(exc)
        data['warnings'].append('OI history unavailable or unverified; ENTER remains blocked.')
    def context_request(base, path, **params):
        try:
            return request(base, path, **params)
        except requests.RequestException as exc:
            raise ValueError(str(exc)) from exc
    context, context_errors, context_warnings = collect_context(
        context_request, asset, lambda: int(clock().timestamp() * 1000), max_age)
    data.update(context)
    # Preserve only raw windows that pass the existing independent validator.
    from observation_store import preserve
    for key, item in context.items():
        try:
            preserve(item, int(clock().timestamp() * 1000), max_age)
        except (ValueError, OSError, sqlite3.Error) as exc:
            data['errors']['storage:' + key] = str(exc)
            data['warnings'].append('Context persistence failed; observation was not saved.')
    data['errors'].update({'context:' + k: v for k, v in context_errors.items()})
    data['warnings'].extend(context_warnings)
    for key, item in context.items():
        data['sources'][key] = metadata(item['provider'], item['instrument'], item['end_ms'],
            'completed observation window end', unit=item['unit'], method=item['method'],
            note='Single-contract executed observations only; no whole-market coverage or future liquidation levels.')
    data['exchange_flow_diagnostics'] = collect_exchange_flows(
        context_request, asset, lambda: int(clock().timestamp()*1000), max_age)
    if data.get('cvd'):
        from price_context import collect as collect_price, preserve as preserve_price
        try:
            payload = collect_price(context_request, data['cvd'], lambda: int(clock().timestamp()*1000), max_age)
            data['perpetual_price'] = payload
            data['sources']['perpetual_price'] = metadata(payload['provider'], payload['instrument'], payload['end_ms'], 'completed observation window end', price_unit='USD')
            try:
                preserve_price(payload, int(clock().timestamp()*1000), max_age)
            except (ValueError, OSError, sqlite3.Error) as exc:
                data['errors']['storage:perpetual_price'] = str(exc)
                data['warnings'].append('Aligned price persistence failed; observation was not saved.')
        except (ValueError, KeyError, TypeError) as exc:
            data['errors']['context:perpetual_price'] = str(exc)
            data['warnings'].append('CVD divergence unavailable: no verified aligned same-contract price window.')
    flow = data['exchange_flow_diagnostics']
    data['errors']['context:exchange flows'] = flow.get('error', flow['reason'])
    data['warnings'].append('Exchange wallet flows: ' + flow['reason'])
    if data.get('ticker', {}).get('priceChangePercent') is None:
        data['warnings'].append('Rolling 24h spot price change unavailable; ENTER is blocked.')
    if data.get('funding'):
        from funding_history import preserve as preserve_funding
        try:
            preserve_funding(data, int(clock().timestamp()*1000), max_age)
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
            data['errors']['storage:funding'] = str(exc)
            data['warnings'].append('Funding persistence failed; observation was not saved.')
    data['retrieved_at'] = clock()
    return data
