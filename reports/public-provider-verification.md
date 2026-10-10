# Alternative public-provider verification

Audit: October 10, 2026, 12:05–12:06 America/Bogota. Exact UTC request times are preserved in the JSON reports.

## Source and application state

Fetched GitHub main at c16faeb5b522b9bfd5303c3a6dee8e3406604e77. Created fix/public-provider-connectivity from that main and cherry-picked the prior live-data validation change (original 828efe2). The application has not been deployed; publishing the cloud environment did not deploy Streamlit. No production URL is expected. The earlier verification report is historical.

## Connectivity results

All calls were direct unauthenticated public GET requests through the inherited environment proxy, with TLS verification enabled. No paid service, API account, VPN, alternate route, Binance mirror or geographic workaround was used.

| Provider | Requests tested | Observed result | Selection |
| --- | --- | --- | --- |
| Kraken spot | BTC and ETH ticker | Proxy CONNECT denied, HTTP 403 | Not selected |
| Kraken futures | Public futures tickers | Proxy CONNECT denied, HTTP 403 | Not selected |
| Coinbase Exchange | BTC-USD and ETH-USD ticker and stats | Proxy CONNECT denied, HTTP 403 | Not selected |
| Deribit | BTC-PERPETUAL and ETH-PERPETUAL ticker | Proxy CONNECT denied, HTTP 403 | Not selected |
| Binance, rechecked | Both assets, all seven existing source requests each | Provider HTTP 451 | Unavailable |

The nine focused alternative requests did not reach their providers. Network-policy denial is not a provider response and does not establish a geographic restriction or global availability. Initial exploratory probes to OKX market ticker, Bybit linear ticker and CoinGecko ping were also denied by the proxy; no integration decision rests on those probes.

The environment's selected custom hosts were api.binance.com and fapi.binance.com. Alternative market-data hosts are absent from the allowlist. Therefore usable alternate connections verified in this environment: **zero**. No provider was chosen before successful connectivity and data validation.

Raw evidence: public-provider-results.json (nine focused probes), binance-recheck.json (14 Binance probes). Repeat with `python scripts/check_public_providers.py` and `python scripts/check_live_apis.py`. A nonzero exit indicates at least one failed probe; HTTP JSON success in the alternative probe means connectivity only, not validated dashboard suitability.

## Documented candidates and semantic constraints

These are research candidates, not verified live feeds:

- [Kraken spot ticker](https://docs.kraken.com/api-reference/market-data/get-ticker-information): pair-specific last price and volume. Its ticker does not provide a source observation timestamp; a retrieval time must not be passed off as one. Today-open and rolling 24-hour change must not be conflated.
- [Kraken futures tickers](https://docs.kraken.com/api-reference/market-data/get-tickers): contract-level price, volume, OI and funding fields plus server time. Instrument metadata, funding units/period and contract-specific OI units require validation before using existing thresholds. Index and dated-futures rows must not be mistaken for perpetuals.
- [Coinbase Exchange stats](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-stats): price statistics and 24-hour base-asset volume. BTC/ETH-USD are USD pairs, not USDT pairs. Base volume is not Binance quote volume; multiplying by latest price is not a measured quote-volume feed. These spot endpoints do not supply perpetual OI or funding.
- [Deribit ticker](https://docs.deribit.com/api-reference/market-data/public-ticker): instrument price, 24-hour statistics, OI, funding fields and source timestamp. BTC/ETH inverse perpetual OI is USD-denominated, not base-asset OI. Perpetual price is not spot price, and funding fields need their own period labels.

No missing metric was computed from an unrelated metric. CVD, liquidation heatmaps, exchange flows and missing core indicators remain unavailable. Future adapters must retain source identity, instrument, currency, units, period and source time per metric. Avoid silently combining unrelated markets into the existing risk model.

## Verified improvements

Added reusable failure classification to dashboard diagnostics and the live-check report. It distinguishes provider restrictions, proxy-policy denial, unavailable proxy, rate limits, timeouts, invalid payloads and general failures. Added bounded, concurrent provider probes with UTC start/completion times, HTTP status, explicit non-integration flags and no redirect following. HTTP 200 by itself is never declared a working data adapter.

All **22 automated tests passed**, including six new tests for policy-versus-provider failure classification, preserving HTTP evidence, timestamped blocked probes, avoiding automatic selection, API error payloads and redirects. Prior stale-data, response validation, manual-refresh and simulated cache-expiry tests remain passing. A separate AppTest using actual Binance calls rendered unavailable values and restriction diagnostics without an exception, with four NO TRADE outputs.

## Remaining blocker

Review and apply a cloud environment allowlist update for api.kraken.com, futures.kraken.com, api.exchange.coinbase.com and www.deribit.com, then rerun direct probes. This is ordinary destination access through the existing proxy; it does not change network location or bypass a provider restriction. Configuration-edit tools are not available in this session, so the user was asked to apply the environment configuration. Provider selection, adapters and real-data refresh verification remain pending actual successful responses.

No deployment, merge, paid-service enrollment or trading functionality was enabled.
