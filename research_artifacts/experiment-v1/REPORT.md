# Breakout experiment v1 — October 10, 2026, America/Bogota

This is a new fixed-assumption experiment. It does not reproduce the missing
original backtest. The recovered original rules/source archive is unchanged.
No original results were searched again, no parameters were optimized, and no
live risk gate was bypassed. No trading or notification actions exist here.

## Frozen assumptions and data

Configuration: `config.json`. Kraken Futures linear perpetuals PF_XBTUSD and
PF_ETHUSD, September 12, 2026 19:00 to October 10, 2026 19:00 America/Bogota
(September 13–October 11 00:00 UTC, exclusive end), plus 20 warm-up hours.
Each contract supplies 41,520 genuine one-minute candles and 692 hourly funding
observations including warm-up. Five-minute/hourly signals are aggregated from
complete same-contract minutes, with no gap interpolation. Raw exchange
responses, normalized records, request parameters and hashes are archived.
The initial fetch included both request boundaries; disjoint [from,to) ownership
removes overlap. A duplicate endpoint boundary differed only in volume floating
precision. No missing minute was synthesized. The resumed raw candle archive
has no receipt metadata from its first attempt; manifests flag this explicitly.
Original publication timestamps and historical revision/as-of versions are
unavailable. Data is exchange-reported and validated, not independent multi-venue
confirmation.

Entry confirmation uses completed closes beyond the previous 20-bar range and
volume strictly above 1.2× prior mean. The experiment deliberately adds no
historical CVD/OI/funding directional filters or live risk scoring: their missing
as-of coverage would otherwise prevent this price-only research. Funding is
charged as a cost, never used as a future signal. Nothing can unlock NO TRADE.

Stops remain the opposite reference-range edge, fixed at signal time. One fixed
1R take-profit uses signal-close-to-stop distance. No partial exits, trailing or
breakeven adjustments. SCALP maximum duration is 60 minutes; DAY TRADE is 12
hours. These exit choices are newly documented assumptions, not original rules.

Entry is next minute open with adverse slippage and native tick rounding. Gap
stops/targets execute at open; ordinary triggers use stop/target price, then
adverse slippage and tick rounding. Same-minute collisions choose stop first.
Timeout exits use the deadline close. Each portfolio permits one position per
asset/direction/horizon/scenario/partition. LONG and SHORT are independent.
Only signals with a complete maximum-holding window inside the partition are
eligible; boundary signals are purged without inspecting whether they would
exit early. Skips and reasons are recorded. No positions cross partitions.

Each independent portfolio starts with $10,000 model equity and a $1,000 fixed
notional cap, rounded down to native quantity precision (BTC 4 / ETH 3 decimals).
No compounding, leverage escalation, cross-portfolio capital reuse or portfolio
aggregation. Actual account collateral, margin conversion and venue eligibility
are not modeled; this is a linear USD research ledger, not an executable account
simulation.

## Exchange cost evidence and uncertainty

The public instruments endpoint assigns both contracts fee schedule UID
`723888f7-0a8e-4183-8648-f920a22339e3`. Its public zero-volume tier reports maker
0.02% and taker 0.05%. Every simulated fill is charged taker: 5 bps on actual
entry and exit notionals, USD fee convention. The runner verifies the linked
schedule and percent-to-bps conversion. `probe-0.json` / `probe-1.json` preserve
raw official fee/instrument evidence. This is a published current base tier,
not verified user entitlement, historical fee schedule or discount evidence.

Base slippage: 2 bps per fill, including spread, plus adverse tick rounding.
Adverse case: 10 bps per fill with the same fee. Higher-fee sensitivity: 25 bps
per fill with base slippage; this is sensitivity, not an assigned user tier.
Slippage assumptions are plausible research scenarios, not measured historical
order-book execution. Queue, depth, latency and market impact are unavailable.

Historical hourly fundingRate is native USD/base/hour. Positive rates debit
LONG and credit SHORT; the modeled rate at timestamp applies over the following
hour, prorated to holding duration. This accrual convention is explicit and not
certified against exchange account statements. Intraminute exit funding is
charged through minute end, adding up to one-minute timing uncertainty. Funding
is real reported history; no missing rate is replaced by zero. No spot borrow
cost is used because these are perpetual instruments. Inverse contracts and
collateral conversion fees are outside this experiment.

## Chronological validation

