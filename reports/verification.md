# BTC/ETH dashboard verification

Audit date: October 10, 2026 (America/Bogota). Exact UTC probe timestamps are in live-api-results.json.

## Source

Verified GitHub main and independently fetched origin/main at c16faeb5b522b9bfd5303c3a6dee8e3406604e77. Work is based on that commit. The older original workspace and its uncommitted files were preserved; changes were made in a separate checkout. Main has no hosting manifest or CI/deployment workflow.

## Published environment

No published URL was present in the repository, and Sites discovery returned no owned sites. The user was asked for the published URL. Production version, runtime, browser refresh and production API reachability therefore remain unverified. No deployment or hosting changes were made.

## Actual live connections

For both BTCUSDT and ETHUSDT, every request reached Binance but returned HTTP 451. Binance's response states: "Service unavailable from a restricted location" under its eligibility terms. This is a provider location restriction, not proof of an API outage globally.

| Metric / source | Endpoint | BTC | ETH |
| --- | --- | --- | --- |
| Spot price and 24h USDT quote volume | api.binance.com/api/v3/ticker/24hr | HTTP 451 | HTTP 451 |
| Open interest in base units | fapi.binance.com/fapi/v1/openInterest | HTTP 451 | HTTP 451 |
| Latest funding rate | fapi.binance.com/fapi/v1/premiumIndex | HTTP 451 | HTTP 451 |
| Hourly and 5-minute candles | api.binance.com/api/v3/klines | HTTP 451 | HTTP 451 |
| Sampled aggregate trades | api.binance.com/api/v3/aggTrades | HTTP 451 | HTTP 451 |
| Hourly OI history | fapi.binance.com/futures/data/openInterestHist | HTTP 451 | HTTP 451 |

Usable live data connections: 0 of 14 requests. Price and volume share a single ticker request. No alternative provider was invented or silently substituted, and no location restriction was bypassed.

## Fixes and checks

- Validate schemas, symbols, finite numeric fields, list order and required timestamps before storing payloads. Invalid responses become source errors rather than UI crashes.
- Retrieve independent endpoints concurrently with bounded request timeouts; record per-source UTC completion times and snapshot completion.
- Hide stale metrics, chart data, structure and sampled flow; retain source timestamps in diagnostics. Future-dated core timestamps beyond 30 seconds also block signals.
- Explicitly state CVD is unavailable. Sampled taker delta remains identified as a limited observed trade sample. Liquidation heatmaps and exchange flows remain unavailable.
- All 16 automated unit/Streamlit tests passed: valid and unavailable rendering, scoring, signal safety, invalid payloads, partial failures, future/stale timestamps, cache expiry after 60 seconds (simulated clock), manual refresh and macro gating.
- A separate Streamlit AppTest ran against actual public API calls: no rendering exceptions, six unavailable/stale metrics, two missing-data errors and four NO TRADE results.
- Active-browser periodic fragment execution was inspected in code (60 seconds) but not observed in production. AppTest checks cache/rerun behavior, not a real browser timer.

No orders, trading credentials, notifications, merges or deployments were enabled. Existing ENTER output remains informational only.
