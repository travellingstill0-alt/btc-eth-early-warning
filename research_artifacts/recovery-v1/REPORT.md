# Research recovery v1 — October 10, 2026, America/Bogota

## Result

No previous seven-day backtest or trade ledger was recovered. Exact reproduction
is blocked by missing original run dates, execution/exit specification, cost
settings and historical risk-gate data. No trades, outcomes, fees, slippage or
excursions were fabricated. Original parameters remain unchanged.

Recovery inspected all eight remote heads, both pull-request heads, reachable
commits and 116 unique historical blobs, worktrees, reflogs and unreachable Git
objects. `git fsck` found no unreachable recovery objects. One worktree exists.
Workspace/shared/scratch/library/download directories and temporary research
artifacts were inspected; no additional backtest was found. The protected
`/tmp/codex-daemon-1000` directory is inaccessible and was not bypassed. Credential
and runtime state directories were not searched for research. Both GitHub PR
bodies were read; issue comments, reviews, review comments and commit comments
are empty. GitHub workflow artifacts and releases are empty. Evidence files
record the scan; this does not prove an artifact never existed elsewhere or
recover deleted GitHub runs/unavailable prior-session storage.

## Recovered strategy rules

Original source: `9270990c213ad8258b4aa486cd9e5884a94db647`.
SCALP: completed five-minute candles. DAY TRADE: completed hourly candles.
Breakout past the prior 20-bar range with volume >1.2 times mean reference volume.
LONG above resistance; SHORT below support. Reference entry is signal close.
Stop/invalidation is the opposite range edge. Two reference targets: 1R and 2R.
Actual execution at signal close, partial target policy, chosen target, timeout,
trade sizing/leverage, overlap handling, fee tiers, slippage/spread and funding/
borrow are not defined by this source. The original live risk assessment also
requires historical ticker, OI, funding, sampled flow and macro review inputs
that are not recovered for the seven-day interval.

The prior session's `research.py` replay primitive is new research code, not a
recovered original simulator. It must not be presented as the prior backtest.

## New verified candle research, distinct from original results

Coinbase Exchange USD spot candles: October 3, 2026 19:00 through October 10,
2026 19:00 America/Bogota (October 4–11 00:00 UTC, exclusive end). Each asset has
2,016 five-minute and 168 hourly research candles, plus 20 warm-up candles per
series. All four series passed exact timestamp coverage, duplicate conflict,
finite OHLCV and completed-interval checks. No candles were interpolated.
Raw HTTP responses, request parameters and SHA-256 hashes are preserved.
These are provider-reported candles with no exchange publication timestamp;
as-of revision history is unknown. They are not independently cross-venue
verified and are not Binance USDT or Kraken perpetual candles.

The original breakout/volume formula produces 235 unexecuted candidates.
Historical risk gates were not evaluated. Prices shown in candidate files are
reference levels, never fills. No trade P&L, win rate, timeout outcome or
MFE/MAE is inferred from candidates.

| Asset | Direction | Horizon | Candidates | Median reference stop distance | Median directional next-candle return |
|---|---|---|---:|---:|---:|
| BTC | LONG | SCALP | 52 | 0.477% | -0.016% |
| BTC | SHORT | SCALP | 52 | 0.617% | -0.007% |
| BTC | LONG | DAY TRADE | 4 | 1.521% | -0.030% |
| BTC | SHORT | DAY TRADE | 6 | 3.220% | +0.020% |
| ETH | LONG | SCALP | 53 | 0.513% | -0.037% |
| ETH | SHORT | SCALP | 56 | 0.731% | -0.010% |
| ETH | LONG | DAY TRADE | 5 | 1.040% | -0.079% |
| ETH | SHORT | DAY TRADE | 7 | 5.660% | +0.065% |

Next-candle return is direction-signed open-to-close movement in the first
following candle, not realized return. Candidates without a following archived
candle are excluded only from that descriptive metric; counts and exact
observation totals remain in `candidate-diagnostics.json`. DAY TRADE samples
are especially small. No cost deductions or execution assumptions apply here.

## Loss diagnosis status

- Entry timing: original reference entry at close differs from guaranteed next
  executable fill. Signed next-open gaps are archived for research candidates;
  actual latency and order fills are missing. No causal attribution yet.
- Weak follow-through: six groups have negative median directional next-candle
  movement in this new window. This is evidence for further investigation only,
  with no significance claim or recovered-loss attribution.
- Stops: DAY TRADE SHORT reference stops span median 3.22% BTC / 5.66% ETH.
  The 1R/2R targets consequently require larger favorable moves. Actual stop
  fills and pre-exit excursions are missing; poor placement is not established.
- Timeouts: original timeout is missing. No timeout-loss percentage can be
  calculated and no new timeout has been invented.
- Costs: account tier and historical fees/slippage are missing. No headline
  exchange fee is represented as an actual account fee; net profitability and
  cost-induced losses remain unverified.

Parameters must remain frozen until a ledger or a full original reproducible
specification allows these questions to be answered. No optimization performed.

## Collection continuity

This run saved new verified Kraken Futures BTC/ETH CVD and executed-liquidation
windows and real OI snapshots. The archive now contains two 15-minute context
windows for each asset/kind and two locally stored OI snapshots for each asset.
These are separate saved observations, not continuous coverage. Context coverage
has a 51-minute unobserved interval between saved windows. Local OI samples have
approximately 65.9-minute gaps; validated remote OI history may cover separate
periods, but is not represented as local snapshot continuity. Exact UTC epoch
intervals, identities and definitions are recorded in `collection-v1/coverage.json`.
Both live SQLite databases passed integrity checks; exports preserve raw context
payloads, observation and receipt times, identity and hash metadata.

All four live panels returned NO TRADE. Exchange-flow requests returned HTTP
400 and remain unavailable. Global macro coverage remains incomplete. No
background collector is running; collection stops when the session/page is
inactive. Missing history is never synthesized or filled with zero.

## Validation and next action

120 tests ran: 118 passed, two opt-in live tests skipped. Separate live collection
checks above used actual public responses. Tests isolate fixture storage in
`/tmp/btc-context-test-fixtures.sqlite3`, outside the live archive. Tests cover
candle coverage/duplicates/OHLCV, safety gates, replay primitives, immutable
context storage and UI rendering. No trading profitability test was possible.

Recommended next action: obtain the original ledger or run specification,
including original dates, traded contract, chosen targets/partial exits,
timeout, sizing, fill policy, historical fees/slippage/funding and risk-gate
inputs. Then replay against same-instrument genuine candles and reconcile each
exit before testing any entry changes. If that information cannot be supplied,
define a clearly labeled new baseline experiment; do not call it reproduction.

No purchase, deployment, merge, orders or notifications. New recurring paid
services: $0. Existing infrastructure charges are unknown; no spending was
incurred against the $25/month limit. Research artifacts are versioned on a
separate Git branch for later sessions, not merged into main.
