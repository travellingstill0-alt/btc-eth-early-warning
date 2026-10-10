# BTC & ETH Early Warning

A mobile-friendly Streamlit research dashboard. No trading operations, credentials, paid data, or background alerts.

## Run

Python 3.10+ (tested with 3.12):

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open the forwarded port 8501 in your development platform. On your own computer, open http://localhost:8501. Android Chrome can use the same accessible deployment URL or your computer's LAN address on a trusted network. Do not expose an unsecured development server to the public internet. This cloud onboarding interface does not provide a localhost preview link.

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Data and behavior

Public USD spot prices, rolling 24h change and base-asset volume use Coinbase, falling back to Kraken. Kraken supplies hourly/five-minute candles and sampled taker flow, falling back to Coinbase. Public Kraken Futures linear perpetuals (`PF_XBTUSD`, `PF_ETHUSD`) supply current open interest and hourly relative funding; Deribit BTC/ETH perpetual tickers are the fallback. Each indicator selects its own provider and reports failed attempts, HTTP status, source, instrument, timestamp type and retrieval time. Failed, malformed, non-finite, stale or future observations trigger fallback; no mock data enters the dashboard.

Spot volume is displayed in BTC/ETH, not estimated USD quote volume. Kraken OI is displayed in base units; Deribit inverse perpetual OI is displayed in USD. Values from these different instruments are never spliced into OI history. Kraken `relativeFundingRate` is shown for one hour and Deribit `funding_8h` for eight hours. The configurable funding threshold retains its eight-hour basis; hourly rates are compared against one eighth of that threshold. This is a threshold adjustment, not a fabricated eight-hour funding observation.

Kraken ticker `o` is UTC-day open, not rolling 24h open. If Coinbase is unavailable, Kraken price and volume still work, but rolling 24h change is explicitly unavailable and blocks ENTER. Verified ticker endpoints supply current OI but not comparable hourly OI history: OI growth is unavailable and both panels remain NO TRADE. No historical points are invented or inferred from spot volume. This limitation is intentional until a verified OI history provider is integrated.

Freshness is checked during provider selection and again on every UI evaluation, including cached snapshots. Spot timestamps are latest-trade times, derivative timestamps are server snapshot times, and completed-candle end times are derived from provider candle boundaries. The UI explicitly notes that volume, OI and funding do not have separate observation timestamps. A recent server snapshot is not proof of each field's individual update time. Candles must have enough contiguous completed bars and a latest close within two intervals; current ticker/funding/OI/trades use the configured age limit (180 seconds by default). Unknown source timestamps and future times beyond five seconds block ENTER.

Active sessions refresh every 60 seconds with a 60-second cache. This is session refresh, not a background monitoring or alert service. No notifications are implemented.

Risk scoring is configurable: absolute 24h change above threshold +2; absolute funding above threshold +2; OI growth above threshold +2; lower highs and lows across two completed 20-hour ranges +1. LOW 0–1, MODERATE 2–3, HIGH 4–5, EXTREME 6–7. LOW describes observed indicators, not safety. Missing/stale required inputs block ENTER.

SCALP uses completed 5-minute candles; DAY TRADE uses completed hourly candles. A close beyond the previous 20-bar range and volume above 1.2 times its average confirms a directional breakout. Opposite range edge is invalidation; targets are one and two times reference-entry-to-invalidation distance. These historical reference levels omit fees, spread, slippage and execution guarantees. HIGH/EXTREME, missing data, stale signal candles or an unchecked macro review produce NO TRADE; otherwise unconfirmed setups WAIT. ENTER is informational, never an order.

CVD, liquidation heatmaps and exchange-labelled inflow/outflow are unavailable, rather than inferred from unrelated metrics. An automated macro feed is not integrated. Review official Federal Reserve/BLS calendars manually; the review checkbox only records your acknowledgement. Even when core inputs are complete, these context gaps remain visible.

## Validation

Unit tests cover provider outages/fallback, timestamps, malformed data, units/periods, candle gaps, risk scoring, missing/stale input protection, macro gating, confirmed breakouts and exclusion of incomplete candles. Streamlit AppTest checks populated and unavailable dashboards.

Run read-only live primary and fallback checks:

```bash
.venv/bin/python scripts/check_public_apis.py --output /tmp/btc-eth-live-check.json
```

The script uses real API responses. In fallback modes, primary outages are deliberately simulated; every secondary response is real. Output records actual HTTP status, request parameters, source timestamps, missing indicators, risk and panel signals. It exits nonzero if an implemented input fails; the explicitly unavailable OI history is excluded from that connectivity exit check. This checks individual GET requests, not sustained uptime or trading execution. Live API connectivity and UI rendering must be checked in each deployment; public API availability is not guaranteed. Android layout uses Streamlit's responsive components; physical-device testing is still required.
