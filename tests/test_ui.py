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
        with patch('market.fetch', side_effect=lambda symbol: {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {'ticker': 'source unavailable'}}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 2)
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
            self.assertTrue(any('UNAVAILABLE' in info.value for info in app.info))

    def test_populated_dashboard_and_macro_gate(self):
        from test_analysis import fixture
        now = datetime.now(timezone.utc)
        def sample(symbol):
            data = fixture()
            shift = int(now.timestamp()*1000) - int(data['retrieved_at'].timestamp()*1000)
            data.update(symbol=symbol, retrieved_at=now, errors={})
            for key in ('candles', 'scalp_candles'):
                for row in data[key]:
                    row[0] += shift; row[6] += shift
            data['ticker'].update(lastPrice='100', quoteVolume='1000000', closeTime=int(now.timestamp()*1000))
            data['funding']['time'] = int(now.timestamp()*1000)
            data['interest'].update(openInterest='123', time=int(now.timestamp()*1000))
            for row in data['interest_history']:
                row['timestamp'] += shift
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
