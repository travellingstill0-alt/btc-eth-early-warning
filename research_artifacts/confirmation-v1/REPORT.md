# Confirmation and exit research v1 — October 10, 2026, America/Bogota

The unchanged baseline was reproduced exactly. Price retests and two simple exit
changes do not establish a reliable improvement. The full verified CVD/OI/funding
strategy is **NOT EVALUATED** because original as-of availability is unverified.
No original missing ledger was searched again or recreated. No parameter grid,
optimization, ranking, automatic strategy promotion or live trade exists here.

## What the follow-through audit found

In the baseline final chronological week, 119/155 trades timed out (76.8%).
Median SCALP MFE upper bounds reached only 25–35% of required target distance.
Median targets required 4.3–4.7 signal-bar ATRs in SCALP and 4.6–7.0 in DAY TRADE.
This is a fixed range-edge stop/1R target design: targets demand much more than
most observed favorable movement during the permitted holding window. It is
evidence of a distance/follow-through mismatch in this experiment, not proof
that a tighter stop, lower target or later entry will improve profitability.

In 70/155 baseline trades, even the favorable-excursion upper bound was below
incurred fees/slippage/funding expressed as return. This is a diagnostic of cost
burden, not an exact hypothetical exit-cost quote at the favorable peak. Verified
peak-price intervals often occurred early in the holding window; peaks are known
only to the minute interval, and partial exit-candle candidates are excluded from
peak-time medians. Post-exit candle returns are never used as pre-exit excursions.

| Asset | Side | Horizon | Median TP % | Median stop % | Median MFE upper % | Median MAE lower % | MFE/TP upper | Peak-time midpoint min | Verified peak intervals |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| BTC | LONG | SCALP | 0.439 | 0.481 | 0.118 | -0.166 | 0.281 | 22.5 | 34/37 |
| BTC | SHORT | SCALP | 0.467 | 0.509 | 0.214 | -0.222 | 0.252 | 5.5 | 31/35 |
| BTC | LONG | DAY TRADE | 1.707 | 1.749 | 0.198 | -1.208 | 0.060 | 5.0 | 2/3 |
| BTC | SHORT | DAY TRADE | 2.744 | 2.784 | 0.791 | -0.681 | 0.247 | 77.0 | 4/5 |
| ETH | LONG | SCALP | 0.458 | 0.504 | 0.120 | -0.250 | 0.280 | 5.5 | 29/32 |
| ETH | SHORT | SCALP | 0.584 | 0.630 | 0.252 | -0.188 | 0.353 | 15.5 | 30/38 |
| ETH | LONG | DAY TRADE | 1.228 | 1.272 | 0.178 | -0.938 | 0.132 | 9.0 | 2/2 |
| ETH | SHORT | DAY TRADE | 4.292 | 4.338 | 2.665 | -0.456 | 0.621 | 344.5 | 2/3 |

These are marginal medians, not one representative trade. MFE/TP uses the
per-trade ratio median. ATR is mean true range over the last 20 completed signal
bars, including confirmation. MAE is negative signed adverse movement. Exit-bar
excursions remain bounds; no tick path or exact peak timestamp is fabricated.
Detailed entry/exit audit includes original breakout protrusion, relative volume,
next-open gaps, target/stop volatility distances, confirmation delay, realized
cost hurdle, minute peak intervals and censored post-entry returns.

## Frozen experiments and assumptions

`config.json` defines a small fixed hypothesis set. Baseline configuration and
original source archives are unchanged, with the baseline SHA-256 pinned.
All 3,321 main/walk-forward baseline rows match archived v1 fields identically.

- `baseline_unchanged`: previous completed 20-bar volume breakout, fixed opposite
  range-edge stop, 1R target, 60-minute SCALP / 12-hour DAY TRADE deadline.
- `price_retest_v1`: after that breakout, wait at most three completed signal
  candles. LONG retests broken resistance as support, closes above it and above
  candle open, with a low above the minimum of the three pre-breakout lows.
  SHORT retests broken support as resistance, closes below it and below open,
  with a high below the maximum of the three pre-breakout highs. Any intervening
  close through the retest level invalidates the setup. Earliest same-side
  confirmation wins on duplicate times. Entry remains next-minute open; stop
  remains the original opposite range edge; 1R uses retest-close-to-stop distance.
  This changes timing and reference-target distance, not just trade selection.
