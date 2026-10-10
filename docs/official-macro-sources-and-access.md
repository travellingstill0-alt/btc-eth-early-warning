# Official macro sources and restricted-network access

Checked October 10, 2026, approximately 17:53 America/Bogota. Evidence is in
`official-macro-access-2026-10-10.json`. Requests used inherited HTTPS proxy and
TLS verification, with redirects disabled. Internet permissions were not changed.
No economic figures, forecasts or event times were inferred or added.

## Current access

BLS Employment Situation schedule, Employment Situation release index and
BLS iCalendar returned HTTP 200. Every other source below failed at proxy
CONNECT with 403 Forbidden. This establishes an environment access blocker,
not a publisher outage. Page contents, current paths, redirects, calendar
schemas and timing on blocked sites remain unverified.

| Region | Institution / primary source | Purpose | Additional exact hostname |
|---|---|---|---|
| USA | Federal Reserve FOMC calendars and news/events | Decisions, minutes, meeting dates, speeches | `www.federalreserve.gov` |
| USA | BLS Employment Situation and release schedule | Official payroll/employment/unemployment releases | None: `www.bls.gov` already works |
| USA | ISM report release calendar | Manufacturing and Services PMI; primary survey publisher, not government | `www.ismworld.org` |
| USA | BEA release schedule | GDP, income/PCE and related national accounts | `www.bea.gov` |
| USA | Census economic indicators | Retail sales and other Census releases | `www.census.gov` |
| Europe | ECB Governing Council and weekly calendars | Monetary policy and speeches | `www.ecb.europa.eu` |
| Europe | Eurostat Euro-indicators release calendar | Official euro-area/EU inflation, GDP, employment and unemployment | `ec.europa.eu` |
| Europe | Destatis weekly release preview | German official releases, including labor-related coverage | `www.destatis.de` |
| Europe | S&P Global PMI release calendar | Primary PMI survey publisher, not government | `www.pmi.spglobal.com` |
| UK | BoE upcoming MPC dates | Monetary policy decisions; speeches need additional verification within the site | `www.bankofengland.co.uk` |
| UK | ONS release calendar | Official employment/labour-market, CPI and GDP releases | `www.ons.gov.uk` |
| Japan | BoJ monetary policy meetings and events | Policy meetings, statements, minutes and speeches | `www.boj.or.jp` |
| Japan | Statistics Bureau Labour Force Survey | Official employment and unemployment | `www.stat.go.jp` |
| Japan | MHLW English portal | Employment referrals/job openings and wage/employment statistics; specific release pages still need discovery | `www.mhlw.go.jp` |
| China | PBoC official English portal | Official policy notices and announcements; not a certified scheduled-decision calendar | `www.pbc.gov.cn` |
| China | NBS English portal/release calendar | Official macro releases and employment/unemployment statistics | `www.stats.gov.cn` |

## Hostnames to add

Use hostname entries, without URL schemes or paths. Keep existing entries.

```text
www.federalreserve.gov
www.ismworld.org
www.bea.gov
www.census.gov
www.ecb.europa.eu
ec.europa.eu
www.destatis.de
www.pmi.spglobal.com
www.bankofengland.co.uk
www.ons.gov.uk
www.boj.or.jp
www.stat.go.jp
www.mhlw.go.jp
www.pbc.gov.cn
www.stats.gov.cn
```

No wildcard or third-party CDN allowances are justified by these probes.
After these are allowed, inspect actual redirects and API/download destinations
and report any additional exact hosts before requesting changes. Existing
calendar adapters already reference Destatis and S&P Global, so these are
included even though S&P is not a government statistical office.

For GitHub CLI PR metadata operations, `api.github.com` is separately missing:
`gh pr view 2` failed with Forbidden at its GraphQL endpoint. Git transport
worked with the existing GitHub CLI credential helper, and the push plus
remote PR head were independently verified. This tooling domain is not a
macroeconomic source and is not required for the completed Git push.

## Coverage and safety limitations

- BLS access does not cover FOMC, ISM, BEA or Census releases, nor certify the
  complete US calendar. Event schedules and economic observations are separate.
- ECB/Eurostat access alone will not cover all European national calendars;
  additional national sources should follow explicit coverage requirements.
- BoE dates do not certify speech coverage. ONS releases require schema,
  revision and timezone checks.
- BoJ meeting schedules may provide dates without an exact statement release
  time. Japan employment sources are distinct from monetary policy sources.
- PBoC announcements can be unscheduled. Do not invent a regular decision time
  or infer no risk from an empty calendar. Chinese versus English publication
  currency and NBS employment definitions need verification.
- ISM and S&P survey calendars are primary publisher sources. Their licensing,
  release conventions and actual timezone wording must be reviewed.

Next: the user adds selected hosts and publishes the environment; a fresh task
then rechecks transport and redirects, validates official page schemas and
revision/freshness behavior, and implements or certifies adapters with fixture
and live tests. Date-only announcements remain timing-unverified; no guessed
release time or synthetic figures are permitted. The existing macro pre/post
windows, required context, OI history, source freshness and assessment integrity
checks remain intact. Daily Coin Metrics flows do not satisfy real-time context
requirements. NO TRADE stays active. No merge, deployment or trading enablement
was performed.
