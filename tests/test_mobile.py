import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from streamlit.testing.v1 import AppTest
from mobile_support import fresh_value, demo_notification, NOTIFICATION_KINDS, research_rows

class MobileTests(unittest.TestCase):
    def test_stale_missing_future_nonfinite_values_are_unavailable(self):
        d={'ticker':{'lastPrice':100,'closeTime':1000000},'sources':{'ticker':{'source_time_ms':1000000}}}
        self.assertEqual(fresh_value(d,'ticker','lastPrice',1000000),100)
        for now in (1180001,994999): self.assertIsNone(fresh_value(d,'ticker','lastPrice',now))
        d['ticker']['lastPrice']='nan'
        self.assertIsNone(fresh_value(d,'ticker','lastPrice',1000000))
        self.assertIsNone(fresh_value({},'ticker','lastPrice',1000000))
    def test_every_notification_is_disabled_demo(self):
        for kind in NOTIFICATION_KINDS:
            p=demo_notification(kind)
            self.assertFalse(p['live_enabled']); self.assertTrue(p['demo']); self.assertIn('TEST ONLY',p['title'])
    def test_all_eight_research_selections(self):
        for asset in ('BTC','ETH'):
            for direction in ('LONG','SHORT'):
                for horizon in ('SCALP','DAY TRADE'):
                    self.assertTrue(research_rows(asset,direction,horizon))
    def test_mobile_outage_views_and_demo(self):
        import streamlit as st
        st.cache_data.clear()
        cal={'fetched_at':datetime.now(timezone.utc).isoformat(),'events':[],'sources':{}}
        with patch('market.fetch',side_effect=lambda symbol,**kw:dict(symbol=symbol,retrieved_at=datetime.now(timezone.utc),errors={})), patch('macro_calendar.fetch_calendar',return_value=cal):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'mobile_app.py')).run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any('INCOMPLETE' in e.value for e in app.error))
            self.assertTrue(all(m.value=='UNAVAILABLE' for m in app.metric))
            for page in ('Economic calendar','Research','Notification tests'):
                app.selectbox[0].set_value(page).run(timeout=20)
                self.assertFalse(app.exception)
            app.button[-1].click().run()
            self.assertTrue(any('TEST ONLY' in s.value for s in app.success))