- `verified_context_retest_v1`: the same price setup additionally requires aligned
  positive CVD / nonpositive price change for LONG, negative CVD / nonnegative
  price change for SHORT, increasing OI over the same three-signal-bar window,
  and absolute known hourly funding no greater than 0.03%/8h equivalent. This is
  directional price-flow sign disagreement, not a certified two-swing divergence
  or reversal forecast. Use only completed buckets with at least a 60-second lag,
  completed funding periods, and independently recorded original availability
  at or before signal. Missing/unverified availability blocks the experiment.
- `half_r_target_v1`: original breakout/stop, 0.5R target, original deadline.
- `half_timeout_v1`: original breakout/stop/1R target, 30-minute SCALP / 6-hour
  DAY TRADE deadline.

No stop-distance parameter was fitted. The two exit factors are simple declared
hypotheses, not chosen by a profitability search. No trailing, partial exits or
breakeven rule was added. The legacy engine, native tick/quantity rounding,
next-open execution, adverse fill costs, gap handling and pessimistic collision
ordering remain unchanged.

Historical prices and funding use the same genuine Kraken Futures PF_XBTUSD /
PF_ETHUSD minute archive as experiment-v1: September 12 19:00–October 10 19:00
America/Bogota (September 13–October 11 UTC, exclusive end), plus 20 warm-up hours.
Each contract has 41,520 minutes and 692 hourly funding observations including
warm-up. No missing candles/rates are filled. Research remains USD linear
perpetual simulation, not spot shorts or an executable account specification.

Costs and sizing remain v1: published current linked base-tier taker fee 5 bps
per fill; slippage/spread 2 bps plus adverse tick rounding; 10-bps slippage and
25-bps fee sensitivity cases. Fees on both actual notionals. Historical funding
uses reported USD/base/hour with the frozen forward-hour prorated accrual
assumption. Actual account/historical fee tiers, order-book execution and funding
statement reconciliation remain unverified. Fixed $1,000 notional cap / $10,000
independent model equity per asset/side/horizon/scenario/partition, no compounding.

## Historical CVD/OI verification and the blocked comparison

The genuine Kraken analytics archive supplies 41,520 minute CVD records and
41,520 OI records per contract, including warm-up. All four series have exact
coverage and no provider errors. CVD buy/sell volumes are finite/nonnegative and
cross-checked against reported cumulative increments. OI OHLC is validated in
native contract base units. Disjoint request intervals prevent overlapping
buckets from being double-counted. The raw responses and normalization hashes
are saved. No spot flow proxy, cross-provider splicing or synthetic history.

This verifies historical values, not what a strategy could have received at the
original entry. APIs provide interval timestamps but no original publication,
revision or receipt history. Newly retrieved historical records therefore have
`available_at: null` and `availability_verified: false`. No completion time or
assumed lag is relabeled as a publisher timestamp. Historical funding also lacks
original availability proof. The full-context variant has 144 blocked group/
partition/scenario comparisons, **not** zero-trade profitability results.

Price-only comparisons inherit v1's completed-candle execution convention and
unknown historical revision provenance; they are not certified exact as-of
replays. `context-feature-audit.json` separates valid aligned historical values
from missing original availability. Future recorded real feed receipts can
support an availability-aware prospective experiment; existing sparse snapshots
do not backfill the old research interval.

## Chronological and walk-forward comparison

Development is September 13–27 UTC, validation September 27–October 4, and final
chronological week October 4–11. Three expanding-context weekly walk-forward
windows follow the first week. Each independent group applies a maximum-holding
boundary purge, no overlapping position and no cross-boundary trade. Regime and
signal features use only completed candles at the signal; funding is a cost, not
future entry information. The unchanged baseline is separately verified.

All 28 days have already been examined. These are retrospective chronological
comparisons and walk-forward diagnostics, **not a pristine untouched out-of-sample
validation**. They cannot be promoted into prospective profitability evidence.
No parameters are refitted by fold. Main and walk-forward ledgers overlap and
must not be added; cost scenarios are alternate simulations, not extra trades.

Final chronological week, published-base costs:

