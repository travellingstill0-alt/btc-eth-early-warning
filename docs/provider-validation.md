# Baseline public provider validation

This report describes the initial provider fallback commit `a8ec8bb`, before OI history integration. See [current OI history validation](oi-history-validation.md) for the newer implementation.

Validated on 2026-10-10 in the attached restricted cloud environment, using the inherited HTTPS proxy and TLS verification. All non-simulated HTTP requests returned 200 with usable data.

Automated validation: 24 tests passed (`.venv/bin/python -m unittest discover -s tests -v`). Streamlit AppTest also rendered both assets using real APIs without exceptions; checking manual macro review did not bypass missing OI history.

Live command: `.venv/bin/python scripts/check_public_apis.py --output /tmp/btc-eth-live-check.json` (exit 0). The normal mode uses real primary providers. Fallback modes simulate primary transport failures and make real secondary requests; they are not evidence that primary providers actually failed.

| Mode | Asset | UTC checked | Spot provider / trade age | OI/funding provider / snapshot age | Hourly / five-minute close age |
|---|---|---|---|---|---|
| normal | BTCUSD | 2026-10-10T18:30:32.860476+00:00 | Coinbase / 3.09s | Kraken Futures / 0.41s | 1832.86s / 32.86s |
| normal | ETHUSD | 2026-10-10T18:30:34.440879+00:00 | Coinbase / 4.08s | Kraken Futures / 0.46s | 1834.44s / 34.44s |
| spot_fallback | BTCUSD | 2026-10-10T18:30:36.404085+00:00 | Kraken / 4.29s | Kraken Futures / 0.70s | 1836.41s / 36.41s |
| spot_fallback | ETHUSD | 2026-10-10T18:30:37.788527+00:00 | Kraken / 2.45s | Kraken Futures / 0.14s | 1837.79s / 37.79s |
| other_fallbacks | BTCUSD | 2026-10-10T18:30:39.612636+00:00 | Coinbase / 2.35s | Deribit / 0.93s | 1839.61s / 39.61s |
| other_fallbacks | ETHUSD | 2026-10-10T18:30:41.297081+00:00 | Coinbase / 3.72s | Deribit / 0.85s | 1841.30s / 41.30s |

| Indicator | BTC | ETH |
|---|---|---|
| Spot price and rolling 24h base volume | Working, Coinbase and Kraken | Working, Coinbase and Kraken |
| Rolling 24h price change | Working through Coinbase; unavailable on Kraken fallback | Working through Coinbase; unavailable on Kraken fallback |
| Completed hourly / five-minute candles and volume | Working, Kraken and Coinbase | Working, Kraken and Coinbase |
| Hourly structure and breakout inputs | Working | Working |
| Limited sampled spot taker flow | Working, Kraken and Coinbase; not CVD | Working, Kraken and Coinbase; not CVD |
| Current open interest | Working, Kraken Futures and Deribit; native units preserved | Working, Kraken Futures and Deribit; native units preserved |
| Funding | Working, Kraken hourly / Deribit eight-hour | Working, Kraken hourly / Deribit eight-hour |
| Comparable hourly OI history / OI growth | Unavailable | Unavailable |
| CVD, liquidation heatmaps, exchange flows, automatic macro calendar | Unavailable | Unavailable |

OI history remains required by the existing safety rules, so SCALP and DAY TRADE both return NO TRADE for both assets in every mode. LOW/MODERATE/HIGH/EXTREME classification and ENTER/WAIT/NO TRADE logic are retained and tested, including confirmed ENTER fixtures with all required observations present. A partial LOW score is not a complete risk assessment.

Kraken spot ticker exposes a UTC-day open, which is not substituted for a rolling 24h open. Funding thresholds use the same eight-hour basis as before; Kraken hourly funding is compared to one eighth of that threshold. Funding rates are displayed at their actual provider periods, not extrapolated. Kraken base-unit OI and Deribit USD OI are not concatenated or compared for growth.

Freshness limitations: trade times corroborate spot price recency, not individual volume update time. Derivatives expose server snapshot timestamps, not separate OI/funding observation times. Candle close ages are interval-boundary times from real source candles; candles use a two-interval freshness limit, not the ticker age limit. UI diagnostics expose these timestamp types and caveats.

Allowed provider hosts: api.kraken.com, api.exchange.coinbase.com, futures.kraken.com, www.deribit.com. Binance remains excluded from the application because earlier real price/OI/funding checks returned HTTP 451 restricted-location errors. No policy bypass, credentials, deployment, alerts, background monitoring or trading execution was added.
