import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ENTRY=str(Path(__file__).resolve().parents[1]/'mobile/cloud_app.py')
class CloudEntryTests(unittest.TestCase):
    def test_no_secret_blocks_feeds(self):
        with patch('market.fetch') as feeds:
            app=AppTest.from_file(ENTRY).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Dashboard locked' in x.value for x in app.error))
            feeds.assert_not_called()
    def test_wrong_password_blocks_feeds_and_secret_not_rendered(self):
        with patch('market.fetch') as feeds:
            app=AppTest.from_file(ENTRY)
            app.secrets['dashboard_access_password']='long-test-passphrase-not-for-production'
            app.run();app.text_input[0].set_value('wrong');app.button[0].click().run()
            self.assertFalse(app.exception);feeds.assert_not_called()
            self.assertTrue(any('Access denied' in x.value for x in app.error))
            self.assertFalse(any('long-test-passphrase' in x.value for x in app.markdown))
    def test_authenticated_view_stays_no_trade(self):
        from datetime import datetime,timezone
        import streamlit as st
        st.cache_data.clear()
        with patch('market.fetch',side_effect=lambda symbol,**kw:dict(symbol=symbol,retrieved_at=datetime.now(timezone.utc),errors={})),patch('macro_calendar.fetch_calendar',return_value=dict(fetched_at=datetime.now(timezone.utc).isoformat(),sources={},events=[])):
            app=AppTest.from_file(ENTRY);app.secrets['dashboard_access_password']='long-test-passphrase-not-for-production'
            app.run();app.text_input[0].set_value('long-test-passphrase-not-for-production');app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any('NO TRADE LOCKED' in x.value for x in app.error))
            app.button[0].click().run()
            self.assertFalse(app.exception);self.assertEqual(len(app.text_input),1)

    def test_disabled_safety_hold_blocks_authenticated_feeds(self):
        with patch('analysis.NO_TRADE_HOLD',False), patch('market.fetch') as feeds:
            app=AppTest.from_file(ENTRY);app.secrets['dashboard_access_password']='long-test-passphrase-not-for-production'
            app.run();app.text_input[0].set_value('long-test-passphrase-not-for-production');app.button[0].click().run()
            self.assertFalse(app.exception);feeds.assert_not_called()
            self.assertTrue(any('Safety lock disabled' in x.value for x in app.error))