| Strategy | Asset | Side | Horizon | Trades | Win % | Profit factor | Expectancy USD | Max DD % | Timeout % |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| baseline_unchanged | BTC | LONG | SCALP | 37 | 21.6 | 0.201 | -1.554 | 0.581 | 81.1 |
| baseline_unchanged | BTC | SHORT | SCALP | 35 | 34.3 | 0.415 | -1.226 | 0.500 | 77.1 |
| price_retest_v1 | BTC | LONG | SCALP | 11 | 27.3 | 0.265 | -1.100 | 0.137 | 100.0 |
| price_retest_v1 | BTC | SHORT | SCALP | 12 | 58.3 | 0.408 | -0.958 | 0.157 | 91.7 |
| half_r_target_v1 | BTC | LONG | SCALP | 42 | 28.6 | 0.203 | -1.480 | 0.625 | 61.9 |
| half_r_target_v1 | BTC | SHORT | SCALP | 41 | 39.0 | 0.349 | -1.324 | 0.544 | 56.1 |
| half_timeout_v1 | BTC | LONG | SCALP | 41 | 14.6 | 0.121 | -1.446 | 0.598 | 92.7 |
| half_timeout_v1 | BTC | SHORT | SCALP | 38 | 18.4 | 0.269 | -1.274 | 0.502 | 92.1 |
| baseline_unchanged | BTC | LONG | DAY TRADE | 3 | 33.3 | 0.416 | -5.394 | 0.314 | 33.3 |
| baseline_unchanged | BTC | SHORT | DAY TRADE | 5 | 40.0 | 1.334 | 1.544 | 0.247 | 80.0 |
| price_retest_v1 | BTC | LONG | DAY TRADE | 1 | 0.0 | 0.000 | -5.267 | 0.178 | 100.0 |
| price_retest_v1 | BTC | SHORT | DAY TRADE | 1 | 100.0 | NO_LOSSES | 19.153 | 0.120 | 0.0 |
| half_r_target_v1 | BTC | LONG | DAY TRADE | 4 | 25.0 | 0.154 | -6.980 | 0.421 | 50.0 |
| half_r_target_v1 | BTC | SHORT | DAY TRADE | 5 | 40.0 | 0.891 | -0.505 | 0.247 | 60.0 |
| half_timeout_v1 | BTC | LONG | DAY TRADE | 4 | 25.0 | 0.533 | -2.528 | 0.226 | 75.0 |
| half_timeout_v1 | BTC | SHORT | DAY TRADE | 5 | 20.0 | 0.061 | -5.486 | 0.312 | 100.0 |
| baseline_unchanged | ETH | LONG | SCALP | 32 | 15.6 | 0.202 | -1.724 | 0.554 | 81.2 |
| baseline_unchanged | ETH | SHORT | SCALP | 38 | 36.8 | 0.940 | -0.131 | 0.388 | 71.1 |
| price_retest_v1 | ETH | LONG | SCALP | 8 | 37.5 | 0.947 | -0.065 | 0.078 | 100.0 |
| price_retest_v1 | ETH | SHORT | SCALP | 8 | 25.0 | 0.415 | -1.454 | 0.130 | 62.5 |
| half_r_target_v1 | ETH | LONG | SCALP | 35 | 22.9 | 0.214 | -1.712 | 0.601 | 62.9 |
| half_r_target_v1 | ETH | SHORT | SCALP | 41 | 41.5 | 0.586 | -0.874 | 0.402 | 48.8 |
| half_timeout_v1 | ETH | LONG | SCALP | 33 | 15.2 | 0.120 | -1.815 | 0.599 | 90.9 |
| half_timeout_v1 | ETH | SHORT | SCALP | 41 | 34.1 | 1.008 | 0.013 | 0.325 | 82.9 |
| baseline_unchanged | ETH | LONG | DAY TRADE | 2 | 0.0 | 0.000 | -4.615 | 0.167 | 100.0 |
| baseline_unchanged | ETH | SHORT | DAY TRADE | 3 | 66.7 | 1.653 | 5.465 | 0.362 | 66.7 |
| price_retest_v1 | ETH | LONG | DAY TRADE | 1 | 0.0 | 0.000 | -1.217 | 0.054 | 100.0 |
| price_retest_v1 | ETH | SHORT | DAY TRADE | 0 | — | — | — | — | — |
| half_r_target_v1 | ETH | LONG | DAY TRADE | 2 | 0.0 | 0.000 | -4.615 | 0.167 | 100.0 |
| half_r_target_v1 | ETH | SHORT | DAY TRADE | 4 | 75.0 | 1.355 | 2.229 | 0.382 | 50.0 |
| half_timeout_v1 | ETH | LONG | DAY TRADE | 3 | 0.0 | 0.000 | -5.739 | 0.179 | 100.0 |
| half_timeout_v1 | ETH | SHORT | DAY TRADE | 4 | 50.0 | 1.358 | 1.787 | 0.293 | 75.0 |

