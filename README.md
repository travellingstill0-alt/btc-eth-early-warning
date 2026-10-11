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

Verified venue-scoped CVD and executed liquidation volumes are integrated as described below. Future liquidation heatmaps and exchange-labelled inflow/outflow remain unavailable and are never inferred from unrelated metrics. An automatic global macro source collector and calendar gate are integrated, but complete live coverage is not verified. Missing/stale calendar information and HIGH/EXTREME event windows block ENTER; manual acknowledgement cannot override them. These unavailable mandatory context inputs keep both panels at NO TRADE even when core inputs are complete.

## Validation

Unit tests cover provider outages/fallback, timestamps, malformed data, units/periods, candle gaps, risk scoring, missing/stale input protection, macro gating, confirmed breakouts and exclusion of incomplete candles. Streamlit AppTest checks populated and unavailable dashboards.

Run read-only live primary and fallback checks:

```bash
.venv/bin/python scripts/check_public_apis.py --history-db /tmp/btc-eth-oi-check.sqlite3 --output /tmp/btc-eth-live-check.json
```

The script uses real API responses. In fallback modes, primary outages are deliberately simulated; every secondary response is real. Output records actual HTTP status, request parameters, source timestamps, missing indicators, risk and panel signals. It exits nonzero if implemented live inputs or normal Kraken OI windows fail, or if missing required data permits a trade signal. Deribit/local history warm-up is expected and must remain NO TRADE. The live check database contains only real newly collected snapshots, so it does not pretend a multi-hour persistence soak has completed. This checks individual GET requests, not sustained uptime or trading execution. Live API connectivity and UI rendering must be checked in each deployment; public API availability is not guaranteed. Android layout uses Streamlit's responsive components; physical-device testing is still required.

See [OI history investigation and validation](docs/oi-history-validation.md) for tested endpoints, live results and persistence limits.

## Mandatory safety context and assessment validity

CVD, liquidation data and exchange flows are mandatory safety inputs. Fresh, complete CVD and executed liquidation observations can satisfy their respective availability checks. Exchange flows have no verified integration and keep both panels at NO TRADE even with complete market/context data and macro acknowledgement. Sampled taker flow cannot substitute for CVD; unknown providers, estimated data and arbitrary context flags do not satisfy these checks.

Each assessment records its evaluation time, rules and a digest of its input snapshot. Signal evaluation rejects expired, future, missing or changed-snapshot assessments and reassesses source freshness at the signal time. Invalid provider timestamps are rejected before selection, allowing another provider or an unavailable input instead of a retrieval crash.

## Verified CVD and executed liquidations

The dashboard shows 15 completed minutes of **single-contract** perpetual CVD (taker buy minus sell volume, reset at the displayed window start) and executed liquidation volume. Neither is whole-market coverage or a prediction of future liquidations.

Kraken Futures minute analytics supplies PF_XBTUSD/BTC and PF_ETHUSD/ETH data. CVD totals use the real buy/sell buckets, cross-check the provider's cumulative increments and require all 15 consecutive minute buckets. Liquidation volume uses real reported buckets, including explicit zeros; missing buckets are unavailable, never zero-filled. Active buckets are excluded.

CVD fallback uses complete Deribit BTC/ETH-PERPETUAL trade history in native USD amounts, not spot samples. Saturated requests are split into disjoint millisecond ranges with a seven-request budget. All ranges must be complete, with contiguous trade sequences, unique trade IDs and valid taker directions. Block/combo executions, unverified response timestamps, truncated results or budget exhaustion make the entire window unavailable. Deribit windows replace Kraken windows without conversion or splicing.

Liquidation fallback uses Kraken public execution history, with a ten-page budget. The oldest observed trade must precede the window start; sequences must be contiguous and overlaps must agree. Only explicit liquidation/partial-liquidation executions are counted. This is an alternate endpoint on the same provider, not independent exchange redundancy. Real BTC sequence gaps observed during validation correctly prevented fallback; ETH fallback supplied complete coverage. A provider outage or insufficient history leaves liquidation data unavailable.

Every assessment revalidates raw context data, provider/contract/unit identity, completed-window boundaries, receipt time, finite values and the configured freshness limit. Exchange flows remain missing, so NO TRADE remains active. No context-derived trading thresholds or predictive heatmaps are invented.

Read-only verification:

```bash
.venv/bin/python scripts/check_context_apis.py --output /tmp/btc-eth-context-check.json
```

This checks real primary/secondary responses under simulated primary outages. It requires the primary feeds to validate; secondary coverage failure is recorded as unavailable rather than hidden. See [provider investigation](docs/context-provider-validation.md) for costs, observed limitations and validation.

