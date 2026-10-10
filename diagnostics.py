"""Classify observed failures without confusing local policy and provider responses."""
import requests


def failure_details(exc):
    status = getattr(getattr(exc, 'response', None), 'status_code', None)
    message = str(exc)
    if isinstance(exc, requests.exceptions.ProxyError) and 'Tunnel connection failed: 403' in message:
        category = 'network_policy_blocked'
        action = 'Review the cloud environment allowed hosts. The provider was not reached.'
    elif isinstance(exc, requests.exceptions.ProxyError):
        category = 'proxy_unavailable'
        action = 'Check the cloud environment proxy; provider reachability is unverified.'
    elif status == 451:
        category = 'provider_restricted'
        action = 'Provider refused access. Keep this source unavailable; do not bypass restrictions.'
    elif status in (401, 403):
        category = 'http_access_denied'
        action = 'Access was denied. Do not assume a geographic cause without the response details.'
    elif status == 429:
        category = 'rate_limited'
        action = 'Retry after the provider cooldown; keep unavailable data explicit.'
    elif isinstance(exc, requests.Timeout):
        category = 'timeout'
        action = 'Request timed out; keep this source unavailable.'
    elif isinstance(exc, ValueError):
        category = 'invalid_payload'
        action = 'Payload failed validation; do not display it as market data.'
    else:
        category = 'request_failed'
        action = 'Request failed; keep this source unavailable.'
    return {'category': category, 'http_status': status, 'action': action}
