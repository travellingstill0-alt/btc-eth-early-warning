"""Loss replay primitives. Explicit assumptions, no parameter optimization or orders."""
from dataclasses import dataclass
from math import isfinite

STRATEGIES = [(asset, side, horizon) for asset in ('BTC', 'ETH')
              for side in ('LONG', 'SHORT') for horizon in ('SCALP', 'DAY TRADE')]

@dataclass(frozen=True)
class Costs:
    fee_bps: float
    slippage_bps: float
    evidence: str
    verified: bool = False

    def __post_init__(self):
        if any(not isfinite(v) or v < 0 for v in (self.fee_bps, self.slippage_bps)) or not self.evidence:
            raise ValueError('Finite nonnegative costs and explicit evidence required')


def replay(bars, signal_index, side, stop, target, timeout_bars, costs):
    """One unit linear contract; next-open entry, pessimistic intrabar ordering.

    Bars: time, end, open, high, low, close. Fees on both actual notionals.
    Funding/borrow are excluded and must be supplied separately for a full P&L.
    Excursions on exit bars are bounded, not claimed as exact intrabar paths.
    """
    if side not in ('LONG', 'SHORT') or timeout_bars < 1:
        raise ValueError('Invalid direction or timeout')
    for i, b in enumerate(bars):
        vals = [b[k] for k in ('open', 'high', 'low', 'close')]
        if any(not isfinite(v) or v <= 0 for v in vals) or not b['low'] <= min(b['open'], b['close']) <= max(b['open'], b['close']) <= b['high']:
            raise ValueError('Invalid OHLC')
        if b['end'] <= b['time'] or (i and b['time'] != bars[i-1]['end']):
            raise ValueError('Incomplete, duplicate or gapped candles')
    start = signal_index + 1
    if signal_index < 0 or start >= len(bars):
        raise ValueError('No next-open execution data')
    sign = 1 if side == 'LONG' else -1
    slip = costs.slippage_bps / 10000
    entry = bars[start]['open'] * (1 + sign * slip)
    if not all(isfinite(v) and v > 0 for v in (stop, target)) or sign*(entry-stop) <= 0 or sign*(target-entry) <= 0:
        return {'status': 'SKIPPED', 'reason': 'Gap invalidates predeclared stop/target'}
    end = min(start + timeout_bars, len(bars))
    mfe, mae = 0., 0.
    for index in range(start, end):
        b = bars[index]
        favorable = b['high'] if sign == 1 else b['low']
        adverse = b['low'] if sign == 1 else b['high']
        stop_hit = adverse <= stop if sign == 1 else adverse >= stop
        target_hit = favorable >= target if sign == 1 else favorable <= target
        gap_stop = sign*(b['open']-stop) <= 0
        gap_target = sign*(b['open']-target) >= 0
        ambiguous = stop_hit and target_hit and not (gap_stop or gap_target)
        mfe = max(mfe, sign*(favorable-entry)/entry)
        mae = min(mae, sign*(adverse-entry)/entry)
        reason = 'STOP' if gap_stop else 'TARGET' if gap_target else 'STOP' if stop_hit else 'TARGET' if target_hit else None
        if reason:
            raw_exit = b['open'] if gap_stop or gap_target else stop if reason == 'STOP' else target
            break
    else:
        reason = 'TIMEOUT' if end-start == timeout_bars else 'CENSORED'
        raw_exit = bars[end-1]['close']
        ambiguous = False
    exit_price = raw_exit*(1-sign*slip)
    fees = (entry+exit_price)*costs.fee_bps/10000
    gross = sign*(exit_price-entry)
    return dict(status='REPLAYED', side=side, signal_time=bars[signal_index]['end'], entry_time=bars[start]['time'],
                exit_time=bars[index]['end'], entry=entry, exit=exit_price, reason=reason,
                stop_distance_pct=abs(entry-stop)/entry*100, bars_held=index-start+1,
                mfe_upper_pct=mfe*100, mae_lower_pct=mae*100, exit_bar_excursions_uncertain=True,
                ambiguous=ambiguous, gross_pnl=gross, fees=fees, net_pnl=gross-fees,
                slippage_cost=abs(entry-bars[start]['open'])+abs(exit_price-raw_exit),
                costs_verified=costs.verified, costs_evidence=costs.evidence,
                limitations=['Funding and borrow costs excluded', 'No depth/queue fill model'])


def entry_hypothesis(closed_bars, side, context):
    """Fixed research definition, using only completed bars and as-of context.

    20-bar range; two subsequent three-bar ranges form higher low/lower high.
    Retest candle touches range edge and closes back inside. CVD/OI/funding
    must share the traded contract and be available by signal time.
    These definitions are hypotheses, not evidence of profitability.
    """
    if len(closed_bars) < 27 or side not in ('LONG', 'SHORT'):
        return {'eligible': False, 'reason': 'Insufficient completed bars or invalid side'}
    reference, first, second, last = closed_bars[-27:-7], closed_bars[-7:-4], closed_bars[-4:-1], closed_bars[-1]
    support, resistance = min(b['low'] for b in reference), max(b['high'] for b in reference)
    long = side == 'LONG'
    conditions = {
        'support_confirmation' if long else 'resistance_confirmation': last['low'] <= support < last['close'] if long else last['high'] >= resistance > last['close'],
        'higher_low' if long else 'lower_high': min(b['low'] for b in second) > min(b['low'] for b in first) if long else max(b['high'] for b in second) < max(b['high'] for b in first),
        'bullish_structure' if long else 'bearish_structure': max(b['high'] for b in second) > max(b['high'] for b in first) if long else min(b['low'] for b in second) < min(b['low'] for b in first),
    }
    valid = all(context.get(k, {}).get('verified') is True and context[k].get('available_at', float('inf')) <= last['end']
                and context[k].get('end', float('inf')) <= last['end']
                and context[k].get('contract') == context.get('traded_contract') and context.get('traded_contract')
                and isfinite(context[k].get('value', float('nan'))) for k in ('cvd', 'oi', 'funding'))
    conditions['positive_cvd' if long else 'negative_cvd'] = bool(valid and (context['cvd']['value'] > 0 if long else context['cvd']['value'] < 0))
    conditions['oi_funding_assessed'] = bool(valid)
    return {'eligible': all(conditions.values()), 'conditions': conditions,
            'oi': context.get('oi'), 'funding': context.get('funding'),
            'note': 'OI/funding are recorded for stratification; no fitted directional threshold.'}
