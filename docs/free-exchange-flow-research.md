# Free BTC/ETH exchange-flow investigation

Checked October 11, 2026. Raw public responses and transport errors are saved in
`free-exchange-flow-probes-2026-10-11.json`. Reproduce with
`scripts/investigate_free_exchange_flows.py`; the bounded probe uses four workers,
12-second request timeouts, TLS verification, inherited proxy settings, no
supplied API keys and no redirect following. It does not approve any provider.

## Result

No new reliable free feed for the dashboard's required fresh exchange-flow safety
input was verified. This is a conclusion about the sources tested and current
access, not proof that no free source exists anywhere. Preserve required exchange
flows as UNAVAILABLE and overall risk as UNKNOWN — INCOMPLETE DATA; NO TRADE
remains active. Existing daily Coin Metrics context remains available with
provisional labels. HIGH/EXTREME observed risk is retained independently.

## Coin Metrics: actual public API responses

`community-api.coinmetrics.io/v4/timeseries/asset-metrics` returned HTTP 200 for
separate `assets=btc` and `assets=eth` requests with
`FlowInExNtv,FlowOutExNtv`, frequency `1d`. Each returned three consecutive daily
observations for October 8–10; the latest interval starts October 10 at 00:00 UTC
and ends October 11 at 00:00 UTC. At the October 11 approximately 22:41 UTC check,
that daily observation start was about 46.7 hours old, and the interval end about
22.7 hours old. Neither timestamp is a current scalp observation.

The metric catalog returned HTTP 200 and defines:

- Inflow: native units sent to exchanges that interval, excluding exchange-to-exchange activity.
- Outflow: native units withdrawn from exchanges that interval, excluding exchange-to-exchange activity.
- Attribution: activity of addresses currently known to belong to the entity,
  from each address's first non-zero balance. This does not independently prove
  wallet ownership, address-list completeness or complete exchange coverage.
- Units: Native units. BTC requests report BTC; ETH requests report ETH.
  These are aggregates across labelled exchanges **for one asset**, not totals
  mixing all assets, USD valuations, exchange reserves or trading volume.

All returned inflow/outflow values were `flash`. Publication timestamps for the
latest BTC metrics were approximately 02:41 UTC October 11, and ETH approximately
01:51–02:19 UTC. Exact timestamps and string values are preserved in the evidence.
Finality and complete attribution are not established. Net inflow is calculated
only as inflow minus outflow within the same asset, scope and completed daily
interval. A positive result is not a trading recommendation. No netflow is derived
from reserve changes, prices, balances or trading volume.

Kraken-specific `FlowInKRKNtv,FlowOutKRKNtv` requests returned **publisher HTTP
403** for both BTC and ETH, with a JSON forbidden/credentials-entitlement error.
These are not environment proxy failures. Their values and free availability
cannot be verified. The existing Kraken diagnostics remain unavailable.

The first filtered legacy `catalog/asset-metrics` request returned HTTP 400
because `assets` is unsupported. A corrected parameter-free request returned
HTTP 200; relevant metric definitions were retained in the evidence. The catalog
lists only daily BTC/ETH exchange aggregate metrics, not free Kraken-specific
metrics. Catalog visibility alone never certifies actual interval coverage.

Observed response headers included `x-ratelimit-plan: download`,
`x-ratelimit-limit: 6000, 6000;w=20;comment="sliding window"`,
`x-ratelimit-reset: 20`, and varying remaining counts. These are response-header
observations, not a guaranteed free-tier contract or a target request rate. No
quota exhaustion was attempted. Routine dashboard caching remains in place;
errors/429s remain unavailable and never become zero flows. The investigator
records Retry-After/rate headers and never retries a throttled probe.

## DefiLlama and other candidates

| Candidate | Probe result | What remains unverified |
|---|---|---|
| DefiLlama CEX dashboard, public Binance CEX protocol candidate and API docs | Environment proxy CONNECT 403 | Payload, wallet lists, native asset breakdown, historical interval flows, update time, rate limits and free API entitlement |
| Glassnode exchange transfer metric and docs | Environment proxy CONNECT 403 | Actual schema, free/key requirements, BTC/ETH coverage, attribution, finality, latency and limits |
| CryptoQuant exchange inflow candidate and docs | Environment proxy CONNECT 403 | Current endpoint/schema, free/key requirements, asset coverage, ownership labels, freshness and limits |
| Mempool BTC block metadata | Environment proxy CONNECT 403 | Response not checked; block/transaction metadata alone would not certify exchange ownership or provide ETH flows |
| Etherscan ETH supply candidate | Environment proxy CONNECT 403 | Response not checked; supply/explorer observations are not independently attributed exchange netflows or BTC coverage |

The DefiLlama `/protocol/binance-cex` URL is a candidate CEX protocol/reserve
resource, not a verified BTC/ETH native netflow API. Do not promote TVL, reserve
changes, USD CEX totals, chain totals or DEX/trading volume to asset-specific
exchange netflows. No DefiLlama API schema or free exchange-flow coverage is
claimed from a blocked request. The same caution applies to community exchange
wallet lists and raw explorers: transactions can be observed without proving
ownership, complete label coverage, internal wallet transfers or indexing finality.

## Exact domains for further investigation

No Internet permissions were modified. Rechecking blocked candidates would need:

```text
api.llama.fi
defillama.com
api-docs.defillama.com
docs.coinmetrics.io
api.glassnode.com
docs.glassnode.com
api.cryptoquant.com
userguide.cryptoquant.com
mempool.space
api.etherscan.io
```

These are investigation hosts, not guaranteed working/free data sources. No
wildcards or unobserved redirected/API hosts are recommended. `api.github.com`
is separately required for the GitHub CLI draft-PR operation, not market data.
Adding domains cannot resolve Coin Metrics' Kraken metric entitlement denial.

## Application and tests

The daily context and existing Kraken diagnostics now explicitly carry
`safety_status=UNAVAILABLE`, `safety_eligible=False`, asset units and scope; the
context also exposes unverified coverage/attribution. The UI explains the
separation from required fresh flows. Diagnostic net inflow subtracts only the
same-asset inflow/outflow. Boolean amounts, reserve/volume substitutions,
wrong-asset rows and remaining pagination are rejected. No new source is used
as a signal input. All existing feeds/features and protections are preserved.

Tests cover BTC and ETH identity, units, pagination, malformed amounts, true zero
observations versus missing data, diagnostic net inflow, blocked/429 probes,
explicit unavailable safety status, and HIGH/EXTREME observed risk remaining
visible while overall risk is UNKNOWN and signals NO TRADE. Run the full suite:

```bash
RUN_LIVE_INTEGRATION=1 .venv/bin/python -m unittest discover -s tests -v
```

After access is permitted, re-probe actual payloads and documentation, establish
attribution methodology/coverage and rate limits, and certify completeness,
publication timestamps and revision/finality behavior before designing an
adapter. Until then do not infer figures, treat missing values as zero, unlock
ENTER, activate alerts, merge or deploy.
