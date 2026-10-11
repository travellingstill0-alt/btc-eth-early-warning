import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from observation_store import preserve

class StoreTests(unittest.TestCase):
    def test_transactional_dedup_and_raw_payload(self):
        payload=dict(provider='test',instrument='test',kind='cvd',start_ms=1,end_ms=2,received_at_ms=3)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'windows.sqlite3'
            with patch('observation_store.parse',return_value={'value':1}):
                self.assertEqual(preserve(payload,3,path=path),preserve(payload,3,path=path))
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM windows').fetchone()[0],1)
                self.assertIn('"received_at_ms":3',db.execute('SELECT payload FROM windows').fetchone()[0])
    def test_invalid_payload_never_creates_archive(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'windows.sqlite3'
            with self.assertRaises((ValueError,KeyError)):
                preserve({},3,path=path)
            self.assertFalse(path.exists())