Development: September 13–27 UTC, 14 days. Validation: September 27–October 4,
7 days. Chronological test: October 4–11, 7 days. Indicator warm-up may use earlier
candles; signal construction only sees candles completed at the signal time.
No parameter fitting or selection occurred after examining these results.
This is retrospective chronological evaluation. The last week was previously
inspected in candidate research, so it is not a pristine untouched holdout and
does not establish prospective out-of-sample reliability.

Walk-forward evaluates three successive seven-day windows after the first week,
using expanding earlier context, frozen rules and no retraining. Its ledger is
separate from the main split ledger: overlapping evaluations must not be counted
twice. Each fold has its own equity and maximum-holding boundary purge. All
metrics remain separate by BTC/ETH, direction, horizon, partition and scenario.

## Final chronological week — published base costs

Win rate uses net P&L > 0. Profit factor is net gains divided by absolute net
losses. Average net return uses actual entry notional. Expectancy is mean net
USD P&L per trade; mean net R is also archived. Drawdown uses minute-close/open-
gap marked equity, entry fees and accrued funding; intraminute drawdown extremes
are not known. Each group's fixed $1,000 notional is only 10% of $10,000 equity,
so drawdown depends on that sizing choice.

| Asset | Side | Horizon | Trades | Win % | Profit factor | Max DD % | Avg net return % | Expectancy USD |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BTC | LONG | SCALP | 37 | 21.6 | 0.201 | 0.581 | -0.156 | -1.554 |
| BTC | SHORT | SCALP | 35 | 34.3 | 0.415 | 0.500 | -0.123 | -1.226 |
| BTC | LONG | DAY TRADE | 3 | 33.3 | 0.416 | 0.314 | -0.541 | -5.394 |
| BTC | SHORT | DAY TRADE | 5 | 40.0 | 1.334 | 0.247 | 0.156 | 1.544 |
| ETH | LONG | SCALP | 32 | 15.6 | 0.202 | 0.554 | -0.173 | -1.724 |
| ETH | SHORT | SCALP | 38 | 36.8 | 0.940 | 0.388 | -0.013 | -0.131 |
| ETH | LONG | DAY TRADE | 2 | 0.0 | 0.000 | 0.167 | -0.462 | -4.615 |
| ETH | SHORT | DAY TRADE | 3 | 66.7 | 1.653 | 0.362 | 0.547 | 5.465 |

Six groups are negative; every SCALP group is negative. Positive DAY TRADE SHORT
results have only five BTC trades and three ETH trades and do not establish an
edge. Both DAY TRADE SHORT groups lost in the preceding two weekly folds.
Every SCALP group lost in all three walk-forward folds. Full development,
validation, weekly-fold and cost-scenario metrics are in `results/metrics.csv`
and `results/metrics.json`, including counts, win rates, profit factors, drawdown,
expectancy, average return, net P&L and exit distributions.

## Cost sensitivity, final week

These sums are descriptive totals across eight independent portfolios, not a
shared-capital portfolio return or combined drawdown. Scenarios retain separate
ledgers and must not be added together.

| Scenario | Trades | Net P&L USD | Fees USD | Slippage/rounding USD | Funding cost USD |
|---|---:|---:|---:|---:|---:|
| published_base | 155 | -161.85 | 154.53 | 66.20 | -0.17 |
| adverse_slippage | 155 | -408.31 | 154.53 | 312.84 | -0.18 |
| higher_fee_sensitivity | 155 | -779.97 | 772.66 | 66.20 | -0.17 |

## Documented failure mechanisms in this experiment

For the base final week, 119/155 trades (76.8%) timed out, versus 21 target and
15 stop exits. The fixed range-edge targets frequently were not reached within
the declared horizon. This diagnoses the experiment's exit distribution without
claiming the timeout or stop is optimal or causing the unavailable original
losses. Trade-level excursions allow subsequent timing/placement research.

Before execution costs, signed entry-open-to-exit-trigger price movement sums
+$58.71 across the independent groups. Slippage/rounding costs $66.20 and fees
$154.53; funding supplies a small $0.17 credit, producing -$161.85 net. Costs
flip 22 otherwise price-positive trades into net losses. These figures separate
weak price advantage from cost drag; they do not justify selecting cheaper
assumptions to manufacture profitability. Fee evidence remains current-tier,
and modeled slippage is not measured.

