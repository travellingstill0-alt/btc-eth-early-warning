# Integration validation

Validated on 2026-10-10. Local integration branch: `integration/oi-history-provider-fallback`.

`feature/public-provider-fallback` at `a8ec8bb840aa3b4e9eb86eb1446cdc07a33b9774` is already an ancestor of `feature/persistent-oi-history` at `7fe614f39afaa3685972d218d8a13af0cd2cd5ce`. Integration therefore fast-forwards from main (`c16faeb`) to the OI history commit; no conflict resolution or duplicated implementation is needed.

Validation:

- `.venv/bin/python -m unittest discover -s tests -v`: 42 tests passed, including Streamlit AppTest, risk/macro gates, stale/missing inputs, provider fallback, OI isolation, persistence, concurrency and warm-up.
- `.venv/bin/python scripts/check_public_apis.py --history-db work/integration-live.sqlite3 --output work/integration-live.json`: exit 0. All actual HTTP requests returned 200. Primary outages in fallback scenarios were simulated; secondary responses were real.
- Normal BTC and ETH observations supplied 15m, 1h, 4h and 24h verified Kraken OI changes. Both informational panels returned WAIT with the check script's simulated macro acknowledgement.
- Spot fallback lacked rolling 24h price change; Deribit and history-only fallback lacked sufficient stored coverage. Both panels returned NO TRADE in every such case.
- `git diff --check`: passed.

The real UI still defaults to unchecked macro review. Provider, contract and unit histories remain separate. No synthetic observations, trading operations, background collectors or alerts were added. No deployment, automated trading, remote branch update or main merge was performed. These checks establish point-in-time connectivity and deterministic behavior, not a multi-hour persistence soak or sustained provider uptime.

Streamlit emitted upstream NumPy timedelta deprecation warnings during AppTest; tests completed successfully.

## Safety corrections after PR review

The earlier WAIT results above describe the original integration. The revised policy requires CVD, liquidation data and exchange flows; no verified integrations exist, so both panels now remain NO TRADE. Arbitrary context payloads cannot unlock them.

Assessments carry an evaluation epoch timestamp, rules and an input digest. Signal generation rejects expired, future, missing or changed-input assessments and reassesses all inputs at decision time. Provider timestamps require valid timezone-aware ISO values or finite, positive, representable epoch values. Invalid timestamps trigger provider fallback or missing-input protection; legitimate fractional trade seconds and ISO microseconds retain millisecond precision.

Regression coverage includes mandatory context on both panels, expired/future assessments, changed inputs, source-age boundary crossings, primary/secondary malformed timestamps, fractional timestamp precision and JSON diagnostics compatibility. Existing UI tests now expect NO TRADE even after macro acknowledgement and selecting a shorter OI lookback.

Final validation: 51 tests passed; git diff --check passed. The read-only live check exited 0 across eight BTC/ETH primary/fallback scenarios. Every actual API request returned HTTP 200; all sixteen panels returned NO TRADE. Normal Kraken history still supplied all four OI windows. No deployment, merge or automated trading occurred.
