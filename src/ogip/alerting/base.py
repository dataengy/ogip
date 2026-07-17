"""Alert delivery — the transport-agnostic half.

Two layers, split on purpose:

* :class:`Messenger` — **how** to deliver on one backend (Telegram, Mattermost, Slack).
  A protocol, not a base class: a transport is anything that can send and self-check.
* :class:`Notifier` — **whether and what** to deliver: dry-run, fallback to a second
  transport, and a result object instead of an exception.

The last part is the important one. An alert that raises is worse than no alert: it turns
"the pipeline degraded" into "the pipeline crashed while complaining". So :meth:`Notifier.notify`
never propagates a transport error — it returns :class:`NotifyResult` and lets the caller decide.

Delivery is best-effort by design and does **not** retry: a failing primary falls straight
through to the fallback rather than blocking an already-unhappy pipeline behind backoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ogip.logger import logger

__all__ = ["Messenger", "Notifier", "NotifyResult", "split_message"]


@dataclass
class NotifyResult:
    """Outcome of one delivery attempt. Falsy when nothing was sent.

    ``backend`` names the transport that actually delivered — which is not always the one
    asked for: a fallback delivery reports ``sent=True`` with the fallback's name and a
    ``reason`` naming the primary that failed. An alert is never lost silently, but the
    degradation stays visible to whoever reads the result.
    """

    sent: bool
    backend: str
    reason: str = ""
    error: str = ""
    extra: dict[str, Any] = field(default_factory=dict[str, Any])

    def __bool__(self) -> bool:
        return self.sent


@runtime_checkable
class Messenger(Protocol):
    """A delivery backend. Structural — no inheritance required."""

    backend: str

    def send(self, text: str) -> dict[str, Any]:
        """Deliver one message. Raise on failure; return the backend's response."""
        ...

    def send_long(self, text: str) -> list[dict[str, Any]]:
        """Deliver a possibly-oversized message, splitting to the backend's limit."""
        ...

    def check_health(self) -> bool:
        """True when the backend is reachable and the credentials work."""
        ...


def split_message(text: str, limit: int) -> list[str]:
    """Split *text* into chunks of at most *limit* chars, preferring line boundaries.

    Every backend has a message-size cap, and all of them reject an oversized post rather
    than truncating it — so a long alert would vanish exactly when it matters most. Lines
    are kept intact where they fit; a single line longer than *limit* is hard-wrapped,
    since there is nothing better to break on.
    """
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:  # a single unbreakable line — hard-wrap it
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return [c for c in chunks if c]


class Notifier:
    """Send text through a :class:`Messenger`, with optional dry-run and fallback.

    Concrete and usable as-is::

        notifier = Notifier(TelegramMessenger(token, chat_id))
        result = notifier.notify("pipeline failed")
        if not result:
            logger.warning("alert not delivered: {e}", e=result.error)
    """

    def __init__(
        self,
        messenger: Messenger,
        *,
        dry_run: bool = False,
        fallback: Messenger | None = None,
    ) -> None:
        self.messenger = messenger
        self.dry_run = dry_run
        self.fallback = fallback

    def notify(self, text: str) -> NotifyResult:
        """Deliver *text*. Never raises — inspect the result."""
        if self.dry_run:
            logger.bind(backend=self.messenger.backend).info(
                "[dry-run] alert not sent: {preview}", preview=text[:200]
            )
            return NotifyResult(
                sent=False,
                backend=self.messenger.backend,
                reason="dry_run",
                extra={"preview": text[:500]},
            )
        try:
            self.messenger.send_long(text)
        except Exception as exc:
            logger.bind(backend=self.messenger.backend).error("alert send failed: {e}", e=exc)
            if self.fallback is None:
                return NotifyResult(sent=False, backend=self.messenger.backend, error=str(exc))
            return self._notify_via_fallback(text, primary_error=exc)
        logger.bind(backend=self.messenger.backend).debug("alert sent")
        return NotifyResult(sent=True, backend=self.messenger.backend)

    def _notify_via_fallback(self, text: str, *, primary_error: Exception) -> NotifyResult:
        assert self.fallback is not None  # guarded by the caller
        try:
            self.fallback.send_long(text)
        except Exception as fallback_error:
            logger.bind(backend=self.fallback.backend).error(
                "fallback also failed: {e}", e=fallback_error
            )
            return NotifyResult(
                sent=False,
                backend=self.messenger.backend,
                error=f"{primary_error}; fallback {self.fallback.backend}: {fallback_error}",
            )
        logger.bind(backend=self.fallback.backend).warning(
            "primary {primary} failed — delivered via fallback", primary=self.messenger.backend
        )
        return NotifyResult(
            sent=True,
            backend=self.fallback.backend,
            reason=f"fallback after {self.messenger.backend} failed",
            error=str(primary_error),
        )

    def notify_if_changed(
        self, text: str | None, *, skip_reason: str = "no change"
    ) -> NotifyResult:
        """Deliver only when *text* is not None — for callers that report only on change."""
        if text is None:
            logger.bind(backend=self.messenger.backend).info("alert skipped: {r}", r=skip_reason)
            return NotifyResult(sent=False, backend=self.messenger.backend, reason=skip_reason)
        return self.notify(text)

    def check_ready(self) -> bool:
        """True when the primary transport is reachable."""
        return self.messenger.check_health()

    def __repr__(self) -> str:
        return f"Notifier(backend={self.messenger.backend!r}, dry_run={self.dry_run})"
