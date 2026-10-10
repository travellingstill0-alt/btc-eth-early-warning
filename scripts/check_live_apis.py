"""Read-only, repeatable live API diagnostics. Run from repository root."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from market import fetch, ENDPOINTS
from analysis import assess, Rules

report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'symbols': {}}
for symbol in ('BTCUSDT', 'ETHUSDT'):
    snapshot = fetch(symbol)
    risk = assess(snapshot, Rules())
    report['symbols'][symbol] = {
        'retrieved_at_utc': snapshot['retrieved_at'].isoformat(),
        'connections': {key: {'url': base + path, 'status': 'failed' if key in snapshot['errors'] else 'response validated',
                              'error': snapshot['errors'].get(key), 'received_at_utc': snapshot['source_retrieved_at'][key]}
                        for key, (base, path, _) in ENDPOINTS.items()},
        'missing_or_stale': risk['missing'],
    }
print(json.dumps(report, indent=2))
sys.exit(1 if any(r['missing_or_stale'] for r in report['symbols'].values()) else 0)
