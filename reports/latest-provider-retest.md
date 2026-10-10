# Latest provider retest

October 10, 2026, approximately 13:12 America/Bogota (18:12 UTC). Exact request times are in provider-retest-results.json and binance-latest-retest.json.

## Branch basis

Fetched latest GitHub main: c16faeb5b522b9bfd5303c3a6dee8e3406604e77. Created fix/provider-retest-policy-evidence from main and carried forward both previous validation commits without changing main. The Streamlit application is not deployed.

## Observed environment mismatch

The user reports a published cloud environment with six allowed domains. However, the environment attached to this task still reports only api.binance.com and fapi.binance.com as custom allowed hosts. Its local /etc/codex/network-policy.json also omits all four required alternative hosts. Actual direct requests independently confirm proxy CONNECT HTTP 403 denials.

A refreshed environment status at 18:12:34 UTC reports current observations, spec/observed revision 12, and network state "unknown", not "enforced". This is not evidence of applied six-domain access. The safe runtime fields are retained in environment-retest-state.json. No secret values or proxy credentials are recorded.

## Actual connectivity and market-data results

| Source | Requests | Price | Volume | Open interest | Funding |
| --- | --- | --- | --- | --- | --- |
| Kraken spot, BTC/ETH ticker | 2 | Blocked | Blocked | Not provided by spot ticker | Not provided by spot ticker |
| Kraken futures tickers, including BTC/ETH candidates | 1 | Blocked | Blocked | Blocked | Blocked |
| Coinbase BTC-USD/ETH-USD ticker and stats | 4 | Blocked | Blocked | Not provided by these spot endpoints | Not provided by these spot endpoints |
| Deribit BTC/ETH perpetual ticker | 2 | Blocked | Blocked | Blocked | Blocked |
| Binance, existing seven sources per asset | 14 | HTTP 451 | HTTP 451 | HTTP 451 | HTTP 451 |

All nine alternative requests were denied by the environment proxy before reaching their providers. The providers' own geographic eligibility or availability cannot be inferred from that result. Binance was reached and refused all 14 requests with HTTP 451. No usable live market-data feed was verified or newly enabled.

Market-source timestamps and freshness remain **unverified** because no market payload was returned. Each attempted metric is explicitly unavailable, with source timestamp null rather than a synthesized request timestamp. Diagnostic start/completion UTC timestamps describe only requests. CVD, liquidation heatmaps, exchange flows and other missing indicators remain unavailable; no substitutes or invented data were introduced.

## Verified improvements and tests

The public-provider probe now records a non-secret policy snapshot showing whether each required destination appears in the local policy. Unknown/missing snapshots remain unknown. Actual HTTP results remain authoritative; snapshot presence is not treated as proof of access.

Added per-metric availability/freshness diagnostics and an explicit distinction between diagnostic times and market-source timestamps. The probes remain public GET-only, bounded, concurrent, credential-free and non-integrated; redirects are not followed.

Ran all automated tests: **25 passed**. New tests cover missing provider hosts, unknown policy snapshots and avoiding fabricated metric timestamps after blocked requests. Existing tests cover response validation, source-failure isolation, stale/future data safety, unavailable/populated UI rendering, cache expiry, manual refresh, risk rules and informational signal gating. `git diff --check` passed.

## Remaining action

The attached environment needs the published configuration containing api.kraken.com, futures.kraken.com, api.exchange.coinbase.com and www.deribit.com applied or reattached. The user was asked to reconnect/apply that version. The proxy was not bypassed and no network policy was edited locally. Once actual access works, source identity, values, units, periods and freshness must be verified before any provider adapter is selected.

No dashboard deployment, trading enablement, paid services, merging or main-branch changes occurred.
