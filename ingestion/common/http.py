"""Polite async fetching for scraped sources (ADR-0014, first slice).

One shared budget: a global connection cap, a per-domain connection cap, and a per-domain
minimum interval — all from the config SSoT (`scraping:` in config/config.yml). Retries
back off exponentially and honour `Retry-After`. The identifying User-Agent is the
difference between polite automation and an anonymous scraper.

Not yet here (next increments, tracked in .ai/tasks/scraping-resilient.md): per-domain
circuit breaker, DLQ table, watermark checkpoints, conditional-GET cache.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ogip.logger import log

if TYPE_CHECKING:
    from ogip.config import ScrapingSettings


class RetryableFetchError(RuntimeError):
    """A response worth retrying (429 / 5xx), carrying the server's requested delay."""

    def __init__(self, status: int, retry_after_secs: float | None) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retry_after_secs = retry_after_secs


class _DomainGate:
    """Per-domain politeness: bounded concurrency + minimum spacing between requests."""

    def __init__(self, per_domain: int, min_interval_secs: float) -> None:
        self.semaphore = asyncio.Semaphore(per_domain)
        self.min_interval_secs = min_interval_secs
        self._last_request = 0.0
        self._spacing_lock = asyncio.Lock()

    async def wait_turn(self) -> None:
        async with self._spacing_lock:
            now = time.monotonic()
            delay = self._last_request + self.min_interval_secs - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()


class PoliteFetcher:
    """Fetch URLs under the shared politeness budget; returns ``{url: body_text}``.

    Failures after all retries are LOGGED and dropped from the result (the run continues
    degraded rather than crashing — a scraped sweep with one dead page is still a sweep).
    """

    def __init__(self, settings: ScrapingSettings) -> None:
        self._settings = settings
        self._global_semaphore = asyncio.Semaphore(settings.max_connections)
        self._gates: dict[str, _DomainGate] = {}

    def _gate(self, url: str) -> _DomainGate:
        domain = urlparse(url).netloc
        if domain not in self._gates:
            self._gates[domain] = _DomainGate(
                self._settings.per_domain, self._settings.min_interval_ms / 1000.0
            )
        return self._gates[domain]

    async def _fetch_one(self, client: httpx.AsyncClient, url: str) -> str:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._settings.retry_attempts),
            wait=wait_exponential(multiplier=1, max=30),
            retry=retry_if_exception_type((RetryableFetchError, httpx.TransportError)),
            reraise=True,
        ):
            with attempt:
                gate = self._gate(url)
                async with self._global_semaphore, gate.semaphore:
                    await gate.wait_turn()
                    response = await client.get(url)
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else None
                    if delay is not None:
                        await asyncio.sleep(delay)  # the server named its price — pay it
                    raise RetryableFetchError(response.status_code, delay)
                response.raise_for_status()  # 4xx (non-429): permanent, no retry
                return response.text
        raise AssertionError("unreachable — AsyncRetrying either returns or reraises")

    async def _fetch_all(self, urls: list[str]) -> dict[str, str]:
        results: dict[str, str] = {}
        async with httpx.AsyncClient(
            timeout=float(self._settings.timeout_secs),
            headers={"User-Agent": self._settings.user_agent},
            follow_redirects=True,
        ) as client:

            async def one(url: str) -> None:
                try:
                    results[url] = await self._fetch_one(client, url)
                except (RetryableFetchError, httpx.HTTPError) as exc:
                    # Degraded, not dead: record and continue. DLQ lands here next slice.
                    log.bind(url=url).warning("fetch failed after retries: {e}", e=exc)

            await asyncio.gather(*(one(u) for u in urls))
        return results

    def fetch_all(self, urls: list[str]) -> dict[str, str]:
        """Sync bridge for ``BaseSource.records()`` callers (dlt drives sync iterators)."""
        return asyncio.run(self._fetch_all(urls))
