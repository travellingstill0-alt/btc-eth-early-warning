"""Compact, read-only BTC/ETH research surface. Unverified inputs fail closed."""
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from market import fetch
from analysis import assess, Rules
from macro_calendar import fetch_calendar, evaluate as evaluate_calendar
from oi_history import calculate_changes

def _fmt(value, suffix="", digits=2):
    try:
        return f"{float(value):,.{digits}f}{suffix}" if value is not None else "UNAVAILABLE"
    except (TypeError, ValueError, OverflowError):
        return "UNAVAILABLE"

def _candles(rows, seconds):
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    finished = [r for r in rows if int(r[6]) < now_ms]
    if seconds == 900:
        # Only aggregate contiguous completed 5-minute candles.
        groups = {}
        for r in finished:
            bucket = int(r[0]) // 900000
            groups.setdefault(bucket, []).append(r)
        out = []
        for bucket, group in sorted(groups.items()):
            group.sort(key=lambda x: x[0])
            if len(group) != 3 or [int(x[0]) for x in group] != [bucket*900000+i*300000 for i in range(3)]:
                continue
            out.append([group[0][0], group[0][1], max(x[2] for x in group),
                        min(x[3] for x in group), group[-1][4], sum(x[5] for x in group),
                        group[-1][6]])
        return out
    return finished

def _chart(rows):
    if not rows:
        st.warning("Candlesticks UNAVAILABLE — no verified completed bars.")
        return
    frame = pd.DataFrame([{"time": pd.to_datetime(r[0], unit="ms", utc=True).isoformat(),
                           "open":float(r[1]), "high":float(r[2]), "low":float(r[3]),
                           "close":float(r[4]), "up":float(r[4])>=float(r[1])} for r in rows[-80:]])
    spec = {"height":245,"data":{"values":frame.to_dict("records")},
            "encoding":{"x":{"field":"time","type":"temporal","title":None}},
            "layer":[
                {"mark":{"type":"rule"},"encoding":{"y":{"field":"low","type":"quantitative","scale":{"zero":False},"title":"USD"},"y2":{"field":"high"},"color":{"field":"up","type":"nominal","legend":None,"scale":{"domain":[True,False],"range":["#20a878","#e05a64"]}}}},
                {"mark":{"type":"bar","size":5},"encoding":{"y":{"field":"open","type":"quantitative","scale":{"zero":False}},"y2":{"field":"close"},"color":{"field":"up","type":"nominal","legend":None,"scale":{"domain":[True,False],"range":["#20a878","#e05a64"]}}}}
            ]}
    st.vega_lite_chart(spec, use_container_width=True)

def _levels(rows):
    closed = _candles(rows, 3600)
    if len(closed) < 20:
        return None, None
    sample = closed[-20:]
    return min(float(x[3]) for x in sample), max(float(x[2]) for x in sample)

@st.cache_data(ttl=60)
def _market(symbol):
    return fetch(symbol)

@st.cache_data(ttl=300)
def _macro():
    return fetch_calendar()