Exchange-wallet flows: a read-only Coin Metrics Community availability adapter now checks paired Kraken-labelled daily BTC/ETH inflow/outflow metrics. These remain **unverified diagnostics**, never a safety input: daily timestamps, unknown entitlement, wallet completeness and finality cannot satisfy the current rules. Network/provider errors remain explicit warnings; exchange flows still block ENTER. See [provider investigation, costs and limitations](docs/exchange-flow-provider-validation.md). Run `python scripts/check_exchange_flow_apis.py` for live access checks; it exits nonzero if provider responses cannot be validated.

Global macro calendar and indicative Asia/Europe/USA sessions now display America/Bogota times with international DST handling, configurable pre/post-event windows, and separate missing-data versus high-risk NO TRADE reasons. Official source access is blocked in this environment, several region-specific adapters and numerical results/forecasts remain missing, and no calendar provider is safety-approved. See [coverage, tests, costs and limitations](docs/global-macro-calendar-validation.md). Run `python scripts/check_macro_sources.py` for read-only live access checks.

## Context validation and safety hold

BLS iCalendar is fetched read-only with a 15-second timeout. Event timestamps require UTC or a supported US Eastern timezone; DST is converted to UTC. Incomplete envelopes/events, duplicate IDs, missing titles and unsupported recurrence/timezones fail closed. The next 45 days must include CPI and Employment Situation. A retrieved schedule expires after one hour; future retrieval times are invalid. BLS supplies no publisher update timestamp in this feed, so a fresh fetch cannot prove schedule currency or full release coverage. Scheduled future releases are expected, not observations.

Coin Metrics requests each asset separately with a bounded eight-day lookback. Validation requires seven consecutive completed UTC daily intervals, finite nonnegative inflow/outflow values, matching assets, unique midnight UTC timestamps, recognized metric status, valid publication timestamps after interval completion, and no unconsumed pagination. Retrieval expires after one hour; latest daily observation start must be no older than 72 hours. Missing/stale/malformed data is explicitly unavailable or unverified. Cached feeds refresh every 60 seconds in an active session; retrieval age is also checked during rendering.

`flash` is prominently marked PROVISIONAL and may be revised. Native-unit daily net inflow means inflow minus outflow, not an order recommendation. Daily flows are broader market context, never real-time scalp confirmation. Neither final nor provisional flows, nor a BLS schedule, can release the unconditional NO TRADE hold. Source completeness and timeliness do not establish exchange attribution accuracy or market-wide coverage.

## Persistent integration checks

```bash
.venv/bin/python -m unittest discover -s tests -v
RUN_LIVE_INTEGRATION=1 .venv/bin/python -m unittest discover -s tests -v
```

The default suite uses deterministic source fixtures and verifies malformed data, missing days, stale/future timestamps, DST, pagination, flash labels, source failure isolation, dashboard rendering and the research hold. Opt-in live tests require both actual context feeds to pass validation and render the dashboard with four NO TRADE signals. Isolated legacy heuristic tests temporarily disable the hold inside the test process to preserve regression coverage of the original safety gates. This is not an application control.

## Market-data alternatives checked October 10, 2026

Read-only probes from this environment returned HTTP 200 for Coinbase Exchange BTC-USD and ETH-USD tickers, Kraken BTC/ETH spot tickers, Kraken Futures tickers, and Deribit BTC futures summaries. Binance still returns HTTP 451 for restricted location. No proxy bypass, trading credentials or order endpoints are used.

Coinbase Exchange or Kraken are candidates for spot prices, candles and trades. Kraken Futures or Deribit are candidates for derivatives context. These are reachable candidates, not verified replacements: adapters must validate timestamps, candle completeness, history depth, native/contract/notional OI units, funding period conventions and venue eligibility. A reachable ticker does not verify historical OI or complete funding coverage. Never splice their data into Binance series or silently substitute USD instruments for USDT. Label each venue/instrument explicitly, establish its own baseline and test stale/failure behavior before considering it required-input coverage. PR #2 retains its existing Coinbase/Kraken spot and Kraken Futures/Deribit fallback adapters; endpoint reachability alone does not certify every required input.

## Remaining macro coverage

- US: BLS covers selected labor, inflation and related statistical releases only. Missing Federal Reserve/FOMC decisions, minutes and speeches; BEA GDP/PCE; Census retail sales and other releases.
- Europe: missing ECB decisions/speeches, Eurostat inflation/GDP/employment and national calendars.
- UK: missing Bank of England decisions/speeches and ONS inflation/GDP/employment/retail sales.
- Asia: missing BOJ/Japan statistics, PBOC/China NBS, RBA/Australia ABS and other regional calendars.

