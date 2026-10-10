"""Official-source macro calendar; uncertain coverage/timing fails closed."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import calendar
import hashlib
import json
import re
import time
from zoneinfo import ZoneInfo
import requests

UTC = timezone.utc
BOGOTA = ZoneInfo('America/Bogota')
KINDS = ('CPI', 'PPI', 'NFP', 'FOMC', 'ISM_MANUFACTURING', 'ISM_SERVICES', 'FED_SPEECH', 'ECB', 'BOJ')
BLS = 'https://www.bls.gov/schedule/news_release/bls.ics'
ISM = 'https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar'
ECB = 'https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html'
BOJ = 'https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm'
# Transport access and live schemas/coverage have not been certified in this environment.
# Never accept a payload's self-asserted verified/complete flags instead.
VALIDATED_ADAPTERS = frozenset()


@dataclass(frozen=True)
class CalendarRules:
    pre_minutes: int = 60
    post_minutes: int = 60
    max_age_seconds: int = 900
    horizon_hours: int = 24

    def validate(self):
        for value, low, high in ((self.pre_minutes, 1, 1440), (self.post_minutes, 1, 1440),
                                 (self.max_age_seconds, 30, 3600), (self.horizon_hours, 1, 168)):
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError('Invalid calendar risk rules')


def local_time(value, zone):
    """Reject ambiguous/nonexistent local times, rather than choosing a DST fold."""
    tz = ZoneInfo(zone)
    a, b = value.replace(tzinfo=tz, fold=0), value.replace(tzinfo=tz, fold=1)
    if a.utcoffset() != b.utcoffset() or a.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != value:
        raise ValueError('Ambiguous or nonexistent event time')
    return a.astimezone(UTC)


def event(kind, title, start, end, source, timing_verified=False, status='scheduled'):
    if end < start:
        raise ValueError('Reversed event interval')
    importance = IMPORTANCE.get(kind, 'HIGH')
    if kind == 'DE_RELEASE' and any(term in title.lower() for term in
            ('inflation', 'consumer price', 'gdp', 'gross domestic', 'employment', 'unemployment', 'industrial production')):
        importance = 'HIGH'
    return dict(id=hashlib.sha256(f'{source}|{kind}|{start.isoformat()}|{title}'.encode()).hexdigest()[:20],
                kind=kind, title=title, importance=importance, region=REGIONS.get(kind, 'UNKNOWN'),
                previous=None, forecast=None, actual=None,
                start_utc=start.isoformat(), end_utc=end.isoformat(), source=source,
                timing_verified=timing_verified, status=status,
                colombia_start=start.astimezone(BOGOTA).isoformat(),
                colombia_end=end.astimezone(BOGOTA).isoformat())


def day_event(kind, title, day, zone, source):
    start = local_time(datetime.combine(day, datetime.min.time()), zone)
    end = local_time(datetime.combine(day+timedelta(days=1), datetime.min.time()), zone)
    return event(kind, title+' (time unverified; whole source-local day)', start, end, source)


def parse_bls(text, source=BLS):
    """Strict bounded iCalendar subset: unsupported revisions/recurrences fail closed."""
    if not text.strip().startswith('BEGIN:VCALENDAR') or not text.strip().endswith('END:VCALENDAR'):
        raise ValueError('Missing/truncated BLS iCalendar envelope')
    lines = re.sub(r'\r?\n[ \t]', '', text).splitlines()
    blocks, block = [], None
    for line in lines:
        if line == 'BEGIN:VEVENT':
            if block is not None: raise ValueError('Nested event')
            block = {}
        elif line == 'END:VEVENT':
            if block is None: raise ValueError('Unmatched event end')
            blocks.append(block); block = None
        elif block is not None:
            if ':' not in line: raise ValueError('Invalid calendar property')
            head, value = line.split(':', 1)
            name = head.split(';')[0]
            if name in block: raise ValueError('Duplicate calendar property')
            block[name] = (head, value)
    if block is not None or not blocks: raise ValueError('Empty/truncated event feed')
    events, identities = [], set()
    labels = {'Consumer Price Index':'CPI', 'Producer Price Index':'PPI', 'Employment Situation':'NFP'}
    for row in blocks:
        title = row.get('SUMMARY', ('',''))[1]
        kind = next((v for k,v in labels.items() if title.startswith(k)), None)
        if kind is None: continue
        if any(k in row for k in ('RRULE', 'RDATE', 'EXDATE', 'RECURRENCE-ID')):
            raise ValueError('Unsupported recurring/revised event')
        uid = row['UID'][1]
        if not uid or uid in identities: raise ValueError('Duplicate/missing event identity')
        identities.add(uid)
        status = row.get('STATUS', ('','CONFIRMED'))[1]
        if status not in ('CONFIRMED','CANCELLED','TENTATIVE'): raise ValueError('Unknown event status')
        head, value = row['DTSTART']
        if 'VALUE=DATE' in head or re.fullmatch(r'\d{8}', value):
            day = datetime.strptime(value, '%Y%m%d').date()
            item = day_event(kind,title,day,'America/New_York',source)
            item['status'] = {'CONFIRMED':'scheduled','CANCELLED':'cancelled','TENTATIVE':'tentative'}[status]
            events.append(item); continue
        if value.endswith('Z'):
            start = datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC)
        else:
            match = re.search(r';TZID="?([^;"\s]+)"?', head)
            if not match or match[1] not in ('America/New_York', 'US/Eastern'):
                raise ValueError('Unverified/floating BLS timezone')
            start = local_time(datetime.strptime(value, '%Y%m%dT%H%M%S'), match[1])
        if 'DURATION' in row: raise ValueError('Unsupported event duration')
        end = start
        if 'DTEND' in row:
            end_head,end_value=row['DTEND']
            if end_value.endswith('Z'):
                end=datetime.strptime(end_value,'%Y%m%dT%H%M%SZ').replace(tzinfo=UTC)
            else:
                zone=re.search(r';TZID="?([^;"\s]+)"?',end_head)
                if not zone or zone[1] not in ('America/New_York','US/Eastern'): raise ValueError('Invalid end timezone')
                end=local_time(datetime.strptime(end_value,'%Y%m%dT%H%M%S'),zone[1])
        events.append(event(kind,title,start,end,source,status=='CONFIRMED',
                            {'CONFIRMED':'scheduled','CANCELLED':'cancelled','TENTATIVE':'tentative'}[status]))
    if set(e['kind'] for e in events) != {'CPI','PPI','NFP'}: raise ValueError('Incomplete BLS event categories')
    return events


class Page(HTMLParser):
    """Retain semantic table cells and text tokens; ignore scripts/styles."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tokens, self.rows, self.row, self.cell, self.skip = [], [], None, None, 0
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip += 1
        if tag == 'tr': self.row = []
        if tag in ('td','th'): self.cell = []
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip = max(0,self.skip-1)
        if tag in ('td','th') and self.cell is not None:
            if self.row is not None: self.row.append(' '.join(self.cell))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row = None
    def handle_data(self, text):
        text = ' '.join(text.split())
        if text and not self.skip:
            self.tokens.append(text)
            if self.cell is not None: self.cell.append(text)


