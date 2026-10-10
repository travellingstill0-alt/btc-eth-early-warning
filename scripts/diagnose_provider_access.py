"""Read-only proxy/provider diagnosis; never changes permissions or credentials."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from macro_calendar import source_specs, BOGOTA
from exchange_flows import BASE, PATH, METRICS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/provider-access-diagnosis.json'))
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    policy=json.loads(Path('/etc/codex/network-policy.json').read_text())
    permitted={r['host'] for r in policy['http_network_policy']['egress_rules']}
    targets=[('Kraken public control','https://api.kraken.com/0/public/Time',{}),
             ('Coinbase public control','https://api.exchange.coinbase.com/time',{}),
             ('Binance public control','https://fapi.binance.com/fapi/v1/time',{}),
             ('Coin Metrics official documentation','https://raw.githubusercontent.com/coinmetrics/product-docs/master/docs/packages/coin-metrics-community-data.md',{})]
    for asset in ('btc','eth'):
        targets.append(('Coin Metrics '+asset.upper(),BASE+PATH,dict(assets=asset,metrics=','.join(METRICS),
                       frequency='1d',limit_per_asset=2,page_size=2,sort='desc')))
    targets.extend((name,url,{}) for name,url,_ in source_specs(now))
    rows=[]
    for name,url,params in targets:
        row=dict(name=name,url=url,params=params,host_allowed_in_snapshot=urlparse(url).hostname in permitted,
                 provider_http_status=None,result='UNKNOWN',key_used=False)
        try:
            response=requests.get(url,params=params,timeout=4,allow_redirects=False)
            row.update(provider_http_status=response.status_code,content_type=response.headers.get('Content-Type'),
                       response_excerpt=response.text[:350])
            status=response.status_code
            row['result']='REACHABLE' if status==200 else 'REDIRECT_NOT_FOLLOWED' if 300<=status<400 else 'AUTHENTICATION_REQUIRED' if status==401 else 'PROVIDER_ACCESS_DENIED' if status==403 else 'QUOTA_OR_RATE_LIMIT' if status==429 else 'REGIONAL_OR_LEGAL_RESTRICTION' if status==451 else 'HTTP_ERROR'
        except requests.exceptions.ProxyError as exc:
            row.update(result='PROXY_POLICY_DENIAL' if '403 Forbidden' in str(exc) else 'PROXY_ERROR',error=str(exc))
        except requests.RequestException as exc:
            row.update(result='TRANSPORT_ERROR',error=str(exc))
        rows.append(row)
        print(name,row['result'],row['provider_http_status'])
    result=dict(checked_at_colombia=datetime.now(timezone.utc).astimezone(BOGOTA).isoformat(),
                policy_mode=policy['http_network_policy']['type'],rows=rows,
                safety='NO TRADE: no verified exchange-flow or complete macro-calendar coverage')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__': main()
