"""Ingestion tasks — getting source data into the platform."""

from __future__ import annotations

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["ingest_rawg", "parse_to_landing"]


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


@odos_task("ingest.parse_to_landing")
def parse_to_landing() -> None:
    """Scraper/parser → Postgres `landing`. Placeholder until ADR-0014's ScraperSource lands."""
    log.warning(
        "ingest.parse_to_landing is a placeholder — wire the async ScraperSource (ADR-0014) here"
    )
