"""Verified OI series and durable observations; no interpolation or contract mixing."""
import math
import os
from contextlib import closing
from pathlib import Path
import sqlite3

WINDOWS = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '24h': 86400}
BASELINE_TOLERANCE_MS = 90_000
MAX_GAP_MS = 180_000
SERIES_UNITS = {
    ('Kraken Futures', 'PF_XBTUSD'): 'BTC',
    ('Kraken Futures', 'PF_ETHUSD'): 'ETH',
    ('Deribit', 'BTC-PERPETUAL'): 'USD',
    ('Deribit', 'ETH-PERPETUAL'): 'USD',
}


def identity(source, unit):
    key = source['provider'], source['instrument'], unit
    if SERIES_UNITS.get(key[:2]) != unit:
        raise ValueError('Unverified provider, contract or OI units')
    return key


def point(key, time_ms, value, received_ms, kind):
    if float(time_ms) != int(time_ms) or float(received_ms) != int(received_ms):
        raise ValueError('Fractional OI timestamp')
    time_ms, received_ms, value = int(time_ms), int(received_ms), float(value)
    if not math.isfinite(value) or value < 0 or time_ms <= 0 or received_ms <= 0:
        raise ValueError('Invalid OI observation')
    if time_ms > received_ms + 5000:
        raise ValueError('Future OI observation')
    if kind not in ('server snapshot', 'completed OI bar'):
        raise ValueError('Unverified OI timestamp type')
    identity(dict(provider=key[0], instrument=key[1]), key[2])
    return dict(provider=key[0], instrument=key[1], unit=key[2], timestamp=time_ms,
                sumOpenInterest=value, received_at_ms=received_ms,
                timestamp_kind=kind, verified=True)


def current_point(data, now_ms, max_age=180):
    interest, source = data['interest'], data['sources']['interest']
    key = identity(source, interest['unit'])
    time_ms = source['source_time_ms']
    if time_ms != interest['time'] or not -5000 <= now_ms - time_ms <= max_age * 1000:
        raise ValueError('Missing, stale or inconsistent current OI timestamp')
    if source['timestamp_kind'] != 'server snapshot':
        raise ValueError('Unverified current OI source')
    return point(key, time_ms, interest['openInterest'], now_ms, source['timestamp_kind'])


def parse_kraken_history(body, current, received_ms):
    """Analytics timestamps are interval starts; use only completed minute closes."""
    if not isinstance(body, dict):
        raise ValueError('Invalid OI history response')
    if body.get('errors'):
        raise ValueError(str(body['errors']))
    rows = body['result']
    times, values = rows['timestamp'], rows['data']
    if not times or len(times) != len(values):
        raise ValueError('Invalid OI history arrays')
    key = current['provider'], current['instrument'], current['unit']
    if key[0] != 'Kraken Futures':
        raise ValueError('Kraken history cannot describe a different provider')
    points, previous = [], 0
    for ts, row in zip(times, values):
        if float(ts) != int(ts):
            raise ValueError('Fractional OI bar timestamp')
        start = int(ts) * 1000
        if start <= previous or start % 60_000 or len(row) != 4:
            raise ValueError('Invalid, duplicate or unordered OI bars')
        previous = start
        o, h, low, close = [float(v) for v in row]
        if any(not math.isfinite(v) or v < 0 for v in (o, h, low, close)) or h < max(o, low, close) or low > min(o, h, close):
            raise ValueError('Invalid OI OHLC values')
        if start > received_ms + 5000:
            raise ValueError('Future OI history bar')
        end = start + 60_000 - 1
        # Include no active bar, nor a bar closing after the selected live snapshot.
        if end < current['timestamp'] and end <= received_ms:
            points.append(point(key, end, close, received_ms, 'completed OI bar'))
    return points


