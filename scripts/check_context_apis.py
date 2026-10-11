"""Read-only verification of actual primary and fallback context responses."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from context_data import collect, parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/btc-eth-context-check.json'))
    args = parser.parse_args()
    reports = []
    for mode in ('primary', 'cvd_fallback', 'liquidation_fallback'):
        for asset in ('BTC', 'ETH'):
            attempts = []
            def request(base, path, **params):
                if (mode == 'cvd_fallback' and path.endswith('/cvd')) or (
                        mode == 'liquidation_fallback' and path.endswith('/liquidation-volume')):
                    raise ValueError('Simulated primary outage; secondary observations remain real')
                attempt = dict(url=base+path, params=params, http_status=None)
                attempts.append(attempt)
                try:
                    response = requests.get(base+path, params=params, timeout=12)
                    attempt['http_status'] = response.status_code
                    response.raise_for_status()
                    return response.json()
                except (requests.RequestException, ValueError) as exc:
                    attempt['error'] = str(exc)
                    raise ValueError(str(exc)) from exc
            clock = lambda: int(datetime.now(timezone.utc).timestamp()*1000)
            data, errors, warnings = collect(request, asset, clock)
            summary = {k: {field: v[field] for field in (
                'provider', 'instrument', 'unit', 'method', 'start_ms', 'end_ms', 'received_at_ms')}
                | dict(observations=parse(v, clock())) for k, v in data.items()}
            report = dict(mode=mode, asset=asset, observations=summary,
                          errors=errors, warnings=warnings, attempts=attempts)
            reports.append(report)
            print(mode, asset, summary, errors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2)+'\n')
    # A secondary with unverifiable coverage must stay unavailable, never turn into zero.
    return int(any(len(r['observations']) != 2 for r in reports if r['mode'] == 'primary'))


if __name__ == '__main__':
    raise SystemExit(main())
