"""Unified alerting — one :class:`Notifier`, three transports.

The alerts abstraction from PLAN A10: business code says *what* happened, this package
decides *where* it goes and *how* to survive the destination being down.

    from ogip.alerting import make_notifier

    notifier = make_notifier()
    if notifier:
        notifier.notify("ingest failed: rawg 503")

``make_notifier`` returns ``None`` when no transport is configured, so alerting stays
optional — a pipeline without credentials runs green and simply says nothing, rather than
failing on a missing token. Set ``OGIP_ALERT_DRY_RUN=true`` to preview alerts with no
credentials at all (same zero-credential demo path the sources take).

Routing is env-driven (``OGIP_ALERT_BACKEND``, ``OGIP_ALERT_FALLBACK_BACKEND``); credentials
per transport are ``OGIP_TG_*`` / ``OGIP_MM_*`` / ``OGIP_SLACK_*``. See
``docs/architecture/observability.md``.
"""

from __future__ import annotations

from ogip.alerting.base import Messenger, Notifier, NotifyResult, split_message
from ogip.alerting.mattermost import MattermostMessenger
from ogip.alerting.settings import (
    AlertingSettings,
    MattermostSettings,
    SlackSettings,
    TelegramSettings,
)
from ogip.alerting.slack import SlackMessenger, SlackSendError
from ogip.alerting.telegram import TelegramMessenger
from ogip.logger import log

__all__ = [
    "BACKENDS",
    "AlertingSettings",
    "MattermostMessenger",
    "MattermostSettings",
    "Messenger",
    "Notifier",
    "NotifyResult",
    "SlackMessenger",
    "SlackSendError",
    "SlackSettings",
    "TelegramMessenger",
    "TelegramSettings",
    "make_messenger",
    "make_notifier",
    "split_message",
]

BACKENDS: tuple[str, ...] = ("telegram", "mattermost", "slack")


def make_messenger(backend: str) -> Messenger | None:
    """Build the transport named *backend* from the environment.

    Returns ``None`` when that transport has no usable credentials — the caller decides
    whether that is fatal. Raises :class:`ValueError` for a name that is not a transport at
    all, because that is a typo in config, not a missing secret.
    """
    if backend not in BACKENDS:
        raise ValueError(f"unknown alerting backend {backend!r} — expected one of {BACKENDS}")

    if backend == "telegram":
        tg = TelegramSettings()
        if not tg.is_configured:
            return None
        assert tg.bot_token is not None  # guarded by is_configured
        return TelegramMessenger(
            tg.bot_token.get_secret_value(),
            tg.chat_id,
            tg.topic_id,
            parse_mode=tg.parse_mode or None,
        )

    if backend == "mattermost":
        mm = MattermostSettings()
        if not mm.is_configured:
            return None
        return MattermostMessenger(
            url=mm.url,
            token=mm.token.get_secret_value() if mm.token else "",
            team=mm.team,
            channel=mm.channel,
            webhook_url=mm.webhook_url.get_secret_value() if mm.webhook_url else "",
            username=mm.username,
        )

    slack = SlackSettings()
    if not slack.is_configured:
        return None
    return SlackMessenger(
        token=slack.token.get_secret_value() if slack.token else "",
        channel=slack.channel,
        webhook_url=slack.webhook_url.get_secret_value() if slack.webhook_url else "",
        username=slack.username,
    )


def make_notifier(
    *,
    backend: str | None = None,
    fallback_backend: str | None = None,
    dry_run: bool | None = None,
) -> Notifier | None:
    """Build the configured :class:`Notifier`, or ``None`` when alerting is off.

    Arguments override the environment. A fallback naming the same backend as the primary is
    dropped: retrying the transport that just failed is not a fallback.
    """
    settings = AlertingSettings()
    primary_name = backend or settings.backend
    fallback_name = settings.fallback_backend if fallback_backend is None else fallback_backend
    effective_dry_run = settings.dry_run if dry_run is None else dry_run

    primary = make_messenger(primary_name)
    if primary is None:
        if not effective_dry_run:
            log.info("alerting off — backend {b} has no credentials", b=primary_name)
            return None
        # Dry-run previews the message and never sends, so credentials are beside the point.
        primary = _null_messenger(primary_name)

    fallback: Messenger | None = None
    if fallback_name and fallback_name != primary_name:
        fallback = make_messenger(fallback_name)
        if fallback is None:
            log.warning(
                "fallback {b} has no credentials — primary {p} has no safety net",
                b=fallback_name,
                p=primary_name,
            )

    return Notifier(primary, dry_run=effective_dry_run, fallback=fallback)


def _null_messenger(backend: str) -> Messenger:
    """A transport that refuses to send — only ever reached behind ``dry_run``."""

    class _Null:
        def __init__(self, name: str) -> None:
            self.backend = name

        def send(self, text: str) -> dict[str, object]:
            raise RuntimeError(f"{self.backend} is not configured")

        def send_long(self, text: str) -> list[dict[str, object]]:
            raise RuntimeError(f"{self.backend} is not configured")

        def check_health(self) -> bool:
            return False

    return _Null(backend)
