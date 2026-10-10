from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from market import fetch
from analysis import Rules, assess, plan

st.set_page_config(page_title='BTC & ETH Early Warning', page_icon='⚠️', layout='wide')
st.title('BTC & ETH Early Warning')
st.caption('Informational research only • No trades • Single-exchange coverage • Heuristics, not predictions')
st.warning('Liquidation heatmaps, exchange net flows and an automatic macro calendar are unavailable. Missing context is never treated as safe.')
with st.sidebar:
    st.header('Transparent rules')
    move = st.number_input('24h absolute move threshold (%)', min_value=0.1, value=4.0)
    funding = st.number_input('Absolute funding threshold (%)', min_value=0.001, value=0.03, format='%.3f')
    oi = st.number_input('OI growth threshold (%)', min_value=0.1, value=10.0)
    stale = st.number_input('Maximum snapshot age (seconds)', min_value=30, value=180)
    macro_clear = st.checkbox('I reviewed upcoming macro events for my trading horizon', value=False)
    st.caption('Manually check FOMC, CPI, payrolls and central bank speeches on Federal Reserve, BLS and ECB calendars. This checkbox does not supply or verify calendar data.')
    st.markdown('[Federal Reserve calendar](https://www.federalreserve.gov/newsevents/calendar.htm) · [BLS releases](https://www.bls.gov/schedule/news_release/)')
    st.write('Score: move +2, funding +2, OI growth +2, bearish structure +1. LOW 0–1; MODERATE 2–3; HIGH 4–5; EXTREME 6–7. Missing data blocks ENTER independently of score.')
    if st.button('Retrieve fresh data'):
        st.cache_data.clear()

@st.cache_data(ttl=60)
def snapshot(symbol):
    return fetch(symbol)

@st.fragment(run_every='60s')
def dashboard():
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        data = snapshot(symbol)
        risk = assess(data, Rules(move, funding, oi, int(stale)))
        st.subheader(symbol.replace('USDT', ' / USDT'))
        st.caption(f"Retrieved {data['retrieved_at'].isoformat()} • UI evaluated {datetime.now(timezone.utc).isoformat()} • UTC • refresh every 60s while this page is active")
        st.write(f"Risk: **{risk['level']}** — score {risk['score']}/7 — {'INCOMPLETE' if risk['missing'] else 'core inputs available'}")
        st.write('; '.join(risk['reasons']) or 'No configured threshold triggered in available inputs.')
        if risk['missing']:
            st.error('Missing/stale inputs: ' + ', '.join(risk['missing']))
        def current(key):
            return {} if 'stale retrieval' in risk['missing'] or f'stale {key}' in risk['missing'] else data.get(key, {})
        ticker, interest, funding_data = current('ticker'), current('interest'), current('funding')
        cols = st.columns(3)
        cols[0].metric('Spot price (USDT)', f"{float(ticker['lastPrice']):,.2f}" if ticker else 'Unavailable / stale', f"{float(ticker['priceChangePercent']):+.2f}% / 24h" if ticker else None)
        cols[1].metric('24h spot quote volume (USDT)', f"{float(ticker['quoteVolume']):,.0f}" if ticker else 'Unavailable / stale')
        cols[2].metric('Perpetual OI (base asset)', f"{float(interest['openInterest']):,.2f}" if interest else 'Unavailable / stale')
        st.write('Latest funding rate: ' + (f"{float(funding_data['lastFundingRate']) * 100:.4f}%" if funding_data else 'Unavailable / stale'))
        st.write('OI change over returned hourly history: ' + (f"{risk['oi_change']:+.2f}%" if risk['oi_change'] is not None and 'stale interest history' not in risk['missing'] and 'stale retrieval' not in risk['missing'] else 'Unavailable / stale'))
        structure = 'Unavailable / stale' if 'stale candles' in risk['missing'] or 'stale retrieval' in risk['missing'] else risk['structure']
        st.write('Hourly market structure: **' + structure + '** (comparison of two completed 20-hour ranges)')
        trades = [] if 'stale order flow' in risk['missing'] or 'stale retrieval' in risk['missing'] else data.get('trades', [])
        if trades:
            delta = sum(float(t['q']) * (-1 if t['m'] else 1) for t in trades)
            start, end = [datetime.fromtimestamp(int(t['T']) / 1000, timezone.utc).isoformat() for t in (trades[0], trades[-1])]
            st.write(f'Sampled spot taker flow delta: **{delta:+,.3f} base units**, {len(trades)} aggregate trades, {start} to {end}.')
            st.caption('Buy taker minus sell taker volume, classified by buyer-is-maker flag. This limited sample is an order-flow proxy, not full-session or cross-exchange CVD.')
        else:
            st.write('Sampled taker flow: Unavailable or stale')
        st.caption('CVD: UNAVAILABLE — no complete cumulative volume delta feed integrated.')
        rows = [] if 'stale candles' in risk['missing'] or 'stale retrieval' in risk['missing'] else data.get('candles', [])
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
        st.info('Liquidation heatmap: UNAVAILABLE — no verified free historical liquidation-level provider integrated. Exchange inflow/outflow: UNAVAILABLE — no reliable free exchange-labelled on-chain feed integrated. These are not estimated from price or volume.')
        with st.expander('Source diagnostics and timestamps'):
            st.write('Spot: api.binance.com; USDT perpetuals: fapi.binance.com. Regional restrictions may block either source. There is no synthetic fallback.')
            st.json({key: value for key, value in data['errors'].items()})
            st.json(data.get('source_failures', {}))
            st.json({'source_retrieved_at_utc': data.get('source_retrieved_at', {}),
                     'spot_close_ms': data.get('ticker', {}).get('closeTime'),
                     'funding_time_ms': data.get('funding', {}).get('time'),
                     'oi_time_ms': data.get('interest', {}).get('time')})
    st.caption('No background alerts, notifications, scheduled monitoring or trading execution are implemented. Refresh stops when the session is inactive.')

dashboard()
