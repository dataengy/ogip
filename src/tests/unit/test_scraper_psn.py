"""Unit tests — ScraperSource slice: PSN Store Product JSON-LD parse (task #18).

No network anywhere (fixtures in unit tests). Pins the PSN-specific registry traps: the
record is a schema.org Product (not VideoGame), the stable JSON-LD is taken rather than the
brittle __NEXT_DATA__, and identity is the composite (concept_id, locale) parsed from the
fetched URL so a regional sweep produces one row per storefront.
"""

from __future__ import annotations

import pytest
from ingestion.sources.psn import _FIXTURE, PsnStoreConcept

PAGE_URL = "https://store.playstation.com/en-us/concept/232093/"


@pytest.fixture
def source() -> PsnStoreConcept:
    from ogip.config import get_settings

    return PsnStoreConcept(get_settings())


class TestParse:
    def test_fixture_exists_and_is_small_text(self) -> None:
        assert _FIXTURE.is_file()
        assert _FIXTURE.stat().st_size < 16_384

    def test_parses_product_block_not_breadcrumbs(self, source: PsnStoreConcept) -> None:
        records = list(source.parse(PAGE_URL, _FIXTURE.read_text("utf-8")))
        assert len(records) == 1  # BreadcrumbList block skipped, Product taken
        rec = records[0]
        assert rec["name"] == "Legendary Eleven"
        assert rec["sku"] == "UP1716-CUSA12032_00-LEGENDARYELEVEN0"
        assert rec["category"] == "Full Game"
        assert rec["price"] == "12.99"
        assert rec["currency"] == "USD"

    def test_composite_key_from_url(self, source: PsnStoreConcept) -> None:
        # Registry trap 3: identity is (concept_id, locale) from the URL, so the SAME game
        # in another locale is a distinct row.
        us = next(iter(source.parse(PAGE_URL, _FIXTURE.read_text("utf-8"))))
        de_url = "https://store.playstation.com/de-de/concept/232093/"
        de = next(iter(source.parse(de_url, _FIXTURE.read_text("utf-8"))))
        assert us["row_key"] == "232093:en-us"
        assert de["row_key"] == "232093:de-de"
        assert us["concept_id"] == de["concept_id"] == "232093"
        assert us["row_key"] != de["row_key"]

    def test_natural_key_and_content_hash(self, source: PsnStoreConcept) -> None:
        body = _FIXTURE.read_text("utf-8")
        first, second = (next(iter(source.parse(PAGE_URL, body))) for _ in range(2))
        assert first["content_hash"] == second["content_hash"]  # stable → landing upsert key
        assert len(first["content_hash"]) == 64

    def test_garbage_and_empty_pages_yield_nothing(self, source: PsnStoreConcept) -> None:
        assert list(source.parse(PAGE_URL, "<html>no ld+json here</html>")) == []
        broken = '<script type="application/ld+json">{not json</script>'
        assert list(source.parse(PAGE_URL, broken)) == []

    def test_demo_records_need_no_network(self, source: PsnStoreConcept) -> None:
        records = list(source.records())  # OGIP_PSN_LIVE unset → fixture path
        assert [r["name"] for r in records] == ["Legendary Eleven"]

    def test_urls_come_from_config_concepts(self, source: PsnStoreConcept) -> None:
        urls = list(source.urls())
        assert urls == ["https://store.playstation.com/en-us/concept/232093/"]


def test_layer0_table_name(source: PsnStoreConcept) -> None:
    assert source.table_name == "psn__concept"


def test_fixture_is_marked_synthetic() -> None:
    assert "SYNTHETIC" in _FIXTURE.read_text("utf-8")[:400]
