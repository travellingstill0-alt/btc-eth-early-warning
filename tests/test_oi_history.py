from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from oi_history import SnapshotStore, calculate_changes, point, parse_kraken_history
from test_analysis import fixture, MS, NOW
from analysis import Rules, assess, plan, REQUIRED_CONTEXT

KEY = ('Kraken Futures', 'PF_XBTUSD', 'BTC')


class OIHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'nested' / 'oi.sqlite3'

    def test_persistence_survives_reopening_and_duplicate_observations(self):
        p = point(KEY, MS, 100, MS, 'server snapshot')
        self.assertEqual(len(SnapshotStore(self.path).record_and_read(p)), 1)
        p['received_at_ms'] += 1000
        self.assertEqual(len(SnapshotStore(self.path).record_and_read(p)), 1)
        p2 = point(KEY, MS+60000, 110, MS+60000, 'server snapshot')
        rows = SnapshotStore(self.path).record_and_read(p2)
        self.assertEqual([r['sumOpenInterest'] for r in rows], [100, 110])
        self.assertEqual(rows[0]['received_at_ms'], MS)
        p2['sumOpenInterest'] = 111
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            SnapshotStore(self.path).record_and_read(p2)

    def test_all_contracts_and_units_are_isolated(self):
        store = SnapshotStore(self.path)
        for key, value in [(KEY, 1), (('Kraken Futures', 'PF_ETHUSD', 'ETH'), 2),
                           (('Deribit', 'BTC-PERPETUAL', 'USD'), 3), (('Deribit', 'ETH-PERPETUAL', 'USD'), 4)]:
            store.record_and_read(point(key, MS, value, MS, 'server snapshot'))
        for key, value in [(KEY, 1), (('Deribit', 'BTC-PERPETUAL', 'USD'), 3)]:
            rows = store.record_and_read(point(key, MS+60000, value, MS+60000, 'server snapshot'))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all((r['provider'], r['instrument'], r['unit']) == key for r in rows))
        with self.assertRaises(ValueError):
            point(('Deribit', 'BTC-PERPETUAL', 'BTC'), MS, 100, MS, 'server snapshot')

    def test_warmup_per_window_and_changes_from_real_observation_rows(self):
        d = fixture()
        for minutes, ready in [(14, ()), (15, ('15m',)), (60, ('15m', '1h')),
                               (240, ('15m', '1h', '4h')), (1440, ('15m', '1h', '4h', '24h'))]:
            with self.subTest(minutes=minutes):
                d['interest_history'] = fixture()['interest_history'][-minutes-1:]
                result = calculate_changes(d, MS)
                self.assertEqual(tuple(w for w, r in result.items() if r['change_pct'] is not None), ready)
                for w in ready:
                    self.assertAlmostEqual(result[w]['change_pct'], 1)
                risk = assess(d, Rules(), NOW)
                self.assertEqual(bool(set(risk['missing']) - set(REQUIRED_CONTEXT)), minutes < 1440)
        d['interest_history'] = d['interest_history'][-241:]
        self.assertEqual(assess(d, Rules(oi_window='4h'), NOW)['missing'], sorted(REQUIRED_CONTEXT))

    def test_gaps_invalid_baselines_and_incompatible_or_unverified_data(self):
        cases = []
        d = fixture(); del d['interest_history'][-20:-15]; cases.append(d)
        d = fixture(); d['interest_history'][0]['sumOpenInterest'] = 0; cases.append(d)
        d = fixture(); d['interest_history'][0]['verified'] = False; cases.append(d)
        d = fixture(); d['interest_history'][0]['unit'] = 'USD'; cases.append(d)
        d = fixture(); d['sources']['interest_history']['instrument'] = 'PF_ETHUSD'; cases.append(d)
        d = fixture(); d['interest_history'][0]['sumOpenInterest'] = float('nan'); cases.append(d)
        d = fixture(); d['interest_history'][0]['received_at_ms'] = MS+60000; cases.append(d)
        d = fixture(); d['interest_history'][0]['received_at_ms'] += 600000; cases.append(d)
        d = fixture(); d['interest_history'].append(deepcopy(d['interest_history'][-1])); cases.append(d)
        d = fixture(); d['interest']['openInterest'] = 103; cases.append(d)
        for i, d in enumerate(cases):
            with self.subTest(case=i):
                self.assertIsNone(calculate_changes(d, MS)['24h']['change_pct'])
                d['scalp_candles'][-1][4:6] = ['115', '20']
                self.assertEqual(plan(d, assess(d, Rules(), NOW), 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_stale_current_observation_cannot_use_fresh_retrieval_to_unlock(self):
        d = fixture()
        self.assertIsNone(calculate_changes(d, MS+181000)['15m']['change_pct'])
        d['sources']['interest']['source_time_ms'] -= 1
        self.assertIsNone(calculate_changes(d, MS)['4h']['change_pct'])

    def test_baseline_is_before_target_and_within_tolerance_no_interpolation(self):
        d = fixture()
        # A minute-offset sample is valid; shifting the nearest baseline >90 seconds is not.
        d['interest_history'] = [r for r in d['interest_history'] if r['timestamp'] != MS-900000]
        r = calculate_changes(d, MS)['15m']
        self.assertEqual(r['baseline_time_ms'], MS-960000)
        self.assertEqual(r['elapsed_seconds'], 960)
        d['interest_history'] = [r for r in d['interest_history'] if r['timestamp'] != MS-960000]
        self.assertIsNone(calculate_changes(d, MS)['15m']['change_pct'])

    def test_persisted_series_accumulates_a_window_after_restart(self):
        store = SnapshotStore(self.path)
        for i in range(16):
            ts = MS - (15-i)*60000
            rows = store.record_and_read(point(KEY, ts, 100+i, ts, 'server snapshot'))
        d = fixture(); d['interest']['openInterest'] = 115
        d['interest_history'] = SnapshotStore(self.path).record_and_read(point(KEY, MS, 115, MS, 'server snapshot'))
        self.assertAlmostEqual(calculate_changes(d, MS)['15m']['change_pct'], 15)
        self.assertIsNone(calculate_changes(d, MS)['1h']['change_pct'])

    def test_unverified_and_stale_observations_never_enter_store(self):
        for mutation in ({'verified': False}, {'received_at_ms': MS+181000},
                         {'timestamp_kind': 'unknown'}, {'sumOpenInterest': -1}):
            p = point(KEY, MS, 100, MS, 'server snapshot'); p.update(mutation)
            with self.assertRaises(ValueError):
                SnapshotStore(self.path).record_and_read(p)
        self.assertFalse(self.path.exists())

    def test_corrupt_database_is_not_silently_reset(self):
        self.path.parent.mkdir()
        self.path.write_text('not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            SnapshotStore(self.path).record_and_read(point(KEY, MS, 100, MS, 'server snapshot'))
        self.assertEqual(self.path.read_text(), 'not a database')

    def test_incomplete_analytics_bar_is_excluded_and_ohlc_close_is_used(self):
        current = point(KEY, MS+30000, 102, MS+30000, 'server snapshot')
        body = {'result': {'timestamp': [MS//1000 - 60, MS//1000],
                           'data': [[99, 101, 98, 100], [100, 10000, 100, 9999]]}, 'errors': []}
        rows = parse_kraken_history(body, current, MS+30000)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['sumOpenInterest'], 100)
        self.assertEqual(rows[0]['timestamp'], MS-1)
        body['result']['data'][0][1] = 1
        with self.assertRaises(ValueError):
            parse_kraken_history(body, current, MS+30000)

    def test_concurrent_sessions_do_not_lose_or_duplicate_observations(self):
        store = SnapshotStore(self.path)
        initial = point(KEY, MS, 100, MS, 'server snapshot')
        store.record_and_read(initial)
        def save(i):
            ts = MS + i*60000
            return SnapshotStore(self.path).record_and_read(point(KEY, ts, 100+i, ts, 'server snapshot'))
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(save, [1, 2, 3, 4, 1, 2, 3, 4]))
        self.assertEqual(len(save(4)), 5)

    def test_cached_change_summary_never_overrides_unverified_raw_history(self):
        d = fixture(); d['oi_changes'] = {'24h': {'change_pct': 1}}
        d['interest_history'][0]['verified'] = False
        self.assertIsNone(assess(d, Rules(), NOW)['oi_change'])

    def test_percentage_overflow_and_fractional_timestamps_are_unavailable(self):
        d = fixture(); d['interest_history'][0]['sumOpenInterest'] = 1e-320
        self.assertIsNone(calculate_changes(d, MS)['24h']['change_pct'])
        with self.assertRaises(ValueError):
            point(KEY, MS+0.5, 100, MS, 'server snapshot')
