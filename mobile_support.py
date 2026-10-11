"""Track A display-only helpers. No trading or notification transport."""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTIFICATION_KINDS = ('BTC LONG', 'BTC SHORT', 'ETH LONG', 'ETH SHORT', 'HIGH risk', 'EXTREME risk', 'High-impact macro')

def demo_notification(kind):
    if kind not in NOTIFICATION_KINDS:
        raise ValueError('Unknown demo category')
    return {'title': 'TEST ONLY — ' + kind, 'body': 'Synthetic interface test. NO TRADE. No trading opportunity asserted.', 'demo': True, 'delivery': 'local preview only', 'live_enabled': False}

def fresh_value(data, key, field, now_ms):
    """Never show stale, timestamp-less, nonfinite values as live."""
    try:
        item = data[key]; source = data['sources'][key]
        for stamp in (source['source_time_ms'], item[{'ticker': 'closeTime', 'interest': 'time', 'funding': 'time'}[key]]):
            if not -5000 <= now_ms - float(stamp) <= 180000:
                return None
        value = float(item[field])
        return value if math.isfinite(value) else None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

def research_rows(asset, direction, horizon):
    path = ROOT / 'research_artifacts/confirmation-v1/results/metrics.csv'
    if not path.exists():
        return []
    with path.open(newline='') as stream:
        return [r for r in csv.DictReader(stream) if r['asset'] == asset and r['direction'] == direction and r['horizon'] == horizon and r['family'] == 'main' and r['partition'] == 'chronological_test' and r['scenario'] == 'published_base']
