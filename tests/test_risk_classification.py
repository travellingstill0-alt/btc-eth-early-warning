import unittest
from datetime import timedelta, datetime, timezone
from pathlib import Path
from unittest.mock import patch
from analysis import assess, plan, Rules
from test_analysis import fixture, NOW, MS

CLEAR = {'clear': True, 'missing': [], 'high_risk': []}

class RiskClassificationTests(unittest.TestCase):
    def test_missing_inputs_for_both_assets_never_classify_overall_low(self):
        for symbol in ('BTCUSD', 'ETHUSD'):
            for key in ('ticker', 'funding', 'interest', 'interest_history', 'candles', 'scalp_candles', 'trades'):
                with self.subTest(symbol=symbol, missing=key):
                    d = fixture(); d['symbol'] = symbol; del d[key]
                    r = assess(d, Rules(), NOW)
                    self.assertEqual(r['level'], 'UNKNOWN')
                    self.assertEqual(r['overall_level'], 'UNKNOWN')
                    self.assertIn(key, r['overall_missing'])
                    self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_macro_context_missing_and_stale_are_explicit(self):
        for macro in ({'clear': False, 'missing': ['ECB unavailable', 'ONS stale'], 'high_risk': []}, CLEAR):
            with patch('analysis.evaluate_calendar', return_value=macro):
                r = assess(fixture(), Rules(), NOW)
            self.assertEqual(r['overall_level'], 'UNKNOWN')
            self.assertIn('exchange flows', r['overall_missing'])
            self.assertIn('liquidation data', r['overall_missing'])
            if macro['missing']:
                self.assertIn('Macro: ONS stale', r['overall_missing'])

    def test_all_data_absent_observed_and_overall_unknown(self):
        d = {'retrieved_at': NOW}
        r = assess(d, Rules(), NOW)
        self.assertEqual(r['observed_level'], 'UNKNOWN')
        self.assertEqual(r['overall_level'], 'UNKNOWN')
        self.assertEqual(r['observed_indicator_count'], 0)
        self.assertIsNone(r['observed_score'])

    def test_stale_data_does_not_contribute_a_score(self):
        for mutation in ('retrieval', 'funding', 'ticker', 'future'):
            d = fixture()
            d['funding']['lastFundingRate'] = '0.001'
            d['ticker']['priceChangePercent'] = '8'
            if mutation == 'retrieval': d['retrieved_at'] -= timedelta(minutes=10)
            if mutation in ('funding', 'ticker'): d['sources'][mutation]['source_time_ms'] -= 600000
            if mutation == 'future': d['funding']['time'] += 600000
            r = assess(d, Rules(), NOW)
            self.assertEqual(r['overall_level'], 'UNKNOWN')
            self.assertLess(r['score'], 4)
            self.assertEqual(plan(d, r, 'DAY TRADE', True, NOW)['status'], 'NO TRADE')
            if mutation == 'retrieval': self.assertEqual(r['observed_level'], 'UNKNOWN')

    def test_missing_or_naive_retrieval_timestamp_is_unknown(self):
        for value in (None, NOW.replace(tzinfo=None), 'invalid'):
            d = fixture(); d['retrieved_at'] = value
            r = assess(d, Rules(), NOW)
            self.assertEqual(r['observed_level'], 'UNKNOWN')
            self.assertEqual(r['overall_level'], 'UNKNOWN')
            self.assertIn('unknown retrieval timestamp', r['overall_missing'])
            self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_conflicting_signs_do_not_cancel_absolute_risk(self):
        d = fixture()
        d['ticker']['priceChangePercent'] = '-8'
        d['funding']['lastFundingRate'] = '0.001'
        r = assess(d, Rules(), NOW)
        self.assertEqual(r['observed_level'], 'HIGH')
        self.assertEqual(r['score'], 4)
        self.assertEqual(r['overall_level'], 'UNKNOWN')
        self.assertEqual(plan(d, r, 'SCALP', True, NOW)['reason_code'], 'HIGH_RISK_AND_MISSING_DATA')

    def test_verified_indicator_thresholds_preserved(self):
        with patch('analysis.REQUIRED_CONTEXT', ()), patch('analysis.evaluate_calendar', return_value=CLEAR):
            for move, funding, oi, expected in ((1, '.0001', 101, 'LOW'), (8, '.0001', 101, 'MODERATE'), (8, '.001', 101, 'HIGH'), (8, '.001', 120, 'EXTREME')):
                d = fixture()
                d['ticker']['priceChangePercent'] = str(move)
                d['funding']['lastFundingRate'] = funding
                d['interest_history'][-1]['sumOpenInterest'] = oi
                d['interest']['openInterest'] = oi
                r = assess(d, Rules(), NOW)
                self.assertEqual(r['observed_level'], expected)
                self.assertEqual(r['overall_level'], expected)
                self.assertEqual(r['overall_missing'], [])
                self.assertEqual(plan(d, r, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_known_macro_high_risk_does_not_appear_low(self):
        macro = {'clear': False, 'missing': [], 'high_risk': ['CPI event window']}
        with patch('analysis.REQUIRED_CONTEXT', ()), patch('analysis.evaluate_calendar', return_value=macro):
            r = assess(fixture(), Rules(), NOW)
            self.assertEqual(r['observed_level'], 'LOW')
            self.assertEqual(r['overall_level'], 'HIGH')
            self.assertEqual(plan(fixture(), r, 'SCALP', True, NOW)['status'], 'NO TRADE')

    def test_invalid_numbers_are_missing_not_zero(self):
        for key, field in (('ticker', 'priceChangePercent'), ('funding', 'lastFundingRate')):
            for value in ('NaN', 'Infinity', 'invalid', None):
                d = fixture(); d[key][field] = value
                r = assess(d, Rules(), NOW)
                self.assertEqual(r['overall_level'], 'UNKNOWN')
                self.assertTrue(any('invalid' in x or '24h price change' in x for x in r['overall_missing']))

    def test_ui_separates_observed_and_overall_for_both_assets(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        st.cache_data.clear()
        def unavailable(symbol, **kwargs):
            return {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {}}
        with patch('market.fetch', side_effect=unavailable), patch('context.fetch_context', return_value={'calendar': None, 'flows': {}, 'errors': {}}), patch('macro_calendar.fetch_calendar', return_value={'fetched_at': datetime.now(timezone.utc).isoformat(), 'sources': {}, 'events': []}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertFalse(app.exception)
            texts = [m.value for m in app.markdown]
            self.assertEqual(texts.count('Observed market risk: **UNKNOWN**'), 2)
            self.assertEqual(texts.count('Overall trading risk: **UNKNOWN — INCOMPLETE DATA**'), 2)
            self.assertEqual(texts.count('**NO TRADE**'), 4)
            self.assertTrue(all('Macro:' in e.value and 'exchange flows' in e.value for e in app.error))
            app.sidebar.checkbox[0].check().run()
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
