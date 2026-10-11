# Independent workstreams

Track A (priority): branch `mobile/android-dashboard`, based on research commit
`a1651944de21b06ffb267eac59cdf015ab94ee1c`. Owns `mobile_app.py`,
`mobile_support.py`, `mobile/`, `tests/test_mobile.py`, `docs/mobile/`.

Track B: branch `research/loss-diagnostics`. Owns research engines, experimental
configurations and versioned research artifacts. Existing entry/exit comparisons,
chronological test and walk-forward results remain preserved in confirmation-v1.
No new strategy experiment was run during this mobile iteration. Baseline rules
remain unchanged. Historical CVD/OI publication availability remains insufficient
for a verified full-context entry backtest. Final test week has been inspected;
a future unseen period is needed for independent validation.

Track A reads frozen research CSVs; it never rewrites them. Shared market,
analysis and calendar adapters require coordinated changes. Neither branch is
merged or deployed. NO TRADE remains locked; trading, live signals and
notifications remain disabled.

## Local preview and Android

From the repository, run:

```sh
.venv/bin/streamlit run mobile_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501 on the machine running the application.
This session's server is loopback-only in a remote cloud workspace. Android's
localhost is the phone, so that URL cannot reach this workspace from Android.
No private forwarding capability or VPN is configured for this session.

For a phone preview without public deployment, run the repository on your own
computer on the same trusted Wi-Fi as your Android phone. Change the address to
`0.0.0.0`, allow port 8501 only from the local network in your firewall, and open
`http://YOUR-COMPUTER-LAN-IP:8501` in Android Chrome. Do not port-forward your
router. Stop the server after testing. HTTPS and authentication are required
before remote/mobile deployment. Chrome Add to Home screen can create a shortcut;
this is not yet an offline PWA or a native Android app.

## Notifications

Seven categories have synthetic in-page previews: BTC LONG/SHORT, ETH LONG/SHORT,
HIGH/EXTREME risk, high-impact macro. No push transport, browser permission,
subscription, sender keys or live signal generation is implemented. Production
Android Web Push needs HTTPS, a root-scope service worker, explicit consent,
a delivery backend and separate approval. All notifications remain disabled.

## Data and safety

Reuses existing verified public adapters and source provenance. Values older
than 180 seconds, unknown timestamps, future timestamps and nonfinite numbers
are unavailable in live market metrics. CVD/liquidations are validated raw
15-minute completed windows. Units/contracts are separate. Independent warnings
remain separate from profitability. LOW observed risk with missing coverage is
explicitly INCOMPLETE and never an all-clear. Regional calendars are partial;
Japan/China are separated by event kind from the existing ASIA adapter.
Collection occurs during active refreshes only; closed sessions create gaps.
Existing immutable SQLite observation stores are preserved, not reset.

## Hosting preparation: budget ceiling $25/month

The provider and specifications behind the user's $7.20/$14.40 options were not
found in saved documentation. These are user-supplied prices, not verified quotes.
No purchase, deployment, invoice or external service was created.

| Option | Quoted base | Remaining under $25 | Status |
|---|---:|---:|---|
| A | $7.20 | $17.80 | Provider/RAM/CPU/storage/tax/traffic unknown |
| B | $14.40 | $10.60 | Provider/RAM/CPU/storage/tax/traffic unknown |

Both totals must include tax, backups, storage, bandwidth and any monitoring.
Do not infer resources from price. Existing data directory was 208 KiB before
this preview; historical artifacts must be budgeted separately. Measure process
RSS under real sessions and collection; a single-session sample is not a capacity
guarantee. Plan a persistent disk for SQLite, snapshot-consistent SQLite backups,
encrypted off-host copies, retention and a restore test. Backup prices remain
unverified. Free certificate software does not establish zero hosting/backup cost.

Before approval: identify provider plans and verify official resource/cost quotes;
load-test concurrent sessions and persistent collection; configure authentication,
firewall, HTTPS reverse proxy and WebSocket forwarding; pin dependencies and
review updates; test backup/restore and physical Android behavior. Public-access
configuration must stay pending explicit deployment approval.
