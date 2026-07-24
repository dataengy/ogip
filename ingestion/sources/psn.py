"""PlayStation Store concept pages — console regional pricing (#18).

Extends the pricing dimension beyond Steam to console: PSN list/sale prices per region.
Contract and politeness terms: spec/sources/games/psn_store_concept.yaml. The registry traps
this connector is built around:

1. **Use ``/{locale}/concept/{id}`` URLs**, not ``/product/<sku>`` — the latter 302s through
   region/age gates; concept URLs return 200 directly.
2. **Extract the schema.org Product JSON-LD, not ``__NEXT_DATA__``.** The Next.js blob is
   richer but brittle across site builds; the JSON-LD subset (name, sku, category, price,
   currency) is the stable contract.
3. **Identity is (concept_id, locale).** One game has one row per regional storefront, so a
   regional sweep is one page fetch per locale — the key is derived from the fetched URL.

Demo mode (default, zero network): parses the bundled fixture page. Live mode fetches the
concepts configured under ``sources.psn.concepts`` in config/config.yml (``{locale}/{id}``
pairs), through the shared politeness budget.
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

_FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "psn_concept.html"
_PAGE_URL = "https://store.playstation.com/{concept}/"
_DEMO_CONCEPT = "en-us/concept/232093"

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)
# From /{locale}/concept/{concept_id} take the locale and the numeric concept id.
_LOCALE_CONCEPT_RE = re.compile(r"/(?P<locale>[a-z]{2}-[a-z]{2})/concept/(?P<concept_id>\d+)")


class PsnStoreConcept(ScraperSource):
    """One record per (concept, locale): identity + the regional pricing dimension."""

    system = "psn"
    entity = "concept"

    def urls(self) -> Iterator[str]:
        source_cfg = cast("dict[str, Any]", load_app_config()["sources"]["psn"])
        for concept in cast("list[str]", source_cfg.get("concepts", [])):
            yield _PAGE_URL.format(concept=concept)

    def records(self) -> Iterator[dict[str, Any]]:
        if self._live_mode():
            yield from super().records()
        else:
            log.bind(source=self.system).info("demo mode — parsing fixture {p}", p=_FIXTURE.name)
            demo_url = _PAGE_URL.format(concept=_DEMO_CONCEPT)
            yield from self.parse(demo_url, _FIXTURE.read_text("utf-8"))

    def parse(self, url: str, body: str) -> Iterator[dict[str, Any]]:
        """Extract the Product JSON-LD block — the page carries several ld+json blocks
        (BreadcrumbList etc.), so match on @type == Product, never take the first blindly."""
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
                if candidate.get("@type") == "Product":
                    yield self._record(url, candidate, raw_block)
                    break

    @staticmethod
    def _record(url: str, ld: dict[str, Any], raw_block: str) -> dict[str, Any]:
        offers = cast("dict[str, Any]", ld.get("offers") or {})
        m = _LOCALE_CONCEPT_RE.search(url)
        concept_id = m.group("concept_id") if m else None
        locale = m.group("locale") if m else None
        return {
            # Composite natural key: the same game has one row per regional storefront, so
            # neither concept_id nor locale is unique alone (registry trap 3).
            "row_key": f"{concept_id}:{locale}",
            "concept_id": concept_id,
            "locale": locale,
            "content_hash": hashlib.sha256(raw_block.encode()).hexdigest(),
            "source_url": url,
            "name": ld.get("name"),
            "sku": ld.get("sku"),
            "category": ld.get("category"),
            "price": offers.get("price"),
            "currency": offers.get("priceCurrency"),
        }

    def _live_mode(self) -> bool:
        """Live only when explicitly asked: OGIP_PSN_LIVE=1. Scraping a real site must never
        be a silent side effect of `make run` — demo mode is the default."""
        return os.environ.get("OGIP_PSN_LIVE") == "1"
