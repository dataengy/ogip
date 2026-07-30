"""Unit tests — ScraperSource slice: SteamCharts CSS-selector parse (task #18).

No network anywhere (fixtures in unit tests). This is the registry's only CSS scrape, so the
tests pin what JSON-LD tests cannot: the three player-count numbers are read by ORDERED
position (current / 24h-peak / all-time), counts land AS-IS with their thousands separators
(Layer-0), and a page missing the app-stat structure yields nothing rather than a partial row.
"""

from __future__ import annotations

import pytest
from ingestion.sources.steamcharts import _FIXTURE, SteamChartsApp

PAGE_URL = "https://steamcharts.com/app/730"


@pytest.fixture
def source() -> SteamChartsApp:
    from ogip.config import get_settings

    return SteamChartsApp(get_settings())


class TestParse:
    def test_fixture_exists_and_is_small_text(self) -> None:
        assert _FIXTURE.is_file()
        assert _FIXTURE.stat().st_size < 16_384

    def test_parses_ordered_player_counts(self, source: SteamChartsApp) -> None:
        records = list(source.parse(PAGE_URL, _FIXTURE.read_text("utf-8")))
        assert len(records) == 1
        rec = records[0]
        assert rec["appid"] == "730"
        assert rec["name"] == "Counter-Strike 2"
        # AS-IS: Layer-0 keeps the site's thousands separators; the numeric cast is staging's job.
        assert rec["current_players"] == "912,345"
        assert rec["peak_24h"] == "1,401,890"
        assert rec["peak_all"] == "1,818,773"

    def test_content_hash_is_stable(self, source: SteamChartsApp) -> None:
        body = _FIXTURE.read_text("utf-8")
        first, second = (next(iter(source.parse(PAGE_URL, body))) for _ in range(2))
        assert first["content_hash"] == second["content_hash"]  # stable → landing upsert key
        assert len(first["content_hash"]) == 64

    def test_missing_appstat_structure_yields_nothing(self, source: SteamChartsApp) -> None:
        # Selector-rot guard: fewer than three ordered num blocks → no row, not a partial one.
        assert list(source.parse(PAGE_URL, "<html><h1 id='app-heading'>X</h1></html>")) == []
        one_stat = '<div class="app-stat"><span class="num">5</span></div>'
        assert list(source.parse(PAGE_URL, f"<html>{one_stat}</html>")) == []

    def test_num_spans_outside_appstat_are_ignored(self, source: SteamChartsApp) -> None:
        # A stray span.num elsewhere on the page must not be mistaken for a stat.
        stray = '<span class="num">999</span>'
        body = stray + _FIXTURE.read_text("utf-8")
        rec = next(iter(source.parse(PAGE_URL, body)))
        assert rec["current_players"] == "912,345"  # the app-stat one, not the stray 999

    def test_demo_records_need_no_network(self, source: SteamChartsApp) -> None:
        records = list(source.records())  # OGIP_STEAMCHARTS_LIVE unset → fixture path
        assert [r["name"] for r in records] == ["Counter-Strike 2"]

    def test_urls_come_from_config_appids(self, source: SteamChartsApp) -> None:
        urls = list(source.urls())
        assert urls == ["https://steamcharts.com/app/730"]


def test_layer0_table_name(source: SteamChartsApp) -> None:
    assert source.table_name == "steamcharts__app"


def test_fixture_is_marked_synthetic() -> None:
    assert "SYNTHETIC" in _FIXTURE.read_text("utf-8")[:400]
