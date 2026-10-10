"""Indicative regional liquidity sessions, not verified venue/holiday opening status."""
from datetime import datetime, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo

SESSIONS = (('ASIA / Tokyo','Asia/Tokyo',9,18),
            ('EUROPE / London','Europe/London',8,17),
            ('USA / New York','America/New_York',8,17))
BOGOTA = ZoneInfo('America/Bogota')


def sessions(now=None):
    now=now or datetime.now(timezone.utc)
    windows=[]
    for name,zone,opening,closing in SESSIONS:
        tz=ZoneInfo(zone)
        today=now.astimezone(tz).date()
        for offset in range(-1,4):
            date=today+timedelta(days=offset)
            if date.weekday()>=5: continue
            start=datetime(date.year,date.month,date.day,opening,tzinfo=tz).astimezone(timezone.utc)
            end=datetime(date.year,date.month,date.day,closing,tzinfo=tz).astimezone(timezone.utc)
            if end < now: continue
            windows.append(dict(name=name,start_utc=start.isoformat(),end_utc=end.isoformat(),
                                colombia_open=start.astimezone(BOGOTA).isoformat(),
                                colombia_close=end.astimezone(BOGOTA).isoformat(),
                                active_scheduled_window=start<=now<end, holiday_status='UNVERIFIED'))
    overlaps=[]
    for a,b in combinations(windows,2):
        if a['name']==b['name']: continue
        start=max(datetime.fromisoformat(a['start_utc']),datetime.fromisoformat(b['start_utc']))
        end=min(datetime.fromisoformat(a['end_utc']),datetime.fromisoformat(b['end_utc']))
        if start<end:
            overlaps.append(dict(sessions=a['name']+' + '+b['name'],
                                 colombia_start=start.astimezone(BOGOTA).isoformat(),
                                 colombia_end=end.astimezone(BOGOTA).isoformat(),active=start<=now<end))
    return dict(windows=windows,overlaps=overlaps,note=(
        'Indicative weekday liquidity windows: Tokyo 09–18, London 08–17, New York 08–17 local. '
        'These conventions are not official exchange hours. Holidays and exceptional closures are unverified; '
        'BTC/ETH trade 24/7. Session activity never clears the macro safety gate.'))