The recovered formula is a breakout entry after the move. Next-open fills,
actual stop distances, holding durations and excursion bounds are in the ledger.
No causal entry/stop improvement is established, and no parameters changed in
response to these outcomes. Future work should predeclare comparisons against
this frozen baseline on new data rather than optimize these 28 days.

## Complete simulation ledger and uncertainty

`results/main-ledger.csv` and `.json`: 1,920 simulated trades across three
scenarios and main chronological partitions. `results/walk_forward-ledger.csv`
and `.json`: 1,401 simulated trades across scenarios and weekly folds. These
are complete simulated executions under the declared policy, never original
or live trade records. Each row has configuration/scenario/partition IDs,
asset/contract, LONG/SHORT, SCALP/DAY TRADE, signal/entry/exit times and prices,
stop/target, native quantity, fee components, slippage/rounding, funding, gross/
net P&L, outcome, duration, exit reason and excursion data.

Intraminute stop/target exit timestamps are represented at minute end with
explicit interval bounds and an `exit_timestamp_exact` flag. Maximum favorable
and adverse excursions on such exits can only be bounded from OHLC, so both
lower/upper bounds and `excursion_exact` are included. The familiar maximum
excursion columns hold MFE upper / MAE lower bounds, not fabricated exact paths.
Gap and timeout timestamps follow the stated execution convention. Zero
ambiguous stop-target collisions occurred in this run. The model can still miss
subminute liquidity and adverse selection.

## Independent warnings and observation preservation

Verified funding snapshots now persist natively with provider, contract, source
snapshot time, receipt time and 1h/8h period. Stale/future, wrong asset/period and
conflicting timestamps are rejected. The field-specific publication time is
unknown; a server snapshot is explicitly labeled. Existing CVD/OI/liquidation
stores continue. `observations/` includes immutable JSON exports, live checks
and gap coverage from actual public retrievals; test fixtures are not exported.

Independent warnings calculate native-period funding extremes and validated OI
window growth without using trade performance. Liquidation volumes remain
executed observations, not future pressure forecasts. CVD divergence and
squeeze warnings remain UNVERIFIED where same-contract aligned histories or
side information are missing. Funding/OI threshold non-trigger is not an
all-clear. Exchange-flow requests still return HTTP 400 and macro coverage
remains incomplete. All four live panels stayed NO TRADE. Collection remains
active-session/explicit-call only; gaps in saved coverage remain flagged.

## Tests, reproducibility and continuity

134 tests ran: 132 passed, two opt-in live tests skipped. Separate real live
checks succeeded for implemented market/context feeds while recording unavailable
exchange flows. Tests cover causal completed-candle signals, next-open fills,
two-sided fees, funding direction/proration, tick/quantity rounding, gap stops,
exit collisions, excursion uncertainty, missing history rejection, timeouts,
no-overlap, partition purge and marked drawdown. Ledger invariants and P&L
reconciliation passed for all 3,321 main/walk-forward rows. Python compilation
and whitespace checks passed.

The offline runner produced byte-identical hashes for every output in a second
run (`reproduction-check.json`). Inputs include raw/normalized data hashes,
frozen configuration and code hashes; `manifest.json` hashes the whole artifact
version. Runtime dependency versions are pinned in `environment-requirements.txt`.

Reproduce without network or live collection, from repository root:

```bash
.venv/bin/python scripts/run_experiment.py \
  --root research_artifacts/experiment-v1 \
  --output /tmp/btc-experiment-replay
```

Choose a new output directory; the runner refuses to overwrite results. Keep
research configurations/artifacts versioned rather than modifying this version.
The original rule archive and recovery-v1/history-v1 are unchanged. Git branch
`research/loss-diagnostics` preserves the new experiment for future sessions.
Local SQLite databases still require a retained disk; committed exports survive
workspace replacement. No background collector or notification service exists.

Recommended next action: keep this baseline frozen and reserve the week
October 11, 2026 19:00–October 18, 2026 19:00 America/Bogota (October 12–19 UTC)
for a prospective evaluation with the same config, followed by a much longer
history study. Any entry-confirmation experiment should have a separate version
and be compared across declared regimes/cost cases, with no retuning on this
retrospective test. A seven-day prospective window still cannot establish a
stable edge, especially for DAY TRADE.

NO TRADE remains locked; automated trading and notifications remain disabled.
No purchases, deployment or merges. Public data and new recurring services cost
$0; existing infrastructure billing is not audited. The $25/month budget has not
been used to subscribe to any service.