def month_number(name):
    return next(i for i in range(1,13) if calendar.month_name[i].lower().startswith(name.rstrip('.').lower()))


def parse_ism(text, source=ISM):
    page=Page(text); events=[]
    if not any('Manufacturing' in t for t in page.tokens) or not any('Services' in t for t in page.tokens):
        raise ValueError('ISM calendar schema missing')
    for row in page.rows:
        if len(row)!=3: continue
        match=re.fullmatch(r'([A-Za-z]+) (20\d{2})',row[0])
        if not match: continue
        for cell,kind in zip(row[1:],('ISM_MANUFACTURING','ISM_SERVICES')):
            day=re.fullmatch(r'(\d{1,2})(?:\*+)?',cell.replace(' ',''))
            if not day: raise ValueError('Unrecognized ISM release date')
            date=datetime(int(match[2]),month_number(match[1]),int(day[1])).date()
            # Official page says EST, including summer. Do not silently assume EDT.
            events.append(day_event(kind,kind.replace('_',' '),date,'America/New_York',source))
    if not events: raise ValueError('No ISM release rows')
    return events


def parse_ecb(text, source=ECB):
    tokens=Page(text).tokens; events=[]
    for i,t in enumerate(tokens):
        if re.fullmatch(r'\d{2}/\d{2}/20\d{2}',t):
            description=' '.join(tokens[i+1:i+3])
            if 'monetary policy meeting' in description.lower() and 'Day 2' in description:
                day=datetime.strptime(t,'%d/%m/%Y').date()
                events.append(day_event('ECB','ECB monetary policy decision',day,'Europe/Berlin',source))
    if not events: raise ValueError('No ECB monetary decision dates')
    return events


