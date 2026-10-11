# CVD and liquidation provider investigation

Investigated on 2026-10-10. Only public GET requests were used; no keys, purchases, orders, background collectors or deployment. This extends Draft PR #2 and supersedes its earlier statement that CVD/executed-liquidation observations were wholly unavailable. Exchange flows remain unavailable and continue to block both panels.

## Selected integrations

| Input | Primary | Fallback | Scope and units |
| --- | --- | --- | --- |
| 15-minute CVD | Kraken Futures `analytics/{symbol}/cvd` | Complete Deribit `public/get_last_trades_by_instrument_and_time` | Kraken PF_XBTUSD/BTC or PF_ETHUSD/ETH; Deribit BTC/ETH-PERPETUAL USD |
| 15-minute executed liquidation volume | Kraken Futures `analytics/{symbol}/liquidation-volume` | Complete Kraken `/derivatives/api/v3/history` | Same Kraken linear contract and native base units; executed events only |

[Kraken market analytics documentation](https://docs.kraken.com/api/docs/futures-api/charts/market-analytics) documents the public types, seconds-based intervals, timestamps and completeness flag. Real CVD responses used `buy_volume`/`sell_volume`; the published schema uses `buyVolume`/`sellVolume`. Both explicit versions are accepted; ambiguous fields are rejected. Completed minute starts and real cumulative increments were verified against returned buy/sell buckets. The displayed CVD resets at the shown window start; it is not an all-history cumulative level.

Kraken liquidation responses contain scalar volume buckets. A nonzero ETH minute reported `0.01`, matching a public `partial liquidation` execution size of `0.01` for the same minute. The BTC minute's 100-trade page was truncated and could not corroborate its entire `0.0036` total; no incomplete sum was substituted. No price conversion is performed. The public history response includes `sequence_id` and `partial liquidation` in addition to the fields/classifications in [the history documentation](https://docs.kraken.com/api/docs/futures-api/trading/get-history). These observed fields are explicitly validated; unfamiliar schema/classifications fail closed.

[Deribit documentation](https://docs.deribit.com/api-reference/market-data/public-get_last_trades_by_instrument_and_time) defines taker direction, trade sequence, time bounds and native USD trade amounts for the selected inverse perpetuals. CVD is an exact sum of the complete returned execution tape, not an estimate from candles or sampled spot trades. `has_more` must be false for every accepted subrange; disjoint range splitting avoids skipping trades sharing a timestamp. Actual response `usOut` timestamps are retained and checked. Seven requests maximum; saturation, sequence gaps or negotiated block/combo trades leave CVD unavailable.

Liquidation history fallback is bounded to ten 100-trade pages. It preserves provider timestamp precision when paging, deduplicates consistent inclusive-boundary overlaps, rejects conflicts and requires contiguous sequences and an observation before the window start. It cannot certify completeness if those checks fail. Both endpoints share Kraken's infrastructure; this provides endpoint fallback, not protection against an exchange-wide outage.

## Alternatives, costs and limitations

- Selected Kraken and Deribit requests succeeded without authentication or payment. No subscription/API charge was incurred. Public endpoints remain subject to rate limits, outages, regional restrictions and changing schemas. Bounded request budgets and existing session caching limit usage; no sustained uptime SLA is claimed.
- Binance futures klines were probed for BTCUSDT/ETHUSDT as an alternative CVD source. Both returned HTTP 451 for regional eligibility restrictions in this environment. No restriction was bypassed and this source was not added as a working fallback.
- Deribit's public liquidation flag is documented in the schema, but [its release notice](https://support.deribit.com/hc/en-us/articles/25944778989341-3-October-2023) says real-time public liquidation flags were removed. Absence of a flag is not evidence of zero liquidation activity; Deribit is therefore not used as a liquidation-volume fallback.
- [CoinGlass CVD](https://docs.coinglass.com/reference/futures-cvd-history) and [liquidation history](https://docs.coinglass.com/reference/liquidation-history) are potential keyed alternatives, not implemented or live-verified here. Its [pricing page](https://www.coinglass.com/pricing) advertises Hobbyist from $29/month ($348/year shown), Startup $79/month, Standard $299/month and Professional $699/month; confirm billing and endpoint entitlement before purchase. The published history table reserves minute-level history for Standard/Professional, with six/twelve days respectively. The cheapest plan should not be assumed sufficient for this dashboard. No paid access was enabled.
- Future liquidation-level heatmaps are separate from executed liquidation volumes. Estimated heatmaps, leverage assumptions, OI changes or price/volume proxies are not accepted as verified liquidation observations. No global CVD or global liquidation completeness is claimed.

## Validation

Unit and UI coverage checks signed CVD arithmetic, cumulative consistency, genuine zero liquidation buckets, missing/duplicate/future/active buckets, stale caches, provider/contract/unit separation, unknown schemas, non-finite values and overflow, complete Deribit tape, time-range splitting, rate limits/budget exhaustion, liquidation execution types, history boundaries, page overlap/conflicts, and NO TRADE with missing exchange flows.

Read-only primary and simulated-outage validation returned HTTP 200 for all actual context requests. Primary Kraken CVD/liquidation windows validated for both assets; real Deribit CVD fallback validated for both. ETH complete execution-history liquidation fallback validated. BTC sequence gaps were rejected, leaving liquidation data unavailable rather than implying zero. These are point-in-time observations, not guaranteed future fallback availability.

No merge, deployment or automated trading was performed. Exchange flows have no verified integration, and both panels remain NO TRADE regardless of macro acknowledgement.

Final results: 67 tests passed with `.venv/bin/python -m unittest discover -s tests -v`; `git diff --check` passed. `scripts/check_public_apis.py` exited 0 across eight end-to-end scenarios, with all sixteen panels returning NO TRADE. Both normal scenarios had fresh verified CVD/liquidations and exchange flows as the remaining missing input. `scripts/check_context_apis.py` exited 0 and recorded secondary coverage failures explicitly. Upstream Streamlit/NumPy timedelta deprecation warnings remain non-failing.