These sources require access checks, official-calendar adapters, timezone/DST normalization, coverage and revision checks. No global all-clear is inferred from an empty calendar. Existing global-calendar pre/post-event blackout windows and required-input checks remain active; complete official-source coverage certification remains future work; the unconditional hold stays active while these gaps remain. Nothing was merged, deployed or connected to automated trading.

## Loss diagnostics research

See [loss investigation and pending evidence](docs/loss-investigation.md).
`research.py` adds explicit next-open replay and fixed entry hypotheses; it
has no profitability results, verified account costs or optimization loop.
Verified raw CVD/liquidation windows now persist in
`data/context_windows.sqlite3` (`CONTEXT_HISTORY_DB_PATH` override), separately
from the existing OI store. Keep backups on a persistent filesystem; overlapping
windows must not be summed. Independent warning diagnostics do not consume
strategy results. NO TRADE stays locked; trading and notifications stay disabled.

Isolate fixture archives when testing:

```bash
CONTEXT_HISTORY_DB_PATH=/tmp/btc-context-test-fixtures.sqlite3 .venv/bin/python -m unittest discover -s tests -v
```

## Recovering saved research in future sessions

Start with [research archive index](research_artifacts/README.md) and
[recovery report v1](research_artifacts/recovery-v1/REPORT.md) on branch
`research/loss-diagnostics`. This branch preserves raw seven-day Coinbase
candles, unexecuted signal candidates, real CVD/OI/liquidation observation
exports, collection gaps and test logs. No original trade ledger was recovered;
`ledger-status.json` distinguishes missing records from zero trades. Do not
represent these candle candidates as the previous backtest or infer fills,
fees, slippage, outcomes or excursions from them.

## Frozen experimental backtest v1

[Experiment report](research_artifacts/experiment-v1/REPORT.md) documents the
separate Kraken Futures experiment, assumptions and limitations. It preserves
28 days of real same-contract one-minute candles and historical funding, current
published base-tier fee evidence, all simulated trades and chronological/
walk-forward/cost metrics. It is not the missing original backtest. No tuning,
trading, notifications or live safety overrides are performed.

Offline deterministic reproduction:

```bash
.venv/bin/python scripts/run_experiment.py --root research_artifacts/experiment-v1 --output /tmp/btc-experiment-replay
```

Use a new output directory. Frozen environment versions are in the experiment's
`environment-requirements.txt`. Funding snapshots persist separately in
`data/funding_snapshots.sqlite3` (`FUNDING_HISTORY_DB_PATH` override), with native
period and source identity. Independent funding/OI warnings use validated inputs;
missing context stays visible. Tests must isolate both snapshot archives:

```bash
FUNDING_HISTORY_DB_PATH=/tmp/btc-funding-test-fixtures.sqlite3 CONTEXT_HISTORY_DB_PATH=/tmp/btc-context-test-fixtures.sqlite3 .venv/bin/python -m unittest discover -s tests -v
```

## Entry and exit research v1

Start with [research index v3](research_artifacts/INDEX-v3.md) and
[confirmation/exit report](research_artifacts/confirmation-v1/REPORT.md).
The frozen baseline remains unchanged. Price retests, 0.5R targets and halved
holding deadlines have versioned comparisons, full ledgers, equal-entry exit
counterfactuals, excursion/peak-time diagnostics and causal regime metrics.
Historical Kraken CVD/OI values are complete, but original as-of availability is
unknown: the full CVD/OI/funding entry variant is explicitly NOT EVALUATED.
The reused 28 days are retrospective research, never a pristine holdout.

The dashboard independently validates aligned single-contract perpetual price
and CVD windows. A sign divergence is an observation, not a reversal forecast.
Verified price windows persist in `data/perpetual_price_windows.sqlite3`
(`PRICE_CONTEXT_DB_PATH` override). Missing/mismatched/stale coverage stays
unavailable. LOW/MODERATE/HIGH/EXTREME scoring and NO TRADE hold remain unchanged.

Isolate all new test snapshot stores:

```bash
PRICE_CONTEXT_DB_PATH=/tmp/btc-price-test-fixtures.sqlite3 FUNDING_HISTORY_DB_PATH=/tmp/btc-funding-test-fixtures.sqlite3 CONTEXT_HISTORY_DB_PATH=/tmp/btc-context-test-fixtures.sqlite3 .venv/bin/python -m unittest discover -s tests -v
```