def parse_boj(text, source=BOJ):
    page=Page(text); events=[]; year=None
    # Associate each row with its table's year; never borrow years from footer/nav.
    for token in page.tokens:
        if re.fullmatch('20\\d{2}',token):
            year=int(token)
        match=re.fullmatch(r'([A-Za-z]+)\.? (\d{1,2}) \([A-Za-z]+\. ?\), (\d{1,2}) \([A-Za-z]+\. ?\)(?:.*)?',token)
        if match and year:
            day=datetime(year,month_number(match[1]),int(match[3])).date()
            events.append(day_event('BOJ','Bank of Japan monetary policy decision',day,'Asia/Tokyo',source))
    if not events: raise ValueError('No BOJ meeting dates or unrecognized format')
    return events


def parse_fed(text, year, month, source):
    page=Page(text); tokens=page.tokens; events=[]
    expected=f'{calendar.month_name[month]} {year}'
    if expected not in ' '.join(tokens): raise ValueError('Wrong Fed calendar month')
    for i,token in enumerate(tokens):
        kind = 'FED_SPEECH' if re.match(r'(Speech|Discussion|Remarks)\s*-',token) else 'FOMC' if token in ('FOMC Meeting','FOMC Press Conference') else None
        if not kind: continue
        # Only associate the explicitly separate release day, not day numbers in titles.
        day=next((t for t in tokens[i+1:i+15] if re.fullmatch(r'\d{1,2}',t)),None)
        if not day: raise ValueError('Fed event day unavailable')
        date=datetime(year,month,int(day)).date()
        events.append(day_event(kind,token,date,'America/New_York',source))
    if not events: raise ValueError('No Fed events or unrecognized calendar schema')
    return events


def fetch_calendar(now=None, request=None):
    now=now or datetime.now(UTC)
    request=request or requests.get
    result=dict(fetched_at=now.isoformat(),sources={},events=[])
    deadline=time.monotonic()+20
    for name,url,parser in source_specs(now):
        report=dict(url=url,checked_at=None,status='unavailable',coverage_verified=False,http_status=None)
        result['sources'][name]=report
        try:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise ValueError('Calendar refresh budget exhausted; source unverified')
            response=request(url,timeout=min(4,remaining),allow_redirects=False,
                             headers={'User-Agent':'BTCETH-ReadOnlyDashboard/1.0','Cache-Control':'no-cache'})
            report['http_status']=response.status_code
            response.raise_for_status()
            if response.status_code != 200: raise ValueError('Redirect/non-200 calendar response')
            if len(response.content)>2_000_000: raise ValueError('Oversized calendar response')
            # Raw responses are retained so safety validation can reparse at decision time.
            report.update(raw=response.text,checked_at=(now if request is not requests.get else datetime.now(UTC)).isoformat())
            report['http_date']=getattr(response,'headers',{}).get('Date')
            report['last_modified']=getattr(response,'headers',{}).get('Last-Modified')
            events=parser(response.text)
            report.update(status='parsed',event_count=len(events),digest=hashlib.sha256(response.text.encode()).hexdigest())
            result['events'].extend(events)
        except (requests.RequestException,ValueError,KeyError,TypeError,OverflowError,AttributeError,StopIteration) as exc:
            report['error']=str(exc)
    result['events'].sort(key=lambda e:e['start_utc'])
    return result


def aware(value):
    if not isinstance(value,str): raise ValueError('Invalid calendar timestamp')
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError('Calendar timestamp needs timezone')
    return dt.astimezone(UTC)


