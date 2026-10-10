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
