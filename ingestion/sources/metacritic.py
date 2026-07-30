"""Metacritic game pages — the first scraped source (task #18).

Metacritic replaced HLTB as the P1 scrape after HLTB's robots/ToS prohibition (see
spec/sources/games/hltb_games.yaml). Extraction contract: the page's schema.org
``VideoGame`` JSON-LD — published for machines and it survives re-skins; every
``class=*metascore*`` CSS selector died in a site rebuild, verified live. Contract and
politeness terms: spec/sources/games/metacritic_game.yaml.

Demo mode (default, zero network): parses the bundled fixture page. Live mode fetches
``https://www.metacritic.com/game/{slug}/`` for the slugs configured under
``sources.metacritic.slugs`` in config/config.yml, through the shared politeness budget.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ingestion.base.scraper_source import ScraperSource

from ogip.config import load_app_config
from ogip.logger import log

if TYPE_CHECKING:
    from collections.abc import Iterator

_FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "metacritic_game.html"
_PAGE_URL = "https://www.metacritic.com/game/{slug}/"

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)


class MetacriticGame(ScraperSource):
    """One record per game page: identity + the quality dimension (metascore)."""

    system = "metacritic"
    entity = "game"

    def urls(self) -> Iterator[str]:
        source_cfg = cast("dict[str, Any]", load_app_config()["sources"]["metacritic"])
        for slug in cast("list[str]", source_cfg.get("slugs", [])):
            yield _PAGE_URL.format(slug=slug)

    def records(self) -> Iterator[dict[str, Any]]:
        if self._live_mode():
            yield from super().records()
        else:
            log.bind(source=self.system).info("demo mode — parsing fixture {p}", p=_FIXTURE.name)
            yield from self.parse(_PAGE_URL.format(slug="hades"), _FIXTURE.read_text("utf-8"))

    def parse(self, url: str, body: str) -> Iterator[dict[str, Any]]:
        """Extract the VideoGame JSON-LD block — pages carry SEVERAL ld+json blocks
        (BreadcrumbList etc.), so match on @type, never take the first blindly."""
        for raw_block in _LD_JSON_RE.findall(body):
            try:
                doc: Any = json.loads(raw_block.strip())
            except json.JSONDecodeError:
                continue
            candidates: list[Any] = cast("list[Any]", doc) if isinstance(doc, list) else [doc]
            for candidate_any in candidates:
                if not isinstance(candidate_any, dict):
                    continue
                candidate = cast("dict[str, Any]", candidate_any)
                if candidate.get("@type") == "VideoGame":
                    yield self._record(url, candidate, raw_block)
                    break

    @staticmethod
    def _record(url: str, ld: dict[str, Any], raw_block: str) -> dict[str, Any]:
        rating = cast("dict[str, Any]", ld.get("aggregateRating") or {})
        publishers = cast("list[dict[str, Any]]", ld.get("publisher") or [])
        return {
            # Natural key + content hash — the future landing-upsert identity (ADR-0006).
            "slug": url.rstrip("/").rsplit("/", 1)[-1],
            "content_hash": hashlib.sha256(raw_block.encode()).hexdigest(),
            "source_url": url,
            "name": ld.get("name"),
            "released": ld.get("datePublished"),
            "genre": ld.get("genre"),
            "publisher": publishers[0].get("name") if publishers else None,
            "metascore": rating.get("ratingValue"),
            "review_count": rating.get("reviewCount"),
        }

    def _live_mode(self) -> bool:
        """Live only when explicitly asked: OGIP_METACRITIC_LIVE=1. Scraping a real site
        must never be a silent side effect of `make run` — demo mode is the default."""
        import os

        return os.environ.get("OGIP_METACRITIC_LIVE") == "1"