# Global additions deliberately retain source/schema/coverage uncertainty.
GLOBAL_SOURCES = {
    'ECB_SPEECH': ('https://www.ecb.europa.eu/press/calendars/weekly/html/index.en.html', ('ECB_SPEECH',)),
    'EUROSTAT': ('https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar', ('EU_CPI','EU_GDP')),
    'SPGLOBAL': ('https://www.pmi.spglobal.com/Public/Release/ReleaseDates?language=en', ('EU_PMI',)),
    'DESTATIS': ('https://www.destatis.de/EN/Press/Dates/Weekly-Preview/_node.html', ('DE_RELEASE',)),
    'BOE': ('https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates', ('BOE',)),
    'ONS': ('https://www.ons.gov.uk/releasecalendar?release-type=type-upcoming', ('UK_CPI','UK_GDP','UK_EMPLOYMENT')),
    'BOJ_SPEECH': ('https://www.boj.or.jp/en/about/calendar/index.htm', ('UEDA_SPEECH',)),
    'CHINA_NBS': ('https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/', ('CHINA_PMI','CHINA_GDP')),
    'PBOC': ('https://www.pbc.gov.cn/en/3688229/3688335/3730276/index.html', ('PBOC',)),
}
BASE_KINDS = KINDS
KINDS = BASE_KINDS + tuple(k for _,kinds in GLOBAL_SOURCES.values() for k in kinds)
REGIONS = {k: 'USA' for k in BASE_KINDS if k not in ('ECB','BOJ')}
REGIONS.update({k:'EUROPE' for k in ('ECB','ECB_SPEECH','EU_CPI','EU_GDP','EU_PMI','DE_RELEASE')})
REGIONS.update({k:'UK' for k in ('BOE','UK_CPI','UK_GDP','UK_EMPLOYMENT')})
REGIONS.update({k:'ASIA' for k in ('BOJ','UEDA_SPEECH','CHINA_PMI','CHINA_GDP','PBOC')})
IMPORTANCE = {k: 'HIGH' for k in KINDS}
IMPORTANCE.update({k:'EXTREME' for k in ('CPI','NFP','FOMC','ECB','BOE','BOJ','PBOC')})
IMPORTANCE.update({'DE_RELEASE':'MODERATE', 'OTHER':'LOW'})


def parse_boe(text, source=GLOBAL_SOURCES['BOE'][0]):
    events=[]; year=None
    for token in Page(text).tokens:
        match=re.search(r'(20\d{2}) confirmed dates',token)
        if match: year=int(match[1])
        date=re.fullmatch(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday) (\d{1,2}) ([A-Za-z]+)',token)
        if date and year:
            day=datetime(year,month_number(date[2]),int(date[1])).date()
            events.append(day_event('BOE','Bank of England MPC decision',day,'Europe/London',source))
    if not events: raise ValueError('No confirmed BOE meeting dates')
    return events


