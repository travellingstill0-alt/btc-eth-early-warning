"""Read-only live availability checks; diagnostics cannot approve a provider."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exchange_flows import collect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/exchange-flow-live.json'))
    args = parser.parse_args()
    reports = []
    for asset in ('BTC', 'ETH'):
        attempts = []
        def request(base, path, **params):
            attempt = dict(url=base+path, params=params, http_status=None)
            attempts.append(attempt)
            try:
                response = requests.get(base+path, params=params, timeout=12)
                attempt['http_status'] = response.status_code
                response.raise_for_status()
                body = response.json()
                attempt['response'] = body
                return body
            except (requests.RequestException, ValueError) as exc:
                attempt['error'] = str(exc)
                raise ValueError(str(exc)) from exc
        report = collect(request, asset, lambda: int(datetime.now(timezone.utc).timestamp()*1000))
        reports.append(dict(report=report, attempts=attempts))
        print(asset, report['status'], report.get('error', report['reason']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2)+'\n')
    # Nonzero explicitly means provider responses were NOT live-validated.
    return int(any(r['report']['status'] == 'unavailable' for r in reports))


if __name__ == '__main__':
    raise SystemExit(main())
