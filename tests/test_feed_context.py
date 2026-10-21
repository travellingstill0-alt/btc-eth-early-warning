import copy
import os
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from context import calendar, flows, fetch_context
from analysis import Rules, assess, plan
from test_analysis import fixture

NOW = datetime(2026, 10, 10, 17, tzinfo=timezone.utc)
ICS = '''BEGIN:VCALENDAR
BEGIN:VEVENT
UID:cpi
DTSTART;TZID=US-Eastern:20261014T083000
SUMMARY:Consumer Price Index
END:VEVENT
BEGIN:VEVENT
UID:jobs
DTSTART;TZID=US-Eastern:20261106T083000
SUMMARY:Employment Situation
END:VEVENT
END:VCALENDAR'''


def payload(asset='btc', status='flash'):
    rows = []
    for i in range(7, 0, -1):
        day = NOW.replace(hour=0) - timedelta(days=i)
        row = {'asset': asset, 'time': day.isoformat()}
        for metric in ('FlowInExNtv', 'FlowOutExNtv'):
            row[metric] = '123.45'
            row[metric + '-status'] = status
            row[metric + '-status-time'] = (day + timedelta(days=1, hours=2)).isoformat()
        rows.append(row)
    return {'data': rows}


class ContextTests(unittest.TestCase):
    def test_calendar_dst_and_partial_coverage(self):
        result = calendar(ICS, NOW, NOW)
        self.assertTrue(result['valid'])
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(result['events'][0]['time'].hour, 12)
        self.assertEqual(result['events'][1]['time'].hour, 13)

    def test_bls_global_adapter_accepts_verified_feed_timezone_and_zero_duration(self):
        from macro_calendar import parse_bls
        text = ICS.replace('END:VEVENT', 'DURATION:PT0M\nEND:VEVENT')
        text = text.replace('END:VCALENDAR', 'BEGIN:VEVENT\nUID:ppi\nDTSTART;TZID=US-Eastern:20261015T083000\nSUMMARY:Producer Price Index\nDURATION:PT0M\nEND:VEVENT\nEND:VCALENDAR')
        events = parse_bls(text)
        self.assertEqual({e['kind'] for e in events}, {'CPI', 'PPI', 'NFP'})
        with self.assertRaises(ValueError):
            parse_bls(text.replace('DURATION:PT0M', 'DURATION:PT1H'))

    def test_bad_calendar_fails_closed(self):
        for text in (ICS.replace('END:VCALENDAR', ''), ICS.replace('TZID=US-Eastern', 'TZID=Unknown'),
                     ICS.replace('UID:cpi', 'UID:jobs'), ICS.replace('SUMMARY:Consumer Price Index', 'SUMMARY:')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                calendar(text, NOW, NOW)

    def test_calendar_stale_future_and_missing_coverage(self):
        self.assertFalse(calendar(ICS, NOW - timedelta(hours=2), NOW)['valid'])
        self.assertFalse(calendar(ICS, NOW + timedelta(minutes=1), NOW)['valid'])
        self.assertFalse(calendar(ICS.replace('SUMMARY:Consumer Price Index', 'SUMMARY:Other'), NOW, NOW)['valid'])

    def test_research_hold_blocks_otherwise_confirmed_setup(self):
        d = fixture(); d['scalp_candles'][-1][4:6] = ['115', '20']
        with patch('analysis.REQUIRED_CONTEXT', ()), patch('analysis.evaluate_calendar', return_value={'clear': True, 'missing': [], 'high_risk': []}):
            now = d['retrieved_at']
            risk = assess(d, Rules(), now)
            self.assertEqual(risk['missing'], [])
            result = plan(d, risk, 'SCALP', True, now)
            self.assertEqual(result['status'], 'NO TRADE')
            self.assertEqual(result['reason_code'], 'RESEARCH_HOLD')

    def test_flash_is_context_only(self):
        result = flows(payload(), 'btc', NOW, NOW)
        self.assertTrue(result['valid'])
        self.assertTrue(result['provisional'])
        self.assertFalse(result['confirmation_eligible'])
        for status in ('flash', 'final'):
            d = fixture()
            d['context'] = flows(payload(status=status), 'btc', NOW, NOW)
            d['scalp_candles'][-1][4:6] = ['115', '20']
            self.assertEqual(plan(d, assess(d, Rules(), d['retrieved_at']), 'SCALP', True, d['retrieved_at'])['status'], 'NO TRADE')

    def test_flow_completeness_freshness_and_pagination(self):
        for change in ('gap', 'old', 'future', 'pagination', 'unknown', 'missing_update'):
            p = payload()
            if change == 'gap': p['data'].pop(3)
            if change == 'old': p['data'] = p['data'][:1]
            if change == 'future': p['data'][-1]['time'] = (NOW + timedelta(days=1)).replace(hour=0).isoformat()
            if change == 'pagination': p['next_page_token'] = 'more'
            if change == 'unknown': p['data'][-1]['FlowInExNtv-status'] = 'unknown'
            if change == 'missing_update': del p['data'][-1]['FlowInExNtv-status-time']
            with self.subTest(change=change):
                self.assertFalse(flows(p, 'btc', NOW, NOW)['valid'])
        self.assertFalse(flows(payload(), 'btc', NOW - timedelta(hours=2), NOW)['valid'])
        self.assertFalse(flows(payload(), 'btc', NOW + timedelta(seconds=1), NOW)['valid'])

    def test_malformed_flows(self):
        for malformed in ([], {}, {'data': None}, {'data': [None]}):
            with self.subTest(payload=malformed), self.assertRaises(ValueError):
                flows(malformed, 'btc', NOW, NOW)
        for field, value in (('FlowInExNtv', 'NaN'), ('FlowOutExNtv', '-1'), ('time', '2026-10-09'),
                             ('asset', 'eth'), ('FlowInExNtv-status-time', 'invalid')):
            p = payload(); p['data'][-1][field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, ArithmeticError)):
                flows(p, 'btc', NOW, NOW)
        p = payload(); p['data'].append(copy.deepcopy(p['data'][-1]))
        with self.assertRaises(ValueError): flows(p, 'btc', NOW, NOW)

    def test_http_integration_and_source_isolation(self):
        ok = Mock(); ok.text = ICS; ok.json.return_value = payload('eth')
        with patch('context.requests.get', side_effect=[ok, ValueError('bad btc'), ok]):
            result = fetch_context()
        self.assertIsNotNone(result['calendar'])
        self.assertIn('btc', result['errors'])
        self.assertIn('eth', result['flows'])

    def test_http_failures_render_as_unavailable(self):
        import requests
        with patch('context.requests.get', side_effect=requests.Timeout('source timeout')):
            result = fetch_context()
        self.assertIsNone(result['calendar'])
        self.assertEqual(result['flows'], {})
        self.assertEqual(set(result['errors']), {'calendar', 'btc', 'eth'})

    def test_populated_context_renders_and_hold_survives_checkbox(self):
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        st.cache_data.clear()
        context = {'calendar': calendar(ICS, NOW, NOW), 'flows': {'btc': flows(payload(), 'btc', NOW, NOW)}, 'errors': {'eth': 'unavailable'}}
        with patch('macro_calendar.fetch_calendar', return_value={'fetched_at': NOW.isoformat(), 'sources': {}, 'events': []}), patch('context.fetch_context', return_value=context), patch('market.fetch', side_effect=lambda symbol, **kwargs: {'symbol': symbol, 'retrieved_at': datetime.now(timezone.utc), 'errors': {}}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any('PROVISIONAL' in x.value for x in app.warning))
            self.assertGreaterEqual(len(app.dataframe), 4)
            app.sidebar.checkbox[0].check().run()
            self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)


@unittest.skipUnless(os.getenv('RUN_LIVE_INTEGRATION') == '1', 'Opt-in read-only network checks')
class LiveIntegrationTests(unittest.TestCase):
    def test_bls_and_both_flow_feeds(self):
        result = fetch_context()
        self.assertIsInstance(result['errors'], dict)
        if result['errors'].get('calendar') or result.get('calendar') is None:
            self.assertFalse((result.get('calendar') or {}).get('valid', False))
        else:
            self.assertTrue(
                result['calendar']['valid'],
                result['calendar']['issues']
            )
        for asset in ('btc', 'eth'):
            self.assertTrue(
                result['flows'][asset]['valid'],
                result['flows'][asset]['issues']
            )
            self.assertFalse(
                result['flows'][asset]['confirmation_eligible']
            )

    def test_live_dashboard(self):
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        st.cache_data.clear()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=90)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(sum(m.value == '**NO TRADE**' for m in app.markdown), 4)
        self.assertFalse(app.sidebar.checkbox[0].value)
