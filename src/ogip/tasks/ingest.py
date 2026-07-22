"""Ingestion tasks — getting source data into the platform."""

from __future__ import annotations

from ogip.config import get_settings, load_app_config
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = [
    "ingest_all",
    "ingest_metacritic",
    "ingest_opencritic",
    "ingest_psn",
    "ingest_rawg",
    "ingest_steamcharts",
    "parse_to_landing",
]


@odos_task("ingest.rawg")
def ingest_rawg() -> str:
    """Extract RAWG games via dlt → raw Parquet (Layer 0). Returns the output path.

    Unconditional. The Dagster lane used to skip this when parquet was already present; that
    condition now belongs to whoever composes the job, not to the task.
    """
    from ingestion.sources.rawg import RawgGames

    settings = get_settings()
    out = RawgGames(settings).run(settings.platform.data_dir)
    log.bind(source="rawg").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.metacritic")
def ingest_metacritic() -> str:
    """Scrape Metacritic → raw Parquet (Layer 0). Returns the output path."""
    from ingestion.sources.metacritic import MetacriticGame

    settings = get_settings()
    out = MetacriticGame(settings).run(settings.platform.data_dir)
    log.bind(source="metacritic").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.opencritic")
def ingest_opencritic() -> str:
    """Scrape OpenCritic → raw Parquet (Layer 0). Returns the output path."""
    from ingestion.sources.opencritic import OpenCriticGame

    settings = get_settings()
    out = OpenCriticGame(settings).run(settings.platform.data_dir)
    log.bind(source="opencritic").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.psn")
def ingest_psn() -> str:
    """Scrape the PlayStation Store → raw Parquet (Layer 0). Returns the output path."""
    from ingestion.sources.psn import PsnStoreConcept

    settings = get_settings()
    out = PsnStoreConcept(settings).run(settings.platform.data_dir)
    log.bind(source="psn").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.steamcharts")
def ingest_steamcharts() -> str:
    """Scrape SteamCharts → raw Parquet (Layer 0). Returns the output path."""
    from ingestion.sources.steamcharts import SteamChartsApp

    settings = get_settings()
    out = SteamChartsApp(settings).run(settings.platform.data_dir)
    log.bind(source="steamcharts").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.all")
def ingest_all() -> str:
    """Run every source enabled in `config/config.yml`; return the RAWG output path.

    Enablement is a **configuration** fact (`sources.<name>.enabled`, SSoT per AGENTS.md hard
    rule 3), not a graph edge — so reading it here does not violate the rule that dependencies
    belong in the spec rather than in task bodies. A spec that wants one specific source still
    addresses `ingest.rawg` or `ingest.metacritic` directly.

    RAWG is unconditional: it is the Layer-0 producer the whole warehouse is built on. Its path
    is the return value because downstream steps key off the RAWG landing.
    """
    enabled = load_app_config()["sources"]
    out = ingest_rawg()
    for name, task in (
        ("metacritic", ingest_metacritic),
        ("opencritic", ingest_opencritic),
        ("psn", ingest_psn),
        ("steamcharts", ingest_steamcharts),
    ):
        if enabled.get(name, {}).get("enabled"):
            task()
        else:
            log.bind(source=name).info("disabled in config — skipped")
    return out


@odos_task("ingest.parse_to_landing")
def parse_to_landing() -> None:
    """Scraper/parser → Postgres `landing`. Placeholder until ADR-0014's ScraperSource lands."""
    log.warning(
        "ingest.parse_to_landing is a placeholder — wire the async ScraperSource (ADR-0014) here"
    )
