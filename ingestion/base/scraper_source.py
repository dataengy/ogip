"""`ScraperSource` — base for scraped sources (ADR-0014 first slice, task #18).

Contract for subclasses: implement ``urls()`` (the pages to fetch) and ``parse(url, body)``
(page → records). ``records()`` fetches every URL through the shared
:class:`~ingestion.common.http.PoliteFetcher` budget and parses each page.

This slice lands scraped records straight to raw Parquet via ``BaseSource.run``; the
Postgres ``landing`` hop (idempotent upsert on natural key + content hash, replayable
parses) is the next increment — see .ai/tasks/scraping-resilient.md deliverables.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from ingestion.common.http import PoliteFetcher

from .base_source import BaseSource

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ogip.config import Settings


class ScraperSource(BaseSource):
    """Base for HTML/undocumented-JSON scrapers; politeness comes from the config SSoT."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def urls(self) -> Iterator[str]:
        """Yield the page URLs for this sweep (discovery strategy lives in the subclass)."""

    @abstractmethod
    def parse(self, url: str, body: str) -> Iterator[dict[str, Any]]:
        """Extract records from one fetched page (pure function of the body — testable)."""

    def records(self) -> Iterator[dict[str, Any]]:
        fetcher = PoliteFetcher(self.settings.scraping)
        pages = fetcher.fetch_all(list(self.urls()))
        for url, body in pages.items():
            yield from self.parse(url, body)
