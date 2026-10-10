"""Direct public GET probes. No credentials, paid services, fallback routing or trading.

Run from repository root. HTTP success alone does not verify data semantics or
freshness. Raw response fields are reported as observations, never normalized into
Binance units. This script is deliberately separate from the dashboard data path.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnostics import failure_details


def candidates():
    items = []
    for asset, pair in [('BTC', 'XBTUSD'), ('ETH', 'ETHUSD')]:
        items.append({'provider': 'Kraken spot', 'asset': asset, 'metrics': ['spot price', '24h base volume'],
                      'url': 'https://api.kraken.com/0/public/Ticker', 'params': {'pair': pair}})
        for endpoint, metrics in [('ticker', ['spot price', '24h base volume', 'last trade time']),
                                  ('stats', ['24h base volume', '24h open and last prices'])]:
            items.append({'provider': 'Coinbase Exchange', 'asset': asset, 'metrics': metrics,
                          'url': f'https://api.exchange.coinbase.com/products/{asset}-USD/{endpoint}', 'params': {}})
        items.append({'provider': 'Deribit', 'asset': asset, 'metrics': ['perpetual price', '24h volume', 'open interest', 'funding'],
                      'url': 'https://www.deribit.com/api/v2/public/ticker',
                      'params': {'instrument_name': asset + '-PERPETUAL'}})
    items.append({'provider': 'Kraken futures', 'asset': 'BTC and ETH',
                  'metrics': ['perpetual price', '24h volume', 'open interest', 'funding'],
                  'url': 'https://futures.kraken.com/derivatives/api/v3/tickers', 'params': {}})
    return items


def policy_evidence(path='/etc/codex/network-policy.json'):
    """Read only non-secret destination policy; never treat it as a live grant."""
    expected = sorted({urlparse(item['url']).hostname for item in candidates()})
    evidence = {'expected_provider_hosts': expected, 'snapshot_available': False,
                'host_snapshot': {host: None for host in expected}}
    try:
        policy = json.loads(Path(path).read_text())
        if policy.get('version') != 1:
            evidence['reason'] = 'Unsupported network-policy snapshot version'
            return evidence
        http = policy['http_network_policy']
        if http['type'] not in ('restricted', 'unrestricted'):
            raise ValueError('Unsupported HTTP policy type')
        hosts = {rule['host'] for rule in http.get('egress_rules', [])}
        evidence.update(snapshot_available=True, version=1, mode=http['type'],
                        host_snapshot={host: http['type'] == 'unrestricted' or host in hosts for host in expected},
                        note='Startup policy snapshot only. Actual request results remain authoritative.')
    except (OSError, ValueError, KeyError, TypeError):
        evidence['reason'] = 'Network-policy snapshot unavailable or malformed'
    return evidence


def probe(candidate):
    start = time.monotonic()
    result = dict(candidate, checked_at_utc=datetime.now(timezone.utc).isoformat(), http_status=None)
    try:
        response = requests.get(candidate['url'], params=candidate['params'], timeout=12, allow_redirects=False)
        result['http_status'] = response.status_code
        response.raise_for_status()
        if response.status_code != 200:
            result.update(status='unexpected_http_status', usable_for_dashboard=False)
            return result
        payload = response.json()
        if not isinstance(payload, dict) or not payload or payload.get('error') or payload.get('message') or payload.get('result') == 'error':
            raise ValueError('Empty, non-object or API-error payload')
        result.update(status='http_json_received_not_integrated', usable_for_dashboard=False,
                      response_observation=payload,
                      note='Connectivity only. Validate instrument identity, units, period and source freshness before integration.')
    except (requests.RequestException, ValueError) as exc:
        details = failure_details(exc)
        if result['http_status'] is not None:
            details['http_status'] = result['http_status']
        result.update(details, status='failed', error=f'{type(exc).__name__}: {exc}', usable_for_dashboard=False)
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - start, 3)
        result['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        result['metric_verification'] = {metric: {
            'status': 'unverified' if result.get('status') == 'http_json_received_not_integrated' else 'unavailable',
            'source_timestamp_utc': None, 'freshness': 'unverified',
            'reason': result.get('category', result.get('note', result.get('status')))
        } for metric in candidate['metrics']}
        result['timestamp_note'] = 'Request times are diagnostics only; they are not market-source timestamps.'
    return result


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(probe, candidates()))
    print(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                      'scope': 'Direct provider connectivity, not dashboard integration or deployment',
                      'network_policy_evidence': policy_evidence(),
                      'results': results}, indent=2))
    return 1 if any(r['status'] != 'http_json_received_not_integrated' for r in results) else 0


if __name__ == '__main__':
    sys.exit(main())
