# Ingesting `github_repos`: dlt vs Airbyte vs custom client

- **Date:** 2026-07-23 · **Refs:** OGIP#18, OGIP#19
- **Source:** `spec/sources/games/github_repos.yaml` (certified Airbyte fit, per the 2026-07-20 refit audit)
- **Companion:** `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`

## Why "custom scraping" is not on the table for GitHub

GitHub exposes complete REST and GraphQL APIs returning the same data structured. HTML scraping
would yield worse data at higher cost, break on every redesign, and violate ToS. OGIP already
splits `ApiSource` from `ScraperSource` (`ingestion/base/`); GitHub is unambiguously the former.
So the third option below is a **custom `ApiSource` client**, not literal scraping — which loses
on every axis and is excluded.

## The dlt caveat, verified

dlt's *verified* GitHub source (`dlthub.com/docs/dlt-ecosystem/verified-sources/github`, checked
2026-07-23) covers only `github_reactions` (GraphQL, full refresh) and `github_repo_events` (REST,
incremental on `created_at`). **None** of the six streams the descriptor needs — `repositories,
releases, stargazers, issues, commits, contributors` — is covered. "dlt" here therefore means
`rest_api` + hand-written configs, not a ready source.

## Comparison

| Axis | dlt (`rest_api`) | Airbyte (`source-github`) | Custom `ApiSource` |
|---|---|---|---|
| Ready-made coverage | verified source useless → write 6 stream configs | 39 streams, 26 incremental, out of the box | write everything |
| Start-up complexity | medium | **high** — abctl (k8s-in-docker) + Terraform + an OAuth app | medium |
| Complexity at stream #6 | linear growth | **~zero** — a stream is a config line | linear growth |
| GraphQL (`releases`) | hand-rolled, a second paradigm | inside the connector | hand-rolled |
| Rate limits | our code | multi-PAT rotation + throttling, waits ≤240 min | our code |
| Incremental state | dlt state, our cursor schema | per-repo × per-stream, internal | fully ours |
| Who fixes an API break | us | Airbyte (certified, GA) | us |
| Monitoring | Prefect flow → **existing obs stack** | own k8s/UI/logs → **not in obs** | Prefect flow → **existing obs stack** |
| Runtime weight | a process | a cluster | a process |
| ADR-0006 fit | ✅ default engine | ❌ `experimental/` only | ✅ |

## The axes where the difference is non-obvious

**Capabilities** — Airbyte's one large, honest win: 39 streams vs the 6 we would write, REST+GraphQL
internal. A future need for `workflow_runs`/`pull_request_stats` is a config line for Airbyte and a
sprint for the other two.

**Support & evolution** — Airbyte versions the connector independently; updates arrive without us,
but so do breakages. dlt/custom: we own the code — slower, but every failure is ours and
diagnosable. Note `source-github` is the *only* connector of 591 that is simultaneously certified,
real code (Python CDK, not manifest-only), and reads public data. A rare exception, not the norm.

**Stability & monitoring — Airbyte's worst axis.** OGIP already runs an obs stack
(VictoriaMetrics/Loki/Alloy/Grafana) + alerting; dlt and custom land in it automatically because
they live inside Prefect flows. Airbyte is a separate cluster with its own UI, logs, and notion of
"sync failed" — routing its failures to the same dashboards/alerts needs an integration that does
not exist. For a platform whose observability is a headline feature, that is not minor.

## SWOT

**dlt (`rest_api`)** — S: default engine (ADR-0006), one runtime, auto-observable, declarative for
REST. W: verified source misses our streams; `releases` GraphQL breaks the declarative story; rate
limits are ours. O: streams grow within the existing source pattern, reused across the other 17
sources. T: "declarative" quietly becomes a typed client we maintain — the exact cost the Airbyte
lane claimed to remove.

**Airbyte (`source-github`)** — S: 39 streams, REST+GraphQL, token rotation, throttling, external
maintenance, certified/GA. W: k8s-in-docker; outside obs; off the `make` path; a whole Terraform
layer; OSS is PAT-only. O: the one source that justifies the lane; yields a measured rather than
theoretical tool verdict. T: the whole case rests on one connector; if it degrades the lane loses
its rationale. Direct conflict with the client brief: *"not wiring managed connectors"*.

**Custom `ApiSource`** — S: full control, precise typing, in obs, zero new runtime, matches what
the client calls the actual job. W: we write pagination, GraphQL, rate limits, and state; costliest
per stream. O: demonstrates exactly the bought skill ("resilient retrieval"). T: reinvents dlt's
REST half; "control" risks being mere duplication.

## Recommendation

Split the roles rather than crown a winner:

- **Product path → dlt.** Six streams: five pure REST via `rest_api`, `releases` a separate GraphQL
  resource. ADR-0006-compliant, in obs, no cluster.
- **Airbyte → keep as the experiment it is.** Its value is not better ingestion; it is the one
  honest measurement of where a maintained connector objectively wins (39 streams, two paradigms,
  token rotation) and why we still keep it out of prod (observability, runtime weight, client
  brief). That is the "architect's eye" the engagement asks for.
- **Custom `ApiSource` → not for GitHub.** Its place is where no API exists — the scrape tail
  (SteamCharts, Metacritic, …).
