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

Public Binance spot API supplies price, 24h changes, quote volume, hourly/5-minute candles and the most recent 1,000 aggregate trades. USDT perpetual futures API supplies open interest, latest funding and up to 25 hourly OI samples. OI is in base asset units; funding is displayed as percent. Sampled buy-minus-sell taker volume is an order-flow proxy, not complete CVD. Each source fails independently; source errors and timestamps are visible. Binance regional restrictions may prevent live data access. No mock data appears in the dashboard.

Active sessions refresh every 60 seconds with a 60-second cache. This is session refresh, not a background monitoring or alert service. No notifications are implemented.

Risk scoring is configurable: absolute 24h change above threshold +2; absolute funding above threshold +2; OI growth above threshold +2; lower highs and lows across two completed 20-hour ranges +1. LOW 0–1, MODERATE 2–3, HIGH 4–5, EXTREME 6–7. LOW describes observed indicators, not safety. Missing/stale required inputs block ENTER.

SCALP uses completed 5-minute candles; DAY TRADE uses completed hourly candles. A close beyond the previous 20-bar range and volume above 1.2 times its average confirms a directional breakout. Opposite range edge is invalidation; targets are one and two times reference-entry-to-invalidation distance. These historical reference levels omit fees, spread, slippage and execution guarantees. HIGH/EXTREME, missing data, stale signal candles or an unchecked macro review produce NO TRADE; otherwise unconfirmed setups WAIT. ENTER is informational, never an order.

Liquidation heatmaps and exchange-labelled inflow/outflow are unavailable, rather than inferred from unrelated metrics. An automated macro feed is not integrated. Review official Federal Reserve/BLS calendars manually; the review checkbox only records your acknowledgement. Even when core inputs are complete, these context gaps remain visible.

## Validation

Unit tests cover scoring, missing/stale input protection, macro gating, confirmed breakouts and exclusion of incomplete candles. Live API connectivity and UI rendering must be checked in each deployment; public API availability is not guaranteed. Android layout uses Streamlit's responsive components; physical-device testing is still required.

## Live-data verification

Run `python scripts/check_live_apis.py` from the repository root. It makes only public GET requests, validates payloads, prints timestamped per-endpoint results and exits nonzero if required data is missing or stale. It does not trade or deploy.

Responses are validated before use; endpoint failures remain independent. Retrievals run concurrently with 12-second request timeouts and record individual UTC completion timestamps. Stale or excessively future-dated source timestamps block signals, and stale metrics, charts and sampled flow are hidden. No last-good or synthetic fallback is presented as current data. CVD remains explicitly unavailable; sampled taker flow is separately labelled.

The 60-second cache expiry and manual refresh are covered by automated Streamlit tests. The active-browser fragment scheduler still requires verification in the actual hosted environment. See `reports/verification.md` and `reports/live-api-results.json` for this audit's results and limits.

Alternative-provider connectivity can be audited with `python scripts/check_public_providers.py`. It makes direct public GET probes without credentials or redirect following and does not modify the dashboard provider. HTTP JSON success is an observation awaiting instrument, unit and timestamp validation. Proxy allowlist denials and provider HTTP restrictions are distinguished. See `reports/public-provider-verification.md` for current results; no alternate feed is enabled until verified from this environment.

The latest retest is recorded in `reports/latest-provider-retest.md`. Provider probes include a safe local policy snapshot and explicit per-metric availability/freshness status. Diagnostic request times never stand in for market-source timestamps. A published cloud environment configuration must be applied to the environment attached to the task before its new destination access can be verified.
