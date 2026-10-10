"""Read-only live checks, including real secondary requests under simulated primary outages."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from market import fetch
from analysis import Rules, assess, plan


def check(mode, symbol, history_path=None):
    original = requests.get
    def fallback_request(url, **kwargs):
        if (mode == 'spot_fallback' and 'coinbase' in url) or (
            mode == 'other_fallbacks' and 'kraken' in url) or (
            mode == 'history_fallback' and '/open-interest' in url):
            raise requests.ConnectionError('Simulated primary outage for live fallback validation')
        return original(url, **kwargs)
    with patch('market.requests.get', side_effect=fallback_request):
        data = fetch(symbol, history_path=history_path)
    now = datetime.now(timezone.utc)
    risk = assess(data, Rules(), now)
    return dict(mode=mode, symbol=symbol, checked_at=now.isoformat(),
                indicators={key: {'available': key in data,
                                   'source': data['sources'].get(key),
                                   'value': data.get(key) if key not in ('candles', 'scalp_candles', 'trades', 'interest_history') else None,
                                   'count': len(data.get(key, [])) if key in ('candles', 'scalp_candles', 'trades', 'interest_history') else None}
                            for key in ('ticker', 'candles', 'scalp_candles', 'interest', 'funding', 'trades', 'interest_history')},
                attempts=data['attempts'], errors=data['errors'], warnings=data['warnings'], risk=risk,
                signals={h: plan(data, risk, h, macro_clear=True, now=now) for h in ('SCALP', 'DAY TRADE')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/btc-eth-live-check.json'))
    parser.add_argument('--history-db', type=Path, help='Persistent OI snapshot database; defaults to the app store')
    args = parser.parse_args()
    reports = [check(mode, symbol, args.history_db) for mode in ('normal', 'spot_fallback', 'other_fallbacks', 'history_fallback')
               for symbol in ('BTCUSD', 'ETHUSD')]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2) + '\n')
    for r in reports:
        print(r['mode'], r['symbol'], {k: v['available'] for k, v in r['indicators'].items()},
              {h: p['status'] for h, p in r['signals'].items()})
        for a in r['attempts']:
            print(' ', a['http_status'], a['url'], a.get('error', ''))
        print(' Missing:', r['risk']['missing'])
        print(' OI changes:', {w: v['change_pct'] for w, v in r['risk']['oi_changes'].items()})
    # History fallback must fail closed during warmup; normal Kraken history should be ready.
    inputs_failed = any(not v['available'] for r in reports for k, v in r['indicators'].items()
                        if k != 'interest_history')
    history_failed = any(v['change_pct'] is None for r in reports if r['mode'] == 'normal'
                         for v in r['risk']['oi_changes'].values())
    unsafe_fallback = any(p['status'] != 'NO TRADE' for r in reports
                          if r['risk']['missing'] for p in r['signals'].values())
    return int(inputs_failed or history_failed or unsafe_fallback)


if __name__ == '__main__':
    raise SystemExit(main())