Expectancy is mean net USD/trade; mean R, average net return, drawdown, all cost
cases, fold metrics and exit counts are also archived. Drawdown uses minute-
close/open-gap marked equity, not unknown intraminute extremes. Profit factor
`NO_LOSSES` on one trade is a tiny-sample description, not an established edge.
No-trade price groups have undefined win rate/expectancy, never a profit claim.

Price retests reduce the final-week baseline's 155 trades to 42. All four retest
SCALP groups remain negative; 37/42 retest trades time out. Retest DAY TRADE has
only 0–1 trade per group. Lower aggregate loss mostly accompanies less exposure;
it does not prove more profitable entries. Retest results also vary across
weekly folds and regimes.

The 0.5R portfolio has 174 trades, 100 timeouts (57.5%) and -$242.97 versus baseline
-$161.85. Shorter deadlines yield 169 trades, 151 timeouts (89.3%) and -$214.70.
These totals describe independent group sums, not a shared-capital portfolio
return. Changing exits alters re-entry frequency and boundary eligibility.
Reducing timeout rate alone did not establish improved net performance.

ETH SHORT SCALP under the shorter deadline earns only $0.53 across 41 trades at
base costs (roughly $0.013/trade), but loses $64.66 with adverse slippage and
$163.18 with the higher fee assumption. This is not robust profitability.
Positive DAY TRADE and high-volatility subgroup results use very small samples.

## Equal-entry exit diagnostics

A second comparison forces the exact baseline entries and suppresses additional
re-entry. This separates exit economics from trading-frequency effects. It uses
the same costs, quantity and signal-time fixed stop, with 0.5R or half-duration
exits. The complete paired ledger has 6,618 records across scenarios/folds;
24 level-invalid pairs are explicitly skipped, not fabricated as zero returns.
Pairs are counterfactual diagnostics, not additional live or portfolio trades.

Final chronological week at base costs, mean alternative-minus-baseline net
USD/trade on identical eligible entries:

| Asset | Side | Horizon | Paired baseline trades | 0.5R delta USD | Half-timeout delta USD |
|---|---|---|---:|---:|---:|
| BTC | LONG | SCALP | 37 | 0.179 | -0.004 |
| BTC | SHORT | SCALP | 35 | -0.047 | 0.011 |
| BTC | LONG | DAY TRADE | 3 | -2.157 | 2.380 |
| BTC | SHORT | DAY TRADE | 5 | -2.049 | -7.030 |
| ETH | LONG | SCALP | 32 | 0.102 | 0.124 |
| ETH | SHORT | SCALP | 38 | -0.585 | 0.065 |
| ETH | LONG | DAY TRADE | 2 | 0.000 | -3.163 |
| ETH | SHORT | DAY TRADE | 3 | -3.353 | -4.071 |

The lower target improves two groups, worsens five and leaves one unchanged;
shorter deadlines help four and hurt four. Effects are not consistent across
assets/directions/horizons. Do not choose a rule from these observed winners.
Paired counts and cost/fold-specific changes are in `analysis/paired-exit-summary`.

## Performance by market regime

Regimes are defined before results using the last 20 completed signal bars:
direction/efficiency ratio >=0.3 means UPTREND or DOWNTREND; otherwise RANGE.
Mean true-range/price >=0.25% for SCALP or >=1% for DAY TRADE means HIGH_VOL;
otherwise NORMAL_VOL. These are transparent heuristic labels, not fitted
quantiles or universal market states. Regime labels never gate these trades.

`REGIMES.md` and `results/regime-metrics.csv` report counts, win rates, profit
factors, net expectancy, marked drawdown and timeout rates separately for every
observed asset/side/horizon/strategy/scenario/partition/regime. Regime portfolios
are analytical subsets with their own initial equity; they are not a deployable
allocation. Counts and net P&L reconcile with their parent group. Absent regimes
are unobserved, never treated as safe/profitable.

In the final week, baseline normal-volatility SCALP RANGE and directional-trend
subgroups are all negative. Some high-volatility subgroups are positive but have
only one or two trades. That does not justify selecting high volatility as an
entry filter. Regime conclusions remain sample-limited, especially DAY TRADE.

## Independent early warnings and safety

