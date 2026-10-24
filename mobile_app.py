"""Android presentation workstream; shared strategies remain unchanged."""
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from market import fetch
from analysis import assess, Rules
from macro_calendar import fetch_calendar, evaluate, CalendarRules
from risk_warnings import warnings
from mobile_support import fresh_value, research_rows, demo_notification, NOTIFICATION_KINDS

st.set_page_config(page_title='BTC/ETH Watch', page_icon='⚠️', layout='centered', initial_sidebar_state='collapsed')
st.html('''<style>
.block-container {padding-top:1.2rem; padding-bottom:2rem; max-width:900px}
[data-testid="stMetricValue"] {font-size:1.7rem}
[data-testid="stToolbar"] {display:none} button {min-height:44px} p, li {overflow-wrap:anywhere}
@media(max-width:600px) {.block-container {padding-left:1rem;padding-right:1rem}
[data-testid="stHorizontalBlock"] {flex-wrap:wrap}
[data-testid="stColumn"] {min-width:100%!important;width:100%!important}}
</style>''')
# Fail closed: public test deployment requires a separate Streamlit secret.
# Never fall back to an unprotected dashboard if secrets are missing.
import hmac
try:
    _test_password = st.secrets.get('DASHBOARD_TEST_PASSWORD', '')
except Exception:
    _test_password = ''
if not isinstance(_test_password, str) or len(_test_password) < 12:
    st.error('Test dashboard locked: configure DASHBOARD_TEST_PASSWORD (12+ characters) in Streamlit Secrets.')
    st.stop()
if not st.session_state.get('test_authenticated', False):
    st.title('BTC / ETH Test Dashboard')
    with st.form('test_login'):
        _entered = st.text_input('Test dashboard password', type='password')
        _submit = st.form_submit_button('Unlock test dashboard')
    if _submit:
        if hmac.compare_digest(_entered, _test_password):
            st.session_state['test_authenticated'] = True
            st.rerun()
        else:
            st.error('Incorrect password.')
    st.stop()
if st.button('Lock test dashboard'):
    st.session_state['test_authenticated'] = False
    st.rerun()
st.title('BTC / ETH Watch')
st.error('NO TRADE LOCKED · Automated trading OFF · Live signals OFF · Notifications OFF')
st.caption('Exchange observations, not trading advice. Missing inputs never mean safe.')
page = st.selectbox('View', ['Markets & risk', 'Economic calendar', 'Research', 'Notification tests'])
asset = st.radio('Asset', ['BTC', 'ETH'], horizontal=True)
if st.button('Refresh verified sources'):
    st.cache_data.clear()

@st.cache_data(ttl=60)
def snapshot(symbol):
    return fetch(symbol, max_age=180)

@st.cache_data(ttl=300)
def calendar():
    return fetch_calendar()

