"""Unit tests — ScraperSource slice: Metacritic JSON-LD parse + politeness math.

No network anywhere (task #18 rule: fixtures in unit tests). The fixture page carries TWO
ld+json blocks on purpose — selecting by @type (not first-block) is the trap under test.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ingestion.common.http import _DomainGate
from ingestion.sources.metacritic import _FIXTURE, MetacriticGame

if TYPE_CHECKING:
    pass

PAGE_URL = "https://www.metacritic.com/game/hades/"


@pytest.fixture
def source() -> MetacriticGame:
    from ogip.config import get_settings

    return MetacriticGame(get_settings())


class TestParse:
    def test_fixture_exists_and_is_small_text(self) -> None:
        # The fixture must stay a small, diffable TEXT file — the LFS law covers binaries.
        assert _FIXTURE.is_file()
        assert _FIXTURE.stat().st_size < 16_384

    def test_parses_video_game_block_not_breadcrumbs(self, source: MetacriticGame) -> None:
        records = list(source.parse(PAGE_URL, _FIXTURE.read_text("utf-8")))
        assert len(records) == 1  # BreadcrumbList block skipped, VideoGame taken
        rec = records[0]
        assert rec["name"] == "Hades"
        assert rec["metascore"] == 93
        assert rec["review_count"] == 61
        assert rec["publisher"] == "Supergiant Games"
        assert rec["genre"] == "Action RPG"
        assert rec["released"] == "2020-09-17"

    def test_natural_key_and_content_hash(self, source: MetacriticGame) -> None:
        body = _FIXTURE.read_text("utf-8")
        first, second = (next(iter(source.parse(PAGE_URL, body))) for _ in range(2))
        assert first["slug"] == "hades"
        assert first["content_hash"] == second["content_hash"]  # stable → landing upsert key
        assert len(first["content_hash"]) == 64

    def test_garbage_and_empty_pages_yield_nothing(self, source: MetacriticGame) -> None:
        assert list(source.parse(PAGE_URL, "<html>no ld+json here</html>")) == []
        broken = '<script type="application/ld+json">{not json</script>'
        assert list(source.parse(PAGE_URL, broken)) == []

    def test_demo_records_need_no_network(self, source: MetacriticGame) -> None:
        records = list(source.records())  # OGIP_METACRITIC_LIVE unset → fixture path
        assert [r["name"] for r in records] == ["Hades"]


class TestPoliteness:
    def test_domain_gate_enforces_min_interval(self) -> None:
        async def two_requests() -> float:
            gate = _DomainGate(per_domain=1, min_interval_secs=0.2)
            started = time.monotonic()
            await gate.wait_turn()
            await gate.wait_turn()
            return time.monotonic() - started

        elapsed = asyncio.run(two_requests())
        assert elapsed >= 0.2  # second request waited out the spacing

    def test_urls_come_from_config_slugs(self, source: MetacriticGame) -> None:
        urls = list(source.urls())
        assert urls == ["https://www.metacritic.com/game/hades/"]


def test_layer0_table_name(source: MetacriticGame) -> None:
    assert source.table_name == "metacritic__game"


def test_fixture_is_marked_synthetic() -> None:
    # Provenance honesty: a fixture that LOOKS like a captured page must say it is not.
    assert "SYNTHETIC" in Path(_FIXTURE).read_text("utf-8")[:400]
