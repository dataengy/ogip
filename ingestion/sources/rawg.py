"""RAWG games source — the M0 walking-skeleton source (clean documented REST API).

Demo mode (no API key): loads the bundled fixture, so the full pipeline runs with zero
credentials. Live mode: paginated fetch from the RAWG API with retries + rate limiting.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ogip.config import Settings
from ogip.logger import log

from ..base.base_source import ApiSource

_FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "rawg_games.json"
_API_URL = "https://api.rawg.io/api/games"


class RawgGames(ApiSource):
    """RAWG `/games` — one record per game."""

    system = "rawg"
    entity = "games"

    def __init__(self, settings: Settings, *, max_pages: int = 1, page_size: int = 40) -> None:
        self.settings = settings
        self.max_pages = max_pages
        self.page_size = page_size

    def records(self) -> Iterator[dict[str, Any]]:
        if self.settings.rawg.is_configured:
            yield from self._fetch_live()
        else:
            log.bind(source=self.system).info("demo mode — loading fixture {p}", p=_FIXTURE.name)
            yield from self._load_fixture()

    def _load_fixture(self) -> Iterator[dict[str, Any]]:
        data: Any = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        yield from data

    def _fetch_live(self) -> Iterator[dict[str, Any]]:
        key = self.settings.rawg.api_key
        assert key is not None  # is_configured guard
        params: dict[str, str | int] = {
            "key": key.get_secret_value(),
            "page_size": self.page_size,
            "ordering": "-added",
        }
        with httpx.Client(timeout=30.0) as client:
            for page in range(1, self.max_pages + 1):
                payload = self._get(client, {**params, "page": page})
                results: list[dict[str, Any]] = payload.get("results", [])
                log.bind(source=self.system).info("page {n}: {c} games", n=page, c=len(results))
                yield from results
                if not payload.get("next"):
                    break

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=20))
    def _get(self, client: httpx.Client, params: dict[str, str | int]) -> dict[str, Any]:
        resp = client.get(_API_URL, params=params)
        resp.raise_for_status()
        data: Any = resp.json()
        return data
