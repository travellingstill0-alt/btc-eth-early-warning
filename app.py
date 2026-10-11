from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from market import fetch
from risk_warnings import warnings as independent_warnings
from analysis import Rules, assess, plan
from macro_calendar import fetch_calendar, evaluate as evaluate_calendar, CalendarRules
from trading_sessions import sessions
from context import fetch_context, COVERAGE_GAPS, retrieval_issues

st.set_page_config(page_title='BTC & ETH Early Warning', page_icon='⚠️', layout='wide')
st.title('BTC & ETH Early Warning')
st.caption('Informational research only • No trades • Public USD spot and perpetual data • Heuristics, not predictions')
st.warning('NO TRADE research hold active. Daily exchange flows are context only. Unavailable, stale or unverified global macro calendars also block ENTER. High-risk event windows independently return NO TRADE.')
with st.sidebar:
    st.header('Transparent rules')
    move = st.number_input('24h absolute move threshold (%)', min_value=0.1, value=4.0)
    funding = st.number_input('Absolute funding threshold (% per 8h)', min_value=0.001, value=0.03, format='%.3f')
    st.caption('Kraken hourly funding is compared with one eighth of this threshold. Actual provider rates and periods are displayed; no eight-hour rate is fabricated.')
    oi = st.number_input('OI growth threshold (%)', min_value=0.1, value=10.0)
    oi_window = st.selectbox('Required OI risk lookback', ['24h', '4h'])
    st.caption('24h preserves the original risk lookback. A selected OI window must have fresh, verified coverage before ENTER is allowed.')
    stale = st.number_input('Maximum snapshot age (seconds)', min_value=30, value=180)
    macro_clear = st.checkbox('I reviewed upcoming macro events for my trading horizon', value=False)
    st.caption('Manual review is additional protection. This checkbox cannot override missing calendar data or high-risk event windows.')
    pre = st.number_input('Macro pre-event warning (minutes)', min_value=1, max_value=1440, value=60)
    post = st.number_input('Macro post-event warning (minutes)', min_value=1, max_value=1440, value=60)
    calendar_age = st.number_input('Maximum calendar verification age (seconds)', min_value=300, max_value=3600, value=900)
    macro_horizon = st.number_input('Macro display horizon (hours)', min_value=1, max_value=168, value=24)
    st.markdown('[Federal Reserve calendar](https://www.federalreserve.gov/newsevents/calendar.htm) · [BLS releases](https://www.bls.gov/schedule/news_release/)')
    st.write('Score: move +2, funding +2, OI growth +2, bearish structure +1. LOW 0–1; MODERATE 2–3; HIGH 4–5; EXTREME 6–7. Missing data blocks ENTER independently of score.')
    if st.button('Retrieve fresh data'):
        st.cache_data.clear()

@st.cache_data(ttl=60)
def snapshot(symbol, maximum_age):
    return fetch(symbol, max_age=maximum_age)

@st.cache_data(ttl=300)
def calendar_snapshot():
    return fetch_calendar()

@st.cache_data(ttl=60)
def context_snapshot():
    return fetch_context()

def render_context(context):
    now = datetime.now(timezone.utc)
    st.subheader('Economic calendar — BLS, partial US coverage')
    calendar = context.get('calendar')
    if calendar:
        issues = calendar['issues'] + retrieval_issues(calendar['retrieved_at'], now, 3600)
        st.caption(f"Retrieved {calendar['retrieved_at'].isoformat()} • event times UTC • 45-day horizon")
        st.write(calendar['note'])
        if issues:
            st.warning('Calendar UNVERIFIED: ' + '; '.join(issues))
        else:
            st.info('BLS schedule validated; global macro coverage remains incomplete.')
        st.dataframe([{'Release': e['title'], 'Scheduled UTC': e['time'].isoformat()} for e in calendar['events']], hide_index=True)
    else:
        st.warning('BLS calendar UNAVAILABLE')
    with st.expander('Macro coverage gaps', expanded=True):
        for region, gap in COVERAGE_GAPS.items():
            st.write(f'{region}: {gap}')
    st.subheader('Daily exchange flows — broader market context')
    st.caption('Exchange-labelled on-chain flows in native BTC/ETH units. Daily intervals begin at 00:00 UTC. Positive net inflow = inflow minus outflow; no directional trade recommendation. Not real-time scalp confirmation or cross-exchange taker flow.')
    for asset in ('btc', 'eth'):
        flow = context.get('flows', {}).get(asset)
        if not flow:
            st.warning(f'{asset.upper()} exchange flows UNAVAILABLE')
            continue
        issues = flow['issues'] + retrieval_issues(flow['retrieved_at'], now, 3600)
        st.caption(f"{asset.upper()} retrieved {flow['retrieved_at'].isoformat()} • seven completed daily intervals required • latest observation maximum age 72h")
        if flow['rows']:
            st.caption('Latest metric publication timestamps: ' + str(flow['rows'][-1]['updated_at']))
        if issues:
            st.warning(f"{asset.upper()} exchange flows UNVERIFIED: " + '; '.join(issues))
        if flow['provisional']:
            st.warning(f'{asset.upper()} PROVISIONAL — Coin Metrics flash data may be revised. Cannot unlock ENTER.')
        st.dataframe([{'Day UTC': r['time'].date().isoformat(), 'Inflow': str(r['inflow']),
                       'Outflow': str(r['outflow']), 'Net inflow': str(r['net_inflow']),
                       'Status': 'PROVISIONAL (flash)' if r['provisional'] else ' / '.join(r['statuses'].values())}
                      for r in flow['rows']], hide_index=True)
    if context.get('errors'):
        with st.expander('Context source errors'):
            st.json(context['errors'])

