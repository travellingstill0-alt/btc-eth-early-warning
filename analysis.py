"""Deterministic, configurable informational heuristics; never executes trades."""
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class Rules:
    move_pct: float = 4.0
    funding_pct: float = 0.03
    oi_growth_pct: float = 10.0
    stale_seconds: int = 180


def closed(rows, now_ms):
    return [r for r in rows if int(r[6]) < now_ms]


def assess(data, rules, now=None):
    now = now or datetime.now(timezone.utc)
    ms = now.timestamp() * 1000
    reasons, missing, score = [], [], 0
    for key in ('ticker', 'candles', 'scalp_candles', 'funding', 'interest', 'interest_history', 'trades'):
        if not data.get(key):
            missing.append(key)
    age = (now - data['retrieved_at']).total_seconds()
    if age > rules.stale_seconds:
        missing.append('stale retrieval')
    for key, field in [('ticker', 'closeTime'), ('funding', 'time'), ('interest', 'time')]:
        if data.get(key) and (ms - int(data[key].get(field, 0))) / 1000 > rules.stale_seconds:
            missing.append(f'stale {key}')
    trades = data.get('trades', [])
    if trades and ms - int(trades[-1].get('T', 0)) > rules.stale_seconds * 1000:
        missing.append('stale order flow')
    for key, step in [('candles', 3600000), ('scalp_candles', 300000)]:
        finished = closed(data.get(key, []), ms)
        if len(finished) < 21:
            missing.append(f'insufficient {key}')
        elif ms - int(finished[-1][6]) > step * 2:
            missing.append(f'stale {key}')
    if data.get('ticker') and abs(float(data['ticker']['priceChangePercent'])) >= rules.move_pct:
        score += 2
        reasons.append('Large absolute 24h price move (+2)')
    if data.get('funding') and abs(float(data['funding']['lastFundingRate']) * 100) >= rules.funding_pct:
        score += 2
        reasons.append('Elevated absolute funding (+2)')
    history = data.get('interest_history', [])
    oi_change = None
    if len(history) >= 2 and float(history[0]['sumOpenInterest']) > 0:
        oi_change = (float(history[-1]['sumOpenInterest']) / float(history[0]['sumOpenInterest']) - 1) * 100
        if oi_change >= rules.oi_growth_pct:
            score += 2
            reasons.append('Rapid open interest growth (+2)')
        if ms - int(history[-1]['timestamp']) > 2 * 3600 * 1000:
            missing.append('stale interest history')
    else:
        missing.append('insufficient interest history')
    bars = closed(data.get('candles', []), ms)
    structure = 'Unavailable'
    if len(bars) >= 40:
        recent, previous = bars[-20:], bars[-40:-20]
        rh, ph = max(float(r[2]) for r in recent), max(float(r[2]) for r in previous)
        rl, pl = min(float(r[3]) for r in recent), min(float(r[3]) for r in previous)
        structure = 'Higher range highs and lows' if rh > ph and rl > pl else 'Lower range highs and lows' if rh < ph and rl < pl else 'Mixed / range'
        if structure == 'Lower range highs and lows':
            score += 1
            reasons.append('Bearish hourly range structure (+1)')
    else:
        missing.append('insufficient structure candles')
    level = 'EXTREME' if score >= 6 else 'HIGH' if score >= 4 else 'MODERATE' if score >= 2 else 'LOW'
    return {'level': level, 'score': score, 'reasons': reasons, 'missing': sorted(set(missing)), 'structure': structure, 'oi_change': oi_change}


def plan(data, risk, timeframe, macro_clear=False, now=None):
    now = now or datetime.now(timezone.utc)
    ms = now.timestamp() * 1000
    rows = closed(data.get('scalp_candles' if timeframe == 'SCALP' else 'candles', []), ms)
    output = {'status': 'NO TRADE', 'reason': 'Missing or stale data, high risk, or macro events not reviewed.'}
    if risk['missing'] or risk['level'] in ('HIGH', 'EXTREME') or not macro_clear or len(rows) < 21:
        return output
    step = 300000 if timeframe == 'SCALP' else 3600000
    if ms - int(rows[-1][6]) > step * 2:
        output['reason'] = 'Signal candles are stale.'
        return output
    reference, last = rows[-21:-1], rows[-1]
    high, low = max(float(r[2]) for r in reference), min(float(r[3]) for r in reference)
    close = float(last[4])
    volumes = [float(r[5]) for r in reference]
    confirmed_volume = float(last[5]) > sum(volumes) / len(volumes) * 1.2
    direction = 'LONG' if close > high else 'SHORT' if close < low else None
    output = {'status': 'WAIT', 'reason': 'Await closed-candle breakout and volume confirmation.', 'resistance': high, 'support': low,
              'confirmation': 'Closed candle beyond the previous 20-bar range with volume > 1.2× its average; macro review required.'}
    if direction and confirmed_volume:
        distance = abs(close - (low if direction == 'LONG' else high))
        sign = 1 if direction == 'LONG' else -1
        output.update(status='ENTER', reason='Historical closed-candle confirmation met; informational only, reassess current execution conditions.', direction=direction,
                      reference_entry=close, invalidation=low if sign == 1 else high,
                      target_1=close + sign * distance, target_2=close + sign * distance * 2)
    return output
