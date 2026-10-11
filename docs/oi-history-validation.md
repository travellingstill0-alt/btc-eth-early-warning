# OI history investigation and validation

Built from `feature/public-provider-fallback` (`a8ec8bb`) on `feature/persistent-oi-history`. Investigated and tested on 2026-10-10. The existing restricted network policy was retained and requests used the inherited HTTPS proxy with TLS verification. No credentials, deployment, collector daemon or trading calls.

## Endpoint findings

| Provider / endpoint | Actual response | Result |
|---|---|---|
| Kraken `/api/charts/v1/analytics/PF_XBTUSD/open-interest` | HTTP 200 | BTC native-unit OI OHLC arrays with timestamps |
| Kraken `/api/charts/v1/analytics/PF_ETHUSD/open-interest` | HTTP 200 | ETH native-unit OI OHLC arrays with timestamps |
| Deribit `/api/v2/public/get_open_interest_history`, BTC/ETH perpetuals | HTTP 400, JSON-RPC -32601 “Method not found” | Candidate method is unavailable |
| Deribit `/api/v2/public/get_tradingview_chart_data`, BTC/ETH perpetuals | HTTP 200 | Price OHLC, volume and cost arrays; no OI field |

Kraken host is `https://futures.kraken.com`. Use `interval=60` (seconds) and `since=<Unix seconds>`; a six-hour `since` request returned approximately 360 minute bars. A one-hour interval returned hourly bars; an invalid interval returned HTTP 400 naming the interval argument. The initial `from`/`to` query did not narrow the result, so it is not used. The implementation requests 24h plus a four-minute margin using the verified `since` parameter, which fits within the observed 2,000-row limit. The API supplies parallel `timestamp` and four-value `data` arrays; `more` was false in the tested responses.

Timestamps identify bar starts; the current minute row changes during the minute and matched contemporaneous ticker OI. Only completed minute OHLC closes are used, at derived end-of-minute boundaries, excluding any close later than the selected live snapshot. BTC and ETH analytics values matched current same-contract ticker OI in base units. No active bar is treated as a completed observation. No suitable free Deribit OI history was verified; the tested chart method is not substituted for OI.

## Real integrated checks

Command: `.venv/bin/python scripts/check_public_apis.py --history-db /tmp/oi-live-check.sqlite3 --output /tmp/oi-live-check.json`.

The recorded run exited 0. Every actual non-simulated provider request returned HTTP 200. Fallback modes explicitly simulated primary transport failures; all secondary observations and saved snapshots were real. Numeric results below are point-in-time measurements, not fixed expectations.

| Asset | UTC checked | 15m OI | 1h OI | 4h OI | 24h OI | OI snapshot age at evaluation |
|---|---|---|---|---|---|---|
| BTCUSD | 2026-10-10T18:43:04.017224+00:00 | +0.0229% | +0.5517% | -0.3453% | -1.5703% | 0.86s |
| ETHUSD | 2026-10-10T18:43:05.860580+00:00 | -0.0826% | +0.0588% | +0.0290% | -0.0527% | 0.74s |

Normal Kraken history satisfied all required data checks. With the live-check script’s simulated manual macro acknowledgement, both panels returned WAIT at the tested prices. The actual UI default leaves macro review unchecked, so live Streamlit AppTest displayed NO TRADE for all four panels. It rendered eight OI-window values, both assets’ metrics and no exceptions or source errors.

Kraken-only spot fallback still lacks rolling 24h price change and returns NO TRADE. Deribit failover starts its own USD-unit snapshot history; it cannot use the Kraken BTC/ETH-unit history. History-only outage mode uses stored Kraken snapshots. Neither local store had 15 minutes or more of real continuous coverage during this session, so all local windows correctly stayed unavailable and both panels returned NO TRADE. The live result does not claim a multi-hour persistence soak; readiness after sufficient coverage is covered by deterministic tests.

## Persistence and safety

- Each selected fresh OI snapshot is stored in SQLite with provider, contract, native unit, source timestamp, receipt timestamp, value and timestamp kind. Provider/contract/unit/source-time form the deduplication key.
- Repeated cached/source timestamps never advance elapsed coverage. Conflicting same-time values are rejected. Transactions and WAL handle concurrent sessions; reconnecting preserves data.
- Only verified provider/contract/unit combinations are supported: Kraken PF_XBTUSD/BTC, PF_ETHUSD/ETH; Deribit BTC-PERPETUAL/USD, ETH-PERPETUAL/USD. No normalization or cross-contract concatenation is performed.
- Each window needs a real positive baseline at or within 90 seconds before its target, an endpoint identical to the fresh selected OI observation, and no internal gap over 180 seconds. Actual timestamps, span and observation count are reported. No interpolation or synthetic backfill occurs.
- Raw history and source identity are revalidated on every assessment, including cached snapshots. Missing/stale/unverified required history blocks ENTER. Cached percentage summaries are not trusted.
- The default OI scoring horizon remains 24h, preserving the prior approximately 24-hour hourly-history risk behavior. The user may explicitly select 4h; thresholds, score weights, risk levels and macro/high-risk gates remain unchanged.
- The default store is `data/oi_snapshots.sqlite3` (ignored by Git). `OI_HISTORY_DB_PATH` selects another file. The same disk must survive process/environment replacement for persistence; no platform durable-volume guarantee is assumed. No automatic pruning is performed.
- Collection happens only on active cache-miss refreshes or explicit checks. Inactive gaps may invalidate local windows. Corrupt/unwritable stores produce warnings and are never reset silently. Verified remote history can still serve the dashboard when persistence fails.

Snapshot source times describe server snapshots, not the unknown individual update times of the OI field. Historical close timestamps are derived interval boundaries. These provenance limits are displayed and do not become fabricated per-field observation times.

## Automated validation

42 tests passed with `.venv/bin/python -m unittest discover -s tests -v`. Coverage includes completed-minute parsing, timestamp/schema validation, 15m/1h/4h/24h warm-up and calculations, restart persistence, duplicate/conflicting values, concurrent writers, gaps and baseline tolerance, corrupted/unwritable stores, provider/contract/unit separation, stale/unverified observations, cached-summary bypass prevention, UI window selection and all prior risk/signal gates. Tests use isolated fixture stores; no test history is injected into live databases.

CVD, liquidation heatmaps, exchange inflow/outflow and automatic macro data remain unavailable. No deployment or automated trading enabled.
