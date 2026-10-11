"""Bounded, read-only probes. Reachability never certifies exchange wallet coverage."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import requests


def targets():
    base = 'https://community-api.coinmetrics.io/v4'
    start = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    result = []
    for asset in ('btc', 'eth'):
        for scope, metrics in (('provider-labelled exchanges', 'FlowInExNtv,FlowOutExNtv'),
                               ('provider-labelled Kraken', 'FlowInKRKNtv,FlowOutKRKNtv')):
            result.append((f'Coin Metrics {asset} {scope}', base+'/timeseries/asset-metrics',
                           {'assets': asset, 'metrics': metrics, 'frequency': '1d', 'start_time': start, 'page_size': 100}))
    result += [
        ('Coin Metrics metric catalog', base+'/catalog/metrics', {'metrics': 'FlowInExNtv,FlowOutExNtv,FlowInKRKNtv,FlowOutKRKNtv'}),
        ('Coin Metrics asset coverage', base+'/catalog/asset-metrics', {}),
        ('Coin Metrics API documentation', 'https://docs.coinmetrics.io/api/v4/', {}),
        ('DefiLlama CEX dashboard', 'https://defillama.com/cexs', {}),
        ('DefiLlama public CEX protocol candidate', 'https://api.llama.fi/protocol/binance-cex', {}),
        ('DefiLlama API documentation', 'https://api-docs.defillama.com/', {}),
        ('Glassnode BTC exchange transfer metric', 'https://api.glassnode.com/v1/metrics/transactions/transfers_volume_to_exchanges_sum', {'a': 'BTC', 'i': '24h'}),
        ('CryptoQuant BTC exchange inflow candidate', 'https://api.cryptoquant.com/v1/btc/exchange-flows/inflow', {'exchange': 'all_exchange', 'window': 'day', 'limit': 2}),
        ('Glassnode documentation', 'https://docs.glassnode.com/', {}),
        ('CryptoQuant documentation', 'https://userguide.cryptoquant.com/', {}),
        ('Mempool public BTC block metadata', 'https://mempool.space/api/blocks', {}),
        ('Etherscan ETH supply candidate', 'https://api.etherscan.io/v2/api', {'chainid': 1, 'module': 'stats', 'action': 'ethsupply'}),
    ]
    return result


def probe(target):
    name, url, params = target
    report = {'name': name, 'requested_url': url, 'params': params,
              'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'safety_eligible': False, 'coverage_verified': False}
    try:
        response = requests.get(url, params=params, timeout=12, allow_redirects=False)
        report.update(url=response.url, http_status=response.status_code,
                      content_type=response.headers.get('Content-Type'),
                      headers={k: v for k, v in response.headers.items() if any(
                          token in k.lower() for token in ('ratelimit', 'retry-after', 'last-modified', 'date', 'location'))})
        if 'json' in response.headers.get('Content-Type', ''):
            body = response.json()
            if name == 'Coin Metrics asset coverage' and isinstance(body, dict) and isinstance(body.get('data'), list):
                body = {'data': [row for row in body['data'] if row.get('metric') in ('FlowInExNtv', 'FlowOutExNtv', 'FlowInKRKNtv', 'FlowOutKRKNtv')]}
                report['response_filtered_to_flow_metrics'] = True
            report['response'] = body
        else:
            report['body_excerpt'] = response.text[:400]
    except (requests.RequestException, ValueError) as exc:
        report['error'] = str(exc)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/free-exchange-flow-probes.json'))
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(probe, targets()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2)+'\n')
    for report in reports:
        print(report['name'], report.get('http_status'), report.get('error', '')[:160])
    print('Diagnostics only: no source is safety-approved by this probe.')

if __name__ == '__main__':
    main()
