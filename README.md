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

Kraken ticker `o` is UTC-day open, not rolling 24h open. If Coinbase is unavailable, Kraken price and volume still work, but rolling 24h change is explicitly unavailable and blocks ENTER. Kraken Futures public minute OI analytics now supplies compatible historical OI for both linear perpetuals. Only completed bar closes are used, alongside the current same-contract snapshot. No suitable free Deribit OI history endpoint was verified. Each fresh selected OI snapshot is therefore also persisted locally, providing a fallback when Kraken history fails or Deribit is selected. No historical points are invented or inferred from spot volume.

Freshness is checked during provider selection and again on every UI evaluation, including cached snapshots. Spot timestamps are latest-trade times, derivative timestamps are server snapshot times, and completed-candle end times are derived from provider candle boundaries. The UI explicitly notes that volume, OI and funding do not have separate observation timestamps. A recent server snapshot is not proof of each field's individual update time. Candles must have enough contiguous completed bars and a latest close within two intervals; current ticker/funding/OI/trades use the configured age limit (180 seconds by default). Unknown source timestamps and future times beyond five seconds block ENTER.

OI changes are shown over 15 minutes, 1 hour and 4 hours, plus the original 24-hour risk lookback. The sidebar defaults to requiring 24h OI coverage; selecting 4h is an explicit change to the required risk horizon, with the same score weights and risk levels. Missing/stale/unverified required OI coverage keeps NO TRADE even when shorter windows are ready. Each change uses the nearest real baseline at or within 90 seconds before the target, reports actual start/end timestamps, and rejects gaps over 180 seconds, zero baselines, incompatible units/contracts, conflicting duplicates and non-finite values. No interpolation is performed. Raw observations are revalidated on each risk assessment; a cached change summary cannot bypass the gate.

Persistent snapshots use SQLite at `data/oi_snapshots.sqlite3`, or the path set by `OI_HISTORY_DB_PATH`. The database is excluded from Git. It stores provider, contract, native units, source timestamp, receipt timestamp, OI value and timestamp type. Source timestamp deduplication prevents repeated/cached data from falsely advancing coverage; original values are immutable. Transactions and WAL allow multiple dashboard sessions to share the store. Corrupt/unwritable storage is reported and never silently reset; verified remote history can still work without storage. Histories are never combined across providers or contracts, and provider fallback may need to warm up its own series. Stored data survives process restarts on the same disk; retaining it across environment replacement requires a persistent filesystem. No automatic pruning or synthetic backfill is performed.

Snapshot collection happens only on cache-miss refreshes of an active page or explicit data checks. There is no background collector or scheduled monitoring. After inactive periods, gaps can invalidate windows until sufficient continuous observations accumulate. Kraken history normally avoids this local warm-up; local fallback needs at least 15 minutes/1 hour/4 hours for those displays, and 24 hours for the default risk window, with acceptable baseline timing and coverage.

Active sessions refresh every 60 seconds with a 60-second cache. This is session refresh, not a background monitoring or alert service. No notifications are implemented.

Risk scoring is configurable: absolute 24h change above threshold +2; absolute funding above threshold +2; OI growth above threshold +2; lower highs and lows across two completed 20-hour ranges +1. LOW 0–1, MODERATE 2–3, HIGH 4–5, EXTREME 6–7. LOW describes observed indicators, not safety. Missing/stale required inputs block ENTER.

SCALP uses completed 5-minute candles; DAY TRADE uses completed hourly candles. A close beyond the previous 20-bar range and volume above 1.2 times its average confirms a directional breakout. Opposite range edge is invalidation; targets are one and two times reference-entry-to-invalidation distance. These historical reference levels omit fees, spread, slippage and execution guarantees. HIGH/EXTREME, missing data, stale signal candles or an unchecked macro review produce NO TRADE; otherwise unconfirmed setups WAIT. ENTER is informational, never an order.

CVD, liquidation heatmaps and exchange-labelled inflow/outflow are unavailable, rather than inferred from unrelated metrics. An automated macro feed is not integrated. Review official Federal Reserve/BLS calendars manually; the review checkbox only records your acknowledgement. Even when core inputs are complete, these context gaps remain visible.

## Validation

Unit tests cover provider outages/fallback, timestamps, malformed data, units/periods, candle gaps, risk scoring, missing/stale input protection, macro gating, confirmed breakouts and exclusion of incomplete candles. Streamlit AppTest checks populated and unavailable dashboards.

Run read-only live primary and fallback checks:

```bash
.venv/bin/python scripts/check_public_apis.py --history-db /tmp/btc-eth-oi-check.sqlite3 --output /tmp/btc-eth-live-check.json
```

The script uses real API responses. In fallback modes, primary outages are deliberately simulated; every secondary response is real. Output records actual HTTP status, request parameters, source timestamps, missing indicators, risk and panel signals. It exits nonzero if implemented live inputs or normal Kraken OI windows fail, or if missing required data permits a trade signal. Deribit/local history warm-up is expected and must remain NO TRADE. The live check database contains only real newly collected snapshots, so it does not pretend a multi-hour persistence soak has completed. This checks individual GET requests, not sustained uptime or trading execution. Live API connectivity and UI rendering must be checked in each deployment; public API availability is not guaranteed. Android layout uses Streamlit's responsive components; physical-device testing is still required.

See [OI history investigation and validation](docs/oi-history-validation.md) for tested endpoints, live results and persistence limits.
