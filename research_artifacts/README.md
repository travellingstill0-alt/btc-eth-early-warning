# Persistent research index

Start here when resuming this project. The research branch is
`research/loss-diagnostics` in `travellingstill0-alt/btc-eth-early-warning`.
NO TRADE remains locked. No execution or notification functionality is enabled.
No paid services, deployment or merge is authorized.

- `recovery-v1/REPORT.md`: scope, recovered rules, missing ledger and reproduction blockers.
- `recovery-v1/commits.txt`, `remote-refs.txt`, `historical-paths.txt`, `blob-search.json`: Git search evidence.
- `recovery-v1/issues.json`, `github-discussions.json`, `workflow-artifacts.json`, `releases.json`: GitHub recovery evidence.
- `recovery-v1/original-analysis.py.txt`: original rules, copied from commit `9270990c213ad8258b4aa486cd9e5884a94db647`.
- `recovery-v1/ledger-status.json`: explicit missing-ledger status. `records: null` means missing, not zero trades.
- `recovery-v1/candidate-diagnostics.json`: descriptive price-only signal observations. Never treat these as backtest trades.
- `recovery-v1/tests.txt`: full test summary.
- `history-v1/`: raw Coinbase responses with request parameters and hashes, validated candles and unexecuted signal candidates.
- `collection-v1/`: real CVD/liquidation windows, local OI snapshots, collection gap report and live safety checks.
- `manifest-v1.json`: SHA-256 hashes for archived files. No credentials or test fixture databases are archived.

Do not overwrite historical artifacts. Use `history-v2`, `collection-v2`, etc.
New collection data belongs to its real provider/contract/unit and observation
period. Do not add zero-filled rows or claim continuous coverage across gaps.
Exports are snapshots, not replacements for the runtime SQLite stores.
The Git branch preserves these exports across workspace replacement; an inactive
page still does not collect new data. The local live databases themselves need
persistent disk or a separately approved backup service.

To resume after fetching this branch, install `requirements.txt`, inspect
`recovery-v1/REPORT.md`, and run the fixture-isolated test command in the README.
Read-only collection is `market.fetch('BTCUSD')` / `market.fetch('ETHUSD')`;
these calls use public feeds and save verified local OI/CVD/liquidation data.
`python scripts/recover_history.py --output research_artifacts/history-v2`
archives a new completed seven-day Coinbase candle window. This is not a
reproduction of the original unavailable backtest.