class StructuredEvents(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.capture=False; self.parts=[]; self.documents=[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('type')=='application/ld+json':
            self.capture=True; self.parts=[]
    def handle_data(self,data):
        if self.capture: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.capture:
            self.documents.append(json.loads(''.join(self.parts))); self.capture=False


def classify(name,title):
    t=title.lower()
    patterns={
        'EUROSTAT': [('inflation','EU_CPI'),('hicp','EU_CPI'),('gdp','EU_GDP'),('gross domestic','EU_GDP')],
        'ONS': [('consumer price','UK_CPI'),('gdp','UK_GDP'),('gross domestic','UK_GDP'),('labour market','UK_EMPLOYMENT'),('employment','UK_EMPLOYMENT')],
        'CHINA_NBS': [('purchasing managers','CHINA_PMI'),('pmi','CHINA_PMI'),('gdp','CHINA_GDP')],
        'BOJ_SPEECH': [('ueda','UEDA_SPEECH')],
    }
    if name in patterns: return next((kind for term,kind in patterns[name] if term in t),None)
    if name=='SPGLOBAL':
        return 'EU_PMI' if ('eurozone' in t or 'euro area' in t) and 'pmi' in t else None
    return GLOBAL_SOURCES[name][1][0]


def parse_structured_page(text,name):
    """Accept explicit schema.org Event timestamps, never scrape guessed times."""
    documents=StructuredEvents(text).documents; events=[]
    for document in documents:
        nodes=document if isinstance(document,list) else document.get('@graph',[document])
        for node in nodes:
            if not isinstance(node,dict) or node.get('@type')!='Event': continue
            title=node['name']; kind=classify(name,title)
            if not kind: continue
            start=aware(node['startDate']); end=aware(node.get('endDate',node['startDate']))
            status=node.get('eventStatus','')
            if status not in ('https://schema.org/EventScheduled','https://schema.org/EventCancelled'):
                raise ValueError('Missing, postponed or unverified event status')
            events.append(event(kind,title,start,end,GLOBAL_SOURCES[name][0],True,
                                'cancelled' if status.endswith('EventCancelled') else 'scheduled'))
    if not events:
        raise ValueError(f'{name}: no explicit structured event dates/status; coverage unavailable')
    return events


def source_specs(now):
    specs=[('BLS',BLS,parse_bls),('ISM',ISM,parse_ism),('ECB',ECB,parse_ecb),('BOJ',BOJ,parse_boj)]
    for delta in (-1,0,1):
        index=now.year*12+now.month-1+delta; year,month=divmod(index,12); month+=1
        url=f'https://www.federalreserve.gov/newsevents/{year}-{calendar.month_name[month].lower()}.htm'
        specs.append((f'FED:{year}-{month:02d}',url,
                      lambda text, y=year,m=month,u=url: parse_fed(text,y,m,u)))
    for name,(url,kinds) in GLOBAL_SOURCES.items():
        parser=parse_boe if name=='BOE' else lambda text,n=name: parse_structured_page(text,n)
        specs.append((name,url,parser))
    return specs


def evaluate(payload, now=None, rules=None):
    now=now or datetime.now(UTC); rules=rules or CalendarRules()
    result=dict(clear=False,warnings=[],events=[],missing=[],high_risk=[],
                reason_code='MISSING_DATA',reason='Calendar unavailable; NO TRADE.')
    try:
        rules.validate()
        if not isinstance(payload,dict): raise ValueError('Missing automatic macro calendar')
        fetched=aware(payload['fetched_at'])
        if not 0 <= (now-fetched).total_seconds() <= rules.max_age_seconds:
            result['missing'].append('Stale/future calendar retrieval')
        categories=set(); identities=set()
        for name,url,parser in source_specs(now):
            try:
                report=payload['sources'][name]
                if report['url']!=url or report['status']!='parsed' or report['http_status']!=200:
                    raise ValueError(report.get('error') or 'Invalid/unavailable source')
                checked=aware(report['checked_at'])
                if not 0 <= (now-checked).total_seconds() <= rules.max_age_seconds:
                    result['missing'].append(f'{name}: stale source verification')
                events=parser(report['raw'])
                # No adapter is admitted until actual timing and interval coverage is validated.
                if name.split(':')[0] not in VALIDATED_ADAPTERS or report.get('coverage_verified') is not True:
                    result['missing'].append(f'{name}: event timing and coverage unverified')
                categories.update(e['kind'] for e in events)
                for item in events:
                    if item['id'] in identities: raise ValueError('Duplicate/conflicting event identity')
                    identities.add(item['id'])
                    event_start,event_end=aware(item['start_utc']),aware(item['end_utc'])
                    if event_end < now-timedelta(minutes=rules.post_minutes) or event_start > now+timedelta(hours=rules.horizon_hours,minutes=rules.pre_minutes): continue
                    result['events'].append(item)
                    if item['status']=='cancelled': continue
                    if item['importance'] in ('HIGH','EXTREME') and event_start-timedelta(minutes=rules.pre_minutes) <= now <= event_end+timedelta(minutes=rules.post_minutes):
                        phase='pre-event' if now < event_start else 'post-event' if now > event_end else 'event'
                        result['high_risk'].append(f"{item['kind']}: {phase} volatility window"+
                                                  (' (timing/status unverified)' if not item['timing_verified'] else ''))
                    elif item['importance'] in ('LOW','MODERATE') and event_start-timedelta(minutes=rules.pre_minutes) <= now <= event_end+timedelta(minutes=rules.post_minutes):
                        result['warnings'].append(f"{item['kind']}: {item['importance']} volatility warning")
            except (ValueError,KeyError,TypeError,OverflowError,AttributeError,StopIteration) as exc:
                result['missing'].append(f'{name}: {exc}')
        result['missing'].extend('Missing category: '+k for k in sorted(set(KINDS)-categories))
        result['clear']=not result['missing'] and not result['high_risk']
        result['reason_code']='HIGH_RISK_AND_MISSING_DATA' if result['high_risk'] and result['missing'] else 'HIGH_RISK' if result['high_risk'] else 'MISSING_DATA' if result['missing'] else 'CLEAR'
        result['reason']='Verified calendar outside high-risk windows.' if result['clear'] else result['reason_code']+': '+ '; '.join(result['high_risk']+result['missing'])+'; NO TRADE.'
        result['events'].sort(key=lambda e:e['start_utc'])
    except (ValueError,KeyError,TypeError,OverflowError,AttributeError,StopIteration) as exc:
        result['missing'].append(str(exc)); result['reason']=str(exc)+'; NO TRADE.'
    return result
