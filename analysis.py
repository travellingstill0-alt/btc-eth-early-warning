"""Deterministic, configurable informational heuristics; never executes trades."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from oi_history import calculate_changes
from hashlib import sha256
from math import isfinite
from context_data import parse as parse_context
from macro_calendar import CalendarRules, evaluate as evaluate_calendar

NO_TRADE_HOLD = True

# All three remain mandatory; exchange flows have no verified integration.
REQUIRED_CONTEXT = ('CVD', 'liquidation data', 'exchange flows')

def data_digest(data):
    return sha256(repr(data).encode()).hexdigest()

@dataclass
class Rules:
    move_pct: float = 4.0
    funding_pct: float = 0.03
    oi_growth_pct: float = 10.0
    stale_seconds: int = 180
    oi_window: str = '24h'
    macro_pre_minutes: int = 60
    macro_post_minutes: int = 60
    macro_max_age_seconds: int = 900
    macro_horizon_hours: int = 24


def closed(rows, now_ms):
    return [r for r in rows if int(r[6]) < now_ms]


def assess(data, rules, now=None):
    now = now or datetime.now(timezone.utc)
    ms = now.timestamp() * 1000
    reasons, missing, score = [], [], 0
    context = {}
    for label in REQUIRED_CONTEXT:
        key = {'CVD': 'cvd', 'liquidation data': 'liquidations'}.get(label)
        if key:
            try:
                item = data[key]
                if item['asset'] != data['symbol'][:3]:
                    raise ValueError('Wrong context asset')
                context[key] = parse_context(item, ms, rules.stale_seconds)
                continue
            except (KeyError, TypeError, ValueError, OverflowError, IndexError, AttributeError):
                pass
        missing.append(label)
    for key in ('ticker', 'candles', 'scalp_candles', 'funding', 'interest', 'interest_history', 'trades'):
        if not data.get(key):
            missing.append(key)
    try:
        age = (now - data['retrieved_at']).total_seconds()
        if age < -5 or age > rules.stale_seconds:
            missing.append('stale retrieval')
    except (KeyError, TypeError, AttributeError):
        missing.append('unknown retrieval timestamp')
    snapshot_verified = not any(x in missing for x in ('stale retrieval', 'unknown retrieval timestamp'))
    for key, field in [('ticker', 'closeTime'), ('funding', 'time'), ('interest', 'time')]:
        if data.get(key) and not -5 <= (ms - int(data[key].get(field, 0))) / 1000 <= rules.stale_seconds:
            missing.append(f'stale {key}')
    for key, limit in [('ticker', rules.stale_seconds), ('funding', rules.stale_seconds),
                       ('interest', rules.stale_seconds), ('trades', rules.stale_seconds),
                       ('candles', 7200), ('scalp_candles', 600)]:
        if data.get(key):
            source_time = data.get('sources', {}).get(key, {}).get('source_time_ms')
            if source_time is None:
                missing.append(f'unknown timestamp {key}')
            elif not -5 <= (ms - source_time) / 1000 <= limit:
                missing.append(f'stale {key}')
    trades = data.get('trades', [])
    if trades and not -5000 <= ms - int(trades[-1].get('T', 0)) <= rules.stale_seconds * 1000:
        missing.append('stale order flow')
    for key, step in [('candles', 3600000), ('scalp_candles', 300000)]:
        finished = closed(data.get(key, []), ms)
        if len(finished) < 21:
            missing.append(f'insufficient {key}')
        elif ms - int(finished[-1][6]) > step * 2:
            missing.append(f'stale {key}')
        required = 40 if key == 'candles' else 21
        recent = finished[-required:]
        if any(int(b[0]) - int(a[0]) != step for a, b in zip(recent, recent[1:])):
            missing.append(f'gaps in {key}')
    move = data.get('ticker', {}).get('priceChangePercent')
    if move is None:
        missing.append('24h price change')
    def usable_number(value):
        try:
            return not isinstance(value, bool) and isfinite(float(value))
        except (TypeError, ValueError, OverflowError):
            return False

    if move is not None and not usable_number(move):
        missing.append('invalid 24h price change')
    move_verified = snapshot_verified and usable_number(move) and not any(x in missing for x in
        ('stale retrieval', 'stale ticker', 'unknown timestamp ticker'))
    if move_verified and abs(float(move)) >= rules.move_pct:
        score += 2
        reasons.append('Large absolute 24h price move (+2)')
    funding = data.get('funding', {})
    period = funding.get('period_hours', 8)
    if period not in (1, 8):
        missing.append('unknown funding period')
    funding_verified = snapshot_verified and bool(funding) and period in (1, 8) and usable_number(funding.get('lastFundingRate')) and not any(x in missing for x in
        ('stale retrieval', 'stale funding', 'unknown timestamp funding'))
    if funding and not usable_number(funding.get('lastFundingRate')):
        missing.append('invalid funding rate')
    if funding_verified and abs(float(funding['lastFundingRate']) * 100) >= rules.funding_pct * period / 8:
        score += 2
        reasons.append(f'Elevated absolute funding over {period}h (+2)')
    oi_changes = calculate_changes(data, int(ms), rules.stale_seconds)
    selected = oi_changes.get(rules.oi_window)
    oi_change = selected['change_pct'] if selected else None
    oi_verified = snapshot_verified and oi_change is not None and not any(x in missing for x in
        ('stale retrieval', 'stale interest', 'unknown timestamp interest'))
    if oi_verified:
        if oi_change >= rules.oi_growth_pct:
            score += 2
            reasons.append(f'Rapid {rules.oi_window} open interest growth (+2)')
    elif oi_change is None:
        missing.append(f'OI {rules.oi_window}: ' + (selected['reason'] if selected else 'unknown required window'))
    bars = closed(data.get('candles', []), ms)
    structure = 'Unavailable'
    structure_verified = snapshot_verified and len(bars) >= 40 and not any(x in missing for x in
        ('stale retrieval', 'stale candles', 'unknown timestamp candles', 'gaps in candles'))
    if structure_verified:
        recent, previous = bars[-20:], bars[-40:-20]
        rh, ph = max(float(r[2]) for r in recent), max(float(r[2]) for r in previous)
        rl, pl = min(float(r[3]) for r in recent), min(float(r[3]) for r in previous)
        structure = 'Higher range highs and lows' if rh > ph and rl > pl else 'Lower range highs and lows' if rh < ph and rl < pl else 'Mixed / range'
        if structure == 'Lower range highs and lows':
            score += 1
            reasons.append('Bearish hourly range structure (+1)')
    elif len(bars) < 40:
        missing.append('insufficient structure candles')
    observed_level = ('EXTREME' if score >= 6 else 'HIGH' if score >= 4 else 'MODERATE' if score >= 2 else 'LOW') if any(
        (move_verified, funding_verified, oi_verified, structure_verified)) else 'UNKNOWN'
    macro = evaluate_calendar(data.get('macro_calendar'), now,
        CalendarRules(rules.macro_pre_minutes, rules.macro_post_minutes,
                      rules.macro_max_age_seconds, rules.macro_horizon_hours))
    overall_missing = sorted(set(missing + ['Macro: ' + item for item in macro['missing']]))
    if not macro['clear'] and not macro['high_risk'] and not macro['missing']:
        overall_missing.append('Macro: coverage unverified')
    overall_level = 'UNKNOWN' if overall_missing else observed_level
    if overall_level != 'UNKNOWN' and macro['high_risk'] and overall_level in ('LOW', 'MODERATE'):
        overall_level = 'HIGH'
    return {'level': overall_level, 'overall_level': overall_level, 'observed_level': observed_level,
            'overall_missing': overall_missing, 'macro_high_risk': macro['high_risk'],
            'observed_score': score if observed_level != 'UNKNOWN' else None,
            'observed_indicator_count': sum((move_verified, funding_verified, oi_verified, structure_verified)),
            'score': score, 'reasons': reasons, 'missing': sorted(set(missing)), 'structure': structure,
            'oi_change': oi_change, 'oi_changes': oi_changes, 'oi_window': rules.oi_window,
            'context': context, 'assessed_at_ms': ms, 'rules': asdict(rules), 'data_digest': data_digest(data)}


def plan(data, risk, timeframe, macro_clear=False, now=None):
    now = now or datetime.now(timezone.utc)
    ms = now.timestamp() * 1000
    output = {'status': 'NO TRADE', 'reason': 'Missing or stale data, high risk, or macro events not reviewed.', 'reason_code': 'MISSING_DATA'}
    try:
        rules = Rules(**risk['rules'])
        assessment_age = (ms - risk['assessed_at_ms']) / 1000
        if not 0 <= assessment_age <= rules.stale_seconds or risk['data_digest'] != data_digest(data):
            return dict(status='NO TRADE', reason='Expired or outdated risk assessment.', reason_code='MISSING_DATA')
        risk = assess(data, rules, now)
        rows = closed(data.get('scalp_candles' if timeframe == 'SCALP' else 'candles', []), ms)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return dict(status='NO TRADE', reason='Invalid or missing risk assessment or market data.', reason_code='MISSING_DATA')
    macro = evaluate_calendar(data.get('macro_calendar'), now,
        CalendarRules(rules.macro_pre_minutes, rules.macro_post_minutes,
                      rules.macro_max_age_seconds, rules.macro_horizon_hours))
    missing = bool(risk['overall_missing']) or len(rows) < 21
    high_risk = risk['observed_level'] in ('HIGH', 'EXTREME') or bool(macro['high_risk'])
    if missing or high_risk or not macro['clear'] or not macro_clear:
        output['reason_code'] = 'HIGH_RISK_AND_MISSING_DATA' if high_risk and missing else 'HIGH_RISK' if high_risk else 'MISSING_DATA' if missing else 'MANUAL_REVIEW_REQUIRED'
        output['reason'] = ('High risk: ' + '; '.join(macro['high_risk'] or [risk['observed_level']]) + '. ' if high_risk else '') + ('Missing/stale inputs: ' + ', '.join(risk['overall_missing']) + '. ' if missing else '') + ('Manual macro review required.' if not macro_clear else '')
        return output
    if NO_TRADE_HOLD:
        return dict(status='NO TRADE', reason='Research hold active: required inputs and global coverage remain unverified.', reason_code='RESEARCH_HOLD')
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
