# Airbyte + Terraform — evaluation lane

> **Experimental. Off the `make` path.** This lane **evaluates** Airbyte; it is not production
> ingestion. Product ingestion goes via **dlt**. Nothing here is wired into `make run`.

- **Tracker:** [#41](https://github.com/dataengy/ogip/issues/41) · task file `.ai/tasks/airbyte-evaluation-lane.md`
- **Design SSoT:** [`docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`](../../../docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md)
- **Plan:** [`docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md`](../../../docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md)
- **Techdebt:** [`docs/techdebt/airbyte-lane.md`](../../../docs/techdebt/airbyte-lane.md)

## Why this lane exists

A 591-source audit of the live OSS registry found **zero** Airbyte connectors for the games-market
domain's real sources (Steam, MobyGames, Gamalytic, SteamDB, HLTB, IGDB, itch, Epic, GOG, PSN, Xbox,
Nintendo, Kickstarter). The lane therefore evaluates the tool on the **one** case that genuinely
earns it — `github_repos` via `airbyte/source-github`, the only connector that is *certified* **and**
real code **and** public-data (39 of 59 certified sources are manifest-only YAML). Engine-ecosystem
activity (Godot/Bevy/O3DE + the modding long tail) is a real input to the scope/budget models.

Full head-to-head: [`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`](../../../docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md).

## Layout

```
experimental/ingestion/airbyte/
  up.sh / down.sh                  abctl local install/uninstall; port from the config SSoT
  credentials.sh                   abctl local credentials → AIRBYTE_CLIENT_ID/SECRET
  connectors/twitch/manifest.yaml  low-code declarative connector for Helix (source-twitch
                                   does not exist in the registry)
  terraform/
    modules/airbyte-connection/    airbyte_source + airbyte_connection + one shared destination
    variant-a-yamldecode/          fileset() + yamldecode() over spec/ — zero generation
    variant-b-codegen-tf/          generated .tf, committed
    variant-c-codegen-tfvars/      generated .tfvars.json + hand-written HCL
```

Only *how config reaches the module* differs between the variants; the resource definitions are
shared. Otherwise the comparison is dishonest and the HCL triplicates.

## Facts that bite

- Airbyte OSS **removed docker-compose** (2024-08-23, PR #13544). Both supported paths — `abctl`
  and Helm — end in Kubernetes. There is no compose file here on purpose.
- The Terraform provider is **8 generic resources**, not per-connector. Pinned **1.2.0** (1.3.0 is
  only `-rc1`). `definition_id` is resolved live via the `airbyte_connector_configuration` data
  source — never stored in a descriptor.
- OSS auth is **client credentials with a 15-minute token TTL** — never a static bearer, which can
  expire mid-apply.
- Sources are driven by the `airbyte:` blocks in `spec/sources/games/*.yaml`, which are a **one-way
  projection** from the ingestion registry SSoT (`~/.ai/skills/.settings/de/ingestion/sources/`).
  Edit the registry, not the projection.

## Status

- **Phase 0** — config SSoT + scaffold ✅
- **Phase 1** — runtime scripts written ✅; the **abctl runtime itself is a NO-GO on this
  machine** (disk-exhausted mid-install; the provider↔runtime premise is therefore *unverified*).
  See [`docs/techdebt/airbyte-lane.md`](../../../docs/techdebt/airbyte-lane.md#phase-1-result).
- **Phase 2** — shared `airbyte-connection` module, schema-verified vs provider 1.2.0, `validate`-green ✅
- **Phase 3** — Variant A (`terraform/variant-a-yamldecode/`): `validate`-green **offline** and
  `terraform console`-proven to discover `github_repos`+`reddit_posts` from the specs, exclude
  twitch (declarative → Phase 5), build github's 6 streams, and parse `godotengine/godot` from the
  descriptor url. `plan`/`apply` — the *measured* datapoint — are blocked on the runtime.
- **Phase 6** — CI `airbyte-tf` job (`fmt`+`validate`) ✅
- **Phases 4, 5, 7** — pending (Variants B/C + drift gate; Twitch declarative; the measured verdict).

**No verdict yet, by design.** The three-variant comparison (Phase 7) must rest on the Phase 3–4
*measurements* — a winner asserted here in advance would be exactly the false-green this repo's
`deferred_functionality` standard exists to prevent. Variant A's wiring is proven; its measured
run and Variants B/C await a working runtime.
