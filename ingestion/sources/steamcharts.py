"""SteamCharts app pages — concurrent-player traction time series (#18).

The registry's ONLY genuine CSS-selector scrape: SteamCharts serves no JSON-LD, so the numbers
come from ordered ``div.app-stat > span.num`` blocks. Contract and politeness terms:
spec/sources/games/steamcharts_app.yaml. The trap this connector is built around: **selector
rot is invisible to the eye.** The values are server-rendered (no JS), but if a rebuild moves
them the parse silently yields nothing — the registry's ``must_contain`` markers are the
structural alarm; here the parse asserting three ordered num blocks is the code-side echo.

Parsing uses only the standard library (``html.parser``) — the project installs no HTML
parser, and pulling one in for three spans would be the wrong dependency.

Demo mode (default, zero network): parses the bundled fixture page. Live mode fetches
``https://steamcharts.com/app/{appid}`` for the appids configured under
``sources.steamcharts.appids`` in config/config.yml, through the shared politeness budget.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ingestion.base.scraper_source import ScraperSource

from ogip.config import load_app_config
from ogip.logger import log

if TYPE_CHECKING:
    from collections.abc import Iterator

_FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "steamcharts_app.html"
_PAGE_URL = "https://steamcharts.com/app/{appid}"
_DEMO_APPID = "730"
_APPID_RE = re.compile(r"/app/(?P<appid>\d+)")


class _AppStatParser(HTMLParser):
    """Collect, in document order, the text of every ``span.num`` inside a ``div.app-stat``,
    plus the ``h1#app-heading`` text. Order is the contract: [current, 24h-peak, all-time]."""

    def __init__(self) -> None:
        super().__init__()
        self._div_is_appstat: list[bool] = []  # one flag per open <div>
        self._appstat_depth = 0
        self._in_num = False
        self._in_heading = False
        self._num_buf: list[str] = []
        self._heading_buf: list[str] = []
        self.nums: list[str] = []
        self.heading = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        classes = attr.get("class", "").split()
        if tag == "div":
            is_appstat = "app-stat" in classes
            self._div_is_appstat.append(is_appstat)
            if is_appstat:
                self._appstat_depth += 1
        elif tag == "span" and "num" in classes and self._appstat_depth > 0:
            self._in_num = True
            self._num_buf = []
        elif tag == "h1" and attr.get("id") == "app-heading":
            self._in_heading = True
            self._heading_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._div_is_appstat:
            if self._div_is_appstat.pop():
                self._appstat_depth -= 1
        elif tag == "span" and self._in_num:
            self._in_num = False
            self.nums.append("".join(self._num_buf).strip())
        elif tag == "h1" and self._in_heading:
            self._in_heading = False
            self.heading = "".join(self._heading_buf).strip()

    def handle_data(self, data: str) -> None:
        if self._in_num:
            self._num_buf.append(data)
        elif self._in_heading:
            self._heading_buf.append(data)


class SteamChartsApp(ScraperSource):
    """One record per app: identity (appid) + the traction dimension (player counts)."""

    system = "steamcharts"
    entity = "app"

    def urls(self) -> Iterator[str]:
        source_cfg = cast("dict[str, Any]", load_app_config()["sources"]["steamcharts"])
        for appid in cast("list[Any]", source_cfg.get("appids", [])):
            yield _PAGE_URL.format(appid=appid)

    def records(self) -> Iterator[dict[str, Any]]:
        if self._live_mode():
            yield from super().records()
        else:
            log.bind(source=self.system).info("demo mode — parsing fixture {p}", p=_FIXTURE.name)
            yield from self.parse(_PAGE_URL.format(appid=_DEMO_APPID), _FIXTURE.read_text("utf-8"))

    def parse(self, url: str, body: str) -> Iterator[dict[str, Any]]:
        """CSS scrape: require the three ordered app-stat numbers. Fewer than three means the
        page changed shape — yield nothing rather than a half-parsed row (selector-rot guard)."""
        parser = _AppStatParser()
        parser.feed(body)
        if len(parser.nums) < 3:
            return
        m = _APPID_RE.search(url)
        current, peak_24h, peak_all = parser.nums[0], parser.nums[1], parser.nums[2]
        # No JSON-LD block to hash — the content identity is the extracted tuple.
        content = json.dumps(
            {"appid": m.group("appid") if m else None, "n": [current, peak_24h, peak_all]},
            sort_keys=True,
        )
        yield {
            "appid": m.group("appid") if m else None,  # natural key from the URL
            "name": parser.heading or None,
            "current_players": current,
            "peak_24h": peak_24h,
            "peak_all": peak_all,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "source_url": url,
        }

    def _live_mode(self) -> bool:
        """Live only when explicitly asked: OGIP_STEAMCHARTS_LIVE=1. Scraping a real site must
        never be a silent side effect of `make run` — demo mode is the default."""
        return os.environ.get("OGIP_STEAMCHARTS_LIVE") == "1"