def render():
    st.set_page_config(page_title="BTC / ETH Watch", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    st.markdown("""<style>
      .block-container{padding:0.65rem 0.7rem 2rem;max-width:1100px}
      h1{font-size:1.45rem!important;margin-bottom:0.15rem!important}
      h3{font-size:1.02rem!important;margin-top:0.6rem!important}
      [data-testid="stMetricValue"]{font-size:1.05rem}
      [data-testid="stVerticalBlock"]{gap:.32rem}
      @media(max-width:640px){[data-testid="stHorizontalBlock"]{gap:.3rem}}
    </style>""",unsafe_allow_html=True)
    st.title("BTC / ETH Watch")
    st.caption("READ-ONLY • no execution • no inferred future liquidation heatmap • UTC source timestamps")
    a,b,c=st.columns([2,2,1])
    asset=a.selectbox("Market",["BTC","ETH"],label_visibility="collapsed")
    timeframe=b.selectbox("Candles",["5m","15m","1h"],label_visibility="collapsed")
    if c.button("↻",help="Refresh verified sources"):
        st.cache_data.clear()
        st.rerun()
    symbol=asset+"USD"
    try:
        data=_market(symbol)
    except Exception as exc:
        st.error("NO TRADE — market source unavailable. "+type(exc).__name__)
        return
    try:
        calendar=_macro()
        macro=evaluate_calendar(calendar)
    except Exception:
        calendar=None
        macro={"missing":["macro calendar unavailable"],"high_risk":[],"clear":False}
    data=dict(data,macro_calendar=calendar)
    try:
        risk=assess(data,Rules())
    except Exception:
        risk={"level":"UNKNOWN","score":None,"missing":["risk assessment failed"],"oi_changes":{},"reasons":[]}
    missing=list(risk.get("missing",[]))+list(macro.get("missing",[]))
    if not macro.get("clear",False):
        missing.append("macro verification incomplete")
    # No live execution or directional signals. A real liquidation-price buffer
    # needs user-specific leverage/margin/position details, which are not collected.
    st.error("DECISION: NO TRADE  |  LONG: DISABLED  |  SHORT: DISABLED  |  WAIT: research only")
    level=risk.get("overall_level",risk.get("level","UNKNOWN"))
    if missing and level not in ("HIGH","EXTREME"):
        level="INCOMPLETE"
    st.write("**Early Warning:** "+str(level)+"  ·  **Data:** "+("INCOMPLETE" if missing else "verified inputs only"))
    if macro.get("high_risk"):
        st.error("Verified macro warning: "+"; ".join(map(str,macro["high_risk"])))
    if missing:
        st.warning("Missing / stale / unverified: "+", ".join(sorted(set(map(str,missing)))))
    st.caption("Entry confirmation: closed candle + volume + verified OI/CVD + macro clearance required. Not confirmed.")
    st.caption("TP1 / TP2 / TP3: UNAVAILABLE (no verified entry). SL invalidation: UNAVAILABLE. SL→liquidation-price buffer: UNAVAILABLE (requires actual position, leverage, margin and exchange liquidation price).")
    ticker=data.get("ticker") or {}
    fund=data.get("funding") or {}
    interest=data.get("interest") or {}
    m1,m2,m3=st.columns(3)
    m1.metric("Spot USD",_fmt(ticker.get("lastPrice")))
    m2.metric("Funding",_fmt(float(fund["lastFundingRate"])*100,"%",5) if "lastFundingRate" in fund else "UNAVAILABLE")
    m3.metric("Funding period",str(fund.get("period_hours","?"))+"h" if fund else "UNAVAILABLE")
    st.caption("Price / funding: "+", ".join(f"{k}: {v.get('provider','?')} @ {datetime.fromtimestamp(v['source_time_ms']/1000,timezone.utc).isoformat()}" for k,v in data.get("sources",{}).items() if k in ("ticker","funding") and v.get("source_time_ms")))
    st.markdown("### 1 · Verified candlesticks")
    sec={"5m":300,"15m":900,"1h":3600}[timeframe]
    rows=data.get("candles" if sec==3600 else "scalp_candles") or []
    _chart(_candles(rows,sec))
    st.markdown("### 2 · Open interest")
    st.caption(f"Current {interest.get('unit','unknown units')}: {_fmt(interest.get('openInterest'))}. Contract/provider histories are not mixed.")
    changes=risk.get("oi_changes") or calculate_changes(data,int(datetime.now(timezone.utc).timestamp()*1000),180)
    cols=st.columns(4)
    for col,window in zip(cols,("5m","15m","1h","24h")):
        item=changes.get(window) or {}
        col.metric(window,_fmt(item.get("change_pct"),"%"))
    history=data.get("interest_history") or []
    if len(history)>=2:
        try:
            frame=pd.DataFrame([{"UTC":pd.to_datetime(x["timestamp"],unit="ms",utc=True),"OI":float(x["sumOpenInterest"])} for x in history])
            st.line_chart(frame.set_index("UTC"),height=105)
        except (KeyError,TypeError,ValueError):
            st.caption("Historical OI trend UNAVAILABLE — incompatible observation format.")
    else:
        st.caption("Historical OI trend UNAVAILABLE — insufficient verified observations.")
    st.markdown("### 3 · CVD (executed perpetual trades)")
    cvd=data.get("cvd")
    st.write("15m: "+(_fmt(risk.get("context",{}).get("cvd",{}).get("value")," "+cvd.get("unit","")) if isinstance(cvd,dict) and risk.get("context",{}).get("cvd",{}).get("value") is not None else "UNAVAILABLE"))
    st.caption("5m: UNAVAILABLE unless independently verified 5-minute trade coverage exists. 15m and 5m must never be inferred from sampled spot trades.")
    st.markdown("### 4 · Liquidation clusters")
    st.warning("Future liquidation heatmap ABOVE / BELOW: UNAVAILABLE — executed liquidations are not predictive clusters.")
    st.markdown("### 5 · Support / resistance (price structure, NOT liquidation zones)")
    support,resistance=_levels(data.get("candles") or [])
    x,y=st.columns(2)
    x.metric("20 closed 1h bars · support",_fmt(support))
    y.metric("20 closed 1h bars · resistance",_fmt(resistance))
    st.caption("Historical 20-hour high/low references, not verified order-book support, liquidation pools, or entry recommendations.")
    st.markdown("### 6 · Observed risk & 7 · Source integrity")
    st.write("Observed: **"+str(risk.get("observed_level",risk.get("level","UNKNOWN")))+"** · Overall: **"+str(level)+"**")
    st.caption("Risk is a heuristic, not a probability or assurance of safety. Missing essential inputs block trading decisions.")
    with st.expander("Source timestamps / unavailable inputs / legacy dashboard"):
        for key,source in data.get("sources",{}).items():
            st.write(f"{key}: {source.get('provider','?')} / {source.get('instrument','?')} / {source.get('source_time_ms','no timestamp')}")
        for key,value in data.get("errors",{}).items():
            st.write(f"{key}: {value}")
        st.write("Exchange flows: "+str(data.get("exchange_flow_diagnostics",{}).get("reason","UNAVAILABLE")))
        st.caption("Legacy full dashboard: add ?legacy=1 to this page URL.")
    st.caption("Automated trading OFF · Live execution OFF · No background alerts")
