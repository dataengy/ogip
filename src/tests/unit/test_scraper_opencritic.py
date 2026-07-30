"""Unit tests — ScraperSource slice: OpenCritic JSON-LD parse (task #18).

No network anywhere (fixtures in unit tests). Beyond the shared JSON-LD traps this pins the
two OpenCritic-specific ones from the registry: the numeric id — not the slug, not the
relative JSON-LD url — is the natural key, and the fixture carries a BreadcrumbList block
alongside the VideoGame one so @type selection is exercised.
"""

from __future__ import annotations

import pytest
from ingestion.sources.opencritic import _FIXTURE, OpenCriticGame

PAGE_URL = "https://opencritic.com/game/1548/the-legend-of-zelda-breath-of-the-wild/"


@pytest.fixture
def source() -> OpenCriticGame:
    from ogip.config import get_settings

    return OpenCriticGame(get_settings())


class TestParse:
    def test_fixture_exists_and_is_small_text(self) -> None:
        assert _FIXTURE.is_file()
        assert _FIXTURE.stat().st_size < 16_384

    def test_parses_video_game_block_not_breadcrumbs(self, source: OpenCriticGame) -> None:
        records = list(source.parse(PAGE_URL, _FIXTURE.read_text("utf-8")))
        assert len(records) == 1  # BreadcrumbList block skipped, VideoGame taken
        rec = records[0]
        assert rec["name"] == "The Legend of Zelda: Breath of the Wild"
        assert rec["score"] == 96
        assert rec["review_count"] == 132
        assert rec["publisher"] == "Nintendo"
        assert rec["genre"] == "Action Adventure"
        assert rec["released"] == "2017-03-03"

    def test_numeric_id_governs_not_slug(self, source: OpenCriticGame) -> None:
        # Registry trap 1: the id is the key, the slug is decorative and the JSON-LD url is
        # relative — identity must come from the fetched URL's numeric id.
        wrong_slug = "https://opencritic.com/game/1548/totally-wrong-slug/"
        rec = next(iter(source.parse(wrong_slug, _FIXTURE.read_text("utf-8"))))
        assert rec["game_id"] == "1548"
        assert rec["slug"] == "totally-wrong-slug"

    def test_natural_key_and_content_hash(self, source: OpenCriticGame) -> None:
        body = _FIXTURE.read_text("utf-8")
        first, second = (next(iter(source.parse(PAGE_URL, body))) for _ in range(2))
        assert first["game_id"] == "1548"
        assert first["content_hash"] == second["content_hash"]  # stable → landing upsert key
        assert len(first["content_hash"]) == 64

    def test_garbage_and_empty_pages_yield_nothing(self, source: OpenCriticGame) -> None:
        assert list(source.parse(PAGE_URL, "<html>no ld+json here</html>")) == []
        broken = '<script type="application/ld+json">{not json</script>'
        assert list(source.parse(PAGE_URL, broken)) == []

    def test_demo_records_need_no_network(self, source: OpenCriticGame) -> None:
        records = list(source.records())  # OGIP_OPENCRITIC_LIVE unset → fixture path
        assert [r["name"] for r in records] == ["The Legend of Zelda: Breath of the Wild"]

    def test_urls_come_from_config_pages(self, source: OpenCriticGame) -> None:
        urls = list(source.urls())
        assert urls == ["https://opencritic.com/game/1548/the-legend-of-zelda-breath-of-the-wild/"]


def test_layer0_table_name(source: OpenCriticGame) -> None:
    assert source.table_name == "opencritic__game"


def test_fixture_is_marked_synthetic() -> None:
    assert "SYNTHETIC" in _FIXTURE.read_text("utf-8")[:400]
