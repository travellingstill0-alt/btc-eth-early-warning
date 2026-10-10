# Provider access diagnosis and Android setup

## Diagnosis

The current environment reports **restricted, enforced network access**. Its custom approved hosts cover Binance, Coinbase, Kraken and Deribit; dependency/source-control presets explain why GitHub documentation is reachable. There are no configured provider credentials or runtime variables.

Fresh runtime tests: Kraken Time HTTP 200; Coinbase time HTTP 200; Coin Metrics official documentation on GitHub HTTP 200; Binance Futures time HTTP 451 with restricted-location text. Both BTC/ETH Coin Metrics requests and all 16 macro requests received proxy CONNECT 403 Forbidden **before any provider HTTP response**. These are destination-policy denials, not proven provider 403s, expired keys or unsupported URLs. The denial explains the immediate failure; it cannot tell us what the provider would return after authorized access.

BLS CPI, Fed October and BOJ release pages could be read through the separate documentation browser. That is not runtime calendar verification. No proxy/TLS setting was changed and no denied destination was reached through an alternate route.

Secondary limitations remain: free Coin Metrics exchange-metric entitlement/coverage is unverified, daily flow observations cannot satisfy the 180-second safety requirement, and several macro pages need dedicated parsers. They are HTML schedules, not interchangeable JSON APIs. No production calendar adapter is approved. BOJ timing may be undecided; full speech/unscheduled-event coverage and previous/forecast/actual figures remain missing. Access alone cannot clear NO TRADE.

## Exact endpoints and permissions

All current endpoints below require **outbound HTTPS 443 and GET**, with **no API key**. Environment editing permission is needed to add hosts; organization Agent Security may require an administrator. No inbound ports, VPN or private exchange account/trading/withdrawal permissions are needed.

Coin Metrics Community: `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics`.
Two separate GET requests use `assets=btc` or `assets=eth`, `metrics=FlowInKRKNtv,FlowOutKRKNtv`, `frequency=1d`, `limit_per_asset=2`, `page_size=2`, `sort=desc`. This probes Kraken-labelled native-unit daily flows, not whole-market verified flows.
[Community access documentation](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data) confirms no key for the free subset. Documentation versions differ on API root; validate the current catalog before changing the implemented root or claiming entitlement.

| Calendar source | Exact configured GET URL | Key |
| --- | --- | --- |
| BLS | https://www.bls.gov/schedule/news_release/bls.ics | None |
| ISM | https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar | None |
| ECB | https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html | None |
| BOJ | https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm | None |
| FED:2026-09 | https://www.federalreserve.gov/newsevents/2026-september.htm | None |
| FED:2026-10 | https://www.federalreserve.gov/newsevents/2026-october.htm | None |
| FED:2026-11 | https://www.federalreserve.gov/newsevents/2026-november.htm | None |
| ECB_SPEECH | https://www.ecb.europa.eu/press/calendars/weekly/html/index.en.html | None |
| EUROSTAT | https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar | None |
| SPGLOBAL | https://www.pmi.spglobal.com/Public/Release/ReleaseDates?language=en | None |
| DESTATIS | https://www.destatis.de/EN/Press/Dates/Weekly-Preview/_node.html | None |
| BOE | https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates | None |
| ONS | https://www.ons.gov.uk/releasecalendar?release-type=type-upcoming | None |
| BOJ_SPEECH | https://www.boj.or.jp/en/about/calendar/index.htm | None |
| CHINA_NBS | https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/ | None |
| PBOC | https://www.pbc.gov.cn/en/3688229/3688335/3730276/index.html | None |

Fed URLs roll with the month; these three are the actual October 2026 test targets. Redirects are not automatically followed. Any redirect destination needs separate inspection/authorization.

All additional destination hosts needed for the current probes:

```text
community-api.coinmetrics.io
ec.europa.eu
www.bankofengland.co.uk
www.bls.gov
www.boj.or.jp
www.destatis.de
www.ecb.europa.eu
www.federalreserve.gov
www.ismworld.org
www.ons.gov.uk
www.pbc.gov.cn
www.pmi.spglobal.com
www.stats.gov.cn
```

## Optional paid providers — not needed now

