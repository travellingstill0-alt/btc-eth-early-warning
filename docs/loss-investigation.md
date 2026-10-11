# Loss investigation — October 10, 2026 (America/Bogota)

Work continues locally on `research/loss-diagnostics` from the unmerged
`integration/oi-history-provider-fallback` branch. No merge, deployment,
purchase, orders or notifications. No strategy/risk thresholds changed.
New recurring services cost $0; total existing hosting charges are unknown and
must be checked before any spending against the $25/month cap.

## Evidence and findings

Neither main nor the latest available integration branch contains the reported
backtests, trade ledger, execution simulator, timeout definition or eight distinct
strategy implementations. Eight reporting groups below are the requested
asset × direction × horizon combinations, not recovered strategy definitions.
Reported unusually low win rates cannot be reproduced or explained without
those artifacts. No historical results or missing data were invented.

The existing research heuristic uses a completed 20-bar range breakout with
volume >1.2× mean volume, reference entry at signal close, stop at the opposite
range edge and targets at 1R/2R. Signal close is not a guaranteed executable
entry. Far range-edge stops may require substantial moves to reach targets;
this is a hypothesis requiring actual trade excursions, not a demonstrated
cause of losses. There is no timeout policy, cost accounting or backtest engine
in that heuristic. Spot price/volume signals and perpetual context are from
different instruments; spot SHORT does not define a borrowable or executable
perpetual short. Missing funding/borrow and execution venue definitions prevent
accurate net returns. These are audit concerns, not proof of implementation bugs
in the unavailable latest backtests.

Current candle completion, data freshness, OI identity separation, context
validation and unconditional hold remain covered by the existing tests.

| Asset | Direction | Horizon | Entry / stop / timeout / MFE / MAE / fees / slippage / regime diagnosis |
|---|---|---|---|
| BTC | LONG | SCALP | Pending actual ledger and historical data |
| BTC | SHORT | SCALP | Pending actual ledger and historical data |
| BTC | LONG | DAY TRADE | Pending actual ledger and historical data |
| BTC | SHORT | DAY TRADE | Pending actual ledger and historical data |
| ETH | LONG | SCALP | Pending actual ledger and historical data |
| ETH | SHORT | SCALP | Pending actual ledger and historical data |
| ETH | LONG | DAY TRADE | Pending actual ledger and historical data |
| ETH | SHORT | DAY TRADE | Pending actual ledger and historical data |

## Added audit tools

`research.replay` accepts explicit costs and timeout; enters at next candle open;
charges fees on entry and exit notionals; applies adverse slippage to each fill;
fills gap stops at open; distinguishes censored trades from timeouts; handles
same-bar stop/target collisions pessimistically and marks ambiguity. MFE/MAE
include exit-bar extremes and are explicitly bounds: OHLC cannot establish
whether those extremes occurred before exit. No exact excursion claims.
Linear one-unit accounting only: inverse contracts, funding, borrow, liquidity,
queue priority and portfolio sizing are not modeled. It is an audit primitive,
not a completed eight-strategy backtest or a verified execution simulation.

`entry_hypothesis` defines fixed support/resistance retests, higher lows/lower
highs and bullish/bearish structure using completed ranges. Verified CVD must
agree directionally; OI/funding require same-contract identity and availability
at or before signal time. OI/funding values are retained for stratification;
no fitted directional threshold or claimed improvement. Definitions must be
reviewed against actual strategy specifications before testing profitability.

## Historical research protocol still required

Obtain immutable original ledgers and parameter versions first. For each entry,
record signal close and order/fill timestamps, executable instrument, stop and
target versions, timeout, gross and net return, funding/borrow, spread, fees,
slippage, excursion bounds and independently defined trend/volatility/session
regimes. Audit directional signs, base versus quote units, percent versus
fraction rates, funding periods, duplicates, gaps, active candles and exit-bar
ordering. Reconcile the original engine against next-open replay.

Use genuine same-contract historical trades/candles and as-of OI, CVD and
funding. Preserve retrieval/publication timestamps and revision uncertainty.
Live 15-minute CVD windows are not long historical coverage. Do not join spot
CVD to perpetual price or splice provider histories. Binance returned 451 in
this environment; no access bypass was attempted. Longer history has not yet
been obtained or certified.

Freeze definitions before chronological development/validation/held-out splits.
Use a purge at least as long as maximum holding horizon; discard trades whose
exit crosses a split and do not score censored trades as losses. Use warm-up
history for indicators only. Reserve an untouched final holdout; do not tune on
its results. Report each of the eight groups independently, baseline versus
hypothesis, gross/net expectancy, counts, win-rate uncertainty, stop/timeout
fractions, excursion distributions and regime coverage. No optimization loop
was added.

Actual account/exchange maker/taker tier fees remain UNVERIFIED. Do not call a
public headline fee an actual account rate. Preserve official fee schedule and
account tier/discount evidence for each execution date, including fee currency.
Compare zero-cost diagnostic, verified base-case and explicit adverse fee/spread/
slippage cases; assumed cases must remain labeled assumed. No realistic cost
comparison or out-of-sample profitability result is available yet.

## Independent warnings and continuity

The dashboard now exposes independent context diagnostics without using any
strategy P&L. Executed liquidation volumes are observations, not predicted
liquidation pressure or directional squeeze evidence. CVD divergence requires
aligned same-contract price and CVD windows; long/short squeeze detection remains
unverified. Existing OI growth, period-normalized funding and macro gates remain
active; abnormality baselines and global macro coverage remain incomplete.

New verified raw CVD/liquidation windows are stored immutably and transactionally
in `data/context_windows.sqlite3` (override `CONTEXT_HISTORY_DB_PATH`). Existing
OI storage remains intact. Payload hashes preserve revisions as separate rows;
retrieval timestamps may create repeated observations. Do not sum overlapping
windows as additional volume/history. Failures are visible; no reset/backfill.
Storage survives process restarts on the same disk; external backups and
persistent hosting are not configured. Collection remains active-session only.
Test fixtures use a separate temporary database, never the live archive.

## Validation performed

Final suite: 115 tests, 113 passed and two opt-in live tests skipped. Replay
regressions cover next-open execution, two-sided costs, LONG/SHORT accounting,
gap stops, ambiguous exits, censored trades, gaps and future context rejection.
Storage tests cover raw-payload preservation, deduplication and rejection before
archive creation. Python compilation and `git diff --check` passed.

Separate real BTC/ETH retrieval results are recorded in
`research-live-check.json`: both horizons stayed NO TRADE, both assets supplied
verified Kraken Futures CVD and executed-liquidation windows, and existing OI
collection succeeded. Four raw context windows were archived. Both SQLite
stores passed integrity checks. Coin Metrics exchange-flow requests returned
HTTP 400 and remained unavailable. This verifies one retrieval, not sustained
collection, deep history, fee schedules or profitable strategies.