The dashboard now retrieves and validates the same contract's 15-minute
perpetual price window alongside CVD. Freshness, exact candle coverage,
provider/contract/asset identity and window equality are required. Positive CVD
with nonpositive price change or negative CVD with nonnegative price change is
shown as a scoped price-flow sign divergence, not a reversal prediction or
certified swing divergence. Spot price cannot substitute. Deribit CVD without a
verified same-contract price adapter remains unavailable for this comparison.
Raw aligned price windows persist transactionally in their own SQLite store.

Existing native-period funding extremes, validated OI growth and executed
liquidation-volume observations remain independent of strategy P&L. Long/short
squeeze direction and future liquidation pressure remain unverified without
required position/side/level data. Exchange-wallet flow diagnostics still return
HTTP 400 and are unverified; no estimated flow releases a gate.

Official calendar probes now parsed 146 event records across some BLS, ECB,
BOJ, Federal Reserve and Bank of England source pages. This is not global safety
certification: ISM, several European/statistical and speech adapters, future Fed
coverage and China sources remain unavailable/incomplete. Macro assessment is
MISSING_DATA, clear=false. Raw source statuses and events are saved, with UTC
source and America/Bogota event times. Parsed events do not imply complete live
USA/EU/Asia coverage, verified revisions or forecasts.

LOW/MODERATE/HIGH/EXTREME scoring and thresholds in `analysis.py` remain unchanged.
Actual BTC/ETH checks showed LOW observed indicator scores **with incomplete
context**, and all four panels remained NO TRADE. LOW is never an all-clear.
Warnings use verified feed inputs, not trade counts, win rates or profitability.
No notifications, scheduled collector, order API or automated trading enabled.

The live archive exports 16 context windows, eight local OI snapshots, four
funding snapshots and two aligned price windows across assets, including prior
observations. All four SQLite stores pass integrity checks. Missing local
coverage intervals and snapshot gaps are explicit in `observations/coverage.json`.
Retrospectively complete remote CVD/OI values are kept separate from real-time
receipt continuity; sparse snapshots cannot manufacture an as-of history.

## Validation, preservation and reproduction

150 tests ran: 148 passed, two opt-in live tests skipped. Separate actual live
market/price/context and macro checks were performed; missing source coverage
was recorded rather than treated as a passing global integration. Tests cover
LONG/SHORT retests, failed holds, causal regimes/signals, missing/late/future
context, CVD/OI normalization, price/CVD identity and alignment, unknown fallback
providers, both divergence signs, strategy-P&L independence and immutable storage.
Existing baseline execution/cost/safety/UI regressions remain green.

All baseline simulation fields match 3,321 archived rows. Audits reconcile P&L,
regime counts/net P&L, ordered excursion bounds, causal labels and nonoverlapping
positions. Frozen code and input hashes match. The 17 comparison outputs and
seven analysis outputs reproduced byte-for-byte in independent offline runs.
11,660 comparison ledger rows include baseline/variants, cost alternatives and
main/walk-forward evaluations; do not interpret that as 11,660 unique trades.
Baseline archives and their manifests are preserved unchanged.

Run from repository root with fresh output directories, without network:

```bash
.venv/bin/python scripts/run_confirmation_research.py \
  --root research_artifacts/confirmation-v1 \
  --output /tmp/btc-confirmation-replay
.venv/bin/python scripts/analyze_confirmation_results.py \
  --root research_artifacts/confirmation-v1 \
  --output /tmp/btc-confirmation-analysis-replay
```

The analysis command reads the archived `results/` under its root; to analyze
newly generated replay outputs, place those results under a separate versioned
root with the same frozen config/context files. It does not overwrite outputs.
`inputs.json`, manifests, code hashes and versioned test logs make later sessions
reviewable. No new runtime dependency was required. Research is committed on
`research/loss-diagnostics`, never merged into main or deployed.

Recommended next step: leave this baseline and hypothesis set frozen; collect
real receipt-timestamped aligned CVD/OI/funding/price observations prospectively,
with gaps reported. Reserve new data for an availability-aware full-context
comparison and a much longer prospective evaluation. Do not retune these rules
from the reused 28-day period or tiny positive subgroups. Active-session collection
continues; no background deployment or paid service is configured.

Budget: public endpoints/new recurring services $0; existing hosting charges are
not audited. No purchases, deployment or merges. NO TRADE stays locked;
automated trading and notifications remain disabled.