@st.fragment(run_every='60s')
def render():
    now = datetime.now(timezone.utc); ms = int(now.timestamp()*1000)
    if page == 'Notification tests':
        st.subheader('Android notification preparation')
        st.info('Simulation only. No push delivery, permission request, subscriptions or background alerts.')
        kind = st.selectbox('Demo category', NOTIFICATION_KINDS)
        if st.button('Preview test notification'):
            payload = demo_notification(kind)
            st.success(payload['title']); st.write(payload['body']); st.json(payload)
        st.caption('Android Web Push requires HTTPS, a service worker, consent and a reviewed delivery backend. All remain disabled.')
        return
    if page == 'Research':
        st.subheader('Archived research · NO TRADE')
        direction = st.radio('Direction', ['LONG', 'SHORT'], horizontal=True)
        horizon = st.radio('Trading horizon', ['SCALP', 'DAY TRADE'], horizontal=True)
        rows = research_rows(asset, direction, horizon)
        st.warning('Historical experiments, not live opportunities. Final test week has already been inspected; small samples do not establish profitability.')
        for row in rows:
            with st.expander(row['strategy'], expanded=row['strategy']=='baseline_unchanged'):
                st.write(f"{row['start']} → {row['end_exclusive']} (UTC)")
                for label, key in [('Trades','trade_count'),('Win rate %','win_rate_pct'),('Profit factor','profit_factor'),('Net expectancy USD','expectancy_usd'),('Drawdown %','maximum_drawdown_pct'),('Timeout %','timeout_fraction_pct')]:
                    st.write(f'{label}: {row[key]}')
        if not rows: st.warning('Research records unavailable for this selection.')
        st.caption('Costs: published base scenario includes fees, slippage and funding. See confirmation-v1 report for assumptions and walk-forward results. Original missing backtest ledger is not reproduced.')
        return
    with st.spinner('Retrieving public sources…'):
        cal = calendar()
    macro = evaluate(cal, rules=CalendarRules())
    if page == 'Economic calendar':
        st.subheader('Economic announcements')
        st.warning('Calendar safety: ' + macro['reason_code'] + '. Coverage is partial; an empty list is not an all-clear.')
        region = st.selectbox('Region', ['USA','Europe','UK','Japan','China'])
        aliases = {'USA':('US','USA'), 'Europe':('EUROPE','EU','Europe','Eurozone','Germany'), 'UK':('UK',), 'Japan':('Japan',), 'China':('China',)}
        events = [e for e in macro['events'] if (e.get('region') in aliases[region] or (region == 'Japan' and e.get('kind') in ('BOJ','UEDA_SPEECH')) or (region == 'China' and e.get('kind') in ('CHINA_PMI','CHINA_GDP','PBOC')))]
        for event in events:
            with st.container(border=True):
                st.write(event.get('title','Unknown event'))
                st.write(event.get('colombia_start',event.get('start_utc','Time unavailable')))
                st.caption(f"Importance: {event.get('importance','Unavailable')} · timing verified: {event.get('timing_verified',False)}")
                st.write(event.get('source','Source unavailable'))
        if not events: st.warning('No announcements returned in this horizon. Coverage unavailable or incomplete; no safe condition inferred.')
        st.caption('Displayed times: America/Bogota. Calendar refresh 5 min; evaluation every minute while active.')
        with st.expander('Coverage gaps'): st.write(macro['missing'])
        return
    with st.spinner('Retrieving '+asset+' observations…'):
        data = dict(snapshot(asset+'USD'), macro_calendar=cal)
    now = datetime.now(timezone.utc); ms = int(now.timestamp()*1000)
    risk = assess(data, Rules(), now=now)
    st.subheader(asset + ' · observed risk ' + risk['level'])
    if not macro['clear']:
        st.warning('Macro coverage incomplete or high-risk: ' + macro['reason_code'] + ' — NO TRADE.')
    if risk['missing']:
        st.error('INCOMPLETE — ' + ', '.join(risk['missing']))
    st.caption('LOW / MODERATE / HIGH / EXTREME measure observed thresholds only. Incomplete coverage prevents an all-clear at every level.')
    st.markdown('### Compact market overview · read-only')
    chart_interval = st.radio('Completed spot candles', ['5m', '15m', '1h'], horizontal=True, key='mobile_candle_interval')
    chart_key = {'5m':'scalp_candles', '15m':'fifteen_min_candles', '1h':'candles'}[chart_interval]
    rows = data.get(chart_key, [])
    source = data.get('sources', {}).get(chart_key, {})
    if rows and source:
        # Provider returns [open_ms, open, high, low, close, volume, end_ms].
        # Show completed candles only; never render the in-progress bar.
        completed = [r for r in rows if len(r) >= 7 and r[6] < ms]
        if completed:
            frame = pd.DataFrame(completed, columns=['time','open','high','low','close','volume','end_ms'])
            frame['time'] = pd.to_datetime(frame['time'], unit='ms', utc=True)
            fig = go.Figure(go.Candlestick(x=frame['time'], open=frame['open'], high=frame['high'],
                                           low=frame['low'], close=frame['close'], name='Spot'))
            fig.update_layout(height=350, margin=dict(l=4,r=4,t=10,b=5),
                              xaxis_rangeslider_visible=False, yaxis_title='USD')
            st.plotly_chart(fig, use_container_width=True, key='mobile_spot_chart')
            with st.expander('Spot candle volume'):
                st.bar_chart(frame.set_index('time')['volume'])
            st.caption(f"Completed {chart_interval} spot candles · {source.get('provider', 'Unknown')} · {source.get('instrument', 'Unknown')}. Not perpetual contract price or a signal.")
        else:
            st.warning('No completed candles available; chart withheld.')
    else:
        st.warning(f'{chart_interval} spot candles unavailable or stale. No chart inferred.')
    oi = data.get('oi_changes', {})
    if isinstance(oi, dict):
        with st.expander('Verified open-interest changes'):
            for window in ('5m','15m','1h','24h'):
                value = oi.get(window)
                if isinstance(value, dict) and value.get('change_pct') is not None:
                    st.write(f"{window}: {value['change_pct']:+.3f}%")
                else:
                    st.write(f'{window}: UNAVAILABLE / unverified')
    st.caption('OI and spot candles may come from different venues. No live entries, alerts or trade execution.')
    for key, field, label in [('ticker','lastPrice','Spot price USD'),('interest','openInterest','Open interest'),('funding','lastFundingRate','Funding')]:
        value = fresh_value(data,key,field,ms)
        item = data.get(key,{})
        if value is None:
            st.metric(label, 'UNAVAILABLE'); st.warning(label+': missing, stale or invalid source timestamp.')
        else:
            suffix = ' '+item.get('unit','') if key=='interest' else ''
            display = f'{value*100:.5f}% / {item.get("period_hours","unknown")}h' if key=='funding' else f'{value:,.2f}{suffix}'
            st.metric(label, display)
        source = data.get('sources',{}).get(key,{})
        st.caption(f"{source.get('provider','Source unavailable')} · {source.get('instrument','Contract unavailable')} · source timestamp ms: {source.get('source_time_ms','Unavailable')}")
    for key,label in [('cvd','CVD / buying and selling pressure'),('liquidations','Observed executed liquidation pressure')]:
        st.subheader(label)
        result = risk.get('context',{}).get(key)
        if result:
            item = data[key]
            st.write(f"{result['value']:+,.6f} {item['unit']} · {item['provider']} / {item['instrument']}")
            if key=='cvd': st.write(f"Buy: {result.get('buy_volume','Unavailable')} · Sell: {result.get('sell_volume','Unavailable')}")
            st.caption(f"Window UTC ms {item['start_ms']}–{item['end_ms']}. Exchange-specific; not whole-market pressure or future liquidation levels.")
        else: st.warning('UNAVAILABLE or stale — no safe condition inferred.')
    st.subheader('Independent early warnings')
    for name, message in warnings(data,ms).items():
        st.write(f'**{name}**: {message}')
    with st.expander('Freshness, gaps and provenance'):
        st.write('Retrieved: '+data['retrieved_at'].isoformat()); st.write('Evaluated: '+now.isoformat())
        st.json(data.get('sources',{})); st.json(data.get('errors',{}))
    st.caption('Refresh every 60 seconds while active. No continuous background collection. Exchange flows and global calendar coverage remain incomplete.')

render()