| Provider | Documented endpoints | Credential / entitlement |
| --- | --- | --- |
| CryptoQuant | `https://api.cryptoquant.com/v1/btc/exchange-flows/inflow`, `https://api.cryptoquant.com/v1/btc/exchange-flows/outflow`, `https://api.cryptoquant.com/v1/eth/exchange-flows/inflow`, `https://api.cryptoquant.com/v1/eth/exchange-flows/outflow` | CryptoQuant-issued **data API key** in `Authorization: Bearer …`. On-chain entitlement Professional/Premium; Professional daily, Premium hourly/per-block where supported. Free Basic excludes on-chain flows. |
| Glassnode | `https://api.glassnode.com/v1/metrics/transactions/transfers_volume_to_exchanges_sum`, `https://api.glassnode.com/v1/metrics/transactions/transfers_volume_from_exchanges_sum` | Glassnode-issued **data API key**, documented `api_key` parameter; appropriate exchange-metric and BTC/ETH resolution entitlement must be confirmed. Never log key-bearing URLs. |

Sources: [CryptoQuant access/authentication](https://cryptoquant.com/apis), [BTC endpoints](https://userguide.cryptoquant.com/api/btc-exchange-flows), [ETH endpoints](https://userguide.cryptoquant.com/api/eth-exchange-flows), [Glassnode endpoints/authentication](https://docs.glassnode.com/basic-api/endpoints/transactions).

Neither optional provider is integrated or was called/purchased. No suitable subscription price was established. Do not configure keys now: the current application has no adapter using them. If later authorized with existing data access, use an environment network secret scoped to the exact HTTPS provider domain, not chat or GitHub. Private Binance/Kraken/Coinbase trading keys are never required. No OpenAI API key is required for this diagnosis/configuration.

## Android guide: two-host first step

1. Open Chrome on Android and sign into ChatGPT with the same account/workspace. If needed, Chrome **⋮ → Desktop site** can expose the web settings. Availability on this account's Android interface is not verified.
2. Open **Settings → Codex Cloud → Environments**, find the environment used by the dashboard task, and select its **… → Edit** action. If settings/edit permission are absent, the environment/workspace owner must perform this change. Changing phone Wi-Fi or browser permissions will not change the cloud proxy.
3. In the environment configuration, enable **Allow Codex to access internet**, retain restricted access with the existing market/dependency hosts, and add just `www.bls.gov` and `community-api.coinmetrics.io` under **Additional allowed domains**. Use Package managers plus additional domains, or the equivalent existing restricted policy.
4. If method controls are available, permit GET; HEAD/OPTIONS can be allowed for diagnostics. No feed needs POST/PUT/DELETE or a private exchange permission. An organization policy may require an administrator to approve destinations.
5. Save/review and test the development configuration. If required by the environment workflow, republish the development environment configuration and start a new task using it. This prepares the development workspace; it does not publish the dashboard. Existing tasks may retain their prior state.
6. In the new task send: **“Verify the applied policy and test public BLS and Coin Metrics BTC/ETH responses through the approved proxy. Keep NO TRADE. Do not merge, deploy, buy subscriptions or enable trading.”** No key or billing setup is needed.

The Settings/menu labels and save/republish/new-task workflow are documented in [OpenAI Cloud environment configuration](https://learn.chatgpt.com/docs/environments/cloud-environments). The Chrome desktop-view step is a mobile navigation suggestion, not a verified screenshot of this account. The [legacy Codex web internet-access page](https://learn.chatgpt.com/docs/cloud/internet-access) documents per-environment allowlists and HTTP-method restrictions; use the interface applicable to the attached environment.

## Verification and safest next step

After setup, recheck that the desired network policy is actually enforced, then inspect the returned feed bodies and entitlement/schema/completeness/freshness. HTTP 200 does not make the data verified. Add more hosts individually as dedicated adapters are ready.

Existing live checkers: `.venv/bin/python scripts/check_macro_sources.py` and `.venv/bin/python scripts/check_exchange_flow_apis.py`. New diagnosis: `.venv/bin/python scripts/diagnose_provider_access.py`. Macro/flow checkers correctly fail when verification cannot be completed; a successful diagnostic-script exit only means its investigation was recorded.

A diagnostic fix preserves the original calendar transport error instead of incorrectly showing an invalid timestamp when no response arrived. It does not relax safety. **NO TRADE stays active.** Cost incurred: **$0**. No subscription, private trading key, merge, deployment, automation or external notification was enabled.

**Simplest safe next step: approve only the two public no-key hosts in the development environment, then rerun live checks.**

Validation: all **92 tests passed**, including the regression for original transport-denial reporting and all existing NO TRADE gates. `git diff --check` passed. Raw diagnostic evidence contains only public requests made without credentials.
