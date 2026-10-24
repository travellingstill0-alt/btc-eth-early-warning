"""Read-only public Binance endpoints. No credentials or trading operations."""
from datetime import datetime, timezone
import requests

SPOT = 'https://api.binance.com'
FUTURES = 'https://fapi.binance.com'

def get(base, path, **params):
    response = requests.get(base + path, params=params, timeout=12)
    response.raise_for_status()
    return response.json()

def fetch(symbol):
    result = {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {}}
    endpoints = {
        'ticker': (SPOT, '/api/v3/ticker/24hr', {}),
        'candles': (SPOT, '/api/v3/klines', {'interval': '1h', 'limit': 100}),
        'scalp_candles': (SPOT, '/api/v3/klines', {'interval': '5m', 'limit': 100}),
        'fifteen_min_candles': (SPOT, '/api/v3/klines', {'interval': '15m', 'limit': 100}),
        'trades': (SPOT, '/api/v3/aggTrades', {'limit': 1000}),
        'interest': (FUTURES, '/fapi/v1/openInterest', {}),
        'funding': (FUTURES, '/fapi/v1/premiumIndex', {}),
        'interest_history': (FUTURES, '/futures/data/openInterestHist', {'period': '1h', 'limit': 25}),
    }
    for key, (base, path, params) in endpoints.items():
        try:
            result[key] = get(base, path, symbol=symbol, **params)
        except (requests.RequestException, ValueError) as exc:
            result['errors'][key] = f'{type(exc).__name__}: {exc}'
    return result