class SnapshotStore:
    def __init__(self, path=None):
        self.path = Path(path if path is not None else os.environ.get(
            'OI_HISTORY_DB_PATH', str(Path(__file__).resolve().parent / 'data' / 'oi_snapshots.sqlite3')))

    def record_and_read(self, current, max_age=180):
        """One transaction per refresh; duplicate source times never advance history."""
        if current.get('verified') is not True or current['timestamp_kind'] != 'server snapshot':
            raise ValueError('Unverified snapshot cannot be persisted')
        key = current['provider'], current['instrument'], current['unit']
        current = point(key, current['timestamp'], current['sumOpenInterest'],
                        current['received_at_ms'], current['timestamp_kind'])
        if not -5000 <= current['received_at_ms'] - current['timestamp'] <= max_age * 1000:
            raise ValueError('Stale snapshot cannot be persisted')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS oi_snapshots (
                provider TEXT NOT NULL, instrument TEXT NOT NULL, unit TEXT NOT NULL,
                timestamp INTEGER NOT NULL CHECK(timestamp > 0), value REAL NOT NULL CHECK(value >= 0),
                received_at_ms INTEGER NOT NULL, timestamp_kind TEXT NOT NULL CHECK(timestamp_kind = 'server snapshot'),
                PRIMARY KEY(provider, instrument, unit, timestamp))''')
            old = db.execute('SELECT value FROM oi_snapshots WHERE provider=? AND instrument=? AND unit=? AND timestamp=?',
                             (*key, current['timestamp'])).fetchone()
            if old and old[0] != current['sumOpenInterest']:
                raise ValueError('Conflicting OI values for the same source timestamp')
            db.execute('INSERT OR IGNORE INTO oi_snapshots VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (*key, current['timestamp'], current['sumOpenInterest'], current['received_at_ms'], current['timestamp_kind']))
            saved = db.execute('SELECT value FROM oi_snapshots WHERE provider=? AND instrument=? AND unit=? AND timestamp=?',
                               (*key, current['timestamp'])).fetchone()
            if saved[0] != current['sumOpenInterest']:
                raise ValueError('Conflicting concurrent OI observation')
            rows = db.execute('''SELECT timestamp, value, received_at_ms, timestamp_kind FROM oi_snapshots
                WHERE provider=? AND instrument=? AND unit=? AND timestamp BETWEEN ? AND ? ORDER BY timestamp''',
                (*key, current['timestamp'] - WINDOWS['24h'] * 1000 - BASELINE_TOLERANCE_MS,
                 current['timestamp'])).fetchall()
        return [point(key, *row) for row in rows]


def calculate_changes(data, now_ms, max_age=180):
    """Revalidate raw observations on every assessment, including cached data."""
    def unavailable(reason):
        return {window: dict(change_pct=None, reason=reason) for window in WINDOWS}
    try:
        current = current_point(data, now_ms, max_age)
        key = current['provider'], current['instrument'], current['unit']
        source = data['sources']['interest_history']
        if (identity(source, source['unit']) != key or source.get('verified') is not True
                or source.get('source_time_ms') != current['timestamp']):
            raise ValueError('Unverified or incompatible OI history source')
        raw = data['interest_history']
        if not raw:
            return unavailable('Warming up: no stored observations')
        rows, previous = [], 0
        for row in raw:
            if (row['provider'], row['instrument'], row['unit']) != key or row.get('verified') is not True:
                raise ValueError('Unverified or incompatible OI history observation')
            checked = point(key, row['timestamp'], row['sumOpenInterest'], row['received_at_ms'], row['timestamp_kind'])
            if checked['received_at_ms'] > now_ms + 5000 or checked['timestamp'] <= previous:
                raise ValueError('Future receipt, duplicate or unordered OI history')
            if checked['timestamp_kind'] == 'server snapshot' and checked['received_at_ms'] - checked['timestamp'] > max_age * 1000:
                raise ValueError('Snapshot was stale when collected')
            previous = checked['timestamp']
            rows.append(checked)
        if rows[-1]['timestamp'] != current['timestamp'] or rows[-1]['sumOpenInterest'] != current['sumOpenInterest']:
            raise ValueError('History does not end at the selected current OI observation')
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        return unavailable(str(exc))
    output = {}
    for window, seconds in WINDOWS.items():
        target = current['timestamp'] - seconds * 1000
        candidates = [i for i, r in enumerate(rows) if r['timestamp'] <= target]
        reason = None
        if not candidates:
            reason = f'Warming up: insufficient {window} observations for this provider/contract'
        else:
            index = candidates[-1]
            baseline = rows[index]
            segment = rows[index:]
            if target - baseline['timestamp'] > BASELINE_TOLERANCE_MS:
                reason = 'No baseline within 90 seconds before the target; not interpolated'
            elif baseline['sumOpenInterest'] <= 0:
                reason = 'Zero OI baseline; percentage change undefined'
            elif any(b['timestamp'] - a['timestamp'] > MAX_GAP_MS for a, b in zip(segment, segment[1:])):
                reason = 'Gap over 180 seconds in OI observations'
            if reason is None:
                change = (current['sumOpenInterest'] / baseline['sumOpenInterest'] - 1) * 100
                if not math.isfinite(change):
                    output[window] = dict(change_pct=None, reason='Invalid percentage change')
                    continue
                output[window] = dict(change_pct=change,
                                      baseline_time_ms=baseline['timestamp'], end_time_ms=current['timestamp'],
                                      elapsed_seconds=(current['timestamp'] - baseline['timestamp']) / 1000,
                                      observation_count=len(segment), provider=key[0], instrument=key[1], unit=key[2],
                                      baseline_value=baseline['sumOpenInterest'], end_value=current['sumOpenInterest'],
                                      reason=None)
                continue
        output[window] = dict(change_pct=None, reason=reason)
    return output
