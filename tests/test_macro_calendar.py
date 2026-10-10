from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch
import requests
import macro_calendar as macro
from analysis import Rules, assess, plan
from test_analysis import fixture, NOW
from trading_sessions import sessions


def bls(day='20261014', status='CONFIRMED', zone='America/New_York'):
    rows=[]
    for i,title in enumerate(('Consumer Price Index','Producer Price Index','Employment Situation')):
        rows.append(f'BEGIN:VEVENT\nUID:event-{i}\nSUMMARY:{title}\nDTSTART;TZID={zone}:{day}T083000\nSTATUS:{status}\nEND:VEVENT')
    return 'BEGIN:VCALENDAR\nVERSION:2.0\n'+ '\n'.join(rows)+'\nEND:VCALENDAR'


def payload(raw=None):
    return dict(fetched_at=NOW.isoformat(), sources={'BLS':dict(url=macro.BLS, checked_at=NOW.isoformat(),
                status='parsed',http_status=200,raw=raw or bls(),coverage_verified=True)},events=[])


class CalendarTests(unittest.TestCase):
    def test_transport_denial_is_reported_before_absent_timestamp(self):
        data=payload()
        data['sources']['BLS'].update(status='unavailable',checked_at=None,http_status=None,
                                      error='Proxy CONNECT 403 Forbidden')
        result=self.isolated(data)
        self.assertFalse(result['clear'])
        self.assertTrue(any('Proxy CONNECT 403' in item for item in result['missing']))
        self.assertFalse(any('Invalid calendar timestamp' in item for item in result['missing']))

    def isolated(self, data, now=NOW, rules=None):
        # Only isolate the deterministic risk engine; never approve production adapters.
        with patch('macro_calendar.source_specs',return_value=[('BLS',macro.BLS,macro.parse_bls)]),\
             patch('macro_calendar.KINDS',('CPI','PPI','NFP')),\
             patch('macro_calendar.VALIDATED_ADAPTERS',frozenset({'BLS'})):
            return macro.evaluate(data,now,rules)

    def test_bls_dst_conversion_and_unverified_figures(self):
        summer=macro.parse_bls(bls('20260714'))[0]
        winter=macro.parse_bls(bls('20261214'))[0]
        self.assertIn('07:30:00-05:00',summer['colombia_start'])
        self.assertIn('08:30:00-05:00',winter['colombia_start'])
        self.assertEqual(summer['importance'],'EXTREME')
        self.assertTrue(summer['timing_verified'])
        for field in ('previous','forecast','actual'): self.assertIsNone(summer[field])

    def test_invalid_ics_timestamp_identity_recurrence_and_completeness(self):
        text=bls()
        variants=[text.replace('END:VCALENDAR',''),text.replace('America/New_York','Floating'),
                  text.replace('20261014T083000','bad'),text.replace('UID:event-1','UID:event-0'),
                  text.replace('STATUS:CONFIRMED','STATUS:UNKNOWN'),
                  text.replace('UID:event-0','UID:event-0\nRRULE:FREQ=MONTHLY'),
                  text.replace('SUMMARY:Employment Situation','SUMMARY:Other'),
                  text.replace('DTSTART;TZID=America/New_York:','DTSTART:'),
                  text.replace('UID:event-0','UID:event-0\nUID:another')]
        for raw in variants:
            with self.subTest(raw=raw[:100]):
                with self.assertRaises((ValueError,KeyError)): macro.parse_bls(raw)

    def test_ambiguous_and_nonexistent_dst_times_are_rejected(self):
        for date in (datetime(2026,3,8,2,30),datetime(2026,11,1,1,30)):
            with self.assertRaises(ValueError): macro.local_time(date,'America/New_York')

    def test_pre_and_post_windows_include_boundaries_and_no_manual_override(self):
        data=payload(bls('20261010'))
        event_time=datetime(2026,10,10,12,30,tzinfo=timezone.utc)
        for delta,expected in ((-61,'CLEAR'),(-60,'HIGH_RISK'),(0,'HIGH_RISK'),(60,'HIGH_RISK'),(61,'CLEAR')):
            now=event_time+timedelta(minutes=delta)
            data['fetched_at']=data['sources']['BLS']['checked_at']=now.isoformat()
            result=self.isolated(data,now)
            self.assertEqual(result['reason_code'],expected)
            self.assertEqual(result['clear'],expected=='CLEAR')
        changed=self.isolated(data,event_time,macro.CalendarRules(120,120,900,24))
        self.assertFalse(changed['clear'])

    def test_missing_stale_future_and_empty_do_not_mean_clear(self):
        variants=[None,{},dict(payload(),sources={}),payload('BEGIN:VCALENDAR\nEND:VCALENDAR')]
        stale=payload(); stale['sources']['BLS']['checked_at']=(NOW-timedelta(seconds=901)).isoformat(); variants.append(stale)
        future=payload(); future['fetched_at']=(NOW+timedelta(seconds=1)).isoformat(); variants.append(future)
        forged=payload(); forged.update(verified=True,complete=True,clear=True,events=[]); variants.append(forged)
        for data in variants:
            result=macro.evaluate(data,NOW)
            self.assertFalse(result['clear'])
            self.assertTrue(result['missing'])

    def test_source_changed_url_and_cached_event_claims_are_rejected(self):
        data=payload(); data['events']=[{'verified':True,'importance':'LOW'}]
        data['sources']['BLS']['url']='https://untrusted.example/calendar'
        self.assertFalse(self.isolated(data)['clear'])
        self.assertTrue(self.isolated(data)['missing'])

    def test_missing_and_high_risk_are_reported_together(self):
        data=payload(bls('20261010'))
        now=datetime(2026,10,10,12,30,tzinfo=timezone.utc)
        data['fetched_at']=data['sources']['BLS']['checked_at']=now.isoformat()
        result=macro.evaluate(data,now)
        self.assertEqual(result['reason_code'],'HIGH_RISK_AND_MISSING_DATA')
        self.assertTrue(result['high_risk'])
        self.assertTrue(result['missing'])

    def test_cancelled_tentative_and_date_only_statuses(self):
        now=datetime(2026,10,10,12,30,tzinfo=timezone.utc)
        for status,expected in (('CANCELLED','CLEAR'),('TENTATIVE','HIGH_RISK')):
            data=payload(bls('20261010',status)); data['fetched_at']=data['sources']['BLS']['checked_at']=now.isoformat()
            self.assertEqual(self.isolated(data,now)['reason_code'],expected)
        text=bls('20261010').replace('DTSTART;TZID=America/New_York:20261010T083000','DTSTART;VALUE=DATE:20261010')
        item=macro.parse_bls(text)[0]
        self.assertFalse(item['timing_verified'])
        self.assertIn('2026-10-09T23:00:00-05:00',item['colombia_start'])

    def test_invalid_settings_never_disable_safety(self):
        for rules in (macro.CalendarRules(0),macro.CalendarRules(-1),macro.CalendarRules(True),
                      macro.CalendarRules(max_age_seconds=999999),macro.CalendarRules(horizon_hours=0)):
            self.assertFalse(self.isolated(payload(),rules=rules)['clear'])

    def test_source_failures_redirects_and_bad_html_fail_closed(self):
        def failure(*a,**k): raise requests.ConnectionError('unavailable')
        result=macro.fetch_calendar(NOW,failure)
        self.assertEqual(len(result['sources']),16)
        self.assertTrue(all(r['status']=='unavailable' for r in result['sources'].values()))
        self.assertFalse(macro.evaluate(result,NOW)['clear'])
        class Response:
            status_code=302; content=b'not a calendar'; text='not a calendar'
            def raise_for_status(self): pass
        result=macro.fetch_calendar(NOW,lambda *a,**k:Response())
        self.assertFalse(macro.evaluate(result,NOW)['clear'])

    def test_official_date_parsers_never_invent_release_times(self):
        ism='<h2>Manufacturing Services</h2><table><tr><td>July 2026</td><td>1</td><td>6**</td></tr></table>'
        events=macro.parse_ism(ism)
        self.assertEqual(len(events),2)
        self.assertTrue(all(not e['timing_verified'] for e in events))
        ecb='<div>29/10/2026</div><div>monetary policy meeting (Day 2), followed by press conference</div>'
        self.assertFalse(macro.parse_ecb(ecb)[0]['timing_verified'])
        boe='<h2>2026 confirmed dates</h2><td>Thursday 5 November</td>'
        self.assertFalse(macro.parse_boe(boe)[0]['timing_verified'])
        boj='<h2>2026</h2><td>Oct. 29 (Thurs.), 30 (Fri.)</td>'
        self.assertFalse(macro.parse_boj(boj)[0]['timing_verified'])
        fed='<h2>October 2026</h2><div>2:00 p.m.</div><div>FOMC Meeting</div><div>28</div>'
        self.assertFalse(macro.parse_fed(fed,2026,10,'official')[0]['timing_verified'])

    def test_global_structured_events_require_explicit_timezone_and_status(self):
        node={'@type':'Event','name':'Consumer price inflation, UK','startDate':'2026-10-10T07:00:00+01:00',
              'eventStatus':'https://schema.org/EventScheduled'}
        def html(value): return '<script type="application/ld+json">'+json.dumps(value)+'</script>'
        item=macro.parse_structured_page(html(node),'ONS')[0]
        self.assertEqual(item['kind'],'UK_CPI')
        self.assertEqual(item['region'],'UK')
        self.assertIn('01:00:00-05:00',item['colombia_start'])
        for mutation in ('timezone','status','postponed'):
            bad=node.copy()
            if mutation=='timezone': bad['startDate']='2026-10-10T07:00:00'
            if mutation=='status': del bad['eventStatus']
            if mutation=='postponed': bad['eventStatus']='https://schema.org/EventPostponed'
            with self.assertRaises(ValueError): macro.parse_structured_page(html(bad),'ONS')

    def test_plan_blocks_macro_even_if_other_inputs_are_isolated(self):
        d=fixture(); d['scalp_candles'][-1][4:6]=['115','20']
        with patch('analysis.REQUIRED_CONTEXT',()):
            risk=assess(d,Rules(),NOW)
            result=plan(d,risk,'SCALP',True,NOW)
            self.assertEqual(result['status'],'NO TRADE')
            self.assertEqual(result['reason_code'],'MISSING_DATA')
            for code,missing,high in (('HIGH_RISK',[],['CPI pre-event']),
                                      ('HIGH_RISK_AND_MISSING_DATA',['ONS stale'],['CPI pre-event'])):
                with patch('analysis.evaluate_calendar',return_value=dict(clear=False,missing=missing,high_risk=high)):
                    result=plan(d,risk,'SCALP',True,NOW)
                    self.assertEqual(result['status'],'NO TRADE')
                    self.assertEqual(result['reason_code'],code)

    def test_sessions_dst_mismatch_overlap_and_weekends(self):
        for date,opening in ((datetime(2026,3,6,12,tzinfo=timezone.utc),'08:00'),
                             (datetime(2026,3,16,12,tzinfo=timezone.utc),'07:00')):
            result=sessions(date)
            us=next(w for w in result['windows'] if w['name'].startswith('USA'))
            self.assertIn('T'+opening,us['colombia_open'])
            self.assertTrue(all(w['holiday_status']=='UNVERIFIED' for w in result['windows']))
            self.assertTrue(any('EUROPE' in o['sessions'] and 'USA' in o['sessions'] for o in result['overlaps']))
        result=sessions(NOW)
        self.assertFalse(any(w['active_scheduled_window'] for w in result['windows']))
        for w in result['windows']:
            self.assertLess(datetime.fromisoformat(w['start_utc']).weekday(),5)

    def test_four_importance_classes(self):
        for kind,expected in (('OTHER','LOW'),('DE_RELEASE','MODERATE'),('PPI','HIGH'),('FOMC','EXTREME')):
            self.assertEqual(macro.event(kind,kind,NOW,NOW,'test')['importance'],expected)
        self.assertEqual(macro.event('DE_RELEASE','Germany consumer price inflation',NOW,NOW,'test')['importance'],'HIGH')

    def test_us_europe_dst_mismatch_changes_overlap_duration(self):
        for day,hours in ((6,4),(16,5),(30,4)):
            now=datetime(2026,3,day,12,tzinfo=timezone.utc)
            result=sessions(now)
            overlap=next(o for o in result['overlaps'] if 'EUROPE' in o['sessions'] and 'USA' in o['sessions'])
            duration=datetime.fromisoformat(overlap['colombia_end'])-datetime.fromisoformat(overlap['colombia_start'])
            self.assertEqual(duration.total_seconds()/3600,hours)

    def test_unverified_json_figures_are_not_promoted(self):
        node={'@type':'Event','name':'GDP monthly estimate, UK',
              'startDate':'2026-10-10T07:00:00Z','eventStatus':'https://schema.org/EventScheduled',
              'previous':3,'forecast':4,'actual':5,'verified':True}
        html='<script type="application/ld+json">'+json.dumps(node)+'</script>'
        item=macro.parse_structured_page(html,'ONS')[0]
        self.assertEqual([item[k] for k in ('previous','forecast','actual')],[None,None,None])
