# Observed regime performance — confirmation research v1

Final chronological week at published base costs, separately by group and
observed causal regime. These retrospectively inspected data are not a pristine
holdout. Tiny samples, absent regimes and NO_LOSSES profit factors do not
establish an edge. All costs/scenarios/folds are in the CSV/JSON source tables.
Regime marked drawdown uses independent analytical subset equity, not a combined
allocation. Definitions and limitations are in REPORT.md.

| Strategy | Asset | Side | Horizon | Regime | Trades | Win % | Profit factor | Expectancy USD | Max DD % | Timeout % |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| baseline_unchanged | BTC | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 1.147 | 0.023 | 100.0 |
| baseline_unchanged | BTC | LONG | SCALP | RANGE_NORMAL_VOL | 17 | 5.9 | 0.085 | -2.692 | 0.458 | 76.5 |
| baseline_unchanged | BTC | LONG | SCALP | UPTREND_NORMAL_VOL | 19 | 31.6 | 0.413 | -0.678 | 0.199 | 84.2 |
| baseline_unchanged | BTC | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 0.0 | 0.000 | -6.976 | 0.161 | 100.0 |
| baseline_unchanged | BTC | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 14 | 35.7 | 0.814 | -0.324 | 0.224 | 85.7 |
| baseline_unchanged | BTC | SHORT | SCALP | RANGE_HIGH_VOL | 2 | 100.0 | NO_LOSSES | 1.405 | 0.067 | 100.0 |
| baseline_unchanged | BTC | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 29.4 | 0.222 | -1.601 | 0.272 | 64.7 |
| price_retest_v1 | BTC | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 2.449 | 0.024 | 100.0 |
| price_retest_v1 | BTC | LONG | SCALP | RANGE_NORMAL_VOL | 1 | 0.0 | 0.000 | -2.871 | 0.029 | 100.0 |
| price_retest_v1 | BTC | LONG | SCALP | UPTREND_NORMAL_VOL | 9 | 22.2 | 0.141 | -1.298 | 0.132 | 100.0 |
| price_retest_v1 | BTC | SHORT | SCALP | DOWNTREND_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 0.523 | 0.031 | 100.0 |
| price_retest_v1 | BTC | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 6 | 50.0 | 0.249 | -1.988 | 0.173 | 83.3 |
| price_retest_v1 | BTC | SHORT | SCALP | RANGE_HIGH_VOL | 1 | 0.0 | 0.000 | -0.776 | 0.068 | 100.0 |
| price_retest_v1 | BTC | SHORT | SCALP | RANGE_NORMAL_VOL | 4 | 75.0 | 1.250 | 0.172 | 0.049 | 100.0 |
| half_r_target_v1 | BTC | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 1.147 | 0.023 | 100.0 |
| half_r_target_v1 | BTC | LONG | SCALP | RANGE_NORMAL_VOL | 17 | 11.8 | 0.068 | -2.292 | 0.390 | 70.6 |
| half_r_target_v1 | BTC | LONG | SCALP | UPTREND_NORMAL_VOL | 24 | 37.5 | 0.327 | -1.015 | 0.298 | 54.2 |
| half_r_target_v1 | BTC | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 0.0 | 0.000 | -6.976 | 0.161 | 100.0 |
| half_r_target_v1 | BTC | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 20 | 40.0 | 0.517 | -0.843 | 0.217 | 60.0 |
| half_r_target_v1 | BTC | SHORT | SCALP | RANGE_HIGH_VOL | 2 | 100.0 | NO_LOSSES | 3.731 | 0.043 | 50.0 |
| half_r_target_v1 | BTC | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 35.3 | 0.103 | -1.820 | 0.309 | 47.1 |
| half_timeout_v1 | BTC | LONG | SCALP | RANGE_HIGH_VOL | 1 | 0.0 | 0.000 | -0.487 | 0.023 | 100.0 |
| half_timeout_v1 | BTC | LONG | SCALP | RANGE_NORMAL_VOL | 18 | 11.1 | 0.109 | -2.005 | 0.361 | 94.4 |
| half_timeout_v1 | BTC | LONG | SCALP | UPTREND_NORMAL_VOL | 22 | 18.2 | 0.142 | -1.033 | 0.233 | 90.9 |
| half_timeout_v1 | BTC | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 0.0 | 0.000 | -2.097 | 0.071 | 100.0 |
| half_timeout_v1 | BTC | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 17 | 23.5 | 0.453 | -0.956 | 0.281 | 94.1 |
| half_timeout_v1 | BTC | SHORT | SCALP | RANGE_HIGH_VOL | 2 | 50.0 | 1.298 | 0.362 | 0.067 | 100.0 |
| half_timeout_v1 | BTC | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 11.8 | 0.039 | -1.689 | 0.287 | 88.2 |
| baseline_unchanged | BTC | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 3 | 33.3 | 0.416 | -5.394 | 0.314 | 33.3 |
| baseline_unchanged | BTC | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 3 | 33.3 | 0.951 | -0.305 | 0.247 | 66.7 |
| baseline_unchanged | BTC | SHORT | DAY TRADE | RANGE_NORMAL_VOL | 2 | 50.0 | 2.928 | 4.317 | 0.130 | 100.0 |
| price_retest_v1 | BTC | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 1 | 0.0 | 0.000 | -5.267 | 0.178 | 100.0 |
| price_retest_v1 | BTC | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 1 | 100.0 | NO_LOSSES | 19.153 | 0.120 | 0.0 |
| half_r_target_v1 | BTC | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 4 | 25.0 | 0.154 | -6.980 | 0.421 | 50.0 |
| half_r_target_v1 | BTC | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 3 | 33.3 | 0.441 | -3.476 | 0.247 | 66.7 |
| half_r_target_v1 | BTC | SHORT | DAY TRADE | RANGE_NORMAL_VOL | 2 | 50.0 | 2.764 | 3.951 | 0.130 | 50.0 |
| half_timeout_v1 | BTC | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 4 | 25.0 | 0.533 | -2.528 | 0.226 | 75.0 |
| half_timeout_v1 | BTC | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 3 | 0.0 | 0.000 | -6.549 | 0.242 | 100.0 |
| half_timeout_v1 | BTC | SHORT | DAY TRADE | RANGE_NORMAL_VOL | 2 | 50.0 | 0.187 | -3.891 | 0.120 | 100.0 |
| baseline_unchanged | ETH | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 5.573 | 0.043 | 100.0 |
| baseline_unchanged | ETH | LONG | SCALP | RANGE_NORMAL_VOL | 16 | 12.5 | 0.059 | -2.380 | 0.381 | 75.0 |
| baseline_unchanged | ETH | LONG | SCALP | UPTREND_NORMAL_VOL | 15 | 13.3 | 0.209 | -1.512 | 0.229 | 86.7 |
| baseline_unchanged | ETH | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 50.0 | 6.281 | 5.952 | 0.081 | 100.0 |
| baseline_unchanged | ETH | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 18 | 33.3 | 0.797 | -0.477 | 0.249 | 83.3 |
| baseline_unchanged | ETH | SHORT | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 14.330 | 0.018 | 0.0 |
| baseline_unchanged | ETH | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 35.3 | 0.402 | -1.330 | 0.240 | 58.8 |
| price_retest_v1 | ETH | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 5.244 | 0.043 | 100.0 |
| price_retest_v1 | ETH | LONG | SCALP | RANGE_NORMAL_VOL | 4 | 0.0 | 0.000 | -2.281 | 0.092 | 100.0 |
| price_retest_v1 | ETH | LONG | SCALP | UPTREND_NORMAL_VOL | 3 | 66.7 | 6.454 | 1.120 | 0.044 | 100.0 |
| price_retest_v1 | ETH | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 3 | 33.3 | 0.919 | -0.094 | 0.064 | 66.7 |
| price_retest_v1 | ETH | SHORT | SCALP | RANGE_NORMAL_VOL | 5 | 20.0 | 0.307 | -2.270 | 0.118 | 60.0 |
| half_r_target_v1 | ETH | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 5.451 | 0.043 | 0.0 |
| half_r_target_v1 | ETH | LONG | SCALP | RANGE_NORMAL_VOL | 16 | 12.5 | 0.030 | -2.358 | 0.377 | 68.8 |
| half_r_target_v1 | ETH | LONG | SCALP | UPTREND_NORMAL_VOL | 18 | 27.8 | 0.260 | -1.535 | 0.278 | 61.1 |
| half_r_target_v1 | ETH | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 50.0 | 5.400 | 4.958 | 0.074 | 50.0 |
| half_r_target_v1 | ETH | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 21 | 42.9 | 0.477 | -1.213 | 0.300 | 57.1 |
| half_r_target_v1 | ETH | SHORT | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 6.446 | 0.000 | 0.0 |
| half_r_target_v1 | ETH | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 35.3 | 0.249 | -1.572 | 0.270 | 41.2 |
| half_timeout_v1 | ETH | LONG | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 1.737 | 0.025 | 100.0 |
| half_timeout_v1 | ETH | LONG | SCALP | RANGE_NORMAL_VOL | 16 | 6.2 | 0.023 | -2.165 | 0.346 | 93.8 |
| half_timeout_v1 | ETH | LONG | SCALP | UPTREND_NORMAL_VOL | 16 | 18.8 | 0.173 | -1.687 | 0.270 | 87.5 |
| half_timeout_v1 | ETH | SHORT | SCALP | DOWNTREND_HIGH_VOL | 2 | 50.0 | 5.396 | 4.034 | 0.081 | 100.0 |
| half_timeout_v1 | ETH | SHORT | SCALP | DOWNTREND_NORMAL_VOL | 21 | 38.1 | 0.941 | -0.090 | 0.166 | 90.5 |
| half_timeout_v1 | ETH | SHORT | SCALP | RANGE_HIGH_VOL | 1 | 100.0 | NO_LOSSES | 14.330 | 0.018 | 0.0 |
| half_timeout_v1 | ETH | SHORT | SCALP | RANGE_NORMAL_VOL | 17 | 23.5 | 0.390 | -1.175 | 0.212 | 76.5 |
| baseline_unchanged | ETH | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 2 | 0.0 | 0.000 | -4.615 | 0.167 | 100.0 |
| baseline_unchanged | ETH | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 3 | 66.7 | 1.653 | 5.465 | 0.362 | 66.7 |
| price_retest_v1 | ETH | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 1 | 0.0 | 0.000 | -1.217 | 0.054 | 100.0 |
| half_r_target_v1 | ETH | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 2 | 0.0 | 0.000 | -4.615 | 0.167 | 100.0 |
| half_r_target_v1 | ETH | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 4 | 75.0 | 1.355 | 2.229 | 0.382 | 50.0 |
| half_timeout_v1 | ETH | LONG | DAY TRADE | UPTREND_NORMAL_VOL | 3 | 0.0 | 0.000 | -5.739 | 0.179 | 100.0 |
| half_timeout_v1 | ETH | SHORT | DAY TRADE | DOWNTREND_NORMAL_VOL | 4 | 50.0 | 1.358 | 1.787 | 0.293 | 75.0 |
