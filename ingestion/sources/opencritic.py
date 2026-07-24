"""OpenCritic game pages — the second quality-dimension scrape beside Metacritic (#18).

Same extraction contract as Metacritic: the page's schema.org ``VideoGame`` JSON-LD, published
for machines and surviving re-skins. Contract and politeness terms:
spec/sources/games/opencritic_game.yaml. Three registry traps this connector is built around:

1. **The numeric id governs; the slug is decorative.** ``/game/1548/anything`` serves id 1548's
   data regardless of the slug — so the natural key is the id parsed from the fetched URL, never
   the slug and never the JSON-LD.
2. **Two ld+json blocks** (VideoGame + BreadcrumbList) — select by ``@type``, never first-block.
3. **The JSON-LD ``url`` is RELATIVE** (``/game/...``), unlike Metacritic's absolute — another
   reason identity must come from the fetched URL.

Demo mode (default, zero network): parses the bundled fixture page. Live mode fetches
``https://opencritic.com/game/{id}/{slug}`` for the pages configured under
``sources.opencritic.pages`` in config/config.yml, through the shared politeness budget.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ingestion.base.scraper_source import ScraperSource

from ogip.config import load_app_config
from ogip.logger import log

if TYPE_CHECKING:
    from collections.abc import Iterator

_FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "opencritic_game.html"
_PAGE_URL = "https://opencritic.com/game/{page}/"
_DEMO_PAGE = "1548/the-legend-of-zelda-breath-of-the-wild"

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)
# From /game/<id>/<slug> take the numeric id (authoritative) and the decorative slug.
_ID_SLUG_RE = re.compile(r"/game/(?P<id>\d+)/(?P<slug>[^/?#]*)")


class OpenCriticGame(ScraperSource):
    """One record per game page: identity (numeric id) + the quality dimension (score)."""

    system = "opencritic"
    entity = "game"

    def urls(self) -> Iterator[str]:
        source_cfg = cast("dict[str, Any]", load_app_config()["sources"]["opencritic"])
        for page in cast("list[str]", source_cfg.get("pages", [])):
            yield _PAGE_URL.format(page=page)

    def records(self) -> Iterator[dict[str, Any]]:
        if self._live_mode():
            yield from super().records()
        else:
            log.bind(source=self.system).info("demo mode — parsing fixture {p}", p=_FIXTURE.name)
            yield from self.parse(_PAGE_URL.format(page=_DEMO_PAGE), _FIXTURE.read_text("utf-8"))

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
        m = _ID_SLUG_RE.search(url)
        return {
            # Natural key is the NUMERIC id from the URL — the slug is decorative and the
            # JSON-LD url is relative, so neither is trustworthy identity (registry trap 1/3).
            "game_id": m.group("id") if m else None,
            "slug": m.group("slug") if m else None,
            "content_hash": hashlib.sha256(raw_block.encode()).hexdigest(),
            "source_url": url,
            "name": ld.get("name"),
            "released": ld.get("datePublished"),
            "genre": ld.get("genre"),
            "publisher": publishers[0].get("name") if publishers else None,
            "score": rating.get("ratingValue"),
            "review_count": rating.get("reviewCount"),
        }

    def _live_mode(self) -> bool:
        """Live only when explicitly asked: OGIP_OPENCRITIC_LIVE=1. Scraping a real site
        must never be a silent side effect of `make run` — demo mode is the default."""
        return os.environ.get("OGIP_OPENCRITIC_LIVE") == "1"
