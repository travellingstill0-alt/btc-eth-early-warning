"""Verified, venue-scoped observations only; no heatmap or market-wide estimates."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math

WINDOW_MS = 900_000
MINUTE_MS = 60_000


def decimal(value, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError('Boolean observation')
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not math.isfinite(float(result)) or (nonnegative and result < 0):
            raise ValueError('Invalid context value')
        return result
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError('Invalid context value') from exc


def integer(value):
    result = decimal(value, True)
    if result != int(result) or result <= 0:
        raise ValueError('Invalid context timestamp or sequence')
    return int(result)


def iso_ms(value):
    if not isinstance(value, str):
        raise ValueError('Invalid context timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Missing timezone')
        return integer(int(parsed.timestamp() * 1000))
    except (TypeError, OverflowError, OSError) as exc:
        raise ValueError('Invalid context timestamp') from exc


def window(now_ms):
    end = int(now_ms) // MINUTE_MS * MINUTE_MS - 1
    return end + 1 - WINDOW_MS, end


def bounds(start, end, now_ms, max_age):
    start, end = integer(start), integer(end)
    if start % MINUTE_MS or (end + 1) % MINUTE_MS or end - start + 1 != WINDOW_MS:
        raise ValueError('Invalid completed 15-minute window')
    if end >= now_ms or now_ms - end > max_age * 1000:
        raise ValueError('Stale or incomplete context window')


def kraken_bars(body, kind, start, end, now_ms, max_age):
    bounds(start, end, now_ms, max_age)
    if body.get('errors'):
        raise ValueError('Kraken context API error')
    result = body['result']
    if result['more'] is not False:
        raise ValueError('Truncated analytics window')
    times = result['timestamp']
    if not isinstance(times, list) or not times:
        raise ValueError('Missing context bars')
    times = [integer(t) * 1000 for t in times]
    if any(t % MINUTE_MS or t > now_ms + 5000 for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Invalid, duplicate, unordered or future context bars')
    # A provider may return the active bucket; never include it in the calculation.
    indices = [i for i, t in enumerate(times) if start <= t <= end]
    if [times[i] for i in indices] != list(range(start, end + 1, MINUTE_MS)):
        raise ValueError('Missing completed context buckets')
    raw = result['data']
    if kind == 'cvd':
        def field(snake, camel):
            keys = [key for key in (snake, camel) if key in raw]
            if len(keys) != 1:
                raise ValueError('Missing or ambiguous CVD schema')
            return raw[keys[0]]
        buy, sell, reported = field('buy_volume', 'buyVolume'), field('sell_volume', 'sellVolume'), raw['cvd']
        if any(not isinstance(a, list) or len(a) != len(times) for a in (buy, sell, reported)):
            raise ValueError('Invalid CVD arrays')
        buy = [decimal(v, True) for v in buy]; sell = [decimal(v, True) for v in sell]
        reported = [decimal(v) for v in reported]
        for i in indices:
            if i > 0 and times[i] - times[i-1] == MINUTE_MS:
                if abs((reported[i] - reported[i-1]) - (buy[i] - sell[i])) > Decimal('0.00000001'):
                    raise ValueError('Provider CVD contradicts buy/sell volume')
        buys, sells = sum((buy[i] for i in indices), Decimal(0)), sum((sell[i] for i in indices), Decimal(0))
        return dict(value=float(buys - sells), buy_volume=float(buys), sell_volume=float(sells), count=15)
    if not isinstance(raw, list) or len(raw) != len(times):
        raise ValueError('Invalid liquidation arrays')
    values = [decimal(v, True) for v in raw]
    return dict(value=float(sum((values[i] for i in indices), Decimal(0))), count=15)


def deribit_cvd(body, instrument, start, end, now_ms, max_age):
    bounds(start, end, now_ms, max_age)
    if body.get('error') or body.get('testnet') is True:
        raise ValueError('Invalid Deribit production response')
    result = body['result']
    if result['has_more'] is not False:
        raise ValueError('Incomplete Deribit trade history')
    trades = result['trades']
    if not isinstance(trades, list) or not trades:
        raise ValueError('No verified trades; empty result is not assumed zero CVD')
    buys, sells, previous_seq, previous_time, ids = Decimal(0), Decimal(0), None, 0, set()
    for trade in trades:
        seq, time_ms = integer(trade['trade_seq']), integer(trade['timestamp'])
        if (trade['instrument_name'] != instrument or not start <= time_ms <= end or time_ms < previous_time
                or (previous_seq is not None and seq != previous_seq + 1) or trade['trade_id'] in ids):
            raise ValueError('Wrong contract, gaps, duplicate or unordered trades')
        if any(trade.get(k) for k in ('block_trade_id', 'combo_trade_id', 'combo_id', 'block_rfq_id')):
            raise ValueError('Negotiated trades cannot be classified as verified taker CVD')
        amount = decimal(trade['amount'], True)
        if trade['direction'] == 'buy': buys += amount
        elif trade['direction'] == 'sell': sells += amount
        else: raise ValueError('Unknown taker direction')
        ids.add(trade['trade_id']); previous_seq, previous_time = seq, time_ms
    return dict(value=float(buys-sells), buy_volume=float(buys), sell_volume=float(sells), count=len(trades))


def kraken_liquidations(body, start, end, now_ms, max_age):
    bounds(start, end, now_ms, max_age)
    if body.get('result') != 'success' or not -5000 <= now_ms - iso_ms(body['serverTime']) <= max_age * 1000:
        raise ValueError('Invalid or stale Kraken history response')
    trades = body['history']
    if not isinstance(trades, list) or not trades:
        raise ValueError('No coverage boundary in liquidation history')
    total, previous, ids = Decimal(0), None, set()
    for trade in trades:
        time_ms = iso_ms(trade['time'])
        seq = integer(trade['sequence_id'])
        if previous is not None and seq != previous + 1:
            raise ValueError('Gap or duplicate in liquidation trade history')
        if trade['uid'] in ids or time_ms > end:
            raise ValueError('Duplicate or out-of-window liquidation trade')
        kind = trade['type']
        if kind not in ('fill', 'liquidation', 'partial liquidation', 'assignment', 'termination', 'block'):
            raise ValueError('Unverified execution classification')
        size = decimal(trade['size'], True)
        if start <= time_ms and kind in ('liquidation', 'partial liquidation'):
            total += size
        previous = seq; ids.add(trade['uid'])
    if min(iso_ms(t['time']) for t in trades) >= start:
        raise ValueError('Liquidation trade history does not cover window start')
    return dict(value=float(total), count=sum(start <= iso_ms(t['time']) for t in trades))


def _parse(payload, now_ms, max_age=180):
    """Revalidate raw data, identity, time and coverage; never trust cached totals."""
    provider, instrument, kind = payload['provider'], payload['instrument'], payload['kind']
    asset = payload['asset']
    if asset not in ('BTC', 'ETH') or kind not in ('cvd', 'liquidations'):
        raise ValueError('Unsupported context')
    start, end = payload['start_ms'], payload['end_ms']
    if not -5000 <= now_ms - integer(payload['received_at_ms']) <= max_age * 1000:
        raise ValueError('Stale or future context retrieval')
    if provider == 'Kraken Futures' and instrument == 'PF_' + ('XBT' if asset == 'BTC' else asset) + 'USD':
        if payload['unit'] != asset:
            raise ValueError('Wrong native context unit')
        if payload['method'] == 'minute analytics':
            return kraken_bars(payload['raw'], kind, start, end, now_ms, max_age)
        if kind == 'liquidations' and payload['method'] == 'complete execution history':
            return kraken_liquidations(payload['raw'], start, end, now_ms, max_age)
    elif (kind == 'cvd' and provider == 'Deribit' and instrument == asset + '-PERPETUAL'
          and payload['unit'] == 'USD' and payload['method'] == 'complete trade history'):
        times = payload['raw']['response_times_ms']
        if not isinstance(times, list) or not times or any(
                t < end or not -5000 <= now_ms - integer(t) <= max_age * 1000 for t in times):
            raise ValueError('Stale, future or missing Deribit response timestamp')
        return deribit_cvd(payload['raw'], instrument, start, end, now_ms, max_age)
    raise ValueError('Unverified context provider, contract or method')


def parse(payload, now_ms, max_age=180):
    result = _parse(payload, now_ms, max_age)
    if any(not math.isfinite(v) for k, v in result.items() if k != 'count'):
        raise ValueError('Context aggregate overflow')
    return result


def collect(request, asset, now_ms, max_age=180):
    """Bounded GETs; switching provider replaces a whole window, never splices it."""
    start, end = window(now_ms())
    symbol = 'PF_' + ('XBT' if asset == 'BTC' else asset) + 'USD'
    errors, warnings, available = {}, [], {}
    def payload(kind, provider, instrument, unit, method, raw):
        item = dict(kind=kind, provider=provider, instrument=instrument, asset=asset, unit=unit,
                    start_ms=start, end_ms=end, received_at_ms=now_ms(), method=method, raw=raw)
        parse(item, now_ms(), max_age)
        return item
    def analytics(kind):
        name = 'cvd' if kind == 'cvd' else 'liquidation-volume'
        raw = request('https://futures.kraken.com', f'/api/charts/v1/analytics/{symbol}/{name}',
                      interval=60, since=start//1000, to=end//1000)
        return payload(kind, 'Kraken Futures', symbol, asset, 'minute analytics', raw)
    def cvd_fallback():
        instrument = asset + '-PERPETUAL'
        # Split saturated time ranges without skipping trades sharing a timestamp.
        calls, response_times = 0, []
        def read(lo, hi):
            nonlocal calls
            calls += 1
            if calls > 7:
                raise ValueError('Deribit history request budget exhausted')
            raw = request('https://www.deribit.com', '/api/v2/public/get_last_trades_by_instrument_and_time',
                          instrument_name=instrument, start_timestamp=lo, end_timestamp=hi, count=1000, sorting='asc')
            if raw.get('error') or raw.get('testnet') is True:
                raise ValueError('Invalid Deribit response')
            response_times.append(integer(raw['usOut']) // 1000)
            result = raw['result']
            if result['has_more'] is True:
                if lo == hi:
                    raise ValueError('Too many trades at one timestamp')
                mid = (lo+hi)//2
                return read(lo, mid) + read(mid+1, hi)
            if result['has_more'] is not False:
                raise ValueError('Unknown history completeness')
            trades = result['trades']
            if not isinstance(trades, list) or any(not lo <= integer(t['timestamp']) <= hi for t in trades):
                raise ValueError('Provider ignored requested trade bounds')
            return trades
        trades = read(start, end)
        return payload('cvd', 'Deribit', instrument, 'USD', 'complete trade history',
                       dict(result=dict(trades=trades, has_more=False), response_times_ms=response_times))
    def liquidation_fallback():
        trades, cursor, server_time = [], datetime.fromtimestamp((end+1)/1000, timezone.utc).isoformat(), None
        # Keep provider nanoseconds as the paging cursor; millisecond rounding may skip trades.
        for _ in range(10):
            raw = request('https://futures.kraken.com', '/derivatives/api/v3/history', symbol=symbol, lastTime=cursor)
            if raw.get('result') != 'success':
                raise ValueError('Invalid liquidation history response')
            page = raw['history']
            if not isinstance(page, list) or not page:
                raise ValueError('Incomplete liquidation history')
            page = sorted(page, key=lambda t: integer(t['sequence_id']))
            server_time = raw['serverTime']
            merged = {t['uid']: t for t in trades}
            for trade in page:
                old = merged.get(trade['uid'])
                fields = ('time', 'sequence_id', 'size', 'type', 'side')
                if old and any(old.get(k) != trade.get(k) for k in fields):
                    raise ValueError('Conflicting execution across history pages')
                merged[trade['uid']] = trade
            previous_count = len(trades)
            trades = sorted(merged.values(), key=lambda t: integer(t['sequence_id']))
            if len(trades) == previous_count:
                raise ValueError('Liquidation history pagination made no progress')
            if iso_ms(page[0]['time']) < start:
                break
            cursor = page[0]['time']
        return payload('liquidations', 'Kraken Futures', symbol, asset, 'complete execution history',
                       dict(result='success', serverTime=server_time, history=trades))
    failures = (ValueError, KeyError, TypeError, IndexError, OverflowError, OSError, AttributeError)
    # request callback converts transport failures into ValueError.
    for kind, secondary in (('cvd', cvd_fallback), ('liquidations', liquidation_fallback)):
        for method, loader in (('primary', lambda kind=kind: analytics(kind)), ('fallback', secondary)):
            try:
                available[kind] = loader()
                if method == 'fallback': warnings.append(f'{kind}: using verified fallback; scope/units shown separately')
                break
            except failures as exc:
                errors[kind+':'+method] = str(exc)
        if kind not in available:
            warnings.append(f'{kind}: UNAVAILABLE — no fresh, complete verified window; NO TRADE')
    return available, errors, warnings