@st.fragment(run_every='60s')
def dashboard():
    render_context(context_snapshot())
    calendar_data = calendar_snapshot()
    macro = evaluate_calendar(calendar_data, rules=CalendarRules(int(pre), int(post), int(calendar_age), int(macro_horizon)))
    st.subheader('Global macro calendar · Colombia time')
    st.write('Macro safety: **' + macro['reason_code'] + '**')
    if not macro['clear']:
        st.warning('NO TRADE: ' + ('; '.join(macro['high_risk']) or 'Critical calendar information is missing, stale or unverified.'))
    if macro['events']:
        st.dataframe(pd.DataFrame([{key: e.get(key) for key in ('region', 'title', 'importance', 'colombia_start', 'colombia_end', 'status', 'timing_verified', 'previous', 'forecast', 'actual', 'source')} for e in macro['events']]), hide_index=True)
    else:
        st.write('No verified calendar coverage. An empty list does not mean no upcoming events.')
    st.caption('America/Bogota (UTC−05:00). International daylight saving follows source timezones. Unknown times cover the whole source-local day. Previous, forecast and actual figures are unavailable unless verified. Calendar refreshes every five minutes while active; safety is rechecked every minute.')
    with st.expander('Calendar coverage and source diagnostics'):
        st.write(macro['missing'])
        st.json({name: {k: v for k, v in report.items() if k != 'raw'} for name, report in calendar_data.get('sources', {}).items()})
    schedule = sessions()
    st.subheader('Regional sessions and overlaps · Colombia time')
    st.caption(schedule['note'])
    st.dataframe(pd.DataFrame(schedule['windows']), hide_index=True)
    st.dataframe(pd.DataFrame(schedule['overlaps']), hide_index=True)
    for symbol in ('BTCUSD', 'ETHUSD'):
        data = dict(snapshot(symbol, int(stale)), macro_calendar=calendar_data)
        with st.expander('Independent early warnings'):
            st.json(independent_warnings(data, int(datetime.now(timezone.utc).timestamp()*1000), int(stale), funding, oi, oi_window))
        risk = assess(data, Rules(move, funding, oi, int(stale), oi_window, int(pre), int(post), int(calendar_age), int(macro_horizon)))
        st.subheader(symbol.replace('USD', ' / USD'))
        st.caption(f"Retrieved {data['retrieved_at'].isoformat()} • UI evaluated {datetime.now(timezone.utc).isoformat()} • UTC • refresh every 60s while this page is active")
        st.write(f"Risk: **{risk['level']}** — score {risk['score']}/7 — {'INCOMPLETE' if risk['missing'] else 'core inputs available'}")
        st.write('; '.join(risk['reasons']) or 'No configured threshold triggered in available inputs.')
        if risk['missing']:
            st.error('Missing/stale inputs: ' + ', '.join(risk['missing']))
        for warning in data.get('warnings', []):
            st.warning(warning)
        ticker, interest, funding_data = data.get('ticker', {}), data.get('interest', {}), data.get('funding', {})
        change = ticker.get('priceChangePercent')
        cols = st.columns(3)
        cols[0].metric('Spot price (USD)', f"{float(ticker['lastPrice']):,.2f}" if ticker else 'Unavailable', f"{float(change):+.2f}% / 24h" if change is not None else None)
        cols[1].metric(f"24h spot volume ({symbol[:3]})", f"{float(ticker['baseVolume']):,.3f}" if ticker else 'Unavailable')
        cols[2].metric(f"Perpetual OI ({interest.get('unit', 'unknown units')})", f"{float(interest['openInterest']):,.2f}" if interest else 'Unavailable')
        st.write('Funding rate: ' + (f"{float(funding_data['lastFundingRate']) * 100:.5f}% / {funding_data.get('period_hours', 8)}h" if funding_data else 'Unavailable'))
        for key, label in [('ticker', 'Spot price / volume'), ('interest', 'Open interest'), ('funding', 'Funding'),
                           ('candles', 'Hourly candles'), ('scalp_candles', 'Five-minute candles'), ('trades', 'Sampled taker flow')]:
            source = data.get('sources', {}).get(key)
            if source:
                source_time = datetime.fromtimestamp(source['source_time_ms'] / 1000, timezone.utc)
                age = (datetime.now(timezone.utc) - source_time).total_seconds()
                limit = source.get('interval_seconds', 0) * 2 or int(stale)
                status = 'STALE' if age > limit or age < -5 else 'Recent source timestamp'
                st.caption(f"{label}: {source['provider']} · {source['instrument']} · {source_time.isoformat()} · {source['timestamp_kind']} · {status} ({age:.1f}s). {source.get('note', '')}")
        if change is None:
            st.warning('Rolling 24h price change: Unavailable. Required for complete risk assessment.')
        history_source = data.get('sources', {}).get('interest_history', {})
        st.caption(f"OI history: {history_source.get('provider', 'Unavailable')} · {history_source.get('instrument', 'unknown contract')} · {history_source.get('unit', 'unknown units')} · {history_source.get('method', 'No verified history')}. Histories remain separate after provider fallback.")
        st.caption('OI changes use a real baseline at or up to 90 seconds before each target, without interpolation. Gaps over 180 seconds invalidate a window. Stored snapshots accumulate only during active refreshes or explicit data checks.')
        for window in ('15m', '1h', '4h', '24h'):
            result = risk['oi_changes'][window]
            label = f'OI change {window}' + (' (required for risk)' if window == oi_window else '')
            if result['change_pct'] is None:
                st.write(f"{label}: Unavailable — {result['reason']}")
            else:
                start = datetime.fromtimestamp(result['baseline_time_ms'] / 1000, timezone.utc).isoformat()
                end = datetime.fromtimestamp(result['end_time_ms'] / 1000, timezone.utc).isoformat()
                st.write(f"{label}: **{result['change_pct']:+.2f}%** · {start} to {end} · {result['observation_count']} observations")
        st.write('Hourly market structure: **' + risk['structure'] + '** (comparison of two completed 20-hour ranges)')
        trades = data.get('trades', [])
        if trades:
            delta = sum(float(t['q']) * (-1 if t['m'] else 1) for t in trades)
            start, end = [datetime.fromtimestamp(int(t['T']) / 1000, timezone.utc).isoformat() for t in (trades[0], trades[-1])]
            st.write(f'Sampled spot taker flow delta: **{delta:+,.3f} base units**, {len(trades)} public trades, {start} to {end}.')
            st.caption('Buy taker minus sell taker volume, classified by the provider’s documented trade side. This limited sample is an order-flow proxy. This sample is not CVD; verified perpetual CVD is shown separately.')
        else:
            st.write('Sampled spot taker flow: Unavailable')
        for key, label in (('cvd', 'Perpetual CVD / 15 completed minutes'),
                           ('liquidations', 'Executed liquidation volume / 15 completed minutes')):
            item, result = data.get(key), risk.get('context', {}).get(key)
            if item and result:
                start = datetime.fromtimestamp(item['start_ms']/1000, timezone.utc).isoformat()
                end = datetime.fromtimestamp(item['end_ms']/1000, timezone.utc).isoformat()
                st.write(f"{label}: **{result['value']:+,.6f} {item['unit']}** · {item['provider']} · {item['instrument']} · {start} to {end}")
                st.caption(f"{item['method']} · {result['count']} observations. Scope is this exchange contract only; providers and units are never combined.")
            else:
                st.warning(f'{label}: UNAVAILABLE or stale — required safety input; NO TRADE.')
        rows = data.get('candles', [])
        if rows:
            frame = pd.DataFrame({'UTC': [pd.to_datetime(r[0], unit='ms', utc=True) for r in rows], 'Close': [float(r[4]) for r in rows]})
            st.line_chart(frame.set_index('UTC'))
        for column, horizon in zip(st.columns(2), ('SCALP', 'DAY TRADE')):
            with column:
                st.markdown(f'### {horizon}')
                p = plan(data, risk, horizon, macro_clear)
                st.markdown(f"**{p.pop('status')}**")
                for key, value in p.items():
                    st.write(f"{key.replace('_', ' ').capitalize()}: {value:,.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').capitalize()}: {value}")
        st.info('Liquidation heatmap: UNAVAILABLE — future liquidation levels are not inferred from executed liquidations. Daily Coin Metrics exchange flows are shown above as context only; their provisional/daily resolution cannot satisfy the required fresh exchange-flow safety input.')
        with st.expander('Source diagnostics and timestamps'):
            st.json(data.get('exchange_flow_diagnostics', {'status': 'unavailable', 'safety_eligible': False}))
            st.write('Spot: Coinbase → Kraken. Candles and sampled taker flow: Kraken → Coinbase. Perpetual OI/funding: Kraken Futures → Deribit. OI history: Kraken minute analytics or persistent observations for the selected provider, contract and units. No history is fabricated or interpolated. Perpetual CVD: Kraken analytics → complete Deribit tape. Executed liquidations: Kraken analytics → complete Kraken execution history; gaps fail closed.')
            st.json({key: value for key, value in data['errors'].items()})
            st.json(data.get('sources', {}))
            st.json(data.get('attempts', []))
    st.caption('No background alerts, notifications, scheduled monitoring or trading execution are implemented. Refresh stops when the session is inactive.')

dashboard()
