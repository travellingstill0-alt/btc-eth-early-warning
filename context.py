"""Read-only context feeds. Neither feed supplies a trading confirmation."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import re
import requests

BLS_URL = 'https://www.bls.gov/schedule/news_release/bls.ics'
FLOW_URL = 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics'
UTC = timezone.utc
METRICS = ('FlowInExNtv', 'FlowOutExNtv')
COVERAGE_GAPS = {
    'US': 'BLS only. Missing Federal Reserve/FOMC decisions, minutes and speeches; BEA GDP/PCE; Census retail sales and other releases.',
    'Europe': 'Missing ECB decisions/speeches, Eurostat inflation/GDP/employment and national calendars.',
    'UK': 'Missing Bank of England decisions/speeches and ONS inflation/GDP/employment/retail sales.',
    'Asia': 'Missing BOJ/Japan statistics, PBOC/China NBS, RBA/Australia ABS and other regional central banks/statistical releases.',
}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a timezone-qualified string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp has no timezone')
    return parsed.astimezone(UTC)


def retrieval_issues(retrieved_at, now, max_age):
    if retrieved_at.tzinfo is None:
        return ['Retrieval timestamp has no timezone']
    age = (now - retrieved_at).total_seconds()
    return ['Future retrieval timestamp'] if age < 0 else ['Stale retrieval'] if age > max_age else []


def calendar(text, retrieved_at, now=None):
    now = now or datetime.now(UTC)
    issues = retrieval_issues(retrieved_at, now, 3600)
    if not isinstance(text, str):
        raise ValueError('Calendar must be text')
    unfolded = re.sub(r'\r?\n[ \t]', '', text)
    if not unfolded.strip().startswith('BEGIN:VCALENDAR') or not unfolded.strip().endswith('END:VCALENDAR'):
        raise ValueError('Incomplete iCalendar envelope')
    blocks = re.findall(r'BEGIN:VEVENT\s*\n(.*?)END:VEVENT', unfolded, re.S)
    if not blocks or len(blocks) != unfolded.count('BEGIN:VEVENT'):
        raise ValueError('Missing or incomplete calendar events')
    events, ids = [], set()
    for block in blocks:
        fields = {}
        for line in block.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                if key.split(';')[0] in ('UID', 'SUMMARY', 'DTSTART', 'STATUS', 'RRULE'):
                    fields[key] = value
        uid, title = fields.get('UID'), fields.get('SUMMARY')
        starts = [(k, v) for k, v in fields.items() if k.split(';')[0] == 'DTSTART']
        if not uid or not title or uid in ids or len(starts) != 1 or 'RRULE' in fields:
            raise ValueError('Incomplete, duplicate or unsupported calendar event')
        ids.add(uid)
        key, value = starts[0]
        if value.endswith('Z'):
            start = datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC)
        elif key in ('DTSTART;TZID=US-Eastern', 'DTSTART;TZID=America/New_York'):
            start = datetime.strptime(value, '%Y%m%dT%H%M%S').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(UTC)
        else:
            raise ValueError('Unsupported or missing event timezone')
        if fields.get('STATUS') == 'CANCELLED':
            continue
        events.append({'uid': uid, 'title': title.replace('\\,', ','), 'time': start})
    upcoming = sorted([e for e in events if now <= e['time'] <= now + timedelta(days=45)], key=lambda e: e['time'])
    for required in ('Consumer Price Index', 'Employment Situation'):
        if not any(e['title'] == required for e in upcoming):
            issues.append(f'Missing {required} in next 45 days')
    return {'source': BLS_URL, 'retrieved_at': retrieved_at, 'events': upcoming, 'issues': issues,
            'valid': not issues, 'coverage_complete': False, 'source_updated_at': None,
            'note': 'BLS schedule only; publisher update timestamp unavailable. Retrieval freshness does not prove schedule currency or global completeness.'}


def flows(payload, asset, retrieved_at, now=None):
    now = now or datetime.now(UTC)
    issues = retrieval_issues(retrieved_at, now, 3600)
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Invalid flow response schema')
    if payload.get('next_page_token') or payload.get('next_page_url'):
        issues.append('Truncated response: pagination remains')
    rows, seen = [], set()
    for item in payload.get('data', []):
        if not isinstance(item, dict):
            raise ValueError('Invalid flow record schema')
        if item.get('asset') != asset:
            raise ValueError('Unexpected asset')
        time = timestamp(item['time'])
        if time.hour or time.minute or time.second or time.microsecond or time in seen:
            raise ValueError('Duplicate or non-daily timestamp')
        seen.add(time)
        if time + timedelta(days=1) > now:
            issues.append('Future or incomplete daily interval')
        values, statuses, updates = {}, {}, {}
        for metric in METRICS:
            value = Decimal(item[metric])
            if not value.is_finite() or value < 0:
                raise ValueError('Invalid flow value')
            status = item.get(metric + '-status', 'unknown')
            statuses[metric] = status
            if status not in ('final', 'flash'):
                issues.append('Unverified metric status')
            updated = item.get(metric + '-status-time')
            updates[metric] = updated
            if not updated:
                issues.append('Missing metric update timestamp')
            elif not time + timedelta(days=1) <= timestamp(updated) <= now:
                issues.append('Invalid metric update timestamp')
            values[metric] = value
        rows.append({'time': time, 'inflow': values[METRICS[0]], 'outflow': values[METRICS[1]],
                     'net_inflow': values[METRICS[0]] - values[METRICS[1]],
                     'provisional': 'flash' in statuses.values(), 'statuses': statuses, 'updated_at': updates})
    rows.sort(key=lambda r: r['time'])
    expected = {now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i) for i in range(1, 8)}
    if not expected.issubset(seen):
        issues.append('Incomplete seven-day daily history')
    if not rows or (now - rows[-1]['time']).total_seconds() > 72 * 3600:
        issues.append('Stale or missing latest daily observation')
    return {'source': FLOW_URL, 'retrieved_at': retrieved_at, 'asset': asset, 'rows': rows,
            'issues': sorted(set(issues)), 'valid': not issues,
            'provisional': any(r['provisional'] for r in rows), 'confirmation_eligible': False}


def fetch_context():
    result = {'calendar': None, 'flows': {}, 'errors': {}}
    try:
        response = requests.get(BLS_URL, timeout=15)
        response.raise_for_status()
        result['calendar'] = calendar(response.text, datetime.now(UTC))
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        result['errors']['calendar'] = f'{type(exc).__name__}: {exc}'
    for asset in ('btc', 'eth'):
        try:
            start = (datetime.now(UTC) - timedelta(days=8)).date().isoformat()
            response = requests.get(FLOW_URL, params={'assets': asset, 'metrics': ','.join(METRICS),
                                    'frequency': '1d', 'start_time': start, 'page_size': 100}, timeout=15)
            response.raise_for_status()
            result['flows'][asset] = flows(response.json(), asset, datetime.now(UTC))
        except (requests.RequestException, ValueError, KeyError, TypeError, ArithmeticError) as exc:
            result['errors'][asset] = f'{type(exc).__name__}: {exc}'
    return result
