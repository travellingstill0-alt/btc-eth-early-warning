"""Immutable verified context windows; SQLite transactions, no synthetic backfill."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from context_data import parse


def preserve(payload, now_ms, max_age=180, path=None):
    parse(payload, now_ms, max_age)
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    path = Path(path or os.environ.get('CONTEXT_HISTORY_DB_PATH', 'data/context_windows.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS windows (digest TEXT PRIMARY KEY, provider TEXT, instrument TEXT, kind TEXT, start_ms INTEGER, end_ms INTEGER, received_ms INTEGER, payload TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO windows VALUES (?,?,?,?,?,?,?,?)',
                   (digest, payload['provider'], payload['instrument'], payload['kind'], payload['start_ms'], payload['end_ms'], payload['received_at_ms'], encoded))
    return digest
