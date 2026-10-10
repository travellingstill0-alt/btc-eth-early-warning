import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from streamlit.testing.v1 import AppTest

class UITests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        st.cache_data.clear()

    def test_unavailable_sources_render_and_block_signals(self):
        with patch('market.fetch', side_effect=lambda symbol, **kwargs: {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {'ticker': 'source unavailable'}}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 2)
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)

    def test_oi_windows_warmup_and_explicit_required_lookback_selection(self):
        from test_analysis import fixture
        now = datetime.now(timezone.utc)
        ms = int(now.timestamp() * 1000)
        def sample(symbol, **kwargs):
            d = fixture(); shift = ms - int(d['retrieved_at'].timestamp() * 1000)
            d.update(symbol=symbol, retrieved_at=now, errors={})
            for source in d['sources'].values():
                source['source_time_ms'] += shift
            for key in ('candles', 'scalp_candles'):
                for row in d[key]:
                    row[0] += shift; row[6] += shift
            d['ticker'].update(lastPrice=100, baseVolume=500, closeTime=ms)
            d['funding']['time'] = ms
            d['interest']['time'] = ms
            d['trades'] = [{'T': ms, 'q': 1, 'm': False}]
            d['interest_history'] = d['interest_history'][-241:]
            for row in d['interest_history']:
                row['timestamp'] += shift; row['received_at_ms'] += shift
            return d
        with patch('market.fetch', side_effect=sample):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.sidebar.selectbox[0].value, '24h')
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
            self.assertTrue(any('OI change 15m:' in m.value for m in app.markdown))
            self.assertTrue(any('Warming up' in m.value for m in app.markdown))
            app.sidebar.checkbox[0].check().run()
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
            app.sidebar.selectbox[0].set_value('4h').run()
            self.assertFalse(app.exception)
            self.assertEqual(sum(m.value == '**WAIT**' for m in app.markdown), 4)
            self.assertTrue(any('UNAVAILABLE' in info.value for info in app.info))

    def test_populated_dashboard_and_macro_gate(self):
        from test_analysis import fixture
        now = datetime.now(timezone.utc)
        def sample(symbol, **kwargs):
            data = fixture()
            shift = int(now.timestamp()*1000) - int(data['retrieved_at'].timestamp()*1000)
            data.update(symbol=symbol, retrieved_at=now, errors={})
            for source in data['sources'].values():
                source['source_time_ms'] += shift
            for key in ('candles', 'scalp_candles'):
                for row in data[key]:
                    row[0] += shift; row[6] += shift
            data['ticker'].update(lastPrice='100', baseVolume='10000', closeTime=int(now.timestamp()*1000))
            data['funding']['time'] = int(now.timestamp()*1000)
            data['interest'].update(openInterest='123', time=int(now.timestamp()*1000))
            for row in data['interest_history']:
                row['timestamp'] += shift
                row['received_at_ms'] += shift
            data['interest_history'][-1]['sumOpenInterest'] = 123
            data['trades'] = [{'T': int(now.timestamp()*1000), 'q': '5', 'm': False}]
            return data
        with patch('market.fetch', side_effect=sample):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 0)
            self.assertEqual(len(app.metric), 6)
            app.sidebar.checkbox[0].check().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(sum(m.value == '**WAIT**' for m in app.markdown), 4)

    def test_fallback_units_timestamps_and_stale_warning(self):
        from test_analysis import fixture
        now = datetime.now(timezone.utc)
        ms = int(now.timestamp() * 1000)
        def sample(symbol, **kwargs):
            data = fixture()
            shift = ms - int(data['retrieved_at'].timestamp() * 1000)
            data.update(symbol=symbol, retrieved_at=now, errors={}, warnings=['interest: using Deribit fallback'])
            for key in ('candles', 'scalp_candles'):
                for row in data[key]:
                    row[0] += shift; row[6] += shift
            for source in data['sources'].values():
                source['source_time_ms'] = ms
            data['ticker'].update(lastPrice=100, baseVolume=500, closeTime=ms, priceChangePercent=None)
            data['interest'].update(openInterest=12300, unit='USD', time=ms)
            data['sources']['interest'].update(provider='Deribit', instrument=symbol[:3] + '-PERPETUAL')
            data['funding'].update(time=ms - 400000, period_hours=8)
            data['sources']['funding']['source_time_ms'] = ms - 400000
            data['trades'] = [{'T': ms, 'q': 1, 'm': False}]
            del data['interest_history']
            return data
        with patch('market.fetch', side_effect=sample):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any('STALE' in c.value for c in app.caption))
            self.assertTrue(any('Deribit' in c.value for c in app.caption))
            self.assertEqual(sum(m.label == 'Perpetual OI (USD)' for m in app.metric), 2)
            self.assertTrue(any('24h price change: Unavailable' in w.value for w in app.warning))
            app.sidebar.checkbox[0].check().run()
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
