"""Read-only public Binance endpoints. No credentials or trading operations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import math
import requests
from diagnostics import failure_details

SPOT = 'https://api.binance.com'
FUTURES = 'https://fapi.binance.com'
ENDPOINTS = {
    'ticker': (SPOT, '/api/v3/ticker/24hr', {}),
    'candles': (SPOT, '/api/v3/klines', {'interval': '1h', 'limit': 100}),
    'scalp_candles': (SPOT, '/api/v3/klines', {'interval': '5m', 'limit': 100}),
    'trades': (SPOT, '/api/v3/aggTrades', {'limit': 1000}),
    'interest': (FUTURES, '/fapi/v1/openInterest', {}),
    'funding': (FUTURES, '/fapi/v1/premiumIndex', {}),
    'interest_history': (FUTURES, '/futures/data/openInterestHist', {'period': '1h', 'limit': 25}),
}


def number(value, minimum=None):
    if isinstance(value, bool):
        raise ValueError('Boolean numeric field')
    n = float(value)
    if not math.isfinite(n) or (minimum is not None and n < minimum):
        raise ValueError('Non-finite or out-of-range numeric field')
    return n


def validate(key, value, symbol):
    """Reject incomplete, wrong-symbol and malformed responses per endpoint."""
    try:
        if key in ('ticker', 'interest', 'funding'):
            if value['symbol'] != symbol:
                raise ValueError('Wrong response symbol')
            fields = {'ticker': ('lastPrice', 'priceChangePercent', 'quoteVolume', 'closeTime'),
                      'interest': ('openInterest', 'time'),
                      'funding': ('lastFundingRate', 'time')}[key]
            for field in fields:
                number(value[field], None if field in ('priceChangePercent', 'lastFundingRate') else 0)
            number(value['closeTime' if key == 'ticker' else 'time'], 1)
            if key == 'ticker':
                number(value['lastPrice'], 1e-300)
        else:
            if not isinstance(value, list) or not value:
                raise ValueError('Empty or non-list response')
            timestamps = []
            for row in value:
                if key in ('candles', 'scalp_candles'):
                    for i in (0, 1, 2, 3, 4, 5, 6):
                        number(row[i], 0)
                    if number(row[6]) <= number(row[0]) or number(row[2]) < number(row[3]):
                        raise ValueError('Invalid candle range')
                    timestamps.append(number(row[0]))
                elif key == 'trades':
                    number(row['q'], 0)
                    if not isinstance(row['m'], bool):
                        raise ValueError('Invalid maker flag')
                    timestamps.append(number(row['T'], 1))
                else:
                    if row['symbol'] != symbol:
                        raise ValueError('Wrong history symbol')
                    number(row['sumOpenInterest'], 0)
                    timestamps.append(number(row['timestamp'], 1))
            if timestamps != sorted(timestamps):
                raise ValueError('Unordered source timestamps')
    except (KeyError, IndexError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed ' + key + ' response') from exc
    return value


def get(base, path, **params):
    response = requests.get(base + path, params=params, timeout=12)
    response.raise_for_status()
    return response.json()


def fetch(symbol):
    if symbol not in ('BTCUSDT', 'ETHUSDT'):
        raise ValueError('Unsupported symbol')
    result = {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {}, 'source_retrieved_at': {}, 'source_failures': {}}
    def retrieve(item):
        key, (base, path, params) = item
        try:
            value = validate(key, get(base, path, symbol=symbol, **params), symbol)
            return key, value, None, datetime.now(timezone.utc).isoformat(), None
        except (requests.RequestException, ValueError) as exc:
            return key, None, f'{type(exc).__name__}: {exc}', datetime.now(timezone.utc).isoformat(), failure_details(exc)
    with ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as pool:
        for key, value, error, timestamp, failure in pool.map(retrieve, ENDPOINTS.items()):
            result['source_retrieved_at'][key] = timestamp
            if error:
                result['errors'][key] = error
                result['source_failures'][key] = failure
            else:
                result[key] = value
    result['retrieved_at'] = datetime.now(timezone.utc)
    return result
